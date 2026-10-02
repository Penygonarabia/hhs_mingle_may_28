# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    is_crm_commercial_user = fields.Boolean(
        string='CRM Commercial User',
        default=False,
        index=True,
        help='Enables CRM Commercial menus and access for this user.'
    )
    crm_commercial_region_id = fields.Many2one(
        'res.country.state',
        string='Region',
        help='Default region assigned to user.'
    )
    crm_commercial_city_id = fields.Char(
        string='City',
        help='Default city assigned to user.'
    )
    crm_commercial_default_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Default Warehouse',
        domain="[('active', '=', True)]",
        help='Default active warehouse for user.'
    )
    reporting_manager_id = fields.Many2one(
        'res.users',
        string='Reporting Manager',
        domain="[('is_crm_commercial_user', '=', True)]",
        index=True,
        help='Reporting manager for approvals.'
    )

    # Permission Flags
    allow_cost_rights = fields.Boolean(
        string='Allow Cost Rights',
        help='Allows viewing original cost price from products and costing summaries.'
    )
    lead_auto_approval = fields.Boolean(
        string='Lead - Auto Approval',
        help='Automatically approves created leads.'
    )
    quotation_auto_approval = fields.Boolean(
        string='Quotation - Auto Approval',
        help='Automatically approves created quotations on save.'
    )
    allow_edit_quotation = fields.Boolean(
        string='Allow to edit Quotation',
        help='Allows editing quotation regardless of status.'
    )
    allow_edit_quotation_desc = fields.Boolean(
        string='Allow to edit description in Quotation',
        help='Allows editing description field in quotation.'
    )
    allow_edit_terms_features = fields.Boolean(
        string='Allow to edit Payment / Warranty Terms & Salient Features',
        help='Allows editing terms and features tabs.'
    )
    allow_export_quotation = fields.Boolean(
        string='Allow export Quotation',
        help='Allows exporting quotation screen data to Excel.'
    )
    allow_edit_default_discount = fields.Boolean(
        string='Allow to edit Default Discount % (Product Category)',
        help='Allows editing discount % column in quotation grid.'
    )
    allow_edit_sale_price = fields.Boolean(
        string='Allow to Edit Sales Price in Quotation',
        help='Allows editing sales price column in quotation grid.'
    )
    discount_limit_percent = fields.Float(
        string='User Discount Limit %',
        default=0.0,
        help='Maximum discount percentage user is authorized to give (0-100).'
    )

    is_locked_by_cron = fields.Boolean(
        string='Locked Due to Inactivity',
        default=False,
        readonly=True,
        help='Indicates if the user account was locked by the system due to pipeline inactivity.'
    )
    locked_date = fields.Datetime(
        string='Lockout Date',
        readonly=True
    )
    lock_reason = fields.Char(
        string='Lockout Reason',
        readonly=True
    )

    def action_unlock_user(self):
        from odoo.exceptions import ValidationError
        for user in self:
            current_user = self.env.user
            is_manager = (user.reporting_manager_id and current_user.id == user.reporting_manager_id.id)
            is_admin = current_user.has_group('crm_commercial.group_crm_commercial_manager') or current_user.has_group('base.group_system')
            if not (is_manager or is_admin):
                mgr_name = user.reporting_manager_id.name if user.reporting_manager_id else 'Reporting Manager'
                raise ValidationError(_("Only the reporting manager (%s) or a CRM Commercial Manager can unlock this user account.") % mgr_name)

            user.write({
                'active': True,
                'is_locked_by_cron': False,
                'locked_date': False,
                'lock_reason': False,
            })
            if user.partner_id:
                user.partner_id.message_post(
                    body=_("User account unlocked by %s.") % current_user.name,
                    subject=_("Account Unlocked"),
                    message_type='notification'
                )
