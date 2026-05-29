from odoo import models, fields, api

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    def action_download_template(self):
        self.ensure_one()

        if not self.contract_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Warning',
                    'message': 'Please select Contract first',
                    'type': 'warning',
                }
            }

        return {
            'type': 'ir.actions.act_url',
            'url': '/hhs/download/equipment/template?contract_id=%s' % self.contract_id.id,
            'target': 'self',
        }

