from odoo import api,fields,models,_


class EmployeeAdvanceReport(models.TransientModel):
    
    _name = "employee.advance.report"
    
    
    employee_ids = fields.Many2many('hr.employee',string="Employee Name")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    
    def print_salary_report(self):
        datas = {
            'model': 'employee.advance.report',
            'form_data': self.read()[0],
        }
        return self.env.ref('employee_advance_report.action_report_employee_advance_report_xlsx').report_action(self, data=datas)

    def print_detail_report(self):
        selection_list = []
        employee_ids = False
        employee_ids = False
        if self.employee_ids:
            employee_ids = self.employee_ids
        else:
            employee_ids = self.env['hr.employee'].search([])

        for employee in employee_ids:
            contract_search = self.env['hr.employee.advance.ps'].search([('employee_id', '=', employee.id)])
            advance_start_date = ''
            ins_rate = 0.00
            ins_date = ''
            ins_remaining_amount = 0.00
            for contract in contract_search:
                emp_no = contract.employee_id.employee_no or ' '
                employee_name = contract.employee_id.display_name or ' '
                type_name = contract.type_id.display_name or ' '
                advance_name = contract.display_name or ' '
                if contract.advance_ins_start_date:
                    advance_start_date = contract.advance_ins_start_date.strftime("%d-%m-%Y") or ' '
                else:
                    advance_start_date = ''
                advance_amount = '{:.2f}'.format(float(contract.advance_amount)) or ' '
                for ins in contract.hr_employee_advance_line_ps:
                    ins_rate = ins.amount
                    if ins.state in ['deducted']:
                        ins_date = ins.installment_date.strftime("%d-%m-%Y")
                        ins_remaining_amount = ins.remaining_value
                ins_rate = '{:.2f}'.format(float(ins_rate)) or''
                ins_date = ins_date or ' '
                ins_remaining_amount = '{:.2f}'.format(float(ins_remaining_amount)) or ' '

                selection_list.append({
                    'employee_name': employee_name,
                    'emp_no': emp_no,
                    'type_name': type_name,
                    'advance_name': advance_name,
                    'advance_start_date': advance_start_date,
                    'advance_amount': advance_amount,
                    'ins_rate': ins_rate,
                    'ins_date': ins_date,
                    'ins_remaining_amount': ins_remaining_amount,
                })

        if not selection_list:
            raise UserError("No data found")

        data = {
            'form_data': self.read()[0],
            'selection': selection_list,
        }
        return self.env.ref('employee_advance_report.action_employee_advance_pdf').with_context(landscape=True).report_action(self, data=data)

