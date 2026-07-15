"""Purge the cached web.assets_* bundle on upgrade.

Covers 17.0.1.0.32: added the "<granted>/<total>" smart button on both
Rights Setup and Module Rights Setup, plus read-only drill-down views for
dashboard.rights.menu. No data changes; this purge is only the routine
asset-cache invalidation described in dashboard_rights/hooks.py.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.dashboard_rights.hooks import purge_web_assets

    _logger.info("dashboard_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)
