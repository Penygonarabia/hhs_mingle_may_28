from lxml import etree

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError


partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer/Vendor",
        store=True, readonly=False, ondelete='restrict',
        compute='_compute_partner_id',
        domain="[('parent_id','=', False), ('is_company','=', True),('partner_types','=', 'customer')]",
        tracking=True,
        check_company=True)

    # domain = [
    #     ('type', '!=', 'private'),
    #     ('company_id', 'in', (False, company_id)),
    #     '|',
    #     '&', ('partner_types', '=', 'both'),
    #     ('partner_types', '=', 'customer' if move_type in ['out_invoice', 'out_refund', 'out_receipt'] else 'vendor')
    # ],
