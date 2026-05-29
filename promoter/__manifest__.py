{
    'name': 'Promoter Management',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Manage promoter assignments, dealers, and showrooms',
    'description': """
Promoter Management Module
==========================
This module allows you to:
- Mark partners as dealers or showrooms
- Assign promoters to showrooms
- Track showroom information and contact details
- Configure regions, districts, and cities
- Enhance res.partner views with custom fields and showroom tab
    """,
    'author': 'Ramesh Manivannan',
    'website': 'https://cielodigital.example.com',
    'depends': [
        'base',
        'contacts',
        'base_address_extended',
        'machine_repair_management',
        'partner_whatsapp',
        'hr',
        'hr_attendance',
    ],
    'data': [
    # Security Groups & Categories (safe to load early)
    'security/promoter_category.xml',
    'security/promoter_groups.xml',
    'security/ir.model.access.csv',

    # Load Views First (to register models before applying rules)
    'views/hr_employee_views.xml',
    'views/hr_attendance_view.xml',
    'views/res_partner_views.xml',
    'views/res_city_views.xml',
    'views/res_region_views.xml',
    # 'views/res_state_district_views.xml',
    'views/promoter_showroom_views.xml',
    'views/res_partner_hide_fields.xml',
    'views/promoter_assignment_views.xml',
    'views/promoter_showroom_sales_views.xml',
    'views/promoter_shop_status_views.xml',    
    'views/size_master_view.xml',
    'views/sales_target_views.xml',
    'views/sales_target_import_views.xml',
    # 'views/product_category_view.xml',
    # 'views/attendance_review_wizard_view.xml',
    'views/promoter_assignment_conflict_wizard_view.xml',
    'views/confirm_promoter_override_views.xml',

    # ✅ Add this line to load the new pivot view
    'views/vi_monthly_sales_target_views.xml',
    'views/res_config_settings_view.xml',

    # Now load the Record Rules (after models are known)
    'security/promoter_record_rules.xml',
],

    'assets': {
        'web.assets_backend': [
            'promoter/static/src/js/promoter_confirm.js',
            'promoter/static/src/css/custom.css',
            'promoter/static/src/css/pivot_fix.css',                                       
        ],
        'web.assets_frontend': [
            'promoter/static/src/css/custom.css',                  
        ],
    },

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
