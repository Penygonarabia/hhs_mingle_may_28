# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ContractType(models.Model):
    _name = 'hr.contract.type'
    _inherit = 'hr.contract.type'
    _description = 'Contract Type'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True, help="Name of the contract", translate=True)
    sequence = fields.Integer(help="Gives the sequence when displaying a list of Contract.", default=10)


class HrPayrollStructureType(models.Model):

    _inherit = 'hr.payroll.structure.type'

    name = fields.Char(translate=True)
