-- ============================================================================
-- DIAGNOSE MODULE LOAD ORDER AND RELATED-FIELD REACHABILITY
-- ============================================================================
--
-- READ ONLY. Nothing here writes. It cannot repair what it finds, and that is
-- deliberate: see "Why there is no fix button" below.
--
-- WHAT IT FINDS
--   A field declared as related='some_m2o.some_field' is only valid if the
--   module declaring it can SEE the module that declares some_field. Odoo
--   checks this in fields.py setup_related() and, when it fails, raises
--
--     KeyError: 'Field <name> referenced in related field definition
--                <model>.<name> does not exist.'
--
--   It never shows up on a normal boot. load_module_graph() calls
--   registry.setup_models() BETWEEN modules, but only for modules being
--   updated, so on a plain restart every class is registered before the single
--   setup pass and the missing dependency stays invisible. Press Upgrade on
--   ANY module and that mid-graph setup runs against a registry holding only
--   the modules loaded so far, and a related field whose target module sorts
--   later in the graph blows up.
--
--   Odoo orders the graph by (depth, name), where depth is distance from base
--   through the MANIFEST depends. A module that declares a related field but
--   does not depend on the module owning the target can sit at a lower depth
--   and load first. That is the whole bug.
--
--   Found this way on staging-hhsv3 (2026-09-11): salesman_new_partner
--   (depends: base, so depth 1) declares res.users.salesman_type_id as
--   related='partner_id.salesman_type_id', while res.partner.salesman_type_id
--   belongs to salesman_type (depends: base, salesman_res_partner, depth 2).
--   Every attempt to upgrade the pbi dashboards died on it and looked for all
--   the world like a pbi fault. It was not. Any module would have hit it.
--
-- WHY THERE IS NO FIX BUTTON
--   Load order comes from the MANIFEST FILE, not the database.
--   odoo/modules/graph.py Graph.add_modules() reads get_manifest(module)
--   ['depends'] off disk; ir_module_module_dependency only reflects that and is
--   rewritten by _update_dependencies on every module update. INSERTing a row
--   into ir_module_module_dependency changes what the Apps list draws, changes
--   nothing about load order, and is erased on the next update. A SQL card
--   physically cannot repair this. The repair is one line in a manifest on the
--   server, which is why block 1 hands back the exact line.
--
--   Deleting the ir_model_fields row does not help either when state='base':
--   _add_manual_fields only instantiates state='manual' rows, so a base-state
--   field comes from live Python and the KeyError survives the delete. That is
--   what separates this from diagnose_and_clean_salesman_type_id.sql, which
--   only ever addressed the state='manual' (Studio) case.
--
-- HOW THE NOISE IS KEPT OUT
--   Two filters, both load-bearing. Without them this returns about fifty rows
--   on dbprod and is useless.
--
--   1. TRANSIENT MODELS ARE SKIPPED. Every module that touches settings adds
--      fields to res.config.settings, and a model inheriting it (hr.config.
--      settings) carries copies attributed to ITS module. Dozens of rows, all
--      structural.
--   2. ONLY NON-CORE DECLARING MODULES. Odoo's own _inherits delegation and
--      mixins generate related fields attributed to the child model's module
--      (mrp.document over ir.attachment, product.document over web_editor's
--      fields). Real by the letter of the check, never actionable, and not
--      ours to fix. author <> 'Odoo S.A.' drops them; block 2 counts what was
--      dropped so nothing is silently hidden.
--
--   What survives is still LATENT rather than live: a finding only crashes if
--   the declaring module genuinely sorts before the target in the graph. The
--   one that is crashing right now is the one named in the traceback. The rest
--   work by luck of depth ordering and will break the day a manifest changes.
--
-- NOTE ON THE PER-CENT SIGN
--   There is not one in this file, SQL or comment, and split_part() is used
--   where LIKE would have been obvious. pbi raw SQL has been bitten before by
--   a stray literal per-cent reaching a parameterised cursor and surfacing as
--   "list index out of range"; keeping the character out costs nothing here.
--
-- Safe to run any number of times.
-- ============================================================================

\echo '=== 1. Related fields a custom module cannot reach ======================='
\echo '    Each row ends in the exact manifest line that fixes it.'
\echo ''

WITH RECURSIVE closure AS (
    -- Direct manifest dependencies, as reflected into the database.
    SELECT mo.name AS module,
           dp.name AS reaches
      FROM ir_module_module mo
      JOIN ir_module_module_dependency dp ON dp.module_id = mo.id
    UNION
    -- ...then everything those reach. UNION (not UNION ALL) terminates the
    -- walk; the module graph is acyclic but a bad manifest need not be.
    SELECT c.module,
           dp2.name
      FROM closure c
      JOIN ir_module_module mo2            ON mo2.name = c.reaches
      JOIN ir_module_module_dependency dp2 ON dp2.module_id = mo2.id
),
rel AS (
    -- Python-declared two-hop related fields on persistent models, declared by
    -- a module that is not Odoo's own. Deeper paths are counted in block 3.
    SELECT f.id                          AS field_id,
           f.model                       AS model,
           f.name                        AS fname,
           f.related                     AS related,
           d.module                      AS decl_module,
           split_part(f.related, '.', 1) AS hop1,
           split_part(f.related, '.', 2) AS hop2
      FROM ir_model_fields f
      JOIN ir_model_data d    ON d.model = 'ir.model.fields' AND d.res_id = f.id
      JOIN ir_module_module m ON m.name = d.module
                             AND m.state = 'installed'
                             AND coalesce(m.author, '') <> 'Odoo S.A.'
      JOIN ir_model im        ON im.model = f.model
                             AND im.transient IS NOT TRUE
     WHERE f.state = 'base'
       AND f.related IS NOT NULL
       AND array_length(string_to_array(f.related, '.'), 1) = 2
),
resolved AS (
    -- Walk the path: hop1 gives the comodel, hop2 the target field, and
    -- ir_model_data the module that declared it. A field declared by several
    -- modules yields several rows; the reachability test below folds them.
    SELECT r.decl_module,
           r.model,
           r.fname,
           r.related,
           r.hop2,
           hop.relation AS comodel,
           td.module    AS target_module
      FROM rel r
      JOIN ir_model_fields hop ON hop.model = r.model      AND hop.name = r.hop1
      JOIN ir_model_fields tgt ON tgt.model = hop.relation AND tgt.name = r.hop2
      JOIN ir_model_data   td  ON td.model = 'ir.model.fields' AND td.res_id = tgt.id
     WHERE hop.relation IS NOT NULL
),
flagged AS (
    SELECT rs.*,
           (rs.target_module = rs.decl_module
            OR EXISTS (SELECT 1
                         FROM closure c
                        WHERE c.module  = rs.decl_module
                          AND c.reaches = rs.target_module)) AS reachable
      FROM resolved rs
)
SELECT decl_module                             AS declaring_module,
       model || '.' || fname                   AS related_field,
       related                                 AS related_path,
       comodel || '.' || hop2                  AS target_field,
       string_agg(DISTINCT target_module, ', ') AS target_declared_by,
       'add ' || quote_literal(min(target_module)) || ' to '
         || decl_module || '/__manifest__.py depends' AS remediation
  FROM flagged
 GROUP BY decl_module, model, fname, related, comodel, hop2
-- Reachable through ANY module owning the target is good enough, so this
-- rejects only fields no owner can be seen from.
HAVING bool_or(reachable) IS NOT TRUE
 ORDER BY 1, 2;

\echo ''
\echo '=== 2. Declared dependencies of every module named above ================='
\echo '    The missing edge is the one you cannot find here.'
\echo ''

WITH RECURSIVE closure AS (
    SELECT mo.name AS module, dp.name AS reaches
      FROM ir_module_module mo
      JOIN ir_module_module_dependency dp ON dp.module_id = mo.id
    UNION
    SELECT c.module, dp2.name
      FROM closure c
      JOIN ir_module_module mo2            ON mo2.name = c.reaches
      JOIN ir_module_module_dependency dp2 ON dp2.module_id = mo2.id
),
rel AS (
    SELECT f.model AS model, f.name AS fname, f.related AS related,
           d.module AS decl_module,
           split_part(f.related, '.', 1) AS hop1,
           split_part(f.related, '.', 2) AS hop2
      FROM ir_model_fields f
      JOIN ir_model_data d    ON d.model = 'ir.model.fields' AND d.res_id = f.id
      JOIN ir_module_module m ON m.name = d.module
                             AND m.state = 'installed'
                             AND coalesce(m.author, '') <> 'Odoo S.A.'
      JOIN ir_model im        ON im.model = f.model AND im.transient IS NOT TRUE
     WHERE f.state = 'base'
       AND f.related IS NOT NULL
       AND array_length(string_to_array(f.related, '.'), 1) = 2
),
resolved AS (
    SELECT r.decl_module, r.model, r.fname, r.hop2,
           hop.relation AS comodel, td.module AS target_module
      FROM rel r
      JOIN ir_model_fields hop ON hop.model = r.model      AND hop.name = r.hop1
      JOIN ir_model_fields tgt ON tgt.model = hop.relation AND tgt.name = r.hop2
      JOIN ir_model_data   td  ON td.model = 'ir.model.fields' AND td.res_id = tgt.id
     WHERE hop.relation IS NOT NULL
),
flagged AS (
    SELECT rs.*,
           (rs.target_module = rs.decl_module
            OR EXISTS (SELECT 1 FROM closure c
                        WHERE c.module = rs.decl_module
                          AND c.reaches = rs.target_module)) AS reachable
      FROM resolved rs
),
involved AS (
    SELECT decl_module AS module
      FROM flagged
     GROUP BY decl_module, model, fname, comodel, hop2
    HAVING bool_or(reachable) IS NOT TRUE
    UNION
    SELECT target_module
      FROM flagged f2
     WHERE NOT EXISTS (SELECT 1 FROM flagged f3
                        WHERE f3.model = f2.model AND f3.fname = f2.fname
                          AND f3.reachable)
)
SELECT mo.name                       AS module,
       coalesce(dp.name, '(none)')   AS depends_on,
       mo.state                      AS state,
       coalesce(mo.author, '(none)') AS author
  FROM ir_module_module mo
  LEFT JOIN ir_module_module_dependency dp ON dp.module_id = mo.id
 WHERE mo.name IN (SELECT module FROM involved)
 ORDER BY 1, 2;

\echo ''
\echo '=== 3. What this check covered and what it left alone ==================='
\echo ''

SELECT (SELECT count(*)
          FROM ir_model_fields
         WHERE state = 'base' AND related IS NOT NULL)  AS related_fields_total,
       (SELECT count(*)
          FROM ir_model_fields f
          JOIN ir_model_data d    ON d.model = 'ir.model.fields' AND d.res_id = f.id
          JOIN ir_module_module m ON m.name = d.module
                                 AND coalesce(m.author, '') = 'Odoo S.A.'
         WHERE f.state = 'base' AND f.related IS NOT NULL)
                                                        AS core_declared_skipped,
       (SELECT count(*)
          FROM ir_model_fields f
          JOIN ir_model im ON im.model = f.model AND im.transient IS TRUE
         WHERE f.state = 'base' AND f.related IS NOT NULL)
                                                        AS transient_skipped,
       (SELECT count(*)
          FROM ir_model_fields
         WHERE state = 'base'
           AND related IS NOT NULL
           AND array_length(string_to_array(related, '.'), 1) > 2)
                                                        AS deep_paths_skipped,
       (SELECT count(*)
          FROM ir_model_fields
         WHERE state = 'manual' AND related IS NOT NULL)
                                                        AS studio_related_fields;
