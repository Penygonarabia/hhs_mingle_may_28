from odoo import fields, models, api, _
import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, warnings, ValidationError
import math

from pygments.styles import default
from psycopg2.errors import UniqueViolation

_logger = logging.getLogger(__name__)

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    equipment_assign_to = fields.Selection(
        [('department', 'Department'), ('employee', 'Employee'), ('other', 'Other')],
        string='Used By',
        required=True,
        default='other')
    name = fields.Char(string="Asset Tag No", required=False)
    # name = fields.Char(string="Asset Tag No",default = "New", required=True)
    brand_id = fields.Many2one('brand', string='Brand')
    model_id = fields.Many2one('equipment.model.code', string='Model')
    recurrent = fields.Boolean(string="Recurrent")
    next_schedule_visit = fields.Date(string="Next Schedule Visit Date")
    last_actual_prevent_visit = fields.Date(string="Last Actual Preventive Visit Date")
    #project_team_id = fields.Many2one('project.project', string="Project")
    project_team_id = fields.Many2one(
        "project.project",
        string="Project",
        domain=[("related_to_amc", "=", True)],
        default=lambda self: self.env["project.project"]
        .search([("related_to_amc", "=", True)], limit=1)
        .id,
    )
    allowed_technicians = fields.Many2many(

        'res.users',

        string='Allowed Technicians',

        compute='_compute_allowed_technicians', store=True

    )
    
    
    maintenance_equipment_bool = fields.Boolean(string="Maintenance Equipment Tab Show",
                                                compute="_compute_maintenance_equipment_bool")

    equipment_contract_id = fields.Many2one('product.product', string="Contract")

    maintenance_contract_type_id = fields.Many2one('crm.contract.type', string="Contract Type")

    service_product_name = fields.Char(
        string="Service Unit Type",
        compute="_compute_service_product_name"
    )

    @api.depends('service_products_code_id')
    def _compute_service_product_name(self):
        for rec in self:
            rec.service_product_name = rec.service_products_code_id.name or ''

    @api.onchange('service_products_code_id')
    def _onchange_service_products_code_id(self):
        for rec in self:
            if rec.service_products_code_id:
                # contract = self.env['crm.contract.type'].search([
                #     ('product_id', '=', rec.service_products_code_id.id)
                # ], limit=1)
                # rec.contract_id=
                for line in rec.contract_id.contract_line_ids:
                    if line.product_id == rec.service_products_code_id:
                        rec.maintenance_contract_type_id = line.contract_type_id.id or None
                    print("++++++++++++++++++++++++++", line.brand_category_id.name, line.product_id.name,
                          line.contract_type_id)

    # brand_id = fields.Many2one('brand', string='Brand')
    # model_id = fields.Many2one('equipment.model.code', string='Model')

    # @api.constrains('service_products_code_id', 'brand_id', 'model_id', 'serial_no')
    # def _check_unique_combination(self):
    #     for rec in self:
    #         domain = [
    #             ('service_products_code_id', '=', rec.service_products_code_id.id),
    #             ('brand_id', '=', rec.brand_id.id),
    #             ('model_id', '=', rec.model_id.id),
    #             ('serial_no', '=', rec.serial_no),
    #             ('id', '!=', rec.id)
    #         ]
    #
    #         if self.search_count(domain):
    #             raise ValidationError(
    #                 "Duplicate record found with the same Service Unit Type, Brand, Model, and Serial No!"
    #             )
    # brand_id = fields.Many2one('brand', string='Brand')
    # model_id = fields.Many2one('equipment.model.code', string='Model')
    
    
    '''Code Added on March 23 2026 by VIJAYA BHASKAR'''
    crm_lead_id = fields.Many2one('crm.lead', string = "CRM Origin")
    
    '''Code Added on March 23 2026 by VIJAYA BHASKAR'''
    @api.onchange('contract_id')
    def _onchange_contract_crm_lead_id(self):
        for rec in self:
            rec.crm_lead_id = rec.contract_id.amc_quotation_id.crm_id.id or False


    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            return {'domain': {'model_id': [('brand_id', '=', self.brand_id.id)]}}
        else:
            return {'domain': {'model_id': []}}

    @api.depends('equipment_assign_to')
    def _compute_maintenance_equipment_bool(self):
        self.maintenance_equipment_bool = False
        equipment = self.env['ir.config_parameter'].sudo().get_param(
            'hhs_maintenance.maintenance_equipment_show')

        if equipment == 'True':
            self.maintenance_equipment_bool=True

    @api.onchange('project_team_id')
    def _onchange_project_team_id(self):
        """Update allowed technicians and clear technician_user_id when project changes"""
        if not self.project_team_id:
            self.allowed_technicians = False
            self.technician_user_id = False  # Clear if no project
            return

        # Compute allowed technicians
        teams = self.env['machine.support.team'].search([
            ('project_ids', 'in', self.project_team_id.id)
        ])
        allowed_users = self.env['res.users']
        for team in teams:
            for line in team.support_team_line_ids:
                if line.support_team_user_id:
                    allowed_users |= line.support_team_user_id

        self.allowed_technicians = allowed_users or False

        # Critical: Clear the current technician_user_id if it is no longer allowed
        # (This ensures the user picks from the new list)
        if self.technician_user_id and self.technician_user_id not in self.allowed_technicians:
            self.technician_user_id = False

    @api.depends('project_team_id')
    def _compute_allowed_technicians(self):
        """Compute allowed technicians from machine.support.team.line via project_ids"""
        for record in self:
            if not record.id:
                record.allowed_technicians = False
                continue

            # Find all support teams linked to this project
            teams = self.env['machine.support.team'].search([
                ('project_ids', 'in', record.project_team_id.id)
            ])

            allowed_users = self.env['res.users']

            # Go through each team's lines and collect support_team_user_id
            for team in teams:
                for line in team.support_team_line_ids:
                    if line.support_team_user_id:
                        allowed_users |= line.support_team_user_id

            record.allowed_technicians = allowed_users or False

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            return {'domain': {'model_id': [('brand_id', '=', self.brand_id.id)]}}
        else:
            return {'domain': {'model_id': []}}

    @api.onchange('service_products_code_id')
    def _onchange_no_of_visits(self):
        if not self.service_products_code_id or not self.contract_id:
            self.no_of_visits = 0
            return

        # Search correct contract line
        contract_line = self.contract_id.contract_line_ids.filtered(
            lambda line: line.product_id == self.service_products_code_id
        )

        if contract_line:
            self.no_of_visits = contract_line[0].no_of_visits_per_year
        else:
            self.no_of_visits = 0

    def migrate(cr, installed_version):
        # Remove the problematic ir.model.fields record
        cr.execute("""
            DELETE FROM ir_model_fields 
            WHERE name = 'recurrent' 
            AND model = 'maintenance.equipment'
            AND ttype = 'selection'
        """)

    @api.model
    def _auto_init(self):
        # Drop the existing field first
        cr = self.env.cr
        try:
            cr.execute("""
                   DELETE FROM ir_model_fields 
                   WHERE name = 'recurrent' 
                   AND model = %s
               """, (self._name,))
        except Exception as e:
            _logger.warning("Could not delete field record: %s", e)
            
        try:
            cr.execute("""
                ALTER TABLE maintenance_equipment DROP CONSTRAINT IF EXISTS maintenance_equipment_serial_no;
            """)
        except Exception as e:
            _logger.warning("Could not drop constraint maintenance_equipment_serial_no: %s", e)

        return super()._auto_init()

    @api.onchange('contract_start_date')
    def _onchange_contract_start_date(self):
        if self.contract_start_date:
            # Only set if still empty
            if not self.next_schedule_visit:
                self.next_schedule_visit = self.contract_start_date
            # Only tick if currently False
            if not self.recurrent:
                self.recurrent = True

    @api.model
    def create(self, vals):
        if 'contract_start_date' in vals:
            # Set next_schedule_visit if not provided
            if not vals.get('next_schedule_visit'):
                vals['next_schedule_visit'] = vals['contract_start_date']
            # Set recurrent to True if not explicitly set
            if 'recurrent' not in vals:
                vals['recurrent'] = True
        return super(MaintenanceEquipment, self).create(vals)
    
    '''Code Added on April 30 2026 by Vijaya Bhaskar Because Client Asked the Single Service Request'''
    
    # def create_single_service_request(self):
    #
    #     created_jobs = []
    #     skipped_jobs = []
    #
    #     for rec in self:
    #
    #
    #         if not rec.contract_id or not rec.contract_id.partner_id:
    #             skipped_jobs.append(f"{rec.display_name} → Missing contract/customer")
    #             continue
    #
    #         if not rec.recurrent:
    #             skipped_jobs.append(f"{rec.display_name} → Recurrent not set")
    #             continue
    #
    #         next_visit_schedule_date = rec.next_schedule_visit
    #         no_of_visits = rec.no_of_visits
    #         partner = rec.contract_id.partner_id
    #
    #
    #         address_parts = [
    #             rec.crm_lead_id.street,
    #             rec.crm_lead_id.street2,
    #             rec.crm_lead_id.customer_city_id.name if rec.crm_lead_id.customer_city_id else "",
    #             rec.crm_lead_id.state_id.name if rec.crm_lead_id.state_id else "",
    #             rec.crm_lead_id.country_id.name if rec.crm_lead_id.country_id else "",
    #             rec.crm_lead_id.zip or "",
    #         ]
    #         full_address = ",".join(filter(None, address_parts))
    #
    #
    #         project = self.env['project.project'].search(
    #             [('name', '=', 'HHS - AMC Project')], limit=1)
    #
    #         service_nature = self.env['service.nature'].search(
    #             [('code', '=', '001')], limit=1)
    #
    #         service_team_id = self.env['machine.support.team'].search(
    #             [('leader_id', '=', rec.technician_user_id.id)], limit=1)
    #
    #         district_search_id = self.env['res.state.district'].search(
    #             [('city_id', '=', rec.crm_lead_id.customer_city_id.id)], limit=1)
    #
    #         existing_request = self.env['machine.repair.support'].search(
    #             [('asset_id', '=', rec.id)],
    #             limit=1
    #         )
    #
    #         if existing_request:
    #             skipped_jobs.append(
    #                 f"{rec.display_name} → Already created ({existing_request.name})"
    #             )
    #             continue
    #
    #
    #         if not next_visit_schedule_date or next_visit_schedule_date > rec.contract_end_date:
    #             skipped_jobs.append(f"{rec.display_name} → Invalid schedule date")
    #             continue
    #
    #
    #         vals = {
    #             'partner_id': partner.id,
    #             'customer_name': partner.name,
    #             'phone': partner.mobile or partner.phone,
    #             'email': partner.email,
    #             'customer_city_id': rec.crm_lead_id.customer_city_id.id or False,
    #             'country_district_id': district_search_id.id or False,
    #             'work_location_id': rec.crm_lead_id.customer_city_id.def_work_center_id.id or False,
    #             'contract_id': rec.contract_id.id,
    #             'asset_id': rec.id,
    #             'brand': rec.brand_id.name,
    #             'product_id': rec.service_products_code_id.id or False,
    #             'model': rec.model_id.model_code or False,
    #             'product_slno': rec.serial_no or False,
    #             'amc_project_id': rec.project_team_id.id or False,
    #             'nature_of_service_id': service_nature.id or False,
    #             'maintenance_type': 'preventive',
    #             'user_id': rec.technician_user_id.id or False,
    #             'team_id': service_team_id.id or False,
    #             'contract_date': rec.contract_start_date,
    #             'contract_expiry_date': rec.contract_end_date,
    #             'service_products_code_id': rec.service_products_code_id.id or False,
    #             'service_group_batch': rec.service_group_batch or False,
    #             'problem': 'AMC Maintenance',
    #             'work_center_group_id': rec.crm_lead_id.customer_city_id.def_work_center_id.work_center_group_id.id or False,
    #             'maintenance_contract_type_id': rec.maintenance_contract_type_id.id or False,
    #             'service_create_from_equipment_bool': True,
    #             'type_of_property': rec.crm_lead_id.type_of_property or False,
    #             'property_type_maintenance_details_id': rec.crm_lead_id.property_type_maintenance_details_id.id or False,
    #             'company_preventive_maintenance': rec.crm_lead_id.company_preventive_maintenance or False,
    #             'customer_identification_scheme': rec.contract_id.customer_identification_scheme or False,
    #             'customer_identification_number': rec.contract_id.customer_identification_number or False,
    #             'building_number': rec.contract_id.building_number or False,
    #             'plot_identification': rec.contract_id.plot_identification or False,
    #             'product_category': rec.brand_id.amc_product_category_id.id or False,
    #         }
    #
    #
    #         service_request = self.env['machine.repair.support'].sudo().create(vals)
    #
    #         service_request._compute_update_contract_line()
    #         service_request._send_whatsapp_greeting()
    #         service_request._onchange_customer_city_id()
    #         service_request.onchange_partner_id_check()
    #
    #         scheduled_state = self.env['project.task.type'].search(
    #             [('code', '=', '101')], limit=1)
    #
    #         service_request.write({
    #             'address_one': full_address,
    #             'address': full_address,
    #             'service_request_state_code': scheduled_state.code,
    #             'service_request_state': scheduled_state.name,
    #             'state': scheduled_state.id,
    #         })
    #
    #         if service_request.task_id:
    #             service_request.task_id.write({
    #                 'address_one': full_address,
    #                 'address': full_address,
    #                 'zip_code': rec.crm_lead_id.customer_city_id.zipcode or False,
    #                 'country_state_id': rec.crm_lead_id.customer_city_id.state_id.id or False,
    #                 'country_id': rec.crm_lead_id.customer_city_id.country_id.id or False,
    #                 'job_card_state_code': scheduled_state.code,
    #                 'job_card_state': scheduled_state.name,
    #                 'job_state': scheduled_state.id
    #             })
    #
    #             if service_request.task_id.name:
    #                 created_jobs.append(service_request.task_id.name)
    #
    #         service_request._create_res_partner()
    #
    #         if service_request and next_visit_schedule_date and no_of_visits:
    #             interval = 12 / no_of_visits
    #             months = math.floor(interval)
    #             days = round((interval - months) * 30)
    #
    #             rec.next_schedule_visit = next_visit_schedule_date + relativedelta(
    #                 months=months,
    #                 days=days
    #             )
    #
    #
    #     message = ""
    #
    #     if created_jobs:
    #         message += _("✅ Created Job Cards:\n%s\n\n") % (",".join(created_jobs))
    #
    #     if skipped_jobs:
    #         message += _("⚠️ Skipped Records:\n%s") % (",".join(skipped_jobs))
    #
    #     if not message:
    #         message = _("No Job Card was created")
    #
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': _('Result'),
    #             'message': message,
    #             'type': 'success' if created_jobs else 'warning',
    #             'sticky': True,
    #         }
    #     }
    
    '''Code Added on July 16 2026 for cron job automatically send when the next invocie schedule date is today  for email alert to supervisor'''
    @api.model
    def cron_send_supervisor_email_alert_maintenance(self):
        today = fields.Date.today()
        seven_days_after = today + relativedelta(days=7)
    
        equipment_search = self.env['maintenance.equipment'].search([
            ('next_schedule_visit', '=', seven_days_after),
            ('recurrent', '=', True),
            ('contract_id', '!=', False),
            ('contract_start_date', '<=', today),
            ('contract_end_date', '>=', seven_days_after),
        ])
    
        if not equipment_search:
            return
    
        supervisor_group = self.env.ref(
            'machine_repair_management.group_technical_allocation_user'
        )
        supervisors = supervisor_group.users
    
        for rec in equipment_search:
            matching_supervisors = supervisors.filtered(
                lambda u: rec.project_team_id in u.project_ids
            )
    
            for user in matching_supervisors:
                subject = f"Upcoming scheduled visit - {rec.name}"
    
                body_html = f"""
                    <p>Dear {user.name},</p>
                    <p>
                        The next scheduled visit for <b>{rec.name}</b> is due on
                        <b>{rec.next_schedule_visit.strftime('%d-%m-%Y')}</b>.
                    </p>
                    <p>Please contact the customer regarding renewal.</p>
                    <br/>
                    <p>
                        Best Regards,<br/>
                        Maintenance Department
                    </p>
                """
    
                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body_html,
                    'email_from': self.env.user.email or self.env.company.email,
                    'email_to': user.email or user.login,
                }).send()
                    
    
    
    
    '''Code Added on July 16 2026 for  cron job automatically send when the next invocie schedule date is today '''
    @api.model
    def cron_create_single_service_request(self, from_cron=False):
        today = fields.Date.today()
        equipment_search = self.env['maintenance.equipment'].search(
            [
                ('next_schedule_visit', '=', today),
                ('recurrent', '=', True),
                ('contract_id', '!=', False),
                ('contract_start_date', '<=', today),
                ('contract_end_date', '>=', today),
            ])

        created_jobs = []
        skipped_jobs = []

        for rec in equipment_search:
            try:
                with self.env.cr.savepoint():

                    if not rec.contract_id or not rec.contract_id.partner_id:
                        skipped_jobs.append(f"{rec.display_name} → Missing contract/customer")
                        continue

                    if not rec.recurrent:
                        skipped_jobs.append(f"{rec.display_name} → Recurrent not set")
                        continue

                    next_visit_schedule_date = rec.next_schedule_visit
                    no_of_visits = rec.no_of_visits
                    partner = rec.contract_id.partner_id

                    # address_parts = [
                    #     rec.crm_lead_id.street,
                    #     rec.crm_lead_id.street2,
                    #     rec.crm_lead_id.customer_city_id.name if rec.crm_lead_id.customer_city_id else "",
                    #     rec.crm_lead_id.state_id.name if rec.crm_lead_id.state_id else "",
                    #     rec.crm_lead_id.country_id.name if rec.crm_lead_id.country_id else "",
                    #     rec.crm_lead_id.district.name if rec.crm_lead_id.district else "",
                    #     rec.crm_lead_id.zip or "",
                    # ]
                    
                    address_parts = [
                            rec.contract_id.site_street,
                            rec.contract_id.site_street2,
                            rec.contract_id.site_customer_city_id.name if rec.contract_id.site_customer_city_id else "",
                            rec.contract_id.site_district_id.name if rec.contract_id.site_district_id else "",
                            rec.contract_id.site_country_id.name if rec.contract_id.site_country_id else "",
                            rec.contract_id.site_district_id.name if rec.contract_id.site_district_id else "",
                            rec.contract_id.site_zip or "",
                        ]
                    full_address = ",".join(filter(None, address_parts))

                    project = self.env['project.project'].search(
                        [('name', '=', 'HHS - AMC Project')], limit=1)

                    service_nature = self.env['service.nature'].search(
                        [('code', '=', '001')], limit=1)

                    service_team_id = self.env['machine.support.team'].search(
                        [('leader_id', '=', rec.technician_user_id.id)], limit=1)

                    district_search_id = self.env['res.state.district'].search(
                        [('id', '=', rec.crm_lead_id.district.id)], limit=1)

                    if (not next_visit_schedule_date
                            or not (rec.contract_start_date <= next_visit_schedule_date <= rec.contract_end_date)):
                        skipped_jobs.append(f"{rec.display_name} → Invalid schedule date")
                        continue

                    next_count = rec.pm_service_count
                    name = f"{rec.name}/{str(next_count).zfill(2)}"

                    if self.env['machine.repair.support'].search_count([('name', '=', name)]):
                        skipped_jobs.append(f"{rec.display_name} → {name} already exists, skipping")
                        continue

                    vals = {
                        'name': name,
                        'partner_id': partner.id,
                        # 'customer_name': partner.name,
                        # 'phone': partner.mobile or partner.phone,
                        # 'email': partner.email,
                        # 'customer_city_id': rec.crm_lead_id.customer_city_id.id or False,
                        # 'country_district_id': district_search_id.id or False,
                        # 'work_location_id': rec.crm_lead_id.customer_city_id.def_work_center_id.id or False,
                        'customer_name': rec.contract_id.contact_persons or False,
                        'phone' : rec.contract_id.contact_persons_mobile or False,
                        'email': rec.contract_id.email,
                        'customer_city_id': rec.contract_id.site_customer_city_id.id or False,
                        'country_district_id': rec.contract_id.site_district_id.id or False,
                        'work_location_id': rec.contract_id.site_customer_city_id.def_work_center_id.id or False,
                              
                        
                        'contract_id': rec.contract_id.id,
                        'asset_id': rec.id,
                        'brand': rec.brand_id.name,
                        'product_id': rec.service_products_code_id.id or False,
                        'model': rec.model_id.model_code or False,
                        'product_slno': rec.serial_no or False,
                        'amc_project_id': rec.project_team_id.id or False,
                        'nature_of_service_id': service_nature.id or False,
                        'maintenance_type': 'preventive',
                        'user_id': rec.technician_user_id.id or False,
                        'team_id': service_team_id.id or False,
                        'contract_date': rec.contract_start_date,
                        'contract_expiry_date': rec.contract_end_date,
                        'service_products_code_id': rec.service_products_code_id.id or False,
                        'service_group_batch': rec.service_group_batch or False,
                        'problem': 'AMC Maintenance',
                        'work_center_group_id': rec.contract_id.site_customer_city_id.def_work_center_id.work_center_group_id.id or False,

                        # 'work_center_group_id': rec.crm_lead_id.customer_city_id.def_work_center_id.work_center_group_id.id or False,
                        'maintenance_contract_type_id': rec.maintenance_contract_type_id.id or False,
                        'service_create_from_equipment_bool': True,
                        'type_of_property': rec.crm_lead_id.type_of_property or False,
                        'property_type_maintenance_details_id': rec.crm_lead_id.property_type_maintenance_details_id.id or False,
                        'company_preventive_maintenance': rec.crm_lead_id.company_preventive_maintenance or False,
                        'customer_identification_scheme': rec.contract_id.customer_identification_scheme or False,
                        'customer_identification_number': rec.contract_id.customer_identification_number or False,
                        'building_number': rec.contract_id.building_number or False,
                        'plot_identification': rec.contract_id.plot_identification or False,
                         'product_category': rec.brand_id.amc_product_category_id.id or False,
                       
                         # 'product_category': rec.service_products_code_id.product_category_id.id or False,
                        'used_location_equipment': rec.location or False,
                        'brand_id': rec.brand_id.id or False,
                        'items_from_own_company_bool': rec.items_from_own_company_bool or False,
                        'model_id': rec.model_id.id or False,
                        'product_product_model_id': rec.product_product_model_id.id or False,
                        'partner_name': rec.contract_id.partner_name or False,
                    }

                    service_request = self.env['machine.repair.support'].sudo().create(vals)

                    service_request._compute_update_contract_line()
                    service_request._send_whatsapp_greeting()
                    service_request._onchange_customer_city_id()
                    # service_request.onchange_partner_id_check()

                    scheduled_state = self.env['project.task.type'].search(
                        [('code', '=', '101')], limit=1)

                    service_request.write({
                        'address_one': full_address,
                        'address': full_address,
                        'service_request_state_code': scheduled_state.code,
                        'service_request_state': scheduled_state.name,
                        'state': scheduled_state.id,
                    })

                    if service_request.task_id:
                        service_request.task_id.write({
                        'address_one': full_address,
                        'address': full_address,
                        'zip_code': rec.contract_id.site_zip or False,
                        'country_state_id':rec.contract_id.site_state_id.id or False,
                        'country_id': rec.contract_id.site_country_id.id or False,
                        'job_card_state_code': scheduled_state.code,
                        'job_card_state': scheduled_state.name,
                        'job_state': scheduled_state.id
                    })
                        # service_request.task_id.write({
                        #     'address_one': full_address,
                        #     'address': full_address,
                        #     'zip_code': rec.crm_lead_id.customer_city_id.zipcode or False,
                        #     'country_state_id': rec.crm_lead_id.customer_city_id.state_id.id or False,
                        #     'country_id': rec.crm_lead_id.customer_city_id.country_id.id or False,
                        #     'job_card_state_code': scheduled_state.code,
                        #     'job_card_state': scheduled_state.name,
                        #     'job_state': scheduled_state.id
                        # })

                        if service_request.task_id.name:
                            created_jobs.append(service_request.task_id.name)

                    service_request._create_res_partner()

                    if service_request and next_visit_schedule_date and no_of_visits:
                        interval = 12 / no_of_visits
                        months = math.floor(interval)
                        days = round((interval - months) * 30)

                        rec.next_schedule_visit = next_visit_schedule_date + relativedelta(
                            months=months,
                            days=days
                        )

                    rec.pm_service_count += 1

            except Exception as e:
                _logger.exception(
                    "Failed to create service request for %s", rec.display_name
                )
                skipped_jobs.append(f"{rec.display_name} → {e}")
                continue

        if from_cron:
            return True
    
    def create_single_service_request(self):
    
        created_jobs = []
        skipped_jobs = []
    
        for rec in self:
    
           
            if not rec.contract_id or not rec.contract_id.partner_id:
                skipped_jobs.append(f"{rec.display_name} → Missing contract/customer")
                continue
    
            if not rec.recurrent:
                skipped_jobs.append(f"{rec.display_name} → Recurrent not set")
                continue
    
            next_visit_schedule_date = rec.next_schedule_visit
            no_of_visits = rec.no_of_visits
            partner = rec.contract_id.partner_id
    
            '''Code Commented on August 12 2026 by Vijaya bhaskar because client asked site address to be shown in the project '''
            # address_parts = [
            #     rec.crm_lead_id.street,
            #     rec.crm_lead_id.street2,
            #     rec.crm_lead_id.customer_city_id.name if rec.crm_lead_id.customer_city_id else "",
            #     rec.crm_lead_id.state_id.name if rec.crm_lead_id.state_id else "",
            #     rec.crm_lead_id.country_id.name if rec.crm_lead_id.country_id else "",
            #     rec.crm_lead_id.district.name if rec.crm_lead_id.district else "",
            #     rec.crm_lead_id.zip or "",
            # ]
            
            address_parts = [
                rec.contract_id.site_street,
                rec.contract_id.site_street2,
                rec.contract_id.site_customer_city_id.name if rec.contract_id.site_customer_city_id else "",
                rec.contract_id.site_district_id.name if rec.contract_id.site_district_id else "",
                rec.contract_id.site_country_id.name if rec.contract_id.site_country_id else "",
                rec.contract_id.site_district_id.name if rec.contract_id.site_district_id else "",
                rec.contract_id.site_zip or "",
            ]
            full_address = ",".join(filter(None, address_parts))
    
            
            project = self.env['project.project'].search(
                [('name', '=', 'HHS - AMC Project')], limit=1)
    
            service_nature = self.env['service.nature'].search(
                [('code', '=', '001')], limit=1)
    
            service_team_id = self.env['machine.support.team'].search(
                [('leader_id', '=', rec.technician_user_id.id)], limit=1)

            district_search_id = self.env['res.state.district'].search(
                [('id', '=', rec.crm_lead_id.district.id)], limit=1)
            
            # existing_request = self.env['machine.repair.support'].search(
            #     [('asset_id', '=', rec.id),
            #    ],
            #     limit=1
            # )
            
            existing_request = self.env['machine.repair.support'].search(
                [('asset_id', '=', rec.id),
                 ('name', '=', f"{rec.name}/{str(rec.pm_service_count).zfill(2)}")],
                limit=1
            )
            
            if existing_request:
                skipped_jobs.append(
                    f"{rec.display_name} → Already created ({existing_request.name})"
                )
                continue
    
         
            # if not next_visit_schedule_date or next_visit_schedule_date > rec.contract_end_date:
            #     skipped_jobs.append(f"{rec.display_name} → Invalid schedule date")
            #     continue
            
            if (not next_visit_schedule_date
                or not (rec.contract_start_date <= next_visit_schedule_date <= rec.contract_end_date)
            ):
                skipped_jobs.append(f"{rec.display_name} → Invalid schedule date")
                continue
            next_count = rec.pm_service_count
           
            vals = {
                # 'name' : f"{rec.name}/{rec.pm_service_count}",
                'name': f"{rec.name}/{str(next_count).zfill(2)}",
                'partner_id': partner.id,
                # 'customer_name': partner.name,
                # 'phone': partner.mobile or partner.phone,
                # 'email': partner.email,
                # 'customer_city_id': rec.crm_lead_id.customer_city_id.id or False,
                # 'country_district_id': district_search_id.id or False,
                # 'work_location_id': rec.crm_lead_id.customer_city_id.def_work_center_id.id or False,
               
                'customer_name': rec.contract_id.contact_persons or False,
                'phone' : rec.contract_id.contact_persons_mobile or False,
                'email': rec.contract_id.email,
                'customer_city_id': rec.contract_id.site_customer_city_id.id or False,
                'country_district_id': rec.contract_id.site_district_id.id or False,
                'work_location_id': rec.contract_id.site_customer_city_id.def_work_center_id.id or False,
                                
                'contract_id': rec.contract_id.id,
                'asset_id': rec.id,
                'brand': rec.brand_id.name,
                'product_id': rec.service_products_code_id.id or False,
                'model': rec.model_id.model_code or False,
                'product_slno': rec.serial_no or False,
                'amc_project_id': rec.project_team_id.id or False,
                'nature_of_service_id': service_nature.id or False,
                'maintenance_type': 'preventive',
                'user_id': rec.technician_user_id.id or False,
                'team_id': service_team_id.id or False,
                'contract_date': rec.contract_start_date,
                'contract_expiry_date': rec.contract_end_date,
                'service_products_code_id': rec.service_products_code_id.id or False,
                'service_group_batch': rec.service_group_batch or False,
                'problem': 'AMC Maintenance',
                # 'work_center_group_id': rec.crm_lead_id.customer_city_id.def_work_center_id.work_center_group_id.id or False,
                'work_center_group_id': rec.contract_id.site_customer_city_id.def_work_center_id.work_center_group_id.id or False,
                'maintenance_contract_type_id': rec.maintenance_contract_type_id.id or False,
                'service_create_from_equipment_bool': True,
                'type_of_property': rec.crm_lead_id.type_of_property or False,
                'property_type_maintenance_details_id': rec.crm_lead_id.property_type_maintenance_details_id.id or False,
                'company_preventive_maintenance': rec.crm_lead_id.company_preventive_maintenance or False,
                'customer_identification_scheme': rec.contract_id.customer_identification_scheme or False,
                'customer_identification_number': rec.contract_id.customer_identification_number or False,
                'building_number': rec.contract_id.building_number or False,
                'plot_identification': rec.contract_id.plot_identification or False,
                 'product_category': rec.brand_id.amc_product_category_id.id or False,
                 # 'product_category': rec.service_products_code_id.product_category_id.id or False,
                
                'used_location_equipment' :rec.location or False,
                'brand_id' : rec.brand_id.id or False,
                'items_from_own_company_bool' :rec.items_from_own_company_bool or False,
                'model_id' : rec.model_id.id or False,
                'product_product_model_id' : rec.product_product_model_id.id or False,
                'partner_name' : rec.contract_id.partner_name or False,


            }
    
            service_request = self.env['machine.repair.support'].sudo().create(vals)
            
            
            service_request._compute_update_contract_line()
            service_request._send_whatsapp_greeting()
            service_request._onchange_customer_city_id()
            # service_request.onchange_partner_id_check()
           
            scheduled_state = self.env['project.task.type'].search(
                [('code', '=', '101')], limit=1)
    
            service_request.write({
                'address_one': full_address,
                'address': full_address,
                'service_request_state_code': scheduled_state.code,
                'service_request_state': scheduled_state.name,
                'state': scheduled_state.id,
            })
    
            if service_request.task_id:
                service_request.task_id.write({
                        'address_one': full_address,
                        'address': full_address,
                        'zip_code': rec.contract_id.site_zip or False,
                        'country_state_id':rec.contract_id.site_state_id.id or False,
                        'country_id': rec.contract_id.site_country_id.id or False,
                        'job_card_state_code': scheduled_state.code,
                        'job_card_state': scheduled_state.name,
                        'job_state': scheduled_state.id
                    })
                # service_request.task_id.write({
                #     'address_one': full_address,
                #     'address': full_address,
                #     'zip_code': rec.crm_lead_id.customer_city_id.zipcode or False,
                #     'country_state_id': rec.crm_lead_id.customer_city_id.state_id.id or False,
                #     'country_id': rec.crm_lead_id.customer_city_id.country_id.id or False,
                #     'job_card_state_code': scheduled_state.code,
                #     'job_card_state': scheduled_state.name,
                #     'job_state': scheduled_state.id
                # })
    
                if service_request.task_id.name:
                    created_jobs.append(service_request.task_id.name)
    
            service_request._create_res_partner()
    
            if service_request and next_visit_schedule_date and no_of_visits:
                interval = 12 / no_of_visits
                months = math.floor(interval)
                days = round((interval - months) * 30)
    
                rec.next_schedule_visit = next_visit_schedule_date + relativedelta(
                    months=months,
                    days=days
                )
    
            rec.pm_service_count += 1
        message = ""
    
        if created_jobs:
            message += _("✅ Created Job Cards:\n%s\n\n") % (",".join(created_jobs))
    
        if skipped_jobs:
            '''Code Added on June 19 2026 by Vijaya Bhaskar'''
            message += ("⚠️ Cannot Create Schedule Preventive maintenance schedules have already been generated for the entire contract period. No additional schedules can be created.")
            # message += _("⚠️ Skipped Records:\n%s") % (",".join(skipped_jobs))
    

    
        if not message:
            message = _("No Job Card was created")
    
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Result'),
                'message': message,
                'type': 'success' if created_jobs else 'warning',
                'sticky': True,
            }
        }
        
    
    '''Code Added on March 23 2026 by Vijaya Bhaskar'''
    def create_service_request(self):
        
        self.ensure_one()

        if not self.contract_id or not self.contract_id.partner_id:
            raise UserError(_("Please set a valid contract and customer before creating a service request."))
        
        if not self.recurrent:
            raise ValidationError(_("Recurrent is Not Set"))
        
        # if not self.next_schedule_visit == fields.Date.today():
        #     raise ValidationError(_("Today Date is not Next Visit Scheduled Date"))
        #

        
        next_visit_schedule_date = self.next_schedule_visit
        
        no_of_visits = self.no_of_visits

        partner = self.contract_id.partner_id

        work_location_id = False
        
        
        # if partner.customer_city_id and partner.customer_city_id.def_work_center_id:
        #     work_location_id = partner.customer_city_id.def_work_center_id.id
        #

        project = self.env['project.project'].search([('name', '=', 'HHS - AMC Project')], limit=1)
        service_nature = self.env['service.nature'].search(
                [('code', '=', '001')],
                limit=1)
        service_team_id = self.env['machine.support.team'].search([('leader_id','=',self.technician_user_id.id)],limit=1)
        
        service_requests = self.env['machine.repair.support']
        batch_group_search = self.env['maintenance.equipment'].search([('service_group_batch','=', self.service_group_batch),
                                                                       ('contract_id','=',self.contract_id.id)]) 
                                                                       
        
        for batch in batch_group_search:
            
            full_address = False
            address_parts =[
                batch.crm_lead_id.street,
                batch.crm_lead_id.street2,
                batch.crm_lead_id.customer_city_id.name if batch.crm_lead_id.customer_city_id else "",
                batch.crm_lead_id.state_id.name if batch.crm_lead_id.name else "",
                batch.crm_lead_id.country_id.name if batch.crm_lead_id.name else "",
                batch.crm_lead_id.zip if batch.crm_lead_id.zip else "",
                
                ]
            full_address =",".join(filter(None,address_parts))
            
            district_search_id = self.env['res.state.district'].search([('city_id','=',self.crm_lead_id.customer_city_id.id)],limit = 1)

            
            vals = {
                
                'partner_id': partner.id,
                'customer_name': partner.name,
                'phone': partner.mobile or partner.phone,
                'email': partner.email,
                'customer_city_id':self.crm_lead_id.customer_city_id.id or None,
                'country_district_id' : district_search_id.id or False,
                # 'address_one' : 
                # 'customer_city_id': partner.customer_city_id.id if partner.customer_city_id else False,
                # 'country_district_id' : self.crm_lead_id.customer_city_id.country_district_id.id  if self.crm_lead_id else False,
                'work_location_id': self.crm_lead_id.customer_city_id.def_work_center_id.id or False,
                'contract_id': self.contract_id.id,
                'asset_id': self.id,
                'brand' : batch.brand_id.name,
                'product_id':self.service_products_code_id.id or False,
                'model' : batch.model_id.model_code or False,
                "product_slno" :batch.serial_no or False,
                "amc_project_id" : self.project_team_id.id or False,
                'nature_of_service_id' : service_nature.id or False,
                'maintenance_type' :'preventive',
                "user_id" : self.technician_user_id.id or False,
                "team_id" : service_team_id.id or False,
                "contract_date" : self.contract_start_date,
                "contract_expiry_date":self.contract_end_date,
                "service_products_code_id":self.service_products_code_id.id or False,
                "service_group_batch" : batch.service_group_batch or False,
                'problem' : 'AMC Maintenance',
                # 'zip_code' : self.crm_lead_id.zip or False,
                'work_center_group_id' : self.crm_lead_id.customer_city_id.def_work_center_id.work_center_group_id.id or False,
                'maintenance_contract_type_id' : self.maintenance_contract_type_id.id or False,
                'service_create_from_equipment_bool' : True,
                'maintenance_type' : 'preventive',
                 "type_of_property" : batch.crm_lead_id.type_of_property or False,
                "property_type_maintenance_details_id" :batch.crm_lead_id.property_type_maintenance_details_id.id or False,
                "company_preventive_maintenance" :batch.crm_lead_id.company_preventive_maintenance or False,
                "customer_identification_scheme" : self.contract_id.customer_identification_scheme or False,
                "customer_identification_number":self.contract_id.customer_identification_number or False,
                "building_number" : self.contract_id.building_number or False,
                "plot_identification": self.contract_id.plot_identification or False,
                "product_category": batch.brand_id.amc_product_category_id.id or False,

                
            }

            if next_visit_schedule_date <= self.contract_end_date:
                request_search = service_requests.search([('service_group_batch','=', self.service_group_batch),
                                                                       ('contract_id','=',self.contract_id.id)])
                #if request_search:
                    #raise ValidationError(_("Already Job Card %s is Created" % request_search.task_id.name ))
                
                service_request = self.env['machine.repair.support'].sudo().create(vals)
                service_request._compute_update_contract_line()
                # service_request._create_job_card()
                service_request._send_whatsapp_greeting()
                service_request._onchange_customer_city_id()
                service_request.onchange_partner_id_check()
                scheduled_state = self.env['project.task.type'].search([('code','=','101')]
                    )
            
                service_request.write({ 
                    'address_one':full_address,
                    'address':full_address,
                    'service_request_state_code' : scheduled_state.code,
                    'service_request_state' : scheduled_state.name,
                    'state' :scheduled_state.id,
                
                })
                
                service_request.task_id.write({
                    'address_one':full_address,
                    'address':full_address,
                    'zip_code':self.crm_lead_id.customer_city_id.zipcode or False,
                    'country_state_id':self.crm_lead_id.customer_city_id.state_id.id or False,
                    'country_id': self.crm_lead_id.customer_city_id.country_id.id or False,
                    'job_card_state_code' : scheduled_state.code,
                    'job_card_state' : scheduled_state.name,
                    'job_state':scheduled_state.id
                    
                
                })
                '''HHS Client again ask customer is retrieved from the res_partner need not fetch from the service request itself on JULY 29-2025 '''
                service_request._create_res_partner()
                service_requests |= service_request
                if service_request and next_visit_schedule_date and no_of_visits:
                    interval = 12 / no_of_visits
                
                    months = math.floor(interval)
                    days = round((interval - months) * 30)
                
                    self.next_schedule_visit = next_visit_schedule_date + relativedelta(
                        months=months,
                        days=days
                    )
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Machine Repair Support'),
            'res_model': 'machine.repair.support',
            'view_mode': 'tree,form',
            # 'res_id': service_request.id,
            'domain': [('id', 'in', service_requests.ids)],
            'target': 'current',
        }
    
    # def create_service_request(self):
    #
    #     self.ensure_one()
    #
    #     if not self.contract_id or not self.contract_id.partner_id:
    #         raise UserError(_("Please set a valid contract and customer before creating a service request."))
    #
    #     if not self.recurrent:
    #         raise ValidationError(_("Recurrent is Not Set"))
    #
    #     if not self.next_schedule_visit == fields.Date.today():
    #         raise ValidationError(_("Today Date is not Next Visit Scheduled Date"))
    #
    #
    #     next_visit_schedule_date = self.next_schedule_visit
    #
    #     no_of_visits = self.no_of_visits
    #
    #     partner = self.contract_id.partner_id
    #
    #     work_location_id = False
    #     if partner.customer_city_id and partner.customer_city_id.def_work_center_id:
    #         work_location_id = partner.customer_city_id.def_work_center_id.id
    #
    #     project = self.env['project.project'].search([('name', '=', 'HHS - AMC Project')], limit=1)
    #     service_nature = self.env['service.nature'].search(
    #             [('code', '=', '001')],
    #             limit=1)
    #     service_team_id = self.env['machine.support.team'].search([('leader_id','=',self.technician_user_id.id)],limit=1)
    #
    #     vals = {
    #
    #         'partner_id': partner.id,
    #         'customer_name': partner.name,
    #         'phone': partner.mobile or partner.phone,
    #         'email': partner.email,
    #         'customer_city_id': partner.customer_city_id.id if partner.customer_city_id else False,
    #         'country_district_id' : partner.customer_city_id.country_district_id.id  if partner.customer_city_id.country_district_id else False,
    #         'work_location_id': work_location_id,
    #         'contract_id': self.contract_id.id,
    #         'asset_id': self.id,
    #         'brand' : self.brand_id.name,
    #         'product_id':self.service_products_code_id.id or False,
    #         "amc_project_id" : self.project_team_id.id or False,
    #         'nature_of_service_id' : service_nature.id or False,
    #         'maintenance_type' :'preventive',
    #         "user_id" : self.technician_user_id.id or False,
    #         "product_slno" : self.serial_no or False,
    #         "team_id" : service_team_id.id or False,
    #         "contract_date" : self.contract_start_date,
    #         "contract_expiry_date":self.contract_end_date,
    #         "service_products_code_id":self.service_products_code_id.id or False
    #     }
    #
    #     if next_visit_schedule_date <= self.contract_end_date:
    #         service_request = self.env['machine.repair.support'].sudo().create(vals)
    #         service_request._compute_update_contract_line()
    #         if service_request and next_visit_schedule_date and no_of_visits:
    #             interval = 12 / no_of_visits
    #
    #             months = math.floor(interval)
    #             days = round((interval - months) * 30)
    #
    #             self.next_schedule_visit = next_visit_schedule_date + relativedelta(
    #                 months=months,
    #                 days=days
    #             )
    #
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': _('Machine Repair Support'),
    #             'res_model': 'machine.repair.support',
    #             'view_mode': 'form',
    #             'res_id': service_request.id,
    #             'target': 'current',
    #         }
            
        
    # @api.model
    # def _cron_service_request_creation(self):
    #
    #     today = fields.Date.today()    
    #
    #     recurrent = False
    #
    #     maintenance_search = self.env['maintenance.equipment'].search([
    #         ('recurrent','=',True),('next_schedule_visit','=',today),
    #         ('contract_start_date','<=',today),
    #         ('contract_end_date','>=',today)
    #
    #         ])
    #
    #
    #     for maintenance_equipment in maintenance_search:
    #     # self.ensure_one()
    #
    #         if not maintenance_equipment.contract_id or not maintenance_equipment.contract_id.partner_id:
    #             raise UserError(_("Please set a valid contract and customer before creating a service request."))
    #
    #         next_visit_schedule_date = maintenance_equipment.next_schedule_visit
    #
    #         no_of_visits = maintenance_equipment.no_of_visits
    #
    #         partner = maintenance_equipment.contract_id.partner_id
    #
    #         recurrent  = maintenance_equipment.recurrent
    #
    #
    #         work_location_id = False
    #         if partner.customer_city_id and partner.customer_city_id.def_work_center_id:
    #             work_location_id = partner.customer_city_id.def_work_center_id.id
    #
    #         project = self.env['project.project'].search([('name', '=', 'HHS - AMC Project')], limit=1)
    #         service_nature = self.env['service.nature'].search(
    #                 [('code', '=', '001')],
    #                 limit=1)
    #         service_team_id = self.env['machine.support.team'].search([('leader_id','=',maintenance_equipment.technician_user_id.id)],limit=1)
    #
    #         vals = {
    #             'partner_id': partner.id,
    #             'customer_name': partner.name,
    #             'phone': partner.mobile or partner.phone,
    #             'email': partner.email,
    #             'customer_city_id': partner.customer_city_id.id if partner.customer_city_id else False,
    #             'country_district_id' : partner.customer_city_id.country_district_id.id  if partner.customer_city_id.country_district_id else False,
    #             'work_location_id': work_location_id,
    #             'contract_id': maintenance_equipment.contract_id.id,
    #             'asset_id': maintenance_equipment.id,
    #             'brand' : maintenance_equipment.brand_id.name,
    #             'product_id':maintenance_equipment.service_products_code_id.id or False,
    #             "amc_project_id" : maintenance_equipment.project_team_id.id or False,
    #             'nature_of_service_id' : service_nature.id or False,
    #             'maintenance_type' :'preventive',
    #             "user_id" : maintenance_equipment.technician_user_id.id or False,
    #             "product_slno" : maintenance_equipment.serial_no or False,
    #             "team_id" : service_team_id.id or False,
    #             "contract_date" : maintenance_equipment.contract_start_date,
    #             "contract_expiry_date":maintenance_equipment.contract_end_date,
    #             "service_products_code_id":maintenance_equipment.service_products_code_id.id or False
    #         }
    #         if next_visit_schedule_date <= maintenance_equipment.contract_end_date:
    #             service_request = self.env['machine.repair.support'].sudo().create(vals)
    #             service_request._compute_update_contract_line()
    #
    #             if service_request and next_visit_schedule_date and no_of_visits:
    #                 interval = 12 / no_of_visits
    #
    #                 months = math.floor(interval)
    #                 days = round((interval - months) * 30)
    #
    #                 maintenance_equipment.next_schedule_visit = next_visit_schedule_date + relativedelta(
    #                     months=months,
    #                     days=days
    #                 )
            

        
        
        
        
        
        
    
class MaintenanceMixin(models.AbstractModel):
    _inherit = 'maintenance.mixin'

    technician_user_id = fields.Many2one('res.users', string='Default Technician', tracking=True)



