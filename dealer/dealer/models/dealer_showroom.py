import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,AccessError
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import requests
from urllib.parse import urlparse, parse_qs, unquote
import logging

_logger = logging.getLogger(__name__)

class dealerShowroom(models.Model):
    _name = 'dsales.showroom'
    _description = 'Dealer Showrooms'
    _order = 'dealer_id,region_id,city,district,name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    dealer_showroom_code = fields.Char(
        string="Dealer Showroom Code",
        required=True,
        index=True,
        tracking=True,
        help="Unique code for the showroom (e.g., E001-JS1)"
    )

    name = fields.Char(string="Dealer Showroom", required=True, tracking=True)
    address = fields.Text(string="Address")
    city = fields.Many2one('res.city', string="City")
    district = fields.Many2one('res.state.district', string="District")     
    region_id = fields.Many2one('res.region', string="Region")
    contact_no = fields.Char(string="Contact No")
    email = fields.Char(string="Email")
    google_maps_url = fields.Char("Google Maps URL")
    latitude = fields.Float(string="Latitude", digits=(10, 6))
    longitude = fields.Float(string="Longitude", digits=(10, 6))

    sale_dealer_required = fields.Boolean(string="Dealer Salesman Required")
    sale_dealer_id = fields.Many2one('res.users', string="Dealer Salesman", readonly=True)
    user_id = fields.Many2one('res.users', string='Mobile User')
    from_date = fields.Date(string="From Date", readonly=True)
    to_date = fields.Date(string="To Date", readonly=True)

    shift1_from = fields.Selection(selection='_get_time_slots', string="Shift-1 From Time", readonly=True)
    shift1_to = fields.Selection(selection='_get_time_slots', string="Shift-1 To Time", readonly=True)
    shift2_from = fields.Selection(selection='_get_time_slots', string="Shift-2 From Time", readonly=True)
    shift2_to = fields.Selection(selection='_get_time_slots', string="Shift-2 To Time", readonly=True)

    dealer_id = fields.Many2one('res.partner', string="Dealer", required=True)
    work_email = fields.Char(related="dealer_id.email", store=True, readonly=False)
    mobile = fields.Char(related="dealer_id.mobile", store=True, readonly=False)
    # gender = fields.Selection(related="dealer_id.gender", store=True, readonly=False)
    

    @api.model
    def _get_time_slots(self):
        times = []
        for hour in range(0, 24):
            for minute in (0, 30):
                time_str = f"{hour:02}:{minute:02}"
                times.append((time_str, time_str))
        return times

    @api.constrains('contact_no', 'email')
    def _check_contact_email(self):
        for rec in self:
            if rec.contact_no and not re.match(r'^\+?\d{10,15}$', rec.contact_no):
                raise ValidationError("Contact No must be 10 to 15 digits (can start with +).")
            if rec.email and not re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,4}$", rec.email):
                raise ValidationError("Invalid Email format.")

    @api.onchange('city')
    def _onchange_city(self):
        if self.city:
            district_search_id = self.env['res.state.district'].search([('city_id','=',self.city.id)],limit=1)
            self.district = district_search_id
            self.region_id = self.city.region_id
        else:
            # self.district = False
            self.region_id = False


    @api.onchange('address')
    def _onchange_address(self):
        """Update latitude and longitude when address changes."""
        geolocator = Nominatim(user_agent="odoo_geocoder")
        for record in self:
            if record.address:
                try:
                    # Geocode the address
                    location = geolocator.geocode(record.address)
                    print("location", location)
                    if location:
                        record.latitude = str(location.latitude)
                        record.longitude = str(location.longitude)
                    else:
                        record.latitude = False
                        record.longitude = False
                        print("Raj")
                except (GeocoderTimedOut, GeocoderServiceError) as e:
                    # Handle errors silently or notify user
                    record.latitude = False
                    record.longitude = False
                    # Optional: Notify user of error
                    return {
                        'warning': {
                            'title': "Geocoding Error",
                            'message': f"Could not geocode address: {str(e)}"
                        }
                    }
            else:
                record.latitude = False
                record.longitude = False

    def extract_lat_long(self, google_maps_url):
        """
        Extract latitude and longitude from Google Maps URLs.
        Handles shortened maps.app.goo.gl links by resolving redirects.
        """
        try:
            if not google_maps_url:
                return None, None

            # Handle short URLs by resolving redirects
            if "goo.gl" in google_maps_url:
                try:
                    response = requests.head(google_maps_url, allow_redirects=True, timeout=5)
                    google_maps_url = response.url
                except Exception:
                    return None, None

            parsed_url = urlparse(google_maps_url)
            query_params = parse_qs(parsed_url.query)

            # Format 1: ?q=lat,lng
            if 'q' in query_params:
                coords = unquote(query_params['q'][0]).split(',')
                if len(coords) == 2:
                    return coords[0].strip(), coords[1].strip()

            # Format 2: /@lat,lng,...
            if '/@' in parsed_url.path:
                at_part = parsed_url.path.split('/@')[1]
                coords = at_part.split(',')[:2]
                if len(coords) == 2:
                    return coords[0].strip(), coords[1].strip()

            # Format 3: /place/lat,lng or /dir/.../lat,lng
            path_parts = parsed_url.path.split('/')
            for part in path_parts:
                if ',' in part:
                    coords = part.split(',')
                    if len(coords) >= 2:
                        lat = coords[0].strip()
                        lng = coords[1].strip()
                        try:
                            float(lat)
                            float(lng)
                            return lat, lng
                        except ValueError:
                            continue
        except Exception:
            pass

        return None, None

    def update_google_map(self):
        for rec in self:
            lat, lng = rec.extract_lat_long(rec.google_maps_url)
            rec.latitude = lat or ''
            rec.longitude = lng or ''

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
        readonly_group = user.has_group('dealer.group_dealer_sales_donotshow')        
        if readonly_group:            
            return self.env['dsales.showroom'].browse([])  

        return super(dealerShowroom, self).search_fetch(domain, field_names, offset, limit, order) 

    # @api.model
    # def check_access_rights(self, operation, raise_exception=True):
    #     user = self.env.user

    #     module_user = user.has_group('dealer.group_dealer_module_user')
    #     backoffice_user = user.has_group('dealer.group_dealer_backoffice_user')
    #     dealer_user = user.has_group('dealer.group_dealer_user')
    #     sales_readonly = user.has_group('dealer.group_dealer_sales_readonly')

    #     # Readonly conditions: module + (backoffice OR dealer) + sales_readonly
    #     if module_user and sales_readonly and (backoffice_user or dealer_user):
    #         if operation in ['create', 'write', 'unlink']:
    #             if raise_exception:
    #                 raise AccessError(_("You have read-only access to sales records."))
    #             return False

    #     # Full access: module + backoffice OR module + dealer (without readonly)
    #     if module_user and ((backoffice_user or dealer_user) and not sales_readonly):
    #         return super().check_access_rights(operation, raise_exception)

    #     # Other users: default behavior
    #     return super().check_access_rights(operation, raise_exception)


    # @api.model
    # def check_access_rights(self, operation, raise_exception=True):
    #     user = self.env.user

    #     # Only block write/create/delete for readonly
    #     if user.has_group('dealer.group_dealer_sales_readonly'):
    #         if operation in ['create', 'write', 'unlink']:
    #             if raise_exception:
    #                 raise AccessError("You have read-only access to Sales Records.")
    #             return False

    #     return super().check_access_rights(operation, raise_exception)

    # @api.model
    # def get_view(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     """
    #     Force readonly users:
    #     - Tree views replaced by minimal hidden tree
    #     - Hide "Create" button in toolbar
    #     - Keep kanban/graph/pivot (dashboard) functional
    #     """
    #     res = super().get_view(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #     user = self.env.user

    #     readonly_group = user.has_group('dealer.group_dealer_sales_readonly')

    #     if readonly_group:
    #         print("readonly_group",readonly_group)
    #         # 1. Hide tree views completely
    #         if view_type == 'tree':
    #             res['arch'] = '<tree><field name="id" invisible="1"/></tree>'
    #             res['fields'] = {'id': {'type': 'integer', 'string': 'ID'}}

    #         # 2. Disable "Create" button for all views (form/kanban/pivot/dashboard)
    #         if toolbar and res.get('toolbar'):
    #             res['toolbar']['create'] = False
    #             # Also disable action buttons if any
    #             if 'action' in res['toolbar']:
    #                 for button in res['toolbar']['action']:
    #                     button['type'] = 'dummy'

    #         # 3. Optional: Prevent the client from accidentally opening tree via dashboard
    #         if view_type in ['form', 'kanban', 'graph', 'pivot']:
    #             # Ensure that any nested tree references are replaced by dummy
    #             # This avoids errors if the dashboard internally queries tree
    #             for field_name, field_def in res.get('fields', {}).items():
    #                 if field_def.get('type') == 'one2many':
    #                     field_def['views'] = {'tree': {'arch': '<tree><field name="id" invisible="1"/></tree>',
    #                                                    'fields': {'id': {'type': 'integer', 'string': 'ID'}}}}

    #     return res

    # @api.model
    # def get_view(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     user = self.env.user
    #     readonly_group = user.has_group('dealer.group_dealer_sales_readonly')
    #     print("readonly_group >>>>>>>>>>>>>>>>>>>", readonly_group)
    #     # return super(dealerShowroom, self).get_view(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
    
