"""Apply per-item chart palettes that mirror the Ninja_Themes_Dashboards JSONs.

Until 17.0.1.2.0 all OT chart items used the single `moonrise` palette. The
reference dashboards in OneDrive (Ninja_Themes_Dashboards/*.json) actually mix
moonrise / default / material per chart. This migration writes the per-xmlid
palette assignment so the live DB matches the data XML — which is noupdate=1
and so would otherwise NOT be re-applied on a plain `-u`.

The map is the source of truth; the XML files were updated in lock-step.
"""
from odoo import api, SUPERUSER_ID


# xmlid (without module prefix) -> chart palette code
ITEM_PALETTE = {
    "bar_cc_tasks_monthwise": "moonrise",
    "bar_crd_tasks_monthwise": "moonrise",
    "bar_crd_tasks_userrole": "moonrise",
    "bar_parts_cust_need_quote_hours": "default",
    "bar_parts_onhold_sp_req_hours": "default",
    "bar_parts_tasks_monthwise": "default",
    "bar_tech_tasks_monthwise": "moonrise",
    "bar_tech_travel_hours": "default",
    "kpi_cc_new_tasks": "moonrise",
    "kpi_crd_closed_tasks": "moonrise",
    "kpi_crd_scheduled_tasks": "moonrise",
    "kpi_parts_cust_need_quote": "moonrise",
    "kpi_parts_onhold_sp_req": "moonrise",
    "kpi_tech_need_reschedule": "moonrise",
    "kpi_tech_parts_ready_reschedule": "moonrise",
    "kpi_tech_req_revisit": "moonrise",
    "kpi_tech_rescheduled": "moonrise",
    "legacy_item_454": "moonrise",
    "legacy_item_455": "moonrise",
    "legacy_item_456": "moonrise",
    "legacy_item_457": "moonrise",
    "legacy_item_458": "moonrise",
    "legacy_item_459": "moonrise",
    "legacy_item_460": "default",
    "legacy_item_461": "material",
    "legacy_item_462": "default",
    "legacy_item_463": "moonrise",
    "legacy_item_464": "material",
    "legacy_item_465": "material",
    "legacy_item_479": "moonrise",
    "legacy_item_480": "moonrise",
    "legacy_item_481": "moonrise",
    "legacy_item_482": "moonrise",
    "legacy_item_483": "moonrise",
    "legacy_item_484": "moonrise",
    "legacy_item_485": "default",
    "legacy_item_486": "material",
    "legacy_item_487": "moonrise",
    "legacy_item_488": "material",
    "legacy_item_489": "default",
    "legacy_item_490": "moonrise",
    "legacy_item_491": "moonrise",
    "legacy_item_492": "moonrise",
    "legacy_item_493": "moonrise",
    "legacy_item_494": "moonrise",
    "legacy_item_495": "moonrise",
    "legacy_item_496": "default",
    "legacy_item_497": "material",
    "legacy_item_498": "moonrise",
    "legacy_item_499": "material",
    "legacy_item_500": "default",
    "legacy_item_501": "moonrise",
    "legacy_item_502": "moonrise",
    "legacy_item_503": "moonrise",
    "legacy_item_504": "moonrise",
    "legacy_item_505": "moonrise",
    "legacy_item_506": "moonrise",
    "legacy_item_507": "default",
    "legacy_item_508": "material",
    "legacy_item_509": "moonrise",
    "legacy_item_510": "material",
    "legacy_item_511": "default",
    "legacy_item_539": "moonrise",
    "legacy_item_540": "moonrise",
    "legacy_item_541": "moonrise",
    "legacy_item_542": "moonrise",
    "legacy_item_543": "moonrise",
    "legacy_item_551": "moonrise",
    "legacy_item_552": "default",
    "legacy_item_553": "moonrise",
    "legacy_item_554": "material",
    "legacy_item_555": "moonrise",
    "legacy_item_556": "default",
    "legacy_item_558": "default",
    "legacy_item_562": "moonrise",
    "legacy_item_563": "moonrise",
    "legacy_item_565": "moonrise",
    "legacy_item_567": "material",
    "legacy_item_568": "default",
    "legacy_item_569": "moonrise",
    "legacy_item_570": "moonrise",
    "legacy_item_571": "moonrise",
    "legacy_item_572": "moonrise",
    "legacy_item_580": "moonrise",
    "legacy_item_581": "moonrise",
    "legacy_item_583": "default",
    "legacy_item_586": "material",
    "legacy_item_587": "moonrise",
    "legacy_item_588": "default",
    "legacy_item_589": "moonrise",
    "legacy_item_590": "material",
    "legacy_item_591": "moonrise",
    "legacy_item_592": "default",
    "legacy_item_593": "moonrise",
    "legacy_item_623": "moonrise",
    "legacy_item_624": "moonrise",
    "legacy_item_625": "moonrise",
    "legacy_item_626": "moonrise",
    "legacy_item_627": "default",
    "legacy_item_628": "material",
    "legacy_item_629": "material",
    "legacy_item_630": "material",
    "legacy_item_631": "material",
    "legacy_item_632": "default",
    "legacy_item_633": "default",
    "legacy_item_634": "moonrise",
    "legacy_item_635": "moonrise",
    "legacy_item_636": "default",
    "legacy_item_637": "material",
    "legacy_item_638": "default",
    "legacy_item_639": "moonrise",
    "legacy_item_640": "moonrise",
    "legacy_item_641": "material",
    "legacy_item_642": "moonrise",
    "legacy_item_643": "moonrise",
    "legacy_item_644": "moonrise",
    "legacy_item_645": "moonrise",
    "legacy_item_646": "moonrise",
    "legacy_item_647": "material",
    "legacy_item_648": "default",
    "legacy_item_666": "default",
    "legacy_item_668": "material",
    "legacy_item_669": "material",
    "legacy_item_670": "material",
    "legacy_item_671": "default",
    "legacy_item_697": "default",
    "legacy_item_698": "default"
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Resolve xmlid -> record id in one query for items present in the DB
    xmlids = env['ir.model.data'].search([
        ('module', '=', 'service_dashboards_ot'),
        ('model', '=', 'ks_dashboard_ninja.item'),
        ('name', 'in', list(ITEM_PALETTE.keys())),
    ])
    name_to_id = {x.name: x.res_id for x in xmlids}
    # Group items by target palette so we issue at most 3 writes
    by_palette = {}
    for xid, palette in ITEM_PALETTE.items():
        rid = name_to_id.get(xid)
        if rid:
            by_palette.setdefault(palette, []).append(rid)

    Item = env['ks_dashboard_ninja.item']
    for palette, ids in by_palette.items():
        items = Item.browse(ids).filtered(lambda r: r.ks_chart_item_color != palette)
        if items:
            items.write({'ks_chart_item_color': palette})
