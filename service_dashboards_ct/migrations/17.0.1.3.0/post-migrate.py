# -*- coding: utf-8 -*-
"""Rebuild drill-down (``ks_dashboard_ninja.item_action``) rows from the
canonical Python data file.

The XML records for ``ks_dashboard_ninja.item_action`` were dropped in
17.0.1.3.0; drill configuration now lives in ``drill_actions_data.py``
and is applied through :func:`hooks.apply_drill_actions`. Calling that
helper here brings existing installs up to the same state as a fresh
install.
"""

from odoo import api, SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    from odoo.addons.service_dashboards_ct.hooks import apply_drill_actions
    env = Environment(cr, SUPERUSER_ID, {})
    apply_drill_actions(env)
