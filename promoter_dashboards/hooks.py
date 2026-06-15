"""promoter_dashboards / hooks.

post_init_hook imports the two KS Dashboard Ninja boards
("Promoters", "Promoter - Sales Comparison") from JSON snapshots in
data/, then attaches the imported boards' actions onto the XML-declared
placeholder menus under "My Dashboard > Promoter Dashboards".

Re-running this hook (e.g. via `-i promoter_dashboards` after the first
install) is safe: if a board with the same `ks_dashboard_menu_name`
already exists, the import is skipped and we just (re)wire the menu.

The XML in views/promoter_dashboard_menus.xml creates the placeholder
menus with stable xmlids but no action; this hook is what makes them
actually open something. If the hook does not run (or aborts), Odoo
hides those leaf menus and "Promoter Dashboards" renders as an empty
parent.
"""

import json
import logging
import os

_logger = logging.getLogger(__name__)


# Each tuple: (json file in data/, sequence under Promoter Dashboards menu,
# xmlid suffix of the placeholder menu declared in
# views/promoter_dashboard_menus.xml).
DASHBOARDS = [
    ("promoters_analysis.json",        10, "menu_promoter_dashboard_promoters"),
    ("promoter_sales_comparison.json", 20, "menu_promoter_dashboard_sales_comparison"),
]


def _read_menu_name(payload):
    try:
        decoded = json.loads(payload)
        return decoded["ks_dashboard_data"][0]["ks_dashboard_menu_name"]
    except (ValueError, KeyError, IndexError):
        return None


def _resolve_placeholder(env, xmlid_suffix):
    """Return the placeholder ir.ui.menu, healing a stale ir.model.data row
    that points to a deleted menu by deleting the orphan row."""
    ModelData = env["ir.model.data"]
    Menu = env["ir.ui.menu"]
    md = ModelData.search([
        ("module", "=", "promoter_dashboards"),
        ("name", "=", xmlid_suffix),
    ], limit=1)
    if not md:
        return None, None
    menu = Menu.browse(md.res_id).exists()
    if not menu:
        _logger.warning(
            "promoter_dashboards: xmlid %s points to deleted menu id=%s; pruning.",
            xmlid_suffix, md.res_id,
        )
        md.unlink()
        return None, None
    return md, menu


def _ensure_client_action(env, board, live_menu):
    """Return a usable ir.actions.client for the board, creating one if the
    board has no client action and we cannot recover it from the live menu."""
    ClientAction = env["ir.actions.client"].sudo()

    action = board.ks_dashboard_client_action_id
    if action:
        return action

    if live_menu and live_menu.action:
        # menu.action is a Reference field "ir.actions.client,<id>"
        try:
            model_name, action_id = live_menu.action.split(",")
            recovered = env[model_name].browse(int(action_id)).exists()
            if recovered:
                board.ks_dashboard_client_action_id = recovered
                return recovered
        except (ValueError, KeyError):
            pass

    action = ClientAction.create({
        "name": board.ks_dashboard_menu_name + " Action",
        "res_model": "ks_dashboard_ninja.board",
        "tag": "ks_dashboard_ninja",
        "params": {
            "ks_dashboard_id": board.id,
            "ks_dashboard_name": board.ks_dashboard_menu_name,
        },
    })
    board.ks_dashboard_client_action_id = action
    return action


def post_init_hook(env):
    """Import the 2 JSON dashboards and wire their actions onto the
    placeholder menus under "My Dashboard > Promoter Dashboards"."""
    Board = env["ks_dashboard_ninja.board"]
    ModelData = env["ir.model.data"]

    my_dashboard = env.ref("ks_dashboard_ninja.board_menu_root", raise_if_not_found=False)
    if not my_dashboard:
        _logger.warning(
            "promoter_dashboards: ks_dashboard_ninja.board_menu_root not found; "
            "skipping import."
        )
        return

    promoter_dashboards_menu = env.ref(
        "promoter_dashboards.promoter_dashboards_menu_root", raise_if_not_found=False
    )
    if not promoter_dashboards_menu:
        _logger.error(
            "promoter_dashboards: promoter_dashboards_menu_root xmlid missing — "
            "views/promoter_dashboard_menus.xml did not load. Aborting hook."
        )
        return

    data_dir = os.path.join(os.path.dirname(__file__), "data")

    for fname, sequence, xmlid_suffix in DASHBOARDS:
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            _logger.warning("promoter_dashboards: %s missing; skipping.", fname)
            continue

        with open(path, "rb") as fh:
            payload = fh.read()

        menu_name = _read_menu_name(payload)
        if not menu_name:
            _logger.warning(
                "promoter_dashboards: cannot read ks_dashboard_menu_name from %s; "
                "skipping.", fname,
            )
            continue

        # Find-or-import the board. Idempotent: a second install reuses
        # the existing board instead of duplicating it.
        board = Board.search([("ks_dashboard_menu_name", "=", menu_name)], limit=1)
        if board:
            _logger.info("promoter_dashboards: '%s' already present; reusing.", menu_name)
        else:
            _logger.info("promoter_dashboards: importing %s ...", fname)
            try:
                Board.ks_import_dashboard(payload, my_dashboard)
            except Exception:
                _logger.exception(
                    "promoter_dashboards: ks_import_dashboard failed for %s; skipping.",
                    fname,
                )
                continue
            board = Board.search([("ks_dashboard_menu_name", "=", menu_name)], limit=1)

        if not board:
            _logger.warning(
                "promoter_dashboards: board '%s' not found after import; skipping.",
                menu_name,
            )
            continue

        live_menu = board.ks_dashboard_menu_id  # auto-created by Board.create()
        md, placeholder_menu = _resolve_placeholder(env, xmlid_suffix)

        # Ensure we have a client action to attach to whichever menu wins.
        client_action = _ensure_client_action(env, board, live_menu)
        action_ref = "ir.actions.client,%d" % client_action.id

        if placeholder_menu:
            # Wire the placeholder: correct parent, sequence, action, active.
            placeholder_menu.write({
                "parent_id": promoter_dashboards_menu.id,
                "sequence": sequence,
                "active": True,
                "action": action_ref,
            })
            # Point the board at the placeholder so subsequent board edits
            # (rename, group-access, etc.) keep flowing onto the stable xmlid.
            if board.ks_dashboard_menu_id.id != placeholder_menu.id:
                board.write({"ks_dashboard_menu_id": placeholder_menu.id})
                if live_menu and live_menu.id != placeholder_menu.id:
                    try:
                        live_menu.unlink()
                    except Exception:
                        _logger.warning(
                            "promoter_dashboards: could not unlink duplicate menu %s.",
                            live_menu.id,
                        )
            _logger.info(
                "promoter_dashboards: wired placeholder %s -> board %s (menu=%s, action=%s).",
                xmlid_suffix, board.id, placeholder_menu.id, client_action.id,
            )
            continue

        # No placeholder (XML somehow skipped, or stale row pruned).
        # Fall back to adopting the live menu under our xmlid namespace so
        # the user still gets a working menu.
        if not live_menu:
            _logger.warning(
                "promoter_dashboards: no placeholder and no live menu for '%s'; "
                "creating one.", menu_name,
            )
            live_menu = env["ir.ui.menu"].sudo().create({
                "name": menu_name,
                "parent_id": promoter_dashboards_menu.id,
                "sequence": sequence,
                "action": action_ref,
            })
            board.write({"ks_dashboard_menu_id": live_menu.id})
        else:
            live_menu.write({
                "parent_id": promoter_dashboards_menu.id,
                "sequence": sequence,
                "active": True,
                "action": action_ref,
            })

        ModelData.create({
            "module": "promoter_dashboards",
            "name": xmlid_suffix,
            "model": "ir.ui.menu",
            "res_id": live_menu.id,
            "noupdate": True,
        })
        _logger.info(
            "promoter_dashboards: adopted live menu %s under xmlid %s.",
            live_menu.id, xmlid_suffix,
        )
