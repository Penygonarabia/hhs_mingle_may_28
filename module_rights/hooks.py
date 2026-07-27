"""dashboard_rights / hooks.

Editing a static CSS/JS asset does NOT, on its own, invalidate the compiled
``web.assets_*`` bundle cached in ``ir_attachment``. A plain container restart
or ``-u`` reloads Python and XML but leaves that bundle in place, so styling
changes to the Users-Setup matrix — notably the Has-Access column-width lock —
kept not showing up on deployed servers even after the file was updated.

Column widths in an Odoo list are computed by the JS/CSS renderer, so that fix
*cannot* be expressed in Python/XML. What we CAN do is make the asset deploy
reliably: drop the cached bundle whenever this module is installed or upgraded,
so the next page load recompiles the CSS/JS from the current source on disk.

Wired from both entry points, because they cover different cases:
  * ``post_init_hook``  -> runs on install (``-i``);
  * ``migrations/<version>/post-migrate.py`` -> runs on every ``-u``
    (post_init_hook does not run on upgrade).
"""

import logging

_logger = logging.getLogger(__name__)


def purge_web_assets(env):
    """Delete the compiled ``web.assets_*`` bundles so Odoo rebuilds the
    frontend CSS/JS from the current source files on the next request."""
    bundles = env["ir.attachment"].sudo().search([
        ("name", "=like", "web.assets_%"),
    ])
    count = len(bundles)
    bundles.unlink()
    _logger.info(
        "module_rights: purged %s cached web.assets_* attachment(s); the "
        "frontend bundle will recompile from disk on next load.", count,
    )


def grandfather_hide_menu_user_legacy_grants(env):
    """Seed ``dashboard.rights.menu`` from the older ``hide_menu_user``
    module's legacy per-user menu restrictions, if that data is present.

    ``hide_menu_user`` (a separate, still-installed module on some servers)
    stores its ``res.users.hide_menu_ids`` / ``ir.ui.menu.restrict_user_ids``
    fields — with no relation table of their own specified — in the
    auto-named m2m table ``ir_ui_menu_res_users_rel`` (columns
    ``res_users_id``, ``ir_ui_menu_id``). A row there means "this menu is
    HIDDEN from this user" — a blocklist, the opposite of this module's own
    hidden-until-granted allowlist.

    Installing/upgrading ``module_rights`` fresh on a server that already
    has that legacy blocklist data must not silently take away menus a user
    can currently see. So: every active internal user is granted every
    menu this module manages EXCEPT the ones ``ir_ui_menu_res_users_rel``
    says are hidden for them — this reproduces their CURRENT effective
    visibility under the new allow-list model.

    Create-if-missing only, like every other grandfathering step in this
    module (see the 17.0.2.0.0 / 17.0.2.0.1 migrations): a user/menu pair
    an admin has already explicitly configured through Module Rights Setup
    is never overwritten. A no-op when ``ir_ui_menu_res_users_rel`` doesn't
    exist (e.g. ``hide_menu_user`` was never installed on this server) or
    when every managed menu already has a row for every active user (e.g.
    an earlier grandfathering migration already filled every gap).
    """
    cr = env.cr
    cr.execute("SELECT to_regclass('public.ir_ui_menu_res_users_rel')")
    if not cr.fetchone()[0]:
        return

    menu_ids = list(env["dashboard.rights.menu"]._managed_menu_ids())
    if not menu_ids:
        return

    user_ids = env["res.users"].sudo().search([
        ("share", "=", False), ("active", "=", True),
    ]).ids
    if not user_ids:
        return

    cr.execute(
        "SELECT res_users_id, ir_ui_menu_id FROM ir_ui_menu_res_users_rel "
        "WHERE res_users_id = ANY(%s) AND ir_ui_menu_id = ANY(%s)",
        [user_ids, menu_ids],
    )
    hidden = {(row[0], row[1]) for row in cr.fetchall()}

    cr.execute(
        "SELECT user_id, menu_id FROM dashboard_rights_menu "
        "WHERE user_id = ANY(%s) AND menu_id = ANY(%s)",
        [user_ids, menu_ids],
    )
    existing = {(row[0], row[1]) for row in cr.fetchall()}

    to_create = [
        {"user_id": uid, "menu_id": mid, "has_access": True}
        for uid in user_ids
        for mid in menu_ids
        if (uid, mid) not in existing and (uid, mid) not in hidden
    ]
    if to_create:
        env["dashboard.rights.menu"].sudo().create(to_create)
    _logger.info(
        "module_rights: legacy hide_menu_user grandfather — created %s "
        "grant(s) across %s user(s) x %s managed menu(s) (%s legacy "
        "hide-rows respected).",
        len(to_create), len(user_ids), len(menu_ids), len(hidden),
    )


def post_init_hook(env):
    purge_web_assets(env)
    grandfather_hide_menu_user_legacy_grants(env)
