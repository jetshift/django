from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from app.views.auth_views import CustomTokenObtainPairView, ProtectedView
from app.views.task_views import TaskViewSet, SubTaskViewSet
from app.views.views import DatabaseViewSet, MigrateDatabaseViewSet, MigrationViewSet, test_view
from app.views.chart_views import ChartsETLTasksView, ChartsDatabasesView

router = DefaultRouter()
router.register(r'databases', DatabaseViewSet)
router.register(r'migrate/databases', MigrateDatabaseViewSet)
router.register(r'tasks', TaskViewSet, basename='tasks')
router.register(r'subtasks', SubTaskViewSet, basename='subtasks')
router.register(r'migrate', MigrationViewSet, basename='migration')

urlpatterns = [
    path('test/', test_view),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('protected/', ProtectedView.as_view(), name='protected'),
]

urlpatterns += [
    path('charts/databases/', ChartsDatabasesView.as_view(), name='charts_databases'),
    path('charts/tasks/', ChartsETLTasksView.as_view(), name='charts_etl_tasks'),
]

urlpatterns += router.urls
