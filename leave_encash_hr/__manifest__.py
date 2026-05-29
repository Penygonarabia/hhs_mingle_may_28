{
    'name': 'Leave Encashment ',
    'category': 'HR',
    'description': """
                  Encashment of Leave
                 """,
    'summary': 'Management of Leave Encashment',
    'author': 'PenygonArabia',
    'version': '17.0.1.2',
    'license': 'LGPL-3',

    'depends': ['base', 'stock', 'account',
                'hr', 'hr_attendance',
                'hr_contract', 'om_hr_payroll','hr_holidays','hr_saudi'
                ],
    
    'data': [
        
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/views_leave_encash.xml',
        # 'views/hr_job_views.xml',
        # 'views/leave_config_setting_views.xml',
        'views/hr_payroll_views.xml',
        # 'views/hr_payroll_data.xml',
        'views/hr_leave_type_views.xml',
        'wizard/views_leave_encash_wizard.xml',
        'report/report_leave_encash_excel.xml',
        'report/report_leave_encash_pdf.xml',

    ],
    
    'installable': True,
    'auto_install': False,
}


