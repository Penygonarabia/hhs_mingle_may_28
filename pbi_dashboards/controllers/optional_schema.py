# -*- coding: utf-8 -*-
"""What this database actually has, for the tables and columns the boards read
but no module in this suite owns.

These dashboards are developed and released separately from the modules whose
data they display, and are merged into servers that already run their own
copies of those modules -- dashboard_groups, sales_budget,
partner_classification, salesman_res_partner, machine_repair_management, and
whichever of the modules that declare res.region is installed there. Declaring
a dependency on any of them would drag this suite's copy of that work into
those servers and overwrite code maintained by someone else, so the suite
depends on NONE of them and resolves their schema at build time instead.

Two probes and one stand-in:

  has_table / has_column  ask the live catalog; never assume a shape.
  column_ref              a qualified column where it exists, a typed NULL
                          where it does not.
  stub_ctes               an empty CTE, of the right shape, per absent table.

A stub is a CTE, and for the whole of a query a CTE shadows a real table of
the same name -- so a 600-line view body can go on reading `salestypes_group`
exactly as written whether the real table is there or not. Where it is not,
the stand-in yields no rows, every LEFT JOIN onto it yields NULL, and the
board opens with that one caption blank. That is already what an unfilled
dimension looks like there, so nothing new has to be taught to the front end.

This is only safe because of what these joins are: every one of them is a
LEFT JOIN supplying a LABEL. None filters a row, and none carries quantity or
value. An absent module costs captions, never figures. Do not extend this to a
table that decides which rows exist or what they sum to -- a silently empty
stand-in would then quietly change the numbers, which is far worse than
failing to install.

Mirrors optional_deps.py, which does the same job for python-pptx.
"""

import logging

_logger = logging.getLogger(__name__)


def has_table(cr, table):
    """True when `table` (a table, view or materialized view) exists here."""
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def has_column(cr, table, column):
    """True when `table` exists here AND carries `column`.

    Both halves matter: a module can be installed at a version that predates
    the column, which reads the same as not installed at all for our purposes.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def column_ref(cr, table, column, sql_type, alias=None):
    """SQL for reading `column` off `table`, whatever this database has.

    Returns the qualified column when it can be read -- either because the
    real table carries it, or because `table` is absent and stub_ctes has
    supplied a stand-in that does -- and a typed NULL when the table is here
    but this particular column is not.
    """
    ref = "%s.%s" % (alias or table, column)
    if not has_table(cr, table):
        return ref            # the stub carries every column we asked it for
    return ref if has_column(cr, table, column) else "NULL::%s" % sql_type


def missing_from(cr, required):
    """Which of `required` this database does not have, in the order given.

    An entry is either a table name (required whole) or a (table, column) pair
    (required down to that column, since a module can be installed at a version
    that predates it). Returns readable names -- "res_region",
    "product_category.code" -- fit for dropping straight into a log line.

    For callers that must have the real thing. Where a caller can carry on
    without it, stub_ctes and column_ref are the gentler answer; this one is
    for a view whose whole reason to exist is resolving codes against those
    masters, and which is therefore better left unbuilt than built empty.
    """
    absent = []
    for item in required:
        if isinstance(item, str):
            if not has_table(cr, item):
                absent.append(item)
        else:
            table, column = item
            if not has_column(cr, table, column):
                absent.append("%s.%s" % (table, column))
    return absent

def stub_ctes(cr, spec):
    """CTE text standing in for whichever of `spec`'s tables are absent.

    `spec` maps a table name to the (column, type) pairs the query reads off
    it -- only those; a stand-in needs no more. Returns SQL ready to open a
    WITH list with, ending in a comma when it is not empty, so the caller
    writes:

        WITH {stubs}first_real_cte AS (...)
    """
    parts, absent = [], []
    for table, columns in spec.items():
        if has_table(cr, table):
            continue
        absent.append(table)
        cols = ', '.join("NULL::%s AS %s" % (typ, name) for name, typ in columns)
        parts.append("%s AS (SELECT %s WHERE false)" % (table, cols))
    if absent:
        # Worth a line in the log: a board whose captions are blank looks like
        # a bug, and this names the module that would fill them.
        _logger.info(
            "pbi optional schema: %s not on this database; the labels they "
            "supply will read blank. Install the module that owns them and "
            "upgrade this one to pick them up.", ', '.join(sorted(absent)))
    return ",\n    ".join(parts) + ",\n    " if parts else ""
