"""Machine Repair management"""
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class RepairRequest(http.Controller):
    """Controller to manage repair requests."""

    @http.route(['/repair'], type='http', auth="public", website=True)
    def get_request(self):
        """Render the repair request form accessible to any user."""
        vals = {
            'product_id': request.env['product.product'].sudo().search([('is_machine', '=', True)]),
            'partner_id': request.env['res.partner'].sudo().search([]),
            'product_category': request.env['product.category'].sudo().search([]),
        }
        return request.render("machine_repair_management.repair_request_form", vals)

    @http.route('/create/repair_request', type='http', methods=['POST'], auth="public", website=True, csrf=False)
    def submit_form_request(self, **POST):
        """Submit the repair request form and redirect to a thank-you page."""
        partner_name = POST.get('partner_id')
        partner_email = POST.get('email')
        partner_phone = POST.get('phone')

        # Search for existing customer by email
        existing_partner = request.env['res.partner'].sudo().search([('email', '=', partner_email)], limit=1)

        if not existing_partner:
            # Create a new customer if not found
            customer = request.env['res.partner'].sudo().create({
                'name': partner_name,
                'email': partner_email,
                'phone': partner_phone
            })
        else:
            customer = existing_partner

        # Update the POST data to include the partner_id
        POST.update({'partner_id': customer.id, 'name': 'Repair from Website'})

        # Create the repair request
        repair = request.env['machine.repair.support'].sudo().create(POST)

        # Redirect to a thank-you page
        return request.redirect('/contactus-thank-you')
