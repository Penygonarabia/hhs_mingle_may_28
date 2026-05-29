/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUpdateProps } from "@odoo/owl";
import { FormRenderer } from "@web/views/form/form_renderer";

let ACTIVE_FORM_RECORD = null;

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);

        this._prevCustomerSignature = null;

        // Store record when the form mounts
        onMounted(() => {
            const record = this.props.record;
            if (!record || record.resModel !== "project.task") return;

            ACTIVE_FORM_RECORD = record;
            this._prevCustomerSignature =
                record.data?.customer_signature_show_bool || false;
        });

        onWillUpdateProps((nextProps) => {
            const record = nextProps.record;
            if (!record || record.resModel !== "project.task") return;

            ACTIVE_FORM_RECORD = record;

            const current =
                record.data?.customer_signature_show_bool || false;

            // Auto-open customer signature tab if changed to true
            if (this._prevCustomerSignature === false && current === true) {
                setTimeout(() => {
                    const tab = [...document.querySelectorAll(
                        ".o_notebook_headers .nav-link"
                    )].find(
                        (el) =>
                            el.textContent.trim() === "Customer Signature"
                    );

                    if (tab && !tab.classList.contains("active")) {
                        tab.click();
                        console.log("[AUTO] Customer Signature tab opened");
                    }

                    setTimeout(() => {
                        const signatureDiv = document.querySelector(
                            ".o_field_signature .o_signature"
                        );
                        if (signatureDiv) {
                            signatureDiv.click();
                            console.log("[AUTO] Signature field focused");
                        } else {
                            console.warn(
                                "[AUTO] Signature field not found"
                            );
                        }
                    }, 300);
                }, 300);
            }

            this._prevCustomerSignature = current;
        });
    },
});

// =============================
// Signature modal Cancel handler
// =============================

document.addEventListener(
    "click",
    async (ev) => {
        const btn = ev.target.closest(
            ".modal-footer .btn.btn-secondary"
        );
        if (!btn) return;

        const modal = btn.closest(".o_dialog");
        if (!modal || !modal.querySelector(".o_web_sign_signature"))
            return;

        console.log("[SIGN MODAL] Cancel clicked");

        const record = ACTIVE_FORM_RECORD;
        if (!record) {
            console.warn("[SIGN MODAL] No active record found");
            return;
        }

        try {
            // 1️⃣ Reset customer signature flag
            await record.update({
                customer_signature_show_bool: false,
            });
            await record.save({ reload: false });

            console.log(
                "[SIGN MODAL] customer_signature_show_bool reset to FALSE"
            );

            // 2️⃣ Get previous job card state code
            const prev_state_code =
                record._initialTextValues
                    ?.previous_job_card_state_code;
			const prev_job_card_name = record._initialTextValues?.job_card_state_code;


            if (!prev_state_code) {
                console.warn(
                    "[SIGN MODAL] Previous job card state code not found"
                );
                return;
            }

            // 3️⃣ Find stage using code
            const result = await record.model.orm.searchRead(
                "project.task.type",
                [["code", "=", prev_state_code]],
                ["id", "name"],
                { limit: 1 }
            );

            if (!result.length) {
                console.warn(
                    "[SIGN MODAL] No matching stage found for code:",
                    prev_state_code
                );
                return;
            }

            const stage = result[0];

            // 4️⃣ Restore job card state (✅ MANY2ONE FIX)
            await record.update({
                job_state: [stage.id, stage.name], // ✅ REQUIRED FORMAT
                job_card_state_code: prev_state_code,
                job_card_state: stage.name,
				previous_job_card_state_code: prev_job_card_name,
            });

            await record.save({ reload: false });

            console.log(
                "[SIGN MODAL] Job card state restored:",
                stage.name
            );
        } catch (error) {
            console.error(
                "[SIGN MODAL] Error restoring job card state:",
                error
            );
        }
    },
    true
);