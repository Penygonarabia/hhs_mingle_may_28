from odoo import fields, models, api, _
import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class StockAdjustmentReportExcel(models.AbstractModel):
    _name = 'report.sync_inventory_adjustment.report_stock_adjustment_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Stock Adjustment Report Xlsx'

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
        sheet = workbook.add_worksheet("Inventory Adjustment Report")
        sheet.set_row(0, 25)
        #
        sheet.merge_range(5, 0, 5, 2, 'Company', header_merge_format)
        # sheet.write(5, 2, 'Warehouse', header_merge_format)
        sheet.write(5, 3, 'Start Date', header_merge_format)
        sheet.write(5, 4, 'End Date', header_merge_format)
        sheet.merge_range(6, 0, 6, 2, wizard.company_id.name, header_data_format)
        # sheet.write(6, 2, wizard.warehouse_ids.name, header_data_format)
        sheet.write(6, 3, str(wizard.start_date), header_data_format)
        sheet.write(6, 4, str(wizard.end_date), header_data_format)

        # if wizard.to_collapse == True:
        sheet.merge_range(0, 0, 2, 10, "Stock Adjustment Report",
                          title_header_merge_format)
        # sheet.merge_range(0, 0, 2, 13, "Movement Report in " + wizard.location_id.name_get()[0][1],
        #                   header_merge_format)
        sheet.write(8, 0, 'S.No', header_merge_format)
        sheet.set_column(0, 0, 5)
        sheet.write(8, 1, 'Reference', header_merge_format)
        sheet.set_column(1, 1, 27)
        sheet.write(8, 2, 'Adjustment Date', header_merge_format)
        sheet.set_column(2, 2, 18)
        # sheet.write(8, 3, 'Code', header_merge_format)
        # sheet.set_column(3, 3, 16)
        sheet.write(8, 3, 'Product', header_merge_format)
        sheet.set_column(3, 3, 40)
        sheet.write(8, 4, 'Computer Qty', header_merge_format)
        sheet.set_column(4, 4, 15)
        sheet.write(8, 5, 'Counted Qty', header_merge_format)
        sheet.set_column(5, 5, 15)
        sheet.write(8, 6, 'Adjusted Qty', header_merge_format)
        sheet.set_column(6, 6, 15)
        sheet.write(8, 7, 'Unit Cost', header_merge_format)
        sheet.set_column(7, 7, 15)
        sheet.write(8, 8, 'Subtotal', header_merge_format)
        sheet.set_column(8, 8, 15)
        # sheet.write(8, 10, 'Site', header_merge_format)
        # sheet.set_column(10, 10, 15)
        # sheet.write(8, 11, 'Reason', header_merge_format)
        # sheet.set_column(11, 11, 30)
        sheet.write(8, 9, 'Comments', header_merge_format)
        sheet.set_column(9, 9, 30)
        sheet.write(8, 10, 'Created By', header_merge_format)
        sheet.set_column(10, 10, 18)

        row = 9
        no = 1

        if wizard.location_id and wizard.category_id and wizard.product_ids:
            # Find the selected category and its child categories
            selected_category = self.env['product.category'].browse(wizard.category_id.id)
            category_ids = selected_category.search([('id', 'child_of', selected_category.id)]).ids

            stock_location = self.env['stock.inventory'].search([
                ('location_id', '=', wizard.location_id.id),
                ('category_id', 'in', category_ids),  # Use 'in' to search for child categories
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date)
            ])

            sub_total = 0.00
            adjusted_qty = 0.00
            parent_categories = {}
            # row = 8  # Initialize the row variable

            for stock in stock_location:
                location_name = stock.location_id.display_name
                parent_category = stock.category_id.parent_id or stock.category_id
                category_name = parent_category.display_name  # Moved category_name assignment here

                if parent_category not in parent_categories:
                    # Create a new header row for the parent category
                    parent_categories[parent_category] = row
                    sheet.merge_range(7, 0, 7, 10, location_name + ' - ' + category_name, header_merge_format)

                    # row += 1  # Increment row for the category header

                for line in stock.line_ids:
                    if line.product_id in wizard.product_ids:
                        name = stock.name
                        date = stock.date.strftime("%Y-%m-%d")
                        code = line.product_id.default_code
                        product = line.product_id.display_name
                        theoretical_qty = line.theoretical_qty
                        remarks = stock.remarks
                        product_qty = line.product_qty
                        adjusted_qty = line.product_qty - line.theoretical_qty
                        cost = line.product_id.standard_price
                        sub_total = adjusted_qty * cost
                        created_by = stock.create_uid.name
                        sheet.write(row, 0, no, right)
                        sheet.write(row, 1, name, left)
                        sheet.write(row, 2, str(date), header_data_format)
                        sheet.write(row, 3, product, left)
                        sheet.write(row, 4, '{:,.2f}'.format(theoretical_qty), right)
                        sheet.write(row, 5, '{:,.2f}'.format(product_qty), right)
                        sheet.write(row, 6, '{:,.2f}'.format(adjusted_qty), right)
                        sheet.write(row, 7, '{:,.2f}'.format(cost), right)
                        sheet.write(row, 8, '{:,.2f}'.format(sub_total), right)
                        sheet.write(row, 9, remarks, left)
                        sheet.write(row, 10, created_by, left)
                        row += 1
                        no += 1


        elif wizard.location_id and wizard.category_id:
            # Find the selected category and its child categories
            selected_category = self.env['product.category'].browse(wizard.category_id.id)
            category_ids = selected_category.search([('id', 'child_of', selected_category.id)]).ids

            stock_location = self.env['stock.inventory'].search([
                ('location_id', '=', wizard.location_id.id),
                ('category_id', 'in', category_ids),  # Use 'in' to search for child categories
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date)
            ])

            sub_total = 0.00
            adjusted_qty = 0.00
            parent_categories = {}
            # row = 8  # Initialize the row variable

            for stock in stock_location:
                location_name = stock.location_id.display_name
                parent_category = stock.category_id.parent_id or stock.category_id
                category_name = parent_category.display_name  # Moved category_name assignment here

                if parent_category not in parent_categories:
                    # Create a new header row for the parent category
                    parent_categories[parent_category] = row
                    sheet.merge_range(7, 0, 7, 10, location_name + ' - ' + category_name, header_merge_format)

                    # row += 1  # Increment row for the category header

                for line in stock.line_ids:
                    name = stock.name
                    date = stock.date.strftime("%Y-%m-%d")
                    code = line.product_id.default_code
                    product = line.product_id.display_name
                    theoretical_qty = line.theoretical_qty
                    remarks = stock.remarks
                    product_qty = line.product_qty
                    adjusted_qty = line.product_qty - line.theoretical_qty
                    cost = line.product_id.standard_price
                    sub_total = adjusted_qty * cost
                    created_by = stock.create_uid.name
                    sheet.write(row, 0, no, right)
                    sheet.write(row, 1, name, left)
                    sheet.write(row, 2, str(date), header_data_format)
                    sheet.write(row, 3, product, left)
                    sheet.write(row, 4, '{:,.2f}'.format(theoretical_qty), right)
                    sheet.write(row, 5, '{:,.2f}'.format(product_qty), right)
                    sheet.write(row, 6, '{:,.2f}'.format(adjusted_qty), right)
                    sheet.write(row, 7, '{:,.2f}'.format(cost), right)
                    sheet.write(row, 8, '{:,.2f}'.format(sub_total), right)
                    sheet.write(row, 9, remarks, left)
                    sheet.write(row, 10, created_by, left)
                    row += 1
                    no += 1


        elif wizard.location_id and wizard.product_ids:
            stock_location = self.env['stock.inventory'].search([
                ('location_id', '=', wizard.location_id.id),
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date)
            ])
            sub_total = 0.00
            adjusted_qty = 0.00
            previous_stock_name = ''
            for stock in stock_location:
                if stock.location_id == wizard.location_id:
                    location_name = stock.location_id.display_name
                    sheet.merge_range(7, 0, 7, 10, location_name, header_merge_format)
                    for line in stock.line_ids:
                        if line.product_id in wizard.product_ids:
                            if stock.name != previous_stock_name:
                                previous_stock_name = stock.name
                                name = stock.name
                                date = stock.date.strftime("%Y-%m-%d")
                                code = line.product_id.default_code
                                product = line.product_id.display_name
                                theoretical_qty = line.theoretical_qty
                                remarks = stock.remarks
                                product_qty = line.product_qty
                                adjusted_qty = line.product_qty - line.theoretical_qty
                                cost = line.product_id.standard_price
                                sub_total = adjusted_qty * cost
                                created_by = stock.create_uid.name

                                # Write data to the sheet

                                sheet.write(row, 0, no, right)
                                sheet.write(row, 1, name, left)
                                sheet.write(row, 2, str(date), header_data_format)
                                sheet.write(row, 3, product, left)
                                sheet.write(row, 4, '{:,.2f}'.format(theoretical_qty), right)
                                sheet.write(row, 5, '{:,.2f}'.format(product_qty), right)
                                sheet.write(row, 6, '{:,.2f}'.format(adjusted_qty), right)
                                sheet.write(row, 7, '{:,.2f}'.format(cost), right)
                                sheet.write(row, 8, '{:,.2f}'.format(sub_total), right)
                                sheet.write(row, 9, remarks, left)
                                sheet.write(row, 10, created_by, left)

                                row += 1
                                no += 1


        # Ensure you have the necessary imports and variable definitions here



        elif wizard.location_id:
            stock_location = self.env['stock.inventory'].search([
                ('location_id', '=', wizard.location_id.id),
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date)
            ])
            sub_total = 0.00
            adjusted_qty = 0.00
            for stock in stock_location:

                if stock.location_id == wizard.location_id:
                    location_name = stock.location_id.display_name
                    sheet.merge_range(7, 0, 7, 10, location_name, header_merge_format)

                    for line in stock.line_ids:
                        name = stock.name
                        date = stock.date.strftime("%Y-%m-%d")
                        code = line.product_id.default_code
                        product = line.product_id.display_name
                        theoretical_qty = line.theoretical_qty
                        remarks = stock.remarks
                        product_qty = line.product_qty
                        adjusted_qty = line.product_qty - line.theoretical_qty
                        cost = line.product_id.standard_price
                        sub_total = adjusted_qty * cost
                        created_by = stock.create_uid.name
                        sheet.write(row, 0, no, right)
                        sheet.write(row, 1, name, left)
                        sheet.write(row, 2, str(date), header_data_format)
                        # sheet.write(row, 3, code, left)
                        sheet.write(row, 3, product, left)
                        sheet.write(row, 4, '{:,.2f}'.format(theoretical_qty), right)
                        sheet.write(row, 5, '{:,.2f}'.format(product_qty), right)
                        sheet.write(row, 6, '{:,.2f}'.format(adjusted_qty), right)
                        sheet.write(row, 7, '{:,.2f}'.format(cost), right)
                        sheet.write(row, 8, '{:,.2f}'.format(sub_total), right)
                        sheet.write(row, 9, remarks, left)
                        sheet.write(row, 10, created_by, left)

                        row += 1
                        no += 1



        elif wizard.category_id and wizard.product_ids:
            stock_location = self.env['stock.inventory'].search([
                ('category_id', 'child_of', wizard.category_id.id),
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date)
            ])

            sub_total = 0.00
            adjusted_qty = 0.00
            no = 1  # Initialize the entry number
            row = 9  # Initialize the row where data will be written in the Excel sheet
            parent_categories = {}  # To track parent categories and their child data

            for stock in stock_location:
                parent_category = stock.category_id.parent_id or stock.category_id
                if parent_category not in parent_categories:
                    # Create a new header row for the parent category
                    category_name = parent_category.display_name
                    # sheet.write(row, 0, "Category", header_merge_format)
                    sheet.merge_range(7, 0, 7, 10, category_name, header_merge_format)
                    parent_categories[parent_category] = row
                    # row += 0

                row_for_category = parent_categories[parent_category]

                for line in stock.line_ids:
                    if line.product_id in wizard.product_ids:
                        name = stock.name
                        date = stock.date.strftime("%Y-%m-%d")
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

                        # sheet.write(row_for_category, 0, "Category", header_data_format)
                        # sheet.write(row_for_category, 1, category_name, header_data_format)
                        sheet.write(row, 0, no, right)
                        sheet.write(row, 1, name, left)
                        sheet.write(row, 2, str(date), header_data_format)
                        # sheet.write(row, 3, code, left)
                        sheet.write(row, 3, product, left)
                        sheet.write(row, 4, '{:,.2f}'.format(theoretical_qty), right)
                        sheet.write(row, 5, '{:,.2f}'.format(product_qty), right)
                        sheet.write(row, 6, '{:,.2f}'.format(adjusted_qty), right)
                        sheet.write(row, 7, '{:,.2f}'.format(cost), right)
                        sheet.write(row, 8, '{:,.2f}'.format(sub_total), right)
                        sheet.write(row, 9, remarks, left)
                        sheet.write(row, 10, created_by, left)

                        row += 1
                        no += 1

        elif wizard.category_id:
            stock_location = self.env['stock.inventory'].search([
                ('category_id', 'child_of', wizard.category_id.id),
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date)
            ])

            sub_total = 0.00
            adjusted_qty = 0.00
            no = 1  # Initialize the entry number
            row = 9  # Initialize the row where data will be written in the Excel sheet
            parent_categories = {}  # To track parent categories and their child data

            for stock in stock_location:
                parent_category = stock.category_id.parent_id or stock.category_id
                if parent_category not in parent_categories:
                    # Create a new header row for the parent category
                    category_name = parent_category.display_name
                    # sheet.write(row, 0, "Category", header_merge_format)
                    sheet.merge_range(7, 0, 7, 10, category_name, header_merge_format)
                    parent_categories[parent_category] = row
                    # row += 0

                row_for_category = parent_categories[parent_category]

                for line in stock.line_ids:
                    name = stock.name
                    date = stock.date.strftime("%Y-%m-%d")
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

                    # sheet.write(row_for_category, 0, "Category", header_data_format)
                    # sheet.write(row_for_category, 1, category_name, header_data_format)
                    sheet.write(row, 0, no, right)
                    sheet.write(row, 1, name, left)
                    sheet.write(row, 2, str(date), header_data_format)
                    # sheet.write(row, 3, code, left)
                    sheet.write(row, 3, product, left)
                    sheet.write(row, 4, '{:,.2f}'.format(theoretical_qty), right)
                    sheet.write(row, 5, '{:,.2f}'.format(product_qty), right)
                    sheet.write(row, 6, '{:,.2f}'.format(adjusted_qty), right)
                    sheet.write(row, 7, '{:,.2f}'.format(cost), right)
                    sheet.write(row, 8, '{:,.2f}'.format(sub_total), right)
                    sheet.write(row, 9, remarks, left)
                    sheet.write(row, 10, created_by, left)

                    row += 1
                    no += 1


        elif wizard.product_ids:
            stock_location = self.env['stock.inventory'].search([
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date)
            ])

            sub_total = 0.00
            adjusted_qty = 0.00
            previous_stock_name = ''
            for stock in stock_location:
                for line in stock.line_ids:
                    if line.product_id in wizard.product_ids:
                        if stock.name != previous_stock_name:
                            # If the stock name has changed, write a header row
                            previous_stock_name = stock.name
                            # sheet.write(row, 0, no, right)
                            # sheet.write(row, 1, stock.name, left)
                            # sheet.merge_range(7, 0, 7, 10, stock.name, header_data_format)
                            # print("previous_stock_name", previous_stock_name)
                            # row += 1
                        name = stock.name
                        date = stock.date.strftime("%Y-%m-%d")
                        code = line.product_id.default_code
                        product = line.product_id.display_name
                        theoretical_qty = line.theoretical_qty
                        remarks = stock.remarks
                        product_qty = line.product_qty
                        adjusted_qty = line.product_qty - line.theoretical_qty
                        cost = line.product_id.standard_price
                        sub_total = adjusted_qty * cost
                        created_by = stock.create_uid.name
                        sheet.write(row, 0, no, right)
                        # if stock.name != previous_stock_name:
                        sheet.write(row, 1, name, left)
                        sheet.write(row, 2, str(date), header_data_format)
                        # sheet.write(row, 3, code, left)
                        sheet.write(row, 3, product, left)
                        sheet.write(row, 4, '{:,.2f}'.format(theoretical_qty), right)
                        sheet.write(row, 5, '{:,.2f}'.format(product_qty), right)
                        sheet.write(row, 6, '{:,.2f}'.format(adjusted_qty), right)
                        sheet.write(row, 7, '{:,.2f}'.format(cost), right)
                        sheet.write(row, 8, '{:,.2f}'.format(sub_total), right)
                        sheet.write(row, 9, remarks, left)
                        sheet.write(row, 10, created_by, left)

                        row += 1
                        no += 1


        elif wizard.start_date and wizard.end_date:
        # stock_adjustment = self.env['stock.inventory'].search(
        #     [('product_id', '=', wizard.product_ids.ids), ('location_id', '=', wizard.location_id.id),
        #      ('company_id', '=', wizard.company_id.id)], order="product_id ASC")
        # stock_adjustment = self.env['stock.inventory'].search(
        #     [('location_id', '=', wizard.location_id.id),
        #      ('company_id', '=', wizard.company_id.id),('date', '>=', wizard.start_date),('date', '<=', wizard.end_date)])

            # Fetch stock adjustments based on the selected date range
            stock_adjustment = self.env['stock.inventory'].search([
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date)
            ])

            # Create a dictionary to store data grouped by location_id
            location_data = {}
            sub_total = 0.00
            adjusted_qty = 0.00
            # Loop through the stock adjustments and group them by location_id
            for stock in stock_adjustment:
                location_name = stock.location_id.display_name

                if location_name not in location_data:
                    location_data[location_name] = []

                for line in stock.line_ids:
                    name = stock.name
                    date = stock.date.strftime("%Y-%m-%d")
                    code = line.product_id.default_code
                    product = line.product_id.display_name
                    theoretical_qty = line.theoretical_qty
                    remarks = stock.remarks
                    print("remarks",remarks)
                    product_qty = line.product_qty
                    adjusted_qty = line.product_qty - line.theoretical_qty
                    cost = line.product_id.standard_price
                    sub_total = adjusted_qty * cost
                    created_by = stock.create_uid.name

                    # Append data to the location group
                    location_data[location_name].append({
                        'name': name,
                        'date': date,
                        'code': code,
                        'product': product,
                        'theoretical_qty': theoretical_qty,
                        'remarks': remarks,
                        'product_qty': product_qty,
                        'adjusted_qty': adjusted_qty,
                        'cost': cost,
                        'sub_total': sub_total,
                        'created_by': created_by
                    })

            # Loop through the grouped data and write it to the Excel sheet
            row = 9
            no = 1

            for location_name, location_items in location_data.items():
                # Write the location name as a header
                sheet.merge_range(row, 0, row, 10, location_name, header_merge_format)
                row += 1
                no = 1

                for item in location_items:
                    sheet.write(row, 0, no, right)
                    sheet.write(row, 1, item['name'], left)
                    sheet.write(row, 2, str(item['date']), header_data_format)
                    # sheet.write(row, 3, item['code'], left)
                    sheet.write(row, 3, item['product'], left)
                    sheet.write(row, 4, '{:,.2f}'.format(item['theoretical_qty']), right)
                    sheet.write(row, 5, '{:,.2f}'.format(item['product_qty']), right)
                    sheet.write(row, 6, '{:,.2f}'.format(item['adjusted_qty']), right)
                    sheet.write(row, 7, '{:,.2f}'.format(item['cost']), right)
                    sheet.write(row, 8, '{:,.2f}'.format(item['sub_total']), right)
                    sheet.write(row, 9, item['remarks'], left)
                    sheet.write(row, 10, item['created_by'], left)
                    # '{:,.2f}'.format(pdt_total)
                    row += 1
                    no += 1

    ######### Working code ########

        # if wizard.product_ids:
        #     product_sums = {}
        #
        #     for product in wizard.product_ids:
        #         product_sums[product.id] = {
        #             'theoretical_qty': 0.0,
        #             'product_qty': 0.0,
        #             'adjusted_qty': 0.0,
        #             'sub_total': 0.0
        #         }
        #
        #     for stock in self.env['stock.inventory'].search([
        #         ('date', '>=', wizard.start_date),
        #         ('date', '<=', wizard.end_date)
        #     ]):
        #         for line in stock.line_ids:
        #             if line.product_id in wizard.product_ids:
        #                 product_id = line.product_id.id
        #
        #                 product_sums[product_id]['theoretical_qty'] += line.theoretical_qty
        #                 product_sums[product_id]['product_qty'] += line.product_qty
        #                 product_sums[product_id]['adjusted_qty'] += line.product_qty - line.theoretical_qty
        #                 product_sums[product_id]['sub_total'] += (line.product_qty - line.theoretical_qty) * line.product_id.standard_price
        #
        #     for product in wizard.product_ids:
        #         product_id = product.id
        #         theoretical_qty = product_sums[product_id]['theoretical_qty']
        #         product_qty = product_sums[product_id]['product_qty']
        #         adjusted_qty = product_sums[product_id]['adjusted_qty']
        #         sub_total = product_sums[product_id]['sub_total']
        #
        #         # Display the calculated sums for each product as needed in your sheet or report.
        #         # Modify the code below to write the sums to your report.
        #         sheet.write(row, 0, no, right)
        #         sheet.write(row, 1, product.display_name, left)
        #         sheet.write(row, 2, str(wizard.start_date) + ' - ' + str(wizard.end_date), header_data_format)
        #         sheet.write(row, 3, theoretical_qty, right)
        #         sheet.write(row, 4, product_qty, right)
        #         sheet.write(row, 5, adjusted_qty, right)
        #         sheet.write(row, 6, sub_total, right)
        #         row += 1
        #         no += 1

        ############# Working code by category_id>>>>>>>>>>>>>>>
        # elif wizard.category_id:
        #     # if record.category_ids:
        #     #     domain.append(('categ_id', 'child_of', record.category_ids.ids))
        #     stock_location = self.env['stock.inventory'].search([
        #         ('category_id', 'child_of', wizard.category_id.id),
        #         ('date', '>=', wizard.start_date),
        #         ('date', '<=', wizard.end_date)
        #     ])
        #     sub_total = 0.00
        #     adjusted_qty = 0.00
        #     for stock in stock_location:
        #
        #         if stock.category_id == wizard.category_id:
        #             category_name = stock.category_id.display_name
        #             print("category_name",category_name)
        #             sheet.merge_range(7, 0, 7, 11, category_name, header_merge_format)
        #
        #
        #             for line in stock.line_ids:
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
        #                 location_name = stock.location_id.display_name
        #                 sheet.write(row, 0, no, right)
        #                 sheet.write(row, 1, name, left)
        #                 sheet.write(row, 2, str(date), header_data_format)
        #                 sheet.write(row, 3, code, left)
        #                 sheet.write(row, 4, product, left)
        #                 sheet.write(row, 5, theoretical_qty, right)
        #                 sheet.write(row, 6, product_qty, right)
        #                 sheet.write(row, 7, adjusted_qty, right)
        #                 sheet.write(row, 8, cost, right)
        #                 sheet.write(row, 9, sub_total, right)
        #                 sheet.write(row, 10, remarks, left)
        #                 sheet.write(row, 11, created_by, left)
        #
        #                 row += 1
        #                 no += 1
        ############# Working code by category_id>>>>>>>>>>>>>>>
        # elif wizard.category_id:
        #     stock_location = self.env['stock.inventory'].search([
        #         ('category_id', 'child_of', wizard.category_id.id),
        #         ('date', '>=', wizard.start_date),
        #         ('date', '<=', wizard.end_date)
        #     ])
        #
        #     sub_total = 0.00
        #     adjusted_qty = 0.00
        #     no = 1  # Initialize the entry number
        #     row = 9  # Initialize the row where data will be written in the Excel sheet
        #
        #     category_names = []  # Create a list to store category names
        #
        #     for stock in stock_location:
        #         if stock.category_id == wizard.category_id:
        #             category_names.append(stock.category_id.display_name)  # Add the selected category name
        #             category_names.extend(child.display_name for child in stock.category_id.child_id)  # Add child category names
        #
        #         for line in stock.line_ids:
        #             name = stock.name
        #             date = stock.date
        #             code = line.product_id.default_code
        #             product = line.product_id.display_name
        #             theoretical_qty = line.theoretical_qty
        #             remarks = stock.remarks
        #             product_qty = line.product_qty
        #             adjusted_qty = line.product_qty - line.theoretical_qty
        #             cost = line.product_id.standard_price
        #             sub_total = adjusted_qty * cost
        #             created_by = stock.create_uid.name
        #             location_name = stock.location_id.display_name
        #
        #             # Use the first category name (which is the selected category) as the category name
        #             category_name = category_names[0] if category_names else ''
        #
        #             sheet.write(row, 0, no, right)
        #             sheet.write(row, 1, name, left)
        #             sheet.write(row, 2, str(date), header_data_format)
        #             sheet.write(row, 3, code, left)
        #             sheet.write(row, 4, product, left)
        #             sheet.write(row, 5, theoretical_qty, right)
        #             sheet.write(row, 6, product_qty, right)
        #             sheet.write(row, 7, adjusted_qty, right)
        #             sheet.write(row, 8, cost, right)
        #             sheet.write(row, 9, sub_total, right)
        #             sheet.write(row, 10, remarks, left)
        #             sheet.write(row, 11, created_by, left)
        #             sheet.write(row, 12, category_name, left)  # Add the category name to the Excel sheet
        #
        #             row += 1
        #             no += 1