/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";


patch(Dialog.prototype, {
        setup() {
        super.setup();
        if (this.props.title == "Odoo"){
            this.props.title = localStorage.getItem("odoo_value");
        }
    }

});

