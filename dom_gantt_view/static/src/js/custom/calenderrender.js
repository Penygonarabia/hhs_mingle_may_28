/** @odoo-module **/

import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { patch } from "@web/core/utils/patch";

patch(DateTimePicker.prototype, {
  /**
   * Happens when a date item is selected:
   * - first tries to zoom in on the item
   * - if could not zoom in: date is considered as final value and triggers a hard select
   * @param {DateItem} dateItem
   */
  zoomOrSelect(dateItem) {
    if (!dateItem.isValid) {
      // Invalid item
      return;
    }
    if (this.zoomIn(dateItem.range[0])) {
      // Zoom was successful
      return;
    }
    const [value] = dateItem.range;
    const valueIndex = this.props.focusedDateIndex;
    const isValid = this.validateAndSelect(value, valueIndex);
    this.shouldAdjustFocusDate = isValid && !this.props.range;
    console.log(" this.shouldAdjustFocusDate", this.shouldAdjustFocusDate);
    console.log("valueIndex", valueIndex);
    console.log("value", value);
    console.log("isValid", isValid);

    // Trigger the page refresh after selecting the date
    // if (isValid) {
    //   window.location.reload(2000);
    // }
  },
});
