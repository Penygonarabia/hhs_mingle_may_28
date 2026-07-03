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


# KS stores each item's measure / list-column selections both as a real
# many2many onto ir.model.fields AND, redundantly, as raw field ids embedded
# in the ks_many2many_field_ordering JSON blob. ks_import_dashboard remaps the
# m2m by name to the importing DB, but the ordering blob is copied verbatim and
# the m2m ids themselves rot whenever a *source* module is reinstalled (which
# renumbers ir.model.fields). A stale id makes KS raise
# "MissingError: ir.model.fields(<id>,)" the moment the board is opened.
#
# Each tuple: (m2m field on the item, sibling *_name key in the ordering blob).
_MEASURE_FIELD_KEYS = [
    ("ks_chart_measure_field",     "ks_chart_measure_field_name"),
    ("ks_chart_measure_field_2",   "ks_chart_measure_field_2_name"),
    ("ks_list_view_fields",        "ks_list_view_fields_name"),
    ("ks_list_view_group_fields",  "ks_list_view_group_fields_name"),
]


def _heal_item_field_ids(env, board):
    """Re-resolve every item's measure/list field ids **by name** against the
    current DB, repairing both the ordering blob and the raw m2m relation.

    KS's custom ``ks_read`` (see ks_dashboard_ninja_items.py) rebuilds these
    four many2many fields *from the ks_many2many_field_ordering blob* whenever
    it is present, so the blob is the real source of truth and a stale id there
    is what makes the board crash with MissingError. We also rewrite the
    underlying relation table by SQL: the ORM's own many2many write is a no-op
    here (it diffs against the blob-synthesised value, which we have already
    healed), so it would otherwise leave the dangling relation row behind.

    Idempotent and cheap: if the stored ids already match the resolved ids the
    item is left untouched. This is what keeps the promoter boards immune to
    ir.model.fields renumbering after a source-module reinstall.
    """
    Field = env["ir.model.fields"].sudo()
    for item in board.ks_dashboard_items_ids:
        model = item.ks_model_id.model
        if not model:
            continue
        try:
            ordering = json.loads(item.ks_many2many_field_ordering or "{}")
        except ValueError:
            continue

        changed = False
        for id_key, name_key in _MEASURE_FIELD_KEYS:
            names = ordering.get(name_key) or []
            if not names:
                continue
            # Resolve by name, preserving the author's column order and
            # dropping any name that no longer exists on the model.
            resolved = []
            for name in names:
                fld = Field.search(
                    [("model", "=", model), ("name", "=", name)], limit=1
                )
                if fld:
                    resolved.append(fld.id)
            if resolved == (ordering.get(id_key) or []):
                continue
            ordering[id_key] = resolved
            changed = True

            # Rewrite the relation table directly; the ORM write path can't be
            # trusted to update it (no-op diff against the synthesised value).
            m2m = item._fields[id_key]
            env.cr.execute(
                'DELETE FROM "%s" WHERE "%s" = %%s'
                % (m2m.relation, m2m.column1),
                (item.id,),
            )
            if resolved:
                env.cr.execute(
                    'INSERT INTO "%s" ("%s", "%s") '
                    "SELECT %%s, unnest(%%s)"
                    % (m2m.relation, m2m.column1, m2m.column2),
                    (item.id, resolved),
                )

        if changed:
            item.ks_many2many_field_ordering = json.dumps(ordering)
            item.invalidate_recordset()
            _logger.info(
                "promoter_dashboards: healed stale field ids on item %s.",
                item.id,
            )


def _read_menu_name(payload):
    try:
        decoded = json.loads(payload)
        return decoded["ks_dashboard_data"][0]["ks_dashboard_menu_name"]
    except (ValueError, KeyError, IndexError):
        return None


def heal_promoter_boards(env):
    """Heal the promoter boards' stale measure field ids.

    Shared by post_init_hook (runs on install) and the post-migrate script
    (runs on ``-u`` upgrade), so either path repairs an already-broken board.
    Resolves each board by the menu name stored in its JSON snapshot so it is
    not tied to any DB id.
    """
    Board = env["ks_dashboard_ninja.board"]
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    for fname, _sequence, _xmlid_suffix in DASHBOARDS:
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            continue
        with open(path, "rb") as fh:
            menu_name = _read_menu_name(fh.read())
        if not menu_name:
            continue
        board = Board.search(
            [("ks_dashboard_menu_name", "=", menu_name)], limit=1
        )
        if board:
            _heal_item_field_ids(env, board)


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

        # Repair any measure/list field ids that rotted since the last install
        # (source-module reinstall renumbers ir.model.fields). Runs on both the
        # fresh-import and reuse paths so re-running `-i promoter_dashboards`
        # fixes an already-broken board.
        _heal_item_field_ids(env, board)

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
            # Also align ks_dashboard_top_menu_id with the menu's actual
            # parent — ks_import_dashboard sets it to board_menu_root, which
            # leaves the board form / dashboard-rights category grouping
            # showing the wrong parent and trips the menu-visibility
            # walk-up in dashboard_rights.
            board_vals = {"ks_dashboard_top_menu_id": promoter_dashboards_menu.id}
            if board.ks_dashboard_menu_id.id != placeholder_menu.id:
                board_vals["ks_dashboard_menu_id"] = placeholder_menu.id
            board.write(board_vals)
            if board.ks_dashboard_menu_id.id == placeholder_menu.id and live_menu and live_menu.id != placeholder_menu.id:
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
            board.write({
                "ks_dashboard_menu_id": live_menu.id,
                "ks_dashboard_top_menu_id": promoter_dashboards_menu.id,
            })
        else:
            live_menu.write({
                "parent_id": promoter_dashboards_menu.id,
                "sequence": sequence,
                "active": True,
                "action": action_ref,
            })
            board.write({"ks_dashboard_top_menu_id": promoter_dashboards_menu.id})

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
