/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Ksdashboardgraph } from "@ks_dashboard_ninja/components/ks_dashboard_graphs/ks_dashboard_graphs";

async function userHasPromoterBlockGroup(env) {
  return await env.services.orm.call("res.users", "has_group", [], {
    group_ext_id: "promoter.group_promoter_sales_donotshow",
  });
}

const originalOnClick = Ksdashboardgraph.prototype.onChartCanvasClick_funnel;

patch(Ksdashboardgraph.prototype, {
  async onChartCanvasClick_funnel(evt, item_id, item) {
    const item_data = this.ks_dashboard_data.ks_item_data[item_id];
    const model_name = item_data.ks_model_name;

    console.log("item_data", item_data);
    console.log("model_name", model_name);

    const blocked_models = [
      "promoter.showroom",
      "promoter.showroom.sales",
      "sales.target",
    ];
    const restricted = await userHasPromoterBlockGroup(this.env);

    if (restricted && blocked_models.includes(model_name)) {
      if (
        (item_data.max_sequnce !== 0 &&
          item_data.sequnce >= item_data.max_sequnce) ||
        item_data.max_sequnce === false
      ) {
        return;
      }
    }

    return originalOnClick.call(this, evt, item_id, item);
  },
});
