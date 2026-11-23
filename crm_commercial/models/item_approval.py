# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class CrmCommercialItemApproval(models.Model):
    _name = 'crm.commercial.item.approval'
    _description = 'Non-Stock Item Approval'
    _order = 'id desc'
    _rec_name = 'name'

    part_no = fields.Char(string='Part No *', required=True, index=True)
    name = fields.Char(string='Item Name *', required=True, index=True)
    long_description = fields.Text(string='Long Description')
    capacity = fields.Char(string='Capacity')
    sale_price = fields.Float(string='Selling Price', default=0.0)
    cost_price = fields.Float(string='Cost Price', default=0.0)

    main_group_name = fields.Char(string='Main Group (Raw)')
    main_grp_id = fields.Many2one('t.mainproducts', string='Main Group', index=True)

    category_name = fields.Char(string='Product Category (Raw)')
    category_id = fields.Many2one('product.category', string='Category', index=True)
    product_category_id = fields.Many2one('product.category', string='Product Category', index=True,
                                          domain="[('parent_id', '=', False)]")
    product_group_id = fields.Many2one('product.category', string='Product Group', index=True,
                                       domain="[('parent_id', '=', product_category_id)]")

    unit_name = fields.Char(string='Unit (Raw)')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', index=True)

    accessories = fields.Char(string='Accessories')

    state = fields.Selection([
        ('draft', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, index=True)

    product_id = fields.Many2one('product.product', string='Created Product', readonly=True, copy=False)
    product_tmpl_id = fields.Many2one('product.template', string='Created Product Template',
                                      related='product_id.product_tmpl_id', readonly=True, store=True)

    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approved_date = fields.Datetime(string='Approved Date', readonly=True, copy=False)
    rejection_reason = fields.Text(string='Rejection Reason', copy=False)

    @api.model
    def _register_hook(self):
        """Self-healing hook: ensure menu and action exist in PostgreSQL on boot."""
        super()._register_hook()
        try:
            self._ensure_action_and_menu()
        except Exception:
            pass

    @api.model
    def _ensure_action_and_menu(self):
        """Ensure the Item Approvals and Import Non-Stock action/menus are in database."""
        # 1. Update action_crm_commercial_item_approval to target crm.commercial.item.approval
        act = self.env['ir.actions.act_window'].sudo().search([
            ('res_model', '=', 'crm.commercial.item.approval')
        ], limit=1)
        if not act:
            act_old = self.env.ref('crm_commercial.action_crm_commercial_item_approval', raise_if_not_found=False)
            if act_old:
                act_old.sudo().write({
                    'name': 'Item Approvals',
                    'res_model': 'crm.commercial.item.approval',
                    'view_mode': 'tree,form',
                    'domain': '[]',
                })
                act = act_old
            else:
                act = self.env['ir.actions.act_window'].sudo().create({
                    'name': 'Item Approvals',
                    'res_model': 'crm.commercial.item.approval',
                    'view_mode': 'tree,form',
                    'target': 'current',
                })

        # 2. Ensure Import Non-Stock wizard action exists
        wiz_act = self.env['ir.actions.act_window'].sudo().search([
            ('res_model', '=', 'crm.commercial.import.non.stock.wizard')
        ], limit=1)
        if not wiz_act:
            wiz_act_ref = self.env.ref('crm_commercial.action_crm_commercial_import_non_stock_wizard', raise_if_not_found=False)
            if wiz_act_ref:
                wiz_act = wiz_act_ref
            else:
                wiz_act = self.env['ir.actions.act_window'].sudo().create({
                    'name': 'Import Non-Stock Items',
                    'res_model': 'crm.commercial.import.non.stock.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                })

        # 3. Ensure menu items exist
        config_menu = self.env.ref('crm_commercial.menu_crm_commercial_config', raise_if_not_found=False)
        if not config_menu:
            config_menu = self.env['ir.ui.menu'].sudo().search([
                ('name', '=', 'Configuration'),
                ('parent_id.name', '=', 'CRM Commercial')
            ], limit=1)

        if config_menu and wiz_act:
            import_menu = self.env['ir.ui.menu'].sudo().search([
                ('parent_id', '=', config_menu.id),
                ('name', '=', 'Import Non-Stock')
            ], limit=1)
            if not import_menu:
                self.env['ir.ui.menu'].sudo().create({
                    'name': 'Import Non-Stock',
                    'parent_id': config_menu.id,
                    'action': f'ir.actions.act_window,{wiz_act.id}',
                    'sequence': 75,
                })

        # 4. Ensure model access rights exist in DB for wizards and staging models
        try:
            Access = self.env['ir.model.access'].sudo()
            group_user = self.env.ref('base.group_user', raise_if_not_found=False)
            group_comm_user = self.env.ref('crm_commercial.group_crm_commercial_user', raise_if_not_found=False)
            group_comm_mgr = self.env.ref('crm_commercial.group_crm_commercial_manager', raise_if_not_found=False)

            target_models = ['crm.commercial.import.non.stock.wizard', 'crm.commercial.item.approval']
            for m_name in target_models:
                m_rec = self.env['ir.model'].sudo().search([('model', '=', m_name)], limit=1)
                if not m_rec:
                    continue
                for g in [group_user, group_comm_user, group_comm_mgr]:
                    if not g:
                        continue
                    existing = Access.search([('model_id', '=', m_rec.id), ('group_id', '=', g.id)], limit=1)
                    if not existing:
                        Access.create({
                            'name': f'{m_name} access for {g.name}',
                            'model_id': m_rec.id,
                            'group_id': g.id,
                            'perm_read': True,
                            'perm_write': True,
                            'perm_create': True,
                            'perm_unlink': True,
                        })
        except Exception:
            pass

        # 5. Clean up any obsolete global region record rules from DB to prevent safe_eval syntax errors
        try:
            rule_names = [
                'rule_crm_commercial_lead_region_global',
                'rule_crm_commercial_quotation_region_global',
                'rule_crm_commercial_sale_order_region_global',
            ]
            for r_xml in rule_names:
                r_rec = self.env.ref(f'crm_commercial.{r_xml}', raise_if_not_found=False)
                if r_rec:
                    r_rec.sudo().unlink()
            old_rules = self.env['ir.rule'].sudo().search([
                ('name', 'in', [
                    'CRM Commercial Lead: User Assigned Region Restriction',
                    'CRM Commercial Quotation: User Assigned Region Restriction',
                    'CRM Commercial Sale Order: User Assigned Region Restriction',
                ])
            ])
            if old_rules:
                old_rules.unlink()
        except Exception:
            pass

        try:
            self.env.cr.commit()
            self.env.registry.clear_cache()
        except Exception:
            pass

    @api.model
    def _resolve_product_category(self, main_grp_val):
        """
        If main group is MDA -> Product Category is Media / Midea.
        If ASK -> ALASKA.
        Searches top-level (parent_id = False) product.category.
        """
        CategoryModel = self.env['product.category'].sudo()
        mg = (main_grp_val or '').strip().upper()

        names_to_check = []
        if mg in ('MDA', 'MIDEA', 'MEDIA'):
            # Check Media first (as specified: 'product category is media'), then Midea
            names_to_check = ['Media', 'Midea', 'MEDIA', 'MIDEA']
        elif mg in ('ASK', 'ALASKA'):
            names_to_check = ['ALASKA', 'Alaska']
        elif mg:
            names_to_check = [main_grp_val.strip()]

        # 1. Search top-level category (parent_id = False) matching names
        for n in names_to_check:
            cat = CategoryModel.search([('parent_id', '=', False), ('name', '=ilike', n)], limit=1)
            if cat:
                return cat

        # 2. Search category anywhere matching names
        for n in names_to_check:
            cat = CategoryModel.search([('name', '=ilike', n)], limit=1)
            if cat:
                return cat

        # 3. If main group is MDA and neither exists, create 'Media' with parent_id=False
        if mg in ('MDA', 'MIDEA', 'MEDIA'):
            return CategoryModel.create({
                'name': 'Media',
                'parent_id': False,
            })
        elif mg in ('ASK', 'ALASKA'):
            return CategoryModel.create({
                'name': 'ALASKA',
                'parent_id': False,
            })
        elif names_to_check:
            return CategoryModel.create({
                'name': names_to_check[0],
                'parent_id': False,
            })

        return CategoryModel.search([('parent_id', '=', False)], limit=1) or CategoryModel.search([], limit=1)

    @api.model
    def _resolve_product_group(self, group_name, parent_category=None):
        """
        Resolves Product Group (e.g. ACWTSplit, CHILLER) under parent_category.
        """
        CategoryModel = self.env['product.category'].sudo()
        g_raw = (group_name or '').strip()
        if not g_raw:
            return False

        # 1. Search under parent_category
        if parent_category:
            grp = CategoryModel.search([
                ('parent_id', '=', parent_category.id),
                ('name', '=ilike', g_raw)
            ], limit=1)
            if grp:
                return grp

        # 2. Search anywhere
        grp = CategoryModel.search([('name', '=ilike', g_raw)], limit=1)
        if grp:
            if not grp.parent_id and parent_category:
                try:
                    grp.write({'parent_id': parent_category.id})
                except Exception:
                    pass
            return grp

        # 3. Create under parent_category
        return CategoryModel.create({
            'name': g_raw,
            'parent_id': parent_category.id if parent_category else False,
        })

    @api.model
    def _resolve_uom(self, unit_val):
        """
        If unit is PCS, ensure unit of measure is PCS.
        Creates uom.uom with name 'PCS' under Unit category if missing.
        """
        UomModel = self.env['uom.uom'].sudo()
        u_raw = (unit_val or '').strip()
        u_upper = u_raw.upper()

        is_pcs = u_upper in ('PCS', 'PC', 'S', 'PIECE', 'PIECES') or not u_raw

        if is_pcs:
            # 1. Search for existing PCS
            for n in ['PCS', 'Pcs', 'pcs']:
                uom = UomModel.search([('name', '=', n)], limit=1)
                if uom:
                    return uom
            uom = UomModel.search([('name', '=ilike', 'PCS')], limit=1)
            if uom:
                return uom

            # 2. Create 'PCS' under Unit of Measure category
            unit_categ = self.env.ref('uom.uom_categ_unit', raise_if_not_found=False)
            if not unit_categ:
                unit_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False) or UomModel.search([], limit=1)
                unit_categ = unit_uom.category_id if unit_uom else self.env['uom.category'].sudo().search([], limit=1)

            if unit_categ:
                has_ref = UomModel.search([('category_id', '=', unit_categ.id), ('uom_type', '=', 'reference')], limit=1)
                return UomModel.create({
                    'name': 'PCS',
                    'category_id': unit_categ.id,
                    'uom_type': 'smaller' if has_ref else 'reference',
                    'factor': 1.0,
                    'rounding': 1.0,
                    'active': True,
                })

        elif u_raw:
            uom = UomModel.search([('name', '=ilike', u_raw)], limit=1)
            if uom:
                return uom

        return self.env.ref('uom.product_uom_unit', raise_if_not_found=False) or UomModel.search([], limit=1)

    def action_approve(self):
        """Approve record(s) and automatically insert into product.template and product.product tables."""
        for rec in self:
            # Check if product with this part_no already exists
            existing_product = self.env['product.product'].sudo().search([
                ('default_code', '=', rec.part_no)
            ], limit=1)

            # 1. Resolve Product Category: if main group is MDA -> Media/Midea
            mg_str = rec.main_group_name or (rec.main_grp_id.mp_code if rec.main_grp_id else '')
            prod_category = rec.product_category_id or self._resolve_product_category(mg_str)

            # 2. Resolve Product Group (e.g. ACWTSplit)
            prod_group = rec.product_group_id or self._resolve_product_group(rec.category_name, prod_category)

            # 3. Resolve Unit of Measure: if unit is PCS -> PCS
            uom = rec.uom_id or self._resolve_uom(rec.unit_name)
            if rec.unit_name and rec.unit_name.strip().upper() in ('PCS', 'PC', 'S', 'PIECE', 'PIECES'):
                if not uom or uom.name.upper() not in ('PCS', 'PC'):
                    uom = self._resolve_uom('PCS')

            # 4. Standard categ_id: group or category
            categ = prod_group or prod_category or rec.category_id

            vals = {
                'name': rec.name,
                'default_code': rec.part_no,
                'long_description': rec.long_description or '',
                'description_sale': rec.long_description or '',
                'capacity': rec.capacity or '',
                'list_price': rec.sale_price or 0.0,
                'standard_price': rec.cost_price or 0.0,
                'categ_id': categ.id if categ else False,
                'non_stock_item': True,
                'approval_state': 'approved',
                'accessories': rec.accessories or '',
            }
            if rec.main_grp_id:
                vals['product_main_grp_id'] = rec.main_grp_id.id
            if prod_category:
                vals['product_category_id'] = prod_category.id
            if prod_group:
                vals['product_group_id'] = prod_group.id
            if uom:
                vals['uom_id'] = uom.id
                vals['uom_po_id'] = uom.id

            if existing_product:
                if existing_product.product_tmpl_id:
                    existing_product.product_tmpl_id.sudo().write(vals)
                else:
                    existing_product.sudo().write(vals)
                product = existing_product
            else:
                template = self.env['product.template'].sudo().create(vals)
                product = template.product_variant_ids[:1]

            rec.write({
                'state': 'approved',
                'product_category_id': prod_category.id if prod_category else False,
                'product_group_id': prod_group.id if prod_group else False,
                'category_id': categ.id if categ else rec.category_id.id,
                'uom_id': uom.id if uom else rec.uom_id.id,
                'product_id': product.id,
                'approved_by_id': self.env.uid,
                'approved_date': fields.Datetime.now(),
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Item(s) Approved'),
                'message': _('Successfully approved and inserted into Product Catalog (product.product & product.template).'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reject(self):
        """Reject item approval record."""
        for rec in self:
            rec.write({
                'state': 'rejected',
                'rejection_reason': rec.rejection_reason or _('Rejected by %s') % self.env.user.name,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Item(s) Rejected'),
                'message': _('Item(s) marked as Rejected. No product was created.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_view_product(self):
        """Smart button to open the created product variant in product.product."""
        self.ensure_one()
        if not self.product_id:
            raise UserError(_("No product has been created for this record yet."))
        return {
            'name': _('Approved Product'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
