-- Removes everything scripts/loyalty_sample_data_load.sql wrote.
--   docker exec -i cloud-db-1 psql -U odoo -d dbprod -X -v ON_ERROR_STOP=1 \
--     < scripts/loyalty_sample_data_rollback.sql

BEGIN;

-- members are exactly the customers the sample docs were written for
UPDATE res_partner p
SET activate_loyalty_feature = false,
    activation_date = NULL,
    customer_tier_id = NULL,
    tier_name = NULL,
    write_date = now(),
    write_uid = 1
WHERE p.id IN (SELECT DISTINCT trnh_partner_id FROM transaction_header
               WHERE trnh_source = 'SAMPLE_LOYALTY');

DELETE FROM customer_tier_movement_history
WHERE customer_id IN (SELECT DISTINCT trnh_partner_id FROM transaction_header
                      WHERE trnh_source = 'SAMPLE_LOYALTY');

DELETE FROM transaction_details
WHERE header_id IN (SELECT id FROM transaction_header WHERE trnh_source = 'SAMPLE_LOYALTY');

DELETE FROM transaction_header WHERE trnh_source = 'SAMPLE_LOYALTY';

DELETE FROM lp_setup_promotions WHERE promotion_reference LIKE 'SMP-PR-%';

-- the four sample tiers, unless something real has started using them
DELETE FROM customer_tier t
WHERE t.name IN ('Bronze', 'Silver', 'Gold', 'Platinum')
  AND NOT EXISTS (SELECT 1 FROM res_partner p WHERE p.customer_tier_id = t.id)
  AND NOT EXISTS (SELECT 1 FROM lp_setup_promotions_tiers pt WHERE pt.tier_id = t.id)
  AND NOT EXISTS (SELECT 1 FROM customer_tier_movement_history h
                  WHERE h.old_tier_id = t.id OR h.new_tier_id = t.id);

COMMIT;
