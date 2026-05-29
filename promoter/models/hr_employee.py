# File: promoter/models/hr_employee.py

from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_promoter = fields.Boolean(
        string="Is Promoter",
        help="Check if this employee is a promoter"
    )