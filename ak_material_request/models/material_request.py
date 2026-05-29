# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software PVT. LTD.
# See LICENSE file for full copyright & licensing details.

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import warnings, UserError, ValidationError


class MaterialRequest(models.Model):
    _name = "material.request"
    _description = "Material Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    def compute_delivery_state(self):
        for material_request in self:
            picking_recs = self.env["stock.picking"].search(
                [("request_id", "=", material_request.id)]
            )
            if picking_recs and all(
                picking.state in ["done", "cancel"] for picking in picking_recs
            ):
                material_request.delivery_state = "process"
            else:
                material_request.delivery_state = "pending"


    @api.model
    def _default_dest_location_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids.lot_stock_id

    @api.model
    def _default_need_picking_operation(self):
        # company = self.env.user.company_id.id
        user_operation = self.env.user.property_warehouse_id.int_type_id.id
        # warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return user_operation
    
   
    

    name = fields.Char(
        string="Reference",
        index=True,
        readonly=1,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirmed"),
            ("approve", "Approved"),
            ("reject", "Rejected"),
        ],
        track_visibility="onchange",
        default="draft",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user and self.env.user.id or False,
        required=True,
        domain=lambda self: [
            ("groups_id", "in", [self.env.ref("stock.group_stock_user").id])
        ],
    )
   
    location_id = fields.Many2one(
        "stock.location",
        string="Stock For Branch",
        copy=True,
        help="Stock needed on Location.",
    
    ) 
    dest_location_id = fields.Many2one(
        "stock.location",
        string="Stock From Branch",
        copy=False,
        help="Location from where stock will be delivered.",
        default=_default_dest_location_id
    )
    request_date = fields.Datetime(string="Request Date", default=fields.Datetime.now())
    request_line_ids = fields.One2many(
        "material.request.line", "request_id", string="Request", copy=True,store=True
    )
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Operation Type",
        copy=False,
        default=lambda self: self.env["stock.picking.type"].search(
            [("code", "=", "internal")], limit=1
        ),
    )
    needed_picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Requesting Operation Type",
        copy=False,
        domain="[('code','=','internal')]",
        default=_default_need_picking_operation

    )
    two_verify = fields.Boolean(string="2 Step Delivery(Via Transit Location)",default=True)
    delivery_state = fields.Selection(
        [("pending", "Transfer Pending"), ("process", "No Pending Transfers")],
        track_visibility="onchange",
        default="pending",
        compute="compute_delivery_state",
    )
    good_needed_on = fields.Datetime(
        string="Goods Needed On",
    )
    # picking_count = fields.Integer(string="Picking Count", compute="compute_picking")
    picking_two_verify = fields.Boolean(string="Picking Two Verify")
    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.company
    )
    approved_user_id = fields.Many2one("res.users", copy=False, string="Approved By",required="1",
                                          domain=lambda self: [("groups_id", "=",self.env.ref("stock.group_stock_manager").id)])
    request_picking_type = fields.Selection([
        ('stock_request', 'Stock Request Type')
    ], string='Internal Picking Type', default='stock_request')

    # @api.model
    # def search(self, args, offset=0, limit=None, order=None, count=False):
    #     # Filter the search results to only include records created by the current user
    #     if self.env.user and not self.env.user.has_group('base.group_system'):
    #         args += [('create_uid', '=', self.env.user.id)]
    #     return super(MaterialRequest, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        if self.env.user:
            if self.env.user.has_group('stock.group_stock_manager'):
                args += [('approved_user_id', '=', self.env.user.id)]
                return super(MaterialRequest, self).search(args, offset=offset, limit=limit, order=order)
            elif self.env.user.has_group('stock.group_stock_user'):
                # If the user is a stock user, filter records by create_uid (current user)
                args += [('create_uid', '=', self.env.user.id)]
                return super(MaterialRequest, self).search(args, offset=offset, limit=limit, order=order)

    @api.constrains("dest_location_id")
    def check_dest_location(self):
        for material_req_rec in self:
            if material_req_rec.dest_location_id.id == material_req_rec.location_id.id:
                raise ValidationError(_("Please update Deliver Stock From Location."))

    # def compute_picking(self):
    #     """These method is used for counting the
    #     Internal Transfer which is created from the material request."""
    #     for material_request_rec in self:
    #         # if self.user_id:
    #         #     print(".......self...",self.user_id.sel_groups_1_9_10)
    #         material_request_rec.picking_count = self.env["stock.picking"].search_count(
    #             [("request_id", "=", material_request_rec.id)]
    #         )

    def action_reset_draft(self):
        for rec in self:
            rec.write({"state": "draft"})

    @api.onchange("company_id")
    def _onchange_2_step_delivery(self):
        for rec in self:
            if rec.company_id.two_step_material_req:
                rec.picking_two_verify = True
    
    
    @api.onchange('user_id')
    def _onchange_user_location(self):
        for rec in self:
            rec.location_id = rec.user_id.property_warehouse_id.lot_stock_id
            stock_manager = self.env['res.users'].search([('id','!=',self.user_id.id)])
            lst_name=[]
            for stock in stock_manager:
                group_stock_manager = stock.has_group('stock.group_stock_manager')
                if group_stock_manager == True and (self.user_id != stock):
                    lst_name.append(stock.id)
                    self.write({'approved_user_id': lst_name})
                   
                 
                    
            # rec.approved_user_id = 
            
            # user_nam = self.env['res.users'].search([('id','=',self.user_id.id)],limit=1)
            # desired_user_gr = user_nam.has_group('base.group_user')
            # print("///////",desired_user_gr)
            # if desired_user_gr:
            #
            #     print("..........group..",user_nam.name)
            # if user_nam:
                # for group in user.groups_id:
                #     if group.id==145:
                #         print(".......self...",group.name,group.id)
                #


    @api.onchange('picking_type_id')
    def _onchange_picking_type(self):
        for rec in self:
            rec.dest_location_id = rec.picking_type_id.warehouse_id.lot_stock_id
            return{'domain':{'dest_location_id':[('id','=',rec.picking_type_id.warehouse_id.lot_stock_id.id)]}}

    @api.onchange('needed_picking_type_id')
    def _onchange_needed_picking_type(self):
        for rec in self:
            rec.location_id = rec.user_id.property_warehouse_id.lot_stock_id
            # rec.location_id = rec.needed_picking_type_id.warehouse_id.lot_stock_id
            return {'domain': {'needed_picking_type_id': [('id', '=', rec.user_id.property_warehouse_id.int_type_id.id)],'location_id':[('id', '=', rec.user_id.property_warehouse_id.lot_stock_id.id)]}}
    
    ###### User Send request to Admin
    def action_send_mail(self):
        self.env.ref('ak_material_request.mail_template_transfer_request').send_mail(self.id,force_send=True)
        return {'effect':{'fadeout':'slow','message':'Your email is send successfully','type':'rainbow_man'}}

    ##### Admin Send the Response to User 
    def action_response_mail(self):
        self.env.ref('ak_material_request.mail_response_template_to_user').send_mail(self.id,force_send=True)
        return {'effect':{'fadeout':'slow','message':'Your email is send successfully','type':'rainbow_man'}}
        
    ### Stock Admin Reject the user request
    def action_reject_mail(self):
        self.env.ref('ak_material_request.mail_reject_template_to_user').send_mail(self.id,force_send=True)
        return {'effect':{'fadeout':'slow','message':'Your email is send successfully','type':'rainbow_man'}}
        
           
    def action_confirm(self):
        for rec in self:
            if not rec.request_line_ids:
                raise ValidationError("Please Enter at-least one Product in the Material Line")
            self.action_send_mail()
            rec.write({"state": "confirm"})

    def _prepare_pick_vals(self, req_line=False, picking=False):
        """This method is used to create stock moves from picking."""
        pick_vals = {
            "product_id": req_line.product_id.id,
            "product_uom_qty": req_line.qty,
            "product_uom": req_line.uom_id.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "picking_type_id": picking.picking_type_id.id,
            "picking_id": picking.id,
            "name": req_line.product_id.display_name,
            # 'order_qty': req_line.qty,
            'on_hand_quantity': req_line.on_hand_qty,
            'analytic_distribution':req_line.request_id.user_id.property_warehouse_id.analytic_id.id
        }
        return pick_vals

    def action_approve(self):
        """This method is used to create Internal Transfer."""
        pick_list_st = []
        pick_list_td = []
        stock_move_obj = self.env["stock.move"]
        for material_req_rec in self:
            if not material_req_rec.dest_location_id:
                raise warnings.warn(
                    _(
                        "Please select the location from which you want to transfer the Stock."
                    )
                )

            if not material_req_rec.request_line_ids:
                raise warnings.warn(_("Please create some requisition lines."))

            scheduled_date = False
            picking_vals = {
                "picking_type_id": material_req_rec.picking_type_id.id,
                "request_id": material_req_rec.id,
                "origin": material_req_rec.name,
                "internal_picking_type": material_req_rec.request_picking_type,
                "location_id": material_req_rec.dest_location_id.id,
                "partner_id": material_req_rec.user_id.partner_id.id,
            }
            if material_req_rec.two_verify:
                # Picking create for two step.
                transit_location = self.env["stock.location"].search(
                    [("usage", "=", "transit")], limit=1
                )
                if not transit_location:
                    return {
                        "type": "ir.actions.act_window",
                        "name": "No Transit Location Warning",
                        "view_mode": "form",
                        "res_model": "transit.location.warning",
                        "context": {
                            "default_name": "No active Transit Location found in the system. Please contact the Inventory manager to Unarchive the Transit Location."
                        },
                        "target": "new",
                    }
                picking_vals.update(
                    {
                        "location_dest_id": transit_location.id,
                    }

                )
            else:
                picking_vals.update(
                    {
                        "location_dest_id": material_req_rec.location_id.id,
                    }
                )

            # Created Main picking.
            main_picking_rec = self.env["stock.picking"].create(picking_vals)

            if material_req_rec.good_needed_on:
                scheduled_date = material_req_rec.good_needed_on

            if material_req_rec.two_verify:
                two_step_picking_rec = self.env["stock.picking"].create(
                    {
                        "location_id": transit_location.id,
                        "location_dest_id": material_req_rec.location_id.id,
                        "picking_type_id": material_req_rec.needed_picking_type_id.id,
                        "internal_picking_type":material_req_rec.request_picking_type,
                        "request_id": material_req_rec.id,
                        "origin": material_req_rec.name,
                        "partner_id": material_req_rec.user_id.partner_id.id,
                        "create_uid":material_req_rec.create_uid.id,
                        "request_user":material_req_rec.create_uid.id
                    }
                )

            for req_line in material_req_rec.request_line_ids:
                stock_move_vals = material_req_rec._prepare_pick_vals(
                    req_line, main_picking_rec
                )
                first_move_rec = stock_move_obj.create(stock_move_vals)
                main_picking_rec.action_confirm()
                if material_req_rec.two_verify:
                    two_verify_stock_move_vals = material_req_rec._prepare_pick_vals(
                        req_line, two_step_picking_rec
                    )
                    
                    two_verify_stock_move_vals.update(
                        {"move_orig_ids": [(6, 0, first_move_rec.ids)]}
                    )
                    stock_move_obj.create(two_verify_stock_move_vals)
                    two_step_picking_rec.action_confirm()
            self.action_response_mail()
            material_req_rec.write({"state": "approve"})

    def action_reject(self):
        action = self.env.ref(
            "ak_material_request.action_reject_material_request_wizard"
        ).read()[0]
        action["context"] = {"default_material_request_id": self.id}
        self.action_reject_mail()
        return action

    @api.model
    def create(self, vals):
        """sequence is created for material request."""
        name = self.env["ir.sequence"].next_by_code("material.request.seq")
        vals.update({"name": name})
        res = super(MaterialRequest, self).create(vals)
        return res

    # def show_picking(self):
    #     """Redirects to the stock picking view."""
    #     for rec in self:
    #         res = self.env.ref("stock.action_picking_tree_all")
    #         res = res.read()[0]
    #         res["domain"] = str([("request_id", "=", rec.id)])
    #     return res

    

    # def show_picking(self):
    #     """Redirects to the stock picking view."""
    #     for rec in self:
    #         picking_ids = self.env["stock.picking"].search(
    #             [("request_id", "=", rec.id)]
    #         ).ids
    #
    #         transit_location = self.env["stock.location"].search([("usage", "=", "transit")])
    #
    #         transit_picking_ids = self.env["stock.picking"].search([
    #             ("id", "in", picking_ids),
    #             ("location_id", "in", transit_location.ids),
    #         ]).ids
    #         if self.env.user.has_group('base.group_user'):
    #             domain = [("id", "in", picking_ids)]
    #
    #         elif self.env.user.has_group('base.group_portal'):
    #             domain = [("id", "in", transit_picking_ids)]
    #
    #         if not self.env.user.has_group('stock.group_stock_manager'):
    #             domain.append(("id", "not in", transit_picking_ids))
    #         res = self.env.ref("stock.action_picking_tree_all")
    #         res = res.read()[0]
    #         res["domain"] = str(domain)
    #     return res

    def show_picking(self):
        """Redirects to the stock picking view."""
        for rec in self:
            picking_ids = self.env["stock.picking"].search(
                [("request_id", "=", rec.id), ("location_id.usage", '=', 'internal')]
            ).ids

            transit_location = self.env["stock.location"].search([("usage", "=", "transit")])

            picking_new_ids = self.env["stock.picking"].search(
                [("request_id", "=", rec.id), ("location_id.usage", '=', 'transit')]
            ).ids

            transit_picking_ids = self.env["stock.picking"].search([
                ("id", "in", picking_new_ids),
                ("location_id", "in", transit_location.ids),
            ]).ids

            domain = []
            # if self.env.user.has_group('stock.group_stock_manager')and len(picking_ids) > 1:
            #     domain = [("id", "=", picking_ids[1])]

            if self.env.user.has_group('stock.group_stock_manager'):
                domain = [("id", "=", picking_ids)]

            elif self.env.user.has_group('stock.group_stock_user'):
                domain = [("id", "in", transit_picking_ids)]

            res = self.sudo().env.ref("stock.action_picking_tree_all")

            res = res.read()[0]
            res["domain"] = str(domain)
        return res

    def unlink(self):
        for rec in self:
            if rec.state not in ["draft", "reject"]:
                raise UserError(
                    _("This record can be deleted only in Draft or Rejected state.")
                )
        return super(MaterialRequest, self).unlink()
