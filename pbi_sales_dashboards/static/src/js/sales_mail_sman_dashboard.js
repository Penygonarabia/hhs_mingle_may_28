/** @odoo-module **/

import { Component, useState, useRef, onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { t, tDate, addLabels, isArabicUI } from "@pbi_dashboards/js/pbi_i18n";
// These come from the shared chart library rather than being copied in: this
// file carries its own groupedBarChart, but anything that has to MEASURE real
// rendered text — fitting a caption to its slot, sizing a chart to its value
// labels, spreading donut labels apart — has one implementation, and it lives
// there.
import { fitCaptionsToSlot, markAllCaptionsForTooltip, attachCaptionTooltips,
         setTooltipEl, clearTooltipEl, attachLegendFilter,
         labelFont, textWidth, widestValueLabel, spreadDonutLabels,
         VALUE_LABEL_GAP } from "@pbi_dashboards/js/pbi_chart_lib";


// "Sales Analysis with Salesman" — the 17-page stacked report layout of
// sales_mail_dashboard_new.js drawn on the data source of
// sales_sman_dashboard.js: actuals from transaction_header /
// transaction_details (credit notes netted, scoped to the AC product
// groups by product_category.code -- ACACC, ACCON, ACCST, ACPAC, ACPKG,
// ACAIP, ACPOR, ACVRF, ACWIN, ACWTS, ACHCL, ATOM), targets from
// v_sales_budget_month. The scope used to be catalogflags flag '10'; that
// rule is gone -- the tag is still synced, but nothing reads it. See
// pbi_sales_dashboards/controllers/sales_mail_sman_main.py for the dimension
// mapping — bidata's channel/region/main-group taxonomy does not exist on
// the legacy tables, so Department becomes Partner Classification, Main
// Group becomes Main Category and Sub-Group becomes Sub Category.
//
// Salesman is a global FILTER here rather than a chart dimension: every
// page narrows with it, exactly as the period does.
//
// The customer-side grouping is the SALES TYPE GROUP (l1) on every page
// that is about one grouping — 4, 5, 10, 11, 15, 16, 17 — rather than the
// Partner Classification it used to be: l1 has no Unassigned bucket in
// scope and is the level the budget is captured at, so those bars tie to
// the Target tile above them. Pages 2, 13 and 14 are still about the
// classification itself and stay on l2.
//
// The three toggle rows are data-driven — q1..q4 are the quarters up to the
// selected month (pages 4 and 5, quarter as the tab and categories as the
// bars), c1..c4 the four largest Partner Classifications and r1..r4 the
// four largest Regions. The slugs are fixed (refs and note keys must
// survive a period change); only the labels move, and they arrive in the
// payload as quarterTabs / classTabs / regionTabs. Gated by its own menu grant
// (menu_pbi_sales_mail_dashboard_sman), per this module's one-grant-per-leaf
// convention.
addLabels({
  // header/footer
  "Sales Analysis with Salesman": "تحليل المبيعات مع مندوب المبيعات",
  "Sales Dashboards": "لوحات معلومات المبيعات",
  "Target": "الهدف",
  "Vs. Target": "مقابل الهدف",
  // filters
  "Filters, Export & Notes": "الفلاتر والتصدير والملاحظات",
  "Filters & Export": "الفلاتر والتصدير",
  "Levels": "المستويات",
  "Sale Type / Channel": "نوع البيع / القناة",
  "Partner Classification": "تصنيف الشريك",
  "Region": "المنطقة",
  "City": "المدينة",
  "Customer": "العميل",
  "Main Category": "الفئة الرئيسية",
  "Sub Category": "الفئة الفرعية",
  "Product Group": "مجموعة المنتجات",
  "Product Sub-Group": "المجموعة الفرعية للمنتجات",
  "Export": "تصدير",
  "Export PowerPoint": "تصدير PowerPoint",
  "Notes": "الملاحظات",
  "Edit Notes": "تعديل الملاحظات",
  "Save Notes": "حفظ الملاحظات",
  "Cancel": "إلغاء",
  "Saving…": "جارٍ الحفظ…",
  "Requirement": "المطلوب",
  "Analysis note": "ملاحظة التحليل",
  "What should this section cover?": "ما الذي يجب أن يغطيه هذا القسم؟",
  "Reset": "إعادة التعيين",
  "Reset this section to its computed note and clear its requirement": "إعادة تعيين هذا القسم إلى ملاحظته المحسوبة ومسح المطلوب منه",
  "Reset All": "إعادة تعيين الكل",
  "Reset all notes": "إعادة تعيين جميع الملاحظات",
  "Reset all sections to the default computed notes": "إعادة تعيين جميع الأقسام إلى الملاحظات المحسوبة الافتراضية",
  "Reset the notes and requirements on every section back to the computed defaults? Nothing is deleted until you press Save Notes — Cancel still undoes this.": "هل تريد إعادة الملاحظات والمتطلبات في كل قسم إلى القيم المحسوبة الافتراضية؟ لن يتم حذف أي شيء حتى تضغط على حفظ الملاحظات — ولا يزال بإمكانك التراجع بالضغط على إلغاء.",
  "All sections reset to the computed defaults — press Save Notes to keep it.": "تمت إعادة تعيين جميع الأقسام إلى القيم المحسوبة الافتراضية — اضغط على حفظ الملاحظات للاحتفاظ بها.",
  "Preset requirement…": "متطلب جاهز…",
  "Predefined": "جاهزة",
  "Added here": "مضافة هنا",
  "Add to list": "إضافة إلى القائمة",
  "Remove from list": "إزالة من القائمة",
  "Added to the list.": "تمت الإضافة إلى القائمة.",
  "Removed from the list.": "تمت الإزالة من القائمة.",
  "Already in the list.": "موجود بالفعل في القائمة.",
  "Write a requirement first.": "اكتب المتطلب أولاً.",
  "Only a requirement added here can be removed.": "يمكن إزالة المتطلبات المضافة هنا فقط.",
  // predefined requirements — the dropdown above every requirement box
  "Lead with achievement against target, then the year-on-year move.":
    "ابدأ بنسبة الإنجاز مقابل الهدف، ثم التغير السنوي.",
  "Name the top three contributors and the share of the total they hold.":
    "اذكر أكبر ثلاثة مساهمين وحصتهم من الإجمالي.",
  "Call out the widest gap to target and what it costs in value.":
    "أبرز أكبر فجوة عن الهدف وتكلفتها بالقيمة.",
  "Compare with the same period last year, in value and in units.":
    "قارن بنفس الفترة من العام الماضي، بالقيمة وبالكمية.",
  "Say which lines are growing and which are falling, with the percentages.":
    "وضّح أي البنود ينمو وأيها يتراجع، مع النسب.",
  "Flag anything below 50% achievement explicitly.":
    "أشر صراحةً إلى أي إنجاز أقل من 50٪.",
  "Explain what moved the numbers rather than restating them.":
    "اشرح ما الذي حرّك الأرقام بدلاً من إعادة ذكرها.",
  "Keep it to two short paragraphs, numbers first.":
    "اجعلها في فقرتين قصيرتين، الأرقام أولاً.",
  "Filters are locked while notes are being edited.": "الفلاتر مقفلة أثناء تعديل الملاحظات.",
  "No changes to save.": "لا توجد تغييرات للحفظ.",
  "Failed to save notes — ": "فشل حفظ الملاحظات — ",
  "unsaved change": "تغيير غير محفوظ",
  "unsaved changes": "تغييرات غير محفوظة",
  "Salesman": "مندوب المبيعات",
  "Sub-category View": "عرض الفئة الفرعية",
  "Regular": "عادي",
  "Manager": "مدير",
  "All": "الكل",
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
  "Scope": "النطاق",
  "AC product groups": "مجموعات منتجات التكييف",
  "Show all": "عرض الكل",
  "No target for a single salesman": "لا يوجد هدف لمندوب مبيعات واحد",
  "Vs. Last Year": "مقابل العام الماضي",
  "Show more": "عرض المزيد",
  "Back to start": "العودة إلى البداية",
  "Edited note": "ملاحظة معدَّلة",
  // section headings
  "Total Company": "إجمالي الشركة",
  "Sales Type Group & Region Performance Trends (YTD)": "اتجاهات أداء مجموعة نوع المبيعات والمناطق (حتى تاريخه السنوي)",
  "By Sales Type Group — Achievement % / YoY %": "حسب مجموعة نوع المبيعات — نسبة الإنجاز٪ / التغير السنوي٪",
  "By Region — Achievement % / YoY %": "حسب المنطقة — نسبة الإنجاز٪ / التغير السنوي٪",
  "Quarterly Sales Progression — Company": "التطور الفصلي للمبيعات — الشركة",
  "Sales Type Groups by Quarter": "مجموعات نوع المبيعات حسب الربع",
  "Regions by Quarter": "المناطق حسب الربع",
  "Sales Type Groups": "مجموعات نوع المبيعات",
  "Main Categories — MTD & YTD": "الفئات الرئيسية — حتى تاريخه الشهري والسنوي",
  "Main Categories": "الفئات الرئيسية",
  "Sub-Categories — Top 8 (YTD)": "الفئات الفرعية — أفضل 8 (حتى تاريخه السنوي)",
  "Sub-Categories Distribution — LY vs TY (Top 8, YTD)": "توزيع الفئات الفرعية — العام الماضي مقابل العام الحالي (أفضل 8، حتى تاريخه السنوي)",
  "Product Groups — Top 10 (YTD)": "مجموعات المنتجات — أفضل 10 (حتى تاريخه السنوي)",
  "Product Groups Distribution — LY vs TY (Top 10, YTD)": "توزيع مجموعات المنتجات — العام الماضي مقابل العام الحالي (أفضل 10، حتى تاريخه السنوي)",
  "Split Product Sub-Groups — Top 10 (YTD)": "مجموعات المنتجات الفرعية Split — أفضل 10 (حتى تاريخه السنوي)",
  "Split Product Sub-Groups Distribution — LY vs TY (Top 10, YTD)": "توزيع مجموعات المنتجات الفرعية Split — العام الماضي مقابل العام الحالي (أفضل 10، حتى تاريخه السنوي)",
  "Main Categories Distribution — LY vs TY (YTD)": "توزيع الفئات الرئيسية — العام الماضي مقابل العام الحالي (حتى تاريخه السنوي)",
  "Sales Type Groups Distribution — LY vs TY (YTD)": "توزيع مجموعات نوع المبيعات — العام الماضي مقابل العام الحالي (حتى تاريخه السنوي)",
  "Top Main Category — Sub-Categories": "الفئة الرئيسية الأعلى — الفئات الفرعية",
  "Top-3 Sub-Categories by Sales Type Group (YTD)": "أفضل 3 فئات فرعية حسب مجموعة نوع المبيعات (حتى تاريخه السنوي)",
  "Regions by Sales Type Group (YTD)": "المناطق حسب مجموعة نوع المبيعات (حتى تاريخه السنوي)",
  "Regions — Main Categories (YTD)": "المناطق — الفئات الرئيسية (حتى تاريخه السنوي)",
  "Regions — Sub-Categories (YTD)": "المناطق — الفئات الفرعية (حتى تاريخه السنوي)",
  "Top Sales Type Group by Region — Main Categories (YTD)": "مجموعة نوع المبيعات الأعلى حسب المنطقة — الفئات الرئيسية (حتى تاريخه السنوي)",
  "Top Sales Type Group by Region — Sub-Categories (YTD)": "مجموعة نوع المبيعات الأعلى حسب المنطقة — الفئات الفرعية (حتى تاريخه السنوي)",
  "Top Sales Type Group — Product Groups (YTD)": "مجموعة نوع المبيعات الأعلى — مجموعات المنتجات (حتى تاريخه السنوي)",
  // error/status text
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

// Page 2's two trend arrays carry a "Total" row appended by the controller
// (_append_total_row). It is the sum of every other row, so left in the same
// chart it owns the value axis by itself and flattens the real categories
// against the baseline, and its Achievement%/YoY% point rides the same two
// lines as theirs. Split here, drawn beside the chart in its own slot.
function splitTotalRow(rows) {
  const list = rows || [];
  const i = list.findIndex(r => r.code === 'Total' || r.label === 'Total');
  return i < 0 ? [list, []] : [list.slice(0, i).concat(list.slice(i + 1)), [list[i]]];
}

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
      const [label, seriesLabel, val, share] = rect.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${seriesLabel}: <b>${fmt(+val)}</b>` +
                   (share ? `<br>${t('Contribution')}: <b>${share}%</b>` : ''));
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
    `<div class="item" data-legend-idx="${i}"><span class="swatch" style="background:${colors[i]}"></span>${l}</div>`).join('');
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
// Bar geometry — shared by groupedBarChart and comboBarLineChart, which
// draw the same bars under different axes.
//
// A bar's value label is centred on the bar and is as wide as its TEXT, not
// as wide as the bar. So the LABEL, not the bar, decides how much room a
// group of bars needs, and a fixed per-group floor cannot know that: the
// old flat 100px left a 23.8px bar pitch on the four-card pages (a 252px
// card, three groups, three series) while "388.6M" measures 31.8px, so every
// neighbouring pair ran ~8px into each other. Five of the board's charts
// were overlapping at the default window size, worst 4.7px after the
// browser's own sub-pixel rounding.
//
// The floor is now derived from the widest label the chart will actually
// draw. Charts get wider rather than losing labels — .chart-scroll already
// scrolls horizontally, and widening past the container is what the old
// `data.length * perGroup` did too — and the print stylesheet scales the
// whole viewBox to the page, so a wider chart prints smaller, not clipped.
// ---------------------------------------------------------------------
const BAR_GAP = 9;             // between bars inside one group
const BAR_FILL = 0.73;         // share of its slot a bar fills
const MIN_GROUP_W = 100;       // the previous flat floor, still the minimum

// {W, groupW, barW} for a clustered bar chart whose value labels do not
// collide — with each other inside a group, or with the next group's.
//
// Two labels clear each other once their centres are `pitch` apart, and the
// centres ARE the bar centres, so the whole thing reduces to one rule: the
// bar pitch (barW + BAR_GAP) must be at least the label pitch. From there,
//
//   * a group holds n bars at that pitch, plus BAR_GAP of slack so the
//     outermost label can overhang its bar and still clear the next group's;
//   * the bar itself grows to whatever that pitch demands. BAR_FILL is the
//     PREFERRED look, not a cap: spending spare room on a fatter bar is what
//     keeps the chart from having to get wider still, and the bars stay
//     BAR_GAP apart either way.
function barLayout(el, data, seriesKeys, valueFmt, marginL, marginR) {
  const n = Math.max(seriesKeys.length, 1);
  const pitch = widestValueLabel(el, data, seriesKeys, valueFmt) + VALUE_LABEL_GAP;
  const perGroup = Math.max(MIN_GROUP_W, Math.ceil(n * pitch + BAR_GAP));
  // The margins sit OUTSIDE the plot, so they are added on top of the groups
  // rather than eaten out of them. Leaving them in is half of what went
  // wrong before: a floor that claimed 100px per group delivered 78.7.
  const W = Math.max(el.clientWidth || 480, data.length * perGroup + marginL + marginR);
  const groupW = (W - marginL - marginR) / Math.max(data.length, 1);
  const slotW = (groupW - BAR_GAP * (n - 1)) / n;
  const barW = Math.min(120, slotW, Math.max(slotW * BAR_FILL, pitch - BAR_GAP));
  // How far apart the bar CENTRES sit, which is what the labels care about.
  // Kept separate from barW so the 120px cap — which bounds the bar but says
  // nothing about the label above it — cannot pull two labels together.
  const barPitch = Math.max(barW + BAR_GAP, pitch);
  return { W, groupW, barW, barPitch, blockW: (n - 1) * barPitch + barW };
}

// ---------------------------------------------------------------------
// chart primitives — groupedBarChart/donutChart copied from
// sales_kpi_dashboard.js (no drill-down here). comboBarLineChart is new:
// bars on the primary (left) axis + line series on a secondary (right,
// percentage) axis, replicating the pbix's lineClusteredColumnComboChart.
// ---------------------------------------------------------------------
function groupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels, valueFmt = fmtCompact, opts = {}) {
  const { height = 230 } = opts;
  const isTotalRow = d => d && (d.code === 'Total' || d.label === 'Total');
  const nonTotalData = data.filter(d => !isTotalRow(d));
  const totalRow = data.find(isTotalRow);
  const defaultShareKey = seriesKeys.includes('sales') ? 'sales' : (seriesKeys.includes('qty') ? 'qty' : null);
  const shareKey = 'shareKey' in opts ? opts.shareKey : defaultShareKey;
  const shareTotal = !shareKey ? 0
    : (opts.shareTotal != null ? opts.shareTotal
       : (totalRow && totalRow[shareKey] != null
          ? totalRow[shareKey]
          : nonTotalData.reduce((sum, d) => sum + (d[shareKey] || 0), 0)));
  const shareOf = d => (isTotalRow(d) || !shareTotal || (!nonTotalData.length && opts.shareTotal == null))
    ? null
    : (d[shareKey] || 0) / shareTotal * 100;

  // House chart design, shared with pbi_chart_lib's groupedBarChart: sets sit
  // close together, the bars inside a set are held apart, and the bars grow to
  // use a filled width instead of letting it become gap. How WIDE a set has to
  // be is decided by the value labels — see barLayout.
  const H = height;
  const marginL = 54, marginR = 10, marginT = 10, marginB = 46;
  const { W, groupW, barW, barPitch, blockW } = barLayout(el, data, seriesKeys, valueFmt, marginL, marginR);
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const maxRaw = Math.max(1, ...data.flatMap(d => seriesKeys.map(k => d[k] || 0)));
  const tickVals = niceAxisTicks(maxRaw, valueFmt);
  const maxVal = tickVals[tickVals.length - 1];
  const gap = BAR_GAP;

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
      svg += `<rect data-series-idx="${si}" data-tip="${tip}" rx="2" ry="2" x="${x}" y="${y}" width="${barW}" height="${Math.max(barH, 1)}" fill="${seriesColors[si]}"/>`;
      svg += `<text class="bar-value" data-series-idx="${si}" x="${x + barW / 2}" y="${y - 3}" text-anchor="middle">${valueFmt(val)}</text>`;
    });
    const label = truncateLabel(d.label, groupW - 8);
    const capX = marginL + gi * groupW + groupW / 2;
    svg += `<text class="axis-label" x="${capX}" y="${H - 24}" text-anchor="middle"><title>${d.label}</title>${label}</text>`;
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

  const donutFont = labelFont(el, 'donut-label', '600 9.5px sans-serif');
  const slices = [];
  let cumulative = 0;
  data.forEach((d, i) => {
    const share = (d.value || 0) / total;
    if (share <= 0) return;
    const trueAngle = (cumulative + share / 2) * 2 * Math.PI - Math.PI / 2;
    const text = (share * 100).toFixed(1) + '%';
    // Measured, not estimated. The old `text.length * 5.6` under-counted a
    // real ".donut-label" by about a fifth — "0.4%" renders 27.3px wide, not
    // 22.4 — so the spreading pass below was working to a slot narrower than
    // the label it had to fit.
    const halfAngle = (textWidth(text, donutFont) / 2 + 4) / labelR;
    slices.push({ label: d.label, share, trueAngle, labelAngle: trueAngle, halfAngle, cumStart: cumulative, colorIdx: i });
    cumulative += share;
  });

  // Spread labels that would sit on top of each other. Slices arrive in
  // cumulative order, so their angles are MONOTONIC and the sweeps are a
  // running max forwards and a running min backwards — no modular arithmetic.
  //
  // That is the fix for a real defect. The old sweeps measured the gap to the
  // neighbour and normalised a negative one with `gap += 2*PI`, which is only
  // sound while the labels are still in order. The moment a push moved one
  // label past the next, the gap between them read as ~6.2 radians of
  // clearance instead of an overlap, and the pass declared them fine: two
  // hairline slices ended 2.1px apart, "0.4%" printed straight over "0.1%" on
  // the LY-vs-TY donuts of pages 8 and 9.
  //
  // Neither sweep closes the circle, so the first and last labels never push
  // each other. They are the pair furthest apart in sweep order, and at these
  // slice counts the spreading always has somewhere to go before it gets
  // there.
  spreadDonutLabels(slices);

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  const rings = [];
  const labels = [];
  slices.forEach(s => {
    const segLen = s.share * circumference;
    const offset = -s.cumStart * circumference;
    rings.push(`<circle data-slice-idx="${s.colorIdx}" data-tip="${s.label}||${t('Share')}||${(s.share * 100).toFixed(1)}" cx="${cx}" cy="${cy}" r="${r}" fill="none"
              stroke="${colors[s.colorIdx % colors.length]}" stroke-width="${thickness}"
              stroke-dasharray="${segLen} ${circumference - segLen}" stroke-dashoffset="${offset}"
              transform="rotate(-90 ${cx} ${cy})"/>`);

    const cosA = Math.cos(s.trueAngle), sinA = Math.sin(s.trueAngle);
    const cosL = Math.cos(s.labelAngle), sinL = Math.sin(s.labelAngle);
    const x1 = cx + cosA * (ringOuterR + 2), y1 = cy + sinA * (ringOuterR + 2);
    const x2 = cx + cosL * (labelR - 9), y2 = cy + sinL * (labelR - 9);
    labels.push(`<line class="donut-leader" data-slice-label-idx="${s.colorIdx}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`);
    const lx = cx + cosL * labelR, ly = cy + sinL * labelR;
    labels.push(`<text class="donut-label" data-slice-label-idx="${s.colorIdx}" x="${lx}" y="${ly}" text-anchor="middle">${(s.share * 100).toFixed(1)}%</text>`);
  });
  svg += rings.join('') + labels.join('');
  svg += `<circle class="donut-total-hit" data-tip="${t('Total')}||${t('Actual')}||${fmt(total)}" cx="${cx}" cy="${cy}" r="${r - thickness / 2}" fill="transparent"/>`;
  svg += `<text class="donut-total" x="${cx}" y="${cy - 2}" text-anchor="middle">${valueFmt(total)}</text>`;
  svg += `<text class="donut-total-label" x="${cx}" y="${cy + 16}" text-anchor="middle">${t('Total')}</text>`;
  svg += `</svg>`;
  el.innerHTML = legendHtml(data.map(d => d.label), data.map((d, i) => colors[i % colors.length])) + svg;
  attachLegendScroll(el);
  attachValueTooltips(el, '.donut-total-hit[data-tip]');
  attachLegendFilter(el, 'donut');
  el.querySelectorAll('circle[data-tip]:not(.donut-total-hit)').forEach(c => {
    c.addEventListener('mousemove', evt => {
      const [label, , share] = c.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${t('Contribution')}: <b>${share}%</b>`);
    });
    c.addEventListener('mouseleave', hideTip);
  });
}

function shadeColor(color, percent) {
  let R = 0, G = 0, B = 0;
  if (!color) return '#666666';
  if (color.startsWith('#')) {
    let hex = color.slice(1);
    if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
    const num = parseInt(hex, 16);
    R = (num >> 16);
    G = ((num >> 8) & 0x00FF);
    B = (num & 0x0000FF);
  } else if (color.startsWith('rgb')) {
    const parts = color.match(/\d+/g);
    if (parts && parts.length >= 3) {
      R = parseInt(parts[0], 10);
      G = parseInt(parts[1], 10);
      B = parseInt(parts[2], 10);
    }
  } else {
    return color;
  }
  R = Math.min(255, Math.max(0, Math.round(R * (1 + percent))));
  G = Math.min(255, Math.max(0, Math.round(G * (1 + percent))));
  B = Math.min(255, Math.max(0, Math.round(B * (1 + percent))));
  return `rgb(${R}, ${G}, ${B})`;
}

function pieChart3D(el, data, colors, valueFmt = fmtCompact) {
  const total = data.reduce((s, d) => s + (d.value || 0), 0);
  const Rx = 75, Ry = 42, Hd = 22;
  const labelRx = Rx + 36, labelRy = Ry + 26;
  const cx = labelRx + 16, cy = labelRy + 14;
  const W = cx * 2, H = cy * 2 + Hd;

  if (total <= 0) {
    let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
    svg += `<ellipse cx="${cx}" cy="${cy + Hd + 4}" rx="${Rx + 6}" ry="${Ry + 3}" fill="rgba(0,0,0,0.06)"/>`;
    svg += `<ellipse cx="${cx}" cy="${cy}" rx="${Rx}" ry="${Ry}" fill="none" stroke="var(--grid)" stroke-width="2"/>`;
    svg += `<text class="donut-total" x="${cx}" y="${cy - 2}" text-anchor="middle">${valueFmt(0)}</text>`;
    svg += `<text class="donut-total-label" x="${cx}" y="${cy + 16}" text-anchor="middle">${t('Total')}</text>`;
    svg += `</svg>`;
    el.innerHTML = legendHtml(data.map(d => d.label), data.map(() => 'var(--grid)')) + svg;
    attachLegendScroll(el);
    return;
  }

  const donutFont = labelFont(el, 'donut-label', '600 9.5px sans-serif');
  const slices = [];
  let cumulative = 0;
  data.forEach((d, i) => {
    const share = (d.value || 0) / total;
    if (share <= 0) return;
    const a0 = cumulative * 2 * Math.PI - Math.PI / 2;
    const a1 = (cumulative + share) * 2 * Math.PI - Math.PI / 2;
    const trueAngle = (cumulative + share / 2) * 2 * Math.PI - Math.PI / 2;
    const text = (share * 100).toFixed(1) + '%';
    const halfAngle = (textWidth(text, donutFont) / 2 + 4) / labelRx;
    slices.push({
      label: d.label,
      value: d.value,
      share,
      a0,
      a1,
      trueAngle,
      labelAngle: trueAngle,
      halfAngle,
      cumStart: cumulative,
      colorIdx: i,
      color: colors[i % colors.length],
      darkColor: shadeColor(colors[i % colors.length], -0.28),
    });
    cumulative += share;
  });

  spreadDonutLabels(slices);

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" class="pie-3d-svg">`;
  // Soft bottom shadow for 3D depth
  svg += `<ellipse cx="${cx}" cy="${cy + Hd + 4}" rx="${Rx + 6}" ry="${Ry + 3}" fill="rgba(0,0,0,0.08)"/>`;

  // 3D side walls
  slices.forEach(s => {
    const checkSegments = [
      { start: Math.max(s.a0, 0), end: Math.min(s.a1, Math.PI) },
      { start: Math.max(s.a0, 2 * Math.PI), end: Math.min(s.a1, 3 * Math.PI) },
      { start: Math.max(s.a0 - 2 * Math.PI, 0), end: Math.min(s.a1 - 2 * Math.PI, Math.PI) }
    ];

    checkSegments.forEach(seg => {
      let t0 = seg.start, t1 = seg.end;
      if (t1 > t0) {
        while (t0 >= 2 * Math.PI) { t0 -= 2 * Math.PI; t1 -= 2 * Math.PI; }
        while (t0 < 0) { t0 += 2 * Math.PI; t1 += 2 * Math.PI; }
        const xt0 = cx + Rx * Math.cos(t0), yt0 = cy + Ry * Math.sin(t0);
        const xt1 = cx + Rx * Math.cos(t1), yt1 = cy + Ry * Math.sin(t1);
        const xb0 = xt0, yb0 = yt0 + Hd;
        const xb1 = xt1, yb1 = yt1 + Hd;
        const large = (t1 - t0 > Math.PI) ? 1 : 0;
        const path = `M ${xt0.toFixed(1)} ${yt0.toFixed(1)} A ${Rx} ${Ry} 0 ${large} 1 ${xt1.toFixed(1)} ${yt1.toFixed(1)} L ${xb1.toFixed(1)} ${yb1.toFixed(1)} A ${Rx} ${Ry} 0 ${large} 0 ${xb0.toFixed(1)} ${yb0.toFixed(1)} Z`;
        svg += `<path class="pie3d-wall" data-slice-idx="${s.colorIdx}" data-tip="${s.label}||${t('Contribution')}||${(s.share * 100).toFixed(1)}" d="${path}" fill="${s.darkColor}"/>`;
      }
    });
  });

  // Top caps
  slices.forEach(s => {
    if (s.share >= 0.999) {
      svg += `<ellipse class="pie3d-slice" data-slice-idx="${s.colorIdx}" data-tip="${s.label}||${t('Contribution')}||${(s.share * 100).toFixed(1)}" cx="${cx}" cy="${cy}" rx="${Rx}" ry="${Ry}" fill="${s.color}"/>`;
    } else {
      const x0 = cx + Rx * Math.cos(s.a0), y0 = cy + Ry * Math.sin(s.a0);
      const x1 = cx + Rx * Math.cos(s.a1), y1 = cy + Ry * Math.sin(s.a1);
      const large = (s.a1 - s.a0 > Math.PI) ? 1 : 0;
      const path = `M ${cx} ${cy} L ${x0.toFixed(1)} ${y0.toFixed(1)} A ${Rx} ${Ry} 0 ${large} 1 ${x1.toFixed(1)} ${y1.toFixed(1)} Z`;
      svg += `<path class="pie3d-slice" data-slice-idx="${s.colorIdx}" data-tip="${s.label}||${t('Contribution')}||${(s.share * 100).toFixed(1)}" d="${path}" fill="${s.color}" stroke="rgba(255,255,255,0.3)" stroke-width="0.75"/>`;
    }
  });

  // Data labels and leader lines
  slices.forEach(s => {
    const cosL = Math.cos(s.labelAngle), sinL = Math.sin(s.labelAngle);
    const cosA = Math.cos(s.trueAngle), sinA = Math.sin(s.trueAngle);
    const x1 = cx + cosA * (Rx + 2);
    const y1 = cy + sinA * (Ry + 2) + (sinA > 0 ? (Hd * sinA * 0.5) : 0);
    const x2 = cx + cosL * (labelRx - 9);
    const y2 = cy + sinL * (labelRy - 7) + (sinL > 0 ? (Hd * 0.35) : 0);
    const lx = cx + cosL * labelRx;
    const ly = cy + sinL * labelRy + (sinL > 0 ? (Hd * 0.35) : 0);

    svg += `<line class="donut-leader" data-slice-label-idx="${s.colorIdx}" x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}"/>`;
    svg += `<text class="donut-label" data-slice-label-idx="${s.colorIdx}" x="${lx.toFixed(1)}" y="${(ly + 3.5).toFixed(1)}" text-anchor="middle">${(s.share * 100).toFixed(1)}%</text>`;
  });

  svg += `</svg>`;
  el.innerHTML = legendHtml(data.map(d => d.label), data.map((d, i) => colors[i % colors.length])) + svg;
  attachLegendScroll(el);
  attachLegendFilter(el, 'pie');
  el.querySelectorAll('[data-slice-idx][data-tip]').forEach(c => {
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
function comboBarLineChart(el, data, barKeys, barColors, barLabels, lineKeys, lineColors, lineLabels, valueFmt = fmtCompact, opts = {}) {
  const { height = 260 } = opts;
  const isTotalRow = d => d && (d.code === 'Total' || d.label === 'Total');
  const nonTotalData = data.filter(d => !isTotalRow(d));
  const totalRow = data.find(isTotalRow);
  const defaultShareKey = barKeys.includes('sales') ? 'sales' : (barKeys.includes('qty') ? 'qty' : null);
  const shareKey = 'shareKey' in opts ? opts.shareKey : defaultShareKey;
  const shareTotal = !shareKey ? 0
    : (opts.shareTotal != null ? opts.shareTotal
       : (totalRow && totalRow[shareKey] != null
          ? totalRow[shareKey]
          : nonTotalData.reduce((sum, d) => sum + (d[shareKey] || 0), 0)));
  const shareOf = d => (isTotalRow(d) || !shareTotal || (!nonTotalData.length && opts.shareTotal == null))
    ? null
    : (d[shareKey] || 0) / shareTotal * 100;

  // House chart design, shared with pbi_chart_lib's groupedBarChart: sets sit
  // close together, the bars inside a set are held apart, and the bars grow to
  // use a filled width instead of letting it become gap. Same label-driven
  // sizing as groupedBarChart — see barLayout.
  const H = height;
  const marginL = 54, marginR = 50, marginT = 10, marginB = 46;
  const { W, groupW, barW, barPitch, blockW } = barLayout(el, data, barKeys, valueFmt, marginL, marginR);
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
  const gap = BAR_GAP;

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
    const groupX = marginL + gi * groupW + groupW / 2 - blockW / 2;
    barKeys.forEach((k, si) => {
      const val = d[k] || 0;
      const barH = barAreaH * (val / maxVal);
      const x = groupX + si * barPitch;
      const y = barAreaTop + barAreaH - barH;
      const share = k === shareKey ? shareOf(d) : null;
      const tip = `${d.label}||${barLabels[si]}||${val}` +
                  (share == null ? '' : `||${share.toFixed(1)}`);
      svg += `<rect data-series-idx="${si}" data-tip="${tip}" rx="2" ry="2" x="${x}" y="${y}" width="${barW}" height="${Math.max(barH, 1)}" fill="${barColors[si]}"/>`;
      svg += `<text class="bar-value" data-series-idx="${si}" x="${x + barW / 2}" y="${y - 3}" text-anchor="middle">${valueFmt(val)}</text>`;
    });
    const label = truncateLabel(d.label, groupW - 8);
    const capX = marginL + gi * groupW + groupW / 2;
    svg += `<text class="axis-label" x="${capX}" y="${H - 24}" text-anchor="middle"><title>${d.label}</title>${label}</text>`;
    const share = shareOf(d);
    if (share != null) {
      svg += `<text class="bar-share" x="${capX}" y="${H - 9}" text-anchor="middle">${share.toFixed(1)}%</text>`;
    }
  });

  const yAt = val => marginT + lineBandH - (lineBandH * Math.min(val, niceMaxPct) / niceMaxPct);
  lineKeys.forEach((k, li) => {
    const pts = data.map((d, gi) => ({ x: marginL + gi * groupW + groupW / 2, y: yAt(d[k]), val: d[k] }))
      .filter(p => p.val != null);
    if (!pts.length) return;
    const path = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    svg += `<path class="combo-line" data-series-idx="${barKeys.length + li}" d="${path}" fill="none" stroke="${lineColors[li]}" stroke-width="2.5"/>`;
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
      svg += `<circle class="combo-dot" data-series-idx="${barKeys.length + p.li}" data-tip="${d.label}||${lineLabels[p.li]}||${p.val.toFixed(1)}%" cx="${p.x}" cy="${p.y}" r="4" fill="${lineColors[p.li]}"/>`;
      const labelY = order === 0 ? p.y - 8 : p.y + 14 + (order - 1) * 12;
      svg += `<text class="combo-pct-value" data-series-idx="${barKeys.length + p.li}" x="${p.x}" y="${labelY}" text-anchor="middle" fill="${lineColors[p.li]}">${p.val.toFixed(1)}%</text>`;
    });
  });
  svg += `</svg>`;
  el.innerHTML = legendHtml([...barLabels, ...lineLabels], [...barColors, ...lineColors]) + svg;
  attachBarTooltips(el);
  // truncateLabel above sizes captions by a per-character estimate, which
  // under-counts uppercase; this trims anything still over its slot against
  // the real glyph widths and gives every cut caption its full text on hover.
  fitCaptionsToSlot(el, groupW - 8);
  markAllCaptionsForTooltip(el);
  attachCaptionTooltips(el);
  attachValueTooltips(el, '.combo-dot[data-tip]');
  attachLegendScroll(el);
  attachLegendFilter(el, 'bar');
}

function groupedQuarterlyBarChart(el, dataByQuarter, quarterTabs, barKeys, barColors, barLabels, valueFmt = fmtCompact) {
  const activeTabs = (quarterTabs || []).filter(tab => dataByQuarter[tab.v] && dataByQuarter[tab.v].length > 0);
  if (!activeTabs.length) {
    el.innerHTML = '<div style="padding: 20px; text-anchor: middle; color: var(--text-secondary);">No data</div>';
    return;
  }

  const items = [];
  const quarterBoundaries = [];
  let currentIndex = 0;

  activeTabs.forEach((tab) => {
    const qRows = dataByQuarter[tab.v] || [];
    qRows.forEach((row) => {
      items.push({
        ...row,
        quarterLabel: tab.l,
        quarterSlug: tab.v,
      });
      currentIndex++;
    });
    quarterBoundaries.push({
      label: tab.l,
      startIndex: currentIndex - qRows.length,
      endIndex: currentIndex - 1,
      count: qRows.length,
    });
  });

  const height = 260;
  const marginL = 54, marginR = 20, marginT = 28, marginB = 46;
  const { W, groupW, barW, barPitch, blockW } = barLayout(el, items, barKeys, valueFmt, marginL, marginR);
  const plotW = W - marginL - marginR, plotH = height - marginT - marginB;

  const maxRaw = Math.max(1, ...items.flatMap(d => barKeys.map(k => d[k] || 0)));
  const tickVals = niceAxisTicks(maxRaw, valueFmt);
  const maxVal = tickVals[tickVals.length - 1];

  let svg = `<svg viewBox="0 0 ${W} ${height}" width="${W}px" height="${height}">`;

  tickVals.forEach(val => {
    const y = marginT + plotH - (plotH * val / maxVal);
    svg += `<line class="gridline" x1="${marginL}" x2="${W - marginR}" y1="${y}" y2="${y}"/>`;
    svg += `<text class="axis-label" x="${marginL - 8}" y="${y + 3}" text-anchor="end">${axisTickLabel(val, valueFmt)}</text>`;
  });
  svg += `<line class="baseline" x1="${marginL}" x2="${W - marginR}" y1="${marginT + plotH}" y2="${marginT + plotH}"/>`;

  quarterBoundaries.forEach((qb, idx) => {
    const startX = marginL + qb.startIndex * groupW;
    const endX = marginL + (qb.endIndex + 1) * groupW;
    const midX = (startX + endX) / 2;

    if (idx > 0) {
      svg += `<line class="section-divider" x1="${startX}" x2="${startX}" y1="${marginT - 14}" y2="${marginT + plotH}" stroke="var(--grid-dark, #cbd5e1)" stroke-width="1.5" stroke-dasharray="4 3"/>`;
    }

    svg += `<text class="quarter-section-title" x="${midX}" y="${marginT - 10}" text-anchor="middle" font-weight="700" font-size="12px" fill="var(--text-main, #1e293b)">${qb.label}</text>`;
  });

  items.forEach((d, gi) => {
    const groupX = marginL + gi * groupW + groupW / 2 - blockW / 2;
    barKeys.forEach((k, si) => {
      const val = d[k] || 0;
      const barH = plotH * (val / maxVal);
      const x = groupX + si * barPitch;
      const y = marginT + plotH - barH;
      const tip = `${d.quarterLabel} - ${d.label}||${barLabels[si]}||${val}`;
      svg += `<rect data-series-idx="${si}" data-tip="${tip}" rx="2" ry="2" x="${x}" y="${y}" width="${barW}" height="${Math.max(barH, 1)}" fill="${barColors[si]}"/>`;
      if (barH > 14) {
        svg += `<text class="bar-value" data-series-idx="${si}" x="${x + barW / 2}" y="${y - 3}" text-anchor="middle">${valueFmt(val)}</text>`;
      }
    });

    const label = truncateLabel(d.label, groupW - 6);
    const capX = marginL + gi * groupW + groupW / 2;
    svg += `<text class="axis-label" x="${capX}" y="${height - 24}" text-anchor="middle"><title>${d.label}</title>${label}</text>`;
  });

  svg += `</svg>`;
  el.innerHTML = legendHtml(barLabels, barColors) + svg;
  attachBarTooltips(el);
  fitCaptionsToSlot(el, groupW - 6);
  markAllCaptionsForTooltip(el);
  attachCaptionTooltips(el);
  attachLegendScroll(el);
  attachLegendFilter(el, 'bar');
}


// ---------------------------------------------------------------------
// narrative rendering — marked-text ("**bold**"/"##heading##") convention
// shared with the server (_pptx_marked_text in main.py) and with the deck's
// speaker notes.
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
// The note as the reader sees it. No "Edited note" tag: whether a note was
// typed or computed is an editing concern, and the editor says so inline.
function narrativeHtml(text) {
  if (!text) return '';
  const blocks = text.split(/\n+/).map(b => b.trim()).filter(Boolean);
  return blocks.map(block => {
    const h = block.match(/^##(.*)##$/);
    if (h) return `<h3>${escapeHtml(h[1])}</h3>`;
    return `<p>${markedToHtml(block)}</p>`;
  }).join('');
}
// The requirement dropdown's predefined half — house instructions that apply
// to any section of a sales report, so they are the same on every database
// and travel with the module rather than living in a table. Anything typed
// into the box can be added to the list beside them (Add to list, stored per
// database in pbi.dashboard.note), and only those added entries can be
// removed again.
const REQUIREMENT_PRESETS = [
  "Lead with achievement against target, then the year-on-year move.",
  "Name the top three contributors and the share of the total they hold.",
  "Call out the widest gap to target and what it costs in value.",
  "Compare with the same period last year, in value and in units.",
  "Say which lines are growing and which are falling, with the percentages.",
  "Flag anything below 50% achievement explicitly.",
  "Explain what moved the numbers rather than restating them.",
  "Keep it to two short paragraphs, numbers first.",
];

// A saved requirement, shown above the note when the board is NOT in edit
// mode: what this section is meant to cover, for whoever writes next month's
// note. Nothing is rendered when no requirement was written.

// Synthesizes or filters the computed narrative text to specifically answer
// or focus on the selected requirement/query preset.
function synthesizeNoteForPreset(presetText, fullNarrative) {
  if (!fullNarrative || !presetText) return fullNarrative || '';
  const paras = fullNarrative.split('\n').map(p => p.trim()).filter(Boolean);
  if (!paras.length) return presetText;

  const lowerPreset = presetText.toLowerCase();

  // 1. "Name the top three contributors and the share of the total they hold."
  if (lowerPreset.includes('top three') || lowerPreset.includes('contributors') || (lowerPreset.includes('share') && lowerPreset.includes('total'))) {
    const matched = paras.filter(p => /leads|hold|share|together|contributor/i.test(p));
    if (matched.length) return matched.join('\n\n');
  }

  // 2. "Call out the widest gap to target and what it costs in value."
  if (lowerPreset.includes('widest gap') || (lowerPreset.includes('gap') && lowerPreset.includes('target'))) {
    const matched = paras.filter(p => /widest gap|short of|carrying a target|carrying a plan|target/i.test(p));
    if (matched.length) return matched.join('\n\n');
  }

  // 3. "Compare with the same period last year, in value and in units."
  if (lowerPreset.includes('last year') || lowerPreset.includes('period last year')) {
    const matched = paras.filter(p => /last year|versus last year|ly\b/i.test(p));
    if (matched.length) return matched.join('\n\n');
  }

  // 4. "Lead with achievement against target, then the year-on-year move."
  if (lowerPreset.includes('lead with achievement') || (lowerPreset.includes('achievement') && lowerPreset.includes('target'))) {
    const targetParas = paras.filter(p => /target|budget|achv|plan/i.test(p));
    const yoyParas = paras.filter(p => /last year|versus last year|ly\b/i.test(p));
    const combined = Array.from(new Set([...targetParas, ...yoyParas]));
    if (combined.length) return combined.join('\n\n');
  }

  // 5. "Say which lines are growing and which are falling, with the percentages."
  if (lowerPreset.includes('growing') || lowerPreset.includes('falling') || lowerPreset.includes('percentages')) {
    const matched = paras.filter(p => /strongest|weakest|growing|falling|up \d|down \d|%/i.test(p));
    if (matched.length) return matched.join('\n\n');
  }

  // 6. "Flag anything below 50% achievement explicitly."
  if (lowerPreset.includes('50%') || lowerPreset.includes('below') || lowerPreset.includes('flag')) {
    const matched = paras.filter(p => /target|short of|widest gap|% of the|achv/i.test(p));
    if (matched.length) return matched.join('\n\n');
  }

  // 7. "Keep it to two short paragraphs, numbers first."
  if (lowerPreset.includes('two short paragraphs') || lowerPreset.includes('two paragraphs')) {
    return paras.slice(0, 2).join('\n\n');
  }

  // 8. "Explain what moved the numbers rather than restating them."
  if (lowerPreset.includes('moved the numbers') || lowerPreset.includes('explain')) {
    const matched = paras.filter(p => /versus last year|at [^ ]+ per unit|average realised|pace against/i.test(p));
    if (matched.length) return matched.join('\n\n');
    return paras.slice(0, 2).join('\n\n');
  }

  // Custom user queries or presets: check keyword matches across paragraphs
  const stopWords = new Set(['what', 'this', 'that', 'with', 'from', 'have', 'been', 'should', 'could', 'cover', 'about', 'section', 'please', 'show']);
  const words = lowerPreset.replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(w => w.length > 3 && !stopWords.has(w));
  if (words.length) {
    const matched = paras.filter(p => {
      const lp = p.toLowerCase();
      return words.some(w => lp.includes(w));
    });
    if (matched.length) return matched.join('\n\n');
  }

  return fullNarrative;
}

// The same panel in edit mode: the requirement on top, the note below it.
// Both are plain textareas over the RAW text — the note keeps the ``**bold**``
// / ``##heading##`` marks the computed narrative is written in, which is the
// same form the deck's speaker notes carry, so what is typed here is what
// comes out of Export PowerPoint.
function noteEditorHtml(noteText, reqText, isOverride, presets) {
  const options = group => presets
    .map((p, i) => [p, i])
    .filter(([p]) => p.custom === group)
    .map(([p, i]) => `<option value="${i}"${p.text === reqText.trim() ? ' selected="selected"' : ''}>${escapeHtml(p.text)}</option>`)
    .join('');
  const predefined = options(false), added = options(true);
  const resetHint = t('Reset this section to its computed note and clear its requirement');
  return `<div class="note-editor">
      <div class="note-editor-head">
        <label class="note-field-label">${t('Requirement')}</label>
        <button type="button" class="note-reset" title="${resetHint}" aria-label="${resetHint}">
          <span class="note-reset-icon" aria-hidden="true">&#8635;</span><span class="note-reset-text">${t('Reset')}</span>
        </button>
      </div>
      <div class="note-preset-row">
        <select class="note-preset">
          <option value="">${t('Preset requirement…')}</option>
          ${predefined ? `<optgroup label="${t('Predefined')}">${predefined}</optgroup>` : ''}
          ${added ? `<optgroup label="${t('Added here')}">${added}</optgroup>` : ''}
        </select>
        <button type="button" class="note-preset-add">${t('Add to list')}</button>
        <button type="button" class="note-preset-del">${t('Remove from list')}</button>
      </div>
      <textarea class="note-req" rows="2" placeholder="${t('What should this section cover?')}">${escapeHtml(reqText)}</textarea>
      <label class="note-field-label">${t('Analysis note')}` +
        (isOverride ? `<span class="edited-note-tag inline">${t('Edited note')}</span>` : '') +
      `</label>
      <textarea class="note-text">${escapeHtml(noteText)}</textarea>
    </div>`;
}

// ---------------------------------------------------------------------
// filter options / page defs
// ---------------------------------------------------------------------
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];
const MONTH_OPTIONS = MONTH_NAMES.map((l, i) => ({ v: i + 1, l }));

// Regular reads product_category.sub_category, Manager reads
// merged_subcategory — the same switch "Sales Dashboard With Salesman"
// carries, kept here because it moves BOTH the Sub Category and the Main
// Category pages (main_category hangs off the sub-category), so the two
// salesman dashboards would otherwise disagree for manager users.
const LEVEL_ORDER = ['salesTypeGroup', 'partnerClassification', 'reportRegion', 'city',
                     'salesman', 'customer', 'mainCategory', 'subCategory',
                     'productGroup', 'productSubGroup'];

const LEVEL_FILTER_LABELS = {
  salesTypeGroup: 'Sale Type / Channel',
  partnerClassification: 'Partner Classification',
  reportRegion: 'Region',
  city: 'City',
  salesman: 'Salesman',
  customer: 'Customer',
  mainCategory: 'Main Category',
  subCategory: 'Sub Category',
  productGroup: 'Product Group',
  productSubGroup: 'Product Sub-Group',
};

const emptyLevelFilters = () =>
  Object.fromEntries(LEVEL_ORDER.map(lv => [lv, 'all']));

const SUBMODE_OPTIONS = [{ v: 'regular', l: 'Regular' }, { v: 'manager', l: 'Manager' }];
const SCOPE_OPTIONS = [
  { v: 'acgroups', l: 'Midea AC (in scope)' },
  { v: 'all', l: 'All MDA lines (raw)' },
];

// Fixed toggle slugs. Which category each one stands for changes with the
// data (the four largest Partner Classifications / Regions this period, see
// sales_mail_sman_main.py's _tabs); the slug does not, so these refs and the
// pbi.dashboard.note keys behind them survive a period change.
const CLASS_SLUGS = ['c1', 'c2', 'c3', 'c4'];
const REGION_SLUGS = ['r1', 'r2', 'r3', 'r4'];
// Pages 4 and 5 toggle by quarter. Four slugs and four sets of refs, but only
// the quarters up to the selected month are rendered (the template t-ifs on
// hasTab), so renderAll skips any slug whose ref has no element.
const QUARTER_SLUGS = ['q1', 'q2', 'q3', 'q4'];

// Short "what process is behind this card" text shown by the (i) info icons
// next to the header and each section's h2, on hover — plain technical
// description of the data source/formula (distinct from the data-driven
// "narrative" business commentary in the .narrative panels). Kept
// English-only (not run through addLabels/t()): these are formula/column-name
// descriptions, not UI chrome. See sales_mail_sman_main.py and
// sales_sman_main.py (_FACT_SQL, CATALOGUE_SCOPE, AMOUNT_EXPR, QTY_EXPR) for
// the source of every figure below.
const PROCESS_NOTES = {
  scope: `Actuals and Target both come from <b>v_pbi_sales_sman_fact</b>, a nightly snapshot over the legacy <b>transaction_header</b>/<b>transaction_details</b> tables — the same source "Sales Dashboard With Salesman" reads, so the two boards cannot disagree. Credit notes (document type 02) subtract; invoices (01) add. <b>Value</b> = SUM(Issued Qty × (Price − Discount − Special Discount)), net of VAT. <b>Quantity</b> counts machines, not lines: only the part tagged with product tag '02' (<b>product.tag</b>) is counted, so a split AC counts once rather than once per half — which is why Quantity and Value are not in proportion. <b>In scope</b>: Midea (MDA) lines whose <b>product_category.code</b>, taken from the line's own product-group link (<b>trnd_groupid</b>), is one of the AC groups (ACACC, ACCON, ACCST, ACPAC, ACPKG, ACAIP, ACPOR, ACVRF, ACWIN, ACWTS, ACHCL, ATOM), excluding customers whose code starts with 'V'. Customer discounts, promo discounts, installation, service charges, shipping and spare parts are separate codes and do not count as sales. <b>Target</b> comes from the Budget screen (<b>v_sales_budget_month</b>), attached per (month × classification × region × city × customer × product group) and de-duplicated before it is summed. Sales-vs-Target is like-for-like: the budget covers exactly those AC product groups and carries no 'V' customer at all, so both sides measure the same population. The budget carries <i>no salesman</i>, so selecting one hides every Target on this report rather than showing a figure that would be both inflated and incomplete. Year, Month, Salesman and Sub-category View narrow every page.`,


  'kpi-amount': `Company-wide Value totals for the selected Month (MTD) and Jan-through-Month (YTD): This Year, Target and Last Year. "vs LY" = This Year ÷ Last Year × 100; "Achv" = This Year ÷ Target × 100.`,
  'kpi-qty': `The same MTD/YTD/This Year/Target/Last Year comparison as the Value tiles above, counting units instead of money, same scope and filters.`,
  'total-company': `The same four totals as the KPI tiles, re-shown as bars: Month and Year-to-date, by Value and by Qty.`,
  'class-region-trends': `YTD Value by Sales Type Group, and by Region. Achievement % = YTD Actual ÷ YTD Target × 100; YoY % = YTD Actual ÷ Last-Year YTD × 100 (a ratio to last year, not a growth rate).`,
  'quarterly-company': `Calendar-year Q1 through the quarter containing the selected month. This-Year actuals are capped at the selected month so later months in the current quarter don't leak in; Target and Last Year are shown for the full quarter.`,
  'quarterly-saletypegroup': `Sales Type Groups (<b>salestypes_group</b>, the head of the salesman drill chain) within the quarter selected above. This-Year actuals are capped at the selected month so a part-finished quarter doesn't borrow later months; Target and Last Year cover the full quarter. The Target is grouped on the budget's OWN sale type (<b>budget_l1_code</b>), not the sale's, so a budget tuple whose parts sold under two groups is not counted twice.`,
  'quarterly-region': `Regions within the quarter selected above. Same quarter rules as the page above: This Year capped at the selected month, Target and Last Year full-quarter.`,
  'main-categories': `Month and Year-to-date Value per Main Category (main_category, reached through the product's sub-category), This Year vs Target vs Last Year.`,
  'subcats-top8': `The 10 Split product sub-groups with the highest YTD Value, ranked This-Year-sales descending. The same 10 feed the distribution donuts on the next page.`,
  'subcats-distribution': `The same Top-10 Split product sub-group YTD data as the previous page, split into two donuts showing each one's share of the total — Last Year and This Year.`,
  'maincats-distribution': `The same Main Categories as page 6, split into Last-Year-share vs This-Year-share donuts.`,
  'saletypegroups': `Month and Year-to-date totals per Sales Type Group (<b>salestypes_group</b> — Dealers, Projects, Key Accounts, Corporate Sales), by Value and by Qty. This is the level the budget is captured at, so the bars tie to the Target tile above them; every in-scope sale carries one, so there is no Unassigned bar.`,
  'saletypegroups-distribution': `The same Sales Type Group YTD data as the previous page, split into Last-Year vs This-Year share donuts, for both Value and Qty.`,
  'topcat-subcats': `Product groups of LCAC sub-categories by MTD and YTD sales, target, and prior year comparison.`,
  'top3-by-class': `Product groups by YTD within the sales type group (1st level: sales type group, 2nd level: product group; Value and Qty shown side by side).`,
  'regions-by-class': `Regions by YTD Value and Qty, narrowed to the sales type group selected above.`,
  'stg-region-maincats': `Main Categories by YTD Value for the region selected above.`,
  'stg-region-subcats': `Product sub-groups for Dealers in the selected region for Split — top 8 by YTD Value.`,
  'stg-productgroups': `Product Sub-Groups narrowed to Projects, top 10 by YTD Value.`,
};

export class PbiSalesMailSmanDashboard extends Component {
  static template = "pbi_sales_dashboards.sales_mail_sman_dashboard";
  static props = ["*"];

  // Source table names in the header are a developer detail — debug mode only.
  selectScope(v) {
    this.state.scope = v;
    this.load();
  }

  get scopeOptions() {
    return [{ v: 'acgroups', l: t("AC product groups") },
            { v: 'all', l: t('Show all') }];
  }

  get isDebugMode() {
    return Boolean(window.odoo && window.odoo.debug);
  }

  setup() {
    this.rpc = useService("rpc");
    this.dialog = useService("dialog");
    this.t = t;
    this.isArabicUI = isArabicUI;
    this.monthOptions = MONTH_OPTIONS;
    this.submodeOptions = SUBMODE_OPTIONS;
    this.classSlugs = CLASS_SLUGS;
    this.regionSlugs = REGION_SLUGS;
    this.quarterSlugs = QUARTER_SLUGS;
    // See load()'s comment below — the request-ordering guard keys off these.
    this._loadSeq = 0;
    this._loadPromise = null;
    // Toggle pages (4, 5, 13-16): {toggleKey: {slug: redraw}} filled by
    // renderAll, plus the set of toggle keys whose panel was opened since
    // the last patch. See drawPanel() for why a panel has to be redrawn
    // when it is shown.
    this._panelDraw = {};
    this._pendingPanels = new Set();
    // Narrative panels: {sectionKey: ref}, registered by putNarrative so that
    // toggling edit mode can repaint every one of them without renderAll
    // redrawing seventeen pages of charts. The two draft maps hold what is
    // typed but not yet saved; a key absent from them means "unedited", which
    // is not the same as an empty string (that is a deliberate blanking).
    this._narrativeSlots = {};
    this._noteDrafts = {};
    this._reqDrafts = {};

    this.state = useState({
      year: null, month: null, salesman: 'all', subMode: 'regular',
      // Developer-mode only. The two scopes are not comparable -- 601m in
      // scope against 477m for every MDA line, the second being LOWER because
      // the lines outside the scope are the negative discount pseudo-parts --
      // so this is a diagnostic, not a business control.
      scope: 'acgroups',
      loading: false, error: '',
      // Note editing: off by default, and while it is on the filters are
      // locked (see the template) — a period change would reload the board
      // out from under drafts that belong to the period being edited.
      editMode: false, savingNotes: false, noteDirty: 0, noteStatus: '',
      // The added half of the requirement dropdown, refreshed by every load
      // and by every add/remove (see presetList()).
      reqPresets: [],
      // What optional packages this SERVER has (see optional_deps.py). Null
      // until the first payload lands, which pptxReady reads as "assume yes"
      // rather than disabling a control on a server that simply predates the
      // check.
      capabilities: null,
      yearOptions: [], salesmanOptions: [],
      periodLabel: '', hasPrevYear: false,
      filtersCollapsed: false,
      levelsCollapsed: true,
      levelFilters: emptyLevelFilters(),
      levelFilterOptions: Object.fromEntries(LEVEL_ORDER.map(lv => [lv, []])),
      classTabs: [],
      regionTabs: [],
      // Quarters, unlike the two category rows, are NOT padded out to four:
      // a quarter that has not happened gets no tab and no printed page. Q1
      // is the safe placeholder because every period has one.
      quarterTabs: [{ v: 'q1', l: 'Q1' }],
      topClassLabel: '—',
      topSaleTypeGroupLabel: '—',
      topMainCategoryLabel: '—',
      toggleState: {
        quarterlySaleTypeGroup: 'q1', quarterlyRegion: 'q1',
        top3ByClass: 'c1', regionsByClass: 'c1',
        stgRegionMaincats: 'r1', stgRegionSubcats: 'r1',
      },
    });

    this.rootRef = useRef('root');
    const refNames = [
      'kpiAmountRow', 'kpiQtyRow', 'tooltip',
      'totalCompanyMtdValueChart', 'totalCompanyMtdQtyChart',
      'totalCompanyYtdValueChart', 'totalCompanyYtdQtyChart', 'totalCompanyNotes',
      'classTrendChart', 'regionTrendChart', 'classRegionTrendsNotes',
      'quarterlyCompanyChart', 'quarterlyCompanyNotes',
      'quarterlyStgChart_q1', 'quarterlyStgChart_q2', 'quarterlyStgChart_q3', 'quarterlyStgChart_q4', 'quarterlyStgNotes',
      'quarterlyRegionChart_q1', 'quarterlyRegionChart_q2', 'quarterlyRegionChart_q3', 'quarterlyRegionChart_q4', 'quarterlyRegionNotes',
      'mainCategoriesMtdWSChart', 'mainCategoriesMtdLCChart',
      'mainCategoriesYtdWSChart', 'mainCategoriesYtdLCChart', 'mainCategoriesNotes',
      'subcatsTop8ValueChart', 'subcatsTop8QtyChart', 'subcatsTop8Notes',
      'subcatsDistributionDonutLY', 'subcatsDistributionDonutTY', 'subcatsDistributionNotes',
      'maincatsDistributionDonutLY', 'maincatsDistributionDonutTY', 'maincatsDistributionNotes',
      'stgMtdValueChart', 'stgMtdQtyChart',
      'stgYtdValueChart', 'stgYtdQtyChart', 'stgNotes',
      'stgDistributionDonutValueLY', 'stgDistributionDonutValueTY',
      'stgDistributionDonutQtyLY', 'stgDistributionDonutQtyTY',
      'stgDistributionNotes',
      'topcatSubcatsMtdChart', 'topcatSubcatsYtdChart', 'topcatSubcatsNotes',
      'top3ByClassValueChart_c1', 'top3ByClassQtyChart_c1',
      'top3ByClassValueChart_c2', 'top3ByClassQtyChart_c2',
      'top3ByClassValueChart_c3', 'top3ByClassQtyChart_c3',
      'top3ByClassValueChart_c4', 'top3ByClassQtyChart_c4', 'top3ByClassNotes',
      'regionsByClassValueChart_c1', 'regionsByClassQtyChart_c1',
      'regionsByClassValueChart_c2', 'regionsByClassQtyChart_c2',
      'regionsByClassValueChart_c3', 'regionsByClassQtyChart_c3',
      'regionsByClassValueChart_c4', 'regionsByClassQtyChart_c4', 'regionsByClassNotes',
      'stgRegionMaincatsChart_r1', 'stgRegionMaincatsChart_r2',
      'stgRegionMaincatsChart_r3', 'stgRegionMaincatsChart_r4', 'stgRegionMaincatsNotes',
      'stgRegionSubcatsChart_r1', 'stgRegionSubcatsChart_r2',
      'stgRegionSubcatsChart_r3', 'stgRegionSubcatsChart_r4', 'stgRegionSubcatsNotes',
      'stgProductgroupsValueChart', 'stgProductgroupsQtyChart', 'stgProductgroupsNotes',
    ];
    this.levelFilterList = LEVEL_ORDER.map(v => ({ v, l: t(LEVEL_FILTER_LABELS[v]) }));
    this.refs = {};
    for (const name of refNames) this.refs[name] = useRef(name);

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
    });
    // A tab opened by setToggle is laid out by THIS patch — the first
    // moment its charts can measure a real width.
    onPatched(() => {
      if (!this._pendingPanels.size) return;
      const keys = [...this._pendingPanels];
      this._pendingPanels.clear();
      for (const key of keys) {
        // Every registered slug, not just the active one: a key can be
        // pending because its panels only just entered the DOM (see
        // drawPanel), in which case the active tab is not the only one that
        // has never been drawn. The draw closures no-op on a slug that is
        // still absent, so this stays safe as well as cheap.
        for (const draw of Object.values(this._panelDraw[key] || {})) draw();
      }
      // Narrative panels are painted straight into the DOM, so the ones
      // whose slot did not exist when renderAll ran are still blank.
      this.repaintNarratives();
    });
    onWillUnmount(() => {
      document.removeEventListener('mousemove', this._onMouseMove);
      if (tooltipEl === this.refs.tooltip.el) tooltipEl = null;
      clearTooltipEl(this.refs.tooltip.el);
    });
  }

  // -- (i) process-note icons: hover shows what data/formula backs a
  // section, reusing the same tooltip element as the chart bar tooltips.
  onInfoEnter(ev, key) { showTip(ev, PROCESS_NOTES[key] || '', true); }
  onInfoLeave() { hideTip(); }

  // -- filters ----------------------------------------------------------
  selectYear(v) { this.state.year = +v; this.load(); }
  selectMonth(v) { this.state.month = +v; this.load(); }
  selectSalesman(v) {
    this.state.salesman = v;
    this.state.levelFilters = { ...this.state.levelFilters, salesman: v };
    this.load();
  }
  selectSubMode(v) { this.state.subMode = v; this.load(); }
  toggleFilters() { this.state.filtersCollapsed = !this.state.filtersCollapsed; }
  toggleLevels() { this.state.levelsCollapsed = !this.state.levelsCollapsed; }

  selectLevelFilter(level, v) {
    const value = v === 'all' ? 'all' : v;
    if (this.state.levelFilters[level] === value) return;
    this.state.levelFilters = { ...this.state.levelFilters, [level]: value };
    if (level === 'salesman') {
      this.state.salesman = value;
    }
    this.load();
  }
  levelValue(level) {
    return this.state.levelFilters[level] || 'all';
  }
  levelOptions(level) {
    return this.state.levelFilterOptions[level] || [];
  }

  setToggle(key, v) {
    if (this.state.toggleState[key] === v) return;
    // Narrative for stgRegionSubcats, stgRegionMaincats and regionsByClass
    // is keyed per region / class; move the slot registration to the new key
    // so repaintNarratives shows the right notes when the active tab changes.
    if (key === 'stgRegionSubcats') {
      const oldKey = 'stg-region-subcats_' + this.state.toggleState[key];
      const newKey = 'stg-region-subcats_' + v;
      if (this._narrativeSlots[oldKey]) {
        this._narrativeSlots[newKey] = this._narrativeSlots[oldKey];
        delete this._narrativeSlots[oldKey];
      }
    }
    if (key === 'stgRegionMaincats') {
      const oldKey = 'stg-region-maincats_' + this.state.toggleState[key];
      const newKey = 'stg-region-maincats_' + v;
      if (this._narrativeSlots[oldKey]) {
        this._narrativeSlots[newKey] = this._narrativeSlots[oldKey];
        delete this._narrativeSlots[oldKey];
      }
    }
    if (key === 'top3ByClass') {
      const oldKey = 'top3-by-class_' + this.state.toggleState[key];
      const newKey = 'top3-by-class_' + v;
      if (this._narrativeSlots[oldKey]) {
        this._narrativeSlots[newKey] = this._narrativeSlots[oldKey];
        delete this._narrativeSlots[oldKey];
      }
    }
    if (key === 'regionsByClass') {
      const oldKey = 'regions-by-class_' + this.state.toggleState[key];
      const newKey = 'regions-by-class_' + v;
      if (this._narrativeSlots[oldKey]) {
        this._narrativeSlots[newKey] = this._narrativeSlots[oldKey];
        delete this._narrativeSlots[oldKey];
      }
    }
    if (key === 'quarterlySaleTypeGroup') {
      const oldKey = 'quarterly-saletypegroup_' + this.state.toggleState[key];
      const newKey = 'quarterly-saletypegroup_' + v;
      if (this._narrativeSlots[oldKey]) {
        this._narrativeSlots[newKey] = this._narrativeSlots[oldKey];
        delete this._narrativeSlots[oldKey];
      }
    }
    if (key === 'quarterlyRegion') {
      const oldKey = 'quarterly-region_' + this.state.toggleState[key];
      const newKey = 'quarterly-region_' + v;
      if (this._narrativeSlots[oldKey]) {
        this._narrativeSlots[newKey] = this._narrativeSlots[oldKey];
        delete this._narrativeSlots[oldKey];
      }
    }
    this.state.toggleState[key] = v;
    this._pendingPanels.add(key);
  }

  // Register (and immediately run) one toggle panel's chart draw.
  //
  // Every chart here sizes itself from its container's clientWidth, and a
  // .toggle-panel that is not the active one is display:none — clientWidth
  // 0, so the primitives fell back to their 480px minimum. renderAll draws
  // all four tabs at once, so only the tab that happened to be open was
  // measured against the real page width; the other three kept a 480px-wide
  // SVG for the rest of the session and looked narrow the moment they were
  // opened. Keeping the draw here lets onPatched re-run it once the panel is
  // actually on screen, with no reload of the payload.
  //
  // A panel's slot can be MISSING when renderAll runs. The quarter pages
  // render only the quarters this period has, and renderAll runs the moment
  // the payload lands — before OWL has patched the new toggle row in, so on a
  // first load every quarter past Q1 is still absent from the DOM. Drawing
  // then is impossible and skipping outright leaves the panel permanently
  // blank; deferring to onPatched draws it at the first moment it exists,
  // which is also the first moment it has a real width.
  //
  // THE DRAW ITSELF REPORTS THAT, by returning false — see drawInto. It used
  // to be a fourth argument holding the element, and that was a trap: four of
  // the six call sites still passed three arguments, so `el` came through
  // undefined, the panel was queued instead of drawn, and pages 13 to 16 came
  // up blank on every first load. They only appeared once a tab was clicked,
  // which is exactly what a verification sweep does before it measures — so
  // the sweep never saw it. A caller cannot forget a return value the way it
  // can forget an argument.
  drawPanel(toggleKey, slug, draw) {
    (this._panelDraw[toggleKey] = this._panelDraw[toggleKey] || {})[slug] = draw;
    if (draw() === false) this._pendingPanels.add(toggleKey);
  }

  // Draw into a ref, but only if it is actually in the DOM. Returns false when
  // it is not, which is what tells drawPanel to wait for the patch that puts
  // it there.
  drawInto(refName, paint) {
    const el = this.refs[refName] && this.refs[refName].el;
    if (!el) return false;
    paint(el);
    return true;
  }

  // The label a toggle slug stands for THIS period — used by the per-tab
  // print headings, which have to be self-contained on a printed page.
  tabLabel(tabs, slug) {
    const tab = (tabs || []).find(x => x.v === slug);
    if (tab && tab.l) return tab.l;
    return (tabs && tabs[0]) ? tabs[0].l : '';
  }

  // Whether a slug is in this period's toggle row at all. Only the quarter
  // pages ask: their row is short rather than padded, so a panel for a
  // quarter that has not happened must not be rendered — and therefore must
  // not print either.
  hasTab(tabs, slug) {
    return (tabs || []).some(x => x.v === slug);
  }

  // The board's own chart palette, taken from the client's Excel deck — see the
  // --report-* block at the top of sales_mail_sman_dashboard.css for why these
  // are named separately from the shared --series-* chrome colours. The
  // --series-* fallbacks keep the charts drawn (in the old colours) if that
  // stylesheet ever fails to load.
  _color(style, name, fallback) {
    return style.getPropertyValue(name).trim() || style.getPropertyValue(fallback).trim();
  }
  seriesColors() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    // [Target, This Year, Last Year] — bar order throughout matching PDF deck.
    return [this._color(style, '--report-target', '--series-3'),
            this._color(style, '--report-this-year', '--series-1'),
            this._color(style, '--report-last-year', '--series-2')];
  }
  lineColors() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    return [this._color(style, '--report-vs-target', '--series-5'),
            this._color(style, '--report-vs-last-year', '--series-6')];
  }

  // -- export -----------------------------------------------------------
  exportParams() {
    return new URLSearchParams({
      period: `${this.state.year}-${String(this.state.month).padStart(2, '0')}`,
      salesman: this.state.salesman,
      subCategoryMode: this.state.subMode,
      scope: this.state.scope,
    });
  }

  // Whether this server can build a .pptx at all — Export PowerPoint goes
  // through python-pptx, which is optional.
  get pptxReady() {
    const caps = this.state.capabilities;
    return !caps || !caps.pptx || caps.pptx.available !== false;
  }

  // The server's own sentence: which package is missing and how to install
  // it. Shown beside the disabled button and on hover.
  get pptxMessage() {
    const caps = this.state.capabilities;
    return (caps && caps.pptx && caps.pptx.message) || '';
  }

  exportPptx() {
    if (!this.pptxReady) { this.state.error = this.pptxMessage; return; }
    window.open(`/pbi_dashboards/sales_mail_sman/export.pptx?${this.exportParams()}`, '_blank');
  }

  // -- data load --------------------------------------------------------
  // Every filter change calls load() immediately, with no debounce — two
  // picks made in quick succession fire two overlapping requests, and network
  // timing doesn't guarantee they resolve in the order they were sent.
  // Without a guard the OLDER request could resolve last and overwrite the
  // newer selection's data with stale figures, so the dashboard would show
  // and export the wrong period while the controls displayed the latest pick.
  // this._loadSeq tags each call; a response is applied only if it is still
  // the most recently-started one. this._loadPromise lets a caller await a
  // load already in flight.
  load() {
    const seq = ++this._loadSeq;
    this.state.loading = true;
    this.state.error = '';
    this._loadPromise = this._loadImpl(seq);
    return this._loadPromise;
  }

  async _loadImpl(seq) {
    try {
      const period = (this.state.year && this.state.month)
        ? `${this.state.year}-${String(this.state.month).padStart(2, '0')}` : null;
      const res = await this.rpc('/pbi_dashboards/sales_mail_sman/data', {
        period,
        salesman: this.state.salesman,
        subCategoryMode: this.state.subMode,
        scope: this.state.scope,
        levelFilters: this.state.levelFilters,
      });
      if (seq !== this._loadSeq) return;
      if (res.error) { this.state.error = res.error; return; }
      this.state.capabilities = res.capabilities || null;
      // A server that predates the notes editor sends no requirements map.
      res.requirements = res.requirements || {};
      this.state.reqPresets = res.requirementPresets || [];
      this.lastJson = res;
      // This payload is a different period/salesman than the drafts were
      // written against (the filters are locked while editing, so this can
      // only be a load that started before edit mode did).
      this._noteDrafts = {};
      this._reqDrafts = {};
      this.state.noteDirty = 0;
      this.state.year = res.period.year;
      this.state.month = res.period.month;
      this.state.periodLabel = tDate(res.period.label);
      this.state.hasPrevYear = res.hasPrevYear;
      if (res.scope) this.state.scope = res.scope;
      this.state.yearOptions = res.yearOptions;
      this.state.salesmanOptions = res.salesmanOptions;
      if (res.levelFilterOptions) {
        this.state.levelFilterOptions = res.levelFilterOptions;
      }
      // The server decides the effective salesman (an unknown code falls back
      // to All) — echo it back so the select shows what was used.
      this.state.salesman = res.salesman;
      this.state.subMode = res.subCategoryMode;
      this.state.classTabs = res.classTabs || [];
      this.state.regionTabs = res.regionTabs || [];
      this.state.quarterTabs = res.quarterTabs || [];
      // The month can move backwards (December -> February), taking the open
      // quarter tab with it. Left pointing at a quarter that no longer exists,
      // the page would show a toggle bar with nothing selected and a blank
      // panel below it.
      for (const key of ['quarterlySaleTypeGroup', 'quarterlyRegion']) {
        if (!this.hasTab(res.quarterTabs, this.state.toggleState[key])) {
          this.state.toggleState[key] = (res.quarterTabs && res.quarterTabs[0]) ? res.quarterTabs[0].v : 'q1';
        }
      }
      for (const key of ['top3ByClass', 'regionsByClass']) {
        if (!this.hasTab(res.classTabs, this.state.toggleState[key])) {
          this.state.toggleState[key] = (res.classTabs && res.classTabs[0]) ? res.classTabs[0].v : 'c1';
        }
      }
      for (const key of ['stgRegionMaincats', 'stgRegionSubcats']) {
        if (!this.hasTab(res.regionTabs, this.state.toggleState[key])) {
          this.state.toggleState[key] = (res.regionTabs && res.regionTabs[0]) ? res.regionTabs[0].v : 'r1';
        }
      }
      this.state.topClassLabel = res.topClassLabel;
      this.state.topSaleTypeGroupLabel = res.topSaleTypeGroupLabel;
      this.state.topMainCategoryLabel = res.topMainCategoryLabel;
      this.renderAll();
    } catch (e) {
      if (seq !== this._loadSeq) return;
      this.state.error = t('Failed to load — ') + e.message;
    } finally {
      if (seq === this._loadSeq) this.state.loading = false;
    }
  }

  // -- KPI tiles: 6 Value + 6 Qty (This Year/Target/Last Year, with the
  // achievement%/YoY% badges folded into the This-Year/Target tile). --
  renderKpis() {
    const k = this.lastJson.kpis;
    // NB: 'tile' is the per-tile loop variable, not 't' — 't' is the
    // imported pbi_i18n translator and would be shadowed inside these
    // closures, so all chrome words are translated up front.
    const mtdLabel = t('MTD'), ytdLabel = t('YTD'), actualLabel = t('Actual');
    const subBadge = (value, comparedTo, prefix) => {
      const p = pct(value, comparedTo);
      if (p == null) return '';
      const cls = p >= 100 ? 'good' : 'bad';
      return `<div class="sub">${prefix} <span class="${cls}">${fmtPct(p)}</span></div>`;
    };
    // The budget carries no salesman -- 60.3% of its money sits on the '*'
    // wildcard -- so once a Salesman is selected there is no target for ANY of
    // the seventeen pages, and the server says so with hasBudget: false. Show
    // an em dash, not a zero: "0" reads as "we budgeted nothing", and the Achv
    // badge beside it would read as 0% achievement against a real business.
    const noTarget = this.lastJson.hasBudget === false;
    const block = (fmtFn, thisYear, target, lastYear) => [
      { value: fmtFn(thisYear), raw: fmt(thisYear), suffix: t('This Year'), sub: subBadge(thisYear, lastYear, t('vs LY')) },
      noTarget
        ? { value: '—', raw: t('No target for a single salesman'), suffix: t('Target'), sub: '', dark: true }
        : { value: fmtFn(target), raw: fmt(target), suffix: t('Target'), sub: subBadge(thisYear, target, t('Achv')) },
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
      <div class="pbi-kpi tile-color-${i % 3}${tile.dark ? ' no-target' : ''}" data-tip="${tile.label}||${actualLabel}||${tile.raw}">
        <div class="value">${tile.value}</div>
        <div class="label">${tile.label}</div>
        ${tile.sub}
      </div>`;
    this.refs.kpiAmountRow.el.innerHTML = amountTiles.map(tileHtml).join('');
    this.refs.kpiQtyRow.el.innerHTML = qtyTiles.map(tileHtml).join('');
    attachValueTooltips(this.refs.kpiAmountRow.el, '.pbi-kpi[data-tip]');
    attachValueTooltips(this.refs.kpiQtyRow.el, '.pbi-kpi[data-tip]');
  }

  // -- narrative panel: a stored note override wins over the computed one --
  // Called once per section by renderAll, which is also where the section's
  // ref is registered, so edit mode can repaint the panels on its own.
  putNarrative(ref, key) {
    this._narrativeSlots[key] = ref;
    this.paintNarrative(key);
  }

  // What the panel shows right now: the editor while editing, otherwise the
  // saved note (or the computed narrative) with any requirement above it.
  paintNarrative(key) {
    const ref = this._narrativeSlots[key];
    if (!ref || !ref.el || !this.lastJson) return;
    const override = this.lastJson.notes[key];
    if (!this.state.editMode) {
      // Read mode is the REPORT, and a report shows its findings, not the
      // apparatus behind them. The requirement is an instruction addressed to
      // whoever writes the note, and "Edited note" is bookkeeping about who
      // wrote it; neither is anything the reader of a sales pack needs, and
      // both were being carried into print as well.
      //
      // Nothing is lost — Edit Notes brings both straight back, which is where
      // they belong: the editor gives the requirement its own box and marks an
      // overridden note with the same tag inline.
      ref.el.innerHTML = narrativeHtml(override || this.lastJson.narratives[key] || '');
      return;
    }
    ref.el.innerHTML = noteEditorHtml(this.noteValue(key), this.requirementValue(key),
                                      !!override, this.presetList());
    const presetEl = ref.el.querySelector('.note-preset');
    presetEl.addEventListener('change', () => {
      const picked = this.presetList()[+presetEl.value];
      if (!picked) return;
      // The picked text lands in the box, where it can still be edited — a
      // preset is a starting point for this section, not a locked value.
      this._reqDrafts[key] = picked.text;
      const baseNarrative = this.lastJson.narratives[key] || '';
      this._noteDrafts[key] = synthesizeNoteForPreset(picked.text, baseNarrative);
      this.paintNarrative(key);
      this.countDirty();
    });
    ref.el.querySelector('.note-preset-add').addEventListener('click',
      () => this.addRequirementPreset(this.requirementValue(key)));
    ref.el.querySelector('.note-preset-del').addEventListener('click',
      () => this.removeRequirementPreset(this.requirementValue(key)));
    const reqEl = ref.el.querySelector('.note-req');
    const textEl = ref.el.querySelector('.note-text');
    reqEl.addEventListener('input', () => { this._reqDrafts[key] = reqEl.value; this.countDirty(); });
    textEl.addEventListener('input', () => { this._noteDrafts[key] = textEl.value; this.countDirty(); });
    ref.el.querySelector('.note-reset').addEventListener('click', () => {
      // Back to the sentences the dashboard computes from this period's
      // figures. Saved that way it stops being an override at all — see
      // savedNoteFor() — so the section starts tracking the data again.
      this.resetSectionDrafts(key);
      this.paintNarrative(key);
      this.countDirty();
    });
  }

  // What "default" means for ONE section, in one place: the sentences the
  // dashboard computes from this period's figures, and no requirement over
  // them. The per-section reset icon and Reset All both call this, so the two
  // cannot come to mean different things.
  //
  // The requirement goes with the note deliberately. A requirement is an
  // instruction for what the note should say; left standing over a recomputed
  // narrative it asks for something that generic text was never written to
  // answer, and the panel then reads as though the note ignored it.
  //
  // Drafts only — nothing is written until Save Notes, and Cancel discards it.
  resetSectionDrafts(key) {
    this._noteDrafts[key] = this.lastJson.narratives[key] || '';
    this._reqDrafts[key] = '';
  }

  repaintNarratives() {
    for (const key of Object.keys(this._narrativeSlots)) this.paintNarrative(key);
  }

  // -- requirement presets ----------------------------------------------
  // What every requirement dropdown lists: the module's own instructions
  // first, then whatever this database added, with duplicates dropped so an
  // entry added before it was predefined does not appear twice.
  presetList() {
    const predefined = REQUIREMENT_PRESETS.map(text => ({ text: t(text), custom: false }));
    const seen = new Set(predefined.map(p => p.text));
    const added = (this.state.reqPresets || [])
      .filter(text => text && !seen.has(text))
      .map(text => ({ text, custom: true }));
    return predefined.concat(added);
  }

  async writePresets(payload, okMessage) {
    try {
      const res = await this.rpc('/pbi_dashboards/sales_mail_sman/requirement_presets', payload);
      if (res.error) { this.state.error = res.error; return; }
      this.state.reqPresets = res.presets || [];
      this.state.noteStatus = okMessage;
      // Every panel carries its own copy of the dropdown.
      this.repaintNarratives();
    } catch (e) {
      this.state.error = t('Failed to save notes — ') + e.message;
    }
  }

  addRequirementPreset(text) {
    const value = (text || '').trim();
    if (!value) { this.state.noteStatus = t('Write a requirement first.'); return; }
    if (this.presetList().some(p => p.text === value)) {
      this.state.noteStatus = t('Already in the list.');
      return;
    }
    return this.writePresets({ add: value }, t('Added to the list.'));
  }

  removeRequirementPreset(text) {
    const value = (text || '').trim();
    // The predefined half ships with the module; only what was added here can
    // be taken away again.
    if (!this.presetList().some(p => p.text === value && p.custom)) {
      this.state.noteStatus = t('Only a requirement added here can be removed.');
      return;
    }
    return this.writePresets({ remove: value }, t('Removed from the list.'));
  }

  // -- note editing -----------------------------------------------------
  // The text in the box: what was typed, else the saved override, else the
  // computed narrative — the editor always opens on what the panel is showing.
  noteValue(key) {
    if (key in this._noteDrafts) return this._noteDrafts[key];
    return this.lastJson.notes[key] || this.lastJson.narratives[key] || '';
  }
  requirementValue(key) {
    if (key in this._reqDrafts) return this._reqDrafts[key];
    return (this.lastJson.requirements || {})[key] || '';
  }
  // A note that matches the computed narrative is NOT an override: stored, it
  // would freeze that section at today's figures for every future month. That
  // is what turns a section reset into a delete.
  savedNoteFor(key) {
    const draft = this.noteValue(key).trim();
    return draft === (this.lastJson.narratives[key] || '').trim() ? '' : draft;
  }

  // Every section a save has to consider.
  //
  // NOT just _narrativeSlots. Six of the seventeen pages are toggle pages and
  // only ever register their ACTIVE tab as a slot (renderAll passes
  // 'top3-by-class_' + the open slug), so the board mounts 17 panels out of 37
  // real note sections. A note written on Q2 and then left behind by switching
  // to Q1 is still stored, still exported to the deck, and was invisible to
  // both the save payload and Reset All — which is what made "Reset All" leave
  // notes standing.
  //
  // The drafts close that gap: anything the user has acted on this session is
  // included whether or not its panel is on screen. Deliberately NOT the whole
  // of lastJson.notes — an untouched stored note that happens to equal today's
  // computed narrative would then be deleted by any save the user did for some
  // other reason, which is a silent data loss nobody asked for.
  noteKeys() {
    return [...new Set([
      ...Object.keys(this._narrativeSlots),
      ...Object.keys(this._noteDrafts),
      ...Object.keys(this._reqDrafts),
    ])];
  }

  // {notes, requirements} holding only the sections whose stored value would
  // actually change — the save payload, and the dirty count behind it.
  noteChanges() {
    const notes = {}, requirements = {};
    for (const key of this.noteKeys()) {
      const wanted = this.savedNoteFor(key);
      if (wanted !== (this.lastJson.notes[key] || '').trim()) notes[key] = wanted;
      const wantedReq = this.requirementValue(key).trim();
      if (wantedReq !== ((this.lastJson.requirements || {})[key] || '').trim()) requirements[key] = wantedReq;
    }
    return { notes, requirements };
  }

  countDirty() {
    const { notes, requirements } = this.noteChanges();
    this.state.noteDirty = Object.keys(notes).length + Object.keys(requirements).length;
  }

  get dirtyLabel() {
    const n = this.state.noteDirty;
    return `${n} ${n === 1 ? t('unsaved change') : t('unsaved changes')}`;
  }

  startEditNotes() {
    if (!this.lastJson) return;
    this.state.noteStatus = '';
    this.state.editMode = true;
    this.countDirty();
    this.repaintNarratives();
  }

  // Every section back to what the dashboard computes from this period's
  // figures — the board as it reads with no note ever having been written.
  //
  // Drafts only: nothing is deleted until Save Notes, and Cancel still throws
  // the whole reset away, which is why one confirm covering all seventeen
  // pages is enough. Saved, it is a DELETE rather than a write of the computed
  // text — savedNoteFor() returns '' for a note that equals the narrative, and
  // an empty requirement drops its row — so the sections go back to tracking
  // the data instead of being frozen at today's numbers.
  //
  // The requirement goes too. "Default" is the panel with nothing on it; a
  // requirement left standing over a recomputed narrative would be asking for
  // something the generic text was not written to answer.
  resetAllNotes() {
    // The mounted panels plus every section that actually has something stored
    // — the notes on the toggle tabs that are not currently open are exactly
    // the ones "Reset All" was failing to reach.
    const keys = [...new Set([
      ...Object.keys(this._narrativeSlots),
      ...Object.keys(this.lastJson.notes || {}),
      ...Object.keys((this.lastJson || {}).requirements || {}),
    ])];
    if (!keys.length) return;
    // The framework's dialog rather than window.confirm: the native one blocks
    // the whole tab and does not carry the backend's theme or RTL direction,
    // and this board is rendered in Arabic as often as in English.
    this.dialog.add(ConfirmationDialog, {
      title: t('Reset all notes'),
      body: t('Reset the notes and requirements on every section back to the computed defaults? ' +
              'Nothing is deleted until you press Save Notes — Cancel still undoes this.'),
      confirmLabel: t('Reset All'),
      cancelLabel: t('Cancel'),
      confirm: () => {
        for (const key of keys) this.resetSectionDrafts(key);
        this.state.noteStatus = t('All sections reset to the computed defaults — press Save Notes to keep it.');
        this.repaintNarratives();
        this.countDirty();
      },
      cancel: () => {},
    });
  }

  cancelEditNotes() {
    this._noteDrafts = {};
    this._reqDrafts = {};
    this.state.editMode = false;
    this.state.noteDirty = 0;
    this.state.noteStatus = '';
    this.repaintNarratives();
  }

  async saveNotes() {
    const { notes, requirements } = this.noteChanges();
    if (!Object.keys(notes).length && !Object.keys(requirements).length) {
      this.state.noteStatus = t('No changes to save.');
      return;
    }
    this.state.savingNotes = true;
    this.state.noteStatus = t('Saving…');
    try {
      const res = await this.rpc('/pbi_dashboards/sales_mail_sman/save_notes', {
        period: `${this.state.year}-${String(this.state.month).padStart(2, '0')}`,
        salesman: this.state.salesman,
        notes, requirements,
      });
      if (res.error) { this.state.error = res.error; this.state.noteStatus = ''; return; }
      // Fold the saved values into the payload the panels read from, so the
      // board reflects the save without reloading seventeen pages of queries.
      // An empty string came back as a deleted row, not as an empty note.
      this.lastJson.requirements = this.lastJson.requirements || {};
      for (const [key, text] of Object.entries(res.notes || {})) {
        if (text) this.lastJson.notes[key] = text; else delete this.lastJson.notes[key];
      }
      for (const [key, text] of Object.entries(res.requirements || {})) {
        if (text) this.lastJson.requirements[key] = text; else delete this.lastJson.requirements[key];
      }
      this.state.error = '';
      this.cancelEditNotes();
    } catch (e) {
      this.state.noteStatus = '';
      this.state.error = t('Failed to save notes — ') + e.message;
    } finally {
      this.state.savingNotes = false;
    }
  }

  _with_pct(rows) {
    return (rows || []).map(r => ({
      ...r,
      achievementPct: r.budget ? (r.sales / r.budget * 100) : null,
      yoyPct: r.prevYearSales ? (r.sales / r.prevYearSales * 100) : null,
    }));
  }

  renderAll() {
    const allColors = this.seriesColors();
    const colors = this.lastJson.hasBudget === false
      ? [allColors[1], allColors[2]]
      : [allColors[0], allColors[1], allColors[2]];
    const lineColors = this.lineColors();
    const noTarget = this.lastJson.hasBudget === false;
    const valueSeries = noTarget ? ['sales', 'prevYearSales'] : ['budget', 'sales', 'prevYearSales'];
    const qtySeries = noTarget ? ['qty', 'prevYearQty'] : ['budgetQty', 'qty', 'prevYearQty'];
    const year = this.state.year || (this.lastJson && this.lastJson.year) || 2025;
    const prevYear = year - 1;
    const seriesLabels = noTarget ? [`A. ${year}`, `A. ${prevYear}`]
                                  : [t('Target'), `A. ${year}`, `A. ${prevYear}`];
    const page2BarLabels = noTarget ? [`${year}`, `${prevYear}`]
                                    : [t('Target'), `${year}`, `${prevYear}`];
    const trendLineLabels = noTarget ? [`Vs. ${prevYear}`]
                                     : [t('Vs. Target'), `Vs. ${prevYear}`];
    const j = this.lastJson;

    this._panelDraw = {};
    this._pendingPanels.clear();

    this.renderKpis();

    // Page 1 — Total Company
    groupedBarChart(this.refs.totalCompanyMtdValueChart.el, j.totalCompany.mtd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.totalCompanyMtdQtyChart.el, j.totalCompany.mtd, qtySeries, colors, seriesLabels, fmtK);
    groupedBarChart(this.refs.totalCompanyYtdValueChart.el, j.totalCompany.ytd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.totalCompanyYtdQtyChart.el, j.totalCompany.ytd, qtySeries, colors, seriesLabels, fmtK);
    this.putNarrative(this.refs.totalCompanyNotes, 'total-company');

    // Page 2 — Sales Achievement and Growth Trends by Department & Region (combo charts with Total included as 5th group)
    comboBarLineChart(this.refs.classTrendChart.el, this._with_pct(j.classTrend || []), valueSeries, colors, page2BarLabels,
      ['achievementPct', 'yoyPct'], lineColors, trendLineLabels, fmtM);
    comboBarLineChart(this.refs.regionTrendChart.el, this._with_pct(j.regionTrend || []), valueSeries, colors, page2BarLabels,
      ['achievementPct', 'yoyPct'], lineColors, trendLineLabels, fmtM);
    this.putNarrative(this.refs.classRegionTrendsNotes, 'class-region-trends');

    // Page 3 — Total Company Sales Quarterly Sales Progression
    groupedBarChart(this.refs.quarterlyCompanyChart.el, j.quarterlyCompany, valueSeries, colors, seriesLabels, fmtM);
    this.putNarrative(this.refs.quarterlyCompanyNotes, 'quarterly-company');

    // Page 4 — Total Company Sales Quarterly Sales Progression (by Department) (tabs: q1..q4)
    for (const slug of this.quarterSlugs) {
      this.drawPanel('quarterlySaleTypeGroup', slug, () => {
        const rows = (j.quarterlySaleTypeGroup && j.quarterlySaleTypeGroup[slug]) || [];
        return this.drawInto(
          'quarterlyStgChart_' + slug, el =>
            groupedBarChart(el, rows, valueSeries, colors, seriesLabels, fmtM)
        );
      });
    }
    this.putNarrative(this.refs.quarterlyStgNotes, 'quarterly-saletypegroup_' + this.state.toggleState.quarterlySaleTypeGroup);

    // Page 5 — Dealers Department Quarterly Sales Progression (tabs: q1..q4)
    for (const slug of this.quarterSlugs) {
      this.drawPanel('quarterlyRegion', slug, () => {
        const rows = (j.quarterlyRegion && j.quarterlyRegion[slug]) || [];
        return this.drawInto(
          'quarterlyRegionChart_' + slug, el =>
            groupedBarChart(el, rows, valueSeries, colors, seriesLabels, fmtM)
        );
      });
    }
    this.putNarrative(this.refs.quarterlyRegionNotes, 'quarterly-region_' + this.state.toggleState.quarterlyRegion);

    // Page 6 — Total Company Sales vs. Target & Last Year by Group by Value (4 cards: Left=Window/Split, Right=Sub-categories: RAC, LCAC, etc.)
    const mtdAll = j.mainCategories.mtd || [];
    const ytdAll = j.mainCategories.ytd || [];
    const isWS = d => ['Window', 'Split', 'ACWIN', 'ACSPL'].includes(d.code) || /window|split/i.test(d.label);
    const isLC = d => ['LCAC', 'CAC', 'ACLCA', 'ACCAC', 'VRF', 'Concealed'].includes(d.code) || /lcac|cac|vrf|concealed/i.test(d.label);

    const mtdWS = mtdAll.filter(isWS).length ? mtdAll.filter(isWS) : mtdAll.slice(0, 2);
    const ytdWS = ytdAll.filter(isWS).length ? ytdAll.filter(isWS) : ytdAll.slice(0, 2);

    const subMtd = (j.lcacSubcats && j.lcacSubcats.mtd) || (j.topcatSubcats && j.topcatSubcats.mtd) || [];
    const subYtd = (j.lcacSubcats && j.lcacSubcats.ytd) || (j.topcatSubcats && j.topcatSubcats.ytd) || [];

    const mtdLC = subMtd.filter(d => !isWS(d)).length
      ? subMtd.filter(d => !isWS(d))
      : (subMtd.length ? subMtd : (mtdAll.filter(isLC).length ? mtdAll.filter(isLC) : mtdAll.filter(d => !isWS(d))));

    const ytdLC = subYtd.filter(d => !isWS(d)).length
      ? subYtd.filter(d => !isWS(d))
      : (subYtd.length ? subYtd : (ytdAll.filter(isLC).length ? ytdAll.filter(isLC) : ytdAll.filter(d => !isWS(d))));

    groupedBarChart(this.refs.mainCategoriesMtdWSChart.el, mtdWS, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.mainCategoriesMtdLCChart.el, mtdLC, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.mainCategoriesYtdWSChart.el, ytdWS, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.mainCategoriesYtdLCChart.el, ytdLC, valueSeries, colors, seriesLabels, fmtM);
    this.putNarrative(this.refs.mainCategoriesNotes, 'main-categories');

    // Page 7 — Total Company Sales vs. Target & Last Year by Sub-Group Value & QTY
    groupedBarChart(this.refs.subcatsTop8ValueChart.el, j.subcatsTop8, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.subcatsTop8QtyChart.el, byQtyDesc(j.subcatsTop8), qtySeries, colors, seriesLabels, fmtK);
    this.putNarrative(this.refs.subcatsTop8Notes, 'subcats-top8');

    // Page 8 — Total Company Split Sales Distribution by Category by Value & QTY
    pieChart3D(this.refs.subcatsDistributionDonutLY.el, j.subcatsTop8.map(d => ({ label: d.label, value: d.prevYearSales })), PALETTE, fmtM);
    pieChart3D(this.refs.subcatsDistributionDonutTY.el, j.subcatsTop8.map(d => ({ label: d.label, value: d.sales })), PALETTE, fmtM);
    this.putNarrative(this.refs.subcatsDistributionNotes, 'subcats-distribution');

    // Page 9 — Total Company Sales Distribution by Category by Value
    const maincatsGroupedYtd = [...ytdWS, ...ytdLC];
    pieChart3D(this.refs.maincatsDistributionDonutLY.el, maincatsGroupedYtd.map(d => ({ label: d.label, value: d.prevYearSales })), PALETTE, fmtM);
    pieChart3D(this.refs.maincatsDistributionDonutTY.el, maincatsGroupedYtd.map(d => ({ label: d.label, value: d.sales })), PALETTE, fmtM);
    this.putNarrative(this.refs.maincatsDistributionNotes, 'maincats-distribution');

    // Page 10 — Total Company Sales vs. Target & Last Year by Department by Value & QTY
    groupedBarChart(this.refs.stgMtdValueChart.el, j.saleTypeGroups.mtd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.stgMtdQtyChart.el, byQtyDesc(j.saleTypeGroups.mtd), qtySeries, colors, seriesLabels, fmtK);
    groupedBarChart(this.refs.stgYtdValueChart.el, j.saleTypeGroups.ytd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.stgYtdQtyChart.el, byQtyDesc(j.saleTypeGroups.ytd), qtySeries, colors, seriesLabels, fmtK);
    this.putNarrative(this.refs.stgNotes, 'saletypegroups');

    // Page 11 — Total Company Sales Distribution by Channel by Value & QTY
    pieChart3D(this.refs.stgDistributionDonutValueLY.el, j.saleTypeGroups.ytd.map(d => ({ label: d.label, value: d.prevYearSales })), PALETTE, fmtM);
    pieChart3D(this.refs.stgDistributionDonutValueTY.el, j.saleTypeGroups.ytd.map(d => ({ label: d.label, value: d.sales })), PALETTE, fmtM);
    pieChart3D(this.refs.stgDistributionDonutQtyLY.el, byQtyDesc(j.saleTypeGroups.ytd).map(d => ({ label: d.label, value: d.prevYearQty })), PALETTE, fmtK);
    pieChart3D(this.refs.stgDistributionDonutQtyTY.el, byQtyDesc(j.saleTypeGroups.ytd).map(d => ({ label: d.label, value: d.qty })), PALETTE, fmtK);
    this.putNarrative(this.refs.stgDistributionNotes, 'saletypegroups-distribution');

    // Page 12 — Total Company Sales vs. Target & Last Year by Sub-Group Value & QTY (LCAC)
    groupedBarChart(this.refs.topcatSubcatsMtdChart.el, j.topcatSubcats.mtd, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.topcatSubcatsYtdChart.el, j.topcatSubcats.ytd, valueSeries, colors, seriesLabels, fmtM);
    this.putNarrative(this.refs.topcatSubcatsNotes, 'topcat-subcats');

    // Page 13 — Total Sales vs. Target & Last Year by Department & Category by Value & Qty (tabs: c1..c4)
    for (const slug of this.classSlugs) {
      this.drawPanel('top3ByClass', slug, () => {
        const rows = j.top3ByClass[slug] || [];
        const drawnV = this.drawInto(
          'top3ByClassValueChart_' + slug, el =>
            groupedBarChart(el, rows, valueSeries, colors, seriesLabels, fmtM)
        );
        const drawnQ = this.drawInto(
          'top3ByClassQtyChart_' + slug, el =>
            groupedBarChart(el, byQtyDesc(rows), qtySeries, colors, seriesLabels, fmtK)
        );
        return drawnV && drawnQ;
      });
    }
    this.putNarrative(this.refs.top3ByClassNotes, 'top3-by-class_' + this.state.toggleState.top3ByClass);

    // Page 14 — Total Sales vs. Target & Last Year by Department by Value & Qty (tabs: c1..c4)
    for (const slug of this.classSlugs) {
      this.drawPanel('regionsByClass', slug, () => {
        const rows = j.regionsByClass[slug] || [];
        const drawnV = this.drawInto(
          'regionsByClassValueChart_' + slug, el =>
            groupedBarChart(el, rows, valueSeries, colors, seriesLabels, fmtM)
        );
        const drawnQ = this.drawInto(
          'regionsByClassQtyChart_' + slug, el =>
            groupedBarChart(el, byQtyDesc(rows), qtySeries, colors, seriesLabels, fmtK)
        );
        return drawnV && drawnQ;
      });
    }
    this.putNarrative(this.refs.regionsByClassNotes, 'regions-by-class_' + this.state.toggleState.regionsByClass);

    // Page 15 — Total Sales vs. Target & Last Year by Dealers & Category by Region by Value (tabs: r1..r4)
    for (const slug of this.regionSlugs) {
      this.drawPanel('stgRegionMaincats', slug, () => this.drawInto(
        'stgRegionMaincatsChart_' + slug, el =>
          groupedBarChart(el, j.stgRegionMaincats[slug] || [], valueSeries, colors, seriesLabels, fmtM)
      ));
    }
    this.putNarrative(this.refs.stgRegionMaincatsNotes, 'stg-region-maincats_' + this.state.toggleState.stgRegionMaincats);

    // Page 16 — Total Sales vs. Target & Last Year by Dealers by Region by Value (Split) (r1: West, r2: Riyadh, r3: East, r4: Qassim)
    for (const slug of this.regionSlugs) {
      this.drawPanel('stgRegionSubcats', slug, () => this.drawInto(
        'stgRegionSubcatsChart_' + slug, el =>
          groupedBarChart(el, j.stgRegionSubcats[slug] || [], valueSeries, colors, seriesLabels, fmtM)
      ));
    }
    this.putNarrative(this.refs.stgRegionSubcatsNotes, 'stg-region-subcats_' + this.state.toggleState.stgRegionSubcats);

    // Page 17 — Total Projects Sales vs. Target & Last Year by Category By Value & QTY
    groupedBarChart(this.refs.stgProductgroupsValueChart.el, j.stgProductgroups, valueSeries, colors, seriesLabels, fmtM);
    groupedBarChart(this.refs.stgProductgroupsQtyChart.el, byQtyDesc(j.stgProductgroups), qtySeries, colors, seriesLabels, fmtK);
    this.putNarrative(this.refs.stgProductgroupsNotes, 'stg-productgroups');
  }
}

registry.category("actions").add("pbi_sales_dashboards.sales_mail_sman_dashboard", PbiSalesMailSmanDashboard);

