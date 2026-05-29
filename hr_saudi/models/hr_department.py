# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class HRDepartment(models.Model):
    _inherit = 'hr.department'
    _description = 'HR Department'

    description = fields.Char(string='Description', translate=True)
    is_main_department = fields.Boolean(string='Administration')
    main_department_id = fields.Many2one('hr.department', string='Main Department')
    dept_code = fields.Char(string='Department code')
    name = fields.Char(translate=True)

    @api.constrains('dept_code')
    def _check_dept_code(self):
        """
        Constraint to ensure `dept_code` is unique and follows a specific format.
        """
        for record in self:
            if not record.dept_code:
                raise ValidationError("The Department Code cannot be empty.")
            if not record.dept_code.isalnum():
                raise ValidationError("The Department Code must contain only alphanumeric characters.")
            # Check uniqueness
            existing_dept = self.search([('dept_code', '=', record.dept_code), ('id', '!=', record.id)])
            if existing_dept:
                raise ValidationError(f"The Department Code '{record.dept_code}' must be unique.")


    # def write(self, vals):
    #     # Object
    #     emp_obj = self.env['hr.employee']
    #     # Update all employees in the same department
    #     if vals.get('manager_id', False):
    #         for rec in self:
    #             emp_ids = emp_obj.search([('department_id', '=', rec.id), ('parent_id', '=', rec.manager_id.id)])
    #             for emp in emp_ids:
    #                 emp.parent_id = vals['manager_id']
    #     return super(HRDepartment, self).write(vals)

    class HrWorkLocation(models.Model):

        _inherit = 'hr.work.location'

        name = fields.Char(translate=True)