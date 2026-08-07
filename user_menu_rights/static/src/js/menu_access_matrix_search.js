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
import { ListRenderer } from "@web/views/list/list_renderer";
import { onMounted, onWillUnmount } from "@odoo/owl";

const MAR_SEARCH_SELECTOR = ".mar_matrix_form .mar_search_box";
const MAR_EXPAND_ALL_SELECTOR = ".mar_matrix_form .mar_expand_all";
const MAR_COLLAPSE_ALL_SELECTOR = ".mar_matrix_form .mar_collapse_all";
const MAR_SEARCH_DEBOUNCE_MS = 180;

/**
 * Expand/collapse state, held per list rather than per renderer instance.
 *
 * Owl can tear down and re-create this renderer while the user is working
 * (any form re-render can do it). Keeping the collapsed set on `this` meant
 * setup() ran again and re-folded everything, so a search's expanded
 * results silently snapped back to "all collapsed". A WeakMap keyed by the
 * list survives that; keying also on record count means Load Menus (which
 * swaps the whole record set) correctly starts fresh at the collapsed
 * default instead of reusing stale paths.
 */
const MAR_STATE = new WeakMap();

function marGetState(list) {
    let state = MAR_STATE.get(list);
    if (!state || state.count !== list.records.length) {
        state = { collapsed: new Set(), lastQuery: "", count: list.records.length };
        for (const r of list.records) {
            if (r.data.is_group && r.data.menu_path) {
                state.collapsed.add(r.data.menu_path);
            }
        }
        MAR_STATE.set(list, state);
    }
    return state;
}

/**
 * How deep a materialized path sits. "/12/" -> 0, "/12/45/" -> 1.
 *
 * The model already indents display_label with four spaces per level, but
 * HTML collapses leading whitespace, so that indent renders as nothing and
 * the whole tree comes out flush-left. The depth is therefore turned into a
 * class here and paid out as cell padding in CSS.
 *
 * Counted by character rather than split()/filter(): this runs once per row
 * per render on a ~760-row list, and the split allocated two arrays each
 * time. menu_path is used rather than the `depth` field because this file
 * already relies on menu_path being present, and Odoo does not guarantee
 * that a column_invisible field is fetched at all.
 *
 * MAR_MAX_DEPTH caps the class, not the data: past it, rows keep the last
 * indent step the stylesheet defines instead of falling back to none.
 */
const MAR_MAX_DEPTH = 10;

function marPathDepth(path) {
    if (!path) {
        return 0;
    }
    let slashes = 0;
    for (let i = 0; i < path.length; i++) {
        if (path.charCodeAt(i) === 47 /* "/" */) {
            slashes++;
        }
    }
    return Math.min(Math.max(slashes - 2, 0), MAR_MAX_DEPTH);
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

class MenuAccessMatrixListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this._state = marGetState(this.props.list);
        this._matchCache = null;

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
        });
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

    async onCellClicked(record, column, ev) {
        if (record.data.is_group && column.name === "display_label") {
            ev.stopPropagation();
            this.toggleCollapse(record.data.menu_path);
            return;
        }
        return super.onCellClicked(record, column, ev);
    }

    // ------------------------------------------------------------------
    // Row visibility — every branch below is O(depth), never O(rows)
    // ------------------------------------------------------------------
    getRowClass(record) {
        let classes = super.getRowClass(record) || "";
        const path = record.data.menu_path;
        // Added before any early return so a row that is currently filtered
        // out still carries its indent when it comes back.
        classes += ` mar_depth_${marPathDepth(path)}`;
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

class MenuAccessMatrixListField extends X2ManyField {}
MenuAccessMatrixListField.components = {
    ...X2ManyField.components,
    ListRenderer: MenuAccessMatrixListRenderer,
};

registry.category("fields").add("mar_matrix_list_field", {
    ...x2ManyField,
    component: MenuAccessMatrixListField,
});
