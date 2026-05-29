/** @odoo-module **/


// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";


// import { useService } from "@web/core/utils/hooks";

// patch(StatusBarField.prototype, {
//     setup() {
//         this._super?.();
//         this.action = useService("action");
//     },

//     // async onClick(stageId) {
//     //     const record = this.props.record;
//     //     const fieldName = this.props.name;           // field name (job_state)
//     //     const stage = this.props.selection.find(s => s[0] === stageId)?.[1]; // stage name

//     //     console.log("Clicked stageId:", stageId);
//     //     console.log("Stage name:", stage);
//     //     console.log("Field name:", fieldName);
//     //     console.log("Task model:", record.resModel);
//     //     console.log("Task ID:", record.resId);

//     //     // Only trigger for job_state field in project.task
//     //     if (record.resModel === "project.task" && fieldName === "job_state") {
//     //         // Example: open popup on "Cancelled" stage
//     //         if (stage === "Cancelled") {
//     //             console.log("Cancelled selected — opening popup...");

//     //             await this.action.doAction({
//     //                 type: "ir.actions.act_window",
//     //                 name: "Cancel Reason Wizard",
//     //                 res_model: "cancelled.reason.wizard",
//     //                 view_mode: "form",
//     //                 target: "new",
//     //                 views: [[false, "form"]],
//     //                 context: { default_task_id: record.resId },
//     //             });

//     //             return; // stop default status change
//     //         }
//     //     }

//     //     // Default behavior for other stages
//     //     if (this._super) {
//     //         await this._super(stageId);
//     //     }
//     // },
//     async onClick(stageId) {
//     const record = this.props.record;
//     const fieldName = this.props.name;

//     if (!record || !this.props.selection) {
//         console.warn("No record or selection available for StatusBarField");
//         return;
//     }

//     const stage = this.props.selection.find(s => s[0] === stageId)?.[1]; 

//     console.log("Clicked stageId:", stageId);
//     console.log("Stage name:", stage);
//     console.log("Field name:", fieldName);
//     console.log("Task model:", record.resModel);
//     console.log("Task ID:", record.resId);

//     if (record.resModel === "project.task" && fieldName === "job_state") {
//         if (stage === "Cancelled") {
//             console.log("Cancelled selected — opening popup...");
//             await this.action.doAction({
//                 type: "ir.actions.act_window",
//                 name: "Cancel Reason Wizard",
//                 res_model: "cancelled.reason.wizard",
//                 view_mode: "form",
//                 target: "new",
//                 views: [[false, "form"]],
//                 context: { default_task_id: record.resId },
//             });
//             return;
//         }
//     }

//     if (this._super) {
//         await this._super(stageId);
//     }
// }

// });



// import { registry } from "@web/core/registry";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { patch } from "@web/core/utils/patch";
// import { useService } from "@web/core/utils/hooks";
// console.log("Closed status selected, opening popup...");

// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup(...arguments)
//         this.action = useService("action");
//         this.orm = useService("orm");

//         console.log('0000000000000000000000000000000000000000', this.action);
//     },


//     async onClick(statusValue) {
//         const tasks = await orm.searchRead(
//             "project.task",
//             [["job_card_state", "=", "Cancelled"]],
//             ["id", "name", "job_card_state"]  // fields to read
//         );

//         console.log(tasks);

//         console.log("Status clicked:", statusValue);
//         console.log("Status clicked:", statusValue);
//         console.log("Task model:", this.props.record.resModel);
//         console.log("Task ID:", this.props.record.resId);
//         await this._super(statusValue);


//         // Only trigger the popup when status = "closed"
//         if (statusValue === "Cancelled") {
//             console.log("Closed status selected, opening popup...");

//             // Open wizard action
//             this.action.doAction({
//                 name: "Task Close Wizard",
//                 type: "ir.actions.act_window",
//                 res_model: "cancelled.reason.wizard",
//                 view_mode: "form",
//                 target: "new",
//                 views: [[false, "form"]],
//                 context: {
//                     default_task_id: this.props.record.data.id,
//                 },
//             });
//         }
//     },
// });
// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { useService } from "@web/core/utils/hooks";

// import { onMounted } from "@odoo/owl";

// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup(...arguments);
//         this.action = useService("action");
//         onMounted(() => {

//             const Value = this.props;
//             console.log("StatusBarField mounted for field:", Value);
//             console.log("StatusBarField mounted for field:", this.props.name);
//             console.log("Current record ID:", this.props.record.resId);
//             console.log("Current value:", this.props.record.job_state);
//         });
//     },


//     async onClick(stageId) {
//         const record = this.props.record;
//         const stageName = this.props.selection.find(s => s[0] === stageId)?.[1];

//         console.log("Clicked stage ID:", stageId);
//         console.log("Stage name:", stageName);

//         // Example: open wizard on "Cancelled"
//         if (record.resModel === "project.task" && this.props.name === "job_state") {
//             if (stageName === "Cancelled") {
//                 await this.action.doAction({
//                     type: "ir.actions.act_window",
//                     name: "Cancel Wizard",
//                     res_model: "cancelled.reason.wizard",
//                     view_mode: "form",
//                     target: "new",
//                     views: [[false, "form"]],
//                     context: { default_task_id: record.resId },
//                 });
//                 return;
//             }
//         }

//         if (this._super) {
//             await this._super(stageId);
//         }
//     },


// });



/** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { useService } from "@web/core/utils/hooks";
// import { onMounted } from "@odoo/owl"; // OWL hook

// patch(StatusBarField.prototype,  {
//     setup() {
//         super.setup(...arguments);
//         this.action = useService("action");

//         // onMounted hook
//         onMounted(() => {
//             console.log("StatusBarField mounted for field:", this.props.name);
//             console.log("Current record ID:", this.props.record.resId);
//             console.log("Current value:", this.props.value);

//             // Example: do something on mount
//             if (this.props.name === "job_state") {
//                 const stageId = this.props.value;
//                 const stageName = this.props.job_state.find(s => s[0] === stageId)?.[1];
//                 console.log("Current job_state on mount:", stageName);
//             }
//         });
//     },

//     async onClick(stageId) {
//         const record = this.props.record;
//         const fieldName = this.props.name;
//         const stageName = this.props.job_state.find(s => s[0] === stageId)?.[1];

//         console.log("Clicked stageId:", stageId);
//         console.log("Clicked stageName:", stageName);
//         console.log("Field name:", fieldName);
//         console.log("Task model:", record.resModel);
//         console.log("Task ID:", record.resId);

//         // Only trigger for job_state field
//         if (record.resModel === "project.task" && fieldName === "job_state") {
//             // Example: open popup on "Cancelled"
//             if (stageName === "Cancelled") {
//                 console.log("Cancelled selected — opening popup...");

//                 await this.action.doAction({
//                     type: "ir.actions.act_window",
//                     name: "Cancel Reason Wizard",
//                     res_model: "cancelled.reason.wizard",
//                     view_mode: "form",
//                     target: "new",
//                     views: [[false, "form"]],
//                     context: { default_task_id: record.resId },
//                 });

//                 return; // stop default status change
//             }
//         }

//         // Default behavior for other stages
//         // if (this._super) {
//         //     await this._super(stageId);
//         // }
//     },
// });

// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");
//         // onMounted hook
//         onMounted(async () => {
//             console.log("StatusBarField mounted for field:", this.props.name);
//             console.log("Current record ID:", this.props.record.resId);

//             // Only for job_state field

//             // const stageRecord = this.props.value; // Many2one: [id, name]
//             // const stageId = stageRecord?.[0];
//             // const stageName = stageRecord?.[1];

//             // console.log("Current job_state on mount - ID:", stageId);
//             // console.log("Current job_state on mount - Name:", stageName);


//             // const tasks = await orm.searchRead(
//             //     "project.task",
//             //     [["id", "=", "stageName"]],
//             //     ["id", "name", "job_card_state"]  // fields to read
//             // );
//             // console.log('tasks', tasks);
//             // const stageId = this.props.value; // Many2one ID
//             // const stageName = this.props.selection?.find(s => s[0] === stageId)?.[1] || "";

//             // console.log("Current job_state on mount - ID:", stageId);
//             // console.log("Current job_state on mount - Name:", stageName);

//             // const tasks = await this.orm.searchRead(
//             //     "project.task",
//             //     [["job_state", "=", stageId]], // correct domain for Many2one
//             //     ["id", "name", "job_state"]
//             // );

//             // console.log("Tasks with this job_state:", tasks);
//             const recordId = this.props.record.resId;
//             const model = this.props.record.resModel;
//             console.log('model---------------',model);


//             const data = await this.env.services.orm.read(model, [recordId], [
//                 "name",
//                 "job_state",
//                 "job_card_state_code"
//             ]);
//             console.log('data-----------------------------',data)




//         });
//     }
//     /**
//      * Triggered when a status in the statusbar is clicked
//      * For Many2one, the parameter is [id, name]
//      */
//     // async onClick(stageRecord) {
//     //     const record = this.props.record;
//     //     const fieldName = this.props.name;

//     //     const stageId = stageRecord?.[0];
//     //     const stageName = stageRecord?.[1];

//     //     console.log("Clicked stageId:", stageId);
//     //     console.log("Clicked stageName:", stageName);
//     //     console.log("Field name:", fieldName);
//     //     console.log("Task model:", record.resModel);
//     //     console.log("Task ID:", record.resId);

//     //     // Only trigger for job_state field in project.task
//     //     if (record.resModel === "project.task" && fieldName === "job_state") {
//     //         if (stageName === "Cancelled") {
//     //             console.log("Cancelled selected — opening wizard...");

//     //             await this.action.doAction({
//     //                 type: "ir.actions.act_window",
//     //                 name: "Cancel Reason Wizard",
//     //                 res_model: "cancelled.reason.wizard", // your wizard model
//     //                 view_mode: "form",
//     //                 target: "new",
//     //                 views: [[false, "form"]],
//     //                 context: { default_task_id: record.resId },
//     //             });

//     //             return; // stop default behavior
//     //         }
//     //     }

//     //     // Default behavior for other stages
//     //     if (this._super) {
//     //         await this._super(stageRecord);
//     //     }
//     // },
// });







/** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { useService } from "@web/core/utils/hooks";
// import { onMounted } from "@odoo/owl";

// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");

//         // Run when component mounts
//         onMounted(async () => {
//             const recordId = this.props.record?.resId;
//             const model = this.props.record?.resModel;
//             const fieldName = this.props.name;

//             console.log("🟢 StatusBarField mounted");
//             console.log("Field:", fieldName);
//             console.log("Model:", model);
//             console.log("Record ID:", recordId);

//             if (model === "project.task" && fieldName === "job_state" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);
//                     console.log("📦 Job Card Data:", data);
//                 } catch (err) {
//                     console.error("❌ Error reading record:", err);
//                 }
//             }
//         });
//     },

//     /**
//      * Triggered when a stage in the status bar is clicked
//      * @param {Array} stageRecord - [id, name] of the clicked stage
//      */
//     async onClick(stageRecord) {
//         const record = this.props.record;
//         const fieldName = this.props.name;

//         const stageId = stageRecord?.[0];
//         const stageName = stageRecord?.[1];

//         console.log("🟨 Clicked stage:", { stageId, stageName, fieldName });

//         // Only for project.task.job_state
//         if (record.resModel === "project.task" && fieldName === "job_state") {
//             if (stageName === "Cancelled") {
//                 console.log("🛑 Cancelled selected — opening wizard...");

//                 await this.action.doAction({
//                     type: "ir.actions.act_window",
//                     name: "Cancel Reason Wizard",
//                     res_model: "cancelled.reason.wizard",
//                     view_mode: "form",
//                     target: "new",
//                     views: [[false, "form"]],
//                     context: { default_task_id: record.resId },
//                 });

//                 return; // prevent default Odoo behavior
//             }
//         }

//         // Default Odoo click behavior
//         if (this._super) {
//             await this._super(stageRecord);
//         }
//     },
// });

/** @odoo-module **/



// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");

//         onMounted(async () => {
//             const recordId = this.props.record?.resId;
//             const model = this.props.record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);

//             if (model === "project.task" && recordId) {
//                 const data = await this.orm.read(model, [recordId], [
//                     "name",
//                     "job_state",
//                     "job_card_state_code",
//                 ]);
//                 console.log("📦 Job Card Data:", data);
//             }
//         });
//     },
// });

/** Patch StatusBarField to log task data and buttons */
// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");

//         // Reactive state to store job card data if needed
//         this.state = useState({
//             jobCardData: null,
//         });

//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);

//             // Expose the record globally for console debugging
//             window.lastStatusRecord = record;

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);

//                     // Save in reactive state
//                     this.state.jobCardData = data[0];

//                     console.log("📦 Job Card Data:", this.state.jobCardData);
//                     let allButtons = Array.from(document.querySelectorAll("button"));
//                     console.log(allButtons);

//                     let buttons = document.querySelectorAll("button.btn.btn-secondary.dropdown-toggle");
//                     buttons.forEach((b, i) => console.log(i, b.textContent));
//                     let moreBtn = document.querySelector("button.btn.btn-secondary.dropdown-toggle");

//                     moreBtn.addEventListener("click", () => {
//                         const observer = new MutationObserver(() => {
//                             let dropdown = document.querySelector(".o-dropdown--menu.dropdown-menu.d-block");
//                             if (dropdown) {
//                                 let items = dropdown.querySelectorAll(".dropdown-item span");
//                                 items.forEach((item, index) => console.log(index, item.textContent));
//                                 observer.disconnect(); // stop observing
//                             }
//                         });
//                         observer.observe(document.body, { childList: true, subtree: true });
//                     });




//                     const dropdown = document.querySelector(".o-dropdown--menu.dropdown-menu.d-block");
//                     if (dropdown) {
//                         const items = dropdown.querySelectorAll(".dropdown-item span");
//                         console.log(items);
//                     }



//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });

// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");

//         this.state = useState({
//             jobCardData: null,
//         });

//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);

//             window.lastStatusRecord = record;

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);

//                     this.state.jobCardData = data[0];
//                     console.log("📦 Job Card Data:", this.state.jobCardData);

//                     // 1️⃣ Log all buttons in the status bar
//                     const allButtons = Array.from(document.querySelectorAll("button"));
//                     console.log("All buttons:", allButtons.map(b => b.textContent.trim()));

//                     // 2️⃣ Handle "More" button dropdown items
//                     const moreBtn = document.querySelector("button.btn.btn-secondary.dropdown-toggle");
//                     if (moreBtn) {
//                         moreBtn.addEventListener("click", () => {
//                             // Use MutationObserver to wait until dropdown renders
//                             const observer = new MutationObserver(() => {
//                                 const dropdown = document.querySelector(".o-dropdown--menu.dropdown-menu.d-block");
//                                 if (dropdown) {
//                                     const items = dropdown.querySelectorAll(".dropdown-item span");
//                                     console.log("Dropdown items:");
//                                     items.forEach((item, index) => console.log(index, item.textContent));
//                                     observer.disconnect(); // stop observing after dropdown is found
//                                 }
//                             });
//                             observer.observe(document.body, { childList: true, subtree: true });
//                         });
//                     }

//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });



// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");

//         this.state = useState({
//             jobCardData: null,
//         });



//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);
//             window.lastStatusRecord = record;

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);
//                     this.state.jobCardData = data[0];
//                     console.log("📦 Job Card Data:", this.state.jobCardData);


//                     // const moreBtn = document.querySelector("button.btn.btn-secondary.dropdown-toggle");
//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });

//         this.clickfunction();

//     },


//    clickfunction(){
//      const moreBtn = document.querySelector("button.btn.btn-secondary.dropdown-toggle");
//     //  const moreBtn = document.querySelectorAll("button.btn.btn-secondary.dropdown-toggle");
//         console.log('more button is visible',moreBtn)
//     }
// });


// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");

//         this.state = useState({
//             jobCardData: null,
//         });

//         const clickfunction = () => {
//             const moreBtn = document.querySelector("button.btn.btn-secondary.dropdown-toggle");
//             console.log('More button is visible:', moreBtn);

//             if (moreBtn) {
//                 // Add click listener
//                 moreBtn.addEventListener("click", () => {
//                     console.log("More button clicked");
//                 });
//             } else {
//                 console.log("More button not yet rendered. Waiting for it...");
//                 // Optional: use MutationObserver to wait
//                 const observer = new MutationObserver(() => {
//                     const btn = document.querySelector("button.btn.btn-secondary.dropdown-toggle");
//                     if (btn) {
//                         console.log("✅ More button appeared:", btn);
//                         btn.addEventListener("click", () => console.log("More button clicked"));
//                         observer.disconnect();
//                     }
//                 });
//                 observer.observe(document.body, { childList: true, subtree: true });
//             }
//         };

//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);
//             window.lastStatusRecord = record;

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);
//                     this.state.jobCardData = data[0];
//                     console.log("📦 Job Card Data:", this.state.jobCardData);

//                     // Call click function here after DOM is ready
//                     clickfunction();

//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });


// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { useService } from "@web/core/utils/hooks";
// import { onMounted, useState } from "@odoo/owl";
// import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");
//         this.dialog = useService("dialog"); // To show popup

//         this.state = useState({
//             jobCardData: null,
//         });

//         // --- Function: handle dropdown item click ---
//         const handleDropdownClick = (itemText) => {
//             if (itemText.trim() === "Cancelled") {
//                 console.log("✅ Cancelled clicked, showing popup");
//                 // this.dialog.alert(
//                 //     "Job Card Cancelled",
//                 //     "You have selected Cancelled for this Job Card."
//                 // );
//                 this.dialog.add(ConfirmationDialog, {
//                     title: "Job Card Cancelled",
//                     body: "You have selected Cancelled for this Job Card.",
//                     confirmText: "OK",      // optional
//                     cancelText: "Cancel",   // optional
//                 }).then(() => {
//                     console.log("User confirmed Cancelled");
//                 }).catch(() => {
//                     console.log("User cancelled the dialog");
//                 });

//             }
//         };

//         // // --- Event delegation: listen for More button and dropdown clicks ---
//         // const attachListeners = () => {
//         //     document.body.addEventListener("click", (ev) => {
//         //         // Detect More button click
//         //         const moreBtn = ev.target.closest("button.btn.btn-secondary.dropdown-toggle");
//         //         if (moreBtn) {
//         //             console.log("ℹ️ More button clicked");
//         //             // Dropdown will appear after this click
//         //         }

//         //         // Detect dropdown item click
//         //         const dropdownItem = ev.target.closest(".dropdown-item span");
//         //         if (dropdownItem) {
//         //             console.log("ℹ️ Dropdown item clicked:", dropdownItem.textContent.trim());
//         //             handleDropdownClick(dropdownItem.textContent);
//         //         }
//         //     });
//         // };

//         const attachListeners = () => {
//             document.body.addEventListener("click", (ev) => {
//                 // Detect More button click
//                 const moreBtn = ev.target.closest("button.btn.btn-secondary.dropdown-toggle");
//                 if (moreBtn) {
//                     console.log("ℹ️ More button clicked");
//                 }

//                 // Detect dropdown item click
//                 const dropdownItem = ev.target.closest(".dropdown-item");
//                 if (dropdownItem) {
//                     const text = dropdownItem.querySelector("span")?.textContent.trim() || "";
//                     console.log("ℹ️ Dropdown item clicked:", text);
//                     handleDropdownClick(text);
//                 }
//             });
//         };


//         // --- onMounted logic ---
//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);
//             window.lastStatusRecord = record;

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);
//                     this.state.jobCardData = data[0];
//                     console.log("📦 Job Card Data:", this.state.jobCardData);

//                     // Attach global click listeners
//                     attachListeners();

//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });
// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { useService } from "@web/core/utils/hooks";
// import { onMounted, useState } from "@odoo/owl";

// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");
//         this.dialog = useService("dialog"); // To show popup

//         this.state = useState({
//             jobCardData: null,
//         });

//         // --- Function: handle dropdown item click ---
//         const handleDropdownClick = (itemText) => {
//             if (itemText.trim() === "Cancelled") {
//                 console.log("✅ Cancelled clicked, showing popup");

//                 // Use the built-in confirm dialog
//                 this.dialog.confirm({
//                     title: "Job Card Cancelled",
//                     body: "You have selected Cancelled for this Job Card.",
//                     confirmText: "OK",
//                     cancelText: "Cancel",
//                 }).then(() => {
//                     console.log("User confirmed Cancelled");
//                     // TODO: Update job card state if needed
//                 }).catch(() => {
//                     console.log("User cancelled the dialog");
//                 });
//             }
//         };

//         // --- Event delegation: listen for More button and dropdown clicks ---
//         const attachListeners = () => {
//             document.body.addEventListener("click", (ev) => {
//                 // Detect More button click
//                 const moreBtn = ev.target.closest("button.btn.btn-secondary.dropdown-toggle");
//                 if (moreBtn) {
//                     console.log("ℹ️ More button clicked");
//                 }

//                 // Detect dropdown item click
//                 const dropdownItem = ev.target.closest(".dropdown-item");
//                 if (dropdownItem) {
//                     const text = dropdownItem.querySelector("span")?.textContent.trim() || "";
//                     console.log("ℹ️ Dropdown item clicked:", text);
//                     handleDropdownClick(text);
//                 }
//             });
//         };

//         // --- onMounted logic ---
//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);
//             window.lastStatusRecord = record;

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);
//                     this.state.jobCardData = data[0];
//                     console.log("📦 Job Card Data:", this.state.jobCardData);

//                     // Attach global click listeners
//                     attachListeners();

//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });
// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { useService } from "@web/core/utils/hooks";
// import { onMounted, useState } from "@odoo/owl";

// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");
//         this.dialog = useService("dialog"); // To show popup

//         this.state = useState({
//             jobCardData: null,
//         });

//         // --- Function: handle dropdown item click ---
//         const handleDropdownClick = (itemText) => {
//             if (itemText.trim() === "Cancelled") {
//                 console.log("✅ Cancelled clicked, showing popup");
//                 this.dialog.confirm({
//                     title: "Job Card Cancelled",
//                     body: "You have selected Cancelled for this Job Card.",
//                     confirmText: "OK",
//                     cancelText: "Cancel",
//                 }).then(() => {
//                     console.log("User confirmed Cancelled");
//                     // TODO: Update job card state if needed
//                 }).catch(() => {
//                     console.log("User cancelled the dialog");
//                 });
//             }
//         };

//         // --- Event delegation: listen for More button and dropdown clicks ---
//         const attachListeners = () => {
//             document.body.addEventListener("click", (ev) => {
//                 // Detect More button click
//                 const moreBtn = ev.target.closest("button.btn.btn-secondary.dropdown-toggle");
//                 if (moreBtn) {
//                     console.log("ℹ️ More button clicked");
//                 }
//                 const dropdownItem = ev.target.closest(".o-dropdown--menu dropdown-menu d-block");
//                 console.log('dropdownItem',dropdownItem)

//                 if (
//                     dropdownItem &&
//                     !dropdownItem.classList.contains("disabled") &&
//                     dropdownItem.closest(".o-dropdown--menu")
//                 ) {
//                     console.log("ℹ️ Dropdown item clicked:", dropdownItem.textContent.trim());
//                     handleDropdownClick(dropdownItem.textContent);
//                 }


//                 // Detect dropdown item click using full selector
//                 // const dropdownItem = ev.target.closest(
//                 //     ".o-dropdown--menu .dropdown-item:not(.disabled):not(:disabled), " +
//                 //     ".o-dropdown--menu .dropdown-item:not(.disabled):not(:disabled) label"
//                 // );
//                 // console.log('dropdownItem',dropdownItem)

//                 // if (dropdownItem) {
//                 //     const text = dropdownItem.textContent.trim();
//                 //     console.log("ℹ️ Dropdown item clicked:", text);
//                 //     handleDropdownClick(text);
//                 // }
//             });
//         };

//         // --- onMounted logic ---
//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);
//             window.lastStatusRecord = record;

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);
//                     this.state.jobCardData = data[0];
//                     console.log("📦 Job Card Data:", this.state.jobCardData);

//                     // Attach global click listeners
//                     attachListeners();

//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });





// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");
//         this.dialog = useService("dialog"); // To show popup

//         this.state = useState({
//             jobCardData: null,
//         });

//         // Handle dropdown item click
//         const handleDropdownClick = (itemText) => {
//             if (itemText.trim() === "Cancelled") {
//                 console.log("✅ Cancelled clicked, showing popup");
//                 this.dialog.confirm({
//                     title: "Job Card Cancelled",
//                     body: "You have selected Cancelled for this Job Card.",
//                     confirmText: "OK",
//                     cancelText: "Cancel",
//                 }).then(() => {
//                     console.log("User confirmed Cancelled");
//                     // TODO: Update job card state if needed
//                 }).catch(() => {
//                     console.log("User cancelled the dialog");
//                 });
//             }
//         };


//         const attachClickListeners = () => {
//             // document.body.addEventListener("click", (ev) => {
//             //     // Detect More button click
//             //     const moreBtn = ev.target.closest("button.btn.btn-secondary.dropdown-toggle");
//             //     if (moreBtn) {
//             //         console.log("ℹ️ More button clicked");
//             //     }

//             //     // Detect dropdown item click robustly
//             //     let dropdownItem = ev.target;
//             //     console.log('dropdownItem', dropdownItem)
//             //     const dropdownItems = document.querySelectorAll(".dropdown-menu .dropdown-item span");

//             //     // Iterate and log their text values
//             //     dropdownItems.forEach((span, index) => {
//             //         console.log(index, span.textContent.trim());
//             //     });
//             //     // If clicked element is not the dropdown-item, check closest parent
//             //     if (!dropdownItem.classList.contains("dropdown-item")) {
//             //         dropdownItem = dropdownItem.closest(".dropdown-item");

//             //         console.log('dropdownItem', dropdownItem)
//             //     }
//             //     console.log('dropdownItem', dropdownItem)
//             //     if (dropdownItem && dropdownItem.closest(".dropdown-item")) {
//             //         const text = dropdownItem.textContent.trim();
//             //         console.log("ℹ️ Dropdown item clicked:", text);
//             //         handleDropdownClick(text);
//             //     }
//             // });
//             // Attach listener once
//             document.body.addEventListener("click", (ev) => {
//                 // Detect More button click
//                 const moreBtn = ev.target.closest("button.btn.btn-secondary.dropdown-toggle");
//                 if (moreBtn) {
//                     console.log("ℹ️ More button clicked");
//                     // Optional: wait a tick for dropdown to appear
//                     setTimeout(() => {
//                         const dropdownSpans = document.querySelectorAll(".dropdown-menu .dropdown-item span");
//                         dropdownSpans.forEach((span, i) => console.log(i, span.textContent.trim()));
//                     }, 100); // 100ms delay ensures DOM updates
//                 }

//                 // Detect actual dropdown item click
//                 const spanClicked = ev.target.closest(".dropdown-menu .dropdown-item span");
//                 if (spanClicked) {
//                     const text = spanClicked.textContent.trim();
//                     console.log("ℹ️ Dropdown span clicked:", text);
//                     if (text === "Cancelled") {
//                         handleDropdownClick(text);
//                         console.log("✅ Cancelled clicked, show popup here");
//                     }
//                 }
//             });

//         };


//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);
//             window.lastStatusRecord = record;

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);
//                     this.state.jobCardData = data[0];
//                     console.log("📦 Job Card Data:", this.state.jobCardData);

//                     attachClickListeners();

//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });



// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");
//         this.dialog = useService("dialog"); // To show popup

//         this.state = useState({
//             jobCardData: null,
//         });

//         const handleDropdownClick = (itemText) => {
//             const text = itemText.trim();
//             if (text === "Cancelled") {
//                 console.log("✅ Cancelled clicked, showing popup");
//                 // this.dialog.confirm({
//                 //     title: "Job Card Cancelled",
//                 //     body: "You have selected Cancelled for this Job Card.",
//                 //     confirmText: "OK",
//                 //     cancelText: "Cancel",
//                 // }).then(() => {
//                 //     console.log("User confirmed Cancelled");
//                 //     // TODO: Update job card state if needed
//                 // }).catch(() => {
//                 //     console.log("User cancelled the dialog");
//                 // });
//             }
//         };

//         const attachClickListeners = () => {
//             document.body.addEventListener("click", (ev) => {
//                 // Detect More button click
//                 const moreBtn = ev.target.closest("button.btn.btn-secondary.dropdown-toggle");
//                 if (moreBtn) {
//                     console.log("ℹ️ More button clicked");
//                     setTimeout(() => {
//                         const dropdownSpans = document.querySelectorAll(".dropdown-menu .dropdown-item span");
//                         dropdownSpans.forEach((span, i) =>
//                             console.log(i, span.textContent.trim())
//                         );
//                     }, 100);
//                 }

//                 // Detect dropdown item click
//                 // const spanClicked = ev.target.closest(".dropdown-menu .dropdown-item span");
//                 // console.log('span is clicked')
//                 // if (spanClicked) {
//                 //     const text = spanClicked.textContent.trim();
//                 //     console.log("ℹ️ Dropdown span clicked:", text);
//                 //     handleDropdownClick(text);
//                 // }
//                 const spanClicked = ev.target.closest(".dropdown-menu .dropdown-item span");
//                 if (spanClicked) {
//                     const text = spanClicked.textContent.trim();
//                     const parentItem = spanClicked.closest(".dropdown-item");
//                     const index = Array.from(parentItem.parentNode.children).indexOf(parentItem);

//                     console.log("🟢 Dropdown span clicked:", text);
//                     console.log("Parent item element:", parentItem);
//                     console.log("Index in menu:", index);

//                     // Call your handler
//                     handleDropdownClick(text);
//                 }
//             });
//         };


//         // const attachClickListeners = () => {
//         //     const dialog = this.dialog; // store reference
//         //     document.body.addEventListener("click", (ev) => {
//         //         // Detect More button click
//         //         const moreBtn = ev.target.closest("button.btn.btn-secondary.dropdown-toggle");
//         //         if (moreBtn) {
//         //             console.log("ℹ️ More button clicked");
//         //             setTimeout(() => {
//         //                 const dropdownSpans = document.querySelectorAll(".dropdown-menu .dropdown-item span");
//         //                 dropdownSpans.forEach((span, i) =>
//         //                     console.log(i, span.textContent.trim())
//         //                 );
//         //             }, 100);
//         //         }

//         //         // Detect dropdown item click
//         //         const spanClicked = ev.target.closest(".dropdown-menu .dropdown-item span");
//         //         if (spanClicked) {
//         //             const text = spanClicked.textContent.trim();
//         //             console.log("ℹ️ Dropdown span clicked:", text);
//         //             if (text === "Cancelled") {
//         //                 console.log("✅ Cancelled clicked, showing popup");
//         //                 dialog.confirm({
//         //                     title: "Job Card Cancelled",
//         //                     body: "You have selected Cancelled for this Job Card.",
//         //                     confirmText: "OK",
//         //                     cancelText: "Cancel",
//         //                 }).then(() => {
//         //                     console.log("User confirmed Cancelled");
//         //                 }).catch(() => {
//         //                     console.log("User cancelled the dialog");
//         //                 });
//         //             }
//         //         }
//         //     });
//         // };

//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;
//             console.log('record',record.data.cancel_status_check);

//             console.log("🟢 Mounted StatusBarField:", model, recordId);
//             window.lastStatusRecord = record;

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "job_card_state_code",
//                     ]);
//                     this.state.jobCardData = data[0];
//                     console.log("📦 Job Card Data:", this.state.jobCardData);

//                     attachClickListeners();

//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });

/** @odoo-module **/
/** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { useService } from "@web/core/utils/hooks";
// import { useState, onMounted } from "@odoo/owl";

// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");

//         // ✅ FIX: Initialize state properly
//         this.state = useState({
//             jobCardData: {},
//         });

//         // Function moved inside setup for access to `this`
//         const attachClickListeners = (self) => {
//             document.body.addEventListener("click", (ev) => {
//                 const spanClicked = ev.target.closest(".dropdown-menu .dropdown-item span");
//                 if (!spanClicked) return;

//                 const text = spanClicked.textContent.trim();
//                 console.log("🟢 Dropdown item clicked:", text);

//                 if (text === "Cancelled") {
//                     const cancelCheck = self.state?.jobCardData?.cancel_status_check;
//                     console.log("🔍 cancel_status_check:", cancelCheck);

//                     if (cancelCheck) {
//                         console.log("🚀 Opening Cancel Wizard Popup...");

//                         self.action.doAction({
//                             type: "ir.actions.act_window",
//                             name: "Cancel Reason",
//                             res_model: "cancel.reason.wizard",
//                             views: [[false, "form"]],
//                             target: "new",
//                             context: {
//                                 default_task_id: self.props.record.resId,
//                             },
//                         });
//                     }
//                 }
//             });
//         };

//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "cancel_status_check",
//                     ]);
//                     this.state.jobCardData = data[0] || {};
//                     console.log("📦 Job Card Data:", this.state.jobCardData);

//                     attachClickListeners(this);
//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });


/** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { useService } from "@web/core/utils/hooks";
// import { useState, onMounted } from "@odoo/owl";

// patch(StatusBarField.prototype, {
//     setup() {
//         super.setup();
//         this.action = useService("action");
//         this.orm = useService("orm");
//         this.state = useState({ jobCardData: {} });

//         const attachClickListeners = (self) => {
//             document.body.addEventListener("click", (ev) => {
//                 // ✅ Detect both direct state clicks and dropdown items
//                 const spanClicked =
//                     ev.target.closest(".o_statusbar_status span") ||
//                     ev.target.closest(".dropdown-menu .dropdown-item span");

//                 if (!spanClicked) return;

//                 const text = spanClicked.textContent.trim();
//                 console.log("🟢 Status clicked:", text);

//                 if (text === "Cancelled") {
//                     const cancelCheck = self.state?.jobCardData?.cancel_status_check;
//                     console.log("🔍 cancel_status_check:", cancelCheck);

//                     if (cancelCheck) {
//                         console.log("🚀 Triggering Cancelled Reason button...");

//                         // ✅ Find your specific button in the DOM
//                         const cancelBtn = document.querySelector('button[name="cancelled_reason_button_mobile"]');

//                         if (cancelBtn) {
//                             cancelBtn.click(); // ✅ Programmatically trigger it
//                             console.log("✅ cancelled_reason_button_mobile clicked automatically");
//                         } else {
//                             console.warn("⚠️ Button cancelled_reason_button_mobile not found. Opening popup manually.");
//                             self.action.doAction({
//                                 type: "ir.actions.act_window",
//                                 name: "Cancelled Reason",
//                                 res_model: "cancel.reason.wizard",
//                                 views: [[false, "form"]],
//                                 target: "new",
//                                 context: {
//                                     default_task_id: self.props.record.resId,
//                                 },
//                             });
//                         }
//                     } else {
//                         console.log("⚠️ cancel_status_check = false, no action triggered.");
//                     }
//                 }
//             });
//         };

//         onMounted(async () => {
//             const record = this.props.record;
//             const recordId = record?.resId;
//             const model = record?.resModel;

//             console.log("🟢 Mounted StatusBarField:", model, recordId);

//             if (model === "project.task" && recordId) {
//                 try {
//                     const data = await this.orm.read(model, [recordId], [
//                         "name",
//                         "job_state",
//                         "cancel_status_check",
//                     ]);
//                     this.state.jobCardData = data[0] || {};
//                     console.log("📦 Job Card Data:", this.state.jobCardData);

//                     attachClickListeners(this);
//                 } catch (error) {
//                     console.error("❌ Error fetching Job Card data:", error);
//                 }
//             }
//         });
//     },
// });







// /** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
// import { useService } from "@web/core/utils/hooks";
// import { useState } from "@odoo/owl";

// patch(StatusBarField.prototype, {
//     setup() {
//         // keep original setup behavior
//         super.setup && super.setup(...arguments);

//         this.action = useService('action');
//         this.orm = useService('orm');
//         this.state = useState({ jobCardData: {} });

//         // prefetch one-time data for the current record (if project.task)
//         try {
//             const record = this.props.record;
//             if (record && record.resModel === 'project.task' && record.resId) {
//                 // read only the required field
//                 this.orm.read(record.resModel, [record.resId], 
//                     ['cancel_status_check', 'job_state', 'job_card_state_code', 'job_card_state'])
//                     .then(data => {
//                         this.state.jobCardData = data[0] || {};
//                         console.log('[statusbar_cancel] jobCardData', this.state.jobCardData);
//                     })
//                     .catch(err => console.error('[statusbar_cancel] orm.read error', err));
//             }
//         } catch (e) {
//             console.error('[statusbar_cancel] setup error', e);
//         }
//     },

//     // intercept status click (works for direct buttons and dropdown)
//     async onStatusClick(ev, state) {
//         console.warn('[statusbar_cancel] calling original onStatusClick failed');

//         const fieldName = this.props.name;
//         const record = this.props.record;
//         const previousStage = record?.data?.[fieldName]?.[1];
//         const [clickedStageId, clickedStageName] = state || [null, null];

//         // let original logic run (it does the stage change)
//         try {
//             await this._super(ev, state);
//         } catch (e) {
//             // some versions use super, keep a fallback
//             console.warn('[statusbar_cancel] calling original onStatusClick failed', e);
//         }

//         // after the stage change attempt, run our logic
//         try {
//             // ensure we only react when user clicked Cancelled and previous wasn't Cancelled
//             if (clickedStageName === 'Cancelled' && previousStage !== 'Cancelled') {
//                 const cancelCheck = this.state?.jobCardData?.cancel_status_check;
//                 console.log('[statusbar_cancel] clicked Cancelled, cancel_status_check=', cancelCheck);

//                 if (cancelCheck) {
//                     // try to find and trigger your specific button
//                     const btn = document.querySelector('button[name="cancelled_reason_button_mobile"]');

//                     if (btn) {
//                         // small delay to ensure DOM updates completed
//                         setTimeout(() => {
//                             try {
//                                 btn.click();
//                                 console.log('[statusbar_cancel] triggered cancelled_reason_button_mobile');
//                             } catch (err) {
//                                 console.error('[statusbar_cancel] failed to click button', err);
//                             }
//                         }, 50);
//                     } else {
//                         // fallback: open the wizard directly
//                         console.warn('[statusbar_cancel] button not found, opening wizard fallback');
//                         this.action.doAction({
//                             type: 'ir.actions.act_window',
//                             name: 'Cancelled Reason',
//                             res_model: 'cancel.reason.wizard',
//                             view_mode: 'form',
//                             target: 'new',
//                             context: { default_task_id: record.resId },
//                         });
//                     }
//                 } else {
//                     console.log('[statusbar_cancel] cancel_status_check is false — no action');
//                 }
//             }
//         } catch (err) {
//             console.error('[statusbar_cancel] post-click handler error', err);
//         }
//     },
// });

/** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";

// const { onMounted } = owl;

// // Patch the FormController so we can react when the form loads
// patch(FormController.prototype, {
//     setup() {
//         super.setup(...arguments);
//         this.orm = useService("orm");
//         this.action = useService("action");

//         // run after DOM is mounted (record loaded)
//         onMounted(async () => {
//             try {
//                 const record = this.model.root;
//                 if (!record || record.resModel !== "project.task") return;

//                 const resId = record.resId;
//                 if (!resId) return;

//                 // read the field value
//                 const data = await this.orm.read("project.task", [resId], ["cancel_status_check"]);
//                 const cancelStatus = data?.[0]?.cancel_status_check || false;

//                 console.log("[auto_cancel_reason] cancel_status_check =", cancelStatus);

//                 if (cancelStatus) {
//                     console.log("[auto_cancel_reason] Opening Cancel Reason wizard automatically...");
//                     this.action.doAction({
//                         type: "ir.actions.act_window",
//                         name: "Cancelled Reason",
//                         res_model: "cancel.reason.wizard",
//                         view_mode: "form",
//                         target: "new",
//                         context: { default_task_id: resId },
//                     });
//                 }
//             } catch (err) {
//                 console.error("[auto_cancel_reason] error:", err);
//             }
//         });
//     },
// });

// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";

// const { onMounted } = owl;

// // Patch the FormController to trigger wizard automatically after form is loaded
// patch(FormController.prototype, {
//     setup() {
//         super.setup(...arguments);

//         // Load Odoo services
//         this.orm = useService("orm");
//         this.action = useService("action");

//         // Run when DOM + record is ready
//         onMounted(async () => {
//             try {
//                 const record = this.model.root;
//                 if (!record || record.resModel !== "project.task") return;

//                 const resId = record.resId;
//                 if (!resId) return;

//                 // Read the field value from backend
//                 const data = await this.orm.read("project.task", [resId], ["cancel_status_check"]);
//                 const cancelStatus = data?.[0]?.cancel_status_check || false;

//                 console.log("[auto_cancel_reason] cancel_status_check =", cancelStatus);

//                 if (cancelStatus) {
//                     console.log("[auto_cancel_reason] Opening Cancel Reason wizard automatically...");

//                     // Try to get the default form view for the wizard
//                     // const viewsData = await this.orm.call("ir.model.data", "xmlid_to_res_id", [
//                     //     "machine_repair_management.cancelled_reason_wizard_form_view", // replace with your XML ID
//                     //     "ir.ui.view",
//                     // ]);
//                     // const viewsData= machine_repair_management.cancelled_reason_wizard_form_view;
//                     // const viewsData = "machine_repair_management.cancelled_reason_wizard_form_view";

//                     // console.log('viewsData', viewsData)

//                     // const viewId = viewsData || false;

//                     // Open wizard safely
//                     await this.action.doAction({
//                         type: "ir.actions.act_window",
//                         name: "Cancelled Reason",
//                         res_model: "cancelled.reason.wizard",
//                         view_mode: "form",
//                         // view_id: viewId,
//                         views: [[false, "form"]],
//                         target: "new",
//                         context: { default_job_card_id: resId },
//                     });
//                 }
//             } catch (err) {
//                 console.error("[auto_cancel_reason] error:", err);
//             }
//         });
//     },
// });

// /** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";
// // import { nextTick } from "owl";
// // import { nextTick } from "@web/tests/helpers/utils";
// // // import { nextTick } from "@web/../tests/helpers/utils";
// // // /home/cielovb/odoo17/odoo/addons/web/static/tests/helpers/utils.js

// console.log("[auto_cancel_reason] Original loadRecord finished");


// patch(FormController.prototype, {

// console.log("[auto_cancel_reason] Original loadRecord finished");
//     async loadRecord(record, options) {
//         console.log("[auto_cancel_reason] loadRecord called", record);

//         // Call original loadRecord
//         await this._super(...arguments);
//         console.log("[auto_cancel_reason] Original loadRecord finished");

//         // Schedule async logic after OWL lifecycle
//         nextTick(async () => {
//             console.log("[auto_cancel_reason] nextTick started for async logic");

//             try {
//                 if (!record) {
//                     console.log("[auto_cancel_reason] No record found, exiting");
//                     return;
//                 }

//                 console.log("[auto_cancel_reason] record resModel:", record.resModel);
//                 if (record.resModel !== "project.task") {
//                     console.log("[auto_cancel_reason] Not a project.task, exiting");
//                     return;
//                 }

//                 const resId = record.resId;
//                 console.log("[auto_cancel_reason] resId:", resId);
//                 if (!resId) {
//                     console.log("[auto_cancel_reason] No resId, exiting");
//                     return;
//                 }

//                 const orm = useService("orm");
//                 const action = useService("action");

//                 console.log("[auto_cancel_reason] Reading cancel_status_check field from backend...");
//                 const data = await orm.read("project.task", [resId], ["cancel_status_check"]);
//                 console.log("[auto_cancel_reason] Data fetched from backend:", data);

//                 const cancelStatus = data?.[0]?.cancel_status_check || false;
//                 console.log("[auto_cancel_reason] cancel_status_check =", cancelStatus);

//                 if (cancelStatus) {
//                     console.log("[auto_cancel_reason] Condition true, opening Cancel Reason wizard...");

//                     await action.doAction({
//                         type: "ir.actions.act_window",
//                         name: "Cancelled Reason",
//                         res_model: "cancelled.reason.wizard",
//                         view_mode: "form",
//                         views: [[false, "form"]],
//                         target: "new",
//                         context: { default_job_card_id: resId },
//                     });

//                     console.log("[auto_cancel_reason] Wizard opened successfully");
//                 } else {
//                     console.log("[auto_cancel_reason] Condition false, wizard not opened");
//                 }
//             } catch (err) {
//                 console.error("[auto_cancel_reason] error in async logic:", err);
//             }
//         });
//     },
// });

// //** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";
// // const { onMounted, onWillUpdateProps } = owl;
// import { onWillStart, useState, onWillUpdateProps, Component } from "@odoo/owl";


// patch(FormController.prototype, {
//     setup() {
//         super.setup(...arguments);
//         this.orm = useService("orm");
//         this.action = useService("action");

//         // 🔁 Check field after form is first mounted
//         onMounted(() => this._checkCancelStatus());

//         // 🔁 Check field again when form data changes (record updated)
//         onWillUpdateProps(() => this._checkCancelStatus());
//     },

//     // onWillStart(async () => await this.fetchHierarchy(this.props.record.resId));

//     //     onWillUpdateProps(async (nextProps) => {
//     //         await this.fetchHierarchy(nextProps.record.resId);
//     //     });

//     async _checkCancelStatus() {
//         try {
//             const record = this.model.root;
//             if (!record || record.resModel !== "project.task" || !record.resId) return;

//             const resId = record.resId;

//             // 🧩 Read the cancel_status_check field every time
//             const data = await this.orm.read("project.task", [resId], ["cancel_status_check"]);
//             const cancelStatus = data?.[0]?.cancel_status_check || false;

//             console.log("[auto_cancel_reason] cancel_status_check =", cancelStatus);

//             if (cancelStatus) {
//                 // ✅ Open the Cancel Reason wizard popup
//                 console.log("[auto_cancel_reason] Opening Cancel Reason wizard automatically...");                
//                 await this.action.doAction({
//                     type: "ir.actions.act_window",
//                     name: "Cancelled Reason",
//                     res_model: "cancelled.reason.wizard",
//                     view_mode: "form",
//                     views: [[false, "form"]], // ✅ dynamically pick the default form
//                     target: "new",
//                     context: { default_job_card_id: resId },
//                 });
//             }

//         } catch (err) {
//             console.error("[auto_cancel_reason] Error:", err);
//         }
//     },
// });

// /** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService, nextTick } from "@web/core/utils/hooks";
// // import { nextTick } from "owl";

// patch(FormController.prototype, {
//     async loadRecord(record, options) {
//         console.log("[auto_cancel_reason] loadRecord called", record);

//         // Call the original method
//         await this._super(...arguments);

//         // Schedule async logic after OWL lifecycle
//         nextTick(async () => {
//             try {
//                 if (!record || record.resModel !== "project.task" || !record.resId) return;

//                 const resId = record.resId;
//                 const orm = useService("orm");
//                 const action = useService("action");

//                 const data = await orm.read("project.task", [resId], ["cancel_status_check"]);
//                 const cancelStatus = data?.[0]?.cancel_status_check || false;

//                 console.log("[auto_cancel_reason] cancel_status_check =", cancelStatus);

//                 if (cancelStatus) {
//                     console.log("[auto_cancel_reason] Opening Cancel Reason wizard automatically...");
//                     await action.doAction({
//                         type: "ir.actions.act_window",
//                         name: "Cancelled Reason",
//                         res_model: "cancelled.reason.wizard",
//                         view_mode: "form",
//                         views: [[false, "form"]],
//                         target: "new",
//                         context: { default_job_card_id: resId },
//                     });
//                 }
//             } catch (err) {
//                 console.error("[auto_cancel_reason] Error:", err);
//             }
//         });
//     },
// });

// /** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService, nextTick } from "@web/core/utils/hooks";

// patch(FormController.prototype, {
//     async loadRecord(record, options) {
//         // Call original method first
//         await this._super(...arguments);

//         // Schedule async logic safely after OWL lifecycle
//         nextTick(async () => {
//             try {
//                 if (!record || record.resModel !== "project.task" || !record.resId) return;

//                 const resId = record.resId;
//                 const orm = useService("orm");
//                 const action = useService("action");

//                 const data = await orm.read("project.task", [resId], ["cancel_status_check"]);
//                 const cancelStatus = data?.[0]?.cancel_status_check || false;

//                 if (cancelStatus) {
//                     await action.doAction({
//                         type: "ir.actions.act_window",
//                         name: "Cancelled Reason",
//                         res_model: "cancelled.reason.wizard",
//                         view_mode: "form",
//                         views: [[false, "form"]],
//                         target: "new",
//                         context: { default_job_card_id: resId },
//                     });
//                 }
//             } catch (err) {
//                 console.error("[auto_cancel_reason] Error:", err);
//             }
//         });
//     },
// });

// WORKING CODE - 11-10-2025
// /** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { FormRenderer } from "@web/views/form/form_renderer";
// import { useService } from "@web/core/utils/hooks";
// import { onMounted, onWillUpdateProps } from "@odoo/owl";

// patch(FormRenderer.prototype, {
//     setup() {
//         super.setup(...arguments);

//         this.orm = useService("orm");
//         this.action = useService("action");

//         // Track if wizard has already been opened for this record
//         this._wizardOpened = false;

//         // Check on form load
//         onMounted(() => this._checkCancelStatus());

//         // Check again whenever props change (record updated)
//         onWillUpdateProps(() => this._checkCancelStatus());
//     },

//     async _checkCancelStatus() {
//         try {
//             const record = this.props.record;
//             if (!record || record.resModel !== "project.task" || !record.resId) return;

//             // Avoid opening multiple times
//             if (this._wizardOpened) return;

//             const resId = record.resId;

//             const data = await this.orm.read("project.task", [resId], ["cancel_status_check"]);
//             const cancelStatus = data?.[0]?.cancel_status_check || false;

//             console.log("[auto_cancel_reason] cancel_status_check =", cancelStatus);

//             if (cancelStatus) {
//                 this._wizardOpened = true;
//                 console.log("[auto_cancel_reason] Opening Cancel Reason wizard automatically...");
//                 await this.action.doAction({
//                     type: "ir.actions.act_window",
//                     name: "Cancelled Reason",
//                     res_model: "cancelled.reason.wizard",
//                     view_mode: "form",
//                     views: [[false, "form"]],
//                     target: "new",
//                     context: { default_job_card_id: resId },
//                 });
//             }

//         } catch (err) {
//             console.error("[auto_cancel_reason] Error:", err);
//         }
//     },
// });


/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUpdateProps } from "@odoo/owl";

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");
        this.action = useService("action");

        // Track initial field value
        this._initialCancelStatus = null;

        // Track if wizard has already been opened
        this._wizardOpened = false;

        // Check initial value on form load
        onMounted(async () => {
            const record = this.props.record;
            if (!record || record.resModel !== "project.task" || !record.resId) return;

            const resId = record.resId;
            const data = await this.orm.read("project.task", [resId], ["cancel_status_check"]);
            this._initialCancelStatus = data?.[0]?.cancel_status_check || false;

            console.log("[auto_cancel_reason] Initial cancel_status_check =", this._initialCancelStatus);
        });

        // Check whenever record is updated
        onWillUpdateProps(() => this._checkCancelStatus());
    },
	 async _checkCancelStatus() {
	        try {
	            const record = this.props.record;
	            if (!record || record.resModel !== "project.task" || !record.resId) return;

	            if (this._wizardOpened) return;

	            const resId = record.resId;
	            const data = await this.orm.read("project.task", [resId], ["cancel_status_check"]);
	            const cancelStatus = data?.[0]?.cancel_status_check || false;

	            console.log("[auto_cancel_reason] Current cancel_status_check =", cancelStatus);

	            // Only open wizard if field was initially false and now became true
	            if (cancelStatus && this._initialCancelStatus === false) {
	                this._wizardOpened = true;
	                console.log("[auto_cancel_reason] Opening Cancel Reason wizard automatically...");
	                await this.action.doAction({
	                    type: "ir.actions.act_window",
	                    name: "Cancelled Reason",
	                    res_model: "cancelled.reason.wizard",
	                    view_mode: "form",
	                    views: [[false, "form"]],
	                    target: "new",
	                    context: { default_job_card_id: resId },
	                    /*flags: {
	                        // Important: use `modal: true` to force modal behavior
	                        modal: true,
	                        // Prevent quick close (top-right X)
	                        no_quick_close: true,
	                        // Disable default footer buttons
	                        hide_default_buttons: true,
	                    },*/
	                });
	            }

	        } catch (err) {
	            console.error("[auto_cancel_reason] Error:", err);
	        }



	setTimeout(() => {
	    const closeButton = document.querySelector('.modal-header .btn-close');

	    if (closeButton) {
	        closeButton.style.display = 'none';
	        console.log('Close button hidden');
	    } else {
	        console.warn('Close button not found');
	    }
	}, 100);

	    },

});



/** @odoo-module **/
/*import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUpdateProps } from "@odoo/owl";

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");
        this.action = useService("action");

        // Track initial field value
        this._initialCancelStatus = null;

        // Track if wizard has already been opened
        this._wizardOpened = false;

        // Check initial value on form load
        onMounted(async () => {
            const record = this.props.record;
            if (!record || record.resModel !== "project.task" || !record.resId) return;

            const resId = record.resId;
            const data = await this.orm.read("project.task", [resId], ["cancel_status_check"]);
            this._initialCancelStatus = data?.[0]?.cancel_status_check || false;

            console.log("[auto_cancel_reason] Initial cancel_status_check =", this._initialCancelStatus);


            const modalEl = document.querySelector(".modal.show");
            if (modalEl) {
                const closeBtn = modalEl.querySelector(".btn-close");
                if (closeBtn) closeBtn.remove(); // 👈 removes top-right X
            }
        });

        // Check whenever record is updated
        onWillUpdateProps(() => this._checkCancelStatus());
    },

    async _checkCancelStatus() {
        try {
            const record = this.props.record;
            if (!record || record.resModel !== "project.task" || !record.resId) return;

            if (this._wizardOpened) return;

            const resId = record.resId;
            const data = await this.orm.read("project.task", [resId], ["cancel_status_check"]);
            const cancelStatus = data?.[0]?.cancel_status_check || false;

            console.log("[auto_cancel_reason] Current cancel_status_check =", cancelStatus);

            // Only open wizard if field was initially false and now became true
            if (cancelStatus && this._initialCancelStatus === false) {
                this._wizardOpened = true;
                console.log("[auto_cancel_reason] Opening Cancel Reason wizard automatically...");
                await this.action.doAction({
                    type: "ir.actions.act_window",
                    name: "Cancelled Reason",
                    res_model: "cancelled.reason.wizard",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    context: { default_job_card_id: resId },
                    flags: {
                        formViewOptions: {
                            hide_default_buttons: true,  // <-- hides the Close button
                        },
                    },
                    // flags: {
                    //         // Important: use `modal: true` to force modal behavior
                    //         modal: true,
                    //         // Prevent quick close (top-right X)
                    //         no_close: true,
                    //         // Disable default footer buttons
                    //         // hide_default_buttons: true,
                    //     },
                });
            }

        } catch (err) {
            console.error("[auto_cancel_reason] Error:", err);
        }
    },
});
*/

