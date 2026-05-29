from odoo import api, fields, models, _
from lxml import etree
import json
from odoo.exceptions import warnings ,UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

def _get_employee(obj):
    if obj.env.user.has_group('hr_saudi.group_sys_manager'):
        return True
    else:
        ids = obj.env['hr.employee'].search([('user_id', '=', obj.env.uid)])
        if ids:
            return ids[0]
        else:
            raise ValidationError(_('The user is not an employee.'))

class HREmployeeTransaction(models.Model):
    _name = 'hr.employee.transaction'
    _description = 'Employee Transaction'

    name = fields.Char(string='Name')
    date = fields.Date(string='Transaction Date', default=fields.Datetime.today())
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_get_employee)
    employee_no = fields.Char(string='Employee No', related='employee_id.employee_no')
    # join_date = fields.Date(string='Join Date', related='employee_id.join_date')
    # Current Information
    current_department_id = fields.Many2one('hr.department', string='Department')
    current_main_department_id = fields.Many2one('hr.department', string='Main Department')
    current_job_id = fields.Many2one('hr.job', string='Job')
    current_branch_id = fields.Many2one('hr.branch', string='Branch Office')
    current_grade_id = fields.Many2one('hr.grade', string='Grade')
    # New Information
    new_department_id = fields.Many2one('hr.department', string='Department')
    new_main_department_id = fields.Many2one('hr.department', string='Main Department')
    new_job_id = fields.Many2one('hr.job', string='Job')
    new_branch_id = fields.Many2one('hr.branch', 'Branch Office')
    new_grade_id = fields.Many2one('hr.grade', string='Grade')
    # Contracts
    contract_ids = fields.Many2many('hr.contract', 'contract_transaction_rel', 'contract_id', 'transaction_id', string='Contracts List')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('request', 'Waiting for Direct Manager approval'),
        ('progress', 'Waiting for HR Manager approval'),
        ('progress2', 'Waiting for Finance Manager approval'),
        ('progress3', 'Waiting for Admin & Financial Director approval'),
        ('approve', 'Approved'),
        ('refused', 'Refused'),
    ], 'Status', readonly=True, tracking=True, default="draft",
        help='Status : User in 1.Draft(default) state Requesting to 2.DM Approval and processed by 3.HRM and Finalized by 4.FM')

    # ==============================================================================================
    d_manager = fields.Many2one('res.users', string="Direct Manager", readonly=True)
    hr_manage_id = fields.Many2one('res.users', string='HR Manager', readonly=True)
    account_manage_id = fields.Many2one('res.users', string='Accounting Manager', readonly=True)
    admin_manager_id = fields.Many2one('res.users', string='Admin & Finance Manager', readonly=True)
    # ==============================================================================================
    #       Responsible Notes
    d_manager_note = fields.Text(string="Direct Manager Note", )
    hr_manage_note = fields.Text(string="HR Manager Note", )
    account_manage_note = fields.Text(string="Accounting Manager Note", )
    admin_manager_note = fields.Text(string="Admin & Finance Manager Note", )

    # Add a Boolean field to indicate if the action_progress3 button has been clicked
    is_progress3_clicked = fields.Boolean(string="Action Progress3 Clicked", default=False)
    
    current_analytic_account_id = fields.Many2one(
        string="Analytic account",
        comodel_name="account.analytic.account",
    )
    
    new_analytic_account_id = fields.Many2one(
        string="Analytic account",
        comodel_name="account.analytic.account",
    )

    @api.model
    def create(self, vals):
        ret = super(HREmployeeTransaction, self).create(vals)
        # Objects
        employee_obj = self.env['hr.employee']
        # Variables
        employee_id = employee_obj.browse(vals.get('employee_id', False))
        new_vals = {'grade_id': ret.new_grade_id.id,
                    'job_id': ret.new_job_id.id,
                    'department_id': ret.new_job_id.department_id.id,
                    'main_department_id': ret.new_job_id.department_id.main_department_id.id,
                    'branch_id': ret.new_branch_id.id,
                    }
        # Update employee
        employee_id.write(new_vals)
        # Sequence
        name = self.env['ir.sequence'].get('hr.employee.transaction.seq')
        ret.name = name
        return ret

    @api.onchange('employee_id')
    def _update_info(self):
        if self.employee_id:
            self.current_department_id = self.employee_id.department_id
            self.current_main_department_id = self.employee_id.main_department_id
            self.current_job_id = self.employee_id.job_id
            self.current_branch_id = self.employee_id.branch_id
            self.current_grade_id = self.employee_id.grade_id
            self.contract_ids = self.employee_id.contract_ids
            self.current_analytic_account_id = self.employee_id.contract_id.analytic_account_id.id or False
            res ={}
            res['domain'] = {'new_analytic_account_id':[('id','!=',self.current_analytic_account_id.id)]}
            return res
        else:
            self.current_department_id = False
            self.current_main_department_id = False
            self.current_branch_id = False
            self.current_grade_id = False
            self.contract_ids = False

    @api.onchange('new_job_id')
    def _update_job_info(self):
        if self.new_job_id:
            self.new_department_id = self.new_job_id.department_id
            self.new_main_department_id = self.new_department_id.main_department_id
        else:
            self.new_department_id = False
            self.new_main_department_id = False
            
            
    @api.constrains('date')
    def _validaty_check_date(self):
        for rec in self:
            if rec.date:
                if rec.date < fields.Date.today():
                    raise ValidationError("Please enter the Date which is Greater than Today Date")
                    

    def action_request(self):
        self.write({'state': 'request'})

    def action_progress(self):
        self.write({'state': 'progress', 'd_manager': self.env.uid})

    def action_progress2(self):
        self.write({'state': 'progress2', 'hr_manage_id': self.env.uid})

    def action_approve(self):
        self.write({'state': 'progress3', 'account_manage_id': self.env.uid})

    def action_progress3(self):
        self.is_progress3_clicked = True
        self.write({'state': 'approve', 'admin_manager_id': self.env.uid})
        if self.state=='approve':
            if self.employee_id:
                # if self.new_analytic_account_id:
                self.employee_id.contract_id.analytic_account_id = self.new_analytic_account_id.id or False
                self.employee_id.department_id = self.new_department_id.id or False
                self.employee_id.main_department_id = self.new_main_department_id.id or False
                
        

    def action_draft(self):
        return self.write({'state': 'draft'})

    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(HREmployeeTransaction, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
    #                                                            submenu=submenu)
    #     if view_type == 'form' and self.employee_id.user_id:
    #         print("Raj")
    #         if not self.state == 'draft':
    #             print("Raj 22222")
    #
    #             doc = etree.XML(res['arch'])
    #             fields_to_make_readonly = ['date', 'employee_id', 'new_job_id', 'new_grade_id', 'new_branch_id']
    #             for field_name in fields_to_make_readonly:
    #                 for node in doc.xpath("//field[@name='%s']" % field_name):
    #                     modifiers = json.loads(node.get("modifiers", "{}"))
    #                     modifiers['readonly'] = True
    #                     node.set("modifiers", json.dumps(modifiers))
    #             res['arch'] = etree.tostring(doc)
    #
    #     return res

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
    #     res = super(HREmployeeTransaction, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
    #                                                              submenu=submenu)
    #     if view_type == 'tree':
    #         user_groups = self.env.user.groups_id.mapped('name')
    #         if 'Your Group Name' in user_groups:  # Replace 'Your Group Name' with the name of the group you want to check
    #             if self.state != 'draft':
    #                 doc = etree.XML(res['arch'])
    #                 fields_to_make_readonly = ['date', 'employee_id', 'new_job_id', 'new_grade_id', 'new_branch_id']
    #                 for field_name in fields_to_make_readonly:
    #                     for node in doc.xpath(
    #                             "//tree/field[@name='%s']" % field_name):  # Targeting fields in tree view only
    #                         modifiers = json.loads(node.get("modifiers", "{}"))
    #                         modifiers['readonly'] = True
    #                         node.set("modifiers", json.dumps(modifiers))
    #                 res['arch'] = etree.tostring(doc)
    #     return res

    # @api.model
    # def search(self, args, offset=0, limit=None, order=None, count=False):
    #     user = self.env.user
    #     if 'Your Group Name' in user.groups_id.mapped('name'):  # Replace 'Your Group Name' with the name of the group you want to check
    #         args += [('state', 'in', ['draft', 'request', 'progress', 'progress2', 'progress3'])]
    #     elif 'Another Group Name' in user.groups_id.mapped(
    #             'name'):  # Replace 'Another Group Name' with another group name
    #         args += [('state', 'in', ['approve', 'refused'])]
    #     return super(HREmployeeTransaction, self).search(args, offset, limit, order, count)

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        if self.env.user:
            if self.env.user.has_group('hr_saudi.group_sys_manager'):
                return super(HREmployeeTransaction, self).search_fetch(domain, field_names, offset, limit, order)

            if self.env.user.has_group('hr_saudi.group_normal_employee'):
                domain += [('employee_id.user_id', '=', self.env.user.id)]
                return super(HREmployeeTransaction, self).search_fetch(domain, field_names, offset, limit, order)

            if self.env.user.has_group('hr_saudi.group_dm'):
                domain += [('state', '=', 'request')]
                return super(HREmployeeTransaction, self).search_fetch(domain, field_names, offset, limit, order)

            if self.env.user.has_group('hr_saudi.group_hrm'):
                domain += [('state', '=', 'progress')]
                return super(HREmployeeTransaction, self).search_fetch(domain, field_names, offset, limit, order)
            if self.env.user.has_group('hr_saudi.group_finance_manager'):
                domain += [('state', '=', 'progress2')]
                return super(HREmployeeTransaction, self).search_fetch(domain, field_names, offset, limit, order)
            if self.env.user.has_group('hr_saudi.group_admin_approval'):
                domain += [('state', '=', 'progress3')]
                return super(HREmployeeTransaction, self).search_fetch(domain, field_names, offset, limit, order)

    # This code was added on 29-05-2024.
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    def get_view(self, view_id=None, view_type='form', toolbar=False, submenu=False, **options):
    
        # res = super(HREmployeeTransaction, self).fields_view_get(view_id=view_id, view_type=view_type,
        #                                                           toolbar=toolbar,
        #                                                           submenu=submenu)
        res = super(HREmployeeTransaction, self).get_view(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                     submenu=submenu, **options)
        
        if view_type == 'form':
            try:
                doc = etree.XML(res['arch'])
                buttons_to_hide = ['action_request', 'action_progress', 'action_progress2', 'action_approve']
                button_to_show = 'action_progress3'
                # draft = 'action_draft'
                
                if self.env.user.has_group('hr_saudi.group_sys_manager'):
                    # Hide specified buttons
                    for button_name in buttons_to_hide:
                        for node in doc.xpath(f"//button[@name='{button_name}']"):
                            # print(f"Hiding button '{button_name}'")
                            modifiers = json.loads(node.get("modifiers", "{}"))
                            modifiers['invisible'] = True
                            node.set("modifiers", json.dumps(modifiers))
                            node.set("invisible", "1")

                    # # Show button 'action_progress3' only if 'is_progress3_clicked' is not True
                    for node in doc.xpath(f"//button[@name='{button_to_show}']"):
                        # print(f"Configuring visibility for button '{button_to_show}' based on 'is_progress3_clicked'")
                        modifiers = json.loads(node.get("modifiers", "{}"))
                        modifiers['invisible'] = [('is_progress3_clicked', '=', True)]
                        node.set("modifiers", json.dumps(modifiers))
                
                # if self.env.user.has_group('hr_saudi.group_sys_manager'):
                #     for button_name in buttons_to_hide:
                #         for node in doc.xpath("//button[@name='%s']" % button_name):
                #             modifiers = json.loads(node.get("modifiers", "{}"))
                #             modifiers['invisible'] = True
                #             node.set("modifiers", json.dumps(modifiers))
                #             node.set("invisible", "0")
                #
                #     # Check if action_progress3 button has been clicked
                #     for node in doc.xpath("//button[@name='%s']" % button_to_show):
                #         modifiers = json.loads(node.get("modifiers", "{}"))
                #         modifiers['invisible'] = [('is_progress3_clicked', '=', True)]
                #         node.set("modifiers", json.dumps(modifiers))
                #         node.set("invisible", "0")

                    # for node in doc.xpath("//button[@name='%s']" % draft):
                    #     modifiers = json.loads(node.get("modifiers", "{}"))
                    #     modifiers['invisible'] = False
                    #     node.set("modifiers", json.dumps(modifiers))
                    #     node.set("invisible", "0")

                res['arch'] = etree.tostring(doc, encoding='unicode')

            except Exception as e:
                _logger.error("Error while modifying field view: %s", e)

        return res

    def unlink(self):
        for rec in self:
            if rec.state == 'approve':
                raise ValidationError(_('Approved Records cannot be deleted'))
        return super(HREmployeeTransaction, self).unlink()






