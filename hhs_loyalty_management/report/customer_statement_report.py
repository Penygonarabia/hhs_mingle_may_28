# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime

class ReportCustomerStatement(models.AbstractModel):
    _name = 'report.hhs_loyalty_management.customer_statement_report'
    _description = 'Customer Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        from_date = data.get('from_date')
        to_date = data.get('to_date')
        customer_id = data.get('customer_id')

        period_display = ''

        if from_date and to_date:
            period_display = '{} to {}'.format(
                fields.Date.from_string(from_date).strftime('%d-%m-%Y'),
                fields.Date.from_string(to_date).strftime('%d-%m-%Y')
            )

        period_month = ''
        if from_date:
            period_month = str(fields.Date.from_string(from_date).month)

        # Get transactions in the period
        domain = [
            ('transaction_date', '>=', from_date),
            ('transaction_date', '<=', to_date),
        ]
        if customer_id:
            domain.append(('partner_id', 'in', customer_id))

        all_transactions = self.env['loyalty.audit.view'].search(domain, order='transaction_date asc, id asc')
        customer_ids = all_transactions.mapped('partner_id')
        
        customers_data = []
        for customer in customer_ids:
            cust_transactions = all_transactions.filtered(lambda t: t.partner_id.id == customer.id)
            
            # Opening Balance for this customer
            opening_domain = [
                ('partner_id', '=', customer.id),
                ('transaction_date', '<', from_date),
            ]
            opening_transactions = self.env['loyalty.audit.view'].search(opening_domain)
            
            opening_regular = sum(opening_transactions.mapped('regular_points'))
            opening_bonus = sum(opening_transactions.mapped('bonus_points'))
            opening_total = sum(opening_transactions.mapped('total_points'))
            
            total_regular = sum(cust_transactions.mapped('regular_points'))
            total_bonus = sum(cust_transactions.mapped('bonus_points'))
            grand_total = sum(cust_transactions.mapped('total_points'))
            
            customers_data.append({
                'customer': customer,
                'opening_balance': {
                    'regular': opening_regular,
                    'bonus': opening_bonus,
                    'total': opening_total,
                },
                'transactions': cust_transactions,
                'total_regular': total_regular,
                'total_bonus': total_bonus,
                'grand_total': grand_total,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'loyalty.customer.statement.wizard',
            'data': data,
            'customer': customer,
            'from_date': from_date,
            'to_date': to_date,
            'period_month': period_month,
            'period_display': period_display,
            'customers_data': customers_data,
            'print_date': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
        }
