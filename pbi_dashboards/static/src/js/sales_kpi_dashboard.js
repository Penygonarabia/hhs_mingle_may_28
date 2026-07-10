/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// ---------------------------------------------------------------------
// formatting/tooltip helpers — trimmed copy of the pattern in
// sales_dashboard.js / sales_analysis_dashboard.js (neither file exports
// its helpers, so each dashboard here carries its own small subset).
// ---------------------------------------------------------------------
const fmt = n => n == null ? "–" : new Intl.NumberFormat('en-US').format(Math.round(n));
const fmtM = n => n == null ? "–" : (n / 1e6).toFixed(1) + "M";
const fmtK = n => n == null ? "–" : (n / 1e3).toFixed(1) + "K";
const fmtCompact = n => n == null ? "–" : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(n);
function pct(part, total) { return total > 0 ? (part / total * 100) : null; }
function fmtPct(p) { return p == null ? "–" : p.toFixed(1) + "%"; }

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

function attachBarTooltips(el) {
  el.querySelectorAll('rect[data-tip]').forEach(rect => {
    rect.addEventListener('mousemove', evt => {
      const [label, seriesLabel, val] = rect.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${seriesLabel}: <b>${fmt(+val)}</b>`);
    });
    rect.addEventListener('mouseleave', hideTip);
  });
}

// Single-line legend with a "▶" arrow that scrolls further right when the
// items overflow the available width — same idea as the reference
// PowerBI legend (e.g. "Dealers  Projects  Modern ...  ▶"), instead of
// wrapping onto a second line or shrinking text.
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
  // One button does double duty: "▶" scrolls right while there's more to
  // see, and once at the end it flips to "◀" to jump straight back to the
  // start — row itself has overflow-x:hidden (no trackpad/wheel scrolling,
  // by design, to keep the legend from feeling like a stray scroll area),
  // so this button is the only way to reach either end.
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
  // A single setTimeout(fn, 0) can fire before the browser has committed
  // layout for an element nested inside a sibling "chart-scroll"
  // (overflow-x:auto) container that just became scrollable itself,
  // under-reporting clientWidth and missing real overflow. Double rAF
  // guarantees a layout/paint has happened first.
  requestAnimationFrame(() => requestAnimationFrame(sync));
}

// Wide categorical palette used for donut slices / drilled-in bar groups —
// unlike the fixed 5 Customer Type colors, a drilled-in level (Customer
// Sub-Type, Region, Customer, Product Group/Sub-Group) can have anywhere
// from a handful to 15 categories, so colors are assigned by position
// rather than carrying fixed per-category meaning once drilled in.
const PALETTE = [
  '#2a78d6', '#1baf7a', '#eda100', '#4a3aa7', '#17a2b8',
  '#e34948', '#8e44ad', '#16a085', '#d35400', '#2c3e50',
  '#c0392b', '#27ae60', '#f39c12', '#7f8c8d', '#3498db',
];

// ---------------------------------------------------------------------
// grouped bar chart — one group per breakdown category, up to 3 series
// (This Year / Target / Last Year). Wide enough that labels never overlap
// — the containing element scrolls horizontally (see .chart-scroll in
// sales_kpi_dashboard.css) instead of compressing categories to fit.
// ---------------------------------------------------------------------
function groupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels, onCategoryClick, valueFmt = fmtCompact) {
  // Wide enough per group that a value label (e.g. "0.1M", ~30px at the
  // 8px font below) never overlaps its neighbor — bar centers need to be
  // at least label-width apart, not just visually-distinct bar widths.
  const perGroup = 180;
  const W = Math.max(el.clientWidth || 480, data.length * perGroup), H = 230;
  const marginL = 54, marginR = 10, marginT = 10, marginB = 46;
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const maxVal = Math.max(1, ...data.flatMap(d => seriesKeys.map(k => d[k] || 0))) * 1.12;
  const groupW = plotW / data.length;
  const gap = 6;
  const barW = Math.min(32, (groupW - gap * (seriesKeys.length - 1)) / seriesKeys.length * 0.9);
  const clickable = !!onCategoryClick;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}px" height="${H}">`;
  const ticks = 4;
  for (let i = 0; i <= ticks; i++) {
    const y = marginT + plotH - (plotH * i / ticks);
    const val = maxVal * i / ticks;
    svg += `<line class="gridline" x1="${marginL}" x2="${W - marginR}" y1="${y}" y2="${y}"/>`;
    svg += `<text class="axis-label" x="${marginL - 8}" y="${y + 3}" text-anchor="end">${valueFmt(val)}</text>`;
  }
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
    svg += `<text class="axis-label${clickable ? ' cat-label-clickable' : ''}" data-code="${d.code}" x="${marginL + gi * groupW + groupW / 2}" y="${H - 24}" text-anchor="middle">${d.label}</text>`;
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
// donut chart — contribution % of each breakdown category to the total
// shown, drawn with the stroke-dasharray ring trick (avoids arc-path math).
// ---------------------------------------------------------------------
function donutChart(el, data, colors, onCategoryClick, valueFmt = fmtCompact) {
  const total = data.reduce((s, d) => s + (d.value || 0), 0);
  if (total <= 0) {
    el.innerHTML = `<p class="subtitle">No data for this selection.</p>`;
    return;
  }
  // EVERY slice gets a label pulled out to the same radius and joined to
  // the ring by a leader line (not just small ones) — labels start at
  // their true angle, then an angular collision pass pushes any that are
  // still too close to their neighbor apart, so the connecting line ends
  // up visibly angled/bent exactly where two slices were crowded and
  // straight where there was already room. H is pinned to 230 to match
  // groupedBarChart's fixed SVG height, so a donut card and its
  // neighboring bar-chart card end up the same height (see
  // .pbi-card-grid{align-items:start} — nothing stretches them to match
  // anymore, so a size mismatch here would show as-is).
  const r = 47, thickness = 20;
  const ringOuterR = r + thickness / 2;
  const labelR = ringOuterR + 40;
  const cx = labelR + 18, cy = labelR + 18;
  const W = cx * 2, H = cy * 2;
  const circumference = 2 * Math.PI * r;
  const clickable = !!onCategoryClick;

  const slices = [];
  let cumulative = 0;
  data.forEach((d, i) => {
    const share = (d.value || 0) / total;
    if (share <= 0) return;
    const trueAngle = (cumulative + share / 2) * 2 * Math.PI - Math.PI / 2;
    // ~5.6px/char at the 9.5px donut-label font, plus a small pad —
    // converted to an angular half-width at labelR via the small-angle
    // approximation (arc length / radius).
    const text = (share * 100).toFixed(1) + '%';
    const halfAngle = (text.length * 5.6 / 2 + 4) / labelR;
    slices.push({ code: d.code, label: d.label, share, trueAngle, labelAngle: trueAngle, halfAngle, cumStart: cumulative, colorIdx: i });
    cumulative += share;
  });

  // Angular relaxation: walk the ring twice (forward, then backward) —
  // whenever two neighbors' labels are closer than the sum of their half
  // widths, push the later one out just enough to clear it. Two passes in
  // opposite directions let separation propagate both ways around a
  // cluster instead of only ever pushing forward.
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
    rings.push(`<circle data-code="${s.code}" data-tip="${s.label}||Share||${(s.share * 100).toFixed(1)}" cx="${cx}" cy="${cy}" r="${r}" fill="none"
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
  svg += `<text class="donut-total" x="${cx}" y="${cy - 2}" text-anchor="middle">${valueFmt(total)}</text>`;
  svg += `<text class="donut-total-label" x="${cx}" y="${cy + 16}" text-anchor="middle">Total</text>`;
  svg += `</svg>`;
  el.innerHTML = legendHtml(data.map(d => d.label), data.map((d, i) => colors[i % colors.length])) + svg;
  attachLegendScroll(el);
  el.querySelectorAll('circle[data-tip]').forEach(c => {
    c.addEventListener('mousemove', evt => {
      const [label, , share] = c.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>Contribution: <b>${share}%</b>`);
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
const CUSTOMER_TYPE_OPTIONS = [
  { v: 'all', l: 'All' }, { v: 'Dealers', l: 'Dealers' }, { v: 'Projects', l: 'Projects' },
  { v: 'Modern Trade', l: 'Modern Trade' }, { v: 'Whole Sale', l: 'Whole Sale' }, { v: 'Others', l: 'Others' },
];
// Fixed category colors for the un-drilled Customer Type chart, keyed by
// CUSTOMER_TYPE_OPTIONS order (excluding "All") — once drilled to a deeper
// level, PALETTE above is used by plain position instead.
const CUSTOMER_TYPE_COLORS = ['--series-1', '--series-2', '--series-3', '--series-5', '--series-4'];

export class PbiSalesKpiDashboard extends Component {
  static template = "pbi_dashboards.sales_kpi_dashboard";
  static props = ["*"];

  setup() {
    this.rpc = useService("rpc");
    this.franchiseOptions = FRANCHISE_OPTIONS;
    this.customerTypeOptions = CUSTOMER_TYPE_OPTIONS;

    this.state = useState({
      period: '', franchise: 'all', customerGroup: 'all', customerType: 'all',
      loading: false, error: '',
      periodOptions: [], customerGroupOptions: [{ v: 'all', l: 'All' }],
      periodLabel: '', hasPrevYear: false,
      // Shared drill-down path: Customer Type -> Customer Sub-Type -> Region
      // -> Customer -> Product Group -> Product Sub-Group. Drilling in ANY
      // chart pushes one entry here and reloads, which re-filters the KPI
      // tiles AND every other chart to the same path — see load().
      drillPath: [], level: 'customerType', levelLabel: 'Customer Type', canDrillFurther: true,
    });

    this.rootRef = useRef('root');
    this.refs = {
      kpiRow: useRef('kpiRow'),
      breadcrumb: useRef('breadcrumb'),
      mtdAmountBar: useRef('mtdAmountBar'), mtdAmountDonut: useRef('mtdAmountDonut'),
      ytdAmountBar: useRef('ytdAmountBar'), ytdAmountDonut: useRef('ytdAmountDonut'),
      mtdQtyBar: useRef('mtdQtyBar'), mtdQtyDonut: useRef('mtdQtyDonut'),
      ytdQtyBar: useRef('ytdQtyBar'), ytdQtyDonut: useRef('ytdQtyDonut'),
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

  resetDrill() { this.state.drillPath = []; }

  selectPeriod(v) { this.state.period = v; this.resetDrill(); this.load(); }
  selectFranchise(v) { this.state.franchise = v; this.resetDrill(); this.load(); }
  selectCustomerGroup(v) { this.state.customerGroup = v; this.resetDrill(); this.load(); }
  selectCustomerType(v) { this.state.customerType = v; this.resetDrill(); this.load(); }

  // Called from any of the 8 charts — drills every chart + the KPI tiles
  // to this category at once (they all reload from the same drillPath).
  onCategoryClick(code, label) {
    if (!this.state.canDrillFurther) return;
    this.state.drillPath = [...this.state.drillPath, { level: this.state.level, code, label }];
    this.load();
  }

  drillTo(pathIndex) {
    // pathIndex === -1 means back to the root (Customer Type) level.
    this.state.drillPath = this.state.drillPath.slice(0, pathIndex + 1);
    this.load();
  }

  renderBreadcrumb() {
    const el = this.refs.breadcrumb.el;
    const parts = [{ label: 'All Customer Types', idx: -1 }, ...this.state.drillPath.map((p, i) => ({ label: p.label, idx: i }))];
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
    return CUSTOMER_TYPE_COLORS.map(v => style.getPropertyValue(v).trim());
  }

  // Category colors for the CURRENT level: the fixed 5-color Customer Type
  // palette at the root, PALETTE by position once drilled to any deeper
  // level (which can have far more than 5 categories).
  categoryColors() {
    return this.state.drillPath.length === 0 ? this.seriesColors() : PALETTE;
  }

  async load() {
    this.state.loading = true;
    this.state.error = '';
    try {
      const res = await this.rpc('/pbi_dashboards/sales_kpi/data', {
        period: this.state.period || null,
        franchise: this.state.franchise,
        customerGroup: this.state.customerGroup,
        customerType: this.state.customerType,
        drillPath: this.state.drillPath,
      });
      if (res.error) { this.state.error = res.error; return; }
      this.lastJson = res;
      this.state.period = `${res.period.year}-${String(res.period.month).padStart(2, '0')}`;
      this.state.periodLabel = res.period.label;
      this.state.hasPrevYear = res.hasPrevYear;
      this.state.periodOptions = res.periodOptions;
      this.state.customerGroupOptions = [{ v: 'all', l: 'All' }, ...res.customerGroupOptions];
      this.state.level = res.level;
      this.state.levelLabel = res.levelLabel;
      this.state.canDrillFurther = res.canDrillFurther;
      this.renderAll();
    } catch (e) {
      this.state.error = 'Failed to load — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  renderKpis() {
    const k = this.lastJson.kpis;
    const tiles = [
      { label: 'MTD - This Year Sales', value: fmtM(k.mtdThisYear) },
      { label: 'MTD - Target', value: fmtM(k.mtdTarget) },
      { label: 'MTD - Sales vs Target %', value: fmtPct(pct(k.mtdThisYear, k.mtdTarget)) },
      { label: 'YTD - This Year Sales', value: fmtM(k.ytdThisYear) },
      { label: 'YTD - Target', value: fmtM(k.ytdTarget) },
      { label: 'YTD - Sales vs Target %', value: fmtPct(pct(k.ytdThisYear, k.ytdTarget)) },
      { label: 'MTD - This Year Sales', value: fmtM(k.mtdThisYear) },
      { label: 'MTD - Last Year Sales', value: fmtM(k.mtdLastYear) },
      { label: 'MTD - TY Sales vs LY Sales %', value: fmtPct(pct(k.mtdThisYear, k.mtdLastYear)) },
      { label: 'YTD - This Year Sales', value: fmtM(k.ytdThisYear) },
      { label: 'YTD - Last Year Sales', value: fmtM(k.ytdLastYear) },
      { label: 'YTD - TY Sales vs LY Sales %', value: fmtPct(pct(k.ytdThisYear, k.ytdLastYear)) },
    ];
    this.refs.kpiRow.el.innerHTML = tiles.map((t, i) => `
      <div class="pbi-kpi tile-color-${i % 6}">
        <div class="value">${t.value}</div>
        <div class="label">${t.label}</div>
      </div>
    `).join('');
  }

  renderAmountSection() {
    const colors = this.categoryColors();
    const seriesColors = this.seriesColors();
    const barColors = [seriesColors[0], seriesColors[2], seriesColors[1]]; // This Year / Target / Last Year
    const seriesLabels = ['This Year Sales', 'Target Sales', 'Last Year Sales'];
    const onClick = this.state.canDrillFurther ? (code, label) => this.onCategoryClick(code, label) : null;
    // Amount values always render in "M" (fmtM), never auto-switching to
    // "K" for smaller bars/slices — Contribution % donuts and bar charts
    // in this section are money, and a chart mixing "5.8M" next to "64.6K"
    // in the same axis reads as inconsistent/broken.
    groupedBarChart(this.refs.mtdAmountBar.el, this.lastJson.breakdown.mtd, ['sales', 'budget', 'prevYearSales'], barColors, seriesLabels, onClick, fmtM);
    groupedBarChart(this.refs.ytdAmountBar.el, this.lastJson.breakdown.ytd, ['sales', 'budget', 'prevYearSales'], barColors, seriesLabels, onClick, fmtM);
    donutChart(this.refs.mtdAmountDonut.el, this.lastJson.breakdown.mtd.map(d => ({ code: d.code, label: d.label, value: d.sales })), colors, onClick, fmtM);
    donutChart(this.refs.ytdAmountDonut.el, this.lastJson.breakdown.ytd.map(d => ({ code: d.code, label: d.label, value: d.sales })), colors, onClick, fmtM);
  }

  renderQtySection() {
    const colors = this.categoryColors();
    const seriesColors = this.seriesColors();
    const barColors = [seriesColors[0], seriesColors[2], seriesColors[1]]; // This Year / Target / Last Year
    const seriesLabels = ['This Year Qty', 'Target Qty', 'Last Year Qty'];
    const onClick = this.state.canDrillFurther ? (code, label) => this.onCategoryClick(code, label) : null;
    // Qty values always render in "K" (fmtK), never auto-switching to a
    // bare number below 1000 — same reasoning as fmtM for Amount: a chart
    // mixing "3.3K" next to a bare "111" in the same axis reads as
    // inconsistent/broken.
    groupedBarChart(this.refs.mtdQtyBar.el, this.lastJson.breakdown.mtd, ['qty', 'budgetQty', 'prevYearQty'], barColors, seriesLabels, onClick, fmtK);
    groupedBarChart(this.refs.ytdQtyBar.el, this.lastJson.breakdown.ytd, ['qty', 'budgetQty', 'prevYearQty'], barColors, seriesLabels, onClick, fmtK);
    donutChart(this.refs.mtdQtyDonut.el, this.lastJson.breakdown.mtd.map(d => ({ code: d.code, label: d.label, value: d.qty })), colors, onClick, fmtK);
    donutChart(this.refs.ytdQtyDonut.el, this.lastJson.breakdown.ytd.map(d => ({ code: d.code, label: d.label, value: d.qty })), colors, onClick, fmtK);
  }

  renderAll() {
    this.renderBreadcrumb();
    this.renderKpis();
    this.renderAmountSection();
    this.renderQtySection();
  }
}

registry.category("actions").add("pbi_dashboards.sales_kpi_dashboard", PbiSalesKpiDashboard);
