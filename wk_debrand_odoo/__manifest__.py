# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
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
{
  "name"                 :  "Odoo Backend Debranding",
  "summary"              :  """This is the base odoo backend debranding module.""",
  "category"             :  "Industries",
  "version"              :  "1.0.1",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo-Backend-Debranding.html",
  "description"          :  """This is the base odoo backend debranding module.""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=wk_debrand_odoo",
  "depends"              :  [
                             'web',
                             'mail',
                             'portal',
                            ],
  "data"                 :  [
                             'views/res_config_view.xml',
                             'views/web_client_template.xml',
                             'views/portal_templates.xml',
                             'views/email_templates.xml',
                             'data/data.xml',
                            ],
  "qweb"                 :  [
                             'static/src/xml/base.xml',
                             'static/src/xml/client_action.xml',
                            ],
  "assets"               : {  
                            "web.assets_backend": [
                                '/wk_debrand_odoo/static/src/js/web_client.js',
                                '/wk_debrand_odoo/static/src/js/dialog.js',
                                '/wk_debrand_odoo/static/src/js/my_widget.js',
                                '/wk_debrand_odoo/static/src/js/user_menu.js',
                                '/wk_debrand_odoo/static/src/js/mail_dialog.js'
                            ],
                            'web.assets_qweb': [
                                'wk_debrand_odoo/static/src/xml/dashboard.xml',
                                'wk_debrand_odoo/static/src/xml/base.xml',
                                'wk_debrand_odoo/static/src/xml/client_action.xml',
                            ],
                         },
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  30,
  "currency"             :  "USD",
  "pre_init_hook"        : "pre_init_check",
}
