import datetime
import re
from decimal import Decimal

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

# A valid PostgreSQL identifier as returned by information_schema (unquoted,
# public schema). Used to guard the table/view name we interpolate into
# COUNT(*)/SELECT * statements against SQL injection.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

# Foreign-key relationships from the pg_constraint catalog. Much faster than
# information_schema.constraint_column_usage on a database with many tables.
# Selects one row per FK column pair; append a WHERE clause on src/tgt.relname.
_FK_SQL = """
    SELECT src.relname AS src_table, srcatt.attname AS src_col,
           tgt.relname AS tgt_table, tgtatt.attname AS tgt_col
    FROM pg_constraint con
    JOIN pg_class src ON src.oid = con.conrelid
    JOIN pg_class tgt ON tgt.oid = con.confrelid
    JOIN pg_namespace ns ON ns.oid = src.relnamespace
    JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS sk(attnum, ord) ON true
    JOIN LATERAL unnest(con.confkey) WITH ORDINALITY AS tk(attnum, ord) ON tk.ord = sk.ord
    JOIN pg_attribute srcatt ON srcatt.attrelid = con.conrelid AND srcatt.attnum = sk.attnum
    JOIN pg_attribute tgtatt ON tgtatt.attrelid = con.confrelid AND tgtatt.attnum = tk.attnum
    WHERE con.contype = 'f' AND ns.nspname = 'public'
"""

# Columns ignored when guessing relationships from matching column names: they
# are technical/denormalised and would create meaningless joins.
_GENERIC_COLS = frozenset({
    "id", "create_uid", "write_uid", "create_date", "write_date",
    "__last_update", "display_name", "active", "name", "sequence", "color",
    "state", "company_id", "currency_id", "message_main_attachment_id",
    "parent_path", "user_lmd", "user_lmt", "lang_flag",
})


def _is_key_like(col):
    """A column that looks like a join key / business code."""
    c = col.lower()
    return "code" in c or c.endswith("_id") or c.endswith("no")


class SqlMsAnalyser(models.AbstractModel):
    _name = "database.studio.analyser"
    _description = "Database Studio Analyser"

    # -- helpers -----------------------------------------------------------
    @api.model
    def _check_access(self):
        if not self.env.user.has_group("database_studio.group_database_studio_user"):
            raise AccessError(_("You are not allowed to use Database Studio."))

    @api.model
    def _validate_object(self, name):
        """Make sure ``name`` is an existing table/view in the public schema
        and a syntactically safe identifier before it is used in a query."""
        if not name or not _IDENT_RE.match(name):
            raise UserError(_("Invalid object name: %s") % name)
        self.env.cr.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (name,),
        )
        if not self.env.cr.fetchone():
            raise UserError(_("Unknown table or view: %s") % name)

    @staticmethod
    def _fmt(value):
        if value is None:
            return None
        if isinstance(value, (bytes, memoryview)):
            return bytes(value).hex()
        return str(value)

    # Above this many rows the per-column aggregates are skipped: they are a
    # convenience, not worth a multi-second pass over a huge result set.
    _AGG_MAX_ROWS = 200000

    @staticmethod
    def _fmt_number(value):
        """Render an aggregate as a plain, non-scientific string."""
        if isinstance(value, Decimal):
            value = value.normalize()
            exponent = value.as_tuple().exponent
            # normalize() turns 1000 into 1E+3; expand it back. At the other
            # end, an average like 10/3 carries 28 digits -- round it off.
            if exponent > 0:
                value = value.quantize(Decimal(1))
            elif exponent < -6:
                value = value.quantize(Decimal("0.000001")).normalize()
            return format(value, "f")
        if isinstance(value, float):
            return format(round(value, 6), ".6f").rstrip("0").rstrip(".") or "0"
        return str(value)

    @api.model
    def _fmt_agg(self, value):
        """Numbers plainly, dates (and anything else) as their usual text."""
        if isinstance(value, (int, float, Decimal)):
            return self._fmt_number(value)
        return self._fmt(value)

    @api.model
    def _compute_aggregates(self, columns, rows):
        """Count/sum/avg/min/max per column over the *whole* result set.

        Computed here, while every row is still in hand, so the grid can show
        a total for a column without re-running the user's query (which could
        be slow, or not even repeatable).  Sum/average are only meaningful for
        numeric columns; min/max also cover dates; count is the number of
        non-NULL values and is filled in for every column.
        """
        if len(rows) > self._AGG_MAX_ROWS:
            return []
        n = len(columns)
        counts = [0] * n
        sums = [None] * n
        mins = [None] * n
        maxs = [None] * n
        numeric = [True] * n
        orderable = [True] * n
        for row in rows:
            for i in range(n):
                v = row[i]
                if v is None:
                    continue
                counts[i] += 1
                if numeric[i]:
                    if isinstance(v, bool) or not isinstance(v, (int, float, Decimal)):
                        numeric[i] = False
                        sums[i] = None
                    else:
                        sums[i] = v if sums[i] is None else sums[i] + v
                if orderable[i]:
                    if isinstance(v, bool) or not isinstance(
                        v, (int, float, Decimal, datetime.date, datetime.datetime)
                    ):
                        orderable[i] = False
                        mins[i] = maxs[i] = None
                    else:
                        try:
                            if mins[i] is None or v < mins[i]:
                                mins[i] = v
                            if maxs[i] is None or v > maxs[i]:
                                maxs[i] = v
                        except TypeError:
                            orderable[i] = False
                            mins[i] = maxs[i] = None
        out = []
        for i in range(n):
            agg = {"count": counts[i], "numeric": numeric[i] and counts[i] > 0}
            if numeric[i] and sums[i] is not None:
                agg["sum"] = self._fmt_number(sums[i])
                # int/Decimal sums divide as Decimal so the average of, say,
                # integer amounts doesn't come out as a binary float.
                total = Decimal(sums[i]) if isinstance(sums[i], int) else sums[i]
                agg["avg"] = self._fmt_number(total / counts[i])
            if mins[i] is not None:
                agg["min"] = self._fmt_agg(mins[i])
                agg["max"] = self._fmt_agg(maxs[i])
            out.append(agg)
        return out

    # -- rpc endpoints -----------------------------------------------------
    @api.model
    def get_objects(self):
        """Return the tables and views of the public schema, grouped."""
        self._check_access()
        self.env.cr.execute(
            """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        tables, views = [], []
        for name, ttype in self.env.cr.fetchall():
            (views if ttype == "VIEW" else tables).append(name)
        return {"tables": tables, "views": views, "favorites": self.get_favorites()}

    @api.model
    def get_favorites(self):
        """The current user's favourite tables/views."""
        self._check_access()
        favs = self.env["database.studio.favorite"].search(
            [("user_id", "=", self.env.uid)]
        )
        return [{"name": f.name, "type": f.obj_type or "table"} for f in favs]

    @api.model
    def toggle_favorite(self, name, obj_type="table"):
        """Add or remove a table/view from the user's favourites; returns the
        updated favourites list."""
        self._check_access()
        if _IDENT_RE.match(name or ""):
            Fav = self.env["database.studio.favorite"]
            existing = Fav.search(
                [("user_id", "=", self.env.uid), ("name", "=", name)], limit=1
            )
            if existing:
                existing.unlink()
            else:
                Fav.create({"name": name, "obj_type": obj_type})
        return self.get_favorites()

    @api.model
    def get_fields(self, table):
        """Column metadata for a table/view."""
        self._check_access()
        self._validate_object(table)
        self.env.cr.execute(
            """
            SELECT column_name, data_type, character_maximum_length,
                   numeric_precision, numeric_scale, datetime_precision,
                   is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        fields = []
        for (col, dtype, charlen, nprec, nscale, dprec, nullable) in self.env.cr.fetchall():
            if charlen is not None:
                precision = str(charlen)
            elif nprec is not None:
                precision = "%s,%s" % (nprec, nscale) if nscale else str(nprec)
            elif dprec is not None:
                precision = str(dprec)
            else:
                precision = ""
            fields.append({
                "name": col,
                "type": dtype,
                "precision": precision,
                "nullable": "YES" if nullable == "YES" else "NO",
            })
        return fields

    @api.model
    def get_fields_multi(self, tables):
        """Column metadata for several tables, grouped by table name."""
        self._check_access()
        groups = []
        for table in (tables or []):
            if not _IDENT_RE.match(table):
                continue
            groups.append({"table": table, "fields": self.get_fields(table)})
        return groups

    @api.model
    def get_data(self, table, page=1, limit=100):
        """Paginated rows of a table/view."""
        self._check_access()
        self._validate_object(table)
        page = max(1, int(page))
        limit = max(1, int(limit))
        self.env.cr.execute('SELECT COUNT(*) FROM "%s"' % table)
        total = self.env.cr.fetchone()[0]
        pages = max(1, (total + limit - 1) // limit)
        page = min(page, pages)
        offset = (page - 1) * limit
        self.env.cr.execute(
            'SELECT * FROM "%s" LIMIT %%s OFFSET %%s' % table, (limit, offset)
        )
        columns = [d[0] for d in self.env.cr.description]
        rows = [[self._fmt(v) for v in r] for r in self.env.cr.fetchall()]
        return {
            "columns": columns,
            "rows": rows,
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit,
        }

    def _columns_by_table(self, tables):
        self.env.cr.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ANY(%s)
            """,
            (tables,),
        )
        cols = {t: set() for t in tables}
        for t, c in self.env.cr.fetchall():
            cols.setdefault(t, set()).add(c)
        return cols

    def _relationship_edges(self, tables, cols):
        """Directed edges (a selected table's column -> another table's column)
        combining real foreign keys, user-defined relations, and matching
        column names. Each edge: (from_table, from_column, to_table, to_column,
        via) with via in FK / custom / name."""
        sel = set(tables)
        edges = []
        seen = set()

        def add(ft, fc, tt, tc, via):
            key = (ft, fc, tt, tc)
            if ft != tt and key not in seen:
                seen.add(key)
                edges.append({
                    "from_table": ft, "from_column": fc,
                    "to_table": tt, "to_column": tc, "via": via,
                })

        # Real foreign keys owned by the selected tables (outgoing).
        self.env.cr.execute(_FK_SQL + " AND src.relname = ANY(%s)", (tables,))
        for src, sc, tgt, tc in self.env.cr.fetchall():
            add(src, sc, tgt, tc, "FK")

        # User-defined relations touching a selected table (oriented so the
        # selected table is the "from" side).
        relations = self.env["database.studio.relation"].search([
            "|", ("from_table", "in", tables), ("to_table", "in", tables),
        ])
        for rel in relations:
            if rel.from_table in sel:
                add(rel.from_table, rel.from_column, rel.to_table, rel.to_column, "custom")
            elif rel.to_table in sel:
                add(rel.to_table, rel.to_column, rel.from_table, rel.from_column, "custom")

        # Matching column names between two selected tables (implicit join key).
        for i, a in enumerate(tables):
            for b in tables[i + 1:]:
                for col in sorted((cols.get(a, set()) & cols.get(b, set())) - _GENERIC_COLS):
                    add(a, col, b, col, "name")
        return edges

    @api.model
    def get_field_mapping(self, tables):
        """How the selected table(s) map to other tables: via foreign keys,
        user-defined relations, or matching column names. Also reports which
        selected tables have no detected relationship, with their candidate
        key columns so the user can wire one up."""
        self._check_access()
        tables = [t for t in (tables or []) if _IDENT_RE.match(t)]
        for t in tables:
            self._validate_object(t)
        if not tables:
            return {"rows": [], "unrelated": [], "candidates": {}}

        cols = self._columns_by_table(tables)
        rows = self._relationship_edges(tables, cols)
        rows.sort(key=lambda e: (e["from_table"], e["from_column"]))

        mentioned = set()
        for e in rows:
            mentioned.add(e["from_table"])
            mentioned.add(e["to_table"])
        unrelated = [t for t in tables if t not in mentioned]
        candidates = {
            t: sorted(c for c in cols.get(t, set()) if _is_key_like(c))
            for t in unrelated
        }
        return {"rows": rows, "unrelated": unrelated, "candidates": candidates}

    @api.model
    def run_query(self, query, page=1, limit=100):
        """Execute an arbitrary query and return a paginated result set."""
        self._check_access()
        empty = {"columns": [], "column_types": [], "rows": [], "total": 0,
                 "page": 1, "pages": 1, "limit": limit, "message": "",
                 "aggregates": []}
        if not query or not query.strip():
            return empty
        try:
            self.env.cr.execute(query)
        except Exception as e:
            self.env.cr.rollback()
            raise UserError(str(e))

        rowcount = self.env.cr.rowcount
        description = self.env.cr.description
        result = dict(empty)
        if description:
            columns = [d[0] for d in description]
            all_rows = self.env.cr.fetchall()
            # Read the types off the same cursor description, so the Fields tab
            # can list a query's own output columns -- results built from CTEs
            # or JSON belong to no table and have nothing else to describe them.
            column_types = self._description_types(description)
            total = len(all_rows)
            limit = max(1, int(limit))
            pages = max(1, (total + limit - 1) // limit)
            page = min(max(1, int(page)), pages)
            start = (page - 1) * limit
            result = {
                "columns": columns,
                "column_types": column_types,
                "rows": [[self._fmt(v) for v in r] for r in all_rows[start:start + limit]],
                "total": total,
                "page": page,
                "pages": pages,
                "limit": limit,
                "message": _("%s row(s) returned") % total,
                "aggregates": self._compute_aggregates(columns, all_rows),
            }
        else:
            result["message"] = _("%s row(s) affected") % rowcount

        return result

    # Hard cap on rows written to an "Export Excel" file, so a huge result
    # set can't exhaust worker memory. Used by the export controller.
    _EXPORT_MAX_ROWS = 200000

    @api.model
    def build_join_query(self, tables):
        """Build a starter SELECT joining the given tables using foreign keys,
        user-defined relations, or matching column names (LEFT JOIN), falling
        back to CROSS JOIN when no relationship is known."""
        self._check_access()
        tables = [t for t in (tables or []) if _IDENT_RE.match(t)]
        for t in tables:
            self._validate_object(t)
        if not tables:
            return {"query": ""}
        lines = self._from_clause(tables)
        query = "SELECT *\n" + "\n".join(lines) + "\nLIMIT 100"
        return {"query": query}

    def _from_clause(self, tables):
        """FROM/JOIN lines linking `tables`, using foreign keys, user-defined
        relations or matching column names, and CROSS JOIN as a last resort."""
        if len(tables) == 1:
            return ['FROM "%s"' % tables[0]]

        cols = self._columns_by_table(tables)
        # adjacency: table -> list of (other_table, this_col, other_col)
        adj = {t: [] for t in tables}
        for e in self._relationship_edges(tables, cols):
            a, ac, b, bc = e["from_table"], e["from_column"], e["to_table"], e["to_column"]
            if a in adj and b in adj:
                adj[a].append((b, ac, bc))
                adj[b].append((a, bc, ac))

        included = {tables[0]}
        lines = ['FROM "%s"' % tables[0]]
        remaining = tables[1:]
        progress = True
        while remaining and progress:
            progress = False
            for r in list(remaining):
                edge = next(((o, rc, oc) for (o, rc, oc) in adj[r] if o in included), None)
                if edge:
                    other, r_col, o_col = edge
                    lines.append(
                        'LEFT JOIN "%s" ON "%s"."%s" = "%s"."%s"'
                        % (r, r, r_col, other, o_col)
                    )
                    included.add(r)
                    remaining.remove(r)
                    progress = True
        for r in remaining:
            lines.append(
                'CROSS JOIN "%s" /* no relation found - add one in '
                'Database Studio > Relations */' % r
            )
        return lines

    # Column types that SUM() makes sense for when a GROUP BY turns the
    # non-grouped picks into aggregates.
    _NUMERIC_TYPES = frozenset({
        "smallint", "integer", "bigint", "decimal", "numeric", "real",
        "double precision", "money",
    })

    @api.model
    def build_field_query(self, fields, group_by=None, order_by=None):
        """Build a SELECT over the individual columns ticked in the Fields
        tab, across one table or several (joined the same way Build query
        joins whole tables).

        `fields`, `group_by` are [{"table":, "name":}]; `order_by` is the same
        plus {"dir": "asc"|"desc"}. When `group_by` is given, the picks that
        are not grouped can no longer be selected raw, so each becomes an
        aggregate — SUM for a numeric column, COUNT(DISTINCT ...) otherwise —
        alongside a COUNT(*), which keeps the generated SQL runnable as-is.
        """
        self._check_access()
        fields = self._clean_field_list(fields)
        if not fields:
            return {"query": ""}
        tables = []
        for f in fields:
            if f["table"] not in tables:
                tables.append(f["table"])
        for t in tables:
            self._validate_object(t)

        known = self._columns_by_table(tables)
        fields = [f for f in fields if f["name"] in known.get(f["table"], ())]
        if not fields:
            return {"query": ""}
        # Grouping/ordering only ever refers to columns that were picked.
        picked = {(f["table"], f["name"]) for f in fields}
        group_by = [g for g in self._clean_field_list(group_by)
                    if (g["table"], g["name"]) in picked]
        order_by = [o for o in self._clean_field_list(order_by, with_dir=True)
                    if (o["table"], o["name"]) in picked]

        types = self._column_types(tables)
        grouped = {(g["table"], g["name"]) for g in group_by}
        # A bare column name is only unambiguous while no other picked table
        # has one too; otherwise it is aliased table_column.
        name_count = {}
        for f in fields:
            name_count[f["name"]] = name_count.get(f["name"], 0) + 1

        def qualified(f):
            return '"%s"."%s"' % (f["table"], f["name"])

        def alias_for(f, suffix=""):
            base = f["name"] if name_count[f["name"]] == 1 else "%s_%s" % (f["table"], f["name"])
            return base + suffix

        select = []
        aggregate_alias = {}
        if group_by:
            for g in group_by:
                select.append("%s AS %s" % (qualified(g), alias_for(g)))
            select.append("COUNT(*) AS row_count")
            for f in fields:
                if (f["table"], f["name"]) in grouped:
                    continue
                dtype = types.get(f["table"], {}).get(f["name"], "")
                if dtype in self._NUMERIC_TYPES:
                    expr, suffix = "SUM(%s)" % qualified(f), "_sum"
                else:
                    expr, suffix = "COUNT(DISTINCT %s)" % qualified(f), "_count"
                alias = alias_for(f, suffix)
                aggregate_alias[(f["table"], f["name"])] = alias
                select.append("%s AS %s" % (expr, alias))
        else:
            for f in fields:
                if name_count[f["name"]] == 1:
                    select.append(qualified(f))
                else:
                    select.append("%s AS %s" % (qualified(f), alias_for(f)))

        parts = ["SELECT\n    " + ",\n    ".join(select)]
        parts.extend(self._from_clause(tables))
        if group_by:
            parts.append("GROUP BY " + ", ".join(qualified(g) for g in group_by))
        order_terms = []
        for o in order_by:
            key = (o["table"], o["name"])
            if not group_by:
                term = qualified(o)
            elif key in grouped:
                term = qualified(o)
            else:
                # Ordering by a column that grouping turned into an aggregate
                # has to name that aggregate instead.
                term = aggregate_alias.get(key)
            if term:
                order_terms.append("%s %s" % (term, "DESC" if o["dir"] == "desc" else "ASC"))
        if order_terms:
            parts.append("ORDER BY " + ", ".join(order_terms))
        parts.append("LIMIT 100")
        return {"query": "\n".join(parts)}

    @staticmethod
    def _clean_field_list(items, with_dir=False):
        """Drop anything that isn't a syntactically valid table/column pair."""
        out = []
        for item in (items or []):
            table = (item or {}).get("table") or ""
            name = (item or {}).get("name") or ""
            if not _IDENT_RE.match(table) or not _IDENT_RE.match(name):
                continue
            entry = {"table": table, "name": name}
            if with_dir:
                entry["dir"] = "desc" if (item.get("dir") == "desc") else "asc"
            out.append(entry)
        return out

    def _column_types(self, tables):
        self.env.cr.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ANY(%s)
            """,
            (tables,),
        )
        types = {}
        for t, c, dtype in self.env.cr.fetchall():
            types.setdefault(t, {})[c] = dtype
        return types


    # -- column type conversion -------------------------------------------
    # Numeric types a text column can be converted to, with the cast used in
    # the ALTER's USING clause. Integers go through numeric first so that
    # "12.7" rounds instead of failing outright the way '12.7'::integer does.
    _CONVERT_TARGETS = {
        "numeric": "numeric",
        "integer": "numeric::integer",
        "bigint": "numeric::bigint",
        "double precision": "double precision",
    }

    # Source types a conversion is offered for. Anything else is left alone:
    # the point of the feature is rescuing numbers stored as text.
    _TEXT_TYPES = frozenset({"text", "character varying", "character"})

    # A text value PostgreSQL will accept as a number. Values failing this are
    # what makes a conversion blow up half way through the table.
    _NUMERIC_LITERAL_RE = r'^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$'
    # Of the convertible ones, those that are not whole numbers -- they round
    # when the target is integer/bigint.
    _FRACTIONAL_RE = r'(\.[0-9]*[1-9])|[eE]'

    _CONVERT_SAMPLES = 5

    @api.model
    def _is_base_table(self, name):
        """Whether `name` is a real table. A view's columns cannot be ALTERed,
        and the Fields tab happily lists views alongside tables, so this is
        reported per object rather than raised."""
        self._validate_object(name)
        self.env.cr.execute(
            """
            SELECT table_type FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (name,),
        )
        return (self.env.cr.fetchone() or [""])[0] == "BASE TABLE"

    def _convert_expr(self, column, target, safe=False):
        """The cast for one column: blank/whitespace-only text becomes NULL
        rather than failing. `safe` additionally lets a value that is not a
        number through as NULL instead of aborting the whole statement -- only
        useful when rewriting a query, where nothing is being overwritten."""
        cast = self._CONVERT_TARGETS[target]
        if safe:
            return ('CASE WHEN btrim("%s") ~ \'%s\' THEN btrim("%s")::%s END'
                    % (column, self._NUMERIC_LITERAL_RE, column, cast))
        return 'NULLIF(btrim("%s"), \'\')::%s' % (column, cast)

    def _dependent_views(self, table, columns):
        """Views built on these columns. PostgreSQL refuses to alter a column
        a view selects, so this is the difference between a clean conversion
        and an error the user cannot read."""
        self.env.cr.execute(
            """
            SELECT DISTINCT dep.relname
            FROM pg_depend d
            JOIN pg_rewrite r ON r.oid = d.objid
            JOIN pg_class dep ON dep.oid = r.ev_class
            JOIN pg_class src ON src.oid = d.refobjid
            JOIN pg_attribute a ON a.attrelid = src.oid AND a.attnum = d.refobjsubid
            JOIN pg_namespace ns ON ns.oid = src.relnamespace
            WHERE ns.nspname = 'public' AND src.relname = %s
              AND a.attname = ANY(%s) AND dep.relname <> %s
            ORDER BY 1
            """,
            (table, columns, table),
        )
        return [r[0] for r in self.env.cr.fetchall()]

    def _odoo_fields_for(self, table, columns):
        """Stored ORM fields sitting on these columns, so the user is told the
        Python side still calls them Char/Text."""
        self.env.cr.execute(
            """
            SELECT m.model, f.name
            FROM ir_model_fields f
            JOIN ir_model m ON m.id = f.model_id
            WHERE replace(m.model, '.', '_') = %s AND f.name = ANY(%s)
              AND f.store = true AND f.ttype IN ('char', 'text', 'html')
            ORDER BY 1, 2
            """,
            (table, columns),
        )
        return ["%s.%s" % (model, name) for model, name in self.env.cr.fetchall()]

    def _profile_columns(self, from_sql, columns, target):
        """How the values in each column would survive the conversion.

        `from_sql` is whatever can follow FROM -- a quoted table name, or a
        parenthesised sub-select wrapping the user's own query. Every column is
        counted in a single pass, so picking twenty of them still reads the
        table once; only the columns that turn out to hold something
        unconvertible cost an extra (tiny) query for their samples.
        """
        if not columns:
            return {}
        selects, params = ["count(*)"], []
        for col in columns:
            c = '"%s"' % col
            selects.append(
                "count(*) FILTER (WHERE {c} IS NOT NULL AND btrim({c}) = '')".format(c=c)
            )
            selects.append(
                "count(*) FILTER (WHERE {c} IS NOT NULL AND btrim({c}) <> '' "
                "AND btrim({c}) !~ %s)".format(c=c)
            )
            params.append(self._NUMERIC_LITERAL_RE)
            selects.append(
                "count(*) FILTER (WHERE {c} IS NOT NULL AND btrim({c}) <> '' "
                "AND btrim({c}) ~ %s AND btrim({c}) ~ %s)".format(c=c)
            )
            params.extend([self._NUMERIC_LITERAL_RE, self._FRACTIONAL_RE])
        self.env.cr.execute(
            "SELECT " + ",\n       ".join(selects) + "\nFROM " + from_sql, params
        )
        row = self.env.cr.fetchone()
        total = row[0]
        out = {}
        for i, col in enumerate(columns):
            blanks, bad, fractional = row[1 + i * 3:4 + i * 3]
            out[col] = {
                "total": total, "blanks": blanks, "bad": bad,
                "fractional": fractional if target in ("integer", "bigint") else 0,
                "samples": self._bad_samples(from_sql, col) if bad else [],
            }
        return out

    def _bad_samples(self, from_sql, column):
        """A few of the values that will not cast, to show the user what is in
        the way."""
        self.env.cr.execute(
            'SELECT DISTINCT btrim("{col}") FROM {frm}\n'
            ' WHERE "{col}" IS NOT NULL AND btrim("{col}") <> \'\''
            ' AND btrim("{col}") !~ %s LIMIT %s'.format(col=column, frm=from_sql),
            (self._NUMERIC_LITERAL_RE, self._CONVERT_SAMPLES),
        )
        return [r[0] for r in self.env.cr.fetchall()]

    def _convert_statements(self, table, columns, target, defaults):
        """The ALTER TABLE for one table, as a list of statements. A column
        default (``''::varchar`` and friends) cannot be cast along with the
        column, so it is dropped first."""
        stmts = []
        dropped = [c for c in columns if defaults.get(c)]
        for col in dropped:
            stmts.append('ALTER TABLE "%s" ALTER COLUMN "%s" DROP DEFAULT' % (table, col))
        clauses = [
            'ALTER COLUMN "%s" TYPE %s USING %s'
            % (col, target, self._convert_expr(col, target))
            for col in columns
        ]
        stmts.append('ALTER TABLE "%s"\n    %s' % (table, ",\n    ".join(clauses)))
        return stmts

    def _blank_bad_statement(self, table, column):
        return (
            'UPDATE "%s" SET "%s" = NULL\n'
            ' WHERE "%s" IS NOT NULL AND btrim("%s") <> \'\' AND btrim("%s") !~ %%s'
            % (table, column, column, column, column)
        )

    def _grouped_columns(self, items):
        """Validated {table: [column, ...]} from the picked-field payload,
        keeping the order the user ticked them in."""
        grouped = {}
        for item in self._clean_field_list(items):
            grouped.setdefault(item["table"], [])
            if item["name"] not in grouped[item["table"]]:
                grouped[item["table"]].append(item["name"])
        return grouped

    @api.model
    def check_column_conversion(self, items, target="numeric"):
        """Dry-run a text -> number conversion of the picked columns: what
        each column holds, what would be lost, and the exact SQL that would
        run. Nothing is written."""
        self._check_access()
        if target not in self._CONVERT_TARGETS:
            raise UserError(_("Unsupported target type: %s") % target)
        grouped = self._grouped_columns(items)
        columns, warnings, sql_blocks = [], [], []
        for table in grouped:
            is_table = self._is_base_table(table)
            types = self._column_types([table]).get(table, {})
            defaults = self._column_defaults(table) if is_table else {}
            convertible = []
            for col in grouped[table]:
                dtype = types.get(col)
                entry = {"table": table, "name": col, "type": dtype or "?"}
                if not is_table:
                    entry.update(
                        convertible=False,
                        reason=_("%s is a view — its columns cannot be altered") % table,
                    )
                elif dtype is None:
                    entry.update(convertible=False, reason=_("no such column"))
                elif dtype == target:
                    entry.update(convertible=False, reason=_("already %s") % target)
                elif dtype not in self._TEXT_TYPES:
                    entry.update(
                        convertible=False,
                        reason=_("only text columns can be converted"),
                    )
                else:
                    entry.update(convertible=True, reason="")
                    entry["drop_default"] = bool(defaults.get(col))
                    convertible.append(col)
                columns.append(entry)
            if convertible:
                profiles = self._profile_columns('"%s"' % table, convertible, target)
                for entry in columns:
                    if entry["table"] == table and entry["name"] in profiles:
                        entry.update(profiles[entry["name"]])
                views = self._dependent_views(table, convertible)
                if views:
                    warnings.append(
                        _("%(table)s: these views depend on the column(s) and must be "
                          "dropped first — %(views)s")
                        % {"table": table, "views": ", ".join(views)}
                    )
                orm_fields = self._odoo_fields_for(table, convertible)
                if orm_fields:
                    warnings.append(
                        _("%(table)s: still declared as text by the ORM — %(fields)s. "
                          "Odoo will keep writing text to them and an upgrade of the "
                          "module owning them will convert the column back.")
                        % {"table": table, "fields": ", ".join(orm_fields)}
                    )
                sql_blocks.extend(
                    self._convert_statements(table, convertible, target, defaults)
                )
        return {
            "mode": "table",
            "target": target,
            "columns": columns,
            "warnings": warnings,
            "sql": ";\n".join(sql_blocks) + (";" if sql_blocks else ""),
            "can_convert": any(c["convertible"] for c in columns),
        }

    def _column_defaults(self, table):
        self.env.cr.execute(
            """
            SELECT column_name, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table,),
        )
        return {c: d for c, d in self.env.cr.fetchall()}

    @api.model
    def convert_columns(self, items, target="numeric", blank_bad=False):
        """Convert the picked text columns to `target`. Each table is altered
        inside its own savepoint, so one table failing (a dependent view, a
        value that will not cast) leaves the others converted and reports the
        error instead of losing the lot.

        With `blank_bad` the values that cannot be read as a number are set to
        NULL first — that is data loss, so the caller has to ask for it.
        """
        self._check_access()
        if target not in self._CONVERT_TARGETS:
            raise UserError(_("Unsupported target type: %s") % target)
        grouped = self._grouped_columns(items)
        results = []
        for table in grouped:
            if not self._is_base_table(table):
                results.append({
                    "table": table, "columns": [], "skipped": grouped[table],
                    "ok": False, "blanked": 0,
                    "error": _("%s is a view — its columns cannot be altered") % table,
                })
                continue
            types = self._column_types([table]).get(table, {})
            defaults = self._column_defaults(table)
            columns = [
                c for c in grouped[table]
                if types.get(c) in self._TEXT_TYPES and types.get(c) != target
            ]
            skipped = [c for c in grouped[table] if c not in columns]
            if not columns:
                results.append({
                    "table": table, "columns": [], "skipped": skipped,
                    "ok": False, "error": _("nothing to convert"), "blanked": 0,
                })
                continue
            blanked = 0
            try:
                with self.env.cr.savepoint():
                    if blank_bad:
                        for col in columns:
                            self.env.cr.execute(
                                self._blank_bad_statement(table, col),
                                (self._NUMERIC_LITERAL_RE,),
                            )
                            blanked += self.env.cr.rowcount
                    for stmt in self._convert_statements(table, columns, target, defaults):
                        self.env.cr.execute(stmt)
            except Exception as e:  # noqa: BLE001 - reported back to the UI
                results.append({
                    "table": table, "columns": columns, "skipped": skipped,
                    "ok": False, "error": str(e).strip(), "blanked": 0,
                })
            else:
                results.append({
                    "table": table, "columns": columns, "skipped": skipped,
                    "ok": True, "error": "", "blanked": blanked,
                })
        converted = sum(len(r["columns"]) for r in results if r["ok"])
        return {
            "results": results,
            "converted": converted,
            "failed": sum(1 for r in results if not r["ok"]),
            "message": _("%(cols)s column(s) converted to %(type)s")
                       % {"cols": converted, "type": target},
        }


    # -- converting the columns of a query result -------------------------
    # A query's output columns belong to no table -- a CTE over a JSON literal
    # is the extreme case -- so there is nothing to ALTER. The equivalent is to
    # rewrite the query itself, wrapping it in a SELECT that casts the picked
    # columns, which is what these build.
    @staticmethod
    def _wrap_query(query):
        """`query` as a sub-select usable after FROM."""
        return "(\n%s\n) sqlms_q" % (query or "").strip().rstrip(";").rstrip()

    @api.model
    def _description_types(self, description):
        """PostgreSQL type names for a cursor description, in column order."""
        oids = list({d.type_code for d in description})
        if not oids:
            return []
        self.env.cr.execute(
            "SELECT oid, format_type(oid, NULL) FROM pg_type WHERE oid = ANY(%s)",
            (oids,),
        )
        names = dict(self.env.cr.fetchall())
        return [names.get(d.type_code, "") for d in description]

    @api.model
    def _result_columns(self, query):
        """The name and type of every column `query` returns, without fetching
        a single row."""
        if not (query or "").strip():
            raise UserError(_("Run a query first: there are no result columns yet."))
        try:
            self.env.cr.execute("SELECT * FROM " + self._wrap_query(query) + " LIMIT 0")
        except Exception as e:
            self.env.cr.rollback()
            raise UserError(str(e))
        description = self.env.cr.description or []
        types = self._description_types(description)
        return [{"name": d[0], "type": t} for d, t in zip(description, types)]

    @api.model
    def get_result_field_types(self, query):
        """Result columns of `query` for the Fields tab, in the same shape the
        table field list uses."""
        self._check_access()
        return [
            {"name": c["name"], "type": c["type"], "precision": "", "nullable": ""}
            for c in self._result_columns(query)
        ]

    def _cast_query(self, query, result_columns, convert, target, safe=False):
        """`query` wrapped in a SELECT that casts the columns in `convert` and
        passes the rest through unchanged."""
        select = []
        for col in result_columns:
            name = col["name"]
            if name in convert:
                select.append(
                    '%s AS "%s"' % (self._convert_expr(name, target, safe), name)
                )
            else:
                select.append('"%s"' % name)
        return ("SELECT\n    " + ",\n    ".join(select) +
                "\nFROM " + self._wrap_query(query))

    @api.model
    def check_query_conversion(self, query, columns, target="numeric", safe=False):
        """Dry-run turning result columns of `query` into numbers. Same report
        as check_column_conversion, but the SQL it returns is a rewritten
        query rather than an ALTER: nothing in the database changes."""
        self._check_access()
        if target not in self._CONVERT_TARGETS:
            raise UserError(_("Unsupported target type: %s") % target)
        result_columns = self._result_columns(query)
        names = [c["name"] for c in result_columns]
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            raise UserError(
                _("The query returns more than one column named %s. Give them "
                  "distinct aliases before converting.") % ", ".join(dupes)
            )
        types = {c["name"]: c["type"] for c in result_columns}
        picked = [c for c in (columns or []) if _IDENT_RE.match(c or "")]

        entries, convertible = [], []
        for name in picked:
            dtype = types.get(name)
            entry = {"table": _("query result"), "name": name, "type": dtype or "?"}
            if dtype is None:
                entry.update(convertible=False, reason=_("not in the result"))
            elif dtype == target:
                entry.update(convertible=False, reason=_("already %s") % target)
            elif dtype not in self._TEXT_TYPES:
                entry.update(convertible=False,
                             reason=_("only text columns can be converted"))
            else:
                entry.update(convertible=True, reason="", drop_default=False)
                convertible.append(name)
            entries.append(entry)

        if convertible:
            profiles = self._profile_columns(
                self._wrap_query(query), convertible, target
            )
            for entry in entries:
                if entry["name"] in profiles:
                    entry.update(profiles[entry["name"]])
        return {
            "mode": "query",
            "target": target,
            "columns": entries,
            "warnings": [],
            "sql": self._cast_query(query, result_columns, set(convertible),
                                    target, safe) if convertible else "",
            "can_convert": bool(convertible),
        }


class SqlMsQuery(models.Model):
    _name = "database.studio.query"
    _description = "Database Studio Query History"
    _order = "last_run desc"

    name = fields.Char(string="Name")
    query = fields.Text(string="SQL", required=True)
    is_favorite = fields.Boolean(string="Favorite")
    last_run = fields.Datetime(string="Last Run", default=fields.Datetime.now, index=True)
    run_count = fields.Integer(string="Runs", default=1)
    user_id = fields.Many2one(
        "res.users", string="User", ondelete="cascade",
        default=lambda self: self.env.user,
    )

    @staticmethod
    def _snippet(query):
        text = " ".join((query or "").split())
        return (text[:120] + "…") if len(text) > 120 else text

    def _find_own(self, query):
        return self.search(
            [("user_id", "=", self.env.uid), ("query", "=", query)], limit=1
        )

    @api.model
    def save_query(self, query, name=None):
        """Save/star a query from the Analyser, naming it (upsert per user)."""
        query = (query or "").strip()
        if not query:
            return False
        vals = {"is_favorite": True}
        if name:
            vals["name"] = name
        rec = self._find_own(query)
        if rec:
            rec.write(vals)
        else:
            vals.setdefault("name", self._snippet(query))
            rec = self.create(dict(vals, query=query))
        return {"id": rec.id, "name": rec.name}

    @api.model
    def save_query_id(self, record_id, query, name=None):
        """Save/star a query tab that is already linked to a History record
        (opened from History, or a prior Save) by updating that same record
        in place, instead of save_query's upsert-by-text — so editing the
        query and re-saving doesn't fork off a duplicate row."""
        rec = self.browse(record_id).exists()
        if not rec or rec.user_id.id != self.env.uid:
            return self.save_query(query, name)
        query = (query or "").strip()
        if not query:
            return False
        vals = {"is_favorite": True, "query": query}
        if name:
            vals["name"] = name
        rec.write(vals)
        return {"id": rec.id, "name": rec.name}

    @api.model
    def log_query_run(self, query):
        """Log an Execute click to History without marking it a favorite, so
        it shows up under the 'On the fly' tab. Bumps run stats on an
        existing record (favorite or not) rather than duplicating it."""
        query = (query or "").strip()
        if not query:
            return False
        rec = self._find_own(query)
        if rec:
            rec.write({"run_count": rec.run_count + 1, "last_run": fields.Datetime.now()})
        else:
            rec = self.create({"query": query, "name": self._snippet(query)})
        return {"id": rec.id, "name": rec.name, "is_favorite": rec.is_favorite}

    def action_unlink(self):
        """Per-row delete button in the history list."""
        self.unlink()

    def action_open_in_analyser(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "database_studio.analyser",
            "name": _("Analyser"),
            "params": {"query": self.query},
            "context": {"default_query": self.query},
        }

    @api.model
    def action_open_analyser(self):
        return {
            "type": "ir.actions.client",
            "tag": "database_studio.analyser",
            "name": _("Analyser"),
        }


class DatabaseStudioRelation(models.Model):
    _name = "database.studio.relation"
    _description = "Database Studio Custom Relation"
    _order = "from_table, from_column"

    from_table = fields.Char(string="From table", required=True)
    from_column = fields.Char(string="From column", required=True)
    to_table = fields.Char(string="To table", required=True)
    to_column = fields.Char(string="To column", required=True)
    note = fields.Char(string="Note")
    active = fields.Boolean(default=True)

    @api.depends("from_table", "from_column", "to_table", "to_column")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s.%s → %s.%s" % (
                rec.from_table or "?", rec.from_column or "?",
                rec.to_table or "?", rec.to_column or "?",
            )


class DatabaseStudioFavorite(models.Model):
    _name = "database.studio.favorite"
    _description = "Database Studio Favourite Object"
    _order = "name"

    user_id = fields.Many2one(
        "res.users", string="User", required=True, index=True,
        ondelete="cascade", default=lambda self: self.env.user,
    )
    name = fields.Char(string="Object", required=True)
    obj_type = fields.Char(string="Type")

    _sql_constraints = [
        ("uniq_user_name", "unique(user_id, name)",
         "This object is already in your favourites."),
    ]
