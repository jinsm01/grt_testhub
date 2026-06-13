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
from .apifox_check_views import (
    apifox_check_config, apifox_check_rules, apifox_check_generate,
    apifox_check_task_status, apifox_check_reports,
    apifox_check_report_detail, apifox_check_report_delete,
    apifox_check_exemptions, apifox_check_report_json,
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

urlpatterns = [
    path('api-testing/', include(router.urls)),
    path('api-testing/import/', import_interfaces, name='import-interfaces'),
    # API Fox CLI 导入（旧版 - TestSuite）
    path('api-testing/apifox/validate/', apifox_import_validate, name='apifox-import-validate'),
    path('api-testing/apifox/import/', apifox_import_execute, name='apifox-import-execute'),
    path('api-testing/apifox/functions/', apifox_function_list, name='apifox-function-list'),
    # Apifox 场景检查 - 配置管理
    path('api-testing/apifox-check/config/', apifox_check_config, name='apifox-check-config'),
    # Apifox 场景检查 - 检查规则管理（启停用）
    path('api-testing/apifox-check/rules/', apifox_check_rules, name='apifox-check-rules'),
    # Apifox 场景检查 - ID字段豁免管理
    path('api-testing/apifox-check/exemptions/', apifox_check_exemptions, name='apifox-check-exemptions'),
    # Apifox 场景检查 - 生成报告
    path('api-testing/apifox-check/generate/', apifox_check_generate, name='apifox-check-generate'),
    # Apifox 场景检查 - 任务状态
    path('api-testing/apifox-check/task/<str:task_id>/', apifox_check_task_status, name='apifox-check-task-status'),
    # Apifox 场景检查 - 报告列表
    path('api-testing/apifox-check/reports/', apifox_check_reports, name='apifox-check-reports'),
    # Apifox 场景检查 - 删除报告 (必须在详情前面，避免被详情模式匹配)
    path('api-testing/apifox-check/report/<str:filename>/delete/', apifox_check_report_delete, name='apifox-check-report-delete'),
    # Apifox 场景检查 - 报告JSON数据 (必须在HTML详情前面，避免被详情模式匹配)
    path('api-testing/apifox-check/report/<str:filename>/json/', apifox_check_report_json, name='apifox-check-report-json'),
    # Apifox 场景检查 - 报告详情 (HTML)
    path('api-testing/apifox-check/report/<str:filename>/', apifox_check_report_detail, name='apifox-check-report-detail'),
]

# 添加媒体文件路由
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
