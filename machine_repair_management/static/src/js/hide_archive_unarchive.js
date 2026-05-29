/** @odoo-module **/

/*import { patch } from "@web/core/utils/patch";
import { ControlPanel } from "@web/views/control_panel/control_panel";
import { ListRenderer } from "@web/views/list/list_renderer";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

const MODELS_TO_HIDE_ARCHIVE = ["project.task"];

// Patch ListRenderer to disable archiving
patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        if (MODELS_TO_HIDE_ARCHIVE.includes(this.props.model)) {
            this.archivable = false;
            console.log(`[ListRenderer] Archiving disabled for model: ${this.props.model}`);
        }
    },
});

// Patch KanbanRenderer to disable archiving
patch(KanbanRenderer.prototype, {
    setup() {
        super.setup();
        if (MODELS_TO_HIDE_ARCHIVE.includes(this.props.model)) {
            this.archivable = false;
            console.log(`[KanbanRenderer] Archiving disabled for model: ${this.props.model}`);
        }
    },
});

// Patch ControlPanel to remove archive/unarchive actions
patch(ControlPanel.prototype, {
    setup() {
        super.setup();
        if (MODELS_TO_HIDE_ARCHIVE.includes(this.props.model)) {
            // Log all actions for debugging
            console.log("[ControlPanel] Original actions:", this.props.actions);
            // Filter out archive and unarchive actions
            this.props.actions = (this.props.actions || []).filter((action) => {
                const isArchiveAction = action.key?.includes("archive") || action.name?.toLowerCase().includes("archive");
                if (isArchiveAction) {
                    console.log(`[ControlPanel] Removing action:`, action);
                }
                return !isArchiveAction;
            });
            console.log("[ControlPanel] Filtered actions:", this.props.actions);
        }
    },
});*/