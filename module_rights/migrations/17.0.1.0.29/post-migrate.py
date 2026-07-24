"""Purge the cached web.assets_* bundle, and re-grandfather existing
Controlled Modules to their now-full menu subtree.

Covers 17.0.1.0.29: replaced the 17.0.1.0.28 single-whole-app-toggle model
with real per-menu granularity (entry menu + every sub-menu, any depth,
each individually grantable). Any access.rights.controlled.module row
created under 17.0.1.0.28 only grandfathered its entry menu itself; this
re-runs grandfathering for the full subtree so previously-registered
modules' sub-menus aren't silently hidden from users who already had the
module's root menu granted.

access.rights.controlled.module itself was removed in 17.0.2.0.0 (Module
Rights Setup now covers every app automatically, no registry needed). Odoo
runs every intermediate version's migrate() using the CURRENT (already
upgraded) model registry, so a DB jumping straight from an old version to
17.0.2.0.0+ would hit this script with the model already gone — guarded
below so that's a no-op instead of a crash; 17.0.2.0.0's own migration
grandfathers everyone against every app menu anyway.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.module_rights.hooks import purge_web_assets

    _logger.info("module_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)

    try:
        ControlledModule = env["access.rights.controlled.module"].sudo()
    except KeyError:
        _logger.info(
            "module_rights: access.rights.controlled.module no longer "
            "exists (removed in 17.0.2.0.0); skipping its re-grandfathering."
        )
        return
    modules = ControlledModule.search([])
    for cm in modules:
        cm._grandfather_existing_access()
    _logger.info(
        "module_rights: re-grandfathered %s Controlled Module(s) to "
        "their full menu subtree.", len(modules),
    )
