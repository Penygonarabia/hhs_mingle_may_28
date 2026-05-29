from odoo import models, fields, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    is_reserved = fields.Boolean(string='Is Reserved')


    

