# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class report_loan_advance(models.TransientModel):
    _name = "report.loan.advance"

    type = fields.Selection([('loan','Loan'),('advance','Advance')], string="Type", required=True, default='loan')
    only_unpaid = fields.Boolean(string="Only Unpaid", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id, required=True)


    def make_unique(self, original_list):
        unique_list = []
        map(lambda x: unique_list.append(x) if (x not in unique_list) else False, original_list)
        return unique_list  


    def get_loan_advance(self):
        loan_advance_ids = {}
        obj = False
        employee_ids = []
        domain = [('state','=','approve')] 
        for record in self:
            if record.type == 'advance':obj = self.env['hr.employee.advance.ps']
            else:obj = self.env['hr.employee.loan.ps']

            loan_advance_ids = obj.search(domain)
            for loan_advance in loan_advance_ids:
                if record.only_unpaid:
                    if loan_advance.balance_amount > 0:employee_ids += [loan_advance.employee_id] 
                else:employee_ids += [loan_advance.employee_id] 
            if not employee_ids:raise ValidationError(_('Record not found.'))
            result = self.make_unique(employee_ids) 
            
        return True


    def action_generate(self):

        self.get_loan_advance()
        data = {}
        # data['form'] = self.read(cr, uid , ids, context=context)[0]
        # context['landscape'] = True
        # datas = {
        #     'ids': [],
        #     'model': 'report.loan.advance',
        #     'form': data['form']
        # }
        return self.env.ref('hr_loan_advance.report_hr_loan_advance').with_context({'landscape':True}).report_action(self)

    def make_unique(self, original_list):
        unique_list = []
        map(lambda x: unique_list.append(x) if (x not in unique_list) else False, original_list)
        return unique_list

    def get_loan_advance_report(self, domain, data):
        record_ids = {}
        if self.type == 'advance':
            record_ids = self.env['hr.employee.advance.ps'].search(domain)
        else:
            record_ids = self.env['hr.employee.loan.ps'].search(domain)
        return record_ids

    def get_employee(self, data):
        result = {}
        domain = [('state', '=', 'approve')]
        employee_ids = []
        record_ids = self.get_loan_advance_report(domain, data)
        #        if not record_ids:raise Warning(_('Record not found'))
        for record_id in record_ids:
            if self.only_unpaid:
                if record_id.balance_amount > 0 and record_id.employee_id not in employee_ids:
                    employee_ids += [record_id.employee_id]
            else:
                if record_id.employee_id not in employee_ids :
                    employee_ids += [record_id.employee_id]
        return employee_ids

    def get_loan_advance_value(self, employee_id, data):
        result = []
        domain = [('employee_id', '=', employee_id.id), ('state', '=', 'approve')]
        result_ids = self.get_loan_advance_report(domain, data)
        for result_id in result_ids:
            if self.only_unpaid:
                if result_id.balance_amount > 0: result += [result_id]
            else:
                result += [result_id]
        return result







# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
