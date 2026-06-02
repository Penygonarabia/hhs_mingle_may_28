/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, xml, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class ChecklistAnswerField extends Component {
    static template = xml`
        <div class="hhs_checklist_answer w-100" style="min-width: 250px;">
            <t t-if="['yes_no', 'condition', 'multiple'].includes(props.record.data.field_type)">
                <div class="d-flex flex-wrap gap-2">
                    <t t-foreach="parsedOptions" t-as="opt" t-key="opt.id">
                        <div class="form-check form-check-inline m-0 p-2 border rounded-pill d-flex align-items-center shadow-sm me-2 mb-2" 
                             t-att-class="isSelected(opt.id) ? 'bg-primary-subtle border-primary' : 'bg-white'"
                             style="cursor: pointer; min-height: 2.5rem;"
                             t-on-click.stop.prevent="() => this.onOptionChange(opt.id, opt.name)">
                            <input class="form-check-input ms-1" 
                                   style="pointer-events: none; width: 1.4rem; height: 1.4rem;"
                                   type="radio" 
                                   t-att-name="'answer_' + props.record.id"
                                   t-att-checked="isSelected(opt.id)"
								   t-att-disabled="isReadonly"
								   />
                            <label class="form-check-label ms-2 me-2 mb-0 fw-bold" 
                                   style="pointer-events: none;">
                                <t t-out="opt.name"/>
                            </label>
                        </div>
                    </t>
                </div>
            </t>
            <t t-elif="['numeric', 'calculated'].includes(props.record.data.field_type)">
                <div class="text-start d-flex justify-content-start align-items-center" t-on-click.stop="">
                    <input type="number" 
                           class="o_input form-control" 
                           style="max-width: 150px;"
                           t-att-value="props.record.data.answer_numeric || ''"
                           t-att-disabled="isReadonly || props.record.data.field_type === 'calculated'"
                           t-on-change="(ev) => this.onNumericChange(ev)"
                           t-on-click.stop=""/>
                </div>
            </t>
            <t t-elif="props.record.data.field_type === 'text'">
                <div class="text-start" t-on-click.stop="">
                    <input type="text" 
                           class="o_input form-control w-100"
                           t-att-value="props.record.data.answer_text || ''"
						   t-att-disabled="isReadonly"
                           t-on-change="(ev) => this.onTextChange(ev)"
                           t-on-click.stop=""/>
                </div>
            </t>
        </div>
    `;

    setup() {
        this.orm = useService("orm");
        this.state = useState({ selectedId: this._getCurrentSelectionId() });
    }

    _getCurrentSelectionId() {
        const val = this.props.record.data.answer_selection_id;
        if (!val) return false;
        if (Array.isArray(val)) return val[0];
        if (typeof val === 'object' && val.id) return val.id;
        return val;
    }
	
	get isReadonly() {
	    return ["101", "102", "103","104","107","108","109","110","111","154","126"].includes(
	        String(this.props.record.data.job_card_state_code || "")
	    );
	}

    isSelected(optionId) {
        // Use local state first for instant feedback, fall back to record data
        if (this.state && this.state.selectedId) {
            return this.state.selectedId === optionId;
        }
        return this._getCurrentSelectionId() === optionId;
    }

    async onOptionChange(optionId, optionName) {
        // NEVER check props.readonly here — Kanban always passes readonly=true
        // but we still need to allow selection for checklist answers.
        
		
		if (this.isReadonly) {
		       return;
		   }
        // Instant UI feedback via local state
        this.state.selectedId = optionId;

        const record = this.props.record;

        // Try the standard Odoo record update first (works in tree/form views)
        try {
            await record.update({
                answer_selection_id: optionId ? [optionId, optionName || ""] : false,
            });
        } catch (e) {
            // If standard update fails (e.g. readonly kanban), use direct ORM write
            console.log("Standard update blocked, using direct ORM write");
        }

        // Always do a direct ORM write to guarantee persistence
        const resId = record.resId;
        if (resId) {
            try {
                await this.orm.write("jobcard.checklist.line", [resId], {
                    answer_selection_id: optionId || false,
                });
            } catch (err) {
                console.error("ORM write failed:", err);
            }
        }
    }

    async onNumericChange(ev) {
		
		if (this.isReadonly) {
		       return;
		   }
		
        const value = parseFloat(ev.target.value) || 0;
        const record = this.props.record;
        try {
            await record.update({ answer_numeric: value });
        } catch (e) {
            console.log("Standard update blocked for numeric");
        }
        if (record.resId) {
            try {
                await this.orm.write("jobcard.checklist.line", [record.resId], {
                    answer_numeric: value,
                });
            } catch (err) {
                console.error("Numeric ORM write failed:", err);
            }
        }
    }

    async onTextChange(ev) {
		if (this.isReadonly) {
		        return;
		    }
        const value = ev.target.value || "";
        const record = this.props.record;
        try {
            await record.update({ answer_text: value });
        } catch (e) {
            console.log("Standard update blocked for text");
        }
        if (record.resId) {
            try {
                await this.orm.write("jobcard.checklist.line", [record.resId], {
                    answer_text: value,
                });
            } catch (err) {
                console.error("Text ORM write failed:", err);
            }
        }
    }

    get parsedOptions() {
        const data = this.props.record.data.option_labels_data || "";
        if (!data) return [];
        return data.split('|').map(str => {
            const [id, name] = str.split(':');
            return { id: parseInt(id), name };
        });
    }

    static props = { ...standardFieldProps };
}

export const checklistAnswer = { component: ChecklistAnswerField };
registry.category("fields").add("checklist_answer", checklistAnswer);
