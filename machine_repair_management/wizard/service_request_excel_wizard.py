from datetime import date, datetime, time
import calendar
import io
import base64
import xlsxwriter
from odoo import api, fields, models


class ServiceRequestExcelWizard(models.TransientModel):
    _name = 'service.request.excel.wizard'
    _description = 'Service Request Excel Report Wizard'

    from_date = fields.Date(
        string='From Date',
        default=lambda self: date.today().replace(day=1)
    )
    to_date = fields.Date(
        string='To Date',
        default=lambda self: date.today().replace(
            day=calendar.monthrange(date.today().year, date.today().month)[1]
        )
    )
    region_id = fields.Many2one('res.region', string='Region')
    product_category_id = fields.Many2one('product.category', string='Product Category')
    job_card_ids = fields.Many2many('project.task', string="Job Card")
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,
                                 required=True)
    work_center_group_id = fields.Many2one('work.center.group', string="Region")

    def generate_excel_report(self):
        import io
        import base64
        import xlsxwriter
        company_id_value = self.env.company.name

        domain = []
        if self.from_date:
            domain.append(('request_date', '>=', self.from_date))
        if self.to_date:
            domain.append(('request_date', '<=', self.to_date))
        # if self.job_card_ids:
        #     domain.append(('id', 'in', self.job_card_ids.ids))
        if self.product_category_id:
            domain.append(('product_category', 'child_of', self.product_category_id.id))
        if self.work_center_group_id:
            domain.append(('work_center_group_id', '=', self.work_center_group_id.id))

        records = self.env['machine.repair.support'].search(domain)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet("Service Requests")

        # Define header format
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#00CED1',  # Aqua / DarkTurquoise
            'border': 2,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#FFFFFF'  # White text
        })

        # Define cell format (with border and text wrap)
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',  # horizontal alignment
            'valign': 'vcenter',  # vertical alignment
            'text_wrap': True  # enable text wrapping
        })

        # Header format for centered text (e.g., report name)
        header_format_center = workbook.add_format({
            'bold': True,
            'bg_color': '#92D050',  # Aqua / Accent 5
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        # Header format for left-aligned text (e.g., company ID)
        header_format_left = workbook.add_format({
            'bold': True,
            'bg_color': '#92D050',  # Aqua / Accent 5
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        # Header format for left-aligned text (e.g., company ID)
        header_format_right = workbook.add_format({
            'bold': True,
            'bg_color': '#92D050',  # Aqua / Accent 5
            'border': 1,
            'align': 'right',
            'valign': 'vcenter'
        })

        # Optional: date and time formats
        date_format = workbook.add_format({'num_format': 'dd-mmm-yyyy', 'border': 1})
        time_format = workbook.add_format({'num_format': 'hh:mm', 'border': 1})

        # Merge for Company ID (columns 0 to 9)
        worksheet.merge_range(0, 0, 0, 8, company_id_value, header_format_left)

        # Merge for Report Name (columns 10 to 18)
        worksheet.merge_range(0, 9, 0, 19, 'Service Request', header_format_center)

        today = date.today()
        current_dt = datetime.now().strftime('%d-%m-%Y %H:%M')
        worksheet.write(0, 20, current_dt, header_format_right)

        headers = [
            'Sl No', 'Region', 'CIC REF.No', 'Call Date', 'Time', 'Contact Name', 'Mobile No', 'District', 'City',
            'Product Category',
            'Product Group', 'Product SubGroup', 'Complaint', 'APPT. Date', 'APPT. Time', 'Call Type', 'Model No',
            'Technician',
            'Capacity', 'Status', 'User Name'
        ]

        # Define column widths corresponding to each header
        column_widths = [
            8, 15, 15, 12, 10, 20, 15, 15, 15, 30, 30, 30, 30,
            12, 10, 20, 40, 20, 12, 32, 30
        ]
        # Set column widths based on headers (minimum width can be adjusted)
        for col_num, width in enumerate(column_widths):
            worksheet.set_column(col_num, col_num, width)

        # Write headers with format
        for col_num, header in enumerate(headers):
            worksheet.write(1, col_num, header, header_format)

        def format_date(dt):
            if not dt:
                return None  # leave the cell empty
            # If dt is already a datetime or date object
            if isinstance(dt, (datetime, date)):
                return dt
            # If dt is a string, try to parse it
            if isinstance(dt, str):
                dt = dt.strip()
                for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):  # common formats
                    try:
                        return datetime.strptime(dt, fmt)
                    except ValueError:
                        continue
            # If parsing fails, return None
            return None

        def format_time(tm):
            if not tm:
                return ''  # Return empty string for empty cells

            # If it's already a datetime object
            if isinstance(tm, datetime):
                return tm

            # If it's a time object, combine with today's date
            if isinstance(tm, time):
                return datetime.combine(datetime.today(), tm)

            # If it's a string
            if isinstance(tm, str):
                tm = tm.strip()
                try:
                    # Try 24-hour format 'HH:MM'
                    return datetime.strptime(tm, '%H:%M')
                except:
                    pass
                try:
                    # Try 24-hour format with seconds 'HH:MM:SS'
                    return datetime.strptime(tm, '%H:%M:%S')
                except:
                    pass
                    # If all fails, return empty string
                return ''

            # For any other type, return empty string
            return ''

        # Write data rows with cell formats
        for row_num, rec in enumerate(records, start=2):
            slno = row_num - 1
            worksheet.write(row_num, 0, slno, cell_format)
            worksheet.write(row_num, 1, rec.work_center_group_id.name if rec.work_center_group_id else '', cell_format)
            worksheet.write(row_num, 2, rec.name or '', cell_format)
            worksheet.write(row_num, 3, format_date(rec.request_created_date), date_format)
            worksheet.write(row_num, 4, format_time(rec.request_created_time), time_format)
            worksheet.write(row_num, 5, rec.customer_name or '', cell_format)
            worksheet.write(row_num, 6, rec.phone or '', cell_format)
            worksheet.write(row_num, 7, rec.country_district_id.name or '', cell_format)
            worksheet.write(row_num, 8, rec.customer_city_id.name or '', cell_format)
            worksheet.write(row_num, 9, rec.product_category.name if rec.product_category else '', cell_format)
            worksheet.write(row_num, 10, rec.product_group_id.name if rec.product_group_id else '', cell_format)
            worksheet.write(row_num, 11, rec.product_sub_group_id.name if rec.product_sub_group_id else '', cell_format)
            worksheet.write(row_num, 12, rec.problem or '', cell_format)
            worksheet.write(row_num, 13, format_date(rec.appt_created_date), date_format)
            worksheet.write(row_num, 14, format_time(rec.appt_created_time), time_format)
            worksheet.write(row_num, 15, rec.call_types_id.name if rec.call_types_id else '', cell_format)
            worksheet.write(row_num, 16, rec.product_id.name or '', cell_format)
            worksheet.write(row_num, 17, rec.user_id.name if rec.user_id else '', cell_format)
            worksheet.write(row_num, 18, rec.capacity or '', cell_format)
            worksheet.write(row_num, 19, rec.service_request_state or '', cell_format)
            worksheet.write(row_num, 20, rec.create_uid.name if rec.create_uid else '', cell_format)

        workbook.close()
        output.seek(0)
        # print(records)

        # self.excel_file = base64.b64encode(output.read())
        # self.file_name = 'Service_Request_Report.xlsx'

        # # Return the wizard view with the download button
        # return {
        #     'name': 'Service Request Report',
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'service.request.excel.wizard',
        #     'view_mode': 'form',
        #     'res_id': self.id,
        #     'target': 'new',
        # }

        file_data = base64.b64encode(output.read())

        attachment = self.env["ir.attachment"].create(
            {
                "name": "Service_Request_Report.xlsx",
                "type": "binary",
                "datas": file_data,
                "store_fname": "Service_Request_Report.xlsx",
                "res_model": self._name,
                "res_id": self.id,
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "new",
        }
