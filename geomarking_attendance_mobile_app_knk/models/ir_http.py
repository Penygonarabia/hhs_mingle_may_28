# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

import base64
import logging
from odoo import api, http, fields, models,_
from odoo.http import request


_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_auth_bearer(cls):
        headers = request.httprequest.environ

        authorization = headers.get("HTTP_AUTHORIZATION")
        if not authorization:
            raise http.SessionExpiredException("token not found")
        if authorization:
            authorization_token = authorization.split(" ")[1]
            user = (
                request.env["res.users"]
                .sudo()
                ._get_user_from_token(authorization_token)
            )
            if not user:
                raise http.SessionExpiredException("wrong key")
            super(IrHttp, cls)._auth_method_public()
            return True
        else:
            # public access
            super(IrHttp, cls)._auth_method_public()
            return True

        raise http.SessionExpiredException("wrong key")


class ResUsers(models.Model):
    _inherit = "res.users"

    client_id = fields.Char(string="Client ID")
    secret_key = fields.Char(string="Secret Key")
    bearer_token = fields.Char(
        string="Bearer Token", compute="_create_bearer_token"
    )

    @api.depends("client_id", "secret_key")
    def _create_bearer_token(self):
        self.bearer_token = base64.b64encode(
            bytes("{}:{}".format(self.client_id, self.secret_key), "utf-8")
        ).decode()

    @api.model
    def _get_user_from_token(self, token):
        # base64.b64encode(bytes('client_id:secret_key', 'utf-8')).decode() for decode
        keys = base64.b64decode(
            token.encode()
        ).decode()  # MTAxMDEwMTE6YWJjQCEl
        client_id = keys.split(":")[0]
        secret_key = keys.split(":")[1]
        user = self.search(
            [("client_id", "=", client_id), ("secret_key", "=", secret_key)],
            limit=1,
        )
        return user
