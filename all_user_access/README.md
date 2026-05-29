# all_user_access

Odoo 17 module that creates a security group "All User Access" and:
- assigns it to all existing users after installation (post_init_hook)
- assigns it to all newly created users (override create)

Installation:
1. Place this module in your addons folder.
2. Update apps list and install the module.
3. The group will be created and assigned automatically.

Note: Installing modules requires appropriate server access and restarting Odoo if necessary.
