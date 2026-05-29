from odoo import models, api, fields,_
from datetime import datetime, date, time as dt_time
from dateutil.relativedelta import relativedelta
import math
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


# def haversine_distance(lat1, lon1, lat2, lon2):
#     """Return distance in meters between two lat/lon points"""
#     R = 6371000  # Earth radius in meters
#     phi1 = math.radians(lat1)
#     phi2 = math.radians(lat2)
#     dphi = math.radians(lat2 - lat1)
#     dlambda = math.radians(lon2 - lon1)

#     a = (math.sin(dphi / 2) ** 2 +
#          math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
#     c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
#     return R * c

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    _description = 'Review Attendance'

    att_date = fields.Date(string='Date', store=True)

    dealer_id = fields.Many2one(
        'res.partner',
        string='Dealer',
        domain="[('is_dealer', '=', True)]",
        tracking=True
    )

    showroom_id = fields.Many2one('promoter.showroom', string='Showroom')

    promoter_id = fields.Many2one('res.users', string="Promoter")

    promoter_ids = fields.Many2many(
        'res.users',
        string="Promoters",
        compute="_compute_available_pro_ids"
    )

    available_promoter_ids = fields.Many2many(
        'res.users', 
        compute="_compute_available_promoter_ids", 
        string="Available Promoters"
    )

    shift_from = fields.Selection(selection=lambda self: self._get_time_selection(), string="Shift From Time")
    shift_to = fields.Selection(selection=lambda self: self._get_time_selection(), string="Shift To Time")

    def _get_time_selection(self):
        return [(f"{h:02}:{m:02}", f"{h:02}:{m:02}") for h in range(24) for m in (0, 30)]
        

    actual_in = fields.Float(string='Actual In Time', compute='_compute_actual_times', store=True)
    actual_out = fields.Float(string='Actual Out Time', compute='_compute_actual_times', store=True)   

    check_in_time = fields.Char(
    string="Check In",
    compute="_compute_check_in_time",
    store=False
    )

    check_out_time = fields.Char(
        string="Check Out",
        compute="_compute_check_out_time",
        store=False
    )

    city_id = fields.Many2one('res.city', string="City")
    region_id = fields.Many2one('res.region', string="Region")
    district_id = fields.Many2one('res.state.district', string="District")
    
    in_region = fields.Char(string="In Region" )
    out_region = fields.Char(string="Out Region")
    in_district = fields.Char(string="In District")
    out_district = fields.Char(string="Out District")
    showroom_name = fields.Char(string="Showroom Name")

    
    # @api.onchange('employee_id')
    # def _compute_location_names(self):
    #     for rec in self:
    #         print("-----employee_id --",rec.employee_id.name)
    #         print("-----promoter_id --",rec.promoter_id)
    #         if rec.employee_id.user_id:
    #         # if rec.promoter_id:
    #             if rec.employee_id.user_id.partner_id:
    #                 rec.in_city = rec.employee_id.user_id.partner_id.customer_city_id.name or  False
    #                 rec.out_city = rec.employee_id.user_id.partner_id.customer_city_id.name or  False
    #                 rec.in_region = rec.employee_id.user_id.partner_id.customer_city_id.region_id.name or  False
    #                 rec.out_region = rec.employee_id.user_id.partner_id.customer_city_id.region_id.name or  False
    #                 rec.in_district = rec.employee_id.user_id.partner_id.customer_city_id.country_district_id.name or  False
    #                 rec.out_district = rec.employee_id.user_id.partner_id.customer_city_id.country_district_id.name or  False

                   
    #                 # rec.in_city = rec.city_id.name if rec.city_id else False
    #                 # rec.out_city = rec.city_id.name if rec.city_id else False
    #                 # rec.in_region = rec.region_id.name if rec.region_id else False
    #                 # rec.out_region = rec.region_id.name if rec.region_id else False
    #                 # rec.in_district = rec.district_id.name if rec.district_id else False
    #                 # rec.out_district = rec.district_id.name if rec.district_id else False


    def _float_to_time(self, value):
        """Convert float hour (e.g. 9.5) to HH:MM string."""
        if not value:
            return ""
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"

    def _compute_check_in_time(self):
        for rec in self:
            rec.check_in_time = self._float_to_time(rec.actual_in)

    def _compute_check_out_time(self):
        for rec in self:
            rec.check_out_time = self._float_to_time(rec.actual_out)


    @api.depends('check_in')
    def _compute_att_date(self):
        for rec in self:
            if rec.check_in:
                rec.att_date = rec.check_in.date()
            else:
                rec.att_date = False


    # Compute actual float time from check_in/check_out datetime
    @api.depends('check_in', 'check_out')
    def _compute_actual_times(self):
        for rec in self:
            if rec.check_in:
                rec.actual_in = (rec.check_in.hour + 3) + rec.check_in.minute / 60.0
            else:
                rec.actual_in = 0.0

            if rec.check_out:
                rec.actual_out = (rec.check_in.hour + 3) + rec.check_out.minute / 60.0
            else:
                rec.actual_out = 0.0

    # Show only promoters in the "Promoter User" group
    @api.depends('promoter_id')
    def _compute_available_promoter_ids(self):
        group = self.env.ref('promoter.group_promoter_user', raise_if_not_found=False)
        promoters = self.env['res.users'].search([('groups_id', 'in', group.id)]) if group else self.env['res.users']
        for rec in self:
            rec.available_promoter_ids = promoters

    # Show promoters assigned to this showroom
    @api.depends('showroom_id')
    def _compute_available_pro_ids(self):
        for rec in self:
            if rec.showroom_id:
                # Compute promoters
                assignments = self.env['promoter.assignment'].search([])
                rec.promoter_ids = assignments.mapped('promoter_id')
                
                # Compute showroom name
                # rec.showroom_name = rec.showroom_id.name
            else:
                rec.promoter_ids = False
                rec.showroom_name = False


    def _convert_time_to_float(self, time_str):
        try:
            if isinstance(time_str, float):
                return time_str
            if isinstance(time_str, str) and ':' in time_str:
                hours, minutes = map(int, time_str.split(':'))
                return hours + (minutes / 60.0)
        except Exception as e:
            _logger.warning(f"Time conversion error: {time_str} | {e}")
        return 0.0

    def _check_attendance_location(self):
        """Validate user location vs showroom"""
        user = self.env.user
        if not (user.current_latitude and user.current_longitude):
            raise ValidationError(_("Your location could not be detected."))

        showroom = user.showroom_id
        if not (showroom.latitude and showroom.longitude):
            raise ValidationError(_("Showroom location is not configured."))

        distance = haversine_distance(
            user.current_latitude, user.current_longitude,
            showroom.latitude, showroom.longitude,
        )

        # allowed_radius = float(
        # self.env["ir.config_parameter"]
        # .sudo()
        # .get_param("geomarking_attendance_mobile_app_knk.wfo_radius", 100)
        # )

        # if distance > allowed_radius:
        #     raise ValidationError(
        #         _("You are too far from the showroom to check in/out. "
        #         "Distance: %.2f meters (allowed: %.2f m)") % (distance, allowed_radius)
        #     )

        # if distance > 100:
        #     raise ValidationError(
        #         _("You are too far from the showroom to check in/out. "
        #         "Distance: %.2f meters (allowed: 100m)") % distance
        #     )

        return distance

    @api.model
    def create(self, vals):
        user = self.env.user
        _logger.info("CREATE method called in hr.attendance")

        # if self.env.user.has_group("promoter.group_promoter_user"):
        #     print("attendance_action_change")
        #     distance = self._check_attendance_location()

        if not vals.get('promoter_id'):
            vals['promoter_id'] = user.id

        if not vals.get('att_date'):
            vals['att_date'] = fields.Date.context_today(self)

        _logger.info(f"Checking assignment for promoter_id={vals['promoter_id']} and att_date={vals['att_date']}")

        showroom = None
        if vals.get('showroom_id'):
            showroom = self.env['promoter.showroom'].browse(vals['showroom_id'])
            print("promoter.showroom-------", showroom.id)

        assignment = self.env['promoter.assignment'].search([
            ('promoter_id', '=', vals['promoter_id']),
            ('from_date', '<=', vals['att_date']),
            ('to_date', '>=', vals['att_date']),
            ('active', '=', True)
        ], limit=1)

        if assignment:
            _logger.info(f"Assignment found: {assignment}")
            vals.setdefault('dealer_id', assignment.dealer_id.id)
            vals.setdefault('showroom_id', assignment.showroom_id.id)

            if not vals.get('shift_from') and assignment.shift1_from:
                vals['shift_from'] = assignment.shift1_from
            if not vals.get('shift_to') and assignment.shift1_to:
                vals['shift_to'] = assignment.shift1_to

            _logger.info(f"Auto-filled shift_from: {vals['shift_from']}, shift_to: {vals['shift_to']}")

            # if assignment gave us showroom, override "showroom" variable
            showroom = assignment.showroom_id

        else:
            _logger.warning("No assignment found.")

        # ✅ Fetch city/region/district from showroom
        if showroom:
            print(
                "promoter.showroom 1-------",
                showroom.city.id if showroom.city else None,
                showroom.region_id.id if showroom.region_id else None,
                showroom.district.id if showroom.district else None
            )

            vals['city_id'] = showroom.city.id if showroom.city else False
            vals['region_id'] = showroom.region_id.id if showroom.region_id else False
            vals['district_id'] = showroom.district.id if showroom.district else False
            vals['in_city'] = showroom.city.name if showroom.city else False
            vals['out_city'] = showroom.city.name if showroom.city else False
            vals['in_region'] = showroom.region_id.name if showroom.region_id else False
            vals['out_region'] = showroom.region_id.name if showroom.region_id else False

        return super(HrAttendance, self).create(vals)

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        user = self.env.user      
        if (user.has_group('promoter.group_promoter_user')):
            domain += [
                 ('dealer_id', '=', user.dealer_id.id),('showroom_id','=',user.showroom_id.id)
            ]
            return super(HrAttendance, self).search_fetch(domain, field_names, offset, limit, order)        
        
        return super(HrAttendance, self).search_fetch(domain, field_names, offset, limit, order)   

    def write(self, vals):
        if vals.get("employee_id"):
            employee = self.env['hr.employee'].browse(vals["employee_id"])
            if not employee.is_promoter:
                raise ValidationError(_("Only promoters can be marked in Attendance."))
        return super().write(vals)