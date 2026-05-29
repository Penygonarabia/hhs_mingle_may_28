{
    "name": "HHS PM Service Parameters",
    "version": "17.0.1.0",
    "category": "Sales/CRM",
    "summary": "Preventive Maintenance Service Parameter Configuration",
    "description": """
        HHS PM Service Module
        =====================
        Adds a PM Service Parameter screen inside CRM module.
        - Define Service Unit Types linked to service products
        - Configure checklist parameters (Visual Inspection, Physical Inspection, etc.)
        - Tag parameters as Major/Minor/Both
        - Sort order and active toggle support
    """,
    "author": "HHS",
    "website": "",
    "depends": ["crm", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/pm_service_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hhs_pm_service/static/src/css/pm_service_tree.css",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
