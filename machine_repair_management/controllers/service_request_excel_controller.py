from odoo import http
from odoo.http import request
import base64

class ServiceRequestExcelController(http.Controller):

    @http.route(['/download/service_request/<int:wizard_id>'], type='http', auth='user')
    def download_service_request_excel(self, wizard_id, **kwargs):
        # Fetch wizard record
        wizard = request.env['service.request.excel.wizard'].browse(wizard_id)
        if wizard.excel_file:
            filecontent = base64.b64decode(wizard.excel_file)
            filename = wizard.file_name or 'Service_Request_Report.xlsx'
            return request.make_response(
                filecontent,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename={filename};')
                ]
            )
        return request.not_found()
