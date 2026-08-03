/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { FormView } from "@web/views/form/form_view";
import { formView as baseFormView } from "@web/views/form/form_view";

class PromoterConfirmController extends FormController {
    async saveRecord() {
        // Get field values
        const conflict = this.model.data.promoter_conflict;
        const userConfirmed = this.model.data.user_confirm_conflict;

        if (conflict && !userConfirmed) {
            const confirmed = await this.dialogService.confirm(
                "This promoter is already assigned during this time period.\n\nDo you want to proceed anyway?",
                { title: "Conflict Detected" }
            );
            if (!confirmed) {
                return false;
            }
            // Set user_confirm_conflict = true
            await this.model.update({ user_confirm_conflict: true });
        }

        // Proceed with normal save
        return super.saveRecord();
    }
}

// Register the custom controller for your form class
export const PromoterConfirmView = {
    ...baseFormView,
    Controller: PromoterConfirmController,
};

registry.category("views").add("promoter_confirm_form", PromoterConfirmView);
