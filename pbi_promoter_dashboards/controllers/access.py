# -*- coding: utf-8 -*-
"""Route-level access check, shared by every dashboard controller here.

Mirrors the menu's own gate: if you can't see the menu, you can't fetch its
data by hitting the JSON route directly either.

user_menu_rights is deliberately NOT a dependency of this module — the two
install and uninstall independently — so the per-user overlay is resolved at
runtime rather than at import time. With it installed, its explicit grants
decide. Without it, there is no per-user overlay at all and the answer falls
back to Odoo's own group-based menu visibility, which is exactly what governs
the menu in that configuration.

Defines no @http.route, so importing it registers nothing.
"""

from odoo.http import request

RIGHTS_MODEL = "menu.access.rights"


def menu_allowed(menu_xmlid):
    """True when the CURRENT user may open the menu at ``menu_xmlid``."""
    menu = request.env.ref(menu_xmlid, raise_if_not_found=False)
    if not menu and "." in menu_xmlid:
        module, record_id = menu_xmlid.split(".", 1)
        for alt_module in (
            "pbi_service_dashboards",
            "pbi_contract_dashboards",
            "pbi_promoter_dashboards",
            "pbi_loyalty_dashboards",
            "pbi_sales_dashboards",
            "pbi_quarterly_sales_dashboards",
            "pbi_dashboards",
        ):
            if alt_module != module:
                menu = request.env.ref(f"{alt_module}.{record_id}", raise_if_not_found=False)
                if menu:
                    break
    if not menu:
        return False
    if RIGHTS_MODEL not in request.env:
        return menu.id in set(request.env["ir.ui.menu"]._visible_menu_ids())
    allowed = request.env[RIGHTS_MODEL].sudo().allowed_menu_ids(request.env.user)
    return menu.id in allowed

