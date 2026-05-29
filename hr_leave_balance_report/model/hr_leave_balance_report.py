# from odoo import models, fields, api
#
# class HRLeaveBalanceReport(models.Model):
#     _name = 'hr.leave.balance.report'
#     _description = 'HR Leave Balance Report'
#
#     employee_id = fields.Many2one('hr.employee', string='Employee')
#     gender = fields.Selection(related='employee_id.gender', string='Gender')
#     nationality = fields.Many2one(related='employee_id.country_id', string='Nationality')
#     department = fields.Many2one(related='employee_id.department_id', string='Department')
#     leave_type = fields.Many2one('hr.leave.type', string='Leave Type')
#     allocated_leave = fields.Float(string='Allocated Leave')
#     taken_leaves = fields.Float(string='Taken Leaves')
#     remaining_leaves = fields.Float(string='Remaining Leaves', compute='_compute_remaining_leaves')
#
#     @api.depends('allocated_leave', 'taken_leaves')
#     def _compute_remaining_leaves(self):
#         for record in self:
#             record.remaining_leaves = record.allocated_leave - record.taken_leaves
#
#     @api.model
#     def create_leave_balance_records(self):
#         # Delete all existing records to avoid duplicates
#         self.search([]).unlink()
#
#         # Create a record for each active employee
#         employees = self.env['hr.employee'].search([('active', '=', True)])
#         for employee in employees:
#             print("employee",employee)
#             self.create({
#                 'employee_id': employee.id,
#                 'allocated_leave': 0.0,
#                 'taken_leaves': 0.0,
#             })
#
#     @api.model
#     def init(self):
#         # Initialize leave balance records when the model is initialized
#         self.create_leave_balance_records()

 # _____________________________________________________________________________________________________________
from odoo import models, fields, api, tools

class HRLeaveBalanceReport(models.Model):
    _name = 'hr.leave.balance.report'
    _description = 'HR Leave Balance Report'
    _auto = False  # indicates that this model is backed by a view, not a table

    employee_id = fields.Many2one('hr.employee', string='Employee')
    # gender = fields.Selection(related='employee_id.gender', string='Gender', store=True)
    gender = fields.Char(string='Gender', store=True)
    # nationality = fields.Many2one(related='employee_id.country_id', string='Nationality', store=True)
    nationality = fields.Many2one('res.country', string='Nationality', store=True)
    # department = fields.Many2one(related='employee_id.department_id', string='Department', store=True)
    department = fields.Many2one('hr.department', string='Department', store=True)
    leave_type = fields.Many2one('hr.leave.type', string='Leave Type', store=True)
    allocated_leave = fields.Float(string='Allocated (Days)')
    taken_leaves = fields.Float(string='Utilized (Days)')
    remaining_leaves = fields.Float(string='Balance (Days)', compute='_compute_remaining_leaves')

    @api.depends('allocated_leave', 'taken_leaves')
    def _compute_remaining_leaves(self):
        for record in self:
            record.remaining_leaves = record.allocated_leave - record.taken_leaves

    @api.model
    def init(self):
        # Drop the view if it exists
        self._cr.execute("""
            DROP VIEW IF EXISTS hr_leave_balance_report CASCADE;
        """)
        # Drop the table if it exists
        self._cr.execute("""
            DROP TABLE IF EXISTS hr_leave_balance_report CASCADE;
        """)

        # Create the view
        self._cr.execute("""
            CREATE OR REPLACE VIEW hr_leave_balance_report AS (
                SELECT
                    row_number() OVER(ORDER BY e.id, lt.id) AS id,
                    e.id AS employee_id,
                    e.gender AS gender,
                    e.country_id AS nationality,
                    e.department_id AS department,
                    lt.id AS leave_type,
                    COALESCE(al.allocated_leave, 0) AS allocated_leave,
                    COALESCE(tl.taken_leaves, 0) AS taken_leaves,
                    COALESCE(al.allocated_leave, 0) - COALESCE(tl.taken_leaves, 0) AS remaining_leaves
                FROM
                    hr_employee e
                LEFT JOIN (
                    SELECT
                        employee_id,
                        holiday_status_id AS leave_type,
                        SUM(number_of_days) AS allocated_leave
                    FROM
                        hr_leave_allocation
                    WHERE
                        state = 'validate'
                    GROUP BY
                        employee_id, holiday_status_id
                ) al ON e.id = al.employee_id
                LEFT JOIN (
                    SELECT
                        employee_id,
                        holiday_status_id AS leave_type,
                        SUM(number_of_days) AS taken_leaves
                    FROM
                        hr_leave
                    WHERE
                        state IN ('validate', 'validate1')
                    GROUP BY
                        employee_id, holiday_status_id
                ) tl ON e.id = tl.employee_id AND al.leave_type = tl.leave_type
                LEFT JOIN hr_leave_type lt ON lt.id = al.leave_type
            );
        """)

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.employee_id.name} - {rec.leave_type.name}" if rec.leave_type else rec.employee_id.name
            result.append((rec.id, name))
        return result
