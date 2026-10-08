# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import re


class CrmCommercialLead(models.Model):
    _name = "crm.commercial.lead"
    _description = "CRM Commercial Lead"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    lead_no = fields.Char(
        string="Lead No",
        required=True,
        readonly=True,
        default=lambda self: _("New"),
        copy=False,
        index=True,
    )
    creation_date = fields.Date(
        string="Creation Date",
        default=fields.Date.context_today,
        required=True,
        readonly=True,
    )
    project_category_id = fields.Many2one(
        "crm.commercial.project.category", string="Project Category", index=True
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        required=True,
        index=True,
    )
    # date oct 7 2026
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        compute="_compute_warehouse_id",
        string="Warehouses",
        default=lambda self: self.env.user.available_warehouse_ids,
    )

    def _compute_warehouse_id(self):
        # self.warehouse_ids = False
        user_warehouses = self.env.user.available_warehouse_ids
        self.warehouse_ids = [(6, 0, user_warehouses.ids)]

    customer_type_id = fields.Many2one(
        "crm.commercial.customer.type",
        string="Customer Type",
        required=True,
        index=True,
    )
    # added by vengatesh sep 22
    # partner_id ,
    # custom_partner,
    # is_customer_type,
    # @api.depends("customer_type_id"),
    # @api.onchange("customer_type_id")
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer/Lead",
    )

    custom_partner = fields.Char(string="Customer/Lead")

    is_customer_type = fields.Boolean(
        compute="_compute_is_customer_type",
        store=False,
    )

    @api.depends("customer_type_id")
    def _compute_is_customer_type(self):
        for rec in self:
            rec.is_customer_type = rec.customer_type_id.code == "01"

    # @api.onchange("customer_type_id")
    # def _onchange_customer_type_id(self):
    #     for rec in self:
    #         rec.partner_id = False
    #         rec.custom_partner = False

    # @api.onchange("partner_id")
    # def _onchange_partner_id(self):
    #     if self.customer_type_id.name == "Customer" and self.partner_id:
    #         self.phone = self.partner_id.mobile
    #         self.email = self.partner_id.email
    #         self.street = self.partner_id.street
    #         self.street2 = self.partner_id.street2
    #         self.city_id = self.partner_id.customer_city_id
    #         self.state_id = self.partner_id.state_id
    #         self.region_id = self.partner_id.region_id
    #         self.country_id = self.partner_id.country_id
    #         self.zip = self.partner_id.zip
    #     else:
    #         self.phone = False
    #         self.email = False
    #         self.street = False
    #         self.street2 = False
    #         self.city_id = False
    #         self.state_id = False
    #         self.region_id = False
    #         self.country_id = self.country_id
    #         self.zip = False
    #         self.existing_partner_id = False

    # sep 28 2026  Added by vengatesh
    @api.onchange("customer_type_id")
    def _onchange_customer_type_id(self):
        if self.customer_type_id and self.customer_type_id.code != "01":
            self.partner_id = False
            self.existing_partner_id = False
            self.phone = False
            self.email = False
            self.street = False
            self.street2 = False
            self.city_id = False
            self.state_id = False
            self.region_id = False
            # self.country_id = False
            self.zip = False
            self.custom_partner = False

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone = self.partner_id.mobile or self.partner_id.phone
            self.email = self.partner_id.email
            self.street = self.partner_id.street
            self.street2 = self.partner_id.street2
            self.city_id = self.partner_id.customer_city_id
            self.state_id = self.partner_id.state_id
            self.region_id = self.partner_id.region_id
            self.country_id = self.partner_id.country_id
            self.zip = self.partner_id.zip
            self.existing_partner_id = self.partner_id

            customer_type = self.env["crm.commercial.customer.type"].search(
                [("code", "=", "01")],
                limit=1,
            )

            if customer_type:
                self.customer_type_id = customer_type
                self.is_customer_type = True

        else:
            self.existing_partner_id = False

    @api.onchange("phone", "email")
    def _onchange_phone_check_partner(self):
        if not self.phone and not self.email:
            return

        partner = False

        if self.phone:
            phone = self.phone.strip()

            partner = self.env["res.partner"].search(
                [
                    ("mobile", "=", phone),
                ],
                limit=1,
            )

        # If phone is not found, search by email
        if not partner and self.email:
            email = self.email.strip()

            partner = self.env["res.partner"].search(
                [("email", "=", email)],
                limit=1,
            )

        if partner:
            # Set customer type
            customer_type = self.env["crm.commercial.customer.type"].search(
                [("code", "=", "01")],
                limit=1,
            )

            if customer_type:
                self.customer_type_id = customer_type
                self.is_customer_type = True

            # Set partner
            self.partner_id = partner
            self.existing_partner_id = partner

            # Copy partner details
            self.phone = partner.mobile or partner.phone
            self.email = partner.email
            self.street = partner.street
            self.street2 = partner.street2
            self.city_id = partner.customer_city_id
            self.state_id = partner.state_id
            self.region_id = partner.region_id
            self.country_id = partner.country_id
            self.zip = partner.zip

    name = fields.Char(string="Lead / Project Name", required=True, index=True)
    probability = fields.Float(string="Probability (%)", default=10.0)
    position = fields.Char(string="Position")

    product_group_id = fields.Many2one(
        "product.category",
        string="Product Group",
        index=True,
        domain="[('id', 'in', crm_product_category_ids)]",
        default=lambda self: self._default_product_group_id(),
    )

    crm_product_category_ids = fields.Many2many(
        # added by vengatesh sep 21
        "product.category",
        "crm_commercial_lead_product_category_rel",
        "lead_id",
        "category_id",
        string="CRM Product Category",
        compute="_compute_crm_product_category_ids",
    )
    product_category_id = fields.Many2one(
        "product.category",
        string="Product Category",
        domain="[('use_for_crm_commercial', '=', True), ('exclude_category', '=', False), ('parent_id', 'child_of', product_group_id), ('id', '!=', product_group_id)] if product_group_id else [('id', '=', False)]",
        index=True,
    )
    show_product_group = fields.Boolean(
        compute="_compute_show_product_group",
    )

    @api.depends("product_group_id")
    def _compute_show_product_group(self):
        for rec in self:
            rec.show_product_group = (
                rec.product_group_id.code != "MDA" if rec.product_group_id else False
            )

    # def _default_product_group_id(self):
    #     ICP = self.env["ir.config_parameter"].sudo()

    #     show_product_category = ICP.get_param(
    #         "crm_commercial.show_crm_commerical_product_category",
    #         default="",
    #     )

    #     configured_category_id = ICP.get_param(
    #         "crm_commercial.crm_product_category_id",
    #         default="",
    #     )

    #     if show_product_category == "True" and configured_category_id:
    #         try:
    #             configured_category_id = int(configured_category_id)
    #         except (ValueError, TypeError):
    #             return False

    #         category = (
    #             self.env["product.category"].browse(configured_category_id).exists()
    #         )

    #         return category.id if category else False

    #     return False
    def _default_product_group_id(self):
        ICP = self.env["ir.config_parameter"].sudo()

        show_product_category = ICP.get_param(
            "crm_commercial.show_crm_commerical_product_category",
            default="",
        )

        configured_category_id = ICP.get_param(
            "crm_commercial.crm_product_category_id",
            default="",
        )

        # Configured category as default
        if show_product_category == "True" and configured_category_id:
            try:
                configured_category_id = int(configured_category_id)
            except (ValueError, TypeError):
                configured_category_id = False

            if configured_category_id:
                category = (
                    self.env["product.category"].browse(configured_category_id).exists()
                )

                if category:
                    return category.id

        # Fallback default: MDA
        mda_category = self.env["product.category"].search(
            [("code", "=", "MDA")],
            limit=1,
        )

        return mda_category.id if mda_category else False

    # added by vengatesh sep 21
    @api.depends("creation_date", "product_category_id")
    def _compute_crm_product_category_ids(self):
        ICP = self.env["ir.config_parameter"].sudo()

        show_product_category = ICP.get_param(
            "crm_commercial.show_crm_commerical_product_category",
            default="",
        )

        configured_category_id = ICP.get_param(
            "crm_commercial.crm_product_category_id",
            default="",
        )

        for rec in self:
            rec.crm_product_category_ids = False

            if show_product_category == "True" and configured_category_id:

                try:
                    configured_category_id = int(configured_category_id)
                except (ValueError, TypeError):
                    configured_category_id = False

                configured_category = (
                    self.env["product.category"].browse(configured_category_id).exists()
                    if configured_category_id
                    else self.env["product.category"]
                )

                # Get all root categories
                product_categories = self.env["product.category"].search(
                    [
                        ("parent_id", "=", False),
                    ]
                )

                # Configured category + all other root categories
                product_categories = configured_category | product_categories

                rec.crm_product_category_ids = [(6, 0, product_categories.ids)]

            else:
                mda_category = self.env["product.category"].search(
                    [("code", "=", "MDA")],
                    limit=1,
                )

                rec.crm_product_category_ids = [(6, 0, mda_category.ids)]

    @api.onchange("product_group_id")
    def _onchange_product_group_id(self):
        if not self.product_group_id:
            self.product_category_id = False
        elif self.product_category_id:
            cat = self.product_category_id
            is_child = False
            while cat:
                if cat.id == self.product_group_id.id:
                    is_child = True
                    break
                cat = cat.parent_id
            if not is_child:
                self.product_category_id = False

    capacity = fields.Char(string="Capacity")
    email = fields.Char(string="Email", required=True, index=True)
    lead_value = fields.Float(string="Lead Value")
    expected_confirmation_date = fields.Date(string="Expected Confirmation Date")
    phone = fields.Char(string="Phone", required=True, index=True)
    description = fields.Text(string="Description")

    @api.constrains("expected_confirmation_date")
    def _check_expected_confirmation_date(self):
        for record in self:
            if (
                record.expected_confirmation_date
                and record.create_date
                and record.expected_confirmation_date <= record.create_date.date()
            ):
                raise ValidationError(
                    "Expected Confirmation Date must be greater than Creation Date."
                )

    def _default_country_id(self):
        return self.env.ref("base.sa", raise_if_not_found=False) or self.env[
            "res.country"
        ].search([("code", "=", "SA")], limit=1)

    # Address Fields
    street = fields.Char(
        string="Street 1",
        required=True,
    )
    street2 = fields.Char(string="Street 2")
    city_id = fields.Many2one(
        "res.city",
        string="City",
        domain="[('country_id', '=', country_id)]",
        required=True,
    )
    city = fields.Char(string="City Name")
    state_id = fields.Many2one(
        "res.country.state",
        string="State",
        domain="[('country_id', '=', country_id)]",
        required=True,
    )
    district = fields.Many2one(
        "res.state.district",
        string="District",
        domain="[('city_id', '=', city_id)]",
        required=True,
    )
    region_id = fields.Many2one("res.region", string="Region", required=True)
    country_id = fields.Many2one(
        "res.country", string="Country", default=_default_country_id
    )
    zip = fields.Char(string="Zip Code")

    # added in vengatesh sep 22 2026
    @api.onchange("city_id")
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            if self.city_id:
                self.state_id = self.city_id.state_id
                # self.country_id = self.city_id.country_id
                self.region_id = self.city_id.region_id

    @api.onchange("country_id")
    def _onchange_country_id_reset_city(self):
        if (
            self.country_id
            and self.city_id
            and self.city_id.country_id != self.country_id
        ):
            self.city_id = False
            self.city = False
            self.state_id = False

    source_id = fields.Many2one(
        "utm.source", string="Source", required=True, index=True
    )
    website = fields.Char(string="Website")
    assigned_id = fields.Many2one(
        "res.users",
        string="Assigned Salesman",
        domain="[('is_salesman', '=', True)]",  # added in vengatesh sep 22 2026
        default=lambda self: self.env.user,
        index=True,
    )
    tag_ids = fields.Many2many("crm.tag", string="Tags")
    existing_partner_id = fields.Many2one(
        "res.partner", string="Matching Existing Customer", readonly=True
    )

    state = fields.Selection(
        [
            ("draft", "New"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("converted", "Converted"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("lead_no", _("New")) == _("New"):
                vals["lead_no"] = self.env["ir.sequence"].next_by_code(
                    "crm.commercial.lead"
                ) or _("New")
        records = super(CrmCommercialLead, self).create(vals_list)

        # added in vengatesh sep 22 2026
        if vals.get("customer_type_id"):
            customer_type_search = self.env["crm.commercial.customer.type"].search(
                [("id", "=", vals.get("customer_type_id"))], limit=1
            )
            if customer_type_search.name == "Lead":
                vals = {
                    "name": vals.get("custom_partner"),
                    "customer_city_id": self.env["res.city"]
                    .search([("id", "=", vals.get("city_id"))], limit=1)
                    .id,
                    "street": vals.get("street"),
                    "street2": vals.get("street2"),
                    "district_id": vals.get("district"),
                    "state_id": vals.get("state_id"),
                    "zip": vals.get("zip"),
                    "region_id": vals.get("region_id"),
                    "mobile": vals.get("phone"),
                    "email": vals.get("email"),
                    "partner_type_hhs": "customer",
                    "sub_partner_type": "crm_lead",
                    "country_id": self.env["res.country"]
                    .search([("id", "=", vals.get("country_id"))], limit=1)
                    .id,
                }
                partner = self.env["res.partner"].create(vals)

        for rec in records:
            if rec.assigned_id and rec.assigned_id.lead_auto_approval:
                rec.state = "approved"

        return records

    @api.constrains("phone")
    def _check_phone_format(self):
        for rec in self:
            if rec.phone:
                digits_only = re.sub(r"\D", "", rec.phone)
                if len(digits_only) != 10:
                    raise ValidationError(
                        _("Phone number must contain exactly 10 digits.")
                    )

    @api.onchange("phone", "email")
    def _onchange_phone_email_check_partner(self):
        if self.phone or self.email:
            domain = []
            if self.phone:
                domain.append(("phone", "=", self.phone))
            if self.email:
                domain.append(("email", "=", self.email))
            partner = (
                self.env["res.partner"].search(["|"] + domain, limit=1)
                if len(domain) > 1
                else self.env["res.partner"].search(domain, limit=1)
            )
            if partner:
                self.existing_partner_id = partner.id
                return {
                    "warning": {
                        "title": _("Existing Customer Found"),
                        "message": _(
                            "Matching customer record found: %s (Phone: %s, Email: %s). Record linked to existing customer."
                        )
                        % (partner.name, partner.phone or "", partner.email or ""),
                    }
                }

    def action_approve(self):
        self.write({"state": "approved"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_convert_to_quotation(self):
        self.ensure_one()
        partner = self.existing_partner_id
        if not partner:
            partner = self.env["res.partner"].create(
                {
                    "name": self.name,
                    "email": self.email,
                    "phone": self.phone,
                    "street": self.street,
                    "street2": self.street2,
                    "city": self.city,
                    "state_id": self.state_id.id if self.state_id else False,
                    "zip": self.zip,
                    "country_id": self.country_id.id if self.country_id else False,
                }
            )
            self.existing_partner_id = partner.id

        quotation = (
            self.env["crm.commercial.quotation"]
            .with_context(skip_validation=True)
            .create(
                {
                    "lead_id": self.id,
                    "lead_no": self.lead_no,
                    "partner_id": partner.id,
                    "to_name": partner.name,
                    "email": self.email,
                    "phone": self.phone,
                    "street": self.street,
                    "street2": self.street2,
                    "city_id": self.city_id.id if self.city_id else False,
                    "city": self.city,
                    "state_id": self.state_id.id if self.state_id else False,
                    # "district": self.district,
                    "district": self.district.id if self.district else False,
                    "region_id": self.region_id.id if self.region_id else False,
                    "country_id": self.country_id.id if self.country_id else False,
                    "zip": self.zip,
                    "warehouse_id": self.warehouse_id.id,
                    "assigned_id": self.assigned_id.id,
                    "project_category_id": (
                        self.project_category_id.id
                        if self.project_category_id
                        else False
                    ),
                    "project_name": self.name,
                    "tag_ids": [(6, 0, self.tag_ids.ids)],
                }
            )
        )
        self.state = "converted"
        return {
            "type": "ir.actions.act_window",
            "name": _("Commercial Quotation"),
            "res_model": "crm.commercial.quotation",
            "res_id": quotation.id,
            "view_mode": "form",
            "target": "current",
        }
