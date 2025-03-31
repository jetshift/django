from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin


class Status(models.TextChoices):
    IDLE = 'idle', 'Idle'
    MIGRATING = 'syncing', 'Syncing'
    PAUSED = 'paused', 'Paused'
    FAILED = 'failed', 'Failed'
    COMPLETED = 'completed', 'Completed'


class Database(models.Model):
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
    password = models.CharField(max_length=191, blank=True, null=True)
    database = models.CharField(max_length=191, blank=True, null=True)
    secure = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'js_databases'

    def __str__(self):
        return f'Database {self.id}'


class MigrateDatabase(models.Model):
    title = models.CharField(max_length=120)
    source_db = models.ForeignKey(Database, on_delete=models.CASCADE, related_name='source_migrations')
    target_db = models.ForeignKey(Database, on_delete=models.CASCADE, related_name='target_migrations')
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.IDLE)
    logs = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'js_migrate_databases'

    def __str__(self):
        return f'MigrateDatabase {self.id}'


class MigrateTable(models.Model):
    TYPE_CHOICES = [
        ('migration', 'Migration'),
        ('etl', 'ETL'),
    ]

    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='migration')
    title = models.CharField(max_length=120)
    source_db = models.ForeignKey(Database, on_delete=models.CASCADE, related_name='source_table_jobs')
    target_db = models.ForeignKey(Database, on_delete=models.CASCADE, related_name='target_table_jobs')
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.IDLE)
    logs = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'js_migrate_tables'

    def __str__(self):
        return f'MigrateTable {self.id}'


def default_migration_task_config():
    return {
        "live_schema": False,
        "primary_id": "id",
        "extract_offset": 0,
        "extract_limit": 10,
        "extract_chunk_size": 30,
        "truncate_table": False,
        "load_chunk_size": 10,
        "sleep_interval": 1
    }


def default_migration_task_stats():
    return {
        "total_source_items": 0,
        "total_target_items": 0
    }


class MigrationTask(models.Model):
    migrate_table = models.ForeignKey(MigrateTable, on_delete=models.CASCADE, related_name='tasks')
    source_table = models.CharField(max_length=255)
    target_table = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.IDLE)
    config = models.JSONField(default=default_migration_task_config)
    stats = models.JSONField(default=default_migration_task_stats)
    deployment_id = models.CharField(max_length=255)
    error = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'js_migrate_table_tasks'

    def __str__(self):
        return f'MigrationTask {self.id}'
