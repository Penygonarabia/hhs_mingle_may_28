{
    "name": "Dashboard Rights — Ninja Bridge",
    "version": "17.0.1.0.1",
    "category": "Settings",
    "summary": "Auto-install bridge that wires Dashboard Rights into "
               "ks_dashboard_ninja (board access checks + menu hiding).",
    "description": """
Dashboard Rights — Ninja Bridge
================================

Auto-installed whenever both ``dashboard_rights`` and ``ks_dashboard_ninja``
are present. Holds every model override that touches Ninja:

* ``ks_dashboard_ninja.board`` create hook (auto-provision rights rows), the
  ``ks_fetch_dashboard_data`` access check, and the ``fetch_dashboard_overview``
  filter (Overview gallery cards match dashboard.rights instead of listing
  every board unconditionally).
* ``ir.ui.menu`` visibility filter that hides dashboards the current user
  is not allowed to see.

Uninstalling ``ks_dashboard_ninja`` auto-removes this bridge module but
leaves the core ``dashboard_rights`` module — and its data — in place.
""",
    "author": "Cielo Digital",
    "depends": [
        "dashboard_rights",
        "ks_dashboard_ninja",
    ],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": True,
    "license": "LGPL-3",
}
