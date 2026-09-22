{
    'name': 'PBI Dashboard Configurations',
    'version': '17.0.3.0.0',
    'category': 'Sales/Dashboard',
    'summary': 'Standing up a dashboard server: what it is missing, the bidata feed, and the master data',
    'author': 'Cielo Digital',
    'description': """
The four things a new dashboard server needs, in the order it needs them, and
nothing else. Everything here is safe to run twice and diagnoses before it
changes anything.

  * SERVER CAPABILITIES -- the two kinds of third party. Optional PYTHON
    PACKAGES (python-pptx, openpyxl) behind the export buttons, which this page
    can install: the request carries a KEY looked up in optional_deps, never a
    package name, so nothing a caller sends reaches a command line. And the
    companion ODOO MODULES the boards read master data from -- dashboard_groups,
    sales_budget, partner_classification, machine_repair_management,
    salesman_res_partner, whichever module declares res.region. Those are
    REPORTED ONLY: installing an Odoo module runs its own hooks, data files and
    migrations, which belongs to Apps. The suite depends on none of them
    deliberately, so an absent one does not fail to install -- it degrades, a
    caption reads "Unassigned" while every total stays correct, and the board
    looks like it is answering. That is the single most common reason a new
    server's dashboard is wrong, and this is the only place it shows.

  * STEP 1, BIDATA TABLE AND v_bidata_live -- the ERP feed arrives outside
    Odoo, so no module creates either. This builds the shape; the rows follow.

  * STEP 2, BIDATA DATA IMPORT -- export a year here, import it there. Inserts
    and updates, never deletes, and diagnoses before it writes.

  * STEP 3, MASTER SETUP -- the masters that turn the feed's codes into the ten
    levels the boards group by, the Product Sub-Group link no module owns any
    more, the view rebuild a REFRESH cannot do, and the verification that proves
    it worked.

WHAT WAS TAKEN OFF THIS PAGE AND WHY. Snapshot freshness, upgrade blockers, the
from-scratch bring-up as its own section, the documents, the feed-vs-dashboard
check and the dated pile of maintenance scripts. Standing up staging-hhsv3
showed the cost of carrying all of it: the four steps that matter were scattered
across seven sections, three of them looked equally urgent, so they were run in
the wrong order -- and each wrong order produced a different failure that looked
like a dashboard bug. The controllers and routes behind those sections are
untouched; they came off the page, they were not deleted, and any of them
returns by adding markup and nothing else.

Nothing here rebuilds anything inside the request except Step 3c, which says so
on the button: only init() can rewrite a view definition, and a REFRESH re-runs
the stale one.
""",
    # pbi_dashboards ONLY, deliberately. Step 3c rebuilds pbi_sales_dashboards'
    # fact view, but this does NOT depend on that module: the model is probed at
    # request time and the step reports it as skipped where it is absent, the way
    # the boards probe tables they do not own. It keeps this page installable on
    # a server carrying a different subset of the boards -- which is exactly the
    # server most likely to need it.
    'depends': [
        'pbi_dashboards',
    ],
    'data': [
        'views/pbi_dashboard_configurations_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pbi_dashboard_configurations/static/src/js/config_page.js',
            'pbi_dashboard_configurations/static/src/xml/config_page.xml',
            'pbi_dashboard_configurations/static/src/css/config_page.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
