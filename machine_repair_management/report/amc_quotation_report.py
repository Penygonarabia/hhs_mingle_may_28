from odoo import api, models
from datetime import datetime
import html


class ReportAMCQuotation(models.AbstractModel):
    _name = 'report.machine_repair_management.report_saleorder_amcquotation'
    _description = 'AMC Quotation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['service.sale.order'].browse(docids)
       
        amc_quotation_list = []
        scopes_of_work = []
        payments = []
        custom_texts = []

        total_qty = 0.0
        emergency_visit = 0.0

        for rec in docs:
            

            # ------------------ AMC QUOTATION ------------------
            for line in rec.service_sale_order_line_ids:
                ### commented on May 12 2026 because decimal precison
                # vals = {
                #     'unit_type': line.product_id.name,
                #     'description': dict(line.contract_type_id._fields['contract_category'].selection).get(
                #         line.contract_type_id.contract_category, ''
                #     ),
                #     'no_of_visits_per_year': line.no_of_visits_per_year or 0.0,
                #     'no_of_visits': line.no_of_emergency_visit or 0.0,
                #     'Qty': line.product_qty or 0.0,
                #     'total': line.total_selling_price or 0.0,
                #     'vat': line.vat or 0.0,
                #     'grand_total': line.total or 0.0,
                #     # 'no_of_emergency_visits': line.no_of_emergency_visit or 0.0,
                #     'brand': line.brand_category_id.name if line.brand_category_id else '',
                #     'unit_selling_price': line.per_unit_selling_price or 0.00,
                # }
                
                qty    = line.product_qty or 0.0
                visits = line.no_of_visits_per_year or 0.0
    
                # ✅ Use stored fields directly — no back-calculation
                per_unit = line.per_unit_selling_price or 0.0          # already 3dp
                total    = round(per_unit * qty * visits, 3)            # guaranteed match
    
                vals = {
                    'unit_type': line.product_id.name,
                    'description': dict(
                        line.contract_type_id._fields['contract_category'].selection
                    ).get(line.contract_type_id.contract_category, ''),
                    'no_of_visits_per_year': visits,
                    'no_of_visits':          line.no_of_emergency_visit or 0.0,
                    'Qty':                   qty,
                    'unit_selling_price':    per_unit,   # 3dp — display as-is
                    'total':                 total,       # per_unit × qty × visits
                    'vat':                   line.vat or 0.0,
                    'grand_total':           line.total or 0.0,
                    'brand':                 line.brand_category_id.name if line.brand_category_id else '',
                }
                amc_quotation_list.append(vals)

                total_qty += line.product_qty or 0.0
                emergency_visit += line.no_of_emergency_visit or 0.0

            # ------------------ SCOPE OF WORK (SQL BASED) ------------------

            # service_lines = rec.service_sale_order_line_ids.filtered(
            #     lambda l: l.product_id and l.product_id.detailed_type == 'service'
            # )
            # print("service_lines}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}", service_lines)

            doc_scopes = []

            if 'pm_checklist_ids' in rec._fields:
                service_lines = rec.pm_checklist_ids.filtered(lambda l: l.is_selected)
            else:
                service_lines = []

            for line in service_lines:
                unit_type_id = line.service_unit_type_id.id
                service_type = line.service_type_id  # 'major' / 'minor'

              

                query = '''
                    SELECT
                        ps.service_type_id,
                        ps.service_type_ar,
                        ps.service_unit_sub_type_id,
                        psl.parameter,
                        psl.parameter_ar,
                        psl.description,
                        psl.description_ara,
                        ps.sort_order_header,
                        pp.product_arabic_name
                    FROM pm_service ps
                    JOIN pm_service_line psl ON ps.id = psl.pm_service_id
                    JOIN product_product pp ON pp.id = ps.service_unit_type_id
                    WHERE ps.service_unit_type_id = %s
                    AND ps.service_type_id = %s
                    AND psl.active = 'true'
                    ORDER BY
                        ps.sort_order_header,
                        CASE
                            WHEN psl.parameter = 'services' THEN 1
                            WHEN psl.parameter = 'physical_inspection' THEN 2
                            WHEN psl.parameter = 'visual_inspection' THEN 3
                            WHEN psl.parameter = 'parameter_measurement' THEN 4
                            ELSE 5
                        END,
                        psl.sno
                '''

                self.env.cr.execute(query, (unit_type_id, service_type))
                res = self.env.cr.dictfetchall()

                

                grouped = {}

                for row in res:

                    service_type_val = row.get('service_type_id') or 'major'
                    sort_order = row.get('sort_order_header') or 0

                    st_en = {
                        'major': 'Major',
                        'minor': 'Minor',
                        'both': 'Major/Minor'
                    }.get(service_type_val, 'major')

                    st_ar = {
                        'major': 'رئيسي',
                        'minor': 'ثانوي',
                        'both': 'ثانوي/رئيسي'
                    }.get(service_type_val, 'رئيسي')

                    sub_type = row.get('service_unit_sub_type_id') or ''

                    sub_type_map_en = {
                        'indoor': 'Indoor',
                        'outdoor': 'Outdoor'
                    }

                    sub_type_map_ar = {
                        'indoor': 'داخلي',
                        'outdoor': 'خارجي'
                    }

                    sub_type_en = sub_type_map_en.get(sub_type, '')
                    sub_type_ar = sub_type_map_ar.get(sub_type, '')

                    param_en = (row.get('parameter') or 'services').replace('_', ' ').title()
                    param_ar = row.get('parameter_ar') or 'الخدمات'

                    desc_en = row.get('description') or ''
                    desc_ar = row.get('description_ara') or ''

                    # UNIQUE KEY
                    group_key = f"{sort_order}_{service_type_val}"

                    # CREATE SERVICE GROUP
                    if group_key not in grouped:
                        grouped[group_key] = {
                            'sort_order': sort_order,
                            'service_en': st_en,
                            'service_ar': st_ar,
                            'params': {}
                        }

                    # CREATE PARAM GROUP
                    if param_en not in grouped[group_key]['params']:
                        grouped[group_key]['params'][param_en] = {
                            'param_en': param_en,
                            'param_ar': param_ar,
                            'lines': []
                        }

                    # APPEND LINES
                    grouped[group_key]['params'][param_en]['lines'].append({
                        'en': desc_en,
                        'ar': desc_ar
                    })

                # CONVERT TO LIST
                grouped_list = []

                for st in grouped.values():
                    grouped_list.append({
                        'sort_order': st['sort_order'],
                        'service_en': st['service_en'],
                        'service_ar': st['service_ar'],
                        'params': list(st['params'].values())
                    })

                # UNIT NAME
                if grouped_list:
                    base_unit_name = line.service_unit_type_id.name or ''

                    full_unit_name = (
                        f"{base_unit_name} - {sub_type_en}"
                        if sub_type_en else base_unit_name
                    )

                    full_unit_name_ar = (
                        f"{row.get('product_arabic_name') or ''} - {sub_type_ar}"
                        if sub_type_ar
                        else (row.get('product_arabic_name') or '')
                    )

                  

                    doc_scopes.append({
                        'unit_type': full_unit_name,
                        'unit_type_ar': full_unit_name_ar,
                        'services': grouped_list,

                        'hide_unit_name': bool(
                            self.env['pm.service'].search([
                                ('service_unit_type_id', '=', line.service_unit_type_id.id),
                                ('service_unit_sub_type_id', '=', line.unit_sub_type_id),
                                ('service_type_id', '=', line.service_type_id),
                            ], limit=1).print_always_default
                        ),
                    })
                    
                # if grouped_list:
                #     base_unit_name = line.service_unit_type_id.name or ''
                #
                #     full_unit_name = (
                #         f"{base_unit_name} - {sub_type_en}"
                #         if sub_type_en else base_unit_name
                #     )
                #
                #     full_unit_name_ar = (
                #         f"{row.get('product_arabic_name') or ''} - {sub_type_ar}"
                #         if sub_type_ar
                #         else (row.get('product_arabic_name') or '')
                #     )
                #
                #     print("product_arabic_name:", row.get('product_arabic_name'))
                #
                #     doc_scopes.append({
                #         'unit_type': full_unit_name,
                #         'unit_type_ar': full_unit_name_ar,
                #         'services': grouped_list
                #     })

                # grouped = {}
                #
                # for row in res:
                #     service_type_val = row.get('service_type_id') or 'major'
                #
                #     # ✅ English
                #     st_en = service_type_val.capitalize()
                #
                #     # ✅ Arabic (fixed mapping)
                #     st_ar = {
                #         'major': 'رئيسي',
                #         'minor': 'ثانوي',
                #         'both': 'كلاهما'
                #     }.get(service_type_val, 'رئيسي')
                #
                #     # ✅ Sub type from SQL (IMPORTANT)
                #     sub_type = row.get('service_unit_sub_type_id') or ''
                #
                #     sub_type_map_en = {
                #         'indoor': 'Indoor',
                #         'outdoor': 'Outdoor'
                #     }
                #
                #     sub_type_map_ar = {
                #         'indoor': 'داخلي',
                #         'outdoor': 'خارجي'
                #     }
                #
                #     sub_type_en = sub_type_map_en.get(sub_type, '')
                #     sub_type_ar = sub_type_map_ar.get(sub_type, '')
                #
                #     # ✅ Parameters
                #     param_en = (row.get('parameter') or 'services').replace('_', ' ').title()
                #     param_ar = row.get('parameter_ar') or 'الخدمات'
                #
                #     desc_en = row.get('description') or ''
                #     desc_ar = row.get('description_ara') or ''
                #
                #     # Create service group
                #     if st_en not in grouped:
                #         grouped[st_en] = {
                #             'service_en': st_en,
                #             'service_ar': st_ar,
                #             'params': {}
                #         }
                #
                #     # Create parameter group
                #     if param_en not in grouped[st_en]['params']:
                #         grouped[st_en]['params'][param_en] = {
                #             'param_en': param_en,
                #             'param_ar': param_ar,
                #             'lines': []
                #         }
                #
                #     grouped[st_en]['params'][param_en]['lines'].append({
                #         'en': desc_en,
                #         'ar': desc_ar
                #     })
                #
                #     # Convert dict → list
                # grouped_list = []
                # for st in grouped.values():
                #     grouped_list.append({
                #         'service_en': st['service_en'],
                #         'service_ar': st['service_ar'],
                #         'params': list(st['params'].values())
                #     })
                #
                # # ✅ Build Unit + Subtype name (OUTSIDE row loop)
                # if grouped_list:
                #     base_unit_name = line.service_unit_type_id.name.replace('[SPLT] Split - ', '')
                #
                #     # use last row's subtype (same for all rows)
                #     sub_type_en = sub_type_map_en.get(sub_type, '')
                #     sub_type_ar = sub_type_map_ar.get(sub_type, '')
                #
                #     full_unit_name = f"{base_unit_name} - {sub_type_en}" if sub_type_en else base_unit_name
                #     full_unit_name_ar = (
                #         f"{line.service_unit_type_id.product_arabic_name or ''} - {sub_type_ar}"
                #         if sub_type_ar else (line.service_unit_type_id.product_arabic_name or '')
                #     )
                #
                #     # ✅ Prevent duplicates
                #     existing = next((d for d in doc_scopes if d['unit_type'] == full_unit_name), None)
                #
                #     if existing:
                #         existing['services'].extend(grouped_list)
                #     else:
                #         doc_scopes.append({
                #             'unit_type': full_unit_name,
                #             'unit_type_ar': full_unit_name_ar,
                #             'services': grouped_list
                #         })

            # Final assignment
            #scopes_of_work.extend(doc_scopes)
            # SORT DOC SCOPES
            doc_scopes = sorted(
                doc_scopes,
                key=lambda x: (
                    x['services'][0].get('sort_order', 999)
                    if x.get('services') else 999
                )
            )

            # FINAL ASSIGNMENT
            scopes_of_work.extend(doc_scopes)

            
            #  doc_scopes = []
            #
            #  service_lines = rec.pm_checklist_ids.filtered(lambda l: l.is_selected)
            #  print("++++++++++++++++++++++++++++++++++++++++++++Service_line",service_lines)
            #
            #  for line in service_lines:
            #      unit_type_id = line.service_unit_type_id.id
            #      #service_type = line.service_type_id
            #
            #      print("unit_type_id", unit_type_id)
            #
            #
            #      query = '''
            #          SELECT
            #              ps.service_type_id,
            #              ps.service_type_ar,
            #              psl.parameter,
            #              psl.parameter_ar,
            #              psl.description,
            #              psl.description_ara
            #          FROM pm_service ps
            #          JOIN pm_service_line psl ON ps.id = psl.pm_service_id
            #          WHERE ps.service_unit_type_id = %s
            #          ORDER BY
            #              psl.service_type,
            #              CASE
            #                  WHEN psl.parameter = 'services' THEN 1
            #                  WHEN psl.parameter = 'physical_inspection' THEN 2
            #                  WHEN psl.parameter = 'visual_inspection' THEN 3
            #                  WHEN psl.parameter = 'parameter_measurement' THEN 4
            #                  ELSE 5
            #              END,
            #              psl.sno
            #      '''
            #
            #      self.env.cr.execute(query, (unit_type_id,))
            #      res = self.env.cr.dictfetchall()
            #
            #      print("UNIT ID+++++++++++++++++++++++++++++:", unit_type_id)
            #      print("RESULT:++++++++++++++++++++++++++++++", res)
            #      # grouped = {}
            #      grouped = {}
            #
            #      for row in res:
            #          st_en = (row.get('service_type_id') or 'Major').capitalize()
            #          st_ar = (row.get('service_type_ar') or 'Major').capitalize()
            #
            #          param_en = (row.get('parameter') or 'services').replace('_', ' ').title()
            #          param_ar = (row.get('parameter_ar') or 'services').replace('_', ' ').title()
            #
            #          desc_en = row.get('description') or ''
            #          desc_ar = row.get('description_ara') or ''
            #
            #          # Create service group
            #          if st_en not in grouped:
            #              grouped[st_en] = {
            #                  'service_en': st_en,
            #                  'service_ar': st_ar,
            #                  'params': {}
            #              }
            #
            #          # Create parameter group
            #          if param_en not in grouped[st_en]['params']:
            #              grouped[st_en]['params'][param_en] = {
            #                  'param_en': param_en,
            #                  'param_ar': param_ar,
            #                  'lines': []
            #              }
            #
            #          # Add description lines
            #          grouped[st_en]['params'][param_en]['lines'].append({
            #              'en': desc_en,
            #              'ar': desc_ar
            #          })
            #      grouped_list = []
            #
            #      for st in grouped.values():
            #          param_list = list(st['params'].values())
            #
            #          grouped_list.append({
            #              'service_en': st['service_en'],
            #              'service_ar': st['service_ar'],
            #              'params': param_list
            #          })
            #      if grouped_list:
            #          doc_scopes.append({
            #              'unit_type': line.service_unit_type_id.name.replace('[SPLT] Split - ', ''),
            #              'unit_type_ar':line.service_unit_type_id.product_arabic_name or '',
            #              'services': grouped_list
            #          })
            #
            #  scopes_of_work.extend(doc_scopes)
            #  print("docccccccccccccccccccccccccccccccccc", doc_scopes)
            #  # scopes_of_work += doc_scopes

            # ------------------ TEXT FIELDS ------------------
            custom_texts.append({
                'terms': rec.terms_of_execution or '',
                'exclusions': rec.exclusions_text or '',
                'others': rec.others_text or '',
            })

            # ------------------ PAYMENTS ------------------
            payment_list = []
            payment_records = self.env['quotation.payment.term'].search([
                ('payment_order_id', '=', rec.id)
            ])

            # ------------------ USER DETAILS ------------------
        current_user = self.env.user
        employee = current_user.employee_ids[:1]

        user_details = {
            'name': current_user.name,
            'email': current_user.email or '',
            'job_title': employee.job_id.name if employee and employee.job_id else '',
            'phone': current_user.phone or '',
            'mobile': current_user.mobile or '',
            'signature': current_user.signature or current_user.name,
        }

        def convert_name(name):
            mapping = {
                'First': '1st',
                'Second': '2nd',
                'Third': '3rd',
                'Fourth': '4th',
                'Fifth': '5th',
                'Sixth': '6th',
                'Seventh': '7th',
                'Eighth': '8th',
                'Ninth': '9th',
                'Tenth': '10th',
                'Eleventh': '11th',
                'Twelfth': '12th',
            }
            for k, v in mapping.items():
                if k in name:
                    return name.replace(k, v)
            return name

        for pay in rec.payment_term_ids:

            formatted_date = ''
            if hasattr(pay, 'payment_date') and pay.payment_date:
                # formatted_date = pay.payment_date.strftime('%d-%B-%Y').lstrip('0')
                formatted_date = f"{pay.payment_date.day}-{pay.payment_date.strftime('%b-%Y')}"
            amount = 0
            if hasattr(pay, 'percentage') and pay.percentage:
                amount = (pay.percentage / 100.0) * rec.amount_total
            elif hasattr(pay, 'amount') and pay.amount:
                amount = pay.amount

            payments.append({
                'name': convert_name(pay.name).replace('%', '').strip(),
                'date': formatted_date,
                'amount': f"SAR {amount:,.2f}"
            })
        # ------------------ FINAL DATA ------------------
        rec = docs[0] if docs else None
        address = [
            rec.street.strip() if rec.street else "",
            rec.street2.strip() if rec.street2 else "",
            # rec.state_id.name.strip() if rec.state_id else "",
            rec.district_id.name.strip() if rec.district_id else "",
            rec.customer_city_id.name.strip() if rec.customer_city_id else "",
            rec.country_id.name.strip() if rec.country_id else "",
            rec.zip.strip() if rec.zip else "",
        ]
        site_address = ", ".join(filter(None, address))

        datas = {
            'quotation_no': rec.name if rec else '',
            'quotations': amc_quotation_list,
            'quotation_date': rec.service_sale_quotation_date.strftime(
                "%d-%m-%Y") if rec and rec.service_sale_quotation_date else '',
            'quotation_expiry_date': rec.date_expiry.strftime("%d-%b-%Y") if rec and rec.date_expiry else '',
            'company_name': rec.partner_name,
            'sub_total': rec.untaxed_amount or 0.0,
            'total_vat': rec.vat_amount or 0.0,
            'grand_total': rec.grand_total_amount or 0.0,
            'total_qty': int(total_qty),
            'company_symbol': rec.company_id.currency_id.name if rec else '',
            # 'address': rec.customer_address if rec else '',
            # 'address': rec.customer_address.replace(',', ', ') if rec and rec.customer_address else '',
            'address': site_address or '',
            'emergency_visit': int(emergency_visit),
            'att_to': rec.crm_id.contact_name if rec and rec.crm_id else '',
            'contact_no': rec.mobile if rec and rec.mobile else '',
            'scope_of_work': scopes_of_work,
            'scope_work': (rec.scope_of_work or '').replace('\n', '<br/>') if rec else '',
            # 'customer_name': rec.customer_name,
            'customer_name': rec.partner_name,
            'payment_advance': payments,
            # 'payment_date': payment_date,
            # 'amount':rec.amount,
            'others': rec.others,
            'name': rec.name,
            'property_type': rec.crm_id.type_of_property,
            'subject': rec.subject,
            'terms_of_execution': (rec.terms_of_execution or '').replace('\n', '<br/>') if rec else '',
            'exclusions_text': (rec.exclusions_text or '').replace('\n', '<br/>') if rec else '',
            'others_text': (rec.others_text or '').replace('\n', '<br/>') if rec else '',
            'user_name': user_details['name'],
            'signature': user_details['signature'],
        }
        
        return {
            'doc_ids': docids,
            'doc_model': 'service.sale.order',
            'docs': docs,
            'sub_total': rec.untaxed_amount,
            'total_vat': rec.vat_amount,
            'grand_total': rec.grand_total_amount,
            'scope_of_work': scopes_of_work,
            'total_qty': int(total_qty),
            **datas,

        }
