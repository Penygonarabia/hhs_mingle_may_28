# -*- coding: utf-8 -*-
from odoo import models, fields,api


class SalesTarget(models.Model):
    _name = 'sales.target'
    _description = 'Sales Target'

    # -------------------
    # Core Foreign Keys
    # -------------------

    dealer_id = fields.Many2one(
        'res.partner',
        string='Dealer',
        domain=[('is_dealer', '=', True)],
        required=True
    )
    showroom_id = fields.Many2one(
        'promoter.showroom',
        string='Showroom',
        required=True,
        domain="[('dealer_id', '=', dealer_id)]"
    )
    promoter_id = fields.Many2one(
       'res.users',
        string='Promoter',
        domain="[('id','in', promoter_user_ids)]",
        required=True,
    )

    promoter_user_ids = fields.Many2many(
        'res.users',
        compute='_compute_promoter_users',
        store=False
    )

    @api.depends('dealer_id', 'showroom_id')
    def _compute_promoter_users(self):
        for rec in self:
            rec.promoter_user_ids =False
            if rec.dealer_id and rec.showroom_id:
                assignments = self.env['promoter.assignment'].search([
                    ('dealer_id', '=', rec.dealer_id.id),
                    ('showroom_id', '=', rec.showroom_id.id),
                    ('active', '=', True)
                ])

                # Only include users linked to promoters
                rec.promoter_user_ids = assignments.promoter_id
            else:

                emp_promoter = self.env['hr.employee'].search([
                    ('is_promoter', '=', True),
                    ('user_id', '!=', False),
                    ('state','=','draft')
                ])
                # for emp in emp_promoter:
                #     print("..........emp",emp.name)
                # user_search= self.env['res.users'].search([('id','in',emp_promoter.user_id.ids)])
                rec.promoter_user_ids = emp_promoter.mapped('user_id')

   
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

    showroom_code = fields.Char(related='showroom_id.code', string='Shop Code', store=True)
    showroom_name = fields.Char(related='showroom_id.name', string='Shop Name', store=True)
    region = fields.Char(related='showroom_id.region_id.name', string='Region', store=True)
    city = fields.Char(related='showroom_id.city.name', string='City', store=True)
    location = fields.Text(related='showroom_id.address', string='Location', store=True)

    promoter_code = fields.Char( string='Promoter Code', store=True)
    promoter_name = fields.Char( string='Promoter Name', store=True)
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