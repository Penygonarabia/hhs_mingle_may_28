/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";

// Clicking a history row opens the Analyser with that query loaded, instead of
// the default form view.
export class SqlMsHistoryController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    openRecord(record) {
        const query = record.data.query;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "database_studio.analyser",
            name: "Analyser",
            params: { query },
            context: { default_query: query },
        });
    }
}

registry.category("views").add("database_studio_history_list", {
    ...listView,
    Controller: SqlMsHistoryController,
});
