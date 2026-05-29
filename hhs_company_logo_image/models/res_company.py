from odoo import api,fields,models,_

class Company(models.Model):
    _inherit = "res.company"


    app_logo_image=fields.Binary("App Image")