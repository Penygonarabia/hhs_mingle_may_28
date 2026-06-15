{
    'name': 'HHS Job Card Post Service Checklist',
    'version': '17.0.1.0.0',
    'category': 'Services/Project',
    'summary': 'Add Post Service Checklist & Photo tabs to Job Cards',
    'description': 'Job Card Checklist Module',
    'author': 'HHS',
    'depends': [
        'machine_repair_management',
        'hhs_post_service_checklist',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/jobcard_checklist_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hhs_jobcard_checklist/static/src/css/checklist_styles.css',
            'hhs_jobcard_checklist/static/src/js/checklist_answer.js',
            'hhs_jobcard_checklist/static/src/js/checklist_photo_upload.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
