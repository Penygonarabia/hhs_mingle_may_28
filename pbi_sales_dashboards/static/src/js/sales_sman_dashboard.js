/** @odoo-module **/

import { Component, useState, useRef, onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { t, addLabels, isArabicUI } from "@pbi_dashboards/js/pbi_i18n";
// These come from the shared chart library rather than being copied in: this
// file carries its own groupedBarChart, but anything that has to MEASURE real
// rendered text — fitting a caption to its slot, sizing a chart to its value
// labels, spreading donut labels apart — has one implementation, and it lives
// there.
import { fitCaptionsToSlot, markAllCaptionsForTooltip, attachCaptionTooltips,
         setTooltipEl, clearTooltipEl, attachLegendFilter,
         labelFont, textWidth, widestValueLabel, spreadDonutLabels,
         VALUE_LABEL_GAP } from "@pbi_dashboards/js/pbi_chart_lib";
// The right-click / long-press level picker. Shared, and knows nothing about
// this chain: it is handed the eleven levels and a callback, and it draws a menu.
import { attachDrillMenu, closeDrillMenu } from "@pbi_dashboards/js/pbi_drill_menu";


// "Sales Dashboard With Salesman" — same chrome and interaction model as
// sales_kpi_dashboard_new.js (Amount/Qty toggle, one wide bar + its donut per
// MTD/YTD row, shared drill path across every chart), on a different source:
// transaction_header/transaction_details for actuals and v_sales_budget_month
// for targets, with TEN drill levels instead of six plus a Regular/Manager
// switch for the category levels. See controllers/sales_sman_main.py.
addLabels({
  "Sales Dashboard With Salesman": "لوحة المبيعات مع المندوب",
  "Amount": "القيمة",
  "Quantity": "الكمية",
  "Sales Type Group": "مجموعة نوع المبيعات",
  "Partner Classification": "تصنيف الشريك",
  "Region": "منطقة",
  "City": "المدينة",
  "Salesman": "المندوب",
  "Customer": "العميل",
  "Main Category": "الفئة الرئيسية",
  "Sub Category": "الفئة الفرعية",
  "Merged Categories": "الفئات المدمجة",
  "Product Group": "مجموعة المنتجات",
  "Product Sub-Group": "المجموعة الفرعية للمنتجات",
  "Sales Type Groups": "مجموعات نوع المبيعات",
  "Partner Classifications": "تصنيفات الشركاء",
  "Regions": "المناطق",
  "Cities": "المدن",
  "Salesmen": "المندوبون",
  "Customers": "العملاء",
  "Main Categories": "الفئات الرئيسية",
  "Sub Categories": "الفئات الفرعية",
  "Product Groups": "مجموعات المنتجات",
  "Product Sub-Groups": "المجموعات الفرعية للمنتجات",
  "Sub-category View": "عرض الفئة الفرعية",
  "Regular": "عادي",
  "Manager": "مدير",
  "Unassigned": "غير مخصص",
  "Others": "أخرى",
  "Filters & Levels": "الفلاتر والمستويات",
  "Filtered by": "مُصفّى حسب",
  "Clear all": "مسح الكل",
  "Reset": "إعادة تعيين",
  "All": "الكل",
  "Year": "السنة",
  "Month": "الشهر",
  "This Year, Target and Last Year": "هذا العام، الهدف والعام الماضي",
  "Scope": "النطاق",
  "AC product groups": "مجموعات منتجات التكييف",
  "Show all": "عرض الكل",
  "This Year and Last Year — no target at this level": "هذا العام والعام الماضي — لا يوجد هدف عند هذا المستوى",
  // Kept alongside the sentence above, which is still the fallback when the
  // server offers no reason. The reasons are separate keys rather than one
  // formatted string so each reads as Arabic rather than as a template.
  "This Year and Last Year — no target": "هذا العام والعام الماضي — لا يوجد هدف",
  "(allocated)": "(موزّع)",
  "target allocated from": "الهدف موزّع من",
  "by last year's mix": "حسب توزيع العام الماضي",
  "the budget is not captured per salesman": "الموازنة غير مسجلة على مستوى المندوب",
  "the budget is not captured per product sub-group": "الموازنة غير مسجلة على مستوى المجموعة الفرعية للمنتج",
  "No target at this level": "لا يوجد هدف عند هذا المستوى",
  "This Year Sales": "مبيعات هذا العام",
  "Target Sales": "مبيعات الهدف",
  "Last Year Sales": "مبيعات العام الماضي",
  "This Year Qty": "كمية هذا العام",
  "Target Qty": "كمية الهدف",
  "Last Year Qty": "كمية العام الماضي",
  "Failed to load": "فشل التحميل",
  "January": "يناير", "February": "فبراير", "March": "مارس", "April": "أبريل",
  "May": "مايو", "June": "يونيو", "July": "يوليو", "August": "أغسطس",
  "September": "سبتمبر", "October": "أكتوبر", "November": "نوفمبر", "December": "ديسمبر",
});

// Exported for "Sales Dashboard - VQ" (sales_vq_dashboard.js), which draws the
// same numbers in both units at once and so needs both formatters -- and the
// exact one, for its table view, where a chart's rounded 7.4M becomes the
// figure it stands for.
export const fmt = n => n == null ? "–" : new Intl.NumberFormat('en-US').format(Math.round(n));
export const fmtM = n => n == null ? "–" : (n / 1e6).toFixed(1) + "M";
export const fmtK = n => n == null ? "–" : (n / 1e3).toFixed(1) + "K";
const fmtCompact = n => n == null ? "–" : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(n);
function pct(part, total) { return total > 0 ? (part / total * 100) : null; }
function fmtPct(p) { return p == null ? "–" : p.toFixed(1) + "%"; }
function fmtPctPrecise(p) { return p == null ? "–" : p.toFixed(2) + "%"; }
// Breakdowns arrive ordered by amount descending. A Qty panel needs its own
// qty-descending order; sort a shallow copy so the Amount chart is untouched.
function byQtyDesc(rows) { return [...rows].sort((a, b) => (b.qty || 0) - (a.qty || 0)); }

let tooltipEl = null;
function showTip(evt, html) {
  if (!tooltipEl) return;
  tooltipEl.innerHTML = html;
  tooltipEl.classList.add('show');
  moveTip(evt);
}
function moveTip(evt) {
  if (!tooltipEl) return;
  tooltipEl.style.left = (evt.clientX + 14) + 'px';
  tooltipEl.style.top = (evt.clientY + 14) + 'px';
}
function hideTip() { if (tooltipEl) tooltipEl.classList.remove('show'); }

function truncateLabel(text, maxWidth, fontSize = 10) {
  if (!text) return text;
  const maxChars = Math.max(1, Math.floor(maxWidth / (fontSize * 0.6)));
  return text.length <= maxChars ? text : text.slice(0, Math.max(1, maxChars - 1)) + '…';
}
// Bars and, since lineChart draws the same figures as points, its dots: the
// tooltip says the same three or four things either way, so the two shapes
// share one binder rather than one growing a second copy of it.
function attachBarTooltips(el) {
  el.querySelectorAll('rect[data-tip], circle.line-dot[data-tip]').forEach(node => {
    node.addEventListener('mousemove', evt => {
      // A fourth part is the contribution %, and only the series the chart
      // shares out carries one — see groupedBarChart's shareKey. Charts that
      // pass three parts get the tooltip they always got.
      const [label, seriesLabel, val, share] = node.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${seriesLabel}: <b>${fmt(+val)}</b>` +
                   (share ? `<br>${t('Contribution')}: <b>${share}%</b>` : ''));
    });
    node.addEventListener('mouseleave', hideTip);
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
    `<div class="item" data-legend-idx="${i}"><span class="swatch" style="background:${colors[i]}"></span>${l}</div>`).join('');
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
  for (const s of ladder) { if (Math.ceil(maxUnits / s) <= 5) { step = s; break; } }
  const niceMaxUnits = Math.ceil(maxUnits / step) * step;
  const ticks = [];
  for (let u = 0; u <= niceMaxUnits; u += step) ticks.push(u * unit);
  return ticks;
}
const axisTickLabel = (val, valueFmt) => valueFmt(val).replace(/\.0(?=\D|$)/, '');

// Every chart below takes the same `opts.drillMenu` and hands it here after
// writing its marks: the spec the board built (its eleven levels, where it is now,
// what to do with a choice) plus the one thing only the chart knows — which row
// a data-code stands for, what it is worth on THIS chart, and what colour it
// was drawn in.
//
// Returning null for a row is how a mark opts out. "Others" does: it is the
// roll-up of every category under the bar cap, so there is no single value to
// open at another level, and a menu whose every entry would lie is worse than
// no menu. Same rule, same code, as onCategoryClick's own guard.
function wireDrillMenu(el, drillMenu, data, describe) {
  if (!drillMenu) return;
  attachDrillMenu(el, Object.assign({}, drillMenu, {
    contextFor: code => {
      const i = data.findIndex(d => String(d.code) === String(code));
      if (i < 0) return null;
      const row = data[i];
      if (String(row.code) === OTHERS_CODE) return null;
      return describe(row, i);
    },
  }));
}

export function groupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels,
                                onCategoryClick, valueFmt = fmtCompact, opts = {}) {
  // shareKey names the series this chart shares out — each category's slice of
  // it, printed under the caption and repeated in that series' tooltip. It is
  // the number the donut beside this chart used to carry, and the boards that
  // still have their donut pass neither option and are unchanged.
  //
  // height is here because "Sales Dashboard - VQ" draws the same chart twice at
  // two sizes: in its card, and filling a full-page panel. An options object
  // rather than a ninth positional argument, which is where this was heading.
  //
  // shareTotal is the whole those shares are taken against. It defaults to the
  // rows on screen, which is right wherever the chart carries every category —
  // including an Others bar for the ones too small to name. A caller that draws
  // only part of the whole (a top-ten with no Others) must pass the real total
  // instead, or ten bars would be reported as 100% of themselves.
  const { shareKey = null, height = 230, shareTotal: shareTotalOpt = null,
          drillMenu = null } = opts;
  seriesLabels = seriesLabels.map(t);
  const isTotalRow = d => d && (d.code === 'Total' || d.label === 'Total');
  const nonTotalData = data.filter(d => !isTotalRow(d));
  const totalRow = data.find(isTotalRow);
  const shareTotal = !shareKey ? 0
    : (shareTotalOpt != null ? shareTotalOpt
       : (totalRow && totalRow[shareKey] != null
          ? totalRow[shareKey]
          : nonTotalData.reduce((sum, d) => sum + (d[shareKey] || 0), 0)));
  const shareOf = d => (isTotalRow(d) || !shareTotal) ? null : (d[shareKey] || 0) / shareTotal * 100;
  // House chart design, shared with pbi_chart_lib's groupedBarChart: sets sit
  // close together, the bars inside a set are held apart, and the bars grow to
  // use a filled width instead of letting it become gap. How WIDE a set has to
  // be is decided by the value labels, which are centred on the bar and as
  // wide as their text — see widestValueLabel.
  const H = height;
  const marginL = 54, marginR = 10, marginT = 10, marginB = 46;
  const gap = 9;
  const nSeries = Math.max(seriesKeys.length, 1);
  const labelPitch = widestValueLabel(el, data, seriesKeys, valueFmt) + VALUE_LABEL_GAP;
  const perGroup = Math.max(100, Math.ceil(nSeries * labelPitch + gap));
  // Margins sit OUTSIDE the plot, so they go on top of the groups rather than
  // being eaten out of them.
  const W = Math.max(el.clientWidth || 480, data.length * perGroup + marginL + marginR);
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const maxRaw = Math.max(1, ...data.flatMap(d => seriesKeys.map(k => d[k] || 0)));
  const tickVals = niceAxisTicks(maxRaw, valueFmt);
  const maxVal = tickVals[tickVals.length - 1];
  const groupW = plotW / Math.max(data.length, 1);
  const slotW = (groupW - gap * (nSeries - 1)) / nSeries;
  // 0.73 is the preferred fill, not a cap: spare room goes into the bar before
  // the chart has to get wider. barPitch stays separate from barW so the 120px
  // cap cannot pull two labels back into each other.
  const barW = Math.min(120, slotW, Math.max(slotW * 0.73, labelPitch - gap));
  const barPitch = Math.max(barW + gap, labelPitch);
  const blockW = (nSeries - 1) * barPitch + barW;
  const clickable = !!onCategoryClick;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}px" height="${H}">`;
  tickVals.forEach(val => {
    const y = marginT + plotH - (plotH * val / maxVal);
    svg += `<line class="gridline" x1="${marginL}" x2="${W - marginR}" y1="${y}" y2="${y}"/>`;
    svg += `<text class="axis-label" x="${marginL - 8}" y="${y + 3}" text-anchor="end">${axisTickLabel(val, valueFmt)}</text>`;
  });
  svg += `<line class="baseline" x1="${marginL}" x2="${W - marginR}" y1="${marginT + plotH}" y2="${marginT + plotH}"/>`;
  data.forEach((d, gi) => {
    const groupX = marginL + gi * groupW + groupW / 2 - blockW / 2;
    seriesKeys.forEach((k, si) => {
      const val = d[k] || 0;
      const barH = plotH * (val / maxVal);
      const x = groupX + si * barPitch;
      const y = marginT + plotH - barH;
      const share = k === shareKey ? shareOf(d) : null;
      const tip = `${d.label}||${seriesLabels[si]}||${val}` +
                  (share == null ? '' : `||${share.toFixed(1)}`);
      svg += `<rect data-code="${d.code}" data-series-idx="${si}" data-tip="${tip}" rx="2" ry="2" x="${x}" y="${y}" width="${barW}" height="${Math.max(barH, 1)}" fill="${seriesColors[si]}" style="${clickable ? 'cursor:pointer' : ''}"/>`;
      svg += `<text class="bar-value" data-series-idx="${si}" x="${x + barW / 2}" y="${y - 3}" text-anchor="middle">${valueFmt(val)}</text>`;
    });
    const label = truncateLabel(d.label, groupW - 8);
    const capX = marginL + gi * groupW + groupW / 2;
    svg += `<text class="axis-label${clickable ? ' cat-label-clickable' : ''}" data-code="${d.code}" x="${capX}" y="${H - 24}" text-anchor="middle"><title>${d.label}</title>${label}</text>`;
    // Under the caption rather than over the bar: it belongs to the category,
    // not to one of its three bars, and over the bar it would collide with the
    // value label already there. No <title> and no .axis-label class, so the
    // caption-fitting pass leaves it alone.
    const share = shareOf(d);
    if (share != null) {
      svg += `<text class="bar-share" x="${capX}" y="${H - 9}" text-anchor="middle">${share.toFixed(1)}%</text>`;
    }
  });
  svg += `</svg>`;
  el.innerHTML = legendHtml(seriesLabels, seriesColors) + svg;
  attachBarTooltips(el);
  // truncateLabel above sizes captions by a per-character estimate, which
  // under-counts uppercase; this trims anything still over its slot against
  // the real glyph widths and gives every cut caption its full text on hover.
  fitCaptionsToSlot(el, groupW - 8);
  markAllCaptionsForTooltip(el);
  attachCaptionTooltips(el);
  attachLegendScroll(el);
  attachLegendFilter(el, 'bar');
  if (onCategoryClick) {
    el.querySelectorAll('[data-code]').forEach(elm => {
      elm.addEventListener('click', () => {
        const row = data.find(d => String(d.code) === elm.getAttribute('data-code'));
        if (row) onCategoryClick(row.code, row.label);
      });
    });
  }
  // Bound to the same [data-code] marks the click above uses -- the bar AND
  // its caption -- but independently of onCategoryClick: at the last level of
  // the chain there is nothing to drill INTO and the click handler is null,
  // while "open this product sub-group by city" is still a fair question.
  //
  const thisYearIdx = shareKey ? seriesKeys.indexOf(shareKey) : 0;
  const valIdx = thisYearIdx >= 0 ? thisYearIdx : 0;
  wireDrillMenu(el, drillMenu, data, row => ({
    label: row.label,
    valueText: valueFmt(row[seriesKeys[valIdx]] || 0),
    color: seriesColors[valIdx],
  }));
}

// opts.total is the period's REAL whole, for the levels where the rows beside
// this donut are a top ten rather than every category. Without it the ring
// would draw ten slices as a full circle and print their subtotal in the middle
// under the word "Total" — a part-to-whole chart quietly restating the part as
// the whole. Given it, the slices are shares of the real total and the rest of
// the ring is simply left unfilled: the gap says "not shown" without inventing
// an Others category the board deliberately dropped.
function donutChart(el, data, colors, onCategoryClick, valueFmt = fmtCompact,
                    opts = {}) {
  const shown = data.reduce((s, d) => s + (d.value || 0), 0);
  const total = Math.max(shown, opts.total || 0);
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
    svg += `<text class="donut-total-label" x="${cx}" y="${cy + 16}" text-anchor="middle">${t('Total')}</text></svg>`;
    el.innerHTML = legendHtml(data.map(d => d.label), data.map(() => 'var(--grid)')) + svg;
    attachLegendScroll(el);
    attachValueTooltips(el, '.donut-total-hit[data-tip]');
    return;
  }

  const donutFont = labelFont(el, 'donut-label', '600 9.5px sans-serif');
  const slices = [];
  let cumulative = 0;
  data.forEach((d, i) => {
    const share = (d.value || 0) / total;
    if (share <= 0) return;
    const trueAngle = (cumulative + share / 2) * 2 * Math.PI - Math.PI / 2;
    const text = (share * 100).toFixed(1) + '%';
    const halfAngle = (textWidth(text, donutFont) / 2 + 4) / labelR;
    slices.push({ code: d.code, label: d.label, share, trueAngle, labelAngle: trueAngle, halfAngle, cumStart: cumulative, colorIdx: i });
    cumulative += share;
  });
  spreadDonutLabels(slices);
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  // Drawn first, so wherever the slices do not reach it stays visible as the
  // uncovered part of the whole. On every level whose rows carry the total the
  // slices cover it completely and this is never seen.
  const rings = [`<circle cx="${cx}" cy="${cy}" r="${r}" fill="none"
              stroke="var(--grid)" stroke-width="${thickness}"/>`];
  const labels = [];
  slices.forEach(s => {
    const segLen = s.share * circumference;
    rings.push(`<circle data-code="${s.code}" data-slice-idx="${s.colorIdx}" data-tip="${s.label}||${t('Share')}||${(s.share * 100).toFixed(1)}" cx="${cx}" cy="${cy}" r="${r}" fill="none"
              stroke="${colors[s.colorIdx % colors.length]}" stroke-width="${thickness}"
              stroke-dasharray="${segLen} ${circumference - segLen}" stroke-dashoffset="${-s.cumStart * circumference}"
              style="${clickable ? 'cursor:pointer' : ''}" transform="rotate(-90 ${cx} ${cy})"/>`);
    const cosA = Math.cos(s.trueAngle), sinA = Math.sin(s.trueAngle);
    const cosL = Math.cos(s.labelAngle), sinL = Math.sin(s.labelAngle);
    labels.push(`<line class="donut-leader" data-slice-label-idx="${s.colorIdx}" x1="${cx + cosA * (ringOuterR + 2)}" y1="${cy + sinA * (ringOuterR + 2)}" x2="${cx + cosL * (labelR - 9)}" y2="${cy + sinL * (labelR - 9)}"/>`);
    labels.push(`<text class="donut-label" data-slice-label-idx="${s.colorIdx}" x="${cx + cosL * labelR}" y="${cy + sinL * labelR}" text-anchor="middle">${(s.share * 100).toFixed(1)}%</text>`);
  });
  svg += rings.join('') + labels.join('');
  svg += `<circle class="donut-total-hit" data-tip="${t('Total')}||${t('Actual')}||${fmt(total)}" cx="${cx}" cy="${cy}" r="${r - thickness / 2}" fill="transparent"/>`;
  svg += `<text class="donut-total" x="${cx}" y="${cy - 2}" text-anchor="middle">${valueFmt(total)}</text>`;
  svg += `<text class="donut-total-label" x="${cx}" y="${cy + 16}" text-anchor="middle">${t('Total')}</text></svg>`;
  el.innerHTML = legendHtml(data.map(d => d.label), data.map((d, i) => colors[i % colors.length])) + svg;
  attachLegendScroll(el);
  attachValueTooltips(el, '.donut-total-hit[data-tip]');
  attachLegendFilter(el, 'donut');
  // The ring's own hit area carries no data-code, so the selector cannot
  // match it and the menu never opens on "Total".
  wireDrillMenu(el, opts.drillMenu, data, (row, i) => ({
    label: row.label,
    valueText: valueFmt(row.value || 0),
    color: colors[i % colors.length],
  }));
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

// The other two shapes the VQ board's chart-type picker can draw, beside
// groupedBarChart above. They live here, with the bar chart and the donut,
// because they need the same private helpers this file already carries — the
// tick ladder that reads its unit off fmtM/fmtK, the caption fitter, the
// legend — and a copy of those in the VQ file would be a second set to keep
// in step. Only the VQ board calls them today.

// One wedge per category, over the measure the card is drawn on. `opts.total`
// is the period's real whole, exactly as in donutChart: on a ranked level the
// rows are a top ten, and the circle is left part-empty rather than restating
// ten categories as the whole of anything. `opts.valueKey` names the series
// shared out — the This Year one, since a pie of three overlapping series is
// not a chart anybody can read.
export function pieChart(el, data, onCategoryClick, valueFmt = fmtCompact, opts = {}) {
  const { valueKey = 'amount', total: totalOpt = 0, height = 230,
          drillMenu = null } = opts;
  const rows = data.map((d, i) => ({ code: d.code, label: d.label, value: d[valueKey] || 0, colorIdx: i }));
  const shown = rows.reduce((sum, d) => sum + d.value, 0);
  const total = Math.max(shown, totalOpt || 0);
  const clickable = !!onCategoryClick;
  // Leave room for the value under the biggest slices and keep the circle
  // inside whatever height the card gave us.
  const r = Math.max(52, Math.round((height - 40) / 2));
  const cx = r + 12, cy = r + 12, W = cx * 2, H = cy * 2;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  // Drawn first: wherever the wedges do not reach, this is the part of the
  // whole that is not on screen.
  svg += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="var(--grid)"/>`;
  if (total > 0) {
    let cumulative = 0;
    rows.forEach(d => {
      const share = d.value / total;
      if (share <= 0) return;
      const a0 = cumulative * 2 * Math.PI - Math.PI / 2;
      const a1 = (cumulative + share) * 2 * Math.PI - Math.PI / 2;
      cumulative += share;
      const x0 = cx + Math.cos(a0) * r, y0 = cy + Math.sin(a0) * r;
      const x1 = cx + Math.cos(a1) * r, y1 = cy + Math.sin(a1) * r;
      const large = share > 0.5 ? 1 : 0;
      // A full circle has no arc to draw -- start and end land on the same
      // point, and the path would collapse to nothing.
      const path = share >= 0.999
        ? `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r} Z`
        : `M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z`;
      svg += `<path class="pie-slice" data-code="${d.code}" data-slice-idx="${d.colorIdx}" data-tip="${d.label}||${t('Share')}||${(share * 100).toFixed(1)}" d="${path}" fill="${PALETTE[d.colorIdx % PALETTE.length]}" style="${clickable ? 'cursor:pointer' : ''}"/>`;
      // Inside the wedge, and only where it fits: a leader line per slice is
      // what the donut needs because its middle is taken, and a pie's is not.
      if (share >= 0.05) {
        const mid = (a0 + a1) / 2;
        svg += `<text class="pie-label" data-slice-label-idx="${d.colorIdx}" x="${cx + Math.cos(mid) * r * 0.62}" y="${cy + Math.sin(mid) * r * 0.62 + 4}" text-anchor="middle">${(share * 100).toFixed(1)}%</text>`;
      }
    });
  }
  svg += `</svg>`;
  el.innerHTML = legendHtml(rows.map(d => d.label), rows.map(d => PALETTE[d.colorIdx % PALETTE.length])) + svg;
  attachLegendScroll(el);
  attachLegendFilter(el, 'pie');
  wireDrillMenu(el, drillMenu, rows, (row, i) => ({
    label: row.label,
    valueText: valueFmt(row.value || 0),
    color: PALETTE[i % PALETTE.length],
  }));
  el.querySelectorAll('.pie-slice[data-tip]').forEach(c => {
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

// The bar chart's data as lines instead of bars, one per series, over the same
// axis, the same slot centres and the same captions — so switching a card from
// bars to lines moves nothing sideways. `opts.area` fills under each line.
//
// No value label over each point, which the bars do carry: three series across
// ten categories is thirty numbers, and a line chart is read for its shape.
// The point's own tooltip has the figure, and the table view has all of them.
export function lineChart(el, data, seriesKeys, seriesColors, seriesLabels,
                          onCategoryClick, valueFmt = fmtCompact, opts = {}) {
  const { shareKey = null, height = 230, shareTotal: shareTotalOpt = null,
          area = false, drillMenu = null } = opts;
  seriesLabels = seriesLabels.map(t);
  const isTotalRow = d => d && (d.code === 'Total' || d.label === 'Total');
  const nonTotalData = data.filter(d => !isTotalRow(d));
  const totalRow = data.find(isTotalRow);
  const shareTotal = !shareKey ? 0
    : (shareTotalOpt != null ? shareTotalOpt
       : (totalRow && totalRow[shareKey] != null
          ? totalRow[shareKey]
          : nonTotalData.reduce((sum, d) => sum + (d[shareKey] || 0), 0)));
  const shareOf = d => (isTotalRow(d) || !shareTotal) ? null : (d[shareKey] || 0) / shareTotal * 100;
  const perGroup = 100;
  const W = Math.max(el.clientWidth || 480, data.length * perGroup), H = height;
  const marginL = 54, marginR = 10, marginT = 10, marginB = 46;
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const maxRaw = Math.max(1, ...data.flatMap(d => seriesKeys.map(k => d[k] || 0)));
  const tickVals = niceAxisTicks(maxRaw, valueFmt);
  const maxVal = tickVals[tickVals.length - 1];
  const groupW = plotW / Math.max(data.length, 1);
  const clickable = !!onCategoryClick;
  const baseY = marginT + plotH;
  const xOf = gi => marginL + gi * groupW + groupW / 2;
  const yOf = val => baseY - plotH * ((val || 0) / maxVal);

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}px" height="${H}">`;
  tickVals.forEach(val => {
    const y = yOf(val);
    svg += `<line class="gridline" x1="${marginL}" x2="${W - marginR}" y1="${y}" y2="${y}"/>`;
    svg += `<text class="axis-label" x="${marginL - 8}" y="${y + 3}" text-anchor="end">${axisTickLabel(val, valueFmt)}</text>`;
  });
  svg += `<line class="baseline" x1="${marginL}" x2="${W - marginR}" y1="${baseY}" y2="${baseY}"/>`;

  seriesKeys.forEach((k, si) => {
    const pts = data.map((d, gi) => `${xOf(gi)},${yOf(d[k])}`).join(' ');
    if (!data.length) return;
    if (area) {
      // Filled to the baseline and stacked on nothing: the three series are
      // this year, its target and last year, which overlap by design rather
      // than adding up, so a stacked area would invent a total.
      svg += `<polygon class="area-fill" data-series-idx="${si}" points="${xOf(0)},${baseY} ${pts} ${xOf(data.length - 1)},${baseY}" fill="${seriesColors[si]}"/>`;
    }
    svg += `<polyline class="line-path" data-series-idx="${si}" points="${pts}" fill="none" stroke="${seriesColors[si]}"/>`;
    data.forEach((d, gi) => {
      const val = d[k] || 0;
      const share = k === shareKey ? shareOf(d) : null;
      const tip = `${d.label}||${seriesLabels[si]}||${val}` +
                  (share == null ? '' : `||${share.toFixed(1)}`);
      svg += `<circle class="line-dot" data-series-idx="${si}" data-code="${d.code}" data-tip="${tip}" cx="${xOf(gi)}" cy="${yOf(val)}" r="3.4" fill="${seriesColors[si]}" style="${clickable ? 'cursor:pointer' : ''}"/>`;
    });
  });

  data.forEach((d, gi) => {
    const capX = xOf(gi);
    svg += `<text class="axis-label${clickable ? ' cat-label-clickable' : ''}" data-code="${d.code}" x="${capX}" y="${H - 24}" text-anchor="middle"><title>${d.label}</title>${truncateLabel(d.label, groupW - 8)}</text>`;
    const share = shareOf(d);
    if (share != null) {
      svg += `<text class="bar-share" x="${capX}" y="${H - 9}" text-anchor="middle">${share.toFixed(1)}%</text>`;
    }
  });
  svg += `</svg>`;
  el.innerHTML = legendHtml(seriesLabels, seriesColors) + svg;
  attachBarTooltips(el);
  fitCaptionsToSlot(el, groupW - 8);
  markAllCaptionsForTooltip(el);
  attachCaptionTooltips(el);
  attachLegendScroll(el);
  attachLegendFilter(el, 'bar');
  if (onCategoryClick) {
    el.querySelectorAll('[data-code]').forEach(elm => {
      elm.addEventListener('click', () => {
        const row = data.find(d => String(d.code) === elm.getAttribute('data-code'));
        if (row) onCategoryClick(row.code, row.label);
      });
    });
  }
  // Same marks, same rows, same menu as the bar chart this one replaces: a
  // card switched from bars to lines answers the same questions.
  const thisYearIdx = opts.shareKey ? seriesKeys.indexOf(opts.shareKey) : 0;
  const valIdx = thisYearIdx >= 0 ? thisYearIdx : 0;
  wireDrillMenu(el, drillMenu, data, row => ({
    label: row.label,
    valueText: valueFmt(row[seriesKeys[valIdx]] || 0),
    color: seriesColors[valIdx],
  }));
}

const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"];
const MONTH_OPTIONS = MONTH_NAMES.map((l, i) => ({ v: i + 1, l }));
const MEASURE_OPTIONS = [{ v: 'amount', l: 'Amount' }, { v: 'qty', l: 'Quantity' }];
const SUBCAT_OPTIONS = [{ v: 'regular', l: 'Regular' }, { v: 'manager', l: 'Manager' }];
const SERIES_COLORS = ['--series-1', '--series-2', '--series-3', '--series-4'];

// Matches OTHERS in sales_sman_main.py. The chart caps how many categories get
// their own bar and rolls the rest into one row under this code, so the bars
// still sum to the KPI tiles; it is a total, not a category, hence not
// drillable. Distinct from the server's '__none__' (Unassigned), which IS a
// real and drillable selection.
export const OTHERS_CODE = '__others__';

// All eleven levels, in drill order. Must stay in step with LEVELS in
// controllers/sales_sman_main.py -- the drill path is exchanged by name.
const LEVEL_ORDER = ['salesTypeGroup', 'partnerClassification', 'reportRegion', 'city',
                     'salesman', 'customer', 'mainCategory', 'subCategory',
                     'productGroup', 'productSubGroup'];
const LEVEL_FILTER_LABELS = {
  salesTypeGroup: 'Sales Type Group', partnerClassification: 'Partner Classification',
  reportRegion: 'Region', city: 'City', salesman: 'Salesman', customer: 'Customer',
  mainCategory: 'Main Category', subCategory: 'Sub Category',
  productGroup: 'Product Group', productSubGroup: 'Product Sub-Group',
};
const LEVEL_NAV_LABELS = {
  salesTypeGroup: 'Sales Type Groups', partnerClassification: 'Partner Classifications',
  reportRegion: 'Regions', city: 'Cities', salesman: 'Salesmen', customer: 'Customers',
  mainCategory: 'Main Categories', subCategory: 'Sub Categories',
  productGroup: 'Product Groups', productSubGroup: 'Product Sub-Groups',
};

const emptyLevelFilters = () =>
  Object.fromEntries(LEVEL_ORDER.map(lv => [lv, 'all']));

export class PbiSalesSmanDashboard extends Component {
  static template = "pbi_sales_dashboards.sales_sman_dashboard";
  static props = ["*"];

  // Overridden by "Sales Dashboard - VQ" (sales_vq_dashboard.js), which reads
  // the same payload from its own gated route. Everything else about the
  // request is identical, so everything else is inherited.
  get route() { return '/pbi_dashboards/sales_sman/data'; }

  // Source model name in the header is a developer detail — debug mode only.
  selectScope(v) {
    this.state.scope = v;
    this.load();
  }

  // Developer mode only -- see the `scope` note on state. Two options, both
  // honest about what they do.
  get scopeOptions() {
    return [{ v: 'acgroups', l: t("AC product groups") },
            { v: 'all', l: t('Show all') }];
  }

  get isDebugMode() {
    return Boolean(window.odoo && window.odoo.debug);
  }

  setup() {
    this.rpc = useService("rpc");
    this.monthOptions = MONTH_OPTIONS;
    this.measureOptions = MEASURE_OPTIONS;
    this.subCategoryOptions = SUBCAT_OPTIONS;

    // One dropdown per level, in drill order, so any level can be narrowed
    // without first drilling down to it.
    this.levelFilterList = LEVEL_ORDER.map(v => ({ v, l: t(LEVEL_FILTER_LABELS[v]) }));

    this.state = useState({
      year: null, month: null,
      loading: false, error: '',
      yearOptions: [],
      hasBudget: false,
      // Developer-mode only. The two scopes are not comparable -- 601m in scope
      // against 477m for every MDA line, the second being LOWER because the
      // lines outside the scope are the negative discount pseudo-parts -- so
      // this is a diagnostic, not a business control.
      scope: 'acgroups',
      measure: 'amount',
      // Regular/Manager lives in the toolbar, not beside the charts: it governs
      // level 7 as well as level 8, so a control only visible at level 8 would
      // leave a user on Main Categories looking at a breakdown decided
      // off-screen.
      subCategoryMode: 'regular',
      // Matches OPENING_LEVEL in sales_sman_main.py, which is where the reason
      // lives. Only the value the very first render uses -- every reply carries
      // the server's own `level` and overwrites it, so the two can never
      // disagree for longer than one request.
      drillPath: [], level: 'salesTypeGroup', canDrillFurther: true,
      levelFilters: emptyLevelFilters(),
      levelFilterOptions: Object.fromEntries(LEVEL_ORDER.map(lv => [lv, []])),
      levelOverride: null,
      filtersCollapsed: false,
      levelsCollapsed: true,
      toolbarCollapsed: false,
      // The snapshot behind this board rebuilds on a cron, so an edit made in
      // the ERP is not on the chart until it runs. This is the control that
      // asks for it, and what the board knows about where that request got to.
      // `state` mirrors the server's: idle | pending | cron_off | unavailable.
      refresh: { state: 'idle', message: '', lastRun: null, busy: false },
    });
    this.levelNav = LEVEL_ORDER.map(v => ({ v, l: t(LEVEL_NAV_LABELS[v]) }));
    this.t = t;
    this.isArabicUI = isArabicUI;

    this.rootRef = useRef('root');
    this.refs = {
      kpiRow: useRef('kpiRow'),
      mtdBar: useRef('mtdBar'), mtdDonut: useRef('mtdDonut'),
      ytdBar: useRef('ytdBar'), ytdDonut: useRef('ytdDonut'),
      tooltip: useRef('tooltip'),
    };
    this._onMouseMove = evt => moveTip(evt);
    onMounted(() => {
      tooltipEl = this.refs.tooltip.el;
      // Two module-level tooltipEl globals are in play: this file's own, used
      // by the tooltips defined here, and pbi_chart_lib's, used by anything
      // imported from it — attachCaptionTooltips among them. Only setting the
      // first left the library half pointing at null, and its showTip returns
      // on null, so the caption tooltip silently never appeared.
      setTooltipEl(this.refs.tooltip.el);
      document.addEventListener('mousemove', this._onMouseMove);
      this.load();
      this.loadRefreshStatus();
    });
    // Owl writes t-att-selected as an ATTRIBUTE, and a <select> the user has
    // already touched ignores that — the browser keeps showing their choice
    // even after state says otherwise. It bites every reset path: Clear all,
    // and Year/Month wiping the eleven levels. Owl has no property
    // binding for it (its setAttribute does not special-case value), so each
    // select declares what it should read in data-value and this puts it there
    // after every patch, by which point the options exist.
    onPatched(() => this.syncSelects());
    onWillUnmount(() => {
      // A poll outlives the board otherwise, and keeps calling a route for a
      // screen nobody is looking at.
      this._stopRefreshPoll();
      document.removeEventListener('mousemove', this._onMouseMove);
      if (tooltipEl === this.refs.tooltip.el) tooltipEl = null;
      clearTooltipEl(this.refs.tooltip.el);
      // It hangs off <body>, so leaving the board would otherwise leave it
      // floating over whatever replaced it.
      closeDrillMenu();
    });
  }

  // What a level's dropdown should read. A level reached by clicking a bar is
  // shown as selected there too — drilling and picking are the same act
  // against the same level, and a dropdown still reading "All" while the
  // charts are scoped to one region would be a plain lie.
  levelValue(level) {
    const drilled = this.state.drillPath.find(p => p.level === level);
    return drilled ? String(drilled.code) : this.state.levelFilters[level];
  }
  levelOptions(level) { return this.state.levelFilterOptions[level] || []; }

  // True when anything Clear all would actually undo has been touched: the
  // period, the drill path, or one of the eleven levels. Deliberately NOT every
  // chip with an x — Sub-category View has its own x but Clear all leaves it
  // be, so counting it would put a button on screen that did nothing when
  // pressed.
  get hasNarrowing() {
    const d = this.defaultScope;
    return this.state.drillPath.length > 0 ||
           (!!d && (this.state.year !== d.year || this.state.month !== d.month)) ||
           LEVEL_ORDER.some(lv => this.state.levelFilters[lv] !== 'all');
  }

  // Back to this month, no drill, no level narrowed — in one request rather
  // than a dozen.
  //
  // Sub-category View is NOT touched: it is how the numbers are read rather
  // than which numbers they are, and someone reading Manager mode has not
  // filtered anything, they have chosen a lens. Its chip still carries an x
  // for undoing it on its own.
  //
  // levelOverride survives too, so clearing while reading the Salesmen tab
  // leaves you on the Salesmen tab. A drill returns to Sales Type Group
  // unasked, since the level was only ever derived from the path.
  clearAll() {
    if (!this.hasNarrowing) return;
    const d = this.defaultScope;
    if (d) {
      // Straight to the known defaults rather than null, or Year and Month
      // would render with nothing selected for the length of the request.
      this.state.year = d.year;
      this.state.month = d.month;
    }
    this.state.drillPath = [];
    this.state.levelFilters = emptyLevelFilters();
    this.load();
  }

  // One chip's x. Routed through the same handlers the dropdowns use, so
  // clearing a chip and choosing that value by hand are the same act: Year and
  // Month still reset the eleven levels beneath them, a level still truncates the
  // drill path from its own depth down.
  clearChip(id) {
    const d = this.defaultScope;
    if (!d) return;
    if (id === 'year') return this.selectYear(d.year);
    if (id === 'month') return this.selectMonth(d.month);
    if (id === 'subCategoryMode') return this.selectSubCategoryMode(d.subCategoryMode);
    this.selectLevelFilter(id, 'all');
  }

  // Everything the toolbar is currently set to, for the header line.
  //
  // The toolbar collapses and the header does not, so without this a collapsed
  // "Filters & Levels" hides every choice that produced the numbers underneath
  // it — you could be looking at one city's figures with nothing on screen
  // saying so. Year, Month and Sub-category View always show, since
  // they always hold a value; the eleven levels show only when they are off All,
  // or a dashboard with nothing filtered would carry ten chips reading "All".
  //
  // `off` marks a chip as moved off its opening value, which is what earns it
  // an x — a chip already at its default would get a control that does nothing.
  //
  // Reads through levelValue(), so a level reached by clicking a bar appears
  // here exactly like one picked from its dropdown.
  get filterSummary() {
    const d = this.defaultScope;
    const out = [];
    const month = MONTH_OPTIONS.find(o => o.v === this.state.month);
    // Same order as the toolbar: the lens (read which way, on whose numbers),
    // then the period, then whatever has been narrowed inside it.
    out.push({ id: 'subCategoryMode', k: t('Sub-category View'),
               v: t(this.state.subCategoryMode === 'manager' ? 'Manager' : 'Regular'),
               off: !!d && this.state.subCategoryMode !== d.subCategoryMode });
    out.push({ id: 'year', k: t('Year'),
               v: this.state.year == null ? '' : String(this.state.year),
               off: !!d && this.state.year !== d.year });
    out.push({ id: 'month', k: t('Month'), v: month ? t(month.l) : '',
               off: !!d && this.state.month !== d.month });
    for (const lf of this.levelFilterList) {
      const value = this.levelValue(lf.v);
      if (!value || value === 'all') continue;
      // The option list is the label source; the drill path is the fallback for
      // the moment between clicking a bar and the new options arriving.
      const opt = this.levelOptions(lf.v).find(o => o.v === value);
      const drilled = this.state.drillPath.find(p => String(p.code) === value && p.level === lf.v);
      out.push({ id: lf.v, k: lf.l,
                 v: opt ? opt.l : (drilled ? drilled.label : value), off: true });
    }
    return out;
  }

  syncSelects() {
    const root = this.rootRef.el;
    if (!root) return;
    for (const sel of root.querySelectorAll('select[data-value]')) {
      const want = sel.getAttribute('data-value');
      if (sel.value !== want) sel.value = want;
    }
  }

  resetDrill() {
    this.state.drillPath = [];
    this.state.levelOverride = null;
  }
  // Year and Month re-scope the whole dashboard, so they clear the
  // ten level filters too — keeping them would silently carry a customer or a
  // city that no longer exists in the new scope and show empty charts.
  resetAll() {
    this.resetDrill();
    this.state.levelFilters = emptyLevelFilters();
  }
  toggleFilters() { this.state.filtersCollapsed = !this.state.filtersCollapsed; }
  toggleLevels() { this.state.levelsCollapsed = !this.state.levelsCollapsed; }
  toggleToolbar() { this.state.toolbarCollapsed = !this.state.toolbarCollapsed; }

  // -------------------------------------------------------------- refreshing
  //
  // The button QUEUES a rebuild; it never waits for one. The server side is
  // ~16s of database CPU, so the request returns as soon as the job is on the
  // cron's queue and this polls until it lands. Debouncing, the once-a-minute
  // floor and the cron's on/off state are all decided server-side -- see
  // pbi.sales.sman.fact.queue_refresh -- so this never has to guess whether a
  // click is safe.

  _stopRefreshPoll() {
    if (this._refreshTimer) { clearTimeout(this._refreshTimer); this._refreshTimer = null; }
  }

  // 15s: the cron thread wakes at most every 60s, so polling faster only costs
  // requests. Stops as soon as nothing is pending.
  _scheduleRefreshPoll(pending) {
    this._stopRefreshPoll();
    if (pending) this._refreshTimer = setTimeout(() => this.loadRefreshStatus(), 15000);
  }

  async loadRefreshStatus() {
    try {
      const res = await this.rpc('/pbi_dashboards/sales_sman/refresh_status', {});
      if (!res || res.error) return;
      const wasPending = this.state.refresh.state === 'pending';
      this.state.refresh.state = res.state;
      this.state.refresh.lastRun = res.last_run;
      // The rebuild finished while we were watching, so the figures on screen
      // are now the stale ones. Reload rather than leave the user to guess.
      if (wasPending && res.state !== 'pending') {
        this.state.refresh.message = t('Refreshed');
        this.load();
      }
      this._scheduleRefreshPoll(res.state === 'pending');
    } catch (e) {
      // Status is a nicety. A board that works must not break because the
      // status route did not answer.
      this._stopRefreshPoll();
    }
  }

  async queueRefresh() {
    if (this.state.refresh.busy || this.state.refresh.state === 'pending') return;
    this.state.refresh.busy = true;
    this.state.refresh.message = '';
    try {
      const res = await this.rpc('/pbi_dashboards/sales_sman/queue_refresh', {});
      if (!res || res.error) {
        this.state.refresh.message = t('Not allowed');
        return;
      }
      this.state.refresh.message = res.message || '';
      this.state.refresh.lastRun = res.last_run;
      // queued and already_queued are the same thing to a reader: a rebuild is
      // coming and the board should watch for it.
      const pending = res.state === 'queued' || res.state === 'already_queued';
      this.state.refresh.state = pending ? 'pending' : res.state;
      this._scheduleRefreshPoll(pending);
    } catch (e) {
      this.state.refresh.message = t('Could not queue the refresh');
    } finally {
      this.state.refresh.busy = false;
    }
  }

  get refreshLabel() {
    const r = this.state.refresh;
    if (r.state === 'pending') return t('Refreshing…');
    if (r.state === 'cron_off') return t('Refresh unavailable');
    return t('Refresh data');
  }

  get refreshTitle() {
    const r = this.state.refresh;
    if (r.state === 'cron_off') {
      return t('The scheduled refresh is switched off. An administrator must re-enable it.');
    }
    if (r.lastRun) {
      // Local time: the server stores UTC and a reader comparing this against
      // their own clock should not have to do the arithmetic.
      return `${t('Last refreshed')}: ${new Date(r.lastRun + 'Z').toLocaleString()}`;
    }
    return t('Rebuilds the figures from the latest ERP data. Runs in the background.');
  }
  selectYear(v) { this.state.year = +v; this.resetAll(); this.load(); }
  selectMonth(v) { this.state.month = +v; this.resetAll(); this.load(); }

  // Truncate the drill path from the first category level rather than clearing
  // it: the levels above (region, city, salesman...) are unaffected by which
  // category field feeds levels 7 and 8, so throwing them away would be rude.
  selectSubCategoryMode(v) {
    if (this.state.subCategoryMode === v) return;
    this.state.subCategoryMode = v;
    const cut = this.state.drillPath.findIndex(
      p => p.level === 'mainCategory' || p.level === 'subCategory');
    if (cut !== -1) this.state.drillPath = this.state.drillPath.slice(0, cut);
    // Both category levels are re-keyed by the switch, so their filters name
    // ids from the other field and must go with them.
    this.state.levelFilters = { ...this.state.levelFilters,
                                mainCategory: 'all', subCategory: 'all' };
    this.state.levelOverride = null;
    this.load();
  }

  // Switching Amount/Quantity is a re-render, not a reload -- the payload
  // carries both measures for every row, and paying a round trip to redraw
  // numbers already in hand would make the control feel broken.
  //
  // EXCEPT on a ranked level, where the server chose WHICH ten rows to send by
  // this measure. There the rows themselves are wrong for the new measure, not
  // merely ordered wrongly: at Product Sub-Group the top ten by value and the
  // top ten by quantity share three members. `rankedBy` is the server saying
  // its choice depended on the measure, so the client asks again rather than
  // re-sorting ten rows that were picked on the other one.
  selectMeasure(v) {
    if (this.state.measure === v) return;
    this.state.measure = v;
    if (this.lastJson && this.lastJson.rankedBy) { this.load(); return; }
    if (this.lastJson) { this.renderKpis(); this.renderCharts(); }
  }
  jumpToLevel(level) {
    if (level === this.state.level) return;
    this.state.levelOverride = level;
    this.load();
  }
  // Narrowing a level invalidates every drill step at or below it: a drill
  // into a different value of the same level would contradict the filter, and
  // the steps under it were chosen inside a scope that no longer holds. The
  // levels ABOVE are untouched — they still describe where the user is.
  selectLevelFilter(level, v) {
    const value = (!v || v === 'all') ? 'all' : v;
    // Against levelValue(), NOT state.levelFilters: a level reached by clicking
    // a bar has its value in the drill path with the filter still on 'all', so
    // comparing the filter alone would read "All -> All", call it a no-op, and
    // refuse the one gesture that undoes a drill.
    if (this.levelValue(level) === value) return;
    this.state.levelFilters = { ...this.state.levelFilters, [level]: value };
    const depth = LEVEL_ORDER.indexOf(level);
    const cut = this.state.drillPath.findIndex(
      p => LEVEL_ORDER.indexOf(p.level) >= depth);
    if (cut !== -1) this.state.drillPath = this.state.drillPath.slice(0, cut);
    this.load();
  }
  onCategoryClick(code, label) {
    if (!this.state.canDrillFurther) return;
    // "Others" is a roll-up of every category below the chart's bar cap, not a
    // category of its own, so there is nothing to drill into. Server-side twin:
    // OTHERS in sales_sman_main.py.
    if (code === OTHERS_CODE) return;
    this.state.drillPath = [...this.state.drillPath, { level: this.state.level, code, label }];
    this.state.levelOverride = null;
    this.load();
  }

  onScopeChipClick(id) {
    if (LEVEL_ORDER.includes(id)) {
      this.jumpToLevel(id);
    }
  }

  // Active drilled levels with their level name and formatted value for the drill menu
  get activeDrills() {
    const list = [];
    LEVEL_ORDER.forEach((lv, i) => {
      const val = this.levelValue(lv);
      if (!val || val === 'all') return;
      const opt = this.levelOptions(lv).find(o => o.v === val);
      const drilled = this.state.drillPath.find(p => String(p.code) === String(val) && p.level === lv);
      const label = opt ? opt.l : (drilled ? drilled.label : val);
      list.push({
        level: lv,
        levelLabel: t(LEVEL_FILTER_LABELS[lv] || ''),
        code: val,
        label: label,
        num: i + 1,
      });
    });
    return list;
  }

  // What the drill menu offers on every chart mark: the eleven levels by their
  // singular names -- the same words the ten dropdowns above use, so a level
  // chosen here and a level narrowed there are visibly the same thing -- plus
  // where the board is now, which the menu leaves out of its own list.
  //
  // Rebuilt on every render rather than held in state: `state.level` moves
  // with each reply, and a menu spec captured once would go on offering the
  // level the reader is already looking at.
  get drillMenuSpec() {
    return {
      levels: this.levelFilterList,
      currentLevel: this.state.level,
      currentLabel: t(LEVEL_FILTER_LABELS[this.state.level] || ''),
      // A level already pinned to one value -- by a drill step above, or by
      // its own dropdown -- would open as a single bar whatever row it was
      // asked about, so it is left out rather than offered. Which levels those
      // are is already on screen, as the chips in the scope line.
      omit: LEVEL_ORDER.filter(lv => this.levelValue(lv) !== 'all'),
      activeDrills: this.activeDrills,
      onPick: (code, label, level) => this.onCategoryDrillTo(code, label, level),
      onJump: level => this.jumpToLevel(level),
      onRelease: level => this.releaseDrillFilter(level),
    };
  }

  // Releasing a filter condition from inside the drill menu without abruptly closing it
  releaseDrillFilter(level) {
    const value = 'all';
    if (this.levelValue(level) === value) return;
    this.state.levelFilters = { ...this.state.levelFilters, [level]: value };
    const depth = LEVEL_ORDER.indexOf(level);
    const cut = this.state.drillPath.findIndex(
      p => LEVEL_ORDER.indexOf(p.level) >= depth);
    if (cut !== -1) this.state.drillPath = this.state.drillPath.slice(0, cut);
    this.load({ keepDrillMenu: true });
  }

  // The one line on the board that says the gesture exists -- built here rather
  // than assembled in the template, where the whitespace between two adjacent
  // <t t-esc/> nodes does not survive into the rendered sentence ("Clicka bar
  // to drill one level").
  //
  // Two readings of the same sentence, one per input device, both in the
  // markup with CSS picking which to show: a hint naming right-click on a
  // phone reads as an instruction the reader has failed to follow.
  get drillHintPointer() {
    return `${t('Click')} ${t('a bar to drill one level')} · `
         + `${t('Right-click')} ${t('a bar for every other level')}`;
  }
  get drillHintTouch() {
    return `${t('Tap')} ${t('a bar to drill one level')} · `
         + `${t('Long-press')} ${t('a bar for every other level')}`;
  }

  // Clicking a bar and picking a level from its menu are ONE act with two
  // halves: the row narrows the data exactly as a plain click would, and the
  // chosen level decides what the charts group by inside it. The server has
  // taken both since it was written -- drillPath filters, viewLevel groups --
  // so this needs no route of its own.
  //
  // That also makes the menu's second half work: a level ABOVE the current one
  // is not a drill but it is a perfectly good question ("this salesman, by
  // region"), and it is the same two halves in the other order.
  //
  // Unlike onCategoryClick this replaces any step already standing at this
  // level rather than appending beside it. The two can only ever collide after
  // a jump back up the chain, and a second identical clause would be dead
  // weight carried through every later request.
  onCategoryDrillTo(code, label, level) {
    if (code === OTHERS_CODE || !LEVEL_ORDER.includes(level)) return;
    if (level === this.state.level) return;
    const here = this.state.level;
    this.state.drillPath = [...this.state.drillPath.filter(p => p.level !== here),
                            { level: here, code, label }];
    this.state.levelOverride = level;
    this.load();
  }

  seriesColors() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    return SERIES_COLORS.map(v => style.getPropertyValue(v).trim());
  }

  async load(opts = {}) {
    // Every mark the open menu was anchored to is about to be replaced, and
    // its header names a row the next payload may not carry.
    if (!opts.keepDrillMenu) {
      closeDrillMenu();
    }
    this.state.loading = true;
    this.state.error = '';
    try {
      const period = (this.state.year && this.state.month)
        ? `${this.state.year}-${String(this.state.month).padStart(2, '0')}` : null;
      const res = await this.rpc(this.route, {
        period,
        subCategoryMode: this.state.subCategoryMode,
        scope: this.state.scope,
        drillPath: this.state.drillPath,
        levelFilters: this.state.levelFilters,
        viewLevel: this.state.levelOverride,
        // Only the ranked levels read it, and only to decide whether the top
        // ten is ten by value or ten by units -- see selectMeasure. The VQ
        // route drops it: that board has no measure control.
        measure: this.state.measure,
      });
      if (res.error) { this.state.error = res.error; return; }
      this.lastJson = res;
      // The first request of a session asks for no period, so what comes back
      // IS what the dashboard opens with — this month. Remembered here because
      // every x, and Clear all, is defined as "back to this".
      if (this.defaultScope === undefined) {
        this.defaultScope = {
          year: res.period.year, month: res.period.month,
          subCategoryMode: res.subCategoryMode || 'regular',
        };
      }
      this.state.year = res.period.year;
      this.state.month = res.period.month;
      this.state.hasBudget = res.hasBudget;
      if (res.scope) this.state.scope = res.scope;
      this.state.yearOptions = res.yearOptions;
      this.state.level = res.level;
      this.state.canDrillFurther = res.canDrillFurther;
      const byLevel = res.levelFilterOptions || {};
      this.state.levelFilterOptions = Object.fromEntries(LEVEL_ORDER.map(lv => {
        const seen = new Set();
        const opts = [];
        for (const o of (byLevel[lv] || [])) {
          if (seen.has(o.v)) continue;
          seen.add(o.v);
          opts.push(o);
        }
        return [lv, opts];
      }));
      this.renderAll();
    } catch (e) {
      this.state.error = t('Failed to load') + ' — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  renderKpis() {
    const k = this.lastJson.kpis;
    const isAmount = this.state.measure === 'amount';
    const valueFmt = isAmount ? fmtM : fmtK;
    const v = isAmount
      ? { mtdTY: k.mtdThisYear, mtdTar: k.mtdTarget, mtdLY: k.mtdLastYear,
          ytdTY: k.ytdThisYear, ytdTar: k.ytdTarget, ytdLY: k.ytdLastYear }
      : { mtdTY: k.mtdQtyThisYear, mtdTar: k.mtdQtyTarget, mtdLY: k.mtdQtyLastYear,
          ytdTY: k.ytdQtyThisYear, ytdTar: k.ytdQtyTarget, ytdLY: k.ytdQtyLastYear };
    const noun = isAmount ? 'Sales' : 'Qty';

    // The budget is not captured per salesman or per product sub-group, so at
    // those levels there is no target to show -- not a zero, an absence. A "0"
    // in a Target tile reads as "we budgeted nothing"; an em dash reads as
    // "this is not measured here", which is the truth. The vs-Target % tile
    // goes with it: a percentage of a number that does not exist is noise.
    const noTarget = this.lastJson.hasBudget === false;
    const dash = '—';
    // An allocated target keeps its figure but not its plain caption: the tile
    // says "(allocated)" and its tooltip names the basis, so the number can
    // never be read off the board as one somebody set at this level.
    const alloc = this.targetIsAllocated;
    const targetTile = (label, value, raw) => noTarget
      ? { label, value: dash, raw: t('No target at this level'), dark: true }
      : alloc
        ? { label: `${label} ${t('(allocated)')}`, value,
            raw: `${raw} · ${t('target allocated from')} `
               + `${t(this.lastJson.budgetBasisLabel)} ${t("by last year's mix")}` }
        : { label, value, raw };

    const tiles = [
      { label: `MTD - This Year ${noun}`, value: valueFmt(v.mtdTY), raw: fmt(v.mtdTY) },
      targetTile(`MTD - Target${isAmount ? '' : ' Qty'}`, valueFmt(v.mtdTar), fmt(v.mtdTar)),
      targetTile(`MTD - ${noun} vs Target %`, fmtPct(pct(v.mtdTY, v.mtdTar)), fmtPctPrecise(pct(v.mtdTY, v.mtdTar))),
      { label: `YTD - This Year ${noun}`, value: valueFmt(v.ytdTY), raw: fmt(v.ytdTY) },
      targetTile(`YTD - Target${isAmount ? '' : ' Qty'}`, valueFmt(v.ytdTar), fmt(v.ytdTar)),
      targetTile(`YTD - ${noun} vs Target %`, fmtPct(pct(v.ytdTY, v.ytdTar)), fmtPctPrecise(pct(v.ytdTY, v.ytdTar))),
      { label: `MTD - This Year ${noun}`, value: valueFmt(v.mtdTY), raw: fmt(v.mtdTY) },
      { label: `MTD - Last Year ${noun}`, value: valueFmt(v.mtdLY), raw: fmt(v.mtdLY) },
      { label: `MTD - TY ${noun} vs LY ${noun} %`, value: fmtPct(pct(v.mtdTY, v.mtdLY)), raw: fmtPctPrecise(pct(v.mtdTY, v.mtdLY)) },
      { label: `YTD - This Year ${noun}`, value: valueFmt(v.ytdTY), raw: fmt(v.ytdTY) },
      { label: `YTD - Last Year ${noun}`, value: valueFmt(v.ytdLY), raw: fmt(v.ytdLY) },
      { label: `YTD - TY ${noun} vs LY ${noun} %`, value: fmtPct(pct(v.ytdTY, v.ytdLY)), raw: fmtPctPrecise(pct(v.ytdTY, v.ytdLY)) },
    ];
    // A dark tile keeps its slot and its colour position -- pulling it out
    // would reflow the other ten every time the user drills into a salesman.
    this.refs.kpiRow.el.innerHTML = tiles.map((tile, i) => `
      <div class="pbi-kpi tile-color-${i}${tile.dark ? ' no-target' : ''}"
           data-tip="${t(tile.label)}||${t('Actual')}||${tile.raw}">
        <div class="value">${tile.value}</div>
        <div class="label">${t(tile.label)}</div>
      </div>`).join('');
    attachValueTooltips(this.refs.kpiRow.el, '.pbi-kpi[data-tip]');
  }

  // Follows what is actually drawn. A card headed "This Year, Target and Last
  // Year" above two series is a small lie the reader has to work out for
  // themselves.
  chartSubtitle() {
    if (!this.lastJson || this.lastJson.hasBudget !== false) {
      // Where the target is allocated, the subtitle carries the whole method in
      // one line -- what it was shared down from, and what it was weighted by.
      // A reader comparing a salesman against it has to be able to see that it
      // is a share of his sale type's target, not a number set for him.
      if (this.targetIsAllocated) {
        return `${t('This Year, Target and Last Year')} · ${t('target allocated from')} `
             + `${t(this.lastJson.budgetBasisLabel)} ${t("by last year's mix")}`;
      }
      return t('This Year, Target and Last Year');
    }
    // Say WHY there is no target, when the server knows why. "No target at
    // this level" alone reads as a dashboard that lost the number; naming the
    // capture — "the budget is not captured per salesman" — tells the reader
    // where the gap actually is, which is the only place it can be closed.
    const why = this.lastJson.budgetReason;
    return why ? `${t('This Year and Last Year — no target')}: ${t(why)}`
               : t('This Year and Last Year — no target at this level');
  }

  // True where the target on screen was shared down from another level rather
  // than captured at this one.
  get targetIsAllocated() {
    return !!(this.lastJson && this.lastJson.budgetAllocated);
  }

  // "Target Sales" becomes "Target Sales (allocated)" wherever the figure is
  // derived. Applied to the series labels, the legend and the KPI tile from one
  // place, so no reading of the board can show an allocated number under a
  // caption that claims it was budgeted.
  targetLabel(label) {
    return this.targetIsAllocated ? `${t(label)} ${t('(allocated)')}` : label;
  }

  chartTitle(period, kind) {
    const isAmount = this.state.measure === 'amount';
    const P = period.toUpperCase();
    if (kind === 'bar') return isAmount ? `${P} – Sales Amount Analysis` : `${P} – Sales Qty Analysis`;
    return isAmount ? `${P} – Amt Contribution %` : `${P} – Qty Contribution %`;
  }

  renderCharts() {
    const sc = this.seriesColors();
    const isAmount = this.state.measure === 'amount';
    // Two series, not three, where there is no target -- the same reason the
    // tile shows a dash. A flat zero Target bar beside a real one does not read
    // as "not measured", it reads as "missed the target completely".
    const noTarget = this.lastJson.hasBudget === false;
    const barColors = noTarget ? [sc[0], sc[1]]
                               : [sc[0], sc[2], sc[1]];   // This Year / Target / Last Year
    const seriesKeys = isAmount
      ? (noTarget ? ['amount', 'prevYearAmount'] : ['amount', 'budgetAmount', 'prevYearAmount'])
      : (noTarget ? ['qty', 'prevYearQty'] : ['qty', 'budgetQty', 'prevYearQty']);
    const seriesLabels = isAmount
      ? (noTarget ? ['This Year Sales', 'Last Year Sales']
                  : ['This Year Sales', this.targetLabel('Target Sales'), 'Last Year Sales'])
      : (noTarget ? ['This Year Qty', 'Last Year Qty']
                  : ['This Year Qty', this.targetLabel('Target Qty'), 'Last Year Qty']);
    const valueFmt = isAmount ? fmtM : fmtK;
    const valueKey = isAmount ? 'amount' : 'qty';
    const onClick = this.state.canDrillFurther ? (code, label) => this.onCategoryClick(code, label) : null;
    const colors = PALETTE;
    const mtd = isAmount ? this.lastJson.breakdown.mtd : byQtyDesc(this.lastJson.breakdown.mtd);
    const ytd = isAmount ? this.lastJson.breakdown.ytd : byQtyDesc(this.lastJson.breakdown.ytd);

    const drillMenu = this.drillMenuSpec;

    groupedBarChart(this.refs.mtdBar.el, mtd, seriesKeys, barColors, seriesLabels, onClick, valueFmt, { drillMenu });
    groupedBarChart(this.refs.ytdBar.el, ytd, seriesKeys, barColors, seriesLabels, onClick, valueFmt, { drillMenu });
    // The donut's whole comes off the KPI tiles, not off the rows it draws --
    // see donutChart's opts.total. Identical on the levels that carry every
    // category; the difference is the ranked ones, where the rows are ten of
    // many.
    const k = this.lastJson.kpis;
    const mtdTotal = isAmount ? k.mtdThisYear : k.mtdQtyThisYear;
    const ytdTotal = isAmount ? k.ytdThisYear : k.ytdQtyThisYear;
    donutChart(this.refs.mtdDonut.el, mtd.map(d => ({ code: d.code, label: d.label, value: d[valueKey] })), colors, onClick, valueFmt, { total: mtdTotal, drillMenu });
    donutChart(this.refs.ytdDonut.el, ytd.map(d => ({ code: d.code, label: d.label, value: d[valueKey] })), colors, onClick, valueFmt, { total: ytdTotal, drillMenu });
  }

  renderAll() { this.renderKpis(); this.renderCharts(); }
}

registry.category("actions").add("pbi_sales_dashboards.sales_sman_dashboard", PbiSalesSmanDashboard);
