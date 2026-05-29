# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "All in one Accounting Reports",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "license": "LGPL-3",
    "category": "Accounting",
    "summary": "Customer Invoice Analysis Report Invoice By Product Category Report Invoice Details Report Product Profit Report By Sales Person Invoice Indent Report Top Customer Invoices Top Vendor Bill Product Invoice Summary Report All In One Invoice",
    "description":  """All in one accounting report useful to provide different reports to do analysis. This module includes 9 different reports.""",
    # "version": "17.0.2",
    "depends": [
                "account","base","invoice_cost_price"
    ],
    "application": True,
    "data": [
        "sh_customer_invoice_analysis/security/ir.model.access.csv",
        'sh_customer_invoice_analysis/wizard/customer_invoice_analysis_wizard.xml',
        'sh_customer_invoice_analysis/report/report_customer_invoice_analysis.xml',

        'sh_invoice_by_category/security/ir.model.access.csv',
        'sh_invoice_by_category/wizard/invoice_by_category_wizard.xml',
        'sh_invoice_by_category/report/report_invoice_by_category.xml',

        'sh_invoice_details_report/security/ir.model.access.csv',
        'sh_invoice_details_report/wizard/invoice_details_report_wizard.xml',
        'sh_invoice_details_report/report/invoice_details_report.xml',

        'sh_invoice_product_profit/security/ir.model.access.csv',
        'sh_invoice_product_profit/wizard/invoices_product_profit_wizard.xml',
        'sh_invoice_product_profit/report/report_invoices_product_profit.xml',

        'sh_invoice_report_salesperson/security/ir.model.access.csv',
        'sh_invoice_report_salesperson/wizard/report_salesperson_wizard.xml',
        'sh_invoice_report_salesperson/report/invoice_salesperson_report.xml',

        'sh_invoice_summary/security/ir.model.access.csv',
        'sh_invoice_summary/wizard/invoice_summary_wizard.xml',
        'sh_invoice_summary/report/report_invoice_summary.xml',

        'sh_product_invoice_indent/security/ir.model.access.csv',
        'sh_product_invoice_indent/wizard/invoice_product_indent_wizard.xml',
        'sh_product_invoice_indent/report/report_invoice_product_indent.xml',

        'sh_top_customers_invoice/security/ir.model.access.csv',
        'sh_top_customers_invoice/wizard/top_customer_invoice_wizard.xml',
        'sh_top_customers_invoice/report/top_customer_invoice_report.xml',

        'sh_top_invoice_product/security/ir.model.access.csv',
        'sh_top_invoice_product/wizard/top_invoicing_wizard.xml',
        'sh_top_invoice_product/report/tip_invoicing_product_report.xml',
        'sh_top_invoice_product/views/top_invoicing_view.xml',

    ],
    "auto_install": False,
    "installable": True,
    "images": ["static/description/background.png", ],
    "price": "100",
    "currency": "EUR",
  
}
