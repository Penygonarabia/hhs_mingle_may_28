from odoo import http
from odoo.http import content_disposition, request
from odoo import fields, models, api, _
import io
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import ValidationError
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime

class PayrollExcelReportController(http.Controller):
    @http.route([
        '/om_hr_payroll/excel_report/<model("gosi.payroll"):wizard>',
    ], type='http', auth="user", csrf=False)

    def get_payroll_excel_report(self,wizard=None,**args):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Payroll Report in Excel Format' + '.xlsx'))
                    ]
                )
        # create workbook object from xlsxwriter library
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # create some style to set up the font type, the font size, the border, and the aligment
        title_style = workbook.add_format({'font_name': 'Times', 'font_size': 18, 'bold': True, 'align': 'center','color':'blue','bg_color': '#6B8E23'})
        header_style = workbook.add_format({'font_name': 'Times', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center','color':'orange'})
        text_style = workbook.add_format({'font_name': 'Times', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
        number_style = workbook.add_format({'font_name': 'Times', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
        total_style = workbook.add_format({'font_name':'Times','bold': True,'left':1,'bottom':1,'right':1,'top':1,'align':'right','bg_color':'0099FF'})
        gtotal_style=workbook.add_format({'font_name':'Times','bold': True,'left':1,'bottom':1,'right':1,'top':1,'font_size': 12,'align':'right','bg_color':'0033FF','color':'white'})
        department_heading_style=workbook.add_format({'font_name': 'Times', 'font_size': 12, 'bold': True, 'align': 'left','color':'blue'})
        basic_style=workbook.add_format({'font_name':'Times','font_size': 12,'left':1,'bold': True,'bottom':1,'right':1,'top':1,'align':'center','bg_color':'#008000','color':'white'})
        allow_style=workbook.add_format({'font_name':'Times','font_size': 12,'left':1,'bold': True,'bottom':1,'right':1,'top':1,'align':'center','bg_color':'#a52a2a','color':'white'})
        deduc_style=workbook.add_format({'font_name':'Times','font_size': 12,'left':1,'bold': True,'bottom':1,'right':1,'top':1,'align':'center','bg_color':'#000000','color':'white'})
        sheet = workbook.add_worksheet("Payroll Report of Employees")
        sheet.set_row(0 , 25)
        for user in wizard:
              # set the orientation to landscape
            sheet.set_landscape()
            # set up the paper size, 9 means A4
            sheet.set_paper(9)
            # set up the margin in inch
            sheet.set_margins(2,2,2,2)
            # set up the column width
            sheet.set_column('A:A',10)
            sheet.set_column('B:B',16)
            sheet.set_column('C:C',16)
            sheet.set_column('D:E',12)
            sheet.set_column('F:F',8)
            sheet.set_column('G:G',20)
            sheet.set_column('H:I',13)
            sheet.set_column('J:J',17)
            sheet.set_column('K:M',15)
            sheet.set_column('N:O',15)
            sheet.set_column('P:P',12)
            sheet.set_column('Q:Q',12)
            sheet.set_column('R:S',12)
            col=0
            sheet.write(4, col, 'S.No.', header_style)
            col += 1            
            sheet.write(4, col, 'Employee Number', header_style)
            col += 1
            sheet.write(4, col, 'Employee Name', header_style)
            col += 1
            sheet.write(4, col,'Reference No.',header_style)
            col += 1
            sheet.write(4, col, 'Job Title', header_style)
            col += 1
            sheet.write(4,col, 'Location', header_style)
            col += 1
            sheet.write(4, col, 'Department', header_style)
            col += 1
            sheet.write(4, col, 'Nationality', header_style)
            col += 1           
            row = 5
            number = 1
            # department_wise_dict=wizard._get_payslips()
            date_from = wizard.from_date
            date_to = wizard.to_date           
            date = datetime.strptime(str(date_from), "%Y-%m-%d")
            date_month=date.month
            date_year=date.year              
            sheet.write('A2','Start Date',header_style)
            sheet.write('B2',str(date_from), text_style)
            sheet.write('A3','End Date',header_style)
            sheet.write('B3',str(date_to), text_style)
            sheet.merge_range('A1:V1', 'Payroll Checklist ('+ str(date_month) + ' -  '+str(date_year) + ' )', title_style)
            allowance = []
            deduction = []
            col_lst = []      
            if wizard.department_ids and wizard.job_ids and wizard.from_date and wizard.to_date:
                employees = request.env['hr.employee'].search(['&',('department_id', '=',wizard.department_ids.ids),('job_id', '=',wizard.job_ids.ids)])
                all_department = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('date_from','=', wizard.from_date),('date_to','=', wizard.to_date),('struct_id','=',wizard.structure_id.id)])
                final_total_list = []              
                for dept in all_department:                
                    col = 0
                    sheet.write(row, col, number, text_style)    
                    col += 1      
                    sheet.write(row, col, dept.employee_id.employee_no or "", text_style)
                    col += 1
                    sheet.write(row, col, dept.employee_id.name or "", text_style)
                    col += 1
                    sheet.write(row, col, dept.number or "", text_style)
                    col += 1
                    sheet.write(row, col, dept.employee_id.job_title or "", text_style)
                    col += 1
                    sheet.write(row, col, dept.employee_id.branch_id.name or "", text_style)
                    col += 1
                    sheet.write(row, col, dept.employee_id.department_id.name or "", text_style)
                    col += 1
                    sheet.write(row, col, dept.employee_id.country_id.name or "", text_style)
                    col += 1                 
                    allowance = []
                    deduction = []
                    col_lst = []
                    for line in dept.line_ids:
                        if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                            if allowance:
                                flag = False
                                for alw in allowance:
                                    if alw['allowance_id'] == line.salary_rule_id.id:
                                       alw['employee_ids'].append({
                                            'payslip_id': dept.id,
                                            'employee_id': dept.employee_id.id,
                                            'total':line.total
                                           })
                                       flag = True
                                if not flag:
                                    allowance.append({
                                        'allowance_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':dept.id,
                                            'employee_id': dept.employee_id.id,
                                            'total':line.total
                                            }]
                                        })
                            else:
                                 allowance.append({
                                        'allowance_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':dept.id,
                                            'employee_id': dept.employee_id.id,
                                            'total':line.total
                                            }]
                                        })
                    
                        elif line.category_id.code == 'DED' or line.category_id.code == 'NET' or line.category_id.code == 'GROSS':
                            if deduction:
                                flag = False
                                for ded in deduction:
                                    if ded['deduction_id'] == line.salary_rule_id.id:
                                       ded['employee_ids'].append({
                                            'payslip_id': dept.id,
                                            'employee_id': dept.employee_id.id,
                                            'total':line.total
                                           })
                                       flag = True
                                if not flag:
                                    deduction.append({
                                        'deduction_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':dept.id,
                                            'employee_id': dept.employee_id.id,
                                            'total':line.total
                                            }]
                                        })                    
                            else:
                                 deduction.append({
                                        'deduction_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':dept.id,
                                            'employee_id': dept.employee_id.id,
                                            'total':line.total
                                            }]
                                        })                    
                    #Make sure that basic is First Line 
                    index = 0     
                    if allowance:
                        for alw in allowance:
                            if alw['name'] == 'BASIC' and index!=0:
                                first_index = allowance[0]
                                allowance[0] = alw
                                allowance[index] = first_index
                            index += 1
                    row_wise_total_list = []
                    value = 0.0
                    for alw in allowance:
                        value = 0.0
                        sheet.write(4, col, alw['name'], header_style)                        
                        for employee in alw['employee_ids']:                          
                            value= employee['total'] 
                            row_wise_total_list.append(value)
                            sheet.write(row, col, value, number_style)
                            col += 1                            
                    value = 0.0  
                    for ded in deduction:
                        value = 0.0 
                        sheet.write(4, col, ded['name'], header_style)                        
                        for employee in ded['employee_ids']:                         
                            value= employee['total'] 
                            row_wise_total_list.append(value)
                            sheet.write(row, col, value, number_style)
                            col+=1
                    final_total_list.append(row_wise_total_list)
                    row += 1
                    number += 1
                totals_list = []
                total_all_allowance = 0.0
                total_all_deduction = 0.0
                for alw in allowance:
                    total_same_allowance = 0.0
                    for employee in alw['employee_ids']:
                        total_same_allowance += employee['total']
                        total_all_allowance += employee['total']
                    totals_list.append({
                        'code': alw['name'],
                        'total': total_same_allowance
                    })
                for ded in deduction:
                    total_same_deduction = 0.0
                    for employee in ded['employee_ids']:
                        total_same_deduction += employee['total']
                        total_all_deduction += employee['total']
                    totals_list.append({
                        'code': ded['name'],
                        'total': total_same_deduction
                    })
                if final_total_list:                   
                    sheet.write(row, 7, 'Total', header_style)
                    col = 8
                    f_list = []
                    for r in range(len(final_total_list[0])):
                        value = 0
                        for v in final_total_list:
                            value += v[r]
                        f_list.append(value)
                    for total_line in f_list:
                        sheet.write(row, col, total_line, number_style)
                        col += 1  
            ##******Group Wise department***********************                                  
            elif wizard.group_wise == "department":
                department_ids = False
                if wizard.department_ids:
                    department_ids = wizard.department_ids
                else:
                    department_ids = request.env['hr.department'].search([])                
                final_total_list = []
                for department in department_ids:               
                    employees = request.env['hr.employee'].search([('department_id', '=',department.id)])
                    department_wise = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('number','!=',False),('date_from','=', wizard.from_date),('date_to','=', wizard.to_date),('struct_id','=',wizard.structure_id.id)])
                    if department_wise:
                        col = 0
                        row += 1                       
                        sheet.write(row, col, 'Department : '+ employees.department_id.name,  department_heading_style)    
                        row += 1
                        department_total_dict = []
                        for department in department_wise:                           
                            col = 0                       
                            sheet.write(row, col, number, text_style)    
                            col += 1              
                            sheet.write(row, col, department.employee_id.employee_no or "", text_style)
                            col += 1
                            sheet.write(row, col, department.employee_id.name or "", text_style)
                            col += 1
                            sheet.write(row, col, department.number or "", text_style)
                            col += 1
                            sheet.write(row, col, department.employee_id.job_title or "", text_style)
                            col += 1
                            sheet.write(row, col, department.employee_id.branch_id.name or "", text_style)
                            col += 1
                            sheet.write(row, col, department.employee_id.department_id.name or "", text_style)
                            col += 1
                            sheet.write(row, col, department.employee_id.country_id.name or "", text_style)
                            col += 1
                            allowance = []
                            deduction = []
                            for line in department.line_ids:
                                if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                    if allowance:
                                        flag = False
                                        for alw in allowance:
                                            if alw['allowance_id'] == line.salary_rule_id.id:
                                               alw['employee_ids'].append({
                                                    'payslip_id': department.id,
                                                    'employee_id': department.employee_id.id,
                                                    'total':line.total
                                                   })
                                               flag = True
                                        if not flag:
                                            allowance.append({
                                                'allowance_id' : line.salary_rule_id.id,
                                                'name':line.code,
                                                'employee_ids':[{
                                                    'payslip_id':department.id,
                                                    'employee_id': department.employee_id.id,
                                                    'total':line.total
                                                    }]
                                                })
                                    else:
                                         allowance.append({
                                                'allowance_id' : line.salary_rule_id.id,
                                                'name':line.code,
                                                'employee_ids':[{
                                                    'payslip_id':department.id,
                                                    'employee_id': department.employee_id.id,
                                                    'total':line.total
                                                    }]
                                                })                            
                                elif line.category_id.code == 'DED' or line.category_id.code == 'NET' or line.category_id.code == 'GROSS':
                                    if deduction:
                                        flag = False
                                        for ded in deduction:
                                            if ded['deduction_id'] == line.salary_rule_id.id:
                                               ded['employee_ids'].append({
                                                    'payslip_id': department.id,
                                                    'employee_id': department.employee_id.id,
                                                    'total':line.total
                                                   })
                                               flag = True
                                        if not flag:
                                            deduction.append({
                                                'deduction_id' : line.salary_rule_id.id,
                                                'name':line.code,
                                                'employee_ids':[{
                                                    'payslip_id':department.id,
                                                    'employee_id': department.employee_id.id,
                                                    'total':line.total
                                                    }]
                                                })                            
                                    else:
                                         deduction.append({
                                                'deduction_id' : line.salary_rule_id.id,
                                                'name':line.code,
                                                'employee_ids':[{
                                                    'payslip_id':department.id,
                                                    'employee_id': department.employee_id.id,
                                                    'total':line.total
                                                    }]
                                                })
                    #Make sure that basic is First Line 
                            index = 0     
                            if allowance:
                                for alw in allowance:
                                    if alw['name'] == 'BASIC' and index!=0:
                                        first_index = allowance[0]
                                        allowance[0] = alw
                                        allowance[index] = first_index
                                    index += 1                            
                            row_wise_total_list = []
                            value = 0.0
                            for alw in allowance:
                                value = 0.0
                                sheet.write(4, col, alw['name'], header_style)
                                for employee in alw['employee_ids']:
                                    value= employee['total'] 
                                    row_wise_total_list.append(value)
                                    sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                    col += 1
                            for ded in deduction:
                                value = 0.0                               
                                sheet.write(4, col, ded['name'], header_style)
                                for employee in ded['employee_ids']:
                                    value = employee['total']
                                    row_wise_total_list.append(value)
                                    sheet.write(row, col,('{:,.2f}'.format(abs(value))), number_style)
                                    col += 1
                            department_total_dict.append(row_wise_total_list)
                            final_total_list.append(row_wise_total_list)
                            row += 1
                            number+= 1
                        sheet.write(row, 7, 'Total', header_style)
                        col = 8
                        d_list = []
                        for dept in range(len(department_total_dict[0])):
                            value = 0
                            for v in range(0,len(department_total_dict)):
                                value+= department_total_dict[v][dept]
                            d_list.append(value)
                        for total_dept in d_list:
                            sheet.write(row, col, ('{:,.2f}'.format(abs(total_dept))), number_style)
                            col += 1
                row +=1
                sheet.write(row, 7, 'Grand Total', header_style)
                col = 8
                f_list = []
                r_list=[]
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in range(0,len(final_total_list)):
                        value+= final_total_list[v][r]
                    f_list.append(value)
                    r_list = f_list
                for total_li in r_list:
                    sheet.write(row, col,('{:,.2f}'.format(abs(total_li))) , number_style)
                    col += 1
                    total_line = 0
            #################  Jobwise Employee Report##################################################           
            elif wizard.group_wise == "jobtitle":
                job_ids = False
                if wizard.job_ids:
                    job_ids = wizard.job_ids
                else:
                   job_ids = request.env['hr.job'].search([])   
                final_total_list = []
                for jobs in job_ids:                   
                    employees = request.env['hr.employee'].search([('job_id', '=',jobs.id)])
                    job_wise = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('date_from','=', wizard.from_date),('date_to','=', wizard.to_date),('struct_id','=',wizard.structure_id.id)])    
                    if job_wise:
                        col = 0
                        row += 1
                        sheet.write(row, col, 'Job Name  : '+ jobs.name,  department_heading_style)                           
                        row += 1
                        job_total_dict = []
                        for job in job_wise:
                            for job_title in job:                         
                                col = 0
                                sheet.write(row, col, number, text_style)    
                                col += 1             
                                sheet.write(row, col, job_title.employee_id.employee_no or "", text_style)
                                col += 1
                                sheet.write(row, col, job_title.employee_id.name or "", text_style)
                                col += 1
                                sheet.write(row, col, job_title.number or "", text_style)
                                col += 1
                                sheet.write(row, col, job_title.employee_id.job_title or "", text_style)
                                col += 1
                                sheet.write(row, col, job_title.employee_id.branch_id.name or "", text_style)
                                col += 1
                                sheet.write(row, col, job_title.employee_id.department_id.name or "", text_style)
                                col += 1
                                sheet.write(row, col, job_title.employee_id.country_id.name or "", text_style)
                                col += 1
                                # row += 1
                                # number += 1
                                allowance = []
                                deduction = []
                                for line in job_title.line_ids:
                                    if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                        if allowance:
                                            flag = False
                                            for alw in allowance:
                                                if alw['allowance_id'] == line.salary_rule_id.id:
                                                   alw['employee_ids'].append({
                                                        'payslip_id': job_title.id,
                                                        'employee_id': job_title.employee_id.id,
                                                        'total':line.total
                                                       })
                                                   flag = True
                                            if not flag:
                                                allowance.append({
                                                    'allowance_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':job_title.id,
                                                        'employee_id': job_title.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })
                                        else:
                                             allowance.append({
                                                    'allowance_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':job_title.id,
                                                        'employee_id': job_title.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })                            
                                    elif line.category_id.code == 'DED' or line.category_id.code == 'NET' or line.category_id.code == 'GROSS':
                                        if deduction:
                                            flag = False
                                            for ded in deduction:
                                                if ded['deduction_id'] == line.salary_rule_id.id:
                                                   ded['employee_ids'].append({
                                                        'payslip_id': job_title.id,
                                                        'employee_id': job_title.employee_id.id,
                                                        'total':line.total
                                                       })
                                                   flag = True
                                            if not flag:
                                                deduction.append({
                                                    'deduction_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':job_title.id,
                                                        'employee_id': job_title.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })                            
                                        else:
                                             deduction.append({
                                                    'deduction_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':job_title.id,
                                                        'employee_id': job_title.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })                            
                            #Make sure that basic is First Line 
                            index=0     
                            if allowance:
                                for alw in allowance:
                                    if alw['name'] == 'BASIC' and index!=0:
                                        first_index = allowance[0]
                                        allowance[0] = alw
                                        allowance[index] = first_index
                                    index += 1                            
                            row_wise_total_list = []
                            value = 0.0
                            for alw in allowance:
                                value = 0.0
                                sheet.write(4, col, alw['name'], header_style)                                
                                for employee in alw['employee_ids']:
                                    if employee['employee_id']:                                  
                                        value= employee['total'] 
                                        row_wise_total_list.append(value)
                                      
                                        sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                        col += 1                            
                            value = 0.0  
                            for ded in deduction:
                                value = 0.0 
                                sheet.write(4, col, ded['name'], header_style)
                                for employee in ded['employee_ids']: 
                                    if employee['employee_id']:                               
                                        value= employee['total'] 
                                        row_wise_total_list.append(value)
                                        sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                        col += 1
                            job_total_dict.append(row_wise_total_list)
                            final_total_list.append(row_wise_total_list)
                            row += 1
                            number += 1
                        sheet.write(row, 7, 'Total', header_style)
                        col = 8
                        d_list = []
                        for dept in range(len(job_total_dict[0])):
                            value = 0
                            for v in range(0,len(job_total_dict)):
                                value+= job_total_dict[v][dept]
                            d_list.append(value)
                        for total_dept in d_list:
                            sheet.write(row, col, ('{:,.2f}'.format(abs(total_dept))), number_style)
                            col += 1
                            # f_list = [sum(i) for i in zip(*final_total_list)]
                            # print("............",str(f_list))
                            # for total_line in f_list:
                            #     sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), number_style)
                            #     col += 1
                row+=1
                sheet.write(row, 7, 'Grand Total', header_style)
                col = 8
                f_list = []
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in final_total_list:
                        value += v[r]
                    f_list.append(value)
                for total_line in f_list:
                    # total_line = 0
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), number_style)
                    col += 1  
                    total_line = 0
            ############## Nationality wise Employee #########################################
            elif wizard.group_wise == "nationality":
                nationality_ids = False
                if wizard.nationality_ids:
                    nationality_ids = wizard.nationality_ids
                else:
                   nationality_ids = request.env['res.country'].search([]) 
                final_total_list = []
                for nation in nationality_ids:                   
                    employees = request.env['hr.employee'].search([('country_id', '=',  nation.id)])
                    nationality = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('date_from','=', wizard.from_date),('date_to','=', wizard.to_date),('struct_id','=',wizard.structure_id.id)])
                    if nationality:
                        col = 0
                        row += 1
                        sheet.write(row, col, 'Nationality  : '+ nation.name,  department_heading_style)                        
                        row += 1
                        nation_total_list=[]   
                        for nation in nationality:                    
                            for nation_wise in nation:
                                col = 0
                                sheet.write(row, col, number, text_style)    
                                col += 1              
                                sheet.write(row, col, nation_wise.employee_id.employee_no or "", text_style)
                                col += 1
                                sheet.write(row, col, nation_wise.employee_id.name or "", text_style)
                                col += 1
                                sheet.write(row, col, nation_wise.number or "", text_style)
                                col += 1
                                sheet.write(row, col, nation_wise.employee_id.job_title or "", text_style)
                                col += 1
                                sheet.write(row, col, nation_wise.employee_id.branch_id.name or "", text_style)
                                col += 1
                                sheet.write(row, col, nation_wise.employee_id.department_id.name or "", text_style)
                                col += 1
                                sheet.write(row, col, nation_wise.employee_id.country_id.name or "", text_style)
                                col += 1
                                # row += 1
                                # number += 1
                                allowance = []
                                deduction = []
                                col_lst = []
                                for line in nation_wise.line_ids:
                                    if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                        if allowance:
                                            flag = False
                                            for alw in allowance:
                                                if alw['allowance_id'] == line.salary_rule_id.id:
                                                   alw['employee_ids'].append({
                                                        'payslip_id': nation_wise.id,
                                                        'employee_id': nation_wise.employee_id.id,
                                                        'total':line.total
                                                       })
                                                   flag = True
                                            if not flag:
                                                allowance.append({
                                                    'allowance_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':nation_wise.id,
                                                        'employee_id': nation_wise.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })
                                        else:
                                             allowance.append({
                                                    'allowance_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':nation_wise.id,
                                                        'employee_id': nation_wise.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })                            
                                    elif line.category_id.code == 'DED' or line.category_id.code == 'NET' or line.category_id.code == 'GROSS':
                                        if deduction:
                                            flag = False
                                            for ded in deduction:
                                                if ded['deduction_id'] == line.salary_rule_id.id:
                                                   ded['employee_ids'].append({
                                                        'payslip_id': nation_wise.id,
                                                        'employee_id': nation_wise.employee_id.id,
                                                        'total':line.total
                                                       })
                                                   flag = True
                                            if not flag:
                                                deduction.append({
                                                    'deduction_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':nation_wise.id,
                                                        'employee_id': nation_wise.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })                            
                                        else:
                                             deduction.append({
                                                    'deduction_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':nation_wise.id,
                                                        'employee_id': nation_wise.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })                            
                            #Make sure that basic is First Line 
                            index = 0     
                            if allowance:
                                for alw in allowance:
                                    if alw['name'] == 'BASIC' and index!=0:
                                        first_index = allowance[0]
                                        allowance[0] = alw
                                        allowance[index] = first_index
                                    index += 1
                            
                            row_wise_total_list = []
                            value = 0.0
                            for alw in allowance:
                                value = 0.0
                                sheet.write(4, col, alw['name'], header_style)
                                
                                for employee in alw['employee_ids']:
                                  
                                    value= employee['total'] 
                                    row_wise_total_list.append(value)
                                    sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                    col += 1                            
                            value = 0.0  
                            for ded in deduction:
                                value = 0.0 
                                sheet.write(4, col, ded['name'], header_style)                                
                                for employee in ded['employee_ids']:                                 
                                    value= employee['total'] 
                                    row_wise_total_list.append(value)
                                    sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                    col+=1
                            nation_total_list.append(row_wise_total_list)        
                            final_total_list.append(row_wise_total_list)
                            row += 1
                            number += 1
                        sheet.write(row, 7, 'Total', header_style)
                        col = 8
                        d_list = []
                        for dept in range(len(nation_total_list[0])):
                            value = 0
                            for v in range(0,len(nation_total_list)):
                                value+= nation_total_list[v][dept]
                            d_list.append(value)
                        for total_dept in d_list:
                            sheet.write(row, col, ('{:,.2f}'.format(abs(total_dept))), number_style)
                            col += 1
                row+=1        
                sheet.write(row, 7, 'Grand Total', header_style)
                col = 8
                f_list = []
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in final_total_list:
                        value += v[r]
                    f_list.append(value)
                for total_line in f_list:
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), number_style)
                    col += 1
                    total_line = 0
            ########### branch wise report ################################
            elif wizard.group_wise=="location":
                branch_ids = False
                if wizard.branch_ids:
                    branch_ids = wizard.branch_ids
                else:

                    branch_ids = request.env['hr.branch'].search([])  
                final_total_list = []    
                for branch in branch_ids:                   
                    employees = request.env['hr.employee'].search([('branch_id', '=',branch.id)])
                    location = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('date_from','=', wizard.from_date),('date_to','=', wizard.to_date),('struct_id','=',wizard.structure_id.id)])
                    if location:
                        col = 0
                        row += 1
                        sheet.write(row, col, 'Branch Name  : '+ branch.name,  department_heading_style)                                                
                        row += 1
                        location_total_list=[]   
                        for bran in location:
                            for branch_wise in bran:
                                col = 0
                                sheet.write(row, col, number, text_style)    
                                col += 1 
                                sheet.write(row, col, branch_wise.employee_id.employee_no or "", text_style)
                                col += 1
                                sheet.write(row, col, branch_wise.employee_id.name or "", text_style)
                                col += 1
                                sheet.write(row, col, branch_wise.number or "", text_style)
                                col += 1
                                sheet.write(row, col, branch_wise.employee_id.job_title or "", text_style)
                                col += 1
                                sheet.write(row, col, branch_wise.employee_id.branch_id.name or "", text_style)
                                col += 1
                                sheet.write(row, col, branch_wise.employee_id.department_id.name or "", text_style)
                                col += 1
                                sheet.write(row, col, branch_wise.employee_id.country_id.name or "", text_style)
                                col += 1
                                # row += 1
                                # number += 1
                                allowance = []
                                deduction = []
                                col_lst = []
                                for line in branch_wise.line_ids:
                                    if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                        if allowance:
                                            flag = False
                                            for alw in allowance:
                                                if alw['allowance_id'] == line.salary_rule_id.id:
                                                   alw['employee_ids'].append({
                                                        'payslip_id': branch_wise.id,
                                                        'employee_id': branch_wise.employee_id.id,
                                                        'total':line.total
                                                       })
                                                   flag = True
                                            if not flag:
                                                allowance.append({
                                                    'allowance_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':branch_wise.id,
                                                        'employee_id': branch_wise.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })
                                        else:
                                             allowance.append({
                                                    'allowance_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':branch_wise.id,
                                                        'employee_id': branch_wise.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })                            
                                    elif line.category_id.code == 'DED' or line.category_id.code == 'NET' or line.category_id.code == 'GROSS':
                                        if deduction:
                                            flag = False
                                            for ded in deduction:
                                                if ded['deduction_id'] == line.salary_rule_id.id:
                                                   ded['employee_ids'].append({
                                                        'payslip_id': branch_wise.id,
                                                        'employee_id': branch_wise.employee_id.id,
                                                        'total':line.total
                                                       })
                                                   flag = True
                                            if not flag:
                                                deduction.append({
                                                    'deduction_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':branch_wise.id,
                                                        'employee_id': branch_wise.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })                            
                                        else:
                                             deduction.append({
                                                    'deduction_id' : line.salary_rule_id.id,
                                                    'name':line.code,
                                                    'employee_ids':[{
                                                        'payslip_id':branch_wise.id,
                                                        'employee_id': branch_wise.employee_id.id,
                                                        'total':line.total
                                                        }]
                                                    })                            
                            #Make sure that basic is First Line 
                            index = 0     
                            if allowance:
                                for alw in allowance:
                                    if alw['name'] == 'BASIC' and index!=0:
                                        first_index = allowance[0]
                                        allowance[0] = alw
                                        allowance[index] = first_index
                                    index += 1
                            
                            row_wise_total_list = []
                            value = 0.0
                            for alw in allowance:
                                value = 0.0
                                sheet.write(4, col, alw['name'], header_style)
                                
                                for employee in alw['employee_ids']:
                                  
                                    value= employee['total'] 
                                    row_wise_total_list.append(value)
                                    sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                    col += 1                            
                            value = 0.0  
                            for ded in deduction:
                                value = 0.0 
                                sheet.write(4, col, ded['name'], header_style)                                
                                for employee in ded['employee_ids']:                                 
                                    value= employee['total'] 
                                    row_wise_total_list.append(value)
                                    sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                    col+=1
                            location_total_list.append(row_wise_total_list)       
                            final_total_list.append(row_wise_total_list)
                            row += 1
                            number+= 1
                        sheet.write(row, 7, 'Total', header_style)
                        col = 8
                        f_list = []
                        for r in range(len(location_total_list[0])):
                            value = 0
                            for v in location_total_list:
                                value += v[r]
                            f_list.append(value)
                        for total_line in f_list:
                            sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), number_style)
                            col += 1
                row+=1
                sheet.write(row, 7, 'Grand Total', header_style)
                col = 8
                f_list = []
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in final_total_list:
                        value += v[r]
                    f_list.append(value)
                for total_line in f_list:
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), number_style)
                    col += 1 
                    total_line = 0
            ################# Employee Wise Report #####################################
            elif wizard.employ_ids and wizard.from_date and wizard.to_date:      
                employ = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',wizard.employ_ids.ids),('date_from','=', wizard.from_date),('date_to','=', wizard.to_date),('struct_id','=',wizard.structure_id.id)])                         
               
                final_total_list = []
                for emp in  employ: 
                    col = 0
                    sheet.write(row, col, number, text_style)
                    col += 1             
                    sheet.write(row, col, emp.employee_id.employee_no or "", text_style)
                    col += 1
                    sheet.write(row, col, emp.employee_id.name or "", text_style)
                    col += 1
                    sheet.write(row, col, emp.number or "", text_style)
                    col += 1
                    sheet.write(row, col, emp.employee_id.job_title or "", text_style)
                    col += 1
                    sheet.write(row, col, emp.employee_id.branch_id.name or "", text_style)
                    col += 1
                    sheet.write(row, col, emp.employee_id.department_id.name or "", text_style)
                    col += 1
                    sheet.write(row, col, emp.employee_id.country_id.name or "", text_style)
                    col += 1 
                    # row += 1
                    # number += 1
                    allowance = []
                    deduction = []
                    col_lst = []
                    for line in emp.line_ids:
                        if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                            if allowance:
                                flag = False
                                for alw in allowance:
                                    if alw['allowance_id'] == line.salary_rule_id.id:
                                       alw['employee_ids'].append({
                                            'payslip_id': emp.id,
                                            'employee_id': emp.employee_id.id,
                                            'total':line.total
                                           })
                                       flag = True
                                if not flag:
                                    allowance.append({
                                        'allowance_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':emp.id,
                                            'employee_id': emp.employee_id.id,
                                            'total':line.total
                                            }]
                                        })
                            else:
                                 allowance.append({
                                        'allowance_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':emp.id,
                                            'employee_id': emp.employee_id.id,
                                            'total':line.total
                                            }]
                                        })                    
                        elif line.category_id.code == 'DED' or line.category_id.code == 'NET' or line.category_id.code == 'GROSS':
                            if deduction:
                                flag = False
                                for ded in deduction:
                                    if ded['deduction_id'] == line.salary_rule_id.id:
                                       ded['employee_ids'].append({
                                            'payslip_id': emp.id,
                                            'employee_id': emp.employee_id.id,
                                            'total':line.total
                                           })
                                       flag = True
                                if not flag:
                                    deduction.append({
                                        'deduction_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':emp.id,
                                            'employee_id': emp.employee_id.id,
                                            'total':line.total
                                            }]
                                        })                    
                            else:
                                 deduction.append({
                                        'deduction_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':emp.id,
                                            'employee_id': emp.employee_id.id,
                                            'total':line.total
                                            }]
                                        })                    
                    #Make sure that basic is First Line 
                    index = 0     
                    if allowance:
                        for alw in allowance:
                            if alw['name'] == 'BASIC' and index!=0:
                                first_index = allowance[0]
                                allowance[0] = alw
                                allowance[index] = first_index
                            index += 1                    
                    row_wise_total_list = []
                    value = 0.0
                    for alw in allowance:
                        value = 0.0
                        sheet.write(4, col, alw['name'], header_style)                        
                        for employee in alw['employee_ids']:                          
                            value= employee['total'] 
                            row_wise_total_list.append(value)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                            col += 1                            
                    value = 0.0  
                    for ded in deduction:
                        value = 0.0 
                        sheet.write(4, col, ded['name'], header_style)                        
                        for employee in ded['employee_ids']:                         
                            value= employee['total'] 
                            row_wise_total_list.append(value)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                            col += 1
                    final_total_list.append(row_wise_total_list)
                    row += 1
                    number += 1
                if final_total_list:                   
                    sheet.write(row, 7, 'Total', header_style)
                    col = 8
                    f_list = []
                    for r in range(len(final_total_list[0])):
                        value = 0
                        for v in final_total_list:
                            value += v[r]
                        f_list.append(value)
                    for total_line in f_list:
                        sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), number_style)
                        col += 1                           
                ############## Summary list *******************************************     
            elif((wizard.department_ids or wizard.job_ids  or wizard.nationality_ids or wizard.branch_ids or wizard.employ_ids) and wizard.from_date and wizard.to_date):
                employees = request.env['hr.employee'].search(['|','|','|',('department_id', '=',wizard.department_ids.ids),('job_id', '=',wizard.job_ids.ids),('country_id', '=',wizard.nationality_ids.ids),('branch_id', '=',wizard.branch_ids.ids)])
                final_total_list = []
                col = 0            
                code_lst = []
                all_dept = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids or wizard.employ_ids.ids),('date_from','=', wizard.from_date),('date_to','=', wizard.to_date),('struct_id','=',wizard.structure_id.id)])
                for dept in all_dept:            
                    for al_dept in dept:            
                        col = 0
                        sheet.write(row, col, number, text_style)    
                        col += 1   
                        sheet.write(row, col, al_dept.employee_id.employee_no or "", text_style)            
                        col += 1
                        sheet.write(row, col, al_dept.employee_id.name or "", text_style)
                        col += 1
                        sheet.write(row, col, al_dept.number or "", text_style)
                        col += 1
                        sheet.write(row, col, al_dept.employee_id.job_title or "", text_style)
                        col += 1
                        sheet.write(row, col, al_dept.employee_id.branch_id.name or "", text_style)
                        col += 1
                        sheet.write(row, col, al_dept.employee_id.department_id.name or "", text_style)
                        col += 1
                        sheet.write(row, col, al_dept.employee_id.country_id.name or "", text_style)
                        col += 1                    
                        allowance = []
                        deduction = []
                        col_lst = []
                        for line in al_dept.line_ids:
                            if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                if allowance:
                                    flag = False
                                    for alw in allowance:
                                        if alw['allowance_id'] == line.salary_rule_id.id:
                                           alw['employee_ids'].append({
                                                'payslip_id': al_dept.id,
                                                'employee_id': al_dept.employee_id.id,
                                                'total':line.total
                                               })
                                           flag = True
                                    if not flag:
                                        allowance.append({
                                            'allowance_id' : line.salary_rule_id.id,
                                            'name':line.code,
                                            'employee_ids':[{
                                                'payslip_id':al_dept.id,
                                                'employee_id': al_dept.employee_id.id,
                                                'total':line.total
                                                }]
                                            })
                                else:
                                     allowance.append({
                                            'allowance_id' : line.salary_rule_id.id,
                                            'name':line.code,
                                            'employee_ids':[{
                                                'payslip_id':al_dept.id,
                                                'employee_id': al_dept.employee_id.id,
                                                'total':line.total
                                                }]
                                            })                        
                            elif line.category_id.code == 'DED' or line.category_id.code == 'NET' or line.category_id.code == 'GROSS':
                                if deduction:
                                    flag = False
                                    for ded in deduction:
                                        if ded['deduction_id'] == line.salary_rule_id.id:
                                           ded['employee_ids'].append({
                                                'payslip_id': al_dept.id,
                                                'employee_id': al_dept.employee_id.id,
                                                'total':line.total
                                               })
                                           flag = True
                                    if not flag:
                                        deduction.append({
                                            'deduction_id' : line.salary_rule_id.id,
                                            'name':line.code,
                                            'employee_ids':[{
                                                'payslip_id':al_dept.id,
                                                'employee_id': al_dept.employee_id.id,
                                                'total':line.total
                                                }]
                                            })                        
                                else:
                                     deduction.append({
                                            'deduction_id' : line.salary_rule_id.id,
                                            'name':line.code,
                                            'employee_ids':[{
                                                'payslip_id':al_dept.id,
                                                'employee_id': al_dept.employee_id.id,
                                                'total':line.total
                                                }]
                                            })                        
                        #Make sure that basic is First Line 
                        index = 0     
                        if allowance:
                            for alw in allowance:
                                if alw['name'] == 'BASIC' and index!=0:
                                    first_index = allowance[0]
                                    allowance[0] = alw
                                    allowance[index] = first_index
                                index += 1
                        row_wise_total_list = []
                        value = 0.0
                        for alw in allowance:
                            value = 0.0
                            sheet.write(4, col, alw['name'], header_style)                            
                            for employee in alw['employee_ids']:                              
                                value= employee['total']  
                                row_wise_total_list.append(value)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                col += 1
                        value = 0.0                                
                        for ded in deduction:
                            value = 0.0 
                            sheet.write(4, col, ded['name'], header_style)                            
                            for employee in ded['employee_ids']:                             
                                value= employee['total'] 
                                row_wise_total_list.append(value)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                col+=1
                        final_total_list.append(row_wise_total_list)
                        row += 1
                        number += 1                                  
                         
                    if final_total_list:                       
                        sheet.write(row, 7, 'Total', header_style)
                        col = 8
                        f_list = []
                        for r in range(len(final_total_list[0])):
                            value = 0
                            for v in final_total_list:
                                value += v[r]
                            f_list.append(value)
                        for total_line in f_list:
                            sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), number_style)
                            col += 1 
            ######### ** Date Wise Report ****************                                         
            elif wizard.from_date and wizard.to_date:    
                payslip_date_wise = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('date_from','>=', wizard.from_date),('date_to','<=', wizard.to_date),('struct_id','=',wizard.structure_id.id)],order="name ASC")
                final_total_list = []
                for payslip in payslip_date_wise:
                    col = 0
                    sheet.write(row, col, number, text_style)
                    col += 1
                    sheet.write(row, col, payslip.employee_id.employee_no or "", text_style)
                    col += 1    
                    sheet.write(row, col, payslip.employee_id.name or "", text_style)
                    col += 1
                    sheet.write(row, col, payslip.number or "", text_style)
                    col += 1
                    sheet.write(row, col, payslip.employee_id.job_title or "", text_style)
                    col += 1
                    sheet.write(row, col, payslip.employee_id.branch_id.name or "", text_style)
                    col += 1
                    sheet.write(row, col, payslip.employee_id.department_id.name or "", text_style)
                    col += 1
                    sheet.write(row, col, payslip.employee_id.country_id.name or "", text_style)
                    col += 1
                    allowance = []
                    deduction = []
                    col_lst = []
                    for line in payslip.line_ids:
                        if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                            if allowance:
                                flag = False
                                for alw in allowance:
                                    if alw['allowance_id'] == line.salary_rule_id.id:
                                       alw['employee_ids'].append({
                                            'payslip_id': payslip.id,
                                            'employee_id': payslip.employee_id.id,
                                            'total':line.total
                                           })
                                       flag = True
                                if not flag:
                                    allowance.append({
                                        'allowance_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':payslip.id,
                                            'employee_id': payslip.employee_id.id,
                                            'total':line.total
                                            }]
                                        })
                            else:
                                 allowance.append({
                                        'allowance_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':payslip.id,
                                            'employee_id': payslip.employee_id.id,
                                            'total':line.total
                                            }]
                                        })                    
                        elif line.category_id.code == 'DED' or line.category_id.code == 'NET' or line.category_id.code == 'GROSS':
                            if deduction:
                                flag = False
                                for ded in deduction:
                                    if ded['deduction_id'] == line.salary_rule_id.id:
                                       ded['employee_ids'].append({
                                            'payslip_id': payslip.id,
                                            'employee_id': payslip.employee_id.id,
                                            'total':line.total
                                           })
                                       flag = True
                                if not flag:
                                    deduction.append({
                                        'deduction_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':payslip.id,
                                            'employee_id': payslip.employee_id.id,
                                            'total':line.total
                                            }]
                                        })                    
                            else:
                                 deduction.append({
                                        'deduction_id' : line.salary_rule_id.id,
                                        'name':line.code,
                                        'employee_ids':[{
                                            'payslip_id':payslip.id,
                                            'employee_id': payslip.employee_id.id,
                                            'total':line.total
                                            }]
                                        })                    
                    #Make sure that basic is First Line 
                    index = 0     
                    if allowance:
                        for alw in allowance:
                            if alw['name'] == 'BASIC' and index!=0:
                                first_index = allowance[0]
                                allowance[0] = alw
                                allowance[index] = first_index
                            index += 1
                    row_wise_total_list = []
                    value = 0.0
                    for alw in allowance:
                        sheet.write(4, col, alw['name'], header_style)
                        for employee in alw['employee_ids']:
                            value= employee['total']
                            row_wise_total_list.append(value)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                            col += 1
                    value = 0.0
                    for ded in deduction:
                        sheet.write(4, col, ded['name'], header_style)
                        for employee in ded['employee_ids']:
                            value = employee['total']
                            row_wise_total_list.append(value)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                            col+=1
                    final_total_list.append(row_wise_total_list)
                    row += 1
                    number+= 1
                """ After getting all employees row details """
                if final_total_list:
                    sheet.write(row, 7, 'Total', header_style)
                    col = 8
                    f_list = []
                    for r in range(len(final_total_list[0])):
                        value = 0
                        for v in final_total_list:
                            value += v[r]
                        f_list.append(value)
                    for total_line in f_list:
                        sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), number_style)
                        col += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
        return response
  
       