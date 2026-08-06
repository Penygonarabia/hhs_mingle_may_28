/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
  fmt, fmtHours, groupedBarChart, donutChart, kpiTileHtml, attachValueTooltips,
  setTooltipEl, clearTooltipEl, moveTip,
  PALETTE,
} from "./pbi_chart_lib";
import { PROMOTER_BOARD_KEYS } from "./promoter_config_client";
import { t, tDate, addLabels, isArabicUI } from "./pbi_i18n";

// EN -> AR for every board title (promoter_config.py BoardConfig.title),
// KPI/chart name (ChartItemConfig.name), and dual-measure bar
// series_labels across both Promoter Dashboards boards ("Promoters",
// "Promoter - Sales Comparison") — the complete set of static strings
// promoter_config.py ever sends to the client. Keyed by the exact English
// string promoter_config.py uses, so t()/state.title and t()/item.name in
// the template pick these up with no per-board wiring. Generic chrome
// words already registered by service_dashboard.js's addLabels() (Region,
// Source, live from, Promoter Dashboards, Actual, ...) are reused via the
// shared pbi_i18n LABELS map and not repeated here.
addLabels({
  // board titles
  "Promoters": "المروجون",
  "Promoter - Sales Comparison": "المروجون - مقارنة المبيعات",
  // KPI / chart names
  "Employees Count By Region, City & Showroom": "عدد الموظفين حسب المنطقة والمدينة والمعرض",
  "Sales (Qty) - Region, City, Product Group, Sub-group wise": "المبيعات (الكمية) - حسب المنطقة والمدينة ومجموعة المنتج والمجموعة الفرعية",
  "Sales (Qty) - Month & Region, City, Showroom wise": "المبيعات (الكمية) - حسب الشهر والمنطقة والمدينة والمعرض",
  "Target vs Actual (Qty) - Overall": "المستهدف مقابل الفعلي (الكمية) - الإجمالي",
  "Sales (Actual vs Target) - Region wise": "المبيعات (الفعلي مقابل المستهدف) - حسب المنطقة",
  "Sales (Actual vs Target) - City wise": "المبيعات (الفعلي مقابل المستهدف) - حسب المدينة",
  "Sales (Actual vs Target) - Month wise": "المبيعات (الفعلي مقابل المستهدف) - حسب الشهر",
  // series labels (dual-measure bar) — "Actual" already in the shared dict
  "Target": "المستهدف",
});

// Same 7-option vocabulary/order/date-math as service_main.py's (and, by
// extension, promoter_main.py's, which shares _resolve_date_range via
// PbiDashboardBoardEngineMixin) DATE_FILTER_LABELS — every board's filter
// bar, default "This Month".
const DATE_FILTER_OPTIONS = [
  { v: 't_year', l: 'This Year' },
  { v: 't_month', l: 'This Month' },
  { v: 't_week', l: 'This Week' },
  { v: 'ls_year', l: 'Last Year' },
  { v: 'ls_month', l: 'Last Month' },
  { v: 'ls_week', l: 'Last Week' },
  { v: 'l_custom', l: 'Custom' },
];
const DEFAULT_DATE_FILTER = 't_month';

// See service_dashboard.js's identical helper set — same sessionStorage
// filter-persistence rationale (Odoo's action manager destroys/rebuilds
// this component on every navigation away and back), namespaced
// separately per board key so Promoter Dashboards filters never collide
// with Service Dashboards ones.
function filterStorageKey(boardKey) {
  return `pbi_promoter_dashboard_filters_${boardKey}`;
}

function loadStoredFilters(boardKey) {
  try {
    const raw = sessionStorage.getItem(filterStorageKey(boardKey));
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function saveStoredFilters(boardKey, filters) {
  try {
    sessionStorage.setItem(filterStorageKey(boardKey), JSON.stringify(filters));
  } catch (e) {
    // ignore (private-browsing storage quota, etc.) — just won't persist
  }
}

export class PbiPromoterDashboard extends Component {
  static template = "pbi_dashboards.promoter_dashboard";
  static props = ["*"];
  // Set per-registration below — which board key (promoter_config.py
  // PROMOTER_BOARDS entry) this instance of the shared component renders.
  static boardKey = null;

  setup() {
    this.rpc = useService("rpc");
    this.actionService = useService("action");
    this.boardKey = this.constructor.boardKey;
    this.t = t;
    this.isArabicUI = isArabicUI;

    const stored = loadStoredFilters(this.boardKey) || {};

    this.state = useState({
      title: '', periodLabel: '', loading: false, error: '',
      items: [],
      // Per-chart INDEPENDENT drill state, keyed by item.key — same
      // convention as Service Dashboards: clicking one chart never
      // touches another chart's state or triggers a full-board reload.
      charts: {},
      dateFilter: stored.dateFilter || DEFAULT_DATE_FILTER,
      customStart: stored.customStart || '', customEnd: stored.customEnd || '',
      regionFilterable: false, regionOptions: [], region: stored.region || 'all',
    });

    this.dateFilterOptions = DATE_FILTER_OPTIONS;

    this.rootRef = useRef('root');
    this.tooltipRef = useRef('tooltip');

    // See service_dashboard.js's identical onPatched rationale: chart
    // containers only exist once OWL commits the DOM patch, so drawing
    // has to happen after that, not in onRendered.
    onPatched(() => this.renderAll());

    this._onMouseMove = evt => moveTip(evt);
    onMounted(() => {
      setTooltipEl(this.tooltipRef.el);
      document.addEventListener('mousemove', this._onMouseMove);
      this.load();
    });
    onWillUnmount(() => {
      document.removeEventListener('mousemove', this._onMouseMove);
      clearTooltipEl(this.tooltipRef.el);
    });
  }

  get kpiItems() { return this.state.items.filter(i => i.type === 'kpi_single' || i.type === 'kpi_dual'); }
  get chartItems() { return this.state.items.filter(i => i.type !== 'kpi_single' && i.type !== 'kpi_dual'); }

  filterParams() {
    return {
      dateFilter: this.state.dateFilter,
      customStart: this.state.customStart,
      customEnd: this.state.customEnd,
      region: this.state.region,
    };
  }

  async load() {
    if (this.state.dateFilter === 'l_custom' && (!this.state.customStart || !this.state.customEnd)) {
      return;
    }
    this.state.loading = true;
    this.state.error = '';
    try {
      const res = await this.rpc('/pbi_dashboards/promoter/board', { board: this.boardKey, ...this.filterParams() });
      if (res.error) { this.state.error = res.error; return; }
      this.state.title = t(res.title);
      this.state.periodLabel = tDate(res.period.label);
      this.state.regionFilterable = res.regionFilterable;
      this.state.regionOptions = res.regionOptions || [];
      this.state.items = res.items;
      const charts = {};
      for (const item of res.items) {
        charts[item.key] = { drillPath: [], breadcrumb: [], terminal: false, data: item };
      }
      this.state.charts = charts;
    } catch (e) {
      this.state.error = 'Failed to load — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  persistFilters() {
    saveStoredFilters(this.boardKey, {
      dateFilter: this.state.dateFilter,
      customStart: this.state.customStart,
      customEnd: this.state.customEnd,
      region: this.state.region,
    });
  }

  selectDateFilter(value) {
    this.state.dateFilter = value;
    this.persistFilters();
    if (value !== 'l_custom') { this.load(); }
  }

  selectCustomStart(value) {
    this.state.customStart = value;
    this.persistFilters();
    this.load();
  }

  selectCustomEnd(value) {
    this.state.customEnd = value;
    this.persistFilters();
    this.load();
  }

  selectRegion(value) {
    this.state.region = value;
    this.persistFilters();
    this.load();
  }

  itemContainer(key) {
    return this.rootRef.el && this.rootRef.el.querySelector(`[data-item-key="${key}"] .chart-body`);
  }

  renderAll() {
    this.state.items.forEach((item, idx) => {
      if (item.type === 'kpi_single' || item.type === 'kpi_dual') {
        this.renderKpi(item, idx);
      } else {
        this.renderChart(item.key);
      }
    });
  }

  renderKpi(item, idx) {
    const el = this.itemContainer(item.key);
    if (!el) return;
    const valueFmt = item.valueFormat === 'hours' ? fmtHours : fmt;
    el.innerHTML = kpiTileHtml(item, idx % 6, valueFmt);
    attachValueTooltips(el, '.pbi-kpi[data-tip]');
  }

  renderChart(key) {
    const item = this.state.items.find(i => i.key === key);
    const chart = this.state.charts[key];
    const el = this.itemContainer(key);
    if (!el || !item || !chart) return;
    const breakdown = chart.data.breakdown || [];
    const onClick = (code, label) => this.onChartClick(key, code, label);
    const valueFmt = chart.data.valueFormat === 'hours' ? fmtHours : fmt;
    if (item.type === 'pie') {
      donutChart(el, breakdown.map(d => ({ code: d.code, label: d.label, value: d.value })), PALETTE, onClick, valueFmt);
    } else if (chart.data.seriesLabels) {
      // Dual-measure bar item (e.g. Sales (Actual vs Target)) — same
      // per-category click/drill as a single-series bar, just 2 bars per
      // category instead of 1.
      groupedBarChart(el, breakdown.map(d => ({ code: d.code, label: d.label, value: d.value, value2: d.value2 })),
        ['value', 'value2'], [PALETTE[0], PALETTE[1]], chart.data.seriesLabels, onClick, valueFmt);
    } else {
      groupedBarChart(el, breakdown.map(d => ({ code: d.code, label: d.label, value: d.value })),
        ['value'], [PALETTE[0]], [item.name], onClick, valueFmt);
    }
  }

  // Called when a bar/pie tile is clicked — drills THIS chart only, one
  // level deeper along its own configured field chain (see
  // promoter_config.py ChartItemConfig.drill / service_sql.py
  // run_breakdown). Once the chain is exhausted, the server returns a
  // terminal domain and this opens a NATIVE Odoo list+form.
  async onChartClick(key, code, label) {
    const chart = this.state.charts[key];
    const newPath = [...chart.drillPath, { code, label }];
    try {
      const res = await this.rpc('/pbi_dashboards/promoter/chart', {
        board: this.boardKey, item: key, drillPath: newPath, ...this.filterParams(),
      });
      if (res.error) { this.state.error = res.error; return; }
      if (res.terminal) {
        await this.actionService.doAction({
          type: 'ir.actions.act_window',
          res_model: res.model,
          view_mode: 'list,form',
          views: [[false, 'list'], [false, 'form']],
          domain: res.domain,
          name: res.name,
          target: 'current',
        });
        return; // don't advance this chart's own drillPath past its last real level
      }
      chart.drillPath = newPath;
      chart.breadcrumb = [...chart.breadcrumb, label];
      chart.data = { ...chart.data, breakdown: res.breakdown, level: res.level };
    } catch (e) {
      this.state.error = 'Failed to load — ' + e.message;
    }
  }

  async drillTo(key, pathIndex) {
    const chart = this.state.charts[key];
    const newPath = chart.drillPath.slice(0, pathIndex + 1);
    try {
      const res = await this.rpc('/pbi_dashboards/promoter/chart', {
        board: this.boardKey, item: key, drillPath: newPath, ...this.filterParams(),
      });
      if (res.error || res.terminal) return; // breadcrumb clicks always land on a non-terminal level
      chart.drillPath = newPath;
      chart.breadcrumb = chart.breadcrumb.slice(0, pathIndex + 1);
      chart.data = { ...chart.data, breakdown: res.breakdown, level: res.level };
    } catch (e) {
      this.state.error = 'Failed to load — ' + e.message;
    }
  }

}

for (const key of PROMOTER_BOARD_KEYS) {
  class Bound extends PbiPromoterDashboard {}
  Bound.boardKey = key;
  registry.category("actions").add(`pbi_dashboards.promoter_dashboard_${key}`, Bound);
}
