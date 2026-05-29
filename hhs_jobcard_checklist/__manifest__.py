{
    'name': 'HHS Job Card Post Service Checklist',
    'version': '17.0.1.0.0',
    'category': 'Services/Project',
    'summary': 'Add Post Service Checklist & Photo tabs to Job Cards',
    'description': """
        Adds two new tabs to the Job Card (project.task) form:
        - Post Service Checklist: loads checklist items from the template
          matching the job card's Brand (Product Category) and Service Unit Type.
        - Post Service Photos: loads photo captions from the same template
          and allows uploading before/after images.

        This module does NOT modify machine_repair_management or
        hhs_post_service_checklist. It only inherits and extends.
    """,
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
