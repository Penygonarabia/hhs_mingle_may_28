# -*- coding: utf-8 -*-
"""Build the ERP master-data defects report as a standalone HTML file.

WHAT THIS IS FOR. docs/erp_master_data_defects.html was written by hand against
dbprod: five defects, each traced to the documents that show it. It is a
document you hand to whoever maintains the ERP. This route re-runs every one of
those detections on whichever server it runs on, so the next server gets its own
evidence instead of dbprod's.

READ-ONLY. Every statement here is a SELECT. Nothing is written, and nothing is
sent anywhere -- the file is handed back to the browser that asked for it.

WHAT IS DETECTED AND WHAT IS WRITTEN DOWN. The evidence is measured; the reading
of it is not. Each defect carries a fixed explanation and a fixed request,
because those are a judgement about what the ERP should do, and re-deriving them
per server would be inventing an opinion from a row count. What changes per
server is the numbers, the documents, and whether the defect is present at all.

A DEFECT THAT IS ABSENT SAYS SO. The report does not quietly omit a clean check
-- a reader needs to know a thing was looked for and not found, or they cannot
tell a clean server from an unfinished report.

PROBED, NEVER ASSUMED. `transaction_details`, `catalog`, `bidata` and
`product_category` are all checked before use; a server missing one gets that
section marked unavailable rather than a traceback. See optional_schema.py in
pbi_dashboards for the same rule applied to the boards' own reads.
"""

import json
import logging
import os

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'study', 'defects_template.html')

# The AC product groups these boards report on. Same list the fact view's
# in_scope test uses; a server reporting a different set should change both.
AC_GROUPS = ('ACACC', 'ACCON', 'ACCST', 'ACPAC', 'ACPKG', 'ACAIP',
             'ACPOR', 'ACVRF', 'ACWIN', 'ACWTS', 'ACHCL', 'ATOM')

# Evidence tables are for reading, not for exporting: enough rows to see the
# shape of a defect, not every instance of it. The headline count above each
# table is unlimited and is the number that matters.
ROW_LIMIT = 25


# `catalog` carries no index on cat_part, so a correlated lookup per detail line
# seq-scans all 11k of it 200k times and the request never returns. Every read of
# it below therefore goes through this CTE once and joins -- a hash join over one
# scan. Measured: minutes to under a second.
CAT_CTE = """
    WITH cat AS (
        SELECT DISTINCT UPPER(TRIM(cat_grp))  AS grp,
                        UPPER(TRIM(cat_part)) AS upart,
                        TRIM(cat_part)        AS as_catalogued
        FROM catalog
    )
"""

# A detection that cannot answer quickly is a bug in the detection, not a
# licence to hold a worker open. Same reasoning as the scripts page's ceiling.
STATEMENT_TIMEOUT = '120s'


def _rows(cr, sql, params=()):
    cr.execute(sql, params)
    cols = [d[0] for d in cr.description]
    return [dict(zip(cols, r)) for r in cr.fetchall()]


def _has(cr, name):
    cr.execute("SELECT to_regclass(%s)", (name,))
    return cr.fetchone()[0] is not None


def _cell(v):
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, (int, float)):
        return v
    return str(v)


def _table(caption, columns, rows, numeric=()):
    return {'caption': caption, 'columns': columns,
            'numeric': list(numeric),
            'rows': [[_cell(r[c]) for c in columns] for r in rows]}


class PbiDashboardConfigDefects(http.Controller):

    def _has_access(self):
        from .main import PbiDashboardConfigurations
        return PbiDashboardConfigurations()._has_access()

    # ---------------------------------------------------------------- 01
    def _lowercase_parts(self, cr):
        """Part numbers typed in a case the catalogue does not hold.

        The ERP's own sales report matches part numbers case-sensitively, so
        these lines fail its unit lookup and their machines go uncounted --
        while their VALUE is counted, because that calculation does not use the
        lookup. That asymmetry is the signature: a month reconciles on revenue
        and disagrees on units.
        """
        rows = _rows(cr, CAT_CTE + """
            SELECT TRIM(h.trnh_no) AS document, h.trnh_date AS date,
                   TRIM(h.trnh_cstno) AS customer,
                   TRIM(d.trnd_part) AS part_as_entered,
                   c.as_catalogued AS catalogue_holds,
                   SUM(COALESCE(d.trnd_qtyiss, 0))::int AS units
            FROM transaction_details d
            JOIN transaction_header h ON h.id = d.header_id
            JOIN cat c ON c.grp = UPPER(TRIM(d.trnd_group))
                      AND c.upart = UPPER(TRIM(d.trnd_part))
            WHERE TRIM(d.trnd_group) = 'MDA'
              AND TRIM(d.trnd_part) <> c.as_catalogued
              AND TRIM(h.trnh_status) IN ('C', 'P')
            GROUP BY 1, 2, 3, 4, 5
            ORDER BY h.trnh_date
        """)
        total = sum(r['units'] for r in rows)
        return {
            'idx': '01',
            'title': 'Part numbers entered in a case the catalogue does not hold',
            'found': bool(rows),
            'count': len(rows),
            'summary': ('%d invoice line%s carr%s a part number whose letter case differs from '
                        'the form held in the product catalogue, covering %d unit%s. The parts '
                        'are otherwise correct and the stock exists — only the case differs.'
                        % (len(rows), '' if len(rows) == 1 else 's',
                           'ies' if len(rows) == 1 else 'y', total,
                           '' if total == 1 else 's')) if rows else
                       'No invoice line carries a part number in a case the catalogue does not hold.',
            'tables': [_table('The lines, and the form the catalogue holds',
                              ['document', 'date', 'customer', 'part_as_entered',
                               'catalogue_holds', 'units'],
                              rows[:ROW_LIMIT], numeric=['units'])] if rows else [],
            'requested': ('Correct the case on the documents listed, so the ERP’s own report picks '
                          'them up. A durable fix would be to match part numbers case-insensitively '
                          'at entry or in reporting, which also prevents recurrence.'),
        }

    # ---------------------------------------------------------------- 02
    def _dangling_group(self, cr):
        """Product groups referenced by invoice lines that no longer exist."""
        rows = _rows(cr, """
            SELECT d.trnd_groupid AS missing_group_id,
                   SUBSTRING(h.trnh_date, 1, 4) AS year,
                   COUNT(*)::int AS invoice_lines,
                   COUNT(DISTINCT UPPER(TRIM(d.trnd_part)))::int AS distinct_parts
            FROM transaction_details d
            JOIN transaction_header h ON h.id = d.header_id
            WHERE d.trnd_groupid IS NOT NULL
              AND TRIM(d.trnd_group) = 'MDA'
              AND NOT EXISTS (SELECT 1 FROM product_category c WHERE c.id = d.trnd_groupid)
            GROUP BY 1, 2 ORDER BY 2, 3 DESC
        """)
        lines = sum(r['invoice_lines'] for r in rows)
        ids = sorted({r['missing_group_id'] for r in rows})
        return {
            'idx': '02',
            'title': 'A product group was deleted while invoice lines still referenced it',
            'found': bool(rows),
            'count': lines,
            'summary': ('%d invoice line%s still point at product group%s %s, which no longer '
                        'exist%s in the product category master. Nothing was reassigned when '
                        'they were removed, so reporting must fall back to the parts catalogue '
                        'to classify them — and any line the catalogue cannot classify either '
                        'drops out of the figures altogether.'
                        % (lines, '' if lines == 1 else 's', '' if len(ids) == 1 else 's',
                           ', '.join(str(i) for i in ids), 's' if len(ids) == 1 else '')) if rows else
                       'Every product group referenced by an invoice line exists in the category master.',
            'tables': [_table('Lines still pointing at a group that is gone',
                              ['missing_group_id', 'year', 'invoice_lines', 'distinct_parts'],
                              rows[:ROW_LIMIT],
                              numeric=['invoice_lines', 'distinct_parts'])] if rows else [],
            'requested': ('Restore the deleted group under its franchise so the references resolve '
                          'again, or reassign those lines to the group that should now hold them.'),
        }

    # ---------------------------------------------------------------- 03
    def _unclassifiable_lines(self, cr):
        """Lines carrying no product group AND no catalogue entry.

        Either alone is survivable -- the group classifies the line, or the
        catalogue does. With neither, nothing can, and the line leaves the AC
        figures entirely. This is the one that costs value rather than
        attribution.

        THE PART MUST BE KNOWN AS A PRODUCT SOMEWHERE, and that qualifier is
        what makes this a defect list rather than noise. Service pseudo-parts --
        INSPECTION, AMC, ADV_PAYMENT, MISCELLANEOUS, TEST-COMMISSION -- carry no
        group and no catalogue entry because they are not products, and they are
        the overwhelming majority by line count: 1,291 of the 1,292 on dbprod.
        Reporting those as defects would bury the one real line and waste the
        reader's time. A genuine part is flagged in `catalogflags` or has a
        `product_template`, and neither of those holds for any of the five.
        """
        known = ("SELECT UPPER(TRIM(default_code)) AS part FROM product_template "
                 "WHERE NULLIF(TRIM(default_code), '') IS NOT NULL")
        if _has(cr, 'catalogflags'):
            known += (" UNION SELECT UPPER(TRIM(cat_part)) FROM catalogflags "
                      "WHERE NULLIF(TRIM(cat_part), '') IS NOT NULL")
        rows = _rows(cr, CAT_CTE + ", known AS (" + known + ")" + """
            SELECT TRIM(h.trnh_no) AS document, h.trnh_date AS date,
                   TRIM(h.trnh_cstno) AS customer,
                   UPPER(TRIM(d.trnd_part)) AS part,""" + """
                   SUM(COALESCE(d.trnd_qtyiss, 0))::int AS units
            FROM transaction_details d
            JOIN transaction_header h ON h.id = d.header_id
            LEFT JOIN cat c ON c.grp = 'MDA' AND c.upart = UPPER(TRIM(d.trnd_part))
            WHERE TRIM(d.trnd_group) = 'MDA'
              AND d.trnd_groupid IS NULL
              AND TRIM(h.trnh_status) IN ('C', 'P')
              AND TRIM(h.trnh_cstno) NOT LIKE 'V%%'
              AND c.upart IS NULL
              AND UPPER(TRIM(d.trnd_part)) IN (SELECT part FROM known)
            GROUP BY 1, 2, 3, 4
            ORDER BY h.trnh_date DESC
        """)
        return {
            'idx': '03',
            'title': 'Lines with neither a product group nor a catalogue entry',
            'found': bool(rows),
            'count': len(rows),
            'summary': ('%d invoice line%s carr%s no product group AND no catalogue entry, so '
                        'nothing can classify %s. %s drop%s out of AC reporting altogether — '
                        'this is the case that costs value, not merely the right bucket.'
                        % (len(rows), '' if len(rows) == 1 else 's',
                           'ies' if len(rows) == 1 else 'y',
                           'it' if len(rows) == 1 else 'them',
                           'It' if len(rows) == 1 else 'They',
                           's' if len(rows) == 1 else '')) if rows else
                       'Every line carries either a product group or a catalogue entry, so all can be classified.',
            'tables': [_table('Lines nothing can classify',
                              ['document', 'date', 'customer', 'part', 'units'],
                              rows[:ROW_LIMIT], numeric=['units'])] if rows else [],
            'requested': ('Assign the product group on the documents listed, and create the missing '
                          'catalogue entries for their parts — either one recovers the line, and the '
                          'catalogue entry also covers any future sale of the same part.'),
        }

    # ---------------------------------------------------------------- 04
    def _stalled_catalogue(self, cr):
        """Parts that sell in an AC group but were never catalogued."""
        # The FEED's own last delivery, excluding rows a local backfill added --
        # otherwise a previous repair makes the feed look current. The derived
        # count is reported separately: "every part has an entry" would be a
        # misleading all-clear if the entries were written here rather than
        # delivered.
        last = _rows(cr, """
            SELECT MAX(create_date) FILTER (
                       WHERE cat_comments IS NULL OR cat_comments NOT LIKE 'DERIVED %%'
                   )::date AS feed_last_loaded,
                   COUNT(*) FILTER (WHERE cat_comments LIKE 'DERIVED %%')::int AS derived_rows
            FROM catalog
        """)[0]
        rows = _rows(cr, CAT_CTE + """
            SELECT TRIM(pg.code) AS product_group,
                   COUNT(*)::int AS parts_with_no_entry
            FROM (
                SELECT UPPER(TRIM(d.trnd_part)) AS part, MAX(d.trnd_groupid) AS gid
                FROM transaction_details d
                JOIN transaction_header h ON h.id = d.header_id
                LEFT JOIN cat c ON c.grp = 'MDA' AND c.upart = UPPER(TRIM(d.trnd_part))
                WHERE TRIM(d.trnd_group) = 'MDA'
                  AND NULLIF(TRIM(d.trnd_part), '') IS NOT NULL
                  AND TRIM(h.trnh_cstno) NOT LIKE 'V%%'
                  AND c.upart IS NULL
                GROUP BY 1
            ) src
            JOIN product_category pg ON pg.id = src.gid
            JOIN product_category pgf ON pgf.id = pg.parent_id AND TRIM(pgf.code) = 'MDA'
            WHERE (LENGTH(pg.parent_path) - LENGTH(REPLACE(pg.parent_path, '/', ''))) = 2
              AND TRIM(pg.code) IN %s
            GROUP BY 1 ORDER BY 2 DESC
        """, (AC_GROUPS,))
        parts = sum(r['parts_with_no_entry'] for r in rows)
        return {
            'idx': '04',
            'title': 'The parts catalogue has stopped receiving new parts',
            'found': bool(rows),
            'count': parts,
            'summary': ('The catalogue last delivered a record on %s. %d part%s that sell into AC '
                        'product groups have no catalogue entry at all. Without one a part is still '
                        'sold and still counted — every total stays correct — but it cannot be filed '
                        'under a product group, so it lands in a single unattributed bucket.'
                        % (last['feed_last_loaded'], parts, '' if parts == 1 else 's')) if rows else
                       ('The catalogue last delivered a record on %s, and every part that sells in an '
                        'AC group has an entry%s.'
                        % (last['feed_last_loaded'],
                           ' — though %d of those entries were derived locally rather than delivered '
                           'by the feed, so the feed itself is still behind'
                           % last['derived_rows'] if last['derived_rows'] else '')),
            'tables': [_table('Uncatalogued selling parts, by the group they belong to',
                              ['product_group', 'parts_with_no_entry'], rows,
                              numeric=['parts_with_no_entry'])] if rows else [],
            'requested': ('Resume the catalogue feed and deliver the parts that have already sold. '
                          'Until then reporting cannot attribute those sales to a product group.'),
        }

    # ---------------------------------------------------------------- 05
    def _feed_gaps(self, cr):
        """Posted documents the bidata extract never received.

        The extract applies its posted/unposted filter AT FEED TIME and carries
        no status column, while the ERP flips documents to posted IN PLACE
        afterwards. A document posted after the extract ran is invisible to it
        permanently, and nothing in the feed reveals the absence. It lands
        hardest on credit notes: an extract that never saw a return cannot
        subtract it, so units and revenue both read high.
        """
        reach = _rows(cr, "SELECT MAX(bi_invdate) AS max_invoice_date FROM bidata")[0]
        rows = _rows(cr, """
            SELECT LPAD(TRIM(h.trnh_type), 2, '0') AS type,
                   TRIM(h.trnh_no) AS document, h.trnh_date AS date,
                   TRIM(h.trnh_status) AS status, TRIM(h.trnh_cstno) AS customer,
                   COUNT(*)::int AS lines
            FROM transaction_details d
            JOIN transaction_header h ON h.id = d.header_id
            WHERE LPAD(TRIM(h.trnh_type), 2, '0') IN ('01', '02')
              AND TRIM(d.trnd_group) = 'MDA'
              AND TRIM(h.trnh_status) IN ('C', 'P')
              AND TRIM(h.trnh_cstno) NOT LIKE 'V%%'
              AND h.trnh_date <= %s
              AND NOT EXISTS (SELECT 1 FROM bidata b
                              WHERE TRIM(b.bi_invno) = TRIM(h.trnh_no))
            GROUP BY 1, 2, 3, 4, 5
            ORDER BY 1 DESC, h.trnh_date
        """, (reach['max_invoice_date'],))
        credits = [r for r in rows if r['type'] == '02']
        return {
            'idx': '05',
            'title': 'The extract never sees a document posted after it runs',
            'found': bool(rows),
            'count': len(rows),
            'summary': ('%d posted document%s dated within the extract’s own reach (to %s) %s no '
                        'rows in it at all, %d of them credit note%s. A return the extract never saw '
                        'cannot be subtracted, so both units and revenue read high.'
                        % (len(rows), '' if len(rows) == 1 else 's', reach['max_invoice_date'],
                           'has' if len(rows) == 1 else 'have', len(credits),
                           '' if len(credits) == 1 else 's')) if rows else
                       ('Every posted document dated within the extract’s reach (to %s) is present '
                        'in it.' % reach['max_invoice_date']),
            'tables': [_table('Posted in the ERP, absent from the extract',
                              ['type', 'document', 'date', 'status', 'customer', 'lines'],
                              rows[:ROW_LIMIT], numeric=['lines'])] if rows else [],
            'requested': ('Have the extract pick up documents whose STATUS has changed since the last '
                          'run, not only those created since. The problem is silent — nothing in the '
                          'feed shows the absence — and it lands on returns.'),
        }

    # ---------------------------------------------------------------- 06
    def _unmapped_sale_types(self, cr):
        """Sale types not mapped to any Sales Type Group (L1)."""
        if not _has(cr, 'sale_types') or not _has(cr, 'salestypes_group'):
            return {'idx': '06', 'title': 'Unmapped Sale Types (Level 1)', 'found': False, 'count': 0,
                    'summary': 'sale_types or salestypes_group table not present.', 'tables': [], 'requested': ''}
        rows = _rows(cr, """
            SELECT st.id, st.sal_ref AS sale_type_code, st.sal_name AS sale_type_name,
                   COUNT(h.id)::int AS transaction_count
            FROM sale_types st
            LEFT JOIN salestypes_group sg ON sg.id = st.saltype_group
            LEFT JOIN transaction_header h ON (h.trnh_xfaceid = st.id OR LPAD(TRIM(h.trnh_xface), 3, '0') = st.sal_ref)
            WHERE st.saltype_group IS NULL
            GROUP BY st.id, st.sal_ref, st.sal_name
            ORDER BY transaction_count DESC, st.sal_ref
        """)
        return {
            'idx': '06',
            'title': 'Sale types missing Sales Type Group mapping (Level 1)',
            'found': bool(rows),
            'count': len(rows),
            'summary': ('%d sale type%s %s not mapped to a Sales Type Group and default%s to "Others".'
                        % (len(rows), '' if len(rows) == 1 else 's',
                           'is' if len(rows) == 1 else 'are', '' if len(rows) == 1 else 's')) if rows else
                       'All sale types are assigned to a valid Sales Type Group.',
            'tables': [_table('Unmapped Sale Types', ['sale_type_code', 'sale_type_name', 'transaction_count'],
                              rows[:ROW_LIMIT], numeric=['transaction_count'])] if rows else [],
            'requested': 'Assign each sale type to its appropriate Sales Type Group in Dashboard Groups > Sale Types.',
        }

    # ---------------------------------------------------------------- 07
    def _unclassified_partners(self, cr):
        """Active customer partners missing Partner Classification (L2)."""
        rows = _rows(cr, """
            SELECT rp.id AS partner_id, rp.ref AS customer_code, rp.name AS customer_name,
                   COUNT(h.id)::int AS invoice_count,
                   ROUND(SUM(CASE WHEN LPAD(TRIM(h.trnh_type), 2, '0') = '02' THEN -COALESCE(d.trnd_ret, 0) * COALESCE(d.trnd_price, 0)
                                  ELSE COALESCE(d.trnd_qtyiss, 0) * COALESCE(d.trnd_price, 0) END)::numeric, 2) AS total_sales
            FROM res_partner rp
            JOIN transaction_header h ON rp.ref = TRIM(h.trnh_cstno)
            JOIN transaction_details d ON d.header_id = h.id
            WHERE rp.partner_classification_id IS NULL
              AND LPAD(TRIM(h.trnh_type), 2, '0') IN ('01', '02')
            GROUP BY rp.id, rp.ref, rp.name
            ORDER BY total_sales DESC
        """)
        return {
            'idx': '07',
            'title': 'Active customer partners missing Partner Classification (Level 2)',
            'found': bool(rows),
            'count': len(rows),
            'summary': ('%d active customer partner%s lack%s a classification and report%s under "Unassigned".'
                        % (len(rows), '' if len(rows) == 1 else 's', '' if len(rows) == 1 else 's',
                           '' if len(rows) == 1 else 's')) if rows else
                       'All active customer partners carry a valid Partner Classification.',
            'tables': [_table('Unclassified Active Partners',
                              ['customer_code', 'customer_name', 'invoice_count', 'total_sales'],
                              rows[:ROW_LIMIT], numeric=['invoice_count', 'total_sales'])] if rows else [],
            'requested': 'Assign partner classifications in Contacts / Partner Classification master.',
        }

    # ---------------------------------------------------------------- 08
    def _orphaned_salesmen(self, cr):
        """Transactions whose salesman code has no partner with is_salesman=true (L5)."""
        rows = _rows(cr, """
            SELECT TRIM(h.trnh_sman) AS salesman_code,
                   MAX(TRIM(h.trnh_salesmanname)) AS salesman_name_entered,
                   COUNT(DISTINCT h.id)::int AS invoice_count,
                   ROUND(SUM(CASE WHEN LPAD(TRIM(h.trnh_type), 2, '0') = '02' THEN -COALESCE(d.trnd_ret, 0) * COALESCE(d.trnd_price, 0)
                                  ELSE COALESCE(d.trnd_qtyiss, 0) * COALESCE(d.trnd_price, 0) END)::numeric, 2) AS total_sales
            FROM transaction_header h
            JOIN transaction_details d ON d.header_id = h.id
            LEFT JOIN res_partner sp ON (
                (sp.salesman_ref IS NOT NULL AND sp.salesman_ref = TRIM(h.trnh_sman))
                OR (sp.ref IS NOT NULL AND sp.ref = TRIM(h.trnh_sman))
                OR (h.trnh_smanid IS NOT NULL AND sp.id = h.trnh_smanid)
            ) AND sp.is_salesman = true
            WHERE sp.id IS NULL
              AND NULLIF(TRIM(h.trnh_sman), '') IS NOT NULL
              AND LPAD(TRIM(h.trnh_type), 2, '0') IN ('01', '02')
            GROUP BY TRIM(h.trnh_sman)
            ORDER BY total_sales DESC
        """)
        return {
            'idx': '08',
            'title': 'Transactions with salesman codes not linked to active salesman partners (Level 5)',
            'found': bool(rows),
            'count': len(rows),
            'summary': ('%d distinct salesman code%s on transactions %s not match an active partner with is_salesman=true.'
                        % (len(rows), '' if len(rows) == 1 else 's', 'does' if len(rows) == 1 else 'do')) if rows else
                       'All transaction salesman codes match active salesman partner records.',
            'tables': [_table('Unmatched Salesman Codes',
                              ['salesman_code', 'salesman_name_entered', 'invoice_count', 'total_sales'],
                              rows[:ROW_LIMIT], numeric=['invoice_count', 'total_sales'])] if rows else [],
            'requested': 'Tag the respective res_partner with is_salesman = true and set salesman_ref to match the code.',
        }

    # ---------------------------------------------------------------- 09
    def _untagged_categories(self, cr):
        """Product categories missing L7/L8 sub-category taxonomy tagging."""
        if not _has(cr, 'sub_category') or not _has(cr, 'main_category'):
            return {'idx': '09', 'title': 'Untagged Product Categories (Levels 7 & 8)', 'found': False, 'count': 0,
                    'summary': 'sub_category or main_category table not present.', 'tables': [], 'requested': ''}
        rows = _rows(cr, """
            SELECT pc.id, pc.name AS category_name, pc.code AS category_code,
                   COUNT(pt.id)::int AS templates_count
            FROM product_category pc
            LEFT JOIN product_template pt ON pt.categ_id = pc.id
            WHERE pc.sub_category IS NULL
            GROUP BY pc.id, pc.name, pc.code
            ORDER BY templates_count DESC, pc.name
        """)
        return {
            'idx': '09',
            'title': 'Product categories missing Sub-Category taxonomy (Levels 7 & 8)',
            'found': bool(rows),
            'count': len(rows),
            'summary': ('%d product categor%s lack%s sub-category tagging and report%s under "Unassigned".'
                        % (len(rows), 'y' if len(rows) == 1 else 'ies', '' if len(rows) == 1 else 's',
                           '' if len(rows) == 1 else 's')) if rows else
                       'All product categories have assigned Sub-Category taxonomy.',
            'tables': [_table('Untagged Categories', ['category_code', 'category_name', 'templates_count'],
                              rows[:ROW_LIMIT], numeric=['templates_count'])] if rows else [],
            'requested': 'Assign sub_category on product categories in Inventory > Configuration > Product Categories.',
        }

    # ------------------------------------------------------------------
    def _build(self):
        cr = request.env.cr
        cr.execute("SET LOCAL statement_timeout = %s", (STATEMENT_TIMEOUT,))
        have = {t: _has(cr, t) for t in
                ('transaction_details', 'transaction_header', 'catalog',
                 'product_category', 'bidata', 'res_partner', 'sale_types',
                 'salestypes_group', 'sub_category', 'main_category')}
        erp = have['transaction_details'] and have['transaction_header']
        defects, unavailable = [], []

        def run(fn, idx, title, needs):
            missing = [t for t in needs if not have.get(t, False)]
            if missing:
                unavailable.append({'idx': idx, 'title': title, 'missing': missing})
                return
            try:
                defects.append(fn(cr))
            except Exception as exc:                 # noqa: BLE001 - reported, not swallowed
                _logger.exception("defects report: detection %s failed", idx)
                unavailable.append({'idx': idx, 'title': title, 'error': str(exc)})

        run(self._lowercase_parts, '01', 'Part numbers entered in a case the catalogue does not hold',
            ['transaction_details', 'transaction_header', 'catalog'] if erp else ['transaction_details'])
        run(self._dangling_group, '02', 'A product group was deleted while invoice lines still referenced it',
            ['transaction_details', 'transaction_header', 'product_category'])
        run(self._unclassifiable_lines, '03', 'Lines with neither a product group nor a catalogue entry',
            ['transaction_details', 'transaction_header', 'catalog'])
        run(self._stalled_catalogue, '04', 'The parts catalogue has stopped receiving new parts',
            ['transaction_details', 'transaction_header', 'catalog', 'product_category'])
        run(self._feed_gaps, '05', 'The extract never sees a document posted after it runs',
            ['transaction_details', 'transaction_header', 'bidata'])
        run(self._unmapped_sale_types, '06', 'Sale types missing Sales Type Group mapping (Level 1)',
            ['sale_types', 'salestypes_group', 'transaction_header'])
        run(self._unclassified_partners, '07', 'Active customer partners missing Partner Classification (Level 2)',
            ['res_partner', 'transaction_header', 'transaction_details'])
        run(self._orphaned_salesmen, '08', 'Transactions with salesman codes not linked to active salesman partners (Level 5)',
            ['res_partner', 'transaction_header', 'transaction_details'])
        run(self._untagged_categories, '09', 'Product categories missing Sub-Category taxonomy (Levels 7 & 8)',
            ['product_category', 'sub_category', 'main_category'])

        return {
            'database': cr.dbname,
            'defects': defects,
            'unavailable': unavailable,
            'found': sum(1 for d in defects if d['found']),
            'checked': len(defects),
        }

    @http.route('/pbi_dashboards/config/build_defects', type='http', auth='user')
    def build_defects(self, **kw):
        if not self._has_access():
            return request.make_response(
                'Forbidden', headers=[('Content-Type', 'text/plain')], status=403)
        try:
            meta = self._build()
            with open(_TEMPLATE, 'r') as fh:
                html = fh.read()
            html = html.replace('"__DEFECTS_META__"', json.dumps(meta, separators=(',', ':'), default=str))
        except Exception as exc:                     # noqa: BLE001 - reported, not swallowed
            _logger.exception("config page: building the defects report failed")
            return request.make_response(
                'Could not build the report: %s' % exc,
                headers=[('Content-Type', 'text/plain')], status=500)

        _logger.info("config page: %s built the defects report (%d of %d checks found something)",
                     request.env.user.login, meta['found'], meta['checked'])
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Disposition', 'attachment; filename="erp_master_data_defects.html"'),
        ])
