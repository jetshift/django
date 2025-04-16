from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from app.utils.encryption import get_fernet


class Status(models.TextChoices):
    IDLE = 'idle', 'Idle'
    MIGRATING = 'syncing', 'Syncing'
    PAUSED = 'paused', 'Paused'
    FAILED = 'failed', 'Failed'
    COMPLETED = 'completed', 'Completed'


class JSDatabase(models.Model):
    DIALECT_CHOICES = [
        ('sqlite', 'SQLite'),
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
    ]

    TYPE_CHOICES = [
        ('source', 'Source'),
        ('target', 'Target'),
    ]

    dialect = models.CharField(max_length=50, choices=DIALECT_CHOICES, default="mysql")
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='source')
    title = models.CharField(max_length=120)
    host = models.CharField(max_length=191, blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    username = models.CharField(max_length=120, blank=True, null=True)
    _password = models.CharField(max_length=191, blank=True, null=True, db_column='password')
    database = models.CharField(max_length=191, blank=True, null=True)
    secure = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def password(self):
        if not self._password:
            return None
        try:
            return get_fernet().decrypt(self._password.encode()).decode()
        except Exception:
            return None

    @password.setter
    def password(self, value):
        if value:
            self._password = get_fernet().encrypt(value.encode()).decode()
        else:
            self._password = None

    def get_decrypted_password(self):
        return self.password

    def set_encrypted_password(self, value):
        self.password = value

    class Meta:
        db_table = 'js_databases'

    def __str__(self):
        return f'JSDatabase {self.id}'


class JSMigrateDatabase(models.Model):
    title = models.CharField(max_length=120)
    source_db = models.ForeignKey(JSDatabase, on_delete=models.CASCADE, related_name='source_migration_databases')
    target_db = models.ForeignKey(JSDatabase, on_delete=models.CASCADE, related_name='target_migration_databases')
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.IDLE)
    logs = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'js_migrate_databases'

    def __str__(self):
        return f'JSMigrateDatabase {self.id}'


class JSTask(models.Model):
    TYPE_CHOICES = [
        ('migration', 'Migration'),
        ('etl', 'ETL'),
    ]

    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='migration')
    title = models.CharField(max_length=120)
    source_db = models.ForeignKey(JSDatabase, on_delete=models.CASCADE, related_name='source_tasks')
    target_db = models.ForeignKey(JSDatabase, on_delete=models.CASCADE, related_name='target_tasks')
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.IDLE, null=True)
    logs = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=now, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'js_tasks'

    def __str__(self):
        return f'JSTask {self.id}'


def default_sub_task_config():
    return {
        "live_schema": True,
        "primary_id": "id",
        "extract_offset": 0,
        "extract_limit": 10,
        "extract_chunk_size": 0,
        "truncate_table": False,
        "load_chunk_size": 10,
        "sleep_interval": 1
    }


def default_sub_task_stats():
    return {
        "total_source_items": 0,
        "total_target_items": 0
    }


class JSSubTask(models.Model):
    task = models.ForeignKey(JSTask, on_delete=models.CASCADE, related_name='subtasks')
    source_table = models.CharField(max_length=255)
    target_table = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.IDLE)
    config = models.JSONField(default=default_sub_task_config, null=True)
    stats = models.JSONField(default=default_sub_task_stats, null=True)
    deployment_id = models.CharField(max_length=255, null=True)
    cron = models.CharField(max_length=255, default='* * * * *')
    error = models.TextField(blank=True, default='', null=True)

    class Meta:
        db_table = 'js_subtasks'

    def __str__(self):
        return f'JSSubTask {self.id}'
