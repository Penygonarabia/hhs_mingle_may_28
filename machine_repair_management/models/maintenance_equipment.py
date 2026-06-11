from odoo import api, fields, models, _, re
from odoo.exceptions import ValidationError
from odoo.tools import float_round

class MaintenanceEquipmentViews(models.Model):
    _inherit = "maintenance.equipment"

    # contracts_no_ids = fields.One2many(
    #     'subscription.contracts',  # related model
    #     'contract_reference_id',  # inverse field (must exist there)
    #     string="Contracts"
    # )
    contract_id = fields.Many2one("subscription.contracts", string="Contract No")
    service_products_code_id = fields.Many2one(
        "product.product", string="Service Unit Type"
    )
    product_unit_type_ids = fields.Many2many(
        "product.product",
        string="Unit Ids",
        compute="_compute_product_unit_type_ids",
        store=True,
    )
    # service_product_code_id=fields.One2many('product.product','contract_id',string="Service Product Code")
    brand = fields.Char(string="Brand")
    description = fields.Char(string="Project Name")
    customer = fields.Char(string="Customer Name")
    contract_start_date = fields.Date(string="Contract Start Date")
    contract_end_date = fields.Date(string="Contract End Date")
    no_of_visits = fields.Integer(string="No of Visits/Year")
    service_group_batch = fields.Char(string="Service Group Batch No")

    task_count = fields.Integer(compute="_compute_task_count", string="Job Card")
    
    '''Code Added on May 11 2026 by Vijaya Bhaskar'''
    pm_service_count = fields.Integer(string = "PM Service Count",default =1, help = "Service Visit First or Second")
    
    emergency_count = fields.Integer(string = "Emergency Count", default =1, help = "Emergency Count")
    
    '''Code Added on May 14 2026 by Vijaya bhaskar'''
    product_ordered_count = fields.Integer(string = "Product Ordered Count",compute = "_compute_product_ordered_count", store = False)
    
    
    '''Code Added on May 22 2026 by Vijaya Bhaskar'''
    customer_code = fields.Char(string = "Customer Code")
    
    warehouse_id = fields.Many2one('stock.warehouse',string = "Warehouse")
    
    work_center_id = fields.Many2one('work.center.location', string = "Work center")
    
    work_center_group_id = fields.Many2one('work.center.group', string = "Work Center  Group")
    
    district = fields.Many2one('res.state.district',string = "District")
    
    '''Code Added on May 26 2026 by Vijaya Bhaskar '''
    
    sales_person_user_id = fields.Many2one('res.users', string  = "SalesPerson")
    
    '''Code Added on June 08 2026 by Vijaya Bhaskar'''
    
    items_from_own_company_bool = fields.Boolean(string = "Items From Own Company",default = False, help = "When the brand have product category and service unit type have same product category")
    
    product_product_model_id = fields.Many2one('product.product',string = "Product model")
    
    product_search_ids = fields.Many2many('product.product',
                                          "maintenance_equipment_search_rel", # different relation table
                                            "equipment_id",
                                            "product_id",
                                            string = "Product Search",
                                            compute = "_compute_product_search_ids",store = False)
                                            
    
    
    '''Code Added on June 08 2026 by Vijaya Bhaskar'''
    @api.depends('items_from_own_company_bool', 'service_products_code_id')
    def _compute_product_search_ids(self):
        for rec in self:
            rec.product_search_ids = False
    
            if rec.items_from_own_company_bool and rec.service_products_code_id:
                # products = self.env['product.product'].search([
                #     ('categ_id', '=', rec.service_products_code_id.categ_id.id)
                # ])
               
                products = self.env['product.product'].search([
                    ('product_category_id','=',rec.brand_id.amc_product_category_id.id),
                    ('product_group_id','=',rec.service_products_code_id.product_group_id.id)
                    ])

                
                rec.product_search_ids = [(6, 0, products.ids)]   
    
    
    # sequence_count = fields.Integer(string = "Sequence Integer Count",default = 1,deprecated = False)
    
    @api.depends('contract_id','service_products_code_id','contract_id.contract_line_ids')
    def _compute_product_ordered_count(self):
        for rec in self:
            rec.product_ordered_count=0
            if rec.contract_id:
                for line in rec.contract_id.contract_line_ids:
                    if line.product_id:
                        if line.product_id == rec.service_products_code_id:
                            rec.product_ordered_count = line.qty_ordered
    
    
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (
                    self.env["ir.config_parameter"]
                            .sudo()
                            .get_param("machine_repair_management.asset_tag_sequence_creation_bool")
                    == "True"
            ):
                #if vals.get("name", "New") == "New":
                if vals.get("name") in [False, None, "", "New"]:
                    contract_id = vals.get("contract_id")
                    contract_search = self.env["subscription.contracts"].browse(contract_id)
                    contract_name = contract_search.name or ""

                    # Remove AMC-
                    contract_name = contract_name.replace("AMC-", "")

                    # -------------------------------------------------
                    # Product Code
                    # -------------------------------------------------
                    product = self.env["product.product"].browse(
                        vals.get("service_products_code_id")
                    )

                    product_code = product.default_code or "PRD"

                    # -------------------------------------------------
                    # Running Sequence
                    # -------------------------------------------------
                    sequence_code = "maintances.equipment.contract"

                    # Example: 001
                    seq_no = self.env["ir.sequence"].next_by_code(sequence_code)
                    seq_no = re.sub(r'^[A-Za-z]+', '', seq_no)
                    seq_no = str(seq_no).zfill(3)
                    
                   
                    product_id = vals.get("service_products_code_id")

                    ordered_count = 0
                    
                    if contract_id and product_id:
                        contract = self.env["subscription.contracts"].browse(contract_id)
                    
                        line = contract.contract_line_ids.filtered(
                            lambda l: l.product_id.id == product_id
                        )[:1]
                    
                        ordered_count = line.qty_ordered if line else 0
                    # Final Sequence
                    equipment_search = self.env['maintenance.equipment'].search_count([('contract_id','=',contract_search.id),('service_products_code_id','=',product.id)])
                    
                    if equipment_search >=ordered_count :
                        raise ValidationError(_("Already all Contracts are created"))
                    
                    seq = f"{contract_name}/{product_code}-{equipment_search+1:03d}"
                    # seq = f"{contract_name}/{product_code}-{seq_no}"

                  
                    # seq_no = str(seq_no).zfill(3)
                    #
                    # # -------------------------------------------------
                    # # Final Sequence
                    # # -------------------------------------------------
                    # seq = f"{contract_search.name}/{product_code}-{seq_no.prefix}"

                    # -------------------------------------------------
                    # Duplicate Check
                    # -------------------------------------------------
                    if self.search([("name", "=", seq)], limit=1):
                        raise ValidationError(
                            f"Sequence '{seq}' already exists."
                        )

                    vals["name"] = seq

        equipments = super().create(vals_list)

        return equipments

    def _compute_task_count(self):
        for rec in self:
            domain = [
                ("contract_id", "=", rec.contract_id.id),
                ("asset_id", "=", rec.id),
                ("service_products_code_id", "=", rec.service_products_code_id.id),
            ]
            rec.task_count = self.env["project.task"].search_count(domain)

    def action_open_related_tasks(self):
        self.ensure_one()

        domain = [
            ("contract_id", "=", self.contract_id.id),
            ("asset_id", "=", self.id),
            ("service_products_code_id", "=", self.service_products_code_id.id),
        ]

        tree_view_id = self.env.ref(
            "machine_repair_management.view_project_task_tree"
        ).id
        form_view_id = self.env.ref(
            "machine_repair_management.view_project_task_form"
        ).id

        return {
            "type": "ir.actions.act_window",
            "name": "Related Tasks",
            "res_model": "project.task",
            "domain": domain,
            "view_mode": "tree,form",
            "views": [[tree_view_id, "tree"], [form_view_id, "form"]],
        }

    @api.constrains("no_of_visits")
    def _check_not_zero(self):
        for rec in self:
            if rec.no_of_visits == 0:
                raise ValidationError(
                    "Zero is not allowed in this field. Please enter a non-zero number."
                )

    @api.depends("contract_id")
    def _compute_product_unit_type_ids(self):
        for rec in self:
            rec.product_unit_type_ids = False
            line_product_lst = []
            for line in self.contract_id.contract_line_ids:
                line_product_lst.append(line.product_id.id)

            rec.product_unit_type_ids = line_product_lst

    @api.onchange("contract_id")
    def _onchange_contract_id(self):
        for rec in self:
            rec.description = rec.contract_id.reference or False
            rec.customer = rec.contract_id.partner_id.name or False
            rec.contract_start_date = rec.contract_id.date_start or False
            rec.contract_end_date = rec.contract_id.date_end or False
            rec.technician_user_id = rec.contract_id.technician_id.leader_id.id or False
            
            '''Code Added on May 22 2026 by Vijaya Bhaskar'''
            rec.customer_code = rec.contract_id.customer_code or False
            rec.warehouse_id = rec.contract_id.warehouse_id.id or False
            rec.work_center_id = rec.contract_id.work_center_id.id or False
            rec.work_center_group_id = rec.contract_id.work_center_group_id.id or False
            '''Code Added on May 26 2026 by Vijaya Bhaskar '''
            rec.sales_person_user_id = rec.contract_id.sales_person_user_id.id or False
            
            
