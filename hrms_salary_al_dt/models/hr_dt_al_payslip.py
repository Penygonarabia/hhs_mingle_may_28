# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, api, _


class SalaryRuleInput(models.Model):
    _inherit = 'hr.payslip'

    def get_inputs(self, contract_ids, date_from, date_to):
        """Compute the other inputs to employee payslip."""
        res = super(SalaryRuleInput, self).get_inputs(contract_ids, date_from, date_to)

        for contract_id in contract_ids.ids if hasattr(contract_ids, 'ids') else contract_ids:
            contract = self.env['hr.contract'].browse(contract_id)
            emp_id = contract.employee_id

            allow_salary = self.env['salary.allowance.detection'].search([
                ('employee_id', '=', emp_id.id),
                ('type', '=', 'transaction_allowance'),
                # ('date', '>=', date_from),
                # ('date', '<=', date_to),
                ('state', '=', 'approve'),
            ])

            for allowance in allow_salary:
                if allowance.date.month == date_from.month and allowance.date.year == date_from.year:
                    salary_rule = self.env['hr.salary.rule'].search([('code', '=', allowance.code)], limit=1)
                    date = ''
                    hours = ''
                    if allowance.days:
                        date = str(allowance.days)
                    if allowance.hours:
                        hours = str(allowance.hours)
                    input_data = {
                        'name': allowance.hr_transaction_id.display_name + " - " + (salary_rule.name if salary_rule else ''),
                        'code': allowance.code,
                        'contract_id': contract_id,
                        'amount': allowance.amount,
                        'date': allowance.date,
                        'reference': allowance.reference,
                        # 'units': (allowance.units + " - " + str(date or hours) if (
                        #         date or hours) else '') or allowance.units
                        # 'units': str(date or hours) + " / " + allowance.units if (
                        #         date or hours) else ''
                        'units': "{:.2f}".format(float(date or hours)) + " / " + allowance.units if (date or hours) else ''

                    }
                    res.append(input_data)


            detect_salary = self.env['salary.allowance.detection'].search([
                ('employee_id', '=', emp_id.id),
                ('type', '=', 'transaction_detection'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('state', '=', 'approve'),
            ])

            for detection in detect_salary:
                if detection.date.month == date_from.month and detection.date.year == date_from.year:
                    date = ''
                    hours = ''
                    if detection.days:
                        date = str(detection.days)
                    if detection.hours:
                        hours = str(detection.hours)
                    salary_rule = self.env['hr.salary.rule'].search([('code', '=', detection.code)], limit=1)
                    input_data = {
                        'name':  detection.hr_transaction_id.display_name + " - " + (salary_rule.name if salary_rule else ''),  # Include salary rule name
                        'code': detection.code,
                        'contract_id': contract_id,
                        'amount': detection.amount,
                        'date': detection.date,
                        'reference': detection.reference,
                        # 'units': (detection.units + " - " + str(date or hours) if (
                        #         date or hours) else '') or detection.units
                        # 'units': str(date or hours) + " / " + detection.units if (
                        #         date or hours) else ''

                        'units': "{:.2f}".format(float(date or hours)) + " / " + detection.units if (date or hours) else ''

                    }
                    res.append(input_data)

        return res

    # def get_inputs(self, contract_ids, date_from, date_to):
    #     """This Compute the other inputs to employee payslip.
    #                        """
    #     res = super(SalaryRuleInput, self).get_inputs(contract_ids, date_from, date_to)
    #     print('Res',res)
    #     contract_obj = self.env['hr.contract']
    #     emp_id = contract_obj.browse(contract_ids[0].id).employee_id
    #     print('Employee',emp_id)
    #     allow__salary = self.env['salary.allowance.detection'].search([
    #         ('employee_id', '=', emp_id.id),
    #         ('type', '=', 'transaction_allowance'),
    #     ])
    #     detect_salary = self.env['salary.allowance.detection'].search([
    #         ('employee_id', '=', emp_id.id),
    #         ('type', '=', 'transaction_detection'),
    #     ])
    #     print("Allowance Salary:", allow__salary)
    #     print("Detection Salary:", detect_salary)
    #     # transaction_salary = self.env['salary.allowance.detection'].search([
    #     #     ('employee_id', '=', emp_id.id),
    #     #     ('type', '=', 'transaction'),
    #     # ])
    #
    #     for all_obj in allow__salary:
    #         current_date = date_from.month
    #         date = all_obj.date
    #         existing_date = date.month
    #         print('Allowance Salary',allow__salary)
    #         if current_date == existing_date:
    #             state = all_obj.state
    #             amount = all_obj.amount
    #             code  = all_obj.code
    #             print('State',state)
    #             print('Amount',amount)
    #             print('Code',code)
    #             for result in res:
    #                 if state == 'approve' and amount != 0 and result.get('code') == code:
    #                     result['amount'] = amount
    #                     print('Result',result)
    #
    #     for detect_obj in detect_salary:
    #         current_date = date_from.month
    #         date = detect_obj.date
    #         existing_date = date.month
    #         if current_date == existing_date:
    #             state = detect_obj.state
    #             amount = detect_obj.amount
    #             code = detect_obj.code
    #             for result in res:
    #                 if state == 'approve' and amount != 0 and result.get('code') == code:
    #                     result['amount'] = amount
    #
    #     # for detect_obj in transaction_salary:
    #     #     current_date = date_from.month
    #     #     date = detect_obj.date
    #     #     existing_date = date.month
    #     #     if current_date == existing_date:
    #     #         state = detect_obj.state
    #     #         amount = detect_obj.amount
    #     #         code = detect_obj.code
    #     #         for result in res:
    #     #             if state == 'approve' and amount != 0 and result.get('code') == code:
    #     #                 result['amount'] = amount
    #     #
    #
    #
    #     return res
