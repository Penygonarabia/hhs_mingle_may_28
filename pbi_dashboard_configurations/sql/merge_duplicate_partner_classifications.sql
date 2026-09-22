-- partner_classification: one row per code, and a constraint to keep it that way
-- =============================================================================
--
-- WHAT THIS FIXES, AND WHAT IT COST
--
-- Every sales figure on the Salesman boards read DOUBLE on staging-hhsv3,
-- value and quantity together, and so did the target. Measured 2026-09-11,
-- August 2026:
--
--     v_pbi_sales_sman_fact, in scope   132,903,672      (what the board drew)
--     the same money, no label joins      50,330,445      (what the ERP holds)
--
-- The cause is not the fact view. partner_classification held TWO complete
-- copies of itself -- ids 11-20 and 21-30, the same ten codes, the same ten
-- labels, a master imported twice -- and the fact view resolves it BY CODE:
--
--     LEFT JOIN partner_classification pcl ON pcl.pc_code = c.cst_cstclassification
--
-- so every invoice line matched two rows and was summed twice. Counted
-- directly: 7,229 invoice lines became 14,445 after that one join. The budget
-- CTE resolves the same master the same way and sums before it groups, so the
-- target doubled with it -- and because the two copies carry DIFFERENT ids,
-- each doubled row also landed under a different l2_code, splitting the
-- Partner Classification level in half rather than simply inflating it.
--
-- sales_sman_fact_view.py says the quiet part out loud:
--
--     "every master's code is unique and non-blank (verified: 6/3/6/10/6 rows,
--      no duplicates), so each join matches exactly one row or none"
--
-- That 10 is this table. The invariant was verified on dbprod and written
-- down; nothing enforced it, and a second import broke it. This restores it
-- and then makes it a constraint, which is the only reason it cannot recur.
--
-- WHAT IT DOES, IN ORDER
--
--   1. Reports the duplicates before touching anything.
--   2. Merges each duplicated code onto its LOWEST id -- but only where the
--      copies are genuinely identical. Two rows sharing a code while carrying
--      different labels are not a double import, they are a master-data
--      question, and this declines them rather than deciding which one the
--      sales belong to.
--   3. Repoints every foreign key that references a doomed id first, found
--      from pg_constraint rather than from a list written here, so a module
--      installed later that links to this master is carried too. Odoo's own
--      external-id rows go with them.
--   4. Adds the UNIQUE index the view has always assumed, once the table can
--      carry it.
--
-- AFTERWARDS THE SNAPSHOT MUST BE REBUILT: this repairs the master the view
-- READS, and v_pbi_sales_sman_fact still holds the doubled rows until it is
-- refreshed. "Rebuild the fact and budget views" does it.
--
-- Safe to run twice: a table that already has one row per code reports that
-- and changes nothing.

\echo ''
\echo '=== Step 1: The duplicates, before anything is changed =================='
\echo ''

SELECT pc_code,
       count(*)                                        AS copies,
       string_agg(id::text, ', ' ORDER BY id)           AS ids,
       count(DISTINCT to_jsonb(p) - 'id' - 'create_uid' - 'create_date'
                                  - 'write_uid' - 'write_date')
                                                       AS distinct_bodies
  FROM partner_classification p
 GROUP BY pc_code
HAVING count(*) > 1
 ORDER BY 2 DESC, 1;

\echo ''
\echo '=== Step 2: Merging each duplicated code onto its lowest id ============='
\echo ''

DO $merge$
DECLARE
    dup        record;
    ref        record;
    moved      integer;
    removed    integer := 0;
    declined   integer := 0;
    repointed  integer := 0;
BEGIN
    FOR dup IN
        SELECT pc_code,
               min(id)                                          AS keep_id,
               array_agg(id ORDER BY id) FILTER (WHERE true)     AS all_ids,
               count(DISTINCT to_jsonb(p) - 'id' - 'create_uid' - 'create_date'
                                          - 'write_uid' - 'write_date') AS bodies
          FROM partner_classification p
         GROUP BY pc_code
        HAVING count(*) > 1
         ORDER BY pc_code
    LOOP
        -- DECLINED, NOT GUESSED. Same code, different content: which of them
        -- the sales belong to is a question about the master data, and a
        -- repair script is not where it gets answered.
        IF dup.bodies > 1 THEN
            RAISE NOTICE 'pc_code % left alone: % copies that are NOT identical (ids %). Resolve it in Odoo -- deleting one here would move sales between classifications.',
                         dup.pc_code, array_length(dup.all_ids, 1), dup.all_ids;
            declined := declined + 1;
            CONTINUE;
        END IF;

        -- Every column anywhere that points at one of the doomed ids, read
        -- from the catalogue rather than from a list -- including tables no
        -- module in this repo owns.
        FOR ref IN
            SELECT c.conrelid::regclass::text AS child_table,
                   a.attname                  AS child_column
              FROM pg_constraint c
              JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
              JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
             WHERE c.confrelid = 'partner_classification'::regclass
               AND c.contype = 'f'
        LOOP
            EXECUTE format(
                'UPDATE %s SET %I = $1 WHERE %I = ANY($2) AND %I <> $1',
                ref.child_table, ref.child_column, ref.child_column, ref.child_column)
            USING dup.keep_id, dup.all_ids;
            GET DIAGNOSTICS moved = ROW_COUNT;
            IF moved > 0 THEN
                RAISE NOTICE '  %.% : % row(s) repointed to id %.',
                             ref.child_table, ref.child_column, moved, dup.keep_id;
                repointed := repointed + moved;
            END IF;
        END LOOP;

        -- Odoo's external ids for the rows about to go, or the next module
        -- update resolves a ref to a record that is not there.
        DELETE FROM ir_model_data
         WHERE model = 'partner.classification'
           AND res_id = ANY(dup.all_ids)
           AND res_id <> dup.keep_id;

        DELETE FROM partner_classification
         WHERE pc_code = dup.pc_code AND id <> dup.keep_id;
        GET DIAGNOSTICS moved = ROW_COUNT;
        removed := removed + moved;
        RAISE NOTICE 'pc_code %: kept id %, removed % duplicate row(s).',
                     dup.pc_code, dup.keep_id, moved;
    END LOOP;

    IF removed = 0 AND declined = 0 THEN
        RAISE NOTICE 'Nothing to merge: partner_classification already holds one row per code.';
    ELSE
        RAISE NOTICE 'Merged: % duplicate row(s) removed, % reference(s) repointed, % code(s) declined.',
                     removed, repointed, declined;
    END IF;
END
$merge$;

\echo ''
\echo '=== Step 3: The UNIQUE index the view has always assumed ================'
\echo ''

DO $guard$
DECLARE
    still_dup integer;
BEGIN
    SELECT count(*) INTO still_dup
      FROM (SELECT 1 FROM partner_classification
             GROUP BY pc_code HAVING count(*) > 1) x;

    IF still_dup > 0 THEN
        RAISE NOTICE 'Index NOT created: % code(s) still have more than one row (see the declines above).', still_dup;
        RETURN;
    END IF;

    CREATE UNIQUE INDEX IF NOT EXISTS partner_classification_pc_code_unique
        ON partner_classification (pc_code);
    RAISE NOTICE 'partner_classification_pc_code_unique is in place: a second import can no longer double the boards.';
END
$guard$;

\echo ''
\echo '=== Step 4: What this database holds now ================================'
\echo ''

SELECT (SELECT count(*) FROM partner_classification)                  AS rows_total,
       (SELECT count(DISTINCT pc_code) FROM partner_classification)   AS codes,
       (SELECT count(*) FROM (SELECT 1 FROM partner_classification
                               GROUP BY pc_code HAVING count(*) > 1) d)
                                                                      AS codes_still_duplicated,
       (SELECT count(*) FROM pg_indexes
         WHERE indexname = 'partner_classification_pc_code_unique')    AS unique_index_present,
       'Rebuild the fact and budget views next -- the snapshot still holds the doubled rows.'
                                                                      AS next_step;
