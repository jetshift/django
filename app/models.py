from django.db import models
from django.utils.timezone import now


class User(models.Model):
    name = models.CharField(max_length=120)
    username = models.CharField(max_length=80, unique=True)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'js_users'

    def __str__(self):
        return f'User {self.id}'


class Status(models.TextChoices):
    PENDING = 'pending', 'Pending'
    MIGRATING = 'migrating', 'Migrating'
    PAUSED = 'paused', 'Paused'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class Database(models.Model):
    DIALECT_CHOICES = [
        ('sqlite', 'SQLite'),
        ('mysql', 'MySQL'),
        ('postgres', 'PostgreSQL'),
    ]

    TYPE_CHOICES = [
        ('source', 'Source'),
        ('target', 'Target'),
    ]

    dialect = models.CharField(max_length=50, choices=DIALECT_CHOICES)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120)
    host = models.CharField(max_length=191, blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    username = models.CharField(max_length=120, blank=True, null=True)
    password = models.CharField(max_length=191, blank=True, null=True)
    database = models.CharField(max_length=191, blank=True, null=True)
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
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    logs = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'js_migrate_databases'

    def __str__(self):
        return f'MigrateDatabase {self.id}'


class MigrateTable(models.Model):
    title = models.CharField(max_length=120)
    source_db = models.ForeignKey(Database, on_delete=models.CASCADE, related_name='source_table_jobs')
    target_db = models.ForeignKey(Database, on_delete=models.CASCADE, related_name='target_table_jobs')
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    logs = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'js_migrate_tables'

    def __str__(self):
        return f'MigrateTable {self.id}'


class MigrationTask(models.Model):
    migrate_table = models.ForeignKey(MigrateTable, on_delete=models.CASCADE, related_name='tasks')
    source_table = models.CharField(max_length=255)
    target_table = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'js_migrate_table_tasks'

    def __str__(self):
        return f'MigrationTask {self.id}'
