/** @odoo-module **/

import {CalendarCommonPopover} from "@web/views/calendar/calendar_common/calendar_common_popover";
import {useService} from "@web/core/utils/hooks";

export class DomGanttCommonPopover extends CalendarCommonPopover {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }
    get isEventEditable() {
        return this.props.model.canEdit;
    }
    get hasFooter() {
        return (
            this.isEventEditable || this.isEventDeletable || this.isEventViewMoreOptions
        );
    }
    get isEventViewMoreOptions() {
        return this.props.model.meta.viewMoreOptions;
    }
    goToFullEvent() {
        this.props.editRecord(this.props.record);
        this.props.close();
    }
}
DomGanttCommonPopover.subTemplates = {
    ...CalendarCommonPopover.subTemplates,
    footer: "dom_gantt_view.DomGanttCommonPopover.footer",
};
