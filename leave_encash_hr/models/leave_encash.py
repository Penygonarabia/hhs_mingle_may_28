from odoo import api, fields, models, _
from datetime import datetime,date,time
from odoo.exceptions import ValidationError,UserError
from dateutil.relativedelta import relativedelta
from lxml import etree
import json
import logging

_logger = logging.getLogger(__name__)


class leave_encash(models.Model):
    _name = 'leave.encash'
    _description = 'Leave Encash'
    _order = 'id desc'

    name = fields.Char('Reference')
    employee_id = fields.Many2one("hr.employee", string="Employee")
    department_id = fields.Many2one("hr.department", string="Department")
    job_id = fields.Many2one("hr.job", string="Job Position")
    leave_carry = fields.Float(string="Total Employee Leave Have")
    date = fields.Date(string="Date", default = datetime.today())
    amount = fields.Float(string="Amount", default = 0.0)

    # amount = fields.Float(string="Amount",compute="_compute_encash_amount" , default = 0.0)
    leave_type_id = fields.Many2one("hr.leave.type", string="Leave Type")
    state = fields.Selection([('draft', 'Draft'),
                               ('request', 'Waiting for Direct Manager approval'),
                                ('progress', 'Waiting for HR Manager approval'),
                                ('progress2', 'Waiting for Finance Manager approval'),
                                ('progress3', 'Waiting for Admin & Financial Director approval'),
                              ('approved', 'Approved'),
                              ('paid', 'Paid'),
                              ('canceled', 'Cancelled')], default='draft')
    days_want = fields.Float(string="Applied En-cash Day Leave")
    
    particular_total_leave = fields.Float(string="Total Allocation for Particular TimeOff", help = "Total Allocation for Particular employee in a Company")
    
    contract_id = fields.Many2one('hr.contract',string="Contract")
    
    company_id = fields.Many2one('res.company',string='Company', default=lambda self: self.env.user.company_id)
    
    payslip_id = fields.Many2one("hr.payslip", string="Payslip" , compute="_compute_payslip")
    
    payslip_bool = fields.Boolean('Payslip Bool',default=False,help="If Payslip done,it will automatically comes True then it will reduce the leave allocation of particular employee")
    
    
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

    leave_deducted = fields.Boolean(string="Leave Deducted", default=False)

    # Add a Boolean field to indicate if the action_progress3 button has been clicked
    is_progress3_clicked = fields.Boolean(string="Action Progress3 Clicked", default=False)

    leave_calculation = fields.Selection(string="Calculate Based On",
                                                    selection=[('wage','Wage'),
                                                                ('hra', 'Wage + HRA'), 
                                                                ('hra_trv', 'Wage + HRA + Travel'),
                                                               ('wage_tr_fd','Basic + Transport + Food'),
                                                               ('hr_tr_sch', 'Wage + HRA + Travel + School'),
                                                               ('hr_tr_fd', 'Wage + HRA + Travel + Food'),
                                                               ('hr_tr_fl', 'Wage + HRA + Travel + Fuel'),
                                                               ('hr_tr_tk', 'Wage + HRA + Travel + Ticket'),
                                                               ('hr_tr_fx', 'Wage + HRA + Travel + Fixed'),
                                                               ('hr_tr_mb', 'Wage + HRA + Travel + Mobile'),
                                                               ('hr_tr_oth', 'Wage + HRA + Travel + Other'),
                                                               ('hr_tr_wk', 'Wage + HRA + Travel + Work'), ('all', 'All')])
    
    
    employee_number = fields.Char(string='Employee No', store = True)
    
    
    @api.onchange('employee_id')
    def _onchange_employ(self):
        for rec in self:
            rec.employee_number = False
            if rec.employee_id:
                rec.employee_number = rec.employee_id.employee_no
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        if self.env.user:
            if self.env.user.has_group('hr_saudi.group_sys_manager'):
                return super(leave_encash, self).search(args, offset=offset, limit=limit, order=order)
            if self.env.user.has_group('hr_saudi.group_normal_employee'):
                args += [('employee_id.user_id', '=', self.env.user.id)]
                return super(leave_encash, self).search(args, offset=offset, limit=limit, order=order)
            if self.env.user.has_group('hr_saudi.group_dm'):
                args += [('state', '=', 'request')]
                return super(leave_encash, self).search(args, offset=offset, limit=limit, order=order)

            if self.env.user.has_group('hr_saudi.group_hrm'):
                args += [('state', '=', 'progress')]
                return super(leave_encash, self).search(args, offset=offset, limit=limit, order=order)
            if self.env.user.has_group('hr_saudi.group_finance_manager'):
                args += [('state', '=', 'progress2')]
                return super(leave_encash, self).search(args, offset=offset, limit=limit, order=order)
            if self.env.user.has_group('hr_saudi.group_admin_approval'):
                args += [('state', '=', 'progress3')]
                print("args", args)
                return super(leave_encash, self).search(args, offset=offset, limit=limit, order=order)

        return super(leave_encash, self).search(args, offset=offset, limit=limit, order=order)


    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(leave_encash, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
    #                                                    submenu=submenu)
    #     if view_type == 'form':
    #         try:
    #             doc = etree.XML(res['arch'])
    #             buttons_to_hide = ['action_request', 'action_progress', 'action_progress2', 'action_approve']
    #             button_to_show = 'action_progress3'
    #             state = 'state'
    #
    #             if self.env.user.has_group('hr_saudi.group_sys_manager'):
    #                 for button_name in buttons_to_hide:
    #                     for node in doc.xpath("//button[@name='%s']" % button_name):
    #                         modifiers = json.loads(node.get("modifiers", "{}"))
    #                         modifiers['invisible'] = True
    #                         node.set("modifiers", json.dumps(modifiers))
    #                         node.set("invisible", "1")
    #
    #                 for node in doc.xpath("//button[@name='%s']" % button_to_show):
    #                     modifiers = json.loads(node.get("modifiers", "{}"))
    #                     modifiers['invisible'] = False
    #                     print("modifiers['invisible']", modifiers['invisible'])
    #                     node.set("modifiers", json.dumps(modifiers))
    #                     print("node", node)
    #                     node.set("invisible", "0")
    #
    #             res['arch'] = etree.tostring(doc, encoding='unicode')
    #         except Exception as e:
    #             _logger.error("Error while modifying field view: %s", e)
    #     return res

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(leave_encash, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                       submenu=submenu)

        if view_type == 'form':
            try:
                doc = etree.XML(res['arch'])
                buttons_to_hide = ['action_request', 'action_progress', 'action_progress2', 'action_approve']
                button_to_show = 'action_progress3'

                if self.env.user.has_group('hr_saudi.group_sys_manager'):
                    for button_name in buttons_to_hide:
                        for node in doc.xpath("//button[@name='%s']" % button_name):
                            modifiers = json.loads(node.get("modifiers", "{}"))
                            modifiers['invisible'] = True
                            node.set("modifiers", json.dumps(modifiers))
                            node.set("invisible", "1")

                    # Check if action_progress3 button has been clicked
                    for node in doc.xpath("//button[@name='%s']" % button_to_show):
                        modifiers = json.loads(node.get("modifiers", "{}"))
                        modifiers['invisible'] = [('is_progress3_clicked', '=', True)]
                        node.set("modifiers", json.dumps(modifiers))
                        node.set("invisible", "1")
                res['arch'] = etree.tostring(doc, encoding='unicode')
            except Exception as e:
                _logger.error("Error while modifying field view: %s", e)
        return res

    def action_request(self):
        if self.days_want == 0.00:
            raise UserError('Please Enter the Days You want to encash your leave')
        elif self.days_want > self.leave_type_id.maximum_allowed_days:
            raise ValidationError('Please enter below maximum allowed days of your selected Leave Type ')
        elif self.days_want > self.particular_total_leave:
            raise ValidationError('Please enter below total allocation for particular total type')
        else:
            self.write({'state': 'request'})

    def action_progress(self):
        self.write({'state': 'progress', 'd_manager': self.env.uid})

    def action_progress2(self):
        self.write({'state': 'progress2', 'hr_manage_id': self.env.uid})

    def action_approve(self):
        self.write({'state': 'progress3', 'account_manage_id': self.env.uid})

    def action_progress3(self):
        if not self.state in ['approved', 'paid', 'canceled']:
            self.is_progress3_clicked = True
            if self.days_want == 0.00:
                raise UserError('Please Enter the Days You want to encash your leave')
            elif self.days_want > self.leave_type_id.maximum_allowed_days:
                raise ValidationError('Please enter below maximum allowed days of your selected Leave Type ')
            elif self.days_want > self.particular_total_leave:
                raise ValidationError('Please enter below total allocation for particular total type')
            else:
                self.write({'state': 'approved', 'admin_manager_id': self.env.uid})


    def action_draft(self):
        return self.write({'state': 'draft'})
    
    # @api.constrains('days_want')
    # def _check_days_want(self):
    #     for rec in self:
    #         if rec.days_want == 0:
    #             raise ValidationError('Please Enter the Days Amount')
    
    @api.constrains('employee_id','leave_type_id') 
    def _check_constrains_leave_encash(self):
        current_date = fields.Date.today()
        current_year_start = current_date.replace(month=1, day=1)
        current_year_end = current_date.replace(month=12, day=31)
        for rec in self:
            leave_type = self.env['hr.leave.type'].search([('is_leave_encash','=',True),('code','=',rec.leave_type_id.code)],limit=1)
            leave_type.maximum_allowed_days
    
            leave_search = self.env['leave.encash'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', current_year_start),
                ('date', '<=', current_year_end),
                ('leave_type_id','=',rec.leave_type_id.id)
            ])
            encash_applied = 0.0
            for leave in leave_search:
                encash_applied += leave.days_want
            if encash_applied >leave_type.maximum_allowed_days :
            # if len(leave_search) >1:
                raise ValidationError("Applied leave encash not more than that of applied leave type id")
    

    
    
    @api.model
    def _compute_payslip(self):
        for rec in self:
            rec.payslip_id = False
            rec.payslip_bool = False
            payslip = self.env['hr.payslip'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'done'),
                ('date_from', '<=', rec.date),
                ('date_to', '>=', rec.date)
            ], limit=1)
            if payslip:
                rec.payslip_id = payslip.id
                rec.payslip_bool = True
                self.state = 'paid'
                if rec.payslip_id and rec.state == 'paid' and not rec.leave_deducted:
                    if rec.payslip_bool:
                        leave_search_allocation = self.env['hr.leave.allocation'].search([
                            ('employee_id', '=', rec.employee_id.id),
                            ('state', '=', 'validate'),
                            ('holiday_status_id', '=', rec.leave_type_id.id)
                        ], limit=1)
                        if leave_search_allocation:
                            leave_search_allocation.number_of_days -= rec.days_want
                            rec.leave_deducted = True
    
    # @api.model
    # def _compute_payslip(self):
    #     for rec in self:
    #         rec.payslip_id = False
    #         rec.payslip_bool = False
    #         payslip = self.env['hr.payslip'].search([
    #                 ('employee_id', '=', rec.employee_id.id),
    #                 ('state', '=', 'done'),
    #                 ('date_from', '<=', rec.date),
    #                 ('date_to', '>=', rec.date)
    #             ], limit=1)
    #         if payslip:
    #             rec.payslip_id = payslip.id
    #             rec.payslip_bool = True
    #             self.state ='paid'
    #             if rec.payslip_id and rec.state =='paid':
    #
    #                 if rec.payslip_bool :
    #
    #                     print("...........................11111111111")
    #                     leave_search_allocation = self.env['hr.leave.allocation'].search([
    #                         ('employee_id', '=', rec.employee_id.id),
    #                         ('state', '=', 'validate'),
    #                         ('holiday_status_id', '=', rec.leave_type_id.id)
    #                     ], limit=1) 
    #                     leave_search_allocation.number_of_days -= rec.days_want


    # @api.depends('payslip_id')
    # def _compute_payslip_bool(self):
    #     for rec in self:
    #         print("...........11222222222222222222222222222")
    #         if rec. payslip_id:
    #             rec.payslip_bool =True 
    #             print("............rec.",rec.payslip_bool)
    #             if rec.payslip_id and rec.state =='paid':
    #
    #                 if rec.payslip_bool :
    #
    #                     print("...........................11111111111")
    #                     leave_search_allocation = self.env['hr.leave.allocation'].search([
    #                         ('employee_id', '=', rec.employee_id.id),
    #                         ('state', '=', 'validate'),
    #                         ('holiday_status_id', '=', rec.leave_type_id.id)
    #                     ], limit=1)
    #
    #
    #                     print("...........leave", leave_search_allocation.number_of_days)
    #                     leave_search_allocation.number_of_days -= rec.days_want
                        # leave_search_allocation._compute_number_of_days_display()  # Recompute display fields if needed
                        # print("................la", leave_search_allocation.number_of_days)
                        # rec.leave_days_updated = True 
            # rec.payslip_bool = False
                # if rec.state=='paid':
                #     rec.payslip_bool = True
                #     if rec.payslip_bool:
                #         print("...........................11111111111")
                #         leave_search_allocation = self.env['hr.leave.allocation'].search([('employee_id','=',rec.employee_id.id),('state', '=', 'validate'),('holiday_status_id', '=', rec.leave_type_id.id)],limit=1)  
                #             # for leave in leave_search_allocation:
                #         print("...........leave",leave_search_allocation.number_of_days)    
                #         leave_search_allocation.number_of_days -= rec.days_want
                #         print("................la",leave_search_allocation.number_of_days)
                #         rec.payslip_bool = False
            
    
    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('leave.encash') or ' '
        res = super(leave_encash, self).create(values)
        return res
    
    @api.onchange("employee_id")
    def _onchange_employee(self):
        for rec in self:
            if rec.employee_id:
                rec.department_id = rec.employee_id.department_id.id or False
                rec.job_id = rec.employee_id.job_id.id or False
                rec.contract_id = rec.employee_id.contract_id.id or False
                rec.leave_carry = rec.employee_id.remaining_leaves
                # print("...........allocation",rec.employee_id.allocation_count,rec.employee_id.allocations_count,rec.employee_id.allocation_display,rec.employee_id.allocation_used_display)
                # print("............................leave..",rec.employee_id.remaining_leaves)
                # print(".////////////////leave count",rec.employee_id.leaves_count,rec.employee_id.allocation_used_display,rec.employee_id.allocation_display)
                # # rec.leave_carry = rec.employee_id.number_of_days
                # print('employee_ idddddddddddddd', rec.employee_id.current_leave_id.name)
            
            
    @api.onchange('leave_calculation')
    # @api.depends('employee_id','leave_carry','days_want','leave_calculation')
    def _compute_encash_amount(self):
        for rec in self:
            rec.amount = False
            if rec.employee_id:
                if rec.employee_id.contract_id:
                    if rec.leave_calculation:
                        amount = 0
                        if rec.leave_calculation == 'wage':
                            amount = rec.employee_id.contract_id.wage
                            # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day
                        elif rec.leave_calculation == 'hra':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance
                                # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day
                            
                            
                        elif rec.leave_calculation == 'hra_trv':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.transport_allowance
                            # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day
                            
                        elif rec.leave_calculation == 'wage_tr_fd':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.transport_allowance + rec.employee_id.contract_id.food_allowance
                                # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day    
                            
                        elif rec.leave_calculation == 'hr_tr_sch':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.school_allowance
                                # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day
                            
                            
                        elif rec.leave_calculation == 'hr_tr_fd':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance +  rec.employee_id.contract_id.transport_allowance + rec.employee_id.contract_id.food_allowance
                                # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day
                        
                        elif rec.leave_calculation == 'hr_tr_fl':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.fuel_allowance +  rec.employee_id.contract_id.transport_allowance
                                # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day    
                            
                        elif rec.leave_calculation == 'hr_tr_tk':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.ticket_allowance +  rec.employee_id.contract_id.transport_allowance
                            # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day
                            
                        elif rec.leave_calculation == 'hr_tr_fx':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.fixed_allowance +  rec.employee_id.contract_id.transport_allowance
                                # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day    
                                
                        elif rec.leave_calculation == 'hr_tr_mb':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.mobile_allowance +  rec.employee_id.contract_id.transport_allowance
                                # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day
                            
                            
                        elif rec.leave_calculation == 'hr_tr_oth':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance +rec.employee_id.contract_id.housing_allowance  +  rec.employee_id.contract_id.transport_allowance
                            # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day
                        elif rec.leave_calculation == 'hr_tr_wk':
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance +  rec.employee_id.contract_id.transport_allowance +  rec.employee_id.contract_id.work_allowance
                                # print("..............amount",amount)
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day     
                        else:
                            amount = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.transport_allowance +rec.employee_id.contract_id.school_allowance + rec.employee_id.contract_id.food_allowance + rec.employee_id.contract_id.fuel_allowance + rec.employee_id.contract_id.ticket_allowance+ rec.employee_id.contract_id.fixed_allowance + rec.employee_id.contract_id.mobile_allowance + rec.employee_id.contract_id.work_allowance +rec.employee_id.contract_id.housing_allowance
                                    
                            one_day = amount /30
                            rec.amount = rec.days_want * one_day 
                            
                    # print(".......aaaaaaa",rec.amount)
                    
                    
    @api.onchange("leave_type_id")
    def _onchange_leave_type(self):
        for rec in self:
            allot_days = 0.0
            leave_days = 0.0
            if rec.employee_id and rec.leave_type_id:
                leave_allocation_search = self.env['hr.leave.allocation'].search([('employee_id','=',rec.employee_id.id),('holiday_status_id','=',rec.leave_type_id.id),('state','=','validate')])
                
                leave_search = self.env['hr.leave'].search([('employee_id','=',rec.employee_id.id),('holiday_status_id','=',rec.leave_type_id.id),('state','=','validate')])
                
                for allocate in leave_allocation_search :
                    allot_days += allocate.number_of_days
                for leave in leave_search:
                    leave_days += leave.number_of_days
                rec.particular_total_leave = allot_days - leave_days
                # rec.particular_total_leave = leave_allocation_search.number_of_days_display
                # print("............particular",rec.particular_total_leave,leave_allocation_search.number_of_days_display)
                
    
    
    # def leave_approve(self):
    #     for rec in self:
    #
    #         # leave_search = self.env['hr.leave']
    #         # val_lst=[]
    #         # holiday_type = 'employee'
    #         # vals = {
    #         #
    #         #     'holiday_status_id': rec.leave_type_id.id,
    #         #     'employee_ids':[(4, rec.employee_id.id)],
    #         #     'number_of_days':rec.days_want,
    #         #     'holiday_type':holiday_type,
    #         #     'name':'Encash-Leave',
    #         #     'request_date_from': rec.date,
    #         #     'request_date_to': rec.date + relativedelta(days=self.days_want),
    #         #     'category_id': rec.contract_id.id,
    #         #     'department_id':rec.department_id.id,
    #         #     'mode_company_id':rec.company_id.id
    #         #     }
    #         # val_lst.append(vals)
    #         # print("....................vals",val_lst)
    #         # leave_approve=leave_search.create(val_lst)
    #         # leave_approve.action_approve()
    #
    #
    #
    #         payslip_search=self.env['hr.payslip'].search([('employee_id','=',self.employee_id.id)])
    #
    #         for payslip in payslip_search:
    #             if payslip.date_from <= self.date <= payslip.date_to:
    #                 if payslip.state =='draft':
    #                     print(".....222222222..",payslip.name)
    #             else:
    #                 print(".........111111111111")
    #                 # self.env['hr.payslip'].create()
    #
    #


    # def approve(self):
    #     if self.days_want == 0.00:
    #         raise ValidationError('Please Enter the Days You want to encash your leave')
    #     elif self.days_want > self.leave_type_id.maximum_allowed_days :
    #         raise ValidationError('Please enter below maximum allowed days of your selected Leave Type ')
    #     elif self.days_want > self.particular_total_leave:
    #         raise ValidationError('Please enter below total allocation for particular total type')
    #
    #     else:
    #         self.state = 'approved'
    #

                

        
        

    def cancel(self):
        self.state = 'canceled'

    def unlink(self):
        for each in self:
            if each.state == 'paid':
                raise ValidationError(_("You cannot delete Paid records"))
        return super(leave_encash, self).unlink()