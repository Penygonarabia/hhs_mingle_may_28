# -*- coding: utf-8 -*-
"""One route reporting which optional packages this server has, so every
dashboard can decide what to offer without each one probing for itself.

The boards that own an export control also receive the same dict inside their
own data payload — this route exists for the ones that do not, and for a board
that wants to re-check after an admin has installed something without having
to reload its data.
"""
from odoo import http

from . import optional_deps


class PbiDashboardCapabilitiesController(http.Controller):

    @http.route('/pbi_dashboards/capabilities', type='json', auth='user')
    def pbi_capabilities(self):
        return optional_deps.capabilities()
