from odoo import models, fields

class MainProductsDesc(models.Model):
    _name = 't.mainproductsdesc'
    _description = 'Main Products Description'
    _table = 't_mainproductsdesc'
    # _auto = False   # 🔥 important because table already exists

    mp_grp = fields.Char(string="Group", size=3)
    mp_code = fields.Char(string="Code", size=20)
    mp_lang = fields.Integer(string="Language")
    mp_desc = fields.Char(string="Description", size=100)
    lang_flag = fields.Integer(string="Lang Flag")