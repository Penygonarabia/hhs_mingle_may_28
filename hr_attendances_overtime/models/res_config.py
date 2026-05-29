# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # regular_grace_time = fields.Float(string='Regular Grace Time in Minutes',config_parameter  = "hr_attendances_overtime.regular_grace_time")
    # executive_grace_time = fields.Float(string='Executive Grace Time in Minutes',config_parameter  = "hr_attendances_overtime.executive_grace_time")
    #

    late_in_calculation = fields.Boolean(string ="Late in Calculation" , default = False,
                                    config_parameter  = "hr_attendances_overtime.late_in_calculation")
    
    
    early_out_calculation = fields.Boolean(string = "Early out Calculation", default = False,
                                           config_parameter = "hr_attendances_overtime.early_out_calculation")
    
    
    overtime_calculation = fields.Boolean(string = "Overtime Calculation", default = False, 
                                          config_parameter = "hr_attendances_overtime.overtime_calculation")
    
    absence_calculation = fields.Boolean (string = "Absence Calculation", default = False,
                                          config_parameter = "hr_attendances_overtime.absence_calculation")


    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        # self.env['ir.config_parameter'].sudo().set_param(
        #     'hr_attendances_overtime.regular_grace_time', self.regular_grace_time)
        # self.env['ir.config_parameter'].sudo().set_param(
        #     'hr_attendances_overtime.executive_grace_time', self.executive_grace_time)
        #

        
        self.env['ir.config_parameter'].sudo().set_param('hr_attendances_overtime.late_in_calculation', self.late_in_calculation)
        self.env['ir.config_parameter'].sudo().set_param('hr_attendances_overtime.early_out_calculation', self.early_out_calculation)
        self.env['ir.config_parameter'].sudo().set_param('hr_attendances_overtime.overtime_calculation', self.overtime_calculation)
        self.env['ir.config_parameter'].sudo().set_param('hr_attendances_overtime.absence_calculation', self.absence_calculation)
        

        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            # regular_grace_time = params.get_param('hr_attendances_overtime.regular_grace_time'),
            # executive_grace_time = params.get_param('hr_attendances_overtime.executive_grace_time'),
            late_in_calculation = params.get_param('hr_attendances_overtime.late_in_calculation'),
            early_out_calculation = params.get_param('hr_attendances_overtime.early_out_calculation'),
            overtime_calculation = params.get_param ('hr_attendances_overtime.overtime_calculation'),
            absence_calculation = params.get_param ('hr_attendances_overtime.absence_calculation'),
           
        )
        print("...............res", res['late_in_calculation'], res['early_out_calculation'],res['overtime_calculation'], res['absence_calculation'])
        return res