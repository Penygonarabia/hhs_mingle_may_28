# -*- coding: utf-8 -*-
# Non-destructive schema reconciliation for dbprod.
# The repo code declares stored fields that the restored production DB lacks
# (code drifted ahead of the dump). On a normal boot Odoo does NOT add columns
# (only -u does, which here fails on unrelated broken views). This adds ONLY the
# missing columns, typed exactly as Odoo would (field.column_type), nullable,
# no constraints, no data change. Existing tables only (won't create new tables).
added = []
skipped_no_table = 0
cr = env.cr
for model_name in sorted(env.registry.models):
    M = env[model_name]
    if getattr(M, '_abstract', False) or getattr(M, '_transient', False):
        continue
    if not getattr(M, '_auto', False):
        continue
    table = M._table
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name=%s", (table,))
    if not cr.fetchone():
        skipped_no_table += 1
        continue
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name=%s", (table,))
    existing = {r[0] for r in cr.fetchall()}
    for fname, field in M._fields.items():
        if not field.store:
            continue
        ctype = field.column_type  # None for non-column (o2m/m2m/non-stored)
        if not ctype:
            continue
        if fname in existing:
            continue
        ddl_type = ctype[1]
        try:
            cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (table, fname, ddl_type))
            added.append((table, fname, ddl_type))
        except Exception as e:
            cr.rollback()
            print("  FAIL %s.%s (%s): %s" % (table, fname, ddl_type, e))
    # commit per-model so one failure doesn't lose prior work
    cr.commit()

print("=== schema reconciliation done ===")
print("columns added:", len(added))
print("tables missing entirely (skipped):", skipped_no_table)
# show a sample, and specifically the work_center_group ones
for t, c, ty in added:
    if t == 'work_center_group':
        print("  +", t, c, ty)
print("--- first 25 of all additions ---")
for t, c, ty in added[:25]:
    print("  +", t, c, ty)
