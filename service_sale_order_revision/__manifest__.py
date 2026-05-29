
{
    "name": "Service Sale Quotation Revision",
    "version": "17.0.1.0.0",
    "category": "Service Sales",
    "summary": """Revise and track the history of sales orders.""",
    "description": """This module helps users to create various revisions of
     sales order data and conveniently access all related order revisions.""",
    "author": "Raj Ganesh S",
    "company": "",
    "maintainer": "",
    "website": "",
    "depends": ["machine_repair_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/service_sale_order_views.xml",
        "wizards/service_sale_order_confirm_view.xml",
        "data/sequence.xml",
    ],
    "images": ["static/description/banner.jpg"],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": True,
}
