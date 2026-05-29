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
        'security/ir.model.access.csv',
        'security/security_groups.xml',
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
        # 'security/ir.model.access.csv',
        # 'views/res_config_settings_views.xml',
        # 'views/loyalty_points_views.xml',
        # 'views/loyalty_transaction_views.xml',
        # 'views/sale_order_views.xml',
        # 'views/account_move_views.xml',
        # 'views/promoter_showroom_sales_views.xml',
        # 'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
