/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class DashboardBulkButtons extends Component {
    static template = "dashboard_rights.BulkButtons";
    static props = ["record", "readonly?", "*"];

    setup() {
        this.orm = useService("orm");
    }

    get lines() {
        return this.props.record.data.visible_line_ids?.records || [];
    }

    async _applyBulk(value) {
        // 1) Reflect change in the open form immediately so the UI is responsive.
        for (const line of this.lines) {
            await line.update({ has_access: value });
        }
        // 2) Persist directly to dashboard.rights server-side, so the change
        //    survives a page refresh without depending on the form Save.
        const matrixId = this.props.record.resId;
        if (!matrixId) {
            return;
        }
        const lineIds = this.lines
            .map((l) => l.resId)
            .filter((id) => typeof id === "number");
        await this.orm.call(
            "dashboard.rights.matrix",
            "action_bulk_set_access",
            [[matrixId], value, lineIds],
        );
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
