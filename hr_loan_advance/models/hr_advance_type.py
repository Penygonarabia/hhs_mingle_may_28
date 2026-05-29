# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import warnings, RedirectWarning
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT



def _get_employee(obj):
    ids = obj.env['hr.employee'].search([('user_id', '=', obj.env.uid)])
    if ids:
        return ids[0]
    else:
        raise warnings.warn(_('The user is not an employee.'))
    return False

class hr_employee_advance_type_ps(models.Model):
    _name = 'hr.employee.advance.type.ps'

    name = fields.Char(string='Name', required=True, translate=True)





