/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PivotGroupByMenu } from "@web/views/pivot/pivot_group_by_menu";
import { isMobileOS } from "@web/core/browser/feature_detection";

patch(PivotGroupByMenu.prototype, {
    setup() {
        super.setup(...arguments);
        // Inject a custom class to the dropdown menu so we can target it purely with CSS for mobile
        if (isMobileOS() || this.env.isSmall) {
            this.dropdownProps.menuClass = (this.dropdownProps.menuClass || "") + " mobile_pivot_dropdown_menu";
        }
    }
});
