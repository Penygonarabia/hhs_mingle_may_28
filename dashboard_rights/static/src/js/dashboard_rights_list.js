/** @odoo-module **/

import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Optional columns that, when all hidden, should collapse the list to unique users.
 */
const OPTIONAL_COLLAPSE_FIELDS = ["dashboard_top_menu_id", "dashboard_id", "has_access"];

/**
 * Custom list renderer for dashboard.rights.
 *
 * Clicking any data row opens the rights-matrix wizard pre-filled and
 * fully loaded for that row's user (Header + Dashboards tab + Users tab).
 *
 * Clicking the boolean_toggle in the Has Access column is passed through
 * unchanged so the toggle still flips the value without navigating.
 *
 * NOTE: in this build of Odoo 17, openRecord is a *prop* (not a method
 * on ListRenderer), so we override onCellClicked instead.
 */
class DashboardRightsListRenderer extends ListRenderer {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    getGroupDisplayName(group) {
        if (group.groupByField.name === "user_role" && !group.value) {
            return "Role Not Assigned Users";
        }
        return super.getGroupDisplayName(group);
    }

    async onCellClicked(record, column, ev) {
        // Let boolean_toggle clicks (has_access) pass through unchanged
        if (ev.target.closest(".o_boolean_toggle") || ev.target.closest(".o_field_boolean")) {
            return super.onCellClicked(record, column, ev);
        }
        // Let the Dashboard column be edited inline (m2o picker) instead of
        // hijacking the click to open the matrix wizard.
        if (column && column.name === "dashboard_id") {
            return super.onCellClicked(record, column, ev);
        }
        // Any other row click → open the matrix wizard for this user
        const action = await this.orm.call(
            "dashboard.rights",
            "action_open_matrix",
            [[record.resId]]
        );
        if (action) {
            await this.actionService.doAction(action);
        }
    }
}

/**
 * Custom list controller for dashboard.rights.
 *
 * Overrides createRecord so the "New" button opens a blank
 * dashboard.rights.matrix form (the user-centric wizard) instead of
 * trying to create a raw dashboard.rights record directly.
 *
 * Overrides onOptionalFieldsChanged to reload with unique_users_only
 * context when all optional columns are hidden, so only one row per
 * user is shown in the default compact view.
 */
class DashboardRightsListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        if (this.props.archInfo && this.props.archInfo.activeActions) {
            this.props.archInfo.activeActions.create = false;
        }
        if (this.activeActions) {
            this.activeActions.create = false;
        }
    }

    async createRecord() {
        const action = await this.orm.call(
            "dashboard.rights.matrix",
            "action_new_wizard",
            []
        );
        await this.actionService.doAction(action);
    }

    /**
     * Called whenever the user toggles an optional column visibility.
     * When ALL collapse-triggering optional columns are hidden we reload
     * the list with unique_users_only=True so the server returns only one
     * row per user.  When any of them becomes visible, we reload without
     * the flag so all rows are shown again.
     */
    onOptionalFieldsChanged(optionalActiveFields) {
        super.onOptionalFieldsChanged(optionalActiveFields);

        const allHidden = OPTIONAL_COLLAPSE_FIELDS.every(
            (f) => !optionalActiveFields[f]
        );

        const currentCtx = this.model.root.context || {};
        const wasUnique = !!currentCtx.unique_users_only;

        // Only reload if the flag state actually changed
        if (allHidden !== wasUnique) {
            const newCtx = { ...currentCtx, unique_users_only: allHidden };
            this.model.load({ context: newCtx });
        }
    }
}

// Assign groupRowTemplate the same way Odoo core does (post-class, not static field)
// so it is definitely set on the constructor object before OWL reads it.
DashboardRightsListRenderer.groupRowTemplate = "dashboard_rights.ListRenderer.GroupRow";

registry.category("views").add("dashboard_rights_list", {
    ...listView,
    Renderer: DashboardRightsListRenderer,
    Controller: DashboardRightsListController,
});
