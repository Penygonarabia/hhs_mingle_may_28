# -*- coding: utf-8 -*-
# Pre-migration script for dealer module v1.0
#
# PURPOSE:
#   The `res_region.name` field is defined with translate=True in base_territory.
#   During upgrade, Odoo converts this column from varchar -> jsonb in PostgreSQL.
#   Several PostgreSQL views in regulartable_api depend on this column and must be
#   dropped BEFORE the column type migration runs, otherwise the upgrade fails with:
#
#       psycopg2.errors.FeatureNotSupported:
#       cannot alter type of a column used by a view or rule
#       DETAIL: rule _RETURN on view db_product_task depends on column "name"
#
#   All dropped views are recreated automatically by their model's init() method
#   after the migration completes.
#
# VIEWS DROPPED:
#   - db_product_task          (regulartable_api: db_project_task.py)
#   - vi_product_task          (regulartable_api: vi_product_task_view.py)
#   - vi_product_task_namelist (regulartable_api: vi_product_task_view_name_list.py)
#   - vi_product_lines_items   (regulartable_api: vi_product_lines_items_view.py)

import logging

_logger = logging.getLogger(__name__)

VIEWS_TO_DROP = [
    'db_product_task',
    'vi_product_task',
    'vi_product_task_namelist',
    'vi_product_lines_items',
    'vi_monthly_sales_target_dealer',
]


def migrate(cr, version):
    """Drop all PostgreSQL views that depend on res_region.name before column migration."""
    _logger.info(
        "dealer pre-migrate: Dropping views that depend on res_region.name "
        "to allow column type conversion (varchar -> jsonb)."
    )
    for view_name in VIEWS_TO_DROP:
        try:
            cr.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE;")
            _logger.info("dealer pre-migrate: Dropped view '%s' (if it existed).", view_name)
        except Exception as e:
            _logger.warning(
                "dealer pre-migrate: Could not drop view '%s': %s", view_name, e
            )
