# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Employee Promotion",

    "author": "Softhealer Technologies",

    "license": "OPL-1",

    "website": "https://www.softhealer.com",

    "support": "support@softhealer.com",

    "version": "15.0.1",

    "category": "Human Resources",

    "summary": "HR Employee Promotion,Employee Promotion Management,Employee Promotion History,Promotion Employee,Employee Evaluation Management,Promotion Workflow history,Print Employee Promotion Report,Employee Promotion PDF,employee promotion log history Odoo",

    "description": """In every workplace promote to your employee is biggest factor. This module helps to manage the proper promotion process. You can manage the employee promotion flow and employee promotion history. You can print the promotion report with the promotion detail.""",

    "depends": [

            'hr_contract',
    ],

    "data": [

        'security/ir.model.access.csv',
        'security/sh_promotion_security.xml',
        'views/sh_hr_promotion.xml',
        'views/sh_promotion_types.xml',
        'reports/sh_hr_promotion_report.xml',


    ],

    "installable": True,
    "auto_install": False,
    "application": True,
    "images": ["static/description/background.png", ],
    "price": "25",
    "currency": "EUR"
}
