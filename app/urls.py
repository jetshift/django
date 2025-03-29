from rest_framework.routers import DefaultRouter
from .views import DatabaseViewSet, MigrateDatabaseViewSet, MigrateTableViewSet, MigrationViewSet, test_view
from django.urls import path

router = DefaultRouter()
router.register(r'databases', DatabaseViewSet)
router.register(r'migrate/databases', MigrateDatabaseViewSet)
router.register(r'migrate/tables', MigrateTableViewSet, basename='migratetable')
router.register(r'migrate', MigrationViewSet, basename='migration')

urlpatterns = [
    path('test/', test_view),
]

urlpatterns += router.urls
