from odoo import api, fields, models, _, re
from odoo.exceptions import ValidationError
from odoo.tools import float_round
from dateutil.relativedelta import relativedelta



class SubscriptionContracts(models.Model):
    """Model for subscription contracts"""

    _inherit = "subscription.contracts"

    technician_id = fields.Many2one("machine.support.team", string="Default Technician")
    amc_quotation_id = fields.Many2one("service.sale.order", string="AMC Quotation")
    partner_name = fields.Char(string="Company Name")

    #20260616 Gokul for visit count pivot
    city = fields.Many2one('res.city', string="City", compute="_compute_partner_details", store=True, readonly=False)
    region = fields.Char(string="Region", compute="_compute_partner_details", store=True, readonly=False)

    @api.depends('partner_id')
    def _compute_partner_details(self):
        for rec in self:
            partner = rec.partner_id.commercial_partner_id
            if partner:
                if not rec.city:
                    rec.city = partner.customer_city_id.id
                if not rec.region:
                    rec.region = partner.customer_city_id.def_work_center_id.work_center_group_id.name
                if not rec.work_center_group_id:
                    rec.work_center_group_id = partner.customer_city_id.def_work_center_id.work_center_group_id.id
            else:
                # Optionally clear them if no partner
                pass


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
            self.contract_reminder = 30
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


