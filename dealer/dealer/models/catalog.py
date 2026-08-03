from odoo import models, fields

class Catalog(models.Model):
    _name = 'catalog.catalog'
    _description = 'Catalog (External SQL Table)'
    _table = 'catalog'
    _auto = False
    _rec_name = 'cat_desc'  

    id = fields.Integer(string='ID', required=True)
    create_uid = fields.Integer(string='Created By')
    write_uid = fields.Integer(string='Updated By')
    create_date = fields.Datetime(string='Created On')
    write_date = fields.Datetime(string='Last Updated On')
    user_id = fields.Char(string='User ID')
    user_lmd = fields.Char(string='User LMD')
    user_lmt = fields.Char(string='User LMT')
    lang_flag = fields.Char(string='Lang Flag')
    lang_flag2 = fields.Char(string='Lang Flag 2')

    # Common display fields
    cat_desc = fields.Char(string='Description')
    cat_desc2 = fields.Char(string='Description 2')
    cat_sdesc = fields.Char(string='Short Description')
    cat_sdesc2 = fields.Char(string='Short Description 2')
    cat_part = fields.Char(string='Part Code')
    cat_pcode = fields.Char(string='Product Code')
    cat_pgroup = fields.Char(string='Product Group')
    cat_psgroup = fields.Char(string='Product Sub Group')
    cat_grp = fields.Char(string='Group')
    cat_pgtype = fields.Char(string='Product Group Type')
    cat_type = fields.Char(string='Product Type')

    # Optional: Add more important fields as needed
    cat_barcode = fields.Char(string='Barcode')
    cat_model = fields.Char(string='Model')
    cat_itemtype = fields.Char(string='Item Type')
    cat_uom = fields.Char(string='UOM')
    cat_stock = fields.Char(string='Stock Status')
    cat_obsolete = fields.Char(string='Obsolete Status')
    cat_image = fields.Char(string='Image Path')

    # You can add remaining fields if you need them later
    # Example:
    # cat_uwt = fields.Char(string='Unit Weight')
    # detail1 = fields.Char(string='Detail 1')
    # detail2 = fields.Char(string='Detail 2')
