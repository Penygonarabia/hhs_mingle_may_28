/** @odoo-module **/

import {DomGanttArchParser} from "./domgantt_arch_parser.esm";
import {DomGanttController} from "./domgantt_controller.esm";
import {DomGanttModel} from "./domgantt_model.esm";
import {DomGanttRenderer} from "./domgantt_renderer.esm";
import {_t} from "@web/core/l10n/translation";
import {calendarView} from "@web/views/calendar/calendar_view";
import {registry} from "@web/core/registry";

export const domGanttView = {
    ...calendarView,
    type: "gantt",
    display_name: _t("Gantt"),
    icon: "fa fa-tasks",
    ViewType: "gantt",
    ArchParser: DomGanttArchParser,
    Model: DomGanttModel,
    Controller: DomGanttController,
    Renderer: DomGanttRenderer,
};

registry.category("views").add("gantt", domGanttView);
