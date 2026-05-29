# -*- coding: utf-8 -*-
{
    'name': "Employee Leave Entry",
    'summary': """
       Employee Leave Entry""",
    'description': """
         Employee Leave Entries 
    """,
    'author': "Cielo Digital Solutions Pvt.Ltd",
    
    'category': 'Uncategorized',
    'version': '17.1',
    'depends': ['base','web', 'hr', 'hr_contract', 'hr_holidays','hr_attendance','hr_attendances_overtime'],
    'data': [
         'security/ir.model.access.csv',
        'wizard/leave_entry_views.xml',
         # 'views/views_res_config_settings.xml',
        
    ],
    'assets': {
    # 'web.assets_backend': [
    #     'leave_entry/static/src/js/colored_field_widget.js',
    #     # 'leave_entry/static/src/css/color.css',
    #     # 'leave_entry/static/src/js/hide_empty_columns.js'
    # ],
    },

    
    'license': 'LGPL-3',
     'installable': True,
    'auto_install': False,
}
