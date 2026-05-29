# -*- coding: utf-8 -*-
# from odoo import http


# class HrTransaction(http.Controller):
#     @http.route('/hr_transaction/hr_transaction', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_transaction/hr_transaction/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_transaction.listing', {
#             'root': '/hr_transaction/hr_transaction',
#             'objects': http.request.env['hr_transaction.hr_transaction'].search([]),
#         })

#     @http.route('/hr_transaction/hr_transaction/objects/<model("hr_transaction.hr_transaction"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_transaction.object', {
#             'object': obj
#         })
