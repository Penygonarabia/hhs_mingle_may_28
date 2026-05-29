# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import json
from odoo.tools import config
from collections import namedtuple
from datetime import datetime
# from odoo.addons.resource.models.resource import float_to_time
from odoo.addons.resource.models.utils import float_to_time
from pytz import timezone, UTC, utc
from datetime import timedelta
import pytz
import requests
import logging
import traceback

_logger = logging.getLogger(__name__)

DummyAttendance = namedtuple(
    "DummyAttendance", "hour_from, hour_to, dayofweek, day_period, week_type"
)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    is_biometric_enable = fields.Boolean(
        string="Biometric Enabled", readonly=True
    )
    biometric_code = fields.Char(string="Biometric Code")
    empl_id = fields.Char(string="Employee ID")
    password = fields.Char(string="Password")
    device_id = fields.Char(string="Device ID", readonly=True)
    firebase_token = fields.Char(string="Firebase Token", readonly=True)
    is_air_planeMode = fields.Boolean(string="Airplane Mode", readonly=True)
    is_location_enabled = fields.Boolean(
        string="Location Enabled", readonly=True
    )
    build_id = fields.Char(string="Build ID", readonly=True)
    device_type = fields.Char(string="Device Type", readonly=True)
    geo_location = fields.Char(string="Geo Location", readonly=True)
    employee_address_ids = fields.One2many(
        "employee.address", "empl_id", string="Employee Address"
    )
    wfh_address = fields.Many2one("res.partner", string="Current Work Address")
    temp_address_id = fields.Many2one("res.partner")

    is_face = fields.Boolean(string="Is Face", default=True)

    is_wfh = fields.Boolean(string="Is WFH", default=True)

    image_authentication = fields.Binary()
    image_unique = fields.Char()
    identification_id = fields.Char(string='Identification No', tracking=True, store=True, compute='_compute_employee_code', readonly=False)


    def send_message(
        self, subject, body, author, message_type, model_name, record_id, **kw
    ):
        msg = self.env["mail.message"].create(
            {"model": model_name, "res_id": record_id, "record_name": body}
        )
        msg.write(
            {
                "subject": subject,
                "author_id": self.env.user.partner_id.id,
                "body": body,
                "message_type": message_type,
            }
        )
        return msg

    def send_notification(
        self, mail_message_id, notification_type, res_partner_id, is_read
    ):
        model = self.env["mail.notification"]
        record = model.sudo().create(
            {
                "mail_message_id": mail_message_id,
                "notification_type": notification_type,
                "res_partner_id": res_partner_id,
                "is_read": is_read,
                "is_app": True,
                "notification_status": "sent",
            }
        )
        return record

    @api.constrains("empl_id")
    def check_employee(self):
        for record in self:
            if record.empl_id:
                count = self.search_count([("empl_id", "=", record.empl_id), ("id", "!=", record.id)])
                if count > 0:
                    raise ValidationError(_("Employee ID should be unique!"))
        # empl_id = self.search_count([("empl_id", "=", self.empl_id)])
        # if empl_id > 0:
        #     raise ValidationError(_("Employee ID should be unique !"))

    def push_notification(self, empl_id, title, body):
        employee_id = self.env["hr.employee"].search(
            [("empl_id", "=", empl_id)], limit=1
        )
        url = "https://fcm.googleapis.com/fcm/send"
        payload = {
            "to": employee_id.firebase_token,
            "collapse_key": "type_a",
            "notification": {"body": body, "title": title},
            "data": {"body": body, "title": title, "empl_id": empl_id},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": "key=%s" % self.env.company.fcm_api_key,
        }
        response = requests.post(
            url, headers=headers, data=json.dumps(payload)
        )
        _logger.info("Run scheduler Check Timesheet {}.".format(response))

    def send_email_notification(self, empl_id, title, body):
        employee = self.env["hr.employee"].search([("empl_id", "=", empl_id)], limit=1)
        template = self.env.ref(
            "geomarking_attendance_mobile_app_knk.geomarking_employee_email_notification"
        )
        if template:
            ctx = {
                "title": title,
                "body": body,
            }
            template.sudo().with_context(ctx).send_mail(
                employee.id, force_send=True
            )
            hr_manager = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("geomarking_attendance_mobile_app_knk.hr_manager")
            )
            on_leave = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("geomarking_attendance_mobile_app_knk.on_leave")
            )
            alternative_hr_manager = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(
                    "geomarking_attendance_mobile_app_knk.alternative_hr_manager"
                )
            )
            if on_leave:
                if alternative_hr_manager:
                    template.sudo().with_context(ctx).send_mail(
                        int(alternative_hr_manager), force_send=True
                    )
            else:
                if hr_manager:
                    template.sudo().with_context(ctx).send_mail(
                        int(hr_manager), force_send=True
                    )

        else:
            _logger.warning("NOTIFICATION EMAIL NOT FOUND")

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for vals in vals_list:
            if vals.get("empl_id") and str(vals.get("empl_id"))[0] == 0:
                raise ValidationError("Employee empl id cannot start with 0.")
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get("empl_id") and str(vals.get("empl_id"))[0] == 0:
            raise ValidationError("Employee empl id cannot start with 0.")
        return res


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    is_biometric_enable = fields.Boolean(string="Biometric Enable")
    biometric_code = fields.Char(string="Biometric Code")
    empl_id = fields.Char(string="Employee ID")
    password = fields.Char(string="Password")


class EmployeeAddress(models.Model):
    _name = "employee.address"
    _description = "Employee Address"

    name = fields.Char(string="Name")
    address_type = fields.Selection(
        [("wfo", "Office Work"), ("wfm", "Remote Work")],
        string="Address Type",
        default="wfm",
    )
    address = fields.Text(string="Address")
    empl_id = fields.Many2one("hr.employee", string="Employee")


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    date = fields.Date(string="Date")
    work_type = fields.Selection(
        [("wfo", "Office Work"), ("wfh", "Remote Work")],
        string="Work Type",
    )

    manual = fields.Boolean()

    # check_in_location = fields.Many2one("multiple.location", string="CheckIn Location")
    # check_out_location = fields.Many2one("multiple.location", string="CheckOut Location")
    check_in_latitude = fields.Char(string="CheckIn Latitude")
    check_in_longitude = fields.Char(string="CheckIn Latitude")
    check_out_latitude = fields.Char(string="CheckOut Longitude")
    check_out_longitude = fields.Char(string="CheckOut Longitude")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(HrAttendance, self).create(vals_list)
        res.date = self.convert_tz(
            fields.Datetime.now(), res.employee_id.tz
        ).date()
        return res

    def _get_report_base_filename(self):
        return "Attendances Report-%s" % (self.employee_id.name)

    def convert_tz(self, datetime, tz):
        return (
            utc.localize(datetime)
            .astimezone(timezone(tz or "UTC"))
            .replace(tzinfo=None)
        )

    def go_to_check_in_google_maps(self):
        url = "https://www.google.com/maps/@{},{},21z".format(
            self.check_in_latitude, self.check_in_longitude
        )
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def go_to_check_out_google_maps(self):
        url = "https://www.google.com/maps/@{},{},21z".format(
            self.check_out_latitude, self.check_out_longitude
        )
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def format_date(self, date):
        if date:
            return str(date.strftime("%I:%M %p"))

    @api.model
    def _cron_daily_auto_checkout(self):
        try:
            yesterday_date = fields.Date.today() - timedelta(days=1)
            domain = [("check_in", "!=", False), ("check_out", "=", False)]
            attendances = self.env["hr.attendance"].search(domain)
            yesterday_attendances = attendances.filtered(
                lambda x: x.check_in.date() == yesterday_date
            )
            current_time = fields.Datetime.now()
            for attendance in yesterday_attendances:
                attendance.check_out = "1900"
    
            yesterday_attendance_alt = attendances.filtered(
                lambda x: x.att_date == yesterday_date
            )
            for record in yesterday_attendance_alt:
                if record.check_in and record.check_in.year == 1900:
                    record.check_out = "1900"
    
            # Combine both lists for report
            all_flagged_attendances = (yesterday_attendances | yesterday_attendance_alt).filtered(
                lambda a: a.check_out and a.check_out.year == 1900
            )
    
            if all_flagged_attendances:
                table_rows = ""
                for record in all_flagged_attendances:
                    emp = record.employee_id
                    table_rows += f"<tr><td>{emp.employee_no or ''}</td><td>{emp.name}</td></tr>"
    
                email_body = f"""
                    <p>The following employees were auto checked out on {yesterday_date.strftime('%d-%m-%Y')} </p>
                    <table border="1" cellpadding="4" cellspacing="0">
                        <tr><th>Employee No</th><th>Employee Name</th></tr>
                        {table_rows}
                    </table>
                """
    
                mail_values = {
                    'subject': _('Auto Checkout Report - %s') % yesterday_date.strftime('%d-%m-%Y'),
                    'body_html': email_body,
                    'email_from': self.env.user.email,
                    'email_to': 'baskar@penygonarabia.com',
                    # multiple emails separated by comma
                }
                self.env['mail.mail'].sudo().create(mail_values).send()
            else:
                email_body = f"""
                    <p>No employees were auto checked out on {yesterday_date.strftime('%d-%m-%Y')}.</p>
                """
                subject = _('Auto Checkout - No Records - %s') % yesterday_date.strftime('%d-%m-%Y')
 
            mail_values = {
                'subject': subject,
                'body_html': email_body,
               'email_from': self.env.user.email,
                'email_to': 'baskar@penygonarabia.com',
            }
            self.env['mail.mail'].sudo().create(mail_values).send()
 
        except Exception as e:
            error_trace = traceback.format_exc()
            error_body = f"""
                <p><strong>Auto Checkout Cron Failed</strong></p>
                <p>Error:</p>
                <pre>{e}</pre>
                <p>Traceback:</p>
                <pre>{error_trace}</pre>
            """
            error_subject = _('Auto Checkout Cron Failed - %s') % fields.Date.today().strftime('%d-%m-%Y')
 
            mail_values = {
                'subject': error_subject,
                'body_html': error_body,
                'email_from': self.env.user.email,
                'email_to': 'baskar@penygonarabia.com',
            }
            self.env['mail.mail'].sudo().create(mail_values).send()





class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wfo_radius = fields.Integer(
        string="WFO Radius",
        config_parameter="geomarking_attendance_mobile_app_knk.wfo_radius",
    )

    hr_manager = fields.Many2one(
        "hr.employee",
        config_parameter="geomarking_attendance_mobile_app_knk.hr_manager",
        readonly=False,
        string="HR Manager",
    )

    alternative_hr_manager = fields.Many2one(
        "hr.employee",
        config_parameter="geomarking_attendance_mobile_app_knk.alternative_hr_manager",
        readonly=False,
        string="Alternative HR Manager",
    )

    on_leave = fields.Boolean(
        config_parameter="geomarking_attendance_mobile_app_knk.on_leave",
        readonly=False,
        string="On Leave",
    )

    attendance_request_limit = fields.Integer(
        "Attendance Requests Limit",
        config_parameter="geomarking_attendance_mobile_app_knk.attendance_requests_limit",
    )

    leave_request_hidden = fields.Boolean(string="Leave Request Hidden",config_parameter="geomarking_attendance_mobile_app_knk.leave_requests_hidden")

    timesheet_hide = fields.Boolean(string="Timesheet hide",config_parameter="geomarking_attendance_mobile_app_knk.timesheets_hide")

class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        # Reset latitude/longitude in case we modify the address without
        # updating the related geolocation fields
        for rec in self:
            previous_latitude = rec.partner_latitude
            previous_longitude = rec.partner_longitude
            if any(
                field in vals
                for field in [
                    "street",
                    "zip",
                    "city",
                    "state_id",
                    "country_id",
                ]
            ) and not all(
                "partner_%s" % field in vals
                for field in ["latitude", "longitude"]
            ):
                vals.update(
                    {
                        "partner_latitude": previous_latitude,
                        "partner_longitude": previous_longitude,
                    }
                )
        return super().write(vals)

    def geo_localize(self):
        # We need country names in English below
        if not self._context.get("force_geo_localize") and (
            self._context.get("import_file")
            or any(
                config[key]
                for key in ["test_enable", "test_file", "init", "update"]
            )
        ):
            return False
        for partner in self.with_context(lang="en_US"):
            result = self._geo_localize(
                partner.street,
                partner.zip,
                partner.city,
                partner.state_id.name,
                partner.country_id.name,
            )
            previous_latitude = self.partner_latitude
            previous_longitude = self.partner_longitude
            if result:
                partner.write(
                    {
                        "partner_latitude": result[0],
                        "partner_longitude": result[1],
                        "date_localization": fields.Date.context_today(
                            partner
                        ),
                    }
                )
            else:
                partner.write(
                    {
                        "partner_latitude": previous_latitude,
                        "partner_longitude": previous_longitude,
                        "date_localization": fields.Date.context_today(
                            partner
                        ),
                    }
                )
        return True


class HrLeave(models.Model):
    _inherit = "hr.leave"

    refusal_reason = fields.Char()

    def action_approve_custom(self, manager_id):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != "confirm" for holiday in self):
            raise UserError(
                _(
                    'Time off request must be confirmed ("To Approve") in order to approve it.'
                )
            )

        current_employee = self.env.user.employee_id
        self.filtered(lambda hol: hol.validation_type == "both").write(
            {"state": "validate1", "first_approver_id": current_employee.id}
        )

        # Post a second message, more verbose than the tracking message
        for holiday in self.filtered(
            lambda holiday: holiday.employee_id.user_id
        ):
            user_tz = timezone(holiday.tz)
            utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
            holiday.message_post(
                body=_(
                    "Your %(leave_type)s planned on %(date)s has been accepted",
                    leave_type=holiday.holiday_status_id.display_name,
                    date=utc_tz.replace(tzinfo=None),
                ),
                partner_ids=holiday.employee_id.user_id.partner_id.ids,
            )

        self.filtered(
            lambda hol: not hol.validation_type == "both"
        ).action_validate()
        if not self.env.context.get("leave_fast_create"):
            self.activity_update_custom(manager_id)
        return True

    def action_refuse_custom(self, manager_id):
        current_employee = self.env["hr.employee"].browse(manager_id)
        if any(
            holiday.state not in ["draft", "confirm", "validate", "validate1"]
            for holiday in self
        ):
            raise UserError(
                _(
                    "Time off request must be confirmed or validated in order to refuse it."
                )
            )

        validated_holidays = self.filtered(
            lambda hol: hol.state == "validate1"
        )
        validated_holidays.write(
            {
                "state": "refuse",
                "first_approver_id": current_employee.id,
                "write_uid": current_employee.user_id.id,
            }
        )
        (self - validated_holidays).write(
            {"state": "refuse", "second_approver_id": current_employee.id}
        )
        # Delete the meeting
        self.mapped("meeting_id").write({"active": False})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped("linked_request_ids")
        if linked_requests:
            linked_requests.action_refuse_custom(manager_id)

        # Post a second message, more verbose than the tracking message
        for holiday in self:
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_(
                        "Your %(leave_type)s planned on %(date)s has been refused",
                        leave_type=holiday.holiday_status_id.display_name,
                        date=holiday.date_from,
                    ),
                    partner_ids=holiday.employee_id.parent_id.user_id.partner_id.ids,
                )
        self.activity_update_custom(manager_id)
        return True

    def activity_update_custom(self, manager_id):
        to_clean, to_do = self.env["hr.leave"], self.env["hr.leave"]
        employee_id = self.env["hr.employee"].sudo().browse(manager_id)
        for holiday in self:
            note = _(
                "New %(leave_type)s Request created by %(user)s",
                leave_type=holiday.holiday_status_id.name,
                user=employee_id.user_id.name
                if employee_id.parent_id.user_id
                else holiday.create_uid.name,
            )
            if holiday.state == "draft":
                to_clean |= holiday
            elif holiday.state == "confirm":
                holiday.activity_schedule(
                    "hr_holidays.mail_act_leave_approval",
                    note=note,
                    user_id=holiday.sudo()._get_responsible_for_approval().id
                    or employee_id.user_id.id
                    if employee_id.user_id
                    else self.env.user.id,
                )
            elif holiday.state == "validate1":
                holiday.activity_feedback(
                    ["hr_holidays.mail_act_leave_approval"]
                )
                holiday.activity_schedule(
                    "hr_holidays.mail_act_leave_second_approval",
                    note=note,
                    user_id=holiday.sudo()._get_responsible_for_approval().id
                    or employee_id.user_id.id
                    if employee_id.user_id
                    else self.env.user.id,
                )
            elif holiday.state == "validate":
                to_do |= holiday
            elif holiday.state == "refuse":
                to_clean |= holiday
        if to_clean:
            to_clean.activity_unlink(
                [
                    "hr_holidays.mail_act_leave_approval",
                    "hr_holidays.mail_act_leave_second_approval",
                ]
            )
        if to_do:
            to_do.activity_feedback(
                [
                    "hr_holidays.mail_act_leave_approval",
                    "hr_holidays.mail_act_leave_second_approval",
                ]
            )

    def get_date_from_to(
        self,
        request_date_from=None,
        request_date_to=None,
        half_day=False,
        custom_hours=False,
        request_date_from_period=None,
        request_hour_from=None,
        request_hour_to=None,
        tz=None,
    ):
        holiday = self
        if (
            request_date_from
            and request_date_to
            and request_date_from > request_date_to
        ):
            request_date_to = request_date_from
        if not request_date_from:
            holiday.date_from = False
        elif not half_day and not custom_hours and not request_date_to:
            holiday.date_to = False
        else:
            if half_day or custom_hours:
                request_date_to = request_date_from
            resource_calendar_id = (
                holiday.employee_id.resource_calendar_id
                or self.env.company.resource_calendar_id
            )
            domain = [
                ("calendar_id", "=", resource_calendar_id.id),
                ("display_type", "=", False),
            ]
            attendances = self.env["resource.calendar.attendance"].read_group(
                domain,
                [
                    "ids:array_agg(id)",
                    "hour_from:min(hour_from)",
                    "hour_to:max(hour_to)",
                    "week_type",
                    "dayofweek",
                    "day_period",
                ],
                ["week_type", "dayofweek", "day_period"],
                lazy=False,
            )

            # Must be sorted by dayofweek ASC and day_period DESC
            attendances = sorted(
                [
                    DummyAttendance(
                        group["hour_from"],
                        group["hour_to"],
                        group["dayofweek"],
                        group["day_period"],
                        group["week_type"],
                    )
                    for group in attendances
                ],
                key=lambda att: (att.dayofweek, att.day_period != "morning"),
            )

            default_value = DummyAttendance(0, 0, 0, "morning", False)

            if resource_calendar_id.two_weeks_calendar:
                # find week type of start_date
                start_week_type = self.env[
                    "resource.calendar.attendance"
                ].get_week_type(request_date_from)
                attendance_actual_week = [
                    att
                    for att in attendances
                    if att.week_type is False
                    or int(att.week_type) == start_week_type
                ]
                attendance_actual_next_week = [
                    att
                    for att in attendances
                    if att.week_type is False
                    or int(att.week_type) != start_week_type
                ]
                # First, add days of actual week coming after date_from
                attendance_filtred = [
                    att
                    for att in attendance_actual_week
                    if int(att.dayofweek) >= request_date_from.weekday()
                ]
                # Second, add days of the other type of week
                attendance_filtred += list(attendance_actual_next_week)
                # Third, add days of actual week (to consider days that we have remove first because they coming before date_from)
                attendance_filtred += list(attendance_actual_week)
                end_week_type = self.env[
                    "resource.calendar.attendance"
                ].get_week_type(request_date_to)
                attendance_actual_week = [
                    att
                    for att in attendances
                    if att.week_type is False
                    or int(att.week_type) == end_week_type
                ]
                attendance_actual_next_week = [
                    att
                    for att in attendances
                    if att.week_type is False
                    or int(att.week_type) != end_week_type
                ]
                attendance_filtred_reversed = list(
                    reversed(
                        [
                            att
                            for att in attendance_actual_week
                            if int(att.dayofweek) <= request_date_to.weekday()
                        ]
                    )
                )
                attendance_filtred_reversed += list(
                    reversed(attendance_actual_next_week)
                )
                attendance_filtred_reversed += list(
                    reversed(attendance_actual_week)
                )

                # find first attendance coming after first_day
                attendance_from = attendance_filtred[0]
                # find last attendance coming before last_day
                attendance_to = attendance_filtred_reversed[0]
            else:
                # find first attendance coming after first_day
                attendance_from = next(
                    (
                        att
                        for att in attendances
                        if int(att.dayofweek) >= request_date_from.weekday()
                    ),
                    attendances[0] if attendances else default_value,
                )
                # find last attendance coming before last_day
                attendance_to = next(
                    (
                        att
                        for att in reversed(attendances)
                        if int(att.dayofweek) <= request_date_to.weekday()
                    ),
                    attendances[-1] if attendances else default_value,
                )

            compensated_request_date_from = request_date_from
            compensated_request_date_to = request_date_to
            if half_day:
                if request_date_from_period == "am":
                    hour_from = float_to_time(attendance_from.hour_from)
                    hour_to = float_to_time(attendance_from.hour_to)
                else:
                    hour_from = float_to_time(attendance_to.hour_from)
                    hour_to = float_to_time(attendance_to.hour_to)
            elif custom_hours:
                hour_from = float_to_time(float(request_hour_from))
                hour_to = float_to_time(float(request_hour_to))
            elif holiday.request_unit_custom:
                hour_from = holiday.date_from.time()
                hour_to = holiday.date_to.time()
                compensated_request_date_from = (
                    holiday._adjust_date_based_on_tz(
                        request_date_from, hour_from
                    )
                )
                compensated_request_date_to = holiday._adjust_date_based_on_tz(
                    request_date_to, hour_to
                )
            else:
                hour_from = float_to_time(attendance_from.hour_from)
                hour_to = float_to_time(attendance_to.hour_to)
            date_from = request_date_from
            date_to = request_date_to
            if tz:
                date_from = (
                    timezone(tz)
                    .localize(
                        datetime.combine(
                            compensated_request_date_from, hour_from
                        )
                    )
                    .astimezone(UTC)
                    .replace(tzinfo=None)
                )
                date_to = (
                    timezone(tz)
                    .localize(
                        datetime.combine(compensated_request_date_to, hour_to)
                    )
                    .astimezone(UTC)
                    .replace(tzinfo=None)
                )

        return date_from, date_to


class ResCompany(models.Model):
    _inherit = "res.company"

    fcm_api_key = fields.Char(string="Fcm Api Key")


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _cron_check_timesheet(self):
        all_employees = self.env["hr.employee"].search([])
        for employee in all_employees:
            timesheet_id = self.env["account.analytic.line"].search(
                [
                    ("date", "=", fields.date.today() - timedelta(days=1)),
                    ("employee_id", "=", employee.id),
                ]
            )
            if not timesheet_id:
                title = "Hello {}!".format(employee.name)
                body = "Fill The Timesheet, Every Penny is Important!"
                if employee.user_partner_id:
                    send_message = self.env["hr.employee"].send_message(
                        title,
                        body,
                        employee.user_partner_id.id,
                        "user_notification",
                        "account.analytic.line",
                        timesheet_id.id,
                    )
                    self.env[
                        "hr.employee"
                    ].send_notification(
                        send_message.id,
                        "inbox",
                        employee.user_partner_id.id,
                        False,
                    )
                    self.env[
                        "hr.employee"
                    ].push_notification(employee.empl_id, title, body)


class MailNotification(models.Model):
    _inherit = "mail.notification"

    is_app = fields.Boolean()


class AllDatabases(models.Model):
    _name = "all.db"
    _description = "All Databases"

    name = fields.Char()
    db_name = fields.Char()
    url = fields.Char()
    logo_img = fields.Image(string="Logo")
    geomarking_app = fields.Boolean()
    odooshoppe_app = fields.Boolean()
    username = fields.Char()
    password = fields.Char()
