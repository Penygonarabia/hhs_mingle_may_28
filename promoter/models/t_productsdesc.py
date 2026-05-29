# from odoo import models, fields

# class TProductsDesc(models.Model):
#     _name = 't.productsdesc'
#     _description = 'Product Description (from SQL table)'
#     _table = 't_productsdesc'
#     _auto = False  # Important: since this is a custom SQL table
#     _rec_name = 'p_desc'

#     id = fields.Integer(string='ID', required=True)
#     lang_flag = fields.Integer(string='Lang Flag')
#     create_uid = fields.Integer(string='Created By')
#     write_uid = fields.Integer(string='Modified By')
#     p_code = fields.Char(string='Product Code')
#     p_desc = fields.Char(string='Product Description')
#     p_grp = fields.Char(string='Product Group')
#     p_lang = fields.Char(string='Product Language')
#     user_lmd = fields.Char(string='User Last Modified')
#     create_date = fields.Datetime(string='Created On')
#     write_date = fields.Datetime(string='Last Modified On')
