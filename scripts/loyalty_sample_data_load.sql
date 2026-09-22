-- Sample data for PBI Dashboards > Loyalty Dashboards > Loyalty Analysis
-- (pbi_loyalty_dashboards/controllers/loyalty_main.py). Uses existing tables
-- and columns only -- no new fields, no module changes.
--
-- What it writes
--   customer_tier         Bronze / Silver / Gold / Platinum (skipped if a name exists)
--   lp_setup_promotions   4 promotions, reference 'SMP-PR-*', ARCHIVED (active=false)
--                         so no app/API/ORM search ever offers them to a customer;
--                         the dashboard reads them by SQL, which ignores active
--   res_partner           ~260 existing customers flagged as loyalty members, with
--                         a tier and an activation_date spread over 2025-2026
--   transaction_header    synthetic Invoice (01) / Credit Note (02) / Redeem (98) docs,
--   transaction_details   trnh_no 'SMP*', trnh_source 'SAMPLE_LOYALTY'
--
-- Why it cannot leak into anything else
--   * Members have NO email, mobile or phone: the monthly statement cron only
--     mails partners with an email, and a tier change only WhatsApps a partner
--     with a mobile/phone.
--   * Members have res_maxinvoicedate NULL and tier thresholds start at 500
--     points, while their customer_loyalty_points_history balance is 0: the
--     daily "Auto Process Customer Tiers" cron finds no matching tier and, with
--     no max invoice date, leaves the tier alone (no write, no history row).
--   * Sample docs are trnh_status 'N' (not posted) and non-MDA lines, so every
--     sales board (v_pbi_sales_sman_fact: status C/P + MDA) and every
--     Configurations defect check (MDA only) ignores them; trnh_sman and
--     trnh_cityid stay NULL, so bring-up's city/salesman inference ignores them.
--   * hhs_loyalty_invoice_processor is uninstalled, so nothing converts the
--     sample invoices into points history.
--
-- Undo with scripts/loyalty_sample_data_rollback.sql.
--
-- Run (the file leaves the transaction open; append COMMIT or ROLLBACK):
--   (cat scripts/loyalty_sample_data_load.sql; echo 'COMMIT;') \
--     | docker exec -i cloud-db-1 psql -U odoo -d dbprod -X -v ON_ERROR_STOP=1

BEGIN;
SELECT setseed(0.4217);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM transaction_header WHERE trnh_source = 'SAMPLE_LOYALTY') THEN
        RAISE EXCEPTION 'Loyalty sample data is already loaded -- run loyalty_sample_data_rollback.sql first';
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- tiers (icons: 12 Bronze Shield, 2 Silver Crown, 1 Gold Crown, 5 Platinum)
-- ---------------------------------------------------------------------------
INSERT INTO customer_tier (name, min_loyalty_points, sort_order, tier_icon,
                           create_uid, write_uid, create_date, write_date)
VALUES ('Bronze',     500, 1, 12, 1, 1, now(), now()),
       ('Silver',    2000, 2,  2, 1, 1, now(), now()),
       ('Gold',      5000, 3,  1, 1, 1, now(), now()),
       ('Platinum', 10000, 4,  5, 1, 1, now(), now())
ON CONFLICT (name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- promotions
-- ---------------------------------------------------------------------------
INSERT INTO lp_setup_promotions (promotion_reference, promotion_name,
                                 promotion_start_date, promotion_end_date,
                                 active, select_all_customers, sort_order,
                                 create_uid, write_uid, create_date, write_date)
VALUES ('SMP-PR-2511', 'Winter Warm-Up Bonus',   '2025-11-01', '2026-01-31', false, true, 1, 1, 1, now(), now()),
       ('SMP-PR-2602', 'Ramadan Double Points',  '2026-02-15', '2026-03-31', false, true, 2, 1, 1, now(), now()),
       ('SMP-PR-2605', 'Summer Cooling Rewards', '2026-05-01', '2026-08-31', false, true, 3, 1, 1, now(), now()),
       ('SMP-PR-2609', 'Back-to-School Bonus',   '2026-09-01', '2026-09-30', false, true, 4, 1, 1, now(), now());

-- ---------------------------------------------------------------------------
-- members: existing customers that resolve to a region/city the same way the
-- dashboard does, with no contact channel at all
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE smp_member ON COMMIT DROP AS
WITH cand AS (
    SELECT DISTINCT ON (p.id)
           p.id, p.ref, p.name, sub.sr_region, sub.sr_code
    FROM res_partner p
    JOIN customer c ON c.cst_no = p.ref
    JOIN t_subregions sub ON sub.sr_code = UPPER(TRIM(c.cst_subregion))
    WHERE p.active
      AND COALESCE(p.email, '') = ''
      AND COALESCE(p.mobile, '') = ''
      AND COALESCE(p.phone, '') = ''
      AND p.res_maxinvoicedate IS NULL
      AND NOT COALESCE(p.activate_loyalty_feature, false)
      AND (SELECT count(*) FROM res_partner p2 WHERE p2.ref = p.ref) = 1
    ORDER BY p.id
), ranked AS (
    SELECT cand.*, row_number() OVER (PARTITION BY sr_code ORDER BY md5(ref)) AS rn
    FROM cand
), picked AS (
    SELECT * FROM ranked
    WHERE rn <= CASE sr_code WHEN 'RYD' THEN 70 WHEN 'JED' THEN 50 WHEN 'KHO' THEN 45
                             WHEN 'QAS' THEN 20 ELSE 10 END
    ORDER BY id
), rnd AS (
    SELECT picked.*, random() AS r_tier, random() AS r_act, random() AS r_day
    FROM picked
)
SELECT id, ref, name, sr_region, sr_code,
       CASE WHEN r_tier < 0.45 THEN 'Bronze'
            WHEN r_tier < 0.75 THEN 'Silver'
            WHEN r_tier < 0.92 THEN 'Gold'
            ELSE 'Platinum' END AS tier,
       CASE WHEN r_act < 0.25 THEN date '2025-01-01' + floor(r_day * 365)::int
            WHEN r_act < 0.37 THEN date '2026-09-01' + floor(r_day * 17)::int
            ELSE date '2026-01-01' + floor(r_day * 243)::int END AS activation_date
FROM rnd;

-- salesman + warehouse: the customer's own most frequent real values, else a
-- regional default
CREATE TEMP TABLE smp_member_ctx ON COMMIT DROP AS
SELECT m.*,
       COALESCE((SELECT h.trnh_salesmanname FROM transaction_header h
                  WHERE h.trnh_cstno = m.ref AND COALESCE(h.trnh_salesmanname, '') <> ''
                  GROUP BY 1 ORDER BY count(*) DESC, 1 LIMIT 1),
                (SELECT s FROM (VALUES ('10', 'Central Sales Desk'), ('20', 'Western Sales Desk'),
                                       ('30', 'Eastern Sales Desk')) v(r, s) WHERE v.r = m.sr_region)
       ) AS salesman,
       COALESCE((SELECT h.trnh_whouse FROM transaction_header h
                  WHERE h.trnh_cstno = m.ref AND COALESCE(h.trnh_whouse, '') <> ''
                  GROUP BY 1 ORDER BY count(*) DESC, 1 LIMIT 1),
                CASE m.sr_region WHEN '10' THEN '101' WHEN '20' THEN '201' ELSE '301' END
       ) AS whouse
FROM smp_member m;

UPDATE res_partner p
SET activate_loyalty_feature = true,
    activation_date = m.activation_date,
    customer_tier_id = t.id,
    tier_name = t.name,
    write_date = now(),
    write_uid = 1
FROM smp_member m
JOIN customer_tier t ON t.name = m.tier
WHERE p.id = m.id;

-- ---------------------------------------------------------------------------
-- part pool: real non-MDA parts with a real price (MDA stays untouched so no
-- Midea sales board or defect check can see these lines)
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE smp_part ON COMMIT DROP AS
SELECT row_number() OVER (ORDER BY part) AS n, part, grp, descr, price
FROM (
    SELECT TRIM(trnd_part) AS part, max(TRIM(trnd_group)) AS grp, max(trnd_desc) AS descr,
           round(percentile_cont(0.5) WITHIN GROUP (ORDER BY trnd_price)::numeric, 2) AS price
    FROM transaction_details
    WHERE TRIM(trnd_group) IN ('BKO', 'CDY')
      AND NULLIF(TRIM(trnd_part), '') IS NOT NULL
      AND trnd_price > 0
    GROUP BY 1
    HAVING count(*) >= 5
) x;

-- ---------------------------------------------------------------------------
-- invoices (01): more and bigger for higher tiers, dated after activation
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE smp_doc (
    hid int, doc_type varchar, doc_no varchar, doc_date date,
    member_id int, ref varchar, name varchar, salesman varchar, whouse varchar,
    tier varchar, src_hid int
) ON COMMIT DROP;

INSERT INTO smp_doc (hid, doc_type, doc_date, member_id, ref, name, salesman, whouse, tier)
SELECT nextval(pg_get_serial_sequence('transaction_header', 'id')), '01',
       m.activation_date + floor(random() * (date '2026-09-17' - m.activation_date + 1))::int,
       m.id, m.ref, m.name, m.salesman, m.whouse, m.tier
FROM smp_member_ctx m
CROSS JOIN LATERAL generate_series(1, CASE m.tier WHEN 'Bronze' THEN 2 WHEN 'Silver' THEN 3
                                                  WHEN 'Gold' THEN 5 ELSE 7 END
                                      + floor(random() * 2)::int) g;

CREATE TEMP TABLE smp_line (
    hid int, slno int, part varchar, grp varchar, descr varchar,
    qty numeric, price numeric, regular numeric, bonus numeric, promo varchar
) ON COMMIT DROP;

INSERT INTO smp_line (hid, slno, part, grp, descr, qty, price)
SELECT d.hid, g, sp.part, sp.grp, sp.descr,
       1 + floor(random() * CASE d.tier WHEN 'Platinum' THEN 20 WHEN 'Gold' THEN 12 ELSE 6 END),
       sp.price
FROM smp_doc d
CROSS JOIN LATERAL generate_series(1, 1 + floor(random() * 3)::int + d.hid * 0) g  -- d.hid: re-roll per doc
CROSS JOIN LATERAL (SELECT floor(random() * (SELECT count(*) FROM smp_part))::int + 1 + g * 0 + d.hid * 0 AS pick) r
JOIN smp_part sp ON sp.n = r.pick;

-- 1 point per SAR 10; lines inside a promotion window use it 45% of the time
-- and earn half as much again as bonus points
UPDATE smp_line l
SET promo = pr.promotion_reference
FROM smp_doc d, lp_setup_promotions pr
WHERE d.hid = l.hid
  AND pr.promotion_reference LIKE 'SMP-PR-%'
  AND d.doc_date BETWEEN pr.promotion_start_date AND pr.promotion_end_date
  AND random() < 0.45;

UPDATE smp_line
SET regular = round(qty * price / 10),
    bonus = CASE WHEN promo IS NOT NULL THEN round(qty * price / 20) ELSE 0 END;

-- ---------------------------------------------------------------------------
-- credit notes (02): ~12% of invoices, a partial return of their first line
-- ---------------------------------------------------------------------------
INSERT INTO smp_doc (hid, doc_type, doc_date, member_id, ref, name, salesman, whouse, tier, src_hid)
SELECT nextval(pg_get_serial_sequence('transaction_header', 'id')), '02',
       LEAST(d.doc_date + 1 + floor(random() * 14)::int, date '2026-09-17'),
       d.member_id, d.ref, d.name, d.salesman, d.whouse, d.tier, d.hid
FROM smp_doc d
WHERE d.doc_type = '01' AND random() < 0.12;

INSERT INTO smp_line (hid, slno, part, grp, descr, qty, price, regular, bonus, promo)
SELECT c.hid, 1, l.part, l.grp, l.descr, rq.qty, l.price,
       round(rq.qty * l.price / 10),
       CASE WHEN l.promo IS NOT NULL THEN round(rq.qty * l.price / 20) ELSE 0 END,
       l.promo
FROM smp_doc c
JOIN smp_line l ON l.hid = c.src_hid AND l.slno = 1
CROSS JOIN LATERAL (SELECT GREATEST(1, floor(l.qty * (0.2 + random() * 0.5))) + c.hid * 0 AS qty) rq
WHERE c.doc_type = '02';

-- ---------------------------------------------------------------------------
-- redemptions (98): ~45% of members, 1-2 each, spending 15-45% of what they
-- have earned, on a date after their first invoice
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE smp_earned ON COMMIT DROP AS
SELECT d.member_id,
       sum(CASE WHEN d.doc_type = '02' THEN -1 ELSE 1 END * (l.regular + l.bonus)) AS pts,
       min(d.doc_date) FILTER (WHERE d.doc_type = '01') AS first_inv
FROM smp_doc d JOIN smp_line l ON l.hid = d.hid
GROUP BY 1;

INSERT INTO smp_doc (hid, doc_type, doc_date, member_id, ref, name, salesman, whouse, tier)
SELECT nextval(pg_get_serial_sequence('transaction_header', 'id')), '98',
       e.first_inv + floor(random() * (date '2026-09-17' - e.first_inv + 1))::int + m.id * 0,
       m.id, m.ref, m.name, m.salesman, m.whouse, m.tier
FROM smp_member_ctx m
JOIN smp_earned e ON e.member_id = m.id AND e.pts > 0
CROSS JOIN LATERAL generate_series(1, 1 + floor(random() * 2)::int + m.id * 0) g
WHERE (hashtext(m.ref) & 1023) < 460;

INSERT INTO smp_line (hid, slno, part, grp, descr, qty, price, regular, bonus)
SELECT d.hid, 1, NULL, NULL, 'Loyalty points redemption', 1, 0,
       round(e.pts * (0.15 + random() * 0.30) / 2), 0
FROM smp_doc d
JOIN smp_earned e ON e.member_id = d.member_id
WHERE d.doc_type = '98';

UPDATE smp_doc SET doc_no = 'SMP' || lpad(hid::text, 8, '0');

-- ---------------------------------------------------------------------------
-- write the feed rows
-- ---------------------------------------------------------------------------
INSERT INTO transaction_header (id, trnh_type, trnh_whouse, trnh_no, trnh_date, trnh_time,
                                trnh_cstno, trnh_cstname, trnh_status, trnh_source,
                                trnh_salesmanname, trnh_tiername, trnh_partner_id,
                                trnh_total, trnh_detrowscount, trnh_referenceno,
                                create_uid, write_uid, create_date, write_date)
SELECT d.hid, d.doc_type, d.whouse, d.doc_no, to_char(d.doc_date, 'YYYYMMDD'),
       lpad((8 + floor(random() * 10))::int::text, 2, '0') || ':' || lpad(floor(random() * 60)::int::text, 2, '0'),
       d.ref, d.name, 'N', 'SAMPLE_LOYALTY',
       d.salesman, d.tier, d.member_id,
       COALESCE((SELECT sum(l.qty * l.price) FROM smp_line l WHERE l.hid = d.hid), 0),
       (SELECT count(*) FROM smp_line l WHERE l.hid = d.hid),
       (SELECT s.doc_no FROM smp_doc s WHERE s.hid = d.src_hid),
       1, 1, now(), now()
FROM smp_doc d;

INSERT INTO transaction_details (header_id, trnd_type, trnd_whouse, trnd_no, trnd_slno,
                                 trnd_part, trnd_group, trnd_desc, trnd_qtyiss, trnd_qtyreq,
                                 trnd_price, trnd_lpoint, trnd_regularpts, trnd_bonuspts,
                                 trnd_promoref, create_uid, write_uid, create_date, write_date)
SELECT d.hid, d.doc_type, d.whouse, d.doc_no, l.slno,
       l.part, l.grp, l.descr, l.qty, l.qty,
       l.price,
       CASE WHEN d.doc_type = '98' THEN l.regular * 2 ELSE l.regular + l.bonus END,
       CASE WHEN d.doc_type = '98' THEN NULL ELSE l.regular END,
       CASE WHEN d.doc_type = '98' THEN NULL ELSE l.bonus END,
       l.promo, 1, 1, now(), now()
FROM smp_doc d
JOIN smp_line l ON l.hid = d.hid;

SELECT d.doc_type, count(DISTINCT d.hid) AS docs, count(*) AS lines
FROM smp_doc d JOIN smp_line l ON l.hid = d.hid
GROUP BY 1 ORDER BY 1;
SELECT tier, count(*) AS members FROM smp_member GROUP BY 1 ORDER BY 1;
