"""promoter_dashboards / hooks.

post_init_hook imports the three KS Dashboard Ninja boards
("Promoters", "Promoter - Sales Comparison", "Sales Target") from JSON
snapshots in data/, then reparents each board's auto-created menu under
"My Dashboard > Promoter Dashboards" and adopts those menus into this
module so subsequent module upgrades don't blow them away.

The JSON files are produced by the standard "Export Dashboard" button
inside KS Dashboard Ninja and re-imported here through the same
`ks_import_dashboard()` API the wizard uses — so the format is identical.

Re-running this hook (e.g. via `-i promoter_dashboards` after the first
install) is safe: if a board with the same `ks_dashboard_menu_name`
already exists, the import is skipped.
"""

import json
import logging
import os

_logger = logging.getLogger(__name__)


# Each tuple: (json file in data/, sequence under Promoter Dashboards menu,
# xmlid suffix to register the menu under in ir_model_data).
#
# The Sales Target board was renamed in-place to "Promoter - Sales Comparison"
# and the original 4-item "Sales Comparison (Actual vs Target)" board was
# removed — so only TWO dashboards are shipped here now, despite three menus
# being declared in views/promoter_dashboard_menus.xml. (That XML is kept as
# placeholder shell only; the post_init_hook adopts whichever live menus the
# imports create.)
DASHBOARDS = [
    ("promoters_analysis.json",        10, "menu_promoter_dashboard_promoters"),
    ("promoter_sales_comparison.json", 20, "menu_promoter_dashboard_sales_comparison"),
]


def post_init_hook(env):
    """Import the 3 JSON dashboards and place their menus under Promoter Dashboards."""
    Board = env["ks_dashboard_ninja.board"]
    Menu = env["ir.ui.menu"]
    ModelData = env["ir.model.data"]

    # Parent menu under which the imported boards' menus must live.
    # board_menu_root = "My Dashboard" — used as `menu_id` for the import call.
    my_dashboard = env.ref("ks_dashboard_ninja.board_menu_root", raise_if_not_found=False)
    if not my_dashboard:
        _logger.warning("promoter_dashboards: ks_dashboard_ninja.board_menu_root not found; skipping import.")
        return
    promoter_dashboards_menu = env.ref(
        "promoter_dashboards.promoter_dashboards_menu_root", raise_if_not_found=False
    )
    if not promoter_dashboards_menu:
        _logger.warning(
            "promoter_dashboards: promoter_dashboards_menu_root not found; menus will stay at root."
        )

    data_dir = os.path.join(os.path.dirname(__file__), "data")

    for fname, sequence, xmlid_suffix in DASHBOARDS:
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            _logger.warning("promoter_dashboards: %s missing; skipping.", fname)
            continue

        with open(path, "rb") as fh:
            payload = fh.read()

        # Skip if a board with the same menu_name is already present —
        # this hook is idempotent so `-i promoter_dashboards` after the
        # first install doesn't duplicate the boards.
        try:
            decoded = json.loads(payload)
            menu_name = decoded["ks_dashboard_data"][0]["ks_dashboard_menu_name"]
        except (ValueError, KeyError, IndexError):
            menu_name = None
        if menu_name and Board.search_count([("ks_dashboard_menu_name", "=", menu_name)]):
            _logger.info("promoter_dashboards: '%s' already imported; skipping %s.", menu_name, fname)
            board = Board.search([("ks_dashboard_menu_name", "=", menu_name)], limit=1)
        else:
            _logger.info("promoter_dashboards: importing %s ...", fname)
            Board.ks_import_dashboard(payload, my_dashboard)
            board = Board.search([("ks_dashboard_menu_name", "=", menu_name)], limit=1)

        # Now consolidate menus. The XML placeholders (created by
        # views/promoter_dashboard_menus.xml with the xmlid we own) have NO
        # action; the auto-created menus from ks_import_dashboard have the
        # action but no xmlid. We want ONE menu per board: the placeholder
        # (keeps the stable xmlid) WITH the action attached.
        if board and board.ks_dashboard_menu_id and promoter_dashboards_menu:
            new_menu = board.ks_dashboard_menu_id   # has action, no xmlid
            placeholder = ModelData.search([
                ("module", "=", "promoter_dashboards"),
                ("name", "=", xmlid_suffix),
            ], limit=1)
            if placeholder and placeholder.res_id != new_menu.id:
                # Copy the action onto the placeholder, reparent + sequence,
                # delete the duplicate new menu, and point the board at the
                # placeholder so future upgrades stay consistent.
                placeholder_menu = Menu.browse(placeholder.res_id)
                placeholder_menu.write({
                    "parent_id": promoter_dashboards_menu.id,
                    "sequence": sequence,
                    "action": new_menu.action,
                })
                board.write({"ks_dashboard_menu_id": placeholder_menu.id})
                new_menu.unlink()
            else:
                # No placeholder existed — just reparent the new menu and
                # adopt it into this module's xmlids.
                new_menu.write({
                    "parent_id": promoter_dashboards_menu.id,
                    "sequence": sequence,
                })
                ModelData.create({
                    "module": "promoter_dashboards",
                    "name": xmlid_suffix,
                    "model": "ir.ui.menu",
                    "res_id": new_menu.id,
                    "noupdate": True,
                })
