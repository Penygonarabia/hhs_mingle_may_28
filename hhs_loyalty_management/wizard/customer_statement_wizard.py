# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta

class LoyaltyCustomerStatementWizard(models.TransientModel):
    _name = 'loyalty.customer.statement.wizard'
    _description = 'Customer Statement Wizard'

    # customer_id = fields.Many2one(
    #     'res.partner',
    #     string='Customer',
    #     domain=[('activate_loyalty_feature', '=', True)]
    # )
    customers_ids=fields.Many2many(
        'res.partner',
        string='Customer',
        domain=[('activate_loyalty_feature', '=', True)]
    )
    from_date = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: date.today().replace(day=1)
    )

    to_date = fields.Date(
        string='To Date',
        required=True,
        default=lambda self: (
                date.today().replace(day=1)
                + relativedelta(months=1, days=-1)
        )
    )

    @api.constrains('from_date', 'to_date')
    def _check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise UserError(_("From Date cannot be greater than To Date."))

    def action_print_pdf(self):
        self.ensure_one()

        domain = [
            ('transaction_date', '>=', self.from_date),
            ('transaction_date', '<=', self.to_date),
        ]

        # Customer filter only when selected
        if self.customer_id:
            domain.append(('partner_id', '=', self.customer_id.id))

        transactions = self.env['loyalty.audit.view'].search(domain)

        if not transactions:
            raise UserError(_("No loyalty transactions found for the selected period."))

        data = {
            'wizard_id': self.id,
            'customer_id': self.customer_id.id if self.customer_id else False,
            'from_date': self.from_date,
            'to_date': self.to_date,
        }

        return self.env.ref(
            'hhs_loyalty_management.action_customer_statement_report'
        ).report_action(self, data=data)

    # def action_print_pdf(self):
    #     self.ensure_one()
    #     # Check if transactions exist for the selected period and customer
    #     domain = [
    #         ('partner_id', '=', self.customer_id.id),
    #         ('transaction_date', '>=', self.from_date),
    #         ('transaction_date', '<=', self.to_date),
    #     ]
    #
    #     transactions = self.env['loyalty.audit.view'].search(domain)
    #     if not transactions:
    #         raise UserError(_("No loyalty transactions found for the selected period."))
    #
    #     data = {
    #         'wizard_id': self.id,
    #         'customer_id': self.customer_id.id,
    #         'from_date': self.from_date,
    #         'to_date': self.to_date,
    #     }
    #     return self.env.ref('hhs_loyalty_management.action_customer_statement_report').report_action(self, data=data)

    def action_export_excel(self):
        # Placeholder for Excel export
        return True
