/*import { registry } from "@web/core/registry";
import { StatusBarButtons } from "@web/views/form/widgets/status_bar_buttons/status_bar_buttons";
 
// Extend StatusBar only for project.task
const StatusBarNoTriggerTask = StatusBar => class extends StatusBar {
    async _onClickStatus(ev) {
        // Check if the current model is project.task
        if (this.props.model === 'project.task') {
            ev.preventDefault();
            ev.stopPropagation();
            // Only visual change, no backend triggered
            console.log("project.task status clicked, no backend triggered");
        } else {
            // Call original behavior for other models
            return super._onClickStatus(ev);
        }
    }
};
 
// Register the extension
registry.category("views").add("statusbar_no_trigger_task", StatusBarNoTriggerTask, {force: true});
 */