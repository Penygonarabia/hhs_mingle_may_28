from odoo import models, fields, api
from odoo.exceptions import UserError , ValidationError
from datetime import datetime, timedelta, time, date
from dateutil.relativedelta import relativedelta
import re


class ServiceSaleOrder(models.Model):
    _inherit = "service.sale.order"


    is_revised = fields.Boolean(string="Is Revised", copy=False)
    org_sale_id = fields.Many2one("service.sale.order", string="Origin", copy=False)
    rev_sale_ids = fields.One2many(
        "service.sale.order",
        "org_sale_id",
        string="Sales Revisions",
        copy=False,
    )
    rev_ord_count = fields.Integer(
        string="Revised Orders",
        compute="_compute_rev_ord_count",
    )
    rev_confirm = fields.Boolean(string="Revised Confirm", copy=False)



    # @api.model
    # def create(self, vals):
    #     if vals.get("name", "New") in ["New", False]:
    #         seq = self.env["ir.sequence"].next_by_code("service.sale.order")
    #         vals["name"] = seq
    #
    #     if vals.get("org_sale_id") and vals.get("amc_quotation"):
    #         original = self.browse(vals["org_sale_id"])
    #
    #         base_ref = original.name.split("/R")[0]
    #         rev_no = len(original.rev_sale_ids) + 1
    #         vals["name"] = f"{base_ref}/R{rev_no}"
    #
    #     record = super(ServiceSaleOrder, self).create(vals)
    #
    #     return record

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if vals.get("name", "New") in ["New", False]:
    #             seq = self.env["ir.sequence"].next_by_code("service.sale.order")
    #             vals["name"] = seq
    #
    #         if vals.get("org_sale_id") and vals.get("amc_quotation"):
    #             original = self.browse(vals["org_sale_id"])
    #
    #             base_ref = original.name.split("/R")[0] if original and original.name else ""
    #             print("base_ref................", base_ref)
    #             rev_no = len(original.rev_sale_ids) + 1
    #             print("rev_no.....................", rev_no)
    #             vals["name"] = f"{base_ref}/R{rev_no}"
    #             print("vals............", vals)
    #     records = super().create(vals_list)
    #     return records
    #
    #
    #
    # def action_revise_quotation(self):
    #     self.ensure_one()
    #
    #     vals = {
    #         "org_sale_id": self.id,
    #         "state": "draft",
    #     }
    #
    #     revised = self.copy(default=vals)
    #     self.is_revised = True
    #     if revised.id:
    #         revised.state = 'draft'
    #         revised.whatsapp_button_click_bool = False
    #         # revised.approval_level_id = False
    #     return {
    #         "type": "ir.actions.act_window",
    #         "res_model": "service.sale.order",
    #         "view_mode": "form",
    #         "res_id": revised.id,
    #     }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (
                    self.env["ir.config_parameter"]
                            .sudo()
                            .get_param("machine_repair_management.sequence_creation_bool")
                    == "True"
            ):
                if vals.get("name", "New") in ["New", False]:
                    
                    # -------------------------------------------------
                    # Service Sale Order created from Job Card
                    # -------------------------------------------------
                    
                    '''Code Added on August 06 2026 by Vijaya Bhaskar from the Job card create a quotation'''
                    
                    if vals.get("job_task_id"):
                        vals["name"] = (
                            self.env["ir.sequence"].next_by_code("service.sale.order")
                            or "New"
                        )
    
                 
                    else:
                    
                        now = datetime.now()
                        current_month = now.month
                        current_year = now.year
                        year_str = now.strftime("%y")
                        month_str = now.strftime("%m")
    
                        # project_id = vals.get("project_id")
                        # amc_id = vals.get("amc_project_id")
                        # is_quotation = vals.get("is_quotation")
                        #
                        # if is_quotation:
                        #     sequence_code = "quotation.machine.repair.support"
                        # elif amc_id and amc_id != project_id:
                        #     sequence_code = "amc.machine.repair.support"
                        # else:
                        #     sequence_code = "machine.repair.support"
                        sequence_code = "quotation.machine.repair.support"
                        sequence = self.env["ir.sequence"].search(
                            [("code", "=", sequence_code)], limit=1
                        )
    
                        loc = "AMC-"
                        number = 1
                        crm_search = self.env['crm.lead'].search([('id', '=', vals.get('crm_id'))], limit=1)
                        location_id = crm_search.customer_city_id.def_work_center_id.id
                        if sequence and sequence.use_date_range and sequence.use_location_wise:
                            for date_range in sequence.date_range_ids:
                                if (
                                        date_range.date_from.year == current_year
                                        and date_range.work_center_id.id == location_id
                                ):
                                    loc = date_range.location_code
                                    number = date_range.number_next_actual
                                    date_range.number_next_actual += 1
                                    break
    
                            seq = f"{sequence.prefix}{loc}{year_str}{str(number).zfill(5)}"
    
                            if self.env["service.sale.order"].search([("name", "=", seq)], limit=1):
                                raise ValidationError(f"Sequence '{seq}' already exists.")
    
                            vals["name"] = seq
    
                        elif sequence and sequence.use_date_range:
                            for date_range in sequence.date_range_ids:
                                if (
                                        date_range.date_from.year == current_year
                                ):
                                    loc = date_range.location_code
                                    number = date_range.number_next_actual
                                    date_range.number_next_actual += 1
                                    break
    
                            seq = f"{sequence.prefix}{loc}{year_str}{str(number).zfill(5)}"
    
                            if self.env["service.sale.order"].search([("name", "=", seq)], limit=1):
                                raise ValidationError(f"Sequence '{seq}' already exists.")
    
                            vals["name"] = seq
    
                        else:
                            vals["name"] = (
                                    self.env["ir.sequence"].next_by_code(sequence_code)
                                    or "New"
                            )

        return super().create(vals_list)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         # Generate sequence for new base quotation
    #         if vals.get("name", "New") in ["New", False]:
    #             seq = self.env["ir.sequence"].next_by_code("service.sale.order")
    #             vals["name"] = seq
    #
    #         # Revision case
    #         if vals.get("org_sale_id") and vals.get("amc_quotation"):
    #             original = self.browse(vals["org_sale_id"])
    #
    #             # ✔️ Find the root document
    #             root = original
    #             while root.org_sale_id:
    #                 root = root.org_sale_id
    #
    #             base_ref = root.name.split("/R")[0]
    #             rev_no = len(root.rev_sale_ids) + 1  # Count all revisions from root
    #
    #             vals["name"] = f"{base_ref}/R{rev_no}"
    #
    #     return super().create(vals_list)

    def action_revise_quotation(self):
        self.ensure_one()

        # ✔️ Find root
        root = self
        while root.org_sale_id:
            root = root.org_sale_id
            
        '''Code Added on June 17 2026 by Vijaya bahskar for revision name is r1 is not added'''    
        revision_count = self.env['service.sale.order'].search_count([
        ('org_sale_id', '=', root.id),
        ])
        # revision_count = 1 means R1 already exists, so next is R2, etc.
        next_revision = revision_count + 1
    
        # 📝 Build the new name: strip any existing /RN suffix from root name, then append new suffix
        base_name = root.name
        
        base_name = re.sub(r'/R\d+$', '', base_name)  # safety: strip if root itself had one
        new_name = f"{base_name}/R{next_revision}"
    
        vals = {
            "org_sale_id": root.id,
            "state": "draft",
            "amc_quotation": True,
            "name": new_name,
        }    
            
        # vals = {
        #     "org_sale_id": root.id,
        #     "state": "draft",
        #     "amc_quotation": True,
        # }


        revised = self.copy(default=vals)
        self.is_revised = True

        revised.state = 'draft'
        revised.whatsapp_button_click_bool = False

        # 🔥 STEP 1 — CREATE CONTRACT (MANDATORY)
        # contract = self.env['subscription.contracts'].create({
        #     'amc_quotation_id': revised.id,
        # })

        # revised.contract_id = contract

        # 🔥 COPY PAYMENT TERMS (LIKE YOUR CONTRACT LOGIC)
        if self.quotation_payment_term_ids and not revised.quotation_payment_term_ids:

            schedule_vals = []
            for line in self.quotation_payment_term_ids:
                schedule_vals.append((0, 0, {
                    'sequence': line.sequence,
                    'name': line.name,
                    'name_arabic': line.name_arabic,
                    'payment_date': line.payment_date,
                    'amount': line.amount,
                    'state': line.state,
                }))

            revised.quotation_payment_term_ids = schedule_vals
            
        '''Code Added on July 29 2026 by Vijaya Bhaskar'''
        if self.pm_checklist_ids and not revised.pm_checklist_ids:
            
            checklist_vals = []
            
            for line in self.pm_checklist_ids:
                checklist_vals.append((0,0,{
                    
                    'service_unit_type_id' : line.service_unit_type_id.id or '',
                    'unit_sub_type_id' : line.unit_sub_type_id or '',
                    'service_type_id' : line.service_type_id or '',
                    'is_selected' : line.is_selected or '',
                    'print_always_default' : line.print_always_default or '',
                    
               
                    }))
                
            revised.pm_checklist_ids = checklist_vals    

        return {
            "type": "ir.actions.act_window",
            "res_model": "service.sale.order",
            "view_mode": "form",
            "res_id": revised.id,
        }

    @api.depends("rev_sale_ids")
    def _compute_rev_ord_count(self):
        for rec in self:
            rec.rev_ord_count = len(rec.rev_sale_ids)

    def get_revised_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Revised Orders",
            "res_model": "service.sale.order",
            "domain": [("org_sale_id", "=", self.id)],
            "view_mode": "tree,form",
            "context": {"create": False},
        }

    def unlink(self):
        for order in self:
            if order.rev_ord_count > 0:
                raise UserError(
                    "Cannot delete a service sale order that has revisions.\n"
                    "Delete revised orders first."
                )
        return super(ServiceSaleOrder, self).unlink()

    # def action_contract_creation(self):
    #     for order in self:
    #         if not order.rev_confirm:
    #             related_orders = order.get_related_orders()
    #
    #             related_orders = related_orders - order
    #             if related_orders:
    #                 wizard = self.env["service.sale.order.wizard"].create({
    #                     "order_id": order.id,
    #                     "sale_orders_ids": [(6, 0, related_orders.ids)],
    #                 })
    #                 return {
    #                     "name": "Confirm Related Sale Orders",
    #                     "type": "ir.actions.act_window",
    #                     "res_model": "service.sale.order.wizard",
    #                     "view_mode": "form",
    #                     "res_id": wizard.id,
    #                     "target": "new",
    #                 }
    #
    #     return super(ServiceSaleOrder, self).action_contract_creation()


    # def get_related_orders(self):
    #     """Return related sale orders still in draft"""
    #     related = self.rev_sale_ids.filtered(lambda r: r.state not in ["cancel", "sale"])
    #
    #     if self.org_sale_id and self.org_sale_id.state not in ["cancel", "sale"]:
    #         related |= self.org_sale_id
    #
    #     if self.org_sale_id:
    #         related |= self.org_sale_id.rev_sale_ids.filtered(
    #             lambda r: r.state not in ["cancel", "sale"]
    #         )
    #
    #     return related

    def get_related_orders(self):
        """Return all revisions of the same base order (including original),
        ordered with latest revisions first, excluding the current record."""
        self.ensure_one()

        # 1) Determine base name (original name without any /R... suffix)
        if self.org_sale_id and self.org_sale_id.name:
            base_name = self.org_sale_id.name.split("/R")[0]
        else:
            # If org_sale_id not set, derive from current name by splitting '/R'
            base_name = (self.name or "").split("/R")[0]

        # 2) Try to find the original/base order record by exact name match.
        base_order = self.search([("name", "=", base_name)], limit=1)
        if not base_order:
            # fallback: use self as base if original can't be found
            base_order = self

        # 3) Collect all orders that belong to this chain:
        #    - the base order itself
        #    - any order whose name starts with base_name (covers /R1, /R2, ...)
        domain = [("name", "ilike", base_name + "%"), ("company_id", "=", base_order.company_id.id)]
        related = self.search(domain)

        # 4) Exclude the current record
        related = related - self

        # 5) Sort by revision number (R#). Original (no /R) gets rev_no = 0.
        def _rev_no(rec):
            name = rec.name or ""
            if "/R" in name:
                try:
                    return int(name.split("/R")[1])
                except Exception:
                    return 0
            return 0

        related = related.sorted(key=_rev_no, reverse=True)  # latest revision first

        return related





