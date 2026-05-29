# -*- coding: utf-8 -*-
# from odoo import http


# class Entitlement(http.Controller):
#     @http.route('/entitlement/entitlement', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/entitlement/entitlement/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('entitlement.listing', {
#             'root': '/entitlement/entitlement',
#             'objects': http.request.env['entitlement.entitlement'].search([]),
#         })

#     @http.route('/entitlement/entitlement/objects/<model("entitlement.entitlement"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('entitlement.object', {
#             'object': obj
#         })
