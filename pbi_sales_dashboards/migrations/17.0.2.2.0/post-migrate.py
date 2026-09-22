# -*- coding: utf-8 -*-
"""Move "Sales Data Study" under "Sales Dashboards - Temp".

Same gap, same fix as migrations/17.0.2.1.0/post-migrate.py, which moved the
four older bidata-backed boards there: views/pbi_sales_dashboards_menus.xml
already declares the new parent, but every menuitem in that file sits in a
``noupdate="1"`` block, and ir.model.data records flagged noupdate are skipped
on upgrade. The XML therefore only takes effect on a fresh install; this closes
the gap for the databases where the menu already exists.

Deliberately narrow: it sets parent_id and nothing else, and only when the menu
is still under the old parent, so re-running it — or running it after an admin
has moved the menu on purpose — changes nothing.

No grant-carrying here, unlike 17.0.2.1.0's migration. That one moved four
dashboards people were already using, so the new container had to inherit the
old one's grants or those dashboards would have vanished from every non-
superuser. "Sales Data Study" is new, "Sales Dashboards - Temp" already carries
the grants it was given then, and this board's own leaf grant travels with the
menu record.

As of pbi_sales_temp_dashboards, these xmlids belong to THAT module and the
env.ref lookups below resolve to nothing — this script is a historical no-op
kept for databases still upgrading past this version from an older one.
"""

from odoo import SUPERUSER_ID, api

MOVED = "pbi_sales_dashboards.menu_pbi_sales_data_study"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    old_parent = env.ref("pbi_sales_dashboards.menu_pbi_sales_dashboards",
                         raise_if_not_found=False)
    new_parent = env.ref("pbi_sales_dashboards.menu_pbi_sales_dashboards_temp",
                         raise_if_not_found=False)
    menu = env.ref(MOVED, raise_if_not_found=False)
    if not (menu and new_parent):
        # The data file runs before this script, so a missing Temp menu means
        # something is wrong upstream; leave the menu where it is rather than
        # guessing.
        return
    if not old_parent or menu.parent_id == old_parent:
        menu.parent_id = new_parent
