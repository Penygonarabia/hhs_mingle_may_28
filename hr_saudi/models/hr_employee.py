# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo import SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from lxml import etree
import json



class HrEmployee(models.Model):
    _inherit = ['hr.employee',]
    _description = 'HR Employee'


    # def action_update_manager(self):
    #     # For updating parent employee records
    #     if not self.parent_id:
    #         self.parent_id = self.department_id.manager_id.id
    #     if self.id == self.parent_id.id:
    #         self.parent_id = self.department_id.parent_id.manager_id.id
    #     if self.parent_id:
    #         self.leave_manager_id = self.parent_id.user_id.id # For updating 'Time Off' field.

  

    # def _get_latest_contract(self):
    #     res = {}
    #     contract_obj = self.env['hr.contract']
    #     for emp in self:
    #         contract_ids = contract_obj.search([('employee_id', '=', emp.id)], order='date_start')
    #         if contract_ids:
    #             res[emp.id] = contract_ids[-1:][0]
    #         else:
    #             res[emp.id] = False
    #     return res

  

    employee_no = fields.Char(string='Employee No')
    middle_name = fields.Char(string='Father Name')
    third_name = fields.Char(string='Grand-Father Name')
    last_name = fields.Char(size=128, string='Family Name')
    arabic_name = fields.Char(string='Arabic Name')
    main_department_id = fields.Many2one('hr.department', string='Main Department')
    grade_id = fields.Many2one('hr.grade', 'Grade')
    branch_id = fields.Many2one('hr.branch', 'Branch Office')
    is_saudi = fields.Boolean(string='Is Saudi', default=False)
    # is_saudi = fields.Boolean(string='Is Saudi', default=True)

    country_id = fields.Many2one('res.country', string='Nationality',
                                 groups="base.group_user")
    driving_license = fields.Binary(string="Driving License", )
    iqama_no = fields.Char(string='Iqama No', size=10, compute="_compute_iqama_no" ,store=True)
    # iqama_professional = fields.Char(string='Iqama profession', size=50)
    iqama_professional = fields.Many2one('iqama.management', string='Iqama Profession')
    iqama_expiry_date = fields.Date(string='Iqama Expiry Date')
    age = fields.Integer( string='Age')
    country_address = fields.Char(size=128, string='Address in the home country')
    country_mobile_phone = fields.Char(string='Mobile',related='address_id.mobile',related_sudo=False,
                        readonly=False)
    # country_mobile_phone = fields.Integer(string='Phone number in the home country')

    work_location = fields.Char('Work Location', default=lambda self: self.env['res.users'].search([('id', '=', self._uid)]).company_id.street)
    join_date = fields.Date(string='Join Date')
    
    # speciality_id = fields.Many2one('hr.speciality', string='Speciality')
    # qualification_ids = fields.One2many('hr.qualification', 'employee_id', string='Qualifications')
    # certification_ids = fields.One2many('hr.certification', 'employee_id', string='Certifications')
    # experience_ids = fields.One2many('hr.experience', 'employee_id', string='Experiences')
    passeport_expiry_date = fields.Date(string='Passport Expiry  Date', invisible=True)
    # passeport_issue_place = fields.Char(string='passport issue place', invisible=True)
    passeport_issue_place = fields.Many2one('res.city',string='Passport issue place', invisible=True)

    # Documents
    # document_ids = fields.One2many('res.documents', 'employee_id', string='Documents')
    # ~ # Medical Insurance
    # ~ insurance_ids = fields.One2many('hr.medical.insurance', 'employee_id', string='Medical Insurances')
    auto_employee_no = fields.Boolean(string='Create emp no automatically')
    # auto_employee_no = fields.Boolean(string='Create emp no automatically', default=_compute_auto_emp_no)
    # Contracts List
    # ~ contract_ids = fields.One2many('hr.contract', 'employee_id', string='Contracts List')
    # Remove other from Gender selection and set default to Male
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', default='male', groups="base.group_user")
    religion = fields.Selection([
        ('muslim', 'Muslim'),
        ('non-muslim', 'Non-muslim')
    ], string='Religion', default='muslim')
    #Assets list
    # asset_ids = fields.Many2many('hr.asset.line', 'asset_employee_rel', 'asset_line_id', 'emp_id', string='List of Assets')
    normal_leave = fields.Float(string='Normal Leave Stock')
    # training_ids = fields.Many2many('hr.training', 'training_employee_rel', 'training_id', 'emp_id', string='Trainings')
    mobile_phone = fields.Char('Work Mobile', readonly=False, )
    manager = fields.Boolean('Is a Manager')
    medic_exam = fields.Date('Medical Examination Date')
    place_of_birth = fields.Char('Birthplace', groups="base.group_user")
    children = fields.Integer('Number of family members', groups="base.group_user")
    vehicle = fields.Char('Company Vehicle')
    vehicle_distance = fields.Integer('Home-Work Dist.', help="In kilometers")
    contract_id = fields.Many2one('hr.contract', string='Current contract', help='Latest contract of the employee')
    # contracts_count = fields.Integer(string='Contracts')
    lang_ids = fields.Many2many('res.lang', 'employee_lang_rel', 'emp_id', 'lang_id')
    disability = fields.Char(string="Disabilities")
    residence_expiration_date = fields.Date(string="Residence expiration date",)

    # -------------------------------------- #
    # hr.employee model fields group update  #
    # ---------------------------------------#
    birthday = fields.Date(
        'Date of Birth',
        groups="base.group_user",
        tracking=True)
    study_field = fields.Char("Field of Study", groups="base.group_user",
                              tracking=True)
    # resource and user
    # required on the resource, make sure required="True" set in the view
    name = fields.Char(string="Employee Name", related='resource_id.name',
                       store=True, readonly=False, tracking=True)
    user_id = fields.Many2one('res.users', 'User',
                              related='resource_id.user_id', store=True,
                              readonly=False)
    user_partner_id = fields.Many2one(related='user_id.partner_id',
                                      related_sudo=False,
                                      string="User's partner")
    active = fields.Boolean('Active', related='resource_id.active',
                            default=True, store=True, readonly=False)
    company_id = fields.Many2one('res.company', )
    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks')
    # private partner
    address_id = fields.Many2one(
        'res.partner', 'Address',
        help='Enter here the private address of the employee, not the one linked to your company.',
        groups="base.group_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    is_address_home_a_company = fields.Boolean(
        'The employee address has a company linked',
        compute='_compute_is_address_home_a_company',
    )
    private_email = fields.Char(string="Private Email", groups="base.group_user")# related='address_home_id.email',
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status', groups="base.group_user", default='single',
        tracking=True)
    spouse_complete_name = fields.Char(string="Spouse Complete Name",
                                       groups="base.group_user", tracking=True)
    spouse_birthdate = fields.Date(string="Spouse Birthdate",
                                   groups="base.group_user", tracking=True)
    country_of_birth = fields.Many2one('res.country', string="Country of Birth",
                                       groups="base.group_user", tracking=True)
    ssnid = fields.Char('SSN No', help='Social Security Number',
                        groups="base.group_user", tracking=True)
    sinid = fields.Char('SIN No', help='Social Insurance Number',
                        groups="base.group_user", tracking=True)
    identification_no = fields.Char(string='Identification No',
                                    groups="base.group_user", tracking=True)
    # passport_id = fields.Char('Passport No', groups="base.group_user",
    #                           tracking=True, invisible=True)
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account Number',
        domain="[('partner_id', '=', address_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        groups="base.group_user",
        tracking=True,
        help='Employee bank salary account')
    permit_no = fields.Char('Work Permit No', groups="base.group_user",
                            tracking=True)
    visa_no = fields.Char('Visa No', groups="base.group_user", tracking=True)
    visa_expire = fields.Date('Visa Expire Date', groups="base.group_user",
                              tracking=True)
    additional_note = fields.Text(string='Additional Note',
                                  groups="base.group_user", tracking=True)
    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other', groups="base.group_user",
        tracking=True)
    study_field = fields.Char("Field of Study", groups="base.group_user",
                              tracking=True)
    study_school = fields.Char("School", groups="base.group_user",
                               tracking=True)
    emergency_contact = fields.Char("Emergency Contact",
                                    groups="base.group_user", tracking=True)
    emergency_phone = fields.Char("Emergency Phone", groups="base.group_user",
                                  tracking=True)
    km_home_work = fields.Integer(string="Home-Work Distance",
                                  groups="base.group_user", tracking=True)

    phone = fields.Char(related='address_id.phone', related_sudo=False,
                        readonly=False, string="Private Phone",
                        groups="base.group_user")
    # employee in company
    # child_ids = fields.One2many('hr.employee', 'parent_id',
    #                             string='Direct subordinates')
    # category_ids = fields.Many2many(
    #     'hr.employee.category', 'employee_category_rel',
    #     'emp_id', 'category_id', groups="hr.group_hr_manager",
    #     string='Tags')
    # misc
    notes = fields.Text('Notes', groups="base.group_user")
    color = fields.Integer('Color Index', default=0, groups="base.group_user")
    barcode = fields.Char(string="Badge ID",
                          help="ID used for employee identification.",
                          groups="base.group_user", copy=False)
    pin = fields.Char(string="PIN", groups="base.group_user", copy=False,
                      help="PIN used to Check In/Out in Kiosk Mode (if enabled in Configuration).")
    departure_reason = fields.Selection([
        ('fired', 'Fired'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired')
    ], string="Departure Reason", groups="base.group_user", copy=False,
        tracking=True)
    departure_description = fields.Text(string="Additional Information",
                                        groups="base.group_user", copy=False,
                                        tracking=True)
    departure_date = fields.Date(string="Departure Date",
                                 groups="base.group_user", copy=False,
                                 tracking=True)
    message_main_attachment_id = fields.Many2one(groups="base.group_user")


    # HR Employee group update fields
    spouse_fiscal_status = fields.Selection([
        ('without_income', 'Without Income'),
        ('high_income', 'With High income'),
        ('low_income', 'With Low Income'),
        ('low_pension', 'With Low Pensions'),
        ('high_pension', 'With High Pensions')
    ], string='Tax status for spouse', groups="base.group_user",
        default='without_income', required=False)
    # Start
    ticket_depends = fields.Integer(string="Ticket Depends")

    contract_warning = fields.Boolean(string='Contract Warning', store=True,  groups="hr.group_hr_user,hr_attendance.group_hr_attendance_kiosk")
    first_contract_date = fields.Date( groups="hr.group_hr_user,hr_attendance.group_hr_attendance_kiosk")

    state = fields.Selection(selection=[('draft', 'Enroll'), ('exit', 'Exit')], string='State',
                             readonly=True, help='',
                             default='draft', tracking=True)

    exit_date = fields.Date(string="Exit Date")
    allocation_used_display = fields.Char(string="Allocation Used Display")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(HrEmployee, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                    submenu=submenu)
        # employee_id = self._context.get('active_id') or self._context.get('params', {}).get('id')
        # print("Context: ", self._context)
        # print("Employee ID: ", employee_id)

        if view_type == 'form':
            doc = etree.XML(res['arch'])
            # List of fields to exclude from being read-only
            exclude_fields = ['last_activity', 'first_contract_date', 'allocation_display',
                              'allocation_remaining_display', 'hours_last_month_display', 'exit_date']
            for node in doc.xpath("//field"):
                field_name = node.get("name")
                # print("field_name", field_name)
                # print("field_name", field_name)
                if field_name not in exclude_fields:
                    modifiers = json.loads(node.get("modifiers", "{}"))
                    # modifiers['readonly'] = [('exit_date', '!=', False)]
                    modifiers['readonly'] = [('state', '=', 'exit')]
                    node.set("modifiers", json.dumps(modifiers))
                    node.set("readonly", "1")
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
   
    @api.depends('document_count')
    def _compute_iqama_no(self):
        for rec in self:
            rec.iqama_no = False
            rec.passport_id = False
            if rec.document_count:
                document_search = self.env['hr.employee.document'].search([('employee_ref','=',rec.id)])
                for document in document_search:
                    document_name_lower = document.document_name.name.lower()
                    if document_name_lower == 'iqama' and document.document_name.active:
                        rec.iqama_no = document.name or False
                        rec.iqama_expiry_date = document.expiry_date or False
                        rec.id_attachment_id = document.doc_attachment_id or False
                    if document_name_lower == 'passport' and document.document_name.active:
                        rec.passport_id = document.name or False
                        rec.passeport_expiry_date = document.expiry_date or False
                        rec.passeport_issue_place = document.place_city_id or False



    @api.constrains('employee_no')
    def _check_employee_no(self):
        for rec in self:
            if rec.employee_no:
                number_count = self.search_count([('employee_no','=',rec.employee_no),('id','!=',rec.id)])
                if number_count > 0:
                    raise ValidationError("Please Enter unique Employee number of an Employee")


                    # print("....rec",rec.document_count)
            
    # Added 'hr_attendance.group_hr_attendance_kiosk' this groups additionally in this field.
    # sign_request_count = fields.Integer(
    #     groups="hr_contract.group_hr_contract_manager,hr_attendance.group_hr_attendance_kiosk",
    # )
    
    # @api.onchange('address_home_id')
    # def _onchange_address_home(self):
    #     for rec in self:
    #         if rec.address_home_id:
    #             rec.country_address = rec.address_home_id.street

    # def _compute_sign_request_count(self):
    #     for employee in self:
    #         contracts = self.env['hr.contract'].sudo().search([('employee_id', '=', employee.id)])
    #         sign_from_contract = contracts.mapped('sign_request_ids')
    #
    #         sign_from_role = self.env['sign.request'].browse([])
    #         if employee.user_id.partner_id.id:
    #             sign_from_role = self.env['sign.request.item'].search([
    #                 ('partner_id', '=', employee.user_id.partner_id.id),
    #                 ('role_id', '=', self.env.ref('sign.sign_item_role_employee').id)]).mapped('sign_request_id')
    #
    #         employee.sign_request_count = len(set(sign_from_contract + sign_from_role))

    # @api.depends('contract_ids.state', 'contract_ids.date_start')
    # def _compute_first_contract_date(self):
    #     for employee in self:
    #         contracts = employee._get_first_contracts()
    #         if contracts:
    #             employee.first_contract_date = min(contracts.mapped('date_start'))
    #         else:
    #             employee.first_contract_date = False

    # @api.depends('contract_id', 'contract_id.state', 'contract_id.kanban_state')
    # def _compute_contract_warning(self):
    #     for employee in self:
    #         employee.contract_warning = not employee.contract_id or employee.contract_id.kanban_state == 'blocked' or employee.contract_id.state != 'open'
    
    # @api.model
    # def update_leave_balance(self):
    #     for employee in self.search([]):
    #         employee.normal_leave += 2.5

    # @api.model
    # def create(self, vals):
    #     emp_id = super(HrEmployee, self).create(vals)
    #     # Sequence
    #     if vals.get('auto_employee_no', False):
    #         employee_no = self.env['ir.sequence'].get('hr.employee.seq')
    #         emp_id.employee_no = employee_no
    #     user = self.env.user
    #     is_admin = user.has_group('base.group_erp_manager') or user.has_group('saudi_hr.group_hrm')
    #     if not is_admin:
    #         raise UserError(_('Only HR Admin/System Admin can create employee profile.'))
    #
    #     return emp_id

    # @api.depends('birthday')
    # def _compute_age(self):
    #     for employee in self:
    #         if not employee.birthday:
    #             print("Birthday is missing for employee:", employee.id)
    #             employee.update({'age': 0})
    #             continue
    #
    #         today_date = fields.Date.from_string(fields.Date.today())
    #         birthday = fields.Date.from_string(employee.birthday)
    #         years = relativedelta(today_date, birthday).years
    #         if years > -1:
    #             employee.update({'age': years})

    # @api.onchange('job_id')
    # def onchange_job_id(self):
    #     if self.job_id:
    #         self.department_id = self.job_id.department_id
    #     else:
    #         self.department_id = False

    # @api.onchange('parent_id')
    # def onchange_manager_id(self):
    #     """
    #         Method to update manager value to leave manager value.
    #     """
    #     if not self.parent_id.user_id:
    #         return
    #
    #     self.leave_manager_id = self.parent_id.user_id.id


# ~ class HRMedicalInsurance(models.Model):
    # ~ _name = 'hr.medical.insurance'
    # ~ _description = 'Employee Medical Insurance'

    # ~ employee_id = fields.Many2one('hr.employee', string='Employee')
    # ~ member_name = fields.Char(string='Insured name')
    # ~ birth_date = fields.Date(string='Birthday')
    # ~ class_type_id = fields.Many2one('hr.medical.insurance.class', string='Class')
    # ~ relation = fields.Selection([
        # ~ ('employee', 'Employee'),
        # ~ ('child', 'Child'),
        # ~ ('spouse', 'Spouse'),
        # ~ ('parent', 'Parents')
    # ~ ], 'Relation')
    # ~ id_number = fields.Char('ID Number', size=20)
    # ~ sponsor_id = fields.Char('Provider')
    # ~ expiry_date = fields.Date(string='Expiry Date')
    # ~ gender = fields.Selection([
        # ~ ('male', 'Male'),
        # ~ ('female', 'Female')
    # ~ ], string='Gender')


# ~ class HRMedicalInsurance(models.Model):
    # ~ _name = "hr.medical.insurance.class"
    # ~ _description = 'Insurance Class'

    # ~ name = fields.Char(string='Name', required=True)
    # ~ description = fields.Text(string='Description')


# class HrQualification(models.Model):
#     _name = 'hr.qualification'
#     _description = 'HR Qualification'
#
#     employee_id = fields.Many2one('hr.employee', string='Employee')
#     name = fields.Char(string='Qualification')
#     university_name = fields.Char(string='University')
#     attended_date_from = fields.Date(string='From')
#     attended_date_to = fields.Date(string='To')
#     program_type = fields.Selection([
#         ('completed', 'Finished'),
#         ('ongoing', 'Ongoing')
#     ], string='State')
#     description = fields.Text(string='Description')

#
# class HrCertification(models.Model):
#     _name = 'hr.certification'
#     _description = 'HR Certification'
#
#     employee_id = fields.Many2one('hr.employee', string='Employee')
#     name = fields.Char(string='Certification')
#     organization_name = fields.Char(string='Issuing Organization')
#     issue_date = fields.Date(string='Issue Date')
#     expiry_date = fields.Date(string='Expiry Date')
#     reg_no = fields.Char(string='Reference Number')
#
#
# class HrExperience(models.Model):
#     _name = "hr.experience"
#     _description = 'HR Experience'
#
#     employee_id = fields.Many2one('hr.employee', string='Employee')
#     company = fields.Char(string='Company')
#     job_title = fields.Char(string='Job')
#     location = fields.Char(string='City')
#     date_from = fields.Date(string='From')
#     date_to = fields.Date(string='To')
#     description = fields.Text(string='Description')
#
#
# class HrSpeciality(models.Model):
#     _name = "hr.speciality"
#     _description = 'HR Speciality'
#
#     name = fields.Char(string='Speciality')
#     description = fields.Text(string='Description')
#
#
class HrGrade(models.Model):
    _name = "hr.grade"
    _description = "Grade Description"

    name = fields.Char('Name', translate=True)
    # hr_job_ids = fields.One2many('hr.job', 'grade_id', 'Job')




