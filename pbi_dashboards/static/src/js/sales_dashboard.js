/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// ---------------------------------------------------------------------
// formatting helpers
// ---------------------------------------------------------------------
const fmt = n => n == null ? "–" : new Intl.NumberFormat('en-US').format(Math.round(n));
const fmtM = n => n == null ? "–" : (n / 1e6).toFixed(1) + "M";
const fmtCompact = n => n == null ? "–" : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(n);
function fmtShare(part, total) { return total > 0 ? Math.round(part / total * 100) + '%' : '–'; }
function fmtYoy(a, b) {
  if (!(a > 0)) return null;
  return (b - a) / a * 100;
}
function yoyWord(pct, upWord, downWord) { return pct >= 0 ? upWord : downWord; }
function yoyHtml(pct) {
  if (pct == null) return '<span class="bad">n/a</span>';
  const cls = pct >= 0 ? 'good' : 'bad';
  return `<span class="${cls}">${pct >= 0 ? '+' : ''}${pct.toFixed(0)}%</span>`;
}
function fmtDelta(pct) {
  if (pct == null) return '<span class="bad">n/a</span>';
  const cls = pct >= 0 ? 'good' : 'bad';
  const sign = pct >= 0 ? '+' : '';
  return `<span class="${cls}">${sign}${pct.toFixed(1)}%</span>`;
}
function legendHtml(labels, colors) {
  if (labels.length < 2) return '';
  return labels.map((l, i) => `<div class="item"><span class="swatch" style="background:${colors[i]}"></span>${l}</div>`).join('');
}

// Text edited into an exported PowerPoint's speaker notes and re-imported —
// rendered distinctly from the auto-generated HTML narrative it replaces
// (see PbiSalesDashboard.importNotes / renderNarratives). The stored text
// carries **bold**/##heading## markers reconstructed from the pptx's actual
// run formatting (see _pptx_read_notes_marked in main.py), so a word the
// user bolded/unbolded by hand in PowerPoint round-trips faithfully — not
// just the auto-bolded figures.
function escapeHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function markedToHtml(marked) {
  return marked.split(/(\*\*.+?\*\*)/g).map(part => {
    const m = part.match(/^\*\*(.*)\*\*$/);
    return m ? `<b>${escapeHtml(m[1])}</b>` : escapeHtml(part);
  }).join('');
}
function noteOverrideHtml(text) {
  const blocks = text.split(/\n+/).map(b => b.trim()).filter(Boolean);
  const html = blocks.flatMap(block => {
    const headingMatch = block.match(/^##(.*)##$/);
    if (headingMatch) return [`<h3>${escapeHtml(headingMatch[1])}</h3>`];
    return block.split(/(?<=[.!?])\s+(?=[A-Z(])/).map(s => s.trim()).filter(Boolean)
      .map(s => `<p>${markedToHtml(s)}</p>`);
  }).join('');
  return `<div class="edited-note-tag">Edited note</div>${html}`;
}

// ---------------------------------------------------------------------
// tooltip — module-scoped since only one dashboard instance is mounted
// at a time (a client action), mirroring the standalone prototype.
// ---------------------------------------------------------------------
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

// ---------------------------------------------------------------------
// citation counter — reset once per load()
// ---------------------------------------------------------------------
let citeSeq = 0;
function cite(title) {
  citeSeq += 1;
  return `<span class="cite" title="${title.replace(/"/g, '&quot;')}">${citeSeq}</span>`;
}

// ---------------------------------------------------------------------
// chart drawing (pure functions operating on a DOM element)
// ---------------------------------------------------------------------
function attachBarTooltips(el) {
  el.querySelectorAll('rect[data-tip]').forEach(rect => {
    rect.addEventListener('mousemove', evt => {
      const [label, seriesLabel, val] = rect.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${seriesLabel}: <b>${fmt(+val)}</b>`);
    });
    rect.addEventListener('mouseleave', hideTip);
  });
}

function groupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels, opts = {}) {
  const W = opts.width || el.clientWidth || 520, H = opts.height || 260;
  const marginL = 60, marginR = 10, marginT = 10, marginB = 30;
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const maxVal = Math.max(1, ...data.flatMap(d => seriesKeys.map(k => d[k] || 0))) * 1.12;
  const groupW = plotW / data.length;
  const barW = Math.min(28, (groupW * 0.6) / seriesKeys.length);
  const gap = 3;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  const ticks = 4;
  for (let i = 0; i <= ticks; i++) {
    const y = marginT + plotH - (plotH * i / ticks);
    const val = maxVal * i / ticks;
    svg += `<line class="gridline" x1="${marginL}" x2="${W - marginR}" y1="${y}" y2="${y}"/>`;
    svg += `<text class="axis-label" x="${marginL - 8}" y="${y + 3}" text-anchor="end">${fmtCompact(val)}</text>`;
  }
  svg += `<line class="baseline" x1="${marginL}" x2="${W - marginR}" y1="${marginT + plotH}" y2="${marginT + plotH}"/>`;

  const labelClickable = !!opts.onLabelClick;
  data.forEach((d, gi) => {
    const groupX = marginL + gi * groupW + groupW / 2 - (barW * seriesKeys.length + gap * (seriesKeys.length - 1)) / 2;
    seriesKeys.forEach((k, si) => {
      const val = d[k] || 0;
      const barH = plotH * (val / maxVal);
      const x = groupX + si * (barW + gap);
      const y = marginT + plotH - barH;
      svg += `<rect data-tip="${d.label}||${seriesLabels[si]}||${val}" rx="3" ry="3" x="${x}" y="${y}" width="${barW}" height="${Math.max(barH, 1)}" fill="${seriesColors[si]}" style="cursor:pointer"/>`;
    });
    // The category label doubles as a drill-down target (opts.onLabelClick)
    // so a bar too short to click reliably can still be drilled into.
    svg += `<text class="axis-label${labelClickable ? ' cat-label-clickable' : ''}" data-cat="${d.label}" x="${marginL + gi * groupW + groupW / 2}" y="${H - 8}" text-anchor="middle">${d.label}</text>`;
  });
  svg += `</svg>`;
  el.innerHTML = svg;
  attachBarTooltips(el);
  if (opts.onLabelClick) {
    el.querySelectorAll('text.cat-label-clickable').forEach(text => {
      text.addEventListener('click', () => opts.onLabelClick(text.getAttribute('data-cat')));
    });
  }
}

function hBarChart(el, data, color, valueLabel, opts = {}) {
  const W = opts.width || el.clientWidth || 520;
  const rowH = 26, marginL = 130, marginR = 60, marginT = 4;
  const H = data.length * rowH + marginT * 2;
  const plotW = W - marginL - marginR;
  const maxVal = Math.max(1, ...data.map(d => d.value || 0)) * 1.05;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  data.forEach((d, i) => {
    const y = marginT + i * rowH;
    const barW = plotW * ((d.value || 0) / maxVal);
    svg += `<text class="bar-label" x="${marginL - 8}" y="${y + rowH * 0.62}" text-anchor="end">${d.label}</text>`;
    svg += `<rect data-tip="${d.label}||${valueLabel}||${d.value || 0}" rx="3" ry="3" x="${marginL}" y="${y + rowH * 0.18}" width="${Math.max(barW, 2)}" height="${rowH * 0.55}" fill="${color}" style="cursor:pointer"/>`;
    svg += `<text class="axis-label" x="${marginL + barW + 6}" y="${y + rowH * 0.62}">${fmtCompact(d.value)}</text>`;
  });
  svg += `</svg>`;
  el.innerHTML = svg;
  attachBarTooltips(el);
}

function hGroupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels, opts = {}) {
  const W = opts.width || el.clientWidth || 520;
  const rowH = 34, marginL = 140, marginR = 60, marginT = 4;
  const H = data.length * rowH + marginT * 2;
  const plotW = W - marginL - marginR;
  const maxVal = Math.max(1, ...data.flatMap(d => seriesKeys.map(k => d[k] || 0))) * 1.08;
  const barH = Math.min(11, (rowH * 0.7) / seriesKeys.length);
  const gap = 2;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  data.forEach((d, i) => {
    const rowY = marginT + i * rowH;
    svg += `<text class="bar-label" x="${marginL - 8}" y="${rowY + rowH / 2 + 4}" text-anchor="end">${d.label}</text>`;
    seriesKeys.forEach((k, si) => {
      const val = d[k] || 0;
      const barW = plotW * (val / maxVal);
      const y = rowY + rowH / 2 - (barH * seriesKeys.length + gap * (seriesKeys.length - 1)) / 2 + si * (barH + gap);
      svg += `<rect data-tip="${d.label}||${seriesLabels[si]}||${val}" rx="2" ry="2" x="${marginL}" y="${y}" width="${Math.max(barW, 2)}" height="${barH}" fill="${seriesColors[si]}" style="cursor:pointer"/>`;
    });
  });
  svg += `</svg>`;
  el.innerHTML = svg;
  attachBarTooltips(el);
}

function lineChart(el, data, seriesKeys, seriesColors, seriesLabels, opts = {}) {
  const W = opts.width || el.clientWidth || 900, H = opts.height || 260;
  const marginL = 55, marginR = 15, marginT = 10, marginB = 30;
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const allVals = data.flatMap(d => seriesKeys.map(k => d[k])).filter(v => v != null);
  const maxVal = Math.max(1, ...allVals) * 1.1;
  const n = data.length;
  const x = i => marginL + plotW * (n === 1 ? 0.5 : i / (n - 1));
  const y = v => marginT + plotH - plotH * (v / maxVal);

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  const ticks = 4;
  for (let i = 0; i <= ticks; i++) {
    const gy = marginT + plotH - (plotH * i / ticks);
    svg += `<line class="gridline" x1="${marginL}" x2="${W - marginR}" y1="${gy}" y2="${gy}"/>`;
    svg += `<text class="axis-label" x="${marginL - 8}" y="${gy + 3}" text-anchor="end">${fmtCompact(maxVal * i / ticks)}</text>`;
  }
  svg += `<line class="baseline" x1="${marginL}" x2="${W - marginR}" y1="${marginT + plotH}" y2="${marginT + plotH}"/>`;

  const maxLabelLen = Math.max(1, ...data.map(d => (d.label || '').length));
  const approxLabelWidth = maxLabelLen * 6.2 + 10;
  const maxLabels = Math.max(2, Math.floor(plotW / approxLabelWidth));
  const labelStep = Math.max(1, Math.ceil(n / maxLabels));
  data.forEach((d, i) => {
    if (i % labelStep === 0) svg += `<text class="axis-label" x="${x(i)}" y="${H - 8}" text-anchor="middle">${d.label}</text>`;
  });

  seriesKeys.forEach((k, si) => {
    let path = '';
    data.forEach((d, i) => {
      if (d[k] == null) return;
      path += (path === '' ? 'M' : 'L') + x(i) + ',' + y(d[k]) + ' ';
    });
    svg += `<path d="${path}" fill="none" stroke="${seriesColors[si]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
  });

  if (opts.highlightIndex != null && opts.highlightIndex >= 0 && opts.highlightIndex < n) {
    const hi = opts.highlightIndex, hx = x(hi);
    svg += `<line class="highlight-line" x1="${hx}" x2="${hx}" y1="${marginT}" y2="${marginT + plotH}"/>`;
    seriesKeys.forEach((k, si) => {
      const v = data[hi][k];
      if (v == null) return;
      svg += `<circle class="highlight-dot" cx="${hx}" cy="${y(v)}" r="4" fill="${seriesColors[si]}"/>`;
    });
  }

  data.forEach((d, i) => {
    svg += `<rect data-i="${i}" x="${x(i) - plotW / n / 2}" y="${marginT}" width="${plotW / n}" height="${plotH}" fill="transparent" style="cursor:crosshair"/>`;
  });
  svg += `</svg>`;
  el.innerHTML = svg;

  el.querySelectorAll('rect[data-i]').forEach(rect => {
    const i = +rect.getAttribute('data-i');
    const d = data[i];
    rect.addEventListener('mousemove', evt => {
      let html = `<b>${d.label}</b><br>`;
      seriesKeys.forEach((k, si) => { html += `${seriesLabels[si]}: <b>${fmt(d[k])}</b><br>`; });
      showTip(evt, html);
    });
    rect.addEventListener('mouseleave', hideTip);
  });
}

// ---------------------------------------------------------------------
// narrative builders
// ---------------------------------------------------------------------
function monthValueSentence(monthLabel, fLabel, cur, prev) {
  const hasBudget = cur.budget > 0, hasPrev = !!prev;
  let s = `For <b>${monthLabel}</b>, ${fLabel} achieved sales value of <b>${fmtM(cur.sales)}</b>`;
  if (hasBudget && hasPrev) {
    const verb = cur.sales >= cur.budget ? 'outperforming' : 'underperforming';
    const cmp = cur.sales >= prev.sales ? 'still above' : 'below';
    s += ` versus a target of <b>${fmtM(cur.budget)}</b>, ${verb} the value target, though this was ${cmp} last year's <b>${fmtM(prev.sales)}</b> for the same period`;
  } else if (hasBudget) {
    const verb = cur.sales >= cur.budget ? 'outperforming' : 'underperforming';
    s += ` versus a target of <b>${fmtM(cur.budget)}</b>, ${verb} the value target`;
  } else if (hasPrev) {
    s += `, ${cur.sales >= prev.sales ? 'above' : 'below'} last year's <b>${fmtM(prev.sales)}</b> for the same period`;
  }
  return s;
}
function monthQtySentence(monthLabel, cur, prev) {
  const hasBudget = cur.budgetQty > 0, hasPrev = !!prev;
  let s = `In volume terms, ${monthLabel} sales reached <b>${fmt(cur.qty)} units</b>`;
  if (hasBudget && hasPrev) {
    s += ` compared with a target of <b>${fmt(cur.budgetQty)} units</b> and <b>${fmt(prev.qty)} units</b> last year, indicating ${cur.qty >= prev.qty ? 'growth' : 'a decline'} over last year ${cur.qty >= cur.budgetQty ? 'and ahead of the volume target' : 'but slightly below the volume target'}`;
  } else if (hasBudget) {
    s += ` compared with a target of <b>${fmt(cur.budgetQty)} units</b>, ${cur.qty >= cur.budgetQty ? 'ahead of' : 'below'} the volume target`;
  } else if (hasPrev) {
    s += ` compared with <b>${fmt(prev.qty)} units</b> last year, indicating ${cur.qty >= prev.qty ? 'growth' : 'a decline'} over last year`;
  }
  return s;
}
function ytdValueSentence(yearLabel, fLabel, cur, prev) {
  const hasBudget = cur.budget > 0, hasPrev = !!prev;
  let s = `For ${yearLabel} year-to-date, ${fLabel}'s sales value is <b>${fmtM(cur.sales)}</b>`;
  if (hasBudget && hasPrev) {
    const gapPct = Math.abs(cur.sales - cur.budget) / cur.budget * 100;
    const closeness = gapPct <= 5 ? 'narrowly ' : '';
    const targetCmp = cur.sales >= cur.budget ? `${closeness}above` : `${closeness}below`;
    s += `, ${targetCmp} the target of <b>${fmtM(cur.budget)}</b>, but clearly ${cur.sales >= prev.sales ? 'ahead of' : 'behind'} last year's <b>${fmtM(prev.sales)}</b>, reflecting ${cur.sales >= prev.sales ? 'a solid uplift' : 'a shortfall'} versus the prior year`;
  } else if (hasBudget) {
    s += `, ${cur.sales >= cur.budget ? 'above' : 'below'} the target of <b>${fmtM(cur.budget)}</b>`;
  } else if (hasPrev) {
    s += `, ${cur.sales >= prev.sales ? 'ahead of' : 'behind'} last year's <b>${fmtM(prev.sales)}</b>`;
  }
  return s;
}
function ytdQtySentence(yearLabel, cur, prev) {
  const hasBudget = cur.budgetQty > 0, hasPrev = !!prev;
  let s = `In terms of quantity, ${yearLabel} YTD sales total <b>${fmt(cur.qty)} units</b>`;
  if (hasBudget && hasPrev) {
    const targetCmp = cur.qty >= cur.budgetQty ? 'above the target of' : 'below the target of';
    const prevCmp = cur.qty >= prev.qty ? "above last year's" : "below last year's";
    const planWord = cur.qty >= cur.budgetQty ? 'ahead of plan' : 'behind plan';
    const yoyW = cur.qty >= prev.qty ? 'improving year on year' : 'declining year on year';
    s += `, which is ${targetCmp} <b>${fmt(cur.budgetQty)} units</b> and ${prevCmp} <b>${fmt(prev.qty)} units</b>, showing that overall unit performance is ${planWord} and ${yoyW}`;
  } else if (hasBudget) {
    s += `, ${cur.qty >= cur.budgetQty ? 'above' : 'below'} the target of <b>${fmt(cur.budgetQty)} units</b>`;
  } else if (hasPrev) {
    s += `, ${cur.qty >= prev.qty ? 'above' : 'below'} last year's <b>${fmt(prev.qty)} units</b>`;
  }
  return s;
}
function trendNarrativeHtml(nar, franchiseLabel) {
  if (!nar) return '<p>Not enough data to generate a summary for this selection.</p>';
  const fLabel = franchiseLabel === 'all' ? 'the selected franchises' : franchiseLabel;
  const monthLabel = `${nar.monthName} ${nar.year}`;
  const notice = nar.isPartialMonth
    ? `<p class="notice">Data for ${monthLabel} is only synced through <b>${new Date(nar.asOfDate).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}</b> — the sales figures below are month-to-date, compared against the same number of days last year, while the budget is the full-month target.</p>`
    : '';
  const p1 = monthValueSentence(monthLabel, fLabel, nar.month, nar.monthPrevYear) + ` ${cite(monthLabel + ' — bi_amount vs bi_budgetamount vs prior-year same period')}.`;
  const p2 = monthQtySentence(monthLabel, nar.month, nar.monthPrevYear) + ` ${cite(monthLabel + ' — bi_qty vs bi_budgetqty vs prior-year same period')}.`;
  const p3 = ytdValueSentence(nar.year, fLabel, nar.ytd, nar.ytdPrevYear) + ` ${cite(`${nar.year} YTD through ${nar.monthName} — bi_amount vs bi_budgetamount vs prior-year YTD`)}.`;
  const p4 = ytdQtySentence(nar.year, nar.ytd, nar.ytdPrevYear) + ` ${cite(`${nar.year} YTD through ${nar.monthName} — bi_qty vs bi_budgetqty vs prior-year YTD`)}.`;
  return `${notice}<p>${p1}</p><p>${p2}</p><h3>Year-to-date ${nar.year} performance</h3><p>${p3}</p><p>${p4}</p>`;
}

function categoryNarrativeSingle(data, dimLabel) {
  if (!data.length) return '<p>No data available for this selection.</p>';
  const total = data.reduce((s, d) => s + (d.sales || 0), 0);
  const top = data.reduce((a, b) => (b.sales || 0) > (a.sales || 0) ? b : a);
  let s = `<b>${top.label}</b> leads ${dimLabel} with sales of <b>${fmtM(top.sales)}</b>, accounting for <b>${fmtShare(top.sales, total)}</b> of the total shown`;
  if (data.length > 1) {
    const low = data.reduce((a, b) => (b.sales || 0) < (a.sales || 0) ? b : a);
    s += `, while <b>${low.label}</b> trails at <b>${fmtM(low.sales)}</b>`;
  }
  s += ` ${cite(`${dimLabel} breakdown by sales amount`)}.`;
  return `<p>${s}</p>`;
}
// Target / This Year / Last Year variant — used once a single month has a
// prior-year figure to compare against (see hasPrevYear in load()).
function categoryNarrativeSingle3(data, dimLabel, isPartialMonth) {
  if (!data.length) return '<p>No data available for this selection.</p>';
  const total = data.reduce((s, d) => s + (d.sales || 0), 0);
  const top = data.reduce((a, b) => (b.sales || 0) > (a.sales || 0) ? b : a);
  const achv = top.budget > 0 ? (top.sales / top.budget * 100) : null;
  const yoy = fmtYoy(top.prevYearSales, top.sales);
  const targetWord = isPartialMonth ? 'full-month target' : 'target';
  const lastYearPhrase = isPartialMonth
    ? `the same days last year (<b>${fmtM(top.prevYearSales)}</b>)`
    : `last year's <b>${fmtM(top.prevYearSales)}</b>`;
  let s = `<b>${top.label}</b> leads ${dimLabel} with sales of <b>${fmtM(top.sales)}</b>, accounting for <b>${fmtShare(top.sales, total)}</b> of the total shown`;
  if (achv != null) s += `, ${achv >= 100 ? 'ahead of' : 'behind'} its ${targetWord} of <b>${fmtM(top.budget)}</b>`;
  if (yoy != null) s += `, and ${yoyWord(yoy, 'up', 'down')} <b>${Math.abs(yoy).toFixed(0)}%</b> versus ${lastYearPhrase}`;
  if (data.length > 1) {
    const low = data.reduce((a, b) => (b.sales || 0) < (a.sales || 0) ? b : a);
    s += `, while <b>${low.label}</b> trails at <b>${fmtM(low.sales)}</b>`;
  }
  s += ` ${cite(`${dimLabel} breakdown — sales vs target vs prior-year same period`)}.`;
  return `<p>${s}</p>`;
}
function categoryNarrativeCompare(data, dimLabel) {
  if (!data.length) return '<p>No data available for this selection.</p>';
  const top25 = data.reduce((a, b) => (b.y2025 || 0) > (a.y2025 || 0) ? b : a);
  let s = `<b>${top25.label}</b> leads ${dimLabel} in 2025 with sales of <b>${fmtM(top25.y2025)}</b>`;
  const withYoy = data.map(d => ({ ...d, yoy: fmtYoy(d.y2024, d.y2025) })).filter(d => d.yoy != null);
  if (withYoy.length) {
    const grower = withYoy.reduce((a, b) => b.yoy > a.yoy ? b : a);
    s += `, and <b>${grower.label}</b> grew the most year-over-year at ${yoyHtml(grower.yoy)}`;
  }
  s += ` ${cite(`${dimLabel} 2024 vs 2025 sales amount`)}.`;
  return `<p>${s}</p>`;
}

function productNarrativeSingle(data) {
  if (!data.length) return '<p>No data available for this selection.</p>';
  const total = data.reduce((s, d) => s + (d.value || 0), 0);
  const top = data[0];
  const s = `<b>${top.label}</b> is the top-selling product group at <b>${fmtM(top.value)}</b>, representing <b>${fmtShare(top.value, total)}</b> of sales across the top ${data.length} groups shown ${cite('Top product groups by sales amount')}.`;
  return `<p>${s}</p>`;
}
function productNarrativeSingle3(data, isPartialMonth) {
  if (!data.length) return '<p>No data available for this selection.</p>';
  const total = data.reduce((s, d) => s + (d.value || 0), 0);
  const top = data[0];
  const achv = top.budget > 0 ? (top.value / top.budget * 100) : null;
  const yoy = fmtYoy(top.prevYearSales, top.value);
  const targetWord = isPartialMonth ? 'full-month target' : 'target';
  const lastYearPhrase = isPartialMonth
    ? `the same days last year (<b>${fmtM(top.prevYearSales)}</b>)`
    : `last year's <b>${fmtM(top.prevYearSales)}</b>`;
  let s = `<b>${top.label}</b> is the top-selling product group at <b>${fmtM(top.value)}</b>, representing <b>${fmtShare(top.value, total)}</b> of sales across the top ${data.length} groups shown`;
  if (achv != null) s += `, ${achv >= 100 ? 'ahead of' : 'behind'} its ${targetWord} of <b>${fmtM(top.budget)}</b>`;
  if (yoy != null) s += `, and ${yoyWord(yoy, 'up', 'down')} <b>${Math.abs(yoy).toFixed(0)}%</b> versus ${lastYearPhrase}`;
  s += ` ${cite('Top product groups — sales vs target vs prior-year same period')}.`;
  return `<p>${s}</p>`;
}
function productNarrativeCompare(data) {
  if (!data.length) return '<p>No data available for this selection.</p>';
  const top = data[0];
  const yoy = fmtYoy(top.y2024, top.y2025);
  const yoyPhrase = yoy == null ? 'with no comparable 2024 figure' : `${yoyWord(yoy, 'up', 'down')} <b>${Math.abs(yoy).toFixed(0)}%</b> year-over-year`;
  const s = `<b>${top.label}</b> remains the top-selling product group in 2025 at <b>${fmtM(top.y2025)}</b>, ${yoyPhrase} ${cite('Top product group, 2024 vs 2025 sales amount')}.`;
  return `<p>${s}</p>`;
}

function salesmanNarrativeSingle(data) {
  if (!data.length) return '<p>No data available for this selection.</p>';
  const top = data.reduce((a, b) => (b.sales || 0) > (a.sales || 0) ? b : a);
  const achvs = data.map(s => s.budget > 0 ? s.sales / s.budget * 100 : null).filter(v => v != null);
  const avg = achvs.length ? achvs.reduce((a, b) => a + b, 0) / achvs.length : null;
  let s = `<b>${top.label}</b> is the top performer with sales of <b>${fmtM(top.sales)}</b>`;
  if (avg != null) s += `, and the group is averaging <b>${avg.toFixed(0)}%</b> achievement against budget`;
  s += ` ${cite('Top 10 salesmen by sales amount')}.`;
  return `<p>${s}</p>`;
}
function salesmanNarrativeSingle3(data, isPartialMonth) {
  if (!data.length) return '<p>No data available for this selection.</p>';
  const top = data.reduce((a, b) => (b.sales || 0) > (a.sales || 0) ? b : a);
  const achvs = data.map(s => s.budget > 0 ? s.sales / s.budget * 100 : null).filter(v => v != null);
  const avgAchv = achvs.length ? achvs.reduce((a, b) => a + b, 0) / achvs.length : null;
  const yoys = data.map(s => fmtYoy(s.prevYearSales, s.sales)).filter(v => v != null);
  const avgYoy = yoys.length ? yoys.reduce((a, b) => a + b, 0) / yoys.length : null;
  const targetWord = isPartialMonth ? 'full-month target' : 'target';
  const lastYearWord = isPartialMonth ? 'the same days last year' : 'last year';
  let s = `<b>${top.label}</b> is the top performer with sales of <b>${fmtM(top.sales)}</b>`;
  if (avgAchv != null) s += `, and the group is averaging <b>${avgAchv.toFixed(0)}%</b> achievement against ${targetWord}`;
  if (avgYoy != null) s += `, ${yoyWord(avgYoy, 'up', 'down')} <b>${Math.abs(avgYoy).toFixed(0)}%</b> versus ${lastYearWord} on average`;
  s += ` ${cite('Top 10 salesmen — sales vs target vs prior-year same period')}.`;
  return `<p>${s}</p>`;
}
function salesmanNarrativeCompare(data) {
  if (!data.length) return '<p>No data available for this selection.</p>';
  const top = data.reduce((a, b) => (b.y2025 || 0) > (a.y2025 || 0) ? b : a);
  const yoys = data.map(s => fmtYoy(s.y2024, s.y2025)).filter(v => v != null);
  const avg = yoys.length ? yoys.reduce((a, b) => a + b, 0) / yoys.length : null;
  let s = `<b>${top.label}</b> leads in 2025 with sales of <b>${fmtM(top.y2025)}</b>`;
  if (avg != null) s += `, with the group averaging ${yoyHtml(avg)} year-over-year`;
  s += ` ${cite('Top 10 salesmen, 2024 vs 2025 sales amount')}.`;
  return `<p>${s}</p>`;
}

// ---------------------------------------------------------------------
// KPI + salesman table renderers
// ---------------------------------------------------------------------
function renderKpisSingle(el, k, monthInfo) {
  const partial = !!k.isPartialMonth;
  const achv = k.budget > 0 ? (k.sales / k.budget * 100) : null;
  const tiles = [];

  if (monthInfo) {
    // Requested order: Target -> This Year -> Last Year, each tagged with
    // the exact month/year it covers so the tile is unambiguous on its own.
    const { monthName, year } = monthInfo;
    tiles.push(
      { label: 'Target', value: fmtM(k.budget), sub: `${monthName} ${year}${partial ? ' · full month' : ''}` },
      { label: 'This Year', value: fmtM(k.sales), sub: `${monthName} ${year}${partial ? ' · month-to-date' : ''}` },
    );
    if (k.prevYearSales != null) {
      tiles.push({
        label: 'Last Year',
        value: fmtM(k.prevYearSales),
        sub: `${monthName} ${year - 1}${partial ? ' · same days' : ''} — ${yoyHtml(fmtYoy(k.prevYearSales, k.sales))}`,
      });
    }
  } else {
    tiles.push(
      { label: 'Total Sales Amount', value: fmtM(k.sales), sub: null },
      { label: 'Total Budget Amount', value: fmtM(k.budget), sub: null },
    );
  }

  tiles.push(
    { label: 'Achievement', value: achv == null ? '–' : achv.toFixed(1) + '%', sub: achv == null ? 'no budget data' : ('<span class="' + (achv >= 100 ? 'good' : 'bad') + '">vs ' + (partial ? 'full-month budget' : 'budget') + '</span>') },
    { label: 'Total Qty Sold', value: fmt(k.qty), sub: 'budget ' + fmt(k.budgetQty) },
    { label: 'Active Customers', value: fmt(k.customers), sub: 'distinct bi_cstno' },
  );

  el.classList.remove('compare');
  el.classList.toggle('six', tiles.length === 6);
  const notice = partial
    ? `<div class="pbi-kpi-notice">Data is only synced through <b>${new Date(k.asOfDate).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</b> for this month — sales figures above are month-to-date, while the budget is the full-month target.</div>`
    : '';
  el.innerHTML = notice + tiles.map(t => `
    <div class="pbi-kpi">
      <div class="label">${t.label}</div>
      <div class="value">${t.value}</div>
      ${t.sub ? `<div class="sub">${t.sub}</div>` : ''}
    </div>
  `).join('');
}
function renderKpisCompare(el, k24, k25) {
  const delta = (a, b) => (a > 0) ? ((b - a) / a * 100) : null;
  const achv25 = k25.budget > 0 ? (k25.sales / k25.budget * 100) : null;
  const tiles = [
    { label: 'Sales Amount (2025)', value: fmtM(k25.sales), sub: fmtDelta(delta(k24.sales, k25.sales)) + ' vs 2024' },
    { label: 'Budget Amount (2025)', value: fmtM(k25.budget), sub: fmtDelta(delta(k24.budget, k25.budget)) + ' vs 2024' },
    { label: 'Achievement (2025)', value: achv25 == null ? '–' : achv25.toFixed(1) + '%', sub: '<span class="' + (achv25 >= 100 ? 'good' : 'bad') + '">vs 2025 budget</span>' },
    { label: 'Active Customers (2025)', value: fmt(k25.customers), sub: fmtDelta(delta(k24.customers, k25.customers)) + ' vs 2024' },
  ];
  el.classList.add('compare');
  el.innerHTML = tiles.map(t => `
    <div class="pbi-kpi">
      <div class="label">${t.label}</div>
      <div class="value">${t.value}</div>
      <div class="sub">${t.sub}</div>
    </div>
  `).join('');
}

function renderSalesmanSingleTable(el, data, monthMode, hasPrevYear, isPartialMonth) {
  const maxVal = Math.max(1, ...data.flatMap(s => [s.sales || 0, s.budget || 0]));
  const salesLabel = monthMode ? (isPartialMonth ? 'This Year (MTD)' : 'This Year') : 'Sales Amount';
  const budgetLabel = monthMode ? (isPartialMonth ? 'Target (Full Month)' : 'Target') : 'Budget Amount';
  const lastYearLabel = isPartialMonth ? 'Last Year (Same Days)' : 'Last Year';
  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Salesman</th><th class="num">${budgetLabel}</th><th class="num">${salesLabel}</th>
        ${hasPrevYear ? `<th class="num">${lastYearLabel}</th><th class="num">YoY %</th>` : '<th class="num">Achv %</th>'}
        <th style="width:160px">Sales</th>
      </tr></thead>
      <tbody>
        ${data.map(s => {
          const achv = s.budget > 0 ? (s.sales / s.budget * 100) : null;
          const achvClass = achv == null ? '' : (achv >= 100 ? 'achv-good' : 'achv-bad');
          const pct = ((s.sales || 0) / maxVal * 100).toFixed(1);
          return `<tr>
            <td>${s.label}</td>
            <td class="num">${fmt(s.budget)}</td>
            <td class="num">${fmt(s.sales)}</td>
            ${hasPrevYear
              ? `<td class="num">${fmt(s.prevYearSales)}</td><td class="num">${yoyHtml(fmtYoy(s.prevYearSales, s.sales))}</td>`
              : `<td class="num ${achvClass}">${achv == null ? '–' : achv.toFixed(0) + '%'}</td>`}
            <td><div class="bar-cell"><div class="mini-bar"><span style="width:${pct}%;background:var(--series-1)"></span></div></div></td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}
function renderSalesmanCompareTable(el, data) {
  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Salesman</th><th class="num">Budget 2025</th><th class="num">Sales 2025</th><th class="num">Sales 2024</th><th class="num">YoY %</th>
      </tr></thead>
      <tbody>
        ${data.map(s => {
          const yoy = s.y2024 > 0 ? ((s.y2025 - s.y2024) / s.y2024 * 100) : null;
          const cls = yoy == null ? '' : (yoy >= 0 ? 'achv-good' : 'achv-bad');
          return `<tr>
            <td>${s.label}</td>
            <td class="num">${fmt(s.budget2025)}</td>
            <td class="num">${fmt(s.y2025)}</td>
            <td class="num">${fmt(s.y2024)}</td>
            <td class="num ${cls}">${yoy == null ? '–' : (yoy >= 0 ? '+' : '') + yoy.toFixed(0) + '%'}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

const MONTH_NAMES_FULL = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_VALUE_RE = /^(\d{4})-(\d{2})$/;

// Data spans Jan 2023 - Oct 2025 (see header), but the Period filter only
// offers the current and previous year — build one "Month Year" entry per
// month across those two years, most recent first.
const DATA_MAX_YEAR = 2025;
const DATA_MAX_MONTH = 10;
function buildYearOptions() {
  const months = [];
  for (let y = DATA_MAX_YEAR - 1; y <= DATA_MAX_YEAR; y++) {
    const lastMonth = y === DATA_MAX_YEAR ? DATA_MAX_MONTH : 12;
    for (let m = 1; m <= lastMonth; m++) {
      months.push({ v: `${y}-${String(m).padStart(2, '0')}`, l: `${MONTH_ABBR[m - 1]} ${y}` });
    }
  }
  months.reverse();
  return months;
}
const YEAR_OPTIONS = buildYearOptions();
const FRANCHISE_OPTIONS = [
  { v: 'all', l: 'All' }, { v: 'Midea', l: 'Midea' }, { v: 'BEKO', l: 'BEKO' }, { v: 'CANDY', l: 'CANDY' },
];
const CUSTOMER_TYPE_OPTIONS = [
  { v: 'all', l: 'All' }, { v: 'Dealers', l: 'Dealers' }, { v: 'Whole Sale', l: 'Whole Sale' },
  { v: 'Modern Trade', l: 'Modern Trade' }, { v: 'Projects', l: 'Projects' }, { v: 'Others', l: 'Others' },
];
// v matches bi_cstregiondesc's exact stored value; l is the friendlier label shown in the dropdown.
const REGION_OPTIONS = [
  { v: 'all', l: 'All' }, { v: 'CENTRAL REGION', l: 'Central' },
  { v: 'EASTERN REGION', l: 'Eastern' }, { v: 'WESTERN REGION', l: 'Western' },
];

export class PbiSalesDashboard extends Component {
  static template = "pbi_dashboards.sales_dashboard";
  static props = ["*"];

  setup() {
    this.rpc = useService("rpc");
    this.yearOptions = YEAR_OPTIONS;
    this.franchiseOptions = FRANCHISE_OPTIONS;
    this.customerTypeOptions = CUSTOMER_TYPE_OPTIONS;
    this.regionOptions = REGION_OPTIONS;
    this.state = useState({
      year: YEAR_OPTIONS[0].v, franchise: 'Midea', customerType: 'all', region: 'all', loading: false, error: '',
      drillLevel: 'region', drillRegion: null, drillCity: null,
    });

    this.rootRef = useRef('root');
    this.refs = {
      kpiRow: useRef('kpiRow'),
      trendTitle: useRef('trendTitle'), trendSubtitle: useRef('trendSubtitle'),
      trendLegend: useRef('trendLegend'), trendChart: useRef('trendChart'), trendNotes: useRef('trendNotes'),
      regionTitle: useRef('regionTitle'), regionSubtitle: useRef('regionSubtitle'), regionBreadcrumb: useRef('regionBreadcrumb'),
      regionLegend: useRef('regionLegend'), regionChart: useRef('regionChart'), regionNotes: useRef('regionNotes'),
      franchiseTitle: useRef('franchiseTitle'), franchiseSubtitle: useRef('franchiseSubtitle'),
      franchiseLegend: useRef('franchiseLegend'), franchiseChart: useRef('franchiseChart'), franchiseNotes: useRef('franchiseNotes'),
      customerTypeTitle: useRef('customerTypeTitle'), customerTypeSubtitle: useRef('customerTypeSubtitle'),
      customerTypeLegend: useRef('customerTypeLegend'), customerTypeChart: useRef('customerTypeChart'), customerTypeNotes: useRef('customerTypeNotes'),
      productTitle: useRef('productTitle'), productSubtitle: useRef('productSubtitle'),
      productLegend: useRef('productLegend'), productChart: useRef('productChart'), productNotes: useRef('productNotes'),
      salesmanTitle: useRef('salesmanTitle'), salesmanSubtitle: useRef('salesmanSubtitle'),
      salesmanTable: useRef('salesmanTable'), salesmanNotes: useRef('salesmanNotes'),
      tooltip: useRef('tooltip'),
      importNotesInput: useRef('importNotesInput'),
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

  selectYear(v) { this.state.year = v; this.resetDrill(); this.load(); }
  selectFranchise(v) { this.state.franchise = v; this.resetDrill(); this.load(); }
  selectCustomerType(v) { this.state.customerType = v; this.resetDrill(); this.load(); }
  selectRegion(v) { this.state.region = v; this.resetDrill(); this.load(); }

  exportPdf() {
    window.print();
  }

  exportPptx() {
    const params = new URLSearchParams({
      year: this.state.year, franchise: this.state.franchise,
      customerType: this.state.customerType, region: this.state.region,
    });
    window.open(`/pbi_dashboards/sales/export.pptx?${params}`, '_blank');
  }

  async importNotes(ev) {
    const file = ev.target.files && ev.target.files[0];
    ev.target.value = '';
    if (!file) return;
    this.state.loading = true;
    try {
      const fd = new FormData();
      fd.append('file', file);
      // Sent as a fallback only — the server trusts the period/franchise/
      // customerType/region embedded in the file itself (set at export time)
      // over these, since the user may have switched screens between
      // exporting and importing.
      fd.append('year', this.state.year);
      fd.append('franchise', this.state.franchise);
      fd.append('customerType', this.state.customerType);
      fd.append('region', this.state.region);
      fd.append('csrf_token', odoo.csrf_token);
      const response = await fetch('/pbi_dashboards/sales/import_notes', { method: 'POST', body: fd });
      const json = await response.json();
      if (json.error) { this.state.error = json.error; return; }
      if (!Object.keys(json.notes).length) {
        this.state.error = "No edited narrative notes were found — the file's speaker notes matched the dashboard's current text.";
        return;
      }
      this.state.error = '';
      // The import may have applied to a different period/franchise/
      // customerType/region than what's currently on screen — switch to it
      // so the edit is visible.
      this.state.year = json.year;
      this.state.franchise = json.franchise;
      this.state.customerType = json.customerType;
      this.state.region = json.region;
      this.resetDrill();
      await this.load();
    } catch (e) {
      this.state.error = 'Failed to import notes — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  resetDrill() {
    this.state.drillLevel = 'region';
    this.state.drillRegion = null;
    this.state.drillCity = null;
  }

  drillDown(label) {
    if (this.state.drillLevel === 'region') {
      this.state.drillRegion = label;
      this.state.drillLevel = 'city';
    } else if (this.state.drillLevel === 'city') {
      this.state.drillCity = label;
      this.state.drillLevel = 'salesman';
    } else {
      return; // salesman is the leaf level
    }
    this.updateRegionSection();
  }

  drillTo(level) {
    if (level === 'region') {
      this.state.drillLevel = 'region';
      this.state.drillRegion = null;
      this.state.drillCity = null;
    } else if (level === 'city') {
      this.state.drillLevel = 'city';
      this.state.drillCity = null;
    } else {
      return;
    }
    this.updateRegionSection();
  }

  renderRegionBreadcrumb() {
    const parts = [{ label: 'All Regions', level: 'region' }];
    if (this.state.drillRegion) parts.push({ label: this.state.drillRegion, level: 'city' });
    if (this.state.drillCity) parts.push({ label: this.state.drillCity, level: 'salesman' });
    const el = this.refs.regionBreadcrumb.el;
    if (parts.length === 1) { el.innerHTML = ''; return; }
    el.innerHTML = parts.map((p, i) => {
      if (i === parts.length - 1) return `<span class="crumb current">${p.label}</span>`;
      return `<span class="crumb" data-level="${p.level}">${p.label}</span><span class="crumb-sep">›</span>`;
    }).join('');
    el.querySelectorAll('.crumb[data-level]').forEach(elm => {
      elm.addEventListener('click', () => this.drillTo(elm.getAttribute('data-level')));
    });
  }

  attachRegionDrillClicks() {
    if (this.state.drillLevel === 'salesman') return; // leaf level, nothing further to drill into
    this.refs.regionChart.el.querySelectorAll('rect[data-tip]').forEach(rect => {
      rect.style.cursor = 'pointer';
      rect.addEventListener('click', () => {
        const label = rect.getAttribute('data-tip').split('||')[0];
        this.drillDown(label);
      });
    });
  }

  async updateRegionSection() {
    const r = this.refs;
    const { c1, c2, c3 } = this.seriesColors();
    const cmpMode = this.state.year === 'compare';
    const level = this.state.drillLevel;
    let data, dimLabel, levelWord, suffix = '';

    if (level === 'region') {
      data = this.lastJson.region;
      dimLabel = 'regions';
      levelWord = 'Region';
    } else if (level === 'city') {
      const res = await this.rpc('/pbi_dashboards/sales/region_drill', {
        year: this.state.year, franchise: this.state.franchise,
        customerType: this.state.customerType, region: this.state.region,
        level: 'city', drillRegion: this.state.drillRegion,
      });
      if (res.error) { this.state.error = res.error; return; }
      data = res.data;
      dimLabel = `cities in ${this.state.drillRegion}`;
      levelWord = 'City';
      suffix = ` — ${this.state.drillRegion}`;
    } else {
      const res = await this.rpc('/pbi_dashboards/sales/region_drill', {
        year: this.state.year, franchise: this.state.franchise,
        customerType: this.state.customerType, region: this.state.region,
        level: 'salesman', drillRegion: this.state.drillRegion, drillCity: this.state.drillCity,
      });
      if (res.error) { this.state.error = res.error; return; }
      data = res.data;
      dimLabel = `salesmen in ${this.state.drillRegion} / ${this.state.drillCity}`;
      levelWord = 'Salesman';
      suffix = ` — ${this.state.drillRegion} / ${this.state.drillCity}`;
    }

    const hasPrevYear = !cmpMode && this.hasPrevYear;
    const isPartialMonth = hasPrevYear && this.isPartialMonth;
    // Budget rows carry no warehouse name, so "City" has no real target in
    // the source data — the backend instead estimates one by splitting the
    // parent region's real target across cities by sales share.
    const budgetEstimated = level === 'city';
    const targetLabel = budgetEstimated ? 'Estimated Target' : (isPartialMonth ? 'Target (Full Month)' : 'Target');
    const thisYearLabel = isPartialMonth ? 'This Year (MTD)' : 'This Year';
    const lastYearLabel = isPartialMonth ? 'Last Year (Same Days)' : 'Last Year';
    const estimatedNote = ' (target estimated: region budget split by city sales share)';
    const suffixParts = [];
    if (suffix) suffixParts.push(suffix.replace(/^ — /, ''));
    if (!cmpMode && this.periodLabel) suffixParts.push(this.periodLabel);
    const combinedSuffix = suffixParts.length ? ` — ${suffixParts.join(', ')}` : '';
    r.regionTitle.el.textContent = cmpMode
      ? `Sales by ${levelWord} — 2024 vs 2025${suffix}`
      : `Sales by ${levelWord}${combinedSuffix}`;
    r.regionSubtitle.el.textContent = (level === 'region' ? 'Click a bar to drill down' : 'Click a bar to drill down further')
      + (cmpMode
          ? (budgetEstimated ? ', with estimated 2025 target' : ', with 2025 budget')
          : hasPrevYear
            ? (isPartialMonth ? ', target (full month) vs this year (MTD) vs last year' : ', target vs this year vs last year') + (budgetEstimated ? estimatedNote : '')
            : ', amount vs budget' + (budgetEstimated ? estimatedNote : ''));

    this.renderRegionBreadcrumb();

    const chartFn = level === 'salesman' ? hGroupedBarChart : groupedBarChart;
    // Salesman is the leaf level — nothing further to drill into, so only
    // wire up the category-label click for region/city charts. A short bar
    // (e.g. a small city) is hard to click directly, so the label is a
    // second, always-clickable target for the same drill-down.
    const chartOpts = level === 'salesman' ? {} : { onLabelClick: (label) => this.drillDown(label) };
    // The exported PowerPoint only carries a top-level "Sales by Region"
    // slide, so an imported note override only applies at that level — once
    // drilled into a city or salesman, fall back to the auto-generated text.
    const regionOverride = level === 'region' ? (this.lastJson.notes || {}).region : null;
    if (cmpMode) {
      const cmpTargetLabel = budgetEstimated ? '2025 Est. Target' : '2025 Budget';
      r.regionLegend.el.innerHTML = legendHtml([cmpTargetLabel, '2025 Sales', '2024 Sales'], [c3, c2, c1]);
      chartFn(r.regionChart.el, data, ['budget2025', 'y2025', 'y2024'], [c3, c2, c1], [cmpTargetLabel, '2025 Sales', '2024 Sales'], chartOpts);
      r.regionNotes.el.innerHTML = regionOverride ? noteOverrideHtml(regionOverride) : categoryNarrativeCompare(data, dimLabel);
    } else if (hasPrevYear) {
      r.regionLegend.el.innerHTML = legendHtml([targetLabel, thisYearLabel, lastYearLabel], [c3, c2, c1]);
      chartFn(r.regionChart.el, data, ['budget', 'sales', 'prevYearSales'], [c3, c2, c1], [targetLabel, thisYearLabel, lastYearLabel], chartOpts);
      r.regionNotes.el.innerHTML = regionOverride ? noteOverrideHtml(regionOverride) : categoryNarrativeSingle3(data, dimLabel, isPartialMonth);
    } else {
      r.regionLegend.el.innerHTML = legendHtml(['Sales', targetLabel], [c1, c2]);
      chartFn(r.regionChart.el, data, ['sales', 'budget'], [c1, c2], ['Sales', targetLabel], chartOpts);
      r.regionNotes.el.innerHTML = regionOverride ? noteOverrideHtml(regionOverride) : categoryNarrativeSingle(data, dimLabel);
    }
    this.attachRegionDrillClicks();
  }

  seriesColors() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    return {
      c1: style.getPropertyValue('--series-1').trim() || '#2a78d6',
      c2: style.getPropertyValue('--series-2').trim() || '#1baf7a',
      c3: style.getPropertyValue('--series-3').trim() || '#eda100',
      c5: style.getPropertyValue('--series-5').trim() || '#4a3aa7',
    };
  }

  setMode(mode, yearLabel, hasPrevYear, isPartialMonth, periodLabel) {
    const { c1, c2, c3 } = this.seriesColors();
    const r = this.refs;

    if (mode === 'compare') {
      const cmpLabels = ['2025 Budget', '2025 Sales', '2024 Sales'];
      const cmpColors = [c3, c2, c1];

      r.trendTitle.el.textContent = 'Monthly Sales — 2024 vs 2025 (with 2025 Budget)';
      r.trendSubtitle.el.textContent = 'Sales amount by month';
      r.trendLegend.el.innerHTML = legendHtml(cmpLabels, cmpColors);

      r.regionLegend.el.innerHTML = legendHtml(cmpLabels, cmpColors);

      r.franchiseTitle.el.textContent = 'Sales by Franchise — 2024 vs 2025';
      r.franchiseSubtitle.el.textContent = 'Sales amount, with 2025 budget';
      r.franchiseLegend.el.innerHTML = legendHtml(cmpLabels, cmpColors);

      r.customerTypeTitle.el.textContent = 'Sales by Customer Type — 2024 vs 2025';
      r.customerTypeSubtitle.el.textContent = 'Sales amount, with 2025 budget';
      r.customerTypeLegend.el.innerHTML = legendHtml(cmpLabels, cmpColors);

      r.productTitle.el.textContent = 'Top Product Groups — 2024 vs 2025';
      r.productSubtitle.el.textContent = 'Sales amount, top 10, with 2025 budget';
      r.productLegend.el.innerHTML = legendHtml(cmpLabels, cmpColors);

      r.salesmanTitle.el.textContent = 'Top 10 Salesmen — 2024 vs 2025';
      r.salesmanSubtitle.el.textContent = 'Sales amount, with 2025 budget, year-over-year';
    } else {
      // When the month is still syncing in, tag every "Target"/"This Year"/
      // "Last Year" label with what it actually covers — otherwise a full-
      // month budget dwarfing a few days of actuals reads as a bug rather
      // than the expected month-to-date effect (see the KPI row notice).
      const targetLabel = isPartialMonth ? 'Target (Full Month)' : 'Target';
      const thisYearLabel = isPartialMonth ? 'This Year (MTD)' : 'This Year';
      const lastYearLabel = isPartialMonth ? 'Last Year (Same Days)' : 'Last Year';
      const dimLabels = hasPrevYear ? [targetLabel, thisYearLabel, lastYearLabel] : ['Sales', 'Budget'];
      const dimColors = hasPrevYear ? [c3, c2, c1] : [c1, c2];
      const cmp3 = hasPrevYear ? (isPartialMonth ? ', target (full month) vs this year (MTD) vs last year' : ', vs target and last year') : '';
      const suffix = periodLabel ? ` — ${periodLabel}` : '';

      r.trendTitle.el.textContent = 'Monthly Sales vs Budget' + suffix;
      r.trendSubtitle.el.textContent = `Amount by month${yearLabel ? ', ' + yearLabel : ''}`;
      r.trendLegend.el.innerHTML = legendHtml(hasPrevYear ? [thisYearLabel, targetLabel, lastYearLabel] : ['Sales Amount', 'Budget Amount'], hasPrevYear ? [c2, c3, c1] : [c1, c2]);

      r.regionLegend.el.innerHTML = legendHtml(dimLabels, dimColors);

      r.franchiseTitle.el.textContent = 'Sales by Franchise' + suffix;
      r.franchiseSubtitle.el.textContent = 'Amount vs budget' + cmp3;
      r.franchiseLegend.el.innerHTML = legendHtml(dimLabels, dimColors);

      r.customerTypeTitle.el.textContent = 'Sales by Customer Type' + suffix;
      r.customerTypeSubtitle.el.textContent = 'Amount vs budget' + cmp3;
      r.customerTypeLegend.el.innerHTML = legendHtml(dimLabels, dimColors);

      r.productTitle.el.textContent = 'Top Product Groups' + suffix;
      r.productSubtitle.el.textContent = 'By sales amount, top 10' + cmp3;
      r.productLegend.el.innerHTML = legendHtml(dimLabels, dimColors);

      r.salesmanTitle.el.textContent = 'Top 10 Salesmen' + suffix;
      r.salesmanSubtitle.el.textContent = hasPrevYear
        ? (isPartialMonth ? 'Target (full month) vs this year (MTD) vs last year' : 'Target vs this year vs last year')
        : 'Sales vs budget, achievement %';
    }
  }

  // Sets the 5 top-level narrative panels (trend/franchise/customerType/
  // product/salesman — region is handled separately in updateRegionSection
  // since it also depends on drill level). Shared by load() and by
  // importNotes(), which re-renders in place without a data refetch.
  renderNarratives(json) {
    const r = this.refs;
    const notes = json.notes || {};
    const put = (ref, key, html) => { ref.el.innerHTML = notes[key] ? noteOverrideHtml(notes[key]) : html; };
    if (this.state.year === 'compare') {
      put(r.trendNotes, 'trend', trendNarrativeHtml(json.narrative, this.state.franchise));
      put(r.franchiseNotes, 'franchise', categoryNarrativeCompare(json.franchise, 'franchises'));
      put(r.customerTypeNotes, 'customerType', categoryNarrativeCompare(json.customerType, 'customer types'));
      put(r.productNotes, 'product', productNarrativeCompare(json.product));
      put(r.salesmanNotes, 'salesman', salesmanNarrativeCompare(json.salesman));
    } else {
      const hasPrevYear = json.kpis.prevYearSales != null;
      const isPartialMonth = !!json.kpis.isPartialMonth;
      put(r.trendNotes, 'trend', trendNarrativeHtml(json.narrative, this.state.franchise));
      put(r.franchiseNotes, 'franchise', hasPrevYear
        ? categoryNarrativeSingle3(json.franchise, 'franchises', isPartialMonth)
        : categoryNarrativeSingle(json.franchise, 'franchises'));
      put(r.customerTypeNotes, 'customerType', hasPrevYear
        ? categoryNarrativeSingle3(json.customerType, 'customer types', isPartialMonth)
        : categoryNarrativeSingle(json.customerType, 'customer types'));
      put(r.productNotes, 'product', hasPrevYear
        ? productNarrativeSingle3(json.product, isPartialMonth)
        : productNarrativeSingle(json.product));
      put(r.salesmanNotes, 'salesman', hasPrevYear
        ? salesmanNarrativeSingle3(json.salesman, isPartialMonth)
        : salesmanNarrativeSingle(json.salesman));
    }
  }

  async load() {
    this.state.loading = true;
    const r = this.refs;
    try {
      const json = await this.rpc('/pbi_dashboards/sales/data', {
        year: this.state.year, franchise: this.state.franchise,
        customerType: this.state.customerType, region: this.state.region,
      });
      if (json.error) throw new Error(json.error);
      this.state.error = '';

      const { c1, c2, c3, c5 } = this.seriesColors();
      citeSeq = 0;

      this.lastJson = json;

      if (this.state.year === 'compare') {
        this.hasPrevYear = false;
        this.periodLabel = null;
        this.setMode('compare');
        renderKpisCompare(r.kpiRow.el, json.kpis2024, json.kpis2025);
        const cmpKeys = ['budget2025', 'y2025', 'y2024'];
        const cmpColors = [c3, c2, c1];
        const cmpLabels = ['2025 Budget', '2025 Sales', '2024 Sales'];
        lineChart(r.trendChart.el, json.trend, cmpKeys, cmpColors, cmpLabels);
        groupedBarChart(r.franchiseChart.el, json.franchise, cmpKeys, cmpColors, cmpLabels);
        groupedBarChart(r.customerTypeChart.el, json.customerType, cmpKeys, cmpColors, cmpLabels);
        hGroupedBarChart(r.productChart.el, json.product, cmpKeys, cmpColors, cmpLabels);
        renderSalesmanCompareTable(r.salesmanTable.el, json.salesman);

        this.renderNarratives(json);
      } else {
        const monthMatch = MONTH_VALUE_RE.exec(this.state.year);
        let yearLabel;
        if (this.state.year === 'all') yearLabel = '2023–2025';
        else if (monthMatch) yearLabel = `${monthMatch[1]} — ${MONTH_ABBR[parseInt(monthMatch[2], 10) - 1]} highlighted`;
        else yearLabel = this.state.year;
        const hasPrevYear = json.kpis.prevYearSales != null;
        const isPartialMonth = !!json.kpis.isPartialMonth;
        const monthInfo = monthMatch
          ? { monthName: MONTH_NAMES_FULL[parseInt(monthMatch[2], 10) - 1], year: parseInt(monthMatch[1], 10) }
          : null;
        const periodLabel = monthMatch ? `${MONTH_ABBR[parseInt(monthMatch[2], 10) - 1]} ${monthMatch[1]}` : (this.state.year === 'all' ? '2023–2025' : null);
        this.hasPrevYear = hasPrevYear;
        this.isPartialMonth = isPartialMonth;
        this.periodLabel = periodLabel;
        this.setMode('single', yearLabel, hasPrevYear, isPartialMonth, periodLabel);
        renderKpisSingle(r.kpiRow.el, json.kpis, monthInfo);
        const trendData = this.state.year === 'all' ? json.monthly
          : json.monthly.map(d => ({ ...d, label: MONTH_ABBR[parseInt(d.label.split('-')[1], 10) - 1] }));
        const highlightIndex = monthMatch
          ? trendData.findIndex(d => d.label === MONTH_ABBR[parseInt(monthMatch[2], 10) - 1])
          : null;
        const targetLabel = isPartialMonth ? 'Target (Full Month)' : 'Target';
        const thisYearLabel = isPartialMonth ? 'This Year (MTD)' : 'This Year';
        const lastYearLabel = isPartialMonth ? 'Last Year (Same Days)' : 'Last Year';
        const dimKeys = hasPrevYear ? ['budget', 'sales', 'prevYearSales'] : ['sales', 'budget'];
        const dimColors = hasPrevYear ? [c3, c2, c1] : [c1, c2];
        const dimLabels = hasPrevYear ? [targetLabel, thisYearLabel, lastYearLabel] : ['Sales', 'Budget'];
        const productKeys = hasPrevYear ? ['budget', 'value', 'prevYearSales'] : ['value', 'budget'];
        const trendKeys = hasPrevYear ? ['sales', 'budget', 'prevYearSales'] : ['sales', 'budget'];
        const trendColors = hasPrevYear ? [c2, c3, c1] : [c1, c2];
        const trendLabels = hasPrevYear ? [thisYearLabel, targetLabel, lastYearLabel] : ['Sales', 'Budget'];
        lineChart(r.trendChart.el, trendData, trendKeys, trendColors, trendLabels, { highlightIndex });
        groupedBarChart(r.franchiseChart.el, json.franchise, dimKeys, dimColors, dimLabels);
        groupedBarChart(r.customerTypeChart.el, json.customerType, dimKeys, dimColors, dimLabels);
        hGroupedBarChart(r.productChart.el, json.product, productKeys, dimColors, dimLabels);
        renderSalesmanSingleTable(r.salesmanTable.el, json.salesman, !!monthMatch, hasPrevYear, isPartialMonth);

        this.renderNarratives(json);
      }

      await this.updateRegionSection();
    } catch (e) {
      this.state.error = 'Failed to load dashboard data — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }
}

registry.category("actions").add("pbi_dashboards.sales_dashboard", PbiSalesDashboard);
