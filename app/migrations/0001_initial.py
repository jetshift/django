# Generated by Django 5.1.7 on 2025-04-22 11:57

import app.models
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='JSDatabase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dialect', models.CharField(choices=[('sqlite', 'SQLite'), ('mysql', 'MySQL'), ('postgresql', 'PostgreSQL'), ('clickhouse', 'ClickHouse')], default='mysql', max_length=50)),
                ('type', models.CharField(choices=[('source', 'Source'), ('target', 'Target')], default='source', max_length=50)),
                ('title', models.CharField(max_length=120)),
                ('host', models.CharField(blank=True, max_length=191, null=True)),
                ('port', models.IntegerField(blank=True, null=True)),
                ('username', models.CharField(blank=True, max_length=120, null=True)),
                ('_password', models.CharField(blank=True, db_column='password', max_length=191, null=True)),
                ('database', models.CharField(blank=True, max_length=191, null=True)),
                ('secure', models.BooleanField(default=False)),
                ('status', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'js_databases',
            },
        ),
        migrations.CreateModel(
            name='JSMigrateDatabase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120)),
                ('status', models.CharField(choices=[('idle', 'Idle'), ('syncing', 'Syncing'), ('paused', 'Paused'), ('failed', 'Failed'), ('completed', 'Completed')], default='idle', max_length=50)),
                ('logs', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_db', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_migration_databases', to='app.jsdatabase')),
                ('target_db', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='target_migration_databases', to='app.jsdatabase')),
            ],
            options={
                'db_table': 'js_migrate_databases',
            },
        ),
        migrations.CreateModel(
            name='JSTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('migration', 'Migration'), ('etl', 'ETL')], default='migration', max_length=50)),
                ('title', models.CharField(max_length=120)),
                ('status', models.CharField(choices=[('idle', 'Idle'), ('syncing', 'Syncing'), ('paused', 'Paused'), ('failed', 'Failed'), ('completed', 'Completed')], default='idle', max_length=50, null=True)),
                ('logs', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('source_db', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_tasks', to='app.jsdatabase')),
                ('target_db', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='target_tasks', to='app.jsdatabase')),
            ],
            options={
                'db_table': 'js_tasks',
            },
        ),
        migrations.CreateModel(
            name='JSSubTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_table', models.CharField(max_length=255)),
                ('target_table', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('idle', 'Idle'), ('syncing', 'Syncing'), ('paused', 'Paused'), ('failed', 'Failed'), ('completed', 'Completed')], default='idle', max_length=50)),
                ('config', models.JSONField(default=app.models.default_sub_task_config, null=True)),
                ('stats', models.JSONField(default=app.models.default_sub_task_stats, null=True)),
                ('deployment_id', models.CharField(max_length=255, null=True)),
                ('cron', models.CharField(default='* * * * *', max_length=255)),
                ('error', models.TextField(blank=True, default='', null=True)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subtasks', to='app.jstask')),
            ],
            options={
                'db_table': 'js_subtasks',
            },
        ),
    ]
