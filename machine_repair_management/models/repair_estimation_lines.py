# -*- coding: utf-8 -*

from odoo import models, fields, api


class RepairEstimationLines(models.Model):
    _name = 'repair.estimation.lines'
    _description = "Repair Estimation Lines"

    task_id = fields.Many2one(
        'project.task',
        string="Task"
    )
    product_id = fields.Many2one(
        'product.product',
        string="Product",
        required=True
    )  # 14/02/2020
    qty = fields.Float(
        string="Quantity",
        default=1.0,
        required=True
    )  # 14/02/2020
    product_uom = fields.Many2one(
        'uom.uom',
        string="UOM",
        required=True
    )  # 14/02/2020
    price = fields.Float(
        string="Price",
        required=True
    )  # 14/02/2020
    notes = fields.Text(
        string="Description",
    )  # 14/02/2020

    #    @api.multi odoo13
    @api.onchange('product_id')
    def product_id_change(self):
        for rec in self:
            rec.product_uom = rec.product_id.uom_id.id
            rec.price = rec.product_id.lst_price
