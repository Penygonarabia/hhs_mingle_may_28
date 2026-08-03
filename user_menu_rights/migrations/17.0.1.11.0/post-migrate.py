# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api, fields

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Rights = env["menu.access.rights"].sudo()
    users = env["res.users"].sudo().search([
        ("share", "=", False),
        ("active", "=", True),
    ])
    
    for user in users:
        if Rights._is_admin_user(user):
            continue
        if hasattr(user, "hide_menu_ids"):
            rights = Rights.search([("user_id", "=", user.id)])
            
            # Clear allowed menus from hidden list
            allowed_menus = rights.filtered(lambda r: r.has_access).mapped("menu_id")
            if allowed_menus:
                user.write({"hide_menu_ids": [fields.Command.unlink(m.id) for m in allowed_menus]})
                if hasattr(allowed_menus, "restrict_user_ids"):
                    for menu in allowed_menus:
                        if user.id in menu.restrict_user_ids.ids:
                            menu.write({"restrict_user_ids": [fields.Command.unlink(user.id)]})
            
            # Link forbidden menus to hidden list
            forbidden_menus = rights.filtered(lambda r: not r.has_access).mapped("menu_id")
            if forbidden_menus:
                user.write({"hide_menu_ids": [fields.Command.link(m.id) for m in forbidden_menus]})
                if hasattr(forbidden_menus, "restrict_user_ids"):
                    for menu in forbidden_menus:
                        if user.id not in menu.restrict_user_ids.ids:
                            menu.write({"restrict_user_ids": [fields.Command.link(user.id)]})
