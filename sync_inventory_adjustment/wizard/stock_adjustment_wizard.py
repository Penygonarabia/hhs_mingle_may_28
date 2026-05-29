from odoo import api, fields, models
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, date, timezone
import pytz
from dateutil import tz
from dateutil.tz import tzutc, tzlocal
from odoo.exceptions import warnings
from collections import defaultdict
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class StockAdjustment(models.TransientModel):
    _name = 'stock.adjustment.report'
    _description = 'Stock Adjustment Report'

    start_date = fields.Date(required=True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    end_date = fields.Date(required=True, default=lambda self: fields.Date.to_string(
        (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    product_ids = fields.Many2many(
        'product.product', string='Product' )
    # warehouse_ids = fields.Many2one('stock.warehouse', string='Warehouse')
    location_id = fields.Many2one(
        'stock.location', 'Location',
        help="Select a location.")
    # to_collapse = fields.Boolean(string='Collapse', default=False)
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, index=True,
        default=lambda self: self.env.user.company_id)
    category_id = fields.Many2one('product.category',string="Product Category")


    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    # @api.onchange('product_ids')
    # def onchange_product_ids(self):
    #     if self.product_ids:
    #         category_ids = self.product_ids.mapped('categ_id.id')
    #         # Assuming you want to set the category based on the category of the first selected product.
    #         self.category_id = category_ids[0] if category_ids else False

    # @api.onchange('to_collapse')
    # def _onchange_product(self):
    #     if self.to_collapse == True:
    #         total_list = []
    #         for rec in self:
    #             if rec.warehouse_ids:
    #                 stock = self.env['stock.quant'].sudo().search([('location_id', '=', rec.location_id.ids)])
    #                 for record in stock:
    #                     total_list.append(record.product_id.id)
    #                 self.update({'product_ids': [(6, 0, total_list)]})


    # def _get_products(self, record):
    #     product_product_obj = self.env['product.product']
    #     domain = [('type', '=', 'product')]
    #     product_ids = False
    #     if record.category_ids:
    #         domain.append(('categ_id', 'child_of', record.category_ids.ids))
    #         product_ids = product_product_obj.search(domain)
    #     if record.product_ids:
    #         product_ids = record.product_ids
    #     if not product_ids:
    #         product_ids = product_product_obj.search(domain)
    #     return product_ids

    # @api.onchange('category_id')
    # def _onchange_product_category(self):
    #     domain = [('categ_id', 'in', self.category_id.ids)]
    #     return {'domain': {'product_ids': domain}}

    # @api.onchange('warehouse_ids')
    # def onchange_warehouse_ids(self):
    #     if self.warehouse_ids:
    #         loc_wh = self.location_id.warehouse_id
    #         res = {}
    #         if self.warehouse_ids != loc_wh:
    #             self.location_id = self.warehouse_ids.lot_stock_id
    #         if self.warehouse_ids.company_id != self.company_id:
    #             self.company_id = self.warehouse_ids.company_id
    #         # res['domain'] = {'location_id': [('id', '=', self.warehouse_ids.ids)]}
    #         # return res
    #     else:
    #         self.location_id = None

    # def generate_report(self):
    #     data = {
    #         'date_start': self.start_date,
    #         'date_stop': self.end_date,
    #         'product_ids': self.product_ids.mapped('id'),
    #         'location_id': self.location_id.id,
    #         'to_collapse': self.to_collapse,
    #         'report_head': f'Movement Report in {self.location_id.name_get()[0][1]}'
    #     }
    #     return self.env.ref('custom_moves_report.moves_report').report_action([], data=data)

    # ~ def print_report_xls(self):
        # ~ datas = {
            # ~ 'model': 'stock_adjustment_report',
            # ~ 'form_data': self.read()[0]
        # ~ }
        # ~ return self.env.ref('sync_inventory_adjustment.action_stock_adjustment_report_xlsx').report_action(self, data=datas)

    def pdf_generate_report(self):
        domain = []

        start_date = self.start_date
        end_date = self.end_date
        company_id = self.company_id
        product_ids = self.product_ids
        category_id = self.category_id
        location_id = self.location_id
        # warehouse_ids = self.warehouse_ids


        if self.location_id and self.category_id and self.product_ids:
            # Find the selected category and its child categories
            selected_category = self.env['product.category'].browse(self.category_id.id)
            category_ids = selected_category.search([('id', 'child_of', selected_category.id)]).ids

            stock_location = self.env['stock.inventory'].search([
                ('location_id', '=', self.location_id.id),
                ('category_id', 'in', category_ids),  # Use 'in' to search for child categories
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date)
            ])

            sub_total = 0.00
            adjusted_qty = 0.00
            parent_categories = []

            for stock in stock_location:
                location_name = stock.location_id.display_name
                parent_category = stock.category_id.parent_id or stock.category_id
                category_name = parent_category.display_name  # Moved category_name assignment here

                # if parent_category not in parent_categories:
                #     # Create a new header row for the parent category
                #     parent_categories[parent_category] = row


                for line in stock.line_ids:
                    if line.product_id in self.product_ids:
                        name = stock.name
                        date = stock.date
                        code = line.product_id.default_code
                        product = line.product_id.display_name
                        theoretical_qty = line.theoretical_qty
                        remarks = stock.remarks
                        product_qty = line.product_qty
                        adjusted_qty = line.product_qty - line.theoretical_qty
                        cost = line.product_id.standard_price
                        sub_total = adjusted_qty * cost
                        created_by = stock.create_uid.name
                        parent_categories.append({
                            'location_name':location_name,
                            'category_name':category_name,
                            'name': name,
                            'date': date,
                            # 'code': code,
                            'product': product,
                            'theoretical_qty': theoretical_qty,
                            'remarks': remarks,
                            'product_qty': product_qty,
                            'adjusted_qty': adjusted_qty,
                            'cost': cost,
                            'sub_total': sub_total,
                            'remarks' : remarks,
                            'created_by': created_by
                        })
            if not parent_categories:
                raise UserError("No data found for the selected criteria.")

            # Create a dictionary to pass to the QWeb template
            report_data = {
                'form_data': self.read()[0],
                'parent_categories': parent_categories,
            }

            # Render the report using the QWeb template and return it as a PDF
            return self.env.ref('sync_inventory_adjustment.action_report_location_category_product_template').with_context(landscape=True).report_action(self, data=report_data)

        elif self.location_id and self.category_id:
            # Find the selected category and its child categories
            selected_category = self.env['product.category'].browse(self.category_id.id)
            category_ids = selected_category.search([('id', 'child_of', selected_category.id)]).ids

            stock_location = self.env['stock.inventory'].search([
                ('location_id', '=', self.location_id.id),
                ('category_id', 'in', category_ids),  # Use 'in' to search for child categories
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date)
            ])

            sub_total = 0.00
            adjusted_qty = 0.00
            parent_categories = []

            for stock in stock_location:
                location_name = stock.location_id.display_name
                parent_category = stock.category_id.parent_id or stock.category_id
                category_name = parent_category.display_name  # Moved category_name assignment here

                # if parent_category not in parent_categories:
                #     # Create a new header row for the parent category
                #     parent_categories[parent_category] = row


                for line in stock.line_ids:
                    name = stock.name
                    date = stock.date
                    code = line.product_id.default_code
                    product = line.product_id.display_name
                    theoretical_qty = line.theoretical_qty
                    remarks = stock.remarks
                    product_qty = line.product_qty
                    adjusted_qty = line.product_qty - line.theoretical_qty
                    cost = line.product_id.standard_price
                    sub_total = adjusted_qty * cost
                    created_by = stock.create_uid.name
                    parent_categories.append({
                            'location_name':location_name,
                            'category_name':category_name,
                            'name': name,
                            'date': date,
                            # 'code': code,
                            'product': product,
                            'theoretical_qty': theoretical_qty,
                            'remarks': remarks,
                            'product_qty': product_qty,
                            'adjusted_qty': adjusted_qty,
                            'cost': cost,
                            'sub_total': sub_total,
                            'remarks': remarks,
                            'created_by': created_by
                        })
            if not parent_categories:
                raise UserError("No data found for the selected criteria.")

            # Create a dictionary to pass to the QWeb template
            report_data = {
                'form_data': self.read()[0],
                'parent_categories': parent_categories,
            }

            # Render the report using the QWeb template and return it as a PDF
            return self.env.ref('sync_inventory_adjustment.action_report_location_category_template').with_context(landscape=True).report_action(self, data=report_data)

        elif self.location_id and self.product_ids:
            stock_location = self.env['stock.inventory'].search([
                ('location_id', '=', self.location_id.id),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date)
            ])
            sub_total = 0.00
            adjusted_qty = 0.00
            previous_stock_name = ''
            location_data = []
            for stock in stock_location:
                if stock.location_id == self.location_id:
                    location_name = stock.location_id.display_name
                    for line in stock.line_ids:
                        if line.product_id in self.product_ids:
                            if stock.name != previous_stock_name:
                                previous_stock_name = stock.name
                            name = stock.name
                            date = stock.date
                            code = line.product_id.default_code
                            product = line.product_id.display_name
                            theoretical_qty = line.theoretical_qty
                            remarks = stock.remarks
                            product_qty = line.product_qty
                            adjusted_qty = line.product_qty - line.theoretical_qty
                            cost = line.product_id.standard_price
                            sub_total = adjusted_qty * cost
                            created_by = stock.create_uid.name
                            location_data.append({
                                'location_name': location_name,
                                'name': name,
                                'date': date,
                                # 'code': code,
                                'product': product,
                                'theoretical_qty': theoretical_qty,
                                'remarks': remarks,
                                'product_qty': product_qty,
                                'adjusted_qty': adjusted_qty,
                                'cost': cost,
                                'sub_total': sub_total,
                                'remarks': remarks,
                                'created_by': created_by
                            })
            if not location_data:
                raise UserError("No data found for the selected criteria.")

            # Create a dictionary to pass to the QWeb template
            report_data = {
                'form_data': self.read()[0],
                'location_data': location_data,
            }

            # Render the report using the QWeb template and return it as a PDF
            return self.env.ref('sync_inventory_adjustment.action_report_location_product_template').with_context(
                landscape=True).report_action(self, data=report_data)



        elif self.location_id:
            stock_location = self.env['stock.inventory'].search([
                ('location_id', '=', self.location_id.id),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date)
            ])
            location_data = []
            for stock in stock_location:
                if stock.location_id == self.location_id:
                    location_name = stock.location_id.display_name
                    for line in stock.line_ids:
                        name = stock.name
                        date = stock.date
                        code = line.product_id.default_code
                        product = line.product_id.display_name
                        theoretical_qty = line.theoretical_qty
                        remarks = stock.remarks
                        product_qty = line.product_qty
                        adjusted_qty = line.product_qty - line.theoretical_qty
                        cost = line.product_id.standard_price
                        sub_total = adjusted_qty * cost
                        created_by = stock.create_uid.name

                        # Append data to the location group
                        location_data.append({
                            'location_name':location_name,
                            'name': name,
                            'date': date,
                            # 'code': code,
                            'product': product,
                            'theoretical_qty': theoretical_qty,
                            'remarks': remarks,
                            'product_qty': product_qty,
                            'adjusted_qty': adjusted_qty,
                            'cost': cost,
                            'sub_total': sub_total,
                            'remarks': remarks,
                            'created_by': created_by
                        })
            if not location_data:
                raise UserError("No data found for the selected criteria.")

            # Create a dictionary to pass to the QWeb template
            report_data = {
                'form_data': self.read()[0],
                'location_data': location_data,
            }

            # Render the report using the QWeb template and return it as a PDF
            return self.env.ref('sync_inventory_adjustment.action_report_location_template').with_context(landscape=True).report_action(self, data=report_data)


        elif self.category_id and self.product_ids:
            stock_location = self.env['stock.inventory'].search([
                ('category_id', 'child_of', self.category_id.id),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date)
            ])

            sub_total = 0.00
            adjusted_qty = 0.00

            parent_categories = []  # To track parent categories and their child data

            for stock in stock_location:
                parent_category = stock.category_id.parent_id or stock.category_id
                if parent_category not in parent_categories:
                    # Create a new header row for the parent category
                    category_name = parent_category.display_name
                #     parent_categories[parent_category] = row
                #
                # row_for_category = parent_categories[parent_category]

                for line in stock.line_ids:
                    if line.product_id in self.product_ids:
                        name = stock.name
                        date = stock.date
                        code = line.product_id.default_code
                        product = line.product_id.display_name
                        theoretical_qty = line.theoretical_qty
                        remarks = stock.remarks
                        product_qty = line.product_qty
                        adjusted_qty = line.product_qty - line.theoretical_qty
                        cost = line.product_id.standard_price
                        sub_total = adjusted_qty * cost
                        created_by = stock.create_uid.name
                        location_name = stock.location_id.display_name

                        parent_categories.append({
                            'category_name' : category_name,
                            'name': name,
                            'date': date,
                            # 'code': code,
                            'product': product,
                            'theoretical_qty': theoretical_qty,
                            'remarks': remarks,
                            'product_qty': product_qty,
                            'adjusted_qty': adjusted_qty,
                            'cost': cost,
                            'sub_total': sub_total,
                            'created_by': created_by

                        })
            if not parent_categories:
                raise UserError("No data found for the selected criteria.")
            # Create a dictionary to pass to the QWeb template
            report_data = {
                'form_data': self.read()[0],
                'parent_categories': parent_categories,
            }

            # Render the report using the QWeb template and return it as a PDF
            return self.env.ref('sync_inventory_adjustment.action_report_category_product_template').with_context(
                landscape=True).report_action(self, data=report_data)


        # elif self.start_date and self.end_date:
        #     # Fetch stock adjustments based on the selected date range
        #     stock_adjustment = self.env['stock.inventory'].search([
        #         ('date', '>=', self.start_date),
        #         ('date', '<=', self.end_date)
        #     ])
        #
        #     # Create a dictionary to store data grouped by location_id
        #     location_data = {}
        #
        #     # Loop through the stock adjustments and group them by location_id
        #     for stock in stock_adjustment:
        #         stock_location = self.env['stock.inventory'].search([
        #             ('location_id', '=', stock.location_id.id),
        #             ('date', '>=', self.start_date),
        #             ('date', '<=', self.end_date)
        #         ])
        #         if stock_location:
        #             location_name = stock_location.location_id.display_name
        #
        #             if location_name not in location_data:
        #                 location_data[location_name] = []
        #
        #             for line in stock_location.line_ids:
        #                 name = stock.name
        #                 date = stock.date
        #                 code = line.product_id.default_code
        #                 product = line.product_id.display_name
        #                 theoretical_qty = line.theoretical_qty
        #                 remarks = stock.remarks
        #                 product_qty = line.product_qty
        #                 adjusted_qty = line.product_qty - line.theoretical_qty
        #                 cost = line.product_id.standard_price
        #                 sub_total = adjusted_qty * cost
        #                 created_by = stock.create_uid.name
        #
        #                 # Append data to the location group
        #                 location_data[location_name].append({
        #                     'serial_number': len(location_data[location_name]) + 1,  # Serial number within each location
        #                     'name': name,
        #                     'date': date,
        #                     'code': code,
        #                     'product': product,
        #                     'theoretical_qty': theoretical_qty,
        #                     'remarks': remarks,
        #                     'product_qty': product_qty,
        #                     'adjusted_qty': adjusted_qty,
        #                     'cost': cost,
        #                     'sub_total': sub_total,
        #                     'created_by': created_by
        #                 })
        #
        #     # Create a dictionary to pass to the QWeb template
        #     report_data = {
        #         'form_data': self.read()[0],
        #         'location_data': location_data,
        #     }
        #
        #     # Render the report using the QWeb template and return it as a PDF
        #     return self.env.ref('sync_inventory_adjustment.action_report_inventory_template').with_context(landscape=True).report_action(self, data=report_data)

        elif self.category_id:
            stock_location = self.env['stock.inventory'].search([
                ('category_id', 'child_of', self.category_id.id),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date)
            ])

            sub_total = 0.00
            adjusted_qty = 0.00

            parent_categories = []  # To track parent categories and their child data

            for stock in stock_location:
                parent_category = stock.category_id.parent_id or stock.category_id
                if parent_category not in parent_categories:
                    # Create a new header row for the parent category
                    category_name = parent_category.display_name
                #     parent_categories[parent_category] = row
                #
                # row_for_category = parent_categories[parent_category]

                for line in stock.line_ids:
                    name = stock.name
                    date = stock.date
                    code = line.product_id.default_code
                    product = line.product_id.display_name
                    theoretical_qty = line.theoretical_qty
                    remarks = stock.remarks
                    product_qty = line.product_qty
                    adjusted_qty = line.product_qty - line.theoretical_qty
                    cost = line.product_id.standard_price
                    sub_total = adjusted_qty * cost
                    created_by = stock.create_uid.name
                    location_name = stock.location_id.display_name

                    parent_categories.append({
                        'name': name,
                        'date': date,
                        # 'code': code,
                        'product': product,
                        'theoretical_qty': theoretical_qty,
                        'remarks': remarks,
                        'product_qty': product_qty,
                        'adjusted_qty': adjusted_qty,
                        'cost': cost,
                        'sub_total': sub_total,
                        'created_by': created_by

                    })
            if not parent_categories:
                raise UserError("No data found for the selected criteria.")
            # Create a dictionary to pass to the QWeb template
            report_data = {
                'form_data': self.read()[0],
                'parent_categories': parent_categories,
            }

            # Render the report using the QWeb template and return it as a PDF
            return self.env.ref('sync_inventory_adjustment.action_report_category_template').with_context(
                landscape=True).report_action(self, data=report_data)

        elif self.product_ids:
            stock_location = self.env['stock.inventory'].search([
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date)
            ])
            product_list = []
            sub_total = 0.00
            adjusted_qty = 0.00
            previous_stock_name = ''
            for stock in stock_location:
                for line in stock.line_ids:
                    if line.product_id in self.product_ids:
                        if stock.name != previous_stock_name:
                            # If the stock name has changed, write a header row
                            previous_stock_name = stock.name
                        # name = stock.name
                        date = stock.date
                        code = line.product_id.default_code
                        product = line.product_id.display_name
                        theoretical_qty = line.theoretical_qty
                        remarks = stock.remarks
                        product_qty = line.product_qty
                        adjusted_qty = line.product_qty - line.theoretical_qty
                        cost = line.product_id.standard_price
                        sub_total = adjusted_qty * cost
                        created_by = stock.create_uid.name
                        product_list.append({
                            # 'location_name':location_name,
                            # 'category_name':category_name,
                            'name': previous_stock_name,
                            'date': date,
                            # 'code': code,
                            'product': product,
                            'theoretical_qty': theoretical_qty,
                            'remarks': remarks,
                            'product_qty': product_qty,
                            'adjusted_qty': adjusted_qty,
                            'cost': cost,
                            'sub_total': sub_total,
                            'created_by': created_by
                        })

            if not product_list:
                raise UserError("No data found for the selected criteria.")
            # Create a dictionary to pass to the QWeb template
            report_data = {
                'form_data': self.read()[0],
                'product_list': product_list,
            }

            # Render the report using the QWeb template and return it as a PDF
            return self.env.ref(
                'sync_inventory_adjustment.action_report_product_template').with_context(
                landscape=True).report_action(self, data=report_data)




        elif self.start_date and self.end_date:
            # Fetch stock adjustments based on the selected date range
            stock_adjustment = self.env['stock.inventory'].search([
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date)
            ])

            # Create a dictionary to store data grouped by location_id
            location_data = {}

            # Loop through the stock adjustments and group them by location_id
            for stock in stock_adjustment:
                location_name = stock.location_id.display_name

                if location_name not in location_data:
                    location_data[location_name] = []

                for line in stock.line_ids:
                    name = stock.name
                    date = stock.date
                    code = line.product_id.default_code
                    product = line.product_id.display_name
                    theoretical_qty = line.theoretical_qty
                    remarks = stock.remarks
                    product_qty = line.product_qty
                    adjusted_qty = line.product_qty - line.theoretical_qty
                    cost = line.product_id.standard_price
                    sub_total = adjusted_qty * cost
                    created_by = stock.create_uid.name

                    # Append data to the location group
                    location_data[location_name].append({
                        'serial_number': len(location_data[location_name]) + 1,  # Serial number within each location
                        'name': name,
                        'date': date,
                        # 'code': code,
                        'product': product,
                        'theoretical_qty': theoretical_qty,
                        'remarks': remarks,
                        'product_qty': product_qty,
                        'adjusted_qty': adjusted_qty,
                        'cost': cost,
                        'sub_total': sub_total,
                        'created_by': created_by
                    })

            if not location_data:
                raise UserError("No data found for the selected criteria.")

            # Create a dictionary to pass to the QWeb template
            report_data = {
                'form_data': self.read()[0],
                'location_data': location_data,
            }

            # Render the report using the QWeb template and return it as a PDF
            return self.env.ref('sync_inventory_adjustment.action_report_inventory_template').with_context(landscape=True).report_action(self, data=report_data)
