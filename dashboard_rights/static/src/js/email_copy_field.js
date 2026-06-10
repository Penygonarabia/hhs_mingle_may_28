/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Two-stage clipboard copy:
 *   1. navigator.clipboard.writeText() — modern API, requires HTTPS / localhost
 *   2. document.execCommand("copy") via hidden textarea — HTTP fallback
 */
async function robustCopy(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
            await navigator.clipboard.writeText(text);
            return;
        } catch (_e) {
            // fall through to execCommand fallback
        }
    }
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText =
        "position:fixed;top:-9999px;left:-9999px;opacity:0;pointer-events:none";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
        if (!document.execCommand("copy")) {
            throw new Error("execCommand copy returned false");
        }
    } finally {
        document.body.removeChild(ta);
    }
}

export class EmailCopyField extends Component {
    static template = "dashboard_rights.EmailCopyField";

    setup() {
        this.notification = useService("notification");
        this.state = useState({ copied: false });
    }

    get displayValue() {
        return (this.props.record.data[this.props.name] || "");
    }

    async onCopy(ev) {
        ev.stopPropagation();
        const text = this.displayValue;
        if (!text) return;
        try {
            await robustCopy(text);
            this.state.copied = true;
            this.notification.add("Email copied to clipboard!", {
                type: "success",
                sticky: false,
            });
            setTimeout(() => {
                this.state.copied = false;
            }, 2000);
        } catch (_e) {
            this.notification.add(
                "Could not copy automatically — please select and copy the email manually.",
                { type: "warning" }
            );
        }
    }
}

registry.category("fields").add("email_copy_char", {
    component: EmailCopyField,
    displayName: "Email (Copy)",
    supportedTypes: ["char"],
});
