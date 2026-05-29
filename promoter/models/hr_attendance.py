from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,AccessError
from datetime import timedelta
import math
import re
from lxml import etree


def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the Earth (meters)."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # -----------------------------
    # Promoter & Time Fields
    # -----------------------------
    is_promoter = fields.Boolean(string="Is Promoter", default=False)
    check_in_time = fields.Char(string="Check In", compute="_compute_check_in_time", store=False)
    check_out_time = fields.Char(string="Check Out", compute="_compute_check_out_time", store=False)
    att_date = fields.Date(string="Attendance Date", compute="_compute_att_date", store=True)
    # -----------------------------
    # Planned Time Fields (from Sheet Line)
    # -----------------------------
    psignin = fields.Datetime(string="Planned Sign In", compute="_compute_planned_times", store=False)
    psignout = fields.Datetime(string="Planned Sign Out", compute="_compute_planned_times", store=False)

    # -----------------------------
    # Showroom / Location Fields
    # -----------------------------
    showroom_id = fields.Many2one('promoter.showroom', string="Showroom")
    showroom_name = fields.Char(string="Showroom Name")
    city_id = fields.Many2one('res.city', string="City")
    region_id = fields.Many2one('res.region', string="Region")
    district_id = fields.Many2one('res.state.district', string="District")
    in_region = fields.Char(string="In Region")
    out_region = fields.Char(string="Out Region")
    in_district = fields.Char(string="In District")
    out_district = fields.Char(string="Out District")

    # -----------------------------
    # Geo Fields
    # -----------------------------
    current_latitude = fields.Float(string="Current Latitude")
    current_longitude = fields.Float(string="Current Longitude")

    @api.model
    def get_view(self, view_id=None, view_type='form', toolbar=False, submenu=False, **options):
        res = super(HrAttendance, self).get_view(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                submenu=submenu, **options)

        if (self.env.user.has_group('promoter.group_promoter_user') or self.env.user.has_group('promoter.group_promoter_backoffice_user')):
            doc = etree.XML(res['arch'])
            if view_type == "form":
                doc.set("create", "false")
                doc.set("delete", "false")
            res['arch'] = etree.tostring(doc, encoding="unicode")

            if view_type == "tree":
                doc.set("create", "false")
                doc.set("delete", "false")
            res["arch"] = etree.tostring(doc, encoding="unicode")

            if view_type == "kanban":
                doc.set("create", "false")
                doc.set("delete", "false")
            res["arch"] = etree.tostring(doc, encoding="unicode")

        return res

    # -----------------------------
    # Helper: convert datetime to HH:MM
    # -----------------------------
    def _datetime_to_hhmm(self, dt):
        if not dt:
            return ""
        return f"{dt.hour:02d}:{dt.minute:02d}"

    # -----------------------------
    # Compute HH:MM for display
    # -----------------------------
    @api.depends('check_in')
    def _compute_check_in_time(self):
        for rec in self:
            if rec.check_in:
                dt = rec.check_in + timedelta(hours=3)  # adjust if needed
                rec.check_in_time = f"{dt.hour:02d}:{dt.minute:02d}"
            else:
                rec.check_in_time = ""

    @api.depends('check_out')
    def _compute_check_out_time(self):
        for rec in self:
            if rec.check_out:
                dt = rec.check_out + timedelta(hours=3)
                rec.check_out_time = f"{dt.hour:02d}:{dt.minute:02d}"
            else:
                rec.check_out_time = ""

    @api.depends('check_in')
    def _compute_att_date(self):
        for rec in self:
            rec.att_date = rec.check_in.date() if rec.check_in else False

    # -----------------------------
    # Helper to extract showroom info
    # -----------------------------
    def _get_showroom_vals(self, showroom):
        return {
            'showroom_name': showroom.name,
            'city_id': showroom.city.id if showroom.city else False,
            'region_id': showroom.region_id.id if showroom.region_id else False,
            'district_id': showroom.district.id if showroom.district else False,
            'in_region': showroom.region_id.name if showroom.region_id else False,
            'out_region': showroom.region_id.name if showroom.region_id else False,
            'in_district': showroom.district.name if showroom.district else False,
            'out_district': showroom.district.name if showroom.district else False,
        }

    # -----------------------------
    # Geo Validation with Safe Radius Conversion
    # -----------------------------
    def _validate_geo(self):
        """Validate promoter's GPS location on check-in and check-out."""
        for rec in self:
            print("\n========== GEO VALIDATION START ==========")
            print(f"[RECORD] ID={rec.id}, EMPLOYEE={rec.employee_id.name}, IS_PROMOTER={rec.is_promoter}")

            # --- Step 0: Validate promoter flag
            if not rec.is_promoter:
                print("[SKIP] Not a promoter, skipping geo validation.")
                continue

            user = self.env.user
            user_name = rec.employee_id.name or user.name or "User"
            print(f"[INFO] User = {user_name} (User ID: {user.id})")

            # --- Step 1: Get GPS from user
            user_lat = user.current_latitude
            user_lon = user.current_longitude
            print(f"[STEP 1] User Coordinates → LAT={user_lat}, LON={user_lon}")

            if not user_lat or not user_lon:
                print("[ERROR] Missing GPS coordinates in user record.")
                raise ValidationError(
                    _("Hi %s, cannot validate your location — GPS coordinates missing on your user profile.")
                    % user_name
                )

            # --- Step 2: Get Active Promoter Assignment
            promoter_assignment = self.env['promoter.assignment'].search([
                ('promoter_id', '=', user.id),
                ('active', '=', True)
            ], limit=1)
            print(f"[STEP 2] Active Promoter Assignment Found → {promoter_assignment.id if promoter_assignment else 'None'}")

            if not promoter_assignment or not promoter_assignment.showroom_id:
                print("[ERROR] No active showroom assigned.")
                raise ValidationError(
                    _("Cannot validate location for promoter '%s': No active showroom assigned.") % user_name
                )

            showroom = promoter_assignment.showroom_id
            print(f"[STEP 3] Assigned Showroom → {showroom.name} (ID={showroom.id})")

            # --- Step 3: promoter_required must be True
            print(f"[STEP 4] Showroom.promoter_required = {showroom.promoter_required}")
            if not showroom.promoter_required:
                print("[ERROR] Showroom does not allow promoter attendance validation.")
                raise ValidationError(
                    _("Hi %s, promoter attendance is not allowed — showroom '%s' does not require promoter validation.")
                    % (user_name, showroom.name)
                )

            # --- Step 4: Validate showroom GPS and city
            print(f"[STEP 5] Showroom Coordinates → LAT={showroom.latitude}, LON={showroom.longitude}")
            if not showroom.latitude or not showroom.longitude:
                print("[ERROR] Showroom coordinates missing.")
                raise ValidationError(
                    _("Cannot validate location for promoter '%s': Showroom '%s' coordinates missing.")
                    % (user_name, showroom.name)
                )

            if not showroom.city:
                print("[ERROR] Showroom city missing.")
                raise ValidationError(
                    _("Geo-location validation failed for promoter '%s': Missing city for showroom '%s'.")
                    % (user_name, showroom.name)
                )

            # --- Step 5: Get safe radius from system parameter
            radius_param = self.env['ir.config_parameter'].sudo().get_param('promoter.promoter_wfo_radius', '100')
            try:
                wfo_radius = int(float(radius_param))
            except (ValueError, TypeError):
                print(f"[WARN] Invalid radius value '{radius_param}', fallback to 100m.")
                wfo_radius = 100

            print(f"[STEP 6] Allowed Radius = {wfo_radius} meters")

            # --- Step 6: Compute actual distance
            distance = haversine(user_lat, user_lon, showroom.latitude, showroom.longitude)
            print(f"[STEP 7] Computed Distance = {distance:.2f} meters")

            # --- Step 7: Validation result
            if distance > wfo_radius:
                print(f"[FAIL] Distance {distance:.2f} > Allowed {wfo_radius}. Validation failed.")
                raise ValidationError(
                    _("Hi %s, you are not in a valid location.\nYou are %.2f meters away (Allowed: %d m).")
                    % (user_name, distance, wfo_radius)
                )

            print(f"[PASS] Geo validation passed. Distance within {wfo_radius} m.")
            print("========== GEO VALIDATION END ==========\n")



    # -----------------------------
    # Create (Check-in)
    # -----------------------------
    @api.model
    def create(self, vals):
        # Detect promoter
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            if getattr(employee, 'is_promoter', False):
                vals['is_promoter'] = True

                # Auto-fill showroom based on logged-in promoter
                user = self.env.user
                showroom = self.env['promoter.showroom'].search([('promoter_id', '=', user.id)], limit=1)
                if showroom:
                    vals['showroom_id'] = showroom.id
                    vals.update(self._get_showroom_vals(showroom))
                else:
                    raise ValidationError(_("No showroom assigned to the logged-in promoter."))

        res = super().create(vals)

        # Validate geo only on promoter check-in
        if res.is_promoter and res.check_in:
            res._validate_geo()

        return res

    # -----------------------------
    # Write (Check-out)
    # -----------------------------
    def write(self, vals):
        res = super().write(vals)

        for rec in self:
            # --- Promoter checkout validation ---
            if vals.get('check_out') and rec.is_promoter:
                print(f"[CHECKOUT VALIDATION] Running for {rec.employee_id.name}")

                # Auto-fill showroom if missing
                if not rec.showroom_id:
                    user = self.env.user
                    showroom = self.env['promoter.showroom'].search(
                        [('promoter_id', '=', user.id)], limit=1
                    )
                    if showroom:
                        rec.showroom_id = showroom.id
                        rec.write(self._get_showroom_vals(showroom))
                    else:
                        raise ValidationError(_("No showroom assigned to the logged-in promoter."))

                # Run geo validation
                rec._validate_geo()

            # --- Manual showroom change ---
            if vals.get('showroom_id'):
                showroom = self.env['promoter.showroom'].browse(vals['showroom_id'])
                rec.write(self._get_showroom_vals(showroom))

        return res

    @api.depends('employee_id')
    def _compute_planned_times(self):
        """Compute planned sign-in/out if hr.attendance_sheet and hr.attendance_sheet_line exist."""
        for rec in self:
            rec.psignin = False
            rec.psignout = False
            print(f"[PSIGN] Start computing for Attendance ID={rec.id}")

            if not rec.employee_id:
                print(f"[PSIGN] Skip - no employee for attendance {rec.id}")
                continue

            # ✅ Check if both models exist in the registry
            # env_models = self.env.registry.models.keys()
            # if 'hr.attendance_sheet' not in env_models or 'hr.attendance_sheet_line' not in env_models:
            #     print(f"[PSIGN] ⚠️ Model not found — hr.attendance_sheet or hr.attendance_sheet_line missing. Skipping employee={rec.employee_id.name}")
            #     continue

            try:
                print(f"[PSIGN] rec.employee_id = {rec.employee_id.id} ({rec.employee_id.name})")

                # ✅ Step 1: Find the latest attendance sheet for this employee
                sheet = self.env['hr.attendance_sheet'].search([
                    ('employee_id', '=', rec.employee_id.id)
                ], limit=1, order='id desc')
                print(f"sheet = {rec.employee_id.id} ({rec.employee_id.name})")
                print(f"[PSIGN] Found sheet: {sheet.id if sheet else 'None'} for employee={rec.employee_id.name}")

                if not sheet:
                    continue  # No sheet found

                # ✅ Step 2: Find the latest line linked to that sheet
                line = self.env['hr.attendance_sheet_line'].search([
                    ('name_id', '=', sheet.id)
                ], limit=1, order='id desc')
                print(f"[PSIGN] Found sheet line: {line.id if line else 'None'} for sheet={sheet.id}")

                if not line:
                    continue

                # ✅ Step 3: Safely assign planned sign-in/out
                def safe_parse(value):
                    if not value:
                        return False
                    if isinstance(value, fields.Datetime):
                        return value
                    if isinstance(value, str):
                        try:
                            return fields.Datetime.from_string(value)
                        except Exception as e:
                            print(f"[PSIGN] Parse error: {e}")
                            return False
                    return False

                rec.psignin = safe_parse(getattr(line, 'psignin', False))
                rec.psignout = safe_parse(getattr(line, 'psignout', False))
                print(f"[PSIGN] ✅ Assigned for {rec.employee_id.name}: psignin={rec.psignin}, psignout={rec.psignout}")

            except Exception as e:
                print(f"[PSIGN] ❌ ERROR for {rec.employee_id.name}: {e}")

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        user = self.env.user

        # Check if user has BOTH backoffice AND readonly groups
        has_both_groups = (
                user.has_group('promoter.group_promoter_backoffice_user') and
                user.has_group('promoter.group_promoter_sales_readonly')
        )

        # If user has both groups, restrict write operations
        if has_both_groups and operation in ['write', 'create', 'unlink']:
            if raise_exception:
                raise AccessError(_("You have read-only access to sales records."))
            return False

        return super().check_access_rights(operation, raise_exception)