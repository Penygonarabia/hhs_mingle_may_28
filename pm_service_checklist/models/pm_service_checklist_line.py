from odoo import models, fields, api

class PMServiceChecklistLine(models.Model):
    _name = 'pm.service.checklist.line'
    _description = 'PM Service Checklist Line'
    _order = "id"

    service_order_id = fields.Many2one(
        'service.sale.order',
        string="Service Order",
        required=True,
        ondelete='cascade'
    )
    service_unit_type_id = fields.Many2one(
        'product.product',
        string="Service Unit Type",
        domain="[('detailed_type', '=', 'service')]",
        required=True
    )
    unit_sub_type_id = fields.Selection([
        ('indoor', 'Indoor'),
        ('outdoor', 'Outdoor')
    ], string="Unit Sub Type")
    service_type_id = fields.Selection([
        ('major', 'Major'),
        ('minor', 'Minor'),
        ('both', 'Major/Minor')
    ], string="Service Type", required=True)
    is_selected = fields.Boolean(
        string="Yes/No",
        default=True
    )
    print_always_default = fields.Boolean(
        string="Print Always",
        default=False
    )

    sort_order = fields.Integer(default=10)
    # sort_order_header = fields.Integer(
    #     string="Sort Order"
    # )
    #sequence = fields.Integer(default=10)