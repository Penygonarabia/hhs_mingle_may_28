from odoo import models, fields, api, _
from math import radians, sin, cos, sqrt, atan2
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class dealerShopStatus(models.Model):
    _name = 'dsales.shop.status'
    _description = 'Review Shop Status'
    _rec_name = 'display_name'
    _order = 'date_time desc'
    _inherit = ['mail.thread', 'mail.activity.mixin'] 

    display_name = fields.Char(compute='_compute_display_name', store=True)

    dealer_id = fields.Many2one(
        'res.partner',
        string='Dealer',
        domain="[('dealersalesman_required', '=', True)]",
        required=True,
        tracking=True
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

    priority = fields.Boolean(string='Priority')
    notes = fields.Text(string='Notes',required=True)

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'dealer_shop_status_attachment_rel',
        'status_id',
        'attachment_id',
        string='Attachments',
        default=lambda self: []
    )

    user_id = fields.Many2one(
        'res.users',
        string='Mobile User',       
        readonly=True
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


    @api.depends('dealer_showroom_id')
    def _compute_location_fields(self):
        for rec in self:
            if rec.dealer_showroom_id:
                rec.city_id = rec.dealer_showroom_id.city.id if rec.dealer_showroom_id.city else False
                rec.district_id = rec.dealer_showroom_id.district.id if rec.dealer_showroom_id.district else False
                rec.region_id = rec.dealer_showroom_id.region_id.id if rec.dealer_showroom_id.region_id else False
            else:
                rec.city_id = False
                rec.district_id = False
                rec.region_id = False

    current_latitude = fields.Float(string="Current Latitude")
    current_longitude = fields.Float(string="Current Longitude")

    @api.constrains('current_latitude', 'current_longitude', 'dealer_showroom_id', 'city_id', 'district_id')
    def _check_geo_location(self):
        # Skip geo-validation for back-office users
        if not self.env.user.has_group('dealer.group_dealer_user'):
            return

        validate_geo = self.env['ir.config_parameter'].sudo().get_param("dealer.validate_geo_location")
        if validate_geo and validate_geo != "False":
            for rec in self:
                # Use user's coordinates without assigning
                user_lat = rec.current_latitude or self.env.user.current_latitude
                user_lon = rec.current_longitude or self.env.user.current_longitude

                # Check coordinates exist
                if not user_lat or not user_lon:
                    raise ValidationError("Cannot validate location: dealer coordinates missing.")
                if not rec.dealer_showroom_id or not rec.dealer_showroom_id.latitude or not rec.showroom_id.longitude:
                    raise ValidationError("Cannot validate location: Showroom coordinates missing.")

                # Optional: check city/district presence
                if not rec.city_id:
                    raise ValidationError("Geo-location validation failed: missing city for showroom.")

                # Haversine distance check
                R = 6371000
                lat1, lon1 = radians(user_lat), radians(user_lon)
                lat2, lon2 = radians(rec.dealer_showroom_id.latitude), radians(rec.dealer_showroom_id.longitude)
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
    #     assignment = self.env['dsales.assignment'].browse(vals.get('dealer_assignment_id'))
    #     if assignment:
    #         vals['user_id'] = assignment.dealer_id.id
    #     return super().create(vals)
    
    
    # @api.model
    # def create(self, vals):
    #     assignment = self.env["dsales.assignment"].browse(vals.get("dealer_assignment_id"))
    #     dealer_name = assignment.sale_dealer_id.name if assignment else self.env.user.name
        
    #     # ✅ Set user_id from assignment
    #     if assignment and assignment.user_id:
    #         vals['user_id'] = assignment.dealer_id.user_id.id

    #     # Restrict mobile users → only today
    #     if self.env.user.has_group("dealer.group_dealer_user"):
    #         today = fields.Date.context_today(self)
    #         if "date_time" in vals:
    #             record_date = fields.Datetime.to_datetime(vals["date_time"]).date()
    #             if record_date != today:
    #                 raise ValidationError(
    #                     f"Hi {dealer_name}, you can only create sales entries for today."
    #                 )

    #     return super().create(vals)


    @api.model
    def create(self, vals):
        self = self.with_context(mail_create_nosubscribe=True)
        assignment_id = vals.get("dealer_assignment_id")
        assignment = self.env["dsales.assignment"].browse(assignment_id)

        # Determine dealer name for messages
        dealer_name = assignment.dealer_id.name if assignment and assignment.dealer_id else self.env.user.name

        # Debug prints
        # print("===== CREATE START =====")
        # print("Assignment ID:", assignment_id)
        # print("Vals received:", vals)
        # print("Dealer Assignment:", assignment)
        # print("Dealer Name:", dealer_name)

        # Set user_id from dealer assignment if available
        if assignment and assignment.sale_dealer_id:
            vals['user_id'] = assignment.sale_dealer_id.id
        else:
            vals['user_id'] = self.env.user.id

        # Restrict mobile users to only today
        if self.env.user.has_group("dealer.group_dealer_user"):
            today = fields.Date.context_today(self)
            record_date = fields.Datetime.to_datetime(vals.get("date_time")).date() if vals.get("date_time") else today
            # print("Record Date:", record_date, "Today:", today)
            if record_date != today:
                raise ValidationError(
                    _("Hi %s, you can only create sales entries for today.") % dealer_name
                )

        result = super().create(vals)

        # print("Created record ID:", result.id)
        # print("===== CREATE END =====\n")
        _logger.info("Created sales record %s for dealer %s", result.id, dealer_name)

        return result


    def write(self, vals):
        if self.env.user.has_group("dealer.group_dealer_user"):
            today = fields.Date.context_today(self)
            for rec in self:
                if rec.date_time and rec.date_time.date() != today:
                    raise ValidationError(
                        f"Hi {rec.user_id.name}, you can only edit sales entries for today."
                    )
        return super().write(vals)


    def _default_dealer_mobile_user_bool(self): 
        return bool(self.env.user.has_group('dealer.group_dealer_user'))       

    dealer_mobile_user_bool = fields.Boolean(string="dealer Mobile User",default=_default_dealer_mobile_user_bool)

    dealer_access_bool = fields.Boolean(string ="dealer_access_bool",default=False)

    @api.onchange('dealer_mobile_user_bool')
    def _onchange_dealer_mobile_user_bool(self):
        for rec in self:
            if rec.dealer_mobile_user_bool:
                rec.dealer_access_bool = True
                # if rec.dealer_access_bool:
                # print("/.///////////////// rec.dealer_access_bool//", rec.dealer_access_bool,rec.dealer_mobile_user_bool)
                dealer_assignment = self.env['dsales.assignment'].search( 
              [('sale_dealer_id', '=', self.env.user.id)], limit=1 ) 
                rec.dealer_id = dealer_assignment.dealer_id.id
                rec.dealer_showroom_id = dealer_assignment.dealer_showroom_id.id
                # print("...........dealer_assignment........",dealer_assignment.sale_dealer_id.name)
                rec.dealer_assignment_id =dealer_assignment.id

    @api.depends('dealer_assignment_id', 'dealer_showroom_id', 'date_time')
    def _compute_display_name(self):
        for rec in self:  # iterate over multiple records
            name_parts = []
            if rec.dealer_assignment_id:
                name_parts.append(str(rec.dealer_assignment_id.name or ''))
            rec.display_name = ' | '.join([p for p in name_parts if p]) or 'Shop Status' 


    # @api.constrains('dealer_id', 'dealer_showroom_id', 'dealer_assignment_id', 'date_time')
    # def _check_unique_shop_status(self):
    #     for record in self:
    #         if not record.dealer_id or not record.dealer_showroom_id \
    #         or not record.dealer_assignment_id or not record.date_time:
    #             continue

    #         domain = [
    #             ('dealer_id', '=', record.dealer_id.id),
    #             ('dealer_showroom_id', '=', record.dealer_showroom_id.id),
    #             ('dealer_assignment_id', '=', record.dealer_assignment_id.id),
    #             ('date_time', '=', record.date_time),
    #             ('id', '!=', record.id),
    #         ]
    #         print("_check_unique_shop_status ",record.dealer_id.id,record.dealer_showroom_id.id,record.dealer_assignment_id.id,record.date_time)
    #         existing = self.env['dsales.shop.status'].search(domain, limit=1)

    #         if existing:
    #             raise ValidationError(
    #                 "Duplicate shop status entry not allowed."
    #             )

                
    def copy(self, default=None):
        # Prevent record duplication
        raise models.ValidationError("Duplicate option is disabled for this model.")

    # @api.model
    # def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
    #     user = self.env.user

    #     dealer_id = user.dealer_id.id if user.dealer_id else False
    #     dealer_showroom_id = user.dealer_showroom_id.id if user.dealer_showroom_id else False        
    #     if user.has_group('dealer.group_dealer_user'):
    #         domain = [
    #             ('dealer_id', '=', dealer_id),
    #             ('dealer_showroom_id', '=', dealer_showroom_id),
    #         ]

    #     return super().search_fetch(domain, field_names, offset=offset, limit=limit, order=order)