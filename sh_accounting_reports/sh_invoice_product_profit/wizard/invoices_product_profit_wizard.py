# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import xlwt
import base64
from odoo.exceptions import UserError
import io
import pytz
import datetime
from datetime import datetime
import xlsxwriter
import dateutil
from datetime import timedelta
from dateutil import relativedelta
from dateutil.relativedelta import relativedelta
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_round




class InvoicesProductProfitReportXLS(models.Model):
    _name = 'sh.invoice.product.profit.xls'
    _description = 'Invoices Product Profit Xls Report'
    excel_file = fields.Binary('Download report Excel' )
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.invoice.product.profit.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
         
                         
        }
        


class InvoiceProductProfitReportTemplate(models.TransientModel):
    _name = 'invoice.product.reporting.template'
    _description = 'Invoice Product Reporting Template'

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product"
    )
  
    start_date = fields.Date(
        string="Start Date"
    )
    end_date = fields.Date(
        string="End Date"
    )
    
    invoice_number = fields.Char(string="Invoice Number")
    invoice_date = fields.Date(string="Invoice Date")
    product_category = fields.Char(string="Product Category")
    account_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        readonly=True,
        store=True
    )
    account_tag_ids = fields.Many2many("account.analytic.tag", string="Analytic Tags")
    product_quantity = fields.Float(string="Product Quantity",readonly=True)
    product_cost = fields.Float(string="Cost Price",store=True,)
    product_sales = fields.Float(string="Sales Price",store=True)
    product_discount = fields.Float(string="Discount",store=True)
    product_profit = fields.Float(string="Profit",store=True)
    # product_margin = fields.Float(string="Margin",store=True)
    customer_name = fields.Char(string="Customer Name")
    tax_individual = fields.Float(string="Tax Amount")
    bill_date = fields.Date(string="Bill Date",store=True)
    vendor_name = fields.Char(string="Vendor Name")
    invoice_date_time = fields.Datetime(string="Invoice Date Time",store=True)
    untaxed_total = fields.Float(string="Un-taxed Total")
    invoice_time = fields.Char(string="Hour")
    # invoice_time = datetime.strptime(invoice_date_time,'%Y-%m-%d %H:%M:%S').time()
    
    
    # invoice_date_time = fields.Datetime(string="Invoice Date Time",groupby='date:hour')




class InvoicesProductProfitWizard(models.TransientModel):
    _name = 'sh.invoice.product.profit.wizard'
    _inherit = 'invoice.product.reporting.template'
    _description = 'Invoices Product Profit Wizard'
    

    sh_start_date = fields.Date(
        'Start Date', required=True, default=fields.Datetime.now)
    sh_end_date = fields.Date(
        'End Date', required=True, default=fields.Datetime.now)
    sh_partner_ids = fields.Many2many(
        'res.partner', string='Customers/Vendors')
    report_by_customer = fields.Selection([('customer_report', 'Customers'), ('product', 'Products Only'), (
        'customer_product', 'Customer With Product')], string='Report Print By', default='customer_report')
    report_by_vendor = fields.Selection([('vendor_report', 'Vendor'), ('product', 'Products Only'), (
        'vendor_product', 'Vendor with Products')], string='Report Print By', default='vendor_report')
    sh_move_type = fields.Selection([('out_invoice', 'Customer Invoice'),
                                     ('out_refund', 'Customer Credit Note'),
                                     ('in_invoice', 'Vendor Bill'),
                                     ('in_refund', 'Vendor Credit Note')], default='out_invoice', string="Invoice Type")
    sh_product_ids = fields.Many2many('product.product', string='Products')
    company_ids = fields.Many2many(
        'res.company', default=lambda self: self.env.companies, string="Companies")

    @api.onchange('sh_move_type')
    def _onchange_move_type(self):
        domain = {}
        if not self.sh_move_type:
            partner_obj = self.env['res.partner'].search([])
            domain = {'sh_partner_ids': [('id', 'in', partner_obj.ids)]}
        else:
            if self.sh_move_type == 'out_invoice' or self.sh_move_type == 'out_refund':
                partner_obj = self.env['res.partner'].search(
                    [('customer_rank', '>', 0)])
                domain = {'sh_partner_ids': [('id', 'in', partner_obj.ids)]}
            elif self.sh_move_type == 'in_invoice' or self.sh_move_type == 'in_refund':
                partner_obj = self.env['res.partner'].search(
                    [('supplier_rank', '>', 0)])
                domain = {'sh_partner_ids': [('id', 'in', partner_obj.ids)]}
        return {'domain': domain}

    @api.constrains('sh_start_date', 'sh_end_date')
    def _check_dates(self):
        if self.filtered(lambda c: c.sh_end_date and c.sh_start_date > c.sh_end_date):
            raise ValidationError(_('start date must be less than end date.'))
    
    
    def generate_report(self):
        sh_partner_ids = False
        sh_start_date = self.sh_start_date
        sh_end_date = self.sh_end_date
        # sh_partner_ids = self.sh_partner_ids
        report_by_customer =self.report_by_customer
        report_by_vendor = self.report_by_vendor
        sh_move_type = self.sh_move_type
        sh_product_ids = self.sh_product_ids
        company_ids = self.company_ids
        
        if self.sh_partner_ids:
            sh_partner_ids = self.sh_partner_ids
            
        else:
            sh_partner_ids = self.env['res.partner'].search([])
        self._cr.execute('delete from sh_invoice_product_profit_wizard;')  
        
        if self.sh_move_type == "out_invoice":
            if self.sh_move_type == "out_invoice" and self.report_by_customer == "customer_report":
        
                move_detail = self.env['account.move'].search([('move_type','=','out_invoice'),('invoice_date','>=',self.sh_start_date),('invoice_date','<=',self.sh_end_date),('state','=','posted'),('company_id', '=', self.company_ids.ids),('partner_id','in',sh_partner_ids.ids)])
            
                for move in move_detail:
                    name = move.name
                    partner_id = move.partner_id.display_name
                    date =move.invoice_date
                    date_time = str(move.datetime_invoice)
                    
                    user_tz = self.env.user.tz or pytz.utc
                    local = pytz.timezone(user_tz)
                    display_date_result = datetime.strftime(pytz.utc.localize(datetime.strptime(date_time,
    DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),"%H")
                  
                  
                    # date_time=pytz.utc.localize(date_time).astimezone(tz)
                 
                    
                    # user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                    # today = user_tz.localize(date_time)
                    # date_start = today.astimezone(pytz.timezone('UTC'))
                    #
                    
                    # if date_time:
                    #     time_invoice = datetime.strptime(str(date_start),'%Y-%m-%d %H:%M:%S').time().hour
                        # pytz.utc.localize(time_invoice).astimezone(tz)
                    reference = 0
                    unit_cost_stock = 0
                    pos_unit = 0
                    bill_unit_of_cost = 0 
                    unit_cost=0
                    bill_unit =0
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

                        
                        
                        product_id = line.product_id.id
                        analytic_account_id = line.analytic_account_id.id
                        category = line.product_id.categ_id.display_name
                        pdt_qty = line.quantity
                        sale_price =line.price_unit * pdt_qty
                        cost_price = line.cost_price
                        # cost_price = (unit_cost_stock or pos_unit or bill_unit_of_cost ) * pdt_qty
                        discount = line.discount
                        profit = sale_price - cost_price
                        tax = line.tax_ids
                        tax_amount=0.0
                        for tax_line in tax:
                            tax_amount = tax_line.amount
                        tax_individual_amount = tax_amount   
                        
                        # if sale_price!=0:
                        #     percent_margin = (profit / sale_price)*100
                        
                        untax_total = sale_price - (tax_individual_amount * sale_price /100)
                        tax_amt = sale_price - untax_total
    
                 
                        self.create({
                            'invoice_number':name,
                            'invoice_date':date,
                            'product_category':category,
                            'account_analytic_id':analytic_account_id,
                            'product_id':product_id,
                            'product_quantity':pdt_qty,
                            'product_cost':cost_price,
                            'product_sales':sale_price,
                            'product_discount':discount,
                            'product_profit':profit,
                            # 'product_margin':percent_margin,
                            'customer_name':partner_id,
                            'tax_individual':tax_amt,
                            'invoice_date_time':date_time,
                            # 'invoice_time':datetime.strptime(date_time,'%Y-%m-%d %H:%M:%S').time().hour
                             'untaxed_total':untax_total,
                            'invoice_time':display_date_result
,
                           
                               
                            })
                action = self.sudo().env.ref('sh_accounting_reports.invoice_product_profit_act_window').read()[0]
                return action
                

                
        if self.sh_move_type == "out_refund":    
            if self.sh_move_type == "out_refund"  and self.report_by_customer == "customer_report":
        
                move_detail = self.env['account.move'].search([('move_type','=','out_refund'),('invoice_date','>=',self.sh_start_date),('invoice_date','<=',self.sh_end_date),('state','=','posted'),('company_id', '=', self.company_ids.ids),('partner_id','=',sh_partner_ids.ids)])
            
                for move in move_detail:
                    name = move.name
                    partner_id = move.partner_id.display_name
                    date =move.invoice_date
                    date_time = move.datetime_invoice
                    reference = 0
                    unit_cost_stock = 0
                    pos_unit = 0
                    bill_unit_of_cost = 0
                    unit_cost=0
                    bill_unit =0 
                    
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
                        #

                        
                        product_id = line.product_id.id
                        analytic_account_id = line.analytic_account_id.id
                        category = line.product_id.categ_id.display_name
                        pdt_qty = line.quantity
                        sale_price =line.price_unit * pdt_qty
                        cost_price = line.cost_price
                        # cost_price = (unit_cost_stock or pos_unit or bill_unit_of_cost ) * pdt_qty
                        discount = line.discount
                        profit = sale_price - cost_price
                        tax = line.tax_ids
                        tax_amount=0.0
                        for tax_line in tax:
                            tax_amount = tax_line.amount
                        tax_individual_amount = tax_amount   
                        
                        # if sale_price!=0:
                        #     percent_margin = (profit / sale_price)*100
                        
                        untax_total = sale_price - (tax_individual_amount * sale_price /100)
                        tax_amt = sale_price - untax_total
    
                 
                        self.create({
                            'invoice_number':name,
                            'invoice_date':date,
                            'product_category':category,
                            'account_analytic_id':analytic_account_id,
                            'product_id':product_id,
                            'product_quantity':pdt_qty,
                            'product_cost':cost_price,
                            'product_sales':sale_price,
                            'product_discount':discount,
                            'product_profit':profit,
                            # 'product_margin':percent_margin,
                            'customer_name':partner_id,
                            'tax_individual':tax_amt,
                            'invoice_date_time':date_time,
                            'untaxed_total':untax_total,
                               
                         })
                        
                action = self.sudo().env.ref('sh_accounting_reports.invoice_product_profit_act_window').read()[0]
                return action
         
         
        if self.sh_move_type == "in_invoice":    
            if self.sh_move_type == "in_invoice"  and self.report_by_vendor == "vendor_report":
        
                move_detail = self.env['account.move'].search([('move_type','=','in_invoice'),('invoice_date','>=',self.sh_start_date),('invoice_date','<=',self.sh_end_date),('state','=','posted'),('company_id', '=', self.company_ids.ids),('partner_id','=',sh_partner_ids.ids)])
            
                for move in move_detail:
                    name = move.name
                    partner_id = move.partner_id.display_name
                    date =move.invoice_date
                    date_time = move.datetime_invoice
                    reference = 0
                    unit_cost_stock = 0
                    pos_unit = 0
                    bill_unit_of_cost = 0
                    unit_cost=0
                    bill_unit =0 
                    
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

                        
                        
                        product_id = line.product_id.id
                        analytic_account_id = line.analytic_account_id.id
                        category = line.product_id.categ_id.display_name
                        pdt_qty = line.quantity
                        sale_price =line.price_unit * pdt_qty
                        cost_price = line.cost_price
                        # cost_price = (unit_cost_stock or pos_unit or bill_unit_of_cost ) * pdt_qty
                        discount = line.discount
                        profit = sale_price - cost_price
                        tax = line.tax_ids
                        tax_amount=0.0
                        for tax_line in tax:
                            tax_amount = tax_line.amount
                        tax_individual_amount = tax_amount   
                        
                        # if sale_price!=0:
                        #     percent_margin = (profit / sale_price)*100
                        #

                        untax_total = sale_price - (tax_individual_amount * sale_price /100)
                        tax_amt = sale_price - untax_total
    
                 
                        self.create({
                            'invoice_number':name,
                            'invoice_date':date,
                            'product_category':category,
                            'account_analytic_id':analytic_account_id,
                            'product_id':product_id,
                            'product_quantity':pdt_qty,
                            'product_cost':cost_price,
                            'product_sales':sale_price,
                            'product_discount':discount,
                            'product_profit':profit,
                            # 'product_margin':percent_margin,
                            'customer_name':partner_id,
                            'tax_individual':tax_amt,
                            'invoice_date_time':date_time,
                            'untaxed_total':untax_total,
                               
                         })
                        
                        
                action = self.sudo().env.ref('sh_accounting_reports.invoice_product_profit_act_window').read()[0]
                return action
                                
        
    def print_report(self):
        datas = self.read()[0]
        return self.env.ref('sh_accounting_reports.sh_invoices_product_profit_action').report_action([], data=datas)

    def print_xls_report(self):
        pass
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Invoices Product Profit', bold_center)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        center = xlwt.easyxf('align: horiz center;')
        bold_center_total = xlwt.easyxf('align: horiz center;font:bold True')
        date_start = False
        date_stop = False
        if self.sh_start_date:
            date_start = fields.Date.from_string(self.sh_start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.sh_end_date:
            date_stop = fields.Date.from_string(self.sh_end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        if self.report_by_customer == 'customer_report':
            worksheet.write_merge(
                0, 1, 0, 9, 'Invoices Product Profit', heading_format)
            worksheet.write_merge(
                2, 2, 0, 9, date_start.strftime("%m-%d-%y") + " to " + date_stop.strftime("%m-%d-%y"), bold)
        elif self.report_by_customer == 'product':
            worksheet.write_merge(
                0, 1, 0, 9, 'Invoices Product Profit', heading_format)
            worksheet.write_merge(
                2, 2, 0, 9, date_start.strftime("%m-%d-%y") + " to " + date_stop.strftime("%m-%d-%y"), bold)
        elif self.report_by_customer == 'customer_product':
            worksheet.write_merge(
                0, 1, 0, 9, 'Invoices Product Profit', heading_format)
            worksheet.write_merge(
                2, 2, 0, 9, date_start.strftime("%m-%d-%y") + " to " + date_stop.strftime("%m-%d-%y"), bold)
        if self.report_by_vendor == 'vendor_report':
            worksheet.write_merge(
                0, 1, 0, 9, 'Invoices Product Profit', heading_format)
            worksheet.write_merge(
                2, 2, 0, 9, date_start.strftime("%m-%d-%y") + " to " + date_stop.strftime("%m-%d-%y"), bold)
        elif self.report_by_vendor == 'product':
            worksheet.write_merge(
                0, 1, 0, 9, 'Invoices Product Profit', heading_format)
            worksheet.write_merge(
                2, 2, 0, 9, date_start.strftime("%m-%d-%y") + " to " + date_stop.strftime("%m-%d-%y"), bold)
        elif self.report_by_vendor == 'customer_product':
            worksheet.write_merge(
                0, 1, 0, 9, 'Invoices Product Profit', heading_format)
            worksheet.write_merge(
                2, 2, 0, 9, date_start.strftime("%m-%d-%y") + " to " + date_stop.strftime("%m-%d-%y"), bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        worksheet.col(7).width = int(15 * 260)
        move_dic_by_customers = {}
        move_dic_by_products = {}
        both_move_list = []
        report_by = ''
        unit_cost_stock = 0.00
        reference = 0
        pos_unit = 0
        unit_cost = 0
        bill_unit_of_cost = 0
        bill_unit = 0
        if self.sh_move_type == 'out_invoice' or self.sh_move_type == 'out_refund':
            report_by = 'customer'
            if self.report_by_customer == 'customer_report':
                partners = False
                if self.sh_partner_ids:
                    partners = self.env['res.partner'].sudo().browse(
                        self.sh_partner_ids.ids)
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
                        if self.sh_move_type == 'out_invoice' or self.sh_move_type == 'out_refund':
                            domain.append(
                                ('move_type', '=', self.sh_move_type))
                        if self.company_ids:
                            domain.append(
                                ('company_id', 'in', self.company_ids.ids))
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
                                        unit_cost = 0
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
                                            #         if not ref.product_id == line.product_id :
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
                                            #

                                            if not line.display_type:
                                                line_dic = {
                                                    'invoice_number': move.name,
                                                    'invoice_date': move.invoice_date,
                                                    'product_category' : line.product_id.categ_id.display_name,
                                                    'product' : line.product_id.display_name,
                                                    'analytic_account':line.analytic_account_id.name,
                                                    'qty': line.quantity,
                                                    'cost': line.cost_price,
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

            elif self.report_by_customer == 'product':
                report_by = 'product'
                products = False
                if self.sh_product_ids:
                    products = self.env['product.product'].sudo().browse(
                        self.sh_product_ids.ids)
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
                        if self.company_ids:
                            domain.append(
                                ('company_id', 'in', self.company_ids.ids))
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
                                            #     bill_unit_of_cost = bill_unit
                                            #

                                            if not line.display_type:
                                                line_dic = {
                                                    'invoice_number': move.name,
                                                    'invoice_date': move.invoice_date,
                                                    'product_category' : line.product_id.categ_id.display_name,
                                                    'analytic_account':line.analytic_account_id.name,
                                                    'customer': move.partner_id.name_get()[0][1],
                                                    'qty': line.quantity,
                                                    'cost': line.cost_price,
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

            elif self.report_by_customer == 'customer_product':
                report_by = 'customer with product'
                products = False
                partners = False
                if self.sh_product_ids:
                    products = self.env['product.product'].sudo().browse(
                        self.sh_product_ids.ids)
                else:
                    products = self.env['product.product'].sudo().search([])
                if self.sh_partner_ids:
                    partners = self.env['res.partner'].sudo().browse(
                        self.sh_partner_ids.ids)
                else:
                    partners = self.env['res.partner'].sudo().search([])
                for partner_id in partners:

                    domain = [
                        ("invoice_date", ">=", fields.Date.to_string(date_start)),
                        ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                        ("partner_id", "=", partner_id.id),
                    ]
                    if self.sh_move_type == 'out_invoice' or self.sh_move_type == 'out_refund':
                        domain.append(
                            ('move_type', '=', self.sh_move_type))
                    if self.company_ids:
                        domain.append(
                            ('company_id', 'in', self.company_ids.ids))
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
                                                        'cost': line.cost_price,

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

        else:
            if self.report_by_vendor == 'vendor_report':
                report_by = 'vendor'
                partners = False
                if self.sh_partner_ids:
                    partners = self.env['res.partner'].sudo().browse(
                        self.sh_partner_ids.ids)
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
                        if self.sh_move_type == 'in_invoice' or self.sh_move_type == 'in_refund':
                            domain.append(
                                ("move_type", "=", self.sh_move_type))
                        if self.company_ids:
                            domain.append(
                                ('company_id', 'in', self.company_ids.ids))
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
                                        pdt_name = ""
                                        pdt_category = ""
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
                                                    'cost': line.cost_price,

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

            elif self.report_by_vendor == 'product':
                report_by = 'product'
                products = False
                if self.sh_product_ids:
                    products = self.env['product.product'].sudo().browse(
                        self.sh_product_ids.ids)
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
                        if self.company_ids:
                            domain.append(
                                ('company_id', 'in', self.company_ids.ids))
                        search_moves = self.env['account.move'].sudo().search(
                            domain)
                        # if search_moves.product_id:
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
                                            #     bill_unit_of_cost = bill_unit
                                            #

                                            if not line.display_type:
                                                line_dic = {
                                                    'invoice_number': move.name,
                                                    'invoice_date': move.invoice_date,
                                                    'product_category' : line.product_id.categ_id.display_name,
                                                    'analytic_account':line.analytic_account_id.name,
                                                    'customer': move.partner_id.name_get()[0][1],
                                                    'qty': line.quantity,
                                                     'cost': line.cost_price,
                                                    # 'cost':  unit_cost_stock or pos_unit or bill_unit_of_cost,
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

            elif self.report_by_vendor == 'vendor_product':
                report_by = 'vendor with product'
                products = False
                partners = False
                if self.sh_product_ids:
                    products = self.env['product.product'].sudo().browse(
                        (self.sh_product_ids.ids))
                else:
                    products = self.env['product.product'].sudo().search([])
                if self.sh_partner_ids:
                    partners = self.env['res.partner'].sudo().browse(
                        (self.sh_partner_ids.ids))
                else:
                    partners = self.env['res.partner'].sudo().search([])
                for partner_id in partners:

                    domain = [
                        ("invoice_date", ">=", fields.Date.to_string(date_start)),
                        ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                        ("partner_id", "=", partner_id.id)
                    ]
                    if self.sh_move_type == 'in_invoice' or self.sh_move_type == 'in_refund':
                        domain.append(
                            ("move_type", "=", self.sh_move_type))
                    if self.company_ids:
                        domain.append(
                            ('company_id', 'in', self.company_ids.ids))
                    search_moves = self.env['account.move'].sudo().search(
                        domain)
                    # if search_moves.partner_id:

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

                                    for product_id in products:
                                        if line.product_id.id == product_id.id:
                                            if not line.display_type:
                                                line_dic = {
                                                    'invoice_number': move.name,
                                                    'invoice_date': move.invoice_date,
                                                    'product_category' : line.product_id.categ_id.display_name,
                                                    'product' : line.product_id.display_name,
                                                    'analytic_account': line.analytic_account_id.name,
                                                    'customer': move.partner_id.name_get()[0][1],
                                                    'qty': line.quantity,
                                                    'cost': line.cost_price,
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

        row = 4
        if report_by == 'customer' or report_by == 'vendor':
            if move_dic_by_customers:
                for customer in move_dic_by_customers.keys():
                    worksheet.write_merge(
                        row, row, 0, 9, customer, bold_center)
                    row = row+2
                    total_cost = 0.0
                    total_sale_price = 0.0
                    total_profit = 0.0
                    total_margin = 0.0
                    worksheet.write(row, 0, "Invoice Number", bold)
                    worksheet.write(row, 1, "Invoice Date", bold)
                    worksheet.write(row,  2, "Product Category", bold)
                    worksheet.write(row,  3, "Analytic Account", bold)
                    worksheet.write(row, 4, "Product", bold)
                    worksheet.write(row, 5, "Quantity", bold)
                    worksheet.write(row, 6, "Cost", bold)
                    worksheet.write(row, 7, "Sale Price", bold)
                    worksheet.write(row, 8, "Discount", bold)
                    worksheet.write(row, 9, "Profit", bold)
                    # worksheet.write(row, 10, "Margin(%)", bold)
                    row += 1
                    for rec in move_dic_by_customers[customer]:
                        worksheet.write(row, 0, rec.get(
                            'invoice_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('invoice_date')), center)
                        worksheet.write(row, 2, str(
                            rec.get('product_category')), center)
                        worksheet.write(row, 3, 
                            rec.get('analytic_account') or " ", center)
                        worksheet.write(row, 4, rec.get('product'), center)
                        worksheet.write(row, 5, "{:.2f}".format(
                            rec.get('qty')), center)
                        # cost = rec.get('cost', 0.0) * rec.get('qty', 0.0)
                        cost = rec.get('cost', 0.0)

                        worksheet.write(row, 6, "{:.2f}".format(cost), center)
                        sale_price = (rec.get('sale_price', 0.0)*rec.get('qty', 0.0) - rec.get(
                            'sale_price', 0.0)*rec.get('qty', 0.0)*rec.get('discount')/100)
                        worksheet.write(
                            row, 7, "{:.2f}".format(sale_price), center)
                        worksheet.write(row, 8, "{:.2f}".format(
                            rec.get('discount')), center)
                        profit = ((rec.get('sale_price', 0.0)*rec.get('qty', 0.0))-rec.get('sale_price', 0.0)*rec.get(
                            'qty', 0.0)*rec.get('discount')/100) - (rec.get('cost', 0.0)*rec.get('qty', 0.0))
                        worksheet.write(
                            row, 9, "{:.2f}".format(profit), center)
                        # if sale_price != 0.0:
                        #     margin = (profit/sale_price)*100
                        # else:
                        #     margin = 0.00
                        # worksheet.write(
                        #     row, 10, "{:.2f}".format(margin), center)
                        total_cost = total_cost + cost
                        total_sale_price = total_sale_price + sale_price
                        if profit:
                            total_profit = total_profit + profit
                        # total_margin = total_margin + margin
                        row = row + 1
                        worksheet.write(row, 4, "Total", left)
                        worksheet.write(row, 6, "{:.2f}".format(
                            total_cost), bold_center_total)
                        worksheet.write(
                            row, 7, "{:.2f}".format(
                                total_sale_price), bold_center_total)
                        worksheet.write(row, 9, "{:.2f}".format(total_profit),
                                        bold_center_total)
                        # worksheet.write(row, 10, "{:.2f}".format(total_margin),
                        #                 bold_center_total)
                    row = row + 2

        elif report_by == 'product':
            if move_dic_by_products:
                for product in move_dic_by_products.keys():
                    worksheet.write_merge(
                        row, row, 0, 9, product, bold_center)
                    row += 2
                    total_cost = 0.0
                    total_sale_price = 0.0
                    total_profit = 0.0
                    total_margin = 0.0
                    worksheet.write(row, 0, "Invoice Number", bold)
                    worksheet.write(row, 1, "Invoice Date", bold)
                    worksheet.write(row,  2, "Product Category", bold)
                    worksheet.write(row,  3, "Analytic Account", bold)
                    worksheet.write(row, 4, "Customer", bold)
                    worksheet.write(row, 5, "Quantity", bold)
                    worksheet.write(row, 6, "Cost", bold)
                    worksheet.write(row, 7, "Sale Price", bold)
                    worksheet.write(row, 8, "Discount", bold)
                    worksheet.write(row, 9, "Profit", bold)
                    # worksheet.write(row, 10, "Margin(%)", bold)
                    row += 1
                    for rec in move_dic_by_products[product]:
                        worksheet.write(row, 0, rec.get(
                            'invoice_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('invoice_date')), center)
                        
                        worksheet.write(row, 2, str(
                            rec.get('product_category')), center)
                        worksheet.write(row, 3, 
                            rec.get('analytic_account') or " ", center)
                        
                        worksheet.write(row, 4, rec.get('customer'), center)
                        
                        worksheet.write(row, 5, "{:.2f}".format(
                            rec.get('qty')), center)
                        # cost = rec.get('cost', 0.0) * rec.get('qty', 0.0)
                        cost = rec.get('cost', 0.0)
                        worksheet.write(row, 6, "{:.2f}".format(cost), center)
                        
                        sale_price = (rec.get('sale_price', 0.0)*rec.get('qty', 0.0) - rec.get(
                            'sale_price', 0.0)*rec.get('qty', 0.0)*rec.get('discount')/100)
                        worksheet.write(
                            row, 7, "{:.2f}".format(sale_price), center)
                        profit = ((rec.get('sale_price', 0.0)*rec.get('qty', 0.0))-rec.get('sale_price', 0.0)*rec.get(
                            'qty', 0.0)*rec.get('discount')/100) - (rec.get('cost', 0.0)*rec.get('qty', 0.0))
                        worksheet.write(
                            row, 8, "{:.2f}".format(rec.get('discount')), center)
                        worksheet.write(
                            row, 9, "{:.2f}".format(profit), center)
                        # if sale_price != 0.0:
                        #     margin = (profit/sale_price)*100
                        # else:
                        #     margin = 0.00
                        # worksheet.write(
                        #     row, 10, "{:.2f}".format(margin), center)
                        total_cost = total_cost + cost
                        total_sale_price = total_sale_price + sale_price
                        if profit:
                            total_profit = total_profit + profit
                        # total_margin = total_margin + margin
                        row += 1
                        worksheet.write(row, 4, "Total", left)
                        worksheet.write(row, 6, "{:.2f}".format(
                            total_cost), bold_center_total)
                        worksheet.write(
                            row, 7, "{:.2f}".format(
                                total_sale_price), bold_center_total)
                        worksheet.write(row, 9, "{:.2f}".format(total_profit),
                                        bold_center_total)
                        # worksheet.write(row, 10, "{:.2f}".format(total_margin),
                        #                 bold_center_total)
                    row += 2
        elif report_by == 'customer with product' or report_by == 'vendor with product':
            total_cost = 0.0
            total_sale_price = 0.0
            total_profit = 0.0
            total_margin = 0.0
            worksheet.write(row, 0, "Invoice Number", bold)
            worksheet.write(row, 1, "Invoice Date", bold)
            worksheet.write(row,  2, "Product Category", bold)
            worksheet.write(row,  3, "Analytic Account", bold)
            worksheet.write(row, 4, "Customer", bold)
            worksheet.write(row, 5, "Product", bold)
            worksheet.write(row, 6, "Quantity", bold)
            worksheet.write(row, 7, "Cost", bold)
            worksheet.write(row, 8, "Sale Price", bold)
            worksheet.write(row, 9, "Discount", bold)
            worksheet.write(row, 10, "Profit", bold)
            # worksheet.write(row, 11, "Margin(%)", bold)
            row = row + 1
            if both_move_list:
                for order in both_move_list:
                    worksheet.write(row, 0, order.get(
                        'invoice_number'), center)
                    worksheet.write(row, 1, str(
                        order.get('invoice_date')), center)
                    
                    worksheet.write(row, 2, str(
                            order.get('product_category')), center)
                    worksheet.write(row, 3, 
                            order.get('analytic_account') or " ", center)
                        
                    worksheet.write(row, 4, order.get('customer'), center)
                    worksheet.write(row, 5, order.get('product'), center)
                    worksheet.write(row, 6, "{:.2f}".format(
                        order.get('qty')), center)
                    # cost = order.get('cost', 0.0) * order.get('qty', 0.0)
                    cost = order.get('cost', 0.0)

                    worksheet.write(row, 7, "{:.2f}".format(cost), center)
                    sale_price = (order.get('sale_price', 0.0)*order.get('qty', 0.0) - order.get(
                        'sale_price', 0.0)*order.get('qty', 0.0)*order.get('discount')/100)
                    worksheet.write(
                        row, 8, "{:.2f}".format(sale_price), center)
                    profit = ((order.get('sale_price', 0.0)*order.get('qty', 0.0))-order.get('sale_price', 0.0)*order.get(
                        'qty', 0.0)*order.get('discount')/100) - (order.get('cost', 0.0)*order.get('qty', 0.0))
                    worksheet.write(
                        row, 9, "{:.2f}".format(order.get('discount')), center)
                    worksheet.write(
                        row, 10, "{:.2f}".format(profit), center)
                    # if sale_price != 0.0:
                    #     margin = (profit/sale_price)*100
                    # else:
                    #     margin = 0.00
                    # worksheet.write(
                    #     row, 11, "{:.2f}".format(margin), center)
                    total_cost = total_cost + cost
                    total_sale_price = total_sale_price + sale_price
                    if profit:
                        total_profit = total_profit + profit
                    # total_margin = total_margin + margin
                    row += 1
                    worksheet.write(row, 5, "Total", left)
                    worksheet.write(row, 7, "{:.2f}".format(
                        total_cost), bold_center_total)
                    worksheet.write(
                        row, 8, "{:.2f}".format(
                            total_sale_price), bold_center_total)
                    worksheet.write(row, 10, "{:.2f}".format(total_profit),
                                    bold_center_total)
                    # worksheet.write(row, 11, "{:.2f}".format(total_margin),
                    #                 bold_center_total)
                row += 2
        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "Invoices Product Profit.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'Invoices Product Profit.xls'),
                                          ('type', '=', 'binary'),
                                          ('res_model', '=', 'ir.ui.view')],
                                         limit=1)
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError('There is no attachments...')

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
                 
        }
