/** @odoo-module **/
import {DomGanttModel} from "@dom_gantt_view/js/domgantt_model.esm";
import {patch} from "@web/core/utils/patch";

patch(DomGanttModel.prototype, {
    async updateRawValueRecords(resIds, record, options = {}) {
        const self = this;
        const recordIds = resIds.map((id) => id);
		//        record.isAllDay = true;
        // Do NOT force all-day: keep as is or default to false if undefined
        if (record.isAllDay === undefined) {
            record.isAllDay = false;
        }
 
        const rawRecord = this.buildRawRecord(record, options);
        delete rawRecord.name;
        await this.orm
            .write(this.meta.resModel, recordIds, rawRecord, {
                context: {from_ui: true},
            })
            .finally(function () {
                self.load();
            });
    },
});
