# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class CrmCommercialSaleOrder(models.Model):
    _name = 'crm.commercial.sale.order'
    _description = 'CRM Commercial Sale Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Order No',
        required=True,
        readonly=True,
        default=lambda self: _('New'),
        copy=False,
        index=True
    )
    quotation_id = fields.Many2one('crm.commercial.quotation', string='Quotation', readonly=True, index=True)
    quotation_no = fields.Char(string='Quotation No', readonly=True)
    quotation_type_id = fields.Many2one('crm.commercial.quotation.type', string='Quotation Type', readonly=True)

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, index=True, readonly=True)
    to_name = fields.Char(string='To', readonly=True)
    email = fields.Char(string='Email', readonly=True)
    phone = fields.Char(string='Phone', readonly=True)

    # Address fields from quotation
    street = fields.Char(string='Street 1', readonly=True)
    street2 = fields.Char(string='Street 2', readonly=True)
    city_id = fields.Many2one('res.city', string='City', readonly=True)
    city = fields.Char(string='City Name', readonly=True)
    district = fields.Char(string='District', readonly=True)
    region_id = fields.Many2one('res.country.state', string='Region', readonly=True)
    state_id = fields.Many2one('res.country.state', string='State', readonly=True)
    country_id = fields.Many2one('res.country', string='Country', readonly=True)
    zip = fields.Char(string='Zip Code', readonly=True)

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, index=True, readonly=True)
    assigned_id = fields.Many2one('res.users', string='Salesman', required=True, index=True, readonly=True)
    project_category_id = fields.Many2one('crm.commercial.project.category', string='Project Category', index=True, readonly=True)
    project_name = fields.Char(string='Project Name', index=True, readonly=True)

    consultant_id = fields.Many2one('crm.commercial.consultant', string='Consultant', readonly=True)
    developer = fields.Char(string='Developer', readonly=True)
    project_status_id = fields.Many2one('crm.commercial.project.status', string='Project Status', readonly=True)
    project_detail_status_id = fields.Many2one('crm.commercial.project.detail.status', string='Project Detail Status', readonly=True)
    tag_ids = fields.Many2many('crm.tag', string='Tags', readonly=True)

    date_order = fields.Date(string='Order Date', default=fields.Date.context_today, required=True, readonly=True)
    expiry_date = fields.Date(string='Expiry Date', required=True, index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('partially_delivered', 'Partially Delivered'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='confirmed', tracking=True, index=True)

    expected_gross_margin = fields.Float(string='Expected Gross Margin %', readonly=True)
    actual_gross_margin = fields.Float(string='Actual Gross Margin %', compute='_compute_actual_gross_margin', store=True)

    # Costing summary & totals from quotation
    total_selling_price = fields.Float(string='Total Selling Price (A)', readonly=True)
    total_cost = fields.Float(string='Total Cost (B)', readonly=True)
    total_supplier_support = fields.Float(string='Total Supplier Support (S)', readonly=True)
    total_dsi = fields.Float(string='Total DSI (C)', readonly=True)
    total_smc = fields.Float(string='Total SMC (D)', readonly=True)
    total_promo = fields.Float(string='Total Promo (E)', readonly=True)
    net_price = fields.Float(string='Net Price (X)', readonly=True)
    total_vat = fields.Float(string='Total VAT', readonly=True)
    total_amount = fields.Float(string='Total Amount', readonly=True)

    # Terms tabs from quotation
    payment_terms_tab = fields.Html(string='Payment Terms', readonly=True)
    warranty_terms_tab = fields.Html(string='Warranty Terms', readonly=True)
    salient_features_tab = fields.Html(string='Salient Features', readonly=True)
    settings_tab = fields.Html(string='Settings', readonly=True)

    line_ids = fields.One2many('crm.commercial.sale.order.line', 'order_id', string='Order Lines', readonly=True, copy=True)
    delivery_schedule_ids = fields.One2many('crm.commercial.delivery.schedule', 'order_id', string='Delivery Schedules')
    audit_ids = fields.One2many('crm.commercial.sale.order.audit', 'order_id', string='Audit Log', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('crm.commercial.sale.order') or _('New')
        return super(CrmCommercialSaleOrder, self).create(vals_list)

    @api.depends('line_ids', 'line_ids.delivered_cost', 'line_ids.delivered_amount')
    def _compute_actual_gross_margin(self):
        for order in self:
            tot_delivered_rev = sum(line.delivered_amount for line in order.line_ids)
            tot_delivered_cost = sum(line.delivered_cost for line in order.line_ids)
            if tot_delivered_rev > 0:
                order.actual_gross_margin = ((tot_delivered_rev - tot_delivered_cost) / tot_delivered_rev) * 100.0
            else:
                order.actual_gross_margin = order.expected_gross_margin

    def _log_audit(self, title, notes):
        for rec in self:
            self.env['crm.commercial.sale.order.audit'].create({
                'order_id': rec.id,
                'user_id': self.env.user.id,
                'title': title,
                'notes': notes,
                'state': rec.state,
            })

    def _update_delivery_state(self):
        for order in self:
            if order.state == 'cancelled':
                continue
            schedules = order.delivery_schedule_ids
            if not schedules:
                target_state = 'confirmed'
            else:
                all_delivered = all(s.status == 'delivered' or (s.qty_to_deliver > 0 and s.delivered_qty >= s.qty_to_deliver) for s in schedules)
                any_delivered = any(s.status == 'delivered' or s.delivered_qty > 0 for s in schedules)
                if all_delivered:
                    target_state = 'delivered'
                elif any_delivered:
                    target_state = 'partially_delivered'
                else:
                    target_state = 'confirmed'

            if order.state != target_state:
                old_state = order.state
                order.state = target_state
                state_dict = dict(self._fields['state'].selection)
                order._log_audit(
                    title='Order Status Updated',
                    notes=f"Order status updated from {state_dict.get(old_state, old_state)} to {state_dict.get(target_state, target_state)} based on delivery schedules."
                )
                if order.quotation_id and order.quotation_id.state not in ('draft', 'rejected', 'cancelled', 'expired'):
                    if order.quotation_id.state != target_state:
                        order.quotation_id.state = target_state
                        order.quotation_id._log_audit(
                            'Quotation Status Updated',
                            f"Quotation status updated to {target_state} matching Sale Order {order.name} delivery progress."
                        )

    def action_extend_expiry(self, new_expiry_date, reason):
        self.ensure_one()
        old_date = self.expiry_date
        self.expiry_date = new_expiry_date
        self._log_audit(
            title='Expiry Date Extended',
            notes=f'Expiry extended from {old_date} to {new_expiry_date}. Reason: {reason}'
        )

    def action_open_expiry_extension(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Extend Expiry Date',
            'res_model': 'crm.commercial.expiry.extension.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }


class CrmCommercialSaleOrderLine(models.Model):
    _name = 'crm.commercial.sale.order.line'
    _description = 'CRM Commercial Sale Order Line'

    order_id = fields.Many2one('crm.commercial.sale.order', string='Order', ondelete='cascade', index=True)
    quotation_line_id = fields.Many2one('crm.commercial.quotation.line', string='Quotation Line', readonly=True)
    name = fields.Text(string='Description / Part Name', readonly=True)

    product_group_id = fields.Many2one(
        'product.category',
        string='Product Group',
        readonly=True
    )
    product_category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        readonly=True
    )
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True, readonly=True)
    qty = fields.Float(string='Ordered Qty', default=1.0, required=True, readonly=True)

    delivered_qty = fields.Float(string='Delivered Qty', compute='_compute_delivered_qty', store=True)
    pending_qty = fields.Float(string='Pending Qty', compute='_compute_pending_qty', store=True)

    unit_cost = fields.Float(string='Unit Cost', readonly=True)
    sale_price = fields.Float(string='Sale Price', readonly=True)
    discount_percent = fields.Float(string='Discount %', readonly=True)
    vat_amount = fields.Float(string='VAT', readonly=True)
    amount = fields.Float(string='Amount', readonly=True)

    delivered_cost = fields.Float(string='Actual Delivered Cost', default=0.0)
    delivered_amount = fields.Float(string='Actual Delivered Amount', default=0.0)

    schedule_ids = fields.One2many('crm.commercial.delivery.schedule', 'order_line_id', string='Schedules')

    @api.depends('schedule_ids', 'schedule_ids.delivered_qty')
    def _compute_delivered_qty(self):
        for line in self:
            line.delivered_qty = sum(sched.delivered_qty for sched in line.schedule_ids)

    @api.depends('qty', 'delivered_qty')
    def _compute_pending_qty(self):
        for line in self:
            line.pending_qty = line.qty - line.delivered_qty


class CrmCommercialDeliverySchedule(models.Model):
    _name = 'crm.commercial.delivery.schedule'
    _description = 'Delivery Schedule'
    _order = 'scheduled_date, id'

    order_id = fields.Many2one('crm.commercial.sale.order', string='Order', ondelete='cascade', index=True)
    order_line_id = fields.Many2one('crm.commercial.sale.order.line', string='Order Item', ondelete='cascade', required=True, index=True, readonly=True)
    product_id = fields.Many2one('product.product', related='order_line_id.product_id', string='Product', readonly=True, store=True)

    # Reporting & Analysis Dimensions (related to Order, Order Line, and Quotation)
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Customer Name', readonly=True, store=True, index=True)
    customer_no = fields.Char(related='order_id.partner_id.ref', string='Customer No', readonly=True, store=True, index=True)
    quotation_id = fields.Many2one('crm.commercial.quotation', related='order_id.quotation_id', string='Quotation', readonly=True, store=True, index=True)
    quotation_type_id = fields.Many2one('crm.commercial.quotation.type', related='order_id.quotation_type_id', string='Quotation Type', readonly=True, store=True, index=True)
    assigned_id = fields.Many2one('res.users', related='order_id.assigned_id', string='Salesman', readonly=True, store=True, index=True)
    warehouse_id = fields.Many2one('stock.warehouse', related='order_id.warehouse_id', string='Warehouse', readonly=True, store=True, index=True)
    region_id = fields.Many2one('res.country.state', related='order_id.region_id', string='Region', readonly=True, store=True, index=True)
    city_id = fields.Many2one('res.city', related='order_id.city_id', string='City', readonly=True, store=True, index=True)
    city_name = fields.Char(related='order_id.city', string='City Name', readonly=True, store=True)

    product_group_id = fields.Many2one('product.category', related='order_line_id.product_group_id', string='Group', readonly=True, store=True, index=True)
    product_category_id = fields.Many2one('product.category', related='order_line_id.product_category_id', string='Category', readonly=True, store=True, index=True)

    quotation_state = fields.Selection(related='order_id.quotation_id.state', string='Quotation Status', readonly=True, store=True, index=True)
    sale_order_state = fields.Selection(related='order_id.state', string='Sales Order Status', readonly=True, store=True, index=True)

    scheduled_date = fields.Date(string='Scheduled Date', required=True, index=True)
    qty_to_deliver = fields.Float(string='Qty to Deliver', required=True)
    delivered_qty = fields.Float(string='Delivered Qty', default=0.0)
    pending_qty = fields.Float(string='Pending Qty', compute='_compute_pending', store=True, readonly=True)
    status = fields.Selection([
        ('yet_to_deliver', 'Yet To Deliver'),
        ('delivered', 'Delivered')
    ], string='Status', default='yet_to_deliver', required=True, index=True)

    @api.depends('qty_to_deliver', 'delivered_qty')
    def _compute_pending(self):
        for rec in self:
            rec.pending_qty = rec.qty_to_deliver - rec.delivered_qty

    @api.onchange('delivered_qty', 'qty_to_deliver')
    def _onchange_delivered_qty(self):
        if self.delivered_qty >= self.qty_to_deliver and self.qty_to_deliver > 0:
            self.status = 'delivered'
        elif self.status == 'delivered' and self.delivered_qty < self.qty_to_deliver:
            self.status = 'yet_to_deliver'

    @api.onchange('status')
    def _onchange_status(self):
        if self.status == 'delivered' and self.delivered_qty < self.qty_to_deliver:
            self.delivered_qty = self.qty_to_deliver
        elif self.status == 'yet_to_deliver' and self.delivered_qty >= self.qty_to_deliver and self.qty_to_deliver > 0:
            self.delivered_qty = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super(CrmCommercialDeliverySchedule, self).create(vals_list)
        for rec in records:
            if rec.order_id:
                prod_name = rec.product_id.display_name or (rec.order_line_id and rec.order_line_id.product_id.display_name) or 'Item'
                status_label = dict(rec._fields['status'].selection).get(rec.status, rec.status)
                rec.order_id._log_audit(
                    title='Delivery Schedule Added',
                    notes=f"Added delivery schedule for {prod_name}:\n"
                          f"- Scheduled Date: {rec.scheduled_date}\n"
                          f"- Qty to Deliver: {rec.qty_to_deliver}\n"
                          f"- Delivered Qty: {rec.delivered_qty}\n"
                          f"- Status: {status_label}"
                )
        records.mapped('order_id')._update_delivery_state()
        return records

    def write(self, vals):
        if len(self) == 1 and 'delivered_qty' not in vals:
            if vals.get('status') == 'delivered' and self.delivered_qty < self.qty_to_deliver:
                vals['delivered_qty'] = self.qty_to_deliver
            elif vals.get('status') == 'yet_to_deliver' and self.delivered_qty >= self.qty_to_deliver and self.qty_to_deliver > 0:
                vals['delivered_qty'] = 0.0

        for rec in self:
            changes = []
            if 'scheduled_date' in vals and str(vals['scheduled_date']) != str(rec.scheduled_date):
                changes.append(f"- Scheduled Date: {rec.scheduled_date} -> {vals['scheduled_date']}")
            if 'qty_to_deliver' in vals and vals['qty_to_deliver'] != rec.qty_to_deliver:
                changes.append(f"- Qty to Deliver: {rec.qty_to_deliver} -> {vals['qty_to_deliver']}")
            if 'delivered_qty' in vals and vals['delivered_qty'] != rec.delivered_qty:
                changes.append(f"- Delivered Qty: {rec.delivered_qty} -> {vals['delivered_qty']}")
            if 'status' in vals and vals['status'] != rec.status:
                old_status = dict(rec._fields['status'].selection).get(rec.status, rec.status)
                new_status = dict(rec._fields['status'].selection).get(vals['status'], vals['status'])
                changes.append(f"- Status: {old_status} -> {new_status}")

            if changes and rec.order_id:
                prod_name = rec.product_id.display_name or (rec.order_line_id and rec.order_line_id.product_id.display_name) or 'Item'
                rec.order_id._log_audit(
                    title='Delivery Schedule Updated',
                    notes=f"Item: {prod_name}\n" + "\n".join(changes)
                )
        res = super(CrmCommercialDeliverySchedule, self).write(vals)
        self.mapped('order_id')._update_delivery_state()
        return res

    def unlink(self):
        orders = self.mapped('order_id')
        for rec in self:
            if rec.order_id:
                prod_name = rec.product_id.display_name or (rec.order_line_id and rec.order_line_id.product_id.display_name) or 'Item'
                rec.order_id._log_audit(
                    title='Delivery Schedule Removed',
                    notes=f"Removed delivery schedule for item: {prod_name} (Scheduled: {rec.scheduled_date}, Qty: {rec.qty_to_deliver})"
                )
        res = super(CrmCommercialDeliverySchedule, self).unlink()
        orders._update_delivery_state()
        return res


class CrmCommercialSaleOrderAudit(models.Model):
    _name = 'crm.commercial.sale.order.audit'
    _description = 'Sale Order Audit Log'
    _order = 'create_date desc'

    order_id = fields.Many2one('crm.commercial.sale.order', string='Order', ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    title = fields.Char(string='Title', readonly=True)
    notes = fields.Text(string='Notes / Reason', readonly=True)
    state = fields.Char(string='Status', readonly=True)

