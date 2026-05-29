/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";

class CustomListController extends ListController {
    getStaticActionMenuItems() {
        // Get the parent class's static action menu items
        const menuItems = super.getStaticActionMenuItems();

        // Hide addPropertyFieldValue by setting isAvailable to false
        if (menuItems.addPropertyFieldValue) {
            menuItems.addPropertyFieldValue.isAvailable = () => false;
        }

        return menuItems;
    }
}

registry.category("views").add("custom_list", {
    ...ListController,
    Controller: CustomListController,
});