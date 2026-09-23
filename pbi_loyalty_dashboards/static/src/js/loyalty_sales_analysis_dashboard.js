/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { t, addLabels, isArabicUI } from "@pbi_dashboards/js/pbi_i18n";
import { fmt, PALETTE, setTooltipEl, clearTooltipEl, moveTip, attachBarTooltips, labelFont, textWidth } from "@pbi_dashboards/js/pbi_chart_lib";

// "Loyalty Customers Sales Analysis" — the Sales Dashboard - VQ layout
// (Amount on the left, Qty on the right, same category order on both —
// see pbi_sales_dashboards/static/src/js/sales_vq_dashboard.js's own
// "value bars .... ][ qty bars ...." row) applied to one drill-down report,
// the same shape as pbi_sales_dashboards' plain Sales Analysis
// (sales_analysis_dashboard.js): a single chain of levels with ONE shared
// breadcrumb/level, click a bar or its caption on EITHER side to drill in —
// both charts read the same this.state.level/selected, so drilling one
// always drills the other with it, automatically.
//
// Reads from loyalty_sales_table_view (transaction_header/transaction_details
// + res.partner/customer-master/product_category, see controllers/
// loyalty_sales_analysis_main.py) filtered to activate_loyalty_feature
// customers only — NOT the bidata-backed v_pbi_sales_analysis the generic
// Sales Analysis dashboard reads, which has no loyalty-customer filter.
addLabels({
  "Loyalty Customers Sales Analysis": "تحليل مبيعات عملاء الولاء",
  "Region -> City -> Main Category -> Sub-Category -> Product Group -> Product Sub Group -> Customer -> Transactions":
    "المنطقة -> المدينة -> الفئة الرئيسية -> الفئة الفرعية -> مجموعة المنتج -> المجموعة الفرعية للمنتج -> العميل -> المعاملات",
  "Amount": "المبلغ",
  "Qty": "الكمية",
  "Total Amount": "إجمالي المبلغ",
  "Total Qty": "إجمالي الكمية",
  "level": "المستوى",
  "click a bar or label to drill in": "انقر على عمود أو تسمية للتعمق",
  "Region": "المنطقة",
  "City": "المدينة",
  "Main Category": "الفئة الرئيسية",
  "Sub-Category": "الفئة الفرعية",
  "Product Group": "مجموعة المنتج",
  "Product Sub Group": "المجموعة الفرعية للمنتج",
  "Customer": "العميل",
  "Transaction List": "قائمة المعاملات",
  "Date Range": "النطاق الزمني",
  "to": "إلى",
  "Range": "النطاق",
  "This Quarter": "هذا الربع",
  "Last Quarter": "الربع الماضي",
  "Custom Date": "تاريخ مخصص",
  "Transaction No": "رقم المعاملة",
  "Date": "التاريخ",
  "Warehouse": "المستودع",
  "Part": "الصنف",
  "No transactions for this selection.": "لا توجد معاملات لهذا التحديد.",
  "No data for this selection.": "لا توجد بيانات لهذا التحديد.",
  "Failed to load": "فشل التحميل",
  "Midea": "ميديا",
  "Beko": "بيكو",
  "Candy": "كاندي",
  "Alaska": "الاسكا",
  "Smeg": "سميج",
  "Ruud": "رود",
});

function formatDate(d) {
  if (!d) return '';
  if (d instanceof Date) {
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  }
  const parts = String(d).split('-');
  if (parts.length === 3 && parts[0].length === 4) {
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
  }
  return String(d);
}

function getLabelWidth(el, data) {
  const font = labelFont(el, 'bar-label', '11px sans-serif');
  let maxW = 0;
  for (const d of data) {
    if (d.label) {
      maxW = Math.max(maxW, textWidth(String(d.label), font));
    }
  }
  return maxW;
}

function getValueLabelWidth(el, data, valueKey) {
  const font = labelFont(el, 'axis-label', '10px sans-serif');
  let maxW = 0;
  for (const d of data) {
    const val = d[valueKey] || 0;
    maxW = Math.max(maxW, textWidth(fmt(val), font));
  }
  return maxW;
}

// Single-series horizontal bar chart, one row per category, in whatever
// order `data` is already in — the two calls in renderReport() pass the
// SAME data array (sorted by amount server side), so the nth bar lines up
// across the Amount and Qty columns.
function hBarChart(el, data, valueKey, color, valueLabel, onClick, customMarginL) {
  const naturalW = el.clientWidth || 420;
  const labelW = customMarginL != null ? customMarginL : (getLabelWidth(el, data) * 1.15 + 24);
  const marginL = Math.max(140, Math.ceil(labelW));
  const valW = getValueLabelWidth(el, data, valueKey);
  const marginR = Math.max(70, Math.ceil(valW + 20));
  const minPlotW = 180;
  const requiredW = marginL + minPlotW + marginR;
  const W = Math.max(naturalW, requiredW);
  const widthAttr = W > naturalW ? `${W}px` : '100%';
  const rowH = 28, marginT = 4;
  const H = data.length * rowH + marginT * 2;
  const plotW = W - marginL - marginR;
  const maxVal = Math.max(1, ...data.map(d => d[valueKey] || 0)) * 1.05;
  const isRTL = isArabicUI();
  const labelX = isRTL ? (marginL - 8) : 4;
  const labelAnchor = isRTL ? 'end' : 'start';

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${widthAttr}" height="${H}">`;
  data.forEach((d, i) => {
    const y = marginT + i * rowH;
    const val = d[valueKey] || 0;
    const barW = plotW * (val / maxVal);
    svg += `<text class="bar-label cat-label-clickable" data-code="${d.code}" x="${labelX}" y="${y + rowH * 0.62}" text-anchor="${labelAnchor}">${d.label}</text>`;
    svg += `<rect data-code="${d.code}" data-tip="${d.label}||${valueLabel}||${val}" rx="3" ry="3" x="${marginL}" y="${y + rowH * 0.18}" width="${Math.max(barW, 2)}" height="${rowH * 0.55}" fill="${color}" style="cursor:pointer"/>`;
    svg += `<text class="axis-label" x="${marginL + barW + 6}" y="${y + rowH * 0.62}">${fmt(val)}</text>`;
  });
  svg += `</svg>`;
  el.innerHTML = svg;
  attachBarTooltips(el);
  el.querySelectorAll('[data-code]').forEach(elm => {
    elm.style.cursor = 'pointer';
    elm.addEventListener('click', () => {
      const code = elm.getAttribute('data-code');
      const row = data.find(d => String(d.code) === code);
      if (row) onClick(row.code, row.label);
    });
  });
}

function renderTransactionTable(el, rows) {
  if (!rows.length) {
    el.innerHTML = `<p class="subtitle">${t('No transactions for this selection.')}</p>`;
    return;
  }
  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>${t('Transaction No')}</th><th>${t('Date')}</th><th>${t('Warehouse')}</th><th>${t('Part')}</th>
        <th class="num">${t('Qty')}</th><th class="num">${t('Amount')}</th>
      </tr></thead>
      <tbody>
        ${rows.map(r => `<tr>
          <td>${r.transactionNo || '–'}</td>
          <td>${formatDate(r.date) || '–'}</td>
          <td>${r.warehouse || '–'}</td>
          <td>${r.part || '–'}</td>
          <td class="num">${fmt(r.qty)}</td>
          <td class="num">${fmt(r.amount)}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

const PERIOD_OPTIONS = [
  { v: 'this_year', l: 'This Year' },
  { v: 'this_month', l: 'This Month' },
  { v: 'this_week', l: 'This Week' },
  { v: 'this_quarter', l: 'This Quarter' },
  { v: 'last_year', l: 'Last Year' },
  { v: 'last_month', l: 'Last Month' },
  { v: 'last_week', l: 'Last Week' },
  { v: 'last_quarter', l: 'Last Quarter' },
  { v: 'custom', l: 'Custom Date' },
];

// v matches catalog.cat_grp / t_groupsdesc.grpd_code exactly (see
// FRANCHISE_OPTIONS in loyalty_sales_analysis_main.py). Midea listed first
// since it's the default.
const FRANCHISE_OPTIONS = [
  { v: 'MDA', l: 'Midea' },
  { v: 'BKO', l: 'Beko' },
  { v: 'CDY', l: 'Candy' },
  { v: 'ASK', l: 'Alaska' },
  { v: 'SMG', l: 'Smeg' },
  { v: 'RUD', l: 'Ruud' },
  { v: 'all', l: 'All' },
];

// "transactions" is a leaf row list, not a group-by level (see loadDrill).
const LEVELS = ['region', 'city', 'mainCategory', 'subCategory', 'productGroup', 'productSubGroup', 'customer', 'transactions'];
const LEVEL_LABELS = {
  region: 'Region', city: 'City', mainCategory: 'Main Category', subCategory: 'Sub-Category',
  productGroup: 'Product Group', productSubGroup: 'Product Sub Group',
  customer: 'Customer', transactions: 'Transaction List',
};

export class PbiLoyaltySalesAnalysisDashboard extends Component {
  static template = "pbi_dashboards.loyalty_sales_analysis_dashboard";
  static props = ["*"];

  get isDebugMode() {
    return Boolean(window.odoo && window.odoo.debug);
  }

  setup() {
    this.rpc = useService("rpc");
    this.t = t;
    this.isArabicUI = isArabicUI;
    this.formatDate = formatDate;
    this.periodOptions = PERIOD_OPTIONS;
    this.franchiseOptions = FRANCHISE_OPTIONS;
    this.levelLabels = LEVEL_LABELS;

    this.state = useState({
      period: 'this_year', franchise: 'MDA', dateFrom: '', dateTo: '',
      resolvedFrom: '', resolvedTo: '',
      loading: false, error: '',
      level: 'region', selected: {}, path: [],
    });

    this.reportData = { rows: [], total: { amount: 0, qty: 0 } };

    this.rootRef = useRef('root');
    this.refs = {
      tooltip: useRef('tooltip'),
      subtitle: useRef('subtitle'),
      breadcrumb: useRef('breadcrumb'),
      bodyAmount: useRef('bodyAmount'),
      bodyQty: useRef('bodyQty'),
      bodyTransactions: useRef('bodyTransactions'),
    };

    this._onMouseMove = evt => moveTip(evt);
    onMounted(() => {
      setTooltipEl(this.refs.tooltip.el);
      document.addEventListener('mousemove', this._onMouseMove);
      this.load();
    });
    onWillUnmount(() => {
      document.removeEventListener('mousemove', this._onMouseMove);
      clearTooltipEl(this.refs.tooltip.el);
    });
  }

  _todayIso() { return new Date().toISOString().slice(0, 10); }

  seriesColors() {
    return [PALETTE[0], PALETTE[1]];
  }

  // ------------------------------------------------------------------
  // loading
  // ------------------------------------------------------------------
  async selectPeriod(v) {
    this.state.period = v;
    if (v === 'custom') {
      if (!this.state.dateFrom) this.state.dateFrom = this.state.resolvedFrom || this._todayIso();
      if (!this.state.dateTo) this.state.dateTo = this.state.resolvedTo || this._todayIso();
    }
    await this.load();
  }

  async selectFranchise(v) { this.state.franchise = v; await this.load(); }
  async setDateFrom(v) { this.state.dateFrom = v; await this.load(); }
  async setDateTo(v) { this.state.dateTo = v; await this.load(); }

  exportPdf() { window.print(); }

  _filterParams() {
    const params = { period: this.state.period, franchise: this.state.franchise };
    if (this.state.period === 'custom') {
      params.dateFrom = this.state.dateFrom;
      params.dateTo = this.state.dateTo;
    }
    return params;
  }

  async load() {
    this.state.loading = true;
    this.state.error = '';
    try {
      const res = await this.rpc('/pbi_dashboards/loyalty_sales_analysis/data', this._filterParams());
      if (res.error) { this.state.error = res.error; return; }
      this.state.resolvedFrom = res.dateFrom;
      this.state.resolvedTo = res.dateTo;
      this.state.level = 'region';
      this.state.selected = {};
      this.state.path = [];
      this.reportData = { rows: res.rows, total: res.total };
      this.renderReport();
    } catch (e) {
      this.state.error = t('Failed to load') + ' — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  async loadDrill() {
    const params = { ...this._filterParams(), level: this.state.level, selected: this.state.selected };
    const res = await this.rpc('/pbi_dashboards/loyalty_sales_analysis/drill', params);
    if (res.error) { this.state.error = res.error; return; }
    this.reportData = res;
    this.renderReport();
  }

  // ------------------------------------------------------------------
  // drill navigation
  // ------------------------------------------------------------------
  onRowClick(code, label) {
    if (this.state.level === 'transactions') return;
    const idx = LEVELS.indexOf(this.state.level);
    this.state.selected[this.state.level] = code;
    this.state.path.push({ level: this.state.level, code, label });
    this.state.level = LEVELS[idx + 1];
    this.loadDrill();
  }

  drillTo(pathIndex) {
    // pathIndex === -1 means back to the root (Region) level.
    this.state.path = this.state.path.slice(0, pathIndex + 1);
    this.state.level = LEVELS[pathIndex + 1];
    for (const lvl of LEVELS) {
      if (!this.state.path.some(p => p.level === lvl)) delete this.state.selected[lvl];
    }
    this.loadDrill();
  }

  // ------------------------------------------------------------------
  // rendering
  // ------------------------------------------------------------------
  renderSubtitle() {
    const total = this.reportData.total || { amount: 0, qty: 0 };
    this.refs.subtitle.el.textContent =
      `${t('Total Amount')}: ${fmt(total.amount)} · ${t('Total Qty')}: ${fmt(total.qty)}`
      + ` · ${t(LEVEL_LABELS[this.state.level])} ${t('level')}`
      + (this.state.level === 'transactions' ? '' : ` · ${t('click a bar or label to drill in')}`);
  }

  renderBreadcrumb() {
    const el = this.refs.breadcrumb.el;
    const parts = [{ label: t('All Regions'), idx: -1 }, ...this.state.path.map((p, i) => ({ label: p.label, idx: i }))];
    if (parts.length === 1) { el.innerHTML = ''; return; }
    el.innerHTML = parts.map((p, i) => {
      if (i === parts.length - 1) return `<span class="crumb current">${p.label}</span>`;
      return `<span class="crumb" data-idx="${p.idx}">${p.label}</span><span class="crumb-sep">›</span>`;
    }).join('');
    el.querySelectorAll('.crumb[data-idx]').forEach(elm => {
      elm.addEventListener('click', () => this.drillTo(+elm.getAttribute('data-idx')));
    });
  }

  renderReport() {
    const data = this.reportData.rows || [];

    this.renderSubtitle();
    this.renderBreadcrumb();

    if (this.state.level === 'transactions') {
      renderTransactionTable(this.refs.bodyTransactions.el, data);
      return;
    }
    const onClick = (code, label) => this.onRowClick(code, label);
    const [colorAmount, colorQty] = this.seriesColors();
    if (!data.length) {
      const msg = `<p class="subtitle">${t('No data for this selection.')}</p>`;
      this.refs.bodyAmount.el.innerHTML = msg;
      this.refs.bodyQty.el.innerHTML = msg;
    } else {
      // Same `data` array, same order, on both sides — that's what keeps
      // the nth bar the same category left and right, and it's also why
      // drilling from either side automatically drills the other: both
      // charts click back into the one onRowClick(), which is the only
      // thing that ever changes this.state.level/selected.
      const rootEl = this.rootRef.el || document.body;
      const maxLabelW = getLabelWidth(rootEl, data);
      const sharedMarginL = Math.max(140, Math.ceil(maxLabelW * 1.15 + 24));

      hBarChart(this.refs.bodyAmount.el, data, 'amount', colorAmount, t('Amount'), onClick, sharedMarginL);
      hBarChart(this.refs.bodyQty.el, data, 'qty', colorQty, t('Qty'), onClick, sharedMarginL);
    }
  }
}

registry.category("actions").add("pbi_dashboards.loyalty_sales_analysis_dashboard", PbiLoyaltySalesAnalysisDashboard);
