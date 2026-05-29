# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

import logging
from math import radians, cos, sin, asin, sqrt
from odoo import http, fields, _, SUPERUSER_ID
from odoo.http import request
import re
from pytz import timezone, utc, UTC
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.http import content_disposition
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from collections import namedtuple
# from odoo.addons.resource.models.resource import float_to_time
from odoo.addons.resource.models.utils import float_to_time

from odoo.tools import float_round

import io

from PyPDF2 import PdfFileReader, PdfFileWriter

from odoo.http import route
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

DATE_FORMAT = "%m-%d-%Y"
DummyAttendance = namedtuple(
    "DummyAttendance", "hour_from, hour_to, dayofweek, day_period, week_type"
)


def check_dateformat(date_string):
    date_format = ""
    try:
        # Try parsing date string as "dd-mm-yyyy" format
        date_format = datetime.strptime(date_string, "%d-%m-%Y")
        return "%d-%m-%Y"
    except ValueError:
        pass

    try:
        # Try parsing date string as "mm-dd-yyyy" format
        date_format = datetime.strptime(date_string, "%m-%d-%Y")
        return "%m-%d-%Y"
    except ValueError:
        pass
    try:
        # Try parsing date string as "yyyy-mm-dd" format
        date_format = datetime.strptime(date_string, "%Y-%m-%d")
        return "%Y-%m-%d"
    except ValueError:
        pass
    try:
        # Try parsing date string as "yyyy-dd-mm" format
        date_format = datetime.strptime(date_string, "%Y-%d-%m")
        return "%Y-%d-%m"
    except ValueError:
        pass

    # If both formats fail, return None
    return date_format


def convert_dateformat(format, date):
    if format == "%Y-%d-%m":
        date_obj = datetime.strptime(date, "%Y-%d-%m")
    elif format == "%d-%m-%Y":
        date_obj = datetime.strptime(date, "%d-%m-%Y")
    elif format == "%m-%d-%Y":
        date_obj = datetime.strptime(date, "%m-%d-%Y")
    elif format == "%Y-%m-%d":
        date_obj = datetime.strptime(date, "%Y-%m-%d")
    new_date_str = date_obj.strftime(DF)
    return new_date_str


class PortalAccount(CustomerPortal):
    def _show_report(
        self, model, report_type, report_ref, download=False, mutiple_rec=False
    ):
        if report_type not in ("html", "pdf", "text"):
            raise UserError(_("Invalid report type: %s", report_type))

        report_sudo = request.env.ref(report_ref).with_user(SUPERUSER_ID)

        if not isinstance(report_sudo, type(request.env["ir.actions.report"])):
            raise UserError(
                _("%s is not the reference of a report", report_ref)
            )

        if hasattr(model, "company_id"):
            report_sudo = report_sudo.with_company(model.company_id)

        method_name = "_render_qweb_%s" % (report_type)
        if mutiple_rec:
            report = getattr(report_sudo, method_name)(
                model.ids, data={"report_type": report_type}
            )[0]
        else:
            report = getattr(report_sudo, method_name)(
                [model.id], data={"report_type": report_type}
            )[0]
        reporthttpheaders = [
            (
                "Content-Type",
                "application/pdf" if report_type == "pdf" else "text/html",
            ),
            ("Content-Length", len(report)),
        ]
        if report_type == "pdf" and download:
            filename = "%s.pdf" % (
                re.sub("\W+", "-", model._get_report_base_filename())
            )
            reporthttpheaders.append(
                ("Content-Disposition", content_disposition(filename))
            )
        return request.make_response(report, headers=reporthttpheaders)

    @http.route(
        [
            "/download/attedance/report/<string:empl_id>/<string:start_date>/<string:end_date>"
        ],
        type="http",
        auth="public",
        website=True,
    )
    def download_attedance_report(self, empl_id, start_date, end_date, **kw):
        attendance = (
            request.env["hr.attendance"]
            .sudo()
            .search(
                [
                    ("employee_id.empl_id", "=", empl_id),
                    ("date", ">=", start_date),
                    ("date", "<=", end_date),
                ]
            )
        )
        record = self._show_report(
            model=attendance,
            report_type="pdf",
            report_ref="geomarking_attendance_mobile_app_knk.print_attendance_report",
            download=True,
            mutiple_rec=True,
        )
        return record

    #########################
    # Apply Leaves
    #########################

    @http.route(
        ["/request/hour/from"],
        type="json",
        auth="auth_bearer",
        methods=["GET", "POST"],
        csrf=False,
    )
    def request_hour_from(self, **post):
        hr_leave = request.env["hr.leave"]
        dict_hrs = dict(hr_leave._fields["request_hour_from"].selection)
        hrs_list = []
        for key, value in dict_hrs.items():
            hrs_list.append({"id": key, "time": value})
        return {"success": True, "request_hour_from": hrs_list}

    @http.route(
        ["/request/hour/to"],
        type="json",
        auth="auth_bearer",
        methods=["GET", "POST"],
        csrf=False,
    )
    def request_hour_to(self, **post):
        hr_leave = request.env["hr.leave"]
        dict_hrs = dict(hr_leave._fields["request_hour_to"].selection)
        hrs_list = []
        for key, value in dict_hrs.items():
            hrs_list.append({"id": key, "time": value})
        return {"success": True, "request_hour_to": hrs_list}

    @http.route(["/apply/leave"], type="json", auth="auth_bearer", csrf=False)
    def employee_apply_leave(
        self,
        empl_id=None,
        start_date=None,
        end_date=None,
        reason=None,
        leave_type_id=None,
        half_day=False,
        custom_hours=False,
        request_date_from_period=None,
        request_hour_from=None,
        request_hour_to=None,
        **post
    ):
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if not employee_id:
            return {"success": False, "msg": _("No employee found.")}
        employee = employee_id.id
        domain = [
            "|",
            ("requires_allocation", "=", "no"),
            "&",
            ("has_valid_allocation", "=", True),
            "&",
            ("virtual_remaining_leaves", ">", 0),
            ("max_leaves", ">", "0"),
        ]
        leave_type = (
            request.env["hr.leave.type"].sudo().browse(int(leave_type_id))
        )
        s_date_format = check_dateformat(start_date)
        e_date_format = check_dateformat(end_date)
        new_start_date = convert_dateformat(s_date_format, start_date)
        new_end_date = convert_dateformat(e_date_format, end_date)
        start_date = datetime.strptime(new_start_date, DF).date()
        end_date = datetime.strptime(new_end_date, DF).date()
        employee = request.env.user.employee_id
        if not (
            employee_id
            and start_date
            and end_date
            and reason
            and leave_type_id
        ):
            return {
                "success": False,
                "msg": _("Some Required Fields are Missing."),
            }
        resource_calendar_id = employee.resource_calendar_id
        domain_1 = [
            ("calendar_id", "=", resource_calendar_id.id),
            ("display_type", "=", False),
        ]
        attendances = (
            request.env["resource.calendar.attendance"]
            .sudo()
            .read_group(
                domain_1,
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
        )
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
        attendance_from = next(
            (
                att
                for att in attendances
                if int(att.dayofweek) >= start_date.weekday()
            ),
            attendances[0] if attendances else default_value,
        )
        attendance_to = next(
            (
                att
                for att in reversed(attendances)
                if int(att.dayofweek) <= end_date.weekday()
            ),
            attendances[-1] if attendances else default_value,
        )
        hour_from = float_to_time(attendance_from.hour_from)
        hour_to = float_to_time(attendance_to.hour_to)
        if not employee:
            employee = employee_id
        start_date = (
            timezone(employee.tz)
            .localize(datetime.combine(start_date, hour_from))
            .astimezone(UTC)
            .replace(tzinfo=None)
        )
        end_date = (
            timezone(employee.tz)
            .localize(datetime.combine(end_date, hour_to))
            .astimezone(UTC)
            .replace(tzinfo=None)
        )
        employee = employee_id
        if start_date.date() > end_date.date():
            return {
                "success": False,
                "msg": _("The start date must be anterior to the end date."),
            }

        domain = [
            ("date_from", "<", end_date),
            ("date_to", ">", start_date),
            ("employee_id", "=", employee.id),
            ("state", "not in", ["cancel", "refuse"]),
        ]
        nholidays = request.env["hr.leave"].sudo().search(domain)
        if nholidays:
            return {
                "success": False,
                "msg": _(
                    "You can not set 2 time off that overlaps on the same day for the same employee."
                ),
            }
        vals = {
            "employee_id": employee_id.id,
            "holiday_status_id": int(leave_type_id),
            "date_from": start_date,
            "request_date_from": start_date,
            "request_date_to": end_date,
            "date_to": end_date,
            "name": reason,
        }

        hr_leave = request.env["hr.leave"]
        date_from, date_to = hr_leave.sudo().get_date_from_to(
            start_date,
            end_date,
            half_day,
            custom_hours,
            request_date_from_period,
            request_hour_from,
            request_hour_to,
            employee.tz,
        )
        vals["date_from"] = date_from
        vals["date_to"] = date_to
        if leave_type.request_unit == "half_day":
            if half_day is True:
                vals["request_unit_half"] = True
                if not request_date_from_period:
                    return {
                        "status": 404,
                        "success": False,
                        "msg": _("Required fields are missing."),
                    }
                vals["request_date_from_period"] = "am"
                vals["number_of_days"] = hr_leave.sudo()._get_number_of_days(
                    date_from, date_to, employee_id.id
                )["days"]
        elif leave_type.request_unit == "hour":
            if half_day is True and custom_hours is False:
                vals["request_unit_half"] = True
                if not request_date_from_period:
                    return {
                        "status": 404,
                        "success": False,
                        "msg": _("Required fields are missing."),
                    }
                vals["request_date_from_period"] = "am"
                if half_day is True:
                    vals[
                        "number_of_days"
                    ] = hr_leave.sudo()._get_number_of_days(
                        date_from, date_to, employee_id.id
                    )[
                        "days"
                    ]
            elif half_day is False and custom_hours is True:
                vals["request_unit_hours"] = True
                if not request_hour_from and not request_hour_to:
                    return {
                        "status": 404,
                        "success": False,
                        "msg": _("Required fields are missing."),
                    }
                vals["request_hour_from"] = request_hour_from
                vals["request_hour_to"] = request_hour_to
            else:
                return {
                    "status": 404,
                    "success": False,
                    "msg": _(
                        "Half_day or custom_hours both can not true at same time"
                    ),
                }
        if leave_type.requires_allocation == "yes":
            available_leaves = leave_type.with_context(
                employee_id=employee.id
            ).virtual_remaining_leaves
            applied_leaves = end_date - start_date
            temp_days = applied_leaves.days + applied_leaves.seconds / (
                3600 * 24
            )
            if available_leaves < temp_days:
                return {
                    "success": False,
                    "msg": _("You can not apply more than available leaves."),
                }

        apply_leave = hr_leave.sudo().create(vals)
        if not request.env.context.get("leave_fast_create"):
            apply_leave.activity_update()
        apply_leave_data = {
            "id": apply_leave.id,
            "time off type": apply_leave.holiday_status_id.name,
            "description": apply_leave.name,
            "start date": apply_leave.date_from,
            "end date": apply_leave.date_to,
            "duraction": apply_leave.duration_display,
            "status": apply_leave.state,
        }
        title = "{} apply a leave".format(employee_id.name)
        body = "{} applied a {} for {}".format(
            employee_id.name,
            apply_leave.holiday_status_id.name,
            apply_leave.duration_display,
        )
        if apply_leave.number_of_days == 1:
            body = "{} applied a {} for 1 day.".format(
                employee_id.name, apply_leave.holiday_status_id.name
            )

        if employee_id.parent_id.address_home_id:
            send_message = employee_id.send_message(
                title,
                body,
                employee_id.parent_id.address_home_id.id,
                "user_notification",
                "hr.leave",
                apply_leave.id,
            )
            employee_id.send_notification(
                send_message.id,
                "inbox",
                employee_id.parent_id.address_home_id.id,
                False,
            )
            employee_id.push_notification(
                employee_id.parent_id.empl_id, title, body
            )

            employee_id.send_email_notification(
                employee_id.parent_id.empl_id, title, body
            )
        return {
            "status": 200,
            "success": True,
            "leave_details": apply_leave_data,
            "msg": "Leave has been Applied."
        }


class API_Hr_Attedance(http.Controller):
    def convert_tz(self, datetime, tz):
        return (
            utc.localize(datetime)
            .astimezone(timezone(tz or "UTC"))
            .replace(tzinfo=None)
        )

    @http.route(
        ["/check/employee"], type="json", auth="auth_bearer", csrf=False
    )
    def check_employee(self, empl_id=None, device_id=None, withOutDeviceID=None, **kw):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        if empl_id:
            domain = [("empl_id", "=", empl_id)]
            if not withOutDeviceID and device_id:
                employee_id = (
                    request.env["hr.employee"]
                    .sudo()
                    .search(
                        [
                            ("empl_id", "=", empl_id),
                            ("device_id", "=", device_id),
                        ]
                    )
                )
                if employee_id:
                    domain += [("device_id", "=", device_id)]
                else:
                    pass
            employee_id = request.env["hr.employee"].sudo().search(domain)
            if employee_id:
                if device_id:
                    if employee_id.device_id:
                        if employee_id.device_id != device_id:
                            return {
                                "success": False,
                                "msg": _(
                                    "Employee registered with another device, please contact to administrator."
                                ),
                            }
                if len(employee_id) == 1 and employee_id.empl_id == empl_id:
                    return {
                        "success": True,
                        "id": employee_id.id,
                        "name": employee_id.name,
                        "password": True if employee_id.password else False,
                        "today_hrs": format(employee_id.hours_today, ".2f"),
                        "job_profile": employee_id.job_title,
                        "department_name": employee_id.department_id.name
                        if employee_id.department_id
                        else False,
                        "empl_id": employee_id.empl_id,
                        "date_of_birth": employee_id.birthday,
                        "city": employee_id.address_home_id.city,
                        "image": employee_id.image_1920,
                        "device_id": employee_id.device_id,
                    }
                elif len(employee_id) == 1 and employee_id.empl_id != empl_id:
                    return {
                        "success": False,
                        "msg": _(
                            "This device is already registered with another employee id."
                        ),
                    }
                elif len(employee_id) > 1:
                    return {
                        "success": False,
                        "msg": _(
                            "This device is registered in multiple employee ids."
                        ),
                    }
                else:
                    return {
                        "success": False,
                        "msg": _("This device is not registered."),
                    }
            else:
                return {"success": False, "msg": _("No employee found.")}

    @http.route(
        ["/create/update/password"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def change_password(
        self, empl_id=None, biometric_code=None, password=None, **kw
    ):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        empl_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if empl_id:
            if empl_id and password and not biometric_code:
                empl_id.password = password
            if empl_id and biometric_code and not password:
                empl_id.biometric_code = biometric_code
                empl_id.is_biometric_enable = True
            if empl_id and biometric_code and password:
                empl_id.password = password
                empl_id.biometric_code = biometric_code
                empl_id.is_biometric_enable = True
            return {"success": True, "msg": _("Password set successfully.")}
        else:
            return {"success": False, "msg": _("No employee found.")}

    @http.route(
        ["/check/password"], type="json", auth="auth_bearer", csrf=False
    )
    def check_password(
        self, empl_id=None, biometric_code=None, password=None, **kw
    ):
        if not empl_id and not password:
            return {"success": False, "msg": _("Required fields are missing.")}
        empl_id = (
            request.env["hr.employee"]
            .sudo()
            .search(
                [
                    ("empl_id", "=", empl_id),
                    "|",
                    ("password", "=", password),
                    ("biometric_code", "=", biometric_code),
                ],
                limit=1,
            )
        )
        if empl_id:
            return {
                "success": True,
                "msg": _("Password matched successfully."),
            }
        else:
            return {
                "success": False,
                "msg": _("Did not match the password please try again."),
            }

    @http.route(
        ["/check/device_info"], type="json", auth="auth_bearer", csrf=False
    )
    def check_device_info(self, device_id=None, **kw):
        if not device_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        domain = [("device_id", "=", device_id)]
        if kw.get("empl_id") and kw.get("empl_id") in ("7667", "1244"):
            return {
                "status": 200,
                "success": True,
                "empl_id": kw.get("empl_id"),
            }

        if kw.get("empl_id"):
            domain += [("empl_id", "=", kw.get("empl_id"))]

        domain += [("empl_id", "not in", ("7667", "1244"))]
        check_device_id = request.env["hr.employee"].sudo().search(domain)
        if len(check_device_id) == 1:
            return {
                "status": 200,
                "success": True,
                "empl_id": check_device_id.empl_id,
            }
        elif len(check_device_id) > 1:
            return {
                "success": False,
                "msg": _(
                    "This device is already registered , please revoke that account"
                ),
            }
        else:
            return {"success": False, "msg": _("Device is not registered")}

    @http.route(
        ["/get/employee/notification"], type="json", auth="auth_bearer"
    )
    def get_empl_notification(self, empl_id=None):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )
        activity_rec_ids = (
            request.env["mail.activity"]
            .sudo()
            .search([("user_id", "=", employee_id.user_id.id)])
        )
        activity_rec_list = []
        for activity_rec_id in activity_rec_ids:
            res_id_rec = request.env[activity_rec_id.res_model].browse(
                activity_rec_id.res_id
            )
            activity_rec_list.append(
                {
                    "id": activity_rec_id.id,
                    "name": activity_rec_id.res_name,
                    "msg": activity_rec_id.note,
                    "record_state": res_id_rec.state,
                    "create_date": activity_rec_id.create_date,
                    "write_date": activity_rec_id.write_date,
                }
            )
        return {"success": True, "notifications": activity_rec_list}

    @http.route("/update/employee/image", type="json", auth="auth_bearer")
    def api_profile_pic_update(
        self, employee_id=None, employee_image=None, **post
    ):
        if not employee_id and not employee_image:
            return {"success": False, "msg": _("Required fields are missing.")}
        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", employee_id)])
        )
        if employee:
            base_url = employee.sudo().get_base_url()
            employee.write({"image_1920": employee_image})
            return {
                "success": True,
                "image": base_url
                + "/web/image/hr.employee/%s/image_1920" % employee.id,
            }
        else:
            return {"success": False, "msg": _("Employee not found.")}

    @http.route(
        ["/update/device_info"], type="json", auth="auth_bearer", csrf=False
    )
    def update_device_info(
        self,
        empl_id,
        device_id,
        is_air_planeMode,
        is_location_enabled,
        build_id,
        device_type,
        geo_location,
        **kw
    ):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        empl_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if empl_id:
            empl_id.update(
                {
                    "device_id": device_id,
                    "is_air_planeMode": is_air_planeMode,
                    "is_location_enabled": is_location_enabled,
                    "build_id": build_id,
                    "device_type": device_type,
                    "geo_location": geo_location,
                }
            )
            return {
                "success": True,
                "msg": _("Device info updated successfully."),
            }
        else:
            return {"success": False, "msg": _("No employee found.")}

    @http.route(
        ["/get/device_info"], type="json", auth="auth_bearer", csrf=False
    )
    def get_device_info(self, empl_id=None, **kw):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        empl_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if empl_id:
            return {
                "success": True,
                "device_id": empl_id.device_id,
                "is_air_planeMode": empl_id.is_air_planeMode,
                "is_location_enabled": empl_id.is_location_enabled,
                "build_id": empl_id.build_id,
                "device_type": empl_id.device_type,
                "geo_location": empl_id.geo_location,
            }
        else:
            return {"success": False, "msg": _("No employee found.")}


    '''Newly added on 08/07/2025 check out handling'''
    @http.route(
        ["/employee/check_in/check_out"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def check_in_check_out(
            self,
            empl_id=None,
            wfo=None,
            wfh=None,
            wfv=None,
            location_id=None,
            latitude=None,
            longitude=None,
            meeting_id=None,
            check_str=None,
            location_type=None,
            save_location=None,
            **kw
    ):
        _logger.info("🚀 check_in_check_out called with: empl_id=%s, latitude=%s, longitude=%s, check_str=%s", empl_id,
                     latitude, longitude, check_str)

        if not (empl_id and latitude and longitude):
            msg = _("Required fields are missing: empl_id({}), latitude({}), longitude({})".format(empl_id, latitude,
                                                                                                   longitude))
            _logger.warning("❌ Missing required fields: %s", msg)
            return {"success": False, "msg": msg}

        empl_id = request.env["hr.employee"].sudo().search([("empl_id", "=", empl_id)], limit=1)
        if not empl_id:
            _logger.warning("❌ No employee found for empl_id.")
            return {"success": False, "msg": _("No employee found.")}

        _logger.info("✅ Employee found: %s", empl_id.name)

        location = None
        if location_type == "multiple" and wfo:
            location = request.env["multiple.location"].sudo().search([("id", "=", int(location_id))])
            if not location:
                _logger.warning("❌ Location not found for id: %s", location_id)
                return {"success": False, "msg": "Please provide the correct location_id."}
            _logger.info("📍 Location found: %s", location.name)

        # Search for existing open attendance
        empl_attendance = request.env["hr.attendance"].sudo().search(
            [("employee_id", "=", empl_id.id), ("check_out", "=", False)],
            limit=1
        )
        _logger.info("🔍 Existing open attendance found: %s", bool(empl_attendance))

        # Handle check-in
        if check_str == "in":
            if not empl_attendance:
                checkin_time = fields.Datetime.now()
                _logger.info("🕒 Creating new attendance for check-in at %s", checkin_time)
                empl_attendance = request.env["hr.attendance"].sudo().create({
                    "employee_id": empl_id.id,
                    "check_in": checkin_time,
                    "work_type": "wfo" if wfo else "wfh" if wfh else False,
                })
            else:
                # _logger.warning("⚠️ Already checked in. Cannot check in again without checking out.")
                _logger.warning("⚠️ Already checked in. Cannot check in again without checking out. Attendance ID: %s",
                                empl_attendance.id)

                return {"success": False, "msg": _("The employee is already checked in. Please check out first.")}

        # Handle check-out
        elif check_str == "out":
            if empl_attendance:
                # checkout_time = fields.Datetime.now()
                # checkout_time = ""
                yesterday_date = fields.Date.today() - timedelta(days=1)
                domain = [("check_in", "!=", False), ("check_out", "=", False)]
                attendances = request.env["hr.attendance"].sudo().search(domain)
                yesterday_attendances = attendances.filtered(
                    lambda x: x.check_in.date() == yesterday_date
                )
                current_time = fields.Datetime.now()
                if yesterday_attendances:
                    for attendance in yesterday_attendances:
                        attendance.check_out = "1900"
                else:
                    empl_attendance.check_out = fields.Datetime.now()




                _logger.info("🕒 Checking out at %s", empl_attendance.check_out)
                # empl_attendance.check_out = checkout_time
            else:
                _logger.warning("⚠️ No open attendance record found for check-out.")
                return {"success": False, "msg": _("No check-in record found. Please check in first.")}

        # Update location details
        if empl_attendance:
            if location_type == "multiple" and wfo:
                if check_str == "in":
                    empl_attendance.check_in_location = location.id
                    _logger.info("📌 Check-in location set to: %s", location.name)
                elif check_str == "out":
                    empl_attendance.check_out_location = location.id
                    _logger.info("📌 Check-out location set to: %s", location.name)

            if wfo:
                empl_attendance.work_type = "wfo"
                _logger.info("💼 Work type set to: wfo")
            elif wfh:
                empl_attendance.work_type = "wfh"
                _logger.info("💼 Work type set to: wfh")

            if save_location:
                if check_str == "in":
                    empl_attendance.check_in_latitude = latitude
                    empl_attendance.check_in_longitude = longitude
                    _logger.info("📍 Check-in coordinates set: (%s, %s)", latitude, longitude)
                elif check_str == "out":
                    empl_attendance.check_out_latitude = latitude
                    empl_attendance.check_out_longitude = longitude
                    _logger.info("📍 Check-out coordinates set: (%s, %s)", latitude, longitude)

            check_in_str = self.convert_tz(empl_attendance.check_in, empl_id.tz) if empl_attendance.check_in else False
            check_out_str = self.convert_tz(empl_attendance.check_out,
                                            empl_id.tz) if empl_attendance.check_out else False

            _logger.info("✅ Returning success response.")
            return {
                "success": True,
                "msg": _("Employee Check-In Successfully.") if check_str == "in" else _(
                    "Employee Check-Out Successfully."),
                "employee_name": empl_id.name,
                "work_type": empl_attendance.work_type,
                "check_in_date": check_in_str,
                "check_out_date": check_out_str,
                "today_hrs": format(empl_id.hours_today, ".2f"),
            }


    '''Comment on 08/07/2025 this original code'''
    # @http.route(
    #     ["/employee/check_in/check_out"],
    #     type="json",
    #     auth="auth_bearer",
    #     csrf=False,
    # )
    # def check_in_check_out(
    #     self,
    #     empl_id=None,
    #     wfo=None,
    #     wfh=None,
    #     wfv=None,
    #     location_id=None,
    #     latitude=None,
    #     longitude=None,
    #     meeting_id=None,
    #     check_str=None,
    #     location_type=None,
    #     save_location=None,
    #     **kw
    # ):
    #     if not (empl_id and latitude and longitude):
    #         return {
    #             "success": False,
    #             "msg": _(
    #                 "Required fields are missing: empl_id({}), latitude({}), longitude({})".format(
    #                     empl_id, latitude, longitude
    #                 )
    #             ),
    #         }
    #
    #     empl_id = (
    #         request.env["hr.employee"]
    #         .sudo()
    #         .search([("empl_id", "=", empl_id)], limit=1)
    #     )
    #
    #     if empl_id:
    #         if location_type == "multiple" and wfo:
    #             location = (
    #                 request.env["multiple.location"]
    #                 .sudo()
    #                 .search([("id", "=", int(location_id))])
    #             )
    #             if not location:
    #                 return {
    #                     "success": False,
    #                     "msg": "Please provide the correct location_id.",
    #                 }
    #
    #
    #         empl_attendance = request.env["hr.attendance"].sudo().search(
    #             [("employee_id", "=", empl_id.id), ("check_out", "=", False)], limit=1
    #         )
    #
    #         if check_str == "in":
    #             if not empl_attendance:
    #                 # Create a new attendance record for check-in
    #                 empl_attendance = request.env["hr.attendance"].sudo().create({
    #                     "employee_id": empl_id.id,
    #                     "check_in": fields.Datetime.now(),
    #                     "work_type": "wfo" if wfo else "wfh" if wfh else False,
    #                 })
    #             else:
    #                 return {
    #                     "success": False,
    #                     "msg": _("The employee is already checked in. Please check out first."),
    #                 }
    #
    #         elif check_str == "out":
    #             if empl_attendance:
    #                 empl_attendance.check_out = fields.Datetime.now()
    #             else:
    #                 return {
    #                     "success": False,
    #                     "msg": _("No check-in record found. Please check in first."),
    #                 }
    #
    #         # Update additional information based on the location and work type
    #         if empl_attendance:
    #             if location_type == "multiple" and wfo:
    #                 if check_str == "in":
    #                     empl_attendance.check_in_location = location.id
    #                 elif check_str == "out":
    #                     empl_attendance.check_out_location = location.id
    #
    #             if wfo:
    #                 empl_attendance.work_type = "wfo"
    #             if wfh:
    #                 empl_attendance.work_type = "wfh"
    #
    #             if save_location:
    #                 if check_str == "in":
    #                     empl_attendance.check_in_latitude = latitude
    #                     empl_attendance.check_in_longitude = longitude
    #                 elif check_str == "out":
    #                     empl_attendance.check_out_latitude = latitude
    #                     empl_attendance.check_out_longitude = longitude
    #
    #             return {
    #                 "success": True,
    #                 "msg": _("Employee Check-In Successfully.")
    #                 if check_str == "in"
    #                 else _("Employee Check-Out Successfully."),
    #                 "employee_name": empl_id.name,
    #                 "work_type": empl_attendance.work_type,
    #                 "check_in_date": self.convert_tz(
    #                     empl_attendance.check_in, empl_id.tz
    #                 ) if empl_attendance.check_in else False,
    #                 "check_out_date": self.convert_tz(
    #                     empl_attendance.check_out, empl_id.tz
    #                 ) if empl_attendance.check_out else False,
    #                 "today_hrs": format(empl_id.hours_today, ".2f"),
    #             }
    #
    #
    #     #     action = empl_id._attendance_action_change(
    #     #         "hr_attendance.hr_attendance_action"
    #     #     )["action"]
    #     #     attendance_details = action["attendance"]
    #     #     empl_attendance = (
    #     #         request.env["hr.attendance"]
    #     #         .sudo()
    #     #         .browse(int(attendance_details.get("id")))
    #     #     )
    #     #     if location_type == "multiple" and wfo:
    #     #         if check_str == "in":
    #     #             empl_attendance.check_in_location = location.id
    #     #         elif check_str == "out":
    #     #             empl_attendance.check_out_location = location.id
    #     #
    #     #     if wfo:
    #     #         empl_attendance.work_type = "wfo"
    #     #     if wfh:
    #     #         empl_attendance.work_type = "wfh"
    #     #     if save_location:
    #     #         if check_str == "in":
    #     #             empl_attendance.check_in_latitude = latitude
    #     #             empl_attendance.check_in_longitude = longitude
    #     #         elif check_str == "out":
    #     #             empl_attendance.check_out_latitude = latitude
    #     #             empl_attendance.check_out_longitude = longitude
    #     #
    #     #     return {
    #     #         "success": True,
    #     #         "msg": _("Employee Check-In Successfully.")
    #     #         if not attendance_details.get("check_out")
    #     #         else _("Employee Check-Out Successfully."),
    #     #         "employee_name": empl_id.name,
    #     #         "work_type": empl_attendance.work_type,
    #     #         "check_in_date": self.convert_tz(
    #     #             attendance_details.get("check_in"), empl_id.tz
    #     #         )
    #     #         if attendance_details.get("check_in")
    #     #         else False,
    #     #         "check_out_date": self.convert_tz(
    #     #             attendance_details.get("check_out"), empl_id.tz
    #     #         )
    #     #         if attendance_details.get("check_out")
    #     #         else False,
    #     #         "today_hrs": format(empl_id.hours_today, ".2f"),
    #     #     }
    #     else:
    #         return {"success": False, "msg": _("No employee found.")}

    @http.route(
        ["/get/employee/today/activity"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def get_empl_today_activity(self, empl_id=None, **kw):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        empl_attendance_dtls = []
        empl_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if empl_id:
            empl_attendance = (
                request.env["hr.attendance"]
                .sudo()
                .search(
                    [
                        ("date", "=", fields.Date.today()),
                        ("employee_id", "=", empl_id.id),
                    ]
                )
            )
            if empl_attendance:
                for rec in empl_attendance:
                    empl_attendance_dtls.append(
                        {
                            "work_type": rec.work_type,
                            "check_in": self.convert_tz(
                                rec.check_in, empl_id.tz
                            )
                            if rec.check_in
                            else False,
                            "check_out": self.convert_tz(
                                rec.check_out, empl_id.tz
                            )
                            if rec.check_out
                            else False,
                            "worked_hrs": format(rec.worked_hours, ".2f"),
                            "location": empl_id.address_id.city
                            if empl_id.address_id
                            else False,
                        }
                    )
                return {
                    "success": True,
                    "empl_attendance_details": empl_attendance_dtls,
                }
            else:
                return {"success": False, "msg": _("No activity found.")}
        else:
            return {"success": False, "msg": _("No employee found.")}

    @http.route(["/check/manager"], type="json", auth="auth_bearer")
    def check_manager_api(self, empl_id=None, **kw):
        all_empl_rec = []
        is_manager = False
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        all_empl_rec.append(employee_id)
        if employee_id.subordinate_ids:
            is_manager = True
            empl_records = (
                request.env["hr.employee"]
                .sudo()
                .search([("id", "in", employee_id.subordinate_ids.ids)])
            )
            all_empl_rec += empl_records
        return {"is_manager": is_manager}

    def get_all_child_employees(self, employee):
        return employee.subordinate_ids

    def check_manager(self, empl_id):
        all_empl_rec = []
        is_manager = False
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        all_empl_rec.append(employee_id)
        if employee_id.subordinate_ids:
            is_manager = True
            all_empl_rec = self.get_all_child_employees(employee_id)
        return is_manager, all_empl_rec

    @http.route(
        ["/show/all/attendance"], type="json", auth="auth_bearer", csrf=False
    )
    def show_all_attendance(
        self, date=None, empl_id=None, **kw
    ):  # Date Format : DD-MM-YYYY
        check_manager, total_employess = self.check_manager(empl_id)
        if check_manager:
            employee_rec_list = []
            for empl_record in total_employess:
                employee_rec_list.append(
                    {
                        "name": empl_record.name,
                        "empl_id": empl_record.empl_id,
                        "date": date,
                        "attendance_record": self.employee_attedance_log(
                            empl_record.empl_id, date
                        ),
                    }
                )
            return {"success": True, "result": employee_rec_list}
        else:
            return {"success": False, "msg": _("Employee is not manager.")}

    @http.route(["/get/manager/record"], type="json", auth="auth_bearer")
    def get_manager_record(self, empl_id=None, **kw):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        all_empl_rec = []
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        all_empl_rec.append(employee_id)
        employee_rec_list = []
        if employee_id.child_ids:
            empl_records = (
                request.env["hr.employee"]
                .sudo()
                .search([("id", "in", employee_id.subordinate_ids.ids)])
            )
            all_empl_rec += empl_records
            for empl_record in all_empl_rec:
                empl_attendance_dtls = []
                empl_attendance = (
                    request.env["hr.attendance"]
                    .sudo()
                    .search(
                        [
                            ("date", "=", fields.Date.today()),
                            ("employee_id", "=", empl_record.id),
                        ]
                    )
                )
                if empl_attendance:
                    for rec in empl_attendance:
                        empl_attendance_dtls.append(
                            {
                                "work_type": rec.work_type,
                                "check_in": self.convert_tz(
                                    rec.check_in, empl_record.tz
                                )
                                if rec.check_in
                                else False,
                                "check_out": self.convert_tz(
                                    rec.check_out, empl_record.tz
                                )
                                if rec.check_out
                                else False,
                                "worked_hrs": format(rec.worked_hours, ".2f"),
                            }
                        )
                employee_rec_list.append(
                    {
                        "name": empl_record.name,
                        "empl_id": empl_record.empl_id,
                        "color_code": "#FF0000"
                        if empl_attendance_dtls
                        else "#000000",
                        "empl_attendance_dtls": empl_attendance_dtls,
                    }
                )
            return {"success": True, "result": employee_rec_list}
        return {"success": True, "msg": _("Employee has not child manager.")}

    @http.route(
        ["/get/employee/weekly/activity"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def get_empl_weekly_activity(self, empl_id=None, **kw):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        empl_attendance_dtls = []
        today = fields.Date.today()
        last_week = today - timedelta(days=7)
        empl_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if empl_id:
            empl_attendance = (
                request.env["hr.attendance"]
                .sudo()
                .search(
                    [
                        ("employee_id", "=", empl_id.id),
                    ]
                )
            )
            if empl_attendance.filtered(lambda x: x.check_in.date() >= last_week and x.check_in.date() <= today):
                for rec in empl_attendance.filtered(lambda x: x.check_in.date() >= last_week and x.check_in.date() <= today):
                    empl_attendance_dtls.append(
                        {
                            "work_type": rec.work_type,
                            "check_in": self.convert_tz(
                                rec.check_in, empl_id.tz
                            )
                            if rec.check_in
                            else False,
                            "check_out": self.convert_tz(
                                rec.check_out, empl_id.tz
                            )
                            if rec.check_out
                            else False,
                            "worked_hrs": format(rec.worked_hours, ".2f"),
                            "location": empl_id.address_id.city
                            if empl_id.address_id
                            else False,
                        }
                    )
                return {
                    "success": True,
                    "empl_attendance_details": empl_attendance_dtls,
                }
            else:
                return {"success": False, "msg": _("No activity found.")}
        else:
            return {"success": False, "msg": _("No employee found.")}

    @http.route(
        ["/get/employee/monthly/activity"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def get_empl_monthly_activity(self, empl_id=None, **kw):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        empl_attendance_dtls = []
        today = fields.Date.today()
        last_month = today - timedelta(days=30)
        empl_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if empl_id:
            empl_attendance = (
                request.env["hr.attendance"]
                .sudo()
                .search(
                    [
                        ("employee_id", "=", empl_id.id),
                    ]
                )
            )
            if empl_attendance.filtered(lambda x: x.check_in.date() >= last_month and x.check_in.date() <= today):
                for rec in empl_attendance.filtered(lambda x: x.check_in.date() >= last_month and x.check_in.date() <= today):
                    empl_attendance_dtls.append(
                        {
                            "work_type": rec.work_type,
                            "check_in": self.convert_tz(
                                rec.check_in, empl_id.tz
                            )
                            if rec.check_in
                            else False,
                            "check_out": self.convert_tz(
                                rec.check_out, empl_id.tz
                            )
                            if rec.check_out
                            else False,
                            "worked_hrs": format(rec.worked_hours, ".2f"),
                            "location": empl_id.address_id.city
                            if empl_id.address_id
                            else False,
                        }
                    )
                return {
                    "success": True,
                    "empl_attendance_details": empl_attendance_dtls,
                }
            else:
                return {"success": False, "msg": _("No activity found.")}
        else:
            return {"success": False, "msg": _("No employee found.")}

    @http.route(
        ["/get/employee/all/activity"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def get_empl_all_activity(self, empl_id=None, **kw):
        if not empl_id:
            return {"success": False, "msg": _("Required fields are missing.")}
        empl_attendance_dtls = []
        empl_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if empl_id:
            empl_attendance = (
                request.env["hr.attendance"]
                .sudo()
                .search([("employee_id", "=", empl_id.id)])
            )
            if empl_attendance:
                for rec in empl_attendance:
                    empl_attendance_dtls.append(
                        {
                            "work_type": rec.work_type,
                            "check_in": self.convert_tz(
                                rec.check_in, empl_id.tz
                            )
                            if rec.check_in
                            else False,
                            "check_out": self.convert_tz(
                                rec.check_out, empl_id.tz
                            )
                            if rec.check_out
                            else False,
                            "worked_hrs": format(rec.worked_hours, ".2f"),
                            "location": empl_id.address_id.city
                            if empl_id.address_id
                            else False,
                            "date": rec.date,
                            "name": rec.employee_id.name,
                        }
                    )
                return {
                    "success": True,
                    "empl_attendance_details": empl_attendance_dtls,
                }
            else:
                return {"success": False, "msg": _("No activity found.")}
        else:
            return {"success": False, "msg": _("No employee found.")}

    def haversine(lat1, lon1, lat2, lon2):
        # Radius of the Earth in kilometers
        lon1 = radians(lon1)
        lon2 = radians(lon2)
        lat1 = radians(lat1)
        lat2 = radians(lat2)

        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2

        c = 2 * asin(sqrt(a))

        # Radius of earth in kilometers. Use 3956 for miles
        r = 6371

        # calculate the result
        return c * r

    @http.route(["/get/employee/address"], type="json", auth="public")
    def get_empl_address(
        self,
        empl_id=None,
        empl_lat=None,
        empl_long=None,
        wfo=None,
        wfh=None,
        wfv=None,
        location_type=None,
        **kw
    ):
        if not empl_id and (not wfo or not wfh):
            return {"success": False, "msg": _("Required fields are missing.")}

        if not location_type:
            return {
                "success": False,
                "msg": "Please Provide the location_type.",
            }

        if not empl_lat and empl_long:
            return {
                "success": False,
                "msg": _("Employee's location details are missing"),
            }
        empl_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )

        if empl_id:
            if wfo:
                if location_type == "single":
                    return {
                        "success": True,
                        "assigned_locations": None,
                        "closest_locations": {
                            "id": 0,
                            "latitude": empl_id.address_id.partner_latitude,
                            "longitude": empl_id.address_id.partner_longitude,
                            "radius": request.env["ir.config_parameter"]
                            .sudo()
                            .get_param(
                                "geomarking_attendance_mobile_app_knk.wfo_radius"
                            ),
                        },
                    }
            if wfh:
                return {
                    "success": True,
                    "latitude": empl_id.wfh_address.partner_latitude,
                    "longitude": empl_id.wfh_address.partner_longitude,
                    "radius": 0,
                }
        else:
            return {"success": False, "msg": _("No employee found.")}

    def get_portal_pdf_url(
        self,
        empl_id,
        start_date,
        end_date,
        suffix=None,
        report_type="pdf",
        download=None,
    ):
        url = "/download/attedance/report/%s/%s/%s?%s%s" % (
            empl_id,
            start_date,
            end_date,
            "report_type=%s" % report_type if report_type else "",
            "&download=true" if download else "",
        )
        return url

    @http.route(
        ["/download/employee/attedance/report"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def employee_attedance_report(
        self, empl_id=None, start_date=None, end_date=None, **kw
    ):
        _logger.info(f"Received parameters - empl_id: {empl_id}, start_date: {start_date}, end_date: {end_date}")
        if not empl_id and not start_date and not end_date:
            _logger.warning("Missing required fields.")
            return {"success": False, "msg": _("Required fields are missing.")}
        start_date_new = datetime.strptime(start_date, "%d/%m/%Y").date()
        end_date_new = datetime.strptime(end_date, "%d/%m/%Y").date()
        _logger.info(f"Parsed dates - start_date: {start_date_new}, end_date: {end_date_new}")
        attendance = (
            request.env["hr.attendance"]
            .sudo()
            .search(
                [
                    ("employee_id.empl_id", "=", empl_id),
                    ("date", ">=", start_date_new),
                    ("date", "<=", end_date_new),
                ]
            )
        )
        _logger.info(f"Attendance search result: {attendance}")
        if not attendance:
            _logger.info("No attendance found for the given criteria.")
            return {"success": False, "msg": _("No report found!.")}
        base_url = (
            request.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )
        url = base_url + self.get_portal_pdf_url(
            empl_id, start_date_new, end_date_new
        )
        _logger.info(f"Generated report URL: {url}")
        return {"success": True, "url": url}

    @http.route(
        ["/employee/attedance/datewise/log"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def employee_attedance_log(
        self, empl_id=None, date=None, **kw
    ):  # Date Format : DD-MM-YYYY
        if not empl_id and not date:
            return {"success": False, "msg": _("Required fields are missing.")}
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        _logger.warning('EMPLOYEE DATEWISE LOG: {}'.format(date))
        date = datetime.strptime(date, "%m-%d-%Y")
        attendance = (
            request.env["hr.attendance"]
            .sudo()
            .search(
                [("employee_id.empl_id", "=", empl_id)],
                order="check_in desc",
            )
        )

        attendance = attendance.filtered(lambda x: x.check_in.date() == date.date())
        _logger.warning("EMPLOYEE DATEWISE ATTENDANCE: {}, DATE: {}".format(attendance, date))
        if not attendance:
            return {"success": False, "msg": _("No Log found!.")}
        first_check_in = (
            self.convert_tz(attendance[-1].check_in, employee_id.tz)
            if attendance[-1].check_in
            else False
        )
        last_check_out = (
            self.convert_tz(attendance[0].check_out, employee_id.tz)
            if attendance[0].check_out
            else False
        )
        worked_hours = sum(attendance.mapped("worked_hours"))
        hours = int(worked_hours)
        minutes = (worked_hours * 60) % 60
        return {
            "success": True,
            "first_check_in": first_check_in,
            "last_check_out": last_check_out,
            "total_hrs": "%d.%02d" % (hours, minutes),
        }

    @http.route(
        ["/website/employee/users"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def website_empl_user(
        self,
        name=None,
        email=None,
        mobile=None,
        role=None,
        timezone=None,
        **kw
    ):
        employee = (
            request.env["hr.employee"]
            .sudo()
            .create(
                {
                    "name": name,
                    "work_email": email,
                    "work_phone": mobile,
                    "job_title": role,
                    "tz": timezone,
                }
            )
        )
        if employee:
            user_vals = {
                "name": employee.name,
                "login": employee.work_email,
                "email": employee.work_email,
            }
            user = request.env["res.users"].sudo().sudo().create(user_vals)
            user_sudo = user.sudo()
            employee.user_id = user_sudo.id
            template = request.env.ref(
                "geomarking_attendance_mobile_app_knk.email_template_edi_geomarking"
            )
            template.sudo().send_mail(user_sudo.id, force_send=True)
        return True

    @http.route(["/get/all/db"], type="json", auth="public")
    def get_all_db(self, **kwargs):
        base_url = (
            request.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )
        model = request.env["all.db"]
        if not kwargs.get("url"):
            return {"success": False, "msg": _("Required fields is missing")}
        domain = [("url", "=", kwargs.get("url"))]
        if kwargs.get("appName") == "OdooShoppe":
            domain += [("odooshoppe_app", "=", True)]
        else:
            domain += [("geomarking_app", "=", True)]
        records = model.search(domain)
        record_list = []
        if not records:
            return {"success": False, "result": record_list}
        for record in records:
            record_list.append(
                {
                    "name": record.name,
                    "db_name": record.db_name,
                    "url": record.url,
                    "username": record.username,
                    "password": record.password,
                    "logo_img": base_url
                    + "/web/image/all.db/%s/logo_img" % record.id,
                }
            )

        return {"success": True, "result": record_list}

    @http.route("/get/user/bearer/token", type="json", auth="public")
    def get_bearer_token(self, email=None, **kwargs):
        if not email:
            return {"success": False, "msg": _("Required fields is missing")}
        model = request.env["res.users"]
        user_id = model.sudo().search(
            [("login", "=", email), ("active", "=", True)]
        )
        if not user_id:
            return {"success": False, "msg": _("User not found")}
        return {
            "success": True,
            "user_id": user_id.id,
            "bearer_token": user_id.bearer_token,
        }


###################################
# Apply Leaves API's
##################################


class API_Apply_leave(API_Hr_Attedance):
    def is_leave_request_hidden(self):
        """Checks if leave requests are hidden based on configuration."""
        leave_request_hidden = request.env["ir.config_parameter"].sudo().get_param(
            "geomarking_attendance_mobile_app_knk.leave_requests_hidden", default=False
        )
        return leave_request_hidden == "True"

    @http.route(
        ["/get/leaves"],
        type="json",
        auth="auth_bearer",
        csrf=False,
        methods=["POST"],
    )
    def get_employee_leave(self, employee_id=None):

        if self.is_leave_request_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Leave requests are currently hidden."),
            }

        if not employee_id:
            return {
                "status": 404,
                "access": False,
                "msg": _("Required fields are missing."),
            }
        check_employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", employee_id)])
        )
        if check_employee_id:
            try:
                all_leave_type_id = (
                    request.env["hr.leave.type"].sudo().search([])
                )
                all_leave_type_rec = all_leave_type_id.get_employees_days(
                    check_employee_id.ids
                )
                leaves_list = []
                for leave in all_leave_type_id:
                    number_of_days = all_leave_type_rec[check_employee_id.id][
                        leave.id
                    ]["virtual_remaining_leaves"]
                    if number_of_days * 1e17 - int(number_of_days) * 1e17 == 0:
                        leaves_list.append(
                            {
                                "leaves_type_id": leave.id,
                                "name": leave.name,
                                "number_of_days": "{} {}".format(
                                    0, leave.request_unit.capitalize()
                                )
                                if number_of_days < 0
                                else "{} {}s".format(
                                    int(number_of_days),
                                    leave.request_unit.capitalize(),
                                )
                                if number_of_days > 1
                                else "{} {}".format(
                                    int(number_of_days),
                                    leave.request_unit.capitalize(),
                                ),
                                "request_unit": leave.request_unit,
                            }
                        )
                    else:
                        leaves_list.append(
                            {
                                "leaves_type_id": leave.id,
                                "name": leave.name,
                                "number_of_days": "{} {}".format(
                                    0, leave.request_unit.capitalize()
                                )
                                if number_of_days < 0
                                else "{} {}s".format(
                                    number_of_days,
                                    leave.request_unit.capitalize(),
                                )
                                if number_of_days > 1
                                else "{} {}".format(
                                    number_of_days,
                                    leave.request_unit.capitalize(),
                                ),
                                "request_unit": leave.request_unit,
                            }
                        )

                if all_leave_type_id:
                    return {
                        "status": 200,
                        "success": True,
                        "leaves": leaves_list,
                    }
                else:
                    return {
                        "status": 200,
                        "success": True,
                        "msg": _("leaves are not available."),
                    }
            except Exception as e:
                _logger.error("GET LEAVES ERROR: {}".format(e))
                return {
                    "status": 404,
                    "success": False,
                    "msg": _("please check employee's related user."),
                }
        else:
            return {
                "status": 404,
                "success": False,
                "msg": _("employee id is Invalid."),
            }

    def employee_leaves_history(self, employee_id, date):
        if self.is_leave_request_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Leave requests are currently hidden."),
            }

        if not employee_id:
            return {
                "status": 404,
                "access": False,
                "msg": _("Required fields are missing."),
            }
        check_employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", employee_id)])
        )
        if not check_employee_id:
            return {
                "status": 404,
                "success": False,
                "msg": _("employee id is Invalid."),
            }
        domain = [("employee_id", "=", int(check_employee_id.id))]
        if date:
            date = datetime.strptime(date, "%m-%d-%Y")
            domain += [("request_date_from", "=", date)]
        leaves_history = request.env["hr.leave"].sudo().search(domain)
        leave_history_list = []
        for leave_history in leaves_history:
            leave_history_list.append(
                {
                    "id": leave_history.id,
                    "time_off_type": leave_history.holiday_status_id.name,
                    "description": leave_history.name,
                    "start_date": leave_history.date_from,
                    "end_date": leave_history.date_to,
                    "duraction": leave_history.duration_display,
                    "status": leave_history.state,
                }
            )
        return {"date": date, "leave_history": leave_history_list}

    @http.route(
        ["/get/all/leaves"],
        type="json",
        auth="auth_bearer",
        csrf=False,
        methods=["POST"],
    )
    def get_employee_all_leaves(self, empl_id=None, date=None):
        if self.is_leave_request_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Leave requests are currently hidden."),
            }

        if not empl_id:
            return {
                "status": 404,
                "access": False,
                "msg": _("Required fields are missing."),
            }
        check_manager, total_employess = self.check_manager(empl_id)
        all_empl_rec = []
        if check_manager:
            for check_employee_id in total_employess:
                all_empl_rec.append(
                    {
                        "name": check_employee_id.name,
                        "empl_id": check_employee_id.empl_id,
                        "date": date,
                        "leaves": self.employee_leaves_history(
                            check_employee_id.empl_id, date
                        ),
                    }
                )
            return {
                "status": 200,
                "success": True,
                "all_empl_leaves": all_empl_rec,
            }
        else:
            return {
                "status": 404,
                "success": False,
                "msg": _("Employee is not manager"),
            }

    @http.route(["/approve/leave"], type="json", auth="auth_bearer")
    def approve_leave(
        self, empl_id=None, leave_id=None, manager_id=None, **kw
    ):
        if self.is_leave_request_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Leave requests are currently hidden."),
            }

        if not empl_id and not leave_id:
            return {
                "status": 404,
                "access": False,
                "msg": _("Required fields are missing."),
            }
        get_employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        manager = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", manager_id)], limit=1)
        )
        if get_employee_id:
            apply_leaves = (
                request.env["hr.leave"]
                .sudo()
                .search(
                    [
                        ("employee_id", "=", get_employee_id.id),
                        ("state", "=", "confirm"),
                        ("id", "=", int(leave_id)),
                    ]
                )
            )
            try:
                if manager_id:
                    apply_leaves.action_approve_custom(
                        get_employee_id.parent_id.id
                    )
                else:
                    apply_leaves.action_approve_custom(get_employee_id.id)
                if apply_leaves.state == "validate1":
                    apply_leaves.action_validate()
                title = "Leave approved"
                body = "leave is approved by {}".format(manager.name)
                send_message = manager.send_message(
                    title,
                    body,
                    get_employee_id.address_home_id.id,
                    "user_notification",
                    "hr.leave",
                    apply_leaves.id,
                )
                manager.send_notification(
                    send_message.id,
                    "inbox",
                    get_employee_id.address_home_id.id,
                    False,
                )
                manager.push_notification(
                    empl_id, title, body
                )
                get_employee_id.send_email_notification(
                    get_employee_id.parent_id.empl_id, title, body
                )
                return {
                    "success": True,
                    "msg": _("Leave is approved successfully."),
                }
            except Exception as e:
                _logger.error("APPROVE LEAVE ERROR: {}".format(e))
                return {"success": False, "msg": _("Leave is not approved.")}

    @http.route(
        ["/cancel/leave"],
        type="json",
        auth="auth_bearer",
        csrf=False,
        methods=["POST"],
    )
    def cancel_leave(
        self, empl_id=None, leave_id=None, manager_id=None, reason=None, **kw
    ):
        if self.is_leave_request_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Leave requests are currently hidden."),
            }

        if not (empl_id and leave_id and reason):
            return {
                "status": 404,
                "access": False,
                "msg": _("Required fields are missing."),
            }
        get_employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if not manager_id:
            manager = get_employee_id.parent_id
        manager = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", manager_id)], limit=1)
        )
        if get_employee_id:
            apply_leaves = (
                request.env["hr.leave"]
                .sudo()
                .search(
                    [
                        ("employee_id", "=", get_employee_id.id),
                        ("state", "=", "confirm"),
                        ("id", "=", int(leave_id)),
                    ]
                )
            )
            if apply_leaves:
                if manager_id:
                    apply_leaves.write(
                        {"write_uid": get_employee_id.parent_id.user_id.id}
                    )
                    apply_leaves.refusal_reason = reason
                    apply_leaves.action_refuse_custom(
                        get_employee_id.parent_id.id
                    )
                else:
                    apply_leaves.action_refuse_custom(get_employee_id.id)
                title = "Leave refused"
                body = "Leave is refused by {}".format(manager.name)
                send_message = manager.send_message(
                    title,
                    body,
                    get_employee_id.address_home_id.id,
                    "user_notification",
                    "hr.leave",
                    apply_leaves.id,
                )
                manager.send_notification(
                    send_message.id,
                    "inbox",
                    get_employee_id.address_home_id.id,
                    False,
                )
                manager.push_notification(
                    empl_id, title, body
                )
                get_employee_id.send_email_notification(
                    get_employee_id.parent_id.empl_id, title, body
                )
                return {
                    "success": True,
                    "msg": _("leave is successfully cancel."),
                }
            else:
                return {
                    "success": False,
                    "msg": _("leave not found in confirm state."),
                }
        else:
            return {"success": False, "msg": _("Employee not found.")}

    @http.route(
        ["/leaves/history"],
        type="json",
        auth="auth_bearer",
        csrf=False,
        methods=["POST"],
    )
    def get_leaves_history(self, employee_id=None, leave_type_id=None):
        if self.is_leave_request_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Leave requests are currently hidden."),
            }

        if not employee_id:
            return {
                "status": 404,
                "access": False,
                "msg": _("Required fields are missing."),
            }
        check_employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", employee_id)])
        )
        if not check_employee_id:
            return {
                "status": 404,
                "success": False,
                "msg": _("employee id is Invalid."),
            }
        domain = [("employee_id", "=", int(check_employee_id.id))]
        if leave_type_id:
            domain += [("holiday_status_id", "=", int(leave_type_id))]
        leaves_history = request.env["hr.leave"].sudo().search(domain)
        leave_history_list = []
        for leave_history in leaves_history:
            leave_history_list.append(
                {
                    "id": leave_history.id,
                    "name": leave_history.holiday_status_id.name,
                    "time_off_type": leave_history.holiday_status_id.name,
                    "description": leave_history.name,
                    "start_date": leave_history.date_from,
                    "end_date": leave_history.date_to,
                    "duraction": leave_history.duration_display,
                    "status": leave_history.state,
                    "date": leave_history.request_date_from,
                    "refuse_reason": leave_history.refusal_reason,
                }
            )
        return {
            "status": 200,
            "success": True,
            "employee_name": check_employee_id.name,
            "empl_id": check_employee_id.empl_id,
            "leave_history": leave_history_list,
        }


######################
# Timesheet
######################


    def time_to_float(hour, minute):
        return float_round(hour + minute / 60, precision_digits=2)


# def float_to_time(duration):
#     hour = int(duration)
#     minute = (duration - int(duration)) * 60
#     temp = minute - int(minute)
#     if (temp * 2) >= 1:
#         minute = ceil(minute)
#     else:
#         minute = int(minute)
#     if hour == 0:
#         hour = "00"
#     elif 1 <= hour <= 9:
#         hour = "0" + str(hour)
#     if minute == 0:
#         minute = "00"
#     elif 1 <= minute <= 9:
#         minute = "0" + str(minute)
#     return "{}:{}".format(hour, minute)


class TimesheetApi(API_Hr_Attedance):
    def convert_tz(self, datetime, tz):
        return (
            utc.localize(datetime)
            .astimezone(timezone(tz or "UTC"))
            .replace(tzinfo=None)
        )

    def is_timesheet_hidden(self):
        """Checks if timesheets are hidden based on configuration."""
        timesheet_hidden = request.env["ir.config_parameter"].sudo().get_param(
            "geomarking_attendance_mobile_app_knk.timesheets_hide", default=False
        )
        return timesheet_hidden == "True"

    @http.route("/timesheet/history", type="json", auth="public")
    def timesheet_history(self, empl_id=None, **kw):
        # Check if timesheets are hidden
        if self.is_timesheet_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Timesheet functionality is currently hidden."),
            }

        if not empl_id:
            return {"success": False, "msg": _("Required fields is missing.")}
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )
        timsheet_list = []
        if employee_id:
            timsheets = (
                request.env["account.analytic.line"]
                .sudo()
                .search([("employee_id", "=", employee_id.id)])
            )
            for timsheet in timsheets:
                duration = str(float_to_time(timsheet.unit_amount))
                timsheet_list.append(
                    {
                        "id": timsheet.id,
                        "date": timsheet.date,
                        "employee": employee_id.name,
                        "project_id": {
                            "id": timsheet.project_id.id,
                            "name": timsheet.project_id.name,
                        },
                        "task_id": {
                            "id": timsheet.task_id.id,
                            "name": timsheet.task_id.name,
                        },
                        "description": timsheet.name,
                        "duration": duration[0:5],
                    }
                )
        else:
            return {"success": False, "msg": _("Employee not found.")}
        return {"success": True, "project": timsheet_list}

    @http.route("/get/project", type="json", auth="auth_bearer")
    def get_project(self, empl_id=None, **kw):
        # Check if timesheets are hidden
        if self.is_timesheet_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Timesheet functionality is currently hidden."),
            }

        if not empl_id:
            return {"success": False, "msg": _("Required fields is missing.")}
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", int(empl_id))])
        )
        project_list = []
        if employee_id:
            employee_tasks = request.env["project.task"].sudo().search(
                [("user_ids", "in", employee_id.user_id.ids)]
            )
            employee_projects = employee_tasks.project_id
            for employee_project in employee_projects:
                project_list.append(
                    {"id": employee_project.id, "name": employee_project.name}
                )
        else:
            return {"success": False, "msg": _("Employee not found.")}
        return {"success": True, "project": project_list}

    @http.route("/get/task", type="json", auth="auth_bearer")
    def get_task(
        self,
        model,
        fields=False,
        offset=0,
        limit=False,
        domain=None,
        sort=None,
        project_id=None,
        **kw
    ):
        # Check if timesheets are hidden
        if self.is_timesheet_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Timesheet functionality is currently hidden."),
            }

        domain = []
        if project_id:
            domain += [["project_id", "=", int(project_id)]]
        record = self.task_search_read(
            model, fields, offset, limit, domain, sort
        )
        updict = {"success": True}
        updict.update(record)
        return updict

    def task_search_read(
        self,
        model,
        fields=False,
        offset=False,
        limit=False,
        domain=None,
        sort=None,
    ):
        # Check if timesheets are hidden
        if self.is_timesheet_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Timesheet functionality is currently hidden."),
            }

        Model = request.env[model].sudo()
        return Model.web_search_read(
            domain, fields, offset=offset, limit=limit, order=sort
        )

    @http.route(["/apply/timesheet"], type="json", auth="public")
    def ts_create(
        self,
        empl_id=None,
        project_id=None,
        task_id=None,
        date=None,
        description=None,
        duration=None,
        **kw
    ):
        # Check if timesheets are hidden
        if self.is_timesheet_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Timesheet functionality is currently hidden."),
            }

        if not (empl_id and project_id and date):
            return {"success": False, "msg": _("Required fields is missing.")}
        project_rec = request.env["project.project"].browse(int(project_id))
        employee_id = request.env["hr.employee"].search(
            [("empl_id", "=", int(empl_id))]
        )
        task_rec = False
        if task_id:
            task_rec = request.env["project.task"].browse(int(task_id))
        if not employee_id:
            return {"success": False, "msg": _("Employee not found.")}
        try:
            date_f = check_dateformat(date)
            date = convert_dateformat(date_f, date)
            duration_l = duration.split(":")
            vals = {
                "employee_id": employee_id.id,
                # 'user_id': employee_id.user_id.id if employee_id.user_id else False,
                "project_id": project_rec.id if project_rec else False,
                "task_id": task_rec.id if task_rec else False,
                "date": date,
                "unit_amount": time_to_float(int(duration_l[0]), int(duration_l[1])),
                "name": description,
            }
            record = request.env["account.analytic.line"].sudo().create(vals)
            return {
                "success": True,
                "id": record.id,
                "employee_name": record.employee_id.name,
                "project_name": record.project_id.name,
                "task_name": record.task_id.name,
                "date": record.date,
                "description": record.name,
                "duration": record.unit_amount,
            }
        except Exception as e:
            _logger.error('APPLY TIMESHEET ERROR: {}'.format(e))
            raise ValidationError(_("You cannot add Alphabets in Duration."))

    @http.route(["/edit/timesheet"], type="json", auth="public")
    def ts_edit(
        self,
        id=None,
        project_id=None,
        task_id=None,
        date=None,
        duration=None,
        description=None,
        **kw
    ):
        # Check if timesheets are hidden
        if self.is_timesheet_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Timesheet functionality is currently hidden."),
            }

        if not id:
            return {"success": False, "msg": _("Required fields is missing.")}
        timesheet_rec = (
            request.env["account.analytic.line"]
            .sudo()
            .search([("id", "=", id)])
        )
        try:
            date_f = check_dateformat(date)
            date = convert_dateformat(date_f, date)
            duration_l = duration.split(':')
            vals = {
                "date": date,
                "unit_amount": time_to_float(int(duration_l[0]), int(duration_l[1])),
                "name": description,
            }
            if project_id:
                if timesheet_rec.project_id.id != project_id:
                    vals["project_id"] = project_id
                    if not task_id:
                        return {
                            "success": False,
                            "msg": _("Task id is required."),
                        }
                    task_rec = request.env["project.task"].search(
                        [("project_id", "=", project_id)]
                    )
                    if task_id in task_rec.ids:
                        vals["task_id"] = task_id
                    else:
                        return {
                            "success": False,
                            "msg": _("Task is not found."),
                        }
            record = timesheet_rec.write(vals)
            if record:
                return {
                    "success": True,
                    "id": id,
                    "date": timesheet_rec.date,
                    "project_name": timesheet_rec.project_id.name,
                    "task_name": timesheet_rec.task_id.name,
                    "duration": timesheet_rec.unit_amount,
                    "description": timesheet_rec.name,
                    "msg": _("Record is successfully updated."),
                }
        except Exception as e:
            _logger.error("EDIT TIMESHEET ERROR: {}".format(e))
            raise ValidationError(_("You cannot add Alphabets in Duration."))

    @http.route(["/delete/timesheet"], type="json", auth="public")
    def ts_delete(self, timesheet_id=None, **kw):
        # Check if timesheets are hidden
        if self.is_timesheet_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Timesheet functionality is currently hidden."),
            }

        if not timesheet_id:
            return {
                "success": False,
                "msg": _("Some Required Fields are Missing."),
            }
        timesheet_rec = (
            request.env["account.analytic.line"]
            .sudo()
            .search([("id", "=", int(timesheet_id))])
        )
        if not timesheet_rec:
            return {"success": False, "msg": _("Record not found.")}
        timesheet_rec.unlink()
        return {
            "success": True,
            "msg": _(
                "Record {} is successfully deleted.".format(timesheet_id)
            ),
        }

    def employee_timesheets(self, empl_id, date):   # Date Format : DD-MM-YYYY
        # Check if timesheets are hidden
        if self.is_timesheet_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Timesheet functionality is currently hidden."),
            }

        if not empl_id:
            return {"success": False, "msg": _("Required fields is missing.")}
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )
        timsheet_list = []
        if employee_id:
            timsheets = (
                request.env["account.analytic.line"]
                .sudo()
                .search(
                    [("employee_id", "=", employee_id.id), ("date", "=", date)]
                )
            )
            for timsheet in timsheets:
                timsheet_list.append(
                    {
                        "id": timsheet.id,
                        "date": timsheet.date,
                        "employee": employee_id.name,
                        "project_id": {
                            "id": timsheet.project_id.id,
                            "name": timsheet.project_id.name,
                        },
                        "task_id": {
                            "id": timsheet.task_id.id,
                            "name": timsheet.task_id.name,
                        },
                        "description": timsheet.name,
                        "duration": str(timsheet.unit_amount).replace(
                            ".", ":"
                        ),
                    }
                )
        else:
            return {"success": False, "msg": _("Record not found.")}
        return {"success": True, "project": timsheet_list}

    @http.route(["/show/all/timesheets"], type="json", auth="public")
    def show_all_timesheets(
        self, date=None, empl_id=None, **kw
    ):  # Date Format : DD-MM-YYYY
        # Check if timesheets are hidden
        if self.is_timesheet_hidden():
            return {
                "status": 403,
                "success": False,
                "msg": _("Timesheet functionality is currently hidden."),
            }
        check_manager, total_employess = self.check_manager(empl_id)
        if check_manager:
            employee_rec_list = []
            for empl_record in total_employess:
                timesheet_history = self.employee_timesheets(
                    empl_record.empl_id, date
                )
                employee_rec_list.append(
                    {
                        "name": empl_record.name,
                        "date": date,
                        "empl_id": empl_record.empl_id,
                        "timsheet_records": timesheet_history,
                    }
                )

            return {"success": True, "result": employee_rec_list}
        return {"success": False, "msg": _("Employee is not manager.")}


    @http.route(
        ["/update/firebase/token/employee"],
        type="json",
        methods=["POST"],  # Correctly specify the HTTP method
        auth="public",  # Adjust to 'user' if authentication is needed
    )
    def update_firebase_token_to_user(self, empl_id=None, **kw):
        if not empl_id:
            return {"status": "error", "error_msg": "Employee ID is required!"}
    
        # Search for the employee using the given employee ID
        employee = request.env["hr.employee"].sudo().search([("empl_id", "=", empl_id)], limit=1)
    
        if not employee:
            return {"status": "error", "error_msg": "No employee found!"}
    
        # Update the employee's Firebase token
        firebase_token = kw.get("firebase_token")
        if not firebase_token:
            return {"status": "error", "error_msg": "Firebase token is required!"}
    
        employee.sudo().write({"firebase_token": firebase_token})
        return {
            "status": "success",
            "empl_id": employee.empl_id,
            "firebase_token": employee.firebase_token,
        }
    # @http.route(
    #     ["/update/firebase/token/employee"],
    #     type="json",
    #     method="POST",
    #     auth="public",
    # )
    # def update_firebase_token_to_uset(self, empl_id=None, **kw):
    #     if empl_id:
    #         employee_id = request.env["hr.employee"].sudo().search([("empl_id", "=", empl_id)],limit=1)
    #
    #         if not employee_id:
    #             return {"status": "error", "error_msg": "No employee found !"}
    #
    #         firebase_token = kw.get("firebase_token")
    #         if not firebase_token:
    #             return {"status": "error", "error_msg": "Firebase token is required!"}
    #
    #         employee.sudo().write({"firebase_token": firebase_token})
    #
    #         # employee_id.sudo().write(
    #         #     {"firebase_token": kw.get("firebase_token")}
    #         # )
    #         return {
    #             "success": True,
    #             "empl_id": employee_id.empl_id,
    #             "firebase_token": employee_id.firebase_token,
    #         }

    @http.route(
        "/api/all/notifications",
        type="json",
        auth="auth_bearer",
        methods=["POST"],
    )
    def get_all_notification(self, empl_id=None, **kwargs):
        model = request.env["mail.notification"]
        # today_date = datetime.today()
        # before_one_week = today_date - timedelta(days=6)
        employee_id = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )

        notifications = model.sudo().search(
            [
                ("is_app", "=", True),
                ("res_partner_id", "=", employee_id.address_home_id.id),
            ]
        )
        notifications = notifications.filtered(
            lambda x: x.mail_message_id.create_date.date()
            >= (datetime.today() - timedelta(days=7)).date()
        )
        notification_list = []
        base_url = employee_id.sudo().get_base_url()
        for notification in notifications[::-1]:
            curr_leave = (
                request.env["hr.leave"]
                .sudo()
                .search([("id", "=", notification.mail_message_id.res_id)])
            )
            type_name = ""
            if notification.mail_message_id.model == "account.analytic.line":
                type_name = "timsheet"
            elif notification.mail_message_id.model == "hr.leave":
                type_name = "leave"
            notification_list.append(
                {
                    "id": notification.id,
                    "type": type_name,
                    "name": notification.mail_message_id.subject,
                    "message_id": notification.mail_message_id.id,
                    "is_read": notification.is_read,
                    "body": notification.mail_message_id.body,
                    "date": notification.mail_message_id.date.date(),
                    "time": notification.mail_message_id.date.time(),
                    "datetime": notification.mail_message_id.date,
                    "display_name": notification.mail_message_id.display_name,
                    "request_date_from": curr_leave.request_date_from,
                    "description": curr_leave.name,
                    "profile_pic": base_url
                    + "/web/image?model=hr.employee&id=%s&field=image_1920"
                    % employee_id.id,
                }
            )
        return {"success": True, "result": notification_list}

    @http.route(
        "/api/read/notification",
        type="json",
        auth="auth_bearer",
        methods=["POST"],
    )
    def read_notification(self, notification_id=None, is_read=None, **kwargs):
        model = request.env["mail.notification"]
        notification = model.search([("id", "=", notification_id)])
        notification.sudo().write({"is_read": True})

        return {
            "success": True,
            "id": notification_id,
            "is_read": notification.is_read,
        }

    # @http.route("/check/employee/in/out", type="json", auth="auth_bearer")
    # def check_employee_in_out(self, empl_id=None, **kwargs):
    #     if not empl_id:
    #         return {
    #             "success": False,
    #             "msg": "Please provide the required fields: empl_id.",
    #         }
    #
    #     employee = (
    #         request.env["hr.employee"]
    #         .sudo()
    #         .search([("empl_id", "=", empl_id)])
    #     )
    #     if not employee:
    #         return {
    #             "sucess": False,
    #             "msg": "Please provide the correct empl_id.",
    #         }
    #
    #     attendance_domain = [
    #         ("employee_id", "=", employee.id),
    #         ("check_out", "=", False),
    #         ("check_in", "!=", False),
    #     ]
    #     attendance = (
    #         request.env["hr.attendance"]
    #         .sudo()
    #         .search(attendance_domain, order="check_in", limit=1)
    #     )
    #     hr_manager_id = request.env['ir.config_parameter'].sudo().get_param("geomarking_attendance_mobile_app_knk.hr_manager")
    #     alternative_hr_manager_id = request.env['ir.config_parameter'].sudo().get_param("geomarking_attendance_mobile_app_knk.alternative_hr_manager")
    #     on_leave = request.env['ir.config_parameter'].sudo().get_param("geomarking_attendance_mobile_app_knk.on_leave")
    #     flag = False
    #     if (not on_leave and employee.id == int(hr_manager_id)) or (on_leave and employee.id == int(alternative_hr_manager_id)):
    #         flag = True
    #     if attendance:
    #         return {
    #             "success": True,
    #             "check_in": True,
    #             "employee": employee.name,
    #             "empl_id": empl_id,
    #             "check_in_time": attendance.check_in,
    #             "hr_manager": flag,
    #         }
    #     else:
    #         return {
    #             "success": True,
    #             "check_in": False,
    #             "empl_id": empl_id,
    #             "employee_name": employee.name,
    #             "hr_manager": flag,
    #         }

    @http.route("/check/employee/in/out", type="json", auth="auth_bearer")
    def check_employee_in_out(self, empl_id=None, **kwargs):
        _logger.info("🔍 API called: /check/employee/in/out")
        _logger.info(f"📥 Received empl_id: {empl_id}")

        if not empl_id:
            _logger.warning("❌ Missing empl_id in request")
            return {
                "success": False,
                "msg": "Please provide the required fields: empl_id.",
            }

        employee = request.env["hr.employee"].sudo().search([("empl_id", "=", empl_id)], limit=1)
        _logger.info(f"👤 Employee search result: {employee.name if employee else 'Not Found'}")

        if not employee:
            _logger.warning("❌ No employee found with given empl_id")
            return {
                "success": False,
                "msg": "Please provide the correct empl_id.",
            }

        # ✅ Only fetch today's check-in
        today = fields.Date.today()
        start_dt = fields.Datetime.from_string(f"{today} 00:00:00")
        end_dt = fields.Datetime.from_string(f"{today} 23:59:59")
        _logger.info(f"📅 Filtering attendance between {start_dt} and {end_dt}")

        attendance_domain = [
            ("employee_id", "=", employee.id),
            ("check_out", "=", False),
            ("check_in", ">=", start_dt),
            ("check_in", "<=", end_dt),
        ]

        attendance = request.env["hr.attendance"].sudo().search(attendance_domain, limit=1)
        _logger.info(f"📄 Attendance found: {'Yes' if attendance else 'No'}")

        # Optional HR Manager check
        hr_manager_id = request.env['ir.config_parameter'].sudo().get_param(
            "geomarking_attendance_mobile_app_knk.hr_manager")
        alternative_hr_manager_id = request.env['ir.config_parameter'].sudo().get_param(
            "geomarking_attendance_mobile_app_knk.alternative_hr_manager")
        on_leave = request.env['ir.config_parameter'].sudo().get_param("geomarking_attendance_mobile_app_knk.on_leave")

        _logger.info(
            f"🧑‍💼 HR Manager ID: {hr_manager_id}, Alternative: {alternative_hr_manager_id}, On Leave: {on_leave}")

        flag = False
        if (not on_leave and employee.id == int(hr_manager_id)) or (
                on_leave and employee.id == int(alternative_hr_manager_id)
        ):
            flag = True
        _logger.info(f"✅ HR Manager Flag: {flag}")

        if attendance:
            response = {
                "success": True,
                "check_in": True,
                "employee": employee.name,
                "empl_id": empl_id,
                "check_in_time": attendance.check_in,
                "hr_manager": flag,
            }
            _logger.info("✅ Returning check_in: True")
            return response
        else:
            response = {
                "success": True,
                "check_in": False,
                "empl_id": empl_id,
                "employee_name": employee.name,
                "hr_manager": flag,
            }
            _logger.info("ℹ️ Returning check_in: False")
            return response

    # @http.route("/check/employee/in/out", type="json", auth="auth_bearer")
    # def check_employee_in_out(self, empl_id=None, **kwargs):
    #     if not empl_id:
    #         return {
    #             "success": False,
    #             "msg": "Please provide the required fields: empl_id.",
    #         }
    #
    #     employee = request.env["hr.employee"].sudo().search([("empl_id", "=", empl_id)], limit=1)
    #     if not employee:
    #         return {
    #             "success": False,
    #             "msg": "Please provide the correct empl_id.",
    #         }
    #
    #     # ✅ Only fetch today's check-in
    #     today = fields.Date.today()
    #     loggin
    #     attendance_domain = [
    #         ("employee_id", "=", employee.id),
    #         ("check_out", "=", False),
    #         ("check_in", ">=", fields.Datetime.from_string(f"{today} 00:00:00")),
    #         ("check_in", "<=", fields.Datetime.from_string(f"{today} 23:59:59")),
    #     ]
    #
    #     attendance = request.env["hr.attendance"].sudo().search(attendance_domain, limit=1)
    #
    #     # Optional HR Manager check
    #     hr_manager_id = request.env['ir.config_parameter'].sudo().get_param(
    #         "geomarking_attendance_mobile_app_knk.hr_manager")
    #     alternative_hr_manager_id = request.env['ir.config_parameter'].sudo().get_param(
    #         "geomarking_attendance_mobile_app_knk.alternative_hr_manager")
    #     on_leave = request.env['ir.config_parameter'].sudo().get_param("geomarking_attendance_mobile_app_knk.on_leave")
    #
    #     flag = False
    #     if (not on_leave and employee.id == int(hr_manager_id)) or (
    #             on_leave and employee.id == int(alternative_hr_manager_id)):
    #         flag = True
    #
    #     if attendance:
    #         return {
    #             "success": True,
    #             "check_in": True,
    #             "employee": employee.name,
    #             "empl_id": empl_id,
    #             "check_in_time": attendance.check_in,
    #             "hr_manager": flag,
    #         }
    #     else:
    #         return {
    #             "success": True,
    #             "check_in": False,
    #             "empl_id": empl_id,
    #             "employee_name": employee.name,
    #             "hr_manager": flag,
    #         }

    @http.route("/get/removal/request/reason", type="json", auth="auth_bearer")
    def get_removal_request_reason(
        self, reason_id=None, empl_id=None, **kwargs
    ):
        domain = []
        if reason_id:
            reason = (
                request.env["removal.request.reason"]
                .sudo()
                .search([("id", "=", int(reason_id))])
            )
            if not reason:
                return {
                    "success": False,
                    "msg": "Please provide the correct reason_id.",
                }
            domain += [("id", "=", int(reason_id))]
        employee = False
        if empl_id:
            employee = (
                request.env["hr.employee"]
                .sudo()
                .search([("empl_id", "=", empl_id)])
            )

        reasons = request.env["removal.request.reason"].sudo().search(domain)

        result = [
            {
                "id": reason.id,
                "name": reason.name,
            }
            for reason in reasons
        ]

        return {
            "success": True,
            "result": result,
            "password": employee.password if employee else False,
        }

    @http.route(
        "/submit/account/removal/request", type="json", auth="auth_bearer"
    )
    def submit_account_removal_request(
        self,
        empl_id=None,
        reason_id=None,
        description=None,
        reason=None,
        **kwargs
    ):
        if not (empl_id and reason_id):
            return {
                "success": False,
                "msg": "Please provide the required fields: empl_id, reason_id",
            }

        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )
        req_reason = (
            request.env["removal.request.reason"]
            .sudo()
            .search([("id", "=", int(reason_id))])
        )
        if not employee:
            return {
                "success": False,
                "msg": "Please provide the correct empl_id.",
            }

        if not req_reason:
            return {
                "success": False,
                "msg": "Please provide the correct reason_id.",
            }

        if req_reason.name == "Others":
            if not reason:
                return {
                    "success": False,
                    "msg": "Please provide reason as you have selected Others.",
                }

        values = {
            "employee_id": employee.id,
            "empl_id": employee.empl_id,
            "reason_id": req_reason.id,
            "request_submission_date": fields.Date.today(),
            "description": description if description else False,
            "note": reason if reason else False,
        }

        try:
            removal_request = (
                request.env["account.removal.request"].sudo().create(values)
            )
            return {
                "success": True,
                "msg": "Your request has been submitted. We 'll take action in 24 hours.",
                "result": {
                    "id": removal_request.id,
                    "name": removal_request.name,
                    "state": removal_request.state,
                },
            }
        except Exception as e:
            _logger.warning("*&*&*&* REMOVAL REQUEST ERROR: {}".format(e))

    @http.route("/api/face/optional", type="json", auth="auth_bearer")
    def api_face_optional(self, empl_id=None, **kwargs):
        if not empl_id:
            return {"success": False, "msg": "Please provide the employee_id"}
        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if not employee:
            return {
                "success": False,
                "msg": "Please provide the correct employee id",
            }
        return {"success": True, "face_data": employee.is_face}

    @http.route("/api/wfh/optional", type="json", auth="auth_bearer")
    def api_wfh_optional(self, empl_id=None, **kwargs):
        if not empl_id:
            return {"success": False, "msg": "Please provide the employee_id"}
        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)], limit=1)
        )
        if not employee:
            return {
                "success": False,
                "msg": "Please provide the correct employee id",
            }
        return {"success": True, "wfh_data": employee.is_wfh}

    @http.route(
        "/get/employee/public/holidays", type="json", auth="auth_bearer"
    )
    def get_employee_public_holiday(self, **kwargs):
        records = [
            {
                "name": holiday.name,
                "date": holiday.date_from.date(),
            }
            for holiday in request.env["resource.calendar.leaves"]
            .sudo()
            .search([("resource_id", "=", False)])
        ]

        return {"success": True, "result": records}

    @http.route("/set/picture", type="json", auth="auth_bearer")
    def set_picture(self, empl_id=None, image_data=None, **kwargs):
        if not (empl_id and image_data):
            return {
                "success": False,
                "msg": "Please provide the required fields: empl_id, base64",
            }
        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )

        if not employee:
            return {
                "success": False,
                "msg": "Please provide the correct empl_id.",
            }

        employee.image_authentication = image_data["bitmap"]
        employee.image_unique = image_data["imageType"]

        return {"success": True, "msg": "Image has been setted up."}

    @http.route("/get/picture", type="json", auth="auth_bearer")
    def get_picture(self, empl_id=None, **kwargs):
        if not (empl_id):
            return {"success": False, "msg": "Please provide the empl_id."}

        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )

        if not employee:
            return {
                "success": False,
                "msg": "Please provide the correct empl_id.",
            }
        return {
            "success": True,
            "result": {
                "bitmap": employee.image_authentication,
                "imageType": employee.image_unique,
            },
        }

    @http.route("/get/manager/employees", type="json", auth="auth_bearer")
    def get_manager_employees(self, empl_id=None, **kwargs):
        if not (empl_id):
            return {"success": False, "msg": "Please provide the empl_id."}

        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )

        if not employee:
            return {
                "success": False,
                "msg": "Please provide the correct empl_id.",
            }

        records = [
            {
                "name": empl.name,
                "empl_id": empl.empl_id,
            }
            for empl in employee.child_ids
        ]

        return {"success": True, "result": records}

    @http.route("/get/employee/timezone", type="json", auth="auth_bearer")
    def get_employee_timezone(self, empl_id=None, **kwargs):
        if not (empl_id):
            return {"success": False, "msg": "Please provide the empl_id."}

        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )

        if not employee:
            return {
                "success": False,
                "msg": "Please provide the correct empl_id.",
            }
        utc_time = datetime.now(timezone("UTC"))
        employee_time = utc_time.astimezone(timezone(employee.tz))
        difference_time_float = (
            employee_time.replace(tzinfo=None) - utc_time.replace(tzinfo=None)
        ).seconds / 3600
        difference_time = "+" + str(float_to_time(difference_time_float))
        # difference_time = "+18:00"
        return {"success": True, "result": difference_time}

    ######################
    # ATTENDANCE REQUEST
    ######################

    @http.route("/get/employee/attendance", type="json", auth="auth_bearer")
    def get_employee_attendance(self, empl_id=None, **kwargs):
        if not empl_id:
            return {
                "success": False,
                "msg": "Please provide the required fields: empl_id",
            }

        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )

        if not employee:
            return {
                "success": False,
                "msg": "Please Provide the correct empl_id",
            }

        return {
            "success": True,
            "result": [
                {
                    "name": "{} to {}".format(
                        self.convert_tz(attendance.check_in, employee.tz) if attendance.check_in else False, self.convert_tz(attendance.check_out, employee.tz) if attendance.check_out else False
                    ),
                    "id": attendance.id,
                }
                for attendance in request.env["hr.attendance"]
                .sudo()
                .search(
                    [("employee_id", "=", employee.id)]
                )
            ],
        }

    def convert_tz_utc(self, datetime, tz):
        return (
            timezone(tz).localize(datetime)
            .astimezone(utc)
            .replace(tzinfo=None)
        )

    @http.route("/attendance/request/create", type="json", auth="auth_bearer")
    def create_attenance_request(
        self,
        empl_id=None,
        request_type=None,
        check_in_datetime=None,
        check_out_datetime=None,
        reason=None,
        attendance_id=None,
        date=None,
        **kwargs
    ):
        if not (empl_id and request_type and reason):
            return {
                "success": False,
                "msg": "Please Provide the required fields: empl_id-{}, request_type-{}, reason-{}".format(
                    empl_id, request_type, reason
                ),
            }

        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )

        if not employee:
            return {
                "success": False,
                "msg": "Please provide the correct value of empl_id.",
            }
        _logger.warning('ATTENDANCE REQUEST ERROR: {}'.format(request_type))
        if request_type not in ["check_in", "check_out", "both"]:
            return {
                "success": False,
                "msg": "Please provide the correct request_type: check_in/check_out/both",
            }

        attendance_request_limit = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "geomarking_attendance_mobile_app_knk.attendance_requests_limit"
            )
        )
        attendance_request = False

        employee_att_req = (
            request.env["attendance.request"]
            .sudo()
            .search(
                [
                    ("employee_id", "=", employee.id),
                    ("state", "in", ("draft", "approve")),
                ]
            )
        )
        if len(
            employee_att_req.filtered(
                lambda x: x.create_date.date() == fields.Date.today()
            )
        ) >= int(attendance_request_limit):
            return {
                "success": False,
                "msg": "The attedance request limit has been reached",
            }

        if request_type != "both":
            if not (check_in_datetime or check_out_datetime):
                return {
                    "success": False,
                    "msg": "Please provide check_in_datetime or check_out_datetime if you are selecting 'both' as a request_type.",
                }

            if not attendance_id:
                return {
                    "success": False,
                    "msg": "Please provide attendance_id if you are selecting 'both' as request_type.",
                }

            attendance = (
                request.env["hr.attendance"]
                .sudo()
                .search([("id", "=", int(attendance_id))])
            )
            if not attendance:
                return {
                    "success": False,
                    "msg": "Please provide the correct value of attendance.",
                }

            if request_type == "check_in":
                if not check_in_datetime:
                    return {
                        "success": False,
                        "msg": "Please Select check in time.",
                    }
                checkInDatetime = datetime.strptime(
                    check_in_datetime, "%H:%M:%S"
                )

                if not attendance.check_in:
                    return {
                        "success": False,
                        "msg": "Attendance doesn't have check_in.",
                    }
                attendance_request = (
                    request.env["attendance.request"]
                    .sudo()
                    .create(
                        {
                            "check_in_datetime": self.convert_tz_utc(datetime.combine(
                                attendance.check_in.date(),
                                checkInDatetime.time(),
                            ), employee.tz),
                            "request_type": request_type,
                            "reason": reason,
                            "employee_id": employee.id,
                            "attendance_id": attendance.id,
                        }
                    )
                )

            elif request_type == "check_out":
                if not check_out_datetime:
                    return {
                        "success": False,
                        "msg": "Please Select check out time.",
                    }
                checkOutDatetime = datetime.strptime(
                    check_out_datetime, "%H:%M:%S"
                )

                if not attendance.check_out:
                    return {
                        "success": False,
                        "msg": "Attendance doesn't have check_out.",
                    }

                attendance_request = (
                    request.env["attendance.request"]
                    .sudo()
                    .create(
                        {
                            "check_out_datetime": self.convert_tz_utc(datetime.combine(
                                attendance.check_out.date(),
                                checkOutDatetime.time(),
                            ), employee.tz),
                            "request_type": request_type,
                            "reason": reason,
                            "employee_id": employee.id,
                            "attendance_id": attendance.id,
                        }
                    )
                )

        else:
            if not (check_in_datetime and check_out_datetime and date):
                return {
                    "success": False,
                    "msg": "Please provide check_in_datetime, check_out_datetime and date if you are selecting 'both' as a request_type.",
                }

            checkInDatetime = datetime.strptime(check_in_datetime, "%H:%M:%S")
            checkOutDatetime = datetime.strptime(
                check_out_datetime, "%H:%M:%S"
            )
            required_date = datetime.strptime(date, "%d/%m/%Y")

            attendance_request = (
                request.env["attendance.request"]
                .sudo()
                .create(
                    {
                        "check_in_datetime": self.convert_tz_utc(datetime.combine(
                            required_date.date(), checkInDatetime.time()
                        ), employee.tz),
                        "check_out_datetime": self.convert_tz_utc(datetime.combine(
                            required_date.date(), checkOutDatetime.time()
                        ), employee.tz),
                        "request_type": request_type,
                        "reason": reason,
                        "employee_id": employee.id,
                    }
                )
            )

        return {
            "success": True,
            "msg": "Request has been created.",
            "result": {
                "attendance_request": [
                    attendance_request.id,
                    attendance_request.name,
                ]
            },
        }

    ATTENDANCE_REQUEST_TYPE = {
        "check_in": "Check-In",
        "check_out": "Check-Out",
        "both": "Both",
    }
    ATTENDANCE_STATUS = {
        "draft": "Draft",
        "approve": "Approved",
        "reject": "Rejected",
        "cancel": "Cancelled",
    }
    MONTHS = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }

    @http.route("/attendance/request/get", type="json", auth="auth_bearer")
    def get_attenance_request(
        self,
        empl_id=None,
        manager=False,
        month=None,
        year=None,
        status="draft",
        hr_manager=False,
        **kwargs
    ):
        if not empl_id:
            return {
                "success": False,
                "msg": "Please provide the required fields: empl_id",
            }

        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )

        if not employee:
            return {
                "success": False,
                "msg": "Please Provide the correct empl_id",
            }
        attendance_request_domain = [("employee_id", "=", employee.id)]
        if manager:
            attendance_request_domain = [
                ("employee_id", "in", employee.subordinate_ids.ids)
            ]
        hr_manager_id = request.env['ir.config_parameter'].sudo().get_param("geomarking_attendance_mobile_app_knk.hr_manager")
        alternative_hr_manager_id = request.env['ir.config_parameter'].sudo().get_param("geomarking_attendance_mobile_app_knk.alternative_hr_manager")
        on_leave = request.env['ir.config_parameter'].sudo().get_param("geomarking_attendance_mobile_app_knk.on_leave")
        flag = False
        if (not on_leave and employee.id == int(hr_manager_id)) or (on_leave and employee.id == int(alternative_hr_manager_id)):
            flag = True
        # breakpoint()
        if ((manager and flag) or (not manager and not flag)) and hr_manager:
            attendance_request_domain = [('im_manager_approval', '=', True)]
        else:
            attendance_request_domain += [('im_manager_approval', '=', False)]
        attendance_requests = (
            request.env["attendance.request"]
            .sudo()
            .search(attendance_request_domain)
        )
        if manager and hr_manager and not flag:
            attendance_requests = attendance_requests.filtered(lambda x: x.employee_id == employee.id)

        if month and year:
            if month not in self.MONTHS.keys():
                return {
                    "success": False,
                    "msg": "Please provide the correct months name: {}".format(
                        self.MONTHS.keys()
                    ),
                }
            attendance_requests = attendance_requests.filtered(
                lambda x: x.create_date.month == self.MONTHS[month]
                and x.create_date.year == year
            )
        if status:
            attendance_requests = attendance_requests.filtered(
                lambda x: x.state == status
            )
        result = []
        for employee in attendance_requests.employee_id:
            result.append(
                {
                    "employee_name": employee.name,
                    "empl_id": employee.empl_id,
                    "requests": [
                        {
                            "name": att_req.name,
                            "id": att_req.id,
                            "request_type": self.ATTENDANCE_REQUEST_TYPE[
                                att_req.request_type
                            ],
                            "reason": att_req.reason,
                            "date": att_req.create_date.date(),
                            "state": self.ATTENDANCE_STATUS[att_req.state],
                            "request_on": self.convert_tz(
                                att_req.create_date, employee.tz
                            ),
                            "approve_reject_on": self.convert_tz(
                                att_req.approve_reject_datetime, employee.tz
                            )
                            if att_req.approve_reject_datetime
                            else False,
                            "cancelled_on": self.convert_tz(
                                att_req.cancelled_datetime, employee.tz
                            )
                            if att_req.cancelled_datetime
                            else False,
                            "check_in": self.convert_tz(att_req.check_in_datetime, employee.tz).strftime(
                                "%H:%M:%S"
                            )
                            if att_req.check_in_datetime
                            else self.convert_tz(att_req.attendance_id.check_in, employee.tz).strftime(
                                "%H:%M:%S"
                            )
                            if att_req.attendance_id.check_in
                            else False,
                            "check_out": self.convert_tz(att_req.check_out_datetime, employee.tz).strftime(
                                "%H:%M:%S"
                            )
                            if att_req.check_out_datetime
                            else self.convert_tz(att_req.attendance_id.check_out, employee.tz).strftime(
                                "%H:%M:%S"
                            )
                            if att_req.attendance_id.check_out
                            else False,
                            "reject_reason": att_req.reject_reason,
                        }
                        for att_req in attendance_requests.filtered(
                            lambda x: x.employee_id.id == employee.id
                        )
                    ],
                }
            )

        # breakpoint()
        return {"success": True, "result": result}

    @http.route("/attendance/request/approve", type="json", auth="auth_bearer")
    def approve_attenance_request(self, request_id=None, **kwargs):
        if not request_id:
            return {
                "success": False,
                "msg": "Please provide the required fields: request_id",
            }

        attendance_request = (
            request.env["attendance.request"]
            .sudo()
            .search([("id", "=", int(request_id))])
        )

        if not attendance_request:
            return {
                "success": False,
                "msg": "Please provide the correct value of request_id.",
            }
        try:
            if attendance_request.im_manager_approval:
                attendance_request.approve_request()
            else:
                attendance_request.im_manager_approval = True
        except Exception as e:
            return {"success": False, "msg": e}

        return {
            "success": True,
            "msg": "{} Request has been approved.".format(
                attendance_request.name
            ),
        }

    @http.route("/attendance/request/reject", type="json", auth="auth_bearer")
    def reject_attenance_request(self, request_id=None, reason=None, **kwargs):
        if not (request_id and reason):
            return {
                "success": False,
                "msg": "Please provide the required fields: request_id, reason",
            }

        attendance_request = (
            request.env["attendance.request"]
            .sudo()
            .search([("id", "=", int(request_id))])
        )

        if not attendance_request:
            return {
                "success": False,
                "msg": "Please provide the correct value of request_id.",
            }
        try:
            attendance_request.reject_reason = reason
            attendance_request.reject_request()
        except Exception as e:
            return {"success": False, "msg": e}

        return {
            "success": True,
            "msg": "{} Request has been rejected.".format(
                attendance_request.name
            ),
        }

    @http.route("/attendance/request/cancel", type="json", auth="auth_bearer")
    def cancel_attenance_request(self, request_id=None, **kwargs):
        if not request_id:
            return {
                "success": False,
                "msg": "Please provide the required fields: request_id",
            }

        attendance_request = (
            request.env["attendance.request"]
            .sudo()
            .search([("id", "=", int(request_id))])
        )

        if not attendance_request:
            return {
                "success": False,
                "msg": "Please provide the correct value of request_id.",
            }
        try:
            attendance_request.cancel_request()
        except Exception as e:
            return {"success": False, "msg": e}

        return {
            "success": True,
            "msg": "{} Request has been canceled.".format(
                attendance_request.name
            ),
        }


class PayslipAPI(http.Controller):

    MONTHS = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    @http.route(
        ["/download/employee/payslip"],
        type="json",
        auth="auth_bearer",
        csrf=False,
    )
    def download_employee_payslip(
        self, empl_id=None, month=None, year=None, **kw
    ):
        if not (empl_id and month and year):
            return {
                "success": False,
                "msg": "Please provide empl_id, month and year.",
            }
        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([("empl_id", "=", empl_id)])
        )
        if not employee:
            return {
                "success": False,
                "msg": "Please provide the correct empl_id.",
            }

        if month not in self.MONTHS.keys():
            return {
                "success": False,
                "msg": "Please provide the correct month name.",
            }

        base_url = (
            request.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )
        payslip_domain = [("employee_id", "=", employee.id)]
        empl_payslip = request.env["hr.payslip"].sudo().search(payslip_domain)
        employee_payslip = empl_payslip.filtered(
            lambda x: x.date_from.month == self.MONTHS[month]
            and x.date_to.month == self.MONTHS[month]
        )

        if employee_payslip:
            url_ids = ",".join([str(x.id) for x in employee_payslip])
            return {
                "success": True,
                "id": employee_payslip.ids,
                "url": base_url + "/print/payslips?list_ids=" + url_ids,
            }
        else:
            return {
                "success": False,
                "msg": "There are no payslip exists of you for {} month".format(
                    month
                ),
            }

    @route(["/print/payslips"], type='http', auth='public')
    def get_payroll_report_print(self, list_ids='', **post):
        ids = [int(s) for s in list_ids.split(',')]
        payslips = request.env['hr.payslip'].sudo().browse(ids)

        pdf_writer = PdfFileWriter()

        for payslip in payslips.with_user(SUPERUSER_ID):
            report = request.env.ref('om_hr_payroll.payslip_details_report', False).sudo()
            report = report.with_context(lang=payslip.employee_id.sudo().address_home_id.lang)
            pdf_content, _ = report.sudo()._render_qweb_pdf(payslip.id, data={'company_id': payslip.company_id})
            reader = PdfFileReader(io.BytesIO(pdf_content), strict=False, overwriteWarnings=False)

            for page in range(reader.getNumPages()):
                pdf_writer.addPage(reader.getPage(page))

        _buffer = io.BytesIO()
        pdf_writer.write(_buffer)
        merged_pdf = _buffer.getvalue()
        _buffer.close()

        if len(payslips) == 1:
            report_name = "Payslip"
        else:
            report_name = "Payslips"

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf)),
            ('Content-Disposition', 'attachment; filename=' + report_name + '.pdf;')
        ]

        return request.make_response(merged_pdf, headers=pdfhttpheaders)
