from django.contrib import admin
from .models import User, Database, MigrateDatabase, MigrateTable

admin.site.register(User)
admin.site.register(Database)
admin.site.register(MigrateDatabase)
admin.site.register(MigrateTable)
