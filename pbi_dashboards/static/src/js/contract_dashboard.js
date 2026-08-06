/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
  fmt, fmtHours, fmtM, groupedBarChart, donutChart, kpiTileHtml, attachValueTooltips,
  setTooltipEl, clearTooltipEl, moveTip,
  PALETTE,
} from "./pbi_chart_lib";
import { CONTRACT_BOARD_KEYS } from "./contract_config_client";
import { t, tDate, addLabels, isArabicUI } from "./pbi_i18n";

// EN -> AR for every board title (contract_config.py BoardConfig.title),
// KPI/chart name (ChartItemConfig.name), dual-measure bar series_labels,
// and Visits-Comparison table column label — the complete set of static
// strings contract_config.py ever sends to the client. Keyed by the exact
// English string contract_config.py uses, so t()/state.title, t()/
// item.name in the template, and t()/c.label in renderTable() below all
// pick these up with no per-board wiring. Generic chrome words already
// registered by service_dashboard.js's addLabels() (Region, Source,
// live from, Contract Dashboards, Actual, ...) are reused via the shared
// pbi_i18n LABELS map and not repeated here.
addLabels({
  // board titles
  "Contract Analysis": "تحليل العقود",
  // KPI / chart names
  "Contract Analysis - Amount (Region wise)": "تحليل العقود - القيمة (حسب المنطقة)",
  "Contract Analysis - Quantity (Region wise)": "تحليل العقود - الكمية (حسب المنطقة)",
  "Contract Analysis - Amount (Month wise)": "تحليل العقود - القيمة (حسب الشهر)",
  "Contract Analysis - Quantity (Month wise)": "تحليل العقود - الكمية (حسب الشهر)",
  "Sales Analysis - Amount (Salesman wise)": "تحليل المبيعات - القيمة (حسب مندوب المبيعات)",
  "Maintenance Service Analysis vs Contract Value": "تحليل خدمة الصيانة مقابل قيمة العقد",
  "Visits Comparison - Preventive & Corrective (Est vs Actual)": "مقارنة الزيارات - الوقائية والتصحيحية (التقديري مقابل الفعلي)",
  // series labels (dual-measure bar)
  "Service Amount (Excl. VAT)": "قيمة الخدمة (غير شاملة الضريبة)",
  "Contract Amount (Incl. VAT)": "قيمة العقد (شاملة الضريبة)",
  // Visits Comparison table column headers
  "City": "المدينة",
  "Contract No": "رقم العقد",
  "Customer": "العميل",
  "Salesman": "مندوب المبيعات",
  "Preventive Est": "الوقائي التقديري",
  "Preventive Actual": "الوقائي الفعلي",
  "Preventive Balance": "الوقائي المتبقي",
  "Corrective Est": "التصحيحي التقديري",
  "Corrective Actual": "التصحيحي الفعلي",
  "Corrective Balance": "التصحيحي المتبقي",
  // table empty state
  "No records": "لا توجد سجلات",
});

// item.valueFormat -> chart-lib formatter, matches service_main.py's
// _value_format ('hours' | 'millions' | 'number') — 'millions' is
// Contract Analysis's own addition (contract_amount/service_amount run
// into the hundreds of thousands, so "0.4M" reads better than "393,758",
// both on KPI tiles and on chart axis ticks/value labels).
function valueFmtFor(item) {
  if (item.valueFormat === 'hours') return fmtHours;
  if (item.valueFormat === 'millions') return fmtM;
  return fmt;
}

// Same 7-option vocabulary/order/date-math as service_main.py's (and, by
// extension, contract_main.py's, which shares _resolve_date_range via
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
// separately per board key so Contract Dashboards filters never collide
// with Service/Promoter Dashboards ones.
function filterStorageKey(boardKey) {
  return `pbi_contract_dashboard_filters_${boardKey}`;
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

// Minimal HTML-escape for table cell text (customer/contract names come
// straight from the DB, unlike every other chart label here which only
// ever reaches a title="..."/data-tip attribute via the shared chart-lib
// helpers) — a "&"/"<" in a name would otherwise corrupt the row markup.
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

export class PbiContractDashboard extends Component {
  static template = "pbi_dashboards.contract_dashboard";
  static props = ["*"];
  // Set per-registration below — which board key (contract_config.py
  // CONTRACT_BOARDS entry) this instance of the shared component renders.
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
      // convention as Service/Promoter Dashboards: clicking one chart
      // never touches another chart's state or triggers a full-board
      // reload. 'table' items never populate drillPath/breadcrumb.
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
      const res = await this.rpc('/pbi_dashboards/contract/board', { board: this.boardKey, ...this.filterParams() });
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
      } else if (item.type === 'table') {
        this.renderTable(item.key);
      } else {
        this.renderChart(item.key);
      }
    });
  }

  renderKpi(item, idx) {
    const el = this.itemContainer(item.key);
    if (!el) return;
    const valueFmt = valueFmtFor(item);
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
    const valueFmt = valueFmtFor(chart.data);
    if (item.type === 'pie') {
      donutChart(el, breakdown.map(d => ({ code: d.code, label: d.label, value: d.value })), PALETTE, onClick, valueFmt);
    } else if (chart.data.seriesLabels) {
      // Dual-measure bar item (e.g. Maintenance Service Analysis vs
      // Contract Value) — same per-category click/drill as a single-series
      // bar, just 2 bars per category instead of 1.
      groupedBarChart(el, breakdown.map(d => ({ code: d.code, label: d.label, value: d.value, value2: d.value2 })),
        ['value', 'value2'], [PALETTE[0], PALETTE[1]], chart.data.seriesLabels, onClick, valueFmt);
    } else {
      groupedBarChart(el, breakdown.map(d => ({ code: d.code, label: d.label, value: d.value })),
        ['value'], [PALETTE[0]], [item.name], onClick, valueFmt);
    }
  }

  // 'table' items (e.g. Visits Comparison) — a flat, ungrouped row listing
  // with no server-side drill chain (the source list view has none
  // either): clicking a row opens that contract's own form directly,
  // computed client-side from the row's own id (no round trip needed).
  renderTable(key) {
    const item = this.state.items.find(i => i.key === key);
    const el = this.itemContainer(key);
    if (!el || !item) return;
    const cols = item.columns || [];
    const rows = item.rows || [];
    let html = '<div class="pbi-table-scroll"><table class="pbi-table"><thead><tr>';
    html += cols.map(c => `<th class="${c.numeric ? 'num' : ''}">${esc(t(c.label))}</th>`).join('');
    html += '</tr></thead><tbody>';
    if (!rows.length) {
      html += `<tr><td colspan="${cols.length}" class="pbi-table-empty">${esc(t('No records'))}</td></tr>`;
    }
    rows.forEach(row => {
      html += `<tr data-row-id="${row.id}">`;
      html += cols.map(c => {
        const v = row[c.field];
        return `<td class="${c.numeric ? 'num' : ''}">${c.numeric ? fmt(v) : esc(v)}</td>`;
      }).join('');
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    el.innerHTML = html;
    el.querySelectorAll('tr[data-row-id]').forEach(tr => {
      tr.addEventListener('click', () => this.openRecord(item.recordModel, +tr.getAttribute('data-row-id')));
    });
  }

  async openRecord(model, resId) {
    if (!model || !resId) return;
    await this.actionService.doAction({
      type: 'ir.actions.act_window',
      res_model: model,
      res_id: resId,
      view_mode: 'form',
      views: [[false, 'form']],
      target: 'current',
    });
  }

  // Called when a bar/pie tile is clicked — drills THIS chart only, one
  // level deeper along its own configured field chain (see
  // contract_config.py ChartItemConfig.drill / service_sql.py
  // run_breakdown). Once the chain is exhausted, the server returns a
  // terminal domain and this opens a NATIVE Odoo list+form.
  async onChartClick(key, code, label) {
    const chart = this.state.charts[key];
    const newPath = [...chart.drillPath, { code, label }];
    try {
      const res = await this.rpc('/pbi_dashboards/contract/chart', {
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
      const res = await this.rpc('/pbi_dashboards/contract/chart', {
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

for (const key of CONTRACT_BOARD_KEYS) {
  class Bound extends PbiContractDashboard {}
  Bound.boardKey = key;
  registry.category("actions").add(`pbi_dashboards.contract_dashboard_${key}`, Bound);
}
