/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
  fmt, fmtHours, fmtM, fmtPctPrecise, groupedBarChart, donutChart, kpiTileHtml, attachValueTooltips,
  setTooltipEl, clearTooltipEl, moveTip, showTip, hideTip,
  PALETTE,
} from "@pbi_dashboards/js/pbi_chart_lib";

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
import { t, tDate, addLabels, isArabicUI } from "@pbi_dashboards/js/pbi_i18n";

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
  // Formula & Details modal — the record-level audit behind a chart.
  // The formula text, term definitions and column labels themselves come
  // from the server (service_config.py's DetailConfig) and are translated
  // through the same t() call, so adding a formula there needs its strings
  // added here and nowhere else.
  "Formula & Details": "المعادلة والتفاصيل",
  "View the formula and the records behind this chart": "عرض المعادلة والسجلات خلف هذا الرسم البياني",
  "Calculation Breakdown": "تفاصيل الحساب والمعادلة",
  "Formula Logic": "منطق المعادلة",
  "Scope": "النطاق",
  "Unit": "الوحدة",
  "Total Job Cards": "إجمالي بطاقات العمل",
  "Records": "السجلات",
  "Job Cards": "بطاقات العمل",
  "Counted": "المحتسبة",
  "Not counted (no value yet)": "غير محتسبة (لا توجد قيمة بعد)",
  "Total": "الإجمالي",
  "Average": "المتوسط",
  "Divisor": "المقسوم عليه",
  "Utilization": "نسبة الاستغلال",
  "Search records, name, work center, status...": "البحث في السجلات، الاسم، مركز العمل، الحالة...",
  "All": "الكل",
  "Download Excel": "تحميل ملف إكسل",
  "Download the table below as an Excel (.xlsx) file": "تحميل الجدول أدناه كملف إكسل (.xlsx)",
  "Show definitions & scope": "عرض التعريفات والنطاق",
  "Hide definitions & scope": "إخفاء التعريفات والنطاق",
  "Loading details...": "جاري تحميل التفاصيل...",
  "No records found for the selected period / criteria.": "لم يتم العثور على سجلات للفترة أو المعايير المحددة.",
  "Job Card #": "رقم بطاقة العمل",
  "Number of New Jobs": "عدد الأعمال الجديدة",
  "Technician": "الفني",
  "Coordinator": "المنسق",
  "Spare Parts Coordinator": "منسق قطع الغيار",
  "Work Center": "مركز العمل",
  "Region": "المنطقة",
  "Status": "الحالة",
  "Open Job Card": "فتح بطاقة العمل",
  "This record has no completed interval yet, so it is listed but not counted in the average.":
    "لم تكتمل الفترة الزمنية لهذا السجل بعد، لذا يظهر في القائمة دون احتسابه في المتوسط.",
  "Showing": "عرض",
  "of": "من",
  "records": "سجلات",
  "Close": "إغلاق",
  // Franchise filter (filter bar) + the modal's multi-select entity picker.
  // "Franchise" itself is already in pbi_i18n.js's shared chrome set (the
  // Sales Study board's own filter bar uses it) — not repeated here, so
  // both boards keep saying the same word.
  "All Franchises": "كل الامتيازات",
  "Search franchise...": "ابحث عن امتياز...",
  "No franchise matches": "لا يوجد امتياز مطابق",
  "Search": "بحث",
  "selected": "محددة",
  "Select all": "تحديد الكل",
  "Clear": "مسح",
  "No match": "لا توجد نتائج",
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

function emptyDetailModal() {
  return {
    isOpen: false,
    loading: false,
    error: '',
    itemKey: '',
    title: '',
    formula: null,       // {expression, terms:[{label, definition}], scope, unit}
    summary: null,       // {agg, entity_label, value_label, entities:[...], ...}
    columns: [],         // [{key, label, kind}] — the formula's own inputs
    valueColumn: null,   // {label, kind, shown}
    records: [],
    // Multi-select: an EMPTY list means "every entity", which is what the
    // modal opens on. Ids are kept as given by the payload (numbers), so
    // the row filter can compare them without coercing on every record.
    selectedEntities: [],
    entityMenuOpen: false,
    entitySearch: '',
    // The term definitions and scope start open on every chart — a reader
    // checks what a figure means before reading the rows. Deliberately not
    // remembered: the toggle folds them for the modal at hand, and the next
    // one opens expanded again.
    formulaOpen: true,
    searchQuery: '',
    sortBy: 'value',
    sortAsc: false,
  };
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
      // Franchise (brand: Midea / Beko / Candy / ...) filter — offered on
      // EVERY board, unlike region: the franchise lives on the job card
      // itself, so there is no board it cannot narrow. Rendered as a
      // type-to-search dropdown rather than a plain <select> because the
      // list runs to dozens of brands.
      franchiseOptions: [], franchise: stored.franchise || 'all',
      franchiseMenuOpen: false, franchiseSearch: '',
      // "Formula & Details" modal — the record-level audit behind one
      // chart's bars. Every field below is filled from the server payload
      // (columns included), so the same modal serves every chart that
      // declares a DetailConfig in service_config.py.
      detailModal: emptyDetailModal(),
    });

    this.dateFilterOptions = DATE_FILTER_OPTIONS;

    this.rootRef = useRef('root');
    this.tooltipRef = useRef('tooltip');

    onPatched(() => this.renderAll());

    this._onMouseMove = evt => moveTip(evt);
    // Both pickers are open panels rather than native <select>s, so
    // nothing closes them for free — a click anywhere outside the panel
    // that owns them has to.
    this._onDocClick = evt => {
      if (!evt.target.closest || !evt.target.closest('.pbi-ms')) {
        this.closeAllPickers();
      }
    };
    onMounted(() => {
      setTooltipEl(this.tooltipRef.el);
      document.addEventListener('mousemove', this._onMouseMove);
      document.addEventListener('click', this._onDocClick, true);
      this.load();
    });
    onWillUnmount(() => {
      document.removeEventListener('mousemove', this._onMouseMove);
      document.removeEventListener('click', this._onDocClick, true);
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
      franchise: this.state.franchise,
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
      this.state.franchiseOptions = res.franchiseOptions || [];
      // A franchise that no longer exists (renamed/archived since the
      // choice was stored) would otherwise silently empty every chart.
      if (this.state.franchise !== 'all' && !this.state.franchiseOptions.includes(this.state.franchise)) {
        this.state.franchise = 'all';
        this.persistFilters();
      }
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
      franchise: this.state.franchise,
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

  // ---------------------------------------------------------------
  // Franchise picker (filter bar) — type-to-search over the brands the
  // server sent, one choice at a time (the scope compiler ANDs its
  // clauses, so two franchises would mean "a card that is both").
  // ---------------------------------------------------------------
  get franchiseLabel() {
    return this.state.franchise === 'all' ? t('All Franchises') : this.state.franchise;
  }

  get franchiseMatches() {
    const q = (this.state.franchiseSearch || '').toLowerCase().trim();
    const opts = this.state.franchiseOptions || [];
    return q ? opts.filter(o => String(o).toLowerCase().includes(q)) : opts;
  }

  closeAllPickers() {
    if (this.state.franchiseMenuOpen) { this.state.franchiseMenuOpen = false; }
    if (this.state.detailModal && this.state.detailModal.entityMenuOpen) {
      this.state.detailModal.entityMenuOpen = false;
    }
  }

  toggleFranchiseMenu() {
    const open = !this.state.franchiseMenuOpen;
    this.closeAllPickers();
    this.state.franchiseMenuOpen = open;
    if (open) { this.state.franchiseSearch = ''; }
  }

  updateFranchiseSearch(value) {
    this.state.franchiseSearch = value;
  }

  selectFranchise(value) {
    this.state.franchiseMenuOpen = false;
    if (value === this.state.franchise) { return; }
    this.state.franchise = value;
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
          views: [[res.listViewId || false, 'list'], [false, 'form']],
          domain: res.domain,
          name: res.name,
          target: 'current',
          // Read by our own project.task search_fetch override: machine_repair_management
          // injects hidden work_center_id/amc_project_id clauses into every list read for
          // back-office+technical-allocation users, which emptied lists the chart had
          // counted. The flag scopes the bypass to this drill-through alone.
          context: { pbi_dashboard_drilldown: true },
          // project.task's list view carries sample="1", so when a drill
          // matches no records Odoo fills the list with fabricated demo rows
          // (REF0001…, lorem ipsum) instead of an empty state — indistinguishable
          // from real data at a glance. A drill-through that legitimately finds
          // nothing has to say nothing.
          useSampleModel: false,
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

  // ---------------------------------------------------------------
  // "Formula & Details" modal
  // ---------------------------------------------------------------
  get detailSearchableKeys() {
    // Mirrors service_main.py's _searchable_cols, so the on-screen search
    // and the one replayed for a download narrow to the same rows.
    const cols = (this.state.detailModal.columns || []).map(c => c.key);
    return ['name', 'entity_name', 'work_center', 'region', 'status', 'value_formatted', ...cols];
  }

  get filteredDetailRecords() {
    const modal = this.state.detailModal;
    if (!modal || !modal.records) return [];
    let list = [...modal.records];

    // No selection at all means every entity — the same reading as the
    // old "All" option, without a magic value in the list.
    if (modal.selectedEntities && modal.selectedEntities.length) {
      const picked = new Set(modal.selectedEntities.map(Number));
      list = list.filter(r => picked.has(Number(r.entity_id)));
    }

    if (modal.searchQuery) {
      const q = modal.searchQuery.toLowerCase().trim();
      const keys = this.detailSearchableKeys;
      list = list.filter(r => keys.some(k => String(r[k] ?? '').toLowerCase().includes(q)));
    }

    if (modal.sortBy) {
      const field = modal.sortBy;
      const asc = modal.sortAsc;
      const isBlank = v => v === undefined || v === null;
      list.sort((a, b) => {
        // A record with no value sinks to the bottom in BOTH directions —
        // reversing it into first place would bury the rows the reader
        // opened the table to see. service_main.py's _apply_view_filters
        // does the same, so a download matches what is on screen.
        const blankA = isBlank(a[field]);
        const blankB = isBlank(b[field]);
        if (blankA || blankB) return blankA && blankB ? 0 : (blankA ? 1 : -1);
        let valA = a[field];
        let valB = b[field];
        if (typeof valA === 'number' && typeof valB === 'number') {
          return asc ? valA - valB : valB - valA;
        }
        valA = String(valA).toLowerCase();
        valB = String(valB).toLowerCase();
        if (valA < valB) return asc ? -1 : 1;
        if (valA > valB) return asc ? 1 : -1;
        return 0;
      });
    }

    return list;
  }

  // Totals over the rows on screen, rolled up the same way the chart
  // rolls them up (service_main.py's _view_totals is the server twin).
  get filteredDetailTotals() {
    const modal = this.state.detailModal;
    const summary = modal.summary || {};
    const kind = summary.value_kind || 'hours';
    const agg = summary.agg || 'sum';
    const list = this.filteredDetailRecords;
    // A record whose interval never completed is listed but not counted —
    // that is exactly why the row count and the denominator can differ.
    const counted = list.filter(r => r.counted && r.value !== null && r.value !== undefined);
    const total = counted.reduce((acc, r) => acc + Number(r.value || 0), 0);
    const avg = counted.length ? total / counted.length : 0;
    const fmt = v => (kind === 'hours' ? fmtHours(v) : v.toFixed(2));

    const out = {
      agg,
      count: list.length,
      counted: agg === 'count' ? list.length : counted.length,
      total,
      totalFormatted: fmt(total),
      avg,
      avgFormatted: fmt(avg),
    };
    if (agg === 'utilization') {
      const divisor = Number(summary.divisor || 0);
      out.divisor = divisor;
      out.divisorLabel = summary.divisor_label || '';
      out.utilizationPct = divisor ? (total / divisor) * 100 : 0;
      out.utilizationFormatted = out.utilizationPct.toFixed(2) + '%';
    }
    return out;
  }

  // Sums for the columns whose DetailColumn declares total=true — the
  // scheduling formula's "Number of New Jobs" divisor is the one that does.
  // Over the rows ON SCREEN, like every other figure in this modal, so
  // narrowing to one coordinator shows the divisor that coordinator's own
  // bar was computed with.
  get detailColumnTotals() {
    const modal = this.state.detailModal;
    const cols = (modal && modal.columns) || [];
    const totals = {};
    if (!cols.some(c => c.total)) { return totals; }
    const rows = this.filteredDetailRecords;
    for (const col of cols) {
      if (!col.total) { continue; }
      // *_raw is the unformatted value run_chart_detail sends alongside
      // each cell; the displayed one is a string and would concatenate.
      totals[col.key] = rows.reduce((acc, r) => acc + Number(r[col.key + '_raw'] || 0), 0);
    }
    return totals;
  }

  getSortIcon(col) {
    const modal = this.state.detailModal;
    if (!modal || modal.sortBy !== col) return 'fa fa-sort text-muted ms-1';
    return modal.sortAsc ? 'fa fa-sort-amount-asc text-primary ms-1' : 'fa fa-sort-amount-desc text-primary ms-1';
  }

  async openDetailModal(itemKey) {
    const item = this.state.items.find(i => i.key === itemKey);
    const modal = emptyDetailModal();
    modal.isOpen = true;
    modal.loading = true;
    modal.itemKey = itemKey;
    modal.title = item ? item.name : '';
    this.state.detailModal = modal;
    try {
      const res = await this.rpc('/pbi_dashboards/service/chart', {
        board: this.boardKey,
        item: itemKey,
        details: true,
        ...this.filterParams(),
      });
      const m = this.state.detailModal;
      if (m.itemKey !== itemKey) return;  // user opened another chart meanwhile
      if (res.error) {
        m.error = res.error;
        m.loading = false;
        return;
      }
      m.formula = res.formula;
      m.summary = res.summary;
      m.columns = res.columns || [];
      m.valueColumn = res.valueColumn || { shown: false };
      m.records = res.records || [];
      // A count chart has no per-record value to sort on.
      m.sortBy = m.valueColumn.shown ? 'value' : 'entity_name';
      m.sortAsc = !m.valueColumn.shown;
      m.loading = false;
    } catch (e) {
      this.state.detailModal.error = 'Failed to load details: ' + e.message;
      this.state.detailModal.loading = false;
    }
  }

  closeDetailModal() {
    if (this.state.detailModal) {
      this.state.detailModal.isOpen = false;
    }
  }

  toggleDetailFormula() {
    const modal = this.state.detailModal;
    if (modal) modal.formulaOpen = !modal.formulaOpen;
  }

  updateDetailSearch(val) {
    if (this.state.detailModal) {
      this.state.detailModal.searchQuery = val;
    }
  }

  // ---------------------------------------------------------------
  // Entity picker (Formula & Details modal) — multi-select. Filtering
  // stays in the browser (the payload already carries every record), and
  // the same id list is replayed server-side for the download so the file
  // matches the table.
  // ---------------------------------------------------------------
  get detailEntities() {
    const modal = this.state.detailModal;
    return (modal && modal.summary && modal.summary.entities) || [];
  }

  get detailEntityMatches() {
    const q = ((this.state.detailModal && this.state.detailModal.entitySearch) || '').toLowerCase().trim();
    const list = this.detailEntities;
    return q ? list.filter(e => String(e.name || '').toLowerCase().includes(q)) : list;
  }

  get detailEntityLabel() {
    const modal = this.state.detailModal;
    const picked = (modal && modal.selectedEntities) || [];
    const entityLabel = t((modal && modal.summary && modal.summary.entity_label) || 'Entity');
    if (!picked.length) { return `${t('All')} — ${entityLabel}`; }
    if (picked.length === 1) {
      const one = this.detailEntities.find(e => Number(e.id) === Number(picked[0]));
      return one ? one.name : entityLabel;
    }
    return `${picked.length} ${entityLabel} ${t('selected')}`;
  }

  isDetailEntitySelected(id) {
    const picked = (this.state.detailModal && this.state.detailModal.selectedEntities) || [];
    return picked.some(p => Number(p) === Number(id));
  }

  toggleDetailEntityMenu() {
    const modal = this.state.detailModal;
    if (!modal) { return; }
    const open = !modal.entityMenuOpen;
    this.closeAllPickers();
    modal.entityMenuOpen = open;
    if (open) { modal.entitySearch = ''; }
  }

  updateDetailEntitySearch(val) {
    if (this.state.detailModal) {
      this.state.detailModal.entitySearch = val;
    }
  }

  toggleDetailEntity(id) {
    const modal = this.state.detailModal;
    if (!modal) { return; }
    const picked = modal.selectedEntities.filter(p => Number(p) !== Number(id));
    if (picked.length === modal.selectedEntities.length) {
      picked.push(Number(id));
    }
    modal.selectedEntities = picked;
  }

  // "Select all" over what the picker's own search is showing, so it
  // means "all of these" rather than "all of them" when a query is typed.
  selectAllDetailEntities() {
    const modal = this.state.detailModal;
    if (!modal) { return; }
    modal.selectedEntities = this.detailEntityMatches.map(e => Number(e.id));
  }

  clearDetailEntities() {
    if (this.state.detailModal) {
      this.state.detailModal.selectedEntities = [];
    }
  }

  sortDetail(col) {
    const modal = this.state.detailModal;
    if (!modal) return;
    if (modal.sortBy === col) {
      modal.sortAsc = !modal.sortAsc;
    } else {
      modal.sortBy = col;
      // text columns read best A-Z first; a value column reads best
      // largest-first, which is what the chart's own bars show.
      modal.sortAsc = col !== 'value';
    }
  }

  async openTaskForm(taskId) {
    if (!taskId) return;
    await this.actionService.doAction({
      type: 'ir.actions.act_window',
      res_model: 'project.task',
      res_id: taskId,
      views: [[false, 'form']],
      target: 'current',
    });
  }

  // The download is a separate request, so the server re-runs the query
  // and has to be told about the narrowing the user did on screen —
  // otherwise the file comes back with rows the table isn't showing.
  // service_main.py's _apply_view_filters replays exactly these.
  detailExportUrl(format) {
    const p = this.filterParams();
    const modal = this.state.detailModal || {};
    const query = new URLSearchParams({
      board: this.boardKey,
      item: modal.itemKey || '',
      dateFilter: p.dateFilter || '',
      customStart: p.customStart || '',
      customEnd: p.customEnd || '',
      region: p.region || '',
      franchise: p.franchise || '',
      // Empty string = no entity restriction, matching the table on screen.
      entityIds: (modal.selectedEntities || []).join(','),
      search: modal.searchQuery || '',
      sortBy: modal.sortBy || '',
      sortAsc: modal.sortAsc ? '1' : '0',
    });
    return `/pbi_dashboards/service/detail_export_${format}?${query.toString()}`;
  }

  downloadDetailExcel() {
    window.location.href = this.detailExportUrl('xlsx');
  }

}


for (const key of BOARD_KEYS) {
  class Bound extends PbiServiceDashboard {}
  Bound.boardKey = key;
  registry.category("actions").add(`pbi_dashboards.service_dashboard_${key}`, Bound);
}
