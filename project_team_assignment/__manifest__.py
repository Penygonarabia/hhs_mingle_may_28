{
    "name": "Project: Team Assignment",
    "version": "17.0.1.0.0",
    "category": "Project",
    "summary": """
Add team members to your project and assign them tasks on the Gantt view
    """,
    "live_test_url": "https://demo17.domiup.com",
    "website": "https://demo17.domiup.com",
    "author": "Domiup (domiup.contact@gmail.com)",
    "license": "OPL-1",
    "price": 50,
    "support": "domiup.contact@gmail.com",
    "depends": ["project_dom_gantt_view", "dom_gantt_resource_wo_event","machine_repair_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/project_role_views.xml",
        "views/project_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "project_team_assignment/static/src/js/calendar_controller.esm.js",
            "project_team_assignment/static/src/js/calendar_model.esm.js",
            "project_team_assignment/static/src/js/calendar_common_renderer.esm.js",
        ]
    },
    "test": [],
    "demo": [],
    "images": ["static/description/banner.gif"],
    "installable": True,
}
