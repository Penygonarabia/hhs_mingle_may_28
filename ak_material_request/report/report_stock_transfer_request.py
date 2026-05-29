from odoo import fields, models, api, _
import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class StockTransferStatusReportExcel(models.AbstractModel):
    _name = 'report.ak_material_request.report_stock_transfer_request_xlsx'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Stock Transfer Request Report Xlsx'

    def generate_xlsx_report(self, workbook, data, wizard):
        
        header_merge_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
        title_header_merge_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 20, 'bg_color': '#D3D3D3', 'border': 1})
        header_data_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', \
                                                  'font_size': 10, 'border': 1})
        left = workbook.add_format({'align': 'left', 'valign': 'vcenter', \
                                                  'font_size': 10, 'border': 1})
        right = workbook.add_format({'align': 'right', 'font_size': 10, 'border': 1})
        product_header_format = workbook.add_format({'valign': 'vcenter', 'font_size': 11, 'border': 1, 'bold': True, })
        
        sheet = workbook.add_worksheet("Stock Transfer Request Report ")
        sheet.set_row(0, 25)
        
        
        sheet.merge_range(0, 0, 2, 18, "Stock Transfer Request Report" , title_header_merge_format)

        # sheet.merge_range(5, 0, 5, 1, 'Company', header_merge_format)
        
        # sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        # sheet.write(4, 2, 'Start Date', header_merge_format)
        # sheet.write(4, 3, 'End Date', header_merge_format)
        
        
        sheet.merge_range(5, 0, 5, 2, 'Company', header_merge_format)
        # sheet.write(5, 2, 'Warehouse', header_merge_format)
        sheet.write(5, 3, 'Start Date', header_merge_format)
        sheet.write(5, 4, 'End Date', header_merge_format)
        sheet.merge_range(6, 0, 6, 2, wizard.company_id.name, header_data_format)
        # sheet.write(6, 2, wizard.warehouse_ids.name, header_data_format)
        sheet.write(6, 3, wizard.start_date.strftime("%d-%m-%Y"), header_data_format)
        sheet.write(6, 4, wizard.end_date.strftime("%d-%m-%Y"), header_data_format)

        # if wizard.to_collapse == True:
        sheet.merge_range(0, 0, 2, 11, "Stock Transfer Request Report",
                          header_merge_format)
        # sheet.merge_range(0, 0, 2, 13, "Movement Report in " + wizard.location_id.name_get()[0][1],
        #                   header_merge_format)
        sheet.write(8, 0, 'S.No', header_merge_format)
        sheet.set_column(0, 0, 5)
        sheet.write(8, 1, 'Request Number', header_merge_format)
        sheet.set_column(1, 1, 18)
        sheet.write(8, 2, 'Request date', header_merge_format)
        sheet.set_column(2, 2, 18)
        # sheet.write(8, 3, 'Code', header_merge_format)
        # sheet.set_column(3, 3, 16)
        sheet.write(8, 3, 'Requesting Warehouse', header_merge_format)
        sheet.set_column(3, 3, 22)
        
        sheet.write(8, 4, 'Product Category', header_merge_format)
        sheet.set_column(4, 4, 22)
        sheet.write(8, 5, 'Product Description', header_merge_format)
        sheet.set_column(5, 5, 35)
        sheet.write(8, 6, 'UOM', header_merge_format)
        sheet.set_column(6, 6, 10)
        sheet.write(8, 7, 'Unit Price', header_merge_format)
        sheet.set_column(8, 8, 10)
        sheet.write(8, 8, 'Requested Qty', header_merge_format)
        sheet.set_column(9, 9, 10)
        sheet.write(8, 9, 'Transferred Qty', header_merge_format)
        sheet.set_column(10, 10, 10)
        sheet.write(8, 10, 'Balance Qty', header_merge_format)
        sheet.set_column(11, 11, 10)
        sheet.write(8, 11, 'Status', header_merge_format)
        sheet.set_column(12, 12, 10)

        row = 9
        no = 1

        #Ensure you have the necessary imports and variable definitions here

        if wizard.source_location_id  and wizard.category_ids and wizard.product_ids:
            categories = self.env['product.category'].sudo().search([('id','child_of',wizard.category_ids.id)])
            if categories:
                stock_location = self.env['stock.picking'].search([
                    ('location_id', '=', wizard.source_location_id.id),
                   
                    ('move_ids_without_package.product_id.categ_id', 'child_of', categories),
                    ('scheduled_date', '>=', wizard.start_date),
                    ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request']),
                ('location_id.usage','=','internal')

                ])
                balance_qty = 0.00
                previous_stock_name = ''
                for stock in stock_location:
                    if stock.location_id == wizard.source_location_id:
                        location_name = stock.location_id.display_name
                        location_dest_name = stock.location_dest_id.display_name
                        #sheet.merge_range(7, 0, 7, 12, location_name + ' - ' + location_dest_name, header_merge_format)
                        for line in stock.move_ids_without_package:
                            if line.product_id.categ_id in categories:
                                categories_name = line.product_id.categ_id.display_name
                                sheet.merge_range(7, 0, 7, 11, location_name +' - ' + location_dest_name + ' - ' + categories_name , header_merge_format)
                                if line.product_id in wizard.product_ids:
                                    if stock.name != previous_stock_name:
                                        # If the stock name has changed, write a header row
                                        previous_stock_name = stock.origin
                                        # sheet.write(row, 0, no, right)
                                        # sheet.write(row, 1, stock.name, left)
                                        # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
                                        # print("previous_stock_name", previous_stock_name)
                                        # row += 1
                                    name = stock.name
                                    # date = stock.scheduled_date.strftime("%Y-%m-%d")
                                    date = stock.scheduled_date.strftime("%d-%m-%Y")
                                    product = line.product_id.display_name
                                    product_uom = line.product_uom.display_name
                                    product_category = line.product_id.categ_id.display_name
                                    source_location = stock.location_id.display_name
                                    destination_location = stock.location_dest_id.display_name
                                    unit_price = line.product_id.standard_price
                                    requested_qty = line.product_uom_qty
                                    transferred_qty = line.quantity_done
                                    balance_qty = line.product_uom_qty - line.quantity_done
                                    state = stock.state
                                    sheet.write(row, 0, no, right)
                                    sheet.write(row, 1, previous_stock_name, left)
                                    sheet.write(row, 2, str(date), header_data_format)
                                    # sheet.write(row, 3, item['code'], left)
                                    sheet.write(row, 3, source_location, left)
                                    # sheet.write(row, 4, destination_location, left)
                                    sheet.write(row, 4, product_category, left)
                                    sheet.write(row, 5, product, left)
                                    sheet.write(row, 6, product_uom, left)
                                    sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
                                    sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
                                    sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
                                    sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
                                    sheet.write(row, 11, state, left)

                                    row += 1
                                    no += 1

        elif wizard.source_location_id and wizard.category_ids:
            categories = self.env['product.category'].sudo().search([('id','child_of',wizard.category_ids.id)])
            if categories:
                stock_location = self.env['stock.picking'].search([
                    ('location_id', '=', wizard.source_location_id.id),
                 
                    ('move_ids_without_package.product_id.categ_id', 'child_of', categories),
                    ('scheduled_date', '>=', wizard.start_date),
                    ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request']),
                    ('location_id.usage','=','internal')

                ])
                balance_qty = 0.00
                previous_stock_name = ''
                for stock in stock_location:
                    if stock.location_id == wizard.source_location_id:
                        location_name = stock.location_id.display_name
                        location_dest_name = stock.location_dest_id.display_name
                        #sheet.merge_range(7, 0, 7, 12, location_name + ' - ' + location_dest_name, header_merge_format)
                        for line in stock.move_ids_without_package:
                            if line.product_id.categ_id in categories:
                                categories_name = line.product_id.categ_id.display_name
                                sheet.merge_range(7, 0, 7, 11, location_name +' - ' + location_dest_name + ' - ' + categories_name , header_merge_format)
                                if stock.name != previous_stock_name:
                                    # If the stock name has changed, write a header row
                                    previous_stock_name = stock.origin
                                    # sheet.write(row, 0, no, right)
                                    # sheet.write(row, 1, stock.name, left)
                                    # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
                                    # print("previous_stock_name", previous_stock_name)
                                    # row += 1
                                name = stock.origin
                                date = stock.scheduled_date.strftime("%d-%m-%Y")
                                product = line.product_id.display_name
                                product_uom = line.product_uom.display_name
                                product_category = line.product_id.categ_id.display_name
                                source_location = stock.location_id.display_name
                                destination_location = stock.location_dest_id.display_name
                                unit_price = line.product_id.standard_price
                                requested_qty = line.product_uom_qty
                                transferred_qty = line.quantity_done
                                balance_qty = line.product_uom_qty - line.quantity_done
                                state = stock.state
                                sheet.write(row, 0, no, right)
                                sheet.write(row, 1, previous_stock_name, left)
                                sheet.write(row, 2, str(date), header_data_format)
                                # sheet.write(row, 3, item['code'], left)
                                sheet.write(row, 3, source_location, left)
                                # sheet.write(row, 4, destination_location, left)
                                sheet.write(row, 4, product_category, left)
                                sheet.write(row, 5, product, left)
                                sheet.write(row, 6, product_uom, left)
                                sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
                                sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
                                sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
                                sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
                                sheet.write(row, 11, state, left)

                                row += 1
                                no += 1

        # elif wizard.source_location_id :
        #     stock_location = self.env['stock.picking'].search([
        #         ('location_id', '=', wizard.source_location_id.id),
        #
        #         ('scheduled_date', '>=', wizard.start_date),
        #         ('scheduled_date', '<=', wizard.end_date),
        #         ('location_id.usage','=','internal'),
        #         ('internal_picking_type','in',['stock_request']),
        #
        #     ])
        #     balance_qty = 0.00
        #     for stock in stock_location:
        #         if stock.location_id == wizard.source_location_id:
        #             location_name = stock.location_id.display_name
        #             location_dest_name = stock.location_dest_id.display_name
        #             sheet.merge_range(7, 0, 7, 11, location_name + ' - ' + location_dest_name, header_merge_format)
        #             for line in stock.move_ids_without_package:
        #                 name = stock.origin
        #                 date = stock.scheduled_date.strftime("%d-%m-%Y")
        #                 product = line.product_id.display_name
        #                 product_uom = line.product_uom.display_name
        #                 product_category = line.product_id.categ_id.display_name
        #                 source_location = stock.location_id.display_name
        #                 destination_location = stock.location_dest_id.display_name
        #                 unit_price = line.product_id.standard_price
        #                 requested_qty = line.product_uom_qty
        #                 transferred_qty = line.quantity_done
        #                 balance_qty = line.product_uom_qty - line.quantity_done
        #                 state = stock.state
        #
        #                 sheet.write(row, 0, no, right)
        #                 sheet.write(row, 1, name, left)
        #                 sheet.write(row, 2, str(date), header_data_format)
        #                 sheet.write(row, 3, source_location, left)
        #                 # sheet.write(row, 4, destination_location, left)
        #                 sheet.write(row, 4, product_category, left)
        #                 sheet.write(row, 5, product, left)
        #                 sheet.write(row, 6, product_uom, left)
        #                 sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
        #                 sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
        #                 sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
        #                 sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
        #                 sheet.write(row, 11, state, left)
        #                 # sheet.write(row, 9, , left)
        #                 # sheet.write(row, 10, , left)
        #                 # '{:,.2f}'.format(pdt_total)
        #                 row += 1
        #                 no += 1
        elif wizard.source_location_id and wizard.category_ids and wizard.product_ids:
            categories = self.env['product.category'].sudo().search([('id','child_of',wizard.category_ids.id)])
            if categories:
                stock_location = self.env['stock.picking'].search([
                    ('location_id', '=', wizard.source_location_id.id),
                    ('move_ids_without_package.product_id.categ_id', 'child_of', categories),
                    ('scheduled_date', '>=', wizard.start_date),
                    ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request']),
                    ('location_id.usage','=','internal')

                ])
                balance_qty = 0.00
                previous_stock_name = ''
                for stock in stock_location:
                    if stock.location_id == wizard.source_location_id:
                        location_name = stock.location_id.display_name
                        # sheet.merge_range(7, 0, 7, 12, location_name, header_merge_format)
                        for line in stock.move_ids_without_package:
                            if line.product_id.categ_id in categories:
                                categories_name = line.product_id.categ_id.display_name
                                sheet.merge_range(7, 0, 7, 11, location_name + ' - ' + categories_name, header_merge_format)
                                if line.product_id in wizard.product_ids:
                                    if stock.name != previous_stock_name:
                                        # If the stock name has changed, write a header row
                                        previous_stock_name = stock.origin
                                        # sheet.write(row, 0, no, right)
                                        # sheet.write(row, 1, stock.name, left)
                                        # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
                                        # print("previous_stock_name", previous_stock_name)
                                        # row += 1
                                    name = stock.origin
                                    date = stock.scheduled_date.strftime("%d-%m-%Y")
                                    product = line.product_id.display_name
                                    product_uom = line.product_uom.display_name
                                    product_category = line.product_id.categ_id.display_name
                                    source_location = stock.location_id.display_name
                                    destination_location = stock.location_dest_id.display_name
                                    unit_price = line.product_id.standard_price
                                    requested_qty = line.product_uom_qty
                                    transferred_qty = line.quantity_done
                                    balance_qty = line.product_uom_qty - line.quantity_done
                                    state = stock.state
                                    sheet.write(row, 0, no, right)
                                    sheet.write(row, 1, previous_stock_name, left)
                                    sheet.write(row, 2, str(date), header_data_format)
                                    # sheet.write(row, 3, item['code'], left)
                                    sheet.write(row, 3, source_location, left)
                                    # sheet.write(row, 4, destination_location, left)
                                    sheet.write(row, 4, product_category, left)
                                    sheet.write(row, 5, product, left)
                                    sheet.write(row, 6, product_uom, left)
                                    sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
                                    sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
                                    sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
                                    sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
                                    sheet.write(row, 11, state, left)

                                    row += 1
                                    no += 1

        # elif  wizard.category_ids and wizard.product_ids:
        #     categories = self.env['product.category'].sudo().search([('id','child_of',wizard.category_ids.id)])
        #     if categories:
        #         stock_location = self.env['stock.picking'].search([
        #
        #             ('move_ids_without_package.product_id.categ_id', 'child_of', categories),
        #             ('scheduled_date', '>=', wizard.start_date),
        #             ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request'])
        #         ])
        #         balance_qty = 0.00
        #         previous_stock_name = ''
        #         for stock in stock_location:
        #             if stock.location_dest_id == wizard.destination_location_id:
        #                 location_dest_name = stock.location_dest_id.display_name
        #                 #sheet.merge_range(7, 0, 7, 12, location_name, header_merge_format)
        #                 for line in stock.move_ids_without_package:
        #                     if line.product_id.categ_id in categories:
        #                         categories_name = line.product_id.categ_id.display_name
        #                         sheet.merge_range(7, 0, 7, 12, location_dest_name + ' - ' + categories_name, header_merge_format)
        #                         if line.product_id in wizard.product_ids:
        #                             if stock.name != previous_stock_name:
        #                                 # If the stock name has changed, write a header row
        #                                 previous_stock_name = stock.name
        #                                 # sheet.write(row, 0, no, right)
        #                                 # sheet.write(row, 1, stock.name, left)
        #                                 # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
        #                                 # print("previous_stock_name", previous_stock_name)
        #                                 # row += 1
        #                             name = stock.name
        #                             date = stock.scheduled_date.strftime("%d-%m-%Y")
        #                             product = line.product_id.display_name
        #                             product_uom = line.product_uom.display_name
        #                             product_category = line.product_id.categ_id.display_name
        #                             source_location = stock.location_id.display_name
        #                             destination_location = stock.location_dest_id.display_name
        #                             unit_price = line.product_id.standard_price
        #                             requested_qty = line.product_uom_qty
        #                             transferred_qty = line.quantity_done
        #                             balance_qty = line.product_uom_qty - line.quantity_done
        #                             state = stock.state
        #                             sheet.write(row, 0, no, right)
        #                             sheet.write(row, 1, previous_stock_name, left)
        #                             sheet.write(row, 2, str(date), header_data_format)
        #                             # sheet.write(row, 3, item['code'], left)
        #                             sheet.write(row, 3, source_location, left)
        #                             sheet.write(row, 4, destination_location, left)
        #                             sheet.write(row, 5, product_category, left)
        #                             sheet.write(row, 6, product, left)
        #                             sheet.write(row, 7, product_uom, left)
        #                             sheet.write(row, 8, '{:,.2f}'.format(unit_price), right)
        #                             sheet.write(row, 9, '{:,.2f}'.format(requested_qty), right)
        #                             sheet.write(row, 10, '{:,.2f}'.format(transferred_qty), right)
        #                             sheet.write(row, 11, '{:,.2f}'.format(balance_qty), right)
        #                             sheet.write(row, 12, state, left)
        #
        #                             row += 1
        #                             no += 1

        elif wizard.source_location_id and wizard.category_ids:
            categories = self.env['product.category'].sudo().search([('id','child_of',wizard.category_ids.id)])
            if categories:
                stock_location = self.env['stock.picking'].search([
                    ('location_id', '=', wizard.source_location_id.id),
                    ('move_ids_without_package.product_id.categ_id', 'child_of', categories),
                    ('scheduled_date', '>=', wizard.start_date),
                    ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request']),
                                    ('location_id.usage','=','internal')

                ])
                balance_qty = 0.00
                previous_stock_name = ''
                for stock in stock_location:
                    if stock.location_id == wizard.source_location_id:
                        location_name = stock.location_id.display_name
                        # sheet.merge_range(7, 0, 7, 12, location_name, header_merge_format)
                        for line in stock.move_ids_without_package:
                            if line.product_id.categ_id in categories:
                                categories_name = line.product_id.categ_id.display_name
                                sheet.merge_range(7, 0, 7, 11, location_name + ' - ' + categories_name, header_merge_format)
                                # if line.product_id in wizard.product_ids:
                                if stock.name != previous_stock_name:
                                    # If the stock name has changed, write a header row
                                    previous_stock_name = stock.origin
                                    # sheet.write(row, 0, no, right)
                                    # sheet.write(row, 1, stock.name, left)
                                    # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
                                    # print("previous_stock_name", previous_stock_name)
                                    # row += 1
                                name = stock.origin
                                date = stock.scheduled_date.strftime("%d-%m-%Y")
                                product = line.product_id.display_name
                                product_uom = line.product_uom.display_name
                                product_category = line.product_id.categ_id.display_name
                                source_location = stock.location_id.display_name
                                destination_location = stock.location_dest_id.display_name
                                unit_price = line.product_id.standard_price
                                requested_qty = line.product_uom_qty
                                transferred_qty = line.quantity_done
                                balance_qty = line.product_uom_qty - line.quantity_done
                                state = stock.state
                                sheet.write(row, 0, no, right)
                                sheet.write(row, 1, previous_stock_name, left)
                                sheet.write(row, 2, str(date), header_data_format)
                                # sheet.write(row, 3, item['code'], left)
                                sheet.write(row, 3, source_location, left)
                                # sheet.write(row, 4, destination_location, left)
                                sheet.write(row, 4, product_category, left)
                                sheet.write(row, 5, product, left)
                                sheet.write(row, 6, product_uom, left)
                                sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
                                sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
                                sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
                                sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
                                sheet.write(row, 11, state, left)

                                row += 1
                                no += 1

        # elif wizard.destination_location_id and wizard.category_ids:
        #     categories = self.env['product.category'].sudo().search([('id','child_of',wizard.category_ids.id)])
        #     if categories:
        #         stock_location = self.env['stock.picking'].search([
        #             ('location_dest_id', '=', wizard.destination_location_id.id),
        #             ('move_ids_without_package.product_id.categ_id', 'child_of', categories),
        #             ('scheduled_date', '>=', wizard.start_date),
        #             ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request'])
        #         ])
        #         balance_qty = 0.00
        #         previous_stock_name = ''
        #         for stock in stock_location:
        #             if stock.location_dest_id == wizard.destination_location_id:
        #                 location_dest_name = stock.location_dest_id.display_name
        #                 #sheet.merge_range(7, 0, 7, 12, location_name, header_merge_format)
        #                 for line in stock.move_ids_without_package:
        #                     if line.product_id.categ_id in categories:
        #                         categories_name = line.product_id.categ_id.display_name
        #                         sheet.merge_range(7, 0, 7, 12, location_dest_name + ' - ' + categories_name, header_merge_format)
        #                         # if line.product_id in wizard.product_ids:
        #                         if stock.name != previous_stock_name:
        #                             # If the stock name has changed, write a header row
        #                             previous_stock_name = stock.name
        #                             # sheet.write(row, 0, no, right)
        #                             # sheet.write(row, 1, stock.name, left)
        #                             # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
        #                             # print("previous_stock_name", previous_stock_name)
        #                             # row += 1
        #                         name = stock.name
        #                         date = stock.scheduled_date.strftime("%d-%m-%Y")
        #                         product = line.product_id.display_name
        #                         product_uom = line.product_uom.display_name
        #                         product_category = line.product_id.categ_id.display_name
        #                         source_location = stock.location_id.display_name
        #                         destination_location = stock.location_dest_id.display_name
        #                         unit_price = line.product_id.standard_price
        #                         requested_qty = line.product_uom_qty
        #                         transferred_qty = line.quantity_done
        #                         balance_qty = line.product_uom_qty - line.quantity_done
        #                         state = stock.state
        #                         sheet.write(row, 0, no, right)
        #                         sheet.write(row, 1, previous_stock_name, left)
        #                         sheet.write(row, 2, str(date), header_data_format)
        #                         # sheet.write(row, 3, item['code'], left)
        #                         sheet.write(row, 3, source_location, left)
        #                         sheet.write(row, 4, destination_location, left)
        #                         sheet.write(row, 5, product_category, left)
        #                         sheet.write(row, 6, product, left)
        #                         sheet.write(row, 7, product_uom, left)
        #                         sheet.write(row, 8, '{:,.2f}'.format(unit_price), right)
        #                         sheet.write(row, 9, '{:,.2f}'.format(requested_qty), right)
        #                         sheet.write(row, 10, '{:,.2f}'.format(transferred_qty), right)
        #                         sheet.write(row, 11, '{:,.2f}'.format(balance_qty), right)
        #                         sheet.write(row, 12, state, left)
        #
        #                         row += 1
        #                         no += 1

        elif wizard.source_location_id and wizard.product_ids:
            stock_location = self.env['stock.picking'].search([
                ('location_id', '=', wizard.source_location_id.id),
                ('scheduled_date', '>=', wizard.start_date),
                ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request']),
                ('location_id.usage','=','internal')

            ])
            balance_qty = 0.00
            previous_stock_name = ''
            for stock in stock_location:
                if stock.location_id == wizard.source_location_id:
                    location_name = stock.location_id.display_name
                    # sheet.merge_range(7, 0, 7, 11, location_name, header_merge_format)
                    for line in stock.move_ids_without_package:
                        if line.product_id in wizard.product_ids:
                            if stock.name != previous_stock_name:
                                # If the stock name has changed, write a header row
                                previous_stock_name = stock.name
                                # sheet.write(row, 0, no, right)
                                # sheet.write(row, 1, stock.name, left)
                                # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
                                # print("previous_stock_name", previous_stock_name)
                                # row += 1
                            name = stock.origin
                            date = stock.scheduled_date.strftime("%d-%m-%Y")
                            product = line.product_id.display_name
                            product_uom = line.product_uom.display_name
                            product_category = line.product_id.categ_id.display_name
                            source_location = stock.location_id.display_name
                            destination_location = stock.location_dest_id.display_name
                            unit_price = line.product_id.standard_price
                            requested_qty = line.product_uom_qty
                            transferred_qty = line.quantity_done
                            balance_qty = line.product_uom_qty - line.quantity_done
                            state = stock.state

                            sheet.write(row, 0, no, right)
                            sheet.write(row, 1, name, left)
                            sheet.write(row, 2, str(date), header_data_format)
                            # sheet.write(row, 3, item['code'], left)
                            sheet.write(row, 3, source_location, left)
                            # sheet.write(row, 4, destination_location, left)
                            sheet.write(row, 4, product_category, left)
                            sheet.write(row, 5, product, left)
                            sheet.write(row, 6, product_uom, left)
                            sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
                            sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
                            sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
                            sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
                            sheet.write(row, 11, state, left)
                            row += 1
                            no += 1

        # elif wizard.destination_location_id and wizard.product_ids:
        #     stock_location = self.env['stock.picking'].search([
        #         ('location_dest_id', '=', wizard.destination_location_id.id),
        #         ('scheduled_date', '>=', wizard.start_date),
        #         ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request'])
        #     ])
        #     balance_qty = 0.00
        #     previous_stock_name = ''
        #     for stock in stock_location:
        #         if stock.location_dest_id == wizard.destination_location_id:
        #             location_dest_name = stock.location_dest_id.display_name
        #             sheet.merge_range(7, 0, 7, 12, location_dest_name, header_merge_format)
        #             for line in stock.move_ids_without_package:
        #                 if line.product_id in wizard.product_ids:
        #                     if stock.name != previous_stock_name:
        #                         # If the stock name has changed, write a header row
        #                         previous_stock_name = stock.name
        #                         # sheet.write(row, 0, no, right)
        #                         # sheet.write(row, 1, stock.name, left)
        #                         # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
        #                         # print("previous_stock_name", previous_stock_name)
        #                         # row += 1
        #                     name = stock.name
        #                     date = stock.scheduled_date.strftime("%d-%m-%Y")
        #                     product = line.product_id.display_name
        #                     product_uom = line.product_uom.display_name
        #                     product_category = line.product_id.categ_id.display_name
        #                     source_location = stock.location_id.display_name
        #                     destination_location = stock.location_dest_id.display_name
        #                     unit_price = line.product_id.standard_price
        #                     requested_qty = line.product_uom_qty
        #                     transferred_qty = line.quantity_done
        #                     balance_qty = line.product_uom_qty - line.quantity_done
        #                     state = stock.state
        #                     sheet.write(row, 0, no, right)
        #                     sheet.write(row, 1, name, left)
        #                     sheet.write(row, 2, str(date), header_data_format)
        #                     sheet.write(row, 3, source_location, left)
        #                     sheet.write(row, 4, destination_location, left)
        #                     sheet.write(row, 5, product_category, left)
        #                     sheet.write(row, 6, product, left)
        #                     sheet.write(row, 7, product_uom, left)
        #                     sheet.write(row, 8, '{:,.2f}'.format(unit_price), right)
        #                     sheet.write(row, 9, '{:,.2f}'.format(requested_qty), right)
        #                     sheet.write(row, 10, '{:,.2f}'.format(transferred_qty), right)
        #                     sheet.write(row, 11, '{:,.2f}'.format(balance_qty), right)
        #                     sheet.write(row, 12, state, left)
        #                     row += 1
        #                     no += 1


        elif wizard.source_location_id:
            stock_location = self.env['stock.picking'].search([
                ('location_id', '=', wizard.source_location_id.id),
                ('scheduled_date', '>=', wizard.start_date),
                ('scheduled_date', '<=', wizard.end_date),
                ('location_id.usage','=','internal')

            ])
            balance_qty = 0.00
            for stock in stock_location:
                if stock.location_id == wizard.source_location_id:
                    location_name = stock.location_id.display_name
                    sheet.merge_range(7, 0, 7, 11, location_name, header_merge_format)
                    for line in stock.move_ids_without_package:
                        name = stock.origin
                        date = stock.scheduled_date.strftime("%d-%m-%Y")
                        product = line.product_id.display_name
                        product_uom = line.product_uom.display_name
                        product_category = line.product_id.categ_id.display_name
                        source_location = stock.location_id.display_name
                        destination_location = stock.location_dest_id.display_name
                        unit_price = line.product_id.standard_price
                        requested_qty = line.product_uom_qty
                        transferred_qty = line.quantity_done
                        balance_qty = line.product_uom_qty - line.quantity_done
                        state = stock.state

                        sheet.write(row, 0, no, right)
                        sheet.write(row, 1, name, left)
                        sheet.write(row, 2, str(date), header_data_format)
                        sheet.write(row, 3, source_location, left)
                        # sheet.write(row, 4, destination_location, left)
                        sheet.write(row, 4, product_category, left)
                        sheet.write(row, 5, product, left)
                        sheet.write(row, 6, product_uom, left)
                        sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
                        sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
                        sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
                        sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
                        sheet.write(row, 11, state, left)
                        # sheet.write(row, 9, , left)
                        # sheet.write(row, 10, , left)
                        # '{:,.2f}'.format(pdt_total)
                        row += 1
                        no += 1


        # elif wizard.destination_location_id:
        #     stock_location = self.env['stock.picking'].search([
        #         ('location_dest_id', '=', wizard.destination_location_id.id),
        #         ('scheduled_date', '>=', wizard.start_date),
        #         ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request'])
        #     ])
        #     balance_qty = 0.00
        #     for stock in stock_location:
        #         if stock.location_dest_id == wizard.destination_location_id:
        #             location_dest_name = stock.location_dest_id.display_name
        #             sheet.merge_range(7, 0, 7, 12, location_dest_name, header_merge_format)
        #             for line in stock.move_ids_without_package:
        #                 name = stock.name
        #                 date = stock.scheduled_date.strftime("%d-%m-%Y")
        #                 # code = line.product_id.default_code
        #                 product = line.product_id.display_name
        #                 product_uom = line.product_uom.display_name
        #                 product_category = line.product_id.categ_id.display_name
        #                 source_location = stock.location_id.display_name
        #                 destination_location = stock.location_dest_id.display_name
        #                 unit_price = line.product_id.standard_price
        #                 requested_qty = line.product_uom_qty
        #                 transferred_qty = line.quantity_done
        #                 balance_qty = line.product_uom_qty - line.quantity_done
        #                 state = stock.state
        #
        #                 sheet.write(row, 0, no, right)
        #                 sheet.write(row, 1, name, left)
        #                 sheet.write(row, 2, str(date), header_data_format)
        #                 # sheet.write(row, 3, item['code'], left)
        #                 sheet.write(row, 3, source_location, left)
        #                 sheet.write(row, 4, destination_location, left)
        #                 sheet.write(row, 5, product_category, left)
        #                 sheet.write(row, 6, product, left)
        #                 sheet.write(row, 7, product_uom, left)
        #                 sheet.write(row, 8, '{:,.2f}'.format(unit_price), right)
        #                 sheet.write(row, 9, '{:,.2f}'.format(requested_qty), right)
        #                 sheet.write(row, 10, '{:,.2f}'.format(transferred_qty), right)
        #                 sheet.write(row, 11, '{:,.2f}'.format(balance_qty), right)
        #                 sheet.write(row, 12, state, left)
        #                 # sheet.write(row, 9, , left)
        #                 # sheet.write(row, 10, , left)
        #                 # '{:,.2f}'.format(pdt_total)
        #                 row += 1
        #                 no += 1


        # elif wizard.category_ids and wizard.product_ids:
        #     categories = self.env['product.category'].sudo().search([('id','child_of',wizard.category_ids.id)])
        #     if categories:
        #         stock_location = self.env['stock.picking'].search([
        #             ('move_ids_without_package.product_id.categ_id', 'child_of', categories),
        #             ('scheduled_date', '>=', wizard.start_date),
        #             ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request'])
        #         ])
        #         balance_qty = 0.00
        #         previous_stock_name = ''
        #         if stock_location:
        #             for stock in stock_location:
        #                 for line in stock.move_ids_without_package:
        #                     if line.product_id.categ_id in categories:
        #                         categories_name = line.product_id.categ_id.display_name
        #                         sheet.merge_range(7, 0, 7, 12, categories_name, header_merge_format)
        #                         if line.product_id in wizard.product_ids:
        #                             if stock.name != previous_stock_name:
        #                                 # If the stock name has changed, write a header row
        #                                 previous_stock_name = stock.name
        #                                 # sheet.write(row, 0, no, right)
        #                                 # sheet.write(row, 1, stock.name, left)
        #                                 # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
        #                                 # print("previous_stock_name", previous_stock_name)
        #                                 # row += 1
        #                             name = stock.name
        #                             date = stock.scheduled_date.strftime("%d-%m-%Y")
        #                             product = line.product_id.display_name
        #                             product_uom = line.product_uom.display_name
        #                             product_category = line.product_id.categ_id.display_name
        #                             source_location = stock.location_id.display_name
        #                             destination_location = stock.location_dest_id.display_name
        #                             unit_price = line.product_id.standard_price
        #                             requested_qty = line.product_uom_qty
        #                             transferred_qty = line.quantity_done
        #                             balance_qty = line.product_uom_qty - line.quantity_done
        #                             state = stock.state
        #                             sheet.write(row, 0, no, right)
        #                             sheet.write(row, 1, previous_stock_name, left)
        #                             sheet.write(row, 2, str(date), header_data_format)
        #                             # sheet.write(row, 3, item['code'], left)
        #                             sheet.write(row, 3, source_location, left)
        #                             sheet.write(row, 4, destination_location, left)
        #                             sheet.write(row, 5, product_category, left)
        #                             sheet.write(row, 6, product, left)
        #                             sheet.write(row, 7, product_uom, left)
        #                             sheet.write(row, 8, '{:,.2f}'.format(unit_price), right)
        #                             sheet.write(row, 9, '{:,.2f}'.format(requested_qty), right)
        #                             sheet.write(row, 10, '{:,.2f}'.format(transferred_qty), right)
        #                             sheet.write(row, 11, '{:,.2f}'.format(balance_qty), right)
        #                             sheet.write(row, 12, state, left)
        #
        #                             row += 1
        #                             no += 1

        elif wizard.category_ids:
            categories = self.env['product.category'].sudo().search([('id','child_of',wizard.category_ids.id)])
            if categories:
                stock_location = self.env['stock.picking'].search([
                    ('move_ids_without_package.product_id.categ_id', 'child_of', categories),
                    ('scheduled_date', '>=', wizard.start_date),
                    ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request']),
                    ('location_id.usage','=','internal')

                ])
                balance_qty = 0.00
                previous_stock_name = ''
                if stock_location:
                    for stock in stock_location:
                        for line in stock.move_ids_without_package:
                            if line.product_id.categ_id in categories:
                                categories_name = line.product_id.categ_id.display_name
                                sheet.merge_range(7, 0, 7, 11, categories_name, header_merge_format)
                                if stock.name != previous_stock_name:
                                    # If the stock name has changed, write a header row
                                    previous_stock_name = stock.origin
                                    # sheet.write(row, 0, no, right)
                                    # sheet.write(row, 1, stock.name, left)
                                    # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
                                    # print("previous_stock_name", previous_stock_name)
                                    # row += 1
                                name = stock.name
                                date = stock.scheduled_date.strftime("%d-%m-%Y")
                                product = line.product_id.display_name
                                product_uom = line.product_uom.display_name
                                product_category = line.product_id.categ_id.display_name
                                source_location = stock.location_id.display_name
                                destination_location = stock.location_dest_id.display_name
                                unit_price = line.product_id.standard_price
                                requested_qty = line.product_uom_qty
                                transferred_qty = line.quantity_done
                                balance_qty = line.product_uom_qty - line.quantity_done
                                state = stock.state
                                sheet.write(row, 0, no, right)
                                sheet.write(row, 1, previous_stock_name, left)
                                sheet.write(row, 2, str(date), header_data_format)
                                # sheet.write(row, 3, item['code'], left)
                                sheet.write(row, 3, source_location, left)
                                # sheet.write(row, 4, destination_location, left)
                                sheet.write(row, 4, product_category, left)
                                sheet.write(row, 5, product, left)
                                sheet.write(row, 6, product_uom, left)
                                sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
                                sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
                                sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
                                sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
                                sheet.write(row, 11, state, left)

                                row += 1
                                no += 1

        elif wizard.product_ids:
            stock_location = self.env['stock.picking'].search([
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request']),
                ('location_id.usage','=','internal')
            ])

            sub_total = 0.00
            adjusted_qty = 0.00
            previous_stock_name = ''
            for stock in stock_location:
                for line in stock.move_ids_without_package:
                    if line.product_id in wizard.product_ids:
                        if stock.name != previous_stock_name:
                            # If the stock name has changed, write a header row
                            previous_stock_name = stock.name
                            # sheet.write(row, 0, no, right)
                            # sheet.write(row, 1, stock.name, left)
                            # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
                            # print("previous_stock_name", previous_stock_name)
                            # row += 1
                        name = stock.origin
                        date = stock.scheduled_date.strftime("%d-%m-%Y")
                        product = line.product_id.display_name
                        product_uom = line.product_uom.display_name
                        product_category = line.product_id.categ_id.display_name
                        source_location = stock.location_id.display_name
                        destination_location = stock.location_dest_id.display_name
                        unit_price = line.product_id.standard_price
                        requested_qty = line.product_uom_qty
                        transferred_qty = line.quantity_done
                        balance_qty = line.product_uom_qty - line.quantity_done
                        state = stock.state

                        sheet.write(row, 0, no, right)
                        sheet.write(row, 1, name, left)
                        sheet.write(row, 2, str(date), header_data_format)
                        sheet.write(row, 3, source_location, left)
                        # sheet.write(row, 4, destination_location, left)
                        sheet.write(row, 4, product_category, left)
                        sheet.write(row, 5, product, left)
                        sheet.write(row, 6, product_uom, left)
                        sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
                        sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
                        sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
                        sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
                        sheet.write(row, 11, state, left)

                        row += 1
                        no += 1


        elif wizard.start_date and wizard.end_date:
            # Fetch stock adjustments based on the selected date range
            stock_transfer = self.env['stock.picking'].search([
                ('scheduled_date', '>=', wizard.start_date),
                ('scheduled_date', '<=', wizard.end_date),('internal_picking_type','in',['stock_request']),
                ('location_id.usage','=','internal')
            ])
            balance_qty = 0.00
            for stock in stock_transfer:
                for line in stock.move_ids_without_package:
                    name = stock.origin
                    date = stock.scheduled_date.strftime("%d-%m-%Y")
                    # code = line.product_id.default_code
                    product = line.product_id.display_name
                    product_uom = line.product_uom.display_name
                    product_category = line.product_id.categ_id.display_name
                    source_location = stock.location_id.display_name
                    destination_location = stock.location_dest_id.display_name
                    unit_price = line.product_id.standard_price
                    requested_qty = line.product_uom_qty
                    transferred_qty = line.quantity_done
                    balance_qty = line.product_uom_qty - line.quantity_done
                    state = stock.state

                    sheet.write(row, 0, no, right)
                    sheet.write(row, 1, name, left)
                    sheet.write(row, 2, str(date), header_data_format)
                    sheet.write(row, 3, source_location, left)
                    # sheet.write(row, 4, destination_location, left)
                    sheet.write(row, 4, product_category , left)
                    sheet.write(row, 5, product, left)
                    sheet.write(row, 6, product_uom, left)
                    sheet.write(row, 7, '{:,.2f}'.format(unit_price), right)
                    sheet.write(row, 8, '{:,.2f}'.format(requested_qty), right)
                    sheet.write(row, 9, '{:,.2f}'.format(transferred_qty), right)
                    sheet.write(row, 10, '{:,.2f}'.format(balance_qty), right)
                    sheet.write(row, 11, state, left)

                    row += 1
                    no += 1

