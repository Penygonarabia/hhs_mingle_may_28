{
    'name': "HHS Maintenance Equipment",
    'summary': """
       Maintenance Equipment """,
    'author': "Gokul",
    'version': '17.0',
    "license": "LGPL-3",
    'depends': ['base', 'maintenance', 'machine_repair_management', 'sales_contract_and_recurring_invoices',
                'hr_maintenance'],
    'data': [
        "security/ir.model.access.csv",
        "views/maintenance_hhs.xml",
        "views/res_config_settings.xml",
        "views/brand_model_view.xml",
        "wizard/maintenance_equipment_import_view.xml",
        "data/cron_maintenace_equipment.xml",
        "data/data_create_service_request.xml",
        # "views/subscription_contract.xml",
    ],
    #'pre_init_hook': 'pre_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,

}
