# Users Setup — Existing Process / Flow

**Path:** Settings ▸ Dashboard Rights ▸ Users Setup
**Module:** `module_rights`
**Model:** `dashboard.rights`

---

## 1. Where it lives

| Element | XML ID | File |
|---|---|---|
| Menu (Settings) | `menu_dashboard_rights_by_user` ("Users Setup") | `views/dashboard_rights_menus.xml:16` |
| Menu (Technical mirror) | `menu_dashboard_rights_tech_by_user` | `views/dashboard_rights_menus.xml:62` |
| Action | `action_dashboard_rights_grid` (name "Users Setup") | `views/dashboard_rights_views.xml:149` |
| Tree view | `view_dashboard_rights_users_list` | `views/dashboard_rights_views.xml:7` |
| Form view | `view_dashboard_rights_form` | `views/dashboard_rights_views.xml:59` |
| Search view | `view_dashboard_rights_search` | `views/dashboard_rights_views.xml:98` |

- The action opens `tree,form` on `dashboard.rights`.
- The tree uses `js_class="dashboard_rights_list"`, with `create="0"` and `delete="0"`.
- **Access gating:** every menu requires group `module_rights.group_dashboard_rights_admin`.

---

## 2. What the page shows

A compact, **one-row-per-user** list with two visible columns:

| Column | Field | Source |
|---|---|---|
| User | `user_id` | Internal, non-shared, active user |
| Status | `access_status` | `"granted / total"` count of dashboards the user can access (e.g. `5 / 12`) |

- Default ordering: `user_id`.
- The module has no dependency on `machine_repair_management` (or any other app) — the earlier "User Role" column/grouping derived from its groups was removed in 17.0.2.0.3.

---

## 3. Data model & row synchronization

The page is backed by `dashboard.rights` — **one record per (user, dashboard)** pair, with `has_access` defaulting to `False`.

- On **every list load**, `web_search_read` calls `_sync_missing_records`, which materializes a `has_access=False` row for every active internal (non-share) user × every `ks_dashboard` board (excluding the "Service Analysis - New" board under My Dashboard). This guarantees every user appears for every dashboard.
- The admin user is intentionally **included** in the list, but admins (superuser or `base.group_system`) are always granted access via `_is_admin_user`, regardless of their stored rows.

---

## 4. The "unique users" collapse mechanism

The underlying data is per-(user, dashboard), so the compact view must show only one row per user. This is driven by the `unique_users_only` context flag:

- The action sets `unique_users_only: True` by default.
- When set, `web_search_read` collapses results to the **first record per user** (`models/dashboard_rights.py:304`).
- The JS controller `onOptionalFieldsChanged` toggles this flag dynamically: if the admin un-hides any optional column (`dashboard_top_menu_id`, `dashboard_id`, `has_access`), the list reloads **without** the flag, expanding back to all per-dashboard rows.

---

## 5. Interaction flow (JS — `static/src/js/dashboard_rights_list.js`)

- **Click a row** → calls `action_open_matrix`, which creates a `dashboard.rights.matrix` transient, loads all dashboards + the users tab for that user, and opens the **Dashboard Rights Setup** matrix wizard form (where per-dashboard grant/revoke actually happens).
- **Click the Has Access toggle** (when that optional column is shown) → passes through normally, flipping the boolean inline without navigating.
- **Click the Dashboard cell** → passes through for inline many2one editing.
- **"New" button** → overridden to open a blank matrix wizard (`action_new_wizard`) instead of creating a raw `dashboard.rights` record. Create/delete are otherwise disabled.

---

## 6. End-to-end flow

1. Admin opens **Settings ▸ Dashboard Rights ▸ Users Setup**.
2. List load auto-syncs missing (user, dashboard) rows, then collapses to one row per user, showing each user's "granted / total" status.
3. Admin clicks a user row → the **matrix wizard** opens, pre-loaded for that user, to grant/revoke individual dashboards.
4. Access decisions are enforced elsewhere via `user_has_dashboard_access` / `allowed_dashboard_ids`.

---

## 7. Notes

- Other groupings (By User / By Category / By Dashboard / Raw) and their actions exist in the same view file, but their sub-menus are **commented out**.
- Only **Users Setup** and the technical **Manage User Rights** wizard menu are currently active.

---

## 8. Required behavior — Matrix Wizard (Dashboard Rights Setup)

These requirements apply to the matrix wizard that opens when an admin clicks a user row in the Users Setup list.

### 8.1 Save-gated editing
1. The admin can change the `has_access` status of **any** dashboard at any time. Changes are held in the UI and are **persisted only when the Save button is clicked** — no toggle should write to the database immediately.

### 8.2 Refresh / revert
2. Clicking the **refresh icon button** (next to Save) **reverts all unsaved changes** back to the original status that was loaded when the wizard was opened.

### 8.3 Grant / Revoke all
3. **Grant Access to All** selects (`has_access = True`) **every** dashboard, regardless of its current selected/unselected state.
4. **Revoke Access from All** unselects (`has_access = False`) **every** dashboard, regardless of its current selected/unselected state.

### 8.4 Dashboards tab — group rows
5. In the **Dashboards** tab list, each **dashboard-menu (group) row** shows, in the **"Dashboard Name"** column, the group's selection status as **`selected count / total dashboards`** under that group (e.g. `3 / 8`).
6. Toggling the **group row's `has_access` control ON** selects **all** dashboards in that group.
7. Toggling the **group row's `has_access` control OFF** unselects **all** dashboards in that group.
8. When dashboards are selected/unselected **manually** within a group:
   - If **all** dashboards in the group are selected → the group row's `has_access` control shows as **selected**.
   - If **any one** dashboard in the group is unselected → the group row's `has_access` control shows as **unselected**.

### 8.5 Group order
9. The **dashboard-menu (group) rows** are listed in the **same order as they appear under the My Dashboard menu** (by menu sequence), not alphabetically. Current order: **My Dashboard → Service Dashboards - OT → Service Dashboards - CT → Promoter Dashboards → Contract Dashboards → Loyalty Dashboards**. Menus not found under My Dashboard sort last.

### 8.6 Scope — only My-Dashboard boards
10. The matrix lists **only dashboards that belong to the My Dashboard menu**: the special "My Dashboard" board and any board that has a top-menu. **Menu-less boards are excluded** — e.g. the standalone *"Actual vs Target"* board (its own menu sits outside My Dashboard) previously loaded as a menu-less "orphan" row that sorted last, right after the Loyalty group, making it look like a Loyalty entry. It no longer appears.

> Requirements 8.1–8.8 operate on the in-UI state only; nothing is committed to the database until **Save** is pressed (per 8.1), and **Refresh** discards them (per 8.2).

---

## 9. Implementation notes (how 8.1–8.8 are built)

Implemented in module version `17.0.1.0.8`.

- **Save-gating + Discard (8.1, 8.2):** the Dashboards tree is bound directly to the real `line_ids` one2many (not a computed field), so native **Save** and the native **Refresh/Discard** icon work normally. Toggles only change the form's in-memory state; nothing is written until Save. Persistence happens in `DashboardRightsMatrix.write()` → `_commit_lines_to_rights()` (the single commit point), which pushes the line state to `dashboard.rights`. Immediate per-row propagation was removed from the line model.
- **Live group cascade + roll-up (8.6, 8.7, 8.8):** `DashboardRightsMatrix._onchange_line_ids_cascade` runs on every toggle. `has_access_prev` (a column-invisible row field) lets it tell whether the group row or a dashboard row was toggled, then it either cascades the group's value down to the dashboards, or rolls the dashboards' aggregate up to the group row.
- **Live count in "Dashboard Name" (8.5):** rendered by a small reactive client widget `dr_group_count` (a `CharField` subclass in `static/src/js/dashboard_rights_matrix_list.js`). For a group row it counts its sibling dashboard rows' `has_access` live, so the `granted / total` figure updates instantly without a server round-trip.
- **Grant / Revoke All (8.3, 8.4):** `static/src/js/dashboard_bulk_buttons.js` stages the value onto every loaded `line_ids` row client-side (leaving the form dirty); it no longer writes to the database, so the change is committed only on Save and reverted by Discard.
- **Group order (8.5 / req. 9):** each line carries a `menu_sequence` integer set in `action_load_dashboards` from the sequence of the dashboard's menu under the **My Dashboard** menu (`my_dashboard_menu.child_id`). The line model `_order` and the tree `default_order` both lead with `menu_sequence`, so the groups follow the menu order. The tree uses `limit="9999"` so the last group is never cut off by the default 40-row page.
- **Scope filter (8.6 / req. 10):** both `action_load_dashboards` (matrix) and `dashboard.rights._sync_missing_records` (compact list) filter boards to `b.id == 1 or b.name == "My Dashboard" or b.ks_dashboard_top_menu_id`, dropping menu-less orphans (e.g. *"Actual vs Target"*). Note: existing `dashboard.rights` rows for an excluded board are left untouched (they are simply no longer shown/managed here).

**Files touched:** `models/dashboard_rights_matrix.py`, `models/dashboard_rights.py`, `views/dashboard_rights_matrix_views.xml`, `static/src/js/dashboard_rights_matrix_list.js`, `static/src/js/dashboard_bulk_buttons.js`, `__manifest__.py`.
