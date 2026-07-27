{
    "name": "Module Rights",
    "version": "17.0.2.0.3",
    "category": "Settings",
    "summary": "Per-user, per-dashboard access rights (Settings page).",
    "description": """
Dashboard Rights
================

New, independent module (does NOT use module_user_rights_roles).

Adds a Settings menu page "Dashboard Rights" that lets an administrator pick
a dashboard category (Service Dashboards, Contract Dashboards, ...) and tick
which dashboards each user is allowed to see/use.

* Persistent model: ``dashboard.rights`` (user x dashboard x has_access).
* Defaults: every checkbox unticked for every non-admin user.
* Admin: always has access to every dashboard (checkboxes ticked & readonly).
* Enforcement: dashboards are hidden in menus and their action access is
  blocked server-side for users without the right.

Module Rights Setup (17.0.2.0.0, replaces the 17.0.1.0.27-32 Rights Setup /
Controlled Modules / Discover Candidate Modules pages)
------------------------------------------------------------------------
Settings > Module Rights > "Module Rights Setup" is a second per-user
page, alongside Users Setup, covering every application's menus — every
top-level app menu in the system (Machine Repair, Promoter, Payroll, My
Dashboard, ...) plus every sub-menu beneath it, at any depth — EXCEPT
Settings (governed by real Odoo groups). No registry/allow-list step is
needed any more: every app just shows up. Each app is a group whose
children are every menu it owns, each individually grantable/revocable,
exactly like Quick Access/Configuration sub-items, enforced through the
same dashboard.rights.menu._managed_menu_ids mechanism (no per-app
enforcement code). Existing active users are grandfathered to every menu
that existed at upgrade time, so nobody loses access to anything they
already used; only new users / future revokes go through the normal grant
flow. Model access.rights.module.matrix (+ .line) deliberately mirrors
dashboard.rights.matrix's field names so the existing dr_access_toggle /
dr_group_count / Grant-All-Revoke-All JS widgets work unchanged, with zero
new client code.

The standalone "Rights Setup" menu entry was removed — the same
dashboard.rights.matrix wizard it opened is still reachable by clicking a
user row in Users Setup, so no functionality was lost. The Settings menu
category itself was renamed from "Dashboard Rights" to "Module Rights"
(17.0.2.0.1).

My Dashboard included, kept in sync (17.0.2.0.1)
--------------------------------------------------
Module Rights Setup now also lists the My Dashboard app itself (boards,
Quick Access, Configuration), so an admin can see and grant everything
from one page. A KS dashboard board has two grants — the board-level one
in Users Setup (dashboard.rights) and the menu-level one here
(dashboard.rights.menu) — and both models now write through
dashboard.rights.menu._dr_sync_board_and_menu on every toggle, from either
page, so the two never disagree about whether a board is visible. A
migration corrects a transient earlier bug where My Dashboard's menus were
briefly (and wrongly) blanket-granted to everyone regardless of their real
per-board access.

Copy Rights
-----------
"Copy Rights From…" button on both Users Setup's matrix and Module Rights
Setup opens a wizard (dashboard.rights.copy.wizard) that copies EVERYTHING
a source user can see — dashboards, Quick Access/Configuration, and every
app menu — onto specific target user(s) or all users in one shot.

Rights-check smart button
--------------------------
Both pages show a "<granted>/<total>" smart button once loaded — a quick
glance at what the selected user currently has, without opening every
group. Clicking it drills into a read-only list (dashboard.rights /
dashboard.rights.menu), pre-filtered to Granted.

Fully independent of machine_repair_management (17.0.2.0.3)
-------------------------------------------------------------
The "User Role" column/filter (Parts / Coordinator / Call Center /
Technician, derived from machine_repair_management group membership) has
been removed everywhere — Users Setup, Module Rights Setup, the Copy
Rights wizard, and the Users-tab widget. This was the module's only
dependency on another app's data; the module now works fully standalone
regardless of whether machine_repair_management is installed.

A fresh install on a server that already has the older hide_menu_user
module's per-user menu restrictions (table ``ir_ui_menu_res_users_rel``)
now grandfathers each user's CURRENT effective menu visibility into
dashboard.rights.menu — granted for every managed menu except the ones
that table says are hidden for them — so switching a server onto this
module doesn't silently take away access nobody meant to revoke.
""",
    "author": "Cielo Digital",
    # Drop the cached web.assets_* bundle on install AND on every upgrade (see
    # hooks.py + migrations/17.0.1.0.19/) so CSS/JS changes to the matrix — the
    # Has-Access column-width lock in particular — actually take effect via a
    # plain -u, instead of silently serving the stale compiled bundle. Column
    # widths are a JS/CSS-renderer concern and can't be fixed in Python/XML.
    "post_init_hook": "post_init_hook",
    "depends": [
        "base",
        "ks_dashboard_ninja",
    ],
    "data": [
        "security/dashboard_rights_groups.xml",
        "security/ir.model.access.csv",
        # NB: data/dashboard_rights_menus_data.xml (which created placeholder
        # "Quick Access"/"Configuration" KS boards) is intentionally NOT loaded.
        # Those boards are excluded from the matrix anyway, and creating a
        # ks_dashboard board via XML fails on this ks_dashboard_ninja build
        # (missing static/images/dashboardOverview/defaultDashboard.png), which
        # blocked reinstall. The quick_access_menu/configuration_menu xmlids the
        # rest of the module references are governed independently.
        "views/dashboard_rights_views.xml",
        # Loaded before dashboard_rights_matrix_views.xml / access_rights_module_
        # matrix_views.xml: both reference action_dashboard_rights_copy_wizard
        # by xmlid in a button, which must already exist in ir_model_data.
        "views/dashboard_rights_copy_wizard_views.xml",
        "views/dashboard_rights_menu_views.xml",
        "views/dashboard_rights_matrix_views.xml",
        "views/access_rights_module_matrix_views.xml",
        "views/dashboard_rights_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "module_rights/static/src/css/dashboard_rights_matrix.css",
            "module_rights/static/src/xml/grouped_user_list.xml",
            "module_rights/static/src/xml/dashboard_rights_list.xml",
            "module_rights/static/src/xml/dashboard_bulk_buttons.xml",
            "module_rights/static/src/xml/header_status_gate.xml",
            "module_rights/static/src/xml/parent_breadcrumb_restore.xml",
            "module_rights/static/src/xml/copy_email_char.xml",
            "module_rights/static/src/js/copy_to_clipboard.js",
            "module_rights/static/src/js/copy_email_char.js",
            "module_rights/static/src/js/grouped_user_list.js",
            "module_rights/static/src/js/dashboard_rights_list.js",
            "module_rights/static/src/js/dashboard_rights_matrix_list.js",
            "module_rights/static/src/js/dashboard_bulk_buttons.js",
            "module_rights/static/src/js/users_tab_refresh.js",
            "module_rights/static/src/js/header_status_gate.js",
            "module_rights/static/src/js/parent_breadcrumb_restore.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
