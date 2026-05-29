# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# License URL : https://store.webkul.com/license.html/
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import api, fields, models, _
from odoo.http import request
from datetime import datetime
from google.oauth2 import service_account
from odoo.tools.misc import file_path
import google.auth.transport.requests

import os
import base64
import requests
import json
import logging
_logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']

class WebPushNotifiactions(models.Model):
    _name = 'pwa.push.notifications'
    _order = 'create_date desc'
    _description = "PWA Push Notifications"

    def _default_website(self):
        return self.env['website'].search([('company_id', '=', self.env.company.id)], limit=1)

    name = fields.Char(string='Title', required=True, translate=True)
    message = fields.Char(string='Body', required=True, translate=True)
    image = fields.Binary(string='Browse Logo')
    banner_image = fields.Binary(string='Browse Banner')
    redirect_url = fields.Char(string='Target Link', required=True)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validated'), ('sent', 'Sent'), ('cancel', 'Canceled'), ('error','Error')], default="draft", string="State")
    image_type = fields.Selection([ ('url', 'URL'),('base_64', 'Browse')], string="Select Logo", help="Select the logo you want to display in the notification", required=True)
    banner_image_type = fields.Selection([ ('url', 'URL'),('base_64', 'Browse')], string="Select Banner", help="Select the banner you want to display in the notification", required=True)
    image_url = fields.Char(string='Logo URL', help="URL of the image you want to display ")
    banner_url = fields.Char(string='Banner URL', help="URL of the banner image you want to display ")
    summary = fields.Text(string="Sent Summary")
    last_sent_date = fields.Date(string="Last Sent Date")
    is_scheduled = fields.Selection([('y', 'Yes'),('n', 'No')], string="Schedule Notification", default="n")
    schedule_date = fields.Date(string="Schedule Date")
    website_id = fields.Many2one('website', string="website", default=_default_website, ondelete='cascade')
    language = fields.Many2one(string="Language",comodel_name="res.lang",required=True)
    send_to = fields.Selection(
        [('all', 'All'),
        ('odoo_users', 'Odoo Users'),
        ('public_users', 'Public Users'),
        ('portal_users', 'Website Users')],
        string='Target User Type',
        default='all',
        required=True,
        help="users for which you want send the notifications")


    def get_notification_data(self):
        self.ensure_one()
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        data = {
            'webpush':{}
        }
        data['webpush']['notification'] = {
            'title' : self.name,
            'body' : self.message,
            'icon' : '/odoo_ecommerce_pwa/static/src/img/launcher_512.png',
        }
        data['webpush']['fcm_options'] = {
            "link": self.redirect_url,
        }
        if self.image_type == 'url':
            data['webpush']['notification']['icon'] = str(self.image_url)
        else:
            data['webpush']['notification']['icon'] = str('%s/web/image/%s/%s/%s'% (base_url, 'pwa.push.notifications', self.id, 'image'))
        if self.banner_image_type == 'url':
            data['webpush']['notification']['image'] = str(self.banner_url)
        else:
            data['webpush']['notification']['image'] = str('%s/web/image/%s/%s/%s'% (base_url, 'pwa.push.notifications', self.id, 'banner_image'))
        return {'message': data}


    def get_notification_registered_users(self):
        registered_users = self.env["pwa.user.registrations"].get_registration_users(type=self.send_to, website_id=self.website_id.id)
        return registered_users
    
    def _get_firebase_auth_file(self):
        f_path = file_path("odoo_ecommerce_pwa/static/src/demo-authentication-file.json")
        if not os.path.exists(f_path):
            website = self.env['website'].sudo().get_current_website()
            firebase_auth_file = website.pwa_firebase_auth_file
            firebase_auth_file_content = base64.b64decode(firebase_auth_file)
            with open(f_path, "w+") as file:
                file.write(firebase_auth_file_content.decode("utf-8"))

        return f_path
    
    def _get_access_token(self):
        """Retrieve a valid access token that can be used to authorize requests.
        :return: Access token.
        """
        credentials = service_account.Credentials.from_service_account_file(
        self._get_firebase_auth_file(), scopes=SCOPES)
        wrequest = google.auth.transport.requests.Request()
        credentials.refresh(wrequest)
        return credentials.token

    def send_pwa_push_notification(self):
        self.ensure_one()
        state = 'draft'
        msg = ''
        success_count, failure_count = 0, 0

        # reteriving the server key for authentication
        try:
            server_key = 'Bearer ' + self._get_access_token()
        except Exception as e:
            state = 'error'
            msg = 'Error in Getting the access token for authorization. Kindly check the authentication file in settings.: %s' % e
            
        if state != 'error':
            headers = {'Authorization':server_key,'Content-Type': 'application/json; UTF-8'}
            sel_users = self.get_notification_registered_users()
            registration_key_list = list(set(sel_users.mapped('registration_key')))

            # getting the pwa_firebase_project_id
            IrDefault = request.env['ir.default'].sudo()
            pwa_firebase_project_id = IrDefault._get('res.config.settings', 'pwa_firebase_project_id')
            
            for reg_key in registration_key_list:
                url = 'https://fcm.googleapis.com/v1/projects/%s/messages:send' % pwa_firebase_project_id
                body = self.get_notification_data()
                body['message']['token'] = reg_key
                try:
                    result = requests.post(url, data=json.dumps(body), headers=headers)
                    result = eval(result.text)
                    state = 'sent'
                    success_count += 1 if result.get('name', False) else 0
                    failure_count += 1 if result.get('error', False) else 0
                except Exception as e:
                    state = 'error'
                    msg = 'Error in Sending push notifications: %s' % e
                    break
        if state != 'draft':
            if state == 'sent':
                msg = 'Status of Last Sent Notification as: \n No of Success = %s \n No. of Failures = %s' % (success_count, failure_count)
            self.write({
                'state': state,
                'summary': msg,
                'last_sent_date': datetime.now(),
            })

    @api.model
    def send_pwa_scheduled_notifications(self):
        records = self.search([('state','=','validate'),('is_scheduled','=','y'),('schedule_date','=',fields.Date().today()),('send_to','!=',None)])
        for rec in records:
            rec.send_pwa_push_notification()

    def set_to_draft(self):
        self.state = 'draft'
        return True

    def validate_template_data(self):
        self.state = 'validate'
        return True

class UserRegistrations(models.Model):
    _name = 'pwa.user.registrations'
    _order = 'create_date'
    _description = "PWA Push Notifications"

    def _default_website(self):
        return self.env['website'].search([('company_id', '=', self.env.company.id)], limit=1)

    user_id = fields.Many2one(comodel_name='res.users', string="User")
    registration_key = fields.Char(string='Registration Key', required=True)
    website_id = fields.Many2one('website', string="website", default=_default_website, ondelete='cascade')

    @api.model
    def get_registration_users(self, type=None, website_id=None):
        public_id = self.env.ref('base.group_public').id
        portal_id = self.env.ref('base.group_portal').id
        records = self.search([('website_id','=',website_id)])
        if type == 'portal_users':
            records = records.filtered(lambda rec: portal_id in rec.user_id.groups_id.ids)
        elif type == 'public_users':
            records = records.filtered(lambda rec: public_id in rec.user_id.groups_id.ids)
        elif type == 'odoo_users':
            portal_id = self.env.ref('base.group_portal').id
            records = records.filtered(lambda rec: portal_id not in rec.user_id.groups_id.ids)
            records = records.filtered(lambda rec: public_id not in rec.user_id.groups_id.ids)
        elif type == 'public_users':
            records = records.filtered(lambda rec: public_id in rec.user_id.groups_id.ids)
        return records
