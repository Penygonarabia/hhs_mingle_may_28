/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { t, tDate, addLabels, isArabicUI } from "./pbi_i18n";

// EN -> AR for every static-chrome string this dashboard renders itself:
// the dashboard title, the 12 fixed KPI tile labels, card/chart titles,
// series legends, filter labels/dimension names, drill-nav/breadcrumb
// chrome and footer boilerplate. Generic words shared with other
// dashboards (Year/Month/Franchise/Region/Total/Share/Contribution/
// Actual/...) already live in pbi_i18n.js's own LABELS dict — reused here
// via t(), not re-added. Deliberately EXCLUDED: Customer Type category
// names (Dealers/Modern Trade/Whole Sale/Projects/Others), franchise names
// (Midea/BEKO/CANDY) and any customer-group/drilled-category name that
// comes back from the server — those are real data values, not chrome.
addLabels({
  "Sales Analysis": "تحليل المبيعات",
  "Sales Dashboards": "لوحات معلومات المبيعات",
  "Customer Group": "مجموعة العملاء",
  // level/dimension names (filter caption + level-jump nav singular form)
  "Customer Type": "نوع العميل",
  "Customer Sub-Type": "النوع الفرعي للعميل",
  "Customer": "العميل",
  "Product Group": "مجموعة المنتجات",
  "Product Sub-Group": "المجموعة الفرعية للمنتجات",
  // level-jump nav plural form
  "Customer Types": "أنواع العملاء",
  "Customer Sub-Types": "الأنواع الفرعية للعملاء",
  "Regions": "المناطق",
  "Customers": "العملاء",
  "Product Groups": "مجموعات المنتجات",
  "Product Sub-Groups": "المجموعات الفرعية للمنتجات",
  // breadcrumb root + drill-hint chrome
  "All Customer Types": "كل أنواع العملاء",
  "Grouped by": "مجمّع حسب",
  "click a bar or slice to drill in": "انقر على عمود أو قطاع للتعمق",
  "(deepest level)": "(أعمق مستوى)",
  // filters/level-nav expand-collapse toggle
  "Filters & Levels": "الفلاتر والمستويات",
  // card / chart titles
  "MTD – Sales Amount Analysis": "تحليل قيمة المبيعات – حتى تاريخه (الشهر)",
  "MTD – Amt Contribution %": "نسبة مساهمة القيمة – حتى تاريخه (الشهر)",
  "YTD – Sales Amount Analysis": "تحليل قيمة المبيعات – حتى تاريخه (السنة)",
  "YTD – Amt Contribution %": "نسبة مساهمة القيمة – حتى تاريخه (السنة)",
  "MTD – Sales Qty Analysis": "تحليل كمية المبيعات – حتى تاريخه (الشهر)",
  "MTD – Qty Contribution %": "نسبة مساهمة الكمية – حتى تاريخه (الشهر)",
  "YTD – Sales Qty Analysis": "تحليل كمية المبيعات – حتى تاريخه (السنة)",
  "YTD – Qty Contribution %": "نسبة مساهمة الكمية – حتى تاريخه (السنة)",
  "This Year, Target and Last Year": "هذا العام، الهدف والعام الماضي",
  // grouped-bar series legend
  "This Year Sales": "مبيعات هذا العام",
  "Target Sales": "مبيعات الهدف",
  "Last Year Sales": "مبيعات العام الماضي",
  "This Year Qty": "كمية هذا العام",
  "Target Qty": "كمية الهدف",
  "Last Year Qty": "كمية العام الماضي",
  // the 12 KPI tiles (10 distinct labels — 2 repeat within the row)
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
  // misc
  "Failed to load": "فشل التحميل",
  // Month filter dropdown (same wording as pbi_i18n.js's internal tDate()
  // month map, added here too since these are standalone option labels,
  // not words embedded inside a pre-formatted date string)
  "January": "يناير", "February": "فبراير", "March": "مارس", "April": "أبريل",
  "May": "مايو", "June": "يونيو", "July": "يوليو", "August": "أغسطس",
  "September": "سبتمبر", "October": "أكتوبر", "November": "نوفمبر", "December": "ديسمبر",
});

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

// Truncates a label to "…" once it would overflow the width of its own
// slot (a group's column on the x-axis) — avoids adjacent category labels
// (e.g. long Product Group / Product Sub-Group names) visually overlapping.
// Approximates SVG text width from character count since there's no layout
// pass available before the string is written into the markup; 0.6×fontSize
// matches the average glyph width used elsewhere in this file (donutChart's
// halfAngle estimate uses 5.6px at 9.5px font, i.e. ~0.59×fontSize).
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

// Same data-tip||-split convention as attachBarTooltips, but for elements
// that already carry a fully-formatted display string (KPI tiles, a donut's
// center total) rather than a raw number attachBarTooltips would re-run
// through fmt() itself — used to surface the EXACT value behind a value
// that's shown compact/rounded on-screen (e.g. "5.1M" tile -> "5,123,456"
// tooltip, "9.7%" -> "9.68%").
function attachValueTooltips(el, selector) {
  el.querySelectorAll(selector).forEach(node => {
    node.addEventListener('mousemove', evt => {
      const [label, sub, val] = node.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${sub}: <b>${val}</b>`);
    });
    node.addEventListener('mouseleave', hideTip);
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

// Whole-number, collision-free y-axis ticks for groupedBarChart. The old
// maxVal*i/ticks linear split, rounded through valueFmt's .toFixed(1),
// duplicated labels (e.g. "0.0M" 4x in a row) whenever the data's max was
// under about half a unit — 4 near-equal small numbers all round to the
// same 1-decimal string. Instead this rounds the axis TOP up to a whole
// multiple of the chart's own unit (1e6 for fmtM, 1e3 for fmtK — matched by
// function identity since every real call site passes exactly one of
// those two) and picks a step from a fixed "nice number" ladder so every
// tick is an exact whole unit, and therefore distinct, by construction.
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

// valueFmt always keeps one decimal (e.g. "2.0M") since it's shared with
// the per-bar value callouts, where that decimal matters — but every tick
// from niceAxisTicks is an exact whole unit, so the y-axis specifically
// can drop the always-".0" for a genuinely whole-number label ("2M").
function axisTickLabel(val, valueFmt) {
  return valueFmt(val).replace(/\.0(?=\D|$)/, '');
}

// ---------------------------------------------------------------------
// grouped bar chart — one group per breakdown category, up to 3 series
// (This Year / Target / Last Year). Wide enough that labels never overlap
// — the containing element scrolls horizontally (see .chart-scroll in
// sales_kpi_dashboard.css) instead of compressing categories to fit.
// ---------------------------------------------------------------------
function groupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels, onCategoryClick, valueFmt = fmtCompact) {
  seriesLabels = seriesLabels.map(t);
  // Wide enough per group that a value label (e.g. "0.1M", ~30px at the
  // 8px font below) never overlaps its neighbor — bar centers need to be
  // at least label-width apart, not just visually-distinct bar widths.
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
// donut chart — contribution % of each breakdown category to the total
// shown, drawn with the stroke-dasharray ring trick (avoids arc-path math).
// ---------------------------------------------------------------------
function donutChart(el, data, colors, onCategoryClick, valueFmt = fmtCompact) {
  const total = data.reduce((s, d) => s + (d.value || 0), 0);
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

  if (total <= 0) {
    // Zero total (e.g. a customer/period with Target set but nothing
    // actually invoiced yet) — there's no wedge to draw since there's
    // nothing to split, but the card still renders the same fixed-size
    // ring + legend (muted grey, no slices) instead of collapsing to a
    // one-line message, so it doesn't lose its place in the grid next to
    // its neighboring bar-chart card (see the sizing comment above).
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
// t_cstclasstypedesc-derived customer-type grouping, matching
// sales_kpi_main.py's CUSTOMER_TYPE_FIXED_CODES exactly (Dealers/Modern
// Trade/Whole Sale/Projects/Others, keyed by bi_csttypecode resolved
// against t_cstclasstypedesc) — NOT sales_mail_main.py's t_salpurgroup-based
// CHANNEL_FIXED_CODES (Dealers/Projects/Key Accounts/Corporate Sales), which
// this used to (wrongly) mirror. See sales_kpi_main.py's CUSTOMER_TYPE_EXPR
// docstring for why those two lookups don't interchange.
const SALES_TYPE_GROUP_OPTIONS = [
  { v: 'all', l: 'All' }, { v: 'Dealers', l: 'Dealers' }, { v: 'Modern Trade', l: 'Modern Trade' },
  { v: 'Whole Sale', l: 'Whole Sale' }, { v: 'Projects', l: 'Projects' }, { v: 'Others', l: 'Others' },
];
// Fixed category colors for the un-drilled Customer Type chart, keyed by
// SALES_TYPE_GROUP_OPTIONS order (excluding "All") — once drilled to a
// deeper level, PALETTE above is used by plain position instead. 5 colors
// for the 5 t_cstclasstypedesc categories (one more than the old 4-category
// t_salpurgroup grouping had) — series-5 (violet) is otherwise unused by any
// category swatch in this file, so it's safe to add here without colliding
// with the KPI-tile or "bad"/negative-text meanings series-5/6 carry
// elsewhere in this codebase.
const SALES_TYPE_GROUP_COLORS = ['--series-1', '--series-2', '--series-3', '--series-4', '--series-5'];

// Singular label (matches sales_kpi_main.py's own LEVEL_LABELS wording) for
// the level-filter dropdown's caption — keyed by the same LEVELS the server
// drives state.level with — the dropdown's own label + option list track
// whichever level is currently active, not just its fixed root level. The
// level-jump NAV BUTTONS use the plural LEVEL_NAV_LABELS below instead (a
// tab naming a whole category of things — "Regions" — reads differently
// than a filter caption for a single picked value). "Customer Type"
// (level key "salesTypeGroup") and "Customer" (level key "customer") are
// deliberately distinct levels — the former is the 5-category
// t_cstclasstypedesc grouping, the latter is individual named customers.
const LEVEL_FILTER_LABELS = {
  salesTypeGroup: 'Customer Type', customerSubType: 'Customer Sub-Type', region: 'Region',
  customer: 'Customer', productGroup: 'Product Group', productSubGroup: 'Product Sub-Group',
};
const LEVEL_NAV_LABELS = {
  salesTypeGroup: 'Customer Types', customerSubType: 'Customer Sub-Types', region: 'Regions',
  customer: 'Customers', productGroup: 'Product Groups', productSubGroup: 'Product Sub-Groups',
};

// Same 6-level chain as sales_kpi_main.py's LEVELS, in order — drives the
// level-jump nav buttons (jumpToLevel) so every level is reachable directly,
// not just by drilling through the ones before it. The Salesman level (and
// its level-nav button) was removed entirely at the user's request — to
// bring it back, re-add "salesman" between "customer" and "productGroup"
// below, plus the matching LEVEL_FILTER_LABELS/LEVEL_NAV_LABELS entries
// above and sales_kpi_main.py's LEVELS/LEVEL_COLUMNS/LEVEL_LABELS.
const LEVEL_ORDER = ['salesTypeGroup', 'customerSubType', 'region', 'customer', 'productGroup', 'productSubGroup'];

export class PbiSalesKpiDashboard extends Component {
  static template = "pbi_dashboards.sales_kpi_dashboard";
  static props = ["*"];

  setup() {
    this.rpc = useService("rpc");
    this.franchiseOptions = FRANCHISE_OPTIONS;
    this.monthOptions = MONTH_OPTIONS;

    this.state = useState({
      year: null, month: null, franchise: 'Midea', customerGroup: 'all', salesTypeGroup: 'all',
      loading: false, error: '',
      yearOptions: [], customerGroupOptions: [{ v: 'all', l: 'All' }],
      periodLabel: '', hasPrevYear: false,
      // Shared drill-down path: Customer Type -> Customer Sub-Type -> Region
      // -> Customer -> Product Group -> Product Sub-Group. Drilling in ANY
      // chart pushes one entry here and reloads, which re-filters the KPI
      // tiles AND every other chart to the same path — see load().
      drillPath: [], level: 'salesTypeGroup', levelLabel: t('Customer Type'), canDrillFurther: true,
      // Level-filter dropdown (the old fixed "Sales Type Groups" select) —
      // recomputed on every load() to track the currently drilled level.
      levelFilterLabel: t(LEVEL_FILTER_LABELS.salesTypeGroup),
      levelFilterOptions: SALES_TYPE_GROUP_OPTIONS,
      levelFilterValue: 'all',
      // The dropdown's own pick at the CURRENT level — narrows the charts to
      // one category WITHOUT drilling (see selectLevelFilter). Cleared any
      // time the level itself changes (real drill, breadcrumb nav, or a
      // top filter reset), since it's only meaningful for the level it was
      // picked at.
      levelFilterSelected: null,
      // Set by the level-jump nav (jumpToLevel) to view any of the 7 levels
      // directly — e.g. straight to Regions — without drilling through the
      // levels in between. Sent to the server as-is; cleared (falls back to
      // the natural next-level-after-drillPath) by any real drill, breadcrumb
      // nav, or top-filter change, so the chain resumes normally afterward.
      levelOverride: null,
      // Expand/collapse for the filters row ONLY (see toggleToolbar) — the
      // level-jump nav stays visible regardless, since it's the primary way
      // to move around the drill chain, not just a filter. Collapsing hides
      // the filters row so more chart cards fit on screen at once, without
      // losing the current filter/drill selections underneath.
      toolbarCollapsed: false,
    });
    this.levelNav = LEVEL_ORDER.map(v => ({ v, l: t(LEVEL_NAV_LABELS[v]) }));
    this.t = t;
    this.isArabicUI = isArabicUI;

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

  resetDrill() { this.state.drillPath = []; this.state.levelFilterSelected = null; this.state.levelOverride = null; }

  // Toggles the filters row's collapsed state (see the toolbarCollapsed
  // state comment) — a pure display toggle, no reload, so collapsing/
  // expanding never disturbs the current filters, drill path or loaded
  // chart data. The level-jump nav is unaffected — it never collapses.
  toggleToolbar() { this.state.toolbarCollapsed = !this.state.toolbarCollapsed; }

  selectYear(v) { this.state.year = +v; this.resetDrill(); this.load(); }
  selectMonth(v) { this.state.month = +v; this.resetDrill(); this.load(); }
  selectFranchise(v) { this.state.franchise = v; this.resetDrill(); this.load(); }
  selectCustomerGroup(v) { this.state.customerGroup = v; this.resetDrill(); this.load(); }
  selectSalesTypeGroup(v) { this.state.salesTypeGroup = v; this.resetDrill(); this.load(); }

  // Level-jump nav — view any of the 6 levels directly (e.g. straight to
  // Regions) using whatever's already been drilled/filtered so far, instead
  // of only being able to reach a level by drilling through every one
  // before it. Doesn't touch drillPath: it's a display-only override for
  // grouping (see sales_kpi_main.py _fetch_bundle's view_level), so the
  // breadcrumb and every already-applied filter stay exactly as they were.
  jumpToLevel(level) {
    if (level === this.state.level && !this.state.levelFilterSelected) return;
    this.state.levelOverride = level;
    this.state.levelFilterSelected = null;
    this.load();
  }

  // Handles the dynamic level-filter dropdown: at the root (undrilled)
  // level it's still the fixed Sales Type Group filter (bi_csttypecode via
  // t_salpurgroup), and at any deeper level it lists that level's own
  // categories. Either way, picking a value only NARROWS the charts to that
  // one category — it never drills (moves to the next level). Real
  // drill-down is chart-click-only (see onCategoryClick).
  selectLevelFilter(v) {
    if (this.state.level === 'salesTypeGroup') { this.selectSalesTypeGroup(v); return; }
    this.state.levelFilterSelected = (!v || v === 'all') ? null : v;
    this.load();
  }

  // Builds the level-filter dropdown's options for whatever level the
  // response just loaded: the fixed 4 Sales Type Groups at the root, or the
  // server's levelOptions (always the FULL set of categories at this level,
  // independent of any quick filter already applied — see sales_kpi_main.py
  // _fetch_bundle) at any deeper level.
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

  // Called from any of the 8 charts — drills every chart + the KPI tiles
  // to this category at once (they all reload from the same drillPath).
  onCategoryClick(code, label) {
    if (!this.state.canDrillFurther) return;
    this.state.drillPath = [...this.state.drillPath, { level: this.state.level, code, label }];
    this.state.levelFilterSelected = null;
    this.state.levelOverride = null;
    this.load();
  }

  drillTo(pathIndex) {
    // pathIndex === -1 means back to the root (Sales Type Group) level.
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

  // Category colors for the CURRENT level: the fixed 4-color Sales Type
  // Group palette when actually viewing Sales Type Group (whether at the
  // natural root or jumped straight back to it — see jumpToLevel), PALETTE
  // by position for every other level (which can have far more than 4
  // categories). Keyed off state.level itself rather than drillPath.length
  // since the level-jump nav can show a deeper level with an empty/short
  // drillPath (no dimension picked yet), where drillPath.length alone would
  // wrongly still say "root".
  categoryColors() {
    return this.state.level === 'salesTypeGroup' ? this.seriesColors() : PALETTE;
  }

  async load() {
    this.state.loading = true;
    this.state.error = '';
    try {
      const period = (this.state.year && this.state.month) ? `${this.state.year}-${String(this.state.month).padStart(2, '0')}` : null;
      const res = await this.rpc('/pbi_dashboards/sales_kpi/data', {
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

  renderKpis() {
    const k = this.lastJson.kpis;
    // Every tile's headline number is rounded/compact (fmtM's "5.1M") so the
    // row stays scannable — `raw` carries the exact figure behind it (full
    // comma-grouped amount, or a 2-decimal % vs. the tile's 1-decimal
    // display) for the hover tooltip (attachValueTooltips below).
    const tiles = [
      { label: t('MTD - This Year Sales'), value: fmtM(k.mtdThisYear), raw: fmt(k.mtdThisYear) },
      { label: t('MTD - Target'), value: fmtM(k.mtdTarget), raw: fmt(k.mtdTarget) },
      { label: t('MTD - Sales vs Target %'), value: fmtPct(pct(k.mtdThisYear, k.mtdTarget)), raw: fmtPctPrecise(pct(k.mtdThisYear, k.mtdTarget)) },
      { label: t('YTD - This Year Sales'), value: fmtM(k.ytdThisYear), raw: fmt(k.ytdThisYear) },
      { label: t('YTD - Target'), value: fmtM(k.ytdTarget), raw: fmt(k.ytdTarget) },
      { label: t('YTD - Sales vs Target %'), value: fmtPct(pct(k.ytdThisYear, k.ytdTarget)), raw: fmtPctPrecise(pct(k.ytdThisYear, k.ytdTarget)) },
      { label: t('MTD - This Year Sales'), value: fmtM(k.mtdThisYear), raw: fmt(k.mtdThisYear) },
      { label: t('MTD - Last Year Sales'), value: fmtM(k.mtdLastYear), raw: fmt(k.mtdLastYear) },
      { label: t('MTD - TY Sales vs LY Sales %'), value: fmtPct(pct(k.mtdThisYear, k.mtdLastYear)), raw: fmtPctPrecise(pct(k.mtdThisYear, k.mtdLastYear)) },
      { label: t('YTD - This Year Sales'), value: fmtM(k.ytdThisYear), raw: fmt(k.ytdThisYear) },
      { label: t('YTD - Last Year Sales'), value: fmtM(k.ytdLastYear), raw: fmt(k.ytdLastYear) },
      { label: t('YTD - TY Sales vs LY Sales %'), value: fmtPct(pct(k.ytdThisYear, k.ytdLastYear)), raw: fmtPctPrecise(pct(k.ytdThisYear, k.ytdLastYear)) },
    ];
    this.refs.kpiRow.el.innerHTML = tiles.map((tile, i) => `
      <div class="pbi-kpi tile-color-${i % 6}" data-tip="${tile.label}||${t('Actual')}||${tile.raw}">
        <div class="value">${tile.value}</div>
        <div class="label">${tile.label}</div>
      </div>
    `).join('');
    attachValueTooltips(this.refs.kpiRow.el, '.pbi-kpi[data-tip]');
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
