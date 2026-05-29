import json
import logging
import functools
import werkzeug.wrappers

from odoo import http
from odoo.addons.project_api.models.common import invalid_response, valid_response
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request
# import pyodbc




    # @http.route('/Token/authenticate', type='http', auth="none", methods=['POST'], csrf=False, save_session=False, cors="*")
    # def get_token(self):
    #     byte_string = request.httprequest.data
    #     data = json.loads(byte_string.decode('utf-8'))
    #
    #     username = data.get('username')
    #     password = data.get('password')
    #
    #     user_id = request.session.authenticate(request.db, username, password)
    #
    #     if not user_id:
    #         return json.dumps({"error": "Invalid Username or Password."}), 401
    #
    #     env = request.env(user=request.env['res.users'].browse(user_id))
    #     api_key = env['res.users.apikeys.description'].check_access_make_key()
    #
    #     token = env['res.users.apikeys']._generate(api_key, username)
    #
    #     payload = {
    #         'user_id': user_id,
    #         'username': username,
    #         'token': token
    #     }
    #
    #     return json.dumps({
    #         "data": payload,
    #         "responsedetail": {
    #             "messages": "User Validated",
    #             "messagestype": 1,
    #             "responsecode": 200
    #         }
    #     }), 200
