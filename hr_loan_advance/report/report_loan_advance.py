# -*- coding: utf-8 -*-
import time
from odoo.report import report_sxw
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo.osv import osv


class loan_advance(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(loan_advance, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_employee': self.get_employee,
            'get_loan_advance_value': self.get_loan_advance_value,
        })
        self.context=context

    def make_unique(self, original_list):
        unique_list = []
        map(lambda x: unique_list.append(x) if (x not in unique_list) else False, original_list)
        return unique_list  

    def get_loan_advance(self, domain, data):
        record_ids = {}
        env = api.Environment(self.cr, self.uid, self.localcontext)
        if data.get('form',{}).get('type','') == 'advance':record_ids = env['hr.employee.advance.ps'].search(domain)
        else:record_ids = env['hr.employee.loan.ps'].search(domain)
        return record_ids


    def get_employee(self, data):
        result = {}
        domain = [('state','=','approve')]
        employee_ids = []
        record_ids = self.get_loan_advance(domain, data)
#        if not record_ids:raise Warning(_('Record not found')) 
        for record_id in record_ids:
            if data.get('form',{}).get('only_unpaid'):
                if record_id.balance_amount > 0:employee_ids += [record_id.employee_id] 
            else:employee_ids += [record_id.employee_id] 
        result = self.make_unique(employee_ids)
        return result



    def get_loan_advance_value(self, employee_id, data):
        result = []
        domain = [('employee_id','=',employee_id.id), ('state','=','approve')]
        result_ids = self.get_loan_advance(domain, data)
        for result_id in result_ids:
            if data.get('form',{}).get('only_unpaid'):
                if result_id.balance_amount > 0:result += [result_id] 
            else:result += [result_id] 
        return result



class report_loan_advance(models.AbstractModel):
    _name = 'report.hr_loan_advance.report_loan_advance'
    _inherit = 'report.abstract_report'
    _template = 'hr_loan_advance.report_loan_advance'
    _wrapped_report_class = loan_advance      



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:                 
