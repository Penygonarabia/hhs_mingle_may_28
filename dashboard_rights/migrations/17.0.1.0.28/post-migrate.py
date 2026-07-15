"""Purge the cached web.assets_* bundle on upgrade.

Covers 17.0.1.0.28 (Controlled Modules now appear in the Rights Setup
matrix as single-child groups). No schema change beyond the transient
dashboard.rights.matrix.line rows this generates at runtime; this purge is
only the routine asset-cache invalidation described in
dashboard_rights/hooks.py.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.dashboard_rights.hooks import purge_web_assets

    _logger.info("dashboard_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)
