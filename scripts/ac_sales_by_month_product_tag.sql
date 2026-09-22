SET statement_timeout = '300s';
SET enable_nestloop = off;
WITH unitpart AS MATERIALIZED (
    SELECT DISTINCT UPPER(TRIM(pt.default_code)) AS part
    FROM product_tag t
    JOIN product_tag_product_template_rel r ON r.product_tag_id = t.id
    JOIN product_template pt ON pt.id = r.product_template_id
    WHERE TRIM(COALESCE(to_jsonb(t.name)->>'en_US',
              CASE WHEN jsonb_typeof(to_jsonb(t.name)) = 'string' THEN t.name::TEXT END
          )) IN ('02','2')
      AND NULLIF(TRIM(pt.default_code), '') IS NOT NULL
),
prod AS MATERIALIZED (
    SELECT DISTINCT ON (UPPER(TRIM(pt.default_code)))
        UPPER(TRIM(pt.default_code)) AS part,
        TRIM(pt.category_code) AS fr, TRIM(pt.group_code) AS pg,
        TRIM(pt.sub_group_code) AS psg,
        COALESCE(to_jsonb(pt.name)->>'en_US',
            CASE WHEN jsonb_typeof(to_jsonb(pt.name)) = 'string' THEN pt.name::TEXT END) AS descr
    FROM product_template pt
    WHERE NULLIF(TRIM(pt.default_code), '') IS NOT NULL
    ORDER BY UPPER(TRIM(pt.default_code)), (pt.group_code IS NULL), pt.id
)
SELECT
    SUBSTRING(h.trnh_date, 1, 4)::INT AS yr,
    SUBSTRING(h.trnh_date, 5, 2)::INT AS mth,
    TO_CHAR(TO_DATE(SUBSTRING(h.trnh_date, 5, 2), 'MM'), 'Month') AS month_name,
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
LEFT JOIN unitpart u ON u.part = UPPER(TRIM(d.trnd_part))
LEFT JOIN prod ON prod.part = UPPER(TRIM(d.trnd_part))
WHERE SUBSTRING(h.trnh_date, 1, 4)::INT IN (2025, 2026)
    AND LPAD(TRIM(h.trnh_type), 2, '0') IN ('01', '02')
    AND TRIM(d.trnd_group) = 'MDA'
    AND TRIM(h.trnh_status) IN ('C', 'P')
    AND TRIM(h.trnh_cstno) NOT LIKE 'V%'
    AND COALESCE(TRIM(pcg.code), prod.pg, '') IN (
        'ACACC','ACCON','ACCST','ACPAC','ACPKG','ACAIP',
        'ACPOR','ACVRF','ACWIN','ACWTS','ACHCL','ATOM')
GROUP BY 1, 2, 3
ORDER BY yr ASC, mth ASC;
