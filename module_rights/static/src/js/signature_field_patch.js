/** @odoo-module **/
/**
 * Patch for an Odoo 17 web core bug.
 *
 * ``SignatureField.onLoadFailed`` calls ``this.notification.add(...)`` but
 * the field's ``setup()`` only injects ``dialogService`` — ``notification``
 * is never wired up. The result: any time a signature image fails to load
 * (broken URL, deleted attachment), the form crashes with a hard
 * ``Cannot read properties of undefined (reading 'add')`` instead of
 * silently failing back to the placeholder.
 *
 * This patch:
 *   1. lazily resolves ``this.notification`` from the environment when the
 *      handler runs, so the failure path no longer touches an undefined
 *      property; and
 *   2. degrades to a silent no-op when the notification service is not
 *      available (e.g. in headless test rigs).
 *
 * Lives in ``dashboard_rights`` because that module is installed on every
 * environment we ship and has no Ninja dependency — keeps the patch where
 * it's loaded regardless of which dashboard modules are present.
 */
import { patch } from "@web/core/utils/patch";
import { SignatureField } from "@web/views/fields/signature/signature_field";

patch(SignatureField.prototype, {
    onLoadFailed() {
        this.state.isValid = false;
        const notification =
            this.notification || (this.env && this.env.services && this.env.services.notification);
        if (notification && typeof notification.add === "function") {
            notification.add(
                this.env._t
                    ? this.env._t("Could not display the selected image")
                    : "Could not display the selected image",
                { type: "danger" },
            );
        }
    },
});
