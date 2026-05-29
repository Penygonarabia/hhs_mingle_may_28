# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,AccessError

class DealerSalesTarget(models.Model): 
    _name = 'dealer.sales.target'
    _description = 'Dealer Sales Target'
    _rec_name = 'sale_dealer_id'

    # -------------------
    # Core Foreign Keys
    # -------------------

    dealer_id = fields.Many2one(
        'res.partner',
        string='Dealer',
        domain=[('dealersalesman_required', '=', True)],
        required=True
    )
    dealer_showroom_id = fields.Many2one(
        'dsales.showroom',
        string='Dealer Showroom',
        required=True,
        domain="[('dealer_id', '=', dealer_id)]"
    )
    sale_dealer_id = fields.Many2one(
       'res.users',
        string='Salesman',
        domain="[('id','in', sale_dealer_user_ids)]",
        required=True,
    )

    sale_dealer_user_ids = fields.Many2many(
        'res.users',
        compute='_compute_dealer_users',
        store=False
    )   


    @api.depends('dealer_id', 'dealer_showroom_id')
    def _compute_dealer_users(self):
        for rec in self:
            rec.sale_dealer_user_ids =False
            if rec.dealer_id and rec.dealer_showroom_id:
                assignments = self.env['dsales.assignment'].search([
                    ('dealer_id', '=', rec.dealer_id.id),
                    ('dealer_showroom_id', '=', rec.dealer_showroom_id.id),
                    ('active', '=', True)
                ])

                # Only include users linked to dealers
                rec.sale_dealer_user_ids = assignments.sale_dealer_id
            else:

                emp_dealer = self.env['hr.employee'].search([
                    ('address_home_id.dealersalesman_required', '=', True),
                    ('user_id', '!=', False),
                    ('state','=','draft')
                ])
                # for emp in emp_dealer:
                #     print("..........emp",emp.name)
                # user_search= self.env['res.users'].search([('id','in',emp_dealer.user_id.ids)])
                rec.sale_dealer_user_ids = emp_dealer.mapped('user_id')

   
    franchise_id = fields.Many2one(
        'product.category',
        string='Franchise'
    )
    group_id = fields.Many2one(
        'product.category',
        string='Product Group'
    )
    subgroup_id = fields.Many2one(
        'product.category',
        string='Product Sub Group'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Model'
    )

    # -------------------
    # Related / Display Fields
    # -------------------
    dealer_code = fields.Char(related='dealer_id.ref', string='Dealer Code', store=True)
    dealer_name = fields.Char(related='dealer_id.name', string='Dealer Name', store=True)

    showroom_code = fields.Char(related='dealer_showroom_id.dealer_showroom_code', string='Shop Code', store=True)
    showroom_name = fields.Char(related='dealer_showroom_id.name', string='Shop Name', store=True)
    region = fields.Char(related='dealer_showroom_id.region_id.name', string='Region', store=True)
    city = fields.Char(related='dealer_showroom_id.city.name', string='City', store=True)
    location = fields.Text(related='dealer_showroom_id.address', string='Location', store=True)

    salesman_code = fields.Char( string='Salesman Code', store=True)
    salesman_name = fields.Char( string='Salesman Name', store=True)
    mobile_no = fields.Char( string='Mobile No', store=True)

    franchise_code = fields.Char(related='franchise_id.code', string='Franchise Code', store=True)
    franchise_name = fields.Char(related='franchise_id.name', string='Franchise Name', store=True)

    product_group_code = fields.Char(related='group_id.code', string='Product Group Code', store=True) 
    product_group_name = fields.Char(related='group_id.name', string='Product Group Name', store=True)

    subgroup_code = fields.Char(related='subgroup_id.code', string='Sub Group Code', store=True)
    subgroup_name = fields.Char(related='subgroup_id.name', string='Sub Group Name', store=True)

    # -------------------
    # Other Fields
    # -------------------
    capacity = fields.Char(string="Capacity")
    year = fields.Selection(
        [(str(y), str(y)) for y in range(2020, 2036)],
        string="Year",
        required=True
    )
    month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string="Month", required=True)
    target_qty = fields.Integer(string="Target Quantity", required=True)
    actual_qty = fields.Integer(string="Actual Quantity", default=0)

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        user = self.env.user

        # Check if user has BOTH backoffice AND readonly groups
        has_both_groups = (
                user.has_group('dealer.group_dealer_backoffice_user') and
                user.has_group('dealer.group_dealer_sales_readonly')
        )

        # If user has both groups, restrict write operations
        if has_both_groups and operation in ['write', 'create', 'unlink']:
            if raise_exception:
                raise AccessError(_("You have read-only access to sales records."))
            return False

        return super().check_access_rights(operation, raise_exception)


    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        user = self.env.user
        readonly_group = user.has_group('dealer.group_dealer_sales_donotshow')

        if readonly_group:
            return self.browse([])

        return super(DealerSalesTarget, self).search_fetch(
            domain, field_names, offset, limit, order
        )