import sys
sys.path.append('D:\\Odoo17\\odoo-17.0')
import odoo
odoo.tools.config.parse_config(['-c', 'D:\\Odoo17\\odoo-17.0\\odoo.conf'])
registry = odoo.registry('hhs_staging_phase1_local')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, 1, {})
    try:
        # Check if it's a table or view
        cr.execute("SELECT table_type FROM information_schema.tables WHERE table_name = 'customer_loyalty_points_history'")
        res = cr.fetchone()
        print('Type:', res)
        
        if res and res[0] == 'VIEW':
            print("It's a view! We can't simply add a column.")
            # Drop it? Or maybe we can just query the definition.
            cr.execute("SELECT pg_get_viewdef('customer_loyalty_points_history')")
            print('ViewDef:', cr.fetchone()[0])
        elif res and res[0] == 'BASE TABLE':
            print("It's a table. Adding id column...")
            cr.execute("ALTER TABLE customer_loyalty_points_history ADD COLUMN id SERIAL PRIMARY KEY;")
            print("Added id column successfully!")
        else:
            print("Table not found!")
    except Exception as e:
        print("Error:", e)
