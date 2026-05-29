from odoo import api, fields, models, _
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, date, timezone
from odoo.exceptions import ValidationError


class StockRequestReportWizard(models.TransientModel):
    
    _name = "stock.request.report"
    
    _description = "Internal Stock Request Report"
    
    
    start_date = fields.Date(string="Start Date",required=True, default = lambda self:fields.Date.to_string(date.today().replace(day=1)))
    end_date = fields.Date(string="End Date",required=True, default = lambda self:fields.Date.to_string((datetime.now()+relativedelta(months = +1,day=1,days=-1)).date()))
    product_ids = fields.Many2many(
        'product.product', string = 'Product')
    source_location_id = fields.Many2one('stock.location', string='Requesting Warehouse')
    # destination_location_id = fields.Many2one('stock.location', string='To Location')
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly = True, index = True,
        default = lambda self: self.env.user.company_id)
    
    category_ids = fields.Many2many('product.category',domain="[('parent_id','=',False)]",string="Product Category")
    
    
    @api.constrains('start_date','end_date')
    def check_start_date_range(self):
        if self.end_date < self.start_date:
            raise ValidationError(_('End Date should be greater than Start Date.'))
    
    # @api.onchange('warehouse_id')
    # def _onchange_warehouse_id(self):
    #     for rec in self:
    #         location_line=[]
    #         res={}
    #         stock=self.env['stock.location'].search([('location_id','child_of',rec.warehouse_id.view_location_id.id)])
    #         for location in stock:
    #             location_line.append(location.id)
    #
    #         res['domain']={'location_id':[('id','in',location_line)]}
    #         return res
    #
    #
    # @api.onchange('location_id')
    # def _onchange_location_based_product(self):
    #     for rec in self:
    #         product_line =[]
    #         res = {}
    #         stock_location = self.env['stock.quant'].search([('location_id','=',rec.location_id.id)])
    #         for product in stock_location:
    #             product_line.append(product.product_id.id)
    #         res['domain'] = {'product_ids':[('id','in',product_line)]}
    #
    #         return res
    #

    def print_report_excel_internal(self):
        
        datas={
             'model': 'stock.request.report',
            'form_data':self.read()[0]
        
            }
        return self.env.ref('ak_material_request.action_report_stock_transfer_request_xlsx').report_action(self, data=datas)
        
        

