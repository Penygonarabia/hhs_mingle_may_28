import sys

menu = env.ref('dealer.menu_dealer_approve_shop_sales', raise_if_not_found=False)
if not menu:
    print("MENU NOT FOUND!")
else:
    print(f"Menu Name: {menu.name}")
    print(f"Action: {menu.action.name if menu.action else 'NONE'}")
    print(f"Groups: {[g.name for g in menu.groups_id]}")
    if menu.action:
        print(f"Action Type: {menu.action.type}")
        print(f"Action Model: {menu.action.res_model}")

import_menu = env.ref('dealer.menu_sales_target_import', raise_if_not_found=False)
if not import_menu:
    print("IMPORT MENU NOT FOUND!")
else:
    print(f"Import Menu Name: {import_menu.name}")
    print(f"Import Action Model: {import_menu.action.res_model if import_menu.action else 'NONE'}")
