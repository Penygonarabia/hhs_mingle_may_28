# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Daily Attendance Report ',
    'summary': 'Report for Employee Daily Attendance Details',
    'sequence': 15,
    'author': 'Ceilo Resource',
    'description': """
        Daily Attendance Report
    """,
    'category': 'report',
    'depends' : ['hr','base','hr_attendances_overtime'],
    'data': [
        
           'security/ir.model.access.csv',
           "wizard/daily_attendance_report_views.xml",
           "report/report_daily_attendance_views.xml",
           "report/report_daily_attendance_pdf.xml",
           "report/report_attendance_pdf_template_views.xml",
      
             
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
