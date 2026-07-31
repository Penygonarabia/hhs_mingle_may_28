from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    inv_qrcodeexport = fields.Char(
        string='QR Code Export',
        default='N'
    )