/** @odoo-module **/
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";
const { DateTime } = luxon;

export class DomGanttController extends CalendarController {
  setup() {
    super.setup(...arguments);
    this.actionService = useService("action");
    this.state = useState({
      showSideBar: false,
      lastJobcardId: sessionStorage.getItem("lastJobcardId") || null,
      showingDay: "",
    });
    // this.defaultDate = new Date();
  }
  get dayHeader() {
    return `${this.date.toFormat("cccc")}, ${this.date.toFormat(
      "d"
    )} ${this.date.toFormat("MMMM")} ${this.date.year}`;
  }
  get date() {
    if (this.props?.context?.planned_date_begin) {
      return DateTime.fromISO(this.props.context.planned_date_begin);
    }
    if (this.model?.data?.planned_date_begin) {
      return DateTime.fromISO(this.model.data.planned_date_begin);
    }

    return this.model.meta.date || DateTime.now();
  }
  async onWillStartModel() {
    let chosenDate = null;

    if (this.props?.context?.planned_date_begin) {
      const pd = this.props.context.planned_date_begin;
      chosenDate =
        typeof pd === "string" ? DateTime.fromISO(pd) : DateTime.fromJSDate(pd);
    } else if (this.props?.context?.default_date) {
      const dd = this.props.context.default_date;
      chosenDate =
        typeof dd === "string" ? DateTime.fromISO(dd) : DateTime.fromJSDate(dd);
    } else {
      chosenDate = DateTime.now();
    }
    this.model.meta.date = chosenDate;
    this.state.showingDay = chosenDate.toFormat("ccc, LLL dd");
    console.log("this.state", this.state.showingDay);

    // If the model has a method to change date, use it instead
    if (typeof this.model.goToDate === "function") {
      this.model.goToDate(chosenDate);
    }
  }

  onClickAddButton() {
    if (!this.model.meta.canCreate) return;
    const context = { ...this.model.meta.context };
    // console.log('context', context)
    context.from_ui = true;
    if (this.model.formViewId) {
      this.displayDialog(FormViewDialog, {
        resModel: this.model.resModel,
        title: _t("New") + " " + this.model.meta.label || "",
        viewId: this.model.formViewId,
        onRecordSaved: () => {
          this.model.load();
        },
        context: context,
      });
    } else {
      this.actionService.doAction(
        {
          type: "ir.actions.act_window",
          res_model: this.model.resModel,
          views: [[false, "form"]],
        },
        {
          additionalContext: context,
        }
      );
    }
  }
}

DomGanttController.template = "dom_gantt_view.DomGanttController";
