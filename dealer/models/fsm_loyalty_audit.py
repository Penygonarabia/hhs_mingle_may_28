from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FSMLoyaltyAudit(models.Model):
    _name = 'fsm.loyalty.audit'
    _description = 'FSM Loyalty Audit'
    _order = 'date_time desc'

    date_time = fields.Datetime(default=fields.Datetime.now)

    dealer_id = fields.Many2one('res.partner', required=True)
    salesman_id = fields.Many2one('res.users', required=True)
    location_id = fields.Many2one('res.partner')

    type = fields.Selection([
        ('1', 'Sales'),
        ('2', 'Credit Note'),
        ('3', 'Redemption')
    ], required=True)

    qty = fields.Float()
    loyalty_points = fields.Float()
    amount_paid = fields.Float(default=0)
    notes = fields.Text()
    reference = fields.Char()
    sales_id = fields.Many2one('dsales.showroom.sales', string='Sales Record', ondelete='cascade')

    type_order = fields.Integer(compute='_compute_type_order', store=True)

    @api.depends('type')
    def _compute_type_order(self):
        for record in self:
            if record.type == '1':
                record.type_order = 1  # Sales first
            elif record.type == '2':
                record.type_order = 2  # CreditNote second
            elif record.type == '3':
                record.type_order = 3  # Redemption last

    @api.model
    def get_ordered_data(self):
        # This will fetch records sorted by the predefined order of `type` values
        ordered_types = ['S', 'C', 'R']  # Define the desired order
        domain = [('type', 'in', ordered_types)]  # Make sure to fetch all required types
        records = self.search(domain)  # Fetch the records

        # Optionally, you could sort records manually if needed
        # Sorting here will make sure records are returned in the desired order of 'S', 'C', 'R'
        sorted_records = sorted(records, key=lambda x: ordered_types.index(x.type))
        return sorted_records

    @api.model
    def get_date_filter_domain(self):
        today = fields.Date.today()
        first_of_month = today.replace(day=1)
        last_of_month = (first_of_month + relativedelta(day=31))
        return [('date_time', '>=', first_of_month), ('date_time', '<=', last_of_month)]