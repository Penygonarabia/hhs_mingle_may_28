/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { copyToClipboard } from "./copy_to_clipboard";

/**
 * Read-only char field that shows a copy icon next to the value, rendered only
 * when the value is non-blank. Used for the Email fields on the Module Rights
 * setup forms. Copy works over plain http via copyToClipboard's fallback.
 */
export class CopyEmailChar extends Component {
    static template = "module_rights.CopyEmailChar";
    static props = { ...standardFieldProps };

    setup() {
        this.notification = useService("notification");
    }

    get email() {
        return (this.props.record.data[this.props.name] || "").trim();
    }

    async onCopy() {
        const email = this.email;
        if (!email) {
            return;
        }
        const ok = await copyToClipboard(email);
        this.notification.add(ok ? `Copied: ${email}` : "Could not copy the email.", {
            type: ok ? "success" : "danger",
        });
    }
}

export const copyEmailChar = {
    component: CopyEmailChar,
    displayName: "Copy Email",
    supportedTypes: ["char"],
};

registry.category("fields").add("copy_email_char", copyEmailChar);
