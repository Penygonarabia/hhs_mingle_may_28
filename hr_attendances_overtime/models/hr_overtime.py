# See LICENSE file for full copyright and licensing details

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrOvertime(models.Model):
    """Overtime Model."""

    _name = 'hr.attendances.overtime'
    _description = "Hr Attendance Overtime"

    name = fields.Char(string="Name")

    overtime_line_ids = fields.One2many(
        'hr.overtime.line',
        'overtime_id',
        string='OvertimeLine',
    )

    # def name_get(self):
    #     result = []
    #     ctx = self._context or {}
    #     if 'attendance_policy' in ctx:
    #         for overtime in self:
    #             name = overtime.name
    #             result.append((overtime.id, name))
    #         return result
    #     return super(HrOvertime, self).name_get()
    
    # def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
    #     ctx = self._context or {}
    #     if 'attendance_policy' in ctx:
    #         args += [('name','!=',False)]
    #     return super(HrOvertime, self)._search(args=args, offset=offset, limit=limit, order=order, count=count,
    #                                                  access_rights_uid=access_rights_uid)    

class OvertimeLine(models.Model):
    """Overtime Line."""

    _name = 'hr.overtime.line'
    _description = "Hr Attendance Overtime Line"
    _order = 'apply_after desc'

    overtime_id = fields.Many2one("hr.attendances.overtime",
                                  string="Overtime")
    name = fields.Char("Name")
    policie_type = fields.Selection([('working_days', 'Working days'),
                                     ('week_end', 'Weekend')],
                                     # ('holiday', 'Holiday')],
                                    string="Type")
    rate = fields.Float("RATE(%)/Day")
    apply_after = fields.Float(string="Apply after")
    
    payroll_transaction_id = fields.Many2one('hr.transaction.entry',string="Overtime Payroll Transaction")


    @api.constrains('name','policie_type','payroll_transaction_id')
    def Validate_name(self):
        for rec in self:
            if rec.rate:
                if rec.rate > 0:
                    # if not (rec.name or rec.policie_type or rec.payroll_transaction_id ):
                    if not rec.name:
                        raise ValidationError("Please Add some Name in the name field.Because the rate/day > 0")
                    if not rec.policie_type:
                        raise ValidationError("Please select Type.It is mandatory when the rate/day > 0")
                    # if not rec.payroll_transaction_id:
                    #     raise ValidationError("Please select Payroll Transaction Field.It is mandatory when the rate/day > 0 ")
                        
    # @api.constrains('policie_type', 'rate', 'apply_after')
    # def _validation_overtime_line(self):
    #     for rec in self:
    #         overtime_ids = rec.search([('rate', '=', rec.rate),
    #                                    ('apply_after', '=',
    #                                     rec.apply_after),
    #                                    ('policie_type', '=',
    #                                     rec.policie_type),
    #                                    ('id', '!=', rec.id)])
    #         if overtime_ids:
    #             raise ValidationError(
    #                 _("Record already exists with name %s !!!") % (rec.name))


class Lateinrules(models.Model):
    """Late In Rule."""

    _name = 'hr.attendance.late'
    _description = "Hr Attendance Late"

    name = fields.Char("Name", required="True")
    attendance_line_ids = fields.One2many(
        "hr.attendance.late.line", "name_id")


class Lateinrulesline(models.Model):
    """Late In Rule Line."""

    _name = 'hr.attendance.late.line'
    _order = 'time desc'
    _description = "Hr Attendance Late Line"

    name_id = fields.Many2one("hr.attendance.late", string="Name")
    time = fields.Float("Time")
    amount_type = fields.Selection([('fixed', 'Fixed'),
                                    ('rate', 'Rate')],
                                   string="Type", default='rate')
    amount = fields.Float(string="Amount")
    rate = fields.Float(string="RATE(%)/Day ")
    
    # for_time_rate = fields.Selection([('1','For ')],string="For Time Rate")
    num_of_times = fields.Selection(
        selection=[
            ('1', 'First'),
            ('2', 'Second'),
            ('3', 'Third'),
            ('4', 'Fourth'),
        ],
        string="Num.of Times",
        required=True,
    )

    latein_transaction_id = fields.Many2one('hr.transaction.entry',string="Latein Payroll Transaction")

    
    @api.constrains('time','amount_type','num_of_times')
    def validity_check(self):
        for rec in self:
            if rec.amount_type=='rate':
                if rec.rate > 0:
                    if not rec.num_of_times:
                        raise ValidationError("Please select the Num. of Times.Because rate > 0")
            if rec.amount_type =='fixed':
                if rec.rate > 0:
                    if not rec.num_of_times:
                        raise ValidationError("Please select Num.of Times.Because Rate>0")     
                    
                
    # @api.constrains('time', 'amount_type', 'rate')
    # def _validation_latein_line(self):
    #     for rec in self:
    #         latein_ids = rec.search([('rate', '=', rec.rate),
    #                                  ('amount_type', '=',
    #                                   rec.amount_type),
    #                                  ('time', '=',
    #                                   rec.time),
    #                                  ('id', '!=', rec.id)])
    #         if latein_ids:
    #             raise ValidationError(_("Record already exists!!!"))


# for the absence Rule


class Absence(models.Model):
    """Absence Model."""

    _name = 'hr.attendance.absence'
    _description = "Hr Attendance absence"

    name = fields.Char("Name", required="True")
    absence_line_ids = fields.One2many(
        "hr.attendance.absence.line", "name_id", "absence line")

    # @api.constrains('name')
    # def _check_absence(self):
    #     for absence in self:
    #         absence_ids = absence.search([
    #             ('name', '=', absence.name),
    #             ('id', '!=', absence.id), ])
    #         if absence_ids:
    #             raise ValidationError("Record already exists!!!")


class Absenceline(models.Model):
    """Absence Line."""

    _name = 'hr.attendance.absence.line'
    _order = 'time asc'
    _description = "Hr Attendance absence line"

    name_id = fields.Many2one("hr.attendance.absence", string="Name")

    time = fields.Selection([('1', 'First Time'),
                             ('2', 'Second Time'),
                             ('3', 'Third Time'),
                             # ('4', 'Fourth Time'),
                             # ('5', 'Fifth Time'),
                             # ('6', 'Sixth Time'),
                             # ('7', 'Seventh Time'),
                             # ('8', 'Eighth Time'),
                             # ('9', 'Ninth Time'),
                             ])
    rate = fields.Float("RATE(%)/Day ")
    
    absent_payroll_transaction_id = fields.Many2one('hr.transaction.entry', string="Absent Payroll Transaction")


    @api.constrains('time','absent_payroll_transaction_id')
    def _validty_check(self):
        for rec in self:
            if rec.rate:
                if rec.rate > 0:
                    if not rec.time:
                        raise ValidationError("Please Select Time Fields.Because it is Mandatory")
                    
                    # if not rec.absent_payroll_transaction_id:
                    #     raise ValidationError("Please select Absent Payroll Transaction")
    # @api.constrains('time', 'rate')
    # def _validation_absence_line(self):
    #     for rec in self:
    #         latein_ids = rec.search([('rate', '=', rec.rate),
    #                                  ('time', '=',
    #                                   rec.time),
    #                                  ('id', '!=', rec.id)])
    #         if latein_ids:
    #             raise ValidationError(
    #                 _("Record already exists with %s !!!") % dict(
    #                     rec._fields['time'].selection).get(rec.time))

class EarlyOut(models.Model):
    
    _name = "hr.attendance.earlyout"
    _description = "Early Check Out"
    
    name = fields.Char('Name', required=True)
    
    early_checkout_line_ids = fields.One2many('hr.attendance.earlyout.line', 'early_id', string="Early Out Line")
    
    
class EarlyOutLine(models.Model):
    
    _name = 'hr.attendance.earlyout.line'
    _description = "Early checkout line"
    
    early_id = fields.Many2one('hr.attendance.earlyout', string="Name")
    
    early_time = fields.Selection([('1','First Time'), ('2', 'Second Time'), ('3', 'Third Time'), ('4', 'Fourth Time')]
                                  , string="Num.of Times")
    
    early_rate = fields.Float(string="RATE(%)/Day ")
    
    time = fields.Float("Time")
    
    earlyout_transaction_id = fields.Many2one('hr.transaction.entry', string="Earlyout Payroll Transaction")
    
    @api.constrains('early_time')
    def _validty_early_rate(self):
        for rec in self:
            if rec.early_rate:
                if rec.early_rate > 0:
                    if not rec.early_time:
                        raise ValidationError("Please Select Time Fields.Because it is Mandatory")
                    
                   

class Diffrules(models.Model):
    """Time Differernt Model."""

    _name = 'hr.attendance.diff'
    _description = "Hr Attendance Diffrules"

    name = fields.Char("Name", required="True",)
    diff_line_ids = fields.One2many(
        "hr.attendance.diff.line", "name_id",)
    
    

class Diffrulesline(models.Model):
    """Time Different Line."""

    _name = 'hr.attendance.diff.line'
    _order = 'time desc'
    _description = "Hr Attendance diff line"

    name_id = fields.Many2one("hr.attendance.diff", string="Name")
    time = fields.Float("Time")
    rate = fields.Float("RATE(%)/Day")

    @api.constrains('time')
    def _validty_early_rate(self):
        for rec in self:
            if rec.rate :
                if rec.rate > 0:
                    if not rec.time :
                        raise ValidationError("Please Select Time Fields.Because it is Mandatory")
                    
    
    # @api.constrains('time', 'rate')
    # def _validation_different_line(self):
    #     for rec in self:
    #         diff_ids = rec.search([('rate', '=', rec.rate),
    #                                ('time', '=',
    #                                 rec.time),
    #                                ('id', '!=', rec.id)])
    #         if diff_ids:
    #             raise ValidationError(_("Record already exists!!!"))
