/** @odoo-module **/
import { Component, useEffect, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * Hides the form's native save / refresh status indicator until the user has
 * clicked **Load Dashboards** (i.e. until `lines_loaded` is True).
 *
 * Header-only edits (picking a user_id) still dirty the form, but the
 * indicator buttons stay hidden so the user isn't prompted to save a
 * half-set-up wizard. Once dashboards are loaded, the indicator behaves
 * normally — toggling Has Access on a row shows the icons as usual.
 */
class HeaderStatusGate extends Component {
    static template = "dashboard_rights.HeaderStatusGate";
    static props = ["record", "*"];

    setup() {
        useEffect(
            (linesLoaded) => {
                document.body.classList.toggle("dr_matrix_pre_load", !linesLoaded);
            },
            () => [!!this.props.record.data.lines_loaded]
        );
        onWillUnmount(() => {
            document.body.classList.remove("dr_matrix_pre_load");
        });
    }
}

registry.category("view_widgets").add("header_status_gate", {
    component: HeaderStatusGate,
});
