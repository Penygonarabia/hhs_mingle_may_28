from odoo import api,fields,models,_
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime,date,time
import time
import pytz
import pandas as pd
from odoo.exceptions import warnings
from odoo.exceptions import ValidationError


class EmployeeDetailReport(models.TransientModel):
    
    _name = "employee.detail.report"
    _description = "Employee Detail Report"
    
    
    employee_ids = fields.Many2many('hr.employee',string="Employee Name")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    department_ids = fields.Many2many('hr.department', string = "Department")
    
    job_title_ids = fields.Many2many('hr.job', string="Job Title")
    
    nationality_ids = fields.Many2many('res.country', string="Nationality")
    
    branch_location_ids = fields.Many2many('hr.work.location', string="Branch Location")
    
    from_joining_date = fields.Date(string='From Joining Date')
    
    to_joining_date = fields.Date(string='To Joining Date')
    
    from_termination_date = fields.Date(string='From Termination Date')
    
    to_termination_date = fields.Date(string='To Termination Date')
    
    from_contract_expiry_date = fields.Date(string='From Contract Expiry Date')
    
    to_contract_expiry_date = fields.Date(string='To Contract Expiry Date')
    
    
    sort_by = fields.Selection([('department','Department'),('job_title','Job Title'),('branch_location','Location'),('nationality','Nationality'),('employee_no','Employee No')],string='Sort By')
    
    employee_status = fields.Selection([('all','All'),('active','Active'),('terminated','Terminated')],string="Employee Status", default='all', required = True)
    
    
    
    
    @api.constrains('from_joining_date', 'to_joining_date')
    def _check_from_joining_date(self):
        if self.filtered(lambda c: c.to_joining_date and c.from_joining_date > c.to_joining_date):
            raise ValidationError(_('From Joining Date must be less than Period To Joining Date.'))
    
    @api.constrains('from_termination_date', 'to_termination_date')
    def _check_from_termination_date(self):
        if self.filtered(lambda c: c.to_termination_date and c.from_termination_date > c.to_termination_date):
            raise ValidationError(_('from termination date must be less than to termination date.'))
  
    
    @api.constrains('from_contract_expiry_date', 'to_contract_expiry_date')
    def _check_from_termination_date(self):
        if self.filtered(lambda c: c.to_contract_expiry_date and c.from_contract_expiry_date > c.to_contract_expiry_date):
            raise ValidationError(_('from contract expiry date must be less than to contract expiry date.'))
  
            
    @api.onchange('from_joining_date')
    def _onchange_from_joining_date(self):
        for rec in self:
            if rec.from_joining_date:
                rec.to_joining_date = rec.from_joining_date  
                
                
    @api.onchange('from_termination_date')
    def _onchange_from_termination_date(self):
        for rec in self:
            if rec.from_termination_date:
                rec.to_termination_date = rec.from_termination_date  
    
    
    @api.onchange('from_contract_expiry_date')
    def _onchange_from_contract_expiry_date(self):
        for rec in self:
            if rec.from_contract_expiry_date:
                rec.to_contract_expiry_date = rec.from_contract_expiry_date                           
    
    
    def print_salary_report(self):
        datas = {
            'model': 'employee.detail.report',
            'form_data': self.read()[0],
        }
        return self.env.ref('employee_details_report.action_report_employee_detail_report_xlsx').report_action(self,data=datas)

    def print_detail_report(self):
        selection_list = []
        employee_ids = False
        
        domain = []
        
     
        employee_status = False
        dept_ids=False
            
        domain += [('id', 'in', self.employee_ids.ids if self.employee_ids else self.env['hr.employee'].search([]).ids)]

        if self.from_joining_date and self.to_joining_date:
            domain += [('joining_date', '<=', self.to_joining_date), ('joining_date', '>=', self.from_joining_date)]

        if self.from_termination_date and self.to_termination_date:
            domain += [('exit_date', '<=', self.to_termination_date), ('exit_date', '>=', self.from_termination_date)]

        if self.from_contract_expiry_date and self.to_contract_expiry_date:
            domain += [('contract_id.date_end', '<=', self.to_contract_expiry_date), ('contract_id.date_end', '>=', self.from_contract_expiry_date)]
                        
    
        if self.employee_status:
            if self.employee_status == 'all':
                domain += [('state','in',['draft','exit'])]
                # domain += ['|', ('contract_warning', '=', False),
                #            ('contract_warning', '=', True)]
            elif self.employee_status == 'active':
                domain += [('state', '=', 'draft'), ('contract_warning', '=', False)]
            elif self.employee_status == 'terminated':
                domain += [('state', '=', 'exit'), ('contract_warning', '=', True)]


        
        if self.department_ids:
            domain += [('department_id', 'in', self.department_ids.ids)]

        if self.job_title_ids:
            domain += [('job_id', 'in', self.job_title_ids.ids)]

        if self.nationality_ids:
            domain += [('country_of_birth', 'in', self.nationality_ids.ids)]

        if self.branch_location_ids:
            domain += [('work_location_id', 'in', self.branch_location_ids.ids)]
    
        employee_search = self.env['hr.employee'].search(domain)
        employee_search = employee_search.sorted(key=lambda s:s.name.lower())

        employee_lst =[]
        
        if self.sort_by:
            if self.sort_by == 'department':
                employee_search = employee_search.filtered(lambda c : c.department_id)
                employee_search = employee_search.sorted(key=lambda c:c.department_id.name.lower())
            
            elif self.sort_by == 'job_title':
                employee_search = employee_search.filtered(lambda c : c.job_id) 
                employee_search = employee_search.sorted(key = lambda c : c.job_id.name.lower())
                
            elif self.sort_by == 'nationality':
                employee_search = employee_search.filtered(lambda c : c.country_of_birth)
                employee_search = employee_search.sorted(key = lambda c:c.country_of_birth.name.lower())
            
            elif self.sort_by == 'branch_location':
                employee_search = employee_search.filtered(lambda c : c.work_location_id)
                employee_search = employee_search.sorted(key = lambda c:c.work_location_id.name.lower())        
            
            elif self.sort_by =='employee_no':
                employee_search = employee_search.sorted(
                    key=lambda c: (
                        0 if c.employee_no and isinstance(c.employee_no, str) and c.employee_no.isdigit() else 1,  # Prioritize numeric first
                        int(c.employee_no) if c.employee_no and isinstance(c.employee_no, str) and c.employee_no.isdigit() else c.employee_no or ''
                    ))

        
        '''for two department search only two department is sorting and display it irresepective of captial and small letter department name'''
        if self.department_ids:
            employee_search = employee_search.sorted(key=lambda c:c.department_id.name.lower())
            
        if self.job_title_ids:
            employee_search = employee_search.sorted(key = lambda c : c.job_id.name.lower())
        
        if self.nationality_ids:
            employee_search = employee_search.sorted(key = lambda c:c.country_of_birth.name.lower())
        
        if self.branch_location_ids:
            employee_search = employee_search.sorted(key = lambda c:c.work_location_id.name.lower())        
                        
                
        seen_department = set()
        seen_job = set()
        seen_nation = set()
        seen_branch = set()
        num = 1
        for employee in employee_search:
            gender_display_name = dict(employee._fields['gender'].selection).get(
                            employee.gender)
            religion_display_name = dict(employee._fields['religion'].selection).get(
                employee.religion)
            state_display_name = dict(employee.contract_id._fields['state'].selection).get(
                    employee.contract_id.state)
            selection_list.append({
                'employee_name': employee.display_name or ' ',
                'emp_no': employee.employee_no or ' ',
                'gender': gender_display_name,
                'd_o_b': employee.birthday.strftime("%d-%m-%Y") if employee.birthday else '',
                'nationality': employee.country_of_birth.name or ' ',
                'religion': religion_display_name,
                'job_title': employee.job_id.name or ' ',

                'department': employee.department_id.name or ' ',
                'location':employee.work_location_id.name or ' ',
                'date_of_joining': employee.joining_date.strftime("%d-%m-%Y") if employee.joining_date else '',
                'date_of_exit': employee.exit_date.strftime("%d-%m-%Y") if employee.exit_date else '',
                'contract_name':employee.contract_id.name or ' ',
                'contract_start_date':employee.contract_id.date_start.strftime("%d-%m-%Y") if employee.contract_id.date_start else ' ',
                'contract_end_date':employee.contract_id.date_end.strftime("%d-%m-%Y") if employee.contract_id.date_end else '',
                'status': state_display_name,

            })

            employee_lst.append(employee.employee_no)

        if len(employee_lst)==0:
            raise ValidationError("Employee is not there in this  Range")
    
        data = {
                'form_data': self.read()[0],
                'selection': selection_list,
                'from_joining_date':self.from_joining_date.strftime("%d-%m-%Y") if self.from_joining_date else ' ',
                'to_joining_date':self.to_joining_date.strftime("%d-%m-%Y") if self.to_joining_date  else ' ',
                'from_termination_date':self.from_termination_date.strftime("%d-%m-%Y") if self.from_termination_date else ' ',
                'to_termination_date':self.to_termination_date.strftime("%d-%m-%Y") if self.to_termination_date else ' ',
                 'from_contract_expiry_date':self.from_contract_expiry_date.strftime("%d-%m-%Y") if self.from_contract_expiry_date else ' ',
                'to_contract_expiry_date':self.to_contract_expiry_date.strftime("%d-%m-%Y") if self.to_contract_expiry_date else ' '
               
               
            }
        return self.env.ref('employee_details_report.action_employee_detail_pdf').with_context(landscape=True).report_action(self, data=data)
        
        

        
        # '''From Joining Date and to Joining Date '''
        # if self.from_joining_date and self.to_joining_date:
        #
        #     employee_ids = False
        #     employee_status = False
        #     if self.employee_status:
        #         employee_status = self.employee_status
        #
        #
        #     if self.employee_ids:
        #         employee_ids = self.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #     joining_lst = []
        #     for employee in employee_ids:
        #         joining_date_search = False
        #
        #         if employee_status == 'active':
        #             joining_date_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('joining_date','>=',self.from_joining_date),('joining_date','<=',self.to_joining_date),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             joining_date_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('id','=',employee.id),('joining_date','>=',self.from_joining_date),('joining_date','<=',self.to_joining_date),('state','=','exit')])
        #
        #         elif employee_status == 'all':
        #             joining_date_search = self.env['hr.employee'].search([('id','=',employee.id),('joining_date','>=',self.from_joining_date),('joining_date','<=',self.to_joining_date)])
        #
        #
        #
        #         if joining_date_search:
        #             for joining_date in joining_date_search:
        #                 gender_display_name = dict(joining_date._fields['gender'].selection).get(
        #                     joining_date.gender)
        #                 religion_display_name = dict(joining_date._fields['religion'].selection).get(
        #                     joining_date.religion)
        #                 state_display_name = dict(joining_date.contract_id._fields['state'].selection).get(
        #                         joining_date.contract_id.state)
        #                 selection_list.append({
        #                     'employee_name': joining_date.display_name or ' ',
        #                     'emp_no': joining_date.employee_no or ' ',
        #                     'gender': gender_display_name,
        #                     'd_o_b': joining_date.birthday.strftime("%d-%m-%Y") if joining_date.birthday else '',
        #                     'nationality': joining_date.country_id.name or ' ',
        #                     'religion': religion_display_name,
        #                     'job_title': joining_date.job_id.name or ' ',
        #
        #                     'department': joining_date.department_id.name or ' ',
        #                     'location':joining_date.work_location_id.name or ' ',
        #                     'date_of_joining': joining_date.joining_date.strftime("%d-%m-%Y") if joining_date.joining_date else '',
        #                     'date_of_exit': joining_date.exit_date.strftime("%d-%m-%Y") if joining_date.exit_date else '',
        #                     'contract_name':joining_date.contract_id.name or ' ',
        #                     'contract_start_date':joining_date.contract_id.date_start.strftime("%d-%m-%Y") if joining_date.contract_id.date_start else ' ',
        #                     'contract_end_date':joining_date.contract_id.date_end.strftime("%d-%m-%Y") if joining_date.contract_id.date_end else '',
        #                     'status': state_display_name,
        #
        #                 })
        #
        #
        #
        #                 joining_lst.append(joining_date.employee_no)
        #
        #
        #     if len(joining_lst)==0:
        #         raise ValidationError("Employee is not there in this Date  Range")
        #
        #     data = {
        #         'form_data': self.read()[0],
        #         'selection': selection_list,
        #         'from_joining_date':self.from_joining_date.strftime("%d-%m-%Y"),
        #         'to_joining_date':self.to_joining_date.strftime("%d-%m-%Y")
        #
        #     }
        #     return self.env.ref('employee_details_report.action_employee_detail_pdf').with_context(landscape=True).report_action(self, data=data)
        #
        #
        #     '''From contract expiry Date and to Contract expiry Date '''
        # elif self.from_contract_expiry_date and self.to_contract_expiry_date:
        #
        #
        #     employee_ids = False
        #     employee_status = False
        #     if self.employee_status:
        #         employee_status = self.employee_status
        #
        #
        #     if self.employee_ids:
        #         employee_ids = self.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #     expiry_lst = []
        #     for employee in employee_ids:
        #         expiration_search = False
        #
        #         if employee_status == 'active':
        #             expiration_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('contract_id.date_end','>=',self.from_contract_expiry_date),('contract_id.date_end','<=',self.to_contract_expiry_date),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             expiration_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('id','=',employee.id),('contract_id.date_end','>=',self.from_contract_expiry_date),('contract_id.date_end','<=',self.to_contract_expiry_date),('state','=','exit')])
        #
        #         elif employee_status == 'all':
        #             expiration_search = self.env['hr.employee'].search([('id','=',employee.id),('contract_id.date_end','>=',self.from_contract_expiry_date),('contract_id.date_end','<=',self.to_contract_expiry_date)])
        #
        #         if expiration_search:
        #             for expiry in expiration_search:
        #
        #                 gender_display_name = dict(expiry._fields['gender'].selection).get(
        #                     expiry.gender)
        #                 religion_display_name = dict(expiry._fields['religion'].selection).get(
        #                     expiry.religion)
        #                 state_display_name = dict(expiry.contract_id._fields['state'].selection).get(
        #                         expiry.contract_id.state)
        #                 selection_list.append({
        #                     'employee_name': expiry.display_name or ' ',
        #                     'emp_no': expiry.employee_no or ' ',
        #                     'gender': gender_display_name,
        #                     'd_o_b': expiry.birthday.strftime("%d-%m-%Y") if expiry.birthday else '',
        #                     'nationality': expiry.country_id.name or ' ',
        #                     'religion': religion_display_name,
        #                     'job_title': expiry.job_id.name or ' ',
        #
        #                     'department': expiry.department_id.name or ' ',
        #                     'location':expiry.work_location_id.name or ' ',
        #                     'date_of_joining': expiry.joining_date.strftime("%d-%m-%Y") if expiry.joining_date else '',
        #                     'date_of_exit': expiry.exit_date.strftime("%d-%m-%Y") if expiry.exit_date else '',
        #                     'contract_name':expiry.contract_id.name or ' ',
        #                     'contract_start_date':expiry.contract_id.date_start.strftime("%d-%m-%Y") if expiry.contract_id.date_start else ' ',
        #                     'contract_end_date':expiry.contract_id.date_end.strftime("%d-%m-%Y") if expiry.contract_id.date_end else '',
        #                     'status': state_display_name,
        #
        #                 })
        #
        #
        #
        #                 expiry_lst.append(expiry.employee_no)
        #
        #
        #     if len(expiry_lst)==0:
        #         raise ValidationError("Employee is not there in this Date  Range")
        #
        #     data = {
        #         'form_data': self.read()[0],
        #         'selection': selection_list,
        #         'from_contract_expiry_date':self.from_contract_expiry_date.strftime("%d-%m-%Y"),
        #         'to_contract_expiry_date':self.to_contract_expiry_date.strftime("%d-%m-%Y")
        #     }
        #     return self.env.ref('employee_details_report.action_employee_detail_pdf').with_context(landscape=True).report_action(self, data=data)
        #
        #     ''' Termination wise Employee search'''
        # elif self.from_termination_date and self.to_termination_date:
        #
        #     employee_ids = False
        #     employee_status = False
        #     if self.employee_status:
        #         employee_status = self.employee_status
        #
        #
        #     if self.employee_ids:
        #         employee_ids = self.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #     termination_lst = []
        #     for employee in employee_ids:
        #         termination_search = False
        #
        #         if employee_status == 'active':
        #             termination_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('exit_date','>=',self.from_termination_date),('exit_date','<=',self.to_termination_date),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             termination_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('id','=',employee.id),('exit_date','>=',self.from_termination_date),('exit_date','<=',self.to_termination_date),('state','=','exit')])
        #
        #         elif employee_status == 'all':
        #             termination_search = self.env['hr.employee'].search([('id','=',employee.id),('exit_date','>=',self.from_termination_date),('exit_date','<=',self.to_termination_date)])
        #
        #         if termination_search:
        #             for terminate in termination_search:
        #                 gender_display_name = dict(terminate._fields['gender'].selection).get(
        #                     terminate.gender)
        #                 religion_display_name = dict(terminate._fields['religion'].selection).get(
        #                     terminate.religion)
        #                 state_display_name = dict(terminate.contract_id._fields['state'].selection).get(
        #                         terminate.contract_id.state)
        #                 selection_list.append({
        #                     'employee_name': terminate.display_name or ' ',
        #                     'emp_no': terminate.employee_no or ' ',
        #                     'gender': gender_display_name,
        #                     'd_o_b': terminate.birthday.strftime("%d-%m-%Y") if terminate.birthday else '',
        #                     'nationality': terminate.country_id.name or ' ',
        #                     'religion': religion_display_name,
        #                     'job_title': terminate.job_id.name or ' ',
        #
        #                     'department': terminate.department_id.name or ' ',
        #                     'location':terminate.work_location_id.name or ' ',
        #                     'date_of_joining': terminate.joining_date.strftime("%d-%m-%Y") if terminate.joining_date else '',
        #                     'date_of_exit': terminate.exit_date.strftime("%d-%m-%Y") if terminate.exit_date else '',
        #                     'contract_name':terminate.contract_id.name or ' ',
        #                     'contract_start_date':terminate.contract_id.date_start.strftime("%d-%m-%Y") if terminate.contract_id.date_start else ' ',
        #                     'contract_end_date':terminate.contract_id.date_end.strftime("%d-%m-%Y") if terminate.contract_id.date_end else '',
        #                     'status': state_display_name,
        #
        #                 })
        #
        #
        #
        #                 termination_lst.append(terminate.employee_no)
        #
        #
        #     if len(termination_lst)==0:
        #         raise ValidationError("Employee is not there in this Date  Range")
        #
        #     data = {
        #         'form_data': self.read()[0],
        #         'selection': selection_list,
        #         'from_termination_date':self.from_termination_date.strftime("%d-%m-%Y"),
        #         'to_termination_date':self.to_termination_date.strftime("%d-%m-%Y")
        #
        #     }
        #     return self.env.ref('employee_details_report.action_employee_detail_pdf').with_context(landscape=True).report_action(self, data=data)
        #
        #     '''Department wise employee and sort wise'''
        # elif self.department_ids or self.sort_by == 'department':
        #
        #     employee_ids = False
        #     dept_ids = False
        #     employee_status = False
        #
        #     if self.employee_status:
        #         employee_status = self.employee_status
        #
        #     if self.employee_ids:
        #         employee_ids = self.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if self.department_ids:
        #         dept_ids = self.department_ids
        #     else:
        #         dept_ids = self.env['hr.department'].search([])
        #
        #     dept_lst = []
        #     for dept in dept_ids:
        #         # for employee in employee_ids:
        #         department_search = False
        #         if employee_status == 'active':
        #             if employee_ids:
        #                 department_search = self.env['hr.employee'].search([('contract_warning','=',False),('department_id','=',dept.id),('state','=','draft'),('id','in',employee_ids.ids)])
        #             else:
        #                 department_search = self.env['hr.employee'].search([('contract_warning','=',False),('department_id','=',dept.id),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             if employee_ids:
        #                 department_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('department_id','=',dept.id),('state','=','exit'),('id','in',employee_ids.ids)])
        #             else:    
        #                 department_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('department_id','=',dept.id),('state','=','exit')])
        #         elif employee_status == 'all':
        #             if employee_ids:
        #                 department_search = self.env['hr.employee'].search([('department_id','=',dept.id),('id','in',employee_ids.ids)])
        #             else:
        #                 department_search = self.env['hr.employee'].search([('department_id','=',dept.id)])
        #
        #         if department_search:
        #             for department in department_search:
        #
        #                 gender_display_name = dict(department._fields['gender'].selection).get(
        #                 department.gender)
        #                 religion_display_name = dict(department._fields['religion'].selection).get(
        #                     department.religion)
        #                 state_display_name = dict(department.contract_id._fields['state'].selection).get(
        #                         department.contract_id.state)
        #                 selection_list.append({
        #                     'employee_name': department.display_name or ' ',
        #                     'emp_no': department.employee_no or ' ',
        #                     'gender': gender_display_name,
        #                     'd_o_b': department.birthday.strftime("%d-%m-%Y") if department.birthday else '',
        #                     'nationality': department.country_id.name or ' ',
        #                     'religion': religion_display_name,
        #                     'job_title': department.job_id.name or ' ',
        #
        #                     'department': department.department_id.name or ' ',
        #                     'location':department.work_location_id.name or ' ',
        #                     'date_of_joining': department.joining_date.strftime("%d-%m-%Y") if department.joining_date else '',
        #                     'date_of_exit': department.exit_date.strftime("%d-%m-%Y") if department.exit_date else '',
        #                     'contract_name':department.contract_id.name or ' ',
        #                     'contract_start_date':department.contract_id.date_start.strftime("%d-%m-%Y") if department.contract_id.date_start else ' ',
        #                     'contract_end_date':department.contract_id.date_end.strftime("%d-%m-%Y") if department.contract_id.date_end else '',
        #                     'status': state_display_name,
        #
        #                 })
        #
        #
        #
        #                 dept_lst.append(department.employee_no)
        #
        #
        #     if len(dept_lst)==0:
        #         raise ValidationError("Employee is not there in this Date  Range")
        #
        #     data = {
        #         'form_data': self.read()[0],
        #         'selection': selection_list,
        #     }
        #     return self.env.ref('employee_details_report.action_employee_detail_pdf').with_context(landscape=True).report_action(self, data=data)
        #
        #
        #     '''Job wise search and sort wise job'''    
        #
        # elif self.job_title_ids or self.sort_by=='job_title':
        #
        #     employee_ids = False
        #     job_ids = False
        #     employee_status = False
        #
        #     if self.employee_status:
        #         employee_status = self.employee_status
        #
        #     if self.employee_ids:
        #         employee_ids = self.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if self.job_title_ids:
        #         job_ids = self.job_title_ids
        #     else:
        #         job_ids = self.env['hr.job'].search([])
        #
        #     job_lst = []
        #     jobs_name = False
        #     for jobs in job_ids:
        #         # for employee in employee_ids:
        #         job_search = False
        #         if employee_status == 'active':
        #             if employee_ids:
        #                 job_search = self.env['hr.employee'].search([('contract_warning','=',False),('job_id','=',jobs.id),('state','=','draft'),('id','in',employee_ids.ids)])
        #             else:
        #                 job_search = self.env['hr.employee'].search([('contract_warning','=',False),('job_id','=',jobs.id),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             if employee_ids:
        #                 job_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('job_id','=',jobs.id),('state','=','exit'),('id','in',employee_ids.ids)])
        #             else:
        #                 job_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('job_id','=',jobs.id),('state','=','exit')])
        #         elif employee_status == 'all':
        #             if employee_ids: 
        #                 job_search = self.env['hr.employee'].search([('job_id','=',jobs.id),('id','in',employee_ids.ids)])
        #             else:
        #                 job_search = self.env['hr.employee'].search([('job_id','=',jobs.id)])
        #
        #         if job_search:
        #             jobs_name = jobs.name
        #
        #             for job in job_search:
        #                 gender_display_name = dict(job._fields['gender'].selection).get(
        #                 job.gender)
        #                 religion_display_name = dict(job._fields['religion'].selection).get(
        #                     job.religion)
        #                 state_display_name = dict(job.contract_id._fields['state'].selection).get(
        #                         job.contract_id.state)
        #                 selection_list.append({
        #                     'employee_name': job.display_name or ' ',
        #                     'emp_no': job.employee_no or ' ',
        #                     'gender': gender_display_name,
        #                     'd_o_b': job.birthday.strftime("%d-%m-%Y") if job.birthday else '',
        #                     'nationality': job.country_id.name or ' ',
        #                     'religion': religion_display_name,
        #                     'job_title': job.job_id.name or ' ',
        #
        #                     'department': job.department_id.name or ' ',
        #                     'location':job.work_location_id.name or ' ',
        #                     'date_of_joining': job.joining_date.strftime("%d-%m-%Y") if job.joining_date else '',
        #                     'date_of_exit': job.exit_date.strftime("%d-%m-%Y") if job.exit_date else '',
        #                     'contract_name':job.contract_id.name or ' ',
        #                     'contract_start_date':job.contract_id.date_start.strftime("%d-%m-%Y") if job.contract_id.date_start else ' ',
        #                     'contract_end_date':job.contract_id.date_end.strftime("%d-%m-%Y") if job.contract_id.date_end else '',
        #                     'status': state_display_name,
        #
        #                 })
        #
        #
        #
        #                 job_lst.append(job.employee_no)
        #
        #
        #     if len(job_lst)==0:
        #         raise ValidationError("Employee is not there in this Date  Range")
        #
        #     data = {
        #         'form_data': self.read()[0],
        #         'selection': selection_list,
        #         'jobsname':jobs_name
        #     }
        #     return self.env.ref('employee_details_report.action_employee_detail_pdf').with_context(landscape=True).report_action(self, data=data)
        #
        #
        #
        #
        #     '''Nationality wise Employee Details'''
        #
        # elif self.nationality_ids or self.sort_by=='nationality':
        #
        #
        #     employee_ids = False
        #     nationality_ids = False
        #     employee_status = False
        #
        #     if self.employee_status:
        #         employee_status = self.employee_status
        #
        #     if self.employee_ids:
        #         employee_ids = self.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if self.nationality_ids:
        #         nationality_ids = self.nationality_ids
        #     else:
        #         nationality_ids = self.env['res.country'].search([])
        #
        #
        #     nationality_lst = []
        #     for nationality in nationality_ids:
        #         # for employee in employee_ids:
        #         nationality_search = False
        #         if employee_status == 'active':
        #             if employee_ids:
        #                 nationality_search = self.env['hr.employee'].search([('contract_warning','=',False),('country_of_birth','=',nationality.id),('state','=','draft'),('id','in',employee_ids.ids)])
        #             else:
        #                 nationality_search = self.env['hr.employee'].search([('contract_warning','=',False),('country_of_birth','=',nationality.id),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             if employee_ids:
        #                 nationality_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('country_of_birth','=',nationality.id),('state','=','exit'),('id','in',employee_ids.ids)])
        #             else:
        #                 nationality_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('country_of_birth','=',nationality.id),('state','=','exit')])
        #         elif employee_status == 'all':
        #             if employee_ids:
        #                 nationality_search = self.env['hr.employee'].search([('country_of_birth','=',nationality.id),('id','in',employee_ids.ids)])
        #             else:
        #                 nationality_search = self.env['hr.employee'].search([('country_of_birth','=',nationality.id)])
        #
        #         if nationality_search:
        #             for nation in nationality_search:
        #
        #                 gender_display_name = dict(nation._fields['gender'].selection).get(
        #                 nation.gender)
        #                 religion_display_name = dict(nation._fields['religion'].selection).get(
        #                     nation.religion)
        #                 state_display_name = dict(nation.contract_id._fields['state'].selection).get(
        #                         nation.contract_id.state)
        #                 selection_list.append({
        #                     'employee_name': nation.display_name or ' ',
        #                     'emp_no': nation.employee_no or ' ',
        #                     'gender': gender_display_name,
        #                     'd_o_b': nation.birthday.strftime("%d-%m-%Y") if nation.birthday else '',
        #                     'nationality': nation.country_id.name or ' ',
        #                     'religion': religion_display_name,
        #                     'job_title': nation.job_id.name or ' ',
        #
        #                     'department': nation.department_id.name or ' ',
        #                     'location':nation.work_location_id.name or ' ',
        #                     'date_of_joining': nation.joining_date.strftime("%d-%m-%Y") if nation.joining_date else '',
        #                     'date_of_exit': nation.exit_date.strftime("%d-%m-%Y") if nation.exit_date else '',
        #                     'contract_name':nation.contract_id.name or ' ',
        #                     'contract_start_date':nation.contract_id.date_start.strftime("%d-%m-%Y") if nation.contract_id.date_start else ' ',
        #                     'contract_end_date':nation.contract_id.date_end.strftime("%d-%m-%Y") if nation.contract_id.date_end else '',
        #                     'status': state_display_name,
        #
        #                 })
        #
        #
        #
        #                 nationality_lst.append(nation.employee_no)
        #
        #
        #     if len(nationality_lst)==0:
        #         raise ValidationError("Employee is not there in this Date  Range")
        #
        #     data = {
        #         'form_data': self.read()[0],
        #         'selection': selection_list,
        #     }
        #     return self.env.ref('employee_details_report.action_employee_detail_pdf').with_context(landscape=True).report_action(self, data=data)
        #
        #
        #
        #     ''' Branch Location'''                
        #
        # elif self.branch_location_ids or self.sort_by=='branch_location':
        #
        #
        #     employee_ids = False
        #     branch_ids = False
        #     employee_status = False
        #
        #     if self.employee_status:
        #         employee_status = self.employee_status
        #
        #     if self.employee_ids:
        #         employee_ids = self.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if self.branch_location_ids:
        #         branch_ids = self.branch_location_ids
        #     else:
        #         branch_ids = self.env['hr.work.location'].search([])
        #
        #     branch_lst = []
        #     for branch_location in branch_ids:
        #         # for employee in employee_ids:
        #         branch_search = False
        #         if employee_status == 'active':
        #             if employee_ids:
        #                 branch_search = self.env['hr.employee'].search([('contract_warning','=',False)('work_location_id','=',branch_location.id),('state','=','draft'),('id','in',employee_ids.ids)])
        #             else:
        #                 branch_search = self.env['hr.employee'].search([('contract_warning','=',False)('work_location_id','=',branch_location.id),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             if employee_ids:
        #                 branch_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('work_location_id','=',branch_location.id),('state','=','exit'),('id','in',employee_ids.ids)])
        #             else:
        #                 branch_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('work_location_id','=',branch_location.id),('state','=','exit')])
        #         elif employee_status == 'all':
        #             if employee_ids:
        #                 branch_search = self.env['hr.employee'].search([('work_location_id','=',branch_location.id),('id','in',employee_ids.ids)])
        #             else:
        #                 branch_search = self.env['hr.employee'].search([('work_location_id','=',branch_location.id)])
        #
        #         if branch_search:
        #             for branch in branch_search:
        #                 gender_display_name = dict(branch._fields['gender'].selection).get(
        #                 branch.gender)
        #                 religion_display_name = dict(branch._fields['religion'].selection).get(
        #                     branch.religion)
        #                 state_display_name = dict(branch.contract_id._fields['state'].selection).get(
        #                         branch.contract_id.state)
        #                 selection_list.append({
        #                     'employee_name': branch.display_name or ' ',
        #                     'emp_no': branch.employee_no or ' ',
        #                     'gender': gender_display_name,
        #                     'd_o_b': branch.birthday.strftime("%d-%m-%Y") if branch.birthday else '',
        #                     'nationality': branch.country_id.name or ' ',
        #                     'religion': religion_display_name,
        #                     'job_title': branch.job_id.name or ' ',
        #
        #                     'department': branch.department_id.name or ' ',
        #                     'location':branch.work_location_id.name or ' ',
        #                     'date_of_joining': branch.joining_date.strftime("%d-%m-%Y") if branch.joining_date else '',
        #                     'date_of_exit': branch.exit_date.strftime("%d-%m-%Y") if branch.exit_date else '',
        #                     'contract_name':branch.contract_id.name or ' ',
        #                     'contract_start_date':branch.contract_id.date_start.strftime("%d-%m-%Y") if branch.contract_id.date_start else ' ',
        #                     'contract_end_date':branch.contract_id.date_end.strftime("%d-%m-%Y") if branch.contract_id.date_end else '',
        #                     'status': state_display_name,
        #
        #                 })
        #
        #
        #
        #                 branch_lst.append(branch.employee_no)
        #
        #
        #     if len(branch_lst)==0:
        #         raise ValidationError("Employee is not there in this Date  Range")
        #
        #     data = {
        #         'form_data': self.read()[0],
        #         'selection': selection_list,
        #     }
        #     return self.env.ref('employee_details_report.action_employee_detail_pdf').with_context(landscape=True).report_action(self, data=data)
        #
        #
        # else:
        #     employee_ids = False
        #     employee_status = False
        #
        #     if self.employee_status:
        #         employee_status = self.employee_status
        #     if self.employee_ids:
        #         employee_ids = self.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     contract_lst = []
        #     for employee in employee_ids:
        #         contract_search = False
        #         if employee_status == 'active':
        #             contract_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             contract_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('id','=',employee.id),('state','=','exit')])
        #         elif employee_status == 'all':
        #             contract_search = self.env['hr.employee'].search([('id','=',employee.id)])
        #         for contract in contract_search:
        #             gender_display_name = dict(contract._fields['gender'].selection).get(
        #                     contract.gender)
        #             religion_display_name = dict(contract._fields['religion'].selection).get(
        #                 contract.religion)
        #             state_display_name = dict(contract.contract_id._fields['state'].selection).get(
        #                     contract.contract_id.state)
        #             selection_list.append({
        #                 'employee_name': contract.display_name or ' ',
        #                 'emp_no': contract.employee_no or ' ',
        #                 'gender': gender_display_name,
        #                 'd_o_b': contract.birthday.strftime("%d-%m-%Y") if contract.birthday else '',
        #                 'nationality': contract.country_id.name or ' ',
        #                 'religion': religion_display_name,
        #                 'job_title': contract.job_id.name or ' ',
        #
        #                 'department': contract.department_id.name or ' ',
        #                 'location':contract.work_location_id.name or ' ',
        #                 'date_of_joining': contract.joining_date.strftime("%d-%m-%Y") if contract.joining_date else '',
        #                 'date_of_exit': contract.exit_date.strftime("%d-%m-%Y") if contract.exit_date else '',
        #                 'contract_name':contract.contract_id.name or ' ',
        #                 'contract_start_date':contract.contract_id.date_start.strftime("%d-%m-%Y") if contract.contract_id.date_start else ' ',
        #                 'contract_end_date':contract.contract_id.date_end.strftime("%d-%m-%Y") if contract.contract_id.date_end else '',
        #                 'status': state_display_name,
        #
        #             })
        #
        #
        #
        #             contract_lst.append(contract.employee_no)
        #
        #
        #     if len(contract_lst)==0:
        #         raise ValidationError("Employee is not there in this Date  Range")
        #
        #     data = {
        #         'form_data': self.read()[0],
        #         'selection': selection_list,
        #     }
        #     return self.env.ref('employee_details_report.action_employee_detail_pdf').with_context(landscape=True).report_action(self, data=data)
        #
        #

                       