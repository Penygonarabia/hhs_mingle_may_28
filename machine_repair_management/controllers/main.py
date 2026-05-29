# -*- coding: utf-8 -*-

import base64
from odoo import http, _
import logging

from odoo.http import request
# from odoo import models,registry, SUPERUSER_ID odoo13
from odoo.addons.portal.controllers.portal import CustomerPortal as website_account
from datetime import datetime, date, time
import pytz

_logger = logging.getLogger(__name__)  # Initialize the logger


class MachineRepairSupport(http.Controller):
   
 
    @http.route('/machine_repair/phone_popup', type='json', auth='user')
    def phone_popup(self, **kwargs):
        phone = kwargs.get('params', {}).get('phone')
        
        
        # unique_code = kwargs.get('params', {}).get('unique_code')
 
        if not phone:
            return False
        
        # Check if machine.repair.support already has a record for this phone
        # support_record_exists = request.env['machine.repair.support'].sudo().search_count([
        #     ('phone', '=', phone)
        # ])
        #
        # if support_record_exists:
        #     return False  # Don't show popup if record exists
        

        
        tasks = request.env['project.task'].sudo().search([
            ('phone', '=', phone),
            ('job_card_state_code', 'not in', ('124', '126'))
        ])
 
        if not tasks:
            return False
 
        tree_view_id = request.env.ref("machine_repair_management.view_project_task_tree").id
        form_view_id = request.env.ref("machine_repair_management.view_project_task_form").id
 
        return {
            "type": "ir.actions.act_window",
            "name": "Task Matches",
            "res_model": "project.task",
            "domain": [("id", "in", tasks.ids)],
            "view_mode": "tree,form",
            "views": [[tree_view_id, "tree"], [form_view_id, "form"]],
            "target": "new",
            "context": {
                "show_update_button": True,
                # "unique_code": unique_code,
            }
        }
 

    def prepare_vals_machine_repair(self, Partner, **post):
        team_obj = request.env['machine.support.team']
        team_match = team_obj.sudo().search([('is_team', '=', True)], limit=1)
        purchase_date_str = post.get('purchase_date')
        try:
            # Assuming the date is in 'YYYY-MM-DD' format (adjust format as needed)
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            # Fallback to current date if the input is invalid
            purchase_date = date.today()
        # call_request_appointment_date_str = post.get('call_request_appointment_date')
        # try:
        #     # Assuming the date is in 'YYYY-MM-DD' format (adjust format as needed)
        #     call_request_appointment_date = datetime.strptime(call_request_appointment_date_str, '%Y-%m-%d').date()
        # except (ValueError, TypeError):
        #     # Fallback to current date if the input is invalid
        #     call_request_appointment_date = date.today()
        #     # Handle partner_id by searching for a partner with the provided name

        # Parse call_request_appointment_date and expected_time
        call_request_appointment_date_str = post.get('call_request_appointment_date')
        expected_time_str = post.get('expected_time')

        try:
            call_request_appointment_date = datetime.strptime(call_request_appointment_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            call_request_appointment_date = date.today()

        try:
            expected_time = datetime.strptime(expected_time_str, '%H:%M').time()
        except (ValueError, TypeError):
            expected_time = time(0, 0)  # Default to 00:00 if invalid

        # Combine date and time into a local datetime
        local_datetime = datetime.combine(call_request_appointment_date, expected_time)

        # Get user's timezone (default to UTC if not set)
        user_tz = request.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)

        # Localize to user's timezone and convert to UTC
        local_datetime_tz = local_tz.localize(local_datetime)
        utc_datetime = local_datetime_tz.astimezone(pytz.UTC)
        utc_datetime_naive = utc_datetime.replace(tzinfo=None)  # Make it naive for Odoo
        partner_id = Partner.id
        if post.get('customer_id'):
            partner = request.env['res.partner'].sudo().search([('name', '=', post.get('customer_id'))], limit=1)
            if partner:
                partner_id = partner.id
            else:
                # Optionally create a new partner
                partner = request.env['res.partner'].sudo().create({
                    'name': post.get('customer_id'),

                })
                partner_id = partner.id
        # Handle product_category as a string
        product_category_name = post.get('product_category')
        product_category = request.env['product.category'].sudo().search([('name', '=', product_category_name)],
                                                                         limit=1)
        if not product_category:
            # Create a new category if it doesn't exist
            product_category = request.env['product.category'].sudo().create({
                'name': product_category_name,
            })
        # Handle product_id as a string
        product_name = post.get('product_id')
        product = request.env['product.product'].sudo().search([('name', '=', product_name)], limit=1)
        if not product and product_name:
            # Create a new product if it doesn't exist
            product = request.env['product.product'].sudo().create({
                'name': product_name,
                'type': 'product',  # Adjust as needed (e.g., 'service', 'consu')
            })
        support_vals = {
            # 'subject': post['subject'],
            'team_id': team_match.id,
            #            'partner_id' :team_match.leader_id.id, odoo13
            'team_leader_id': team_match.leader_id.id,
            'user_id': team_match.leader_id.id,
            'email': post.get('email'),
            'phone': post.get('phone'),
            'partner_city': int(post['city_id']),
            'address': post.get('address'),
            # 'product_category': product_category.id,
            'product_category': int(post['product_category']),
            'product_id': product.id if product else False,  # Use product ID or False
            # 'product_id': int(post['product_id']),
            'product_slno': post['product_slno'],
            'purchase_invoice_no': post['purchase_invoice_no'],
            'purchase_date': purchase_date,
            'call_request_appointment_date': utc_datetime_naive,
            'purchase_dealer_name': post['purchase_dealer_name'],
            'comment': post['comment'],
            'problem': post['problem'],
            # 'description': post['description'],
            # 'priority': post['priority'],
            'partner_id': partner_id,
            # 'partner_id': partner_id,
            'website_brand': post['brand'],
            # 'website_model': post['model'],
            # 'damage': post['damage'],
            # 'website_year': post['year'],
            # 'nature_of_service_id': post['service_id'],
            # 'nature_of_service_id': int(post['service_id']),
            'custome_client_user_id': request.env.user.id,
        }
        city_id = request.env['res.city'].sudo().search([('id', '=', int(post['city_id']))], limit=1)
        work_center_search = request.env['work.center.location'].sudo().search(
            [('id', '=', city_id.def_work_center_id.id)], limit=1)
        support_vals.update({
            'work_location_id': work_center_search.id
        })
        return support_vals

    def prepare_open_machine_repair_vals(self, **post):
        service_ids = request.env['service.nature'].sudo().search([])
        srvice_type_ids = request.env['repair.type'].sudo().search([])
        product_category_ids = request.env['product.category'].sudo().search([])
        product_ids = request.env['product.product'].sudo().search([])
        city_ids = request.env['res.city'].sudo().search([])

        vals = {
            'service_ids': service_ids,
            'srvice_type_ids': srvice_type_ids,
            'product_ids': product_ids,
            'product_category_ids': product_category_ids,
            'city_ids': city_ids,
        }
        return vals

    @http.route(['/page/machine_repair_support_ticket'], type='http', auth="public", website=True)
    def open_machine_repair_request(self, **post):
        vals = self.prepare_open_machine_repair_vals(**post)
        return request.render("machine_repair_management.website_machine_repair_support_ticket", vals)

    @http.route(['/machine_repair_management/request_submitted'], type='http', auth="public", methods=['POST'],
                website=True)
    def request_submitted(self, **post):
        #         cr, uid, context, pool = http.request.cr, http.request.uid, http.request.context, request.env
        #        Partner = request.env['res.partner'].sudo().search([('email', '=', post['email'])]) odoo13
        if request.env.user.has_group('base.group_public'):
            Partner = request.env['res.partner'].sudo().search([('email', '=', post['email'])], limit=1)
        else:
            Partner = request.env.user.partner_id
        if Partner:
            support_vals = self.prepare_vals_machine_repair(Partner, **post)
            support = request.env['machine.repair.support'].sudo().create(support_vals)
            values = {
                'support': support,
                'user': request.env.user
            }
            attachment_list = request.httprequest.files.getlist('attachment')
            for image in attachment_list:
                if post.get('attachment'):
                    attachments = {
                        'res_name': image.filename,
                        'res_model': 'machine.repair.support',
                        'res_id': support,
                        'datas': base64.encodebytes(image.read()),
                        'type': 'binary',
                        # 'datas_fname': image.filename, odoo13
                        'name': image.filename,
                    }
                    attachment_obj = http.request.env['ir.attachment']
                    attach = attachment_obj.sudo().create(attachments)
            if len(attachment_list) > 0:
                group_msg = _(
                    'Customer has sent %s attachments to this machine repair ticket. Name of attachments are: ') % (
                                len(attachment_list))
                for attach in attachment_list:
                    group_msg = group_msg + '\n' + attach.filename
                group_msg = group_msg + '\n' + '. You can see top attachment menu to download attachments.'
                support.sudo().message_post(body=group_msg, message_type='comment')
            return request.render('machine_repair_management.thanks_mail_send', values)
        else:
            return request.render('machine_repair_management.support_invalid', {'user': request.env.user})

    # not necessary  odoo13
    #    @http.route(['/machine_repair_management/invite'], auth='public', website=True, methods=['POST'])
    #    def index_user_invite(self, **kw):
    #        email = kw.get('email')
    #        name = kw.get('name')
    ##         cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
    #        user = request.env['res.users'].browse(request.uid)
    #        user_exist = request.env['res.users'].sudo().search([('login','=',str(email))])
    #        vals = {
    #                  'user_id':user_exist,
    #                }
    #        if user_exist:
    #            return http.request.render('machine_repair_management.user_alredy_exist', vals)
    #        value={
    #              'name': name,
    #              'email': email,
    #              'invitation_date':datetime.date.today(),
    #              'referrer_user_id':user.id,
    #              }
    #        user_info_id = self.create_history(value)
    #        base_url = http.request.env['ir.config_parameter'].get_param('web.base.url', default='http://localhost:8069') + '/page/machine_repair_management.user_thanks'
    #        url = "%s?user_info=%s" %(base_url, user_info_id.id)
    #        reject_url = http.request.env['ir.config_parameter'].get_param('web.base.url', default='http://localhost:8069') + '/page/machine_repair_management.user_thanks_reject'
    #        rejected_url = "%s?user_info=%s" %(reject_url, user_info_id.id)
    #        local_context = http.request.env.context.copy()
    #        issue_template = http.request.env.ref('machine_repair_management.email_template_machine_ticket')
    #        local_context.update({'user_email': email, 'url': url, 'name':name,'rejected_url':rejected_url})
    #        issue_template.sudo().with_context(local_context).send_mail(request.uid)

    @http.route(['/machine_repair_email/feedback/<int:order_id>'], type='http', auth='public', website=True)
    def feedback_email(self, order_id, **kw):
        values = {}
        values.update({'machine_ticket_id': order_id})
        return request.render("machine_repair_management.machine_repair_feedback", values)

    @http.route(['/machine_repari/feedback/'],
                methods=['POST'], auth='public', website=True)
    def start_rating(self, **kw):
        partner_id = kw['partner_id']
        user_id = kw['machine_ticket_id']
        ticket_obj = request.env['machine.repair.support'].sudo().browse(int(user_id))
        # if partner_id == UserInput.partner_id.id:
        vals = {
            'rating': kw['star'],
            'comment': kw['comment'],
        }
        ticket_obj.sudo().write(vals)
        customer_msg = _(ticket_obj.partner_id.name + 'has send this feedback rating is %s and comment is %s') % (
            kw['star'], kw['comment'],)
        ticket_obj.sudo().message_post(body=customer_msg)
        return http.request.render("machine_repair_management.successful_feedback")


class website_account(website_account):

    def _prepare_portal_layout_values(self):  # odoo11
        values = super(website_account, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values.update({
            'repair_request_count': request.env['machine.repair.support'].search_count(
                [('partner_id', 'child_of', [partner.commercial_partner_id.id])]),
            'page_name': 'repair_requests',
        })
        return values

    #     @http.route()
    #     def account(self, **kw):
    #         """ Add ticket documents to main account page """
    #         response = super(website_account, self).account(**kw)
    #         partner = request.env.user.partner_id
    #         ticket = request.env['machine.repair.support']
    #         ticket_count = ticket.sudo().search_count([
    #         ('partner_id', 'child_of', [partner.commercial_partner_id.id])
    #           ])
    #         response.qcontext.update({
    #         'ticket_count': ticket_count,
    #         })
    #         return response

    @http.route(['/my/repair_requests', '/my/repair_requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_repair_request(self, page=1, **kw):
        response = super(website_account, self)
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        support_obj = http.request.env['machine.repair.support']
        domain = [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id])
        ]
        # pager
        pager = request.website.pager(
            url="/my/repair_requests",
            total=values.get('repair_request_count'),
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        repair_request = support_obj.sudo().search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'repair_requests': repair_request,
            'page_name': 'repair_requests',
            'pager': pager,
            'default_url': '/my/repair_requests',
        })
        return request.render("machine_repair_management.display_repair_requests", values)

    @http.route(['/my/repair_request/<model("machine.repair.support"):repair_request>'], type='http', auth="user",
                website=True)
    def my_repair_request(self, repair_request=None, access_token=None, **kw):
        attachment_list = request.httprequest.files.getlist('attachment')
        support_obj = http.request.env['machine.repair.support'].sudo().browse(repair_request.id)
        for image in attachment_list:
            if kw.get('attachment'):
                attachments = {
                    'res_name': image.filename,
                    'res_model': 'machine.repair.support',
                    'res_id': repair_request.id,
                    'datas': base64.encodebytes(image.read()),
                    'type': 'binary',
                    # 'datas_fname': image.filename, odoo13
                    'name': image.filename,
                }
                attachment_obj = http.request.env['ir.attachment']
                attachment_obj.sudo().create(attachments)
        if len(attachment_list) > 0:
            group_msg = _(
                'Customer has sent %s attachments to this Machine repair ticket. Name of attachments are: ') % (
                            len(attachment_list))
            for attach in attachment_list:
                group_msg = group_msg + '\n' + attach.filename
            group_msg = group_msg + '\n' + '. You can see top attachment menu to download attachments.'
            support_obj.sudo().message_post(body=group_msg, message_type='comment')
            customer_msg = _('%s') % (kw.get('ticket_comment'))
            support_obj.sudo().message_post(body=customer_msg, message_type='comment')
            return http.request.render('machine_repair_management.successful_ticket_send', {
            })
        if kw.get('ticket_comment'):
            customer_msg = _('%s') % (kw.get('ticket_comment'))
            support_obj.sudo().message_post(body=customer_msg, message_type='comment')
            return http.request.render('machine_repair_management.successful_ticket_send', {
            })
        return request.render("machine_repair_management.display_repair_request_from",
                              {'repair_request': repair_request, 'token': access_token, 'user': request.env.user})


class JobCardPortal(http.Controller):

    def is_admin_user(self, user):
        """Helper method to check if the user is an admin."""
        return user.has_group('base.group_system')

    @http.route(['/my/jobcards'], type='http', auth="user", website=True)
    def portal_jobcards(self, **kw):
        _logger.info("Job Cards list accessed.")
        user = request.env.user
        domain = [] if self.is_admin_user(user) else [('technician_id', '=', user.id)]

        jobcards = request.env['jobcard'].sudo().search(domain)
        _logger.debug(f"Job Cards found: {jobcards}")

        return request.render("machine_repair_management.portal_jobcards", {'jobcards': jobcards})

    @http.route(['/my/jobcard/<model("jobcard"):jobcard>'], type='http', auth="user", website=True)
    def portal_jobcard_detail(self, jobcard=None, **kw):
        user = request.env.user
        if not self.is_admin_user(user) and jobcard.technician_id != user:
            return request.redirect('/my/home')

        return request.render("machine_repair_management.portal_jobcard_page", {'jobcard': jobcard})