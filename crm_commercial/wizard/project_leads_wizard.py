# -*- coding: utf-8 -*-
import base64
import io
import os
import logging

import xlsxwriter

from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectLeadsReportWizard(models.TransientModel):
    _name = 'hhs.project.leads.wizard'
    _description = 'Project Leads Report Wizard'

    @api.model
    def _register_hook(self):
        super()._register_hook()
        try:
            self._ensure_action_and_menu()
        except Exception as e:
            _logger.warning("ProjectLeadsReportWizard _register_hook exception: %s", e)

    @api.model
    def _ensure_action_and_menu(self):
        env = self.env
        # 1. Check or create Window Action
        action = env.ref('crm_commercial.action_project_leads_wizard', raise_if_not_found=False)
        if not action:
            xml_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', 'views', 'project_leads_wizard_views.xml')
            )
            if os.path.exists(xml_path):
                try:
                    tools.convert_file(env.cr, 'crm_commercial', xml_path, {}, mode='update', noupdate=False, kind='data')
                    action = env.ref('crm_commercial.action_project_leads_wizard', raise_if_not_found=False)
                except Exception as ex:
                    _logger.warning("tools.convert_file failed: %s", ex)

        if not action:
            lead_model = env['ir.model'].search([('model', '=', 'crm.commercial.lead')], limit=1)
            action = env['ir.actions.act_window'].create({
                'name': 'Project Lead Report',
                'res_model': 'hhs.project.leads.wizard',
                'view_mode': 'form',
                'target': 'new',
                'binding_model_id': lead_model.id if lead_model else False,
                'binding_view_types': 'list,form',
            })
            env['ir.model.data'].create({
                'module': 'crm_commercial',
                'name': 'action_project_leads_wizard',
                'model': 'ir.actions.act_window',
                'res_id': action.id,
                'noupdate': True,
            })

        # 2. Check / create menu under Reports
        reports_parent = env.ref('crm_commercial.menu_crm_commercial_reports', raise_if_not_found=False)
        if reports_parent:
            report_menu = env.ref('crm_commercial.menu_project_leads_report', raise_if_not_found=False)
            if not report_menu:
                existing = env['ir.ui.menu'].search([
                    ('parent_id', '=', reports_parent.id),
                    ('name', '=', 'Project Lead Report'),
                ], limit=1)
                if not existing:
                    report_menu = env['ir.ui.menu'].create({
                        'name': 'Project Lead Report',
                        'parent_id': reports_parent.id,
                        'action': f'ir.actions.act_window,{action.id}',
                        'sequence': 5,
                    })
                    env['ir.model.data'].create({
                        'module': 'crm_commercial',
                        'name': 'menu_project_leads_report',
                        'model': 'ir.ui.menu',
                        'res_id': report_menu.id,
                        'noupdate': True,
                    })

        # 3. Check / create menu under Transactions
        trans_parent = env.ref('crm_commercial.menu_crm_commercial_transactions', raise_if_not_found=False)
        if trans_parent:
            trans_menu = env.ref('crm_commercial.menu_project_leads_report_trans', raise_if_not_found=False)
            if not trans_menu:
                existing_trans = env['ir.ui.menu'].search([
                    ('parent_id', '=', trans_parent.id),
                    ('name', '=', 'Project Lead Report'),
                ], limit=1)
                if not existing_trans:
                    trans_menu = env['ir.ui.menu'].create({
                        'name': 'Project Lead Report',
                        'parent_id': trans_parent.id,
                        'action': f'ir.actions.act_window,{action.id}',
                        'sequence': 15,
                    })
                    env['ir.model.data'].create({
                        'module': 'crm_commercial',
                        'name': 'menu_project_leads_report_trans',
                        'model': 'ir.ui.menu',
                        'res_id': trans_menu.id,
                        'noupdate': True,
                    })

        # 4. Ensure base.group_user access
        model_rec = env['ir.model'].search([('model', '=', 'hhs.project.leads.wizard')], limit=1)
        if model_rec:
            group_user = env.ref('base.group_user', raise_if_not_found=False)
            if group_user:
                existing_acl = env['ir.model.access'].search([
                    ('model_id', '=', model_rec.id),
                    ('group_id', '=', group_user.id),
                ], limit=1)
                if not existing_acl:
                    env['ir.model.access'].create({
                        'name': 'hhs.project.leads.wizard base',
                        'model_id': model_rec.id,
                        'group_id': group_user.id,
                        'perm_read': True,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True,
                    })

    date_from = fields.Date(string='From Date', required=True,
                            default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    region_id = fields.Many2one('res.region', string='Region')
    project_category_id = fields.Many2one('crm.commercial.project.category', string='Project')
    partner_id = fields.Many2one('res.partner', string='Customer')
    state = fields.Selection([
        ('draft', 'New'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('converted', 'Converted'),
    ], string='Status', help='Leave empty to include leads in every status.')

    file_data = fields.Binary(string='Report', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)

    def _get_domain(self):
        self.ensure_one()
        domain = [
            ('creation_date', '>=', self.date_from),
            ('creation_date', '<=', self.date_to),
        ]
        if self.state:
            domain.append(('state', '=', self.state))
        if self.region_id:
            domain.append(('region_id', '=', self.region_id.id))
        if self.project_category_id:
            domain.append(('project_category_id', '=', self.project_category_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        return domain

    def action_export_excel(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise ValidationError(_('From Date cannot be later than To Date.'))
        leads = self.env['crm.commercial.lead'].search(self._get_domain(), order='creation_date, id')
        if not leads:
            raise UserError(_('No leads found for the selected filters.'))

        # Same columns / cell formatting as the leads list "Print Leads - Excel"
        report = self.env['report.crm_commercial.lead_list_xlsx']
        cols = [(f, h) for f, h in report._LEAD_COLUMNS if f in leads._fields]

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Project Leads')
        f_title = wb.add_format({'bold': True, 'font_size': 14})
        f_head = wb.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': '#FFFFFF',
                                'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        f_txt = wb.add_format({'border': 1})
        f_num = wb.add_format({'border': 1, 'num_format': '#,##0.00'})

        ws.write(0, 0, 'Project Leads', f_title)
        filters = [f'Period: {self.date_from} to {self.date_to}']
        if self.region_id:
            filters.append(f'Region: {self.region_id.name}')
        if self.project_category_id:
            filters.append(f'Project: {self.project_category_id.display_name}')
        if self.partner_id:
            filters.append(f'Customer: {self.partner_id.display_name}')
        if self.state:
            filters.append(f'Status: {dict(self._fields["state"].selection)[self.state]}')
        ws.write(1, 0, '   |   '.join(filters))

        hr = 3
        ws.set_row(hr, 32)
        for c, (_f, heading) in enumerate(cols):
            ws.write(hr, c, heading, f_head)
            ws.set_column(c, c, max(14, len(heading) + 4))

        row = hr + 1
        for lead in leads:
            for c, (fname, _h) in enumerate(cols):
                val = report._cell(lead, fname)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    ws.write_number(row, c, val, f_num)
                else:
                    ws.write(row, c, val, f_txt)
            row += 1

        ws.freeze_panes(hr + 1, 0)
        ws.autofilter(hr, 0, row - 1, len(cols) - 1)
        wb.close()

        self.write({
            'file_data': base64.b64encode(output.getvalue()),
            'file_name': f'Project_Leads_{self.date_from}_{self.date_to}.xlsx',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}'
                   f'&field=file_data&filename_field=file_name&download=true',
            'target': 'self',
        }
