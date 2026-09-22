-- Normalise invoice-line part numbers to the case the parts catalogue holds.
--
--   psql -U odoo -d <database> -v ON_ERROR_STOP=1 -f scripts/normalise_part_number_case.sql
--
-- Also offered on PBI Dashboards > Configurations.
--
-- WHAT THIS FIXES, AND WHAT IT DOES NOT -- read this before running it.
--
-- Some invoice lines carry a part number typed in a case the catalogue does not
-- hold (MSTE12CRN1AG2KSA-NP-f against MSTE12CRN1AG2KSA-NP-F). The parts are
-- otherwise correct and the stock exists; only the letter case differs.
--
--   * IT DOES NOT MOVE A DASHBOARD FIGURE. These boards already upper-case both
--     sides of every part-number join -- the fact view, the catalogflags gate in
--     v_bidata_live, and the catalog chain all do. That was deliberate and it is
--     why the odd casings cost nothing here. Do not run this expecting a number
--     to change; if one does, something else is wrong.
--   * IT DOES NOT FIX THE ERP'S OWN REPORT. That runs inside the ERP, against
--     the ERP's own copy. This updates the reporting database only, and a
--     re-sync from the ERP can reintroduce every row it touched.
--
-- So what is it for? Two things worth having anyway. It removes a class of
-- latent bug for any future consumer that joins on the part number WITHOUT
-- upper-casing -- the boards remember to, but that is a rule someone has to
-- keep re-applying. And it makes the defect report's count fall to zero here,
-- so the remaining occurrences on the ERP side are the ones being tracked
-- rather than a mixture of both.
--
-- THE DURABLE FIX IS UPSTREAM: match part numbers case-insensitively at entry
-- in the ERP, or correct them there. This is housekeeping, not that.
--
-- DIRECTION. The catalogue is the master, so lines are moved to ITS casing,
-- never the reverse. The repair refuses to run if any part number appears under
-- more than one casing in the catalogue, because then there is no single right
-- answer and guessing would corrupt the line.
--
-- SAFE TO RUN TWICE: a second run finds nothing left to change.

\echo ''
\echo '=== 1. DIAGNOSIS (read-only) ================================================'
\echo ''

SELECT to_regclass('transaction_details') IS NOT NULL AS has_transaction_details,
       to_regclass('catalog')             IS NOT NULL AS has_catalog;

\echo ''
\echo '-- Part numbers the catalogue holds in more than one casing. MUST be empty;'
\echo '-- the repair declines to run if it is not.'
SELECT UPPER(TRIM(cat_grp)) AS franchise, UPPER(TRIM(cat_part)) AS part,
       count(DISTINCT TRIM(cat_part)) AS distinct_casings
FROM catalog
GROUP BY 1, 2 HAVING count(DISTINCT TRIM(cat_part)) > 1;

\echo ''
\echo '-- The lines, and the form the catalogue holds.'
WITH cat AS (
    SELECT DISTINCT UPPER(TRIM(cat_grp)) AS grp, UPPER(TRIM(cat_part)) AS upart,
                    TRIM(cat_part) AS as_catalogued
    FROM catalog
)
SELECT TRIM(d.trnd_part) AS as_entered, c.as_catalogued, count(*) AS lines,
       min(h.trnh_date) AS first_seen, max(h.trnh_date) AS last_seen
FROM transaction_details d
JOIN transaction_header h ON h.id = d.header_id
JOIN cat c ON c.grp = UPPER(TRIM(d.trnd_group)) AND c.upart = UPPER(TRIM(d.trnd_part))
WHERE TRIM(d.trnd_part) <> c.as_catalogued
GROUP BY 1, 2 ORDER BY 3 DESC, 1;

\echo ''
\echo '=== 2. REPAIR (guarded, idempotent) ========================================='
\echo ''

BEGIN;

DO $$
DECLARE
    v_ambiguous int;
    v_fixed     bigint;
BEGIN
    IF to_regclass('transaction_details') IS NULL OR to_regclass('catalog') IS NULL THEN
        RAISE NOTICE 'SKIPPED: this database does not carry the ERP feed tables this script acts on.';
        RETURN;
    END IF;

    -- No single right answer where the catalogue itself disagrees.
    SELECT count(*) INTO v_ambiguous FROM (
        SELECT 1 FROM catalog
        GROUP BY UPPER(TRIM(cat_grp)), UPPER(TRIM(cat_part))
        HAVING count(DISTINCT TRIM(cat_part)) > 1) x;
    IF v_ambiguous > 0 THEN
        RAISE NOTICE 'DECLINED: % part number(s) appear under more than one casing in the '
                     'catalogue, so the target form is ambiguous. Resolve those first.',
                     v_ambiguous;
        RETURN;
    END IF;

    -- Joined through a CTE rather than a correlated lookup: `catalog` carries no
    -- index on cat_part, so a per-row probe seq-scans all of it for every
    -- detail line.
    WITH cat AS (
        SELECT DISTINCT UPPER(TRIM(cat_grp)) AS grp, UPPER(TRIM(cat_part)) AS upart,
                        TRIM(cat_part) AS as_catalogued
        FROM catalog
    ), fix AS (
        SELECT d.id, c.as_catalogued
        FROM transaction_details d
        JOIN cat c ON c.grp = UPPER(TRIM(d.trnd_group))
                  AND c.upart = UPPER(TRIM(d.trnd_part))
        WHERE TRIM(d.trnd_part) <> c.as_catalogued
    )
    UPDATE transaction_details t
       SET trnd_part = fix.as_catalogued
      FROM fix
     WHERE fix.id = t.id;

    GET DIAGNOSTICS v_fixed = ROW_COUNT;
    IF v_fixed = 0 THEN
        RAISE NOTICE 'NOTHING TO DO: every invoice line already carries the catalogue''s casing.';
    ELSE
        RAISE NOTICE 'NORMALISED: % invoice line(s) moved to the catalogue''s casing.', v_fixed;
        RAISE NOTICE 'NOTE: no dashboard figure should change -- the boards already upper-case '
                     'both sides of every part-number join. This is housekeeping, and it does '
                     'not repair the ERP''s own copy.';
    END IF;
END $$;

COMMIT;

\echo ''
\echo '-- Confirmation: nothing should remain after a successful run.'
WITH cat AS (
    SELECT DISTINCT UPPER(TRIM(cat_grp)) AS grp, UPPER(TRIM(cat_part)) AS upart,
                    TRIM(cat_part) AS as_catalogued
    FROM catalog
)
SELECT count(*) AS lines_still_mismatched
FROM transaction_details d
JOIN cat c ON c.grp = UPPER(TRIM(d.trnd_group)) AND c.upart = UPPER(TRIM(d.trnd_part))
WHERE TRIM(d.trnd_part) <> c.as_catalogued;
