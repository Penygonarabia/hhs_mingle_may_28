/** @odoo-module **/

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { t, tDate, addLabels, isArabicUI } from "@pbi_dashboards/js/pbi_i18n";
import { fmt, fmtCompact, fmtPct, pct } from "@pbi_dashboards/js/pbi_chart_lib";

// "Sales Data Study" — a Power BI style matrix with January to December across
// the top and Qty and Value under each month, over whichever drill chain the
// server declares. Rows expand IN PLACE, so an ancestor and its descendants are
// on screen together — the point of a matrix over a drill-down chart.
//
// TWO boards run on this one component: the six-level bidata chain (Customer
// Type > Customer Sub-Type > Region > Customer > Product Group > Product
// Sub-Group, controllers/sales_study_main.py) and the ten-level salesman chain
// (sales_study_sman_dashboard.js, controllers/sales_study_sman_main.py). They
// carry the same menu name on purpose, so keeping them one component is what
// stops two boards a user reads as the same thing from drifting apart. Nothing
// here knows a level name: the chain arrives as `levels` in the meta reply and
// the slicers are built from it. A subclass supplies its route, its subtitle
// and which of the board-specific filters it shows.
//
// The tree is fetched lazily: opening a row asks the server for that row's
// children only (controllers/sales_study_main.py, one GROUP BY per node, the
// twelve month pairs riding along on the same scan), and everything already
// fetched is kept, so collapsing and re-opening a row is free. Nothing about
// the hierarchy is held server-side between requests — the client sends the
// path of {level, code} ancestors it wants children for.
//
// BOTH the thead and the tbody are drawn as HTML strings from here rather than
// by OWL. The tbody because a six-level tree runs to thousands of rows and one
// innerHTML write plus one delegated click listener beats a t-foreach with
// per-row handlers; the thead because its shape depends on the measure toggle,
// and mixing an OWL-owned header with a hand-written body means the header can
// be rebuilt by a patch AFTER this file has filled in the grand-total row,
// silently blanking it. Both are t-ref'd empty elements OWL never touches.
addLabels({
  "Sales Data Study": "دراسة بيانات المبيعات",
  "Sales Dashboards - Temp": "لوحات المبيعات - مؤقت",
  "Qty and Value by month across all six levels": "الكمية والقيمة شهريًا عبر المستويات الستة",
  "Filters & Levels": "الفلاتر والمستويات",
  "Filters": "الفلاتر",
  "Levels": "المستويات",
  "Customer Group": "مجموعة العملاء",
  "Customer Type": "نوع العميل",
  "Customer Sub-Type": "النوع الفرعي للعميل",
  "Customer": "العميل",
  "Product Group": "مجموعة المنتجات",
  "Product Sub-Group": "المجموعة الفرعية للمنتجات",
  "Period": "الفترة",
  "Selected month": "الشهر المحدد",
  "Year to date": "منذ بداية السنة",
  "Full year": "السنة كاملة",
  "Group by": "تجميع حسب",
  "Sales Type Group": "مجموعة نوع البيع",
  "Partner Classification": "تصنيف العميل",
  "Region": "المنطقة",
  "City": "المدينة",
  "Salesman": "مندوب المبيعات",
  "Customer": "العميل",
  "Main Category": "الفئة الرئيسية",
  "Sub Category": "الفئة الفرعية",
  "Pack Size": "حجم العبوة",
  "Product Classification": "تصنيف المنتج",
  "Sort rows by": "ترتيب الصفوف حسب",
  "Value": "القيمة",
  "Qty": "الكمية",
  "Both": "كليهما",
  "Name": "الاسم",
  "Show": "عرض",
  "Total": "الإجمالي",
  "Grand Total": "الإجمالي الكلي",
  "Expand next level": "توسيع المستوى التالي",
  "Collapse all": "طي الكل",
  "Export CSV": "تصدير CSV",
  "Search rows": "بحث في الصفوف",
  "Row hierarchy": "تسلسل الصفوف",
  "rows shown": "صف معروض",
  "No rows for this selection.": "لا توجد صفوف لهذا الاختيار.",
  "No rows match the search.": "لا توجد صفوف مطابقة للبحث.",
  "Others": "أخرى",
  "Data": "البيانات",
  "Sales": "المبيعات",
  "Budget": "الميزانية",
  "Sales & Budget": "المبيعات والميزانية",
  "Bud Qty": "كمية الميزانية",
  "Bud Value": "قيمة الميزانية",
  "No target is captured at this level.": "لا يوجد هدف مسجل في هذا المستوى.",
  "No budget has been entered for this year.": "لم يتم إدخال ميزانية لهذه السنة.",
  "more rows": "صفوف إضافية",
  "Everything visible is already expanded.": "كل ما هو ظاهر تم توسيعه بالفعل.",
  "Failed to load": "فشل التحميل",
  "January": "يناير", "February": "فبراير", "March": "مارس", "April": "أبريل",
  "May": "مايو", "June": "يونيو", "July": "يوليو", "August": "أغسطس",
  "September": "سبتمبر", "October": "أكتوبر", "November": "نوفمبر", "December": "ديسمبر",
  "Jan": "ينا", "Feb": "فبر", "Mar": "مار", "Apr": "أبر", "Jun": "يون",
  "Jul": "يول", "Aug": "أغس", "Sep": "سبت", "Oct": "أكت", "Nov": "نوف", "Dec": "ديس",
});

const FRANCHISE_OPTIONS = [
  { v: 'all', l: 'All' }, { v: 'Midea', l: 'Midea' }, { v: 'BEKO', l: 'BEKO' }, { v: 'CANDY', l: 'CANDY' },
];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"];
const MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_OPTIONS = MONTH_NAMES.map((l, i) => ({ v: i + 1, l }));
const SCOPE_OPTIONS = [
  { v: 'year', l: 'Full year' }, { v: 'ytd', l: 'Year to date' }, { v: 'mtd', l: 'Selected month' },
];
const SORT_OPTIONS = [
  { v: 'value', l: 'Value' }, { v: 'qty', l: 'Qty' }, { v: 'label', l: 'Name' },
];
const GROUP_BY_OPTIONS = [
  { v: 'salesTypeGroup', l: 'Sales Type Group' },
  { v: 'partnerClassification', l: 'Partner Classification' },
  { v: 'reportRegion', l: 'Region' },
  { v: 'city', l: 'City' },
  { v: 'salesman', l: 'Salesman' },
  { v: 'customer', l: 'Customer' },
  { v: 'mainCategory', l: 'Main Category' },
  { v: 'subCategory', l: 'Sub Category' },
  { v: 'productGroup', l: 'Product Group' },
  { v: 'productSubGroup', l: 'Product Sub-Group' },
];
// Which measure the twelve month columns carry. Purely a display switch —
// every response always carries both, so toggling re-draws in place.
const MEASURE_OPTIONS = [
  { v: 'value', l: 'Value' }, { v: 'qty', l: 'Qty' },
];
// Which DATA the twelve month columns carry: the actuals, the target, or both
// side by side. Unlike the measure toggle this is NOT a pure display switch --
// the target is a second set of queries over a second temp table, so the server
// only builds it when a mode other than 'sales' asks for it. That is why
// selectDataset refetches where selectMeasure only redraws.
//
// Offered only by boards whose source HAS a target (showBudget); the bidata
// six-level board has none.
const DATASET_OPTIONS = [
  { v: 'sales', l: 'Sales' }, { v: 'budget', l: 'Budget' }, { v: 'both', l: 'Sales & Budget' },
];
// Ten-level board only: which product-category reading feeds levels 7 and 8.
// The snapshot carries both side by side, so this is a choice of column on the
// server, not a different build of the facts.
const SUB_MODE_OPTIONS = [
  { v: 'regular', l: 'Regular' }, { v: 'manager', l: 'Manager' },
];
// Ten-level board, developer mode only: 'acgroups' is the Midea AC scope the
// board is about, 'all' drops it. The two are not comparable — see SCOPES in
// controllers/sales_sman_main.py — which is why it is not offered normally.
const PRODUCT_SCOPE_OPTIONS = [
  { v: 'acgroups', l: 'AC product groups' }, { v: 'all', l: 'All MDA lines' },
];

// Row keys are the level:code segments of a row's ancestry joined together.
// The separator is the ASCII unit separator so it cannot collide with a
// master-data code the way '|' or '-' could.
const SEP = '\u001f';
const ROOT_KEY = '';

// Server-side ceiling on nodes per request (MAX_NODES_PER_REQUEST in
// sales_study_main.py). Requests are chunked to it rather than being refused.
const CHUNK = 100;

// One colour per level — the matrix's only use of colour, so a row's level is
// readable without counting indents. Literal values rather than the --series-*
// custom properties the chart boards use: those run out at five (and --series-4
// is referenced in places but never defined), while the salesman chain needs
// ten. Same palette as pbi_chart_lib's PALETTE, in the same order.
const DEPTH_COLORS = [
  '#2a78d6', '#1baf7a', '#eda100', '#4a3aa7', '#17a2b8',
  '#e34948', '#8e44ad', '#16a085', '#d35400', '#2c3e50',
];

const esc = s => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// Format helpers: Values in Millions (M) and Quantities in Thousands (K).
// Mouse hover on each cell displays the exact full number via the title attribute.
export const fmtValueM = v => {
  if (v == null) return '–';
  if (v === 0) return '0.0M';
  const m = v / 1e6;
  if (Math.abs(m) < 1 && Math.abs(m) >= 0.005) {
    return m.toFixed(2) + 'M';
  }
  return m.toFixed(1) + 'M';
};

export const fmtQtyK = v => {
  if (v == null) return '–';
  if (v === 0) return '0.0K';
  const k = v / 1e3;
  if (Math.abs(k) < 1 && Math.abs(k) >= 0.05) {
    return k.toFixed(2) + 'K';
  }
  return k.toFixed(1) + 'K';
};

export const formatMeasure = (v, measure = 'value') => {
  return measure === 'qty' ? fmtQtyK(v) : fmtValueM(v);
};

// A month cell that is exactly zero is drawn empty. Across 24 month columns a
// grid of zeros is what hides the shape of the year; blanks let the months a
// row actually sold in stand out.
const monthCellNum = (v, measure = 'value') => (!v ? '' : formatMeasure(v, measure));

// Total cells (row total and grand total)
const totalCellNum = (v, measure = 'value') => (v == null ? '–' : formatMeasure(v, measure));

export class PbiSalesStudyDashboard extends Component {
  static template = "pbi_sales_dashboards.sales_study_dashboard";
  static props = ["*"];

  // ------------------------------------------------------------------
  // board configuration — what the ten-level sibling overrides, and the
  // only thing that differs between the two boards.
  // ------------------------------------------------------------------
  get route() { return '/pbi_dashboards/sales_study/data'; }
  get sourceName() { return 'v_bidata_live'; }
  get subtitleText() { return t('Qty and Value by month across all six levels'); }
  get menuPath() { return t('Sales Dashboards - Temp'); }
  get csvName() { return 'sales_data_study'; }
  get showFranchise() { return true; }
  get showCustomerGroup() { return true; }
  get showSubMode() { return false; }
  get showProductScope() { return false; }
  get showGroupBy() { return true; }
  get groupByOptions() {
    if (this.state.allLevels && this.state.allLevels.length) {
      return this.state.allLevels;
    }
    if (this.state.levels && this.state.levels.length) {
      return this.state.levels;
    }
    return GROUP_BY_OPTIONS;
  }
  // Whether this board's source carries a TARGET at all. False here: the
  // bidata six-level chain has no budget to read. The salesman board overrides
  // it — see sales_study_sman_dashboard.js.
  get showBudget() { return false; }
  get showMonth() { return this.state.periodScope === 'mtd'; }

  /** The board-specific half of every request. The shared half is period,
   *  sort, levelFilters, nodes and meta. */
  extraParams() {
    return {
      franchise: this.state.franchise,
      customerGroup: this.state.customerGroup,
      scope: this.state.periodScope,
    };
  }

  get isDebugMode() {
    return Boolean(window.odoo && window.odoo.debug);
  }

  setup() {
    this.rpc = useService("rpc");
    this.franchiseOptions = FRANCHISE_OPTIONS;
    this.monthOptions = MONTH_OPTIONS;
    this.scopeOptions = SCOPE_OPTIONS;
    this.sortOptions = SORT_OPTIONS;
    this.measureOptions = MEASURE_OPTIONS;
    this.datasetOptions = DATASET_OPTIONS;
    this.subModeOptions = SUB_MODE_OPTIONS;
    this.productScopeOptions = PRODUCT_SCOPE_OPTIONS;
    this.t = t;
    this.isArabicUI = isArabicUI;

    this.state = useState({
      year: null, month: null, franchise: 'Midea', customerGroup: 'all',
      // periodScope is year/ytd/mtd. productScope is the salesman board's
      // separate in-scope-lines whitelist; the six-level board never sends it.
      periodScope: 'year', productScope: 'acgroups', subMode: 'regular',
      sort: 'value', groupBy: 'salesTypeGroup', measure: 'value', search: '',
      // 'sales' | 'budget' | 'both'. Always 'sales' on a board with no target,
      // and it opens there everywhere, so nothing about today's board changes
      // until someone asks for the budget.
      dataset: 'sales',
      // Set from the server's reply: whether a target exists for the year on
      // screen, and which levels will draw blank cells because the capture
      // does not reach them (level -> the reason, in words).
      hasBudget: false, budgetUnsafe: {},
      loading: false, error: '', notice: '',
      yearOptions: [], customerGroupOptions: [{ v: 'all', l: 'All' }],
      // The drill chain, as the server declares it: [{v: level, l: label}].
      // Empty until the first reply, which is what the slicer row is built
      // from — nothing here is hardcoded to a level set.
      levels: [],
      allLevels: [],
      // {level: code} for the slicers, absent meaning All. Sent as
      // levelFilters and applied to every node in the request.
      levelFilters: {},
      levelFilterOptions: {},
      periodLabel: '', total: { qty: 0, value: 0, m: [] },
      rowCount: 0,
      filtersCollapsed: false,
      levelsCollapsed: true,
      toolbarCollapsed: false,
      // THE PART NUMBER. Two fields, not one, and deliberately: `partInput` is
      // what is being typed and `partNo` is what the board is showing. A part
      // filter is a round trip that rebuilds the whole temp table, so it fires
      // on Enter or blur, never per keystroke — unlike `search`, which only
      // re-draws rows already in the browser.
      partInput: '', partNo: '',
      // The server's answer to "where does this part sit": one entry per level,
      // carrying a value where the slice holds one and a count where it holds
      // many. Null when no part is selected.
      part: null,
    });

    // The fetched tree. `nodes[key]` holds one node's children exactly as the
    // server returned them; `nodePaths[key]` the {level, code} chain that
    // fetched them (needed again to re-fetch on a sort change). `expandedSet`
    // is which rows are open — a row can be open with its node still in
    // flight, which is what `pendingKeys` renders as a spinner.
    this.nodes = {};
    this.nodePaths = { [ROOT_KEY]: [] };
    this.expandedSet = new Set();
    this.pendingKeys = new Set();
    // Rebuilt on every render: the flat list of rows actually on screen, and
    // a key -> row lookup for the click handler and the CSV export.
    this.visibleRows = [];
    this.rowIndex = new Map();

    this.headRef = useRef('matrixHead');
    this.bodyRef = useRef('matrixBody');

    onMounted(() => {
      // One delegated listener for the whole matrix: the body is re-rendered
      // wholesale on every change, so per-row listeners would have to be
      // re-attached each time (and leak the old ones in between).
      this.bodyRef.el.addEventListener('click', evt => {
        const tr = evt.target.closest('tr[data-key]');
        if (!tr) return;
        this.toggleRow(tr.getAttribute('data-key'));
      });
      this.load();
    });
  }

  // ------------------------------------------------------------------
  // measure toggle
  // ------------------------------------------------------------------
  get showQty() { return this.state.measure !== 'value'; }
  get showValue() { return this.state.measure !== 'qty'; }
  get measureCount() { return this.state.measure === 'both' ? 2 : 1; }

  // The dataset half of the same idea. `wantsBudget` is what the REQUEST asks
  // for; `showSales`/`showBudgetCols` are what the DRAW puts on screen. They
  // come apart for one render: the moment the toggle flips, the reply carrying
  // the target has not arrived yet.
  // Whether this board offers the Part No box at all. Only a board whose
  // source carries part_no can — see the part section of
  // controllers/sales_study_sman_main.py.
  get showPartFilter() { return false; }
  get hasPart() { return Boolean(this.state.partNo); }

  // A part selected takes the target off the board, because there is none to
  // show: the budget is captured per tuple, not per part. The server refuses it
  // and says why; this keeps the client from asking in the first place, so the
  // request does not pay ~0.4s building a budget temp it will not read.
  get wantsBudget() {
    return this.showBudget && !this.hasPart && this.state.dataset !== 'sales';
  }
  get showSales() { return !this.wantsBudget || this.state.dataset !== 'budget'; }
  get showBudgetCols() { return this.wantsBudget && this.state.hasBudget; }
  get datasetCount() { return (this.showSales ? 1 : 0) + (this.showBudgetCols ? 1 : 0) || 1; }

  /** Cells per month, and per the Total group before its % column. */
  get cellsPerGroup() { return this.measureCount * this.datasetCount; }
  get columnCount() { return 1 + 12 * this.cellsPerGroup + this.cellsPerGroup + 1; }

  /** The (dataset, measure) pairs a group emits, in draw order: sales first,
   *  then budget, qty before value within each. One list, so the header, the
   *  body, the grand total and the CSV cannot disagree about column order. */
  get cellSpec() {
    const out = [];
    for (const src of (this.showSales ? ['s'] : []).concat(this.showBudgetCols ? ['b'] : [])) {
      if (this.showQty) out.push({ src, measure: 'qty' });
      if (this.showValue) out.push({ src, measure: 'value' });
    }
    return out;
  }

  // ------------------------------------------------------------------
  // filters
  // ------------------------------------------------------------------
  selectYear(v) { this.state.year = +v; this.load(); }
  selectMonth(v) { this.state.month = +v; this.load(); }
  selectFranchise(v) { this.state.franchise = v; this.load(); }
  selectCustomerGroup(v) { this.state.customerGroup = v; this.load(); }
  selectScope(v) { this.state.periodScope = v; this.load(); }
  selectSubMode(v) { this.state.subMode = v; this.load(); }
  selectProductScope(v) { this.state.productScope = v; this.load(); }

  // A slicer narrows every node in the tree, including the levels above it, so
  // the whole matrix is refetched rather than filtered in place. The option
  // lists come back with it: each level's list is narrowed by the levels above
  // it, so picking a Customer Type reshapes the Region slicer below.
  selectLevelFilter(level, v) {
    if (this.levelFilterValue(level) === v) return;
    this.state.levelFilters[level] = v;
    this.load();
  }

  clearLevelFilters() {
    if (!this.hasLevelFilters) return;
    this.state.levelFilters = {};
    this.load();
  }

  levelFilterValue(level) { return this.state.levelFilters[level] || 'all'; }

  get hasLevelFilters() {
    return Object.values(this.state.levelFilters).some(v => v && v !== 'all');
  }

  // A sort change re-orders rows the SERVER picked: each node returns its top
  // rows by the chosen measure, so re-sorting in the browser would only
  // shuffle the rows already fetched and quietly keep the previous measure's
  // selection. Re-fetch what is open instead, leaving the tree open.
  async selectSort(v) {
    if (this.state.sort === v) return;
    this.state.sort = v;
    await this.refetchOpen();
  }

  selectGroupBy(v) {
    if (this.state.groupBy === v) return;
    this.state.groupBy = v;
    this.load();
  }

  // Purely a display switch: every response carries both measures, so this
  // only changes which columns are drawn.
  selectMeasure(v) {
    if (this.state.measure === v) return;
    this.state.measure = v;
    this.renderAll();
  }

  // NOT a display switch, unlike the measure toggle: the target is a second
  // set of queries the server only runs when asked, so switching this on has
  // to go back for it. Switching it OFF refetches too — so that a board left
  // on Sales stops paying for a target nobody is looking at.
  async selectDataset(v) {
    if (this.state.dataset === v) return;
    this.state.dataset = v;
    await this.refetchOpen(true);
  }

  onSearch(v) {
    this.state.search = v;
    this.renderMatrix();
  }

  // ------------------------------------------------------------------
  // part number
  //
  // A part narrows the SLICE — every row of the matrix, every slicer list and
  // the grand total — which is a different thing from the search box beside the
  // matrix. Search filters rows already fetched; this one goes back to the
  // server and re-cuts what the board is about.
  // ------------------------------------------------------------------
  onPartInput(v) { this.state.partInput = v; }

  onPartKey(ev) {
    if (ev.key === 'Enter') this.applyPart();
    else if (ev.key === 'Escape') this.clearPart();
  }

  applyPart() {
    // Folded here as well as on the server so the box shows what is actually
    // being asked for, rather than echoing a case the snapshot does not store.
    const v = (this.state.partInput || '').trim().toUpperCase();
    this.state.partInput = v;
    if (v === this.state.partNo) return;
    this.state.partNo = v;
    this.load();
  }

  clearPart() {
    if (!this.state.partNo && !this.state.partInput) return;
    this.state.partInput = '';
    this.state.partNo = '';
    this.state.part = null;
    this.load();
  }

  /** The resolved chain, split the way it actually behaves: the levels that
   *  resolve to one value, and the ones that do not. */
  get partChain() { return (this.state.part && this.state.part.chain) || []; }

  /** A part the AC-groups scope would have dropped. The lookup shows it anyway
   *  — a known part number is not a browse — but the board says so, because
   *  its figures then belong to a wider slice than the unfiltered board's. */
  get partOutOfScope() {
    const p = this.state.part;
    return Boolean(p && p.found && p.inScope === false);
  }

  toggleFilters() { this.state.filtersCollapsed = !this.state.filtersCollapsed; }
  toggleLevels() { this.state.levelsCollapsed = !this.state.levelsCollapsed; }
  toggleToolbar() { this.state.toolbarCollapsed = !this.state.toolbarCollapsed; }

  // ------------------------------------------------------------------
  // fetching
  // ------------------------------------------------------------------
  get period() {
    return (this.state.year && this.state.month)
      ? `${this.state.year}-${String(this.state.month).padStart(2, '0')}` : null;
  }

  async fetchNodes(list, meta = false) {
    const res = await this.rpc(this.route, {
      period: this.period,
      sort: this.state.sort,
      groupBy: this.state.groupBy,
      levelFilters: { ...this.state.levelFilters },
      nodes: list.map(n => ({ key: n.key, path: n.path })),
      meta,
      withBudget: this.wantsBudget,
      partNo: this.showPartFilter ? this.state.partNo : '',
      ...this.extraParams(),
    });
    if (res.error) { this.state.error = res.error; return null; }
    for (const n of list) this.nodePaths[n.key] = n.path;
    Object.assign(this.nodes, res.nodes || {});
    return res;
  }

  // Requests are split to the server's own per-request node ceiling rather
  // than being rejected by it — "expand next level" on a wide branch can ask
  // for more nodes than one request may carry.
  async fetchNodesChunked(list, meta = false) {
    let first = null;
    for (let i = 0; i < list.length; i += CHUNK) {
      const res = await this.fetchNodes(list.slice(i, i + CHUNK), meta && i === 0);
      if (res === null) return null;
      if (first === null) first = res;
    }
    return first;
  }

  async load() {
    this.state.loading = true;
    this.state.error = '';
    this.state.notice = '';
    this.nodes = {};
    this.nodePaths = { [ROOT_KEY]: [] };
    this.expandedSet = new Set();
    this.pendingKeys = new Set();
    try {
      const res = await this.fetchNodes([{ key: ROOT_KEY, path: [] }], true);
      if (!res) return;
      this.state.year = res.period.year;
      this.state.month = res.period.month;
      this.state.periodLabel = tDate(res.period.label);
      this.state.yearOptions = res.yearOptions;
      if (res.customerGroupOptions) {
        this.state.customerGroupOptions = [{ v: 'all', l: 'All' }, ...res.customerGroupOptions];
      }
      this.applyMeta(res);
      this.renderAll();
    } catch (e) {
      this.state.error = t('Failed to load') + ' — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  // Re-runs every node currently in the tree, leaving the open/closed state
  // exactly as it is. Used by the sort control.
  async refetchOpen(withMeta = false) {
    // The root has to lead when meta is wanted: fetchNodesChunked asks for it
    // on the FIRST chunk only, and the meta reply carries the grand total —
    // which, once the budget is on, is a figure this request has to bring back
    // rather than one the previous reply still holds.
    const keys = Object.keys(this.nodes);
    const ordered = [ROOT_KEY, ...keys.filter(k => k !== ROOT_KEY)]
      .filter(k => keys.includes(k) || k === ROOT_KEY);
    const list = ordered.map(k => ({ key: k, path: this.nodePaths[k] || [] }));
    this.state.loading = true;
    this.state.error = '';
    try {
      this.nodes = {};
      const res = await this.fetchNodesChunked(list, withMeta);
      if (res && withMeta) this.applyMeta(res);
      this.renderAll();
    } catch (e) {
      this.state.error = t('Failed to load') + ' — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  /** The half of a meta reply that is not the tree. Shared by load() and a
   *  dataset switch, so the two cannot apply it differently. */
  applyMeta(res) {
    this.state.levels = res.levels || [];
    this.state.allLevels = res.allLevels || res.levels || [];
    if (res.groupBy) {
      this.state.groupBy = res.groupBy;
    }
    this.state.levelFilterOptions = res.levelFilterOptions || {};
    const total = res.total || { qty: 0, value: 0, m: [] };
    // The grand total arrives with its target under `b`; flattened here onto
    // the same bqty/bvalue/bm/budgetOk names every ROW uses, so cellValue and
    // the Others roll-up have one shape to read rather than two.
    const tb = total.b;
    this.state.total = {
      ...total,
      budgetOk: Boolean(tb),
      budgetReason: tb ? '' : t('No target is captured at this level.'),
      bqty: tb ? tb.qty : 0, bvalue: tb ? tb.value : 0, bm: tb ? tb.m : [],
    };
    this.state.hasBudget = Boolean(res.hasBudget);
    this.state.budgetUnsafe = res.budgetUnsafe || {};
    // A board asked for the target and there is none for this year says so
    // once, in the notice line, rather than drawing twelve columns of blanks
    // with no explanation.
    if (this.wantsBudget && !this.state.hasBudget) {
      this.state.notice = t('No budget has been entered for this year.');
    }
    // A part that sold nothing in the year on screen is the one case where the
    // board legitimately draws no rows at all, so it says so rather than
    // leaving an empty matrix to be read as a fault. Since the part filter
    // bypasses the product scope, "no rows" now really does mean no sales —
    // it can no longer be the scope quietly hiding them.
    this.state.part = res.part || null;
    if (this.state.partNo && this.state.part && !this.state.part.found) {
      this.state.notice = t('No sales for this part number in this period.');
      return;
    }
    // More than one of these can be true at once, so they are collected rather
    // than raced — a part outside the scope, on a board left on Budget, has two
    // things to say and both matter.
    const says = [];
    if (this.partOutOfScope) {
      says.push(t('This part is outside the product scope') + ' — ' +
                t('a part lookup ignores it, so these figures are not comparable with the unfiltered board.'));
    }
    if (this.hasPart && this.showBudget && this.state.dataset !== 'sales') {
      // The Data control is left on Budget / Sales & Budget so it comes back
      // when the part is cleared — but nothing is drawn for it, and the reason
      // is the point. (`res.budgetBlocked` carries the same sentence from the
      // server, for a client that asked anyway; `wantsBudget` means this one
      // never does.)
      says.push(t('Showing sales only') + ' — ' +
                t('the budget is not captured per part'));
    }
    if (says.length) this.state.notice = says.join('  ·  ');
  }

  // ------------------------------------------------------------------
  // expand / collapse
  // ------------------------------------------------------------------
  async toggleRow(key) {
    const row = this.rowIndex.get(key);
    if (!row || !row.expandable) return;
    if (this.expandedSet.has(key)) {
      this.expandedSet.delete(key);
      this.renderMatrix();
      return;
    }
    this.expandedSet.add(key);
    if (this.nodes[key]) { this.renderMatrix(); return; }
    this.pendingKeys.add(key);
    this.renderMatrix();
    try {
      await this.fetchNodes([{ key, path: row.path }]);
    } catch (e) {
      this.state.error = t('Failed to load') + ' — ' + e.message;
      this.expandedSet.delete(key);
    } finally {
      this.pendingKeys.delete(key);
      this.renderMatrix();
    }
  }

  // Power BI's "expand all down one level": every row on screen that can be
  // expanded and isn't, in one go.
  async expandNextLevel() {
    const targets = this.visibleRows.filter(r => r.expandable && !r.expanded && !r.others);
    if (!targets.length) { this.state.notice = t('Everything visible is already expanded.'); return; }
    this.state.notice = '';
    this.state.loading = true;
    this.state.error = '';
    try {
      const missing = targets.filter(r => !this.nodes[r.key]).map(r => ({ key: r.key, path: r.path }));
      if (missing.length) await this.fetchNodesChunked(missing);
      for (const r of targets) this.expandedSet.add(r.key);
      this.renderMatrix();
    } catch (e) {
      this.state.error = t('Failed to load') + ' — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  collapseAll() {
    this.expandedSet.clear();
    this.state.notice = '';
    this.renderMatrix();
  }

  // ------------------------------------------------------------------
  // tree -> flat rows
  // ------------------------------------------------------------------
  childKey(parentKey, level, code) {
    const seg = `${level}:${code}`;
    return parentKey ? parentKey + SEP + seg : seg;
  }

  /**
   * Flattens the loaded tree into the rows to draw, honouring the open set
   * and the search box.
   *
   * Search keeps a row when its own name matches OR one of its loaded
   * descendants does — an ancestor is what makes a deep match findable, so
   * dropping it would hide the match itself. Rows are matched against what
   * has been FETCHED; a branch that was never opened has nothing to search.
   */
  buildRows(key, path, depth, parent, needle) {
    const node = this.nodes[key];
    if (!node || !node.rows) return { rows: [], matched: false };
    const maxAbs = node.rows.reduce((m, r) => Math.max(m, Math.abs(r.value)), 0) || 1;
    const out = [];
    let anyMatch = false;
    // Running totals of what this node actually returned, so a capped node's
    // leftovers can be stated exactly — month by month as well as in total.
    let shownQty = 0, shownValue = 0;
    const shownMonths = new Array(12).fill(0).map(() => [0, 0]);
    // Per NODE, not per row: whether this level carries a target at all, and
    // why not. The server sends budget:false plus budgetReason for a level the
    // capture does not reach, and every row under it draws blanks.
    const budgetOk = node.budget === true;
    const budgetReason = node.budgetReason || '';
    let shownBQty = 0, shownBValue = 0;
    const shownBMonths = new Array(12).fill(0).map(() => [0, 0]);
    for (const r of node.rows) {
      const childKey = this.childKey(key, node.level, r.code);
      const childPath = [...path, { level: node.level, code: r.code }];
      shownQty += r.qty;
      shownValue += r.value;
      for (let i = 0; i < 12; i++) {
        const pair = (r.m && r.m[i]) || [0, 0];
        shownMonths[i][0] += pair[0];
        shownMonths[i][1] += pair[1];
      }
      if (budgetOk) {
        shownBQty += r.bqty || 0;
        shownBValue += r.bvalue || 0;
        for (let i = 0; i < 12; i++) {
          const pair = (r.bm && r.bm[i]) || [0, 0];
          shownBMonths[i][0] += pair[0];
          shownBMonths[i][1] += pair[1];
        }
      }
      const expanded = this.expandedSet.has(childKey);
      const selfMatch = !needle || String(r.label || '').toLowerCase().includes(needle)
                        || String(r.code || '').toLowerCase().includes(needle);
      const sub = expanded
        ? this.buildRows(childKey, childPath, depth + 1, r, needle)
        : { rows: [], matched: false };
      if (!needle || selfMatch || sub.matched) {
        anyMatch = anyMatch || selfMatch || sub.matched;
        out.push({
          key: childKey, path: childPath, depth,
          level: node.level, levelLabel: node.levelLabel,
          code: r.code, label: r.label, qty: r.qty, value: r.value, m: r.m || [],
          budgetOk, budgetReason,
          bqty: r.bqty || 0, bvalue: r.bvalue || 0, bm: r.bm || [],
          expandable: node.hasChildren, expanded,
          pending: this.pendingKeys.has(childKey),
          bar: Math.abs(r.value) / maxAbs,
          highlight: Boolean(needle) && selfMatch,
        });
        out.push(...sub.rows);
      }
    }
    // Whatever the node's row cap left out, as one roll-up row: the parent's
    // own figures minus the rows that came back. Keeps every branch adding up
    // to its parent instead of silently losing the tail.
    if (node.more > 0 && !needle) {
      const pm = parent.m || [];
      out.push({
        key: key + SEP + '__others__', others: true, depth,
        level: node.level, levelLabel: node.levelLabel,
        label: `${t('Others')} — ${fmt(node.more)} ${t('more rows')}`,
        qty: parent.qty - shownQty, value: parent.value - shownValue,
        m: shownMonths.map((s, i) => {
          const p = pm[i] || [0, 0];
          return [p[0] - s[0], p[1] - s[1]];
        }),
        // The parent's target minus the rows that came back, on the same
        // subtraction as the actuals — but ONLY when the parent has a target
        // of its own to subtract from. The root's parent is the grand total,
        // whose budget half applyMeta normalises onto the same field names.
        budgetOk: budgetOk && parent.budgetOk !== false,
        budgetReason,
        bqty: (parent.bqty || 0) - shownBQty,
        bvalue: (parent.bvalue || 0) - shownBValue,
        bm: shownBMonths.map((s, i) => {
          const p = (parent.bm && parent.bm[i]) || [0, 0];
          return [p[0] - s[0], p[1] - s[1]];
        }),
        expandable: false, expanded: false, bar: 0,
      });
    }
    return { rows: out, matched: anyMatch };
  }

  // ------------------------------------------------------------------
  // render
  // ------------------------------------------------------------------
  renderAll() {
    this.renderHead();
    this.renderMatrix();
  }

  /** Two header rows (month groups, then the measures under each) plus the
   *  Grand Total. Drawn here rather than in the template because its shape
   *  follows the measure toggle — see the note at the top of this file. */
  renderHead() {
    const el = this.headRef.el;
    if (!el) return;
    const span = this.cellsPerGroup;
    const monthGroups = MONTH_ABBR.map((ab, i) =>
      `<th class="num month-group" colspan="${span}" title="${esc(t(MONTH_NAMES[i]))}">${esc(t(ab))}</th>`
    ).join('');
    // Column captions come off cellSpec, so the header cannot fall out of step
    // with the body when the dataset toggle changes the column set.
    const HEAD = {
      's:qty': ['Qty', 'sub'], 's:value': ['Value', 'sub'],
      'b:qty': ['Bud Qty', 'sub budget-col'], 'b:value': ['Bud Value', 'sub budget-col'],
    };
    const measureCells = () => this.cellSpec.map(c => {
      const [label, cls] = HEAD[`${c.src}:${c.measure}`];
      return `<th class="num ${cls}">${esc(t(label))}</th>`;
    }).join('');
    el.innerHTML = `
      <tr>
        <th class="name-col" rowspan="2">${t('Name')}</th>
        ${monthGroups}
        <th class="num total-group" colspan="${span + 1}">${t('Total')}</th>
      </tr>
      <tr>
        ${MONTH_ABBR.map(() => measureCells()).join('')}
        ${measureCells()}
        <th class="num sub">%</th>
      </tr>
      <tr class="grand-total-row">
        <th class="name-col">${t('Grand Total')}</th>
        ${this.measureCellsHtml(this.state.total, true)}
        ${this.totalCellsHtml(this.state.total, this.state.total, true)}
      </tr>`;
  }

  /** One row's figures for a (dataset, measure) pair, or null.
   *
   * NULL IS NOT ZERO, and the difference is the whole point of the unsafe
   * rules: a row whose level carries no captured target has no target, which
   * is a different statement from a target of nought. Nulls draw as a dimmed
   * blank carrying the reason, never as 0. */
  cellValue(row, spec, monthIdx = null) {
    if (spec.src === 'b') {
      if (!row.budgetOk) return null;
      if (monthIdx === null) return spec.measure === 'qty' ? row.bqty : row.bvalue;
      const pair = (row.bm && row.bm[monthIdx]) || [0, 0];
      return spec.measure === 'qty' ? pair[0] : pair[1];
    }
    if (monthIdx === null) return spec.measure === 'qty' ? row.qty : row.value;
    const pair = (row.m && row.m[monthIdx]) || [0, 0];
    return spec.measure === 'qty' ? pair[0] : pair[1];
  }

  /** The twelve month groups of one row, honouring both toggles. */
  measureCellsHtml(row, isHeader = false) {
    const tag = isHeader ? 'th' : 'td';
    const spec = this.cellSpec;
    let html = '';
    for (let i = 0; i < 12; i++) {
      for (const c of spec) {
        const v = this.cellValue(row, c, i);
        const cls = 'num month-cell' + (c.src === 'b' ? ' budget-col' : '');
        if (v === null) {
          html += `<${tag} class="${cls} no-budget" title="${esc(row.budgetReason || t('No target is captured at this level.'))}">–</${tag}>`;
          continue;
        }
        const what = c.src === 'b'
          ? (c.measure === 'qty' ? t('Bud Qty') : t('Bud Value'))
          : (c.measure === 'qty' ? t('Qty') : t('Value'));
        const labelPrefix = row.label ? `${esc(row.label)} · ` : (isHeader ? `${esc(t('Grand Total'))} · ` : '');
        const title = `${labelPrefix}${esc(t(MONTH_NAMES[i]))} ${esc(what)}: ${fmt(v)}`;
        html += `<${tag} class="${cls}" title="${title}">${monthCellNum(v, c.measure)}</${tag}>`;
      }
    }
    return html;
  }

  /** The Total group: the row's year figures, formatted as M (value) and K (qty),
   *  plus its share of the grand total. Hovering reveals the exact value.
   *
   * The share stays a SALES share whatever the dataset toggle shows — it is
   * the row's weight in the board, and making it flip to a share of target
   * would change what the column means without changing its heading. */
  totalCellsHtml(row, total, isHeader = false, bar = '') {
    const tag = isHeader ? 'th' : 'td';
    let html = '';
    this.cellSpec.forEach((c, i) => {
      const v = this.cellValue(row, c, null);
      const cls = 'num total-cell' + (c.src === 'b' ? ' budget-col' : '')
                  + (i === 0 && bar ? ' total-first' : '');
      if (v === null) {
        html += `<${tag} class="${cls} no-budget" title="${esc(row.budgetReason || t('No target is captured at this level.'))}">–</${tag}>`;
        return;
      }
      const what = c.src === 'b'
        ? (c.measure === 'qty' ? t('Bud Qty') : t('Bud Value'))
        : (c.measure === 'qty' ? t('Qty') : t('Value'));
      const labelPrefix = row.label ? `${esc(row.label)} · ` : (isHeader ? `${esc(t('Grand Total'))} · ` : '');
      const title = `${labelPrefix}${esc(t('Total'))} ${esc(what)}: ${fmt(v)}`;
      const formatted = totalCellNum(v, c.measure);
      // The bar rides on the FIRST cell of the group whatever that cell now
      // is — with Budget alone selected the first cell is a target, and a bar
      // scaled by sales under a target figure would be a lie about which
      // number it measures. It is scaled by the cell it sits on.
      html += bar && i === 0
        ? `<${tag} class="${cls}" title="${title}">${bar}<span class="cell-text">${formatted}</span></${tag}>`
        : `<${tag} class="${cls}" title="${title}">${formatted}</${tag}>`;
    });
    const share = this.showValue ? pct(row.value, total.value) : pct(row.qty, total.qty);
    const shareTitle = isHeader ? '100%' : `${fmtPct(share)}`;
    html += `<${tag} class="num muted" title="${shareTitle}">${isHeader ? '100.0%' : fmtPct(share)}</${tag}>`;
    return html;
  }

  renderMatrix() {
    const needle = (this.state.search || '').trim().toLowerCase();
    const total = this.state.total || { qty: 0, value: 0, m: [] };
    const built = this.buildRows(ROOT_KEY, [], 0, total, needle);
    this.visibleRows = built.rows;
    this.rowIndex = new Map(built.rows.map(r => [r.key, r]));
    this.state.rowCount = built.rows.length;

    const el = this.bodyRef.el;
    if (!el) return;
    if (!built.rows.length) {
      el.innerHTML = `<tr class="empty-row"><td colspan="${this.columnCount}">${
        needle ? t('No rows match the search.') : t('No rows for this selection.')}</td></tr>`;
      return;
    }
    el.innerHTML = built.rows.map(r => this.rowHtml(r, total)).join('');
  }

  rowHtml(r, total) {
    const indent = 10 + r.depth * 18;
    // +/- rather than a chevron: at the size a 4px-indented tree can afford,
    // a triangle is a smudge. The minus is U+2212, not a hyphen, so it sits at
    // the same width and height as the plus it replaces.
    const twist = r.others ? '<span class="twisty spacer"></span>'
      : r.pending ? '<span class="twisty pending">◌</span>'
      : r.expandable ? `<span class="twisty">${r.expanded ? '\u2212' : '+'}</span>`
      : '<span class="twisty spacer"></span>';
    const color = this.levelColor(r.depth);
    const cls = ['matrix-row', `depth-${Math.min(r.depth, 5)}`];
    if (r.others) cls.push('others-row');
    if (r.expandable && !r.others) cls.push('clickable');
    if (r.expanded) cls.push('open');
    if (r.highlight) cls.push('hit');
    // The data bar sits on the Total cell and is scaled within the row's OWN
    // siblings, not against the grand total — at depth 4 or 5 every share of
    // the total is a sliver, and a bar that is always empty says nothing. Its
    // width reads "against the rest of this branch", which is the comparison
    // the eye is making at that point anyway.
    const bar = r.others ? '' :
      `<span class="cell-bar" style="width:${(r.bar * 100).toFixed(2)}%;background:${color}"></span>`;
    const keyAttr = r.others ? '' : ` data-key="${esc(r.key)}"`;
    const title = `${esc(r.levelLabel)}: ${esc(r.label)}${r.code ? ' (' + esc(r.code) + ')' : ''}`;
    return `
      <tr class="${cls.join(' ')}"${keyAttr}>
        <td class="name-cell" style="padding-inline-start:${indent}px">
          ${twist}<span class="level-dot" style="background:${color}"></span>
          <span class="row-label" title="${title}">${esc(r.label)}</span>
        </td>
        ${this.measureCellsHtml(r)}
        ${this.totalCellsHtml(r, total, false, bar)}
      </tr>`;
  }

  // ------------------------------------------------------------------
  // misc
  // ------------------------------------------------------------------
  levelColor(i) { return DEPTH_COLORS[Math.min(i, DEPTH_COLORS.length - 1)]; }

  /** A slicer's options, de-duplicated by code.
   *
   * The server groups by code and aggregates the caption, so it cannot send
   * the same code twice — but OWL kills the WHOLE board on a duplicate
   * t-foreach key ("Got duplicate key in t-foreach: POR001"), and losing the
   * board is a far worse answer to a data quirk than losing one dropdown
   * entry. Cheap insurance on a list of at most a few hundred. */
  levelFilterOptionsFor(level) {
    const opts = this.state.levelFilterOptions[level] || [];
    const seen = new Set();
    return opts.filter(o => {
      const k = String(o.v);
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
  }

  scopeLabel() {
    const opt = SCOPE_OPTIONS.find(o => o.v === this.state.periodScope);
    return opt ? t(opt.l) : '';
  }

  // Exports exactly what is on screen — same rows, same order, same
  // expansion — with the ancestor chain spelled out per row so the file is
  // readable without the tree, and every month in full precision whatever the
  // measure toggle is showing.
  exportCsv() {
    const total = this.state.total || { qty: 0, value: 0, m: [] };
    // Same columns, same order, as the matrix — driven off cellSpec so the
    // file cannot carry a column set the screen never showed. A blank target
    // cell exports as EMPTY rather than 0: the distinction between "no target
    // captured" and "a target of nought" is exactly what a spreadsheet would
    // otherwise destroy.
    const spec = this.cellSpec;
    const CAP = { 's:qty': 'Qty', 's:value': 'Value',
                  'b:qty': 'Bud Qty', 'b:value': 'Bud Value' };
    // THE PART, ON EVERY ROW, and only when one is filtered.
    //
    // The filename already names it, but a filename does not survive being
    // pasted into a sheet beside another export — and every row of a
    // part-filtered file belongs to that part, so the column is true rather
    // than repetitive. Two exports of two parts then stack into one sheet that
    // can be pivoted, which is the whole reason anyone exports this board.
    //
    // Omitted entirely when no part is filtered, rather than carried blank: an
    // unfiltered export keeps exactly the column set it has today, so anything
    // already reading these files is unaffected. A part-filtered export is a
    // shape that did not exist before this feature, so nothing consumes it yet.
    const partCols = this.hasPart
      ? ['Part No', 'Part Description']
      : [];
    const partVals = this.hasPart
      ? [this.state.partNo, (this.state.part && this.state.part.partLabel) || '']
      : [];
    const head = [...partCols, 'Level', 'Hierarchy', 'Name', 'Code'];
    for (const ab of MONTH_ABBR) {
      for (const c of spec) head.push(`${ab} ${CAP[`${c.src}:${c.measure}`]}`);
    }
    for (const c of spec) head.push(`Total ${CAP[`${c.src}:${c.measure}`]}`);
    head.push('Value %');
    const q = s => `"${String(s == null ? '' : s).replace(/"/g, '""')}"`;
    const lines = [head.map(q).join(',')];
    for (const r of this.visibleRows) {
      const chain = r.others ? '' : r.path.map(p => p.code).join(' > ');
      const cells = [...partVals, r.levelLabel, chain, r.label,
                     r.others ? '' : r.code];
      for (let i = 0; i < 12; i++) {
        for (const c of spec) {
          const v = this.cellValue(r, c, i);
          cells.push(v === null ? '' : Math.round(v));
        }
      }
      for (const c of spec) {
        const v = this.cellValue(r, c, null);
        cells.push(v === null ? '' : Math.round(v));
      }
      cells.push((pct(r.value, total.value) || 0).toFixed(2));
      lines.push(cells.map(q).join(','));
    }
    // BOM first so Excel opens the file as UTF-8 — customer names carry
    // Arabic script and would otherwise arrive as mojibake.
    const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const part = this.state.partNo ? `_${this.state.partNo.replace(/[^A-Za-z0-9._-]/g, '')}` : '';
    a.download = `${this.csvName}${part}_${this.state.year}_${String(this.state.month).padStart(2, '0')}_${this.state.periodScope}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

registry.category("actions").add("pbi_sales_dashboards.sales_study_dashboard", PbiSalesStudyDashboard);
