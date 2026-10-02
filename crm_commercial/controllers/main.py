# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import os

class CrmCommercialController(http.Controller):

    @http.route('/crm_commercial/download_material_template', type='http', auth='user')
    def download_material_template(self, **kw):
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'description', 'sample_material_list.xlsx')
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                content = f.read()
            return request.make_response(
                content,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', 'attachment; filename="sample_material_list.xlsx"')
                ]
            )
        return request.not_found()
