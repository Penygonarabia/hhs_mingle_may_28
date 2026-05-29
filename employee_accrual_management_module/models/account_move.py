from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    # custom_gratuity_sheet_id = fields.Many2one(
    # 	'mih.auh.gratuity.sheet',
    #     string='Gratuity Sheet',
    #     readonly=True
    # )

    def action_post(self):
        res = super(AccountMove, self).action_post()
        gratuity = self.env['mih.auh.gratuity.line'].search([('custom_move_id', '=', self.id)])
        for rec in gratuity:
            rec.current_last_amt = 0.00
            rec_b = self.env['mih.auh.gratuity.line'].search([('id', '!=', rec.id), ('custom_late_working_day', '<', rec.custom_late_working_day),
                                                               ('custom_employee_id', '=', rec.custom_employee_id.id)], order='custom_late_working_day desc', limit=1)  # Another record
            rec.current_last_amt = rec_b.current_last_amt + rec.custom_esob_amounts

            rec.write({'current_last_amt': rec.current_last_amt})
            rec.action_lock()
        return res