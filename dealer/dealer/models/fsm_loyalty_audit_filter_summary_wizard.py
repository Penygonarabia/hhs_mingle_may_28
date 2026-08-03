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
        # Force-fix the view in the database in case the module was not upgraded
        pivot_view = self.env.ref('dealer.view_fsm_loyalty_audit_pivot_mob', raise_if_not_found=False)
        if pivot_view and 'type_order' in pivot_view.arch:
            new_arch = pivot_view.arch.replace('<field name="type_order" type="sort"  invisible="1"/>', '')
            new_arch = new_arch.replace('<field name="type_order" type="sort" invisible="1"/>', '')
            pivot_view.sudo().write({'arch': new_arch})

        domain = [('sales_id.state', '=', 'approved')]

        if self.start_date:
            domain.append(('date_time', '>=', self.start_date))

        if self.end_date:
            domain.append(('date_time', '<=', self.end_date))

        pivot_view_id = self.env.ref('dealer.view_fsm_loyalty_audit_pivot_mob').id
        tree_view_id = self.env.ref('dealer.view_fsm_loyalty_audit_tree_mob').id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Loyalty Points Summary',
            'res_model': 'fsm.loyalty.audit',
            'view_mode': 'pivot,tree',
            'views': [(pivot_view_id, 'pivot'), (tree_view_id, 'tree')],
            'domain': domain,
            'target': 'current',
        }