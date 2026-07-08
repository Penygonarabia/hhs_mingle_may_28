{
    'name': 'Loyalty Management',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Manage customer loyalty points and transactions with a feature toggle.',
    'description': """
Loyalty Management Module
=========================
Features:
- Enable/Disable Loyalty Program from Settings.
- Customer Loyalty Points tracking.
- Loyalty Transaction history (Earn/Redeem).
- Integration with Sales and Invoicing.
    """,
    'author': 'Kartheeswaran A',
    'depends': ['base', 'product', 'stock', 'sale', ],
    'data': [
        'data/sequence_creation.xml',
        'data/tier_icons_data.xml',
        'security/ir.model.access.csv',
        'views/views_loyalty_tier_icon.xml',
        'views/views_res_config_settings.xml',
        'views/views_customer_tier.xml',
        'views/views_manual_promotion_reason_types.xml',
        'views/views_loyalty_points_history_tab.xml',
        'views/views_customer_loyalty_tab.xml',
        'views/views_enter_manual_promotion_points.xml',
        'views/views_promotion_setup.xml',
        'wizard/promotion_report_wizard_views.xml',
        'report/report_promotion.xml',
        'views/views_process_tier.xml',
        'views/loyalty_audit_view.xml',
        'views/loyalty_points_summary_wizard_view.xml',
        'wizard/customer_list_report_wizard_view.xml',
        'report/customer_list_report.xml',
        # 'views/loyalty_menu.xml',
        'wizard/promotion_report_wizard_views.xml',
        'wizard/customer_statement_wizard_view.xml',
        'report/customer_statement_report.xml',
        'report/customer_statement_templates.xml',
        'report/report_promotion.xml',
        'report/report_promotion_detailed.xml',
        'views/views_sales_table_view.xml',
        'views/promotion_participation_views.xml',
        'data/cron_job_customer_list.xml',
        'data/customer_statement_cron.xml',
        'data/process_tier_cron.xml',
        'views/customer_notification_views.xml',
        # 'report/loyalty_points_summary_report.xml',
        # 'report/loyalty_points_summary_template.xml',
        # 'security/ir.model.access.csv',
        # 'views/res_config_settings_views.xml',
        # 'views/loyalty_points_views.xml',
        # 'views/loyalty_transaction_views.xml',
        # 'views/sale_order_views.xml',
        # 'views/account_move_views.xml',
        # 'views/promoter_showroom_sales_views.xml',
        # 'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hhs_loyalty_management/static/src/css/tier_icon_picker.css',
            'hhs_loyalty_management/static/src/js/tier_icon_picker.js',
            'hhs_loyalty_management/static/src/xml/tier_icon_picker.xml',
        ]
    },
    'installable': True,
    'application': True,
}
