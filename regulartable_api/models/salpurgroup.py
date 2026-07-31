from odoo import models, fields


class TSalPurGroup(models.Model):
    _name = "t.salpurgroup"
    _description = "Sales Purchase Group"

    spg_type = fields.Char("Type")
    spg_code = fields.Char("Code", required=True)
    spg_lang = fields.Char("Language", required=True)
    spg_desc = fields.Char("Description")
    user_id = fields.Char("User ID")
    user_lmd = fields.Char("Last Modified")
    lang_flag = fields.Char("Language Flag")

    _sql_constraints = [
        (
            "spg_code_lang_unique",
            "unique(spg_code, spg_lang)",
            "SPG Code and Language already exist."
        )
    ]