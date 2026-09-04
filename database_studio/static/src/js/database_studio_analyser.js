/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { download } from "@web/core/network/download";
import { browser } from "@web/core/browser/browser";
import { ErrorDialog, RPCErrorDialog } from "@web/core/errors/error_dialogs";
import { patch } from "@web/core/utils/patch";
import { Component, useState, useRef, onMounted, onPatched, onWillStart, onWillUnmount } from "@odoo/owl";

/**
 * Universal clipboard copy helper supporting secure (navigator.clipboard)
 * and insecure/HTTP contexts (textarea + execCommand('copy') fallback).
 */
export async function copyToClipboard(text) {
    if (text === null || text === undefined) {
        return false;
    }
    const str = String(text);
    let ok = false;
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function" && window.isSecureContext) {
        try {
            await navigator.clipboard.writeText(str);
            ok = true;
        } catch (e) {
            ok = false;
        }
    }
    if (!ok) {
        try {
            const ta = document.createElement("textarea");
            ta.value = str;
            ta.setAttribute("readonly", "");
            ta.style.position = "fixed";
            ta.style.top = "0";
            ta.style.left = "-9999px";
            ta.style.opacity = "0";
            ta.style.pointerEvents = "none";
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            if (ta.setSelectionRange) {
                ta.setSelectionRange(0, str.length);
            }
            ok = document.execCommand("copy");
            document.body.removeChild(ta);
        } catch (e) {
            ok = false;
        }
    }
    return ok;
}

// Global patch for Odoo error dialogs so "Copy to clipboard" works reliably
// on both HTTPS and HTTP (insecure context) deployments.
if (ErrorDialog) {
    patch(ErrorDialog.prototype, {
        async onClickClipboard() {
            const parts = [
                this.props.name,
                this.props.message,
                this.props.traceback || (this.props.data && this.props.data.debug) || "",
            ].filter(Boolean);
            const text = parts.join("\n\n") || this.props.message || "";
            await copyToClipboard(text);
            this.state.isCopied = true;
        },
    });
}

if (RPCErrorDialog) {
    patch(RPCErrorDialog.prototype, {
        async onClickClipboard() {
            const traceback = this.props.traceback || (this.props.data && this.props.data.debug) || "";
            const parts = [
                this.props.name,
                this.props.message,
                traceback,
            ].filter(Boolean);
            const text = parts.join("\n\n") || this.props.message || "";
            await copyToClipboard(text);
            this.state.isCopied = true;
        },
    });
}

// Fallback for browser.navigator.clipboard.writeText
try {
    if (browser && browser.navigator) {
        if (!browser.navigator.clipboard) {
            try {
                browser.navigator.clipboard = {};
            } catch (e) {
                try {
                    browser.navigator = Object.create(window.navigator);
                    browser.navigator.clipboard = {};
                } catch (e2) {}
            }
        }
        if (browser.navigator.clipboard) {
            const origWrite = typeof browser.navigator.clipboard.writeText === "function"
                ? browser.navigator.clipboard.writeText.bind(browser.navigator.clipboard)
                : null;
            browser.navigator.clipboard.writeText = async function (text) {
                const ok = await copyToClipboard(text);
                if (!ok && origWrite) {
                    return origWrite(text);
                }
            };
        }
    }
} catch (e) {}


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
    "USING", "TRUE", "FALSE", "OVER", "PARTITION", "WINDOW", "INTERSECT",
    "EXCEPT", "LATERAL", "NATURAL", "RECURSIVE", "BEGIN", "DECLARE",
    "COMMIT", "ROLLBACK",
];
const KEYWORD_SET = new Set(KEYWORDS);

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

// `range` (a {start, end} of the executed selection) is painted with a
// selection-like background so the part of the script that was run stays
// visible after Execute — a textarea shows no selection once it loses focus.
function highlightSql(text, range) {
    if (range && range.end > range.start) {
        return highlightSql(text.slice(0, range.start)) +
            '<span class="sqlms-execsel">' +
            highlightSql(text.slice(range.start, range.end)) +
            "</span>" +
            highlightSql(text.slice(range.end));
    }
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

// ---------------------------------------------------------------------
// SQL formatter
//
// A token-driven pretty printer: it re-lays the query out with one clause
// per line and real indentation for sub-queries, CTEs and CASE bodies,
// instead of the old "newline before a few keywords, break after every
// comma" pass which left everything at column zero. String literals,
// comments and dollar-quoted bodies are copied through untouched.
// ---------------------------------------------------------------------

const INDENT_STR = "    ";
const WORD_RE_Y = /[A-Za-z_][A-Za-z0-9_$]*/y;
const NUM_RE_Y = /\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/y;
const PARAM_RE_Y = /\$\d+/y;
const OP_RE_Y = /::|<=|>=|<>|!=|\|\||->>|->|#>>|#>|:=|=|<|>|\+|-|\*|\/|%|\^|~|@|&|\||!|\?|:/y;

// Clause keywords that start a new line, longest phrase first so "UNION ALL"
// wins over "UNION" and "GROUP BY" is never read as a bare "GROUP".
const CLAUSE_PHRASES = [
    ["DELETE", "FROM"], ["INSERT", "INTO"], ["ON", "CONFLICT"],
    ["GROUP", "BY"], ["ORDER", "BY"], ["PARTITION", "BY"],
    ["UNION", "ALL"], ["INTERSECT", "ALL"], ["EXCEPT", "ALL"],
    ["FETCH", "FIRST"], ["FETCH", "NEXT"],
    ["WITH"], ["SELECT"], ["FROM"], ["WHERE"], ["HAVING"], ["WINDOW"],
    ["LIMIT"], ["OFFSET"], ["UNION"], ["INTERSECT"], ["EXCEPT"],
    ["VALUES"], ["UPDATE"], ["SET"], ["RETURNING"],
];
// What each clause does to the lists that follow it.
const CLAUSE_KEY = {
    "SELECT": "select", "FROM": "from", "WHERE": "where", "HAVING": "where",
    "GROUP BY": "group", "ORDER BY": "group", "PARTITION BY": "group",
    "SET": "set", "VALUES": "values", "RETURNING": "select", "WITH": "with",
    "INSERT INTO": "other", "DELETE FROM": "from", "UPDATE": "from",
};
const JOIN_PHRASES = [
    ["LEFT", "OUTER", "JOIN"], ["RIGHT", "OUTER", "JOIN"], ["FULL", "OUTER", "JOIN"],
    ["NATURAL", "LEFT", "JOIN"], ["NATURAL", "RIGHT", "JOIN"],
    ["LEFT", "JOIN"], ["RIGHT", "JOIN"], ["INNER", "JOIN"], ["FULL", "JOIN"],
    ["CROSS", "JOIN"], ["NATURAL", "JOIN"], ["JOIN"],
];
// Statement/block words that always want a line of their own.
const BLOCK_WORDS = new Set(["BEGIN", "DECLARE", "COMMIT", "ROLLBACK"]);
// A clause whose comma-separated list is broken one item per line.
const LIST_CLAUSES = new Set(["select", "from", "set", "values", "with"]);

// Splits the text into tokens, remembering for each whether the source had
// whitespace (and a newline) before it: that is what tells `count(*)` from
// `INSERT INTO t (a, b)`, and a trailing comment from a standalone one.
function tokenizeSql(text) {
    const tokens = [];
    const n = text.length;
    let i = 0;
    let ws = false;
    let nl = false;
    while (i < n) {
        const ch = text[i];
        if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r" || ch === "\f") {
            ws = true;
            nl = nl || ch === "\n";
            i += 1;
            continue;
        }
        let type = null;
        let j = i;
        if (ch === "'" || ch === '"') {
            type = "str";
            j = _skipQuoted(text, i, ch);
        } else if (ch === "-" && text[i + 1] === "-") {
            type = "lcomment";
            j = text.indexOf("\n", i);
            j = j === -1 ? n : j;
        } else if (ch === "/" && text[i + 1] === "*") {
            type = "bcomment";
            j = text.indexOf("*/", i + 2);
            j = j === -1 ? n : j + 2;
        } else if (ch === "$") {
            const k = _skipDollarQuoted(text, i);
            if (k > i) {
                type = "str";
                j = k;
            } else {
                PARAM_RE_Y.lastIndex = i;
                const param = PARAM_RE_Y.exec(text);
                if (param) {
                    type = "num";
                    j = i + param[0].length;
                }
            }
        }
        if (type === null) {
            WORD_RE_Y.lastIndex = i;
            const word = WORD_RE_Y.exec(text);
            if (word) {
                type = "word";
                j = i + word[0].length;
            }
        }
        if (type === null) {
            NUM_RE_Y.lastIndex = i;
            const num = NUM_RE_Y.exec(text);
            if (num) {
                type = "num";
                j = i + num[0].length;
            }
        }
        if (type === null && "(),;.".indexOf(ch) !== -1) {
            type = "punct";
            j = i + 1;
        }
        if (type === null) {
            OP_RE_Y.lastIndex = i;
            const op = OP_RE_Y.exec(text);
            type = "op";
            j = i + (op ? op[0].length : 1);
        }
        const value = text.slice(i, j);
        tokens.push({
            type,
            value,
            wsBefore: ws,
            nlBefore: nl,
            upper: type === "word" ? value.toUpperCase() : "",
        });
        ws = false;
        nl = false;
        i = j;
    }
    return tokens;
}

function formatSql(text) {
    if (!text || !text.trim()) {
        return text;
    }
    const tokens = tokenizeSql(text);
    if (!tokens.length) {
        return text;
    }

    const lines = [];
    let cur = "";
    let curIndent = 0;
    let indent = 0;
    let clause = "";
    let parens = [];
    let cases = [];
    let glueNext = false;
    let pendingBetween = false;

    function flush() {
        if (cur.length) {
            lines.push(INDENT_STR.repeat(curIndent) + cur);
            cur = "";
        }
    }
    // Ends the current line and sets the indent the next one starts at.
    function newline(level) {
        flush();
        curIndent = level === undefined ? indent : Math.max(0, level);
        glueNext = false;
    }
    function add(value, glue) {
        const tight = glue === "none" || glueNext;
        glueNext = false;
        cur = cur.length ? cur + (tight ? "" : " ") + value : value;
    }

    function wordAt(k) {
        const t = tokens[k];
        return t && t.type === "word" ? t.upper : null;
    }
    function matchPhrase(k, phrases) {
        for (const phrase of phrases) {
            let hit = true;
            for (let d = 0; d < phrase.length; d++) {
                if (wordAt(k + d) !== phrase[d]) {
                    hit = false;
                    break;
                }
            }
            if (hit) {
                return phrase;
            }
        }
        return null;
    }
    // True while the innermost parenthesis is an ordinary one (a function
    // call or an IN list): its contents are kept on one line.
    function inPlainParen() {
        return parens.length > 0 && !parens[parens.length - 1].sub;
    }
    // "(" opens a sub-query — and so gets its own indented block — when the
    // first thing inside it starts a query.
    function opensSubquery(k) {
        const next = wordAt(k + 1);
        return next === "SELECT" || next === "WITH" || next === "VALUES";
    }
    // Whether the select list about to start holds more than one item, which
    // is what decides between "SELECT a" and a column-per-line block.
    function listIsMulti(k) {
        let depth = 0;
        for (let x = k; x < tokens.length; x++) {
            const t = tokens[x];
            if (t.type !== "punct") {
                if (depth === 0 && t.type === "word" &&
                        matchPhrase(x, CLAUSE_PHRASES) && t.upper !== "VALUES") {
                    return false;
                }
                if (depth === 0 && t.type === "word" && t.upper === "INTO") {
                    return false;
                }
                continue;
            }
            if (t.value === "(") {
                depth += 1;
            } else if (t.value === ")") {
                if (depth === 0) {
                    return false;
                }
                depth -= 1;
            } else if (t.value === ";") {
                return false;
            } else if (t.value === "," && depth === 0) {
                return true;
            }
        }
        return false;
    }

    let i = 0;
    while (i < tokens.length) {
        const tok = tokens[i];

        if (tok.type === "lcomment") {
            // A comment that stood on its own line keeps its own line; one
            // that trailed code stays at the end of that code. Either way the
            // line after it resumes at the indent the comment sat at, so a
            // comment in the middle of a select list doesn't reset it.
            if (tok.nlBefore && cur.length) {
                newline(curIndent);
            }
            const level = curIndent;
            add(tok.value);
            newline(level);
            i += 1;
            continue;
        }
        if (tok.type === "bcomment") {
            add(tok.value);
            i += 1;
            continue;
        }
        if (tok.type === "punct") {
            if (tok.value === "(") {
                const sub = opensSubquery(i);
                add("(", tok.wsBefore ? undefined : "none");
                parens.push({
                    sub,
                    savedIndent: indent,
                    savedClause: clause,
                    savedCases: cases.length,
                });
                if (sub) {
                    indent += 1;
                    newline(indent);
                    clause = "";
                } else {
                    glueNext = true;
                }
                i += 1;
                continue;
            }
            if (tok.value === ")") {
                const open = parens.pop();
                if (open && open.sub) {
                    indent = open.savedIndent;
                    newline(indent);
                    add(")");
                } else {
                    add(")", "none");
                }
                if (open) {
                    clause = open.savedClause;
                    cases.length = Math.min(cases.length, open.savedCases);
                }
                i += 1;
                continue;
            }
            if (tok.value === ",") {
                add(",", "none");
                if (!inPlainParen() && LIST_CLAUSES.has(clause)) {
                    newline(clause === "with" ? indent : indent + 1);
                }
                i += 1;
                continue;
            }
            if (tok.value === ";") {
                add(";", "none");
                flush();
                lines.push("");
                indent = 0;
                curIndent = 0;
                clause = "";
                parens = [];
                cases = [];
                pendingBetween = false;
                i += 1;
                continue;
            }
            if (tok.value === ".") {
                add(".", "none");
                glueNext = true;
                i += 1;
                continue;
            }
        }
        if (tok.type === "op") {
            if (tok.value === "::") {
                add("::", "none");
                glueNext = true;
                i += 1;
                continue;
            }
            const prev = tokens[i - 1];
            const unary = (tok.value === "-" || tok.value === "+") &&
                (!prev || prev.type === "op" ||
                    (prev.type === "punct" && prev.value !== ")"));
            add(tok.value);
            if (unary) {
                glueNext = true;
            }
            i += 1;
            continue;
        }
        if (tok.type !== "word") {
            add(tok.value);
            i += 1;
            continue;
        }

        // -- words --------------------------------------------------------
        const plain = inPlainParen();
        const join = plain ? null : matchPhrase(i, JOIN_PHRASES);
        if (join) {
            newline(indent);
            for (const w of join) {
                add(w);
                i += 1;
            }
            clause = "join";
            continue;
        }
        const phrase = plain ? null : matchPhrase(i, CLAUSE_PHRASES);
        if (phrase) {
            newline(indent);
            for (const w of phrase) {
                add(w);
                i += 1;
            }
            clause = CLAUSE_KEY[phrase.join(" ")] || "other";
            if (clause === "select") {
                if (wordAt(i) === "DISTINCT" || wordAt(i) === "ALL") {
                    add(tokens[i].upper);
                    i += 1;
                    if (wordAt(i) === "ON") {
                        add("ON");
                        i += 1;
                    }
                }
                if (listIsMulti(i)) {
                    newline(indent + 1);
                }
            }
            pendingBetween = false;
            continue;
        }
        const upper = tok.upper;
        if (upper === "CASE") {
            cases.push({ savedIndent: indent, base: curIndent });
            add("CASE");
            indent = curIndent + 1;
            i += 1;
            continue;
        }
        if ((upper === "WHEN" || upper === "ELSE") && cases.length) {
            newline(indent);
            add(upper);
            i += 1;
            continue;
        }
        if (upper === "END" && cases.length) {
            const open = cases.pop();
            indent = open.savedIndent;
            newline(open.base);
            add("END");
            i += 1;
            continue;
        }
        if ((upper === "AND" || upper === "OR") && !plain) {
            if (pendingBetween && upper === "AND") {
                pendingBetween = false;
                add("AND");
            } else if (clause === "where" || clause === "on") {
                newline(indent + 1);
                add(upper);
            } else {
                add(upper);
            }
            i += 1;
            continue;
        }
        if (upper === "BETWEEN") {
            pendingBetween = true;
            add("BETWEEN");
            i += 1;
            continue;
        }
        if (upper === "ON" && clause === "join") {
            clause = "on";
            add("ON");
            i += 1;
            continue;
        }
        if (BLOCK_WORDS.has(upper) && !plain && !parens.length) {
            newline(indent);
            add(upper);
            i += 1;
            continue;
        }
        add(KEYWORD_SET.has(upper) ? upper : tok.value);
        i += 1;
    }
    flush();
    // Collapse the run of blank lines a trailing ';' can leave behind.
    return lines
        .join("\n")
        .replace(/\n{3,}/g, "\n\n")
        .replace(/\s+$/, "");
}

// ---------------------------------------------------------------------
// Statement outline + folding
//
// The editor is ONE textarea holding the whole query: splitting the text
// into a textarea per ';' used to break scripts (a DECLARE ... BEGIN ... END
// body, or anything else carrying inner semicolons, was torn into pieces
// that could no longer be selected and run as a whole). Statements are now
// only an *outline*: the scanner below finds their ranges so a fold icon can
// be offered in the gutter, and folding merely swaps a statement's text for
// a comment placeholder inside that same textarea.
// ---------------------------------------------------------------------

// Smallest a dragged panel may be made, so neither can be collapsed to
// nothing and left with no bar to drag back. The sidebar figure matches its
// CSS min-width, which would otherwise silently win over a smaller one here.
const RESIZE_MIN = { sidebar: 240, editor: 140 };

// Both must match the editor CSS (padding / line-height) so the gutter's
// fold icons line up with the lines they belong to.
const EDITOR_PAD_TOP = 10;
const EDITOR_LINE_H = 20;

// Skips a '...' or "..." literal starting at i, returning the index just
// past its closing quote ('' inside a string is an escaped quote).
function _skipQuoted(text, i, quote) {
    const n = text.length;
    let j = i + 1;
    while (j < n) {
        if (text[j] === quote) {
            if (quote === "'" && text[j + 1] === "'") {
                j += 2;
                continue;
            }
            return j + 1;
        }
        j += 1;
    }
    return n;
}

// Skips a $tag$ ... $tag$ literal starting at i. Dollar quoting is how a
// plpgsql body (DO $$ DECLARE ... BEGIN ... END $$) carries semicolons, so
// missing it here is exactly what used to chop such a script apart.
// Returns i unchanged when this '$' does not open one (e.g. a $1 parameter).
function _skipDollarQuoted(text, i) {
    const open = /^\$([A-Za-z_][A-Za-z0-9_]*)?\$/.exec(text.slice(i, i + 64));
    if (!open) {
        return i;
    }
    const tag = open[0];
    const close = text.indexOf(tag, i + tag.length);
    return close === -1 ? text.length : close + tag.length;
}

// Replaces single-quoted string literals, comments and dollar-quoted bodies
// with blanks (preserving length), so keywords/identifiers are counted and
// extracted cleanly without matching contents of string literals or comments.
// Note: Double-quoted strings ("...") are SQL identifiers (tables, columns)
// and must NOT be stripped.
function stripNonCode(text) {
    let out = "";
    let i = 0;
    const n = text.length;
    while (i < n) {
        const ch = text[i];
        let j = i;
        if (ch === "'") {
            j = _skipQuoted(text, i, ch);
        } else if (ch === "-" && text[i + 1] === "-") {
            j = text.indexOf("\n", i);
            j = j === -1 ? n : j;
        } else if (ch === "/" && text[i + 1] === "*") {
            j = text.indexOf("*/", i + 2);
            j = j === -1 ? n : j + 2;
        } else if (ch === "$") {
            j = _skipDollarQuoted(text, i);
        }
        if (j > i) {
            out += text.slice(i, j).replace(/[^\n]/g, " ");
            i = j;
        } else {
            out += ch;
            i += 1;
        }
    }
    return out;
}

// How many block levels a statement opens (BEGIN/CASE) minus how many it
// closes (END), so a T-SQL style BEGIN ... END body is outlined as one
// section instead of one per inner ';'. A bare transaction BEGIN opens
// nothing, and COMMIT/ROLLBACK close whatever is open.
function _blockDelta(segment) {
    const code = stripNonCode(segment);
    if (/^\s*BEGIN(\s+(WORK|TRANSACTION)\b[\s\S]*)?$/i.test(code)) {
        return 0;
    }
    if (/\b(COMMIT|ROLLBACK)\b/i.test(code)) {
        return -1;
    }
    const opens = (code.match(/\b(BEGIN|CASE)\b/gi) || []).length;
    const closes = (code.match(/\bEND\b/gi) || []).length;
    return opens - closes;
}

// Character ranges of the top-level statements in `text`, each trimmed of
// surrounding whitespace (so folding a statement never eats the blank line
// that separates it from the next one). Semicolons inside strings, quoted
// identifiers, comments and dollar-quoted bodies are not separators.
export function findStatementRanges(text) {
    const raw = [];
    let segStart = 0;
    let i = 0;
    const n = text.length;
    while (i < n) {
        const ch = text[i];
        if (ch === "'" || ch === '"') {
            i = _skipQuoted(text, i, ch);
        } else if (ch === "-" && text[i + 1] === "-") {
            const j = text.indexOf("\n", i);
            i = j === -1 ? n : j;
        } else if (ch === "/" && text[i + 1] === "*") {
            const j = text.indexOf("*/", i + 2);
            i = j === -1 ? n : j + 2;
        } else if (ch === "$") {
            const j = _skipDollarQuoted(text, i);
            i = j > i ? j : i + 1;
        } else if (ch === ";") {
            raw.push([segStart, i]);
            segStart = i + 1;
            i += 1;
        } else {
            i += 1;
        }
    }
    if (segStart < n) {
        raw.push([segStart, n]);
    }
    // Merge the pieces of an unfinished block back together.
    const merged = [];
    let depth = 0;
    let open = null;
    for (const [s, e] of raw) {
        if (open === null) {
            open = s;
        }
        depth = Math.max(0, depth + _blockDelta(text.slice(s, e)));
        if (depth === 0) {
            merged.push([open, e]);
            open = null;
        }
    }
    if (open !== null) {
        merged.push([open, n]);
    }
    // Trim, dropping ranges that hold nothing but whitespace.
    const out = [];
    for (const [s, e] of merged) {
        const seg = text.slice(s, e);
        const lead = seg.length - seg.replace(/^\s+/, "").length;
        const trail = seg.length - seg.replace(/\s+$/, "").length;
        if (s + lead < e - trail) {
            out.push({ start: s + lead, end: e - trail });
        }
    }
    return out;
}

// A folded statement is replaced, in the editor text itself, by this
// one-line block comment. Being a real SQL comment means a fold that is
// somehow executed (e.g. the user selects across it) is simply ignored by
// Postgres rather than being a syntax error.
let _foldIdSeq = 0;
const FOLD_MARK = "/* \u25b8 fold#";
const FOLD_RE_G = /\/\* \u25b8 fold#(\d+):[\s\S]*?\*\//g;

function foldPlaceholder(id, preview, lines) {
    return FOLD_MARK + id + ": " + preview + " \u2026 (" + lines + " lines) */";
}
function foldRe(id) {
    return new RegExp("\\/\\* \\u25b8 fold#" + id + ":[\\s\\S]*?\\*\\/");
}

// Editor text -> the real query: every placeholder swapped back for the
// text it stands for. Runs to a fixed point so a fold nested inside another
// folded statement is restored too.
export function expandFolds(text, folds) {
    if (!folds || !Object.keys(folds).length || text.indexOf(FOLD_MARK) === -1) {
        return text;
    }
    let out = text;
    for (let pass = 0; pass < 10; pass++) {
        let changed = false;
        out = out.replace(FOLD_RE_G, (m, id) => {
            const f = folds[id];
            if (!f) {
                return m;
            }
            changed = true;
            return f.text;
        });
        if (!changed) {
            break;
        }
    }
    return out;
}

// Tab ids only need to be unique within one page load, and the History
// list needs to mint them without an Analyser instance to hand a counter out
// from — so these live at module scope rather than on component state.
let _qtabIdSeq = 0;

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
        // `query` is the real SQL; `display` is what the textarea shows,
        // which differs only while statements are folded (see expandFolds).
        query: query || "",
        display: query || "",
        folds: {},
        execQuery: "",
        execRange: null,
        queryResult: null,
        selectedCols: [],
        aggFunc: "",
        historyId: opts.historyId || null,
        isSaved: !!opts.isSaved,
        // Set for a tab holding a view's own definition (see showViewScript):
        // the view it came from, and the flag that stops closing it from
        // asking to save something the database already holds.
        viewName: opts.viewName || null,
        isScript: !!opts.viewName,
    };
}

// Holds the Analyser's whole workspace between visits. Odoo doesn't keep
// client-action controllers alive off-screen the way it does act_window
// breadcrumbs, so stepping out to *any* other menu destroys the component
// outright — there is no live instance left to call back into. This holds
// actual state *data*, not a component reference, so a plain object
// surviving in this module is what bridges the trip away and back: the open
// query tabs and their results, plus what the Fields and Mapping tabs were
// showing. It doubles as the hand-off for a query picked in the History
// list (see database_studio_history_list.js), which appends its tab to
// whatever is already parked here.
export const analyserRegistry = { pending: null };

// Everything outside the query tabs that makes up "where I was": the picked
// object on the left and the two other tabs' contents. Snapshotted and
// restored wholesale so returning to the Analyser puts back the same view of
// it rather than a blank Fields/Mapping pane.
const SESSION_KEYS = [
    "activeTab", "selected", "selectedType", "filter", "searchMode",
    "showFavorites", "showTables", "showViews", "checked",
    "fieldGroups", "collapsedGroups", "fieldFilter", "fieldSel", "fieldCols",
    "mapping", "mappingCols",
];

// The snapshot lives only as long as the browser tab does, but a stale one
// resurfacing a day later would be a surprise rather than a convenience.
// This is generous enough to cover a working day's worth of stepping away
// and back, and short enough that tomorrow starts clean.
const PENDING_TTL_MS = 12 * 60 * 60 * 1000;

// The Fields tab's copyable columns, in the order Copy writes them. `table`
// has no header cell of its own (it is the group title above each grid), so
// it cannot be picked — it is only written when nothing is picked at all.
const FIELD_COLUMNS = [
    { key: "table", label: "table" },
    { key: "name", label: "name" },
    { key: "type", label: "type" },
    { key: "precision", label: "precision/length" },
    { key: "nullable", label: "nullable" },
];

// Same, for the Mapping tab. Every one of these has a header, so any of them
// can be picked.
const MAPPING_COLUMNS = [
    { key: "from_table", label: "from_table" },
    { key: "from_column", label: "from_column" },
    { key: "to_table", label: "to_table" },
    { key: "to_column", label: "to_column" },
    { key: "via", label: "via" },
];

// The numeric types a text column can be converted to, in the order the
// dialog offers them.
export const CONVERT_TARGETS = [
    { value: "numeric", label: "Number (numeric) — decimals kept exactly" },
    { value: "integer", label: "Whole number (integer) — decimals rounded" },
    { value: "bigint", label: "Large whole number (bigint) — decimals rounded" },
    { value: "double precision", label: "Floating point (double precision)" },
];

// Name of the pseudo-table the Fields tab uses for a query's own output
// columns, which belong to no real table.
export const RESULT_GROUP = "query result";

// Converts the text columns ticked in the Fields tab into a numeric type.
// Two shapes, depending on where the ticked columns came from:
//   * a real table — DDL on the live database, so the dialog dry-runs it first
//     (what each column holds, what would not cast, which views are in the
//     way) and shows the exact ALTER TABLE before anything is written;
//   * a query's result columns — there is nothing to ALTER, so the query is
//     rewritten to cast them, and nothing in the database changes.
export class SqlMsConvertTypeDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            target: "numeric",
            blankBad: false,
            loading: true,
            converting: false,
            report: null,
            error: "",
            showSql: false,
        });
        onWillStart(() => this.check());
    }
    get targets() {
        return CONVERT_TARGETS;
    }
    get isQuery() {
        return this.props.mode === "query";
    }
    async check() {
        this.state.loading = true;
        this.state.error = "";
        try {
            this.state.report = this.isQuery
                ? await this.orm.call(
                    "database.studio.analyser", "check_query_conversion",
                    [this.props.query, this.props.items.map((i) => i.name),
                     this.state.target, this.state.blankBad]
                )
                : await this.orm.call(
                    "database.studio.analyser", "check_column_conversion",
                    [this.props.items, this.state.target]
                );
        } catch (e) {
            this.state.report = null;
            this.state.error = this._errorText(e);
        } finally {
            this.state.loading = false;
        }
    }
    _errorText(e) {
        return (e && e.data && e.data.message) || (e && e.message) || String(e);
    }
    onTargetChange(ev) {
        this.state.target = ev.target.value;
        this.check();
    }
    // Rewriting a query, the "leave the bad values out" choice changes the
    // generated SQL, so the preview has to be rebuilt for it to stay honest.
    onBlankBadChange(ev) {
        this.state.blankBad = ev.target.checked;
        if (this.isQuery) {
            this.check();
        }
    }
    get columns() {
        return (this.state.report && this.state.report.columns) || [];
    }
    get convertible() {
        return this.columns.filter((c) => c.convertible);
    }
    get skipped() {
        return this.columns.filter((c) => !c.convertible);
    }
    // Values that will not cast. Unless the user agrees to blank them the
    // ALTER would fail part way through, so this gates the Convert button.
    get badTotal() {
        return this.convertible.reduce((n, c) => n + (c.bad || 0), 0);
    }
    get blankTotal() {
        return this.convertible.reduce((n, c) => n + (c.blanks || 0), 0);
    }
    get roundTotal() {
        return this.convertible.reduce((n, c) => n + (c.fractional || 0), 0);
    }
    get canConvert() {
        return !!(this.state.report && this.state.report.can_convert) &&
            !this.state.loading && !this.state.converting &&
            (this.badTotal === 0 || this.state.blankBad);
    }
    toggleSql() {
        this.state.showSql = !this.state.showSql;
    }
    async confirm() {
        if (!this.canConvert) {
            return;
        }
        if (this.isQuery) {
            // Nothing to execute: the rewritten query is the whole result.
            this.props.onApply(this.state.report.sql);
            this.props.close();
            return;
        }
        this.state.converting = true;
        this.state.error = "";
        let res;
        try {
            res = await this.orm.call(
                "database.studio.analyser", "convert_columns",
                [this.convertible.map((c) => ({ table: c.table, name: c.name })),
                 this.state.target, this.state.blankBad]
            );
        } catch (e) {
            this.state.error = this._errorText(e);
            return;
        } finally {
            this.state.converting = false;
        }
        this.props.onDone(res);
        this.props.close();
    }
}
SqlMsConvertTypeDialog.template = "database_studio.ConvertTypeDialog";
SqlMsConvertTypeDialog.components = { Dialog };
SqlMsConvertTypeDialog.props = {
    close: Function,
    items: Array,
    mode: { type: String, optional: true },
    query: { type: String, optional: true },
    onDone: { type: Function, optional: true },
    onApply: { type: Function, optional: true },
};
SqlMsConvertTypeDialog.defaultProps = { mode: "table", query: "" };

// ---------------------------------------------------------------------
// SQL Query Autocomplete & Intelligent Suggestions
// ---------------------------------------------------------------------

const SQL_AUTOCOMPLETE_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN",
    "FULL JOIN", "CROSS JOIN", "ON", "GROUP BY", "ORDER BY", "HAVING", "LIMIT",
    "OFFSET", "AS", "AND", "OR", "NOT", "IN", "IS NULL", "IS NOT NULL", "LIKE",
    "ILIKE", "BETWEEN", "EXISTS", "DISTINCT", "UNION", "UNION ALL", "INTERSECT",
    "EXCEPT", "CASE", "WHEN", "THEN", "ELSE", "END", "WITH", "WITH RECURSIVE",
    "INSERT INTO", "VALUES", "UPDATE", "SET", "DELETE FROM", "CREATE TABLE",
    "ALTER TABLE", "DROP TABLE", "TRUNCATE", "ASC", "DESC", "NULLS FIRST",
    "NULLS LAST", "COALESCE", "NULLIF", "CAST", "RETURNING", "OVER", "PARTITION BY"
];

const SQL_AUTOCOMPLETE_FUNCTIONS = [
    { name: "COUNT(*)", insertText: "COUNT(*)", detail: "Count rows" },
    { name: "COUNT()", insertText: "COUNT()", cursorOffset: 6, detail: "Count expression" },
    { name: "SUM()", insertText: "SUM()", cursorOffset: 4, detail: "Sum values" },
    { name: "AVG()", insertText: "AVG()", cursorOffset: 4, detail: "Average value" },
    { name: "MIN()", insertText: "MIN()", cursorOffset: 4, detail: "Minimum value" },
    { name: "MAX()", insertText: "MAX()", cursorOffset: 4, detail: "Maximum value" },
    { name: "COALESCE()", insertText: "COALESCE()", cursorOffset: 9, detail: "First non-null" },
    { name: "CONCAT()", insertText: "CONCAT()", cursorOffset: 7, detail: "Concatenate strings" },
    { name: "SUBSTRING()", insertText: "SUBSTRING()", cursorOffset: 10, detail: "Extract substring" },
    { name: "LOWER()", insertText: "LOWER()", cursorOffset: 6, detail: "Lower-case text" },
    { name: "UPPER()", insertText: "UPPER()", cursorOffset: 6, detail: "Upper-case text" },
    { name: "TRIM()", insertText: "TRIM()", cursorOffset: 5, detail: "Trim whitespace" },
    { name: "REPLACE()", insertText: "REPLACE()", cursorOffset: 8, detail: "Replace substring" },
    { name: "LENGTH()", insertText: "LENGTH()", cursorOffset: 7, detail: "String length" },
    { name: "SPLIT_PART()", insertText: "SPLIT_PART()", cursorOffset: 11, detail: "Split string" },
    { name: "NOW()", insertText: "NOW()", detail: "Current timestamp" },
    { name: "CURRENT_DATE", insertText: "CURRENT_DATE", detail: "Current date" },
    { name: "CURRENT_TIMESTAMP", insertText: "CURRENT_TIMESTAMP", detail: "Current timestamp" },
    { name: "DATE_TRUNC()", insertText: "DATE_TRUNC('month', )", cursorOffset: 20, detail: "Truncate timestamp" },
    { name: "AGE()", insertText: "AGE()", cursorOffset: 4, detail: "Calculate age/interval" },
    { name: "EXTRACT()", insertText: "EXTRACT(YEAR FROM )", cursorOffset: 18, detail: "Extract date field" },
    { name: "TO_CHAR()", insertText: "TO_CHAR()", cursorOffset: 8, detail: "Format to string" },
    { name: "TO_DATE()", insertText: "TO_DATE()", cursorOffset: 8, detail: "Parse to date" },
    { name: "ROUND()", insertText: "ROUND()", cursorOffset: 6, detail: "Round number" },
    { name: "FLOOR()", insertText: "FLOOR()", cursorOffset: 6, detail: "Floor number" },
    { name: "CEIL()", insertText: "CEIL()", cursorOffset: 5, detail: "Ceiling number" },
    { name: "ABS()", insertText: "ABS()", cursorOffset: 4, detail: "Absolute value" },
    { name: "STRING_AGG()", insertText: "STRING_AGG(, ', ')", cursorOffset: 11, detail: "Aggregate strings" },
    { name: "ARRAY_AGG()", insertText: "ARRAY_AGG()", cursorOffset: 10, detail: "Aggregate to array" },
    { name: "JSON_AGG()", insertText: "JSON_AGG()", cursorOffset: 9, detail: "Aggregate to JSON array" },
    { name: "JSONB_AGG()", insertText: "JSONB_AGG()", cursorOffset: 10, detail: "Aggregate to JSONB array" },
    { name: "JSONB_BUILD_OBJECT()", insertText: "JSONB_BUILD_OBJECT()", cursorOffset: 19, detail: "Build JSONB object" },
    { name: "ROW_NUMBER() OVER ()", insertText: "ROW_NUMBER() OVER (PARTITION BY  ORDER BY )", cursorOffset: 32, detail: "Window row number" },
    { name: "DENSE_RANK() OVER ()", insertText: "DENSE_RANK() OVER (ORDER BY )", cursorOffset: 28, detail: "Window dense rank" },
    { name: "LAG() OVER ()", insertText: "LAG() OVER (ORDER BY )", cursorOffset: 21, detail: "Window lag value" },
    { name: "LEAD() OVER ()", insertText: "LEAD() OVER (ORDER BY )", cursorOffset: 22, detail: "Window lead value" },
];

const CARET_STYLE_PROPERTIES = [
    "direction", "boxSizing", "width", "height", "overflowX", "overflowY",
    "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth", "borderStyle",
    "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
    "fontStyle", "fontVariant", "fontWeight", "fontStretch", "fontSize", "fontSizeAdjust",
    "lineHeight", "fontFamily", "textAlign", "textTransform", "textIndent",
    "textDecoration", "letterSpacing", "wordSpacing", "tabSize", "MozTabSize"
];

function getCaretCoordinates(element, position) {
    if (!element) return { top: 10, left: 32, lineHeight: 20 };
    const div = document.createElement("div");
    div.id = "sqlms-caret-position-mirror";
    document.body.appendChild(div);

    const style = div.style;
    const computed = window.getComputedStyle(element);

    style.whiteSpace = "pre";
    style.position = "absolute";
    style.visibility = "hidden";
    style.top = "0";
    style.left = "-9999px";

    CARET_STYLE_PROPERTIES.forEach((prop) => {
        style[prop] = computed[prop];
    });

    style.overflow = "hidden";

    div.textContent = element.value.substring(0, position);

    const span = document.createElement("span");
    span.textContent = element.value.substring(position) || ".";
    div.appendChild(span);

    const coordinates = {
        top: span.offsetTop + parseInt(computed.borderTopWidth || 0, 10),
        left: span.offsetLeft + parseInt(computed.borderLeftWidth || 0, 10),
        lineHeight: parseInt(computed.lineHeight, 10) || 20,
    };

    document.body.removeChild(div);
    return coordinates;
}

function findTableSchema(schemaCache, tableName) {
    if (!tableName || !schemaCache) return null;
    let clean = String(tableName).replace(/['"`]/g, "").trim();
    if (clean.includes(".")) {
        clean = clean.split(".").pop();
    }
    if (schemaCache[clean]) return { name: clean, info: schemaCache[clean] };
    const lower = clean.toLowerCase();
    for (const [key, val] of Object.entries(schemaCache)) {
        if (key.toLowerCase() === lower) {
            return { name: key, info: val };
        }
    }
    return null;
}

function extractTablesAndAliases(sqlText) {
    const cleanSql = stripNonCode(sqlText || "");
    const tables = [];
    const aliases = {};
    const reservedWords = new Set([
        "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "CROSS", "FULL", "ON",
        "GROUP", "ORDER", "LIMIT", "OFFSET", "HAVING", "SET", "UNION", "SELECT", "USING",
        "NATURAL", "AND", "OR", "AS", "BY", "ASC", "DESC", "IN", "NOT", "NULL", "IS",
        "CASE", "WHEN", "THEN", "ELSE", "END", "FROM", "INTO", "UPDATE", "TABLE", "VALUES",
        "WITH", "RETURNING", "DISTINCT", "ALL", "EXISTS", "BETWEEN", "LIKE", "ILIKE"
    ]);

    const normalize = (name) => {
        if (!name) return "";
        let clean = name.replace(/['"`]/g, "").trim();
        if (clean.includes(".")) {
            clean = clean.split(".").pop();
        }
        return clean;
    };

    const addTableAndAlias = (tblName, aliasName) => {
        const rawTable = normalize(tblName);
        if (rawTable && !reservedWords.has(rawTable.toUpperCase())) {
            if (!tables.some((t) => t.toLowerCase() === rawTable.toLowerCase())) {
                tables.push(rawTable);
            }
            const normAlias = normalize(aliasName);
            if (normAlias && !reservedWords.has(normAlias.toUpperCase()) && normAlias.toLowerCase() !== rawTable.toLowerCase()) {
                aliases[normAlias.toLowerCase()] = rawTable;
            }
        }
    };

    // 1. Scan for FROM / INTO / UPDATE / JOIN blocks
    const clauseRegex = /\b(?:FROM|INTO|UPDATE|(?:(?:LEFT|RIGHT|FULL|INNER|CROSS|NATURAL|OUTER)\s+)*JOIN)\s+([^;]+?)(?=\b(?:WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|OFFSET|UNION|ON|USING|SET|RETURNING|WINDOW|VALUES|\)|\;|$))/gi;
    let match;
    while ((match = clauseRegex.exec(cleanSql)) !== null) {
        const clauseBody = match[1];
        const subParts = clauseBody.split(/,|\b(?:INNER|LEFT|RIGHT|FULL|CROSS|NATURAL|OUTER)?\s*JOIN\b/i);
        for (let part of subParts) {
            part = part.trim();
            if (!part || part.startsWith("(")) continue;
            const tokens = part.split(/\s+/).filter(Boolean);
            if (tokens.length >= 1) {
                const rawTable = tokens[0];
                let alias = null;
                if (tokens.length >= 2) {
                    if (tokens[1].toUpperCase() === "AS" && tokens[2]) {
                        alias = tokens[2];
                    } else if (tokens[1].toUpperCase() !== "AS") {
                        alias = tokens[1];
                    }
                }
                addTableAndAlias(rawTable, alias);
            }
        }
    }

    // 2. Direct regex scan for table + alias patterns (e.g. `FROM table alias`, `JOIN table alias`, `FROM table AS alias`)
    const directRegex = /\b(?:FROM|JOIN|UPDATE|INTO)\s+([a-zA-Z0-9_."`]+)(?:\s+(?:AS\s+)?([a-zA-Z0-9_"`]+))?/gi;
    while ((match = directRegex.exec(cleanSql)) !== null) {
        addTableAndAlias(match[1], match[2]);
    }

    // 3. Comma-separated tables in FROM clause (e.g. `FROM t1 a, t2 b, t3 c`)
    const fromListMatch = /\bFROM\s+([^;]+?)(?=\b(?:WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|OFFSET|UNION|JOIN|\)|\;|$))/gi;
    while ((match = fromListMatch.exec(cleanSql)) !== null) {
        const parts = match[1].split(",");
        for (let p of parts) {
            p = p.trim();
            if (!p || p.startsWith("(")) continue;
            const tokens = p.split(/\s+/).filter(Boolean);
            if (tokens.length >= 1) {
                let alias = null;
                if (tokens.length >= 2) {
                    if (tokens[1].toUpperCase() === "AS" && tokens[2]) {
                        alias = tokens[2];
                    } else if (tokens[1].toUpperCase() !== "AS") {
                        alias = tokens[1];
                    }
                }
                addTableAndAlias(tokens[0], alias);
            }
        }
    }

    return { tables, aliases };
}

function detectSqlContext(cleanBefore) {
    const kwRegex = /\b(SELECT|FROM|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN|CROSS\s+JOIN|JOIN|WHERE|ON|USING|GROUP\s+BY|ORDER\s+BY|HAVING|SET|INTO|UPDATE|TABLE|VALUES)\b/gi;
    let lastKw = "";
    let lastMatch = null;
    let m;
    while ((m = kwRegex.exec(cleanBefore)) !== null) {
        lastMatch = m;
        lastKw = m[1].toUpperCase().replace(/\s+/g, " ");
    }

    if (!lastKw) {
        return { clause: "", isTableContext: false, isFieldContext: false };
    }

    const afterKw = cleanBefore.substring(lastMatch.index + lastMatch[0].length).trim();

    if (lastKw === "FROM" || lastKw.includes("JOIN") || lastKw === "INTO" || lastKw === "UPDATE" || lastKw === "TABLE") {
        const wordsAfter = afterKw.split(/\s+/).filter(Boolean);
        const isTableContext = wordsAfter.length <= 1 && !afterKw.includes(",");
        return {
            clause: lastKw,
            isTableContext,
            isFieldContext: !isTableContext,
        };
    }

    const isFieldContext = ["SELECT", "WHERE", "ON", "USING", "GROUP BY", "ORDER BY", "HAVING", "SET"].includes(lastKw);
    return {
        clause: lastKw,
        isTableContext: false,
        isFieldContext,
    };
}

function formatMatchParts(text, prefix) {
    if (!prefix) return null;
    const lower = text.toLowerCase();
    const pLower = prefix.toLowerCase();
    const idx = lower.indexOf(pLower);
    if (idx === -1) return null;
    return {
        pre: text.substring(0, idx),
        match: text.substring(idx, idx + prefix.length),
        post: text.substring(idx + prefix.length),
    };
}

function getAutocompleteSuggestions(fullText, caretPos, schemaCache, knownTables, knownViews) {
    const textBefore = fullText.substring(0, caretPos);
    if (!textBefore) return { items: [], replaceStart: 0, replaceEnd: 0, prefix: "" };

    const cleanBefore = stripNonCode(textBefore);
    const { tables: queryTables, aliases } = extractTablesAndAliases(fullText);
    const { clause, isTableContext, isFieldContext } = detectSqlContext(cleanBefore);

    // Check if after dot (e.g. `res_partner.` or `rp.` or `"res_partner".` or `"rp".` or `th.trn`)
    const dotMatch = /["`]?([a-zA-Z0-9_]+)["`]?\.["`]?([a-zA-Z0-9_]*)$/.exec(textBefore);
    if (dotMatch) {
        const qualifier = dotMatch[1].toLowerCase();
        const fieldPrefix = dotMatch[2] || "";
        const replaceStart = caretPos - fieldPrefix.length;
        const replaceEnd = caretPos;

        // Resolve table name from alias or qualifier
        const resolvedTable = aliases[qualifier] || qualifier;
        const entry = findTableSchema(schemaCache, resolvedTable);

        const items = [];
        if (entry && entry.info && entry.info.columns) {
            for (let i = 0; i < entry.info.columns.length; i++) {
                const col = entry.info.columns[i];
                const lowerCol = col.name.toLowerCase();
                const pLower = fieldPrefix.toLowerCase();
                if (!fieldPrefix || lowerCol.includes(pLower)) {
                    const starts = !fieldPrefix || lowerCol.startsWith(pLower);
                    items.push({
                        id: `col_${entry.name}_${col.name}`,
                        name: col.name,
                        insertText: col.name,
                        category: "field",
                        categoryLabel: dotMatch[1],
                        dtype: col.type || "",
                        detail: entry.name,
                        matchParts: formatMatchParts(col.name, fieldPrefix),
                        score: starts ? (1400 - i) : (900 - i),
                    });
                }
            }
        }

        items.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));
        return {
            items: items.slice(0, 40),
            replaceStart,
            replaceEnd,
            prefix: fieldPrefix,
        };
    }

    // Normal word prefix match
    const wordMatch = /([a-zA-Z0-9_]+)$/.exec(textBefore);
    const prefix = wordMatch ? wordMatch[1] : "";
    const pLower = prefix.toLowerCase();

    // If prefix is empty, only trigger if we are in a field context with query tables or in a table clause
    if (!prefix && !isTableContext && !(isFieldContext && queryTables.length > 0)) {
        return { items: [], replaceStart: caretPos, replaceEnd: caretPos, prefix: "" };
    }

    const replaceStart = caretPos - prefix.length;
    const replaceEnd = caretPos;
    const items = [];

    // 1. Columns / Fields from tables present in the query (Highest Priority)
    const activeTables = queryTables.length ? queryTables : (isFieldContext ? [] : (knownTables || []).slice(0, 5));
    const seenColKeys = new Set();

    // Alias-prefixed fields (e.g. `th.trn_id` if alias `th` exists)
    if (isFieldContext && Object.keys(aliases).length > 0) {
        for (const [aliasName, targetTable] of Object.entries(aliases)) {
            const entry = findTableSchema(schemaCache, targetTable);
            if (entry && entry.info && entry.info.columns) {
                for (let i = 0; i < entry.info.columns.length; i++) {
                    const col = entry.info.columns[i];
                    const lowerCol = col.name.toLowerCase();
                    const qualifiedName = `${aliasName}.${col.name}`;
                    const qualifiedLower = qualifiedName.toLowerCase();
                    if (!prefix || lowerCol.includes(pLower) || qualifiedLower.includes(pLower) || aliasName.toLowerCase().startsWith(pLower)) {
                        const starts = !prefix || qualifiedLower.startsWith(pLower) || lowerCol.startsWith(pLower);
                        let score = starts ? 1500 : 1100;
                        score -= i;
                        const key = `alias_${qualifiedName}`;
                        if (!seenColKeys.has(key)) {
                            seenColKeys.add(key);
                            items.push({
                                id: `col_alias_${aliasName}_${col.name}`,
                                name: qualifiedName,
                                insertText: qualifiedName,
                                category: "field",
                                categoryLabel: aliasName,
                                dtype: col.type || "",
                                detail: targetTable,
                                matchParts: formatMatchParts(qualifiedName, prefix) || formatMatchParts(col.name, prefix),
                                score,
                            });
                        }
                    }
                }
            }
        }
    }

    // Bare fields from query tables
    for (const tName of activeTables) {
        const entry = findTableSchema(schemaCache, tName);
        if (entry && entry.info && entry.info.columns) {
            for (let i = 0; i < entry.info.columns.length; i++) {
                const col = entry.info.columns[i];
                const lowerCol = col.name.toLowerCase();
                if (!prefix || lowerCol.includes(pLower)) {
                    const starts = !prefix || lowerCol.startsWith(pLower);
                    let score = starts ? 1400 : 1000;
                    if (isFieldContext) score += 200;
                    score -= i; // preserve column order for ties

                    const key = `${entry.name}.${col.name}`;
                    if (!seenColKeys.has(key)) {
                        seenColKeys.add(key);
                        items.push({
                            id: `col_${entry.name}_${col.name}`,
                            name: col.name,
                            insertText: col.name,
                            category: "field",
                            categoryLabel: "field",
                            dtype: col.type || "",
                            detail: entry.name,
                            matchParts: formatMatchParts(col.name, prefix),
                            score,
                        });
                    }
                }
            }
        }
    }

    // 2. Table Aliases (e.g. `th.` if `FROM transaction_header th`)
    if (isFieldContext && Object.keys(aliases).length > 0) {
        for (const [aliasName, targetTable] of Object.entries(aliases)) {
            const aLower = aliasName.toLowerCase();
            if (!prefix || aLower.startsWith(pLower) || aLower.includes(pLower)) {
                const starts = !prefix || aLower.startsWith(pLower);
                items.push({
                    id: `alias_${aliasName}`,
                    name: `${aliasName}.`,
                    insertText: `${aliasName}.`,
                    category: "table",
                    categoryLabel: "alias",
                    detail: `Alias for ${targetTable}`,
                    matchParts: formatMatchParts(`${aliasName}.`, prefix),
                    score: starts ? 1350 : 950,
                });
            }
        }
    }

    // 3. Tables & Views
    const allTables = new Set([...(knownTables || []), ...Object.keys(schemaCache || {})]);
    const allViews = new Set(knownViews || []);

    // If queryTables exist and we are in field context, suppress or deprioritize tables so they don't pollute column completions
    const showAllTables = isTableContext || queryTables.length === 0 || (!isFieldContext && prefix.length >= 2);

    if (showAllTables && (prefix || isTableContext)) {
        for (const tName of allTables) {
            const lower = tName.toLowerCase();
            const isView = allViews.has(tName) || (schemaCache[tName] && schemaCache[tName].type === "view");
            if (!prefix || lower.includes(pLower)) {
                const starts = !prefix || lower.startsWith(pLower);
                let score = starts ? 500 : 200;
                if (isTableContext) {
                    score += 1000;
                }
                items.push({
                    id: `tbl_${tName}`,
                    name: tName,
                    insertText: tName + " ",
                    category: isView ? "view" : "table",
                    categoryLabel: isView ? "view" : "table",
                    detail: isView ? "View" : "Table",
                    matchParts: formatMatchParts(tName, prefix),
                    score,
                });
            }
        }
    }

    // 4. Other columns from all tables across database (only when no query tables are specified and prefix >= 2)
    if (!activeTables.length && prefix.length >= 2) {
        for (const [tName, info] of Object.entries(schemaCache || {})) {
            if (info && info.columns) {
                for (const col of info.columns) {
                    const lowerCol = col.name.toLowerCase();
                    if (lowerCol.includes(pLower)) {
                        const starts = lowerCol.startsWith(pLower);
                        const key = `${tName}.${col.name}`;
                        if (!seenColKeys.has(key)) {
                            seenColKeys.add(key);
                            items.push({
                                id: `col_${tName}_${col.name}`,
                                name: col.name,
                                insertText: col.name,
                                category: "field",
                                categoryLabel: "field",
                                dtype: col.type || "",
                                detail: tName,
                                matchParts: formatMatchParts(col.name, prefix),
                                score: starts ? 400 : 150,
                            });
                        }
                    }
                }
            }
        }
    }

    // 5. SQL Functions (e.g. COUNT(), SUM(), AVG(), COALESCE(), etc.)
    if (!isTableContext) {
        for (const fn of SQL_AUTOCOMPLETE_FUNCTIONS) {
            const lower = fn.name.toLowerCase();
            if (!prefix || lower.includes(pLower)) {
                const starts = !prefix || lower.startsWith(pLower);
                let score = starts ? 700 : 350;
                if (isFieldContext) score += 50;
                items.push({
                    id: `fn_${fn.name}`,
                    name: fn.name,
                    insertText: fn.insertText,
                    cursorOffset: fn.cursorOffset,
                    category: "function",
                    categoryLabel: "func",
                    detail: fn.detail,
                    matchParts: formatMatchParts(fn.name, prefix),
                    score,
                });
            }
        }
    }

    // 6. SQL Keywords
    if (prefix) {
        for (const kw of SQL_AUTOCOMPLETE_KEYWORDS) {
            const lower = kw.toLowerCase();
            if (lower.includes(pLower)) {
                const starts = lower.startsWith(pLower);
                let score = starts ? 600 : 250;
                if (isTableContext && (kw === "JOIN" || kw === "ON" || kw === "AS" || kw === "WHERE")) {
                    score += 600;
                }
                items.push({
                    id: `kw_${kw}`,
                    name: kw,
                    insertText: kw + " ",
                    category: "keyword",
                    categoryLabel: "keyword",
                    detail: "SQL Keyword",
                    matchParts: formatMatchParts(kw, prefix),
                    score,
                });
            }
        }
    }

    items.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));

    return {
        items: items.slice(0, 40),
        replaceStart,
        replaceEnd,
        prefix,
    };
}


export class SqlMsAnalyser extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.taRef = useRef("queryTextarea");
        this.preRef = useRef("queryHighlight");
        this.gutterRef = useRef("queryGutter");
        this.rootRef = useRef("rootEl");
        this.sidebarRef = useRef("sidebarEl");
        this.editorRef = useRef("editorEl");
        this.acListRef = useRef("acListEl");
        this.autocompleteRef = useRef("autocompleteEl");
        this.schemaCache = {};

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
            fieldFilter: "",
            fieldSel: {},
            // Header columns picked in the Fields / Mapping grids, by their
            // index in FIELD_COLUMNS / MAPPING_COLUMNS. Copy narrows to
            // these; empty means "every column", as it does for results.
            fieldCols: [],
            mapping: null,
            mappingCols: [],
            query: "",
            display: "",
            folds: {},
            execQuery: "",
            execRange: null,
            queryResult: null,
            qtabs: [],
            activeQtabId: null,
            loading: false,
            currentExecutionId: null,
            cancelling: false,
            exporting: false,
            favorites: [],
            showFavorites: true,
            showTables: true,
            showViews: true,
            checked: {},
            tabMenuOpen: false,
            selectedCols: [],
            aggFunc: "",
            autocomplete: {
                visible: false,
                items: [],
                selectedIndex: -1,
                top: 0,
                left: 0,
                replaceStart: 0,
                replaceEnd: 0,
                prefix: "",
            },
        });

        // Pick up where the last visit left off. A still-fresh snapshot —
        // parked by the previous Analyser on its way out, or by a
        // history-list click — restores the whole workspace; a query handed
        // in by a record button (action_open_in_analyser) joins it as one
        // more tab rather than replacing it. With neither, start on a single
        // blank tab.
        const act = this.props.action || {};
        const incoming = (act.params && act.params.query) ||
            (act.context && act.context.default_query);
        const pending = analyserRegistry.pending;
        analyserRegistry.pending = null;
        const usePending = pending && pending.qtabs && pending.qtabs.length &&
            (Date.now() - pending.ts) < PENDING_TTL_MS;
        if (usePending) {
            this._restoreSession(pending);
        }
        if (incoming || !usePending) {
            this._snapshotActiveQtab();
            const t = this._makeQtab(incoming || "");
            this.state.qtabs.push(t);
            this._loadQtab(t);
            if (incoming) {
                this.state.activeTab = "query";
            }
        }

        onMounted(() => this.loadObjects());
        onMounted(() => this.loadSchemaForAutocomplete());
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

        // Keyboard shortcuts (see _onShortcut). Bound on the document because
        // the result grid itself is not focusable, so there is no element the
        // key event would otherwise reach.
        this._onKeydown = (ev) => this._onShortcut(ev);
        onMounted(() => document.addEventListener("keydown", this._onKeydown));
        onWillUnmount(() => document.removeEventListener("keydown", this._onKeydown));

        // Leaving for another menu destroys this component, so park the
        // workspace on the way out; the next Analyser to mount picks it up
        // above. This covers every exit, the "Query history" button included
        // (which is why openHistory no longer snapshots for itself).
        onWillUnmount(() => this._snapshotSession());
    }

    // -- workspace snapshot / restore ----------------------------------
    _snapshotSession() {
        this._snapshotActiveQtab();
        const snap = {
            qtabs: this.state.qtabs,
            activeQtabId: this.state.activeQtabId,
            ts: Date.now(),
        };
        for (const key of SESSION_KEYS) {
            snap[key] = this.state[key];
        }
        analyserRegistry.pending = snap;
    }
    _restoreSession(snap) {
        this.state.qtabs = snap.qtabs;
        const active = snap.qtabs.find((t) => t.id === snap.activeQtabId) ||
            snap.qtabs[snap.qtabs.length - 1];
        this._loadQtab(active);
        // After _loadQtab, which may point `selected` at a script tab's view:
        // the snapshot is the more recent truth about what was on screen.
        for (const key of SESSION_KEYS) {
            if (snap[key] !== undefined) {
                this.state[key] = snap[key];
            }
        }
    }

    // -- resizing the sidebar / editor ---------------------------------
    // Both used the browser's own `resize`, whose handle is a few pixels in
    // one corner — an easy thing to miss and a fiddly thing to hit. They are
    // dragged by a bar running the full length of the edge instead. Pointer
    // events (not mouse) so a trackpad, touchscreen or pen all work, and the
    // pointer is captured so the drag survives the cursor outrunning the bar.
    startResize(ev, what) {
        const target = what === "sidebar" ? this.sidebarRef.el : this.editorRef.el;
        if (!target) {
            return;
        }
        ev.preventDefault();
        const bar = ev.currentTarget;
        const rect = target.getBoundingClientRect();
        const horizontal = what === "sidebar";
        const onMove = (e) => {
            if (horizontal) {
                const width = Math.min(
                    Math.max(e.clientX - rect.left, RESIZE_MIN.sidebar),
                    window.innerWidth * 0.7
                );
                target.style.width = width + "px";
            } else {
                const height = Math.min(
                    Math.max(e.clientY - rect.top, RESIZE_MIN.editor),
                    Math.max(RESIZE_MIN.editor, window.innerHeight - rect.top - 80)
                );
                target.style.height = height + "px";
            }
        };
        const onUp = () => {
            bar.releasePointerCapture(ev.pointerId);
            bar.removeEventListener("pointermove", onMove);
            bar.removeEventListener("pointerup", onUp);
            bar.removeEventListener("pointercancel", onUp);
            bar.classList.remove("sqlms-resizer-active");
        };
        bar.setPointerCapture(ev.pointerId);
        bar.classList.add("sqlms-resizer-active");
        bar.addEventListener("pointermove", onMove);
        bar.addEventListener("pointerup", onUp);
        bar.addEventListener("pointercancel", onUp);
    }
    // Double-clicking the bar drops the inline size, so the panel falls back
    // to whatever the stylesheet says.
    resetResize(what) {
        const target = what === "sidebar" ? this.sidebarRef.el : this.editorRef.el;
        if (target) {
            target.style.removeProperty(what === "sidebar" ? "width" : "height");
        }
    }

    _fitHeight() {
        const el = this.rootRef.el;
        if (el) {
            const top = el.getBoundingClientRect().top;
            el.style.setProperty("height", (window.innerHeight - top) + "px", "important");
        }
    }

    // The editor is a single textarea with a highlight <pre> behind it and a
    // fold gutter in front. Both are re-created whenever the user leaves and
    // returns to the Query tab, so they are re-filled from state here. The
    // textarea's own value is only written when it actually differs (on a
    // plain keystroke it already matches), so this never fights the user's
    // typing or moves the caret.
    _syncEditor() {
        const ta = this.taRef.el;
        const text = this.state.display || "";
        if (ta && ta.value !== text) {
            ta.value = text;
        }
        if (this.preRef.el) {
            this.preRef.el.innerHTML = highlightSql(text, this.state.execRange) + "\n";
        }
        this._syncEditorScroll(ta ? ta.scrollTop : 0, ta ? ta.scrollLeft : 0);
    }
    _syncEditorScroll(top, left) {
        if (this.preRef.el) {
            this.preRef.el.scrollTop = top;
            this.preRef.el.scrollLeft = left;
        }
        if (this.gutterRef.el) {
            this.gutterRef.el.style.transform = "translateY(" + -top + "px)";
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
            this._openBuiltQuery(res.query);
        } finally {
            this.state.loading = false;
        }
    }

    openHistory() {
        // Park the workspace now rather than waiting for onWillUnmount: the
        // History list needs it in place before its own rows can be clicked,
        // and doAction may resolve either side of the unmount.
        this._snapshotSession();
        this.action.doAction("database_studio.action_sql_ms_query");
    }

    async loadObjects() {
        const res = await this.orm.call("database.studio.analyser", "get_objects", []);
        this.state.tables = res.tables;
        this.state.views = res.views;
        this.state.favorites = res.favorites || [];
        this.loadSchemaForAutocomplete();
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
    // While a view's script tab is the one in front, that view is shown too
    // (first) whatever else is picked, so its columns are always at hand next
    // to the script -- and ticking a table alongside it still works, which is
    // how the view's fields get compared with a table's.
    _fieldsTables() {
        const checked = Object.keys(this.state.checked);
        const tables = checked.length
            ? checked
            : (this.state.selected ? [this.state.selected] : []);
        const t = this.qtab;
        const view = t && t.viewName ? t.viewName : null;
        if (view && !tables.includes(view)) {
            return [view].concat(tables);
        }
        return tables;
    }
    async loadFields() {
        const tables = this._fieldsTables();
        if (!tables.length) {
            // Nothing ticked on the left: show what the current query returned
            // instead. A result assembled from CTEs, JSON or expressions
            // belongs to no table, so this is the only place its columns and
            // their types are visible at all.
            this.state.fieldGroups = this._resultFieldGroups();
            this._pruneFieldPicks();
            return;
        }
        this.state.loading = true;
        try {
            this.state.fieldGroups = await this.orm.call(
                "database.studio.analyser", "get_fields_multi", [tables]
            );
            if (this.state.fieldGroups) {
                for (const g of this.state.fieldGroups) {
                    if (g.table && g.fields) {
                        this.schemaCache[g.table] = {
                            type: (this.state.views || []).includes(g.table) ? "view" : "table",
                            columns: g.fields.map((f) => ({ name: f.name, type: f.type })),
                        };
                    }
                }
            }
            // Unticking a table on the left hides its fields; drop any picks
            // that went with it rather than letting them turn up invisibly in
            // the next built query.
            this._pruneFieldPicks();
        } finally {
            this.state.loading = false;
        }
    }
    // The active query tab's result, as a single field group. Empty until a
    // query has actually returned columns.
    _resultFieldGroups() {
        const res = this.state.queryResult;
        if (!res || !(res.columns || []).length) {
            return [];
        }
        const types = res.column_types || [];
        return [{
            table: RESULT_GROUP,
            derived: true,
            fields: res.columns.map((name, i) => ({
                name, type: types[i] || "", precision: "", nullable: "",
            })),
        }];
    }
    _pruneFieldPicks() {
        const shown = new Set(this.state.fieldGroups.map((g) => g.table));
        for (const key of Object.keys(this.state.fieldSel)) {
            if (!shown.has(this.state.fieldSel[key].table)) {
                delete this.state.fieldSel[key];
            }
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
    // The field list narrowed by the Fields tab's own search box, dropping
    // tables that have nothing matching. Everything downstream (the "all"
    // tick box, the counters) works off these, so searching and then ticking
    // "all" picks exactly what is on screen.
    get filteredFieldGroups() {
        const term = (this.state.fieldFilter || "").trim().toLowerCase();
        const groups = this.state.fieldGroups || [];
        if (!term) {
            return groups;
        }
        const out = [];
        for (const g of groups) {
            const fields = g.fields.filter((f) => f.name.toLowerCase().includes(term));
            if (fields.length) {
                out.push({ table: g.table, fields });
            }
        }
        return out;
    }
    get visibleFieldCount() {
        return this.filteredFieldGroups.reduce((n, g) => n + g.fields.length, 0);
    }
    clearFieldFilter() {
        this.state.fieldFilter = "";
    }
    clearFilter() {
        this.state.filter = "";
    }

    // -- field picking (Fields tab) ------------------------------------
    _fieldKey(table, name) {
        return table + "." + name;
    }
    fieldPick(table, name) {
        return this.state.fieldSel[this._fieldKey(table, name)] || null;
    }
    isFieldPicked(table, name) {
        return !!this.state.fieldSel[this._fieldKey(table, name)];
    }
    fieldOrderDir(table, name) {
        const pick = this.fieldPick(table, name);
        return pick ? pick.order : "";
    }
    isFieldGrouped(table, name) {
        const pick = this.fieldPick(table, name);
        return !!(pick && pick.group);
    }
    _pickField(table, field) {
        const key = this._fieldKey(table, field.name);
        if (!this.state.fieldSel[key]) {
            this.state.fieldSel[key] = {
                table,
                name: field.name,
                type: field.type,
                derived: table === RESULT_GROUP,
                group: false,
                order: "",
                orderSeq: 0,
            };
        }
        return this.state.fieldSel[key];
    }
    // Result columns cannot be joined or grouped the way table columns can —
    // there is no table to select them from — so Build query stays out.
    get hasDerivedPicks() {
        return this.pickedFields.some((f) => f.derived);
    }
    toggleFieldPick(table, field, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const key = this._fieldKey(table, field.name);
        if (this.state.fieldSel[key]) {
            delete this.state.fieldSel[key];
        } else {
            this._pickField(table, field);
        }
    }
    // Grouping/ordering a field implies selecting it — you cannot group by
    // something the query does not pick.
    toggleFieldGroupBy(table, field, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const pick = this._pickField(table, field);
        pick.group = !pick.group;
    }
    cycleFieldOrder(table, field, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const pick = this._pickField(table, field);
        if (pick.order === "") {
            pick.order = "asc";
            pick.orderSeq = ++SqlMsAnalyser._orderSeq;
        } else if (pick.order === "asc") {
            pick.order = "desc";
        } else {
            pick.order = "";
            pick.orderSeq = 0;
        }
    }
    allFieldsPicked(group) {
        return group.fields.length > 0 &&
            group.fields.every((f) => this.isFieldPicked(group.table, f.name));
    }
    toggleAllFields(group, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const pickAll = !this.allFieldsPicked(group);
        for (const f of group.fields) {
            const key = this._fieldKey(group.table, f.name);
            if (pickAll) {
                this._pickField(group.table, f);
            } else {
                delete this.state.fieldSel[key];
            }
        }
    }
    get pickedFields() {
        return Object.values(this.state.fieldSel);
    }
    get pickedFieldCount() {
        return this.pickedFields.length;
    }
    get groupedFieldCount() {
        return this.pickedFields.filter((f) => f.group).length;
    }
    get orderedFieldCount() {
        return this.pickedFields.filter((f) => f.order).length;
    }
    clearFieldPicks() {
        this.state.fieldSel = {};
    }
    // Turn the ticked text columns into a numeric column. The dialog does the
    // dry run and the ALTER; here we only report what came back and refresh
    // the field list so the new types show.
    openConvertType() {
        const picked = this.pickedFields;
        if (!picked.length) {
            return;
        }
        const derived = this.hasDerivedPicks;
        this.dialog.add(SqlMsConvertTypeDialog, {
            mode: derived ? "query" : "table",
            query: derived ? (this.state.execQuery || this.state.query || "") : "",
            items: picked.map((f) => ({ table: f.table, name: f.name })),
            onApply: (sql) => this._openBuiltQuery(sql),
            onDone: async (res) => {
                if (res.converted) {
                    this.notification.add(res.message, { type: "success" });
                }
                for (const r of (res.results || []).filter((r) => !r.ok)) {
                    this.notification.add(r.table + ": " + r.error,
                                          { type: "danger", sticky: true });
                }
                await this.loadFields();
            },
        });
    }
    // Builds a SELECT of exactly the ticked columns (joining their tables
    // when there is more than one) and drops it into the query editor.
    async buildFieldQuery() {
        const picked = this.pickedFields;
        if (!picked.length) {
            return;
        }
        const strip = (f) => ({ table: f.table, name: f.name });
        const orderBy = picked
            .filter((f) => f.order)
            .sort((a, b) => a.orderSeq - b.orderSeq)
            .map((f) => ({ table: f.table, name: f.name, dir: f.order }));
        this.state.loading = true;
        let res;
        try {
            res = await this.orm.call(
                "database.studio.analyser", "build_field_query",
                [picked.map(strip), picked.filter((f) => f.group).map(strip), orderBy]
            );
        } finally {
            this.state.loading = false;
        }
        if (res && res.query) {
            this._openBuiltQuery(res.query);
        }
    }
    // A generated query lands in a fresh tab whenever the current one already
    // holds something, so building never silently discards typed work.
    _openBuiltQuery(query) {
        this.state.activeTab = "query";
        if ((this.state.query || "").trim()) {
            this.addQtab();
        }
        this.setQuery(query);
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
            t.display = this.state.display;
            t.folds = this.state.folds;
            t.execQuery = this.state.execQuery;
            t.execRange = this.state.execRange;
            t.queryResult = this.state.queryResult;
            t.selectedCols = this.state.selectedCols;
            t.aggFunc = this.state.aggFunc;
        }
    }
    _loadQtab(t) {
        this.state.activeQtabId = t.id;
        this.state.query = t.query;
        // Tabs restored from an older snapshot (or from History) may predate
        // the folding editor and carry no display/folds of their own.
        this.state.display = t.display === undefined ? t.query : t.display;
        this.state.folds = t.folds || {};
        this.state.execQuery = t.execQuery;
        this.state.execRange = t.execRange || null;
        this.state.queryResult = t.queryResult;
        this.state.selectedCols = t.selectedCols || [];
        this.state.aggFunc = t.aggFunc || "";
        this._syncEditor();
        // A script tab is about one view, so fronting it points the rest of
        // the tool at that view too: it lights up in the list on the left and
        // the Fields tab lists its columns (see _fieldsTables).
        if (t.viewName) {
            this.state.selected = t.viewName;
            this.state.selectedType = "view";
            if (this.state.activeTab === "fields") {
                this.loadFields();
            }
        }
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
        // A view's definition is the database's text, not the user's: it can
        // be pulled from the view again whenever it is wanted, so closing it
        // has nothing to save.
        if (t.isScript) {
            this._doRemoveQtab(id);
            return;
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
    // -- closing several tabs at once ----------------------------------
    toggleTabMenu() {
        this.state.tabMenuOpen = !this.state.tabMenuOpen;
    }
    closeTabMenu() {
        this.state.tabMenuOpen = false;
    }
    // How many tabs each menu entry would close, both to label the entries
    // and to grey out the ones that would do nothing.
    get otherQtabCount() {
        return this.state.qtabs.filter((t) => t.id !== this.state.activeQtabId).length;
    }
    get leftQtabCount() {
        const i = this.state.qtabs.findIndex((t) => t.id === this.state.activeQtabId);
        return i === -1 ? 0 : i;
    }
    get rightQtabCount() {
        const i = this.state.qtabs.findIndex((t) => t.id === this.state.activeQtabId);
        return i === -1 ? 0 : this.state.qtabs.length - i - 1;
    }
    get savedQtabCount() {
        return this.state.qtabs.filter((t) => t.isSaved).length;
    }
    closeOtherQtabs() {
        const keep = this.state.activeQtabId;
        return this._closeQtabs(this.state.qtabs.filter((t) => t.id !== keep));
    }
    closeQtabsToLeft() {
        const i = this.state.qtabs.findIndex((t) => t.id === this.state.activeQtabId);
        return i === -1 ? null : this._closeQtabs(this.state.qtabs.slice(0, i));
    }
    closeQtabsToRight() {
        const i = this.state.qtabs.findIndex((t) => t.id === this.state.activeQtabId);
        return i === -1 ? null : this._closeQtabs(this.state.qtabs.slice(i + 1));
    }
    // Every tab that is already in History — closing these can never lose
    // anything, so the whole set goes without a single prompt.
    closeSavedQtabs() {
        return this._closeQtabs(this.state.qtabs.filter((t) => t.isSaved));
    }
    closeAllQtabs() {
        return this._closeQtabs(this.state.qtabs.slice());
    }
    // Closes `targets` in turn, asking about each one that still holds
    // unsaved text exactly as closing it on its own would. The prompts are
    // sequential — the next tab is only considered once this one has been
    // answered — and dismissing a prompt without choosing (Escape, or its X)
    // stops the whole run rather than ploughing on through the rest.
    async _closeQtabs(targets) {
        this.closeTabMenu();
        this._snapshotActiveQtab();
        for (const t of targets) {
            if (!this.state.qtabs.some((x) => x.id === t.id)) {
                continue;
            }
            // Bring the tab being asked about to the front first, so the
            // dialog is never asking about a query the user cannot see.
            if (t.id !== this.state.activeQtabId) {
                this._snapshotActiveQtab();
                this._loadQtab(t);
            }
            if ((await this._confirmCloseQtab(t)) === "cancel") {
                return;
            }
            this._doRemoveQtab(t.id);
        }
    }
    // Resolves "close" once this tab may go — immediately for a saved or
    // empty one, otherwise after the user picks Save or Discard — and
    // "cancel" if they dismissed the prompt instead of answering it.
    _confirmCloseQtab(t) {
        const query = (t.query || "").trim();
        if (t.isSaved || t.isScript || !query) {
            return Promise.resolve("close");
        }
        return new Promise((resolve) => {
            // The dialog closes itself right after handing us the answer, so
            // onClose fires either way; this tells a real answer apart from a
            // dismissal. Both handlers set it before their first await, i.e.
            // while still running synchronously inside the click.
            let answered = false;
            this.dialog.add(
                SqlMsCloseTabDialog,
                {
                    tabName: t.name,
                    defaultName: t.fullName || query.replace(/\s+/g, " ").slice(0, 60),
                    onSave: async (name) => {
                        answered = true;
                        await this._persistSave(t, query, name);
                        this.notification.add("Query saved ★", { type: "success" });
                        resolve("close");
                    },
                    onDiscard: () => {
                        answered = true;
                        resolve("close");
                    },
                },
                {
                    onClose: () => {
                        if (!answered) {
                            resolve("cancel");
                        }
                    },
                }
            );
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
    // The statements found in the editor text, as an outline for the fold
    // gutter. Nothing here splits the text apart: the whole query stays in
    // one textarea, so any part of it (or all of it) can be selected and run.
    get sections() {
        // Rendering asks for this several times per patch (and a patch happens
        // on every keystroke), so the scan is memoised on the text it scanned.
        const text = this.state.display || "";
        const folds = this.state.folds || {};
        const stamp = Object.keys(folds).join(",");
        const cached = this._sectionsCache;
        if (cached && cached.text === text && cached.stamp === stamp) {
            return cached.sections;
        }
        const sections = this._computeSections(text, folds);
        this._sectionsCache = { text, stamp, sections };
        return sections;
    }
    _computeSections(text, folds) {
        // Every statement is listed, foldable or not: whether an icon is
        // actually drawn is `foldable` below. Skipping one-line texts here
        // used to strand a folded single statement — folding collapsed it to
        // the one-line placeholder, which then had no icon to unfold it with.
        const ranges = findStatementRanges(text);
        // Line of each statement's first character, walked in one pass.
        let line = 0;
        let pos = 0;
        const out = [];
        for (const r of ranges) {
            while (pos < r.start) {
                if (text[pos] === "\n") {
                    line += 1;
                }
                pos += 1;
            }
            const body = text.slice(r.start, r.end);
            const marker = /^\/\* \u25b8 fold#(\d+):/.exec(body);
            const foldId = marker && folds[marker[1]] ? marker[1] : null;
            const lineCount = foldId
                ? folds[foldId].lines
                : (body.match(/\n/g) || []).length + 1;
            out.push({
                key: r.start + ":" + (foldId || "0"),
                index: out.length,
                start: r.start,
                end: r.end,
                line,
                lineCount,
                foldId,
                collapsed: !!foldId,
                top: EDITOR_PAD_TOP + line * EDITOR_LINE_H,
                foldable: !!foldId || lineCount > 1,
            });
        }
        return out;
    }
    get foldableCount() {
        return this.sections.filter((sc) => sc.foldable).length;
    }
    // Writes new editor text, keeping the real query (folds expanded) in
    // step and forgetting any fold whose placeholder the user has deleted —
    // deleting the placeholder line deletes that statement, as it looks like
    // it should.
    _setDisplay(text) {
        // Any edit (or a fold) moves the text under the executed range, so
        // the "this is what ran" marker is dropped rather than left pointing
        // at the wrong characters.
        this.state.execRange = null;
        this.state.display = text;
        this.state.query = expandFolds(text, this.state.folds);
        for (const id of Object.keys(this.state.folds)) {
            if (!foldRe(id).test(text)) {
                delete this.state.folds[id];
            }
        }
        this._syncEditor();
    }
    toggleSection(index) {
        const sec = this.sections[index];
        if (!sec) {
            return;
        }
        if (sec.foldId) {
            this._unfold(sec.foldId);
        } else {
            this._fold(sec);
        }
    }
    _fold(sec) {
        const text = this.state.display || "";
        const body = text.slice(sec.start, sec.end);
        if (!body.trim()) {
            return;
        }
        const id = ++_foldIdSeq;
        // "*/" inside the preview would close the placeholder comment early.
        const preview = body
            .trim()
            .replace(/\s+/g, " ")
            .replace(/\*\//g, "*\u2044")
            .slice(0, 60);
        this.state.folds[id] = { text: body, preview, lines: sec.lineCount };
        this._setDisplay(
            text.slice(0, sec.start) +
            foldPlaceholder(id, preview, sec.lineCount) +
            text.slice(sec.end)
        );
    }
    _unfold(id) {
        const f = this.state.folds[id];
        if (!f) {
            return;
        }
        this._setDisplay((this.state.display || "").replace(foldRe(id), () => f.text));
    }
    foldAll() {
        // Fold from the bottom up so folding one statement doesn't shift the
        // character ranges of the ones still to be folded.
        for (const sec of this.sections.slice().reverse()) {
            if (sec.foldable && !sec.foldId) {
                this._fold(sec);
            }
        }
    }
    unfoldAll() {
        for (const id of Object.keys(this.state.folds)) {
            this._unfold(id);
        }
    }
    setQuery(text) {
        this.state.execRange = null;
        this.state.folds = {};
        this.state.query = text;
        this.state.display = text;
        this._syncEditor();
    }
    // Fired on every keystroke: record the new text (and the query it stands
    // for) without ever rewriting the textarea, so the caret stays put.
    onEditorInput(ev) {
        this._setDisplay(ev.target.value);
        this.updateAutocomplete(ev.target);
    }
    // Handle keyboard navigation for autocomplete and Tab indenting
    onEditorKeyDown(ev) {
        const ac = this.state.autocomplete;
        if (ac && ac.visible && ac.items.length) {
            if (ev.key === "ArrowDown") {
                ev.preventDefault();
                this.navigateAutocomplete(1);
                return;
            }
            if (ev.key === "ArrowUp") {
                ev.preventDefault();
                this.navigateAutocomplete(-1);
                return;
            }
            if (ev.key === "Enter") {
                if (ac.selectedIndex >= 0 && ac.items[ac.selectedIndex]) {
                    ev.preventDefault();
                    this.selectAutocompleteItem();
                    return;
                } else {
                    // No suggestion was focused/selected by the user: dismiss popup and allow standard Enter (newline)
                    this.closeAutocomplete();
                    return;
                }
            }
            if (ev.key === "Tab") {
                if (ac.selectedIndex >= 0 && ac.items[ac.selectedIndex]) {
                    ev.preventDefault();
                    this.selectAutocompleteItem();
                    return;
                }
                // If not explicitly focused, close autocomplete and allow Tab indent
                this.closeAutocomplete();
            }
            if (ev.key === "Escape") {
                ev.preventDefault();
                this.closeAutocomplete();
                return;
            }
        }

        if (ev.key !== "Tab") {
            return;
        }
        ev.preventDefault();
        const ta = ev.target;
        const start = ta.selectionStart;
        const end = ta.selectionEnd;
        const val = ta.value;
        const isMultiLine = val.substring(start, end).includes("\n");

        if (!ev.shiftKey && !isMultiLine) {
            // Single cursor or single line selection: insert 4 spaces (or replace selection)
            let inserted = false;
            try {
                inserted = document.execCommand("insertText", false, INDENT_STR);
            } catch (e) {
                inserted = false;
            }
            if (!inserted) {
                const before = val.substring(0, start);
                const after = val.substring(end);
                ta.value = before + INDENT_STR + after;
                ta.selectionStart = ta.selectionEnd = start + INDENT_STR.length;
                this._setDisplay(ta.value);
            }
            return;
        }

        // Multi-line block or Shift+Tab: indent or unindent whole lines
        const lineStart = val.lastIndexOf("\n", start - 1) + 1;
        let lineEnd = val.indexOf("\n", end);
        if (lineEnd === -1) {
            lineEnd = val.length;
        }

        const lines = val.substring(lineStart, lineEnd).split("\n");

        if (ev.shiftKey) {
            // Shift+Tab: Unindent lines
            let firstLineRemoved = 0;
            let totalRemoved = 0;
            const modified = lines.map((line, idx) => {
                let removeCount = 0;
                if (line.startsWith("\t")) {
                    removeCount = 1;
                } else {
                    while (removeCount < INDENT_STR.length && line[removeCount] === " ") {
                        removeCount++;
                    }
                }
                if (idx === 0) {
                    firstLineRemoved = removeCount;
                }
                totalRemoved += removeCount;
                return line.substring(removeCount);
            });

            const newBlock = modified.join("\n");
            ta.value = val.substring(0, lineStart) + newBlock + val.substring(lineEnd);
            ta.selectionStart = Math.max(lineStart, start - firstLineRemoved);
            ta.selectionEnd = Math.max(ta.selectionStart, end - totalRemoved);
            this._setDisplay(ta.value);
        } else {
            // Tab with multi-line selection: Indent lines
            const modified = lines.map((line) => INDENT_STR + line);
            const newBlock = modified.join("\n");
            ta.value = val.substring(0, lineStart) + newBlock + val.substring(lineEnd);
            ta.selectionStart = start + INDENT_STR.length;
            ta.selectionEnd = end + (INDENT_STR.length * lines.length);
            this._setDisplay(ta.value);
        }
    }
    // The band marking what the last Execute ran. It goes when the user
    // asks for it to go (the toolbar button) and when they put the caret
    // back in the editor, which is the point at which it stops describing
    // anything they are looking at.
    clearExecHighlight() {
        if (this.state.execRange) {
            this.state.execRange = null;
            this._syncEditor();
        }
    }
    onEditorScroll(ev) {
        this._syncEditorScroll(ev.target.scrollTop, ev.target.scrollLeft);
        if (this.state.autocomplete.visible) {
            this.closeAutocomplete();
        }
    }
    onEditorBlur() {
        setTimeout(() => {
            if (this.state && this.state.autocomplete) {
                this.closeAutocomplete();
            }
        }, 200);
    }
    async loadSchemaForAutocomplete() {
        try {
            const schema = await this.orm.call("database.studio.analyser", "get_schema_for_autocomplete", []);
            if (schema && typeof schema === "object") {
                this.schemaCache = Object.assign(this.schemaCache || {}, schema);
            }
        } catch (e) {
            // Non-blocking fallback
        }
    }
    async _fetchMissingTableSchema(tableNames) {
        if (!tableNames || !tableNames.length || this._fetchingMissingTables) return;
        this._fetchingMissingTables = true;
        try {
            const groups = await this.orm.call("database.studio.analyser", "get_fields_multi", [tableNames]);
            if (groups && groups.length) {
                if (!this.schemaCache) this.schemaCache = {};
                for (const g of groups) {
                    if (g.table && g.fields) {
                        this.schemaCache[g.table] = {
                            type: (this.state.views || []).includes(g.table) ? "view" : "table",
                            columns: g.fields.map((f) => ({ name: f.name, type: f.type })),
                        };
                    }
                }
                const ta = this.taRef.el;
                if (ta && document.activeElement === ta) {
                    this.updateAutocomplete(ta);
                }
            }
        } catch (e) {
            // Non-blocking fallback
        } finally {
            this._fetchingMissingTables = false;
        }
    }
    updateAutocomplete(ta) {
        if (!ta) return;
        const caretPos = ta.selectionStart;
        const fullText = ta.value;

        // Check if query has tables not yet loaded in schemaCache
        const { tables: queryTables } = extractTablesAndAliases(fullText);
        if (queryTables && queryTables.length) {
            const missing = queryTables.filter((t) => !findTableSchema(this.schemaCache, t));
            if (missing.length && !this._fetchingMissingTables) {
                this._fetchMissingTableSchema(missing);
            }
        }

        const { items, replaceStart, replaceEnd, prefix } = getAutocompleteSuggestions(
            fullText,
            caretPos,
            this.schemaCache || {},
            this.state.tables || [],
            this.state.views || []
        );

        if (!items.length) {
            this.closeAutocomplete();
            return;
        }

        const coords = getCaretCoordinates(ta, caretPos);
        const editorEl = this.editorRef.el;
        const editorRect = editorEl ? editorEl.getBoundingClientRect() : { width: 600, height: 300 };

        let top = coords.top - ta.scrollTop + coords.lineHeight + 6;
        let left = coords.left - ta.scrollLeft;

        left = Math.max(32, Math.min(left, (editorRect.width || 600) - 340));

        const popupHeight = Math.min(260, items.length * 32 + 60);
        if (top + popupHeight > (editorRect.height || 300) && coords.top - ta.scrollTop > popupHeight) {
            top = Math.max(10, coords.top - ta.scrollTop - popupHeight - 4);
        } else {
            top = Math.max(10, top);
        }

        this.state.autocomplete = {
            visible: true,
            items,
            selectedIndex: -1,
            top,
            left,
            replaceStart,
            replaceEnd,
            prefix,
        };
    }
    navigateAutocomplete(delta) {
        const ac = this.state.autocomplete;
        if (!ac.visible || !ac.items.length) return;
        const count = ac.items.length;
        let nextIndex;
        if (ac.selectedIndex < 0) {
            nextIndex = delta > 0 ? 0 : count - 1;
        } else {
            nextIndex = (ac.selectedIndex + delta) % count;
            if (nextIndex < 0) nextIndex += count;
        }
        ac.selectedIndex = nextIndex;

        const listEl = this.acListRef.el;
        if (listEl && listEl.children[nextIndex]) {
            listEl.children[nextIndex].scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
    }
    selectAutocompleteItem(item) {
        const ta = this.taRef.el;
        if (!ta) return;
        const ac = this.state.autocomplete;
        const chosen = item || (ac.selectedIndex >= 0 && ac.items && ac.items[ac.selectedIndex]);
        if (!chosen) {
            this.closeAutocomplete();
            return;
        }

        const val = ta.value;
        const start = ac.replaceStart;
        const end = ac.replaceEnd;
        const before = val.substring(0, start);
        const after = val.substring(end);
        const insertText = chosen.insertText;

        ta.value = before + insertText + after;

        let newCursorPos = start + insertText.length;
        if (chosen.cursorOffset != null) {
            newCursorPos = start + chosen.cursorOffset;
        }

        ta.selectionStart = newCursorPos;
        ta.selectionEnd = newCursorPos;
        this._setDisplay(ta.value);

        this.closeAutocomplete();
        ta.focus();
    }
    closeAutocomplete() {
        if (this.state.autocomplete) {
            this.state.autocomplete.visible = false;
            this.state.autocomplete.items = [];
            this.state.autocomplete.selectedIndex = -1;
        }
    }
    onAutocompleteHover(index) {
        if (this.state.autocomplete) {
            this.state.autocomplete.selectedIndex = index;
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

    // -- view scripts --------------------------------------------------
    // The SELECT behind a view, fetched from the catalog and dropped into a
    // query tab of its own, where it can be read, folded, edited and run like
    // any other query. Asking a second time refreshes the tab already showing
    // that view instead of stacking a duplicate next to it.
    async showViewScript(name, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.loading = true;
        let info;
        try {
            info = await this.orm.call(
                "database.studio.analyser", "get_view_script", [name]
            );
        } finally {
            this.state.loading = false;
        }
        this._snapshotActiveQtab();
        let tab = this.state.qtabs.find((t) => t.viewName === name);
        if (tab) {
            tab.query = info.script;
            tab.display = info.script;
            tab.folds = {};
            tab.execRange = null;
        } else {
            tab = makeQtab(info.script, { name: name, viewName: name });
            this.state.qtabs.push(tab);
        }
        this.state.activeTab = "query";
        this._loadQtab(tab);
    }

    _activeQuery() {
        // Run only the highlighted selection when the user has one, like a
        // real query analyser; otherwise run the whole editor content. A
        // textarea keeps its selectionStart/End after it is blurred (e.g. by
        // clicking the Execute button), so this works even though the button
        // click took the focus away. Folded statements caught in the
        // selection are restored to their real text before running.
        const ta = this.taRef.el;
        if (ta && ta.selectionEnd > ta.selectionStart) {
            const sel = ta.value.substring(ta.selectionStart, ta.selectionEnd).trim();
            if (sel) {
                return {
                    query: expandFolds(sel, this.state.folds).trim(),
                    range: { start: ta.selectionStart, end: ta.selectionEnd },
                };
            }
        }
        return { query: this.state.query, range: null };
    }

    // `fresh` distinguishes a real Execute click (re-capture the editor's
    // selection/text as the query to run) from a pager click (First/Previous/
    // Next/Last must keep paging through the already-executed query, even
    // though First also requests page 1).
    async runQuery(page = 1, fresh = false) {
        if (fresh) {
            const active = this._activeQuery();
            this.state.execQuery = active.query;
            this.state.execRange = active.range;
            this._syncEditor();
            // A new run may have a different column set; don't carry a
            // column selection over from whatever was run before.
            this.state.selectedCols = [];
        }
        const query = this.state.execQuery || this.state.query;
        const execQuery = this.state.execQuery;
        const execRange = this.state.execRange;
        // Remember which tab this run belongs to: if the user switches query
        // tabs before the RPC resolves, the result must land on that tab
        // instead of clobbering whatever tab is active by then.
        const qtabId = this.state.activeQtabId;
        const executionId = "exec_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9);
        this.state.currentExecutionId = executionId;
        this.state.loading = true;
        this.state.cancelling = false;
        let result;
        try {
            result = await this.orm.call(
                "database.studio.analyser", "run_query", [query, page, 100]
            );
        } catch (err) {
            if (this.state.cancelling) {
                this.notification.add("SQL execution was cancelled.", { type: "info" });
                return;
            }
            const errMsg =
                (err && err.data && err.data.message) ||
                (err && err.message) ||
                String(err || "Query execution failed");
            result = {
                columns: [],
                column_types: [],
                rows: [],
                total: 0,
                page: 1,
                pages: 1,
                limit: 100,
                error: errMsg,
                message: errMsg,
                aggregates: [],
            };
        } finally {
            this.state.loading = false;
            this.state.cancelling = false;
            this.state.currentExecutionId = null;
        }
        if (result && result.cancelled) {
            this.notification.add("SQL execution was cancelled.", { type: "info" });
            if (qtabId === this.state.activeQtabId) {
                this.state.queryResult = result;
            }
            return;
        }
        if (result && result.error) {
            this.notification.add(result.error, { type: "danger" });
        }
        if (qtabId === this.state.activeQtabId) {
            this.state.queryResult = result;
        } else {
            const t = this.state.qtabs.find((x) => x.id === qtabId);
            if (t) {
                t.execQuery = execQuery;
                t.execRange = execRange;
                t.queryResult = result;
            }
        }
        // A successful Execute (not a pager click and not an error) logs to History under the
        // "On the fly" tab, same as the old always-log behavior — but never
        // lets logging failures surface as if the query itself had failed.
        if (fresh && query && query.trim() && !(result && result.error)) {
            this.orm.call("database.studio.query", "log_query_run", [query]).catch(() => {});
        }
    }

    async cancelQuery() {
        if (!this.state.loading || !this.state.currentExecutionId) {
            return;
        }
        this.state.cancelling = true;
        try {
            const res = await this.orm.call(
                "database.studio.analyser", "cancel_query", [this.state.currentExecutionId]
            );
            if (res && res.message) {
                this.notification.add(res.message, {
                    type: res.success ? "info" : "warning",
                });
            }
        } catch (err) {
            this.notification.add(err.message || "Failed to cancel query execution", {
                type: "warning",
            });
        }
    }

    // -- keyboard shortcuts ---------------------------------------------
    // Alt+C copies the selected column(s) from anywhere in the analyser, and
    // plain Ctrl/Cmd+C does the same while columns are picked and nothing
    // else is highlighted — so a column can be selected and copied without
    // reaching for the mouse again. (Ctrl+Shift+C is deliberately not used:
    // browsers keep that one for their own devtools.)
    _onShortcut(ev) {
        if (ev.defaultPrevented || !this.rootRef.el || !this.rootRef.el.isConnected) {
            return;
        }
        const res = this.state.queryResult;
        if (!res || !res.columns.length) {
            return;
        }
        // ev.key is unreliable under Alt (Option+C types "ç" on a Mac), so
        // the physical key is what's matched.
        if (ev.code !== "KeyC" && (ev.key || "").toLowerCase() !== "c") {
            return;
        }
        // Never take a key away from the query editor or any other field:
        // there Alt+C/Ctrl+C still mean whatever they normally mean.
        const target = ev.target || {};
        const tag = (target.tagName || "").toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select" ||
                target.isContentEditable) {
            return;
        }
        if (ev.altKey && !ev.ctrlKey && !ev.metaKey) {
            ev.preventDefault();
            this.copyResults();
            return;
        }
        if ((ev.ctrlKey || ev.metaKey) && !ev.altKey && !ev.shiftKey) {
            const selection = window.getSelection && window.getSelection().toString();
            if (!selection && this.state.selectedCols.length) {
                ev.preventDefault();
                this.copyResults();
            }
        }
    }

    // -- result aggregates ----------------------------------------------
    // Sum/count/average (plus min/max) come back with the result, computed
    // server-side over *every* row the query returned — not just the page on
    // screen — so the totals row means what it says on a paginated result.
    get aggLabels() {
        return {
            count: "Count",
            sum: "Sum",
            avg: "Average",
            min: "Min",
            max: "Max",
        };
    }
    get aggLabel() {
        return this.aggLabels[this.state.aggFunc] || "";
    }
    setAggFunc(func) {
        this.state.aggFunc = func;
    }
    // The aggregate shown under one column: only for the selected column(s)
    // when any are picked (that is the point of picking them), for every
    // column that has one otherwise. Blank where the function doesn't apply,
    // e.g. the sum of a text column.
    aggValue(res, index) {
        if (!this.state.aggFunc) {
            return "";
        }
        if (this.state.selectedCols.length && !this.state.selectedCols.includes(index)) {
            return "";
        }
        const agg = (res.aggregates || [])[index];
        if (!agg) {
            return "";
        }
        const value = agg[this.state.aggFunc];
        return value === undefined || value === null ? "" : String(value);
    }

    // -- copy helpers --------------------------------------------------
    async _copy(text, label) {
        const ok = await copyToClipboard(text);
        this.notification.add(
            ok ? label + " copied to clipboard" : "Could not copy to clipboard",
            { type: ok ? "success" : "danger" }
        );
    }
    // -- Fields / Mapping column selection ------------------------------
    // The same gesture the result grid has: click a header to add that
    // column to the selection, click it again to drop it, and Copy then puts
    // just those columns on the clipboard. With nothing picked, Copy writes
    // every column — exactly what it did before.
    _toggleCol(list, index) {
        const i = list.indexOf(index);
        if (i === -1) {
            list.push(index);
        } else {
            list.splice(i, 1);
        }
    }
    _pickedCols(list, defs) {
        return list.length
            ? list.slice().sort((a, b) => a - b)
            : defs.map((c, i) => i);
    }
    // Tab-separated so a paste lands in one spreadsheet column per column.
    _copyRows(cols, defs, rows, label) {
        const lines = [cols.map((i) => defs[i].label).join("\t")];
        for (const row of rows) {
            lines.push(cols.map((i) => {
                const v = row[defs[i].key];
                return v === null || v === undefined ? "" : v;
            }).join("\t"));
        }
        this._copy(lines.join("\n"), label);
    }
    toggleFieldColumn(index, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this._toggleCol(this.state.fieldCols, index);
    }
    isFieldColSelected(index) {
        return this.state.fieldCols.includes(index);
    }
    clearFieldColumns() {
        this.state.fieldCols = [];
    }
    toggleMappingColumn(index, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this._toggleCol(this.state.mappingCols, index);
    }
    isMappingColSelected(index) {
        return this.state.mappingCols.includes(index);
    }
    clearMappingColumns() {
        this.state.mappingCols = [];
    }
    copyMapping() {
        const cols = this._pickedCols(this.state.mappingCols, MAPPING_COLUMNS);
        const rows = (this.state.mapping && this.state.mapping.rows) || [];
        this._copyRows(cols, MAPPING_COLUMNS, rows, "Mapping");
    }
    copyFields() {
        const cols = this._pickedCols(this.state.fieldCols, FIELD_COLUMNS);
        const rows = [];
        for (const g of this.state.fieldGroups || []) {
            for (const f of g.fields) {
                rows.push({
                    table: g.table,
                    name: f.name,
                    type: f.type,
                    precision: f.precision,
                    nullable: f.nullable,
                });
            }
        }
        this._copyRows(cols, FIELD_COLUMNS, rows, "Fields");
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
// Bumped each time a field is switched into ORDER BY, so the ORDER BY clause
// follows the order the user actually picked them in.
SqlMsAnalyser._orderSeq = 0;

registry.category("actions").add("database_studio.analyser", SqlMsAnalyser);
