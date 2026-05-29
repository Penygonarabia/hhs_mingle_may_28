/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { DomGanttCommonRenderer } from "./domgantt_common_renderer.esm";

patch(DomGanttCommonRenderer.prototype, {
  //   setup() {
  //     if (super.setup) super.setup(...arguments);
  //     // Bind method so it can be called in lifecycle hooks
  //     this.applyPinkToWeekendSlots = this.applyPinkToWeekendSlots.bind(this);
  //   },
  //   onMounted() {
  //     if (super.onMounted) super.onMounted(...arguments);
  //     this.applyPinkToWeekendSlots();
  //   },
  //   onPatched() {
  //     if (super.onPatched) super.onPatched(...arguments);
  //     this.applyPinkToWeekendSlots();
  //   },
  //   /**
  //    * Apply pink background to all Friday (5) and Saturday (6) timeline slots
  //    */
  //   applyPinkToWeekendSlots() {
  //     const slots = document.querySelectorAll("td.fc-timeline-slot");
  //     slots.forEach((slot) => {
  //       const dateStr = slot.getAttribute("data-date");
  //       if (!dateStr) return;
  //       const slotDate = new Date(dateStr);
  //       const day = slotDate.getDay(); // 0=Sunday, 5=Friday, 6=Saturday
  //       if (day === 5 || day === 6) {
  //         slot.style.backgroundColor = "pink";
  //       }
  //     });
  //   },
});
