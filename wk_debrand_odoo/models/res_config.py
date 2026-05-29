# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################
import base64, os
from odoo import fields, models, api, tools
import logging
_logger = logging.getLogger(__name__)

class IrDefault(models.Model):
    _inherit = 'ir.default'

    @api.model
    def set_wk_favicon(self, model, field):
        script_dir = os.path.dirname(__file__)
        rel_path = "../static/src/img/favicon.png"
        abs_file_path = os.path.join(script_dir, rel_path)
        with open(abs_file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            self.set('res.config.settings', 'wk_favicon', encoded_string.decode("utf-8"))

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wk_favicon = fields.Binary(string="Favicon Image")
    title_brand = fields.Char(string="Title Brand")
    odoo_text_replacement = fields.Char(string='Replace Text "Odoo" With?')
    favicon_url = fields.Char(string="Url")
    attach_id = fields.Integer(string="Favicon Attach ID")

    @api.model
    def get_debranding_settings(self):
        """Fetch the debranding settings stored in ir.default."""
        IrDefault = self.env['ir.default'].sudo()
        result = {
            'wk_favicon': IrDefault._get('res.config.settings', "wk_favicon"),
            'title_brand': IrDefault._get('res.config.settings', "title_brand"),
            'odoo_text_replacement': IrDefault._get('res.config.settings', "odoo_text_replacement"),
            'favicon_url': IrDefault._get('res.config.settings', "favicon_url"),
            'attach_id': IrDefault._get('res.config.settings', "attach_id"),
        }
        return result

    def set_values(self):
        """Save the values for debranding settings."""
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()

        # Save debranding settings
        IrDefault.set('res.config.settings', "wk_favicon", self.wk_favicon and self.wk_favicon.decode("utf-8") or False)
        IrDefault.set('res.config.settings', "title_brand", self.title_brand)
        IrDefault.set('res.config.settings', "odoo_text_replacement", self.odoo_text_replacement)

        attach_id = None
        if not self.attach_id:
            # Search for existing Favicon attachment
            attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'Favicon')], limit=1)
            if attachment:
                # Update existing attachment
                attachment.write({'datas': self.wk_favicon and self.wk_favicon.decode("utf-8") or False})
                attach_id = attachment.id
            else:
                # Create new attachment
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': 'Favicon',
                    'datas': self.wk_favicon and self.wk_favicon.decode("utf-8") or False,
                    'public': True,
                })
                attach_id = attachment.id
        else:
            # Update existing attachment if ID is provided
            attachment = self.env['ir.attachment'].sudo().browse(self.attach_id)
            if attachment.exists():
                attachment.write({'datas': self.wk_favicon and self.wk_favicon.decode("utf-8") or False})
                attach_id = attachment.id

        # Set favicon URL
        if attach_id:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            image_url = f"{base_url}/web/image/?model=ir.attachment&id={attach_id}&field=datas"
            IrDefault.set('res.config.settings', "favicon_url", image_url)
            IrDefault.set('res.config.settings', "attach_id", attach_id)

    @api.model
    def get_values(self):
        """Retrieve the saved debranding settings and populate them in the form."""
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()

        # Fetch values from ir.default
        wk_favicon = IrDefault._get('res.config.settings', "wk_favicon")
        title_brand = IrDefault._get('res.config.settings', "title_brand")
        odoo_text_replacement = IrDefault._get('res.config.settings', "odoo_text_replacement")
        favicon_url = IrDefault._get('res.config.settings', "favicon_url")
        attach_id = IrDefault._get('res.config.settings', "attach_id")

        res.update(
            wk_favicon=wk_favicon,
            title_brand=title_brand,
            odoo_text_replacement=odoo_text_replacement,
            favicon_url=favicon_url,
            attach_id=attach_id,
        )
        return res