/** @odoo-module **/

// import { Component, useState, useEnv } from "@odoo/owl";
// import { registry } from "@web/core/registry";
// import { useService, useBus } from "@web/core/utils/hooks";
// export class MyComponent extends Component {
//   static template = "MyComponent";

//   setup() {
//     this.env = useEnv();
//     this.orm = useService("orm");
//     this.actionService = useService("action");
//     this.notification = useService("notification");

//     const context = this.env.searchModel?._context || {};
//     this.state = useState({
//       jobcardId: context.active_id || null,
//       hideJobcardList: context.hide_jobcard_list || false,
//       jobCardNumber:
//         context.job_card_number ||
//         sessionStorage.getItem("jobCardNumber") ||
//         "",
//       customerName:
//         context.customer_name || sessionStorage.getItem("customerName") || "",
//       serviceDatetime:
//         context.service_requested_datetime ||
//         sessionStorage.getItem("serviceDatetime") ||
//         "",
//       planned_date_begin: context.planned_date_begin || "",
//       planned_date_end: context.planned_date_end || "",
//       job_card_state_code: context.job_card_state_code || "",
//       job_card_state: context.job_card_state || "",
//       job_state: context.job_state || "",
//       user_ids: [],
//       teamId: null,
//       technicianName: "",
//       service_requested_datetime_formatted: "",
//     });

//     if (this.state.serviceDatetime) {
//       const d = new Date(this.state.serviceDatetime.replace(" ", "T"));
//       d.setHours(d.getHours() + 3); // Adjust timezone
//       const pad = (n) => n.toString().padStart(2, "0");
//       this.state.service_requested_datetime_formatted = `${pad(
//         d.getDate()
//       )}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(
//         d.getMinutes()
//       )}:${pad(d.getSeconds())}`;
//     }

//     this.hasSlotClicked = false;

//     if (this.env.bus) {
//       useBus(this.env.bus, "toggle-jobcard-list", (ev) => {
//         this.state.hideJobcardList = ev.detail.hideJobcardList;
//       });

//       useBus(this.env.bus, "slot-clicked", (event) => {
//         if (!this.hasSlotClicked) {
//           this.hasSlotClicked = true;
//           this.updateSelectedJobCard(event.detail, true);
//         }
//       });
//     }
//   }

//   async updateSelectedJobCard(data, isSlot = false) {
//     if (!data) return;
//     const now = new Date();
//     now.setHours(0, 0, 0, 0);

//     // Validate slot date (cannot schedule past)
//     if (isSlot && data.planned_date_begin) {
//       const plannedBegin = new Date(data.planned_date_begin);
//       const plannedEnd = data.planned_date_end
//         ? new Date(data.planned_date_end)
//         : null;

//       if (plannedBegin < now || (plannedEnd && plannedEnd < now)) {
//         this.notification.add(
//           `⚠️ Scheduling Error: Jobcards cannot be assigned to past dates. Please select today or a future date.`,
//           { type: "danger" }
//         );
//         this.hasSlotClicked = false;
//         return;
//       }
//     }

//     // Update job card info
//     if (data.id && !data.planned_date_begin) {
//       this.state.jobcardId = data.id;
//       this.state.name = data.name || "";
//       this.state.customerName = data.customer_name || "";
//       this.state.planned_date_begin = null;
//       this.state.planned_date_end = null;
//       this.state.user_ids = [];
//       this.state.teamId = null;
//       this.state.technicianName = "";
//     } else if (isSlot) {
//       this.state.planned_date_begin = data.planned_date_begin || null;
//       this.state.planned_date_end = data.planned_date_end || null;
//       this.state.user_ids = data.user_ids || [];
//       this.state.teamId = data.user_ids?.length
//         ? parseInt(data.user_ids[0])
//         : null;
//     }

//     if (this.state.teamId) {
//       try {
//         const users = await this.orm.call("res.users", "read", [
//           [this.state.teamId],
//           ["name"],
//         ]);
//         this.state.technicianName = users?.[0]?.name || null;
//       } catch {
//         this.state.technicianName = null;
//       }
//     } else {
//       this.state.technicianName = null;
//     }

//     sessionStorage.setItem("jobcardId", this.state.jobcardId);
//     sessionStorage.setItem("jobCardNumber", this.state.jobCardNumber);
//     sessionStorage.setItem("customerName", this.state.customerName);
//     sessionStorage.setItem("serviceDatetime", this.state.serviceDatetime || "");

//     try {
//       await this.updateJobCard();
//     } catch (err) {
//       console.error(err);
//     } finally {
//       this.hasSlotClicked = true;
//     }
//   }

//   async updateJobCard() {
//     const previousjobStateCode = this.state.job_card_state_code;
//     let jobStateCode = this.state.job_card_state_code;

//     //Allow updates only for specific job states
//     if (![101, 117, 132, 204, 133, 122, 134].includes(parseInt(jobStateCode))) {
//       this.notification.add(
//         "⚠️ Only jobcards in 'Draft', 'New', or 'Scheduled' states can be updated.",
//         { type: "warning" }
//       );
//       return;
//     }

//     // Restrict technician reassignment for states 117, 132, 204, 133
//     const noReassignStates = [204, 133, 134]; // States where reassignment is not allowed
//     if (noReassignStates.includes(parseInt(jobStateCode))) {
//       this.notification.add(
//         "⚠️ Technician reassignment is not allowed in this job state.",
//         { type: "warning" }
//       );
//       return;
//     }
//     // const targetCode = Number(jobStateCode) === 117 ? 204 : jobStateCode;
//     // console.log(targetCode);
//     const targetCode =
//       Number(jobStateCode) === 101
//         ? 102
//         : Number(jobStateCode) === 117
//         ? 204
//         : Number(jobStateCode) === 132
//         ? 133
//         : Number(jobStateCode) === 122
//         ? 134
//         : jobStateCode;

//     console.log(targetCode);

//     let taskStages = await this.orm.searchRead(
//       "project.task.type",
//       [["code", "=", String(targetCode)]],
//       [("id", "code", "name")]
//     );
//     console.log("taskStages", taskStages);
//     // Use the first record as your stateTransition
//     const stateTransition = {
//       job_state: taskStages[0].id,
//       job_card_state: taskStages[0].name,
//     };
//     console.log("stateTransition:", stateTransition);

//     const payload = {
//       jobcardId: this.state.jobcardId,
//       plannedDateBegin: this.state.planned_date_begin,
//       plannedDateEnd: this.state.planned_date_end,
//       technician_id: this.state.teamId || null,
//       job_card_state_code: targetCode,
//       ...stateTransition,
//     };
//     // this.hasSlotClicked = true;

//     console.log("✅ Payload:", payload);
//     const jobcardIdInt = parseInt(payload.jobcardId, 10);
//     if (!jobcardIdInt) return;

//     try {
//       const [taskData] = await this.orm.searchRead(
//         "project.task",
//         [["id", "=", jobcardIdInt]],
//         ["second_visit_technician_bool", "technician_first_visit_id"]
//       );

//       const isSecondVisit = taskData?.second_visit_technician_bool || false;

//       console.log("Second Visit Bool:", isSecondVisit);

//       const values = {
//         planned_date_begin: payload.plannedDateBegin,
//         planned_date_end: payload.plannedDateEnd,
//         job_card_state_code: targetCode,
//         job_state: payload.job_state,
//         job_card_state: payload.job_card_state,
//         technician_id: payload.technician_id,
//       };

//       if (!taskData?.technician_first_visit_id) {
//         values.technician_first_visit_id = payload.technician_id;
//       } else if (taskData?.second_visit_technician_bool) {
//         values.technician_second_visit_id = payload.technician_id;
//       } else {
//         console.log(
//           "ℹ️ Technician assignment skipped (no eligible visit condition)."
//         );
//       }

//       this.highlightSlotCell();

//       await this.orm.write("project.task", [jobcardIdInt], values);

//       sessionStorage.setItem("lastJobcardId", payload.jobcardId);
//       sessionStorage.setItem("plannedStart", payload.plannedDateBegin);

//       this.notification.add(
//         `✅ Task updated successfully\nJobcard Number: ${
//           this.state.jobCardNumber || this.state.name
//         }\nTechnician: ${this.state.technicianName}`,
//         { type: "success" }
//       );

//       const mrsRecords = await this.orm.searchRead(
//         "machine.repair.support",
//         [["task_id", "=", jobcardIdInt]],
//         ["id"]
//       );

//       if (mrsRecords?.length) {
//         const taskData2 = await this.orm.read(
//           "project.task",
//           [jobcardIdInt],
//           ["team_id"]
//         );
//         const taskTeamId = taskData2?.[0]?.team_id?.[0] || null;

//         const valuesMRS = {
//           task_id: payload.jobcardId,
//           service_request_state: payload.job_card_state,
//           service_request_state_code: payload.job_card_state_code,
//           user_id: payload.technician_id,
//           team_id: taskTeamId,
//           call_request_appointment_date: this.state.serviceDatetime || null,
//           technician_appointment_date: payload.plannedDateBegin || null,
//         };

//         const mrsIds = mrsRecords.map((r) => r.id).filter((id) => !isNaN(id));
//         if (mrsIds.length) {
//           await this.orm.write("machine.repair.support", mrsIds, valuesMRS);
//         }
//       }
//     } catch (err) {
//       this.notification.add("❌ Failed to update Job Card or MRS.", {
//         type: "danger",
//       });
//       console.error(err);
//     }

//     setTimeout(() => {
//       const nextArrows = document.querySelectorAll(".oi.oi-arrow-right");
//       nextArrows.forEach((el) => el.click());
//       const previousArrows = document.querySelectorAll(".oi.oi-arrow-left");
//       previousArrows.forEach((el) => el.click());
//       sessionStorage.removeItem("lastJobcardId");
//     }, 2000);
//   }

//   highlightSlotCell() {
//     const container =
//       document.querySelector(
//         ".o_gantt_view, .o_gantt, .o_content, .o_view_controller"
//       ) || document.body;

//     if (!container) return;

//     let overlay = document.createElement("div");
//     overlay.id = "slotHighlightOverlay";
//     Object.assign(overlay.style, {
//       position: "absolute",
//       borderRadius: "6px",
//       background: "rgba(255, 235, 59, 0.55)",
//       outline: "2px solid rgba(255, 193, 7, 0.9)",
//       pointerEvents: "none",
//       zIndex: "9999",
//       display: "flex",
//       alignItems: "center",
//       justifyContent: "center",
//       color: "#000",
//       fontWeight: "bold",
//       fontSize: "10px",
//       textAlign: "center",
//     });

//     container.addEventListener("click", (ev) => {
//       const cell = ev.target.closest(
//         "td[data-resource-id][data-date], td[data-date], .o_gantt_cell[data-date]"
//       );
//       if (!cell) return;

//       if (overlay.parentElement) overlay.parentElement.removeChild(overlay);
//       document.body.appendChild(overlay);

//       const widthPx = 140;
//       const heightPx = 45;

//       const top = ev.clientY;
//       const left = ev.clientX;

//       Object.assign(overlay.style, {
//         width: widthPx + "px",
//         height: heightPx + "px",
//         top: top + "px",
//         left: left + "px",
//       });

//       overlay.textContent = `Technician: ${this.state.technicianName || "N/A"}`;

//       setTimeout(() => overlay.remove(), 5000);
//     });
//   }
// }

// registry.category("components").add("MyComponent", MyComponent);


//commanded on - 20-11-2025
/** @odoo-module **/

//import { Component, useState, onMounted, useEnv } from "@odoo/owl";
//import { registry } from "@web/core/registry";
//import { useService, useBus } from "@web/core/utils/hooks";
//import { useTaskStages } from "./useTaskStages";
//
//export class MyComponent extends Component {
//  static template = "MyComponent";
//
//  setup() {
//    this.env = useEnv();
//    this.orm = useService("orm");
//    this.actionService = useService("action");
//    this.notification = useService("notification");
//    //  ✅ Hook instance
//    this.taskStageHook = useTaskStages();
//
//    const context = this.env.searchModel?._context || {};
//    this.state = useState({
//      jobcardId: context.active_id || null,
//      hideJobcardList: context.hide_jobcard_list || false,
//      jobCardNumber:
//        context.job_card_number ||
//        sessionStorage.getItem("jobCardNumber") ||
//        "",
//      customerName:
//        context.customer_name || sessionStorage.getItem("customerName") || "",
//      serviceDatetime:
//        context.service_requested_datetime ||
//        sessionStorage.getItem("serviceDatetime") ||
//        "",
//      planned_date_begin: context.planned_date_begin || "",
//      planned_date_end: context.planned_date_end || "",
//      job_card_state_code: context.job_card_state_code || "",
//      job_card_state: context.job_card_state || "",
//      job_state: context.job_state || "",
//      user_ids: [],
//      teamId: null,
//      technicianName: "",
//      service_requested_datetime_formatted: "",
//    });
//
//    // Format datetime if available
//    if (this.state.serviceDatetime) {
//      const d = new Date(this.state.serviceDatetime.replace(" ", "T"));
//      d.setHours(d.getHours() + 3); // adjust timezone
//      const pad = (n) => n.toString().padStart(2, "0");
//      this.state.service_requested_datetime_formatted = `${pad(
//        d.getDate()
//      )}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(
//        d.getMinutes()
//      )}:${pad(d.getSeconds())}`;
//    }
//
//    this.hasSlotClicked = false;
//
//    // Event listeners
//    if (this.env.bus) {
//      useBus(this.env.bus, "toggle-jobcard-list", (ev) => {
//        this.state.hideJobcardList = ev.detail.hideJobcardList;
//      });
//
//      useBus(this.env.bus, "slot-clicked", (event) => {
//        if (!this.hasSlotClicked) {
//          this.hasSlotClicked = true;
//          this.updateSelectedJobCard(event.detail, true);
//        }
//      });
//    }
//  }
//
//  async updateSelectedJobCard(data, isSlot = false) {
//    if (!data) return;
//    const now = new Date();
//    now.setHours(0, 0, 0, 0);
//
//    if (isSlot && data.planned_date_begin) {
//      const plannedBegin = new Date(data.planned_date_begin);
//      const plannedEnd = data.planned_date_end
//        ? new Date(data.planned_date_end)
//        : null;
//
//      if (plannedBegin < now || (plannedEnd && plannedEnd < now)) {
//        this.notification.add(
//          `⚠️ Scheduling Error: Jobcards cannot be assigned to past dates.`,
//          { type: "danger" }
//        );
//        this.hasSlotClicked = false;
//        return;
//      }
//    }
//
//    if (data.id && !data.planned_date_begin) {
//      this.state.jobcardId = data.id;
//      this.state.name = data.name || "";
//      this.state.customerName = data.customer_name || "";
//      this.state.planned_date_begin = null;
//      this.state.planned_date_end = null;
//      this.state.user_ids = [];
//      this.state.teamId = null;
//      this.state.technicianName = "";
//    } else if (isSlot) {
//      this.state.planned_date_begin = data.planned_date_begin || null;
//      this.state.planned_date_end = data.planned_date_end || null;
//      this.state.user_ids = data.user_ids || [];
//      this.state.teamId = data.user_ids?.length
//        ? parseInt(data.user_ids[0])
//        : null;
//    }
//
//    if (this.state.teamId) {
//      try {
//        const users = await this.orm.call("res.users", "read", [
//          [this.state.teamId],
//          ["name"],
//        ]);
//        this.state.technicianName = users?.[0]?.name || null;
//      } catch {
//        this.state.technicianName = null;
//      }
//    }
//
//    sessionStorage.setItem("jobcardId", this.state.jobcardId);
//    sessionStorage.setItem("jobCardNumber", this.state.jobCardNumber);
//    sessionStorage.setItem("customerName", this.state.customerName);
//    sessionStorage.setItem("serviceDatetime", this.state.serviceDatetime || "");
//
//    try {
//      await this.updateJobCard();
//    } catch (err) {
//      console.error(err);
//    } finally {
//      this.hasSlotClicked = true;
//    }
//  }
//
//  async updateJobCard() {
//    const previousjobStateCode = this.state.job_card_state_code;
//    let jobStateCode = this.state.job_card_state_code;
//
//    // Restrict update to specific states
//    if (
//      ![101, 107, 152,207, 156, 117, 132, 204, 133, 122, 134].includes(
//        parseInt(jobStateCode)
//      )
//    ) {
//      this.notification.add(
//        "⚠️ Only jobcards in Draft or Scheduled states can be updated.",
//        { type: "warning" }
//      );
//      return;
//    }
//
//    const noReassignStates = [204, 133, 134];
//    if (noReassignStates.includes(parseInt(jobStateCode))) {
//      this.notification.add(
//        "⚠️ Technician reassignment not allowed in this state.",
//        { type: "warning" }
//      );
//      return;
//    }
//
//    const targetCode =
//      Number(jobStateCode) === 101
//        ? 102
//        : Number(jobStateCode) === 107
//        ? 102
//        : Number(jobStateCode) === 117
//        ? 204
//        : Number(jobStateCode) === 132
//        ? 133
//        : Number(jobStateCode) === 122
//        ? 134
//        : Number(jobStateCode) === 152
//        ? 102
//        : Number(jobStateCode) === 156
//        ? 102
//        : Number(jobStateCode) === 207
//        ? 102
//        : jobStateCode;
//
//    console.log("🔍 Target Code:", targetCode);
//
//    // ✅ Use Hook to Fetch Task Stage
//    // await this.taskStageHook.fetchTaskStages(this.orm, targetCode);
//    await this.taskStageHook.fetchTaskStages(
//      this.orm,
//      targetCode,
//      this.state.jobcardId
//    );
//
//    const { stages, taskInfo, error } = this.taskStageHook.state;
//
//    if (error || !stages.length) {
//      this.notification.add(error || "❌ Task stage not found.", {
//        type: "danger",
//      });
//      return;
//    }
//
//    // ✅ Use first stage found
//    const taskStage = stages[0];
//    const stateTransition = {
//      job_state: taskStage.id,
//      job_card_state: taskStage.name,
//      job_card_state_code: taskStage.code,
//    };
//
//    console.log("✅ State Transition:", stateTransition);
//
//    const payload = {
//      jobcardId: this.state.jobcardId,
//      plannedDateBegin: this.state.planned_date_begin,
//      plannedDateEnd: this.state.planned_date_end,
//      technician_id: this.state.teamId || null,
//      ...stateTransition,
//    };
//
//    console.log("📦 Payload:", payload);
//
//    const jobcardIdInt = parseInt(payload.jobcardId, 10);
//    if (!jobcardIdInt) return;
//
//    try {
//      // await this.taskStageHook.fetchTaskStages(this.orm, jobcardIdInt);
//
//      // const { taskInfo, error } = this.taskStageHook.state;
//
//      // if (error || !taskInfo.length) {
//      //   this.notification.add(error || "❌ Task stage not found.", {
//      //     type: "danger",
//      //   });
//      //   return;
//      // }
//      const taskData = taskInfo;
//
//      console.log("taskdata", taskData);
//
//      // const [taskData] = await this.orm.searchRead(
//      //   "project.task",
//      //   [["id", "=", jobcardIdInt]],
//      //   ["second_visit_technician_bool", "technician_first_visit_id"]
//      // );
//
//      const isSecondVisit = taskData?.second_visit_technician_bool || false;
//
//      const values = {
//        planned_date_begin: payload.plannedDateBegin,
//        planned_date_end: payload.plannedDateEnd,
//        job_card_state_code: targetCode,
//        job_state: payload.job_state,
//        job_card_state: payload.job_card_state,
//        technician_id: payload.technician_id,
//      };
//
//      if (!taskData?.technician_first_visit_id) {
//        values.technician_first_visit_id = payload.technician_id;
//      } else if (isSecondVisit) {
//        values.technician_second_visit_id = payload.technician_id;
//      }
//      // console.log("values for formview scheduling Button-->", values);
//
//      await this.orm.write("project.task", [jobcardIdInt], values);
//      this.notification.add(
//        `✅ Task updated successfully\nJobcard Number: ${
//          this.state.jobCardNumber || this.state.name
//        }\nTechnician: ${this.state.technicianName}`,
//        { type: "success" }
//      );
//
//      // this.notification.add(
//      //   `✅ Jobcard updated to '${payload.job_card_state}' successfully.`,
//      //   { type: "success" }
//      // );
//
//      const mrsRecords = await this.orm.searchRead(
//        "machine.repair.support",
//        [["task_id", "=", jobcardIdInt]],
//        ["id"]
//      );
//
//      if (mrsRecords?.length) {
//        const taskData2 = await this.orm.read(
//          "project.task",
//          [jobcardIdInt],
//          ["team_id"]
//        );
//        const taskTeamId = taskData2?.[0]?.team_id?.[0] || null;
//
//        const MRSvalues = {
//          task_id: payload.jobcardId,
//          service_request_state: payload.job_card_state,
//          service_request_state_code: payload.job_card_state_code,
//          user_id: payload.technician_id,
//          team_id: taskTeamId,
//          call_request_appointment_date: this.state.serviceDatetime || null,
//          technician_appointment_date: payload.plannedDateBegin || null,
//        };
//        console.log("MRSvalues", MRSvalues);
//
//        const mrsIds = mrsRecords.map((r) => r.id).filter((id) => !isNaN(id));
//        if (mrsIds.length) {
//          await this.orm.write("machine.repair.support", mrsIds, MRSvalues);
//        }
//      }
//    } catch (err) {
//      console.error(err);
//      this.notification.add("❌ Failed to update jobcard.", {
//        type: "danger",
//      });
//    }
//    setTimeout(() => {
//      const nextArrows = document.querySelectorAll(".oi.oi-arrow-right");
//      nextArrows.forEach((el) => el.click());
//      const previousArrows = document.querySelectorAll(".oi.oi-arrow-left");
//      previousArrows.forEach((el) => el.click());
//      sessionStorage.removeItem("lastJobcardId");
//    }, 2000);
//  }
//
//  highlightSlotCell(ev) {
//    const container = document.querySelector(".o_gantt_view") || document.body;
//    if (!container) return;
//
//    const overlay = document.createElement("div");
//    overlay.id = "slotHighlightOverlay";
//    Object.assign(overlay.style, {
//      position: "absolute",
//      borderRadius: "6px",
//      background: "rgba(255, 235, 59, 0.55)",
//      outline: "2px solid rgba(255, 193, 7, 0.9)",
//      pointerEvents: "none",
//      zIndex: "9999",
//      display: "flex",
//      alignItems: "center",
//      justifyContent: "center",
//      color: "#000",
//      fontWeight: "bold",
//      fontSize: "10px",
//      textAlign: "center",
//    });
//
//    container.addEventListener("click", (ev) => {
//      const cell = ev.target.closest("td[data-resource-id][data-date]");
//      if (!cell) return;
//
//      if (overlay.parentElement) overlay.parentElement.removeChild(overlay);
//      document.body.appendChild(overlay);
//
//      const widthPx = 140;
//      const heightPx = 45;
//
//      const top = ev.clientY;
//      const left = ev.clientX;
//
//      Object.assign(overlay.style, {
//        width: widthPx + "px",
//        height: heightPx + "px",
//        top: top + "px",
//        left: left + "px",
//      });
//
//      overlay.textContent = `Technician: ${this.state.technicianName || "N/A"}`;
//      setTimeout(() => overlay.remove(), 5000);
//    });
//  }
//}
//
//registry.category("actions").add("my_module.my_component", MyComponent);


import { Component, useState, useEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
export class MyComponent extends Component {
  static template = "MyComponent";

  setup() {
    this.env = useEnv();
    this.orm = useService("orm");
    this.actionService = useService("action");
    this.notification = useService("notification");

    const context = this.env.searchModel?._context || {};
    this.state = useState({
      jobcardId: context.active_id || null,
      hideJobcardList: context.hide_jobcard_list || false,
      jobCardNumber:
        context.job_card_number ||
        sessionStorage.getItem("jobCardNumber") ||
        "",
      customerName:
        context.customer_name || sessionStorage.getItem("customerName") || "",
      serviceDatetime:
        context.service_requested_datetime ||
        sessionStorage.getItem("serviceDatetime") ||
        "",
      planned_date_begin: context.planned_date_begin || "",
      planned_date_end: context.planned_date_end || "",
      job_card_state_code: context.job_card_state_code || "",
      job_card_state: context.job_card_state || "",
      job_state: context.job_state || "",
      user_ids: [],
      teamId: null,
      technicianName: "",
      service_requested_datetime_formatted: "",
      unitpulloutcheck: context.unit_pull_out_status_check || "",
      warehouseId: null,
      quatecraetedBy: context.quote_created_by || "",
    });
    console.log("this.state", this.state);

    if (this.state.serviceDatetime) {
      const d = new Date(this.state.serviceDatetime.replace(" ", "T"));
      d.setHours(d.getHours() + 3); // Adjust timezone
      const pad = (n) => n.toString().padStart(2, "0");
      this.state.service_requested_datetime_formatted = `${pad(
        d.getDate()
      )}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(
        d.getMinutes()
      )}:${pad(d.getSeconds())}`;
    }

    this.hasSlotClicked = false;

    if (this.env.bus) {
      useBus(this.env.bus, "toggle-jobcard-list", (ev) => {
        this.state.hideJobcardList = ev.detail.hideJobcardList;
      });

      useBus(this.env.bus, "slot-clicked", (event) => {
        if (!this.hasSlotClicked) {
          this.hasSlotClicked = true;
          this.updateSelectedJobCard(event.detail, true);

          // Highlight the clicked cell
          const cellEl = event.detail.domElement;
          if (cellEl) {
            this.highlightSlotCell(cellEl);
          }
        }
      });
    }
  }

  async updateSelectedJobCard(data, isSlot = false) {
    if (!data) return;
    const now = new Date();
    now.setHours(0, 0, 0, 0);

    // Validate slot date (cannot schedule past)
    if (isSlot && data.planned_date_begin) {
      const plannedBegin = new Date(data.planned_date_begin);
      const plannedEnd = data.planned_date_end
        ? new Date(data.planned_date_end)
        : null;

      if (plannedBegin < now || (plannedEnd && plannedEnd < now)) {
        this.notification.add(
          `⚠️ Scheduling Error: Jobcards cannot be assigned to past dates. Please select today or a future date.`,
          { type: "danger" }
        );
        this.hasSlotClicked = false;
        return;
      }
    }

    // Update job card info
    if (data.id && !data.planned_date_begin) {
      this.state.jobcardId = data.id;
      this.state.name = data.name || "";
      this.state.customerName = data.customer_name || "";
      this.state.planned_date_begin = null;
      this.state.planned_date_end = null;
      this.state.user_ids = [];
      this.state.teamId = null;
      this.state.technicianName = "";
    } else if (isSlot) {
      this.state.planned_date_begin = data.planned_date_begin || null;
      this.state.planned_date_end = data.planned_date_end || null;
      this.state.user_ids = data.user_ids || [];
      this.state.teamId = data.user_ids?.length
        ? parseInt(data.user_ids[0])
        : null;
    }
    if (this.state.teamId) {
      try {
        const users = await this.orm.call("res.users", "read", [
          [this.state.teamId],
          ["name", "property_warehouse_id"],
        ]);
        this.state.technicianName = users?.[0]?.name || null;
        this.state.warehouseId = users?.[0]?.property_warehouse_id[0] || null;
        console.log(" this.state.warehouseId", this.state.warehouseId);
      } catch {
        this.state.technicianName = null;
      }
    }

    // if (this.state.teamId) {
    //   try {
    //     const users = await this.orm.call("res.users", "read", [
    //       [this.state.teamId],
    //       ["name"],
    //     ]);
    //     this.state.technicianName = users?.[0]?.name || null;
    //   } catch {
    //     this.state.technicianName = null;
    //   }
    // } else {
    //   this.state.technicianName = null;
    // }

    sessionStorage.setItem("jobcardId", this.state.jobcardId);
    sessionStorage.setItem("jobCardNumber", this.state.jobCardNumber);
    sessionStorage.setItem("customerName", this.state.customerName);
    sessionStorage.setItem("serviceDatetime", this.state.serviceDatetime || "");

    try {
      await this.updateJobCard();
    } catch (err) {
      console.error(err);
    } finally {
      this.hasSlotClicked = false;
    }
  }

  async updateJobCard() {
    const previousjobStateCode = this.state.job_card_state_code;
    let jobStateCode = this.state.job_card_state_code;

    //Allow updates only for specific job states
    if (
      [
        103, 104, 105, 106, 108, 109, 110, 111, 113, 114, 115, 116, 118, 119,
        120, 121, 123, 125, 134, 204, 208,
      ].includes(parseInt(jobStateCode))
    ) {
      //   [(117, 127, 132, 204, 208, 133, 122, 134)].includes(
      //     parseInt(jobStateCode)
      //   )
      // )
      this.notification.add(
        "⚠️ Only jobcards in 'New', or 'Scheduled' states can be updated.",
        { type: "warning" }
      );
      return;
    }

    // Restrict technician reassignment for states 117, 132, 204, 133
    const noReassignStates = [204, 208, 133, 134]; // States where reassignment is not allowed
    if (noReassignStates.includes(parseInt(jobStateCode))) {
      this.notification.add(
        "⚠️ Technician reassignment is not allowed in this job state.",
        { type: "warning" }
      );
      return;
    }
    // const targetCode = Number(jobStateCode) === 117 ? 204 : jobStateCode;
    // console.log(targetCode);
    // / const mapping = {
    //       101: 102,
    //       102: 102,
    //       107: 102,
    //       117: 204,
    //       122: 134,
    //       132: 133,
    //       152: 102,
    //       156: 102,
    //       207: 208,
    //     };
    const targetCode =
      Number(jobStateCode) === 101
        ? 102
        : Number(jobStateCode) === 101
        ? 102
        : Number(jobStateCode) === 117
        ? 204
        : Number(jobStateCode) === 132
        ? 133
        : Number(jobStateCode) === 152
        ? 208
        : Number(jobStateCode) === 122
        ? 134
        : Number(jobStateCode) === 156
        ? 102
        : Number(jobStateCode) === 127 &&
          this.state.unitpulloutcheck === true &&
          this.stste.quatecraetedBy === "S"
        ? 204
        : Number(jobStateCode) === 207 &&
          this.state.unitpulloutcheck === true &&
          this.stste.quatecraetedBy === "T"
        ? 208
        : jobStateCode;

    console.log(targetCode);

    let taskStages = await this.orm.searchRead(
      "project.task.type",
      [["code", "=", String(targetCode)]],
      [("id", "code", "name")]
    );
    console.log("taskStages", taskStages);
    // Use the first record as your stateTransition
    const stateTransition = {
      job_state: taskStages[0].id,
      job_card_state: taskStages[0].name,
    };
    console.log("stateTransition:", stateTransition);

    // const warehouse = await this.orm.searchRead(
    //   "project.task",
    //   [["id", "=", parseInt(this.state.jobcardId)]],
    //   ["id", "name", "warehouse_id"]
    // );
    // console.log("warehouse", warehouse);
    try {
      const warehouse = await this.orm.searchRead(
        "project.task",
        [["id", "=", parseInt(this.state.jobcardId)]],
        ["id", "name", "warehouse_id"]
      );

      if (warehouse && warehouse.length > 0) {
        // Access the first element of the warehouse_id array
        const jobcardwarehouseId =
          warehouse[0].warehouse_id && warehouse[0].warehouse_id[0];
        console.log("warehouseId", jobcardwarehouseId);
      } else {
        console.log("No task found for the given jobcardId");
      }
    } catch (error) {
      console.error("Error fetching warehouse data:", error);
    }

    const payload = {
      jobcardId: this.state.jobcardId,
      plannedDateBegin: this.state.planned_date_begin,
      plannedDateEnd: this.state.planned_date_end,
      technician_id: this.state.teamId || null,
      job_card_state_code: targetCode,
      warehouse_id: this.state.warehouseId || null,
      // warehouse_id: this.state.warehouseId ? null : jobcardwarehouseId,
      ...stateTransition,
    };
    // this.hasSlotClicked = true;

    console.log("✅ Payload:", payload);
    const jobcardIdInt = parseInt(payload.jobcardId, 10);
    if (!jobcardIdInt) return;
    // this.highlightSlotCell();

    try {
      const [taskData] = await this.orm.searchRead(
        "project.task",
        [["id", "=", jobcardIdInt]],
        ["second_visit_technician_bool", "technician_first_visit_id"]
      );

      const isSecondVisit = taskData?.second_visit_technician_bool || false;

      console.log("Second Visit Bool:", isSecondVisit);

      const values = {
        planned_date_begin: payload.plannedDateBegin,
        planned_date_end: payload.plannedDateEnd,
        job_card_state_code: targetCode,
        job_state: payload.job_state,
        job_card_state: payload.job_card_state,
        technician_id: payload.technician_id,
        warehouse_id: payload.warehouse_id,
      };

      // if (!taskData?.technician_first_visit_id) {
      //   values.technician_first_visit_id = payload.technician_id;
      // }
      if (
        taskData.technician_first_visit_id !== null &&
        values.job_card_state_code === 102
      ) {
        values.technician_first_visit_id = payload.technician_id;
      } else if (taskData?.second_visit_technician_bool) {
        values.technician_second_visit_id = payload.technician_id;
      } else {
        console.log(
          "ℹ️ Technician assignment skipped (no eligible visit condition)."
        );
      }

      // this.highlightSlotCell();

      await this.orm.write("project.task", [jobcardIdInt], values);

      sessionStorage.setItem("lastJobcardId", payload.jobcardId);
      sessionStorage.setItem("plannedStart", payload.plannedDateBegin);

      this.notification.add(
        `✅ Task updated successfully\nJobcard Number: ${
          this.state.jobCardNumber || this.state.name
        }\nTechnician: ${this.state.technicianName}`,
        { type: "success" }
      );

      const mrsRecords = await this.orm.searchRead(
        "machine.repair.support",
        [["task_id", "=", jobcardIdInt]],
        ["id"]
      );

      if (mrsRecords?.length) {
        const taskData2 = await this.orm.read(
          "project.task",
          [jobcardIdInt],
          ["team_id"]
        );
        const taskTeamId = taskData2?.[0]?.team_id?.[0] || null;

        const valuesMRS = {
          task_id: payload.jobcardId,
          service_request_state: payload.job_card_state,
          service_request_state_code: payload.job_card_state_code,
          user_id: payload.technician_id,
          team_id: taskTeamId,
          call_request_appointment_date: this.state.serviceDatetime || null,
          technician_appointment_date: payload.plannedDateBegin || null,
        };

        const mrsIds = mrsRecords.map((r) => r.id).filter((id) => !isNaN(id));
        if (mrsIds.length) {
          await this.orm.write("machine.repair.support", mrsIds, valuesMRS);
        }
      }
    } catch (err) {
      this.notification.add(
        "Already job assigned this slot.Please choose some other slot",
        {
          type: "info",
        }
      );
      console.error(err);
    }

    setTimeout(() => {
      const nextArrows = document.querySelectorAll(".oi.oi-arrow-right");
      nextArrows.forEach((el) => el.click());
      const previousArrows = document.querySelectorAll(".oi.oi-arrow-left");
      previousArrows.forEach((el) => el.click());
      sessionStorage.removeItem("lastJobcardId");
    }, 2000);
  }

  highlightSlotCell() {
    const container =
      document.querySelector(
        ".o_gantt_view, .o_gantt, .o_content, .o_view_controller"
      ) || document.body;

    if (!container) return;

    let overlay = document.createElement("div");
    overlay.id = "slotHighlightOverlay";
    Object.assign(overlay.style, {
      position: "absolute",
      borderRadius: "6px",
      background: "rgba(255, 235, 59, 0.55)",
      outline: "2px solid rgba(255, 193, 7, 0.9)",
      pointerEvents: "none",
      zIndex: "9999",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#000",
      fontWeight: "bold",
      fontSize: "10px",
      textAlign: "center",
    });

    container.addEventListener("click", (ev) => {
      const cell = ev.target.closest(
        "td[data-resource-id][data-date], td[data-date], .o_gantt_cell[data-date]"
      );
      if (!cell) return;

      if (overlay.parentElement) overlay.parentElement.removeChild(overlay);
      document.body.appendChild(overlay);

      const widthPx = 140;
      const heightPx = 45;

      const top = ev.clientY;
      const left = ev.clientX;

      Object.assign(overlay.style, {
        width: widthPx + "px",
        height: heightPx + "px",
        top: top + "px",
        left: left + "px",
      });
      // overlay.textContent = `Jobcard: ${this.state.name || "N/A"}`;
      overlay.textContent = `Technician: ${this.state.technicianName || "N/A"}`;

      setTimeout(() => overlay.remove(), 5000);
    });
  }
}

registry.category("components").add("MyComponent", MyComponent);

