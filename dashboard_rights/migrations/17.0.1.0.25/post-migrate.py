"""Purge the cached web.assets_* bundle on upgrade.

Covers 17.0.1.0.25 (fix: the popup's Grant All/Revoke All buttons used a bare
`disabled="expr"` on native <button> elements, which OWL treats as a static
HTML attribute string for native tags — any non-empty value disables the
button regardless of the expression's actual truthiness. Component props
(like CheckBox's `disabled`) DO get dynamic expression binding automatically;
native elements need `t-att-disabled` instead. Both buttons were permanently
disabled until this fix.). See dashboard_rights/hooks.py for the rationale.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.dashboard_rights.hooks import purge_web_assets

    _logger.info("dashboard_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)
