from odoo import models, fields, api
from datetime import datetime

class LoyaltyInvoiceProcessor(models.TransientModel):
    _name = 'loyalty.invoice.processor'
    _description = 'Loyalty Invoice Processor Wizard'

    start_date = fields.Date(string='Invoice Start Date')
    end_date = fields.Date(string='Invoice End Date')
    invoice_ids = fields.Many2many(
        'transaction.header',
        string='Select Invoices',
        domain="[('trnh_processed', '=', 'N')]"
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string='Select Customers'
    )
    available_partner_ids = fields.Many2many(
        'res.partner',
        relation='loyalty_invoice_processor_available_partner_rel',
        compute='_compute_available_partner_ids'
    )

    @api.depends('start_date', 'end_date')
    def _compute_available_partner_ids(self):
        for rec in self:
            domain = [('trnh_processed', '=', 'N')]
            if rec.start_date:
                domain.append(('trnh_date', '>=', rec.start_date.strftime('%Y%m%d')))
            if rec.end_date:
                domain.append(('trnh_date', '<=', rec.end_date.strftime('%Y%m%d')))
            
            # Fetch distinct customer numbers
            headers = self.env['transaction.header'].search_read(domain, ['trnh_cstno'])
            cstnos = list(set([h['trnh_cstno'] for h in headers if h.get('trnh_cstno')]))
            
            if cstnos:
                partners = self.env['res.partner'].search([('ref', 'in', cstnos)])
                rec.available_partner_ids = partners.ids
            else:
                rec.available_partner_ids = False

    def action_process_invoices(self):
        """
        Main entry point to select unprocessed transaction headers,
        process each with savepoints, and record results.
        """
        from odoo.exceptions import ValidationError
        
        if self and not ((self.start_date and self.end_date) or self.invoice_ids):
            raise ValidationError("You must provide either Invoice Dates (Start and End Date) or Select specific Invoices.")

        domain = [('trnh_processed', '=', 'N')]
        if self:
            if self.start_date:
                domain.append(('trnh_date', '>=', self.start_date.strftime('%Y%m%d')))
            if self.end_date:
                domain.append(('trnh_date', '<=', self.end_date.strftime('%Y%m%d')))
            if self.invoice_ids:
                domain.append(('id', 'in', self.invoice_ids.ids))
            if self.partner_ids:
                refs = [r for r in self.partner_ids.mapped('ref') if r]
                if refs:
                    domain.append(('trnh_cstno', 'in', refs))

        headers = self.env['transaction.header'].sudo().search(domain)
        success_invoices = []
        failed_invoices = []

        for header in headers:
            try:
                # Wrap each single invoice processing in a savepoint to ensure transactional isolation
                with self.env.cr.savepoint():
                    self._process_single_invoice(header)
                success_invoices.append(header.trnh_no or '')
            except Exception as e:
                failed_invoices.append(header.trnh_no or '')
                # Standard rollback is handled automatically by the context manager on exception.
                # Now record the error in the custom processed log table.
                self.env['loyalty.points.processed.log'].sudo().create({
                    'type': 'error',
                    'doc_type': str(header.trnh_type).zfill(2) if header.trnh_type else '',
                    'warehouse': header.trnh_whouse or '',
                    'reference': header.trnh_no or '',
                    'error_message': str(e),
                    'sql_statement': f"Failed to process transaction header: {header.trnh_no}",
                })

        msg_lines = [f"Processed {len(success_invoices)} successfully. Failed {len(failed_invoices)}."]
        if success_invoices:
            msg_lines.append(f"Success Invoices: {', '.join(success_invoices)}")
        if failed_invoices:
            msg_lines.append(f"Failed Invoices: {', '.join(failed_invoices)}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Invoice Processing Completed',
                'message': '\n'.join(msg_lines),
                'sticky': True,
            }
        }

    def _process_single_invoice(self, header):
        """
        Processes a single invoice header, its detail lines, computes loyalty & promo points,
        updates detail lines, creates audit records and logs execution.
        """
        # 1. Parse date (trnh_date is varchar in YYYYMMDD format)
        try:
            parsed_date = datetime.strptime(header.trnh_date, '%Y%m%d').date()
        except Exception:
            parsed_date = fields.Date.today()

        # 2. Find res.partner (using trnh_cstno as customer reference ref)
        partner = self.env['res.partner'].sudo().search([('ref', '=', header.trnh_cstno)], limit=1)
        if not partner:
            raise ValueError(f"Customer with code/reference '{header.trnh_cstno}' not found in Odoo.")

        # 3. Check if customer has loyalty active
        if not partner.activate_loyalty_feature:
            header.sudo().write({'trnh_processed': 'Y'})
            return

        # 4. Fetch detail lines
        details = self.env['transaction.details'].sudo().search([
            ('trnd_no', '=', header.trnh_no),
            ('trnd_whouse', '=', header.trnh_whouse)
        ])

        Invoice_points_vr = 0.0
        Invoice_points_promovr = 0.0
        Total_qty = 0.0
        Sales_value = 0.0
        Total_price = 0.0
        Total_disc = 0.0
        Total_spldisc = 0.0

        # Type '01' is Invoice (sign=1), others (like credit note) are deduction (sign=-1)
        doc_type_str = str(header.trnh_type).zfill(2) if header.trnh_type else ''
        sign = 1 if doc_type_str == '01' else -1

        for detail in details:
            # Find product variant by default_code (trnd_part)
            product = self.env['product.product'].sudo().search([('default_code', '=', detail.trnd_part)], limit=1)
            
            Items_loyalty_point_vr = 0.0
            if product:
                # Calculate regular points (Items_loyalty_point_vr)
                # Find customer-specific loyalty setup first
                loyalty_line = self.env['customer.loyalty.line'].sudo().search([
                    ('partner_id', '=', partner.id),
                    ('product_id', '=', product.id)
                ], limit=1)

                if loyalty_line:
                    Items_loyalty_point_vr = loyalty_line.loyalty_points
                else:
                    Items_loyalty_point_vr = product.cst_loyalty_points or 0.0

            # Only process lines that have regular loyalty points > 0
            if Items_loyalty_point_vr <= 0:
                continue

            # Calculate promotion points (Items_loyalty_point_promovr)
            # Convert parsed_date to string YYYY-MM-DD for correct ORM date comparison
            parsed_date_str = parsed_date.strftime('%Y-%m-%d')
            promotions = self.env['lp.setup.promotions'].sudo().search([
                ('promotion_start_date', '<=', parsed_date_str),
                ('promotion_end_date', '>=', parsed_date_str),
                ('active', '=', True)
            ], order='sort_order asc, select_all_customers asc, id desc')

            matching_promo = None
            promo_prod_line = None

            if product:
                # Pre-calculate all parent categories for the product
                parent_category_ids = []
                cat = product.categ_id
                while cat:
                    parent_category_ids.append(cat.id)
                    cat = cat.parent_id

                for promo in promotions:
                    # Check if product is in promotion (match by product)
                    prod_line = promo.applicable_product_ids.filtered(
                        lambda p: (p.product_name_id and p.product_name_id.id == product.id)
                    )
                    if not prod_line:
                        continue

                    # Check if customer is eligible
                    is_eligible = False
                    if promo.select_all_customers:
                        is_eligible = True
                    elif partner.customer_tier_id and partner.customer_tier_id.id in promo.tier_line_ids.mapped('tier_id').ids:
                        is_eligible = True
                    elif partner.id in promo.customer_line_ids.mapped('customer_id').ids:
                        is_eligible = True

                    if is_eligible:
                        matching_promo = promo
                        promo_prod_line = prod_line[0]
                        break

            Items_loyalty_point_promovr = 0.0
            promo_ref = ''

            if matching_promo and promo_prod_line:
                promo_ref = matching_promo.promotion_reference or ''
                promotional_value = promo_prod_line.promotional_value_per_qty or 0.0

                if promo_prod_line.promotion_type == 'multiplier':
                    Items_loyalty_point_promovr = (Items_loyalty_point_vr * promotional_value) - Items_loyalty_point_vr
                else:  # bonus
                    Items_loyalty_point_promovr = promotional_value

            # Calculate line totals
            qty = detail.trnd_qtyiss or 0.0
            Total_item_points_vr = Items_loyalty_point_vr * qty
            Total_item_points_promovr = Items_loyalty_point_promovr * qty

            Invoice_points_vr += Total_item_points_vr
            Invoice_points_promovr += Total_item_points_promovr

            Total_qty += qty
            
            # Sales value calculation: price - discount - special_discount
            price = detail.trnd_price or 0.0
            disc = detail.trnd_disc or 0.0
            spldisc = detail.trnd_cstspldisc or 0.0
            Total_price += price
            Total_disc += disc
            Total_spldisc += spldisc
            Sales_value += (qty * (price - disc - spldisc))

            # Write values back to detail line
            detail.sudo().write({
                'trnd_promoref': promo_ref,
                'trnd_regularpts': Total_item_points_vr,
                'trnd_bonuspts': Total_item_points_promovr
            })

# History creation moved to aggregated block (single record per invoice)

        # Create aggregated loyalty points history record
        doc_type = header.trnh_type if header.trnh_type in ('01', '02') else ('01' if sign == 1 else '02')
        adj_type = '+' if sign == 1 else '-'
        clph_type_val = 'I' if sign == 1 else 'O'

        self.env['customer.loyalty.points.history'].sudo().create({
            'clph_cstid': partner.id,
            'clph_cstcode': partner.ref or '',
            'clph_date': parsed_date,
            'clph_doctype': doc_type,
            'clph_docnumber': header.trnh_no,
            'clph_adjtype': adj_type,
            'clph_type': clph_type_val,
            'clph_whouse': header.trnh_whouse or '',
            'clph_regpoints': Invoice_points_vr,
            'clph_bonuspoints': Invoice_points_promovr,
            'clph_totalpoints': Invoice_points_vr + Invoice_points_promovr,
            'clph_note': '',
            'clph_uid': str(self.env.user.id),
            'clph_datetime': fields.Datetime.now(),
            'clph_reasoncode': '',
            'clph_promoref': '',
            'clph_export': 'False',
            'clph_redemptionprice': 0.0,
        })

        # Calculate and update partner loyalty balance
        if Invoice_points_vr > 0 or Invoice_points_promovr > 0:
            new_balance = partner.loyalty_points + (Invoice_points_vr + Invoice_points_promovr) * sign
            partner.sudo().write({'loyalty_points': new_balance})

        # 6. Mark header as processed
        header.sudo().write({'trnh_processed': 'Y'})

        # 7. Write success log record
        self.env['loyalty.points.processed.log'].sudo().create({
            'type': 'info',
            'doc_type': doc_type_str,
            'warehouse': header.trnh_whouse or '',
            'reference': header.trnh_no or '',
            'total_price': Total_price,
            'total_discount': Total_disc,
            'total_special_discount': Total_spldisc,
            'regular_points': Invoice_points_vr,
            'promotion_points': Invoice_points_promovr,
            'quantity': int(Total_qty * sign),
            'sales_value': Sales_value * sign,
            'error_message': f"Processed OK. Sign: {sign}, Regular Pts: {Invoice_points_vr:.1f}, Promo Pts: {Invoice_points_promovr:.1f}, Qty: {int(Total_qty * sign)}, Sales Value: {Sales_value * sign:.2f} | Price: {Total_price:.2f}, Discount: {Total_disc:.2f}, Customer Spl Discount: {Total_spldisc:.2f}",
            'sql_statement': f"Processed successfully with sign {sign}.",
        })
