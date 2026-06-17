from odoo import api, fields, models

class DsalesRejectWizard(models.TransientModel):
    _name = 'dsales.reject.wizard'
    _description = 'Reject Sales Wizard'

    reason = fields.Text(string="Reason", required=True)

    def action_confirm_reject(self):
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', '')
        if active_ids:
            if active_model == 'dsales.showroom.sales.line':
                lines = self.env['dsales.showroom.sales.line'].browse(active_ids)
                sales = lines.mapped('sales_id')
            else:
                sales = self.env['dsales.showroom.sales'].browse(active_ids)
                
            for sale in sales:
                sale.write({
                    'state': 'rejected',
                    'reject_reason': self.reason,
                    'rejected_by': self.env.user.id,
                    'rejected_date': fields.Datetime.now()
                })
                sale._send_whatsapp_notification(sale)
