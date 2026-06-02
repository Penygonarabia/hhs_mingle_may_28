# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import qrcode
from io import BytesIO
from num2words import num2words

from translate import Translator

def generate_qr_code(value):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,
        border=4,
    )
    qr.add_data(value)
    qr.make(fit=True)
    img = qr.make_image()
    stream = BytesIO()
    img.save(stream, format="PNG")
    qr_img = base64.b64encode(stream.getvalue())
    return qr_img


class ContractInvoiceReport(models.AbstractModel):
    _name = 'report.machine_repair_management.contract_invoice_report'
    _description = 'Contract Invoice Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Main method to get report values for the invoice template"""

        # Get the account move record
        docs = self.env['account.move'].browse(docids)

        if not docs:
            raise UserError(_("No invoice found!"))

        # We'll handle multiple invoices but typically it's one
        report_data = []

        for move in docs:
            # Get product lines from invoice lines
            product_lines = self._get_product_lines(move)

            # contract_no = ''
            # invoice_cycle = ''
            #
            # if move.subscription_contract_id:
            #     contract_no = move.subscription_contract_id.name
            #     invoice_cycle = move.subscription_contract_id.number_of_installments
            # elif move.invoice_origin:
            #     contract_no = move.invoice_origin
            contract = move.subscription_contract_id

            total = contract.number_of_installments if contract else 0

            invoices = self.env['account.move'].search([
                ('subscription_contract_id', '=', contract.id)
            ], order="invoice_date, id") if contract else self.env['account.move']

            current = invoices.ids.index(move.id) + 1 if move.id in invoices.ids else 0

            # Get totals
            totals = self._get_totals(move, product_lines)

            amount_words_en = totals['amount_words_en']
            amount_words_ar = totals['amount_words_ar']

            # Prepare company information
            company_info = self._get_company_info(move.company_id)

            # Prepare customer information
            customer_info = self._get_customer_info(move.partner_id)

            # Generate QR code for invoice
            # qr_image = self._generate_qr_code(move)
            qr_image = move.qr_image
            # Prepare the document data
            doc_data = {
                # Company Information
                'company_name': company_info['name'],
                'company_address': company_info['address'],
                'company_building_number': company_info['building_number'],
                'company_street_name': company_info['street_name'],
                'district': company_info['district'],
                'company_city': company_info['city'],
                'company_country': company_info['country'],
                'company_zip_code': company_info['zip_code'],
                'company_additional_number': company_info['additional_number'],
                'company_vat': company_info['vat'],
                'company_other_id': company_info['other_id'],
                'warehouse_id': self._get_warehouse_name(move),

                # Invoice Information
                'invoice_no': move.name or '/',
                'invoice_date': move.invoice_date.strftime('%d/%m/%Y') if move.invoice_date else '',
                'name': move.ref or move.name or '/',  # Job Card No
                'control_card_no': move.ref or '',  # CIC Ref No

                # Customer Information
                'customer_name': customer_info['name'],
                'customer_no': customer_info['customer_no'],
                'address': customer_info['address'],
                'building_no': customer_info['building_number'],
                'street_name': customer_info['street_name'],
                'district': customer_info['district'],
                'city': customer_info['city'],
                'country': customer_info['country'],
                'zipcode': customer_info['zip_code'],
                'additional_number': customer_info['additional_number'],
                'vat': customer_info['vat'],
                'other_id': customer_info['other_id'],

                # QR Code
                'qr_image': qr_image,

                # Lines and Totals
                'product_lines': product_lines,
                'totals': totals,
            }

            report_data.append(doc_data)

        return {
            'docs': docs,
            'jobs': report_data,
            'current_installment': current,
            'total_installments': total,
            'res_company': docs.company_id if docs else self.env.company,
            'product_lines': product_lines if docs else [],
            'totals': totals if docs else [],
            'amount_words_en': amount_words_en,
            'amount_words_ar': amount_words_ar,
        }

    def _get_product_lines(self, move):
        """Get product lines from invoice lines"""
        product_lines = []

        for line in move.invoice_line_ids:
            # Get product details
            product = line.product_id

            # Calculate unit price, discount, net unit price
            unit_price = line.price_unit
            discount_percent = line.discount
            discount_amount = (unit_price * discount_percent / 100) if discount_percent else 0
            net_unit_price = unit_price - discount_amount
            quantity = line.quantity
            extended_price = net_unit_price * quantity
            vat_percent = line.tax_ids.amount if line.tax_ids else 0
            vat_amount = (extended_price * vat_percent / 100) if vat_percent else 0
            total = extended_price + vat_amount

            # Get Arabic name if available
            arabic_name = product.name_ar if hasattr(product, 'name_ar') and product.name_ar else ''

            product_lines.append({
                'stock_group': product.categ_id.name if product.categ_id else '',
                'stock_number': product.default_code or '',
                'description': line.name or product.name,
                'arabic_name': arabic_name,
                'qty': quantity,
                'unit_price': unit_price,
                'unit_discount': discount_amount,
                'net_unit_price': net_unit_price,
                'extended_price': extended_price,
                'vat_percent': vat_percent,
                'vat_amount': vat_amount,
                'total': total,
            })

        return product_lines



    def _get_totals(self, move, product_lines):
        total_extended_price = 0.0
        total_vat_amt = 0.0
        grand_total = 0.0

        for line in product_lines:
            total_extended_price += line['extended_price']
            total_vat_amt += line['vat_amount']
            grand_total += line['total']

        # English amount in words
        amount_words_en = self._amount_to_words_en(grand_total)

        # Arabic amount in words
        amount_words_ar = self._amount_to_words_ar(grand_total)

        return {
            'total_extended_price': total_extended_price,
            'total_vat_amt': total_vat_amt,
            'grand_total': grand_total,
            'amount_words_en': amount_words_en,
            'amount_words_ar': amount_words_ar,
        }

    def _get_company_info(self, company):
        """Get company information formatted for the report"""
        # Get building number and street from street field
        street_parts = company.street.split(',') if company.street else ['', '']
        building_number = street_parts[0] if street_parts else ''
        street_name = street_parts[1] if len(street_parts) > 1 else ''

        # Get additional number from street2
        additional_number = company.street2 or ''

        # Get district from city or other field
        district = company.city or ''

        # Get other ID (company registration number)
        other_id = company.company_registry or ''

        return {
            'name': company.name,
            'address': company.street or '',
            'building_number': building_number,
            'street_name': street_name,
            'district': district,
            'city': company.city or '',
            'country': company.country_id.name if company.country_id else '',
            'zip_code': company.zip or '',
            'additional_number': additional_number,
            'vat': company.vat or '',
            'other_id': other_id,
        }

    def _get_customer_info(self, partner):
        """Get customer information formatted for the report"""
        # Get building number and street from street field
        street_parts = partner.street.split(',') if partner.street else ['', '']
        building_number = street_parts[0] if street_parts else ''
        street_name = street_parts[1] if len(street_parts) > 1 else ''

        # Get additional number from street2
        additional_number = partner.street2 or ''

        # Get district from city or other field
        district = partner.city or ''

        # Get customer number from ref or other field
        customer_no = partner.ref or ''

        # Get other ID
        other_id = partner.company_registry or ''

        return {
            'name': partner.name,
            'customer_no': customer_no,
            'address': partner.street or '',
            'building_number': building_number,
            'street_name': street_name,
            'district': district,
            'city': partner.city or '',
            'country': partner.country_id.name if partner.country_id else '',
            'zip_code': partner.zip or '',
            'additional_number': additional_number,
            'vat': partner.vat or '',
            'other_id': other_id,
        }

    def _get_warehouse_name(self, move):
        """Get warehouse name from the invoice or related objects"""
        # Try to get warehouse from invoice lines
        for line in move.invoice_line_ids:
            if line.product_id and line.product_id.product_tmpl_id:
                # You might have a warehouse field on product or you can get from stock moves
                pass

        # Return default or empty warehouse name
        # You can customize this based on your actual warehouse field
        return move.warehouse_id.name if hasattr(move, 'warehouse_id') and move.warehouse_id else ''

    # def _generate_qr_code(self, move):
    #     """Generate QR code for the invoice"""
    #     try:
    #         # Prepare QR code data based on your requirements
    #         qr_data = {
    #             'invoice_number': move.name,
    #             'invoice_date': str(move.invoice_date) if move.invoice_date else '',
    #             'total_amount': move.amount_total,
    #             'vat_number': move.company_id.vat or '',
    #             'customer': move.partner_id.name,
    #         }
    #
    #         # Convert to string format (you can customize the format)
    #         qr_string = f"Invoice: {move.name}\nDate: {move.invoice_date}\nTotal: {move.amount_total}\nVAT: {move.company_id.vat}"
    #
    #         # Generate QR code
    #         qr = qrcode.QRCode(version=1, box_size=10, border=4)
    #         qr.add_data(qr_string)
    #         qr.make(fit=True)
    #
    #         img = qr.make_image(fill_color="black", back_color="white")
    #
    #         # Convert to base64
    #         buffer = BytesIO()
    #         img.save(buffer, format='PNG')
    #         qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    #
    #         return qr_base64
    #     except Exception as e:
    #         # Return None if QR generation fails
    #         return None

    def _amount_to_words_en(self, amount):
        try:
            amount = float(amount)

            integer_part = int(amount)
            decimal_part = int(round((amount - integer_part) * 100))

            words = num2words(integer_part, lang='en').title()

            if decimal_part:
                words += f" And {num2words(decimal_part, lang='en').title()} Halalas"

            return f"{words} Saudi Riyals Only"

        except Exception:
            return "Zero Saudi Riyals Only"

    def _amount_to_words_ar(self, amount):
        try:
            amount = float(amount)

            integer_part = int(amount)
            decimal_part = int(round((amount - integer_part) * 100))

            words = num2words(integer_part, lang='ar')

            if decimal_part:
                words += f" و {num2words(decimal_part, lang='ar')} هللة"

            return f"{words} ريال سعودي فقط"

        except Exception:
            return "صفر ريال سعودي فقط"


    def _convert_to_arabic_words(self, number):
        """Convert number to Arabic words - Basic implementation"""
        # This is a simplified version. You'll need a complete implementation
        # Or use a library like arabic_num2words

        arabic_numbers = {
            0: 'صفر', 1: 'واحد', 2: 'اثنان', 3: 'ثلاثة', 4: 'أربعة',
            5: 'خمسة', 6: 'ستة', 7: 'سبعة', 8: 'ثمانية', 9: 'تسعة',
            10: 'عشرة', 20: 'عشرون', 30: 'ثلاثون', 40: 'أربعون',
            50: 'خمسون', 60: 'ستون', 70: 'سبعون', 80: 'ثمانون',
            90: 'تسعون', 100: 'مائة', 200: 'مائتان', 300: 'ثلاثمائة',
            400: 'أربعمائة', 500: 'خمسمائة', 600: 'ستمائة',
            700: 'سبعمائة', 800: 'ثمانمائة', 900: 'تسعمائة',
            1000: 'ألف', 2000: 'ألفان', 3000: 'ثلاثة آلاف'
        }

        if number <= 10:
            return arabic_numbers.get(number, str(number))
        elif number < 100:
            tens = (number // 10) * 10
            units = number % 10
            if units == 0:
                return arabic_numbers.get(tens, str(tens))
            else:
                return f"{arabic_numbers.get(units, str(units))} و{arabic_numbers.get(tens, str(tens))}"
        elif number < 1000:
            hundreds = (number // 100) * 100
            rest = number % 100
            if rest == 0:
                return arabic_numbers.get(hundreds, str(hundreds))
            else:
                return f"{arabic_numbers.get(hundreds, str(hundreds))} و{self._convert_to_arabic_words(rest)}"
        else:
            thousands = number // 1000
            rest = number % 1000
            if rest == 0:
                return f"{self._convert_to_arabic_words(thousands)} {arabic_numbers.get(1000, 'ألف')}"
            else:
                return f"{self._convert_to_arabic_words(thousands)} {arabic_numbers.get(1000, 'ألف')} و{self._convert_to_arabic_words(rest)}"

class AccountMove(models.Model):
    _inherit = 'account.move'

