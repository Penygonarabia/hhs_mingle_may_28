/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

const MODELS_TO_CLEAN = [
    "project.task",          // ← replace with your actual model
   
    // add as many as you want
];

patch(FormController.prototype, {
    getStaticActionMenuItems() {
        const items = super.getStaticActionMenuItems(...arguments);

        // This runs LAST → nothing can add it back after this
        delete items.addPropertyFieldValue;

        // Optional: remove only on certain models
        // if (!["product.template", "product.product"].includes(this.props.resModel)) {
        //     return items;
        // }
        // delete items.addPropertyFieldValue;
		
		if (MODELS_TO_CLEAN.includes(this.props.resModel)) {
		            delete items.archive;     // hides "Archive"
		            delete items.unarchive;   // hides "Unarchive" (when record is already archived)
					delete items.delete;
					delete items.duplicate;
		        }

        return items;
    },
});