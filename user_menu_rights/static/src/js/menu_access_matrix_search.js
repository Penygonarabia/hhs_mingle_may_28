/** @odoo-module **/

/**
 * Live search filter + expand/collapse for the Menu Access Rights matrix's
 * tree.
 *
 * Search follows a pattern already proven on this exact Odoo build: this
 * custom list renderer reads the search input's live DOM value (scoped
 * under .mar_matrix_form so it can never pick up an unrelated page's search
 * box) to decide which rows to hide. The input is deliberately a plain DOM
 * <input>, not an Odoo field —
 * see the view arch for why.
 *
 * Expand/collapse uses manual render() rather than useState, since it's the
 * renderer itself (not a field widget) that owns both the toggle click and
 * the row-hiding decision. Its state lives in MAR_STATE (below), not on the
 * component, so it survives Owl re-creating this renderer.
 *
 * Both are purely display filters — neither touches has_access or triggers
 * any write, so neither can affect what gets saved.
 *
 * PERFORMANCE NOTE: getRowClass runs once per row, and this list is ~760
 * rows. Anything done per-row is multiplied by that on EVERY render, so
 * two things are deliberately avoided here:
 *   - re-running document.querySelector for the search box per row (the
 *     element is cached instead), and
 *   - scanning all records per row to find matching ancestors/descendants,
 *     which made typing O(rows²) — ~580k string compares per keystroke,
 *     the reported "typing is slow". Match data is computed ONCE per
 *     (query, row-count) into prefix Sets, then every per-row question is
 *     an O(depth) Set lookup. Typing is also debounced.
 *
 * Registered ONLY as the widget on menu.access.matrix's line_ids field
 * (see views/menu_access_matrix_views.xml, widget="mar_matrix_list_field"),
 * so this file can only ever run while that one form is open.
 */

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import {
    BooleanToggleField,
    booleanToggleField,
} from "@web/views/fields/boolean_toggle/boolean_toggle_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { onMounted, onWillUnmount, onPatched, xml } from "@odoo/owl";

const MAR_SEARCH_SELECTOR = ".mar_matrix_form .mar_search_box";
const MAR_EXPAND_ALL_SELECTOR = ".mar_matrix_form .mar_expand_all";
const MAR_COLLAPSE_ALL_SELECTOR = ".mar_matrix_form .mar_collapse_all";
const MAR_TREE_WRAP_SELECTOR = ".mar_matrix_form .mar_tree_wrap";
const MAR_SEARCH_DEBOUNCE_MS = 180;

/**
 * Expand/collapse state, held outside the component AND outside the list.
 *
 * Owl can tear down and re-create this renderer while the user is working,
 * and a toggle now reloads the whole form (see MarAccessToggleField), which
 * hands the renderer a brand-new list object with brand-new record ids.
 * Keying the state on the list (a WeakMap) therefore threw the user's
 * expand/collapse away on every single tick — the tree snapped back to
 * fully-folded under their cursor. Keying on the row COUNT instead survives
 * a reload of the same tree, while still resetting when a different user's
 * tree (a different number of rows) is loaded.
 */
let MAR_STATE = null;

function marGetState(list) {
    const count = list.records.length;
    if (!MAR_STATE || MAR_STATE.count !== count) {
        MAR_STATE = { collapsed: new Set(), lastQuery: "", count };
        for (const r of list.records) {
            if (r.data.is_group && r.data.menu_path) {
                MAR_STATE.collapsed.add(r.data.menu_path);
            }
        }
    }
    return MAR_STATE;
}

/**
 * Scroll offset of the tree panel, held across a reload.
 *
 * A toggle reloads the whole form, which tears the tree's rows out of the DOM
 * and puts new ones back. While the container is briefly short, the browser
 * clamps scrollTop, so restoring once — even in a single requestAnimationFrame
 * — lands on a container that has not finished settling and the panel ends up
 * at the bottom. The value is therefore parked here, re-applied on every frame
 * until it sticks, and re-applied again from the renderer's onPatched (Owl
 * re-renders asynchronously, so the patch can land after the frames run out).
 */
let MAR_PENDING_SCROLL = null;
let MAR_SCROLL_FRAME = null;

function marRememberScrollTop() {
    const wrap = document.querySelector(MAR_TREE_WRAP_SELECTOR);
    MAR_PENDING_SCROLL = wrap ? wrap.scrollTop : null;
}

function marApplyPendingScroll() {
    // A second caller must not start a competing loop — they would fight over
    // scrollTop and the last writer would win at a random frame.
    if (MAR_PENDING_SCROLL === null || MAR_SCROLL_FRAME !== null) {
        return;
    }
    const target = MAR_PENDING_SCROLL;
    let frames = 0;
    const apply = () => {
        const wrap = document.querySelector(MAR_TREE_WRAP_SELECTOR);
        if (wrap && wrap.scrollTop !== target) {
            wrap.scrollTop = target;
        }
        if (++frames < 10) {
            MAR_SCROLL_FRAME = requestAnimationFrame(apply);
        } else {
            MAR_SCROLL_FRAME = null;
            MAR_PENDING_SCROLL = null;
        }
    };
    MAR_SCROLL_FRAME = requestAnimationFrame(apply);
}

/**
 * Strict ancestor paths of a materialized path.
 * "/12/45/302/" -> ["/12/", "/12/45/"]  (excludes the path itself)
 */
function marAncestorPaths(path) {
    const ids = path.split("/").filter(Boolean);
    const out = [];
    for (let i = 1; i < ids.length; i++) {
        out.push(`/${ids.slice(0, i).join("/")}/`);
    }
    return out;
}

/**
 * Helper to copy text to the clipboard. Supports both secure (navigator.clipboard)
 * and non-secure (document.execCommand) contexts.
 */
function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text);
    } else {
        return new Promise((resolve, reject) => {
            try {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.left = '-9999px';
                textarea.style.top = '-9999px';
                document.body.appendChild(textarea);
                textarea.focus();
                textarea.select();
                const successful = document.execCommand('copy');
                document.body.removeChild(textarea);
                if (successful) {
                    resolve();
                } else {
                    reject(new Error('execCommand copy was unsuccessful'));
                }
            } catch (err) {
                reject(err);
            }
        });
    }
}

/**
 * Searches for the active Odoo breadcrumb or page title, parses the user's
 * email, and appends a clickable copy button with visual feedback.
 */
function updateHeaderCopyIcon() {
    const selectors = [
        '.o_last_breadcrumb_item',
        '.breadcrumb-item.active',
        '.o_control_panel_breadcrumbs .active',
        '.o_control_panel_title',
        '.o_breadcrumb .active'
    ];
    let titleEl = null;
    for (const selector of selectors) {
        titleEl = document.querySelector(selector);
        if (titleEl) break;
    }
    if (!titleEl) return;

    // Avoid duplicating copy button
    if (titleEl.querySelector('.mar_copy_email_btn')) return;

    const fullText = (titleEl.textContent || '').trim();
    if (!fullText.includes('Menu Access Rights -')) return;

    const parts = fullText.split(' / ');
    if (parts.length < 2) return;

    const email = parts[parts.length - 1].trim();
    if (!email || !email.includes('@')) return;

    const btn = document.createElement('span');
    btn.className = 'mar_copy_email_btn';
    btn.setAttribute('title', 'Copy Email');
    btn.innerHTML = '<i class="fa fa-copy"></i>';

    // Completely isolate button events from Odoo's handlers
    const preventAndStop = (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        ev.stopImmediatePropagation();
    };
    btn.addEventListener('click', (ev) => {
        preventAndStop(ev);
        copyToClipboard(email).then(() => {
            const icon = btn.querySelector('.fa');
            if (icon) {
                icon.className = 'fa fa-check';
                setTimeout(() => {
                    icon.className = 'fa fa-copy';
                }, 1500);
            }
        }).catch(err => {
            console.error('Clipboard copy failed:', err);
        });
    });
    btn.addEventListener('mousedown', preventAndStop);
    btn.addEventListener('mouseup', preventAndStop);

    titleEl.appendChild(btn);
}

class MenuAccessMatrixListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this._matchCache = null;
        this._titleObserver = null;

        this._onSearchInput = () => {
            clearTimeout(this._searchTimer);
            this._searchTimer = setTimeout(() => this._applySearch(), MAR_SEARCH_DEBOUNCE_MS);
        };
        // preventDefault: these are <a href="#"> (see the view arch's
        // comment for why not a real <button>) — without this, the click
        // would also change window.location.hash to "#", stomping on
        // Odoo's own hash-based routing state.
        this._onExpandAll = (ev) => {
            ev.preventDefault();
            this.expandAll();
        };
        this._onCollapseAll = (ev) => {
            ev.preventDefault();
            this.collapseAll();
        };
        onMounted(() => {
            this._searchEl = document.querySelector(MAR_SEARCH_SELECTOR);
            if (this._searchEl) {
                this._searchEl.addEventListener("input", this._onSearchInput);
            }
            this._expandAllEl = document.querySelector(MAR_EXPAND_ALL_SELECTOR);
            if (this._expandAllEl) {
                this._expandAllEl.addEventListener("click", this._onExpandAll);
            }
            this._collapseAllEl = document.querySelector(MAR_COLLAPSE_ALL_SELECTOR);
            if (this._collapseAllEl) {
                this._collapseAllEl.addEventListener("click", this._onCollapseAll);
            }

            // Set up MutationObserver to watch for title changes in the DOM and inject/re-inject copy button
            if (typeof MutationObserver !== 'undefined') {
                const targetNode = document.body;
                const config = { childList: true, subtree: true, characterData: true };
                const callback = () => {
                    updateHeaderCopyIcon();
                };
                this._titleObserver = new MutationObserver(callback);
                this._titleObserver.observe(targetNode, config);
            }
            updateHeaderCopyIcon();
        });
        // The reload after a toggle finishes as an Owl patch, which can land
        // after marApplyPendingScroll's frames have run out. Re-arming here is
        // what makes the restore reliable rather than racy.
        onPatched(() => marApplyPendingScroll());
        onWillUnmount(() => {
            clearTimeout(this._searchTimer);
            if (this._searchEl) {
                this._searchEl.removeEventListener("input", this._onSearchInput);
            }
            if (this._expandAllEl) {
                this._expandAllEl.removeEventListener("click", this._onExpandAll);
            }
            if (this._collapseAllEl) {
                this._collapseAllEl.removeEventListener("click", this._onCollapseAll);
            }
            if (this._titleObserver) {
                this._titleObserver.disconnect();
                this._titleObserver = null;
            }
        });
    }

    // ------------------------------------------------------------------
    // Search
    // ------------------------------------------------------------------
    _marQuery() {
        // Cached element: re-querying the DOM per row was ~760 needless
        // querySelector calls per render (see the PERFORMANCE NOTE above).
        if (!this._searchEl || !this._searchEl.isConnected) {
            this._searchEl = document.querySelector(MAR_SEARCH_SELECTOR);
        }
        return ((this._searchEl && this._searchEl.value) || "").trim().toLowerCase();
    }

    _marMatches(record, query) {
        return (record.data.display_label || "").toLowerCase().includes(query);
    }

    /**
     * Match data for `query`, computed once and cached:
     *   matched    — paths whose OWN label matches
     *   onMatchAncestorChain — strict ancestors of a match (kept visible so
     *                  a deep hit still shows its menu context)
     *   openPaths  — everything to auto-expand so hits are actually on
     *                screen: each match's ancestor chain, plus a matched
     *                group itself (so matching "PBI Dashboards" opens it).
     */
    _marMatchInfo(query) {
        const records = this.props.list.records;
        const key = `${records.length}|${query}`;
        if (this._matchCache && this._matchCache.key === key) {
            return this._matchCache;
        }
        const matched = new Set();
        const onMatchAncestorChain = new Set();
        const openPaths = new Set();
        for (const r of records) {
            const path = r.data.menu_path;
            if (!path || !this._marMatches(r, query)) {
                continue;
            }
            matched.add(path);
            if (r.data.is_group) {
                openPaths.add(path);
            }
            for (const p of marAncestorPaths(path)) {
                onMatchAncestorChain.add(p);
                openPaths.add(p);
            }
        }
        this._matchCache = { key, matched, onMatchAncestorChain, openPaths };
        return this._matchCache;
    }

    _applySearch() {
        const query = this._marQuery();
        if (query === this._state.lastQuery) {
            return;
        }
        this._state.lastQuery = query;
        if (!query) {
            // Cleared: back to the page's default (everything folded).
            this.collapseAll();
            return;
        }
        // Auto-expand every branch containing a hit. This is what makes
        // collapse state and search agree: rather than having search
        // "override" collapse — which left a group rendering its collapsed
        // caret while its children were visible, and made expand/collapse
        // look broken while filtering — the matched branches are genuinely
        // expanded, so the caret always tells the truth and toggling keeps
        // working normally during a search.
        const info = this._marMatchInfo(query);
        for (const path of info.openPaths) {
            this._collapsed.delete(path);
        }
        this.render();
    }

    // ------------------------------------------------------------------
    // Expand / collapse
    // ------------------------------------------------------------------
    // Read through marGetState every time rather than caching the object in
    // setup(): a toggle reloads the form, and the renderer often survives
    // that with a new props.list, so a cached reference would silently point
    // at the state of a list that no longer exists.
    get _state() {
        return marGetState(this.props.list);
    }

    get _collapsed() {
        return this._state.collapsed;
    }

    _collapseEveryGroup() {
        for (const r of this.props.list.records) {
            if (r.data.is_group && r.data.menu_path) {
                this._collapsed.add(r.data.menu_path);
            }
        }
    }

    toggleCollapse(path) {
        if (!path) {
            return;
        }
        if (this._collapsed.has(path)) {
            this._collapsed.delete(path);
        } else {
            this._collapsed.add(path);
        }
        this.render();
    }

    expandAll() {
        this._collapsed.clear();
        this.render();
    }

    collapseAll() {
        this._collapseEveryGroup();
        this.render();
    }

    _marHiddenByCollapse(path) {
        if (!path || !this._collapsed.size) {
            return false;
        }
        for (const p of marAncestorPaths(path)) {
            if (this._collapsed.has(p)) {
                return true;
            }
        }
        return false;
    }

    /**
     * A group's name folds/unfolds it; every other cell does nothing.
     *
     * super is deliberately never called. The list is not editable, and in a
     * non-editable x2many ListRenderer.onCellClicked asks the field to OPEN
     * the row — a form dialog on a throwaway transient line, which is not a
     * thing this screen has. The Has Access switch is unaffected either way:
     * it handles its own click and stops propagation before reaching here.
     */
    async onCellClicked(record, column, ev) {
        if (record.data.is_group && column.name === "display_label") {
            ev.stopPropagation();
            this.toggleCollapse(record.data.menu_path);
        }
    }

    // ------------------------------------------------------------------
    // Row visibility — every branch below is O(depth), never O(rows)
    // ------------------------------------------------------------------
    getRowClass(record) {
        let classes = super.getRowClass(record) || "";
        const path = record.data.menu_path;
        
        // Calculate depth from display_label's leading spaces to bypass Odoo optimization on hidden columns
        const label = record.data.display_label || "";
        const leadingSpaces = (label.match(/^ */) || [""])[0].length;
        const depth = Math.floor(leadingSpaces / 4);
        
        classes += ` mar_depth_${depth}`;
        if (path && this._collapsed.has(path)) {
            classes += " mar_collapsed";
        }

        // Collapse applies whether or not a search is active, so a folded
        // caret always means "my children really are hidden".
        if (this._marHiddenByCollapse(path)) {
            return `${classes} d-none`;
        }

        const query = this._marQuery();
        if (!query) {
            return classes;
        }
        if (!path) {
            return `${classes} d-none`;
        }

        const info = this._marMatchInfo(query);
        // Own label matches, or a descendant matched (keep the context
        // chain), or an ancestor matched (reveal a matched app's sub-tree).
        if (info.matched.has(path) || info.onMatchAncestorChain.has(path)) {
            return classes;
        }
        for (const p of marAncestorPaths(path)) {
            if (info.matched.has(p)) {
                return classes;
            }
        }
        return `${classes} d-none`;
    }
}

// ---------------------------------------------------------------------------
// The Has Access toggle
//
// The cascade hangs off the toggle itself, not off the list renderer. Two
// earlier attempts failed for reasons worth recording:
//
//   1. ListRenderer.onCellClicked — never fires for this cell. Odoo's
//      BooleanToggleField template binds t-on-click.stop, so the click is
//      consumed before it reaches the row.
//   2. Diffing has_access across renders in onPatched — it *worked*, but it
//      is a guess: it has to infer "the user toggled this one row" from the
//      shape of a re-render, and it cannot tell a user toggle apart from a
//      reload that brings back different data. Overriding onChange removes
//      the guessing entirely: this method runs if and only if a human
//      clicked this row's toggle.
//
// A toggle now STAGES the row instead of writing it. record.update() marks
// the form dirty, which is what puts Odoo's own Save / Discard back in the
// breadcrumb — an earlier version called menu.access.matrix.action_cascade_
// toggle straight from here and reloaded the form, so every tick was written
// on the spot and the form was never dirty. There was then nothing on screen
// saying a change had happened, and no way to back one out.
//
// Only the clicked row is updated here. The cascade to descendants and the
// ancestor roll-up stay server-side in MenuAccessMatrixLine.write, which runs
// when Odoo saves the o2m command; the reload Odoo does after a save is what
// brings the cascaded rows and the server-computed count_label /
// access_status back. Cascading client-side instead would mean one
// record.update() per affected row, and each one costs an onchange round-trip
// — a top-level app can carry 100+ descendants.
//
// Consequence worth knowing: between the click and Save, only the clicked row
// moves. Its children and parents follow when you press Save.
// ---------------------------------------------------------------------------
class MarAccessToggleField extends BooleanToggleField {
    /**
     * Own template, for one reason: stock web.BooleanField renders the switch
     * as `disabled="props.readonly"`, and this list is not editable, so
     * props.readonly is ALWAYS true here and the switch would never be
     * clickable at all. Readonly is a statement about inline editing, which
     * this field does not use — it stages through record.update() below and
     * Odoo's own Save is what writes. The one
     * case that really must lock is a user who is an Odoo administrator (they
     * implicitly have every menu, so the rows are informational); that is read
     * straight off the row instead.
     */
    static template = xml`
        <CheckBox
            id="props.id"
            value="state.value"
            className="'o_field_boolean o_boolean_toggle form-switch'"
            disabled="isLocked"
            onChange.bind="onChange">
            ​
        </CheckBox>
    `;
    static components = { CheckBox };

    get isLocked() {
        return Boolean(this.props.record.data.is_user_admin);
    }

    async onChange(newValue) {
        this.state.value = newValue;
        // The update re-renders the list, and the tree panel is a scroll
        // container of its own — without this the panel jumps.
        marRememberScrollTop();
        try {
            await this.props.record.update({ [this.props.name]: newValue });
        } catch (err) {
            // Put the switch back so the screen never claims a grant the
            // record does not carry.
            this.state.value = !newValue;
            MAR_PENDING_SCROLL = null;
            throw err;
        }
        marApplyPendingScroll();
    }
}

registry.category("fields").add("mar_access_toggle", {
    ...booleanToggleField,
    component: MarAccessToggleField,
});

class MenuAccessMatrixListField extends X2ManyField {}
MenuAccessMatrixListField.components = {
    ...X2ManyField.components,
    ListRenderer: MenuAccessMatrixListRenderer,
};

registry.category("fields").add("mar_matrix_list_field", {
    ...x2ManyField,
    component: MenuAccessMatrixListField,
});
