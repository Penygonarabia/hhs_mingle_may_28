import os
import subprocess
import tempfile
import logging
import json
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AutoDbBackupConfig(models.Model):
    _name = 'auto.db.backup.config'
    _description = 'Database Backup Configuration'
    _rec_name = 'db_name'

    # =========================================================================
    # DATABASE CONNECTION
    # =========================================================================
    db_host = fields.Char(
        string="DB Host", required=True, default='localhost',
    )
    db_port = fields.Char(
        string="DB Port", required=True, default='5432',
    )
    db_name = fields.Char(
        string="Database Name", required=True,
    )
    db_user = fields.Char(
        string="DB Username", required=True, default='odoo',
    )
    db_password = fields.Char(
        string="DB Password", required=True,
    )

    # =========================================================================
    # STORAGE TYPE
    # =========================================================================
    storage_type = fields.Selection([
        ('local', 'Local / Mounted Drive'),
        ('google_drive', 'Google Drive'),
    ], string="Storage Type", default='google_drive', required=True,
    )

    # LOCAL STORAGE
    backup_path = fields.Char(
        string="Local Backup Directory",
        default='/tmp/odoo_backups',
    )

    # GOOGLE DRIVE
    gdrive_credentials_path = fields.Char(
        string="Service Account JSON Path",
        help="Full file path to the Google Service Account credentials JSON file on the server.\n"
             "Example: /etc/odoo/gdrive_credentials.json",
    )
    gdrive_folder_id = fields.Char(
        string="Google Drive Folder ID",
        help="The ID of the Google Drive folder where backups will be uploaded.\n"
             "To find it: Open the folder in Google Drive, the URL will be:\n"
             "https://drive.google.com/drive/folders/XXXXXXXXX\n"
             "Copy the XXXXXXXXX part and paste it here.",
    )

    # =========================================================================
    # BACKUP SETTINGS
    # =========================================================================
    backup_format = fields.Selection([
        ('sql', 'SQL (Plain Text - pg_dump)'),
        ('custom', 'Custom (pg_dump -Fc, compressed)'),
    ], string="Backup Format", default='custom', required=True,
    )
    retention_days = fields.Integer(
        string="Keep Backups For (Days)", default=30,
    )
    is_active = fields.Boolean(
        string="Active", default=True,
    )

    # =========================================================================
    # STATUS DISPLAY
    # =========================================================================
    last_backup_date = fields.Datetime(
        string="Last Successful Backup", readonly=True,
    )
    last_backup_size = fields.Char(
        string="Last Backup Size", readonly=True,
    )
    backup_count = fields.Integer(
        string="Total Backups", compute='_compute_backup_count',
    )

    def _compute_backup_count(self):
        LogObj = self.env['auto.db.backup.log']
        for rec in self:
            rec.backup_count = LogObj.search_count([('config_id', '=', rec.id)])

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def action_test_connection(self):
        """Test the PostgreSQL connection."""
        self.ensure_one()
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password or ''
            cmd = [
                'pg_isready',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', self.db_name,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=env)
            if result.returncode == 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Successful'),
                        'message': _('PostgreSQL connection to %s is working!') % self.db_name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(
                    _('Connection Failed!\n\n%s\n%s') % (result.stdout, result.stderr)
                )
        except FileNotFoundError:
            raise UserError(_('pg_isready not found. Install PostgreSQL client tools.'))
        except subprocess.TimeoutExpired:
            raise UserError(_('Connection timed out.'))

    def action_test_gdrive(self):
        """Test Google Drive connection."""
        self.ensure_one()
        if self.storage_type != 'google_drive':
            raise UserError(_('Select Google Drive storage type first.'))
        try:
            service = self._get_gdrive_service()
            # Try listing files in the folder
            results = service.files().list(
                q=f"'{self.gdrive_folder_id}' in parents and trashed=false",
                pageSize=5,
                fields="files(id, name)"
            ).execute()
            file_count = len(results.get('files', []))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Google Drive Connected!'),
                    'message': _('Successfully connected! Found %d files in the folder.') % file_count,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except FileNotFoundError:
            raise UserError(
                _('Credentials JSON file not found at: %s\n\n'
                  'Please upload the Service Account JSON file to the server.') % self.gdrive_credentials_path
            )
        except ImportError:
            raise UserError(
                _('Google API libraries not installed.\n\n'
                  'Run on your server:\n'
                  '  pip3 install google-api-python-client google-auth')
            )
        except Exception as e:
            raise UserError(_('Google Drive Error:\n\n%s') % str(e))

    def action_backup_now(self):
        """Manually trigger a backup."""
        self.ensure_one()
        self._execute_backup()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Backup Complete'),
                'message': _('Database "%s" backed up successfully!') % self.db_name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'name': _('Backup Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'auto.db.backup.log',
            'view_mode': 'list,form',
            'domain': [('config_id', '=', self.id)],
            'context': {'default_config_id': self.id},
        }

    # =========================================================================
    # GOOGLE DRIVE HELPERS
    # =========================================================================

    def _get_gdrive_service(self):
        """Build and return a Google Drive API service object."""
        from google.oauth2 import service_account
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        import json

        creds_path = self.gdrive_credentials_path
        if not creds_path or not os.path.isfile(creds_path):
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")

        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        
        # Read file to check if it's a Service Account or User Token
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
        
        if 'token' in creds_data:
            # Format: token.json (User Account)
            credentials = Credentials.from_authorized_user_info(creds_data, scopes=SCOPES)
        else:
            # Format: service_account.json
            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=SCOPES
            )
            
        service = build('drive', 'v3', credentials=credentials)
        return service

    def _upload_to_gdrive(self, local_filepath, filename):
        """Upload a file to Google Drive folder."""
        from googleapiclient.http import MediaFileUpload

        try:
            service = self._get_gdrive_service()

            file_metadata = {
                'name': filename,
                'parents': [self.gdrive_folder_id],
            }
            media = MediaFileUpload(
                local_filepath,
                mimetype='application/octet-stream',
                resumable=True,
            )
            # Create the file directly in the user-owned folder
            uploaded = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink',
                supportsAllDrives=True
            ).execute()

            gdrive_link = uploaded.get('webViewLink', '')
            _logger.info("Auto Backup: Uploaded %s to Google Drive (ID: %s)",
                         filename, uploaded.get('id'))
            return True, gdrive_link

        except Exception as e:
            _logger.exception("Auto Backup: Google Drive upload failed: %s", e)
            return False, str(e)

    def _cleanup_old_gdrive(self):
        """Delete old backup files from Google Drive based on retention days."""
        if not self.retention_days or self.retention_days <= 0:
            return
        try:
            service = self._get_gdrive_service()

            # List all files in the folder
            results = service.files().list(
                q=f"'{self.gdrive_folder_id}' in parents and trashed=false",
                pageSize=500,
                fields="files(id, name, createdTime)"
            ).execute()
            files = results.get('files', [])

            cutoff = datetime.now() - timedelta(days=self.retention_days)
            deleted = 0
            for f in files:
                fname = f.get('name', '')
                if not fname.startswith(self.db_name):
                    continue
                if not (fname.endswith('.sql') or fname.endswith('.dump')):
                    continue
                # Parse date from filename
                try:
                    date_part = fname.replace(self.db_name + '_', '').split('.')[0]
                    file_date = datetime.strptime(date_part, '%Y%m%d_%H%M%S')
                    if file_date < cutoff:
                        service.files().delete(fileId=f['id']).execute()
                        deleted += 1
                        _logger.info("Auto Backup: Deleted old GDrive backup %s", fname)
                except (ValueError, IndexError):
                    continue

            if deleted:
                _logger.info("Auto Backup: Cleaned %d old backups from Google Drive", deleted)

        except Exception as e:
            _logger.warning("Auto Backup: GDrive cleanup error: %s", e)

    # =========================================================================
    # CORE BACKUP LOGIC
    # =========================================================================

    def _execute_backup(self):
        """Execute pg_dump and store locally or upload to Google Drive."""
        self.ensure_one()

        # 1. Determine temp dump location
        local_tmp = self.backup_path or tempfile.gettempdir()
        if not os.path.isdir(local_tmp):
            try:
                os.makedirs(local_tmp, exist_ok=True)
            except OSError as e:
                self._log_backup('failed', error=f'Cannot create directory {local_tmp}: {e}')
                return

        # 2. Build filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = '.sql' if self.backup_format == 'sql' else '.dump'
        filename = f"{self.db_name}_{timestamp}{ext}"
        filepath = os.path.join(local_tmp, filename)

        # 3. Build pg_dump command
        cmd = [
            'pg_dump',
            '-h', self.db_host,
            '-p', self.db_port,
            '-U', self.db_user,
            '-d', self.db_name,
            '--no-owner',
        ]
        if self.backup_format == 'custom':
            cmd.extend(['-Fc'])
        else:
            cmd.extend(['-Fp'])
        cmd.extend(['-f', filepath])

        # 4. Execute pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_password or ''

        start_time = datetime.now()
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=3600, env=env
            )
            duration = (datetime.now() - start_time).total_seconds()

            if result.returncode != 0 or not os.path.isfile(filepath):
                error_msg = result.stderr or 'pg_dump failed'
                self._log_backup('failed', error=error_msg, duration=duration)
                return

            file_size = os.path.getsize(filepath)
            size_str = self._format_size(file_size)

            # 5. Handle storage
            final_path = filepath
            if self.storage_type == 'google_drive':
                success, gdrive_info = self._upload_to_gdrive(filepath, filename)
                if success:
                    final_path = f'Google Drive: {gdrive_info}'
                    # Remove local temp file
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
                else:
                    self._log_backup('failed',
                                     error=f'pg_dump OK but Google Drive upload failed: {gdrive_info}',
                                     duration=duration)
                    return

            self.write({
                'last_backup_date': fields.Datetime.now(),
                'last_backup_size': size_str,
            })
            self._log_backup('success', filepath=final_path, size=size_str, duration=duration)
            _logger.info("Auto Backup: %s -> %s (%s)", self.db_name, final_path, size_str)

        except FileNotFoundError:
            self._log_backup('failed', error='pg_dump not found. Install PostgreSQL client tools.')
        except subprocess.TimeoutExpired:
            self._log_backup('failed', error='Backup timed out after 1 hour.')
        except Exception as e:
            self._log_backup('failed', error=str(e))

        # 6. Cleanup
        if self.storage_type == 'local' and self.retention_days > 0:
            self._cleanup_old_local()
        elif self.storage_type == 'google_drive' and self.retention_days > 0:
            self._cleanup_old_gdrive()

    def _log_backup(self, status, filepath='', size='', error='', duration=0):
        self.env['auto.db.backup.log'].sudo().create({
            'config_id': self.id,
            'db_name': self.db_name,
            'backup_datetime': fields.Datetime.now(),
            'filepath': filepath,
            'file_size': size,
            'status': status,
            'error_message': error,
            'duration': round(duration, 1),
        })

    def _cleanup_old_local(self):
        """Delete local backups older than retention_days."""
        if not self.retention_days or self.retention_days <= 0:
            return
        backup_dir = self.backup_path
        if not backup_dir or not os.path.isdir(backup_dir):
            return
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for fname in os.listdir(backup_dir):
            fpath = os.path.join(backup_dir, fname)
            if not os.path.isfile(fpath):
                continue
            if not fname.startswith(self.db_name):
                continue
            if not (fname.endswith('.sql') or fname.endswith('.dump')):
                continue
            file_mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if file_mtime < cutoff:
                try:
                    os.remove(fpath)
                except OSError:
                    pass

    @staticmethod
    def _format_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes / (1024 ** 2):.1f} MB"
        else:
            return f"{size_bytes / (1024 ** 3):.2f} GB"

    # =========================================================================
    # CRON ENTRY POINT
    # =========================================================================

    @api.model
    def _cron_run_backup(self):
        configs = self.search([('is_active', '=', True)])
        for config in configs:
            try:
                config._execute_backup()
            except Exception as e:
                _logger.exception("Auto Backup CRON: %s: %s", config.db_name, e)
