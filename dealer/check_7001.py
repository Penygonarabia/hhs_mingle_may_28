import sys
sys.path.append('D:\\Odoo17\\odoo-17.0')
import odoo
from odoo import api, SUPERUSER_ID

def run():
    odoo.tools.config.parse_config(['-c', 'D:\\Odoo17\\odoo-17.0\\odoo.conf'])
    registry = odoo.registry('hhs_staging_phase1_local')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        sales = env['dsales.showroom.sales'].search([('invoice_no', '=', '7001')])
        if not sales:
            print("Invoice 7001 not found.")
            return
        
        print(f"Found Invoice 7001. State: {sales.state}")
        
        # Trigger a dummy write to force the sync logic
        # We need to include 'state' in vals because our if condition checks for it
        # Wait, the if condition is: any(k in vals for k in ['line_ids', 'qty', 'is_sales_return', 'dealer_id', 'date_time', 'notes', 'state'])
        sales.write({'state': sales.state})
        print("Triggered write.")
        
        # Check if audit records were created
        audits = env['fsm.loyalty.audit'].search([('reference', '=', '7001')])
        print(f"Audits found: {len(audits)}")
        for a in audits:
            print(f"- Audit: qty={a.qty}, points={a.loyalty_points}")

if __name__ == '__main__':
    run()
