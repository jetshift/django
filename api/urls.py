from rest_framework.routers import DefaultRouter
from .views import UserViewSet, DatabaseViewSet, MigrateDatabaseViewSet, MigrateTableViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'databases', DatabaseViewSet)
router.register(r'migrate-databases', MigrateDatabaseViewSet)
router.register(r'migrate-tables', MigrateTableViewSet)

urlpatterns = router.urls
