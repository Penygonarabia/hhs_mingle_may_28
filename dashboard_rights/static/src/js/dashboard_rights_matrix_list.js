/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { BooleanToggleField, booleanToggleField } from "@web/views/fields/boolean_toggle/boolean_toggle_field";
import { useState, onWillUpdateProps, onWillStart, onMounted, onWillUnmount, xml } from "@odoo/owl";

/**
 * "Has Access" toggle widget.
 *
 * Dashboard (child) rows behave like a normal boolean_toggle. Group (menu) rows
 * act as a reactive MASTER toggle:
 *   - displayed state is derived live from the children (ON only when every
 *     dashboard under the menu is ON) — so manually toggling dashboards rolls
 *     up to the group row automatically;
 *   - clicking it cascades the new value to every dashboard in the group.
 *
 * Everything is client-side and reactive (it reads the sibling rows during
 * render, like the count widget), so there is no server onchange round-trip and
 * no fragile "which side was toggled" detection — toggling ANY dashboard off
 * after a group-ON works reliably. Nothing is written until Save.
 */
class DrAccessToggleField extends BooleanToggleField {
    static components = { CheckBox };
    static template = xml`
        <CheckBox id="props.id" value="checkboxValue"
                  className="'o_field_boolean o_boolean_toggle form-switch'"
                  disabled="props.readonly" onChange.bind="onChange">&#8203;</CheckBox>
    `;

    get isGroupRow() {
        return !!this.props.record.data.is_group;
    }

    siblingChildren() {
        const rec = this.props.record;
        const root = rec.model.root;
        const all = (root.data.line_ids && root.data.line_ids.records) || [];
        return all.filter(
            (r) => r.data.menu_name === rec.data.menu_name && !r.data.is_group
        );
    }

    get checkboxValue() {
        if (this.isGroupRow) {
            // Group row: derived live from the dashboards (reactive read).
            const kids = this.siblingChildren();
            return kids.length > 0 && kids.every((r) => r.data.has_access);
        }
        // Dashboard row: the parent class keeps `state.value` synced with the
        // record and updates it optimistically on toggle, which is what makes a
        // single click register in the editable list.
        return this.state.value;
    }

    async onChange(newValue) {
        if (this.isGroupRow) {
            // Master toggle: cascade to every dashboard in this group, then
            // commit the group row itself. The displayed value is derived from
            // the dashboards, so it re-renders as they update.
            this.state.value = newValue;
            for (const kid of this.siblingChildren()) {
                if (kid.data.has_access !== newValue) {
                    await kid.update({ has_access: newValue });
                }
            }
            await this.props.record.update(
                { [this.props.name]: newValue },
                { save: this.props.autosave }
            );
        } else {
            // Dashboard row: identical to the standard boolean_toggle (optimistic
            // state + save), so it toggles on the FIRST click.
            return super.onChange(newValue);
        }
    }
}

registry.category("fields").add("dr_access_toggle", {
    ...booleanToggleField,
    component: DrAccessToggleField,
});

/**
 * "Dashboard Name" column widget.
 *
 * For a dashboard row it shows the board name (the stored value). For a group
 * (menu) row it shows a LIVE "<granted> / <total>" count computed from the
 * sibling dashboard rows. Reading the siblings' has_access here makes the count
 * reactive: it updates the instant any row is toggled, with no server round-trip
 * and independent of onchange timing — and nothing is written until Save.
 */
class DrGroupCountField extends CharField {
    get formattedValue() {
        const rec = this.props.record;
        if (!rec.data.is_group) {
            return super.formattedValue;
        }
        const root = rec.model.root;
        const all = (root.data.line_ids && root.data.line_ids.records) || [];
        const menu = rec.data.menu_name;
        const kids = all.filter((r) => r.data.menu_name === menu && !r.data.is_group);
        const granted = kids.filter((r) => r.data.has_access).length;
        return `${granted} / ${kids.length}`;
    }
}

registry.category("fields").add("dr_group_count", {
    ...charField,
    component: DrGroupCountField,
});

class DashboardRightsMatrixListRenderer extends ListRenderer {
    setup() {
        super.setup();

        // Use a dedicated property for collapsed state to avoid overwriting this.state
        // which contains the column definitions initialized in super.setup()
        this.collapsedState = useState({
            collapsed: {},
        });

        onWillStart(() => {
            this.initializeCollapsedState(this.props.list.records);
        });

        onWillUpdateProps((nextProps) => {
            this.initializeCollapsedState(nextProps.list.records);
        });

        // The Dashboards tree is bound directly to line_ids (so Save/Discard
        // work natively), which means search filtering is done here in the
        // renderer. Re-render the list as the user types in the search box.
        this._onSearchInput = () => this.render();
        onMounted(() => {
            this._searchEl =
                document.querySelector(".dr_matrix_form input[name='search_text']") ||
                document.querySelector(".dr_matrix_form input[placeholder*='Search by Menu']");
            if (this._searchEl) {
                this._searchEl.addEventListener("input", this._onSearchInput);
            }
        });
        onWillUnmount(() => {
            if (this._searchEl) {
                this._searchEl.removeEventListener("input", this._onSearchInput);
            }
        });
    }

    initializeCollapsedState(records) {
        for (const record of records || []) {
            const menuName = record.data.menu_name;
            if (menuName && this.collapsedState.collapsed[menuName] === undefined) {
                // Default to collapsed (true)
                this.collapsedState.collapsed[menuName] = true;
            }
        }
    }

    getRowClass(record) {
        let classes = super.getRowClass(record) || "";
        const isParent = !!record.data.is_group;
        const menuName = record.data.menu_name;

        // Check if a search filter is currently active in the input field
        const searchInput = document.querySelector(".dr_matrix_form input[placeholder*='Search by Menu']") ||
                            document.querySelector(".dr_matrix_form input[name='search_text']");
        const query = (searchInput && searchInput.value || "").trim().toLowerCase();
        const isSearching = query !== "";

        if (isParent) {
            classes += " dr_parent_row";
            if (this.collapsedState.collapsed[menuName] && !isSearching) {
                classes += " dr_collapsed";
            }
        } else {
            classes += " dr_child_row";
            if (this.collapsedState.collapsed[menuName] && !isSearching) {
                classes += " d-none";
            }
        }

        // Client-side search: hide rows whose Menu or Dashboard Name doesn't
        // match the query (mirrors the previous server-side filter).
        if (isSearching) {
            const name = (record.data.dashboard_name || "").toLowerCase();
            const menu = (menuName || "").toLowerCase();
            if (!menu.includes(query) && !name.includes(query)) {
                classes += " d-none";
            }
        }
        return classes;
    }

    async onCellClicked(record, column, ev) {
        // Bypass collapse/expand toggling if clicking the Has Access checkbox cell
        if (ev.target.closest(".o_boolean_toggle") || ev.target.closest(".o_field_boolean") || (column && column.name === "has_access")) {
            return super.onCellClicked(record, column, ev);
        }

        const isParent = !!record.data.is_group;
        if (isParent) {
            const menuName = record.data.menu_name;
            this.collapsedState.collapsed[menuName] = !this.collapsedState.collapsed[menuName];
            ev.stopPropagation();
            return;
        }

        return super.onCellClicked(record, column, ev);
    }
}

class DashboardRightsMatrixListField extends X2ManyField {}
DashboardRightsMatrixListField.components = {
    ...X2ManyField.components,
    ListRenderer: DashboardRightsMatrixListRenderer,
};

registry.category("fields").add("dashboard_rights_matrix_list_field", {
    ...x2ManyField,
    component: DashboardRightsMatrixListField,
});
