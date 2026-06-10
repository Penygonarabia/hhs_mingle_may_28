/** @odoo-module **/
import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Invisible widget placed at the top of the Users tab page.
 *
 * When the Users tab becomes active (first open or returning to it), this widget:
 *  1. Calls action_reload_users_tab on the server — which deletes and recreates the
 *     user_list_ids records so their IDs change.  New IDs = new pool objects on the
 *     client = no stale dashboard_rights_given cache.
 *  2. Calls record.load() to fetch the parent record with the freshly-created sub-records.
 *
 * Crucially, doAction is NOT used here, so the breadcrumb navigation is preserved.
 *
 * The refresh is skipped when the form has unsaved changes (isDirty) to avoid
 * silently discarding in-progress edits.
 */
class UsersTabRefresh extends Component {
    static template = "dashboard_rights.UsersTabRefresh";
    static props = ["record", "readonly?", "*"];

    setup() {
        this.root = useRef("root");
        this.orm = useService("orm");
        this._observer = null;
        this._wasActive = false;
        this._refreshing = false;

        onMounted(() => {
            const page = this._findPage();
            if (!page) return;

            this._wasActive = page.classList.contains("active");
            this._attachObserver(page);

            // Case 1: tab is already active when the widget mounts (first click on Users tab)
            if (this._wasActive) {
                this._refresh();
            }
        });

        onWillUnmount(() => {
            this._observer?.disconnect();
            this._observer = null;
        });
    }

    _findPage() {
        let el = this.root.el;
        while (el && el !== document.body) {
            if (el.getAttribute?.("role") === "tabpanel" || el.classList?.contains("tab-pane")) {
                return el;
            }
            el = el.parentElement;
        }
        return null;
    }

    _attachObserver(page) {
        this._observer = new MutationObserver(() => {
            const isActive = page.classList.contains("active");
            if (isActive && !this._wasActive) {
                // Case 2: transition from another tab to this one
                this._wasActive = true;
                this._refresh();
            } else if (!isActive) {
                this._wasActive = false;
            }
        });
        this._observer.observe(page, { attributes: true, attributeFilter: ["class"] });
    }

    async _refresh() {
        const record = this.props.record;

        // Don't refresh if the form has unsaved changes
        if (record.isDirty) return;
        // Don't refresh for a new unsaved record (no ID yet)
        if (!record.resId) return;
        // Prevent concurrent refreshes
        if (this._refreshing) return;

        this._refreshing = true;
        try {
            // Server recreates user_list_ids records (new IDs → bypasses stale pool cache)
            await this.orm.call(
                "dashboard.rights.matrix",
                "action_reload_users_tab",
                [[record.resId]]
            );
            // record.load() fetches the parent with the new sub-record IDs + fresh field values.
            // This does NOT call doAction, so the breadcrumb is untouched.
            await record.load();
        } catch (_e) {
            // Silent fail — Users tab will just show existing data
        } finally {
            this._refreshing = false;
        }
    }
}

registry.category("view_widgets").add("users_tab_refresh", {
    component: UsersTabRefresh,
});
