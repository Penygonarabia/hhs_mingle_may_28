# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Employee Document Renewal Report ',
    'summary': 'Report for renewal Employee Details',
    'sequence': 15,
    'license': 'LGPL-3',
    'author': 'Penygonarabia',
    'description': """
        Employee Document Renewal Report
    """,
    'category': 'report',
    'depends' : ['hr','base','om_hr_payroll','report_xlsx'],
    'data': [
        
           'security/ir.model.access.csv',
          "wizard/views_employee_documents_renewal.xml",
          "report/report_employee_renewal_xlsx.xml",
          'report/report_employee_renewal_pdf_report.xml',
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
