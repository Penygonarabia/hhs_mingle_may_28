# -*- coding: utf-8 -*-
#################################################################################
# Author      : CFIS (<https://www.cfis.store/>)
# Copyright(c): 2017-Present CFIS.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.cfis.store/>
#################################################################################

{
    "name": "Organization Chart | OrgChart | Org Chart | Employee Hierarchy | Employee Chart",
    "summary": """
        This module allows the hr users to quickly view the Employee Hierarchy using the existing Employee master, 
        also the HR Manager will get the options for drag and drop, create , edit and delete options from the chart itself.
        """,
    "version": "17.1",
    "description": """
        This module allows the hr users to quickly view the Employee Hierarchy using the existing Employee master, 
        also the HR Manager will get the options for drag and drop, create , edit and delete options from the chart itself.
        Organization Chart
        OrgChart
        Org Chart
        Employee Hierarchy
        Employee Chart
        """,    
    "author": "CFIS",
    "maintainer": "CFIS",
    "license" :  "Other proprietary",
    "website": "https://www.cfis.store",
    "images": ["images/organization_chart.png"],
    "category": "Extra Tools",
    "depends": [
        "base",
        "hr",
   
    ],
    "data": [
        "views/orgchart_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
      		"/organization_chart/static/src/libs/jspdf_min.js",
          	"/organization_chart/static/src/libs/html2canvas_min.js",           
           	"/organization_chart/static/src/libs/jquery.orgchart.js",
            "/organization_chart/static/src/libs/jquery.orgchart.css",           
			"/organization_chart/static/src/js/org_chart_employee.js",
          	"/organization_chart/static/src/css/style.css",
            "/organization_chart/static/src/xml/org_chart_employee.xml",
        ],
    },
    "installable": True,
    "application": True,
    "price"                 :  22,
    "currency"              :  "EUR",
}