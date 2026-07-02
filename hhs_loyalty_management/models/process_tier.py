from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from datetime import date, timedelta
from markupsafe import Markup
import logging
_logger = logging.getLogger(__name__)



class ProcessTier(models.Model):
    _name = 'process.tier'
    _description = 'Process Tier'
    _order = 'id desc'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed')
    ], default='draft')

    select_all_customers = fields.Boolean(
        string="Select All Customers"
    )

    process_customer_id = fields.Many2one(
        'res.partner',
        string="Customer"
    )

    message = fields.Text(
        readonly=True
    )
    process_datetime = fields.Datetime(
        string='Process Date & Time',
        default=fields.Datetime.now,
        readonly=True
    )
    process_customer_ids = fields.Many2many(
        'res.partner',
        string="Multiple Customers"
    )
    customer_names = fields.Html(
        string="Customers",
        compute="_compute_customer_names",
        sanitize=False
    )

    @api.depends(
        'process_customer_id',
        'process_customer_ids',
        'select_all_customers'
    )
    def _compute_customer_names(self):

        for rec in self:

            badges = ""

            # Single customer
            if not rec.select_all_customers and rec.process_customer_id:
                badges += f"""
                        <div style="margin-bottom:4px;">
                            <span style="
                                background:#e5e7eb;
                                color:#374151;
                                padding:4px 10px;
                                border-radius:12px;
                                font-size:12px;
                                display:inline-block;
                            ">
                                {rec.process_customer_id.name}
                            </span>
                        </div>
                    """

            # Multiple customers
            if rec.select_all_customers:

                for customer in rec.process_customer_ids:
                    badges += f"""
                            <div style="margin-bottom:4px;">
                                <span style="
                                    background:#e5e7eb;
                                    color:#374151;
                                    padding:4px 10px;
                                    border-radius:12px;
                                    font-size:12px;
                                    display:inline-block;
                                ">
                                    {customer.name}
                                </span>
                            </div>
                        """

            rec.customer_names = Markup(badges)
    # customer_names = fields.Html(
    #     string="Customers",
    #     compute="_compute_customer_names",
    #     sanitize=False
    # )
    #
    # @api.depends('process_customer_ids')
    # def _compute_customer_names(self):
    #     for rec in self:
    #
    #         badges = ""
    #
    #         for customer in rec.process_customer_ids:
    #             badges += f"""
    #                     <div style="margin-bottom:4px;">
    #                         <span style="
    #                             background-color:#e5e7eb;
    #                             color:#374151;
    #                             padding:4px 10px;
    #                             border-radius:12px;
    #                             display:inline-block;
    #                             font-size:12px;
    #                             font-weight:500;
    #                         ">
    #                             {customer.name}
    #                         </span>
    #                     </div>
    #                 """
    #
    #         rec.customer_names = Markup(badges)

    @api.onchange('select_all_customers')
    def _onchange_select_all_customers_ids(self):

        if self.select_all_customers:

            customers = self.env['res.partner'].search([
                ('activate_loyalty_feature', '=', True)
            ])

            self.process_customer_ids = [(6, 0, customers.ids)]

        else:

            self.process_customer_ids = [(5, 0, 0)]

    # -----------------------------------------
    # PREVENT DELETE FOR DONE RECORDS
    # -----------------------------------------

    def unlink(self):
        for rec in self:
            if rec.state == 'processed':
                raise UserError(
                    _("Processed records cannot be deleted.")
                )

        return super(ProcessTier, self).unlink()

    @api.onchange('select_all_customers')
    def _onchange_select_all_customers(self):

        if self.select_all_customers:
            self.process_customer_id = False

    # def _update_customer_tier(
    #         self,
    #         customer,
    #         matched_tier,
    #         loyalty_points,
    #         movement_type,
    #         old_tier_id=False
    # ):
    #
    #     print("===================================")
    #     print("UPDATING CUSTOMER TIER")
    #     print("Customer :", customer.name)
    #     print("Old Tier :", old_tier_id)
    #     print("New Tier :", matched_tier.name)
    #     print("Points :", loyalty_points)
    #     print("Movement :", movement_type)
    #     print("===================================")
    #
    #     customer.write({
    #         'customer_tier_id': matched_tier.id,
    #         'tier_name': matched_tier.name,
    #     })
    #
    #     # OPTIONAL
    #     # customer.send_tier_whatsapp_notification(
    #     #     movement_type=movement_type,
    #     #     tier_name=matched_tier.name,
    #     #     loyalty_points=loyalty_points
    #     # )
    #
    #     self.env['customer.tier.movement.history'].create({
    #         'customer_id': customer.id,
    #         'old_tier_id': old_tier_id,
    #         'new_tier_id': matched_tier.id,
    #         'movement_type': movement_type,
    #         'points': loyalty_points,
    #     })

    # def action_run_tier_process(self):
    #     for rec in self:
    #         # -------------------------------------------------
    #         # GET CUSTOMERS
    #         # -------------------------------------------------
    #
    #         if rec.select_all_customers:
    #
    #             customers = self.env['res.partner'].search([
    #                 ('activate_loyalty_feature', '=', True)
    #             ])
    #
    #         else:
    #
    #             if not rec.process_customer_id:
    #                 raise UserError(_("Please select customer."))
    #
    #             customers = rec.process_customer_id
    #
    #
    #         # -------------------------------------------------
    #         # GET TIERS
    #         # -------------------------------------------------
    #
    #         tiers = self.env['customer.tier'].search(
    #             [],
    #             order='min_loyalty_points desc'
    #         )
    #
    #         completed = 0
    #
    #         # -------------------------------------------------
    #         # PROCESS CUSTOMERS
    #         # -------------------------------------------------
    #
    #         for customer in customers:
    #             # tiers = self.env['customer.tier'].search(
    #             #     [],
    #             #     order='min_loyalty_points desc'
    #             # )
    #
    #             # -------------------------------------------------
    #             # GET ACTUAL BALANCE POINTS
    #             # -------------------------------------------------
    #
    #             loyalty_points = (
    #                     customer.balance_points_regular or 0
    #             )
    #
    #             # IF BONUS ALSO INCLUDED
    #
    #             # loyalty_points = (
    #             #     (customer.balance_points_regular or 0)
    #             #     + (customer.balance_points_bonus or 0)
    #             # )
    #
    #             # -------------------------------------------------
    #             # UPDATE CUSTOMER POINTS
    #             # -------------------------------------------------
    #
    #             customer.write({
    #                 'loyalty_points': loyalty_points
    #             })
    #
    #             current_tier = customer.customer_tier_id
    #
    #             matched_tier = False
    #
    #             # -------------------------------------------------
    #             # FIND MATCHING TIER
    #             # -------------------------------------------------
    #
    #             for tier in tiers:
    #
    #                 if loyalty_points >= tier.min_loyalty_points:
    #                     matched_tier = tier
    #                     break
    #
    #             # -------------------------------------------------
    #             # DEBUG
    #             # -------------------------------------------------
    #
    #             print("===================================")
    #             print("CUSTOMER :", customer.name)
    #             print("POINTS :", loyalty_points)
    #             print(
    #                 "CURRENT TIER :",
    #                 current_tier.name if current_tier else "NO TIER"
    #             )
    #             print(
    #                 "MATCHED TIER :",
    #                 matched_tier.name if matched_tier else "NO MATCH"
    #             )
    #             print("===================================")
    #
    #             # -------------------------------------------------
    #             # NO MATCHING TIER
    #             # -------------------------------------------------
    #
    #             if not matched_tier:
    #                 continue
    #
    #             # -------------------------------------------------
    #             # NEW CUSTOMER
    #             # -------------------------------------------------
    #             if not current_tier:
    #
    #                 customer.write({
    #                     'customer_tier_id': matched_tier.id,
    #                     'tier_name': matched_tier.name or False
    #                 })
    #
    #                 customer.send_tier_whatsapp_notification(
    #                     movement_type='upgrade',
    #                     tier_name=matched_tier.name,
    #                     loyalty_points=loyalty_points
    #                 )
    #
    #                 self.env[
    #                     'customer.tier.movement.history'
    #                 ].create({
    #                     'customer_id': customer.id,
    #                     'old_tier_id': False,
    #                     'new_tier_id': matched_tier.id,
    #                     'movement_type': 'upgrade',
    #                     'points': loyalty_points,
    #                 })
    #
    #                 print("NEW CUSTOMER TIER ASSIGNED")
    #
    #                 continue
    #             # if not current_tier:
    #             #
    #             #     customer.write({
    #             #         'customer_tier_id': matched_tier.id,
    #             #         'tier_name':matched_tier.name or False
    #             #     })
    #             #     customer.send_tier_whatsapp_notification(
    #             #         movement_type='upgrade',
    #             #         tier_name=matched_tier.name,
    #             #         loyalty_points=loyalty_points
    #             #     )
    #             #
    #             #     self.env[
    #             #         'customer.tier.movement.history'
    #             #     ].create({
    #             #         'customer_id': customer.id,
    #             #         'old_tier_id': False,
    #             #         'new_tier_id': matched_tier.id,
    #             #         'movement_type': 'upgrade',
    #             #         'points': loyalty_points,
    #             #     })
    #             #
    #             #     print("NEW CUSTOMER TIER ASSIGNED")
    #
    #             # -------------------------------------------------
    #             # UPGRADE
    #             # -------------------------------------------------
    #
    #             elif matched_tier.sort_order > current_tier.sort_order:
    #
    #                 old_tier = current_tier.id
    #
    #                 customer.write({
    #                     'customer_tier_id': matched_tier.id,'tier_name':matched_tier.name
    #                 })
    #                 customer.send_tier_whatsapp_notification(
    #                     movement_type='upgrade',
    #                     tier_name=matched_tier.name,
    #                     loyalty_points=loyalty_points
    #                 )
    #
    #                 self.env[
    #                     'customer.tier.movement.history'
    #                 ].create({
    #                     'customer_id': customer.id,
    #                     'old_tier_id': old_tier,
    #                     'new_tier_id': matched_tier.id,
    #                     'movement_type': 'upgrade',
    #                     'points': loyalty_points,
    #                 })
    #
    #                 print("CUSTOMER UPGRADED")
    #
    #             # -------------------------------------------------
    #             # DOWNGRADE
    #             # -------------------------------------------------
    #
    #             elif matched_tier.sort_order < current_tier.sort_order:
    #
    #                 waiting_days = int(
    #                     self.env['ir.config_parameter'].sudo().get_param(
    #                         'hhs_loyalty_management.tier_downgrade_waiting_days',
    #                         default=90
    #                     )
    #                 )
    #
    #                 if customer.res_maxinvoicedate:
    #
    #                     allowed_date = (
    #                             date.today()
    #                             - timedelta(days=waiting_days)
    #                     )
    #
    #                     print(
    #                         "LAST PURCHASE :",
    #                         customer.res_maxinvoicedate
    #                     )
    #
    #                     print(
    #                         "ALLOWED DATE :",
    #                         allowed_date
    #                     )
    #
    #                     if customer.res_maxinvoicedate <= allowed_date:
    #                         old_tier = current_tier.id
    #
    #                         customer.write({
    #                             'customer_tier_id': matched_tier.id,'tier_name':matched_tier.name
    #                         })
    #                         customer.send_tier_whatsapp_notification(
    #                             movement_type='downgrade',
    #                             tier_name=matched_tier.name,
    #                             loyalty_points=loyalty_points
    #                         )
    #
    #                         self.env[
    #                             'customer.tier.movement.history'
    #                         ].create({
    #                             'customer_id': customer.id,
    #                             'old_tier_id': old_tier,
    #                             'new_tier_id': matched_tier.id,
    #                             'movement_type': 'downgrade',
    #                             'points': loyalty_points,
    #                         })
    #
    #                         print("CUSTOMER DOWNGRADED")
    #                         print("===================================")
    #                         print("DOWNGRADE CHECK")
    #                         print("Customer :", customer.name)
    #                         print("Current Tier :", current_tier.name)
    #                         print("Matched Tier :", matched_tier.name)
    #                         print("Customer Points :", loyalty_points)
    #                         print("Last Invoice Date :", customer.res_maxinvoicedate)
    #                         print("Allowed Date :", allowed_date)
    #                         print("Condition Result :", customer.res_maxinvoicedate <= allowed_date)
    #                         print("===================================")
    #
    #             completed += 1
    #
    #
    #         # -------------------------------------------------
    #         # COMPLETED
    #         # -------------------------------------------------
    #
    #         rec.state = 'processed'
    #
    #         rec.message = _(
    #             "Tier Process Completed Successfully.\n\n"
    #             "Processed Customers : %s"
    #         ) % completed
    #
    #     # -------------------------------------------------
    #     # SUCCESS MESSAGE
    #     # -------------------------------------------------
    #
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': _('Success'),
    #             'message': rec.message,
    #             'type': 'success',
    #             'sticky': True,
    #         }
    #     }
    def _update_customer_tier(
            self,
            customer,
            matched_tier,
            loyalty_points,
            movement_type,
            old_tier_id=False
    ):

        # -------------------------------------------------
        # UPDATE CUSTOMER
        # -------------------------------------------------
        
        matched_id = matched_tier.id if matched_tier else False
        matched_name = matched_tier.name if matched_tier else False

        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("========== EXECUTING UPDATE TIER DB WRITE ==========")
        _logger.info("Customer Name: %s", customer.name)
        _logger.info("matched_tier.id: %s", matched_id)
        _logger.info("matched_tier.name: %s", matched_name)
        _logger.info("loyalty_points: %s", loyalty_points)
        
        customer.write({
            'customer_tier_id': matched_id,
            'tier_name': matched_name,
            'loyalty_points': loyalty_points,
        })
        _logger.info("=> customer.write executed successfully without crashing.")

        # -------------------------------------------------
        # SEND WHATSAPP
        # -------------------------------------------------

        customer.send_tier_whatsapp_notification(
            movement_type=movement_type,
            tier_name=matched_name or "None",
            loyalty_points=loyalty_points
        )

        # -------------------------------------------------
        # CREATE HISTORY
        # -------------------------------------------------

        self.env['customer.tier.movement.history'].create({
            'customer_id': customer.id,
            'old_tier_id': old_tier_id,
            'new_tier_id': matched_id,
            'movement_type': movement_type,
            'points': loyalty_points,
        })

        # -------------------------------------------------
        # MAIN PROCESS
        # -------------------------------------------------

    def action_run_tier_process(self):

        for rec in self:

            # -------------------------------------------------
            # GET CUSTOMERS
            # -------------------------------------------------

            if rec.select_all_customers:
                customers = self.env['res.partner'].search([('activate_loyalty_feature', '=', True)])

            else:

                if rec.process_customer_ids:

                    customers = rec.process_customer_ids

                elif rec.process_customer_id:

                    customers = rec.process_customer_id

                else:

                    raise UserError(
                        _("Please select customer.")
                    )

            # -------------------------------------------------
            # GET TIERS
            # -------------------------------------------------

            tiers = self.env['customer.tier'].search(
                [],
                order='min_loyalty_points desc'
            )

            completed = 0

            # -------------------------------------------------
            # PROCESS CUSTOMERS
            # -------------------------------------------------

            for customer in customers:

                completed += 1

                # -------------------------------------------------
                # GET LOYALTY POINTS
                # -------------------------------------------------
                import logging
                _logger = logging.getLogger(__name__)
                _logger.info("--------- ANALYZING CUSTOMER: %s ---------", customer.name)
                
                customer._compute_loyalty_points()

                loyalty_points = max(
                    customer.balance_points_regular or 0,
                    0
                )

                # -------------------------------------------------
                # CURRENT TIER
                # -------------------------------------------------

                current_tier = customer.customer_tier_id

                matched_tier = False

                # -------------------------------------------------
                # FIND MATCHING TIER
                # -------------------------------------------------

                for tier in tiers:

                    if loyalty_points >= tier.min_loyalty_points:
                        matched_tier = tier
                        break

                # -------------------------------------------------
                # ZERO TIER MATCH (POINTS LOWER THAN LOWEST TIER)
                # -------------------------------------------------

                if not matched_tier:
                    if not current_tier:
                        continue  # Already has no tier.

                    _logger.info("Customer %s points are lower than the lowest tier (ZERO MATCH). Checking downgrade grace period.", customer.name)

                    if not customer.res_maxinvoicedate:
                        continue

                    waiting_days = int(
                        self.env[
                            'ir.config_parameter'
                        ].sudo().get_param(
                            'hhs_loyalty_management.'
                            'tier_downgrade_waiting_days',
                            default=90
                        )
                    )

                    allowed_date = (
                            date.today()
                            - timedelta(days=waiting_days)
                    )
                    
                    if customer.res_maxinvoicedate <= allowed_date:
                        _logger.info("Customer %s triggers STRIP DOWNGRADE. Removing tier.", customer.name)
                        rec._update_customer_tier(
                            customer=customer,
                            matched_tier=False,
                            loyalty_points=loyalty_points,
                            movement_type='downgrade',
                            old_tier_id=current_tier.id
                        )

                    continue

                # -------------------------------------------------
                # NEW CUSTOMER
                # -------------------------------------------------

                if not current_tier:
                    _logger.info("Customer %s has NO current tier. Initiating Upgrade path immediately.", customer.name)
                    rec._update_customer_tier(
                        customer=customer,
                        matched_tier=matched_tier,
                        loyalty_points=loyalty_points,
                        movement_type='upgrade',
                        old_tier_id=False
                    )

                    continue

                # -------------------------------------------------
                # SAME TIER
                # -------------------------------------------------

                if current_tier.id == matched_tier.id:
                    _logger.info("Customer %s matched tier is same as current tier (%s). Skipping.", customer.name, matched_tier.name)
                    continue

                matched_sort = matched_tier.sort_order or 0
                current_sort = current_tier.sort_order or 0
                _logger.info("Customer %s logic evaluation: matched_sort=%s vs current_sort=%s", customer.name, matched_sort, current_sort)

                # -------------------------------------------------
                # UPGRADE
                # LOWER SORT ORDER = HIGHER TIER
                # -------------------------------------------------

                if matched_sort < current_sort:
                    _logger.info("Customer %s triggers UPGRADE path.", customer.name)
                    rec._update_customer_tier(
                        customer=customer,
                        matched_tier=matched_tier,
                        loyalty_points=loyalty_points,
                        movement_type='upgrade',
                        old_tier_id=current_tier.id
                    )

                # -------------------------------------------------
                # DOWNGRADE
                # -------------------------------------------------

                elif matched_sort > current_sort:
                    _logger.info("Customer %s triggers DOWNGRADE check sequence.", customer.name)
                    # -----------------------------------------
                    # NO LAST PURCHASE DATE
                    # -----------------------------------------

                    if not customer.res_maxinvoicedate:
                        continue

                    # -----------------------------------------
                    # WAITING DAYS
                    # -----------------------------------------

                    waiting_days = int(
                        self.env[
                            'ir.config_parameter'
                        ].sudo().get_param(
                            'hhs_loyalty_management.'
                            'tier_downgrade_waiting_days',
                            default=90
                        )
                    )

                    allowed_date = (
                            date.today()
                            - timedelta(days=waiting_days)
                    )

                    # -----------------------------------------
                    # DOWNGRADE AFTER WAITING PERIOD
                    # -----------------------------------------

                    if (
                            customer.res_maxinvoicedate
                            <= allowed_date
                    ):
                        rec._update_customer_tier(
                            customer=customer,
                            matched_tier=matched_tier,
                            loyalty_points=loyalty_points,
                            movement_type='downgrade',
                            old_tier_id=current_tier.id
                        )

            # -------------------------------------------------
            # COMPLETED
            # -------------------------------------------------

            rec.state = 'processed'

            rec.message = _(
                "Tier Process Completed Successfully.\n\n"
                "Processed Customers : %s"
            ) % completed

        # -------------------------------------------------
        # SUCCESS MESSAGE
        # -------------------------------------------------

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': rec.message,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    @api.model
    def cron_auto_process_tiers(self):
        _logger.info("Executing automatic cron tier processing for all active loyalty customers...")
        process_rec = self.create({
            'select_all_customers': True,
            'state': 'draft',
        })
        process_rec.action_run_tier_process()
        _logger.info("Completed automatic cron tier processing successfully.")
        return True

    # staging def action_run_tier_process(self):
    #
    #     for rec in self:
    #
    #         # -------------------------------------------------
    #         # GET CUSTOMERS
    #         # -------------------------------------------------
    #
    #         if rec.select_all_customers:
    #
    #             customers = self.env['res.partner'].search([
    #                 ('activate_loyalty_feature', '=', True)
    #             ])
    #             for customer_search in rec.process_customer_ids:
    #                 customers=customer_search.id
    #
    #         else:
    #
    #             if not rec.process_customer_id:
    #                 raise UserError(_("Please select customer."))
    #
    #             customers = rec.process_customer_id
    #
    #         # -------------------------------------------------
    #         # GET TIERS
    #         # -------------------------------------------------
    #
    #         tiers = self.env['customer.tier'].search(
    #             [],
    #             order='min_loyalty_points desc'
    #         )
    #
    #         completed = 0
    #
    #         # -------------------------------------------------
    #         # PROCESS CUSTOMERS
    #         # -------------------------------------------------
    #
    #         for customer in customers:
    #
    #             completed += 1
    #
    #             # -------------------------------------------------
    #             # GET LOYALTY POINTS
    #             # CLAMP NEGATIVE POINTS TO 0
    #             # -------------------------------------------------
    #
    #             loyalty_points = max(customer.balance_points_regular or 0, 0)
    #
    #             # -------------------------------------------------
    #             # FIND CURRENT TIER
    #             # -------------------------------------------------
    #
    #             current_tier = customer.customer_tier_id
    #
    #             matched_tier = False
    #
    #             # -------------------------------------------------
    #             # FIND MATCHING TIER
    #             # -------------------------------------------------
    #
    #             for tier in tiers:
    #                 if loyalty_points >= tier.min_loyalty_points:
    #                     matched_tier = tier
    #                     break
    #
    #             # -------------------------------------------------
    #             # NO MATCHING TIER
    #             # -------------------------------------------------
    #
    #             if not matched_tier:
    #                 continue
    #
    #             # -------------------------------------------------
    #             # NEW CUSTOMER — NO EXISTING TIER
    #             # -------------------------------------------------
    #
    #             if not current_tier:
    #                 rec._update_customer_tier(
    #                     customer=customer,
    #                     matched_tier=matched_tier,
    #                     loyalty_points=loyalty_points,
    #                     movement_type='upgrade',
    #                     old_tier_id=False
    #                 )
    #
    #                 continue
    #
    #             # -------------------------------------------------
    #             # SAME TIER — NO CHANGE
    #             # -------------------------------------------------
    #
    #             if current_tier.id == matched_tier.id:
    #                 continue
    #
    #             matched_sort = matched_tier.sort_order or 0
    #             current_sort = current_tier.sort_order or 0
    #
    #             # -------------------------------------------------
    #             # UPGRADE
    #             # -------------------------------------------------
    #
    #             if matched_sort < current_sort:
    #
    #                 rec._update_customer_tier(
    #                     customer=customer,
    #                     matched_tier=matched_tier,
    #                     loyalty_points=loyalty_points,
    #                     movement_type='upgrade',
    #                     old_tier_id=current_tier.id
    #                 )
    #
    #             # -------------------------------------------------
    #             # DOWNGRADE
    #             # -------------------------------------------------
    #
    #             elif matched_sort > current_sort:
    #
    #                 # -----------------------------------------
    #                 # FORCE DOWNGRADE — POINTS BELOW CURRENT
    #                 # TIER MINIMUM, SKIP WAITING PERIOD
    #                 # -----------------------------------------
    #
    #                 if loyalty_points < (current_tier.min_loyalty_points or 0):
    #                     rec._update_customer_tier(
    #                         customer=customer,
    #                         matched_tier=matched_tier,
    #                         loyalty_points=loyalty_points,
    #                         movement_type='downgrade',
    #                         old_tier_id=current_tier.id
    #                     )
    #
    #                     continue
    #
    #                 # -----------------------------------------
    #                 # NO LAST PURCHASE DATE — SKIP DOWNGRADE
    #                 # -----------------------------------------
    #
    #                 if not customer.res_maxinvoicedate:
    #                     continue
    #
    #                 # -----------------------------------------
    #                 # CHECK WAITING PERIOD
    #                 # -----------------------------------------
    #
    #                 waiting_days = int(
    #                     self.env['ir.config_parameter'].sudo().get_param(
    #                         'hhs_loyalty_management.tier_downgrade_waiting_days',
    #                         default=90
    #                     )
    #                 )
    #
    #                 allowed_date = date.today() - timedelta(days=waiting_days)
    #
    #                 # -----------------------------------------
    #                 # DOWNGRADE ONLY AFTER WAITING PERIOD
    #                 # -----------------------------------------
    #
    #                 if customer.res_maxinvoicedate <= allowed_date:
    #                     rec._update_customer_tier(
    #                         customer=customer,
    #                         matched_tier=matched_tier,
    #                         loyalty_points=loyalty_points,
    #                         movement_type='downgrade',
    #                         old_tier_id=current_tier.id
    #                     )
    #
    #         # -------------------------------------------------
    #         # COMPLETED
    #         # -------------------------------------------------
    #
    #         rec.state = 'processed'
    #
    #         rec.message = _(
    #             "Tier Process Completed Successfully.\n\n"
    #             "Processed Customers : %s"
    #         ) % completed
    #
    #     # -------------------------------------------------
    #     # SUCCESS MESSAGE
    #     # -------------------------------------------------
    #
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': _('Success'),
    #             'message': rec.message,
    #             'type': 'success',
    #             'sticky': True,
    #         }
    #     }
    #
    # def _update_customer_tier(
    #         self,
    #         customer,
    #         matched_tier,
    #         loyalty_points,
    #         movement_type,
    #         old_tier_id=False
    # ):
    #     # -------------------------------------------------
    #     # UPDATE CUSTOMER
    #     # -------------------------------------------------
    #
    #     customer.write({
    #         'customer_tier_id': matched_tier.id,
    #         'tier_name': matched_tier.name,
    #         'loyalty_points': loyalty_points,
    #     })
    #
    #     # -------------------------------------------------
    #     # SEND WHATSAPP
    #     # -------------------------------------------------
    #
    #     customer.send_tier_whatsapp_notification(
    #         movement_type=movement_type,
    #         tier_name=matched_tier.name,
    #         loyalty_points=loyalty_points
    #     )
    #
    #     # -------------------------------------------------
    #     # CREATE HISTORY
    #     # -------------------------------------------------
    #
    #     self.env['customer.tier.movement.history'].create({
    #         'customer_id': customer.id,
    #         'old_tier_id': old_tier_id,
    #         'new_tier_id': matched_tier.id,
    #         'movement_type': movement_type,
    #         'points': loyalty_points,
    #     })

    # single workingdef _update_customer_tier(
    #         self,
    #         customer,
    #         matched_tier,
    #         loyalty_points,
    #         movement_type,
    #         old_tier_id=False
    # ):
    #
    #     print("===================================")
    #     print("UPDATING CUSTOMER TIER")
    #     print("Customer :", customer.name)
    #     print("Old Tier :", old_tier_id)
    #     print("New Tier :", matched_tier.name)
    #     print("Points :", loyalty_points)
    #     print("Movement :", movement_type)
    #     print("===================================")
    #
    #     # UPDATE CUSTOMER
    #
    #     customer.write({
    #         'customer_tier_id': matched_tier.id,
    #         'tier_name': matched_tier.name,
    #         'loyalty_points': loyalty_points,
    #     })
    #
    #     # SEND WHATSAPP
    #
    #     customer.send_tier_whatsapp_notification(
    #         movement_type=movement_type,
    #         tier_name=matched_tier.name,
    #         loyalty_points=loyalty_points
    #     )
    #
    #     # CREATE HISTORY
    #
    #     self.env[
    #         'customer.tier.movement.history'
    #     ].create({
    #         'customer_id': customer.id,
    #         'old_tier_id': old_tier_id,
    #         'new_tier_id': matched_tier.id,
    #         'movement_type': movement_type,
    #         'points': loyalty_points,
    #     })
    #
    #     print("TIER UPDATED SUCCESSFULLY")
    #
    #     # -------------------------------------------------
    #     # MAIN PROCESS
    #     # -------------------------------------------------
    #
    # def action_run_tier_process(self):
    #
    #     for rec in self:
    #
    #         # -------------------------------------------------
    #         # GET CUSTOMERS
    #         # -------------------------------------------------
    #
    #         if rec.select_all_customers:
    #
    #             customers = self.env['res.partner'].search([
    #                 ('activate_loyalty_feature', '=', True)
    #             ])
    #
    #         else:
    #
    #             if not rec.process_customer_id:
    #                 raise UserError(_("Please select customer."))
    #
    #             customers = rec.process_customer_id
    #
    #         # -------------------------------------------------
    #         # GET TIERS
    #         # -------------------------------------------------
    #
    #         tiers = self.env['customer.tier'].search(
    #             [],
    #             order='min_loyalty_points desc'
    #         )
    #
    #         completed = 0
    #
    #         # -------------------------------------------------
    #         # PROCESS CUSTOMERS
    #         # -------------------------------------------------
    #
    #         for customer in customers:
    #
    #             completed += 1
    #
    #             # -------------------------------------------------
    #             # GET LOYALTY POINTS
    #             # -------------------------------------------------
    #
    #             loyalty_points = (
    #                     customer.balance_points_regular or 0
    #             )
    #
    #             # -------------------------------------------------
    #             # FIND CURRENT TIER
    #             # -------------------------------------------------
    #
    #             current_tier = customer.customer_tier_id
    #
    #             matched_tier = False
    #
    #             # -------------------------------------------------
    #             # FIND MATCHING TIER
    #             # -------------------------------------------------
    #
    #             for tier in tiers:
    #
    #                 if loyalty_points >= tier.min_loyalty_points:
    #                     matched_tier = tier
    #                     break
    #
    #             # -------------------------------------------------
    #             # DEBUG
    #             # -------------------------------------------------
    #
    #             print("===================================")
    #             print("CUSTOMER :", customer.name)
    #             print("POINTS :", loyalty_points)
    #             print(
    #                 "CURRENT TIER :",
    #                 current_tier.name if current_tier else "NO TIER"
    #             )
    #             print(
    #                 "MATCHED TIER :",
    #                 matched_tier.name if matched_tier else "NO MATCH"
    #             )
    #             print("===================================")
    #
    #             # -------------------------------------------------
    #             # NO MATCHING TIER
    #             # -------------------------------------------------
    #
    #             if not matched_tier:
    #                 continue
    #
    #             # -------------------------------------------------
    #             # NEW CUSTOMER
    #             # -------------------------------------------------
    #             print("")
    #             if not current_tier:
    #                 rec._update_customer_tier(
    #                     customer=customer,
    #                     matched_tier=matched_tier,
    #                     loyalty_points=loyalty_points,
    #                     movement_type='upgrade',
    #                     old_tier_id=False
    #                 )
    #
    #                 print("NEW CUSTOMER TIER ASSIGNED")
    #
    #                 continue
    #
    #
    #             # -------------------------------------------------
    #             # SAME TIER
    #             # -------------------------------------------------
    #
    #             if current_tier.id == matched_tier.id:
    #                 print("CUSTOMER ALREADY IN SAME TIER")
    #
    #                 continue
    #
    #             matched_sort = matched_tier.sort_order or 0
    #             current_sort = current_tier.sort_order or 0
    #
    #             # -------------------------------------------------
    #             # UPGRADE
    #             # -------------------------------------------------
    #             print("matched_sort:", matched_sort,current_sort)
    #             if matched_sort < current_sort:
    #                 print("upgradeeeeeeeeeeeeeeeeeeeeeeeeeeeee",'1')
    #
    #                 print("CUSTOMER UPGRADED")
    #
    #                 rec._update_customer_tier(
    #                     customer=customer,
    #                     matched_tier=matched_tier,
    #                     loyalty_points=loyalty_points,
    #                     movement_type='upgrade',
    #                     old_tier_id=current_tier.id
    #                 )
    #
    #             # -------------------------------------------------
    #             # DOWNGRADE
    #             # -------------------------------------------------
    #
    #             elif matched_sort > current_sort:
    #                 print("downgradeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",'2')
    #
    #                 waiting_days = int(
    #                     self.env['ir.config_parameter'].sudo().get_param(
    #                         'hhs_loyalty_management.tier_downgrade_waiting_days',
    #                         default=90
    #                     )
    #                 )
    #
    #                 # -----------------------------------------
    #                 # NO LAST PURCHASE DATE
    #                 # -----------------------------------------
    #                 print("11111111111111111111111111111111")
    #                 rec._update_customer_tier(
    #                     customer=customer,
    #                     matched_tier=matched_tier,
    #                     loyalty_points=loyalty_points,
    #                     movement_type='downgrade',
    #                     old_tier_id=current_tier.id
    #                 )
    #                 print("222222222222222222222222222222222")
    #                 if not customer.res_maxinvoicedate:
    #                     print(
    #                         "NO LAST PURCHASE DATE FOUND - "
    #                         "DOWNGRADE SKIPPED"
    #                     )
    #
    #                     continue
    #                 print("33333333333333333333333333333")
    #
    #                 # -----------------------------------------
    #                 # CHECK WAITING PERIOD
    #                 # -----------------------------------------
    #
    #                 allowed_date = (
    #                         date.today()
    #                         - timedelta(days=waiting_days)
    #                 )
    #
    #                 print("LAST PURCHASE :", customer.res_maxinvoicedate)
    #                 print("ALLOWED DATE :", allowed_date)
    #
    #                 # DOWNGRADE ONLY AFTER WAITING PERIOD
    #
    #                 if customer.res_maxinvoicedate <= allowed_date:
    #
    #                     print("CUSTOMER DOWNGRADED")
    #
    #                     rec._update_customer_tier(
    #                         customer=customer,
    #                         matched_tier=matched_tier,
    #                         loyalty_points=loyalty_points,
    #                         movement_type='downgrade',
    #                         old_tier_id=current_tier.id
    #                     )
    #
    #                 else:
    #
    #                     print(
    #                         "DOWNGRADE WAITING PERIOD NOT COMPLETED"
    #                     )
    #
    #             # elif matched_sort < current_sort:
    #             #
    #             #     waiting_days = int(
    #             #         self.env['ir.config_parameter'].sudo().get_param(
    #             #             'hhs_loyalty_management.tier_downgrade_waiting_days',
    #             #             default=90
    #             #         )
    #             #     )
    #             #     # customer.res_maxinvoicedate = (
    #             #     #         date.today() - timedelta(days=120)
    #             #     # )
    #             #     #
    #             #     # allowed_date = (
    #             #     #         date.today()
    #             #     #         - timedelta(days=waiting_days)
    #             #     # )
    #             #     #
    #             #     # print("LAST PURCHASE :", customer.res_maxinvoicedate)
    #             #     # print("ALLOWED DATE :", allowed_date)
    #             #     #
    #             #     # if customer.res_maxinvoicedate <= allowed_date:
    #             #     #     print("CUSTOMER DOWNGRADED")
    #             #     #
    #             #     #     rec._update_customer_tier(
    #             #     #         customer=customer,
    #             #     #         matched_tier=matched_tier,
    #             #     #         loyalty_points=loyalty_points,
    #             #     #         movement_type='downgrade',
    #             #     #         old_tier_id=current_tier.id
    #             #     #     )
    #             #
    #             #     if customer.res_maxinvoicedate:
    #             #
    #             #         allowed_date = (
    #             #                 date.today()
    #             #                 - timedelta(days=waiting_days)
    #             #         )
    #             #
    #             #         print("LAST PURCHASE :", customer.res_maxinvoicedate)
    #             #         print("ALLOWED DATE :", allowed_date)
    #             #
    #             #         # DOWNGRADE ONLY AFTER WAITING PERIOD
    #             #
    #             #         if customer.res_maxinvoicedate <= allowed_date:
    #             #
    #             #             print("CUSTOMER DOWNGRADED")
    #             #
    #             #             rec._update_customer_tier(
    #             #                 customer=customer,
    #             #                 matched_tier=matched_tier,
    #             #                 loyalty_points=loyalty_points,
    #             #                 movement_type='downgrade',
    #             #                 old_tier_id=current_tier.id
    #             #             )
    #             #
    #             #         else:
    #             #
    #             #             print(
    #             #                 "DOWNGRADE WAITING PERIOD NOT COMPLETED"
    #             #             )
    #
    #         # -------------------------------------------------
    #         # COMPLETED
    #         # -------------------------------------------------
    #
    #         rec.state = 'processed'
    #
    #         rec.message = _(
    #             "Tier Process Completed Successfully.\n\n"
    #             "Processed Customers : %s"
    #         ) % completed
    #
    #     # -------------------------------------------------
    #     # SUCCESS MESSAGE
    #     # -------------------------------------------------
    #
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': _('Success'),
    #             'message': rec.message,
    #             'type': 'success',
    #             'sticky': True,
    #         }
    #     }


class CustomerTierMovementHistory(models.Model):
    _name = 'customer.tier.movement.history'
    _description = 'Customer Tier Movement History'
    _order = 'create_date desc'

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer'
    )

    old_tier_id = fields.Many2one(
        'customer.tier',
        string='Old Tier'
    )

    new_tier_id = fields.Many2one(
        'customer.tier',
        string='New Tier'
    )

    movement_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade')
    ])

    points = fields.Float()

    movement_date = fields.Datetime(string="Changed Date",
                                    default=fields.Datetime.now
                                    )


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_tier_id = fields.Many2one(
        'customer.tier',
        string='Customer Tier'
    )

    loyalty_points = fields.Float(
        string='Regular Loyalty Points'
    )

    last_purchase_date = fields.Date(
        string='Last Purchase Date'
    )
    res_maxinvoicedate = fields.Date(
        string='Last Purchase Date'
    )

    def send_tier_whatsapp_notification(
            self,
            movement_type,
            tier_name,
            loyalty_points
    ):
        import requests
        import logging

        _logger = logging.getLogger(__name__)

        # -----------------------------------------
        # GET PHONE NUMBER
        # -----------------------------------------

        phone_number = self.mobile or self.phone
        country_code = self.country_id.phone_code or '91'

        if not phone_number:
            _logger.info(
                "No mobile number for customer %s",
                self.name
            )
            return False

        # -----------------------------------------
        # FORMAT PHONE NUMBER
        # -----------------------------------------

        # Remove spaces, +, -, brackets etc.
        phone_number = ''.join(
            filter(str.isdigit, phone_number)
        )

        # Add country code if missing
        if not phone_number.startswith(str(country_code)):
            phone_number = f"{country_code}{phone_number}"

        _logger.info(
            "Formatted WhatsApp Number : %s",
            phone_number
        )

        # -----------------------------------------
        # CONFIGURATION
        # -----------------------------------------

        whatsapp_phone_number_id = self.env[
            'ir.config_parameter'
        ].sudo().get_param(
            'whatsapp_sale_order_notify.whatsapp_phone_number_id'
        )

        access_token = self.env[
            'ir.config_parameter'
        ].sudo().get_param(
            'whatsapp_sale_order_notify.whatsapp_access_token'
        )

        if not access_token:
            _logger.info(
                "No WhatsApp access token configured"
            )
            return False

        base_url = (
            f"https://graph.facebook.com/v18.0/"
            f"{whatsapp_phone_number_id}/messages"
        )

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # -----------------------------------------
        # MESSAGE
        # -----------------------------------------

        if movement_type == 'upgrade':

            message = (
                f"Dear {self.name},\n\n"
                f"Congratulations 🎉\n"
                f"Your loyalty tier has been upgraded "
                f"to {tier_name}.\n\n"
                f"Current Points : {loyalty_points}\n\n"
                f"Thank You."
            )

        else:

            message = (
                f"Dear {self.name},\n\n"
                f"Your loyalty tier has been downgraded "
                f"to {tier_name}.\n\n"
                f"Current Points : {loyalty_points}\n\n"
                f"Continue shopping to upgrade again."
            )

        # -----------------------------------------
        # PAYLOAD
        # -----------------------------------------

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": message
            }
        }

        _logger.info(
            "WhatsApp Payload : %s",
            payload
        )

        # -----------------------------------------
        # SEND MESSAGE
        # -----------------------------------------

        try:

            response = requests.post(
                base_url,
                headers=headers,
                json=payload
            )

            _logger.info(
                "WhatsApp Status Code : %s",
                response.status_code
            )

            _logger.info(
                "WhatsApp Response : %s",
                response.text
            )

            response.raise_for_status()

            # Save chatter message
            self.message_post(
                body=_(
                    "WhatsApp tier notification sent successfully."
                )
            )

            _logger.info(
                "Tier WhatsApp sent successfully "
                "to %s (%s)",
                self.name,
                phone_number
            )

            return True

        except Exception as e:

            _logger.error(
                "WhatsApp sending failed for %s : %s",
                self.name,
                str(e)
            )

            return False
