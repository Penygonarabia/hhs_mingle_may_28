/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    CopyClipboardCharField,
    copyClipboardCharField,
} from "@web/views/fields/copy_clipboard/copy_clipboard_field";

/**
 * Char field that renders the standard CopyClipboardChar layout but
 * forces the button label to "Copy Email ID" (the field's `string`
 * attribute is consumed by Odoo's view compiler for the form label,
 * so it never reaches the widget's copyText).
 */
class EmailIdCopyField extends CopyClipboardCharField {
    setup() {
        super.setup();
        this.copyText = _t("Copy Email ID");
    }
}

registry.category("fields").add("email_id_copy", {
    ...copyClipboardCharField,
    component: EmailIdCopyField,
});
