# Generated by Django 5.1.7 on 2025-06-04 04:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jstask',
            name='type',
            field=models.CharField(choices=[('migration', 'Migration'), ('etl', 'ETL'), ('cdc', 'CDC')], default='migration', max_length=50),
        ),
    ]
