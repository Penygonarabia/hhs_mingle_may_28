# -*- coding: utf-8 -*-
import base64
import io

import xlsxwriter

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError


class ConfirmedOrdersReportWizard(models.TransientModel):
    _name = 'crm.commercial.confirmed.orders.wizard'
    _description = 'Confirmed Booked Projects Report Wizard'

    date_from = fields.Date(string='From Date', required=True,
                            default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    region_id = fields.Many2one('res.region', string='Region')
    project_category_id = fields.Many2one('crm.commercial.project.category', string='Project')
    partner_id = fields.Many2one('res.partner', string='Customer')
    state = fields.Selection([
        ('confirmed', 'Confirmed'),
        ('partially_delivered', 'Partially Delivered'),
        ('delivered', 'Delivered'),
    ], string='Status', help='Leave empty to include all confirmed / delivered orders.')

    file_data = fields.Binary(string='Report', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)

    # ------------------------------------------------------------------
    def _get_domain(self):
        self.ensure_one()
        domain = [
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('state', 'in', [self.state] if self.state else
             ['confirmed', 'partially_delivered', 'delivered']),
        ]
        if self.project_category_id:
            domain.append(('project_category_id', '=', self.project_category_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        return domain

    @staticmethod
    def _line_schedule_date(line):
        """Next pending delivery date of the line; if everything is delivered,
        the last scheduled date. Empty when no schedule exists."""
        schedules = line.schedule_ids
        if not schedules:
            return ''
        pending = schedules.filtered(lambda s: s.status != 'delivered')
        if pending:
            return min(pending.mapped('scheduled_date'))
        return max(schedules.mapped('scheduled_date'))

    @staticmethod
    def _line_gm_percent(line):
        """Actual GM % = (delivered amount - delivered cost) / delivered amount.
        0 when nothing has been delivered yet."""
        if line.delivered_amount:
            return (line.delivered_amount - line.delivered_cost) / line.delivered_amount * 100.0
        return 0.0

    @staticmethod
    def _order_region(order):
        """Return the res.region (East / West ...) of an order. Never returns a
        res.country.state. Sources, in order: city -> quotation -> order."""
        city = order.city_id
        if city and 'region_id' in city._fields and city.region_id:
            return city.region_id
        quo = order.quotation_id
        if quo and 'region_id' in quo._fields and \
                quo._fields['region_id'].comodel_name == 'res.region' and quo.region_id:
            return quo.region_id
        if order._fields['region_id'].comodel_name == 'res.region' and order.region_id:
            return order.region_id
        return order.env['res.region']

    def action_export_excel(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise ValidationError(_('From Date cannot be later than To Date.'))
        orders = self.env['crm.commercial.sale.order'].search(self._get_domain(), order='date_order, id')
        if self.region_id:
            orders = orders.filtered(lambda o: self._order_region(o) == self.region_id)
        if not orders:
            raise UserError(_('No orders found for the selected filters.'))

        # Make sure actual cost is current before exporting
        orders._recompute_actual_delivery()

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Confirmed Booked Projects')

        f_title = wb.add_format({'bold': True, 'font_size': 14})
        f_head = wb.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': '#FFFFFF',
                                'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        f_txt = wb.add_format({'border': 1})
        f_num = wb.add_format({'border': 1, 'num_format': '#,##0.00'})
        f_pct = wb.add_format({'border': 1, 'num_format': '0.00"%"'})
        f_date = wb.add_format({'border': 1, 'num_format': 'dd-mmm-yyyy', 'align': 'left'})
        f_tot_p = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#DDEBF7', 'num_format': '0.00"%"'})
        f_tot = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#DDEBF7', 'num_format': '#,##0.00'})
        f_tot_t = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#DDEBF7'})

        # (header, getter(order, line), format, width, sum?)
        cols = [
            ('Region', lambda o, l: o.region_id.name or '', f_txt, 18, False),
            ('City', lambda o, l: o.city or o.city_id.name or '', f_txt, 16, False),
            ('Salesman', lambda o, l: o.assigned_id.name or '', f_txt, 20, False),
            ('Project Name', lambda o, l: o.project_name or '', f_txt, 30, False),
            ('Product', lambda o, l: l.product_id.display_name or '', f_txt, 36, False),
            ('Value', lambda o, l: l.amount, f_num, 16, True),
            # ('Total Amount', lambda o, l: l.amount, f_num, 16, True),
            # ('Ordered Qty', lambda o, l: l.qty, f_num, 13, True),
            ('Delivered Qty', lambda o, l: l.delivered_qty, f_num, 13, True),
            ('Remaining', lambda o, l: 0, f_num, 13, True),
            # ('Remaining', lambda o, l: l.qty - l.delivered_qty, f_num, 13, True),  # Ordered Qty - Delivered Qty,
            # ('Delivered', lambda o, l: l.qty - l.delivered_qty, f_num, 13, True),  # Ordered Qty - Delivered Qty,
            ('GM %', lambda o, l: self._line_gm_percent(l), f_pct, 14, False),
            # ('Actual GM %', lambda o, l: self._line_gm_percent(l), f_pct, 14, False),
            ('Delivery', lambda o, l: self._line_schedule_date(l), f_date, 14, False),
            # ('Scheduled Date', lambda o, l: self._line_schedule_date(l), f_date, 14, False),
        ]

        ws.write(0, 0, 'Confirmed Booked Projects', f_title)
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
        for c, (h, _g, _f, w, _s) in enumerate(cols):
            ws.write(hr, c, h, f_head)
            ws.set_column(c, c, w)

        row = hr + 1
        lines_all = self.env['crm.commercial.sale.order.line']
        for order in orders:
            for line in order.line_ids:
                lines_all |= line
                for c, (_h, getter, fmt, _w, _s) in enumerate(cols):
                    ws.write(row, c, getter(order, line), fmt)
                row += 1

        # Totals row (live Excel SUM formulas)
        first, last = hr + 2, row
        ws.write(row, 0, 'TOTAL', f_tot_t)
        for c, (_h, getter, _f, _w, do_sum) in enumerate(cols):
            if c == 0:
                continue
            if do_sum:
                col = xlsxwriter.utility.xl_col_to_name(c)
                value = sum(getter(l.order_id, l) for l in lines_all)
                ws.write_formula(row, c, f'=SUM({col}{first}:{col}{last})', f_tot, value)
            else:
                ws.write(row, c, '', f_tot_t)

        # Weighted Actual GM % for the whole report (not a simple sum/average)
        rev = sum(lines_all.mapped('delivered_amount'))
        cost = sum(lines_all.mapped('delivered_cost'))
        gm_col = next((i for i, col in enumerate(cols) if 'GM' in col[0]), None)
        if gm_col is not None:  # skip silently if the GM column was removed
            ws.write(row, gm_col, ((rev - cost) / rev * 100.0) if rev else 0.0, f_tot_p)

        ws.freeze_panes(hr + 1, 0)
        ws.autofilter(hr, 0, row - 1, len(cols) - 1)
        wb.close()

        self.write({
            'file_data': base64.b64encode(output.getvalue()),
            'file_name': f'Confirmed_Booked_Projects_{self.date_from}_{self.date_to}.xlsx',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}'
                   f'&field=file_data&filename_field=file_name&download=true',
            'target': 'self',
        }

# # -*- coding: utf-8 -*-
# # -*- coding: utf-8 -*-
# import base64
# import io
#
# import xlsxwriter
#
# from odoo import fields, models, _
# from odoo.exceptions import UserError, ValidationError
#
#
# class ConfirmedOrdersReportWizard(models.TransientModel):
#     _name = 'crm.commercial.confirmed.orders.wizard'
#     _description = 'Confirmed Booked Projects Report Wizard'
#
#     date_from = fields.Date(string='From Date', required=True,
#                             default=lambda self: fields.Date.today().replace(day=1))
#     date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
#     region_id = fields.Many2one('res.country.state', string='Region')
#     project_category_id = fields.Many2one('crm.commercial.project.category', string='Project')
#     partner_id = fields.Many2one('res.partner', string='Customer')
#     state = fields.Selection([
#         ('confirmed', 'Confirmed'),
#         ('partially_delivered', 'Partially Delivered'),
#         ('delivered', 'Delivered'),
#     ], string='Status', help='Leave empty to include all confirmed / delivered orders.')
#
#     file_data = fields.Binary(string='Report', readonly=True)
#     file_name = fields.Char(string='File Name', readonly=True)
#
#     # ------------------------------------------------------------------
#     def _get_domain(self):
#         self.ensure_one()
#         domain = [
#             ('date_order', '>=', self.date_from),
#             ('date_order', '<=', self.date_to),
#             ('state', 'in', [self.state] if self.state else
#              ['confirmed', 'partially_delivered', 'delivered']),
#         ]
#         if self.region_id:
#             domain.append(('region_id', '=', self.region_id.id))
#         if self.project_category_id:
#             domain.append(('project_category_id', '=', self.project_category_id.id))
#         if self.partner_id:
#             domain.append(('partner_id', '=', self.partner_id.id))
#         return domain
#
#     @staticmethod
#     def _line_schedule_date(line):
#         """Next pending delivery date of the line; if everything is delivered,
#         the last scheduled date. Empty when no schedule exists."""
#         schedules = line.schedule_ids
#         if not schedules:
#             return ''
#         pending = schedules.filtered(lambda s: s.status != 'delivered')
#         if pending:
#             return min(pending.mapped('scheduled_date'))
#         return max(schedules.mapped('scheduled_date'))
#
#     @staticmethod
#     def _line_gm_percent(line):
#         """Actual GM % = (delivered amount - delivered cost) / delivered amount.
#         0 when nothing has been delivered yet."""
#         if line.delivered_amount:
#             return (line.delivered_amount - line.delivered_cost) / line.delivered_amount * 100.0
#         return 0.0
#
#     def action_export_excel(self):
#         self.ensure_one()
#         if self.date_from > self.date_to:
#             raise ValidationError(_('From Date cannot be later than To Date.'))
#         orders = self.env['crm.commercial.sale.order'].search(self._get_domain(), order='date_order, id')
#         if not orders:
#             raise UserError(_('No orders found for the selected filters.'))
#
#         # Make sure actual cost is current before exporting
#         orders._recompute_actual_delivery()
#
#         output = io.BytesIO()
#         wb = xlsxwriter.Workbook(output, {'in_memory': True})
#         ws = wb.add_worksheet('Confirmed Booked Projects')
#
#         f_title = wb.add_format({'bold': True, 'font_size': 14})
#         f_head = wb.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': '#FFFFFF',
#                                 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
#         f_txt = wb.add_format({'border': 1})
#         f_num = wb.add_format({'border': 1, 'num_format': '#,##0.00'})
#         f_pct = wb.add_format({'border': 1, 'num_format': '0.00"%"'})
#         f_date = wb.add_format({'border': 1, 'num_format': 'dd-mmm-yyyy', 'align': 'left'})
#         f_tot_p = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#DDEBF7', 'num_format': '0.00"%"'})
#         f_tot = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#DDEBF7', 'num_format': '#,##0.00'})
#         f_tot_t = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#DDEBF7'})
#
#         # (header, getter(order, line), format, width, sum?)
#         cols = [
#             ('Region', lambda o, l: o.region_id.name or '', f_txt, 18, False),
#             ('City', lambda o, l: o.city or o.city_id.name or '', f_txt, 16, False),
#             ('Salesman', lambda o, l: o.assigned_id.name or '', f_txt, 20, False),
#             ('Project Name', lambda o, l: o.project_name or '', f_txt, 30, False),
#             ('Product', lambda o, l: l.product_id.display_name or '', f_txt, 36, False),
#             ('Value', lambda o, l: l.amount, f_num, 16, True),
#             # ('Total Amount', lambda o, l: l.amount, f_num, 16, True),
#             ('Ordered Qty', lambda o, l: l.qty, f_num, 13, True),
#             ('Delivered Qty', lambda o, l: l.delivered_qty, f_num, 13, True),
#             ('Remaining', lambda o, l: l.qty - l.delivered_qty, f_num, 13, True),  # Ordered Qty - Delivered Qty,
#             # ('Delivered', lambda o, l: l.qty - l.delivered_qty, f_num, 13, True),  # Ordered Qty - Delivered Qty,
#             ('GM %', lambda o, l: self._line_gm_percent(l), f_pct, 14, False),
#             # ('Actual GM %', lambda o, l: self._line_gm_percent(l), f_pct, 14, False),
#             ('Delivery', lambda o, l: self._line_schedule_date(l), f_date, 14, False),
#             # ('Scheduled Date', lambda o, l: self._line_schedule_date(l), f_date, 14, False),
#         ]
#
#         ws.write(0, 0, 'Confirmed Booked Projects', f_title)
#         filters = [f'Period: {self.date_from} to {self.date_to}']
#         if self.region_id:
#             filters.append(f'Region: {self.region_id.name}')
#         if self.project_category_id:
#             filters.append(f'Project: {self.project_category_id.display_name}')
#         if self.partner_id:
#             filters.append(f'Customer: {self.partner_id.display_name}')
#         if self.state:
#             filters.append(f'Status: {dict(self._fields["state"].selection)[self.state]}')
#         ws.write(1, 0, '   |   '.join(filters))
#
#         hr = 3
#         ws.set_row(hr, 32)
#         for c, (h, _g, _f, w, _s) in enumerate(cols):
#             ws.write(hr, c, h, f_head)
#             ws.set_column(c, c, w)
#
#         row = hr + 1
#         lines_all = self.env['crm.commercial.sale.order.line']
#         for order in orders:
#             for line in order.line_ids:
#                 lines_all |= line
#                 for c, (_h, getter, fmt, _w, _s) in enumerate(cols):
#                     ws.write(row, c, getter(order, line), fmt)
#                 row += 1
#
#         # Totals row (live Excel SUM formulas)
#         first, last = hr + 2, row
#         ws.write(row, 0, 'TOTAL', f_tot_t)
#         for c, (_h, getter, _f, _w, do_sum) in enumerate(cols):
#             if c == 0:
#                 continue
#             if do_sum:
#                 col = xlsxwriter.utility.xl_col_to_name(c)
#                 value = sum(getter(l.order_id, l) for l in lines_all)
#                 ws.write_formula(row, c, f'=SUM({col}{first}:{col}{last})', f_tot, value)
#             else:
#                 ws.write(row, c, '', f_tot_t)
#
#         # Weighted Actual GM % for the whole report (not a simple sum/average)
#         rev = sum(lines_all.mapped('delivered_amount'))
#         cost = sum(lines_all.mapped('delivered_cost'))
#         gm_col = next((i for i, col in enumerate(cols) if 'GM' in col[0]), None)
#         if gm_col is not None:  # skip silently if the GM column was removed
#             ws.write(row, gm_col, ((rev - cost) / rev * 100.0) if rev else 0.0, f_tot_p)
#
#         ws.freeze_panes(hr + 1, 0)
#         ws.autofilter(hr, 0, row - 1, len(cols) - 1)
#         wb.close()
#
#         self.write({
#             'file_data': base64.b64encode(output.getvalue()),
#             'file_name': f'Confirmed_Booked_Projects_{self.date_from}_{self.date_to}.xlsx',
#         })
#         return {
#             'type': 'ir.actions.act_url',
#             'url': f'/web/content/?model={self._name}&id={self.id}'
#                    f'&field=file_data&filename_field=file_name&download=true',
#             'target': 'self',
#         }


# # -*- coding: utf-8 -*-
# import base64
# import io
#
# import xlsxwriter
#
# from odoo import fields, models, _
# from odoo.exceptions import UserError, ValidationError
#
#
# class ConfirmedOrdersReportWizard(models.TransientModel):
#     _name = 'crm.commercial.confirmed.orders.wizard'
#     _description = 'Confirmed Booked Projects Report Wizard'
#
#     date_from = fields.Date(string='From Date', required=True,
#                             default=lambda self: fields.Date.today().replace(day=1))
#     date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
#     region_id = fields.Many2one('res.country.state', string='Region')
#     project_category_id = fields.Many2one('crm.commercial.project.category', string='Project')
#     partner_id = fields.Many2one('res.partner', string='Customer')
#     state = fields.Selection([
#         ('confirmed', 'Confirmed'),
#         ('partially_delivered', 'Partially Delivered'),
#         ('delivered', 'Delivered'),
#     ], string='Status', help='Leave empty to include all confirmed / delivered orders.')
#
#     file_data = fields.Binary(string='Report', readonly=True)
#     file_name = fields.Char(string='File Name', readonly=True)
#
#     # ------------------------------------------------------------------
#     def _get_domain(self):
#         self.ensure_one()
#         domain = [
#             ('date_order', '>=', self.date_from),
#             ('date_order', '<=', self.date_to),
#             ('state', 'in', [self.state] if self.state else
#              ['confirmed', 'partially_delivered', 'delivered']),
#         ]
#         if self.region_id:
#             domain.append(('region_id', '=', self.region_id.id))
#         if self.project_category_id:
#             domain.append(('project_category_id', '=', self.project_category_id.id))
#         if self.partner_id:
#             domain.append(('partner_id', '=', self.partner_id.id))
#         return domain
#
#     def action_export_excel(self):
#         self.ensure_one()
#         if self.date_from > self.date_to:
#             raise ValidationError(_('From Date cannot be later than To Date.'))
#         orders = self.env['crm.commercial.sale.order'].search(self._get_domain(), order='date_order, id')
#         if not orders:
#             raise UserError(_('No orders found for the selected filters.'))
#
#         # Make sure actual cost is current before exporting
#         orders._recompute_actual_delivery()
#
#         output = io.BytesIO()
#         wb = xlsxwriter.Workbook(output, {'in_memory': True})
#         ws = wb.add_worksheet('Confirmed Booked Projects')
#
#         f_title = wb.add_format({'bold': True, 'font_size': 14})
#         f_head = wb.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': '#FFFFFF',
#                                 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
#         f_txt = wb.add_format({'border': 1})
#         f_date = wb.add_format({'border': 1, 'num_format': 'dd-mmm-yyyy'})
#         f_num = wb.add_format({'border': 1, 'num_format': '#,##0.00'})
#         f_pct = wb.add_format({'border': 1, 'num_format': '0.00"%"'})
#         f_tot = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#DDEBF7', 'num_format': '#,##0.00'})
#         f_tot_t = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#DDEBF7'})
#         f_tot_p = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#DDEBF7', 'num_format': '0.00"%"'})
#
#         # (header, getter, format, width, sum?)
#         state_map = dict(orders._fields['state'].selection)
#         cols = [
#             ('S.No', None, f_txt, 6, False),
#             ('Order No', lambda o: o.name, f_txt, 16, False),
#             ('Order Date', lambda o: o.date_order, f_date, 13, False),
#             ('Quotation No', lambda o: o.quotation_no or '', f_txt, 16, False),
#             ('Customer', lambda o: o.partner_id.display_name, f_txt, 30, False),
#             ('Region', lambda o: o.region_id.name or '', f_txt, 16, False),
#             ('City', lambda o: o.city or o.city_id.name or '', f_txt, 14, False),
#             ('Project Category', lambda o: o.project_category_id.display_name or '', f_txt, 20, False),
#             ('Project Name', lambda o: o.project_name or '', f_txt, 28, False),
#             ('Consultant', lambda o: o.consultant_id.display_name or '', f_txt, 20, False),
#             ('Developer', lambda o: o.developer or '', f_txt, 20, False),
#             ('Salesman', lambda o: o.assigned_id.name, f_txt, 18, False),
#             ('Warehouse', lambda o: o.warehouse_id.name, f_txt, 16, False),
#             ('Project Status', lambda o: o.project_status_id.display_name or '', f_txt, 16, False),
#             ('Order Status', lambda o: state_map.get(o.state, o.state), f_txt, 16, False),
#             ('Selling Price (A)', lambda o: o.total_selling_price, f_num, 15, True),
#             ('Cost (B)', lambda o: o.total_cost, f_num, 15, True),
#             ('Supplier Support (S)', lambda o: o.total_supplier_support, f_num, 15, True),
#             ('DSI (C)', lambda o: o.total_dsi, f_num, 13, True),
#             ('SMC (D)', lambda o: o.total_smc, f_num, 13, True),
#             ('Promo (E)', lambda o: o.total_promo, f_num, 13, True),
#             ('Net Price (X)', lambda o: o.net_price, f_num, 15, True),
#             ('VAT', lambda o: o.total_vat, f_num, 13, True),
#             ('Total Amount', lambda o: o.total_amount, f_num, 16, True),
#             ('Expected GM %', lambda o: o.expected_gross_margin, f_pct, 13, False),
#             ('Ordered Qty', lambda o: sum(o.line_ids.mapped('qty')), f_num, 12, True),
#             ('Delivered Qty', lambda o: sum(o.line_ids.mapped('delivered_qty')), f_num, 12, True),
#             ('Actual Delivered Amount', lambda o: o.total_delivered_amount, f_num, 16, True),
#             ('Actual Delivered Cost', lambda o: o.total_delivered_cost, f_num, 16, True),
#             ('Actual GM Amount', lambda o: o.actual_gross_margin_amount, f_num, 15, True),
#             ('Actual GM %', lambda o: o.actual_gross_margin, f_pct, 13, False),
#         ]
#
#         ws.write(0, 0, 'Confirmed Booked Projects', f_title)
#         filters = [f'Period: {self.date_from} to {self.date_to}']
#         if self.region_id:
#             filters.append(f'Region: {self.region_id.name}')
#         if self.project_category_id:
#             filters.append(f'Project: {self.project_category_id.display_name}')
#         if self.partner_id:
#             filters.append(f'Customer: {self.partner_id.display_name}')
#         if self.state:
#             filters.append(f'Status: {dict(self._fields["state"].selection)[self.state]}')
#         ws.write(1, 0, '   |   '.join(filters))
#
#         hr = 3
#         ws.set_row(hr, 32)
#         for c, (h, _g, _f, w, _s) in enumerate(cols):
#             ws.write(hr, c, h, f_head)
#             ws.set_column(c, c, w)
#
#         row = hr + 1
#         for idx, order in enumerate(orders, 1):
#             for c, (h, getter, fmt, _w, _s) in enumerate(cols):
#                 ws.write(row, c, idx if getter is None else getter(order), fmt)
#             row += 1
#
#         # Totals row
#         first, last = hr + 2, row  # 1-based excel rows
#         ws.write(row, 0, 'TOTAL', f_tot_t)
#         idx_of = {h: i for i, (h, *_r) in enumerate(cols)}
#         for c, (h, _g, _f, _w, do_sum) in enumerate(cols):
#             if c == 0:
#                 continue
#             if do_sum:
#                 col = xlsxwriter.utility.xl_col_to_name(c)
#                 ws.write_formula(row, c, f'=SUM({col}{first}:{col}{last})', f_tot,
#                                  sum(getter(o) for o in orders) if (getter := cols[c][1]) else 0)
#             else:
#                 ws.write(row, c, '', f_tot_t)
#         # Weighted GM % in totals
#         rev = sum(orders.mapped('total_delivered_amount'))
#         gm = sum(orders.mapped('actual_gross_margin_amount'))
#         ws.write(row, idx_of['Actual GM %'], (gm / rev * 100.0) if rev else 0.0, f_tot_p)
#         sell = sum(orders.mapped('total_selling_price'))
#         exp_gm = sum(o.expected_gross_margin * o.total_selling_price for o in orders)
#         ws.write(row, idx_of['Expected GM %'], (exp_gm / sell) if sell else 0.0, f_tot_p)
#
#         ws.freeze_panes(hr + 1, 2)
#         ws.autofilter(hr, 0, row - 1, len(cols) - 1)
#         wb.close()
#
#         self.write({
#             'file_data': base64.b64encode(output.getvalue()),
#             'file_name': f'Confirmed_Booked_Projects_{self.date_from}_{self.date_to}.xlsx',
#         })
#         return {
#             'type': 'ir.actions.act_url',
#             'url': f'/web/content/?model={self._name}&id={self.id}'
#                    f'&field=file_data&filename_field=file_name&download=true',
#             'target': 'self',
#         }
