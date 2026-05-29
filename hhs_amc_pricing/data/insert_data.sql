-- ============================================================
-- INSERT DATA FOR t_mainproducts AND brand TABLES
-- Run AFTER installing the hhs_amc_pricing module
-- ============================================================

-- ============ BRAND ============
INSERT INTO brand (id, name, create_uid, write_uid, create_date, write_date)
VALUES (1, 'Midea', 2, 2, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Reset sequence
SELECT setval('brand_id_seq', (SELECT MAX(id) FROM brand));

-- ============ T_MAINPRODUCTS ============
INSERT INTO t_mainproducts (id, mp_grp, mp_code, mp_sort, create_uid, write_uid, create_date, write_date)
VALUES
    (1,  'ASK', 'OTHERS',  1, 1, 1, NOW(), NOW()),
    (2,  'BKO', 'OTHERS',  2, 1, 1, NOW(), NOW()),
    (3,  'CDY', 'OTHERS',  3, 1, 1, NOW(), NOW()),
    (4,  'MDA', 'OTHERS',  4, 1, 1, NOW(), NOW()),
    (5,  'MDA', 'WINDOWS', 5, 1, 1, NOW(), NOW()),
    (6,  'MDA', 'SPLIT',   6, 1, 1, NOW(), NOW()),
    (7,  'MDA', 'LCAC',    7, 1, 1, NOW(), NOW()),
    (8,  'MDA', 'CAC',     8, 1, 1, NOW(), NOW()),
    (9,  'RUD', 'OTHERS',  9, 1, 1, NOW(), NOW()),
    (10, 'SMG', 'OTHERS', 10, 1, 1, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Reset sequence
SELECT setval('t_mainproducts_id_seq', (SELECT MAX(id) FROM t_mainproducts));

-- ============ VERIFY ============
SELECT 'brand' AS table_name, COUNT(*) AS rows FROM brand
UNION ALL
SELECT 't_mainproducts', COUNT(*) FROM t_mainproducts;
