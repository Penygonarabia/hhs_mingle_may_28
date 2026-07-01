Service Dashboards CT Layout Sync
=================================

Purpose
-------
Keep chart ordering, position, and size identical across servers during
service_dashboards_ct install or upgrade.

Source of truth used by install/upgrade
---------------------------------------
- data/service_dashboard_layout.xml

This file is loaded by the module manifest with noupdate="0", so layout values
are re-applied on every module upgrade.

Snapshot backup copy
--------------------
- data/service_dashboard_layout_snapshot.xml

This file stores the same layout snapshot as a backup/reference copy.

How this was generated
----------------------
The current live layout was exported from DB and written back with:

python3 scripts/save_service_dashboard_ct_layouts.py --db-csv

The script writes item grid_corners and then triggers:
- ks_dashboard_ninja.board.service_dashboard_ct_rebuild_layouts

So ks_gridstack_config is rebuilt from the saved positions.

Recommended workflow after changing dashboard design
----------------------------------------------------
1. Arrange/resize charts in UI.
2. Regenerate layout file from live DB:
   python3 scripts/save_service_dashboard_ct_layouts.py --db-csv
3. Update backup snapshot copy:
   cp service_dashboards_ct/data/service_dashboard_layout.xml \
      service_dashboards_ct/data/service_dashboard_layout_snapshot.xml
4. Upgrade module on target server:
   odoo -u service_dashboards_ct -d <db_name> --stop-after-init
