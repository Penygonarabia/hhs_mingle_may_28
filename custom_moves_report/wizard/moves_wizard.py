from odoo import api, fields, models
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, date, timezone
import pytz
from dateutil import tz
from dateutil.tz import tzutc, tzlocal

class movesDetails(models.TransientModel):
    _name = 'moves.details.report'
    _description = 'Product Moves Report'

    start_date = fields.Date(required = True, default = lambda self: fields.Date.to_string(date.today().replace(day=1)))
    end_date = fields.Date(required = True, default = lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    product_ids = fields.Many2many(
        'product.product', string = 'Product', required = True,)
    warehouse_ids = fields.Many2many('stock.warehouse', string = 'Warehouse')
    location_id = fields.Many2one(
        'stock.location', 'Location', required=True,
        help="Select a location.")
    to_collapse = fields.Boolean(string = 'Collapse', default = False)
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly = True, index = True,
        default = lambda self: self.env.user.company_id)
    
    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    @api.onchange('to_collapse')
    def _onchange_product(self):
        if self.to_collapse == True:
            total_list = []
            for rec in self:
                if rec.warehouse_ids:
                    stock = self.env['stock.quant'].sudo().search([('location_id', '=', rec.location_id.ids)])
                    for record in stock:
                        total_list.append(record.product_id.id)
                    self.update({'product_ids': [(6, 0, total_list)]})

    @api.onchange('warehouse_ids')
    def onchange_warehouse_ids(self):
        if self.warehouse_ids:
            loc_wh = self.location_id.warehouse_id
            res = {} 
            if self.warehouse_ids != loc_wh:
                self.location_id = self.warehouse_ids.lot_stock_id
            if self.warehouse_ids.company_id != self.company_id:
                self.company_id = self.warehouse_ids.company_id
            res['domain'] = {'location_id': [('id', '=', self.warehouse_ids.ids)]}
            return res
        else:
            self.location_id = None

    def generate_report(self):
        data = {
            'date_start': self.start_date,
            'date_stop': self.end_date,
            'product_ids': self.product_ids.mapped('id'),
            'location_id': self.location_id.id,
            'to_collapse': self.to_collapse,
            'report_head': f'Movement Report in {self.location_id.name_get()[0][1]}'
        }
        return self.env.ref('custom_moves_report.moves_report').report_action([], data=data)

    def print_xls_report(self):
        datas={
             'model': 'custom_moves_report',
            'form_data':self.read()[0]
        
            }
        return self.env.ref('custom_moves_report.action_custom_moves_report_xlsx').report_action(self, data=datas)
        
        



















