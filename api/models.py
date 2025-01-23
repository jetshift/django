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


class Database(models.Model):
    DIALECT_CHOICES = [
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
    status = models.IntegerField(default=0)
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
    source_tables = models.TextField(blank=True, null=True)
    target_tables = models.TextField(blank=True, null=True)
    status = models.IntegerField(default=0)
    logs = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'js_migrate_tables'

    def __str__(self):
        return f'MigrateTable {self.id}'
