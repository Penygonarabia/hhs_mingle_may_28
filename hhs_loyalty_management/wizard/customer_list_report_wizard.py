# # -*- coding: utf-8 -*-
# """
# Customer List Report Wizard
# ===========================
# TransientModel that collects filter parameters and generates:
#   - A grouped PDF report (QWeb)
#   - A styled XLSX download (openpyxl)
#
# Data sources:
#   res_partner  (p)
#   sl_salesman  (s)   — sm_code, sm_lang
#   sl_salesmandesc (d) — sm_code, sm_name, sm_lang='1'
#
# Grouping: by sm_code (salesman code), sorted salesman_code → customer_code.
# """
#
# import io
# import base64
# import logging
# import time
#
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
#
# _logger = logging.getLogger(__name__)
#
#
#
#
# class CustomerListReportWizard(models.TransientModel):
#     """
#     Wizard: Customer List Report
#     Produces a salesman-grouped list of customers.
#     """
#     _name = 'customer.list.report.wizard'
#     _description = 'Customer List Report Wizard'
#
#     # ------------------------------------------------------------------
#     # Fields
#     # ------------------------------------------------------------------
#
#
#     customer_ids = fields.Many2many(
#         'res.partner',
#         'cust_list_rpt_wiz_partner_rel',
#         'wizard_id',
#         'partner_id',
#         string='Customers',
#     )
#     classification = fields.Char(string='Classification')
#
#
#
#     # ------------------------------------------------------------------
#     # Constraints
#     # ------------------------------------------------------------------
#
#     @api.constrains('last_purchase_from', 'last_purchase_to')
#     def _check_dates(self):
#         for rec in self:
#             if (rec.last_purchase_from and rec.last_purchase_to
#                     and rec.last_purchase_from > rec.last_purchase_to):
#                 raise UserError(
#                     _("Last Purchase 'To Date' must be ≥ 'From Date'.")
#                 )
#
#
#
#     # ------------------------------------------------------------------
#     # Core SQL helper
#     # ------------------------------------------------------------------
#
#     def _build_report_data(self):
#         """
#         Execute the optimized SQL query and group rows by salesman.
#
#         Returns
#         -------
#         dict  {sm_code: {'salesman_name': str, 'customers': [row, ...]}}
#         list  of the same customer rows (flat, for counting)
#         """
#         self.ensure_one()
#         t0 = time.time()
#
#         # ---- Build dynamic WHERE clauses ----------------------------
#         params = {'lang': '1'}
#         where_clauses = ["d.sm_lang = %(lang)s"]
#
#
#
#         # Customer filter
#         if self.customer_ids:
#             where_clauses.append("p.id = ANY(%(partner_ids)s)")
#             params['partner_ids'] = self.customer_ids.ids
#         where_sql = ' AND '.join(where_clauses)
#
#         # ---- Main query ---------------------------------------------
#         query = f"""
#             SELECT
#                 p.ref                AS customer_code,
#                 p.name               AS customer_name,
#                 cc.cc_desc           AS classification,
#                 ''                   AS region,
#                 p.city               AS city,
#                 p.last_purchase_date AS last_purchase_date,
#                 s.sm_code            AS sm_code,
#                 d.sm_name            AS sm_name
#             FROM res_partner p
#             JOIN sl_salesman s
#                 ON p.salesman_code = s.sm_code
#             JOIN sl_salesmandesc d
#                 ON s.sm_code = d.sm_code
#                 AND d.sm_lang = %(lang)s
#             JOIN customer c
#                 ON c.cst_no = p.ref
#             JOIN t_cstclassificationdesc cc
#                 ON cc.cc_code = c.cst_cstclassification
#             WHERE {where_sql}
#               AND p.active = TRUE
#               AND COALESCE(c.cst_allowloyalty, '0') != '1'
#             ORDER BY
#                 COALESCE(s.sm_code, ''),
#                 COALESCE(p.ref, p.name)
#         """
#
#         _logger.info(
#             "CustomerListReport | filters: customers=%s classification=%s",
#             [p.ref or p.name for p in self.customer_ids] or 'All',
#             self.classification or 'All',
#         )
#
#         self.env.cr.execute(query, params)
#         rows = self.env.cr.dictfetchall()
#
#         elapsed = round(time.time() - t0, 3)
#         _logger.info(
#             "CustomerListReport | records fetched: %d | elapsed: %ss",
#             len(rows), elapsed,
#         )
#
#         if not rows:
#             raise UserError(
#                 _("No customer records found for selected filters.")
#             )
#
#         # ---- Group by salesman --------------------------------------
#         grouped = {}
#         for row in rows:
#             code = row['sm_code'] or ''
#             if code not in grouped:
#                 grouped[code] = {
#                     'sm_code': code,
#                     'sm_name': row['sm_name'] or '',
#                     'customers': [],
#                 }
#             grouped[code]['customers'].append(row)
#
#         return grouped, rows
#
#     # ------------------------------------------------------------------
#     # Action: Print PDF
#     # ------------------------------------------------------------------
#
#     def action_print_pdf(self):
#         """Render QWeb PDF report."""
#         self.ensure_one()
#         grouped, flat_rows = self._build_report_data()
#
#         # Prepare filter labels for the report header
#         filters = self._get_filter_labels()
#
#         data = {
#             'grouped': grouped,
#             'flat_rows': flat_rows,
#             'filters': filters,
#             'wizard_id': self.id,
#             'company_dict': {
#                 'name': self.env.company.name,
#                 'street': self.env.company.street or '',
#                 'city': self.env.company.city or '',
#                 'phone': self.env.company.phone or '',
#                 'logo': self.env.company.logo,
#             },
#             'user_name': self.env.user.name,
#             'printed_at': fields.Datetime.now().strftime('%d-%m-%Y %H:%M'),
#         }
#
#         return self.env.ref(
#             'hhs_loyalty_management.action_report_customer_list'
#         ).report_action(self, data=data)
#
#     def _get_filter_labels(self):
#         """Return an ordered dict of filter display values."""
#         labels = {}
#         labels['Classification'] = self.classification or 'All'
#         return labels


# -*- coding: utf-8 -*-

import logging
import time
from collections import OrderedDict
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CustomerListReportWizard(models.TransientModel):
    _name = 'customer.list.report.wizard'
    _description = 'Customer List Report Wizard'

    # ==========================================================
    # FILTERS
    # ==========================================================

    salesman_from_id = fields.Many2one(
        'sl.salesman',
        string='Salesman From'
    )

    salesman_to_id = fields.Many2one(
        'sl.salesman',
        string='Salesman To'
    )

    customer_ids = fields.Many2many(
        'res.partner',
        'cust_list_rpt_wiz_partner_rel',
        'wizard_id',
        'partner_id',
        string='Customers',
        domain="[('activate_loyalty_feature','=',False)]"
    )

    classification = fields.Char(
        string='Classification'
    )

    # last_purchase_from = fields.Date(
    #     string='Last Purchase From'
    # )
    #
    # last_purchase_to = fields.Date(
    #     string='Last Purchase To'
    # )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    email = fields.Char('Email')

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @api.constrains('last_purchase_from', 'last_purchase_to')
    def _check_dates(self):
        for rec in self:
            if (
                rec.last_purchase_from
                and rec.last_purchase_to
                and rec.last_purchase_from > rec.last_purchase_to
            ):
                raise UserError(
                    _("Last Purchase To Date must be greater than or equal to From Date.")
                )

    # ==========================================================
    # REPORT DATA
    # ==========================================================

    def _build_report_data(self):
        self.ensure_one()

        start_time = time.time()

        params = {
            'lang': '1',
        }

        where_clauses = [
            "p.active = TRUE",
            "COALESCE(p.ref, '') <> ''",
        ]

        # ------------------------------------------------------
        # Customer Filter Only
        # ------------------------------------------------------

        if self.customer_ids:
            where_clauses.append(
                "p.id IN %(partner_ids)s"
            )
            params['partner_ids'] = tuple(self.customer_ids.ids)

        where_sql = " AND ".join(where_clauses)

        query = f"""
            SELECT DISTINCT

                p.ref AS customer_code,

                p.name AS customer_name,

                COALESCE(cc.cc_desc, '') AS classification,

                COALESCE(wcg.name, '') AS region,

                COALESCE(p.city, '') AS city,

                p.res_maxinvoicedate AS last_purchase_date,

                p.salesman_code AS sm_code,

                COALESCE(d.sm_name, '') AS sm_name,
                COALESCE(h.sm_stype, '') AS sm_stype,
                CASE
                    WHEN h.sm_stype = 'D' THEN 'Dealer'
                    WHEN h.sm_stype = 'P' THEN 'Project'
                    ELSE COALESCE(h.sm_stype, '')
                END AS sm_stype

            FROM res_partner p
            LEFT JOIN sl_salesman h
            ON h.sm_code=p.salesman_code
            LEFT JOIN sl_salesmandesc d
                 ON d.sm_code = p.salesman_code
           
            LEFT JOIN customer c
            ON c.cst_no = p.ref

             LEFT JOIN t_cstclassificationdesc cc
            ON cc.cc_code = c.cst_cstclassification
            
            LEFT JOIN res_city city_tbl
             ON city_tbl.id = p.customer_city_id
            
             LEFT JOIN work_center_location wcl
             ON wcl.id = city_tbl.def_work_center_id
            
             LEFT JOIN work_center_group wcg
             ON wcg.id = wcl.work_center_group_id
             
              WHERE p.salesman_code=d.sm_code
              AND p.salesman_code=h.sm_code
              AND {where_sql}

            ORDER BY
                p.salesman_code,
                p.ref
        """

       #  query = f"""
       #         SELECT DISTINCT
       #          p.ref AS customer_code,
       #          p.name AS customer_name,
       #          COALESCE(cc.cc_desc, '') AS classification,
       #          '' AS region,
       #          COALESCE(p.city, '') AS city,
       #          p.res_maxinvoicedate,
       #          p.salesman_code AS sm_code,
       #          COALESCE(d.sm_name, '') AS sm_name
       #      FROM res_partner p
       #      LEFT JOIN sl_salesmandesc d
       #          ON d.sm_code = p.salesman_code
       #          AND d.sm_lang = '1'
       #      LEFT JOIN customer c
       #          ON c.cst_no = p.ref
       #      LEFT JOIN t_cstclassificationdesc cc
       #          ON cc.cc_code = c.cst_cstclassification
       #      WHERE p.active = TRUE
       #        AND COALESCE(p.ref, '') <> ''
       #      ORDER BY
       #          p.salesman_code,
       #          p.ref;
       # """

        _logger.info("Customer List Report SQL")
        _logger.info(query)
        _logger.info(params)

        self.env.cr.execute(query, params)

        rows = self.env.cr.dictfetchall()

        elapsed = round(time.time() - start_time, 3)

        _logger.info(
            "Customer List Report fetched %s records in %s seconds",
            len(rows),
            elapsed
        )

        if not rows:
            raise UserError(
                _("No customer records found for selected filters.")
            )

        grouped = OrderedDict()

        for row in rows:

            sm_code = row.get('sm_code') or ''

            if sm_code not in grouped:
                grouped[sm_code] = {
                    'sm_code': sm_code,
                    'sm_name': row.get('sm_name') or '',
                    'sm_stype':row.get('sm_stype') or '',
                    'customers': []
                }

            grouped[sm_code]['customers'].append(row)

        return grouped, rows
    # ==========================================================
    # FILTER LABELS
    # ==========================================================

    def _get_filter_labels(self):
        self.ensure_one()

        return {
            'Customers':
                ', '.join(
                    self.customer_ids.mapped('name')
                ) if self.customer_ids else 'All'
        }
    # ==========================================================
    # PDF REPORT
    # ==========================================================

    def action_print_pdf(self):
        self.ensure_one()

        grouped, flat_rows = self._build_report_data()

        data = {
            'grouped': grouped,
            'flat_rows': flat_rows,
            'filters': self._get_filter_labels(),

            'company_dict': {
                'name': self.env.company.name,
                'street': self.env.company.street or '',
                'city': self.env.company.city or '',
                'phone': self.env.company.phone or '',
                'logo': self.env.company.logo,
            },

            'user_name': self.env.user.name,

            'printed_at':
                fields.Datetime.now().strftime(
                    '%d-%m-%Y %H:%M:%S'
                ),

            'wizard_id': self.id,
        }

        return self.env.ref(
            'hhs_loyalty_management.action_report_customer_list'
        ).report_action(
            self,
            data=data
        )

    def action_send_customer_list_email(self):
        self.ensure_one()

        grouped, flat_rows = self._build_report_data()

        report_action = self.env.ref(
            'hhs_loyalty_management.action_report_customer_list'
        )

        pdf_content, _ = report_action._render_qweb_pdf(self.id)

        attachment = self.env['ir.attachment'].create({
            'name': 'Customer_List_Report.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })

        # ADD THE CONFIG PARAMETER CODE HERE

        params = self.env['ir.config_parameter'].sudo()

        email_to = params.get_param(
            'hhs_loyalty_management.customer_list_email_ids'
        )

        email_cc = params.get_param(
            'hhs_loyalty_management.customer_list_cc_email_ids'
        )

        mail_content = params.get_param(
            'hhs_loyalty_management.customer_list_mail_content'
        )

        body_html = f"""
              <p>Dear Sir/Madam,</p>

              <p>{mail_content}</p>

              <p>Regards,<br/>
              {self.env.user.name}</p>
          """

        self.env['mail.mail'].create({
            'subject': 'Customer List Report',
            'body_html': body_html,
            'email_from': self.env.user.email,
            'email_to': email_to,
            'email_cc': email_cc,
            'attachment_ids': [(4, attachment.id)],
        }).send()

        return True

    # def action_send_customer_list_email(self):
    #     self.ensure_one()
    #
    #     grouped, flat_rows = self._build_report_data()
    #
    #     report_action = self.env.ref(
    #         'hhs_loyalty_management.action_report_customer_list'
    #     )
    #
    #     pdf_content, _ = report_action._render_qweb_pdf(self.id)
    #
    #     attachment = self.env['ir.attachment'].create({
    #         'name': 'Customer_List_Report.pdf',
    #         'type': 'binary',
    #         'datas': base64.b64encode(pdf_content),
    #         'mimetype': 'application/pdf',
    #     })
    #
    #     salesman_codes = list(grouped.keys())
    #
    #     for sm_code in salesman_codes:
    #
    #         salesman = self.env['sl.salesman'].search([
    #             ('sm_code', '=', sm_code)
    #         ], limit=1)
    #
    #         if not salesman:
    #             continue
    #
    #         # Option 1: Direct email field
    #         email_to = salesman.email
    #
    #         # Option 2: From Odoo user
    #         if not email_to and salesman.sm_userid:
    #             user = self.env['res.users'].search([
    #                 ('login', '=', salesman.sm_userid)
    #             ], limit=1)
    #
    #             email_to = user.email
    #
    #         if not email_to:
    #             continue
    #
    #         subject = f"Customer List Report - {sm_code}"
    #
    #         body_html = f"""
    #             <p>Dear {salesman.sm_name},</p>
    #
    #             <p>
    #                 Please find attached the Customer List Report.
    #             </p>
    #
    #             <p>
    #                 <b>Salesman Code:</b> {salesman.sm_code}<br/>
    #                 <b>Salesman Type:</b> {salesman.sm_type or ''}
    #             </p>
    #
    #             <p>
    #                 Regards,<br/>
    #                 {self.env.user.name}
    #             </p>
    #         """
    #
    #         mail = self.env['mail.mail'].create({
    #             'subject': subject,
    #             'body_html': body_html,
    #             'email_from': self.env.user.email,
    #             'email_to': email_to,
    #             'attachment_ids': [(4, attachment.id)],
    #         })
    #
    #         mail.send()