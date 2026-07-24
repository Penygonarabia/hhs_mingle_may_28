"""Purge the cached web.assets_* bundle on upgrade.

Covers 17.0.1.0.27 (promoted "Rights Setup" to Settings > Dashboard Rights,
added the access.rights.controlled.module registry and its discovery
wizard). No existing Users Setup data is touched by this upgrade — this
purge is only the routine asset-cache invalidation described in
module_rights/hooks.py.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.module_rights.hooks import purge_web_assets

    _logger.info("module_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)
