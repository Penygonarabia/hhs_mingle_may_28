"""Repair stale KS measure field ids on upgrade.

post_init_hook only runs on install, so a plain ``-u promoter_dashboards``
would otherwise never re-run the heal. This post-migrate script makes an
upgrade sufficient: it re-resolves the promoter boards' measure/list field ids
by name against the current DB, fixing the "MissingError: ir.model.fields(N,)"
crash that a source-module reinstall leaves behind.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Imported lazily so the module is on sys.path when the migration runs.
    from odoo.addons.promoter_dashboards.hooks import heal_promoter_boards

    _logger.info("promoter_dashboards: healing stale KS field ids on upgrade.")
    heal_promoter_boards(env)
