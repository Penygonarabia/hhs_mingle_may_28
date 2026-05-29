# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class UpdateAccruedLeave(models.Model):

    _name = 'update.accrued.leave'
    _rec_name = 'employee_id'
    _description = 'Update Accrued Leave Days/Tickets'
    # _inherit = ['mail.thread.cc', 'mail.activity.mixin', 'rating.mixin']

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    leave_ticket = fields.Selection([('leave', 'Leave'), ('ticket', 'Ticket')],
                                 string='Leave/Ticket', required=True)
    type_of_adjustment = fields.Selection([('b/f_wd', 'B/F-wd'), ('adjustment', 'Adjustment'), ('utilised', 'Utilised')], string='Type Of Adjustment', required=True)
    no_of_tickets = fields.Float(string='No.of Days/Tickets', required=True)


    employee_no = fields.Char(string="Employee No",store=True)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        for rec in self:
            rec.employee_no = rec.employee_id.employee_no or False
    
    
    @api.onchange('no_of_tickets', 'type_of_adjustment', 'no_of_tickets','employee_id','leave_ticket')
    def change_adjustment(self):
        emp_obj = self.env['hr.employee'].search([('id', '=', self.employee_id.id)],limit=1)
        
        if self.type_of_adjustment == 'b/f_wd' and self.leave_ticket == 'leave':
            emp_obj.write({'bfwd_previous_year' : self.no_of_tickets})
        elif self.type_of_adjustment == 'b/f_wd' and self.leave_ticket == 'ticket':
            emp_obj.write({'bfwd_previous_year_ticket': self.no_of_tickets})
        elif self.type_of_adjustment == 'adjustment' and self.leave_ticket == 'leave':
            emp_obj.write({'adjustments' : self.no_of_tickets})
        elif self.type_of_adjustment == 'adjustment' and self.leave_ticket == 'ticket':
            emp_obj.write({'adjustments_ticket' : self.no_of_tickets})
        elif self.type_of_adjustment == 'utilised' and self.leave_ticket == 'leave':
            emp_obj.write({'utilised_this_year' : self.no_of_tickets})
        elif self.type_of_adjustment == 'utilised' and self.leave_ticket == 'ticket':
            emp_obj.write({'utilised_this_year_ticket' : self.no_of_tickets})

    @api.constrains('no_of_tickets')
    def _check_float_field(self):
        for record in self:
            try:
                # Attempt to cast the field to a float to ensure it's a valid float number
                float(record.no_of_tickets)
            except (TypeError, ValueError):
                raise ValidationError("The value for Float Field must be a valid float number.")
            
            
    @api.constrains('employee_id','leave_ticket','type_of_adjustment')
    def _check_constarains_employee(self):
        for rec in self:
            search_leave = self.env['update.accrued.leave'].search([('employee_id','=',rec.employee_id.id),('leave_ticket','=',rec.leave_ticket),
                                                                    ('type_of_adjustment','=',rec.type_of_adjustment)])
            if len(search_leave)>1:
                raise ValidationError('Already Employee %s is used for Leave/Ticket. ' %rec.employee_id.name)
           
