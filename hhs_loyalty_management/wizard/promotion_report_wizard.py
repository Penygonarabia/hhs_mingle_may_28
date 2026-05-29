from odoo import models, fields, api

class PromotionReportWizard(models.TransientModel):
    _name = 'promotion.report.wizard'
    _description = 'Promotion Report Wizard'

    from_date = fields.Date(
        string='From Date', 
        required=True, 
        default=lambda self: fields.Date.context_today(self).replace(day=1)
    )
    to_date = fields.Date(
        string='To Date', 
        required=True, 
        default=fields.Date.context_today
    )

    def action_print_report(self):
        data = {
            'form': self.read()[0],
        }
        return self.env.ref('hhs_loyalty_management.action_report_promotion').report_action(self, data=data)
