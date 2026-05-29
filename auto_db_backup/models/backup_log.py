from odoo import models, fields


class AutoDbBackupLog(models.Model):
    _name = 'auto.db.backup.log'
    _description = 'Database Backup Log'
    _order = 'backup_datetime desc'

    config_id = fields.Many2one(
        'auto.db.backup.config', string="Backup Config",
        ondelete='cascade',
    )
    db_name = fields.Char(string="Database", readonly=True)
    backup_datetime = fields.Datetime(string="Backup Time", readonly=True)
    filepath = fields.Char(string="File Path", readonly=True)
    file_size = fields.Char(string="File Size", readonly=True)
    duration = fields.Float(string="Duration (sec)", readonly=True)
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string="Status", readonly=True)
    error_message = fields.Text(string="Error Details", readonly=True)
