/** @odoo-module **/
/**
 * ks_print_fix.js
 * Fixes ks_tile layout5 (and ks_kpi) printing — overrides gridstack inline
 * styles and patches the correct DOM class names for each tile type.
 */

const _snaps = [];

function snap(el, css) {
    if (!el) return;
    _snaps.push({ el, orig: el.style.cssText });
    el.style.cssText = css;
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */
function unlockScroll() {
    ['ks_dashboard_main_content','o_content','ks_dashboard_ninja'].forEach(function(c) {
        const el = document.querySelector('.' + c);
        if (el) snap(el, 'overflow:visible!important;height:auto!important;max-height:none!important;width:100%!important;');
    });
}

function isTileItem(content) {
    /* Classes may be on content itself (ks_tile) or a descendant (ks_kpi) */
    var tileClasses = ['ks_dashboard_item_l5','ks_dashboard_kpi','encapsulated-kpi-tile',
                       'custom-layout-1','custom-layout-3','encap-layout-2-box'];
    for (var i = 0; i < tileClasses.length; i++) {
        if (content.classList.contains(tileClasses[i])) return true;
    }
    /* querySelector needs '.' prefix for class selectors */
    return !!content.querySelector('.' + tileClasses.join(',.'));
}

function resetGridStack() {
    document.querySelectorAll('.grid-stack > .grid-stack-item').forEach(function(item) {
        item.classList.remove('ks_print_tile','ks_print_list');
        const content = item.querySelector('.grid-stack-item-content');
        if (!content) return;
        if (isTileItem(content)) {
            item.classList.add('ks_print_tile');
        } else if (content.querySelector('.ks_list_card_body,.ks_list_view_container')) {
            item.classList.add('ks_print_list');
        }
        snap(item, 'position:static!important;transform:none!important;height:auto!important;min-height:0!important;');
    });
    document.querySelectorAll('.grid-stack-item-content').forEach(function(el) {
        snap(el, 'position:static!important;transform:none!important;height:auto!important;max-height:none!important;');
    });
}

/* ── Patch ks_tile layout5 ────────────────────────────────────────────────── */
function patchTileLayout5(root) {
    const bg = root.style.backgroundColor || 'transparent';
    snap(root,
        'background-color:' + bg + '!important;height:130px!important;max-height:135px!important;' +
        'overflow:hidden!important;display:flex!important;flex-direction:column!important;' +
        'justify-content:center!important;align-items:center!important;padding:8px 4px!important;border-radius:10px!important;'
    );

    /* Icon circle */
    const iconCircle = root.querySelector('.ks_dashboard_icon_l5');
    if (iconCircle) {
        snap(iconCircle,
            'position:relative!important;top:auto!important;left:auto!important;' +
            'right:auto!important;bottom:auto!important;z-index:auto!important;' +
            'display:flex!important;align-items:center!important;justify-content:center!important;' +
            'width:50px!important;height:50px!important;min-width:50px!important;min-height:50px!important;' +
            'border-radius:50%!important;background-color:rgba(255,255,255,0.9)!important;' +
            'margin:0 auto 6px auto!important;overflow:visible!important;flex-shrink:0!important;'
        );
        /* FontAwesome glyph - override fa-4x with smaller size */
        const iconSpan = iconCircle.querySelector('span.fa, i.fa');
        if (iconSpan) {
            const origColor = iconSpan.style.color || '#333';
            snap(iconSpan,
                'display:inline-block!important;visibility:visible!important;opacity:1!important;' +
                'font-size:22px!important;line-height:1!important;color:' + origColor + '!important;' +
                'font-family:"FontAwesome","Font Awesome 5 Free","Font Awesome 6 Free",FontAwesome!important;' +
                'font-weight:900!important;'
            );
        }
        const iconImg = iconCircle.querySelector('img');
        if (iconImg) snap(iconImg, 'display:block!important;visibility:visible!important;width:28px!important;height:28px!important;');
    }

    /* Value — ks_tile layout5 specific class */
    const valueEl = root.querySelector('.ks_dashboard_item_domain_count_l5');
    if (valueEl) {
        snap(valueEl,
            'display:block!important;visibility:visible!important;opacity:1!important;' +
            'color:#ffffff!important;font-size:1.4rem!important;font-weight:700!important;' +
            'text-align:center!important;line-height:1.2!important;margin:0 0 2px 0!important;'
        );
        valueEl.querySelectorAll('*').forEach(function(c) {
            snap(c, 'color:#ffffff!important;visibility:visible!important;opacity:1!important;');
        });
    }

    /* Label — ks_tile layout5 specific class */
    const labelEl = root.querySelector('.ks_dashboard_item_name_l5');
    if (labelEl) {
        snap(labelEl,
            'display:block!important;visibility:visible!important;opacity:1!important;' +
            'color:#ffffff!important;font-size:0.68rem!important;text-align:center!important;' +
            'word-break:break-word!important;line-height:1.1!important;'
        );
    }

    /* Hide UI controls */
    root.querySelectorAll('.ks_dashboard_item_header_l2,.select-btn,.ks_img_display').forEach(function(el) {
        snap(el, 'display:none!important;');
    });
}

/* ── Patch ks_tile layout1 (icon left, value+label right) ───────────────── */
function patchTileLayout1(root) {
    const bg = root.style.backgroundColor || 'transparent';
    snap(root,
        'background-color:' + bg + '!important;height:130px!important;max-height:135px!important;' +
        'overflow:hidden!important;display:flex!important;flex-direction:row!important;' +
        'align-items:center!important;padding:8px!important;border-radius:10px!important;'
    );
    const mainBody = root.querySelector('.ks_dashboard_item_main_body.encapsulated-tile-1');
    if (mainBody) snap(mainBody, 'display:flex!important;flex-direction:row!important;align-items:center!important;width:100%!important;');

    const iconDiv = root.querySelector('.ks_dashboard_icon');
    if (iconDiv) {
        snap(iconDiv,
            'display:flex!important;align-items:center!important;justify-content:center!important;' +
            'width:46px!important;height:46px!important;min-width:46px!important;min-height:46px!important;' +
            'border-radius:50%!important;background-color:rgba(255,255,255,0.9)!important;' +
            'margin-right:8px!important;overflow:visible!important;flex-shrink:0!important;'
        );
        const iconSpan = iconDiv.querySelector('span.fa,i.fa');
        if (iconSpan) {
            snap(iconSpan,
                'display:inline-block!important;visibility:visible!important;opacity:1!important;' +
                'font-size:20px!important;line-height:1!important;color:' + (iconSpan.style.color || '#333') + '!important;' +
                'font-family:"FontAwesome","Font Awesome 5 Free","Font Awesome 6 Free",FontAwesome!important;font-weight:900!important;'
            );
        }
    }
    const countEl = root.querySelector('.ks_dashboard_item_domain_count');
    if (countEl) snap(countEl, 'display:block!important;visibility:visible!important;opacity:1!important;font-size:1.2rem!important;font-weight:700!important;line-height:1.2!important;');
    const nameEl = root.querySelector('.ks_dashboard_item_name');
    if (nameEl) snap(nameEl, 'display:block!important;visibility:visible!important;opacity:1!important;font-size:0.62rem!important;line-height:1.1!important;word-break:break-word!important;white-space:normal!important;');
    root.querySelectorAll('.ks_dashboard_item_header,.select-btn,.ks_img_display').forEach(function(el) { snap(el, 'display:none!important;'); });
}

/* ── Patch ks_tile layout2 (value+label left, icon right) ───────────────── */
function patchTileLayout2(root) {
    const bg = root.style.backgroundColor || 'transparent';
    snap(root,
        'background-color:' + bg + '!important;height:130px!important;max-height:135px!important;' +
        'overflow:hidden!important;display:flex!important;flex-direction:row!important;' +
        'align-items:center!important;justify-content:space-between!important;' +
        'padding:8px!important;border-radius:10px!important;'
    );
    const countEl = root.querySelector('.ks_dashboard_item_domain_count_l2');
    if (countEl) snap(countEl, 'display:block!important;visibility:visible!important;opacity:1!important;font-size:1.2rem!important;font-weight:700!important;line-height:1.2!important;margin:0!important;');
    const nameEl = root.querySelector('.ks_dashboard_item_name_l2');
    if (nameEl) snap(nameEl, 'display:block!important;visibility:visible!important;opacity:1!important;font-size:0.62rem!important;line-height:1.1!important;word-break:break-word!important;white-space:normal!important;margin:0!important;');
    const iconDiv = root.querySelector('.ks_dashboard_icon_l2');
    if (iconDiv) {
        snap(iconDiv,
            'display:flex!important;align-items:center!important;justify-content:center!important;' +
            'width:46px!important;height:46px!important;min-width:46px!important;min-height:46px!important;' +
            'border-radius:50%!important;background-color:rgba(255,255,255,0.9)!important;' +
            'padding:0!important;overflow:visible!important;flex-shrink:0!important;'
        );
        const iconSpan = iconDiv.querySelector('span.fa,i.fa,span,i');
        if (iconSpan) {
            snap(iconSpan,
                'display:inline-block!important;visibility:visible!important;opacity:1!important;' +
                'font-size:20px!important;line-height:1!important;color:' + (iconSpan.style.color || '#333') + '!important;' +
                'font-family:"FontAwesome","Font Awesome 5 Free","Font Awesome 6 Free",FontAwesome!important;font-weight:900!important;'
            );
        }
    }
    root.querySelectorAll('.ks_dashboard_item_header_l6,.select-btn,.ks_img_display').forEach(function(el) { snap(el, 'display:none!important;'); });
}

/* ── Patch ks_tile layout3 (icon left, value+label right, solid bg) ─────── */
function patchTileLayout3(root) {
    const bg = root.style.backgroundColor || 'transparent';
    snap(root,
        'background-color:' + bg + '!important;height:130px!important;max-height:135px!important;' +
        'overflow:hidden!important;display:flex!important;flex-direction:row!important;' +
        'align-items:center!important;padding:8px!important;border-radius:10px!important;'
    );
    const mainBody = root.querySelector('.ks_dashboard_item_main_body.encapsulated-main-body');
    if (mainBody) snap(mainBody, 'display:flex!important;flex-direction:row!important;align-items:center!important;width:100%!important;');

    const iconDiv = root.querySelector('.ks_dashboard_icon_l3');
    if (iconDiv) {
        /* overview_main.scss sets position:absolute — pull back into flex flow */
        snap(iconDiv,
            'position:relative!important;top:auto!important;left:auto!important;' +
            'display:flex!important;align-items:center!important;justify-content:center!important;' +
            'width:46px!important;height:46px!important;min-width:46px!important;min-height:46px!important;' +
            'max-width:46px!important;border-radius:50%!important;background-color:rgba(255,255,255,0.9)!important;' +
            'margin-right:8px!important;overflow:visible!important;flex-shrink:0!important;'
        );
        /* inner span is also position:absolute with transform — reset both */
        const iconSpan = iconDiv.querySelector('span,i');
        if (iconSpan) {
            snap(iconSpan,
                'position:static!important;transform:none!important;' +
                'display:inline-block!important;visibility:visible!important;opacity:1!important;' +
                'font-size:20px!important;line-height:1!important;color:' + (iconSpan.style.color || '#333') + '!important;' +
                'font-family:"FontAwesome","Font Awesome 5 Free","Font Awesome 6 Free",FontAwesome!important;font-weight:900!important;'
            );
        }
    }
    const countEl = root.querySelector('.ks_dashboard_item_domain_count_l3');
    if (countEl) snap(countEl, 'display:block!important;visibility:visible!important;opacity:1!important;font-size:1.2rem!important;font-weight:700!important;line-height:1.2!important;text-align:left!important;');
    const nameEl = root.querySelector('.ks_dashboard_item_name_l3');
    if (nameEl) snap(nameEl, 'display:block!important;visibility:visible!important;opacity:1!important;font-size:0.62rem!important;line-height:1.1!important;word-break:break-word!important;white-space:normal!important;text-align:left!important;');
    root.querySelectorAll('.ks_dashboard_item_header,.select-btn,.ks_img_display').forEach(function(el) { snap(el, 'display:none!important;'); });
}

/* ── Patch ks_kpi (Service Analysis style) ───────────────────────────────── */
function patchKpiTile(tile) {
    const item = tile.classList.contains('ks_dashboarditem_id')
        ? tile : tile.querySelector('.ks_dashboarditem_id');
    if (!item) return;

    const bg = item.style.backgroundColor || 'transparent';
    snap(item,
        'background-color:' + bg + '!important;height:130px!important;max-height:135px!important;' +
        'overflow:hidden!important;display:flex!important;flex-direction:column!important;' +
        'justify-content:center!important;align-items:center!important;padding:8px 4px!important;border-radius:10px!important;'
    );

    const iconCircle = item.querySelector('.ks_dashboard_icon_l5');
    if (iconCircle) {
        snap(iconCircle,
            'position:relative!important;top:auto!important;left:auto!important;' +
            'right:auto!important;bottom:auto!important;display:flex!important;' +
            'align-items:center!important;justify-content:center!important;' +
            'width:50px!important;height:50px!important;min-width:50px!important;min-height:50px!important;' +
            'border-radius:50%!important;background-color:rgba(255,255,255,0.9)!important;' +
            'margin:0 auto 6px auto!important;overflow:visible!important;flex-shrink:0!important;'
        );
        const iconSpan = iconCircle.querySelector('span.fa,i.fa,span,i');
        if (iconSpan) {
            snap(iconSpan,
                'display:inline-block!important;visibility:visible!important;opacity:1!important;' +
                'font-size:22px!important;line-height:1!important;color:#333!important;' +
                'font-family:"FontAwesome","Font Awesome 5 Free","Font Awesome 6 Free",FontAwesome!important;' +
                'font-weight:900!important;'
            );
        }
    }

    const count = item.querySelector('.ks_dashboard_kpi_count_preview');
    if (count) {
        snap(count, 'display:block!important;visibility:visible!important;opacity:1!important;color:#000!important;font-size:1.3rem!important;font-weight:700!important;text-align:center!important;line-height:1.2!important;');
        count.querySelectorAll('*').forEach(function(c) { snap(c, 'color:#000!important;visibility:visible!important;'); });
    }

    const label = item.querySelector('.ks_dashboard_kpi_name_preview');
    if (label) snap(label, 'display:block!important;visibility:visible!important;opacity:1!important;color:#000!important;font-size:0.68rem!important;text-align:center!important;');
}

/* ── Main beforeprint ─────────────────────────────────────────────────────── */
function beforePrint() {
    _snaps.length = 0;
    unlockScroll();
    resetGridStack();

    /* Patch ks_tile layout1, 2, 3 (contract dashboard style) */
    document.querySelectorAll('.custom-layout-1').forEach(function(root) { patchTileLayout1(root); });
    document.querySelectorAll('.encap-layout-2-box').forEach(function(root) { patchTileLayout2(root); });
    document.querySelectorAll('.custom-layout-3').forEach(function(root) { patchTileLayout3(root); });

    /* Patch layout5 tiles (ks_tile type) */
    document.querySelectorAll('.ks_dashboard_item_l5').forEach(function(root) {
        patchTileLayout5(root);
    });

    /* Patch KPI tiles (ks_kpi type - encapsulated-kpi-tile wrapper) */
    document.querySelectorAll('.ks_dashboard_kpi').forEach(function(tile) {
        patchKpiTile(tile);
    });
}

function afterPrint() {
    document.querySelectorAll('.ks_print_tile,.ks_print_list').forEach(function(el) {
        el.classList.remove('ks_print_tile','ks_print_list');
    });
    _snaps.forEach(function(s) { s.el.style.cssText = s.orig; });
    _snaps.length = 0;
}

window.addEventListener('beforeprint', beforePrint);
window.addEventListener('afterprint', afterPrint);
