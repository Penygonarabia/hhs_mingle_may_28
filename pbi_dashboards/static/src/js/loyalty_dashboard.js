/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// ---------------------------------------------------------------------
// formatting helpers (trimmed copy of the pattern in sales_dashboard.js —
// that file doesn't export its helpers, and this dashboard's charts are
// plain count/points totals, not sales-vs-budget, so only a subset applies)
// ---------------------------------------------------------------------
const fmt = n => n == null ? "–" : new Intl.NumberFormat('en-US').format(Math.round(n));
const fmtCompact = n => n == null ? "–" : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 0 }).format(n);
function legendHtml(labels, colors) {
  if (labels.length < 2) return '';
  return labels.map((l, i) => `<div class="item"><span class="swatch" style="background:${colors[i % colors.length]}"></span>${l}</div>`).join('');
}

// ---------------------------------------------------------------------
// tooltip — module-scoped since only one dashboard instance is mounted
// at a time (a client action)
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
// chart drawing (pure functions operating on a DOM element — same
// vertical/horizontal bar shapes as sales_dashboard.js so the two
// dashboards read as one visual family)
// ---------------------------------------------------------------------
// Standard "nice numbers" axis step (1/2/5 x a power of 10), so that
// N equally-spaced ticks from 0 are always distinct whole numbers.
function niceAxisStep(maxVal, maxTicks) {
  if (maxVal <= 0) return 1;
  const rawStep = maxVal / maxTicks;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const residual = rawStep / magnitude;
  let niceResidual;
  if (residual > 5) niceResidual = 10;
  else if (residual > 2) niceResidual = 5;
  else if (residual > 1) niceResidual = 2;
  else niceResidual = 1;
  return Math.max(1, niceResidual * magnitude);
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

function groupedBarChart(el, data, seriesKeys, seriesColors, seriesLabels, opts = {}) {
  const W = opts.width || el.clientWidth || 520, H = opts.height || 260;
  const marginL = 60, marginR = 10, marginT = 10, marginB = 30;
  const plotW = W - marginL - marginR, plotH = H - marginT - marginB;
  const rawMax = Math.max(1, ...data.flatMap(d => seriesKeys.map(k => d[k] || 0)));
  // A "nice" whole-number step (1/2/5 x a power of 10) so gridline ticks
  // (0, step, 2*step, ...) are always distinct once rounded to whole
  // numbers — dividing rawMax into N equal fractional slices and rounding
  // each independently can make two different ticks collide (e.g. 2.52
  // and 3.36 both round to "3").
  const step = niceAxisStep(rawMax, 4);
  const ticks = Math.max(1, Math.ceil((rawMax * 1.12) / step));
  const maxVal = ticks * step;
  const groupW = plotW / data.length;
  const barW = Math.min(28, (groupW * 0.6) / seriesKeys.length);
  const gap = 3;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  for (let i = 0; i <= ticks; i++) {
    const y = marginT + plotH - (plotH * i / ticks);
    const val = i * step;
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
      svg += `<rect data-tip="${d.label}||${seriesLabels[si]}||${val}" rx="3" ry="3" x="${x}" y="${y}" width="${barW}" height="${Math.max(barH, 1)}" fill="${seriesColors[si % seriesColors.length]}" style="cursor:pointer"/>`;
    });
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

function hBarChart(el, data, color, valueLabel) {
  const W = el.clientWidth || 520;
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

// ---------------------------------------------------------------------
// promotion participation — flat pivot tables (no drill-down), reusing
// the .data-table styling that sales_dashboard.css already defines on
// the shared .pbi-sales-dashboard root class.
// ---------------------------------------------------------------------
function renderPromoParticipationTable(el, rows, opts = {}) {
  const withSalesman = !!opts.withSalesman;
  if (!rows.length) {
    el.innerHTML = `<p class="subtitle">No promotions with recorded usage in this period.</p>`;
    return;
  }
  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        ${withSalesman ? '<th>Salesman</th>' : ''}
        <th>Promotion Ref</th><th>Promotion Name</th><th>Date</th>
        <th class="num">No. of Loyalty Customers</th>
        <th class="num">No. of Utilised Customers</th>
        <th style="width:160px">Participation</th>
      </tr></thead>
      <tbody>
        ${rows.map(r => {
          const pct = r.loyaltyCustomers > 0 ? (r.usedCustomers / r.loyaltyCustomers * 100) : 0;
          return `<tr>
            ${withSalesman ? `<td>${r.salesman}</td>` : ''}
            <td>${r.promoRef}</td>
            <td>${r.promoName}</td>
            <td>${r.date || '–'}</td>
            <td class="num">${fmt(r.loyaltyCustomers)}</td>
            <td class="num">${fmt(r.usedCustomers)}</td>
            <td><div class="bar-cell"><div class="mini-bar"><span style="width:${pct.toFixed(1)}%;background:var(--series-1)"></span></div>${pct.toFixed(1)}%</div></td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

// ---------------------------------------------------------------------
// filter options
// ---------------------------------------------------------------------
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

// v matches work_center_group.name exactly; l is the friendlier label shown in the dropdown.
const REGION_OPTIONS = [
  { v: 'all', l: 'All' },
  { v: 'Central Region', l: 'Central' },
  { v: 'Eastern Region', l: 'Eastern' },
  { v: 'Western Region', l: 'Western' },
];

// Each chart's drill path (Region is always level 0) and whether it stacks
// one bar per tier (only "Number of customers per tier") or a single value
// series. The leaf level's bar click redirects instead of drilling further.
const CHART_CONFIGS = [
  { key: 'tier', title: 'Number of customers per tier', subtitle: 'Region wise', levels: ['region', 'city'], multiSeries: true },
  { key: 'pointsIssued', title: 'Points issued', subtitle: 'Region wise', levels: ['region', 'city', 'customer'], multiSeries: false },
  { key: 'pointsRedeemed', title: 'Points redeemed', subtitle: 'Region wise', levels: ['region', 'city', 'customer'], multiSeries: false },
  { key: 'newUsers', title: 'Newly added users', subtitle: 'Region wise, for the selected period', levels: ['region', 'city'], multiSeries: false },
];

export class PbiLoyaltyDashboard extends Component {
  static template = "pbi_dashboards.loyalty_dashboard";
  static props = ["*"];

  setup() {
    this.rpc = useService("rpc");
    this.action = useService("action");
    this.periodOptions = PERIOD_OPTIONS;
    this.regionOptions = REGION_OPTIONS;
    this.chartConfigs = CHART_CONFIGS;

    this.state = useState({
      period: 'this_year', region: 'all', dateFrom: '', dateTo: '',
      resolvedFrom: '', resolvedTo: '',
      loading: false, error: '',
      drills: Object.fromEntries(CHART_CONFIGS.map(c => [c.key, this._emptyDrill()])),
    });

    this.tiers = [];
    this.chartData = Object.fromEntries(CHART_CONFIGS.map(c => [c.key, []]));

    this.rootRef = useRef('root');
    this.refs = {
      tooltip: useRef('tooltip'),
      promoParticipationTable: useRef('promoParticipationTable'),
      promoParticipationSalesmanTable: useRef('promoParticipationSalesmanTable'),
    };
    this.promoParticipation = [];
    this.promoParticipationSalesman = [];
    for (const cfg of CHART_CONFIGS) {
      this.refs[cfg.key] = {
        title: useRef(cfg.key + 'Title'),
        subtitle: useRef(cfg.key + 'Subtitle'),
        breadcrumb: useRef(cfg.key + 'Breadcrumb'),
        legend: useRef(cfg.key + 'Legend'),
        chart: useRef(cfg.key + 'Chart'),
      };
    }

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

  _emptyDrill() {
    return { level: 'region', regionId: null, regionLabel: null, cityId: null, cityLabel: null };
  }

  _todayIso() { return new Date().toISOString().slice(0, 10); }

  seriesColors() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    const read = (name, fallback) => style.getPropertyValue(name).trim() || fallback;
    return [
      read('--series-2', '#1baf7a'), read('--series-1', '#2a78d6'),
      read('--series-3', '#eda100'), read('--series-5', '#4a3aa7'), read('--series-6', '#e34948'),
    ];
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

  async selectRegion(v) { this.state.region = v; await this.load(); }

  async setDateFrom(v) { this.state.dateFrom = v; await this.load(); }
  async setDateTo(v) { this.state.dateTo = v; await this.load(); }

  exportPdf() {
    window.print();
  }

  _filterParams() {
    const params = { period: this.state.period, region: this.state.region };
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
      const res = await this.rpc('/pbi_dashboards/loyalty/data', this._filterParams());
      if (res.error) { this.state.error = res.error; return; }
      this.state.resolvedFrom = res.dateFrom;
      this.state.resolvedTo = res.dateTo;
      this.tiers = res.tier.tiers;
      this.chartData = {
        tier: res.tier.data, pointsIssued: res.pointsIssued,
        pointsRedeemed: res.pointsRedeemed, newUsers: res.newUsers,
      };
      this.promoParticipation = res.promoParticipation || [];
      this.promoParticipationSalesman = res.promoParticipationSalesman || [];
      for (const cfg of CHART_CONFIGS) this.state.drills[cfg.key] = this._emptyDrill();
      for (const cfg of CHART_CONFIGS) this.renderSection(cfg.key);
      renderPromoParticipationTable(this.refs.promoParticipationTable.el, this.promoParticipation);
      renderPromoParticipationTable(this.refs.promoParticipationSalesmanTable.el, this.promoParticipationSalesman, { withSalesman: true });
    } catch (e) {
      this.state.error = 'Failed to load — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  async loadDrill(key) {
    const drill = this.state.drills[key];
    const params = {
      ...this._filterParams(), chart: key, level: drill.level,
      drillRegionId: drill.regionId, drillCityId: drill.cityId,
    };
    const res = await this.rpc('/pbi_dashboards/loyalty/drill', params);
    if (res.error) { this.state.error = res.error; return; }
    this.chartData[key] = res.data;
    if (key === 'tier') this.tiers = res.tiers;
    this.renderSection(key);
  }

  // ------------------------------------------------------------------
  // drill navigation
  // ------------------------------------------------------------------
  onBarClick(key, label) {
    const cfg = CHART_CONFIGS.find(c => c.key === key);
    const drill = this.state.drills[key];
    const row = (this.chartData[key] || []).find(d => d.label === label);
    if (!row) return;

    const idx = cfg.levels.indexOf(drill.level);
    if (idx === cfg.levels.length - 1) {
      this.redirect(key, row);
      return;
    }
    if (drill.level === 'region') {
      drill.regionId = row.id;
      drill.regionLabel = row.label;
    } else if (drill.level === 'city') {
      drill.cityId = row.id;
      drill.cityLabel = row.label;
    }
    drill.level = cfg.levels[idx + 1];
    this.loadDrill(key);
  }

  drillTo(key, level) {
    const drill = this.state.drills[key];
    drill.level = level;
    if (level === 'region') {
      drill.regionId = null; drill.regionLabel = null; drill.cityId = null; drill.cityLabel = null;
    } else if (level === 'city') {
      drill.cityId = null; drill.cityLabel = null;
    }
    this.loadDrill(key);
  }

  redirect(key, row) {
    const cfg = CHART_CONFIGS.find(c => c.key === key);
    const leaf = cfg.levels[cfg.levels.length - 1];
    if (leaf === 'city') {
      // "Number of customers per tier" / "Newly added users" — redirect to
      // the customer list for the selected city.
      const domain = [['work_center_id', '=', row.id], ['activate_loyalty_feature', '=', true]];
      domain.push(['activation_date', '>=', this.state.resolvedFrom]);
      domain.push(['activation_date', '<=', this.state.resolvedTo]);
      this.action.doAction({
        type: 'ir.actions.act_window',
        name: `Customers — ${row.label}`,
        res_model: 'res.partner',
        views: [[false, 'list'], [false, 'form']],
        view_mode: 'list',
        target: 'current',
        domain,
      });
    } else {
      // "Points issued" / "Points redeemed" — redirect to the loyalty
      // points history list for the selected customer.
      this.action.doAction({
        type: 'ir.actions.act_window',
        name: `Loyalty Points — ${row.label}`,
        res_model: 'customer.loyalty.points.history',
        views: [[false, 'list'], [false, 'form']],
        view_mode: 'list',
        target: 'current',
        domain: [['customer_no', '=', row.id]],
      });
    }
  }

  // ------------------------------------------------------------------
  // rendering
  // ------------------------------------------------------------------
  renderBreadcrumb(key) {
    const drill = this.state.drills[key];
    const parts = [{ label: 'All Regions', level: 'region' }];
    if (drill.regionLabel) parts.push({ label: drill.regionLabel, level: 'city' });
    if (drill.cityLabel) parts.push({ label: drill.cityLabel, level: 'customer' });
    const el = this.refs[key].breadcrumb.el;
    if (parts.length === 1) { el.innerHTML = ''; return; }
    el.innerHTML = parts.map((p, i) => {
      if (i === parts.length - 1) return `<span class="crumb current">${p.label}</span>`;
      return `<span class="crumb" data-level="${p.level}">${p.label}</span><span class="crumb-sep">›</span>`;
    }).join('');
    el.querySelectorAll('.crumb[data-level]').forEach(elm => {
      elm.addEventListener('click', () => this.drillTo(key, elm.getAttribute('data-level')));
    });
  }

  renderSection(key) {
    const cfg = CHART_CONFIGS.find(c => c.key === key);
    const r = this.refs[key];
    const drill = this.state.drills[key];
    const data = this.chartData[key] || [];
    const colors = this.seriesColors();

    const levelIdx = cfg.levels.indexOf(drill.level);
    const isLeaf = levelIdx === cfg.levels.length - 1;
    const suffixParts = [drill.regionLabel, drill.cityLabel].filter(Boolean);
    const suffix = suffixParts.length ? ` — ${suffixParts.join(' / ')}` : '';
    r.title.el.textContent = `${cfg.title}${suffix}`;

    const leafNoun = cfg.levels[cfg.levels.length - 1] === 'city' ? 'the customer list' : 'the loyalty points list';
    const nextNoun = drill.level === 'region' ? 'cities' : 'customers';
    r.subtitle.el.textContent = isLeaf
      ? `${cfg.subtitle} · click a bar to open ${leafNoun}`
      : `${cfg.subtitle} · click a bar or label to drill into ${nextNoun}`;

    this.renderBreadcrumb(key);

    if (cfg.multiSeries) {
      r.legend.el.innerHTML = legendHtml(this.tiers, colors);
      groupedBarChart(r.chart.el, data, this.tiers, colors, this.tiers, {
        onLabelClick: (label) => this.onBarClick(key, label),
      });
    } else if (isLeaf && drill.level === 'customer') {
      r.legend.el.innerHTML = '';
      hBarChart(r.chart.el, data, colors[0], cfg.title);
    } else {
      r.legend.el.innerHTML = '';
      groupedBarChart(r.chart.el, data, ['value'], [colors[0]], [cfg.title], {
        onLabelClick: (label) => this.onBarClick(key, label),
      });
    }

    r.chart.el.querySelectorAll('rect[data-tip]').forEach(rect => {
      rect.style.cursor = 'pointer';
      rect.addEventListener('click', () => {
        const label = rect.getAttribute('data-tip').split('||')[0];
        this.onBarClick(key, label);
      });
    });
  }
}

registry.category("actions").add("pbi_dashboards.loyalty_dashboard", PbiLoyaltyDashboard);
