/** @odoo-module **/
/*
import { registry } from "@web/core/registry";

const userMenuRegistry = registry.category("user_menuitems");*/

// Remove the profile/preferences menu
/*userMenuRegistry.remove("profile");
userMenuRegistry.remove("preferences");*/


/** @odoo-module **/

import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

const userMenuRegistry = registry.category("user_menuitems");

patch(UserMenu.prototype, {
    setup() {
        super.setup();

        userMenuRegistry.remove("documentation");
        userMenuRegistry.remove("support");
        userMenuRegistry.remove("shortcuts");
        userMenuRegistry.remove("profile");
        userMenuRegistry.remove("odoo_account");

        // Do NOT remove log_out unless you intentionally
        // want to disable logging out.
        // userMenuRegistry.remove("log_out");
    },
});
