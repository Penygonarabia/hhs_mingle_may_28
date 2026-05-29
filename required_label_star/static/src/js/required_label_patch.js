/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormLabel } from "@web/views/form/form_label";
import { fieldVisualFeedback } from "@web/views/fields/field";
import { _t } from "@web/core/l10n/translation";
// /home/cielovengatesh/odoo17/addons/web/static/src/views/form/form_label.js
// console.log('the file is loaded');
patch(FormLabel.prototype, {
   get className() {
        const { invalid, empty, readonly,required} = fieldVisualFeedback(
            this.props.fieldInfo.field,
            this.props.record,
            this.props.fieldName,
            this.props.fieldInfo
        );
        const classes = this.props.className ? [this.props.className] : [];
        if (invalid) {
            classes.push("o_field_invalid");
        }
        if (empty) {
            classes.push("o_form_label_empty");
        }
        if (readonly && !this.props.notMuttedLabel) {
            classes.push("o_form_label_readonly");
        }
          if (required) {
            classes.push("o_form_label_required");
        }
        return classes.join(" ");
    }
});
