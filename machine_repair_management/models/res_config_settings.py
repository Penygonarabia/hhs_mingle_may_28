from odoo import fields, api, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    maintenance_service_show = fields.Boolean(
        string="Maintenance contract required (Yes/ No).",
        default=False,
        config_parameter="machine_repair_management.maintenance_service_show",
    )
    internal_service_show = fields.Boolean(
        string="Internal maintenance required (Yes/ No).",
        default=False,
        config_parameter="machine_repair_management.internal_service_show",
    )
    job_card_show = fields.Boolean(
        string="Use request # itself as job card #",
        default=False,
        config_parameter="machine_repair_management.job_card_show",
    )
    project_bool = fields.Boolean(
        "Default Project (Yes/ No).",
        default=False,
        config_parameter="machine_repair_management.project_bool",
    )
    # project_id = fields.Many2one(
    #     'project.project',
    #     string='Project',
    #     default=lambda self: self.env['project.project'].search([('name', '=', 'HHS')], limit=1)
    # )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        default=False,
        config_parameter="machine_repair_management.project_id",
    )

    inspection_amount = fields.Float(
        string="Inspection Charge",
        default=False,
        config_parameter="machine_repair_management.inspection_amount",
    )

    """ This code is used for when we create the payment receipt from the job card it will show inspection charges code and description done by Vijaya bhaskar on Jun -10-2025 """
    inspection_charges_description = fields.Char(
        string="Inspection Charges Description",
        config_parameter="machine_repair_management.inspection_charges_description",
    )

    inspection_charges_code = fields.Char(
        string="Inspection Charges Code",
        config_parameter="machine_repair_management.inspection_charges_code",
    )

    job_card_closed_time_enable = fields.Boolean(
        string="Job Card Completed Time Enable/Disable",
        default=False,
        help="Enable/Disable the job card Completed Date/Time",
        config_parameter="machine_repair_management.job_card_closed_time_enable",
    )

    supervisor_service_product_add = fields.Boolean(
        string="Supervisor Add Service Record",
        default=False,
        help="Supervisor user add the service product/Not",
        config_parameter="machine_repair_management.supervisor_service_product_add",
    )

    technician_service_product_add = fields.Boolean(
        string="Technician Add Service Record",
        default=False,
        help="Technician user add the service Product/Not",
        config_parameter="machine_repair_management.technician_service_product_add",
    )

    parts_service_product_add = fields.Boolean(
        string="Parts Add Service Record",
        default=False,
        help="Parts User add the service Record/Not",
        config_parameter="machine_repair_management.parts_service_product_add",
    )

    supervisor_parts_product_add = fields.Boolean(
        string="Supervisor Add Parts Record",
        default=False,
        help="Supervisor User add the Parts Product/Not",
        config_parameter="machine_repair_management.supervisor_parts_product_add",
    )

    technician_parts_product_add = fields.Boolean(
        string="Technician Add Parts Record",
        default=False,
        help="Technician user add the Parts Product/Not",
        config_parameter="machine_repair_management.technician_parts_product_add",
    )

    parts_user_parts_product_add = fields.Boolean(
        string="Parts Add Parts Record",
        default=False,
        help="Parts User add the Parts Record/Not",
        config_parameter="machine_repair_management.parts_user_parts_product_add",
    )

    whatsapp_send_bool = fields.Boolean(
        string="Whatsapp Send",
        default=False,
        help="All Whatsapp Send feature Enable/Not",
        config_parameter="machine_repair_management.whatsapp_send_bool",
    )

    sequence_creation_bool = fields.Boolean(
        string="Sequence Creation",
        default=False,
        help="Sequence Creation Based on the Machine Repair Management",
        config_parameter="machine_repair_management.sequence_creation_bool",
    )

    negative_stock_allow = fields.Boolean(
        string="Allow Negative Stock",
        default=False,
        help="Skip Validation for On Hand Qty Stock has zero quantity",
        config_parameter="machine_repair_management.negative_stock_allow",
    )

    make_interface_code = fields.Boolean(
        string="Make Interface Code Mandatory",
        default=False,
        help="Make Interface Code Mandatory",
        config_parameter="machine_repair_management.make_interface_code",
    )

    no_of_technician_visit = fields.Float(
        string="No.of Technician/Visit",
        config_parameter="machine_repair_management.no_of_technician_visit",
    )

    warranty_expiry_enable = fields.Boolean(
        string="Enable Warranty Expiry Validation",
        default=False,
        config_parameter="machine_repair_management.warranty_expiry_enable",
        help="Enable/Disable warranty expiry validation",
    )

    labor_cost_hr = fields.Float(
        string="Labor Cost/HR",
        config_parameter="machine_repair_management.labor_cost_hr",
    )

    units_serviced_visit = fields.Float(
        string="Units Serviced/Visit",
        config_parameter="machine_repair_management.units_serviced_visit",
    )

    travel_hr_for_people = fields.Float(
        string="Travel Hours",
        config_parameter="machine_repair_management.travel_hr_for_people",
    )

    gross_profit = fields.Float(
        string="Service Gross Margin",
        config_parameter="machine_repair_management.gross_profit",
    )

    add_paid_service_price = fields.Float(
        string="Additional Paid Service Price",
        config_parameter="machine_repair_management.add_paid_service_price",
    )
    installment_product_id = fields.Many2one(
        "product.template",
        string="Installment Product",
        config_parameter="machine_repair_management.installment_product_id",
    )

    spare_parts_gross_profit = fields.Float(
        string="Spare Parts Gross Margin",
        config_parameter="machine_repair_management.spare_parts_gross_profit",
    )

    asset_tag_sequence_creation_bool=fields.Boolean(string="Asset Tag Sequence Creation", default=False, help = "Sequence Creation Based on the Machine Repair Management",config_parameter = "machine_repair_management.asset_tag_sequence_creation_bool")

    '''Code Added on June 05 2026 by Vijaya Bhaskar '''
    
    invoice_txt_contract = fields.Char(string = "Invoice Text Contract", config_parameter = "machine_repair_management.invoice_txt_contract")
    
    '''Code Added on June 23 2026 by Vijaya Bhaskar'''
    
    notify_salesman_sixty_day = fields.Integer(string = "Notify Salesman 60 days before contract Expiration",config_parameter ='machine_repair_management.notify_salesman_sixty_day')

    notify_manager_thirty_day = fields.Integer(string = "Notify Manager 30 Days before Contract Expiration", config_parameter = 'machine_repair_management.notify_manager_thirty_day')
    

    '''Code Added on July 09 2026 by Vijaya Bhaskar client asked model is shown based on the country selected'''

    manufacturing_country_code = fields.Boolean(string = "Manufacturing Country Code", default = False, help = "Manufacturing Country Code Y/N",
                                                config_parameter = "machine_repair_management.manufacturing_country_code")
    
    
    filtering_data_by_country = fields.Char(string = "Filtering Data", default = "KSA", config_parameter = "machine_repair_management.filtering_data_by_country" , help = "Filtering Data Based on the country should be visible in the Model")
    
    

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env["ir.config_parameter"].sudo()
        # project_id = int(params.get_param('machine_repair_management.project_id', default=False))
        installment_product_param = params.get_param(
            "machine_repair_management.installment_product_id", default=""
        )
        installment_product_id = (
            int(installment_product_param) if installment_product_param else False
        )
        res.update(
            maintenance_service_show=params.get_param(
                "machine_repair_management.maintenance_service_show"
            ),
            internal_service_show=params.get_param(
                "machine_repair_management.internal_service_show"
            ),
            job_card_show=params.get_param("machine_repair_management.job_card_show"),
            # project_id=params.get_param('machine_repair_management.project_id'),
            # project_id = params.get_param('machine_repair_management.project_id'),
            project_bool=params.get_param("machine_repair_management.project_bool"),
            inspection_amount=params.get_param(
                "machine_repair_management.inspection_amount"
            ),
            inspection_charges_description=params.get_param(
                "machine_repair_management.inspection_charges_description"
            ),
            inspection_charges_code=params.get_param(
                "machine_repair_management.inspection_charges_code"
            ),
            job_card_closed_time_enable=params.get_param(
                "machine_repair_management.job_card_closed_time_enable"
            ),
            supervisor_service_product_add=params.get_param(
                "machine_repair_management.supervisor_service_product_add"
            ),
            technician_service_product_add=params.get_param(
                "machine_repair_management.technician_service_product_add"
            ),
            parts_service_product_add=params.get_param(
                "machine_repair_management.parts_service_product_add"
            ),
            supervisor_parts_product_add=params.get_param(
                "machine_repair_management.supervisor_parts_product_add"
            ),
            technician_parts_product_add=params.get_param(
                "machine_repair_management.technician_parts_product_add"
            ),
            parts_user_parts_product_add=params.get_param(
                "machine_repair_management.parts_user_parts_product_add"
            ),
            whatsapp_send_bool=params.get_param(
                "machine_repair_management.whatsapp_send_bool"
            ),
            sequence_creation_bool=params.get_param(
                "machine_repair_management.sequence_creation_bool"
            ),
            negative_stock_allow=params.get_param(
                "machine_repair_management.negative_stock_allow"
            ),
            make_interface_code=params.get_param(
                "machine_repair_management.make_interface_code"
            ),
            warranty_expiry_enable=params.get_param(
                "machine_repair_management.warranty_expiry_enable"
            ),
            no_of_technician_visit=float(
                params.get_param(
                    "machine_repair_management.no_of_technician_visit", default=0.0
                )
            ),
            labor_cost_hr=float(
                params.get_param("machine_repair_management.labor_cost_hr", default=0.0)
            ),
            units_serviced_visit=float(
                params.get_param(
                    "machine_repair_management.units_serviced_visit", default=0.0
                )
            ),
            travel_hr_for_people=float(
                params.get_param(
                    "machine_repair_management.travel_hr_for_people", default=0.0
                )
            ),
            gross_profit=float(
                params.get_param("machine_repair_management.gross_profit", default=0.0)
            ),
            add_paid_service_price=float(
                params.get_param(
                    "machine_repair_management.add_paid_service_price", default=0.0
                )
            ),
            installment_product_id=installment_product_id,
            asset_tag_sequence_creation_bool=params.get_param('machine_repair_management.asset_tag_sequence_creation_bool'),
            invoice_txt_contract = params.get_param('machine_repair_management.invoice_txt_contract'),
            notify_salesman_sixty_day = params.get_param('machine_repair_management.notify_salesman_sixty_day'),
            notify_manager_thirty_day = params.get_param('machine_repair_management.notify_manager_thirty_day'),
            manufacturing_country_code = params.get_param('machine_repair_management.manufacturing_country_code'),
            
            filtering_data_by_country = params.get_param('machine_repair_management.filtering_data_by_country', default='KSA'),
            
            
            
            

        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        installment_product_id_str = (
            str(self.installment_product_id.id) if self.installment_product_id else ""
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.maintenance_service_show",
            self.maintenance_service_show,
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.internal_service_show",
            self.internal_service_show,
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.job_card_show", self.job_card_show
        )
        # self.env['ir.config_parameter'].sudo().get_param('machine_reapir_management.project_id', self.project_id)
        # self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.project_id', self.project_id)

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.project_bool", self.project_bool
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.inspection_amount", self.inspection_amount
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.inspection_charges_description",
            self.inspection_charges_description,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.inspection_charges_code",
            self.inspection_charges_code,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.job_card_closed_time_enable",
            self.job_card_closed_time_enable,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.supervisor_service_product_add",
            self.supervisor_service_product_add,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.technician_service_product_add",
            self.technician_service_product_add,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.parts_service_product_add",
            self.parts_service_product_add,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.supervisor_parts_product_add",
            self.supervisor_parts_product_add,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.technician_parts_product_add",
            self.technician_parts_product_add,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.parts_user_parts_product_add",
            self.parts_user_parts_product_add,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.whatsapp_send_bool", self.whatsapp_send_bool
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.sequence_creation_bool",
            self.sequence_creation_bool,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.negative_stock_allow", self.negative_stock_allow
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.make_interface_code", self.make_interface_code
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.warranty_expiry_enable",
            self.warranty_expiry_enable,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.no_of_technician_visit",
            self.no_of_technician_visit,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.labor_cost_hr", self.labor_cost_hr
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.units_serviced_visit", self.units_serviced_visit
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.travel_hr_for_people", self.travel_hr_for_people
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.gross_profit", self.gross_profit
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.add_paid_service_price",
            self.add_paid_service_price,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "machine_repair_management.installment_product_id",
            installment_product_id_str,
        )
        self.env['ir.config_parameter'].sudo().set_param('machine_repair_management.asset_tag_sequence_creation_bool', self.asset_tag_sequence_creation_bool)
        
        self.env['ir.config_parameter'].sudo().set_param('machine_repair_management.invoice_txt_contract',self.invoice_txt_contract)
        
        self.env['ir.config_parameter'].sudo().set_param('machine_repair_management.notify_salesman_sixty_day',self.notify_salesman_sixty_day)
        
        self.env['ir.config_parameter'].sudo().set_param('machine_repair_management.notify_manager_thirty_day',self.notify_manager_thirty_day)
        
        self.env['ir.config_parameter'].sudo().set_param('machine_repair_management.manufacturing_country_code', self.manufacturing_country_code)
        
        self.env['ir.config_parameter'].sudo().set_param('machine_repair_management.filtering_data_by_country',self.filtering_data_by_country)
        
        
        return res
