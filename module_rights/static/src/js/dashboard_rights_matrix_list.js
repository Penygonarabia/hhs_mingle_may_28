/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { BooleanToggleField, booleanToggleField } from "@web/views/fields/boolean_toggle/boolean_toggle_field";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, useEffect, onMounted, onWillUnmount, xml } from "@odoo/owl";

/**
 * A many2one field's value in record.data is `[id, display_name]` or
 * `false` (see relational_model/utils.js's many2one handling) — never a
 * bare id. Unwrap to the id (or `false`).
 */
function dr_m2oId(value) {
    return Array.isArray(value) ? value[0] : false;
}

/**
 * Compute every record in `siblings` (one app's flat menu-tree rows) that
 * must change alongside `target` when its Has Access is set to `value`, so
 * toggling ANY menu/sub-menu keeps the whole tree internally consistent:
 *
 *   - Turning a row ON also turns ON every ANCESTOR — a granted sub-menu
 *     is not actually reachable if its parent menu is hidden (see
 *     ir_ui_menu._dr_restricted_menu_ids' walk-up: a menu with no visible
 *     children gets hidden regardless of its own grant), so the parent
 *     chain has to come along.
 *   - Turning a row ON or OFF always cascades to every DESCENDANT — a
 *     folder's own toggle is a real bulk grant/revoke for everything
 *     under it, not just itself.
 *
 * Returns only the records whose has_access actually differs from `value`
 * (target included), so callers don't write rows that already match.
 * Falls back to just `target` when `parent_menu_id` isn't part of this
 * model's data at all (Users Setup's dashboard/Quick-Access/Configuration
 * groups are deliberately flat 1-level lists — there is no tree to walk).
 */
function drCascadeTargets(target, siblings, value) {
    if (target.data.parent_menu_id === undefined) {
        return target.data.has_access === value ? [] : [target];
    }
    const byMenuId = new Map();
    const byParentId = new Map();
    for (const rec of siblings) {
        const mid = dr_m2oId(rec.data.menu_id);
        if (!mid) {
            continue;
        }
        byMenuId.set(mid, rec);
        const pid = dr_m2oId(rec.data.parent_menu_id) || 0;
        if (!byParentId.has(pid)) {
            byParentId.set(pid, []);
        }
        byParentId.get(pid).push(rec);
    }

    const result = new Map();
    const include = (rec) => {
        if (rec.data.has_access !== value) {
            result.set(rec.id, rec);
        }
    };
    include(target);

    let frontier = byParentId.get(dr_m2oId(target.data.menu_id) || 0) || [];
    while (frontier.length) {
        const next = [];
        for (const rec of frontier) {
            include(rec);
            next.push(...(byParentId.get(dr_m2oId(rec.data.menu_id) || 0) || []));
        }
        frontier = next;
    }

    if (value) {
        let cur = target;
        const seen = new Set();
        while (true) {
            const parentId = dr_m2oId(cur.data.parent_menu_id);
            if (!parentId || seen.has(parentId)) {
                break;
            }
            seen.add(parentId);
            const parent = byMenuId.get(parentId);
            if (!parent) {
                break;
            }
            include(parent);
            cur = parent;
        }
    }

    return [...result.values()];
}

/**
 * Sets `has_access = value` on every record in `records`.
 *
 * A single record goes through the normal `record.update(..., {save:
 * true})` — one RPC, and the widget's own reactive state stays correctly
 * bound to that record.
 *
 * Multiple records (a folder toggle cascading to a whole subtree, or
 * Grant All / Revoke All on a big app) are sent as ONE `action_bulk_set_access`
 * RPC instead of one `update()` per record. Firing N `update()` calls at
 * once (even via Promise.all) looks harmless but isn't: every write for a
 * KS board also re-reads and conditionally creates/updates a SECOND row
 * server-side (dashboard.rights.menu._dr_sync_board_and_menu, which keeps
 * a board's dashboard.rights row in lockstep with its
 * dashboard.rights.menu row). Concurrent requests each get their own
 * transaction, so two overlapping "does this row already exist" reads can
 * both see "no" before either commits its create — one write silently
 * wins and the other's board-level sync is lost. This was reproduced
 * empirically: cascading ~20 rows via Promise.all dropped exactly one
 * board's sync. Sending them as a single server-side write() instead runs
 * every row sequentially inside ONE transaction, so there's nothing left
 * to race, and it's one round-trip instead of N. The root record is
 * reloaded afterward so the client's in-memory rows pick up the change —
 * `record.update()` handles that itself for the single-record path.
 */
async function drApplyCascade(records, value) {
    if (!records.length) {
        return;
    }
    if (records.length === 1) {
        await records[0].update({ has_access: value }, { save: true });
        return;
    }
    const model = records[0].model;
    await model.orm.call(
        records[0].resModel,
        "action_bulk_set_access",
        [records.map((r) => r.resId), value]
    );
    await model.root.load();
}

/**
 * "Has Access" toggle widget.
 *
 * Dashboard (child) rows behave like a normal boolean_toggle: a single click
 * writes straight through.
 *
 * Group (menu) rows are READ-ONLY here — a status indicator only:
 *   - checked only when every dashboard in the menu is granted;
 *   - unchecked when none are;
 *   - "indeterminate" (a dash, native checkbox behavior) when some but not
 *     all are granted, so a partially-granted menu is visually distinct from
 *     a fully-revoked one at a glance.
 * Granting/revoking a whole menu happens exclusively in the group-children
 * popup now (see DrGroupChildrenDialog below) — there is no cascade-on-click
 * here anymore. That removes the one entry point (this toggle) that used to
 * have to independently agree with the popup on what "the group's state" is;
 * now there is exactly one place that mutates a group's dashboards.
 *
 * Group rows render a plain, inert checkbox (no <CheckBox> component) rather
 * than a disabled interactive one: <CheckBox>'s own click handler always
 * calls stopPropagation() when the click lands on the input/label, REGARDLESS
 * of its disabled state, which would swallow a click meant to bubble up and
 * open the group-children popup (a small but real "dead zone" exactly over
 * the switch graphic, confirmed while testing). A bare, non-component input
 * has no click handling of its own, so every point in the cell reliably
 * bubbles to the row and opens the popup.
 */
class DrAccessToggleField extends BooleanToggleField {
    static components = { CheckBox };
    static template = xml`
        <div t-ref="dr_toggle_root">
            <t t-if="isGroupRow">
                <div class="o-checkbox form-check o_field_boolean o_boolean_toggle form-switch">
                    <input type="checkbox" class="form-check-input" t-att-checked="checkboxValue" disabled="disabled"/>
                </div>
            </t>
            <t t-else="">
                <CheckBox id="props.id" value="checkboxValue"
                          className="'o_field_boolean o_boolean_toggle form-switch'"
                          disabled="isLocked" onChange.bind="onChange">&#8203;</CheckBox>
            </t>
        </div>
    `;

    setup() {
        super.setup();
        this.dr_toggleRootRef = useRef("dr_toggle_root");
        // Native checkboxes support a third visual state (a dash) via the
        // `.indeterminate` DOM property — there is no template attribute for
        // it, so it has to be set imperatively whenever the derived group
        // state is "some but not all granted".
        useEffect(
            () => {
                const input = this.dr_toggleRootRef.el && this.dr_toggleRootRef.el.querySelector("input");
                if (input) {
                    input.indeterminate = this.isPartial;
                }
            },
            () => [this.checkboxValue, this.isPartial]
        );
    }

    get isGroupRow() {
        return !!this.props.record.data.is_group;
    }

    get isLocked() {
        // Group rows are always a read-only status indicator now (granting/
        // revoking happens only in the popup). Dashboard rows are locked only
        // when the configured user is an admin (forced ON everywhere).
        return this.isGroupRow || !!this.props.record.data.is_user_admin;
    }

    siblingChildren() {
        const rec = this.props.record;
        const root = rec.model.root;
        const all = (root.data.line_ids && root.data.line_ids.records) || [];
        return all.filter(
            (r) => r.data.menu_name === rec.data.menu_name && !r.data.is_group
        );
    }

    get isPartial() {
        if (!this.isGroupRow) {
            return false;
        }
        const kids = this.siblingChildren();
        const granted = kids.filter((r) => r.data.has_access).length;
        return granted > 0 && granted < kids.length;
    }

    get checkboxValue() {
        if (this.isGroupRow) {
            // Group row: derived live from the dashboards (reactive read).
            const kids = this.siblingChildren();
            return kids.length > 0 && kids.every((r) => r.data.has_access);
        }
        // Dashboard row: the parent class keeps `state.value` synced with the
        // record and updates it optimistically on toggle, which is what makes a
        // single click register instantly.
        return this.state.value;
    }

    async onChange(newValue) {
        // Group rows are always isLocked (disabled), so this only ever fires
        // for an individual dashboard row (reached via the search-filtered
        // inline view). Cascades to ancestors/descendants exactly like the
        // group-children popup (see drCascadeTargets) so a menu granted via
        // search and one granted via the popup behave identically.
        this.state.value = newValue;
        const targets = drCascadeTargets(this.props.record, this.siblingChildren(), newValue);
        await drApplyCascade(targets, newValue);
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

/**
 * Popup opened by clicking a group (menu) row: lists just that menu's
 * dashboards with a checkbox each, plus Grant All / Revoke All. This is now
 * the ONLY place a group's dashboards are granted/revoked from (the main
 * table's own group-row toggle is read-only — see DrAccessToggleField above).
 *
 * IMPORTANT: this dialog does NOT hold a snapshot array of child records.
 * An earlier version captured `props.children` as a plain array built once
 * when the dialog opened; that array (and the CheckBox bindings reading it)
 * never re-rendered after a write, even though the write itself succeeded and
 * the MAIN table (which always re-derives fresh on every render) showed the
 * correct state — confirmed empirically: after clicking Revoke All, the
 * underlying DOM `input.checked` for every row inside the dialog was still
 * literally `true`, i.e. Owl never re-rendered this component at all, while
 * the main table's group row correctly dropped to "0 / 15" and the database
 * write had genuinely happened. Passing a detached snapshot array into a
 * dialog-service-mounted component is fragile — it isn't part of the normal
 * view/renderer component tree that Odoo's own reactivity plumbing is set up
 * for.
 *
 * Fix: (1) `children` is a getter that re-derives the list fresh from the
 * root record on every access, exactly like DrAccessToggleField.siblingChildren()
 * and DrGroupCountField.formattedValue already do reliably elsewhere in this
 * file; and (2) belt-and-suspenders, every mutating action explicitly calls
 * this.render() afterward so the popup's own visual state is guaranteed
 * correct regardless of whatever exact Owl-reactivity subtlety caused the
 * original bug — don't rely solely on implicit tracking across the dialog
 * service boundary.
 */
class DrGroupChildrenDialog extends Component {
    static components = { Dialog, CheckBox };
    static props = ["title", "menuName", "rootRecord", "isUserAdmin", "close"];
    static template = xml`
        <Dialog title="props.title" size="'md'">
            <div class="dr_group_dialog">
                <div class="dr_group_dialog_summary text-muted mb-2">
                    <t t-esc="grantedCount"/> / <t t-esc="children.length"/> granted
                </div>
                <div class="dr_group_dialog_actions mb-2" t-if="!props.isUserAdmin">
                    <button class="btn btn-sm btn-outline-success me-2"
                            t-att-disabled="busyState.busy || allGranted"
                            t-on-click="() => this.setAll(true)">Grant All</button>
                    <button class="btn btn-sm btn-outline-danger"
                            t-att-disabled="busyState.busy || noneGranted"
                            t-on-click="() => this.setAll(false)">Revoke All</button>
                </div>
                <table class="table table-sm dr_group_dialog_table mb-0">
                    <tbody>
                        <t t-foreach="treeRows" t-as="row" t-key="row.child.id">
                            <tr>
                                <td class="dr_group_dialog_name"
                                    t-attf-style="padding-left: {{row.depth * 20}}px;"
                                    t-att-class="row.hasChildren ? 'fw-bold' : ''">
                                    <t t-esc="row.child.data.dashboard_name"/>
                                </td>
                                <td class="dr_group_dialog_toggle text-end">
                                    <CheckBox
                                        value="row.child.data.has_access"
                                        disabled="props.isUserAdmin or busyState.busy"
                                        onChange.bind="(val) => this.onToggle(row.child, val)"
                                        className="'o_field_boolean o_boolean_toggle form-switch'">&#8203;</CheckBox>
                                </td>
                            </tr>
                        </t>
                    </tbody>
                </table>
            </div>
            <t t-set-slot="footer">
                <button class="btn btn-primary" t-on-click="() => props.close()">Close</button>
            </t>
        </Dialog>
    `;

    setup() {
        this.busyState = useState({ busy: false });
    }

    get children() {
        const list = this.props.rootRecord.data.line_ids;
        const all = (list && list.records) || [];
        return all.filter(
            (r) => r.data.menu_name === this.props.menuName && !r.data.is_group
        );
    }

    /**
     * A many2one field's value in record.data is `[id, display_name]` or
     * `false` (see relational_model/utils.js's `fromXmlSerializedForm` /
     * `getFieldsSpec` many2one handling) — never a bare id. Unwrap to the id
     * (or `false`) so it can be used as a plain Map key / Set member.
     */
    _m2oId(value) {
        return Array.isArray(value) ? value[0] : false;
    }

    /**
     * `children` in real menu-tree order (depth-first, matching each
     * node's REAL parent — see access.rights.module.matrix.line.parent_menu_id
     * — not the flat "one big group" order it's stored in). Falls back to a
     * flat list (all depth 0) when `parent_menu_id` isn't a field on this
     * model at all (dashboard.rights.matrix.line — Users Setup's boards/
     * Quick-Access/Configuration groups are deliberately already flat
     * 1-level lists, so there is no tree to build there).
     */
    get treeRows() {
        const kids = this.children;
        if (!kids.length || kids[0].data.parent_menu_id === undefined) {
            return kids.map((child) => ({ child, depth: 0, hasChildren: false }));
        }
        const byParent = new Map();
        for (const child of kids) {
            const key = this._m2oId(child.data.parent_menu_id) || 0;
            if (!byParent.has(key)) {
                byParent.set(key, []);
            }
            byParent.get(key).push(child);
        }
        const menuIds = new Set(kids.map((c) => this._m2oId(c.data.menu_id)).filter(Boolean));
        const roots = kids.filter((child) => {
            const parentId = this._m2oId(child.data.parent_menu_id);
            return !parentId || !menuIds.has(parentId);
        });
        const rows = [];
        const visit = (child, depth) => {
            const ownChildren = byParent.get(this._m2oId(child.data.menu_id) || 0) || [];
            rows.push({ child, depth, hasChildren: ownChildren.length > 0 });
            for (const kid of ownChildren) {
                visit(kid, depth + 1);
            }
        };
        for (const root of roots) {
            visit(root, 0);
        }
        return rows;
    }

    get grantedCount() {
        return this.children.filter((c) => c.data.has_access).length;
    }

    get allGranted() {
        const kids = this.children;
        return kids.length > 0 && kids.every((c) => c.data.has_access);
    }

    get noneGranted() {
        return this.children.every((c) => !c.data.has_access);
    }

    async onToggle(child, value) {
        if (this.busyState.busy) {
            return;
        }
        this.busyState.busy = true;
        try {
            // See drCascadeTargets: ON also grants every ancestor (so the
            // toggled row stays reachable), and either direction also
            // cascades to every descendant (a folder's own toggle is a
            // real bulk grant/revoke for everything under it).
            const targets = drCascadeTargets(child, this.children, value);
            await drApplyCascade(targets, value);
        } finally {
            this.busyState.busy = false;
            this.render();
        }
    }

    async setAll(value) {
        if (this.busyState.busy) {
            return;
        }
        this.busyState.busy = true;
        try {
            const kids = this.children.filter((c) => c.data.has_access !== value);
            await drApplyCascade(kids, value);
        } finally {
            this.busyState.busy = false;
            this.render();
        }
    }
}

class DashboardRightsMatrixListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");

        // The Dashboards tree is bound directly to line_ids (so Save/Discard
        // work natively), which means search filtering is done here in the
        // renderer. Re-render the list as the user types in the search box.
        this._onSearchInput = () => this.render();
        onMounted(() => {
            this._searchEl = document.querySelector(".dr_matrix_form .dr_matrix_search_input input");
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

    getRowClass(record) {
        let classes = super.getRowClass(record) || "";
        const isParent = !!record.data.is_group;
        const menuName = record.data.menu_name;

        // Check if a search filter is currently active in the input field
        const searchInput = document.querySelector(".dr_matrix_form .dr_matrix_search_input input");
        const query = (searchInput && searchInput.value || "").trim().toLowerCase();
        const isSearching = query !== "";

        if (isParent) {
            // Group rows are always shown collapsed (the caret always reads
            // "▶", i.e. "click for details") — child rows are no longer
            // expanded inline; a click on the row opens the details dialog
            // instead (see onCellClicked below).
            classes += " dr_parent_row";
            if (!isSearching) {
                classes += " dr_collapsed";
            }
        } else {
            classes += " dr_child_row";
            if (!isSearching) {
                classes += " d-none";
            }
        }

        // Client-side search: hide rows whose Menu or Dashboard Name doesn't
        // match the query (mirrors the previous server-side filter). While
        // searching, matching child rows are shown inline (there's no group
        // to open a dialog against for a filtered result).
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
        const isParent = !!record.data.is_group;
        if (!isParent) {
            // Dashboard (child) rows — reachable via search — keep their
            // simple, independent toggle; no group/popup logic involved.
            return super.onCellClicked(record, column, ev);
        }

        // Group rows are read-only for Has Access (DrAccessToggleField always
        // disables them) — ANY click on the row, the toggle cell included,
        // opens the popup instead. No more special-casing the has_access
        // column: there's nothing for a direct click on it to do on its own.
        ev.stopPropagation();
        const menuName = record.data.menu_name;
        this.dialogService.add(DrGroupChildrenDialog, {
            title: menuName,
            menuName,
            rootRecord: record.model.root,
            isUserAdmin: !!record.data.is_user_admin,
        });
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
