from odoo.exceptions import ValidationError
from odoo.exceptions import AccessError
from odoo import models, fields, api, _

class FSMLoyaltyRedemption(models.Model):
    _name = 'fsm.loyalty.redemption'
    _description = 'FSM Loyalty Redemption'
    _rec_name = 'name'
    _order = 'date_time desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="Redemption Reference",
        compute="_compute_name"
    )

    @api.depends()
    def _compute_name(self):
        user = self.env.user
        for rec in self:
            if user.has_group('dealer.group_dealer_user'):
                rec.name = "Redemption"
            else:
                rec.name = "Redemption"

    dealer_id = fields.Many2one('res.partner',domain="[('dealersalesman_required', '=', True)]", required=True)
    dealer_showroom_id = fields.Many2one(
        'dsales.showroom',
        string='Dealer Showroom',
        required=True,
        domain="[('dealer_id', '=', dealer_id)]"
    )
    salesman_id = fields.Many2one('res.users',domain="[('dealer_id', '=', dealer_id), ('dealer_showroom_id', '=', dealer_showroom_id)]", required=True)

    transaction_reference = fields.Char(
        string="Transaction Reference",
        default="New",
        readonly=True,
        copy=False,
    )

    date_time = fields.Datetime(default=fields.Datetime.now)

    points_available = fields.Float(
        string="Available Points",
        compute='_compute_available',
        store=True
    )

    points_redeemed = fields.Float(
    string="Points Redeemed",
    required=True
    )

    payment_reference = fields.Char(string="Payment Reference", required=True)
    amount_paid = fields.Float(
        string="Amount Paid",
        compute='_compute_amount',
        store=True
    )
    notes = fields.Text(string="Notes")
    state = fields.Selection(
        [('draft', 'Draft'), ('processed', 'Processed')],
        string="Status",
        default='draft',
        readonly=True,
        tracking=True
    )

    # ---------------------------
    # Compute Available Points
    # ---------------------------
    @api.depends('dealer_id', 'salesman_id')
    def _compute_available(self):
        Audit = self.env['fsm.loyalty.audit']
        for rec in self:
            if not rec.dealer_id or not rec.salesman_id:
                rec.points_available = 0
                continue

            result = Audit.read_group(
                domain=[
                    ('dealer_id', '=', rec.dealer_id.id),
                    ('salesman_id', '=', rec.salesman_id.id)
                ],
                fields=['loyalty_points:sum'],
                groupby=[]
            )
            rec.points_available = result[0]['loyalty_points'] if result and 'loyalty_points' in result[0] else 0

    # ---------------------------
    # Compute Amount
    # ---------------------------
    @api.depends('points_redeemed')
    def _compute_amount(self):
        point_value = float(self.env['ir.config_parameter'].sudo().get_param('fsm.loyalty_point_value', 0))
        for rec in self:
            rec.amount_paid = rec.points_redeemed * point_value

    # ---------------------------
    # Process Redemption Button
    # ---------------------------
    def action_process(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_("Redemption already processed."))

            if rec.points_redeemed <= 0:
                raise ValidationError(_("Redeemed points must be greater than zero."))

            print("rec.points_redeemed--",rec.points_redeemed,"--rec.points_available",rec.points_available)
            if rec.points_redeemed > rec.points_available:
                raise ValidationError(_("Insufficient loyalty points."))

            # Create negative audit entry
            self.env['fsm.loyalty.audit'].create({
                'date_time': fields.Datetime.now(),
                'dealer_id': rec.dealer_id.id,
                'salesman_id': rec.salesman_id.id,
                'type': '3',
                'qty': 0,
                'loyalty_points': -rec.points_redeemed,
                'amount_paid': rec.amount_paid,
                'reference': rec.transaction_reference,
                'notes':rec.notes
            })

            rec.state = 'processed'

    # ---------------------------
    # Print Loyalty Redemption Button
    # ---------------------------
    def action_print_loyalty_redemption(self):
        for rec in self:
            if rec.state != 'processed':
                raise ValidationError(_("Only processed redemptions can be printed."))

        return self.env.ref('dealer.action_fsm_loyalty_redemption_report').report_action(self)


    @api.model
    def create(self, values):
        if values.get('transaction_reference', 'New') == 'New':
            self.env.cr.execute("SELECT MAX(transaction_reference) FROM fsm_loyalty_redemption WHERE transaction_reference LIKE 'RED%'")
            max_ref = self.env.cr.fetchone()[0]
            if max_ref:
                try:
                    num = int(max_ref[3:])
                    values['transaction_reference'] = f"RED{num + 1:05d}"
                except ValueError:
                    values['transaction_reference'] = "RED00001"
            else:
                values['transaction_reference'] = "RED00001"
            
        """ Prevent creation when state is 'processed' """
        if values.get('state') == 'processed':
            raise AccessError(_("You cannot create records with the 'processed' state."))
        return super().create(values)

    def write(self, values):
        """ Prevent modifications when state is 'processed' """
        if self.state == 'processed':
            raise AccessError(_("You cannot modify records with the 'processed' state."))
        return super().write(values)

    # -------------------------------------------------
    # SQL Constraint
    # -------------------------------------------------
    _sql_constraints = [
        ('points_positive',
         'CHECK(points_redeemed > 0)',
         'Redeemed points must be greater than zero.')
    ]