from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError,AccessError
from datetime import datetime, date,time, timezone,timedelta
from math import radians, sin, cos, sqrt, atan2
import re 
import logging

_logger = logging.getLogger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c


class dealerShowroomSales(models.Model):
    _name = 'dsales.showroom.sales'
    _description = 'Review Showroom Sales'
    _rec_name = 'invoice_no'
    _order = 'date_time desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Using python constrains instead of _sql_constraints so it works even if old duplicate records exist

    name = fields.Char(
        string="Redemption Reference",
        compute="_compute_name"
    )

    @api.depends()
    def _compute_name(self):
        user = self.env.user
        for rec in self:
            if user.has_group('dealer.group_dealer_user'):
                rec.name = "Update Sales"
            else:
                rec.name = "Review Shop Sales"

    dealer_id = fields.Many2one(
        'res.partner',
        string='Dealer',
        domain="[('dealersalesman_required', '=', True)]",
        required=True,
    )

    dealer_showroom_id = fields.Many2one(
        'dsales.showroom',
        string='Dealer Showroom',
        required=True,
        domain="[('dealer_id', '=', dealer_id)]"
    )

    
    dealer_assignment_id = fields.Many2one(
        'dsales.assignment',
        string='Salesman',
        required=True,
        domain="[('dealer_id', '=', dealer_id), ('dealer_showroom_id', '=', dealer_showroom_id)]",
    )


    date_time = fields.Datetime(
        string='Date & Time',
        default=fields.Datetime.now,
        required=True
    )

    # product_category_id = fields.Many2one('t.groupsdesc', string='Category',required=True)
    # group_id = fields.Many2one('t.productsdesc', string='Group',required=True) 
    # subgroup_id = fields.Many2one('vi.product.subgroup', string='Sub Group', required=True)
    # group_code = fields.Char(related='group_id.p_grp', store=True)
    # product_id = fields.Many2one('vi.product.catalog', string='Product', required=True)
    # product_code = fields.Char(related='subgroup_id.psubgroup_code', store=True)

    product_category_id = fields.Many2one(
        'product.category',
        string="Product Category",
        domain="[('parent_id','=',False),('name', '!=', 'All')]"
    )


    # product_category_id = fields.Many2one(
    #     'product.category',
    #     string="Product Category",
    #     domain="[('parent_id','=',False),('name', '!=', 'All')]",
    #     readonly=True,  # always readonly in the view
    #     compute='_compute_product_category_id',  # compute it
    #     store=True
    # )

    # @api.depends('dealer_mobile_user_bool')
    # def _compute_product_category_id(self):
    #     for rec in self:
    #         if rec.dealer_mobile_user_bool:
    #             dealer_assignment = self.env['dsales.assignment'].search(
    #                 [('dealer_id', '=', self.env.user.id)], limit=1
    #             )
    #             rec.product_category_id = dealer_assignment.category_id.id if dealer_assignment else False
    #         else:
    #             rec.product_category_id = rec.product_category_id or False

  
    # @api.depends('dealer_mobile_user_bool')
    # def _compute_product_category_id(self):
    #     for rec in self:
    #         if rec.dealer_mobile_user_bool:
    #             # Mobile user → auto-fill from dealer assignment
    #             dealer_assignment = self.env['dsales.assignment'].search(
    #                 [('sale_dealer_id', '=', self.env.user.id)], limit=1
    #             )
    #             rec.product_category_id = dealer_assignment.category_id.id if dealer_assignment else False
    #         else:
    #             # Back-office → keep existing value, editable
    #             rec.product_category_id = rec.product_category_id

    # def _inverse_product_category_id(self): allowed_group_is_dealer
    #     # Allows saving value if changed by back-office user
    #     for rec in self:
    #         rec.product_category_id = rec.product_category_id



    group_id = fields.Many2one('product.category',string="Product Group" , 
                                     context=lambda self: {'show_only_name': True})

    subgroup_id = fields.Many2one('product.category',string="Product Sub Group",
                                        context=lambda self: {'show_only_name': True})
                                        
    product_id = fields.Many2one('product.product', string="Model",required=False)
    

    size_id = fields.Many2one('product.size', string='Capacity', compute="_compute_capacity")
    
    is_sales_return = fields.Boolean(string="Sales Return", help="Enable this option to record a sales return. "
         "This will allow negative quantities, and Notes will be mandatory.")
    qty = fields.Integer(string='Quantity',required=False)
    notes = fields.Text(string='Notes')

    @api.onchange('is_sales_return')
    def _onchange_is_sales_return(self):
        for record in self:
            if not record.is_sales_return:
                record.qty = 0
                record.notes = False

    year = fields.Integer(
        string="Year",
        compute="_compute_year_month",
        store=True
    )

    month = fields.Integer(
        string="Month",
        compute="_compute_year_month",
        store=True
    )

    @api.depends("date_time")
    def _compute_year_month(self):
        for rec in self:
            if rec.date_time:
                rec.year = rec.date_time.year
                rec.month = rec.date_time.month
            else:
                rec.year = 0
                rec.month = 0

    
    invoice_no = fields.Char(string='Invoice No', required=True, copy=False)

    @api.model
    def _get_default_invoice_no(self):
        seq = self.env['ir.sequence'].search([('name', '=', 'SALES_ENTRY')], limit=1)
        if seq:
            return seq.next_by_id()
        return self.env['ir.sequence'].next_by_code('SALES_ENTRY') or 'New'

    @api.constrains('invoice_no')
    def _check_unique_invoice_no(self):
        for rec in self:
            if rec.invoice_no:
                if self.search_count([('invoice_no', '=', rec.invoice_no)]) > 1:
                    raise ValidationError(_("Invoice Number must be unique! Duplicate found: %s") % rec.invoice_no)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        compute='_compute_requires_approval',
        store=True
    )

    @api.depends('dealer_id', 'line_ids.qty', 'date_time')
    def _compute_requires_approval(self):
        for rec in self:
            rec.requires_approval = False
            params = self.env['ir.config_parameter'].sudo()
            
            from odoo.fields import Date as FieldDate
            def _parse_date(val):
                if val and val != 'False':
                    try: return FieldDate.to_date(val)
                    except Exception: return False
                return False

            current_date = (rec.date_time or fields.Datetime.now()).date()
            total_qty = sum(abs(line.qty) for line in rec.line_ids) if rec.line_ids else abs(rec.qty or 0)

            is_dealer = False
            if rec.dealer_id:
                is_cust = getattr(rec.dealer_id, 'partner_type_hhs', False) == 'customer'
                is_sub_dealer = getattr(rec.dealer_id, 'sub_partner_type', False) == 'dealer'
                is_req = getattr(rec.dealer_id, 'dealersalesman_required', False)
                if is_cust and is_sub_dealer and is_req:
                    is_dealer = True

            if is_dealer:
                # Check Dealer Limit unconditionally
                base_dealer_limit = float(params.get_param('dealer.dealer_sales_limit', default=100.0))
                if total_qty >= base_dealer_limit:
                    rec.requires_approval = True

                dealer_required = params.get_param('dealer.dealer_promotion_multiplier_required')
                if dealer_required and dealer_required != 'False':
                    from_date = _parse_date(params.get_param('dealer.dealer_promotion_from_date', ''))
                    to_date = _parse_date(params.get_param('dealer.dealer_promotion_to_date', ''))
                    
                    valid_date = True
                    if from_date and current_date < from_date: valid_date = False
                    if to_date and current_date > to_date: valid_date = False
                    
                    if valid_date:
                        dealer_sales_limit = float(params.get_param('dealer.dealer_sales_limit', default=100.0))
                        if total_qty >= dealer_sales_limit:
                            rec.requires_approval = True
            else:
                # Check Retailer Limit unconditionally
                base_retailer_limit = float(params.get_param('dealer.retailer_sales_limit', default=25.0))
                if total_qty >= base_retailer_limit:
                    rec.requires_approval = True

                gen_required = params.get_param('dealer.general_promotion_multiplier_required')
                if gen_required and gen_required != 'False':
                    from_date = _parse_date(params.get_param('dealer.general_promotion_from_date', ''))
                    to_date = _parse_date(params.get_param('dealer.general_promotion_to_date', ''))
                    
                    valid_date = True
                    if from_date and current_date < from_date: valid_date = False
                    if to_date and current_date > to_date: valid_date = False
                    
                    if valid_date:
                        retailer_sales_limit = float(params.get_param('dealer.retailer_sales_limit', default=25.0))
                        if total_qty >= retailer_sales_limit:
                            rec.requires_approval = True

    invoice_attachment = fields.Binary(string='Invoice Attachment')
    invoice_attachment_name = fields.Char(string='Attachment Name')
    
    line_ids = fields.One2many(
        'dsales.showroom.sales.line',
        'sales_id',
        string="Sales Lines"
    )

    @api.constrains('line_ids', 'state')
    def _check_at_least_one_line(self):
        for rec in self:
            if rec.state != 'draft':
                if not rec.line_ids:
                    raise UserError(_("At least one sales entry (line) is required!"))
                if not any(line.product_id for line in rec.line_ids):
                    raise UserError(_("At least one product entry must be selected in the sales lines!"))

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'dealer_shop_sales_attachment_rel',
        'sales_id',
        'attachment_id',
        string='Attachments'
    )

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("At least one sales line is required.")
            if not any(line.product_id for line in rec.line_ids):
                raise UserError("At least one product entry must be selected in the sales lines.")
            if rec.requires_approval:
                rec.state = 'submitted'
            else:
                rec.state = 'approved'

    def action_open_add_item_wizard(self):
        self.ensure_one()
        return {
            'name': _('Add Item'),
            'type': 'ir.actions.act_window',
            'res_model': 'dealer.sales.line.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sales_id': self.id}
        }

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            self._send_whatsapp_notification(rec)

    def _send_whatsapp_notification(self, rec):
        _logger.info(f"WhatsApp Notification: Sales record {rec.invoice_no} rejected for Salesman {rec.user_id.name if rec.user_id else ''}")

    def _default_dealer_mobile_user_bool(self): 
        return bool(self.env.user.has_group('dealer.group_dealer_user'))    

    @api.depends('product_id')
    def _compute_capacity(self):
        Size = self.env['product.size']
        for record in self:
            record.size_id = False
            if record.product_id and record.product_id.name:
                text = record.product_id.name
                match = re.search(r'\b\d+[A-Z]\b', text)
                if match:
                    capacity_str = match.group()
                    # Search for existing size
                    size_rec = Size.search([('capacity', '=', capacity_str)], limit=1)
                    if not size_rec:
                        # Create with mandatory 'code' field
                        size_rec = Size.create({
                            'code': capacity_str,
                            'capacity': capacity_str,
                        })
                    record.size_id = size_rec.id

    dealer_mobile_user_bool = fields.Boolean(string="dealer Mobile User",default=_default_dealer_mobile_user_bool)

    dealer_access_bool = fields.Boolean(string ="dealer_access_bool",compute="_compute_dealer_access_bool",default=False)

   
    
        # Helper field to control readonly
    # product_category_readonly = fields.Boolean(
    #     string="Product Category Readonly",
    #     compute="_compute_product_category_readonly"
    # )

    # @api.depends('dealer_mobile_user_bool')
    # def _compute_product_category_readonly(self):
    #     for rec in self:
    #         rec.product_category_readonly = rec.dealer_mobile_user_bool

    @api.depends('dealer_mobile_user_bool')
    def _compute_dealer_access_bool(self):
        for rec in self:
            rec.dealer_access_bool = bool(rec.dealer_mobile_user_bool)
            

    @api.onchange('dealer_mobile_user_bool')
    def _onchange_dealer_mobile_user_bool(self):
        for rec in self:
            if not rec.dealer_mobile_user_bool:
                rec.dealer_access_bool = False
                rec.dealer_id = False
                rec.dealer_showroom_id = False
                rec.dealer_assignment_id = False
                rec.product_category_id = False
                return             
                # print("/.///////////////// rec.dealer_access_bool//", rec.dealer_access_bool,rec.dealer_mobile_user_bool)
            dealer_assignment = self.env['dsales.assignment'].search( 
            [('sale_dealer_id', '=', self.env.user.id)], limit=1 ) 
            if dealer_assignment:
                rec.dealer_id = dealer_assignment.dealer_id.id
                rec.dealer_showroom_id = dealer_assignment.dealer_showroom_id.id
                rec.dealer_assignment_id = dealer_assignment.id
                rec.product_category_id = dealer_assignment.category_id.id
                # Make field readonly for mobile users
                # rec._fields['product_category_id'].readonly = True
                # print("...........dealer_assignment........",dealer_assignment.dealer_id.name ,rec._fields['product_category_id'].readonly)
           


    # @api.constrains('qty')
    # def _check_qty_positive(self):
    #     for rec in self:
    #         if rec.qty <= 0:
    #             raise ValidationError("Quantity must be greater than zero.")

    user_id = fields.Many2one(
    'res.users',
    string='Salesman',
    readonly=True,
    )

    city_id = fields.Many2one(
        'res.city', 
        string="City", 
        compute="_compute_location_fields", 
        store=True, 
        readonly=True
    )

    district_id = fields.Many2one(
        'res.state.district', 
        string="District", 
        compute="_compute_location_fields", 
        store=True, 
        readonly=True
    )

    region_id = fields.Many2one(
        'res.region', 
        string="Region", 
        compute="_compute_location_fields", 
        store=True, 
        readonly=True
    )
    
    work_center_location_id  = fields.Many2one('work.center.location',string = "Work Center", compute = "_compute_location_fields",store = True)

    current_latitude = fields.Float(string="Current Latitude")
    current_longitude = fields.Float(string="Current Longitude")

    fsm_loyalty_points = fields.Float("Loyalty Points", compute='_compute_fsm_loyalty_points', store=True)

    applied_multiplier = fields.Float(
        string="Applied Multiplier",
        compute="_compute_applied_multiplier",
        store=True,
        help="The final multiplier applied to loyalty points for this invoice."
    )

    @api.depends('dealer_id', 'line_ids.qty', 'date_time')
    def _compute_applied_multiplier(self):
        for rec in self:
            raw_multiplier = rec._get_raw_multiplier()
            total_qty = sum(abs(line.qty) for line in rec.line_ids) if rec.line_ids else abs(rec.qty or 0)
            rec.applied_multiplier = total_qty * raw_multiplier

    def _get_raw_multiplier(self):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        
        from odoo.fields import Date as FieldDate
        def _parse_date(val):
            if val and val != 'False':
                try:
                    return FieldDate.to_date(val)
                except Exception:
                    return False
            return False

        current_date = (self.date_time or fields.Datetime.now()).date()

        # Step 1 & 2: Identify promotion type (Dealer vs General)
        is_dealer = False
        if self.dealer_id:
            is_cust = getattr(self.dealer_id, 'partner_type_hhs', False) == 'customer'
            is_sub_dealer = getattr(self.dealer_id, 'sub_partner_type', False) == 'dealer'
            is_req = getattr(self.dealer_id, 'dealersalesman_required', False)
            if is_cust and is_sub_dealer and is_req:
                is_dealer = True

        if is_dealer:
            dealer_required = params.get_param('dealer.dealer_promotion_multiplier_required')
            if dealer_required and dealer_required != 'False':
                from_date = _parse_date(params.get_param('dealer.dealer_promotion_from_date', ''))
                to_date = _parse_date(params.get_param('dealer.dealer_promotion_to_date', ''))
                
                # Step 1: Check promotion validity date
                valid_date = True
                if from_date and current_date < from_date:
                    valid_date = False
                if to_date and current_date > to_date:
                    valid_date = False
                
                if valid_date:
                    min_qty = float(params.get_param('dealer.dealer_promotion_minimum_quantity', default=0.0))
                    total_qty = sum(abs(line.qty) for line in self.line_ids) if self.line_ids else abs(self.qty or 0)
                    
                    # Grant promotion if minimum quantity is met
                    if total_qty >= min_qty:
                        return float(params.get_param('dealer.dealer_promotion_multiplier_value', default=1.0))

        # Check General Multiplier
        gen_required = params.get_param('dealer.general_promotion_multiplier_required')
        if gen_required and gen_required != 'False':
            from_date = _parse_date(params.get_param('dealer.general_promotion_from_date', ''))
            to_date = _parse_date(params.get_param('dealer.general_promotion_to_date', ''))
            
            # Step 1: Check promotion validity date
            valid_date = True
            if from_date and current_date < from_date:
                valid_date = False
            if to_date and current_date > to_date:
                valid_date = False
            
            if valid_date:
                # Grant promotion as long as the date is valid
                return float(params.get_param('dealer.general_promotion_multiplier_value', default=1.0))
                
        return 1.0

    @api.depends('product_id', 'qty', 'is_sales_return', 'line_ids.qty', 'dealer_id')
    def _compute_fsm_loyalty_points(self):
        for rec in self:
            if rec.product_id and rec.qty:
                multiplier = rec._get_applicable_multiplier()
                qty = abs(rec.qty)
                points = qty * rec.product_id.fsm_loyalty_points * multiplier
                if rec.is_sales_return:
                    rec.fsm_loyalty_points = -1 * points
                else:
                    rec.fsm_loyalty_points = points
            else:
                rec.fsm_loyalty_points = 0.0


    @api.constrains("current_latitude", "current_longitude", "dealer_showroom_id", "city_id", "district_id")
    def _check_geo_location(self):
        """Validate dealer's location against showroom coordinates."""
        # Skip geo-validation for back-office users
        if not self.env.user.has_group("dealer.group_dealer_user"):
            return

        validate_geo = self.env["ir.config_parameter"].sudo().get_param("dealer.validate_geo_location")
        if not validate_geo or validate_geo == "False":
            return  # switch off validation if param disabled

        for rec in self:
            # Get dealer coordinates (from record or user)
            user_lat = rec.current_latitude or self.env.user.current_latitude
            user_lon = rec.current_longitude or self.env.user.current_longitude

            if not user_lat or not user_lon:
                raise ValidationError("Cannot validate location: dealer coordinates missing.")
            if not rec.dealer_showroom_id  or not rec.dealer_showroom_id .latitude or not rec.dealer_showroom_id .longitude:
                raise ValidationError("Cannot validate location: Showroom coordinates missing.")
            if not rec.city_id:
                raise ValidationError("Geo-location validation failed: missing city for showroom.")

            # Compute haversine distance
            distance = haversine(user_lat, user_lon, rec.dealer_showroom_id .latitude, rec.dealer_showroom_id .longitude)

            wfo_radius = int(
            self.env['ir.config_parameter'].sudo().get_param('dealer.dealer_wfo_radius', default=0)
            )
            
            # Reject if outside 100m radius
            if distance > wfo_radius:
                raise ValidationError(
                    _("You cannot enter sales. You are not in a valid location (distance %.2f m).") % distance
                )



    @api.depends('dealer_showroom_id')
    def _compute_location_fields(self):
        for rec in self:
            if rec.dealer_showroom_id:
                rec.city_id = rec.dealer_showroom_id.city.id if rec.dealer_showroom_id.city else False
                rec.district_id = rec.dealer_showroom_id.district.id if rec.dealer_showroom_id.district else False
                rec.region_id = rec.dealer_showroom_id.region_id.id if rec.dealer_showroom_id.region_id else False
                rec.work_center_location_id = rec.dealer_showroom_id.city.def_work_center_id.id if rec.dealer_showroom_id.city else False
            else:
                rec.city_id = False
                rec.district_id = False
                rec.region_id = False
                rec.work_center_location_id = False


    @api.onchange('dealer_assignment_id')
    def _onchange_available_user(self):
        for rec in self:
            if rec.dealer_assignment_id:
                print("rec.dealer_id.dealer_id.user_id.id", rec.dealer_assignment_id.sale_dealer_id.id)
                rec.user_id = rec.dealer_assignment_id.sale_dealer_id.id    

    def copy(self, default=None):
        # Prevent record duplication
        raise models.ValidationError("Duplicate option is disabled for this model.")

    # @api.model
    # def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
    #     user = self.env.user      
    #     if (user.has_group('dealer.group_dealer_user')):
    #         domain += [
    #              ('dealer_id', '=', user.dealer_id.id),('showroom','=',user.dealer_showroom_id.id)
    #         ]
    #         return super(dealerShowroomSales, self).search_fetch(domain, field_names, offset, limit, order)        
        
    #     return super(dealerShowroomSales, self).search_fetch(domain, field_names, offset, limit, order)


    @api.model
    def create(self, vals):
        """Create sales entry and update related sales.target (with checkout restriction)."""
        # Today's date (server / Odoo UTC)
        today = fields.Datetime.now().date()
        # Debug info
        server_dt = datetime.now()
        utc_dt = datetime.now(timezone.utc)
        odoo_now = fields.Datetime.now()
        _logger.info("🕒 Server local datetime: %s", server_dt)
        _logger.info("🕒 Explicit UTC datetime: %s", utc_dt)
        _logger.info("🕒 Odoo fields.Datetime.now(): %s", odoo_now)

        # Only enforce for mobile dealer users
        if self.env.user.has_group("dealer.group_dealer_user"):

            # Must have date_time in vals to validate
            if not vals.get("date_time"):
                raise ValidationError(_("date_time is required for dealer sales."))

            # Full datetime object of the record being created
            try:
                record_dt = fields.Datetime.to_datetime(vals["date_time"])
            except Exception:
                raise ValidationError(_("Invalid date_time format."))

            record_date = record_dt.date()

            
            _logger.info("📌 CREATE check -> Today (UTC): %s | Record date: %s", today, record_date)

            # Rule: Only allow today's date
            if record_date != today:
                raise ValidationError(
                    _("Hi %s, you can only create sales entries for today (%s).") %
                    (self.env.user.name, today)
                )

        # If we have assignment_id, check the dealer's attendance for today
        if vals.get("dealer_assignment_id"):
            assignment = self.env["dsales.assignment"].browse(vals["dealer_assignment_id"])
            dealer_user = assignment.sale_dealer_id
            if not dealer_user:
                raise ValidationError(_("Invalid assignment / dealer for this sales entry."))
                # employee = dealer_user.employee_id
                # if not employee:
                #     raise ValidationError(
                #         _("No employee record linked to dealer user %s.") % dealer_user.name
                #     )

                # Build start_of_day and end_of_day for today (UTC/server)
            start_of_day = datetime.combine(today, time.min)
            end_of_day = datetime.combine(today, time.max)
            start_str = fields.Datetime.to_string(start_of_day)
            end_str = fields.Datetime.to_string(end_of_day)

            # attendance = self.env["hr.attendance"].search([
            #     ("employee_id", "=", employee.id),
            #     ("check_in", ">=", start_str),
            #     ("check_in", "<=", end_str),
            # ], order="check_in desc", limit=1)

            # # Log found attendance for debugging
            # if attendance:
            #     _logger.info("🧾 Found attendance for %s (Employee %s): check_in=%s check_out=%s",
            #                 dealer_user.name, employee.name, attendance.check_in, attendance.check_out)
            # else:
            #     _logger.info("🧾 No attendance found for dealer %s (Employee %s) today",
            #                 dealer_user.name, employee.name)

            # # If today's attendance exists and has check_out set -> block creation
            # if attendance and attendance.check_out:
            #     checkout_plus_3 = attendance.check_out + timedelta(hours=3)
            #     raise ValidationError(
            #         _("You cannot create sales after checkout at %s.") % checkout_plus_3
            #     )

            # else:
            #     raise ValidationError(_("Invalid assignment / dealer for this sales entry."))

        # proceed with normal creation and target update
        record = super(dealerShowroomSales, self).create(vals)
        self._update_target_on_create(record, create_if_missing=True)
        # -------------------------------------------------
        # FSM LOYALTY AUDIT CREATION
        # -------------------------------------------------
        for line in record.line_ids:
            if line.product_id and line.qty:
                loyalty_points = line.fsm_loyalty_points
                trans_type = '2' if record.is_sales_return else '1'

                salesman_id = (
                    record.dealer_assignment_id.sale_dealer_id.id
                    if record.dealer_assignment_id and record.dealer_assignment_id.sale_dealer_id
                    else self.env.user.id
                )

                if not record.dealer_id:
                    raise ValidationError(_("Dealer is required for Loyalty Audit."))

                self.env['fsm.loyalty.audit'].create({
                    'date_time': record.date_time or fields.Datetime.now(),
                    'dealer_id': record.dealer_id.id,
                    'salesman_id': salesman_id,
                    'location_id': record.dealer_showroom_id.id if record.dealer_showroom_id else False,
                    'type': trans_type,
                    'qty': line.qty,
                    'loyalty_points': loyalty_points,
                    'amount_paid': 0,
                    'reference': record.invoice_no or self.env['ir.sequence'].next_by_code('dsales.showroom.sales'),
                    'notes': record.notes,
                })

                # except Exception as e:
                #     _logger.error("FSM Loyalty Audit creation failed: %s", str(e))

        return record

    def write(self, vals):
        """Update sales records and adjust related sales.target quantities."""
        today = fields.Datetime.now().date()  # ✅ server UTC date
        # Debug info
        server_dt = datetime.now()
        utc_dt = datetime.now(timezone.utc)
        odoo_now = fields.Datetime.now()

        _logger.info("🕒 Server local datetime: %s", server_dt)
        _logger.info("🕒 Explicit UTC datetime: %s", utc_dt)
        _logger.info("🕒 Odoo fields.Datetime.now(): %s", odoo_now)

        # Restrict dealer users to modify only today's records (server UTC only)
        if self.env.user.has_group("dealer.group_dealer_user"):
           
            for record in self:
                # Default check: use record.date_time unless new date_time in vals
                record_date = record.date_time.date() if record.date_time else None
                if "date_time" in vals:
                    record_date = fields.Datetime.to_datetime(vals["date_time"]).date()

                _logger.info("📌 WRITE check -> Today (UTC): %s | Record date: %s", today, record_date)

                if record_date and record_date != today:
                    raise ValidationError(
                        f"Hi {self.env.user.name}, you can only update today's sales entries ({today})."
                    )

                # Check hr.attendance for checkout
                if record.dealer_assignment_id and record.dealer_assignment_id.dealer_id:
                    attendance = self.env['hr.attendance'].search([
                        ('employee_id', '=', record.dealer_assignment_id.dealer_id.id),
                        ('check_in', '<=', record_date),
                    ], order='check_in desc', limit=1)
                    if attendance and attendance.check_out and record_date > attendance.check_out:
                        raise ValidationError(
                            _("You cannot update sales after checkout (%s).") % attendance.check_out
                        )

        target_obj = self.env['dealer.sales.target']
        old_data = []

        # Save old target keys and quantities
        for record in self:
            for line in record.line_ids:
                old_data.append({
                    'record': record,
                    'line': line,
                    'key': self._get_target_key(record, line),
                    'qty': int(line.qty or 0),
                })
            # Also keep old header qty in case old records without lines are edited
            if record.qty:
                old_data.append({
                    'record': record,
                    'line': None,
                    'key': self._get_target_key(record),
                    'qty': int(record.qty),
                })

        res = super().write(vals)

        for data in old_data:
            record = data['record']
            old_key = data['key']
            old_qty = data['qty']
            line = data.get('line')

            # Subtract old quantity from old target
            old_target = target_obj.search(old_key, limit=1)
            if old_target:
                old_target.actual_qty = max(0, old_target.actual_qty - old_qty)

        # After super().write, process new quantities.
        for record in self:
            for line in record.line_ids:
                new_key = self._get_target_key(record, line)
                new_qty = int(line.qty or 0)
                new_target = target_obj.search(new_key, limit=1)

                if new_target:
                    new_target.actual_qty += new_qty
                else:
                    self._create_target(record, line)
            
            if record.qty:
                new_key = self._get_target_key(record)
                new_qty = int(record.qty or 0)
                new_target = target_obj.search(new_key, limit=1)
                if new_target:
                    new_target.actual_qty += new_qty
                else:
                    self._create_target(record)

        return res

    def unlink(self):
        """Allow dealer (mobile) users to delete only today's records.
        Always adjust related sales.target actual_qty before deletion.
        """
        target_obj = self.env['dealer.sales.target']
        today = date.today()  # or datetime.now(timezone.utc).date()

        for record in self:
            # Mobile users can delete only today's records
            if self.env.user.has_group("dealer.group_dealer_user"):
                record_date = record.date_time.date() if record.date_time else None
                if record_date != today:
                    raise ValidationError(
                        f"Hi {self.env.user.name}, you can only delete today's records ({today})."
                    )

            # Adjust actual_qty before deleting
            for line in record.line_ids:
                old_qty = int(line.qty or 0)
                if old_qty:
                    target_domain = record._get_target_key(record, line)
                    old_target = target_obj.search(target_domain, limit=1)
                    if old_target:
                        old_target.actual_qty = max(0, old_target.actual_qty - old_qty)
            if record.qty:
                old_qty = int(record.qty)
                target_domain = record._get_target_key(record)
                old_target = target_obj.search(target_domain, limit=1)
                if old_target:
                    old_target.actual_qty = max(0, old_target.actual_qty - old_qty)

        return super().unlink()


    def _get_target_key(self, record, line=None):
        """Returns the search domain for the corresponding sales.target record."""
        
        # Helper to safely get related field
        def safe(field, default=False):
            return getattr(field, 'id', default) if hasattr(field, 'id') else default

        # Extract year/month from date_time or fallback to today
        record_dt = fields.Datetime.to_datetime(record.date_time) if record.date_time else fields.Datetime.context_timestamp(record, fields.Datetime.now())
        year_str = str(record_dt.year)
        month_str = str(record_dt.month).zfill(2)

        return [
            ('region', '=', record.region_id.with_context(lang='en_US').name if record.region_id else False),
            ('city', '=', record.city_id.with_context(lang='en_US').name if record.city_id else False),
            ('dealer_id', '=', safe(record.dealer_id)),
            ('dealer_showroom_id', '=', safe(record.dealer_showroom_id)),
            ('sale_dealer_id', '=', record.dealer_assignment_id.sale_dealer_id.id if record.dealer_assignment_id and record.dealer_assignment_id.sale_dealer_id else False),
            ('franchise_id', '=', line.product_category_id.id if line and line.product_category_id else (record.product_category_id.id if record.product_category_id else False)),
            ('group_id', '=', safe(line.product_group_id) if line else safe(record.group_id)),
            ('subgroup_id', '=', safe(line.product_subgroup_id) if line else safe(record.subgroup_id)),
            ('year', '=', year_str),
            ('month', '=', month_str),
        ]

    def _update_target_on_create(self, record, create_if_missing=True):
        """
        Update sales.target when a sales record is created.
        """
        target_obj = self.env['dealer.sales.target']
        lines_to_process = record.line_ids if record.line_ids else [None]
        for line in lines_to_process:
            if not line and not record.qty:
                continue
            key = self._get_target_key(record, line)
            qty = int(line.qty or 0) if line else int(record.qty or 0)

            target_record = target_obj.search(key, limit=1)
            if target_record:
                target_record.actual_qty += qty
            elif create_if_missing:
                self._create_target(record, line)

    def _create_target(self, record, line=None):
        """Create a new sales.target record from a sales record."""
        
        # Helper to safely get id or fallback
        def safe_id(field):
            return getattr(field, 'id', False) if field else False

        # Extract dealer info
        salesman = record.dealer_assignment_id.sale_dealer_id if record.dealer_assignment_id else None
        # user = dealer.user_id if dealer else None
        sale_dealer_id = safe_id(salesman)
        salesman_code = f"pr_{getattr(salesman, 'user_code', '')}" if salesman else ""
        salesman_name = salesman.name if salesman else ""

        # Extract franchise info
        franchise = line.product_category_id if line else record.product_category_id
        franchise_id = safe_id(franchise)
        franchise_code = getattr(franchise, 'code', "")
        franchise_name = getattr(franchise, 'name', "")
        capacity = line.capacity if line else (record.size_id.display_name if record.size_id else False)
        actual_qty = int(line.qty or 0) if line else int(record.qty or 0)
        group_id = safe_id(line.product_group_id) if line else safe_id(record.group_id)
        subgroup_id = safe_id(line.product_subgroup_id) if line else safe_id(record.subgroup_id)

        # Extract region/city/showroom
        region_name = record.region_id.with_context(lang='en_US').name if record.region_id else ""
        city_name = record.city_id.with_context(lang='en_US').name if record.city_id else ""
        showroom_id = safe_id(record.dealer_showroom_id)

        # Year/Month from date_time
        dt = fields.Datetime.to_datetime(record.date_time) if record.date_time else fields.Datetime.context_timestamp(record, fields.Datetime.now())
        year_str = str(dt.year)
        month_str = str(dt.month).zfill(2)

        vals = {
            'region': region_name,
            'city': city_name,
            'dealer_id': safe_id(record.dealer_id),
            'dealer_showroom_id': showroom_id,
            'sale_dealer_id': sale_dealer_id,
            'franchise_id': franchise_id,
            'group_id': group_id,
            'subgroup_id': subgroup_id,
            'year': year_str,
            'month': month_str,
            'target_qty': 0,
            'actual_qty': actual_qty,
            'capacity': capacity,
            'franchise_code': franchise_code,
            'franchise_name': franchise_name,
            'salesman_code': salesman_code,
            'salesman_name': salesman_name,
        }

        _logger.info("Creating sales.target with values: %s", vals)
        return self.env['dealer.sales.target'].create(vals)


    @api.constrains("date_time")
    def _check_date_today_mobile_users(self):
        for rec in self:
            # Only check if the logged-in user is in the Mobile User group
            if self.env.user.has_group("dealer.group_dealer_user"):
                if rec.date_time:
                    today = fields.Date.context_today(self)
                    record_date = rec.date_time.date()  # convert datetime → date
                    if record_date != today:
                        raise ValidationError(
                            f"Hi {rec.user_id.name}, you can only edit sales entries for today."
                        )

    @api.constrains('is_sales_return', 'notes', 'line_ids')
    def _check_sales_return(self):
        for record in self:
            if not record.line_ids:
                pass # Or raise error if mandatory, but wait until submission
            for line in record.line_ids:
                if not record.is_sales_return and line.qty <= 0:
                    raise ValidationError("Quantity must be greater than zero.")
                if record.is_sales_return and line.qty >= 0:
                    raise ValidationError("For Sales Return, Quantity must be negative and cannot be zero.")
            if record.is_sales_return and (not record.notes or not record.notes.strip()):
                raise ValidationError("Notes are mandatory for Sales Return.")

    @api.onchange('product_category_id')
    def _onchange_product_category_id(self):
        for rec in self:
            # Clear dependent fields
            rec.group_id = False
            rec.subgroup_id = False
            rec.product_id = False

    @api.onchange('group_id')
    def _onchange_group_id(self):
        for rec in self:
            # Clear dependent fields
            rec.subgroup_id = False
            rec.product_id = False

    @api.onchange('subgroup_id')
    def _onchange_subgroup_id(self):
        for rec in self:
            # Clear dependent fields
            rec.product_id = False

    @api.model
    def default_get(self, fields_list):
        """Override 'New' button behavior to validate current user's location."""
        res = super().default_get(fields_list)

        # Current logged-in user
        user = self.env.user
        user_name = user.name

        # Skip for back-office users
        if not user.has_group("dealer.group_dealer_user"):
            return res

        validate_geo = self.env["ir.config_parameter"].sudo().get_param("dealer.validate_geo_location")
        if not validate_geo or validate_geo == "False":
            return res

        user_lat = user.current_latitude
        user_lon = user.current_longitude

        if not user_lat or not user_lon:
            raise ValidationError(
                _("Cannot validate location for dealer '%s': Coordinates missing.") % user_name
            )

        # Get the assigned showroom for this dealer
        dealer_assignment = self.env['dsales.assignment'].search(
            [('sale_dealer_id', '=', user.id),('active', '=', True)], limit=1
        )
        if not dealer_assignment or not dealer_assignment.dealer_showroom_id:
            raise ValidationError(
                _("Cannot validate location for dealer '%s': No showroom assigned.") % user_name
            )

        showroom = dealer_assignment.dealer_showroom_id

        if not showroom.latitude or not showroom.longitude:
            raise ValidationError(
                _("Cannot validate location for dealer '%s': Showroom coordinates missing.") % user_name
            )
        if not showroom.city:
            raise ValidationError(
                _("Geo-location validation failed for dealer '%s': Missing city for showroom.") % user_name
            )

        # --- SAFE conversion of stored config parameter (handles '7400.86', '7400', None, etc.)
        radius_param = self.env['ir.config_parameter'].sudo().get_param('dealer.dealer_wfo_radius', '0')
        try:
            wfo_radius = int(float(radius_param))
        except (ValueError, TypeError):
            wfo_radius = 0

        # Compute distance
        distance = haversine(user_lat, user_lon, showroom.latitude, showroom.longitude)

        if distance > wfo_radius:
            raise ValidationError(
                _("Hi '%s', you are not in a valid location (distance %.2f m).") % (user_name, distance)
            )

        return res

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        user = self.env.user

        # Check if user has BOTH backoffice AND readonly groups
        has_both_groups = (
                user.has_group('dealer.group_dealer_backoffice_user') and
                user.has_group('dealer.group_dealer_sales_readonly')
        )

        # If user has both groups, restrict write operations
        if has_both_groups and operation in ['write', 'create', 'unlink']:
            if raise_exception:
                raise AccessError(_("You have read-only access to sales records."))
            return False

        return super().check_access_rights(operation, raise_exception)

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        user = self.env.user

        # Full access: dealer_user
        if user.has_group('dealer.group_dealer_user'):
            dealer_id = user.dealer_id.id if user.dealer_id else False
            dealer_showroom_id = user.dealer_showroom_id.id if user.dealer_showroom_id else False

            # Only pass IDs, not recordsets
            domain += [
                ('dealer_id', '=', dealer_id),
                ('dealer_showroom_id', '=', dealer_showroom_id)
            ]
        #code added on DEC 2  by Vijaya Bhaskar    
        # Dealer backoffice user
        elif user.has_group('dealer.group_dealer_backoffice_user'):
            dealer_id = user.dealer_id.id if user.dealer_id else False
            dealer_showroom_id = user.dealer_showroom_id.id if user.dealer_showroom_id else False            
        
            # work_center_ids = user.default_work_center_id.ids if user.default_work_center_id else self.env['work.center.location'].search([]).ids
          
            # domain += [('work_center_location_id','=',work_center_ids)]
            # domain += [
            #     ('dealer_id', '=', dealer_id),
            #     ('dealer_showroom_id', '=', dealer_showroom_id),
            #     ('work_center_location_id', 'in', work_center_ids)
            # ]  

            domain += []
            
        # Readonly: hide all records
        elif user.has_group('dealer.group_dealer_sales_donotshow'):
            return self.browse([])

        return super(dealerShowroomSales, self).search_fetch(
            domain, field_names, offset, limit, order
        )
class DealerShowroomSalesLine(models.Model):
    _name = 'dsales.showroom.sales.line'
    _description = 'Showroom Sales Line'

    sales_id = fields.Many2one('dsales.showroom.sales', string='Sales', required=True, ondelete='cascade')

    product_category_id = fields.Many2one('product.category', string="Product Category", domain="[('parent_id','=',False),('name', '!=', 'All')]")
    product_group_id = fields.Many2one('product.category', string="Product Group", context={'show_only_name': True})
    product_subgroup_id = fields.Many2one('product.category', string="Product Sub Group", context={'show_only_name': True})
    product_id = fields.Many2one('product.product', string="Model")

    product_name = fields.Char(related='product_id.name', string='Name', readonly=True)
    capacity = fields.Char(string='Capacity', compute="_compute_capacity", store=True)
    fsm_loyalty_points = fields.Float("Loyalty Points", compute='_compute_fsm_loyalty_points', store=True)
    qty = fields.Integer(string='Qty', required=True, default=1)

    @api.depends('product_id')
    def _compute_capacity(self):
        for rec in self:
            rec.capacity = False
            if rec.product_id and rec.product_id.name:
                text = rec.product_id.name
                match = re.search(r'\b\d+[A-Z]\b', text)
                if match:
                    rec.capacity = match.group()

    @api.depends('product_id', 'qty', 'sales_id.is_sales_return', 'sales_id.line_ids.qty', 'sales_id.dealer_id')
    def _compute_fsm_loyalty_points(self):
        for rec in self:
            if rec.product_id and rec.qty:
                raw_multiplier = rec.sales_id._get_raw_multiplier() if rec.sales_id else 1.0
                qty = abs(rec.qty)
                points = qty * rec.product_id.fsm_loyalty_points * raw_multiplier
                if rec.sales_id and rec.sales_id.is_sales_return:
                    rec.fsm_loyalty_points = -1 * points
                else:
                    rec.fsm_loyalty_points = points
            else:
                rec.fsm_loyalty_points = 0.0

    @api.onchange('product_category_id')
    def _onchange_product_category_id(self):
        for rec in self:
            rec.product_group_id = False
            rec.product_subgroup_id = False
            rec.product_id = False
            domain = []
            if rec.product_category_id:
                domain = [('parent_id', '=', rec.product_category_id.id)]
            return {'domain': {'product_group_id': domain}}

    @api.onchange('product_group_id')
    def _onchange_product_group_id(self):
        for rec in self:
            rec.product_subgroup_id = False
            rec.product_id = False
            domain = []
            if rec.product_group_id:
                domain = [('parent_id', '=', rec.product_group_id.id)]
            return {'domain': {'product_subgroup_id': domain}}

    @api.onchange('product_subgroup_id')
    def _onchange_product_subgroup_id(self):
        for rec in self:
            rec.product_id = False
            domain = []
            if rec.product_subgroup_id:
                domain.append(('product_tmpl_id.categ_id', 'child_of', rec.product_subgroup_id.id))
            return {'domain': {'product_id': domain}}

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if not rec.product_id or not rec.product_id.categ_id:
                continue
            categ = rec.product_id.categ_id
            if not rec.product_subgroup_id:
                rec.product_subgroup_id = categ
            if not rec.product_group_id and categ.parent_id:
                rec.product_group_id = categ.parent_id
            if not rec.product_category_id and categ.parent_id and categ.parent_id.parent_id:
                rec.product_category_id = categ.parent_id.parent_id
