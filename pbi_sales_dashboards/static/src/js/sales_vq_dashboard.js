/** @odoo-module **/

import { useRef, onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { t, addLabels } from "@pbi_dashboards/js/pbi_i18n";
import { PbiSalesSmanDashboard, groupedBarChart, pieChart, lineChart, fmt, fmtM, fmtK,
         OTHERS_CODE } from "./sales_sman_dashboard";
// A table row drills exactly as its bar does, so it opens the same menu.
import { attachDrillMenu, closeDrillMenu } from "@pbi_dashboards/js/pbi_drill_menu";

// "Sales Dashboard - VQ" — Value and Quantity, side by side.
//
// The same board as "Sales Dashboard With Salesman": same snapshot, same ten
// drill levels, same Regular/Manager switch, same KPI tiles, same toolbar and
// scope line. Everything visible is inherited from that component; this file is
// only what differs, and what differs is one row of the layout:
//
//   With Salesman   MTD:  [ value bars ......... ][ value donut ]
//                   YTD:  [ value bars ......... ][ value donut ]
//
//   VQ              MTD:  [ value bars ....][ qty bars ....]
//                   YTD:  [ value bars ....][ qty bars ....]
//
// The donut carried one number per slice — that category's share of the total —
// and dropping it would have dropped that number with it, so the bars carry it
// now: a contribution % under every caption, on BOTH charts (its own measure's
// share on each), and in the This Year bar's tooltip. See groupedBarChart's
// shareKey in sales_sman_dashboard.js.
//
// The quantity chart keeps the VALUE chart's category order rather than sorting
// itself by quantity. The two charts are a pair — the nth bar is the same
// category on both, which is the whole point of reading them side by side — and
// a chart that reordered itself would break that for the sake of a ranking the
// reader can already see in the bar heights.
//
// The chart itself can be a bar chart, a pie, a line or an area chart. One
// button carries the current shape's icon and drops a list of the four rather
// than four buttons sitting in the card header: the header is shared with the
// table switch, the CSV and the full-page control, and on a card this size
// three more permanent icons cost more room than the choice is worth. Picking
// a shape also puts the card back on its chart, so the list never sets a shape
// you cannot see. Bar and line/area draw every series; the pie draws the This
// Year one alone, since three overlapping series is not a pie anybody reads.
//
// Every card also carries a chart/table switch. The table is the SAME rows the
// chart draws -- one column per series, the contribution % as a Share column,
// and a total line the shares add up to -- at full precision rather than the
// axis's rounding, and its rows drill exactly as the bars do. Per card, not per
// board: reading one card's figures is usually a question about that card.
//
// Any card can also be thrown full page, in whichever view it is on, and a
// table can be taken away as CSV. The full-page panel is the same card, not a
// second one: it shares the card's chart/table state, so switching view inside
// it switches the card underneath, and closing it leaves you where you were.
//
// Data comes from its own route for access reasons only; the payload is byte
// for byte the one the salesman board reads. See controllers/sales_vq_main.py.
// Only the two strings this board introduces. "Total" and "Contribution" are
// already in pbi_i18n's shared chrome dictionary, and repeating them here would
// be two copies to keep in step for no gain.
addLabels({
  "Sales Dashboard - VQ": "لوحة المبيعات - القيمة والكمية",
  "KPI Tiles": "بطاقات المؤشرات",
  "Show as chart": "عرض كرسم بياني",
  "Chart type": "نوع الرسم البياني",
  "Bar": "أعمدة",
  "Pie": "دائري",
  "Line": "خطي",
  "Area": "مساحي",
  "Show as table": "عرض كجدول",
  "Open full page": "عرض بملء الصفحة",
  "Download CSV": "تنزيل CSV",
  "Close": "إغلاق",
  "Share": "الحصة",
  "No data": "لا توجد بيانات",
  "Target, This Year and Last Year": "الهدف، هذا العام والعام الماضي",
});

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

// The same rows the chart beside it draws, as numbers you can read off rather
// than measure against an axis: one column per series, plus the contribution %
// the bars carry under their captions, plus a total line that makes the shares
// visibly add up.
//
// Deliberately the EXACT figures (fmt), not the axis's rounded 7.4M. Someone who
// switches to the table has asked for the number, and a table that repeated the
// chart's rounding would answer a question nobody asked it.
function dataTable(el, data, seriesKeys, seriesLabels, shareKey, levelLabel,
                  onCategoryClick, shareTotal, drillMenu) {
  const clickable = !!onCategoryClick;
  let html = '<div class="pbi-table-scroll"><table class="pbi-table"><thead><tr>';
  html += `<th>${esc(levelLabel)}</th>`;
  html += seriesLabels.map(l => `<th class="num">${esc(t(l))}</th>`).join('');
  html += `<th class="num">${esc(t('Share'))}</th></tr></thead><tbody>`;
  if (!data.length) {
    html += `<tr><td colspan="${seriesKeys.length + 2}" class="pbi-table-empty">${esc(t('No data'))}</td></tr>`;
  }
  data.forEach(d => {
    html += `<tr data-code="${esc(d.code)}"${clickable ? ' class="row-clickable"' : ''}>`;
    html += `<td>${esc(d.label)}</td>`;
    html += seriesKeys.map(k => `<td class="num">${fmt(d[k] || 0)}</td>`).join('');
    const share = shareTotal ? (d[shareKey] || 0) / shareTotal * 100 : null;
    html += `<td class="num">${share == null ? '–' : share.toFixed(1) + '%'}</td>`;
    html += '</tr>';
  });
  html += '</tbody><tfoot><tr>';
  html += `<th>${esc(t('Total'))}</th>`;
  html += seriesKeys.map(k =>
    `<th class="num">${fmt(data.reduce((sum, d) => sum + (d[k] || 0), 0))}</th>`).join('');
  // NOT a hardcoded 100%: on a ranked level the rows are the top ten of a
  // larger whole, and their shares are meant to fall short of it. Summing what
  // is actually in the column is the only line that stays true either way.
  const shareSum = data.reduce((sum, d) => sum + (d[shareKey] || 0), 0);
  html += `<th class="num">${data.length && shareTotal
    ? (shareSum / shareTotal * 100).toFixed(1) + '%' : '–'}</th>`;
  html += '</tr></tfoot></table></div>';
  el.innerHTML = html;
  // A row drills exactly as its bar does, including "Others" being inert --
  // onCategoryClick is the same handler and carries the same guard. A table
  // that dead-ended a drill the chart offers would make the two views
  // different tools rather than two readings of one.
  if (onCategoryClick) {
    el.querySelectorAll('tr[data-code]').forEach(tr => {
      tr.addEventListener('click', () => {
        const row = data.find(d => String(d.code) === tr.getAttribute('data-code'));
        if (row) onCategoryClick(row.code, row.label);
      });
    });
  }
  // And right-click / long-press a row for the other ten levels, as on the
  // chart. The selector is the ROW, not the cells: the whole line is the
  // category, and a menu that only opened over the first column would be a
  // gesture the reader has to aim.
  if (drillMenu) {
    attachDrillMenu(el, Object.assign({}, drillMenu, {
      selector: 'tr[data-code]',
      contextFor: code => {
        const row = data.find(d => String(d.code) === String(code));
        // Same guard the charts carry: "Others" is a roll-up, not a category,
        // so there is nothing to open at another level.
        if (!row || String(row.code) === OTHERS_CODE) return null;
        return { label: row.label, valueText: fmt(row[shareKey] || row[seriesKeys[0]] || 0) };
      },
    }));
  }
}

export class PbiSalesVqDashboard extends PbiSalesSmanDashboard {
  static template = "pbi_sales_dashboards.sales_vq_dashboard";

  get route() { return '/pbi_dashboards/sales_vq/data'; }

  setup() {
    super.setup();
    // 1. Filters (Year, Month, Sub-category View) is expanded by default.
    // 2. Levels (10 level filter dropdowns) is collapsed by default.
    // 3. Level buttons (10 level nav buttons) remains permanently open outside.
    this.state.filtersCollapsed = false;
    this.state.levelsCollapsed = true;
    // The two charts that replace the two donuts. Added after super.setup()
    // rather than by rewriting it: still inside this component's setup, so
    // useRef is where a hook must be, and the inherited refs — including the
    // donut ones, which this template has no nodes for and this file never
    // touches — are left exactly as they were.
    this.refs.mtdQtyBar = useRef('mtdQtyBar');
    this.refs.ytdQtyBar = useRef('ytdQtyBar');
    // Chart or table, per card and not per board: someone comparing this
    // month's quantities against a target usually wants the figures for ONE of
    // the four and the shape of the other three.
    this.state.views = { mtdAmount: 'chart', mtdQty: 'chart',
                         ytdAmount: 'chart', ytdQty: 'chart' };
    // Which shape each card's chart is drawn in, and which card's shape list
    // is open (one at a time, and null when none is).
    this.state.kinds = { mtdAmount: 'bar', mtdQty: 'bar',
                         ytdAmount: 'bar', ytdQty: 'bar' };
    this.state.kindMenu = null;
    // Which card is open full page, or null. One at a time: the panel covers
    // the board, so a second would have nowhere to go.
    this.state.modal = null;
    this.refs.modalBody = useRef('modalBody');

    // The panel's body is created by the patch that opens it, so it cannot be
    // filled from the click that set the state -- there is no element yet.
    // Filling it here also covers every later patch: switching view inside the
    // panel, and a reload landing while it is open.
    onPatched(() => this.renderModal());
    // Escape closes, as it does in every other overlay the user meets. On the
    // document rather than the panel: the panel is not focused, and requiring a
    // click into it first would make the key look broken.
    this._onKeyDown = ev => {
      if (ev.key !== 'Escape') return;
      // The shape list first: it is the thing most recently opened, and
      // closing the panel under it would leave it hanging over the board.
      if (this.state.kindMenu) this.state.kindMenu = null;
      else if (this.state.modal) this.closeModal();
    };
    // A menu that only closed on a second click of its own button would sit
    // over the card while the reader tried to use what is underneath.
    this._onDocClick = ev => {
      if (this.state.kindMenu && !ev.target.closest('.kind-picker')) {
        this.state.kindMenu = null;
      }
    };
    onMounted(() => {
      document.addEventListener('keydown', this._onKeyDown);
      document.addEventListener('click', this._onDocClick);
    });
    onWillUnmount(() => {
      document.removeEventListener('keydown', this._onKeyDown);
      document.removeEventListener('click', this._onDocClick);
    });
  }

  get modalCard() {
    return this.vqCardList.find(c => c.id === this.state.modal) || null;
  }
  // Both close the level menu: the panel opening would cover it, and the panel
  // closing takes the card it was anchored to off screen.
  openModal(id) { closeDrillMenu(); this.state.modal = id; }
  closeModal() { closeDrillMenu(); this.state.modal = null; }

  // The four cards, in the order they are drawn. The template names a card by
  // its id; everything else about it is derived here, so the two cannot say
  // different things about which ref belongs to which measure.
  get vqCardList() {
    return [
      { id: 'mtdAmount', period: 'mtd', measure: 'amount', ref: 'mtdBar' },
      { id: 'mtdQty', period: 'mtd', measure: 'qty', ref: 'mtdQtyBar' },
      { id: 'ytdAmount', period: 'ytd', measure: 'amount', ref: 'ytdBar' },
      { id: 'ytdQty', period: 'ytd', measure: 'qty', ref: 'ytdQtyBar' },
    ];
  }

  cardView(id) { return this.state.views[id] || 'chart'; }
  cardKind(id) { return this.state.kinds[id] || 'bar'; }

  // The four shapes, in the order the list offers them: the two that answer
  // "how big" first, then the two that answer "which way is it going".
  get chartKindList() {
    return [{ v: 'bar', l: 'Bar' }, { v: 'pie', l: 'Pie' },
            { v: 'line', l: 'Line' }, { v: 'area', l: 'Area' }];
  }
  chartKindLabel(id) {
    const k = this.chartKindList.find(x => x.v === this.cardKind(id));
    return t(k ? k.l : 'Bar');
  }

  // The card and its full-page panel each draw their own copy of the header,
  // so the open menu is keyed by both -- otherwise opening it in the panel
  // would also open the one on the card hidden behind it.
  kindMenuKey(id, inModal) { return `${id}|${inModal ? 'modal' : 'card'}`; }
  kindMenuOpen(id, inModal) { return this.state.kindMenu === this.kindMenuKey(id, inModal); }
  toggleKindMenu(id, inModal) {
    const key = this.kindMenuKey(id, inModal);
    this.state.kindMenu = this.state.kindMenu === key ? null : key;
  }

  setCardKind(id, kind) {
    this.state.kindMenu = null;
    const changed = this.cardKind(id) !== kind;
    this.state.kinds[id] = kind;
    // Picking a shape while the card is on its table means the table was not
    // what was wanted: show the shape that was just chosen.
    if (this.cardView(id) !== 'chart') { this.setCardView(id, 'chart'); return; }
    if (changed && this.lastJson) this.renderCard(this.vqCardList.find(c => c.id === id));
  }

  // Re-renders THAT card rather than all four. The container is a plain div the
  // template never fills, so Owl's patch does not touch what was written into
  // it and there is no need to wait for one.
  setCardView(id, mode) {
    if (this.cardView(id) === mode) return;
    this.state.views[id] = mode;
    if (this.lastJson) this.renderCard(this.vqCardList.find(c => c.id === id));
  }

  // Both measures are on screen at once here, so the title says which chart is
  // which instead of following a toggle. Deliberately not an override of the
  // inherited chartTitle(period, kind): same shape, different question.
  vqChartTitle(period, measure) {
    const P = period.toUpperCase();
    return measure === 'amount' ? `${P} – Sales Value Analysis`
                                : `${P} – Sales Qty Analysis`;
  }

  // This card's whole, off the KPI tiles rather than off the rows on screen.
  //
  // The two used to be the same number and are not any more: a ranked level
  // (top ten, no Others) draws part of the total by design, so a share taken
  // against the visible rows would say every top-ten list adds to 100% of
  // itself. Against the tile it says what it means -- these ten are 43.6% of
  // the month -- and on every other level, where the bars DO carry the whole,
  // it is the same figure it always was.
  cardTotal(period, measure) {
    const k = this.lastJson && this.lastJson.kpis;
    if (!k) return 0;
    const isAmount = measure === 'amount';
    return period === 'mtd' ? (isAmount ? k.mtdThisYear : k.mtdQtyThisYear)
                            : (isAmount ? k.ytdThisYear : k.ytdQtyThisYear);
  }

  // The donut's centre held the period total. The card subtitle holds it now,
  // in that chart's own unit, so removing the donut costs the reader nothing.
  vqSubtitle(period, measure) {
    const base = this.chartSubtitle();
    if (!(this.lastJson && this.lastJson.kpis)) return base;
    const fmtT = measure === 'amount' ? fmtM : fmtK;
    return `${base} · ${t('Total')} ${fmtT(this.cardTotal(period, measure))}`;
  }

  _color(style, name, fallback) {
    return style.getPropertyValue(name).trim() || style.getPropertyValue(fallback).trim();
  }

  seriesColors() {
    const style = getComputedStyle(this.rootRef.el || document.documentElement);
    // [Target, This Year, Last Year] — matching attached PDF palette
    return [this._color(style, '--report-target', '--series-3'),
            this._color(style, '--report-this-year', '--series-1'),
            this._color(style, '--report-last-year', '--series-2')];
  }

  // Follows what is actually drawn, matching "Sales Analysis with Salesman".
  chartSubtitle() {
    if (!this.lastJson || this.lastJson.hasBudget !== false) {
      if (this.targetIsAllocated) {
        return `${t('Target, This Year and Last Year')} · ${t('target allocated from')} `
             + `${t(this.lastJson.budgetBasisLabel)} ${t("by last year's mix")}`;
      }
      return t('Target, This Year and Last Year');
    }
    const why = this.lastJson.budgetReason;
    return why ? `${t('This Year and Last Year — no target')}: ${t(why)}`
               : t('This Year and Last Year — no target at this level');
  }

  // Everything the four cards share, worked out once per render: which
  // series exist at this level, their colours, their labels and the rows.
  //
  // Order and colours match "Sales Analysis with Salesman" and the PDF presentation:
  // [Target (#4472C4), A. 2025 (#ED7D31), A. 2024 (#A5A5A5)] when target exists,
  // and [A. 2025 (#ED7D31), A. 2024 (#A5A5A5)] when no target is present.
  chartSpec() {
    const sc = this.seriesColors();
    const noTarget = this.lastJson.hasBudget === false;
    const barColors = noTarget ? [sc[1], sc[2]]
                               : [sc[0], sc[1], sc[2]];   // Target / This Year / Last Year
    const year = this.state.year || (this.lastJson && this.lastJson.year) || 2025;
    const prevYear = year - 1;
    const amtKeys = noTarget ? ['amount', 'prevYearAmount']
                             : ['budgetAmount', 'amount', 'prevYearAmount'];
    const amtLabels = noTarget ? [`A. ${year}`, `A. ${prevYear}`]
                               : [this.targetLabel(t('Target')), `A. ${year}`, `A. ${prevYear}`];
    const qtyKeys = noTarget ? ['qty', 'prevYearQty']
                             : ['budgetQty', 'qty', 'prevYearQty'];
    const qtyLabels = noTarget ? [`A. ${year}`, `A. ${prevYear}`]
                               : [this.targetLabel(t('Target')), `A. ${year}`, `A. ${prevYear}`];
    const onClick = this.state.canDrillFurther
      ? (code, label) => this.onCategoryClick(code, label) : null;
    const { mtd, ytd } = this.lastJson.breakdown;

    return {
      barColors, onClick,
      rows: { mtd, ytd },
      amount: { keys: amtKeys, labels: amtLabels, valueFmt: fmtM, shareKey: 'amount' },
      qty: { keys: qtyKeys, labels: qtyLabels, valueFmt: fmtK, shareKey: 'qty' },
    };
  }

  // What the "Category" column of a table is called: the level the board is
  // currently grouped at, the same word the level nav and the filter above it
  // use. A column headed "Category" while the bars are salesmen would be its
  // own small lie.
  get vqLevelLabel() {
    const lf = this.levelFilterList.find(l => l.v === this.state.level);
    return lf ? lf.l : t('Category');
  }

  renderCard(card) {
    if (!card || !this.refs[card.ref]) return;
    this.renderInto(card, this.refs[card.ref].el);
  }

  // Fills the full-page panel with whatever its card is showing. The chart is
  // drawn taller here rather than scaled up: an SVG stretched to fit would take
  // its captions and value labels with it.
  renderModal() {
    const card = this.modalCard;
    if (!card || !this.refs.modalBody.el) return;
    this.renderInto(card, this.refs.modalBody.el,
                    Math.max(320, Math.round(window.innerHeight * 0.62)));
  }

  renderInto(card, el, height = 230) {
    if (!el || !this.lastJson) return;
    const spec = this.chartSpec();
    const m = spec[card.measure];
    const rows = spec.rows[card.period];
    // Last argument of groupedBarChart is the series the chart shares out:
    // value share on the value cards, quantity share on the quantity ones. A
    // category can be a fifth of the money and a third of the boxes, and saying
    // so is the reason this board exists -- so the table repeats it in its own
    // Share column rather than dropping it on the way over.
    const shareTotal = this.cardTotal(card.period, card.measure);
    // Every shape a card can be on, and the table too: the level menu belongs
    // to the ROW, not to the drawing of it, so switching a card from bars to a
    // pie must not take it away.
    const drillMenu = this.drillMenuSpec;
    if (this.cardView(card.id) === 'table') {
      dataTable(el, rows, m.keys, m.labels, m.shareKey,
                this.vqLevelLabel, spec.onClick, shareTotal, drillMenu);
      return;
    }
    const kind = this.cardKind(card.id);
    if (kind === 'pie') {
      // The share the bars print under their captions IS the pie: one measure,
      // cut up by category, against the same total the card's subtitle names.
      pieChart(el, rows, spec.onClick, m.valueFmt,
               { valueKey: m.shareKey, total: shareTotal, height, drillMenu });
    } else if (kind === 'line' || kind === 'area') {
      lineChart(el, rows, m.keys, spec.barColors, m.labels, spec.onClick,
                m.valueFmt, { shareKey: m.shareKey, height, shareTotal,
                              area: kind === 'area', drillMenu });
    } else {
      groupedBarChart(el, rows, m.keys, spec.barColors, m.labels, spec.onClick,
                      m.valueFmt, { shareKey: m.shareKey, height, shareTotal, drillMenu });
    }
  }

  // The table, as a file. Same columns, same rows, same order and the same
  // total line -- what was on screen is what lands in the spreadsheet, because
  // a download that quietly carries different numbers from the table it came
  // from is worse than no download.
  //
  // Full precision, like the table: this is the copy someone will do their own
  // arithmetic on. The Share column goes with it; recomputing a contribution
  // from rounded exports is how two people end up with two answers.
  downloadCard(id) {
    const card = this.vqCardList.find(c => c.id === id);
    if (!card || !this.lastJson) return;
    const spec = this.chartSpec();
    const m = spec[card.measure];
    const rows = spec.rows[card.period];
    const shareTotal = this.cardTotal(card.period, card.measure);

    const q = v => `"${String(v == null ? '' : v).replace(/"/g, '""')}"`;
    const lines = [[this.vqLevelLabel, ...m.labels.map(l => t(l)), t('Share')]
                   .map(q).join(',')];
    rows.forEach(d => {
      const share = shareTotal ? (d[m.shareKey] || 0) / shareTotal * 100 : null;
      lines.push([d.label, ...m.keys.map(k => Math.round(d[k] || 0)),
                  share == null ? '' : share.toFixed(1)].map(q).join(','));
    });
    const shareSum = rows.reduce((sum, d) => sum + (d[m.shareKey] || 0), 0);
    lines.push([t('Total'),
                ...m.keys.map(k => Math.round(rows.reduce((sum, d) => sum + (d[k] || 0), 0))),
                rows.length && shareTotal
                  ? (shareSum / shareTotal * 100).toFixed(1) : ''].map(q).join(','));

    // BOM first so Excel opens the file as UTF-8 -- customer names carry Arabic
    // script and would otherwise arrive as mojibake. Same reasoning, same
    // handling as the Sales Data Study export.
    const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sales_vq_${card.period}_${card.measure}_${this.state.level}_`
               + `${this.state.year}_${String(this.state.month).padStart(2, '0')}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  renderCharts() {
    this.vqCardList.forEach(card => this.renderCard(card));
    // A reload while the panel is open -- a drill from one of its own rows,
    // say -- has to reach the panel too, and no patch necessarily follows.
    this.renderModal();
  }
}

registry.category("actions").add("pbi_sales_dashboards.sales_vq_dashboard", PbiSalesVqDashboard);
