# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalAccount(CustomerPortal):
    """ Super customer portal and get count of contracts """

    def _prepare_home_portal_values(self, counters):
        """ Prepares values for the home portal """
        values = super()._prepare_home_portal_values(counters)

        user = request.env.user
        contract_model = request.env['subscription.contracts']
        is_admin = user.has_group('base.group_system')
        domain = []
        if not is_admin:
            partner_id = user.partner_id.id
            domain = [('partner_id', '=', partner_id)]

        contract_count = contract_model.search(domain)
        values['contract_count'] = len(contract_count)
        return values


class ContractsController(http.Controller):
    """ Sale contract in customer portal controller """

    @http.route(['/my/contracts'], type='http', auth='user', csrf=False,
                website=True)
    def portal_my_quotes(self):
        """ Displays Contracts in portal """
        user = request.env.user
        partner_id = user.partner_id.id
        is_admin = user.has_group('base.group_system')

        domain = []
        if not is_admin:
            domain = [('partner_id', '=', partner_id)]

        records = request.env['subscription.contracts'].search(domain)

        values = {
            'records': records,
        }
        return request.render(
            'sales_contract_and_recurring_invoices.tmp_contract_details',
            values)

    @http.route(['/contracts/<int:contract_id>/'], type='http', auth='user',
                csrf=False, website=True)
    def portal_manufacture(self, contract_id):
        """ Customer portal subscription contract """
        values = {
            'records': request.env['subscription.contracts'].browse(
                contract_id),
        }
        return request.render(
            'sales_contract_and_recurring_invoices.contract_details', values)
        
        
    
    @http.route(['/contract/download_word/<string:contract_ids>'], type='http', auth='user', website=True)
    def download_word(self, contract_ids, **kw):
        """ Download contract report as an editable Word document generated directly from data """
        ids = [int(i) for i in contract_ids.split(',')]
        contracts = request.env['subscription.contracts'].browse(ids)
        if not contracts.exists():
            return request.not_found()

        contract = contracts[0]

        import tempfile
        import os
        import subprocess
        import json
        from datetime import date

        def _get_char(obj, field, default=""):
            val = getattr(obj, field, False)
            return val if val else default

        def _get_float(obj, field, default=0.0):
            val = getattr(obj, field, False)
            return float(val) if val else default

        # Payment schedule lines
        payment_schedule = []
        for pline in contract.payment_schedule_line_ids:
            payment_schedule.append({
                'name': _get_char(pline, 'name'),
                'name_ara': getattr(pline, 'name_ara', _get_char(pline, 'name')),
                'payment_date': pline.payment_date.strftime('%d-%m-%Y') if pline.payment_date else '',
                'amount': _get_float(pline, 'amount')
            })

        # Contract lines
        contract_lines = []
        for line in contract.contract_line_ids:
            visits_word_en = contract.number_to_words(line.no_of_visits_per_year) if hasattr(contract, 'number_to_words') else str(line.no_of_visits_per_year)
            visits_word_ar = contract.number_to_words_ar(line.no_of_visits_per_year) if hasattr(contract, 'number_to_words_ar') else str(line.no_of_visits_per_year)

            contract_lines.append({
                'description': _get_char(line, 'description'),
                'no_of_visits_per_year': getattr(line, 'no_of_visits_per_year', 0),
                'product_name': line.product_id.name if line.product_id else '',
                'product_arabic_name': getattr(line.product_id, 'product_arabic_name', line.product_id.name) if line.product_id else '',
                'visits_words_en': visits_word_en,
                'visits_words_ar': visits_word_ar,
                'no_of_emergency_visit': getattr(line, 'no_of_emergency_visit', 0),
                'brand_name': line.brand_category_id.name if line.brand_category_id else '',
                'contract_type': line.contract_type_id.name if getattr(line, 'contract_type_id', False) else '',
                'qty_ordered': _get_float(line, 'qty_ordered')
            })

        # Payment term texts
        payment_term_en = ""
        payment_term_ar = ""
        if hasattr(contract, 'get_payment_term_text'):
            payment_term_en = contract.get_payment_term_text()
        if hasattr(contract, 'get_payment_term_text_ar'):
            payment_term_ar = contract.get_payment_term_text_ar()

        data = {
            'today': date.today().strftime('%d-%m-%Y'),
            'name': _get_char(contract, 'name'),
            'partner_name': _get_char(contract, 'partner_name'),
            'customer_name': _get_char(contract, 'customer_name'),
            'id_party': _get_char(contract, 'id_party'),
            'job_position': _get_char(contract, 'job_position'),
            'mobile_no': _get_char(contract, 'mobile_no'),
            'email': _get_char(contract, 'email'),
            'date_start': contract.date_start.strftime('%d-%m-%Y') if contract.date_start else '',
            'date_end': contract.date_end.strftime('%d-%m-%Y') if contract.date_end else '',
            'amount_total': _get_float(contract, 'amount_total'),
            'payment_term_text': payment_term_en,
            'payment_term_text_ar': payment_term_ar,
            'payment_schedule_lines': payment_schedule,
            'add_paid_service_price': _get_float(contract, 'add_paid_service_price'),
            'contract_lines': contract_lines,
            'service_coordinator_person': _get_char(contract, 'service_coordinator_person'),
            'service_coordinator_mobile': _get_char(contract, 'service_coordinator_mobile'),
            'contact_persons': _get_char(contract, 'contact_persons'),
            'contact_persons_mobile': _get_char(contract, 'contact_persons_mobile'),
            'additional_info': _get_char(contract, 'additional_info'),
            'site_address': _get_char(contract, 'site_address')
        }

        json_path = tempfile.mktemp(suffix=".json")
        docx_path = tempfile.mktemp(suffix=".docx")

        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)

            # script_path = r"d:\Installation_Folder\hhs_cloud_001\sales_contract_and_recurring_invoices\generate_contract_word.py"
            # clean_env = os.environ.copy()
            # clean_env.pop('PYTHONPATH', None)
            # clean_env.pop('PYTHONHOME', None)
            # python_exe = r"C:\Program Files\Odoo 17.0.20260525\python\python.exe"
            #
            # result = subprocess.run(
            #     [python_exe, '-E', script_path, json_path, docx_path],
            #     capture_output=True,
            #     text=True,
            #     env=clean_env
            # )
            
            import sys
            from pathlib import Path
            
            python_exe = sys.executable
            
            script_path = (
                Path(__file__).resolve().parent.parent /
                "generate_contract_word.py"
            )
            
            clean_env = os.environ.copy()
            clean_env.pop("PYTHONPATH", None)
            clean_env.pop("PYTHONHOME", None)
            
            result = subprocess.run(
                [
                    python_exe,
                    "-E",
                    str(script_path),
                    json_path,
                    docx_path,
                ],
                capture_output=True,
                text=True,
                env=clean_env,
            )
            
            if result.returncode != 0:
                raise Exception(
                    f"""
            Script : {script_path}
            
            STDOUT:
            {result.stdout}
            
            STDERR:
            {result.stderr}
            """
                )

            if result.returncode != 0:
                raise Exception(f"DOCX generation failed: {result.stderr}\n{result.stdout}")

            with open(docx_path, 'rb') as f:
                docx_content = f.read()

        finally:
            if os.path.exists(json_path):
                try: os.remove(json_path)
                except: pass
            if os.path.exists(docx_path):
                try: os.remove(docx_path)
                except: pass

        filename = f'Contract_Document_{contract.name or ids[0]}.docx'
        return request.make_response(
            docx_content,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )


    @http.route(['/contract/download_converted_word/<string:contract_ids>'], type='http', auth='user', website=True)
    def download_converted_word(self, contract_ids, **kw):
        """ Download contract report as an editable Word document generated via PDF-to-DOCX """
        ids = [int(i) for i in contract_ids.split(',')]
        from odoo.http import request
        import tempfile
        import subprocess
        import logging
        import sys
        import os

        _logger = logging.getLogger(__name__)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf_path = temp_pdf.name

        temp_docx_path = temp_pdf_path.replace('.pdf', '.docx')

        try:
            # Get path to helper script
            module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            helper_path = os.path.join(module_dir, 'pdf_to_docx_helper.py')

            # Run helper script with the correct python executable
            python_exe = sys.executable
            result = subprocess.run(
                [python_exe, helper_path, temp_pdf_path, temp_docx_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            with open(temp_docx_path, 'rb') as docx_file:
                docx_content = docx_file.read()

            contract_name = contracts[0].name if len(contracts) == 1 else "contracts"
            filename = f"Contract_Document_{contract_name}.docx"

            response = request.make_response(
                docx_content,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                    ('Content-Disposition', f'attachment; filename="{filename}"')
                ]
            )
            return response
        except subprocess.CalledProcessError as e:
            _logger.error("Failed to convert PDF to DOCX: %s\nStderr: %s", e, e.stderr)
            return request.not_found()
        except Exception as e:
            _logger.error("Failed to convert PDF to DOCX: %s", e)
            return request.not_found()
        finally:
            if os.path.exists(temp_pdf_path):
                try: os.unlink(temp_pdf_path)
                except: pass
            if os.path.exists(temp_docx_path):
                try: os.unlink(temp_docx_path)
                except: pass
    @http.route(['/contract/download_converted_word/<string:contract_ids>'], type='http', auth='user', website=True)
    def download_converted_word(self, contract_ids, **kw):
        """ Download contract report as an editable Word document generated via PDF-to-DOCX """
        ids = [int(i) for i in contract_ids.split(',')]
        
        from odoo.http import request
        import tempfile
        import subprocess
        import logging
        import sys
        import os
        
        _logger = logging.getLogger(__name__)

        contracts = request.env['subscription.contracts'].browse(ids)
        if not contracts.exists():
            return request.not_found()

        # Render PDF from report using correct Odoo 17 signature: _render_qweb_pdf(report_ref, res_ids=...)
        pdf_content, _ = request.env['ir.actions.report']._render_qweb_pdf('sales_contract_and_recurring_invoices.report_contract_document_template', res_ids=ids)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf_path = temp_pdf.name

        temp_docx_path = temp_pdf_path.replace('.pdf', '.docx')

        try:
            module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            helper_path = os.path.join(module_dir, 'pdf_to_docx_helper.py')

            python_exe = sys.executable
            subprocess.run(
                [python_exe, helper_path, temp_pdf_path, temp_docx_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            with open(temp_docx_path, 'rb') as docx_file:
                docx_content = docx_file.read()

            contract_name = contracts[0].name if len(contracts) == 1 else "contracts"
            filename = f"Contract_Document_{contract_name}.docx"

            response = request.make_response(
                docx_content,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                    ('Content-Disposition', f'attachment; filename="{filename}"')
                ]
            )
            return response
        except subprocess.CalledProcessError as e:
            _logger.error("Failed to convert PDF to DOCX: %s\nStderr: %s", e, e.stderr)
            return request.not_found()
        except Exception as e:
            _logger.error("Failed to convert PDF to DOCX: %s", e)
            return request.not_found()
        finally:
            if os.path.exists(temp_pdf_path):
                try: os.unlink(temp_pdf_path)
                except: pass
            if os.path.exists(temp_docx_path):
                try: os.unlink(temp_docx_path)
                except: pass    

    # @http.route(['/report/pdf/<int:contract_id>/'], type='http', auth='user',
    #             csrf=False, website=True)
    # def action_print_report(self, contract_id):
    #     """ Print subscription contract report """
    #     data = {
    #         'records': request.env['subscription.contracts'].browse(contract_id)
    #     }
    #     report = request.env.ref(
    #         'sales_contract_and_recurring_invoices.action_report_subscription_contracts')
    #     pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
    #         'sales_contract_and_recurring_invoices.action_report_subscription_contracts',
    #         [report.id], data=data)[0]
    #     pdfhttpheaders = [('Content-Type', 'application/pdf'),
    #                       ('Content-Length', len(pdf))]
    #     return request.make_response(pdf, headers=pdfhttpheaders)
