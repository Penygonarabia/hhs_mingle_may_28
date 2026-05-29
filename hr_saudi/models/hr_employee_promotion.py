# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, \
    DEFAULT_SERVER_DATETIME_FORMAT

DTI_FMT = '%Y-%m-%d %H:%M:%S'


class HrEmployeePromotion(models.Model):
    _name = 'hr.employee.promotion'
    _inherit = ['mail.thread']
    _description = 'HR Employee Promotion'

    name = fields.Char('Promotion ID', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_no = fields.Char(string='Employee NO', related='employee_id.employee_no')
    department_id = fields.Many2one('hr.department', string='Current Section', related='employee_id.department_id')
    current_job_id = fields.Many2one('hr.job', string='Current Job', related='employee_id.job_id')
    branch_id = fields.Many2one('hr.branch', string='Current Branch', related='employee_id.branch_id')
    promotion_type = fields.Selection(string="Promotion Type", selection=[('assign', 'Mandated'), ('design', 'Appoint')], required=True)
    start_date = fields.Date(string="Start Date", required=True)
    job_id = fields.Many2one('hr.job', string='New Job', required=True)
    new_department_id = fields.Many2one('hr.department', string='New Section', related='job_id.department_id')
    new_branch_id = fields.Many2one('hr.branch', string='New Branch')
    contract_ids = fields.Many2many('hr.contract', 'contract_promotion_rel', 'contract_id', 'promotion_id', string='Contract')
    state = fields.Selection(string="State", selection=[('draft', 'Draft'), ('done', 'تمت الموافقة'), ('refused', 'Refused')])
    user_id = fields.Many2one('res.users', 'User', required=True, default=lambda self: self.env.user)

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('hr.promotion.seq')
        return super(HrEmployeePromotion, self).create(vals)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.contract_ids = self.employee_id.contract_ids

    def button_hrm(self):
        for operation in self:
            operation.state = 'draft'

    def button_accept(self):
        models_data = self.env['ir.model.data']
        message_notif_obj = self.env['message.notif']
        template_id = models_data.get_object_reference('saudi_hr', 'calendar_template_transaction_warning')[1]
        date_now = datetime.now().strftime(DTI_FMT)
        dt_now = datetime.strptime(date_now, DTI_FMT)
        for operation in self:
            users = [operation.employee_id.user_id.id, operation.department_id.manager_id.user_id.id, operation.new_department_id.manager_id.user_id.id]
            for user in users:
                vals = {
                    'start_datetime': (dt_now + timedelta(seconds=5)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'type_event': 'info',
                    'template_id': template_id,
                    'user_id': user,
                    'res_id': self.id,
                    'model': 'hr.employee.promotion',
                    'notif': True,
                    'number_repeat': 2,
                }
                if user == operation.employee_id.user_id.id:
                    vals.update({
                        'name': 'You were promoted from job '+operation.current_job_id.name.encode(
                            'UTF-8')+' To '+operation.job_id.name.encode('UTF-8')+' Start Date '+operation.start_date,
                    })
                else:
                    vals.update({
                        'name': 'The employee has been promoted ' + operation.employee_id.name.encode(
                            'UTF-8') + ' From job ' + operation.current_job_id.name.encode(
                            'UTF-8') + ' To ' + operation.job_id.name.encode('UTF-8')+' Start Date'+operation.start_date,
                    })
                message_notif_obj.create(vals)

            ir_model_data = self.env['ir.model.data']
            try:
                template = ir_model_data.get_object_reference('saudi_hr', 'email_template_promotion')[1]
            except ValueError:
                template = False
            try:
                compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False
            ctx = dict()
            ctx.update({
                'default_model': 'hr.employee.promotion',
                'default_res_id': self.ids[0],
                'default_use_template': bool(template),
                'default_template_id': template,
                'default_composition_mode': 'comment',
                'default_partner_ids': [(6, 0, users)],
                'default_body': 'The employee has been promoted ' + operation.employee_id.name.encode(
                            'UTF-8') + ' From job ' + operation.current_job_id.name.encode(
                            'UTF-8') + ' To ' + operation.job_id.name.encode('UTF-8')+'Start Date '+operation.start_date,
            })
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,
            }

    def button_refuse(self):
        for operation in self:
            operation.state = 'refused'
