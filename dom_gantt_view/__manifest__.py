{
    "name": "Gantt View",
    "version": "17.0.1.0.0",
    "category": "Gantt",
    "summary": "Gantt View for the community edition",
    "live_test_url": "https://demo17.domiup.com",
    "website": "https://www.youtube.com/watch?v=qyWRRxr8Ehk",
    "author": "Domiup (domiup.contact@gmail.com)",
    "price": 50,
    "currency": "EUR",
    "license": "OPL-1",
    "support": "domiup.contact@gmail.com",
    "depends": ["web"],
    "excludes": ["web_gantt"],
    "assets": {
        "web.assets_backend": [
            "dom_gantt_view/static/src/**/*",
            # "dom_gantt_view/static/src/js/*",

            # "dom_gantt_view/static/src/js/custom/calenderrender.js",
            # "dom_gantt_view/static/src/js/custom/component.js",
            # "dom_gantt_view/static/src/js/custom/component.xml",
       
         
        ],
    },
    "images": ["static/description/banner.gif"],
    "installable": True,
    "application": True,
}
