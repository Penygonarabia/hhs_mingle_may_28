from odoo import fields, models, api, _
from odoo.tools.misc import xlsxwriter
import io
from datetime import datetime,date
import pytz
import pandas as pd
from odoo.exceptions import warnings, ValidationError
import base64
import io
from io import BytesIO
from PIL import Image as PILImage
from openpyxl.drawing.image import Image
from PIL import Image



class JobCardExcel(models.AbstractModel):
    _name = 'report.machine_repair_management.report_job_card_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Job Card Report Xlsx'

    def generate_xlsx_report(self, workbook, data, wizard):

        # Formats
        header_merge_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})

        header_merge_format3 = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                    'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
        
        header_merge_format_right = workbook.add_format({'bold': True, 'align': 'right', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
        
        header_merge_format_left = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})


        header_data_format = workbook.add_format({'align': 'right', 'valign': 'vcenter',
                                                  'font_size': 10, 'border': 1})
        header_data_format2 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#F2D7D5', 'border': 1})
        header_data_format3 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#87CEFA', 'border': 1})
        name_format = workbook.add_format({'align': 'left', 'valign': 'top',
                                           'font_size': 10, 'border': 1})
        
        engineer_comments_format = workbook.add_format({'align':'left','valign':'top',
                                                        'font_size':10,'border':1,'text_wrap':True})
        text_name_format = workbook.add_format({'align': 'left', 'valign': 'vcenter',
                                           'font_size': 10, 'border': 1,"text_wrap":True})
        
        text_number_format = workbook.add_format({'align': 'right', 'valign': 'vcenter',
                                           'font_size': 10, 'border': 1,"text_wrap":True})
        
        num_format = workbook.add_format({'align': 'right', 'valign': 'top',
                                          'font_size': 10, 'border': 1})
        header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter',
                                                  'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})

        header_data_format4 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#B7950B', 'border': 1})
        
        name_wrap_format = workbook.add_format({
        'text_wrap': True,
        'valign': 'top',
        'font_size': 10,  # optional
        'border': 1,
        'align': 'left'
        })
        
        number_wrap_format = workbook.add_format({
        'text_wrap': True,
        'valign': 'top',
        'font_size': 10,  # optional
        'border': 1,
        'align': 'right'
        })
        
        
        # Sheet
        sheet = workbook.add_worksheet("Job Card Report")
        sheet.set_row(0, 25)
     
        sheet.merge_range(0, 0, 2, 48, "Job Card Report", header_merge_format)
       
        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 6, wizard.company_id.name, header_merge_format)

        sheet.merge_range(4, 7, 4, 8, 'Today Date', header_merge_format)
        sheet.merge_range(4, 9, 4, 10, datetime.today().strftime("%d-%b-%Y"), header_merge_format)
        
        
        sheet.merge_range(5, 0, 5, 1, 'Start Date', header_merge_format)
        sheet.merge_range(5, 2, 5, 3, wizard.from_date.strftime("%d-%b-%Y"), header_merge_format)

        sheet.merge_range(5, 4, 5, 5, 'End Date', header_merge_format)
        sheet.merge_range(5, 6, 5, 7, wizard.to_date.strftime("%d-%b-%Y"), header_merge_format)

        # Header
        row = 7
        col = 0
        # if wizard.type == 'loan':
        headers = ['S.No', 'Region',  'Card Control No', 'Month',
                   'Date', 'Time', 'Customer Name', 'Mobile No', 'Address','Property Type','Function','PM Company',
                   'Brand', 'Group Type','Model No', 'Serial Number', 'Purchase No',
                   'Purchase Date', 'Dealer', 'Warranty Status', 'warranty Expiry Date',
                   'Symptoms','Defects','Services','Freon Charge Qty', 'Job Done', 'Invoice No', 'Appoint Date','Appoint Time', 'Technician',
                   'No of Visits', 'Parts', 'Part Name', 'Qty', 'Parts - Warranty Cost', 'Parts Charge',
                   'Service Charge', 'Total', 'Status', 'Action Status','Jobcard Created User',
                   'Last Modified User', 'Month', 'Completion Date', 'Completion Time', 'RTAT', 'Engineer Comments','Remarks',
                   'Customer Signature'
                   ]
        col_widths = [8, 12, 15, 8, 10, 8, 18, 15, 18, 15,12,15,15, 
                      12, 25, 18, 15, 18, 25, 18, 15, 25, 
                      25, 25, 15, 12, 18, 18, 18, 18, 12, 18, 
                      60, 8, 15, 15, 15, 10, 30, 18, 18, 18,
                       10, 12, 12, 10, 18, 18, 18]

        for header, width in zip(headers, col_widths):
            sheet.write(row, col, header, header_merge_format)
            sheet.set_column(col, col, width)
            col += 1
      
        if wizard.company_id.logo:
            logo_data = base64.b64decode(wizard.company_id.logo)
            logo_stream = io.BytesIO(logo_data)
            sheet.insert_image('A1:B1', 'logo.png', {
                'image_data': logo_stream,
                'x_scale': 0.70,# Adjust scale to fit image within the merged cells
                'y_scale': 0.70, # Adjust scale as needed
                # 'x_offset': 0.20,  # Optional: fine-tune positioning horizontally
                # 'y_offset': 0.20    # Optional: fine-tune positioning vertically
            })
        
        # Data rows
        row = 8
        no = 1
        domain = [('id', 'in',
                   wizard.job_card_ids.ids if wizard.job_card_ids else self.env['project.task'].search([]).ids)]

        # if wizard.from_date and wizard.to_date:
        #     domain += [('service_created_datetime', '<=', wizard.to_date), ('service_created_datetime', '>=', wizard.from_date)]
        
        '''Code Commented on June 29 2026 by Vijaya Bhaskar because before Feb 01 2026 client asked request date is taken from machine repair support '''
        # if wizard.from_date and wizard.to_date:
        #     domain += [('service_created_datetime', '<=', wizard.to_date), ('service_created_datetime', '>=', wizard.from_date)]
        
        cutoff_date = date(2026, 2, 1)

        if wizard.from_date and wizard.from_date < cutoff_date:
            model = self.env['machine.repair.support']
            date_field = 'request_date'
        else:
            model = self.env['project.task']
            date_field = 'service_created_datetime'
        
        # Date domain
        if wizard.from_date and wizard.to_date:
            domain += [
                (date_field, '>=', wizard.from_date),
                (date_field, '<=', wizard.to_date),
            ]
     
        if wizard.job_card_ids:
            domain += [('id', 'in', wizard.job_card_ids.ids)]
        if wizard.product_category_ids:
            domain += [('product_category_id', 'child_of', wizard.product_category_ids.ids)]
            # domain += [('product_category_id', 'in', wizard.product_category_ids.ids)]

            
        if wizard.work_center_group_id:
            domain += [('work_center_id.work_center_group_id','=',wizard.work_center_group_id.id)]
        
        
        '''Added on April 15 2026 by Vijaya Bhaskar as per client asked the Job Status Filter'''
        if wizard.job_state_ids:
            domain += [('job_card_state_code','in', wizard.job_state_ids.mapped('code'))]
            
        
        
        domain += [('work_center_id','in', wizard.env.user.default_work_center_id.ids if wizard.env.user.default_work_center_id else self.env['work.center.location'].search([]).ids)]  
     
        job_card_search = self.env['project.task'].search(domain,order ="service_created_datetime Asc")
        
        # job_card_search = self.env['project.task'].search(domain)
        
        if wizard.job_card_ids:
            job_card_search = job_card_search.sorted(key=lambda c: c.name.lower())

        if wizard.product_category_ids:
            job_card_search = job_card_search.sorted(key=lambda c: c.product_category_id.name.lower())

        seen_job_cards = set()
        seen_product_categories = set()
        num = 1
        job_lst = []
        total_jobs_count = 0.0
        total_rtat_hours = 0.0
        format_rtat_hours = False
      
        ''' for cancelled job card'''
        job_card_cancel_count = len(job_card_search.filtered(lambda l:l.job_card_state_code == '154'))
        #### this is full not considered the domain for search_count
        # job_card_cancel_count = job_card_search.search_count([('job_card_state_code','=','124')])
          
        '''for Closed Job Card '''
        job_card_closed_count = len(job_card_search.filtered(lambda l :l.job_card_state_code == '126'))

        # job_card_closed_count = job_card_search.search_count([('job_card_state_code','=','126')])
          
        ''' For Total parts amount include tax''' 
        job_card_parts_amount = sum(line.parts_grand_total_amount for line in job_card_search.filtered(lambda l :l.parts_grand_total_amount) if line.parts_grand_total_amount)
          
        ''' For service amount total'''
        job_card_service_amount = sum(line.service_grand_total_amount for line in job_card_search.filtered(lambda l:l.service_grand_total_amount) if line.service_grand_total_amount)
          
        ''' for Grand total both service and parts'''
        job_card_grand_total_amount = sum(line.grand_total for line in job_card_search.filtered(lambda l:l.grand_total) if line.grand_total) 
          
        ''' Job card not in the state in closed and cancelled '''
        job_card_pending_count = len(job_card_search.filtered(lambda l : l.job_card_state_code not in ('126','154')))
        # job_card_pending_count = job_card_search.search_count([('job_card_state_code','not in',('124','126'))])
        
        '''Job card is below 48 hour count'''
        job_card_below_48_hour = len(job_card_search.filtered(lambda l : l.rtat_hours and l.rtat_hours < 48.0 and l.job_card_state_code == '126'))
        
        
        '''Job card is above 120 hours count'''        
        job_card_above_120_hour = len(job_card_search.filtered(lambda l: l.rtat_hours and l.rtat_hours > 120.0 and l.job_card_state_code == '126'))
        
       
        
        '''Job Card Closed Not Under Warranty'''
        job_card_closed_count_not_under_warranty = len(job_card_search.filtered(lambda l :l.job_card_state_code == '126' and   l.service_warranty_id.amount_required))
        
        # Code Commented On April 15 2026 by Vijaya Bhaskar Because Client Asked Warranty all comes Under warranty and other than that Not Under Warranty
        #job_card_closed_count_not_under_warranty = len(job_card_search.filtered(lambda l :l.job_card_state_code == '126' and not l.service_warranty_id.warranty_applicable_bool))

        
        '''Job Card Closed Under Warranty'''
        job_card_closed_count_under_warranty = len(job_card_search.filtered(lambda l :l.job_card_state_code == '126'  and not l.service_warranty_id.amount_required))
        
        # Code Commented On April 15 2026 by Vijaya Bhaskar Because Client Asked Warranty all comes Under warranty and other than that Not Under Warranty
        # job_card_closed_count_under_warranty = len(job_card_search.filtered(lambda l :l.job_card_state_code == '126'  and l.service_warranty_id and l.service_warranty_id.warranty_applicable_bool))

        
        spare_parts_warranty = 0.0
        
        service_charge_warranty = 0.0
        
        spare_parts_price  = 0.0
        
        '''code Added on May 14 2026'''
        total_service_qty = 0.0
        
        for job in job_card_search:
              
            lines_count = []
            product_name_count = []
            total_jobs_count += 1
            total_rtat_hours += job.rtat_hours if job.job_card_state_code  == '126' else 0.0
              
              
 
            col = 0
            sheet.write(row, col, no, num_format)
            col += 1
            # sheet.write(row, col, job.location_id.res_region_id.name or ' ', name_format)
            sheet.write(row, col, job.work_center_group_id.name or ' ', name_format)
            col += 1
            sheet.write(row, col, job.name or ' ', name_format)
            col += 1
            # sheet.write(row, col, job.control_card_no or ' ', name_format)
            # col += 1
            sheet.write(row, col,job.service_created_datetime.strftime('%B') if job.service_created_datetime else '',
                          name_format)
            col += 1
            sheet.write(row, col,job.service_created_datetime.strftime("%d-%m-%Y") if job.service_created_datetime else ' ',
                          name_format)
            col += 1
            
            service_created_time = False
            user_tz = self.env.user.tz or 'UTC'
            user_timezone = pytz.timezone(user_tz)
            localized_dt = pytz.utc.localize(job.service_created_datetime).astimezone(user_timezone)
            service_created_time = localized_dt.strftime('%H:%M')

            
            sheet.write(row, col,service_created_time if job.service_created_datetime else '',
                          num_format)
            col += 1
            sheet.write(row, col, job.partner_id.name or ' ', name_format)
            col += 1
            sheet.write(row, col, job.phone or ' ', name_format)
            col += 1
            sheet.write(row, col, job.address or ' ', name_format)
            col += 1
            sheet.write(row, col, (job.type_of_property or ' ').capitalize(), name_format)
            col += 1
            sheet.write(row, col, job.property_type_maintenance_details_id.complete_name or '',name_format)
            col += 1
            sheet.write(row, col, job.company_preventive_maintenance or ' ',name_format)
            col += 1
            sheet.write(row, col, job.product_category_id.name or ' ', name_format)
            col += 1
            sheet.write(row, col, job.product_id.category_group_type or  '',name_format )
            col += 1
            # sheet.write(row, col, job.product_id.display_name or ' ', name_format)

            sheet.write(row, col, job.product_id.default_code or ' ', name_format)
            col += 1
            sheet.write(row, col, job.product_slno or ' ', name_format)
            col += 1
            sheet.write(row, col, job.purchase_invoice_no or ' ', name_format)
            col += 1
            sheet.write(row, col,job.purchase_date.strftime("%d-%m-%Y") if job.purchase_date else ' ',
                          name_format)
            col += 1
            sheet.write(row, col, job.dealer_id.name or ' ', name_format)
            col += 1
            sheet.write(row, col, job.service_warranty_id.name or ' ', name_format)
            col += 1
            sheet.write(row, col,job.warranty_expiry_date.strftime("%d-%m-%Y") if job.warranty_expiry_date else ' ',
                          name_format)
            col += 1

    
            symptoms = '\n'.join(f"[{sym.code.sym_code}] {sym.code.sym_desc}" for sym in job.symptoms_line_ids if sym.code)
            # symptoms = '\n'.join(sym.code.sym_desc for sym in job.symptoms_line_ids if sym.code)
            sheet.write(row, col, symptoms or '', text_name_format)
            symptoms_count = symptoms.count('\n') + 1 if symptoms else 1
            lines_count.append(symptoms_count)
            col += 1
            
            
            defects = "\n".join(f"[{defect.code.def_code}] {defect.code.def_desc}" for defect in job.defects_type_ids if defect.code)
            sheet.write(row, col, defects or '',text_name_format)
            col += 1
            
            services  = "\n".join(f"[{service.code.code}] {service.code.name}"for service in job.service_type_ids if service.code)
            sheet.write (row, col, services or '',text_name_format)
            col += 1
            
            # service_qty = "\n".join(f"{service.service_quantity}" for service in job.service_type_ids if service.code)
            service_qty = "\n".join(
                str(service.service_quantity)
                for service in job.service_type_ids
                if service.code and service.service_quantity > 0
            )
            sheet.write (row, col, service_qty or '', text_number_format)
            col += 1
            '''code Added on May 14 2026'''
            total_service_qty  += sum(line.service_quantity for line in job.service_type_ids)
            
          
            sheet.write(row, col,'',name_format)
            col += 1
              
            sheet.write(row, col,job.invoice_no or '',name_format)
            col += 1
              
            sheet.write(row, col,job.planned_date_begin.strftime("%d-%m-%Y") if job.planned_date_begin else ' ',
                          name_format)
            
            # sheet.write(row, col,job.appointment_datetime.strftime("%d-%m-%Y") if job.appointment_datetime else ' ',
            #               name_format)
            col += 1
              
            planned_date_begin = False
            if job.planned_date_begin:
                planned_date_begin_dt = pytz.utc.localize(job.planned_date_begin).astimezone(user_timezone)
                planned_date_begin = planned_date_begin_dt.strftime('%H:%M')
              
            sheet.write(row, col,planned_date_begin if job.planned_date_begin else '',
                          num_format)
            
            # sheet.write(row, col,job.appointment_datetime.strftime('%H:%M') if job.appointment_datetime else '',
            #               name_format)
            col += 1
              
            sheet.write(row, col, job.technician_id.name or ' ', name_format)
            col += 1
              
            sheet.write(row, col, job.technician_no_of_visit_count or ' ', name_format)
            col += 1
              
            product_codes = []
            product_name = []
            product_qty = []
            product_unit_price = []
            product_cost_price_charge = []
            product_inspection_charge = []
        
            for line in job.product_line_ids:
                product_codes.append(line.product_id.default_code or '')
                product_name.append(line.product_id.name or '')
                product_qty.append(str(int(line.qty)) if line.qty else '0.0')
                '''Code Added on Feb 04 2026'''
                # if line.standard_price:
                #     line.standard_price = 0.0
                
                '''Code Added on March 30 2026 by Vijaya bhaskar client asked to Parts - Warranty Cost Column'''
                # product_unit_price.append(str(round(line.product_id.standard_price,2)) if line.product_id.standard_price and line.under_warranty_bool  else '0.00')
                product_unit_price.append(str(round(line.qty * line.product_id.standard_price,2)) if line.product_id.standard_price and line.under_warranty_bool  else '0.00')

                
                product_cost_price_charge.append(str(round(line.total,2)) if line.product_id and not line.under_warranty_bool and not( line.product_id.service_product_price_edit_bool or line.product_id.service_type_bool) else '0.00')
                
                product_inspection_charge.append(str(round(line.total,2)) if line.product_id  and (line.product_id.service_product_price_edit_bool or line.product_id.service_type_bool) else '0.00')
                
                '''Code Commented on March 30 2026 by Vijaya bhaskar client asked to Parts - Warranty Cost Column
                product_unit_price.append(str(round(line.product_id.standard_price,2)) if line.product_id.standard_price and job.service_warranty_id.warranty_applicable_bool and not job.service_warranty_id.misuse_warranty_bool else '0.00')
                spare_parts_warranty += line.product_id.standard_price if job.service_warranty_id.warranty_applicable_bool and not job.service_warranty_id.misuse_warranty_bool else 0.0

                ''' 
                
                spare_parts_warranty += (line.qty * line.product_id.standard_price) if line.product_id.standard_price and line.under_warranty_bool else 0.0
                
                ''' Code Added on April 01 2026 by Vijaya Bhaskar
                spare_parts_warranty += line.product_id.standard_price if line.product_id.standard_price and line.under_warranty_bool else 0.0
                '''
                service_charge_warranty += line.total if line.product_id and (line.product_id.service_product_price_edit_bool or line.product_id.service_type_bool) else 0.0
                
                spare_parts_price += line.total if line.product_id and not line.under_warranty_bool and not( line.product_id.service_product_price_edit_bool or line.product_id.service_type_bool) else 0.0
                
                # product_unit_price.append(str(line.standard_price) if line.standard_price else '0.00')
                # spare_parts_warranty += line.standard_price
        
            # Join values with newlines so they appear as multiple lines in a single cell
            product_codes_str = '\n'.join(product_codes) if product_codes else ''
            product_name_str = '\n'.join(product_name) if product_name else ''
            product_qty_str = '\n'.join(product_qty) if product_qty else ''
            product_unit_price_str = '\n'.join(product_unit_price) if product_unit_price else ''
            product_cost_price_str = "\n".join(product_cost_price_charge) if product_cost_price_charge else ''
            product_inspection_charge_str = "\n".join(product_inspection_charge) if product_inspection_charge else ''
            # Write into sheet with wrap_format
            sheet.write(row, col, product_codes_str, name_wrap_format)
            col += 1
            sheet.write(row, col, product_name_str, name_wrap_format)
            col += 1
            sheet.write(row, col, product_qty_str, number_wrap_format)
            col += 1
            sheet.write(row, col, product_unit_price_str, number_wrap_format)
            col += 1
            '''Code Added on March 30 2026 by Vijaya bhaskar client asked to Parts - Warranty Cost Column'''
            sheet.write(row, col, product_cost_price_str, number_wrap_format)
            
            col += 1
            sheet.write(row, col, product_inspection_charge_str, number_wrap_format)
            
            col += 1
            
           
            ''''Currently working but each product parts are not coming by line by line in a single cell so it is commented on Aug-28-2025 by VIJAYA BHASKAR'''      
            # ''' Product code'''
            # parts_code = "\n".join(line.product_id.default_code for line in job.product_line_ids if line.product_id.detailed_type !='service')
            # sheet.write(row,col, parts_code or ' ', name_format)
            # product_count = parts_code.count('\n') + 1 if parts_code else 1
            # lines_count.append(product_count)
            #
            # """ sheet.set_row(row, product_count * 18)"""
            # col += 1
            #
            #
            # ''' Product name'''
            # parts_name = "\n".join(line.product_id.name for line in job.product_line_ids if line.product_id.detailed_type !='service')
            # sheet.write(row,col, parts_name or ' ', name_format)
            # product_name_count = parts_name.count('\n') + 1 if parts_name else 1
            # lines_count.append(product_name_count)
            # # sheet.set_row(row, product_name_count * 18)
            # col += 1
            #
            # ''' Product Qty '''
            # parts_qty = "\n".join(f"{line.qty:,.2f}" for line in job.product_line_ids if line.product_id.detailed_type !='service')
            # sheet.write(row,col, parts_qty or ' ', num_format)
            # product_qty_count = parts_qty.count('\n') + 1 if parts_qty else 1
            # lines_count.append(product_qty_count)
            # # sheet.set_row(row, product_qty_count * 18)
            # col += 1
            #
            # ''' Product Unit price'''
            # parts_unit_price = "\n".join(f"{line.standard_price:,.2f}" if line.under_warranty_bool else "0.00" for line in job.product_line_ids if line.product_id.detailed_type !='service'  )
            # sheet.write(row,col, parts_unit_price or ' ', num_format)
            # product_unit_price_count = parts_unit_price.count('\n') + 1 if parts_unit_price else 1
            # lines_count.append(product_unit_price_count)
            # # sheet.set_row(row, product_unit_price_count * 18)
            # col += 1
            '''Code Commented on March 30 2026 by Vijaya bhaskar client asked to Parts - Warranty Cost Column
            sheet.write(row,col, round(job.parts_grand_total_amount, 2) or 0.0,num_format)
            col += 1
            sheet.write(row,col, round(job.service_grand_total_amount, 2) or 0.0,num_format)
            col += 1

            '''
            
            sheet.write(row,col, round(job.grand_total, 2) or 0.0,num_format)
            col += 1  
            # sheet.write(row,col, f"{job.parts_grand_total_amount:,.2f}" or '',num_format)
            # col += 1
            # sheet.write(row,col, f"{job.service_grand_total_amount:,.2f}" or '',num_format)
            # col += 1
            # sheet.write(row,col, f"{job.grand_total:,.2f}" or '',num_format)
            # col += 1
              
          
            # '''Product standard price'''
            # parts_standard_price = "\n".join(f"{line.standard_price:.2f}" for line in job.product_line_ids if job.product_id)
            # sheet.write(row,col, parts_standard_price or ' ', num_format)
            # # product_standard_price_count = parts_standard_price.count('\n') + 1 if parts_standard_price else 1
            # # sheet.set_row(row, product_standard_price_count * 18)
            # col += 1
          
          
          
            #  '''product service charge'''
            # parts_standard_price = "\n".join(f"{line.standard_price:.2f}" for line in job.product_line_ids if job.product_id)
            # sheet.write(row,col, parts_standard_price or ' ', num_format)
            # # product_standard_price_count = parts_standard_price.count('\n') + 1 if parts_standard_price else 1
            # # sheet.set_row(row, product_standard_price_count * 18)
            # col += 1
            #
            # ''' Product Total'''
            # parts_total = "\n".join(f"{line.total:.2f}" for line in job.product_line_ids if job.product_id)
            # sheet.write(row,col, parts_total or ' ', num_format)
            # # product_subtotal_count = parts_total.count('\n') + 1 if parts_total else 1
            # # sheet.set_row(row, product_subtotal_count * 18)
            # col += 1
            #
            sheet.write(row, col, job.job_card_state or '',name_format)
            col += 1
            
            if job.job_card_state_code == '126':
                sheet.write(row, col, 'Closed', name_format)
            elif job.job_card_state_code == '154':
                sheet.write(row, col, 'Cancelled', name_format)    
            else:
                sheet.write(row, col, 'Not Closed', name_format)
            col += 1        
              
            '''Job card created user'''
            sheet.write(row,col, job.create_uid.name or '',name_format)
            col += 1
              
            '''Job card Last modifed user'''
                             
            sheet.write(row,col, job.write_uid.name or '',name_format)
            col += 1
              
             
            sheet.write(row, col,job.closed_datetime.strftime('%B') if job.closed_datetime else '',
                          name_format)
            col += 1
            sheet.write(row, col, job.closed_datetime.strftime("%d-%m-%Y") if job.closed_datetime else ' ',
                          name_format)
            col += 1
            
            closed_datetime = False
            if job.closed_datetime:
                closed_datetime_dt = pytz.utc.localize(job.closed_datetime).astimezone(user_timezone)
                closed_datetime = closed_datetime_dt.strftime('%H:%M')
                
            sheet.write(row, col, closed_datetime if job.closed_datetime else '',
                          num_format)# max_lines = max(
            # len(product_codes),
            # len(product_name),
            # len(product_qty),
            # len(product_unit_price)
            # )
            # sheet.set_row(row, 15 * (max_lines if max_lines > 1 else 1))
            col += 1
            # rtat_col_index = headers.index('RTAT')
            #
            # duration_fmt = workbook.add_format({
            #     'num_format': '[h]:mm',
            #     'align': 'center',
            #     'valign': 'vcenter',
            #     'border': 1
            # })
            #
            # sheet.set_column(rtat_col_index, rtat_col_index, None, duration_fmt)
            # if job.rtat_hours and job.job_card_state_code == '126':
            #     sheet.write_number(row, col, job.rtat_hours / 24)
            # else:
            #     sheet.write_blank(row, col, None, duration_fmt)
            
            
            duration_fmt = workbook.add_format({
            'num_format': '[h]:mm',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
            if job.rtat_hours and job.job_card_state_code == '126':
                excel_time = job.rtat_hours / 24
                sheet.write_number(row, col, round(job.rtat_hours,2), num_format)
            else:
                sheet.write_blank(row, col,None, num_format)
            # duration_fmt = workbook.add_format({'num_format': '[h]:mm','align': 'center','valign': 'vcenter','border': 1})  
            #  # sheet.set_column('AP:AP', 12, duration_fmt)   # 12 = nice width for hh:mm display
            # if job.rtat_hours and job.job_card_state_code == '126':
            #     hours_check = int(job.rtat_hours)
            #     min_check = int(round((job.rtat_hours - hours_check)* 60))
            #
            #     time_format_hours =  (hours_check * 60 + min_check)/1440
            #
            #       # format_hours = f"{hours_check}:{min_check:02d}"
            #      # # format_hours = f"{hours_check} H :{min_check:02d} min"
            #      # sheet.write(row, col, format_hours , num_format)
            #      # sheet.write(row, col, time_format_hours,num_format )
            #     sheet.write(row, col, job.rtat_hours / 24,duration_fmt)
            #      # sheet.write_formula(total_row, total_col, '=SUM(AP9:AP149)', duration_fmt)  # Displays as 2893:44
            # else:
            #     sheet.write(row, col, '', num_format)
            

            col += 1
            sheet.write(row, col, job.engineer_comments or '', engineer_comments_format)
            col += 1
            sheet.write(row, col, job.supervisor_comments or '', engineer_comments_format)
            col += 1
            
            if job.signature:
                try:
                    signature = job.signature
            
                    # 🔥 CRITICAL: remove base64 header
                    if isinstance(signature, str) and ',' in signature:
                        signature = signature.split(',')[1]
            
                    # Decode
                    image_bytes = base64.b64decode(signature)
            
                    # Load image
                    image = Image.open(io.BytesIO(image_bytes))
                    image.load()  # 🔥 forces validation
            
                    # Resize
                    image.thumbnail((120, 60))
            
                    # Save to memory
                    image_stream = io.BytesIO()
                    image.save(image_stream, format='PNG')
                    image_stream.seek(0)
            
                    # Insert into Excel
                    sheet.insert_image(row, col, 'signature.png', {
                        'image_data': image_stream,
                        'x_offset': 5,
                        'y_offset': 5,
                    })
            
                    # Adjust cell
                    sheet.set_row(row, image.height * 0.75)
                    sheet.set_column(col, col, image.width / 7)
            
                except Exception as e:
                    # SHOW REAL ERROR (not hiding it)
                    sheet.write(row, col, f'Image Error: {e}', name_format)
            else:
                sheet.write(row, col, '',name_format)
            
            ##### currently working commented on Vijaya Bhaskar on JAN 30 2026
            # if job.signature:
            #     try:
            #         # Decode the base64 signature
            #         signature_data = base64.b64decode(job.signature)
            #         image = Image.open(io.BytesIO(signature_data))
            #
            #         # Resize image to fit cell appropriately
            #         max_width = 100  # pixels
            #         max_height = 100  # pixels
            #         image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            #
            #         # Save to temporary file
            #         temp_file = io.BytesIO()
            #         image.save(temp_file, format='PNG')
            #         temp_file.seek(0)
            #
            #         # Calculate cell position
            #         cell_width = 10  # Adjust based on your column width
            #         cell_height = 25  # Adjust based on your row height
            #
            #         # Insert image with proper positioning within the cell
            #         sheet.insert_image(row, col, '', {
            #             'image_data': temp_file,
            #             # Small offset from top
            #             'x_scale': 2,  # Scale down to fit
            #             'y_scale': 2   # Scale down to fit
            #         })
            #
            #         # Adjust row height to accommodate the image
            #         sheet.set_row(row, max(15, image.height + 4))
            #
            #     except Exception as e:
            #         sheet.write(row, col, 'Signature Error', name_format)
            # else:
            #     sheet.write(row, col, '', name_format)
                            
            # sheet.write(row, col, job.signature or '')
            #
            
            job_lst.append(job.name)
              
            max_line_count = max(lines_count) if lines_count else 1
            sheet.set_row(row, max_line_count * 60) 
              
            row += 1
            no += 1
            num += 1
        row += 1
        col = 0
         
        sheet.merge_range(row,col, row,  col+1, "Pending Job Card", header_merge_format_left)
        col += 2
        sheet.write(row,col, job_card_pending_count, header_merge_format_right)  
      
        # sheet.write(row, col, f"{job_card_closed_count:,.2f}", header_merge_format_right)

        col += 2
        sheet.merge_range(row, col,row, col+1, "Under Warranty Closed",header_merge_format )
        col += 2
        sheet.write(row, col, job_card_closed_count_under_warranty or  '',header_merge_format_right)
        # sheet.write(row, col, f"{job_card_closed_count_under_warranty:,.2f}",header_merge_format_right)
        col += 1
        
        col += 1
        # sheet.write(row, col, "No of Jobs Repeated",header_merge_format)
        col += 2
      
        sheet.write(row, col, "Below 48 Hours", header_merge_format_left)
        col += 1
        sheet.write(row,col, f"{job_card_below_48_hour:,.2f}", header_merge_format_right )
        col += 2
        
        sheet.write(row,col,'S/P',header_merge_format_left)
        col +=1
       
        '''Code Added on March 30 2026 by Vijaya bhaskar client asked to Parts - Warranty Cost Column'''
        # sheet.write(row,col,f"{job_card_parts_amount:,.2f}",header_merge_format_right)

        sheet.write(row,col, f"{spare_parts_price:,.2f}",header_merge_format_right)
       
                 
        row += 1
        col = 0
        
        sheet.merge_range(row, col, row, col+1, 'Closed Job Card', header_merge_format_left)
        col += 2
        sheet.write(row, col, job_card_closed_count, header_merge_format_right)
        col += 2
        sheet.merge_range(row, col, row, col+1, "Not Warranty Closed", header_merge_format)
        col += 2
        sheet.write(row, col,job_card_closed_count_not_under_warranty or ' ', header_merge_format_right)

        # sheet.write(row, col,f"{job_card_closed_count_not_under_warranty:,.2f}", header_merge_format_right)
        col += 2
        # sheet.write(row, col, "Handed Over Completed",header_merge_format)
        col += 2
        sheet.write(row, col, 'Above 120 Hours',header_merge_format_left )
        col += 1
        sheet.write(row, col, f"{job_card_above_120_hour:,.2f}", header_merge_format_right)
        col += 2
        sheet.write(row,col,'SVC',header_merge_format_left)
        col +=1
        '''Code Commented on March 30 2026 by Vijaya bhaskar client asked to Parts - Warranty Cost Column '''
        # sheet.write(row,col,f"{job_card_service_amount:,.2f}",header_merge_format_right)
        sheet.write(row,col,f"{service_charge_warranty:,.2f}", header_merge_format_right)
        
     
        # sheet.write(row,col,  f"{total_jobs_count:,.2f}" , header_merge_format_right)

          
        row += 1
        col = 0
        sheet.merge_range(row,col, row,  col+1, "Cancel Job Card", header_merge_format_left)
        col += 2
        sheet.write(row,col,job_card_cancel_count, header_merge_format_right) 
        col += 6
        # sheet.write(row, col, "Handed Over Pending", header_merge_format)
        col += 2
          
        # sheet.merge_range(row,col,row, col+1,  "Total RTAT",header_merge_format)
        sheet.write(row, col, "Total RTAT", header_merge_format_left)
        col += 1
        total_rtat = int(total_rtat_hours)
        total_minute_rtat = int(round((total_rtat_hours - total_rtat) * 60))
        sheet.write(row, col, f"{total_rtat} H:{total_minute_rtat :02d} min" or ' ',  header_merge_format_right)
        # sheet.write(row, col, f"{total_rtat} H:{ total_minute_rtat :02d} min" or ' ',  header_merge_format_right)

        col +=2
        
        sheet.write(row, col, 'SVC Income', header_merge_format_left)
        col += 1
        sheet.write(row,col, f"{job_card_grand_total_amount:,.2f}", header_merge_format_right)
        # sheet.write(row,col,f"{job_card_cancel_count:,.2f}", header_merge_format_right) 
        
        row += 1
        col = 0
        sheet.merge_range(row, col, row, col+1, 'Total Job Card',  header_merge_format_left)
        col += 2
        sheet.write(row,col,  total_jobs_count , header_merge_format_right)
        col += 8
        
        avg_rtat = False
        avg_rtat_hours = False
        avg_rtat_min = False
        if job_card_closed_count != 0:
            avg_rtat = total_rtat_hours/job_card_closed_count
            
            avg_rtat_hours = int(avg_rtat)
            avg_rtat_min = int(round((avg_rtat - avg_rtat_hours)* 60))
            
        
        sheet.write(row, col, 'AVG RTAT', header_merge_format_left)
        col += 1
        if avg_rtat_hours and avg_rtat_min: 
            sheet.write(row, col, f"{avg_rtat_hours} H:{avg_rtat_min:02d} min", header_merge_format_right)
        else :
            sheet.write(row , col, "00 H:00 min", header_merge_format_right)    
        col += 2
        sheet.write(row, col, "Spare Parts Warranty", header_merge_format_left)
        col += 1
        sheet.write (row, col, f"{spare_parts_warranty:,.2f}", header_merge_format_right)
        
        '''Code Added on May 14 2026 by Vijaya Bhaskar client asked total free on qty'''
        
        row += 1
        col = 0
        sheet.merge_range(row, col, row, col+1, 'Total Freon Charge Qty',  header_merge_format_left)
        col += 2
        
        sheet.write(row,col,  total_service_qty , header_merge_format_right)
        
        
        
      
                
        if len(job_lst) == 0:
            raise ValidationError("Job Cards are not in this range")
    

