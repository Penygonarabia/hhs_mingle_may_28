/** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { DomGanttController } from "@dom_gantt_view/js/domgantt_controller.esm";
// // import { DomGanttController } from "@dom_gantt_view/js/domgantt_controller.esm";
// import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
// import { markup } from "@odoo/owl";
// import { _t } from "@web/core/l10n/translation";
// // import { escape } from "@web/core/utils/html_utils";
// import { escape } from "@web/core/utils/strings";


// patch(DomGanttController.prototype, {
//     async createRecord(record) {
//         await this.showConfirmation("Are you sure you want to create this record?", async () => {
//             // Proceed with the original createRecord logic
//             return super.createRecord(...arguments);
//         });
//     },

//     showConfirmation(warning, callback) {
//         const message = _t(warning);
//         this.env.services.dialog.add(ConfirmationDialog, {
//             body: markup(
//                 `<div class="text-danger">${escape(message)}</div>`
//             ),
//             confirm: async () => {
//                 if (callback) await callback();
//             },
//             cancel: () => {
//                 console.log("📌 Action canceled by user");
//             },
//         });
//     },
// });


// import { patch } from "@web/core/utils/patch";
// import { DomGanttController } from "@dom_gantt_view/js/domgantt_controller.esm";
// import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
// import { markup } from "@odoo/owl";
// import { _t } from "@web/core/l10n/translation";
// import { escape } from "@web/core/utils/strings";


// patch(DomGanttController.prototype, {
//     async createRecord(record) {
//         // Prepare props that were originally used in SelectCreateDialog
//         const props = {
//             resModel: this.model.meta.resModel,
//             context: this.env.searchModel._context,
//             domain: [["job_card_state_code", "in", ["101", "102", "107", "163"]]],
//             noCreate: !this.model.meta.canCreate,
//             onSelected: async (resIds) => {
//                 if (resIds.length) {
//                     await this.model.updateRawValueRecords(resIds, record);
//                 }
//             },
//         };

//         // Show confirmation dialog
//         await this.showConfirmation(
//             "Are you sure you want to plan this task?",
//             async () => {
//                 // Execute the onSelected logic after user confirms
//                 // Simulate selection of records here (you may integrate a UI to choose resIds if needed)
//                 const resIds = await this.env.services.orm.searchRead(
//                     props.resModel,
//                     props.domain,
//                     ["id"]
//                 ).then(records => records.map(r => r.id));

//                 await props.onSelected(resIds);
//             }
//         );
//     },

//     showConfirmation(warning, callback) {
//         const message = _t(warning);
//         this.env.services.dialog.add(ConfirmationDialog, {
//             body: markup(
//                 `<div class="text-danger">${escape(message)}</div>`
//             ),
//             confirm: async () => {
//                 if (callback) await callback();
//             },
//             cancel: () => {
//                 console.log("📌 Action canceled by user");
//             },
//         });
//     },
// });


import { patch } from "@web/core/utils/patch";
import { DomGanttController } from "@dom_gantt_view/js/domgantt_controller.esm";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { useService } from "@web/core/utils/hooks";


patch(DomGanttController.prototype, {
    createRecord(record) {
        if (record.selectTask && this.model.meta.canEdit) {
            return this.planTaskAssignment(record);
        }
        return super.createRecord(...arguments);
    },

    planTaskAssignment(record) {
        const dialogProps = this.getSelectCreateDialogProps({ record });

        // Auto-select records before showing the dialog
        // this.env.services.orm
        //     .searchRead(dialogProps.resModel, dialogProps.domain, ['id'])
        //     .then(async (data) => {
        //         const resIds = data.map(r => r.id);
        //         if (resIds.length) {
        //             await dialogProps.onSelected(resIds);
        //         }
        //     });

        // // Skip opening the dialog completely
        //  this.displayDialog(SelectCreateDialog, dialogProps);
    },

    getSelectCreateDialogProps({ record }) {
        const domain = [["job_card_state_code", "in", ["101", "102", "107", "163"]]];
        const rawRecord = this.model.buildRawRecord(record);
        const context = {
            ...this.env.searchModel._context,
            ...this.model.makeContextDefaults(rawRecord),
        };

        return {
            title: _t("Plan5"),
            resModel: this.model.meta.resModel,
            context,
            domain,
            noCreate: !this.model.meta.canCreate,
            onSelected: async (resIds) => {
                if (resIds.length) {
                    await this.model.updateRawValueRecords(resIds, record);
                }
            },
        };
    },
    getPlanDialogDomain() {
        const dateStartField = this.model.meta.fieldMapping.date_start;
        const dateStopField = this.model.meta.fieldMapping.date_stop;
        const newDomain = Domain.removeDomainLeaves(this.env.searchModel.globalDomain, [
            dateStartField,
            dateStopField,
        ]);
        return Domain.and([
            newDomain,
            ["|", [dateStartField, "=", false], [dateStopField, "=", false]],
        ]).toList({});
    },
});


// patch(DomGanttController.prototype, {
//     createRecord(record) {
//         if (record.selectTask && this.model.meta.canEdit) {
//             return this.planTaskAssignment(record);
//         }
//         return super.createRecord(...arguments);
//     },

//     planTaskAssignment(record) {
//         this.displayDialog(SelectCreateDialog, this.getSelectCreateDialogProps({ record }));
//     },

//     getSelectCreateDialogProps({ record }) {
//         const domain = [["job_card_state_code", "in", ["101", "102", "107", "163"]]];
//         const rawRecord = this.model.buildRawRecord(record);
//         const context = {
//             ...this.env.searchModel._context,
//             ...this.model.makeContextDefaults(rawRecord),
//         };
//           this.model.meta.viewId
	     
// // 	        this.env.services.orm.searchRead(this.model.meta.resModel, domain, ['name', 'customer_name']).then(data => {
// //     console.log("🔍 Records in dialog domain:", data.length, data.map(d => d.name));
// //     console.log("👥 Customer names:", data.map(d => d.customer_name));
// //     console.log("🔍 Records with name and customer_name:", data.map(d => `${d.name} ${d.customer_name}`));
// // });


//         return {
//             title: _t("Plan5"),
//             resModel: this.model.meta.resModel,
//             context,
//             domain,
//             noCreate: !this.model.meta.canCreate,
//             onSelected: async (resIds) => {
//                 if (resIds.length) {
//                     await this.model.updateRawValueRecords(resIds, record);
//                 }
//             },
//         };
//     },

//     getPlanDialogDomain() {
//         const dateStartField = this.model.meta.fieldMapping.date_start;
//         const dateStopField = this.model.meta.fieldMapping.date_stop;
//         const newDomain = Domain.removeDomainLeaves(this.env.searchModel.globalDomain, [
//             dateStartField,
//             dateStopField,
//         ]);
//         return Domain.and([
//             newDomain,
//             ["|", [dateStartField, "=", false], [dateStopField, "=", false]],
//         ]).toList({});
//     },
// });


// import { patch } from "@web/core/utils/patch";
// import { DomGanttController } from "@dom_gantt_view/js/domgantt_controller.esm";
// import {Domain} from "@web/core/domain";
// import {_t} from "@web/core/l10n/translation";
// import {SelectCreateDialog} from "@web/views/view_dialogs/select_create_dialog";
// import { useService } from "@web/core/utils/hooks";
// patch(DomGanttController.prototype, {
//     setup() {
//         super.setup(...arguments);
//           this.actionService = useService("action");
//         setTimeout(() => this.insertSideIframe(), 1000); // Ensure DOM is ready
//     },

//     insertSideIframe() {
//         const ganttRoot = document.querySelector(".o_gantt_view");

//         if (!ganttRoot || document.querySelector("#custom-gantt-iframe-wrapper")) {
//             return;
//         }

//         // Wrap gantt content and iframe into a flex container
//         const wrapper = document.createElement("div");
//         wrapper.id = "custom-gantt-iframe-wrapper";
//         wrapper.style.display = "flex";
//         wrapper.style.height = "calc(100vh - 150px)"; // Adjust height as needed

//         // Create iframe container
//         const iframeContainer = document.createElement("div");
//         iframeContainer.style.width = "10%";
//         iframeContainer.style.minWidth = "200px";
//         iframeContainer.style.marginRight = "10px";
//         iframeContainer.style.borderRight = "1px solid #ccc";
//         iframeContainer.style.paddingRight = "10px";

//         const iframe = document.createElement("iframe");
//         iframe.id = "custom-gantt-iframe";
//         // iframe.src ="http://localhost:8071/web#action=1304&model=machine.repair.support&view_type=list&menu_id=922";// Change model/view as needed
//         iframe.style.width = "100%";
//         iframe.style.height = "100%";
//         iframe.style.border = "none";
//         iframe.style.background = "#fff";

//         iframeContainer.appendChild(iframe);

//         // Move the current Gantt content into a new container
//         const ganttContent = document.createElement("div");
//         ganttContent.style.flexGrow = "1";

//         // Move all children of ganttRoot into ganttContent
//         while (ganttRoot.firstChild) {
//             ganttContent.appendChild(ganttRoot.firstChild);
//         }

//         // Append iframe and gantt into wrapper
//         wrapper.appendChild(iframeContainer);
//         wrapper.appendChild(ganttContent);
//         ganttRoot.appendChild(wrapper);
//     },
//         createRecord(record) {
//         if (record.selectTask && this.model.meta.canEdit) {
//             return this.planTaskAssignment(record);
//         }
//         return super.createRecord(...arguments);
//     },
//     planTaskAssignment(record) {
//         this.displayDialog(
//             SelectCreateDialog,
//             this.getSelectCreateDialogProps({record})
//         );
//     },
//     	getSelectCreateDialogProps({ record }) {
// 	        const domain = [["job_card_state_code", "in", ["101", "102",'107','163']]];
	        

// 	        const rawRecord = this.model.buildRawRecord(record);
// 	        const context = {
// 	            ...this.env.searchModel._context,
// 	            ...this.model.makeContextDefaults(rawRecord)
// 	        };

// 	        this.model.meta.viewId
// 	        console.log('his.model.meta.viewId', this.model.meta)
// 	        console.log('his.model.meta.viewId', this.model.meta.viewId)
// // 
//     //    DEBUG
// 	        this.env.services.orm.searchRead(this.model.meta.resModel, domain, ['name']).then(data => {
// 	            console.log("🔍 Records in dialog domain:", data.length, data.map(d => d.name));
// 	        });


// 	        // view_project_task_tree
// 	        return {
// 	            title: _t("Plan"),
// 	            resModel: this.model.meta.resModel,
// 	            context,
// 	            domain,
// 	            noCreate: !this.model.meta.canCreate,
// 	            onSelected: async (resIds) => {
// 	                if (resIds.length) {
// 	                    await this.model.updateRawValueRecords(resIds, record);
// 	                }
// 	            },
// 	        };
// 	    },

//     getPlanDialogDomain() {
//         const dateStartField = this.model.meta.fieldMapping.date_start;
//         const dateStopField = this.model.meta.fieldMapping.date_stop;
//         const newDomain = Domain.removeDomainLeaves(this.env.searchModel.globalDomain, [
//             dateStartField,
//             dateStopField,
//         ]);
//         return Domain.and([
//             newDomain,
//             ["|", [dateStartField, "=", false], [dateStopField, "=", false]],
//         ]).toList({});
//     },
// });




// import {DomGanttController} from "@dom_gantt_view/js/domgantt_controller.esm";
// import {Domain} from "@web/core/domain";
// import {SelectCreateDialog} from "@web/views/view_dialogs/select_create_dialog";
// import {_t} from "@web/core/l10n/translation";
// import {patch} from "@web/core/utils/patch";

// patch(DomGanttController.prototype, {
//     createRecord(record) {
//         if (record.selectTask && this.model.meta.canEdit) {
//             return this.planTaskAssignment(record);
//         }
//         return super.createRecord(...arguments);
//     },
//     planTaskAssignment(record) {
//         this.displayDialog(
//             SelectCreateDialog,
//             this.getSelectCreateDialogProps({record})
//         );
//     },

//    /* getSelectCreateDialogProps(params) {
//         const {record} = params;
//         const domain = this.getPlanDialogDomain();
//         let context = this.env.searchModel._context;
//         const rawRecord = this.model.buildRawRecord(record);
//         context = Object.assign(context, this.model.makeContextDefaults(rawRecord));
//         return {
//             title: _t("Plan"),
//             resModel: this.model.meta.resModel,
//             context: context,
//             domain,
//             noCreate: !this.model.meta.canCreate,
//             onSelected: async (resIds) => {
//                 if (resIds.length) {
//                     await this.model.updateRawValueRecords(resIds, record);
//                 }
//             },
//         };
//     },*/
	
// 	getSelectCreateDialogProps({ record }) {
// 	        const domain = [["job_card_state_code", "in", ["101", "102",'107','163']]];
	        

// 	        const rawRecord = this.model.buildRawRecord(record);
// 	        const context = {
// 	            ...this.env.searchModel._context,
// 	            ...this.model.makeContextDefaults(rawRecord)
// 	        };

// 	        this.model.meta.viewId
// 	        console.log('his.model.meta.viewId', this.model.meta)
// 	        console.log('his.model.meta.viewId', this.model.meta.viewId)

// 	        // DEBUG
// 	        this.env.services.orm.searchRead(this.model.meta.resModel, domain, ['name']).then(data => {
// 	            console.log("🔍 Records in dialog domain:", data.length, data.map(d => d.name));
// 	        });


// 	        // view_project_task_tree
// 	        return {
// 	            title: _t("Plan"),
// 	            resModel: this.model.meta.resModel,
// 	            context,
// 	            domain,
// 	            noCreate: !this.model.meta.canCreate,
// 	            onSelected: async (resIds) => {
// 	                if (resIds.length) {
// 	                    await this.model.updateRawValueRecords(resIds, record);
// 	                }
// 	            },
// 	        };
// 	    },

//     getPlanDialogDomain() {
//         const dateStartField = this.model.meta.fieldMapping.date_start;
//         const dateStopField = this.model.meta.fieldMapping.date_stop;
//         const newDomain = Domain.removeDomainLeaves(this.env.searchModel.globalDomain, [
//             dateStartField,
//             dateStopField,
//         ]);
//         return Domain.and([
//             newDomain,
//             ["|", [dateStartField, "=", false], [dateStopField, "=", false]],
//         ]).toList({});
//     },
// });
