{
    "name": "Service Dashboard",
    "version": "17.0.1.0.0",
    "category": "Services",
    "summary": "Service Dashboard View",
    "description": """
        Service Dashboard View aggregating data from project tasks, warranties, and work centers.
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "depends": ["base", "project", "product", "machine_repair_management","dashboard_user_rights_roles", "ks_dashboard_ninja", "hr_timesheet"],
    "data": [
        "security/ir.model.access.csv",
        "views/service_dashboard_views.xml",
        "views/dbmodel_jobcards_views.xml",
        "views/dbm_spareparts_warranty_views.xml",
        "views/views_dbmodel_usergroup_analysis.xml",
        "views/dbmodel_task_message_log_analysis_views.xml"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
