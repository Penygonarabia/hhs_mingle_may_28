from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 't.productsubs'
    _description = 'Productsubs Model'

    ps_dsirate = fields.Char(string='ps_dsirate')
    ps_duty = fields.Char(string='ps_duty')
    ps_grp = fields.Char(string='ps_grp')
    ps_markup = fields.Char(string='ps_markup')
    ps_mmgrp = fields.Char(string='ps_mmgrp')
    ps_pcat = fields.Char(string='ps_pcat')
    ps_pcode = fields.Char(string='ps_pcode')
    ps_prcgrp = fields.Char(string='ps_prcgrp')
    ps_psub = fields.Char(string='ps_psub')
    ps_psubgroup = fields.Char(string='ps_psubgroup')
    ps_sort = fields.Char(string='ps_sort')
    user_id = fields.Char(string='user_id')
    user_lmd = fields.Char(string='user_lmd')
    user_lmt = fields.Char(string='user_lmt')
