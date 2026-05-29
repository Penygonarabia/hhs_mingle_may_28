# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    "name": "GeoMarking - Employee Attendance Mobile App",
    "version": "17.0.1.0",
    "category": "Human Resources",
    "license": "OPL-1",
    "website": "https://www.kanakinfosystems.com",
    "author": "Kanak Infosystems LLP.",
    "summary": """
        geomarking mobile app
        employee attendance
        mobile app for employee attendance
        employee attendance tracker app
        employee time tracker app
        employee attendance tracker
        app for attendance tracking
        employee mobile app
        employee attendance record
        employee attendance system
        employee attendance tracker free
        app for employee attendance
        how to track employee attendance
        employee attendance management system
        employee attendance monitoring system
        employee attendance mobile application
        mobile app for attendance tacking
        mobile app tracking
        geomarking
        employee attendance tracker
        geomarking employee attendance app
        employee attendance mobile app
        attendance tracking
        apps to track attendance
        biometric attendance system
        attendance tracker apps
        employee attendance sheet
        employee attendance calendar
        odoo attendance mobile app
        employee location tracking app
        track employee
        employee tracking app
    """,
    "description": "This app contains API that connects GeoMarking app to server for its working.",
    "images": ["static/description/banner/Geomarking.gif"],
    "depends": [
        "hr",
        "hr_attendance",
        "portal",
        "base_geolocalize",
        "hr_holidays_attendance",
        "mail",
        "hr_timesheet",
        "om_hr_payroll",
        # "hrms_salary_al_dt",
        'hr_saudi',
        "base"
       
    ],
    "data": [
        # "security/security.xml",
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "report/attendance_pdf.xml",
        "views/all_db_view.xml",
        "views/views.xml",
        "views/hr_attendance.xml",
        "views/inherit_res_users_form_view.xml",
        "views/account_removal_request.xml",
        "views/removal_request_reason.xml",
        "views/attendance_request.xml",
        "views/geomarking_menuitem.xml",
    ],
    "auto_install": False,
    "installable": True,
    "price": 439,
    "currency": "USD",
    "live_test_url": "https://www.youtube.com/watch?v=XyscaDo2RrY&t=332s",
}
