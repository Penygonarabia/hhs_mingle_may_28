-- ============================================================================
-- DIAGNOSE AND REPAIR 'salesman_type_id' BROKEN FIELD IN IR_MODEL_FIELDS
-- ============================================================================
--
-- Why this is needed:
-- During module upgrade, Odoo checks all related fields in the registry.
-- If a custom/studio field `salesman_type_id` exists on `res.users` pointing to
-- `partner_id.salesman_type_id` when `salesman_type_id` does not exist on
-- `res.partner`, Odoo halts with:
--   KeyError: 'Field salesman_type_id referenced in related field definition res.users.salesman_type_id does not exist.'
--
-- SCOPE, AND WHAT THIS DOES NOT FIX
--   Step 2 below deletes state='manual' rows only. That is not a conservative
--   choice, it is the only one available: _add_manual_fields instantiates
--   manual rows and nothing else, so a state='base' row comes from live Python
--   on the filesystem and the KeyError survives any delete.
--
--   If step 1 reports state='base', stop here. The cause is a module load
--   order problem -- a module declaring the related field without depending on
--   the module that owns the target -- and it is repaired in a manifest, not
--   in SQL. Run diagnose_module_load_order.sql (Upgrade Blockers on the
--   Configurations page), which names the module and the exact depends line.
--
--   That is what it was on staging-hhsv3 on 2026-09-11: both rows were base,
--   salesman_new_partner declared res.users.salesman_type_id without depending
--   on salesman_type, and this script had nothing to delete.
--
-- Server filesystem search command:
--   grep -rn "salesman_type_id" /var/odoo/staging-hhsv3.cieloapps.com/ --include=*.py
--
-- Safe to run multiple times.
-- ============================================================================

-- 1. Report all ir_model_fields matching salesman_type_id or related references
SELECT id, model, name, field_description, ttype, relation, related, state
FROM ir_model_fields
WHERE name = 'salesman_type_id'
   OR related LIKE '%salesman_type_id%';

-- 2. Clean up manual / studio field definition on res.users if it references missing partner field
DELETE FROM ir_model_fields
WHERE name = 'salesman_type_id'
  AND model = 'res.users'
  AND state = 'manual';

-- 3. Check remaining fields after cleanup
SELECT id, model, name, field_description, ttype, relation, related, state,
       'Cleanup complete. If defined in Python code on server, run: grep -rn "salesman_type_id" /var/odoo/staging-hhsv3.cieloapps.com/' AS status
FROM ir_model_fields
WHERE name = 'salesman_type_id';
