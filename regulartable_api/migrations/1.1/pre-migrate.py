def migrate(cr, version):
    if not version:
        return
    
    # Tables and columns that are being converted to Many2one
    # We must clear non-integer values (like '*') before Odoo attempts to ALTER TYPE
    updates = {
        'transaction_header': [
            'trnh_partner_id', 'trnh_cityid', 'trnh_regionid', 'trnh_smanid', 'trnh_rptregionid'
        ],
        'transaction_details': [
            'trnd_productid', 'trnd_categoryid', 'trnd_groupid', 'trnd_subgroupid'
        ]
    }
    
    for table, columns in updates.items():
        # Check if table exists
        cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = %s", (table,))
        if not cr.fetchone():
            continue
            
        for col in columns:
            # Check if column exists and is character varying or text
            cr.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s 
                AND data_type IN ('character varying', 'text')
            """, (table, col))
            if cr.fetchone():
                # Set invalid non-integer strings to NULL to avoid InvalidTextRepresentation error
                cr.execute(f"UPDATE {table} SET {col} = NULL WHERE {col} IS NOT NULL AND {col} !~ '^[0-9]+$'")
