/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUpdateProps } from "@odoo/owl";

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");
        this.action = useService("action");

        // Track initial values
        this._initialCancelStatus = false;
        this._initialOnholdStatus = false;

        // Prevent opening wizard multiple times
        this._wizardOpened = false;

        onMounted(async () => {
            const record = this.props.record;
            if (!record || record.resModel !== "project.task" || !record.resId) return;

            const resId = record.resId;
            const data = await this.orm.read(
                "project.task",
                [resId],
                ["cancel_status_check", "onhold_spareparts_status_check"]
            );

            this._initialCancelStatus = data[0]?.cancel_status_check || false;
            this._initialOnholdStatus = data[0]?.onhold_spareparts_status_check || false;

            console.log(
                "[auto_reason] Initial values:",
                this._initialCancelStatus,
                this._initialOnholdStatus
            );
        });

        onWillUpdateProps(() => this._checkStatusChange());
    },

    async _checkStatusChange() {
        try {
            const record = this.props.record;
            if (!record || record.resModel !== "project.task" || !record.resId) return;
            if (this._wizardOpened) return;

            const resId = record.resId;
            const data = await this.orm.read(
                "project.task",
                [resId],
                ["cancel_status_check", "onhold_spareparts_status_check"]
            );

            const cancelStatus = data[0]?.cancel_status_check || false;
            const onholdStatus = data[0]?.onhold_spareparts_status_check || false;

            console.log(
                "[auto_reason] Current values:",
                cancelStatus,
                onholdStatus
            );

            /* ---------------- CANCELLED ---------------- */
            if (cancelStatus && !this._initialCancelStatus) {
                this._wizardOpened = true;

                await this._openWizard({
                    name: "Cancelled Reason",
                    res_model: "cancelled.reason.wizard",
                    resId: resId,
                });
            }

            /* ---------------- ON HOLD SPARE PARTS ---------------- */
            if (onholdStatus && !this._initialOnholdStatus) {
                this._wizardOpened = true;

                await this._openWizard({
                    name: "OnHold Spare Parts Reason",
                    res_model: "onhold.spareparts.reason.wizard",
                    resId: resId,
                });
            }
        } catch (err) {
            console.error("[auto_reason] Error:", err);
        }
    },

    async _openWizard({ name, res_model, resId }) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: res_model,
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_job_card_id: resId,
            },
        });

        // Hide modal close button
        setTimeout(() => {
            const closeButton = document.querySelector(".modal-header .btn-close");
            if (closeButton) {
                closeButton.style.display = "none";
            }
        }, 100);
    },
});



/** @odoo-module **/
/**Working code commented on JAN 23 2026 by Vijaya bhaskar**/
/**import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUpdateProps } from "@odoo/owl";

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");
        this.action = useService("action");

        // Track initial field value
        this._initialCancelStatus = null;

        // Track if wizard has already been opened
        this._wizardOpened = false;

        // Check initial value on form load
        onMounted(async () => {
            const record = this.props.record;
            if (!record || record.resModel !== "project.task" || !record.resId) return;

            const resId = record.resId;
            const data = await this.orm.read("project.task", [resId], ["onhold_spareparts_status_check"]);
            this._initialCancelStatus = data?.[0]?.onhold_spareparts_status_check || false;

            console.log("[auto_cancel_reason] Initial onhold_spareparts_status_check =", this._initialCancelStatus);
        });

        // Check whenever record is updated
        onWillUpdateProps(() => this._checkCancelStatus());
    },
	 async _checkCancelStatus() {
	        try {
	            const record = this.props.record;
	            if (!record || record.resModel !== "project.task" || !record.resId) return;

	            if (this._wizardOpened) return;

	            const resId = record.resId;
	            const data = await this.orm.read("project.task", [resId], ["onhold_spareparts_status_check"]);
	            const cancelStatus = data?.[0]?.onhold_spareparts_status_check || false;

	            console.log("[auto_cancel_reason] Current onhold_spareparts_status_check =", cancelStatus);

	            // Only open wizard if field was initially false and now became true
	            if (cancelStatus && this._initialCancelStatus === false) {
	                this._wizardOpened = true;
	                console.log("[auto_cancel_reason] Opening Cancel Reason wizard automatically...");
	                await this.action.doAction({
	                    type: "ir.actions.act_window",
	                    name: "OnHold Spare Parts Reason",
	                    res_model: "onhold.spareparts.reason.wizard",
	                    view_mode: "form",
	                    views: [[false, "form"]],
	                    target: "new",
	                    context: { default_job_card_id: resId },
	                    flags: {
	                        // Important: use `modal: true` to force modal behavior
	                        modal: true,
	                        // Prevent quick close (top-right X)
	                        no_quick_close: true,
	                        // Disable default footer buttons
	                        hide_default_buttons: true,
	                    },
	                });
	            }

	        } catch (err) {
	            console.error("[onhold_spareparts_status_check] Error:", err);
	        }


	setTimeout(() => {
	    const closeButton = document.querySelector('.modal-header .btn-close');

	    if (closeButton) {
	        closeButton.style.display = 'none';
	        console.log('Close button hidden');
	    } else {
	        console.warn('Close button not found');
	    }
	}, 100);

	    },


});
**/

