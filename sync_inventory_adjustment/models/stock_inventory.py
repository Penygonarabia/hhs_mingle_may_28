# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils, float_compare

class AccountMove(models.Model):
    _inherit="account.move"

    def _check_balanced(self):
        # You should implement your balance check logic here
        return True


class Inventory(models.Model):
    _name = "stock.inventory"
    _description = "Inventory"
    _order = "date desc, id desc"

    @api.model
    def create(self, vals):
        upd_vals = vals.copy()
        if upd_vals.get("name", "/") == "/":
            upd_vals["name"] = self.env["ir.sequence"].next_by_code("stock.inventory")
        return super().create(upd_vals)


    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))

    name = fields.Char(
        'Inventory Reference',
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]})
    date = fields.Datetime(
        'Inventory Date',
         required=True,
        default=fields.Datetime.now,
        help="If the inventory adjustment is not validated, date at which the theoritical quantities have been checked.\n"
             "If the inventory adjustment is validated, date at which the inventory adjustment has been validated.")
    line_ids = fields.One2many(
        'stock.inventory.line', 'inventory_id', string='Inventories',
        copy=True, readonly=False,
        states={'done': [('readonly', True)]})
  
    
    move_ids = fields.One2many(
        'stock.move', 'inventory_id', string='Created Moves',
        states={'done': [('readonly', True)]})
    

    
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        ('done', 'Validated')],
        copy=False, index=True, readonly=True,
        default='draft')
    company_id = fields.Many2one(
        'res.company', 'Company',
        index=True, required=True, default=lambda self : self.env.user.company_id,
        states={'draft': [('readonly', False)]})
    location_id = fields.Many2one(
        'stock.location', 'Inventoried Location',
        required=True,
        states={'draft': [('readonly', False)]},
        default=_default_location_id)
    product_id = fields.Many2one(
        'product.product', 'Inventoried Product',
        states={'draft': [('readonly', False)]},
        help="Specify Product to focus your inventory on a particular Product.")
    package_id = fields.Many2one(
        'stock.quant.package', 'Inventoried Pack',
        states={'draft': [('readonly', False)]},
        help="Specify Pack to focus your inventory on a particular Pack.")
    partner_id = fields.Many2one(
        'res.partner', 'Inventoried Owner',
        states={'draft': [('readonly', False)]},
        help="Specify Owner to focus your inventory on a particular Owner.")
    lot_id = fields.Many2one(
        'stock.lot', 'Inventoried Lot/Serial Number',
        copy=False,
        states={'draft': [('readonly', False)]},
        help="Specify Lot/Serial Number to focus your inventory on a particular Lot/Serial Number.")
    filter = fields.Selection(
        string='Inventory of', selection='_selection_filter',
        required=True,
        default='none',
        help="If you do an entire inventory, you can choose 'All Products' and it will prefill the inventory with the current stock.  If you only do some products  "
             "(e.g. Cycle Counting) you can choose 'Manual Selection of Products' and the system won't propose anything.  You can also let the "
             "system propose for a single product / lot /... ")
    total_qty = fields.Float('Total Quantity', compute='_compute_total_qty')
    category_id = fields.Many2one(
        'product.category', 'Product Category',
        states={'draft': [('readonly', False)]},
        help="Specify Product Category to focus your inventory on a particular Category.")
    exhausted = fields.Boolean('Include Exhausted Products', readonly=True, states={'draft': [('readonly', False)]})
    remarks = fields.Char('Remarks')
    analytic_account_id = fields.Many2one(
        string="Analytic Account", comodel_name="account.analytic.account"
    )

    adj_yes_no = fields.Selection(string='Adj Qty Y/N', selection=[
        ('yes', 'Yes'),
        ('no', 'No'), ],
                                  copy=False, index=True,
                                  default='yes')
    journal_pick_id = fields.Many2one('account.move',string="Journal Entry")
    journal_count = fields.Integer(compute="compute_journal_count")

    def journal_count_number(self):
        pass
    
    def compute_journal_count(self):
        for rec in self:
            rec.journal_count = self.env['account.move'].search_count([('id','=',self.journal_pick_id.id)])

    
    def action_view_journal(self):
      
        if self.journal_pick_id:
            return{
                'type':'ir.actions.act_window',
                    'target':'current',
                    'res_id':self.journal_pick_id.id,
                    'res_model':'account.move',
                    'view_mode':'form',
        
                    }
            
        return False


    @api.constrains('line_ids')
    def _check_exist_product_in_line(self):
        for transfer in self:
            exist_product_list = []
            for line in transfer.line_ids:
                if line.product_id.id in exist_product_list:
                    raise ValidationError(_('Product should be one per line.The Product \' %s \' is already there in the line.'%(line.product_id.display_name)))
                exist_product_list.append(line.product_id.id)
    
    

    @api.onchange('location_id')
    def _update_analytic_account(self):
        for rec in self:
            if rec.location_id:
                # Access the parent warehouse_id from the location_id
                warehouse_id = rec.location_id.warehouse_id
                if warehouse_id:
                    # Access the analytic_id from the parent warehouse
                    analytic_account = warehouse_id.analytic_id
                    # Update the analytic_account_id field with the new value
                    rec.analytic_account_id = analytic_account

    @api.depends('product_id', 'line_ids.product_qty')
    def _compute_total_qty(self):
        """ For single product inventory, total quantity of the counted """
        self.ensure_one()
        if self.product_id:
            self.total_qty = sum(self.mapped('line_ids').mapped('product_qty'))
        else:
            self.total_qty = 0

    @api.onchange('filter')
    def _onchange_filter(self):
        if self.filter not in ('product', 'product_owner'):
            self.product_id = False
        if self.filter != 'lot':
            self.lot_id = False
        if self.filter not in ('owner', 'product_owner'):
            self.partner_id = False
        if self.filter != 'pack':
            self.package_id = False
        if self.filter != 'category':
            self.category_id = False
        if self.filter != 'product':
            self.exhausted = False
        if self.filter == 'product':
            self.exhausted = True

    @api.model
    def _selection_filter(self):
        """ Get the list of filter allowed according to the options checked
        in 'Settings/Warehouse'. """
        res_filter = [
            ('none', _('All products')),
            ('category', _('One product category')),
            ('product', _('One product only')),
            ('partial', _('Select products manually'))]

        if self.user_has_groups('stock.group_tracking_owner'):
            res_filter += [('owner', _('One owner only')), ('product_owner', _('One product for a specific owner'))]
        if self.user_has_groups('stock.group_production_lot'):
            res_filter.append(('lot', _('One Lot/Serial Number')))
        if self.user_has_groups('stock.group_tracking_lot'):
            res_filter.append(('pack', _('A Pack')))
        return res_filter

    def action_reset_product_qty(self):
        self.mapped('line_ids').write({'product_qty': 0})
        return True

    def action_validate(self):
        lines = self.line_ids.filtered(lambda l: l.theoretical_qty != l.product_qty)
        debit_sums = {}
        credit_sums = {}
        line_product=[]
        for line in lines:
            # line_product.append(line.product_id.id)
            # self.adjusted_qty_ids.write({'product_id':line.product_id.id})

            if not line.quant_id:
                quants = self.env['stock.quant']._gather(line.product_id, line.location_id, lot_id=line.prod_lot_id, package_id=line.package_id, owner_id=None, strict=True)
                line.quant_id = quants and quants.id
                if not quants:
                    line.quant_id = self.env['stock.quant'].create({
                        'product_id': line.product_id.id,
                        'location_id': line.location_id.id,
                        'inventory_quantity': line.product_qty,
                        'quantity':line.product_qty,
                        'lot_id': line.prod_lot_id and line.prod_lot_id.id,
                    })
                   
                else:
                    line.quant_id.write({'inventory_quantity': line.product_qty})  # Update the inventory quantity
    
            if line.theoretical_qty < line.product_qty:
            
                stock_move = self.env['stock.move'].create({
                    'name': self.name,  # Customize the name as needed
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(line.theoretical_qty - line.product_qty),
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': line.product_id.property_stock_inventory.id,
                    'location_dest_id': line.location_id.id,  # Replace with the actual destination location ID
                    'company_id': self.company_id.id,
                    'state': 'done', 
                    'analytic_account_id':self.analytic_account_id.id,
                    'inventory_id':self.id,
                    'inventory_adjustment':True
            
                     # You can change the initial state if needed
                    # Add any other necessary fields to the stock move
                }) 
            
            if line.theoretical_qty > line.product_qty:
                stock_move = self.env['stock.move'].create({
                    'name': self.name,  # Customize the name as needed
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(line.theoretical_qty - line.product_qty),
                    'product_uom': line.product_id.uom_id.id,
                    'location_id':  line.location_id.id ,
                    'location_dest_id':line.product_id.property_stock_inventory.id,
                      # Replace with the actual destination location ID
                    'company_id': self.company_id.id,
                    'state': 'done',
                    'analytic_account_id':self.analytic_account_id.id,
                    'inventory_adjustment':True,
            
                     'inventory_id':self.id  # You can change the initial state if needed
                    # Add any other necessary fields to the stock move
                })  

            # Check if the difference is positive or negative and update debit/credit accordingly
            if line.theoretical_qty > line.product_qty:
                debit_category_id = line.product_id.property_stock_inventory.valuation_in_account_id.id
                credit_category_id = line.product_id.categ_id.property_stock_valuation_account_id.id

            # Check if the difference is positive or negative and update debit/credit accordingly
            if line.theoretical_qty < line.product_qty:
                debit_category_id = line.product_id.categ_id.property_stock_valuation_account_id.id
                credit_category_id = line.product_id.property_stock_inventory.valuation_in_account_id.id
            
            # debit_category_id = line.product_id.categ_id.property_stock_account_input_categ_id.id
            # credit_category_id = line.product_id.categ_id.property_stock_account_output_categ_id.id
            
            # Update debit sums
            if debit_category_id in debit_sums:
                debit_sums[debit_category_id] += abs(line.theoretical_qty - line.product_qty) * line.product_id.standard_price
            else:
                debit_sums[debit_category_id] = abs(line.theoretical_qty - line.product_qty) * line.product_id.standard_price
    
            # Update credit sums
            if credit_category_id in credit_sums:
                credit_sums[credit_category_id] += abs(line.theoretical_qty - line.product_qty) * line.product_id.standard_price
            else:
                credit_sums[credit_category_id] = abs(line.theoretical_qty - line.product_qty) * line.product_id.standard_price
    
        debit_vals = []
        credit_vals = []
    
        for category_id, debit_sum in debit_sums.items():
            debit_vals.append({
                'name':'Inventory Adjusted',
                'debit': debit_sum,
                'credit': 0.0,
                'currency_id': self.company_id.currency_id.id,
                'analytic_account_id': self.analytic_account_id.id,
                'account_id': category_id,
                
            })
        for category_id, credit_sum in credit_sums.items():
            credit_vals.append({
                'name':'Inventory Adjusted',
                'debit': 0.0,
                'credit': credit_sum,
                'currency_id': self.company_id.currency_id.id,
                'analytic_account_id': self.analytic_account_id.id,
                'account_id': category_id,
            })
    
        if debit_vals or credit_vals:
            journal_pick_id = self.env["account.move"]
            line_ids = []
    
            line_ids.extend([(0, 0, debit) for debit in debit_vals])
            line_ids.extend([(0, 0, credit) for credit in credit_vals])
            
            if line.product_id.standard_price !=0:
            
                journal_entry = journal_pick_id.create(
                    {
                        # "name":self.name,
                        "date": self.date,
                        "ref": self.name,
                        "move_type": "entry",
                        # "state": "draft",
                        'line_ids': line_ids,
                        "journal_id":line.product_id.categ_id.property_stock_journal.id
                    }
                )
                journal_entry.action_post()
                self.write({'journal_pick_id': journal_entry.id})
            # line.quant_id.with_context(inventory_id=self.id)
        self.write({'state': 'done', 'date': fields.Datetime.now()})
        return True
    

    def action_cancel_draft(self):
        self.write({
            'line_ids': [(5,)],
            'state': 'draft'
        })



    def action_start(self):
     
        for inventory in self.filtered(lambda x: x.state not in ('done','cancel')):
            vals = {'state': 'confirm', 'date': fields.Datetime.now()}
            if (inventory.filter != 'partial') and not inventory.line_ids:
                vals.update({'line_ids': [(0, 0, line_values) for line_values in inventory._get_inventory_lines_values()]})
            inventory.write(vals)
        return True

    def _get_inventory_lines_values(self):
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
        domain = ' location_id in %s AND quantity != 0 AND active = TRUE'
        args = (tuple(locations.ids),)

        vals = []
        Product = self.env['product.product']
        # Empty recordset of products available in stock_quants
        quant_products = self.env['product.product']
        # Empty recordset of products to filter
        products_to_filter = self.env['product.product']

        # case 0: Filter on company
        if self.company_id:
            domain += ' AND company_id = %s'
            args += (self.company_id.id,)

        #case 1: Filter on One owner only or One product for a specific owner
        if self.partner_id:
            domain += ' AND owner_id = %s'
            args += (self.partner_id.id,)
        #case 2: Filter on One Lot/Serial Number
        if self.lot_id:
            domain += ' AND lot_id = %s'
            args += (self.lot_id.id,)
        #case 3: Filter on One product
        if self.product_id:
            domain += ' AND product_id = %s'
            args += (self.product_id.id,)
            products_to_filter |= self.product_id
        #case 4: Filter on A Pack
        if self.package_id:
            domain += ' AND package_id = %s'
            args += (self.package_id.id,)
        #case 5: Filter on One product category + Exahausted Products
        if self.category_id:
            categ_products = Product.search([('categ_id', 'child_of', self.category_id.id)])
            domain += ' AND product_id = ANY (%s)'
            args += (categ_products.ids,)
            products_to_filter |= categ_products

        self.env.cr.execute("""SELECT stock_quant.id as quant_id, product_id, sum(quantity) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
            FROM stock_quant
            LEFT JOIN product_product
            ON product_product.id = stock_quant.product_id
            WHERE %s
            GROUP BY stock_quant.id, product_id, location_id, lot_id, package_id, partner_id """ % domain, args)

        for product_data in self.env.cr.dictfetchall():
            # replace the None the dictionary by False, because falsy values are tested later on
            for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                product_data[void_field] = False
            product_data['theoretical_qty'] = product_data['product_qty']
            product_data['quant_id'] = product_data['quant_id']
            if product_data['product_id']:
                product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
                quant_products |= Product.browse(product_data['product_id'])
            vals.append(product_data)
        if self.exhausted:
            exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
            vals.extend(exhausted_vals)
        return vals

    def _get_exhausted_inventory_line(self, products, quant_products):
        '''
        This function return inventory lines for exausted products
        :param products: products With Selected Filter.
        :param quant_products: products available in stock_quants
        '''
        vals = []
        exhausted_domain = [('type', 'not in', ('service', 'consu', 'digital'))]
        if products:
            exhausted_products = products - quant_products
            exhausted_domain += [('id', 'in', exhausted_products.ids)]
        else:
            exhausted_domain += [('id', 'not in', quant_products.ids)]
        exhausted_products = self.env['product.product'].search(exhausted_domain)
        for product in exhausted_products:
            vals.append({
                'inventory_id': self.id,
                'product_id': product.id,
                'location_id': self.location_id.id,
                'product_uom_id': product.uom_id.id,
            })
        return vals

    
    # @api.depends('line_ids')
    # def _compute_adjusted_qty(self):
    #     for rec in self:
    #         # for line in rec.line_ids:
    #         #     if line.theoretical_qty != l.product_qty):
    #         #     print("....line",line.product_id.name)
    #         #
    #
    #         adjusted_qty_values = []
    #         for line in rec.line_ids:
    #             adjusted_qty_values.append((0, 0, {
    #                 'product_id': line.product_id.id,
    #                  'product_uom_id':line.product_id.uom_id.id,
    #                  'location_id':line.location_id.id
    #                 # 'quantity': line.product_qty,  # Adjusted quantity
    #                 # Add other relevant fields as needed
    #             }))
    #
    #         self.write({
    #         'adjusted_qty_ids': adjusted_qty_values
    #     })
                        
            # self.adjusted_qty_ids=[(0,0,{'product_id':line.product_id.id,'product_uom_id':line.product_id.uom_id.id,'location_id':line.location_id.id}) for line in self.line_ids.filtered(lambda l: l.theoretical_qty != l.product_qty)]

                # if line.product_id:
                #     if line.theoretical_qty != line.product_qty:
                #         print("....")
                # # if rec.line_ids:
                #         self.adjusted_qty_ids.write({'product_id': line.product_id.id})
                #         print("....product",line.product_id.id, self.adjusted_qty_ids.product_id.name )
                #
                #

    

class InventoryLine(models.Model):
    _name = "stock.inventory.line"
    _description = "Inventory Line"
    _order = "product_id, inventory_id, location_id, prod_lot_id"

    inventory_id = fields.Many2one(
        'stock.inventory', 'Inventory',
        index=True, ondelete='cascade')
    
    # adjusted_id = fields.Many2one('stock.inventory','Adjusted')
    partner_id = fields.Many2one('res.partner', 'Owner')
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', '=', 'product')],
        index=True, required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure')
    product_uom_category_id = fields.Many2one(string='Uom category', related='product_uom_id.category_id')
    product_qty = fields.Float(
        'Checked Quantity',compute="_compute_counted_qty",
        digits='Product Unit of Measure', store=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        index=True, required=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Pack', index=True)

    adj_yes_no = fields.Selection(string='Adj Qty Y/N', selection=[
        ('yes', 'Yes'),
        ('no', 'No'),],
        related='inventory_id.adj_yes_no', store=True,
        copy=False, index=True,)

    prod_lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial Number')
    company_id = fields.Many2one(
        'res.company', 'Company', related='inventory_id.company_id',
        index=True, readonly=True, store=True)
    # TDE FIXME: necessary ? -> replace by location_id
    state = fields.Selection(
        string='Status',  related='inventory_id.state', readonly=True)
    theoretical_qty = fields.Float(
        'O/H Qty', compute='_compute_theoretical_qty',
        digits='Product Unit of Measure', readonly=True, store=True)
    inventory_location_id = fields.Many2one(
        'stock.location', 'Inventory Location', related='inventory_id.location_id', related_sudo=False, readonly=False)
    product_tracking = fields.Selection(string='Tracking', related='product_id.tracking', readonly=True)

    quant_id = fields.Many2one('stock.quant', string='Quants')
    reason_id = fields.Many2one('stock.adjustment.reason', string='Reason')
    remarks = fields.Char('Remarks')

    si_analytic_account_id = fields.Many2one(
        string="Analytic Account", comodel_name="account.analytic.account", readonly=True
    )
    counted_qty = fields.Float('Counted Qty',  digits='Product Unit of Measure',compute='_compute_counted_qty', store=True)

    @api.onchange('location_id')
    def _update_analytic_account(self):
        for rec in self:
            if rec.location_id:
                # Access the parent warehouse_id from the location_id
                warehouse_id = rec.location_id.warehouse_id
                if warehouse_id:
                    # Access the analytic_id from the parent warehouse
                    analytic_account = warehouse_id.analytic_id
                    # Update the analytic_account_id field with the new value
                    rec.si_analytic_account_id = analytic_account

    
    # @api.depends('theoretical_qty','counted_qty','adj_yes_no','product_qty')
    # def _compute_counted_qty(self):
    #     self.product_qty = 0.0
    #     self.counted_qty = 0.0
    #     for rec in self:
    #         if rec.adj_yes_no == 'yes':
    #             rec.product_qty = rec.theoretical_qty + rec.counted_qty
    #         if rec.adj_yes_no == 'no':
    #             rec.counted_qty = rec.theoretical_qty -  rec.product_qty
    @api.depends('theoretical_qty', 'counted_qty', 'adj_yes_no', 'product_qty')
    def _compute_counted_qty(self):
        for rec in self:
            if rec.adj_yes_no == 'yes':
                rec.product_qty = rec.theoretical_qty + rec.counted_qty
            elif rec.adj_yes_no == 'no':
                rec.counted_qty = rec.product_qty - rec.theoretical_qty

    @api.depends('location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id')
    def _compute_theoretical_qty(self):
        # self.ensure_one()
        for rec in self:
            if not rec.product_id:
                rec.theoretical_qty = 0
                return
            theoretical_qty = rec.product_id.get_theoretical_quantity(
                rec.product_id.id,
                rec.location_id.id,
                lot_id=rec.prod_lot_id.id,
                package_id=rec.package_id.id,
                owner_id=rec.partner_id.id,
                to_uom=rec.product_uom_id.id,
            )
            rec.theoretical_qty = theoretical_qty
            
            # rec.unit_cost = rec.product_id.standard_price
            # rec.subtotal = theoretical_qty * rec.product_id.standard_price


            


    @api.onchange('product_id')
    def _onchange_product(self):
        # If no UoM or incorrect UoM put default one from product
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            # self.unit_cost = self.product_id.standard_price
            # self.subtotal = self.theoretical_qty * self.product_id.standard_price

class ProductProduct(models.Model):

    _inherit = 'product.product'

    @api.model
    def get_theoretical_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None,
                                 to_uom=None):
        product_id = self.env['product.product'].browse(product_id)
        product_id.check_access_rights('read')
        product_id.check_access_rule('read')

        location_id = self.env['stock.location'].browse(location_id)
        lot_id = self.env['stock.lot'].browse(lot_id)
        package_id = self.env['stock.quant.package'].browse(package_id)
        owner_id = self.env['res.partner'].browse(owner_id)
        to_uom = self.env['uom.uom'].browse(to_uom)
        quants = self.env['stock.quant']._gather(product_id, location_id, lot_id=lot_id, package_id=package_id,
                                                 owner_id=owner_id, strict=True)
        if lot_id:
            quants = quants.filtered(lambda q: q.lot_id == lot_id)
        theoretical_quantity = sum([quant.quantity for quant in quants])
        if to_uom and product_id.uom_id != to_uom:
            theoretical_quantity = product_id.uom_id._compute_quantity(theoretical_quantity, to_uom)
        return theoretical_quantity


class StockLot(models.Model):
    _inherit = 'stock.lot'

    product_id = fields.Many2one(
        'product.product', 'Product', index=True)