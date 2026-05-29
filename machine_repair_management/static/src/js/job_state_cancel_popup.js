/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useService } from "@web/core/utils/hooks";

class OpenWizardClientAction extends Component {
    static template = "machine_repair_management.OpenWizardClientAction";
    setup() {
        this.actionService = useService("action");
    }

    async openWizard() {
        const action = {
            type: "ir.actions.act_window",
            res_model: "cancelled.reason.wizard",
            view_mode: "form",
            target: "new",
            views: [[false, "form"]],
            context: {
                default_job_card_id: this.props.job_card_id,
            },
        };
        await this.actionService.doAction(action);
    }
}

registry.category("actions").add("open_cancelled_wizard", OpenWizardClientAction);
/*

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Field } from "@web/views/fields/field";

const JobStateField = {
    ...Field,
    mounted() {
        this._super(...arguments);
        this.action = useService("action");
        this.on("change", this, this._onJobStateChange.bind(this));
    },
    _onJobStateChange() {
        const value = this.value; // Assuming job_state is a many2one field
        if (value) {
            this.env.model.orm.call(
                'project.task', // Replace with the model of job_state
                'read',
                [value],
                { fields: ['code'] }
            ).then((result) => {
                if (result[0].code === '124') {
                    this.action.doAction({
                        type: 'ir.actions.act_window',
                        name: 'Cancelled Reason',
                        res_model: 'cancelled.reason.wizard',
                        view_mode: 'form',
                        views: [[false, 'form']],
                        target: 'new',
                        context: { default_job_card_id: this.record.data.id },
                    });
                }
            });
        }
    },
};

registry.category("fields").add("job_state_field", JobStateField);*/
/*import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    name: "cancel_popup_on_statusbar",
    async _onStatusbarClick(ev) {
        // Call the parent method first
        const result = await super._onStatusbarClick(ev);

        const fieldName = ev.currentTarget.dataset.field;
        if (fieldName === "job_state") {
            const newState = ev.currentTarget.dataset.value;
            if (newState && newState.includes("124")) {
                this.env.services.action.doAction({
                    type: "ir.actions.act_window",
                    name: "Cancelled Reason",
                    res_model: "cancelled.reason.wizard",
                    view_mode: "form",
                    target: "new",
                    context: {
                        default_job_card_id: this.model.root.data.id,
                    },
                });
            }
        }
        return result;
    },
});*/
