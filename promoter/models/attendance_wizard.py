from odoo import models, fields, api

class AttendanceWizard(models.TransientModel):
    _name = 'attendance.wizard'
    _description = 'Attendance Wizard'

    dealer_id = fields.Many2one(
        'res.partner',
        string='Dealer',
        domain="[('is_dealer', '=', True)]"
    )
    showroom_id = fields.Many2one('promoter.showroom', string='Showroom')
    promoter_id = fields.Many2one('res.users', string="Promoter")
    att_date = fields.Date(string='Date', store=True)
    shift_from = fields.Selection(selection=lambda self: self._get_time_selection(), string="Shift From Time")
    shift_to = fields.Selection(selection=lambda self: self._get_time_selection(), string="Shift To Time")

    def _get_time_selection(self):
        return [(f"{h:02}:{m:02}", f"{h:02}:{m:02}") for h in range(24) for m in (0, 30)]
    check_in = fields.Date(string='Date', store=True)
    check_out = fields.Date(string='Date', store=True)