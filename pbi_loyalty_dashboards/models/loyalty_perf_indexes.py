from odoo import models, api


class PbiLoyaltyPerfIndexes(models.AbstractModel):
    _name = 'pbi.loyalty.perf.indexes'
    _description = 'PBI Loyalty Performance Indexes'

    def init(self):
        super().init()
        self._create_indexes()

    @api.model
    def _create_indexes(self):
        indexes = [
            "CREATE INDEX IF NOT EXISTS res_partner_loyalty_ref_idx ON res_partner (ref) WHERE activate_loyalty_feature = true;",
            "CREATE INDEX IF NOT EXISTS transaction_header_cst_type_date_idx ON transaction_header (trnh_cstno, trnh_type, trnh_date);",
            "CREATE INDEX IF NOT EXISTS transaction_header_cst_date_idx ON transaction_header (trnh_cstno, trnh_date);",
            "CREATE INDEX IF NOT EXISTS transaction_details_trnd_no_whouse_idx ON transaction_details (trnd_no, trnd_whouse);",
            "CREATE INDEX IF NOT EXISTS customer_cst_subregion_upper_idx ON customer (upper(trim(cst_subregion)));",
            "CREATE INDEX IF NOT EXISTS t_subregions_sr_code_idx ON t_subregions (sr_code);",
            "CREATE INDEX IF NOT EXISTS t_subregions_sr_region_idx ON t_subregions (sr_region);",
            "CREATE INDEX IF NOT EXISTS t_regionsdesc_r_code_lang_idx ON t_regionsdesc (r_code, r_lang);",
            "CREATE INDEX IF NOT EXISTS t_subregionsdesc_sr_code_lang_idx ON t_subregionsdesc (sr_code, sr_lang);",
            "CREATE INDEX IF NOT EXISTS catalog_cat_part_upper_trim_idx ON catalog (upper(trim(cat_part)));",
            "CREATE INDEX IF NOT EXISTS res_city_code_upper_idx ON res_city (upper(trim(code)));",
        ]
        for idx in indexes:
            try:
                self.env.cr.execute(idx)
            except Exception:
                pass
