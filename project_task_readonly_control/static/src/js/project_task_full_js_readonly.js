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

        // const container = document.querySelector(".o_form_sheet_bg");
        // const banner = document.createElement("div");
        // banner.className = "o_readonly_banner";
        // banner.innerText = "🔒 This page is in Readonly Mode";
        // container.style.position = "relative";
        // container.appendChild(banner);
      });

      this.dialogService.add(AlertDialog, {
        title: "Access Restricted",
        body: "This record is in a protected state. You cannot edit it.",
      });
    }
  },
});
