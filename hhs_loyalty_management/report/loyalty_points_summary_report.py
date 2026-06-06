# -*- coding: utf-8 -*-

from odoo import models


class LoyaltyPointsSummaryReport(models.AbstractModel):
    """
    Abstract model acting as the QWeb report renderer.
    The `data` dict produced by the wizard is passed directly
    to the template as `docs` — no additional DB queries needed.
    """
    _name = 'report.hhs_loyalty_management.report_loyalty_points_summary_template'
    _description = 'Loyalty Points Summary Report'
    _table = 'report_loyalty_points_summary'  # override: auto-derived name exceeds PG 63-char limit

    def _get_report_values(self, docids, data=None):
        """
        Called by the Odoo report framework.
        `data` is the dict built by the wizard's action_generate_pdf().
        We compute grand-total summary values here so the template
        stays logic-free.
        """
        if not data:
            data = {}

        report_lines = data.get('report_lines', [])

        # -- Summary totals -------------------------------------------------
        totals = {
            'opening_balance':  sum(r.get('opening_balance', 0)  for r in report_lines),
            'regular_points':   sum(r.get('regular_points', 0)   for r in report_lines),
            'bonus_points':     sum(r.get('bonus_points', 0)      for r in report_lines),
            'redeemed_points':  sum(r.get('redeemed_points', 0)  for r in report_lines),
            'expired_points':   sum(r.get('expired_points', 0)   for r in report_lines),
            'available_points': sum(r.get('available_points', 0) for r in report_lines),
            'total_purchase':   sum(r.get('total_purchase', 0)   for r in report_lines),
        }

        return {
            'doc_ids': docids,
            'doc_model': 'loyalty.points.summary.wizard',
            'docs': data,
            'report_lines': report_lines,
            'totals': totals,
        }
