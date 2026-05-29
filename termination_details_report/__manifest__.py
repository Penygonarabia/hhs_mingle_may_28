# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Termination Details Report',
    'summary': 'Report for Termination Details',
    'sequence': 15,
    'license': 'LGPL-3',
    'description': """
        Termination Details Report
    """,
    'category': 'report',
    'depends' : ['hr','base','hr_exit_process','report_xlsx','hr_end_service_benefits'],
    'data': [
        
        
          'security/ir.model.access.csv',
          "wizard/views_termination_details_report.xml",
          "wizard/termination_details_template.xml",
          "report/report_termination_details_xlsx.xml",
      
             
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
