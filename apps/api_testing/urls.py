from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import (
    ApiProjectViewSet, ApiCollectionViewSet, ApiRequestViewSet,
    EnvironmentViewSet, RequestHistoryViewSet, TestSuiteViewSet,
    TestSuiteRequestViewSet, TestExecutionViewSet, UserViewSet,
    ScheduledTaskViewSet, TaskExecutionLogViewSet, NotificationLogViewSet,
    TaskNotificationSettingViewSet, OperationLogViewSet,
    ApiDashboardViewSet, AIServiceConfigViewSet, import_interfaces,
    apifox_import_validate, apifox_import_execute, apifox_function_list
)
from .views_scenario import (
    AutomationScenarioViewSet, ScenarioStepViewSet, ScenarioExecutionViewSet,
    apifox_import_v2_validate, apifox_import_v2_execute
)

router = DefaultRouter()
router.register(r'dashboard', ApiDashboardViewSet, basename='dashboard')
router.register(r'projects', ApiProjectViewSet)
router.register(r'collections', ApiCollectionViewSet)
router.register(r'requests', ApiRequestViewSet)
router.register(r'environments', EnvironmentViewSet)
router.register(r'histories', RequestHistoryViewSet)
router.register(r'test-suites', TestSuiteViewSet)
router.register(r'test-suite-requests', TestSuiteRequestViewSet)
router.register(r'test-executions', TestExecutionViewSet)
router.register(r'users', UserViewSet)
router.register(r'scheduled-tasks', ScheduledTaskViewSet, basename='scheduledtask')
router.register(r'task-execution-logs', TaskExecutionLogViewSet, basename='taskexecutionlog')
router.register(r'notification-logs', NotificationLogViewSet)
router.register(r'task-notification-settings', TaskNotificationSettingViewSet)
router.register(r'operation-logs', OperationLogViewSet)
router.register(r'ai-service-configs', AIServiceConfigViewSet, basename='aiserviceconfig')
# 自动化场景路由
router.register(r'automation-scenarios', AutomationScenarioViewSet, basename='automation-scenario')
router.register(r'scenario-steps', ScenarioStepViewSet, basename='scenario-step')
router.register(r'scenario-executions', ScenarioExecutionViewSet, basename='scenario-execution')

urlpatterns = [
    path('api-testing/', include(router.urls)),
    path('api-testing/import/', import_interfaces, name='import-interfaces'),
    # API Fox CLI 导入（旧版 - TestSuite）
    path('api-testing/apifox/validate/', apifox_import_validate, name='apifox-import-validate'),
    path('api-testing/apifox/import/', apifox_import_execute, name='apifox-import-execute'),
    path('api-testing/apifox/functions/', apifox_function_list, name='apifox-function-list'),
    # API Fox CLI 导入（新版 - AutomationScenario）
    path('api-testing/apifox/v2/validate/', apifox_import_v2_validate, name='apifox-import-v2-validate'),
    path('api-testing/apifox/v2/import/', apifox_import_v2_execute, name='apifox-import-v2-execute'),
    # 兼容前端调用的 URL
    path('api-testing/apifox/import-v2/', apifox_import_v2_execute, name='apifox-import-v2-execute-alt'),
]

# 添加媒体文件路由
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
