/** @odoo-module **/

/**
 * Left panel of the Menu Access Rights page: the user picker.
 *
 * Two widgets, both registered only for that one form (see
 * views/menu_access_matrix_views.xml), so nothing here can run elsewhere:
 *
 *   mar_user_cell       — avatar initials + name + email in one cell.
 *                         Rendered from plain data rather than a
 *                         server-built Html field, because the stock "html"
 *                         widget sets the cell's tooltip to the field's raw
 *                         value, which showed literal "<div class=…>" markup
 *                         on hover.
 *   mar_user_list_field — the list itself: filters rows against the plain
 *                         DOM search box above it, marks the selected row,
 *                         and makes a whole row clickable to switch the
 *                         right-hand panel to that user.
 */

import { registry } from "@web/core/registry";
import { charField } from "@web/views/fields/char/char_field";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import { Component, xml, onMounted, onWillUnmount } from "@odoo/owl";

const MAR_USER_SEARCH_SELECTOR = ".mar_matrix_form .mar_user_search_box";
const MAR_USER_SEARCH_DEBOUNCE_MS = 150;

// ---------------------------------------------------------------------------
// Cell: avatar + name + email
// ---------------------------------------------------------------------------
class MarUserCellField extends Component {
    static template = xml`
        <div class="mar_user_cell">
            <div class="mar_avatar" t-esc="initials"/>
            <div class="mar_user_text">
                <div class="mar_user_name" t-esc="props.record.data.user_name"/>
                <div class="mar_user_email" t-esc="props.record.data.user_email"/>
            </div>
        </div>
    `;
    static props = ["record", "readonly?", "*"];

    get initials() {
        const name = this.props.record.data.user_name || "?";
        return name.trim().split(/\s+/).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
    }
}

registry.category("fields").add("mar_user_cell", {
    ...charField,
    component: MarUserCellField,
});

// ---------------------------------------------------------------------------
// List: filter + select
// ---------------------------------------------------------------------------
class MarUserListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this._onUserSearchInput = () => {
            clearTimeout(this._userSearchTimer);
            this._userSearchTimer = setTimeout(() => this.render(), MAR_USER_SEARCH_DEBOUNCE_MS);
        };
        onMounted(() => {
            this._userSearchEl = document.querySelector(MAR_USER_SEARCH_SELECTOR);
            if (this._userSearchEl) {
                this._userSearchEl.addEventListener("input", this._onUserSearchInput);
            }
        });
        onWillUnmount(() => {
            clearTimeout(this._userSearchTimer);
            if (this._userSearchEl) {
                this._userSearchEl.removeEventListener("input", this._onUserSearchInput);
            }
        });
    }

    _marUserQuery() {
        if (!this._userSearchEl || !this._userSearchEl.isConnected) {
            this._userSearchEl = document.querySelector(MAR_USER_SEARCH_SELECTOR);
        }
        return ((this._userSearchEl && this._userSearchEl.value) || "").trim().toLowerCase();
    }

    getRowClass(record) {
        let classes = super.getRowClass(record) || "";
        if (record.data.is_selected) {
            classes += " mar_user_selected";
        }
        const query = this._marUserQuery();
        if (!query) {
            return classes;
        }
        const name = (record.data.user_name || "").toLowerCase();
        const email = (record.data.user_email || "").toLowerCase();
        return name.includes(query) || email.includes(query) ? classes : `${classes} d-none`;
    }

    /**
     * Click anywhere on a user row to load that user on the right.
     *
     * Goes straight to the ORM rather than through an Odoo <button>: a
     * type="object" button force-saves the form first, and this list sits in
     * the same form as the (editable) menu tree, so an in-progress edit would
     * be committed just because someone clicked a different user.
     */
    async onCellClicked(record, column, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const root = record.model.root;
        const userId = Array.isArray(record.data.user_id)
            ? record.data.user_id[0]
            : record.data.user_id;
        if (!userId || !root.resId) {
            return;
        }
        // Drop any pending form state BEFORE switching. Selecting a user
        // replaces the whole menu tree server-side, so edits still staged
        // against the previous user's rows would otherwise be saved against
        // the incoming user — the corruption path guarded server-side in
        // menu.access.matrix.line._propagate_to_rights. Nothing is lost:
        // toggles already persist the moment they're clicked, so a dirty
        // form here only ever holds the "row is being edited" marker.
        if (typeof root.discard === "function") {
            await root.discard();
        }
        await record.model.orm.call(
            "menu.access.matrix", "action_select_user", [[root.resId], userId],
        );
        await root.load();
    }
}

class MarUserListField extends X2ManyField {}
MarUserListField.components = {
    ...X2ManyField.components,
    ListRenderer: MarUserListRenderer,
};

registry.category("fields").add("mar_user_list_field", {
    ...x2ManyField,
    component: MarUserListField,
});
