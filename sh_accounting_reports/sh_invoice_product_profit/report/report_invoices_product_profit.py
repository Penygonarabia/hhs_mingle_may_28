# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
import pytz
from datetime import datetime, timedelta


class InvoicesProductProfitAnalysis(models.AbstractModel):
    _name = 'report.sh_accounting_reports.sh_invoices_product_profit_doc'
    _description = 'Invoices Product Profit report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_by = ''
        data = dict(data or {})
        move_dic_by_customers = {}
        move_dic_by_products = {}
        both_move_list = []
        date_start = False
        date_stop = False
        if data['sh_start_date']:
            date_start = fields.Date.from_string(data['sh_start_date'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['sh_end_date']:
            date_stop = fields.Date.from_string(data['sh_end_date'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        if data.get('sh_move_type') == 'out_invoice' or data.get('sh_move_type') == 'out_refund':
            report_by = 'customer'
            if data.get('report_by_customer') == 'customer_report':
                partners = False
                if data.get('sh_partner_ids', False):
                    partners = self.env['res.partner'].sudo().browse(
                        data.get('sh_partner_ids', False))
                else:
                    partners = self.env['res.partner'].sudo().search([])
                if partners:
                    for partner_id in partners:
                        move_list = []
                        domain = [
                            ("invoice_date", ">=", fields.Date.to_string(date_start)),
                            ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                            ("partner_id", "=", partner_id.id),
                        ]
                        if data.get('sh_move_type') == 'out_invoice' or data.get('sh_move_type') == 'out_refund':
                            domain.append(
                                ('move_type', '=', data.get('sh_move_type')))
                        if data.get('company_ids', False):
                            domain.append(
                                ('company_id', 'in', data.get('company_ids', False)))
                        search_moves = self.env['account.move'].sudo().search(
                            domain)
                        unit_cost_stock = 0.00
                        if search_moves.partner_id:

                            if search_moves:
                                for move in search_moves:
                                    if move.invoice_line_ids:
                                        move_dic = {}
                                        reference = 0
                                        unit_cost_stock = 0
                                        pos_unit = 0
                                        bill_unit_of_cost = 0 
                                        for line in move.invoice_line_ids:
                                            # unit_cost_sale = self.env['sale.order'].search([('state', '=', 'sale'),('name','=',move.invoice_origin)])
                                            # for stock in unit_cost_sale:
                                            #     sale = stock.name
                                            #     payment_ref = self.env['stock.valuation.layer'].search(
                                            #         [('stock_move_id.origin', '=', stock.name)])
                                            #     for ref in payment_ref:
                                            #         if ref.product_id == line.product_id:
                                            #             reference = ref.unit_cost
                                            #         if not ref.product_id == line.product_id:
                                            #             reference = line.product_id.standard_price
                                            #     unit_cost_stock = reference
                                            #
                                            # pos_cost = self.env['pos.order'].search([('state','=','invoiced'),('name','=',move.invoice_origin)])
                                            # for pos in pos_cost:
                                            #     pos_source_name = pos.name
                                            #     stock_pick = self.env['stock.picking'].search([('origin','=',pos_source_name)])
                                            #     for stock in stock_pick:
                                            #         pos_name = stock.name
                                            #         stock_valuation =self.env['stock.valuation.layer'].search([('stock_move_id.reference','=',pos_name)])
                                            #         for valuation in stock_valuation:
                                            #             if valuation.product_id == line.product_id:
                                            #                 unit_cost = valuation.unit_cost
                                            #             if not valuation.product_id == line.product_id:
                                            #                 unit_cost = line.product_id.standard_price
                                            #         pos_unit = unit_cost
                                            #
                                            # bill_of_cost = self.env['purchase.order'].search([('state','=','purchase'),('name','=',move.invoice_origin)])
                                            # for bill in bill_of_cost:
                                            #     bill_of_name = bill.name
                                            #     stock_valuation = self.env['stock.valuation.layer'].search([('stock_move_id.origin','=',bill_of_name)])
                                            #     for stock in stock_valuation:
                                            #         if not stock.stock_landed_cost_id:
                                            #             if stock.product_id == line.product_id:
                                            #                 bill_unit = stock.unit_cost
                                            #             if not stock.product_id == line.product_id:
                                            #                 bill_unit = line.product_id.standard_price
                                            #     bill_unit_of_cost = bill_unit
                                            #

                                            if not line.display_type:
                                                line_dic = {
                                                    'invoice_number': move.name,
                                                    'invoice_date': move.invoice_date,
                                                    'product_category' : line.product_id.categ_id.display_name,
                                                    'product' : line.product_id.display_name,
                                                    'analytic_account':line.analytic_account_id.name,
                                                    'qty': line.quantity,
                                                    'cost':line.cost_price,
                                                    # 'cost': unit_cost_stock or pos_unit or bill_unit_of_cost,
                                                    'sale_price': line.price_unit,
                                                    'discount': line.discount,
                                                }
                                                if move_dic.get(line.product_id.id, False):
                                                    qty = move_dic.get(
                                                        line.product_id.id)['qty']
                                                    qty = qty + line.quantity
                                                    line_dic.update({
                                                        'qty': qty,
                                                    })
                                                move_dic.update(
                                                    {line.product_id.id: line_dic})
                                        for key, value in move_dic.items():
                                            move_list.append(value)
                            move_dic_by_customers.update(
                                {partner_id.name_get()[0][1]: move_list})
            elif data.get('report_by_customer') == 'product':
                report_by = 'product'
                products = False
                if data.get('sh_product_ids', False):
                    products = self.env['product.product'].sudo().browse(
                        data.get('sh_product_ids', False))
                else:
                    products = self.env['product.product'].sudo().search([])
                if products:
                    for product_id in products:
                        move_list = []
                        domain = [
                            ("invoice_date", ">=",
                             fields.Date.to_string(date_start)),
                            ("invoice_date", "<=",
                             fields.Date.to_string(date_stop)),
                        ]
                        if data.get('company_ids', False):
                            domain.append(
                                ('company_id', 'in', data.get('company_ids', False)))
                        search_moves = self.env['account.move'].sudo().search(
                            domain)
                        if product_id in search_moves.invoice_line_ids.product_id:

                            if search_moves:
                                for move in search_moves:
                                    if move.invoice_line_ids:
                                        move_dic = {}
                                        reference = 0
                                        unit_cost_stock = 0
                                        pos_unit = 0
                                        bill_unit = 0
                                        unit_cost = 0
                                        bill_unit_of_cost = 0 
                                        for line in move.invoice_line_ids.sudo().filtered(lambda x: x.product_id.id == product_id.id):
                                            # unit_cost_sale = self.env['sale.order'].search([('state', '=', 'sale'),('name','=',move.invoice_origin)])
                                            # for stock in unit_cost_sale:
                                            #     sale = stock.name
                                            #     payment_ref = self.env['stock.valuation.layer'].search(
                                            #         [('stock_move_id.origin', '=', stock.name)])
                                            #     for ref in payment_ref:
                                            #         if ref.product_id == line.product_id:
                                            #             reference = ref.unit_cost
                                            #         if not ref.product_id == line.product_id:
                                            #             reference = line.product_id.standard_price
                                            # unit_cost_stock = reference
                                            #
                                            # pos_cost = self.env['pos.order'].search([('state','=','invoiced'),('name','=',move.invoice_origin)])
                                            # for pos in pos_cost:
                                            #     pos_source_name = pos.name
                                            #     stock_pick = self.env['stock.picking'].search([('origin','=',pos_source_name)])
                                            #     for stock in stock_pick:
                                            #         pos_name = stock.name
                                            #         stock_valuation = self.env['stock.valuation.layer'].search([('stock_move_id.reference','=',pos_name)])
                                            #         for valuation in stock_valuation:
                                            #             if valuation.product_id == line.product_id:
                                            #                 unit_cost = valuation.unit_cost
                                            #             if not valuation.product_id == line.product_id:
                                            #                 unit_cost = line.product_id.standard_price
                                            # pos_unit = unit_cost
                                            #
                                            # bill_of_cost = self.env['purchase.order'].search([('state','=','purchase'),('name','=',move.invoice_origin)])
                                            # for bill in bill_of_cost:
                                            #     bill_of_name = bill.name
                                            #     stock_valuation = self.env['stock.valuation.layer'].search([('stock_move_id.origin','=',bill_of_name)])
                                            #     for stock in stock_valuation:
                                            #         if not stock.stock_landed_cost_id:
                                            #             if stock.product_id == line.product_id:
                                            #                 bill_unit = stock.unit_cost
                                            #             if not stock.product_id == line.product_id:
                                            #                 bill_unit = line.product_id.standard_price
                                            # bill_unit_of_cost = bill_unit
    
                                            if not line.display_type:
                                                line_dic = {
                                                    'invoice_number': move.name,
                                                    'invoice_date': move.invoice_date,
                                                    'product_category' : line.product_id.categ_id.display_name,
                                                    'analytic_account':line.analytic_account_id.name,
                                                    'customer': move.partner_id.name_get()[0][1],
                                                    'qty': line.quantity,
                                                    # 'cost': unit_cost_stock or pos_unit or bill_unit_of_cost,
                                                    'cost':line.cost_price,
                                                    'sale_price': line.price_unit,
                                                    'discount': line.discount,
                                                }
                                                if move_dic.get(line.product_id.id, False):
                                                    qty = move_dic.get(
                                                        line.product_id.id)['qty']
                                                    qty = qty + line.quantity
                                                    line_dic.update({
                                                        'qty': qty,
                                                    })
                                                move_dic.update(
                                                    {line.product_id.id: line_dic})
                                        for key, value in move_dic.items():
                                            move_list.append(value)
                            move_dic_by_products.update(
                                {product_id.name_get()[0][1]: move_list})
            elif data.get('report_by_customer') == 'customer_product':
                report_by = 'customer with product'
                products = False
                partners = False
                if data.get('sh_product_ids', False):
                    products = self.env['product.product'].sudo().browse(
                        data.get('sh_product_ids', False))
                else:
                    products = self.env['product.product'].sudo().search([])
                if data.get('sh_partner_ids', False):
                    partners = self.env['res.partner'].sudo().browse(
                        data.get('sh_partner_ids', False))
                else:
                    partners = self.env['res.partner'].sudo().search([])
                for partner_id in partners:

                    domain = [
                        ("invoice_date", ">=", fields.Date.to_string(date_start)),
                        ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                        ("partner_id", "=", partner_id.id),
                    ]
                    if data.get('sh_move_type') == 'out_invoice' or data.get('sh_move_type') == 'out_refund':
                        domain.append(
                            ('move_type', '=', data.get('sh_move_type')))
                    if data.get('company_ids', False):
                        domain.append(
                            ('company_id', 'in', data.get('company_ids', False)))
                    search_moves = self.env['account.move'].sudo().search(
                        domain)
                    if search_moves.partner_id:

                        if search_moves:
                            for move in search_moves:
                                if move.invoice_line_ids:
                                    move_dic = {}
                                    reference = 0
                                    unit_cost_stock = 0
                                    pos_unit = 0
                                    bill_unit_of_cost = 0 
                                    for line in move.invoice_line_ids:
                                        # unit_cost_sale = self.env['sale.order'].search([('state', '=', 'sale'),('name','=',move.invoice_origin)])
                                        # for stock in unit_cost_sale:
                                        #     sale = stock.name
                                        #     payment_ref = self.env['stock.valuation.layer'].search(
                                        #         [('stock_move_id.origin', '=', stock.name)])
                                        #     for ref in payment_ref:
                                        #         if ref.product_id == line.product_id:
                                        #             reference = ref.unit_cost
                                        #         if not ref.product_id == line.product_id:
                                        #             reference = line.product_id.standard_price
                                        # unit_cost_stock = reference
                                        #
                                        # pos_cost = self.env['pos.order'].search([('state','=','invoiced'),('name','=',move.invoice_origin)])
                                        # for pos in pos_cost:
                                        #     pos_source_name = pos.name
                                        #     stock_pick = self.env['stock.picking'].search([('origin','=',pos_source_name)])
                                        #     for stock in stock_pick:
                                        #         pos_name = stock.name
                                        #         stock_valuation =self.env['stock.valuation.layer'].search([('stock_move_id.reference','=',pos_name)])
                                        #         for valuation in stock_valuation:
                                        #             if valuation.product_id == line.product_id:
                                        #                 unit_cost = valuation.unit_cost
                                        #             if not valuation.product_id == line.product_id:
                                        #                 unit_cost = line.product_id.standard_price
                                        # pos_unit = unit_cost
                                        #
                                        # bill_of_cost = self.env['purchase.order'].search([('state','=','purchase'),('name','=',move.invoice_origin)])
                                        # for bill in bill_of_cost:
                                        #     bill_of_name = bill.name
                                        #     stock_valuation = self.env['stock.valuation.layer'].search([('stock_move_id.origin','=',bill_of_name)])
                                        #     for stock in stock_valuation:
                                        #         if not stock.stock_landed_cost_id:
                                        #             if stock.product_id == line.product_id:
                                        #                 bill_unit = stock.unit_cost
                                        #             if not stock.product_id == line.product_id:
                                        #                 bill_unit = line.product_id.standard_price
                                        # bill_unit_of_cost = bill_unit
                                        #

                                        for product_id in products:
                                            if line.product_id.id == product_id.id:
                                                if not line.display_type:
                                                    line_dic = {
                                                        'invoice_number': move.name,
                                                        'invoice_date': move.invoice_date,
                                                        'product_category' : line.product_id.categ_id.display_name,
                                                        'product' : line.product_id.display_name,
                                                        'analytic_account':line.analytic_account_id.name,
                                                        'customer': move.partner_id.name_get()[0][1],
                                                        'qty': line.quantity,
                                                        'cost':line.cost_price,
                                                        'cost': unit_cost_stock or pos_unit or bill_unit_of_cost,
                                                        'sale_price': line.price_unit,
                                                        'discount': line.discount,
                                                    }
                                                    if move_dic.get(line.product_id.id, False):
                                                        qty = move_dic.get(
                                                            line.product_id.id)['qty']
                                                        qty = qty + line.quantity
                                                        line_dic.update({
                                                            'qty': qty,
                                                        })
                                                    move_dic.update(
                                                        {line.product_id.id: line_dic})
                                    for key, value in move_dic.items():
                                        both_move_list.append(value)

        else:
            if data.get('report_by_vendor') == 'vendor_report':
                report_by = 'vendor'
                partners = False
                if data.get('sh_partner_ids', False):
                    partners = self.env['res.partner'].sudo().browse(
                        data.get('sh_partner_ids', False))
                else:
                    partners = self.env['res.partner'].sudo().search([])
                if partners:
                    for partner_id in partners:
                        move_list = []
                        domain = [
                            ("invoice_date", ">=", fields.Date.to_string(date_start)),
                            ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                            ("partner_id", "=", partner_id.id)
                        ]
                        if data.get('sh_move_type') == 'in_invoice' or data.get('sh_move_type') == 'in_refund':
                            domain.append(
                                ('move_type', '=', data.get('sh_move_type')))
                        if data.get('company_ids', False):
                            domain.append(
                                ('company_id', 'in', data.get('company_ids', False)))
                        search_moves = self.env['account.move'].sudo().search(
                            domain)
                        if search_moves.partner_id:
                            if search_moves:
                                for move in search_moves:
                                    if move.invoice_line_ids:
                                        move_dic = {}
                                        reference = 0
                                        unit_cost_stock = 0
                                        pos_unit = 0
                                        bill_unit_of_cost = 0 
                                        for line in move.invoice_line_ids:
                                            # unit_cost_sale = self.env['sale.order'].search([('state', '=', 'sale'),('name','=',move.invoice_origin)])
                                            # for stock in unit_cost_sale:
                                            #     sale = stock.name
                                            #     payment_ref = self.env['stock.valuation.layer'].search(
                                            #         [('stock_move_id.origin', '=', stock.name),('product_id','=',line.product_id.id)])
                                            #     for ref in payment_ref:
                                            #         if ref.product_id == line.product_id:
                                            #             reference = ref.unit_cost
                                            #         if not ref.product_id == line.product_id:
                                            #             reference = line.product_id.standard_price
                                            # unit_cost_stock = reference
                                            #
                                            # pos_cost = self.env['pos.order'].search([('state','=','invoiced'),('name','=',move.invoice_origin)])
                                            # for pos in pos_cost:
                                            #     pos_source_name = pos.name
                                            #     stock_pick = self.env['stock.picking'].search([('origin','=',pos_source_name)])
                                            #     for stock in stock_pick:
                                            #         pos_name = stock.name
                                            #         stock_valuation =self.env['stock.valuation.layer'].search([('stock_move_id.reference','=',pos_name)])
                                            #         for valuation in stock_valuation:
                                            #             if valuation.product_id == line.product_id:
                                            #                 unit_cost=valuation.unit_cost
                                            #             if not valuation.product_id == line.product_id:
                                            #                 unit_cost = line.product_id.standard_price
                                            # pos_unit = unit_cost
                                            #
                                            # bill_of_cost = self.env['purchase.order'].search([('state','=','purchase'),('name','=',move.invoice_origin)])
                                            # for bill in bill_of_cost:
                                            #     bill_of_name = bill.name
                                            #     stock_valuation = self.env['stock.valuation.layer'].search([('stock_move_id.origin','=',bill_of_name)])
                                            #     for stock in stock_valuation:
                                            #         if not stock.stock_landed_cost_id:
                                            #             if stock.product_id == line.product_id:
                                            #                 bill_unit = stock.unit_cost
                                            #             if not stock.product_id == line.product_id:
                                            #                 bill_unit = line.product_id.standard_price
                                            # bill_unit_of_cost = bill_unit
    
                                            if not line.display_type:
                                                line_dic = {
                                                    'invoice_number': move.name,
                                                    'invoice_date': move.invoice_date,
                                                    'product_category' : line.product_id.categ_id.display_name,
                                                    'product' : line.product_id.display_name,
                                                    'analytic_account':line.analytic_account_id.name,
                                                    'qty': line.quantity,
                                                    'cost':line.cost_price,
                                                    # 'cost': unit_cost_stock or pos_unit or bill_unit_of_cost,
                                                    'sale_price': line.price_unit,
                                                    'discount': line.discount,
                                                }
                                                if move_dic.get(line.product_id.id, False):
                                                    qty = move_dic.get(
                                                        line.product_id.id)['qty']
                                                    qty = qty + line.quantity
                                                    line_dic.update({
                                                        'qty': qty,
                                                    })
                                                move_dic.update(
                                                    {line.product_id.id: line_dic})
                                        for key, value in move_dic.items():
                                            move_list.append(value)
                            move_dic_by_customers.update(
                                {partner_id.name_get()[0][1]: move_list})
            elif data.get('report_by_vendor') == 'product':
                report_by = 'product'
                products = False
                if data.get('sh_product_ids', False):
                    products = self.env['product.product'].sudo().browse(
                        data.get('sh_product_ids', False))
                else:
                    products = self.env['product.product'].sudo().search([])
                if products:
                    for product_id in products:
                        move_list = []
                        domain = [
                            ("invoice_date", ">=",
                             fields.Date.to_string(date_start)),
                            ("invoice_date", "<=",
                             fields.Date.to_string(date_stop)),
                        ]
                        if data.get('company_ids', False):
                            domain.append(
                                ('company_id', 'in', data.get('company_ids', False)))
                        search_moves = self.env['account.move'].sudo().search(
                            domain)
                        if product_id in search_moves.invoice_line_ids.product_id:

                            if search_moves:
                                for move in search_moves:
                                    if move.invoice_line_ids:
                                        move_dic = {}
                                        reference = 0
                                        unit_cost_stock = 0
                                        pos_unit = 0
                                        bill_unit_of_cost = 0 
                                        for line in move.invoice_line_ids.sudo().filtered(lambda x: x.product_id.id == product_id.id):
                                            # unit_cost_sale = self.env['sale.order'].search([('state', '=', 'sale'),('name','=',move.invoice_origin)])
                                            # for stock in unit_cost_sale:
                                            #     sale = stock.name
                                            #     payment_ref = self.env['stock.valuation.layer'].search(
                                            #         [('stock_move_id.origin', '=', stock.name)])
                                            #     for ref in payment_ref:
                                            #         if ref.product_id == line.product_id:
                                            #             reference = ref.unit_cost
                                            #         if not ref.product_id == line.product_id:
                                            #             reference = line.product_id.standard_price
                                            # unit_cost_stock = reference
                                            #
                                            # pos_cost = self.env['pos.order'].search([('state','=','invoiced'),('name','=',move.invoice_origin)])
                                            # for pos in pos_cost:
                                            #     pos_source_name = pos.name
                                            #     stock_pick = self.env['stock.picking'].search([('origin','=',pos_source_name)])
                                            #     for stock in stock_pick:
                                            #         pos_name = stock.name
                                            #         stock_valuation =self.env['stock.valuation.layer'].search([('stock_move_id.reference','=',pos_name)])
                                            #         for valuation in stock_valuation:
                                            #             if valuation.product_id == line.product_id:
                                            #                 unit_cost = valuation.unit_cost
                                            #             if not valuation.product_id == line.product_id:
                                            #                 unit_cost= line.product_id.standard_price
                                            #
                                            # pos_unit = unit_cost
                                            #
                                            # bill_of_cost = self.env['purchase.order'].search([('state','=','purchase'),('name','=',move.invoice_origin)])
                                            # for bill in bill_of_cost:
                                            #     bill_of_name = bill.name
                                            #     stock_valuation = self.env['stock.valuation.layer'].search([('stock_move_id.origin','=',bill_of_name)])
                                            #     for stock in stock_valuation:
                                            #         if not stock.stock_landed_cost_id:
                                            #             if stock.product_id == line.product_id:
                                            #                 bill_unit = stock.unit_cost
                                            #             if not stock.product_id == line.product_id:
                                            #                 bill_unit = line.product_id.standard_price
                                            # bill_unit_of_cost = bill_unit
    
                                            if not line.display_type:
                                                line_dic = {
                                                    'invoice_number': move.name,
                                                    'invoice_date': move.invoice_date,
                                                    'product_category' : line.product_id.categ_id.display_name,
                                                    'analytic_account':line.analytic_account_id.name,
                                                    'customer': move.partner_id.name_get()[0][1],
                                                    'qty': line.quantity,
                                                    'cost':line.cost_price,
                                                    # 'cost': unit_cost_stock or pos_unit or bill_unit_of_cost,
                                                    'sale_price': line.price_unit,
                                                    'discount': line.discount,
                                                }
                                                if move_dic.get(line.product_id.id, False):
                                                    qty = move_dic.get(
                                                        line.product_id.id)['qty']
                                                    qty = qty + line.quantity
                                                    line_dic.update({
                                                        'qty': qty,
                                                    })
                                                move_dic.update(
                                                    {line.product_id.id: line_dic})
                                        for key, value in move_dic.items():
                                            move_list.append(value)
                            move_dic_by_products.update(
                                {product_id.name_get()[0][1]: move_list})
            elif data.get('report_by_vendor') == 'vendor_product':
                report_by = 'vendor with product'
                products = False
                partners = False
                if data.get('sh_product_ids', False):
                    products = self.env['product.product'].sudo().browse(
                        data.get('sh_product_ids', False))
                else:
                    products = self.env['product.product'].sudo().search([])
                if data.get('sh_partner_ids', False):
                    partners = self.env['res.partner'].sudo().browse(
                        data.get('sh_partner_ids', False))
                else:
                    partners = self.env['res.partner'].sudo().search([])
                for partner_id in partners:

                    domain = [
                        ("invoice_date", ">=", fields.Date.to_string(date_start)),
                        ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                        ("partner_id", "=", partner_id.id),
                    ]
                    if data.get('sh_move_type') == 'in_invoice' or data.get('sh_move_type') == 'in_refund':
                        domain.append(
                            ('move_type', '=', data.get('sh_move_type')))
                    if data.get('company_ids', False):
                        domain.append(
                            ('company_id', 'in', data.get('company_ids', False)))
                    search_moves = self.env['account.move'].sudo().search(
                        domain)
                    if search_moves:
                        for move in search_moves:
                            if move.invoice_line_ids:
                                move_dic = {}
                                reference = 0
                                unit_cost_stock = 0
                                pos_unit = 0
                                bill_unit_of_cost = 0 
                                for line in move.invoice_line_ids:
                                    # unit_cost_sale = self.env['sale.order'].search([('state', '=', 'sale'),('name','=',move.invoice_origin)])
                                    # for stock in unit_cost_sale:
                                    #     sale = stock.name
                                    #     payment_ref = self.env['stock.valuation.layer'].search(
                                    #         [('stock_move_id.origin', '=', stock.name)])
                                    #     for ref in payment_ref:
                                    #         if ref.product_id == line.product_id:
                                    #             reference = ref.unit_cost
                                    #         if not ref.product_id == line.product_id:
                                    #             referenc = line.product_id.standard_price
                                    # unit_cost_stock = reference
                                    #
                                    # pos_cost = self.env['pos.order'].search([('state','=','invoiced'),('name','=',move.invoice_origin)])
                                    # for pos in pos_cost:
                                    #     pos_source_name = pos.name
                                    #     stock_pick = self.env['stock.picking'].search([('origin','=',pos_source_name)])
                                    #     for stock in stock_pick:
                                    #         pos_name = stock.name
                                    #         stock_valuation =self.env['stock.valuation.layer'].search([('stock_move_id.reference','=',pos_name)])
                                    #         for valuation in stock_valuation:
                                    #             if valuation.product_id == line.product_id:
                                    #                 unit_cost=valuation.unit_cost
                                    #             if not valution.product_id == line.product_id:
                                    #                 unit_cost = line.product_id.standard_price
                                    # pos_unit = unit_cost
                                    #
                                    # bill_of_cost = self.env['purchase.order'].search([('state','=','purchase'),('name','=',move.invoice_origin)])
                                    # for bill in bill_of_cost:
                                    #     bill_of_name = bill.name
                                    #     stock_valuation = self.env['stock.valuation.layer'].search([('stock_move_id.origin','=',bill_of_name)])
                                    #     for stock in stock_valuation:
                                    #         if not stock.stock_landed_cost_id:
                                    #             if stock.product_id == line.product_id:
                                    #                 bill_unit = stock.unit_cost
                                    #             if not stock.product_id == line.product_id:
                                    #                 bill_unit = line.product_id.standard_price
                                    # bill_unit_of_cost = bill_unit

                                    for product_id in products:
                                        if line.product_id.id == product_id.id:
                                            if not line.display_type:
                                                line_dic = {
                                                    'invoice_number': move.name,
                                                    'invoice_date': move.invoice_date,
                                                    'product_category' : line.product_id.categ_id.display_name,
                                                    'product' : line.product_id.display_name,
                                                    'analytic_account':line.analytic_account_id.name,
                                                    'customer': move.partner_id.name_get()[0][1],
                                                    'qty': line.quantity,
                                                    'cost':line.cost_price,
                                                    # 'cost': unit_cost_stock or pos_unit or bill_unit_of_cost,
                                                    'sale_price': line.price_unit,
                                                    'discount': line.discount,
                                                }
                                                if move_dic.get(line.product_id.id, False):
                                                    qty = move_dic.get(
                                                        line.product_id.id)['qty']
                                                    qty = qty + line.quantity
                                                    line_dic.update({
                                                        'qty': qty,
                                                    })
                                                move_dic.update(
                                                    {line.product_id.id: line_dic})
                                for key, value in move_dic.items():
                                    both_move_list.append(value)

        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'move_dic_by_customers': move_dic_by_customers,
            'move_dic_by_product': move_dic_by_products,
            'both_move_list': both_move_list,
            'report_by': report_by
        })
        return data
