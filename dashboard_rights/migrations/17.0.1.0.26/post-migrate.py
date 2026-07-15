"""Purge the cached web.assets_* bundle on upgrade.

Covers 17.0.1.0.26 (removed the non-working "Copy Email ID" button from the
matrix header, plus the two now-fully-dead copy-to-clipboard widget files it
and an earlier abandoned attempt left behind). See dashboard_rights/hooks.py
for the rationale.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.dashboard_rights.hooks import purge_web_assets

    _logger.info("dashboard_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)
