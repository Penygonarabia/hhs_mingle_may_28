{
    "name": "Required Label Star",
    "version": "17.0.1.0.0",
    "summary": "Adds * symbol to required form field labels",
    "description": "This module patches Odoo form labels to automatically show a red * for required fields.",
    "category": "Web",
    "author": "Vengateshwaran.S",
    "Company":"Cielo Digitals",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "required_label_star/static/src/js/required_label_patch.js",
            "required_label_star/static/src/css/required_label_patch.css",
        ],
    },
    "installable": True,
    "application": False,
}
