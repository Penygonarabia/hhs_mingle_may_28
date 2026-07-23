/** @odoo-module **/
import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Restores the "Dashboard Rights" parent breadcrumb when the matrix form is
 * opened directly via URL (e.g. browser refresh).
 *
 * On a hard refresh, Odoo only puts the current form's action on the
 * controller stack — the original list-view breadcrumb is lost. This widget
 * detects that case (breadcrumbs.length <= 1) and re-runs:
 *   1) doAction(list, clearBreadcrumbs)  → stack = [list]
 *   2) doAction(matrix with res_id)      → stack = [list, matrix]
 *
 * noEmptyTransition keeps the visual flash minimal.
 */
class ParentBreadcrumbRestore extends Component {
    static template = "dashboard_rights.ParentBreadcrumbRestore";
    static props = ["record", "*"];

    setup() {
        this.actionService = useService("action");
        this._restored = false;
        onMounted(() => this._restoreParent());
    }

    async _restoreParent() {
        if (this._restored) return;
        const breadcrumbs = this.env.config?.breadcrumbs;
        if (!breadcrumbs || breadcrumbs.length > 1) return;
        const resId = this.props.record.resId;
        if (!resId) return;
        this._restored = true;
        try {
            await this.actionService.doAction(
                "dashboard_rights.action_dashboard_rights_list",
                { clearBreadcrumbs: true, noEmptyTransition: true }
            );
            await this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "dashboard.rights.matrix",
                res_id: resId,
                view_mode: "form",
                views: [[false, "form"]],
                target: "current",
            });
        } catch (_e) {
            // Silent fail — the in-form back link still works.
        }
    }
}

registry.category("view_widgets").add("parent_breadcrumb_restore", {
    component: ParentBreadcrumbRestore,
});
