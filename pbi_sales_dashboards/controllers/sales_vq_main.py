# -*- coding: utf-8 -*-
"""Backs "PBI Dashboards > Sales Dashboards > Sales Dashboard - VQ".

The SAME board as "Sales Dashboard With Salesman" (sales_sman_main.py) — same
snapshot, same eleven drill levels, same Regular/Manager switch, same budget
rules — drawn differently: value and quantity side by side instead of a value
chart beside its contribution donut. See static/src/js/sales_vq_dashboard.js.

There is nothing to query differently, so nothing is queried differently: the
payload already carries amount AND qty for every bar and every tile, and the
board that shows both at once needs no extra field. This file is therefore the
route and the gate, and nothing else — PbiSalesSmanController._data does the
work. Even the bar caps are shared now: BAR_CAPS lives beside the engine, and
both boards name it, because both are read as rankings at the same four levels.

WHY A ROUTE OF ITS OWN, then. Two reasons, and both are about access rather
than data:

  * the gate is per menu (access.py mirrors the menu's own visibility), so a
    user granted this board and not "Sales Dashboard With Salesman" has to be
    able to fetch this one and not that one. Sharing the sman route would tie
    the two grants together in whichever direction the shared route named.
  * one route per board is this module's convention, and the menu grant is
    declared against it the same way every other leaf here is.

Deliberately NOT an http.Controller subclass of PbiSalesSmanController:
subclassing would inherit its @http.route method too and register
/pbi_dashboards/sales_sman/data twice. Calling the engine is the whole
relationship, so it is called.
"""

from odoo import http

from .sales_sman_main import BAR_CAPS, DEFAULT_SCOPE, PbiSalesSmanController

MENU_VQ = "pbi_sales_dashboards.menu_pbi_sales_vq"


class PbiSalesVqController(http.Controller):

    @http.route('/pbi_dashboards/sales_vq/data', type='json', auth='user')
    def sales_vq_data(self, period=None, subCategoryMode='regular',
                      drillPath=None, levelFilters=None, viewLevel=None,
                      scope=DEFAULT_SCOPE, **kw):
        # Same signature as the sman route on purpose: the client is the same
        # component with a different route getter, so it sends the same
        # arguments. **kw swallows anything else the browser is still posting
        # from a cached bundle -- and, more to the point, keeps `menu_xmlid`
        # out of _data: the gate below is the route's to name, never the
        # caller's.
        #
        # `measure` is deliberately among the things **kw drops. This board has
        # no Amount/Quantity control -- it shows both at once -- and its two
        # charts are a PAIR: the nth bar is the same category on both, which is
        # the whole point of reading them side by side. Ranking the ten by
        # quantity would break that for one of the two charts. So the ten are
        # chosen by value here, always, and the quantity chart draws those ten.
        return PbiSalesSmanController()._data(MENU_VQ, period, subCategoryMode,
                                              drillPath, levelFilters, viewLevel,
                                              scope, BAR_CAPS)
