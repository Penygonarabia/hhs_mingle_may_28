/** @odoo-module **/
 
/*import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { Dialog } from "@web/core/dialog/dialog";

patch(FormController.prototype, "machine_repair_job_stock_warning", {
    async saveButtonClicked(...args) {
        const result = await super.saveButtonClicked(...args);
 
        if (this.model.root.context.show_stock_warning) {
            this.displayStockWarning();
        }
        return result;
    },
 
    displayStockWarning() {
        Dialog.alert(this, {
            title: "Warning",
            body: "Stock is not available for this product!",
        });
    },
});
 */


 

// /** @odoo-module **/
 
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { Dialog } from "@web/core/dialog/dialog";
// /*import { busService } from "@web/core/bus/bus_service";
// */ 
// console.log('llllllllllllllllllllllllllllllllllllllllllllll')
// patch(FormController.prototype, {
//     setup() {
//         super.setup();
// // /*        this.busService = this.env.services.bus_service;
// // */		this.busService = services["bus_service"];
// //         this.busService.addChannel("stock_warning");
// //         this.busService.addEventListener("notification", this.onBusNotification.bind(this));
//     },
 
//     onBusNotification(ev) {
//         for (const { type, payload } of ev.detail) {
//             if (type === "stock_warning") {
//                 Dialog.alert(this, {
//                     title: "Warning",
//                     body: payload.message || "⚠️ Stock not available!",
//                 });
//             }
//         }
//     },
// });


// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";
// import { Dialog } from "@web/core/dialog/dialog";
// patch(FormController.prototype, {
//     setup() {
//      super.setup();

//         this.actionService = useService("action");
//          this.dialogService = useService("dialog");

//         // Current action context
//         const context = this.actionService.currentAction?.context || {};
//         console.log("Full context:", context);

//         // Access specific values:
//         const showStockWarning = context.show_stock_warning;
//         const projectTaskId = context.params?.id;

//         console.log("Show stock warning:", showStockWarning);
//         console.log("Project Task ID:", projectTaskId);
//     },
//     this.dialogService.add(WarningDialog, {
// title: _t("Connection to device failed"),
// message: _t("Check if the device is still connected"),
// })

// });


/** @odoo-module **/
/*import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
// import { _t } from "@web/core/l10n/translations";
// import { _t } from "@web/core/l10n/translation";
console.log('llllllllllllllllllllllllllllllllllllllllllllll')
patch(FormController.prototype, {
    setup() {
   super.setup();

        this.actionService = useService("action");
        this.dialogService = useService("dialog");

        // Current action context
        const context = this.actionService.currentAction?.context || {};
        console.log("Full context:", context);

        const showStockWarning = context.show_stock_warning;
        const projectTaskId = context.params?.id;

        console.log("Show stock warning:", showStockWarning);
        console.log("Project Task ID:", projectTaskId);

        // Show dialog if stock warning is enabled
        if (showStockWarning) {
            this.dialogService.add(Dialog, {
                title: ("Warning"),
                body: ("⚠️ Stock is not available for this product!"),
            });
        }
    },
});*/


import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
 
console.log("✅ stock_warning_patch.js loaded");
 
patch(FormController.prototype, {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        console.log("⚙️ FormController patch setup done");
    },
 
    async saveRecord(...args) {
        // Call the original save
        const result = await super.saveRecord(...args);
 
        try {
            // Get the current action context
            const context = this.actionService?.currentAction?.context || {};
            console.log("🟢 Context after save:", context);
 
            // If Python set show_stock_warning, show popup
            if (context.show_stock_warning) {
                const msg = context.warning_products
                    ? `⚠️ Stock not available for: ${context.warning_products}`
                    : "⚠️ Stock is not available for this product!";
                console.log("⚠️ Triggering stock warning popup:", msg);
                this.dialogService.add(Dialog, {
                    title: "Warning",
                    body: msg,
                });
            } else {
                console.log("ℹ️ No stock warning context found.");
            }
        } catch (err) {
            console.error("❌ Error in stock warning patch:", err);
        }
 
        return result;
    },
}, "machine_repair_job_stock_warning_patch");
 

/*import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
 
console.log("🧩 stock_warning.js loaded");
 
patch(FormController.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
    },
 
    async saveButtonClicked(...args) {
        const result = await super.saveButtonClicked(...args);
 
        // Step: Access current context
        const context = this.model.root?.context || {};
        console.log("📦 Form context:", context);
 
        if (context.show_stock_warning) {
            console.log("⚠️ Stock warning detected — showing popup");
            this.dialogService.add(Dialog, {
                title: "Warning",
                body: "⚠️ Stock is not available for this product!",
            });
        }
 
        return result;
    },
});*/

/** @odoo-module **/
 
/** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { Dialog } from "@web/core/dialog/dialog";

// console.log('Module loaded');
// const originalSaveButtonClicked = FormController.prototype.saveButtonClicked;
// patch(FormController.prototype,{
//     async saveButtonClicked(...args) {
//         // const result = await this._super(...args); // Call original save

//         const showStockWarning = this.model.root?.context?.show_stock_warning;
//         console.log("Show stock warning after save:", showStockWarning);

//         if (showStockWarning) {
//             Dialog.alert(this, {
//                 title: "Warning",
//                 body: "⚠️ Stock is not available for this product!",
//             });
//         }

//         return result;
//     },
// // });
// /** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";
// import { Dialog } from "@web/core/dialog/dialog";

// console.log("Module loaded");

// // Save original method reference
// const originalSaveButtonClicked = FormController.prototype.saveButtonClicked;

// patch(FormController.prototype,{
//     async saveButtonClicked(...args) {
//         // Call original saveButtonClicked
//         const result = await originalSaveButtonClicked.apply(this, args);

//         // Use services
//         // this.actionService = useService("action");
//         this.dialogService = useService("dialog");

//         // Get current action context
//         const context = this.model.root?.context?.show_stock_warning|| {};
//         const showStockWarning = context.show_stock_warning;
//         const projectTaskId = context.params?.id;

//         console.log("Show stock warning after save:", showStockWarning);
//         console.log("Project Task ID:", projectTaskId);

//         // Show dialog only if flag is true
//         if (showStockWarning) {
//             this.dialogService.add(Dialog, {
//                 title: "Warning",
//                 body: `⚠️ Stock is not available for task ID ${projectTaskId}!`,
//             });
//         }

//         return result;
//     },
// });



