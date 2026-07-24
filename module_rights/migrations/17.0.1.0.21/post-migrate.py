"""Purge the cached web.assets_* bundle on upgrade.

Covers 17.0.1.0.21 (group-toggle cascade hardening + children popup). See
module_rights/hooks.py for the rationale.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.module_rights.hooks import purge_web_assets

    _logger.info("module_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)
