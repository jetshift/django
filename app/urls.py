from rest_framework.routers import DefaultRouter
from .views import DatabaseViewSet, MigrateDatabaseViewSet, MigrateTableViewSet, MigrationViewSet

router = DefaultRouter()
router.register(r'databases', DatabaseViewSet)
router.register(r'migrate/databases', MigrateDatabaseViewSet)
router.register(r'migrate/tables', MigrateTableViewSet)
router.register(r'migrate', MigrationViewSet, basename='migration')

urlpatterns = router.urls
