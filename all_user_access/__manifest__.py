{
    "name": "All User Access",
    "version": "1.0.0",
    "summary": "Creates a group and assigns it to all users (existing and new).",
    "description": "Module to create a security group 'All User Access' and automatically assign it to all existing and newly created users.",
    "author": "ChatGPT for User",
    "category": "Tools",
    "depends": ["base"],
    "data": [
        "security/security.xml"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    # "post_init_hook": "post_init_assign_group"
}
