/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { t, tDate, addLabels, isArabicUI } from "./pbi_i18n";

// "Sales Analysis - New" — sibling of sales_mail_dashboard.js, same
// bidata-direct 17-page report data (own JSON route, see
// pbi_dashboards/controllers/sales_mail_main.py's sales_mail_data_new),
// but WITHOUT the Prev/Next/page-picker navigation: every page renders
// stacked, one after another, in the same order they're listed in the
// header/page-picker over there — see the CSS's ".pbi-page { display:
// block; }" (no page-nav, no .active gating) instead of the original's
// show-one-page-at-a-time toggle. Gated by its own menu grant
// (menu_pbi_sales_mail_dashboard_new), independent of "Sales Analysis",
// per this module's one-grant-per-leaf convention. EN -> AR strings below
// mirror sales_mail_dashboard.js's own addLabels call (both files are
// bundled together, but this file is kept self-contained so it doesn't
// depend on load order).
addLabels({
  // header/footer
  "Sales Analysis - New": "تحليل المبيعات - جديد",
  "Sales Dashboards": "لوحات معلومات المبيعات",
  // filters
  "Filters & Export": "الفلاتر والتصدير",
  "Export": "تصدير",
  "Export PDF": "تصدير PDF",
  "Export PowerPoint": "تصدير PowerPoint",
  "Import Notes": "استيراد الملاحظات",
  // month filter options
  "January": "يناير", "February": "فبراير", "March": "مارس", "April": "أبريل",
  "May": "مايو", "June": "يونيو", "July": "يوليو", "August": "أغسطس",
  "September": "سبتمبر", "October": "أكتوبر", "November": "نوفمبر", "December": "ديسمبر",
  // generic axis/legend/chart words
  "Value": "القيمة",
  "Quantity": "الكمية",
  "Amount": "المبلغ",
  "MTD": "حتى تاريخه الشهري",
  "YTD": "حتى تاريخه السنوي",
  "Target": "الهدف",
  "vs LY": "مقابل العام الماضي",
  "Achv": "الإنجاز",
  "Vs. Target": "مقابل الهدف",
  "Vs. Last Year": "مقابل العام الماضي",
  "Main Group": "المجموعة الرئيسية",
  "Main Groups": "المجموعات الرئيسية",
  "Departments": "الأقسام",
  "Show more": "عرض المزيد",
  "Back to start": "العودة إلى البداية",
  "Edited note": "ملاحظة معدَّلة",
  // section headings
  "Total Company": "إجمالي الشركة",
  "Department & Region Performance Trends": "اتجاهات أداء الأقسام والمناطق",
  "Department & Region Performance Trends (YTD)": "اتجاهات أداء الأقسام والمناطق (حتى تاريخه السنوي)",
  "Quarterly Sales Progression — Company": "التطور الفصلي للمبيعات — الشركة",
  "Quarterly Progression by Department": "التطور الفصلي حسب القسم",
  "Quarterly Progression by Region (Dealers)": "التطور الفصلي حسب المنطقة (الموزعون)",
  "Quarterly Progression by Region — Dealers": "التطور الفصلي حسب المنطقة — الموزعون",
  "Main Groups — MTD & YTD": "المجموعات الرئيسية — حتى تاريخه الشهري والسنوي",
  "Product Sub-Groups — Top 8 (YTD)": "المجموعات الفرعية للمنتجات — أفضل 8 (حتى تاريخه السنوي)",
  "Sub-Groups Distribution — LY vs TY": "توزيع المجموعات الفرعية — العام الماضي مقابل العام الحالي",
  "Sub-Groups Distribution — LY vs TY (Top 8, YTD)": "توزيع المجموعات الفرعية — العام الماضي مقابل العام الحالي (أفضل 8، حتى تاريخه السنوي)",
  "Main Groups Distribution — LY vs TY": "توزيع المجموعات الرئيسية — العام الماضي مقابل العام الحالي",
  "Main Groups Distribution — LY vs TY (YTD)": "توزيع المجموعات الرئيسية — العام الماضي مقابل العام الحالي (حتى تاريخه السنوي)",
  "Departments — MTD & YTD": "الأقسام — حتى تاريخه الشهري والسنوي",
  "Departments Distribution — LY vs TY": "توزيع الأقسام — العام الماضي مقابل العام الحالي",
  "Departments Distribution — LY vs TY (YTD)": "توزيع الأقسام — العام الماضي مقابل العام الحالي (حتى تاريخه السنوي)",
  "LCAC Sub-Groups": "المجموعات الفرعية لـ LCAC",
  "Top-3 Sub-Groups by Channel": "أفضل 3 مجموعات فرعية حسب القناة",
  "Top-3 Sub-Groups by Channel (YTD)": "أفضل 3 مجموعات فرعية حسب القناة (حتى تاريخه السنوي)",
  "Regions by Channel": "المناطق حسب القناة",
  "Regions by Channel (YTD)": "المناطق حسب القناة (حتى تاريخه السنوي)",
  "Dealers by Region — Main Groups": "الموزعون حسب المنطقة — المجموعات الرئيسية",
  "Dealers by Region — Main Groups (YTD)": "الموزعون حسب المنطقة — المجموعات الرئيسية (حتى تاريخه السنوي)",
  "Dealers by Region — Split Sub-Groups": "الموزعون حسب المنطقة — المجموعات الفرعية لـ Split",
  "Dealers by Region — Split Sub-Groups (YTD)": "الموزعون حسب المنطقة — المجموعات الفرعية لـ Split (حتى تاريخه السنوي)",
  "Projects — Product Groups (YTD)": "المشاريع — مجموعات المنتجات (حتى تاريخه السنوي)",
  // page-2 card headings
  "By Department — Achievement % / YoY %": "حسب القسم — نسبة الإنجاز٪ / التغير السنوي٪",
  "By Dealer Region — Achievement % / YoY %": "حسب منطقة الموزع — نسبة الإنجاز٪ / التغير السنوي٪",
  // error/status text
  "No edited narrative notes were found — the file's speaker notes matched the dashboard's current text.":
    "لم يتم العثور على ملاحظات سردية معدَّلة — تطابقت ملاحظات المتحدث في الملف مع النص الحالي للوحة المعلومات.",
  "Failed to import notes — ": "فشل استيراد الملاحظات — ",
  "Failed to load — ": "فشل التحميل — ",
});

// ---------------------------------------------------------------------
// formatting/tooltip helpers — same trimmed-copy convention as every other
// dashboard JS file here (none of them export helpers, so each carries its
// own small subset — see sales_kpi_dashboard.js).
// ---------------------------------------------------------------------
const fmt = n => n == null ? "–" : new Intl.NumberFormat('en-US').format(Math.round(n));
const fmtM = n => n == null ? "–" : (n / 1e6).toFixed(1) + "M";
const fmtK = n => n == null ? "–" : (n / 1e3).toFixed(1) + "K";
const fmtCompact = n => n == null ? "–" : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(n);
// Every breakdown array from the controller is ordered by This-Year SALES
// descending (shared with the paired Value chart). A Qty panel needs its
// OWN This-Year-Qty-descending order instead — sorting a shallow copy here
// keeps the Value chart's array/order untouched.
function byQtyDesc(rows) { return [...rows].sort((a, b) => (b.qty || 0) - (a.qty || 0)); }

function pct(part, total) { return total > 0 ? (part / total * 100) : null; }
function fmtPct(p) { return p == null ? "–" : p.toFixed(1) + "%"; }
function fmtPctPrecise(p) { return p == null ? "–" : p.toFixed(2) + "%"; }

let tooltipEl = null;
function showTip(evt, html, wide) {
  if (!tooltipEl) return;
  tooltipEl.innerHTML = html;
  tooltipEl.classList.toggle('wide', !!wide);
  tooltipEl.classList.add('show');
  moveTip(evt);
}
function moveTip(evt) {
  if (!tooltipEl) return;
  const pad = 14;
  const viewportW = window.innerWidth || document.documentElement.clientWidth;
  const viewportH = window.innerHeight || document.documentElement.clientHeight;
  const tipW = tooltipEl.offsetWidth || 320;
  const tipH = tooltipEl.offsetHeight || 100;

  let left = evt.clientX + pad;
  let top = evt.clientY + pad;

  if (left + tipW > viewportW - pad) {
    left = evt.clientX - tipW - pad;
    if (left < pad) {
      left = Math.max(pad, viewportW - tipW - pad);
    }
  }

  if (top + tipH > viewportH - pad) {
    top = evt.clientY - tipH - pad;
    if (top < pad) {
      top = Math.max(pad, viewportH - tipH - pad);
    }
  }

  tooltipEl.style.left = left + 'px';
  tooltipEl.style.top = top + 'px';
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
  return `<div class="pbi-legend-wrap"><div class="pbi-legend">${items}</div><button type="button" class="legend-more" title="${t('Show more')}">&#9654;</button></div>`;
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
    btn.title = atEnd ? t('Back to start') : t('Show more');
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
// chart primitives — groupedBarChart/donutChart copied from
// sales_kpi_dashboard.js (no drill-down here). comboBarLineChart is new:
// bars on the primary (left) axis + line series on a secondary (right,
// percentage) axis, replicating the pbix's lineClusteredColumnComboChart.
// ---------------------------------------------------------------------
function groupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels, valueFmt = fmtCompact) {
  const perGroup = 180;
  const W = Math.max(el.clientWidth || 480, data.length * perGroup), H = 230;
  const marginL = 54, marginR = 10, marginT = 10, marginB = 46;
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const maxRaw = Math.max(1, ...data.flatMap(d => seriesKeys.map(k => d[k] || 0)));
  const tickVals = niceAxisTicks(maxRaw, valueFmt);
  const maxVal = tickVals[tickVals.length - 1];
  const groupW = plotW / Math.max(data.length, 1);
  const gap = 6;
  const barW = Math.min(32, (groupW - gap * (seriesKeys.length - 1)) / seriesKeys.length * 0.9);

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
      svg += `<rect data-tip="${d.label}||${seriesLabels[si]}||${val}" rx="2" ry="2" x="${x}" y="${y}" width="${barW}" height="${Math.max(barH, 1)}" fill="${seriesColors[si]}"/>`;
      svg += `<text class="bar-value" x="${x + barW / 2}" y="${y - 3}" text-anchor="middle">${valueFmt(val)}</text>`;
    });
    const label = truncateLabel(d.label, groupW - 8);
    svg += `<text class="axis-label" x="${marginL + gi * groupW + groupW / 2}" y="${H - 24}" text-anchor="middle"><title>${d.label}</title>${label}</text>`;
  });
  svg += `</svg>`;
  el.innerHTML = legendHtml(seriesLabels, seriesColors) + svg;
  attachBarTooltips(el);
  attachLegendScroll(el);
}

function donutChart(el, data, colors, valueFmt = fmtCompact) {
  const total = data.reduce((s, d) => s + (d.value || 0), 0);
  const r = 47, thickness = 20;
  const ringOuterR = r + thickness / 2;
  const labelR = ringOuterR + 40;
  const cx = labelR + 18, cy = labelR + 18;
  const W = cx * 2, H = cy * 2;
  const circumference = 2 * Math.PI * r;

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
    slices.push({ label: d.label, share, trueAngle, labelAngle: trueAngle, halfAngle, cumStart: cumulative, colorIdx: i });
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
    rings.push(`<circle data-tip="${s.label}||${t('Share')}||${(s.share * 100).toFixed(1)}" cx="${cx}" cy="${cy}" r="${r}" fill="none"
              stroke="${colors[s.colorIdx % colors.length]}" stroke-width="${thickness}"
              stroke-dasharray="${segLen} ${circumference - segLen}" stroke-dashoffset="${offset}"
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
  });
}

// Bars (Target/This Year/Last Year) on the primary axis + line series
// (Achievement%/YoY%) on a secondary 0-N% right-hand axis — mirrors the
// pbix's lineClusteredColumnComboChart (Ch2's Department/Region trend
// charts), the one genuinely new visual type in this rebuild.
function comboBarLineChart(el, data, barKeys, barColors, barLabels, lineKeys, lineColors, lineLabels, valueFmt = fmtCompact) {
  const perGroup = 190;
  const W = Math.max(el.clientWidth || 480, data.length * perGroup), H = 260;
  const marginL = 54, marginR = 50, marginT = 10, marginB = 46;
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  // The Achievement%/YoY% lines get their OWN reserved band across the top
  // of the plot (not just a secondary scale sharing the bars' full
  // height) — with a shared height, a line's pixel position depends on
  // where its % value falls between 0 and niceMaxPct, which for typical
  // 60-120% figures often lands right at/behind a tall bar's top,
  // hiding the dot and its new value label behind the bar. Confining bars
  // to barAreaTop/barAreaH (below the line band, same baseline as before)
  // and lines to marginT/lineBandH (above it) guarantees the lines always
  // sit above every bar regardless of the actual data.
  const lineBandH = plotH * 0.32, lineBandGap = 22;
  const barAreaTop = marginT + lineBandH + lineBandGap, barAreaH = plotH - lineBandH - lineBandGap;
  const maxRaw = Math.max(1, ...data.flatMap(d => barKeys.map(k => d[k] || 0)));
  const tickVals = niceAxisTicks(maxRaw, valueFmt);
  const maxVal = tickVals[tickVals.length - 1];
  const maxPctRaw = Math.max(150, ...data.flatMap(d => lineKeys.map(k => d[k] || 0)));
  const niceMaxPct = Math.ceil(maxPctRaw / 50) * 50;
  const groupW = plotW / Math.max(data.length, 1);
  const gap = 6;
  const barW = Math.min(28, (groupW - gap * (barKeys.length - 1)) / barKeys.length * 0.9);

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}px" height="${H}">`;
  tickVals.forEach(val => {
    const y = barAreaTop + barAreaH - (barAreaH * val / maxVal);
    svg += `<line class="gridline" x1="${marginL}" x2="${W - marginR}" y1="${y}" y2="${y}"/>`;
    svg += `<text class="axis-label" x="${marginL - 8}" y="${y + 3}" text-anchor="end">${axisTickLabel(val, valueFmt)}</text>`;
  });
  svg += `<line class="baseline" x1="${marginL}" x2="${W - marginR}" y1="${barAreaTop + barAreaH}" y2="${barAreaTop + barAreaH}"/>`;
  const pctStep = niceMaxPct / 4;
  for (let p = 0; p <= niceMaxPct + 0.001; p += pctStep) {
    const y = marginT + lineBandH - (lineBandH * p / niceMaxPct);
    svg += `<text class="axis-label combo-pct-label" x="${W - marginR + 8}" y="${y + 3}" text-anchor="start">${Math.round(p)}%</text>`;
  }

  data.forEach((d, gi) => {
    const groupX = marginL + gi * groupW + groupW / 2 - (barW * barKeys.length + gap * (barKeys.length - 1)) / 2;
    barKeys.forEach((k, si) => {
      const val = d[k] || 0;
      const barH = barAreaH * (val / maxVal);
      const x = groupX + si * (barW + gap);
      const y = barAreaTop + barAreaH - barH;
      svg += `<rect data-tip="${d.label}||${barLabels[si]}||${val}" rx="2" ry="2" x="${x}" y="${y}" width="${barW}" height="${Math.max(barH, 1)}" fill="${barColors[si]}"/>`;
      svg += `<text class="bar-value" x="${x + barW / 2}" y="${y - 3}" text-anchor="middle">${valueFmt(val)}</text>`;
    });
    const label = truncateLabel(d.label, groupW - 8);
    svg += `<text class="axis-label" x="${marginL + gi * groupW + groupW / 2}" y="${H - 24}" text-anchor="middle"><title>${d.label}</title>${label}</text>`;
  });

  const yAt = val => marginT + lineBandH - (lineBandH * Math.min(val, niceMaxPct) / niceMaxPct);
  lineKeys.forEach((k, li) => {
    const pts = data.map((d, gi) => ({ x: marginL + gi * groupW + groupW / 2, y: yAt(d[k]), val: d[k] }))
      .filter(p => p.val != null);
    if (!pts.length) return;
    const path = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    svg += `<path class="combo-line" d="${path}" fill="none" stroke="${lineColors[li]}" stroke-width="2.5"/>`;
  });

  // Dots + value labels are placed per DATA POINT (across both lines
  // together), not per line — Vs. Target and Vs. Last Year cross over
  // (sometimes one is higher, sometimes the other), so a label
  // above/below assignment fixed to a line index can land both labels in
  // the same cramped gap between two close, order-flipped dots. Sorting
  // by actual y at each point instead guarantees the topmost dot always
  // gets the "above" label and the bottom one always gets "below",
  // regardless of which series that happens to be this time.
  data.forEach((d, gi) => {
    const x = marginL + gi * groupW + groupW / 2;
    const here = lineKeys
      .map((k, li) => (d[k] == null ? null : { li, x, y: yAt(d[k]), val: d[k] }))
      .filter(Boolean)
      .sort((a, b) => a.y - b.y);
    here.forEach((p, order) => {
      svg += `<circle class="combo-dot" data-tip="${d.label}||${lineLabels[p.li]}||${p.val.toFixed(1)}%" cx="${p.x}" cy="${p.y}" r="4" fill="${lineColors[p.li]}"/>`;
      const labelY = order === 0 ? p.y - 8 : p.y + 14 + (order - 1) * 12;
      svg += `<text class="combo-pct-value" x="${p.x}" y="${labelY}" text-anchor="middle" fill="${lineColors[p.li]}">${p.val.toFixed(1)}%</text>`;
    });
  });
  svg += `</svg>`;
  el.innerHTML = legendHtml([...barLabels, ...lineLabels], [...barColors, ...lineColors]) + svg;
  attachBarTooltips(el);
  attachValueTooltips(el, '.combo-dot[data-tip]');
  attachLegendScroll(el);
}

// ---------------------------------------------------------------------
// narrative rendering — marked-text ("**bold**"/"##heading##") convention
// shared with the server (_pptx_marked_text in main.py) and with the
// PPTX-notes round-trip.
// ---------------------------------------------------------------------
function escapeHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function markedToHtml(marked) {
  return marked.split(/(\*\*.+?\*\*)/g).map(part => {
    const m = part.match(/^\*\*(.*)\*\*$/);
    return m ? `<b>${escapeHtml(m[1])}</b>` : escapeHtml(part);
  }).join('');
}
function narrativeHtml(text, isOverride) {
  if (!text) return '';
  const blocks = text.split(/\n+/).map(b => b.trim()).filter(Boolean);
  const html = blocks.map(block => {
    const h = block.match(/^##(.*)##$/);
    if (h) return `<h3>${escapeHtml(h[1])}</h3>`;
    return `<p>${markedToHtml(block)}</p>`;
  }).join('');
  return (isOverride ? `<div class="edited-note-tag">${t('Edited note')}</div>` : '') + html;
}

// ---------------------------------------------------------------------
// filter options / page defs
// ---------------------------------------------------------------------
const FRANCHISE_OPTIONS = [
  { v: 'all', l: 'All' }, { v: 'Midea', l: 'Midea' }, { v: 'BEKO', l: 'BEKO' }, { v: 'CANDY', l: 'CANDY' },
];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];
const MONTH_OPTIONS = MONTH_NAMES.map((l, i) => ({ v: i + 1, l }));

// Labels come from t_cstclasstypedesc (per-code display text) — 'mt'/'ws'/
// 'projects' are internal slugs (ref/state-key plumbing) that happen to
// already match their own display labels here (Modern Trade/Whole Sale/
// Projects). See CHANNEL_LABELS in sales_mail_main.py.
const CHANNEL_TOGGLE_OPTIONS = [
  { v: 'dealers', l: 'Dealers' }, { v: 'mt', l: 'Modern Trade' }, { v: 'ws', l: 'Whole Sale' }, { v: 'projects', l: 'Projects' },
];
const REGION_TOGGLE_OPTIONS = [
  { v: 'riyadh', l: 'Riyadh' }, { v: 'qassim', l: 'Qassim' }, { v: 'western', l: 'Western' }, { v: 'eastern', l: 'Eastern' },
];

// Rebuilt from the client's actual Power BI source (HHS_SalesData_Analysis.pbix)
// — see plan revision 2. Drives each toggle-page's toggle-button row (the
// section numbering/order below is purely static — see the .pbi-page
// sections in the template, always rendered stacked in this order, no
// page-picker to keep in sync).
const PAGE_DEFS = [
  { slug: 'total-company', title: 'Total Company' },
  { slug: 'dept-region-trends', title: 'Department & Region Performance Trends' },
  { slug: 'quarterly-company', title: 'Quarterly Sales Progression — Company' },
  { slug: 'quarterly-department', title: 'Quarterly Progression by Department', toggle: { key: 'quarterlyDepartment', options: CHANNEL_TOGGLE_OPTIONS } },
  { slug: 'quarterly-region', title: 'Quarterly Progression by Region (Dealers)', toggle: { key: 'quarterlyRegion', options: REGION_TOGGLE_OPTIONS } },
  { slug: 'main-groups', title: 'Main Groups — MTD & YTD' },
  { slug: 'subgroups-top8', title: 'Product Sub-Groups — Top 8 (YTD)' },
  { slug: 'subgroups-distribution', title: 'Sub-Groups Distribution — LY vs TY' },
  { slug: 'maingroups-distribution', title: 'Main Groups Distribution — LY vs TY' },
  { slug: 'departments', title: 'Departments — MTD & YTD' },
  { slug: 'departments-distribution', title: 'Departments Distribution — LY vs TY' },
  { slug: 'lcac-subgroups', title: 'LCAC Sub-Groups' },
  { slug: 'top3-by-channel', title: 'Top-3 Sub-Groups by Channel', toggle: { key: 'top3ByChannel', options: CHANNEL_TOGGLE_OPTIONS } },
  { slug: 'regions-by-channel', title: 'Regions by Channel', toggle: { key: 'regionsByChannel', options: CHANNEL_TOGGLE_OPTIONS } },
  { slug: 'dealers-region-maingroups', title: 'Dealers by Region — Main Groups', toggle: { key: 'dealersRegionMaingroups', options: REGION_TOGGLE_OPTIONS } },
  { slug: 'dealers-region-subgroups', title: 'Dealers by Region — Split Sub-Groups', toggle: { key: 'dealersRegionSubgroups', options: REGION_TOGGLE_OPTIONS } },
  { slug: 'projects-productgroups', title: 'Projects — Product Groups (YTD)' },
];

// Short "what process is behind this card" text shown by the (i) info
// icons next to the header and each section's h2, on hover — plain
// technical description of the data source/formula/comparison logic
// (distinct from the data-driven "narrative" business commentary in the
// .narrative panels). Kept English-only (not run through addLabels/t()):
// these are formula/column-name descriptions, not UI chrome. See
// sales_mail_main.py (AMOUNT_EXPR, BASE_SCOPE_SQL,
// MAIN_GROUP_EXPR_DERIVED, CHANNEL_DIM_EXPR, _breakdown_by_quarter,
// _with_pct) for the source of every figure below.
const PROCESS_NOTES = {
  scope: `All figures here are scoped to the Midea AC product family plus the BEKO and CANDY product groups, and exclude dealer accounts whose customer code starts with "V". <b>Value</b> = SUM(Quantity × (Unit Price − Discount − Special Discount)), not the raw Amount field (only ~14% populated). <b>Quantity</b> = SUM(bi_qty), same scope/filters as Value — no extra countable-unit restriction. Target = the separate budget feed. Use the Franchise filter to narrow to Midea, BEKO or CANDY (default All covers all three).`,
  'kpi-amount': `Company-wide Value totals for the selected Month (MTD) and Jan-through-Month (YTD): This Year, Target (budget) and Last Year. "vs LY" = This Year ÷ Last Year × 100; "Achv" = This Year ÷ Target × 100.`,
  'kpi-qty': `Same MTD/YTD/This Year/Target/Last Year comparison as the Amount tiles above, but counting units (SUM of bi_qty) instead of value, same scope/filters as Value.`,
  'total-company': `4 separate totals for the selected Month (MTD) and Jan-through-Month (YTD), by Value and by Qty — same formulas and This Year/Target/Last Year comparison as the KPI tiles above, just re-shown as bars.`,
  'dept-region-trends': `YTD Value by Department (Dealers/Modern Trade/Whole Sale/Projects) and by Dealer Region (Riyadh/Qassim/Western/Eastern, Dealers channel only). Achievement % = YTD Actual ÷ YTD Target × 100; YoY % = YTD Actual ÷ Last-Year YTD × 100 (a ratio to last year, not a growth rate).`,
  'quarterly-company': `Calendar-year Q1 through the quarter containing the selected month. This-Year actual is capped at the selected month so later months in the current quarter don't leak in; Target and Last Year are shown for the full quarter.`,
  'quarterly-department': `Same quarterly logic as the company view, filtered to the department selected above (Dealers/Modern Trade/Whole Sale/Projects).`,
  'quarterly-region': `Same quarterly logic as the company view, filtered to the Dealers channel and the region selected above.`,
  'main-groups': `"Main Group" isn't a stored column — it's derived from the product group code into 5 buckets (Windows/Split/CAC/LCAC/Others). MTD and YTD Value per bucket, This Year vs Target vs Last Year.`,
  'subgroups-top8': `The 8 product sub-groups with the highest YTD Value, ranked This-Year-sales descending. The same 8 groups feed the distribution donuts on the next page.`,
  'subgroups-distribution': `The same Top-8 sub-group YTD data as the previous page, split into two donuts showing each group's share of the total — one for Last Year, one for This Year.`,
  'maingroups-distribution': `The same 5 derived Main-Group buckets as the Main Groups page, split into Last-Year-share vs This-Year-share donuts.`,
  'departments': `MTD and YTD totals per department (Dealers/Modern Trade/Whole Sale/Projects), by Value and by Qty — This Year vs Target vs Last Year.`,
  'departments-distribution': `The same department YTD data as the previous page, split into Last-Year vs This-Year share donuts, for both Value and Qty.`,
  'lcac-subgroups': `Product sub-groups filtered to Main Group = LCAC only. MTD and YTD Value per sub-group.`,
  'top3-by-channel': `The 3 product sub-groups with the highest YTD Qty within the department selected above (Value and Qty shown side by side, ranked by Qty).`,
  'regions-by-channel': `The 4 fixed dealer regions, YTD Qty, filtered to the department selected above.`,
  'dealers-region-maingroups': `The 5 derived Main-Group buckets, YTD Value, filtered to the Dealers channel and the region selected above.`,
  'dealers-region-subgroups': `Product sub-groups filtered to the Dealers channel, Main Group = Split, and the region selected above — top 8 by YTD Qty.`,
  'projects-productgroups': `Product groups filtered to the Projects channel, top 8 by YTD Value.`,
};

export class PbiSalesMailDashboardNew extends Component {
  static template = "pbi_dashboards.sales_mail_dashboard_new";
  static props = ["*"];

  get isDebugMode() {
    return Boolean(window.odoo && window.odoo.debug);
  }

  setup() {
    this.rpc = useService("rpc");
    this.t = t;
    this.isArabicUI = isArabicUI;
    this.franchiseOptions = FRANCHISE_OPTIONS;
    this.monthOptions = MONTH_OPTIONS;
    this.pages = PAGE_DEFS;
    // See load()'s comment below — request-ordering guard + the
    // exportPdf()-awaits-in-flight-load guard both key off these.
    this._loadSeq = 0;
    this._loadPromise = null;

    this.state = useState({
      year: null, month: null, franchise: 'Midea',
      loading: false, error: '',
      yearOptions: [], periodLabel: '', hasPrevYear: false,
      filtersCollapsed: false,
      toggleState: {
        quarterlyDepartment: 'dealers', quarterlyRegion: 'riyadh',
        top3ByChannel: 'dealers', regionsByChannel: 'dealers',
        dealersRegionMaingroups: 'riyadh', dealersRegionSubgroups: 'riyadh',
      },
    });

    this.rootRef = useRef('root');
    const refNames = [
      'kpiAmountRow', 'kpiQtyRow', 'tooltip', 'importNotesInput',
      'totalCompanyMtdValueChart', 'totalCompanyMtdQtyChart', 'totalCompanyYtdValueChart', 'totalCompanyYtdQtyChart', 'totalCompanyNotes',
      'deptTrendChart', 'regionTrendChart', 'deptRegionTrendsNotes',
      'quarterlyCompanyChart', 'quarterlyCompanyNotes',
      ...['dealers', 'mt', 'ws', 'projects'].flatMap(s => [`quarterlyDepartmentChart_${s}`, `quarterlyDepartmentNotes_${s}`]),
      ...['riyadh', 'qassim', 'western', 'eastern'].flatMap(s => [`quarterlyRegionChart_${s}`, `quarterlyRegionNotes_${s}`]),
      'mainGroupsMtdChart', 'mainGroupsYtdChart', 'mainGroupsNotes',
      'subgroupsTop8ValueChart', 'subgroupsTop8QtyChart', 'subgroupsTop8Notes',
      'subgroupsDistributionDonutLY', 'subgroupsDistributionDonutTY', 'subgroupsDistributionNotes',
      'maingroupsDistributionDonutLY', 'maingroupsDistributionDonutTY', 'maingroupsDistributionNotes',
      'departmentsMtdValueChart', 'departmentsMtdQtyChart', 'departmentsYtdValueChart', 'departmentsYtdQtyChart', 'departmentsNotes',
      'departmentsDistributionDonutValueLY', 'departmentsDistributionDonutValueTY',
      'departmentsDistributionDonutQtyLY', 'departmentsDistributionDonutQtyTY', 'departmentsDistributionNotes',
      'lcacSubgroupsMtdChart', 'lcacSubgroupsYtdChart', 'lcacSubgroupsNotes',
      ...['dealers', 'mt', 'ws', 'projects'].flatMap(s => [`top3ByChannelValueChart_${s}`, `top3ByChannelQtyChart_${s}`, `top3ByChannelNotes_${s}`]),
      ...['dealers', 'mt', 'ws', 'projects'].flatMap(s => [`regionsByChannelValueChart_${s}`, `regionsByChannelQtyChart_${s}`, `regionsByChannelNotes_${s}`]),
      ...['riyadh', 'qassim', 'western', 'eastern'].flatMap(s => [`dealersRegionMaingroupsChart_${s}`, `dealersRegionMaingroupsNotes_${s}`]),
      ...['riyadh', 'qassim', 'western', 'eastern'].flatMap(s => [`dealersRegionSubgroupsChart_${s}`, `dealersRegionSubgroupsNotes_${s}`]),
      'projectsProductgroupsValueChart', 'projectsProductgroupsQtyChart', 'projectsProductgroupsNotes',
    ];
    this.refs = {};
    for (const name of refNames) this.refs[name] = useRef(name);

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

  // -- (i) process-note icons: hover shows what data/formula backs a
  // section, reusing the same tooltip element as the chart bar tooltips.
  onInfoEnter(ev, key) { showTip(ev, PROCESS_NOTES[key] || '', true); }
  onInfoLeave() { hideTip(); }

  // -- filters ----------------------------------------------------------
  selectYear(v) { this.state.year = +v; this.load(); }
  selectMonth(v) { this.state.month = +v; this.load(); }
  selectFranchise(v) { this.state.franchise = v; this.load(); }
  // Hides/shows the Year/Month/Franchise filters AND the Export PDF/
  // PowerPoint/Import Notes row together (one panel, one toggle) — unlike
  // sales_kpi_dashboard's toggleToolbar, there's no separate always-visible
  // nav row here to leave in place, so the whole .filters block collapses.
  toggleFilters() { this.state.filtersCollapsed = !this.state.filtersCollapsed; }

  setToggle(key, v) { this.state.toggleState[key] = v; }

  seriesColors() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    // [This Year, Target, Last Year] — bar order/meaning throughout.
    return [style.getPropertyValue('--series-1').trim(), style.getPropertyValue('--series-3').trim(),
            style.getPropertyValue('--series-2').trim()];
  }
  lineColors() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    return [style.getPropertyValue('--series-5').trim(), style.getPropertyValue('--series-6').trim()];
  }

  // Waits out any in-flight load() first (e.g. a filter changed and its
  // request hasn't resolved yet) so window.print() always snapshots the
  // currently-selected Year/Month/Franchise's data, never whatever was on
  // screen before that request started — see load()'s comment.
  async exportPdf() {
    if (this._loadPromise) await this._loadPromise;
    window.print();
  }

  exportPptx() {
    const params = new URLSearchParams({
      period: `${this.state.year}-${String(this.state.month).padStart(2, '0')}`,
      franchise: this.state.franchise,
    });
    window.open(`/pbi_dashboards/sales_mail_new/export.pptx?${params}`, '_blank');
  }

  async importNotes(ev) {
    const file = ev.target.files && ev.target.files[0];
    ev.target.value = '';
    if (!file) return;
    this.state.loading = true;
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('period', `${this.state.year}-${String(this.state.month).padStart(2, '0')}`);
      fd.append('franchise', this.state.franchise);
      fd.append('csrf_token', odoo.csrf_token);
      const response = await fetch('/pbi_dashboards/sales_mail_new/import_notes', { method: 'POST', body: fd });
      const json = await response.json();
      if (json.error) { this.state.error = json.error; return; }
      if (!Object.keys(json.notes).length) {
        this.state.error = t("No edited narrative notes were found — the file's speaker notes matched the dashboard's current text.");
        return;
      }
      this.state.error = '';
      const [y, m] = json.period.split('-');
      this.state.year = +y; this.state.month = +m; this.state.franchise = json.franchise;
      await this.load();
    } catch (e) {
      this.state.error = t('Failed to import notes — ') + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  // -- data load ----------------------------------------------------------
  // Every filter change (selectYear/selectMonth/selectFranchise) calls
  // load() immediately, with no debounce — two picks made in quick
  // succession (e.g. Year then Month before the Year-only request has
  // resolved) fire two overlapping requests. Network timing doesn't
  // guarantee they resolve in the order they were sent, so without a
  // guard the OLDER request could resolve last and overwrite the newer
  // selection's data with stale figures (this.lastJson, state.year/month,
  // every chart) — the dashboard would then silently show/export the
  // wrong period even though the filter controls display the latest pick.
  // this._loadSeq tags each call; a response is only applied if it's
  // still the most recently-started one by the time it resolves.
  // this._loadPromise lets exportPdf() below await any load already in
  // flight instead of printing whatever was on screen before it started.
  load() {
    const seq = ++this._loadSeq;
    this.state.loading = true;
    this.state.error = '';
    this._loadPromise = this._loadImpl(seq);
    return this._loadPromise;
  }

  async _loadImpl(seq) {
    try {
      const period = (this.state.year && this.state.month) ? `${this.state.year}-${String(this.state.month).padStart(2, '0')}` : null;
      const res = await this.rpc('/pbi_dashboards/sales_mail_new/data', { period, franchise: this.state.franchise });
      if (seq !== this._loadSeq) return;
      if (res.error) { this.state.error = res.error; return; }
      this.lastJson = res;
      this.state.year = res.period.year;
      this.state.month = res.period.month;
      this.state.periodLabel = tDate(res.period.label);
      this.state.hasPrevYear = res.hasPrevYear;
      this.state.yearOptions = res.yearOptions;
      this.renderAll();
    } catch (e) {
      if (seq !== this._loadSeq) return;
      this.state.error = t('Failed to load — ') + e.message;
    } finally {
      if (seq === this._loadSeq) this.state.loading = false;
    }
  }

  // -- KPI tiles: 6 Amount + 6 Qty (This Year/Target/Last Year, with the
  // achievement%/YoY% badges folded into the This-Year/Target tile). --
  renderKpis() {
    const k = this.lastJson.kpis;
    // NB: 'tile' is used below (not 't') as the per-tile loop variable name —
    // this dashboard's KPI-tile object was historically named `t`, which
    // would shadow the imported pbi_i18n t() translator inside these
    // closures, so all chrome words (MTD/YTD/Actual/…) are translated up
    // front via the module-level t() before the tile objects are built.
    const mtdLabel = t('MTD'), ytdLabel = t('YTD'), actualLabel = t('Actual');
    const subBadge = (value, comparedTo, prefix) => {
      const p = pct(value, comparedTo);
      if (p == null) return '';
      const cls = p >= 100 ? 'good' : 'bad';
      return `<div class="sub">${prefix} <span class="${cls}">${fmtPct(p)}</span></div>`;
    };
    const block = (fmtFn, thisYear, target, lastYear) => [
      { value: fmtFn(thisYear), raw: fmt(thisYear), suffix: t('This Year'), sub: subBadge(thisYear, lastYear, t('vs LY')) },
      { value: fmtFn(target), raw: fmt(target), suffix: t('Target'), sub: subBadge(thisYear, target, t('Achv')) },
      { value: fmtFn(lastYear), raw: fmt(lastYear), suffix: t('Last Year'), sub: '' },
    ];
    const amountTiles = [
      ...block(fmtM, k.mtdThisYear, k.mtdTarget, k.mtdLastYear).map(tile => ({ ...tile, label: `${mtdLabel} - ${tile.suffix}` })),
      ...block(fmtM, k.ytdThisYear, k.ytdTarget, k.ytdLastYear).map(tile => ({ ...tile, label: `${ytdLabel} - ${tile.suffix}` })),
    ];
    const qtyTiles = [
      ...block(fmtK, k.mtdQtyThisYear, k.mtdQtyTarget, k.mtdQtyLastYear).map(tile => ({ ...tile, label: `${mtdLabel} - ${tile.suffix}` })),
      ...block(fmtK, k.ytdQtyThisYear, k.ytdQtyTarget, k.ytdQtyLastYear).map(tile => ({ ...tile, label: `${ytdLabel} - ${tile.suffix}` })),
    ];
    const tileHtml = (tile, i) => `
      <div class="pbi-kpi tile-color-${i % 3}" data-tip="${tile.label}||${actualLabel}||${tile.raw}">
        <div class="value">${tile.value}</div>
        <div class="label">${tile.label}</div>
        ${tile.sub}
      </div>`;
    this.refs.kpiAmountRow.el.innerHTML = amountTiles.map(tileHtml).join('');
    this.refs.kpiQtyRow.el.innerHTML = qtyTiles.map(tileHtml).join('');
    attachValueTooltips(this.refs.kpiAmountRow.el, '.pbi-kpi[data-tip]');
    attachValueTooltips(this.refs.kpiQtyRow.el, '.pbi-kpi[data-tip]');
  }

  // -- narrative panel: notes override wins over the computed narrative --
  putNarrative(ref, key) {
    const override = this.lastJson.notes[key];
    ref.el.innerHTML = narrativeHtml(override || this.lastJson.narratives[key] || '', !!override);
  }

  renderAll() {
    const colors = this.seriesColors();
    const lineColors = this.lineColors();
    const valueSeries = ['sales', 'budget', 'prevYearSales'];
    const qtySeries = ['qty', 'budgetQty', 'prevYearQty'];
    const seriesLabels = [t('This Year'), t('Target'), t('Last Year')];
    const trendLineLabels = [t('Vs. Target'), t('Vs. Last Year')];
    const j = this.lastJson;

    this.renderKpis();

    // Page 1 — Total Company (4 separate "3-bar, no category" charts)
    groupedBarChart(this.refs.totalCompanyMtdValueChart.el, j.totalCompany.mtd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.totalCompanyMtdQtyChart.el, j.totalCompany.mtd, qtySeries, colors, seriesLabels, fmtK);
    groupedBarChart(this.refs.totalCompanyYtdValueChart.el, j.totalCompany.ytd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.totalCompanyYtdQtyChart.el, j.totalCompany.ytd, qtySeries, colors, seriesLabels, fmtK);
    this.putNarrative(this.refs.totalCompanyNotes, 'total-company');

    // Page 2 — Department & Region Performance Trends (combo charts)
    comboBarLineChart(this.refs.deptTrendChart.el, j.deptTrend, valueSeries, colors, seriesLabels,
      ['achievementPct', 'yoyPct'], lineColors, trendLineLabels, fmtM);
    comboBarLineChart(this.refs.regionTrendChart.el, j.regionTrend, valueSeries, colors, seriesLabels,
      ['achievementPct', 'yoyPct'], lineColors, trendLineLabels, fmtM);
    this.putNarrative(this.refs.deptRegionTrendsNotes, 'dept-region-trends');

    // Page 3 — Quarterly Sales Progression — Company
    groupedBarChart(this.refs.quarterlyCompanyChart.el, j.quarterlyCompany, valueSeries, colors, seriesLabels, fmtM);
    this.putNarrative(this.refs.quarterlyCompanyNotes, 'quarterly-company');

    // Page 4 — Quarterly Progression by Department (toggle)
    for (const slug of ['dealers', 'mt', 'ws', 'projects']) {
      groupedBarChart(this.refs[`quarterlyDepartmentChart_${slug}`].el, j.quarterlyDepartment[slug], valueSeries, colors, seriesLabels, fmtM);
      this.putNarrative(this.refs[`quarterlyDepartmentNotes_${slug}`], `quarterly-department_${slug}`);
    }

    // Page 5 — Quarterly Progression by Region (toggle)
    for (const slug of ['riyadh', 'qassim', 'western', 'eastern']) {
      groupedBarChart(this.refs[`quarterlyRegionChart_${slug}`].el, j.quarterlyRegion[slug], valueSeries, colors, seriesLabels, fmtM);
      this.putNarrative(this.refs[`quarterlyRegionNotes_${slug}`], `quarterly-region_${slug}`);
    }

    // Page 6 — Main Groups — MTD & YTD
    groupedBarChart(this.refs.mainGroupsMtdChart.el, j.mainGroups.mtd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.mainGroupsYtdChart.el, j.mainGroups.ytd, valueSeries, colors, seriesLabels, fmtM);
    this.putNarrative(this.refs.mainGroupsNotes, 'main-groups');

    // Page 7 — Product Sub-Groups — Top 8 (YTD)
    groupedBarChart(this.refs.subgroupsTop8ValueChart.el, j.subgroupsTop8, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.subgroupsTop8QtyChart.el, byQtyDesc(j.subgroupsTop8), qtySeries, colors, seriesLabels, fmtK);
    this.putNarrative(this.refs.subgroupsTop8Notes, 'subgroups-top8');

    // Page 8 — Sub-Groups Distribution — LY vs TY
    donutChart(this.refs.subgroupsDistributionDonutLY.el, j.subgroupsTop8.map(d => ({ label: d.label, value: d.prevYearSales })), PALETTE, fmtM);
    donutChart(this.refs.subgroupsDistributionDonutTY.el, j.subgroupsTop8.map(d => ({ label: d.label, value: d.sales })), PALETTE, fmtM);
    this.putNarrative(this.refs.subgroupsDistributionNotes, 'subgroups-distribution');

    // Page 9 — Main Groups Distribution — LY vs TY
    donutChart(this.refs.maingroupsDistributionDonutLY.el, j.mainGroups.ytd.map(d => ({ label: d.label, value: d.prevYearSales })), PALETTE, fmtM);
    donutChart(this.refs.maingroupsDistributionDonutTY.el, j.mainGroups.ytd.map(d => ({ label: d.label, value: d.sales })), PALETTE, fmtM);
    this.putNarrative(this.refs.maingroupsDistributionNotes, 'maingroups-distribution');

    // Page 10 — Departments — MTD & YTD
    groupedBarChart(this.refs.departmentsMtdValueChart.el, j.departments.mtd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.departmentsMtdQtyChart.el, byQtyDesc(j.departments.mtd), qtySeries, colors, seriesLabels, fmtK);
    groupedBarChart(this.refs.departmentsYtdValueChart.el, j.departments.ytd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.departmentsYtdQtyChart.el, byQtyDesc(j.departments.ytd), qtySeries, colors, seriesLabels, fmtK);
    this.putNarrative(this.refs.departmentsNotes, 'departments');

    // Page 11 — Departments Distribution — LY vs TY
    donutChart(this.refs.departmentsDistributionDonutValueLY.el, j.departments.ytd.map(d => ({ label: d.label, value: d.prevYearSales })), PALETTE, fmtM);
    donutChart(this.refs.departmentsDistributionDonutValueTY.el, j.departments.ytd.map(d => ({ label: d.label, value: d.sales })), PALETTE, fmtM);
    donutChart(this.refs.departmentsDistributionDonutQtyLY.el, byQtyDesc(j.departments.ytd).map(d => ({ label: d.label, value: d.prevYearQty })), PALETTE, fmtK);
    donutChart(this.refs.departmentsDistributionDonutQtyTY.el, byQtyDesc(j.departments.ytd).map(d => ({ label: d.label, value: d.qty })), PALETTE, fmtK);
    this.putNarrative(this.refs.departmentsDistributionNotes, 'departments-distribution');

    // Page 12 — LCAC Sub-Groups
    groupedBarChart(this.refs.lcacSubgroupsMtdChart.el, j.lcacSubgroups.mtd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.lcacSubgroupsYtdChart.el, j.lcacSubgroups.ytd, valueSeries, colors, seriesLabels, fmtM);
    this.putNarrative(this.refs.lcacSubgroupsNotes, 'lcac-subgroups');

    // Page 13 — Top-3 Sub-Groups by Channel (toggle)
    for (const slug of ['dealers', 'mt', 'ws', 'projects']) {
      const rows = j.top3ByChannel[slug];
      groupedBarChart(this.refs[`top3ByChannelValueChart_${slug}`].el, rows, valueSeries, colors, seriesLabels, fmtM);
      groupedBarChart(this.refs[`top3ByChannelQtyChart_${slug}`].el, byQtyDesc(rows), qtySeries, colors, seriesLabels, fmtK);
      this.putNarrative(this.refs[`top3ByChannelNotes_${slug}`], `top3-by-channel_${slug}`);
    }

    // Page 14 — Regions by Channel (toggle)
    for (const slug of ['dealers', 'mt', 'ws', 'projects']) {
      const rows = j.regionsByChannel[slug];
      groupedBarChart(this.refs[`regionsByChannelValueChart_${slug}`].el, rows, valueSeries, colors, seriesLabels, fmtM);
      groupedBarChart(this.refs[`regionsByChannelQtyChart_${slug}`].el, byQtyDesc(rows), qtySeries, colors, seriesLabels, fmtK);
      this.putNarrative(this.refs[`regionsByChannelNotes_${slug}`], `regions-by-channel_${slug}`);
    }

    // Page 15 — Dealers by Region — Main Groups (toggle)
    for (const slug of ['riyadh', 'qassim', 'western', 'eastern']) {
      groupedBarChart(this.refs[`dealersRegionMaingroupsChart_${slug}`].el, j.dealersRegionMaingroups[slug], valueSeries, colors, seriesLabels, fmtM);
      this.putNarrative(this.refs[`dealersRegionMaingroupsNotes_${slug}`], `dealers-region-maingroups_${slug}`);
    }

    // Page 16 — Dealers by Region — Split Sub-Groups (toggle)
    for (const slug of ['riyadh', 'qassim', 'western', 'eastern']) {
      groupedBarChart(this.refs[`dealersRegionSubgroupsChart_${slug}`].el, byQtyDesc(j.dealersRegionSubgroups[slug]), qtySeries, colors, seriesLabels, fmtK);
      this.putNarrative(this.refs[`dealersRegionSubgroupsNotes_${slug}`], `dealers-region-subgroups_${slug}`);
    }

    // Page 17 — Projects — Product Groups (YTD)
    groupedBarChart(this.refs.projectsProductgroupsValueChart.el, j.projectsProductgroups, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.projectsProductgroupsQtyChart.el, byQtyDesc(j.projectsProductgroups), qtySeries, colors, seriesLabels, fmtK);
    this.putNarrative(this.refs.projectsProductgroupsNotes, 'projects-productgroups');
  }
}

registry.category("actions").add("pbi_dashboards.sales_mail_dashboard_new", PbiSalesMailDashboardNew);
