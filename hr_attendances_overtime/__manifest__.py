# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    # Module information
    "name": "HR Attendance OverTime",
    "version": "17.0.1.0.0",
    "category": "Human Resources",
    "license": "LGPL-3",
    "summary": "This module manage employee Overtime and attendance details.",
    'sequence': 1,
    "description": """This module manage employee Overtime and attendance details.
                    HR Attendance OverTime
					HR Attendance Policies
					Odoo HR Attendance OverTime
					HR Attendance OverTime Odoo
					hr attendance sheet and policies 
					Human Resource Attendance Reports
					hr attendance policy
					hr policies for attendance
					hr policies on attendance
					hr attendance policy system
					hr attendance policy template    
					Attendance Policies
					hr attendance Rules
					hr attendance Sheet
					Employee Overtime
					Employee attendance
					Attendance OverTime
					Attendance Rules
					hr attendance
					Employee
					Attendance
					OverTime
					policies
					HR""",
    

    # Author
    "author": "Serpent Consulting Services Pvt. Ltd.",
    'website': 'http://www.serpentcs.com',

    # Dependencies
    "depends": [
                "hr_holidays", "hr_attendance", "om_hr_payroll", 'hr_contract',"hr","base","mail", "geomarking_attendance_mobile_app_knk"
    ],

    # Views
    "data": [
        "security/ir.model.access.csv",
        'data/hr_payroll_demo.xml',
        "data/attendance_batch_data.xml",
        "data/compute_attendance_data.xml",
        "data/attendance_sheet_scheduler.xml",
        "data/email_scheduler_data.xml",
        # "data/email_template.xml",
        "views/hr_contract.xml",
        "views/hr_overtime_view.xml",
        "views/hr_attendance_policies_view.xml",
        "views/hr_attendance_sheet_view.xml",
        "wizard/change_attendance_data_view.xml",
        "wizard/views_attendance_batches_wizard.xml",
        "views/hr_attendance_views.xml",
        "views/res_config_view.xml",
        # "data/late_in_email_template.xml",
        # "data/early_out_email_template.xml",
    ],
    
    # Odoo App Store Specific 
    'images': ['static/description/HR-Attendance-OverTime-Banner.png'],
    "live_test_url": "https://www.youtube.com/watch?v=0ayc26P8x9o",

    # Technical
    "installable": True,
    "auto_install": False,
    'price': 75,
    'currency': 'EUR',
}
