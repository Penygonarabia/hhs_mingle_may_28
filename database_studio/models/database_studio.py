import re

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
        empty = {"columns": [], "rows": [], "total": 0, "page": 1,
                 "pages": 1, "limit": limit, "message": ""}
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
            total = len(all_rows)
            limit = max(1, int(limit))
            pages = max(1, (total + limit - 1) // limit)
            page = min(max(1, int(page)), pages)
            start = (page - 1) * limit
            result = {
                "columns": columns,
                "rows": [[self._fmt(v) for v in r] for r in all_rows[start:start + limit]],
                "total": total,
                "page": page,
                "pages": pages,
                "limit": limit,
                "message": _("%s row(s) returned") % total,
            }
        else:
            result["message"] = _("%s row(s) affected") % rowcount

        # Log the executed query into history once per execution (not per page).
        # Runs only after the cursor's result set has been fully fetched.
        if int(page) == 1:
            self.env["database.studio.query"]._log(query)
        return result

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
        if len(tables) == 1:
            return {"query": 'SELECT *\nFROM "%s"\nLIMIT 100' % tables[0]}

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

        query = "SELECT *\n" + "\n".join(lines) + "\nLIMIT 100"
        return {"query": query}


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
    def _log(self, query):
        """Record an executed query, or bump its counter if already stored."""
        query = (query or "").strip()
        if not query:
            return
        existing = self._find_own(query)
        if existing:
            existing.write({
                "last_run": fields.Datetime.now(),
                "run_count": existing.run_count + 1,
            })
        else:
            self.create({"query": query, "name": self._snippet(query)})

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
