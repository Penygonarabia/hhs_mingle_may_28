/** @odoo-module **/

import { registry } from "@web/core/registry";

const userMenuRegistry = registry.category("user_menuitems");

// Remove Shortcuts
userMenuRegistry.remove("shortcuts");

// Remove My Profile
userMenuRegistry.remove("profile");