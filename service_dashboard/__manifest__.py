{
    "name": "Service Dashboards - Custom Theme",
    "version": "17.0.1.0.9",
    "category": "Services",
    "summary": "Service Dashboard View",
    "description": """
        Service Dashboard View aggregating data from project tasks, warranties, and work centers.
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "depends": ["base", "project", "product", "machine_repair_management", "dashboard_user_rights_roles", "ks_dashboard_ninja", "ks_dn_advance", "hr_timesheet", "service_dashboards"],
    "data": [
        "security/ir.model.access.csv",
        "security/service_dashboard_rules.xml",
        "data/ir_cron.xml",
        # "views/service_dashboard_views.xml",
        # "views/dbmodel_jobcards_views.xml",
        # "views/dbm_spareparts_warranty_views.xml",
        "views/views_dbmodel_usergroup_analysis.xml",
        "views/dbmodel_task_message_log_analysis_views.xml",
        "views/service_dashboard_menus.xml",
        # Per-role Service Analysis dashboards (CC / CRD / Parts / Technicians).
        # Migrated here from the former standalone module service_dashboard_user_boards.
        "data/service_user_boards.xml",
        # Full pixel-faithful dump of the legacy live boards (Service Analysis variants,
        # Technician Analysis, Sales & Cost Analysis) — every styling + functional field
        # captured so a fresh DB rebuilds them identically.
        "data/legacy_service_boards.xml",
        # Chart positions only. noupdate=0 so a `-u service_dashboard` on any
        # server re-applies the latest grid_corners and rebuilds each board's
        # ks_gridstack_config — so the visual chart order matches local exactly.
        "data/service_dashboard_layout.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}
