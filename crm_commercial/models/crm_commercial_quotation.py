# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import re


class CrmCommercialQuotation(models.Model):
    _name = "crm.commercial.quotation"
    _description = "CRM Commercial Quotation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Quotation No",
        required=True,
        readonly=True,
        default=lambda self: _("New"),
        copy=False,
        index=True,
    )
    revision_number = fields.Integer(string="Revision #", default=0, readonly=True)
    parent_quotation_id = fields.Many2one(
        "crm.commercial.quotation", string="Parent Quotation", readonly=True
    )

    lead_id = fields.Many2one(
        "crm.commercial.lead", string="Source Lead", readonly=True
    )
    lead_no = fields.Char(string="Lead No", readonly=True, index=True)
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
        self.warehouse_ids = False
        user_warehouses = self.env.user.available_warehouse_ids
        self.warehouse_ids = [(6, 0, user_warehouses.ids)]

    # -------------------------------------------------------------------------
    # Partner auto-create helper
    # -------------------------------------------------------------------------
    def _get_or_create_partner(self, vals=None):
        """
        Search for an existing res.partner by phone / email from the
        quotation form data.  If found, return that partner.  If no
        match exists and the quotation has a customer name (to_name),
        create a new res.partner and return it.
        Returns a res.partner recordset (possibly empty).
        """
        vals = vals or {}
        phone = (vals.get("phone") or getattr(self, "phone", "") or "").strip()
        email = (vals.get("email") or getattr(self, "email", "") or "").strip()
        to_name = (vals.get("to_name") or getattr(self, "to_name", "") or "").strip()

        if not phone and not email:
            return self.env["res.partner"]

        # Build search domain: match on phone OR mobile OR email
        if phone:
            domain = [("mobile", "=", phone)]
        else:
            domain = [("email", "=", email)]

        partner = self.env["res.partner"].search(domain, limit=1)
        if partner:
            return partner

        # No existing partner found – create one if we have a name
        if not to_name:
            return self.env["res.partner"]

        city_id = vals.get("city_id") or (
            self.city_id.id if getattr(self, "city_id", False) else False
        )
        state_id = vals.get("state_id") or (
            self.state_id.id if getattr(self, "state_id", False) else False
        )
        country_id = vals.get("country_id") or (
            self.country_id.id if getattr(self, "country_id", False) else False
        )
        district_id = vals.get("district") or (
            self.district.id if getattr(self, "district", False) else False
        )
        region_id = vals.get("region_id") or (
            self.region_id.id if getattr(self, "region_id", False) else False
        )

        partner_vals = {
            "name": to_name,
            "email": email or False,
            "mobile": phone or False,
            "street": vals.get("street") or getattr(self, "street", False) or False,
            "street2": vals.get("street2") or getattr(self, "street2", False) or False,
            "zip": vals.get("zip") or getattr(self, "zip", False) or False,
            "state_id": state_id or False,
            "country_id": country_id or False,
            "partner_type_hhs": "customer",
            "sub_partner_type": "project",
        }
        # Conditionally set custom address fields if they exist on res.partner
        if city_id:
            partner_vals["customer_city_id"] = city_id
        if district_id:
            partner_vals["district_id"] = district_id
        if region_id:
            partner_vals["region_id"] = region_id

        new_partner = self.env["res.partner"].create(partner_vals)
        return new_partner

    @api.onchange("phone", "email")
    def _onchange_phone_email(self):
        if not self.phone and not self.email:
            return

        domain = []

        if self.phone:
            phone = self.phone.strip()
            domain = ["|", ("phone", "=", phone), ("mobile", "=", phone)]
        elif self.email:
            email = self.email.strip()
            domain = [("email", "=", email)]

        partner = self.env["res.partner"].search(domain, limit=1)

        if partner:
            self.partner_id = partner
            self.to_name = partner.name

            # Contact details
            self.email = partner.email or ""
            self.phone = partner.phone or partner.mobile or ""

            # Address
            self.street = partner.street or ""
            self.street2 = partner.street2 or ""
            self.zip = partner.zip or ""

            # Location
            self.city_id = partner.customer_city_id or False
            self.city = (
                partner.customer_city_id.name if partner.customer_city_id else ""
            )
            self.district = partner.district_id or False
            self.region_id = partner.region_id or False
            self.state_id = partner.state_id or False
            self.country_id = partner.country_id or False
            return {
                "warning": {
                    "title": _("Existing Customer Found"),
                    "message": _(
                        "Matching customer record found: %s "
                        "(Phone: %s, Email: %s). "
                        "Record linked to existing customer."
                    )
                    % (
                        partner.name,
                        partner.phone or partner.mobile or "",
                        partner.email or "",
                    ),
                }
            }
        else:
            # New phone/email → partner will be created on save
            return {
                "warning": {
                    "title": _("New Customer"),
                    "message": _(
                        "No existing customer found for the given Phone/Email. "
                        "A new customer record will be created automatically "
                        "when you save."
                    ),
                }
            }

    quotation_type_id = fields.Many2one(
        "crm.commercial.quotation.type", string="Quotation Type", index=True
    )
    partner_id = fields.Many2one("res.partner", string="Customer No", index=True)
    to_name = fields.Char(string="To", required=True)
    email = fields.Char(string="Email", required=True)
    phone = fields.Char(string="Phone", required=True)

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

    @api.onchange("city_id")
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            if self.city_id.state_id:
                self.state_id = self.city_id.state_id
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

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("confirmed", "Confirmed"),
            ("partially_delivered", "Partially Delivered"),
            ("delivered", "Delivered"),
            ("expired", "Expired"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        index=True,
    )

    assigned_id = fields.Many2one(
        "res.users",
        string="Assigned Salesman",
        domain="[('is_salesman', '=', True)]",
        default=lambda self: self.env.user,
        index=True,
    )
    project_category_id = fields.Many2one(
        "crm.commercial.project.category", string="Project Category", index=True
    )
    product_category_id = fields.Many2one(
        "product.category",
        string="Product Category",
        domain="[('use_for_crm_commercial', '=', True), ('exclude_category', '=', False)]",
        index=True,
        help="Select product category to auto-populate Payment Terms, Warranty Terms and Salient Features tabs.",
    )
    project_name = fields.Char(string="Project Name", index=True)

    expected_gross_margin = fields.Float(
        string="Expected Gross Margin %", readonly=True
    )
    expected_confirmation_date = fields.Date(string="Expected Confirmation Date")
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    expiry_date = fields.Date(string="Expiry Date")
    project_expected_closure_date = fields.Date(string="Project Expected Closure Date")
    developer = fields.Char(string="Developer")
    possibility_percent = fields.Float(string="Possibility (%)", default=50.0)
    project_status_id = fields.Many2one(
        "crm.commercial.project.status",
        string="Project Status",
        # required=True,
    )

    @api.onchange("project_status_id")
    def _onchange_project_status_id(self):
        if self.project_status_id:
            self.possibility_percent = self.project_status_id.probability

    project_detail_status_id = fields.Many2one(
        "crm.commercial.project.detail.status",
        string="Project Detail Status",
        # required=True,
    )
    consultant_id = fields.Many2one(
        "crm.commercial.consultant",
        string="Consultant",
        # required=True
    )
    tag_ids = fields.Many2many("crm.tag", string="Tags")
    ignore_for_reporting = fields.Boolean(
        string="Ignore this quotation for Reporting", default=False
    )
    show_vat_row_wise = fields.Boolean(
        string="Show the VAT calculation Row wise",
        default=False,
        help="If enabled, shows row-wise VAT details in PDF.",
    )

    # Additional Info Section
    supplier_support_recording = fields.Float(
        string="Supplier Support Recording", default=0.0
    )
    dsi_type = fields.Selection(
        [
            ("zero", "Zero"),
            ("original", "Original"),
            ("management", "Management Defined"),
        ],
        string="DSI Mode",
        default="zero",
    )
    dsi_percent = fields.Float(string="DSI %", default=0.0)
    salesman_commission_percent = fields.Float(
        string="Salesman Commission %", default=0.0
    )
    additional_discount_percent = fields.Float(
        string="Additional Discount %", default=0.0
    )
    promotion_percent = fields.Float(string="Promotion (E) %", default=0.0)

    total_project_value = fields.Float(
        string="Total Project Value", compute="_compute_costing_summary", store=True
    )
    delivered_value = fields.Float(string="Delivered Value", default=0.0)
    balance_value = fields.Float(
        string="Balance", compute="_compute_balance_value", store=True
    )

    # Costing Summary Fields
    total_selling_price = fields.Float(
        string="Total Selling Price (A)", compute="_compute_costing_summary", store=True
    )
    total_cost = fields.Float(
        string="Total Cost (B)", compute="_compute_costing_summary", store=True
    )
    total_supplier_support = fields.Float(
        string="Total Supplier Support (S)",
        compute="_compute_costing_summary",
        store=True,
    )
    total_dsi = fields.Float(
        string="Total DSI (C)", compute="_compute_costing_summary", store=True
    )
    total_smc = fields.Float(
        string="Total SMC (D)", compute="_compute_costing_summary", store=True
    )
    total_promo = fields.Float(
        string="Total Promo (E)", compute="_compute_costing_summary", store=True
    )
    net_price = fields.Float(
        string="Net Price (X)", compute="_compute_costing_summary", store=True
    )
    gross_margin = fields.Float(
        string="Gross Margin", compute="_compute_costing_summary", store=True
    )
    gross_margin_percent = fields.Float(
        string="Gross Margin (%)", compute="_compute_costing_summary", store=True
    )
    total_vat = fields.Float(
        string="Total VAT", compute="_compute_costing_summary", store=True
    )
    total_amount = fields.Float(
        string="Total Amount", compute="_compute_costing_summary", store=True
    )

    # Details & Tabs
    line_ids = fields.One2many(
        "crm.commercial.quotation.line",
        "quotation_id",
        string="General Material List Lines",
        copy=True,
    )
    payment_terms_tab = fields.Html(
        string="Payment Terms",
        compute="_compute_category_terms",
        store=True,
        readonly=False,
        precompute=True,
    )
    warranty_terms_tab = fields.Html(
        string="Warranty Terms",
        compute="_compute_category_terms",
        store=True,
        readonly=False,
        precompute=True,
    )
    salient_features_tab = fields.Html(
        string="Salient Features",
        compute="_compute_category_terms",
        store=True,
        readonly=False,
        precompute=True,
    )

    def _default_settings_tab(self):
        ICP = self.env["ir.config_parameter"].sudo()
        header = ICP.get_param("crm_commercial.terms_header_notes", default="")
        paragraph = ICP.get_param(
            "crm_commercial.quotation_intro_paragraph", default=""
        )
        footer = ICP.get_param("crm_commercial.terms_footer_notes", default="")
        combined = (header or "") + (paragraph or "") + (footer or "")
        return combined if combined.strip() else False

    settings_tab = fields.Html(string="Settings", default=_default_settings_tab)
    audit_ids = fields.One2many(
        "crm.commercial.quotation.audit",
        "quotation_id",
        string="Audit Log",
        readonly=True,
    )
    sale_order_ids = fields.One2many(
        "crm.commercial.sale.order", "quotation_id", string="Sale Orders"
    )
    sale_order_count = fields.Integer(
        string="Sale Orders Count", compute="_compute_sale_order_count"
    )

    @api.depends("sale_order_ids")
    def _compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_order_ids)

    def action_view_sale_order(self):
        self.ensure_one()
        orders = self.sale_order_ids
        action = self.env["ir.actions.actions"]._for_xml_id(
            "crm_commercial.action_crm_commercial_sale_order"
        )
        if len(orders) > 1:
            action["domain"] = [("id", "in", orders.ids)]
        elif len(orders) == 1:
            form_view = [
                (
                    self.env.ref(
                        "crm_commercial.view_crm_commercial_sale_order_form"
                    ).id,
                    "form",
                )
            ]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = orders.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    @api.depends("line_ids.product_category_id", "line_ids.product_id")
    def _compute_category_terms(self):
        for rec in self:
            payment_terms = False
            warranty_terms = False
            salient_features = False

            for line in rec.line_ids:
                cat = line.product_category_id or (
                    line.product_id.categ_id if line.product_id else False
                )
                while cat:
                    if cat.payment_terms_content and not payment_terms:
                        payment_terms = cat.payment_terms_content
                    if cat.warranty_terms_content and not warranty_terms:
                        warranty_terms = cat.warranty_terms_content
                    if cat.salient_features_content and not salient_features:
                        salient_features = cat.salient_features_content
                    if payment_terms and warranty_terms and salient_features:
                        break
                    cat = cat.parent_id

            if payment_terms:
                rec.payment_terms_tab = payment_terms
            elif not rec.payment_terms_tab:
                rec.payment_terms_tab = False

            if warranty_terms:
                rec.warranty_terms_tab = warranty_terms
            elif not rec.warranty_terms_tab:
                rec.warranty_terms_tab = False

            if salient_features:
                rec.salient_features_tab = salient_features
            elif not rec.salient_features_tab:
                rec.salient_features_tab = False

    @api.onchange("line_ids")
    def _onchange_line_ids_product_category(self):
        """Populate payment terms, warranty terms, and salient features strictly when product category or product is selected in grid lines."""
        payment_terms = False
        warranty_terms = False
        salient_features = False

        for line in self.line_ids:
            cat = line.product_category_id or (
                line.product_id.categ_id if line.product_id else False
            )
            while cat:
                if cat.payment_terms_content and not payment_terms:
                    payment_terms = cat.payment_terms_content
                if cat.warranty_terms_content and not warranty_terms:
                    warranty_terms = cat.warranty_terms_content
                if cat.salient_features_content and not salient_features:
                    salient_features = cat.salient_features_content
                if payment_terms and warranty_terms and salient_features:
                    break
                cat = cat.parent_id

        if payment_terms:
            self.payment_terms_tab = payment_terms
        if warranty_terms:
            self.warranty_terms_tab = warranty_terms
        if salient_features:
            self.salient_features_tab = salient_features

    @api.model_create_multi
    def create(self, vals_list):
        ICP = self.env["ir.config_parameter"].sudo()
        header = ICP.get_param("crm_commercial.terms_header_notes", default="")
        paragraph = ICP.get_param(
            "crm_commercial.quotation_intro_paragraph", default=""
        )
        footer = ICP.get_param("crm_commercial.terms_footer_notes", default="")
        combined_settings = (header or "") + (paragraph or "") + (footer or "")

        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "crm.commercial.quotation"
                ) or _("New")

            if not vals.get("settings_tab") and combined_settings.strip():
                vals["settings_tab"] = combined_settings

            # Auto-create / link res.partner when phone or email is provided
            # but no partner_id is explicitly set on the record.
            if not vals.get("partner_id") and (vals.get("phone") or vals.get("email")):
                phone = (vals.get("phone") or "").strip()
                email = (vals.get("email") or "").strip()
                to_name = (vals.get("to_name") or "").strip()

                if phone:
                    domain = [("mobile", "=", phone)]
                else:
                    domain = [("email", "=", email)]

                existing_partner = self.env["res.partner"].search(domain, limit=1)

                if existing_partner:
                    vals["partner_id"] = existing_partner.id
                elif to_name:
                    partner_vals = {
                        "name": to_name,
                        "email": email or False,
                        "mobile": phone or False,
                        "street": vals.get("street") or False,
                        "street2": vals.get("street2") or False,
                        "zip": vals.get("zip") or False,
                        "state_id": vals.get("state_id") or False,
                        "country_id": vals.get("country_id") or False,
                        "partner_type_hhs": "customer",
                        "sub_partner_type": "project",
                    }
                    if vals.get("city_id"):
                        partner_vals["customer_city_id"] = vals["city_id"]
                    if vals.get("district"):
                        partner_vals["district_id"] = vals["district"]
                    if vals.get("region_id"):
                        partner_vals["region_id"] = vals["region_id"]

                    new_partner = self.env["res.partner"].create(partner_vals)
                    vals["partner_id"] = new_partner.id

        records = super(CrmCommercialQuotation, self).create(vals_list)
        for rec in records:
            rec._log_audit(
                "Quotation Created",
                f"Created initial quotation record with status {rec.state}.",
            )
            if rec.assigned_id and rec.assigned_id.quotation_auto_approval:
                rec.state = "approved"
        return records

    def write(self, vals):
        if "state" in vals:
            for rec in self:
                rec._log_audit(
                    "Status Changed",
                    f'Status updated from {rec.state} to {vals.get("state")}.',
                )
        res = super(CrmCommercialQuotation, self).write(vals)
        return res

    def _log_audit(self, title, notes):
        for rec in self:
            self.env["crm.commercial.quotation.audit"].create(
                {
                    "quotation_id": rec.id,
                    "user_id": self.env.user.id,
                    "title": title,
                    "notes": notes,
                    "state": rec.state,
                }
            )

    @api.constrains(
        "line_ids",
        "line_ids.sale_price",
        "line_ids.unit_cost",
        "line_ids.discount_percent",
        "line_ids.display_type",
    )
    def _check_sales_price_below_cost(self):
        for rec in self:
            below_cost_items = []
            for line in rec.line_ids.filtered(lambda l: not l.display_type):
                effective_price = line.sale_price * (
                    1.0 - (line.discount_percent / 100.0)
                )
                if line.unit_cost > 0 and effective_price < line.unit_cost:
                    below_cost_items.append(
                        f"{line.product_id.display_name} (Price: {effective_price:.2f}, Cost: {line.unit_cost:.2f})"
                    )
            if below_cost_items:
                raise ValidationError(
                    _(
                        "Cost Validation Failed! Sales price after discount cannot be less than unit cost for items:\n- "
                    )
                    + "\n- ".join(below_cost_items)
                )

    @api.depends(
        "line_ids",
        "line_ids.amount",
        "line_ids.unit_cost",
        "supplier_support_recording",
        "dsi_percent",
        "salesman_commission_percent",
        "promotion_percent",
        "line_ids.display_type",
    )
    def _compute_costing_summary(self):
        for rec in self:
            product_lines = rec.line_ids.filtered(lambda l: not l.display_type)
            a = sum(line.qty * line.sale_price for line in product_lines)
            b = sum(line.qty * line.unit_cost for line in product_lines)
            s = rec.supplier_support_recording
            c = a * (rec.dsi_percent / 100.0) if rec.dsi_type != "zero" else 0.0
            d = a * (rec.salesman_commission_percent / 100.0)
            e = a * (rec.promotion_percent / 100.0)
            x = a + e - c - d
            gm = x - (b - s)
            gm_pct = (gm / x * 100.0) if x else 0.0
            vat = sum(line.vat_amount for line in product_lines)
            tot = sum(line.amount for line in product_lines)

            rec.total_selling_price = a
            rec.total_cost = b
            rec.total_supplier_support = s
            rec.total_dsi = c
            rec.total_smc = d
            rec.total_promo = e
            rec.net_price = x
            rec.gross_margin = gm
            rec.gross_margin_percent = gm_pct
            rec.total_vat = vat
            rec.total_amount = tot
            rec.total_project_value = tot

    @api.depends("total_project_value", "delivered_value")
    def _compute_balance_value(self):
        for rec in self:
            rec.balance_value = rec.total_project_value - rec.delivered_value

    def action_recalculate(self):
        for rec in self:
            for line in rec.line_ids:
                line._compute_pricing()
            rec._compute_costing_summary()

    def action_refresh_cost(self):
        for rec in self:
            for line in rec.line_ids:
                if line.product_id:
                    line.unit_cost = line.product_id.standard_price
                    line.sale_price = line.product_id.lst_price
            rec.action_recalculate()

    def _get_pdf_category_details(self):
        """Returns structured details of categories used on lines for PDF rendering."""
        self.ensure_one()
        cat_map = {}
        for line in self.line_ids:
            cat = line.product_category_id or (
                line.product_id.categ_id if line.product_id else False
            )
            while cat:
                if cat.id not in cat_map and (
                    cat.payment_terms_content
                    or cat.warranty_terms_content
                    or cat.salient_features_content
                ):
                    cat_map[cat.id] = {
                        "id": cat.id,
                        "category": cat,
                        "name": cat.name,
                        "payment_terms": cat.payment_terms_content,
                        "warranty_terms": cat.warranty_terms_content,
                        "salient_features": cat.salient_features_content,
                    }
                cat = cat.parent_id
        return list(cat_map.values())

    def action_open_import_material_list(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Import Material List",
            "res_model": "crm.commercial.import.material.list.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_quotation_id": self.id},
        }

    def action_copy_quotation(self):
        self.ensure_one()
        line_commands = []
        for line in self.line_ids:
            line_commands.append(
                (
                    0,
                    0,
                    {
                        "product_group_id": (
                            line.product_group_id.id if line.product_group_id else False
                        ),
                        "product_category_id": (
                            line.product_category_id.id
                            if line.product_category_id
                            else False
                        ),
                        "sale_type_id": (
                            line.sale_type_id.id if line.sale_type_id else False
                        ),
                        "product_id": line.product_id.id if line.product_id else False,
                        "qty": line.qty,
                        "unit_cost": line.unit_cost,
                        "sale_price": line.sale_price,
                        "discount_percent": line.discount_percent,
                        "special_support": line.special_support,
                        "vat_percent": line.vat_percent,
                    },
                )
            )

        country_rec = self._default_country_id()

        ctx = dict(self.env.context)
        ctx.update(
            {
                "default_state": "draft",
                "default_quotation_type_id": (
                    self.quotation_type_id.id if self.quotation_type_id else False
                ),
                "default_assigned_id": (
                    self.assigned_id.id if self.assigned_id else False
                ),
                "default_project_category_id": (
                    self.project_category_id.id if self.project_category_id else False
                ),
                "default_product_category_id": (
                    self.product_category_id.id if self.product_category_id else False
                ),
                "default_project_name": self.project_name,
                "default_expected_confirmation_date": self.expected_confirmation_date,
                "default_date": fields.Date.context_today(self),
                "default_expiry_date": self.expiry_date,
                "default_project_expected_closure_date": self.project_expected_closure_date,
                "default_developer": self.developer,
                "default_possibility_percent": self.possibility_percent,
                "default_project_status_id": (
                    self.project_status_id.id if self.project_status_id else False
                ),
                "default_project_detail_status_id": (
                    self.project_detail_status_id.id
                    if self.project_detail_status_id
                    else False
                ),
                "default_consultant_id": (
                    self.consultant_id.id if self.consultant_id else False
                ),
                "default_tag_ids": (
                    [(6, 0, self.tag_ids.ids)] if self.tag_ids else False
                ),
                "default_ignore_for_reporting": self.ignore_for_reporting,
                "default_show_vat_row_wise": self.show_vat_row_wise,
                "default_supplier_support_recording": self.supplier_support_recording,
                "default_dsi_type": self.dsi_type,
                "default_dsi_percent": self.dsi_percent,
                "default_salesman_commission_percent": self.salesman_commission_percent,
                "default_additional_discount_percent": self.additional_discount_percent,
                "default_promotion_percent": self.promotion_percent,
                "default_payment_terms_tab": self.payment_terms_tab,
                "default_warranty_terms_tab": self.warranty_terms_tab,
                "default_salient_features_tab": self.salient_features_tab,
                "default_settings_tab": self.settings_tab,
                "default_line_ids": line_commands,
                "default_warehouse_id": False,
                "default_partner_id": False,
                "default_to_name": False,
                "default_email": False,
                "default_phone": False,
                "default_street": False,
                "default_street2": False,
                "default_city_id": False,
                "default_city": False,
                "default_district": False,
                "default_region_id": False,
                "default_state_id": False,
                "default_country_id": country_rec.id if country_rec else False,
                "default_zip": False,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Commercial Quotation"),
            "res_model": "crm.commercial.quotation",
            "view_mode": "form",
            "target": "current",
            "context": ctx,
        }

    def action_revision(self):
        self.ensure_one()
        self.state = "cancelled"
        self._log_audit(
            "Quotation Revised",
            f"Quotation cancelled due to new revision #{self.revision_number + 1}.",
        )
        revised = self.copy(
            {
                "name": f"{self.name.split('-R')[0]}-R{self.revision_number + 1}",
                "revision_number": self.revision_number + 1,
                "parent_quotation_id": self.id,
                "state": "draft",
                "date": fields.Date.context_today(self),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Revised Quotation"),
            "res_model": "crm.commercial.quotation",
            "res_id": revised.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_confirm(self):
        last_so = False
        for rec in self:
            if not rec.partner_id:
                raise ValidationError(
                    _("Customer No is mandatory to confirm quotation.")
                )
            # Check required fields at confirm time only
            missing_fields = []
            if not rec.project_status_id:
                missing_fields.append(_("Project Status"))
            if not rec.project_detail_status_id:
                missing_fields.append(_("Project Detail Status"))
            if not rec.consultant_id:
                missing_fields.append(_("Consultant"))

            if missing_fields:
                raise ValidationError(
                    _(
                        "The following fields are mandatory to confirm the quotation:\n- %s"
                    )
                    % "\n- ".join(missing_fields)
                )

            rec.expected_gross_margin = rec.gross_margin_percent
            rec.state = "confirmed"

            # Check if Sale Order already exists
            existing_so = self.env["crm.commercial.sale.order"].search(
                [("quotation_id", "=", rec.id)], limit=1
            )
            if existing_so:
                last_so = existing_so
                continue

            # Create Sale Order with ALL information from quotation screen
            so = self.env["crm.commercial.sale.order"].create(
                {
                    "quotation_id": rec.id,
                    "quotation_no": rec.name,
                    "quotation_type_id": (
                        rec.quotation_type_id.id if rec.quotation_type_id else False
                    ),
                    "partner_id": rec.partner_id.id,
                    "to_name": rec.to_name,
                    "email": rec.email,
                    "phone": rec.phone,
                    # Address fields
                    "street": rec.street,
                    "street2": rec.street2,
                    "city_id": rec.city_id.id if rec.city_id else False,
                    "city": rec.city,
                    "district": rec.district,
                    "region_id": rec.region_id.id if rec.region_id else False,
                    "state_id": rec.state_id.id if rec.state_id else False,
                    "country_id": rec.country_id.id if rec.country_id else False,
                    "zip": rec.zip,
                    # Header & commercial details
                    "warehouse_id": rec.warehouse_id.id,
                    "assigned_id": rec.assigned_id.id,
                    "project_category_id": (
                        rec.project_category_id.id if rec.project_category_id else False
                    ),
                    "project_name": rec.project_name,
                    "consultant_id": (
                        rec.consultant_id.id if rec.consultant_id else False
                    ),
                    "developer": rec.developer,
                    "project_status_id": (
                        rec.project_status_id.id if rec.project_status_id else False
                    ),
                    "project_detail_status_id": (
                        rec.project_detail_status_id.id
                        if rec.project_detail_status_id
                        else False
                    ),
                    "tag_ids": [(6, 0, rec.tag_ids.ids)],
                    "date_order": rec.date or fields.Date.context_today(rec),
                    "expiry_date": rec.expiry_date,
                    "expected_gross_margin": rec.gross_margin_percent,
                    "actual_gross_margin": rec.gross_margin_percent,
                    # Costing totals
                    "total_selling_price": rec.total_selling_price,
                    "total_cost": rec.total_cost,
                    "total_supplier_support": rec.total_supplier_support,
                    "total_dsi": rec.total_dsi,
                    "total_smc": rec.total_smc,
                    "total_promo": rec.total_promo,
                    "net_price": rec.net_price,
                    "total_vat": rec.total_vat,
                    "total_amount": rec.total_amount,
                    # Terms tabs
                    "payment_terms_tab": rec.payment_terms_tab,
                    "warranty_terms_tab": rec.warranty_terms_tab,
                    "salient_features_tab": rec.salient_features_tab,
                    "settings_tab": rec.settings_tab,
                }
            )

            # Create Order Items and Delivery Schedule for each product line
            for line in rec.line_ids.filtered(
                lambda l: not l.display_type and l.product_id
            ):
                so_line = self.env["crm.commercial.sale.order.line"].create(
                    {
                        "order_id": so.id,
                        "quotation_line_id": line.id,
                        "name": line.name or line.product_id.display_name,
                        "product_group_id": (
                            line.product_group_id.id if line.product_group_id else False
                        ),
                        "product_category_id": (
                            line.product_category_id.id
                            if line.product_category_id
                            else False
                        ),
                        "product_id": line.product_id.id,
                        "qty": line.qty,
                        "unit_cost": line.unit_cost,
                        "sale_price": line.sale_price,
                        "discount_percent": line.discount_percent,
                        "vat_amount": line.vat_amount,
                        "amount": line.amount,
                    }
                )
                self.env["crm.commercial.delivery.schedule"].create(
                    {
                        "order_id": so.id,
                        "order_line_id": so_line.id,
                        "scheduled_date": rec.date or fields.Date.context_today(rec),
                        "qty_to_deliver": line.qty,
                        "delivered_qty": 0.0,
                        "status": "yet_to_deliver",
                    }
                )

            so._log_audit(
                title="Sale Order Created from Quotation",
                notes=f"Sale Order {so.name} generated from confirmed Quotation {rec.name}. "
                f"Imported {len(so.line_ids)} item(s) and {len(so.delivery_schedule_ids)} delivery schedule line(s).",
            )

            rec._log_audit(
                "Quotation Confirmed",
                f"Quotation confirmed and Sale Order {so.name} created.",
            )
            last_so = so

        if len(self) == 1 and last_so:
            return self.action_view_sale_order()


class CrmCommercialQuotationLine(models.Model):
    _name = "crm.commercial.quotation.line"
    _description = "CRM Commercial Quotation Line"
    _order = "quotation_id, sequence, id"

    quotation_id = fields.Many2one(
        "crm.commercial.quotation", string="Quotation", ondelete="cascade", index=True
    )
    sequence = fields.Integer(string="Sequence", default=10)
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")], default=False
    )
    name = fields.Text(string="Description / Section Name")

    product_group_id = fields.Many2one(
        "product.category",
        string="Product Group",
        domain="[('use_for_crm_commercial', '=', True), ('parent_id', '=', False)]",
    )
    product_category_id = fields.Many2one(
        "product.category",
        string="Product Category",
        domain="[('use_for_crm_commercial', '=', True), ('exclude_category', '=', False), ('parent_id', 'child_of', product_group_id), ('id', '!=', product_group_id)] if product_group_id else [('id', '=', False)]",
    )
    sale_type_id = fields.Many2one("crm.commercial.sale.type", string="Sale Type")
    product_id = fields.Many2one(
        "product.product",
        string="Part No / Product",
        index=True,
        domain="[('categ_id', 'child_of', product_category_id)] if product_category_id else []",
    )

    stock_qty = fields.Float(
        string="Stock", compute="_compute_stock_qty", readonly=True
    )
    qty = fields.Float(string="Qty", default=1.0)

    unit_cost = fields.Float(string="Unit Cost")
    sale_price = fields.Float(string="Sale Price")
    discount_percent = fields.Float(string="Discount %", default=0.0)
    special_support = fields.Float(string="Spl Spt", default=0.0)

    dsi = fields.Float(string="DSI", related="quotation_id.dsi_percent", readonly=True)
    smc = fields.Float(
        string="SMC", related="quotation_id.salesman_commission_percent", readonly=True
    )

    vat_percent = fields.Float(string="VAT %", default=15.0)
    vat_amount = fields.Float(string="VAT", compute="_compute_pricing", store=True)
    amount = fields.Float(string="Amount", compute="_compute_pricing", store=True)

    @api.onchange("product_group_id")
    def _onchange_product_group_id(self):
        """Reset product_category_id if product_group_id is cleared or changed."""
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

    def _get_linked_product_for(self, product):
        if not product:
            return False
        rec = self.env["crm.commercial.linked.product"].search(
            [
                ("source_product_id", "=", product.id),
                ("status", "=", "active"),
                ("active", "=", True),
            ],
            limit=1,
        )
        if rec and rec.linked_product_id:
            return rec.linked_product_id
        rec2 = self.env["crm.commercial.linked.product"].search(
            [
                ("linked_product_id", "=", product.id),
                ("status", "=", "active"),
                ("active", "=", True),
            ],
            limit=1,
        )
        if rec2 and rec2.source_product_id:
            return rec2.source_product_id
        return False

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_cost = self.product_id.standard_price
            self.sale_price = self.product_id.lst_price

            prod_cat = (
                getattr(self.product_id, "product_group_id", False)
                or getattr(self.product_id, "product_category_id", False)
                or self.product_id.categ_id
            )

            category_rec = False
            group_rec = False
            if prod_cat:
                cat = prod_cat
                while cat:
                    if cat.use_for_crm_commercial:
                        if cat.parent_id and not category_rec:
                            category_rec = cat
                        if not cat.parent_id and not group_rec:
                            group_rec = cat
                    cat = cat.parent_id

            if not category_rec and prod_cat and prod_cat.use_for_crm_commercial:
                category_rec = prod_cat

            if not group_rec and category_rec and category_rec.parent_id:
                c = category_rec
                while c.parent_id:
                    c = c.parent_id
                group_rec = c

            if category_rec:
                self.product_category_id = category_rec.id
                if category_rec.default_discount_percent:
                    self.discount_percent = category_rec.default_discount_percent

            if group_rec:
                self.product_group_id = group_rec.id

            cat = self.product_category_id or prod_cat
            while cat:
                if self.quotation_id:
                    if (
                        cat.payment_terms_content
                        and not self.quotation_id.payment_terms_tab
                    ):
                        self.quotation_id.payment_terms_tab = cat.payment_terms_content
                    if (
                        cat.warranty_terms_content
                        and not self.quotation_id.warranty_terms_tab
                    ):
                        self.quotation_id.warranty_terms_tab = (
                            cat.warranty_terms_content
                        )
                    if (
                        cat.salient_features_content
                        and not self.quotation_id.salient_features_tab
                    ):
                        self.quotation_id.salient_features_tab = (
                            cat.salient_features_content
                        )
                cat = cat.parent_id

            # Auto-add linked product if active
            if self.quotation_id and not self.env.context.get(
                "skip_linked_product_addition"
            ):
                linked_prod = self._get_linked_product_for(self.product_id)
                if linked_prod:
                    already_exists = self.quotation_id.line_ids.filtered(
                        lambda l: l.product_id.id == linked_prod.id
                    )
                    if not already_exists:
                        l_prod_cat = (
                            getattr(linked_prod, "product_group_id", False)
                            or getattr(linked_prod, "product_category_id", False)
                            or linked_prod.categ_id
                        )
                        l_cat_rec = False
                        l_grp_rec = False
                        if l_prod_cat:
                            c = l_prod_cat
                            while c:
                                if c.use_for_crm_commercial:
                                    if c.parent_id and not l_cat_rec:
                                        l_cat_rec = c
                                    if not c.parent_id and not l_grp_rec:
                                        l_grp_rec = c
                                c = c.parent_id
                        if (
                            not l_cat_rec
                            and l_prod_cat
                            and l_prod_cat.use_for_crm_commercial
                        ):
                            l_cat_rec = l_prod_cat
                        if not l_grp_rec and l_cat_rec and l_cat_rec.parent_id:
                            c = l_cat_rec
                            while c.parent_id:
                                c = c.parent_id
                            l_grp_rec = c
                        l_disc = (
                            l_cat_rec.default_discount_percent
                            if l_cat_rec and l_cat_rec.default_discount_percent
                            else 0.0
                        )

                        line_vals = {
                            "quotation_id": self.quotation_id._origin.id
                            or self.quotation_id.id,
                            "product_group_id": l_grp_rec.id if l_grp_rec else False,
                            "product_category_id": l_cat_rec.id if l_cat_rec else False,
                            "product_id": linked_prod.id,
                            "qty": self.qty or 1.0,
                            "unit_cost": linked_prod.standard_price,
                            "sale_price": linked_prod.lst_price,
                            "discount_percent": l_disc,
                        }
                        if self.quotation_id._origin.id:
                            self.env["crm.commercial.quotation.line"].with_context(
                                skip_linked_product_addition=True
                            ).create(line_vals)
                        else:
                            self.quotation_id.line_ids = [(0, 0, line_vals)]

    @api.onchange("product_category_id")
    def _onchange_product_category_id_terms(self):
        """When Product Category is selected on a grid line, auto-populate terms in quotation tabs and default discount if empty."""
        cat = self.product_category_id
        if cat:
            if cat.default_discount_percent and not self.discount_percent:
                self.discount_percent = cat.default_discount_percent
            while cat:
                if self.quotation_id:
                    if cat.payment_terms_content:
                        self.quotation_id.payment_terms_tab = cat.payment_terms_content
                    if cat.warranty_terms_content:
                        self.quotation_id.warranty_terms_tab = (
                            cat.warranty_terms_content
                        )
                    if cat.salient_features_content:
                        self.quotation_id.salient_features_tab = (
                            cat.salient_features_content
                        )
                cat = cat.parent_id

    @api.onchange("discount_percent")
    def _onchange_discount_percent_limit(self):
        if self.discount_percent and self.product_category_id:
            user_limit = self.env.user.discount_limit_percent
            categ_limit = self.product_category_id.default_discount_percent
            entered_disc = self.discount_percent
            if user_limit > 0 and entered_disc > user_limit:
                self.discount_percent = user_limit
                return {
                    "warning": {
                        "title": _("User Discount Limit Exceeded"),
                        "message": _(
                            "Your maximum discount limit is %s%%. You entered %s%%."
                        )
                        % (user_limit, entered_disc),
                    }
                }
            if categ_limit > 0 and entered_disc > categ_limit:
                self.discount_percent = categ_limit
                return {
                    "warning": {
                        "title": _("Category Discount Limit Exceeded"),
                        "message": _(
                            "Product Category (%s) discount limit is %s%%. You entered %s%%."
                        )
                        % (self.product_category_id.name, categ_limit, entered_disc),
                    }
                }

    @api.constrains("discount_percent", "product_category_id", "display_type")
    def _check_discount_limit(self):
        for line in self:
            if line.display_type:
                continue
            user = self.env.user
            user_limit = user.discount_limit_percent
            categ_limit = (
                line.product_category_id.default_discount_percent
                if line.product_category_id
                else 0.0
            )

            if user_limit > 0 and line.discount_percent > user_limit:
                raise ValidationError(
                    _("Your Discount Limit is %s%%. You entered %s%%.")
                    % (user_limit, line.discount_percent)
                )
            if categ_limit > 0 and line.discount_percent > categ_limit:
                raise ValidationError(
                    _("Product Category (%s) Discount Limit is %s%%. You entered %s%%.")
                    % (
                        line.product_category_id.name,
                        categ_limit,
                        line.discount_percent,
                    )
                )

    @api.depends("product_id", "quotation_id.warehouse_id")
    def _compute_stock_qty(self):
        for line in self:
            if line.product_id and line.quotation_id.warehouse_id:
                line.stock_qty = line.product_id.with_context(
                    warehouse=line.quotation_id.warehouse_id.id
                ).qty_available
            elif line.product_id:
                line.stock_qty = line.product_id.qty_available
            else:
                line.stock_qty = 0.0

    @api.depends("qty", "sale_price", "discount_percent", "vat_percent", "display_type")
    def _compute_pricing(self):
        for line in self:
            if line.display_type:
                line.vat_amount = 0.0
                line.amount = 0.0
                continue
            discounted_unit_price = line.sale_price * (
                1.0 - (line.discount_percent / 100.0)
            )
            subtotal = line.qty * discounted_unit_price
            vat = subtotal * (line.vat_percent / 100.0)
            line.vat_amount = vat
            line.amount = subtotal + vat

    def _add_linked_product_line(self):
        for line in self:
            if not line.quotation_id or not line.product_id:
                continue
            if self.env.context.get("skip_linked_product_addition"):
                continue
            linked_prod = self._get_linked_product_for(line.product_id)
            if linked_prod:
                already_exists = line.quotation_id.line_ids.filtered(
                    lambda l: l.product_id.id == linked_prod.id
                )
                if not already_exists:
                    prod_cat = (
                        getattr(linked_prod, "product_group_id", False)
                        or getattr(linked_prod, "product_category_id", False)
                        or linked_prod.categ_id
                    )
                    category_rec = False
                    group_rec = False
                    if prod_cat:
                        cat = prod_cat
                        while cat:
                            if cat.use_for_crm_commercial:
                                if cat.parent_id and not category_rec:
                                    category_rec = cat
                                if not cat.parent_id and not group_rec:
                                    group_rec = cat
                            cat = cat.parent_id
                    if (
                        not category_rec
                        and prod_cat
                        and prod_cat.use_for_crm_commercial
                    ):
                        category_rec = prod_cat
                    if not group_rec and category_rec and category_rec.parent_id:
                        c = category_rec
                        while c.parent_id:
                            c = c.parent_id
                        group_rec = c
                    line_discount = (
                        category_rec.default_discount_percent
                        if category_rec and category_rec.default_discount_percent
                        else 0.0
                    )

                    self.with_context(skip_linked_product_addition=True).create(
                        {
                            "quotation_id": line.quotation_id.id,
                            "product_group_id": group_rec.id if group_rec else False,
                            "product_category_id": (
                                category_rec.id if category_rec else False
                            ),
                            "product_id": linked_prod.id,
                            "qty": line.qty or 1.0,
                            "unit_cost": linked_prod.standard_price,
                            "sale_price": linked_prod.lst_price,
                            "discount_percent": line_discount,
                        }
                    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(CrmCommercialQuotationLine, self).create(vals_list)
        if not self.env.context.get("skip_linked_product_addition"):
            records._add_linked_product_line()
        return records


class CrmCommercialQuotationAudit(models.Model):
    _name = "crm.commercial.quotation.audit"
    _description = "Quotation Audit Log"
    _order = "create_date desc"

    quotation_id = fields.Many2one(
        "crm.commercial.quotation", string="Quotation", ondelete="cascade", index=True
    )
    user_id = fields.Many2one("res.users", string="User", readonly=True)
    title = fields.Char(string="Title", readonly=True)
    notes = fields.Text(string="Notes / Reason", readonly=True)
    state = fields.Char(string="Status", readonly=True)
