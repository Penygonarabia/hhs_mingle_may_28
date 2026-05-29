{
    "name": "CRM Custom View",
    "version": "1.0",
    "category": "CRM",
    "summary": "Customizations for CRM Lead/Opportunity form view",
    "description": "Hide Internal Notes, Marketing and Tracking groups in CRM lead form view",
    "author": "Ramesh Manivannan",
    "depends": ["crm","machine_repair_management"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/crm_lead_views.xml",
        "views/res_config_settings_view.xml",
        "views/property_type_maintenance_details_views.xml",
    ],
    "installable": True,
    "application": False,
}