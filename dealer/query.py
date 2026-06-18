import sys

sales = env['dsales.showroom.sales'].search([('invoice_no', 'ilike', 'Inv2002')], limit=5)
print(f"Found {len(sales)} sales")
for sale in sales:
    print(f"Sale ID: {sale.id}, Invoice: '{sale.invoice_no}', State: {sale.state}")
    for line in sale.line_ids:
        print(f"  Line {line.id}: product={line.product_id.name}, qty={line.qty}, categ={line.product_category_id.id}, group={line.product_group_id.id}, subgroup={line.product_subgroup_id.id}")
    
    audits = env['fsm.loyalty.audit'].search([('sales_id', '=', sale.id)])
    print(f"  Audits by sales_id: {audits}")
    
    if sale.dealer_id:
        env.cr.execute(f"SELECT dealer_id, sales_qty, year, month FROM vi_monthly_sales_target_dealer WHERE sales_qty > 0 AND dealer_id = {sale.dealer_id.id}")
        targets = env.cr.fetchall()
        print(f"  Targets: {targets}")
