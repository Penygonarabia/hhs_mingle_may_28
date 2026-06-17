from odoo import fields, models, api, _
from odoo.osv import expression
from datetime import datetime


class CrmLead(models.Model):
    """ Inheriting account move model to add id of subscription """
    _inherit = 'crm.lead'
    _order = "id desc"

    amc_quotation_count = fields.Integer(string="AMC Quotations", compute="_compute_amc_quotation_count")

    '''Code Added on March 21 2026 by Vijaya Bhaskar'''
    customer_city_id = fields.Many2one('res.city', string="Customer City")

    @api.onchange('partner_id')
    def _onchange_partner_city(self):
        self.customer_city_id = self.partner_id.customer_city_id.id or None
        
        
    # '''Code Added on March 23 2026 by Vijaya Bhaskar'''
    # @api.model_create_multi
    # def create(self, vals_list):
    #     records = super(CrmLead, self).create(vals_list)
    #
    #     for rec, vals in zip(records, vals_list):
    #         partner = rec.partner_id
    #
    #         if not partner:
    #             continue
    #
    #         if vals.get('street'):
    #             partner.street = vals.get('street')
    #
    #         if vals.get('street2'):
    #             partner.street2 = vals.get('street2')
    #
    #         if vals.get('customer_city_id'):
    #             partner.customer_city_id = vals.get('customer_city_id')
    #
    #         if vals.get('state_id'):
    #             partner.state_id = vals.get('state_id')
    #
    #         if vals.get('country_id'):
    #             partner.country_id = vals.get('country_id')
    #
    #         if vals.get('zip'):
    #             partner.zip = vals.get('zip')
    #
    #         if vals.get('email_from'):
    #             partner.email = vals.get('email_from')
    #
    #         if vals.get('phone'):
    #             partner.mobile = vals.get('phone')    
    #
    #     return super(CrmLead, self).create(vals_list)
    #
    #
    # def write(self,vals):
    #     res = super(CrmLead, self).write(vals)
    #
    #     if 'street' in vals:
    #         self.partner_id.street = vals.get('street')
    #     if 'street2' in vals:
    #         self.partner_id.street2 = vals.get('street2')
    #
    #     if 'customer_city_id' in vals:
    #         city_search = self.env['res.city'].search([('id','=', vals.get('customer_city_id'))],limit =1)
    #         self.partner_id.customer_city_id  = city_search.id
    #
    #     if 'state_id' in vals:
    #         state_search = self.env['res.country.state'].search([('id','=', vals.get('state_id'))],limit = 1)
    #
    #         self.partner_id.state_id = state_search.id
    #         self.partner_id.customer_city_id.state_id = state_search.id
    #
    #     if 'country_id' in vals:
    #
    #         country_search = self.env['res.country'].search([('id','=',vals.get('country_id'))],limit = 1)
    #
    #         self.partner_id.country_id = country_search.id
    #         self.partner_id.customer_city_id.country_id = country_search.id
    #
    #
    #     if 'zip' in vals:
    #
    #         self.partner_id.zip = vals.get('zip')
    #         self.partner_id.customer_city_id.zipcode = vals.get('zip')
    #
    #
    #     if 'email_from' in vals:
    #         self.partner_id.email = vals.get('email_from')
    #
    #     if 'phone' in vals:
    #         self.partner_id.mobile = vals.get('phone')        
    #
    #     return res     
    #


    @api.model_create_multi
    def create(self, vals_list):
        records = super(CrmLead, self).create(vals_list)

        for rec, vals in zip(records, vals_list):
            partner = rec.partner_id

            if not partner:
                continue

            if vals.get('street'):
                partner.street = vals.get('street')

            if vals.get('street2'):
                partner.street2 = vals.get('street2')

            if vals.get('customer_city_id'):
                partner.customer_city_id = vals.get('customer_city_id')

            if vals.get('state_id'):
                partner.state_id = vals.get('state_id')

            if vals.get('country_id'):
                partner.country_id = vals.get('country_id')

            if vals.get('zip'):
                partner.zip = vals.get('zip')

            if vals.get('email_from'):
                partner.email = vals.get('email_from')

            if vals.get('phone'):
                partner.mobile = vals.get('phone')
                
            '''Code Added on May 22 2026 by Vijaya Bhaskar'''     
            if vals.get('customer_code'):
                partner.ref = vals.get('customer_code')
                        

        return records

    def write(self, vals):
        res = super(CrmLead, self).write(vals)

        if 'street' in vals:
            self.partner_id.street = vals.get('street')
        if 'street2' in vals:
            self.partner_id.street2 = vals.get('street2')

        if 'customer_city_id' in vals:
            city_search = self.env['res.city'].search([('id', '=', vals.get('customer_city_id'))], limit=1)
            self.partner_id.customer_city_id = city_search.id

        if 'state_id' in vals:
            state_search = self.env['res.country.state'].search([('id', '=', vals.get('state_id'))], limit=1)

            self.partner_id.state_id = state_search.id

        if 'country_id' in vals:
            country_search = self.env['res.country'].search([('id', '=', vals.get('country_id'))], limit=1)

            self.partner_id.country_id = country_search.id

        if 'zip' in vals:
            self.partner_id.zip = vals.get('zip')

        if 'email_from' in vals:
            self.partner_id.email = vals.get('email_from')

        if 'phone' in vals:
            self.partner_id.mobile = vals.get('phone')
            
        '''Code Added on May 22 2026 by Vijaya Bhaskar'''     
        if vals.get('customer_code'):
            partner.ref = vals.get('customer_code')    

        return res

        # @api.onchange('partner_id')

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        user = self.env.user

        # if not user._is_admin():
        if not user.user_has_groups('hr_saudi.group_sys_manager'):
            # Check if user is CRM Team Leader (user_id in crm.team)
            leader_teams = self.env['crm.team'].search([('user_id', '=', user.id)])

            if leader_teams:
                # Team leader → can see own records OR records of their teams
                domain = expression.AND([
                    domain,
                    ['|',
                     ('create_uid', '=', user.id),
                     ('team_id', 'in', leader_teams.ids)
                     ]
                ])
            else:
                # Normal member → only own created records
                domain = expression.AND([
                    domain,
                    [('create_uid', '=', user.id)]
                ])

        return super(CrmLead, self).search_fetch(domain, field_names, offset, limit, order)

    # def quotation_amc(self):
    #     self.ensure_one()
    #     service_quotation = self.env['service.sale.order'].create({
    #         'crm_id' : self.id,
    #         'customer_name' : self.partner_name,
    #         'customer_address' : self.street,
    #         'date_expiry' : self.date_deadline,
    #         'amc_quotation' : True,
    #         'is_approval': True,  # must pass required field
    #         'company_id': self.company_id.id,
    #     })
    #     # 👇 Call approval assignment here as well, just in case
    #     service_quotation._assign_approval_level()
    #     return {
    #     'name': 'AMC Quotation',
    #     'type': 'ir.actions.act_window',
    #     'res_model': 'service.sale.order',
    #     'view_mode': 'form',
    #     'target': 'current',
    #     'res_id': service_quotation.id,   # 👈 open the newly created record
    # }

    def quotation_amc(self):
        self.ensure_one()

        # Step 1: Prepare basic values
        gross_profit = float(
            self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.gross_profit', default=0.0))
        add_paid_service_price = float(
            self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.add_paid_service_price',
                                                             default=0.0))
        travel_hours = float(
            self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.travel_hr_for_people',
                                                             default=0.0))
        current_datetime = fields.Datetime.now()
        # Fix the time for date_expiry → combine date_deadline with current time in user's timezone
        # Handle date_expiry with proper time
        date_expiry_value = False
        if self.date_deadline:
            # Get the current time
            current_time = fields.Datetime.now().time()

            # Combine date_deadline with current time
            date_expiry_value = datetime.combine(self.date_deadline, current_time)

        address_parts = [
            self.street or False,
            self.street2 or False,
            self.customer_city_id.name or False,
            self.district.name or False,
            self.state_id.name or False,
            self.country_id.name or False,
            self.zip or False,
        
        ]
        address = ", ".join(filter(None, address_parts))

        values = {
            'crm_id': self.id,
            'customer_name': self.partner_id.name,
            'partner_name' : self.partner_name,
            'contact_name' : self.contact_name,
            'function' : self.function,
            'email_from': self.email_from,
            'job_position': self.job_position,#20260408 Gokul
            'mobile' : self.phone,
            'customer_address': address,
            'service_sale_quotation_date': current_datetime,  # Set here instead of default
            'date_expiry': date_expiry_value,
            'amc_quotation': True,
            'is_approval': True,
            'company_id': self.company_id.id or self.env.company.id,
            'state': 'draft',
            'invoice_interval': 365,
            'contract_period': 1,
            'gross_profit': gross_profit,  # ✅ Added Here
            'travel_hours': travel_hours,  # ✅ Added Here
            'add_paid_service_price': add_paid_service_price,
            'spare_parts_amount_discount': float(
                self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.spare_parts_gross_profit')),
            
            'warehouse_id' : self.warehouse_id.id or False,
            'customer_code' : self.customer_code or False,
            'work_center_id' :self.work_center_id.id or False,
            'work_center_group_id' : self.work_center_group_id.id or False,
            'sales_person_user_id' : self.user_id.id or False,
            
            'street': self.street or '',
            'street2':self.street2 or ' ',
            'customer_city_id' :self.customer_city_id.id or '',
            'district_id': self.district.id or '',
            'state_id': self.state_id.id or '',
            'country_id':self.country_id.id or '',
            'zip': self.zip or '',


        }

        # Step 2: Fetch suggested approval rules
        suggested_ids = self.env['approval.approval'].search([])  # all approval rules

        if suggested_ids:
            # Add them to the service.sale.order
            values['suggested_ids'] = [(6, 0, suggested_ids.ids)]

            # Step 3: Decide approval level based on CRM’s planned revenue
            company = self.company_id or self.env.company
            estimated_amount = self.prorated_revenue or 0

            if company.approval_type == 'before_tax_amount':
                data = suggested_ids.filtered(lambda l: l.minimum_amount <= estimated_amount)
            elif company.approval_type == 'total':
                data = suggested_ids.filtered(lambda l: l.minimum_amount <= estimated_amount)
            else:
                data = False

            # Step 4: If match found → set approval_level_id
            if data:
                values['approval_level_id'] = data.sorted(key=lambda l: l.minimum_amount)[0].id

        # Step 5: Finally create the Service Sale Order
        service_quotation = self.env['service.sale.order'].create(values)
        scope_search = self.env['amc.scope.of.work'].search([
            ('amc_auto_populate', '=', True)
        ])
        if scope_search:
            lines = []
            for rec in scope_search:
                lines.append((0, 0, {
                    'name': rec.id,
                    'is_selected': True  # ✅ checkbox ticked here
                }))
            service_quotation.write({
                'scope_line_ids': lines,
                'enable_scope': True
            })

        # Step 6: Return action to open the created record
        return {
            'name': 'Quotations',
            'type': 'ir.actions.act_window',
            'res_model': 'service.sale.order',
            'view_mode': 'form',
            'target': 'current',
            'res_id': service_quotation.id,
        }

    def view_amc_quotation(self):
        self.ensure_one()
        return {
            'name': ('Quotations'),
            'domain': [('amc_quotation', '=', True), ('crm_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'service.sale.order',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',

        }

    def _compute_amc_quotation_count(self):
        for record in self:
            # Count records in service.sale.order matching the domain
            count = self.env['service.sale.order'].search_count([
                ('amc_quotation', '=', True),
                ('crm_id', '=', record.id)
            ])
            record.amc_quotation_count = count
