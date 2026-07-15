"""Purge the cached web.assets_* bundle; bring My Dashboard's menus into
Module Rights Setup and correct a transient bug from 17.0.2.0.0.

Covers 17.0.2.0.1: Module Rights Setup now also lists the My Dashboard app
(boards, Quick Access, Configuration) instead of excluding it, and the two
grants a KS board has — dashboard.rights (board-level, Users Setup) and
dashboard.rights.menu (menu-level, this page) — are kept in sync going
forward via dashboard.rights.menu._dr_sync_board_and_menu.

This migration does two things:

1. Grandfathers every currently active user onto every NON-board menu in
   the My Dashboard tree that's newly in scope (the app root itself, and
   its category folders like "Service Dashboards - CT") — the same
   blanket "was implicitly visible, nothing explicit before" baseline
   17.0.2.0.0 already applied to every other app. Quick Access/
   Configuration sub-items already have real historical grants and are
   left untouched (create-if-missing only).

2. CORRECTS every KS board's dashboard.rights.menu row to match that
   board's real, existing dashboard.rights.has_access for each user —
   overwriting, not just filling gaps. This fixes a bug in an earlier,
   never-released iteration of 17.0.2.0.0's own migration: it briefly
   excluded the wrong xmlid (a category folder one level below the real
   My Dashboard app root) so the root's own exclusion never took effect,
   and every board ended up blanket-granted to every user regardless of
   their real per-board access. That bad code never shipped, but this
   corrective step is cheap and makes 17.0.2.0.1 self-healing regardless
   of exactly what a given database's dashboard_rights_menu table
   currently holds for these menus.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.dashboard_rights.hooks import purge_web_assets

    _logger.info("dashboard_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)

    _grandfather_my_dashboard_non_board_menus(env)
    _correct_board_menu_grants(env)


def _grandfather_my_dashboard_non_board_menus(env):
    root = env.ref("ks_dashboard_ninja.board_menu_root", raise_if_not_found=False)
    if not root:
        return
    cr = env.cr
    cr.execute(
        """
        WITH RECURSIVE tree AS (
            SELECT id FROM ir_ui_menu WHERE id = %s
            UNION ALL
            SELECT m.id FROM ir_ui_menu m JOIN tree t ON m.parent_id = t.id
        )
        SELECT id FROM tree
        """,
        (root.id,),
    )
    subtree_ids = [row[0] for row in cr.fetchall()]
    if not subtree_ids:
        return

    # Exclude board leaf menus — handled separately (and correctly, per
    # real per-user access) by _correct_board_menu_grants below.
    cr.execute(
        "SELECT ks_dashboard_menu_id FROM ks_dashboard_ninja_board "
        "WHERE ks_dashboard_menu_id = ANY(%s)",
        [subtree_ids],
    )
    board_menu_ids = {row[0] for row in cr.fetchall() if row[0]}
    non_board_menu_ids = [mid for mid in subtree_ids if mid not in board_menu_ids]
    if not non_board_menu_ids:
        return

    user_ids = env["res.users"].sudo().search([
        ("share", "=", False), ("active", "=", True),
    ]).ids
    if not user_ids:
        return

    cr.execute(
        "SELECT user_id, menu_id FROM dashboard_rights_menu "
        "WHERE user_id = ANY(%s) AND menu_id = ANY(%s)",
        [user_ids, non_board_menu_ids],
    )
    existing = {(row[0], row[1]) for row in cr.fetchall()}
    to_create = [
        {"user_id": uid, "menu_id": mid, "has_access": True}
        for uid in user_ids
        for mid in non_board_menu_ids
        if (uid, mid) not in existing
    ]
    if to_create:
        env["dashboard.rights.menu"].sudo().create(to_create)
    _logger.info(
        "dashboard_rights: grandfathered %s grant(s) across %s user(s) x "
        "%s My Dashboard non-board menu(s).",
        len(to_create), len(user_ids), len(non_board_menu_ids),
    )


def _correct_board_menu_grants(env):
    cr = env.cr
    cr.execute(
        "SELECT id, ks_dashboard_menu_id FROM ks_dashboard_ninja_board "
        "WHERE ks_dashboard_menu_id IS NOT NULL"
    )
    board_by_menu = {row[1]: row[0] for row in cr.fetchall()}
    if not board_by_menu:
        return
    menu_ids = list(board_by_menu.keys())
    board_ids = list(board_by_menu.values())

    user_ids = env["res.users"].sudo().search([
        ("share", "=", False), ("active", "=", True),
    ]).ids
    if not user_ids:
        return

    cr.execute(
        "SELECT user_id, dashboard_id, has_access FROM dashboard_rights "
        "WHERE user_id = ANY(%s) AND dashboard_id = ANY(%s)",
        [user_ids, board_ids],
    )
    board_access = {(row[0], row[1]): row[2] for row in cr.fetchall()}

    cr.execute(
        "SELECT id, user_id, menu_id, has_access FROM dashboard_rights_menu "
        "WHERE user_id = ANY(%s) AND menu_id = ANY(%s)",
        [user_ids, menu_ids],
    )
    existing_rows = {(row[1], row[2]): (row[0], row[3]) for row in cr.fetchall()}

    RightsMenu = env["dashboard.rights.menu"].sudo()
    to_create = []
    corrected = 0
    for uid in user_ids:
        for menu_id, board_id in board_by_menu.items():
            target = board_access.get((uid, board_id), False)
            row = existing_rows.get((uid, menu_id))
            if row is None:
                to_create.append({
                    "user_id": uid, "menu_id": menu_id, "has_access": target,
                })
            else:
                row_id, current = row
                if current != target:
                    cr.execute(
                        "UPDATE dashboard_rights_menu SET has_access = %s WHERE id = %s",
                        (target, row_id),
                    )
                    corrected += 1
    if to_create:
        RightsMenu.create(to_create)
    if corrected:
        # Direct SQL updates above bypass the model's write() override
        # (which normally clears the menu-visibility cache on every
        # change) — do it once here instead of per row.
        env.registry.clear_cache()
    _logger.info(
        "dashboard_rights: board-menu grant sync — created %s, corrected %s "
        "row(s) across %s user(s) x %s board(s) to match real board access.",
        len(to_create), corrected, len(user_ids), len(board_by_menu),
    )
