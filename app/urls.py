from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from app.views.views import DatabaseViewSet, MigrateDatabaseViewSet, MigrateTableViewSet, MigrationTaskSet, MigrationViewSet, test_view, ProtectedView, CustomTokenObtainPairView

from app.views.chart_views import ChartsETLTasksView, ChartsDatabasesView

router = DefaultRouter()
router.register(r'databases', DatabaseViewSet)
router.register(r'migrate/databases', MigrateDatabaseViewSet)
router.register(r'migrate/tables', MigrateTableViewSet, basename='migratetable')
router.register(r'tasks', MigrationTaskSet, basename='task')
router.register(r'migrate', MigrationViewSet, basename='migration')

urlpatterns = [
    path('test/', test_view),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('protected/', ProtectedView.as_view(), name='protected'),
]

urlpatterns += [
    path('charts/etl-tasks/', ChartsETLTasksView.as_view(), name='charts_etl_tasks'),
    path('charts/databases/', ChartsDatabasesView.as_view(), name='charts_databases'),
]

urlpatterns += router.urls
