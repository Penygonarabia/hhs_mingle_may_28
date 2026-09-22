-- ============================================================================
-- Rename three module technical names in an existing database.
--
--   dashboard_rights              -> module_rights
--   dashboard_rights_ninja_bridge -> module_rights_ninja_bridge
--   dashboard_user_rights_roles   -> module_user_rights_roles
--
-- The folders and every in-code reference (external-ID prefixes, asset paths,
-- OWL template namespaces, `depends` entries) were renamed already; this moves
-- the database rows that key off the technical name so the modules stay
-- "installed" instead of reappearing as new/uninstalled ones.
--
-- Model names, SQL tables (dashboard_rights, dashboard_rights_menu,
-- user_dashboard_rights_rel), fields (dashboard_rights_id,
-- dashboard_rights_given) and record ids (view_dashboard_rights_list,
-- group_dashboard_rights_admin, ...) are deliberately NOT renamed — only the
-- module that owns them.
--
-- Run with the Odoo container stopped, then restart with:
--   -u module_rights,module_rights_ninja_bridge,module_user_rights_roles
--
--   docker exec -i cloud-db-1 psql -U odoo -d dbprod \
--       -v ON_ERROR_STOP=1 -f - < scripts/rename_dashboard_rights_modules.sql
-- ============================================================================

BEGIN;

-- 1. The module records themselves.
UPDATE ir_module_module SET name = 'module_rights'
 WHERE name = 'dashboard_rights';
UPDATE ir_module_module SET name = 'module_rights_ninja_bridge'
 WHERE name = 'dashboard_rights_ninja_bridge';
UPDATE ir_module_module SET name = 'module_user_rights_roles'
 WHERE name = 'dashboard_user_rights_roles';

-- 2. Dependency rows of *other* modules that point at the old names.
UPDATE ir_module_module_dependency SET name = 'module_rights'
 WHERE name = 'dashboard_rights';
UPDATE ir_module_module_dependency SET name = 'module_rights_ninja_bridge'
 WHERE name = 'dashboard_rights_ninja_bridge';
UPDATE ir_module_module_dependency SET name = 'module_user_rights_roles'
 WHERE name = 'dashboard_user_rights_roles';

-- 3. Exclusion rows (harmless no-op if none exist).
UPDATE ir_module_module_exclusion SET name = 'module_rights'
 WHERE name = 'dashboard_rights';
UPDATE ir_module_module_exclusion SET name = 'module_rights_ninja_bridge'
 WHERE name = 'dashboard_rights_ninja_bridge';
UPDATE ir_module_module_exclusion SET name = 'module_user_rights_roles'
 WHERE name = 'dashboard_user_rights_roles';

-- 4. XML-ID ownership: every external ID these modules created.
UPDATE ir_model_data SET module = 'module_rights'
 WHERE module = 'dashboard_rights';
UPDATE ir_model_data SET module = 'module_rights_ninja_bridge'
 WHERE module = 'dashboard_rights_ninja_bridge';
UPDATE ir_model_data SET module = 'module_user_rights_roles'
 WHERE module = 'dashboard_user_rights_roles';

-- 5. base.module_<technical_name> XML-IDs of the ir.module.module records.
UPDATE ir_model_data SET name = 'module_module_rights'
 WHERE module = 'base' AND model = 'ir.module.module'
   AND name = 'module_dashboard_rights';
UPDATE ir_model_data SET name = 'module_module_rights_ninja_bridge'
 WHERE module = 'base' AND model = 'ir.module.module'
   AND name = 'module_dashboard_rights_ninja_bridge';
UPDATE ir_model_data SET name = 'module_module_user_rights_roles'
 WHERE module = 'base' AND model = 'ir.module.module'
   AND name = 'module_dashboard_user_rights_roles';

-- 6. QWeb view keys are "<module>.<record_id>".
UPDATE ir_ui_view
   SET key = regexp_replace(key, '^dashboard_rights\.', 'module_rights.')
 WHERE key LIKE 'dashboard_rights.%';
UPDATE ir_ui_view
   SET key = regexp_replace(key, '^dashboard_rights_ninja_bridge\.',
                            'module_rights_ninja_bridge.')
 WHERE key LIKE 'dashboard_rights_ninja_bridge.%';
UPDATE ir_ui_view
   SET key = regexp_replace(key, '^dashboard_user_rights_roles\.',
                            'module_user_rights_roles.')
 WHERE key LIKE 'dashboard_user_rights_roles.%';

-- 7. Server-action python that resolves external IDs by string. The upgrade
--    would rewrite these from the XML anyway; doing it here keeps the DB
--    consistent even before the upgrade runs.
UPDATE ir_act_server
   SET code = replace(code, 'dashboard_rights.', 'module_rights.')
 WHERE code LIKE '%dashboard_rights.%';

-- 8. ir.asset rows, if any were ever created as data records.
UPDATE ir_asset SET path = replace(path, 'dashboard_rights/', 'module_rights/')
 WHERE path LIKE '%dashboard_rights/%';

-- 9. Drop the compiled asset bundles so the renamed static paths are rebuilt.
DELETE FROM ir_attachment WHERE name LIKE 'web.assets_%';

-- Sanity check: nothing should remain.
SELECT 'ir_module_module' AS tbl, name FROM ir_module_module
 WHERE name IN ('dashboard_rights', 'dashboard_rights_ninja_bridge',
                'dashboard_user_rights_roles')
UNION ALL
SELECT 'ir_module_module_dependency', name FROM ir_module_module_dependency
 WHERE name IN ('dashboard_rights', 'dashboard_rights_ninja_bridge',
                'dashboard_user_rights_roles')
UNION ALL
SELECT 'ir_model_data', module FROM ir_model_data
 WHERE module IN ('dashboard_rights', 'dashboard_rights_ninja_bridge',
                  'dashboard_user_rights_roles');

COMMIT;
