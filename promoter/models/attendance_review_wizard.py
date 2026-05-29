from odoo import models, fields, api
from datetime import datetime, timedelta

class AttendanceReviewWizard(models.TransientModel):
    _name = 'attendance.review.wizard'
    _description = 'Attendance Review Wizard'

    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')

    promoter_id = fields.Many2one(
        'res.users',
        string="Promoter",
        domain=lambda self: [('id', 'in', self.available_promoter_ids.ids)]
    )

    available_promoter_ids = fields.Many2many(
        'res.users',
        string="Available Promoters",
        compute='_compute_available_promoters',
        store=False
    )

    @api.depends('from_date', 'to_date')
    def _compute_available_promoters(self):
        """Compute all promoters from assignments overlapping the selected dates"""
        # Get all employees marked as promoters and map to users
        all_promoter_users = self.env['hr.employee'].search([('is_promoter', '=', True)]).mapped('user_id')
        for rec in self:
            if rec.from_date and rec.to_date:
                # Find assignments overlapping the date range
                assignments = self.env['promoter.assignment'].search([
                    ('from_date', '<=', rec.to_date),
                    ('to_date', '>=', rec.from_date),
                    ('active', '=', True),
                ])
                # Map assigned users and filter only promoters
                rec.available_promoter_ids = assignments.mapped('promoter_id').filtered(lambda u: u.is_promoter)
            else:
                # If no dates selected, show all promoters
                rec.available_promoter_ids = all_promoter_users

    @api.onchange('from_date', 'to_date')
    def _onchange_promoter_domain(self):
        """Dynamically restrict promoter selection based on assignments"""
        for rec in self:
            if rec.from_date and rec.to_date:
                assignments = self.env['promoter.assignment'].search([
                    ('from_date', '<=', rec.to_date),
                    ('to_date', '>=', rec.from_date),
                    ('active', '=', True),
                ])
                available_ids = assignments.mapped('promoter_id').ids
                return {'domain': {'promoter_id': [('id', 'in', available_ids)]}}
            else:
                return {'domain': {'promoter_id': []}}


    def action_populate(self):
        domain = []

        if self.promoter_id:
            domain.append(('employee_id.user_id', '=', self.promoter_id.id))
            domain.append(('employee_id.is_promoter', '=', True))
        if not self.promoter_id:
            domain.append(('employee_id.is_promoter', '=', True))
            
        if self.from_date and self.to_date:
            if self.from_date == self.to_date:
                # Single-day: include all times
                from_dt = datetime.combine(self.from_date, datetime.min.time())
                to_dt = datetime.combine(self.from_date, datetime.max.time())
                domain.append(('check_in', '>=', from_dt))
                domain.append(('check_in', '<=', to_dt))
            else:
                # Multi-day: from start of from_date to end of to_date
                from_dt = datetime.combine(self.from_date, datetime.min.time())
                to_dt = datetime.combine(self.to_date, datetime.max.time())
                domain.append(('check_in', '>=', from_dt))
                domain.append(('check_in', '<=', to_dt))
        elif self.from_date:
            from_dt = datetime.combine(self.from_date, datetime.min.time())
            domain.append(('check_in', '>=', from_dt))
        elif self.to_date:
            to_dt = datetime.combine(self.to_date, datetime.max.time())
            domain.append(('check_in', '<=', to_dt))

        attendance_records = self.env['hr.attendance'].search(domain)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Review Attendance',
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form',
            'views': [
                [self.env.ref('hr_attendance.view_attendance_tree').id, 'tree'],
            ],
            'domain': domain,
            'target': 'current',
        }