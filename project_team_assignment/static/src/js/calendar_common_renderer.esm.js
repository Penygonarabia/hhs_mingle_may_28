/** @odoo-module **/
import {DomGanttCommonRenderer} from "@dom_gantt_view/js/common/domgantt_common_renderer.esm";
import {patch} from "@web/core/utils/patch";

patch(DomGanttCommonRenderer.prototype, {
    onDateClick(info) {
        if (info.jsEvent.target.closest(".o_gantt_click_to_chose")) {
            info.selectTask = true;
            this.props.createRecord(this.fcEventToRecord(info));
          
        } else {
            super.onDateClick(...arguments);
        }
    },
    fcEventToRecord(event) {
        const res = super.fcEventToRecord(...arguments);
        res.selectTask = event.selectTask;
        return res;
    },
});
