/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class TierIconPickerField extends Component {
    static template = "hhs_loyalty_management.TierIconPicker";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ icons: [] });

        onWillStart(async () => {
            const icons = await this.orm.searchRead(
                "loyalty.tier.icon",
                [["active", "=", true]],
                ["id", "name", "fa_icon", "color"],
                { order: "sequence asc, name asc" }
            );
            this.state.icons = icons;
        });
    }

    get value() {
        const val = this.props.record.data[this.props.name];
        if (!val) return false;
        return Array.isArray(val) ? val[0] : (val.id || val);
    }

    getSelectedIcon() {
        if (!this.value) return false;
        return this.state.icons.find(i => i.id === this.value) || false;
    }

    selectIcon(icon) {
        if (!this.props.readonly) {
            if (this.value === icon.id) {
                this.props.record.update({ [this.props.name]: false });
            } else {
                this.props.record.update({ [this.props.name]: [icon.id, icon.name] });
            }
        }
    }
}

export const tierIconPickerField = {
    component: TierIconPickerField,
    supportedTypes: ["many2one"],
};

registry.category("fields").add("tier_icon_picker", tierIconPickerField);
