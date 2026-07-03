from odoo import models, fields, api, _
from odoo.exceptions import UserError, warnings, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tier_name = fields.Char(
        string="Tier"
    )

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
    loyalty_transaction_history_ids = fields.One2many(
        'loyalty.transaction.history',
        'partner_id',
        string='Loyalty Transaction History'
    )
    # partner_id = fields.Many2one(
    #     'res.partner',
    #     string='Customer'
    # )
    loyalty_points = fields.Integer(
        string='Points'
    )

    redeemed_points = fields.Integer(
        string='Redeemed'
    )

    balance_points = fields.Integer(
        string='Balance'
    )

    def read(self, fields=None, load='_classic_read'):
        res = super(ResPartner, self).read(fields, load)
        for rec in self:
            rec._compute_loyalty_points()
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

            rec.collected_points_regular = sum(
                history.filtered(
                    lambda x: str(x.clph_doctype) == '99'
                ).mapped('clph_regpoints')
            )

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

            rec.balance_points_regular = (
                    rec.collected_points_regular
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

            rec.balance_points_bonus = (
                    rec.collected_points_bonus
                    - rec.redeem_points_bonus
                    - rec.expired_points_bonus
            )

            regular_total = sum(history.mapped('clph_regpoints'))

            bonus_total = sum(history.mapped('clph_bonuspoints'))

            rec.collected_points_regular = regular_total

            rec.collected_points_bonus = bonus_total



class LoyaltyTransactionHistory(models.Model):
    _name = 'loyalty.transaction.history'
    _description = 'Loyalty Transaction History'
    _order = 'clph_datetime desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer'
    )

    loyalty_points = fields.Integer(
        string='Points'
    )

    redeemed_points = fields.Integer(
        string='Redeemed'
    )

    balance_points = fields.Integer(
        string='Balance'
    )

    clph_docnumber = fields.Char(
        string='Reference'
    )

    clph_points = fields.Integer(
        string='Points'
    )

    clph_whouse = fields.Char(
        string='W/H'
    )

    clph_note = fields.Text(
        string='Notes'
    )

    clph_datetime = fields.Datetime(
        string='Entry Time'
    )
    clph_bonuspoints=fields.Integer(string='Bonus Points')

