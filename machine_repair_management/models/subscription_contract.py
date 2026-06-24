from odoo import api, fields, models, _, re
from odoo.exceptions import ValidationError
from odoo.tools import float_round
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)


class SubscriptionContracts(models.Model):
    """Model for subscription contracts"""

    _inherit = "subscription.contracts"

    technician_id = fields.Many2one("machine.support.team", string="Default Technician")
    amc_quotation_id = fields.Many2one("service.sale.order", string="AMC Quotation")
    partner_name = fields.Char(string="Company Name")

    #20260616 Gokul for visit count pivot
    #city = fields.Many2one('res.city', string="City" )
    # region = fields.Char(string="Region")

    # @api.depends('partner_id')
    # def _compute_partner_details(self):
    #     for rec in self:
    #         partner = rec.partner_id.commercial_partner_id
    #         if partner:
    #             if not rec.city:
    #                 rec.city = partner.customer_city_id.id
    #             if not rec.region:
    #                 rec.region = partner.customer_city_id.def_work_center_id.work_center_group_id.name
    #             if not rec.work_center_group_id:
    #                 rec.work_center_group_id = partner.customer_city_id.def_work_center_id.work_center_group_id.id
    #         else:
    #             # Optionally clear them if no partner
    #             pass


    # 20260415 gokul
    customer_identification_scheme = fields.Selection(
        [
            ("TIN", "Tax Identification Number"),
            ("CRN", "Commercial Registration Number"),
            ("IQA", "Iqama Number"),
            ("NAT", "National ID"),
        ],
        string="Identification Scheme",
        help="Additional Identification scheme for Seller/Buyer",
    )
    customer_identification_number = fields.Char(
        "VAT No", help="Additional Identification Number for Seller/Buyer"
    )
    building_number = fields.Char("Building Number")
    plot_identification = fields.Char("Plot Identification")
    
    '''Code Added on May 22 2026 by Vijaya Bhaskar'''
    customer_code = fields.Char(string = "Customer Code")
    
    warehouse_id = fields.Many2one('stock.warehouse',string = "Warehouse")
    
    work_center_id = fields.Many2one('work.center.location', string = "Work center")
    
    work_center_group_id = fields.Many2one('work.center.group', string = "Work Center  Group")
    
    district = fields.Many2one('res.state.district',string = "District")
    
     
    '''Code Added on May 26 2026 by Vijaya Bhaskar '''
    
    sales_person_user_id = fields.Many2one('res.users', string  = "SalesPerson")
    
    '''Code Added on June 05 2026 by Vijaya Bhaskar'''
    
    invoice_txt = fields.Text(string = "Invoice Text", default = lambda self:self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.invoice_txt_contract'))
    warehouse_lst_ids = fields.Many2many('stock.warehouse',string = "Warehouse List ids", compute="_compute_warehouse_lst_ids")
    
    '''Code Added on June 16 2026 by Vijaya Bhaskar client asked site address similar to address'''
    street = fields.Char(string = "Street")
    
    street2 = fields.Char(string = "Street2")
    
    customer_city_id = fields.Many2one('res.city', string = "Customer City")
    
    district_id  = fields.Many2one('res.state.district',string = "District")
    
    state_id = fields.Many2one('res.country.state', string = "State")
    
    country_id = fields.Many2one('res.country', string = "Country")
    
    zip = fields.Char(string = "Zip")
    
    '''code Added on June 22 2026 by Vijaya Bhaskar due to original name is updated when we create the contract'''
    original_name = fields.Char(string = "Original name")
    
    '''Code Added on June 23 2026 by Vijaya Bhaskar'''
    
    notification_send_salesman = fields.Boolean(string = "Notification Send Salesman", default = False)
    
    notification_send_manager = fields.Boolean(string = "Notification Send Manager", default = False)
    
    renewal_confirm_by_customer = fields.Boolean(string = "Renewal Confirm By Customer", default = False)
    
    confirmation_date = fields.Date(string = "Confirmation Date")
    
    
    # def send_notification_salesman_for_sixty_day(self):
    #     today = fields.Date.today()
    #
    #     for rec in self:
    #         if not rec.date_end:
    #             continue
    #
    #         reminder_date = rec.date_end - relativedelta(days=rec.contract_reminder)
    #
    #         if reminder_date == today and rec.state == 'ongoing':
    #             subject = f"Contract Notification - {rec.name}"
    #
    #             body_html = f"""
    #                 <p>Dear {rec.sales_person_user_id.name or ''},</p>
    #
    #                 <p>
    #                     The contract <b>{rec.name}</b> will expire on
    #                     <b>{rec.date_end.strftime('%d-%m-%Y')}</b>.
    #                 </p>
    #
    #                 <p>
    #                     Please contact the customer regarding renewal.
    #                 </p>
    #
    #                 <br/>
    #                 <p>
    #                     Best Regards,<br/>
    #                     Maintenance Department
    #                 </p>
    #             """
    #
    #             self.env['mail.mail'].create({
    #                 'subject': subject,
    #                 'body_html': body_html,
    #                 'email_from': self.env.user.email or self.env.company.email,
    #                 'email_to': rec.sales_person_user_id.login,
    #             }).send()
    #
    #             rec.notification_send_salesman = True
    
 

    def send_notification_salesman_for_sixty_day(self):
        today = fields.Date.today()
    
        _logger.info("Salesman notification cron started on %s", today)
        print("Salesman notification cron started on", today)
    
        for rec in self:
            _logger.info(
                "Processing Contract: %s, End Date: %s, Reminder Days: %s, State: %s",
                rec.name,
                rec.date_end,
                rec.contract_reminder,
                rec.state
            )
            print(
                f"Processing Contract: {rec.name}, End Date: {rec.date_end}, "
                f"Reminder Days: {rec.contract_reminder}, State: {rec.state}"
            )
    
            if not rec.date_end:
                _logger.info("Skipping %s - No end date found", rec.name)
                print(f"Skipping {rec.name} - No end date found")
                continue
    
            reminder_date = rec.date_end - relativedelta(days=rec.contract_reminder)
    
            _logger.info(
                "Contract: %s | Reminder Date: %s | Today: %s",
                rec.name,
                reminder_date,
                today
            )
            print(
                f"Contract: {rec.name} | Reminder Date: {reminder_date} | Today: {today}"
            )
    
            if reminder_date == today and rec.state == 'Ongoing':
                _logger.info("Sending notification for contract %s", rec.name)
                print(f"Sending notification for contract {rec.name}")
    
                subject = f"Contract Notification - {rec.name}"
    
                body_html = f"""
                    <p>Dear {rec.sales_person_user_id.name or ''},</p>
    
                    <p>
                        The contract <b>{rec.name}</b> will expire on
                        <b>{rec.date_end.strftime('%d-%m-%Y')}</b>.
                    </p>
    
                    <p>
                        Please contact the customer regarding renewal.
                    </p>
    
                    <br/>
                    <p>
                        Best Regards,<br/>
                        Maintenance Department
                    </p>
                """
    
                mail = self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body_html,
                    'email_from': self.env.user.email or self.env.company.email,
                    'email_to': rec.sales_person_user_id.login,
                })
    
                _logger.info(
                    "Mail created for %s (%s)",
                    rec.sales_person_user_id.name,
                    rec.sales_person_user_id.login
                )
                print(
                    f"Mail created for {rec.sales_person_user_id.name} "
                    f"({rec.sales_person_user_id.login})"
                )
    
                mail.send()
    
                _logger.info("Mail sent successfully for contract %s", rec.name)
                print(f"Mail sent successfully for contract {rec.name}")
    
                rec.notification_send_salesman = True
    
                _logger.info(
                    "notification_send_salesman updated to True for %s",
                    rec.name
                )
                print(
                    f"notification_send_salesman updated to True for {rec.name}"
                )
                            
    
    def send_notification_manager(self): 
        today = fields.Date.today()
    
        renewal_days = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'machine_repair_management.notify_manager_thirty_day', 30
            )
        )
    
        manager_group = self.env.ref(
            'hr_exit_process.group_genaral_manager_for_exit'
        )
    
        for rec in self:
            if (
                rec.notification_send_salesman
                and not rec.confirmation_date
                and not rec.renewal_confirm_by_customer
                 and rec.state == 'Ongoing'
            ):
                reminder_date = rec.date_end - relativedelta(days=renewal_days)
    
                if reminder_date == today:
    
                    for manager in manager_group.users:
                        if not manager.login:
                            continue
    
                        subject = f"Contract Notification - {rec.name}"
    
                        body_html = f"""
                            <p>Dear {manager.name},</p>
    
                            <p>
                                The contract <b>{rec.name}</b> will expire on
                                <b>{rec.date_end.strftime('%d-%m-%Y')}</b>.
                            </p>
    
                            <p>
                                Please contact the customer regarding renewal.
                            </p>
    
                            <br/>
                            <p>
                                Best Regards,<br/>
                                Maintenance Department
                            </p>
                        """
    
                        self.env['mail.mail'].create({
                            'subject': subject,
                            'body_html': body_html,
                            'email_from': self.env.user.email or self.env.company.email,
                            'email_to': manager.login,
                        }).send()
                        
    
    @api.depends('amc_quotation_id')
    def _compute_warehouse_lst_ids(self):
        
        user = self.env.user
    
        for rec in self:
            if user.has_group('warehouse_restrictions_app.group_restrict_stock_warehouse'):
                warehouse_ids = user.available_warehouse_ids.ids if user.available_warehouse_ids and user.restrict_stock_warehouse_operation  else self.env['stock.warehouse'].search([]).ids
            else:
                warehouse_ids = self.env['stock.warehouse'].search([]).ids
    
            rec.warehouse_lst_ids = [(6, 0, warehouse_ids)]  
    

    # 20260415 gokul
    @api.onchange('partner_id', 'amc_quotation_id')
    def onchange_partner_id_set_identification(self):
       
        if self.partner_id:
            if self.partner_id.additional_identification_scheme == 'TIN':
                self.customer_identification_scheme = self.partner_id.additional_identification_scheme or False
                # Show VAT
                self.customer_identification_number = self.partner_id.vat or False
            else:
                # Show other identification
                self.customer_identification_scheme = self.partner_id.additional_identification_scheme or False
                self.customer_identification_number = self.partner_id.additional_identification_number or False
            self.building_number = self.partner_id.building_number or False
            self.plot_identification = self.partner_id.plot_identification or False
            # self.invoice_interval_duration = self.amc_quotation_id.invoice_interval_duration or False

    # 20260415 gokul
    @api.model
    def create(self, vals):
        records = super().create(vals)

        for rec in records:
            partner = rec.partner_id

            if rec.customer_identification_scheme:
                partner.additional_identification_scheme = rec.customer_identification_scheme

            if rec.building_number:
                partner.building_number = rec.building_number

            if rec.plot_identification:
                partner.plot_identification = rec.plot_identification

            if rec.customer_identification_number:
                if rec.customer_identification_scheme == 'TIN':
                    partner.vat = rec.customer_identification_number
                else:
                    partner.additional_identification_number = rec.customer_identification_number

        records.onchange_amc_quotation_id()
        return records

    def write(self, vals):
        res = super().write(vals)

        for rec in self:
            partner = rec.partner_id

            if 'customer_identification_scheme' in vals:
                partner.additional_identification_scheme = rec.customer_identification_scheme

            if 'building_number' in vals:
                partner.building_number = rec.building_number

            if 'plot_identification' in vals:
                partner.plot_identification = rec.plot_identification

            if 'customer_identification_number' in vals or 'customer_identification_scheme' in vals:
                if rec.customer_identification_number:
                    if rec.customer_identification_scheme == 'TIN':
                        partner.vat = rec.customer_identification_number
                    else:
                        partner.additional_identification_number = rec.customer_identification_number
            
            '''Code Added on June 16 2026 by Vijaya Bhaskar client asked site address similar to address''' 
            if 'street' in vals:
                partner.street = vals.get('street')
            if 'street2' in vals:
                partner.street2 = vals.get('street2')
    
            if 'customer_city_id' in vals:
                city_search = self.env['res.city'].search([('id', '=', vals.get('customer_city_id'))], limit=1)
                partner.customer_city_id = city_search.id
    
            if 'state_id' in vals:
                state_search = self.env['res.country.state'].search([('id', '=', vals.get('state_id'))], limit=1)
    
                partner.state_id = state_search.id
    
            if 'country_id' in vals:
                country_search = self.env['res.country'].search([('id', '=', vals.get('country_id'))], limit=1)
    
                partner.country_id = country_search.id
    
            if 'zip' in vals:
                partner.zip = vals.get('zip')
    
            if 'email_from' in vals:
                partner.email = vals.get('email_from')
    
            if 'phone' in vals:
                partner.mobile = vals.get('phone')
            
        return res

    @api.constrains(
        'customer_identification_scheme',
        'customer_identification_number',
        'building_number',
        'plot_identification',
    )
    def _check_customer_identification(self):
        if self.env.context.get("skip_state_validation"):
            return

        for rec in self:
            scheme = rec.customer_identification_scheme
            number = rec.customer_identification_number

            # =========================
            # VAT / Identification Check
            # =========================
            if scheme and number:

                if not number.isdigit():
                    raise ValidationError(
                        _("Please enter only numbers in Identification Number")
                    )

                if scheme == "TIN":
                    if len(number) != 15:
                        raise ValidationError(
                            _("Tax Identification Number must be exactly 15 digits")
                        )
                else:
                    if len(number) != 10:
                        raise ValidationError(
                            _("Identification Number must be exactly 10 digits")
                        )

            # =========================
            # TIN Specific Address Check
            # =========================
            if scheme == "TIN":

                # -------- Building Number --------
                if rec.building_number:
                    if not rec.building_number.isdigit():
                        raise ValidationError(_("Building Number must be numeric"))

                    if len(rec.building_number) != 4:
                        raise ValidationError(_("Building Number must be exactly 4 digits"))

                # -------- Plot Identification --------
                if rec.plot_identification:
                    if not rec.plot_identification.isdigit():
                        raise ValidationError(_("Additional No. must be numeric"))

                    if len(rec.plot_identification) != 4:
                        raise ValidationError(_("Additional No. must be exactly 4 digits"))

    # @api.onchange("amc_quotation_id")
    # def onchange_amc_quotation_id(self):
    #     total_prevent = 0
    #     total_correct = 0
    #     if self.amc_quotation_id:
    #         if self.amc_quotation_id.customer_name:
    #             partner = self.env["res.partner"].search(
    #                 [("name", "=", self.amc_quotation_id.customer_name)], limit=1
    #             )
    #             if partner:
    #                 self.partner_id = partner.id if partner else False
    #         # self.reference = f"{self.amc_quotation_id.name} - {self.partner_id.name}"
    #         self.reference = self.amc_quotation_id.crm_id.name
    #         self.recurring_period = self.amc_quotation_id.contract_period
    #         self.recurring_period_interval = self.amc_quotation_id.contract_interval
    #         self.recurring_invoice = self.amc_quotation_id.invoice_interval
    #         self.entitlement_prevent = self.amc_quotation_id.no_of_prevent_service
    #         self.entitlement_correct = self.amc_quotation_id.no_of_correct_service
    #         self.travel_hours = self.amc_quotation_id.travel_hours
    #         self.gross_profit = self.amc_quotation_id.gross_profit
    #         self.payment_term_id = self.amc_quotation_id.payment_term_id
    #         self.customer_name = self.amc_quotation_id.customer_name
    #         self.contact_person = self.amc_quotation_id.crm_id.contact_name
    #         self.mobile_no = self.amc_quotation_id.crm_id.mobile
    #         self.email = self.amc_quotation_id.crm_id.email_from
    #         self.job_position = self.amc_quotation_id.crm_id.function
    #         self.contract_reminder = 30
    #         self.date = fields.Date.today()
    #         self.add_paid_service_price = self.amc_quotation_id.add_paid_service_price
    #         self.invoice_interval_duration = (
    #             self.amc_quotation_id.invoice_interval_duration or False
    #         )
    #         self.number_of_installments = (
    #             self.amc_quotation_id.number_of_installments or False
    #         )
    #         self.contract_duration_days = (
    #             self.amc_quotation_id.contract_duration_days or False
    #         )

    #         line_commands = [(5, 0, 0)]
    #         for line in self.amc_quotation_id.service_sale_order_line_ids:
    #             line_commands.append(
    #                 (
    #                     0,
    #                     0,
    #                     {
    #                         "product_id": line.product_id.id,
    #                         "qty_ordered": line.product_qty,
    #                         "no_of_visits_per_year": line.no_of_visits_per_year,
    #                         "no_of_emergency_visit": line.no_of_emergency_visit,
    #                         "days_required_for_rpm": line.days_required_for_rpm,
    #                         "days_require_rpm_round_off": line.days_require_rpm_round_off,
    #                         "standard_hours": line.standard_hours,
    #                         "total_hr": line.total_hr,
    #                         "total_cost": line.total_cost,
    #                         "total_price": line.total_price,
    #                         "price_unit": line.price_unit,
    #                         "vat_amt": line.vat_percent,
    #                         "vat": line.vat,
    #                         "sub_total": line.total_amc,
    #                         "analytic_account_id": 3,  # Hardcoded; consider making this dynamic if needed
    #                         "actual_prevent_count": line.actual_prevent_count,
    #                         "balance_prevent_count": line.balance_prevent_count,
    #                         "total_correct_count": line.total_correct_count,
    #                         "actual_correct_count": line.actual_correct_count,
    #                         "balance_correct_count": line.balance_correct_count,
    #                         "main_category_id": line.main_category_id.id,
    #                         "brand_category_id": line.brand_category_id.id,
    #                         "contract_type_id": line.contract_type_id.id,
    #                         "amc_pricing_id": line.amc_pricing_id.id,
    #                         "unit_cost_price": line.unit_cost_price,
    #                         "unit_selling_price": line.unit_selling_price,
    #                         "spare_parts_cost_per_category": line.spare_parts_cost_per_category,
    #                         "spare_parts_cost": line.spare_parts_cost,
    #                         "spare_parts_selling_price": line.spare_parts_selling_price,
    #                         "total_selling_price": line.total_selling_price,
    #                         "per_unit_selling_price": line.per_unit_selling_price,
    #                         # 'analytic_account_id': self.amc_quotation_id.analytic_account_id.id,
    #                     },
    #                 )
    #             )
    #             total_prevent += line.no_of_visits_per_year
    #             total_correct += line.no_of_emergency_visit
    #         self.entitlement_prevent = total_prevent
    #         self.entitlement_correct = total_correct
    #         # Assign the commands to contract_line_ids
    #         self.contract_line_ids = line_commands
    #     else:
    #         # Clear fields if amc_quotation_id is unset
    #         self.reference = False
    #         self.partner_id = False
    #         self.recurring_period = False
    #         self.recurring_period_interval = False
    #         self.recurring_invoice = False
    #         self.contract_line_ids = [(5, 0, 0)]  # Clear contract_line_ids

    @api.onchange("amc_quotation_id")
    def onchange_amc_quotation_id(self):
        total_prevent = 0
        total_correct = 0
        if self.amc_quotation_id:
            '''Code added on June 07 2026 by vijaya bhaskar'''
            if self.amc_quotation_id.crm_id.partner_id:
                self.partner_id = self.amc_quotation_id.crm_id.partner_id.id if self.amc_quotation_id.crm_id.partner_id else False

            # if self.amc_quotation_id.customer_name:
            #     partner = self.env["res.partner"].search(
            #         [("name", "=", self.amc_quotation_id.customer_name)], limit=1
            #     )
            #     if partner:
            #         self.partner_id = partner.id if partner else False
            # self.reference = f"{self.amc_quotation_id.name} - {self.partner_id.name}"
            self.partner_name  = self.amc_quotation_id.crm_id.partner_name or False
            self.reference = self.amc_quotation_id.crm_id.name
            self.recurring_period = self.amc_quotation_id.contract_period
            self.recurring_period_interval = self.amc_quotation_id.contract_interval
            self.recurring_invoice = self.amc_quotation_id.invoice_interval
            self.entitlement_prevent = self.amc_quotation_id.no_of_prevent_service
            self.entitlement_correct = self.amc_quotation_id.no_of_correct_service
            self.travel_hours = self.amc_quotation_id.travel_hours
            self.gross_profit = self.amc_quotation_id.gross_profit
            self.payment_term_id = self.amc_quotation_id.payment_term_id
            # self.customer_name = self.amc_quotation_id.customer_name
            # self.contact_person = self.amc_quotation_id.crm_id.contact_name
            #  # self.mobile_no = self.amc_quotation_id.crm_id.mobile
            # #code added on May 25 2026 by Vijaya Bhaskar client asked the country calling code 
            # # self.mobile_no =f"+{self.amc_quotation_id.crm_id.country_id.phone_code if self.amc_quotation_id.crm_id and self.amc_quotation_id.crm_id.country_id else ''}-{self.amc_quotation_id.crm_id.phone if self.amc_quotation_id.crm_id else ''}"
            # self.mobile_no = self.amc_quotation_id.crm_id.phone or False
            # self.email = self.amc_quotation_id.crm_id.email_from
            # self.job_position = self.amc_quotation_id.crm_id.function
            # self.contract_reminder = 30
            self.contract_reminder = int(self.env['ir.config_parameter'].sudo().get_param(
            'machine_repair_management.notify_salesman_sixty_day', 0))
            self.date = fields.Date.today()
            self.add_paid_service_price = self.amc_quotation_id.add_paid_service_price
            self.invoice_interval_duration = (
                self.amc_quotation_id.invoice_interval_duration or False
            )
            self.number_of_installments = (
                self.amc_quotation_id.number_of_installments or False
            )
            self.contract_duration_days = (
                self.amc_quotation_id.contract_duration_days or False
            )

            line_commands = [(5, 0, 0)]
            for line in self.amc_quotation_id.service_sale_order_line_ids:
                """code added on Mar 21 2026 by vijaya bhaskar"""

                units_serviced_visit = float(
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param(
                        "machine_repair_management.units_serviced_visit", default=0.0
                    )
                )

                days_required = (
                    line.product_qty / units_serviced_visit
                    if units_serviced_visit
                    else 0.0
                )

                line_commands.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "qty_ordered": line.product_qty,
                            "no_of_visits_per_year": line.no_of_visits_per_year,
                            "no_of_emergency_visit": line.no_of_emergency_visit,
                            "days_required_for_rpm": line.days_required_for_rpm,
                             #Code Commented on May 30 2026 by Vijaya Bhaskar client asked Total Preventive count is no of visits per year
                            #"days_require_rpm_round_off": line.days_require_rpm_round_off,
                            "days_require_rpm_round_off":line.no_of_visits_per_year,
                            
                            "standard_hours": line.standard_hours,
                            "total_hr": line.total_hr,
                            "total_cost": line.total_cost,
                            "total_price": line.total_price,
                            "price_unit": line.price_unit,
                            "vat_amt": line.vat_percent,
                            "vat": line.vat,
                            "sub_total": line.total_amc,
                            "analytic_account_id": 3,  # Hardcoded; consider making this dynamic if needed
                            "actual_prevent_count": line.actual_prevent_count,
                            "balance_prevent_count": line.balance_prevent_count,
                            "total_correct_count": line.total_correct_count,
                            "actual_correct_count": line.actual_correct_count,
                            "balance_correct_count": line.balance_correct_count,
                            "main_category_id": line.main_category_id.id,
                            "brand_category_id": line.brand_category_id.id,
                            "contract_type_id": line.contract_type_id.id,
                            "amc_pricing_id": line.amc_pricing_id.id,
                            "unit_cost_price": line.unit_cost_price,
                            "unit_selling_price": line.unit_selling_price,
                            "spare_parts_cost_per_category": line.spare_parts_cost_per_category,
                            "spare_parts_cost": line.spare_parts_cost,
                            "spare_parts_selling_price": line.spare_parts_selling_price,
                            "total_selling_price": line.total_selling_price,
                            "per_unit_selling_price": line.per_unit_selling_price,
                            # 'analytic_account_id': self.amc_quotation_id.analytic_account_id.id,
                        },
                    )
                )
                """code added on Mar 21 2026 by vijaya bhaskar"""
                #Code Commented on May 30 2026 by Vijaya Bhaskar client asked Total Preventive count is no of visits per year
                # total_prevent += float_round(days_required, precision_digits=0)
                total_prevent += line.no_of_visits_per_year
                total_correct += line.no_of_emergency_visit
            self.entitlement_prevent = total_prevent
            self.entitlement_correct = total_correct
            # Assign the commands to contract_line_ids
            self.contract_line_ids = line_commands
        # else:
        #     # Clear fields if amc_quotation_id is unset
        #     self.reference = False
        #     self.partner_id = False
        #     self.recurring_period = False
        #     self.recurring_period_interval = False
        #     self.recurring_invoice = False
        #     self.contract_line_ids = [(5, 0, 0)]  # Clear contract_line_ids

    # def create(self, vals):
    #     record = super().create(vals)
    #     if record.amc_quotation_id:
    #         record.onchange_amc_quotation_id()
    #     return record

    # def write(self, vals):
    #     res = super().write(vals)
    #     if "amc_quotation_id" in vals:
    #         self.onchange_amc_quotation_id()
    #     return res
    
    
    '''Code Added on June 05 2026 by Vijaya Bhaskar'''
    @api.onchange('invoice_interval_duration','date_start')
    def _onchange_invoice_interval(self):
        for rec in self:
            invoice_txt = self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.invoice_txt_contract')
            if rec.invoice_interval_duration:
                if rec.invoice_interval_duration == 'annual':
                    end_date = rec.date_start + relativedelta(years=1, days=-1) 
                    rec.invoice_txt = (
                        f"{invoice_txt} Annual Period : "
                        f"{rec.date_start.strftime('%d-%m-%Y')} to "
                        f"{end_date.strftime('%d-%m-%Y')}"
                    )
                elif rec.invoice_interval_duration == 'semi_annual':
                    end_date = rec.date_start + relativedelta(months=6, days=-1) 
                    rec.invoice_txt = (
                        f"{invoice_txt} Semi-Annual Period : "
                        f"{rec.date_start.strftime('%d-%m-%Y')} to "
                        f"{end_date.strftime('%d-%m-%Y')}"
                    )
                
                elif rec.invoice_interval_duration == 'quarterly':
                    end_date = rec.date_start + relativedelta(months=3, days=-1) 

                    rec.invoice_txt = (
                            f"{invoice_txt} Quarterly Period : "
                            f"{rec.date_start.strftime('%d-%m-%Y')} to "
                            f"{end_date.strftime('%d-%m-%Y')}"
                        )
                
                
                elif rec.invoice_interval_duration == 'monthly':
                    end_date = rec.date_start + relativedelta(months=1, days=-1) 
                    rec.invoice_txt = (
                            f"{invoice_txt} Monthly Period : "
                            f"{rec.date_start.strftime('%d-%m-%Y')} to "
                            f"{end_date.strftime('%d-%m-%Y')}"
                        )
                
                # period_names = {
                #
                #     'annual':'Annual',
                #     'semi_annual' : 'Semi-Annual',
                #     'quarterly' :'Quarterly',
                #     'monthly' : 'Monthly'
                #
                #     }
                #
                # if rec.invoice_interval_duration:
                #     rec.invoice_txt = (
                #         f"{invoice_txt}{period_names[rec.invoice_interval_duration]} Period : "
                #         f"{rec.date_start.strftime('%d-%m-%Y')} to " 
                #         f"{end_date.strftime('%d-%m-%Y')}"
                #
                #         )
                #


