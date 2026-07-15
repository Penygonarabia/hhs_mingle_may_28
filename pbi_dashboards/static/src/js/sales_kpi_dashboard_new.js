/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { t, tDate, addLabels, isArabicUI } from "./pbi_i18n";

// "Sales Dashboard - New" — sibling of sales_kpi_dashboard.js, same
// bidata-direct MTD/YTD KPI + Sales Type Group chart data (own JSON route,
// see pbi_dashboards/controllers/sales_kpi_main.py's sales_kpi_data_new),
// but with an Amount/Qty toggle: only the selected measure's 12 KPI tiles
// and MTD/YTD chart pair render at a time, and each chart row is one
// widened bar chart + its contribution-% donut side by side (MTD row, then
// a second YTD row below it) instead of the original's 4-across
// Bar/Donut/Bar/Donut grid. EN -> AR strings below cover everything this
// file renders itself that ISN'T already in pbi_i18n.js's shared LABELS
// dict (Year/Month/Franchise/Region/Total/Share/Contribution/Actual/...)
// or already added by sales_kpi_dashboard.js's own addLabels call (both
// files are bundled together, but this file is kept self-contained so it
// doesn't depend on load order). Deliberately EXCLUDED: Customer Type
// category names, franchise names and any drilled-category name that comes
// back from the server — those are real data values, not chrome.
addLabels({
  "Sales Dashboard - New": "لوحة مبيعات المبيعات - جديد",
  "Amount": "القيمة",
  "Quantity": "الكمية",
  "Customer Group": "مجموعة العملاء",
  "Customer Type": "نوع العميل",
  "Customer Sub-Type": "النوع الفرعي للعميل",
  "Customer": "العميل",
  "Product Group": "مجموعة المنتجات",
  "Product Sub-Group": "المجموعة الفرعية للمنتجات",
  "Customer Types": "أنواع العملاء",
  "Customer Sub-Types": "الأنواع الفرعية للعملاء",
  "Regions": "المناطق",
  "Customers": "العملاء",
  "Product Groups": "مجموعات المنتجات",
  "Product Sub-Groups": "المجموعات الفرعية للمنتجات",
  "All Customer Types": "كل أنواع العملاء",
  "Grouped by": "مجمّع حسب",
  "click a bar or slice to drill in": "انقر على عمود أو قطاع للتعمق",
  "(deepest level)": "(أعمق مستوى)",
  "Filters & Levels": "الفلاتر والمستويات",
  "MTD – Sales Amount Analysis": "تحليل قيمة المبيعات – حتى تاريخه (الشهر)",
  "MTD – Amt Contribution %": "نسبة مساهمة القيمة – حتى تاريخه (الشهر)",
  "YTD – Sales Amount Analysis": "تحليل قيمة المبيعات – حتى تاريخه (السنة)",
  "YTD – Amt Contribution %": "نسبة مساهمة القيمة – حتى تاريخه (السنة)",
  "MTD – Sales Qty Analysis": "تحليل كمية المبيعات – حتى تاريخه (الشهر)",
  "MTD – Qty Contribution %": "نسبة مساهمة الكمية – حتى تاريخه (الشهر)",
  "YTD – Sales Qty Analysis": "تحليل كمية المبيعات – حتى تاريخه (السنة)",
  "YTD – Qty Contribution %": "نسبة مساهمة الكمية – حتى تاريخه (السنة)",
  "This Year, Target and Last Year": "هذا العام، الهدف والعام الماضي",
  "This Year Sales": "مبيعات هذا العام",
  "Target Sales": "مبيعات الهدف",
  "Last Year Sales": "مبيعات العام الماضي",
  "This Year Qty": "كمية هذا العام",
  "Target Qty": "كمية الهدف",
  "Last Year Qty": "كمية العام الماضي",
  "MTD - This Year Sales": "مبيعات هذا العام - حتى تاريخه (الشهر)",
  "MTD - Target": "الهدف - حتى تاريخه (الشهر)",
  "MTD - Sales vs Target %": "المبيعات مقابل الهدف % - حتى تاريخه (الشهر)",
  "YTD - This Year Sales": "مبيعات هذا العام - حتى تاريخه (السنة)",
  "YTD - Target": "الهدف - حتى تاريخه (السنة)",
  "YTD - Sales vs Target %": "المبيعات مقابل الهدف % - حتى تاريخه (السنة)",
  "MTD - Last Year Sales": "مبيعات العام الماضي - حتى تاريخه (الشهر)",
  "MTD - TY Sales vs LY Sales %": "مبيعات هذا العام مقابل العام الماضي % - حتى تاريخه (الشهر)",
  "YTD - Last Year Sales": "مبيعات العام الماضي - حتى تاريخه (السنة)",
  "YTD - TY Sales vs LY Sales %": "مبيعات هذا العام مقابل العام الماضي % - حتى تاريخه (السنة)",
  "MTD - This Year Qty": "كمية هذا العام - حتى تاريخه (الشهر)",
  "MTD - Target Qty": "كمية الهدف - حتى تاريخه (الشهر)",
  "MTD - Qty vs Target %": "الكمية مقابل الهدف % - حتى تاريخه (الشهر)",
  "YTD - This Year Qty": "كمية هذا العام - حتى تاريخه (السنة)",
  "YTD - Target Qty": "كمية الهدف - حتى تاريخه (السنة)",
  "YTD - Qty vs Target %": "الكمية مقابل الهدف % - حتى تاريخه (السنة)",
  "MTD - Last Year Qty": "كمية العام الماضي - حتى تاريخه (الشهر)",
  "MTD - TY Qty vs LY Qty %": "كمية هذا العام مقابل العام الماضي % - حتى تاريخه (الشهر)",
  "YTD - Last Year Qty": "كمية العام الماضي - حتى تاريخه (السنة)",
  "YTD - TY Qty vs LY Qty %": "كمية هذا العام مقابل العام الماضي % - حتى تاريخه (السنة)",
  "Failed to load": "فشل التحميل",
  "January": "يناير", "February": "فبراير", "March": "مارس", "April": "أبريل",
  "May": "مايو", "June": "يونيو", "July": "يوليو", "August": "أغسطس",
  "September": "سبتمبر", "October": "أكتوبر", "November": "نوفمبر", "December": "ديسمبر",
});

// ---------------------------------------------------------------------
// formatting/tooltip helpers — trimmed copy of the pattern in
// sales_kpi_dashboard.js (not exported there, so carried here too).
// ---------------------------------------------------------------------
const fmt = n => n == null ? "–" : new Intl.NumberFormat('en-US').format(Math.round(n));
const fmtM = n => n == null ? "–" : (n / 1e6).toFixed(1) + "M";
const fmtK = n => n == null ? "–" : (n / 1e3).toFixed(1) + "K";
const fmtCompact = n => n == null ? "–" : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(n);
function pct(part, total) { return total > 0 ? (part / total * 100) : null; }
function fmtPct(p) { return p == null ? "–" : p.toFixed(1) + "%"; }
function fmtPctPrecise(p) { return p == null ? "–" : p.toFixed(2) + "%"; }

let tooltipEl = null;
function showTip(evt, html) {
  if (!tooltipEl) return;
  tooltipEl.innerHTML = html;
  tooltipEl.classList.add('show');
  moveTip(evt);
}
function moveTip(evt) {
  if (!tooltipEl) return;
  const pad = 14;
  tooltipEl.style.left = (evt.clientX + pad) + 'px';
  tooltipEl.style.top = (evt.clientY + pad) + 'px';
}
function hideTip() { if (tooltipEl) tooltipEl.classList.remove('show'); }

function truncateLabel(text, maxWidth, fontSize = 10) {
  if (!text) return text;
  const maxChars = Math.max(1, Math.floor(maxWidth / (fontSize * 0.6)));
  if (text.length <= maxChars) return text;
  return text.slice(0, Math.max(1, maxChars - 1)) + '…';
}

function attachBarTooltips(el) {
  el.querySelectorAll('rect[data-tip]').forEach(rect => {
    rect.addEventListener('mousemove', evt => {
      const [label, seriesLabel, val] = rect.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${seriesLabel}: <b>${fmt(+val)}</b>`);
    });
    rect.addEventListener('mouseleave', hideTip);
  });
}

function attachValueTooltips(el, selector) {
  el.querySelectorAll(selector).forEach(node => {
    node.addEventListener('mousemove', evt => {
      const [label, sub, val] = node.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${sub}: <b>${val}</b>`);
    });
    node.addEventListener('mouseleave', hideTip);
  });
}

function legendHtml(labels, colors) {
  const items = labels.map((l, i) =>
    `<div class="item"><span class="swatch" style="background:${colors[i]}"></span>${l}</div>`).join('');
  return `<div class="pbi-legend-wrap"><div class="pbi-legend">${items}</div><button type="button" class="legend-more" title="Show more">&#9654;</button></div>`;
}
function attachLegendScroll(container) {
  const wrap = container.querySelector('.pbi-legend-wrap');
  if (!wrap) return;
  const row = wrap.querySelector('.pbi-legend');
  const btn = wrap.querySelector('.legend-more');
  const sync = () => {
    const overflowing = row.scrollWidth > row.clientWidth + 1;
    btn.style.visibility = overflowing ? 'visible' : 'hidden';
    if (!overflowing) return;
    const atEnd = row.scrollLeft >= row.scrollWidth - row.clientWidth - 1;
    btn.innerHTML = atEnd ? '&#9664;' : '&#9654;';
    btn.title = atEnd ? 'Back to start' : 'Show more';
  };
  btn.addEventListener('click', () => {
    const atEnd = row.scrollLeft >= row.scrollWidth - row.clientWidth - 1;
    row.scrollTo({ left: atEnd ? 0 : row.scrollLeft + 140, behavior: 'smooth' });
    setTimeout(sync, 300);
  });
  requestAnimationFrame(() => requestAnimationFrame(sync));
}

const PALETTE = [
  '#2a78d6', '#1baf7a', '#eda100', '#4a3aa7', '#17a2b8',
  '#e34948', '#8e44ad', '#16a085', '#d35400', '#2c3e50',
  '#c0392b', '#27ae60', '#f39c12', '#7f8c8d', '#3498db',
];

function niceAxisTicks(maxVal, valueFmt) {
  const unit = valueFmt === fmtM ? 1e6 : valueFmt === fmtK ? 1e3 : 1;
  const maxUnits = Math.max(1, Math.ceil(maxVal / unit));
  const ladder = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000];
  let step = ladder[ladder.length - 1];
  for (const s of ladder) {
    if (Math.ceil(maxUnits / s) <= 5) { step = s; break; }
  }
  const niceMaxUnits = Math.ceil(maxUnits / step) * step;
  const ticks = [];
  for (let u = 0; u <= niceMaxUnits; u += step) ticks.push(u * unit);
  return ticks;
}

function axisTickLabel(val, valueFmt) {
  return valueFmt(val).replace(/\.0(?=\D|$)/, '');
}

// ---------------------------------------------------------------------
// grouped bar chart — same as sales_kpi_dashboard.js's, one group per
// breakdown category, up to 3 series (This Year / Target / Last Year).
// ---------------------------------------------------------------------
function groupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels, onCategoryClick, valueFmt = fmtCompact) {
  seriesLabels = seriesLabels.map(t);
  const perGroup = 180;
  const W = Math.max(el.clientWidth || 480, data.length * perGroup), H = 230;
  const marginL = 54, marginR = 10, marginT = 10, marginB = 46;
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const maxRaw = Math.max(1, ...data.flatMap(d => seriesKeys.map(k => d[k] || 0)));
  const tickVals = niceAxisTicks(maxRaw, valueFmt);
  const maxVal = tickVals[tickVals.length - 1];
  const groupW = plotW / data.length;
  const gap = 6;
  const barW = Math.min(32, (groupW - gap * (seriesKeys.length - 1)) / seriesKeys.length * 0.9);
  const clickable = !!onCategoryClick;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}px" height="${H}">`;
  tickVals.forEach(val => {
    const y = marginT + plotH - (plotH * val / maxVal);
    svg += `<line class="gridline" x1="${marginL}" x2="${W - marginR}" y1="${y}" y2="${y}"/>`;
    svg += `<text class="axis-label" x="${marginL - 8}" y="${y + 3}" text-anchor="end">${axisTickLabel(val, valueFmt)}</text>`;
  });
  svg += `<line class="baseline" x1="${marginL}" x2="${W - marginR}" y1="${marginT + plotH}" y2="${marginT + plotH}"/>`;

  data.forEach((d, gi) => {
    const groupX = marginL + gi * groupW + groupW / 2 - (barW * seriesKeys.length + gap * (seriesKeys.length - 1)) / 2;
    seriesKeys.forEach((k, si) => {
      const val = d[k] || 0;
      const barH = plotH * (val / maxVal);
      const x = groupX + si * (barW + gap);
      const y = marginT + plotH - barH;
      svg += `<rect data-code="${d.code}" data-tip="${d.label}||${seriesLabels[si]}||${val}" rx="2" ry="2" x="${x}" y="${y}" width="${barW}" height="${Math.max(barH, 1)}" fill="${seriesColors[si]}" style="${clickable ? 'cursor:pointer' : ''}"/>`;
      svg += `<text class="bar-value" x="${x + barW / 2}" y="${y - 3}" text-anchor="middle">${valueFmt(val)}</text>`;
    });
    const label = truncateLabel(d.label, groupW - 8);
    svg += `<text class="axis-label${clickable ? ' cat-label-clickable' : ''}" data-code="${d.code}" x="${marginL + gi * groupW + groupW / 2}" y="${H - 24}" text-anchor="middle"><title>${d.label}</title>${label}</text>`;
  });
  svg += `</svg>`;
  el.innerHTML = legendHtml(seriesLabels, seriesColors) + svg;
  attachBarTooltips(el);
  attachLegendScroll(el);
  if (onCategoryClick) {
    el.querySelectorAll('[data-code]').forEach(elm => {
      elm.addEventListener('click', () => {
        const row = data.find(d => String(d.code) === elm.getAttribute('data-code'));
        if (row) onCategoryClick(row.code, row.label);
      });
    });
  }
}

// ---------------------------------------------------------------------
// donut chart — same as sales_kpi_dashboard.js's.
// ---------------------------------------------------------------------
function donutChart(el, data, colors, onCategoryClick, valueFmt = fmtCompact) {
  const total = data.reduce((s, d) => s + (d.value || 0), 0);
  const r = 47, thickness = 20;
  const ringOuterR = r + thickness / 2;
  const labelR = ringOuterR + 40;
  const cx = labelR + 18, cy = labelR + 18;
  const W = cx * 2, H = cy * 2;
  const circumference = 2 * Math.PI * r;
  const clickable = !!onCategoryClick;

  if (total <= 0) {
    let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
    svg += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--grid)" stroke-width="${thickness}"/>`;
    svg += `<circle class="donut-total-hit" data-tip="${t('Total')}||${t('Actual')}||${fmt(0)}" cx="${cx}" cy="${cy}" r="${r - thickness / 2}" fill="transparent"/>`;
    svg += `<text class="donut-total" x="${cx}" y="${cy - 2}" text-anchor="middle">${valueFmt(0)}</text>`;
    svg += `<text class="donut-total-label" x="${cx}" y="${cy + 16}" text-anchor="middle">${t('Total')}</text>`;
    svg += `</svg>`;
    el.innerHTML = legendHtml(data.map(d => d.label), data.map(() => 'var(--grid)')) + svg;
    attachLegendScroll(el);
    attachValueTooltips(el, '.donut-total-hit[data-tip]');
    return;
  }

  const slices = [];
  let cumulative = 0;
  data.forEach((d, i) => {
    const share = (d.value || 0) / total;
    if (share <= 0) return;
    const trueAngle = (cumulative + share / 2) * 2 * Math.PI - Math.PI / 2;
    const text = (share * 100).toFixed(1) + '%';
    const halfAngle = (text.length * 5.6 / 2 + 4) / labelR;
    slices.push({ code: d.code, label: d.label, share, trueAngle, labelAngle: trueAngle, halfAngle, cumStart: cumulative, colorIdx: i });
    cumulative += share;
  });

  const n = slices.length;
  for (let pass = 0; pass < 2; pass++) {
    for (let k = 0; k < n; k++) {
      const i = pass === 0 ? k : n - 1 - k;
      const j = pass === 0 ? (i + 1) % n : (i - 1 + n) % n;
      let gap = pass === 0 ? slices[j].labelAngle - slices[i].labelAngle : slices[i].labelAngle - slices[j].labelAngle;
      if (gap < 0) gap += 2 * Math.PI;
      const needed = slices[i].halfAngle + slices[j].halfAngle + 0.025;
      if (gap < needed) {
        const deficit = needed - gap;
        slices[j].labelAngle += pass === 0 ? deficit : -deficit;
      }
    }
  }

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  const rings = [];
  const labels = [];
  slices.forEach(s => {
    const segLen = s.share * circumference;
    const offset = -s.cumStart * circumference;
    rings.push(`<circle data-code="${s.code}" data-tip="${s.label}||${t('Share')}||${(s.share * 100).toFixed(1)}" cx="${cx}" cy="${cy}" r="${r}" fill="none"
              stroke="${colors[s.colorIdx % colors.length]}" stroke-width="${thickness}"
              stroke-dasharray="${segLen} ${circumference - segLen}" stroke-dashoffset="${offset}"
              style="${clickable ? 'cursor:pointer' : ''}"
              transform="rotate(-90 ${cx} ${cy})"/>`);

    const cosA = Math.cos(s.trueAngle), sinA = Math.sin(s.trueAngle);
    const cosL = Math.cos(s.labelAngle), sinL = Math.sin(s.labelAngle);
    const x1 = cx + cosA * (ringOuterR + 2), y1 = cy + sinA * (ringOuterR + 2);
    const x2 = cx + cosL * (labelR - 9), y2 = cy + sinL * (labelR - 9);
    labels.push(`<line class="donut-leader" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`);
    const lx = cx + cosL * labelR, ly = cy + sinL * labelR;
    labels.push(`<text class="donut-label" x="${lx}" y="${ly}" text-anchor="middle">${(s.share * 100).toFixed(1)}%</text>`);
  });
  svg += rings.join('') + labels.join('');
  svg += `<circle class="donut-total-hit" data-tip="${t('Total')}||${t('Actual')}||${fmt(total)}" cx="${cx}" cy="${cy}" r="${r - thickness / 2}" fill="transparent"/>`;
  svg += `<text class="donut-total" x="${cx}" y="${cy - 2}" text-anchor="middle">${valueFmt(total)}</text>`;
  svg += `<text class="donut-total-label" x="${cx}" y="${cy + 16}" text-anchor="middle">${t('Total')}</text>`;
  svg += `</svg>`;
  el.innerHTML = legendHtml(data.map(d => d.label), data.map((d, i) => colors[i % colors.length])) + svg;
  attachLegendScroll(el);
  attachValueTooltips(el, '.donut-total-hit[data-tip]');
  el.querySelectorAll('circle[data-tip]:not(.donut-total-hit)').forEach(c => {
    c.addEventListener('mousemove', evt => {
      const [label, , share] = c.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${t('Contribution')}: <b>${share}%</b>`);
    });
    c.addEventListener('mouseleave', hideTip);
    if (onCategoryClick) {
      c.addEventListener('click', () => {
        const row = data.find(d => String(d.code) === c.getAttribute('data-code'));
        if (row) onCategoryClick(row.code, row.label);
      });
    }
  });
}

// ---------------------------------------------------------------------
// filter options
// ---------------------------------------------------------------------
const FRANCHISE_OPTIONS = [
  { v: 'all', l: 'All' }, { v: 'Midea', l: 'Midea' }, { v: 'BEKO', l: 'BEKO' }, { v: 'CANDY', l: 'CANDY' },
];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"];
const MONTH_OPTIONS = MONTH_NAMES.map((l, i) => ({ v: i + 1, l }));
const SALES_TYPE_GROUP_OPTIONS = [
  { v: 'all', l: 'All' }, { v: 'Dealers', l: 'Dealers' }, { v: 'Projects', l: 'Projects' },
  { v: 'Key Accounts', l: 'Key Accounts' }, { v: 'Corporate Sales', l: 'Corporate Sales' },
];
const SALES_TYPE_GROUP_COLORS = ['--series-1', '--series-2', '--series-3', '--series-4'];

const LEVEL_FILTER_LABELS = {
  salesTypeGroup: 'Customer Type', customerSubType: 'Customer Sub-Type', region: 'Region',
  customer: 'Customer', productGroup: 'Product Group', productSubGroup: 'Product Sub-Group',
};
const LEVEL_NAV_LABELS = {
  salesTypeGroup: 'Customer Types', customerSubType: 'Customer Sub-Types', region: 'Regions',
  customer: 'Customers', productGroup: 'Product Groups', productSubGroup: 'Product Sub-Groups',
};

// No "salesman" entry — sales_kpi_main.py's LEVELS chain doesn't include
// that level (removed there per an earlier request), so a nav button for
// it would jump to a level the server silently ignores.
const LEVEL_ORDER = ['salesTypeGroup', 'customerSubType', 'region', 'customer', 'productGroup', 'productSubGroup'];

// Amount vs Qty toggle options — the only new piece of UI/state this file
// adds over sales_kpi_dashboard.js. Selecting one narrows BOTH the KPI
// tile row and the MTD/YTD chart pair to that one measure (see
// renderKpis/renderCharts below) — nothing server-side changes, the
// backend bundle (sales_kpi_data_new) always returns both measures, same
// as the original dashboard's route.
const MEASURE_OPTIONS = [
  { v: 'amount', l: 'Amount' },
  { v: 'qty', l: 'Quantity' },
];

export class PbiSalesKpiDashboardNew extends Component {
  static template = "pbi_dashboards.sales_kpi_dashboard_new";
  static props = ["*"];

  setup() {
    this.rpc = useService("rpc");
    this.franchiseOptions = FRANCHISE_OPTIONS;
    this.monthOptions = MONTH_OPTIONS;
    this.measureOptions = MEASURE_OPTIONS;

    this.state = useState({
      year: null, month: null, franchise: 'Midea', customerGroup: 'all', salesTypeGroup: 'all',
      loading: false, error: '',
      yearOptions: [], customerGroupOptions: [{ v: 'all', l: 'All' }],
      periodLabel: '', hasPrevYear: false,
      // Amount/Qty toggle — see MEASURE_OPTIONS above.
      measure: 'amount',
      drillPath: [], level: 'salesTypeGroup', levelLabel: t('Customer Type'), canDrillFurther: true,
      levelFilterLabel: t(LEVEL_FILTER_LABELS.salesTypeGroup),
      levelFilterOptions: SALES_TYPE_GROUP_OPTIONS,
      levelFilterValue: 'all',
      levelFilterSelected: null,
      levelOverride: null,
      toolbarCollapsed: false,
    });
    this.levelNav = LEVEL_ORDER.map(v => ({ v, l: t(LEVEL_NAV_LABELS[v]) }));
    this.t = t;
    this.isArabicUI = isArabicUI;

    this.rootRef = useRef('root');
    this.refs = {
      kpiRow: useRef('kpiRow'),
      breadcrumb: useRef('breadcrumb'),
      // One chart pair per period (MTD/YTD) — unlike sales_kpi_dashboard.js's
      // 8 refs (Amount+Qty always both mounted), this dashboard only ever
      // shows one measure at a time, so 4 refs are re-rendered in place
      // when the toggle changes (see renderCharts).
      mtdBar: useRef('mtdBar'), mtdDonut: useRef('mtdDonut'),
      ytdBar: useRef('ytdBar'), ytdDonut: useRef('ytdDonut'),
      tooltip: useRef('tooltip'),
    };

    this._onMouseMove = evt => moveTip(evt);
    onMounted(() => {
      tooltipEl = this.refs.tooltip.el;
      document.addEventListener('mousemove', this._onMouseMove);
      this.load();
    });
    onWillUnmount(() => {
      document.removeEventListener('mousemove', this._onMouseMove);
      if (tooltipEl === this.refs.tooltip.el) tooltipEl = null;
    });
  }

  resetDrill() { this.state.drillPath = []; this.state.levelFilterSelected = null; this.state.levelOverride = null; }

  toggleToolbar() { this.state.toolbarCollapsed = !this.state.toolbarCollapsed; }

  selectYear(v) { this.state.year = +v; this.resetDrill(); this.load(); }
  selectMonth(v) { this.state.month = +v; this.resetDrill(); this.load(); }
  selectFranchise(v) { this.state.franchise = v; this.resetDrill(); this.load(); }
  selectCustomerGroup(v) { this.state.customerGroup = v; this.resetDrill(); this.load(); }
  selectSalesTypeGroup(v) { this.state.salesTypeGroup = v; this.resetDrill(); this.load(); }

  // Amount/Qty toggle — purely a display switch on data already loaded
  // (this.lastJson always carries both measures), so it just re-renders
  // the tiles/charts in place instead of round-tripping to the server.
  selectMeasure(v) {
    if (this.state.measure === v) return;
    this.state.measure = v;
    if (this.lastJson) {
      this.renderKpis();
      this.renderCharts();
    }
  }

  jumpToLevel(level) {
    if (level === this.state.level && !this.state.levelFilterSelected) return;
    this.state.levelOverride = level;
    this.state.levelFilterSelected = null;
    this.load();
  }

  selectLevelFilter(v) {
    if (this.state.level === 'salesTypeGroup') { this.selectSalesTypeGroup(v); return; }
    this.state.levelFilterSelected = (!v || v === 'all') ? null : v;
    this.load();
  }

  buildLevelFilterOptions(res) {
    if (res.level === 'salesTypeGroup') return SALES_TYPE_GROUP_OPTIONS;
    const rows = res.levelOptions || [];
    const opts = [{ v: 'all', l: 'All' }];
    const seen = new Set();
    for (const r of rows) {
      if (seen.has(r.v)) continue;
      seen.add(r.v);
      opts.push(r);
    }
    return opts;
  }

  onCategoryClick(code, label) {
    if (!this.state.canDrillFurther) return;
    this.state.drillPath = [...this.state.drillPath, { level: this.state.level, code, label }];
    this.state.levelFilterSelected = null;
    this.state.levelOverride = null;
    this.load();
  }

  drillTo(pathIndex) {
    this.state.drillPath = this.state.drillPath.slice(0, pathIndex + 1);
    this.state.levelFilterSelected = null;
    this.state.levelOverride = null;
    this.load();
  }

  renderBreadcrumb() {
    const el = this.refs.breadcrumb.el;
    const parts = [{ label: t('All Customer Types'), idx: -1 }, ...this.state.drillPath.map((p, i) => ({ label: p.label, idx: i }))];
    if (parts.length === 1) { el.innerHTML = ''; return; }
    el.innerHTML = parts.map((p, i) => {
      if (i === parts.length - 1) return `<span class="crumb current">${p.label}</span>`;
      return `<span class="crumb" data-idx="${p.idx}">${p.label}</span><span class="crumb-sep">›</span>`;
    }).join('');
    el.querySelectorAll('.crumb[data-idx]').forEach(elm => {
      elm.addEventListener('click', () => this.drillTo(+elm.getAttribute('data-idx')));
    });
  }

  seriesColors() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    return SALES_TYPE_GROUP_COLORS.map(v => style.getPropertyValue(v).trim());
  }

  categoryColors() {
    return this.state.level === 'salesTypeGroup' ? this.seriesColors() : PALETTE;
  }

  async load() {
    this.state.loading = true;
    this.state.error = '';
    try {
      const period = (this.state.year && this.state.month) ? `${this.state.year}-${String(this.state.month).padStart(2, '0')}` : null;
      const res = await this.rpc('/pbi_dashboards/sales_kpi_new/data', {
        period,
        franchise: this.state.franchise,
        customerGroup: this.state.customerGroup,
        salesTypeGroup: this.state.salesTypeGroup,
        drillPath: this.state.drillPath,
        levelFilterCode: this.state.levelFilterSelected,
        viewLevel: this.state.levelOverride,
      });
      if (res.error) { this.state.error = res.error; return; }
      this.lastJson = res;
      this.state.year = res.period.year;
      this.state.month = res.period.month;
      this.state.periodLabel = tDate(res.period.label);
      this.state.hasPrevYear = res.hasPrevYear;
      this.state.yearOptions = res.yearOptions;
      this.state.customerGroupOptions = [{ v: 'all', l: 'All' }, ...res.customerGroupOptions];
      this.state.level = res.level;
      this.state.levelLabel = t(res.levelLabel);
      this.state.canDrillFurther = res.canDrillFurther;
      this.state.levelFilterLabel = t(LEVEL_FILTER_LABELS[res.level] || res.levelLabel);
      this.state.levelFilterOptions = this.buildLevelFilterOptions(res);
      this.state.levelFilterValue = res.level === 'salesTypeGroup' ? this.state.salesTypeGroup : (this.state.levelFilterSelected || 'all');
      this.renderAll();
    } catch (e) {
      this.state.error = t('Failed to load') + ' — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  // 12-tile KPI row for whichever measure is toggled — Amount tiles read
  // the plain sales/budget kpi fields (fmtM display, same as
  // sales_kpi_dashboard.js), Qty tiles read the parallel *Qty kpi fields
  // the same bundle already carries (fmtK display, matching the Qty
  // chart's own formatting) — see sales_kpi_main.py _fetch_bundle's kpis
  // dict for both sets.
  renderKpis() {
    const k = this.lastJson.kpis;
    const isAmount = this.state.measure === 'amount';
    const valueFmt = isAmount ? fmtM : fmtK;
    const rawFmt = fmt;
    const f = { mtdTY: k.mtdThisYear, mtdTar: k.mtdTarget, mtdLY: k.mtdLastYear,
                ytdTY: k.ytdThisYear, ytdTar: k.ytdTarget, ytdLY: k.ytdLastYear };
    const q = { mtdTY: k.mtdQtyThisYear, mtdTar: k.mtdQtyTarget, mtdLY: k.mtdQtyLastYear,
                ytdTY: k.ytdQtyThisYear, ytdTar: k.ytdQtyTarget, ytdLY: k.ytdQtyLastYear };
    const v = isAmount ? f : q;
    const noun = isAmount ? 'Sales' : 'Qty';
    const tiles = [
      { label: t(`MTD - This Year ${noun}`), value: valueFmt(v.mtdTY), raw: rawFmt(v.mtdTY) },
      { label: t(`MTD - Target${isAmount ? '' : ' Qty'}`), value: valueFmt(v.mtdTar), raw: rawFmt(v.mtdTar) },
      { label: t(`MTD - ${noun} vs Target %`), value: fmtPct(pct(v.mtdTY, v.mtdTar)), raw: fmtPctPrecise(pct(v.mtdTY, v.mtdTar)) },
      { label: t(`YTD - This Year ${noun}`), value: valueFmt(v.ytdTY), raw: rawFmt(v.ytdTY) },
      { label: t(`YTD - Target${isAmount ? '' : ' Qty'}`), value: valueFmt(v.ytdTar), raw: rawFmt(v.ytdTar) },
      { label: t(`YTD - ${noun} vs Target %`), value: fmtPct(pct(v.ytdTY, v.ytdTar)), raw: fmtPctPrecise(pct(v.ytdTY, v.ytdTar)) },
      { label: t(`MTD - This Year ${noun}`), value: valueFmt(v.mtdTY), raw: rawFmt(v.mtdTY) },
      { label: t(`MTD - Last Year ${noun}`), value: valueFmt(v.mtdLY), raw: rawFmt(v.mtdLY) },
      { label: t(`MTD - TY ${noun} vs LY ${noun} %`), value: fmtPct(pct(v.mtdTY, v.mtdLY)), raw: fmtPctPrecise(pct(v.mtdTY, v.mtdLY)) },
      { label: t(`YTD - This Year ${noun}`), value: valueFmt(v.ytdTY), raw: rawFmt(v.ytdTY) },
      { label: t(`YTD - Last Year ${noun}`), value: valueFmt(v.ytdLY), raw: rawFmt(v.ytdLY) },
      { label: t(`YTD - TY ${noun} vs LY ${noun} %`), value: fmtPct(pct(v.ytdTY, v.ytdLY)), raw: fmtPctPrecise(pct(v.ytdTY, v.ytdLY)) },
    ];
    this.refs.kpiRow.el.innerHTML = tiles.map((tile, i) => `
      <div class="pbi-kpi tile-color-${i % 6}" data-tip="${tile.label}||${t('Actual')}||${tile.raw}">
        <div class="value">${tile.value}</div>
        <div class="label">${tile.label}</div>
      </div>
    `).join('');
    attachValueTooltips(this.refs.kpiRow.el, '.pbi-kpi[data-tip]');
  }

  // Chart title for the current measure/period — used by the template so
  // "MTD – Sales Amount Analysis" swaps to "MTD – Sales Qty Analysis" (etc)
  // as the toggle changes, same wording as sales_kpi_dashboard.js's fixed
  // per-section titles.
  chartTitle(period, kind) {
    const isAmount = this.state.measure === 'amount';
    const noun = isAmount ? 'Amt' : 'Qty';
    if (kind === 'bar') {
      return isAmount ? t(`${period.toUpperCase()} – Sales Amount Analysis`) : t(`${period.toUpperCase()} – Sales Qty Analysis`);
    }
    return t(`${period.toUpperCase()} – ${noun} Contribution %`);
  }

  // Renders only the MTD/YTD bar+donut pair for the currently toggled
  // measure — the widened-bar/one-donut-per-row layout itself comes from
  // .pbi-card-grid-wide in sales_kpi_dashboard_new.css, this just picks
  // which series/keys/formatter to feed groupedBarChart/donutChart.
  renderCharts() {
    const colors = this.categoryColors();
    const seriesColors = this.seriesColors();
    const barColors = [seriesColors[0], seriesColors[2], seriesColors[1]]; // This Year / Target / Last Year
    const isAmount = this.state.measure === 'amount';
    const seriesKeys = isAmount ? ['sales', 'budget', 'prevYearSales'] : ['qty', 'budgetQty', 'prevYearQty'];
    const seriesLabels = isAmount ? ['This Year Sales', 'Target Sales', 'Last Year Sales'] : ['This Year Qty', 'Target Qty', 'Last Year Qty'];
    const valueFmt = isAmount ? fmtM : fmtK;
    const valueKey = isAmount ? 'sales' : 'qty';
    const onClick = this.state.canDrillFurther ? (code, label) => this.onCategoryClick(code, label) : null;

    groupedBarChart(this.refs.mtdBar.el, this.lastJson.breakdown.mtd, seriesKeys, barColors, seriesLabels, onClick, valueFmt);
    groupedBarChart(this.refs.ytdBar.el, this.lastJson.breakdown.ytd, seriesKeys, barColors, seriesLabels, onClick, valueFmt);
    donutChart(this.refs.mtdDonut.el, this.lastJson.breakdown.mtd.map(d => ({ code: d.code, label: d.label, value: d[valueKey] })), colors, onClick, valueFmt);
    donutChart(this.refs.ytdDonut.el, this.lastJson.breakdown.ytd.map(d => ({ code: d.code, label: d.label, value: d[valueKey] })), colors, onClick, valueFmt);
  }

  renderAll() {
    this.renderBreadcrumb();
    this.renderKpis();
    this.renderCharts();
  }
}

registry.category("actions").add("pbi_dashboards.sales_kpi_dashboard_new", PbiSalesKpiDashboardNew);
