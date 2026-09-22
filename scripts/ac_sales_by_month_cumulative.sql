SET statement_timeout = '300s';
SET enable_nestloop = off;
WITH unitpart AS MATERIALIZED (
    SELECT DISTINCT UPPER(TRIM(cat_grp)) AS grp, UPPER(TRIM(cat_stock)) AS stock,
           UPPER(TRIM(cat_part)) AS part
    FROM catalogflags
    WHERE TRIM(cat_flag) = '02' AND NULLIF(TRIM(cat_part), '') IS NOT NULL
),
cat AS MATERIALIZED (
    SELECT DISTINCT ON (UPPER(TRIM(cat_part)))
        UPPER(TRIM(cat_part)) AS part, TRIM(cat_grp) AS fr,
        TRIM(cat_pgroup) AS pg, TRIM(cat_psgroup) AS psg, cat_desc AS descr
    FROM catalog ORDER BY 1, id
),
d1 AS MATERIALIZED (
    SELECT DISTINCT ON (TRIM(code)) id, TRIM(code) AS code, name
    FROM product_category
    WHERE (LENGTH(parent_path) - LENGTH(REPLACE(parent_path, '/', ''))) = 1
      AND NULLIF(TRIM(code), '') IS NOT NULL ORDER BY TRIM(code), id
),
d2 AS MATERIALIZED (
    SELECT DISTINCT ON (parent_id, TRIM(code)) id, parent_id, TRIM(code) AS code, name
    FROM product_category
    WHERE (LENGTH(parent_path) - LENGTH(REPLACE(parent_path, '/', ''))) = 2
      AND NULLIF(TRIM(code), '') IS NOT NULL ORDER BY parent_id, TRIM(code), id
),
base AS (
SELECT
    SUBSTRING(h.trnh_date, 1, 4)::INT AS yr,
    SUBSTRING(h.trnh_date, 5, 2)::INT AS mth,
    SUM(
        CASE
            WHEN u.part IS NULL THEN 0
            WHEN LPAD(TRIM(h.trnh_type), 2, '0') = '02' THEN -COALESCE(d.trnd_ret, 0)
            ELSE COALESCE(d.trnd_qtyiss, 0)
        END
    )::NUMERIC AS sales_qty,
    ROUND(SUM(
        (CASE
            WHEN LPAD(TRIM(h.trnh_type), 2, '0') = '02' THEN -COALESCE(d.trnd_ret, 0)
            ELSE COALESCE(d.trnd_qtyiss, 0)
         END)
        *
        (
            COALESCE(d.trnd_price, 0)
            - (
                COALESCE(d.trnd_disc, 0)
                + COALESCE(d.trnd_promodisc, 0)
                + COALESCE(d.trnd_campaign, 0)
                + CASE
                    WHEN COALESCE(h.trnh_total, 0) > 0 THEN
                        (
                            COALESCE(d.trnd_price, 0)
                            - COALESCE(d.trnd_disc, 0)
                            - COALESCE(d.trnd_promodisc, 0)
                            - COALESCE(d.trnd_campaign, 0)
                        ) * COALESCE(h.trnh_headdisc, 0) / h.trnh_total
                    ELSE 0
                  END
            )
            - COALESCE(d.trnd_cstspldisc, 0)
        )
    )::NUMERIC, 2) AS sales_value
FROM transaction_details d
JOIN transaction_header h
    ON h.id = d.header_id
   AND TRIM(h.trnh_whouse) = TRIM(d.trnd_whouse)
LEFT JOIN product_category pcg
    ON pcg.id = d.trnd_groupid
LEFT JOIN unitpart u ON u.grp = TRIM(d.trnd_group) AND u.stock = TRIM(d.trnd_stock)
   AND u.part = UPPER(TRIM(d.trnd_part))
LEFT JOIN cat ON cat.part = UPPER(TRIM(d.trnd_part))
LEFT JOIN d1 ON d1.code = cat.fr
LEFT JOIN d2 ON d2.parent_id = d1.id AND d2.code = cat.pg
WHERE SUBSTRING(h.trnh_date, 1, 4)::INT IN (2025, 2026)
    AND LPAD(TRIM(h.trnh_type), 2, '0') IN ('01', '02')
    AND TRIM(d.trnd_group) = 'MDA'
    AND TRIM(h.trnh_status) IN ('C', 'P')
    AND TRIM(h.trnh_cstno) NOT LIKE 'V%'
    AND COALESCE(TRIM(pcg.code), TRIM(d2.code), '') IN (
        'ACACC','ACCON','ACCST','ACPAC','ACPKG','ACAIP',
        'ACPOR','ACVRF','ACWIN','ACWTS','ACHCL','ATOM')
GROUP BY 1,2 ORDER BY 1,2
)
SELECT yr, mth,
       TO_CHAR(TO_DATE(mth::text,'MM'),'Month') AS month_name,
       sales_qty, sales_value,
       SUM(sales_qty)   OVER (PARTITION BY yr ORDER BY mth) AS cumm_sales_qty,
       SUM(sales_value) OVER (PARTITION BY yr ORDER BY mth) AS cumm_sales_value
FROM base ORDER BY yr, mth;
