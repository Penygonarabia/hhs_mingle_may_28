import logging
from odoo import models, fields, api, _, re
from odoo.exceptions import ValidationError



_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ✅ Project Name
    name = fields.Char(
        'Project Name', index='trigram',
        compute='_compute_name', readonly=False, store=True)
    # name = fields.Char(string="Project Name", required=True)
    # email_from = fields.Char(required=True)
    email_from = fields.Char(
        'Email', tracking=40, index='trigram',
        compute='_compute_email_from', inverse='_inverse_email_from', readonly=False, store=True, required = False)
    phone = fields.Char(required=True)
    mobile = fields.Char()
    contact_name = fields.Char()
    function = fields.Char()
    partner_id = fields.Many2one('res.partner')
    partner_name = fields.Char(required=True)
    street = fields.Char(required=True)
    
    '''Code Added on May 22 2026 by Vijaya Bhaskar'''
    customer_code = fields.Char(string = "Customer Code")
    
    warehouse_id = fields.Many2one('stock.warehouse',string = "Warehouse")
    
    work_center_id = fields.Many2one('work.center.location', string = "Work Center")
    
    work_center_group_id = fields.Many2one('work.center.group', string = "Work Center Group")
    
    district = fields.Many2one('res.state.district',string = "District")
    
    '''Code Added on June 12 2026 by Vijaya Bhaskar client asked site address similar to address'''
    site_street = fields.Char(string = "Street")
    
    site_street2 = fields.Char(string = "Street2")
    
    site_customer_city_id = fields.Many2one('res.city', string = "Customer City")
    
    site_district_id  = fields.Many2one('res.state.district',string = "District")
    
    site_state_id = fields.Many2one('res.country.state', string = "State")
    
    site_country_id = fields.Many2one('res.country', string = "Country")
    
    site_zip = fields.Char(string = "Zip")
    
    '''Code Added on June 20 2026 by Vijaya Bhaskar'''
    customer_name = fields.Char(string = "Customer")

    
    @api.depends('partner_id', 'customer_name')
    def _compute_name(self):
        for lead in self:
            if not lead.name:
                partner_name = lead.partner_id.name or lead.customer_name
                if partner_name:
                    lead.name = _("%s's opportunity") % partner_name  

    # @api.depends('partner_id','customer_name')
    # def _compute_name(self):
    #     for lead in self:
    #         if not lead.name and lead.partner_id and lead.partner_id.name:
    #             lead.name = _("%s's opportunity") % lead.partner_id.name
    #             '''Code Added on June 22 2026 by Vijaya Bhaskar '''    
    #         elif lead.customer_name:
    #             lead.name = _("%s's opportunity") %  lead.customer_name  
    
    '''Code Added on June 12 2026 by Vijaya Bhaskar client asked site address similar to address'''

    @api.onchange('street','street2','state_id','country_id','district','zip','customer_city_id')
    def _onchange_address_customer(self):
        for rec in self:
            rec.site_street = rec.street or ''
            rec.site_street2 = rec.street2 or ''
            rec.site_state_id = rec.state_id.id or ''
            rec.site_customer_city_id = rec.customer_city_id.id or ''
            rec.site_district_id = rec.district.id or ''
            rec.site_country_id = rec.country_id.id or ''
            rec.site_zip = rec.zip or ''
    
    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        pass

    # @api.constrains('phone')
    # def _check_valid_phone_number(self):
    #     for rec in self:
    #         if rec.phone:
    #             if len(rec.phone) < 8 or len(rec.phone) > 15:
    #                 raise ValidationError(_(
    #                     "Mobile number must be 10 digits."
    #                 ))
    #             # Prevent all same digits like 0000000000, 1111111111
    #             if len(set(rec.phone)) == 1:
    #                 raise ValidationError(_(
    #                     "Mobile number cannot contain all identical digits."
    #                 ))

    @api.constrains('phone')
    def _check_valid_phone_number(self):
        for rec in self:
            if rec.phone:
                if len(rec.phone) != 10:
                    raise ValidationError(_(
                        "Mobile number must be 10 digits."
                    ))
                # Prevent all same digits like 0000000000, 1111111111
                if len(set(rec.phone)) == 1:
                    raise ValidationError(_(
                        "Mobile number cannot contain all identical digits."
                    ))

    """Code Added on March 18 2026"""
    type_of_property = fields.Selection(
        [("commercial", "Commercial"), ("residential", "Residential")],
        string="Type of Property",required="True"
    )

    property_type_maintenance_details_id = fields.Many2one(
        "property.type.maintenance.details", string="Function",required="True"
    )
    company_preventive_maintenance = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Any company currently performing preventive maintenance at the site ?",
        default=False,required="True"
    )

    company_preventive_maintenance_bool = fields.Boolean(
        string="Any company currently performing preventive maintenance at the site ?",
        default=False,
    )

    job_position = fields.Char(string="Job Position", required=True)

    hide_additional_fields = fields.Boolean(
        compute="_compute_hide_additional_fields",
        store=False
    )

    '''Code Added on March 21 2026 by Vijaya Bhaskar'''
    customer_city_id = fields.Many2one('res.city', string="Customer City")

    @api.onchange('partner_id')
    def _onchange_partner_city(self):
        self.customer_city_id = self.partner_id.customer_city_id.id or None
        
        '''Code Added on May 22 2026 by Vijaya Bhaskar'''

        self.work_center_id = self.partner_id.customer_city_id.def_work_center_id.id or False
        
        self.work_center_group_id = self.partner_id.customer_city_id.def_work_center_id.work_center_group_id.id or False
        
        self.district = self.partner_id.customer_city_id.country_district_id.id or False
        
        '''Code Added on May 23 2026 by Vijaya Bhaskar'''
        if self.partner_id.ref:
            self.customer_code = self.partner_id.ref
            
        pipeline_search = self.env['crm.lead'].search([('phone','=',self.phone),
                                                       ('partner_id','=',self.partner_id.id),
                                                       ('customer_code','=',self.customer_code)
                                                       ],limit=1)
            
        if pipeline_search:
            if pipeline_search.type_of_property and pipeline_search.property_type_maintenance_details_id and pipeline_search.company_preventive_maintenance and pipeline_search.partner_name:
                self.type_of_property = pipeline_search.type_of_property or False
                self.property_type_maintenance_details_id = pipeline_search.property_type_maintenance_details_id.id or False
                self.company_preventive_maintenance = pipeline_search.company_preventive_maintenance or False
                self.partner_name = pipeline_search.partner_name or False
                self.job_position = pipeline_search.job_position or False
                self.warehouse_id = pipeline_search.warehouse_id.id or False
        
        '''Code Added on june 20 2026 by Vijaya Bhaskar'''
        # if self.partner_id:
        self.customer_name = self.partner_id.name or False
        

    '''Code Added on May 22 2026 by Vijaya Bhaskar'''
    @api.onchange('phone')
    def _onchange_phone_number(self):
        customer_search = self.env['res.partner'].search([('mobile','=',self.phone),('mobile','!=',False)],limit =1)
        self.partner_id = customer_search.id
        
        
        
    '''Code Added on May 22 2026 by Vijaya Bhaskar'''
    @api.onchange('customer_city_id')
    def _onchange_customer_city(self):
        self.district = self.customer_city_id.country_district_id.id or False
        self.state_id = self.customer_city_id.state_id.id or False
        self.zip = self.customer_city_id.zipcode or False
        '''Code Added on May 25 2026 by Vijaya Bhaskar client asked a default country code as Saudi Arabia when we create a new Record'''
        if self.customer_city_id:
            self.country_id = self.customer_city_id.country_id.id or False
        '''Code Added on May 23 2026 by Vijaya Bhaskar'''
        self.work_center_id = self.customer_city_id.def_work_center_id.id or False
        
        self.work_center_group_id = self.customer_city_id.def_work_center_id.work_center_group_id.id or False
        
        self.district = self.customer_city_id.country_district_id.id or False
        
        if self.partner_id.ref:
            self.customer_code = self.partner_id.ref
    
    '''Code Added on May 25 2026 by Vijaya Bhaskar client asked a default country code as Saudi Arabia when we create a new Record'''
            
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        saudi = self.env.ref('base.sa', raise_if_not_found=False)
        if saudi:
            res['country_id']= saudi.id

        return res
    
    
    # def _compute_hide_additional_fields(self):
    #     param = self.env['ir.config_parameter'].sudo().get_param(
    #         'crm_custom_view.hide_additional_fields'
    #     )
    #     value = param == 'True'
    #
    #     _logger.info("==== CONFIG PARAM VALUE: %s ====", param)
    #     _logger.info("==== COMPUTED BOOLEAN VALUE: %s ====", value)
    #
    #     for rec in self:
    #         rec.hide_additional_fields = value
    #         _logger.info(
    #             "Record ID %s → hide_additional_fields = %s",
    #             rec.id, rec.hide_additional_fields
    #         )

    '''Code Added on April 04 2026 by Vijaya Bhaskar'''

    @api.depends('partner_id')
    def _compute_hide_additional_fields(self):
        for rec in self:
            rec.hide_additional_fields = False
            if self.env['ir.config_parameter'].sudo().get_param('crm_custom_view.hide_additional_fields') == 'True':
                rec.hide_additional_fields = True

    # @api.onchange('partner_id')
    # def _onchange_set_others(self):
    #     if not self.others:
    #         self.others = self.env['ir.config_parameter'].sudo().get_param('crm_custom_view.subject')

    @api.constrains(
        'name', 'partner_id', 'email_from', 'phone',
        'partner_name', 'street', 'contact_name', 'function', 'mobile', 'type'
    )
    def _check_required_fields(self):
        for rec in self:
            if rec.type != 'lead':
                continue

            missing = []

            # if not rec.hide_additional_fields:
            #     if not rec.contact_name:
            #         missing.append("Contact Name")
            #
            #     if not rec.function:
            #         missing.append("Job Position")
            #
            #     if not rec.mobile:
            #         missing.append("Mobile")

            # 1️⃣ Project Name
            if not rec.name:
                missing.append("Project Name")

            # 2️⃣ Customer
            if not rec.partner_id:
                missing.append("Customer")

                # 3️⃣ Email
            if not rec.email_from:
                missing.append("Email")

            # 4️⃣ Phone
            if not rec.phone:
                missing.append("Phone")

                # 5️⃣ Company Name
            if not rec.partner_name:
                missing.append("Company Name")

            # 6️⃣ Address
            if not rec.street:
                missing.append("Address")

            # # 7️⃣ Contact Name
            # if not rec.contact_name:
            #     missing.append("Contact Name")
            #
            # # 8️⃣ Job Position
            # if not rec.function:
            #     missing.append("Job Position")
            #
            # # 9️⃣ Mobile
            # if not rec.mobile:
            #     missing.append("Mobile")

            if missing:
                raise ValidationError(
                    "Please fill the following fields:\n- " + "\n- ".join(missing)
                )

    # -------------------------
    # ✅ NAME AUTO SET
    # -------------------------
    @api.model
    def create(self, vals):

        if not vals.get('name'):
            if vals.get('partner_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                vals['name'] = f"{partner.name} Project"
            elif vals.get('partner_name'):
                vals['name'] = f"{vals.get('partner_name')} Project"
            else:
                vals['name'] = "New Project"
        
        '''Code Added on June 20 2026 by Vijaya Bhaskar'''

      
        record = super().create(vals)
        record._create_res_partner()
        return record

    def _create_res_partner(self):
        for rec in self:
            partner_vals = {
                "name": rec.customer_name or False,
                "street": rec.street or False,
                "street2": rec.street2 or False,
                "customer_city_id": rec.customer_city_id.id or False,
                "state_id": rec.state_id.id or False,
                "country_id": rec.country_id.id or False,
                "zip": rec.zip or False,
                "email": rec.email_from or None,
                "mobile": rec.phone or None,
                # "partner_type_hhs": "customer",
                # "sub_partner_type": "retail",
            }
            partner_search = self.env["res.partner"].search(
                [("mobile", "=", rec.phone), ("id", "=", rec.partner_id.id)]
            )
           
            if not partner_search:
                partner = self.env["res.partner"].create(partner_vals)
                rec.partner_id = partner.id  

    # -------------------------
    # ✅ UI AUTO FILL
    # -------------------------
    # @api.onchange('partner_id')
    # def _onchange_partner(self):
    #     if self.partner_id:
    #         self.name = f"{self.partner_id.name} Project"
