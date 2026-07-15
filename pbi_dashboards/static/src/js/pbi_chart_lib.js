/** @odoo-module **/

/*
 * Shared SVG chart / KPI-tile rendering helpers, lifted out of
 * sales_kpi_dashboard.js (copy, not refactor — that file is a live
 * dashboard and stays untouched) so pbi_dashboards/static/src/js/
 * service_dashboard.js (the generic Service Dashboards engine, one
 * component for all 15 boards) can reuse the exact same visual style
 * instead of re-implementing bar/donut charts.
 */

import { t } from "./pbi_i18n";

// ---------------------------------------------------------------------
// formatting
// ---------------------------------------------------------------------
export const fmt = n => n == null ? "–" : new Intl.NumberFormat('en-US').format(Math.round(n));
export const fmtM = n => n == null ? "–" : (n / 1e6).toFixed(1) + "M";
export const fmtK = n => n == null ? "–" : (n / 1e3).toFixed(1) + "K";
export const fmtCompact = n => n == null ? "–" : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(n);
export function pct(part, total) { return total > 0 ? (part / total * 100) : null; }
export function fmtPct(p) { return p == null ? "–" : p.toFixed(1) + "%"; }
export function fmtPctPrecise(p) { return p == null ? "–" : p.toFixed(2) + "%"; }
// H:MM — matches ks_dashboard_ninja's own float_time widget, used for every
// "*_hours" measure (RTAT, onhold/cstneedquote/technician-travel/worked
// hours, etc.) instead of the plain decimal-hours number.
export function fmtHours(n) {
  if (n == null) return "–";
  const totalMin = Math.round(n * 60);
  const h = Math.floor(Math.abs(totalMin) / 60) * Math.sign(totalMin || 1);
  const m = Math.abs(totalMin) % 60;
  return `${h}:${String(m).padStart(2, '0')}`;
}

// ---------------------------------------------------------------------
// tooltip — a single shared element, owned by whichever dashboard mounts
// it (t-ref="tooltip"); callers wire setTooltipEl/clearTooltipEl from
// their own onMounted/onWillUnmount, matching sales_kpi_dashboard.js's
// module-level tooltipEl convention.
// ---------------------------------------------------------------------
let tooltipEl = null;
export function setTooltipEl(el) { tooltipEl = el; }
export function clearTooltipEl(el) { if (tooltipEl === el) tooltipEl = null; }
export function showTip(evt, html) {
  if (!tooltipEl) return;
  tooltipEl.innerHTML = html;
  tooltipEl.classList.add('show');
  moveTip(evt);
}
export function moveTip(evt) {
  if (!tooltipEl) return;
  const pad = 14;
  tooltipEl.style.left = (evt.clientX + pad) + 'px';
  tooltipEl.style.top = (evt.clientY + pad) + 'px';
}
export function hideTip() { if (tooltipEl) tooltipEl.classList.remove('show'); }

// Truncates a label to "…" once it would overflow the width of its own
// slot (a group's column on the x-axis) — avoids adjacent category labels
// visually overlapping.
export function truncateLabel(text, maxWidth, fontSize = 10) {
  if (!text) return text;
  const maxChars = Math.max(1, Math.floor(maxWidth / (fontSize * 0.6)));
  if (text.length <= maxChars) return text;
  return text.slice(0, Math.max(1, maxChars - 1)) + '…';
}

export function attachBarTooltips(el) {
  el.querySelectorAll('rect[data-tip]').forEach(rect => {
    rect.addEventListener('mousemove', evt => {
      const [label, seriesLabel, val] = rect.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${seriesLabel}: <b>${fmt(+val)}</b>`);
    });
    rect.addEventListener('mouseleave', hideTip);
  });
}

export function attachValueTooltips(el, selector) {
  el.querySelectorAll(selector).forEach(node => {
    node.addEventListener('mousemove', evt => {
      const [label, sub, val] = node.getAttribute('data-tip').split('||');
      showTip(evt, `<b>${label}</b><br>${sub}: <b>${val}</b>`);
    });
    node.addEventListener('mouseleave', hideTip);
  });
}

// Single-line legend with a "▶" arrow that scrolls further right when the
// items overflow the available width. A legend with exactly one entry
// (a single-series bar, or a pie/donut with only one category) is
// redundant — it just repeats the card's own title — so it's suppressed.
export function legendHtml(labels, colors) {
  if (labels.length <= 1) return '';
  const items = labels.map((l, i) =>
    `<div class="item"><span class="swatch" style="background:${colors[i]}"></span>${l}</div>`).join('');
  return `<div class="pbi-legend-wrap"><div class="pbi-legend">${items}</div><button type="button" class="legend-more" title="Show more">&#9654;</button></div>`;
}
export function attachLegendScroll(container) {
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

// Wide categorical palette used for donut slices / bar groups — colors are
// assigned by position (a groupby level can have anywhere from a handful
// to 15 categories).
export const PALETTE = [
  '#2a78d6', '#1baf7a', '#eda100', '#4a3aa7', '#17a2b8',
  '#e34948', '#8e44ad', '#16a085', '#d35400', '#2c3e50',
  '#c0392b', '#27ae60', '#f39c12', '#7f8c8d', '#3498db',
];

// Whole-number, collision-free y-axis ticks for groupedBarChart. Steps
// follow a 1-2-5 ladder scaled by increasing powers of 10 (1, 2, 5, 10,
// 20, 50, 100, ... 100000, 200000, 500000, ...) instead of a fixed list
// topping out at 10000 — a hardcoded ceiling silently produced 30-40
// ticks (all their labels overlapping into an unreadable smear) for any
// chart whose values exceed ~50000, e.g. Contract Analysis's contract
// amounts running into the hundreds of thousands.
export function niceAxisTicks(maxVal, valueFmt) {
  const unit = valueFmt === fmtM ? 1e6 : valueFmt === fmtK ? 1e3 : 1;
  const maxUnits = Math.max(1, Math.ceil(maxVal / unit));
  let step = 1;
  find_step:
  for (let magnitude = 1; magnitude <= 1e15; magnitude *= 10) {
    for (const base of [1, 2, 5]) {
      const candidate = base * magnitude;
      if (Math.ceil(maxUnits / candidate) <= 5) {
        step = candidate;
        break find_step;
      }
    }
  }
  const niceMaxUnits = Math.ceil(maxUnits / step) * step;
  const ticks = [];
  for (let u = 0; u <= niceMaxUnits; u += step) ticks.push(u * unit);
  return ticks;
}
export function axisTickLabel(val, valueFmt) {
  return valueFmt(val).replace(/\.0(?=\D|$)/, '');
}

// ---------------------------------------------------------------------
// grouped bar chart — one group per breakdown category, up to N series.
// Also used for dual-measure bar items (e.g. Estimated vs Actual Hours),
// which pass seriesKeys=['value', 'value2'].
// ---------------------------------------------------------------------
export function groupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels, onCategoryClick, valueFmt = fmt) {
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
// donut chart — contribution % of each breakdown category to the total
// shown, drawn with the stroke-dasharray ring trick.
// ---------------------------------------------------------------------
export function donutChart(el, data, colors, onCategoryClick, valueFmt = fmt) {
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
// KPI tiles — single-value and dual-value ("Total / Closed"-style)
// variants, rendered per-item by the Service Dashboards engine (unlike
// Sales KPI's fixed 12-tile row, a board here can have 3-17 items mixed
// with bar/pie/multiseries charts, so tiles are built one at a time
// rather than as one fixed-shape row).
// ---------------------------------------------------------------------
export function kpiTileHtml(item, tileColorIdx, valueFmt = fmt) {
  const name = t(item.name);
  if (item.type === 'kpi_dual') {
    return `
      <div class="pbi-kpi pbi-kpi-dual tile-color-${tileColorIdx}" data-tip="${name}||${t('Total / Closed')}||${valueFmt(item.value)} / ${valueFmt(item.value2)}">
        <div class="value-dual"><span class="v1">${valueFmt(item.value)}</span><span class="sep">/</span><span class="v2">${valueFmt(item.value2)}</span></div>
        <div class="label">${name}</div>
      </div>`;
  }
  return `
    <div class="pbi-kpi tile-color-${tileColorIdx}" data-tip="${name}||${t('Actual')}||${valueFmt(item.value)}">
      <div class="value">${valueFmt(item.value)}</div>
      <div class="label">${name}</div>
    </div>`;
}
