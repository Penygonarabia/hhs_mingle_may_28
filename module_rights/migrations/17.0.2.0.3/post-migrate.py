"""Purge the cached web.assets_* bundle; grandfather legacy hide_menu_user
menu restrictions into dashboard.rights.menu.

Covers 17.0.2.0.3: the "User Role" column/filter (Parts / Coordinator /
Call Center / Technician, derived from machine_repair_management group
membership) was removed everywhere — this was the module's only
dependency on another app's data, and the module now works fully
standalone regardless of whether machine_repair_management is installed.

Also runs the same legacy-grant grandfathering as post_init_hook (see
hooks.grandfather_hide_menu_user_legacy_grants) here too, on upgrade —
not just on a fresh install — so a server that had hide_menu_user's
ir_ui_menu_res_users_rel data appear or change AFTER module_rights was
first installed still gets any newly-missing grants filled in. Like
every other grandfathering step in this module, it only creates rows
that don't exist yet, so it is a cheap no-op on a server (like this
one) where an earlier migration already granted every managed menu to
every active user.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.module_rights.hooks import (
        grandfather_hide_menu_user_legacy_grants,
        purge_web_assets,
    )

    _logger.info("module_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)

    grandfather_hide_menu_user_legacy_grants(env)
