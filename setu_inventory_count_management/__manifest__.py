{
    'name': 'Multi User Inventory Count / Stock Take',
    'version': '17.0',
    'category': 'Inventory',
    'license': 'OPL-1',
    'price': 149,
    #'price' : 126,
    'currency': 'EUR',

    # Author
    'author': 'PenygonArabia',
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',

    'summary': """
        Inventory Count is the solution that helps to manage inventory that is to check and keep track record of physical inventory.
        inventory count, stock count, inventory management, stock management, stock analysis, inventory analysis, physical stock count, count inventories, employee performance, simultaneously inventory count, simultaneously stock count, approval, rejection, barcode scanning, track record, session management, work accuracy, discrepancy report, adjustment report, inventory adjustment report, statistic report,

    """,

    'description' : """
        Inventory Count is the solution that helps to manage inventory that is to check and keep track record of physical inventory and the one with stock count in Inventory Management Software. Inventory Management is a crucial part of any business and so is maintaining the physical count of Inventory. Stock count in business helps you from avoiding stock out that is out of stock nightmares. For businesses of Warehouse management accurate stock present physically as the one in Inventory Software is most crucial. Inventory analysis by comparing physical Inventory with the one in software also allows you to check Employee Performance , Employee Activity Management , Manage Supervisor Activity on counting inventory , Employee overtime that is track time taken by employee in counting. This module will allow employee to check in/out within active work location time. Scanning products through a Barcode machine and entering the quantity counted physically can then be compared with one in the system.
    """,

    'images': ['static/description/banner.gif'],

    'depends': ['stock_account','stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/ir_cron.xml',
        'data/mail_template_data.xml',
        'views/inventory_session_details.xml',
        'views/inventory_count.xml',
        'views/inventory_session.xml',
        'views/actions.xml',
        'views/stock_inventory.xml',
        'views/stock_location.xml',
        'views/inventory_count_planner.xml',
        'views/res_config_settings_views.xml',
        'views/stock_move_line.xml',
        'views/stock_move.xml',
        'views/inventory_count_backdate_action.xml',
        'wizard/inventory_count_report.xml',
        'wizard/inventory_adjustment_report.xml',
        'wizard/inventory_user_states_report.xml',
        'wizard/setu_inventory_count_configuration.xml',
        'wizard/wizards.xml',
        'wizard/inventory_count_backdate_wizard.xml',
        'views/report_inventory_count_session_inprogress.xml',
    ],

    # Technical
    'installable': True,
    'auto_install': False,
    'application': True,
    'active': False,

    
}
