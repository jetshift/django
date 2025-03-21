from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatabaseViewSet, MigrateDatabaseViewSet, MigrateTableViewSet

router = DefaultRouter()
router.register(r'databases', DatabaseViewSet)
router.register(r'migrate/databases', MigrateDatabaseViewSet)
router.register(r'migrate/tables', MigrateTableViewSet)

urlpatterns = router.urls
