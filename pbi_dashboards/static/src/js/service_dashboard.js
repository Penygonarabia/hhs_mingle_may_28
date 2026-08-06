/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
  fmt, fmtHours, fmtM, fmtPctPrecise, groupedBarChart, donutChart, kpiTileHtml, attachValueTooltips,
  setTooltipEl, clearTooltipEl, moveTip, showTip, hideTip,
  PALETTE,
} from "./pbi_chart_lib";

// service_main.py's _value_format -> the formatter it names. "percent"
// is fmtPctPrecise (2 decimals: the utilization spec's own worked example
// is 96.59%, which fmtPct's 1 decimal would round away). "millions" was
// already being sent by _value_format for *_amount measures but never
// handled here, so those values rendered as plain integers.
const VALUE_FORMATTERS = {
  hours: fmtHours,
  percent: fmtPctPrecise,
  millions: fmtM,
};
const valueFormatter = name => VALUE_FORMATTERS[name] || fmt;
import { BOARD_KEYS } from "./service_config_client";
import { t, tDate, addLabels, isArabicUI } from "./pbi_i18n";

// EN -> AR for every board title (service_config.py BoardConfig.title) and
// KPI/chart name (ChartItemConfig.name) across all 15 Service Dashboards
// boards, plus the one dual-measure bar's series_labels — the complete set
// of static strings service_config.py ever sends to the client. Keyed by
// the exact English string service_config.py uses, so t()/state.title and
// t()/item.name in the template pick these up with no per-board wiring.
addLabels({
  // board titles
  "Service Analysis": "تحليل الخدمة",
  "Service Analysis (C)": "تحليل الخدمة (المنطقة الوسطى)",
  "Service Analysis (E)": "تحليل الخدمة (المنطقة الشرقية)",
  "Service Analysis (W)": "تحليل الخدمة (المنطقة الغربية)",
  "Service Analysis (UWC)": "تحليل الخدمة (موقع عمل المستخدم)",
  "Service Analysis (JCs)": "تحليل الخدمة (بطاقات العمل)",
  "Sales & Cost Analysis": "تحليل المبيعات والتكاليف",
  "Service Analysis (CC)": "تحليل الخدمة (مركز الاتصال)",
  "Service Analysis (CRD)": "تحليل الخدمة (منسق)",
  "Service Analysis (Parts)": "تحليل الخدمة (قطع الغيار)",
  "Technician Analysis": "تحليل الفنيين",
  "Service Analysis - CC Users": "تحليل الخدمة - مستخدمو مركز الاتصال",
  "Service Analysis - CRD Users": "تحليل الخدمة - مستخدمو التنسيق",
  "Service Analysis - Parts Users": "تحليل الخدمة - مستخدمو قطع الغيار",
  "Service Analysis - Technicians": "تحليل الخدمة - الفنيون",
  // KPI / chart names
  "Total / Closed Job Cards": "بطاقات العمل: الإجمالي / المغلق",
  "Total service Revenue": "إجمالي إيرادات الخدمة",
  "Labor Revenue": "إيرادات العمالة",
  "Spare Parts Revenue": "إيرادات قطع الغيار",
  "Spare Parts Warranty": "ضمان قطع الغيار",
  "AVG RTAT": "متوسط زمن الاستجابة (RTAT)",
  "Month wise - Jobs Count": "عدد الأعمال حسب الشهر",
  "Job Cards - Status analysis on weekly basis": "بطاقات العمل - تحليل الحالة أسبوعيًا",
  "Job Cards - Not Closed Status analysis on weekly basis": "بطاقات العمل - تحليل الحالة غير المغلقة أسبوعيًا",
  "Job Status Wise - Count": "عدد بطاقات العمل حسب الحالة",
  "Warranty Sts & Region - Jobs Count": "عدد الأعمال حسب حالة الضمان والمنطقة",
  "Warranty Status - Jobs (%)": "حالة الضمان - الأعمال (%)",
  "Region Wise - RTAT (Avg)": "متوسط زمن الاستجابة حسب المنطقة",
  "Region Wise - RTAT (Avg %)": "متوسط زمن الاستجابة حسب المنطقة (%)",
  "Region Wise - Jobs Count": "عدد الأعمال حسب المنطقة",
  "Region Wise - Jobs (%)": "الأعمال حسب المنطقة (%)",
  "Job Cards - Month Wise": "بطاقات العمل حسب الشهر",
  "Job Cards - Warranty Status Wise (%)": "بطاقات العمل حسب حالة الضمان (%)",
  "Job Cards - Default Work Centre Wise": "بطاقات العمل حسب مركز العمل الافتراضي",
  "Job Cards - Status Wise (Closed & Cancelled)": "بطاقات العمل حسب الحالة (مغلقة وملغاة)",
  "Job Cards - Status Wise (Except Closed & Cancelled)": "بطاقات العمل حسب الحالة (باستثناء المغلقة والملغاة)",
  "Job Cards - Warranty Wise (%)": "بطاقات العمل حسب الضمان (%)",
  "Jobs Count - Overall": "إجمالي عدد الأعمال",
  "Job Cards - Overall Closed": "إجمالي بطاقات العمل المغلقة",
  "Job Cards - Overall Cancelled": "إجمالي بطاقات العمل الملغاة",
  "Job Cards - Overall Not Closed": "إجمالي بطاقات العمل غير المغلقة",
  "Total Service Revenue - Month Wise": "إجمالي إيرادات الخدمة حسب الشهر",
  "Total Service Revenue - Month Wise (%)": "إجمالي إيرادات الخدمة حسب الشهر (%)",
  "Total Service Revenue - Region Wise": "إجمالي إيرادات الخدمة حسب المنطقة",
  "Total Service Revenue - Region Wise (%)": "إجمالي إيرادات الخدمة حسب المنطقة (%)",
  "Labour Revenue - Region Wise": "إيرادات العمالة حسب المنطقة",
  "Labour Revenue - Region Wise (%)": "إيرادات العمالة حسب المنطقة (%)",
  "Spare Parts Warranty Revenue - Region Wise": "إيرادات ضمان قطع الغيار حسب المنطقة",
  "Spare Parts Warranty Revenue - Region Wise (%)": "إيرادات ضمان قطع الغيار حسب المنطقة (%)",
  "Spare Parts Revenue - Region Wise": "إيرادات قطع الغيار حسب المنطقة",
  "Spare Parts Revenue - Region Wise (%)": "إيرادات قطع الغيار حسب المنطقة (%)",
  "Total Job Cards - Month wise": "إجمالي بطاقات العمل حسب الشهر",
  "Total Job Cards - User wise": "إجمالي بطاقات العمل حسب المستخدم",
  "Total Job Cards - Scheduled": "إجمالي بطاقات العمل المجدولة",
  "Total Job Cards - Closed": "إجمالي بطاقات العمل المغلقة",
  "Total Scheduled Job Cards - Month wise": "إجمالي بطاقات العمل المجدولة حسب الشهر",
  "Total Closed Job Cards - Month wise": "إجمالي بطاقات العمل المغلقة حسب الشهر",
  "Job Cards - Users wise": "بطاقات العمل حسب المستخدم",
  "Cst Need Quote": "العميل بحاجة إلى عرض سعر",
  "On Hold - SP Req": "معلّق - بانتظار قطع الغيار",
  "Job Card - Status wise Analysis": "تحليل بطاقة العمل حسب الحالة",
  "Job Card - User wise Analysis": "تحليل بطاقة العمل حسب المستخدم",
  "Total Spare Part Requests": "إجمالي طلبات قطع الغيار",
  "Average Waiting Period: On Hold to Parts Ready": "متوسط فترة الانتظار: من التعليق إلى جاهزية قطع الغيار",
  "Average Waiting Period: Parts Ready to Hand Over": "متوسط فترة الانتظار: من جاهزية قطع الغيار إلى التسليم",
  "Average Time: Customer Quotation Request to Parts Added & Service Charge Request":
    "متوسط الوقت: من طلب عرض السعر إلى إضافة القطع وطلب رسوم الخدمة",
  "My Spare Part Requests": "طلبات قطع الغيار الخاصة بي",
  "Scheduled": "مجدول",
  "Parts Ready & Rescheduled": "قطع الغيار جاهزة وأُعيدت جدولتها",
  "On hold": "معلّق",
  "Technician Closed Job Cards": "بطاقات العمل المغلقة حسب الفني",
  "Technician Jobs - Average RTAT": "أعمال الفنيين - متوسط زمن الاستجابة",
  "Technician Utilization": "نسبة استغلال الفني",
  "Technician Labor Hours": "ساعات عمل الفنيين",
  "Technician Travel Hours": "ساعات تنقل الفنيين",
  "Scheduling Performance": "أداء الجدولة",
  "Job Closing Performance": "أداء إغلاق الأعمال",
  "Total Closed Job Cards": "إجمالي بطاقات العمل المغلقة",
  "Employee Performance Analysis - Actual Hours": "تحليل أداء الموظف - الساعات الفعلية",
  "Employee Performance Analysis - Estimated vs Actual Hours": "تحليل أداء الموظف - الساعات المقدرة مقابل الفعلية",
  "New Tasks": "مهام جديدة",
  "Tasks - Month wise": "المهام حسب الشهر",
  "Scheduled Tasks": "مهام مجدولة",
  "Closed Tasks": "مهام مغلقة",
  "Tasks - User Role wise": "المهام حسب دور المستخدم",
  "On Hold - SP Req Tasks": "مهام معلّقة - بانتظار قطع الغيار",
  "Customer Need Quote Tasks": "مهام العميل بحاجة إلى عرض سعر",
  "My Closed Job Cards": "بطاقات العمل المغلقة الخاصة بي",
  "My Jobs - Average RTAT": "أعمالي - متوسط زمن الاستجابة",
  "My Utilization": "نسبة استغلالي",
  "My Labor Hours": "ساعات عملي",
  "My Scheduling Performance": "أداء الجدولة الخاص بي",
  "My Job Closing Performance": "أداء إغلاق الأعمال الخاص بي",
  "Req. Revisit Tasks": "مهام تحتاج زيارة متابعة",
  "Need Reschedule Tasks": "مهام بحاجة لإعادة الجدولة",
  "Parts Ready & Reschedule Tasks": "مهام قطع الغيار جاهزة وإعادة الجدولة",
  "Rescheduled Tasks": "مهام أُعيدت جدولتها",
  // series labels (dual-measure bar)
  "Estimated Hours": "الساعات المقدرة",
  "Actual Hours": "الساعات الفعلية",
});

// Same 7-option vocabulary/order/date-math as service_main.py's
// DATE_FILTER_LABELS — every board's filter bar, default "This Month".
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

// Odoo's action manager destroys and rebuilds this component on every
// navigation away and back (it's not kept alive in the DOM), so any
// filter choice held only in this.state is lost the moment the user
// visits another page and returns — reported as "period resets to This
// Month". Persist the last-picked filters per board in sessionStorage
// (survives navigation within the tab/session, not meant to leak across
// browser sessions like localStorage would) and restore them on setup.
function filterStorageKey(boardKey) {
  return `pbi_service_dashboard_filters_${boardKey}`;
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

export class PbiServiceDashboard extends Component {
  static template = "pbi_dashboards.service_dashboard";
  static props = ["*"];
  // Set per-registration below — which board key (service_config.py
  // BOARDS entry) this instance of the shared component renders.
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
      // Per-chart INDEPENDENT drill state, keyed by item.key — the key
      // departure from Sales Analysis (KPI)'s single page-global
      // drillPath. Clicking one chart never touches another chart's
      // state or triggers a full-board reload.
      charts: {},
      // Period filter — always present. dateFilter drives the dropdown;
      // customStart/customEnd only matter when dateFilter === 'l_custom'.
      // Restored from sessionStorage if the user picked something on a
      // previous visit this session (see filterStorageKey above).
      dateFilter: stored.dateFilter || DEFAULT_DATE_FILTER,
      customStart: stored.customStart || '', customEnd: stored.customEnd || '',
      // Region filter — only rendered when regionFilterable is true
      // (server tells us per-board: CRD/Parts/Technician/Sales & Cost
      // Analysis, the 4 boards with a "Regions" custom filter on the
      // source dashboard). region: 'all' means no restriction.
      regionFilterable: false, regionOptions: [], region: stored.region || 'all', scopeInfo: '',
    });

    this.dateFilterOptions = DATE_FILTER_OPTIONS;

    this.rootRef = useRef('root');
    this.tooltipRef = useRef('tooltip');

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

  get isDebugMode() {
    return Boolean(window.odoo && window.odoo.debug);
  }

  onInfoEnter(ev, infoText) { showTip(ev, infoText, true); }
  onInfoLeave() { hideTip(); }

  // Current filter selections, included on every board/chart RPC so a
  // drill-down stays scoped to whatever period/region is on screen.
  filterParams() {
    return {
      dateFilter: this.state.dateFilter,
      customStart: this.state.customStart,
      customEnd: this.state.customEnd,
      region: this.state.region,
    };
  }

  async load() {
    // A custom range with only one endpoint picked isn't submittable yet —
    // wait for both before hitting the server (avoids a wasted request
    // that would just fall back to This Month).
    if (this.state.dateFilter === 'l_custom' && (!this.state.customStart || !this.state.customEnd)) {
      return;
    }
    this.state.loading = true;
    this.state.error = '';
    try {
      const res = await this.rpc('/pbi_dashboards/service/board', { board: this.boardKey, ...this.filterParams() });
      if (res.error) { this.state.error = res.error; return; }
      this.state.title = t(res.title);
      this.state.scopeInfo = res.scopeInfo || '';
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
    const valueFmt = valueFormatter(item.valueFormat);
    el.innerHTML = kpiTileHtml(item, idx % 6, valueFmt);
    attachValueTooltips(el, '.pbi-kpi[data-tip]');
    el.querySelectorAll('.info-icon[data-info]').forEach(icon => {
      icon.addEventListener('mouseenter', ev => this.onInfoEnter(ev, icon.getAttribute('data-info')));
      icon.addEventListener('mouseleave', () => this.onInfoLeave());
    });
  }

  // Renders whatever this ONE chart's current drill state holds — either
  // the breakdown at its current level (bar/pie) or nothing further once
  // terminal (a native Odoo list/form was already opened, see
  // onChartClick below).
  renderChart(key) {
    const item = this.state.items.find(i => i.key === key);
    const chart = this.state.charts[key];
    const el = this.itemContainer(key);
    if (!el || !item || !chart) return;
    const breakdown = chart.data.breakdown || [];
    const onClick = (code, label) => this.onChartClick(key, code, label);
    const valueFmt = valueFormatter(chart.data.valueFormat);
    if (item.type === 'pie') {
      donutChart(el, breakdown.map(d => ({ code: d.code, label: d.label, value: d.value })), PALETTE, onClick, valueFmt);
    } else if (chart.data.seriesLabels) {
      // Dual-measure bar item (e.g. Estimated vs Actual Hours) — same
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
  // service_config.py ChartItemConfig.drill / service_sql.py
  // run_breakdown). Once the chain is exhausted, the server returns a
  // terminal domain and this opens a NATIVE Odoo list+form (no custom
  // list UI needed — row-click on Odoo's own list view opens the real
  // project.task/machine.repair.support form for free).
  async onChartClick(key, code, label) {
    const chart = this.state.charts[key];
    const newPath = [...chart.drillPath, { code, label }];
    try {
      const res = await this.rpc('/pbi_dashboards/service/chart', {
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
      const res = await this.rpc('/pbi_dashboards/service/chart', {
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

for (const key of BOARD_KEYS) {
  class Bound extends PbiServiceDashboard {}
  Bound.boardKey = key;
  registry.category("actions").add(`pbi_dashboards.service_dashboard_${key}`, Bound);
}
