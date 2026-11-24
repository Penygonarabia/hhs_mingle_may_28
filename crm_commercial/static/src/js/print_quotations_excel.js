/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { Component } from "@odoo/owl";

/** "Print Quotation (Excel)": exports every quotation matching the current search. */
export class PrintQuotationsExcel extends Component {
    static template = "crm_commercial.PrintQuotationsExcel";
    static components = { DropdownItem };

    async onPrintQuotations() {
        // The dropdown unmounts this component on select, so use the raw
        // env services (useService wrappers reject once the component is destroyed).
        const { orm, action } = this.env.services;
        const { domain, context } = this.env.searchModel;
        const ids = await orm.search("crm.commercial.quotation", domain, { context });
        const report = await orm.call("crm.commercial.quotation", "action_print_quotations_xlsx", [ids]);
        await action.doAction(report);
    }
}

registry.category("cogMenu").add(
    "print-quotations-excel-menu",
    {
        Component: PrintQuotationsExcel,
        groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
        isDisplayed: async (env) =>
            env.config.viewType === "list" &&
            env.searchModel.resModel === "crm.commercial.quotation" &&
            !env.model.root.selection.length,
    },
    { sequence: 6 }
);
