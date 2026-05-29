# custom_addons/hr_employee_own_report/models/hr_employee.py
from odoo import models, fields, api,_

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # personnel_number = fields.Char('Personnel number')
    # joining_date = fields.Date('Joining Date')
    # length_of_service = fields.Char('Length of Service', compute='_compute_length_of_service')
    allocated_leaves = fields.Float(compute='_compute_leave_balances')
    taken_leaves = fields.Float(compute='_compute_leave_balances')
    remaining_leaves = fields.Float(compute='_compute_leave_balances')
    leave_ids = fields.One2many('hr.leave', 'employee_id', string="Leave History")


    @api.depends('name')
    def _compute_leave_balances(self):
        for employee in self:
            allocations = self.env['hr.leave.allocation'].search(
                [('employee_id', '=', employee.id), ('state', '=', 'validate')])
            leaves = self.env['hr.leave'].search([('employee_id', '=', employee.id), ('state', '=', 'validate')])

            allocated_days = sum(allocation.number_of_days for allocation in allocations)
            taken_days = sum(leave.number_of_days for leave in leaves)

            employee.allocated_leaves = allocated_days
            employee.taken_leaves = taken_days
            employee.remaining_leaves = allocated_days - taken_days

    # def get_report_values(self, docids, data=None):
    #     print("raj")
    #     docs = self.browse(docids)
    #     print("docs", docs.employee_id.name)
    #     return {
    #         'doc_ids': docids,
    #         'doc_model': 'hr.employee',
    #         'docs': docs,
    #     }

    # def _compute_length_of_service(self):
    #     for record in self:
    #         if record.joining_date:
    #             delta = fields.Date.today() - record.joining_date
    #             record.length_of_service = f"{delta.days // 365} Years, {delta.days % 365} Days"
    #         else:
    #             record.length_of_service = "N/A"
