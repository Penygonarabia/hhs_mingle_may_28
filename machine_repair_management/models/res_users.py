from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    def_location_id = fields.Many2one("hr.work.location", string="Default Location")
    def_department_id = fields.Many2one("hr.department", string="Default Department")
    is_default_member = fields.Boolean(string="Default Team Member", default=False)
    default_work_center_id = fields.Many2many(
        "work.center.location", string="Default Work Center"
    )
    user_code = fields.Char(string="Interface Code")
    project_ids = fields.Many2many("project.project", string="Project")
    discount_limit = fields.Float(string="Maximum Allowed Margin Discount %")
    warehouse_category_user_line_ids = fields.One2many(
        "res.users.line", "user_id", string="Allowed Warehouse"
    )

    # default_technician_warehouse_id = fields.Many2one('stock.warehouse', string = "Default Technician Warehouse",deprecated =False)

    # property_warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse', company_dependent=True, check_company=True,store = True,index=True)

    """Default Warehouse is not used for import Excel so we use warehouse_id to replace Property_warehouse_id on August 28-2025"""
    # warehouse_id = fields.Many2one('stock.warehouse',string = "Default Warehouse" , store = True,deprecated =False)

    # @api.onchange('warehouse_id')
    # def _onchange_warehouse_id(self):
    #     for rec in self:
    #         if rec.warehouse_id:
    #             rec.property_warehouse_id = rec.warehouse_id.id or None

    # @api.constrains('user_code')
    # def _check_user_code(self):
    #   for rec in self:
    #    code_search = self.env['res.users'].search([('user_code','=',rec.user_code),('id','!=',rec.id)])
    #  if len(code_search) > 1:
    #    raise ValidationError('User code is Unique One.Please give another One')

    _sql_constraints = [
        ("unique_user_code", "unique(user_code)", "Interface Code must be unique!")
    ]

    @api.constrains("user_code")
    def _check_interface_code_required(self):
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.make_interface_code")
        )
        if param == "True":
            for rec in self:
                if not rec.user_code:
                    raise ValidationError(_("Interface Code is mandatory."))
                self.env.cr.execute(
                    """
                        SELECT 1 FROM sl_salesmandesc
                        WHERE sm_code = %s
                        LIMIT 1
                    """,
                    (rec.user_code,),
                )

                if not self.env.cr.fetchone():
                    raise ValidationError(
                        _("Interface Code must exist in Salesman Master.")
                    )


class ResUsersLine(models.Model):
    _name = "res.users.line"
    _description = "Res Users Line"

    user_id = fields.Many2one("res.users", string="User")
    product_category_line_id = fields.Many2one(
        "product.category", string="Product Category"
    )
    warehouse_line_id = fields.Many2one("stock.warehouse", string="Default Warehouse")
    # warehouse_lst_ids = fields.Many2many('stock.warehouse', string ="Warehouse list", related='user_id.available_warehouse_ids')
    warehouse_lst_ids = fields.Many2many(
        "stock.warehouse",
        string="Warehouse List",
        compute="_compute_warehouse_lst_ids",
        store=False,
    )

    @api.depends("user_id", "user_id.available_warehouse_ids")
    def _compute_warehouse_lst_ids(self):
        all_warehouses = self.env["stock.warehouse"].search([])

        for rec in self:
            if rec.user_id and rec.user_id.available_warehouse_ids:
                rec.warehouse_lst_ids = rec.user_id.available_warehouse_ids
            else:
                rec.warehouse_lst_ids = all_warehouses

    @api.constrains("product_category_line_id", "warehouse_line_id", "user_id")
    def validity_check_product_category(self):
        for rec in self:
            if rec.product_category_line_id and rec.warehouse_line_id:
                warehouse_search = self.env["res.users.line"].search(
                    [
                        (
                            "product_category_line_id",
                            "=",
                            rec.product_category_line_id.id,
                        ),
                        ("warehouse_line_id", "=", rec.warehouse_line_id.id),
                        ("user_id", "=", rec.user_id.id),
                    ]
                )
                if len(warehouse_search) > 1:
                    raise ValidationError(
                        "Already Product Category and Default warehouse is there"
                    )
