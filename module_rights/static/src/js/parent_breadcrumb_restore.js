/** @odoo-module **/
import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Restores a plain "Module Rights" breadcrumb when the matrix form is
 * opened directly via URL (e.g. browser refresh) instead of the usual
 * click-through from Users Setup / Module Rights Setup.
 *
 * On a hard refresh, Odoo only puts the current form's action on the
 * controller stack — the original list-view breadcrumb is lost, so
 * FormController.displayName() (which always prefers
 * record.data.display_name — here the CONFIGURED USER's name, e.g.
 * "Afsal") ends up as an orphaned, unclickable single crumb reading just
 * that user's name. This widget detects that case (breadcrumbs.length <=
 * 1) and re-runs:
 *   1) doAction(action_dashboard_rights_list, clearBreadcrumbs) → stack =
 *      [list] — its breadcrumb reads "Module Rights".
 *   2) doAction(matrix/module-matrix form, res_id)               → stack =
 *      [list, form] — stacked on top, same pattern proven to work.
 * An ad-hoc action object opened WITH clearBreadcrumbs in a single step
 * was tried and reliably hangs (doAction never resolves) — this two-step
 * shape is the one that actually completes, so it's kept even though it
 * produces two crumbs under the hood.
 *
 * The second crumb would read the configured user's name (e.g. "Afsal") —
 * exactly the bit that should disappear. Rather than fight
 * FormController's onRendered, which re-asserts record.display_name as
 * that crumb's text on every render (a one-time overwrite gets clobbered
 * on the very next reactive tick), a MutationObserver just hides that
 * LAST breadcrumb item's DOM node for as long as this widget stays
 * mounted, leaving only the first crumb, "Module Rights", visible.
 *
 * The ordinary click-through breadcrumb (Users Setup / <user>, reached by
 * clicking a row) is untouched by any of this — it never hits this
 * fallback since its breadcrumb stack already has more than one entry.
 *
 * `resModel` is read from the record itself (not hardcoded) because this
 * same widget is embedded in both dashboard.rights.matrix ("Users Setup"
 * / Rights Setup) and access.rights.module.matrix ("Module Rights Setup")
 * — hardcoding one would reopen the WRONG model's record for the other.
 *
 * noEmptyTransition keeps the visual flash minimal.
 */
class ParentBreadcrumbRestore extends Component {
    static template = "module_rights.ParentBreadcrumbRestore";
    static props = ["record", "*"];

    setup() {
        this.actionService = useService("action");
        this._restored = false;
        this._breadcrumbObserver = null;
        onMounted(() => this._restoreParent());
        onWillUnmount(() => this._breadcrumbObserver?.disconnect());
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
                "module_rights.action_dashboard_rights_list",
                { clearBreadcrumbs: true, noEmptyTransition: true }
            );
            await this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: this.props.record.resModel,
                res_id: resId,
                view_mode: "form",
                views: [[false, "form"]],
                target: "current",
            });
            this._hideLastBreadcrumb();
        } catch (_e) {
            // Silent fail — the in-form back link still works.
        }
    }

    _hideLastBreadcrumb() {
        const apply = () => {
            const el = document.querySelector(".o_last_breadcrumb_item");
            // !important: the active backend theme forces this element's
            // display via its own `!important` rule, which beats a plain
            // inline style (confirmed: getComputedStyle stayed "flex" even
            // with el.style.display set to "none" — only setProperty's own
            // "important" priority actually wins over that).
            if (el && el.style.getPropertyValue("display") !== "none") {
                el.style.setProperty("display", "none", "important");
            }
        };
        apply();
        const target = document.querySelector(".o_breadcrumb");
        if (!target) return;
        this._breadcrumbObserver = new MutationObserver(apply);
        this._breadcrumbObserver.observe(target, {
            childList: true,
            subtree: true,
            characterData: true,
        });
    }
}

registry.category("view_widgets").add("parent_breadcrumb_restore", {
    component: ParentBreadcrumbRestore,
});
