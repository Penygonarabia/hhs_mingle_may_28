# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software PVT. LTD.
# See LICENSE file for full copyright & licensing details.

# Author: Aktiv Software PVT. LTD.
# mail: odoo@aktivsoftware.com
# Copyright (C) 2015-Present Aktiv Software PVT. LTD.
# Contributions:
#   Aktiv Software:
#       - Geet Thakar
#       - Shivam Kachhia
#       - Tanvi Gajera

{
    "name": "Internal Material Request / Inter-Warehouse Request",
    "version": "17.0.1.0.0",
    "summary": """This module allows Warehouse users to create Internal Material Requests.
    Internal Warehouse Transfer,
    Stock Request,
    Goods Request,
    2-Step Delivery Requests with Transit Location,
    Inter-Warehouse Transfer,
    Inter Warehouse Transfer,
    Material Request,
    Internal Request,
    Stock Request,
    Goods Request,
    Transit Request,
    Goods Transfer,
    Stock Transfer,
    Material Transfer,
    Warehouse Transfer,
    Internal Warehouse Transfer,
    Goods Transfer between Warehouse,
    Stock Transfer between Transfer,
    Warehouse to Warehouse Transfer,
    """,
    "description": """
        Title: Internal Material Request / Inter-Warehouse Request \n
        Author: Aktiv Software PVT. LTD. \n
        mail: odoo@aktivsoftware.com \n
        Copyright (C) 2015-Present Aktiv Software PVt. LTD. \n
        Contributions: Aktiv Software:  \n
            - Janvi Raval
            - Komal Jimudiya
            - Burhan Vakharia
            - Tanvi Gajera
        This module allows users to create Internal material request request
        to any internal stock location.
        It allows users to create Inter-Warehouse Requests.
        The requests can be 1-Step or 2-Step Requests.
        2-Step Requests are routed via a Transit Location.
        Material Request,
        Internal Request,
        Stock Request,
        Goods Request,
        Transit Request,
        Goods Transfer,
        Stock Transfer,
        Material Transfer,
        Warehouse Transfer,
        Internal Warehouse Transfer,
        Goods Transfer between Warehouse,
        Stock Transfer between Transfer,
        Warehouse to Warehouse Transfer,
    """,
    "author": "Aktiv Software",
    "website": "http://www.aktivsoftware.com",
    "license": "LGPL-3",
    "price": 18.00,
    "currency": "EUR",
    "category": "Inventory",
    "depends": ["base","stock", "point_of_sale", "stock_analytic"],
    "data": [
        "security/ir.model.access.csv",
        "data/material_request_sequence.xml",
        "data/mail_template.xml",
        "wizard/reject_reason_wizard_views.xml",
        "wizard/transit_location_wizard.xml",
        "wizard/request_report_wizard_views.xml",
        "views/material_request_view.xml",
        "views/res_config_views.xml",
        "views/res_company_views.xml",
        'views/stock_picking_views.xml',
        "report/report_stock_transfer_request.xml",
        "report/request_document_pdf.xml",
    ],
    "images": ["static/description/banner.jpg"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
