/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

let nextId = 0;

export class JobTypeRadioField extends Component {
    static template = "machine_repair_management.JobTypeRadioField";

    static props = {
        ...standardFieldProps,
        orientation: { type: String, optional: true },
        label: { type: String, optional: true },
        domain: { type: Array, optional: true },
    };

    static defaultProps = {
        orientation: "vertical",
    };

    setup() {
        this.id = `job_type_radio_${nextId++}`;
        this.type = this.props.record.fields[this.props.name].type;
		
        if (this.type === "many2one") {
            this.specialData = useSpecialData(async (orm, props) => {
                const { relation } = props.record.fields[props.name];
                const kwargs = {
                    specification: { display_name: 1 },
                    domain: props.domain,
                };
                const { records } = await orm.call(
                    relation,
                    "web_search_read",
                    [],
                    kwargs
                );
                return records.map((r) => [r.id, r.display_name]);
            });
        }
    }

    get items() {
        if (this.type === "selection") {
            return this.props.record.fields[this.props.name].selection;
        }
        if (this.type === "many2one") {
            return this.specialData.data;
        }
        return [];
    }

    get value() {
        if (this.type === "selection") {
            return this.props.record.data[this.props.name];
        }
        if (this.type === "many2one") {
            return Array.isArray(this.props.record.data[this.props.name])
                ? this.props.record.data[this.props.name][0]
                : this.props.record.data[this.props.name];
        }
        return null;
    }
	
	get correctiveCount() {
	       return this.props.record.data.actual_corrective || "";
	   }

	   get preventiveCount() {
	       return this.props.record.data.actual_preventive || "";
	   }

    isDisabled(item) {
        if (
            this.props.name === "maintenance_type" &&
            item[0] === "preventive"
        ) {
            return true;
        }
        return this.props.readonly;
    }

    onChange(item) {
        if (this.isDisabled(item)) {
            return;
        }

        if (this.type === "selection") {
            this.props.record.update({
                [this.props.name]: item[0],
            });
        } else if (this.type === "many2one") {
            this.props.record.update({
                [this.props.name]: item,
            });
        }
    }
}

export const jobTypeRadioField = {
    component: JobTypeRadioField,
    displayName: _t("Radio"),
    supportedTypes: ["selection", "many2one"],
    supportedOptions: [
        {
            label: _t("Display horizontally"),
            name: "horizontal",
            type: "boolean",
        },
    ],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ options, string }, dynamicInfo) => ({
        orientation: options.horizontal ? "horizontal" : "vertical",
        label: string,
        domain: dynamicInfo.domain(),
    }),
};

registry.category("fields").add("job_type_radio", jobTypeRadioField);