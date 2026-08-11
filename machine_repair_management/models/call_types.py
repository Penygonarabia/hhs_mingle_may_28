from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CallTypes(models.Model):
    _name = "call.types"
    _description = "Call Types"
    _rec_name = "complete_name"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    complete_name = fields.Char(string="Complete Name", compute="_compute_name")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,
                                 required=True)

    @api.depends('name', 'code')
    def _compute_name(self):
        for rec in self:
            if rec.code and rec.name:
                rec.complete_name = '[%s] %s' % (rec.code, rec.name)
            else:
                rec.complete_name = rec.name

    @api.constrains('code')
    def _check_valid_code(self):
        for rec in self:
            code_search = self.env['call.types'].search([('code', '=', rec.code)])
            if len(code_search) > 1:
                raise ValidationError("Code is Unique one.Please give the unique Code")


class MachineRepairSupport(models.Model):
    _inherit = 'machine.repair.support'

    @api.model
    def _default_call_type_id(self):
        call_type_search = self.env['call.types'].search([('name', '=', 'Call Center')], limit=1)
        return call_type_search.id if call_type_search else False

    call_types_id = fields.Many2one('call.types', string="Call Type", default=_default_call_type_id)
    maintenance_type = fields.Selection([('corrective', 'Corrective'), ('preventive', 'Preventive')], string='Job Type',
                                        default="corrective")
    work_location_id = fields.Many2one('work.center.location', string="Work Center")
    call_request_appointment_date = fields.Datetime(
        string='Service Requested Appt Date & Time',
        copy=False,
    )
    # call_request_appointment_date = fields.Datetime(
    #     string='Requested Appointment Date & Time',
    #     default=fields.Datetime.now,
    #     copy=False,
    # )

    technician_appointment_date = fields.Datetime(
        string='Actual App Date & Time',
        # default=fields.Datetime.now,
        copy=False,
    )
    call_center_comments = fields.Text(string="Call Center comments")
    location_id = fields.Many2one('hr.work.location', string="Location",
                                  default=lambda
                                      self: self.env.user.def_location_id if self.env.user.def_location_id else False)
    phone_number_bool = fields.Boolean(string="Phone number Bool", default=False, )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
    )
    # warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    # available_warehouse_ids = fields.Many2many('stock.warehouse', compute='_compute_available_warehouse_ids')
    # available_category_ids = fields.Many2many('product.category', compute='_compute_available_category_ids')

    # @api.depends('location_id', 'warehouse_id')
    # def _compute_available_category_ids(self):
    #     for rec in self:
    #         rec.available_category_ids = False
    #         if rec.location_id and rec.warehouse_id:
    #             lines = self.env['product.category.line'].search([
    #                 ('location_id', '=', rec.location_id.id),
    #                 ('warehouse_id', '=', rec.warehouse_id.id)
    #             ])
    #             categories = lines.mapped('category_location_id')
    #             rec.available_category_ids = [(6, 0, categories.ids)]
    #             print("rec.available_category_ids", rec.available_category_ids)

    # @api.depends('location_id')
    # def _compute_available_warehouse_ids(self):
    #     for rec in self:
    #         rec.available_warehouse_ids = False
    #         if rec.location_id:
    #             lines = self.env['product.category.line'].search([
    #                 ('location_id', '=', rec.location_id.id)
    #             ])
    #             warehouses = lines.mapped('warehouse_id')
    #             rec.available_warehouse_ids = [(6, 0, warehouses.ids)]
    #             # print("rec.available_warehouse_ids", rec.available_warehouse_ids)

    @api.onchange('phone')
    def _compute_phone_number_bool(self):
        for rec in self:
            # rec.phone_number_bool = False
            if rec.phone:
                if len(rec.phone) != 10:
                    # if len(rec.phone) < 10 or len(rec.phone) > 15:
                    raise ValidationError(_(
                        "Mobile number must be 10 digits."
                    ))
                rec.phone_number_bool = True
                if rec.phone_number_bool:
                    ''' 
                    partner_search = self.env['res.partner'].search([('mobile', '=', rec.phone),('blocked_customer','=',True)], limit=1)
                    service_request_search = self.env['machine.repair.support'].search([('phone','=',rec.phone)],order ="id Desc",limit = 1)    

                    if partner_search:
                        rec.partner_id = partner_search
                    elif service_request_search:
                        rec.customer_name = service_request_search.customer_name
                    '''
                    partner_search = self.env['res.partner'].search([('mobile', '=', rec.phone)], limit=1)
                    if partner_search:
                        rec.partner_id = partner_search.id

                        # rec.customer_name = partner_search.name
                        '''Code Added on August 10 2026 client f call center user type the user’s alternative mobile number or contract screen'''
                    elif not partner_search:
                        contract_search = self.env['subscription.contracts'].search([('contact_persons_mobile','=', rec.phone)],limit = 1)
                        if contract_search:
                            rec.customer_name = contract_search.contact_persons or False
                            rec.address_one = contract_search.site_address or False
                            rec.address_two = False
                            rec.customer_city_id = contract_search.site_customer_city_id.id or False
                            rec.country_district_id = contract_search.site_district_id.id or False
                            rec.country_state_id = contract_search.site_state_id.id or False
                            rec.country_id = contract_search.site_country_id.id or False
                            rec.zip_code = contract_search.site_zip or False
                            rec.work_location_id = None
                            rec.customer_identification_scheme = contract_search.customer_identification_scheme or False
                            rec.customer_identification_number = contract_search.customer_identification_number or False
                            rec.building_number = contract_search.building_number or False
                            rec.plot_identification = contract_search.plot_identification or False
                            rec.partner_name  = contract_search.partner_name or False
               
                        
                        
                    else:
                        rec.customer_name = None
                        rec.email = False
                        rec.address = False
                        rec.address_one = False
                        rec.address_two = False
                        rec.customer_city_id = False
                        rec.country_district_id = False
                        rec.country_state_id = None
                        rec.country_id = False
                        rec.zip_code = False
                        rec.work_location_id = None
                        rec.customer_identification_scheme = False
                        rec.customer_identification_number = False
                        # rec.whatsapp_opt_in = False
                        rec.building_number = False
                        rec.plot_identification = False
                        rec.partner_latitude = False
                        rec.partner_longitude = False

                        # return {
                        #     'warning': {
                        #         'title': 'No Customer Found',
                        #         'message': 'No customer found with this phone number.',
                        #     }
                        # }

                        return {
                            'type': 'ir.actions.act_window',
                            'name': 'No Customer Found',
                            'res_model': 'partner.warning.wizard',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_phone': rec.phone,
                            },
                        }

    ''' Currently working Vijaya bhaskar is commented on april 10 2025 because location work center is derived from the res partner customer city
    @api.onchange('location_id')
    def _onchange_location_id(self):
        for rec in self:
            if rec.location_id:
                location_lst = self.env['work.center.location'].search([
                    ('location_id', '=', rec.location_id.id)
                ]).ids
                return {'domain': {'work_location_id': [('id', 'in', location_lst)] if location_lst else [('id', '=', 0)]}}
            else:
                return {'domain': {'work_location_id': [('id', '=', 0)]}}
        
    '''
