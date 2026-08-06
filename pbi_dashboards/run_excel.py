# -*- coding: utf-8 -*-
import sys
import odoo
from odoo.tools import config

config.parse_config([
    '-c', '/etc/odoo/odoo.conf',
    '-d', 'dbprod',
    '--db_host=db',
    '--db_user=odoo',
    '--db_password=odoo'
])

from odoo.addons.pbi_dashboards.generate_excel import generate_report

try:
    generate_report()
    print("SUCCESS: Excel report generated at /tmp/Service_Dashboards_Tally_Report.xlsx")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
