# -*- coding: utf-8 -*-
{
    'name': "Contract Phase 2 - Service & Repair",
    'version': '17.0.1.0.0',
    'category': 'Services/Project',
    'summary': "Lead-driven multi-jobcard Service & Repair flow (non-AMC) with "
               "consolidated quotation, Hyperpay payments and invoicing.",
    'description': """
Contract Phase 2 - Service & Repair
===================================
Handles the scenario where a residential/commercial customer has several
(5-10) air conditioners requiring repair, WITHOUT an AMC or service contract.

Flow:
  1. A Lead (crm.lead) is raised for Service & Repair.
  2. Inspection payment is collected (Hyperpay link via WhatsApp / manual tick).
  3. Multiple job cards are bulk-created from a technician grid on the lead.
  4. Each job card lists the required spare parts and service charges.
  5. All job cards are consolidated into a single quotation (Populate button).
  6. Regular approval / WhatsApp flow, then job payment (Hyperpay).
  7. Technicians are assigned, jobs completed, invoice generated.
  8. Optional balance payment handling.

Adds a Job Card TYPE (Regular / AMC / Service & Repair).
""",
    'author': "Hussein and Al Hassan G. Shaker Bros",
    'license': 'LGPL-3',
    'depends': [
        'machine_repair_management',
        'hyperbill_payments',
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/crm_lead_views.xml',
        'views/job_card_views.xml',
        'views/service_sale_order_views.xml',
        'views/contract_phase2_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'contract_phase2/static/src/css/cp2_lists.css',
            'contract_phase2/static/src/js/cp2_scoped_x2many_field.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
