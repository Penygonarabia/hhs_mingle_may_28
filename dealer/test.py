import psycopg2
conn = psycopg2.connect('dbname=hhs_staging_phase1_local user=odoo password=odoo host=localhost')
cur = conn.cursor()
cur.execute("SELECT id, purchase_date FROM registration_form WHERE purchase_date IS NOT NULL AND purchase_date !~ '^[12][0-9]{3}-[01][0-9]-[0-3][0-9]'")
print(cur.fetchall())
