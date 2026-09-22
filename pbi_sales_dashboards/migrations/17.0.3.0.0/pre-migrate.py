# -*- coding: utf-8 -*-
"""Hand the "Sales Dashboards - Temp" xmlids to pbi_sales_temp_dashboards.

The five boards under that container moved to their own module in 17.0.3.0.0,
and their menus and actions went with them. On an installed database the
ir_ui_menu and ir_actions_client rows must NOT be recreated: menu.access.rights
grants hang off ir_ui_menu.id with ondelete=cascade, so a delete-and-recreate
would silently revoke every per-user grant on all five boards (584 of them on
the database this was written against).

pbi_sales_temp_dashboards' own pre_init_hook does the same reassignment, and
between the two this is covered from either direction:

  * ``-i pbi_sales_temp_dashboards -u pbi_sales_dashboards`` — either one wins,
    the other is a no-op; both are idempotent.
  * ``-u pbi_sales_dashboards`` ALONE, with the new module not installed —
    only this script runs, and it is the one that matters. Without it the
    rows would still be owned by pbi_sales_dashboards while no longer declared
    in its data, and ir.model.data._process_end() would delete them as
    obsolete at the end of the run, taking the grants with them. Reassigned to
    a module that is not part of this run, they are out of _process_end's
    reach and simply wait for the new module to be installed.

Runs pre-migrate, before this module's data files are re-read, for the same
reason the hook is pre_init: the rows have to be out of this module's
namespace before the loader gets to them.
"""

import logging

_logger = logging.getLogger(__name__)

NEW_MODULE = "pbi_sales_temp_dashboards"

ADOPTED = (
    "menu_pbi_sales_dashboards_temp",
    "action_pbi_sales_kpi_dashboard",
    "menu_pbi_sales_kpi_analysis",
    "action_pbi_sales_kpi_dashboard_new",
    "menu_pbi_sales_kpi_analysis_new",
    "action_pbi_sales_mail_dashboard",
    "menu_pbi_sales_mail_dashboard",
    "action_pbi_sales_mail_dashboard_new",
    "menu_pbi_sales_mail_dashboard_new",
    "action_pbi_sales_data_study",
    "menu_pbi_sales_data_study",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = %s
         WHERE module = 'pbi_sales_dashboards'
           AND name IN %s
        """,
        (NEW_MODULE, tuple(ADOPTED)),
    )
    if cr.rowcount:
        _logger.info("pbi_sales_dashboards: handed %s external identifiers to %s "
                     "(menus and their grants kept intact)", cr.rowcount, NEW_MODULE)
