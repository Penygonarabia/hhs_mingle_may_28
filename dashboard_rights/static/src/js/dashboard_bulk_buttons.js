/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class DashboardBulkButtons extends Component {
    static template = "dashboard_rights.BulkButtons";
    static props = ["record", "readonly?", "*"];

    get lines() {
        return this.props.record.data.visible_line_ids?.records || [];
    }

    async _applyBulk(value) {
        for (const line of this.lines) {
            if (!line.data.is_user_admin) {
                await line.update({ has_access: value });
            }
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
