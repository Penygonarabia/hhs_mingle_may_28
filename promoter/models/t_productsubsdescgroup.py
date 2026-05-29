from odoo import models, fields

class TProductSubsDescGroup(models.Model):
    _name = 't.productsubsdescgroup'
    _description = 'Product Sub Description Group (from SQL table)'
    _table = 't_productsubsdescgroup'  # Actual SQL table name
    _auto = False
    _rec_name = 'psg_desc'  # Use this as label in dropdowns

    id = fields.Integer(string='ID', required=True)
    create_uid = fields.Integer(string='Created By')
    write_uid = fields.Integer(string='Modified By')
    lang_flag = fields.Char(string='Lang Flag')
    psg_desc = fields.Char(string='Subgroup Description')  # This appears in dropdowns
    psg_grp = fields.Char(string='Group Code')
    psg_lang = fields.Char(string='Language')
    psg_pcode = fields.Char(string='Product Code')
    psg_psub = fields.Char(string='Subgroup Code')
    user_lmd = fields.Char(string='Last Modified User')
    create_date = fields.Datetime(string='Created On')
    write_date = fields.Datetime(string='Last Modified On')
