/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class DashboardBulkButtons extends Component {
    static template = "dashboard_rights.BulkButtons";
    static props = ["record", "readonly?", "*"];

    setup() {
        this._busy = false;
    }

    /**
     * Stage a Has Access value on every loaded dashboard row *in the browser*.
     *
     * Nothing is written to the database here: the rows are simply selected
     * (true) or unselected (false) and the form is left dirty, so the change is
     * only committed when the user clicks Save — and reverted by the Refresh
     * (discard) icon. The server `_onchange_line_ids_cascade` keeps the
     * group rows and their `granted/total` counts in sync as each row updates.
     */
    async _applyBulk(value) {
        const record = this.props.record;
        if (this._busy) {
            return;
        }
        this._busy = true;
        try {
            const list = record.data.line_ids;
            if (list && list.records) {
                for (const line of list.records) {
                    if (line.data.has_access !== value) {
                        await line.update({ has_access: value });
                    }
                }
            }
        } finally {
            this._busy = false;
        }
    }

    onGrantAll(ev) {
        ev.stopPropagation();
        this._applyBulk(true);
    }

    onRevokeAll(ev) {
        ev.stopPropagation();
        this._applyBulk(false);
    }
}

registry.category("view_widgets").add("dashboard_bulk_buttons", {
    component: DashboardBulkButtons,
});
