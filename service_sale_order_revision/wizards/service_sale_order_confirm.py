from odoo import models, fields


class ServiceSaleOrderConfirmWizard(models.TransientModel):
    _name = "service.sale.order.wizard"
    _description = "Confirm Service Sale Order Wizard"

    order_id = fields.Many2one(
        "service.sale.order",
        string="Sale Orders to Confirm",
        help="Select the sale orders to be conform.",
    )
    sale_orders_ids = fields.Many2many(
        "service.sale.order",
        string="Sale Orders to Cancel",
        help="Select the sale orders to be canceled.",
    )

    def action_rev_cancel_orders(self):
        """Method to confirm or cancel selected sale orders."""
        for wizard in self:
            wizard.order_id.rev_confirm = True
            wizard.order_id.action_confirm()
            for order in wizard.sale_orders_ids:
                order.state = 'cancel'
        return {"type": "ir.actions.act_window_close"}

    def action_rev_keep_orders(self):
        """Method to keep related sale orders."""
        for wizard in self:
            wizard.order_id.rev_confirm = True
            wizard.order_id.action_confirm()
        return {"type": "ir.actions.act_window_close"}
