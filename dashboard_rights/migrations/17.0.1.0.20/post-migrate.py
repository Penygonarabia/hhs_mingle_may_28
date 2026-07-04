"""Purge the cached web.assets_* bundle on upgrade.

Migration scripts are version-gated (Odoo only runs the folder whose version is
newly crossed), so each release that ships a CSS/JS change needs its own folder
to guarantee the asset bundle is dropped and recompiled from disk. This one
covers 17.0.1.0.20 (the non-editable-list fix for the Has-Access column growth).
See dashboard_rights/hooks.py for the rationale.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.dashboard_rights.hooks import purge_web_assets

    _logger.info("dashboard_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)
