/** @odoo-module **/

import {Field} from "@web/views/fields/field";
import {archParseBoolean} from "@web/views/utils";
import {browser} from "@web/core/browser/browser";
import {evaluateExpr} from "@web/core/py_js/py";
import {visitXML} from "@web/core/utils/xml";

const FIELD_ATTRIBUTE_NAMES = [
    "date_start",
    "date_delay",
    "date_stop",
    "all_day",
    "recurrence_update",
    "create_name_field",
    "color",
];
const SCALES = ["day", "week", "month", "year"];

export class DomGanttParseArchError extends Error {}

export class DomGanttArchParser {
    parse(arch, models, modelName) {
        const fields = models[modelName];
        const fieldNames = new Set(fields.display_name ? ["display_name"] : []);
        const fieldMapping = {date_start: "date_start"};
        let jsClass = null;
        // Start custom here
        let eventLimit = false;
        // End custom
        let scales = [...SCALES];
        const sessionScale = browser.sessionStorage.getItem("calendar-scale");
        let scale = sessionScale || "week";
        let canCreate = true;
        let canDelete = true;
        let canEdit = true;
        let quickCreate = true;
        let quickCreateViewId = null;
        let hasEditDialog = false;
        let showUnusualDays = false;
        let isDateHidden = false;
        let isTimeHidden = true;
        let isTimeEndHidden = false;
        // 1: normal, 2: move endtime far right
        let eventTimeDisplayFar = false;
        let eventTimeFormatDigits = false;
        let isDateTimeScale = false;
        let scaleHours = 0;
        let formViewId = false;
        const popoverFieldNodes = {};
        const filtersInfo = {};

        // Start custom here
        let resourceWidth = false;
        let slotMinWidth = false;
        let resourceOrder = false;
        let resourceGroupField = false;
        const columnFields = {};
        let label = false;
        let eventTitleField = false;
        let hideEventTitle = false;
        let slotLabelFormat = false;
        let resourceWOEventField = false;
        let viewMoreOptions = false;
        let minResourceHeight = false;
        // End custom

        // eslint-disable-next-line complexity
        visitXML(arch, (node) => {
            switch (node.tagName) {
                case "gantt": {
                    if (!node.hasAttribute("date_start")) {
                        throw new DomGanttParseArchError(
                            `Calendar view has not defined "date_start" attribute.`
                        );
                    }

                    jsClass = node.getAttribute("js_class");

                    for (const fieldAttrName of FIELD_ATTRIBUTE_NAMES) {
                        if (node.hasAttribute(fieldAttrName)) {
                            const fieldName = node.getAttribute(fieldAttrName);
                            fieldNames.add(fieldName);
                            fieldMapping[fieldAttrName] = fieldName;
                        }
                    }

                    if (node.hasAttribute("event_limit")) {
                        eventLimit = evaluateExpr(node.getAttribute("event_limit"));
                        if (!Number.isInteger(eventLimit)) {
                            throw new DomGanttParseArchError(
                                `Calendar view's event limit should be a number`
                            );
                        }
                    }
                    if (node.hasAttribute("scales")) {
                        const scalesAttr = node.getAttribute("scales");
                        scales = scalesAttr
                            .split(",")
                            .filter((s) => SCALES.includes(s));
                    }
                    if (node.hasAttribute("mode")) {
                        scale = node.getAttribute("mode");
                        if (!scales.includes(scale)) {
                            throw new DomGanttParseArchError(
                                `Calendar view cannot display mode: ${scale}`
                            );
                        }
                    }
                    if (node.hasAttribute("create")) {
                        canCreate = archParseBoolean(node.getAttribute("create"), true);
                    }
                    if (node.hasAttribute("delete")) {
                        canDelete = archParseBoolean(node.getAttribute("delete"), true);
                    }
                    if (node.hasAttribute("edit")) {
                        canEdit = archParseBoolean(node.getAttribute("edit"), true);
                    }
                    if (node.hasAttribute("quick_create")) {
                        quickCreate = archParseBoolean(
                            node.getAttribute("quick_create"),
                            true
                        );
                        if (quickCreate && node.hasAttribute("quick_create_view_id")) {
                            quickCreateViewId = parseInt(
                                node.getAttribute("quick_create_view_id"),
                                10
                            );
                        }
                    }
                    if (node.hasAttribute("event_open_popup")) {
                        hasEditDialog = archParseBoolean(
                            node.getAttribute("event_open_popup")
                        );
                    }
                    if (node.hasAttribute("show_unusual_days")) {
                        showUnusualDays = archParseBoolean(
                            node.getAttribute("show_unusual_days")
                        );
                    }
                    if (node.hasAttribute("hide_date")) {
                        isDateHidden = archParseBoolean(node.getAttribute("hide_date"));
                    }
                    if (node.hasAttribute("hide_time")) {
                        isTimeHidden = archParseBoolean(node.getAttribute("hide_time"));
                    }
                    if (node.hasAttribute("hide_time_end")) {
                        isTimeEndHidden = archParseBoolean(
                            node.getAttribute("hide_time_end")
                        );
                    }
                    if (node.hasAttribute("event_time_display_far")) {
                        eventTimeDisplayFar = archParseBoolean(
                            node.getAttribute("event_time_display_far")
                        );
                    }
                    if (node.hasAttribute("event_time_format_digits")) {
                        eventTimeFormatDigits = archParseBoolean(
                            node.getAttribute("event_time_format_digits")
                        );
                    }
                    if (node.hasAttribute("datetime_scale")) {
                        isDateTimeScale = archParseBoolean(
                            node.getAttribute("datetime_scale")
                        );
                    }
                    if (node.hasAttribute("datetime_scale_hour")) {
                        scaleHours = parseInt(
                            node.getAttribute("datetime_scale_hour"),
                            12
                        );
                    }
                    if (node.hasAttribute("form_view_id")) {
                        formViewId = parseInt(node.getAttribute("form_view_id"), 10);
                    }
                    // Start custom here
                    if (node.hasAttribute("resource_width_percentage")) {
                        resourceWidth = node.getAttribute("resource_width_percentage");
                    }
                    if (node.hasAttribute("slot_min_width")) {
                        slotMinWidth = parseInt(
                            node.getAttribute("slot_min_width"),
                            20
                        );
                    }
                    if (node.hasAttribute("resource_order")) {
                        resourceOrder = node.getAttribute("resource_order");
                    }
                    if (node.hasAttribute("string")) {
                        label = node.getAttribute("string");
                    }
                    if (node.hasAttribute("event_title_field")) {
                        eventTitleField = node.getAttribute("event_title_field");
                        fieldNames.add(eventTitleField);
                    }
                    if (node.hasAttribute("hide_event_title")) {
                        hideEventTitle = archParseBoolean(
                            node.getAttribute("hide_event_title")
                        );
                    }
                    if (node.hasAttribute("header_label_format")) {
                        slotLabelFormat = node.getAttribute("header_label_format");
                    }
                    if (node.hasAttribute("view_more_options")) {
                        viewMoreOptions = archParseBoolean(
                            node.getAttribute("view_more_options")
                        );
                    }
                    if (node.hasAttribute("min_resource_height")) {
                        minResourceHeight = node.getAttribute("min_resource_height");
                    }

                    // End custom

                    break;
                }
                case "field": {
                    const fieldName = node.getAttribute("name");
                    fieldNames.add(fieldName);

                    const fieldInfo = Field.parseFieldNode(
                        node,
                        models,
                        modelName,
                        "gantt",
                        jsClass
                    );
                    popoverFieldNodes[fieldName] = fieldInfo;
                    // Start custom here
                    // popoverFieldNodes[fieldName] = fieldInfo;
                    if (node.parentNode.tagName === "templates") {
                        popoverFieldNodes[fieldName] = fieldInfo;
                    } else if (node.parentNode.tagName === "gantt") {
                        columnFields[fieldName] = fieldInfo;
                    }
                    // End custom
                    const field = fields[fieldName];
                    if (
                        !node.hasAttribute("invisible") ||
                        node.hasAttribute("filters")
                    ) {
                        let filterInfo = null;
                        if (
                            node.hasAttribute("avatar_field") ||
                            node.hasAttribute("write_model") ||
                            node.hasAttribute("write_field") ||
                            node.hasAttribute("color") ||
                            node.hasAttribute("filters")
                        ) {
                            filtersInfo[fieldName] = filtersInfo[fieldName] || {
                                avatarFieldName: null,
                                colorFieldName: null,
                                fieldName,
                                filterFieldName: null,
                                label: field.string,
                                resModel: field.relation,
                                writeFieldName: null,
                                writeResModel: null,
                            };
                            filterInfo = filtersInfo[fieldName];
                        }
                        if (node.hasAttribute("filter_field")) {
                            filterInfo.filterFieldName =
                                node.getAttribute("filter_field");
                        }
                        if (node.hasAttribute("avatar_field")) {
                            filterInfo.avatarFieldName =
                                node.getAttribute("avatar_field");
                        }
                        if (node.hasAttribute("write_model")) {
                            filterInfo.writeResModel = node.getAttribute("write_model");
                        }
                        if (node.hasAttribute("write_field")) {
                            filterInfo.writeFieldName =
                                node.getAttribute("write_field");
                        }
                        if (node.hasAttribute("filters")) {
                            if (node.hasAttribute("color")) {
                                filterInfo.colorFieldName = node.getAttribute("color");
                            }
                            if (node.hasAttribute("avatar_field") && field.relation) {
                                if (
                                    field.relation.includes([
                                        "res.users",
                                        "res.partners",
                                        "hr.employee",
                                    ])
                                ) {
                                    filterInfo.avatarFieldName = "image_128";
                                }
                            }
                        }
                        if (node.hasAttribute("is_resource_group_field")) {
                            if (
                                archParseBoolean(
                                    node.getAttribute("is_resource_group_field")
                                )
                            ) {
                                resourceGroupField = fieldName;
                            }
                        }
                        if (
                            node.hasAttribute("resource_wo_event_field") &&
                            node.parentNode.tagName === "gantt"
                        ) {
                            if (
                                archParseBoolean(
                                    node.getAttribute("resource_wo_event_field")
                                )
                            ) {
                                resourceWOEventField = fieldName;
                            }
                        }
                    }

                    break;
                }
            }
        });

        return {
            canCreate,
            canDelete,
            canEdit,
            eventLimit,
            fieldMapping,
            fieldNames: [...fieldNames],
            filtersInfo,
            formViewId,
            hasEditDialog,
            quickCreate,
            quickCreateViewId,
            isDateHidden,
            isTimeHidden,
            isTimeEndHidden,
            eventTimeDisplayFar,
            eventTimeFormatDigits,
            isDateTimeScale,
            scaleHours,
            popoverFieldNodes,
            scale,
            scales,
            showUnusualDays,
            // Start custom here
            resourceWidth,
            resourceOrder,
            slotMinWidth,
            resourceGroupField,
            columnFields,
            label,
            eventTitleField,
            hideEventTitle,
            slotLabelFormat,
            resourceWOEventField,
            viewMoreOptions,
            minResourceHeight,
            // End custom
        };
    }
}
