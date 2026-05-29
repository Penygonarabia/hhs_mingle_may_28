from odoo import models, fields

class TMainProductsDesc(models.Model):
    _name = 't.mainproductsdesc'
    _description = 'T Main Products Description'
   

    mp_grp = fields.Char(string="Main Product Group")
    mp_code = fields.Char(string="Main Product Code")

    mp_lang = fields.Integer(string="Language")
    mp_desc = fields.Char(string="Description")

    lang_flag = fields.Integer(string="Lang Flag")
