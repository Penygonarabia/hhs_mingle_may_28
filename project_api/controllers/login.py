import json
import logging
import functools
import traceback
import werkzeug.wrappers
from datetime import date, datetime, timedelta
from odoo import http,models
from odoo.addons.project_api.models.common import invalid_response, valid_response
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request
from werkzeug.wrappers import Response
from odoo.tools import format_datetime

_logger = logging.getLogger(__name__)

def serialize_datetime(dt):
    return dt.strftime('%Y-%m-%d') if dt else None

def float_to_time_string(value):
    """Convert a float value representing hours into a time string format HH:MM."""
    if value is None or value == 0:
        return ''
    hours, remainder = divmod(value * 3600, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{int(hours):02}:{int(minutes):02}'

def validate_token(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        # Retrieve the access token from request headers
        access_token = request.httprequest.headers.get("access_token")
        if not access_token:
            return invalid_response(
                "access_token_not_found",
                "Missing access token in request header",
                401
            )

        # Search for the access token in the database
        access_token_data = request.env["api.access_token"].sudo().search(
            [("token", "=", access_token)], order="id DESC", limit=1
        )

        # Validate the token
        if not access_token_data:
            return invalid_response(
                "invalid_access_token",
                "The provided access token is invalid",
                401
            )

        # if access_token_data.has_expired():
        #     return invalid_response(
        #         "access_token_expired",
        #         "The access token has expired",
        #         401
        #     )

        # Update the request environment with the user's ID
        request.update_env(user=access_token_data.user_id.id)

        # Proceed with the original function
        return func(self, *args, **kwargs)

    return wrap

# def validate_token(func):
#     @functools.wraps(func)
#     def wrap(self, *args, **kwargs):
#         access_token = request.httprequest.headers.get("access_token")
#         if not access_token:
#             return invalid_response("access_token_not_found", "missing access token in request header", 401)
#         access_token_data = request.env["api.access_token"].sudo().search([("token", "=", access_token)],
#                                                                           order="id DESC", limit=1)
#
#         if access_token_data.find_or_create_token(user_id=access_token_data.user_id.id) != access_token:
#             return invalid_response("access_token", "token seems to have expired or invalid", 401)
#
#         request.session.uid = access_token_data.user_id.id
#         request.uid = access_token_data.user_id.id
#         return func(self, *args, **kwargs)
#
#     return wrap


class AccessToken(http.Controller):
    @http.route("/api/login", methods=["GET"], type="http", auth="none", csrf=False)
    def api_login(self, **post):

        params = ["db", "login", "password"]
        params = {key: post.get(key) for key in params if post.get(key)}
        db, username, password = (
            params.get("db"),
            post.get("login"),
            post.get("password"),
        )
        _credentials_includes_in_body = all([db, username, password])
        if not _credentials_includes_in_body:
            # The request post body is empty the credetials maybe passed via the headers.
            headers = request.httprequest.headers
            db = headers.get("db")
            username = headers.get("login")
            password = headers.get("password")
            _credentials_includes_in_headers = all([db, username, password])
            if not _credentials_includes_in_headers:
                # Empty 'db' or 'username' or 'password:
                return invalid_response(
                    "missing error", "either of the following are missing [db, username,password]", 403,
                )
        # Login in odoo database:
        try:
            request.session.authenticate(db, username, password)
        except AccessError as aee:
            return invalid_response("Access error", "Error: %s" % aee.name)
        except AccessDenied as ade:
            return invalid_response("Access denied", "Login, password or db invalid")
        except Exception as e:
            # Invalid database:
            info = "The database name is not valid {}".format((e))
            error = "invalid_database"
            _logger.error(info)
            return invalid_response("wrong database name", error, 403)

        uid = request.session.uid
        # odoo login failed:
        if not uid:
            info = "authentication failed"
            error = "authentication failed"
            _logger.error(info)
            return invalid_response(401, error, info)

        # Generate tokens
        access_token = request.env["api.access_token"].find_or_create_token(user_id=uid, create=True)
        # Successful response:
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "uid": uid,
                    "user_context": request.session.get_context() if uid else {},
                    "company_id": request.env.user.company_id.id if uid else None,
                    "company_ids": request.env.user.company_ids.ids if uid else None,
                    "partner_id": request.env.user.partner_id.id,
                    "access_token": access_token,
                    "company_name": request.env.user.company_name,
                    "country": request.env.user.country_id.name,
                    "contact_address": request.env.user.contact_address,
                }
            ),
        )

    @http.route("/api/login/token_api_key", methods=["GET"], type="http", auth="none", csrf=False)
    def api_login_api_key(self, **post):
        try:
            # Extract credentials from headers
            headers = request.httprequest.headers
            db = headers.get("db")
            api_key = headers.get("api_key")

            # Check if both database and API key are provided
            if not all([db, api_key]):
                return invalid_response(
                    "missing error", "either of the following are missing [db ,api_key]", 403
                )

            # Authenticate using API key
            user_id = request.env["res.users.apikeys"]._check_credentials(scope="rpc", key=api_key)

            # If authentication fails, return error response
            if not user_id:
                info = "authentication failed"
                error = "authentication failed"
                _logger.error(info)
                return invalid_response(401, error, info)

            # Fetch user information
            uid = user_id
            user_obj = request.env['res.users'].sudo().browse(int(uid))

            # Generate access token
            access_token = request.env["api.access_token"].find_or_create_token(user_id=uid, create=True)

            # Prepare response data
            response_data = {
                "uid": uid,
                "user_name": user_obj.name,
                "company_id": user_obj.company_id.id if uid else None,
                "company_ids": user_obj.company_ids.ids if uid else None,
                "partner_id": user_obj.partner_id.name,
                "access_token": access_token,
                "company_name": user_obj.company_id.name,
                "country": user_obj.partner_id.country_id.name,
                "contact_address": user_obj.partner_id.city,
            }

            # Return JSON response
            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
                response=json.dumps(response_data),
            )

        except Exception as e:
            # Handle exceptions and return error response
            error_msg = str(e)
            _logger.error(error_msg)
            return invalid_response(500, "internal_server_error", error_msg)


    @validate_token
    @http.route("/api/employee/create", methods=["POST"], type="json", auth="none", csrf=False)
    def create_employee(self, **post):
        try:
            _logger.info("Attempting to create an employee...")

            user_id = request.uid
            user_obj = request.env['res.users'].browse(user_id)

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)

            emp_name = payload.get("emp_name")
            emp_no = payload.get("emp_no")
            # emp_last_name = payload.get("emp_last_name")
            # # emp_manager = payload.get("emp_manager")
            # emp_yrs_exp = payload.get("emp_yrs_exp")
            # emp_passport_no = payload.get("emp_passport_no")
            # emp_passport_expiry_date = payload.get("emp_passport_expiry_date")
            # emp_passport_issue_place = payload.get("emp_passport_issue_place")
            # emp_iqama_no = payload.get("emp_iqama_no")
            # emp_is_saudi = payload.get("emp_is_saudi")
            # emp_iqama_professional = payload.get("emp_iqama_professional")
            # emp_iqama_expiry_date = payload.get("emp_iqama_expiry_date")
            # emp_religion = payload.get("emp_religion")
            # emp_gender = payload.get("emp_gender")
            # emp_dob = payload.get("emp_dob")
            # emp_hiring_date = payload.get("emp_hiring_date")
            # emp_marital = payload.get("emp_marital")
            # emp_visa = payload.get("emp_visa")
            # emp_visa_expire = payload.get("emp_visa_expire")
            # emp_work_phone = payload.get("emp_work_phone")
            # emp_work_email = payload.get("emp_work_email")
            # emp_dept_code = payload.get("emp_dept_code")
            # emp_job_name = payload.get("emp_job_name")
            # emp_joining_date = payload.get("emp_joining_date")
            # emp_location_no = payload.get("emp_location_no")
            emp_last_name = payload.get("emp_last_name") if payload.get("emp_last_name") else ""
            emp_yrs_exp = payload.get("emp_yrs_exp") if payload.get("emp_yrs_exp") else ""
            emp_passport_no = payload.get("emp_passport_no") if payload.get("emp_passport_no") else ""
            emp_passport_expiry_date = payload.get("emp_passport_expiry_date") if payload.get(
                "emp_passport_expiry_date") else ""
            emp_passport_issue_place = payload.get("emp_passport_issue_place") if payload.get(
                "emp_passport_issue_place") else ""
            emp_iqama_no = payload.get("emp_iqama_no") if payload.get("emp_iqama_no") else ""
            emp_is_saudi = payload.get("emp_is_saudi") if payload.get("emp_is_saudi") else ""
            emp_iqama_professional = payload.get("emp_iqama_professional") if payload.get(
                "emp_iqama_professional") else ""
            emp_iqama_expiry_date = payload.get("emp_iqama_expiry_date") if payload.get(
                "emp_iqama_expiry_date") else ""
            emp_religion = payload.get("emp_religion") if payload.get("emp_religion") else ""
            emp_gender = payload.get("emp_gender") if payload.get("emp_gender") else ""
            emp_dob = payload.get("emp_dob") if payload.get("emp_dob") else ""
            emp_hiring_date = payload.get("emp_hiring_date") if payload.get("emp_hiring_date") else ""
            emp_marital = payload.get("emp_marital") if payload.get("emp_marital") else ""
            emp_visa = payload.get("emp_visa") if payload.get("emp_visa") else ""
            emp_visa_expire = payload.get("emp_visa_expire") if payload.get("emp_visa_expire") else ""
            emp_work_phone = payload.get("emp_work_phone") if payload.get("emp_work_phone") else ""
            emp_work_email = payload.get("emp_work_email") if payload.get("emp_work_email") else ""
            emp_dept_code = payload.get("emp_dept_code") if payload.get("emp_dept_code") else ""
            emp_job_name = payload.get("emp_job_name") if payload.get("emp_job_name") else ""
            emp_joining_date = payload.get("emp_joining_date") if payload.get("emp_joining_date") else ""
            emp_location_no = payload.get("emp_location_no") if payload.get("emp_location_no") else ""
            emp_country_of_birth = payload.get("emp_country_of_birth") if payload.get("emp_country_of_birth") else ""
            emp_exit_date = payload.get("emp_exit_date") if payload.get("emp_exit_date") else ""
            emp_state = payload.get("emp_state") if payload.get("emp_state") else ""
            iqama_professional = payload.get("iqama_professional") if payload.get("iqama_professional") else ""
            iqama_company_id = payload.get("iqama_company_id") if payload.get("iqama_company_id") else ""


            _logger.info("Employee name: %s, Employee number: %s", emp_name, emp_no)

            emp_obj = request.env['hr.employee'].search([('employee_no', '=', emp_no), ('active', 'in', [True, False])])

            # Check for duplicate employee name and employee number
            # duplicate_employee = emp_obj.search([
            #     ('employee_no', '=', emp_no)
            # ])
            if emp_obj:
                _logger.warning("Duplicate employee number: %s", emp_no)

                return {
                    "error": "An employee number already exists."
                }, 400
            if not emp_obj:
                emp_dept_code_dep = ''
                emp_job_name_job = ''
                emp_location_no_loc = ''
                emp_iqama_professional_no = ''
                emp_passport_issue_place_name = ''
                emp_country_of_birth_name = ''
                if emp_dept_code:
                    department_obj = request.env['hr.department'].search([
                        ('dept_code', '=', emp_dept_code),
                    ])
                    emp_dept_code_dep = department_obj.id if department_obj else ''

                if emp_job_name:
                    job_obj = request.env['hr.job'].search([
                        ('name', '=', emp_job_name),
                    ])
                    emp_job_name_job = job_obj.id if job_obj else ''
                if emp_location_no:
                    location_obj = request.env['hr.work.location'].search([
                        ('location_number', '=', emp_location_no)
                    ])
                    emp_location_no_loc = location_obj.id if location_obj else ''

                if emp_iqama_professional:
                    iqama_obj = request.env['iqama.management'].search([
                        ('code', '=', emp_iqama_professional)
                    ])
                    emp_iqama_professional_no = iqama_obj.id if iqama_obj else ''

                if emp_passport_issue_place:
                    city_obj = request.env['res.city'].search([
                        ('name', '=', emp_passport_issue_place)
                    ])
                    emp_passport_issue_place_name = city_obj.id if city_obj else ''

                if emp_country_of_birth:
                    country_of_birth_obj = request.env['res.country'].search([
                        ('name', '=', emp_country_of_birth)
                    ])
                    emp_country_of_birth_name = country_of_birth_obj.id if country_of_birth_obj else ''

                if  emp_joining_date < emp_hiring_date:
                    _logger.warning("Employee joining date should not less than hiring date : %s", emp_joining_date)

                    return {
                        "error": "Employee joining date should not less than hiring date."
                    }, 400

                new_emp = request.env['hr.employee'].create({
                    'name': emp_name if emp_name else "",
                    'employee_no': emp_no if emp_no else "",
                    'last_name': emp_last_name if emp_last_name else "",
                    # 'parent_id': emp_manager,
                    'yrs_of_exp': emp_yrs_exp if emp_yrs_exp else "",
                    'passport_id': emp_passport_no if emp_passport_no else "",
                    'passeport_expiry_date': str(emp_passport_expiry_date) if emp_passport_expiry_date else False,
                    # 'passeport_issue_place': emp_passport_issue_place if emp_passport_issue_place else "",
                    'passeport_issue_place': emp_passport_issue_place_name if emp_passport_issue_place_name else "",
                    'iqama_no': emp_iqama_no if emp_iqama_no else "",
                    'iqama_professional': emp_iqama_professional_no if emp_iqama_professional_no else "",
                    # 'iqama_professional': emp_iqama_professional if emp_iqama_professional else "",
                    'iqama_expiry_date': str(emp_iqama_expiry_date) if emp_iqama_expiry_date else False,
                    'is_saudi': emp_is_saudi if emp_is_saudi else "",
                    'religion': emp_religion if emp_religion else "",
                    'gender': emp_gender if emp_gender else "",
                    'birthday': str(emp_dob) if emp_dob else False,
                    'hiring_date': str(emp_hiring_date) if emp_hiring_date else False,
                    'marital': emp_marital if emp_marital else "",
                    'visa_no': emp_visa if emp_visa else "",
                    'visa_expire': str(emp_visa_expire) if emp_visa_expire else False,
                    'work_phone': emp_work_phone if emp_work_phone else "",
                    'work_email': emp_work_email if emp_work_email else "",
                    # 'department_id': department_obj.id if emp_name else "",
                    'department_id': emp_dept_code_dep if emp_dept_code_dep else "",
                    # 'job_id': job_obj.id if emp_name else "",
                    'job_id': emp_job_name_job if emp_job_name_job else "",
                    'joining_date': str(emp_joining_date) if emp_joining_date else False,
                    'work_location_id': emp_location_no_loc if emp_location_no_loc else "",
                    'country_of_birth': emp_country_of_birth_name if emp_country_of_birth_name else "",
                    'exit_date': str(emp_exit_date) if emp_exit_date else False,
                    'state': emp_state if emp_state else "",
                    # 'iqama_professional': iqama_professional if iqama_professional else "",
                    'iqama_company_id': iqama_company_id if iqama_company_id else "",
                })

                if new_emp:
                    _logger.info("Employee created successfully.")

                    # Prepare response data
                    response_data = {
                        "empl_id": new_emp.id,
                        "employee_no": new_emp.employee_no,
                        "name": new_emp.name,
                        "last_name": new_emp.last_name,
                        # "parent_id": new_emp.parent_id.name,
                        "yrs_of_exp": new_emp.yrs_of_exp,
                        "passport_id": new_emp.passport_id,
                        "passeport_expiry_date": new_emp.passeport_expiry_date,
                        "passeport_issue_place": new_emp.passeport_issue_place.name,
                        "iqama_no": new_emp.iqama_no,
                        #"iqama_professional": new_emp.iqama_professional.name,
                        'iqama_expiry_date': new_emp.iqama_expiry_date,
                        'is_saudi': new_emp.is_saudi,
                        'religion': new_emp.religion,
                        'gender': new_emp.religion,
                        'birthday': new_emp.birthday,
                        'hiring_date': new_emp.hiring_date,
                        'marital': new_emp.marital,
                        'visa_no': new_emp.visa_no,
                        'visa_expire': new_emp.visa_expire,
                        'work_email': new_emp.work_email,
                        'work_phone': new_emp.work_phone,
                        'department_id': new_emp.department_id.name,
                        'job_id': new_emp.job_id.name,
                        'joining_date': new_emp.joining_date,
                        'work_location_id': new_emp.work_location_id.name,
                        'country_of_birth': new_emp.country_of_birth.name,
                        'exit_date': new_emp.exit_date,
                        'state': new_emp.state,
                        'iqama_professional': new_emp.iqama_professional,
                        'iqama_company_id': new_emp.iqama_company_id,
                        "message": "Employee created successfully"
                    }

                    return response_data, 201
        except Exception as e:
            _logger.error("An error occurred while creating the employee: %s", e)
            return {
                "error": "An error occurred while creating the employee"
            }, 404

    @validate_token
    @http.route("/api/employee/read_all", type='http', auth='none', methods=["GET"], csrf=False)
    def read_all_employees(self):
        try:
            employee_no = request.params.get('employee_no')

            if employee_no:
                emp_obj = request.env['hr.employee'].search([('employee_no', '=', employee_no), ('active', 'in', [True, False])])
            else:
                emp_obj = request.env['hr.employee'].search([])

            employees = []
            for emp in emp_obj:
                vals = {
                    'id': emp.id or '',
                    'employee_no': emp.employee_no or '',
                    'name': emp.name or '',
                    'middle_name': emp.middle_name or '',
                    'third_name': emp.third_name or '',
                    'last_name': emp.last_name or '',
                    # 'department_id': emp.department_id.id if emp.department_id else None,
                    'department_id': emp.department_id.id or '',
                    'job_id': emp.job_id.id or '',
                    'job_name': emp.job_id.name or '',
                    'employee_type': emp.employee_type or '',
                    'joining_date': str(emp.joining_date) or '',
                    'department_name': emp.department_id.name or '',
                    'parent_id': emp.parent_id.id or '',
                    'manager_name': emp.parent_id.name or '',
                    'company_id': emp.company_id.id or '',
                    'company_name': emp.company_id.name or '',
                    'yrs_of_exp': emp.yrs_of_exp or '',
                    'passport_id': emp.passport_id or '',
                    'work_mobile': emp.mobile_phone or '',
                    'work_phone': emp.work_phone or '',
                    'work_email': emp.work_email or '',
                    'passport_expiry_date': str(emp.passeport_expiry_date) or '',
                    'passport_issue_place': emp.passeport_issue_place.name or '',
                    'visa_no': emp.visa_no or '',
                    'visa_expire': str(emp.visa_expire) or '',
                    'study_field': emp.study_field or '',
                    'certificate': emp.certificate or '',
                    'iqama_no': emp.iqama_no or '',
                    'iqama_professional': emp.iqama_professional.name or '',
                    'iqama_expiry_date': str(emp.iqama_expiry_date) or '',
                    'is_saudi': emp.is_saudi or '',
                    'religion': emp.religion or '',
                    'gender': emp.gender or '',
                    'birthday': str(emp.birthday) or '',
                    'age': emp.age or '',
                    'marital': emp.marital or '',
                    'hiring_date': str(emp.hiring_date) or '',
                    'country_of_birth': emp.country_of_birth.name or '',
                    'exit_date': str(emp.exit_date) or '',
                    'state': emp.state or '',
                    'iqama_professional': emp.iqama_professional or '',
                    'iqama_company_id': emp.iqama_company_id or '',

                }
                employees.append(vals)

            response_data = {
                'status': 200,
                'response': employees,
                'message': 'Success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data),
            )
        except Exception as e:
            _logger.error("An error occurred while reading the employees: %s", e)
            error_response = {
                'status': 500,
                'error': "An error occurred while reading the employees"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)


    @validate_token
    @http.route("/api/employee/write", methods=["POST"], type="json", auth="none", csrf=False)
    def write_employee(self, **post):
        try:
            _logger.info("Attempting to update an employee...")

            user_id = request.uid
            user_obj = request.env['res.users'].browse(user_id)

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)

            emp_no = payload.get("emp_no")
            emp_name = payload.get("emp_name")
            emp_last_name = payload.get("emp_last_name")
            # emp_manager = payload.get("emp_manager")
            emp_yrs_exp = payload.get("emp_yrs_exp")
            emp_passport_no = payload.get("emp_passport_no")
            emp_passport_expiry_date = payload.get("emp_passport_expiry_date")
            emp_passport_issue_place = payload.get("emp_passport_issue_place")
            emp_iqama_no = payload.get("emp_iqama_no")
            emp_is_saudi = payload.get("emp_is_saudi")
            emp_iqama_professional = payload.get("emp_iqama_professional")
            emp_iqama_expiry_date = payload.get("emp_iqama_expiry_date")
            emp_religion = payload.get("emp_religion")
            emp_gender = payload.get("emp_gender")
            emp_dob = payload.get("emp_dob")
            emp_hiring_date = payload.get("emp_hiring_date")
            emp_marital = payload.get("emp_marital")
            emp_visa = payload.get("emp_visa")
            emp_visa_expire = payload.get("emp_visa_expire")
            emp_work_phone = payload.get("emp_work_phone")
            emp_work_email = payload.get("emp_work_email")
            emp_dept_code = payload.get("emp_dept_code")
            emp_job_name = payload.get("emp_job_name")
            emp_joining_date = payload.get("emp_joining_date")
            emp_location_no = payload.get("emp_location_no")
            emp_country_of_birth = payload.get("emp_country_of_birth")
            emp_exit_date = payload.get("emp_exit_date")
            emp_state = payload.get("emp_state")
            iqama_company_id = payload.get("iqama_company_id")
            iqama_professional = payload.get("iqama_professional")

            print("emp_dept_code", emp_dept_code)


            _logger.info("Employee ID: %s, New Employee Name: %s",  emp_name)

            emp_obj = request.env['hr.employee']
            emp = emp_obj.search([('employee_no', '=', emp_no), ('active', 'in', [True, False])], limit=1)

            if not emp.exists():
                _logger.error("Employee with ID %s not found.", emp_no)
                return {
                    "error": "Employee not found"
                }, 404

            # department_obj = request.env['hr.department'].sudo().search([
            #     ('dept_code', '=', emp_dept_code),
            # ], limit=1)
            # job_obj = request.env['hr.job'].search([
            #     ('name', '=', emp_job_name),
            # ], limit=1)
            # location_obj = request.env['hr.work.location'].search([
            #     ('location_number', '=', emp_location_no)
            # ], limit=1)

            emp_dept_code_dep = ''
            emp_job_name_job = ''
            emp_location_no_loc = ''
            emp_iqama_professional_no = ''
            emp_passport_issue_place_name = ''
            emp_country_of_birth_name = ''
            if emp_dept_code:
                department_obj = request.env['hr.department'].search([
                    ('dept_code', '=', emp_dept_code),
                ])
                if department_obj:
                    emp_dept_code_dep = department_obj.id
                else:
                    return {
                        "error": f"No department found with code: {emp_dept_code}"
                    }, 404

            if emp_job_name:
                job_obj = request.env['hr.job'].search([
                    ('name', '=', emp_job_name),
                ])
                if job_obj:
                    emp_job_name_job = job_obj.id
                else:
                    return {
                        "error": f"No job found with name: {emp_job_name}"
                    }, 404

            if emp_location_no:
                location_obj = request.env['hr.work.location'].search([
                    ('code', '=', emp_location_no)
                ])
                if location_obj:
                    emp_location_no_loc = location_obj.id
                else:
                    return {
                        "error": f"No work location found with number: {emp_location_no}"
                    }, 404

            if emp_iqama_professional:
                iqama_obj = request.env['iqama.management'].search([
                    ('code', '=', emp_iqama_professional)
                ])
                if iqama_obj:
                    emp_iqama_professional_no = iqama_obj.id
                else:
                    return {
                        "error": f"No iqama professional found with code: {emp_iqama_professional}"
                    }, 404

            if emp_passport_issue_place:
                city_obj = request.env['res.city'].search([
                    ('name', '=', emp_passport_issue_place)
                ])
                if city_obj:
                    emp_passport_issue_place_name = city_obj.id
                else:
                    return {
                        "error": f"No city found with name: {emp_passport_issue_place}"
                    }, 404

            if emp_country_of_birth:
                country_of_birth_obj = request.env['res.country'].search([
                    ('name', '=', emp_country_of_birth)
                ])
                if country_of_birth_obj:
                    emp_country_of_birth_name = country_of_birth_obj.id \
                        if country_of_birth_obj else ''
                else:
                    return {
                        "error": f"No Nationality found with name: {emp_country_of_birth}"
                    }, 404

            is_updated = emp.write({
                'name': emp_name if emp_name else emp.emp_name,
                'last_name': emp_last_name if emp_last_name else emp.last_name,
                # 'parent_id': emp_manager,
                'yrs_of_exp': emp_yrs_exp if emp_yrs_exp else emp.yrs_of_exp,
                'passport_id': emp_passport_no if emp_passport_no else emp.passport_id,
                'passeport_expiry_date': emp_passport_expiry_date if emp_passport_expiry_date else emp.passeport_expiry_date,
                # 'passeport_issue_place': emp_passport_issue_place if emp_passport_issue_place else emp.passeport_issue_place.id,
                'passeport_issue_place': emp_passport_issue_place_name if emp_passport_issue_place_name else emp.passeport_issue_place.id,
                'iqama_no': emp_iqama_no if emp_iqama_no else emp.iqama_no,
                # 'iqama_professional': emp_iqama_professional if emp_iqama_professional else emp.iqama_professional,
                'iqama_professional': emp_iqama_professional_no if emp_iqama_professional_no else emp.iqama_professional,
                'iqama_expiry_date': emp_iqama_expiry_date if emp_iqama_expiry_date else emp.iqama_expiry_date,
                'is_saudi': emp_is_saudi if emp_is_saudi else emp.is_saudi,
                'religion': emp_religion if emp_religion else emp.religion,
                'gender': emp_gender if emp_gender else emp.gender,
                'birthday': emp_dob if emp_dob else emp.birthday,
                'hiring_date': emp_hiring_date if emp_hiring_date else emp.hiring_date,
                'marital': emp_marital if emp_marital else emp.marital,
                'visa_no': emp_visa if emp_visa else emp.visa_no,
                'visa_expire': emp_visa_expire if emp_visa_expire else emp.visa_expire,
                'work_phone': emp_work_phone if emp_work_phone else emp.work_phone,
                'work_email': emp_work_email if emp_work_email else emp.work_email,
                # 'department_id': department_obj.id if department_obj else emp.department_id,
                'department_id': emp_dept_code_dep if emp_dept_code_dep else emp.department_id,
                # 'job_id': job_obj.id if job_obj else emp.job_id,
                'job_id': emp_job_name_job if emp_job_name_job else emp.job_id,
                'joining_date': emp_joining_date if emp_joining_date else emp.joining_date,
                'work_location_id': emp_location_no_loc if emp_location_no_loc else emp.work_location_id,
                'country_of_birth': emp_country_of_birth_name if emp_country_of_birth_name else emp.country_of_birth,
                # 'work_location_id': location_obj.id if location_obj else emp.work_location_id
                'exit_date': emp_exit_date if emp_exit_date else emp.exit_date,
                'state': emp_state if emp_state else emp.state,
                'iqama_professional': iqama_professional if iqama_professional else emp.iqama_professional,
                'iqama_company_id': iqama_company_id if iqama_company_id else emp.iqama_company_id,
            })

            if is_updated:
                _logger.info("Employee updated successfully.")

                # Prepare response data
                response_data = {
                    "empl_id": emp.id,
                    "name": emp.name,
                    "employee_no": emp.employee_no,
                    "last_name": emp.last_name,
                    # "parent_id": emp.parent_id.name,
                    "yrs_of_exp": emp.yrs_of_exp,
                    "passport_id": emp.passport_id,
                    "passeport_expiry_date": emp.passeport_expiry_date,
                    "passeport_issue_place": emp.passeport_issue_place,
                    "iqama_no": emp.iqama_no,
                    "iqama_professional": emp.iqama_professional,
                    'iqama_expiry_date': emp.iqama_expiry_date,
                    'is_saudi': emp.is_saudi,
                    'religion': emp.religion,
                    'gender': emp.religion,
                    'birthday': emp.birthday,
                    'hiring_date': emp.hiring_date,
                    'marital': emp.marital,
                    'visa_no': emp.visa_no,
                    'visa_expire': emp.visa_expire,
                    'work_email': emp.work_email,
                    'work_phone': emp.work_phone,
                    'department_id': emp.department_id.name,
                    'job_id': emp.job_id.name,
                    'joining_date': emp.joining_date,
                    'work_location_id': emp.work_location_id.name,
                    'country_of_birth': emp.country_of_birth.name,
                    'exit_date': emp.exit_date,
                    'state': emp.state,
                    'iqama_company_id': emp.iqama_company_id,
                    "message": "Employee updated successfully"
                }
                return response_data, 200
        except Exception as e:
            _logger.error("An error occurred while updating the employee: %s", e)
            return {
                "error": "An error occurred while updating the employee"
            }, 404


    @validate_token
    @http.route("/api/employee/delete", methods=["POST"], type="json", auth="none", csrf=False)
    def delete_employee(self, **post):
        try:
            _logger.info("Attempting to delete an employee...")

            # Decode the JSON payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract the employee ID from the payload
            emp_no = payload.get("emp_no")

            if not emp_no:
                _logger.error("Employee with Employee Number %s not found.", emp_no)
                return {
                    "error": "Employee Number not found"
                }, 404

            _logger.info("Employee ID: %s", emp_no)

            # Fetch the employee object using the employee ID
            # emp_obj = request.env['hr.employee']
            delete_search = request.env['hr.employee'].sudo().search([('employee_no', '=', emp_no)])

            # emp = emp_obj.browse(int(emp_id))

            if not delete_search:
                _logger.error("Employee with ID %s not found.", emp_no)
                return {
                    "error": "Employee not found"
                }, 404

            # Delete the employee
            delete_search.unlink()
            _logger.info("Employee with Employee No and Employee Name %s deleted successfully.", emp_no, delete_search.name )

            # Prepare response data
            response_data = {
                "status": 200,
                "message": "Employee deleted successfully"
            }

            return response_data

        except Exception as e:
            _logger.error("An error occurred while updating the employee: %s", e)
            return {
                "error": "An error occurred while updating the employee"
            }, 404

    #### Fetch the department single or whole
    ''' Search all Dept via postman content_type ='text/plain' and give dept_id in params which give only particular department only shown '''

    @validate_token
    @http.route("/api/department/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _department_search_all(self):
        try:
            dept_code = request.params.get("dept_code")


            if dept_code:
                dept_code = request.env['hr.department'].sudo().search([('dept_code', '=', dept_code)])
            else:
                dept_code = request.env['hr.department'].sudo().search([])

            dept_lst = []

            for dept in dept_code:
                vals = {
                    'id': dept.id,
                    'dept_code': dept.dept_code or '',
                    'Name': dept.name,
                    'Manager': dept.manager_id.name or ' ',
                    'Parent Department': dept.parent_id.name or ' ',
                    'Company': dept.company_id.name or ' ',
                    'Administration': dept.is_main_department or ' ',
                    'Description': dept.description or ' ',
                    'Destination Location': dept.dest_location_id.name or ' '

                }
                dept_lst.append(vals)

            response_data = {
                'status': '200',
                'response': dept_lst,
                'message': 'success'

            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data),
            )

        except Exception as e:
            _logger.error("An error occurred while reading the employees: %s", e)
            error_response = {
                'status': 500,
                'error': "An error occurred while reading the employees"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)

    ''' Create a new department with name and description via postman and content-type:"application/json", Body : {"params:{"name":"Purchase","description":"For Purchase"}}'''

    @validate_token
    @http.route('/api/department/create', methods=["POST"], type="json", auth="none", csrf=False)
    def _department_create(self):
        try:
            _logger.info("Attempting to create a department...")

            # Decode and parse the JSON payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)
            payload = json.loads(payload)

            # Extract parameters from the payload

            params = payload.get('params', {})
            dept_name = params.get('name', '')
            dept_description = params.get('description', '')
            dept_code = params.get('dept_code', '')

            if not dept_name or not dept_code:
                return {
                    "error": "Missing 'dept_name', or 'dept_code' in the request."
                }, 400

            dept_search = request.env['hr.department']

            # Check for duplicate department
            duplicate_department = dept_search.sudo().search([
                ('name', '=', dept_name),
                ('dept_code', '=', dept_code)
            ])

            if duplicate_department:
                _logger.warning("Duplicate department found with name: %s, and dept_code: %s",
                                dept_name, dept_code)
                return {
                    "error": "A department with the same name, description, and dept_code already exists."
                }, 400

            # Create the new department
            new_dept = dept_search.sudo().create({
                'name': dept_name if dept_name else '' ,
                'description': dept_description if dept_description else '',
                'dept_code': dept_code if dept_code else ''
            })

            if new_dept:
                _logger.info("Department created successfully.")

                # Prepare response data
                response_data = {
                    "department_id": new_dept.id,
                    "name": new_dept.name,
                    "description": new_dept.description,
                    "dept_code": new_dept.dept_code,
                    "message": "Department created successfully"
                }

                return response_data, 201
        except json.JSONDecodeError:
            _logger.error("Invalid JSON payload")
            return {"error": "Invalid JSON payload"}, 400
        except Exception as e:
            _logger.error("An error occurred while creating the department: %s", str(e))
            return {
                "error": "An error occurred while creating the department."
            }, 500

    @validate_token
    @http.route('/api/department/update', methods=["POST"], type="json", auth="none", csrf=False)
    def _department_update(self, **kw):

        if 'dept_code' not in kw or 'name' not in kw:
            return {"error": "Missing 'id' or 'name' in request"}

        try:
            dept_code = int(kw['dept_code'])
        except ValueError:
            return {"error": "Invalid 'dept_code' format"}

        name = kw['name']
        dept_code = kw['dept_code']
        description = kw['description']

        # Search for the partner with the given ID
        update_search = request.env['hr.department'].sudo().search([('dept_code', '=', dept_code)])

        if not update_search:
            return {"error": f"No Department found with ID {dept_code}"}

        # Update the email
        update_search.write({
            'name': name,
            'dept_code': dept_code,
            'description': description
        })

        return {"success": True, "message": f"name updated for ID {dept_code}"}

    @validate_token
    @http.route('/api/department/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def _department_delete(self, **kw):

        if 'dept_code' not in kw:
            return {"error": "Missing 'dept_code' in request"}

        try:
            dept_code = kw['dept_code']
        except ValueError:
            return {"error": "Invalid 'dept_code' format"}

        # Search for the department with the given dept_code
        delete_search = request.env['hr.department'].sudo().search([('dept_code', '=', dept_code)])

        if not delete_search:
            return {"error": f"No Department found with dept_code {dept_code}"}

        # Delete the department
        delete_search.unlink()

        return {"success": True, "message": f"Department with dept_code {dept_code} deleted successfully"}

    @validate_token
    @http.route("/api/stock_quant/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _stock_quant_search_all(self):
        try:
            _logger.info("Attempting to search for stock_quant...")

            # Retrieve parameters
            default_code = request.params.get("default_code")
            warehouse_code = request.params.get("warehouse_code")

            # Ensure both parameters are provided
            if not default_code or not warehouse_code:
                return werkzeug.wrappers.Response(
                    status=400,
                    content_type="application/json; charset=utf-8",
                    response=json.dumps({
                        'status': 400,
                        'error': "Both 'default_code' and 'warehouse_code' are required"
                    })
                )

            # Resolve product_id from default_code
            product = request.env['product.product'].sudo().search([('default_code', '=', default_code)], limit=1)
            if not product:
                return werkzeug.wrappers.Response(
                    status=404,
                    content_type="application/json; charset=utf-8",
                    response=json.dumps({
                        'status': 404,
                        'error': f"Product with default_code '{default_code}' not found"
                    })
                )

            # Resolve location_id from warehouse_code
            warehouse = request.env['stock.warehouse'].sudo().search([('code', '=', warehouse_code)], limit=1)
            if not warehouse:
                return werkzeug.wrappers.Response(
                    status=404,
                    content_type="application/json; charset=utf-8",
                    response=json.dumps({
                        'status': 404,
                        'error': f"Warehouse with code '{warehouse_code}' not found"
                    })
                )

            # Perform search in stock.quant with AND condition
            stock_quant_obj = request.env['stock.quant'].sudo().search([
                ('product_id', '=', product.id),
                ('location_id', '=', warehouse.lot_stock_id.id)
            ])

            # Serialize response data
            stock_quant_list = []
            for stock_quant_line in stock_quant_obj:
                stock_quant_data = {
                    "product_id": stock_quant_line.product_id.id,
                    "location_id": stock_quant_line.location_id.id,
                    "quantity": stock_quant_line.quantity,
                    "reserved_quantity": stock_quant_line.reserved_quantity,
                    "user_id": stock_quant_line.user_id.id if stock_quant_line.user_id else None,
                    "create_uid": stock_quant_line.create_uid.id if stock_quant_line.create_uid else None,
                    "write_uid": stock_quant_line.write_uid.id if stock_quant_line.write_uid else None,
                    "create_date": stock_quant_line.create_date.strftime(
                        '%Y-%m-%d %H:%M:%S') if stock_quant_line.create_date else None,
                    "write_date": stock_quant_line.write_date.strftime(
                        '%Y-%m-%d %H:%M:%S') if stock_quant_line.write_date else None,
                    "in_date": stock_quant_line.in_date.strftime(
                        '%Y-%m-%d %H:%M:%S') if stock_quant_line.in_date else None,
                }
                stock_quant_list.append(stock_quant_data)

            # Prepare the response data
            response_data = {
                'status': 200,
                'response': stock_quant_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for stock_quant: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for stock_quant"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )

    @validate_token
    @http.route("/api/stock_quant/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _stock_quant_create(self, **post):
        try:
            _logger.info("Attempting to create stock_quant...")

            # Decode and parse request body
            payload_raw = request.httprequest.data.decode()
            _logger.debug("Received raw payload: %s", payload_raw)

            payload = json.loads(payload_raw)
            params = payload.get('params', {})
            _logger.debug("Parsed params: %s", params)

            # Validate required field
            product_code = params.get('product_code')
            location_code = params.get('location_code')

            if not product_code:
                return {"error": "Missing required field: product_code"}, 400

            if not location_code:
                return {"error": "Missing required fields: location_id"}, 400

            # Optional fields
            #location_id = params.get('location_id')
            quantity = params.get('quantity')
            reserved_quantity = params.get('reserved_quantity')
            user_id = params.get('user_id')
            create_uid = params.get('create_uid')
            write_uid = params.get('write_uid')
            create_date = params.get('create_date')
            write_date = params.get('write_date')
            in_date = params.get('in_date')
            is_reserved = params.get('is_reserved')         


            # Find product by default_code
            product = request.env['product.product'].sudo().search([
                ('default_code', '=', product_code)
            ], limit=1)
            print("product", product, product.id)

            if not product:
                return {
                    "error": f"No stockable product found with code: {product_code}"
                }, 400
           
            # Find stock_warehouse by code, then use its lot_stock_id as location
            warehouse = request.env['stock.warehouse'].sudo().search([
                ('code', '=', location_code)
            ], limit=1)

            if not warehouse or not warehouse.lot_stock_id:
                return {
                    "error": f"No warehouse or lot_stock_id found with code: {location_code}"
                }, 400

            # Create stock.quant
            new_quant = request.env['stock.quant'].sudo().create({
                'product_id': product.id,
                'location_id': warehouse.lot_stock_id.id,
                'quantity': quantity,
                'reserved_quantity': reserved_quantity,
                'user_id': int(user_id) if user_id else None,
                'create_uid': create_uid,
                'write_uid': write_uid,
                'create_date': create_date,
                'write_date': write_date,
                'in_date': in_date,
                'is_reserved': is_reserved,
            })

            _logger.info("Stock quant created for product_code: %s", product_code)
            return {
                "success": True,
                "message": f"Stock quant created for product code: {product_code}",
                "data": {
                    "id": new_quant.id,
                    "product_id": new_quant.product_id.id,
                    "location_id": new_quant.location_id.id if new_quant.location_id else None,
                    "quantity": new_quant.quantity,
                    "reserved_quantity": new_quant.reserved_quantity,
                    "user_id": new_quant.user_id.id if new_quant.user_id else None,
                    "create_uid": new_quant.create_uid.id if new_quant.create_uid else None,
                    "write_uid": new_quant.write_uid.id if new_quant.write_uid else None,
                    "create_date": str(new_quant.create_date),
                    "write_date": str(new_quant.write_date),
                    "in_date": str(new_quant.in_date) if new_quant.in_date else None,
                    "is_reserved": new_quant.is_reserved if new_quant.is_reserved else None,
                }
            }

        except Exception as e:
            _logger.exception("Exception occurred while creating stock_quant")
            return {
                "error": f"Exception occurred: {str(e)}"
            }, 500

            

    @validate_token
    @http.route("/api/stock_quant/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _stock_quant_update(self, **post):
        try:
            _logger.info("Attempting to update stock_quant...")

            # Decode and parse the JSON payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}

            _logger.debug("Extracted params: %s", params)

            # Extract necessary fields
            product_code = params.get('product_code')
            location_code = params.get('location_code')

            if not product_code or not location_code:
                return {"error": "Missing required fields: 'product_code' or 'location_code'"}

            # Find the product by default_code
            product = request.env['product.product'].sudo().search([
                ('default_code', '=', product_code)
            ], limit=1)

            if not product:
                _logger.error("No stockable product found with code: %s", product_code)
                return {"error": f"No stockable product found with code: {product_code}"}

            # Find the warehouse and its lot_stock_id
            warehouse = request.env['stock.warehouse'].sudo().search([
                ('code', '=', location_code)
            ], limit=1)

            if not warehouse or not warehouse.lot_stock_id:
                _logger.error("No warehouse or lot_stock_id found with code: %s", location_code)
                return {"error": f"No warehouse or lot_stock_id found with code: {location_code}"}

            location_id = warehouse.lot_stock_id.id

            # Search for the existing stock.quant record
            stock_quant_update = request.env['stock.quant'].sudo().search([
                ('product_id', '=', product.id),
                ('location_id', '=', location_id)
            ], limit=1)

            if not stock_quant_update:
                _logger.warning("stock_quant not found for product_id: %s and location_id: %s", product.id, location_id)
                return {
                    "error": f"stock_quant with product_code {product_code} and location_code {location_code} not found"
                }

            # Prepare the update dictionary excluding control keys
            excluded_keys = {
                "product_code", "product_id", "product", "location_code",
                "warehouse.lot_stock_id", "warehouse"
            }

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in excluded_keys and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for product_id: %s", product.id)
                return {"error": "No valid fields provided for update"}

            # Perform the update
            _logger.info("Updating stock_quant for product_id: %s with data: %s", product.id, update_vals)
            stock_quant_update.sudo().write(update_vals)

            _logger.info("stock_quant updated successfully for product_id: %s", product.id)

            return {
                "success": True,
                "message": f"stock_quant updated for product_id: {product.id}",
                "data": {
                    'id': stock_quant_update.id,
                    'product_id': stock_quant_update.product_id.id,
                    'location_id': stock_quant_update.location_id.id,
                    'quantity': stock_quant_update.quantity,
                    'reserved_quantity': stock_quant_update.reserved_quantity,
                    'user_id': stock_quant_update.user_id.id if stock_quant_update.user_id else None,
                    'create_uid': stock_quant_update.create_uid.id,
                    'write_uid': stock_quant_update.write_uid.id,
                    'create_date': str(stock_quant_update.create_date),
                    'write_date': str(stock_quant_update.write_date),
                    'in_date': str(stock_quant_update.in_date) if stock_quant_update.in_date else None,
                }
            }

        except Exception as e:
            _logger.exception("An error occurred while updating the stock_quant: %s", str(e))
            return {"error": "An error occurred while updating the stock_quant"}



    @validate_token
    @http.route('/api/stock_quant/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_stock_quant(self, **post):
        try:
            _logger.info("Attempting to delete stock_quant...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
                
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)


            product_id = params.get('product_id')

            # Validate product_id
            if not product_id or not isinstance(product_id, str):
                _logger.error("Invalid or missing product_id.")
                return {"error": "Invalid or missing product_id."}, 400

            _logger.info("Deleting stock_quant for product_id: %s", product_id)

            # Search for the record
            stock_quant_obj = request.env['stock.quant'].sudo().search([('product_id', '=', product_id)], limit=1)

            if not stock_quant_obj.exists():
                _logger.warning("stock_quant not found for product_id: %s", product_id)
                return {"error": f"stock_quant with product_id: {product_id} not found."}, 404

            # Delete the record
            stock_quant_obj.sudo().unlink()
            _logger.info("stock_quant deleted successfully for product_id: %s", product_id)

            return {"success": True, "message": f"stock_quant deleted for product_id: {product_id}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the stock_quant: %s", e)
            return {"error": "An error occurred while deleting the stock_quant"}, 500



    @validate_token
    @http.route("/api/location/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _location_search_all(self):
        try:
            location_no = request.params.get("location_no")

            if location_no:
                location_obj = request.env['hr.work.location'].sudo().search([('location_number', '=', location_no)])
            else:
                location_obj = request.env['hr.work.location'].sudo().search([])

            loc_lst = []

            for loc in location_obj:
                vals = {
                    'id': loc.id,
                    'Location Number': loc.location_number,
                    'Name': loc.name,
                    'company_id': loc.company_id.name or ' ',
                    'Address': loc.address_id.name

                }
                loc_lst.append(vals)

            response_data = {
                'status': '200',
                'response': loc_lst,
                'message': 'success'

            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data),
            )

        except Exception as e:
            _logger.error("An error occurred while reading the location: %s", e)
            error_response = {
                'status': 500,
                'error': "An error occurred while reading the locations"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)

    @validate_token
    @http.route('/api/location/create', methods=["POST"], type="json", auth="none", csrf=False)
    def _location_create(self, **post):
        try:
            _logger.info("Attempting to create a location...")

            # Decode and log the received payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Load the payload into a dictionary
            payload = json.loads(payload)
            params = payload.get('params', {})

            # Extract location information from the payload
            location_no = params.get('location_no')
            loc_name = params.get('name')
            loc_address_id = params.get('address_id')
            loc_company_id = params.get('company_id')

            _logger.info("Location number: %s, Location name: %s", location_no, loc_name)

            # Validate required fields
            if not location_no or not loc_name:
                return {
                    "error": "Missing 'location_no' or 'name' in the request."
                }, 400

            # Search for existing location with the same number
            loc_search = request.env['hr.work.location']
            search_loc = loc_search.sudo().search([('location_number', '=', location_no)], limit=1)

            if search_loc:
                _logger.warning("Duplicate location found for location number: %s", location_no)
                return {
                    "error": "A location with this number already exists."
                }, 400

            # Create a new location record
            new_location = loc_search.sudo().create({
                'name': loc_name,
                'address_id': loc_address_id,
                'company_id': loc_company_id,
                'location_number': location_no
            })

            if new_location:
                _logger.info("Location created successfully.")

                # Prepare response data
                response_data = {
                    "message": "Location created successfully.",
                    "location": {
                        "id": new_location.id,
                        "name": new_location.name,
                        "location_number": new_location.location_number
                    }
                }

                return response_data, 201

        except Exception as e:
            _logger.error("An error occurred while creating the location: %s", e)
            return {
                "error": "An error occurred while creating the location."
            }, 500

    @validate_token
    @http.route('/api/location/update', methods=["POST"], type="json", auth="none", csrf=False)
    def _location_update(self, **post):
        try:
            _logger.info("Attempting to update a location...")

            # Decode and log the received payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Load the payload into a dictionary
            payload = json.loads(payload)
            params = payload.get('params', {})

            # Extract location information from the payload
            location_no = params.get('location_no')
            loc_name = params.get('name')
            loc_address_id = params.get('address_id')
            loc_company_id = params.get('company_id')

            _logger.info("Updating location number: %s", location_no)

            # Validate required fields
            if not location_no:
                return {"error": "Missing 'location_no' in the request."}, 400

            # Search for the location with the given location number
            location_record = request.env['hr.work.location'].sudo().search([('location_number', '=', location_no)],
                                                                            limit=1)

            if not location_record:
                _logger.warning("No location found with number: %s", location_no)
                return {"error": f"No location found with number {location_no}."}, 404

            # Perform the update
            location_record.write({
                'name': loc_name,
                'company_id': loc_company_id,
                'address_id': loc_address_id,
                'location_number': location_no
            })

            _logger.info("Location updated successfully.")

            # Prepare response data
            return {
                "success": True,
                "message": f"Location updated successfully for number {location_no}."
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the location: %s", e)
            return {
                "error": "An error occurred while updating the location."
            }, 500

    @validate_token
    @http.route('/api/location/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def _location_delete(self, **kw):

        if 'location_no' not in kw:
            return {"error": "Missing 'location_no' in request"}

        try:
            location_no = kw['location_no']
        except ValueError:
            return {"error": "Invalid 'location_no' format"}

        # Search for the location with the given location_id
        delete_search = request.env['hr.work.location'].sudo().search([('location_number', '=', location_no)])

        if not delete_search:
            return {"error": f"No Location found with location_id {location_no}"}

        # Delete the location
        delete_search.unlink()

        return {"success": True, "message": f"Location with id {location_no} deleted successfully"}

    @validate_token
    @http.route("/api/contract/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _contract_search_all(self):
        try:
            _logger.info("Attempting to search for contracts...")

            # Extract the employee_no parameter from the request
            employee_no = request.params.get("employee_no")

            # Search for contracts based on the employee_no if provided
            if employee_no:
                # contracts = request.env['hr.contract'].sudo().search([('id', '=', int(contract_id))])
                contracts = request.env['hr.contract'].sudo().search([('employee_no', '=', employee_no)])
            else:
                contracts = request.env['hr.contract'].sudo().search([])

            # Prepare the list of contracts
            contract_list = []
            for contract in contracts:
                contract_data = {
                    'id': contract.id,
                    'employee_no': contract.employee_no,
                    'name': contract.name,
                    'employee_id': contract.employee_id.name,
                    'date_start': str(contract.date_start) or '',
                    'date_end': str(contract.date_end) or '',
                    'notice_days': contract.notice_days or '',
                    'date_reneview': str(contract.date_reneview) or '',
                    'structure_type_id': contract.structure_type_id.name if contract.structure_type_id else None,
                    'schedule_pay': contract.schedule_pay or '',
                    'department_id': contract.department_id.name if contract.department_id else None,
                    'company_id': contract.company_id.name if contract.company_id else None,
                    'job_id': contract.job_id.name if contract.job_id else None,
                    'struct_id': contract.struct_id.name if contract.struct_id else None,
                    'type_id': contract.type_id.name if contract.type_id else None,
                    'contract_type_id': contract.contract_type_id.name if contract.contract_type_id else None,
                    'hr_responsible_id': contract.hr_responsible_id.name if contract.hr_responsible_id else None,
                    'analytic_account_id': contract.analytic_account_id.name if contract.analytic_account_id else None,
                    'journal_id': contract.journal_id.name if contract.journal_id else None,
                    'ramadan_working_hours': str(contract.ramadan_working_hours) or '',
                    'nature': contract.nature,
                    'duration': contract.duration,
                    'wage': contract.wage,
                    'house_allowance': contract.house_allowance,
                    'transport_allowance': contract.transport_allowance,
                    'school_allowance': contract.school_allowance,
                    'food_allowance': contract.food_allowance,
                    'fuel_allowance': contract.fuel_allowance,
                    'ticket_allowance': contract.ticket_allowance,
                    'fixed_allowance': contract.fixed_allowance,
                    'mobile_allowance': contract.mobile_allowance,
                    'work_allowance': contract.work_allowance,
                    'housing_allowance': contract.housing_allowance,
                    'total': contract.total,
                    'calculate_based_on_allowance': contract.calculate_based_on_allowance,
                    # 'gosi_amt': contract.gosi_amt,
                    # 'gosi_comp_amt': contract.gosi_comp_amt,
                    # 'gosi_non_comp': contract.gosi_non_comp,
                }
                contract_list.append(contract_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': contract_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for contracts: %s", e)
            error_response = {
                'status': 500,
                'error': "An error occurred while searching for contracts"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)

    @validate_token
    @http.route('/api/contract/create', methods=["POST"], type="json", auth="none", csrf=False)
    def create_contract(self, **post):
        try:
            _logger.info("Attempting to create a contract...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)

            params = payload.get('params', {})

            employee_no = params.get('employee_no')
            # employee_id = params.get('employee_id')
            contract_name = params.get('contract_name')
            date_start = params.get('date_start')
            date_end = params.get('date_end')
            struct_id = params.get('struct_id')
            hr_responsible_id = params.get('hr_responsible_id')
            wage = params.get('wage')
            house_allowance = params.get('house_allowance')
            transport_allowance = params.get('transport_allowance')
            school_allowance = params.get('school_allowance')
            food_allowance = params.get('food_allowance')
            fuel_allowance = params.get('fuel_allowance')
            ticket_allowance = params.get('ticket_allowance')
            fixed_allowance = params.get('fixed_allowance')
            mobile_allowance = params.get('mobile_allowance')
            work_allowance = params.get('work_allowance')
            housing_allowance = params.get('housing_allowance')


            _logger.info("Contract name: %s, Employee number: %s", contract_name, employee_no)

            employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
            if not employee_obj:
                _logger.warning("employee is not found for that employee_number: %s", employee_no)
                return {
                    "error": "employee is not found for that employee_number"
                }, 400

            contract_obj = request.env['hr.contract']

            # Check for duplicate contract for the employee number
            duplicate_contract = contract_obj.search([
                ('employee_no', '=', employee_no)
            ])
            if duplicate_contract:
                _logger.warning("Duplicate contract found for employee number: %s", employee_no)
                return {
                    "error": "A contract with this 'employee_no' already exists."
                }, 400

            new_contract = contract_obj.create({
                'name': contract_name,
                'employee_id': employee_obj.id,
                'employee_no': employee_no,
                'date_start': date_start if date_start else False,
                'date_end': date_end if date_end else False,
                'struct_id': struct_id if struct_id else False,
                'hr_responsible_id': hr_responsible_id if hr_responsible_id else False,
                'wage': wage if wage else '',
                'house_allowance': house_allowance if house_allowance else '',
                'transport_allowance': transport_allowance if transport_allowance else '',
                'school_allowance': school_allowance if school_allowance else '',
                'food_allowance': food_allowance if food_allowance else '',
                'fuel_allowance': fuel_allowance if fuel_allowance else '',
                'ticket_allowance': ticket_allowance if ticket_allowance else '',
                'fixed_allowance': fixed_allowance if fixed_allowance else '',
                'mobile_allowance': mobile_allowance if mobile_allowance else '',
                'work_allowance': work_allowance if work_allowance else '',
                'housing_allowance': housing_allowance if housing_allowance else ''
            })

            if new_contract:
                _logger.info("Contract created successfully.")

                # Prepare response data
                response_data = {
                    "message": "Contract created successfully.",
                    "contract": {
                        'name': new_contract.name,
                        'employee_id': employee_obj.name,
                        'employee_no': new_contract.employee_no,
                        'date_start': str(new_contract.date_start),
                        'date_end': str(new_contract.date_end),
                        'struct_id': new_contract.struct_id.name if new_contract.struct_id else None,
                        'hr_responsible_id': new_contract.hr_responsible_id.name if new_contract.hr_responsible_id else None,
                        'wage': new_contract.wage,
                        'house_allowance': new_contract.house_allowance,
                        'transport_allowance': new_contract.transport_allowance,
                        'school_allowance': new_contract.school_allowance,
                        'food_allowance': new_contract.food_allowance,
                        'fuel_allowance': new_contract.fuel_allowance,
                        'ticket_allowance': new_contract.ticket_allowance,
                        'fixed_allowance': new_contract.fixed_allowance,
                        'mobile_allowance': new_contract.mobile_allowance,
                        'work_allowance': new_contract.work_allowance,
                        'housing_allowance': new_contract.housing_allowance
                    }
                }

                return response_data, 201
        except Exception as e:
            _logger.error("An error occurred while creating the contract: %s", e)
            return {
                "error": "An error occurred while creating the contract"
            }, 500

    @validate_token
    @http.route('/api/contract/update', methods=["POST"], type="json", auth="none", csrf=False)
    def _contract_update(self, **post):
        try:
            _logger.info("Attempting to update a contract...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get('params', {})

            if 'employee_no' not in params:
                return {"error": "Missing 'employee_no' in request"}, 400

            employee_no = params.get('employee_no')
            name = params.get('name')
            date_start = params.get('date_start')
            date_end = params.get('date_end')
            wage = params.get('wage')
            house_allowance = params.get('house_allowance')
            transport_allowance = params.get('transport_allowance')
            school_allowance = params.get('school_allowance')
            food_allowance = params.get('food_allowance')
            fuel_allowance = params.get('fuel_allowance')
            ticket_allowance = params.get('ticket_allowance')
            fixed_allowance = params.get('fixed_allowance')
            mobile_allowance = params.get('mobile_allowance')
            work_allowance = params.get('work_allowance')
            housing_allowance = params.get('housing_allowance')

            _logger.info("Updating contract for employee number: %s", employee_no)

            # Search for the contract with the given employee_no
            update_search = request.env['hr.contract'].sudo().search([('employee_no', '=', employee_no)])
            _logger.debug("update_search: %s", update_search)

            if not update_search:
                return {"error": f"No contract found with employee number {employee_no}"}, 404

            # Update the contract details
            update_search.write({
                'name': name if name else update_search.name,
                'date_start': date_start if date_start else update_search.date_start,
                'date_end': date_end if date_end else update_search.date_end,
                'wage': wage if wage else update_search.wage,
                'house_allowance': house_allowance if house_allowance else update_search.house_allowance,
                'transport_allowance': transport_allowance if transport_allowance else update_search.transport_allowance,
                'school_allowance': school_allowance if school_allowance else update_search.school_allowance,
                'food_allowance': food_allowance if food_allowance else update_search.food_allowance,
                'fuel_allowance': fuel_allowance if fuel_allowance else update_search.fuel_allowance,
                'ticket_allowance': ticket_allowance if ticket_allowance else update_search.ticket_allowance,
                'fixed_allowance': fixed_allowance if fixed_allowance else update_search.fixed_allowance,
                'mobile_allowance': mobile_allowance if mobile_allowance else update_search.mobile_allowance,
                'work_allowance': work_allowance if work_allowance else update_search.work_allowance,
                'housing_allowance': housing_allowance if housing_allowance else update_search.housing_allowance,
            })

            _logger.info("Contract updated successfully for employee number: %s", employee_no)
            return {"success": True, "message": f"Contract updated for employee number {employee_no}"}, 200

        except Exception as e:
            _logger.error("An error occurred while updating the contract: %s", e)
            return {"error": "An error occurred while updating the contract"}, 500

    @validate_token
    @http.route('/api/contract/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def _contract_delete(self, **post):
        try:
            _logger.info("Attempting to delete a contract...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get('params', {})


            if 'id' not in params:
                return {"error": "Missing 'id' in request"}, 400

            try:
                contract_id = int(params['id'])
            except ValueError:
                return {"error": "Invalid 'id' format"}, 400

            # Search for the contract with the given id
            delete_search = request.env['hr.contract'].sudo().search([('id', '=', contract_id)])
            _logger.debug("delete_search: %s", delete_search)

            if not delete_search:
                return {"error": f"No contract found with id {contract_id}"}, 404

            # Delete the contract
            delete_search.unlink()

            _logger.info("Contract with id %s deleted successfully.", contract_id)
            return {"success": True, "message": f"Contract with id {contract_id} deleted successfully"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the contract: %s", e)
            return {"error": "An error occurred while deleting the contract"}, 500
        
    @validate_token
    @http.route("/api/document/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _document_search_all(self):
        try:
            _logger.info("Attempting to search for document...")

            document_number = request.params.get("document_number")

            if document_number:
                documents = request.env['hr.employee.document'].sudo().search([('name', '=', document_number)])
            else:
                documents = request.env['hr.employee.document'].sudo().search([])

            # Prepare the list of documents
            documents_list = []
            for doc in documents:
                doc_data = {
                    'id': doc.id,
                    'document_number': doc.name,
                    'document_name': doc.document_name.name or '',
                    'issue_date': str(doc.issue_date) or '',
                    'expiry_date': str(doc.expiry_date) or '',
                    # 'attachment_id': doc.doc_attachment_id.name or '',
                    'employee_ref': doc.employee_ref.name or '',
                }
                documents_list.append(doc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': documents_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )


        except Exception as e:
            _logger.error("An error occurred while searching for documents: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for documents"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)

    @validate_token
    @http.route('/api/document/create', methods=["POST"], type="json", auth="none", csrf=False)
    def create_document(self, **post):
        try:
            _logger.info("Attempting to create a document...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)

            params = payload.get('params', {})

            document_number = params.get('document_number')
            document_name = params.get('document_name')
            issue_date = params.get('issue_date')
            expiry_date = params.get('expiry_date')
            employee_no = params.get('employee_no')

            _logger.info("Contract name: %s, Document number: %s", document_number, document_name, employee_no)

            document_obj = request.env['hr.employee.document']
            employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])

            # Check for duplicate document for the employee number
            # duplicate_contract = document_obj.search([
            #     ('name', '=', document_number), ('employee_ref', '=', employee_obj.id)
            # ])
            duplicate_document = document_obj.search([
                ('name', '=', document_number)
            ])
            if duplicate_document:
                _logger.warning("Duplicate document found for document number: %s", document_number)
                return {
                    "error": "A document with this 'document_number' already exists."
                }, 400

            new_contract = document_obj.create({
                'name': document_number,
                'document_name': document_name,
                'issue_date': issue_date,
                'expiry_date': expiry_date,
                'employee_ref': employee_obj.id,
            })

            if new_contract:
                _logger.info("Document created successfully.")

                # Prepare response data
                response_data = {
                    "message": "Document created successfully.",
                    "document": {
                        'name': new_contract.name,
                        'document_name': new_contract.document_name,
                        'employee_ref': new_contract.employee_ref,
                        'issue_date': new_contract.issue_date,
                        'expiry_date': new_contract.expiry_date,
                    }
                }

                return response_data, 201
        except Exception as e:
            _logger.error("An error occurred while creating the document: %s", e)
            return {
                "error": "An error occurred while creating the document"
            }, 500

    @validate_token
    @http.route('/api/document/update', methods=["POST"], type="json", auth="none", csrf=False)
    def _document_update(self, **post):
        try:
            _logger.info("Attempting to update a document...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get('params', {})

            if 'employee_no' not in params:
                return {"error": "Missing 'employee_no' in request"}, 400

            document_number = params.get('document_number')
            document_name = params.get('document_name')
            issue_date = params.get('issue_date')
            expiry_date = params.get('expiry_date')
            employee_no = params.get('employee_no')


            _logger.info("Updating document for employee number: %s", employee_no)

            # Search for the document with the given employee_no
            employee_search = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
            update_search = request.env['hr.employee.document'].sudo().search([('name', '=', document_number),
                                                                              ('employee_ref', '=', employee_search.id)])

            _logger.debug("update_search: %s", update_search)

            if not update_search:
                return {"error": f"No document found with employee number {employee_no}"}, 404

            # Update the contract details
            update_search.write({
                'name': document_number,
                'document_name': document_name,
                'issue_date': issue_date,
                'expiry_date': expiry_date,
                'employee_ref': employee_search.id,
            })

            _logger.info("Document updated successfully for employee number: %s", employee_search.name)
            return {"success": True, "message": f"Document updated for employee number {employee_search.name}"}, 200

        except Exception as e:
            _logger.error("An error occurred while updating the document: %s", e)
            return {"error": "An error occurred while updating the document"}, 500

    @validate_token
    @http.route('/api/document/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def _document_delete(self, **post):
        try:
            _logger.info("Attempting to delete a document...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get('params', {})

            if 'document_number' not in params:
                return {"error": "Missing 'id' in request"}, 400

            try:
                document = params['document_number']
            except ValueError:
                return {"error": "Invalid 'document_number' format"}, 400

            # Search for the document with the given document_number
            delete_search = request.env['hr.employee.document'].sudo().search([('name', '=', document)])
            _logger.debug("delete_search: %s", delete_search)

            if not delete_search:
                return {"error": f"No document found with name {document}"}, 404

            # Delete the contract
            delete_search.unlink()

            _logger.info("Document with id %s deleted successfully.", document)
            return {"success": True, "message": f"Document with id {document} deleted successfully"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the document: %s", e)
            return {"error": "An error occurred while deleting the document"}, 500

    @validate_token
    @http.route("/api/job/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _job_search_all(self):
        try:
            _logger.info("Attempting to search for job_title...")

            job_title = request.params.get("name")

            if job_title:
                job_position = request.env['hr.job'].sudo().search([('name', '=', job_title)])
            else:
                job_position = request.env['hr.job'].sudo().search([])

            # Prepare the list of job_position
            job_title_list = []
            for job in job_position:
                doc_data = {
                    'id': job.id,
                    'name': job.name,
                    'company_id': job.company_id.name,
                    'address_id': job.address_id.name,

                }
                job_title_list.append(doc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': job_title_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )


        except Exception as e:
            _logger.error("An error occurred while searching for job title: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for job title"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)

    @validate_token
    @http.route('/api/job/create', methods=["POST"], type="json", auth="none", csrf=False)
    def create_document(self, **post):
        try:
            _logger.info("Attempting to create a job...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)

            params = payload.get('params', {})

            name = params.get('name')
            company_id = params.get('company_id')
            address_id = params.get('address_id')

            _logger.info("Job Title: %s", name)

            job_obj = request.env['hr.job']

            duplicate_job_title = job_obj.search([
                ('name', '=', name)
            ])
            if duplicate_job_title:
                _logger.warning("Duplicate job title found for Job name: %s", name)
                return {
                    "error": "A document with this 'document_number' already exists."
                }, 400

            new_job_title = job_obj.create({
                'name': name,
                'company_id': company_id,
                'address_id': address_id,
            })

            if new_job_title:
                _logger.info("Job Title created successfully.")

                # Prepare response data
                response_data = {
                    "message": "Job Title created successfully.",
                    "job_title": {
                        'name': new_job_title.name,
                        'company_id': new_job_title.company_id,
                        'address_id': new_job_title.address_id,
                    }
                }

                return response_data, 201
        except Exception as e:
            _logger.error("An error occurred while creating the Job Title: %s", e)
            return {
                "error": "An error occurred while creating the Job Title"
            }, 500

    @validate_token
    @http.route('/api/job/update', methods=["POST"], type="json", auth="none", csrf=False)
    def _job_update(self, **post):
        try:
            _logger.info("Attempting to update a Job Title...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get('params', {})

            if 'name' not in params:
                return {"error": "Missing 'name' in request"}, 400

            name = params.get('name')
            company_id = params.get('company_id')
            address_id = params.get('address_id')

            _logger.info("Updating job title for name: %s", name)

            # Search for the job_title with the given name
            update_search = request.env['hr.job'].sudo().search([('name', '=', name)])

            _logger.debug("update_search: %s", update_search)

            if not update_search:
                return {"error": f"No job title found with name {name}"}, 404

            # Update the job details
            update_search.write({
                'name': name,
                'company_id': company_id,
                'address_id': address_id,
            })

            _logger.info("Job Title updated successfully for name: %s", update_search.name)
            return {"success": True, "message": f"Job Title updated for name {update_search.name}"}, 200

        except Exception as e:
            _logger.error("An error occurred while updating the Job Title: %s", e)
            return {"error": "An error occurred while updating the Job Title"}, 500

    @validate_token
    @http.route('/api/job/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def _job_delete(self, **post):
        try:
            _logger.info("Attempting to delete a Job Title...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get('params', {})

            if 'name' not in params:
                return {"error": "Missing 'name' in request"}, 400

            try:
                name = params['name']
            except ValueError:
                return {"error": "Invalid 'name' format"}, 400

            # Search for the Job Title with the given id
            delete_search = request.env['hr.job'].sudo().search([('name', '=', name)])
            _logger.debug("delete_search: %s", delete_search)

            if not delete_search:
                return {"error": f"No Job Title found with id {name}"}, 404

            # Delete the Job Title
            delete_search.unlink()

            _logger.info("Job Title with id %s deleted successfully.", name)
            return {"success": True, "message": f"Job Title with id {name} deleted successfully"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the Job Title: %s", e)
            return {"error": "An error occurred while deleting the Job Title"}, 500

    @validate_token
    @http.route("/api/dependence/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _dependence_search_all(self):
        try:
            _logger.info("Attempting to search for dependence...")

            employee_no = request.params.get("employee_no")
            employee = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])

            if employee_no:
                dependence = request.env['hr.employee.family'].sudo().search([('employee_id', '=', employee.id)])
            else:
                dependence = request.env['hr.employee.family'].sudo().search([])

            # Prepare the list of dependence
            dependence_list = []
            for dep in dependence:
                doc_data = {
                    'id': dep.id,
                    'employee_no': dep.employee_id.name,
                    'relation_id': dep.relation_id.name,
                    'member_name': dep.member_name,
                    'member_contact': dep.member_contact or '',
                    'birth_date': str(dep.birth_date),
                }
                dependence_list.append(doc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': dependence_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )


        except Exception as e:
            _logger.error("An error occurred while searching for dependence: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for dependence"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)

    @validate_token
    @http.route('/api/dependence/create', methods=["POST"], type="json", auth="none", csrf=False)
    def create_dependence(self, **post):
        try:
            _logger.info("Attempting to create a dependence...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)

            params = payload.get('params', {})

            # name = params.get('name')
            employee_no = params.get('employee_no')
            member_name = params.get('member_name')
            member_contact = params.get('member_contact')
            birth_date = params.get('birth_date')
            relation_name = params.get('relation_name')

            _logger.info("Dependence: %s", employee_no)

            dependence_obj = request.env['hr.employee.family']
            employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
            relation_obj = request.env['hr.employee.relation'].sudo().search([('name', '=', relation_name)])

            duplicate_job_title = dependence_obj.search([
                ('member_name', '=', member_name)
            ])
            if duplicate_job_title:
                _logger.warning("Duplicate dependence found for Employee No: %s", employee_no, member_name)
                return {
                    "error": "A dependence with this 'member_name' already exists."
                }, 400

            new_dependence = dependence_obj.create({
                'employee_id': employee_obj.id,
                'relation_id': relation_obj.id,
                'member_name': member_name,
                'member_contact': member_contact,
                'birth_date': birth_date,
            })

            if new_dependence:
                _logger.info("Dependence created successfully.")

                # Prepare response data
                response_data = {
                    "message": "Dependence created successfully.",
                    "dependence": {
                        'employee_id': new_dependence.employee_id.name,
                        'relation_id': new_dependence.relation_id.name,
                        'member_name': new_dependence.member_name,
                        'member_contact': new_dependence.member_contact,
                        'birth_date': new_dependence.birth_date,
                    }
                }

                return response_data, 201
        except Exception as e:
            _logger.error("An error occurred while creating the Dependence: %s", e)
            return {
                "error": "An error occurred while creating the Dependence"
            }, 500

    @validate_token
    @http.route('/api/dependence/update', methods=["POST"], type="json", auth="none", csrf=False)
    def _dependence_update(self, **post):
        try:
            _logger.info("Attempting to update a _dependence_update...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get('params', {})

            if 'employee_no' not in params:
                return {"error": "Missing 'employee_no' in request"}, 400

            employee_no = params.get('employee_no')
            member_name = params.get('member_name')
            member_contact = params.get('member_contact')
            birth_date = params.get('birth_date')
            relation_name = params.get('relation_name')

            _logger.info("Updating dependence for employee_no: %s", employee_no)

            # Search for the dependence with the given name
            employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
            relation_obj = request.env['hr.employee.relation'].sudo().search([('name', '=', relation_name)])
            update_search = request.env['hr.employee.family'].sudo().search([('employee_id', '=', employee_obj.id),
                                                                             ('member_name', '=', member_name)])

            _logger.debug("update_search: %s", update_search)

            if not update_search:
                return {"error": f"No dependence found with employee_no {employee_no}"}, 404

            # Update the dependence details
            for update in update_search:
                update.write({
                    'employee_id': employee_obj.id,
                    'relation_id': relation_obj.id,
                    'member_name': member_name,
                    'member_contact': member_contact,
                    'birth_date': birth_date,
                })

                _logger.info("Dependence updated successfully for name: %s", update_search.employee_id.name)
                return {"success": True, "message": f"Dependence updated for name {update_search.employee_id.name}"}, 200

        except Exception as e:
            _logger.error("An error occurred while updating the Dependence: %s", e)
            return {"error": "An error occurred while updating the Dependence"}, 500

    @validate_token
    @http.route('/api/dependence/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def _job_delete(self, **post):
        try:
            _logger.info("Attempting to delete a Job Title...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get('params', {})

            if 'member_name' not in params and 'employee_no' not in params:
                return {"error": "Missing 'member_name' in request"}, 400

            try:
                member_name = params['member_name']
                employee_no = params['employee_no']
            except ValueError:
                return {"error": "Invalid 'member_name' format"}, 400

            # Search for the dependence with the given member_name and employee_no
            employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
            delete_search = request.env['hr.employee.family'].sudo().search([('member_name', '=', member_name),
                                                                             ("employee_id", '=', employee_obj.id)])
            _logger.debug("delete_search: %s", delete_search)

            if not delete_search:
                return {"error": f"No dependence found with id {member_name}"}, 404

            # Delete the Job Title
            delete_search.unlink()

            _logger.info("Dependence with id %s deleted successfully.", member_name)
            return {"success": True, "message": f"Dependence with id {member_name} deleted successfully"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the dependence: %s", e)
            return {"error": "An error occurred while deleting the Job Title"}, 500

    ### commanded on 28/08/2024
    # @validate_token
    # @http.route("/api/attendance/search", methods=["GET"], type="http", auth="none", csrf=False)
    # def _attendance_search_all(self):
    #     try:
    #         _logger.info("Attempting to search for attendance...")
    #
    #         # employee_no = request.params.get("employee_no")
    #         check_in = request.params.get("check_in")
    #         # employee = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
    #         if check_in:
    #             # attendance = request.env['hr.attendance'].sudo().search([('check_in', '>=', check_in + ' 00:00:00'), ('check_in', '<=', check_in + ' 23:59:59')])
    #             attendance = request.env['hr.attendance'].sudo().search([('check_in', '>=', check_in + ' 00:00:00'), ('check_in', '<=', check_in + ' 23:59:59')])
    #
    #             attendance_list = []
    #             for attend in attendance:
    #                 attend_data = {
    #                     'id': attend.id,
    #                     'employee_name': attend.employee_id.name,
    #                     'employee_no': attend.employee_id.employee_no or '',
    #                     'check_in': str(attend.check_in) or '',
    #                     'check_out': str(attend.check_out) or '',
    #                     'worked_hours': attend.worked_hours or '',
    #                     'process': attend.process or '',
    #                 }
    #                 attendance_list.append(attend_data)
    #         else:
    #             attendance = request.env['hr.attendance'].sudo().search([])
    #
    #         # Prepare the list of attendance
    #         attendance_list = []
    #         for attend in attendance:
    #             attend_data = {
    #                 'id': attend.id,
    #                 'employee_name': attend.employee_id.name,
    #                 'employee_no': attend.employee_id.employee_no or '',
    #                 'check_in': str(attend.check_in) or '',
    #                 'check_out': str(attend.check_out) or '',
    #                 'worked_hours': attend.worked_hours or '',
    #                 'process': attend.process or '',
    #             }
    #             attendance_list.append(attend_data)
    #
    #         # Prepare the response data
    #         response_data = {
    #             'status': '200',
    #             'response': attendance_list,
    #             'message': 'success'
    #         }
    #
    #         return werkzeug.wrappers.Response(
    #             status=200,
    #             content_type="application/json; charset=utf-8",
    #             response=json.dumps(response_data)
    #         )
    #
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while searching for attendance: %s", e)
    #
    #         error_response = {
    #             'status': 500,
    #             'error': "An error occurred while searching for attendance"
    #         }
    #         return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
    #                                      status=500)
    
    
    '''Code Added on April 22 2026 by Vijaya bhaskar'''
    # def _upsert_attendance(self, employee_no, check_in_str, check_out_str,
    #                        process, date_str):
    #     """
    #     Core upsert function implementing HHS attendance business rules.
    #
    #     Check-in  → keep EARLIEST (lesser) value
    #     Check-out → keep LATEST  (greater) value
    #
    #     Returns (record, created: bool, error_msg: str)
    #     """
    #     # -- Parse employee --
    #     employee = request.env['hr.employee'].sudo().search(
    #         [('employee_no', '=', employee_no)], limit=1
    #     )
    #     if not employee:
    #         return None, False, f"Employee not found with employee_no: {employee_no}"
    #
    #
    #
    #     # -- Parse datetimes safely --
    #     try:
    #         check_in_dt = (
    #             datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
    #             if check_in_str else None
    #         )
    #         check_out_dt = (
    #             datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S')
    #             if check_out_str else None
    #         )
    #         att_date = (
    #             datetime.strptime(date_str, '%Y-%m-%d').date()
    #             if date_str else None
    #         )
    #     except ValueError as e:
    #         return None, False, f"Invalid date format: {e}"
    #
    #     # -- Validate check_out year (1900 = null placeholder, reject it) --
    #     if check_out_dt and check_out_dt.year == 1900:
    #         check_out_dt = None
    #
    #     attendance_obj = request.env['hr.attendance'].sudo()
    #
    #     # -- Search for existing record by employee + date --
    #     existing = attendance_obj.search([
    #         ('employee_id', '=', employee.id),
    #         ('att_date', '=', att_date),
    #     ], limit=1)
    #
    #     if existing:
    #         # -------------------------------------------------------
    #         # Record EXISTS → apply min/max rules
    #         # -------------------------------------------------------
    #         update_vals = {}
    #         # Case : 1
    #         # Type : Mobile
    #         # CHECK-IN: keep the EARLIER (minimum) time
    #         # check_in_dt : 1900-01-01 00:00:00(API)
    #         # existing.check_in: 2026-04-27 08:43:34 (hr_attendance)
    #         # existing.check_out: None
    #         # check_out_dt :1900-01-01 00:00:00 (API)
    #
    #
    #          # Case : 2
    #         # Type : Finger Print
    #         # CHECK-IN: keep the EARLIER (minimum) time
    #         # check_in_dt : 2026-04-27 08:43:34(API)
    #         # existing.check_in: 1900-01-01 00:00:00  (hr_attendance)
    #         # existing.check_out: None
    #         # check_out_dt :1900-01-01 00:00:00 (API)
    #
    #
    #         # Case : 3
    #         # Type : Mobile
    #         # CHECK-IN: keep the EARLIER (minimum) time
    #         # check_in_dt : 1900-01-01 00:00:00(API)
    #         # existing.check_in: 2026-04-27 08:43:34 (hr_attendance)
    #
    #         # check_out_dt :2026-04-27 18:43:34 (API)
    #         # existing.check_out:1900-01-01 00:00:00  (hr_attendance)
    #
    #
    #         if check_in_dt:
    #             if existing.check_in: 
    #                 if check_in_dt < existing.check_in  and check_in_dt.year != 1900:
    #                     update_vals['check_in'] = check_in_dt
    #                     _logger.info(
    #                         "check_in updated to earlier value %s for employee %s",
    #                         check_in_dt, employee_no
    #                     )
    #                 else:
    #                     _logger.info(
    #                         "Existing check_in %s is already earlier; skipping update for employee %s",
    #                         existing.check_in, employee_no
    #                     )
    #             else:
    #                 # No check_in on record yet → just set it
    #                 update_vals['check_in'] = check_in_dt
    #
    #         # CHECK-OUT: keep the LATER (maximum) time
    #         if check_out_dt:
    #             if existing.check_out:
    #                 if check_out_dt > existing.check_out:
    #                     update_vals['check_out'] = check_out_dt
    #                     _logger.info(
    #                         "check_out updated to later value %s for employee %s",
    #                         check_out_dt, employee_no
    #                     )
    #                 else:
    #                     _logger.info(
    #                         "Existing check_out %s is already later; skipping update for employee %s",
    #                         existing.check_out, employee_no
    #                     )
    #             else:
    #                 # No check_out on record yet → just set it
    #                 update_vals['check_out'] = check_out_dt
    #
    #         # Process: update only if explicitly provided
    #         if process is not None:
    #             update_vals['process'] = process
    #
    #         if update_vals:
    #             existing.write(update_vals)
    #             _logger.info(
    #                 "Attendance record updated for employee %s on %s: %s",
    #                 employee_no, att_date, update_vals
    #             )
    #
    #         return existing, False, None  # False = not newly created
    #
    #     else:
    #         # -------------------------------------------------------
    #         # Record DOES NOT EXIST → create new
    #         # -------------------------------------------------------
    #         new_record = attendance_obj.create({
    #             'employee_id': employee.id,
    #             'check_in': check_in_dt,
    #             'check_out': check_out_dt,
    #             'process': process,
    #             'att_date': att_date,
    #         })
    #         _logger.info(
    #             "New attendance record created for employee %s on %s",
    #             employee_no, att_date
    #         )
    #         return new_record, True, None  # True = newly created
    
    def _upsert_attendance(self, employee_no, check_in_str, check_out_str,
                           process, date_str):

        # -------------------------------------------------------
        # Employee
        # -------------------------------------------------------
        employee = request.env['hr.employee'].sudo().search(
            [('employee_no', '=', employee_no)], limit=1
        )
        if not employee:
            return None, False, f"Employee not found: {employee_no}"

        # -------------------------------------------------------
        # Parse Dates
        # -------------------------------------------------------
        try:
            check_in_dt = (
                datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
                if check_in_str else None
            )
            check_out_dt = (
                datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S')
                if check_out_str else None
            )
            att_date = (
                datetime.strptime(date_str, '%Y-%m-%d').date()
                if date_str else None
            )
        except Exception as e:
            return None, False, f"Invalid date format: {e}"

        # -------------------------------------------------------
        # Ignore dummy values (1900)
        # -------------------------------------------------------
        if check_in_dt and check_in_dt.year == 1900:
            check_in_dt = None
        if check_out_dt and check_out_dt.year == 1900:
            check_out_dt = None

        attendance_obj = request.env['hr.attendance'].sudo()

        existing = attendance_obj.search([
            ('employee_id', '=', employee.id),
            ('att_date', '=', att_date),
        ], limit=1)

        # =======================================================
        # UPDATE EXISTING RECORD
        # =======================================================
        if existing:

            update_vals = {}
            process_should_reset = False

            # -------------------------------
            # CHECK-IN (EARLIEST)
            # -------------------------------
            if check_in_dt:
                if existing.check_in:
                    if check_in_dt < existing.check_in:
                        update_vals['check_in'] = check_in_dt
                        process_should_reset = True
                        _logger.info("Earlier check-in applied: %s", check_in_dt)
                else:
                    update_vals['check_in'] = check_in_dt
                    process_should_reset = True

            # -------------------------------
            # CHECK-OUT (LATEST)
            # -------------------------------
            if check_out_dt:
                if existing.check_out:
                    if check_out_dt > existing.check_out:
                        update_vals['check_out'] = check_out_dt
                        process_should_reset = True
                        _logger.info("Later check-out applied: %s", check_out_dt)
                else:
                    update_vals['check_out'] = check_out_dt
                    process_should_reset = True

            # -------------------------------
            # PROCESS RESET LOGIC
            # -------------------------------
            if process_should_reset and existing.process == 'yes':
                update_vals['process'] = 'no'
                _logger.info(
                    "Process reset to 'No' due to new punch for employee %s",
                    employee_no
                )

            # -------------------------------
            # WRITE ONLY IF CHANGE EXISTS
            # -------------------------------
            if update_vals:
                existing.write(update_vals)
                _logger.info(
                    "Attendance updated for %s on %s: %s",
                    employee_no, att_date, update_vals
                )
            else:
                _logger.info(
                    "No update needed for %s on %s",
                    employee_no, att_date
                )

            return existing, False, None

        # =======================================================
        # CREATE NEW RECORD
        # =======================================================
        else:
            new_record = attendance_obj.create({
                'employee_id': employee.id,
                'check_in': check_in_dt,
                'check_out': check_out_dt,
                'process': 'no',   # 🔥 ALWAYS No on first entry
                'att_date': att_date,
            })

            _logger.info(
                "New attendance created for %s on %s",
                employee_no, att_date
            )

            return new_record, True, None
    

    # =========================================================================
    # LEGACY ROUTE: POST /api/attendance/create
    # Kept for backward compatibility — other software still calls this URL.
    # Internally now runs _upsert_attendance instead of the old broken logic.
    #   - If record EXISTS  → compare and update (earliest check-in, latest check-out)
    #   - If record MISSING → create new record
    # =========================================================================
    @validate_token
    @http.route('/api/attendance/create', methods=["POST"], type="json",
                auth="none", csrf=False)
    def create_attendance(self, **post):
        try:
            _logger.info("Legacy /api/attendance/create — routing to upsert logic...")

            payload = json.loads(request.httprequest.data.decode())
            params  = payload.get('params', {})

            employee_no = params.get('employee_no')
            check_in    = params.get('check_in')
            check_out   = params.get('check_out')
            process     = params.get('process')
            date        = params.get('date')

            if not employee_no:
                return {"error": "employee_no is required."}, 400
            if not date:
                return {"error": "date is required."}, 400

            # Delegate entirely to upsert — handles create OR update correctly
            record, created, error = self._upsert_attendance(
                employee_no, check_in, check_out, process, date
            )

            if error:
                return {"error": error}, 404

            response_data = {
                "message": "Attendance created successfully." if created else "Attendance already existed and was updated.",
                "attendance": {
                    "employee_id": record.employee_id.name,
                    "check_in":    str(record.check_in)  if record.check_in  else '',
                    "check_out":   str(record.check_out) if record.check_out else '',
                    "process":     record.process or '',
                    "date":        str(record.att_date)  if record.att_date  else '',
                }
            }

            return response_data, 201 if created else 200

        except Exception as e:
            _logger.error("Legacy create_attendance error: %s", e)
            return {"error": "An error occurred while creating the attendance."}, 500

    # =========================================================================
    # LEGACY ROUTE: POST /api/attendance/update
    # Kept for backward compatibility — other software still calls this URL.
    # Internally now runs _upsert_attendance instead of the old broken logic.
    #   - If record EXISTS  → compare and update (earliest check-in, latest check-out)
    #   - If record MISSING → creates new record (safer than returning 404)
    # =========================================================================
    @validate_token
    @http.route('/api/attendance/update', methods=["POST"], type="json",
                auth="none", csrf=False)
    def update_attendance(self, **post):
        try:
            _logger.info("Legacy /api/attendance/update — routing to upsert logic...")

            payload = json.loads(request.httprequest.data.decode())
            params  = payload.get('params', {})

            employee_no = params.get('employee_no')
            check_in    = params.get('check_in')
            check_out   = params.get('check_out')
            process     = params.get('process')
            date        = params.get('date')

            if not employee_no:
                return {"error": "employee_no is required."}, 400
            if not date:
                return {"error": "date is required."}, 400

            # Delegate entirely to upsert — handles update OR create correctly
            record, created, error = self._upsert_attendance(
                employee_no, check_in, check_out, process, date
            )

            if error:
                return {"error": error}, 404

            response_data = {
                "message": "Attendance updated successfully." if not created else "Record not found — new attendance created.",
                "attendance": {
                    "employee_id": record.employee_id.name,
                    "check_in":    str(record.check_in)  if record.check_in  else '',
                    "check_out":   str(record.check_out) if record.check_out else '',
                    "process":     record.process or '',
                    "date":        str(record.att_date)  if record.att_date  else '',
                }
            }

            return response_data, 200 if not created else 201

        except Exception as e:
            _logger.error("Legacy update_attendance error: %s", e)
            return {"error": "An error occurred while updating the attendance."}, 500

    # =========================================================================
    # SEARCH: GET /api/attendance/search
    # =========================================================================
    # @validate_token
    # @http.route("/api/attendance/search", methods=["GET"], type="http",
    #             auth="none", csrf=False)
    # def attendance_search(self):
    #     """
    #     Search attendance records.
    #     Query params: check_in (date YYYY-MM-DD), employee_no
    #     Both filters are INDEPENDENT — either or both can be used.
    #     """
    #     try:
    #         _logger.info("Searching attendance records...")
    #
    #         check_in_date = request.params.get("check_in")
    #         employee_no   = request.params.get("employee_no")
    #
    #         domain = []
    #
    #         # Filter by check_in date (full day range)
    #         if check_in_date:
    #             domain.append(('check_in', '>=', check_in_date + ' 00:00:00'))
    #             domain.append(('check_in', '<=', check_in_date + ' 23:59:59'))
    #
    #         # Filter by employee_no — INDEPENDENT of check_in filter
    #         if employee_no:
    #             employee = request.env['hr.employee'].sudo().search(
    #                 [('employee_no', '=', employee_no)], limit=1
    #             )
    #             if not employee:
    #                 return request.make_response(
    #                     json.dumps({'status': 404, 'error': 'Employee not found.'}),
    #                     headers={'Content-Type': 'application/json'},
    #                     status=404
    #                 )
    #             domain.append(('employee_id', '=', employee.id))
    #
    #         records = request.env['hr.attendance'].sudo().search(domain)
    #
    #         attendance_list = [
    #             {
    #                 'id': rec.id,
    #                 'employee_name': rec.employee_id.name,
    #                 'employee_no': rec.employee_id.employee_no or '',
    #                 'check_in': str(rec.check_in) if rec.check_in else '',
    #                 'check_out': str(rec.check_out) if rec.check_out else '',
    #                 # Fix: use `is not None` to preserve 0.0 worked_hours
    #                 'worked_hours': rec.worked_hours if rec.worked_hours is not None else '',
    #                 'process': rec.process or '',
    #             }
    #             for rec in records
    #         ]
    #
    #         return werkzeug.wrappers.Response(
    #             status=200,
    #             content_type="application/json; charset=utf-8",
    #             response=json.dumps({
    #                 'status': '200',
    #                 'response': attendance_list,
    #                 'message': 'success',
    #                 'total': len(attendance_list),
    #             })
    #         )
    #
    #     except Exception as e:
    #         _logger.error("Search error: %s", e)
    #         return request.make_response(
    #             json.dumps({'status': 500, 'error': 'An error occurred while searching attendance.'}),
    #             headers={'Content-Type': 'application/json'},
    #             status=500
    #         )
    
    @validate_token
    @http.route("/api/attendance/search", methods=["GET"], type="http",
                auth="none", csrf=False)
    def attendance_search(self):
        try:
            _logger.info("Searching attendance records...")
    
            check_in_date = request.params.get("check_in")
            employee_no   = request.params.get("employee_no")
    
            domain = []
    
            # --------------------------------------------------
            # Filter by DATE (Correct way → use att_date)
            # --------------------------------------------------
            if check_in_date:
                try:
                    date_obj = datetime.strptime(check_in_date, '%Y-%m-%d').date()
                    domain.append(('att_date', '=', date_obj))
                except Exception:
                    return request.make_response(
                        json.dumps({'status': 400, 'error': 'Invalid date format. Use YYYY-MM-DD'}),
                        headers={'Content-Type': 'application/json'},
                        status=400
                    )
    
            # --------------------------------------------------
            # Filter by employee_no
            # --------------------------------------------------
            if employee_no:
                employee = request.env['hr.employee'].sudo().search(
                    [('employee_no', '=', employee_no)], limit=1
                )
                if not employee:
                    return request.make_response(
                        json.dumps({'status': 404, 'error': 'Employee not found'}),
                        headers={'Content-Type': 'application/json'},
                        status=404
                    )
    
                domain.append(('employee_id', '=', employee.id))
    
            # --------------------------------------------------
            # Search with ordering
            # --------------------------------------------------
            records = request.env['hr.attendance'].sudo().search(
                domain,
                order='att_date desc, employee_id asc'
            )
    
            # --------------------------------------------------
            # Response
            # --------------------------------------------------
            attendance_list = []
            for rec in records:
                attendance_list.append({
                    'id': rec.id,
                    'employee_name': rec.employee_id.name,
                    'employee_no': rec.employee_id.employee_no or '',
                    'date': str(rec.att_date) if rec.att_date else '',
                    'check_in': str(rec.check_in) if rec.check_in else '',
                    'check_out': str(rec.check_out) if rec.check_out else '',
                    'worked_hours': rec.worked_hours if rec.worked_hours is not None else '',
                    'process': rec.process or '',
                })
    
            return request.make_response(
                json.dumps({
                    'status': 200,
                    'message': 'success',
                    'total': len(attendance_list),
                    'response': attendance_list
                }),
                headers={'Content-Type': 'application/json'},
                status=200
            )
    
        except Exception as e:
            _logger.error("Search error: %s", e)
            return request.make_response(
                json.dumps({'status': 500, 'error': 'Internal server error'}),
                headers={'Content-Type': 'application/json'},
                status=500
            )
    ##### Working Code Commented on April 22 2026 by Vijaya bhaskar becuase they want check in earlier and check out maximum
    # @validate_token
    # @http.route("/api/attendance/search", methods=["GET"], type="http", auth="none", csrf=False)
    # def _attendance_search_all(self):
    #     try:
    #         _logger.info("Attempting to search for attendance...")
    #
    #         check_in = request.params.get("check_in")
    #         # check_out = request.params.get("check_out")
    #         employee_no = request.params.get("employee_no")
    #
    #         domain = []
    #
    #         if check_in:
    #             domain.append(('check_in', '>=', check_in + ' 00:00:00'))
    #             domain.append(('check_in', '<=', check_in + ' 23:59:59'))
    #         # if check_out:
    #         #     domain.append(('check_out', '>=', check_out + ' 00:00:00'))
    #         #     domain.append(('check_out', '<=', check_out + ' 23:59:59'))
    #
    #         if employee_no:
    #             employee = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
    #             if employee:
    #                 domain.append(('employee_id', '=', employee.id))
    #             else:
    #                 return request.make_response(json.dumps({
    #                     'status': 404,
    #                     'error': 'Employee not found.'
    #                 }), headers={'Content-Type': 'application/json'}, status=404)
    #
    #         attendance = request.env['hr.attendance'].sudo().search(domain)
    #
    #         # Prepare the list of attendance
    #         attendance_list = []
    #         for attend in attendance:
    #             attend_data = {
    #                 'id': attend.id,
    #                 'employee_name': attend.employee_id.name,
    #                 'employee_no': attend.employee_id.employee_no or '',
    #                 'check_in': str(attend.check_in) or '',
    #                 'check_out': str(attend.check_out) or '',
    #                 'worked_hours': attend.worked_hours or '',
    #                 'process': attend.process or '',
    #             }
    #             attendance_list.append(attend_data)
    #
    #         # Prepare the response data
    #         response_data = {
    #             'status': '200',
    #             'response': attendance_list,
    #             'message': 'success'
    #         }
    #
    #         return werkzeug.wrappers.Response(
    #             status=200,
    #             content_type="application/json; charset=utf-8",
    #             response=json.dumps(response_data)
    #         )
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while searching for attendance: %s", e)
    #
    #         error_response = {
    #             'status': 500,
    #             'error': "An error occurred while searching for attendance"
    #         }
    #         return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
    #                                      status=500)
    #
    # ### Newly Added this code Attendance update method on 25/11/2024
    # @validate_token
    # @http.route('/api/attendance/update', methods=["POST"], type="json", auth="none", csrf=False)
    # def update_attendance(self, **post):
    #     try:
    #         _logger.info("Attempting to update attendance...")
    #
    #         # Decode and parse the JSON payload
    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)
    #         payload = json.loads(payload)
    #
    #         # Extract parameters
    #         params = payload.get('params', {})
    #         _logger.debug("params: %s", params)
    #
    #         employee_no = params.get('employee_no')
    #         check_in = params.get('check_in')
    #         check_out = params.get('check_out')
    #         process = params.get('process')
    #         date = params.get('date')
    #
    #         _logger.info("Updating attendance for employee number: %s", employee_no)
    #
    #         # Search for the employee with the given employee number
    #         employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
    #         if not employee_obj:
    #             _logger.warning("Employee not found with employee number: %s", employee_no)
    #             return {
    #                 "error": "Employee not found."
    #             }, 404
    #
    #         attendance_obj = request.env['hr.attendance']
    #
    #         # Parse the dates
    #         check_in_date = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S') if check_in else None
    #         check_out_date = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S') if check_out else None
    #         check_out_year = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S').year if check_out else None
    #         date = datetime.strptime(date, '%Y-%m-%d').date() if date else None
    #
    #         # Search for attendance by check-in or check-out
    #         attendance_record_check_in = attendance_obj.sudo().search([
    #             ('employee_id', '=', employee_obj.id),
    #             ('att_date', '=', date),
    #             ('check_in', '=', check_in_date),
    #         ])
    #
    #         # attendance_record_check_out = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id),
    #         #     ('att_date', '=', date),
    #         #     ('check_out', '=', check_out_date),
    #         # ], limit=1)
    #
    #         # Check if either record exists
    #         attendance_record = attendance_record_check_in
    #         if not attendance_record:
    #             _logger.warning("Attendance record not found for Employee No: %s on date: %s", employee_no, date)
    #             return {
    #                 "error": "Attendance record not found for the given employee and date."
    #             }, 404
    #
    #         # Update the attendance record based on provided values
    #         if attendance_record:
    #             if check_in_date == attendance_record.check_in and check_out_year != 1900:
    #                 attendance_record.sudo().write({
    #                     'check_in': check_in_date or attendance_record.check_in,
    #                     'check_out': check_out_date or attendance_record.check_out,
    #                     'process': process or attendance_record.process,
    #                 })
    #
    #                 _logger.info("Attendance updated successfully for Employee No: %s", employee_no)
    #
    #                 # Prepare response data
    #                 response_data = {
    #                     "message": "Attendance updated successfully.",
    #                     "attendance": {
    #                         'employee_id': attendance_record.employee_id.name,
    #                         'check_in': attendance_record.check_in,
    #                         'check_out': attendance_record.check_out,
    #                         'process': attendance_record.process,
    #                         'date': attendance_record.att_date,
    #                     }
    #                 }
    #
    #                 return response_data, 200
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while updating the attendance: %s", e)
    #         return {
    #             "error": "An error occurred while updating the attendance."
    #         }, 500
    #
    # ### Newly Added this code Attendance Create method on 25/11/2024
    # @validate_token
    # @http.route('/api/attendance/create', methods=["POST"], type="json", auth="none", csrf=False)
    # def create_attendance(self, **post):
    #     try:
    #         _logger.info("Attempting to create attendance...")
    #
    #         # Decode the payload data
    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)
    #
    #         # Parse the JSON payload
    #         payload = json.loads(payload)
    #
    #         # Extract parameters from the payload
    #         params = payload.get('params', {})
    #         _logger.debug("params: %s", params)
    #
    #         employee_no = params.get('employee_no')
    #         check_in = params.get('check_in')
    #         check_out = params.get('check_out')
    #         # worked_hours = params.get('worked_hours')
    #         process = params.get('process')
    #         date = params.get('date')
    #
    #
    #
    #         _logger.info("Creating attendance for employee number: %s", employee_no)
    #
    #         # Search for the employee with the given employee number
    #         employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
    #         if not employee_obj:
    #             _logger.warning("Employee not found with employee number: %s", employee_no)
    #             return {
    #                 "error": "Employee not found."
    #             }, 404
    #
    #         attendance_obj = request.env['hr.attendance']
    #
    #         # # Extract only the date part from check_in and check_out
    #         # check_in_date = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S').date()
    #         # check_out_date = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S').date()
    #         check_in_date = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S') if check_in else None
    #         check_out_date = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S') if check_out else None
    #         date = datetime.strptime(date, '%Y-%m-%d').date() if date else None
    #
    #         _logger.debug("check_in_date: %s, check_out_date: %s", check_in_date, check_out_date)
    #
    #         # Check for duplicate attendance records
    #         # attendance_obj_duplicate = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id)
    #         # ])
    #         # if attendance_obj_duplicate:
    #         #     for check in attendance_obj_duplicate:
    #         #         # existing_check_in_date = check.check_in.date()
    #         #         existing_check_in_date = check.check_in
    #         #         print("existing_check_in_date", existing_check_in_date)
    #         #         # existing_check_out_date = check.check_out.date()
    #         #         existing_check_out_date = check.check_out
    #         #         print("existing_check_out_date", existing_check_out_date)
    #         #
    #         #         _logger.debug("existing_check_in_date: %s, existing_check_out_date: %s", existing_check_in_date,
    #         #                       existing_check_out_date)
    #         #
    #         #         # if existing_check_in_date == check_in_date and existing_check_out_date == check_out_date:
    #         #         if (existing_check_in_date >= check_in_date <= existing_check_in_date) and (existing_check_out_date >= check_out_date <= existing_check_out_date):
    #         #             _logger.warning("Duplicate attendance found for Employee No: %s", employee_no)
    #         #             return {
    #         #                 "error": "Attendance with this 'employee_no', 'check_in', and 'check_out' already exists."
    #         #             }, 400
    #         #         # else:
    #         #         # if not attendance_obj_duplicate:
    #         # new_attendance = attendance_obj.create({
    #         #     'employee_id': employee_obj.id,
    #         #     'check_in': check_in,
    #         #     'check_out': check_out,
    #         #     # 'worked_hours': worked_hours,
    #         #     'process': process,
    #         # })
    #         #
    #         # if new_attendance:
    #         #     _logger.info("Attendance created successfully for Employee No: %s", employee_no)
    #         #
    #         #     # Prepare response data
    #         #     response_data = {
    #         #         "message": "Attendance created successfully.",
    #         #         "attendance": {
    #         #             'employee_id': new_attendance.employee_id.name,
    #         #             'check_in': new_attendance.check_in,
    #         #             'check_out': new_attendance.check_out,
    #         #             # 'worked_hours': new_attendance.worked_hours,
    #         #             'process': new_attendance.process,
    #         #         }
    #         #     }
    #         #
    #         #     return response_data, 201
    #
    #         # Check for duplicate attendance records based on `check_in` and `check_out`
    #         # duplicate_check_in = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id),
    #         #     ('check_in', '<=', check_in_date),
    #         #     ('check_out', '>=', check_in_date)
    #         # ])
    #         # duplicate_check_out = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id),
    #         #     ('check_in', '<=', check_out_date),
    #         #     ('check_out', '>=', check_out_date)
    #         # ])
    #         # duplicate_date = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id),
    #         #     ('check_in', '>=', check_in_date),
    #         #     ('check_out', '<=', check_out_date)
    #         # ])
    #         duplicate_check_in = attendance_obj.sudo().search([
    #             ('employee_id', '=', employee_obj.id),
    #             ('check_in', '=', check_in_date),
    #             ('att_date', '=', date)
    #         ])
    #         # duplicate_check_out = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id),
    #         #     # ('check_in', '<=', check_out_date),
    #         #     ('check_out', '=', check_out_date),
    #         #     ('att_date', '=', date)
    #         # ])
    #         duplicate_date = attendance_obj.sudo().search([
    #             ('employee_id', '=', employee_obj.id),
    #             ('check_in', '>=', check_in_date),
    #             ('check_out', '<=', check_out_date),
    #             ('att_date', '=', date)
    #         ])
    #
    #         # if duplicate_check_in or duplicate_check_out or duplicate_date:
    #         #     _logger.warning("Duplicate attendance found for Employee No: %s", employee_no)
    #         #     return {
    #         #         "error": "Duplicate attendance record found for the given time or date."
    #         #     }, 400
    #
    #
    #         if duplicate_date:
    #             _logger.warning("Duplicate attendance found for Employee No: %s", employee_no)
    #             return {
    #                 "error": "Duplicate attendance record found for the given time or duplicate_date."
    #             }, 400
    #
    #         if duplicate_check_in:
    #             _logger.warning("Duplicate attendance found for Employee No: %s", employee_no)
    #             return {
    #                 "error": "Duplicate attendance record found for the given time or duplicate_check_in."
    #             }, 400
    #
    #         # if duplicate_check_out:
    #         #     _logger.warning("Duplicate attendance found for Employee No: %s", employee_no)
    #         #     return {
    #         #         "error": "Duplicate attendance record found for the given time or duplicate_check_out."
    #         #     }, 400
    #
    #         # attendance_obj_duplicate = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id)
    #         # ])
    #         #
    #         # if attendance_obj_duplicate:
    #         #     for check in attendance_obj_duplicate:
    #         #         existing_check_in_date = check.check_in
    #         #         print("existing_check_in_date", existing_check_in_date)
    #         #         existing_check_out_date = check.check_out
    #         #         print("existing_check_out_date", existing_check_out_date)
    #         #
    #         #         _logger.debug("existing_check_in_date: %s, existing_check_out_date: %s", existing_check_in_date,
    #         #                       existing_check_out_date)
    #         #
    #         #         # Check if the new record overlaps with any existing record
    #         #         # if (check_in_date <= existing_check_out_date and check_out_date >= existing_check_in_date):
    #         #         if (check_in_date <= existing_check_out_date and check_out_date >= existing_check_in_date):
    #         #             _logger.warning("Duplicate attendance found for Employee No: %s", employee_no)
    #         #             return {
    #         #                 "error": "Attendance with this 'employee_no', 'check_in', and 'check_out' already exists."
    #         #             }, 400
    #
    #         # Create new attendance record if no duplicates were found
    #         new_attendance = attendance_obj.create({
    #             'employee_id': employee_obj.id,
    #             'check_in': check_in,
    #             'check_out': check_out,
    #             'process': process,
    #             'att_date': date,
    #         })
    #
    #         if new_attendance:
    #             _logger.info("Attendance created successfully for Employee No: %s", employee_no)
    #
    #             # Prepare response data
    #             response_data = {
    #                 "message": "Attendance created successfully.",
    #                 "attendance": {
    #                     'employee_id': new_attendance.employee_id.name,
    #                     'check_in': new_attendance.check_in,
    #                     'check_out': new_attendance.check_out,
    #                     'process': new_attendance.process,
    #                     'date': new_attendance.att_date,
    #
    #                 }
    #             }
    #
    #             return response_data, 201
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while creating the attendance: %s", e)
    #         return {
    #             "error": "An error occurred while creating the attendance"
    #         }, 500

    ### Date wise consider this code correctly working commanded on 22/11/2024
    # @validate_token
    # @http.route('/api/attendance/create', methods=["POST"], type="json", auth="none", csrf=False)
    # def create_attendance(self, **post):
    #     try:
    #         _logger.info("Attempting to create attendance...")
    #
    #         # Decode the payload data
    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)
    #
    #         # Parse the JSON payload
    #         payload = json.loads(payload)
    #
    #         # Extract parameters from the payload
    #         params = payload.get('params', {})
    #         _logger.debug("params: %s", params)
    #
    #         employee_no = params.get('employee_no')
    #         check_in = params.get('check_in')
    #         check_out = params.get('check_out')
    #         process = params.get('process')
    #         date = params.get('date')
    #
    #         # Log employee information
    #         _logger.info("Creating attendance for employee number: %s", employee_no)
    #
    #         # Search for the employee with the given employee number
    #         employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)], limit=1)
    #         if not employee_obj:
    #             _logger.warning("Employee not found with employee number: %s", employee_no)
    #             return {
    #                 "error": "Employee not found."
    #             }, 404
    #
    #         attendance_obj = request.env['hr.attendance']
    #
    #         # Convert check_in and check_out to datetime objects
    #         check_in_date = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
    #         check_out_date = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
    #         _logger.debug("check_in_date: %s, check_out_date: %s", check_in_date, check_out_date)
    #
    #         # Check for overlapping attendance records
    #         # attendance_obj_duplicate = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id),
    #         #     '|', '&',
    #         #     ('check_in', '<=', check_out_date), ('check_in', '>=', check_in_date),
    #         #     '&',
    #         #     ('check_out', '>=', check_in_date), ('check_out', '<=', check_out_date)
    #         # ])
    #
    #
    #         ## Already working code
    #         # attendance_obj_duplicate = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id),
    #         #     '|',
    #         #     '&', ('check_in', '<=', check_out_date), ('check_out', '>=', check_in_date),
    #         #     '&', ('check_in', '<=', check_in_date), ('check_out', '>=', check_out_date)
    #         # ])
    #
    #         # # Check for duplicate records (att_date and overlapping time validation)
    #         # duplicate_attendance = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id),
    #         #     ('att_date', '=', date),
    #         #     '|',
    #         #     '&', ('check_in', '<=', check_out_date), ('check_out', '>=', check_in_date),  # Overlapping time
    #         #     '&', ('check_in', '>=', check_in_date), ('check_out', '<=', check_out_date)  # Fully enclosed
    #         # ])
    #
    #         # if duplicate_attendance:
    #         #     _logger.warning("Duplicate attendance found for Employee No: %s", employee_no)
    #         #     return {
    #         #         "error": "Duplicate attendance found for the given date or overlapping time."
    #         #     }, 400
    #
    #         # attendance_obj_duplicate = attendance_obj.sudo().search([
    #         #     ('employee_id', '=', employee_obj.id),
    #         #     ('check_in', '>=', check_in_date), ('check_out', '<=', check_out_date)
    #         # ])
    #         attendance_obj_duplicate = attendance_obj.sudo().search([
    #             ('employee_id', '=', employee_obj.id),
    #             ('att_date', '=', date)
    #         ])
    #
    #         if attendance_obj_duplicate:
    #             _logger.warning("Duplicate attendance found for Employee No: %s", employee_no)
    #             return {
    #                 # "error": "Attendance with overlapping 'check_in' and 'check_out' already exists."
    #                 "error": "Attendance with overlapping 'date' already exists."
    #             }, 400
    #
    #         # Create a new attendance record
    #         new_attendance = attendance_obj.sudo().create({
    #             'employee_id': employee_obj.id,
    #             'check_in': check_in,
    #             'check_out': check_out,
    #             'process': process,
    #             'att_date': date,
    #         })
    #
    #         if new_attendance:
    #             _logger.info("Attendance created successfully for Employee No: %s", employee_no)
    #
    #             # Prepare response data
    #             response_data = {
    #                 "message": "Attendance created successfully.",
    #                 "attendance": {
    #                     'employee_id': new_attendance.employee_id.name,
    #                     'check_in': new_attendance.check_in,
    #                     'check_out': new_attendance.check_out,
    #                     'process': new_attendance.process,
    #                     'date': new_attendance.att_date,
    #                 }
    #             }
    #
    #             return response_data, 201
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while creating the attendance: %s", e)
    #         return {
    #             "error": "An error occurred while creating the attendance."
    #         }, 500

    # @validate_token
    # @http.route('/api/attendance/update', methods=["POST"], type="json", auth="none", csrf=False)
    # def update_attendance(self, **post):
    #     try:
    #         _logger.info("Attempting to update attendance...")
    #
    #         # Decode the payload data
    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)
    #
    #         # Parse the JSON payload
    #         payload = json.loads(payload)
    #         _logger.debug("payload: %s", payload)
    #
    #         # Extract parameters from the payload
    #         params = payload.get('params', {})
    #         _logger.debug("params: %s", params)
    #
    #         employee_no = params.get('employee_no')
    #         check_in_str = params.get('check_in')
    #         check_out_str = params.get('check_out')
    #         process = params.get('process')
    #         att_date_str = params.get('date')
    #
    #         # Parse check_in and check_out as datetime objects
    #         check_in = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S') if check_in_str else None
    #         check_out = datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S') if check_out_str else None
    #         att_date = datetime.strptime(att_date_str, '%Y-%m-%d').date()
    #
    #         _logger.info("Updating attendance for employee number: %s", employee_no)
    #
    #         # Search for the employee with the given employee number
    #         employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
    #         if not employee_obj:
    #             _logger.warning("Employee not found with employee number: %s", employee_no)
    #             return {
    #                 "error": "Employee not found."
    #             }, 404
    #
    #         # Search for the attendance record with the given employee ID
    #         attendance_obj = request.env['hr.attendance'].sudo().search([
    #             ('employee_id', '=', employee_obj.id)
    #         ])
    #
    #         if attendance_obj:
    #             updated = False
    #             for attendance in attendance_obj:
    #                 _logger.debug("Current attendance record: %s", attendance)
    #
    #                 # Update the attendance record if it matches the check_in and check_out times
    #                 if attendance.check_in <= check_in <= attendance.check_out or attendance.check_in <= check_out <= attendance.check_out:
    #                     attendance.write({
    #                         'check_in': check_in if check_in else attendance.check_in,
    #                         'check_out': check_out if check_out else attendance.check_in,
    #                         'process': process,
    #                     })
    #                     _logger.info("Attendance updated successfully for employee number: %s", employee_no)
    #                     updated = True
    #
    #             if updated:
    #                 return {
    #                     "success": True,
    #                     "message": f"Attendance updated for employee: {employee_obj.name}"
    #                 }, 200
    #             else:
    #                 _logger.warning("No matching attendance record found for employee number: %s", employee_no)
    #                 return {
    #                     "error": "Attendance record not found."
    #                 }, 404
    #         else:
    #             _logger.warning("Attendance record not found for employee number: %s", employee_no)
    #             return {
    #                 "error": "Attendance record not found."
    #             }, 404
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while updating the attendance: %s", e)
    #         return {
    #             "error": "An error occurred while updating the attendance"
    #         }, 500

    ## Date wise consider this code correctly working commanded on 22/11/2024
    # @validate_token
    # @http.route('/api/attendance/update', methods=["POST"], type="json", auth="none", csrf=False)
    # def update_attendance(self, **post):
    #     try:
    #         _logger.info("Attempting to update attendance...")
    #
    #         # Decode the payload data
    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)
    #
    #         # Parse the JSON payload
    #         payload = json.loads(payload)
    #         _logger.debug("payload: %s", payload)
    #
    #         # Extract parameters from the payload
    #         params = payload.get('params', {})
    #         _logger.debug("params: %s", params)
    #
    #         employee_no = params.get('employee_no')
    #         check_in_str = params.get('check_in')
    #         check_out_str = params.get('check_out')
    #         att_date_str = params.get('date')
    #         process = params.get('process')
    #
    #         # if not employee_no or not check_in_str or not check_out_str or not att_date_str:
    #         #     _logger.warning("Missing required parameters in payload")
    #         #     return {
    #         #         "error": "Missing required parameters."
    #         #     }, 400
    #         if not employee_no or not att_date_str:
    #             _logger.warning("Missing required parameters in payload")
    #             return {
    #                 "error": "Missing required parameters."
    #             }, 400
    #
    #         # Parse check_in, check_out, and att_date as datetime/date objects
    #         check_in = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
    #         check_out = datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S')
    #         att_date = datetime.strptime(att_date_str, '%Y-%m-%d').date()
    #
    #         _logger.info("Updating attendance for employee number: %s on date: %s", employee_no, att_date)
    #
    #         # Search for the employee with the given employee number
    #         employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
    #         if not employee_obj:
    #             _logger.warning("Employee not found with employee number: %s", employee_no)
    #             return {
    #                 "error": "Employee not found."
    #             }, 404
    #
    #         # Search for the attendance record with the given employee ID and att_date
    #         attendance_obj = request.env['hr.attendance'].sudo().search([
    #             ('employee_id', '=', employee_obj.id),
    #             ('att_date', '=', att_date)
    #         ])
    #
    #         if attendance_obj:
    #             for attendance in attendance_obj:
    #                 _logger.debug("Current attendance record: %s", attendance)
    #
    #                 # Update the attendance record directly if found
    #                 attendance.write({
    #                     'check_in': check_in if check_in else attendance.check_in,
    #                     'check_out': check_out if check_out else attendance.check_out,
    #                     'process': process,
    #                 })
    #                 _logger.info("Attendance updated successfully for employee number: %s", employee_no)
    #
    #             return {
    #                 "success": True,
    #                 "message": f"Attendance updated for employee: {employee_obj.name}"
    #             }, 200
    #         else:
    #             _logger.warning("Attendance record not found for employee number: %s", employee_no)
    #             return {
    #                 "error": "Attendance record not found."
    #             }, 404
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while updating the attendance: %s", e)
    #         return {
    #             "error": "An error occurred while updating the attendance."
    #         }, 500

    @validate_token
    @http.route('/api/attendance/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_attendance(self, **post):
        try:
            _logger.info("Attempting to delete attendance...")

            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            _logger.debug("payload: %s", payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            employee_no = params.get('employee_no')
            check_in_str = params.get('check_in')
            # check_out_str = params.get('check_out')

            # Parse check_in and check_out as datetime objects
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
            # check_out = datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S')

            _logger.info("Deleting attendance for employee number: %s", employee_no)

            # Search for the employee with the given employee number
            employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
            if not employee_obj:
                _logger.warning("Employee not found with employee number: %s", employee_no)
                return {
                    "error": "Employee not found."
                }, 404

            # Search for the attendance record with the given employee ID and date range
            attendance_obj = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee_obj.id),
                ('check_in', '>=', check_in), ('check_in', '<=', check_in)
            ])

            if attendance_obj:
                attendance_obj.sudo().unlink()
                _logger.info("Attendance deleted successfully for employee number: %s", employee_no)
                return {
                    "success": True,
                    "message": f"Attendance deleted for employee: {employee_obj.name}"
                }, 200
            else:
                _logger.warning("Attendance record not found for employee number: %s", employee_no)
                return {
                    "error": "Attendance record not found."
                }, 404

        except Exception as e:
            _logger.error("An error occurred while deleting the attendance: %s", e)
            return {
                "error": "An error occurred while deleting the attendance"
            }, 500

    # @validate_token
    # @http.route("/api/attendance_sheet/search", methods=["GET"], type="http", auth="none", csrf=False)
    # def _attendance_sheet_search_all(self):
    #     try:
    #         _logger.info("Attempting to search for attendance_sheet...")
    #
    #         employee_no = request.params.get("employee_no")
    #         employee = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
    #
    #         if employee_no:
    #             attendance_sheet = request.env['hr.attendance.sheet'].sudo().search([('employee_id', '=', employee.id)])
    #         else:
    #             attendance_sheet = request.env['hr.attendance.sheet'].sudo().search([])
    #
    #         # Prepare the list of attendance
    #         attendance_sheet_list = []
    #         for attend in attendance_sheet:
    #             attend_data = {
    #                 'id': attend.id,
    #                 'employee_name': attend.employee_id.name or '',
    #                 'ATTH_EMPCODE': attend.employee_id.employee_no or '',
    #                 'ATTH_FROMDATE': str(attend.request_date_from) or '',
    #                 'ATTH_TODATE': str(attend.request_date_to) or '',
    #                 'ATTH_NO_LATEIN': attend.no_latein or '',
    #                 'ATTH_TOTAL_LATEIN': attend.total_latein or '',
    #                 'ATTH_NO_OVERTIME': attend.no_overtime or '',
    #                 'ATTH_TOTAL_OVERTIME': attend.total_overtime or '',
    #                 'ATTH_NO_DIFFTIME': attend.no_difftime or '',
    #                 'ATTH_TOTAL_DIFFTIME': attend.total_difftime or '',
    #                 'ATTH_NO_ABSENCE': attend.no_absence or '',
    #                 'ATTH_TOTAL_ABSENCE': attend.total_absence or '',
    #                 'ATTH_LATEIN_TOTAMOUNT': attend.latein or '',
    #                 'ATTH_OVERTIME_TOTAMOUNT': attend.overtime or '',
    #                 'ATTH_DIFFTIME_TOTAMOUNT': attend.time_different or '',
    #                 'ATTH_ABSENCE_TOTAMOUNT': attend.absent or '',
    #
    #             }
    #             attendance_sheet_list.append(attend_data)
    #
    #         # Prepare the response data
    #         response_data = {
    #             'status': '200',
    #             'response': attendance_sheet_list,
    #             'message': 'success'
    #         }
    #
    #         return werkzeug.wrappers.Response(
    #             status=200,
    #             content_type="application/json; charset=utf-8",
    #             response=json.dumps(response_data)
    #         )
    #
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while searching for attendance_sheet: %s", e)
    #
    #         error_response = {
    #             'status': 500,
    #             'error': "An error occurred while searching for attendance_sheet"
    #         }
    #         return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
    #                                      status=500)

    @validate_token
    @http.route("/api/attendance_sheet/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _attendance_sheet_search_all(self):
        try:
            _logger.info("Attempting to search for attendance_sheet...")

            employee_no = request.params.get("employee_no")
            request_date_from = request.params.get("request_date_from")
            request_date_to = request.params.get("request_date_to")
            # create_date = request.params.get("create_date")
            # write_date = request.params.get("write_date")

            domain = []

            if employee_no:
                employee = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
                if employee:
                    domain.append(('employee_id', '=', employee.id))
                else:
                    return request.make_response(json.dumps({
                        'status': 404,
                        'error': 'Employee not found.'
                    }), headers={'Content-Type': 'application/json'}, status=404)

            # Filter by date range
            # if request_date_from and request_date_to:
            #     domain.append(
            #         ('request_date_from', '>=', request_date_from),
            #         ('request_date_to', '<=', request_date_to)
            #     )
            #     domain.append(('request_date_to', '<=', request_date_to))
            # elif request_date_from:
            #     domain.append(('request_date_from', '>=', request_date_from))
            # elif request_date_to:
            #     domain.append(('request_date_to', '<=', request_date_to))

            if request_date_from:
                domain.append(('request_date_from', '>=', request_date_from))

            if request_date_to:
                domain.append(('request_date_to', '<=', request_date_to))

            domain.append(('export_sheet', '=', 'no'))

            # if create_date:
            #     domain.append(('create_date', '>=', create_date))
            #
            # if write_date:
            #     domain.append(('write_date', '<=', write_date))

            # # Search for attendance sheets based on the constructed domain
            #
            # attendance_sheet = request.env['hr.attendance.sheet'].sudo().search(domain)

            # Perform search based on domain, or search all if domain is empty
            if domain:
                attendance_sheet = request.env['hr.attendance.sheet'].sudo().search(domain)
            else:
                attendance_sheet = request.env['hr.attendance.sheet'].sudo().search([('export_sheet', '=', 'no')])

            # Prepare the list of attendance sheets
            attendance_sheet_list = []
            for attend in attendance_sheet:
                attend_data = {
                    'id': attend.id,
                    'employee_name': attend.employee_id.name or '',
                    'ATTH_EMPCODE': attend.employee_id.employee_no or '',
                    'ATTH_FROMDATE': str(attend.request_date_from) or '',
                    'ATTH_TODATE': str(attend.request_date_to) or '',
                    'ATTH_NO_LATEIN': attend.no_latein or '',
                    'ATTH_TOTAL_LATEIN': attend.total_latein or '',
                    'ATTH_NO_OVERTIME': attend.no_overtime or '',
                    'ATTH_TOTAL_OVERTIME': attend.total_overtime or '',
                    'ATTH_NO_DIFFTIME': attend.no_difftime or '',
                    'ATTH_TOTAL_DIFFTIME': attend.total_difftime or '',
                    'ATTH_NO_ABSENCE': attend.no_absence or '',
                    'ATTH_TOTAL_ABSENCE': attend.total_absence or '',
                    'ATTH_LATEIN_TOTAMOUNT': attend.latein or '',
                    'ATTH_OVERTIME_TOTAMOUNT': attend.overtime or '',
                    'ATTH_DIFFTIME_TOTAMOUNT': attend.time_different or '',
                    'ATTH_ABSENCE_TOTAMOUNT': attend.absent or '',
                    'create_date': str(attend.create_date.date()) or '',
                    'write_date': str(attend.write_date.date()) or '',
                    'export_sheet': attend.export_sheet or '',
                    # 'create_date': str(attend.create_date) or '',
                    # 'write_date': str(attend.write_date) or '',
                }
                attendance_sheet_list.append(attend_data)
                attend.write({'export_sheet': 'yes'})

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': attendance_sheet_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for attendance_sheet: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for attendance_sheet"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)

    @validate_token
    @http.route("/api/attendance_sheet_line/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _attendance_sheet_line_search_all(self):
        try:
            _logger.info("Attempting to search for attendance_sheet_line...")

            name_id = request.params.get("name_id")

            if name_id:
                attendance_sheet_line = request.env['hr.attendance.sheet.line'].sudo().search([('name_id', '=', int(name_id)), ('export', '=', 'no')])
                # attendance_sheet_line = request.env['hr.attendance.sheet.line'].sudo().search([('name_id', '=', int(name_id))])

            else:
                # attendance_sheet_line = request.env['hr.attendance.sheet.line'].sudo().search([('export_bool', '=', False)])
                attendance_sheet_line = request.env['hr.attendance.sheet.line'].sudo().search([('export', '=', 'no')])
                # attendance_sheet_line = request.env['hr.attendance.sheet.line'].sudo().search(['|', ('export', '=', 'no'), ('export_bool', '=', False)])

            # Prepare the list of attendance
            attendance_sheet_line_list = []
            for attend in attendance_sheet_line:
                print("attend", attend.export_bool)
                attend_data = {
                    'id': attend.id,
                    'name_id': attend.name_id.id or '',
                    'ATTD_DATE': str(attend.date) or '',
                    'ATTD_DAY': attend.day or '',
                    'ATTD_PLANNEDSIGNIN': float_to_time_string(attend.psignin) or '',
                    'ATTD_PLANNEDSIGNOUT': float_to_time_string(attend.psignout) or '',
                    'ATTD_ACTUALSIGNIN': float_to_time_string(attend.asignin) or '',
                    'ATTD_ACTUALSIGNOUT': float_to_time_string(attend.asignout) or '',
                    'ATTD_LATEIN': float_to_time_string(attend.latein) or '',
                    'ATTD_OVERTIME': float_to_time_string(attend.overtime) or '',
                    'ATTD_DIFFTIME': float_to_time_string(attend.difftime) or '',
                    'ATTD_TOTALHOURS': float_to_time_string(attend.total_attendance) or '',
                    'ATTD_STATUS': attend.status or '',
                    'ATTD_LEAVESTATUS': attend.holiday_status or '',
                    # 'export_bool': attend.export_bool or '',
                    'export': attend.export or '',
                    'ATTD_EARLYOUT': float_to_time_string(attend.early_out_line) or '',
                }
                attendance_sheet_line_list.append(attend_data)
                attend.write({'export_bool': True, 'export': 'yes'})

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': attendance_sheet_line_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )


        except Exception as e:
            _logger.error("An error occurred while searching for attendance_sheet_line: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for attendance_sheet_line"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)

    @validate_token
    @http.route("/api/hr_transaction/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _hr_transaction_search_all(self):
        try:
            _logger.info("Attempting to search for hr_transaction...")

            employee_no = request.params.get("employee_no")
            start_date = request.params.get("start_date")
            end_date = request.params.get("end_date")

            domain = []

            if employee_no:
                employee = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
                if employee:
                    domain.append(('employee_id', '=', employee.id))
                else:
                    return request.make_response(json.dumps({
                        'status': 404,
                        'error': 'Employee not found.'
                    }), headers={'Content-Type': 'application/json'}, status=404)
            # employee = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])



            # Filter by date range
            if start_date and end_date:
                domain.extend([
                    ('date', '>=', start_date),
                    ('date', '<=', end_date)
                ])
                # domain.append(('request_date_to', '<=', request_date_to))
            elif start_date:
                domain.append(('date', '>=', start_date))
            elif end_date:
                domain.append(('date', '<=', end_date))

            # domain.append(('export', '=', 'no'), ('state', '=', 'approve'))

            # Additional filters
            domain.extend([('export', '=', 'no'), ('state', '=', 'approve')])

            if domain:
                hr_transaction = request.env['salary.allowance.detection'].sudo().search(domain)
                print("hr_transaction domain", hr_transaction)
            # else:
            #     hr_transaction = request.env['salary.allowance.detection'].sudo().search([('export', '=', 'no'),
            #                                                                               ('state', '=', 'approve')])



            # Prepare the list of hr_transaction
            hr_transaction_list = []
            for trans in hr_transaction:
                if trans.attendance_sheet_id:
                    # trans.export = 'yes'
                    trans_data = {
                        'id': trans.id,
                        'employee_name': trans.employee_id.name or '',
                        'employee_no': trans.employee_id.employee_no or '',
                        'date': str(trans.date) or '',
                        'reference': trans.reference or '',
                        'transaction_type_id': trans.transaction_type_id.name or '',
                        'hr_transaction_id': trans.hr_transaction_id.id or '',
                        'type': trans.type or '',
                        'reason': trans.reason or '',
                        'code': trans.code or '',
                        'units': trans.units or '',
                        'hours': trans.hours or '',
                        'days': trans.days or '',
                        'amount': trans.amount or '',
                        'attendance_sheet_id': trans.attendance_sheet_id.id or '',
                        'export': trans.export or ''
                    }
                    hr_transaction_list.append(trans_data)
                    trans.write({'export': 'yes'})


            # Prepare the response data
            response_data = {
                'status': '200',
                'response': hr_transaction_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )


        except Exception as e:
            _logger.error("An error occurred while searching for hr_transaction: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for hr_transaction"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
                                         status=500)

    # @validate_token
    # @http.route('/api/attendance_sheet/create', methods=["POST"], type="json", auth="none", csrf=False)
    # def create_attendance(self, **post):
    #     try:
    #         _logger.info("Attempting to create attendance...")
    
    #         # Decode the payload data
    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)
    
    #         # Parse the JSON payload
    #         payload = json.loads(payload)
    #         print("...............reecord", payload)
    #         params = payload.get('params', {})
    
    #         # for record in payload:
    #         employee_id = params.get('employee_id')
    #         request_date_from = params.get('request_date_from')
    #         request_date_to = params.get('request_date_to')
    #         # no_latein = record.get('no_latein')
    #         # total_latein = record.get('total_latein')
    #         # no_overtime = record.get('no_overtime')
    #         # total_overtime = record.get('total_overtime')
    #         # no_difftime = record.get('no_difftime')
    #         # total_difftime = record.get('total_difftime')
    #         # no_absence = record.get('no_absence')
    #         # total_absence = record.get('total_absence')
    #         # latein = record.get('latein')
    #         # overtime = record.get('overtime')
    #         # time_different = record.get('time_different')
    #         # absent = record.get('absent')
    #         # attendance_policy = record.get('attendance_policy')
    #         # attendance_sheet_batch_id = record.get('attendance_sheet_batch_id')
    
    #         _logger.info("Creating attendance for employee ID: %s", employee_id)
    
    #         # Search for the employee with the given employee ID
    #         # employee_obj = request.env['hr.employee'].sudo().search([('id', '=', employee_id)])
    #         # if not employee_obj:
    #         #     _logger.warning("Employee not found with ID: %s", employee_id)
    #         #     continue
    
    #         attendance_obj = request.env['hr.attendance.sheet']
    
    #         # Create new attendance record
    #         new_attendance = attendance_obj.write({
    #             'employee_id': employee_id,
    #             'request_date_from': request_date_from,
    #             'request_date_to': request_date_to,
    #             # 'no_latein': no_latein,
    #             # 'total_latein': total_latein,
    #             # 'no_overtime': no_overtime,
    #             # 'total_overtime': total_overtime,
    #             # 'no_difftime': no_difftime,
    #             # 'total_difftime': total_difftime,
    #             # 'no_absence': no_absence,
    #             # 'total_absence': total_absence,
    #             # 'latein': latein,
    #             # 'overtime': overtime,
    #             # 'time_different': time_different,
    #             # 'absent': absent,
    #             # 'attendance_policy': attendance_policy,
    #             # 'attendance_sheet_batch_id': attendance_sheet_batch_id,
    #         })
    
    #         if new_attendance:
    #             _logger.info("Attendance created successfully for Employee ID: %s", employee_id)
    #             _logger.info("Creating attendance for employee ID: %s", employee_id)
    
    #         # Search for the employee with the given employee ID
    #         # employee_obj = request.env['hr.employee'].sudo().search([('id', '=', employee_id)])
    #         # if not employee_obj:
    #         #     _logger.warning("Employee not found with ID: %s", employee_id)
    #         #     continue
    
    #         # attendance_obj = request.env['hr.attendance']
    #         #
    #         # # Create new attendance record
    #         # new_attendance = attendance_obj.create({
    #         #     'employee_id': employee_id,
    #         #     'request_date_from': request_date_from,
    #         #     'request_date_to': request_date_to,
    #         #     # 'no_latein': no_latein,
    #         #     # 'total_latein': total_latein,
    #         #     # 'no_overtime': no_overtime,
    #         #     # 'total_overtime': total_overtime,
    #         #     # 'no_difftime': no_difftime,
    #         #     # 'total_difftime': total_difftime,
    #         #     # 'no_absence': no_absence,
    #         #     # 'total_absence': total_absence,
    #         #     # 'latein': latein,
    #         #     # 'overtime': overtime,
    #         #     # 'time_different': time_different,
    #         #     # 'absent': absent,
    #         #     # 'attendance_policy': attendance_policy,
    #         #     # 'attendance_sheet_batch_id': attendance_sheet_batch_id,
    #         # })
    #         #
    #         # if new_attendance:
    #         #     _logger.info("Attendance created successfully for Employee ID: %s", employee_id)
    
    #         return {
    #             "message": "Attendance data created successfully."
    #         }, 201
    
    #     except Exception as e:
    #         _logger.error("An error occurred while creating the attendance: %s", e)
    #         return {
    #             "error": "An error occurred while creating the attendance"
    #         }, 500


    @validate_token
    @http.route("/api/bidata/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _bidata_search_all(self):
        try:
            _logger.info("Attempting to search for bidata...")

            bi_sqlrecid = request.params.get("BI_SQLRECID")

            if bi_sqlrecid:
                bidata_obj = request.env['bidata'].sudo().search([('bi_sqlrecid', '=', bi_sqlrecid)])
            else:
                bidata_obj = request.env['bidata'].sudo().search([])

            # Prepare the list of bidata
            bidata_list = []
            for bidata in bidata_obj:
                bidata_data = {
                    "id": bidata.id,
                    "bi_sqlrecid": bidata.bi_sqlrecid,
                    "bi_year": bidata.bi_year,
                    "bi_csttypecode": bidata.bi_csttypecode,
                    "bi_csttypedesc": bidata.bi_csttypedesc,
                    "bi_cstsubtypecode": bidata.bi_cstsubtypecode,
                    "bi_cstsubtypedesc": bidata.bi_cstsubtypedesc,
                    "bi_cstregioncode": bidata.bi_cstregioncode,
                    "bi_cstregiondesc": bidata.bi_cstregiondesc,
                    "bi_cstsubregioncode": bidata.bi_cstsubregioncode,
                    "bi_cstsubregiondesc": bidata.bi_cstsubregiondesc,
                    "bi_salesmancode": bidata.bi_salesmancode,
                    "bi_salesmanname": bidata.bi_salesmanname,
                    "bi_cstno": bidata.bi_cstno,
                    "bi_cstname": bidata.bi_cstname,
                    "bi_pgroupcode": bidata.bi_pgroupcode,
                    "bi_pgroupname": bidata.bi_pgroupname,
                    "bi_psgroupcode": bidata.bi_psgroupcode,
                    "bi_psgroupname": bidata.bi_psgroupname,
                    "bi_catmodelcode": bidata.bi_catmodelcode,
                    "bi_catmainpartno": bidata.bi_catmainpartno,
                    "bi_monthdate": str(bidata.bi_monthdate),
                    "bi_invoicecost": bidata.bi_invoicecost,
                    "bi_qty": bidata.bi_qty,
                    "bi_amount": bidata.bi_amount,
                    "bi_pyqty": bidata.bi_pyqty,
                    "bi_pyamount": bidata.bi_pyamount,
                    "bi_budgetqty": bidata.bi_budgetqty,
                    "bi_budgetamount": bidata.bi_budgetamount,
                    "bi_lastmodifieddate": str(bidata.bi_lastmodifieddate),
                }
                bidata_list.append(bidata_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': bidata_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for bidata: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for bidata"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )

    @validate_token
    @http.route('/api/bidata/create', methods=["POST"], type="json", auth="none", csrf=False)
    def create_bidata(self, **post):
        try:
            _logger.info("Attempting to create bidata...")

            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            bi_sqlrecid = params.get('BI_SQLRECID')

            # Check for existing record with the same BI_SQLRECID
            existing_bidata = request.env['bidata'].sudo().search([('bi_sqlrecid', '=', bi_sqlrecid)])
            if existing_bidata:
                _logger.warning("Bidata already exists for BI_SQLRECID: %s", bi_sqlrecid)
                return {
                    "error": f"Bidata with BI_SQLRECID: {bi_sqlrecid} already exists."
                }, 409  # Conflict status code

            # Extract remaining parameters
            bi_year = params.get('BI_YEAR')
            bi_csttypecode = params.get('BI_CSTTYPECODE')
            bi_csttypedesc = params.get('BI_CSTTYPEDESC')
            bi_cstsubtypecode = params.get('BI_CSTSUBTYPECODE')
            bi_cstsubtypedesc = params.get('BI_CSTSUBTYPEDESC')
            bi_cstregioncode = params.get('BI_CSTREGIONCODE')
            bi_cstregiondesc = params.get('BI_CSTREGIONDESC')
            bi_cstsubregioncode = params.get('BI_CSTSUBREGIONCODE')
            bi_cstsubregiondesc = params.get('BI_CSTSUBREGIONDESC')
            bi_salesmancode = params.get('BI_SALESMANCODE')
            bi_salesmanname = params.get('BI_SALESMANNAME')
            bi_cstno = params.get('BI_CSTNO')
            bi_cstname = params.get('BI_CSTNAME')
            bi_pgroupcode = params.get('BI_PGROUPCODE')
            bi_pgroupname = params.get('BI_PGROUPNAME')
            bi_psgroupcode = params.get('BI_PSGROUPCODE')
            bi_psgroupname = params.get('BI_PSGROUPNAME')
            bi_catmodelcode = params.get('BI_CATMODELCODE')
            bi_catmainpartno = params.get('BI_CATMAINPARTNO')
            bi_monthdate = params.get('BI_MONTHDATE')
            bi_invoicecost = params.get('BI_INVOICECOST')
            bi_qty = params.get('BI_QTY')
            bi_amount = params.get('BI_AMOUNT')
            bi_pyqty = params.get('BI_PYQTY')
            bi_pyamount = params.get('BI_PYAMOUNT')
            bi_budgetqty = params.get('BI_BUDGETQTY')
            bi_budgetamount = params.get('BI_BUDGETAMOUNT')
            bi_lastmodifieddate = params.get('BI_LASTMODIFIEDDATE')

            _logger.info("Creating bidata for BI_SQLRECID: %s", bi_sqlrecid)

            # Create new record
            new_record = request.env['bidata'].sudo().create({
                'bi_sqlrecid': bi_sqlrecid,
                'bi_year': bi_year,
                'bi_csttypecode': bi_csttypecode,
                'bi_csttypedesc': bi_csttypedesc,
                'bi_cstsubtypecode': bi_cstsubtypecode,
                'bi_cstsubtypedesc': bi_cstsubtypedesc,
                'bi_cstregioncode': bi_cstregioncode,
                'bi_cstregiondesc': bi_cstregiondesc,
                'bi_cstsubregioncode': bi_cstsubregioncode,
                'bi_cstsubregiondesc': bi_cstsubregiondesc,
                'bi_salesmancode': bi_salesmancode,
                'bi_salesmanname': bi_salesmanname,
                'bi_cstno': bi_cstno,
                'bi_cstname': bi_cstname,
                'bi_pgroupcode': bi_pgroupcode,
                'bi_pgroupname': bi_pgroupname,
                'bi_psgroupcode': bi_psgroupcode,
                'bi_psgroupname': bi_psgroupname,
                'bi_catmodelcode': bi_catmodelcode,
                'bi_catmainpartno': bi_catmainpartno,
                'bi_monthdate': bi_monthdate,
                'bi_invoicecost': bi_invoicecost,
                'bi_qty': bi_qty,
                'bi_amount': bi_amount,
                'bi_pyqty': bi_pyqty,
                'bi_pyamount': bi_pyamount,
                'bi_budgetqty': bi_budgetqty,
                'bi_budgetamount': bi_budgetamount,
                'bi_lastmodifieddate': bi_lastmodifieddate,
            })
            _logger.info("Bidata created successfully for BI_SQLRECID: %s", bi_sqlrecid)
            return {
                "success": True,
                "message": f"Bidata created for BI_SQLRECID: {bi_sqlrecid}",
                "data": {
                    "id": new_record.id,
                    "bi_sqlrecid": new_record.bi_sqlrecid,
                    "bi_year": new_record.bi_year,
                    "bi_csttypecode": new_record.bi_csttypecode,
                    "bi_csttypedesc": new_record.bi_csttypedesc,
                    "bi_cstsubtypecode": new_record.bi_cstsubtypecode,
                    "bi_cstsubtypedesc": new_record.bi_cstsubtypedesc,
                    "bi_cstregioncode": new_record.bi_cstregioncode,
                    "bi_cstregiondesc": new_record.bi_cstregiondesc,
                    "bi_cstsubregioncode": new_record.bi_cstsubregioncode,
                    "bi_cstsubregiondesc": new_record.bi_cstsubregiondesc,
                    "bi_salesmancode": new_record.bi_salesmancode,
                    "bi_salesmanname": new_record.bi_salesmanname,
                    "bi_cstno": new_record.bi_cstno,
                    "bi_cstname": new_record.bi_cstname,
                    "bi_pgroupcode": new_record.bi_pgroupcode,
                    "bi_pgroupname": new_record.bi_pgroupname,
                    "bi_psgroupcode": new_record.bi_psgroupcode,
                    "bi_psgroupname": new_record.bi_psgroupname,
                    "bi_catmodelcode": new_record.bi_catmodelcode,
                    "bi_catmainpartno": new_record.bi_catmainpartno,
                    "bi_monthdate": new_record.bi_monthdate,
                    "bi_invoicecost": new_record.bi_invoicecost,
                    "bi_qty": new_record.bi_qty,
                    "bi_amount": new_record.bi_amount,
                    "bi_pyqty": new_record.bi_pyqty,
                    "bi_pyamount": new_record.bi_pyamount,
                    "bi_budgetqty": new_record.bi_budgetqty,
                    "bi_budgetamount": new_record.bi_budgetamount,
                    "bi_lastmodifieddate": new_record.bi_lastmodifieddate,
                }
            }, 201

        except Exception as e:
            _logger.error("An error occurred while creating the bidata: %s", e)
            return {
                "error": "An error occurred while creating the bidata"
            }, 500

    @validate_token
    @http.route('/api/bidata/update', methods=["POST"], type="json", auth="none", csrf=False)
    def update_bidata(self, **post):
        try:
            _logger.info("Attempting to update bidata...")

            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            bi_sqlrecid = params.get('BI_SQLRECID')
            bi_year = params.get('BI_YEAR')
            bi_csttypecode = params.get('BI_CSTTYPECODE')
            bi_csttypedesc = params.get('BI_CSTTYPEDESC')
            bi_cstsubtypecode = params.get('BI_CSTSUBTYPECODE')
            bi_cstsubtypedesc = params.get('BI_CSTSUBTYPEDESC')
            bi_cstregioncode = params.get('BI_CSTREGIONCODE')
            bi_cstregiondesc = params.get('BI_CSTREGIONDESC')
            bi_cstsubregioncode = params.get('BI_CSTSUBREGIONCODE')
            bi_cstsubregiondesc = params.get('BI_CSTSUBREGIONDESC')
            bi_salesmancode = params.get('BI_SALESMANCODE')
            bi_salesmanname = params.get('BI_SALESMANNAME')
            bi_cstno = params.get('BI_CSTNO')
            bi_cstname = params.get('BI_CSTNAME')
            bi_pgroupcode = params.get('BI_PGROUPCODE')
            bi_pgroupname = params.get('BI_PGROUPNAME')
            bi_psgroupcode = params.get('BI_PSGROUPCODE')
            bi_psgroupname = params.get('BI_PSGROUPNAME')
            bi_catmodelcode = params.get('BI_CATMODELCODE')
            bi_catmainpartno = params.get('BI_CATMAINPARTNO')
            bi_monthdate = params.get('BI_MONTHDATE')
            bi_invoicecost = params.get('BI_INVOICECOST')
            bi_qty = params.get('BI_QTY')
            bi_amount = params.get('BI_AMOUNT')
            bi_pyqty = params.get('BI_PYQTY')
            bi_pyamount = params.get('BI_PYAMOUNT')
            bi_budgetqty = params.get('BI_BUDGETQTY')
            bi_budgetamount = params.get('BI_BUDGETAMOUNT')
            bi_lastmodifieddate = params.get('BI_LASTMODIFIEDDATE')

            _logger.info("Updating bidata for BI_SQLRECID: %s", bi_sqlrecid)

            # Search for the bidata with the given BI_SQLRECID
            bidata_obj = request.env['bidata'].sudo().search([('bi_sqlrecid', '=', bi_sqlrecid)])
            if bidata_obj:
                # Update existing record
                bidata_obj.sudo().write({
                    'bi_year': bi_year,
                    'bi_csttypecode': bi_csttypecode,
                    'bi_csttypedesc': bi_csttypedesc,
                    'bi_cstsubtypecode': bi_cstsubtypecode,
                    'bi_cstsubtypedesc': bi_cstsubtypedesc,
                    'bi_cstregioncode': bi_cstregioncode,
                    'bi_cstregiondesc': bi_cstregiondesc,
                    'bi_cstsubregioncode': bi_cstsubregioncode,
                    'bi_cstsubregiondesc': bi_cstsubregiondesc,
                    'bi_salesmancode': bi_salesmancode,
                    'bi_salesmanname': bi_salesmanname,
                    'bi_cstno': bi_cstno,
                    'bi_cstname': bi_cstname,
                    'bi_pgroupcode': bi_pgroupcode,
                    'bi_pgroupname': bi_pgroupname,
                    'bi_psgroupcode': bi_psgroupcode,
                    'bi_psgroupname': bi_psgroupname,
                    'bi_catmodelcode': bi_catmodelcode,
                    'bi_catmainpartno': bi_catmainpartno,
                    'bi_monthdate': bi_monthdate,
                    'bi_invoicecost': bi_invoicecost,
                    'bi_qty': bi_qty,
                    'bi_amount': bi_amount,
                    'bi_pyqty': bi_pyqty,
                    'bi_pyamount': bi_pyamount,
                    'bi_budgetqty': bi_budgetqty,
                    'bi_budgetamount': bi_budgetamount,
                    'bi_lastmodifieddate': bi_lastmodifieddate,
                })
                _logger.info("Bidata updated successfully for BI_SQLRECID: %s", bi_sqlrecid)
                return {
                    "success": True,
                    "message": f"Bidata updated for BI_SQLRECID: {bi_sqlrecid}"
                }, 200
            else:
                _logger.warning("Bidata not found with BI_SQLRECID: %s", bi_sqlrecid)
                return {
                    "error": "Bidata not found."
                }, 404

        except Exception as e:
            _logger.error("An error occurred while updating the bidata: %s", e)
            return {
                "error": "An error occurred while updating the bidata"
            }, 500


    @validate_token
    @http.route('/api/bidata/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_bidata(self, **post):
        try:
            _logger.info("Attempting to delete bidata...")

            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            bi_sqlrecid = params.get('BI_SQLRECID')
            print("bi_sqlrecid", bi_sqlrecid)
            if not bi_sqlrecid:
                _logger.error("BI_SQLRECID not provided in the request.")
                return {
                    "error": "BI_SQLRECID not provided."
                }, 400  # Bad Request

            _logger.info("Deleting bidata for BI_SQLRECID: %s", bi_sqlrecid)

            # Search for the record to delete
            bidata_obj = request.env['bidata'].sudo().search([('bi_sqlrecid', '=', bi_sqlrecid)])
            if not bidata_obj:
                _logger.warning("Bidata not found for BI_SQLRECID: %s", bi_sqlrecid)
                return {
                    "error": f"Bidata with BI_SQLRECID: {bi_sqlrecid} not found."
                }, 404  # Not Found

            # Delete the record
            bidata_obj.sudo().unlink()
            _logger.info("Bidata deleted successfully for BI_SQLRECID: %s", bi_sqlrecid)
            return {
                "success": True,
                "message": f"Bidata deleted for BI_SQLRECID: {bi_sqlrecid}"
            }, 200  # OK

        except Exception as e:
            _logger.error("An error occurred while deleting the bidata: %s", e)
            return {
                "error": "An error occurred while deleting the bidata"
            }, 500  # Internal Server Error


    @validate_token
    @http.route("/api/t_regionsdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_regionsdesc_search_all(self):
        try:
            _logger.info("Attempting to search for t_regionsdesc...")

            r_code = request.params.get("r_code")
            r_lang = request.params.get("r_lang")
            if r_code:
                t_regionsdesc_obj = request.env['t.regionsdesc'].sudo().search([('r_code', '=', r_code),('r_lang', '=', r_lang)])
            else:
                t_regionsdesc_obj = request.env['t.regionsdesc'].sudo().search([])


            # Prepare the list of t_regionsdesc
            t_regionsdesc_list = []
            for t_regionsdesc_line in t_regionsdesc_obj:
                t_regionsdesc_data = {
                    "r_lang": t_regionsdesc_line.r_lang,
                    "r_code": t_regionsdesc_line.r_code,
                    "lang_flag": t_regionsdesc_line.lang_flag,
                    "r_desc": t_regionsdesc_line.r_desc,
                    "user_lmd": t_regionsdesc_line.user_lmd,                    
                }
                t_regionsdesc_list.append(t_regionsdesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_regionsdesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_regionsdesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_regionsdesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    

    @validate_token
    @http.route("/api/t_regionsdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_regionsdesc_create(self, **post):
        try:
            _logger.info("Attempting to create region...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            r_code = params.get('r_code')
            r_lang = params.get('r_lang')
            lang_flag = params.get('lang_flag')
            r_desc = params.get('r_desc')
            user_lmd = params.get('user_lmd')

            existing_region = request.env['t.regionsdesc'].sudo().search([('r_code', '=', r_code),('r_lang', '=', r_lang)], limit=1)
            if existing_region:
                _logger.warning("Region already exists for r_code: %s", r_code)
                return {
                    "error": f"Region with r_code {r_code} and r_lang {r_lang} already exists."
                }
            r_code = params.get('r_code')
            r_lang = params.get('r_lang')
            lang_flag = params.get('lang_flag')
            r_desc = params.get('r_desc')
            user_lmd = params.get('user_lmd')

            _logger.info("Creating region for r_code: %s", r_code)

            new_record = request.env['t.regionsdesc'].sudo().create({
                'r_code': r_code,
                'r_lang': r_lang,
                'lang_flag': lang_flag,
                'r_desc': r_desc,
                'user_lmd': int(user_lmd) if user_lmd else None,
            })

            _logger.info("Region created successfully for r_code: %s", r_code)
            return {
                "success": True,
                "message": f"Region created for r_code: {r_code}",
                "data": {
                    'id': new_record.id,
                    'r_code': new_record.r_code,
                    'r_lang': new_record.r_lang,
                    'lang_flag': new_record.lang_flag,
                    'r_desc': new_record.r_desc,
                    'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the region: %s", str(e))
            return {
                "error": "An error occurred while creating the region"
            }

    @validate_token
    @http.route("/api/t_regionsdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_regionsdesc_update(self, **post):
        try:
            _logger.info("Attempting to update region...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            r_code = params.get('r_code')
            r_lang = params.get('r_lang')
            if not r_code:
                _logger.error("Missing 'r_code' in params.")
                return {"error": "Missing required field: r_code"}, 400  # Bad Request

            _logger.info("Searching for region with r_code: %s", r_code)

            # Search for the existing record
            reg_update = request.env['t.regionsdesc'].sudo().search([('r_code', '=', r_code),('r_lang', '=', r_lang)], limit=1)

            if not reg_update:
                _logger.warning("Region not found for r_code: %s", r_code)
                return {"error": f"Region with r_code {r_code} and r_lang {r_lang} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            # update_vals = {
            #     key: value for key, value in params.items() if key != "r_code" and value is not None
            # }

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ("r_code", "r_lang") and value is not None
            }
            
            if not update_vals:
                _logger.warning("No valid fields to update for r_code: %s", r_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating region for r_code: %s with data: %s", r_code, update_vals)
            reg_update.sudo().write(update_vals)

            _logger.info("Region updated successfully for r_code: %s", r_code)
            return {
                "success": True,
                "message": f"Region updated for r_code: {r_code}",
                "data": {
                    'id': reg_update.id,
                    'r_code': reg_update.r_code,
                    'r_lang': reg_update.r_lang,
                    'lang_flag': reg_update.lang_flag,
                    'r_desc': reg_update.r_desc,
                    'user_lmd': reg_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the region: %s", str(e))
            return {"error": "An error occurred while updating the region"}, 500  # Internal Server Error

    @validate_token
    @http.route('/api/t_regionsdesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_regionsdesc(self, **post):
        try:
            _logger.info("Attempting to delete t_regionsdesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            r_code = params.get('r_code')

            # Validate r_code
            if not r_code or not isinstance(r_code, str):
                _logger.error("Invalid or missing r_code.")
                return {"error": "Invalid or missing r_code."}, 400

            _logger.info("Deleting t_regionsdesc for r_code: %s", r_code)

            # Search for the record
            t_regionsdesc_obj = request.env['t.regionsdesc'].sudo().search([('r_code', '=', r_code)], limit=1)

            if not t_regionsdesc_obj.exists():
                _logger.warning("t_regionsdesc not found for r_code: %s", r_code)
                return {"error": f"t_regionsdesc with r_code: {r_code} not found."}, 404

            # Delete the record
            t_regionsdesc_obj.sudo().unlink()
            _logger.info("t_regionsdesc deleted successfully for r_code: %s", r_code)

            return {"success": True, "message": f"t_regionsdesc deleted for r_code: {r_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_regionsdesc: %s", e)
            return {"error": "An error occurred while deleting the t_regionsdesc"}, 500


    @validate_token
    @http.route("/api/catalogdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _catalogdesc_search_all(self):
        try:
            _logger.info("Attempting to search for catalogdesc...")

            cat_grp = request.params.get("cat_grp")
            cat_stock = request.params.get("cat_stock")
            cat_part = request.params.get("cat_part")
            cat_lang = request.params.get("cat_lang")
           
            if cat_part:
                catalogdesc_obj = request.env['catalogdesc'].sudo().search([('cat_part', '=', cat_part),('cat_stock', '=', cat_stock),('cat_part', '=', cat_part),('cat_lang', '=', cat_lang)])
            else:
                catalogdesc_obj = request.env['catalogdesc'].sudo().search([])

            # Prepare the list of catalogdesc
            catalogdesc_list = []
            for catalogdesc_line in catalogdesc_obj:
                catalogdesc_data = {
                    "cat_comments": catalogdesc_line.cat_comments,
                    "cat_desc": catalogdesc_line.cat_desc,
                    "cat_grp": catalogdesc_line.cat_grp,
                    "cat_lang": catalogdesc_line.cat_lang,
                    "cat_part": catalogdesc_line.cat_part,
                    "cat_sdesc": catalogdesc_line.cat_sdesc,
                    "cat_shortdesc": catalogdesc_line.cat_shortdesc,
                    "cat_specs": catalogdesc_line.cat_specs,
                    "cat_splname": catalogdesc_line.cat_splname,
                    "cat_stock": catalogdesc_line.cat_stock,
                    "lang_flag": catalogdesc_line.lang_flag,
                    "user_lmd": catalogdesc_line.user_lmd,                  
                }
                catalogdesc_list.append(catalogdesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': catalogdesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for catalogdesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for catalogdesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            ) 

    @validate_token
    @http.route("/api/catalogdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _catalogdesc_create(self, **post):
        try:
            _logger.info("Attempting to create catalogdesc...")

            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            cat_grp = request.params.get("cat_grp")
            cat_stock = request.params.get("cat_stock")
            cat_part = request.params.get("cat_part")
            cat_lang = request.params.get("cat_lang")
            cat_comments = params.get('cat_comments')
            cat_desc = params.get('cat_desc')
            cat_sdesc = params.get('cat_sdesc')
            cat_shortdesc = params.get('cat_shortdesc')
            cat_specs = params.get('cat_specs')
            cat_splname = params.get('cat_splname')
            lang_flag = params.get('lang_flag')
            user_lmd = params.get('user_lmd')

            existing_catalogdesc = request.env['catalogdesc'].sudo().search([('cat_grp', '=', cat_grp),('cat_stock', '=', cat_stock),('cat_part', '=', cat_part),('cat_lang', '=', cat_lang)], limit=1)
            if existing_catalogdesc:
                _logger.warning("catalogdesc already exists for cat_part: %s", cat_part)
                return {
                    "error": f"catalogdesc with cat_part {cat_part} already exists."
                }

            cat_comments = params.get('cat_comments')
            cat_desc = params.get('cat_desc')
            cat_grp = params.get('cat_grp')
            cat_lang = params.get('cat_lang')
            cat_part = params.get('cat_part')
            cat_sdesc = params.get('cat_sdesc')
            cat_shortdesc = params.get('cat_shortdesc')
            cat_specs = params.get('cat_specs')
            cat_splname = params.get('cat_splname')
            cat_stock = params.get('cat_stock')
            lang_flag = params.get('lang_flag')
            user_lmd = params.get('user_lmd')


            _logger.info("Creating catalogdesc for cat_part: %s", cat_part)

            new_record = request.env['catalogdesc'].sudo().create({
               'cat_comments': cat_comments,
                'cat_desc': cat_desc,
                'cat_grp': cat_grp,
                'cat_lang': cat_lang,
                'cat_part': cat_part,
                'cat_sdesc': cat_sdesc,
                'cat_shortdesc': cat_shortdesc,
                'cat_specs': cat_specs,
                'cat_splname': cat_splname,
                'cat_stock': cat_stock,
                'lang_flag': lang_flag,
                'user_lmd': user_lmd,
            })

            _logger.info("catalogdesc created successfully for cat_part: %s", cat_part)
            return {
                "success": True,
                "message": f"catalogdesc created for cat_part: {cat_part}",
                "data": {
                   'cat_comments': new_record.cat_comments,
                    'cat_desc': new_record.cat_desc,
                    'cat_grp': new_record.cat_grp,
                    'cat_lang': new_record.cat_lang,
                    'cat_part': new_record.cat_part,
                    'cat_sdesc': new_record.cat_sdesc,
                    'cat_shortdesc': new_record.cat_shortdesc,
                    'cat_specs': new_record.cat_specs,
                    'cat_splname': new_record.cat_splname,
                    'cat_stock': new_record.cat_stock,
                    'lang_flag': new_record.lang_flag,
                    'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the catalogdesc: %s", str(e))
            return {
                "error": "An error occurred while creating the catalogdesc"
            }


    @validate_token
    @http.route("/api/catalogdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _catalogdesc_update(self, **post):
        try:
            _logger.info("Attempting to update catalogdesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cat_part = params.get('cat_part')
            if not cat_part:
                _logger.error("Missing 'cat_part' in params.")
                return {"error": "Missing required field: cat_part"}, 400  # Bad Request

            _logger.info("Searching for catalogdesc with cat_part: %s", cat_part)

            # Search for the existing record
            catalogdesc_update = request.env['catalogdesc'].sudo().search([('cat_grp', '=', cat_grp),('cat_stock', '=', cat_stock),('cat_part', '=', cat_part),('cat_lang', '=', cat_lang)], limit=1)

            if not catalogdesc_update:
                _logger.warning("catalogdesc not found for cat_part: %s", cat_part)
                return {"error": f"catalogdesc with cat_part {cat_part} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key != "cat_part" and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cat_part: %s", cat_part)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating catalogdesc for cat_part: %s with data: %s", cat_part, update_vals)
            catalogdesc_update.sudo().write(update_vals)

            _logger.info("catalogdesc updated successfully for cat_part: %s", cat_part)
            return {
                "success": True,
                "message": f"catalogdesc updated for cat_part: {cat_part}",
                "data": {
                    'cat_comments': catalogdesc_update.cat_comments,
                     'cat_desc': catalogdesc_update.cat_desc,
                     'cat_grp': catalogdesc_update.cat_grp,
                     'cat_lang': catalogdesc_update.cat_lang,
                     'cat_part': catalogdesc_update.cat_part,
                     'cat_sdesc': catalogdesc_update.cat_sdesc,
                     'cat_shortdesc': catalogdesc_update.cat_shortdesc,
                     'cat_specs': catalogdesc_update.cat_specs,
                     'cat_splname': catalogdesc_update.cat_splname,
                     'cat_stock': catalogdesc_update.cat_stock,
                     'lang_flag': catalogdesc_update.lang_flag,
                     'user_lmd': catalogdesc_update.user_lmd,

                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the catalogdesc: %s", str(e))
            return {"error": "An error occurred while updating the catalogdesc"}, 500

    @validate_token
    @http.route('/api/catalogdesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_catalogdesc(self, **post):
        try:
            _logger.info("Attempting to delete catalogdesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cat_part = params.get('cat_part')

            # Validate cat_part
            if not cat_part or not isinstance(cat_part, str):
                _logger.error("Invalid or missing cat_part.")
                return {"error": "Invalid or missing cat_part."}, 400

            _logger.info("Deleting catalogdesc for cat_part: %s", cat_part)

            # Search for the record
            catalogdesc_obj = request.env['catalogdesc'].sudo().search([('cat_part', '=', cat_part)], limit=1)

            if not catalogdesc_obj.exists():
                _logger.warning("catalogdesc not found for cat_part: %s", cat_part)
                return {"error": f"catalogdesc with cat_part: {cat_part} not found."}, 404

            # Delete the record
            catalogdesc_obj.sudo().unlink()
            _logger.info("catalogdesc deleted successfully for cat_part: %s", cat_part)

            return {"success": True, "message": f"catalogdesc deleted for cat_part: {cat_part}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the catalogdesc: %s", e)
            return {"error": "An error occurred while deleting the catalogdesc"}, 500


    @validate_token
    @http.route("/api/customerdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _customerdesc_search_all(self):
        try:
            _logger.info("Attempting to search for customerdesc...")

            cst_no = request.params.get("cst_no")
            cst_lang = request.params.get("cst_lang")

            if cst_no:
                customerdesc_obj = request.env['customerdesc'].sudo().search([('cst_no', '=', cst_no),('cst_lang', '=', cst_lang)])
            else:
                customerdesc_obj = request.env['customerdesc'].sudo().search([])


            # Prepare the list of customerdesc
            customerdesc_list = []
            for customerdesc_line in customerdesc_obj:
                customerdesc_data = {
                    "cst_no": customerdesc_line.cst_no,
                    "cst_lang": customerdesc_line.cst_lang,
                    "cst_add": customerdesc_line.cst_add,
                    "cst_add2": customerdesc_line.cst_add2,
                    "cst_cityname": customerdesc_line.cst_cityname,
                    "cst_cname": customerdesc_line.cst_cname,
                    "cst_countname": customerdesc_line.cst_countname,
                    "cst_ctitle": customerdesc_line.cst_ctitle,
                     "cst_message": customerdesc_line.cst_message,
                    "cst_name": customerdesc_line.cst_name,                    
                    "lang_flag": customerdesc_line.lang_flag,
                    "user_lmd": customerdesc_line.user_lmd,                
                }
                customerdesc_list.append(customerdesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': customerdesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for customerdesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for customerdesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )   


    @validate_token
    @http.route("/api/customerdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _customerdesc_create(self, **post):
        try:
            _logger.info("Attempting to create customerdesc...")

            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            _logger.debug("Extracted params: %s", params)

            # Extract all parameters before checking for existing record
            cst_no = params.get('cst_no')
            cst_add = params.get('cst_add')
            cst_add2 = params.get('cst_add2')
            cst_cityname = params.get('cst_cityname')
            cst_cname = params.get('cst_cname')
            cst_countname = params.get('cst_countname')
            cst_ctitle = params.get('cst_ctitle')
            cst_lang = params.get('cst_lang')
            cst_message = params.get('cst_message')
            cst_name = params.get('cst_name')
            lang_flag = params.get('lang_flag')
            user_lmd = params.get('user_lmd')

            if not cst_no:
                return {"error": "Missing required field: cst_no"}

            existing_customerdesc = request.env['customerdesc'].sudo().search([('cst_no', '=', cst_no),('cst_lang', '=', cst_lang)], limit=1)
            if existing_customerdesc:
                _logger.warning("customerdesc already exists for cst_no: %s", cst_no)
                return {"error": f"customerdesc with cst_no {cst_no} and cst_lang {cst_lang} already exists."}

            _logger.info("Creating customerdesc for cst_no: %s", cst_no)

            # Create new record
            new_record = request.env['customerdesc'].sudo().create({
                'cst_add': cst_add,
                'cst_add2': cst_add2,
                'cst_cityname': cst_cityname,
                'cst_cname': cst_cname,
                'cst_countname': cst_countname,
                'cst_ctitle': cst_ctitle,
                'cst_lang': cst_lang,
                'cst_message': cst_message,
                'cst_name': cst_name,
                'cst_no': cst_no,
                'lang_flag': lang_flag,
                'user_lmd': user_lmd,
            })

            _logger.info("customerdesc created successfully for cst_no: %s", cst_no)
            return {
                "success": True,
                "message": f"customerdesc created for cst_no: {cst_no}",
                "data": {
                    'cst_add': new_record.cst_add,
                    'cst_add2': new_record.cst_add2,
                    'cst_cityname': new_record.cst_cityname,
                    'cst_cname': new_record.cst_cname,
                    'cst_countname': new_record.cst_countname,
                    'cst_ctitle': new_record.cst_ctitle,
                    'cst_lang': new_record.cst_lang,
                    'cst_message': new_record.cst_message,
                    'cst_name': new_record.cst_name,
                    'cst_no': new_record.cst_no,
                    'lang_flag': new_record.lang_flag,
                    'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the customerdesc: %s", str(e), exc_info=True)
            return {"error": str(e)}


    @validate_token
    @http.route("/api/customerdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _customerdesc_update(self, **post):
        try:
            _logger.info("Attempting to update customerdesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cst_no = params.get('cst_no')
            cst_lang = params.get('cst_lang')
            if not cst_no:
                _logger.error("Missing 'cst_no' in params.")
                return {"error": "Missing required field: cst_no"}, 400  # Bad Request

            _logger.info("Searching for customerdesc with cst_no: %s", cst_no)

            # Search for the existing record
            customerdesc_update = request.env['customerdesc'].sudo().search([('cst_no', '=', cst_no),('cst_lang', '=', cst_lang)], limit=1)

            if not customerdesc_update:
                _logger.warning("customerdesc not found for cst_no: %s", cst_no)
                return {"error": f"customerdesc with cst_no {cst_no} and cst_lang {cst_lang} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("cst_no","cst_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cst_no: %s", cst_no)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating customerdesc for cst_no: %s with data: %s", cst_no, update_vals)
            customerdesc_update.sudo().write(update_vals)

            _logger.info("customerdesc updated successfully for cst_no: %s", cst_no)
            return {
                "success": True,
                "message": f"customerdesc updated for cst_no: {cst_no}",
                "data": {                    
                     'cst_add': customerdesc_update.cst_add,
                     'cst_add2': customerdesc_update.cst_add2,
                     'cst_cityname': customerdesc_update.cst_cityname,
                     'cst_cname': customerdesc_update.cst_cname,
                     'cst_countname': customerdesc_update.cst_countname,
                     'cst_ctitle': customerdesc_update.cst_ctitle,
                     'cst_lang': customerdesc_update.cst_lang,
                     'cst_message': customerdesc_update.cst_message,
                     'cst_name': customerdesc_update.cst_name,
                     'cst_no': customerdesc_update.cst_no,
                     'lang_flag': customerdesc_update.lang_flag,
                     'user_lmd': customerdesc_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the customerdesc: %s", str(e))
            return {"error": "An error occurred while updating the customerdesc"}, 500   
   

    @validate_token
    @http.route('/api/customerdesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_customerdesc(self, **post):
        try:
            _logger.info("Attempting to delete customerdesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cst_no = params.get('cst_no')

            # Validate cst_no
            if not cst_no or not isinstance(cst_no, str):
                _logger.error("Invalid or missing cst_no.")
                return {"error": "Invalid or missing cst_no."}, 400

            _logger.info("Deleting customerdesc for cst_no: %s", cst_no)

            # Search for the record
            t_customerdesc_obj = request.env['customerdesc'].sudo().search([('cst_no', '=', cst_no)], limit=1)

            if not t_customerdesc_obj.exists():
                _logger.warning("customerdesc not found for cst_no: %s", cst_no)
                return {"error": f"customerdesc with cst_no: {cst_no} not found."}, 404

            # Delete the record
            t_customerdesc_obj.sudo().unlink()
            _logger.info("t_customerdesc deleted successfully for cst_no: %s", cst_no)

            return {"success": True, "message": f"t_customerdesc deleted for cst_no: {cst_no}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the customerdesc: %s", e)
            return {"error": "An error occurred while deleting the customerdesc"}, 500

            
    @validate_token
    @http.route("/api/customergroups/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _customergroups_search_all(self):
        try:
            _logger.info("Attempting to search for customergroups...")

            cst_no = request.params.get("cst_no")
           
            if cst_no:
                customergroups_obj = request.env['customergroups'].sudo().search([('cst_no', '=', cst_no)])
            else:
                customergroups_obj = request.env['customergroups'].sudo().search([])


            # Prepare the list of customergroups
            customergroups_list = []
            for customergroups_line in customergroups_obj:
                customergroups_data = {
                   "cst_group": customergroups_line.cst_group,
                    "cst_no": customergroups_line.cst_no,
                    "user_id": customergroups_line.user_id,
                    "user_lmd": customergroups_line.user_lmd,
                    "user_lmt": customergroups_line.user_lmt,                
                }
                customergroups_list.append(customergroups_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': customergroups_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for customergroups: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for customergroups"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )


    @validate_token
    @http.route("/api/customergroups/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _customergroups_create(self, **post):
        try:
            _logger.info("Attempting to create customergroups...")

            # Decode and parse the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)
            payload = json.loads(payload)
            params = payload.get('params', {})

            _logger.debug("params: %s", params)

            # Extract parameters with default values to avoid missing variable errors
            cst_no = params.get('cst_no', '').strip()
            cst_group = params.get('cst_group', '').strip()
            user_id = params.get('user_id', '').strip()
            user_lmd = params.get('user_lmd', '').strip()
            user_lmt = params.get('user_lmt', '').strip()

            if not cst_no:
                return {"error": "Missing required field: cst_no"}

            # Check if customer group already exists
            existing_customergroups = request.env['customergroups'].sudo().search([('cst_no', '=', cst_no)], limit=1)
            if existing_customergroups:
                _logger.warning("customergroups already exists for cst_no: %s", cst_no)
                return {"error": f"customergroups with cst_no {cst_no} already exists."}

            _logger.info("Creating customergroups for cst_no: %s", cst_no)

            # Create new record
            new_record = request.env['customergroups'].sudo().create({
                'cst_no': cst_no,
                'cst_group': cst_group,
                'user_id': user_id,
                'user_lmd': user_lmd,
                'user_lmt': user_lmt,
            })

            _logger.info("customergroups created successfully for cst_no: %s", cst_no)
            return {
                "success": True,
                "message": f"customergroups created for cst_no: {cst_no}",
                "data": {
                    'cst_no': new_record.cst_no,
                    'cst_group': new_record.cst_group,
                    'user_id': new_record.user_id,
                    'user_lmd': new_record.user_lmd,
                    'user_lmt': new_record.user_lmt,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the customergroups: %s", str(e), exc_info=True)
            return {"error": "An error occurred while creating the customergroups"}


    @validate_token
    @http.route("/api/customergroups/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _customergroups_update(self, **post):
        try:
            _logger.info("Attempting to update customergroups...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cst_no = params.get('cst_no')
            if not cst_no:
                _logger.error("Missing 'cst_no' in params.")
                return {"error": "Missing required field: cst_no"}, 400  # Bad Request

            _logger.info("Searching for customergroups with cst_no: %s", cst_no)

            # Search for the existing record
            customergroups_update = request.env['customergroups'].sudo().search([('cst_no', '=', cst_no)], limit=1)

            if not customergroups_update:
                _logger.warning("customergroups not found for cst_no: %s", cst_no)
                return {"error": f"customergroups with cst_no {cst_no} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key != "cst_no" and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cst_no: %s", cst_no)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating customergroups for cst_no: %s with data: %s", cst_no, update_vals)
            customergroups_update.sudo().write(update_vals)

            _logger.info("customergroups updated successfully for cst_no: %s", cst_no)
            return {
                "success": True,
                "message": f"customergroups updated for cst_no: {cst_no}",
                "data": {
                    
                     'cst_group': customergroups_update.cst_group,
                     'cst_no': customergroups_update.cst_no,
                     'user_id': customergroups_update.user_id,
                     'user_lmd': customergroups_update.user_lmd,
                     'user_lmt': customergroups_update.user_lmt,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the customergroups: %s", str(e))
            return {"error": "An error occurred while updating the customergroups"}, 500 


    @validate_token
    @http.route('/api/customergroups/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_customergroups(self, **post):
        try:
            _logger.info("Attempting to delete customergroups...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cst_no = params.get('cst_no')

            # Validate cst_no
            if not cst_no or not isinstance(cst_no, str):
                _logger.error("Invalid or missing cst_no.")
                return {"error": "Invalid or missing cst_no."}, 400

            _logger.info("Deleting customergroups for cst_no: %s", cst_no)

            # Search for the record
            t_customergroups_obj = request.env['customergroups'].sudo().search([('cst_no', '=', cst_no)], limit=1)

            if not t_customergroups_obj.exists():
                _logger.warning("customergroups not found for cst_no: %s", cst_no)
                return {"error": f"customergroups with cst_no: {cst_no} not found."}, 404

            # Delete the record
            t_customergroups_obj.sudo().unlink()
            _logger.info("customergroups deleted successfully for cst_no: %s", cst_no)

            return {"success": True, "message": f"customergroups deleted for cst_no: {cst_no}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the customergroups: %s", e)
            return {"error": "An error occurred while deleting the customergroups"}, 500


    @validate_token
    @http.route("/api/sl_salesmandesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _sl_salesmandesc_search_all(self):
        try:
            _logger.info("Attempting to search for sl_salesmandesc...")

            sm_code = request.params.get("sm_code")
            sm_lang = request.params.get("sm_lang")
           
            if sm_code:
                sl_salesmandesc_obj = request.env['sl.salesmandesc'].sudo().search([('sm_code', '=', sm_code),('sm_lang', '=', sm_lang)])
            else:
                sl_salesmandesc_obj = request.env['sl.salesmandesc'].sudo().search([])


            # Prepare the list of sl_salesmandesc
            sl_salesmandesc_list = []
            for sl_salesmandesc_line in sl_salesmandesc_obj:
                sl_salesmandesc_data = {
                   "lang_flag": sl_salesmandesc_line.lang_flag,
                    "sm_code": sl_salesmandesc_line.sm_code,
                    "sm_lang": sl_salesmandesc_line.sm_lang,
                    "sm_name": sl_salesmandesc_line.sm_name,
                    "user_lmd": sl_salesmandesc_line.user_lmd,               
                }
                sl_salesmandesc_list.append(sl_salesmandesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': sl_salesmandesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for sl_salesmandesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for sl_salesmandesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )
    
    @validate_token
    @http.route("/api/sl_salesmandesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _sl_salesmandesc_create(self, **post):
        try:
            _logger.info("Attempting to create sl_salesmandesc...")

            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

           # ✅ Extract parameters BEFORE checking for existing record
            sm_code = params.get('sm_code', '').strip()
            lang_flag = params.get('lang_flag', '').strip()
            sm_lang = params.get('sm_lang', '').strip()
            sm_name = params.get('sm_name', '').strip()
            user_lmd = params.get('user_lmd', '').strip()

            if not sm_code:
                return {"error": "Missing required field: sm_code"}

            # Check if sl_salesmandesc already exists
            existing_sl_salesmandesc = request.env['sl.salesmandesc'].sudo().search([('sm_code', '=', sm_code),('sm_lang', '=', sm_lang)], limit=1)
            if existing_sl_salesmandesc:
                _logger.warning("sl_salesmandesc already exists for sm_code: %s", sm_code)
                return {"error": f"sl_salesmandesc with sm_code {sm_code} and sm_lang {sm_lang} already exists."}

            _logger.info("Creating sl_salesmandesc for sm_code: %s", sm_code)

            new_record = request.env['sl.salesmandesc'].sudo().create({
                    'sm_code': sm_code,
                    'lang_flag': lang_flag,
                    'sm_lang': sm_lang,
                    'sm_name': sm_name,
                    'user_lmd': user_lmd,
            })

            _logger.info("sl_salesmandesc created successfully for sm_code: %s", sm_code)
            return {
                "success": True,
                "message": f"sl_salesmandesc created for sm_code: {sm_code}",
                "data": {
                  'sm_code': new_record.sm_code,
                  'lang_flag': new_record.lang_flag,
                  'sm_lang': new_record.sm_lang,
                  'sm_name': new_record.sm_name,
                  'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the sl_salesmandesc: %s", str(e))
            return {
                "error": "An error occurred while creating the sl_salesmandesc"
            }


    @validate_token
    @http.route("/api/sl_salesmandesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _sl_salesmandesc_update(self, **post):
        try:
            _logger.info("Attempting to update sl_salesmandesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            sm_code = params.get('sm_code')
            sm_lang = params.get('sm_lang')
            
            if not sm_code:
                _logger.error("Missing 'sm_code' in params.")
                return {"error": "Missing required field: sm_code"}, 400  # Bad Request

            _logger.info("Searching for sl_salesmandesc with sm_code: %s", sm_code)

            # Search for the existing record
            sl_salesmandesc_update = request.env['sl.salesmandesc'].sudo().search([('sm_code', '=', sm_code),('sm_lang', '=', sm_lang)], limit=1)

            if not sl_salesmandesc_update:
                _logger.warning("sl_salesmandesc not found for sm_code: %s", sm_code)
                return {"error": f"sl_salesmandesc with sm_code {sm_code} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ( "sm_code","sm_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for sm_code: %s", sm_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating sl_salesmandesc for sm_code: %s with data: %s", sm_code, update_vals)
            sl_salesmandesc_update.sudo().write(update_vals)

            _logger.info("sl_salesmandesc updated successfully for sm_code: %s", sm_code)
            return {
                "success": True,
                "message": f"sl_salesmandesc updated for sm_code: {sm_code}",
                "data": {
                     'lang_flag': sl_salesmandesc_update.lang_flag,
                     'sm_code': sl_salesmandesc_update.sm_code,
                     'sm_lang': sl_salesmandesc_update.sm_lang,
                     'sm_name': sl_salesmandesc_update.sm_name,
                     'user_lmd': sl_salesmandesc_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the sl_salesmandesc: %s", str(e))
            return {"error": "An error occurred while updating the sl_salesmandesc"}, 500

    @validate_token
    @http.route('/api/sl_salesmandesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_sl_salesmandesc(self, **post):
        try:
            _logger.info("Attempting to delete sl_salesmandesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            sm_code = params.get('sm_code')

            # Validate sm_code
            if not sm_code or not isinstance(sm_code, str):
                _logger.error("Invalid or missing sm_code.")
                return {"error": "Invalid or missing sm_code."}, 400

            _logger.info("Deleting sl_salesmandesc for sm_code: %s", sm_code)

            # Search for the record
            t_sl_salesmandesc_obj = request.env['sl.salesmandesc'].sudo().search([('sm_code', '=', sm_code)], limit=1)

            if not t_sl_salesmandesc_obj.exists():
                _logger.warning("sl_salesmandesc not found for sm_code: %s", sm_code)
                return {"error": f"sl_salesmandesc with sm_code: {sm_code} not found."}, 404

            # Delete the record
            t_sl_salesmandesc_obj.sudo().unlink()
            _logger.info("sl_salesmandesc deleted successfully for sm_code: %s", sm_code)

            return {"success": True, "message": f"sl_salesmandesc deleted for sm_code: {sm_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the sl_salesmandesc: %s", e)
            return {"error": "An error occurred while deleting the sl_salesmandesc"}, 500     

    @validate_token
    @http.route("/api/t_cstclassification/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_cstclassification_search_all(self):
        try:
            _logger.info("Attempting to search for t_cstclassification...")

            cc_code = request.params.get("cc_code")
           
            if cc_code:
                t_cstclassification_obj = request.env['t.cstclassification'].sudo().search([('cc_code', '=', cc_code)])
            else:
                t_cstclassification_obj = request.env['t.cstclassification'].sudo().search([])


            # Prepare the list of t_cstclassification
            t_cstclassification_list = []
            for t_cstclassification_line in t_cstclassification_obj:
                t_cstclassification_data = {
                "cc_code": t_cstclassification_line.cc_code,
                "cc_cstclasstype": t_cstclassification_line.cc_cstclasstype,
                "user_id": t_cstclassification_line.user_id,
                "user_lmd": t_cstclassification_line.user_lmd,
                "user_lmt": t_cstclassification_line.user_lmt,
                }
                
                t_cstclassification_list.append(t_cstclassification_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_cstclassification_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_cstclassification: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_cstclassification"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )


    @validate_token
    @http.route("/api/t_cstclassification/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_cstclassification_create(self, **post):
        try:
            _logger.info("Attempting to create t_cstclassification...")

            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            # Extract parameters from the payload (Assign them first!)
            cc_code = params.get('cc_code')
            cc_cstclasstype = params.get('cc_cstclasstype', '')  # Default empty string to avoid None issues
            user_id = params.get('user_id', '')
            user_lmd = params.get('user_lmd', '')
            user_lmt = params.get('user_lmt', '')

            existing_t_cstclassification = request.env['t.cstclassification'].sudo().search([('cc_code', '=', cc_code)], limit=1)
            if existing_t_cstclassification:
                _logger.warning("t_cstclassification already exists for cc_code: %s", cc_code)
                return {
                    "error": f"t_cstclassification with cc_code {cc_code} already exists."
                }

                cc_code = params.get('cc_code')
                cc_cstclasstype = params.get('cc_cstclasstype')
                user_id = params.get('user_id')
                user_lmd = params.get('user_lmd')
                user_lmt = params.get('user_lmt')

            _logger.info("Creating t_cstclassification for cc_code: %s", cc_code)

            new_record = request.env['t.cstclassification'].sudo().create({
                    'cc_code': cc_code,
                    'cc_cstclasstype': cc_cstclasstype,
                    'user_id': user_id,
                    'user_lmd': user_lmd,
                    'user_lmt': user_lmt,
            })

            _logger.info("t_cstclassification created successfully for cc_code: %s", cc_code)
            return {
                "success": True,
                "message": f"t_cstclassification created for cc_code: {cc_code}",
                "data": {
                  'cc_code': new_record.cc_code,
                  'cc_cstclasstype': new_record.cc_cstclasstype,
                  'user_id': new_record.user_id,
                  'user_lmd': new_record.user_lmd,
                  'user_lmt': new_record.user_lmt,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_cstclassification: %s", str(e))
            return {
                "error": "An error occurred while creating the t_cstclassification"
            }


    @validate_token
    @http.route("/api/t_cstclassification/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_cstclassification_update(self, **post):
        try:
            _logger.info("Attempting to update t_cstclassification...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cc_code = params.get('cc_code')
            if not cc_code:
                _logger.error("Missing 'cc_code' in params.")
                return {"error": "Missing required field: cc_code"}, 400  # Bad Request

            _logger.info("Searching for t_cstclassification with cc_code: %s", cc_code)

            # Search for the existing record
            t_cstclassification_update = request.env['t.cstclassification'].sudo().search([('cc_code', '=', cc_code)], limit=1)

            if not t_cstclassification_update:
                _logger.warning("t_cstclassification not found for cc_code: %s", cc_code)
                return {"error": f"t_cstclassification with cc_code {cc_code} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key != "cc_code" and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cc_code: %s", cc_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_cstclassification for cc_code: %s with data: %s", cc_code, update_vals)
            t_cstclassification_update.sudo().write(update_vals)

            _logger.info("t_cstclassification updated successfully for cc_code: %s", cc_code)
            return {
                "success": True,
                "message": f"t_cstclassification updated for cc_code: {cc_code}",
                "data": {
                      'cc_code': t_cstclassification_update.cc_code,
                      'cc_cstclasstype': t_cstclassification_update.cc_cstclasstype,
                      'user_id': t_cstclassification_update.user_id,
                      'user_lmd': t_cstclassification_update.user_lmd,
                      'user_lmt': t_cstclassification_update.user_lmt,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_cstclassification: %s", str(e))
            return {"error": "An error occurred while updating the t_cstclassification"}, 500 

    @validate_token
    @http.route('/api/t_cstclassification/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_cstclassification(self, **post):
        try:
            _logger.info("Attempting to delete t_cstclassification...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cc_code = params.get('cc_code')

            # Validate cc_code
            if not cc_code or not isinstance(cc_code, str):
                _logger.error("Invalid or missing cc_code.")
                return {"error": "Invalid or missing cc_code."}, 400

            _logger.info("Deleting t_cstclassification for cc_code: %s", cc_code)

            # Search for the record
            t_cstclassification_obj = request.env['t.cstclassification'].sudo().search([('cc_code', '=', cc_code)], limit=1)

            if not t_cstclassification_obj.exists():
                _logger.warning("t_cstclassification not found for cc_code: %s", cc_code)
                return {"error": f"t_cstclassification with cc_code: {cc_code} not found."}, 404

            # Delete the record
            t_cstclassification_obj.sudo().unlink()
            _logger.info("t_cstclassification deleted successfully for cc_code: %s", cc_code)

            return {"success": True, "message": f"t_cstclassification deleted for cc_code: {cc_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_cstclassification: %s", e)
            return {"error": "An error occurred while deleting the t_cstclassification"}, 500


    @validate_token
    @http.route("/api/t_cstclassificationdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_cstclassificationdesc_search_all(self):
        try:
            _logger.info("Attempting to search for t_cstclassificationdesc...")

            cc_code = request.params.get("cc_code")
           
            if cc_code:
                t_cstclassificationdesc_obj = request.env['t.cstclassificationdesc'].sudo().search([('cc_code', '=', cc_code)])
            else:
                t_cstclassificationdesc_obj = request.env['t.cstclassificationdesc'].sudo().search([])


            # Prepare the list of t_cstclassificationdesc
            t_cstclassificationdesc_list = []
            for t_cstclassificationdesc_line in t_cstclassificationdesc_obj:
                t_cstclassificationdesc_data = {
                "cc_code": t_cstclassificationdesc_line.cc_code,
                "cc_desc": t_cstclassificationdesc_line.cc_desc,
                "cc_lang": t_cstclassificationdesc_line.cc_lang,
                "lang_flag": t_cstclassificationdesc_line.lang_flag,
                "user_lmd": t_cstclassificationdesc_line.user_lmd,

                }
                t_cstclassificationdesc_list.append(t_cstclassificationdesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_cstclassificationdesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_cstclassificationdesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_cstclassificationdesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )

    @validate_token
    @http.route("/api/t_cstclassificationdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_cstclassificationdesc_create(self, **post):
        try:
            _logger.info("Attempting to create t_cstclassificationdesc...")

            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            cc_code = params.get('cc_code')
            cc_desc = params.get('cc_desc')
            cc_lang = params.get('cc_lang')
            lang_flag = params.get('lang_flag')
            user_lmd = params.get('user_lmd')

            existing_t_cstclassificationdesc = request.env['t.cstclassificationdesc'].sudo().search([('cc_code', '=', cc_code)], limit=1)
            if existing_t_cstclassificationdesc:
                _logger.warning("t_cstclassificationdesc already exists for cc_code: %s", cc_code)
                return {
                    "error": f"t_cstclassificationdesc with cc_code {cc_code} already exists."
                }

                cc_code = params.get('cc_code')
                cc_desc = params.get('cc_desc')
                cc_lang = params.get('cc_lang')
                lang_flag = params.get('lang_flag')
                user_lmd = params.get('user_lmd')

            _logger.info("Creating t_cstclassificationdesc for cc_code: %s", cc_code)

            new_record = request.env['t.cstclassificationdesc'].sudo().create({
                    'cc_code': cc_code,
                    'cc_desc': cc_desc,
                    'cc_lang': cc_lang,
                    'lang_flag': lang_flag,
                    'user_lmd': user_lmd,
            })

            _logger.info("t_cstclassificationdesc created successfully for cc_code: %s", cc_code)
            return {
                "success": True,
                "message": f"t_cstclassificationdesc created for cc_code: {cc_code}",
                "data": {
                  'cc_code': new_record.cc_code,
                  'cc_desc': new_record.cc_desc,
                  'cc_lang': new_record.cc_lang,
                  'lang_flag': new_record.lang_flag,
                  'user_lmd': new_record.user_lmd,

                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_cstclassificationdesc: %s", str(e))
            return {
                "error": "An error occurred while creating the t_cstclassificationdesc"
            }


    @validate_token
    @http.route("/api/t_cstclassificationdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def update_t_cstclassificationdesc(self, **post):
        try:
            _logger.info("Attempting to update t_cstclassificationdesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cc_code = params.get('cc_code')
            if not cc_code:
                _logger.error("Missing 'cc_code' in params.")
                return {"error": "Missing required field: cc_code"}, 400  # Bad Request

            _logger.info("Searching for t_cstclassificationdesc with cc_code: %s", cc_code)

            # Search for the existing record
            t_cstclassificationdesc_update = request.env['t.cstclassificationdesc'].sudo().search([('cc_code', '=', cc_code)], limit=1)

            if not t_cstclassificationdesc_update:
                _logger.warning("t_cstclassificationdesc not found for cc_code: %s", cc_code)
                return {"error": f"t_cstclassificationdesc with cc_code {cc_code} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key != "cc_code" and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cc_code: %s", cc_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_cstclassificationdesc for cc_code: %s with data: %s", cc_code, update_vals)
            t_cstclassificationdesc_update.sudo().write(update_vals)

            _logger.info("t_cstclassificationdesc updated successfully for cc_code: %s", cc_code)
            return {
                "success": True,
                "message": f"t_cstclassificationdesc updated for cc_code: {cc_code}",
                "data": {
                             'cc_code': t_cstclassificationdesc_update.cc_code,
                             'cc_desc': t_cstclassificationdesc_update.cc_desc,
                             'cc_lang': t_cstclassificationdesc_update.cc_lang,
                             'lang_flag': t_cstclassificationdesc_update.lang_flag,
                             'user_lmd': t_cstclassificationdesc_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_cstclassificationdesc: %s", str(e))
            return {"error": "An error occurred while updating the t_cstclassificationdesc"}, 500


    @validate_token
    @http.route('/api/t_cstclassificationdesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_cstclassificationdesc(self, **post):
        try:
            _logger.info("Attempting to delete t_cstclassificationdesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cc_code = params.get('cc_code')

            # Validate cc_code
            if not cc_code or not isinstance(cc_code, str):
                _logger.error("Invalid or missing cc_code.")
                return {"error": "Invalid or missing cc_code."}, 400

            _logger.info("Deleting t_cstclassificationdesc for cc_code: %s", cc_code)

            # Search for the record
            t_cstclassificationdesc_obj = request.env['t.cstclassificationdesc'].sudo().search([('cc_code', '=', cc_code)], limit=1)

            if not t_cstclassificationdesc_obj.exists():
                _logger.warning("t_cstclassificationdesc not found for cc_code: %s", cc_code)
                return {"error": f"t_cstclassificationdesc with cc_code: {cc_code} not found."}, 404

            # Delete the record
            t_cstclassificationdesc_obj.sudo().unlink()
            _logger.info("t_cstclassificationdesc deleted successfully for cc_code: %s", cc_code)

            return {"success": True, "message": f"t_cstclassificationdesc deleted for cc_code: {cc_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_cstclassificationdesc: %s", e)
            return {"error": "An error occurred while deleting the t_cstclassificationdesc"}, 500


    @validate_token
    @http.route("/api/t_cstclasstypedesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_cstclasstypedesc_search_all(self):
        try:
            _logger.info("Attempting to search for t_cstclasstypedesc...")

            cs_code = request.params.get("cs_code")
            cs_lang = request.params.get("cs_lang")
           
            if cs_code:
                t_cstclasstypedesc_obj = request.env['t.cstclasstypedesc'].sudo().search([('cs_code', '=', cs_code),('cs_lang', '=', cs_lang)])
            else:
                t_cstclasstypedesc_obj = request.env['t.cstclasstypedesc'].sudo().search([])


            # Prepare the list of t_cstclasstypedesc
            t_cstclasstypedesc_list = []
            for t_cstclasstypedesc_line in t_cstclasstypedesc_obj:
                t_cstclasstypedesc_data = {
                "cs_code": t_cstclasstypedesc_line.cs_code,
                "cs_desc": t_cstclasstypedesc_line.cs_desc,
                "cs_lang": t_cstclasstypedesc_line.cs_lang,
                "lang_flag": t_cstclasstypedesc_line.lang_flag,
                "user_lmd": t_cstclasstypedesc_line.user_lmd,

                }
                t_cstclasstypedesc_list.append(t_cstclasstypedesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_cstclasstypedesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_cstclasstypedesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_cstclasstypedesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )


    @validate_token
    @http.route("/api/t_cstclasstypedesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_cstclasstypedesc_create(self, **post):
        try:
            _logger.info("Attempting to create t_cstclasstypedesc...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            cs_code = params.get('cs_code')
            cs_desc = params.get('cs_desc')
            cs_lang = params.get('cs_lang')
            lang_flag = params.get('lang_flag')
            user_lmd = params.get('user_lmd')

            existing_t_cstclasstypedesc = request.env['t.cstclasstypedesc'].sudo().search([('cs_code', '=', cs_code),('cs_lang', '=', cs_lang)], limit=1)
            if existing_t_cstclasstypedesc:
                _logger.warning("t_cstclasstypedesc already exists for cs_code: %s", cs_code)
                return {
                    "error": f"t_cstclasstypedesc with cs_code {cs_code} and {cs_lang} already exists."
                }

                cs_code = params.get('cs_code')
                cs_desc = params.get('cs_desc')
                cs_lang = params.get('cs_lang')
                lang_flag = params.get('lang_flag')
                user_lmd = params.get('user_lmd')

            _logger.info("Creating t_cstclasstypedesc for cs_code: %s", cs_code)

            new_record = request.env['t.cstclasstypedesc'].sudo().create({
                    'cs_code': cs_code,
                    'cs_desc': cs_desc,
                    'cs_lang': cs_lang,
                    'lang_flag': lang_flag,
                    'user_lmd': user_lmd,
            })

            _logger.info("t_cstclasstypedesc created successfully for cs_code: %s", cs_code)
            return {
                "success": True,
                "message": f"t_cstclasstypedesc created for cs_code: {cs_code}",
                "data": {
                  'cs_code': new_record.cs_code,
                  'cs_desc': new_record.cs_desc,
                  'cs_lang': new_record.cs_lang,
                  'lang_flag': new_record.lang_flag,
                  'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_cstclasstypedesc: %s", str(e))
            return {
                "error": "An error occurred while creating the t_cstclasstypedesc"
            }


    @validate_token
    @http.route("/api/t_cstclasstypedesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_cstclasstypedesc_update(self, **post):
        try:
            _logger.info("Attempting to update t_cstclasstypedesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cs_code = params.get('cs_code')
            cs_lang = params.get('cs_lang')

            if not cs_code:
                _logger.error("Missing 'cs_code' in params.")
                return {"error": "Missing required field: cs_code"}, 400  # Bad Request

            _logger.info("Searching for t_cstclasstypedesc with cs_code: %s", cs_code)

            # Search for the existing record
            t_cstclasstypedesc_update = request.env['t.cstclasstypedesc'].sudo().search([('cs_code', '=', cs_code),('cs_lang', '=', cs_lang)], limit=1)

            if not t_cstclasstypedesc_update:
                _logger.warning("t_cstclasstypedesc not found for cs_code: %s", cs_code)
                return {"error": f"t_cstclasstypedesc with cs_code {cs_code} and {cs_lang} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in("cs_code","cs_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cs_code: %s", cs_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_cstclasstypedesc for cs_code: %s with data: %s", cs_code, update_vals)
            t_cstclasstypedesc_update.sudo().write(update_vals)

            _logger.info("t_cstclasstypedesc updated successfully for cs_code: %s", cs_code)
            return {
                "success": True,
                "message": f"t_cstclasstypedesc updated for cs_code: {cs_code}",
                "data": {
                       'cs_code': t_cstclasstypedesc_update.cs_code,
                       'cs_desc': t_cstclasstypedesc_update.cs_desc,
                       'cs_lang': t_cstclasstypedesc_update.cs_lang,
                       'lang_flag': t_cstclasstypedesc_update.lang_flag,
                       'user_lmd': t_cstclasstypedesc_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_cstclasstypedesc: %s", str(e))
            return {"error": "An error occurred while updating the t_cstclasstypedesc"}, 500

    @validate_token
    @http.route('/api/t_cstclasstypedesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_cstclasstypedesc(self, **post):
        try:
            _logger.info("Attempting to delete t_cstclasstypedesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cs_code = params.get('cs_code')

            # Validate cs_code
            if not cs_code or not isinstance(cs_code, str):
                _logger.error("Invalid or missing cs_code.")
                return {"error": "Invalid or missing cs_code."}, 400

            _logger.info("Deleting t_cstclasstypedesc for cs_code: %s", cs_code)

            # Search for the record
            t_cstclasstypedesc_obj = request.env['t.cstclasstypedesc'].sudo().search([('cs_code', '=', cs_code)], limit=1)

            if not t_cstclasstypedesc_obj.exists():
                _logger.warning("t_cstclasstypedesc not found for cs_code: %s", cs_code)
                return {"error": f"t_cstclasstypedesc with cs_code: {cs_code} and {cs_lang} not found."}, 404

            # Delete the record
            t_cstclasstypedesc_obj.sudo().unlink()
            _logger.info("t_cstclasstypedesc deleted successfully for cs_code: %s", cs_code)

            return {"success": True, "message": f"t_cstclasstypedesc deleted for cs_code: {cs_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_cstclasstypedesc: %s", e)
            return {"error": "An error occurred while deleting the t_cstclasstypedesc"}, 500       

    @validate_token
    @http.route("/api/t_cstgroupdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_cstgroupdesc_search_all(self):
        try:
            _logger.info("Attempting to search for t_cstgroupdesc...")

            cg_code = request.params.get("cg_code")
            cg_lang = request.params.get("cg_lang")

            if cg_code:
                t_cstgroupdesc_obj = request.env['t.cstgroupdesc'].sudo().search([('cg_code', '=', cg_code),('cg_lang', '=', cg_lang)])
            else:
                t_cstgroupdesc_obj = request.env['t.cstgroupdesc'].sudo().search([])


            # Prepare the list of t_cstgroupdesc
            t_cstgroupdesc_list = []
            for t_cstgroupdesc_line in t_cstgroupdesc_obj:
                t_cstgroupdesc_data = {
                "cg_code": t_cstgroupdesc_line.cg_code,
                "cg_desc": t_cstgroupdesc_line.cg_desc,
                "cg_lang": t_cstgroupdesc_line.cg_lang,
                "lang_flag": t_cstgroupdesc_line.lang_flag,
                "user_lmd": t_cstgroupdesc_line.user_lmd,

                }
                t_cstgroupdesc_list.append(t_cstgroupdesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_cstgroupdesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_cstgroupdesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_cstgroupdesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )

    @validate_token
    @http.route("/api/t_cstgroupdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_cstgroupdesc_create(self, **post):
        try:
            _logger.info("Attempting to create t_cstgroupdesc...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            cg_code = params.get('cg_code')
            cg_desc = params.get('cg_desc')
            cg_lang = params.get('cg_lang')
            lang_flag = params.get('lang_flag')
            user_lmd = params.get('user_lmd')

            existing_t_cstgroupdesc = request.env['t.cstgroupdesc'].sudo().search([('cg_code', '=', cg_code),('cg_lang', '=', cg_lang)], limit=1)
            if existing_t_cstgroupdesc:
                _logger.warning("t_cstgroupdesc already exists for cg_code: %s", cg_code)
                return {
                    "error": f"t_cstgroupdesc with cg_code {cg_code} already exists."
                }

                cg_code = params.get('cg_code')
                cg_desc = params.get('cg_desc')
                cg_lang = params.get('cg_lang')
                lang_flag = params.get('lang_flag')
                user_lmd = params.get('user_lmd')


            _logger.info("Creating t_cstgroupdesc for cg_code: %s", cg_code)

            new_record = request.env['t.cstgroupdesc'].sudo().create({
                   'cg_code': cg_code,
                    'cg_desc': cg_desc,
                    'cg_lang': cg_lang,
                    'lang_flag': lang_flag,
                    'user_lmd': user_lmd,
            })

            _logger.info("t_cstgroupdesc created successfully for cg_code: %s", cg_code)
            return {
                "success": True,
                "message": f"t_cstgroupdesc created for cg_code: {cg_code}",
                "data": {
                    'cg_code': new_record.cg_code,
                    'cg_desc': new_record.cg_desc,
                    'cg_lang': new_record.cg_lang,
                    'lang_flag': new_record.lang_flag,
                    'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_cstgroupdesc: %s", str(e))
            return {
                "error": "An error occurred while creating the t_cstgroupdesc"
            }            

    @validate_token
    @http.route("/api/t_cstgroupdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_cstgroupdesc_update(self, **post):
        try:
            _logger.info("Attempting to update t_cstgroupdesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cg_code = params.get('cg_code')
            cg_lang = request.params.get("cg_lang")

            if not cg_code:
                _logger.error("Missing 'cg_code' in params.")
                return {"error": "Missing required field: cg_code"}, 400  # Bad Request

            _logger.info("Searching for t_cstgroupdesc with cg_code: %s", cg_code)

            # Search for the existing record            
            t_cstgroupdesc_update = request.env['t.cstgroupdesc'].sudo().search([('cg_code', '=', cg_code),('cg_lang', '=', cg_lang)], limit=1)

            if not t_cstgroupdesc_update:
                _logger.warning("t_cstgroupdesc not found for cg_code: %s", cg_code)
                return {"error": f"t_cstgroupdesc with cg_code {cg_code} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {                
                key: value for key, value in params.items() if key not in("cg_code","cg_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cg_code: %s", cg_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_cstgroupdesc for cg_code: %s with data: %s", cg_code, update_vals)
            t_cstgroupdesc_update.sudo().write(update_vals)

            _logger.info("t_cstgroupdesc updated successfully for cg_code: %s", cg_code)
            return {
                "success": True,
                "message": f"t_cstgroupdesc updated for cg_code: {cg_code}",
                "data": {
                        'cg_code': t_cstgroupdesc_update.cg_code,
                         'cg_desc': t_cstgroupdesc_update.cg_desc,
                         'cg_lang': t_cstgroupdesc_update.cg_lang,
                         'lang_flag': t_cstgroupdesc_update.lang_flag,
                         'user_lmd': t_cstgroupdesc_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_cstgroupdesc: %s", str(e))
            return {"error": "An error occurred while updating the t_cstgroupdesc"}, 500


    @validate_token
    @http.route('/api/t_cstgroupdesc/delete', methods=["POST"], type="json", auth="public", csrf=False)
    def delete_t_cstgroupdesc(self, **post):
        try:
            _logger.info("Attempting to delete t_cstgroupdesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cg_code = params.get('cg_code')
            cg_lang = request.params.get("cg_lang")

            # Validate cg_code
            if not cg_code or not isinstance(cg_code, str):
                _logger.error("Invalid or missing cg_code.")
                return {"error": "Invalid or missing cg_code."}, 400

            _logger.info("Deleting t_cstgroupdesc for cg_code: %s", cg_code)

            # Search for the record
            t_cstgroupdesc_obj = request.env['t.cstgroupdesc'].sudo().search([('cg_code', '=', cg_code),('cg_lang', '=', cg_lang)], limit=1)

            if not t_cstgroupdesc_obj.exists():
                _logger.warning("t_cstgroupdesc not found for cg_code: %s", cg_code)
                return {"error": f"t_cstgroupdesc with cg_code: {cg_code} and cg_lang: {cg_lang} not found."}, 404

            # Delete the record
            t_cstgroupdesc_obj.sudo().unlink()
            _logger.info("t_cstgroupdesc deleted successfully for cg_code: %s", cg_code)

            return {"success": True, "message": f"t_cstgroupdesc deleted for cg_code: {cg_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_cstgroupdesc: %s", e)
            return {"error": "An error occurred while deleting the t_cstgroupdesc"}, 500

    @validate_token
    @http.route("/api/t_cstgroup/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_cstgroup_search_all(self):
        try:
            _logger.info("Attempting to search for t_cstgroup...")

            cg_code = request.params.get("cg_code")
            user_id = request.params.get("user_id")

            if cg_code:
                t_cstgroup_obj = request.env['t.cstgroup'].sudo().search([('cg_code', '=', cg_code),('user_id', '=', user_id)])
            else:
                t_cstgroup_obj = request.env['t.cstgroup'].sudo().search([])


            # Prepare the list of t_cstgroup
            t_cstgroup_list = []
            for t_cstgroup_line in t_cstgroup_obj:
                t_cstgroup_data = {
                "cg_code": t_cstgroup_line.cg_code,
                "user_id": t_cstgroup_line.user_id,
                "user_lmd": t_cstgroup_line.user_lmd,
                "user_lmt": t_cstgroup_line.user_lmt,
                "cg_export": t_cstgroup_line.cg_export,
                }
                t_cstgroup_list.append(t_cstgroup_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_cstgroup_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_cstgroup: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_cstgroup"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )

    @validate_token
    @http.route("/api/t_cstgroup/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_cstgroup_create(self, **post):
        try:
            _logger.info("Attempting to create t_cstgroup...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            cg_code = params.get('cg_code')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')
            user_lmt = params.get('user_lmt')
            cg_export = params.get('cg_export')

            existing_t_cstgroup = request.env['t.cstgroup'].sudo().search([('cg_code', '=', cg_code)], limit=1)
            if existing_t_cstgroup:
                _logger.warning("t_cstgroup already exists for cg_code: %s", cg_code)
                return {
                    "error": f"t_cstgroup with cg_code {cg_code} already exists."
                }

                cg_code = params.get('cg_code')
                user_id = params.get('user_id')
                user_lmd = params.get('user_lmd')
                user_lmt = params.get('user_lmt')
                cg_export = params.get('cg_export')


            _logger.info("Creating t_cstgroup for cg_code: %s", cg_code)

            new_record = request.env['t.cstgroup'].sudo().create({
                   'cg_code': cg_code,
                    'user_id': user_id,
                    'user_lmd': user_lmd,
                    'user_lmt': user_lmt,
                    'cg_export': cg_export,
            })

            _logger.info("t_cstgroup created successfully for cg_code: %s", cg_code)
            return {
                "success": True,
                "message": f"t_cstgroup created for cg_code: {cg_code}",
                "data": {
                    'cg_code': new_record.cg_code,
                    'user_id': new_record.user_id,
                    'user_lmd': new_record.user_lmd,
                    'user_lmt': new_record.user_lmt,
                    'cg_export': new_record.cg_export,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_cstgroup: %s", str(e))
            return {
                "error": "An error occurred while creating the t_cstgroup"
            }            

    @validate_token
    @http.route("/api/t_cstgroup/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_cstgroup_update(self, **post):
        try:
            _logger.info("Attempting to update t_cstgroup...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cg_code = params.get('cg_code')
            user_id = params.get('user_id')
            
            if not cg_code:
                _logger.error("Missing 'cg_code' in params.")
                return {"error": "Missing required field: cg_code"}, 400  # Bad Request

            _logger.info("Searching for t_cstgroup with cg_code: %s", cg_code)

            # Search for the existing record
            t_cstgroup_update = request.env['t.cstgroup'].sudo().search([('cg_code', '=', cg_code),('user_id', '=', user_id)], limit=1)

            if not t_cstgroup_update:
                _logger.warning("t_cstgroup not found for cg_code: %s", cg_code)
                return {"error": f"t_cstgroup with cg_code {cg_code} and user_id {user_id} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in("cg_code","user_id") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cg_code: %s", cg_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_cstgroup for cg_code: %s with data: %s", cg_code, update_vals)
            t_cstgroup_update.sudo().write(update_vals)

            _logger.info("t_cstgroup updated successfully for cg_code: %s", cg_code)
            return {
                "success": True,
                "message": f"t_cstgroup updated for cg_code: {cg_code}",
                "data": {
                        'cg_code': t_cstgroup_update.cg_code,
                         'user_id': t_cstgroup_update.user_id,
                         'user_lmd': t_cstgroup_update.user_lmd,
                         'user_lmt': t_cstgroup_update.user_lmt,
                         'cg_export': t_cstgroup_update.cg_export,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_cstgroup: %s", str(e))
            return {"error": "An error occurred while updating the t_cstgroup"}, 500


    @validate_token
    @http.route('/api/t_cstgroup/delete', methods=["POST"], type="json", auth="public", csrf=False)
    def delete_t_cstgroup(self, **post):
        try:
            _logger.info("Attempting to delete t_cstgroup...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cg_code = params.get('cg_code')
            user_id = params.get('user_id')
            
            # Validate cg_code
            if not cg_code or not isinstance(cg_code, str):
                _logger.error("Invalid or missing cg_code.")
                return {"error": "Invalid or missing cg_code."}, 400

            _logger.info("Deleting t_cstgroup for cg_code: %s", cg_code)

            # Search for the record
            t_cstgroup_obj = request.env['t.cstgroup'].sudo().search([('cg_code', '=', cg_code),('user_id', '=', user_id)], limit=1)

            if not t_cstgroup_obj.exists():
                _logger.warning("t_cstgroup not found for cg_code: %s", cg_code)
                return {"error": f"t_cstgroup with cg_code: {cg_code} and {user_id} not found."}, 404

            # Delete the record
            t_cstgroup_obj.sudo().unlink()
            _logger.info("t_cstgroup deleted successfully for cg_code: %s", cg_code)

            return {"success": True, "message": f"t_cstgroup deleted for cg_code: {cg_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_cstgroup: %s", e)
            return {"error": "An error occurred while deleting the t_cstgroup"}, 500

    @validate_token
    @http.route("/api/t_groupsdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_groupsdesc_search_all(self):
        try:
            _logger.info("Attempting to search for t_groupsdesc...")

            grpd_code = request.params.get("grpd_code")
            grpd_lang = request.params.get("grpd_lang")

            if grpd_code:
                t_groupsdesc_obj = request.env['t.groupsdesc'].sudo().search([('grpd_code', '=', grpd_code),('grpd_lang', '=', grpd_lang)])
            else:
                t_groupsdesc_obj = request.env['t.groupsdesc'].sudo().search([])


            # Prepare the list of t_groupsdesc
            t_groupsdesc_list = []
            for t_groupsdesc_line in t_groupsdesc_obj:
                t_groupsdesc_data = {
               "detail1": t_groupsdesc_line.detail1,
                "detail2": t_groupsdesc_line.detail2,
                "detail3": t_groupsdesc_line.detail3,
                "grpd_code": t_groupsdesc_line.grpd_code,
                "grpd_comments": t_groupsdesc_line.grpd_comments,
                "grpd_desc": t_groupsdesc_line.grpd_desc,
                "grpd_lang": t_groupsdesc_line.grpd_lang,
                "grpd_splname": t_groupsdesc_line.grpd_splname,
                "lang_flag": t_groupsdesc_line.lang_flag,
                "user_lmd": t_groupsdesc_line.user_lmd,

                }
                t_groupsdesc_list.append(t_groupsdesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_groupsdesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_groupsdesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_groupsdesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            ) 


    @validate_token
    @http.route("/api/t_groupsdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_groupsdesc_create(self, **post):
        try:
            _logger.info("Attempting to create t_groupsdesc...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            grpd_code = params.get('grpd_code')
            detail1 = params.get('detail1')
            detail2 = params.get('detail2')
            detail3 = params.get('detail3')
            grpd_comments = params.get('grpd_comments')
            grpd_desc = params.get('grpd_desc')
            grpd_lang = params.get('grpd_lang')
            grpd_splname = params.get('grpd_splname')
            lang_flag = params.get('lang_flag')
            user_lmd = params.get('user_lmd')

            existing_t_groupsdesc = request.env['t.groupsdesc'].sudo().search([('grpd_code', '=', grpd_code),('grpd_lang', '=', grpd_lang)], limit=1)
            if existing_t_groupsdesc:
                _logger.warning("t_groupsdesc already exists for grpd_code: %s", grpd_code)
                return {
                    "error": f"t_groupsdesc with grpd_code {grpd_code} and {grpd_lang} already exists."
                }

                detail1 = params.get('detail1')
                detail2 = params.get('detail2')
                detail3 = params.get('detail3')
                grpd_code = params.get('grpd_code')
                grpd_comments = params.get('grpd_comments')
                grpd_desc = params.get('grpd_desc')
                grpd_lang = params.get('grpd_lang')
                grpd_splname = params.get('grpd_splname')
                lang_flag = params.get('lang_flag')
                user_lmd = params.get('user_lmd')

            _logger.info("Creating t_groupsdesc for grpd_code: %s", grpd_code)

            new_record = request.env['t.groupsdesc'].sudo().create({
                    'detail1': detail1,
                    'detail2': detail2,
                    'detail3': detail3,
                    'grpd_code': grpd_code,
                    'grpd_comments': grpd_comments,
                    'grpd_desc': grpd_desc,
                    'grpd_lang': grpd_lang,
                    'grpd_splname': grpd_splname,
                    'lang_flag': lang_flag,
                    'user_lmd': user_lmd,
            })

            _logger.info("t_groupsdesc created successfully for grpd_code: %s", grpd_code)
            return {
                "success": True,
                "message": f"t_groupsdesc created for grpd_code: {grpd_code}",
                "data": {
                    'detail1': new_record.detail1,
                    'detail2': new_record.detail2,
                    'detail3': new_record.detail3,
                    'grpd_code': new_record.grpd_code,
                    'grpd_comments': new_record.grpd_comments,
                    'grpd_desc': new_record.grpd_desc,
                    'grpd_lang': new_record.grpd_lang,
                    'grpd_splname': new_record.grpd_splname,
                    'lang_flag': new_record.lang_flag,
                    'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_groupsdesc: %s", str(e))
            return {
                "error": "An error occurred while creating the t_groupsdesc"
            }

    @validate_token
    @http.route("/api/t_groupsdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_groupsdesc_update(self, **post):
        try:
            _logger.info("Attempting to update t_groupsdesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            grpd_code = params.get('grpd_code')
            grpd_lang = params.get('grpd_lang')

            if not grpd_code:
                _logger.error("Missing 'grpd_code' in params.")
                return {"error": "Missing required field: grpd_code"}, 400  # Bad Request

            _logger.info("Searching for t_groupsdesc with grpd_code: %s", grpd_code)

            # Search for the existing record
            t_groupsdesc_update = request.env['t.groupsdesc'].sudo().search([('grpd_code', '=', grpd_code),('grpd_lang', '=', grpd_lang)], limit=1)

            if not t_groupsdesc_update:
                _logger.warning("t_groupsdesc not found for grpd_code: %s", grpd_code)
                return {"error": f"t_groupsdesc with grpd_code {grpd_code} and grpd_lang {grpd_lang} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("grpd_code","grpd_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for grpd_code: %s", grpd_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_groupsdesc for grpd_code: %s with data: %s", grpd_code, update_vals)
            t_groupsdesc_update.sudo().write(update_vals)

            _logger.info("t_groupsdesc updated successfully for grpd_code: %s", grpd_code)
            return {
                "success": True,
                "message": f"t_groupsdesc updated for grpd_code: {grpd_code}",
                "data": {
                         'detail1': t_groupsdesc_update.detail1,
                         'detail2': t_groupsdesc_update.detail2,
                         'detail3': t_groupsdesc_update.detail3,
                         'grpd_code': t_groupsdesc_update.grpd_code,
                         'grpd_comments': t_groupsdesc_update.grpd_comments,
                         'grpd_desc': t_groupsdesc_update.grpd_desc,
                         'grpd_lang': t_groupsdesc_update.grpd_lang,
                         'grpd_splname': t_groupsdesc_update.grpd_splname,
                         'lang_flag': t_groupsdesc_update.lang_flag,
                         'user_lmd': t_groupsdesc_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_groupsdesc: %s", str(e))
            return {"error": "An error occurred while updating the t_groupsdesc"}, 500  # Internal Server Error

    @validate_token
    @http.route('/api/t_groupsdesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_groupsdesc(self, **post):
        try:
            _logger.info("Attempting to delete t_groupsdesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            grpd_code = params.get('grpd_code')

            # Validate grpd_code
            if not grpd_code or not isinstance(grpd_code, str):
                _logger.error("Invalid or missing grpd_code.")
                return {"error": "Invalid or missing grpd_code."}, 400

            _logger.info("Deleting t_groupsdesc for grpd_code: %s", grpd_code)

            # Search for the record
            t_groupsdesc_obj = request.env['t.groupsdesc'].sudo().search([('grpd_code', '=', grpd_code)], limit=1)

            if not t_groupsdesc_obj.exists():
                _logger.warning("t_groupsdesc not found for grpd_code: %s", grpd_code)
                return {"error": f"t_groupsdesc with grpd_code: {grpd_code} not found."}, 404

            # Delete the record
            t_groupsdesc_obj.sudo().unlink()
            _logger.info("t_groupsdesc deleted successfully for grpd_code: %s", grpd_code)

            return {"success": True, "message": f"t_groupsdesc deleted for grpd_code: {grpd_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_groupsdesc: %s", e)
            return {"error": "An error occurred while deleting the t_groupsdesc"}, 500

    @validate_token
    @http.route("/api/t_productsdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_productsdesc_search_all(self):
        try:
            _logger.info("Attempting to search for t_productsdesc...")

            p_grp = request.params.get("p_grp")
            p_code = request.params.get("p_code")
            p_lang = request.params.get("p_lang")
                       
            if p_code:
                t_productsdesc_obj = request.env['t.productsdesc'].sudo().search([('p_grp', '=', p_grp),('p_code', '=', p_code),('p_lang', '=', p_lang)])
            else:
                t_productsdesc_obj = request.env['t.productsdesc'].sudo().search([])

            # Prepare the list of t_productsdesc
            t_productsdesc_list = []
            for t_productsdesc_line in t_productsdesc_obj:
                t_productsdesc_data = {
                "lang_flag": t_productsdesc_line.lang_flag,
                "p_code": t_productsdesc_line.p_code,
                "p_desc": t_productsdesc_line.p_desc,
                "p_grp": t_productsdesc_line.p_grp,
                "p_lang": t_productsdesc_line.p_lang,
                "user_lmd": t_productsdesc_line.user_lmd,               
                }
                t_productsdesc_list.append(t_productsdesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_productsdesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_productsdesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_productsdesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    

    @validate_token
    @http.route("/api/t_productsdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_productsdesc_create(self, **post):
        try:
            _logger.info("Attempting to create t_productsdesc...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            p_code = params.get('p_code')
            lang_flag = params.get('lang_flag')
            p_desc = params.get('p_desc')
            p_grp = params.get('p_grp')
            p_lang = params.get('p_lang')
            user_lmd = params.get('user_lmd')

            existing_t_productsdesc = request.env['t.productsdesc'].sudo().search([('p_grp', '=', p_grp),('p_code', '=', p_code),('p_lang', '=', p_lang)], limit=1)
            if existing_t_productsdesc:
                _logger.warning("t_productsdesc already exists for p_code: %s", p_code)
                return {
                    "error": f"t_productsdesc with p_code {p_code} already exists."
                }

                lang_flag = params.get('lang_flag')
                p_code = params.get('p_code')
                p_desc = params.get('p_desc')
                p_grp = params.get('p_grp')
                p_lang = params.get('p_lang')
                user_lmd = params.get('user_lmd')                

            _logger.info("Creating t_productsdesc for p_code: %s", p_code)

            new_record = request.env['t.productsdesc'].sudo().create({
                    'lang_flag': lang_flag,
                    'p_code': p_code,
                    'p_desc': p_desc,
                    'p_grp': p_grp,
                    'p_lang': p_lang,
                    'user_lmd': user_lmd,
            })

            _logger.info("t_productsdesc created successfully for p_code: %s", p_code)
            return {
                "success": True,
                "message": f"t_productsdesc created for p_code: {p_code}",
                "data": {
                    'lang_flag': new_record.lang_flag,
                    'p_code': new_record.p_code,
                    'p_desc': new_record.p_desc,
                    'p_grp': new_record.p_grp,
                    'p_lang': new_record.p_lang,
                    'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_productsdesc: %s", str(e))
            return {
                "error": "An error occurred while creating the t_productsdesc"
            }


    @validate_token
    @http.route("/api/t_productsdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_productsdesc_update(self, **post):
        try:
            _logger.info("Attempting to update t_productsdesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            p_grp = params.get('p_grp')
            p_code = params.get('p_code')
            p_lang = params.get('p_lang')

            if not p_code:
                _logger.error("Missing 'p_code' in params.")
                return {"error": "Missing required field: p_code"}, 400  # Bad Request

            _logger.info("Searching for t_productsdesc with p_code: %s", p_code)

            # Search for the existing record
            t_productsdesc_update = request.env['t.productsdesc'].sudo().search([('p_grp', '=', p_grp),('p_code', '=', p_code),('p_lang', '=', p_lang)], limit=1)

            if not t_productsdesc_update:
                _logger.warning("t_productsdesc not found for p_code: %s", p_code)
                return {"error": f"t_productsdesc with p_grp {p_grp} ,p_code {p_code} and p_lang {p_lang}  not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("p_grp","p_code","p_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for p_code: %s", p_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_productsdesc for p_code: %s with data: %s", p_code, update_vals)
            t_productsdesc_update.sudo().write(update_vals)

            _logger.info("t_productsdesc updated successfully for p_code: %s", p_code)
            return {
                "success": True,
                "message": f"t_productsdesc updated for p_code: {p_code}",
                "data": {
                             'lang_flag': t_productsdesc_update.lang_flag,
                             'p_code': t_productsdesc_update.p_code,
                             'p_desc': t_productsdesc_update.p_desc,
                             'p_grp': t_productsdesc_update.p_grp,
                             'p_lang': t_productsdesc_update.p_lang,
                             'user_lmd': t_productsdesc_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_productsdesc: %s", str(e))
            return {"error": "An error occurred while updating the t_productsdesc"}, 500  # Internal Server Error

    @validate_token
    @http.route('/api/t_productsdesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_productsdesc(self, **post):
        try:
            _logger.info("Attempting to delete t_productsdesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            p_code = params.get('p_code')

            # Validate p_code
            if not p_code or not isinstance(p_code, str):
                _logger.error("Invalid or missing p_code.")
                return {"error": "Invalid or missing p_code."}, 400

            _logger.info("Deleting t_productsdesc for p_code: %s", p_code)

            # Search for the record
            t_productsdesc_obj = request.env['t.productsdesc'].sudo().search([('p_code', '=', p_code)], limit=1)

            if not t_productsdesc_obj.exists():
                _logger.warning("t_productsdesc not found for p_code: %s", p_code)
                return {"error": f"t_productsdesc with p_code: {p_code} not found."}, 404

            # Delete the record
            t_productsdesc_obj.sudo().unlink()
            _logger.info("t_productsdesc deleted successfully for p_code: %s", p_code)

            return {"success": True, "message": f"t_productsdesc deleted for p_code: {p_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_productsdesc: %s", e)
            return {"error": "An error occurred while deleting the t_productsdesc"}, 500


    @validate_token
    @http.route("/api/t_productsubsdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_productsubsdesc_search_all(self):
        try:
            _logger.info("Attempting to search for t_productsubsdesc...")

            ps_grp = request.params.get("ps_grp")
            ps_pcode = request.params.get("ps_pcode")
            ps_psub = request.params.get("ps_psub")
            ps_lang = request.params.get("ps_lang")

            if ps_pcode:
                t_productsubsdesc_obj = request.env['t.productsubsdesc'].sudo().search([('ps_grp', '=', ps_grp),('ps_pcode', '=', ps_pcode),('ps_psub', '=', ps_psub),('ps_lang', '=', ps_lang)])
            else:
                t_productsubsdesc_obj = request.env['t.productsubsdesc'].sudo().search([])


            # Prepare the list of t_productsubsdesc
            t_productsubsdesc_list = []
            for t_productsubsdesc_line in t_productsubsdesc_obj:
                t_productsubsdesc_data = {
                "lang_flag": t_productsubsdesc_line.lang_flag,
                "ps_desc": t_productsubsdesc_line.ps_desc,
                "ps_grp": t_productsubsdesc_line.ps_grp,
                "ps_lang": t_productsubsdesc_line.ps_lang,
                "ps_pcode": t_productsubsdesc_line.ps_pcode,
                "ps_psub": t_productsubsdesc_line.ps_psub,
                "user_lmd": t_productsubsdesc_line.user_lmd,               
                }

                t_productsubsdesc_list.append(t_productsubsdesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_productsubsdesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_productsubsdesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_productsubsdesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    

    @validate_token
    @http.route("/api/t_productsubsdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_productsubsdesc_create(self, **post):
        try:
            _logger.info("Attempting to create t_productsubsdesc...")

            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            ps_pcode = params.get('ps_pcode')
            lang_flag = params.get('lang_flag')
            ps_desc = params.get('ps_desc')
            ps_grp = params.get('ps_grp')
            ps_lang = params.get('ps_lang')
            ps_psub = params.get('ps_psub')
            user_lmd = params.get('user_lmd')

            existing_t_productsubsdesc = request.env['t.productsubsdesc'].sudo().search([('ps_grp', '=', ps_grp),('ps_pcode', '=', ps_pcode),('ps_psub', '=', ps_psub),('ps_lang', '=', ps_lang)], limit=1)
            if existing_t_productsubsdesc:
                _logger.warning("t_productsubsdesc already exists for ps_pcode: %s", ps_pcode)
                return {
                    "error": f"t_productsubsdesc with ps_grp {ps_grp}, ps_pcode {ps_pcode}, ps_psub {ps_psub} and {ps_lang} already exists."
                }

                lang_flag = params.get('lang_flag')
                ps_desc = params.get('ps_desc')
                ps_grp = params.get('ps_grp')
                ps_lang = params.get('ps_lang')
                ps_pcode = params.get('ps_pcode')
                ps_psub = params.get('ps_psub')
                user_lmd = params.get('user_lmd')                

            _logger.info("Creating t_productsubsdesc for ps_pcode: %s", ps_pcode)

            new_record = request.env['t.productsubsdesc'].sudo().create({
                    'lang_flag': lang_flag,
                    'ps_desc': ps_desc,
                    'ps_grp': ps_grp,
                    'ps_lang': ps_lang,
                    'ps_pcode': ps_pcode,
                    'ps_psub': ps_psub,
                    'user_lmd': user_lmd,
            })

            _logger.info("t_productsubsdesc created successfully for ps_pcode: %s", ps_pcode)
            return {
                "success": True,
                "message": f"t_productsubsdesc created for ps_pcode: {ps_pcode}",
                "data": {
                    'lang_flag': new_record.lang_flag,
                    'ps_desc': new_record.ps_desc,
                    'ps_grp': new_record.ps_grp,
                    'ps_lang': new_record.ps_lang,
                    'ps_pcode': new_record.ps_pcode,
                    'ps_psub': new_record.ps_psub,
                    'user_lmd': new_record.user_lmd,                    
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_productsubsdesc: %s", str(e))
            return {
                "error": "An error occurred while creating the t_productsubsdesc"
            }

    @validate_token
    @http.route("/api/t_productsubsdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_productsubsdesc_update(self, **post):
        try:
            _logger.info("Attempting to update t_productsubsdesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            ps_grp = params.get('ps_grp')
            ps_pcode = params.get('ps_pcode')
            ps_psub = params.get('ps_psub')
            ps_lang = params.get('ps_lang')

            if not ps_pcode:
                _logger.error("Missing 'ps_pcode' in params.")
                return {"error": "Missing required field: ps_pcode"}, 400  # Bad Request

            _logger.info("Searching for t_productsubsdesc with ps_pcode: %s", ps_pcode)

            # Search for the existing record
            t_productsubsdesc_update = request.env['t.productsubsdesc'].sudo().search([('ps_grp', '=', ps_grp),('ps_pcode', '=', ps_pcode),('ps_psub', '=', ps_psub),('ps_lang', '=', ps_lang)], limit=1)

            if not t_productsubsdesc_update:
                _logger.warning("t_productsubsdesc not found for ps_pcode: %s", ps_pcode)
                return {"error": f"t_productsubsdesc with ps_grp {ps_grp},  ps_pcode {ps_pcode},ps_psub {ps_psub} and ps_lang {ps_lang} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("ps_grp", "ps_pcode","ps_psub","ps_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for ps_pcode: %s", ps_pcode)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_productsubsdesc for ps_pcode: %s with data: %s", ps_pcode, update_vals)
            t_productsubsdesc_update.sudo().write(update_vals)

            _logger.info("t_productsubsdesc updated successfully for ps_pcode: %s", ps_pcode)
            return {
                "success": True,
                "message": f"t_productsubsdesc updated for ps_pcode: {ps_pcode}",
                "data": {
                             'lang_flag': t_productsubsdesc_update.lang_flag,
                             'ps_desc': t_productsubsdesc_update.ps_desc,
                             'ps_grp': t_productsubsdesc_update.ps_grp,
                             'ps_lang': t_productsubsdesc_update.ps_lang,
                             'ps_pcode': t_productsubsdesc_update.ps_pcode,
                             'ps_psub': t_productsubsdesc_update.ps_psub,
                             'user_lmd': t_productsubsdesc_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_productsubsdesc: %s", str(e))
            return {"error": "An error occurred while updating the t_productsubsdesc"}, 500  # Internal Server Error

    @validate_token
    @http.route('/api/t_productsubsdesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_productsubsdesc(self, **post):
        try:
            _logger.info("Attempting to delete t_productsubsdesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            ps_pcode = params.get('ps_pcode')

            # Validate ps_pcode
            if not ps_pcode or not isinstance(ps_pcode, str):
                _logger.error("Invalid or missing ps_pcode.")
                return {"error": "Invalid or missing ps_pcode."}, 400

            _logger.info("Deleting t_productsubsdesc for ps_pcode: %s", ps_pcode)

            # Search for the record
            t_productsubsdesc_obj = request.env['t.productsubsdesc'].sudo().search([('ps_pcode', '=', ps_pcode)], limit=1)

            if not t_productsubsdesc_obj.exists():
                _logger.warning("t_productsubsdesc not found for ps_pcode: %s", ps_pcode)
                return {"error": f"t_productsubsdesc with ps_pcode: {ps_pcode} not found."}, 404

            # Delete the record
            t_productsubsdesc_obj.sudo().unlink()
            _logger.info("t_productsubsdesc deleted successfully for ps_pcode: %s", ps_pcode)

            return {"success": True, "message": f"t_productsubsdesc deleted for ps_pcode: {ps_pcode}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_productsubsdesc: %s", e)
            return {"error": "An error occurred while deleting the t_productsubsdesc"}, 500


    @validate_token
    @http.route("/api/t_subregions/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_subregions_search_all(self):
        try:
            _logger.info("Attempting to search for t_subregions...")

            sr_code = request.params.get("sr_code")
           
            if sr_code:
                t_subregions_obj = request.env['t.subregions'].sudo().search([('sr_code', '=', sr_code)])
            else:
                t_subregions_obj = request.env['t.subregions'].sudo().search([])


            # Prepare the list of t_subregions
            t_subregions_list = []
            for t_subregions_line in t_subregions_obj:
                t_subregions_data = {
                "sr_code": t_subregions_line.sr_code,
                "sr_disable": t_subregions_line.sr_disable,
                "sr_region": t_subregions_line.sr_region,
                "sr_sort": t_subregions_line.sr_sort,
                "user_id": t_subregions_line.user_id,
                "user_lmd": t_subregions_line.user_lmd,
                "user_lmt": t_subregions_line.user_lmt,
                }
                t_subregions_list.append(t_subregions_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_subregions_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_subregions: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_subregions"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    

    @validate_token
    @http.route("/api/t_subregions/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_subregions_create(self, **post):
        try:
            _logger.info("Attempting to create t_subregions...")

            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            sr_code = params.get('sr_code')
            sr_disable = params.get('sr_disable')
            sr_region = params.get('sr_region')
            sr_sort = params.get('sr_sort')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')
            user_lmt = params.get('user_lmt')

            existing_t_subregions = request.env['t.subregions'].sudo().search([('sr_code', '=', sr_code)], limit=1)
            if existing_t_subregions:
                _logger.warning("t_subregions already exists for sr_code: %s", sr_code)
                return {
                    "error": f"t_subregions with sr_code {sr_code} already exists."
                }

                sr_code = params.get('sr_code')
                sr_disable = params.get('sr_disable')
                sr_region = params.get('sr_region')
                sr_sort = params.get('sr_sort')
                user_id = params.get('user_id')
                user_lmd = params.get('user_lmd')
                user_lmt = params.get('user_lmt')

            _logger.info("Creating t_subregions for sr_code: %s", sr_code)

            new_record = request.env['t.subregions'].sudo().create({
                    'sr_code': sr_code,
                    'sr_disable': sr_disable,
                    'sr_region': sr_region,
                    'sr_sort': sr_sort,
                    'user_id': user_id,
                    'user_lmd': user_lmd,
                    'user_lmt': user_lmt,
            })

            _logger.info("t_subregions created successfully for sr_code: %s", sr_code)
            return {
                "success": True,
                "message": f"t_subregions created for sr_code: {sr_code}",
                "data": {
                    'sr_code': new_record.sr_code,
                    'sr_disable': new_record.sr_disable,
                    'sr_region': new_record.sr_region,
                    'sr_sort': new_record.sr_sort,
                    'user_id': new_record.user_id,
                    'user_lmd': new_record.user_lmd,
                    'user_lmt': new_record.user_lmt,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_subregions: %s", str(e))
            return {
                "error": "An error occurred while creating the t_subregions"
            }

    @validate_token
    @http.route("/api/t_subregions/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_subregions_update(self, **post):
        try:
            _logger.info("Attempting to update t_subregions...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            sr_code = params.get('sr_code')
            if not sr_code:
                _logger.error("Missing 'sr_code' in params.")
                return {"error": "Missing required field: sr_code"}, 400  # Bad Request

            _logger.info("Searching for t_subregions with sr_code: %s", sr_code)

            # Search for the existing record
            t_subregions_update = request.env['t.subregions'].sudo().search([('sr_code', '=', sr_code)], limit=1)

            if not t_subregions_update:
                _logger.warning("t_subregions not found for sr_code: %s", sr_code)
                return {"error": f"t_subregions with sr_code {sr_code} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key != "sr_code" and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for sr_code: %s", sr_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_subregions for sr_code: %s with data: %s", sr_code, update_vals)
            t_subregions_update.sudo().write(update_vals)

            _logger.info("t_subregions updated successfully for sr_code: %s", sr_code)
            return {
                "success": True,
                "message": f"t_subregions updated for sr_code: {sr_code}",
                "data": {
                                 'sr_code': t_subregions_update.sr_code,
                                 'sr_disable': t_subregions_update.sr_disable,
                                 'sr_region': t_subregions_update.sr_region,
                                 'sr_sort': t_subregions_update.sr_sort,
                                 'user_id': t_subregions_update.user_id,
                                 'user_lmd': t_subregions_update.user_lmd,
                                 'user_lmt': t_subregions_update.user_lmt,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_subregions: %s", str(e))
            return {"error": "An error occurred while updating the t_subregions"}, 500  # Internal Server Error


    @validate_token
    @http.route('/api/t_subregions/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_subregions(self, **post):
        try:
            _logger.info("Attempting to delete t_subregions...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            sr_code = params.get('sr_code')

            # Validate sr_code
            if not sr_code or not isinstance(sr_code, str):
                _logger.error("Invalid or missing sr_code.")
                return {"error": "Invalid or missing sr_code."}, 400

            _logger.info("Deleting t_subregions for sr_code: %s", sr_code)

            # Search for the record
            t_subregions_obj = request.env['t.subregions'].sudo().search([('sr_code', '=', sr_code)], limit=1)

            if not t_subregions_obj.exists():
                _logger.warning("t_subregions not found for sr_code: %s", sr_code)
                return {"error": f"t_subregions with sr_code: {sr_code} not found."}, 404

            # Delete the record
            t_subregions_obj.sudo().unlink()
            _logger.info("t_subregions deleted successfully for sr_code: %s", sr_code)

            return {"success": True, "message": f"t_subregions deleted for sr_code: {sr_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_subregions: %s", e)
            return {"error": "An error occurred while deleting the t_subregions"}, 500



    @validate_token
    @http.route("/api/t_subregionsdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_subregionsdesc_search_all(self):
        try:
            _logger.info("Attempting to search for t_subregionsdesc...")

            sr_code = request.params.get("sr_code")
            sr_lang = request.params.get("sr_lang")
           
            if sr_code:
                t_subregionsdesc_obj = request.env['t.subregionsdesc'].sudo().search([('sr_code', '=', sr_code),('sr_lang', '=', sr_lang)])
            else:
                t_subregionsdesc_obj = request.env['t.subregionsdesc'].sudo().search([])


            # Prepare the list of t_subregionsdesc
            t_subregionsdesc_list = []
            for t_subregionsdesc_line in t_subregionsdesc_obj:
                t_subregionsdesc_data = {
                "lang_flag": t_subregionsdesc_line.lang_flag,
                "sr_code": t_subregionsdesc_line.sr_code,
                "sr_desc": t_subregionsdesc_line.sr_desc,
                "sr_lang": t_subregionsdesc_line.sr_lang,
                "user_lmd": t_subregionsdesc_line.user_lmd,

                }
                t_subregionsdesc_list.append(t_subregionsdesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_subregionsdesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_subregionsdesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_subregionsdesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )   


    @validate_token
    @http.route("/api/t_subregionsdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_subregionsdesc_create(self, **post):
        try:
            _logger.info("Attempting to create t_subregionsdesc...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            sr_code = params.get('sr_code')
            lang_flag = params.get('lang_flag')
            sr_desc = params.get('sr_desc')
            sr_lang = params.get('sr_lang')
            user_lmd = params.get('user_lmd')

            existing_t_subregionsdesc = request.env['t.subregionsdesc'].sudo().search([('sr_code', '=', sr_code),('sr_lang', '=', sr_lang)], limit=1)
            if existing_t_subregionsdesc:
                _logger.warning("t_subregionsdesc already exists for sr_code: %s", sr_code)
                return {
                    "error": f"t_subregionsdesc with sr_code {sr_code} already exists."
                }

                lang_flag = params.get('lang_flag')
                sr_code = params.get('sr_code')
                sr_desc = params.get('sr_desc')
                sr_lang = params.get('sr_lang')
                user_lmd = params.get('user_lmd')

            _logger.info("Creating t_subregionsdesc for sr_code: %s", sr_code)

            new_record = request.env['t.subregionsdesc'].sudo().create({
                    'lang_flag': lang_flag,
                    'sr_code': sr_code,
                    'sr_desc': sr_desc,
                    'sr_lang': sr_lang,
                    'user_lmd': user_lmd,
            })

            _logger.info("t_subregionsdesc created successfully for sr_code: %s", sr_code)
            return {
                "success": True,
                "message": f"t_subregionsdesc created for sr_code: {sr_code}",
                "data": {
                    'lang_flag': new_record.lang_flag,
                    'sr_code': new_record.sr_code,
                    'sr_desc': new_record.sr_desc,
                    'sr_lang': new_record.sr_lang,
                    'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_subregionsdesc: %s", str(e))
            return {
                "error": "An error occurred while creating the t_subregionsdesc"
            }


    @validate_token
    @http.route("/api/t_subregionsdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_subregionsdesc_update(self, **post):
        try:
            _logger.info("Attempting to update t_subregionsdesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            sr_code = params.get('sr_code')
            sr_lang = params.get('sr_lang')

            if not sr_code:
                _logger.error("Missing 'sr_code' in params.")
                return {"error": "Missing required field: sr_code"}, 400  # Bad Request

            _logger.info("Searching for t_subregionsdesc with sr_code: %s", sr_code)

            # Search for the existing record
            t_subregionsdesc_update = request.env['t.subregionsdesc'].sudo().search([('sr_code', '=', sr_code),('sr_lang', '=', sr_lang)], limit=1)

            if not t_subregionsdesc_update:
                _logger.warning("t_subregionsdesc not found for sr_code: %s", sr_code)
                return {"error": f"t_subregionsdesc with sr_code {sr_code} and sr_lang {sr_lang} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("sr_code","sr_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for sr_code: %s", sr_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_subregionsdesc for sr_code: %s with data: %s", sr_code, update_vals)
            t_subregionsdesc_update.sudo().write(update_vals)

            _logger.info("t_subregionsdesc updated successfully for sr_code: %s", sr_code)
            return {
                "success": True,
                "message": f"t_subregionsdesc updated for sr_code: {sr_code}",
                "data": {
                                 'lang_flag': t_subregionsdesc_update.lang_flag,
                                 'sr_code': t_subregionsdesc_update.sr_code,
                                 'sr_desc': t_subregionsdesc_update.sr_desc,
                                 'sr_lang': t_subregionsdesc_update.sr_lang,
                                 'user_lmd': t_subregionsdesc_update.user_lmd,
                        }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_subregionsdesc: %s", str(e))
            return {"error": "An error occurred while updating the t_subregionsdesc"}, 500  # Internal Server Error


    @validate_token
    @http.route('/api/t_subregionsdesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_subregionsdesc(self, **post):
        try:
            _logger.info("Attempting to delete t_subregionsdesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            sr_code = params.get('sr_code')

            # Validate sr_code
            if not sr_code or not isinstance(sr_code, str):
                _logger.error("Invalid or missing sr_code.")
                return {"error": "Invalid or missing sr_code."}, 400

            _logger.info("Deleting t_subregionsdesc for sr_code: %s", sr_code)

            # Search for the record
            t_subregionsdesc_obj = request.env['t.subregionsdesc'].sudo().search([('sr_code', '=', sr_code)], limit=1)

            if not t_subregionsdesc_obj.exists():
                _logger.warning("t_subregionsdesc not found for sr_code: %s", sr_code)
                return {"error": f"t_subregionsdesc with sr_code: {sr_code} not found."}, 404

            # Delete the record
            t_subregionsdesc_obj.sudo().unlink()
            _logger.info("t_subregionsdesc deleted successfully for sr_code: %s", sr_code)

            return {"success": True, "message": f"t_subregionsdesc deleted for sr_code: {sr_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_subregionsdesc: %s", e)
            return {"error": "An error occurred while deleting the t_subregionsdesc"}, 500

    @validate_token
    @http.route("/api/t_warehousedesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_warehousedesc_search_all(self):
        try:
            _logger.info("Attempting to search for t_warehousedesc...")

            wh_code = request.params.get("wh_code")
            wh_lang = request.params.get("wh_lang")

            if wh_code:
                t_warehousedesc_obj = request.env['t.warehousedesc'].sudo().search([('wh_code', '=', wh_code),('wh_lang', '=', wh_lang)])
            else:
                t_warehousedesc_obj = request.env['t.warehousedesc'].sudo().search([])

            # Prepare the list of t_warehousedesc
            t_warehousedesc_list = []
            for t_warehousedesc_line in t_warehousedesc_obj:
                t_warehousedesc_data = {
                "lang_flag": t_warehousedesc_line.lang_flag,
                "user_lmd": t_warehousedesc_line.user_lmd,
                "wh_code": t_warehousedesc_line.wh_code,
                "wh_desc": t_warehousedesc_line.wh_desc,
                "wh_lang": t_warehousedesc_line.wh_lang,
                "wh_pmessage": t_warehousedesc_line.wh_pmessage,
                }
                t_warehousedesc_list.append(t_warehousedesc_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_warehousedesc_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_warehousedesc: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_warehousedesc"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    


    @validate_token
    @http.route("/api/t_warehousedesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_warehousedesc_create(self, **post):
        try:
            _logger.info("Attempting to create t_warehousedesc...")

            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            wh_code = params.get('wh_code')
            wh_desc = params.get('wh_desc')
            wh_lang = params.get('wh_lang')
            wh_pmessage = params.get('wh_pmessage')
            lang_flag = params.get('lang_flag')
            user_lmd = params.get('user_lmd')

            existing_t_warehousedesc = request.env['t.warehousedesc'].sudo().search([('wh_code', '=', wh_code),('wh_lang', '=', wh_lang)], limit=1)
            if existing_t_warehousedesc:
                _logger.warning("t_warehousedesc already exists for wh_code: %s", wh_code)
                return {
                    "error": f"t_warehousedesc with wh_code {wh_code} and wh_lang {wh_lang} already exists."
                }

                lang_flag = params.get('lang_flag')
                user_lmd = params.get('user_lmd')
                wh_code = params.get('wh_code')
                wh_desc = params.get('wh_desc')
                wh_lang = params.get('wh_lang')
                wh_pmessage = params.get('wh_pmessage')

            _logger.info("Creating t_warehousedesc for wh_code: %s", wh_code)

            new_record = request.env['t.warehousedesc'].sudo().create({
                    'lang_flag': lang_flag,
                    'user_lmd': user_lmd,
                    'wh_code': wh_code,
                    'wh_desc': wh_desc,
                    'wh_lang': wh_lang,
                    'wh_pmessage': wh_pmessage,
            })

            _logger.info("t_warehousedesc created successfully for wh_code: %s", wh_code)
            return {
                "success": True,
                "message": f"t_warehousedesc created for wh_code: {wh_code}",
                "data": {
                    'lang_flag': new_record.lang_flag,
                    'user_lmd': new_record.user_lmd,
                    'wh_code': new_record.wh_code,
                    'wh_desc': new_record.wh_desc,
                    'wh_lang': new_record.wh_lang,
                    'wh_pmessage': new_record.wh_pmessage,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_warehousedesc: %s", str(e))
            return {
                "error": "An error occurred while creating the t_warehousedesc"
            }

    @validate_token
    @http.route("/api/t_warehousedesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_warehousedesc_update(self, **post):
        try:
            _logger.info("Attempting to update t_warehousedesc...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            wh_code = params.get('wh_code')
            wh_lang = params.get('wh_lang')
            if not wh_code:
                _logger.error("Missing 'wh_code' in params.")
                return {"error": "Missing required field: wh_code"}, 400  # Bad Request

            _logger.info("Searching for t_warehousedesc with wh_code: %s", wh_code)

            # Search for the existing record
            t_warehousedesc_update = request.env['t.warehousedesc'].sudo().search([('wh_code', '=', wh_code),('wh_lang', '=', wh_lang)], limit=1)

            if not t_warehousedesc_update:
                _logger.warning("t_warehousedesc not found for wh_code: %s", wh_code)
                return {"error": f"t_warehousedesc with wh_code {wh_code} and wh_lang {wh_lang} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("wh_code","wh_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for wh_code: %s", wh_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_warehousedesc for wh_code: %s with data: %s", wh_code, update_vals)
            t_warehousedesc_update.sudo().write(update_vals)

            _logger.info("t_warehousedesc updated successfully for wh_code: %s", wh_code)
            return {
                "success": True,
                "message": f"t_warehousedesc updated for wh_code: {wh_code}",
                "data": {
                                 'lang_flag': t_warehousedesc_update.lang_flag,
                                 'user_lmd': t_warehousedesc_update.user_lmd,
                                 'wh_code': t_warehousedesc_update.wh_code,
                                 'wh_desc': t_warehousedesc_update.wh_desc,
                                 'wh_lang': t_warehousedesc_update.wh_lang,
                                 'wh_pmessage': t_warehousedesc_update.wh_pmessage,                         

                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_warehousedesc: %s", str(e))
            return {"error": "An error occurred while updating the t_warehousedesc"}, 500  # Internal Server Error

    @validate_token
    @http.route('/api/t_warehousedesc/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_warehousedesc(self, **post):
        try:
            _logger.info("Attempting to delete t_warehousedesc...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            wh_code = params.get('wh_code')            

            # Validate wh_code
            if not wh_code or not isinstance(wh_code, str):
                _logger.error("Invalid or missing wh_code.")
                return {"error": "Invalid or missing wh_code."}, 400

            _logger.info("Deleting t_warehousedesc for wh_code: %s", wh_code)

            # Search for the record
            t_warehousedesc_obj = request.env['t.warehousedesc'].sudo().search([('wh_code', '=', wh_code)], limit=1)

            if not t_warehousedesc_obj.exists():
                _logger.warning("t_warehousedesc not found for wh_code: %s", wh_code)
                return {"error": f"t_warehousedesc with wh_code: {wh_code} not found."}, 404

            # Delete the record
            t_warehousedesc_obj.sudo().unlink()
            _logger.info("t_warehousedesc deleted successfully for wh_code: %s", wh_code)

            return {"success": True, "message": f"t_warehousedesc deleted for wh_code: {wh_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_warehousedesc: %s", e)
            return {"error": "An error occurred while deleting the t_warehousedesc"}, 500

    @validate_token
    @http.route("/api/catalog/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _catalog_search_all(self):
        try:
            _logger.info("Attempting to search for catalog...")

            cat_grp = request.params.get("cat_grp")
            cat_stock = request.params.get("cat_stock")
            cat_part = request.params.get("cat_part")
           
            if cat_part:
                catalog_obj = request.env['catalog'].sudo().search([('cat_grp', '=', cat_grp),('cat_stock', '=', cat_stock),('cat_part', '=', cat_part)])
            else:
                catalog_obj = request.env['catalog'].sudo().search([])
             
            # Prepare the list of catalog
            catalog_list = []
            for catalog_line in catalog_obj:
                catalog_data = {
                "cat_allzcost": catalog_line.cat_allzcost,
                "cat_assembl": catalog_line.cat_assembl,
                "cat_associategrp": catalog_line.cat_associategrp,
                "cat_associatepart": catalog_line.cat_associatepart,
                "cat_avcost": catalog_line.cat_avcost,
                "cat_backward": catalog_line.cat_backward,
                "cat_barcode": catalog_line.cat_barcode,
                "cat_bltncode": catalog_line.cat_bltncode,
                "cat_bulletin": catalog_line.cat_bulletin,
                "cat_cat": catalog_line.cat_cat,
                "cat_comments": catalog_line.cat_comments,
                "cat_comments2": catalog_line.cat_comments2,
                "cat_desc": catalog_line.cat_desc,
                "cat_desc2": catalog_line.cat_desc2,
                "cat_discont": catalog_line.cat_discont,
                "cat_discontdate": catalog_line.cat_discontdate,
                "cat_dsiamount": catalog_line.cat_dsiamount,
                "cat_duty": catalog_line.cat_duty,
                "cat_fccode": catalog_line.cat_fccode,
                "cat_fccost": catalog_line.cat_fccost,
                "cat_flag": catalog_line.cat_flag,
                "cat_frac": catalog_line.cat_frac,
                "cat_genorder": catalog_line.cat_genorder,
                "cat_grouppart": catalog_line.cat_grouppart,
                "cat_grp": catalog_line.cat_grp,
                "cat_image": catalog_line.cat_image,
                "cat_intrdate": catalog_line.cat_intrdate,
                "cat_itemtype": catalog_line.cat_itemtype,
                "cat_kit": catalog_line.cat_kit,
                "cat_lastsprice": catalog_line.cat_lastsprice,
                "cat_lccost": catalog_line.cat_lccost,
                "cat_lrctdate": catalog_line.cat_lrctdate,
                "cat_mainpartno": catalog_line.cat_mainpartno,
                "cat_manu": catalog_line.cat_manu,
                "cat_max": catalog_line.cat_max,
                "cat_mccode": catalog_line.cat_mccode,
                "cat_min": catalog_line.cat_min,
                "cat_mmcode": catalog_line.cat_mmcode,
                "cat_model": catalog_line.cat_model,
                "cat_modelcode": catalog_line.cat_modelcode,
                "cat_multispl": catalog_line.cat_multispl,
                "cat_nonstock": catalog_line.cat_nonstock,
                "cat_obsolete": catalog_line.cat_obsolete,
                "cat_oldbarcode": catalog_line.cat_oldbarcode,
                "cat_oldpart": catalog_line.cat_oldpart,
                "cat_ordflag": catalog_line.cat_ordflag,
                "cat_pack": catalog_line.cat_pack,
                "cat_packqty": catalog_line.cat_packqty,
                "cat_part": catalog_line.cat_part,
                "cat_parttype": catalog_line.cat_parttype,
                "cat_pcode": catalog_line.cat_pcode,
                "cat_pcount": catalog_line.cat_pcount,
                "cat_pgroup": catalog_line.cat_pgroup,
                "cat_pgtype": catalog_line.cat_pgtype,
                "cat_pointval": catalog_line.cat_pointval,
                "cat_ppack": catalog_line.cat_ppack,
                "cat_pqtydi": catalog_line.cat_pqtydi,
                "cat_priority": catalog_line.cat_priority,
                "cat_psgroup": catalog_line.cat_psgroup,
                "cat_qqtydi": catalog_line.cat_qqtydi,
                "cat_recsal": catalog_line.cat_recsal,
                "cat_royalty": catalog_line.cat_royalty,
                "cat_royaltyfc": catalog_line.cat_royaltyfc,
                "cat_rptcode": catalog_line.cat_rptcode,
                "cat_salestype": catalog_line.cat_salestype,
                "cat_sdesc": catalog_line.cat_sdesc,
                "cat_sdesc2": catalog_line.cat_sdesc2,
                "cat_season": catalog_line.cat_season,
                "cat_service": catalog_line.cat_service,
                "cat_servicekit": catalog_line.cat_servicekit,
                "cat_shortdesc": catalog_line.cat_shortdesc,
                "cat_shortdesc2": catalog_line.cat_shortdesc2,
                "cat_slife": catalog_line.cat_slife,
                "cat_slifef": catalog_line.cat_slifef,
                "cat_spack": catalog_line.cat_spack,
                "cat_specs": catalog_line.cat_specs,
                "cat_specs2": catalog_line.cat_specs2,
                "cat_splkit": catalog_line.cat_splkit,
                "cat_splname": catalog_line.cat_splname,
                "cat_splname2": catalog_line.cat_splname2,
                "cat_splno": catalog_line.cat_splno,
                "cat_splpart": catalog_line.cat_splpart,
                "cat_spricecdate": catalog_line.cat_spricecdate,
                "cat_stcost": catalog_line.cat_stcost,
                "cat_stock": catalog_line.cat_stock,
                "cat_subpar": catalog_line.cat_subpar,
                "cat_substo": catalog_line.cat_substo,
                "cat_supdat": catalog_line.cat_supdat,
                "cat_supdate": catalog_line.cat_supdate,
                "cat_supgrp": catalog_line.cat_supgrp,
                "cat_suppar": catalog_line.cat_suppar,
                "cat_suppart": catalog_line.cat_suppart,
                "cat_supsto": catalog_line.cat_supsto,
                "cat_supstock": catalog_line.cat_supstock,
                "cat_type": catalog_line.cat_type,
                "cat_uh": catalog_line.cat_uh,
                "cat_ul": catalog_line.cat_ul,
                "cat_uom": catalog_line.cat_uom,
                "cat_uvol": catalog_line.cat_uvol,
                "cat_uw": catalog_line.cat_uw,
                "cat_uwt": catalog_line.cat_uwt,
                "cat_vat": catalog_line.cat_vat,
                "cat_vuom": catalog_line.cat_vuom,
                "cat_wom": catalog_line.cat_wom,
                "cat_wprd": catalog_line.cat_wprd,
                "cat_wprdf": catalog_line.cat_wprdf,
                "detail1": catalog_line.detail1,
                "detail2": catalog_line.detail2,
                "detail3": catalog_line.detail3,
                "lang_flag": catalog_line.lang_flag,
                "lang_flag2": catalog_line.lang_flag2,
                "user_id": catalog_line.user_id,
                "user_lmd": catalog_line.user_lmd,
                "user_lmt": catalog_line.user_lmt,
                }
                catalog_list.append(catalog_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': catalog_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for catalog: %s", e)

            error_response = {
                'status': 500,
                'error': f"An error occurred while searching for catalog-- {str(e)}"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    

    @validate_token
    @http.route("/api/catalog/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _catalog_create(self, **post):
        try:
            _logger.info("Attempting to create catalog...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            cat_part = params.get('cat_part')
            cat_allzcost = params.get('cat_allzcost')
            cat_assembl = params.get('cat_assembl')
            cat_associategrp = params.get('cat_associategrp')
            cat_associatepart = params.get('cat_associatepart')
            cat_avcost = params.get('cat_avcost')
            cat_backward = params.get('cat_backward')
            cat_barcode = params.get('cat_barcode')
            cat_bltncode = params.get('cat_bltncode')
            cat_bulletin = params.get('cat_bulletin')
            cat_cat = params.get('cat_cat')
            cat_comments = params.get('cat_comments')
            cat_comments2 = params.get('cat_comments2')
            cat_desc = params.get('cat_desc')
            cat_desc2 = params.get('cat_desc2')
            cat_discont = params.get('cat_discont')
            cat_discontdate = params.get('cat_discontdate')
            cat_dsiamount = params.get('cat_dsiamount')
            cat_duty = params.get('cat_duty')
            cat_fccode = params.get('cat_fccode')
            cat_fccost = params.get('cat_fccost')
            cat_flag = params.get('cat_flag')
            cat_frac = params.get('cat_frac')
            cat_genorder = params.get('cat_genorder')
            cat_grouppart = params.get('cat_grouppart')
            cat_grp = params.get('cat_grp')
            cat_image = params.get('cat_image')
            cat_intrdate = params.get('cat_intrdate')
            cat_itemtype = params.get('cat_itemtype')
            cat_kit = params.get('cat_kit')
            cat_lastsprice = params.get('cat_lastsprice')
            cat_lccost = params.get('cat_lccost')
            cat_lrctdate = params.get('cat_lrctdate')
            cat_mainpartno = params.get('cat_mainpartno')
            cat_manu = params.get('cat_manu')
            cat_max = params.get('cat_max')
            cat_mccode = params.get('cat_mccode')
            cat_min = params.get('cat_min')
            cat_mmcode = params.get('cat_mmcode')
            cat_model = params.get('cat_model')
            cat_modelcode = params.get('cat_modelcode')
            cat_multispl = params.get('cat_multispl')
            cat_nonstock = params.get('cat_nonstock')
            cat_obsolete = params.get('cat_obsolete')
            cat_oldbarcode = params.get('cat_oldbarcode')
            cat_oldpart = params.get('cat_oldpart')
            cat_ordflag = params.get('cat_ordflag')
            cat_pack = params.get('cat_pack')
            cat_packqty = params.get('cat_packqty')
            cat_parttype = params.get('cat_parttype')
            cat_pcode = params.get('cat_pcode')
            cat_pcount = params.get('cat_pcount')
            cat_pgroup = params.get('cat_pgroup')
            cat_pgtype = params.get('cat_pgtype')
            cat_pointval = params.get('cat_pointval')
            cat_ppack = params.get('cat_ppack')
            cat_pqtydi = params.get('cat_pqtydi')
            cat_priority = params.get('cat_priority')
            cat_psgroup = params.get('cat_psgroup')
            cat_qqtydi = params.get('cat_qqtydi')
            cat_recsal = params.get('cat_recsal')
            cat_royalty = params.get('cat_royalty')
            cat_royaltyfc = params.get('cat_royaltyfc')
            cat_rptcode = params.get('cat_rptcode')
            cat_salestype = params.get('cat_salestype')
            cat_sdesc = params.get('cat_sdesc')
            cat_sdesc2 = params.get('cat_sdesc2')
            cat_season = params.get('cat_season')
            cat_service = params.get('cat_service')
            cat_servicekit = params.get('cat_servicekit')
            cat_shortdesc = params.get('cat_shortdesc')
            cat_shortdesc2 = params.get('cat_shortdesc2')
            cat_slife = params.get('cat_slife')
            cat_slifef = params.get('cat_slifef')
            cat_spack = params.get('cat_spack')
            cat_specs = params.get('cat_specs')
            cat_specs2 = params.get('cat_specs2')
            cat_splkit = params.get('cat_splkit')
            cat_splname = params.get('cat_splname')
            cat_splname2 = params.get('cat_splname2')
            cat_splno = params.get('cat_splno')
            cat_splpart = params.get('cat_splpart')
            cat_spricecdate = params.get('cat_spricecdate')
            cat_stcost = params.get('cat_stcost')
            cat_stock = params.get('cat_stock')
            cat_subpar = params.get('cat_subpar')
            cat_substo = params.get('cat_substo')
            cat_supdat = params.get('cat_supdat')
            cat_supdate = params.get('cat_supdate')
            cat_supgrp = params.get('cat_supgrp')
            cat_suppar = params.get('cat_suppar')
            cat_suppart = params.get('cat_suppart')
            cat_supsto = params.get('cat_supsto')
            cat_supstock = params.get('cat_supstock')
            cat_type = params.get('cat_type')
            cat_uh = params.get('cat_uh')
            cat_ul = params.get('cat_ul')
            cat_uom = params.get('cat_uom')
            cat_uvol = params.get('cat_uvol')
            cat_uw = params.get('cat_uw')
            cat_uwt = params.get('cat_uwt')
            cat_vat = params.get('cat_vat')
            cat_vuom = params.get('cat_vuom')
            cat_wom = params.get('cat_wom')
            cat_wprd = params.get('cat_wprd')
            cat_wprdf = params.get('cat_wprdf')
            detail1 = params.get('detail1')
            detail2 = params.get('detail2')
            detail3 = params.get('detail3')
            lang_flag = params.get('lang_flag')
            lang_flag2 = params.get('lang_flag2')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')
            user_lmt = params.get('user_lmt')

            existing_catalog = request.env['catalog'].sudo().search([('cat_grp', '=', cat_grp),('cat_stock', '=', cat_stock),('cat_part', '=', cat_part)], limit=1)
            if existing_catalog:
                _logger.warning("Catalog already exists for cat_part: %s", cat_part)
                return {  # Function returns here if catalog exists
                    "error": f"Catalog with cat_grp {cat_grp},cat_stock {cat_stock} and cat_part {cat_part} already exists."
                }

            cat_allzcost = params.get('cat_allzcost')
            cat_assembl = params.get('cat_assembl')
            cat_associategrp = params.get('cat_associategrp')
            cat_associatepart = params.get('cat_associatepart')
            cat_avcost = params.get('cat_avcost')
            cat_backward = params.get('cat_backward')
            cat_barcode = params.get('cat_barcode')
            cat_bltncode = params.get('cat_bltncode')
            cat_bulletin = params.get('cat_bulletin')
            cat_cat = params.get('cat_cat')
            cat_comments = params.get('cat_comments')
            cat_comments2 = params.get('cat_comments2')
            cat_desc = params.get('cat_desc')
            cat_desc2 = params.get('cat_desc2')
            cat_discont = params.get('cat_discont')
            cat_discontdate = params.get('cat_discontdate')
            cat_dsiamount = params.get('cat_dsiamount')
            cat_duty = params.get('cat_duty')
            cat_fccode = params.get('cat_fccode')
            cat_fccost = params.get('cat_fccost')
            cat_flag = params.get('cat_flag')
            cat_frac = params.get('cat_frac')
            cat_genorder = params.get('cat_genorder')
            cat_grouppart = params.get('cat_grouppart')
            cat_grp = params.get('cat_grp')
            cat_image = params.get('cat_image')
            cat_intrdate = params.get('cat_intrdate')
            cat_itemtype = params.get('cat_itemtype')
            cat_kit = params.get('cat_kit')
            cat_lastsprice = params.get('cat_lastsprice')
            cat_lccost = params.get('cat_lccost')
            cat_lrctdate = params.get('cat_lrctdate')
            cat_mainpartno = params.get('cat_mainpartno')
            cat_manu = params.get('cat_manu')
            cat_max = params.get('cat_max')
            cat_mccode = params.get('cat_mccode')
            cat_min = params.get('cat_min')
            cat_mmcode = params.get('cat_mmcode')
            cat_model = params.get('cat_model')
            cat_modelcode = params.get('cat_modelcode')
            cat_multispl = params.get('cat_multispl')
            cat_nonstock = params.get('cat_nonstock')
            cat_obsolete = params.get('cat_obsolete')
            cat_oldbarcode = params.get('cat_oldbarcode')
            cat_oldpart = params.get('cat_oldpart')
            cat_ordflag = params.get('cat_ordflag')
            cat_pack = params.get('cat_pack')
            cat_packqty = params.get('cat_packqty')
            cat_part = params.get('cat_part')
            cat_parttype = params.get('cat_parttype')
            cat_pcode = params.get('cat_pcode')
            cat_pcount = params.get('cat_pcount')
            cat_pgroup = params.get('cat_pgroup')
            cat_pgtype = params.get('cat_pgtype')
            cat_pointval = params.get('cat_pointval')
            cat_ppack = params.get('cat_ppack')
            cat_pqtydi = params.get('cat_pqtydi')
            cat_priority = params.get('cat_priority')
            cat_psgroup = params.get('cat_psgroup')
            cat_qqtydi = params.get('cat_qqtydi')
            cat_recsal = params.get('cat_recsal')
            cat_royalty = params.get('cat_royalty')
            cat_royaltyfc = params.get('cat_royaltyfc')
            cat_rptcode = params.get('cat_rptcode')
            cat_salestype = params.get('cat_salestype')
            cat_sdesc = params.get('cat_sdesc')
            cat_sdesc2 = params.get('cat_sdesc2')
            cat_season = params.get('cat_season')
            cat_service = params.get('cat_service')
            cat_servicekit = params.get('cat_servicekit')
            cat_shortdesc = params.get('cat_shortdesc')
            cat_shortdesc2 = params.get('cat_shortdesc2')
            cat_slife = params.get('cat_slife')
            cat_slifef = params.get('cat_slifef')
            cat_spack = params.get('cat_spack')
            cat_specs = params.get('cat_specs')
            cat_specs2 = params.get('cat_specs2')
            cat_splkit = params.get('cat_splkit')
            cat_splname = params.get('cat_splname')
            cat_splname2 = params.get('cat_splname2')
            cat_splno = params.get('cat_splno')
            cat_splpart = params.get('cat_splpart')
            cat_spricecdate = params.get('cat_spricecdate')
            cat_stcost = params.get('cat_stcost')
            cat_stock = params.get('cat_stock')
            cat_subpar = params.get('cat_subpar')
            cat_substo = params.get('cat_substo')
            cat_supdat = params.get('cat_supdat')
            cat_supdate = params.get('cat_supdate')
            cat_supgrp = params.get('cat_supgrp')
            cat_suppar = params.get('cat_suppar')
            cat_suppart = params.get('cat_suppart')
            cat_supsto = params.get('cat_supsto')
            cat_supstock = params.get('cat_supstock')
            cat_type = params.get('cat_type')
            cat_uh = params.get('cat_uh')
            cat_ul = params.get('cat_ul')
            cat_uom = params.get('cat_uom')
            cat_uvol = params.get('cat_uvol')
            cat_uw = params.get('cat_uw')
            cat_uwt = params.get('cat_uwt')
            cat_vat = params.get('cat_vat')
            cat_vuom = params.get('cat_vuom')
            cat_wom = params.get('cat_wom')
            cat_wprd = params.get('cat_wprd')
            cat_wprdf = params.get('cat_wprdf')
            detail1 = params.get('detail1')
            detail2 = params.get('detail2')
            detail3 = params.get('detail3')
            lang_flag = params.get('lang_flag')
            lang_flag2 = params.get('lang_flag2')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')
            user_lmt = params.get('user_lmt')

            _logger.info("Creating catalog for cat_part: %s", cat_part)

            new_record = request.env['catalog'].sudo().create({
                    'cat_allzcost': cat_allzcost,
                    'cat_assembl': cat_assembl,
                    'cat_associategrp': cat_associategrp,
                    'cat_associatepart': cat_associatepart,
                    'cat_avcost': cat_avcost,
                    'cat_backward': cat_backward,
                    'cat_barcode': cat_barcode,
                    'cat_bltncode': cat_bltncode,
                    'cat_bulletin': cat_bulletin,
                    'cat_cat': cat_cat,
                    'cat_comments': cat_comments,
                    'cat_comments2': cat_comments2,
                    'cat_desc': cat_desc,
                    'cat_desc2': cat_desc2,
                    'cat_discont': cat_discont,
                    'cat_discontdate': cat_discontdate,
                    'cat_dsiamount': cat_dsiamount,
                    'cat_duty': cat_duty,
                    'cat_fccode': cat_fccode,
                    'cat_fccost': cat_fccost,
                    'cat_flag': cat_flag,
                    'cat_frac': cat_frac,
                    'cat_genorder': cat_genorder,
                    'cat_grouppart': cat_grouppart,
                    'cat_grp': cat_grp,
                    'cat_image': cat_image,
                    'cat_intrdate': cat_intrdate,
                    'cat_itemtype': cat_itemtype,
                    'cat_kit': cat_kit,
                    'cat_lastsprice': cat_lastsprice,
                    'cat_lccost': cat_lccost,
                    'cat_lrctdate': cat_lrctdate,
                    'cat_mainpartno': cat_mainpartno,
                    'cat_manu': cat_manu,
                    'cat_max': cat_max,
                    'cat_mccode': cat_mccode,
                    'cat_min': cat_min,
                    'cat_mmcode': cat_mmcode,
                    'cat_model': cat_model,
                    'cat_modelcode': cat_modelcode,
                    'cat_multispl': cat_multispl,
                    'cat_nonstock': cat_nonstock,
                    'cat_obsolete': cat_obsolete,
                    'cat_oldbarcode': cat_oldbarcode,
                    'cat_oldpart': cat_oldpart,
                    'cat_ordflag': cat_ordflag,
                    'cat_pack': cat_pack,
                    'cat_packqty': cat_packqty,
                    'cat_part': cat_part,
                    'cat_parttype': cat_parttype,
                    'cat_pcode': cat_pcode,
                    'cat_pcount': cat_pcount,
                    'cat_pgroup': cat_pgroup,
                    'cat_pgtype': cat_pgtype,
                    'cat_pointval': cat_pointval,
                    'cat_ppack': cat_ppack,
                    'cat_pqtydi': cat_pqtydi,
                    'cat_priority': cat_priority,
                    'cat_psgroup': cat_psgroup,
                    'cat_qqtydi': cat_qqtydi,
                    'cat_recsal': cat_recsal,
                    'cat_royalty': cat_royalty,
                    'cat_royaltyfc': cat_royaltyfc,
                    'cat_rptcode': cat_rptcode,
                    'cat_salestype': cat_salestype,
                    'cat_sdesc': cat_sdesc,
                    'cat_sdesc2': cat_sdesc2,
                    'cat_season': cat_season,
                    'cat_service': cat_service,
                    'cat_servicekit': cat_servicekit,
                    'cat_shortdesc': cat_shortdesc,
                    'cat_shortdesc2': cat_shortdesc2,
                    'cat_slife': cat_slife,
                    'cat_slifef': cat_slifef,
                    'cat_spack': cat_spack,
                    'cat_specs': cat_specs,
                    'cat_specs2': cat_specs2,
                    'cat_splkit': cat_splkit,
                    'cat_splname': cat_splname,
                    'cat_splname2': cat_splname2,
                    'cat_splno': cat_splno,
                    'cat_splpart': cat_splpart,
                    'cat_spricecdate': cat_spricecdate,
                    'cat_stcost': cat_stcost,
                    'cat_stock': cat_stock,
                    'cat_subpar': cat_subpar,
                    'cat_substo': cat_substo,
                    'cat_supdat': cat_supdat,
                    'cat_supdate': cat_supdate,
                    'cat_supgrp': cat_supgrp,
                    'cat_suppar': cat_suppar,
                    'cat_suppart': cat_suppart,
                    'cat_supsto': cat_supsto,
                    'cat_supstock': cat_supstock,
                    'cat_type': cat_type,
                    'cat_uh': cat_uh,
                    'cat_ul': cat_ul,
                    'cat_uom': cat_uom,
                    'cat_uvol': cat_uvol,
                    'cat_uw': cat_uw,
                    'cat_uwt': cat_uwt,
                    'cat_vat': cat_vat,
                    'cat_vuom': cat_vuom,
                    'cat_wom': cat_wom,
                    'cat_wprd': cat_wprd,
                    'cat_wprdf': cat_wprdf,
                    'detail1': detail1,
                    'detail2': detail2,
                    'detail3': detail3,
                    'lang_flag': lang_flag,
                    'lang_flag2': lang_flag2,
                    'user_id': user_id,
                    'user_lmd': user_lmd,
                    'user_lmt': user_lmt,
            })

            _logger.info("catalog created successfully for cat_part: %s", cat_part)
            return {
                "success": True,
                "message": f"catalog created for cat_grp: {cat_grp},cat_stock: {cat_stock} and cat_part: {cat_part}",
                "data": {
                    'cat_allzcost': new_record.cat_allzcost,
                    'cat_assembl': new_record.cat_assembl,
                    'cat_associategrp': new_record.cat_associategrp,
                    'cat_associatepart': new_record.cat_associatepart,
                    'cat_avcost': new_record.cat_avcost,
                    'cat_backward': new_record.cat_backward,
                    'cat_barcode': new_record.cat_barcode,
                    'cat_bltncode': new_record.cat_bltncode,
                    'cat_bulletin': new_record.cat_bulletin,
                    'cat_cat': new_record.cat_cat,
                    'cat_comments': new_record.cat_comments,
                    'cat_comments2': new_record.cat_comments2,
                    'cat_desc': new_record.cat_desc,
                    'cat_desc2': new_record.cat_desc2,
                    'cat_discont': new_record.cat_discont,
                    'cat_discontdate': new_record.cat_discontdate,
                    'cat_dsiamount': new_record.cat_dsiamount,
                    'cat_duty': new_record.cat_duty,
                    'cat_fccode': new_record.cat_fccode,
                    'cat_fccost': new_record.cat_fccost,
                    'cat_flag': new_record.cat_flag,
                    'cat_frac': new_record.cat_frac,
                    'cat_genorder': new_record.cat_genorder,
                    'cat_grouppart': new_record.cat_grouppart,
                    'cat_grp': new_record.cat_grp,
                    'cat_image': new_record.cat_image,
                    'cat_intrdate': new_record.cat_intrdate,
                    'cat_itemtype': new_record.cat_itemtype,
                    'cat_kit': new_record.cat_kit,
                    'cat_lastsprice': new_record.cat_lastsprice,
                    'cat_lccost': new_record.cat_lccost,
                    'cat_lrctdate': new_record.cat_lrctdate,
                    'cat_mainpartno': new_record.cat_mainpartno,
                    'cat_manu': new_record.cat_manu,
                    'cat_max': new_record.cat_max,
                    'cat_mccode': new_record.cat_mccode,
                    'cat_min': new_record.cat_min,
                    'cat_mmcode': new_record.cat_mmcode,
                    'cat_model': new_record.cat_model,
                    'cat_modelcode': new_record.cat_modelcode,
                    'cat_multispl': new_record.cat_multispl,
                    'cat_nonstock': new_record.cat_nonstock,
                    'cat_obsolete': new_record.cat_obsolete,
                    'cat_oldbarcode': new_record.cat_oldbarcode,
                    'cat_oldpart': new_record.cat_oldpart,
                    'cat_ordflag': new_record.cat_ordflag,
                    'cat_pack': new_record.cat_pack,
                    'cat_packqty': new_record.cat_packqty,
                    'cat_part': new_record.cat_part,
                    'cat_parttype': new_record.cat_parttype,
                    'cat_pcode': new_record.cat_pcode,
                    'cat_pcount': new_record.cat_pcount,
                    'cat_pgroup': new_record.cat_pgroup,
                    'cat_pgtype': new_record.cat_pgtype,
                    'cat_pointval': new_record.cat_pointval,
                    'cat_ppack': new_record.cat_ppack,
                    'cat_pqtydi': new_record.cat_pqtydi,
                    'cat_priority': new_record.cat_priority,
                    'cat_psgroup': new_record.cat_psgroup,
                    'cat_qqtydi': new_record.cat_qqtydi,
                    'cat_recsal': new_record.cat_recsal,
                    'cat_royalty': new_record.cat_royalty,
                    'cat_royaltyfc': new_record.cat_royaltyfc,
                    'cat_rptcode': new_record.cat_rptcode,
                    'cat_salestype': new_record.cat_salestype,
                    'cat_sdesc': new_record.cat_sdesc,
                    'cat_sdesc2': new_record.cat_sdesc2,
                    'cat_season': new_record.cat_season,
                    'cat_service': new_record.cat_service,
                    'cat_servicekit': new_record.cat_servicekit,
                    'cat_shortdesc': new_record.cat_shortdesc,
                    'cat_shortdesc2': new_record.cat_shortdesc2,
                    'cat_slife': new_record.cat_slife,
                    'cat_slifef': new_record.cat_slifef,
                    'cat_spack': new_record.cat_spack,
                    'cat_specs': new_record.cat_specs,
                    'cat_specs2': new_record.cat_specs2,
                    'cat_splkit': new_record.cat_splkit,
                    'cat_splname': new_record.cat_splname,
                    'cat_splname2': new_record.cat_splname2,
                    'cat_splno': new_record.cat_splno,
                    'cat_splpart': new_record.cat_splpart,
                    'cat_spricecdate': new_record.cat_spricecdate,
                    'cat_stcost': new_record.cat_stcost,
                    'cat_stock': new_record.cat_stock,
                    'cat_subpar': new_record.cat_subpar,
                    'cat_substo': new_record.cat_substo,
                    'cat_supdat': new_record.cat_supdat,
                    'cat_supdate': new_record.cat_supdate,
                    'cat_supgrp': new_record.cat_supgrp,
                    'cat_suppar': new_record.cat_suppar,
                    'cat_suppart': new_record.cat_suppart,
                    'cat_supsto': new_record.cat_supsto,
                    'cat_supstock': new_record.cat_supstock,
                    'cat_type': new_record.cat_type,
                    'cat_uh': new_record.cat_uh,
                    'cat_ul': new_record.cat_ul,
                    'cat_uom': new_record.cat_uom,
                    'cat_uvol': new_record.cat_uvol,
                    'cat_uw': new_record.cat_uw,
                    'cat_uwt': new_record.cat_uwt,
                    'cat_vat': new_record.cat_vat,
                    'cat_vuom': new_record.cat_vuom,
                    'cat_wom': new_record.cat_wom,
                    'cat_wprd': new_record.cat_wprd,
                    'cat_wprdf': new_record.cat_wprdf,
                    'detail1': new_record.detail1,
                    'detail2': new_record.detail2,
                    'detail3': new_record.detail3,
                    'lang_flag': new_record.lang_flag,
                    'lang_flag2': new_record.lang_flag2,
                    'user_id': new_record.user_id,
                    'user_lmd': new_record.user_lmd,
                    'user_lmt': new_record.user_lmt,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the catalog: %s", str(e))
            return {
                "error": "An error occurred while creating the catalog"
            }

    @validate_token
    @http.route("/api/catalog/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _catalog_update(self, **post):
        try:
            _logger.info("Attempting to update catalog...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cat_grp = params.get('cat_grp')
            cat_stock = params.get('cat_stock')
            cat_part = params.get('cat_part')

            if not cat_part:
                _logger.error("Missing 'cat_part' in params.")
                return {"error": "Missing required field: cat_part"}, 400  # Bad Request

            _logger.info("Searching for catalog with cat_part: %s", cat_part)

            # Search for the existing record
            catalog_update = request.env['catalog'].sudo().search([('cat_grp', '=', cat_grp),('cat_stock', '=', cat_stock),('cat_part', '=', cat_part)], limit=1)

            if not catalog_update:
                _logger.warning("catalog not found for cat_part: %s", cat_part)
                return {"error": f"catalog with cat_grp {cat_grp},cat_stock {cat_stock} and cat_part {cat_part} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("cat_grp","cat_stock","cat_part") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cat_part: %s", cat_part)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating catalog for cat_part: %s with data: %s", cat_part, update_vals)
            catalog_update.sudo().write(update_vals)

            _logger.info("catalog updated successfully for cat_part: %s", cat_part)
            return {
                "success": True,
                "message": f"catalog updated for cat_part: {cat_part}",
                "data": {
                                 'cat_allzcost': catalog_update.cat_allzcost,
                                 'cat_assembl': catalog_update.cat_assembl,
                                 'cat_associategrp': catalog_update.cat_associategrp,
                                 'cat_associatepart': catalog_update.cat_associatepart,
                                 'cat_avcost': catalog_update.cat_avcost,
                                 'cat_backward': catalog_update.cat_backward,
                                 'cat_barcode': catalog_update.cat_barcode,
                                 'cat_bltncode': catalog_update.cat_bltncode,
                                 'cat_bulletin': catalog_update.cat_bulletin,
                                 'cat_cat': catalog_update.cat_cat,
                                 'cat_comments': catalog_update.cat_comments,
                                 'cat_comments2': catalog_update.cat_comments2,
                                 'cat_desc': catalog_update.cat_desc,
                                 'cat_desc2': catalog_update.cat_desc2,
                                 'cat_discont': catalog_update.cat_discont,
                                 'cat_discontdate': catalog_update.cat_discontdate,
                                 'cat_dsiamount': catalog_update.cat_dsiamount,
                                 'cat_duty': catalog_update.cat_duty,
                                 'cat_fccode': catalog_update.cat_fccode,
                                 'cat_fccost': catalog_update.cat_fccost,
                                 'cat_flag': catalog_update.cat_flag,
                                 'cat_frac': catalog_update.cat_frac,
                                 'cat_genorder': catalog_update.cat_genorder,
                                 'cat_grouppart': catalog_update.cat_grouppart,
                                 'cat_grp': catalog_update.cat_grp,
                                 'cat_image': catalog_update.cat_image,
                                 'cat_intrdate': catalog_update.cat_intrdate,
                                 'cat_itemtype': catalog_update.cat_itemtype,
                                 'cat_kit': catalog_update.cat_kit,
                                 'cat_lastsprice': catalog_update.cat_lastsprice,
                                 'cat_lccost': catalog_update.cat_lccost,
                                 'cat_lrctdate': catalog_update.cat_lrctdate,
                                 'cat_mainpartno': catalog_update.cat_mainpartno,
                                 'cat_manu': catalog_update.cat_manu,
                                 'cat_max': catalog_update.cat_max,
                                 'cat_mccode': catalog_update.cat_mccode,
                                 'cat_min': catalog_update.cat_min,
                                 'cat_mmcode': catalog_update.cat_mmcode,
                                 'cat_model': catalog_update.cat_model,
                                 'cat_modelcode': catalog_update.cat_modelcode,
                                 'cat_multispl': catalog_update.cat_multispl,
                                 'cat_nonstock': catalog_update.cat_nonstock,
                                 'cat_obsolete': catalog_update.cat_obsolete,
                                 'cat_oldbarcode': catalog_update.cat_oldbarcode,
                                 'cat_oldpart': catalog_update.cat_oldpart,
                                 'cat_ordflag': catalog_update.cat_ordflag,
                                 'cat_pack': catalog_update.cat_pack,
                                 'cat_packqty': catalog_update.cat_packqty,
                                 'cat_part': catalog_update.cat_part,
                                 'cat_parttype': catalog_update.cat_parttype,
                                 'cat_pcode': catalog_update.cat_pcode,
                                 'cat_pcount': catalog_update.cat_pcount,
                                 'cat_pgroup': catalog_update.cat_pgroup,
                                 'cat_pgtype': catalog_update.cat_pgtype,
                                 'cat_pointval': catalog_update.cat_pointval,
                                 'cat_ppack': catalog_update.cat_ppack,
                                 'cat_pqtydi': catalog_update.cat_pqtydi,
                                 'cat_priority': catalog_update.cat_priority,
                                 'cat_psgroup': catalog_update.cat_psgroup,
                                 'cat_qqtydi': catalog_update.cat_qqtydi,
                                 'cat_recsal': catalog_update.cat_recsal,
                                 'cat_royalty': catalog_update.cat_royalty,
                                 'cat_royaltyfc': catalog_update.cat_royaltyfc,
                                 'cat_rptcode': catalog_update.cat_rptcode,
                                 'cat_salestype': catalog_update.cat_salestype,
                                 'cat_sdesc': catalog_update.cat_sdesc,
                                 'cat_sdesc2': catalog_update.cat_sdesc2,
                                 'cat_season': catalog_update.cat_season,
                                 'cat_service': catalog_update.cat_service,
                                 'cat_servicekit': catalog_update.cat_servicekit,
                                 'cat_shortdesc': catalog_update.cat_shortdesc,
                                 'cat_shortdesc2': catalog_update.cat_shortdesc2,
                                 'cat_slife': catalog_update.cat_slife,
                                 'cat_slifef': catalog_update.cat_slifef,
                                 'cat_spack': catalog_update.cat_spack,
                                 'cat_specs': catalog_update.cat_specs,
                                 'cat_specs2': catalog_update.cat_specs2,
                                 'cat_splkit': catalog_update.cat_splkit,
                                 'cat_splname': catalog_update.cat_splname,
                                 'cat_splname2': catalog_update.cat_splname2,
                                 'cat_splno': catalog_update.cat_splno,
                                 'cat_splpart': catalog_update.cat_splpart,
                                 'cat_spricecdate': catalog_update.cat_spricecdate,
                                 'cat_stcost': catalog_update.cat_stcost,
                                 'cat_stock': catalog_update.cat_stock,
                                 'cat_subpar': catalog_update.cat_subpar,
                                 'cat_substo': catalog_update.cat_substo,
                                 'cat_supdat': catalog_update.cat_supdat,
                                 'cat_supdate': catalog_update.cat_supdate,
                                 'cat_supgrp': catalog_update.cat_supgrp,
                                 'cat_suppar': catalog_update.cat_suppar,
                                 'cat_suppart': catalog_update.cat_suppart,
                                 'cat_supsto': catalog_update.cat_supsto,
                                 'cat_supstock': catalog_update.cat_supstock,
                                 'cat_type': catalog_update.cat_type,
                                 'cat_uh': catalog_update.cat_uh,
                                 'cat_ul': catalog_update.cat_ul,
                                 'cat_uom': catalog_update.cat_uom,
                                 'cat_uvol': catalog_update.cat_uvol,
                                 'cat_uw': catalog_update.cat_uw,
                                 'cat_uwt': catalog_update.cat_uwt,
                                 'cat_vat': catalog_update.cat_vat,
                                 'cat_vuom': catalog_update.cat_vuom,
                                 'cat_wom': catalog_update.cat_wom,
                                 'cat_wprd': catalog_update.cat_wprd,
                                 'cat_wprdf': catalog_update.cat_wprdf,
                                 'detail1': catalog_update.detail1,
                                 'detail2': catalog_update.detail2,
                                 'detail3': catalog_update.detail3,
                                 'lang_flag': catalog_update.lang_flag,
                                 'lang_flag2': catalog_update.lang_flag2,
                                 'user_id': catalog_update.user_id,
                                 'user_lmd': catalog_update.user_lmd,
                                 'user_lmt': catalog_update.user_lmt,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the catalog: %s", str(e))
            return {"error": "An error occurred while updating the catalog"}, 500  # Internal Server Error

    @validate_token
    @http.route('/api/catalog/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_catalog(self, **post):
        try:
            _logger.info("Attempting to delete catalog...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cat_part = params.get('cat_part')

            # Validate cat_part
            if not cat_part or not isinstance(cat_part, str):
                _logger.error("Invalid or missing cat_part.")
                return {"error": "Invalid or missing cat_part."}, 400

            _logger.info("Deleting catalog for cat_part: %s", cat_part)

            # Search for the record
            t_catalog_obj = request.env['catalog'].sudo().search([('cat_part', '=', cat_part)], limit=1)

            if not t_catalog_obj.exists():
                _logger.warning("catalog not found for cat_part: %s", cat_part)
                return {"error": f"catalog with cat_part: {cat_part} not found."}, 404

            # Delete the record
            t_catalog_obj.sudo().unlink()
            _logger.info("catalog deleted successfully for cat_part: %s", cat_part)

            return {"success": True, "message": f"catalog deleted for cat_part: {cat_part}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the catalog: %s", e)
            return {"error": "An error occurred while deleting the catalog"}, 500


    @validate_token
    @http.route("/api/bisalary/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _bisalary_search_all(self):
        try:
            _logger.info("Attempting to search for bisalary...")

            employeecode = request.params.get("employeecode")
            processdate = request.params.get("processdate")
            salarymonth = request.params.get("salarymonth")
           
            if employeecode and processdate and salarymonth:
                bisalary_obj = request.env['bisalary'].sudo().search([('employeecode', '=', employeecode),('processdate', '=', processdate),('salarymonth', '=', salarymonth)])
            else:
                bisalary_obj = request.env['bisalary'].sudo().search([])

            # Prepare the list of bisalary
            bisalary_list = []
            for bisalary_line in bisalary_obj:
                bisalary_data = {
                "absenteeismamount": bisalary_line.absenteeismamount,
                "absenteeismdays": bisalary_line.absenteeismdays,
                "accruedleaveamount": bisalary_line.accruedleaveamount,
                "accruedleavedays": bisalary_line.accruedleavedays,
                "advances": bisalary_line.advances,
                "advancespaid": bisalary_line.advancespaid,
                "allowance9": bisalary_line.allowance9,
                "analysiscode": bisalary_line.analysiscode,
                "analysiskey": bisalary_line.analysiskey,
                "basicsalary": bisalary_line.basicsalary,
                "billsotherdeductibles": bisalary_line.billsotherdeductibles,
                "bonus": bisalary_line.bonus,
                "city": bisalary_line.city,
                "commission": bisalary_line.commission,
                "costcentercode": bisalary_line.costcentercode,
                "costcentername": bisalary_line.costcentername,
                "department": bisalary_line.department,
                "departmentcode": bisalary_line.departmentcode,
                "departmentname": bisalary_line.departmentname,
                "e_dateleft": bisalary_line.e_dateleft,
                "employeecode": bisalary_line.employeecode,
                "employeegosi": bisalary_line.employeegosi,
                "employeergosi": bisalary_line.employeergosi,
                "eos": bisalary_line.eos,
                "eosadvances": bisalary_line.eosadvances,
                "facatorycode": bisalary_line.facatorycode,
                "factoryname": bisalary_line.factoryname,
                "finesamount": bisalary_line.finesamount,
                "finesdays": bisalary_line.finesdays,
                "fixeallowance": bisalary_line.fixeallowance,
                "foodallowance": bisalary_line.foodallowance,
                "fuelallowance": bisalary_line.fuelallowance,
                "gender": bisalary_line.gender,
                "holidayovertimehours": bisalary_line.holidayovertimehours,
                "housingallowance": bisalary_line.housingallowance,
                "jobtitle": bisalary_line.jobtitle,
                "jobtitlecode": bisalary_line.jobtitlecode,
                "joindate": bisalary_line.joindate,
                "loanrepayments": bisalary_line.loanrepayments,
                "loans": bisalary_line.loans,
                "locationcode": bisalary_line.locationcode,
                "locationname": bisalary_line.locationname,
                "mobileallowance": bisalary_line.mobileallowance,
                "name": bisalary_line.name,
                "nationality": bisalary_line.nationality,
                "nationalitycode": bisalary_line.nationalitycode,
                "netsalary": bisalary_line.netsalary,
                "otheradditions": bisalary_line.otheradditions,
                "otherdeductions": bisalary_line.otherdeductions,
                "overtimeamount": bisalary_line.overtimeamount,
                "overtimeamountamount": bisalary_line.overtimeamountamount,
                "overtimehours": bisalary_line.overtimehours,
                "personalleaveamount": bisalary_line.personalleaveamount,
                "personalleavedays": bisalary_line.personalleavedays,
                "processdate": bisalary_line.processdate,
                "publicholidaysamount": bisalary_line.publicholidaysamount,
                "publicholidaysdays": bisalary_line.publicholidaysdays,
                "region": bisalary_line.region,
                "salarygrade": bisalary_line.salarygrade,
                "salarygradedesc": bisalary_line.salarygradedesc,
                "salarymonth": bisalary_line.salarymonth,
                "salaryyear": bisalary_line.salaryyear,
                "schoolallowance": bisalary_line.schoolallowance,
                "severancepay": bisalary_line.severancepay,
                "subdepartmentcode": bisalary_line.subdepartmentcode,
                "subdepartmentname": bisalary_line.subdepartmentname,
                "ticketallowance": bisalary_line.ticketallowance,
                "tickets": bisalary_line.tickets,
                "totalpayable": bisalary_line.totalpayable,
                "transportallowance": bisalary_line.transportallowance,
                }
                bisalary_list.append(bisalary_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': bisalary_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for bisalary: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for bisalary"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    

    @validate_token
    @http.route("/api/bisalary/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _bisalary_create(self, **post):
        try:
            _logger.info("Attempting to create bisalary...")

            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            employeecode = params.get('employeecode')
            absenteeismamount = params.get('absenteeismamount')
            absenteeismdays = params.get('absenteeismdays')
            accruedleaveamount = params.get('accruedleaveamount')
            accruedleavedays = params.get('accruedleavedays')
            advances = params.get('advances')
            advancespaid = params.get('advancespaid')
            allowance9 = params.get('allowance9')
            analysiscode = params.get('analysiscode')
            analysiskey = params.get('analysiskey')
            basicsalary = params.get('basicsalary')
            billsotherdeductibles = params.get('billsotherdeductibles')
            bonus = params.get('bonus')
            city = params.get('city')
            commission = params.get('commission')
            costcentercode = params.get('costcentercode')
            costcentername = params.get('costcentername')
            department = params.get('department')
            departmentcode = params.get('departmentcode')
            departmentname = params.get('departmentname')
            e_dateleft = params.get('e_dateleft')
            employeegosi = params.get('employeegosi')
            employeergosi = params.get('employeergosi')
            eos = params.get('eos')
            eosadvances = params.get('eosadvances')
            facatorycode = params.get('facatorycode')
            factoryname = params.get('factoryname')
            finesamount = params.get('finesamount')
            finesdays = params.get('finesdays')
            fixeallowance = params.get('fixeallowance')
            foodallowance = params.get('foodallowance')
            fuelallowance = params.get('fuelallowance')
            gender = params.get('gender')
            holidayovertimehours = params.get('holidayovertimehours')
            housingallowance = params.get('housingallowance')
            jobtitle = params.get('jobtitle')
            jobtitlecode = params.get('jobtitlecode')
            joindate = params.get('joindate')
            loanrepayments = params.get('loanrepayments')
            loans = params.get('loans')
            locationcode = params.get('locationcode')
            locationname = params.get('locationname')
            mobileallowance = params.get('mobileallowance')
            name = params.get('name')
            nationality = params.get('nationality')
            nationalitycode = params.get('nationalitycode')
            netsalary = params.get('netsalary')
            otheradditions = params.get('otheradditions')
            otherdeductions = params.get('otherdeductions')
            overtimeamount = params.get('overtimeamount')
            overtimeamountamount = params.get('overtimeamountamount')
            overtimehours = params.get('overtimehours')
            personalleaveamount = params.get('personalleaveamount')
            personalleavedays = params.get('personalleavedays')
            processdate = params.get('processdate')
            publicholidaysamount = params.get('publicholidaysamount')
            publicholidaysdays = params.get('publicholidaysdays')
            region = params.get('region')
            salarygrade = params.get('salarygrade')
            salarygradedesc = params.get('salarygradedesc')
            salarymonth = params.get('salarymonth')
            salaryyear = params.get('salaryyear')
            schoolallowance = params.get('schoolallowance')
            severancepay = params.get('severancepay')
            subdepartmentcode = params.get('subdepartmentcode')
            subdepartmentname = params.get('subdepartmentname')
            ticketallowance = params.get('ticketallowance')
            tickets = params.get('tickets')
            totalpayable = params.get('totalpayable')
            transportallowance = params.get('transportallowance')

            existing_bisalary = request.env['bisalary'].sudo().search([('employeecode', '=', employeecode),('processdate', '=', processdate),('salarymonth', '=', salarymonth)], limit=1)
            if existing_bisalary:
                _logger.warning("bisalary already exists for employeecode: %s", employeecode)
                return {
                    "error": f"bisalary with employeecode {employeecode}, processdate {processdate} salarymonth {salarymonth} already exists."
                }

            absenteeismamount = params.get('absenteeismamount')
            absenteeismdays = params.get('absenteeismdays')
            accruedleaveamount = params.get('accruedleaveamount')
            accruedleavedays = params.get('accruedleavedays')
            advances = params.get('advances')
            advancespaid = params.get('advancespaid')
            allowance9 = params.get('allowance9')
            analysiscode = params.get('analysiscode')
            analysiskey = params.get('analysiskey')
            basicsalary = params.get('basicsalary')
            billsotherdeductibles = params.get('billsotherdeductibles')
            bonus = params.get('bonus')
            city = params.get('city')
            commission = params.get('commission')
            costcentercode = params.get('costcentercode')
            costcentername = params.get('costcentername')
            department = params.get('department')
            departmentcode = params.get('departmentcode')
            departmentname = params.get('departmentname')
            e_dateleft = params.get('e_dateleft')
            employeecode = params.get('employeecode')
            employeegosi = params.get('employeegosi')
            employeergosi = params.get('employeergosi')
            eos = params.get('eos')
            eosadvances = params.get('eosadvances')
            facatorycode = params.get('facatorycode')
            factoryname = params.get('factoryname')
            finesamount = params.get('finesamount')
            finesdays = params.get('finesdays')
            fixeallowance = params.get('fixeallowance')
            foodallowance = params.get('foodallowance')
            fuelallowance = params.get('fuelallowance')
            gender = params.get('gender')
            holidayovertimehours = params.get('holidayovertimehours')
            housingallowance = params.get('housingallowance')
            jobtitle = params.get('jobtitle')
            jobtitlecode = params.get('jobtitlecode')
            joindate = params.get('joindate')
            loanrepayments = params.get('loanrepayments')
            loans = params.get('loans')
            locationcode = params.get('locationcode')
            locationname = params.get('locationname')
            mobileallowance = params.get('mobileallowance')
            name = params.get('name')
            nationality = params.get('nationality')
            nationalitycode = params.get('nationalitycode')
            netsalary = params.get('netsalary')
            otheradditions = params.get('otheradditions')
            otherdeductions = params.get('otherdeductions')
            overtimeamount = params.get('overtimeamount')
            overtimeamountamount = params.get('overtimeamountamount')
            overtimehours = params.get('overtimehours')
            personalleaveamount = params.get('personalleaveamount')
            personalleavedays = params.get('personalleavedays')
            processdate = params.get('processdate')
            publicholidaysamount = params.get('publicholidaysamount')
            publicholidaysdays = params.get('publicholidaysdays')
            region = params.get('region')
            salarygrade = params.get('salarygrade')
            salarygradedesc = params.get('salarygradedesc')
            salarymonth = params.get('salarymonth')
            salaryyear = params.get('salaryyear')
            schoolallowance = params.get('schoolallowance')
            severancepay = params.get('severancepay')
            subdepartmentcode = params.get('subdepartmentcode')
            subdepartmentname = params.get('subdepartmentname')
            ticketallowance = params.get('ticketallowance')
            tickets = params.get('tickets')
            totalpayable = params.get('totalpayable')
            transportallowance = params.get('transportallowance')


            _logger.info("Creating bisalary for employeecode: %s", employeecode)

            new_record = request.env['bisalary'].sudo().create({
                    'absenteeismamount': absenteeismamount,
                    'absenteeismdays': absenteeismdays,
                    'accruedleaveamount': accruedleaveamount,
                    'accruedleavedays': accruedleavedays,
                    'advances': advances,
                    'advancespaid': advancespaid,
                    'allowance9': allowance9,
                    'analysiscode': analysiscode,
                    'analysiskey': analysiskey,
                    'basicsalary': basicsalary,
                    'billsotherdeductibles': billsotherdeductibles,
                    'bonus': bonus,
                    'city': city,
                    'commission': commission,
                    'costcentercode': costcentercode,
                    'costcentername': costcentername,
                    'department': department,
                    'departmentcode': departmentcode,
                    'departmentname': departmentname,
                    'e_dateleft': e_dateleft,
                    'employeecode': employeecode,
                    'employeegosi': employeegosi,
                    'employeergosi': employeergosi,
                    'eos': eos,
                    'eosadvances': eosadvances,
                    'facatorycode': facatorycode,
                    'factoryname': factoryname,
                    'finesamount': finesamount,
                    'finesdays': finesdays,
                    'fixeallowance': fixeallowance,
                    'foodallowance': foodallowance,
                    'fuelallowance': fuelallowance,
                    'gender': gender,
                    'holidayovertimehours': holidayovertimehours,
                    'housingallowance': housingallowance,
                    'jobtitle': jobtitle,
                    'jobtitlecode': jobtitlecode,
                    'joindate': joindate,
                    'loanrepayments': loanrepayments,
                    'loans': loans,
                    'locationcode': locationcode,
                    'locationname': locationname,
                    'mobileallowance': mobileallowance,
                    'name': name,
                    'nationality': nationality,
                    'nationalitycode': nationalitycode,
                    'netsalary': netsalary,
                    'otheradditions': otheradditions,
                    'otherdeductions': otherdeductions,
                    'overtimeamount': overtimeamount,
                    'overtimeamountamount': overtimeamountamount,
                    'overtimehours': overtimehours,
                    'personalleaveamount': personalleaveamount,
                    'personalleavedays': personalleavedays,
                    'processdate': processdate,
                    'publicholidaysamount': publicholidaysamount,
                    'publicholidaysdays': publicholidaysdays,
                    'region': region,
                    'salarygrade': salarygrade,
                    'salarygradedesc': salarygradedesc,
                    'salarymonth': salarymonth,
                    'salaryyear': salaryyear,
                    'schoolallowance': schoolallowance,
                    'severancepay': severancepay,
                    'subdepartmentcode': subdepartmentcode,
                    'subdepartmentname': subdepartmentname,
                    'ticketallowance': ticketallowance,
                    'tickets': tickets,
                    'totalpayable': totalpayable,
                    'transportallowance': transportallowance,

            })

            _logger.info("bisalary created successfully for employeecode: %s", employeecode)
            return {
                "success": True,
                "message": f"bisalary created for employeecode: {employeecode}",
                "data": {
                    'absenteeismamount': new_record.absenteeismamount,
                    'absenteeismdays': new_record.absenteeismdays,
                    'accruedleaveamount': new_record.accruedleaveamount,
                    'accruedleavedays': new_record.accruedleavedays,
                    'advances': new_record.advances,
                    'advancespaid': new_record.advancespaid,
                    'allowance9': new_record.allowance9,
                    'analysiscode': new_record.analysiscode,
                    'analysiskey': new_record.analysiskey,
                    'basicsalary': new_record.basicsalary,
                    'billsotherdeductibles': new_record.billsotherdeductibles,
                    'bonus': new_record.bonus,
                    'city': new_record.city,
                    'commission': new_record.commission,
                    'costcentercode': new_record.costcentercode,
                    'costcentername': new_record.costcentername,
                    'department': new_record.department,
                    'departmentcode': new_record.departmentcode,
                    'departmentname': new_record.departmentname,
                    'e_dateleft': new_record.e_dateleft,
                    'employeecode': new_record.employeecode,
                    'employeegosi': new_record.employeegosi,
                    'employeergosi': new_record.employeergosi,
                    'eos': new_record.eos,
                    'eosadvances': new_record.eosadvances,
                    'facatorycode': new_record.facatorycode,
                    'factoryname': new_record.factoryname,
                    'finesamount': new_record.finesamount,
                    'finesdays': new_record.finesdays,
                    'fixeallowance': new_record.fixeallowance,
                    'foodallowance': new_record.foodallowance,
                    'fuelallowance': new_record.fuelallowance,
                    'gender': new_record.gender,
                    'holidayovertimehours': new_record.holidayovertimehours,
                    'housingallowance': new_record.housingallowance,
                    'jobtitle': new_record.jobtitle,
                    'jobtitlecode': new_record.jobtitlecode,
                    'joindate': new_record.joindate,
                    'loanrepayments': new_record.loanrepayments,
                    'loans': new_record.loans,
                    'locationcode': new_record.locationcode,
                    'locationname': new_record.locationname,
                    'mobileallowance': new_record.mobileallowance,
                    'name': new_record.name,
                    'nationality': new_record.nationality,
                    'nationalitycode': new_record.nationalitycode,
                    'netsalary': new_record.netsalary,
                    'otheradditions': new_record.otheradditions,
                    'otherdeductions': new_record.otherdeductions,
                    'overtimeamount': new_record.overtimeamount,
                    'overtimeamountamount': new_record.overtimeamountamount,
                    'overtimehours': new_record.overtimehours,
                    'personalleaveamount': new_record.personalleaveamount,
                    'personalleavedays': new_record.personalleavedays,
                    'processdate': new_record.processdate,
                    'publicholidaysamount': new_record.publicholidaysamount,
                    'publicholidaysdays': new_record.publicholidaysdays,
                    'region': new_record.region,
                    'salarygrade': new_record.salarygrade,
                    'salarygradedesc': new_record.salarygradedesc,
                    'salarymonth': new_record.salarymonth,
                    'salaryyear': new_record.salaryyear,
                    'schoolallowance': new_record.schoolallowance,
                    'severancepay': new_record.severancepay,
                    'subdepartmentcode': new_record.subdepartmentcode,
                    'subdepartmentname': new_record.subdepartmentname,
                    'ticketallowance': new_record.ticketallowance,
                    'tickets': new_record.tickets,
                    'totalpayable': new_record.totalpayable,
                    'transportallowance': new_record.transportallowance,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the bisalary: %s", str(e))
            return {
                "error": "An error occurred while creating the bisalary"
            }

    @validate_token
    @http.route("/api/bisalary/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _bisalary_update(self, **post):
        try:
            _logger.info("Attempting to update bisalary...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            employeecode = params.get('employeecode')
            processdate = params.get('processdate')
            salarymonth = params.get('salarymonth')

            if not employeecode:
                _logger.error("Missing 'employeecode' in params.")
                return {"error": "Missing required field: employeecode"}, 400  # Bad Request

            _logger.info("Searching for bisalary with employeecode: %s", employeecode)

            # Search for the existing record
            bisalary_update = request.env['bisalary'].sudo().search([('employeecode', '=', employeecode),('processdate', '=', processdate),('salarymonth', '=', salarymonth)], limit=1)

            if not bisalary_update:
                _logger.warning("bisalary not found for employeecode: %s", employeecode)
                return {"error": f"bisalary with employeecode {employeecode} processdate {processdate}  and {salarymonth} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("employeecode","processdate","salarymonth") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for employeecode: %s", employeecode)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating bisalary for employeecode: %s with data: %s", employeecode, update_vals)
            bisalary_update.sudo().write(update_vals)

            _logger.info("bisalary updated successfully for employeecode: %s", employeecode)
            return {
                "success": True,
                "message": f"bisalary updated for employeecode: {employeecode}",
                "data": {
                                 'absenteeismamount': bisalary_update.absenteeismamount,
                                 'absenteeismdays': bisalary_update.absenteeismdays,
                                 'accruedleaveamount': bisalary_update.accruedleaveamount,
                                 'accruedleavedays': bisalary_update.accruedleavedays,
                                 'advances': bisalary_update.advances,
                                 'advancespaid': bisalary_update.advancespaid,
                                 'allowance9': bisalary_update.allowance9,
                                 'analysiscode': bisalary_update.analysiscode,
                                 'analysiskey': bisalary_update.analysiskey,
                                 'basicsalary': bisalary_update.basicsalary,
                                 'billsotherdeductibles': bisalary_update.billsotherdeductibles,
                                 'bonus': bisalary_update.bonus,
                                 'city': bisalary_update.city,
                                 'commission': bisalary_update.commission,
                                 'costcentercode': bisalary_update.costcentercode,
                                 'costcentername': bisalary_update.costcentername,
                                 'department': bisalary_update.department,
                                 'departmentcode': bisalary_update.departmentcode,
                                 'departmentname': bisalary_update.departmentname,
                                 'e_dateleft': bisalary_update.e_dateleft,
                                 'employeecode': bisalary_update.employeecode,
                                 'employeegosi': bisalary_update.employeegosi,
                                 'employeergosi': bisalary_update.employeergosi,
                                 'eos': bisalary_update.eos,
                                 'eosadvances': bisalary_update.eosadvances,
                                 'facatorycode': bisalary_update.facatorycode,
                                 'factoryname': bisalary_update.factoryname,
                                 'finesamount': bisalary_update.finesamount,
                                 'finesdays': bisalary_update.finesdays,
                                 'fixeallowance': bisalary_update.fixeallowance,
                                 'foodallowance': bisalary_update.foodallowance,
                                 'fuelallowance': bisalary_update.fuelallowance,
                                 'gender': bisalary_update.gender,
                                 'holidayovertimehours': bisalary_update.holidayovertimehours,
                                 'housingallowance': bisalary_update.housingallowance,
                                 'jobtitle': bisalary_update.jobtitle,
                                 'jobtitlecode': bisalary_update.jobtitlecode,
                                 'joindate': bisalary_update.joindate,
                                 'loanrepayments': bisalary_update.loanrepayments,
                                 'loans': bisalary_update.loans,
                                 'locationcode': bisalary_update.locationcode,
                                 'locationname': bisalary_update.locationname,
                                 'mobileallowance': bisalary_update.mobileallowance,
                                 'name': bisalary_update.name,
                                 'nationality': bisalary_update.nationality,
                                 'nationalitycode': bisalary_update.nationalitycode,
                                 'netsalary': bisalary_update.netsalary,
                                 'otheradditions': bisalary_update.otheradditions,
                                 'otherdeductions': bisalary_update.otherdeductions,
                                 'overtimeamount': bisalary_update.overtimeamount,
                                 'overtimeamountamount': bisalary_update.overtimeamountamount,
                                 'overtimehours': bisalary_update.overtimehours,
                                 'personalleaveamount': bisalary_update.personalleaveamount,
                                 'personalleavedays': bisalary_update.personalleavedays,
                                 'processdate': bisalary_update.processdate,
                                 'publicholidaysamount': bisalary_update.publicholidaysamount,
                                 'publicholidaysdays': bisalary_update.publicholidaysdays,
                                 'region': bisalary_update.region,
                                 'salarygrade': bisalary_update.salarygrade,
                                 'salarygradedesc': bisalary_update.salarygradedesc,
                                 'salarymonth': bisalary_update.salarymonth,
                                 'salaryyear': bisalary_update.salaryyear,
                                 'schoolallowance': bisalary_update.schoolallowance,
                                 'severancepay': bisalary_update.severancepay,
                                 'subdepartmentcode': bisalary_update.subdepartmentcode,
                                 'subdepartmentname': bisalary_update.subdepartmentname,
                                 'ticketallowance': bisalary_update.ticketallowance,
                                 'tickets': bisalary_update.tickets,
                                 'totalpayable': bisalary_update.totalpayable,
                                 'transportallowance': bisalary_update.transportallowance,

                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the bisalary: %s", str(e))
            return {"error": "An error occurred while updating the bisalary"}, 500  # Internal Server Error

    @validate_token
    @http.route('/api/bisalary/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_bisalary(self, **post):
        try:
            _logger.info("Attempting to delete bisalary...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            employeecode = params.get('employeecode')

            # Validate employeecode
            if not employeecode or not isinstance(employeecode, str):
                _logger.error("Invalid or missing employeecode.")
                return {"error": "Invalid or missing employeecode."}, 400

            _logger.info("Deleting bisalary for employeecode: %s", employeecode)

            # Search for the record
            t_bisalary_obj = request.env['bisalary'].sudo().search([('employeecode', '=', employeecode)], limit=1)

            if not t_bisalary_obj.exists():
                _logger.warning("bisalary not found for employeecode: %s", employeecode)
                return {"error": f"bisalary with employeecode: {employeecode} not found."}, 404

            # Delete the record
            t_bisalary_obj.sudo().unlink()
            _logger.info("bisalary deleted successfully for employeecode: %s", employeecode)

            return {"success": True, "message": f"bisalary deleted for employeecode: {employeecode}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the bisalary: %s", e)
            return {"error": "An error occurred while deleting the bisalary"}, 500

    
    @validate_token
    @http.route("/api/customer/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _customer_search_all(self):
        try:
            _logger.info("Attempting to search for customer...")

            cst_no = request.params.get("cst_no")
           
            if cst_no:
                customer_obj = request.env['customer'].sudo().search([('cst_no', '=', cst_no)])
            else:
                customer_obj = request.env['customer'].sudo().search([])

            # Prepare the list of customer
            customer_list = []
            for customer_line in customer_obj:
                customer_data = {
                "cst_account": customer_line.cst_account,
                "cst_add": customer_line.cst_add,
                "cst_add2": customer_line.cst_add2,
                "cst_addno": customer_line.cst_addno,
                "cst_alloweditcstname": customer_line.cst_alloweditcstname,
                "cst_allowloyalty": customer_line.cst_allowloyalty,
                "cst_balance": customer_line.cst_balance,
                "cst_buildno": customer_line.cst_buildno,
                "cst_calcretailfromfix": customer_line.cst_calcretailfromfix,
                "cst_climit": customer_line.cst_climit,
                "cst_cname": customer_line.cst_cname,
                "cst_cname2": customer_line.cst_cname2,
                "cst_comreg": customer_line.cst_comreg,
                "cst_credit": customer_line.cst_credit,
                "cst_cstclassification": customer_line.cst_cstclassification,
                "cst_cstpromogrp": customer_line.cst_cstpromogrp,
                "cst_ctitle": customer_line.cst_ctitle,
                "cst_ctitle2": customer_line.cst_ctitle2,
                "cst_defslt": customer_line.cst_defslt,
                "cst_defwh": customer_line.cst_defwh,
                "cst_disabled": customer_line.cst_disabled,
                "cst_district": customer_line.cst_district,
                "cst_doctype": customer_line.cst_doctype,
                "cst_dsireq": customer_line.cst_dsireq,
                "cst_email": customer_line.cst_email,
                "cst_export": customer_line.cst_export,
                "cst_exsh": customer_line.cst_exsh,
                "cst_fax": customer_line.cst_fax,
                "cst_hhscash": customer_line.cst_hhscash,
                "cst_idnumber": customer_line.cst_idnumber,
                "cst_intdate": customer_line.cst_intdate,
                "cst_invreqautocrnote": customer_line.cst_invreqautocrnote,
                "cst_lpoint": customer_line.cst_lpoint,
                "cst_lredeem": customer_line.cst_lredeem,
                "cst_message": customer_line.cst_message,
                "cst_message2": customer_line.cst_message2,
                "cst_name": customer_line.cst_name,
                "cst_name2": customer_line.cst_name2,
                "cst_nationality": customer_line.cst_nationality,
                "cst_nearby": customer_line.cst_nearby,
                "cst_no": customer_line.cst_no,
                "cst_noofvehicles": customer_line.cst_noofvehicles,
                "cst_odsi": customer_line.cst_odsi,
                "cst_otheradd": customer_line.cst_otheradd,
                "cst_partcustomer": customer_line.cst_partcustomer,
                "cst_pcode": customer_line.cst_pcode,
                "cst_region": customer_line.cst_region,
                "cst_showdiscount": customer_line.cst_showdiscount,
                "cst_sman": customer_line.cst_sman,
                "cst_streetname": customer_line.cst_streetname,
                "cst_subregion": customer_line.cst_subregion,
                "cst_suspendc": customer_line.cst_suspendc,
                "cst_tele": customer_line.cst_tele,
                "cst_tprv": customer_line.cst_tprv,
                "cst_ty1": customer_line.cst_ty1,
                "cst_ty2": customer_line.cst_ty2,
                "cst_ty3": customer_line.cst_ty3,
                "cst_ty4": customer_line.cst_ty4,
                "cst_vatgrp": customer_line.cst_vatgrp,
                "cst_vatreg": customer_line.cst_vatreg,
                "cst_whcrcustomer": customer_line.cst_whcrcustomer,
                "cst_ytd": customer_line.cst_ytd,
                "lang_flag": customer_line.lang_flag,
                "lang_flag2": customer_line.lang_flag2,
                "user_id": customer_line.user_id,
                "user_lmd": customer_line.user_lmd,
                }
                customer_list.append(customer_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': customer_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for customer: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for customer"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    

    @validate_token
    @http.route("/api/customer/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _customer_create(self, **post):
        try:
            _logger.info("Attempting to create customer...")

            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            cst_no = params.get('cst_no')
            cst_account = params.get('cst_account')
            cst_add = params.get('cst_add')
            cst_add2 = params.get('cst_add2')
            cst_addno = params.get('cst_addno')
            cst_alloweditcstname = params.get('cst_alloweditcstname')
            cst_allowloyalty = params.get('cst_allowloyalty')
            cst_balance = params.get('cst_balance')
            cst_buildno = params.get('cst_buildno')
            cst_calcretailfromfix = params.get('cst_calcretailfromfix')
            cst_climit = params.get('cst_climit')
            cst_cname = params.get('cst_cname')
            cst_cname2 = params.get('cst_cname2')
            cst_comreg = params.get('cst_comreg')
            cst_credit = params.get('cst_credit')
            cst_cstclassification = params.get('cst_cstclassification')
            cst_cstpromogrp = params.get('cst_cstpromogrp')
            cst_ctitle = params.get('cst_ctitle')
            cst_ctitle2 = params.get('cst_ctitle2')
            cst_defslt = params.get('cst_defslt')
            cst_defwh = params.get('cst_defwh')
            cst_disabled = params.get('cst_disabled')
            cst_district = params.get('cst_district')
            cst_doctype = params.get('cst_doctype')
            cst_dsireq = params.get('cst_dsireq')
            cst_email = params.get('cst_email')
            cst_export = params.get('cst_export')
            cst_exsh = params.get('cst_exsh')
            cst_fax = params.get('cst_fax')
            cst_hhscash = params.get('cst_hhscash')
            cst_idnumber = params.get('cst_idnumber')
            cst_intdate = params.get('cst_intdate')
            cst_invreqautocrnote = params.get('cst_invreqautocrnote')
            cst_lpoint = params.get('cst_lpoint')
            cst_lredeem = params.get('cst_lredeem')
            cst_message = params.get('cst_message')
            cst_message2 = params.get('cst_message2')
            cst_name = params.get('cst_name')
            cst_name2 = params.get('cst_name2')
            cst_nationality = params.get('cst_nationality')
            cst_nearby = params.get('cst_nearby')
            cst_noofvehicles = params.get('cst_noofvehicles')
            cst_odsi = params.get('cst_odsi')
            cst_otheradd = params.get('cst_otheradd')
            cst_partcustomer = params.get('cst_partcustomer')
            cst_pcode = params.get('cst_pcode')
            cst_region = params.get('cst_region')
            cst_showdiscount = params.get('cst_showdiscount')
            cst_sman = params.get('cst_sman')
            cst_streetname = params.get('cst_streetname')
            cst_subregion = params.get('cst_subregion')
            cst_suspendc = params.get('cst_suspendc')
            cst_tele = params.get('cst_tele')
            cst_tprv = params.get('cst_tprv')
            cst_ty1 = params.get('cst_ty1')
            cst_ty2 = params.get('cst_ty2')
            cst_ty3 = params.get('cst_ty3')
            cst_ty4 = params.get('cst_ty4')
            cst_vatgrp = params.get('cst_vatgrp')
            cst_vatreg = params.get('cst_vatreg')
            cst_whcrcustomer = params.get('cst_whcrcustomer')
            cst_ytd = params.get('cst_ytd')
            lang_flag = params.get('lang_flag')
            lang_flag2 = params.get('lang_flag2')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')

            existing_customer = request.env['customer'].sudo().search([('cst_no', '=', cst_no)], limit=1)
            if existing_customer:
                _logger.warning("customer already exists for cst_no: %s", cst_no)
                return {
                    "error": f"customer with cst_no {cst_no} already exists."
                }

            cst_account = params.get('cst_account')
            cst_add = params.get('cst_add')
            cst_add2 = params.get('cst_add2')
            cst_addno = params.get('cst_addno')
            cst_alloweditcstname = params.get('cst_alloweditcstname')
            cst_allowloyalty = params.get('cst_allowloyalty')
            cst_balance = params.get('cst_balance')
            cst_buildno = params.get('cst_buildno')
            cst_calcretailfromfix = params.get('cst_calcretailfromfix')
            cst_climit = params.get('cst_climit')
            cst_cname = params.get('cst_cname')
            cst_cname2 = params.get('cst_cname2')
            cst_comreg = params.get('cst_comreg')
            cst_credit = params.get('cst_credit')
            cst_cstclassification = params.get('cst_cstclassification')
            cst_cstpromogrp = params.get('cst_cstpromogrp')
            cst_ctitle = params.get('cst_ctitle')
            cst_ctitle2 = params.get('cst_ctitle2')
            cst_defslt = params.get('cst_defslt')
            cst_defwh = params.get('cst_defwh')
            cst_disabled = params.get('cst_disabled')
            cst_district = params.get('cst_district')
            cst_doctype = params.get('cst_doctype')
            cst_dsireq = params.get('cst_dsireq')
            cst_email = params.get('cst_email')
            cst_export = params.get('cst_export')
            cst_exsh = params.get('cst_exsh')
            cst_fax = params.get('cst_fax')
            cst_hhscash = params.get('cst_hhscash')
            cst_idnumber = params.get('cst_idnumber')
            cst_intdate = params.get('cst_intdate')
            cst_invreqautocrnote = params.get('cst_invreqautocrnote')
            cst_lpoint = params.get('cst_lpoint')
            cst_lredeem = params.get('cst_lredeem')
            cst_message = params.get('cst_message')
            cst_message2 = params.get('cst_message2')
            cst_name = params.get('cst_name')
            cst_name2 = params.get('cst_name2')
            cst_nationality = params.get('cst_nationality')
            cst_nearby = params.get('cst_nearby')
            cst_no = params.get('cst_no')
            cst_noofvehicles = params.get('cst_noofvehicles')
            cst_odsi = params.get('cst_odsi')
            cst_otheradd = params.get('cst_otheradd')
            cst_partcustomer = params.get('cst_partcustomer')
            cst_pcode = params.get('cst_pcode')
            cst_region = params.get('cst_region')
            cst_showdiscount = params.get('cst_showdiscount')
            cst_sman = params.get('cst_sman')
            cst_streetname = params.get('cst_streetname')
            cst_subregion = params.get('cst_subregion')
            cst_suspendc = params.get('cst_suspendc')
            cst_tele = params.get('cst_tele')
            cst_tprv = params.get('cst_tprv')
            cst_ty1 = params.get('cst_ty1')
            cst_ty2 = params.get('cst_ty2')
            cst_ty3 = params.get('cst_ty3')
            cst_ty4 = params.get('cst_ty4')
            cst_vatgrp = params.get('cst_vatgrp')
            cst_vatreg = params.get('cst_vatreg')
            cst_whcrcustomer = params.get('cst_whcrcustomer')
            cst_ytd = params.get('cst_ytd')
            lang_flag = params.get('lang_flag')
            lang_flag2 = params.get('lang_flag2')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')


            _logger.info("Creating customer for cst_no: %s", cst_no)

            new_record = request.env['customer'].sudo().create({
                    'cst_account': cst_account,
                    'cst_add': cst_add,
                    'cst_add2': cst_add2,
                    'cst_addno': cst_addno,
                    'cst_alloweditcstname': cst_alloweditcstname,
                    'cst_allowloyalty': cst_allowloyalty,
                    'cst_balance': cst_balance,
                    'cst_buildno': cst_buildno,
                    'cst_calcretailfromfix': cst_calcretailfromfix,
                    'cst_climit': cst_climit,
                    'cst_cname': cst_cname,
                    'cst_cname2': cst_cname2,
                    'cst_comreg': cst_comreg,
                    'cst_credit': cst_credit,
                    'cst_cstclassification': cst_cstclassification,
                    'cst_cstpromogrp': cst_cstpromogrp,
                    'cst_ctitle': cst_ctitle,
                    'cst_ctitle2': cst_ctitle2,
                    'cst_defslt': cst_defslt,
                    'cst_defwh': cst_defwh,
                    'cst_disabled': cst_disabled,
                    'cst_district': cst_district,
                    'cst_doctype': cst_doctype,
                    'cst_dsireq': cst_dsireq,
                    'cst_email': cst_email,
                    'cst_export': cst_export,
                    'cst_exsh': cst_exsh,
                    'cst_fax': cst_fax,
                    'cst_hhscash': cst_hhscash,
                    'cst_idnumber': cst_idnumber,
                    'cst_intdate': cst_intdate,
                    'cst_invreqautocrnote': cst_invreqautocrnote,
                    'cst_lpoint': cst_lpoint,
                    'cst_lredeem': cst_lredeem,
                    'cst_message': cst_message,
                    'cst_message2': cst_message2,
                    'cst_name': cst_name,
                    'cst_name2': cst_name2,
                    'cst_nationality': cst_nationality,
                    'cst_nearby': cst_nearby,
                    'cst_no': cst_no,
                    'cst_noofvehicles': cst_noofvehicles,
                    'cst_odsi': cst_odsi,
                    'cst_otheradd': cst_otheradd,
                    'cst_partcustomer': cst_partcustomer,
                    'cst_pcode': cst_pcode,
                    'cst_region': cst_region,
                    'cst_showdiscount': cst_showdiscount,
                    'cst_sman': cst_sman,
                    'cst_streetname': cst_streetname,
                    'cst_subregion': cst_subregion,
                    'cst_suspendc': cst_suspendc,
                    'cst_tele': cst_tele,
                    'cst_tprv': cst_tprv,
                    'cst_ty1': cst_ty1,
                    'cst_ty2': cst_ty2,
                    'cst_ty3': cst_ty3,
                    'cst_ty4': cst_ty4,
                    'cst_vatgrp': cst_vatgrp,
                    'cst_vatreg': cst_vatreg,
                    'cst_whcrcustomer': cst_whcrcustomer,
                    'cst_ytd': cst_ytd,
                    'lang_flag': lang_flag,
                    'lang_flag2': lang_flag2,
                    'user_id': user_id,
                    'user_lmd': user_lmd,

            })

            _logger.info("customer created successfully for cst_no: %s", cst_no)
            return {
                "success": True,
                "message": f"customer created for cst_no: {cst_no}",
                "data": {
                    'cst_account': new_record.cst_account,
                    'cst_add': new_record.cst_add,
                    'cst_add2': new_record.cst_add2,
                    'cst_addno': new_record.cst_addno,
                    'cst_alloweditcstname': new_record.cst_alloweditcstname,
                    'cst_allowloyalty': new_record.cst_allowloyalty,
                    'cst_balance': new_record.cst_balance,
                    'cst_buildno': new_record.cst_buildno,
                    'cst_calcretailfromfix': new_record.cst_calcretailfromfix,
                    'cst_climit': new_record.cst_climit,
                    'cst_cname': new_record.cst_cname,
                    'cst_cname2': new_record.cst_cname2,
                    'cst_comreg': new_record.cst_comreg,
                    'cst_credit': new_record.cst_credit,
                    'cst_cstclassification': new_record.cst_cstclassification,
                    'cst_cstpromogrp': new_record.cst_cstpromogrp,
                    'cst_ctitle': new_record.cst_ctitle,
                    'cst_ctitle2': new_record.cst_ctitle2,
                    'cst_defslt': new_record.cst_defslt,
                    'cst_defwh': new_record.cst_defwh,
                    'cst_disabled': new_record.cst_disabled,
                    'cst_district': new_record.cst_district,
                    'cst_doctype': new_record.cst_doctype,
                    'cst_dsireq': new_record.cst_dsireq,
                    'cst_email': new_record.cst_email,
                    'cst_export': new_record.cst_export,
                    'cst_exsh': new_record.cst_exsh,
                    'cst_fax': new_record.cst_fax,
                    'cst_hhscash': new_record.cst_hhscash,
                    'cst_idnumber': new_record.cst_idnumber,
                    'cst_intdate': new_record.cst_intdate,
                    'cst_invreqautocrnote': new_record.cst_invreqautocrnote,
                    'cst_lpoint': new_record.cst_lpoint,
                    'cst_lredeem': new_record.cst_lredeem,
                    'cst_message': new_record.cst_message,
                    'cst_message2': new_record.cst_message2,
                    'cst_name': new_record.cst_name,
                    'cst_name2': new_record.cst_name2,
                    'cst_nationality': new_record.cst_nationality,
                    'cst_nearby': new_record.cst_nearby,
                    'cst_no': new_record.cst_no,
                    'cst_noofvehicles': new_record.cst_noofvehicles,
                    'cst_odsi': new_record.cst_odsi,
                    'cst_otheradd': new_record.cst_otheradd,
                    'cst_partcustomer': new_record.cst_partcustomer,
                    'cst_pcode': new_record.cst_pcode,
                    'cst_region': new_record.cst_region,
                    'cst_showdiscount': new_record.cst_showdiscount,
                    'cst_sman': new_record.cst_sman,
                    'cst_streetname': new_record.cst_streetname,
                    'cst_subregion': new_record.cst_subregion,
                    'cst_suspendc': new_record.cst_suspendc,
                    'cst_tele': new_record.cst_tele,
                    'cst_tprv': new_record.cst_tprv,
                    'cst_ty1': new_record.cst_ty1,
                    'cst_ty2': new_record.cst_ty2,
                    'cst_ty3': new_record.cst_ty3,
                    'cst_ty4': new_record.cst_ty4,
                    'cst_vatgrp': new_record.cst_vatgrp,
                    'cst_vatreg': new_record.cst_vatreg,
                    'cst_whcrcustomer': new_record.cst_whcrcustomer,
                    'cst_ytd': new_record.cst_ytd,
                    'lang_flag': new_record.lang_flag,
                    'lang_flag2': new_record.lang_flag2,
                    'user_id': new_record.user_id,
                    'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the customer: %s", str(e))
            return {
                "error": "An error occurred while creating the customer"
            }

    @validate_token
    @http.route("/api/customer/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _customer_update(self, **post):
        try:
            _logger.info("Attempting to update customer...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            cst_no = params.get('cst_no')
            if not cst_no:
                _logger.error("Missing 'cst_no' in params.")
                return {"error": "Missing required field: cst_no"}, 400  # Bad Request

            _logger.info("Searching for customer with cst_no: %s", cst_no)

            # Search for the existing record
            customer_update = request.env['customer'].sudo().search([('cst_no', '=', cst_no)], limit=1)

            if not customer_update:
                _logger.warning("customer not found for cst_no: %s", cst_no)
                return {"error": f"customer with cst_no {cst_no} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key != "cst_no" and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for cst_no: %s", cst_no)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating customer for cst_no: %s with data: %s", cst_no, update_vals)
            customer_update.sudo().write(update_vals)

            _logger.info("customer updated successfully for cst_no: %s", cst_no)
            return {
                "success": True,
                "message": f"customer updated for cst_no: {cst_no}",
                "data": {
                                 'cst_account': customer_update.cst_account,
                                 'cst_add': customer_update.cst_add,
                                 'cst_add2': customer_update.cst_add2,
                                 'cst_addno': customer_update.cst_addno,
                                 'cst_alloweditcstname': customer_update.cst_alloweditcstname,
                                 'cst_allowloyalty': customer_update.cst_allowloyalty,
                                 'cst_balance': customer_update.cst_balance,
                                 'cst_buildno': customer_update.cst_buildno,
                                 'cst_calcretailfromfix': customer_update.cst_calcretailfromfix,
                                 'cst_climit': customer_update.cst_climit,
                                 'cst_cname': customer_update.cst_cname,
                                 'cst_cname2': customer_update.cst_cname2,
                                 'cst_comreg': customer_update.cst_comreg,
                                 'cst_credit': customer_update.cst_credit,
                                 'cst_cstclassification': customer_update.cst_cstclassification,
                                 'cst_cstpromogrp': customer_update.cst_cstpromogrp,
                                 'cst_ctitle': customer_update.cst_ctitle,
                                 'cst_ctitle2': customer_update.cst_ctitle2,
                                 'cst_defslt': customer_update.cst_defslt,
                                 'cst_defwh': customer_update.cst_defwh,
                                 'cst_disabled': customer_update.cst_disabled,
                                 'cst_district': customer_update.cst_district,
                                 'cst_doctype': customer_update.cst_doctype,
                                 'cst_dsireq': customer_update.cst_dsireq,
                                 'cst_email': customer_update.cst_email,
                                 'cst_export': customer_update.cst_export,
                                 'cst_exsh': customer_update.cst_exsh,
                                 'cst_fax': customer_update.cst_fax,
                                 'cst_hhscash': customer_update.cst_hhscash,
                                 'cst_idnumber': customer_update.cst_idnumber,
                                 'cst_intdate': customer_update.cst_intdate,
                                 'cst_invreqautocrnote': customer_update.cst_invreqautocrnote,
                                 'cst_lpoint': customer_update.cst_lpoint,
                                 'cst_lredeem': customer_update.cst_lredeem,
                                 'cst_message': customer_update.cst_message,
                                 'cst_message2': customer_update.cst_message2,
                                 'cst_name': customer_update.cst_name,
                                 'cst_name2': customer_update.cst_name2,
                                 'cst_nationality': customer_update.cst_nationality,
                                 'cst_nearby': customer_update.cst_nearby,
                                 'cst_no': customer_update.cst_no,
                                 'cst_noofvehicles': customer_update.cst_noofvehicles,
                                 'cst_odsi': customer_update.cst_odsi,
                                 'cst_otheradd': customer_update.cst_otheradd,
                                 'cst_partcustomer': customer_update.cst_partcustomer,
                                 'cst_pcode': customer_update.cst_pcode,
                                 'cst_region': customer_update.cst_region,
                                 'cst_showdiscount': customer_update.cst_showdiscount,
                                 'cst_sman': customer_update.cst_sman,
                                 'cst_streetname': customer_update.cst_streetname,
                                 'cst_subregion': customer_update.cst_subregion,
                                 'cst_suspendc': customer_update.cst_suspendc,
                                 'cst_tele': customer_update.cst_tele,
                                 'cst_tprv': customer_update.cst_tprv,
                                 'cst_ty1': customer_update.cst_ty1,
                                 'cst_ty2': customer_update.cst_ty2,
                                 'cst_ty3': customer_update.cst_ty3,
                                 'cst_ty4': customer_update.cst_ty4,
                                 'cst_vatgrp': customer_update.cst_vatgrp,
                                 'cst_vatreg': customer_update.cst_vatreg,
                                 'cst_whcrcustomer': customer_update.cst_whcrcustomer,
                                 'cst_ytd': customer_update.cst_ytd,
                                 'lang_flag': customer_update.lang_flag,
                                 'lang_flag2': customer_update.lang_flag2,
                                 'user_id': customer_update.user_id,
                                 'user_lmd': customer_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the customer: %s", str(e))
            return {"error": "An error occurred while updating the customer"}, 500  # Internal Server Error

    @validate_token
    @http.route('/api/customer/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_customer(self, **post):
        try:
            _logger.info("Attempting to delete customer...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            cst_no = params.get('cst_no')

            # Validate cst_no
            if not cst_no or not isinstance(cst_no, str):
                _logger.error("Invalid or missing cst_no.")
                return {"error": "Invalid or missing cst_no."}, 400

            _logger.info("Deleting customer for cst_no: %s", cst_no)

            # Search for the record
            t_customer_obj = request.env['customer'].sudo().search([('cst_no', '=', cst_no)], limit=1)

            if not t_customer_obj.exists():
                _logger.warning("customer not found for cst_no: %s", cst_no)
                return {"error": f"customer with cst_no: {cst_no} not found."}, 404

            # Delete the record
            t_customer_obj.sudo().unlink()
            _logger.info("customer deleted successfully for cst_no: %s", cst_no)

            return {"success": True, "message": f"customer deleted for cst_no: {cst_no}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the customer: %s", e)
            return {"error": "An error occurred while deleting the customer"}, 500


    @validate_token
    @http.route("/api/t_warehouse/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_warehouse_search_all(self):
        try:
            _logger.info("Attempting to search for t_warehouse...")

            wh_code = request.params.get("wh_code")
           
            if wh_code:
                t_warehouse_obj = request.env['t.warehouse'].sudo().search([('wh_code', '=', wh_code)])
            else:
                t_warehouse_obj = request.env['t.warehouse'].sudo().search([])


            # Prepare the list of t_warehouse
            t_warehouse_list = []
            for t_warehouse_line in t_warehouse_obj:
                t_warehouse_data = {
                "lang_flag": t_warehouse_line.lang_flag,
                "lang_flag2": t_warehouse_line.lang_flag2,
                "old_code": t_warehouse_line.old_code,
                "user_id": t_warehouse_line.user_id,
                "user_lmd": t_warehouse_line.user_lmd,
                "user_lmt": t_warehouse_line.user_lmt,
                "wh_acconline": t_warehouse_line.wh_acconline,
                "wh_address": t_warehouse_line.wh_address,
                "wh_address2": t_warehouse_line.wh_address2,
                "wh_allordqty": t_warehouse_line.wh_allordqty,
                "wh_applysdisc": t_warehouse_line.wh_applysdisc,
                "wh_autofj": t_warehouse_line.wh_autofj,
                "wh_batchno": t_warehouse_line.wh_batchno,
                "wh_bpdefault": t_warehouse_line.wh_bpdefault,
                "wh_bpname": t_warehouse_line.wh_bpname,
                "wh_budgetfri": t_warehouse_line.wh_budgetfri,
                "wh_budgetmon": t_warehouse_line.wh_budgetmon,
                "wh_budgetsat": t_warehouse_line.wh_budgetsat,
                "wh_budgetsun": t_warehouse_line.wh_budgetsun,
                "wh_budgetthu": t_warehouse_line.wh_budgetthu,
                "wh_budgettue": t_warehouse_line.wh_budgettue,
                "wh_budgetwed": t_warehouse_line.wh_budgetwed,
                "wh_cc": t_warehouse_line.wh_cc,
                "wh_city": t_warehouse_line.wh_city,
                "wh_cntno": t_warehouse_line.wh_cntno,
                "wh_code": t_warehouse_line.wh_code,
                "wh_companyname": t_warehouse_line.wh_companyname,
                "wh_companyname2": t_warehouse_line.wh_companyname2,
                "wh_conrcvnextno": t_warehouse_line.wh_conrcvnextno,
                "wh_conrcvprefix": t_warehouse_line.wh_conrcvprefix,
                "wh_costabovealwd": t_warehouse_line.wh_costabovealwd,
                "wh_crno": t_warehouse_line.wh_crno,
                "wh_cstno": t_warehouse_line.wh_cstno,
                "wh_cstwh": t_warehouse_line.wh_cstwh,
                "wh_desc": t_warehouse_line.wh_desc,
                "wh_desc2": t_warehouse_line.wh_desc2,
                "wh_email": t_warehouse_line.wh_email,
                "wh_emailserver": t_warehouse_line.wh_emailserver,
                "wh_excludegenorder": t_warehouse_line.wh_excludegenorder,
                "wh_exposstype": t_warehouse_line.wh_exposstype,
                "wh_expsyncdate": t_warehouse_line.wh_expsyncdate,
                "wh_fjno": t_warehouse_line.wh_fjno,
                "wh_fjpfix": t_warehouse_line.wh_fjpfix,
                "wh_group": t_warehouse_line.wh_group,
                "wh_gsprncfgfpath": t_warehouse_line.wh_gsprncfgfpath,
                "wh_iedir": t_warehouse_line.wh_iedir,
                "wh_inactive": t_warehouse_line.wh_inactive,
                "wh_installationgrp": t_warehouse_line.wh_installationgrp,
                "wh_installationpartnumber": t_warehouse_line.wh_installationpartnumber,
                "wh_installationstock": t_warehouse_line.wh_installationstock,
                "wh_invreqautocrnote": t_warehouse_line.wh_invreqautocrnote,
                "wh_libarcode": t_warehouse_line.wh_libarcode,
                "wh_licstno": t_warehouse_line.wh_licstno,
                "wh_lidate": t_warehouse_line.wh_lidate,
                "wh_mainwh": t_warehouse_line.wh_mainwh,
                "wh_maxadddisc": t_warehouse_line.wh_maxadddisc,
                "wh_mgremail": t_warehouse_line.wh_mgremail,
                "wh_mpass": t_warehouse_line.wh_mpass,
                "wh_oldonline": t_warehouse_line.wh_oldonline,
                "wh_online": t_warehouse_line.wh_online,
                "wh_onlinecstdelinext": t_warehouse_line.wh_onlinecstdelinext,
                "wh_onlinecstdeliprefix": t_warehouse_line.wh_onlinecstdeliprefix,
                "wh_onlinecstinvnext": t_warehouse_line.wh_onlinecstinvnext,
                "wh_onlinecstinvprefix": t_warehouse_line.wh_onlinecstinvprefix,
                "wh_onlinecstordnext": t_warehouse_line.wh_onlinecstordnext,
                "wh_onlinecstordprefix": t_warehouse_line.wh_onlinecstordprefix,
                "wh_onlinewhouse": t_warehouse_line.wh_onlinewhouse,
                "wh_opentransferscreen": t_warehouse_line.wh_opentransferscreen,
                "wh_pdfversion": t_warehouse_line.wh_pdfversion,
                "wh_penystdate": t_warehouse_line.wh_penystdate,
                "wh_period": t_warehouse_line.wh_period,
                "wh_pmessage": t_warehouse_line.wh_pmessage,
                "wh_pmessage2": t_warehouse_line.wh_pmessage2,
                "wh_postavgcostvar": t_warehouse_line.wh_postavgcostvar,
                "wh_preprint": t_warehouse_line.wh_preprint,
                "wh_printpm": t_warehouse_line.wh_printpm,
                "wh_qtsamediscp": t_warehouse_line.wh_qtsamediscp,
                "wh_rctbatchnext": t_warehouse_line.wh_rctbatchnext,
                "wh_rctbatchprefix": t_warehouse_line.wh_rctbatchprefix,
                "wh_region": t_warehouse_line.wh_region,
                "wh_remote": t_warehouse_line.wh_remote,
                "wh_shp01": t_warehouse_line.wh_shp01,
                "wh_shp02": t_warehouse_line.wh_shp02,
                "wh_shp03": t_warehouse_line.wh_shp03,
                "wh_shp04": t_warehouse_line.wh_shp04,
                "wh_shp05": t_warehouse_line.wh_shp05,
                "wh_shp06": t_warehouse_line.wh_shp06,
                "wh_shp07": t_warehouse_line.wh_shp07,
                "wh_shp08": t_warehouse_line.wh_shp08,
                "wh_shp09": t_warehouse_line.wh_shp09,
                "wh_shp10": t_warehouse_line.wh_shp10,
                "wh_shp11": t_warehouse_line.wh_shp11,
                "wh_shp12": t_warehouse_line.wh_shp12,
                "wh_shp13": t_warehouse_line.wh_shp13,
                "wh_shp14": t_warehouse_line.wh_shp14,
                "wh_shp15": t_warehouse_line.wh_shp15,
                "wh_shp16": t_warehouse_line.wh_shp16,
                "wh_shp17": t_warehouse_line.wh_shp17,
                "wh_shp18": t_warehouse_line.wh_shp18,
                "wh_shp19": t_warehouse_line.wh_shp19,
                "wh_shp20": t_warehouse_line.wh_shp20,
                "wh_shp21": t_warehouse_line.wh_shp21,
                "wh_shp22": t_warehouse_line.wh_shp22,
                "wh_shp23": t_warehouse_line.wh_shp23,
                "wh_shp24": t_warehouse_line.wh_shp24,
                "wh_syncdate": t_warehouse_line.wh_syncdate,
                "wh_tel": t_warehouse_line.wh_tel,
                "wh_transportgrp": t_warehouse_line.wh_transportgrp,
                "wh_transportpartnumber": t_warehouse_line.wh_transportpartnumber,
                "wh_transportstock": t_warehouse_line.wh_transportstock,
                "wh_trn_autoreceive": t_warehouse_line.wh_trn_autoreceive,
                "wh_trnpicklistrequired": t_warehouse_line.wh_trnpicklistrequired,
                "wh_vatregno": t_warehouse_line.wh_vatregno,
                "wh_xmlpdffbkpath": t_warehouse_line.wh_xmlpdffbkpath,
                "wh_xmlpdffsavetodb": t_warehouse_line.wh_xmlpdffsavetodb,
                "wh_year": t_warehouse_line.wh_year,

                }
                t_warehouse_list.append(t_warehouse_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_warehouse_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_warehouse: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_warehouse"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    

    @validate_token
    @http.route("/api/t_warehouse/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_warehouse_create(self, **post):
        try:
            _logger.info("Attempting to create t_warehouse...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            wh_code = params.get('wh_code')
            lang_flag = params.get('lang_flag')
            lang_flag2 = params.get('lang_flag2')
            old_code = params.get('old_code')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')
            user_lmt = params.get('user_lmt')
            wh_acconline = params.get('wh_acconline')
            wh_address = params.get('wh_address')
            wh_address2 = params.get('wh_address2')
            wh_allordqty = params.get('wh_allordqty')
            wh_applysdisc = params.get('wh_applysdisc')
            wh_autofj = params.get('wh_autofj')
            wh_batchno = params.get('wh_batchno')
            wh_bpdefault = params.get('wh_bpdefault')
            wh_bpname = params.get('wh_bpname')
            wh_budgetfri = params.get('wh_budgetfri')
            wh_budgetmon = params.get('wh_budgetmon')
            wh_budgetsat = params.get('wh_budgetsat')
            wh_budgetsun = params.get('wh_budgetsun')
            wh_budgetthu = params.get('wh_budgetthu')
            wh_budgettue = params.get('wh_budgettue')
            wh_budgetwed = params.get('wh_budgetwed')
            wh_cc = params.get('wh_cc')
            wh_city = params.get('wh_city')
            wh_cntno = params.get('wh_cntno')
            wh_companyname = params.get('wh_companyname')
            wh_companyname2 = params.get('wh_companyname2')
            wh_conrcvnextno = params.get('wh_conrcvnextno')
            wh_conrcvprefix = params.get('wh_conrcvprefix')
            wh_costabovealwd = params.get('wh_costabovealwd')
            wh_crno = params.get('wh_crno')
            wh_cstno = params.get('wh_cstno')
            wh_cstwh = params.get('wh_cstwh')
            wh_desc = params.get('wh_desc')
            wh_desc2 = params.get('wh_desc2')
            wh_email = params.get('wh_email')
            wh_emailserver = params.get('wh_emailserver')
            wh_excludegenorder = params.get('wh_excludegenorder')
            wh_exposstype = params.get('wh_exposstype')
            wh_expsyncdate = params.get('wh_expsyncdate')
            wh_fjno = params.get('wh_fjno')
            wh_fjpfix = params.get('wh_fjpfix')
            wh_group = params.get('wh_group')
            wh_gsprncfgfpath = params.get('wh_gsprncfgfpath')
            wh_iedir = params.get('wh_iedir')
            wh_inactive = params.get('wh_inactive')
            wh_installationgrp = params.get('wh_installationgrp')
            wh_installationpartnumber = params.get('wh_installationpartnumber')
            wh_installationstock = params.get('wh_installationstock')
            wh_invreqautocrnote = params.get('wh_invreqautocrnote')
            wh_libarcode = params.get('wh_libarcode')
            wh_licstno = params.get('wh_licstno')
            wh_lidate = params.get('wh_lidate')
            wh_mainwh = params.get('wh_mainwh')
            wh_maxadddisc = params.get('wh_maxadddisc')
            wh_mgremail = params.get('wh_mgremail')
            wh_mpass = params.get('wh_mpass')
            wh_oldonline = params.get('wh_oldonline')
            wh_online = params.get('wh_online')
            wh_onlinecstdelinext = params.get('wh_onlinecstdelinext')
            wh_onlinecstdeliprefix = params.get('wh_onlinecstdeliprefix')
            wh_onlinecstinvnext = params.get('wh_onlinecstinvnext')
            wh_onlinecstinvprefix = params.get('wh_onlinecstinvprefix')
            wh_onlinecstordnext = params.get('wh_onlinecstordnext')
            wh_onlinecstordprefix = params.get('wh_onlinecstordprefix')
            wh_onlinewhouse = params.get('wh_onlinewhouse')
            wh_opentransferscreen = params.get('wh_opentransferscreen')
            wh_pdfversion = params.get('wh_pdfversion')
            wh_penystdate = params.get('wh_penystdate')
            wh_period = params.get('wh_period')
            wh_pmessage = params.get('wh_pmessage')
            wh_pmessage2 = params.get('wh_pmessage2')
            wh_postavgcostvar = params.get('wh_postavgcostvar')
            wh_preprint = params.get('wh_preprint')
            wh_printpm = params.get('wh_printpm')
            wh_qtsamediscp = params.get('wh_qtsamediscp')
            wh_rctbatchnext = params.get('wh_rctbatchnext')
            wh_rctbatchprefix = params.get('wh_rctbatchprefix')
            wh_region = params.get('wh_region')
            wh_remote = params.get('wh_remote')
            wh_shp01 = params.get('wh_shp01')
            wh_shp02 = params.get('wh_shp02')
            wh_shp03 = params.get('wh_shp03')
            wh_shp04 = params.get('wh_shp04')
            wh_shp05 = params.get('wh_shp05')
            wh_shp06 = params.get('wh_shp06')
            wh_shp07 = params.get('wh_shp07')
            wh_shp08 = params.get('wh_shp08')
            wh_shp09 = params.get('wh_shp09')
            wh_shp10 = params.get('wh_shp10')
            wh_shp11 = params.get('wh_shp11')
            wh_shp12 = params.get('wh_shp12')
            wh_shp13 = params.get('wh_shp13')
            wh_shp14 = params.get('wh_shp14')
            wh_shp15 = params.get('wh_shp15')
            wh_shp16 = params.get('wh_shp16')
            wh_shp17 = params.get('wh_shp17')
            wh_shp18 = params.get('wh_shp18')
            wh_shp19 = params.get('wh_shp19')
            wh_shp20 = params.get('wh_shp20')
            wh_shp21 = params.get('wh_shp21')
            wh_shp22 = params.get('wh_shp22')
            wh_shp23 = params.get('wh_shp23')
            wh_shp24 = params.get('wh_shp24')
            wh_syncdate = params.get('wh_syncdate')
            wh_tel = params.get('wh_tel')
            wh_transportgrp = params.get('wh_transportgrp')
            wh_transportpartnumber = params.get('wh_transportpartnumber')
            wh_transportstock = params.get('wh_transportstock')
            wh_trn_autoreceive = params.get('wh_trn_autoreceive')
            wh_trnpicklistrequired = params.get('wh_trnpicklistrequired')
            wh_vatregno = params.get('wh_vatregno')
            wh_xmlpdffbkpath = params.get('wh_xmlpdffbkpath')
            wh_xmlpdffsavetodb = params.get('wh_xmlpdffsavetodb')
            wh_year = params.get('wh_year')

            existing_t_warehouse = request.env['t.warehouse'].sudo().search([('wh_code', '=', wh_code)], limit=1)
            if existing_t_warehouse:
                _logger.warning("t_warehouse already exists for wh_code: %s", wh_code)
                return {
                    "error": f"t_warehouse with wh_code {wh_code} already exists."
                }

            lang_flag = params.get('lang_flag')
            lang_flag2 = params.get('lang_flag2')
            old_code = params.get('old_code')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')
            user_lmt = params.get('user_lmt')
            wh_acconline = params.get('wh_acconline')
            wh_address = params.get('wh_address')
            wh_address2 = params.get('wh_address2')
            wh_allordqty = params.get('wh_allordqty')
            wh_applysdisc = params.get('wh_applysdisc')
            wh_autofj = params.get('wh_autofj')
            wh_batchno = params.get('wh_batchno')
            wh_bpdefault = params.get('wh_bpdefault')
            wh_bpname = params.get('wh_bpname')
            wh_budgetfri = params.get('wh_budgetfri')
            wh_budgetmon = params.get('wh_budgetmon')
            wh_budgetsat = params.get('wh_budgetsat')
            wh_budgetsun = params.get('wh_budgetsun')
            wh_budgetthu = params.get('wh_budgetthu')
            wh_budgettue = params.get('wh_budgettue')
            wh_budgetwed = params.get('wh_budgetwed')
            wh_cc = params.get('wh_cc')
            wh_city = params.get('wh_city')
            wh_cntno = params.get('wh_cntno')
            wh_code = params.get('wh_code')
            wh_companyname = params.get('wh_companyname')
            wh_companyname2 = params.get('wh_companyname2')
            wh_conrcvnextno = params.get('wh_conrcvnextno')
            wh_conrcvprefix = params.get('wh_conrcvprefix')
            wh_costabovealwd = params.get('wh_costabovealwd')
            wh_crno = params.get('wh_crno')
            wh_cstno = params.get('wh_cstno')
            wh_cstwh = params.get('wh_cstwh')
            wh_desc = params.get('wh_desc')
            wh_desc2 = params.get('wh_desc2')
            wh_email = params.get('wh_email')
            wh_emailserver = params.get('wh_emailserver')
            wh_excludegenorder = params.get('wh_excludegenorder')
            wh_exposstype = params.get('wh_exposstype')
            wh_expsyncdate = params.get('wh_expsyncdate')
            wh_fjno = params.get('wh_fjno')
            wh_fjpfix = params.get('wh_fjpfix')
            wh_group = params.get('wh_group')
            wh_gsprncfgfpath = params.get('wh_gsprncfgfpath')
            wh_iedir = params.get('wh_iedir')
            wh_inactive = params.get('wh_inactive')
            wh_installationgrp = params.get('wh_installationgrp')
            wh_installationpartnumber = params.get('wh_installationpartnumber')
            wh_installationstock = params.get('wh_installationstock')
            wh_invreqautocrnote = params.get('wh_invreqautocrnote')
            wh_libarcode = params.get('wh_libarcode')
            wh_licstno = params.get('wh_licstno')
            wh_lidate = params.get('wh_lidate')
            wh_mainwh = params.get('wh_mainwh')
            wh_maxadddisc = params.get('wh_maxadddisc')
            wh_mgremail = params.get('wh_mgremail')
            wh_mpass = params.get('wh_mpass')
            wh_oldonline = params.get('wh_oldonline')
            wh_online = params.get('wh_online')
            wh_onlinecstdelinext = params.get('wh_onlinecstdelinext')
            wh_onlinecstdeliprefix = params.get('wh_onlinecstdeliprefix')
            wh_onlinecstinvnext = params.get('wh_onlinecstinvnext')
            wh_onlinecstinvprefix = params.get('wh_onlinecstinvprefix')
            wh_onlinecstordnext = params.get('wh_onlinecstordnext')
            wh_onlinecstordprefix = params.get('wh_onlinecstordprefix')
            wh_onlinewhouse = params.get('wh_onlinewhouse')
            wh_opentransferscreen = params.get('wh_opentransferscreen')
            wh_pdfversion = params.get('wh_pdfversion')
            wh_penystdate = params.get('wh_penystdate')
            wh_period = params.get('wh_period')
            wh_pmessage = params.get('wh_pmessage')
            wh_pmessage2 = params.get('wh_pmessage2')
            wh_postavgcostvar = params.get('wh_postavgcostvar')
            wh_preprint = params.get('wh_preprint')
            wh_printpm = params.get('wh_printpm')
            wh_qtsamediscp = params.get('wh_qtsamediscp')
            wh_rctbatchnext = params.get('wh_rctbatchnext')
            wh_rctbatchprefix = params.get('wh_rctbatchprefix')
            wh_region = params.get('wh_region')
            wh_remote = params.get('wh_remote')
            wh_shp01 = params.get('wh_shp01')
            wh_shp02 = params.get('wh_shp02')
            wh_shp03 = params.get('wh_shp03')
            wh_shp04 = params.get('wh_shp04')
            wh_shp05 = params.get('wh_shp05')
            wh_shp06 = params.get('wh_shp06')
            wh_shp07 = params.get('wh_shp07')
            wh_shp08 = params.get('wh_shp08')
            wh_shp09 = params.get('wh_shp09')
            wh_shp10 = params.get('wh_shp10')
            wh_shp11 = params.get('wh_shp11')
            wh_shp12 = params.get('wh_shp12')
            wh_shp13 = params.get('wh_shp13')
            wh_shp14 = params.get('wh_shp14')
            wh_shp15 = params.get('wh_shp15')
            wh_shp16 = params.get('wh_shp16')
            wh_shp17 = params.get('wh_shp17')
            wh_shp18 = params.get('wh_shp18')
            wh_shp19 = params.get('wh_shp19')
            wh_shp20 = params.get('wh_shp20')
            wh_shp21 = params.get('wh_shp21')
            wh_shp22 = params.get('wh_shp22')
            wh_shp23 = params.get('wh_shp23')
            wh_shp24 = params.get('wh_shp24')
            wh_syncdate = params.get('wh_syncdate')
            wh_tel = params.get('wh_tel')
            wh_transportgrp = params.get('wh_transportgrp')
            wh_transportpartnumber = params.get('wh_transportpartnumber')
            wh_transportstock = params.get('wh_transportstock')
            wh_trn_autoreceive = params.get('wh_trn_autoreceive')
            wh_trnpicklistrequired = params.get('wh_trnpicklistrequired')
            wh_vatregno = params.get('wh_vatregno')
            wh_xmlpdffbkpath = params.get('wh_xmlpdffbkpath')
            wh_xmlpdffsavetodb = params.get('wh_xmlpdffsavetodb')
            wh_year = params.get('wh_year')


            _logger.info("Creating t_warehouse for wh_code: %s", wh_code)

            new_record = request.env['t.warehouse'].sudo().create({
                    'lang_flag': lang_flag,
                    'lang_flag2': lang_flag2,
                    'old_code': old_code,
                    'user_id': user_id,
                    'user_lmd': user_lmd,
                    'user_lmt': user_lmt,
                    'wh_acconline': wh_acconline,
                    'wh_address': wh_address,
                    'wh_address2': wh_address2,
                    'wh_allordqty': wh_allordqty,
                    'wh_applysdisc': wh_applysdisc,
                    'wh_autofj': wh_autofj,
                    'wh_batchno': wh_batchno,
                    'wh_bpdefault': wh_bpdefault,
                    'wh_bpname': wh_bpname,
                    'wh_budgetfri': wh_budgetfri,
                    'wh_budgetmon': wh_budgetmon,
                    'wh_budgetsat': wh_budgetsat,
                    'wh_budgetsun': wh_budgetsun,
                    'wh_budgetthu': wh_budgetthu,
                    'wh_budgettue': wh_budgettue,
                    'wh_budgetwed': wh_budgetwed,
                    'wh_cc': wh_cc,
                    'wh_city': wh_city,
                    'wh_cntno': wh_cntno,
                    'wh_code': wh_code,
                    'wh_companyname': wh_companyname,
                    'wh_companyname2': wh_companyname2,
                    'wh_conrcvnextno': wh_conrcvnextno,
                    'wh_conrcvprefix': wh_conrcvprefix,
                    'wh_costabovealwd': wh_costabovealwd,
                    'wh_crno': wh_crno,
                    'wh_cstno': wh_cstno,
                    'wh_cstwh': wh_cstwh,
                    'wh_desc': wh_desc,
                    'wh_desc2': wh_desc2,
                    'wh_email': wh_email,
                    'wh_emailserver': wh_emailserver,
                    'wh_excludegenorder': wh_excludegenorder,
                    'wh_exposstype': wh_exposstype,
                    'wh_expsyncdate': wh_expsyncdate,
                    'wh_fjno': wh_fjno,
                    'wh_fjpfix': wh_fjpfix,
                    'wh_group': wh_group,
                    'wh_gsprncfgfpath': wh_gsprncfgfpath,
                    'wh_iedir': wh_iedir,
                    'wh_inactive': wh_inactive,
                    'wh_installationgrp': wh_installationgrp,
                    'wh_installationpartnumber': wh_installationpartnumber,
                    'wh_installationstock': wh_installationstock,
                    'wh_invreqautocrnote': wh_invreqautocrnote,
                    'wh_libarcode': wh_libarcode,
                    'wh_licstno': wh_licstno,
                    'wh_lidate': wh_lidate,
                    'wh_mainwh': wh_mainwh,
                    'wh_maxadddisc': wh_maxadddisc,
                    'wh_mgremail': wh_mgremail,
                    'wh_mpass': wh_mpass,
                    'wh_oldonline': wh_oldonline,
                    'wh_online': wh_online,
                    'wh_onlinecstdelinext': wh_onlinecstdelinext,
                    'wh_onlinecstdeliprefix': wh_onlinecstdeliprefix,
                    'wh_onlinecstinvnext': wh_onlinecstinvnext,
                    'wh_onlinecstinvprefix': wh_onlinecstinvprefix,
                    'wh_onlinecstordnext': wh_onlinecstordnext,
                    'wh_onlinecstordprefix': wh_onlinecstordprefix,
                    'wh_onlinewhouse': wh_onlinewhouse,
                    'wh_opentransferscreen': wh_opentransferscreen,
                    'wh_pdfversion': wh_pdfversion,
                    'wh_penystdate': wh_penystdate,
                    'wh_period': wh_period,
                    'wh_pmessage': wh_pmessage,
                    'wh_pmessage2': wh_pmessage2,
                    'wh_postavgcostvar': wh_postavgcostvar,
                    'wh_preprint': wh_preprint,
                    'wh_printpm': wh_printpm,
                    'wh_qtsamediscp': wh_qtsamediscp,
                    'wh_rctbatchnext': wh_rctbatchnext,
                    'wh_rctbatchprefix': wh_rctbatchprefix,
                    'wh_region': wh_region,
                    'wh_remote': wh_remote,
                    'wh_shp01': wh_shp01,
                    'wh_shp02': wh_shp02,
                    'wh_shp03': wh_shp03,
                    'wh_shp04': wh_shp04,
                    'wh_shp05': wh_shp05,
                    'wh_shp06': wh_shp06,
                    'wh_shp07': wh_shp07,
                    'wh_shp08': wh_shp08,
                    'wh_shp09': wh_shp09,
                    'wh_shp10': wh_shp10,
                    'wh_shp11': wh_shp11,
                    'wh_shp12': wh_shp12,
                    'wh_shp13': wh_shp13,
                    'wh_shp14': wh_shp14,
                    'wh_shp15': wh_shp15,
                    'wh_shp16': wh_shp16,
                    'wh_shp17': wh_shp17,
                    'wh_shp18': wh_shp18,
                    'wh_shp19': wh_shp19,
                    'wh_shp20': wh_shp20,
                    'wh_shp21': wh_shp21,
                    'wh_shp22': wh_shp22,
                    'wh_shp23': wh_shp23,
                    'wh_shp24': wh_shp24,
                    'wh_syncdate': wh_syncdate,
                    'wh_tel': wh_tel,
                    'wh_transportgrp': wh_transportgrp,
                    'wh_transportpartnumber': wh_transportpartnumber,
                    'wh_transportstock': wh_transportstock,
                    'wh_trn_autoreceive': wh_trn_autoreceive,
                    'wh_trnpicklistrequired': wh_trnpicklistrequired,
                    'wh_vatregno': wh_vatregno,
                    'wh_xmlpdffbkpath': wh_xmlpdffbkpath,
                    'wh_xmlpdffsavetodb': wh_xmlpdffsavetodb,
                    'wh_year': wh_year,
            })

            _logger.info("t_warehouse created successfully for wh_code: %s", wh_code)
            return {
                "success": True,
                "message": f"t_warehouse created for wh_code: {wh_code}",
                "data": {
                    'lang_flag': new_record.lang_flag,
                    'lang_flag2': new_record.lang_flag2,
                    'old_code': new_record.old_code,
                    'user_id': new_record.user_id,
                    'user_lmd': new_record.user_lmd,
                    'user_lmt': new_record.user_lmt,
                    'wh_acconline': new_record.wh_acconline,
                    'wh_address': new_record.wh_address,
                    'wh_address2': new_record.wh_address2,
                    'wh_allordqty': new_record.wh_allordqty,
                    'wh_applysdisc': new_record.wh_applysdisc,
                    'wh_autofj': new_record.wh_autofj,
                    'wh_batchno': new_record.wh_batchno,
                    'wh_bpdefault': new_record.wh_bpdefault,
                    'wh_bpname': new_record.wh_bpname,
                    'wh_budgetfri': new_record.wh_budgetfri,
                    'wh_budgetmon': new_record.wh_budgetmon,
                    'wh_budgetsat': new_record.wh_budgetsat,
                    'wh_budgetsun': new_record.wh_budgetsun,
                    'wh_budgetthu': new_record.wh_budgetthu,
                    'wh_budgettue': new_record.wh_budgettue,
                    'wh_budgetwed': new_record.wh_budgetwed,
                    'wh_cc': new_record.wh_cc,
                    'wh_city': new_record.wh_city,
                    'wh_cntno': new_record.wh_cntno,
                    'wh_code': new_record.wh_code,
                    'wh_companyname': new_record.wh_companyname,
                    'wh_companyname2': new_record.wh_companyname2,
                    'wh_conrcvnextno': new_record.wh_conrcvnextno,
                    'wh_conrcvprefix': new_record.wh_conrcvprefix,
                    'wh_costabovealwd': new_record.wh_costabovealwd,
                    'wh_crno': new_record.wh_crno,
                    'wh_cstno': new_record.wh_cstno,
                    'wh_cstwh': new_record.wh_cstwh,
                    'wh_desc': new_record.wh_desc,
                    'wh_desc2': new_record.wh_desc2,
                    'wh_email': new_record.wh_email,
                    'wh_emailserver': new_record.wh_emailserver,
                    'wh_excludegenorder': new_record.wh_excludegenorder,
                    'wh_exposstype': new_record.wh_exposstype,
                    'wh_expsyncdate': new_record.wh_expsyncdate,
                    'wh_fjno': new_record.wh_fjno,
                    'wh_fjpfix': new_record.wh_fjpfix,
                    'wh_group': new_record.wh_group,
                    'wh_gsprncfgfpath': new_record.wh_gsprncfgfpath,
                    'wh_iedir': new_record.wh_iedir,
                    'wh_inactive': new_record.wh_inactive,
                    'wh_installationgrp': new_record.wh_installationgrp,
                    'wh_installationpartnumber': new_record.wh_installationpartnumber,
                    'wh_installationstock': new_record.wh_installationstock,
                    'wh_invreqautocrnote': new_record.wh_invreqautocrnote,
                    'wh_libarcode': new_record.wh_libarcode,
                    'wh_licstno': new_record.wh_licstno,
                    'wh_lidate': new_record.wh_lidate,
                    'wh_mainwh': new_record.wh_mainwh,
                    'wh_maxadddisc': new_record.wh_maxadddisc,
                    'wh_mgremail': new_record.wh_mgremail,
                    'wh_mpass': new_record.wh_mpass,
                    'wh_oldonline': new_record.wh_oldonline,
                    'wh_online': new_record.wh_online,
                    'wh_onlinecstdelinext': new_record.wh_onlinecstdelinext,
                    'wh_onlinecstdeliprefix': new_record.wh_onlinecstdeliprefix,
                    'wh_onlinecstinvnext': new_record.wh_onlinecstinvnext,
                    'wh_onlinecstinvprefix': new_record.wh_onlinecstinvprefix,
                    'wh_onlinecstordnext': new_record.wh_onlinecstordnext,
                    'wh_onlinecstordprefix': new_record.wh_onlinecstordprefix,
                    'wh_onlinewhouse': new_record.wh_onlinewhouse,
                    'wh_opentransferscreen': new_record.wh_opentransferscreen,
                    'wh_pdfversion': new_record.wh_pdfversion,
                    'wh_penystdate': new_record.wh_penystdate,
                    'wh_period': new_record.wh_period,
                    'wh_pmessage': new_record.wh_pmessage,
                    'wh_pmessage2': new_record.wh_pmessage2,
                    'wh_postavgcostvar': new_record.wh_postavgcostvar,
                    'wh_preprint': new_record.wh_preprint,
                    'wh_printpm': new_record.wh_printpm,
                    'wh_qtsamediscp': new_record.wh_qtsamediscp,
                    'wh_rctbatchnext': new_record.wh_rctbatchnext,
                    'wh_rctbatchprefix': new_record.wh_rctbatchprefix,
                    'wh_region': new_record.wh_region,
                    'wh_remote': new_record.wh_remote,
                    'wh_shp01': new_record.wh_shp01,
                    'wh_shp02': new_record.wh_shp02,
                    'wh_shp03': new_record.wh_shp03,
                    'wh_shp04': new_record.wh_shp04,
                    'wh_shp05': new_record.wh_shp05,
                    'wh_shp06': new_record.wh_shp06,
                    'wh_shp07': new_record.wh_shp07,
                    'wh_shp08': new_record.wh_shp08,
                    'wh_shp09': new_record.wh_shp09,
                    'wh_shp10': new_record.wh_shp10,
                    'wh_shp11': new_record.wh_shp11,
                    'wh_shp12': new_record.wh_shp12,
                    'wh_shp13': new_record.wh_shp13,
                    'wh_shp14': new_record.wh_shp14,
                    'wh_shp15': new_record.wh_shp15,
                    'wh_shp16': new_record.wh_shp16,
                    'wh_shp17': new_record.wh_shp17,
                    'wh_shp18': new_record.wh_shp18,
                    'wh_shp19': new_record.wh_shp19,
                    'wh_shp20': new_record.wh_shp20,
                    'wh_shp21': new_record.wh_shp21,
                    'wh_shp22': new_record.wh_shp22,
                    'wh_shp23': new_record.wh_shp23,
                    'wh_shp24': new_record.wh_shp24,
                    'wh_syncdate': new_record.wh_syncdate,
                    'wh_tel': new_record.wh_tel,
                    'wh_transportgrp': new_record.wh_transportgrp,
                    'wh_transportpartnumber': new_record.wh_transportpartnumber,
                    'wh_transportstock': new_record.wh_transportstock,
                    'wh_trn_autoreceive': new_record.wh_trn_autoreceive,
                    'wh_trnpicklistrequired': new_record.wh_trnpicklistrequired,
                    'wh_vatregno': new_record.wh_vatregno,
                    'wh_xmlpdffbkpath': new_record.wh_xmlpdffbkpath,
                    'wh_xmlpdffsavetodb': new_record.wh_xmlpdffsavetodb,
                    'wh_year': new_record.wh_year,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_warehouse: %s", str(e))
            return {
                "error": "An error occurred while creating the t_warehouse"
            }

    @validate_token
    @http.route("/api/t_warehouse/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_warehouse_update(self, **post):
        try:
            _logger.info("Attempting to update t_warehouse...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            wh_code = params.get('wh_code')
            if not wh_code:
                _logger.error("Missing 'wh_code' in params.")
                return {"error": "Missing required field: wh_code"}, 400  # Bad Request

            _logger.info("Searching for t_warehouse with wh_code: %s", wh_code)

            # Search for the existing record
            t_warehouse_update = request.env['t.warehouse'].sudo().search([('wh_code', '=', wh_code)], limit=1)

            if not t_warehouse_update:
                _logger.warning("t_warehouse not found for wh_code: %s", wh_code)
                return {"error": f"t_warehouse with wh_code {wh_code} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key != "wh_code" and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for wh_code: %s", wh_code)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_warehouse for wh_code: %s with data: %s", wh_code, update_vals)
            t_warehouse_update.sudo().write(update_vals)

            _logger.info("t_warehouse updated successfully for wh_code: %s", wh_code)
            return {
                "success": True,
                "message": f"t_warehouse updated for wh_code: {wh_code}",
                "data": {
                            'lang_flag': t_warehouse_update.lang_flag,
                            'lang_flag2': t_warehouse_update.lang_flag2,
                            'old_code': t_warehouse_update.old_code,
                            'user_id': t_warehouse_update.user_id,
                            'user_lmd': t_warehouse_update.user_lmd,
                            'user_lmt': t_warehouse_update.user_lmt,
                            'wh_acconline': t_warehouse_update.wh_acconline,
                            'wh_address': t_warehouse_update.wh_address,
                            'wh_address2': t_warehouse_update.wh_address2,
                            'wh_allordqty': t_warehouse_update.wh_allordqty,
                            'wh_applysdisc': t_warehouse_update.wh_applysdisc,
                            'wh_autofj': t_warehouse_update.wh_autofj,
                            'wh_batchno': t_warehouse_update.wh_batchno,
                            'wh_bpdefault': t_warehouse_update.wh_bpdefault,
                            'wh_bpname': t_warehouse_update.wh_bpname,
                            'wh_budgetfri': t_warehouse_update.wh_budgetfri,
                            'wh_budgetmon': t_warehouse_update.wh_budgetmon,
                            'wh_budgetsat': t_warehouse_update.wh_budgetsat,
                            'wh_budgetsun': t_warehouse_update.wh_budgetsun,
                            'wh_budgetthu': t_warehouse_update.wh_budgetthu,
                            'wh_budgettue': t_warehouse_update.wh_budgettue,
                            'wh_budgetwed': t_warehouse_update.wh_budgetwed,
                            'wh_cc': t_warehouse_update.wh_cc,
                            'wh_city': t_warehouse_update.wh_city,
                            'wh_cntno': t_warehouse_update.wh_cntno,
                            'wh_code': t_warehouse_update.wh_code,
                            'wh_companyname': t_warehouse_update.wh_companyname,
                            'wh_companyname2': t_warehouse_update.wh_companyname2,
                            'wh_conrcvnextno': t_warehouse_update.wh_conrcvnextno,
                            'wh_conrcvprefix': t_warehouse_update.wh_conrcvprefix,
                            'wh_costabovealwd': t_warehouse_update.wh_costabovealwd,
                            'wh_crno': t_warehouse_update.wh_crno,
                            'wh_cstno': t_warehouse_update.wh_cstno,
                            'wh_cstwh': t_warehouse_update.wh_cstwh,
                            'wh_desc': t_warehouse_update.wh_desc,
                            'wh_desc2': t_warehouse_update.wh_desc2,
                            'wh_email': t_warehouse_update.wh_email,
                            'wh_emailserver': t_warehouse_update.wh_emailserver,
                            'wh_excludegenorder': t_warehouse_update.wh_excludegenorder,
                            'wh_exposstype': t_warehouse_update.wh_exposstype,
                            'wh_expsyncdate': t_warehouse_update.wh_expsyncdate,
                            'wh_fjno': t_warehouse_update.wh_fjno,
                            'wh_fjpfix': t_warehouse_update.wh_fjpfix,
                            'wh_group': t_warehouse_update.wh_group,
                            'wh_gsprncfgfpath': t_warehouse_update.wh_gsprncfgfpath,
                            'wh_iedir': t_warehouse_update.wh_iedir,
                            'wh_inactive': t_warehouse_update.wh_inactive,
                            'wh_installationgrp': t_warehouse_update.wh_installationgrp,
                            'wh_installationpartnumber': t_warehouse_update.wh_installationpartnumber,
                            'wh_installationstock': t_warehouse_update.wh_installationstock,
                            'wh_invreqautocrnote': t_warehouse_update.wh_invreqautocrnote,
                            'wh_libarcode': t_warehouse_update.wh_libarcode,
                            'wh_licstno': t_warehouse_update.wh_licstno,
                            'wh_lidate': t_warehouse_update.wh_lidate,
                            'wh_mainwh': t_warehouse_update.wh_mainwh,
                            'wh_maxadddisc': t_warehouse_update.wh_maxadddisc,
                            'wh_mgremail': t_warehouse_update.wh_mgremail,
                            'wh_mpass': t_warehouse_update.wh_mpass,
                            'wh_oldonline': t_warehouse_update.wh_oldonline,
                            'wh_online': t_warehouse_update.wh_online,
                            'wh_onlinecstdelinext': t_warehouse_update.wh_onlinecstdelinext,
                            'wh_onlinecstdeliprefix': t_warehouse_update.wh_onlinecstdeliprefix,
                            'wh_onlinecstinvnext': t_warehouse_update.wh_onlinecstinvnext,
                            'wh_onlinecstinvprefix': t_warehouse_update.wh_onlinecstinvprefix,
                            'wh_onlinecstordnext': t_warehouse_update.wh_onlinecstordnext,
                            'wh_onlinecstordprefix': t_warehouse_update.wh_onlinecstordprefix,
                            'wh_onlinewhouse': t_warehouse_update.wh_onlinewhouse,
                            'wh_opentransferscreen': t_warehouse_update.wh_opentransferscreen,
                            'wh_pdfversion': t_warehouse_update.wh_pdfversion,
                            'wh_penystdate': t_warehouse_update.wh_penystdate,
                            'wh_period': t_warehouse_update.wh_period,
                            'wh_pmessage': t_warehouse_update.wh_pmessage,
                            'wh_pmessage2': t_warehouse_update.wh_pmessage2,
                            'wh_postavgcostvar': t_warehouse_update.wh_postavgcostvar,
                            'wh_preprint': t_warehouse_update.wh_preprint,
                            'wh_printpm': t_warehouse_update.wh_printpm,
                            'wh_qtsamediscp': t_warehouse_update.wh_qtsamediscp,
                            'wh_rctbatchnext': t_warehouse_update.wh_rctbatchnext,
                            'wh_rctbatchprefix': t_warehouse_update.wh_rctbatchprefix,
                            'wh_region': t_warehouse_update.wh_region,
                            'wh_remote': t_warehouse_update.wh_remote,
                            'wh_shp01': t_warehouse_update.wh_shp01,
                            'wh_shp02': t_warehouse_update.wh_shp02,
                            'wh_shp03': t_warehouse_update.wh_shp03,
                            'wh_shp04': t_warehouse_update.wh_shp04,
                            'wh_shp05': t_warehouse_update.wh_shp05,
                            'wh_shp06': t_warehouse_update.wh_shp06,
                            'wh_shp07': t_warehouse_update.wh_shp07,
                            'wh_shp08': t_warehouse_update.wh_shp08,
                            'wh_shp09': t_warehouse_update.wh_shp09,
                            'wh_shp10': t_warehouse_update.wh_shp10,
                            'wh_shp11': t_warehouse_update.wh_shp11,
                            'wh_shp12': t_warehouse_update.wh_shp12,
                            'wh_shp13': t_warehouse_update.wh_shp13,
                            'wh_shp14': t_warehouse_update.wh_shp14,
                            'wh_shp15': t_warehouse_update.wh_shp15,
                            'wh_shp16': t_warehouse_update.wh_shp16,
                            'wh_shp17': t_warehouse_update.wh_shp17,
                            'wh_shp18': t_warehouse_update.wh_shp18,
                            'wh_shp19': t_warehouse_update.wh_shp19,
                            'wh_shp20': t_warehouse_update.wh_shp20,
                            'wh_shp21': t_warehouse_update.wh_shp21,
                            'wh_shp22': t_warehouse_update.wh_shp22,
                            'wh_shp23': t_warehouse_update.wh_shp23,
                            'wh_shp24': t_warehouse_update.wh_shp24,
                            'wh_syncdate': t_warehouse_update.wh_syncdate,
                            'wh_tel': t_warehouse_update.wh_tel,
                            'wh_transportgrp': t_warehouse_update.wh_transportgrp,
                            'wh_transportpartnumber': t_warehouse_update.wh_transportpartnumber,
                            'wh_transportstock': t_warehouse_update.wh_transportstock,
                            'wh_trn_autoreceive': t_warehouse_update.wh_trn_autoreceive,
                            'wh_trnpicklistrequired': t_warehouse_update.wh_trnpicklistrequired,
                            'wh_vatregno': t_warehouse_update.wh_vatregno,
                            'wh_xmlpdffbkpath': t_warehouse_update.wh_xmlpdffbkpath,
                            'wh_xmlpdffsavetodb': t_warehouse_update.wh_xmlpdffsavetodb,
                            'wh_year': t_warehouse_update.wh_year,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_warehouse: %s", str(e))
            return {"error": "An error occurred while updating the t_warehouse"}, 500  # Internal Server Error


    @validate_token
    @http.route('/api/t_warehouse/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_warehouse(self, **post):
        try:
            _logger.info("Attempting to delete t_warehouse...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            wh_code = params.get('wh_code')

            # Validate wh_code
            if not wh_code or not isinstance(wh_code, str):
                _logger.error("Invalid or missing wh_code.")
                return {"error": "Invalid or missing wh_code."}, 400

            _logger.info("Deleting t_warehouse for wh_code: %s", wh_code)

            # Search for the record
            t_warehouse_obj = request.env['t.warehouse'].sudo().search([('wh_code', '=', wh_code)], limit=1)

            if not t_warehouse_obj.exists():
                _logger.warning("t_warehouse not found for wh_code: %s", wh_code)
                return {"error": f"t_warehouse with wh_code: {wh_code} not found."}, 404

            # Delete the record
            t_warehouse_obj.sudo().unlink()
            _logger.info("t_warehouse deleted successfully for wh_code: %s", wh_code)

            return {"success": True, "message": f"t_warehouse deleted for wh_code: {wh_code}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_warehouse: %s", e)
            return {"error": "An error occurred while deleting the t_warehouse"}, 500



    @validate_token
    @http.route("/api/t_productsubs/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_productsubs_search_all(self):
        try:
            _logger.info("Attempting to search for t_productsubs...")

            ps_grp = request.params.get("ps_grp")
            ps_pcode = request.params.get("ps_pcode")
            ps_psub = request.params.get("ps_psub")
           
            if ps_grp:
                t_productsubs_obj = request.env['t.productsubs'].sudo().search([('ps_grp', '=', ps_grp),('ps_pcode', '=', ps_pcode),('ps_psub', '=', ps_psub)])
            else:
                t_productsubs_obj = request.env['t.productsubs'].sudo().search([])


            # Prepare the list of t_productsubs
            t_productsubs_list = []
            for t_productsubs_line in t_productsubs_obj:
                t_productsubs_data = {
                "ps_dsirate": t_productsubs_line.ps_dsirate,
                "ps_duty": t_productsubs_line.ps_duty,
                "ps_grp": t_productsubs_line.ps_grp,
                "ps_markup": t_productsubs_line.ps_markup,
                "ps_mmgrp": t_productsubs_line.ps_mmgrp,
                "ps_pcat": t_productsubs_line.ps_pcat,
                "ps_pcode": t_productsubs_line.ps_pcode,
                "ps_prcgrp": t_productsubs_line.ps_prcgrp,
                "ps_psub": t_productsubs_line.ps_psub,
                "ps_psubgroup": t_productsubs_line.ps_psubgroup,
                "ps_sort": t_productsubs_line.ps_sort,
                "user_id": t_productsubs_line.user_id,
                "user_lmd": t_productsubs_line.user_lmd,
                "user_lmt": t_productsubs_line.user_lmt,
                }
                t_productsubs_list.append(t_productsubs_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_productsubs_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_productsubs: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_productsubs"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    

    @validate_token
    @http.route("/api/t_productsubs/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_productsubs_create(self, **post):
        try:
            _logger.info("Attempting to create t_productsubs...")

            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            ps_dsirate = params.get('ps_dsirate')
            ps_duty = params.get('ps_duty')
            ps_grp = params.get('ps_grp')
            ps_markup = params.get('ps_markup')
            ps_mmgrp = params.get('ps_mmgrp')
            ps_pcat = params.get('ps_pcat')
            ps_pcode = params.get('ps_pcode')
            ps_prcgrp = params.get('ps_prcgrp')
            ps_psub = params.get('ps_psub')
            ps_psubgroup = params.get('ps_psubgroup')
            ps_sort = params.get('ps_sort')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')
            user_lmt = params.get('user_lmt')


            existing_t_productsubs = request.env['t.productsubs'].sudo().search([('ps_grp', '=', ps_grp),('ps_pcode', '=', ps_pcode),('ps_psub', '=', ps_psub)], limit=1)
            if existing_t_productsubs:
                _logger.warning("t_productsubs already exists for ps_grp: %s", ps_grp)
                return {
                    "error": f"t_productsubs with ps_grp {ps_grp} ,ps_pcode {ps_pcode} and ps_psub {ps_psub} already exists."
                }

            ps_dsirate = params.get('ps_dsirate')
            ps_duty = params.get('ps_duty')
            ps_grp = params.get('ps_grp')
            ps_markup = params.get('ps_markup')
            ps_mmgrp = params.get('ps_mmgrp')
            ps_pcat = params.get('ps_pcat')
            ps_pcode = params.get('ps_pcode')
            ps_prcgrp = params.get('ps_prcgrp')
            ps_psub = params.get('ps_psub')
            ps_psubgroup = params.get('ps_psubgroup')
            ps_sort = params.get('ps_sort')
            user_id = params.get('user_id')
            user_lmd = params.get('user_lmd')
            user_lmt = params.get('user_lmt')           


            _logger.info("Creating t_productsubs for ps_grp: %s", ps_grp)

            new_record = request.env['t.productsubs'].sudo().create({
                    'ps_dsirate': ps_dsirate,
                    'ps_duty': ps_duty,
                    'ps_grp': ps_grp,
                    'ps_markup': ps_markup,
                    'ps_mmgrp': ps_mmgrp,
                    'ps_pcat': ps_pcat,
                    'ps_pcode': ps_pcode,
                    'ps_prcgrp': ps_prcgrp,
                    'ps_psub': ps_psub,
                    'ps_psubgroup': ps_psubgroup,
                    'ps_sort': ps_sort,
                    'user_id': user_id,
                    'user_lmd': user_lmd,
                    'user_lmt': user_lmt,
            })

            _logger.info("t_productsubs created successfully for ps_grp: %s", ps_grp)
            return {
                "success": True,
                "message": f"t_productsubs created for ps_grp: {ps_grp}",
                "data": {
                    'ps_dsirate': new_record.ps_dsirate,
                    'ps_duty': new_record.ps_duty,
                    'ps_grp': new_record.ps_grp,
                    'ps_markup': new_record.ps_markup,
                    'ps_mmgrp': new_record.ps_mmgrp,
                    'ps_pcat': new_record.ps_pcat,
                    'ps_pcode': new_record.ps_pcode,
                    'ps_prcgrp': new_record.ps_prcgrp,
                    'ps_psub': new_record.ps_psub,
                    'ps_psubgroup': new_record.ps_psubgroup,
                    'ps_sort': new_record.ps_sort,
                    'user_id': new_record.user_id,
                    'user_lmd': new_record.user_lmd,
                    'user_lmt': new_record.user_lmt,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_productsubs: %s", str(e))
            return {
                "error": "An error occurred while creating the t_productsubs"
            }

    @validate_token
    @http.route("/api/t_productsubs/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_productsubs_update(self, **post):
        try:
            _logger.info("Attempting to update t_productsubs...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            ps_grp = params.get('ps_grp')
            ps_pcode = params.get('ps_pcode')
            ps_psub = params.get('ps_psub')

            if not ps_grp:
                _logger.error("Missing 'ps_grp' in params.")
                return {"error": "Missing required field: ps_grp"}, 400  # Bad Request

            _logger.info("Searching for t_productsubs with ps_grp: %s", ps_grp)

            # Search for the existing record
            t_productsubs_update = request.env['t.productsubs'].sudo().search([('ps_grp', '=', ps_grp),('ps_pcode', '=', ps_pcode),('ps_psub', '=', ps_psub)], limit=1)

            if not t_productsubs_update:
                _logger.warning("t_productsubs not found for ps_grp: %s", ps_grp)
                return {"error": f"t_productsubs with ps_grp {ps_grp},ps_pcode {ps_pcode} and ps_psub {ps_psub} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("ps_grp","ps_pcode","ps_psub") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for ps_grp: %s", ps_grp)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_productsubs for ps_grp: %s with data: %s", ps_grp, update_vals)
            t_productsubs_update.sudo().write(update_vals)

            _logger.info("t_productsubs updated successfully for ps_grp: %s", ps_grp)
            return {
                "success": True,
                "message": f"t_productsubs updated for ps_grp: {ps_grp}",
                "data": {
                             'ps_dsirate': t_productsubs_update.ps_dsirate,
                             'ps_duty': t_productsubs_update.ps_duty,
                             'ps_grp': t_productsubs_update.ps_grp,
                             'ps_markup': t_productsubs_update.ps_markup,
                             'ps_mmgrp': t_productsubs_update.ps_mmgrp,
                             'ps_pcat': t_productsubs_update.ps_pcat,
                             'ps_pcode': t_productsubs_update.ps_pcode,
                             'ps_prcgrp': t_productsubs_update.ps_prcgrp,
                             'ps_psub': t_productsubs_update.ps_psub,
                             'ps_psubgroup': t_productsubs_update.ps_psubgroup,
                             'ps_sort': t_productsubs_update.ps_sort,
                             'user_id': t_productsubs_update.user_id,
                             'user_lmd': t_productsubs_update.user_lmd,
                             'user_lmt': t_productsubs_update.user_lmt,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_productsubs: %s", str(e))
            return {"error": "An error occurred while updating the t_productsubs"}, 500  # Internal Server Error

    @validate_token
    @http.route('/api/t_productsubs/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_productsubs(self, **post):
        try:
            _logger.info("Attempting to delete t_productsubs...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            ps_grp = params.get('ps_grp')

            # Validate ps_grp
            if not ps_grp or not isinstance(ps_grp, str):
                _logger.error("Invalid or missing ps_grp.")
                return {"error": "Invalid or missing ps_grp."}, 400

            _logger.info("Deleting t_productsubs for ps_grp: %s", ps_grp)

            # Search for the record
            t_productsubs_obj = request.env['t.productsubs'].sudo().search([('ps_grp', '=', ps_grp)], limit=1)

            if not t_productsubs_obj.exists():
                _logger.warning("t_productsubs not found for ps_grp: %s", ps_grp)
                return {"error": f"t_productsubs with ps_grp: {ps_grp} not found."}, 404

            # Delete the record
            t_productsubs_obj.sudo().unlink()
            _logger.info("t_productsubs deleted successfully for ps_grp: %s", ps_grp)

            return {"success": True, "message": f"t_productsubs deleted for ps_grp: {ps_grp}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_productsubs: %s", e)
            return {"error": "An error occurred while deleting the t_productsubs"}, 500

   

    @validate_token
    @http.route("/api/t_productsubsdescgroup/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _t_productsubsdescgroup_all(self):
        try:
            _logger.info("Attempting to search for t_productsubsdescgroup...")

            psg_grp = request.params.get("psg_grp")
            psg_pcode = request.params.get("psg_pcode")
            psg_psub = request.params.get("psg_psub")
            psg_lang = request.params.get("psg_lang")
           
            if psg_grp:
                t_productsubsdescgroup_obj = request.env['t.productsubsdescgroup'].sudo().search([('psg_grp', '=', psg_grp),('psg_pcode', '=', psg_pcode),('psg_psub', '=', psg_psub),('psg_lang', '=', psg_lang)])
            else:
                t_productsubsdescgroup_obj = request.env['t.productsubsdescgroup'].sudo().search([])


            # Prepare the list of t_productsubsdescgroup
            t_productsubsdescgroup_list = []
            for t_productsubsdescgroup_line in t_productsubsdescgroup_obj:
                t_productsubsdescgroup_data = {
                "lang_flag": t_productsubsdescgroup_line.lang_flag,
                "psg_desc": t_productsubsdescgroup_line.psg_desc,
                "psg_grp": t_productsubsdescgroup_line.psg_grp,
                "psg_lang": t_productsubsdescgroup_line.psg_lang,
                "psg_pcode": t_productsubsdescgroup_line.psg_pcode,
                "psg_psub": t_productsubsdescgroup_line.psg_psub,
                "user_lmd": t_productsubsdescgroup_line.user_lmd,
                }
                t_productsubsdescgroup_list.append(t_productsubsdescgroup_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': t_productsubsdescgroup_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for t_productsubsdescgroup: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for t_productsubsdescgroup"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )    


    @validate_token
    @http.route("/api/t_productsubsdescgroup/create", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_productsubsdescgroup_create(self, **post):
        try:
            _logger.info("Attempting to create t_productsubsdescgroup...")
            
            # Decode the payload data
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)

            # Extract parameters from the payload
            params = payload.get('params', {})
            _logger.debug("params: %s", params)
            print("params", params)

            lang_flag = params.get('lang_flag')
            psg_desc = params.get('psg_desc')
            psg_grp = params.get('psg_grp')
            psg_lang = params.get('psg_lang')
            psg_pcode = params.get('psg_pcode')
            psg_psub = params.get('psg_psub')
            user_lmd = params.get('user_lmd')


            existing_t_productsubsdescgroup = request.env['t.productsubsdescgroup'].sudo().search([('psg_grp', '=', psg_grp),('psg_pcode', '=', psg_pcode),('psg_psub', '=', psg_psub),('psg_lang', '=', psg_lang)], limit=1)
            if existing_t_productsubsdescgroup:
                _logger.warning("t_productsubsdescgroup already exists for psg_grp: %s", psg_grp)
                return {
                    "error": f"t_productsubsdescgroup with psg_grp {psg_grp},psg_pcode {psg_pcode},psg_psub {psg_psub} and psg_lang {psg_lang} already exists."
                }

            lang_flag = params.get('lang_flag')
            psg_desc = params.get('psg_desc')
            psg_grp = params.get('psg_grp')
            psg_lang = params.get('psg_lang')
            psg_pcode = params.get('psg_pcode')
            psg_psub = params.get('psg_psub')
            user_lmd = params.get('user_lmd')        


            _logger.info("Creating t_productsubsdescgroup for psg_grp: %s", psg_grp)

            new_record = request.env['t.productsubsdescgroup'].sudo().create({
                   'lang_flag': lang_flag,
                    'psg_desc': psg_desc,
                    'psg_grp': psg_grp,
                    'psg_lang': psg_lang,
                    'psg_pcode': psg_pcode,
                    'psg_psub': psg_psub,
                    'user_lmd': user_lmd,
            })

            _logger.info("t_productsubsdescgroup created successfully for psg_grp: %s", psg_grp)
            return {
                "success": True,
                "message": f"t_productsubsdescgroup created for psg_grp: {psg_grp}",
                "data": {
                    'lang_flag': new_record.lang_flag,
                    'psg_desc': new_record.psg_desc,
                    'psg_grp': new_record.psg_grp,
                    'psg_lang': new_record.psg_lang,
                    'psg_pcode': new_record.psg_pcode,
                    'psg_psub': new_record.psg_psub,
                    'user_lmd': new_record.user_lmd,
                }
            }

        except Exception as e:
            _logger.error("An error occurred while creating the t_productsubsdescgroup: %s", str(e))
            return {
                "error": "An error occurred while creating the t_productsubsdescgroup"
            }


    @validate_token
    @http.route("/api/t_productsubsdescgroup/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_productsubsdescgroup_update(self, **post):
        try:
            _logger.info("Attempting to update t_productsubsdescgroup...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            psg_grp = params.get('psg_grp')
            psg_pcode = params.get('psg_pcode')
            psg_psub = params.get('psg_psub')
            psg_lang = params.get('psg_lang')

            if not psg_grp:
                _logger.error("Missing 'psg_grp' in params.")
                return {"error": "Missing required field: psg_grp"}, 400  # Bad Request

            _logger.info("Searching for t_productsubsdescgroup with psg_grp: %s", psg_grp)

            # Search for the existing record
            t_productsubsdescgroup_update = request.env['t.productsubsdescgroup'].sudo().search([('psg_grp', '=', psg_grp),('psg_pcode', '=', psg_pcode),('psg_psub', '=', psg_psub),('psg_lang', '=', psg_lang)], limit=1)

            if not t_productsubsdescgroup_update:
                _logger.warning("t_productsubsdescgroup not found for psg_grp: %s", psg_grp)
                return {"error": f"t_productsubsdescgroup with psg_grp {psg_grp},psg_psub {psg_psub},psg_pcode {psg_pcode} and psg_lang {psg_lang} not found"}, 404  # Not Found

            # Prepare the update dictionary dynamically
            update_vals = {
                key: value for key, value in params.items() if key not in ("psg_grp","psg_pcode","psg_psub","psg_lang") and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for psg_grp: %s", psg_grp)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating t_productsubsdescgroup for psg_grp: %s with data: %s", psg_grp, update_vals)
            t_productsubsdescgroup_update.sudo().write(update_vals)

            _logger.info("t_productsubsdescgroup updated successfully for psg_grp: %s", psg_grp)
            return {
                "success": True,
                "message": f"t_productsubsdescgroup updated for psg_grp: {psg_grp}",
                "data": {
                             'lang_flag': t_productsubsdescgroup_update.lang_flag,
                             'psg_desc': t_productsubsdescgroup_update.psg_desc,
                             'psg_grp': t_productsubsdescgroup_update.psg_grp,
                             'psg_lang': t_productsubsdescgroup_update.psg_lang,
                             'psg_pcode': t_productsubsdescgroup_update.psg_pcode,
                             'psg_psub': t_productsubsdescgroup_update.psg_psub,
                             'user_lmd': t_productsubsdescgroup_update.user_lmd,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the t_productsubsdescgroup: %s", str(e))
            return {"error": "An error occurred while updating the t_productsubsdescgroup"}, 500  # Internal Server Error


    @validate_token
    @http.route('/api/t_productsubsdescgroup/delete', methods=["POST"], type="json", auth="none", csrf=False)
    def delete_t_productsubsdescgroup(self, **post):
        try:
            _logger.info("Attempting to delete t_productsubsdescgroup...")

            # Decode JSON payload manually
            try:
                payload = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.debug("Received payload data: %s", payload)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON format: %s", str(e))
                return {"error": "Invalid JSON format."}, 400  # Bad Request

            # Extract parameters safely
            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            psg_grp = params.get('psg_grp')

            # Validate psg_grp
            if not psg_grp or not isinstance(psg_grp, str):
                _logger.error("Invalid or missing psg_grp.")
                return {"error": "Invalid or missing psg_grp."}, 400

            _logger.info("Deleting t_productsubsdescgroup for psg_grp: %s", psg_grp)

            # Search for the record
            t_productsubsdescgroup_obj = request.env['t.productsubsdescgroup'].sudo().search([('psg_grp', '=', psg_grp)], limit=1)

            if not t_productsubsdescgroup_obj.exists():
                _logger.warning("t_productsubsdescgroup not found for psg_grp: %s", psg_grp)
                return {"error": f"t_productsubsdescgroup with psg_grp: {psg_grp} not found."}, 404

            # Delete the record
            t_productsubsdescgroup_obj.sudo().unlink()
            _logger.info("t_productsubsdescgroup deleted successfully for psg_grp: %s", psg_grp)

            return {"success": True, "message": f"t_productsubsdescgroup deleted for psg_grp: {psg_grp}"}, 200

        except Exception as e:
            _logger.error("An error occurred while deleting the t_productsubsdescgroup: %s", e)
            return {"error": "An error occurred while deleting the t_productsubsdescgroup"}, 500

    @validate_token
    @http.route("/api/attendance_request/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _attendance_request_all(self):
        try:
            _logger.info("Attempting to search for attendance_request...")

            employee_no = request.params.get("employee_no")
            att_date = request.params.get("att_date")

            if employee_no and att_date:
                attendance_request_obj = request.env['hr.attendance'].sudo().search(
                    [('employee_no', '=', employee_no), ('att_date', '=', att_date)])
            else:
                attendance_request_obj = request.env['hr.attendance'].sudo().search([])

            # Prepare the list of attendance_request
            attendance_request_list = []
            for attendance_request_line in attendance_request_obj:
                attendance_request_data = {
                    "employee_no": attendance_request_line.employee_no,
                    "check_in": attendance_request_line.check_in.strftime(
                        "%Y-%m-%d %H:%M:%S") if attendance_request_line.check_in else None,
                    "check_out": attendance_request_line.check_out.strftime(
                        "%Y-%m-%d %H:%M:%S") if attendance_request_line.check_out else None,
                    "att_date": attendance_request_line.att_date.strftime(
                        "%Y-%m-%d") if attendance_request_line.att_date else None,
                    "process": attendance_request_line.process,
                }
                attendance_request_list.append(attendance_request_data)

            # Prepare the response data
            response_data = {
                'status': '200',
                'response': attendance_request_list,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("An error occurred while searching for attendance_request: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for attendance_request"
            }
            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps(error_response)
            )

    @validate_token
    @http.route('/api/attendance_request/create', methods=["POST"], type="json", auth="none", csrf=False)
    def create_request_attendance(self, **post):
        try:
            _logger.info("Attempting to create attendance request...")

            # Decode and parse the JSON payload
            payload = request.httprequest.data.decode()
            payload = json.loads(payload)
            params = payload.get('params', {})
            _logger.debug("Received payload: %s", params)

            # Extract parameters with default empty strings if missing
            employee_no = params.get('E_CODE', "")
            check_in_str = params.get('EREQ_DATA2', "")
            check_out_str = params.get('EREQ_DATA3', "")
            att_date_str = params.get('EREQ_DATA1', "")
            date_str = params.get('EREQ_DATE', "")

            if not employee_no or not att_date_str:
                _logger.warning("Missing required parameters in payload")
                return {"error": "Missing required parameters."}, 400

            # Parse date and time fields, adjusting check_in and check_out by 3 hours
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S') - timedelta(
                hours=3) if check_in_str else None
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S') - timedelta(
                hours=3) if check_out_str else None
            att_date = datetime.strptime(att_date_str, '%Y-%m-%d').date()
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

            _logger.info("Creating attendance request for employee number: %s on date: %s", employee_no, att_date)

            # Search for the employee with the given employee number
            employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
            if not employee_obj:
                _logger.warning("Employee not found with employee number: %s", employee_no)
                return {"error": "Employee not found."}, 404

            # Check if an attendance record already exists for the employee on the specified date
            attendance_exists = request.env['hr.attendance'].sudo().search_count([
                ('employee_id', '=', employee_obj.id),
                ('att_date', '=', att_date)
            ]) > 0

            if attendance_exists:
                _logger.warning("Attendance record already exists for employee number: %s on date: %s", employee_no,
                                att_date)
                return {"error": "Attendance record already exists."}, 409

            # Create a new attendance record
            attendance = request.env['hr.attendance'].sudo().create({
                'employee_id': employee_obj.id,
                'check_in': check_in,
                'check_out': check_out,
                'att_date': att_date,
                'date': date  # Optional if needed
            })

            _logger.info("Attendance request created successfully for employee number: %s", employee_no)

            return {
                "success": True,
                "message": f"Attendance request created for employee: {employee_obj.name}",
                "attendance_id": attendance.id
            }, 201

        except Exception as e:
            _logger.error("An error occurred while creating the attendance: %s", e)
            return {
                "error": "An error occurred while creating the attendance."
            }, 500

        # Cielo Cloud Zatca customer Api
        
    @validate_token
    @http.route('/api/hr_leave/create', methods=["POST"], type="json", auth="none", csrf=False)
    def create_leave(self, **post):
        try:
            _logger.info("Attempting to create a leave of absence...")

            # Decode and parse the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)
            payload = json.loads(payload)

            params = payload.get('params', {})
            _logger.debug("Params: %s", params)

            # Extract the required fields
            holiday_type = params.get('holiday_type')
            employee_number = params.get('employee_number')
            holiday_code = params.get('holiday_status_id')
            request_date_from = params.get('request_date_from')
            request_date_to = params.get('request_date_to')
            number_of_days_display = params.get('number_of_days_display', 0.0)
            vacation_entitle = params.get('vacation_entitle', 0.0)
            national_holiday = params.get('national_holiday', 0.0)
            vacation_utilised = params.get('vacation_utilised', 0.0)
            paid_leave = params.get('paid_leave', 0.0)
            unpaid_leave = params.get('unpaid_leave', 0.0)
            actual_return_date = params.get('actual_return_date')
            name = params.get('name')
            # uid = params.get('uid')

            # Validate mandatory fields
            if not all([holiday_type, employee_number, holiday_code, request_date_from, request_date_to]):
                return {
                    "error": "Mandatory fields are missing (holiday_type, employee_number, holiday_status_id, request_date_from, request_date_to)."
                }, 400

            # Convert dates to `datetime.date` format
            request_date_from = datetime.strptime(request_date_from, '%Y-%m-%d').date()
            request_date_to = datetime.strptime(request_date_to, '%Y-%m-%d').date()
            actual_return_date = datetime.strptime(actual_return_date,
                                                   '%Y-%m-%d').date() if actual_return_date else None

            # Search for the employee
            employee = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_number)], limit=1)
            print("employee", employee.name)
            if not employee:
                return {
                    "error": "No employee found for the provided employee_number."
                }, 404

            # Search for the leave type
            leave_type = request.env['hr.leave.type'].sudo().search([('code', '=', holiday_code)], limit=1)
            if not leave_type:
                return {
                    "error": "No leave type found for the provided holiday_code."
                }, 404
            print("leave_type", leave_type.code, leave_type.id)

            existing_leave = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', leave_type.id),
                ('request_date_from', '=', request_date_from),
                ('request_date_to', '=', request_date_to),
            ])

            if existing_leave:
                return {
                    "error": "A leave request already exists for the provided employee and date range."
                }, 400

            # # Create the leave record
            # if not existing_leave:
            leave_obj = request.env['hr.leave']
            new_leave = leave_obj.sudo().create({
                'holiday_type': holiday_type,
                # 'employee_ids': [(6, 0, [employee.id])],
                # 'employee_ids': employee.id,
                'employee_id': employee.id,
                'employee_number': employee_number,
                'holiday_status_id': leave_type.id,
                'request_date_from': request_date_from,
                'request_date_to': request_date_to,
                'number_of_days': number_of_days_display,
                'vacation_entitle': vacation_entitle,
                'national_holiday': national_holiday,
                'vacation_utilised': vacation_utilised,
                'paid_leave': paid_leave,
                'unpaid_leave': unpaid_leave,
                'actual_return_date': actual_return_date,
                'name': name,
                'date_from': request_date_from,
                'date_to': request_date_to,


            })
            # # Avoid writing undefined fields to `employee_ids`
            if new_leave.employee_id:
                # new_leave.sudo().write({'employee_ids': [(4, new_leave.employee_id.id)], 'create_uid': 2, 'write_uid' : 2})
                new_leave.sudo().write({'state': 'draft'})

            # Approve the leave if needed
            new_leave.sudo().action_confirm()
            if new_leave.employee_id:
                # new_leave.sudo().write({'employee_ids': [(4, new_leave.employee_id.id)], 'create_uid': 2, 'write_uid' : 2})
                new_leave.sudo().write({'state': 'confirm'})
            #     new_leave.sudo().write({'state': 'validate1'})
            # new_leave.sudo().action_validate()
            # if new_leave.employee_id:
            #     # new_leave.sudo().write({'employee_ids': [(4, new_leave.employee_id.id)], 'create_uid': 2, 'write_uid' : 2})
            #     new_leave.sudo().write({'state': 'validate'})
            new_leave.sudo().action_approve()

            # Prepare response data
            response_data = {
                "message": "Leave created successfully.",
                "leave": {
                    "id": new_leave.id,
                    "holiday_type": new_leave.holiday_type,
                    "employee_ids": [emp.name for emp in new_leave.employee_ids],
                    "request_date_from": str(new_leave.request_date_from),
                    "request_date_to": str(new_leave.request_date_to),
                    "number_of_days_display": new_leave.number_of_days_display,
                    "date_from": str(new_leave.date_from),
                    "date_to": str(new_leave.date_to),
                }
            }
            return response_data, 201

        except Exception as e:
            _logger.error("An error occurred while creating the leave: %s", e)
            return {
                "error": "An error occurred while creating the leave."
            }, 500    

    # @validate_token
    # @http.route("/api/customer/create", methods=["POST"], type="json", auth="none", csrf=False)
    # def create_customer(self, **post):
    #     try:
    #         _logger.info("Attempting to create a customer...")

    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)

    #         payload = json.loads(payload)

    #         # Extract data from the payload
    #         company_type = payload.get("company_type")
    #         cust_name = payload.get("cust_name")
    #         street = payload.get("street")
    #         street2 = payload.get("street2")
    #         city = payload.get("city")
    #         zip_code = payload.get("zip")
    #         state_id = payload.get("state_id")
    #         country_id = payload.get("country_id")
    #         vat = payload.get("vat")
    #         phone = payload.get("phone")
    #         mobile = payload.get("mobile")
    #         email = payload.get("email")

    #         _logger.info("Customer name: %s, Company type: %s", cust_name, company_type)

    #         # Validate mandatory fields
    #         if not cust_name:
    #             return {
    #                 "error": "The 'name' field is mandatory."
    #             }, 400

    #         # Check for duplicate customer
    #         cust_obj = request.env['res.partner'].search([('customer', '=', True), ('ref', '=', cust_name)])

    #         if cust_obj:
    #             _logger.warning("Duplicate customer name: %s", cust_name)
    #             return {
    #                 "error": "A customer with this name already exists."
    #             }, 400

    #         # Create new customer record
    #         new_customer = request.env['res.partner'].create({
    #             'company_type': company_type if company_type else "person",  # Default to 'person' if not provided
    #             'name': cust_name,
    #             'street': street if street else "",
    #             'street2': street2 if street2 else "",
    #             'city': city if city else "",
    #             'zip': zip_code if zip_code else "",
    #             'state_id': request.env['res.country.state'].browse(state_id) if state_id else False,
    #             'country_id': request.env['res.country'].browse(country_id) if country_id else False,
    #             'vat': vat if vat else "",
    #             'phone': phone if phone else "",
    #             'mobile': mobile if mobile else "",
    #             'email': email if email else "",
    #             'customer': True,
    #         })

    #         if new_customer:
    #             _logger.info("Customer created successfully.")

    #             # Prepare response data
    #             response_data = {
    #                 "customer_id": new_customer.id,
    #                 "name": new_customer.name,
    #                 "company_type": new_customer.company_type,
    #                 "street": new_customer.street,
    #                 "street2": new_customer.street2,
    #                 "city": new_customer.city,
    #                 "zip": new_customer.zip,
    #                 "state": new_customer.state_id.name if new_customer.state_id else "",
    #                 "country": new_customer.country_id.name if new_customer.country_id else "",
    #                 "vat": new_customer.vat,
    #                 "phone": new_customer.phone,
    #                 "mobile": new_customer.mobile,
    #                 "email": new_customer.email,
    #                 "message": "Customer created successfully"
    #             }

    #             return response_data, 201

    #     except Exception as e:
    #         _logger.error("An error occurred while creating the customer: %s", e)
    #         return {
    #             "error": "An error occurred while creating the customer"
    #         }, 404

    # @validate_token
    # @http.route("/api/customer/search", methods=["GET"], type="http", auth="none", csrf=False)
    # def _customer_search_all(self):
    #     try:
    #         # Extract search parameter from the request
    #         ref = request.params.get("ref")

    #         # Determine whether to search for a specific customer or retrieve all
    #         if ref:
    #             customers = request.env['res.partner'].sudo().search([('ref', '=', ref)])
    #         else:
    #             customers = request.env['res.partner'].sudo().search(
    #                 [('partner_type', '=', 'customer')])  # Retrieve all customers

    #         # Prepare the customer list for the response
    #         customer_lst = []
    #         for customer in customers:
    #             vals = {
    #                 'customer_id': customer.id,
    #                 'name': customer.name,
    #                 'company_type': customer.company_type,
    #                 'street': customer.street,
    #                 'street2': customer.street2,
    #                 'city': customer.city,
    #                 'zip': customer.zip,
    #                 'state': customer.state_id.name if customer.state_id else '',
    #                 'country': customer.country_id.name if customer.country_id else '',
    #                 'ref': customer.ref,
    #                 'phone': customer.phone,
    #                 'mobile': customer.mobile,
    #                 'email': customer.email,
    #             }
    #             customer_lst.append(vals)

    #         response_data = {
    #             'status': '200',
    #             'response': customer_lst,
    #             'message': 'success'
    #         }

    #         return werkzeug.wrappers.Response(
    #             status=200,
    #             content_type="application/json; charset=utf-8",
    #             response=json.dumps(response_data),
    #         )

    #     except Exception as e:
    #         _logger.error("An error occurred while fetching customers: %s", e)
    #         error_response = {
    #             'status': 500,
    #             'error': "An error occurred while fetching customer data"
    #         }
    #         return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'},
    #                                      status=500)

    # @validate_token
    # @http.route("/api/customer/write", methods=["POST"], type="json", auth="none", csrf=False)
    # def write_customer(self, **post):
    #     try:
    #         _logger.info("Attempting to update a customer...")

    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)

    #         payload = json.loads(payload)

    #         cust_ref = payload.get("cust_ref")  # Change 'cust_id' to 'cust_ref'
    #         cust_name = payload.get("cust_name")
    #         cust_email = payload.get("cust_email")
    #         cust_phone = payload.get("cust_phone")
    #         cust_street = payload.get("cust_street")
    #         cust_city = payload.get("cust_city")
    #         cust_country = payload.get("cust_country")
    #         cust_zip = payload.get("cust_zip")
    #         cust_state = payload.get("cust_state")
    #         cust_is_company = payload.get("cust_is_company")
    #         cust_vat = payload.get("cust_vat")

    #         _logger.info("Customer ref: %s, New Customer Name: %s", cust_ref, cust_name)

    #         customer_obj = request.env['res.partner']
    #         customer = customer_obj.search([('ref', '=', cust_ref), ('customer', '=', True)], limit=1)

    #         if not customer.exists():
    #             _logger.error("Customer with ref %s not found.", cust_ref)
    #             return {
    #                 "error": "Customer not found"
    #             }, 404

    #         # Handle Country and State lookup if provided
    #         customer_country_id = ''
    #         customer_state_id = ''

    #         if cust_country:
    #             country_obj = request.env['res.country'].search([('name', '=', cust_country)], limit=1)
    #             if country_obj:
    #                 customer_country_id = country_obj.id
    #             else:
    #                 return {
    #                     "error": f"No country found with name: {cust_country}"
    #                 }, 404

    #         if cust_state:
    #             state_obj = request.env['res.country.state'].search(
    #                 [('name', '=', cust_state), ('country_id', '=', customer_country_id)], limit=1)
    #             if state_obj:
    #                 customer_state_id = state_obj.id
    #             else:
    #                 return {
    #                     "error": f"No state found with name: {cust_state} in the given country"
    #                 }, 404

    #         # Update customer data
    #         is_updated = customer.write({
    #             'name': cust_name if cust_name else customer.name,
    #             'email': cust_email if cust_email else customer.email,
    #             'phone': cust_phone if cust_phone else customer.phone,
    #             'street': cust_street if cust_street else customer.street,
    #             'city': cust_city if cust_city else customer.city,
    #             'zip': cust_zip if cust_zip else customer.zip,
    #             'state_id': customer_state_id if customer_state_id else customer.state_id.id,
    #             'country_id': customer_country_id if customer_country_id else customer.country_id.id,
    #             'is_company': cust_is_company if cust_is_company is not None else customer.is_company,
    #             'vat': cust_vat if cust_vat else customer.vat,
    #         })

    #         if is_updated:
    #             _logger.info("Customer updated successfully.")

    #             # Prepare response data
    #             response_data = {
    #                 "cust_ref": customer.ref,
    #                 "name": customer.name,
    #                 "email": customer.email,
    #                 "phone": customer.phone,
    #                 "street": customer.street,
    #                 "city": customer.city,
    #                 "zip": customer.zip,
    #                 "state_id": customer.state_id.name,
    #                 "country_id": customer.country_id.name,
    #                 "is_company": customer.is_company,
    #                 "vat": customer.vat,
    #                 "message": "Customer updated successfully"
    #             }
    #             return response_data, 200
    #     except Exception as e:
    #         _logger.error("An error occurred while updating the customer: %s", e)
    #         return {
    #             "error": "An error occurred while updating the customer"
    #         }, 404

    # @validate_token
    # @http.route("/api/customer/delete", methods=["DELETE"], type="json", auth="none", csrf=False)
    # def delete_customer(self, **post):
    #     try:
    #         _logger.info("Attempting to delete a customer...")

    #         # Decode and load the JSON payload
    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)
    #         payload = json.loads(payload)

    #         # Extract the customer ref from the payload
    #         cust_ref = payload.get("cust_ref")

    #         # Log customer reference
    #         _logger.info("Customer ref: %s", cust_ref)

    #         # Search for the customer using the 'ref' field
    #         customer_obj = request.env['res.partner']
    #         customer = customer_obj.search([('ref', '=', cust_ref), ('customer', '=', True)], limit=1)

    #         # Check if customer exists
    #         if not customer.exists():
    #             _logger.error("Customer with ref %s not found.", cust_ref)
    #             return {
    #                 "error": "Customer not found"
    #             }, 404

    #         # Delete the customer
    #         customer.unlink()

    #         # Log the successful deletion
    #         _logger.info("Customer with ref %s deleted successfully.", cust_ref)

    #         # Prepare the response data
    #         response_data = {
    #             "cust_ref": cust_ref,
    #             "message": "Customer deleted successfully"
    #         }
    #         return response_data, 200

    #     except Exception as e:
    #         _logger.error("An error occurred while deleting the customer: %s", e)
    #         return {
    #             "error": "An error occurred while deleting the customer"
    #         }, 500

    # Product Category Api

    @validate_token
    @http.route('/api/product/category/create', methods=["POST"], type='json', auth="none", csrf=False)
    def create_product_category(self, **post):
        try:
            _logger.info("Creating a new product category...")

            # Extract the data from the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            name = payload.get("name")  # The final category to create
            parent_path = payload.get("parent_path")  # Parent hierarchy as a string

            # Validate mandatory fields
            if not name:
                return {"error": "The 'name' field is mandatory."}, 400

            # Initialize parent_id as False (root level)
            parent_id = False

            # Process parent path if provided
            if parent_path:
                parent_names = parent_path.split('/')  # Split the path into parts
                for parent_name in parent_names:
                    # Check if the parent category already exists
                    parent_category = request.env['product.category'].search([
                        ('name', '=', parent_name),
                        ('parent_id', '=', parent_id)  # Ensure it's under the correct parent
                    ], limit=1)

                    if not parent_category:
                        # Create the parent category if it doesn't exist
                        parent_category = request.env['product.category'].create({
                            'name': parent_name,
                            'parent_id': parent_id,
                        })

                    # Update parent_id to the current category for the next iteration
                    parent_id = parent_category.id

            # Check if the final category already exists under the computed parent
            existing_category = request.env['product.category'].search([
                ('name', '=', name),
                ('parent_id', '=', parent_id)
            ], limit=1)
            if existing_category:
                _logger.warning("Category with name '%s' already exists under parent '%s'", name, parent_path)
                return {"error": "Product category with this name already exists under the specified parent."}, 400

            # Create the final category
            new_category = request.env['product.category'].create({
                'name': name,
                'parent_id': parent_id,
            })

            # Response data
            response_data = {
                "category_id": new_category.id,
                "name": new_category.name,
                "parent_id": parent_id,
                "parent_path": parent_path,
                "message": "Product category created successfully."
            }

            return response_data, 201  # HTTP Status 201 for Created

        except Exception as e:
            _logger.error("An error occurred while creating the category: %s", str(e))
            return {"error": "An error occurred while creating the category."}, 500

    @validate_token
    @http.route("/api/product/category/search", methods=["GET"], type="http", auth="none", csrf=False)
    def _product_category_search_all(self):
        try:
            # Extract search parameter from the request
            name = request.params.get("name")

            # If a category name is provided, search by category name
            if name:
                categories = request.env['product.category'].sudo().search(
                    [('name', 'ilike', name)])  # Search by category name
            else:
                categories = request.env['product.category'].sudo().search([])  # Retrieve all categories

            # Prepare the category list for the response
            category_lst = []
            for category in categories:
                vals = {
                    'category_id': category.id,
                    'name': category.name,
                    'parent_id': category.parent_id.id if category.parent_id else False,
                }
                category_lst.append(vals)

            # Prepare response data
            response_data = {
                'status': '200',
                'response': category_lst,
                'message': 'success'
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data),
            )

        except Exception as e:
            _logger.error("An error occurred while fetching product categories: %s", e)
            error_response = {
                'status': 500,
                'error': "An error occurred while fetching product category data"
            }
            return request.make_response(json.dumps(error_response), headers={'Content-Type': 'application/json'}, status=500)

    @validate_token
    @http.route('/api/attendance_request/update', methods=["POST"], type="json", auth="none", csrf=False)
    def update_request_attendance(self, **post):
        try:
            _logger.info("Attempting to update attendance request...")

            # Decode and parse the JSON payload
            payload = request.httprequest.data.decode()
            payload = json.loads(payload)
            params = payload.get('params', {})
            _logger.debug("Received payload: %s", params)

            # Extract parameters with default empty strings if missing
            employee_no = params.get('E_CODE', "")
            check_in_str = params.get('EREQ_DATA2', "")
            check_out_str = params.get('EREQ_DATA3', "")
            att_date_str = params.get('EREQ_DATA1', "")
            date_str = params.get('EREQ_DATE', "")

            if not employee_no or not att_date_str:
                _logger.warning("Missing required parameters in payload")
                return {"error": "Missing required parameters."}, 400

            # Parse date and time fields, adjusting check_in and check_out by 3 hours
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S') - timedelta(
                hours=3) if check_in_str else None
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S') - timedelta(
                hours=3) if check_out_str else None
            att_date = datetime.strptime(att_date_str, '%Y-%m-%d').date()
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

            _logger.info("Updating attendance request for employee number: %s on date: %s", employee_no, att_date)

            # Search for the employee with the given employee number
            employee_obj = request.env['hr.employee'].sudo().search([('employee_no', '=', employee_no)])
            if not employee_obj:
                _logger.warning("Employee not found with employee number: %s", employee_no)
                return {"error": "Employee not found."}, 404

            # Search for the attendance record with the given employee ID and att_date
            attendance_obj = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee_obj.id),
                ('att_date', '=', att_date)
            ])

            if attendance_obj:
                for attendance in attendance_obj:
                    _logger.debug("Current attendance record: %s", attendance)

                    # Update the attendance record
                    attendance.write({
                        'check_in': check_in if check_in else attendance.check_in,
                        'check_out': check_out if check_out else attendance.check_out,
                        "process":"no",
                    })
                    _logger.info("Attendance request updated successfully for employee number: %s", employee_no)

                return {
                    "success": True,
                    "message": f"Attendance request updated for employee: {employee_obj.name}"
                }, 200
            else:
                _logger.warning("Attendance request record not found for employee number: %s", employee_no)
                return {"error": "Attendance request record not found."}, 404

        except Exception as e:
            _logger.error("An error occurred while updating the attendance: %s", e)
            return {
                "error": "An error occurred while updating the attendance."
            }, 500


    @validate_token
    @http.route('/api/product/category/update', methods=['PUT'], type='json', auth='none', csrf=False)
    def update_product_category(self, **post):
        try:
            _logger.info("Attempting to update product category by name...")

            # Get data from the request payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            _logger.debug("Received payload data: %s", payload)

            # Extract data from the payload
            category_name = payload.get("name")
            parent_category_name = payload.get("parent_category_name")

            # Validate mandatory fields
            if not category_name:
                return {
                    "error": "The 'name' field is mandatory."
                }, 400

            # Search for the product category by name
            category = request.env['product.category'].sudo().search([('name', '=', category_name)], limit=1)

            if not category:
                return {
                    "error": f"Product category with name '{category_name}' does not exist."
                }, 404

            # Handle parent category logic
            if parent_category_name == "":  # Explicitly remove the parent if an empty string is provided
                category.write({
                    'parent_id': False,
                })
            elif parent_category_name and parent_category_name.strip():
                # Search for the parent category if a valid name is provided
                parent_category = request.env['product.category'].sudo().search(
                    [('complete_name', '=', parent_category_name.strip())], limit=1)
                if not parent_category:
                    return {
                        "error": f"Parent category '{parent_category_name}' does not exist."
                    }, 404

                # Update the parent category
                category.write({
                    'parent_id': parent_category.id,
                })

            # Update the category name
            category.write({
                'name': category_name
            })

            # Prepare response
            response_data = {
                "category_id": category.id,
                "name": category.name,
                "parent_category": category.parent_id.complete_name if category.parent_id else "",
                "message": "Product category updated successfully."
            }

            return response_data, 200

        except Exception as e:
            _logger.error("An error occurred while updating the product category: %s", e)
            return {
                "error": "An error occurred while updating the product category."
            }, 500

    # Product Api

    @validate_token
    @http.route("/api/product/create", methods=["POST"], type="json", auth="none", csrf=False)
    def create_product(self, **post):
        try:
            _logger.info("Attempting to create a product...")

            # Decode the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)

            # Extract fields from the payload
            product_name = payload.get("product_name")
            product_code = payload.get("product_code")
            product_type = payload.get("product_type")
            sale_ok = payload.get("sale_ok")
            purchase_ok = payload.get("purchase_ok")
            product_category = payload.get("product_category")
            list_price = payload.get("list_price")
            standard_price = payload.get("standard_price")

            _logger.info("Product name: %s, Product code: %s", product_name, product_code)

            # Search for an existing product.template
            product_template_obj = request.env['product.template'].search([('default_code', '=', product_code)],
                                                                          limit=1)

            if product_template_obj:
                _logger.info("Found existing product template with code: %s", product_code)
            else:
                # If product.template does not exist, create a new one
                _logger.info("No existing product template found, creating a new one...")

                # Default category to False if not provided
                category_obj = False
                if product_category:
                    category_obj = request.env['product.category'].search([('name', '=', product_category)], limit=1)

                # Validate the product type
                if product_type not in ['product', 'consu', 'service']:
                    return {
                        "error": "Invalid product type. Valid types are 'product', 'consu', and 'service'."
                    }, 400

                # Create product.template (base template)
                product_template_obj = request.env['product.template'].create({
                    'name': product_name if product_name else "",
                    'default_code': product_code if product_code else "",
                    'type': product_type if product_type else 'product',  # 'product', 'consu', 'service'
                    'sale_ok': sale_ok if sale_ok else True,  # Default to True if not provided
                    'purchase_ok': purchase_ok if purchase_ok else True,  # Default to True if not provided
                    'categ_id': category_obj.id if category_obj else False,
                    'list_price': list_price if list_price else 0.0,
                    'standard_price': standard_price if standard_price else 0.0,
                })

            _logger.info("Product template created or found successfully.")

            # Prepare response data
            response_data = {
                "product_template_id": product_template_obj.id,
                "name": product_template_obj.name,
                "default_code": product_template_obj.default_code,
                "type": product_template_obj.type,
                "sale_ok": product_template_obj.sale_ok,
                "purchase_ok": product_template_obj.purchase_ok,
                "product_category": product_template_obj.categ_id.name if product_template_obj.categ_id else "",
                "list_price": product_template_obj.list_price,
                "standard_price": product_template_obj.standard_price,
                "message": "Product template created or found successfully"
            }

            return response_data, 201

        except Exception as e:
            _logger.error("An error occurred while creating the product: %s", e)
            return {
                "error": "An error occurred while creating the product"
            }, 500

    @validate_token
    @http.route("/api/product/update", methods=["PUT"], type="json", auth="none", csrf=False)
    def update_product(self, **post):
        try:
            _logger.info("Attempting to update a product...")

            # Decode the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)

            # Extract default_code to identify the product
            default_code = payload.get("default_code")

            if not default_code:
                return {
                    "error": "The 'default_code' parameter is required to identify the product."
                }, 400

            # Search for the product by default_code
            product_template_obj = request.env['product.template'].search([('default_code', '=', default_code)],
                                                                          limit=1)

            if not product_template_obj:
                return {
                    "error": f"No product found with 'default_code': {default_code}."
                }, 404

            _logger.info("Found product template: %s", product_template_obj.name)

            # Fields to update
            update_fields = {}
            if "product_name" in payload:
                update_fields['name'] = payload.get("product_name")
            if "product_type" in payload:
                product_type = payload.get("product_type")
                if product_type not in ['product', 'consu', 'service']:
                    return {
                        "error": "Invalid product type. Valid types are 'product', 'consu', and 'service'."
                    }, 400
                update_fields['type'] = product_type
            if "sale_ok" in payload:
                update_fields['sale_ok'] = payload.get("sale_ok")
            if "purchase_ok" in payload:
                update_fields['purchase_ok'] = payload.get("purchase_ok")
            if "product_category" in payload:
                category_name = payload.get("product_category")
                category_obj = request.env['product.category'].search([('name', '=', category_name)], limit=1)
                if category_obj:
                    update_fields['categ_id'] = category_obj.id
                else:
                    return {
                        "error": f"No product category found with name '{category_name}'."
                    }, 400
            if "list_price" in payload:
                update_fields['list_price'] = payload.get("list_price")
            if "standard_price" in payload:
                update_fields['standard_price'] = payload.get("standard_price")

            # Update the product.template
            product_template_obj.write(update_fields)

            _logger.info("Product template updated successfully.")

            # Prepare response data
            response_data = {
                "product_template_id": product_template_obj.id,
                "name": product_template_obj.name,
                "default_code": product_template_obj.default_code,
                "type": product_template_obj.type,
                "sale_ok": product_template_obj.sale_ok,
                "purchase_ok": product_template_obj.purchase_ok,
                "product_category": product_template_obj.categ_id.name if product_template_obj.categ_id else "",
                "list_price": product_template_obj.list_price,
                "standard_price": product_template_obj.standard_price,
                "message": "Product template updated successfully"
            }

            return response_data, 200

        except Exception as e:
            _logger.error("An error occurred while updating the product: %s", e)
            return {
                "error": "An error occurred while updating the product"
            }, 500

    @validate_token
    @http.route("/api/products/search", methods=["GET"], type="http", auth="none", csrf=False)
    def get_all_products(self, **params):
        try:
            _logger.info("Fetching products...")

            # Extract the optional 'default_code' parameter
            default_code = params.get("default_code")

            # Search for products based on default_code if provided
            domain = []
            if default_code:
                domain = [('default_code', '=', default_code)]
                _logger.info("Filtering products by default_code: %s", default_code)

            # Fetch products
            product_templates = request.env['product.template'].search(domain)

            if not product_templates:
                response_data = {
                    "error": "No products found" + (f" with default_code '{default_code}'." if default_code else ".")
                }
                return Response(
                    json.dumps(response_data), status=404, content_type="application/json"
                )

            # Prepare response data
            products = []
            for product in product_templates:
                products.append({
                    "product_template_id": product.id,
                    "name": product.name,
                    "default_code": product.default_code,
                    "type": product.type,
                    "sale_ok": product.sale_ok,
                    "purchase_ok": product.purchase_ok,
                    "product_category": product.categ_id.name if product.categ_id else "",
                    "list_price": product.list_price,
                    "standard_price": product.standard_price
                })

            _logger.info("Products fetched successfully. Total: %d", len(products))

            # Return the response
            response_data = {
                "products": products,
                "message": f"Successfully fetched {len(products)} product(s)"
            }
            return Response(
                json.dumps(response_data), status=200, content_type="application/json"
            )

        except Exception as e:
            _logger.error("An error occurred while fetching products: %s", e)
            response_data = {
                "error": "An error occurred while fetching products"
            }
            return Response(
                json.dumps(response_data), status=500, content_type="application/json"
            )


    @validate_token
    @http.route('/api/invoices/create', methods=["POST"], type="json", auth="none", csrf=False)
    def create_invoice(self):
        """
        Create an invoice, post it to the confirmed state, with optional invoice date, tax handling by name, and discounts.
        """
        try:
            # Log incoming data
            data = request.jsonrequest
            _logger.info("Received data for invoice creation: %s", data)

            # Validate required fields
            partner_name = data.get("partner_name")
            journal_code = data.get("journal_code")
            invoice_date = data.get("invoice_date")  # Optional
            invoice_lines = data.get("invoice_lines")

            if not partner_name or not invoice_lines or not journal_code:
                return {
                    "error": "Missing required fields: 'partner_name', 'invoice_lines', or 'journal_code'."
                }, 400

            # Apply current user's company context
            current_company = request.env.company
            _logger.info(f"Creating invoice for company: {current_company.name}")

            # Search Partner by Name (restricted to current company)
            partner = request.env['res.partner'].search([('name', '=', partner_name)], limit=1)

            if not partner:
                return {
                    "error": f"Partner with name '{partner_name}' does not exist in the current company."
                }, 404

            # Search Journal by Code (restricted to current company)
            journal = request.env['account.journal'].with_context(company_id=current_company.id).search(
                [('code', '=', journal_code), ('company_id', '=', current_company.id)], limit=1
            )
            if not journal:
                return {
                    "error": f"Journal with code '{journal_code}' does not exist in the current company."
                }, 404

            # Prepare invoice lines
            line_vals = []
            invoice_line_details = []
            for line in invoice_lines:
                default_code = line.get('default_code')
                quantity = line.get('quantity', 1)
                price_unit = line.get('price_unit')
                discount = line.get('discount', 0)  # Optional Discount (default: 0)
                tax_names = line.get('tax_names', [])  # Tax Names

                # Validate product details
                if not default_code or not price_unit:
                    return {
                        "error": "Each invoice line must have 'default_code' and 'price_unit'."
                    }, 400

                # Search Product by Default Code (restricted to current company)
                product = request.env['product.product'].search([('default_code', '=', default_code)], limit=1)
                if not product:
                    return {
                        "error": f"Product with default_code '{default_code}' does not exist in the current company."
                    }, 404

                # Prepare tax_ids by searching for tax names (restricted to current company)
                taxes = request.env['account.tax'].sudo().with_context(company_id=current_company.id).search(
                    [('name', 'in', tax_names), ('company_id', '=', current_company.id)]
                )
                if tax_names and not taxes:
                    return {
                        "error": f"Taxes with names {tax_names} do not exist in the current company."
                    }, 404
                tax_ids_command = [(6, 0, taxes.ids)] if taxes else False

                # Calculate line subtotal (excluding tax)
                line_total = quantity * price_unit * (1 - discount / 100)

                # Add invoice line values (account_id auto-fetched by Odoo)
                line_vals.append((0, 0, {
                    'product_id': product.id,
                    'quantity': quantity,
                    'price_unit': price_unit,
                    'discount': discount,
                    'tax_ids': tax_ids_command,
                }))

                # Collect invoice line details to return in response
                invoice_line_details.append({
                    'product_name': product.name,
                    'quantity': quantity,
                    'price_unit': price_unit,
                    'discount': discount,
                    'tax_names': tax_names,
                    'line_total': line_total
                })

            # Create the invoice with company context
            invoice_values = {
                'move_type': 'out_invoice',  # Outgoing invoice
                'partner_id': partner.id,
                'journal_id': journal.id,
                'invoice_line_ids': line_vals,
                'company_id': current_company.id,
            }

            # Set optional invoice date
            if invoice_date:
                invoice_values['invoice_date'] = invoice_date

            # Create the invoice
            invoice = request.env['account.move'].sudo().with_context(company_id=current_company.id).create(
                invoice_values)
            _logger.info(f"Invoice created successfully: {invoice.id}")

            # Post the invoice to move it to 'Posted' state
            invoice.action_post()
            _logger.info(f"Invoice posted successfully: {invoice.id}")

            # **Call send_for_clearance function**
            try:
                invoice.send_for_clearance()
                _logger.info(f"Invoice sent for clearance successfully: {invoice.id}")
            except Exception as e:
                _logger.error(f"Error during send_for_clearance for Invoice {invoice.name}: {str(e)}")
                return {
                    "error": f"Invoice posted but clearance failed: {str(e)}"
                }, 500

            # Return the created invoice details including invoice lines
            return {
                "message": "Invoice created and posted successfully",
                "invoice_id": invoice.id,
                "invoice_name": invoice.name,
                "invoice_date": invoice.invoice_date,
                "invoice_state": invoice.state,  # Confirmed state
                "invoice_lines": invoice_line_details
            }, 201

        except Exception as e:
            _logger.error("Error creating invoice: %s", e)
            return {
                "error": "An error occurred while creating the invoice."
            }, 500
            

    @http.route('/api/view/cstclasstypedesc', type='http', auth='public', methods=['GET'], csrf=False)
    def get_cstclasstypedesc_view_data(self, **kwargs):
        try:
            # Fetch parameters from URL
            cs_code = request.params.get("cs_code")
            cs_lang = request.params.get("cs_lang")

            domain = []
            if cs_code:
                domain.append(('cs_code', '=', cs_code))
            if cs_lang:
                domain.append(('cs_lang', '=', cs_lang))

            # Search in the model (make sure this model exists)
            records = request.env['v.cstclasstypedesc'].sudo().search(domain)

            # Build response list
            result = []
            for rec in records:
                result.append({
                    "cs_name": rec.cs_name,
                    "cs_code": rec.cs_code,
                    "cs_desc": rec.cs_desc,
                    "cs_lang": rec.cs_lang,
                    "lang_flag": rec.lang_flag,
                    "user_lmd": rec.user_lmd,
                })

            # Successful response
            response_data = {
                'status': 200,
                'response': result,
                'message': 'success'
            }

            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.exception("Error fetching cstclasstypedesc data")

            error_response = {
                'status': 500,
                'error': 'Internal Server Error'
            }

            return request.make_response(
                json.dumps(error_response),
                headers=[('Content-Type', 'application/json')],
                status=500
            )    

    
    @http.route('/api/view/productlinesitems', type='http', auth='public', methods=['GET'], csrf=False)
    def get_productlinesitems_view_data(self, **kwargs):
        try:
            inv_no = request.params.get("inv_no")
            # Fetch all records first
            productlinesitems_obj = request.env['vi.product.lines.items'].sudo().search([])

            # Filter using lambda if inv_no is provided
            if inv_no:
                productlinesitems_obj = list(filter(lambda t: t.inv_no == inv_no, productlinesitems_obj))

            # if inv_no:
            #     productlinesitems_obj = request.env['vi.product.lines.items'].sudo().search([
            #         ('inv_no', '=', inv_no)
            #     ])
            # else:
            #     productlinesitems_obj = request.env['vi.product.lines.items'].sudo().search([])

            productlinesitems_list = []
            for t in productlinesitems_obj:
                productlinesitems_list.append({
                    "id": t.id,
                    "inv_whouse": t.inv_whouse,
                    "inv_no": t.inv_no,
                    "inv_slno": t.inv_slno,
                    "inv_subslno": t.inv_subslno,
                    "inv_orcr": t.inv_orcr,
                    "inv_orcpno": t.inv_orcpno,
                    "inv_pno": t.inv_pno,
                    "inv_pact": t.inv_pact,
                    "inv_nonstock": t.inv_nonstock,
                    "inv_desc": t.inv_desc,
                    "inv_stock": t.inv_stock,
                    "inv_group": t.inv_group,
                    "inv_part": t.inv_part,
                    "inv_det1": t.inv_det1,
                    "inv_det2": t.inv_det2,
                    "inv_qtyreq": t.inv_qtyreq,
                    "inv_qtyiss": t.inv_qtyiss,
                    "inv_cost": t.inv_cost,
                    "inv_price": t.inv_price,
                    "inv_disc": t.inv_disc,
                    "inv_pdisc": t.inv_pdisc,
                    "inv_vatcode": t.inv_vatcode,
                    "inv_vat": t.inv_vat,
                    "inv_ret": t.inv_ret,
                    "inv_pidref": t.inv_pidref,
                    "inv_xface": t.inv_xface,
                    "inv_fleetsale": t.inv_fleetsale,
                    "inv_trnslno": t.inv_trnslno,
                    "inv_trnsubslno": t.inv_trnsubslno,
                    "inv_subtrntype": t.inv_subtrntype,
                    "inv_subtrnref": t.inv_subtrnref,
                    "inv_cstordflag": t.inv_cstordflag,
                    "inv_sourcewh": t.inv_sourcewh,
                    "inv_discp": t.inv_discp,
                    "inv_reqgroup": t.inv_reqgroup,
                    "inv_reqstock": t.inv_reqstock,
                    "inv_reqpart": t.inv_reqpart,
                    "inv_reqdesc": t.inv_reqdesc,
                    "inv_orgreqqty": t.inv_orgreqqty,
                    "inv_cstpriceflg": t.inv_cstpriceflg,
                    "inv_isswhouse": t.inv_isswhouse,
                    "inv_export": t.inv_export,
                    "inv_wqty": t.inv_wqty,
                    "inv_dsiamt": t.inv_dsiamt,
                    "inv_salcat": t.inv_salcat,
                    "inv_vatexp": t.inv_vatexp,
                    "inv_promodisc": t.inv_promodisc,
                    "inv_promomsg1": t.inv_promomsg1,
                    "inv_promomsg2": t.inv_promomsg2,
                    "inv_promomsg3": t.inv_promomsg3,
                    "inv_campaign": t.inv_campaign,
                    "inv_campaignref": t.inv_campaignref,
                    "inv_autocrnoteval": t.inv_autocrnoteval,
                    "inv_autocrnotestatus": t.inv_autocrnotestatus,
                })

            response_data = {
                'status': 200,
                'response': productlinesitems_list,
                'message': 'success'
            }

            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error("An error occurred while searching for productlinesitems: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for productlinesitems"
            }

            return request.make_response(
                json.dumps(error_response),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

            
    @http.route('/api/view/productlinesserviceitems', type='http', auth='public', methods=['GET'], csrf=False)
    def get_productlinesserviceitems_view_data(self, **kwargs):
        try:
            inv_no = request.params.get("inv_no")

            if inv_no:
                productlinesitems_obj = request.env['vi.product.lines.serviceitems'].sudo().search([
                    ('inv_no', '=', inv_no)
                ])
            else:
                productlinesitems_obj = request.env['vi.product.lines.serviceitems'].sudo().search([])

            productlinesitems_list = []
            for t in productlinesitems_obj:
                productlinesitems_list.append({
                    "id": t.id,
                    "inv_whouse": t.inv_whouse,
                    "inv_no": t.inv_no,
                    "inv_slno": t.inv_slno,
                    "inv_subslno": t.inv_subslno,
                    "inv_orcr": t.inv_orcr,
                    "inv_orcpno": t.inv_orcpno,
                    "inv_pno": t.inv_pno,
                    "inv_pact": t.inv_pact,
                    "inv_nonstock": t.inv_nonstock,
                    "inv_desc": t.inv_desc,
                    "inv_stock": t.inv_stock,
                    "inv_group": t.inv_group,
                    "inv_part": t.inv_part,
                    "inv_det1": t.inv_det1,
                    "inv_det2": t.inv_det2,
                    "inv_qtyreq": t.inv_qtyreq,
                    "inv_qtyiss": t.inv_qtyiss,
                    "inv_cost": t.inv_cost,
                    "inv_price": t.inv_price,
                    "inv_disc": t.inv_disc,
                    "inv_pdisc": t.inv_pdisc,
                    "inv_vatcode": t.inv_vatcode,
                    "inv_ret": t.inv_ret,
                    "inv_pidref": t.inv_pidref,
                    "inv_xface": t.inv_xface,
                    "inv_fleetsale": t.inv_fleetsale,
                    "inv_trnslno": t.inv_trnslno,
                    "inv_trnsubslno": t.inv_trnsubslno,
                    "inv_subtrntype": t.inv_subtrntype,
                    "inv_subtrnref": t.inv_subtrnref,
                    "inv_cstordflag": t.inv_cstordflag,
                    "inv_sourcewh": t.inv_sourcewh,
                    "inv_discp": t.inv_discp,
                    "inv_reqgroup": t.inv_reqgroup,
                    "inv_reqstock": t.inv_reqstock,
                    "inv_reqpart": t.inv_reqpart,
                    "inv_reqdesc": t.inv_reqdesc,
                    "inv_orgreqqty": t.inv_orgreqqty,
                    "inv_cstpriceflg": t.inv_cstpriceflg,
                    "inv_isswhouse": t.inv_isswhouse,
                    "inv_export": t.inv_export,
                    "inv_wqty": t.inv_wqty,
                    "inv_dsiamt": t.inv_dsiamt,
                    "inv_salcat": t.inv_salcat,
                    "inv_vatexp": t.inv_vatexp,
                    "inv_promodisc": t.inv_promodisc,
                    "inv_promomsg1": t.inv_promomsg1,
                    "inv_promomsg2": t.inv_promomsg2,
                    "inv_promomsg3": t.inv_promomsg3,
                    "inv_campaign": t.inv_campaign,
                    "inv_campaignref": t.inv_campaignref,
                    "inv_autocrnoteval": t.inv_autocrnoteval,
                    "inv_autocrnotestatus": t.inv_autocrnotestatus,
                })

            response_data = {
                'status': 200,
                'response': productlinesitems_list,
                'message': 'success'
            }

            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error("An error occurred while searching for productlinesitems: %s", e)

            error_response = {
                'status': 500,
                'error': "An error occurred while searching for productlinesitems"
            }

            return request.make_response(
                json.dumps(error_response),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    
    @http.route('/api/view/producttaskitems', type='http',auth='none', methods=['GET'], csrf=False)
    def get_producttaskitems_view_data(self, **kwargs):
        try:
            _logger.info("Attempting to search for producttaskitems producttaskitems...")
            inv_manualinvno = request.params.get("inv_manualinvno")
            inv_whouse = request.params.get("inv_whouse")

            if inv_manualinvno:
                producttaskitems_obj = request.env['vi.product.task'].sudo().search([
                    ('inv_manualinvno', '=', inv_manualinvno), ('inv_whouse', '=', inv_whouse)
                ])
            else:
                producttaskitems_obj = request.env['vi.product.task'].sudo().search([])

            producttaskitems_list = []
            for t in producttaskitems_obj:
                producttaskitems_list.append({               
                    "id": t.id,
                    "inv_whouse": t.inv_whouse,
                    "location_code": t.location_code,
                    "number_next": t.number_next,
                    "work_center_id": t.work_center_id,
                    "inv_no": t.inv_no,
                    'inv_date': t.inv_date,
                    "inv_batch": t.inv_batch,
                    "inv_sman": t.inv_sman,
                    "inv_xface": t.inv_xface,
                    "inv_cstno": t.inv_cstno,
                    "inv_cstname": t.inv_cstname,
                    "inv_cstadd": t.inv_cstadd,
                    "inv_cstref": t.inv_cstref,
                    "inv_comm": t.inv_comm,
                    "inv_mop": t.inv_mop,
                    "inv_ccard": t.inv_ccard,
                    "inv_ccardno": t.inv_ccardno,
                    "inv_ccardedt": t.inv_ccardedt,
                    "inv_deposit": t.inv_deposit,
                    "inv_period": t.inv_period,
                    "inv_status": t.inv_status,
                    "user_id": t.user_id,
                    'user_lmd': t.user_lmd,
                    "inv_headdisc": t.inv_headdisc,
                    "inv_headdiscper": t.inv_headdiscper,
                    "inv_cashamt": t.inv_cashamt,
                    "inv_creditamt": t.inv_creditamt,
                    "inv_ccardamt": t.inv_ccardamt,
                    "inv_deladd": t.inv_deladd,
                    "user_lmt": t.user_lmt,
                    "inv_manualinvno": t.inv_manualinvno,
                    "inv_print": t.inv_print,
                    "inv_total": t.inv_total,
                    "inv_discuserid": t.inv_discuserid,
                    "inv_manualdoc": t.inv_manualdoc,
                    "inv_franchise": t.inv_franchise,
                    "inv_pickinglist": t.inv_pickinglist,
                    "inv_ccmachine": t.inv_ccmachine,
                    "inv_bankcode": t.inv_bankcode,
                    "inv_vatupdstatus": t.inv_vatupdstatus,
                    "inv_cstvatreg": t.inv_cstvatreg,
                    "inv_reqapprove": t.inv_reqapprove,
                    "inv_crtuserid": t.inv_crtuserid,
                    "inv_crtuserlmd": t.inv_crtuserlmd,
                    "inv_crtuserlmt": t.inv_crtuserlmt,
                    "inv_apruserid": t.inv_apruserid,
                    "inv_apruserlmd": t.inv_apruserlmd,
                    "inv_apruserlmt": t.inv_apruserlmt,
                    "inv_aprcrlmtuserid": t.inv_aprcrlmtuserid,
                    "inv_aprcrlmtuserlmd": t.inv_aprcrlmtuserlmd,
                    "inv_aprcrlmtuserlmt": t.inv_aprcrlmtuserlmt,
                    "inv_onlineorderref": t.inv_onlineorderref,
                    "inv_onlineprofileid": t.inv_onlineprofileid,
                    "inv_smmodule": t.inv_smmodule,
                    "inv_reqautocrnote": t.inv_reqautocrnote,
                    "inv_cstidtype": t.inv_cstidtype,
                    "inv_streetname": t.inv_streetname,
                    "inv_buildno": t.inv_buildno,
                    "inv_addno": t.inv_addno,
                    "inv_pobox": t.inv_pobox,
                    "inv_district": t.inv_district,
                    "inv_region": t.inv_region,
                    "inv_nearby": t.inv_nearby,
                    "inv_city": t.inv_city,
                    "inv_countrycode": t.inv_countrycode,
                    "inv_countryname": t.inv_countryname,
                    "inv_vatgroup": t.inv_vatgroup,
                    "inv_uuid": t.inv_uuid,
                    "inv_cstid": t.inv_cstid,
                    "inv_cstmobile": t.inv_cstmobile,
                    "inv_cstemail": t.inv_cstemail,
                    "inv_add2": t.inv_add2,
                    "inv_idno": t.inv_idno,
                    "mode_of_payment": t.mode_of_payment,
                    "mode_of_payment_balance_amount": t.mode_of_payment_balance_amount,
                    "contract_id": t.contract_id,
                    "inspection_charges_amount": t.inspection_charges_amount,
                    "balance_paid": t.balance_paid,
                    "final_balance_amount": t.final_balance_amount,
                    "inv_detrowscount": t.inv_detrowscount,
                })

            return request.make_response(
                json.dumps({
                    'status': 200,
                    'response': producttaskitems_list,
                    'message': 'success'
                }),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.exception("Error in /api/view/producttaskitems: %s", e)
            return request.make_response(
                json.dumps({'status': 500, 'error': 'Internal server error'}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    # @http.route('/api/view/producttaskitems', type='http',auth='none', methods=['GET'], csrf=False)
    # def get_producttaskitems_view_data(self, **kwargs):
    #     try:
    #         _logger.info("Attempting to search for producttaskitems producttaskitems...")
    #         inv_manualinvno = request.params.get("inv_manualinvno")
    #         inv_whouse = request.params.get("inv_whouse")
    #
    #         if inv_manualinvno:
    #             producttaskitems_obj = request.env['vi.product.task'].sudo().search([
    #                 ('inv_manualinvno', '=', inv_manualinvno), ('inv_whouse', '=', inv_whouse)
    #             ])
    #         else:
    #             producttaskitems_obj = request.env['vi.product.task'].sudo().search([])
    #
    #         producttaskitems_list = []
    #         for t in producttaskitems_obj:
    #             producttaskitems_list.append({               
    #                 "id": t.id,
    #                 "inv_whouse": t.inv_whouse,
    #                 "location_code": t.location_code,
    #                 "number_next": t.number_next,
    #                 "work_center_id": t.work_center_id,
    #                 "inv_no": t.inv_no,
    #                 'inv_date': t.inv_date,
    #                 "inv_batch": t.inv_batch,
    #                 "inv_sman": t.inv_sman,
    #                 "inv_xface": t.inv_xface,
    #                 "inv_cstno": t.inv_cstno,
    #                 "inv_cstname": t.inv_cstname,
    #                 "inv_cstadd": t.inv_cstadd,
    #                 "inv_cstref": t.inv_cstref,
    #                 "inv_comm": t.inv_comm,
    #                 "inv_mop": t.inv_mop,
    #                 "inv_ccard": t.inv_ccard,
    #                 "inv_ccardno": t.inv_ccardno,
    #                 "inv_ccardedt": t.inv_ccardedt,
    #                 "inv_deposit": t.inv_deposit,
    #                 "inv_period": t.inv_period,
    #                 "inv_status": t.inv_status,
    #                 "user_id": t.user_id,
    #                 'user_lmd': t.user_lmd,
    #                 "inv_headdisc": t.inv_headdisc,
    #                 "inv_headdiscper": t.inv_headdiscper,
    #                 "inv_cashamt": t.inv_cashamt,
    #                 "inv_creditamt": t.inv_creditamt,
    #                 "inv_ccardamt": t.inv_ccardamt,
    #                 "inv_deladd": t.inv_deladd,
    #                 "user_lmt": t.user_lmt,
    #                 "inv_manualinvno": t.inv_manualinvno,
    #                 "inv_print": t.inv_print,
    #                 "inv_total": t.inv_total,
    #                 "inv_discuserid": t.inv_discuserid,
    #                 "inv_manualdoc": t.inv_manualdoc,
    #                 "inv_franchise": t.inv_franchise,
    #                 "inv_pickinglist": t.inv_pickinglist,
    #                 "inv_ccmachine": t.inv_ccmachine,
    #                 "inv_bankcode": t.inv_bankcode,
    #                 "inv_vatupdstatus": t.inv_vatupdstatus,
    #                 "inv_cstvatreg": t.inv_cstvatreg,
    #                 "inv_reqapprove": t.inv_reqapprove,
    #                 "inv_crtuserid": t.inv_crtuserid,
    #                 "inv_crtuserlmd": t.inv_crtuserlmd,
    #                 "inv_crtuserlmt": t.inv_crtuserlmt,
    #                 "inv_apruserid": t.inv_apruserid,
    #                 "inv_apruserlmd": t.inv_apruserlmd,
    #                 "inv_apruserlmt": t.inv_apruserlmt,
    #                 "inv_aprcrlmtuserid": t.inv_aprcrlmtuserid,
    #                 "inv_aprcrlmtuserlmd": t.inv_aprcrlmtuserlmd,
    #                 "inv_aprcrlmtuserlmt": t.inv_aprcrlmtuserlmt,
    #                 "inv_onlineorderref": t.inv_onlineorderref,
    #                 "inv_onlineprofileid": t.inv_onlineprofileid,
    #                 "inv_smmodule": t.inv_smmodule,
    #                 "inv_reqautocrnote": t.inv_reqautocrnote,
    #                 "inv_cstidtype": t.inv_cstidtype,
    #                 "inv_streetname": t.inv_streetname,
    #                 "inv_buildno": t.inv_buildno,
    #                 "inv_addno": t.inv_addno,
    #                 "inv_pobox": t.inv_pobox,
    #                 "inv_district": t.inv_district,
    #                 "inv_region": t.inv_region,
    #                 "inv_nearby": t.inv_nearby,
    #                 "inv_city": t.inv_city,
    #                 "inv_countrycode": t.inv_countrycode,
    #                 "inv_countryname": t.inv_countryname,
    #                 "inv_vatgroup": t.inv_vatgroup,
    #                 "inv_uuid": t.inv_uuid,
    #                 "inv_cstid": t.inv_cstid,
    #                 "inv_cstmobile": t.inv_cstmobile,
    #                 "inv_cstemail": t.inv_cstemail,
    #                 "inv_add2": t.inv_add2,
    #                 "inv_idno": t.inv_idno,
    #                 "mode_of_payment": t.mode_of_payment,
    #                 "mode_of_payment_balance_amount": t.mode_of_payment_balance_amount,
    #                 "contract_id": t.contract_id,
    #                 "inspection_charges_amount": t.inspection_charges_amount,
    #                 "balance_paid": t.balance_paid,
    #                 "final_balance_amount": t.final_balance_amount,
    #             })
    #
    #         return request.make_response(
    #             json.dumps({
    #                 'status': 200,
    #                 'response': producttaskitems_list,
    #                 'message': 'success'
    #             }),
    #             headers=[('Content-Type', 'application/json')]
    #         )
    #
    #     except Exception as e:
    #         _logger.exception("Error in /api/view/producttaskitems: %s", e)
    #         return request.make_response(
    #             json.dumps({'status': 500, 'error': 'Internal server error'}),
    #             headers=[('Content-Type', 'application/json')],
    #             status=500
    #         )
    #

          
    @validate_token
    @http.route("/api/project_task/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_project_tasks_update(self, **post):
        try:
            _logger.info("Attempting to update project_task...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            name = params.get('name')
            id = params.get('id')
            
            if not name:
                _logger.error("Missing 'name' in params.")
                return {"error": "Missing required field: name"}, 400  # Bad Request

            _logger.info("Searching for project_task with name: %s", name)

            # Search for the existing record
            project_task_update = request.env['project.task'].sudo().search([('name', '=', name),('id', '=', id)], limit=1)

            if not project_task_update:
                _logger.warning("project_task not found for name: %s", name)
                return {"error": f"project_task with name {name} and id {id} not found"}, 404  # Not Found

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ("name", "id") and value is not None
            }
            
            if not update_vals:
                _logger.warning("No valid fields to update for name: %s", name)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating project_task for name: %s with data: %s", name, update_vals)
            project_task_update.sudo().write(update_vals)

            _logger.info("project_task updated successfully for name: %s", name)
            return {
                "success": True,
                "message": f"project_task updated for name: {name}",
                "data": {
                    'id': project_task_update.id,
                    'name': project_task_update.name,
                    'export_bool': project_task_update.export_bool,
                    'invoice_no': project_task_update.invoice_no,
                    'access_token': project_task_update.access_token,
                    'state': project_task_update.state,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the project_task: %s", str(e))
            return {"error": "An error occurred while updating the project_task"}, 500  # Internal Server Error



    @http.route('/api/view/projecttaskrefname', type='http',auth='none', methods=['GET'], csrf=False)
    def get_projecttaskrefname_view_data(self, **kwargs):
        try:
            _logger.info("Attempting to search for projecttaskrefname...")
            contract_id = request.params.get("contract_id")

            if contract_id:
                projecttaskrefname_obj = request.env['vi.project.task.refname'].sudo().search([
                    ('contract_id', '=', contract_id)])
            else:
                projecttaskrefname_obj = request.env['vi.project.task.refname'].sudo().search([])

            projecttaskrefname_list = []
            for t in projecttaskrefname_obj:
                projecttaskrefname_list.append({               
                    "id": t.id,
                    "contract_id": t.contract_id,
                    "ref": t.ref,                       
                })

            return request.make_response(
                json.dumps({
                    'status': 200,
                    'response': projecttaskrefname_list,
                    'message': 'success'
                }),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.exception("Error in /api/view/projecttaskrefname: %s", e)
            return request.make_response(
                json.dumps({'status': 500, 'error': 'Internal server error'}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    # @validate_token
    # @http.route("/api/ir_sequence_date_range/update", methods=["POST"], type="json", auth="none", csrf=False)
    # def _ir_sequence_date_range_update(self, **post):
    #     try:
    #         _logger.info("Attempting to update ir_sequence...")
    #
    #         # Decode and log the payload
    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)
    #
    #         # Parse the JSON payload
    #         payload = json.loads(payload)
    #         params = payload.get('params', {})
    #
    #         if not params:
    #             _logger.error("Missing 'params' key in request body.")
    #             return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request
    #
    #         _logger.debug("Extracted params: %s", params)
    #
    #         # Extract required field
    #         work_center_id = params.get('work_center_id')
    #         location_code = params.get('location_code')
    #         date_from = params.get('date_from')
    #         date_to = params.get('date_to')
    #
    #         if not work_center_id:
    #             _logger.error("Missing 'work_center_id' in params.")
    #             return {"error": "Missing required field: work_center_id"}, 400  # Bad Request
    #
    #         _logger.info("Searching for ir_sequence with work_center_id: %s", work_center_id)
    #
    #         # Search for the existing record
    #         sequence_update = request.env['ir.sequence.date_range'].sudo().search(
    #             [('work_center_id', '=', work_center_id), ('location_code', '=', location_code),
    #              ('date_from', '=', date_from), ('date_to', '=', date_to)], limit=1)
    #
    #         if not sequence_update:
    #             _logger.warning("ir_sequence not found for work_center_id: %s", work_center_id)
    #             return {
    #                 "error": f"ir_sequence with work_center_id {work_center_id} and location_code {location_code} not found"}, 404  # Not Found
    #
    #         update_vals = {
    #             key: value
    #             for key, value in params.items()
    #             if key not in ("work_center_id", "location_code", "date_from", "date_to") and value is not None
    #         }
    #
    #         if not update_vals:
    #             _logger.warning("No valid fields to update for work_center_id: %s", work_center_id)
    #             return {"error": "No valid fields provided for update"}, 400  # Bad Request
    #
    #         # Perform the update
    #         _logger.info("Updating ir_sequence for work_center_id: %s with data: %s", work_center_id, update_vals)
    #         sequence_update.sudo().write(update_vals)
    #
    #         _logger.info("ir_sequence updated successfully for work_center_id: %s", work_center_id)
    #         return {
    #             "success": True,
    #             "message": f"ir_sequence updated for work_center_id: {work_center_id}",
    #             "data": {
    #                 'id': sequence_update.id,
    #                 'work_center_id': sequence_update.work_center_id.id,
    #                 'location_code': sequence_update.location_code,
    #                 'number_next': sequence_update.number_next,
    #                 'date_from': sequence_update.date_from,
    #                 'date_to': sequence_update.date_to,
    #             }
    #         }, 200
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while updating the ir_sequence: %s", str(e))
    #         return {"error": "An error occurred while updating the ir_sequence"}, 500  # Internal Server Error

    @validate_token
    @http.route("/api/ir_sequence_date_range/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _ir_sequence_date_range_update(self, **post):
        try:
            _logger.info("Attempting to update ir.sequence.date_range...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get("params", {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400

            _logger.debug("Extracted params: %s", params)

            # Extract required fields
            work_center_id = params.get("work_center_id")
            location_code = params.get("location_code")
            date_from = params.get("date_from")
            date_to = params.get("date_to")

            # Validation for required fields
            missing_fields = []
            if not work_center_id:
                missing_fields.append("work_center_id")
            if not location_code:
                missing_fields.append("location_code")
            if not date_from or not date_to:
                missing_fields.append("date_from/date_to")

            if missing_fields:
                _logger.error("Missing required fields: %s", ", ".join(missing_fields))
                return {"error": f"Missing required fields: {', '.join(missing_fields)}"}, 400

            _logger.info(
                "Searching for ir.sequence.date_range with work_center_id=%s, location_code=%s, date_from=%s, date_to=%s",
                work_center_id, location_code, date_from, date_to
            )

            # Search for the existing date range record
            sequence_update = request.env["ir.sequence.date_range"].sudo().search([
                ("work_center_id.name", "=", work_center_id),
                ("location_code", "=", location_code),
                ("date_from", "=", date_from),
                ("date_to", "=", date_to),
            ], limit=1)

            # If no record found
            if not sequence_update:
                _logger.warning(
                    "ir.sequence.date_range not found for work_center_id=%s and location_code=%s",
                    work_center_id, location_code
                )
                return {
                    "error": f"ir_sequence.date_range with work_center_id '{work_center_id}' and location_code '{location_code}' not found"
                }, 404

            # Validation: Allow update only if name == 'Job Card' and both flags are True
            seq = sequence_update.sequence_id
            if not (seq.name == 'Job Card' and seq.use_date_range and seq.use_location_wise):
                _logger.warning(
                    "Update not allowed: ir_sequence '%s' does not meet date range and location-wise requirements.",
                    seq.name
                )
                return {
                    "error": f"ir_sequence '{seq.name}' uses date range or location-wise configuration incorrectly. Update not allowed."
                }, 404

            # Prepare update values (exclude identifiers)
            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ("work_center_id", "location_code", "date_from", "date_to")
                   and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for work_center_id=%s", work_center_id)
                return {"error": "No valid fields provided for update"}, 400

            # Perform the update
            _logger.info(
                "Updating ir.sequence.date_range for work_center_id=%s with data=%s",
                work_center_id, update_vals
            )
            sequence_update.sudo().write(update_vals)

            _logger.info("ir.sequence.date_range updated successfully for work_center_id=%s", work_center_id)

            return {
                "success": True,
                "message": f"ir_sequence.date_range updated successfully for work_center_id {work_center_id}",
                "data": {
                    "id": sequence_update.id,
                    "work_center_id": sequence_update.work_center_id.id,
                    "location_code": sequence_update.location_code,
                    "number_next": sequence_update.number_next,
                    "date_from": str(sequence_update.date_from),
                    "date_to": str(sequence_update.date_to),
                },
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating ir_sequence.date_range: %s", str(e))
            return {
                "error": f"An error occurred while updating the ir_sequence.date_range: {str(e)}"
            }, 500

    @validate_token
    @http.route("/api/ir_sequence_update/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _ir_sequence_update(self, **post):
        try:
            _logger.info("Attempting to update ir_sequence_update...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            name = params.get('name')
            if not name:
                _logger.error("Missing 'name' in params.")
                return {"error": "Missing required field: name"}, 400

            _logger.info("Searching for ir_sequence with name: %s", name)

            # Search for the existing record
            sequence_update = request.env['ir.sequence'].sudo().search([('name', '=', name)], limit=1)

            if not sequence_update:
                _logger.warning("ir_sequence not found for name: %s", name)
                return {"error": f"ir_sequence with name '{name}' not found"}, 404

            if sequence_update.use_date_range or sequence_update.use_location_wise:
                _logger.warning(
                    "ir_sequence '%s' uses date range or location-wise configuration. Update not allowed.",
                    name
                )
                return {
                    "error": f"Update not allowed: ir_sequence '{name}' uses date range or location-wise configuration."
                }, 404

            # Prepare update values
            update_vals = {
                key: value for key, value in params.items()
                if key != "name" and value is not None
            }

            if not update_vals:
                _logger.warning("No valid fields to update for name: %s", name)
                return {"error": "No valid fields provided for update"}, 400

            # Perform the update
            _logger.info("Updating ir_sequence for name: %s with data: %s", name, update_vals)
            sequence_update.sudo().write(update_vals)

            _logger.info("ir_sequence updated successfully for name: %s", name)

            return {
                "success": True,
                "message": f"ir_sequence '{name}' updated successfully.",
                "data": {
                    "id": sequence_update.id,
                    "name": sequence_update.name,
                    "number_next": sequence_update.number_next,
                    "prefix": sequence_update.prefix,
                    "number_increment": sequence_update.number_increment
                },
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the ir_sequence: %s", str(e))
            return {
                "error": f"An error occurred while updating the ir_sequence: {str(e)}"
            }, 500

    @http.route('/api/view/producttaskitemsnamelist', type='http', auth='none', methods=['GET'], csrf=False)
    def get_producttaskitems_namelist_view_data(self, **kwargs):
        try:

            producttaskitems_namelist_obj = request.env['vi.product.task.namelist'].sudo().search([])

            producttaskitems_name_list = []
            for t in producttaskitems_namelist_obj:
                producttaskitems_name_list.append({
                    "inv_whouse": t.inv_whouse,
                    "inv_manualinvno": t.inv_manualinvno,
                })

            return request.make_response(
                json.dumps({
                    'status': 200,
                    'response': producttaskitems_name_list,
                    'message': 'success'
                }),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.exception("Error in /api/view/producttaskitemsnamelist: %s", e)
            return request.make_response(
                json.dumps({'status': 500, 'error': 'Internal server error'}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
            
    @validate_token
    @http.route('/api/view/irsequencenext', type='http', auth='public', methods=['GET'], csrf=False)
    def get_irsequence_view_data(self, **kwargs):
        try:
            # Fetch parameters from URL
            name = request.params.get("name")          
 
            domain = []
            if name:
                domain.append(('name', '=', name))
           
            # Search in the model (make sure this model exists)
            records = request.env['ir.sequence'].sudo().search(domain)
 
            # Build response list
            result = []
            for rec in records:
                result.append({
                    "prefix": rec.prefix,
                    "number_next": rec.number_next,
                    "name": rec.name,
                })
 
            # Successful response
            response_data = {
                'status': 200,
                'response': result,
                'message': 'success'
            }
 
            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )
 
        except Exception as e:
            _logger.exception("Error fetching ir_sequence data")
 
            error_response = {
                'status': 500,
                'error': 'Internal Server Error'
            }
 
            return request.make_response(
                json.dumps(error_response),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

            
    @validate_token
    @http.route('/api/product_template/update',methods=["POST"],type="json",auth="none",csrf=False)
    def update_product_template_price(self, **post):
        try:
            _logger.info("Attempting to update product price from VI_STOCK")
            # Parse request payload
            payload = request.httprequest.data.decode()
            payload = json.loads(payload)
            params = payload.get('params', {})

            stk_part = params.get('stk_part')
            unit_cost = params.get('unit_cost')

            # Validation
            if not stk_part or unit_cost is None:
                return {
                    "success": False,
                    "error": "stk_part and unit_cost are required"
                }, 400

            # Find product variant by default_code
            product_variant = request.env['product.product'].sudo().search(
                [('default_code', '=', stk_part)],
                limit=1
            )

            if not product_variant:
                _logger.warning("Product not found for stk_part: %s", stk_part)
                return {
                    "success": False,
                    "error": f"Product not found for stk_part {stk_part}"
                }, 404

            product_template = product_variant.product_tmpl_id

            # Update list_price
            product_template.write({
                'list_price': unit_cost
            })

            _logger.info(
                "Updated list_price for stk_part %s to %s",
                stk_part, unit_cost
            )

            return {
                "success": True,
                "stk_part": stk_part,
                "product_template_id": product_template.id,
                "list_price": unit_cost,
                "message": "Product price updated successfully"
            }, 200

        except Exception as e:
            _logger.exception("Error while updating product price")
            return {
                "success": False,
                "error": str(e)
            }, 500
    
    @validate_token
    @http.route("/api/ir_property/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_ir_property_update(self, **post):
        try:
            _logger.info("Attempting to update ir_property...")

            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            payload = json.loads(payload)
            params = payload.get("params", {})

            if not params:
                return {"error": "Invalid request: 'params' key is missing"}, 400

            product_id = params.get("product_id")
            if not product_id:
                return {"error": "Missing required field: product_id"}, 400

            _logger.info("Searching ir_property for product_id: %s", product_id)

            ir_property = request.env["ir.property"].sudo().search([
                ("res_id", "in", [
                    f"product.template,{product_id}",
                    f"product.product,{product_id}",
                    f"res.partner,{product_id}",
                    f"res.users,{product_id}",
                ])
            ], limit=1)

            if not ir_property:
                return {
                    "success": False,
                    "error": f"ir_property not found for product_id {product_id}"
                }, 404

            # Allowed value fields only
            allowed_fields = {
                "value_integer",
                "value_reference",                
                "value_text",
                "value_float",
                "value_binary",
            }

            update_vals = {
                k: v for k, v in params.items()
                if k in allowed_fields and v is not None
            }

            if not update_vals:
                return {"error": "No valid fields provided for update"}, 400

            _logger.info(
                "Updating ir_property ID %s with values %s",
                ir_property.id,
                update_vals
            )

            ir_property.write(update_vals)

            return {
                "success": True,
                "message": "ir_property updated successfully",
                "data": {
                    "id": ir_property.id,
                    "res_id": ir_property.res_id,
                    "type": ir_property.type,
                    "value_integer": ir_property.value_integer,
                    "value_reference": ir_property.value_reference,
                    "value_text": ir_property.value_text,
                    "value_float": ir_property.value_float,
                    "value_binary": ir_property.value_binary,
                }
            }, 200

        except Exception as e:
            _logger.exception("Error updating ir_property")
            return {"error": str(e)}, 500
    
    # @validate_token
    # @http.route("/api/ir_property/update", methods=["POST"], type="json", auth="none", csrf=False)
    # def _t_ir_property_update(self, **post):
    #     try:
    #         _logger.info("Attempting to update ir_property...")
    #
    #         # Decode and log the payload
    #         payload = request.httprequest.data.decode()
    #         _logger.debug("Received payload data: %s", payload)
    #
    #         # Parse the JSON payload
    #         payload = json.loads(payload)
    #         params = payload.get('params', {})
    #
    #         if not params:
    #             _logger.error("Missing 'params' key in request body.")
    #             return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request
    #
    #         _logger.debug("Extracted params: %s", params)
    #
    #         # Extract required field
    #         name = params.get('name')
    #         product_id = params.get('product_id')            
    #
    #
    #         if not name or not product_id:
    #             _logger.error("Missing 'name' in params.")
    #             return {"error": "Missing required field: name"}, 400  # Bad Request
    #
    #         _logger.info("Searching for ir_property with name: %s", name)
    #
    #         res_id = f"product.product,{product_id}"
    #
    #         # Search for the existing record
    #         ir_property_update = request.env['ir.property'].sudo().search([('name', '=', name),('res_id', '=', res_id)], limit=1)
    #
    #         if not ir_property_update:
    #             _logger.warning("ir_property not found for name: %s", name)
    #             return {"success": False,"error": f"ir_property with name '{name}' and product {product_id}"}, 404  # Not Found
    #
    #          # Only allow valid value fields
    #         allowed_fields = {
    #             "value_float",
    #             "value_integer",
    #             "value_char",
    #             "value_boolean",
    #             "value_reference",
    #         }
    #
    #         update_vals = {
    #             k: v for k, v in params.items()
    #             if k in allowed_fields and v is not None
    #         }
    #
    #         if not update_vals:
    #             _logger.warning("No valid fields to update for name: %s", name)
    #             return {"error": "No valid fields provided for update"}, 400  # Bad Request
    #
    #         # Perform the update
    #         _logger.info("Updating ir_property for name: %s with data: %s", name, update_vals)
    #         ir_property_update.sudo().write(update_vals)
    #
    #         _logger.info("ir_property updated successfully for name: %s", name)
    #         return {
    #             "success": True,
    #             "message": f"ir_property updated for name: {name}",
    #             "data": {
    #                 'id': ir_property_update.id,
    #                 'name': ir_property_update.name,
    #                 'value_float': ir_property_update.value_float,
    #                 'res_id': ir_property_update.res_id,
    #                 'value_float': ir_property_update.value_float,
    #                 'type': ir_property_update.type,
    #             }
    #         }, 200
    #
    #     except Exception as e:
    #         _logger.error("An error occurred while updating the ir_property: %s", str(e))
    #         return {"error": "An error occurred while updating the ir_property"}, 500    

    @validate_token
    @http.route("/api/project_task_qrcode/update", methods=["POST"], type="json", auth="none", csrf=False)
    def _t_project_task_qrcode_update(self, **post):
        try:
            _logger.info("Attempting to update project_task_qrcode...")

            # Decode and log the payload
            payload = request.httprequest.data.decode()
            _logger.debug("Received payload data: %s", payload)

            # Parse the JSON payload
            payload = json.loads(payload)
            params = payload.get('params', {})

            if not params:
                _logger.error("Missing 'params' key in request body.")
                return {"error": "Invalid request: 'params' key is missing"}, 400  # Bad Request

            _logger.debug("Extracted params: %s", params)

            # Extract required field
            name = params.get('name')
            
            
            if not name:
                _logger.error("Missing 'name' in params.")
                return {"error": "Missing required field: name"}, 400  # Bad Request

            _logger.info("Searching for project_task_qrcode with name: %s", name)

            # Search for the existing record
            project_task_qrcode_update = request.env['project.task'].sudo().search([('name', '=', name)], limit=1)

            if not project_task_qrcode_update:
                _logger.warning("project_task_qrcode not found for name: %s", name)
                return {"error": f"project_task_qrcode with name {name} and id {id} not found"}, 404  # Not Found

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ("name") and value is not None
            }
            
            if not update_vals:
                _logger.warning("No valid fields to update for name: %s", name)
                return {"error": "No valid fields provided for update"}, 400  # Bad Request

            # Perform the update
            _logger.info("Updating project_task_qrcode for name: %s with data: %s", name, update_vals)
            project_task_qrcode_update.sudo().write(update_vals)

            _logger.info("project_task_qrcode updated successfully for name: %s", name)
            return {
                "success": True,
                "message": f"project_task_qrcode updated for name: {name}",
                "data": {
                    'id': project_task_qrcode_update.id,
                    'name': project_task_qrcode_update.name,
                    'export_bool': project_task_qrcode_update.export_bool,
                    'invoice_no': project_task_qrcode_update.invoice_no,
                    'inv_pvs_xmlhas': project_task_qrcode_update.inv_pvs_xmlhas,
                    'inv_xmlhas': project_task_qrcode_update.inv_xmlhas,
                    'inv_qrcode_has': project_task_qrcode_update.inv_qrcode_has,
                }
            }, 200

        except Exception as e:
            _logger.error("An error occurred while updating the project_task_qrcode: %s", str(e))
            return {"error": "An error occurred while updating the project_task_qrcode"}, 500  # Internal Server Error    
    
    @validate_token
    @http.route("/api/stock_warehouse/create", methods=["POST"], type="json", auth="none", csrf=False)
    def warehouse_create(self, **post):
        try:
            _logger.info("Attempting to create/update stock.warehouse...")

            # Decode payload
            payload = request.httprequest.data.decode()
            payload = json.loads(payload)

            params = payload.get('params', {})
            _logger.debug("params: %s", params)

            # Extract fields
            wh_code = params.get('wh_code')
            wh_desc = params.get('wh_desc')

            if not wh_code:
                return {"error": "wh_code is required"}

            # Check existing warehouse
            warehouse = request.env['stock.warehouse'].sudo().search([
                ('code', '=', wh_code)
            ], limit=1)

            # ✅ UPDATE
            if warehouse:
                _logger.info("Updating warehouse: %s", wh_code)

                warehouse.write({
                    'name': wh_desc
                })

                return {
                    "success": True,
                    "message": f"Warehouse updated: {wh_code}"
                }

            # ✅ CREATE (Odoo handles locations automatically)
            _logger.info("Creating warehouse: %s", wh_code)

            new_wh = request.env['stock.warehouse'].sudo().create({
                'code': wh_code,
                'name': wh_desc,
                'company_id': 1
            })

            return {
                "success": True,
                "message": f"Warehouse created: {wh_code}",
                "data": {
                    "id": new_wh.id,
                    "code": new_wh.code,
                    "name": new_wh.name
                }
            }

        except Exception as e:
            _logger.error("Error in warehouse_create: %s", str(e))
            return {
                "error": str(e)
            }
    
    
    @validate_token
    @http.route("/api/project_task/search", methods=["GET"], type="http", auth="none", csrf=False)
    def search_project_tasks(self, **kwargs):
        try:
            _logger.info("Searching project_task by name (GET)...")

            
            name = kwargs.get('name')

            if not name:
                return request.make_response(
                    json.dumps({"error": "Missing required parameter: name"}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # 🔍 Search using 'ilike' (partial match)
            tasks = request.env['project.task'].sudo().search([
                ('name', 'ilike', name)
            ])

            if not tasks:
                return request.make_response(
                    json.dumps({"error": f"No project_task found for name: {name}"}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # 📦 Prepare response
            result = []
            for task in tasks:
                result.append({
                    'id': task.id,
                    'name': task.name,
                    'export_bool': task.export_bool,
                    'invoice_no': task.invoice_no,
                    'access_token': task.access_token,
                    'state': task.state,
                })

            return request.make_response(
                json.dumps({
                    "success": True,
                    "count": len(result),
                    "data": result
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            _logger.error("Error in search API: %s", str(e))
            return request.make_response(
                json.dumps({"error": "Internal Server Error"}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @validate_token        
    @http.route('/api/transactionheader/upsert', type='json', auth='public', methods=['POST'], csrf=False)
    def upsert_transaction_header(self, **kwargs):
        try:
            # ✅ Safe JSON handling (fix for your error)
            data = request.jsonrequest if hasattr(request, 'jsonrequest') else request.params

            print("DATA RECEIVED:", data)

            # ✅ Mandatory validation
            if not data.get('trnh_whouse') or not data.get('trnh_no'):
                return {
                    "status": "error",
                    "message": "trnh_whouse and trnh_no are mandatory"
                }

            model = request.env['transaction.header'].sudo()

            # ✅ Unique key
            domain = [
                ('trnh_type', '=', data.get('trnh_type')),
                ('trnh_whouse', '=', data.get('trnh_whouse')),
                ('trnh_no', '=', data.get('trnh_no')),
            ]

            record = model.search(domain, limit=1)

            # ✅ SAFE FIELD MAPPING (avoid system fields)
            vals = {
                key: data[key]
                for key in data
                if key in model._fields and key not in ['id', 'create_date', 'write_date']
            }

            if record:
                record.write(vals)
                return {
                    "status": "updated",
                    "id": record.id
                }
            else:
                new_rec = model.create(vals)
                return {
                    "status": "created",
                    "id": new_rec.id
                }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @validate_token
    @http.route('/api/transactiondetails/upsert', type='json', auth='public', methods=['POST'], csrf=False)
    def upsert_transaction(self, **kwargs):

        data = request.jsonrequest if hasattr(request, 'jsonrequest') else request.params

        # ✅ Mandatory validation
        if not data.get('trnd_whouse') or not data.get('trnd_no'):
            return {
                "status": "error",
                "message": "trnd_whouse and trnd_no are mandatory"
            }

        model = request.env['transaction.details'].sudo()

        # ✅ Unique key (supports multiple lines)
        domain = [
            ('trnd_type', '=', data.get('trnd_type')),
            ('trnd_whouse', '=', data.get('trnd_whouse')),
            ('trnd_no', '=', data.get('trnd_no')),
            ('trnd_slno', '=', data.get('trnd_slno', 0)),
        ]

        record = model.search(domain, limit=1)

        # ✅ AUTO MAP ALL FIELDS (no need to write 80 fields manually)
        fields_list = model._fields.keys()

        vals = {}
        for field in fields_list:
            if field in data:
                vals[field] = data.get(field)

        if record:
            record.write(vals)
            return {
                "status": "updated",
                "id": record.id
            }
        else:
            new_rec = model.create(vals)
            return {
                "status": "created",
                "id": new_rec.id
               } 
    
    
    @validate_token
    @http.route(
        '/api/customerloyaltypointshistory/get',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False
    )
    def get_customer_loyalty_points_history(self, **kwargs):

        model = request.env['vi.customer.loyalty.points.history'].sudo()

        domain = []

        if kwargs.get('clph_cstid'):
            domain.append(('clph_cstid', '=', kwargs.get('clph_cstid')))

        if kwargs.get('clph_docnumber'):
            domain.append(('clph_docnumber', '=', kwargs.get('clph_docnumber')))

        records = model.search(domain)

        result = []

        for rec in records:
            result.append({
                "id": rec.id,
                "clph_cstid": rec.clph_cstid,
                "clph_cstcode": rec.clph_cstcode,
                "clph_date": str(rec.clph_date) if rec.clph_date else "",
                "clph_doctype": rec.clph_doctype,
                "clph_docnumber": rec.clph_docnumber,
                "clph_type": rec.clph_type,
                "clph_whouse": rec.clph_whouse,
                "clph_regpoints": rec.clph_regpoints,
                "clph_bonuspoints": rec.clph_bonuspoints,
                "clph_totalpoints": rec.clph_totalpoints,
                "clph_note": rec.clph_note,
                "clph_uid": rec.clph_uid,
                "clph_datetime": str(rec.clph_datetime) if rec.clph_datetime else "",
                "clph_adjtype": rec.clph_adjtype,
                "clph_reasoncode": rec.clph_reasoncode,
                "clph_promoref": rec.clph_promoref,
                "clph_lmd": str(rec.clph_lmd) if rec.clph_lmd else "",
                "clph_export": rec.clph_export
            })

        response_data = {
            "status": "success",
            "count": len(result),
            "data": result
        }

        return Response(
            json.dumps(response_data),
            content_type='application/json;charset=utf-8',
            status=200
        )
        

    @validate_token
    @http.route(
        '/api/customerloyaltypointshistory/updateexport',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def update_export_flag(self, **kwargs):

        raw_data = request.httprequest.data

        data = {}

        if raw_data:
            data = json.loads(raw_data.decode('utf-8'))

        clph_cstid = data.get('clph_cstid')
        clph_cstcode = data.get('clph_cstcode')
        clph_docnumber = data.get('clph_docnumber')
        clph_export = data.get('clph_export', 'Y')

        # ✅ Validation
        if not clph_cstid or not clph_cstcode or not clph_docnumber:

            return Response(
                json.dumps({
                    "status": "error",
                    "message": "clph_cstid, clph_cstcode and clph_docnumber are mandatory"
                }),
                content_type='application/json',
                status=400
            )

        # ✅ Direct SQL Update
        request.env.cr.execute("""
            UPDATE customer_loyalty_points_history
            SET clph_export = %s
            WHERE clph_cstid = %s
              AND clph_cstcode = %s
              AND clph_docnumber = %s
        """, (
            clph_export,
            int(clph_cstid),
            clph_cstcode,
            clph_docnumber
        ))

        updated_count = request.env.cr.rowcount

        request.env.cr.commit()

        return Response(
            json.dumps({
                "status": "success",
                "message": "Export flag updated successfully",
                "updated_count": updated_count
            }),
            content_type='application/json',
            status=200
        )
                    
    
    
    @validate_token
    @http.route("/api/t_products/search", methods=["GET"], type="http", auth="none", csrf=False)
    def t_products_search(self, **kwargs):
        try:
            _logger.info("Searching t_products records")

            p_grp = request.params.get("p_grp")
            p_code = request.params.get("p_code")

            domain = []

            if p_grp:
                domain.append(('p_grp', '=', p_grp))

            if p_code:
                domain.append(('p_code', '=', p_code))

            records = request.env['t.products'].sudo().search(domain)

            result = []

            for rec in records:
                result.append({
                    "p_grp": rec.p_grp,
                    "p_code": rec.p_code,
                    "p_markup": rec.p_markup,
                    "p_pcat": rec.p_pcat,
                    "p_duty": rec.p_duty,
                    "user_id": rec.user_id,
                    "user_lmd": str(rec.user_lmd) if rec.user_lmd else "",
                    "user_lmt": rec.user_lmt,
                    "p_desc": rec.p_desc,
                    "p_desc2": rec.p_desc2,
                    "lang_flag": rec.lang_flag,
                    "lang_flag2": rec.lang_flag2,
                    "p_sort": rec.p_sort,
                    "p_loyaltyreq": rec.p_loyaltyreq,
                    "p_mpcode": rec.p_mpcode,
                })

            response_data = {
                "status": 200,
                "response": result,
                "message": "success"
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("Error searching t_products: %s", str(e))

            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps({
                    "status": 500,
                    "error": "Error while searching t_products"
                })
            )

    # =====================================================
    # CREATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_products/create", methods=["POST"], type="json", auth="none", csrf=False)
    def t_products_create(self, **post):
        try:
            _logger.info("Creating t_products")

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            p_grp = params.get("p_grp")
            p_code = params.get("p_code")

            existing = request.env['t.products'].sudo().search([
                ('p_grp', '=', p_grp),
                ('p_code', '=', p_code)
            ], limit=1)

            if existing:
                return {
                    "success": False,
                    "message": f"Record already exists for p_grp {p_grp} and p_code {p_code}"
                }

            new_record = request.env['t.products'].sudo().create({
                'p_grp': params.get('p_grp'),
                'p_code': params.get('p_code'),
                'p_markup': params.get('p_markup'),
                'p_pcat': params.get('p_pcat'),
                'p_duty': params.get('p_duty'),
                'user_id': params.get('user_id'),
                'user_lmd': params.get('user_lmd'),
                'user_lmt': params.get('user_lmt'),
                'p_desc': params.get('p_desc'),
                'p_desc2': params.get('p_desc2'),
                'lang_flag': params.get('lang_flag'),
                'lang_flag2': params.get('lang_flag2'),
                'p_sort': params.get('p_sort'),
                'p_loyaltyreq': params.get('p_loyaltyreq'),
                'p_mpcode': params.get('p_mpcode'),
            })

            return {
                "success": True,
                "message": "t_products created successfully",
                "data": {
                    "id": new_record.id,
                    "p_grp": new_record.p_grp,
                    "p_code": new_record.p_code
                }
            }

        except Exception as e:
            _logger.error("Error creating t_products: %s", str(e))

            return {
                "success": False,
                "message": "Error while creating t_products"
            }

    # =====================================================
    # UPDATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_products/update", methods=["POST"], type="json", auth="none", csrf=False)
    def t_products_update(self, **post):
        try:
            _logger.info("Updating t_products")

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            p_grp = params.get("p_grp")
            p_code = params.get("p_code")

            record = request.env['t.products'].sudo().search([
                ('p_grp', '=', p_grp),
                ('p_code', '=', p_code)
            ], limit=1)

            if not record:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ('p_grp', 'p_code') and value is not None
            }

            if update_vals:
                record.sudo().write(update_vals)

            return {
                "success": True,
                "message": "t_products updated successfully",
                "data": {
                    "p_grp": record.p_grp,
                    "p_code": record.p_code
                }
            }

        except Exception as e:
            _logger.error("Error updating t_products: %s", str(e))

            return {
                "success": False,
                "message": "Error while updating t_products"
            }

    # =====================================================
    # DELETE API
    # =====================================================
    @validate_token
    @http.route("/api/t_products/delete", methods=["POST"], type="json", auth="none", csrf=False)
    def t_products_delete(self, **post):
        try:
            _logger.info("Deleting t_products")

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            p_grp = params.get("p_grp")
            p_code = params.get("p_code")

            record = request.env['t.products'].sudo().search([
                ('p_grp', '=', p_grp),
                ('p_code', '=', p_code)
            ], limit=1)

            if not record:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            record.sudo().unlink()

            return {
                "success": True,
                "message": f"t_products deleted for p_code {p_code}"
            }

        except Exception as e:
            _logger.error("Error deleting t_products: %s", str(e))

            return {
                "success": False,
                "message": "Error while deleting t_products"
            }

    # =====================================================
    # SEARCH API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproducts/search", methods=["GET"], type="http", auth="none", csrf=False)
    def t_mainproducts_search(self, **kwargs):
        try:

            mp_grp = request.params.get("mp_grp")
            mp_code = request.params.get("mp_code")

            domain = []

            if mp_grp:
                domain.append(('mp_grp', '=', mp_grp))

            if mp_code:
                domain.append(('mp_code', '=', mp_code))

            records = request.env['t.mainproducts'].sudo().search(domain)

            result = []

            for rec in records:
                result.append({
                    "mp_grp": rec.mp_grp,
                    "mp_code": rec.mp_code,
                    "mp_sort": rec.mp_sort,
                    "user_id": rec.user_id,
                    "user_lmd": str(rec.user_lmd) if rec.user_lmd else "",
                    "user_lmt": rec.user_lmt,
                })

            response_data = {
                "status": 200,
                "response": result,
                "message": "success"
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error(str(e))

            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps({
                    "status": 500,
                    "error": str(e)
                })
            )

    # =====================================================
    # CREATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproducts/create", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproducts_create(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")

            existing = request.env['t.mainproducts'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code)
            ], limit=1)

            if existing:
                return {
                    "success": False,
                    "message": "Record already exists"
                }

            rec = request.env['t.mainproducts'].sudo().create({
                'mp_grp': params.get('mp_grp'),
                'mp_code': params.get('mp_code'),
                'mp_sort': params.get('mp_sort'),
                'user_id': params.get('user_id'),
                'user_lmd': params.get('user_lmd'),
                'user_lmt': params.get('user_lmt'),
            })

            return {
                "success": True,
                "message": "Created Successfully",
                "data": {
                    "id": rec.id,
                    "mp_grp": rec.mp_grp,
                    "mp_code": rec.mp_code
                }
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

    # =====================================================
    # UPDATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproducts/update", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproducts_update(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")

            rec = request.env['t.mainproducts'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code)
            ], limit=1)

            if not rec:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ('mp_grp', 'mp_code') and value is not None
            }

            rec.sudo().write(update_vals)

            return {
                "success": True,
                "message": "Updated Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

    # =====================================================
    # DELETE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproducts/delete", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproducts_delete(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")

            rec = request.env['t.mainproducts'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code)
            ], limit=1)

            if not rec:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            rec.sudo().unlink()

            return {
                "success": True,
                "message": "Deleted Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }


    # =====================================================
    # SEARCH API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproductsdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def t_mainproductsdesc_search(self, **kwargs):
        try:

            mp_grp = request.params.get("mp_grp")
            mp_code = request.params.get("mp_code")
            mp_lang = request.params.get("mp_lang")

            domain = []

            if mp_grp:
                domain.append(('mp_grp', '=', mp_grp))

            if mp_code:
                domain.append(('mp_code', '=', mp_code))

            if mp_lang:
                domain.append(('mp_lang', '=', int(mp_lang)))

            records = request.env['t.mainproductsdesc'].sudo().search(domain)

            result = []

            for rec in records:
                result.append({
                    "mp_grp": rec.mp_grp,
                    "mp_code": rec.mp_code,
                    "mp_lang": rec.mp_lang,
                    "mp_desc": rec.mp_desc,
                    "lang_flag": rec.lang_flag,
                })

            response_data = {
                "status": 200,
                "response": result,
                "message": "success"
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error(str(e))

            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps({
                    "status": 500,
                    "error": str(e)
                })
            )

    # =====================================================
    # CREATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproductsdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproductsdesc_create(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")
            mp_lang = params.get("mp_lang")

            existing = request.env['t.mainproductsdesc'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code),
                ('mp_lang', '=', mp_lang)
            ], limit=1)

            if existing:
                return {
                    "success": False,
                    "message": "Record already exists"
                }

            rec = request.env['t.mainproductsdesc'].sudo().create({
                'mp_grp': params.get('mp_grp'),
                'mp_code': params.get('mp_code'),
                'mp_lang': params.get('mp_lang'),
                'mp_desc': params.get('mp_desc'),
                'lang_flag': params.get('lang_flag'),
            })

            return {
                "success": True,
                "message": "Created Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

    # =====================================================
    # UPDATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproductsdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproductsdesc_update(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")
            mp_lang = params.get("mp_lang")

            rec = request.env['t.mainproductsdesc'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code),
                ('mp_lang', '=', mp_lang)
            ], limit=1)

            if not rec:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ('mp_grp', 'mp_code', 'mp_lang') and value is not None
            }

            rec.sudo().write(update_vals)

            return {
                "success": True,
                "message": "Updated Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

    # =====================================================
    # DELETE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproductsdesc/delete", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproductsdesc_delete(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")
            mp_lang = params.get("mp_lang")

            rec = request.env['t.mainproductsdesc'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code),
                ('mp_lang', '=', mp_lang)
            ], limit=1)

            if not rec:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            rec.sudo().unlink()

            return {
                "success": True,
                "message": "Deleted Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

            
    @http.route(
        '/api/view/accountmove',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False
        )
    def get_account_move_view_data(self, **kwargs):

        try:
            inv_no = request.params.get("inv_no")

            domain = []

            if inv_no:
                domain.append(('inv_no', '=', inv_no))

            account_move_obj = request.env['vi.account.move'].sudo().search(domain)

            account_move_list = []

            for t in account_move_obj:
                account_move_list.append({

                    "id": t.id,
                    "inv_whouse": t.inv_whouse or "",
                    "inv_no": t.inv_no or "",
                    "inv_date": str(t.inv_date) if t.inv_date else "",
                    "inv_batch": t.inv_batch or "",
                    "inv_sman": t.inv_sman or "",
                    "inv_xface": t.inv_xface or 0,
                    "inv_cstno": t.inv_cstno or "",
                    "inv_cstname": t.inv_cstname or "",
                    "inv_cstadd": t.inv_cstadd or "",
                    "inv_cstref": t.inv_cstref or "",
                    "inv_comm": t.inv_comm or "",
                    "inv_mop": t.inv_mop or 0,

                    "inv_ccard": t.inv_ccard or "",
                    "inv_ccardno": t.inv_ccardno or "",
                    "inv_ccardedt": t.inv_ccardedt or "",

                    "inv_deposit": t.inv_deposit or 0,
                    "inv_period": t.inv_period or "",
                    "inv_status": t.inv_status or "",

                    "user_id": t.user_id or 0,
                    "user_lmd": t.user_lmd or "",

                    "inv_headdisc": t.inv_headdisc or 0,
                    "inv_headdiscper": t.inv_headdiscper or 0,

                    "inv_cashamt": t.inv_cashamt or 0,
                    "inv_creditamt": t.inv_creditamt or 0,
                    "inv_ccardamt": t.inv_ccardamt or 0,

                    "inv_deladd": t.inv_deladd or "",

                    "user_lmt": t.user_lmt or "",

                    "inv_manualinvno": t.inv_manualinvno or "",

                    "inv_print": t.inv_print or "",

                    "inv_total": t.inv_total or 0,

                    "inv_discuserid": t.inv_discuserid or "",

                    "inv_manualdoc": t.inv_manualdoc or "",

                    "inv_franchise": t.inv_franchise or "",

                    "inv_pickinglist": t.inv_pickinglist or "",

                    "inv_ccmachine": t.inv_ccmachine or "",

                    "inv_bankcode": t.inv_bankcode or "",

                    "inv_vatupdstatus": t.inv_vatupdstatus or 0,

                    "inv_cstvatreg": t.inv_cstvatreg or "",

                    "inv_reqapprove": t.inv_reqapprove or "",

                    "inv_crtuserid": t.inv_crtuserid or "",
                    "inv_crtuserlmd": t.inv_crtuserlmd or "",
                    "inv_crtuserlmt": t.inv_crtuserlmt or "",

                    "inv_apruserid": t.inv_apruserid or "",
                    "inv_apruserlmd": t.inv_apruserlmd or "",
                    "inv_apruserlmt": t.inv_apruserlmt or "",

                    "inv_aprcrlmtuserid": t.inv_aprcrlmtuserid or "",
                    "inv_aprcrlmtuserlmd": t.inv_aprcrlmtuserlmd or "",
                    "inv_aprcrlmtuserlmt": t.inv_aprcrlmtuserlmt or "",

                    "inv_onlineorderref": t.inv_onlineorderref or "",

                    "inv_onlineprofileid": t.inv_onlineprofileid or "",

                    "inv_smmodule": t.inv_smmodule or "",

                    "inv_reqautocrnote": t.inv_reqautocrnote or "",

                    "inv_cstidtype": t.inv_cstidtype or "",

                    "inv_streetname": t.inv_streetname or "",

                    "inv_buildno": t.inv_buildno or "",

                    "inv_addno": t.inv_addno or "",

                    "inv_pobox": t.inv_pobox or "",

                    "inv_district": t.inv_district or "",

                    "inv_region": t.inv_region or "",

                    "inv_nearby": t.inv_nearby or "",

                    "inv_city": t.inv_city or "",

                    "inv_countrycode": t.inv_countrycode or "",

                    "inv_countryname": t.inv_countryname or "",

                    "inv_vatgroup": t.inv_vatgroup or "",

                    "inv_cstid": t.inv_cstid or "",

                    "inv_cstmobile": t.inv_cstmobile or "",

                    "inv_cstemail": t.inv_cstemail or "",

                    "inv_add1": t.inv_add1 or "",

                    "inv_add2": t.inv_add2 or "",

                    "inv_idno": t.inv_idno or ""

                })

            response_data = {
                'status': 200,
                'response': account_move_list,
                'message': 'success'
            }

            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:

            _logger.error(
                "An error occurred while searching for account move: %s",
                traceback.format_exc()
            )

            error_response = {
                'status': 500,
                'error': str(e)
            }

            return request.make_response(
                json.dumps(error_response),
                headers=[('Content-Type', 'application/json')],
                status=500
            )


    @http.route(
        '/api/view/accountmoveline',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False
    )
    def get_account_move_line_view_data(self, **kwargs):

        try:
            inv_no = request.params.get("inv_no")

            if inv_no:
                account_move_line_obj = request.env['vi.account.move.line'].sudo().search([
                    ('inv_no', '=', inv_no)
                ])
            else:
                account_move_line_obj = request.env['vi.account.move.line'].sudo().search([])

            account_move_line_list = []

            for t in account_move_line_obj:
                account_move_line_list.append({
                    "id": t.id,
                    "inv_whouse": t.inv_whouse,
                    "inv_no": t.inv_no,
                    "inv_slno": t.inv_slno,
                    "inv_subslno": t.inv_subslno,
                    "inv_orcr": t.inv_orcr,
                    "inv_orcpno": t.inv_orcpno,
                    "inv_pno": t.inv_pno,
                    "inv_pact": t.inv_pact,
                    "inv_nonstock": t.inv_nonstock,
                    "inv_desc": t.inv_desc,
                    "inv_group": t.inv_group,
                    "inv_stock": t.inv_stock,
                    "inv_part": t.inv_part,
                    "inv_det1": t.inv_det1,
                    "inv_det2": t.inv_det2,
                    "inv_qtyreq": t.inv_qtyreq,
                    "inv_qtyiss": t.inv_qtyiss,
                    "inv_cost": t.inv_cost,
                    "inv_price": t.inv_price,
                    "inv_disc": t.inv_disc,
                    "inv_pdisc": t.inv_pdisc,
                    "inv_vatcode": t.inv_vatcode,
                    "inv_vat": t.inv_vat,
                    "inv_ret": t.inv_ret,
                    "inv_pidref": t.inv_pidref,
                    "inv_xface": t.inv_xface,
                    "inv_fleetsale": t.inv_fleetsale,
                    "inv_trnslno": t.inv_trnslno,
                    "inv_trnsubslno": t.inv_trnsubslno,
                    "inv_subtrntype": t.inv_subtrntype,
                    "inv_subtrnref": t.inv_subtrnref,
                    "inv_cstordflag": t.inv_cstordflag,
                    "inv_sourcewh": t.inv_sourcewh,
                    "inv_discp": t.inv_discp,
                    "inv_reqgroup": t.inv_reqgroup,
                    "inv_reqstock": t.inv_reqstock,
                    "inv_reqpart": t.inv_reqpart,
                    "inv_reqdesc": t.inv_reqdesc,
                    "inv_orgreqqty": t.inv_orgreqqty,
                    "inv_cstpriceflg": t.inv_cstpriceflg,
                    "inv_isswhouse": t.inv_isswhouse,
                    "inv_export": t.inv_export,
                    "inv_wqty": t.inv_wqty,
                    "inv_dsiamt": t.inv_dsiamt,
                    "inv_salcat": t.inv_salcat,
                    "inv_vatexp": t.inv_vatexp,
                    "inv_promodisc": t.inv_promodisc,
                    "inv_promomsg1": t.inv_promomsg1,
                    "inv_promomsg2": t.inv_promomsg2,
                    "inv_promomsg3": t.inv_promomsg3,
                    "inv_campaign": t.inv_campaign,
                    "inv_campaignref": t.inv_campaignref,
                    "inv_autocrnoteval": t.inv_autocrnoteval,
                    "inv_autocrnotestatus": t.inv_autocrnotestatus,
                })

            response_data = {
                'status': 200,
                'response': account_move_line_list,
                'message': 'success'
            }

            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error(
                "An error occurred while searching for account move: %s",
                traceback.format_exc()
            )

            error_response = {
                'status': 500,
                'error': 'An error occurred while searching for account move line'
            }

            return request.make_response(
                json.dumps(error_response),
                headers=[('Content-Type', 'application/json')],
                status=500
            )


       
    # @validate_token
    @http.route(
        "/api/account_move/update",
        methods=["POST"],
        type="http",
        auth="none",
        csrf=False
    )
    def _account_move_update(self, **post):

        try:

            payload = json.loads(
                request.httprequest.data.decode('utf-8')
            )

            params = payload.get('params', {})

            if not params:
                return request.make_response(
                    json.dumps({
                        "error": "Missing params"
                    }),
                    headers=[('Content-Type', 'application/json')]
                )

            move_id = params.get('id')
            move_name = params.get('name')

            account_move = request.env['account.move'].sudo().search([
                ('id', '=', move_id),
                ('name', '=', move_name)
            ], limit=1)

            if not account_move:
                return request.make_response(
                    json.dumps({
                        "error": "Record not found"
                    }),
                    headers=[('Content-Type', 'application/json')]
                )

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ('id', 'name')
            }

            account_move.write(update_vals)

            return request.make_response(
                json.dumps({
                    "success": True,
                    "message": "Updated Successfully"
                }),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:

            _logger.exception(e)

            return request.make_response(
                json.dumps({
                    "error": str(e)
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

            
    # @validate_token
    @http.route('/api/view/accountmovenamelist', type='http', auth='none', methods=['GET'], csrf=False)
    def get_accountmove_namelist_view_data(self, **kwargs):
        try:

            accountmove_namelist_obj = request.env['vi.account.move.namelist'].sudo().search([])

            accountmove_name_list = []

            for t in accountmove_namelist_obj:
                accountmove_name_list.append({
                    "inv_whouse": t.inv_whouse,
                    "inv_manualinvno": t.inv_manualinvno,
                })

            return request.make_response(
                json.dumps({
                    'status': 200,
                    'response': accountmove_name_list,
                    'message': 'success'
                }),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.exception("Error in /api/view/accountmovenamelist: %s", e)

            return request.make_response(
                json.dumps({
                    'status': 500,
                    'error': 'Internal server error'
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
            
    @validate_token
    @http.route("/api/t_products/search", methods=["GET"], type="http", auth="none", csrf=False)
    def t_products_search(self, **kwargs):
        try:
            _logger.info("Searching t_products records")

            p_grp = request.params.get("p_grp")
            p_code = request.params.get("p_code")

            domain = []

            if p_grp:
                domain.append(('p_grp', '=', p_grp))

            if p_code:
                domain.append(('p_code', '=', p_code))

            records = request.env['t.products'].sudo().search(domain)

            result = []

            for rec in records:
                result.append({
                    "p_grp": rec.p_grp,
                    "p_code": rec.p_code,
                    "p_markup": rec.p_markup,
                    "p_pcat": rec.p_pcat,
                    "p_duty": rec.p_duty,
                    "user_id": rec.user_id,
                    "user_lmd": str(rec.user_lmd) if rec.user_lmd else "",
                    "user_lmt": rec.user_lmt,
                    "p_desc": rec.p_desc,
                    "p_desc2": rec.p_desc2,
                    "lang_flag": rec.lang_flag,
                    "lang_flag2": rec.lang_flag2,
                    "p_sort": rec.p_sort,
                    "p_loyaltyreq": rec.p_loyaltyreq,
                    "p_mpcode": rec.p_mpcode,
                })

            response_data = {
                "status": 200,
                "response": result,
                "message": "success"
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error("Error searching t_products: %s", str(e))

            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps({
                    "status": 500,
                    "error": "Error while searching t_products"
                })
            )

    # =====================================================
    # CREATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_products/create", methods=["POST"], type="json", auth="none", csrf=False)
    def t_products_create(self, **post):
        try:
            _logger.info("Creating t_products")

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            p_grp = params.get("p_grp")
            p_code = params.get("p_code")

            existing = request.env['t.products'].sudo().search([
                ('p_grp', '=', p_grp),
                ('p_code', '=', p_code)
            ], limit=1)

            if existing:
                return {
                    "success": False,
                    "message": f"Record already exists for p_grp {p_grp} and p_code {p_code}"
                }

            new_record = request.env['t.products'].sudo().create({
                'p_grp': params.get('p_grp'),
                'p_code': params.get('p_code'),
                'p_markup': params.get('p_markup'),
                'p_pcat': params.get('p_pcat'),
                'p_duty': params.get('p_duty'),
                'user_id': params.get('user_id'),
                'user_lmd': params.get('user_lmd'),
                'user_lmt': params.get('user_lmt'),
                'p_desc': params.get('p_desc'),
                'p_desc2': params.get('p_desc2'),
                'lang_flag': params.get('lang_flag'),
                'lang_flag2': params.get('lang_flag2'),
                'p_sort': params.get('p_sort'),
                'p_loyaltyreq': params.get('p_loyaltyreq'),
                'p_mpcode': params.get('p_mpcode'),
            })

            return {
                "success": True,
                "message": "t_products created successfully",
                "data": {
                    "id": new_record.id,
                    "p_grp": new_record.p_grp,
                    "p_code": new_record.p_code
                }
            }

        except Exception as e:
            _logger.error("Error creating t_products: %s", str(e))

            return {
                "success": False,
                "message": "Error while creating t_products"
            }

    # =====================================================
    # UPDATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_products/update", methods=["POST"], type="json", auth="none", csrf=False)
    def t_products_update(self, **post):
        try:
            _logger.info("Updating t_products")

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            p_grp = params.get("p_grp")
            p_code = params.get("p_code")

            record = request.env['t.products'].sudo().search([
                ('p_grp', '=', p_grp),
                ('p_code', '=', p_code)
            ], limit=1)

            if not record:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ('p_grp', 'p_code') and value is not None
            }

            if update_vals:
                record.sudo().write(update_vals)

            return {
                "success": True,
                "message": "t_products updated successfully",
                "data": {
                    "p_grp": record.p_grp,
                    "p_code": record.p_code
                }
            }

        except Exception as e:
            _logger.error("Error updating t_products: %s", str(e))

            return {
                "success": False,
                "message": "Error while updating t_products"
            }

    # =====================================================
    # DELETE API
    # =====================================================
    @validate_token
    @http.route("/api/t_products/delete", methods=["POST"], type="json", auth="none", csrf=False)
    def t_products_delete(self, **post):
        try:
            _logger.info("Deleting t_products")

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            p_grp = params.get("p_grp")
            p_code = params.get("p_code")

            record = request.env['t.products'].sudo().search([
                ('p_grp', '=', p_grp),
                ('p_code', '=', p_code)
            ], limit=1)

            if not record:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            record.sudo().unlink()

            return {
                "success": True,
                "message": f"t_products deleted for p_code {p_code}"
            }

        except Exception as e:
            _logger.error("Error deleting t_products: %s", str(e))

            return {
                "success": False,
                "message": "Error while deleting t_products"
            }

    # =====================================================
    # SEARCH API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproducts/search", methods=["GET"], type="http", auth="none", csrf=False)
    def t_mainproducts_search(self, **kwargs):
        try:

            mp_grp = request.params.get("mp_grp")
            mp_code = request.params.get("mp_code")

            domain = []

            if mp_grp:
                domain.append(('mp_grp', '=', mp_grp))

            if mp_code:
                domain.append(('mp_code', '=', mp_code))

            records = request.env['t.mainproducts'].sudo().search(domain)

            result = []

            for rec in records:
                result.append({
                    "mp_grp": rec.mp_grp,
                    "mp_code": rec.mp_code,
                    "mp_sort": rec.mp_sort,
                    "user_id": rec.user_id,
                    "user_lmd": str(rec.user_lmd) if rec.user_lmd else "",
                    "user_lmt": rec.user_lmt,
                })

            response_data = {
                "status": 200,
                "response": result,
                "message": "success"
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error(str(e))

            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps({
                    "status": 500,
                    "error": str(e)
                })
            )

    # =====================================================
    # CREATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproducts/create", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproducts_create(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")

            existing = request.env['t.mainproducts'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code)
            ], limit=1)

            if existing:
                return {
                    "success": False,
                    "message": "Record already exists"
                }

            rec = request.env['t.mainproducts'].sudo().create({
                'mp_grp': params.get('mp_grp'),
                'mp_code': params.get('mp_code'),
                'mp_sort': params.get('mp_sort'),
                'user_id': params.get('user_id'),
                'user_lmd': params.get('user_lmd'),
                'user_lmt': params.get('user_lmt'),
            })

            return {
                "success": True,
                "message": "Created Successfully",
                "data": {
                    "id": rec.id,
                    "mp_grp": rec.mp_grp,
                    "mp_code": rec.mp_code
                }
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

    # =====================================================
    # UPDATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproducts/update", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproducts_update(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")

            rec = request.env['t.mainproducts'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code)
            ], limit=1)

            if not rec:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ('mp_grp', 'mp_code') and value is not None
            }

            rec.sudo().write(update_vals)

            return {
                "success": True,
                "message": "Updated Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

    # =====================================================
    # DELETE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproducts/delete", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproducts_delete(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")

            rec = request.env['t.mainproducts'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code)
            ], limit=1)

            if not rec:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            rec.sudo().unlink()

            return {
                "success": True,
                "message": "Deleted Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }


    # =====================================================
    # SEARCH API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproductsdesc/search", methods=["GET"], type="http", auth="none", csrf=False)
    def t_mainproductsdesc_search(self, **kwargs):
        try:

            mp_grp = request.params.get("mp_grp")
            mp_code = request.params.get("mp_code")
            mp_lang = request.params.get("mp_lang")

            domain = []

            if mp_grp:
                domain.append(('mp_grp', '=', mp_grp))

            if mp_code:
                domain.append(('mp_code', '=', mp_code))

            if mp_lang:
                domain.append(('mp_lang', '=', int(mp_lang)))

            records = request.env['t.mainproductsdesc'].sudo().search(domain)

            result = []

            for rec in records:
                result.append({
                    "mp_grp": rec.mp_grp,
                    "mp_code": rec.mp_code,
                    "mp_lang": rec.mp_lang,
                    "mp_desc": rec.mp_desc,
                    "lang_flag": rec.lang_flag,
                })

            response_data = {
                "status": 200,
                "response": result,
                "message": "success"
            }

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                response=json.dumps(response_data)
            )

        except Exception as e:
            _logger.error(str(e))

            return werkzeug.wrappers.Response(
                status=500,
                content_type="application/json; charset=utf-8",
                response=json.dumps({
                    "status": 500,
                    "error": str(e)
                })
            )

    # =====================================================
    # CREATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproductsdesc/create", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproductsdesc_create(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")
            mp_lang = params.get("mp_lang")

            existing = request.env['t.mainproductsdesc'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code),
                ('mp_lang', '=', mp_lang)
            ], limit=1)

            if existing:
                return {
                    "success": False,
                    "message": "Record already exists"
                }

            rec = request.env['t.mainproductsdesc'].sudo().create({
                'mp_grp': params.get('mp_grp'),
                'mp_code': params.get('mp_code'),
                'mp_lang': params.get('mp_lang'),
                'mp_desc': params.get('mp_desc'),
                'lang_flag': params.get('lang_flag'),
            })

            return {
                "success": True,
                "message": "Created Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

    # =====================================================
    # UPDATE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproductsdesc/update", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproductsdesc_update(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")
            mp_lang = params.get("mp_lang")

            rec = request.env['t.mainproductsdesc'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code),
                ('mp_lang', '=', mp_lang)
            ], limit=1)

            if not rec:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            update_vals = {
                key: value
                for key, value in params.items()
                if key not in ('mp_grp', 'mp_code', 'mp_lang') and value is not None
            }

            rec.sudo().write(update_vals)

            return {
                "success": True,
                "message": "Updated Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

    # =====================================================
    # DELETE API
    # =====================================================
    @validate_token
    @http.route("/api/t_mainproductsdesc/delete", methods=["POST"], type="json", auth="none", csrf=False)
    def t_mainproductsdesc_delete(self, **post):
        try:

            payload = json.loads(request.httprequest.data.decode('utf-8'))
            params = payload.get("params", {})

            mp_grp = params.get("mp_grp")
            mp_code = params.get("mp_code")
            mp_lang = params.get("mp_lang")

            rec = request.env['t.mainproductsdesc'].sudo().search([
                ('mp_grp', '=', mp_grp),
                ('mp_code', '=', mp_code),
                ('mp_lang', '=', mp_lang)
            ], limit=1)

            if not rec:
                return {
                    "success": False,
                    "message": "Record not found"
                }

            rec.sudo().unlink()

            return {
                "success": True,
                "message": "Deleted Successfully"
            }

        except Exception as e:
            _logger.error(str(e))

            return {
                "success": False,
                "message": str(e)
            }

    @validate_token
    @http.route("/api/customer_updates", methods=["GET"], type="http", auth="none", csrf=False)
    def customer_updates(self, **kwargs):
        try:
            last_modified = kwargs.get('last_modified')

            domain = []
            if last_modified:
                domain.append(('write_date', '>=', last_modified))

            customers = request.env['res.partner'].sudo().search(domain)

            result = []
            for rec in customers:
                result.append({
                    "name": rec.name,
                    "ref": rec.ref,
                    "collected_points_regular": rec.collected_points_regular,
                    "balance_points_regular": rec.balance_points_regular,
                    "tier_name": rec.tier_name,
                    "activation_date": str(rec.activation_date) if rec.activation_date else "",
                    "redemption_deadline": str(rec.redemption_deadline) if rec.redemption_deadline else "",
                    "activate_loyalty_feature": rec.activate_loyalty_feature,
                    "write_date": str(rec.write_date) if rec.write_date else "",
                })

            return Response(
                json.dumps({
                    "status": "success",
                    "count": len(result),
                    "data": result
                }),
                content_type="application/json",
                status=200
            )

        except Exception as e:
            return Response(
                json.dumps({
                    "status": "error",
                    "message": str(e)
                }),
                content_type="application/json",
                status=500
            )

    @validate_token
    @http.route("/api/loyalty_audit_updates", methods=["GET"], type="http", auth="none", csrf=False)
    def loyalty_audit_updates(self, **kwargs):
        try:
            last_modified = kwargs.get('last_modified')

            domain = []
            if last_modified:
                domain.append(('write_date', '>=', last_modified))

            records = request.env['customer.loyalty.points.history'].sudo().search(domain)

            result = []
            for rec in records:
                result.append({
                    "clph_cstcode": rec.clph_cstcode,
                    "clph_date": str(rec.clph_date) if rec.clph_date else "",
                    "clph_doctype": rec.clph_doctype,
                    "clph_docnumber": rec.clph_docnumber,
                    "clph_type": rec.clph_type,
                    "clph_whouse": rec.clph_whouse,
                    "clph_regpoints": rec.clph_regpoints,
                    "clph_note": rec.clph_note,
                    "clph_adjtype": rec.clph_adjtype,
                    "write_date": str(rec.write_date) if rec.write_date else "",
                })

            return Response(
                json.dumps({
                    "status": "success",
                    "count": len(result),
                    "data": result
                }),
                content_type="application/json",
                status=200
            )

        except Exception as e:
            return Response(
                json.dumps({
                    "status": "error",
                    "message": str(e)
                }),
                content_type="application/json",
                status=500
            )

        
# @http.route(["/api/auth/token"], methods=["DELETE"], type="http", auth="none", csrf=False)
    # def delete(self, **post):
    #     """Delete a given token"""
    #     token = request.env["api.access_token"]
    #     access_token = post.get("access_token")
    #
    #     access_token = token.search([("token", "=", access_token)], limit=1)
    #     if not access_token:
    #         error = "Access token is missing in the request header or invalid token was provided"
    #         return invalid_response(400, error)
    #     for token in access_token:
    #         token.unlink()
    #     # Successful response:
    #     return valid_response([{"message": "access token %s successfully deleted" % (access_token,), "delete": True}])
