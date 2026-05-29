/** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";
// import { useState, onWillStart } from "@odoo/owl";

// patch(FormController.prototype, {
//   setup() {
//     super.setup();

//     this.userService = useService("user");
//     this.orm = useService("orm");

//     // ✅ Always initialize state synchronously
//     this.state = useState({
//       isReadonly: false,
//     });

//     onWillStart(async () => {
//       if (!this.props.resId) return;

//       const records = await this.orm.read(
//         this.props.resModel,
//         [this.props.resId],
//         ["job_card_state_code"],
//       );

//       const stateCode = records[0]?.job_card_state_code;
//       console.log("stateCode", stateCode);

//       const isTechnicalUser = await this.userService.hasGroup(
//         "machine_repair_management.group_technical_allocation_user",
//       );

//       this.state.isReadonly =
//         isTechnicalUser && ["121", "129"].includes(String(stateCode));
//       console.log("this.state.isReadonly", this.state.isReadonly);
//     });
//   },

//   get modelParams() {
//     const params = super.modelParams;
//     console.log("params", params);

//     let mode = this.props.mode || "edit";

//     const records = this.orm
//       .read(
//         params.config.resModel,
//         [params.config.resId],
//         ["job_card_state_code"],
//       )
//       .then((res) => {
//         console.log("Resolved:", res);
//         console.log("State Code:", res[0]?.job_card_state_code);
//       });

//     console.log("Promise:", "request sent");

//     const isTechnicalUser = params.config.context.uid;
//     console.log("isTechnicalUser", isTechnicalUser);

//     const stateCode = records[0]?.job_card_state_code;
//     console.log("stateCode", stateCode);

//     if (this.state?.isReadonly) {
//       mode = "readonly";
//       console.log("mode", mode);
//     }

//     params.config.mode = mode;

//     return params;
//   },
// });

// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";
// // import { useState, onWillStart } from "@odoo/owl";

// patch(FormController.prototype, {
//   setup() {
//     super.setup();

//     this.userService = useService("user");
//     this.orm = useService("orm");
//   },
//   async isReadonlyByState() {
//     // 1. Fetch the state
//     const records = await this.orm.read(
//       this.props.resModel,
//       [this.props.resId],
//       ["job_card_state_code"],
//     );

//     const stateCode = records[0]?.job_card_state_code;

//     console.log("job_card_state_code =", stateCode);

//     // 2. Check group (also async in Odoo 16+)
//     const isTechnicalUser = await this.userService.hasGroup(
//       "machine_repair_management.group_technical_allocation_user",
//     );

//     console.log("isTechnicalUser:", isTechnicalUser);
//     const isReadOnly =
//       isTechnicalUser && ["121", "129"].includes(String(stateCode));

//     console.log("job_card_state_code =", stateCode);
//     console.log("isTechnicalUser =", isTechnicalUser);
//     console.log(
//       "is in protected states (121,129) =",
//       ["121", "129"].includes(stateCode),
//     );
//     console.log("→ Final isReadonlyByState() =", isReadOnly);

//     return isReadOnly;
//   },

//   get modelParams() {
//     const params = super.modelParams;

//     let mode = this.props.mode || "edit";

//     const isReadonly = this.isReadonlyByState();

//     console.log("IS READONLY:", isReadonly);

//     if (isReadonly) {
//       mode = "readonly";
//     }

//     params.config.mode = mode;

//     return params;
//   },
// });

/** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";
// import { onMounted } from "@odoo/owl";

// patch(FormController.prototype, {
//   setup() {
//     super.setup();

//     this.orm = useService("orm");
//     this.userService = useService("user");

//     this.isReadonlyFlag = false;

//     // ✅ AFTER PAGE RENDER
//     onMounted(async () => {
//       await this._computeReadonly();
//     });
//   },

//   async _computeReadonly() {
//     try {
//       const records = await this.orm.read(
//         this.props.resModel,
//         [this.props.resId],
//         // ["job_card_state_code"],
//       );
//       console.log("records", records);

//       const stateCode = records[0]?.job_card_state_code;

//       const isTechnicalUser = await this.userService.hasGroup(
//         "machine_repair_management.group_technical_allocation_user",
//       );

//       const isProtected = ["121", "129"].includes(String(stateCode));

//       this.isReadonlyFlag = isProtected && isTechnicalUser;

//       console.log("===== AFTER RENDER CHECK =====");
//       console.log("stateCode =", stateCode);
//       console.log("isTechnicalUser =", isTechnicalUser);
//       console.log("isProtected =", isProtected);
//       console.log("FINAL isReadonlyFlag =", this.isReadonlyFlag);
//       console.log("this.mode", this.model);
//       console.log("this.model.root", this.model.root);

//       if (this.isReadonlyFlag === true) {
//         this.model.root.config;
//         console.log("this.model.root.config", this.model.root.config.mode);
//         let changes = await this.model.load({
//           resId: this.props.resId,
//           mode: "readonly",
//         });
//         console.log("await this.model.load });", changes);
//       }
//       // // 🔥 APPLY AFTER RENDER
//       // if (this.isReadonlyFlag) {
//       //   // this.model.config.mode("readonly"); // ✅ BEST WAY
//       // }
//     } catch (error) {
//       console.error("Readonly error:", error);
//     }
//   },
// });

/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onRendered } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
patch(FormController.prototype, {
  setup() {
    super.setup();

    this.orm = useService("orm");
    this.userService = useService("user");
    this.dialogService = useService("dialog");
    this._readonlyApplied = false;

    onMounted(async () => {
      await this._applyReadonlyInstant();
    });
    // onRendered(() => {
    //   if (this.isReadonlyFlag && this.el) {
    //     const statusbar = document.querySelector(".o_form_statusbar");
    //     console.log("statusbar", statusbar);
    //     if (statusbar) {
    //       statusbar.classList.add("o_statusbar_blocked");
    //     }
    //   }
    // });
  },

  async _applyReadonlyInstant() {
    // ✅ Apply only for project.task
    if (this.props.resModel !== "project.task") return;
    if (!this.props.resId || this._readonlyApplied) return;

    const records = await this.orm.read(
      this.props.resModel,
      [this.props.resId],
      ["job_card_state_code"],
    );

    const stateCode = records[0]?.job_card_state_code;

    const isTechnicalUser = await this.userService.hasGroup(
      "machine_repair_management.group_technical_allocation_user",
    );

    const isProtected = ["121", "129"].includes(String(stateCode));
    const isReadonly = isProtected && isTechnicalUser;

    console.log("Instant readonly:", isReadonly);
    console.log("this.mode", this.model);
    console.log("this.model.root", this.model.root);
    console.log("this.props.info", this.props.info);
    if (isReadonly) {
      this._readonlyApplied = true;

      // 🔥 KEY PART (NO RELOAD)
      // this.model.root.isInEdition = false;
      this.model.config.mode = "readonly";
      // 🔥 force UI refresh
      this.render();

      // 🔥 IMPORTANT: wait for DOM update
      setTimeout(() => {
        // if (this.el) {
        const statusbar = document.querySelector(".o_form_statusbar");
        const SchedulingBtn = document.querySelector(
          "button[name='action_open_js_popup']",
        );
        const saveBtn = document.querySelector("button[name='action_save']");

        // Discard button
        const discardBtn = document.querySelector(
          "button[name='action_discard']",
        );
        console.log("statusbar", statusbar);
        if (statusbar) {
          statusbar.classList.add("o_statusbar_blocked");
          SchedulingBtn.classList.add("o_btn_disabled");
          saveBtn.classList.add("o_btn_disabled");
          discardBtn.classList.add("o_btn_disabled");
        }

        const container = document.querySelector(".o_form_sheet_bg");

        const banner = document.createElement("div");
        banner.className = "o_readonly_banner";
        banner.innerText = "🔒 This page is in Readonly Mode";

        container.style.position = "relative";
        container.appendChild(banner);

        // }
      });

      this.dialogService.add(AlertDialog, {
        title: "Access Restricted",
        body: "This record is in a protected state. You cannot edit it.",
      });
    }
  },
});

// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";
// import { useState, onMounted, onWillStart } from "@odoo/owl";
// patch(FormController.prototype, {
//   setup() {
//     super.setup();
//     this.userService = useService("user");
//     this.orm = useService("orm");
//     this.state = useState({
//       jobcardstatecode: null,
//     });

//     onMounted(async () => {
//       const res = this.orm.read(
//         this.props.resModel,
//         [this.props.resId],
//         ["job_card_state_code"],
//       );

//       console.log("ORM RESULT:", res);

//       if (res && res.length) {
//         this.state.jobcardstatecode = res[0].job_card_state_code;
//       }
//     });
//   },

//   isReadonlyByState() {
//     const state = this.state.jobcardstatecode || "";

//     const isGroup = this.userService.hasGroup(
//       "machine_repair_management.group_technical_allocation_user",
//     );

//     console.log("STATE:", state);
//     console.log("IS GROUP:", isGroup);

//     return isGroup && ["121", "129"].includes(state);
//   },

//   // ✅ Override modelParams
//   get modelParams() {
//     const params = super.modelParams;

//     let mode = this.props.mode || "edit";

//     const isReadonly = this.isReadonlyByState();

//     console.log("IS READONLY:", isReadonly);

//     if (isReadonly) {
//       mode = "readonly";
//     }

//     params.config.mode = mode;

//     return params;
//   },
// });

// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";

// patch(FormController.prototype, {
//   setup() {
//     super.setup();
//     this.userService = useService("user");
//     this.orm = useService("orm");
//   },

//   _isReadonlyByState(dta) {
//     const record = this.model?.root;
//     if (!record) return false;

//     const state = record.data.job_card_state_code;

//     const isGroup = this.userService.hasGroup(
//       "machine_repair_management.group_technical_allocation_user",
//     );

//     return isGroup && ["121", "129"].includes(state);
//   },

//   get modelParams() {
//     const params = super.modelParams;
//     console.log("params", params);
//     console.log("params", params.config.resId);
//     console.log("params", params.config.resModel);

//     const result = this.orm.read(
//       params.config.resModel,
//       [params.config.resId],
//       ["job_card_state_code"],
//     );
//     console.log("result", result);
//     let mode = this.props.mode || "edit";
//     console.log("mode", mode);

//     const data = this._isReadonlyByState();
//     console.log("_isReadonlyByState result:", data);

//     params.config.mode = mode;
//     console.log("record", params.config.mode);
//     return params;
//   },
// });

// /** @odoo-module **/
// import { patch } from "@web/core/utils/patch";
// import { FormController } from "@web/views/form/form_controller";
// import { useService } from "@web/core/utils/hooks";
// import { onMounted, onPatched } from "@odoo/owl";

// patch(FormController.prototype, {
//   setup() {
//     super.setup();
//     this.userService = useService("user");

//     onMounted(() => {
//       this.isReadonlyByState();
//     });
//   },

//   isReadonlyByState() {
//     const record = this.model.root;
//     console.log("record", record);
//     if (!record) return false;

//     const isGroup = this.userService.hasGroup(
//       "machine_repair_management.group_technical_allocation_user",
//     );
//     console.log("isGroup", isGroup);
//     const state = record.data.job_card_state_code;
//     console.log("state", state);

//     return isGroup && ["121", "129"].includes(state);
//   },

//   get isReadonly() {
//     return this.isReadonlyByState() || super.isReadonly;
//   },
// });
