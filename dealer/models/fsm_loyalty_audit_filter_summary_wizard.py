from odoo import models, fields, api
from datetime import date
import calendar


class FsmLoyaltyAuditFilterWizard(models.TransientModel):
    _name = 'fsm.loyalty.audit.filter.summary.wizard'
    _description = 'Loyalty Audit Filter Summary Wizard'

    def _default_start_date(self):
        today = date.today()
        return today.replace(day=1)

    def _default_end_date(self):
        today = date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        return today.replace(day=last_day)

    start_date = fields.Date(
        string="Start Date",
        default=_default_start_date
    )

    end_date = fields.Date(
        string="End Date",
        default=_default_end_date
    )

    def apply_filter_summary(self):
        action = self.env.ref('dealer.action_fsm_loyalty_audit_pivot_mob').read()[0]

        domain = [('sales_id.state', '=', 'approved')]

        if self.start_date:
            domain.append(('date_time', '>=', self.start_date))

        if self.end_date:
            domain.append(('date_time', '<=', self.end_date))

        action['domain'] = domain
        return action