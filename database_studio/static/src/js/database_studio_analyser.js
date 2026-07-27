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

export class SqlMsAnalyser extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.editorRef = useRef("editor");
        this.highlightRef = useRef("highlight");
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
            _qtabSeq: 0,
            loading: false,
            exporting: false,
            favorites: [],
            showFavorites: true,
            showTables: true,
            showViews: true,
            checked: {},
        });

        // Preload a query when opened from the History list / a record button.
        const act = this.props.action || {};
        const incoming = (act.params && act.params.query) ||
            (act.context && act.context.default_query);
        // Start with one query tab (seeded with any preloaded query).
        const first = this._makeQtab(incoming || "");
        this.state.qtabs.push(first);
        this.state.activeQtabId = first.id;
        this.state.query = first.query;
        if (incoming) {
            this.state.activeTab = "query";
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

    _syncEditor() {
        if (this.editorRef.el && this.editorRef.el.value !== this.state.query) {
            this.editorRef.el.value = this.state.query;
        }
        if (this.highlightRef.el) {
            this.highlightRef.el.innerHTML = highlightSql(this.state.query) + "\n";
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
        const id = ++this.state._qtabSeq;
        return {
            id,
            name: "Query " + id,
            query: query || "",
            execQuery: "",
            execWasSelection: false,
            queryResult: null,
        };
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
        }
    }
    _loadQtab(t) {
        this.state.activeQtabId = t.id;
        this.state.query = t.query;
        this.state.execQuery = t.execQuery;
        this.state.execWasSelection = t.execWasSelection;
        this.state.queryResult = t.queryResult;
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
        const query = (t.query || "").trim();
        if (!query) {
            this._doRemoveQtab(id);
            return;
        }
        // Unsaved content — ask whether to save before closing.
        this.dialog.add(SqlMsCloseTabDialog, {
            tabName: t.name,
            defaultName: query.replace(/\s+/g, " ").slice(0, 60),
            onSave: async (name) => {
                await this.orm.call("database.studio.query", "save_query", [query, name || false]);
                this.notification.add("Query saved ★", { type: "success" });
                this._doRemoveQtab(id);
            },
            onDiscard: () => this._doRemoveQtab(id),
        });
    }
    _doRemoveQtab(id) {
        const idx = this.state.qtabs.findIndex((t) => t.id === id);
        if (idx === -1) {
            return;
        }
        const wasActive = id === this.state.activeQtabId;
        this.state.qtabs.splice(idx, 1);
        // Never leave the editor with zero tabs.
        if (!this.state.qtabs.length) {
            const t = this._makeQtab("");
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
    setQuery(text) {
        this.state.query = text;
        if (this.editorRef.el) {
            this.editorRef.el.value = text;
        }
        this._renderHighlight();
    }
    onQueryInput(ev) {
        this.state.query = ev.target.value;
        this._renderHighlight();
    }
    onQueryScroll(ev) {
        if (this.highlightRef.el) {
            this.highlightRef.el.scrollTop = ev.target.scrollTop;
            this.highlightRef.el.scrollLeft = ev.target.scrollLeft;
        }
    }
    _renderHighlight() {
        if (this.highlightRef.el) {
            this.highlightRef.el.innerHTML = highlightSql(this.state.query) + "\n";
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
        this.dialog.add(SqlMsSaveDialog, {
            defaultName: q.replace(/\s+/g, " ").slice(0, 60),
            onConfirm: async (name) => {
                await this.orm.call("database.studio.query", "save_query", [q, name || false]);
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
        // real query analyser; otherwise run the whole editor content.
        const ta = this.editorRef.el;
        if (ta && ta.selectionEnd > ta.selectionStart) {
            const sel = ta.value.substring(ta.selectionStart, ta.selectionEnd).trim();
            if (sel) {
                return { query: sel, isSelection: true };
            }
        }
        return { query: this.state.query, isSelection: false };
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
