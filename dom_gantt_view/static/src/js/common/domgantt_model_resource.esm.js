/** @odoo-module **/

import {Component} from "@odoo/owl";
import {Field} from "@web/views/fields/field";
import {Record} from "@web/model/record";

export class DomGanttModelResource extends Component {}
DomGanttModelResource.components = {
    Field,
    Record,
};
DomGanttModelResource.template = "domGantt.ModelResource";
DomGanttModelResource.props = {
    record: Object,
    model: Object,
    fieldName: String,
};
