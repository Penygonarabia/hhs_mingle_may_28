/** @odoo-module **/

/** @odoo-module **/
import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { patch } from "@web/core/utils/patch";

 

patch(StatusBarField.prototype, {
    async selectItem(item) {
        // 1. Check if we are already saving
        if (this._isStatusSaving) {
            console.log("Status update already in progress, ignoring click.");
            return;
        }

        // 2. Apply the lock
        this._isStatusSaving = true;

        try {
            // 3. Process the actual click event
            await super.selectItem(...arguments);
        } finally {
            // 4. Release the lock when finished
            this._isStatusSaving = false;
        }
    }
});

/*import { patch } from "@web/core/utils/patch";
import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { useService } from "@web/core/utils/hooks";

patch(StatusBarField.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this._isProcessing = false;
    },

    async selectItem(item) {
        if (this._isProcessing) return;

        const record = this.props.record;
        const recordId = record.resId;
        const fieldName = this.props.name;

        // Only apply logic to job_state field
        if (fieldName !== 'job_state') {
            return super.selectItem(item);
        }

        // ✅ Server-side role-aware check
        if (recordId) {
            try {
                const statusCheck = await this.orm.call(
                    'project.task',
                    'check_job_state_change_allowed',
                    [recordId]
                );

                if (!statusCheck.can_proceed) {
                    this.notification.add(statusCheck.message, {
                        type: "danger",
                        title: "Status Change Not Allowed",
                    });
                    return;
                }

            } catch (error) {
                console.error("State check failed:", error);
                return;
            }
        }

        // ✅ Disable statusbar during processing
        this._isProcessing = true;
        this._disableStatusBar();

        try {
            await super.selectItem(item);

            // ✅ After save — check if further changes allowed
            if (recordId) {
                const newStatusCheck = await this.orm.call(
                    'project.task',
                    'check_job_state_change_allowed',
                    [recordId]
                );

                if (newStatusCheck.can_proceed) {
                    // Re-enable — more changes allowed
                    this._enableStatusBar();
                }
                // Keep disabled if blocked (Closed, or role restriction)

            }

        } catch (error) {
            this._enableStatusBar();
            console.error("Status change failed:", error);
        } finally {
            this._isProcessing = false;
        }
    },

    _disableStatusBar() {
        const el = this.__owl__.bdom?.el;
        if (el) {
            el.style.pointerEvents = "none";
            el.style.opacity = "0.5";
            el.style.cursor = "not-allowed";
        }
    },

    _enableStatusBar() {
        const el = this.__owl__.bdom?.el;
        if (el) {
            el.style.pointerEvents = "";
            el.style.opacity = "";
            el.style.cursor = "";
        }
    },
});*/

/*import { patch } from "@web/core/utils/patch";
import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";

patch(StatusBarField.prototype, {
    setup() {
        super.setup();
        this._statusClicked = false;

        // Reset after record save
        this.props.record.model.bus.addEventListener("NEED_LOCAL_CHANGES", () => {
            this._statusClicked = false;
        });
    },

    async selectItem(item) {
        if (this._statusClicked) {
            return;
        }

        this._statusClicked = true;

        return super.selectItem(item);
    },
});*/