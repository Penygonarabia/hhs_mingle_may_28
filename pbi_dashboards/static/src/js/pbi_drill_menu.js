/** @odoo-module **/

/*
 * The drill menu: right-click a mark on a chart (or long-press it on a phone)
 * and pick which of the OTHER levels to open it at.
 *
 * A left-click on a bar has always drilled one step -- into the next level of
 * the chain -- and it still does. That is the fast path and it is unchanged.
 * What it could not do is reach level 7 from level 1 without six clicks, or
 * ask the reverse question ("this salesman, by region"), and both are one
 * gesture here: the mark says WHICH row, the menu says WHICH LEVEL to open it
 * at, and the board applies the two together.
 *
 * Written against nothing but the DOM, so any board with `data-code` marks can
 * attach it -- the two sales boards that use it today (sales_sman_dashboard.js
 * and the VQ board that extends it) pass their ten levels and their own
 * handler; nothing about the chain is known here.
 *
 * The menu is appended to <body>, not to the chart: every chart on these
 * boards sits inside a `.chart-scroll` with `overflow-x: auto`, and a menu
 * inside one would be clipped at the card's edge or, worse, extend the card's
 * scroll width. Body-level means it also carries its own colours rather than
 * inheriting the board's custom properties -- see pbi_drill_menu.css.
 */

import { t } from "./pbi_i18n";

// Long enough that a press-and-drag to scroll the chart does not trip it,
// short enough to feel like the platform's own long-press. Between the two,
// Android's ~500ms and iOS's ~450ms.
const LONG_PRESS_MS = 480;
// A finger never holds perfectly still. Past this, the gesture was a scroll.
const MOVE_TOLERANCE_PX = 12;
// Below this the menu is a bottom sheet rather than a popup at the pointer --
// same breakpoint the two boards already use for their KPI tiles.
const PHONE_MAX_PX = 600;

let layerEl = null;
let layerCleanup = null;
// Set by a long-press. The synthetic click that follows the touch would
// otherwise ALSO drill one level, so the board would move under the menu that
// just opened. Enforced by one document-level capture listener, installed once.
let suppressClickUntil = 0;
let clickGuardInstalled = false;

function installClickGuard() {
  if (clickGuardInstalled) return;
  clickGuardInstalled = true;
  document.addEventListener('click', ev => {
    if (Date.now() >= suppressClickUntil) return;
    // The menu's own buttons are exempt: the guard exists to swallow the click
    // that ENDED the long press, not the tap that answers the menu it opened.
    if (ev.target.closest && ev.target.closest('.pbi-drill-layer')) return;
    ev.stopPropagation();
    ev.preventDefault();
  }, true);
}

const isPhone = () => window.innerWidth <= PHONE_MAX_PX;

function node(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  // textContent, never innerHTML: every label here is a database value --
  // customer and city names carrying "&", quotes and Arabic script.
  if (text != null) n.textContent = text;
  return n;
}

export function closeDrillMenu() {
  if (layerCleanup) layerCleanup();
  layerCleanup = null;
  if (layerEl && layerEl.parentNode) layerEl.parentNode.removeChild(layerEl);
  layerEl = null;
}

export function isDrillMenuOpen() { return !!layerEl; }

/*
 * opts:
 *   x, y            where the gesture happened, in client coordinates
 *   code, label     the row the mark stands for
 *   valueText       that row's figure, already formatted (optional)
 *   color           the mark's own colour, so the menu names the bar it came
 *                   from by sight and not only by word
 *   levels          [{v, l}] every level of the chain, in drill order
 *   currentLevel    where the board is now; excluded from the list, since
 *                   opening this row at its own level draws one bar
 *   omit            levels to leave out for the same reason -- ones the board
 *                   has already pinned to a single value. They stay in
 *                   `levels`, so the numbering still counts the whole chain
 *   activeDrills    [{level, levelLabel, code, label, num}] currently narrowed /
 *                   drilled levels
 *   currentLabel    that level's name, for the header line
 *   onPick(level)   apply
 *   onJump(level)   jump to level tab
 *   onRelease(level) release filter condition
 *   dir             'rtl' | 'ltr', taken from the board
 */
export function openDrillMenu(opts) {
  closeDrillMenu();
  const { levels = [], currentLevel, onPick, onJump, onRelease } = opts;
  const idx = levels.findIndex(l => l.v === currentLevel);
  // `levels` stays whole -- the numbers beside the entries count positions in
  // the chain, and renumbering them as the reader narrows would make the one
  // thing the list is FOR, showing how far a jump is, move underfoot.
  let currentOmit = new Set(opts.omit || []);
  let currentActiveDrills = [...(opts.activeDrills || [])];

  const below = levels.filter((l, i) => i > idx && !currentOmit.has(l.v));
  const above = levels.filter((l, i) => i < idx && !currentOmit.has(l.v));
  if (!below.length && !above.length && !currentActiveDrills.length) return;

  const phone = isPhone();
  const layer = node('div', 'pbi-drill-layer' + (phone ? ' as-sheet' : ''));
  layer.dir = opts.dir || 'ltr';
  const backdrop = node('div', 'pbi-drill-backdrop');
  const menu = node('div', 'pbi-drill-menu');
  menu.setAttribute('role', 'menu');
  menu.tabIndex = -1;

  // Head: which row was picked, at which level, and what it is worth. Without
  // it a list of ten level names says nothing about what it would apply to --
  // and on a chart of fifteen bars, "which one did I press" is a real question.
  const head = node('div', 'pbi-drill-head');
  const dot = node('span', 'dot');
  if (opts.color) dot.style.background = opts.color;
  head.appendChild(dot);
  const headText = node('div', 'txt');
  headText.appendChild(node('div', 'name', opts.label));
  const metaBits = [];
  if (opts.currentLabel) metaBits.push(opts.currentLabel);
  if (opts.valueText) metaBits.push(opts.valueText);
  if (metaBits.length) headText.appendChild(node('div', 'meta', metaBits.join(' · ')));
  head.appendChild(headText);
  const closeBtn = node('button', 'pbi-drill-close', '×');
  closeBtn.type = 'button';
  closeBtn.setAttribute('aria-label', t('Close'));
  closeBtn.addEventListener('click', closeDrillMenu);
  head.appendChild(closeBtn);
  menu.appendChild(head);

  // Active Drills Section at the top (under head)
  const activeSection = node('div', 'pbi-drill-active');
  menu.appendChild(activeSection);

  const body = node('div', 'pbi-drill-body');
  menu.appendChild(body);

  let items = [];

  const renderContent = () => {
    // 1. Render active drilled levels at top
    activeSection.innerHTML = '';
    if (currentActiveDrills.length > 0) {
      activeSection.style.display = '';
      activeSection.appendChild(node('div', 'pbi-drill-active-title', t('Drilled levels')));
      const list = node('div', 'pbi-drill-active-list');
      currentActiveDrills.forEach(item => {
        const chip = node('div', 'pbi-drill-active-chip');
        const btn = node('button', 'pbi-drill-chip-btn');
        btn.type = 'button';
        btn.title = `${t('Open')} ${item.levelLabel}`;
        btn.appendChild(node('span', 'num', String(item.num)));
        const kSpan = node('span', 'k', item.levelLabel + ':');
        const vSpan = node('span', 'v', item.label);
        btn.appendChild(kSpan);
        btn.appendChild(vSpan);
        btn.addEventListener('click', () => {
          closeDrillMenu();
          if (onJump) onJump(item.level);
        });

        const xBtn = node('button', 'pbi-drill-chip-x', '×');
        xBtn.type = 'button';
        xBtn.title = `${t('Release filter')} — ${item.levelLabel}`;
        xBtn.setAttribute('aria-label', `${t('Release filter')} — ${item.levelLabel}`);
        xBtn.addEventListener('click', ev => {
          ev.stopPropagation();
          const targetLevel = item.level;
          currentActiveDrills = currentActiveDrills.filter(d => d.level !== targetLevel);
          currentOmit.delete(targetLevel);
          if (onRelease) onRelease(targetLevel);
          renderContent();
          if (!phone) placeAtPointer(menu, opts.x, opts.y, layer.dir === 'rtl');
        });

        chip.appendChild(btn);
        chip.appendChild(xBtn);
        list.appendChild(chip);
      });
      activeSection.appendChild(list);
    } else {
      activeSection.style.display = 'none';
    }

    // 2. Render available levels below
    body.innerHTML = '';
    items = [];
    const curBelow = levels.filter((l, i) => i > idx && !currentOmit.has(l.v));
    const curAbove = levels.filter((l, i) => i < idx && !currentOmit.has(l.v));

    const addGroup = (title, list, kind) => {
      if (!list.length) return;
      body.appendChild(node('div', 'pbi-drill-group', title));
      list.forEach(lv => {
        const btn = node('button', 'pbi-drill-item' + (kind === 'up' ? ' up' : ''));
        btn.type = 'button';
        btn.setAttribute('role', 'menuitem');
        // Its position in the chain, 1-10. The chain is the thing being
        // navigated, and a bare list of ten names does not show how far a jump
        // is; the number does, in the space of one character.
        btn.appendChild(node('span', 'num', String(levels.findIndex(l => l.v === lv.v) + 1)));
        btn.appendChild(node('span', 'lbl', lv.l));
        // The one level a plain left-click already reaches. Marked so the menu
        // teaches the shortcut rather than replacing it.
        if (kind === 'down' && levels[idx + 1] && levels[idx + 1].v === lv.v) {
          btn.appendChild(node('span', 'badge', t('Next')));
        }
        btn.addEventListener('click', () => {
          closeDrillMenu();
          if (onPick) onPick(lv.v);
        });
        items.push(btn);
        body.appendChild(btn);
      });
    };

    addGroup(t('Drill down to'), curBelow, 'down');
    // The levels ABOVE the current one are a different question, not a drill:
    // "this salesman, by region" rather than "this region, by salesman". The
    // board answers both the same way -- the row filters, the level groups --
    // so they belong in one menu under two headings, not in two menus.
    addGroup(t('Break down by'), curAbove, 'up');
  };

  renderContent();

  if (phone) {
    // A sheet needs a way out that is not "tap the small × in the corner" or
    // "tap the strip of backdrop above me".
    const cancel = node('button', 'pbi-drill-cancel', t('Cancel'));
    cancel.type = 'button';
    cancel.addEventListener('click', closeDrillMenu);
    menu.appendChild(cancel);
  }

  layer.appendChild(backdrop);
  layer.appendChild(menu);
  document.body.appendChild(layer);
  layerEl = layer;

  if (!phone) placeAtPointer(menu, opts.x, opts.y, layer.dir === 'rtl');

  backdrop.addEventListener('click', closeDrillMenu);
  // contextmenu ON the backdrop: a second right-click outside the menu should
  // dismiss it, not raise the browser's own menu over ours.
  backdrop.addEventListener('contextmenu', ev => { ev.preventDefault(); closeDrillMenu(); });

  const onKey = ev => {
    if (ev.key === 'Escape') { ev.stopPropagation(); closeDrillMenu(); return; }
    if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
    ev.preventDefault();
    const here = items.indexOf(document.activeElement);
    const step = ev.key === 'ArrowDown' ? 1 : -1;
    const next = (here + step + items.length) % items.length;
    if (items[next]) items[next].focus();
  };
  // Anything that moves the board out from under the menu closes it: the menu
  // is anchored to a pointer position that no longer means anything.
  const onAway = () => closeDrillMenu();
  document.addEventListener('keydown', onKey, true);
  window.addEventListener('resize', onAway);
  // Capture, so a scroll inside the card's own scroller counts too.
  window.addEventListener('scroll', onAway, true);
  layerCleanup = () => {
    document.removeEventListener('keydown', onKey, true);
    window.removeEventListener('resize', onAway);
    window.removeEventListener('scroll', onAway, true);
  };

  if (items.length) items[0].focus({ preventScroll: true });
}

// Beside the pointer, and inside the window. Opens away from the cursor on the
// side there is room for it, which on an RTL board is the other side by
// default -- the menu should not have to cross the pointer to be read.
function placeAtPointer(menu, x, y, rtl) {
  const pad = 8;
  const w = menu.offsetWidth, h = menu.offsetHeight;
  const vw = window.innerWidth, vh = window.innerHeight;
  let left = rtl ? x - w - 4 : x + 4;
  if (left + w > vw - pad) left = x - w - 4;
  if (left < pad) left = Math.min(pad, Math.max(pad, vw - w - pad));
  let top = y + 4;
  if (top + h > vh - pad) top = y - h - 4;
  if (top < pad) top = pad;
  menu.style.left = Math.round(left) + 'px';
  menu.style.top = Math.round(top) + 'px';
}

/*
 * Bind the menu to every mark in `container` that carries a data-code.
 *
 * Called after each render, on freshly written nodes, exactly like the click
 * and tooltip binders beside it -- innerHTML has just replaced everything, so
 * there is nothing to unbind.
 *
 * spec:
 *   levels, currentLevel, currentLabel, onPick(code, label, level)
 *   contextFor(code) -> { label, valueText, color } | null
 *       null for a mark that is not a real, drillable row -- an "Others"
 *       roll-up, say. Returning it suppresses the menu on that mark rather
 *       than opening one whose every choice would be a lie.
 *   selector  defaults to '[data-code]', which on these charts is the rect or
 *       wedge AND its caption: right-clicking the word under a bar is the same
 *       gesture as right-clicking the bar.
 */
export function attachDrillMenu(container, spec) {
  if (!container || !spec || !spec.levels || !spec.onPick) return;
  installClickGuard();
  // Marks the surface a long press is meaningful on. What it buys is in the
  // CSS: iOS raises its own Copy / Look Up callout on a long press that lands
  // on selectable text, and a chart is mostly axis ticks, value labels and
  // captions -- so a press that misses a thin bar by a few points answered
  // with a text-selection sheet over the chart instead of the level list.
  // Seen on an iPhone 15 Pro Max against the "0M" axis label.
  container.classList.add('pbi-drill-surface');
  const selector = spec.selector || '[data-code]';
  const dir = (container.closest && container.closest('[dir]'))
    ? container.closest('[dir]').getAttribute('dir') : 'ltr';

  const open = (code, x, y) => {
    const ctx = spec.contextFor ? spec.contextFor(code) : null;
    if (!ctx) return false;
    openDrillMenu({
      x, y, dir,
      code, label: ctx.label, valueText: ctx.valueText, color: ctx.color,
      levels: spec.levels, currentLevel: spec.currentLevel,
      currentLabel: spec.currentLabel, omit: spec.omit,
      activeDrills: spec.activeDrills,
      onPick: level => spec.onPick(code, ctx.label, level),
      onJump: level => spec.onJump && spec.onJump(level),
      onRelease: level => spec.onRelease && spec.onRelease(level),
    });
    return true;
  };

  container.querySelectorAll(selector).forEach(mark => {
    const code = mark.getAttribute('data-code');
    if (code == null) return;
    mark.classList.add('pbi-drillable');

    // Desktop: the platform gesture for "what else can this do".
    mark.addEventListener('contextmenu', ev => {
      // Suppress the browser menu whether or not we open ours -- on an
      // "Others" bar, offering Save Image As over a chart is not an
      // improvement, and the mark has already said it is not drillable.
      ev.preventDefault();
      ev.stopPropagation();
      // A touch long-press raises contextmenu too on most mobile browsers,
      // after our own timer has already opened the menu. Do not open twice.
      if (Date.now() < suppressClickUntil) return;
      open(code, ev.clientX, ev.clientY);
    });

    // Touch and pen: press and hold. Never the mouse -- holding a mouse button
    // down is a drag, and a menu appearing mid-drag is a bug, not a feature.
    let timer = null, startX = 0, startY = 0;
    const cancel = () => { if (timer) { clearTimeout(timer); timer = null; } };
    mark.addEventListener('pointerdown', ev => {
      if (ev.pointerType === 'mouse') return;
      startX = ev.clientX; startY = ev.clientY;
      cancel();
      timer = setTimeout(() => {
        timer = null;
        if (!open(code, startX, startY)) return;
        // Both the synthetic click this touch will produce and, right behind
        // it, the contextmenu some mobile browsers raise from the same press.
        suppressClickUntil = Date.now() + 900;
        // The platform's own signal that a long-press registered. Absent on
        // iOS, where it is simply a no-op.
        if (navigator.vibrate) navigator.vibrate(12);
      }, LONG_PRESS_MS);
    });
    mark.addEventListener('pointermove', ev => {
      if (!timer) return;
      if (Math.abs(ev.clientX - startX) > MOVE_TOLERANCE_PX ||
          Math.abs(ev.clientY - startY) > MOVE_TOLERANCE_PX) cancel();
    });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(
      e => mark.addEventListener(e, cancel));
  });
}
