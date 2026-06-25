/** @odoo-module **/

import { Component, useState, useEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";

export class MyComponent extends Component {
  static template = "MyComponent";

  setup() {
    this.env = useEnv();
    this.orm = useService("orm");
    this.actionService = useService("action");
    this.notification = useService("notification");
    this.dialog = useService("dialog");
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
      balanceAmountreceivedBool: context.balance_amount_received_bool || "", // added 24/01/2026
      serviceWarrantyId: context.service_warranty_id || "", // added 24/01/2026
      warehouseId: null,
      quatecraetedBy: context.quote_created_by || "",
      last_rescheduled_status_code: context.last_rescheduled_status_code || "",
      dealer_id: context.dealer_id || "",
    });
    console.log("this.state", this.state);

    if (this.state.serviceDatetime) {
      const d = new Date(this.state.serviceDatetime.replace(" ", "T"));
      d.setHours(d.getHours() + 3); // Adjust timezone
      const pad = (n) => n.toString().padStart(2, "0");
      this.state.service_requested_datetime_formatted = `${pad(
        d.getDate(),
      )}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(
        d.getMinutes(),
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
          { type: "danger" },
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
          ["name", "property_warehouse_id", "warehouse_category_user_line_ids"],
        ]);
        this.state.technicianName = users?.[0]?.name || null;
        this.state.warehouseId = users?.[0]?.property_warehouse_id[0] || null;
        this.state.warehouseLineId =
          users?.[0]?.warehouse_category_user_line_ids || null;
        console.log(" this.state.warehouseId", this.state.warehouseId);
      } catch {
        this.state.technicianName = null;
      }
    }
    // // FEB 05 2026  Modified by Vengatesh Component
    // const warehouseId = this.state.warehouseId;
    // const warehouses = await this.orm.searchRead(
    //   "stock.warehouse",
    //   [["id", "=", warehouseId]],
    //   ["id", "name", "product_category_ids"],
    // );

    // console.log("warehouses----------------", warehouses);
    // const id = this.state.jobcardId;

    // const categoryData = await this.orm.searchRead(
    //   "project.task",
    //   [["id", "=", id]],
    //   ["product_category_id"],
    // );
    // console.log("this.state.selectedJobCardId", categoryData);
    // const warehouse = warehouses[0];
    // if (!warehouse) {
    //   return this.notification.add(
    //     _t("Warehouse not found for the selected technician."),
    //     { type: "danger" },
    //   );
    // }
    // const task = categoryData[0];

    // // 3️⃣ Normalize IDs
    // const taskCategoryId = task.product_category_id[0]; // Many2one → ID
    // const warehouseCategoryIds = warehouse.product_category_ids; // Many2many → [ids]
    // const isCategoryMatched = warehouseCategoryIds.includes(taskCategoryId);
    // // 5️⃣ Act on condition
    // // if (!isCategoryMatched) {
    // //   return this.notification.add(
    // //     `Job Card category is not allowed for warehouse: ${warehouses.name}`,
    // //     { type: "danger" },
    // //   );
    // // }
    // if (!isCategoryMatched) {
    //   this.dialog.add(ConfirmationDialog, {
    //     title: "Category Mismatch",
    //     body: _t(
    //       "Job Card category is not allowed for warehouse: %s",
    //       warehouse.name,
    //     ),

    //     confirmClass: "btn-primary",
    //     confirmLabel: _t("Confirm"),
    //     cancelLabel: _t("Cancel"),
    //     cancel: () => { },
    //   });
    //   this.hasSlotClicked = false;
    //   return;
    // }

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

    //Adden on Raj - 12-03-2026
    const warehouse = await this.workCenterlocationMatch();

    //27-02-2025
    //    const warehouse = await this.resUserlineMatchJCPC();

    /* -------------------------------------------------
     *  SLOT + WAREHOUSE SELECTION FEB 17 205
     * ------------------------------------------------- */
    // const warehouse = await this.onSlotClick();

    // Stop flow if no warehouse is selected
    if (!warehouse) {
      this.hasSlotClicked = false;
      console.log("Warehouse not selected, stopping update.");
      return; // ✅ stops here
    }

    sessionStorage.setItem("jobcardId", this.state.jobcardId);
    sessionStorage.setItem("jobCardNumber", this.state.jobCardNumber);
    sessionStorage.setItem("customerName", this.state.customerName);
    sessionStorage.setItem("serviceDatetime", this.state.serviceDatetime || "");
    sessionStorage.setItem("dealer_id", this.state.dealer_id || "");
    try {
      await this.updateJobCard();
    } catch (err) {
      console.error(err);
    } finally {
      this.hasSlotClicked = false;
    }
  }

  // Mar 11 2026 Vengateshwaran S
  async workCenterlocationMatch() {
    // Mar 11 2026 Vengateshwaran S
    const stopFlow = (msg) => {
      this.hasSlotClicked = false;
      if (msg && this.notification) {
        this.notification.add(msg, { type: "info" });
      }
      return null;
    };

    this.hasSlotClicked = true;

    const taskId = this.state.jobcardId;

    /* 1️⃣ Fetch task */
    const task = await this._getTask(taskId);
    if (!task) return;

    const categoryId = task.product_category_id?.[0];
    const categoryName = task.product_category_id?.[1];
    const workCenterId = task.work_center_id?.[0] || null;

    let warehouse = null;
    let lineIds = this.state.warehouseLineId;
    let technicianRequired = false;

    /* 2️⃣ CHECK WORK CENTER LOCATION CONDITION */
    if (workCenterId) {
      // const workCenterLocation = await this.orm.searchRead(
      //   "work.center.location",
      //   [
      //     ["id", "=", workCenterId],
      //     ["technician_warehouse_required_bool", "=", true],
      //   ],
      //   ["id"],
      // );
      const workCenterLocation = await this.orm.searchRead(
        "work.center.location",
        [["id", "=", workCenterId]],
        ["technician_warehouse_required_bool"],
      );

      // if (!workCenterLocation.length) {
      //   return stopFlow(
      //     "Technician warehouse is not required for this Work Center.",
      //   );
      // }
      if (workCenterLocation.length) {
        technicianRequired =
          workCenterLocation[0].technician_warehouse_required_bool;
      }
    }
    if (technicianRequired === true) {
      if (lineIds.length) {
        /* 3️⃣ Try from res.users.line */
        const lines = await this.orm.searchRead(
          "res.users.line",
          [
            ["id", "in", lineIds],
            ["product_category_line_id", "=", categoryId],
          ],
          ["warehouse_line_id"],
        );

        if (lines.length && lines[0].warehouse_line_id) {
          warehouse = lines[0].warehouse_line_id[0];
        }
        console.log("lineIds", warehouse);
      }
      console.log("lineIds", lineIds);

      /* 4️⃣ FALLBACK: work center + default + category */
      // if (!warehouse) {
      //   console.loh("warehouse-------------------------", warehouse);
      if (!workCenterId)
        return stopFlow("Work Center is not configured for this Job Card.");
      // let warehousedata = await this._findWarehouse([
      //   // ["work_center_id", "=", workCenterId],
      //   // ["region_default_warehouse_bool", "=", true],//-- no need
      //   ["product_category_ids", "in", [categoryId]],
      //   ["warehouse_type", "=", "technician_warehouse"],
      // ]);
      let warehousedata = await this.orm.searchRead(
        "stock.warehouse",
        [
          ["id", "=", warehouse],
          ["product_category_ids", "in", [categoryId]],
          ["warehouse_type", "=", "technician_warehouse"],
        ],
        ["id", "name", "warehouse_type"],
      );
      console.log("warehousedata ----------------------------", warehousedata);

      // warehouse = warehousedata?.id;
      warehouse = warehousedata?.[0]?.id;
      console.log("warehouse", warehouse);
    } else {
      if (!warehouse) {
        if (!workCenterId) {
          return stopFlow("Work Center is not configured for this Job Card.");
        }

        // let warehousedata = await this._findWarehouse([
        //   ["work_center_id", "=", workCenterId],
        //   //default warehouse - need
        //   ["region_default_warehouse_bool", "=", true],
        //   ["product_category_ids", "in", [categoryId]],
        //   ["warehouse_type", "=", "main_warehouse"], // changed here
        // ]);

        let warehousedata = await this.orm.searchRead(
          "stock.warehouse",
          [
            //["work_center_id", "=", workCenterId],
            ["work_center_ids", "in", [workCenterId]],
            //default warehouse - need
            ["region_default_warehouse_bool", "=", true],
            ["product_category_ids", "in", [categoryId]],
            ["warehouse_type", "=", "main_warehouse"], // changed here
          ],
          ["id", "name", "warehouse_type"],
        );

        // warehouse = warehousedata?.id;
        console.log(
          "warehousedata technician required false ----------------------------",
          warehousedata,
        );
        warehouse = warehousedata?.[0]?.id;
        console.log(
          "warehouse  technician required false ----------------------",
          warehouse,
        );
      }
    }

    if (!warehouse) {
      let message = "";

      if (technicianRequired) {
        message = markup(
          _t(
            "Technician warehouse is not available for the technician <b>%s</b> to the Product category <b>%s</b>.",
            this.state.technicianName,
            categoryName,
          ),
        );
      } else {
        message = markup(
          _t(
            "Main warehouse is not available for the technician <b>%s</b> to the Product category <b>%s</b>.",
            this.state.technicianName,
            categoryName,
          ),
        );
      }

      this.dialog.add(ConfirmationDialog, {
        title: _t("Validation Error"),
        body: message,
      });
      // this.dialog.add(ConfirmationDialog, {
      //   title: _t("ValidationError"),
      //   // body: _t("No matching warehouse found for this Job Card.{taskId}"),
      //   body: _t(
      //     // "No matching warehouse found for this Job Card: %s",
      //     // this.state.jobCardNumber,
      //     "Technician warehouse is not available to the technician: %s",
      //     categoryName,
      //     this.state.technicianName,

      //     "Main warehouse is not available to the technician : %s",
      //     categoryName,
      //     this.state.technicianName,
      //   ),
      // });
      return;
      // return stopFlow("No matching warehouse found for this Job Card.");
    }

    /* ✅ SUCCESS */
    this.matchedWarehouseId = warehouse;
    console.log("Final resUserlineMatchJCPC Warehouse:", warehouse);

    this.hasSlotClicked = false;
    return warehouse;
  }

  //Feb 27-2025 VENGATESHWARAN S
  async resUserlineMatchJCPC() {
    //27-02-2025
    const stopFlow = (msg) => {
      this.hasSlotClicked = false;
      // if (msg) this._info(msg);
      if (msg && this.notification) {
        this.notification.add(msg, { type: "info" });
      }
      return null;
    };
    this.hasSlotClicked = true; // mark as clicked at the start
    const taskId = this.state.jobcardId;

    /* 1️⃣ Fetch task once */
    const task = await this._getTask(taskId);
    if (!task) return;
    //  stopFlow("Job Card not found.");

    const categoryId = task.product_category_id?.[0];
    const workCenterId = task.work_center_id?.[0] || null;

    let warehouse = null;
    let lineIds = this.state.warehouseLineId;

    //     const lines = await this.orm.searchRead(
    //     "res.users.line",
    //     [
    //         ["id", "in", lineIds],
    //         ["product_category_line_id", "=", categoryId]
    //     ],
    //     ["warehouse_line_id"]
    // );

    // const lines = await this.orm.read("res.users.line", lineIds, [
    //   "product_category_line_id",
    //   "warehouse_line_id",
    // ]);
    // console.log("lineIds", lines);
    // const matchedLine = lines.find(
    //   (line) => line.product_category_line_id?.[0] === categoryId,
    // );

    // if (matchedLine?.warehouse_line_id) {
    //   warehouse = matchedLine.warehouse_line_id[0];
    //   console.log("warehouse", warehouse);
    // }
    /* 1️⃣ Try from res.users.line */
    if (lineIds.length) {
      const lines = await this.orm.searchRead(
        "res.users.line",
        [
          ["id", "in", lineIds],
          ["product_category_line_id", "=", categoryId],
        ],
        ["warehouse_line_id"],
      );

      if (lines.length && lines[0].warehouse_line_id) {
        warehouse = lines[0].warehouse_line_id[0];
      }
    }
    /*  FALLBACK: work_center + default + category */
    if (!warehouse) {
      if (!workCenterId)
        return stopFlow("Work Center is not configured for this Job Card.");

      let warehousedata = await this._findWarehouse([
        ["work_center_id", "=", workCenterId],
        ["default_work_center_bool", "=", true],
        ["product_category_ids", "in", [categoryId]],
      ]);
      warehouse = warehousedata?.id;
      console.log("warehouse---------------", warehouse);
    }
    if (!warehouse) {
      return stopFlow("No matching warehouse found for this Job Card.");
    }
    /* ✅ SUCCESS */
    this.matchedWarehouseId = warehouse;
    console.log("Final resUserlineMatchJCPC Warehouse:", warehouse);

    this.hasSlotClicked = false;
    return warehouse; // reset after success
  }

  //Feb 27-2025 VENGATESHWARAN S
  async _getTask(taskId) {
    const [task] = await this.orm.searchRead(
      "project.task",
      [["id", "=", taskId]],
      ["work_center_id", "product_category_id"],
    );

    if (!task?.product_category_id) {
      this._error(_t("Product Category is not configured for the Job Card."));
      return null;
    }

    return task;
  }

  //Added by Raj - 12-03-2026
  async _findWarehouse(domain) {
    const res = await this.orm.searchRead("stock.warehouse", domain, [
      "id",
      "name",
      "warehouse_type", //workCenterlocationMatch
      "product_category_ids",
      "work_center_id",
    ]);
    console.log("warehousedata", res);
    return res.length ? res[0] : null;
  }

  // //Feb 27-2025 VENGATESHWARAN S
  //  async _findWarehouse(domain) {
  //    const res = await this.orm.searchRead("stock.warehouse", domain, [
  //      "id",
  //      "name",
  //    ]);
  //    return res.length ? res[0] : null;
  //  }

  _error(message) {
    this.notification.add(message, { type: "danger" });
    this.hasSlotClicked = false;
  }

  // async updateJobCard() {
  //   const previousjobStateCode = this.state.job_card_state_code;
  //   let jobStateCode = this.state.job_card_state_code;

  //   //Allow updates only for specific job states
  //   if (
  //     [
  //       103, 104, 105, 106, 108, 109, 110, 111, 113, 114, 115, 116, 118, 119,
  //       120, 121, 123, 125, 134, 204, 208,
  //     ].includes(parseInt(jobStateCode))
  //   ) {
  //     //   [(117, 127, 132, 204, 208, 133, 122, 134)].includes(
  //     //     parseInt(jobStateCode)
  //     //   )
  //     // )
  //     this.notification.add(
  //       "⚠️ Only jobcards in 'New', or 'Scheduled' states can be updated.",
  //       { type: "warning" }
  //     );
  //     return;
  //   }

  //   // Restrict technician reassignment for states 117, 132, 204, 133
  //   const noReassignStates = [204, 208, 134]; // States where reassignment is not allowed
  //   if (noReassignStates.includes(parseInt(jobStateCode))) {
  //     this.notification.add(
  //       "⚠️ Technician reassignment is not allowed in this job state.",
  //       { type: "warning" }
  //     );
  //     return;
  //   }
  //   // const targetCode = Number(jobStateCode) === 117 ? 204 : jobStateCode;
  //   // console.log(targetCode);
  //   // / const mapping = {
  //   //       101: 102,
  //   //       102: 102,
  //   //       107: 102,
  //   //       117: 204,
  //   //       122: 134,
  //   //       132: 133,
  //   //       152: 102,
  //   //       156: 102,
  //   //       207: 208,
  //   //     };
  //   // const targetCode =
  //   //   Number(jobStateCode) === 101
  //   //     ? 102
  //   //     : Number(jobStateCode) === 101
  //   //     ? 102
  //   //     : Number(jobStateCode) === 117
  //   //     ? 204
  //   //     : Number(jobStateCode) === 132
  //   //     ? 133
  //   //     : Number(jobStateCode) === 152
  //   //     ? 208
  //   //     : Number(jobStateCode) === 122
  //   //     ? 134
  //   //     : Number(jobStateCode) === 156
  //   //     ? 102
  //   //     : Number(jobStateCode) === 127 &&
  //   //       this.state.unitpulloutcheck === true &&
  //   //       this.stste.quatecraetedBy === "S"
  //   //     ? 204
  //   //     : Number(jobStateCode) === 207 &&
  //   //       this.state.unitpulloutcheck === true &&
  //   //       this.stste.quatecraetedBy === "T"
  //   //     ? 208
  //   //     : jobStateCode;

  //   // let taskStages = await this.orm.searchRead(
  //   //   "project.task.type",
  //   //   [["code", "=", String(jobStateCode)]],
  //   //   [("id", "code", "name", "dynamic_job_state_code")]
  //   // );
  //   // const stageState = await this.orm.searchRead(
  //   //   "project.task.type",
  //   //   [["code", "=", taskStages[0].dynamic_job_state_code]],
  //   //   ["id", "code", "name"]
  //   // );
  //   // // Use the first record as your stateTransition
  //   // const stateTransition = {
  //   //   job_card_state_code: parseInt(taskStages[0].dynamic_job_state_code),
  //   //   job_state: stageState[0].id,
  //   //   job_card_state: stageState[0].name,
  //   // };
  //   // console.log("stateTransition:", stateTransition);

  //   //08/01/2026 in my componet
  //   let lastRescheduledStatusCode = this.state.last_rescheduled_status_code;
  //   console.log("lastRescheduledStatusCode", lastRescheduledStatusCode);

  //   let stateTransition = {}; // ✅ declare once

  //   if (lastRescheduledStatusCode) {
  //     const stageLastResult = await this.orm.searchRead(
  //       "project.task.type",
  //       [["code", "=", String(lastRescheduledStatusCode)]],
  //       ["id", "code", "name"]
  //     );

  //     if (stageLastResult.length) {
  //       stateTransition = {
  //         job_card_state_code: Number(stageLastResult[0].code),
  //         job_state: stageLastResult[0].id,
  //         job_card_state: stageLastResult[0].name,
  //         last_rescheduled_status_code: Number(lastRescheduledStatusCode),
  //       };
  //     }
  //   } else {
  //     const taskStages = await this.orm.searchRead(
  //       "project.task.type",
  //       [["code", "=", String(jobStateCode)]],
  //       ["id", "code", "name", "dynamic_job_state_code"]
  //     );

  //     if (!taskStages.length || !taskStages[0].dynamic_job_state_code) {
  //       return; // ❗ nothing to process safely
  //     }

  //     const stageState = await this.orm.searchRead(
  //       "project.task.type",
  //       [["code", "=", String(taskStages[0].dynamic_job_state_code)]],
  //       ["id", "code", "name", "scheduling_status_bool"]
  //     );

  //     if (!stageState.length) {
  //       return;
  //     }

  //     stateTransition = {
  //       job_card_state_code: Number(taskStages[0].dynamic_job_state_code),
  //       job_state: stageState[0].id,
  //       job_card_state: stageState[0].name,
  //     };

  //     // 🔹 update ONLY when scheduling is true
  //     if (stageState[0].scheduling_status_bool === true) {
  //       stateTransition.last_rescheduled_status_code = Number(
  //         stageState[0].code
  //       );
  //     }
  //   }

  //   // ✅ Use stateTransition safely here
  //   console.log("Final stateTransition", stateTransition);

  //   // const warehouse = await this.orm.searchRead(
  //   //   "project.task",
  //   //   [["id", "=", parseInt(this.state.jobcardId)]],
  //   //   ["id", "name", "warehouse_id"]
  //   // );
  //   // console.log("warehouse", warehouse);
  //   try {
  //     const warehouse = await this.orm.searchRead(
  //       "project.task",
  //       [["id", "=", parseInt(this.state.jobcardId)]],
  //       ["id", "name", "warehouse_id"]
  //     );

  //     if (warehouse && warehouse.length > 0) {
  //       // Access the first element of the warehouse_id array
  //       const jobcardwarehouseId =
  //         warehouse[0].warehouse_id && warehouse[0].warehouse_id[0];
  //       console.log("warehouseId", jobcardwarehouseId);
  //     } else {
  //       console.log("No task found for the given jobcardId");
  //     }
  //   } catch (error) {
  //     console.error("Error fetching warehouse data:", error);
  //   }

  //   const payload = {
  //     jobcardId: this.state.jobcardId,
  //     plannedDateBegin: this.state.planned_date_begin,
  //     plannedDateEnd: this.state.planned_date_end,
  //     technician_id: this.state.teamId || null,
  //     // job_card_state_code: targetCode,
  //     warehouse_id: this.state.warehouseId || null,
  //     // warehouse_id: this.state.warehouseId ? null : jobcardwarehouseId,
  //     ...stateTransition,
  //   };
  //   // this.hasSlotClicked = true;

  //   console.log("✅ Payload:", payload);
  //   const jobcardIdInt = parseInt(payload.jobcardId, 10);
  //   if (!jobcardIdInt) return;
  //   // this.highlightSlotCell();

  //   try {
  //     const [taskData] = await this.orm.searchRead(
  //       "project.task",
  //       [["id", "=", jobcardIdInt]],
  //       ["second_visit_technician_bool", "technician_first_visit_id"]
  //     );

  //     const isSecondVisit = taskData?.second_visit_technician_bool || false;

  //     console.log("Second Visit Bool:", isSecondVisit);

  //     const values = {
  //       planned_date_begin: payload.plannedDateBegin,
  //       planned_date_end: payload.plannedDateEnd,
  //       job_card_state_code: payload.job_card_state_code,
  //       job_state: payload.job_state,
  //       job_card_state: payload.job_card_state,
  //       technician_id: payload.technician_id,
  //       warehouse_id: payload.warehouse_id,
  //       last_rescheduled_status_code:
  //         payload.last_rescheduled_status_code || ""
  //     };

  //     // if (!taskData?.technician_first_visit_id) {
  //     //   values.technician_first_visit_id = payload.technician_id;
  //     // }
  //     if (
  //       taskData.technician_first_visit_id !== null &&
  //       values.job_card_state_code === 102
  //     ) {
  //       values.technician_first_visit_id = payload.technician_id;
  //     } else if (taskData?.second_visit_technician_bool) {
  //       values.technician_second_visit_id = payload.technician_id;
  //     } else {
  //       console.log(
  //         "ℹ️ Technician assignment skipped (no eligible visit condition)."
  //       );
  //     }

  //     // this.highlightSlotCell();

  //     await this.orm.write("project.task", [jobcardIdInt], values);

  //     sessionStorage.setItem("lastJobcardId", payload.jobcardId);
  //     sessionStorage.setItem("plannedStart", payload.plannedDateBegin);

  //     this.notification.add(
  //       `✅ Task updated successfully\nJobcard Number: ${
  //         this.state.jobCardNumber || this.state.name
  //       }\nTechnician: ${this.state.technicianName}`,
  //       { type: "success" }
  //     );

  //     const mrsRecords = await this.orm.searchRead(
  //       "machine.repair.support",
  //       [["task_id", "=", jobcardIdInt]],
  //       ["id"]
  //     );

  //     if (mrsRecords?.length) {
  //       const taskData2 = await this.orm.read(
  //         "project.task",
  //         [jobcardIdInt],
  //         ["team_id"]
  //       );
  //       const taskTeamId = taskData2?.[0]?.team_id?.[0] || null;

  //       const valuesMRS = {
  //         task_id: payload.jobcardId,
  //         service_request_state: payload.job_card_state,
  //         service_request_state_code: payload.job_card_state_code,
  //         user_id: payload.technician_id,
  //         team_id: taskTeamId,
  //         call_request_appointment_date: this.state.serviceDatetime || null,
  //         technician_appointment_date: payload.plannedDateBegin || null,
  //       };

  //       const mrsIds = mrsRecords.map((r) => r.id).filter((id) => !isNaN(id));
  //       if (mrsIds.length) {
  //         await this.orm.write("machine.repair.support", mrsIds, valuesMRS);
  //       }
  //     }
  //   } catch (err) {
  //     this.notification.add(
  //       "Already job assigned this slot.Please choose some other slot",
  //       {
  //         type: "info",
  //       }
  //     );
  //     console.error(err);
  //   }

  //   setTimeout(() => {
  //     const nextArrows = document.querySelectorAll(".oi.oi-arrow-right");
  //     nextArrows.forEach((el) => el.click());
  //     const previousArrows = document.querySelectorAll(".oi.oi-arrow-left");
  //     previousArrows.forEach((el) => el.click());
  //     sessionStorage.removeItem("lastJobcardId");
  //   }, 2000);
  // }

  // ======================================================================================
  // async updateJobCard() {
  //   // 24/01/2026
  //   // 26-01-2026 Commented by Venkateswaran
  //   const previousjobStateCode = this.state.job_card_state_code;
  //   let jobStateCode = this.state.job_card_state_code;

  //   //Allow updates only for specific job states
  //   if (
  //     [
  //       103, 104, 105, 106, 108, 109, 110, 111, 113, 114, 115, 116, 118, 119,
  //       120, 121, 123, 125, 134, 204, 208,
  //     ].includes(parseInt(jobStateCode))
  //   ) {
  //     //   [(117, 127, 132, 204, 208, 133, 122, 134)].includes(
  //     //     parseInt(jobStateCode)
  //     //   )
  //     // )
  //     this.notification.add(
  //       "⚠️ Only jobcards in 'New', or 'Scheduled' states can be updated.",
  //       { type: "warning" },
  //     );
  //     return;
  //   }

  //   // Restrict technician reassignment for states 117, 132, 204, 133
  //   const noReassignStates = [204, 208, 133, 134]; // States where reassignment is not allowed
  //   if (noReassignStates.includes(parseInt(jobStateCode))) {
  //     this.notification.add(
  //       "⚠️ Technician reassignment is not allowed in this job state.",
  //       { type: "warning" },
  //     );
  //     return;
  //   }
  //   // const targetCode = Number(jobStateCode) === 117 ? 204 : jobStateCode;
  //   // console.log(targetCode);
  //   // / const mapping = {
  //   //       101: 102,
  //   //       102: 102,
  //   //       107: 102,
  //   //       117: 204,
  //   //       122: 134,
  //   //       132: 133,
  //   //       152: 102,
  //   //       156: 102,
  //   //       207: 208,
  //   //     };
  //   // const targetCode =
  //   //   Number(jobStateCode) === 101
  //   //     ? 102
  //   //     : Number(jobStateCode) === 101
  //   //     ? 102
  //   //     : Number(jobStateCode) === 117
  //   //     ? 204
  //   //     : Number(jobStateCode) === 132
  //   //     ? 133
  //   //     : Number(jobStateCode) === 152
  //   //     ? 208
  //   //     : Number(jobStateCode) === 122
  //   //     ? 134
  //   //     : Number(jobStateCode) === 156
  //   //     ? 102
  //   //     : Number(jobStateCode) === 127 &&
  //   //       this.state.unitpulloutcheck === true &&
  //   //       this.stste.quatecraetedBy === "S"
  //   //     ? 204
  //   //     : Number(jobStateCode) === 207 &&
  //   //       this.state.unitpulloutcheck === true &&
  //   //       this.stste.quatecraetedBy === "T"
  //   //     ? 208
  //   //     : jobStateCode;

  //   //   let taskStages = await this.orm.searchRead(
  //   //     "project.task.type",
  //   //     [["code", "=", String(jobStateCode)]],
  //   //     [("id", "code", "name", "dynamic_job_state_code")],
  //   //   );
  //   //   const stageState = await this.orm.searchRead(
  //   //     "project.task.type",
  //   //     [["code", "=", taskStages[0].dynamic_job_state_code]],
  //   //     ["id", "code", "name"],
  //   //   );
  //   //   // Use the first record as your stateTransition
  //   //   const stateTransition = {
  //   //     job_card_state_code: parseInt(taskStages[0].dynamic_job_state_code),
  //   //     job_state: stageState[0].id,
  //   //     job_card_state: stageState[0].name,
  //   //   };
  //   //   console.log("stateTransition:", stateTransition);
  //   // }

  //   let warrantyId = this.state.serviceWarrantyId;
  //   // added 24/01/2026
  //   let warrantyData = await this.orm.read(
  //     "service.warranty",
  //     [warrantyId],
  //     ["warranty_applicable_bool"],
  //   );
  //   console.log("warrantyData", warrantyData);
  //   const warrantyApplicable = warrantyData?.length
  //     ? warrantyData[0].warranty_applicable_bool
  //     : false;
  //   console.log("warrantyApplicable", warrantyApplicable);

  //   let isUnitPullOutStatusCheck = this.state.unitpulloutcheck;
  //   let balanceAmountreceivedBool = this.state.balanceAmountreceivedBool;
  //   console.log(
  //     "isUnitPullOutStatusCheck=============",
  //     isUnitPullOutStatusCheck,
  //   );
  //   console.log("balanceAmountreceivedBool", balanceAmountreceivedBool);

  //   let stateTransition = null;
  //   if (
  //     // added 24/01/2026
  //     warrantyApplicable === false &&
  //     // jobStateCode === 127 &&
  //     Number(jobStateCode) === 127 &&
  //     isUnitPullOutStatusCheck === true &&
  //     balanceAmountreceivedBool === true
  //   ) {
  //     const forcedStage = await this.orm.searchRead(
  //       "project.task.type",
  //       [["code", "=", 204]],
  //       ["id", "code", "name"],
  //     );

  //     if (forcedStage.length) {
  //       stateTransition = {
  //         job_card_state_code: parseInt(forcedStage[0].code),
  //         job_state: forcedStage[0].id,
  //         job_card_state: forcedStage[0].name,
  //       };

  //       // Object.assign(this.state, stateTransition);
  //       console.log("stateTransition 204:", stateTransition);
  //     }
  //   } else {
  //     const taskStages = await this.orm.searchRead(
  //       "project.task.type",
  //       [["code", "=", jobStateCode]],
  //       ["id", "code", "name", "dynamic_job_state_code"],
  //     );

  //     if (taskStages.length) {
  //       const stageState = await this.orm.searchRead(
  //         "project.task.type",
  //         [["code", "=", taskStages[0].dynamic_job_state_code]],
  //         ["id", "code", "name"],
  //       );

  //       if (stageState.length) {
  //         stateTransition = {
  //           job_card_state_code: parseInt(taskStages[0].dynamic_job_state_code),
  //           job_state: stageState[0].id,
  //           job_card_state: stageState[0].name,
  //         };

  //         console.log("stateTransition:", stateTransition);
  //       }
  //     }
  //   }

  //   // const warehouse = await this.orm.searchRead(
  //   //   "project.task",
  //   //   [["id", "=", parseInt(this.state.jobcardId)]],
  //   //   ["id", "name", "warehouse_id"]
  //   // );
  //   // console.log("warehouse", warehouse);
  //   try {
  //     const warehouse = await this.orm.searchRead(
  //       "project.task",
  //       [["id", "=", parseInt(this.state.jobcardId)]],
  //       ["id", "name", "warehouse_id"],
  //     );

  //     if (warehouse && warehouse.length > 0) {
  //       // Access the first element of the warehouse_id array
  //       const jobcardwarehouseId =
  //         warehouse[0].warehouse_id && warehouse[0].warehouse_id[0];
  //       console.log("warehouseId", jobcardwarehouseId);
  //     } else {
  //       console.log("No task found for the given jobcardId");
  //     }
  //   } catch (error) {
  //     console.error("Error fetching warehouse data:", error);
  //   }

  //   const payload = {
  //     jobcardId: this.state.jobcardId,
  //     plannedDateBegin: this.state.planned_date_begin,
  //     plannedDateEnd: this.state.planned_date_end,
  //     technician_id: this.state.teamId || null,
  //     // job_card_state_code: targetCode,
  //     warehouse_id: this.state.warehouseId || null,
  //     // warehouse_id: this.state.warehouseId ? null : jobcardwarehouseId,
  //     ...stateTransition,
  //   };
  //   // this.hasSlotClicked = true;

  //   console.log("✅ Payload:", payload);
  //   const jobcardIdInt = parseInt(payload.jobcardId, 10);
  //   if (!jobcardIdInt) return;
  //   // this.highlightSlotCell();

  //   try {
  //     const [taskData] = await this.orm.searchRead(
  //       "project.task",
  //       [["id", "=", jobcardIdInt]],
  //       ["second_visit_technician_bool", "technician_first_visit_id"],
  //     );

  //     const isSecondVisit = taskData?.second_visit_technician_bool || false;

  //     console.log("Second Visit Bool:", isSecondVisit);

  //     const values = {
  //       planned_date_begin: payload.plannedDateBegin,
  //       planned_date_end: payload.plannedDateEnd,
  //       job_card_state_code: payload.job_card_state_code,
  //       job_state: payload.job_state,
  //       job_card_state: payload.job_card_state,
  //       technician_id: payload.technician_id,
  //       warehouse_id: payload.warehouse_id,
  //     };

  //     // if (!taskData?.technician_first_visit_id) {
  //     //   values.technician_first_visit_id = payload.technician_id;
  //     // }
  //     if (
  //       taskData.technician_first_visit_id !== null &&
  //       values.job_card_state_code === 102
  //     ) {
  //       values.technician_first_visit_id = payload.technician_id;
  //     } else if (taskData?.second_visit_technician_bool) {
  //       values.technician_second_visit_id = payload.technician_id;
  //     } else {
  //       console.log(
  //         "ℹ️ Technician assignment skipped (no eligible visit condition).",
  //       );
  //     }

  //     // this.highlightSlotCell();

  //     await this.orm.write("project.task", [jobcardIdInt], values);

  //     sessionStorage.setItem("lastJobcardId", payload.jobcardId);
  //     sessionStorage.setItem("plannedStart", payload.plannedDateBegin);

  //     this.notification.add(
  //       `✅ Task updated successfully\nJobcard Number: ${
  //         this.state.jobCardNumber || this.state.name
  //       }\nTechnician: ${this.state.technicianName}`,
  //       { type: "success" },
  //     );

  //     const mrsRecords = await this.orm.searchRead(
  //       "machine.repair.support",
  //       [["task_id", "=", jobcardIdInt]],
  //       ["id"],
  //     );

  //     if (mrsRecords?.length) {
  //       const taskData2 = await this.orm.read(
  //         "project.task",
  //         [jobcardIdInt],
  //         ["team_id"],
  //       );
  //       const taskTeamId = taskData2?.[0]?.team_id?.[0] || null;

  //       const valuesMRS = {
  //         task_id: payload.jobcardId,
  //         service_request_state: payload.job_card_state,
  //         service_request_state_code: payload.job_card_state_code,
  //         user_id: payload.technician_id,
  //         team_id: taskTeamId,
  //         call_request_appointment_date: this.state.serviceDatetime || null,
  //         technician_appointment_date: payload.plannedDateBegin || null,
  //       };

  //       const mrsIds = mrsRecords.map((r) => r.id).filter((id) => !isNaN(id));
  //       if (mrsIds.length) {
  //         await this.orm.write("machine.repair.support", mrsIds, valuesMRS);
  //       }
  //     }
  //   } catch (err) {
  //     this.notification.add(
  //       "Already job assigned this slot.Please choose some other slot",
  //       {
  //         type: "info",
  //       },
  //     );
  //     console.error(err);
  //   }

  //   setTimeout(() => {
  //     const nextArrows = document.querySelectorAll(".oi.oi-arrow-right");
  //     nextArrows.forEach((el) => el.click());
  //     const previousArrows = document.querySelectorAll(".oi.oi-arrow-left");
  //     previousArrows.forEach((el) => el.click());
  //     sessionStorage.removeItem("lastJobcardId");
  //   }, 2000);
  // }

  // =================================================================================

  async updateJobCard() {
    // 26-01-2026 MODIFIED BY VENGATESH
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
        { type: "warning" },
      );
      return;
    }

    // Restrict technician reassignment for states 117, 132, 204, 133
    const noReassignStates = [204, 208, 133, 134]; // States where reassignment is not allowed
    if (noReassignStates.includes(parseInt(jobStateCode))) {
      this.notification.add(
        "⚠️ Technician reassignment is not allowed in this job state.",
        { type: "warning" },
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
    // const targetCode =
    //   Number(jobStateCode) === 101
    //     ? 102
    //     : Number(jobStateCode) === 101
    //     ? 102
    //     : Number(jobStateCode) === 117
    //     ? 204
    //     : Number(jobStateCode) === 132
    //     ? 133
    //     : Number(jobStateCode) === 152
    //     ? 208
    //     : Number(jobStateCode) === 122
    //     ? 134
    //     : Number(jobStateCode) === 156
    //     ? 102
    //     : Number(jobStateCode) === 127 &&
    //       this.state.unitpulloutcheck === true &&
    //       this.stste.quatecraetedBy === "S"
    //     ? 204
    //     : Number(jobStateCode) === 207 &&
    //       this.state.unitpulloutcheck === true &&
    //       this.stste.quatecraetedBy === "T"
    //     ? 208
    //     : jobStateCode;

    //   let taskStages = await this.orm.searchRead(
    //     "project.task.type",
    //     [["code", "=", String(jobStateCode)]],
    //     [("id", "code", "name", "dynamic_job_state_code")],
    //   );
    //   const stageState = await this.orm.searchRead(
    //     "project.task.type",
    //     [["code", "=", taskStages[0].dynamic_job_state_code]],
    //     ["id", "code", "name"],
    //   );
    //   // Use the first record as your stateTransition
    //   const stateTransition = {
    //     job_card_state_code: parseInt(taskStages[0].dynamic_job_state_code),
    //     job_state: stageState[0].id,
    //     job_card_state: stageState[0].name,
    //   };
    //   console.log("stateTransition:", stateTransition);
    // }

    let warrantyId = this.state.serviceWarrantyId;
    // added 24/01/2026
    let warrantyData = await this.orm.read(
      "service.warranty",
      [warrantyId],
      ["warranty_applicable_bool"],
    );
    console.log("warrantyData", warrantyData);
    const warrantyApplicable = warrantyData?.length
      ? warrantyData[0].warranty_applicable_bool
      : false;
    console.log("warrantyApplicable", warrantyApplicable);

    let isUnitPullOutStatusCheck = this.state.unitpulloutcheck;
    let balanceAmountreceivedBool = this.state.balanceAmountreceivedBool;
    let lastRescheduledStatusCode = this.state.last_rescheduled_status_code;
    console.log("lastRescheduledStatusCode", lastRescheduledStatusCode);
    console.log(
      "isUnitPullOutStatusCheck=============",
      isUnitPullOutStatusCheck,
    );
    console.log("balanceAmountreceivedBool", balanceAmountreceivedBool);

    let stateTransition = {};
    if (
      // added 24/01/2026
      warrantyApplicable === false &&
      // jobStateCode === 127 &&
      Number(jobStateCode) === 127 &&
      isUnitPullOutStatusCheck === true &&
      balanceAmountreceivedBool === true
    ) {
      const forcedStage = await this.orm.searchRead(
        "project.task.type",
        [["code", "=", 204]],
        ["id", "code", "name"],
      );

      if (forcedStage.length) {
        stateTransition = {
          job_card_state_code: parseInt(forcedStage[0].code),
          job_state: forcedStage[0].id,
          job_card_state: forcedStage[0].name,
        };

        // Object.assign(this.state, stateTransition);
        console.log("stateTransition 204:", stateTransition);
      }
    }
    // else if(jobStateCode=107 && ){

    // }
    else if (Number(jobStateCode) === 107 && lastRescheduledStatusCode) {
      //26 - jan - 2026  Modified by Vengatesh
      const stageLastResult = await this.orm.searchRead(
        "project.task.type",
        [["code", "=", String(lastRescheduledStatusCode)]],
        ["id", "code", "name"],
      );

      if (stageLastResult.length) {
        stateTransition = {
          job_card_state_code: Number(stageLastResult[0].code),
          job_state: stageLastResult[0].id,
          job_card_state: stageLastResult[0].name,
          last_rescheduled_status_code: Number(lastRescheduledStatusCode),
        };
      }
    } else {
      const taskStages = await this.orm.searchRead(
        "project.task.type",
        [["code", "=", String(jobStateCode)]],
        ["id", "code", "name", "dynamic_job_state_code"],
      );

      if (!taskStages.length || !taskStages[0].dynamic_job_state_code) {
        return; // ❗ nothing to process safely
      }

      const stageState = await this.orm.searchRead(
        "project.task.type",
        [["code", "=", String(taskStages[0].dynamic_job_state_code)]],
        ["id", "code", "name", "scheduling_status_bool"],
      );

      if (!stageState.length) {
        return;
      }

      stateTransition = {
        job_card_state_code: Number(taskStages[0].dynamic_job_state_code),
        job_state: stageState[0].id,
        job_card_state: stageState[0].name,
        last_rescheduled_status_code: Number(lastRescheduledStatusCode) || null,
      };

      // 🔹 update ONLY when scheduling is true
      if (stageState[0].scheduling_status_bool === true) {
        stateTransition.last_rescheduled_status_code = Number(
          stageState[0].code,
        );
      }
    }
    console.log("Final stateTransition", stateTransition);

    //  else {
    //   const taskStages = await this.orm.searchRead(
    //     "project.task.type",
    //     [["code", "=", jobStateCode]],
    //     ["id", "code", "name", "dynamic_job_state_code"],
    //   );

    //   if (taskStages.length) {
    //     const stageState = await this.orm.searchRead(
    //       "project.task.type",
    //       [["code", "=", taskStages[0].dynamic_job_state_code]],
    //       ["id", "code", "name"],
    //     );
    //     console.log("stageState------------------>", stageState);

    //     if (stageState.length) {
    //       stateTransition = {
    //         job_card_state_code: parseInt(taskStages[0].dynamic_job_state_code),
    //         job_state: stageState[0].id,
    //         job_card_state: stageState[0].name,
    //       };
    //       if (stageState[0].scheduling_status_bool === true) {
    //         stateTransition.last_rescheduled_status_code = Number(
    //           stageState[0].code,
    //         );
    //       }

    //       console.log("stateTransition:", stateTransition);
    //     }
    //   }
    // }

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
        ["id", "name", "warehouse_id"],
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
      // job_card_state_code: targetCode,
      // warehouse_id: this.state.warehouseId || null,
      warehouse_id: this.matchedWarehouseId,
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
        ["second_visit_technician_bool", "technician_first_visit_id"],
      );

      const isSecondVisit = taskData?.second_visit_technician_bool || false;

      console.log("Second Visit Bool:", isSecondVisit);

      const values = {
        planned_date_begin: payload.plannedDateBegin,
        planned_date_end: payload.plannedDateEnd,
        job_card_state_code: payload.job_card_state_code,
        job_state: payload.job_state,
        job_card_state: payload.job_card_state,
        technician_id: payload.technician_id,
        warehouse_id: payload.warehouse_id,
        last_rescheduled_status_code:
          payload.last_rescheduled_status_code || "",
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
          "ℹ️ Technician assignment skipped (no eligible visit condition).",
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
        { type: "success" },
      );

      const mrsRecords = await this.orm.searchRead(
        "machine.repair.support",
        [["task_id", "=", jobcardIdInt]],
        ["id"],
      );

      if (mrsRecords?.length) {
        const taskData2 = await this.orm.read(
          "project.task",
          [jobcardIdInt],
          ["team_id"],
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
        },
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
        ".o_gantt_view, .o_gantt, .o_content, .o_view_controller",
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
        "td[data-resource-id][data-date], td[data-date], .o_gantt_cell[data-date]",
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
