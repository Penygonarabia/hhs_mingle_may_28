/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

/**
 * Contract Phase 2 - list styling scope hook.
 *
 * The "Product Consume Part/Service" one2many grid on the job card is a
 * SHARED base view used by every job card type (regular/AMC/Service &
 * Repair), so it can't be given the o_cp2_grid class in XML without also
 * styling that grid for non-S&R cards - which the module must not do.
 *
 * This widget is a thin subclass of the stock one2many/many2many field: it
 * behaves exactly like `widget="one2many"` (same component, same props),
 * and only adds the `o_cp2_grid` marker class - and only when the record
 * showing the field is a Service & Repair job card
 * (job_card_type == 'service_repair'). Every other job card type, and every
 * other x2many field in the database, is completely unaffected since they
 * never use this widget.
 */
export class Cp2ScopedX2ManyField extends X2ManyField {
    setup() {
        super.setup();
        if (this.props.record.data.job_card_type === "service_repair") {
            this.className = `${this.className} o_cp2_grid`;
        }
    }
}

export const cp2ScopedX2ManyField = {
    ...x2ManyField,
    component: Cp2ScopedX2ManyField,
};

registry.category("fields").add("cp2_scoped_list", cp2ScopedX2ManyField);
