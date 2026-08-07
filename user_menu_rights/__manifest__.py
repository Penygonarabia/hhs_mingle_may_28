{
    "name": "User Menu Rights",
    "version": "17.0.1.11.0",
    "category": "Settings",
    "summary": "Per-user, per-menu access rights — standalone, no dependency on any other app.",
    "description": """
User Menu Rights
=================

Adds a Settings page that lets an administrator control, per individual user,
which menus and sub-menus of the system that user can see — down to a single
menu item, a whole sub-menu branch, or a whole top-level app in one toggle.

* Persistent model: ``menu.access.rights`` (user x menu x has_access).
* On install, every existing active user is grandfathered to exactly the
  menus they can already see (via their real Odoo group membership), so
  installing this module never silently takes access away from anyone.
  Only future grants/revokes go through the Menu Rights screens.
* Enforcement: menus without an explicit grant are hidden in the backend
  menu tree, for every user except the true superuser.
* Scope is EVERY menu in the system — Settings and its whole subtree
  included. The one exception is a narrow lockout guard: this module's own
  page and the menus leading to it are never hidden from a member of
  "Menu Rights Admin", so revoking Settings for yourself can't take away
  the only screen that could undo it.

One screen — Settings ▸ Menu Rights Setup ▸ User Menu Rights — split into
two panels:

* **Left**: every internal user (avatar, name, email) with a search box
  matching on name or email. Clicking a user loads them on the right.
* **Right**: that user's full menu tree. Toggling any row cascades to its
  whole sub-tree and rolls up into its ancestors, so one control handles
  "one menu", "one sub-menu branch", or "one whole app". Search, Expand /
  Collapse All, Copy Rights From…, and Grant / Revoke All sit above it.

NB: toggles persist immediately (the tree is an editable list, so each
change is written on click) — Odoo's own save/discard only clears the
form's dirty state.

Self-contained: depends on "base" only, defines its own models, and can be
installed on any Odoo 17 database without any other custom module.
""",
    "author": "Cielo Digital",
    # Deliberately "base" only — this module is self-contained and installable
    # on any Odoo 17 database on its own. It touches no other custom module's
    # models, and its Settings menu hangs off base.menu_administration.
    "depends": ["base"],
    "post_init_hook": "post_init_hook",
    "data": [
        "security/menu_rights_groups.xml",
        "security/ir.model.access.csv",
        "views/menu_access_copy_wizard_views.xml",
        "views/menu_access_matrix_views.xml",
        "views/menu_rights_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "user_menu_rights/static/src/css/menu_access_rights.css",
            "user_menu_rights/static/src/js/menu_access_matrix_search.js",
            "user_menu_rights/static/src/js/menu_access_users_list.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
