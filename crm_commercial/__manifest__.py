# -*- coding: utf-8 -*-
{
    'name': 'CRM Commercial',
    'version': '17.0.1.0.0',
    'category': 'CRM Commercial',
    'summary': 'Commercial CRM for project leads, quotations, sale orders, multi-level approvals, costing and pipeline reports.',
    'description': """
        CRM Commercial Module for HHS.
        - Master Configurations: Terms & Conditions, User Rights, Masters.
        - Product Categories: Excluded categories, Default Discount, Payment/Warranty/Salient Features.
        - Products: Non-stock imports, Discontinued tracking, Item Approvals, Long description.
        - Leads: Single-page form, duplicate customer check, auto-approval.
        - Quotations: Costing Summary (Gross Margin, Net Price, DSI, SMC, Promo),
                      Multi-tab layout, Cost validation, Excel import, Copy & Revision.
        - Sale Orders: Multiple Delivery Schedules, Expiry extension audit, Actual Gross Margin.
        - Approvals: Multi-level & salesman-wise via Approval Configurations.
        - Reports: Quotation PDF (row-wise VAT toggle), Pipeline Excel, Sales Order Pivot.
        - Crons: Weekly reminders, User inactivity locking, Order expiry notifications.
    """,
    'author': 'CIELO ERP',
    'website': 'https://hh-shaker.com.sa',
    'depends': [
        'base',
        'mail',
        'crm',
        'sale',
        'stock',
        'bi_all_in_one_dynamic_approval',
        'report_xlsx',
        'hhs_loyalty_management',
        'machine_repair_management',
    ],
    'data': [
        # Security - groups first, record rules last (after models)
        'security/crm_commercial_security.xml',
        'security/ir.model.access.csv',
        # Sequences and Crons
        'data/crm_commercial_sequence.xml',
        'data/crm_commercial_cron.xml',
        # Settings & User extensions
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        # Masters
        'views/masters_views.xml',
        # Product extensions
        'views/product_category_views.xml',
        'views/product_views.xml',
        # Wizard views (actions defined here, referenced by transaction screens)
        'wizard/import_non_stock_wizard_views.xml',
        'wizard/import_material_list_wizard_views.xml',
        'wizard/expiry_extension_wizard_views.xml',
        # Item approvals
        'views/item_approval_views.xml',
        # Transaction screens
        'views/crm_commercial_lead_views.xml',
        'views/crm_commercial_quotation_views.xml',
        'views/crm_commercial_sale_order_views.xml',
        # Report pivot/graph views
        'views/sales_order_analysis_views.xml',
        # Menu (last, after all actions are defined)
        'views/menu_views.xml',
        # Record rules (after models are in DB)
        'security/crm_commercial_record_rules.xml',
        # PDF Reports
        'reports/quotation_pdf_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_commercial/static/src/css/rtl_support.css',
            'crm_commercial/static/src/js/rtl_support.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
