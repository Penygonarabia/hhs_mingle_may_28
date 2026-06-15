#!/usr/bin/env python3
"""
migrate_amc_to_dbcloud.py
=========================
Migrate 518 AMC quotation records (and their dependencies) from dbcloud_new
into dbcloud so that dbcloud becomes the single authoritative database.

What this script does, in order:
  1. Backup dbcloud (pg_dump to /tmp/dbcloud_backup_<ts>.dump)
  2. Add missing columns to service_sale_order in dbcloud
  3. Add missing columns to crm_lead in dbcloud
  4. Copy 8 missing products (product_template + product_product) into dbcloud
  5. Copy 88 CRM leads into dbcloud  (offset IDs +10000)
  6. Copy 518 AMC service_sale_orders  (offset IDs +10000)
  7. Copy 734 service_sale_order_lines  (offset IDs +10000)
  8. Update PostgreSQL sequences so future inserts don't collide

ID strategy:
  All inserted records get id = (old id in dbcloud_new) + ID_OFFSET (10000).
  This avoids collision because dbcloud's max service_sale_order id is 255
  and dbcloud_new's max is 656, so offset IDs start at 10001 and are safe.

User mapping:
  Users with the same login in both DBs keep their IDs (they happen to match).
  Users that only exist in dbcloud_new are mapped to admin (id=2).

FK columns that are kept as-is (IDs match between DBs):
  warehouse_id, work_center_id, work_center_group_id, payment_term_id,
  partner_id (in crm_lead), stage_id, country_id, state_id, company_id.

FK columns that are nulled (table not in dbcloud or too complex to map):
  current_waiting_approval_line_id, contract_id, approval_level_id,
  service_sale_approval_id, job_task_id.
"""

import subprocess
import sys
import time
from datetime import datetime

import json

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2.extras import Json as PgJson
except ImportError:
    print("ERROR: psycopg2 not available. Run: pip3 install psycopg2-binary")
    sys.exit(1)

# ── connection params ─────────────────────────────────────────────────────────
DSN_SOURCE = "host=localhost port=5434 dbname=dbcloud_new user=odoo password=odoo"
DSN_TARGET = "host=localhost port=5434 dbname=dbcloud      user=odoo password=odoo"
ID_OFFSET  = 10_000   # added to every imported id to avoid collisions

# ── helpers ───────────────────────────────────────────────────────────────────
def log(msg):
    print(f"  {msg}")

def step(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def run(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"ERROR running: {cmd}\n{r.stderr}")
        sys.exit(1)
    return r.stdout.strip()

def cols_in_table(cur, table):
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
    """, (table,))
    return {r[0] for r in cur.fetchall()}

def add_column_if_missing(cur, table, col, col_type):
    cur.execute(f"""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s AND column_name=%s
    """, (table, col))
    if not cur.fetchone():
        log(f"  ADD COLUMN {table}.{col} {col_type}")
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}')

def offset_id(val):
    return (val + ID_OFFSET) if val is not None else None

def adapt_value(v):
    """Convert Python dicts/lists (from JSONB columns) to psycopg2 Json wrapper."""
    if isinstance(v, (dict, list)):
        return PgJson(v)
    return v

def adapt_row(row):
    return [adapt_value(v) for v in row]

_fk_map_cache = {}

def get_fk_map(cur, table):
    """Return dict: column_name → foreign_table for all FKs on table. Cached."""
    if table not in _fk_map_cache:
        cur.execute("""
            SELECT kcu.column_name, ccu.table_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name
            WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_name=%s
        """, (table,))
        _fk_map_cache[table] = {r[0]: r[1] for r in cur.fetchall()}
    return _fk_map_cache[table]

# Cache of valid ID sets per table (populated lazily — loads ALL IDs at once)
_valid_ids_cache = {}

def get_valid_ids(cur, table):
    """Return set of all IDs in `table`. Loads entire table's IDs once and caches."""
    if table not in _valid_ids_cache:
        cur.execute(f"SELECT id FROM {table}")
        _valid_ids_cache[table] = {r[0] for r in cur.fetchall()}
    return _valid_ids_cache[table]

def safe_row(dc, table, row_dict, always_null=None, skip_cols=None):
    """
    Null out FK column values that don't exist in the destination DB.
    Uses a per-table ID set (loaded once) for O(1) membership checks.
    """
    fk_map = get_fk_map(dc, table)
    always_null = always_null or set()
    skip_cols = skip_cols or {'id'}
    result = {}
    for col, val in row_dict.items():
        if col in always_null:
            result[col] = None
        elif col in skip_cols:
            result[col] = val
        elif col in fk_map and val is not None:
            ref_table = fk_map[col]
            valid_ids = get_valid_ids(dc, ref_table)
            result[col] = val if val in valid_ids else None
        else:
            result[col] = val
    return result

# ── user map ──────────────────────────────────────────────────────────────────
def build_user_map(src_cur, dst_cur):
    src_cur.execute("SELECT id, login FROM res_users")
    src_users = {r[0]: r[1] for r in src_cur.fetchall()}
    dst_cur.execute("SELECT login, id FROM res_users")
    dst_logins = {r[0]: r[1] for r in dst_cur.fetchall()}
    user_map = {}
    for uid, login in src_users.items():
        user_map[uid] = dst_logins.get(login, 2)   # fall back to admin
    return user_map

# ─────────────────────────────────────────────────────────────────────────────
def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Step 1: Backup ────────────────────────────────────────────────────────
    step("Step 1: Backup dbcloud")
    backup_path = f"/tmp/dbcloud_backup_{ts}.dump"
    log(f"Writing backup to {backup_path} ...")
    r = subprocess.run(
        f"docker exec cloud-db-1 pg_dump -U odoo -Fc dbcloud",
        shell=True, capture_output=True
    )
    if r.returncode != 0:
        print(f"ERROR: pg_dump failed: {r.stderr.decode()}")
        sys.exit(1)
    with open(backup_path, "wb") as f:
        f.write(r.stdout)
    size_mb = len(r.stdout) / 1024 / 1024
    log(f"Backup complete: {size_mb:.1f} MB")

    # ── Connect ───────────────────────────────────────────────────────────────
    src = psycopg2.connect(DSN_SOURCE)
    dst = psycopg2.connect(DSN_TARGET)
    src.autocommit = False
    dst.autocommit = False
    sc = src.cursor(cursor_factory=psycopg2.extras.DictCursor)
    dc = dst.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # ── Step 2: Add missing columns to service_sale_order ────────────────────
    step("Step 2: Add missing columns to dbcloud.service_sale_order")
    missing_sso_cols = [
        ("annual_quotation_value",   "NUMERIC"),
        ("enable_scope",             "BOOLEAN DEFAULT false"),
        ("exclusions_text",          "TEXT"),
        ("is_revised",               "BOOLEAN DEFAULT false"),
        ("late_payment_note",        "TEXT"),
        ("org_sale_id",              "INTEGER"),
        ("others",                   "CHARACTER VARYING"),
        ("others_text",              "TEXT"),
        ("payment_frequency_text",   "CHARACTER VARYING"),
        ("rev_confirm",              "BOOLEAN DEFAULT false"),
        ("scope_of_work",            "CHARACTER VARYING"),
        ("service_sale_approval_id", "INTEGER"),
        ("sp_gross_margin",          "DOUBLE PRECISION"),
        ("subject",                  "CHARACTER VARYING"),
        ("terms_of_execution",       "TEXT"),
    ]
    for col, typ in missing_sso_cols:
        add_column_if_missing(dc, "service_sale_order", col, typ)
    dst.commit()

    # ── Step 3: Add missing columns to crm_lead ───────────────────────────────
    step("Step 3: Add missing columns to dbcloud.crm_lead")
    missing_crm_cols = [
        ("type_of_property",                    "CHARACTER VARYING"),
        ("warehouse_id",                         "INTEGER"),
        ("work_center_id",                       "INTEGER"),
        ("work_center_group_id",                 "INTEGER"),
        ("district",                             "INTEGER"),
        ("customer_code",                        "CHARACTER VARYING"),
        ("job_position",                         "CHARACTER VARYING"),
        ("property_type_maintenance_details_id", "INTEGER"),
        ("company_preventive_maintenance",       "CHARACTER VARYING"),
        ("company_preventive_maintenance_bool",  "BOOLEAN DEFAULT false"),
    ]
    for col, typ in missing_crm_cols:
        add_column_if_missing(dc, "crm_lead", col, typ)
    dst.commit()

    # ── Step 4: Copy 8 missing products ──────────────────────────────────────
    step("Step 4: Copy missing products into dbcloud")
    MISSING_PRODUCT_IDS = [44040, 55200, 42676, 44051, 55198, 55201, 55202, 55199]

    # Get columns that exist in both product_template tables
    sc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='product_template' ORDER BY ordinal_position")
    src_pt_cols = [r[0] for r in sc.fetchall()]
    dc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='product_template' ORDER BY ordinal_position")
    dst_pt_cols_set = {r[0] for r in dc.fetchall()}
    common_pt_cols = [c for c in src_pt_cols if c in dst_pt_cols_set]

    sc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='product_product' ORDER BY ordinal_position")
    src_pp_cols = [r[0] for r in sc.fetchall()]
    dc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='product_product' ORDER BY ordinal_position")
    dst_pp_cols_set = {r[0] for r in dc.fetchall()}
    common_pp_cols = [c for c in src_pp_cols if c in dst_pp_cols_set]

    # Fetch templates needed
    sc.execute(f"""
        SELECT pt.* FROM product_template pt
        JOIN product_product pp ON pp.product_tmpl_id = pt.id
        WHERE pp.id = ANY(%s)
    """, (MISSING_PRODUCT_IDS,))
    templates = sc.fetchall()

    # Get dict version with only common columns
    tmpl_col_idx = {col: i for i, col in enumerate(src_pt_cols)}
    for tmpl in templates:
        tmpl_id = tmpl['id']
        # Check if already exists in dst
        dc.execute("SELECT 1 FROM product_template WHERE id=%s", (tmpl_id,))
        if dc.fetchone():
            log(f"  product_template {tmpl_id} already exists, skipping")
            continue
        vals = {c: tmpl[c] for c in common_pt_cols}
        cols_str = ', '.join(f'"{c}"' for c in common_pt_cols)
        placeholders = ', '.join(['%s'] * len(common_pt_cols))
        dc.execute(f'INSERT INTO product_template ({cols_str}) VALUES ({placeholders})',
                   adapt_row([vals[c] for c in common_pt_cols]))
        log(f"  Inserted product_template {tmpl_id}: {tmpl['name']}")

    # Fetch product_product records
    sc.execute(f"SELECT * FROM product_product WHERE id = ANY(%s)", (MISSING_PRODUCT_IDS,))
    products = sc.fetchall()
    for prod in products:
        pp_id = prod['id']
        dc.execute("SELECT 1 FROM product_product WHERE id=%s", (pp_id,))
        if dc.fetchone():
            log(f"  product_product {pp_id} already exists, skipping")
            continue
        vals = {c: prod[c] for c in common_pp_cols}
        cols_str = ', '.join(f'"{c}"' for c in common_pp_cols)
        placeholders = ', '.join(['%s'] * len(common_pp_cols))
        dc.execute(f'INSERT INTO product_product ({cols_str}) VALUES ({placeholders})',
                   adapt_row([vals[c] for c in common_pp_cols]))
        log(f"  Inserted product_product {pp_id}")

    dst.commit()

    # ── Build user map ────────────────────────────────────────────────────────
    user_map = build_user_map(sc, dc)

    # ── Step 4b: Build set of valid CRM team IDs in dbcloud ──────────────────
    step("Step 4b: Check existing CRM teams in dbcloud")
    dc.execute("SELECT id FROM crm_team")
    valid_team_ids = {r[0] for r in dc.fetchall()}
    log(f"  Valid team IDs in dbcloud: {sorted(valid_team_ids)}")

    # ── Step 5: Copy CRM leads ────────────────────────────────────────────────
    step("Step 5: Copy CRM leads from dbcloud_new → dbcloud")

    # Columns common to both crm_lead tables (now that we've added missing ones)
    dc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='crm_lead' ORDER BY ordinal_position")
    dst_crm_cols_set = {r[0] for r in dc.fetchall()}
    sc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='crm_lead' ORDER BY ordinal_position")
    src_crm_cols = [r[0] for r in sc.fetchall()]
    common_crm_cols = [c for c in src_crm_cols if c in dst_crm_cols_set]

    # Fetch all CRM leads referenced by AMC quotations
    sc.execute("""
        SELECT * FROM crm_lead
        WHERE id IN (
            SELECT DISTINCT crm_id FROM service_sale_order
            WHERE amc_quotation=true AND crm_id IS NOT NULL
        )
        ORDER BY id
    """)
    crm_leads = sc.fetchall()
    log(f"  Found {len(crm_leads)} CRM leads to migrate")

    # Columns that need ID remapping
    crm_user_cols = {'user_id', 'create_uid', 'write_uid'}
    # 'partner_id' keeps same value (same IDs in both DBs)
    # 'stage_id', 'team_id', 'company_id' etc. keep same value

    # Columns to NULL in crm_lead (tables that may not align)
    crm_null_cols = {
        'lead_mining_request_id', 'campaign_id', 'medium_id', 'source_id',
        'recurring_plan', 'lost_reason_id', 'lang_id',
    }

    inserted_crm = 0
    skipped_crm = 0
    for lead in crm_leads:
        new_id = lead['id'] + ID_OFFSET
        dc.execute("SELECT 1 FROM crm_lead WHERE id=%s", (new_id,))
        if dc.fetchone():
            skipped_crm += 1
            continue

        row = {}
        for c in common_crm_cols:
            v = lead[c]
            if c == 'id':
                v = new_id
            elif c in crm_user_cols:
                v = user_map.get(v, 2) if v is not None else None
            elif c in crm_null_cols:
                v = None
            row[c] = v

        # Auto-null any remaining FK values that don't exist in dbcloud
        row = safe_row(dc, 'crm_lead', row, always_null=crm_null_cols)

        cols_str = ', '.join(f'"{c}"' for c in row)
        placeholders = ', '.join(['%s'] * len(row))
        dc.execute(f'INSERT INTO crm_lead ({cols_str}) VALUES ({placeholders})',
                   adapt_row(list(row.values())))
        inserted_crm += 1

    dst.commit()
    log(f"  Inserted {inserted_crm} CRM leads, skipped {skipped_crm} (already existed)")

    # Build crm_id remap: old crm_id → new crm_id
    crm_id_map = {lead['id']: lead['id'] + ID_OFFSET for lead in crm_leads}

    # ── Step 6: Copy AMC service_sale_orders ──────────────────────────────────
    step("Step 6: Copy 518 AMC service_sale_orders → dbcloud")

    # Get common columns (now that we've added missing ones in step 2)
    dc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='service_sale_order' ORDER BY ordinal_position")
    dst_sso_cols_set = {r[0] for r in dc.fetchall()}
    sc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='service_sale_order' ORDER BY ordinal_position")
    src_sso_cols = [r[0] for r in sc.fetchall()]
    common_sso_cols = [c for c in src_sso_cols if c in dst_sso_cols_set]

    sc.execute("""
        SELECT * FROM service_sale_order
        WHERE amc_quotation = true
        ORDER BY id
    """)
    amc_orders = sc.fetchall()
    log(f"  Found {len(amc_orders)} AMC orders to migrate")

    # Collect all AMC order IDs so we can remap org_sale_id self-references
    amc_ids = {o['id'] for o in amc_orders}

    sso_user_cols = {
        'user_id', 'create_uid', 'write_uid',
        'rejected_user_id', 'sales_person_user_id', 'quote_created_user_id'
    }
    sso_null_cols = {
        # Table doesn't exist in dbcloud or too complex to remap
        'current_waiting_approval_line_id',
        'contract_id',
        'approval_level_id',
        'service_sale_approval_id',
        'job_task_id',
    }

    inserted_sso = 0
    skipped_sso = 0
    for order in amc_orders:
        new_id = order['id'] + ID_OFFSET
        dc.execute("SELECT 1 FROM service_sale_order WHERE id=%s", (new_id,))
        if dc.fetchone():
            skipped_sso += 1
            continue

        row = {}
        for c in common_sso_cols:
            v = order[c]
            if c == 'id':
                v = new_id
            elif c == 'crm_id':
                v = crm_id_map.get(v) if v is not None else None
            elif c in sso_user_cols:
                v = user_map.get(v, 2) if v is not None else None
            elif c in sso_null_cols:
                v = None
            elif c == 'org_sale_id':
                # Self-reference: remap if the referenced order is also being imported
                if v is not None and v in amc_ids:
                    v = v + ID_OFFSET
                else:
                    v = None
            row[c] = v

        row = safe_row(dc, 'service_sale_order', row,
                       always_null=sso_null_cols,
                       skip_cols={'id', 'crm_id', 'org_sale_id'} | sso_user_cols)
        cols_str = ', '.join(f'"{c}"' for c in row)
        placeholders = ', '.join(['%s'] * len(row))
        dc.execute(f'INSERT INTO service_sale_order ({cols_str}) VALUES ({placeholders})',
                   adapt_row(list(row.values())))
        inserted_sso += 1

    dst.commit()
    log(f"  Inserted {inserted_sso} AMC orders, skipped {skipped_sso}")

    # ── Step 7: Copy service_sale_order_lines ─────────────────────────────────
    step("Step 7: Copy service_sale_order_lines → dbcloud")

    dc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='service_sale_order_line' ORDER BY ordinal_position")
    dst_line_cols_set = {r[0] for r in dc.fetchall()}
    sc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='service_sale_order_line' ORDER BY ordinal_position")
    src_line_cols = [r[0] for r in sc.fetchall()]
    common_line_cols = [c for c in src_line_cols if c in dst_line_cols_set]

    sc.execute("""
        SELECT * FROM service_sale_order_line
        WHERE service_sale_id IN (
            SELECT id FROM service_sale_order WHERE amc_quotation=true
        )
        ORDER BY id
    """)
    lines = sc.fetchall()
    log(f"  Found {len(lines)} lines to migrate")

    line_user_cols = {'create_uid', 'write_uid'}
    # product_id: if missing → NULL; uom: same IDs
    # amc_quotation_id references pm_service which may not exist in dbcloud → NULL

    inserted_lines = 0
    skipped_lines = 0

    for line in lines:
        new_id = line['id'] + ID_OFFSET
        dc.execute("SELECT 1 FROM service_sale_order_line WHERE id=%s", (new_id,))
        if dc.fetchone():
            skipped_lines += 1
            continue

        row = {}
        for c in common_line_cols:
            v = line[c]
            if c == 'id':
                v = new_id
            elif c == 'service_sale_id':
                v = v + ID_OFFSET if v is not None else None
            elif c in line_user_cols:
                v = user_map.get(v, 2) if v is not None else None
            row[c] = v

        # Auto-null FK columns that reference missing rows (e.g. product_id, amc_quotation_id)
        row = safe_row(dc, 'service_sale_order_line', row,
                       skip_cols={'id', 'service_sale_id'} | line_user_cols)
        cols_str = ', '.join(f'"{c}"' for c in row)
        placeholders = ', '.join(['%s'] * len(row))
        dc.execute(f'INSERT INTO service_sale_order_line ({cols_str}) VALUES ({placeholders})',
                   adapt_row(list(row.values())))
        inserted_lines += 1

    dst.commit()
    log(f"  Inserted {inserted_lines} lines, skipped {skipped_lines}")

    # ── Step 8: Update sequences ───────────────────────────────────────────────
    step("Step 8: Update sequences in dbcloud")
    sequences = {
        'service_sale_order_id_seq':      'service_sale_order',
        'service_sale_order_line_id_seq': 'service_sale_order_line',
        'crm_lead_id_seq':                'crm_lead',
    }
    for seq, table in sequences.items():
        dc.execute(f"SELECT max(id) FROM {table}")
        max_id = dc.fetchone()[0] or 0
        new_val = max_id + 1
        dc.execute(f"SELECT setval('{seq}', %s)", (new_val,))
        log(f"  {seq} → {new_val}")

    dst.commit()

    sc.close(); dc.close()
    src.close(); dst.close()

    print(f"\n{'='*60}")
    print(f"  MIGRATION COMPLETE")
    print(f"  Backup:        {backup_path}")
    print(f"  CRM leads:     {inserted_crm} inserted")
    print(f"  AMC orders:    {inserted_sso} inserted")
    print(f"  Order lines:   {inserted_lines} inserted")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
