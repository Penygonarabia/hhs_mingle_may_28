-- Deletes credit note CR20112352 so June 2026 AC figures match the bidata
-- snapshot. Applied to dbprod 2026-09-03 at the user's explicit direction.
--
--   psql -U odoo -d <database> -v ON_ERROR_STOP=1 -f scripts/delete_CR20112352_bidata_align.sql
--
-- ============================================================================
-- READ THIS BEFORE RUNNING IT ANYWHERE.
--
-- This is NOT a defect repair. The other scripts in this directory fix things
-- that were provably broken -- a deleted product category that 10,941 rows still
-- referenced, an invoice line with no product group. This one deletes a document
-- that is entirely correct, because the reporting feed never received it.
--
-- CR20112352 is a POSTED credit note (status P, 18 June 2026, warehouse 201,
-- customer J337 "Bin Moamen Trading Co.", salesman J1-043, against invoice
-- IN20139377). It records goods a customer actually returned:
--
--     MSTA12CRNAG14-NP-F   1 returned   500.00 - 10.00 disc - 72.50 spl = 417.50
--     MSTA12CRNAG14-NP-C   1 returned   930.00 - 18.60 disc - 134.85 spl = 776.55
--     CSTDISC              (customer discount line, outside AC scope)
--
-- Deleting it removes 1 unit and SAR 1,194.05 of returns from June, which is
-- what makes the month agree with bidata -- bidata holds ZERO rows for this
-- document. The header was created 2026-06-19 and rewritten 2026-07-29, the
-- same posting flip seen elsewhere; bidata's own bi_lastmodifieddate stops at
-- 2026-04-15, so the feed simply predates the posting.
--
-- The consequence is that June's figures no longer reflect this return. Stock
-- came back and the customer was credited, and after this runs no credit note
-- in the sales data says so. Anyone auditing June will find the return in the
-- ERP and not here.
--
-- The alternative, not taken: leave the data alone and correct the expected
-- baseline instead, since the pre-deletion figures were the accurate ones.
-- ============================================================================
--
-- REVERSIBLE. The rows are copied into bak_cr20112352_header /
-- bak_cr20112352_details before anything is removed, and the footer has the
-- two statements that put them back.
--
-- IDEMPOTENT. A second run finds nothing to delete and says so.

BEGIN;

DO $$
DECLARE
    v_header  integer;
    v_details integer;
BEGIN
    SELECT id INTO v_header
    FROM transaction_header
    WHERE TRIM(trnh_no) = 'CR20112352'
      AND LPAD(TRIM(trnh_type),2,'0') = '02'
      AND SUBSTRING(trnh_date,1,6) = '202606';

    IF v_header IS NULL THEN
        RAISE NOTICE 'SKIPPED: CR20112352 is not present (already deleted, or this database never had it).';
        RETURN;
    END IF;

    -- Back up first, every column, exactly as stored. Dropped and rebuilt so a
    -- re-run after a restore captures the current rows rather than stale ones.
    DROP TABLE IF EXISTS bak_cr20112352_header, bak_cr20112352_details;

    EXECUTE 'CREATE TABLE bak_cr20112352_header  AS SELECT * FROM transaction_header  WHERE id = ' || v_header;
    EXECUTE 'CREATE TABLE bak_cr20112352_details AS SELECT * FROM transaction_details WHERE header_id = ' || v_header;

    EXECUTE 'COMMENT ON TABLE bak_cr20112352_header IS ' ||
            quote_literal('Backup of posted credit note CR20112352, deleted to match the bidata snapshot. ' ||
                          'Restore: INSERT INTO transaction_header SELECT * FROM bak_cr20112352_header;');
    EXECUTE 'COMMENT ON TABLE bak_cr20112352_details IS ' ||
            quote_literal('Backup of CR20112352 detail lines. ' ||
                          'Restore: INSERT INTO transaction_details SELECT * FROM bak_cr20112352_details;');

    SELECT count(*) INTO v_details FROM bak_cr20112352_details;

    DELETE FROM transaction_details WHERE header_id = v_header;
    DELETE FROM transaction_header  WHERE id = v_header;

    RAISE NOTICE 'DELETED: CR20112352 (header id %, % detail lines). Backed up to bak_cr20112352_header / bak_cr20112352_details.',
                 v_header, v_details;
    RAISE NOTICE 'June 2026 AC should now read 1 unit and SAR 1,194.05 higher than before.';
END $$;

COMMIT;

-- Verify with:
--   ./scripts/check_ac_sales_vs_erp.sh 2026-06
--
-- Restore, should this need undoing:
--   INSERT INTO transaction_header  SELECT * FROM bak_cr20112352_header;
--   INSERT INTO transaction_details SELECT * FROM bak_cr20112352_details;
--
-- Keep the two bak_ tables. They are the only record left of this document.
