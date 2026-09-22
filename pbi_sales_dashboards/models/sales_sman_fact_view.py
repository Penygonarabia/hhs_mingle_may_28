# -*- coding: utf-8 -*-
"""One row per (year, month, part, full 10-level path), carrying sales AND budget
side by side, for the two salesman boards:

    PBI Dashboards > Sales Dashboards > Sales Dashboard With Salesman
    PBI Dashboards > Sales Dashboards > Sales Analysis with Salesman

See docs/sales_salesman_10_levels_data_plan.md for how each level was chosen and
what its coverage is.

HOW CURRENT IT IS
-----------------
The ACTUALS are a snapshot, rebuilt nightly at 02:30 and on demand -- yesterday's
invoices do not change, so recomputing them per request would buy nothing for
16 seconds a page. Two things are NOT left to that clock:

  * the BUDGET, read live through v_pbi_sales_budget_live, so a target typed in
    this morning is on the chart now -- see _build_budget_live_view;
  * the MASTER DATA behind the eleven levels, which is edited by hand during the
    day and decides which bucket a sale falls in. Editing any of it queues the
    refresh cron, so the snapshot follows within a minute or two rather than at
    02:30 -- see _MASTER_DATA_TABLES and _install_master_data_triggers.

WHAT IS IN A ROW
----------------
Eleven levels, each as a code AND a description, so a chart never has to resolve
a caption itself:

    l1   salestypes_group        l6   customer
    l2   partner_classification  l7   main_category     (l7m = manager view)
    l3   res_region              l8   sub_category      (l8m = manager view)
    l4   res_city                l9   product_category depth 2  (product group)
    l5   salesman                lfam product_family    (the PRODUCT SUB-GROUP)

lfam IS THE PRODUCT SUB-GROUP the boards report -- ELITE R410, one bar per
model. product_category's own depth-3 tier splits that into the indoor and
outdoor halves the system ships as, which is a fact about the warehouse rather
than about the market; it was carried as l10 for a while and drew nobody's
chart. Dropping it also turned the sub-group's target from a share of the
product group's into a captured one, because the budget states the family and
never stated the halves. d3 below still resolves the depth-3 category -- that is
where the family link is read -- it is simply not reported as a level.

l1 IS THE DEPARTMENT on these boards -- that is what the word means here. A
customer-side tier was carried above it for a while, the ERP's customer class
type, because the client's own monthly report is cut by that instead; it was
removed because two levels both claiming "department" made the boards and the
business disagree about a shared term. The master survives (partner.class.type)
and nothing here reads it.

plus franchise_code/franchise_label, part_no/part_label, in_scope,
unit_tagged, qty, amount, budget_qty, budget_value and budget_key -- and
budget_l1_code/budget_l1_label, the sale type the BUDGET itself was captured
under, which is not always the one the row sold under. See the column.

Column names deliberately match what the controllers already build their SQL
from -- `qty`, `amount`, and the l<n>_code / l<n>_label pairs in
sales_sman_main.LEVEL_COLUMNS and sales_mail_sman_main.LEVEL_SPEC -- so the
rewire is a change of FROM clause, not a rename of every query.

WHAT COUNTS AS A SALE
--------------------
Midea AC only. A detail line is in scope when

    transaction_details.trnd_group = 'MDA'
    AND transaction_header.trnh_status IN ('C', 'P')
    AND product_category.code, joined by id from transaction_details.trnd_groupid,
        is one of
        ACACC ACCON ACCST ACPAC ACPKG ACAIP ACPOR ACVRF ACWIN ACWTS ACHCL ATOM
    AND transaction_header.trnh_cstno does not start with 'V'

POSTED AND CLOSED DOCUMENTS ONLY -- 'P' posted, 'C' closed, 'N' not posted, and
the column holds nothing else. 'C' and 'N' first appear on 2026-05-03, so this
test is inert for 2024, 2025 and January-April 2026 and only bites in the
current year, where it takes May and June away from what bidata reports. That
divergence is CORRECT and must not be "fixed": bidata carries no status column
at all, its rows were filtered when the feed ran, and the statuses were then
rewritten underneath it -- all 179 'C' and 47 of the 59 'N' May/June headers
were re-written on or after 2026-07-29, after the feed had captured those
months. bidata holds those documents as they stood when they were still posted.
See the block on the clause itself.

The franchise test and the status test are applied when the snapshot is built;
the product and customer tests ride
along as the `in_scope` column, so the debug-only Scope control can still widen
to every MDA line without a rebuild. (Ten of the twelve codes exist on this
database; ACHCL and ATOM match no category today. They are listed because the
scope is the business's, not this view's -- if those groups are ever created
they are in scope without a code change.)

Scoping on the same product_category the budget is captured against
(product_group_id) is what makes the target like-for-like: both sides are keyed
on one taxonomy rather than on two definitions that happen to agree. It also
drops what is not an AC sale -- CSTDISC (-136.7m for 2025), AC promo discount
(-13.5m), installation, service charges, shipping, spares and gift items all
carry their own group codes on trnd_groupid.

Note that l9/l10 still come from the `catalog` chain below, NOT from
trnd_groupid/trnd_subgroupid. The two agree on what is in scope but are resolved
independently; if they are ever reconciled, l9 is the one to move.

VALUE is the net line value, on the ISSUED quantity:

    trnd_qtyiss * (trnd_price - <all discounts> - trnd_cstspldisc)

where <all discounts> is the line discount plus the promotion plus the campaign
plus this line's share of the document's header discount:

    trnd_disc + trnd_promodisc + trnd_campaign
    + CASE WHEN trnh_total > 0
           THEN (trnd_price - trnd_disc - trnd_promodisc - trnd_campaign)
                * trnh_headdisc / trnh_total
           ELSE 0 END

with document type 02 (credit note) taken at trnd_ret and subtracted, and type
01 (invoice) added. QUANTITY uses a different quantity -- see the qty comment in
the sales CTE: it counts only the part carrying Odoo's product.tag '02', so a split
AC counts once rather than twice. The gate is on QUANTITY ONLY. The two measures
are deliberately not in proportion; gating value the same way would drop SAR
330.5m of SAR 601.0m for 2025.

BOTH MEASURES ARE THE ONES "Sales Dashboard - New" AND "Sales Analysis - New"
REPORT. Those boards read v_bidata_live, whose bi_amount is the raw invoiced
quantity times the net price and whose bi_qty is the catalogflags-'02' gate
the unitpart CTE below USED to read. Since 2026-09-03 this side reads the
product.tag mirrored from that same column instead; the two are measured
identical at every year, and the unitpart CTE says what to check first if they
ever stop being. Re-verified in scope on dbprod 2026-09-03, after the two scope
fixes below and after v_bidata_live's own unit gate was made case-insensitive
(scripts/v_bidata_live_case_insensitive_unit_gate.sql):

               units                       value SAR
    year   this table   New boards    this table      New boards
    2024      245,143      245,143   500,945,110     500,945,110
    2025      271,569      271,569   601,004,804     601,004,804
    2026      187,268      142,614   411,852,839     305,991,514

VALUE AND UNITS NOW AGREE TO THE RIYAL AND TO THE UNIT on every month of 2024
and 2025, and on January-June 2026. Two things had to move for that:

  * the cross-franchise groupid guard on in_scope below, worth SAR 1,550 of
    May 2024 -- the last value gap;
  * v_bidata_live's unit gate, which compared the part number case-sensitively
    and so counted 32 units of 2024, 19 of 2025 and 275 of 2026 as zero. THAT
    was the bidata side being short, not this one: this table has upper-cased
    both sides of the join since 2026-09-02.

2026 JULY AND AUGUST HAVE NO bidata TO AGREE WITH, and that is a feed lag
rather than a disagreement. bidata carries SAR 5,115,043 of July and nothing at
all of August, against SAR 44,492,262 and SAR 66,484,106 here; the ERP tables
this table reads are complete for both months. The boards are right and bidata
will catch up. Do not "reconcile" those two months downward.

Budget is the same on both sides at every year (SAR 433,718,765 / 676,460,596 /
717,136,054), once budget_value is de-duplicated per budget_key as below.

The product hierarchy (l7-l10) resolves through the legacy `catalog` table
(cat_grp / cat_pgroup / cat_psgroup -> product_category.code, chained
parent-to-child), NOT through product_template.categ_id. categ_id points at a
depth-1 franchise for 570 of the parts that sell, which left l7/l8/l9 NULL on
40.8 percent of the money and put the franchise name "Midea" on the product
SUB-GROUP chart as its largest bar. Chaining each tier to its parent is
load-bearing: codes repeat across franchise branches (OTH, SPASK, OTH001,
OTHERS, SPAF01), so a join on code alone fans rows out.

CAN `catalog` AND `catalogflags` BE REPLACED BY THE product_* TABLES?
--------------------------------------------------------------------
HALF DONE, as of 2026-09-03. The blocker was never the code -- it was that the
part numbers which started selling in 2026 had never been created as Odoo
products at all. 149 of them were created that day (`sale_ok = False`, named
after the part number, product group from trnd_groupid, 73 tagged '02'), and
that closed one of the two gaps:

  * THE UNIT GATE HAS MOVED. product.tag '02' now reads 245,111 / 271,550 /
    187,217 over these lines -- identical to catalogflags at every year, where
    before the products existed 2026 read 90,311 against 142,614. See the
    unitpart CTE, which is now the tag read.

  * THE HIERARCHY HAS NOT, and l10 is why. Value on parts with no
    product_template fell from SAR 159,202,046 of 2026 to ZERO, and the
    Product Group level is within SAR 14.3m (3.5 pct) -- but SAR 173,454,128
    of 2026, 42 pct, still has no product_sub_group_id. That is NOT a coverage
    gap that creating more rows would close: bidata's sub-group codes and
    product_category's are DIFFERENT CODE SYSTEMS. bidata says WTSG006 and
    WIN011; product_category holds WTS021; WTSG006 exists as no category at
    all, and only 11 of the 150 parts resolved. Moving l9/l10 needs a code
    mapping or the missing categories created -- do not assume the bidata code
    is the category code.

  * THE SCOPE TEST would also lose SAR 21,238 of 2026 if it read the whitelist
    off product_template instead of the chain (2025 is identical either way).

So `catalog` still resolves l7-l10 and the scope, and `catalogflags` is no
longer read by this view at all. The remaining SAR 14.3m at l9 is the DUPLICATE
TEMPLATE problem rather than missing data -- a part number can carry both a
well-formed row and a bare import twin, and DISTINCT ON picks whichever has the
lower id.

THE BUDGET RULE
---------------
v_sales_budget_month is not captured per part, and 60.3 percent of its money
sits on salesman_code = '*'. So budget is NOT joined row-by-row. It is
aggregated to its own real grain first --

    (year, month, partner_classification, region, city, SALESMAN, customer,
     product_group, product_family)

-- and then attached to every part row that shares that tuple. The same budget
figure therefore repeats across the parts of a group, exactly as intended: one
value per part per month.

That list is _BUDGET_CTE_SQL's GROUP BY, and `budget_key` must name every
column in it. Salesman is in it because the budget is captured per salesman
wherever it names one -- the 39.7 pct of the money not sitting on
salesman_code = '*' -- and it was the one grain column the key used to omit.
See _BUDGET_KEY_SQL for what that cost and on which databases it showed.

`budget_key` identifies that tuple. Because the figure repeats, a chart MUST
de-duplicate before it sums -- max() per (chart level, budget_key), then sum:

    SELECT lvl, sum(sales), sum(budget) FROM (
        SELECT <level> AS lvl, budget_key,
               sum(amount) AS sales, max(budget_value) AS budget
        FROM v_pbi_sales_sman_fact
        WHERE <filters>
        GROUP BY 1, 2
    ) t GROUP BY lvl

A plain SUM(budget_value) is wrong at every level and reads several times the
real target.

WHERE THE TARGET IS VALID -- re-measured on 2025 under the scope above, true
budget SAR 676,460,596:

    l1 l2 l3 l4 l6 l7 l8 l9  100.0 pct   exact
    lfam product sub-group   100.0 pct   exact -- the budget states the family
    l5  salesman             110.3 pct   INVALID -- suppress the target
    part                                 INVALID -- suppress the target

(The 280.3 pct that used to sit here was product_category's depth-3
indoor/outdoor tier, reported as l10. The budget never stated it. It is no
longer a level -- the sub-group is the family, which the budget does state.)

The scope change moved the in-scope actuals from SAR 602.9m under the old
catalogflags-'10' rule to SAR 601.0m for 2025, and left this profile exactly
where it was, so BUDGET_UNSAFE_LEVELS in the controllers is unchanged.

Those three are not a defect in this table; the budget genuinely carries no
salesman, no sub-group and no part. Charts at those levels must show This Year
vs Last Year only.

MATERIALISED, NOT LIVE
----------------------
Building the rows is expensive and VARIES WILDLY with cache state: the MDA
detail lines aggregated across fifteen joins, over tables the planner has no
statistics for. Measured on dbprod it has run in under 2 minutes warm, 15
minutes cold with the hash spilling to disk, and 26 minutes once the part-number
joins were normalised with upper() -- a function on a join key cannot use an
index and forces the hash onto a computed value. Budget for the worst case. The boards fire roughly 32
queries per page load, so a plain view would be unusable. As a materialised view
with the indexes below, those queries are index scans over pre-built rows.

Note that the plain build takes an ACCESS EXCLUSIVE lock for its whole run --
init() does DROP then CREATE -- so the dashboards BLOCK while it happens. Only
the CONCURRENTLY refresh below keeps them serving.

Refresh after the legacy ERP feed lands -- data/pbi_sales_sman_fact_cron.xml
runs it nightly, or call it directly:

    env['pbi.sales.sman.fact'].refresh_fact()

REFRESH ... CONCURRENTLY needs the unique index on id and holds no read lock,
so the dashboards keep serving the previous snapshot while it rebuilds. It is
much slower than the plain build -- about 3 minutes on dbprod, because it builds
a fresh copy and then DIFFS it against the live one row by row -- which is the
price of not locking readers out. Fine for a nightly cron; do not put it on a
request path.
"""

import logging

from datetime import timedelta

from odoo import api, fields, models

from odoo.addons.pbi_dashboards.controllers import board_sql, optional_schema

_logger = logging.getLogger(__name__)


# THE BUDGET HALF OF THE FACT, WRITTEN ONCE AND USED TWICE.
#
# Once inside the snapshot below, where it meets the actuals through a FULL
# OUTER JOIN; and once as v_pbi_sales_budget_live, the plain view the boards
# read their TARGET from so that a budget entered a minute ago is on the chart
# now rather than after the 02:30 refresh. Shared text, because two copies of
# this would be two answers to "what is the target" and only one of them would
# be right.
#
# {group_whitelist} is the sole difference between the two uses. The clause
# scopes the budget to the product groups that HAVE in-scope sales; inside the
# snapshot that reads the `sales` CTE being built alongside it, and in the live
# view -- where no such CTE exists, and where re-deriving it would drag the
# whole expensive actuals query along -- it reads the same set back off the
# finished snapshot. Sales do not change between refreshes either, so the two
# whitelists agree.
# The product groups whose categories all resolve to ONE family, so a budget row
# in them that names no family can only belong to that one. Resolved THROUGH the
# merge link, which is what makes VRF and Cassette single-family groups at all --
# see scripts/merge_duplicate_product_families.sql.
_SINGLE_FAMILY_GROUP_SQL = """
            SELECT c.parent_id AS group_id,
                   min(COALESCE(gfm.pfam_merged_into, gf.id)) AS fam
              FROM product_category c
              JOIN product_family gf  ON gf.id  = {pcat_family_col_c}
              LEFT JOIN product_family gfm ON gfm.id = gf.id
             GROUP BY c.parent_id
            HAVING count(DISTINCT COALESCE(gfm.pfam_merged_into, gf.id)) = 1
"""

# THE BUDGET TUPLE'S IDENTITY. Built here once and used by BOTH the snapshot
# and v_pbi_sales_budget_live, which used to spell it out separately and are
# required to agree character for character -- the two-stage max() de-duplication
# every budget query runs is grouped on it, so a difference silently stops
# collapsing repeats.
#
# IT MUST CARRY EVERY COLUMN _BUDGET_CTE_SQL GROUPS BY, AND IT DID NOT.
# That CTE's grain is the nine columns of its GROUP BY -- yr, mth, l2, l3, l4,
# l5, l6, l9, lfam -- while this key named only eight of them: l5, the budget's
# own salesman, was missing. A key COARSER than the grain does not merge those
# rows, it discards them. Two budget rows differing only by salesman shared one
# key, and max(budget_value) over that key kept the larger and threw the rest of
# the target away.
#
# It is invisible wherever the budget carries no salesman -- every row gets a
# NULL l5, one row per key, nothing to collapse -- which is why a database whose
# v_sales_budget_month has no salesman_partner_id (or an unpopulated one) reads
# the target correctly while a database that HAS the attribution reads it low.
# staging-hhsv3 was short SAR 21.3m of the 2025 YTD target to September, and
# SAR 7.2m of September itself, against the same budget file locally.
#
# Alias `b` at both sites: the snapshot's budget CTE and the live view's
# `FROM budget b` both bind it.
_BUDGET_KEY_SQL = (
    "b.yr::text||'-'||lpad(b.mth::text,2,'0')||'|'||"
    "COALESCE(b.l2_code::text,'')||'|'||COALESCE(b.l3_code::text,'')||'|'||"
    "COALESCE(b.l4_code::text,'')||'|'||COALESCE(b.l5_code::text,'')||'|'||"
    "COALESCE(b.l6_code,'')||'|'||COALESCE(b.l9_code::text,'')||'|'||"
    "COALESCE(b.lfam_code::text,'')"
)

_BUDGET_CTE_SQL = """        SELECT b.year AS yr, b.month AS mth,
               bpcl.id                     AS l2_code,
               brreg.id                    AS l3_code,
               b.city_id                   AS l4_code,
               {budget_salesman}           AS l5_code,
               trim(b.customer_code)       AS l6_code,
               b.product_group_id          AS l9_code,
               -- THE FAMILY IS PART OF THE BUDGET'S OWN GRAIN, not a share of
               -- the product group's. The file states it -- erp_subgroup_code
               -- is WTSG006 for ELITE R410 -- in the same code system
               -- product_family.pfam_ref uses, so it resolves directly and the
               -- Family level carries a CAPTURED target rather than an
               -- allocated one. It reaches 98.2 pct of the 2025 budget value.
               -- A row whose code names no family (the '*' sentinel, and the
               -- 1.8 pct that match nothing) yields NULL and reports under a
               -- blank family, which is what it is.
               COALESCE({fam_merged_bfam}, bfam.id, bgf.fam) AS lfam_code,
               max(bsg.id)                 AS l1_code,
               max(COALESCE(bmc.id, bpmc.id)) AS l7_code,
               max(COALESCE(bsc.id, bpsc.id)) AS l8_code,
               max(COALESCE(bpmcm.id, bpmc.id, bmc.id)) AS l7m_code,
               max(COALESCE(bscm.id, bpscm.id, bsc.id, bpsc.id)) AS l8m_code,
               max(b.franchise_code)        AS franchise_code,
               sum(b.budget_qty)            AS budget_qty,
               sum(b.budget_amount)         AS budget_value
        FROM v_sales_budget_month b
        LEFT JOIN partner_classification bpcl ON bpcl.pc_code     = b.partner_classification_code
        LEFT JOIN res_region             brreg ON brreg.code      = b.region_code
        LEFT JOIN product_family         bfam ON bfam.pfam_ref    = btrim({budget_erp_subgroup})
        -- FALLBACK FOR A BUDGET ROW THAT NAMES NO FAMILY.
        --
        -- The file's sub-group code is sometimes the ERP's '*' sentinel -- "not
        -- applicable", a real value rather than missing data. Where the product
        -- group it sits in has exactly ONE family, that row belongs to that
        -- family and nowhere else, so saying so is not a guess.
        --
        -- It is worth SAR 8,762,546 of the 2025 VRF target, which is the whole
        -- of the unresolved budget on this database. Without it VRF read 16.7m
        -- of sales against 10.6m of target while the rest of its own target sat
        -- on a nameless bar beside it.
        --
        -- Deliberately NOT applied where a group carries more than one family:
        -- there the sentinel means the budget really was captured across them,
        -- and picking one would move money onto a bar nobody budgeted it for.
        LEFT JOIN ({single_family_group}) bgf ON bgf.group_id = b.product_group_id
        LEFT JOIN salestypes_group       bsg  ON bsg.salgrp_ref   = b.salestype_group_code
        LEFT JOIN main_category          bmc  ON bmc.maincat_ref  = b.main_category_code
        LEFT JOIN sub_category           bsc  ON bsc.subcat_ref   = b.sub_category_code
        LEFT JOIN sub_category           bscm ON bscm.subcat_ref  = b.merged_subcategory_code
        LEFT JOIN product_category       bpc  ON bpc.id           = b.product_group_id
        LEFT JOIN sub_category           bpsc ON bpsc.id          = {pcat_sub_bpc}
        LEFT JOIN main_category          bpmc ON bpmc.id          = bpsc.subcat_maincategory_id
        LEFT JOIN sub_category           bpscm ON bpscm.id        = COALESCE({pcat_merged_bpc}, {pcat_sub_bpc})
        LEFT JOIN main_category          bpmcm ON bpmcm.id        = bpscm.subcat_maincategory_id
        -- Same population on both sides of every achievement percentage.
        --
        -- The board's scope cannot be applied to the budget directly: the
        -- budget was never captured per part (89 pct of its rows carry
        -- part_no = '*'), so it has no product to look a group_code up on.
        --
        -- It does not need to be, and this clause is what keeps that true. The
        -- budget only ever covers the eight AC product groups, and the scope
        -- is itself defined on the product group -- so scoping the budget to
        -- the groups that have in-scope sales makes the two populations the
        -- same by construction, not by coincidence. The one part of the scope
        -- that is not group-shaped, the 'V' customer exclusion, cannot pull
        -- them apart either: the budget carries no 'V' customer at all (0 of
        -- 30,502 rows for 2025), while on the actuals side those customers are
        -- 73 lines and SAR 3.6m -- so the exclusion removes from the actuals
        -- exactly what was never in the target.
        --
        -- Today this drops nothing: all 8 budgeted groups have in-scope sales.
        -- It is here so that if the scope ever narrows, the target narrows
        -- with it instead of the two sides quietly drifting apart.
        WHERE b.product_group_id IN ({group_whitelist})
        GROUP BY 1,2,3,4,5,6,7,8,9"""

# What the live view borrows from the snapshot rather than computing.
#
# For a budget tuple that rides a sales row, the snapshot takes l7m/l8m from
# THAT ROW, not from the budget -- and the budget's own merged sub-category
# disagrees on 2,239 of 8,181 tuples carrying SAR 505,889,540 (measured on
# dbprod 2026-08-29). "Sales Analysis with Salesman" in Manager sub-mode groups
# its target by exactly those columns, so computing them here from the budget
# would move three quarters of the annual target between bars as a side effect
# of a refresh-timing change. They are read back off the snapshot instead,
# keyed by budget_key, which is indexed.
#
# l7/l8 need no such care: measured the same day, the budget's own main and sub
# category agree with the sales row's on all 8,181 tuples. They are still taken
# from the snapshot for the same reason -- so that every level this view reports
# a target at is the level the snapshot would have reported.
#
# If the snapshot has no matching sales row, the live view falls back to the
# budget tuple's own resolved categories (kmc/ksc/kmcm/kscm).
_BUDGET_SNAPSHOT_LEVELS_SQL = """
    LEFT JOIN main_category          kmc  ON kmc.id  = k.l7_code
    LEFT JOIN sub_category           ksc  ON ksc.id  = k.l8_code
    LEFT JOIN main_category          kmcm ON kmcm.id = k.l7m_code
    LEFT JOIN sub_category           kscm ON kscm.id = k.l8m_code
    LEFT JOIN v_pbi_sales_budget_snap snap ON snap.budget_key = k.budget_key
"""


class PbiSalesSmanFact(models.Model):
    _name = 'pbi.sales.sman.fact'
    _description = 'PBI Sales (Salesman) - 10-level fact with sales and budget'
    _table = 'v_pbi_sales_sman_fact'
    _auto = False
    _order = 'id'

    # Planner settings this build needs, applied for the duration of the
    # transaction that runs it. SET LOCAL reverts at commit and changes nothing
    # database-wide.
    #
    # NOT optional. This view joins the same legacy master tables v_bidata_live
    # joins, and needs the same settings they do (see _planner_hints on
    # PbiSalesKpiLiveSourceMixin in controllers/sales_kpi_main.py). Without
    # them the CREATE below picks a nested-loop plan and effectively does not
    # finish: on dbprod 2026-08-27 it was still burning CPU after 16 MINUTES
    # and had to be cancelled, against 16 SECONDS with these two lines in
    # place. That made every `-u pbi_sales_dashboards` unrunnable, since a
    # module upgrade re-runs init(). The unique indexes added to those master
    # tables that same day are what tipped the planner into the bad plan -- the
    # same trap documented on PbiSalesKpiLiveSourceMixin, where indexes made
    # the hint MORE necessary, not less.
    _PLANNER_HINTS = ("SET LOCAL jit = off", "SET LOCAL enable_nestloop = off")

    # THE LABEL TABLES THIS VIEW READS AND NO MODULE HERE OWNS.
    #
    # This suite declares no dependency on the modules that own them -- see
    # pbi_dashboards/controllers/optional_schema.py for why -- so each is
    # probed and, where absent, stood in for by an empty CTE of the same
    # shape. Every join onto them below is a LEFT JOIN feeding an l<n>_label
    # or the budget columns; none filters a sales row and none carries qty or
    # amount, so an absent module blanks captions and leaves every figure on
    # the sales side exactly where it was.
    #
    # Listed per table are only the columns this view actually reads, with the
    # types they carry on dbprod (2026-08-29). Add a column here the moment
    # the SQL below starts reading it, or the stand-in will be a column short.
    _OPTIONAL_TABLES = {
        # dashboard_groups
        'salestypes_group': (('id', 'integer'), ('salgrp_ref', 'varchar'),
                             ('salgrp_name', 'varchar')),
        'main_category': (('id', 'integer'), ('maincat_name', 'varchar'),
                          ('maincat_ref', 'varchar')),
        'sub_category': (('id', 'integer'), ('subcat_name', 'varchar'),
                         ('subcat_ref', 'varchar'),
                         ('subcat_maincategory_id', 'integer')),
        'sale_types': (('id', 'integer'), ('sal_ref', 'varchar'),
                       ('saltype_group', 'integer')),
        # whichever module declares res.region on the target server
        'res_region': (('id', 'integer'), ('code', 'varchar'), ('name', 'text')),
        # partner_classification
        'partner_classification': (('id', 'integer'), ('pc_code', 'varchar'),
                                   ('complete_name', 'varchar'),
                                   ('pc_classification1', 'varchar')),
        # dashboard_groups again -- lfam's own master. Its link lives on
        # product_category and is read through optional_schema.column_ref
        # below, for the same reason partner_classification's department link
        # is: the TABLE can be absent, and so can the COLUMN, on a server
        # carrying an older dashboard_groups than the one that added the tier.
        'product_family': (('id', 'integer'), ('pfam_ref', 'varchar'),
                           ('pfam_name', 'varchar'),
                           ('pfam_merged_into', 'integer')),
        # base_address_extended -- core Odoo, but not installed everywhere
        'res_city': (('id', 'integer'), ('name', 'text'),
                     ('report_region', 'integer'), ('code', 'varchar')),
        # sales_budget. An empty budget meets the sales side through a FULL
        # OUTER JOIN, so the boards keep every sales row and simply show no
        # target -- which is what a month with no budget captured already
        # looks like.
        'v_sales_budget_month': (
            ('year', 'integer'), ('month', 'integer'), ('city_id', 'integer'),
            ('customer_code', 'varchar'), ('product_group_id', 'integer'),
            ('franchise_code', 'varchar'),
            ('salestype_group_code', 'varchar'),
            ('partner_classification_code', 'varchar'),
            ('region_code', 'varchar'), ('main_category_code', 'varchar'),
            ('sub_category_code', 'varchar'),
            ('merged_subcategory_code', 'varchar'),
            ('erp_subgroup_code', 'varchar'),
            ('budget_qty', 'numeric'), ('budget_amount', 'numeric'),
        ),
    }

    # THE MASTER DATA THAT DECIDES WHICH BUCKET A SALE FALLS IN.
    #
    # A snapshot is only as current as its last refresh, and until this was
    # here that meant 02:30. Yesterday's invoices do not change overnight, so
    # snapshotting the ACTUALS is right -- but the master data that says which
    # bucket an invoice lands in is edited by hand, during the day, and the
    # edit was not on a chart until the following morning. Found the hard way
    # on dbprod (2026-09-02): sale types were re-pointed at their sales type
    # groups at 08:38, and the Sales Type Group chart still had 65,929 rows /
    # SAR 1.23bn under "Others" that the live master data now calls "Dealers".
    #
    # Worse than merely stale, it was INCONSISTENT: the target half of these
    # boards is read live (v_pbi_sales_budget_live), so a group renamed today
    # captioned the budget bar one way and the actuals bar beside it another.
    #
    # So each of these tables carries a statement trigger that queues the
    # refresh cron -- see _install_master_data_triggers. Between the queue and
    # the cron thread's poll the delay is under two minutes; nothing here has
    # to be refreshed by hand and nothing waits for 02:30.
    #
    # A POSTGRES TRIGGER rather than an Odoo write() override, for two
    # reasons. Every one of these tables belongs to a module this suite
    # deliberately does not depend on (see the manifest), so there is no model
    # here to override and no load order that would make one reliable. And the
    # tables are written by more than the ORM -- imports, migrations and the
    # ERP feed all reach them in SQL, where a Python hook never fires.
    #
    # WHAT IS AND IS NOT LISTED. These eight are the CONFIGURATION behind the
    # levels: small tables, edited by an administrator, cheap to react to. The
    # feed-side sources of l5 and l6 -- customer, customerdesc, sl_salesmandesc,
    # res_partner -- are not here on purpose: they are bulk-loaded, some of
    # them hot, and a refresh costs ~16s of database CPU, so reacting to every
    # write would have the snapshot rebuilding continuously. Those land with
    # the feed, and the feed lands before the nightly cron.
    _MASTER_DATA_TABLES = (
        'salestypes_group',        # l1
        'sale_types',              # l1  (saltype_group is what moved above)
        'partner_classification',  # l2
        'res_region',              # l3
        'res_city',                # l4, and report_region feeds l3
        'main_category',           # l7
        'sub_category',            # l7 via subcat_maincategory_id, l8
        'product_family',          # lfam
        'product_category',        # l9, lfam via product_family, the l7/l8
                                   # link, and in_scope
        # l1 on the SALES side too, since the `ka` CTE reads the budget's own
        # classification -> group assignment back out of it. Re-classify a
        # partner classification in the budget and the actuals follow on the
        # next rebuild rather than at 02:30.
        'sales_budget_line',       # l1 via ka (v_sales_budget_month reads it)
    )

    # The floor between two rebuilds. An edit made while a refresh is already
    # queued rides on that one; an edit made just after a refresh ran waits
    # this long, so re-pointing twenty sale types one after another costs one
    # rebuild rather than twenty. Nothing is dropped -- the wait is on the
    # queued time, not on whether the edit is noticed.
    _STALE_REBUILD_FLOOR = '60 seconds'

    def _apply_planner_hints(self):
        for hint in self._PLANNER_HINTS:
            self._cr.execute(hint)

    # ----------------------------------------------------- the rebuild lock
    # One advisory key, shared by everything that rewrites or repopulates this
    # snapshot: init(), refresh_fact(), and the config page's bring-up
    # pipeline (pbi_dashboard_configurations/controllers/bring_up.py, which
    # cannot import this class -- it does not depend on this module -- and
    # repeats the literal instead). CHANGE IT IN BOTH PLACES OR NEITHER.
    #
    # WHY IT EXISTS. These two parties take ACCESS EXCLUSIVE locks in opposite
    # orders and deadlock. The bring-up's step 2 does DDL on the master tables
    # (ALTER TABLE product_category ADD COLUMN product_family, ALTER TABLE
    # res_partner, CREATE TABLE product_family), then reads the snapshot; a
    # refresh holds the snapshot and then reads the master tables. Worse, the
    # bring-up SUMMONS its own opponent: product_category and product_family
    # are both in _MASTER_DATA_TABLES, so step 2's own writes fire the stale
    # triggers, queue this cron, and the cron thread wakes inside step 2's
    # transaction -- which is why a server with cron threads deadlocks here
    # while a dev box with --max-cron-threads=0 never does, and why the same
    # step runs clean locally and dies on staging.
    #
    # A lock_timeout cannot fix that: both sides are already waiting when
    # Postgres notices, and it kills one of them. Ordering can. Both parties
    # take THIS lock before their first relation lock, so there is a single
    # global order and no cycle to detect.
    _REBUILD_LOCK_KEY = 7420110

    def _take_rebuild_lock(self):
        """Block until nothing else is rebuilding the snapshot.

        Transaction-scoped, so it is released by COMMIT or ROLLBACK and cannot
        be leaked by a worker that dies holding it. Note that a rollback
        releases it -- refresh_fact's fallback path re-takes it for that
        reason, and anything acquiring it inside a SAVEPOINT loses it when that
        savepoint aborts.
        """
        self._cr.execute("SELECT pg_advisory_xact_lock(%s)",
                         (self._REBUILD_LOCK_KEY,))

    def _try_rebuild_lock(self):
        """Take the rebuild lock if it is free. True if this transaction has
        it; False if somebody else is rebuilding right now."""
        self._cr.execute("SELECT pg_try_advisory_xact_lock(%s)",
                         (self._REBUILD_LOCK_KEY,))
        return self._cr.fetchone()[0]

    def init(self):
        cr = self._cr
        # BUILT ONLY WHERE THE ERP FEED IS. This reads legacy tables loaded
        # into the database from outside Odoo (transaction_header/details, catalog, catalogflags, customer) -- no module creates
        # them, so no dependency can express this. Where they are absent the
        # view is left unbuilt: Odoo tolerates an _auto=False model with no
        # table, says so in the log and carries on. Before this, a from-scratch
        # install of the pbi stack died here (2026-08-28).
        self._cr.execute("SELECT to_regclass('transaction_header')")
        if not self._cr.fetchone()[0]:
            return
        # Ahead of the first DDL, so a refresh already in flight finishes
        # before the DROP below starts rather than deadlocking against it.
        self._take_rebuild_lock()
        # AND ONLY WHERE THE PRODUCT SPINE IS. product_category.code is the
        # one foreign column this view cannot do without: the catalog chain
        # d1/d2/d3 is keyed on it, and it decides in_scope -- which the boards
        # filter on. A stand-in would not blank a caption, it would report
        # every row out of scope and every total as zero, and a board of
        # confident zeroes is worse than a board that says it is not built.
        # So this one is a precondition, not an optional label.
        if not optional_schema.has_column(cr, 'product_category', 'code'):
            _logger.info(
                "pbi.sales.sman.fact: product_category.code is absent, so the "
                "product hierarchy this view is keyed on cannot be resolved; "
                "leaving v_pbi_sales_sman_fact unbuilt. The salesman boards "
                "need it; the other sales boards do not and are unaffected.")
            return
        stubs = optional_schema.stub_ctes(cr, self._OPTIONAL_TABLES)
        # dashboard_groups' two columns on product.category, and
        # machine_repair_management's on res.city, are labels: a typed NULL
        # blanks the Main/Sub Category and Region captions and nothing else.
        pcat_sub = optional_schema.column_ref(
            cr, 'product_category', 'sub_category', 'integer')
        pcat_merged = optional_schema.column_ref(
            cr, 'product_category', 'merged_subcategory', 'integer')
        # lfam's link, on the depth-3 category. A typed NULL leaves every row
        # under a blank family -- the same degradation an absent master gets.
        pcat_family = optional_schema.column_ref(
            cr, 'product_category', 'product_family', 'integer', alias='d3')
        # The same column read INSIDE the d3 CTE, where product_category is the
        # only table in scope and carries no alias.
        pcat_family_col = optional_schema.column_ref(
            cr, 'product_category', 'product_family', 'integer')
        pcat_family_col_pc = optional_schema.column_ref(
            cr, 'product_category', 'product_family', 'integer', alias='pc')
        single_family_group = _SINGLE_FAMILY_GROUP_SQL.format(
            pcat_family_col_c=optional_schema.column_ref(
                cr, 'product_category', 'product_family', 'integer', alias='c'))
        # "Report under another family". Absent on a server carrying an older
        # dashboard_groups, where every family simply reports under itself.
        fam_merged_dfam = optional_schema.column_ref(
            cr, 'product_family', 'pfam_merged_into', 'integer', alias='dfam')
        fam_merged_bfam = optional_schema.column_ref(
            cr, 'product_family', 'pfam_merged_into', 'integer', alias='bfam')
        # The budget file's own sub-group code, which names the family. On a
        # server whose sales_budget predates it the reference becomes a typed
        # NULL and every budget row reports under a blank family -- the level
        # still draws, it just carries no captured target.
        budget_erp_subgroup = optional_schema.column_ref(
            cr, 'v_sales_budget_month', 'erp_subgroup_code', 'varchar', alias='b')
        city_report_region = optional_schema.column_ref(
            cr, 'res_city', 'report_region', 'integer', alias='city')
        city_code = optional_schema.column_ref(
            cr, 'res_city', 'code', 'varchar', alias='city')
        # The customer master's own city code, which is what fills the region
        # in when the invoice header carries neither -- see the cust_city CTE.
        cust_subregion = optional_schema.column_ref(
            cr, 'customer', 'cst_subregion', 'varchar', alias='c')
        # salesman_res_partner's flag. Without it no partner is a salesman, so
        # the join is closed off rather than left to match any partner and
        # caption a line with the wrong person's name -- l5_label then falls
        # through to the ERP feed's own salesman name, which is the same text.
        sp_salesman_test = (
            'AND sp.is_salesman'
            if optional_schema.has_column(cr, 'res_partner', 'is_salesman')
            else 'AND false')
        self._apply_planner_hints()
        # The live budget view reads this matview, so it has to go first:
        # Odoo calls init() more than once while it builds the registry, and
        # on the second pass the DROP below fails with "cannot drop ...
        # because other objects depend on it" -- which aborts the whole
        # upgrade. Explicitly, not with CASCADE: CASCADE would also take out
        # anything else someone has built on the snapshot, which is not this
        # method's call to make.
        cr.execute("DROP VIEW IF EXISTS v_pbi_sales_budget_live")
        cr.execute("DROP MATERIALIZED VIEW IF EXISTS v_pbi_sales_budget_snap")
        cr.execute("DROP MATERIALIZED VIEW IF EXISTS v_pbi_sales_scope_groups")
        cr.execute("DROP MATERIALIZED VIEW IF EXISTS v_pbi_sales_sman_fact")
        # No params are passed to this execute(), so psycopg2 does NOT run
        # %-interpolation over the string and the literal % in NOT LIKE 'V%'
        # below is safe. Never copy that clause into a controller query that
        # does pass params -- there it would have to be written %%.
        #
        # .format() only fills the two label expressions named below (the SQL
        # carries no other braces); it is not %-interpolation and leaves the
        # literal % alone.
        cr.execute("""
            CREATE MATERIALIZED VIEW v_pbi_sales_sman_fact AS
    WITH {stubs}unitpart AS MATERIALIZED (
        -- THE UNIT-BEARING PART, read from Odoo's own product.tag '02'.
        --
        -- A split air conditioner ships as two parts on one invoice; only one
        -- of them bears the unit. See the qty note in the sales CTE for what
        -- that means and why quantity is gated on this while value is not.
        --
        -- MOVED OFF catalogflags ON 2026-09-03, and it took a data fix to make
        -- that possible rather than a code one. The tag is mirrored from
        -- catalogflags by part number, so it only ever reached a part that HAS
        -- a product_template -- 1,018 part numbers against catalogflags' 1,127.
        -- The 109 it missed were the parts that started selling in 2026, and
        -- reading the tag then cost 2026 37 pct of its units (90,311 against
        -- 142,614) while leaving 2024 and 2025 untouched: a loss falling
        -- entirely on the current year, deflating the boards' units against a
        -- target that is not deflated with them. That is why this CTE read the
        -- legacy table for a year, and why a previous attempt to switch was
        -- reverted.
        --
        -- Those products now exist: 149 templates created 2026-09-03 for the
        -- parts selling in 2026 that had none, 73 of them tagged '02'. Measured
        -- the same day over the MDA lines this view aggregates, the two gates
        -- are IDENTICAL at every year:
        --
        --     2024   245,111 = 245,111
        --     2025   271,550 = 271,550
        --     2026   187,217 = 187,217
        --
        -- and across every part that sells on MDA the sets differ on nine
        -- part numbers (FCU-*, AHU-*) which carry ZERO in-scope units and zero
        -- value -- they are flagged in catalogflags, have no template, and
        -- appear nowhere in this table's in-scope population.
        --
        -- KEYED ON THE PART ALONE, where the catalogflags read was keyed on
        -- (group, stock, part). Both dropped components were inert here and the
        -- tag has neither:
        --
        --   * stock is a constant wildcard -- trnd_stock has exactly ONE
        --     distinct value across every MDA line and cat_stock exactly one
        --     across every '02' row, both '*';
        --   * the group is already fixed by the query -- this view is MDA-only
        --     (see the WHERE on the sales CTE), so a franchise column could
        --     only ever match itself. Measured: no part tagged '02' under
        --     another franchise sells on MDA at all.
        --
        -- WHAT TO WATCH. v_bidata_live still gates on catalogflags keyed on
        -- (franchise, part, stock), so the two sides now read DIFFERENT
        -- sources for the same measure. They agree today, to the unit, at every
        -- year. They stay agreeing only while the tag mirrors the flag -- so if
        -- the boards and bidata ever disagree on QUANTITY again, compare the
        -- two part sets first (the query above), before looking anywhere else.
        --
        -- product.tag is core Odoo, from the `product` module -- the same
        -- module that owns product_category, which the d1/d2/d3 CTEs below
        -- already read unconditionally. So it is NOT stubbed through
        -- _OPTIONAL_TABLES, and deliberately: an empty stub here would not
        -- blank a caption, it would silently zero EVERY quantity on every
        -- board. Failing loudly on a database without `product` is the better
        -- of the two.
        --
        -- The tag name is read shape-agnostically. product_tag.name is a
        -- translated column, which is jsonb on this database and varchar on a
        -- server where the owning module was upgraded at a different time; a
        -- literal name->>'en_US' dies with "operator does not exist" on the
        -- second kind. Same rule, same expression as board_sql's label reads.
        -- Trimmed and compared as text, because '02' is a code rather than a
        -- translation -- it is the same string in every language.
        --
        -- DISTINCT is load-bearing now, where it was defensive before: a part
        -- number may carry MORE THAN ONE product_template on this database
        -- (a well-formed row and a bare import twin), and both can be tagged.
        -- Without it a duplicate would multiply the detail line rather than
        -- merely flag it.
        --
        -- upper() on the part, here and on every other side of a part-number
        -- join in this view -- see the `cat` CTE. The part number is the ONE
        -- key on this database that is not reliably upper-cased: 21 part
        -- numbers appear in transaction_details in more than one casing.
        SELECT DISTINCT upper(trim(cat_part)) AS part
        FROM catalogflags
        WHERE trim(cat_flag) = '02'
          AND NULLIF(trim(cat_part), '') IS NOT NULL
        UNION
        SELECT DISTINCT upper(trim(t.default_code)) AS part
        FROM product_template t
        JOIN product_tag_product_template_rel r ON r.product_template_id = t.id
        JOIN product_tag g ON g.id = r.product_tag_id
        WHERE trim({tag_name}) = '02'
          AND NULLIF(trim(t.default_code), '') IS NOT NULL
    ),
    cat AS (
        -- MATCHED CASE-INSENSITIVELY, and that is load-bearing. 21 part numbers
        -- appear in transaction_details in more than one casing -- the ERP
        -- takes them as typed -- while `catalog` and `catalogflags` hold each
        -- exactly once. A case-sensitive join therefore drops the odd-cased
        -- line out of the taxonomy AND out of the unit gate, and since those
        -- lines also tend to carry no trnd_groupid they fall out of scope
        -- entirely rather than landing in the wrong bucket.
        --
        -- Measured: it cost February 2026 fifty-one units and SAR 21,666
        -- (MSTS12CRNAG15-NP-f and MSTS12CRNAG15-f, against the -F rows the
        -- catalog holds) and January SAR 1,430 (fqzhw-02n1g vs FQZHW-02N1G).
        -- Both months now reconcile on the parts that HAVE a catalog row.
        --
        -- Safe to normalise: neither catalog nor catalogflags has a single part
        -- number appearing in two casings, so upper() cannot make two rows
        -- where there was one. Nothing else needs it -- group codes, category
        -- codes and customer numbers are all uniformly upper case already.
        --
        -- KEYED ON (FRANCHISE, PART), NOT ON THE PART ALONE, and the join below
        -- carries the franchise too. A part number is unique WITHIN a franchise
        -- branch of the catalog and not across it: TH1152 is catalogued twice,
        -- once as RUD/ACC ("RUUD - 2 STAGE THERMOSTAT") and once as MDA/ACACC
        -- ("THERMOSTAT (WIFI)"). Keyed on the part alone, DISTINCT ON kept
        -- whichever row had the lower id -- the RUD one -- so an MDA sale of it
        -- resolved to the RUUD accessories group, which is not in the AC
        -- whitelist, and the line fell OUT OF SCOPE altogether. That is
        -- SAR 1,550 of May 2024, and it was the last value gap between these
        -- boards and v_bidata_live for 2024, 2025 and 2026-to-June: bidata
        -- carries the franchise on the row (bi_franchisecode) and never had the
        -- ambiguity to resolve.
        --
        -- Two part numbers are catalogued under more than one franchise today
        -- and one of them sells on MDA, so the fix is worth exactly SAR 1,550 --
        -- but the shape of it is what matters: every other key in this view is
        -- already franchise-qualified (see unitpart, and see the d1/d2/d3
        -- parent-to-child chaining, which exists for the same reason), and this
        -- was the one place a code was trusted on its own.
        SELECT DISTINCT ON (upper(trim(cat_grp)), upper(trim(cat_part)))
               upper(trim(cat_grp)) AS grp, upper(trim(cat_part)) AS part,
               trim(cat_grp) AS fr, trim(cat_pgroup) AS pg, trim(cat_psgroup) AS psg,
               cat_desc AS descr
        FROM catalog ORDER BY 1, 2, id
    ),
    tmplgrp AS (
        -- THIRD AND LAST ANSWER for a line's product group, behind
        -- trnd_groupid and the `catalog` chain: the part's own Odoo product
        -- category. It fires only where BOTH of those are silent.
        --
        -- Why it is needed. `catalog` is an external feed and it is not
        -- complete: MSTE12CRN1AG2KSA-NP-F sells, is flagged '02', carries a
        -- product_template categorised Midea/ACWTSplit -- and has no catalog
        -- row at all. That costs nothing on a line whose trnd_groupid is set,
        -- because the groupid answers first. But IN20141789 line 1 carries the
        -- part typed in lower case AND no trnd_groupid (the two travel
        -- together -- see the `cat` CTE), so both existing answers were NULL,
        -- the line fell out of scope, and August 2026 read 3 units short of
        -- v_bidata_live -- which classifies from bi_pgroupcode stored on its
        -- own row and never had to resolve anything.
        --
        -- Measured over 2024-2026 before it was added: it brings exactly ONE
        -- line and 3 units into scope, all in 2026, and takes NOTHING out.
        -- 2024 and 2025 are untouched to the unit.
        --
        -- FRANCHISE-CHECKED at the join, like trnd_groupid and like `cat`:
        -- product_category codes repeat across franchise branches, so the
        -- category is believed only when its parent IS the branch the line
        -- sold under. Depth 2 only -- that is the product-group tier, the same
        -- tier d2 reads.
        --
        -- DISTINCT ON because a part number may carry more than one
        -- product_template on this database (a well-formed row and a bare
        -- import twin); lowest id wins, deterministically.
        --
        -- It deliberately supplies the SCOPE only, not l9/l10. Those come from
        -- d2/d3 and stay NULL here, which leaves this part where its own other
        -- lines already sit -- product group "Unassigned" -- rather than
        -- attributing one line differently from the other 28 of the same part
        -- in the same month. The real fix for the attribution is the missing
        -- catalog row upstream, and it is worth 1,848 units of 2026.
        SELECT DISTINCT ON (upper(trim(t.default_code)))
               upper(trim(t.default_code)) AS part,
               trim(pc.code) AS pg, trim(pf.code) AS fr
        FROM product_template t
        JOIN product_category pc ON pc.id = t.categ_id
        JOIN product_category pf ON pf.id = pc.parent_id
        WHERE NULLIF(trim(t.default_code), '') IS NOT NULL
          AND (length(pc.parent_path)-length(replace(pc.parent_path,'/','')))=2
        ORDER BY 1, t.id
    ),
    d1 AS (SELECT DISTINCT ON (trim(code)) id, trim(code) AS code, name
           FROM product_category
           WHERE (length(parent_path)-length(replace(parent_path,'/','')))=1
             AND NULLIF(trim(code),'') IS NOT NULL ORDER BY trim(code), id),
    d2 AS (SELECT DISTINCT ON (parent_id, trim(code)) id, parent_id, trim(code) AS code,
                  name, {pcat_sub} AS sub_category,
                  -- IDENTITY FALLBACK, and the Manager view does not work
                  -- without it.
                  --
                  -- product_category.merged_subcategory means "Manager view.
                  -- Leave empty to fall back to the Sub Category" -- its own
                  -- help text, and what sales_budget_line._build_category_map
                  -- has always implemented on the budget side
                  -- (`merged = walk(cid, 'merged') or sub`). Reading the column
                  -- raw here did not implement it, and the column is empty on
                  -- all 240 categories, so every SALE got a NULL l8m: Manager
                  -- sub-mode put the whole year's actuals on "Unassigned"
                  -- while the target -- grouped on the regular reading, and
                  -- fallen back on the budget side -- sat on RAC/LCAC/APPLIED
                  -- with no sales beside it. Every figure on the board was
                  -- filed under the wrong bar, in both directions at once.
                  --
                  -- With the fallback, Manager reads exactly like Regular
                  -- until somebody tags a merge on a product category, and
                  -- diverges only where one is tagged -- which is what the
                  -- field offers to do.
                  COALESCE({pcat_merged}, {pcat_sub}) AS merged_subcategory
           FROM product_category
           WHERE (length(parent_path)-length(replace(parent_path,'/','')))=2
             AND NULLIF(trim(code),'') IS NOT NULL ORDER BY parent_id, trim(code), id),
    d3 AS (SELECT DISTINCT ON (pc.parent_id, trim(pc.code))
                  pc.id, pc.parent_id, trim(pc.code) AS code, pc.name,
                  -- The family link, carried here so the sales side can meet
                  -- the budget's family on the join -- see lfam_code below --
                  -- and resolved THROUGH a merge, so a family reporting under
                  -- another lands on the same code the budget side does.
                  COALESCE({fam_merged_dfam}, {pcat_family_col_pc}) AS product_family
           FROM product_category pc
           LEFT JOIN product_family dfam ON dfam.id = {pcat_family_col_pc}
            WHERE (length(pc.parent_path)-length(replace(pc.parent_path,'/','')))=3
              AND NULLIF(trim(pc.code),'') IS NOT NULL
            ORDER BY pc.parent_id, trim(pc.code), pc.id),
    cust AS (
        SELECT c.cst_no, COALESCE(c.cst_name, cd.cst_name) AS cst_name
        FROM customer c
        LEFT JOIN LATERAL (SELECT cst_name FROM customerdesc d
                           WHERE d.cst_no = c.cst_no ORDER BY d.cst_lang LIMIT 1) cd ON true
    ),
    -- res_city keyed on the spelling the ERP FEED uses, which is not always
    -- the spelling res.city holds: the feed still says KHM and TAB where the
    -- cities were renamed KMH and TBK. A real city always wins (the NOT
    -- EXISTS), so this can only fill a gap, never shadow a genuine code.
    --
    -- sales_budget/models/sales_budget_import.py holds the same two pairs as
    -- CITY_CODE_ALIASES and pbi_budget_dashboards/models/bidata_budget_month.py
    -- as SQL. Duplicated rather than imported because the pbi_* modules
    -- deliberately do not depend on that one -- if this list changes, change
    -- it in all three. If res.city is ever put back to KHM/TAB, delete the
    -- UNION branch rather than inverting it.
    cty AS (
        SELECT upper(btrim({city_code})) AS code, city.id,
               {city_report_region} AS report_region
        FROM res_city city
        UNION ALL
        SELECT a.feed_code, city.id, {city_report_region}
        FROM (VALUES ('KHM', 'KMH'), ('TAB', 'TBK')) AS a(feed_code, city_code)
        JOIN res_city city ON upper(btrim({city_code})) = a.city_code
        WHERE NOT EXISTS (SELECT 1 FROM res_city x
                          WHERE upper(btrim(x.code)) = a.feed_code)
    ),
    -- THE CUSTOMER'S OWN CITY, and the region it reports into. Used only where
    -- the invoice header carries NEITHER a report region NOR a city of its
    -- own, which is a real gap in the feed rather than a rare one: 868 lines
    -- and SAR 14,863,955 of 2026 arrived with trnh_cityid NULL and were drawn
    -- as an "Unassigned" region on every region chart.
    --
    -- The header still wins wherever it has a value. That matters: on the
    -- 13,872 2026 headers that carry BOTH, the two agree on 13,810 and differ
    -- on 62, so the customer's city is a good stand-in but not an authority --
    -- a ship-to address can legitimately differ from the customer's own.
    cust_city AS (
        SELECT c.cst_no, cty.id AS city_id, cty.report_region
        FROM customer c
        JOIN cty ON cty.code = upper(btrim({cust_subregion}))
    ),
    sales AS (
        SELECT
            substring(h.trnh_date,1,4)::int   AS yr,
            substring(h.trnh_date,5,2)::int   AS mth,
            trim(d.trnd_group)                AS franchise_code,
            -- Upper-cased for the same reason the joins are -- see the `cat`
            -- CTE. Without it MSTS12CRNAG15-NP-F and MSTS12CRNAG15-NP-f are
            -- two rows and two bars for one physical part.
            upper(trim(d.trnd_part))          AS part_no,
            -- Whether this line's (group, stock, part) carries the '02'
            -- catalogflags row -- the same test the qty expression below gates
            -- on, carried per row so the gated and ungated unit counts can both
            -- be measured off the snapshot without rebuilding it.
            (u.part IS NOT NULL)              AS unit_tagged,
            -- THE SCOPE OF THE BOARD, carried as a column rather than applied
            -- here: the debug-only Scope control can widen to every MDA line,
            -- and a snapshot pre-filtered to the scope could never answer that.
            --
            -- The product test reads product_category.code straight off
            -- transaction_details.trnd_groupid -- the source system's own
            -- product-group key on the line. It is a real FK: 23 distinct
            -- values on MDA lines, every one a depth-2 category, populated on
            -- 94.3 pct of them.
            --
            -- THE COALESCE IS NOT DECORATION -- it is what makes the board
            -- agree with bidata.
            --
            -- trnd_groupid = 1193 is a DANGLING REFERENCE: no product_category
            -- row has that id (the table stops at 1,172, and 1190-1200 is
            -- empty), yet 10,451 MDA lines point at it -- and they are real
            -- machines, parts like MDV-V56WDHN1(ATB) and MDV-D56T2/VN1-DA5(2),
            -- which the `catalog` chain classifies as ACVRF, ACCON and ACCST.
            -- Reading trnd_groupid alone therefore dropped SAR 60,866,777 of
            -- 2025 and SAR 32,303,319 of 2026-to-July.
            --
            -- That is exactly the shortfall measured against bidata's own
            -- monthly figures: for 2026 months 3, 4 and 5 the gap equalled the
            -- 1193 money TO THE CENT, and across January-July it accounted for
            -- 32,303,319 of a 32,518,366 gap -- 99.3 pct. Falling back to the
            -- catalog chain wherever trnd_groupid does not resolve closes it.
            --
            -- Both inputs are needed, in this order: trnd_groupid is the ERP's
            -- own per-line answer and wins where it exists; the chain covers
            -- the 1193 orphans and the 5,041 lines a year with no groupid at
            -- all. RESTORING product_category id 1193 upstream would make the
            -- fallback redundant for the orphans, and is still worth doing.
            --
            -- NOT trnd_productid, which looks like the direct route and is not
            -- one: its values run 19,655-90,394 while product_category.id
            -- stops at 1,172, so that join matches nothing at all; and where it
            -- does resolve against product_template (81.6 pct of MDA lines) the
            -- part number on the row agrees only 12.0 pct of the time -- line
            -- part MDV-D56T2/VN1-DA5(AT) points at template code 49099187,
            -- group SPCDY. It is a stale key.
            --
            -- COALESCE, not a bare IN: a line with no trnd_groupid leaves the
            -- code NULL, and `NULL IN (...)` is NULL rather than false -- which
            -- the budget-only COALESCE downstream would then read as "in
            -- scope".
            --
            -- AND THE GROUPID IS ONLY AN ANSWER FOR ITS OWN FRANCHISE.
            -- product_category codes repeat across franchise branches, so the
            -- id has to be checked against the branch the LINE sold under
            -- before it is believed. One line in 2024-2026 fails that test and
            -- it is a real error: TH1152, a Midea WiFi thermostat on an MDA
            -- invoice, carries trnd_groupid 1042 -- which is RUD/ACC, Ruud's
            -- accessories group. Reading it straight put the line outside the
            -- AC whitelist and dropped SAR 1,550 of May 2024. Rejecting the
            -- cross-franchise id lets the catalog chain answer instead, and the
            -- chain has an MDA row for that part (MDA/ACACC), so the line lands
            -- in scope and in the right bucket.
            --
            -- bidata never had this to resolve: it carries the franchise on the
            -- row and derives the product group within it, which is why this
            -- was the LAST value gap between these boards and v_bidata_live
            -- across 2024, 2025 and 2026-to-June. It is now closed to the
            -- riyal on every month of all three years.
            --
            -- Paired with the (franchise, part) key on the `cat` CTE above:
            -- the guard is what makes the fallback fire, and that key is what
            -- makes the fallback right -- TH1152 is catalogued under RUD as
            -- well, and keyed on the part alone the chain answered RUD/ACC too.
            (COALESCE(CASE WHEN trim(pcgf.code) = trim(d.trnd_group)
                           THEN trim(pcg.code) END,
                      trim(d2.code),
                      CASE WHEN tg.fr = trim(d.trnd_group)
                           THEN tg.pg END, '') IN (
                 'ACACC','ACCON','ACCST','ACPAC','ACPKG','ACAIP',
                 'ACPOR','ACVRF','ACWIN','ACWTS','ACHCL','ATOM')
             AND trim(h.trnh_cstno) NOT LIKE 'V%')  AS in_scope,
            max(cat.descr)                    AS part_label,
            -- L1 from the master data sale type group.
            sg.id AS l1_code,
            pcl.id AS l2_code,
            rreg.id AS l3_code,
            -- Header city first, the customer master's second -- see cust_city.
            COALESCE(city.id, cc.city_id) AS l4_code,
            trim(h.trnh_sman) AS l5_code,
            max(COALESCE(sp.name, sm.sm_name, h.trnh_salesmanname, h.trnh_sman)) AS l5_label,
            trim(h.trnh_cstno) AS l6_code,
            mc.id  AS l7_code,
            sc.id  AS l8_code,
            mcm.id AS l7m_code,
            scm.id AS l8m_code,
            d2.id  AS l9_code,
            -- The family, from the sub-group's own master link. A function of
            -- d3, so it adds nothing to this CTE's grain -- it is carried
            -- because the budget states a family too and the two have to meet
            -- on it (see the FULL OUTER JOIN and budget_key below).
            {pcat_family} AS lfam_code,
            -- QTY COUNTS UNITS, NOT LINE ITEMS.
            --
            -- A split air conditioner ships as two parts on the same invoice:
            -- the condenser (outdoor) and the fan-coil (indoor). IN20140433
            -- carries MSTL36CRN3MB-NP-C qty 7 and MSTL36CRN3MB-NP-F qty 7 --
            -- seven machines, not fourteen. Summing both lines overstates every
            -- quantity on the board by roughly the split share of the mix.
            --
            -- The unit-bearing half is the one carrying product.tag '02',
            -- matched on the part -- see the unitpart CTE, and see it also for
            -- why this reads Odoo's own tag rather than the catalogflags column
            -- it is mirrored from, and what had to be true before it could.
            -- Measured on this
            -- database the flag lands on 613 parts of catalog type 'F'
            -- (fan-coil) and 403 of type 'O'/'A'/'P' (single-piece window,
            -- portable), against just 2 of type 'C' (condenser) -- so counting
            -- only flagged lines counts machines. This replaces the older
            -- cat_parttype='C' rule; the flag is the source system's own marker
            -- rather than a reading of it.
            --
            -- ⚠️ THE FLAG STILL LAGS THE CATALOG. In-scope units under this
            -- gate, against the old "everything except a condenser" rule
            -- (dbprod, 2026-08-27):
            --
            --     2024   245,111 vs 256,780   -4.5 pct
            --     2025   271,550 vs 295,215   -8.0 pct
            --     2026   162,599 vs 224,856  -27.7 pct  (partial year)
            --
            -- Read 2026 with care: that rule counts a line whose part has NO
            -- catalog row at all (cat_parttype is NULL, which is not 'C'), and
            -- new parts are exactly what the catalog is missing -- so the right
            -- column is inflated most in the year the gap looks worst. The
            -- share of in-scope VALUE sitting on flagged parts, which has no
            -- such artefact, is flat at 46.7 / 45.0 / 45.2 pct across the three
            -- years, so there is no widening trend to read into this.
            --
            -- What does hold is the level: reported YoY unit growth for 2025 is
            -- +10.8 pct where the old rule reads +15.0 pct. That is coverage,
            -- not trade. Kept anyway, because the flag is the business's own
            -- rule AND because it is the one the New boards report -- matching
            -- them is the point of this gate. If unit growth ever reads low for
            -- the current year, look here first.
            --
            -- Two thirds of that 2025 gap of 23,664 units is REAL MACHINES the
            -- flag simply has not reached yet, not accessories correctly left
            -- at zero:
            --
            --     ACWTS 'O'   7,879    ACACC 'O'   5,554  (accessory)
            --     ACPAC 'F'   3,895    ACACC 'P'   2,509  (accessory)
            --     ACVRF 'O'   3,827
            --
            -- i.e. 15,601 machines missing (5.7 pct of the 271,550 reported)
            -- against 8,063 accessories rightly excluded. A hybrid -- flag '02'
            -- where present, "count unless condenser" where absent, skipping
            -- ACACC -- would recover the 15,601 without pulling the
            -- accessories back in, and would read 287,151 for 2025. Not done:
            -- the '02' rule is what was asked for, and changing it is a
            -- business call, not a code cleanup.
            --
            -- THE GATE IS ON, AND IT APPLIES TO QUANTITY ONLY. A line whose
            -- part carries no '02' catalogflags row contributes zero UNITS but
            -- its full VALUE -- which is the whole point: both halves of a
            -- split carry real money (2,503 + 1,347 on that invoice), and on
            -- 2025 the unflagged lines are SAR 330.5m of SAR 601.0m in scope,
            -- mostly condensers. Gating value the same way would report 45
            -- percent of the year against a target of SAR 676m. Value stays on
            -- the issued quantity; see the amount expression below.
            --
            -- "Sales Dashboard - New" and "Sales Analysis - New" split the two
            -- measures the same way and for the same reason: v_bidata_live
            -- gates bi_qty on this flag but computes bi_amount from the RAW
            -- invoiced quantity. Their controllers spell out what happens when
            -- that is got wrong -- deriving value from the gated count halved
            -- every figure on those boards, 601.0M -> 270.7M for 2025. See
            -- PbiSalesMailNewController in controllers/sales_mail_main.py.
            --
            -- Because of that the two measures are deliberately NOT in
            -- proportion, and a reader comparing them will notice. Units are
            -- machines; value is money.
            --
            -- Credit notes still subtract, at trnd_ret rather than trnd_qtyiss.
            -- `unit_tagged` above carries the same test per row, so the ungated
            -- reading is still available without a rebuild.
            sum(CASE WHEN u.part IS NULL THEN 0
                     WHEN lpad(trim(h.trnh_type),2,'0') = '02'
                     THEN -COALESCE(d.trnd_ret,0)
                     ELSE COALESCE(d.trnd_qtyiss,0) END)::numeric AS qty,
            --
            -- THE DISCOUNT IS FOUR THINGS, NOT ONE. trnd_disc is only the line
            -- discount; a line can also carry a promotion (trnd_promodisc) and
            -- a campaign (trnd_campaign), and the document can carry a header
            -- discount (trnh_headdisc) that belongs to no line at all. The
            -- header one is spread across the lines in proportion to what each
            -- is worth AFTER its own three discounts, over the document total
            -- -- which is why trnh_total guards the division: a document with a
            -- zero or missing total has nothing to apportion against, and
            -- dividing by it would raise rather than return zero.
            --
            -- Measured against the New boards on dbprod (2026-08-27) this is
            -- small but strictly an improvement -- it moves three months and
            -- every one of them towards bidata, two of them onto it exactly:
            --
            --     2024-10   -191 ->  0        exact
            --     2024-12  -1,225 -> -1,125
            --     2025-06   +145 ->  0        exact
            --
            -- every other month of 2024-2026 unchanged. Small because
            -- promotions, campaigns and header discounts are rare on AC lines,
            -- not because the terms are redundant.
            --
            -- Written as one multiplication rather than the two the credit-note
            -- CASE used to duplicate: the quantity is what flips sign, the
            -- price bracket is identical on both arms, and repeating this
            -- bracket twice would be four more places to get the discount
            -- wrong. Verified equivalent on the old formula before the change.
            sum((CASE WHEN lpad(trim(h.trnh_type),2,'0') = '02'
                      THEN -COALESCE(d.trnd_ret,0)
                      ELSE COALESCE(d.trnd_qtyiss,0) END)
                * (COALESCE(d.trnd_price,0)
                   - (COALESCE(d.trnd_disc,0)
                      + COALESCE(d.trnd_promodisc,0)
                      + COALESCE(d.trnd_campaign,0)
                      + CASE WHEN COALESCE(h.trnh_total,0) > 0
                             THEN (COALESCE(d.trnd_price,0)
                                   - COALESCE(d.trnd_disc,0)
                                   - COALESCE(d.trnd_promodisc,0)
                                   - COALESCE(d.trnd_campaign,0))
                                  * COALESCE(h.trnh_headdisc,0) / h.trnh_total
                             ELSE 0 END)
                   - COALESCE(d.trnd_cstspldisc,0)))::numeric AS amount
        FROM transaction_details d
        -- header_id is the real key -- an FK to transaction_header.id, so it
        -- cannot fan a detail line out. The warehouse equality rides along as
        -- an INVARIANT GUARD, per instruction.
        --
        -- It is inert on this database and expected to stay that way: across
        -- the WHOLE of transaction_details -- 200,235 rows, 2024-01-01 to
        -- 2026-08-05, every document type and every franchise, not just the
        -- board's scope -- trnh_whouse equals trnd_whouse on every single row,
        -- with no exceptions and no NULLs on either side. So it selects nothing
        -- out today; it is here to make a line whose two warehouses ever
        -- disagree fall out rather than be counted against the wrong branch.
        --
        -- Do NOT expect it to move any figure. In particular it does nothing
        -- for the June 2026 gap against "Sales Dashboard - New": CR20112352 and
        -- its posted twin CR20112381 are both warehouse 201 on header and on
        -- every line.
        --
        -- Note this is NOT the same column as trnd_stock, despite the names
        -- reading alike. trnd_stock is '*' on every MDA line and cat_stock is
        -- '*' on all 1,127 catalogflags '02' rows -- that key component is a
        -- constant wildcard carrying no information. The real warehouse lives
        -- here, in trnd_whouse (201, 101, 301, ...).
        JOIN transaction_header h ON h.id = d.header_id
                                 AND trim(h.trnh_whouse) = trim(d.trnd_whouse)
        -- LEFT, not INNER. The board's default scope is the AC product groups
        -- excluding 'V' customers, but the debug-only Scope control can widen
        -- it to every MDA line, and a snapshot pre-filtered to the scope could
        -- never answer that. So the test rides along as the in_scope column and
        -- the filtering happens at query time; a part the catalog chain cannot
        -- map simply falls out of scope rather than out of the snapshot.
        LEFT JOIN product_category pcg ON pcg.id = d.trnd_groupid
        -- The franchise the groupid actually belongs to -- see the in_scope
        -- test, which will not read a code from another franchise's branch.
        LEFT JOIN product_category pcgf ON pcgf.id = pcg.parent_id
        -- Part alone: see the unitpart CTE for why the group and stock
        -- components were dropped and what they were worth (nothing).
        LEFT JOIN unitpart u ON u.part = upper(trim(d.trnd_part))
        -- Both halves of the key -- see the `cat` CTE for the part number that
        -- is catalogued under two franchises and what joining on it alone cost.
        LEFT JOIN cat  ON cat.grp = upper(trim(d.trnd_group))
                      AND cat.part = upper(trim(d.trnd_part))
        -- Scope backstop only -- see the tmplgrp CTE. Part alone here; the
        -- franchise is checked in the in_scope test itself, where the line's
        -- own trnd_group is in scope.
        LEFT JOIN tmplgrp tg ON tg.part = upper(trim(d.trnd_part))
        LEFT JOIN d1   ON d1.code = cat.fr
        LEFT JOIN d2   ON d2.parent_id = d1.id AND d2.code = cat.pg
        LEFT JOIN d3   ON d3.parent_id = d2.id AND d3.code = cat.psg
        LEFT JOIN sub_category  sc  ON sc.id  = d2.sub_category
        LEFT JOIN main_category mc  ON mc.id  = sc.subcat_maincategory_id
        LEFT JOIN sub_category  scm ON scm.id = d2.merged_subcategory
        LEFT JOIN main_category mcm ON mcm.id = scm.subcat_maincategory_id
        LEFT JOIN customer c ON c.cst_no = h.trnh_cstno
        LEFT JOIN res_city city ON city.id = h.trnh_cityid
        LEFT JOIN cust_city cc ON cc.cst_no = h.trnh_cstno
        LEFT JOIN res_region rreg ON rreg.id = COALESCE(h.trnh_rptregionid,
                                                        {city_report_region},
                                                        cc.report_region)
        LEFT JOIN partner_classification pcl ON (pcl.pc_code = lpad(trim(c.cst_cstclassification), 3, '0')
                                              OR pcl.pc_code = trim(c.cst_cstclassification))
        LEFT JOIN LATERAL (SELECT sm2.sm_name FROM sl_salesmandesc sm2
                           WHERE sm2.sm_code = h.trnh_sman AND sm2.sm_lang='1' LIMIT 1) sm ON true
        LEFT JOIN res_partner sp ON sp.id = h.trnh_smanid {sp_salesman_test}
        -- THE SALE TYPE COMES FROM trnh_xface, THE CODE, NOT FROM trnh_xfaceid.
        --
        -- trnh_xfaceid is a denormalised id the ERP feed writes beside the
        -- code, and it is only ever as current as the run that wrote it. A
        -- sale type created AFTER those rows landed has no id to point at, so
        -- the feed leaves whatever was there -- and the row then reports under
        -- a sale type it was never booked under. That is not hypothetical:
        -- 101 Modern Trade and 102 Wholesale were added to sale_types on
        -- 2026-09, and all 2,830 headers carrying them still hold
        -- trnh_xfaceid = 1, so every one of them counted as 001 FG Direct
        -- Sales -- i.e. under Dealers -- and the two new types drew no bar at
        -- all. Reading the id first is what hid them.
        --
        -- The code is the safer of the two on this database and by some
        -- distance: trnh_xface is populated on all 63,813 headers, every one
        -- of its 16 distinct values resolves to a sale_types row, and it
        -- agrees with trnh_xfaceid everywhere the id is not stale. The id is
        -- kept only as a fallback for a header whose code no master row
        -- matches -- none today, but a code retired from sale_types would
        -- otherwise silently lose its group.
        --
        -- This is also what makes sale_types a live master rather than a
        -- caption: add or re-point a sale type and the next refresh -- queued
        -- within a minute by the trigger in _install_master_data_triggers --
        -- moves the sales under it. Before this it moved nothing, because the
        -- id had already decided.
        LEFT JOIN sale_types st ON st.id = COALESCE(
            (SELECT st2.id FROM sale_types st2
             WHERE st2.sal_ref = lpad(trim(h.trnh_xface),3,'0') LIMIT 1),
            h.trnh_xfaceid)
        LEFT JOIN salestypes_group sg ON sg.id = st.saltype_group
        -- MIDEA ONLY. Both boards are Midea AC boards now: the whole budget
        -- is MDA (SAR 676,460,596 for 2025, not one row on any other code) and
        -- the twelve product groups in scope are all Midea AC. Applied here
        -- rather than carried as a column, because unlike the scope test there
        -- is no view of this board that wants the other franchises -- which is
        -- also why neither board offers a Franchise control any more.
        WHERE lpad(trim(h.trnh_type),2,'0') IN ('01','02')
          AND trim(d.trnd_group) = 'MDA'
          -- POSTED AND CLOSED DOCUMENTS ONLY. trnh_status carries exactly
          -- three values on this database and nothing else: 'P' posted, 'C'
          -- closed, 'N' not posted. 'C' and 'N' are NEW -- the first of either
          -- is dated 2026-05-03, everything before that is 'P' -- so this test
          -- changes nothing for 2024, 2025 or January-April 2026 and only
          -- starts biting in the current year.
          --
          -- IT MOVES MAY AND JUNE 2026 AWAY FROM bidata, AND THAT IS CORRECT.
          -- Against the New boards (dbprod, 2026-08-27, MTD):
          --
          --     2026-05   44,184,012 vs 44,285,156   -101,144   was exact
          --     2026-06   62,947,350 vs 62,370,712   +576,638   was -1,194
          --
          -- with units moving 21,123 vs 21,175 and 27,574 vs 27,300 the same
          -- way. Every other month of 2024-2026 is untouched.
          --
          -- DO NOT "FIX" THAT GAP BY RELAXING THIS TEST. bidata cannot agree,
          -- for two reasons that compound:
          --
          --   1. It carries NO STATUS COLUMN AT ALL -- nothing matching
          --      '%stat%' exists on the table. The filter is applied when the
          --      feed is populated, so what survives into bidata is whatever
          --      passed the test ON THE DAY IT RAN, and the column that decided
          --      it is not carried across for anyone to re-check.
          --
          --   2. The statuses were then REWRITTEN UNDERNEATH IT. Every one of
          --      the 381 'C' headers on 2026 was written on or after
          --      2026-07-29, and 99 of the 108 'N' ones were written since
          --      July. Narrowing to May and June documents specifically: all
          --      179 'C' and 47 of the 59 'N' were re-written on or after
          --      2026-07-29, after the feed had already captured those months.
          --
          -- So bidata is a PRE-RECLASSIFICATION SNAPSHOT of May and June: it
          -- holds those documents as they stood when they were still posted.
          -- Reading it back today and concluding "bidata keeps unposted
          -- documents, so this rule is wrong" inverts cause and effect. This
          -- table reads the ERP live and reports what the ERP says NOW, which
          -- is the point of it.
          --
          -- One document is a separate matter and this test does not explain
          -- it: CR20112352 (18 Jun 2026, customer J337, SAR -1,194.05) is the
          -- only in-scope document across 2024-2026 present in the ERP and
          -- absent from bidata altogether. It happens to be 'N' and so falls
          -- out here anyway.
          AND trim(h.trnh_status) IN ('C', 'P')
        GROUP BY 1, 2, 3, 4, 5, 6,
                 sg.id, pcl.id, rreg.id, city.id, cc.city_id,
                 trim(h.trnh_sman), trim(h.trnh_cstno),
                 mc.id, sc.id, mcm.id, scm.id, d2.id, d3.id, {pcat_family}
    ),
    budget AS (
        -- Resolved from the budget's CODES, not from ids it stores.
        --
        -- The budget carries every dimension twice: as a link to our master
        -- and as the code the source file actually had (see
        -- SalesBudgetLine._compute_dimension_codes). Reading the codes and
        -- resolving them HERE moves the dependency on those masters out of the
        -- budget and into the reporting layer, which depends on them anyway --
        -- it is the actuals side of this very view that resolves
        -- partner_classification by pc_code already.
        --
        -- The ids this produces are identical to the ids the budget stores:
        -- the codes were derived from them, and every master's code is unique
        -- and non-blank (verified: 6/3/6/10/6 rows, no duplicates), so each
        -- join matches exactly one row or none. A row whose code is '' matches
        -- nothing and yields NULL -- which is what its id was.
{budget_cte}
    ),
    codes AS (
    SELECT
        COALESCE(s.yr, b.yr)   AS yr,
        COALESCE(s.mth, b.mth) AS mth,
        -- l2 l3 l4 l6 l9 ARE the join key, so s and b agree wherever both
        -- exist and COALESCE only fills a budget-only row. The rest are NOT
        -- in the key, so a sales row must keep its OWN category -- taking b's
        -- would re-attribute the actuals by whatever the budget happened to
        -- say. Found the hard way, back when product_category.merged_subcategory
        -- was read raw and was NULL on all 240 categories while the budget
        -- carried a merged code on every row: a plain COALESCE then made the
        -- dead Manager view look alive, captioned off the budget side. d2 now
        -- applies the identity fallback the field always meant, so the sales
        -- side has its own merged reading -- and this rule still stands, for
        -- the reason above rather than for that symptom.
        CASE WHEN s.part_no IS NULL THEN b.franchise_code
             ELSE s.franchise_code END AS franchise_code,
        s.part_no, s.part_label, s.unit_tagged,
        -- A budget-only row belongs to whatever scope is on screen: the target
        -- exists either way, and blanking it under the AC-groups scope would
        -- make the default view lose targets it has today.
        CASE WHEN s.part_no IS NULL THEN true ELSE s.in_scope END AS in_scope,
        CASE WHEN s.part_no IS NULL THEN b.l1_code  ELSE s.l1_code  END AS l1_code,
        -- The BUDGET's own sale type, kept beside the row's one rather than
        -- instead of it, because at l1 the two are different facts and both are
        -- needed. l1 is not in the join key (see the CASE above: a sales row
        -- must keep its own category), so one budget tuple can land on rows of
        -- two sale types -- and the max()-per-budget_key de-duplication that
        -- every budget query runs then returns its whole figure once per sale
        -- type. Measured: 3 tuples in 2025, SAR 90,232 counted twice, which is
        -- the 0.018 pct by which the l1 target bars used to overshoot their own
        -- tile. The budget side is never ambiguous -- every capture tuple
        -- carries exactly one salestype_group_id, in all three years -- so
        -- grouping the target on THIS column instead is exact by construction,
        -- and leaves the actuals attributed as they were.
        b.l1_code AS budget_l1_code,
        COALESCE(s.l2_code, b.l2_code) AS l2_code,
        COALESCE(s.l3_code, b.l3_code) AS l3_code,
        COALESCE(s.l4_code, b.l4_code) AS l4_code,
        s.l5_code, s.l5_label,
        COALESCE(s.l6_code, b.l6_code) AS l6_code,
        CASE WHEN s.part_no IS NULL THEN b.l7_code  ELSE s.l7_code  END AS l7_code,
        CASE WHEN s.part_no IS NULL THEN b.l8_code  ELSE s.l8_code  END AS l8_code,
        CASE WHEN s.part_no IS NULL THEN b.l7m_code ELSE s.l7m_code END AS l7m_code,
        CASE WHEN s.part_no IS NULL THEN b.l8m_code ELSE s.l8m_code END AS l8m_code,
        COALESCE(s.l9_code, b.l9_code) AS l9_code,
        COALESCE(s.lfam_code, b.lfam_code) AS lfam_code,
        COALESCE(s.qty, 0)    AS qty,
        COALESCE(s.amount, 0) AS amount,
        CASE WHEN b.yr IS NULL THEN NULL ELSE {budget_key} END AS budget_key,
        b.budget_qty, b.budget_value
    FROM sales s
    FULL OUTER JOIN budget b
      -- s.in_scope is part of the JOIN, not a WHERE, and it is what keeps the
      -- target whole. Without it a budget tuple whose only matching actuals
      -- are out of scope rides on those out-of-scope rows and vanishes the
      -- moment the board filters on in_scope -- SAR 364,998 of the SAR
      -- 676,460,596 target for 2025. Failing the join instead turns that
      -- tuple into a budget-only row, which is in scope by definition, and
      -- leaves the out-of-scope actual with no target attached rather than
      -- one it should never have carried.
      ON  s.in_scope
      AND b.yr = s.yr AND b.mth = s.mth
      AND b.l2_code IS NOT DISTINCT FROM s.l2_code
      AND b.l3_code IS NOT DISTINCT FROM s.l3_code
      AND b.l4_code IS NOT DISTINCT FROM s.l4_code
      AND b.l6_code IS NOT DISTINCT FROM s.l6_code
      AND b.l9_code IS NOT DISTINCT FROM s.l9_code
      AND b.lfam_code IS NOT DISTINCT FROM s.lfam_code
    ),
    v AS (
    SELECT
        k.yr, k.mth, k.franchise_code, fr.name AS franchise_label,
        k.part_no, k.part_label, k.in_scope, k.unit_tagged,
        -- Every level code is TEXT on the way out, including the ones that
        -- are integer ids underneath (l1-l4, l7-l10 are row ids; l5/l6 are
        -- already char codes). Callers treat a level code as an opaque string:
        -- they COALESCE it to the '__none__' sentinel, ship it to the browser
        -- as JSON, and get it back in a drill path. Left as integer,
        -- COALESCE(l1_code, '__none__') fails with "invalid input syntax for
        -- type integer" the moment the first chart groups by level 1. The fact
        -- CTE this view replaced cast them the same way (sg.id::text); keeping
        -- that contract is what lets the controllers stay unchanged.
        k.l1_code::text  AS l1_code,  sg.salgrp_name AS l1_label,
        k.budget_l1_code::text AS budget_l1_code, sgb.salgrp_name AS budget_l1_label,
        k.l2_code::text  AS l2_code,  COALESCE(NULLIF(pcl.pc_classification1,''), pcl.complete_name) AS l2_label,
        -- res_region.name / res_city.name are read through
        -- _translated_text_expr rather than a literal ->>'en_US': their
        -- storage type is another module's decision (three modules declare
        -- res.region; the column follows whichever was upgraded last) and
        -- has differed between our two servers, where the literal form
        -- failed with "character varying ->> unknown".
        k.l3_code::text  AS l3_code,  {region_name} AS l3_label,
        k.l4_code::text  AS l4_code,  {city_name} AS l4_label,
        k.l5_code,                    k.l5_label,
        -- COALESCE, because a budget-only row's customer code need not be a
        -- customer. The 2026 budget is captured against ten segment codes
        -- (JEDDLR, RYDPRJ, WHSALE...), each one a city x channel that the
        -- budget ALSO states in its own region_id/city_id/
        -- partner_classification_id columns -- so the code is redundant rather
        -- than wrong, but it joins to no customer, and cst_name alone left
        -- those rows nameless: ten blank captions carrying the entire target at
        -- the Customer level. The code itself names them, and any real customer
        -- missing a name is covered by the same fallback.
        k.l6_code,                    COALESCE(cu.cst_name, k.l6_code) AS l6_label,
        k.l7_code::text  AS l7_code,  mc.maincat_name    AS l7_label,
        k.l8_code::text  AS l8_code,  sc.subcat_name     AS l8_label,
        k.l7m_code::text AS l7m_code, mcm.maincat_name   AS l7m_label,
        k.l8m_code::text AS l8m_code, scm.subcat_name    AS l8m_label,
        k.l9_code::text  AS l9_code,  CASE WHEN UPPER(COALESCE(pg.name, '')) IN ('ACWTSPLIT', 'ACWTS') OR COALESCE(pg.code, '') = 'ACWTS' OR UPPER(COALESCE(pg.name, '')) LIKE '%ACWTSPLIT%' THEN 'Split' ELSE pg.name END AS l9_label,
        -- THE PRODUCT SUB-GROUP, NAMED RATHER THAN NUMBERED.
        --
        -- It is the model family -- ELITE R410 -- and it is what the boards
        -- report as Product Sub-Group. The name is not lfam by accident: it
        -- arrived after l1-l10 were fixed, sat between l9 and the old l10 while
        -- both existed, and numbering it would have meant either lying about
        -- where it sat or renumbering the chain. LEVELS in
        -- controllers/sales_sman_main.py decides the drill order; this is only
        -- a column name.
        --
        -- Resolved from the depth-3 category's family rather than per part, so
        -- every category in a family reports under that family, always. See the
        -- product.family docstring for how the mapping was worked out
        -- (catalog.cat_mainpartno joins the indoor and outdoor halves; bidata
        -- names what the pair is) and for why it is stored as master data
        -- rather than re-derived here -- bidata lags, and a level that read it
        -- live would lag with it.
        k.lfam_code::text AS lfam_code, pfam.pfam_name   AS lfam_label,
        k.qty, k.amount,
        k.budget_key, k.budget_qty, k.budget_value
    FROM codes k
    LEFT JOIN d1                    fr   ON fr.code = k.franchise_code
    LEFT JOIN salestypes_group      sg   ON sg.id   = k.l1_code
    LEFT JOIN salestypes_group      sgb  ON sgb.id  = k.budget_l1_code
    LEFT JOIN partner_classification pcl ON pcl.id  = k.l2_code
    LEFT JOIN res_region            rreg ON rreg.id = k.l3_code
    LEFT JOIN res_city              city ON city.id = k.l4_code
    LEFT JOIN cust                  cu   ON cu.cst_no = k.l6_code
    LEFT JOIN main_category         mc   ON mc.id   = k.l7_code
    LEFT JOIN sub_category          sc   ON sc.id   = k.l8_code
    LEFT JOIN main_category         mcm  ON mcm.id  = k.l7m_code
    LEFT JOIN sub_category          scm  ON scm.id  = k.l8m_code
    LEFT JOIN product_category      pg   ON pg.id   = k.l9_code
    LEFT JOIN product_family        pfam ON pfam.id = k.lfam_code
    )
    SELECT row_number() OVER (ORDER BY yr, mth, part_no, l6_code) AS id, v.*
    FROM v
        """.format(
            stubs=stubs,
            budget_key=_BUDGET_KEY_SQL,
            budget_cte=_BUDGET_CTE_SQL.format(
                budget_salesman=optional_schema.column_ref(cr, 'v_sales_budget_month', 'salesman_partner_id', 'integer', alias='b'),
                budget_erp_subgroup=budget_erp_subgroup,
                fam_merged_bfam=fam_merged_bfam,
                single_family_group=single_family_group,
                group_whitelist="\n            SELECT DISTINCT l9_code FROM sales\n"
                                "            WHERE l9_code IS NOT NULL AND in_scope",
                pcat_sub_bpc=optional_schema.column_ref(cr, 'product_category', 'sub_category', 'integer', alias='bpc'),
                pcat_merged_bpc=optional_schema.column_ref(cr, 'product_category', 'merged_subcategory', 'integer', alias='bpc')),
            pcat_sub=pcat_sub,
            pcat_merged=pcat_merged,
            pcat_family=pcat_family,
            pcat_family_col=pcat_family_col,
            pcat_family_col_pc=pcat_family_col_pc,
            fam_merged_dfam=fam_merged_dfam,
            city_report_region=city_report_region,
            city_code=city_code,
            cust_subregion=cust_subregion,
            sp_salesman_test=sp_salesman_test,
            region_name=board_sql._translated_text_expr("rreg.name", "en_US"),
            city_name=board_sql._translated_text_expr("city.name", "en_US"),
            # product_tag.name, read whether it is stored as jsonb or varchar
            # -- see the unitpart CTE. Compared against a CODE, not a label,
            # so the language asked for makes no difference to the answer.
            tag_name=board_sql._translated_text_expr("g.name", "en_US"),
        ))
        # Unique on id is not optional: REFRESH ... CONCURRENTLY requires it.
        cr.execute("CREATE UNIQUE INDEX pbi_sman_fact_id_idx ON v_pbi_sales_sman_fact (id)")
        # Every board filters on the period first, then narrows by level.
        cr.execute("CREATE INDEX pbi_sman_fact_period_idx ON v_pbi_sales_sman_fact (yr, mth)")
        cr.execute("CREATE INDEX pbi_sman_fact_budget_key_idx ON v_pbi_sales_sman_fact (budget_key)")
        cr.execute("CREATE INDEX pbi_sman_fact_franchise_idx ON v_pbi_sales_sman_fact (franchise_code)")
        cr.execute("CREATE INDEX pbi_sman_fact_scope_idx ON v_pbi_sales_sman_fact (in_scope)")
        cr.execute("CREATE INDEX pbi_sman_fact_sman_idx ON v_pbi_sales_sman_fact (l5_code)")
        cr.execute("CREATE INDEX pbi_sman_fact_group_idx ON v_pbi_sales_sman_fact (l9_code)")
        cr.execute("ANALYZE v_pbi_sales_sman_fact")
        self._build_budget_helpers()
        self._build_budget_live_view(stubs)
        self._install_master_data_triggers()

    def _install_master_data_triggers(self):
        """Make an edit to any of the eleven levels' master data rebuild this.

        Each table in _MASTER_DATA_TABLES gets one AFTER INSERT/UPDATE/DELETE
        STATEMENT trigger that queues the refresh cron by writing the row
        ir.cron._trigger() would have written. The cron thread wakes at most
        every 60 seconds (odoo/service/server.py, SLEEP_INTERVAL) and picks it
        up then; the notify that would wake it sooner is issued on a connection
        to the `postgres` database, which a trigger running inside this one
        cannot reach, so a poll is what this waits for.

        STATEMENT level, not ROW: one bulk UPDATE over product_category should
        queue one rebuild, not one per row, and nothing here reads NEW or OLD.

        Called last in init(), which means it is skipped on exactly the servers
        where the two early returns above skip the view itself -- no ERP feed,
        no snapshot, nothing to keep current.

        Idempotent: init() re-runs on every upgrade, and both statements below
        replace whatever was there.
        """
        cr = self._cr
        # The queue write itself. Deliberately does NOT name the cron by id:
        # ir_model_data is read at trigger time, so an uninstall/reinstall that
        # renumbers the cron does not leave a trigger pointing at nothing.
        #
        # Three ways out, all silent by design -- a trigger is not the place to
        # fail somebody's save over a dashboard that will refresh at 02:30
        # anyway: the cron does not exist (module half-installed), it is
        # switched off (an admin's decision, not to be worked around), or a
        # refresh is queued already.
        cr.execute("""
            CREATE OR REPLACE FUNCTION pbi_sales_sman_fact_mark_stale()
            RETURNS trigger LANGUAGE plpgsql AS $pbi$
            DECLARE
                v_cron integer;
                v_due  timestamp;
            BEGIN
                SELECT d.res_id INTO v_cron
                  FROM ir_model_data d
                 WHERE d.module = 'pbi_sales_dashboards'
                   AND d.name   = 'ir_cron_pbi_sales_sman_fact_refresh';
                IF v_cron IS NULL THEN
                    RETURN NULL;
                END IF;
                -- Already queued. One refresh answers every edit made before
                -- it runs, so a second row would only buy a second rebuild.
                PERFORM 1 FROM ir_cron_trigger t WHERE t.cron_id = v_cron;
                IF FOUND THEN
                    RETURN NULL;
                END IF;
                SELECT greatest(now() AT TIME ZONE 'UTC',
                                COALESCE(c.lastcall, '-infinity'::timestamp)
                                  + interval '{floor}')
                  INTO v_due
                  FROM ir_cron c
                 WHERE c.id = v_cron AND c.active;
                IF v_due IS NULL THEN
                    RETURN NULL;
                END IF;
                -- ir.cron._trigger() in SQL. call_at is UTC-naive, the way
                -- every Odoo datetime column is stored and the way
                -- _get_all_ready_jobs compares it.
                INSERT INTO ir_cron_trigger (cron_id, call_at, create_uid,
                                             create_date, write_uid, write_date)
                VALUES (v_cron, v_due, 1, now() AT TIME ZONE 'UTC',
                        1, now() AT TIME ZONE 'UTC');
                RETURN NULL;
            END;
            $pbi$
        """.format(floor=self._STALE_REBUILD_FLOOR))
        installed = []
        for table in self._MASTER_DATA_TABLES:
            # Probed, not assumed, for the same reason _OPTIONAL_TABLES is:
            # the modules that own these tables are not dependencies and need
            # not be on the server at all.
            cr.execute("SELECT to_regclass(%s)", (table,))
            if not cr.fetchone()[0]:
                continue
            # Table names come from the frozen tuple above, never from input.
            cr.execute('DROP TRIGGER IF EXISTS pbi_sman_fact_stale ON "%s"'
                       % table)
            cr.execute('CREATE TRIGGER pbi_sman_fact_stale '
                       'AFTER INSERT OR UPDATE OR DELETE ON "%s" '
                       'FOR EACH STATEMENT '
                       'EXECUTE FUNCTION pbi_sales_sman_fact_mark_stale()'
                       % table)
            installed.append(table)
        _logger.info("pbi.sales.sman.fact: master-data refresh triggers on %s",
                     ", ".join(installed) or "no table (none present)")

    def _build_budget_helpers(self):
        """The two small snapshot-derived tables v_pbi_sales_budget_live reads.

        Both were subqueries inside that view until a measurement on dbprod
        showed what they cost: each budget query a board runs was sequentially
        scanning 74,799 snapshot rows to rebuild them, ~230ms a time, several
        times per page. Precomputed here they are 8,181 rows and 10 rows, and
        the live view joins them by an indexed key instead.

        Materialised, not plain, and that is not a step back towards the
        problem this whole change set out to fix: both are derived from the
        SNAPSHOT, so they are exactly as current as it is and no more. The
        BUDGET itself -- the figures, and which tuples exist at all -- stays
        live. What is borrowed here is only how a budget tuple's level codes
        were resolved against the sales it rode, which cannot change until the
        sales do. refresh_fact rebuilds both right after the snapshot, so the
        three never disagree.
        """
        cr = self._cr
        # Per budget_key, the level codes the snapshot took from the sales row
        # rather than from the budget -- see _BUDGET_SNAPSHOT_LEVELS_SQL.
        cr.execute("""
            CREATE MATERIALIZED VIEW v_pbi_sales_budget_snap AS
            SELECT budget_key,
                   max(l7_code)  AS l7_code,  max(l7_label)  AS l7_label,
                   max(l8_code)  AS l8_code,  max(l8_label)  AS l8_label,
                   max(l7m_code) AS l7m_code, max(l7m_label) AS l7m_label,
                   max(l8m_code) AS l8m_code, max(l8m_label) AS l8m_label
            FROM v_pbi_sales_sman_fact
            WHERE budget_key IS NOT NULL
            GROUP BY budget_key
        """)
        # UNIQUE so the live view's join is a single-row lookup, and so a
        # future REFRESH ... CONCURRENTLY is allowed at all.
        cr.execute("CREATE UNIQUE INDEX pbi_budget_snap_key_idx "
                   "ON v_pbi_sales_budget_snap (budget_key)")
        cr.execute("ANALYZE v_pbi_sales_budget_snap")
        # The product groups that have in-scope sales: the whitelist that keeps
        # the target's population the same as the actuals'. Ten rows, and it was
        # costing a full scan of the snapshot on every budget query.
        cr.execute("""
            CREATE MATERIALIZED VIEW v_pbi_sales_scope_groups AS
            SELECT DISTINCT l9_code::int AS l9_code
            FROM v_pbi_sales_sman_fact
            WHERE l9_code IS NOT NULL AND in_scope
        """)
        cr.execute("CREATE UNIQUE INDEX pbi_scope_groups_idx "
                   "ON v_pbi_sales_scope_groups (l9_code)")
        cr.execute("ANALYZE v_pbi_sales_scope_groups")

    def _build_budget_live_view(self, stubs):
        """The TARGET, read live instead of out of the snapshot.

        The snapshot is rebuilt once a night because the ACTUALS behind it cost
        16 seconds to compute. The budget costs almost nothing -- it is a small
        table and six lookups -- and yet, riding inside the same snapshot, a
        target typed in this morning did not reach a chart until 02:30 the next
        day. This view carries the budget half on its own so the boards can read
        it at request time; the actuals stay snapshotted, which is right,
        because yesterday's invoices do not change either.

        Built from _BUDGET_CTE_SQL, the very text the snapshot builds its budget
        from, so the two cannot answer differently. What it does NOT recompute
        is the level codes the snapshot takes from the sales row a budget tuple
        rides -- see _BUDGET_SNAPSHOT_LEVELS_SQL for why that distinction is
        worth SAR 505m -- and the product-group whitelist, which reads the same
        rows back off the snapshot rather than re-deriving them from the
        actuals query this view exists to avoid running.
        """
        cr = self._cr
        cr.execute("""
            CREATE OR REPLACE VIEW v_pbi_sales_budget_live AS
            WITH {stubs}cust AS (
                SELECT c.cst_no, COALESCE(c.cst_name, cd.cst_name) AS cst_name
                FROM customer c
                LEFT JOIN (SELECT DISTINCT ON (cst_no) cst_no, cst_name
                           FROM customerdesc
                           ORDER BY cst_no, cst_lang) cd ON cd.cst_no = c.cst_no
            ),
            budget AS (
{budget_cte}
            ),
            keyed AS (
                -- Literally the snapshot's own key now: both sites interpolate
                -- _BUDGET_KEY_SQL, so they cannot drift apart or away from the
                -- grain of the CTE above. See that constant for what a key
                -- coarser than the grain costs.
                SELECT b.*, {budget_key} AS budget_key
                FROM budget b
            )
            SELECT k.yr, k.mth, k.budget_key, k.budget_qty, k.budget_value,
                   k.franchise_code,
                   k.l1_code::text AS budget_l1_code, sgb.salgrp_name AS budget_l1_label,
                   k.l2_code::text AS l2_code,
                   COALESCE(NULLIF(pcl.pc_classification1,''), pcl.complete_name) AS l2_label,
                   k.l3_code::text AS l3_code, {region_name} AS l3_label,
                   k.l4_code::text AS l4_code, {city_name} AS l4_label,
                   k.l5_code::text AS l5_code, COALESCE(sman.name, k.l5_code::text) AS l5_label,
                   k.l6_code, COALESCE(cu.cst_name, k.l6_code) AS l6_label,
                   COALESCE(snap.l7_code, k.l7_code::text)   AS l7_code,
                   COALESCE(snap.l7_label, kmc.maincat_name) AS l7_label,
                   COALESCE(snap.l8_code, k.l8_code::text)   AS l8_code,
                   COALESCE(snap.l8_label, ksc.subcat_name)  AS l8_label,
                   COALESCE(snap.l7m_code, k.l7m_code::text)   AS l7m_code,
                   COALESCE(snap.l7m_label, kmcm.maincat_name) AS l7m_label,
                   COALESCE(snap.l8m_code, k.l8m_code::text)   AS l8m_code,
                   COALESCE(snap.l8m_label, kscm.subcat_name)  AS l8m_label,
                   k.l9_code::text AS l9_code, CASE WHEN UPPER(COALESCE(pg.name, '')) IN ('ACWTSPLIT', 'ACWTS') OR COALESCE(pg.code, '') = 'ACWTS' OR UPPER(COALESCE(pg.name, '')) LIKE '%ACWTSPLIT%' THEN 'Split' ELSE pg.name END AS l9_label,
                   k.lfam_code::text AS lfam_code, kfam.pfam_name AS lfam_label
            FROM keyed k
            LEFT JOIN salestypes_group       sgb  ON sgb.id = k.l1_code
            LEFT JOIN partner_classification pcl  ON pcl.id = k.l2_code
            LEFT JOIN res_region             rreg ON rreg.id = k.l3_code
            LEFT JOIN res_city               city ON city.id = k.l4_code
            LEFT JOIN res_partner            sman ON sman.id = k.l5_code
            LEFT JOIN cust                   cu   ON cu.cst_no = k.l6_code
            LEFT JOIN product_category       pg   ON pg.id = k.l9_code
            LEFT JOIN product_family         kfam ON kfam.id = k.lfam_code
{snapshot_levels}
        """.format(
            stubs=stubs,
            budget_key=_BUDGET_KEY_SQL,
            budget_cte=_BUDGET_CTE_SQL.format(
                budget_salesman=optional_schema.column_ref(
                    cr, 'v_sales_budget_month', 'salesman_partner_id', 'integer',
                    alias='b'),
                budget_erp_subgroup=optional_schema.column_ref(
                    cr, 'v_sales_budget_month', 'erp_subgroup_code', 'varchar',
                    alias='b'),
                fam_merged_bfam=optional_schema.column_ref(
                    cr, 'product_family', 'pfam_merged_into', 'integer',
                    alias='bfam'),
                single_family_group=_SINGLE_FAMILY_GROUP_SQL.format(
                    pcat_family_col_c=optional_schema.column_ref(
                        cr, 'product_category', 'product_family', 'integer',
                        alias='c')),
                group_whitelist="SELECT l9_code FROM v_pbi_sales_scope_groups",
                pcat_sub_bpc=optional_schema.column_ref(cr, 'product_category', 'sub_category', 'integer', alias='bpc'),
                pcat_merged_bpc=optional_schema.column_ref(cr, 'product_category', 'merged_subcategory', 'integer', alias='bpc')),
            snapshot_levels=_BUDGET_SNAPSHOT_LEVELS_SQL,
            region_name=board_sql._translated_text_expr("rreg.name", "en_US"),
            city_name=board_sql._translated_text_expr("city.name", "en_US"),
        ))

    @api.model
    def refresh_fact(self):
        """Rebuild the snapshot. CONCURRENTLY so readers are never blocked; it
        falls back to a plain refresh on the very first run, when the view has
        never been populated and CONCURRENTLY is not allowed."""
        cr = self._cr
        # STAND DOWN IF A REBUILD IS ALREADY RUNNING. Try, never wait: this is
        # a cron thread, and blocking it for the length of a bring-up would
        # hold a worker to do work that is about to be thrown away -- init()
        # re-CREATEs the matview WITH DATA, so it repopulates anyway. The
        # requeue below is what makes standing down safe: whatever edit queued
        # this run is still answered, one poll later.
        if not self._try_rebuild_lock():
            _logger.info("pbi.sales.sman.fact: another rebuild holds the "
                         "snapshot lock, skipping this refresh and requeueing.")
            self.queue_refresh()
            return True
        # Same planner settings init() needs, and for the same reason -- a
        # REFRESH re-runs the view's own query. Re-applied after the rollback
        # below because a rollback discards SET LOCAL along with everything
        # else in the transaction.
        self._apply_planner_hints()
        try:
            cr.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY v_pbi_sales_sman_fact")
        except Exception:
            cr.rollback()
            # The rollback dropped the advisory lock with everything else, and
            # the plain REFRESH below is the half that takes ACCESS EXCLUSIVE
            # -- exactly the lock this is here to order. Re-take it, and wait
            # this time: the work is already begun and the snapshot is now
            # unrefreshed either way.
            self._take_rebuild_lock()
            self._apply_planner_hints()
            cr.execute("REFRESH MATERIALIZED VIEW v_pbi_sales_sman_fact")
        cr.execute("ANALYZE v_pbi_sales_sman_fact")
        # The two derived tables are rebuilt with it: they are snapshot-shaped,
        # so leaving them behind would let the live view resolve a budget
        # tuple's levels against sales that have since moved.
        cr.execute("REFRESH MATERIALIZED VIEW v_pbi_sales_budget_snap")
        cr.execute("ANALYZE v_pbi_sales_budget_snap")
        cr.execute("REFRESH MATERIALIZED VIEW v_pbi_sales_scope_groups")
        cr.execute("ANALYZE v_pbi_sales_scope_groups")
        return True

    _REFRESH_CRON_XMLID = 'pbi_sales_dashboards.ir_cron_pbi_sales_sman_fact_refresh'

    @api.model
    def queue_refresh(self):
        """Ask the cron for a rebuild. NEVER rebuilds here, and that is the point.

        refresh_fact() is ~16s of database CPU on dbprod. Called from an HTTP
        request it holds a worker for that long and a transaction open across
        it, and on an instance with few workers a couple of impatient clicks
        stall the lot -- which is what running the REFRESH by hand in a SQL
        client did on staging.

        So this writes the same queue row ir.cron._trigger() writes, and
        returns. The cron thread polls every 60 seconds
        (odoo/service/server.py, SLEEP_INTERVAL) and does the work in its own
        thread, off the request path. The board polls refresh_status() to watch
        it land.

        Deliberately shares every rule with the master-data triggers in
        _install_master_data_triggers, because a button able to bypass them
        would be a way to hammer the database that editing a product category
        is not:

        * ALREADY QUEUED -> say so, write nothing. One rebuild answers every
          request made before it runs; a second row buys only a second rebuild.
        * CRON INACTIVE -> report and stop. Switching that cron off is an
          admin's decision about database load, and a dashboard button is not
          the place to overrule it.
        * FLOOR -> the queued time is never sooner than the last run plus
          _STALE_REBUILD_FLOOR, so no amount of clicking rebuilds faster than
          once a minute.

        Returns a dict the board renders as-is. Never raises for an expected
        state: "the cron is off" is information, not an error.
        """
        cron = self.env.ref(self._REFRESH_CRON_XMLID, raise_if_not_found=False)
        if not cron:
            return {'state': 'unavailable',
                    'message': 'The refresh job is not installed on this server.'}
        # sudo: a dashboard reader may not read ir.cron, and who may ask for a
        # refresh is decided by the menu check in the controller, not by
        # ir.cron's own ACL.
        cron = cron.sudo()
        last_run = cron.lastcall.isoformat() if cron.lastcall else None
        if not cron.active:
            return {'state': 'cron_off', 'last_run': last_run,
                    'message': 'The scheduled refresh is switched off. '
                               'An administrator must re-enable it.'}
        queued_at = self._queued_at(cron)
        if queued_at:
            return {'state': 'already_queued', 'last_run': last_run,
                    'due': queued_at.isoformat(),
                    'message': 'A refresh is already queued.'}
        # One source of truth for the floor: the triggers interpolate the same
        # string into SQL as an interval.
        floor = timedelta(seconds=int(self._STALE_REBUILD_FLOOR.split()[0]))
        now = fields.Datetime.now()
        due = max(now, cron.lastcall + floor) if cron.lastcall else now
        cron._trigger(at=due)
        return {'state': 'queued', 'last_run': last_run,
                'due': due.isoformat(),
                'message': 'Refresh queued. It runs within about a minute.'}

    @api.model
    def refresh_status(self):
        """When the snapshot last rebuilt, and whether one is pending.

        Cheap enough for the board to poll while it waits: one indexed read on
        ir_cron_trigger and one field off ir_cron. It never touches the view.
        """
        cron = self.env.ref(self._REFRESH_CRON_XMLID, raise_if_not_found=False)
        if not cron:
            return {'state': 'unavailable', 'last_run': None, 'due': None}
        cron = cron.sudo()
        queued_at = self._queued_at(cron)
        return {
            'state': ('pending' if queued_at
                      else 'cron_off' if not cron.active
                      else 'idle'),
            'due': queued_at.isoformat() if queued_at else None,
            # lastcall is when the cron last RAN, which is when the snapshot
            # last rebuilt -- every path that rebuilds it goes through this job.
            # A REFRESH run by hand in a SQL client does NOT move it, so read
            # this as "last refreshed by the system", not "last refreshed".
            'last_run': cron.lastcall.isoformat() if cron.lastcall else None,
        }

    @api.model
    def _queued_at(self, cron):
        """Earliest pending trigger for ``cron``, or None."""
        self.env.cr.execute(
            "SELECT min(call_at) FROM ir_cron_trigger WHERE cron_id = %s",
            (cron.id,))
        return self.env.cr.fetchone()[0]
