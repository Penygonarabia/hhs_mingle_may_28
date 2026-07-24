/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { copyToClipboard } from "./copy_to_clipboard";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class GroupedUserList extends X2ManyField {
    static template = "module_rights.GroupedUserList";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ collapsed: {} });
    }

    /** Copy a user's email to the clipboard (http-safe, see copyToClipboard). */
    async copyEmail(email) {
        email = (email || "").trim();
        if (!email) {
            return;
        }
        const ok = await copyToClipboard(email);
        this.notification.add(
            ok ? `Copied: ${email}` : "Could not copy the email.",
            { type: ok ? "success" : "danger" }
        );
    }

    get groups() {
        // Read the search text from the parent form record — this is reactive in OWL,
        // so the getter re-runs whenever the user types in the search box.
        const q = (this.props.record.data.user_search_text_tab || "").toLowerCase().trim();

        // this.list is X2ManyField's getter: returns this.props.value (the StaticList)
        const records = this.list?.records ?? [];

        const filtered = q
            ? records.filter(rec =>
                (rec.data.user_name  || "").toLowerCase().includes(q) ||
                (rec.data.user_email || "").toLowerCase().includes(q) ||
                (rec.data.user_role  || "").toLowerCase().includes(q)
            )
            : records;

        const map = {};
        for (const rec of filtered) {
            // Match the list view's group label for users without a role.
            const role = rec.data.user_role || "Role Not Assigned Users";
            if (!map[role]) map[role] = [];
            map[role].push(rec);
        }
        return Object.entries(map)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([role, users]) => ({ role, users }));
    }

    toggleGroup(role) {
        this.state.collapsed[role] = !this.state.collapsed[role];
    }

    isCollapsed(role) {
        return !!this.state.collapsed[role];
    }

    async onSelectUser(record) {
        // Use the underlying user_id (stable) + the parent matrix id, NOT the
        // matrix.user line's own resId — that resId is invalidated whenever
        // the Users-tab refresh unlinks-and-recreates the lines.
        const userIdField = record?.data?.user_id;
        const userId = Array.isArray(userIdField) ? userIdField[0] : userIdField;
        const matrixId = this.props.record.resId;
        if (!userId || !matrixId) return;
        const action = await this.orm.call(
            "dashboard.rights.matrix",
            "action_select_user_id",
            [[matrixId], userId]
        );
        if (action) {
            // Odoo 17 _preprocessAction requires a `views` array.
            // Add it if the server didn't include it.
            if (action.type === "ir.actions.act_window" && !action.views) {
                action.views = [[action.view_id || false, action.view_mode || "form"]];
            }
            await this.actionService.doAction(action);
        } else {
            // action_load_dashboards returns False to avoid pushing a new
            // breadcrumb entry. Reload the parent record in place so the
            // header reflects the newly-selected user_id.
            await this.props.record.load();
        }

        // Focus back to the Dashboards tab after user selection
        setTimeout(() => {
            const dashboardTab = document.querySelector('.dr_matrix_form .o_notebook a.nav-link[name="dashboards"]');
            if (dashboardTab) {
                dashboardTab.click();
            }
        }, 150);
    }
}

registry.category("fields").add("grouped_user_list", {
    ...x2ManyField,
    component: GroupedUserList,
});
