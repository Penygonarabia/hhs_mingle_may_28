import psycopg2
conn = psycopg2.connect('dbname=hhs_staging_phase1_local')
conn.autocommit = True
cur = conn.cursor()
cur.execute("DELETE FROM ir_act_window_view WHERE act_window_id IN (SELECT id FROM ir_act_window WHERE name='Approve Shop Sales')")
print(f"Deleted {cur.rowcount} act_window_view records.")
