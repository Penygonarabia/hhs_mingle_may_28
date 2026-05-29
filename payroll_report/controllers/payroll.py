from odoo import http
from odoo.http import content_disposition, request
from odoo import fields, models, api, _
import io
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import ValidationError
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime

class PayrollExcelReptController(http.Controller):
    @http.route([
        '/om_hr_payroll/excel_report/<model("gosi.payroll"):wizard>',
    ], type='http', auth="user", csrf=False)

    def get_payroll_ex_report(self,wizard=None,**args):
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
        title_style = workbook.add_format({'font_name': 'Times', 'font_size': 18, 'bold': True, 'align': 'center','color':'white','bg_color': '#00008B'})
        header_style = workbook.add_format({'font_name': 'Times', 'bold': True,  'align': 'center','color':'black'})
        text_style = workbook.add_format({'font_name': 'Times', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
        gtotal_style=workbook.add_format({'font_name':'Times','bold': True,'left':1,'bottom':1,'right':1,'top':1,'font_size': 12,'align':'right','bg_color':'0033FF','color':'white'})
        department_heading_style=workbook.add_format({'font_name': 'Times', 'font_size': 14, 'bold': True, 'align': 'left','color':'black'})
        
        basic_style=workbook.add_format({'font_name':'Times','font_size': 12,'left':1,'bold': True,'bottom':1,'right':1,'top':1,'align':'center','bg_color':'#F2D7D5','color':'black'})
        allow_style=workbook.add_format({'font_name':'Times','font_size': 12,'left':1,'bold': True,'bottom':1,'right':1,'top':1,'align':'center','bg_color':'#87CEFA','color':'black'})
        deduc_style=workbook.add_format({'font_name':'Times','font_size': 12,'left':1,'bold': True,'bottom':1,'right':1,'top':1,'align':'center','bg_color':'#B7950B','color':'white'})
        other_style=workbook.add_format({'font_name':'Times','font_size': 12,'bold': True,'align':'center'})

        gross_pay_style=workbook.add_format({'font_name':'Times','font_size':12,'bold':True,'align':'center','bg_color':'#2E86C1','color':'white'})    
        net_pay_style=workbook.add_format({'font_name':'Times','font_size':12,'bold':True,'align':'center','bg_color':'#2ECC71','color':'white'})    

        total_style = workbook.add_format({'font_name':'Times','bold': True,'left':1,'bottom':1,'right':1,'top':1,'align':'center','bg_color':'#B22222','color':'white'})
        total_number_style = workbook.add_format({'font_name':'Times','bold': True,'left':1,'bottom':1,'right':1,'top':1,'align':'right','color':'black'})
        number_style = workbook.add_format({'font_name': 'Times', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})

        sheet = workbook.add_worksheet("Payroll Report of Employees")
        sheet.set_row(0, 25)
        
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
            sheet.set_column('C:C',30)
            sheet.set_column('D:D',12)
            sheet.set_column('E:E',35)
            sheet.set_column('F:F',8)
            sheet.set_column('G:G',20)
            sheet.set_column('H:I',13)
            sheet.set_column('J:J',25)
            sheet.set_column('K:M',15)
            sheet.set_column('N:N',16)
            sheet.set_column('O:O',15)
            sheet.set_column('P:P',20)
            sheet.set_column('Q:Q',15)
            sheet.set_column('R:S',10)
            # sheet.set_column('T:T',30)
            col=0
            sheet.write(4, col, 'S.No.',basic_style)
            col+=1
            sheet.write(4, col, 'Employee Number',basic_style)
            col+=1
            sheet.write(4, col, 'Employee Name', basic_style)
            col+=1
            sheet.write(4, col,'Reference No.',basic_style)
            col+=1
            sheet.write(4, col, 'Job Title', basic_style)
            col+=1
            sheet.write(4,col, 'Location', basic_style)
            col+=1
            sheet.write(4, col, 'Department',basic_style)
            col+=1
            sheet.write(4, col, 'Nationality', basic_style)
            col+=1          
            row = 5
            number = 1
            
            date = datetime.strptime(str(wizard.from_date), "%Y-%m-%d")
            date_month=date.month
            date_year=date.year
               
            sheet.write('A2','Start Date',header_style)
            sheet.write('B2',str(wizard.from_date), text_style)
            sheet.write('A3','End Date',header_style)
            sheet.write('B3',str(wizard.to_date), text_style)        
                   
            sheet.merge_range('A1:Z1', 'Payroll Checklist ('+ str(date_month) + ' -  '+str(date_year) + ' )', title_style)
            sheet.merge_range('A4:H4', 'Basic Info', basic_style)
            sheet.merge_range('I4:T4', 'Allowance',  allow_style)
            sheet.merge_range('V4:Y4', 'Deduction',  deduc_style)
            
            if wizard.department_ids and wizard.job_ids and wizard.from_date and wizard.to_date:
                employees = request.env['hr.employee'].search(['&',('department_id', '=',wizard.department_ids.ids),('job_id', '=',wizard.job_ids.ids)])
                all_department = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('date_from','>=', wizard.from_date),('date_to','<=', wizard.to_date),('struct_id','=',wizard.structure_id.id)],order="name ASC")
                final_total_list = []
                dept_lst = []              
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
                    deduct=0.0
                    dedu=0.0
                    total=0.0
                    value=0.0
                    allowan=0.0
                    tota_emp=0.0
                    total_ded = 0.0
                    net_total = 0.0
                    gross_total = 0.0
                    total_allowance = 0.0
                    for line in dept.line_ids:
                        if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                            if line.sequence <= 11 :
                                allowan =line.total
                                total_allowance += allowan
                                allowance.append(allowan)
                                sheet.write(4,col,line.name,allow_style)
                                sheet.set_column(4,col,len(line.name))
                                sheet.write(row, col, ('{:,.2f}'.format(abs(allowan))), number_style)
                                col+=1
                            if line.sequence > 11:
                                value+=line.total
                    allowance.append(value)
                    sheet.write(4,col,'Other Transaction',allow_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                    col+=1
                    gross_total = total_allowance + value
                    allowance.append(gross_total)
                    sheet.write(4, col, 'Gross Salary', gross_pay_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(gross_total))), number_style)
                    col += 1
                    for line in dept.line_ids:
                        if line.code =="GOSI":
                            deduct =line.total
                            allowance.append(deduct)
                            sheet.write(4,col,'GOSI',deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                            col += 1
                        if line.code=="Loan":
                            deduct =line.total
                            allowance.append(deduct)
                            sheet.write(4,col,'Loan',deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                            col += 1
                    # final_total_list.append(allowance)        
                    for line in dept.line_ids:
                        if line.category_id.code == 'DED':
                            if line.sequence >=1:
                                total_ded += line.total
                                if line.code == "GOSI":
                                    deduct = line.total
                                if line.code == "Loan":
                                    dedu = line.total
                                total_emp = total_ded - (deduct + dedu)
                    allowance.append(total_emp)
                    allowance.append(total_ded)
                    sheet.write(4, col, 'Others', deduc_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_emp))), number_style)
                    col += 1
                    sheet.write(4, col, 'Total Deductions ', deduc_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_ded))), number_style)
                    col += 1    
                    net_total = gross_total + total_ded
                    allowance.append(net_total)
                    sheet.write(4,col,'Net Salary',net_pay_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(net_total))), number_style)
                    col += 1         
                    final_total_list.append(allowance)
                    dept_lst.append(dept.employee_id.name)            
                    row += 1
                    number+= 1
                sheet.write(row, 7, 'Total',total_style)
                col=8
                f_list = []
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in range(0,len(final_total_list)):
                        if r < len(final_total_list[v]):
                            value += final_total_list[v][r]
                        else:
                            print(f"Index {r} out of range in sublist {v}")
                                
                    f_list.append(value)
                for total_line in f_list:
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), total_number_style)
                    col += 1
                
                if len(dept_lst)==0:
                    raise ValidationError("Payroll of the employee is not there in this Range")
           
            elif wizard.group_wise == "department":
                department_ids = False
                if wizard.department_ids:
                    department_ids = wizard.department_ids
                else:
                    department_ids = request.env['hr.department'].search([])                
                final_total_list = []
                dept_group = []
                for department in department_ids:               
                    employees = request.env['hr.employee'].search([('department_id', '=',department.id)])
                    department_wise = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('number','!=',False),('date_from','>=', wizard.from_date),('date_to','<=', wizard.to_date),('struct_id','=',wizard.structure_id.id)],order="name ASC")
                    if department_wise:
                        col = 0
                        # row += 1                       
                        sheet.write(row, col, employees.department_id.name,  department_heading_style)    
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
                            deduct=0.0
                            dedu=0.0
                            total=0.0
                            value=0.0
                            allowan=0.0
                            tota_emp=0.0
                            total_ded = 0.0
                            net_total = 0.0
                            gross_total = 0.0
                            total_allowance = 0.0
                            for line in department.line_ids:
                                if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                    if line.sequence <= 11 :
                                        allowan =line.total
                                        total_allowance += allowan
                                        allowance.append(allowan)
                                        sheet.write(4,col,line.name,allow_style)
                                        # sheet.set_column(4,col,len(line.name))
                                        sheet.write(row, col, ('{:,.2f}'.format(abs(allowan))), number_style)
                                        col+=1
                                    if line.sequence > 11:
                                        value+=line.total
                            allowance.append(value)
                            sheet.write(4,col,'Other Transaction',allow_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                            col+=1
                            gross_total = total_allowance + value
                            allowance.append(gross_total)
                            sheet.write(4, col, 'Gross Salary', gross_pay_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(gross_total))), number_style)
                            col += 1
                            for line in department.line_ids:
                                if line.code =="GOSI":
                                    deduct =line.total
                                    allowance.append(deduct)
                                    sheet.write(4,col,'GOSI',deduc_style)
                                    sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                                    col += 1
                                if line.code=="Loan":
                                    deduct =line.total
                                    allowance.append(deduct)
                                    sheet.write(4,col,'Loan',deduc_style)
                                    sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                                    col += 1
                        # final_total_list.append(allowance)        
                            for line in department.line_ids:
                                if line.category_id.code == 'DED':
                                    if line.sequence >=1:
                                        total_ded += line.total
                                        if line.code == "GOSI":
                                            deduct = line.total
                                        if line.code == "Loan":
                                            dedu = line.total
                                        total_emp = total_ded - (deduct + dedu)
                            allowance.append(total_emp)
                            allowance.append(total_ded)
                            sheet.write(4, col, 'Others', deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(total_emp))), number_style)
                            col += 1
                            sheet.write(4, col, 'Total Deductions ', deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(total_ded))), number_style)
                            col += 1 
                            net_total = gross_total + total_ded
                            allowance.append(net_total)
                            sheet.write(4,col,'Net Salary',net_pay_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(net_total))), number_style)
                            col += 1    
                            final_total_list.append(allowance)  
                            department_total_dict.append(allowance)
                            dept_group.append(department.employee_id.name)
                            row += 1
                            number+= 1
                        sheet.write(row, 7, 'Sub Total', total_style)
                        col = 8
                        d_list = []
                        for dept in range(len(department_total_dict[0])):
                            value = 0
                            for v in range(0,len(department_total_dict)):
                                value+= department_total_dict[v][dept]
                            d_list.append(value)
                        for total_dept in d_list:
                            sheet.write(row, col, ('{:,.2f}'.format(abs(total_dept))), total_number_style)
                            col += 1
                row +=1
                sheet.write(row, 7, 'Grand Total', total_style)
                col = 8
                f_list = []
                r_list=[]
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in range(0,len(final_total_list)):
                        if r < len(final_total_list[v]):
                            value += final_total_list[v][r]
                        else:
                            print(f"Index {r} out of range in sublist {v}")
                                
                    f_list.append(value)
                    r_list = f_list
                for total_li in r_list:
                    sheet.write(row, col,('{:,.2f}'.format(abs(total_li))) , total_number_style)
                    col += 1
                
                if len(dept_group)==0:
                    raise ValidationError("Departmentwise group by employees is not there in this range")
           
            elif wizard.group_wise == "jobtitle":
                job_ids = False
                if wizard.job_ids:
                    job_ids = wizard.job_ids
                else:
                   job_ids = request.env['hr.job'].search([])   
                final_total_list = []
                job_group_lst = []
                for jobs in job_ids:                   
                    employees = request.env['hr.employee'].search([('job_id', '=',jobs.id)])
                    job_wise = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('date_from','>=', wizard.from_date),('date_to','<=', wizard.to_date),('struct_id','=',wizard.structure_id.id)],order="name ASC")    
                    if job_wise:
                        col = 0
                        # row += 1
                        sheet.write(row, col, jobs.name,  department_heading_style)                           
                        row += 1
                        department_total_dict = []
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
                                allowance = []
                                deduction = []
                                deduct=0.0
                                dedu=0.0
                                total=0.0
                                value=0.0
                                allowan=0.0
                                tota_emp=0.0
                                total_ded = 0.0
                                net_total = 0.0
                                gross_total = 0.0
                                total_allowance = 0.0
                                for line in job_title.line_ids:
                                    if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                        if line.sequence <= 11 :
                                            allowan =line.total
                                            total_allowance += allowan
                                            allowance.append(allowan)
                                            sheet.write(4,col,line.name,allow_style)
                                            sheet.write(row, col, ('{:,.2f}'.format(abs(allowan))), number_style)
                                            col+=1
                                        if line.sequence > 11:
                                            value+=line.total
                                allowance.append(value)
                                sheet.write(4,col,'Other Transaction',allow_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                col+=1
                                gross_total = total_allowance + value
                                allowance.append(gross_total)
                                sheet.write(4, col, 'Gross Salary', gross_pay_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(gross_total))), number_style)
                                col += 1
                                for line in job_title.line_ids:
                                    if line.code =="GOSI":
                                        deduct =line.total
                                        allowance.append(deduct)
                                        sheet.write(4,col,'GOSI',deduc_style)
                                        sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                                        col += 1
                                    if line.code=="Loan":
                                        deduct =line.total
                                        allowance.append(deduct)
                                        sheet.write(4,col,'Loan',deduc_style)
                                        sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                                        col += 1
                                # final_total_list.append(allowance)        
                                for line in job_title.line_ids:
                                    if line.category_id.code == 'DED':
                                        if line.sequence >=1:
                                            total_ded += line.total
                                            if line.code == "GOSI":
                                                deduct = line.total
                                            if line.code == "Loan":
                                                dedu = line.total
                                            total_emp = total_ded - (deduct + dedu)
                                allowance.append(total_emp)
                                allowance.append(total_ded)
                                sheet.write(4, col, 'Others', deduc_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(total_emp))), number_style)
                                col += 1
                                sheet.write(4, col, 'Total Deductions ', deduc_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(total_ded))), number_style)
                                col += 1 
                                # final_total_list.append(allowance)        
                                net_total = gross_total + total_ded
                                allowance.append(net_total)
                                sheet.write(4,col,'Net Salary',net_pay_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(net_total))), number_style)
                                col += 1
                                final_total_list.append(allowance)  
                                department_total_dict.append(allowance)
                                job_group_lst.append(job_title.employee_id.name)
                                row += 1
                                number+= 1
                            sheet.write(row, 7, ' Sub Total', total_style)
                            col = 8
                            d_list = []
                            for dept in range(len(department_total_dict[0])):
                                value = 0
                                for v in range(0,len(department_total_dict)):
                                    value+= department_total_dict[v][dept]
                                d_list.append(value)
                            for total_dept in d_list:
                                sheet.write(row, col, ('{:,.2f}'.format(abs(total_dept))), total_number_style)
                                col += 1
                row +=1
                sheet.write(row, 7, 'Grand Total', total_style)
                col = 8
                f_list = []
                r_list=[]
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in range(0,len(final_total_list)):
                        if r < len(final_total_list[v]):
                            value += final_total_list[v][r]
                        else:
                            print(f"Index {r} out of range in sublist {v}")
                                
                    f_list.append(value)
                    r_list = f_list
                for total_li in r_list:
                    sheet.write(row, col,('{:,.2f}'.format(abs(total_li))) , total_number_style)
                    col += 1
                
                if len(job_group_lst) ==0:
                    raise ValidationError("Job wise Employee Payroll is not there in this range")
                
            elif wizard.group_wise == "nationality":
                nationality_ids = False
                if wizard.nationality_ids:
                    nationality_ids = wizard.nationality_ids
                else:
                   nationality_ids = request.env['res.country'].search([]) 
                final_total_list = []
                nation_group_lst = []
                for nation in nationality_ids:                   
                    employees = request.env['hr.employee'].search([('country_id', '=',  nation.id)])
                    nationality = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('date_from','>=', wizard.from_date),('date_to','<=', wizard.to_date),('struct_id','=',wizard.structure_id.id)],order="name ASC")
                    if nationality:
                        col = 0
                        # row += 1
                        sheet.write(row, col, nation.name,  department_heading_style)                        
                        row += 1
                        department_total_dict=[]   
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
                                allowance = []
                                deduction = []
                                deduct=0.0
                                dedu=0.0
                                total=0.0
                                value=0.0
                                allowan=0.0
                                tota_emp=0.0
                                total_ded = 0.0
                                net_total = 0.0
                                gross_total = 0.0
                                total_allowance = 0.0
                                for line in nation_wise.line_ids:
                                    if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                        if line.sequence <= 11 :
                                            allowan =line.total
                                            total_allowance += allowan
                                            allowance.append(allowan)
                                            sheet.write(4,col,line.name,allow_style)
                                            sheet.write(row, col, ('{:,.2f}'.format(abs(allowan))), number_style)
                                            col+=1
                                        if line.sequence > 11:
                                            value+=line.total
                                allowance.append(value)
                                sheet.write(4,col,'Other Transaction',allow_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                col+=1
                                gross_total = total_allowance + value
                                allowance.append(gross_total)
                                sheet.write(4, col, 'Gross Salary', gross_pay_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(gross_total))), number_style)
                                col += 1
                                for line in nation_wise.line_ids:
                                    if line.code =="GOSI":
                                        deduct =line.total
                                        allowance.append(deduct)
                                        sheet.write(4,col,'GOSI',deduc_style)
                                        sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                                        col += 1
                                    if line.code=="Loan":
                                        deduct =line.total
                                        allowance.append(deduct)
                                        sheet.write(4,col,'Loan',deduc_style)
                                        sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                                        col += 1
                                for line in nation_wise.line_ids:
                                    if line.category_id.code == 'DED':
                                        if line.sequence >=1:
                                            total_ded += line.total
                                            if line.code == "GOSI":
                                                deduct = line.total
                                            if line.code == "Loan":
                                                dedu = line.total
                                            total_emp = total_ded - (deduct + dedu)
                                allowance.append(total_emp)
                                allowance.append(total_ded)
                                sheet.write(4, col, 'Others', deduc_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(total_emp))), number_style)
                                col += 1
                                sheet.write(4, col, 'Total Deductions ', deduc_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(total_ded))), number_style)
                                col += 1 
                                net_total = gross_total + total_ded
                                allowance.append(net_total)
                                sheet.write(4,col,'Net Salary',net_pay_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(net_total))), number_style)
                                col += 1
                                final_total_list.append(allowance)  
                                department_total_dict.append(allowance)
                                nation_group_lst.append(nation_wise.employee_id.name)
                                row += 1
                                number+= 1
                            sheet.write(row, 7, 'Sub Total', total_style)
                            col = 8
                            d_list = []
                            for dept in range(len(department_total_dict[0])):
                                value = 0
                                for v in range(0,len(department_total_dict)):
                                    value+= department_total_dict[v][dept]
                                d_list.append(value)
                            for total_dept in d_list:
                                sheet.write(row, col, ('{:,.2f}'.format(abs(total_dept))), total_number_style)
                                col += 1
                row +=1
                sheet.write(row, 7, 'Grand Total', total_style)
                col = 8
                f_list = []
                r_list=[]
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in range(0,len(final_total_list)):
                        if r < len(final_total_list[v]):
                            value += final_total_list[v][r]
                        else:
                            print(f"Index {r} out of range in sublist {v}")
                                
                    f_list.append(value)
                    r_list = f_list
                for total_li in r_list:
                    sheet.write(row, col,('{:,.2f}'.format(abs(total_li))) , total_number_style)
                    col += 1
                
                if len(nation_group_lst) == 0:
                    raise ValidationError("Nation wise group employees is not there in this range")                   
                    
            elif wizard.group_wise=="location":
                branch_ids = False
                if wizard.branch_ids:
                    branch_ids = wizard.branch_ids
                else:
                    branch_ids = request.env['hr.branch'].search([])  
                final_total_list = []
                location_group_lst = []    
                for branch in branch_ids:                   
                    employees = request.env['hr.employee'].search([('branch_id', '=',branch.id)])
                    location = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids),('date_from','>=', wizard.from_date),('date_to','<=', wizard.to_date),('struct_id','=',wizard.structure_id.id)],order="name ASC")
                    if location:
                        col = 0
                        # row += 1
                        sheet.write(row, col,  branch.name,  department_heading_style)                                                
                        row += 1
                        department_total_dict=[]   
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
                                deduct=0.0
                                dedu=0.0
                                total=0.0
                                value=0.0
                                allowan=0.0
                                tota_emp=0.0
                                total_ded = 0.0
                                net_total = 0.0
                                gross_total = 0.0
                                total_allowance = 0.0
                                for line in branch_wise.line_ids:
                                      if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                        if line.sequence <= 11 :
                                            allowan =line.total
                                            total_allowance += allowan
                                            allowance.append(allowan)
                                            sheet.write(4,col,line.name,allow_style)
                                            # sheet.set_column(4,col,len(line.name))
                                            sheet.write(row, col, ('{:,.2f}'.format(abs(allowan))), number_style)
                                            col+=1
                                        if line.sequence > 11:
                                            value+=line.total
                                allowance.append(value)
                                sheet.write(4,col,'Other Transaction',allow_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                                col+=1
                                gross_total = total_allowance + value
                                allowance.append(gross_total)
                                sheet.write(4, col, 'Gross Salary', gross_pay_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(gross_total))), number_style)
                                col += 1
                                for line in branch_wise.line_ids:
                                    if line.code =="GOSI":
                                        deduct =line.total
                                        allowance.append(deduct)
                                        sheet.write(4,col,'GOSI',deduc_style)
                                        sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                                        col += 1
                                    if line.code=="Loan":
                                        deduct =line.total
                                        allowance.append(deduct)
                                        sheet.write(4,col,'Loan',deduc_style)
                                        sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                                        col += 1
                                for line in branch_wise.line_ids:
                                    if line.category_id.code == 'DED':
                                        if line.sequence >= 1:
                                            total_ded += line.total
                                            if line.code == "GOSI":
                                                deduct = line.total
                                            if line.code == "Loan":
                                                dedu = line.total
                                            total_emp = total_ded - (deduct + dedu)
                                allowance.append(total_emp)
                                allowance.append(total_ded)
                                sheet.write(4, col, 'Others', deduc_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(total_emp))), number_style)
                                col += 1
                                sheet.write(4, col, 'Total Deductions ', deduc_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(total_ded))), number_style)
                                col += 1
                                net_total = gross_total + total_ded
                                allowance.append(net_total)
                               
                                sheet.write(4,col,'Net Salary',net_pay_style)
                                sheet.write(row, col, ('{:,.2f}'.format(abs(net_total))), number_style)
                                col += 1
                                final_total_list.append(allowance)  
                                department_total_dict.append(allowance)
                                location_group_lst.append(branch_wise.employee_id.name)
                                row += 1
                                number+= 1
                            sheet.write(row, 7, 'Sub Total', total_style)
                            col = 8
                            d_list = []
                            for dept in range(len(department_total_dict[0])):
                                value = 0
                                for v in range(0,len(department_total_dict)):
                                    value+= department_total_dict[v][dept]
                                d_list.append(value)
                            for total_dept in d_list:
                                sheet.write(row, col, ('{:,.2f}'.format(abs(total_dept))), total_number_style)
                                col += 1
                row +=1
                sheet.write(row, 7, 'Grand Total', total_style)
                col = 8
                f_list = []
                r_list=[]
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in range(0,len(final_total_list)):
                        if r < len(final_total_list[v]):
                            value += final_total_list[v][r]
                        else:
                            print(f"Index {r} out of range in sublist {v}")
                                
                    f_list.append(value)
                    r_list = f_list
                for total_li in r_list:
                    sheet.write(row, col,('{:,.2f}'.format(abs(total_li))) , total_number_style)
                    col += 1
                if len(location_group_lst) == 0:
                    raise ValidationError("Location wise grouping payroll employee is not there in this range ")
            
            elif wizard.employ_ids and wizard.from_date and wizard.to_date:      
                employ = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',wizard.employ_ids.ids),('date_from','>=', wizard.from_date),('date_to','<=', wizard.to_date),('struct_id','=',wizard.structure_id.id)],order="name ASC")                         
                final_total_list = []
                emp_lst = []
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
                    allowance = []
                    deduction = []
                    col_lst = []
                    deduct=0.0
                    dedu=0.0
                    total=0.0
                    value=0.0
                    allowan=0.0
                    tota_emp=0.0
                    total_ded = 0.0
                    net_total = 0.0
                    gross_total = 0.0
                    total_allowance = 0.0
                    for line in emp.line_ids:
                        if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                            if line.sequence <= 11 :
                                allowan =line.total
                                total_allowance += allowan
                                allowance.append(allowan)
                                sheet.write(4,col,line.name,allow_style)
                                sheet.set_column(4,col,len(line.name))
                                sheet.write(row, col, ('{:,.2f}'.format(abs(allowan))), number_style)
                                col+=1
                            if line.sequence > 11:
                                value+=line.total
                    allowance.append(value)
                    sheet.write(4,col,'Other Transaction',allow_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                    col+=1
                    gross_total = total_allowance + value
                    allowance.append(gross_total)
                    sheet.write(4, col, 'Gross Salary', gross_pay_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(gross_total))), number_style)
                    col += 1
                    for line in emp.line_ids:
                        if line.code =="GOSI":
                            deduct =line.total
                            allowance.append(deduct)
                            sheet.write(4,col,'GOSI',deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                            col += 1
                        if line.code=="Loan":
                            deduct =line.total
                            allowance.append(deduct)
                            sheet.write(4,col,'Loan',deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                            col += 1
                    for line in emp.line_ids:
                        if line.category_id.code == 'DED':
                            if line.sequence >=1:
                                total_ded += line.total
                                if line.code=="GOSI":
                                    deduct=line.total
                                if line.code == "Loan":
                                    dedu=line.total
                                total_emp=total_ded - (deduct+dedu)
                    allowance.append(total_emp)
                    allowance.append(total_ded)
                    sheet.write(4,col,'Others',deduc_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_emp))), number_style)
                    col += 1
                    sheet.write(4, col, 'Total Deductions ', deduc_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_ded))), number_style)
                    col += 1
                    net_total = gross_total + total_ded
                    allowance.append(net_total)
                    sheet.write(4,col,'Net Salary',net_pay_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(net_total))), number_style)
                    col += 1   
                    final_total_list.append(allowance)
                    emp_lst.append(emp.employee_id.name)            
                    row += 1
                    number+= 1
                sheet.write(row, 7, 'Total',total_style)
                col=8
                f_list = []
                for r in range(len(final_total_list[0])):
                    value = 0
                    for v in range(0,len(final_total_list)):
                        if r < len(final_total_list[v]):
                            value += final_total_list[v][r]
                        else:
                            print(f"Index {r} out of range in sublist {v}")
                                
                    f_list.append(value)
                for total_line in f_list:
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), total_number_style)
                    col += 1 
                
                if len(emp_lst) == 0:
                    raise ValidationError("Payroll employee is not there in this range")           
   
            elif((wizard.department_ids or wizard.job_ids  or wizard.nationality_ids or wizard.branch_ids or wizard.employ_ids) and wizard.from_date and wizard.to_date):
                employees = request.env['hr.employee'].search(['|','|','|',('department_id', '=',wizard.department_ids.ids),('job_id', '=',wizard.job_ids.ids),('country_id', '=',wizard.nationality_ids.ids),('branch_id', '=',wizard.branch_ids.ids)])
                final_total_list = []
                col = 0            
                code_lst = []
                dept_lst = []
                all_dept = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('employee_id','=',employees.ids or wizard.employ_ids.ids),('date_from','=', wizard.from_date),('date_to','=', wizard.to_date),('struct_id','=',wizard.structure_id.id)],order="name ASC")
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
                        deduct=0.0
                        dedu=0.0
                        total=0.0
                        value=0.0
                        allowan=0.0
                        tota_emp=0.0
                        total_ded = 0.0
                        net_total = 0.0
                        gross_total = 0.0
                        total_allowance = 0.0
                        for line in al_dept.line_ids:
                            if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                                if line.sequence <= 11 :
                                    allowan =line.total
                                    total_allowance += allowan
                                    allowance.append(allowan)
                                    sheet.write(4,col,line.name,allow_style)
                                    sheet.set_column(4,col,len(line.name))
                                    sheet.write(row, col, ('{:,.2f}'.format(abs(allowan))), number_style)
                                    col+=1
                                if line.sequence > 11:
                                    value+=line.total
                    allowance.append(value)
                    sheet.write(4,col,'Other Transaction',allow_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                    col+=1
                    gross_total = total_allowance + value
                    allowance.append(gross_total)
                    sheet.write(4, col, 'Gross Salary', gross_pay_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(gross_total))), number_style)
                    col += 1
                    for line in al_dept.line_ids:
                        if line.code =="GOSI":
                            deduct =line.total
                            allowance.append(deduct)
                            sheet.write(4,col,'GOSI',deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                            col += 1
                        if line.code=="Loan":
                            deduct =line.total
                            allowance.append(deduct)
                            sheet.write(4,col,'Loan',deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                            col += 1
                    for line in al_dept.line_ids:
                        if line.category_id.code == 'DED':
                            if line.sequence >=1:
                                total_ded += line.total
                                if line.code == "GOSI":
                                    deduct = line.total
                                if line.code == "Loan":
                                    dedu = line.total
                                total_emp = total_ded - (deduct + dedu)
                    allowance.append(total_emp)
                    allowance.append(total_ded)
                    sheet.write(4, col, 'Others', deduc_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_emp))), number_style)
                    col += 1
                    sheet.write(4, col, 'Total Deductions ', deduc_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_ded))), number_style)
                    col += 1
                    net_total = gross_total + total_ded
                    allowance.append(net_total)
                    sheet.write(4,col,'Net Salary',net_pay_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(net_total))), number_style)
                    col += 1
                    final_total_list.append(allowance)
                    dept_lst.append(al_dept.employee_id.name)            
                    row += 1
                    number+= 1
                    
                
                sheet.write(row, 7, 'Total',total_style)
                col=8
                f_list = []
                if final_total_list:
                    for r in range(len(final_total_list[0])):
                        value = 0
                        for v in range(0,len(final_total_list)):
                            if r < len(final_total_list[v]):
                                value += final_total_list[v][r]
                            else:
                                print(f"Index {r} out of range in sublist {v}")
                                    
                           
                        f_list.append(value)
                    for total_line in f_list:
                        sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), total_number_style)
                        col += 1        
             
                if len(dept_lst) ==0:
                    raise ValidationError("Payroll employee is not there in this range")    
               
            
            elif wizard.from_date and wizard.to_date:    
                payslip_date_wise = request.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('date_from','>=', wizard.from_date),('date_to','<=', wizard.to_date),('struct_id','=',wizard.structure_id.id)],order="name ASC")
                final_total_list = []
                date_lst = []
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
                    deduct=0.0
                    dedu=0.0
                    total=0.0
                    value=0.0
                    allowan=0.0
                    tota_emp=0.0
                    total_ded = 0.0
                    net_total = 0.0
                    gross_total = 0.0
                    total_allowance = 0.0
                    for line in payslip.line_ids:
                        if line.category_id.code == 'ALW' or line.category_id.code == 'BASIC' :
                            if line.sequence <= 11 :
                                allowan = line.total
                                total_allowance += allowan
                                allowance.append(allowan)
                                sheet.write(4,col,line.name,allow_style)
                                sheet.set_column(4,col,len(line.name))
                                sheet.write(row, col, ('{:,.2f}'.format(abs(allowan))), number_style)
                                col+=1
                            if line.sequence > 11:
                                value+=line.total
                    allowance.append(value)
                    sheet.write(4,col,'Other Transaction',allow_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(value))), number_style)
                    col+=1
                    # for line in payslip.line_ids:
                    #     gross_total =0.0   
                    #     if line.code == "GROSS":
                    gross_total = total_allowance + value
                    allowance.append(gross_total)
                    sheet.write(4, col, 'Gross Salary', gross_pay_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(gross_total))), number_style)
                    col += 1
                    for line in payslip.line_ids:
            
                        if line.code =="GOSI":
                            deduct =line.total
                            allowance.append(deduct)
                            sheet.write(4,col,'GOSI',deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                            col += 1
                        if line.code=="Loan":
                            deduct =line.total
                            allowance.append(deduct)
                            sheet.write(4,col,'Loan',deduc_style)
                            sheet.write(row, col, ('{:,.2f}'.format(abs(deduct))), number_style)
                            col += 1
                    for line in payslip.line_ids:
                        if line.category_id.code == 'DED':
                            if line.sequence >=1:
                                total_ded += line.total
                                if line.code == "GOSI":
                                    deduct = line.total
                                if line.code == "Loan":
                                    dedu = line.total
                                total_emp = total_ded - (deduct + dedu)
                    allowance.append(total_emp)
                    allowance.append(total_ded)
                    sheet.write(4, col, 'Others', deduc_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_emp))), number_style)
                    col += 1
                    sheet.write(4, col, 'Total Deductions ', deduc_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(total_ded))), number_style)
                    col += 1
                    
                    net_total = gross_total + total_ded
                    allowance.append(net_total)
                    sheet.write(4,col,'Net Salary',net_pay_style)
                    sheet.write(row, col, ('{:,.2f}'.format(abs(net_total))), number_style)
                    col += 1
                    final_total_list.append(allowance)
                    date_lst.append(payslip.employee_id.name)
                    row += 1
                    number+= 1
                sheet.write(row, 7, 'Total',total_style)
                col=8
                f_list = []
                if len(date_lst)==0:
                    raise ValidationError(_("Payroll employee is not there in this range")) 
                if final_total_list:
                    for r in range(len(final_total_list[0])):
                        value = 0
                        for v in range(0,len(final_total_list)):
                            if r < len(final_total_list[v]):
                                value += final_total_list[v][r]
                            else:
                                print(f"Index {r} out of range in sublist {v}")
                
                        f_list.append(value)
                    for total_line in f_list:
                        sheet.write(row, col, ('{:,.2f}'.format(abs(total_line))), total_number_style)
                        col += 1
                    

          
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
        return response
        
        
        
        
        
        
        
        
        