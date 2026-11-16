/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { Component } from "@odoo/owl";

/** "Print Leads - Excel": exports every lead matching the current search. */
export class PrintLeadsExcel extends Component {
    static template = "crm_commercial.PrintLeadsExcel";
    static components = { DropdownItem };

    async onPrintLeads() {
        // The dropdown unmounts this component on select, so use the raw
        // env services (useService wrappers reject once the component is destroyed).
        const { orm, action } = this.env.services;
        const { domain, context } = this.env.searchModel;
        const ids = await orm.search("crm.commercial.lead", domain, { context });
        const report = await orm.call("crm.commercial.lead", "action_print_leads_xlsx", [ids]);
        await action.doAction(report);
    }
}

registry.category("cogMenu").add(
    "print-leads-excel-menu",
    {
        Component: PrintLeadsExcel,
        groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
        isDisplayed: async (env) =>
            env.config.viewType === "list" &&
            env.searchModel.resModel === "crm.commercial.lead" &&
            !env.model.root.selection.length,
    },
    { sequence: 5 }
);
