from odoo import models, api
from datetime import datetime

class PromotionReport(models.AbstractModel):
    _name = 'report.hhs_loyalty_management.report_promotion_template'
    _description = 'Promotion Report Abstract Model'

    @api.model
    def _get_report_values(self, docids, data=None):

        from_date = data['form']['from_date']
        to_date = data['form']['to_date']

        docs = self.env['lp.setup.promotions'].search([
            ('promotion_start_date', '>=', from_date),
            ('promotion_start_date', '<=', to_date),
        ])

        # Format dates
        from_date_format = datetime.strptime(
            from_date, '%Y-%m-%d'
        ).strftime('%d-%m-%Y')

        to_date_format = datetime.strptime(
            to_date, '%Y-%m-%d'
        ).strftime('%d-%m-%Y')

        return {
            'doc_ids': docids,
            'doc_model': 'lp.setup.promotions',
            'docs': docs,
            'data': data,
            'from_date': from_date_format,
            'to_date': to_date_format,
        }
