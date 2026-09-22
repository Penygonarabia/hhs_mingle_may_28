# Running a committed .sql file through Odoo's cursor.
#
# The files in ../sql are written for psql, and three things in them do not
# survive being handed to psycopg2 unchanged. This module deals with all three
# and nothing else -- it takes no SQL from a request, only a filename the
# controller already recognised.
#
#   1. psql META-COMMANDS. `\echo` and friends are the client's, not the
#      server's, and reach the server as a syntax error. Stripped, with their
#      text kept as output so a script's own narration still appears.
#
#   2. TRANSACTION CONTROL. A `BEGIN` inside Odoo's already-open transaction
#      warns and does nothing; a `COMMIT` would commit ODOO's transaction
#      mid-request, ending it early and taking whatever else the request had
#      done with it. Both are dropped and the transaction is left to Odoo,
#      which commits a successful JSON request anyway. The scripts stay
#      all-or-nothing either way.
#
#   3. STATEMENT SPLITTING. Splitting on ';' breaks a `DO $$ ... $$;` block in
#      half, and ac_scope_data_fixes_portable.sql is two such blocks. The
#      splitter below tracks dollar quoting, ordinary quoting and both comment
#      forms, so a semicolon inside any of them is not a boundary.

import re

# A dollar-quote opener: $$ or $tag$ where tag is an identifier.
_DOLLAR_OPEN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")

# Statements that manage the transaction. Odoo owns it; see note 2 above.
_TXN = re.compile(r"^\s*(BEGIN|COMMIT|ROLLBACK|START\s+TRANSACTION|END)\s*;?\s*$",
                  re.IGNORECASE)


def strip_meta(sql):
    """Drop psql meta-command lines, returning (sql, narration).

    A meta line starts with a backslash at the beginning of a line. `\\echo
    'text'` carries the script's own commentary, which is worth showing, so its
    argument is pulled out and returned rather than discarded.
    """
    kept, narration = [], []
    for line in sql.splitlines():
        if line.lstrip().startswith("\\"):
            stripped = line.strip()
            if stripped.startswith("\\echo"):
                text = stripped[len("\\echo"):].strip()
                # \echo '' is a blank line in psql output; keep it as one.
                if len(text) >= 2 and text[0] == text[-1] == "'":
                    text = text[1:-1]
                narration.append(text)
            # Every other meta-command (\timing, \copy, \d) is a client
            # feature with no server equivalent. Dropped silently: they change
            # how psql PRESENTS a run, never what it does to the database.
            kept.append("")          # keep line numbers honest
            continue
        kept.append(line)
    return "\n".join(kept), narration


def bare_sql(stmt):
    """`stmt` with its comments stripped -- what the statement actually runs.

    Two callers need this and for the same reason: a fragment that is only
    comments has nothing to execute, and a statement's first LINE does not say
    what it does. The repair script's REFRESH lives inside a DO block that
    falls back to a blocking refresh, so it announces itself as `DO $refresh$`
    and anything matching on the first line stops seeing it.
    """
    bare = re.sub(r"--[^\n]*", "", stmt)
    bare = re.sub(r"/\*.*?\*/", "", bare, flags=re.S)
    return bare.strip()


def split_statements(sql):
    """Split into executable statements, honouring quoting and comments.

    Returns statements with transaction-control ones removed. Whitespace-only
    and comment-only fragments are dropped, so the caller gets a list it can
    execute in order without checking each one first.
    """
    out, buf = [], []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]

        # -- line comment
        if ch == "-" and sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j == -1 else j
            buf.append(sql[i:j])
            i = j
            continue

        # /* block comment */ -- Postgres nests these, so count depth.
        if ch == "/" and sql.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if sql.startswith("/*", j):
                    depth += 1
                    j += 2
                elif sql.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            buf.append(sql[i:j])
            i = j
            continue

        # 'single quoted', with '' as the escape
        if ch == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            buf.append(sql[i:j])
            i = j
            continue

        # "quoted identifier"
        if ch == '"':
            j = sql.find('"', i + 1)
            j = n if j == -1 else j + 1
            buf.append(sql[i:j])
            i = j
            continue

        # $$ ... $$ / $tag$ ... $tag$ -- the one that matters for DO blocks
        if ch == "$":
            m = _DOLLAR_OPEN.match(sql, i)
            if m:
                tag = m.group(0)
                j = sql.find(tag, m.end())
                j = n if j == -1 else j + len(tag)
                buf.append(sql[i:j])
                i = j
                continue

        if ch == ";":
            out.append("".join(buf))
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    if buf:
        out.append("".join(buf))

    statements = []
    for raw in out:
        # A fragment that is only comments and whitespace has nothing to run.
        bare = bare_sql(raw)
        if not bare:
            continue
        if _TXN.match(bare):
            continue
        statements.append(raw.strip())
    return statements
