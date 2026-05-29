{
    'name': 'Dealer Management',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Manage dealer assignments, dealers, and showrooms',
    'description': """
Dealer Management Module
==========================
This module allows you to:
- Mark partners as dealers or showrooms
- Assign dealers to showrooms
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
        'promoter',
    ],
    'data': [
    # Security Groups & Categories (safe to load early)   
    'security/dealer_groups.xml',
    'security/ir.model.access.csv',
    'views/dealer_showroom_views.xml',
    # Action for the filter wizard    
    'views/fsm_loyalty_audit_stmt_filter_wizard_views.xml',
    'views/fsm_loyalty_audit_filter_Summary_wizard.xml',
    # Load Views First (to register models before applying rules)
    # 'views/hr_employee_views.xml',
    'views/res_partner_views.xml',
    # 'views/res_city_views.xml',
    # 'views/res_region_views.xml',    
    # 'views/res_partner_hide_fields.xml',
    'views/dealer_assignment_views.xml',
    'views/dealer_showroom_sales_views.xml',
    'views/dealer_shop_status_views.xml',    
    'views/size_master_view.xml',
    'views/sales_target_views.xml',
    'views/sales_target_import_views.xml',
    'views/res_users_view.xml',
    'views/fsm_loyalty_audit_view.xml',
    'views/fsm_loyalty_audit_pivot.xml',
    'views/fsm_loyalty_redemption_view.xml',  
    'views/product_view.xml',
    # 'views/confirm_dealer_override_views.xml',

    # ✅ Add this line to load the new pivot view
    'views/vi_monthly_sales_target_views.xml',
    'views/res_config_settings_view.xml',
    'report/fsm_loyalty_redemption_report.xml',
],

    'assets': {
        'web.assets_backend': [
            # 'dealer/static/src/js/dealer_confirm.js',
            # 'dealer/static/src/css/custom.css',
            # 'dealer/static/src/css/pivot_fix.css',   
            'dealer/static/src/js/hide_user_menu.js',                                    
        ],
        'web.assets_frontend': [
            'dealer/static/src/css/custom.css',                  
        ],
    },

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}