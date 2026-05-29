# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    "name" : "All in one Dynamic Approval | Sale Dynamic Approval | Purchase Dynamic Approval | Invoice Dynamic Approval",
    "version":"17.0.0.3",
    "category":"Extra Tools",
    "summary":"All in one Dynamic Approval on Invoice Dynamic Approval Purchase Dynamic Approval Sales Dynamic Approval based on model All dynamic approval all in one approval all in one multi approval all in one multi-level approval request dynamic approval request all",
    "description":"""

        Purchase and Sale Dynamic Approval Odoo App helps users to dynamic and multi level approvals for sales order, purchase order, payment and journal entry. User can configure dynamic approval which is based on minimum amount of total and before tax amount. Order should be approved by user and specific group. User can view email notification about approval and rejection of the order.

    """,
    "author": "BROWSEINFO",
    "price": 39,
    "currency": 'EUR',
    "website" : "https://www.browseinfo.com/demo-request?app=bi_all_in_one_dynamic_approval&version=17&edition=Community",
    "depends":["base", "sale_management", "purchase","account"],
    "data":[
        'security/security_access_data.xml',
        'security/ir.model.access.csv',
        'data/approval_email_template.xml',
        'wizard/sale_order_reject_views.xml',
        'wizard/purchase_order_reject_views.xml',
        'wizard/invoice_reject_views.xml',
        'wizard/account_payment_reject_views.xml',
        'views/approval_line_views.xml',
        'views/approval_views.xml',
        'views/model_approval_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_approved_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_payment_views.xml',
        'views/account_move_views.xml',
        ],
    'license':'OPL-1',
    "auto_install": False,
    "installable": True,
    "live_test_url":'https://www.browseinfo.com/demo-request?app=bi_all_in_one_dynamic_approval&version=17&edition=Community',
    "images":["static/description/Banner.gif"],
}
