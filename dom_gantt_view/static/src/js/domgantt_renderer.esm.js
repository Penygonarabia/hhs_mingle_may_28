/** @odoo-module **/
/** @odoo-module **/
import { ActionSwiper } from "@web/core/action_swiper/action_swiper";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { DomGanttCommonRenderer } from "./common/domgantt_common_renderer.esm";
import { MyComponent } from "./custom/component";
import { JobcardList } from "./custom/JobcardList";
import { onMounted } from "@odoo/owl";
import { session } from "@web/session";

export class DomGanttRenderer extends CalendarRenderer {
  setup() {
    super.setup();

    const isRTL = session.user_context.lang.startsWith("ar");

    // 🔹 Set container direction and layout on mount
    onMounted(() => {
      const container = document.querySelector(".o_calendar_renderer");
      if (container) {
        container.style.direction = isRTL ? "rtl" : "ltr";
        // container.style.flexDirection = "row"; // keep sidebar + calendar order
      }
    });

    // 🔹 Set calendar options for RTL
    this.calendarOptions = {
      ...this.calendarOptions,
      direction: isRTL ? "rtl" : "ltr",
    };

    // 🔹 Restore hide_jobcard_list flag from sessionStorage
    const hideFlag = sessionStorage.getItem("hide_jobcard_list");
    if (hideFlag === "true") {
      this.env.searchModel.context.hide_jobcard_list = true;
      sessionStorage.removeItem("hide_jobcard_list");
    }
  }

  getComponentProps(viewType) {
    const baseProps = super.getComponentProps(viewType);
    return {
      ...baseProps,
      defaultDate: this.defaultDate,
    };
  }
}

DomGanttRenderer.components = {
  day: DomGanttCommonRenderer,
  week: DomGanttCommonRenderer,
  month: DomGanttCommonRenderer,
  year: DomGanttCommonRenderer,
  ActionSwiper,
  MyComponent,
  JobcardList,
};
