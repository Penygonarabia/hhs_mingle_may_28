{
    "name": "Service Dashboards - CT",
    "version": "17.0.1.1.0",
    "category": "Services",
    "summary": "Service Dashboards with the custom (custom-1) chart palette.",
    "description": """
        Custom-theme variant of the Service Dashboards. Self-contained: owns
        its own dbmodel_* SQL views (suffixed _ct) and its own copies of the
        board records. Installs and uninstalls independently of the sibling
        service_dashboards_ot module.
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "depends": [
        "base",
        "project",
        "product",
        "machine_repair_management",
        "dashboard_user_rights_roles",
        "ks_dashboard_ninja",
        "ks_dn_advance",
        "hr_timesheet",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/service_dashboard_rules.xml",
        "data/ir_cron.xml",
        "views/views_dbmodel_usergroup_analysis_ct.xml",
        "views/dbmodel_task_message_log_analysis_views_ct.xml",
        "views/service_dashboards_menus.xml",
        "data/service_user_boards.xml",
        "data/legacy_service_boards.xml",
        "data/service_dashboard_layout.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}
