from datetime import timedelta
import pytz

from odoo import fields, api, models


class movesReport(models.AbstractModel):

    _name = 'report.custom_moves_report.report_moves'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        data.update(
            {
            'product_ids': data.get('product_ids'),
            'location_id': data.get('location_id'),
            'date_start': data.get('date_start'),
            'date_stop': data.get('date_stop'),
            'report_head': data.get('report_head'),
            'to_collapse': data.get('to_collapse'),
            }
        )
        data.update(self.get_sale_details(data['date_start'], data['date_stop'], data['product_ids'], data['location_id'], data['to_collapse']))
        return data

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, products=False, location=False, to_collapse=False):
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        # else:
        #     # start by default today 00:00:00
        #     user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        #     today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
        #     date_start = today.astimezone(pytz.timezone('UTC'))

        if date_stop:
            date_stop = fields.Datetime.from_string(date_stop)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        # else:
        #     # stop by default today 23:59:59
        #     date_stop = date_start + timedelta(days=1, seconds=-1)
        #
        domain = [
            '&', '&', 
            ('state', '=', 'done'),
            ('product_id', 'in', products),
            ('date', '<=', fields.Date.to_string(date_stop)),
            '|',
            ('location_id', '=', location),
            ('location_dest_id', '=', location),
        ]
            
        all_moves = self.env['stock.move.line'].search(domain, order='date')
        prods = self.env['product.product'].search([('id', 'in', products)])
        prods = [prod.name_get()[0][1] for prod in prods]
        return{
            'products': prods,
            'data': list(self._process_moves(products, all_moves, date_start, location))
        }
    
    @api.model
    def _process_moves(self, products, all_moves, date_start, location):
        for product in products:
            lst = []
            total_out = 0
            total_in = 0
            opening_balance = 0
            balance = 0
            value = 0
            v_value=0
            in_value = 0
            out_value = 0
            individual_out_value = 0
            individual_in_value = 0
            val = 0
            total_int_value=0
            
            moves = all_moves.filtered(lambda r: r.product_id.id==product)
            if moves:
                balance = sum(-move.quantity if move.location_id.id==location else move.quantity for move in moves if move.date<=date_start)
                opening_balance = balance
           
                valuation_layer_ids = self.env['stock.valuation.layer'].search([('product_id','=',moves.product_id.ids)])
                for sto in valuation_layer_ids:
                    val = sto.unit_cost
                total_int_value = val
                value = opening_balance * total_int_value
                v_value = value
                
                moves = moves.filtered(lambda r: r.date>=date_start)
                for move in moves:
                    temp_dict = {}
                    individual_out_value = 0
                    individual_in_value = 0
                    if location == move.location_id.id:
                        temp_dict['out'] = move.quantity
                        temp_dict['in'] = '--'
                        balance += -(move.quantity)
                        total_out += move.quantity
                        total = move.quantity
                        out_value = total_int_value * total_out
                        individual_out_value = total_int_value * total
                        value = total_int_value * balance
                        
                    else:
                        temp_dict['in'] =  move.quantity
                        temp_dict['out'] = '--'
                        balance += move.quantity
                        total_in += move.quantity
                        tot_in = move.quantity
                        individual_in_value = total_int_value * tot_in
                        in_value = total_int_value * total_in
                        value =total_int_value * balance
                        
                    temp_dict['date'] = move.date
                    temp_dict['picking_type'] = self.substitute(move.picking_type_id.code)
                    temp_dict['balance'] = balance
                    temp_dict['value'] = value
                    temp_dict['v_value'] = "{:,.2f}".format(v_value )
                    temp_dict['in_value'] = "{:,.2f}".format(in_value )
                    temp_dict['individual_out_value'] = "{:,.2f}".format(individual_out_value)
                    temp_dict['individual_in_value'] =  "{:,.2f}".format(individual_in_value)
                    temp_dict['out_value'] = "{:,.2f}".format(out_value)
                    temp_dict['reference'] = move.reference
                    temp_dict['location_id'] = move.location_id.name_get()[0][1]
                    temp_dict['location_dest_id'] = move.location_dest_id.name_get()[0][1]
                    lst.append(temp_dict)
                
          
            yield {
                'opening_balance': opening_balance,
                'v_value':v_value,
                'total_in': total_in,
                'in_value':in_value,
                'total_out': total_out,
                'out_value': out_value,
                'balance': balance,
                'value':value,
                'lst': lst,
            }
     
        
    @staticmethod
    def substitute(code):
        return code.replace('_', " ").title() if code else code
