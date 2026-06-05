# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SubscriptionContracts(models.Model):
    _inherit = 'subscription.contracts'

    service_amount = fields.Float(
        string='Contract Value (Excl. VAT)',
        related='untaxed_amount',
        store=True,
    )
    contract_amount = fields.Monetary(
        string='Contract Value (Incl. VAT)',
        related='amount_total',
        store=True,
    )

    region = fields.Many2one(
        'work.center.group',
        string='Region',
        related='work_center_group_id',
        store=True,
    )
    city = fields.Many2one(
        'work.center.location',
        string='City',
        related='work_center_id',
        store=True,
    )

    # Visit metrics — declared as compute (not related=) so the module installs
    # cleanly even if the source fields on the target server were declared with
    # a slightly different type (e.g. Integer vs Float).
    preventive_estimated = fields.Float(
        string='Preventive Est',
        compute='_compute_visit_metrics',
        store=True,
    )
    preventive_actual = fields.Float(
        string='Preventive Actual',
        compute='_compute_visit_metrics',
        store=True,
    )
    preventive_balance = fields.Float(
        string='Preventive Balance',
        compute='_compute_visit_metrics',
        store=True,
    )
    corrective_estimated = fields.Float(
        string='Corrective Est',
        compute='_compute_visit_metrics',
        store=True,
    )
    corrective_actual = fields.Float(
        string='Corrective Actual',
        compute='_compute_visit_metrics',
        store=True,
    )
    corrective_balance = fields.Float(
        string='Corrective Balance',
        compute='_compute_visit_metrics',
        store=True,
    )

    @api.depends(
        'entitlement_prevent', 'entitlement_correct',
        'actual_prevent_count', 'actual_correct_count',
        'balance_prevent', 'balance_correct',
    )
    def _compute_visit_metrics(self):
        for rec in self:
            rec.preventive_estimated = _safe_float(rec, 'entitlement_prevent')
            rec.preventive_actual = _safe_float(rec, 'actual_prevent_count')
            rec.preventive_balance = _safe_float(rec, 'balance_prevent')
            rec.corrective_estimated = _safe_float(rec, 'entitlement_correct')
            rec.corrective_actual = _safe_float(rec, 'actual_correct_count')
            rec.corrective_balance = _safe_float(rec, 'balance_correct')


def _safe_float(record, field_name):
    try:
        return float(getattr(record, field_name, 0) or 0)
    except (TypeError, ValueError):
        return 0.0
