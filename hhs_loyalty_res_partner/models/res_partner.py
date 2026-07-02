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
            collected_reg = sum(history.filtered(lambda x: x.clph_adjtype == '+').mapped('clph_regpoints'))
            redeem_reg = sum(history.filtered(lambda x: str(x.clph_doctype) == '98').mapped('clph_regpoints'))
            expired_reg = sum(history.filtered(lambda x: str(x.clph_doctype) == '97').mapped('clph_regpoints'))
            returned_reg = sum(history.filtered(lambda x: str(x.clph_doctype) == '02').mapped('clph_regpoints'))

            rec.collected_points_regular = max(collected_reg - returned_reg, 0)
            rec.redeem_points_regular = redeem_reg
            rec.expired_points_regular = expired_reg
            rec.balance_points_regular = max(rec.collected_points_regular - redeem_reg - expired_reg, 0)

            # -----------------------------
            # BONUS
            # -----------------------------
            collected_bonus = sum(history.filtered(lambda x: x.clph_adjtype == '+').mapped('clph_bonuspoints'))
            redeem_bonus = sum(history.filtered(lambda x: str(x.clph_doctype) == '98').mapped('clph_bonuspoints'))
            expired_bonus = sum(history.filtered(lambda x: str(x.clph_doctype) == '97').mapped('clph_bonuspoints'))
            returned_bonus = sum(history.filtered(lambda x: str(x.clph_doctype) == '02').mapped('clph_bonuspoints'))

            rec.collected_points_bonus = max(collected_bonus - returned_bonus, 0)
            rec.redeem_points_bonus = redeem_bonus
            rec.expired_points_bonus = expired_bonus
            rec.balance_points_bonus = max(rec.collected_points_bonus - redeem_bonus - expired_bonus, 0)



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

