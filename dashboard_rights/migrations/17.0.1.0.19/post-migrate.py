"""Purge the cached web.assets_* bundle on upgrade.

``post_init_hook`` only runs on install, so a plain ``-u dashboard_rights``
would otherwise keep serving the stale compiled CSS/JS and the Has-Access
column-width lock (and any other styling change) would not appear. Running the
purge here makes an upgrade sufficient to refresh the frontend, using the same
mechanism that already reliably delivers this module's Python/XML changes.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Imported lazily so the module is on sys.path when the migration runs.
    from odoo.addons.dashboard_rights.hooks import purge_web_assets

    _logger.info("dashboard_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)
