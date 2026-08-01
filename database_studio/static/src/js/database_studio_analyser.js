/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { download } from "@web/core/network/download";
import { Component, useState, useRef, onMounted, onPatched, onWillUnmount } from "@odoo/owl";

// Small dialog to name a query before saving it to history.
export class SqlMsSaveDialog extends Component {
    setup() {
        this.state = useState({ name: this.props.defaultName || "" });
        this.inputRef = useRef("input");
        onMounted(() => {
            if (this.inputRef.el) {
                this.inputRef.el.focus();
                this.inputRef.el.select();
            }
        });
    }
    confirm() {
        this.props.onConfirm((this.state.name || "").trim());
        this.props.close();
    }
    onKeydown(ev) {
        if (ev.key === "Enter") {
            this.confirm();
        }
    }
}
SqlMsSaveDialog.template = "database_studio.SaveDialog";
SqlMsSaveDialog.components = { Dialog };
SqlMsSaveDialog.props = {
    close: Function,
    onConfirm: Function,
    defaultName: { type: String, optional: true },
};

// Shown when closing a query tab that still holds unsaved text: lets the user
// save it to history (with a name) or discard it before the tab is removed.
export class SqlMsCloseTabDialog extends Component {
    setup() {
        this.state = useState({ name: this.props.defaultName || "" });
        this.inputRef = useRef("input");
        onMounted(() => {
            if (this.inputRef.el) {
                this.inputRef.el.focus();
                this.inputRef.el.select();
            }
        });
    }
    save() {
        this.props.onSave((this.state.name || "").trim());
        this.props.close();
    }
    discard() {
        this.props.onDiscard();
        this.props.close();
    }
}
SqlMsCloseTabDialog.template = "database_studio.CloseTabDialog";
SqlMsCloseTabDialog.components = { Dialog };
SqlMsCloseTabDialog.props = {
    close: Function,
    onSave: Function,
    onDiscard: Function,
    tabName: { type: String, optional: true },
    defaultName: { type: String, optional: true },
};

const KEYWORDS = [
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
    "DELETE", "CREATE", "ALTER", "DROP", "TABLE", "VIEW", "INDEX", "JOIN",
    "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "CROSS", "ON", "AS", "AND",
    "OR", "NOT", "NULL", "IS", "IN", "LIKE", "ILIKE", "BETWEEN", "GROUP",
    "BY", "ORDER", "HAVING", "LIMIT", "OFFSET", "DISTINCT", "UNION", "ALL",
    "CASE", "WHEN", "THEN", "ELSE", "END", "ASC", "DESC", "COUNT", "SUM",
    "AVG", "MIN", "MAX", "COALESCE", "CAST", "EXISTS", "WITH", "RETURNING",
    "USING", "TRUE", "FALSE",
];
const KEYWORD_RE = new RegExp("\\b(" + KEYWORDS.join("|") + ")\\b", "gi");
const KEYWORD_SET = new Set(KEYWORDS);
const NEWLINE_BEFORE = [
    "FROM", "WHERE", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL JOIN",
    "OUTER JOIN", "CROSS JOIN", "JOIN", "GROUP BY", "ORDER BY", "HAVING",
    "LIMIT", "OFFSET", "UNION", "VALUES", "SET", "RETURNING",
];

// One regex covering every token kind so highlighting is a single, ordered
// pass. This avoids the placeholder collisions that used to turn string
// literals such as '' or IN ('a','b') into numbers.
const TOKEN_RE = new RegExp(
    "('(?:[^']|'')*')" +          // 1: single-quoted string (handles '' and %)
    "|(\"(?:[^\"]|\"\")*\")" +    // 2: double-quoted identifier
    "|(--[^\\n]*|/\\*[\\s\\S]*?\\*/)" + // 3: comment
    "|(\\b\\d+(?:\\.\\d+)?\\b)" + // 4: number
    "|([A-Za-z_][A-Za-z0-9_$]*)", // 5: identifier / keyword
    "g"
);

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function highlightSql(text) {
    let out = "";
    let last = 0;
    let m;
    TOKEN_RE.lastIndex = 0;
    while ((m = TOKEN_RE.exec(text)) !== null) {
        out += escapeHtml(text.slice(last, m.index));
        const raw = escapeHtml(m[0]);
        if (m[1]) {
            out += '<span class="sqlms-str">' + raw + "</span>";
        } else if (m[2]) {
            out += '<span class="sqlms-ident">' + raw + "</span>";
        } else if (m[3]) {
            out += '<span class="sqlms-comment">' + raw + "</span>";
        } else if (m[4]) {
            out += '<span class="sqlms-num">' + raw + "</span>";
        } else if (KEYWORD_SET.has(m[0].toUpperCase())) {
            out += '<span class="sqlms-kw">' + raw + "</span>";
        } else {
            out += raw;
        }
        last = m.index + m[0].length;
    }
    out += escapeHtml(text.slice(last));
    return out;
}

function formatSql(text) {
    if (!text) {
        return text;
    }
    // Protect string literals and comments so formatting never rewrites their
    // contents (e.g. a comma or keyword inside 'a,b' or '%x%').
    const protectedTokens = [];
    let out = text.replace(
        /('(?:[^']|'')*')|(--[^\n]*|\/\*[\s\S]*?\*\/)/g,
        (mtok) => {
            protectedTokens.push(mtok);
            return " \x00" + (protectedTokens.length - 1) + "\x00 ";
        }
    );
    out = out.replace(/\s+/g, " ").trim();
    out = out.replace(KEYWORD_RE, (mkw) => mkw.toUpperCase());
    const phrases = NEWLINE_BEFORE.slice().sort((a, b) => b.length - a.length);
    for (const p of phrases) {
        const re = new RegExp("\\s+" + p.replace(/ /g, "\\s+") + "\\b", "gi");
        out = out.replace(re, "\n" + p);
    }
    out = out.replace(/,\s*/g, ",\n    ");
    // Restore protected tokens.
    out = out.replace(/\x00(\d+)\x00/g, (mtok, i) => protectedTokens[Number(i)]);
    return out.replace(/[ \t]+\n/g, "\n");
}

// Splits a query's text into top-level statements on ';', ignoring
// semicolons inside string literals, quoted identifiers, and comments so a
// query tab can render (and collapse) each statement as its own block.
// Rejoining the returned parts with ";" reconstructs the original text
// exactly (the separator characters themselves are not included in a part).
function splitStatements(text) {
    const parts = [];
    let cur = "";
    let i = 0;
    const n = text.length;
    while (i < n) {
        const ch = text[i];
        if (ch === "'") {
            let j = i + 1;
            while (j < n) {
                if (text[j] === "'") {
                    if (text[j + 1] === "'") {
                        j += 2;
                        continue;
                    }
                    j += 1;
                    break;
                }
                j += 1;
            }
            cur += text.slice(i, j);
            i = j;
        } else if (ch === '"') {
            let j = i + 1;
            while (j < n && text[j] !== '"') {
                j += 1;
            }
            j = Math.min(j + 1, n);
            cur += text.slice(i, j);
            i = j;
        } else if (ch === "-" && text[i + 1] === "-") {
            let j = text.indexOf("\n", i);
            j = j === -1 ? n : j;
            cur += text.slice(i, j);
            i = j;
        } else if (ch === "/" && text[i + 1] === "*") {
            let j = text.indexOf("*/", i + 2);
            j = j === -1 ? n : j + 2;
            cur += text.slice(i, j);
            i = j;
        } else if (ch === ";") {
            parts.push(cur);
            cur = "";
            i += 1;
        } else {
            cur += ch;
            i += 1;
        }
    }
    if (cur.trim() || !parts.length) {
        parts.push(cur);
    }
    return parts;
}

// Tab/block ids only need to be unique within one page load, and the History
// list needs to mint them without an Analyser instance to hand a counter out
// from — so these live at module scope rather than on component state.
let _qtabIdSeq = 0;
let _blockIdSeq = 0;

function makeBlocks(text) {
    return splitStatements(text || "").map((t) => ({
        id: ++_blockIdSeq,
        text: t,
        collapsed: false,
    }));
}

// History names can run long; the qtab bar has room for a short label only.
function truncateName(name, max = 20) {
    if (!name) {
        return name;
    }
    return name.length > max ? name.slice(0, max) + "..." : name;
}

// opts.historyId links this tab to a database.studio.query record (it was
// either opened from History or has since been Saved): Save then updates
// that same record instead of upserting a new one, and closing the tab
// skips the "save before closing?" prompt once opts.isSaved is true.
// opts.name is the record's full (untruncated) name, kept as fullName so a
// later Save can prefill it — qt.name is the truncated label actually shown
// on the tab.
export function makeQtab(query, opts) {
    opts = opts || {};
    const id = ++_qtabIdSeq;
    return {
        id,
        name: opts.name ? truncateName(opts.name) : "Query " + id,
        fullName: opts.name || null,
        query: query || "",
        blocks: makeBlocks(query),
        execQuery: "",
        execWasSelection: false,
        queryResult: null,
        selectedCols: [],
        historyId: opts.historyId || null,
        isSaved: !!opts.isSaved,
    };
}

// Lets a query opened from the History list land in a new tab of whatever
// Analyser it was opened from, instead of losing other open tabs. This holds
// actual tab *data*, not a component reference: navigating to History fully
// destroys the Analyser component (Odoo doesn't keep client-action
// controllers alive off-screen the way it does act_window breadcrumbs), so
// by the time a history row is clicked there is no live instance left to
// call back into — only a plain object surviving in this module can bridge
// the trip to History and back.
export const analyserRegistry = { pending: null };

// If the user leaves for History and then wanders off elsewhere instead of
// coming back (e.g. switches to an unrelated app), the snapshot above would
// otherwise sit around indefinitely and resurface as a surprise the next
// time an Analyser happens to open. Only honor it within this window of it
// being set.
const PENDING_TTL_MS = 5 * 60 * 1000;

export class SqlMsAnalyser extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.blocksRef = useRef("blocksContainer");
        this.rootRef = useRef("rootEl");

        this.state = useState({
            tables: [],
            views: [],
            filter: "",
            selected: null,
            selectedType: null,
            activeTab: "query",
            searchMode: "contains",
            fieldGroups: [],
            collapsedGroups: {},
            mapping: null,
            query: "",
            execQuery: "",
            execWasSelection: false,
            queryResult: null,
            // Query sub-tabs. state.query/execQuery/queryResult always mirror
            // the active tab; switching snapshots them back into their tab.
            qtabs: [],
            activeQtabId: null,
            loading: false,
            exporting: false,
            favorites: [],
            showFavorites: true,
            showTables: true,
            showViews: true,
            checked: {},
            selectedCols: [],
        });

        // A query passed directly by a record button (action_open_in_analyser)
        // is an explicit, one-off request — it always wins over any leftover
        // registry snapshot. Otherwise, a still-fresh snapshot left by a
        // history-list click (this Analyser's own tabs, plus the newly picked
        // query) is restored instead of starting blank.
        const act = this.props.action || {};
        const incoming = (act.params && act.params.query) ||
            (act.context && act.context.default_query);
        const pending = analyserRegistry.pending;
        analyserRegistry.pending = null;
        const usePending = !incoming && pending && pending.qtabs && pending.qtabs.length &&
            (Date.now() - pending.ts) < PENDING_TTL_MS;
        if (usePending) {
            this.state.qtabs = pending.qtabs;
            const active = pending.qtabs.find((t) => t.id === pending.activeQtabId) ||
                pending.qtabs[pending.qtabs.length - 1];
            this._loadQtab(active);
            this.state.activeTab = "query";
        } else {
            const first = this._makeQtab(incoming || "");
            this.state.qtabs.push(first);
            this.state.activeQtabId = first.id;
            this.state.query = first.query;
            if (incoming) {
                this.state.activeTab = "query";
            }
        }

        onMounted(() => this.loadObjects());
        // Populate the textarea/highlight from the initial active tab.
        onMounted(() => this._syncEditor());
        // The query editor's <textarea> is destroyed/recreated whenever the
        // user leaves and returns to the Query tab. Re-sync its value and the
        // highlight overlay from state so the typed query is never lost.
        onPatched(() => this._syncEditor());

        // The backend theme forces the action container to full-viewport
        // height below the navbar, so our panel would overflow the bottom of
        // the screen. Pin the root's height to the space actually available
        // from its top to the viewport bottom, and keep it correct on resize.
        this._onResize = () => this._fitHeight();
        onMounted(() => {
            this._fitHeight();
            window.addEventListener("resize", this._onResize);
        });
        onWillUnmount(() => window.removeEventListener("resize", this._onResize));
    }

    _fitHeight() {
        const el = this.rootRef.el;
        if (el) {
            const top = el.getBoundingClientRect().top;
            el.style.setProperty("height", (window.innerHeight - top) + "px", "important");
        }
    }

    // Each statement block has its own textarea/highlight <pre>, found by
    // data-block-id rather than a static t-ref (the number of blocks is
    // dynamic). Re-sync all of them from state whenever the editor DOM is
    // (re)created (e.g. switching back to the Query tab, or a block just
    // got split on blur). A block's own text is written into its textarea's
    // .value verbatim by onBlockInput before this runs, so on a plain
    // keystroke ta.value already equals blk.text and this is a no-op —
    // it never fights the user's typing or moves the caret.
    _syncEditor() {
        const root = this.blocksRef.el;
        if (!root) {
            return;
        }
        for (const blk of this.queryBlocks) {
            const ta = root.querySelector(
                '.sqlms-block-textarea[data-block-id="' + blk.id + '"]'
            );
            if (ta && ta.value !== blk.text) {
                ta.value = blk.text;
            }
            const pre = root.querySelector(
                '.sqlms-block-highlight[data-block-id="' + blk.id + '"]'
            );
            if (pre) {
                pre.innerHTML = highlightSql(blk.text) + "\n";
            }
        }
    }

    toggleTables() {
        this.state.showTables = !this.state.showTables;
    }
    toggleViews() {
        this.state.showViews = !this.state.showViews;
    }

    // -- multi-select checkboxes ---------------------------------------
    toggleCheck(name, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        if (this.state.checked[name]) {
            delete this.state.checked[name];
        } else {
            this.state.checked[name] = true;
        }
        if (this.state.activeTab === "mapping") {
            this.loadMapping();
        } else if (this.state.activeTab === "fields") {
            this.loadFields();
        }
    }
    get checkedCount() {
        return Object.keys(this.state.checked).length;
    }
    clearChecks() {
        this.state.checked = {};
    }
    async buildQuery() {
        const tables = Object.keys(this.state.checked);
        if (!tables.length) {
            return;
        }
        this.state.loading = true;
        try {
            const res = await this.orm.call(
                "database.studio.analyser", "build_join_query", [tables]
            );
            this.state.activeTab = "query";
            this.setQuery(res.query);
        } finally {
            this.state.loading = false;
        }
    }

    openHistory() {
        // Snapshot our tabs so that, if the user picks a row there, this
        // Analyser's work isn't lost even though the component itself is
        // about to be destroyed (see analyserRegistry's docstring above).
        this._snapshotActiveQtab();
        analyserRegistry.pending = {
            qtabs: this.state.qtabs,
            activeQtabId: this.state.activeQtabId,
            ts: Date.now(),
        };
        this.action.doAction("database_studio.action_sql_ms_query");
    }

    async loadObjects() {
        const res = await this.orm.call("database.studio.analyser", "get_objects", []);
        this.state.tables = res.tables;
        this.state.views = res.views;
        this.state.favorites = res.favorites || [];
    }

    // -- favourites ----------------------------------------------------
    toggleFavorites() {
        this.state.showFavorites = !this.state.showFavorites;
    }
    isFavorite(name) {
        return this.state.favorites.some((f) => f.name === name);
    }
    async toggleFavorite(name, type, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.favorites = await this.orm.call(
            "database.studio.analyser", "toggle_favorite", [name, type || "table"]
        );
    }
    get filteredFavorites() {
        return this._filter(this.state.favorites, (f) => f.name);
    }

    get filteredTables() {
        return this._filter(this.state.tables);
    }
    get filteredViews() {
        return this._filter(this.state.views);
    }
    _filter(list, getName) {
        const f = this.state.filter.trim().toLowerCase();
        if (!f) {
            return list;
        }
        const mode = this.state.searchMode;
        return list.filter((item) => {
            const x = (getName ? getName(item) : item).toLowerCase();
            if (mode === "start") {
                return x.startsWith(f);
            }
            if (mode === "end") {
                return x.endsWith(f);
            }
            return x.includes(f);
        });
    }

    async selectObject(name, type) {
        this.state.selected = name;
        this.state.selectedType = type;
        if (this.state.activeTab === "mapping") {
            await this.loadMapping();
        } else {
            // Clicking a table always shows its fields.
            this.state.activeTab = "fields";
            await this.loadFields();
        }
    }

    async setTab(tab) {
        this.state.activeTab = tab;
        if (tab === "fields") {
            await this.loadFields();
        } else if (tab === "mapping") {
            await this.loadMapping();
        } else if (tab === "query" && this.state.selected && !this.state.query.trim()) {
            // Prefill a SELECT for the currently selected table/view, but only
            // when the editor is empty so a typed query is never overwritten.
            this.setQuery('SELECT * FROM "' + this.state.selected + '"');
        }
    }

    // Fields are shown for the checked tables if any, else the clicked table.
    _fieldsTables() {
        const checked = Object.keys(this.state.checked);
        if (checked.length) {
            return checked;
        }
        return this.state.selected ? [this.state.selected] : [];
    }
    async loadFields() {
        const tables = this._fieldsTables();
        if (!tables.length) {
            this.state.fieldGroups = [];
            return;
        }
        this.state.loading = true;
        try {
            this.state.fieldGroups = await this.orm.call(
                "database.studio.analyser", "get_fields_multi", [tables]
            );
        } finally {
            this.state.loading = false;
        }
    }
    toggleFieldGroup(table) {
        if (this.state.collapsedGroups[table]) {
            delete this.state.collapsedGroups[table];
        } else {
            this.state.collapsedGroups[table] = true;
        }
    }
    get fieldCount() {
        return (this.state.fieldGroups || []).reduce((n, g) => n + g.fields.length, 0);
    }

    // Tables referenced after FROM/JOIN in the current query (only those that
    // are real tables/views, so aliases and subqueries are ignored).
    _tablesInQuery() {
        const known = new Set([...this.state.tables, ...this.state.views]);
        const out = [];
        const re = /\b(?:from|join)\s+("?)([A-Za-z_][A-Za-z0-9_$]*)\1/gi;
        let m;
        while ((m = re.exec(this.state.query || "")) !== null) {
            if (known.has(m[2]) && !out.includes(m[2])) {
                out.push(m[2]);
            }
        }
        return out;
    }
    // Field mapping is computed for the checked tables if any; otherwise for
    // the selected object combined with any table(s) used in the query.
    _mappingTables() {
        const checked = Object.keys(this.state.checked);
        if (checked.length) {
            return checked;
        }
        const set = [];
        if (this.state.selected) {
            set.push(this.state.selected);
        }
        for (const t of this._tablesInQuery()) {
            if (!set.includes(t)) {
                set.push(t);
            }
        }
        return set;
    }
    async loadMapping() {
        const tables = this._mappingTables();
        if (!tables.length) {
            this.state.mapping = [];
            return;
        }
        this.state.loading = true;
        try {
            this.state.mapping = await this.orm.call(
                "database.studio.analyser", "get_field_mapping", [tables]
            );
        } finally {
            this.state.loading = false;
        }
    }

    // -- query sub-tabs ------------------------------------------------
    _makeQtab(query) {
        return makeQtab(query);
    }
    get qtab() {
        return this.state.qtabs.find((t) => t.id === this.state.activeQtabId);
    }
    // Copy the live editor state back into the active tab so nothing is lost
    // when we switch to or close another tab.
    _snapshotActiveQtab() {
        const t = this.qtab;
        if (t) {
            t.query = this.state.query;
            t.execQuery = this.state.execQuery;
            t.execWasSelection = this.state.execWasSelection;
            t.queryResult = this.state.queryResult;
            t.selectedCols = this.state.selectedCols;
        }
    }
    _loadQtab(t) {
        this.state.activeQtabId = t.id;
        this.state.query = t.query;
        this.state.execQuery = t.execQuery;
        this.state.execWasSelection = t.execWasSelection;
        this.state.queryResult = t.queryResult;
        this.state.selectedCols = t.selectedCols || [];
        this._syncEditor();
    }
    addQtab() {
        this._snapshotActiveQtab();
        const t = this._makeQtab("");
        this.state.qtabs.push(t);
        this.state.activeTab = "query";
        this._loadQtab(t);
    }
    switchQtab(id) {
        this.state.activeTab = "query";
        if (id === this.state.activeQtabId) {
            return;
        }
        this._snapshotActiveQtab();
        const t = this.state.qtabs.find((x) => x.id === id);
        if (t) {
            this._loadQtab(t);
        }
    }
    removeQtab(id, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const t = this.state.qtabs.find((x) => x.id === id);
        if (!t) {
            return;
        }
        // Make sure we test the up-to-date text of the active tab.
        if (id === this.state.activeQtabId) {
            this._snapshotActiveQtab();
        }
        // Already saved (starred) — it's persisted, so there's nothing this
        // close could lose. Don't ask again.
        if (t.isSaved) {
            this._doRemoveQtab(id);
            return;
        }
        const query = (t.query || "").trim();
        if (!query) {
            this._doRemoveQtab(id);
            return;
        }
        // Unsaved content — ask whether to save before closing.
        this.dialog.add(SqlMsCloseTabDialog, {
            tabName: t.name,
            defaultName: t.fullName || query.replace(/\s+/g, " ").slice(0, 60),
            onSave: async (name) => {
                await this._persistSave(t, query, name);
                this.notification.add("Query saved ★", { type: "success" });
                this._doRemoveQtab(id);
            },
            onDiscard: () => this._doRemoveQtab(id),
        });
    }
    // Saves `query` under `name`, updating the tab's linked History record in
    // place if it already has one (opened from History, or a prior Save) so
    // editing + re-saving doesn't fork off a duplicate row; otherwise
    // upserts by exact query text as before. Updates the tab's own link/name
    // fields from the result either way.
    async _persistSave(t, query, name) {
        const result = t.historyId
            ? await this.orm.call("database.studio.query", "save_query_id", [t.historyId, query, name || false])
            : await this.orm.call("database.studio.query", "save_query", [query, name || false]);
        if (t && result) {
            t.historyId = result.id;
            t.fullName = result.name;
            t.name = truncateName(result.name);
            t.isSaved = true;
        }
        return result;
    }
    _doRemoveQtab(id) {
        const idx = this.state.qtabs.findIndex((t) => t.id === id);
        if (idx === -1) {
            return;
        }
        const wasActive = id === this.state.activeQtabId;
        this.state.qtabs.splice(idx, 1);
        // Never leave the editor with zero tabs. Its name always resets to
        // "Query 1" here rather than continuing the running counter, since
        // from the user's perspective this is a fresh start, not tab N+1.
        if (!this.state.qtabs.length) {
            const t = this._makeQtab("");
            t.name = "Query 1";
            this.state.qtabs.push(t);
            this._loadQtab(t);
            return;
        }
        if (wasActive) {
            const next = this.state.qtabs[Math.min(idx, this.state.qtabs.length - 1)];
            this._loadQtab(next);
        }
    }

    // -- query editor --------------------------------------------------
    // A query tab's text as a list of persistent ';'-separated statement
    // blocks, each individually collapsible/foldable (view built from the
    // active tab's stable block objects — see makeBlocks).
    get queryBlocks() {
        const blocks = (this.qtab && this.qtab.blocks) || [];
        return blocks.map((b, index) => ({
            id: b.id,
            index,
            text: b.text,
            collapsed: b.collapsed,
            preview: b.text.trim().replace(/\s+/g, " ").slice(0, 80) || "(empty)",
            lineCount: (b.text.match(/\n/g) || []).length + 1,
        }));
    }
    toggleBlockCollapse(id) {
        const blk = this.qtab && this.qtab.blocks.find((b) => b.id === id);
        if (blk) {
            blk.collapsed = !blk.collapsed;
        }
    }
    setQuery(text) {
        this.state.query = text;
        const t = this.qtab;
        if (t) {
            t.blocks = makeBlocks(text);
        }
        this._syncEditor();
    }
    // Fired on every keystroke in a block's own textarea: just record its
    // new text verbatim (no re-splitting, no touching other blocks) so the
    // block's DOM node is never restructured mid-edit — see _syncEditor.
    onBlockInput(id, ev) {
        const t = this.qtab;
        const blk = t && t.blocks.find((b) => b.id === id);
        if (!blk) {
            return;
        }
        blk.text = ev.target.value;
        this.state.query = t.blocks.map((b) => b.text).join(";");
    }
    // Only on losing focus (not every keystroke) do we check whether the
    // user finished typing a new statement (a ';' now sits inside this
    // block) and, if so, fold it into separate blocks.
    onBlockBlur(id) {
        const t = this.qtab;
        if (!t) {
            return;
        }
        const idx = t.blocks.findIndex((b) => b.id === id);
        if (idx === -1) {
            return;
        }
        // An emptied-out statement collapses away entirely instead of
        // lingering as a blank section, as long as it isn't the tab's only
        // block (a single empty block is just the normal empty-editor state).
        if (!t.blocks[idx].text.trim() && t.blocks.length > 1) {
            t.blocks.splice(idx, 1);
            this.state.query = t.blocks.map((b) => b.text).join(";");
            return;
        }
        const pieces = splitStatements(t.blocks[idx].text);
        if (pieces.length <= 1) {
            return;
        }
        const fresh = pieces.map((text) => ({
            id: ++_blockIdSeq,
            text,
            collapsed: false,
        }));
        t.blocks.splice(idx, 1, ...fresh);
        this.state.query = t.blocks.map((b) => b.text).join(";");
    }
    onBlockScroll(ev) {
        const id = ev.target.dataset.blockId;
        const root = this.blocksRef.el;
        const pre = root && root.querySelector(
            '.sqlms-block-highlight[data-block-id="' + id + '"]'
        );
        if (pre) {
            pre.scrollTop = ev.target.scrollTop;
            pre.scrollLeft = ev.target.scrollLeft;
        }
    }
    formatQuery() {
        this.setQuery(formatSql(this.state.query));
    }
    clearQuery() {
        this.state.queryResult = null;
        this.setQuery("");
    }
    copyQuery() {
        if (this.state.query.trim()) {
            this._copy(this.state.query, "Query");
        }
    }
    saveQuery() {
        const q = this.state.query.trim();
        if (!q) {
            return;
        }
        const t = this.qtab;
        this.dialog.add(SqlMsSaveDialog, {
            defaultName: (t && t.fullName) || q.replace(/\s+/g, " ").slice(0, 60),
            onConfirm: async (name) => {
                await this._persistSave(t, q, name);
                this.notification.add("Query saved ★", { type: "success" });
            },
        });
    }
    insertObject(name, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.activeTab = "query";
        const stmt = 'SELECT * FROM "' + name + '"';
        // Each click builds a full SELECT for the clicked table. Stack it as a
        // separate statement instead of dropping the bare name after FROM.
        const cur = this.state.query.replace(/;\s*$/, "").trimEnd();
        this.setQuery(cur ? cur + ";\n" + stmt : stmt);
    }

    _activeQuery() {
        // Run only the highlighted selection when the user has one, like a
        // real query analyser; otherwise run the whole editor content. A
        // textarea keeps its selectionStart/End after it is blurred (e.g. by
        // clicking the Execute button), so check every block's textarea
        // rather than requiring one to still have focus.
        const root = this.blocksRef.el;
        const textareas = root ? root.querySelectorAll(".sqlms-block-textarea") : [];
        for (const ta of textareas) {
            if (ta.selectionEnd > ta.selectionStart) {
                const sel = ta.value.substring(ta.selectionStart, ta.selectionEnd).trim();
                if (sel) {
                    return { query: sel, isSelection: true };
                }
            }
        }
        return { query: this._fullQueryForExec(), isSelection: false };
    }
    // Joins the active tab's statement blocks for execution, skipping any
    // that are blank. A block can end up empty from a stray double ';' (or a
    // fresh, not-yet-typed-into one) — sending that straight to Postgres as
    // "...; ; ..." is a guaranteed syntax error, so it's dropped here rather
    // than surfacing as a confusing failure on Execute.
    _fullQueryForExec() {
        const t = this.qtab;
        if (!t) {
            return this.state.query;
        }
        return t.blocks
            .filter((b) => b.text.trim())
            .map((b) => b.text)
            .join(";");
    }

    // `fresh` distinguishes a real Execute click (re-capture the editor's
    // selection/text as the query to run) from a pager click (First/Previous/
    // Next/Last must keep paging through the already-executed query, even
    // though First also requests page 1).
    async runQuery(page = 1, fresh = false) {
        if (fresh) {
            const active = this._activeQuery();
            this.state.execQuery = active.query;
            this.state.execWasSelection = active.isSelection;
            // A new run may have a different column set; don't carry a
            // column selection over from whatever was run before.
            this.state.selectedCols = [];
        }
        const query = this.state.execQuery || this.state.query;
        const execQuery = this.state.execQuery;
        const execWasSelection = this.state.execWasSelection;
        // Remember which tab this run belongs to: if the user switches query
        // tabs before the RPC resolves, the result must land on that tab
        // instead of clobbering whatever tab is active by then.
        const qtabId = this.state.activeQtabId;
        this.state.loading = true;
        let result;
        try {
            result = await this.orm.call(
                "database.studio.analyser", "run_query", [query, page, 100]
            );
        } finally {
            this.state.loading = false;
        }
        if (qtabId === this.state.activeQtabId) {
            this.state.queryResult = result;
        } else {
            const t = this.state.qtabs.find((x) => x.id === qtabId);
            if (t) {
                t.execQuery = execQuery;
                t.execWasSelection = execWasSelection;
                t.queryResult = result;
            }
        }
        // A successful Execute (not a pager click) logs to History under the
        // "On the fly" tab, same as the old always-log behavior — but never
        // lets logging failures surface as if the query itself had failed.
        if (fresh && query && query.trim()) {
            this.orm.call("database.studio.query", "log_query_run", [query]).catch(() => {});
        }
    }

    // -- copy helpers --------------------------------------------------
    async _copy(text, label) {
        let ok = false;
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                ok = true;
            }
        } catch (e) {
            ok = false;
        }
        if (!ok) {
            // navigator.clipboard is unavailable on insecure (http) origins;
            // fall back to a hidden textarea + execCommand.
            try {
                const ta = document.createElement("textarea");
                ta.value = text;
                ta.setAttribute("readonly", "");
                ta.style.position = "fixed";
                ta.style.top = "0";
                ta.style.left = "0";
                ta.style.opacity = "0";
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                ok = document.execCommand("copy");
                document.body.removeChild(ta);
            } catch (e) {
                ok = false;
            }
        }
        this.notification.add(
            ok ? label + " copied to clipboard" : "Could not copy to clipboard",
            { type: ok ? "success" : "danger" }
        );
    }
    copyMapping() {
        const header = ["from_table", "from_column", "to_table", "to_column", "via"].join("\t");
        const rows = (this.state.mapping && this.state.mapping.rows) || [];
        const body = rows
            .map((m) => [m.from_table, m.from_column, m.to_table, m.to_column, m.via].join("\t"))
            .join("\n");
        this._copy(header + "\n" + body, "Mapping");
    }
    copyFields() {
        const groups = this.state.fieldGroups || [];
        const header = ["table", "name", "type", "precision/length", "nullable"].join("\t");
        const lines = [header];
        for (const g of groups) {
            for (const f of g.fields) {
                lines.push([g.table, f.name, f.type, f.precision, f.nullable].join("\t"));
            }
        }
        this._copy(lines.join("\n"), "Fields");
    }
    // -- result column selection ---------------------------------------
    // Clicking a column header toggles it in/out of the selection (no
    // modifier key needed, several columns can be picked this way). Copy
    // then exports only the selected columns; with none selected it exports
    // every column, same as before.
    toggleColumn(index, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const i = this.state.selectedCols.indexOf(index);
        if (i === -1) {
            this.state.selectedCols.push(index);
        } else {
            this.state.selectedCols.splice(i, 1);
        }
    }
    clearColumnSelection() {
        this.state.selectedCols = [];
    }
    // Copies only the currently displayed page (unlike Export Excel, which
    // pulls the full, unpaginated result set) since clipboard copy is meant
    // for pasting a quick look, not the whole result set. Restricted to the
    // selected column(s) when any are picked, else every column.
    copyResults() {
        const res = this.state.queryResult;
        if (!res || !res.columns.length) {
            return;
        }
        const cols = this.state.selectedCols.length
            ? this.state.selectedCols.slice().sort((a, b) => a - b)
            : res.columns.map((c, i) => i);
        const header = cols.map((i) => res.columns[i]).join("\t");
        const lines = (res.rows || []).map(
            (row) => cols.map((i) => (row[i] === null ? "" : row[i])).join("\t")
        );
        this._copy([header, ...lines].join("\n"), "Results");
    }
    // Full, unpaginated result set as a downloaded .xlsx — a normal file
    // download isn't bound by clipboard permissions/activation, so it works
    // regardless of result size or origin security.
    async exportExcel() {
        const query = this.state.execQuery || this.state.query;
        if (!query || !query.trim()) {
            return;
        }
        this.state.exporting = true;
        try {
            await download({
                url: "/database_studio/export_xlsx",
                data: { query },
            });
        } catch (e) {
            this.notification.add("Could not export to Excel", { type: "danger" });
        } finally {
            this.state.exporting = false;
        }
    }
}

SqlMsAnalyser.template = "database_studio.Analyser";

registry.category("actions").add("database_studio.analyser", SqlMsAnalyser);
