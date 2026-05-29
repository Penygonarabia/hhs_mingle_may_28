# -*- coding: utf-8 -*-
import time
from odoo.exceptions import UserError
from odoo import models, fields, api, _
from odoo.exceptions import UserError, warnings, ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import pytz
import requests
import logging
from odoo.exceptions import RedirectWarning
import re
from geopy.geocoders import Nominatim
from num2words import num2words
from num2words.lang_EN import Num2Word_EN
from translate import Translator

_logger = logging.getLogger(__name__)

"""
code   State
101    New
102    Scheduled (Technician Assigned)
103    Technician Accepted
104    Technician Rejected
105    Failed to attend call (Customer not answered)
106    Out of City
107    Rescheduled (Collect the re-schedule date & time @ the time of this request)
108    Customer Accepted
109    Technician Started
110    Technician Reached
111    Warranty Verification
112    Cancelled. Not Agree to Pay for Inspection
113    Inspection Started
114    Quotation provided. Waiting customer approval
115    Job Started (In-progress)
116    Payment Refused
117    Unit Pull Out
118    Unit Replaced
119    Unit Returned
120    Pending
121    On Hold - Spare Parts Required
122    Parts Ready
123    Parts Received
124    Cancelled
125    Ready to Invoice (Complete)
126    Closed

"""


class MachineRepairSupport(models.Model):
    _name = "machine.repair.support"
    _description = "Machine Repair Support"
    _order = "id desc"
    #     _inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "format.address.mixin",
        "portal.mixin",
    ]

    @api.model
    def create(self, vals):
        if vals.get("state"):
            state = self.env["project.task.type"].sudo().browse(vals["state"])
            if not state.exists():
                vals["state"] = False
        # return super().create(vals)

        if vals.get("custome_client_user_id", False):
            client_user_id = self.env["res.users"].browse(
                int(vals.get("custome_client_user_id"))
            )
            if client_user_id:
                vals.update({"company_id": client_user_id.company_id.id})
        else:
            vals.update({"custome_client_user_id": self.env.user.id})

        if vals.get("name", False):
            if not vals.get("name", "New") == "New":
                vals["subject"] = vals["name"]

        ##### currently worked client want to parallel run commented on  Sep 23-2025
        if (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.sequence_creation_bool")
            == "True"
        ):
            if vals.get("name", "New") == "New":
                now = datetime.now()
                current_month = now.month
                current_year = now.year
                year_str = now.strftime("%y")
                month_str = now.strftime("%m")
                
                # amc_project = self.env["project.project"].search(
                #     [("name", "=", "HHS - AMC Project")], limit=1
                # )
 
                # amc_project_id = amc_project.id
 
                # AMC check
                # is_amcId = vals.get("amc_project_id")
 
                # sequence_code = (
                #     "amc.machine.repair.support"
                #     if is_amcId == amc_project_id
                #     else "machine.repair.support"
                # )
                project_id = vals.get("project_id")
                amc_id = vals.get("amc_project_id")
                project_search = self.env['project.project'].search([('id','=',amc_id),("name", "=", "HHS")],limit=1)
            
                sequence_code = (
                    "amc.machine.repair.support"
                    if not project_search
                    else "machine.repair.support"
                )
 
                # Get sequence
                sequence = self.env["ir.sequence"].search(
                    [("code", "=", sequence_code)], limit=1
                )

                # # Get the sequence object
                # sequence = self.env["ir.sequence"].search(
                #     [("code", "=", "machine.repair.support")], limit=1
                # )
                loc = "RO-"
                number = 1

                # Get the location_id from vals
                location_id = vals.get("work_location_id")
                # location_id = vals.get('location_id')

                # Loop through date_range_ids
                if project_search:
                    if sequence.use_date_range and sequence.use_location_wise:
                        for date_range in sequence.date_range_ids:
                            if (
                                date_range.date_from.month == current_month
                                and date_range.date_from.year == current_year
                            ):
                                if date_range.work_center_id.id == location_id:
                                    loc = date_range.location_code
                                    number = date_range.number_next_actual
                                    date_range.number_next_actual += 1
                                    break
                        seq = f"{loc}{year_str}{month_str}{str(number).zfill(4)}"
                        existing = self.env["machine.repair.support"].search(
                            [("name", "=", seq)], limit=1
                        )
                        if existing:
                            raise ValidationError(
                                f"A record with first name '{seq}' already exists."
                            )
                        vals["name"] = seq
                    elif sequence.use_date_range:
                        for date_range in sequence.date_range_ids:
                            if (
                                date_range.date_from.month == current_month
                                and date_range.date_from.year == current_year
                            ):
                                loc = date_range.location_code
                                number = date_range.number_next_actual
                                date_range.number_next_actual += 1
                                break
                        seq = f"{loc}{year_str}{month_str}{str(number).zfill(4)}"
    
                        existing = self.env["machine.repair.support"].search(
                            [("name", "=", seq)], limit=1
                        )
    
                        if existing:
                            raise ValidationError(
                                f"A record with second name '{seq}' already exists."
                            )
                        # vals['name'] = self.env['ir.sequence'].next_by_code('machine.repair.support') or 'New'
    
                        vals["name"] = seq
                    else:
                        vals["name"] = (
                            self.env["ir.sequence"].next_by_code("machine.repair.support")
                            or "New"
                        )
             
                '''Code Added on May 21 2026 by Vijaya Bhaskar'''
                if not project_search:
                    if vals.get('maintenance_type') == 'corrective':

                        contract_id = vals.get('contract_id')
                        product_id = vals.get("service_products_code_id")
                
                        contract = self.env["subscription.contracts"].browse(contract_id)
                
                        # Get matching contract line
                        line = contract.contract_line_ids.filtered(
                            lambda l: l.product_id.id == product_id
                        )[:1]
                
                        ordered_count = line.no_of_emergency_visit if line else 0
                
                        # Existing corrective visits count
                        machine_repair_search = self.env['machine.repair.support'].search_count([
                            ('contract_id', '=', contract.id),
                            ('service_products_code_id', '=', product_id),
                            ('maintenance_type', '=', 'corrective')
                        ])
                
                        # Exceeded check
                        if machine_repair_search >= ordered_count:
                            vals['emergency_count_exceed'] = True
                
                        # Sequence Name
                        vals['name'] = f"{contract.name}/EC-{machine_repair_search + 1:02d}"
                    
                    
                    '''Code Added on May 23 2026 by Vijaya Bhaskar because Already Preventive Count has finished their quota'''
                    # if vals.get('maintenance_type') == 'preventive' and vals.get('paid_service_bool')==True:
                    #     contract_id = vals.get('contract_id')
                    #     product_id = vals.get("service_products_code_id")
                    #
                    #     contract = self.env["subscription.contracts"].browse(contract_id)
                    #
                    #     machine_repair_search = self.env['machine.repair.support'].search_count([
                    #         ('contract_id', '=', contract.id),
                    #         ('service_products_code_id', '=', product_id),
                    #         ('maintenance_type', '=', 'preventive'),
                    #         ('paid_service_bool','=', True)
                    #     ])
                    #
                    #
                    #     vals['emergency_count_exceed'] = True
                    #
                    #     # Sequence Name
                    #     vals['name'] = f"{contract.name}/PS-{machine_repair_search + 1:02d}"
                    #

                        
                    
                
        if vals.get("partner_id", False):
            if "phone" and "email" not in vals:
                partner = self.env["res.partner"].sudo().browse(vals["partner_id"])
                if partner:
                    vals.update(
                        {
                            "email": partner.email,
                            "phone": partner.mobile,
                        }
                    )

        """ if the default warranty is false then it will cause error because default lambda is not work for first time for this field
         sr_service_warranty_id = fields.Many2one('service.warranty', string="Service Warranty", 
                                             default  = lambda self: self.env['service.warranty'].search([('warranty_applicable_bool','=',False)]))

        if not vals.get('sr_service_warranty_id'):
            warranty = self.env['service.warranty'].search([('warranty_applicable_bool', '=', False)], limit=1)
            if warranty:
                vals['sr_service_warranty_id'] = warranty.id 
        """
        if vals.get("sr_service_warranty_id"):
            if vals.get("warranty"):

                if not vals.get("purchase_invoice_no"):
                    raise ValidationError(
                        _("Please enter Purchase Invoice No in the Service Request")
                    )

                if not vals.get("purchase_date"):
                    raise ValidationError(
                        _("Please enter Purchase date in the Service Request")
                    )

                if not vals.get("dealer_id"):
                    raise ValidationError(
                        _("Please enter Dealer Name in the Service Request")
                    )

        if vals.get("phone", False):
            search_partner = self.env["res.partner"].search(
                [("mobile", "=", vals.get("phone"))], limit=1
            )
            if search_partner:
                vals["partner_id"] = search_partner.id

        symptom_lines = vals.get("symptom_line_ids", [])
        problem = vals.get("problem")

        if not self.env.context.get("skip_state_validation"):
            if not symptom_lines and not problem:
                raise ValidationError(
                    _(
                        "Please enter at least one line in Symptoms or Complaint Details."
                    )
                )

        record = super(MachineRepairSupport, self).create(vals)
        record._create_job_card()
        record._send_whatsapp_greeting()
        """HHS Client again ask customer is retrieved from the res_partner need not fetch from the service request itself on JULY 29-2025 """
        record._create_res_partner()
        # record.action_show_job_card()
        # return super(MachineRepairSupport, self).create(vals)
        return record

    def _create_job_card(self):
        for rec in self:
            job_card_vals = {
                "service_nature_id": rec.nature_of_service_id.id,
                "location_id": rec.location_id.id,
                "name": rec.name,
                "partner_id": rec.partner_id.id,
                "phone": rec.phone,
                "service_created_datetime": rec.request_date,
                # 'priority' : rec.priority,
                "service_requested_datetime": rec.call_request_appointment_date,
                "technician_id": rec.user_id.id,
                # 'appointment_datetime': rec.technician_appointment_date,
                # 'planned_date_begin' : rec.technician_appointment_date,
                # 'appointment_datetime' : rec.call_request_appointment_date,
                # 'technician_appointment_date' : rec.technician_appointment_date,
                # 'state': rec.state,
                "product_category_id": rec.product_category.id,
                "product_id": rec.product_id.id,
                "brand": rec.brand,
                "model": rec.model,
                "product_slno": rec.product_slno,
                "purchase_invoice_no": rec.purchase_invoice_no,
                "purchase_date": rec.purchase_date,
                "dealer_id": rec.dealer_id.id,
                # 'purchase_dealer_name': rec.purchase_dealer_name,
                "warranty": rec.warranty,
                "warranty_expiry_date": rec.website_year,
                "client_comments": rec.problem,
                "service_call_center_comments": rec.call_center_comments,
                "region_id": rec.location_id.res_region_id.id,
                "work_center_id": rec.work_location_id.id,
                # Code was commented on August -26-2025 by Vijaya Bhaskar because client asked warehouse was selected based on the technician id filtered'''
                # 'warehouse_id' : rec.warehouse_id.id,
                # 'warehouse_code':rec.warehouse_id.code,
                "service_request_id": rec.id,
                "job_card_partner_city": rec.partner_city,
                "job_card_state_code": rec.service_request_state_code,
                "job_card_state": rec.service_request_state,
                "sale_order_id": False,
                "sale_line_id": False,
                "priority": rec.priority if rec.priority == "1" else None,
                "work_center_group_id": rec.work_location_id.work_center_group_id.id,
                "planned_date_begin": (
                    rec.technician_appointment_date
                    if rec.technician_appointment_date
                    else None
                ),
                "team_id": rec.team_id.id if rec.team_id else None,
                "customer_city_id": rec.customer_city_id.id or None,
                "country_district_id": rec.country_district_id.id or None,
                "country_state_id": rec.country_state_id.id or None,
                "country_id": rec.country_id.id or None,
                "zip_code": rec.zip_code or None,
                "customer_name": rec.customer_name or None,
                "customer_identification_scheme": rec.customer_identification_scheme
                or None,
                "customer_identification_number": rec.customer_identification_number
                or None,
                "whatsapp_opt_in": rec.whatsapp_opt_in or None,
                "building_number": rec.building_number or False,
                "plot_identification": rec.plot_identification or False,
                "partner_latitude": rec.partner_latitude or False,
                "partner_longitude": rec.partner_longitude or False,
                "latitude": rec.partner_latitude or False,
                "longitude": rec.partner_longitude or False,
                "address_one": rec.address_one or False,
                "address_two": rec.address_two or False,
                "email": rec.email or False,
                "address": rec.address or None,
                "product_group_id": rec.product_group_id.id or None,
                "product_sub_group_id": rec.product_sub_group_id.id or None,
                "svc_id": rec.svc_id.id or None,
                "symptoms_line_ids": [
                    (0, 0, {"code": line.sym_id.id}) for line in rec.symptom_line_ids
                ],
                "attachment_ids": rec.attachment_ids.ids or None,
                "service_warranty_id": rec.sr_service_warranty_id.id or None,
                "img1_text": "Unit Name Plate",
                "img2_text": "Damaged Parts",
                "amc_project_id": rec.amc_project_id.id or None,
                "maintenance_type": rec.maintenance_type or None,
                "contract_id": rec.contract_id.id or False,
                "contract_date": rec.contract_date or None,
                "contract_expiry_date": rec.contract_expiry_date or None,
                "asset_id": rec.asset_id.id or None,
                "service_products_code_id": rec.service_products_code_id.id or None,
                "actual_preventive": rec.actual_preventive or None,
                "actual_corrective": rec.actual_corrective or None,
                "paid_service_bool": rec.paid_service_bool or None,
                "project_related_amc_bool": rec.project_related_amc_bool or None,
                "inspection_charges_amount": (
                    rec.paid_service_amount
                    if rec.paid_service_amount > 0 and rec.paid_service_bool
                    else None
                ),
                "balance_amount_received_bool": (
                    True if rec.project_related_amc_bool else False
                ),
                "action_status": "Not Closed",
                "type_of_property": rec.type_of_property or None,
                "property_type_maintenance_details_id": rec.property_type_maintenance_details_id.id
                or None,
                "company_preventive_maintenance_bool": rec.company_preventive_maintenance_bool
                or None,
                "company_preventive_maintenance": rec.company_preventive_maintenance
                or None,
                "service_group_batch": self.service_group_batch or False,

                "service_create_from_equipment_bool" : self.service_create_from_equipment_bool or False,
                "maintenance_contract_type_id" :  self.maintenance_contract_type_id.id or False,
                'emergency_count_exceed' : self.emergency_count_exceed or False,
                'used_location_equipment' : self.used_location_equipment or False,

            }

            # job_card = self.env['project.task'].with_context(skip_warranty_validation=True).sudo().create(job_card_vals)

            job_card = (
                self.env["project.task"]
                .with_context(
                    skip_warranty_validation=True,
                    skip_state_validation=True,
                    creating=True,
                )
                .sudo()
                .create(job_card_vals)
            )

            # job_card = self.env['project.task'].with_context(skip_state_validation=True).sudo().create(job_card_vals)
            rec.task_id = job_card.id
            _logger.info(
                "✅ ...................Job card state code %s",
                job_card.job_card_state_code,
                self.service_request_state_code,
            )

            job_card._onchange_planned_date_begin()
            """if technician is assign from the service then automatically update in the job card on July 19 2025"""
            self._onchange_team_id()
            job_card._compute_technician_id()
            if rec.project_related_amc_bool:
                job_card.action_load_checklist()

            """code added on DEC 5 if warranty is selected then purchase date and warranty expiry date is created to job card"""
            if self.purchase_date:
                job_card._onchange_purchase_date_warranty()
            if self.website_year:
                job_card._onchange_expiry_date_warranty()

            if job_card.team_id:
                scheduled_state = self.env["project.task.type"].search(
                    [("code", "=", "102")], limit=1
                )

                job_card.job_card_state_code = scheduled_state.code
                job_card.job_card_state = scheduled_state.name
                job_card.job_state = scheduled_state
                job_card.available_state_ids = [
                    (
                        6,
                        0,
                        self.env["project.task.type"]
                        .search([("code", "in", ("102", "103", "104"))])
                        .ids,
                    )
                ]
                # job_card._onchange_job_card_state_status()
                job_card._compute_available_state_ids()

            # self.action_whatsapp_send()
            # rec.job_card_no = job_card.name

    def _create_res_partner(self):
        for rec in self:
            partner_vals = {
                "name": rec.customer_name or False,
                "street": rec.address_one or False,
                "street2": rec.address_two or False,
                "customer_city_id": rec.customer_city_id.id or False,
                "state_id": rec.country_state_id.id or False,
                "country_id": rec.country_id.id or False,
                "zip": rec.zip_code or False,
                "building_number": rec.building_number or None,
                "plot_identification": rec.plot_identification or None,
                "email": rec.email or None,
                "x_whatsapp_opt_in": rec.whatsapp_opt_in or None,
                "mobile": rec.phone or None,
                "partner_type_hhs": "customer",
                "sub_partner_type": "retail",
                "vat": (
                    rec.customer_identification_number
                    if rec.customer_identification_scheme == "TIN"
                    else None
                ),
                "additional_identification_number": (
                    rec.customer_identification_number
                    if rec.customer_identification_scheme != "TIN"
                    else None
                ),
                "additional_identification_scheme": rec.customer_identification_scheme,
            }
            partner_search = self.env["res.partner"].search(
                [("mobile", "=", rec.phone), ("id", "=", rec.partner_id.id)]
            )
            # if not partner_search:
            #     partner = self.env['res.partner'].create(partner_vals)
            #     rec.partner_id = partner
            if not partner_search:
                partner = self.env["res.partner"].create(partner_vals)
                rec.partner_id = partner.id
                rec.task_id.partner_id = partner.id
            else:
                partner = partner_search.update(
                    {
                        "vat": (
                            rec.customer_identification_number
                            if rec.customer_identification_scheme == "TIN"
                            else None
                        ),
                        "additional_identification_number": (
                            rec.customer_identification_number
                            if rec.customer_identification_scheme != "TIN"
                            else None
                        ),
                        "additional_identification_scheme": rec.customer_identification_scheme,
                        "building_number": (
                            rec.building_number
                            if rec.customer_identification_scheme == "TIN"
                            else None
                        ),
                        "plot_identification": (
                            rec.plot_identification
                            if rec.customer_identification_scheme == "TIN"
                            else None
                        ),
                    }
                )
                rec.partner_id = partner_search.id

    def _send_whatsapp_greeting(self):
        _logger.info("✅ WhatsApp greeting send triggered for order %s", self.name)
        if (
            not self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.whatsapp_send_bool")
            == "True"
        ):
            _logger.info("❌ No WhatsApp set in res Config Settings")
            return False

        # Validate partner data
        phone_number = self.phone
        whatsapp_opt_in = self.whatsapp_opt_in
        # whatsapp_opt_in = self.partner_id.x_whatsapp_opt_in
        country_code = self.country_id.phone_code

        if not whatsapp_opt_in:
            _logger.info("❌ No WhatsApp opt-in for customer %s", self.customer_name)
            return False

        if not phone_number:
            _logger.info(
                "❌ No mobile number found for customer  %s", self.customer_name
            )
            return False

        # Format phone number (E.164 without +)
        phone_number = phone_number.replace("+", "").replace(" ", "")
        phone_number = f"{country_code}{phone_number}"
        _logger.info("............Formatted phone number: %s", phone_number)

        # base_url = 'https://graph.facebook.com/v18.0/629139543620025'
        whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"

        base_url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}"

        access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"

        # headers = {
        #     'Authorization': f'Bearer {access_token}',
        # }

        # base_url = f'https://graph.facebook.com/{api_version}/{phone_number_id}'
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        if not access_token:
            _logger.error("❌ No WhatsApp access token configured")
            return False

        # Send greeting template message
        template_url = f"{base_url}/messages"
        # template_payload = {
        #     'messaging_product': 'whatsapp',
        #     'to': phone_number,
        #     'type': 'template',
        #     'template': {
        #         'name': 'hello_world',
        #         'language': {'code': 'en_US'}
        #     }
        # }

        """
        message = False
     
        message = f"Welcome Shaker & Co. \n \n Dear Customer {self.customer_name},\n Thank you for contacting Shaker & Co. your service request number is {self.name}.We will send you an appointment schedule shortly.\n\n Thank You.\n Service Team"
                
        template_payload = {
            
            'messaging_product':"whatsapp",
            'to':phone_number,
            "type":"text",
            "text":{
                'body': message,
                }
            
            }
        """

        """This is working perfect but i commented by Vijaya Bhaskar on august-02-2025 because they don't want Default Template """
        """
        template_payload = {
              "messaging_product": "whatsapp",
               'to': phone_number,
              "type": "template",
              "template": {
                "name": "initial_contact_optin",
                "language": {
                  "code": "en"
                },
                "components": [
                    
                #     {
                #     "type": "body",
                #     "parameters": [
                #         {"type": "text", "text": str(self.name or "")}
                #     ]
                # },
                  {
                    "type": "button",
                    "sub_type": "quick_reply",
                    "index": "0",
                    "parameters": [
                      {
                        "type": "payload",
                        "payload": "OPTIN_YES"
                      }
                    ]
                  },
                  {
                    "type": "button",
                    "sub_type": "quick_reply",
                    "index": "1",
                    "parameters": [
                      {
                        "type": "payload",
                        "payload": "OPTIN_NO"
                      }
                    ]
                  }
                 
                ]
              }
            }
            """

        template_payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                # "name": "approval",
                # "name": "initial_contact_optin",
                "name": "greetings",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(self.name)},
                            {"type": "text", "text": str(self.name)},  # Replaces {{2}}
                        ],
                    },
                    {
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": "0",
                        "parameters": [{"type": "payload", "payload": "OPTIN_YES"}],
                    },
                    {
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": "1",
                        "parameters": [{"type": "payload", "payload": "OPTIN_NO"}],
                    },
                ],
            },
        }

        try:
            response = requests.post(
                template_url, headers=headers, json=template_payload
            )
            response.raise_for_status()
            _logger.info("✅ Greeting message sent for order %s:", self.name)
            # _logger.info("✅ Greeting message sent for order %s:%s", self.name, response.json())
            self.message_post(body=_("WhatsApp greeting message sent successfully"))
            return True

        except requests.exceptions.RequestException as e:
            _logger.error(
                "❌ Greeting Message Failed to send WhatsApp message: %s", str(e)
            )
            return False

    # def _send_whatsapp_greeting(self):
    #     _logger.info(
    #         "✅ WhatsApp greeting send triggered for order %s at %s", self.name
    #     )
    #     if (
    #         not self.env["ir.config_parameter"]
    #         .sudo()
    #         .get_param("machine_repair_management.whatsapp_send_bool")
    #         == "True"
    #     ):
    #         _logger.info("❌ No WhatsApp set in res Config Settings")
    #         return False

    #     # Validate partner data
    #     phone_number = self.phone
    #     whatsapp_opt_in = self.whatsapp_opt_in
    #     # whatsapp_opt_in = self.partner_id.x_whatsapp_opt_in
    #     country_code = self.country_id.phone_code

    #     if not whatsapp_opt_in:
    #         _logger.info("❌ No WhatsApp opt-in for customer %s", self.customer_name)
    #         return False

    #     if not phone_number:
    #         _logger.info(
    #             "❌ No mobile number found for customer  %s", self.customer_name
    #         )
    #         return False

    #     # Format phone number (E.164 without +)
    #     phone_number = phone_number.replace("+", "").replace(" ", "")
    #     phone_number = f"{country_code}{phone_number}"
    #     _logger.info("Formatted phone number: %s", phone_number)

    #     # base_url = 'https://graph.facebook.com/v18.0/629139543620025'
    #     whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"

    #     base_url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}"

    #     access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"

    #     # headers = {
    #     #     'Authorization': f'Bearer {access_token}',
    #     # }

    #     # base_url = f'https://graph.facebook.com/{api_version}/{phone_number_id}'
    #     headers = {
    #         "Authorization": f"Bearer {access_token}",
    #         "Content-Type": "application/json",
    #     }
    #     if not access_token:
    #         _logger.error("❌ No WhatsApp access token configured")
    #         return False

    #     # Send greeting template message
    #     template_url = f"{base_url}/messages"
    #     # template_payload = {
    #     #     'messaging_product': 'whatsapp',
    #     #     'to': phone_number,
    #     #     'type': 'template',
    #     #     'template': {
    #     #         'name': 'hello_world',
    #     #         'language': {'code': 'en_US'}
    #     #     }
    #     # }

    #     """
    #     message = False

    #     message = f"Welcome Shaker & Co. \n \n Dear Customer {self.customer_name},\n Thank you for contacting Shaker & Co. your service request number is {self.name}.We will send you an appointment schedule shortly.\n\n Thank You.\n Service Team"

    #     template_payload = {

    #         'messaging_product':"whatsapp",
    #         'to':phone_number,
    #         "type":"text",
    #         "text":{
    #             'body': message,
    #             }

    #         }
    #     """

    #     """This is working perfect but i commented by Vijaya Bhaskar on august-02-2025 because they don't want Default Template """
    #     """
    #     template_payload = {
    #           "messaging_product": "whatsapp",
    #            'to': phone_number,
    #           "type": "template",
    #           "template": {
    #             "name": "initial_contact_optin",
    #             "language": {
    #               "code": "en"
    #             },
    #             "components": [

    #             #     {
    #             #     "type": "body",
    #             #     "parameters": [
    #             #         {"type": "text", "text": str(self.name or "")}
    #             #     ]
    #             # },
    #               {
    #                 "type": "button",
    #                 "sub_type": "quick_reply",
    #                 "index": "0",
    #                 "parameters": [
    #                   {
    #                     "type": "payload",
    #                     "payload": "OPTIN_YES"
    #                   }
    #                 ]
    #               },
    #               {
    #                 "type": "button",
    #                 "sub_type": "quick_reply",
    #                 "index": "1",
    #                 "parameters": [
    #                   {
    #                     "type": "payload",
    #                     "payload": "OPTIN_NO"
    #                   }
    #                 ]
    #               }

    #             ]
    #           }
    #         }
    #         """

    #     template_payload = {
    #         "messaging_product": "whatsapp",
    #         "to": phone_number,
    #         "type": "template",
    #         "template": {
    #             # "name": "approval",
    #             # "name": "initial_contact_optin",
    #             "name": "greetings",
    #             "language": {"code": "en"},
    #             "components": [
    #                 {
    #                     "type": "body",
    #                     "parameters": [
    #                         {"type": "text", "text": str(self.name)},
    #                         {"type": "text", "text": str(self.name)},  # Replaces {{2}}
    #                     ],
    #                 },
    #                 {
    #                     "type": "button",
    #                     "sub_type": "quick_reply",
    #                     "index": "0",
    #                     "parameters": [{"type": "payload", "payload": "OPTIN_YES"}],
    #                 },
    #                 {
    #                     "type": "button",
    #                     "sub_type": "quick_reply",
    #                     "index": "1",
    #                     "parameters": [{"type": "payload", "payload": "OPTIN_NO"}],
    #                 },
    #             ],
    #         },
    #     }

    #     try:
    #         response = requests.post(
    #             template_url, headers=headers, json=template_payload
    #         )
    #         response.raise_for_status()
    #         _logger.info(
    #             "✅ Greeting message sent for order %s: %s", self.name, response.json()
    #         )
    #         self.message_post(body=_("WhatsApp greeting message sent successfully"))
    #         return True
    #     except requests.exceptions.RequestException as e:
    #         error_details = {
    #             "status_code": response.status_code if response else "No response",
    #             "request_payload": template_payload,
    #         }
    #         _logger.error(
    #             "❌ Greeting send error for order %s: %s | Details: %s",
    #             self.name,
    #             str(e),
    #         )
    #         return False

    #    @api.multi odoo13
    @api.depends("timesheet_line_ids.unit_amount")
    def _compute_total_spend_hours(self):
        for rec in self:
            spend_hours = 0.0
            for line in rec.timesheet_line_ids:
                spend_hours += line.unit_amount
            rec.total_spend_hours = spend_hours

    @api.onchange("project_id")
    def onchnage_project(self):
        for rec in self:
            rec.analytic_account_id = rec.project_id.analytic_account_id

    def action_whatsapp_send(self):
        for rec in self:
            if not rec.phone:
                raise ValidationError("Please Enter Correct Phone Number")

            message = "Your Service Request %s is Created" % rec.name
            whatsapp_url = "https://api.whatsapp.com/send?phone=%s&text=%s" % (
                rec.phone,
                message,
            )
            return {
                "type": "ir.actions.act_url",
                "target": "new",
                "url": whatsapp_url,
            }

    @api.onchange("product_id")
    def onchnage_product(self):
        for rec in self:
            '''Code Added on May 23 2026 by Vijaya Bhaskar because they need product from contract'''
            if not rec.project_related_amc_bool:
                rec.brand = rec.product_id.brand
                # rec.color = rec.product_id.color odoo13
                rec.color = rec.product_id.color_custom
                rec.model = rec.product_id.model
                rec.year = rec.product_id.year

    state = fields.Many2one(
        "project.task.type",
        string="Machine Status",
        domain=lambda self: self._get_machine_state_domain(),
        tracking=True,
        store=True,
    )

    @api.model
    def _get_machine_state_domain(self):
        domain = []
        if self.project_id:
            project = self.env["project.project"].browse(self.project_id.id)
            if project.exists():
                domain.append(("project_ids", "=", project.id))

        user = self.env.user
        if user.has_group("machine_repair_management.group_job_card_back_office_user"):
            domain.append(("back_office_user", "=", True))
        elif user.has_group("machine_repair_management.group_job_card_mobile_user"):
            domain.append(("mobile_user", "=", True))

        return domain

    @api.onchange("project_id")
    def _onchange_project_id(self):
        # This ensures that when the project_id is changed, the corresponding state is set
        if self.project_id:
            # Find the corresponding fallback state based on the selected project
            fallback_state = self.env["project.task.type"].search(
                [("project_ids", "=", self.project_id.id)], limit=1
            )
            if fallback_state:
                self.state = fallback_state.id
            else:
                self.state = False  # If no state is found, reset it to False

    @api.onchange("state")
    def _onchange_machine_state(self):
        # Ensure that the state exists, otherwise reset it
        if self.state and not self.state.exists():
            self.state = False

    def write(self, vals):
        if vals.get("state"):
            state = self.env["project.task.type"].sudo().browse(vals["state"])
            if not state.exists():
                vals["state"] = False
        return super().write(vals)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        # Set the default project_id if it's provided (or fetched dynamically)
        if self.project_id:
            project = self.env["project.project"].browse(self.project_id.id)
            fallback_state = self.env["project.task.type"].search(
                [("project_ids", "=", project.id)], limit=1
            )
            if fallback_state:
                res["state"] = fallback_state.id
        return res

    """ This code is commented by Vijaya bhaskar on Jun-11-2025 for time being because name field is not shown in the Import/Export because it is readonly"""
    name = fields.Char(
        string="Number",
        required=False,
        default="New",
        copy=False,
        readonly=True,
        exportable=True,
    )

    email = fields.Char(string="Email", required=False)
    phone = fields.Char(string="Mobile No")
    category = fields.Selection(
        [
            ("technical", "Technical"),
            ("functional", "Functional"),
            ("support", "Support"),
        ],
        string="Category",
    )
    subject = fields.Char(string="Subject")
    description = fields.Text(string="Description")
    priority = fields.Selection(
        [("0", "Low"), ("2", "Middle"), ("1", "High")], string="Priority", default="0"
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
    )
    request_date = fields.Datetime(
        string="Create Date",
        default=fields.Datetime.now,
        copy=False,
    )
    close_date = fields.Datetime(
        string="Close Date",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Technician",
    )
    available_user_ids = fields.Many2many(
        "res.users", compute="_compute_available_user_ids", store=True
    )
    active = fields.Boolean(default=True)

    @api.depends("team_id", "team_id.support_team_line_ids")
    def _compute_available_user_ids(self):
        for rec in self:
            rec.available_user_ids = False
            team_lst = []
            if rec.team_id:
                if rec.team_id.support_team_line_ids:
                    for line in rec.team_id.support_team_line_ids:
                        # if line.is_default_team_member:
                        team_lst.append(line.support_team_user_id.id)
                        # if line.is_default_team_member:
                        rec.available_user_ids = team_lst
                        # rec.available_user_ids = line.support_team_user_id.ids

    @api.onchange("team_id")
    def _onchange_team_id(self):
        for rec in self:
            if rec.team_id:
                rec.user_id = rec.team_id.leader_id.id
                # available_ids = rec.available_user_ids.ids
                # default_line = rec.team_id.support_team_line_ids.filtered(lambda l: l.is_default_team_member)
                # if default_line and default_line.support_team_user_id.id in available_ids:
                #     rec.user_id = default_line.support_team_user_id.id
                # elif available_ids:
                #     rec.user_id = available_ids[0]
                # if rec.task_id:
                #     rec.task_id.team_id = rec.team_id.id or False
                #     rec.task_id.technician_id = rec.user_id.id or False
                #

    department_id = fields.Many2one("hr.department", string="Department")
    timesheet_line_ids = fields.One2many(
        "account.analytic.line",
        "repair_request_id",
        string="Timesheets",
    )
    is_close = fields.Boolean(
        string="Is Ticket Closed ?",
        tracking=True,
        default=False,
        copy=False,
    )
    total_spend_hours = fields.Float(
        string="Total Hours Spent", compute="_compute_total_spend_hours"
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        default=lambda self: self._get_default_project(),
    )

    @api.model
    def _get_default_project(self):
        project_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.project_id")
        )
        if project_id:
            return int(project_id)
        else:
            project = self.env["project.project"].search(
                [("name", "=", "HHS")], limit=1
            )
            # print("project", project)
            return project.id if project else False

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
    )
    team_id = fields.Many2one("machine.support.team", string="Machine Repair Team")
    team_leader_id = fields.Many2one(
        "res.users",
        string="Team Leader",
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
    )
    task_id = fields.Many2one(
        "project.task",
        string="Task",
        readonly=True,
    )
    is_task_created = fields.Boolean(
        string="Is Task Created ?",
        default=False,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.user.company_id,
        string="Company",
        readonly=False,
        #        readonly=True,
    )
    comment = fields.Text(
        string="Customer Comment",
    )
    rating = fields.Selection(
        [
            ("poor", "Poor"),
            ("average", "Average"),
            ("good", "Good"),
            ("very good", "Very Good"),
            ("excellent", "Excellent"),
        ],
        string="Customer Rating",
    )
    product_category = fields.Many2one(
        "product.category",
        string="Product Category",
        domain="[('parent_id','=',False),('name', '!=', 'All')]",
    )
    # product_category = fields.Many2one(
    #     'product.category',
    #     string="Product Category",
    #     domain=lambda self: self._get_valid_product_category_domain_check()
    # )
    #
    # @api.model
    # def _get_valid_product_category_domain_check(self):
    #     all_categories = self.env['product.category'].search([('name', '!=', 'All')])
    #     valid_categories = all_categories.filtered(lambda c: not c.parent_id or c.parent_id.name != 'All')
    #     return [('id', 'in', valid_categories.ids)]

    product_id = fields.Many2one("product.product", string="Model No")

    """this Code is commented by Vijaya Bhaskar on Aug -06-2025 due to client ask the product sub category level"""
    # product_id = fields.Many2one(
    #     'product.product',
    #     domain="[('is_machine', '=', True),('categ_id','=',product_category)]",
    #     string="Product"
    # )
    brand = fields.Char(string="Brand")
    color = fields.Char(string="Color")
    model = fields.Char(string="Model")
    year = fields.Char(string="Year")

    accompanying_items = fields.Text(
        string="Accompanying Items",
    )
    damage = fields.Text(
        string="Damage",
    )
    warranty = fields.Boolean(
        string="Warranty",
    )
    img1 = fields.Binary(
        string="Images1",
    )
    img2 = fields.Binary(
        string="Images2",
    )
    img3 = fields.Binary(
        string="Images3",
    )
    img4 = fields.Binary(
        string="Images4",
    )
    img5 = fields.Binary(
        string="Images5",
    )
    repair_types_ids = fields.Many2many("repair.type", string="Repair Type")
    problem = fields.Text(
        string="Complaint Details",
    )
    cosume_part_ids = fields.One2many(
        "product.consume.part", "machine_id", string="Product consume Part"
    )
    nature_of_service_id = fields.Many2one("service.nature", string="Service Types")
    lot_id = fields.Many2one("stock.lot", string="Lot")
    website_brand = fields.Char(string="Website Brand")
    website_model = fields.Char(string="Website Model")
    # website_year = fields.Char(
    #     string = "Website Year"
    # )
    website_year = fields.Date(string="Website Year", store=True)

    is_readonly = fields.Boolean(
        string="Is Readonly", compute="_compute_is_readonly", store=False
    )

    partner_city = fields.Char(string="City")

    """New Added for customer by Vijaya Bhaskar on July - 10 - 2025 """

    customer_city_id = fields.Many2one(
        "res.city", string="City", domain=lambda self: self._get_city_domain()
    )

    district = fields.Char("District")

    country_district_id = fields.Many2one("res.state.district", string="District")

    country_state_id = fields.Many2one(
        "res.country.state",
        string="State",
        ondelete="restrict",
        domain="[('country_id', '=?', country_id)]",
    )

    country_id = fields.Many2one("res.country", string="Country")

    zip_code = fields.Char(string="Zip code")

    customer_name = fields.Char(string="Customer name")

    customer_identification_scheme = fields.Selection(
        [
            ("TIN", "Tax Identification Number"),
            ("CRN", "Commercial Registration Number"),
            ("IQA", "Iqama Number"),
            ("NAT", "National ID"),
        ],
        string="Identification Scheme",
        help="Additional Identification scheme for Seller/Buyer",
    )

    customer_identification_number = fields.Char(
        "VAT No", help="Additional Identification Number for Seller/Buyer"
    )

    whatsapp_opt_in = fields.Boolean(string="Whatsapp", default=True)

    building_number = fields.Char("Building Number")

    plot_identification = fields.Char("Plot Identification")

    partner_latitude = fields.Float(string="Latitude", digits=(10, 7))

    partner_longitude = fields.Float(string="Longitude", digits=(10, 7))

    address_one = fields.Char(string="Address 1")

    address_two = fields.Char(string="Address 2")

    product_group_id = fields.Many2one(
        "product.category",
        string="Product Group",
        context=lambda self: {"show_only_name": True},
    )

    product_sub_group_id = fields.Many2one(
        "product.category",
        string="Product Sub Group",
        context=lambda self: {"show_only_name": True},
    )

    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Attachment",
        domain="[('mimetype','in',['image/jpeg','image/png','application/pdf','image/gif'])]",
    )

    sr_service_warranty_id = fields.Many2one(
        "service.warranty",
        string="Service Warranty",
        default=lambda self: self.env["service.warranty"].search(
            [("warranty_applicable_bool", "=", False)]
        ),
    )

    # available_city_ids = fields.Many2many('res.city',string ="Cities")

    whatsapp_service_send_bool = fields.Boolean(
        string="Whatsapp Send Y/N",
        default=False,
        help="All Whatsapp Send feature Enable/Not in res.config_settings",
        compute="_compute_whatsapp_service_send_bool",
    )

    sequence_creation_bool = fields.Boolean(
        string="Sequence Creation",
        default=False,
        compute="_compute_sequence_creation_bool",
        store=False,
    )

    # @api.depends('customer_name')
    # def _compute_sequence_creation_bool(self):
    #     for rec in self:
    #         rec.sequence_creation_bool = False
    #         if self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.sequence_creation_bool') == 'True':
    #             rec.sequence_creation_bool = True
    #

    @api.depends("customer_name")
    def _compute_sequence_creation_bool(self):
        config_val = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.sequence_creation_bool", "False")
        )
        for rec in self:
            rec.sequence_creation_bool = config_val == "True"

    @api.depends("customer_name")
    def _compute_whatsapp_service_send_bool(self):
        for rec in self:
            rec.whatsapp_service_send_bool = False
            whatsapp_search = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("machine_repair_management.whatsapp_send_bool")
            )
            if whatsapp_search == "True":
                rec.whatsapp_service_send_bool = True

    def _get_city_domain(self):
        user = self.env.user
        work_center = user.default_work_center_id
        if work_center:
            return [("def_work_center_id", "in", work_center.ids)]
        return []

    @api.onchange("sr_service_warranty_id")
    def _onchange_service_warranty(self):
        for rec in self:
            if rec.sr_service_warranty_id:
                rec.warranty = (
                    rec.sr_service_warranty_id.warranty_applicable_bool or None
                )

    @api.constrains("building_number", "plot_identification", "zip_code")
    def _check_building_number(self):
        for rec in self:
            if rec.building_number:
                if not rec.building_number.isdigit():
                    raise ValidationError(
                        "Please enter Building number is always number not character"
                    )
                if rec.building_number.isdigit():
                    if len(rec.building_number) != 4:
                        raise ValidationError("Building number  always 4 numbers")
            if rec.plot_identification:
                if not rec.plot_identification.isdigit():
                    raise ValidationError(
                        "Please enter Plot identification number is always number"
                    )
                if rec.plot_identification.isdigit():
                    if len(rec.plot_identification) != 4:
                        raise ValidationError(
                            "Plot identification Number always 4 digits"
                        )
            if rec.zip_code:
                if not rec.zip_code.isdigit():
                    raise ValidationError(
                        "Please enter Zip Code is always number not character"
                    )
                if rec.zip_code.isdigit():
                    if len(rec.zip_code) != 5:
                        raise ValidationError("Zip Code  always 5 numbers")

    @api.onchange("customer_identification_scheme")
    def _onchange_customer_identification_scheme(self):
        for rec in self:
            if rec.customer_identification_scheme:
                if rec.customer_identification_scheme != "TIN":
                    rec.customer_identification_number = (
                        rec.partner_id.additional_identification_number
                    )
                    rec.building_number = None
                    rec.plot_identification = None
                else:
                    if rec.partner_id.additional_identification_scheme == "TIN":
                        rec.customer_identification_number = rec.partner_id.vat or None
                        rec.building_number = rec.partner_id.building_number or None
                        rec.plot_identification = (
                            rec.partner_id.plot_identification or None
                        )
            else:
                rec.customer_identification_number = None
                rec.building_number = None
                rec.plot_identification = None

    @api.onchange(
        "address_one",
        "address_two",
        "zip_code",
        "district",
        "customer_city_id",
        "country_state_id",
        "country_id",
    )
    def _onchange_get_lat_lon(self):
        for rec in self:
            address_parts = [
                rec.building_number,
                rec.plot_identification,
                rec.address_one,
                rec.address_two,
                rec.zip_code,
                rec.district,
                rec.customer_city_id.name if rec.customer_city_id else "",
                rec.country_state_id.name if rec.country_state_id else "",
                rec.country_id.name if rec.country_id else "",
            ]
            full_address = ", ".join(filter(None, address_parts))
            if full_address:
                try:
                    geolocator = Nominatim(user_agent="odoo_geolocator")
                    location = geolocator.geocode(full_address, timeout=10)
                    if location:
                        rec.partner_latitude = location.latitude
                        rec.partner_longitude = location.longitude
                except Exception as e:
                    _logger.warning(f"GeoPy geocoding failed for '{full_address}': {e}")

    @api.depends("is_readonly")
    def _compute_is_readonly(self):
        for record in self:
            if record.env.user.has_group(
                "machine_repair_management.group_technical_allocation_user"
            ):
                record.is_readonly = True
            else:
                record.is_readonly = False

    @api.constrains("attachment_ids")
    def _validation_attachment_ids(self):
        for rec in self:
            if rec.attachment_ids:
                allowed_mimetypes = [
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "application/pdf",
                ]
                for attachment in rec.attachment_ids:
                    if attachment.mimetype not in allowed_mimetypes:
                        raise ValidationError(
                            "Only PDF, JPG, PNG, and GIF files are allowed.\n"
                            f"Invalid file: {attachment.name}"
                        )

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        user = self.env.user
        # Manager gets all records

        # # Regular user only sees their own records
        # if user.has_group('machine_repair_management.group_machine_repair_user'):
        #     domain += [('user_id', '=', user.id)]
        #     return super(MachineRepairSupport, self).search_fetch(domain, field_names, offset, limit, order)
        #
        # for Admin user

        amc_project_ids = user.project_ids.ids

        """Code added on Aug-29-2025 because Admin user show all the records"""
        if user.has_group("base.group_system"):
            if user.default_work_center_id:
                domain += [("work_location_id", "in", user.default_work_center_id.ids)]
                domain += [("amc_project_id", "in", amc_project_ids)]

            return super(MachineRepairSupport, self).search_fetch(
                domain, field_names, offset, limit, order
            )
        ###supervisor
        if (
            user.has_group("machine_repair_management.group_job_card_back_office_user")
            and user.has_group(
                "machine_repair_management.group_technical_allocation_user"
            )
        ) and user.default_work_center_id:
            domain += [("work_location_id", "in", user.default_work_center_id.ids)]
            domain += [("amc_project_id", "in", amc_project_ids)]
            return super(MachineRepairSupport, self).search_fetch(
                domain, field_names, offset, limit, order
            )
        ###parts User
        if user.has_group(
            "machine_repair_management.group_job_card_back_office_user"
        ) and user.has_group("machine_repair_management.group_parts_user"):
            domain += [("service_request_state_code", "in", ("121", "122"))]
            domain += [("amc_project_id", "in", amc_project_ids)]
            # domain += [
            #     ('job_card_state','=','On Hold - Spare Parts Required'),('job_card_state_code','=','121')
            # ]
            if user.default_work_center_id:
                domain += [("work_center_id", "in", user.default_work_center_id.ids)]
            return super(MachineRepairSupport, self).search_fetch(
                domain, field_names, offset, limit, order
            )

        # if user.has_group('machine_repair_management.group_job_card_back_office_user') and \
        #     user.has_group('machine_repair_management.group_parts_user') and user.default_work_center_id:
        #     domain += [
        #         ('work_location_id', 'in', user.default_work_center_id.ids)
        #     ]
        #     return super(MachineRepairSupport, self).search_fetch(domain, field_names, offset, limit, order)

        # for Admin user
        # if user.has_group('machine_repair_management.group_admin_user') and  \
        #     user.has_group('machine_repair_management.group_job_card_back_office_user'):
        #     if user.default_work_center_id:
        #         domain += [
        #             ('work_location_id', 'in', user.default_work_center_id.ids)
        #         ]
        #     else:
        #         domain += [
        #             ('work_location_id', 'in', self.env['work.center.location'].search([]).ids)
        #         ]
        #
        #     return super(MachineRepairSupport, self).search_fetch(domain, field_names, offset, limit, order)

        # For mobile users (technicians)
        if user.has_group("machine_repair_management.group_job_card_back_office_user"):
            if user.default_work_center_id:
                domain += [
                    ("user_id", "=", user.id),
                    ("work_location_id", "in", user.default_work_center_id.ids),
                ]
                domain += [("amc_project_id", "in", amc_project_ids)]
            else:
                domain += [
                    (
                        "work_location_id",
                        "in",
                        self.env["work.center.location"].search([]).ids,
                    )
                ]
                domain += [("amc_project_id", "in", amc_project_ids)]

            return super(MachineRepairSupport, self).search_fetch(
                domain, field_names, offset, limit, order
            )

        # working corrctly commented by vijay bhaskar on june-18-2025
        # if user.has_group('machine_repair_management.group_job_card_back_office_user') and \
        #     user.has_group('machine_repair_management.group_job_card_mobile_user'):
        #     domain += [
        #         ('user_id', '=', user.id)
        #     ]
        #     return super(MachineRepairSupport, self).search_fetch(domain, field_names, offset, limit, order)

        # Default fallback
        return super(MachineRepairSupport, self).search_fetch(
            domain, field_names, offset, limit, order
        )

    total_consumed_hours = fields.Float(
        string="Total Consumed Hours",
        #         compute='compute_total_hours',
        #         store=True,
    )
    custome_client_user_id = fields.Many2one(
        "res.users",
        string="Ticket Created User",
        readonly=True,
        track_visibility="always",
    )
    product_slno = fields.Char(string="Serial Number")
    purchase_invoice_no = fields.Char(string="Purchase Invoice Number")
    purchase_date = fields.Date(string="Purchase Date")

    # purchase_dealer_name = fields.Char(string="Dealer Name",deprecated=False)
    dealer_id = fields.Many2one(
        "res.partner",
        string="Dealer Name",
        domain="[('partner_type_hhs','=','customer'),('sub_partner_type','=','dealer')]",
    )
    # @api.onchange('dealer_id')
    # def _onchange_dealer_id(self):
    #     if self.dealer_id and not self.dealer_id.id:
    #         # This triggers when clicking "Create and Edit..."
    #         return {
    #             'context': {
    #                 'default_partner_type_hhs': 'customer',
    #                 'default_sub_partner_type': 'dealer'
    #             }
    #         }

    internal_bool = fields.Boolean(string="Internal")
    address = fields.Char(string="Address", compute="_compute_address", store=True)
    job_card_no = fields.Char(string="Job Card No.")
    status = fields.Char(string="Status")
    service_request_state = fields.Char(string="Service Request State", store=True)
    service_request_state_code = fields.Char(string="Service Request Code", store=True)
    work_center_group_id = fields.Many2one(
        "work.center.group", string="Work Center Group"
    )
    import_bool = fields.Boolean(string="Import", default=False)
    svc_id = fields.Many2one(
        "service.capacity",
        string="Capacity",
    )
    capacity = fields.Char(string="Capacity")
    purchase_dealer_name = fields.Char(string="Dealer Name")
    # job_card_read_state = fields.Many2one(related='task_id.job_state', string ="Job card state",store=True, deprecated =True)
    # service_request_state = fields.Char(string = "Service Request State",compute="_compute_job_card_state",store=True)
    # service_request_state_code = fields.Char(string ="Service Request Code",    compute="_compute_job_card_state",store=True)
    # job_card_read_state = fields.Many2one(related='task_id.job_state', string ="Job card state",store=True)

    @api.onchange("state")
    def _onchange_state(self):
        for rec in self:
            rec.service_request_state = rec.state.name
            rec.service_request_state_code = rec.state.code
            # rec.state = rec.job_state

    # @api.model
    # def _default_internal_tab_show_bool(self):
    #     internal_search = self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.internal_service_show')
    #     return internal_search
    #

    # @api.model
    # def _default_maintenance_tab_show_bool(self):
    #     maintenance_search = self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.maintenance_service_show')
    #     return maintenance_search
    #
    # @api.model
    # def _default_job_card_no_bool(self):
    #     job_card_search = self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.job_card_show')
    #     return job_card_search

    internal_tab_show_bool = fields.Boolean(
        string="Internal Tab show", compute="_compute_internal"
    )
    maintenance_tab_show_bool = fields.Boolean(
        string="Maintenance Tab show", compute="_compute_internal"
    )
    job_card_no_bool = fields.Boolean(
        string="Job card no bool", compute="_compute_internal"
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Warehouse", compute="_compute_warehouse", store=True
    )

    # project_type_id = fields.Many2one('project.project', string = "Project")

    """ Commented by Vijaya Bhaskar on Sep 17 2025 due to warehouse interface is not required on the product category 
    @api.constrains('product_category','work_location_id')
    def _check_warehouse_id(self):
        for rec in self:
            if rec.product_category and rec.work_location_id:
                work_center = rec.product_category.category_line_ids.mapped('work_center_location_id')
                if rec.work_location_id not in work_center:
                    raise ValidationError("Please give same Work center in Product Category warehouse is not defined")
    """

    @api.depends("work_location_id", "product_category")
    def _compute_warehouse(self):
        for rec in self:
            rec.warehouse_id = False
            if rec.product_category and rec.work_location_id:
                for warehouse in rec.product_category.category_line_ids:
                    if warehouse.work_center_location_id and rec.work_location_id:
                        if warehouse.work_center_location_id == rec.work_location_id:
                            rec.warehouse_id = warehouse.warehouse_id.id

    @api.depends("call_types_id")
    def _compute_internal(self):
        self.internal_tab_show_bool = False
        self.maintenance_tab_show_bool = False
        self.job_card_no_bool = False

        internal_search = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.internal_service_show")
        )
        maintenance_search = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.maintenance_service_show")
        )
        job_card_search = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.job_card_show")
        )

        if internal_search == "True":
            self.internal_tab_show_bool = True

        if maintenance_search == "True":
            self.maintenance_tab_show_bool = True

        if job_card_search == "True":
            self.job_card_no_bool = True

            # internal_tab_show_bool = fields.Boolean(string="Internal Tab show" , default = _default_internal_tab_show_bool, )

    # maintenance_tab_show_bool = fields.Boolean(string = "Maintenance Tab show", default = _default_maintenance_tab_show_bool, )
    #
    # job_card_no_bool = fields.Boolean(string ="Job card no bool" , default = _default_job_card_no_bool, )

    ##Contract based update field Added on 15-11-2025

    contract_id = fields.Many2one("subscription.contracts", string="Contract No")
    contract_date = fields.Date(string="Contract Start Date")
    # asset_no = fields.Char(string="Asset Tag No")
    symptom_line_ids = fields.One2many(
        "machine.repair.support.symptoms",
        "machine_repair_support_id",
        string="Symptoms",
    )
    contract_expiry_date = fields.Date(string="Contract Expiry Date")

    # asset_id = fields.Many2one(
    #     'subscription.contracts.line',
    #     string="Asset Tag No",
    #     domain="[('subscription_contract_id', '=', contract_id)]"  # Dynamic domain
    # )

    @api.constrains("contract_expiry_date")
    def _check_contract_expiry_date(self):
        for rec in self:
            if rec.contract_expiry_date:
                today = date.today()
                if rec.contract_expiry_date < today:
                    raise ValidationError(_("Contract is already expired"))

    asset_id = fields.Many2one(
        "maintenance.equipment",
        string="Equipment Tag No",
        domain="[('contract_id', '=', contract_id)]",  # Dynamic domain
    )

    service_products_code_id = fields.Many2one(
        "product.product",
        string="Service Unit Type",
        domain="[('detailed_type', '=', 'service')]",
    )

    actual_preventive = fields.Char(
        string="Actual Preventive", compute="_compute_actual_counts", store=True
    )

    actual_corrective = fields.Char(
        string="Actual Corrective", compute="_compute_actual_counts", store=True
    )
    paid_service_bool = fields.Boolean("Paid Service", default=False)
    paid_service_editable = fields.Boolean(
        compute="_compute_paid_service_editable", readonly=False
    )

    contract_already_updated = fields.Boolean(default=False)
    
    '''Code Added on May 21 2026 by Vijaya Bhaskar'''
    emergency_count_exceed = fields.Boolean(string = "Emergency Count")
    
    '''Code Added on May 22 2026 by Vijaya Bhaskar'''
    used_location_equipment = fields.Char(string = "Used in Location")


    @api.depends("contract_id", "asset_id", "service_products_code_id")
    def _compute_actual_counts(self):
        for rec in self:
            total_pre = done_pre = 0
            total_cor = done_cor = 0
            '''Code Added on May 26 2026 by Vijaya Bhaskar client asked total corrective count will be total emergency count irrespective of product'''
            total_corrective_count = 0
            if rec.contract_id and rec.asset_id and rec.service_products_code_id:
                # Filter relevant lines
                lines = rec.contract_id.contract_line_ids.filtered(
                    lambda l: l.product_id == rec.service_products_code_id
                )
                '''Code Added on May 26 2026 by Vijaya Bhaskar client asked total corrective count will be total emergency count irrespective of product'''
                total_corrective_count = sum(line.no_of_emergency_visit for line in rec.contract_id.contract_line_ids)
                for li in lines:
                    # Preventive
                    total_pre += li.days_require_rpm_round_off or 0
                    done_pre += li.actual_prevent_count or 0
                    # Corrective
                    total_cor += li.no_of_emergency_visit or 0
                    done_cor += li.actual_correct_count or 0
            # Set final results
            rec.actual_preventive = f"{done_pre} / {total_pre}"
            # rec.actual_corrective = f"{done_cor} / {total_cor}"
            '''Code Added on May 26 2026 by Vijaya Bhaskar client asked total corrective count will be total emergency count irrespective of product'''
            rec.actual_corrective = f"{done_cor} / {total_corrective_count}"

    # @api.depends("contract_id", "asset_id", "service_products_code_id")
    # def _compute_actual_counts(self):
    #     for rec in self:
    #         total_pre = done_pre = 0
    #         total_cor = done_cor = 0
    #         if rec.contract_id and rec.asset_id and rec.service_products_code_id:
    #             # Filter relevant lines
    #             lines = rec.contract_id.contract_line_ids.filtered(
    #                 lambda l: l.product_id == rec.service_products_code_id
    #             )
    #             for li in lines:
    #                 # Preventive
    #                 total_pre += li.days_require_rpm_round_off or 0
    #                 done_pre += li.actual_prevent_count or 0
    #                 # Corrective
    #                 total_cor += li.no_of_emergency_visit or 0
    #                 done_cor += li.actual_correct_count or 0
    #         # Set final results
    #         rec.actual_preventive = f"{done_pre} / {total_pre}"
    #         rec.actual_corrective = f"{done_cor} / {total_cor}"

    def _compute_update_contract_line(self):
        for rec in self:
            # if rec.service_request_state_code == '126' and not rec.contract_already_updated and rec.amc_project_id:
            if (
                rec.service_request_state_code == "126"
                and not rec.contract_already_updated
                and rec.project_related_amc_bool
            ):
                if rec.contract_id and rec.asset_id and rec.service_products_code_id:
                    # CORRECTIVE JOB
                    '''Code Added on May 23 2026 by Vijaya Bhaskar'''
                    rec.asset_id.last_actual_prevent_visit = fields.Date.today()
                    if rec.maintenance_type == "corrective":
                        lines = rec.contract_id.contract_line_ids.filtered(
                            lambda l: l.product_id == rec.service_products_code_id
                        )
                        for li in lines:
                            if li.actual_correct_count < li.no_of_emergency_visit:
                                li.actual_correct_count += 1

                    # PREVENTIVE JOB
                    if rec.maintenance_type == "preventive":
                        lines = rec.contract_id.contract_line_ids.filtered(
                            lambda l: l.product_id == rec.service_products_code_id
                        )
                        for li in lines:
                            if li.actual_prevent_count < li.days_require_rpm_round_off:
                                li.actual_prevent_count += 1

                    if rec.paid_service_bool:
                        lines = rec.contract_id.contract_line_ids.filtered(
                            lambda l: l.product_id == rec.service_products_code_id
                        )
                        for li in lines:
                            # if li.paid_visit_count:
                            li.paid_visit_count += 1

                rec.contract_already_updated = True

    # @api.depends('contract_id.contract_line_ids.actual_corrective',
    #              'contract_id.contract_line_ids.actual_preventive')
    @api.depends("contract_id", "asset_id", "service_products_code_id")
    def _compute_paid_service_editable(self):
        for rec in self:
            rec.paid_service_editable = False
            line = rec.contract_id.contract_line_ids.filtered(
                lambda l: l.product_id == rec.service_products_code_id
            )
            if not line:
                continue
            li = line[0]
            # CORRECTIVE
            if rec.maintenance_type == "corrective":
                if li.actual_correct_count == li.no_of_emergency_visit:
                    rec.paid_service_editable = True
            # PREVENTIVE
            if rec.maintenance_type == "preventive":
                if li.actual_prevent_count == li.days_require_rpm_round_off:
                    rec.paid_service_editable = True

    @api.constrains("paid_service_bool", "contract_id", "service_products_code_id")
    def _check_corrective_paid_service(self):
        for rec in self:
            line = rec.contract_id.contract_line_ids.filtered(
                lambda l: l.product_id == rec.service_products_code_id
            )
            if not line:
                continue

            li = line[0]

            # If corrective is fully used and user still didn't tick paid
            if rec.maintenance_type == "corrective":
                if li.actual_correct_count == li.no_of_emergency_visit:
                    if not rec.paid_service_bool:
                        raise ValidationError(
                            _(
                                "Corrective visits are fully used. Please enable Paid Service."
                            )
                        )
            if rec.maintenance_type == "preventive":
                pass
                '''Code Commented on May 22 2026 by Vijaya Bhaskar meanwhile becasue when i create the service request from Maintenance equipment it will raise error'''
                # if li.actual_prevent_count == li.days_require_rpm_round_off:
                #     if not rec.paid_service_bool:
                #         raise ValidationError(
                #             _(
                #                 "Preventive visits are fully used. Please enable Paid Service."
                #             )
                #         )

    @api.onchange("asset_id")
    def _onchange_service_products_code_id(self):
        for rec in self:
            rec.service_products_code_id = (
                rec.asset_id.service_products_code_id or False
            )
            rec.model = rec.asset_id.model_id.model_code or False
            rec.brand = rec.asset_id.brand_id.name or False
            rec.product_slno = rec.asset_id.serial_no or False
            rec.nature_of_service_id = (
                self.env["service.nature"].search([("code", "=", "001")], limit=1).id
            )
            '''Code Added on May 21 2026 by Vijaya Bhaskar'''
            rec.product_category = rec.asset_id.brand_id.amc_product_category_id.id or False
            '''Code Added on May 23 2026 by Vijaya Bhaskar'''
            rec.used_location_equipment = rec.asset_id.location or False
            rec.product_id = rec.asset_id.service_products_code_id.id or False

    @api.onchange("contract_id")
    def _update_related_data_subscription(self):
        for rec in self:
            if rec.contract_id:
                rec.contract_date = rec.contract_id.date_start or None
                rec.contract_expiry_date = rec.contract_id.date_end or None

    ###################################### Contract Changes End #######################################

    @api.constrains("symptom_line_ids")
    def _check_symptom_lines(self):
        """Code is added on Sep-09-2025 by Vijaya Bhaskar skip the validation by create the duplicate job card"""

        if self.env.context.get("skip_state_validation"):
            return False
        for rec in self:
            for line in rec.symptom_line_ids:
                if not line.sym_id:
                    raise ValidationError(
                        "Each Symptom line must have selected if you clicked"
                    )

                    # job_card_create_bool = fields.Boolean(string = "Job card create", default = False , compute ="_compute_" )

    ## Commented by Raj 21-03-26 - reason hhs live this code is commented
    # @api.constrains('symptom_line_ids', 'problem')
    # def _check_symptom_line_ids(self):
    #     '''Code is added on Sep-09-2025 by Vijaya Bhaskar skip the validation by create the duplicate job card'''
    #     if self.env.context.get('skip_state_validation'):
    #         return False
    #     for rec in self:
    #         if not rec.symptom_line_ids and not rec.problem:
    #             raise ValidationError("Please Enter at-least one line at the Symptoms or Complaint Details")

    @api.onchange("warranty")
    # @api.depends('purchase_date','product_category','product_category.warranty_period_combo','product_category.warranty_period')
    def __onchange_warranty(self):
        for rec in self:
            rec.website_year = False
            if rec.warranty:
                if rec.purchase_date and rec.product_category:
                    if (
                        rec.product_category.warranty_period
                        and rec.product_category.warranty_period_combo
                    ):
                        if rec.product_category.warranty_period_combo == "years":
                            rec.website_year = rec.purchase_date + relativedelta(
                                years=rec.product_category.warranty_period
                            )
                        elif rec.product_category.warranty_period_combo == "months":
                            rec.website_year = rec.purchase_date + relativedelta(
                                months=rec.product_category.warranty_period
                            )
                        elif rec.product_category.warranty_period_combo == "days":
                            rec.website_year = rec.purchase_date + relativedelta(
                                days=rec.product_category.warranty_period
                            )

            # if rec.website_year:
            #     if rec.website_year >= rec.request_date:
            #         rec.warranty = True
            #

    # @api.onchange('product_category')
    # def _onchange_product_category(self):
    #     for rec in self:
    #         # rec.product_id = False
    #         if rec.product_category:
    #             rec.nature_of_service_id = rec.product_category.def_servicetypeid.id or False

    @api.onchange("product_category")
    def _onchange_product_category(self):
        for rec in self:
            # rec.product_id = False
            if rec.product_category:
                rec.nature_of_service_id = (
                    rec.product_category.def_servicetypeid.id or False
                )
            """Code Added on Mar 16 2026 client asked to clear the concerned category"""
            if rec._origin and rec.product_category == rec._origin.product_category:
                return
            '''Code Added on May 23 2026 by Vijaya Bhaskar'''
            if not rec.project_related_amc_bool:
                rec.product_group_id = False
                rec.product_sub_group_id = False
                rec.product_id = False
                rec.product_slno = False
                rec.product_id = False
                rec.year = False
                rec.symptom_line_ids = [(5, 0, 0)]

    """Code Added on Mar 16 2026 client asked to clear the concerned category"""

    @api.onchange("product_group_id")
    def _onchange_product_group_id(self):
        for rec in self:
            if not rec.product_group_id:
                continue

            if rec._origin and rec.product_group_id == rec._origin.product_group_id:
                return

            '''Code Added on May 23 2026 by Vijaya Bhaskar'''
            if not rec.project_related_amc_bool:
                rec.product_sub_group_id = False
                rec.product_id = False
                rec.product_slno = False


    """Code Added on Mar 16 2026 client asked to clear the concerned category"""

    @api.onchange("product_sub_group_id")
    def _onchange_product_sub_group_id(self):
        for rec in self:
            if not rec.product_sub_group_id:
                continue
            if (
                rec._origin
                and rec.product_sub_group_id == rec._origin.product_sub_group_id
            ):
                return
            
            '''Code Added on May 23 2026 by Vijaya Bhaskar'''
            if not rec.project_related_amc_bool:
                rec.product_id = False
                rec.product_slno = False
                
    @api.onchange("partner_id")
    def onchange_partner_id(self):
        for rec in self:
            if rec.partner_id:
                if rec.partner_id.blocked_customer and rec.partner_id.blocked_reason:
                    # return {
                    #     'warning': {
                    #         'title': "Blocked Customer Alert",
                    #         'message': f"{rec.partner_id.name} is a blocked customer.Reason: {rec.partner_id.blocked_reason}. Selection reverted."
                    #     }
                    # }
                    raise ValidationError(
                        "%s is Blocked Customer.The reason is '%s'."
                        % (rec.partner_id.name, rec.partner_id.blocked_reason)
                    )
                elif rec.partner_id.blocked_customer:
                    raise ValidationError(
                        "%s is Blocked Customer." % rec.partner_id.name
                    )

                rec.email = rec.partner_id.email
                rec.phone = rec.partner_id.mobile

                address_parts = [
                    rec.partner_id.street or False,
                    rec.partner_id.street2 or False,
                    (
                        rec.partner_id.customer_city_id.name
                        if rec.partner_id.customer_city_id
                        else False
                    ),
                    rec.partner_id.state_id.name if rec.partner_id.state_id else False,
                    (
                        rec.partner_id.country_id.name
                        if rec.partner_id.state_id
                        else False
                    ),
                    rec.partner_id.zip or False,
                ]
                rec.address = ",".join(filter(None, address_parts))
                rec.work_location_id = (
                    rec.partner_id.customer_city_id.def_work_center_id.id or False
                )
                rec.partner_city = rec.partner_id.customer_city_id.name
                rec.work_center_group_id = (
                    rec.work_location_id.work_center_group_id.id or False
                )
                # rec.customer_city_id =
                if rec.phone:
                    try:
                        return rec.action_show_job_card()
                    except ValidationError:
                        pass
                        # If no job cards found, continue with normal onchange
                        # return {
                        #     'warning': {
                        #         'title': "No Job Cards Found",
                        #         'message': "No job cards found for this phone number."
                        #     }
                        # }
                # rec.address = rec.partner_id.street + "," + rec.partner_id.street2+"," + rec.partner_id.customer_city_id.name +","+\
                #                 rec.partner_id.state_id.name + ","+ rec.partner_id.country_id.name+ ","+ rec.partner_id.zip
                # rec.phone = rec.partner_id.phone

    # def read(self, fields=None, load='_classic_read'):
    #     res = super(MachineRepairSupport, self).read(fields, load)
    #     for rec in self:
    #         rec.action_show_job_card()
    #     return res
    mobile_number_bool = fields.Boolean(
        "Mobile Bool", default=False, compute="_compute_mobile_number_bool"
    )

    @api.depends("phone")
    def _compute_mobile_number_bool(self):
        for rec in self:
            rec.mobile_number_bool = False
            if rec.phone:
                rec.mobile_number_bool = True
                # if rec.mobile_number_bool:
                #     rec.action_show_job_card()

    @api.onchange("customer_city_id")
    def _onchange_customer_city_id(self):
        for rec in self:
            if rec.customer_city_id:
                service_request_search = self.env["machine.repair.support"].search(
                    [
                        ("phone", "=", rec.phone),
                        ("customer_name", "=", rec.customer_name),
                    ],
                    order="id Desc",
                    limit=1,
                )
                district_search_id = self.env["res.state.district"].search(
                    [("city_id", "=", rec.customer_city_id.id)], limit=1
                )
                rec.work_location_id = (
                    rec.customer_city_id.def_work_center_id.id or False
                )
                rec.country_district_id = (
                    service_request_search.country_district_id.id
                    if service_request_search
                    else district_search_id
                )
                # rec.country_district_id = rec.customer_city_id.country_district_id.id or False
                rec.country_state_id = rec.customer_city_id.state_id.id or False
                rec.country_id = rec.customer_city_id.country_id.id or False
                rec.zip_code = rec.customer_city_id.zipcode or False
                rec.work_center_group_id = (
                    rec.work_location_id.work_center_group_id.id or False
                )
                # rec.country_district_id = district_search_id or False

    # @api.onchange('customer_name')
    # def _onchange_customer_name(self):
    #     for rec in self:
    #         service_request_search = self.env['machine.repair.support'].search([('phone','=',rec.phone)],order ="id Desc", limit = 1)
    #
    #         if service_request_search:
    #             rec.email = service_request_search.email or False
    #             rec.address = service_request_search.address or False
    #             rec.address_one = service_request_search.address_one or False
    #             rec.address_two = service_request_search.address_two or False
    #             rec.customer_city_id = service_request_search.customer_city_id.id or False
    #             rec.country_district_id = service_request_search.country_district_id.id or False
    #             rec.country_state_id = service_request_search.country_state_id.id or None
    #             rec.country_id = service_request_search.country_id.id or False
    #             rec.zip_code = service_request_search.zip_code or False
    #             rec.work_location_id = service_request_search.customer_city_id.def_work_center_id.id or False
    #             rec.customer_identification_scheme = service_request_search.customer_identification_scheme or False
    #             rec.customer_identification_number = service_request_search.customer_identification_number or False
    #             rec.whatsapp_opt_in = service_request_search.whatsapp_opt_in or False
    #             rec.building_number = service_request_search.building_number or False
    #             rec.plot_identification = service_request_search.plot_identification or False
    #             rec.partner_latitude = service_request_search.partner_latitude or False
    #             rec.partner_longitude = service_request_search.partner_longitude or False
    #             rec.work_center_group_id = service_request_search.work_location_id.work_center_group_id.id or False
    #             rec.partner_id = service_request_search.partner_id.id or False
    #         else:
    #             rec.email = False
    #             rec.address = False
    #             rec.address_one = False
    #             rec.address_two = False
    #             rec.customer_city_id = False
    #             rec.country_district_id = False
    #             rec.country_state_id = None
    #             rec.country_id = False
    #             rec.zip_code = False
    #             rec.work_location_id = None
    #             rec.customer_identification_scheme = False
    #             rec.customer_identification_number = False
    #             rec.whatsapp_opt_in = False
    #             rec.building_number = False
    #             rec.plot_identification = False
    #             rec.partner_latitude = False
    #             rec.partner_longitude = False
    #             # rec.work_center_group_id = False

    """this code is added to get the contract from the customer code added on July 29 2025"""

    @api.onchange("partner_id")
    def onchange_partner_id_check(self):
        for rec in self:
            if rec.partner_id:
                rec.customer_name = rec.partner_id.name or None
                rec.address_one = rec.partner_id.street or None
                rec.address_two = rec.partner_id.street2 or None
                rec.customer_city_id = rec.partner_id.customer_city_id.id or None
                rec.customer_identification_scheme = (
                    rec.partner_id.additional_identification_scheme or None
                )
                rec.customer_identification_number = (
                    rec.partner_id.additional_identification_number
                    if rec.partner_id.additional_identification_scheme != "TIN"
                    else rec.partner_id.vat
                )
                rec.building_number = rec.partner_id.building_number or None
                rec.plot_identification = rec.partner_id.plot_identification or None
                rec.whatsapp_opt_in = rec.partner_id.x_whatsapp_opt_in or None
                rec.partner_latitude = rec.partner_id.partner_latitude or None
                rec.partner_longitude = rec.partner_id.partner_longitude or None

                # else:
            #     rec.email = False
            #     rec.address = False
            #     rec.address_one = False
            #     rec.address_two = False
            #     rec.customer_city_id = False
            #     rec.country_district_id = False
            #     rec.country_state_id = None
            #     rec.country_id = False
            #     rec.zip_code = False
            #     rec.work_location_id = None
            #     rec.customer_identification_scheme = False
            #     rec.customer_identification_number = False
            #     rec.whatsapp_opt_in = False
            #     rec.building_number = False
            #     rec.plot_identification = False
            #     rec.partner_latitude = False
            #     rec.partner_longitude = False

    @api.depends(
        "address_one",
        "address_two",
        "customer_city_id",
        "country_district_id",
        "country_state_id",
        "country_id",
        "zip_code",
    )
    def _compute_address(self):
        for rec in self:
            # rec.address = False
            address_parts = [
                rec.address_one or False,
                rec.address_two or False,
                rec.customer_city_id.name or False,
                rec.country_district_id.name or False,
                rec.country_state_id.name or False,
                rec.country_id.name or False,
                rec.zip_code or False,
            ]
            rec.address = ",".join(filter(None, address_parts))

    @api.constrains("phone")
    def _check_valid_phone_number(self):
        for rec in self:
            if rec.phone:
                # if len(rec.phone) < 10 or len(rec.phone) > 15:
                if len(rec.phone) != 10:
                    raise ValidationError(_("Mobile number must be 10 digits."))

    @api.constrains("email")
    def _check_email_validity(self):
        """Code is added on Sep-09-2025 by Vijaya Bhaskar skip the validation by create the duplicate job card"""
        if self.env.context.get("skip_state_validation"):
            return False
        for rec in self:
            if rec.email:
                if "@" not in rec.email or "." not in rec.email:
                    raise ValidationError(
                        "Please enter a valid email address must contain @ and ."
                    )
                if not re.match(
                    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", rec.email
                ):
                    raise ValidationError(
                        "Please enter a properly formatted email address"
                    )

    @api.constrains("customer_identification_number")
    def _valid_check_customer_identification_number(self):
        """Code is added on Sep-09-2025 by Vijaya Bhaskar skip the validation by create the duplicate job card"""
        if self.env.context.get("skip_state_validation"):
            return False
        for rec in self:
            if rec.customer_identification_scheme:
                if rec.customer_identification_number:
                    if not rec.customer_identification_number.isdigit():
                        raise ValidationError(
                            "Please enter Only Numbers in the identification Numbers"
                        )
                    if rec.customer_identification_scheme == "TIN":
                        if rec.customer_identification_number:
                            if len(rec.customer_identification_number) != 15:
                                raise ValidationError(
                                    "Tax identification number is only 15 numbers"
                                )
                    elif rec.customer_identification_scheme != "TIN":
                        if rec.customer_identification_number:
                            if len(rec.customer_identification_number) != 10:
                                raise ValidationError(
                                    "Identification number is only 10 numbers"
                                )

    def action_show_job_card(self):
        job_card_search = (
            self.env["project.task"]
            .sudo()
            .search(
                [
                    ("phone", "=", self.phone),
                    ("job_card_state_code", "not in", ("126", "124")),
                ]
            )
        )

        if job_card_search:
            return {
                "type": "ir.actions.act_window",
                "name": "Job Cards",
                "res_model": "project.task",
                "view_mode": "tree,form",
                "target": "new",
                "domain": [("id", "in", job_card_search.ids)],
                "views": [
                    (
                        self.env.ref(
                            "machine_repair_management.view_project_task_tree"
                        ).id,
                        "tree",
                    ),
                    (False, "form"),
                ],
                "context": {"create": False, "delete": False},
            }

    @api.onchange("product_category")
    def product_id_change(self):
        return {
            "domain": {
                "product_id": [
                    ("is_machine", "=", True),
                    ("categ_id", "=", self.product_category.id),
                ]
            }
        }

    @api.onchange("team_id")
    def team_id_change(self):
        for rec in self:
            rec.team_leader_id = rec.team_id.leader_id.id

    def show_machine_diagnosys_task(self):
        for rec in self:
            res = self.env.ref("machine_repair_management.action_view_task_diagnosis")
            res = res.sudo().read()[0]
            res["domain"] = str(
                [("task_type", "=", "diagnosys"), ("machine_ticket_id", "=", rec.id)]
            )
            res["context"] = {
                "default_machine_ticket_id": rec.id,
                "default_task_type": "diagnosys",
            }
        return res

    def show_work_order_task(self):
        self.ensure_one()
        task = self.env["project.task"].search(
            [("service_request_id", "=", self.id)], limit=1
        )
        if task:
            return {
                "type": "ir.actions.act_window",
                "name": "Job Card",
                "res_model": "project.task",
                "res_id": task.id,  # Opens the form view of this specific record
                "view_mode": "form",
                "target": "current",
            }
        else:
            return {
                "type": "ir.actions.act_window",
                "name": "Job Card",
                "res_model": "project.task",
                "view_mode": "tree,form",
                "domain": [("service_request_id", "=", self.id)],
                "target": "current",
            }

    request_created_date = fields.Date(
        string="Call Date", compute="_compute_request_date_time", store=True
    )

    request_created_time = fields.Char(
        string="Call Time", compute="_compute_request_date_time", store=True
    )

    @api.depends("request_date")
    def _compute_request_date_time(self):
        for record in self:
            if record.request_date:
                user_tz = self.env.user.tz or "UTC"
                user_timezone = pytz.timezone(user_tz)
                localized_dt = pytz.utc.localize(record.request_date).astimezone(
                    user_timezone
                )

                record.request_created_date = localized_dt.date()
                record.request_created_time = localized_dt.strftime("%H:%M:%S")
            # if record.request_date:
            #     record.request_created_date = record.request_date.date()
            #     record.request_created_time = record.request_date.strftime('%H:%M:%S')

    appt_created_date = fields.Date(
        string="Actual App Date", compute="_compute_appoint_date_time", store=True
    )
    appt_created_time = fields.Char(
        string="Actual App Time", compute="_compute_appoint_date_time", store=True
    )

    service_request_appt_date = fields.Date(
        string="Service Req.Appt.Date",
        store=True,
        compute="_compute_service_request_date",
    )

    service_request_appt_time = fields.Char(
        string="Service Req.Appt Time",
        store=True,
        compute="_compute_service_request_date",
    )

    @api.depends("call_request_appointment_date")
    def _compute_service_request_date(self):
        for rec in self:
            rec.service_request_appt_date = False
            rec.service_request_appt_time = False
            if rec.call_request_appointment_date:
                user_tz = self.env.user.tz or "UTC"
                user_timezone = pytz.timezone(user_tz)
                local_timezone = pytz.utc.localize(
                    rec.call_request_appointment_date
                ).astimezone(user_timezone)
                rec.service_request_appt_date = local_timezone.date()
                rec.service_request_appt_time = local_timezone.strftime("%H:%M:%S")

    @api.depends("technician_appointment_date")
    def _compute_appoint_date_time(self):
        for record in self:
            # if record.request_date:
            record.appt_created_date = False
            record.appt_created_time = False
            if record.technician_appointment_date:
                user_tz = self.env.user.tz or "UTC"
                user_timezone = pytz.timezone(user_tz)
                local_timezone = pytz.utc.localize(
                    record.technician_appointment_date
                ).astimezone(user_timezone)
                record.appt_created_date = local_timezone.date()
                record.appt_created_time = local_timezone.strftime("%H:%M:%S")

                # record.appt_created_date = record.call_request_appointment_date.strftime("%d-%m-%Y")
                # record.appt_created_time = record.call_request_appointment_date.strftime('%H:%M:%S')

    cic_ref_no = fields.Char(string="CIC Ref No")
    work_order_no = fields.Char(string="Work order no")
    district = fields.Char(string="District")

    """Code added on March 17 2026"""
    type_of_property = fields.Selection(
        [("commercial", "Commercial"), ("residential", "Residential")],
        string="Type of Property",
    )
    property_type_maintenance_details_id = fields.Many2one(
        "property.type.maintenance.details", string="Function"
    )
    company_preventive_maintenance_bool = fields.Boolean(
        string="Any company currently performing preventive maintenance at the site ?",
        default=False,
    )
    company_preventive_maintenance = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Any company currently performing preventive maintenance at the site ?",
        default=False,
    )

    # @api.constrains('call_request_appointment_date', 'technician_appointment_date')
    # def _check_call_request_appointment(self):
    #     for rec in self:
    #         if rec.call_request_appointment_date and rec.request_date:
    #             if rec.call_request_appointment_date < rec.request_date:
    #                 raise ValidationError("Service Requested  Appt Date & Time is always greater than create Date")
    #         if rec.technician_appointment_date and rec.request_date:
    #             if rec.technician_appointment_date < rec.request_date:
    #                 raise ValidationError('Actual Appt Date & Time is always greater than create Date')
    #         if rec.technician_appointment_date and rec.call_request_appointment_date:
    #             if rec.technician_appointment_date <  rec.call_request_appointment_date:
    #                 raise ValidationError("Actual Appt Date & Time is always greater than Service Requested Appt Date & Time")

    """Code Added on Feb 25 2026"""

    def service_request_job_card_report(self):
        self.ensure_one()
        job_lst = []
        product_lines = []
        total_amt_lst = []
        total_extended_price = 0.00
        total_vat_amt = 0.00
        extended_price = 0.00
        grand_total = 0.00
        total = 0.00
        amount_words = False
        job_lst_symptoms = []
        job_lst_defects = []
        job_lst_services = []

        for job in self.task_id.symptoms_line_ids:
            vals = {
                "symptoms_id": job.code.sym_desc,
            }
            job_lst_symptoms.append(vals)
        for job in self.task_id.defects_type_ids:
            vals = {
                "defects_id": job.code.def_desc,
            }
            job_lst_defects.append(vals)
        for job in self.task_id.service_type_ids:
            vals = {
                "services_id": job.code.name,
            }
            job_lst_services.append(vals)
        for job in self.task_id:
            signature_data = None
            if job.signature:
                try:
                    # If it's already a string, use it directly
                    if isinstance(job.signature, str):
                        signature_data = job.signature
                    # If it's bytes, decode it
                    elif isinstance(job.signature, bytes):
                        signature_data = job.signature.decode("utf-8")
                    else:
                        # Try to convert to string
                        signature_data = str(job.signature)
                except Exception as e:
                    _logger.warning("Failed to process signature: %s", str(e))
                    signature_data = None

            local_app_start_time = False
            local_closed_date_time = False
            user_tz = self.env.user.tz or "UTC"
            user_timezone = pytz.timezone(user_tz)
            local_service_created_datetime = pytz.utc.localize(
                job.service_created_datetime
            ).astimezone(user_timezone)
            if job.planned_date_begin:
                local_app_start_time = pytz.utc.localize(
                    job.planned_date_begin
                ).astimezone(user_timezone)
            if job.closed_datetime:
                local_closed_date_time = pytz.utc.localize(
                    job.closed_datetime
                ).astimezone(user_timezone)

            vals = {
                "warehouse_id": job.warehouse_id.name,
                "cic_ref_no": job.control_card_no,
                "partner_id": job.partner_id.name,
                "customer_name": job.customer_name or "",
                "address": job.address_one or "",
                "vat": job.partner_id.vat,
                "job_card_no": job.name,
                "engineer_comments": (
                    job.engineer_comments
                    if job.job_card_state_code != "117" and job.engineer_comments
                    else (
                        f"Unit Pull Out - {job.engineer_comments}"
                        if job.engineer_comments
                        else None
                    )
                ),
                # 'service_created_date': job.service_created_datetime.strftime(
                #     "%d-%m-%Y %H:%M:%S") if job.service_created_datetime else None,
                "service_created_date": (
                    local_service_created_datetime.strftime("%d-%m-%Y %H:%M:%S")
                    if job.service_created_datetime
                    else None
                ),
                "completed_date_time": (
                    job.closed_datetime.strftime("%d-%m-%Y %H:%M:%S")
                    if job.closed_datetime
                    else None
                ),
                "model_no": job.product_id.default_code or None,
                "serial_no": job.product_slno or None,
                "technician_name": job.technician_id.name,
                "company_vat": self.env.company.vat,
                # 'signature': job.signature,
                "services_warranty": job.service_warranty_id.name,
                "dealer_name": job.dealer_id.name,
                "invoice_no": job.purchase_invoice_no,
                "invoice_date": (
                    job.purchase_date.strftime("%d-%m-%Y")
                    if job.purchase_date
                    else None
                ),
                "technician_first_visit": job.technician_first_visit_id.name or None,
                "first_visit_date": (
                    job.technician_first_visit_date.strftime("%d-%m-%Y")
                    if job.technician_first_visit_date
                    else None
                ),
                "first_vist_time_in": (
                    job.technician_first_intime if job.technician_first_intime else None
                ),
                "first_vist_time_out": (
                    job.technician_first_outtime
                    if job.technician_first_outtime
                    else None
                ),
                "technician_second_visit": (
                    job.technician_second_visit_id.name
                    if job.technician_second_visit_id
                    else None
                ),
                "second_visit_date": (
                    job.technician_second_visit_date.strftime("%d-%m-%Y")
                    if job.technician_second_visit_date
                    else None
                ),
                "second_visit_time_in": (
                    job.technician_second_intime
                    if job.technician_second_intime
                    else None
                ),
                "second_visit_time_out": (
                    job.technician_second_outtime
                    if job.technician_second_outtime
                    else None
                ),
                "customer_mob_no": job.phone,
                "customer_VAT_no": job.customer_identification_number or "",
                "engineer_comments_second": job.engineer_comments_second or "",
                "promised_date_time": (
                    local_closed_date_time.strftime("%d-%m-%Y %H:%M:%S")
                    if job.closed_datetime
                    else None
                ),
                "second_visit_technician_bool": job.second_visit_technician_bool,
                "client_comments": job.client_comments if job.client_comments else None,
                "volt": job.volt,
                "ampere": job.ampere,
                "lp": job.lp,
                "hp": job.hp,
                "sat": job.sat,
                "rat": job.rat,
                "length": job.length,
                "width": job.width,
                "area": job.area,
                "p_length": job.p_length,
                "work_center_id": (
                    job.work_center_id.name if job.work_center_id else None
                ),
                "signature": signature_data,
                "closed_date_time": (
                    local_closed_date_time.strftime("%d-%m-%Y %H:%M:%S")
                    if job.closed_datetime
                    else None
                ),
                # Add this line
            }
            job_lst.append(vals)

        for product in self.task_id.product_line_ids:
            extended_price = product.price_unit
            total = product.total
            # total = extended_price + product.tax_amount

            product_vals = {
                "stock_group": product.product_id.product_category_id.code,
                "stock_number": product.product_id.default_code,
                "description": product.product_id.name,
                "qty": product.qty,
                "unit_price": product.price_unit,
                "unit_discount": "",
                "net_unit_price": product.price_unit,
                "extended_price": extended_price,
                "vat_percent": product.vat if not product.under_warranty_bool else 0.00,
                "vat_amount": (
                    product.tax_amount if not product.under_warranty_bool else 0.00
                ),
                "total": product.total if not product.under_warranty_bool else 0.00,
            }
            product_lines.append(product_vals)
            total_extended_price += extended_price
            total_vat_amt += product.tax_amount
            grand_total += total
            amount_words = num2words(grand_total, to="currency", lang="ar")
            trans = Translator(from_lang="ar", to_lang="en")
            amount_words = trans.translate(amount_words)
        total_vals = {
            "total_extended_price": total_extended_price,
            "total_vat_amt": total_vat_amt,
            "grand_total": grand_total,
            "amount_words": amount_words,
        }
        total_amt_lst.append(total_vals)
        # if not product_lines:
        #     raise ValidationError("Product Consume Part/Service tab not in products")

        datas = {
            "service_jobs": job_lst,
            "symptoms": job_lst_symptoms,
            "defects": job_lst_defects,
            "services": job_lst_services,
            "product_lines": product_lines,
            "totals": total_amt_lst,
            "form_data": self.read()[0],
            # 'name':self.name,
            # 'signature_sign':self.signature,
            # 'signature':self.signature,
        }

        return self.env.ref(
            "machine_repair_management.service_request_job_card_report"
        ).report_action(self, data=datas)

    """ Need to check 
    @api.constrains('team_id', 'task_id')
    def _check_technician_conflict(self):
        for rec in self:

           # Get user's timezone
           user_tz = self.env.user.tz or 'UTC'
           tz = pytz.timezone(user_tz)



           local_timezone = pytz.utc.localize(rec.request_date).astimezone(tz)
           # Get current time in user's local timezone
           now_local = fields.Datetime.context_timestamp(rec, fields.Datetime.now())
           print(".............local",now_local,rec.user_id.name,rec.task_id.name)
           # Convert back to UTC for comparison with UTC stored fields
           now_utc = now_local.astimezone(pytz.utc).replace(tzinfo=None)
           print(".............time",now_utc,local_timezone)

           # Search for active overlapping tasks in UTC
           conflicting_tasks = self.env['project.task'].search([
               ('technician_id', '=', rec.user_id.id),
               ('id', '!=', rec.task_id.id),
                # ('planned_date_begin', '<=', local_timezone),
                #     ('planned_date_end', '>=', local_timezone),

               ('job_card_state_code', 'not in', ('126','124')),
           ])
           for conf in conflicting_tasks:
               planned = pytz.utc.localize(conf.planned_date_begin).astimezone(tz) 
               late = pytz.utc.localize(conf.planned_date_end).astimezone(tz) 
               if planned < local_timezone and  late > local_timezone:
                   print(".......conf",conf.technician_id.name,conf.planned_date_begin,conf.planned_date_end.conf.name)

           if conflicting_tasks:
               task_names = ', '.join(conflicting_tasks.mapped('name'))
               raise ValidationError(_(
                   "Technician %s is already assigned to the following task(s) at this time (your local time: %s):\n%s"
               ) % (rec.user_id.name, user_tz, task_names))
    """
    # @api.constrains('partner_id')
    # def _check_partner_id_blocked_customer(self):
    #     for rec in self:
    #         if rec.partner_id:
    #             if rec.partner_id.blocked_customer:
    #                 raise ValidationError("%s is Blocked Customer.So Don't Service Him/Her" % rec.partner_id.name)

    """code added on Nov 19 2025"""
    amc_project_id = fields.Many2one(
        "project.project",
        string="Project",
    )

    project_related_amc_bool = fields.Boolean(
        string="Project AMC (Y/N)",
        default=False,
        compute="_compute_project_related_amc_bool",
        store=True,
    )

    """Code Added on March 23 2026 by Vijaya Bhaskar"""
    service_group_batch = fields.Char(
        string="Service Group Batch", help="Maintenance Equipment Group Batch"
    )
    
    '''Code Added on Mar 26 2026 by Vijaya Bhaskar'''
    maintenance_contract_type_id = fields.Many2one('crm.contract.type', string = "Maintenance Contract Type")
    
    service_create_from_equipment_bool = fields.Boolean(string = 'Service Create Equipment bool', default = False)
    

    @api.depends("amc_project_id")
    def _compute_project_related_amc_bool(self):
        for rec in self:
            rec.project_related_amc_bool = False
            if rec.amc_project_id:
                if rec.amc_project_id.related_to_amc:
                    rec.project_related_amc_bool = True

    paid_service_amount = fields.Float(
        string="Paid Service Amount", compute="_compute_paid_service_amount", store=True
    )

    @api.depends(
        "paid_service_bool", "contract_id", "contract_id.add_paid_service_price"
    )
    def _compute_paid_service_amount(self):
        for rec in self:
            rec.paid_service_amount = False
            if rec.paid_service_bool and rec.contract_id.add_paid_service_price > 0.0:
                rec.paid_service_amount = rec.contract_id.add_paid_service_price


class HrTimesheetSheet(models.Model):
    _inherit = "account.analytic.line"

    #     support_request_id = fields.Many2one(
    #         'machine.repair.support',
    #         domain=[('is_close','=',False)],
    #         string='Machine Repair Support',
    #     )
    billable = fields.Boolean(
        string="Chargable?",
        default=True,
    )


class View(models.Model):
    _inherit = "ir.ui.view"
    # _inherit = ["ir.ui.view", "website.seo.metadata"]

    visibility = fields.Selection(default="connected")
