from odoo import models, fields, api, _
from math import radians, sin, cos, sqrt, atan2
from odoo.exceptions import ValidationError
from datetime import datetime

class PromoterShopStatus(models.Model):
    _name = 'promoter.shop.status'
    _description = 'Review Shop Status'
    _rec_name = 'display_name'
    _order = 'date_time desc'
    _inherit = ['mail.thread', 'mail.activity.mixin'] 

    display_name = fields.Char(compute='_compute_display_name', store=True)

    dealer_id = fields.Many2one(
        'res.partner',
        string='Dealer',
        domain="[('is_dealer', '=', True)]",
        required=True,
        tracking=True
    )

    showroom_id = fields.Many2one(
        'promoter.showroom',
        string='Showroom',
        required=True,
        domain="[('dealer_id', '=', dealer_id)]"
    )

    assignment_id = fields.Many2one(
        'promoter.assignment',
        string='Promoter',
        required=True,
        domain="[('dealer_id', '=', dealer_id), ('showroom_id', '=', showroom)]",
    )

    date_time = fields.Datetime(
        string='Date & Time',
        default=fields.Datetime.now,
        required=True
    )

    priority = fields.Boolean(string='Priority')
    notes = fields.Text(string='Notes',required=True)

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'promoter_shop_status_attachment_rel',
        'status_id',
        'attachment_id',
        string='Attachments',
        default=lambda self: []
    )

    user_id = fields.Many2one(
    'res.users',
    string='Promoter',
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

    @api.depends('showroom_id')
    def _compute_location_fields(self):
        for rec in self:
            if rec.showroom_id:
                rec.city_id = rec.showroom_id.city.id if rec.showroom_id.city else False
                rec.district_id = rec.showroom_id.district.id if rec.showroom_id.district else False
                rec.region_id = rec.showroom_id.region_id.id if rec.showroom_id.region_id else False
            else:
                rec.city_id = False
                rec.district_id = False
                rec.region_id = False

    current_latitude = fields.Float(string="Current Latitude")
    current_longitude = fields.Float(string="Current Longitude")

    @api.constrains('current_latitude', 'current_longitude', 'showroom_id', 'city_id', 'district_id')
    def _check_geo_location(self):
        # Skip geo-validation for back-office users
        if not self.env.user.has_group('promoter.group_promoter_user'):
            return

        validate_geo = self.env['ir.config_parameter'].sudo().get_param("promoter.validate_geo_location")
        if validate_geo and validate_geo != "False":
            for rec in self:
                # Use user's coordinates without assigning
                user_lat = rec.current_latitude or self.env.user.current_latitude
                user_lon = rec.current_longitude or self.env.user.current_longitude

                # Check coordinates exist
                if not user_lat or not user_lon:
                    raise ValidationError("Cannot validate location: Promoter coordinates missing.")
                if not rec.showroom_id or not rec.showroom_id.latitude or not rec.showroom_id.longitude:
                    raise ValidationError("Cannot validate location: Showroom coordinates missing.")

                # Optional: check city/district presence
                if not rec.city_id:
                    raise ValidationError("Geo-location validation failed: missing city for showroom.")

                # Haversine distance check
                R = 6371000
                lat1, lon1 = radians(user_lat), radians(user_lon)
                lat2, lon2 = radians(rec.showroom_id.latitude), radians(rec.showroom_id.longitude)
                dlat, dlon = lat2 - lat1, lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance = R * c

                wfo_radius = int(
                self.env['ir.config_parameter'].sudo().get_param('attendance.wfo_radius', default=100)
                )

                if distance > wfo_radius:
                    raise ValidationError(
                        f"You cannot enter sales. You are not in a valid location (distance {distance:.2f} m)."
                    )

    # @api.model
    # def create(self, vals):
    #     assignment = self.env['promoter.assignment'].browse(vals.get('assignment_id'))
    #     if assignment:
    #         vals['user_id'] = assignment.promoter_id.id
    #     return super().create(vals)
    
    
    @api.model
    def create(self, vals):
        assignment = self.env["promoter.assignment"].browse(vals.get("assignment_id"))
        promoter_name = assignment.promoter_id.name if assignment else self.env.user.name
        if assignment:
            vals["user_id"] = assignment.promoter_id.id

        # Restrict mobile users → only today
        if self.env.user.has_group("promoter.group_promoter_user"):
            today = fields.Date.context_today(self)
            if "date_time" in vals:
                record_date = fields.Datetime.to_datetime(vals["date_time"]).date()
                if record_date != today:
                    raise ValidationError(
                        f"Hi {promoter_name}, you can only create sales entries for today."
                    )

        return super().create(vals)

    def write(self, vals):
        if self.env.user.has_group("promoter.group_promoter_user"):
            today = fields.Date.context_today(self)
            for rec in self:
                if rec.date_time and rec.date_time.date() != today:
                    raise ValidationError(
                        f"Hi {rec.user_id.name}, you can only edit sales entries for today."
                    )
        return super().write(vals)


    def _default_promoter_mobile_user_bool(self): 
        return bool(self.env.user.has_group('promoter.group_promoter_user'))       

    promoter_mobile_user_bool = fields.Boolean(string="Promoter Mobile User",default=_default_promoter_mobile_user_bool)

    promoter_access_bool = fields.Boolean(string ="promoter_access_bool",default=False)

    @api.onchange('promoter_mobile_user_bool')
    def _onchange_promoter_mobile_user_bool(self):
        for rec in self:
            if rec.promoter_mobile_user_bool:
                rec.promoter_access_bool = True
                # if rec.promoter_access_bool:
                print("/.///////////////// rec.promoter_access_bool//", rec.promoter_access_bool,rec.promoter_mobile_user_bool)
                promoter_assignment = self.env['promoter.assignment'].search( 
              [('promoter_id', '=', self.env.user.id)], limit=1 ) 
                rec.dealer_id = promoter_assignment.dealer_id.id
                rec.showroom_id = promoter_assignment.showroom_id.id
                print("...........promoter_assignment........",promoter_assignment.promoter_id.name)
                rec.assignment_id =promoter_assignment.id

    # Compute display name from promoter + showroom + date_time
    @api.depends('assignment_id', 'showroom_id', 'date_time')
    def _compute_display_name(self):
        for rec in self:
            name_parts = []
            if rec.assignment_id:
                name_parts.append(str(rec.assignment_id.name or ''))
            # if rec.showroom_id:
            #     name_parts.append(str(rec.showroom_id.name or ''))
            # if rec.date_time:
            #     name_parts.append(rec.date_time.strftime('%Y-%m-%d %H:%M'))
            rec.display_name = ' | '.join([p for p in name_parts if p]) or 'Shop Status'


    # Constraint 1: Prevent duplicate dealer+showroom+promoter+datetime entries
    @api.constrains('dealer_id', 'showroom_id', 'assignment_id', 'date_time')
    def _check_unique_shop_status(self):
        for record in self:
            domain = [
                ('dealer_id', '=', record.dealer_id.id),
                ('showroom_id', '=', record.showroom_id.id),
                ('assignment_id', '=', record.assignment_id.id),
                ('date_time', '=', record.date_time),
                ('id', '!=', record.id)
            ]
            existing = self.search(domain, limit=1)
            if existing:
                raise ValidationError(
                    "A shop status entry already exists for this Dealer, Showroom, Promoter, and Date & Time."
                ) 
                
    def copy(self, default=None):
        # Prevent record duplication
        raise models.ValidationError("Duplicate option is disabled for this model.")

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        user = self.env.user      
        if (user.has_group('promoter.group_promoter_user')):
            domain += [
                 ('dealer_id', '=', user.dealer_id.id),('showroom_id','=',user.showroom_id.id)
            ]
            # print("-----domain-----------",domain)
            return super(PromoterShopStatus, self).search_fetch(domain, field_names, offset, limit, order)        
        
        return super(PromoterShopStatus, self).search_fetch(domain, field_names, offset, limit, order)