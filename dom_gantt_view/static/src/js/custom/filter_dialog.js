/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class FilterDialog extends Component {
  static template = "FilterDialog";
  static components = { Dialog };

  setup() {
    // ✅ Get lists passed from parent
    this.cityList = this.props.cityList || [];
    this.jobStates = this.props.jobStates || [];
    console.log("cityList", this.cityList);
    console.log("jobStates", this.jobStates);
  }

  // 🌆 Optional: Listen for city changes
  onCityChange(ev) {
    const selectedCityId = ev.target.value;
    const selectedCity = this.cityList.find(
      (c) => c.id === parseInt(selectedCityId)
    );
    console.log("🏙️ City changed:", selectedCityId, selectedCity?.name);
  }

  // ❌ Cancel button handler
  onCancel() {
    this.props.close?.();
  }

  // ✅ Apply button handler
  onConfirm() {
    const city = this.refs?.city?.value || "";
    const status = this.refs?.status?.value || ""; // ✅ fixed here

    console.log("✅ Confirming filter:", { city, status });
    this.props.onApply?.({ city, status });
    this.props.close?.();
  }
}
