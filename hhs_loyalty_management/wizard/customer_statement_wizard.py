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
        if self.customers_ids:
            domain.append(('partner_id', 'in', self.customers_ids.ids))

        transactions = self.env['loyalty.audit.view'].search(domain)

        if not transactions:
            raise UserError(_("No loyalty transactions found for the selected period."))

        data = {
            'wizard_id': self.id,
            'customer_id': self.customers_ids.ids if self.customers_ids else False,
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

    @api.model
    def cron_send_monthly_statement(self):
        import base64
        import logging
        _logger = logging.getLogger(__name__)

        today = date.today()
        first_day_this_month = today.replace(day=1)
        last_day_prev_month = first_day_this_month - relativedelta(days=1)
        first_day_prev_month = last_day_prev_month.replace(day=1)

        customers = self.env['res.partner'].search([
            ('activate_loyalty_feature', '=', True),
            ('email', '!=', False)
        ])

        if not customers:
            _logger.info("No customers with loyalty active and valid email found.")
            return

        report = self.env.ref('hhs_loyalty_management.action_customer_statement_report')

        for customer in customers:
            try:
                wizard = self.create({
                    'customers_ids': [(6, 0, [customer.id])],
                    'from_date': first_day_prev_month,
                    'to_date': last_day_prev_month,
                })
                
                data = {
                    'wizard_id': wizard.id,
                    'customer_id': [customer.id],
                    'from_date': wizard.from_date,
                    'to_date': wizard.to_date,
                }
                
                pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                    report.report_name,
                    [wizard.id],
                    data=data
                )
                
                attachment = self.env['ir.attachment'].create({
                    'name': f'Customer_Loyalty_Point_Statement.pdf',
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'mimetype': 'application/pdf',
                })
                
                body_html = f"""
                    <p>Dear {customer.name},</p>
                    <p>Please find attached your Monthly Customer Loyalty Point Statement for the period {first_day_prev_month.strftime('%d-%m-%Y')} to {last_day_prev_month.strftime('%d-%m-%Y')}.</p>
                    <p>Regards,<br/>System Generated Mail</p>
                """

                # Get email_from: try company, then user, then outgoing mail server smtp_user
                email_from = (
                    self.env.company.email
                    or self.env.user.email
                    or self.env['ir.mail_server'].sudo().search([], limit=1).smtp_user
                    or 'noreply@hhs.com.sa'
                )

                mail = self.env['mail.mail'].sudo().create({
                    'subject': 'Monthly Customer Loyalty Point Statement',
                    'body_html': body_html,
                    'email_from': email_from,
                    'email_to': customer.email,
                    'attachment_ids': [(4, attachment.id)],
                })
                mail.sudo().send()
                _logger.info(f"Monthly loyalty statement sent to {customer.name} ({customer.email}) from {email_from}")
            except Exception as e:
                _logger.error(f"Failed to send monthly loyalty statement to {customer.name}: {str(e)}")
