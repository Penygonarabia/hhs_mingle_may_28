# -*- coding: utf-8 -*-
from odoo import api, fields, models ,_
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import http
from odoo.exceptions import warnings, UserError, ValidationError



class AuhCustomWizard(models.TransientModel):
    _name = 'auh.custom.wizard'
    _description = 'Auh Custom Wizard'

    month_end_date = fields.Date(string="Month End Date", default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))


    def create_auh_gratuity_sheet(self):
        employee_ids = self.env['hr.employee'].search([('custom_gratuity_generate','=', True), ('joining_date', '<=', self.month_end_date)])
        journal_id = self.env['account.journal'].search([('custom_is_gratuity_journal', '=', True)],limit=1)
        if not journal_id:
            raise ValidationError(_('Configure Gratuity Journal on Accounting journals, Click on checkbox "Is Gratuity Journal?" to create.'))

        dates = date.today()
        previous_month = dates + relativedelta(day=1, months=-1)
        previous_month_last = dates + relativedelta(day=1, months=-1, days=-1)
        first_day = dates + relativedelta(day=1)
        last_day = dates + relativedelta(day=1, months=+1, days=-1)
        next_month_first = self.month_end_date.replace(day=1)
        next_month_last = dates + relativedelta(day=1, months=+2, days=-1)
        if (self.month_end_date >= first_day) and (self.month_end_date < last_day):
            raise ValidationError(_('Already gratuity has been created for the employees on the date %s')
                                      % (self.month_end_date.strftime("%d-%m-%Y")))
        if self.month_end_date < first_day:
            raise ValidationError(_('Previous Month Date should not be allowed. Only Current month alone can be allowed'))
        if self.month_end_date > last_day:
            raise ValidationError(_('Future Month Date should not be allowed. Only Current month alone can be allowed'))
        move_pool = self.env['account.move']

        move = {
                'date': last_day,
                'journal_id': journal_id.id,

                }
        custom_move = move_pool.create(move)
        for empl in employee_ids:
            contracts = empl._get_contracts(first_day, last_day)
            if not contracts:
                continue
            # custom_gratuity = self.env['mih.auh.gratuity.sheet'].search(
            #     [('custom_date_of_join', '=', empl.joining_date)])
            sheet_vals = {
                'custom_employee_id': empl.id,
                'custom_date_of_join': empl.joining_date if self.month_end_date == last_day else next_month_first,
                'custom_late_working_day': self.month_end_date,
                'custom_contract_id': contracts.id,
                'custom_basic_salary': contracts.wage,
                'custom_allowance': contracts.custom_allowance
            }
            custom_gratuity_id = self.env['mih.auh.gratuity.sheet'].create(sheet_vals)
            deb_interest_line = (0, 0, {
                'name': empl.name,
                'date': last_day,
                'partner_id': empl.address_id.id,
                'account_id': journal_id.default_debit_account_id.id,
                'journal_id':  journal_id.id,
                #'analytic_tag_ids' : [(6, 0, empl.contract_id.x_analytic_tag_ids.ids)],
                # 'analytic_account_id': empl.contract_id.analytic_account_id.id,
                'debit': custom_gratuity_id.custom_esob_amounts,
                'credit':0.0
            })
            cred_interest_line = (0, 0, {
                'name': empl.name,
                'date': last_day,
                'partner_id': empl.address_id.id,
                'account_id': journal_id.default_credit_account_id.id,
                'journal_id': journal_id.id,
#                'analytic_tag_ids' : [(6, 0, empl.contract_id.x_analytic_tag_ids.ids)],
#                 'analytic_account_id': empl.contract_id.analytic_account_id.id,
                'debit': 0.0,
                'credit': custom_gratuity_id.custom_esob_amounts
            })
            custom_move.write({
                'line_ids': [deb_interest_line, cred_interest_line],
                })
            custom_gratuity_id.write({
                'custom_move_id':custom_move.id,
                'custom_type': 'less_than_five_year' if custom_gratuity_id.no_of_days <= 1825 else 'greater_than_five_year',

            })

            dupl_empl = self.env['mih.auh.gratuity.sheet'].search([('id', '!=', custom_gratuity_id.id),
                                                                   ('custom_employee_id', '=', custom_gratuity_id.custom_employee_id.id),
                                                                   ('custom_late_working_day', '=', custom_gratuity_id.custom_late_working_day)])


            if self.month_end_date == dupl_empl.custom_late_working_day:
                raise ValidationError(_('Already gratuity has been created for the employees on the date %s')
                                      % (self.month_end_date.strftime("%d-%m-%Y")))


        auh_action = self.env.ref("hr_gratuity.action_auh_gratuity_custom").read()[0]
        try:
            auh_action['domain'] = [('id', 'in', custom_gratuity_id.ids)]
        except Exception as e:
            se = http.serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Not available any running employee contract.',
                'data': se
            }

        return auh_action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
