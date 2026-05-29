# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Noorjahan NA (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <https://www.gnu.org/licenses/>.
#
################################################################################
from odoo import fields, models,api ,_
import logging
_logger = logging.getLogger(__name__)

class WebsiteMenu(models.Model):
    _inherit = 'website.menu'
    """Inheriting to add Groups related fields for use in rules"""

    user_type = fields.Selection(
        [('internal', 'Internal User'), ('portal', 'Portal User')],
        string='User Type',
        help="Select the user type that can see this menu. Leave empty for all users.",
        default=False  # Default behavior: visible to all users.
    )

    def _compute_visible(self):
        for menu in self:
            visible = True
            user = self.env.user


            # Debug start
            print(f"Checking menu visibility for user: {user.name} ({user.id}) and menu: {menu.name}")


            # # Admin users can see all menus
            # if user.has_group('base.group_system') or user.id == self.env.ref('base.user_admin').id:
            #     print(f"User {user.name} is admin or system user, showing all menus.")
            #     menu.is_visible = True
            #     continue

            # Check page visibility
            if menu.page_id:
                page_sudo = menu.page_id.sudo()
                if (not page_sudo.is_visible
                        or (not page_sudo.view_id._handle_visibility(do_raise=False)
                            and page_sudo.view_id._get_cached_visibility() != "password")):
                    visible = False

            # Check controller visibility
            if menu.controller_page_id:
                controller_page_sudo = menu.controller_page_id.sudo()
                if (not controller_page_sudo.is_published
                        or (not controller_page_sudo.view_id._handle_visibility(do_raise=False)
                            and controller_page_sudo.view_id._get_cached_visibility() != "password")):
                    visible = False

            # Check user type
            if menu.user_type:
                if menu.user_type == 'portal' and not user.has_group('base.group_portal'):

                    visible = False
                elif menu.user_type == 'internal' and not user.has_group('base.group_user'):

                    print(f"Menu {menu.name} is for portal users, but {user.name} is not a portal user.")
                    visible = False
                elif menu.user_type == 'internal' and not user.has_group('base.group_user'):
                    print(f"Menu {menu.name} is for internal users, but {user.name} is not an internal user.")

                    visible = False

            # Assign computed visibility
            menu.is_visible = visible

            print(f"Menu {menu.name} visibility for {user.name}: {visible}")



