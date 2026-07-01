/** @odoo-module **/

/*
 * Loyalty Analysis · "Points issued" drilldown redirect.
 *
 * Desired flow:
 *   Region -> City -> Customer (bar)  -> points-history LIST (kept)
 *   click a list row                  -> that customer's res.partner FORM
 *
 * i.e. KEEP the points-history list, but skip the intermediate
 * points-history *form* page: a row click jumps straight to the customer's
 * Odoo contact form.
 *
 * Two scoped patches:
 *
 * 1) Ksdashboardgraph.onChartCanvasClick_funnel - bar/funnel chart click
 *    handler (see charts_render_global_functions.js). At the final drill level
 *    of the "Points issued" chart we open the points-history list ourselves so
 *    we can tag it with a context flag (ks_loyalty_redirect_partner). This
 *    keeps the default list but lets us scope the row-click redirect to this
 *    chart only (so "Points redeemed" - same model - is unaffected).
 *
 * 2) ListController.openRecord - when a row is opened in a list carrying that
 *    flag, open the related res.partner form (via the row's customer_no)
 *    instead of the points-history form.
 *
 * Anything unexpected falls back to super / default behaviour.
 */

import { patch } from "@web/core/utils/patch";
import { Ksdashboardgraph } from "@ks_dashboard_ninja/components/ks_dashboard_graphs/ks_dashboard_graphs";
import { ListController } from "@web/views/list/list_controller";

const POINTS_HISTORY_MODEL = "customer.loyalty.points.history";
// Charts whose customer-level drilldown should redirect row clicks to the
// customer's res.partner form (same model + Region/City/Customer drill).
const REDIRECT_CHART_NAMES = ["Points issued", "Points redeemed"];
const REDIRECT_FLAG = "ks_loyalty_redirect_partner";

function ksOpenPartnerForm(actionService, partnerId) {
    actionService.doAction({
        type: "ir.actions.act_window",
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
        view_mode: "form",
        target: "current",
    });
}

// Mirror onChartCanvasClick_funnel's own logic for resolving the clicked bar
// index, so we read the exact same per-bar domain it would have used.
function ksResolveClickedDomain(evt, item_data) {
    const chart_data = JSON.parse(item_data["ks_chart_data"]);
    const labels = chart_data["labels"] || [];
    const domains = chart_data["domains"] || [];
    const activePoint = evt && evt.target && evt.target.dataItem ? evt.target.dataItem.dataContext : undefined;
    if (!activePoint) {
        return false;
    }
    let index;
    if (
        typeof activePoint.ksRowIndex === "number" &&
        activePoint.ksRowIndex >= 0 &&
        activePoint.ksRowIndex < labels.length
    ) {
        index = activePoint.ksRowIndex;
    } else if (activePoint.category) {
        for (let i = 0; i < labels.length; i++) {
            if (labels[i] == activePoint.category) {
                index = i;
            }
        }
    } else if (activePoint.stage) {
        for (let i = 0; i < labels.length; i++) {
            if (labels[i] == activePoint.stage) {
                index = i;
            }
        }
    }
    return index === undefined ? false : domains[index];
}

patch(Ksdashboardgraph.prototype, {
    async onChartCanvasClick_funnel(evt, item_id, item) {
        try {
            if (!(this.env.inDialog || this.env.mode === "edit")) {
                const item_data = this.ks_dashboard_data.ks_item_data[item_id];
                const sequnce = item_data && item_data.sequnce ? item_data.sequnce : 0;
                // Final level == the branch where the funnel handler would open
                // records instead of drilling further.
                const isFinalLevel =
                    item_data && !(item_data.max_sequnce != 0 && sequnce < item_data.max_sequnce);

                if (
                    isFinalLevel &&
                    item_data.ks_model_name === POINTS_HISTORY_MODEL &&
                    REDIRECT_CHART_NAMES.includes(item_data.name) &&
                    item_data.ks_show_records
                ) {
                    const domain = ksResolveClickedDomain(evt, item_data);
                    if (domain) {
                        // Keep the points-history list, but tag it so the row
                        // click (handled below) redirects to the partner.
                        this.actionService.doAction(
                            {
                                name: item_data.name,
                                type: "ir.actions.act_window",
                                res_model: POINTS_HISTORY_MODEL,
                                domain: typeof domain === "string" ? JSON.parse(domain) : domain,
                                views: [
                                    [false, "list"],
                                    [false, "form"],
                                ],
                                view_mode: "list",
                                target: "current",
                                context: { [REDIRECT_FLAG]: 1, group_by: false },
                            },
                            { on_reverse_breadcrumb: this.on_reverse_breadcrumb }
                        );
                        return;
                    }
                }
            }
        } catch (e) {
            // Any unexpected DOM/domain shape: fall back to the default behaviour.
        }
        return super.onChartCanvasClick_funnel(...arguments);
    },
});

patch(ListController.prototype, {
    async openRecord(record) {
        try {
            if (
                this.props.context &&
                this.props.context[REDIRECT_FLAG] &&
                record.resModel === POINTS_HISTORY_MODEL
            ) {
                const partner = record.data.customer_no;
                const partnerId = Array.isArray(partner) ? partner[0] : partner;
                if (partnerId) {
                    ksOpenPartnerForm(this.actionService, partnerId);
                    return;
                }
            }
        } catch (e) {
            // Fall back to the default record opening on any unexpected shape.
        }
        return super.openRecord(record);
    },
});
