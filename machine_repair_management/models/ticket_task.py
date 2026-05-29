# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, warnings


class ProjectTask(models.Model):
    _inherit = "project.task"

    #     ticket_id = fields.Many2one(
    #         'machine.repair.support',
    #         string='Machine Repair Ticket',
    #         readonly=True,
    #         copy=False,
    #     )
    machine_ticket_id = fields.Many2one(
        'machine.repair.support',
        string='Machine Repair Ticket',
        readonly=True,
        copy=False,
    )
    task_type = fields.Selection(
        selection=[
            ('diagnosys', 'Diagnosys'),
            ('work_order', 'Work Order'),
        ],
        string="Type",
        readonly=True, default="work_order"
    )
    repair_estimation_line_ids = fields.One2many(
        'repair.estimation.lines',
        'task_id',
        string="Repair Estimation Lines"
    )

# #    @api.multi odoo13
#     def show_quotation(self):
#         for rec in self:
#             res = self.env.ref('sale.action_quotations')
#             res = res.sudo().read()[0]
#             res['domain'] = str([('task_id','=', rec.id)])
#         return res

# def show_quotation(self):
#     return {
#         'name':'Sale Order',
#         'res_model':'sale.order',
#         "view_mode":'tree,form',
#         "domain":[('task_id','=',self.id)],
#         "type" :'ir.actions.act_window',
#
#
#         }
#


#    @api.multi odoo13
#     def create_quotation(self):
#         for rec in self:
#             if not rec.repair_estimation_line_ids:
#                 raise UserError(_('Please add Estimation detail to create quotation!'))
#             vales = {
#                 'task_id': rec.id,
#                 'partner_id': rec.partner_id.id,
#                 # 'user_id': rec.user_id.id,
#                 # 'user_id': rec.activity_user_id.id,
#                 # 'user_id': rec.user_ids[0].id if rec.user_ids else False,
#                 'user_id': rec.partner_id.user_id.id or False,
#                 'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
#             }
#             order_id = self.env['sale.order'].sudo().create(vales)
#             for line in rec.repair_estimation_line_ids:
#
#                 if not line.product_id:
#                     raise UserError(_('Product not defined on Estimation Repair Lines!'))
#
#                 price_unit = line.price
#                 if order_id.pricelist_id:
#                     price_unit, rule_id = order_id.pricelist_id._get_product_price_rule(
#                         line.product_id,
#                         line.qty or 1.0,
#                         order_id.partner_id,
#                     )
#
#                 orderlinevals = {
#                     'order_id' : order_id.id,
#                     'product_id' : line.product_id.id,
#                     'product_uom_qty' : line.qty,
#                     'product_uom' : line.product_uom.id,
#                     'price_unit' : price_unit,
#                     'name' : line.notes or line.product_id.name or '/', #14/02/2020
#                 }
#                 line_id = self.env['sale.order.line'].create(orderlinevals)
#         action = self.env.ref('sale.action_quotations')
#         result = action.sudo().read()[0]
#         result['domain'] = [('id', '=', order_id.id)]
#         return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
