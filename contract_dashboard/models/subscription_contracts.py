# -*- coding: utf-8 -*-
from odoo import fields, models


class SubscriptionContracts(models.Model):
    _inherit = 'subscription.contracts'

    region_id = fields.Many2one(
        'res.region',
        string='Region',
        store=True,
    )
    customer_city_id = fields.Many2one(
        'res.city',
        string='City',
        store=True,
    )

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

    preventive_estimated = fields.Integer(
        string='Preventive Est', related='entitlement_prevent', store=True)
    preventive_actual = fields.Integer(
        string='Preventive Actual', related='actual_prevent_count', store=True)
    preventive_balance = fields.Float(
        string='Preventive Balance', related='balance_prevent', store=True)
    corrective_estimated = fields.Integer(
        string='Corrective Est', related='entitlement_correct', store=True)
    corrective_actual = fields.Integer(
        string='Corrective Actual', related='actual_correct_count', store=True)
    corrective_balance = fields.Float(
        string='Corrective Balance', related='balance_correct', store=True)
