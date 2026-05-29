# See LICENSE file for full copyright and licensing details

from odoo import models, fields,api,_


class AttendancePolicies(models.Model):
    """Attendance Policies."""

    _name = 'hr.attendance.policies'
    

    name = fields.Char(string="Name",)
    attendance_grace_time = fields.Float('Grace Time')
    additional_overtime = fields.Boolean(string="Use Basic Only for Additional Overtime %")
    overtime_id = fields.Many2one(
        'hr.attendances.overtime',
        string='Overtime Rule', ondelete='restrict',
    )
    diff_rule_id = fields.Many2one(
        "hr.attendance.diff", string="Difference Rule", ondelete='restrict')
    late_id = fields.Many2one(
        "hr.attendance.late", string="Late Rule", ondelete='restrict')
    absent_id = fields.Many2one(
        "hr.attendance.absence", string="Absence Rule", ondelete='restrict')
    
    early_checkout_id = fields.Many2one('hr.attendance.earlyout',string="Early Check-out Rules", ondelete='restrict')
