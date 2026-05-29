/** @odoo-module **/
 
//calendar_force_day_patch.js
 
 
import { patch } from "@web/core/utils/patch";
import { CalendarController } from "@web/views/calendar/calendar_controller";
 
patch(CalendarController.prototype, {
  get datePickerProps() {
    const props = super.datePickerProps;
    return {
      ...props,
      onSelect: (date) => {
        const scale = "day"; // 🔥 Force Day scale always
        this.model.load({ scale, date });
      },
    };
  },
});
 