/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";

export class CustomFormController extends FormController {
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        if (menuItems.addPropertyFieldValue) {
            menuItems.addPropertyFieldValue.isAvailable = () => false;
        }
        return menuItems;
    }
}

// Register the custom controller with a unique key to avoid conflicts
registry.category("views").add("custom_form", {
    ...FormController,
    Controller: CustomFormController,
}, { force: true });