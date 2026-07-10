/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// ---------------------------------------------------------------------
// formatting/tooltip helpers — trimmed copy of the pattern in
// loyalty_dashboard.js / sales_dashboard.js (neither file exports its
// helpers, so each dashboard here carries its own small subset)
// ---------------------------------------------------------------------
const fmt = n => n == null ? "–" : new Intl.NumberFormat('en-US').format(Math.round(n));
const fmtCompact = n => n == null ? "–" : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(n);

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

// Every drill level (region..customer) is rendered the same way: one
// horizontal bar per row, click a bar or label to drill in. Same shape as
// loyalty_dashboard.js's hBarChart, plus a data-code attribute so the click
// handler can pass the row's code (not just its display label) back to the
// controller for the next level's WHERE filter.
function hBarChart(el, data, color, valueLabel) {
  const W = el.clientWidth || 640;
  const rowH = 28, marginL = 220, marginR = 70, marginT = 4;
  const H = data.length * rowH + marginT * 2;
  const plotW = W - marginL - marginR;
  const maxVal = Math.max(1, ...data.map(d => Math.abs(d.value) || 0)) * 1.05;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">`;
  data.forEach((d, i) => {
    const y = marginT + i * rowH;
    const barW = plotW * (Math.abs(d.value || 0) / maxVal);
    svg += `<text class="bar-label cat-label-clickable" data-code="${d.code}" x="${marginL - 8}" y="${y + rowH * 0.62}" text-anchor="end">${d.label}</text>`;
    svg += `<rect data-code="${d.code}" data-tip="${d.label}||${valueLabel}||${d.value || 0}" rx="3" ry="3" x="${marginL}" y="${y + rowH * 0.18}" width="${Math.max(barW, 2)}" height="${rowH * 0.55}" fill="${color}" style="cursor:pointer"/>`;
    svg += `<text class="axis-label" x="${marginL + barW + 6}" y="${y + rowH * 0.62}">${fmtCompact(d.value)}</text>`;
  });
  svg += `</svg>`;
  el.innerHTML = svg;
  attachBarTooltips(el);
}

function renderTransactionTable(el, rows) {
  if (!rows.length) {
    el.innerHTML = `<p class="subtitle">No transactions for this selection.</p>`;
    return;
  }
  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Transaction No</th><th>Date</th><th>Warehouse</th><th>Part</th>
        <th class="num">Qty</th><th class="num">Amount</th>
      </tr></thead>
      <tbody>
        ${rows.map(r => `<tr>
          <td>${r.transactionNo || '–'}</td>
          <td>${r.date || '–'}</td>
          <td>${r.warehouse || '–'}</td>
          <td>${r.part || '–'}</td>
          <td class="num">${fmt(r.qty)}</td>
          <td class="num">${fmt(r.amount)}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

// ---------------------------------------------------------------------
// filter options — Period only (no Region filter: Region is itself the
// first drill level in this report, not a cross-cutting one)
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

// Drill order per the report spec. "transactions" is a leaf row list, not
// a group-by level (see loadDrill / renderReport).
const LEVELS = ['region', 'city', 'main', 'mainSub', 'prodGroup', 'productSubGroup', 'customer', 'transactions'];
const LEVEL_LABELS = {
  region: 'Region', city: 'City', main: 'Main', mainSub: 'Main Sub',
  prodGroup: 'Prod Group', productSubGroup: 'Product Sub Group',
  customer: 'Customer', transactions: 'Transaction List',
};

const REPORT_CONFIGS = [
  { key: 'amount', title: 'Report 1 — Sales by Amount', valueLabel: 'Amount' },
  { key: 'qty', title: 'Report 2 — Sales by Qty', valueLabel: 'Qty' },
];

export class PbiSalesAnalysisDashboard extends Component {
  static template = "pbi_dashboards.sales_analysis_dashboard";
  static props = ["*"];

  setup() {
    this.rpc = useService("rpc");
    this.periodOptions = PERIOD_OPTIONS;
    this.reportConfigs = REPORT_CONFIGS;
    this.levelLabels = LEVEL_LABELS;

    this.state = useState({
      period: 'this_year', dateFrom: '', dateTo: '',
      resolvedFrom: '', resolvedTo: '',
      loading: false, error: '',
      reports: Object.fromEntries(REPORT_CONFIGS.map(c => [c.key, this._emptyReportState()])),
    });

    this.reportData = Object.fromEntries(REPORT_CONFIGS.map(c => [c.key, { rows: [], total: 0 }]));

    this.rootRef = useRef('root');
    this.refs = { tooltip: useRef('tooltip') };
    for (const cfg of REPORT_CONFIGS) {
      this.refs[cfg.key] = {
        subtitle: useRef(cfg.key + 'Subtitle'),
        breadcrumb: useRef(cfg.key + 'Breadcrumb'),
        body: useRef(cfg.key + 'Body'),
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

  _emptyReportState() {
    return { level: 'region', selected: {}, path: [] };
  }

  _todayIso() { return new Date().toISOString().slice(0, 10); }

  renderSubtitle(key) {
    const cfg = REPORT_CONFIGS.find(c => c.key === key);
    const total = (this.reportData[key] && this.reportData[key].total) || 0;
    const level = this.state.reports[key].level;
    this.refs[key].subtitle.el.textContent = `Total ${cfg.valueLabel}: ${fmt(total)} · ${LEVEL_LABELS[level]} level`
      + (level === 'transactions' ? '' : ' · click a bar or label to drill in');
  }

  seriesColor() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    return style.getPropertyValue('--series-1').trim() || '#2a78d6';
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

  async setDateFrom(v) { this.state.dateFrom = v; await this.load(); }
  async setDateTo(v) { this.state.dateTo = v; await this.load(); }

  _filterParams() {
    const params = { period: this.state.period };
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
      const res = await this.rpc('/pbi_dashboards/sales_analysis/data', this._filterParams());
      if (res.error) { this.state.error = res.error; return; }
      this.state.resolvedFrom = res.dateFrom;
      this.state.resolvedTo = res.dateTo;
      for (const cfg of REPORT_CONFIGS) {
        this.state.reports[cfg.key] = this._emptyReportState();
        this.reportData[cfg.key] = res[cfg.key];
        this.renderReport(cfg.key);
      }
    } catch (e) {
      this.state.error = 'Failed to load — ' + e.message;
    } finally {
      this.state.loading = false;
    }
  }

  async loadDrill(key) {
    const rep = this.state.reports[key];
    const params = { ...this._filterParams(), report: key, level: rep.level, selected: rep.selected };
    const res = await this.rpc('/pbi_dashboards/sales_analysis/drill', params);
    if (res.error) { this.state.error = res.error; return; }
    this.reportData[key] = res;
    this.renderReport(key);
  }

  // ------------------------------------------------------------------
  // drill navigation
  // ------------------------------------------------------------------
  onRowClick(key, code, label) {
    const rep = this.state.reports[key];
    if (rep.level === 'transactions') return;
    const idx = LEVELS.indexOf(rep.level);
    rep.selected[rep.level] = code;
    rep.path.push({ level: rep.level, code, label });
    rep.level = LEVELS[idx + 1];
    this.loadDrill(key);
  }

  drillTo(key, pathIndex) {
    // pathIndex === -1 means back to the root (Region) level.
    const rep = this.state.reports[key];
    rep.path = rep.path.slice(0, pathIndex + 1);
    const newLevelIdx = pathIndex + 1;
    rep.level = LEVELS[newLevelIdx];
    for (const lvl of LEVELS) {
      if (!rep.path.some(p => p.level === lvl)) delete rep.selected[lvl];
    }
    this.loadDrill(key);
  }

  // ------------------------------------------------------------------
  // rendering
  // ------------------------------------------------------------------
  renderBreadcrumb(key) {
    const rep = this.state.reports[key];
    const el = this.refs[key].breadcrumb.el;
    const parts = [{ label: 'All Regions', idx: -1 }, ...rep.path.map((p, i) => ({ label: p.label, idx: i }))];
    if (parts.length === 1) { el.innerHTML = ''; return; }
    el.innerHTML = parts.map((p, i) => {
      if (i === parts.length - 1) return `<span class="crumb current">${p.label}</span>`;
      return `<span class="crumb" data-idx="${p.idx}">${p.label}</span><span class="crumb-sep">›</span>`;
    }).join('');
    el.querySelectorAll('.crumb[data-idx]').forEach(elm => {
      elm.addEventListener('click', () => this.drillTo(key, +elm.getAttribute('data-idx')));
    });
  }

  renderReport(key) {
    const cfg = REPORT_CONFIGS.find(c => c.key === key);
    const r = this.refs[key];
    const rep = this.state.reports[key];
    const data = this.reportData[key] || { rows: [], total: 0 };

    this.renderSubtitle(key);
    this.renderBreadcrumb(key);

    if (rep.level === 'transactions') {
      renderTransactionTable(r.body.el, data.rows || []);
    } else {
      const rows = data.rows || [];
      if (!rows.length) {
        r.body.el.innerHTML = `<p class="subtitle">No data for this selection.</p>`;
      } else {
        hBarChart(r.body.el, rows, this.seriesColor(), cfg.valueLabel);
        r.body.el.querySelectorAll('[data-code]').forEach(elm => {
          elm.style.cursor = 'pointer';
          elm.addEventListener('click', () => {
            const code = elm.getAttribute('data-code');
            const row = rows.find(d => String(d.code) === code);
            if (row) this.onRowClick(key, row.code, row.label);
          });
        });
      }
    }
  }
}

registry.category("actions").add("pbi_dashboards.sales_analysis_dashboard", PbiSalesAnalysisDashboard);
