from odoo import models, fields, api, _
from odoo.exceptions import UserError, warnings, ValidationError


class CustomerLoyaltyResPartner(models.Model):
    _inherit = 'res.partner'

    activate_loyalty_feature = fields.Boolean(
        string="Activate Loyalty Feature"
    )
    tier_movement_history_ids = fields.One2many(
        'customer.tier.movement.history', 'customer_id')

    activation_date = fields.Date(
        string="Activation Date"
    )

    redemption_deadline = fields.Date(
        string="Redemption Deadline"
    )

    applicable_loyalty_line_ids = fields.One2many(
        'customer.loyalty.line',
        'partner_id',
        string='Applicable Loyalty Lines'
    )
    tier_name = fields.Char(
        string="Tier",
        # compute="_compute_tier_name",
        store=True,
        # related='customer_tier_id.name',
    )
    salesman_code = fields.Char(string="Salesman Code")
    salesman_name = fields.Char(string="Salesman Name")

    collected_points_regular = fields.Integer(
        string="Collected",
        compute="_compute_loyalty_points",
        store=True
    )

    redeem_points_regular = fields.Integer(
        string="Redeem"
    )

    expired_points_regular = fields.Integer(
        string="Expired"
    )

    balance_points_regular = fields.Integer(
        string="Balance"
    )
    collected_points_bonus = fields.Integer(
        string="Collected",
        compute="_compute_loyalty_points",
        store=True
    )

    redeem_points_bonus = fields.Integer(
        string="Redeem"
    )

    expired_points_bonus = fields.Integer(
        string="Expired"
    )

    balance_points_bonus = fields.Integer(
        string="Balance"
    )
    # loyalty_transaction_history_ids = fields.One2many(
    #     'loyalty.transaction.history',
    #     'partner_id',
    #     string='Loyalty Transaction History'
    # )
    loyalty_transaction_ids = fields.One2many('customer.loyalty.points.history', 'partner_id',
                                              string='Loyalty Transactions',compute = "_load_loyalty_transactions")

    loyalty_points = fields.Integer(
        string='Points'
    )

    redeemed_points = fields.Integer(
        string='Redeemed'
    )

    balance_points = fields.Integer(
        string='Balance'
    )
    invoice_points_bonus = fields.Integer(string='Invoice Points')
    credit_note_points_bonus = fields.Integer(string='Credit Note Points')
    invoice_points_regular=fields.Integer(string='Invoice Points Regular')
    credit_note_points_regular=fields.Integer(sting='Credit Note Points Regular')

    # @api.onchange('partner_type_hhs')
    # def _prepare_loyalty_transactions(self):
    #     vals_list = [(5, 0, 0)]
    #     print(".111111111111111111")
    #     history_records = self.env['customer.loyalty.points.history'].sudo().search([
    #         ('clph_cstcode', '=', self.ref)
    #     ])
    #     print(".2222222222222222222")
    #
    #     for history in history_records:
    #         print("..........history",history.clph_cstcode)
    #         vals_list.append((0, 0, {
    #             'type': history.type,
    #             'clph_whouse': history.clph_whouse,
    #             'clph_docnumber': history.clph_docnumber,
    #             'clph_datetime': history.clph_datetime,
    #             'clph_points': history.clph_points,
    #             'clph_bonuspoints': history.clph_bonuspoints,
    #             'clph_note': history.clph_note,
    #         }))
    #
    #     self.loyalty_transaction_ids = vals_list

    def _load_loyalty_transactions(self):
        for rec in self:
            history_ids = self.env['customer.loyalty.points.history'].sudo().search([
                ('clph_cstcode', '=', rec.ref)
            ])

            rec.loyalty_transaction_ids = [(6, 0, history_ids.ids)]

    @api.onchange('partner_type_hhs')
    def _on_change_partner_type(self):
        for rec in self:
            print(".........11111111111111111111")
            customer_loyalty_points_search = self.env['customer.loyalty.points.history'].sudo().search([
                ('clph_cstcode', '=', rec.ref)
            ])
            print("....................cust")
            customer_lst = [(5, 0, 0)]
            for customer in customer_loyalty_points_search:

                print(".................customer",customer.clph_cstid,customer.clph_cstcode)
                history_vals = {

                    'type': customer.type,
                    'clph_whouse': customer.clph_whouse,
                    'clph_docnumber': customer.clph_docnumber,
                    'clph_datetime': customer.clph_datetime,
                    'clph_points': customer.clph_points,
                    'clph_bonuspoints': customer.clph_bonuspoints,
                    'clph_note': customer.clph_note

                }
                customer_lst.append((0, 0, history_vals))
            rec.loyalty_transaction_ids = customer_lst


            # self.env.cr.execute("""
            #     SELECT id, sm_code, sm_name, user_id
            #     FROM sl_salesman
            # """)
            #
            # salesmen = self.env.cr.dictfetchall()
            #
            # for salesman in salesmen:
            #     if rec.ref == salesman.get('sm_code'):
            #         print("Match Found")
            #         print("Partner Ref:", rec.ref)
            #         print("Salesman:", salesman)
            #
            #         rec.salesman_code = salesman.get('sm_code')
            #         rec.salesman_name = salesman.get('sm_name')
            #         break

    # @api.depends('balance_points_regular','collected_points_regular','expired_points_bonus','redeem_points_regular')
    # def _compute_tier_name(self):
    #     for rec in self:
    #         rec.tier_name = False
    #         print("tier_name", rec.balance_points_regular)
    #         tiers = self.env['customer.tier'].search(
    #             [],
    #         )
    #         for tier in tiers:
    #             if rec.balance_points_regular >= tier.min_loyalty_points:
    #                 rec.tier_name = tier.name
    #                 break
    #             print("tier_name",tier.name)

    # @api.depends('balance_points')
    # def _compute_tier_name(self):
    #     for rec in self:
    #         if rec.balance_points:
    #             customer_points_search = self.env['customer.tier'].search([])
    #             for line in customer_points_search:
    #
    #                 if rec.balance_points > line.min_loyalty_points and rec.balance_points < line.min_loyalty_points:
    #                     rec.tier_name = line.name
    # print("tier_nameeeeeeeeeeeeeeeeeeee",rec.tier_name)

    def read(self, fields=None, load='_classic_read'):
        res = super(CustomerLoyaltyResPartner, self).read(fields, load)
        for rec in self:
            rec._compute_loyalty_points()
            rec._load_loyalty_transactions()

            # rec._on_change_partner_type()
            # rec._compute_tier_name()
        return res

    # @api.depends('loyalty_transaction_history_ids')
    def _compute_loyalty_points(self):

        for rec in self:
            history = self.env['customer.loyalty.points.history'].search([
                ('clph_cstid', '=', rec.id)
            ])

            # -----------------------------
            # REGULAR
            # -----------------------------

            regular_history = history.filtered(
                lambda x: x.clph_doctype == '99'
            )
            total_points = 0
            for line in history:

                # ADDITION
                if line.clph_adjtype == '+':
                    total_points += line.clph_regpoints
                # DEDUCTION
                elif line.clph_adjtype == '-':
                    total_points -= line.clph_regpoints
            # print("regular_history",line.clph_regpoints)
            # FINAL VALUE
            rec.collected_points_regular = total_points
            rec.redeem_points_regular = sum(
                history.filtered(
                    lambda x: str(x.clph_doctype) == '98'
                ).mapped('clph_regpoints')
            )

            rec.expired_points_regular = sum(
                history.filtered(
                    lambda x: str(x.clph_doctype) == '97'
                ).mapped('clph_regpoints')
            )
            rec.invoice_points_regular = sum(
                history.filtered(
                    lambda x: x.clph_doctype == '01'
                ).mapped('clph_regpoints')
            )

            rec.credit_note_points_regular = sum(
                history.filtered(
                    lambda x: x.clph_doctype == '02'
                ).mapped('clph_regpoints')
            )

            rec.balance_points_regular = (
                    rec.collected_points_regular
                    + rec.invoice_points_regular
                    - rec.credit_note_points_regular
                    - rec.redeem_points_regular
                    - rec.expired_points_regular
            )

            # -----------------------------
            # BONUS
            # -----------------------------

            rec.collected_points_bonus = sum(
                history.filtered(
                    lambda x: str(x.clph_doctype) == '99'
                ).mapped('clph_bonuspoints')
            )

            rec.redeem_points_bonus = sum(
                history.filtered(
                    lambda x: str(x.clph_doctype) == '98'
                ).mapped('clph_bonuspoints')
            )

            rec.expired_points_bonus = sum(
                history.filtered(
                    lambda x: str(x.clph_doctype) == '97'
                ).mapped('clph_bonuspoints')
            )

            rec.invoice_points_bonus = sum(
                history.filtered(
                    lambda x: x.clph_doctype == '01'
                ).mapped('clph_bonuspoints')
            )

            rec.credit_note_points_bonus = sum(
                history.filtered(
                    lambda x: x.clph_doctype == '02'
                ).mapped('clph_bonuspoints')
            )

            rec.balance_points_bonus = (
                    rec.collected_points_bonus
                    + rec.invoice_points_bonus
                    - rec.credit_note_points_bonus
                    - rec.redeem_points_bonus
                    - rec.expired_points_bonus
            )

    # def generate_loyalty_transaction_history(self):
    #     history_search=self.env['customer.loyalty.points.history'].search([('clph_cstid','=',self.id)],limit=1)
    #     self.env['loyalty.transaction.history'].create({
    #         'partner_id': history_search.id,
    #         # 'loyalty_points': loyalty_points,
    #         # 'redeemed_points': redeemed_points,
    #         # 'balance_points': balance_points,
    #         'clph_docnumber': history_search.clph_docnumber or '',
    #         # 'clph_points': total_points,
    #         'clph_whouse': '0',
    #         'clph_note': history_search.clph_note or '',
    #         'clph_datetime': fields.Datetime.now(),
    #
    #     })

    @api.onchange('activate_loyalty_feature')
    def _onchange_activate_loyalty_feature(self):
        for rec in self:
            if rec.activate_loyalty_feature:
                rec.activation_date = fields.Date.today()
            else:
                rec.activation_date = False


class CustomerLoyaltyLine(models.Model):
    _name = 'customer.loyalty.line'
    _description = 'Customer Loyalty Line'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer'
    )

    product_id = fields.Many2one(
        'product.product',
        string="Product"
    )

    loyalty_points = fields.Integer(
        string="Points"
    )

    @api.constrains('loyalty_points')
    def _check_loyalty_points_limit(self):

        limit = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'hhs_loyalty_management.customer_loyalty_point_limit',
                default=0
            )
        )
        for rec in self:

            if rec.loyalty_points and limit:

                if rec.loyalty_points > limit:
                    raise ValidationError(
                        _("Number of Points cannot exceed %s.") % limit
                    )

    @api.constrains('partner_id', 'product_id')
    def _check_duplicate_product(self):

        for rec in self:

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('partner_id', '=', rec.partner_id.id),
                ('product_id', '=', rec.product_id.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    "Duplicate Product are not allowed for this Customer."
                )

# class LoyaltyTransactionHistory(models.Model):
#     _name = 'loyalty.transaction.history'
#     _description = 'Loyalty Transaction History'
#     _order = 'clph_datetime desc'
#
#     partner_id = fields.Many2one(
#         'res.partner',
#         string='Customer'
#     )
#
#     loyalty_points = fields.Integer(
#         string='Regular Points'
#     )
#
#     redeemed_points = fields.Integer(
#         string='Redeemed'
#     )
#
#     balance_points = fields.Integer(
#         string='Balance'
#     )
#
#     clph_docnumber = fields.Char(
#         string='Reference'
#     )
#
#     clph_points = fields.Integer(
#         string='Regular Points'
#     )
#
#     clph_whouse = fields.Char(
#         string='W/H'
#     )
#
#     clph_note = fields.Text(
#         string='Notes'
#     )
#
#     clph_datetime = fields.Datetime(
#         string='Date'
#     )
#     # clph_bonuspoints=fields.Char(string='Bonus Points')
#     clph_bonuspoint=fields.Integer(string='Bonus Points')
#     type=fields.Char(string='Type')
