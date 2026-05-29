{
    "name": "Project Task Readonly Control",
    "version": "17.0.1.0.0",
    "summary": "Make Project Task readonly based on state and user group",
    "depends": ["project", "machine_repair_management"],
    "author": "Vengateshwaran.S",
    "data": [
        # "security/ir.rule.xml",
        # "views/project_task_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "project_task_readonly_control/static/src/js/project_task_full_js_readonly.js",
            "project_task_readonly_control/static/src/css/project.css",
        ]
    },
    "installable": True,
    "application": False,
}
