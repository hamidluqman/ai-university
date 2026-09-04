import os
import shutil
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Creates a timestamped backup of the SQLite database.'

    def handle(self, *args, **kwargs):
        db_path = settings.DATABASES['default']['NAME']
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'db_backup_{timestamp}.sqlite3'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            shutil.copy2(db_path, backup_path)
            self.stdout.write(self.style.SUCCESS(f'Successfully backed up database to {backup_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Backup failed: {e}'))