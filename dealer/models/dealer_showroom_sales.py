from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,AccessError
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
    _rec_name = 'name'
    _order = 'date_time desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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

    invoice_id = fields.Many2one('dsales.showroom.invoice', string='Invoice Reference', ondelete='cascade')
    approval_state = fields.Selection(related='invoice_id.state', store=True, string='Approval Status')
    
    calculated_points = fields.Float(string='Calculated Points', compute='_compute_points', store=True)
    multiplier_applied = fields.Float(string='Multiplier Applied', compute='_compute_points', store=True)
    final_points = fields.Float(string='Final Points', compute='_compute_points', store=True)

    @api.depends('qty', 'product_id', 'date_time', 'dealer_id')
    def _compute_points(self):
        params = self.env['ir.config_parameter'].sudo()
        gen_req = params.get_param('dealer.gen_promo_required')
        dealer_req = params.get_param('dealer.dealer_promo_required')
        
        for rec in self:
            calc = (abs(rec.qty) * rec.product_id.fsm_loyalty_points) if (rec.product_id and rec.qty) else 0.0
            if rec.is_sales_return:
                calc = -calc
                
            rec.calculated_points = calc
            multiplier = 1.0
            
            rec_date = rec.date_time.date() if rec.date_time else fields.Date.context_today(self)
            
            # check general
            if gen_req:
                f_date = params.get_param('dealer.gen_promo_from')
                t_date = params.get_param('dealer.gen_promo_to')
                if f_date and t_date and str(rec_date) >= f_date and str(rec_date) <= t_date:
                    val = params.get_param('dealer.gen_promo_multiplier')
                    if val:
                        multiplier *= float(val)
            
            # check dealer
            if dealer_req:
                f_date = params.get_param('dealer.dealer_promo_from')
                t_date = params.get_param('dealer.dealer_promo_to')
                min_qty = int(params.get_param('dealer.dealer_promo_min_qty') or 1)
                if f_date and t_date and str(rec_date) >= f_date and str(rec_date) <= t_date:
                    if abs(rec.qty) >= min_qty:
                        val = params.get_param('dealer.dealer_promo_multiplier')
                        if val:
                            multiplier *= float(val)
                            
            rec.multiplier_applied = multiplier
            rec.final_points = rec.calculated_points * multiplier

    # limits are now checked on the invoice header level


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
                                        
    product_id = fields.Many2one('product.product', string="Model",required=True)
    product_description = fields.Char(related='product_id.name', string='Description', readonly=True)

    @api.onchange('subgroup_id', 'invoice_id')
    def _onchange_product_filtering(self):
        domain = [
            ('show_in_dealer_app', '=', True),
            ('is_outdoor_unit', '=', False),
            ('is_midea_brand', '=', True)
        ]
        if self.subgroup_id:
            domain.append(('product_tmpl_id.categ_id', 'child_of', self.subgroup_id.id))
            
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param('dealer.filter_dealer_purchases') and self.invoice_id and self.invoice_id.dealer_id:
            sales = self.env['sale.order'].search([
                ('partner_id', '=', self.invoice_id.dealer_id.id),
                ('state', 'in', ['sale', 'done'])
            ])
            purchased_products = sales.mapped('order_line.product_id').ids
            if purchased_products:
                domain.append(('id', 'in', purchased_products))
            else:
                domain.append(('id', 'in', []))
                
        return {'domain': {'product_id': domain}}
    

    size_id = fields.Many2one('product.size', string='Capacity', compute="_compute_capacity")
    
    is_sales_return = fields.Boolean(string="Sales Return", help="Enable this option to record a sales return. "
         "This will allow negative quantities, and Notes will be mandatory.")
    qty = fields.Integer(string='Quantity',required=True)
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

    # Attachment moved to header

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


    @api.depends('product_id', 'qty', 'is_sales_return')
    def _compute_fsm_loyalty_points(self):
        for rec in self:
            if rec.product_id and rec.qty:
                qty = abs(rec.qty)
                if rec.is_sales_return:
                    rec.fsm_loyalty_points = -1 * qty * rec.product_id.fsm_loyalty_points
                else:
                    rec.fsm_loyalty_points = qty * rec.product_id.fsm_loyalty_points


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
        if record.product_id and record.qty:

            # Always control sign safely
            base_points = record.qty * record.product_id.fsm_loyalty_points
            loyalty_points = -abs(base_points) if record.is_sales_return else abs(base_points)
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
                'qty': record.qty,
                'loyalty_points': record.final_points if record.final_points else loyalty_points,
                'amount_paid': 0,
                'reference': self.env['ir.sequence'].next_by_code('dsales.showroom.sales'),
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
            old_data.append({
                'record': record,
                'key': self._get_target_key(record),
                'qty': int(record.qty or 0),
            })

        res = super().write(vals)

        for data in old_data:
            record = data['record']
            old_key = data['key']
            old_qty = data['qty']

            # Subtract old quantity from old target
            old_target = target_obj.search(old_key, limit=1)
            if old_target:
                old_target.actual_qty = max(0, old_target.actual_qty - old_qty)

            # Add new quantity to new target
            new_key = self._get_target_key(record)
            new_qty = int(record.qty or 0)
            new_target = target_obj.search(new_key, limit=1)

            # ✅ Allow both mobile & back-office to create if missing
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
            old_qty = int(record.qty or 0)
            if old_qty:
                target_domain = record._get_target_key(record)
                old_target = target_obj.search(target_domain, limit=1)
                if old_target:
                    old_target.actual_qty = max(0, old_target.actual_qty - old_qty)
                    _logger.info(
                        "Sales target %s adjusted: -%s (new actual_qty=%s)",
                        old_target.id, old_qty, old_target.actual_qty
                    )
                else:
                    _logger.warning(
                        "No matching sales.target found for record %s with key %s",
                        record.id, target_domain
                    )

        return super().unlink()


    def _get_target_key(self, record):
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
            ('franchise_id', '=', record.product_category_id.id if record.product_category_id else False),
            ('group_id', '=', safe(record.group_id)),
            ('subgroup_id', '=', safe(record.subgroup_id)),
            ('year', '=', year_str),
            ('month', '=', month_str),
        ]

    def _update_target_on_create(self, record, create_if_missing=True):
        """
        Update sales.target when a sales record is created.
        - If target exists: increment actual_qty
        - If not exists:
            * Back-office: create a new one
            * Mobile: skip creation (only update allowed)
        """
        target_obj = self.env['dealer.sales.target']
        key = self._get_target_key(record)
        qty = int(record.qty or 0)

        target_record = target_obj.search(key, limit=1)
        if target_record:
            _logger.info(
                "Updating sales.target ID %s | Old actual_qty=%s | Adding qty=%s | New actual_qty=%s",
                target_record.id, target_record.actual_qty, qty, target_record.actual_qty + qty
            )
            target_record.actual_qty += qty
        elif create_if_missing:
            _logger.info("No sales.target found → Creating new one")
            self._create_target(record)
        else:
            _logger.warning(
                "Mobile user tried to create sales.target → skipped | key=%s | qty=%s",
                key, qty
            )

    def _create_target(self, record):
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
        franchise = record.product_category_id
        franchise_id = safe_id(franchise)
        franchise_code = getattr(franchise, 'code', "")
        franchise_name = getattr(franchise, 'name', "")
        capacity = record.size_id.display_name if record.size_id else False

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
            'group_id': safe_id(record.group_id),
            'subgroup_id': safe_id(record.subgroup_id),
            'year': year_str,
            'month': month_str,
            'target_qty': 0,
            'actual_qty': int(record.qty or 0),
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

    @api.constrains('qty', 'is_sales_return', 'notes')
    def _check_sales_return(self):
        for line in self:
            # Rule 1: For normal sales (not a return) → qty must be > 0
            if not line.is_sales_return and line.qty <= 0:
                raise ValidationError("Quantity must be greater than zero.")

            # Rule 2: For sales return → notes must be provided
            if line.is_sales_return and (not line.notes or not line.notes.strip()):
                raise ValidationError("Notes are mandatory for Sales Return.")
             # Rule 3: Quantity cannot be zero
            if line.is_sales_return and line.qty >= 0:
                raise ValidationError("For Sales Return, Quantity must be negative and cannot be zero.")

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