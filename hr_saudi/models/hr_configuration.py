# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
 

class HRConfiguration(models.Model):
    _name = "hr.configuration"
    _description = 'HR Configuration'

    auto_employee_no = fields.Boolean(string='Employee Number Auto-creation')
    auto_contract_no = fields.Boolean(string='Contract Number Auto-creation')

    @api.model
    def create(self, vals):
        number_records = super(HRConfiguration, self).search_count([])
        if number_records > 0:
            raise ValidationError(_('Cannot create more than ONE record, modify the existing instead!'))
        return super(HRConfiguration, self).create(vals)

    def name_get(self):
        res = []
        for conf in self:
            res.append((conf.id, _('Numbering setting')))
        return res

    def unlink(self):
        for config in self:
            # Check Super User
            if self._uid != SUPERUSER_ID:
                raise ValidationError(_('Cannot delete, please check sysadmin'))
        return super(HRConfiguration, self).unlink()


# class HrPlanActivity(models.Model):
#
#     _inherit = "hr.plan.activity.type"
#
#     summary = fields.Char(translate=True)
#     note = fields.Html(translate=True)


# class HrPlan(models.Model):
#
#     _inherit = "hr.plan"
#
#     name = fields.Char(translate=True)


class HrLeaveAccrualPlan(models.Model):

    _inherit = "hr.leave.accrual.plan"

    name = fields.Char(translate=True)


class ResourceCalendarLeave(models.Model):

    _inherit = "resource.calendar.leaves"

    name = fields.Char(translate=True)
