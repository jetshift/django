from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin


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
    password = models.CharField(max_length=191, blank=True, null=True)
    database = models.CharField(max_length=191, blank=True, null=True)
    secure = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

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


def default_task_details_config():
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


def default_task_details_stats():
    return {
        "total_source_items": 0,
        "total_target_items": 0
    }


class JSTaskDetail(models.Model):
    task = models.ForeignKey(JSTask, on_delete=models.CASCADE, related_name='details')
    source_table = models.CharField(max_length=255)
    target_table = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.IDLE)
    config = models.JSONField(default=default_task_details_config)
    stats = models.JSONField(default=default_task_details_stats)
    deployment_id = models.CharField(max_length=255)
    error = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'js_task_details'

    def __str__(self):
        return f'JSTaskDetail {self.id}'
