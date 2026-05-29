{
    "name": "Gantt View: Show Resource Which having no Event",
    "version": "17.0.1.0.0",
    "category": "Gantt",
    "summary": """
This module shows Resources which having no Event.
For example, showing all Assignees on the gantt view even though they
don't have any task.
    """,
    "live_test_url": "https://demo17.domiup.com",
    "website": "",
    "author": "Domiup (domiup.contact@gmail.com)",
    "license": "OPL-1",
    "price": 50,
    "currency": "USD",
    "support": "domiup.contact@gmail.com",
    "depends": ["dom_gantt_view"],
    "data": [],
    "test": [],
    "demo": [],
    "assets": {
        "web.assets_backend": [
            "dom_gantt_resource_wo_event/static/src/**/*",
        ],
    },
    "images": ["static/description/banner.gif"],
    "installable": True,
}
