/** @odoo-module **/
/* 
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
 
patch(FormRenderer.prototype, {
    setup() {
		super.setup(...arguments);
    },
 
    _renderTag() {
        const result = this._super?.(...arguments);
        // If modal and flag no_quick_close, hide top-right X
        if (this.props?.no_quick_close && this.el) {
            const closeBtn = this.el.querySelector(".o_form_close");
            if (closeBtn) {
                closeBtn.style.display = "none";
            }
        }
        return result;
    },
});*/
 

/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";

patch(Dialog.prototype, {
    mounted() {
        this._super(...arguments);
        if (this.props.resModel === "cancelled.reason.wizard") {
            this._renderPromise.then(() => {
                const closeButton = this.el?.querySelector(".modal-header .btn-close");
                if (closeButton) {
                    closeButton.style.display = "none";
                    console.log("Close button hidden for cancelled.reason.wizard");
                } else {
                    console.log("Close button not found in the modal header");
                }
            });
        }
    },
});