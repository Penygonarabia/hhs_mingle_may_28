# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResCity(models.Model):
    _inherit = "res.city"

    region_id = fields.Many2one(
        "res.region",
        string="Region",
        index=True,
        help="Region to which this city belongs.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("report_region") and not vals.get("region_id"):
                vals["region_id"] = vals["report_region"]
            elif vals.get("region_id") and not vals.get("report_region"):
                vals["report_region"] = vals["region_id"]
        return super(ResCity, self).create(vals_list)

    def write(self, vals):
        if vals.get("report_region") and "region_id" not in vals:
            vals["region_id"] = vals["report_region"]
        elif vals.get("region_id") and "report_region" not in vals:
            vals["report_region"] = vals["region_id"]
        return super(ResCity, self).write(vals)

    def _auto_init(self):
        res = super(ResCity, self)._auto_init()
        try:
            self.env.cr.execute("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'res_city' AND column_name = 'report_region'
                    ) AND EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'res_city' AND column_name = 'region_id'
                    ) THEN
                        -- Populate region_id from report_region if region_id is NULL
                        UPDATE res_city
                        SET region_id = report_region
                        WHERE region_id IS NULL AND report_region IS NOT NULL;

                        -- Keep report_region in sync with region_id
                        UPDATE res_city
                        SET report_region = region_id
                        WHERE report_region IS NULL AND region_id IS NOT NULL;
                    END IF;
                END $$;
            """)
        except Exception:
            pass
        return res
