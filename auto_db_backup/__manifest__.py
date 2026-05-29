{
    'name': 'Auto Database Backup',
    'version': '17.0.1.0',
    'category': 'Administration',
    'summary': 'Automated daily PostgreSQL database backup (SQL only, no filestore)',
    'description': """
        Auto Database Backup for Odoo 17 Community
        ============================================
        - Configure DB username, password, host, port
        - Daily automated backup via cron job
        - SQL-only backup (pg_dump) — no filestore
        - Store backups on any drive/path you choose
        - Auto-cleanup of old backups based on retention days
        - Full backup history log with status tracking
    """,
    'author': 'Haka IT',
    'website': 'https://www.haka.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/backup_config_views.xml',
        'views/backup_log_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
