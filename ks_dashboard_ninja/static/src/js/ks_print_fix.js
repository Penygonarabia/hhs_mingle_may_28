/** @odoo-module **/

/**
 * ks_print_fix.js
 *
 * Fixes KPI tile rendering during browser print (Ctrl+P / window.print()).
 */

/** Store original inline styles so we can restore them after print */
const _snapshots = [];

/**
 * Save an element's current inline style string and apply a new one.
 * @param {HTMLElement} el
 * @param {string} newStyle  CSS text to apply (replaces cssText)
 */
function patchStyle(el, newStyle) {
    _snapshots.push({ el, original: el.style.cssText });
    el.style.cssText = newStyle;
}

/**
 * Called just before the browser renders the print preview.
 * Iterates every KPI tile and forces legible layout + colours.
 */
function beforePrint() {
    _snapshots.length = 0;   // clear previous snapshots

    /* ── 1. Page-level resets ─────────────────────────────────────────── */
    const content = document.querySelector('.ks_dashboard_main_content');
    if (content) {
        patchStyle(content, 'overflow:visible!important;height:auto!important;max-height:none!important;');
    }

    /* ── 2. Per-tile patches ──────────────────────────────────────────── */
    const tiles = document.querySelectorAll('.ks_dashboard_kpi');
    tiles.forEach(function (tile) {

        /* The actual KPI item element (has the inline background + font-color) */
        const item = tile.classList.contains('ks_dashboarditem_id')
            ? tile
            : tile.querySelector('.ks_dashboarditem_id');

        if (!item) return;

        /* Read the current computed background colour so we keep it */
        const bgColor = item.style.backgroundColor || 'transparent';

        /* ── Tile wrapper (grid-stack-item-content) ── */
        patchStyle(item,
            'background-color:' + bgColor + '!important;' +
            'color:#000000!important;' +              // override white font
            'height:auto!important;' +
            'max-height:none!important;' +
            'overflow:visible!important;' +
            'position:relative!important;' +
            'display:flex!important;' +
            'flex-direction:column!important;' +
            'justify-content:center!important;' +
            'align-items:center!important;' +
            'padding:8px!important;'
        );

        /* ── Icon container (position:absolute → relative) ── */
        const iconEl = item.querySelector('.ks_dashboard_icon_l5');
        if (iconEl) {
            patchStyle(iconEl,
                'position:relative!important;' +
                'top:auto!important;left:auto!important;' +
                'right:auto!important;bottom:auto!important;' +
                'z-index:auto!important;' +
                'display:flex!important;' +
                'align-items:center!important;' +
                'justify-content:center!important;' +
                'width:52px!important;height:52px!important;' +
                'min-width:52px!important;min-height:52px!important;' +
                'border-radius:50%!important;' +
                'background-color:rgba(255,255,255,0.9)!important;' +
                'margin:4px auto 6px auto!important;' +
                'overflow:visible!important;' +
                'flex-shrink:0!important;'
            );

            /* Icon <span> / <i> — force the FA glyph colour to be visible */
            const iconSpan = iconEl.querySelector('span, i');
            if (iconSpan) {
                patchStyle(iconSpan,
                    'display:inline-block!important;' +
                    'visibility:visible!important;' +
                    'opacity:1!important;' +
                    'color:#333333!important;' +   // dark icon on white circle
                    'font-size:20px!important;' +
                    'line-height:1!important;' +
                    'font-family:"FontAwesome", "Font Awesome 5 Free", "Font Awesome 6 Free", FontAwesome!important;' +
                    'font-weight:900!important;'
                );
            }

            /* Custom image icon */
            const iconImg = iconEl.querySelector('img');
            if (iconImg) {
                patchStyle(iconImg,
                    'display:block!important;' +
                    'visibility:visible!important;' +
                    'width:28px!important;height:28px!important;'
                );
            }
        }

        /* ── Count / value ── */
        const countEl = item.querySelector('.ks_dashboard_kpi_count_preview');
        if (countEl) {
            patchStyle(countEl,
                'display:block!important;' +
                'visibility:visible!important;' +
                'opacity:1!important;' +
                'color:#000000!important;' +
                'font-size:1.3rem!important;' +
                'font-weight:700!important;' +
                'text-align:center!important;' +
                'line-height:1.2!important;' +
                'margin:2px 0!important;'
            );
            /* Override children too (t-esc generates a text node, but span may exist) */
            countEl.querySelectorAll('*').forEach(function (c) {
                patchStyle(c, 'color:#000000!important;display:inline!important;visibility:visible!important;opacity:1!important;');
            });
        }

        /* ── KPI name / label ── */
        const nameEl = item.querySelector('.ks_dashboard_kpi_name_preview');
        if (nameEl) {
            patchStyle(nameEl,
                'display:block!important;' +
                'visibility:visible!important;' +
                'opacity:1!important;' +
                'color:#000000!important;' +
                'font-size:0.75rem!important;' +
                'text-align:center!important;' +
                'word-break:break-word!important;'
            );
        }

        /* ── vs Prev / vs Target ── */
        ['var-prev', 'pre_deviation', 'target_deviation'].forEach(function (cls) {
            const el = item.querySelector('.' + cls);
            if (el) {
                patchStyle(el,
                    'display:block!important;' +
                    'visibility:visible!important;' +
                    'opacity:1!important;' +
                    'color:#000000!important;' +
                    'font-size:0.7rem!important;' +
                    'text-align:center!important;'
                );
                /* Also fix any child divs that may have inline colour */
                el.querySelectorAll('*').forEach(function (c) {
                    patchStyle(c, 'color:#000000!important;');
                });
            }
        });

        /* ── flex-container (count + vs-prev row) ── */
        const flexEl = item.querySelector('.flex-container');
        if (flexEl) {
            patchStyle(flexEl,
                'display:flex!important;' +
                'flex-direction:row!important;' +
                'justify-content:center!important;' +
                'align-items:center!important;' +
                'gap:8px!important;flex-wrap:wrap!important;'
            );
        }

        /* ── Main body wrapper ── */
        const bodyEl = item.querySelector('.ks_dashboard_item_main_body_l5');
        if (bodyEl) {
            patchStyle(bodyEl,
                'display:flex!important;' +
                'flex-direction:column!important;' +
                'align-items:center!important;' +
                'width:100%!important;'
            );
        }

        /* ── Hide UI-only controls ── */
        ['.ks_dashboard_item_header_l6', '.select-btn', '.ks_img_display'].forEach(function (sel) {
            const el = item.querySelector(sel);
            if (el) patchStyle(el, 'display:none!important;');
        });
    });
}

/**
 * Called after the print dialog closes.
 * Restores every element's original inline style.
 */
function afterPrint() {
    _snapshots.forEach(function (s) {
        s.el.style.cssText = s.original;
    });
    _snapshots.length = 0;
}

/* Register the hooks */
window.addEventListener('beforeprint', beforePrint);
window.addEventListener('afterprint', afterPrint);
