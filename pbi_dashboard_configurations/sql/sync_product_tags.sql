-- Synchronize Product Tags and Template Relations for Unit Gating and AC Scope
--
--   psql -U odoo -d <database> -v ON_ERROR_STOP=1 -f pbi_dashboard_configurations/sql/sync_product_tags.sql
--
-- Also offered on PBI Dashboards > Configurations > Maintenance Scripts.
--
-- PURPOSE:
--   1. Split-System Unit Gating (Flag '02'): A split AC sale consists of 2 lines
--      (Indoor + Outdoor unit). Only lines tagged with '02' are counted in sales_qty
--      to eliminate double-counting.
--   2. AC Scope (Flag '10'): Tags air-conditioning equipment lines for AC scope filtering.
--   3. Idempotently creates '02' and '10' tags in product_tag (handling both JSONB & TEXT).
--   4. Populates product_tag_product_template_rel from legacy catalogflags.
--

\echo '----------------------------------------------------------------------'
\echo 'Step 1: Diagnostics Before Synchronization'
\echo '----------------------------------------------------------------------'

DO $$
BEGIN
    RAISE NOTICE 'Checking product_tag and relation state before sync...';
END $$;

SELECT 
    t.id AS tag_id,
    COALESCE(to_jsonb(t.name)->>'en_US', t.name::text) AS tag_name,
    COUNT(r.product_template_id) AS tagged_templates_count
FROM product_tag t
LEFT JOIN product_tag_product_template_rel r ON r.product_tag_id = t.id
GROUP BY t.id, t.name
ORDER BY t.id;

-- ----------------------------------------------------------------------
-- Step 2: Ensure Tag Masters in product_tag
-- ----------------------------------------------------------------------

DO $$
DECLARE
    v_is_jsonb boolean := false;
    v_tag_02_id integer;
    v_tag_10_id integer;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'product_tag') THEN
        SELECT (data_type = 'jsonb') INTO v_is_jsonb
        FROM information_schema.columns 
        WHERE table_name = 'product_tag' AND column_name = 'name';

        -- 2.1 Ensure Tag '02' (Machine Unit Gated) exists
        SELECT id INTO v_tag_02_id FROM product_tag 
        WHERE TRIM(COALESCE(to_jsonb(name)->>'en_US', 
                   CASE WHEN jsonb_typeof(to_jsonb(name)) = 'string' THEN name::TEXT END)) IN ('02', '2')
        ORDER BY id LIMIT 1;

        IF v_tag_02_id IS NULL THEN
            IF v_is_jsonb THEN
                EXECUTE 'INSERT INTO product_tag (name, color, create_date, write_date) VALUES ($1::jsonb, 1, NOW(), NOW())'
                USING '{"en_US": "02"}';
            ELSE
                EXECUTE 'INSERT INTO product_tag (name, color, create_date, write_date) VALUES ($1, 1, NOW(), NOW())'
                USING '02';
            END IF;
        END IF;

        -- 2.2 Ensure Tag '10' (AC Scope) exists
        SELECT id INTO v_tag_10_id FROM product_tag 
        WHERE TRIM(COALESCE(to_jsonb(name)->>'en_US', 
                   CASE WHEN jsonb_typeof(to_jsonb(name)) = 'string' THEN name::TEXT END)) IN ('10')
        ORDER BY id LIMIT 1;

        IF v_tag_10_id IS NULL THEN
            IF v_is_jsonb THEN
                EXECUTE 'INSERT INTO product_tag (name, color, create_date, write_date) VALUES ($1::jsonb, 2, NOW(), NOW())'
                USING '{"en_US": "10"}';
            ELSE
                EXECUTE 'INSERT INTO product_tag (name, color, create_date, write_date) VALUES ($1, 2, NOW(), NOW())'
                USING '10';
            END IF;
        END IF;
    END IF;
END $$;

\echo '----------------------------------------------------------------------'
\echo 'Step 3: Populate product_tag_product_template_rel from catalogflags'
\echo '----------------------------------------------------------------------'

-- 3.1 Tag '02' unit gating sync from catalogflags
DO $$
DECLARE
    v_tag_02_id integer;
    v_inserted integer := 0;
BEGIN
    SELECT id INTO v_tag_02_id FROM product_tag 
    WHERE TRIM(COALESCE(to_jsonb(name)->>'en_US', 
               CASE WHEN jsonb_typeof(to_jsonb(name)) = 'string' THEN name::TEXT END)) IN ('02', '2')
    ORDER BY id LIMIT 1;

    IF v_tag_02_id IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'catalogflags') THEN
        WITH candidate_templates AS (
            SELECT DISTINCT pt.id AS template_id, v_tag_02_id AS tag_id
            FROM product_template pt
            JOIN catalogflags cf ON UPPER(TRIM(cf.cat_part)) = UPPER(TRIM(pt.default_code))
            WHERE TRIM(cf.cat_flag) = '02'
              AND NULLIF(TRIM(pt.default_code), '') IS NOT NULL
        )
        INSERT INTO product_tag_product_template_rel (product_template_id, product_tag_id)
        SELECT c.template_id, c.tag_id
        FROM candidate_templates c
        WHERE NOT EXISTS (
            SELECT 1 FROM product_tag_product_template_rel r 
            WHERE r.product_template_id = c.template_id 
              AND r.product_tag_id = c.tag_id
        );
        GET DIAGNOSTICS v_inserted = ROW_COUNT;
        RAISE NOTICE 'Tag 02 synchronized: % new template relations created.', v_inserted;
    ELSE
        RAISE NOTICE 'Tag 02 not found or catalogflags table does not exist.';
    END IF;
END $$;

-- 3.2 Tag '10' AC scope sync from catalogflags
DO $$
DECLARE
    v_tag_10_id integer;
    v_inserted integer := 0;
BEGIN
    SELECT id INTO v_tag_10_id FROM product_tag 
    WHERE TRIM(COALESCE(to_jsonb(name)->>'en_US', 
               CASE WHEN jsonb_typeof(to_jsonb(name)) = 'string' THEN name::TEXT END)) IN ('10')
    ORDER BY id LIMIT 1;

    IF v_tag_10_id IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'catalogflags') THEN
        WITH candidate_templates AS (
            SELECT DISTINCT pt.id AS template_id, v_tag_10_id AS tag_id
            FROM product_template pt
            JOIN catalogflags cf ON UPPER(TRIM(cf.cat_part)) = UPPER(TRIM(pt.default_code))
            WHERE TRIM(cf.cat_flag) = '10'
              AND NULLIF(TRIM(pt.default_code), '') IS NOT NULL
        )
        INSERT INTO product_tag_product_template_rel (product_template_id, product_tag_id)
        SELECT c.template_id, c.tag_id
        FROM candidate_templates c
        WHERE NOT EXISTS (
            SELECT 1 FROM product_tag_product_template_rel r 
            WHERE r.product_template_id = c.template_id 
              AND r.product_tag_id = c.tag_id
        );
        GET DIAGNOSTICS v_inserted = ROW_COUNT;
        RAISE NOTICE 'Tag 10 synchronized: % new template relations created.', v_inserted;
    ELSE
        RAISE NOTICE 'Tag 10 not found or catalogflags table does not exist.';
    END IF;
END $$;

\echo '----------------------------------------------------------------------'
\echo 'Step 4: Verification Summary After Synchronization'
\echo '----------------------------------------------------------------------'

SELECT 
    t.id AS tag_id,
    COALESCE(to_jsonb(t.name)->>'en_US', t.name::text) AS tag_name,
    COUNT(r.product_template_id) AS tagged_templates_count
FROM product_tag t
LEFT JOIN product_tag_product_template_rel r ON r.product_tag_id = t.id
GROUP BY t.id, t.name
ORDER BY t.id;
