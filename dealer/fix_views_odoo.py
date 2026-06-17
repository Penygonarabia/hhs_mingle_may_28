import sys
import os

odoo_path = r"D:\Odoo17\odoo-17.0"
if odoo_path not in sys.path:
    sys.path.append(odoo_path)

import odoo

def fix_db():
    odoo.tools.config.parse_config(['-c', r'D:\Odoo17\odoo-17.0\odoo.conf'])
    registry = odoo.registry('hhs_staging_phase1_local')
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        action = env['ir.actions.act_window'].search([('name', '=', 'Approve Shop Sales')])
        if action:
            views = env['ir.actions.act_window.view'].search([('act_window_id', 'in', action.ids)])
            views.unlink()
            print(f"Deleted {len(views)} act_window_view records.")
            cr.commit()

if __name__ == "__main__":
    fix_db()
