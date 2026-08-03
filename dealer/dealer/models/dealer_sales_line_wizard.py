from odoo import models, fields, api, _
import re

class DealerSalesLineWizard(models.TransientModel):
    _name = 'dealer.sales.line.wizard'
    _description = 'Add Item'

    sales_id = fields.Many2one('dsales.showroom.sales')
    line_id = fields.Many2one('dsales.showroom.sales.line')

    product_category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        domain="[('parent_id','=', False), ('name', '!=', 'All')]"
    )

    product_group_id = fields.Many2one(
        'product.category',
        string='Product Group',
        domain="[('parent_id', '=', product_category_id)]"
    )

    product_subgroup_id = fields.Many2one(
        'product.category',
        string='Product Sub Group',
        domain="[('parent_id', '=', product_group_id)]"
    )

    product_id = fields.Many2one(
        'product.product',
        string='Model'
    )

    product_name = fields.Char(
        related='product_id.name',
        string='Name',
        readonly=True
    )

    capacity = fields.Char(
        string='Capacity',
        compute='_compute_capacity',
        readonly=True,
    )

    qty = fields.Integer(string='Qty', default=1, required=True)

    loyalty_points = fields.Float(
        string='Loyalty Points',
        compute='_compute_loyalty_points',
        readonly=True
    )

    @api.onchange('product_category_id')
    def _onchange_product_category_id(self):
        if self.product_group_id and self.product_group_id.parent_id != self.product_category_id:
            self.product_group_id = False
        if not self.product_category_id:
            self.product_group_id = False
            self.product_subgroup_id = False
            # self.product_id = False
        
        domain = []
        if self.product_category_id:
            domain = [('parent_id', '=', self.product_category_id.id)]
        # Also narrow product domain to category level
        product_domain = [('show_in_dealer_app', '=', True)]
        if self.product_category_id:
            product_domain.append(('product_tmpl_id.categ_id', 'child_of', self.product_category_id.id))
        return {'domain': {'product_group_id': domain, 'product_id': product_domain}}

    @api.onchange('product_group_id')
    def _onchange_product_group_id(self):
        if self.product_subgroup_id and self.product_subgroup_id.parent_id != self.product_group_id:
            self.product_subgroup_id = False
        if not self.product_group_id:
            self.product_subgroup_id = False
            # self.product_id = False
            
        domain = []
        if self.product_group_id:
            domain = [('parent_id', '=', self.product_group_id.id)]
        # Also narrow product domain to group level
        product_domain = [('show_in_dealer_app', '=', True)]
        if self.product_group_id:
            product_domain.append(('product_tmpl_id.categ_id', 'child_of', self.product_group_id.id))
        elif self.product_category_id:
            product_domain.append(('product_tmpl_id.categ_id', 'child_of', self.product_category_id.id))
        return {'domain': {'product_subgroup_id': domain, 'product_id': product_domain}}

    @api.onchange('product_subgroup_id')
    def _onchange_product_subgroup_id(self):
        # Allow the domain to re-apply without clearing the product_id
        # self.product_id = False
            
        domain = []
        if self.product_subgroup_id:
            domain.append(('product_tmpl_id.categ_id', 'child_of', self.product_subgroup_id.id))
        elif self.product_group_id:
            domain.append(('product_tmpl_id.categ_id', 'child_of', self.product_group_id.id))
        elif self.product_category_id:
            domain.append(('product_tmpl_id.categ_id', 'child_of', self.product_category_id.id))
        domain.append(('show_in_dealer_app', '=', True))
        return {'domain': {'product_id': domain}}

    @api.onchange('product_id')
    def _onchange_product_id(self):
        pass

    @api.depends('product_id')
    def _compute_capacity(self):
        for rec in self:
            rec.capacity = ''
            if rec.product_id and rec.product_id.name:
                match = re.search(r'\b\d+[A-Z]\b', rec.product_id.name)
                if match:
                    rec.capacity = match.group()

    @api.depends('product_id', 'qty')
    def _compute_loyalty_points(self):
        for rec in self:
            if rec.product_id and rec.qty:
                pts = abs(rec.qty) * (rec.product_id.fsm_loyalty_points or 0.0)
                rec.loyalty_points = pts
            else:
                rec.loyalty_points = 0.0

    def action_add(self):
        self.ensure_one()
        vals = {
            'sales_id': self.sales_id.id,
            'product_id': self.product_id.id,
            'qty': self.qty,
        }
        if self.line_id:
            self.line_id.write(vals)
        else:
            self.env['dsales.showroom.sales.line'].create(vals)
        return {'type': 'ir.actions.act_window_close'}