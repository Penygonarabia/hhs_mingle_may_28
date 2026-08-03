import sys
env.cr.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'dsales_showroom_sales' AND column_name IN ('year', 'month')")
print(env.cr.fetchall())
env.cr.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'dealer_sales_target' AND column_name IN ('year', 'month')")
print(env.cr.fetchall())
