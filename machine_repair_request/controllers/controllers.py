# -*- coding: utf-8 -*-
# from odoo import http


# class MachineRepairRequest(http.Controller):
#     @http.route('/machine_repair_request/machine_repair_request', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/machine_repair_request/machine_repair_request/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('machine_repair_request.listing', {
#             'root': '/machine_repair_request/machine_repair_request',
#             'objects': http.request.env['machine_repair_request.machine_repair_request'].search([]),
#         })

#     @http.route('/machine_repair_request/machine_repair_request/objects/<model("machine_repair_request.machine_repair_request"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('machine_repair_request.object', {
#             'object': obj
#         })

