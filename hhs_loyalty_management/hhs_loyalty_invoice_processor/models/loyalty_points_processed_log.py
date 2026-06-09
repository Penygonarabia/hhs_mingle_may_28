from odoo import models, fields, api


class LoyaltyPointsProcessedLog(models.Model):
    _name = 'loyalty.points.processed.log'
    _description = 'Loyalty Points Processed Log'
    _order = 'created_date_time desc'

    # Processing status - kept as original Selection to avoid DB column conflict
    type = fields.Selection([
        ('error', 'Failed'),
        ('info', 'Success'),
        ('warning', 'Warning'),
    ], string='Status', required=True, default='error')

    # NEW field: ERP Document type code
    # 01=Invoice, 02=Credit Note, 97=Expiry, 98=Redeem, 99=Adjustment
    doc_type = fields.Char(
        string='Doc Type Code',
        help='ERP Document Type: 01=Invoice, 02=Credit Note, 97=Expiry, 98=Redeem, 99=Adjustment'
    )

    doc_type_label = fields.Char(
        string='Type',
        compute='_compute_doc_type_label',
        store=False
    )

    warehouse = fields.Char(string='Warehouse')
    reference = fields.Char(string='Reference/Document No')
    error_message = fields.Text(string='Message')
    sql_statement = fields.Text(string='SQL Statement/Context')
    created_date_time = fields.Datetime(
        string='Created Date & Time',
        default=fields.Datetime.now,
        required=True
    )
    total_price = fields.Float(string='Invoice Price')
    total_discount = fields.Float(string='Discount Amount')
    total_special_discount = fields.Float(string='Customer Spl Discount')
    regular_points = fields.Float(string='Regular Points')
    promotion_points = fields.Float(string='Promotion Points')
    quantity = fields.Integer(string='Invoice Quantity')
    sales_value = fields.Float(string='Sales Value')

    @api.depends('doc_type')
    def _compute_doc_type_label(self):
        type_map = {
            '01': 'Invoice',
            '02': 'Credit Note',
            '97': 'Expiry',
            '98': 'Redeem',
            '99': 'Adjustment',
        }
        for rec in self:
            rec.doc_type_label = type_map.get(rec.doc_type, rec.doc_type or '')
