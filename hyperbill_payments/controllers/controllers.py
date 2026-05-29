# -*- coding: utf-8 -*-
# from odoo import http


# class HyperpayConf(http.Controller):
#     @http.route('/hyperpay_conf/hyperpay_conf', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hyperpay_conf/hyperpay_conf/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hyperpay_conf.listing', {
#             'root': '/hyperpay_conf/hyperpay_conf',
#             'objects': http.request.env['hyperpay_conf.hyperpay_conf'].search([]),
#         })

#     @http.route('/hyperpay_conf/hyperpay_conf/objects/<model("hyperpay_conf.hyperpay_conf"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hyperpay_conf.object', {
#             'object': obj
#         })

