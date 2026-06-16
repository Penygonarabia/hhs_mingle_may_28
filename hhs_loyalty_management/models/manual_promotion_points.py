from odoo import models, fields, api
from odoo.exceptions import UserError, warnings, ValidationError
from odoo import _


class EnterManualPromotionPoints(models.Model):
    _name = 'manual.promotional.points'
    _description = 'Manual Promotion Points'
    _rec_name = 'reference'
    _order = 'transaction_date desc'

    # name = fields.Char(string="Name", required=True)

    reference = fields.Char(
        string='Reference',
        copy=False
    )

    reason_type_id = fields.Many2one(
        'manual.promotion.reason.types',
        string='Reason Type',
        required=True
    )

    adjustment_types = fields.Selection([
        ('addition', 'Addition'),
        ('deduction', 'Deduction'),
    ], string='Adjustment Type', required=True)
    transaction_date = fields.Date(
        string='Transaction Date',
        default=fields.Date.context_today,
        required=True
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        domain="[('activate_loyalty_feature', '=', True)]"
    )

    number_of_points = fields.Integer(
        string='Number of Points'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed')
    ], string='Status', default='draft')

    adjustment_symbol = fields.Char(
        string='Symbol',
        compute='_compute_adjustment_symbol'
    )

    def unlink(self):
        for rec in self:
            if rec.state == 'processed':
                raise UserError(
                    _("Processed records cannot be deleted.")
                )

        return super(
            EnterManualPromotionPoints,
            self.with_context(unlink_mode=True)
        ).unlink()

    # @api.constrains('number_of_points')
    # def _check_number_of_points_limit(self):
    #
    #     limit = int(
    #         self.env['ir.config_parameter'].sudo().get_param(
    #             'hhs_loyalty_management.customer_loyalty_point_limit',
    #             default=0
    #         )
    #     )
    #     for rec in self:
    #
    #         if rec.number_of_points and limit:
    #
    #             if rec.number_of_points > limit:
    #                 raise ValidationError(
    #                     _("Number of Points cannot exceed %s.") % limit
    #                 )

    @api.depends('adjustment_types')
    def _compute_adjustment_symbol(self):
        for rec in self:
            if rec.adjustment_types == 'addition':
                rec.adjustment_symbol = '+'
            elif rec.adjustment_types == 'deduction':
                rec.adjustment_symbol = '-'
            else:
                rec.adjustment_symbol = ''

    @api.constrains('transaction_date', 'customer_id', 'reason_type_id')
    def _check_duplicate_record(self):

        for rec in self:

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('transaction_date', '=', rec.transaction_date),
                ('customer_id', '=', rec.customer_id.id),
                ('reason_type_id', '=', rec.reason_type_id.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    _("Duplicate record is not allowed for the same "
                      "Customer, Adjustment Type and Reason Type.")
                )

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    @api.model
    def create(self, vals):
        if vals.get("reference") in [False, None, "", "New"]:
            vals['reference'] = self.env['ir.sequence'].next_by_code(
                'loyalty.points.adjustment'
            ) or 'New'

        return super().create(vals)

    # def write(self, vals):
    #     for rec in self:
    #         if rec.state == 'processed':
    #             raise ValidationError("Processed records cannot be edited.")
    #     return super().write(vals)
    def write(self, vals):
        for rec in self:
            if rec.state == 'processed' and self.env.context.get('unlink_mode') != True:
                raise ValidationError(
                    _("Processed records cannot be edited.")
                )

        return super().write(vals)


    def action_process(self):
        print("customerid111111111111111111111",'1')
        for rec in self:
            # -------------------------------------------------
            # PREVENT DUPLICATE PROCESSING
            # -------------------------------------------------
            existing_history = self.env[
                'customer.loyalty.points.history'
            ].search([
                ('clph_docnumber', '=', rec.reference)
            ], limit=1)
            if existing_history:
                raise ValidationError(
                    _("This record is already processed.")
                )
            # -------------------------------------------------
            # ADJUSTMENT TYPE
            # -------------------------------------------------

            if rec.adjustment_types == 'addition':
                adj_type = '+'
                clph_type = 'I'
            else:
                adj_type = '-'
                clph_type = 'O'
            print(
                "Adjustment Type : ",
                rec.adjustment_types,
                adj_type
            )

            last_transaction = self.env[
                # 'loyalty.transaction.history'
                'customer.loyalty.points.history'
            ].search(
                [('clph_cstid', '=', rec.customer_id.id)],
                order='clph_datetime desc',
                limit=1
            )
            previous_balance = (
                    last_transaction.balance_points or 0
            )
            print("PREVIOUS BALANCE :", previous_balance)
            if rec.adjustment_types == 'addition':
                loyalty_points = rec.number_of_points
                redeemed_points = 0

                balance_points = (
                        previous_balance
                        + rec.number_of_points
                )
            else:
                loyalty_points = 0
                redeemed_points = rec.number_of_points
                balance_points = (
                        previous_balance
                        - rec.number_of_points
                )


            # -------------------------------------------------
            # CREATE CUSTOMER LOYALTY POINTS HISTORY
            # -------------------------------------------------

            self.env[
                'customer.loyalty.points.history'
            ].create({

                'clph_cstid': rec.customer_id.id,
                'partner_id': rec.customer_id.id,
                'clph_cstcode': rec.customer_id.ref or '',
                'clph_date': rec.transaction_date,
                # 99 = Adjustment / Collected
                'clph_doctype': '99',
                'clph_docnumber': rec.reference or '',
                'clph_adjtype': adj_type,
                'clph_type': clph_type,
                'clph_whouse': 0,
                'clph_regpoints': rec.number_of_points or 0,
                'clph_bonuspoints': 0,
                'clph_totalpoints': rec.number_of_points or 0,
                'clph_note': '',
                'clph_uid': self.env.user.id,
                'clph_datetime': fields.Datetime.now(),
                'clph_reasoncode': rec.reason_type_id.reason_code or '',
                'clph_promoref': rec.reference or '',
                'clph_export': False,

                'loyalty_points': loyalty_points,
                'redeemed_points': redeemed_points,
                'balance_points': balance_points,
                'clph_points': rec.number_of_points,
                'type': 'Adjustments',

            })

            # -------------------------------------------------
            # GET PREVIOUS BALANCE
            # -------------------------------------------------

            # last_transaction = self.env[
            #     # 'loyalty.transaction.history'
            #     'customer.loyalty.points.history'
            # ].search(
            #     [('clph_cstid', '=', rec.customer_id.id)],
            #     order='clph_datetime desc',
            #     limit=1
            # )
            # previous_balance = (
            #         last_transaction.balance_points or 0
            # )
            # print("PREVIOUS BALANCE :", previous_balance)

            # -------------------------------------------------
            # CALCULATE NEW BALANCE
            # -------------------------------------------------

            # if rec.adjustment_types == 'addition':
            #     loyalty_points = rec.number_of_points
            #     redeemed_points = 0
            #
            #     balance_points = (
            #             previous_balance
            #             + rec.number_of_points
            #     )
            # else:
            #     loyalty_points = 0
            #     redeemed_points = rec.number_of_points
            #     balance_points = (
            #             previous_balance
            #             - rec.number_of_points
            #     )

            print("NEW BALANCE :", balance_points)

            # -------------------------------------------------
            # CREATE LOYALTY TRANSACTION HISTORY
            # -------------------------------------------------

            # self.env[
            #     # 'loyalty.transaction.history'
            #     'customer.loyalty.points.history'
            # ].create({
            #
            #     'partner_id': rec.customer_id.id,
            #     'clph_cstid':rec.customer_id.id,
            #     'loyalty_points': loyalty_points,
            #     'redeemed_points': redeemed_points,
            #     'balance_points': balance_points,
            #     'clph_docnumber': rec.reference or '',
            #     'clph_points': rec.number_of_points,
            #     'clph_whouse': '',
            #     'clph_note': '',
            #     'clph_datetime': fields.Datetime.now(),
            #     'clph_bonuspoint': 0,
            #     'type': 'Adjustments',
            # })
            print('customeridddddddddddddddddddddddd',rec.customer_id.id)
            # -------------------------------------------------
            # UPDATE CUSTOMER CURRENT BALANCE
            # -------------------------------------------------
            rec.customer_id.write({
                'loyalty_points': balance_points
            })
            # -------------------------------------------------
            # UPDATE STATE
            # -------------------------------------------------
            rec.state = 'processed'
            print("PROCESS COMPLETED")

    # def action_process(self):
    #     for rec in self:
    #
    #         # Prevent duplicate processing
    #         existing_history = self.env['customer.loyalty.points.history'].search([
    #             ('clph_docnumber', '=', rec.reference)
    #         ], limit=1)
    #
    #         if existing_history:
    #             raise ValidationError(
    #                 _("This record is already processed.")
    #             )
    #
    #         # # Points calculation
    #         # reg_points = rec.number_of_points if rec.adjustment_type == 'Addition' else 0
    #         # bonus_points = 0
    #         #
    #         # total_points = rec.number_of_points
    #         # if rec.adjustment_type == 'Deduction':
    #         #     total_points = -abs(rec.number_of_points)
    #
    #         if rec.adjustment_types == 'addition':
    #             adj_type = '+'
    #             clph_type = 'I'
    #             #total_points = rec.number_of_points
    #         else:
    #             adj_type = '-'
    #             clph_type = 'O'
    #             #total_points = -abs(rec.number_of_points)
    #
    #         print("Adjustment Type: ", rec.adjustment_types,adj_type)
    #         # Insert into Customer Loyalty Points History
    #         self.env['customer.loyalty.points.history'].create({
    #             'clph_cstid': rec.customer_id.id,
    #             'clph_cstcode': rec.customer_id.ref or '',
    #             'clph_date': rec.transaction_date,
    #             'clph_doctype': 99,
    #             'clph_docnumber': rec.reference or '',
    #             'clph_adjtype': adj_type,
    #             'clph_type': clph_type,
    #             'clph_whouse': 0,
    #             'clph_regpoints': rec.number_of_points or '',
    #             'clph_bonuspoints': 0,
    #             'clph_totalpoints': rec.number_of_points or '',
    #             'clph_note': '',
    #             'clph_uid': self.env.user.id or '',
    #             'clph_datetime': fields.Datetime.now(),
    #             'clph_reasoncode': rec.reason_type_id.reason_code or '',
    #             'clph_promoref': rec.reference or '',
    #             'clph_export': 'False',
    #         })
    #         # -----------------------------------------
    #         # Create Loyalty Transaction History
    #         # -----------------------------------------
    #
    #         if rec.adjustment_types == 'addition':
    #
    #             loyalty_points = rec.number_of_points
    #             redeemed_points = 0
    #             balance_points = rec.number_of_points
    #
    #         else:
    #
    #             loyalty_points = 0
    #             redeemed_points = rec.number_of_points
    #             balance_points = -rec.number_of_points
    #
    #         self.env['loyalty.transaction.history'].create({
    #             'partner_id': rec.customer_id.id,
    #             'loyalty_points': loyalty_points,
    #             'redeemed_points': redeemed_points,
    #             'balance_points': balance_points,
    #             'clph_docnumber': rec.reference or '',
    #             'clph_points': rec.number_of_points,
    #             'clph_whouse': '',
    #             'clph_note': rec.reason_type_id.reason_name or '',
    #             'clph_datetime': fields.Datetime.now(),
    #             'clph_bonuspoints':'',
    #             'type':'Adjustments',
    #
    #         })
    #
    #         rec.state = 'processed'


class CustomerLoyaltyPointsHistory(models.Model):
    _name = 'customer.loyalty.points.history'
    _description = 'Customer Loyalty Points History'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer'
    )
    clph_cstid = fields.Many2one('res.partner')
    clph_docnumber = fields.Char(string='Reference')
    clph_cstcode = fields.Char()
    clph_date = fields.Date()
    # clph_doctype = fields.Char()
    clph_doctype = fields.Selection([
        ('99', 'Adjustments'), ('98', 'Redeem'), ('97', 'Expiry'),
        ('01', 'Invoice'), ('02', 'Credit Note')
    ])
    clph_adjtype = fields.Char()
    clph_type = fields.Char()
    clph_whouse = fields.Char(string='W/H')
    clph_regpoints = fields.Integer()
    clph_bonuspoints = fields.Integer()
    clph_totalpoints = fields.Integer()
    clph_note = fields.Char(string='Note')
    clph_uid = fields.Char()
    clph_datetime = fields.Datetime(string='Date')
    clph_reasoncode = fields.Char()
    clph_promoref = fields.Char()
    clph_export = fields.Char()
    clph_points = fields.Integer(
        string='Regular Points'
    )
    balance_points = fields.Integer(
        string='Balance'
    )
    loyalty_points = fields.Integer(
        string='Regular Points'
    )
    redeemed_points = fields.Integer(
        string='Redeemed'
    )
    balance_points_regular = fields.Integer(
        string="Balance"
    )
    clph_bonuspoint = fields.Integer(string='Bonus Points')
    type = fields.Char(string='Type')
    
    display_regpoints = fields.Integer(string='Regular Points', compute='_compute_display_points')
    display_bonuspoints = fields.Integer(string='Bonus Points', compute='_compute_display_points')

    reason_type_id = fields.Many2one(
        'manual.promotion.reason.types',
        string='Reason Type',
        compute='_compute_reason_type',
        store=True
    )

    @api.depends('clph_reasoncode')
    def _compute_reason_type(self):
        for rec in self:
            if rec.clph_reasoncode:
                reason = self.env['manual.promotion.reason.types'].search([('reason_code', '=', rec.clph_reasoncode)], limit=1)
                rec.reason_type_id = reason.id
            else:
                rec.reason_type_id = False

    @api.depends('clph_regpoints', 'clph_bonuspoints', 'clph_doctype', 'clph_adjtype')
    def _compute_display_points(self):
        for rec in self:
            sign = -1 if (rec.clph_doctype in ['02', '98', '97'] or (rec.clph_doctype == '99' and rec.clph_adjtype == '-')) else 1
            rec.display_regpoints = (rec.clph_regpoints or 0) * sign
            rec.display_bonuspoints = (rec.clph_bonuspoints or 0) * sign

    # collected_points_regular = fields.Integer(

    def read(self, fields=None, load='_classic_read'):
        res = super(CustomerLoyaltyPointsHistory, self).read(fields, load)
        for rec in self:
            rec._compute_loyalty_points()
            # rec._compute_tier_name()
        return res

    # @api.depends('loyalty_transaction_history_ids')
    def _compute_loyalty_points(self):

        for rec in self:
            history = self.env['customer.loyalty.points.history'].search([
                ('clph_cstid', '=', rec.id)
            ])
            total_points = 0

            for line in history:

                # Invoice
                if line.clph_doctype == '01':
                    total_points += line.clph_regpoints

                # Redeem
                elif line.clph_doctype == '98':
                    total_points -= line.clph_regpoints

                # Expiry
                elif line.clph_doctype == '97':
                    total_points -= line.clph_regpoints

                # Credit Note
                elif line.clph_doctype == '02':
                    total_points -= line.clph_regpoints

                # Adjustment
                elif line.clph_doctype == '99':
                    if line.clph_adjtype == '+':
                        total_points += line.clph_regpoints
                    elif line.clph_adjtype == '-':
                        total_points -= line.clph_regpoints

            rec.balance_points_regular = total_points

    # ---------------------------------------------------------
    # MIGRATE OLD HISTORY
    # ---------------------------------------------------------

    # def generate_loyalty_transaction_history(self):
    #
    #     transaction_obj = self.env['loyalty.transaction.history']
    #
    #     history_records = self.search([])
    #
    #     for rec in history_records:
    #
    #         existing = transaction_obj.search([
    #             ('clph_docnumber', '=', rec.CLPH_DOCNUMBER),
    #             ('partner_id', '=', rec.CLPH_CSTID.id),
    #         ], limit=1)
    #
    #         if existing:
    #             continue
    #
    #         loyalty_points = 0
    #         redeemed_points = 0
    #         balance_points = 0
    #
    #         if rec.CLPH_ADJTYPE == '+':
    #
    #             loyalty_points = rec.CLPH_TOTALPOINTS or 0
    #
    #             balance_points = rec.CLPH_TOTALPOINTS or 0
    #
    #         elif rec.CLPH_ADJTYPE == '-':
    #
    #             redeemed_points = abs(rec.CLPH_TOTALPOINTS or 0)
    #
    #             balance_points = -(abs(rec.CLPH_TOTALPOINTS or 0))
    #
    #         transaction_obj.create({
    #
    #             'partner_id': rec.CLPH_CSTID.id,
    #
    #             'loyalty_points': loyalty_points,
    #
    #             'redeemed_points': redeemed_points,
    #
    #             'balance_points': balance_points,
    #
    #             'clph_docnumber': rec.CLPH_DOCNUMBER,
    #
    #             'clph_points': rec.CLPH_TOTALPOINTS,
    #
    #             'clph_whouse': rec.CLPH_WHOUSE,
    #
    #             'clph_note': rec.CLPH_NOTE,
    #
    #             'clph_datetime': rec.CLPH_DATETIME,
    #
    #         })
