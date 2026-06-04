from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve
from django.http import FileResponse, HttpResponse
from django.utils.encoding import escape_uri_path
import mimetypes
import os
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def serve_allure_report(request, path, document_root):
    """自定义视图来提供 Allure 报告文件，确保正确的字符编码"""
    fullpath = os.path.join(document_root, path)
    
    if not os.path.exists(fullpath):
        from django.http import Http404
        raise Http404("File not found")
    
    # 检测文件类型
    content_type, encoding = mimetypes.guess_type(fullpath)
    
    # 对于 HTML 文件，强制使用 UTF-8 编码
    if content_type == 'text/html':
        content_type = 'text/html; charset=utf-8'
    elif content_type is None:
        content_type = 'application/octet-stream'
    
    # 读取文件内容
    with open(fullpath, 'rb') as f:
        response = HttpResponse(f.read(), content_type=content_type)
    
    # 设置编码相关头
    if encoding:
        response['Content-Encoding'] = encoding
    
    # 设置文件名（处理中文）
    filename = os.path.basename(fullpath)
    response['Content-Disposition'] = f'inline; filename="{escape_uri_path(filename)}"'
    
    return response

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    path('api/auth/', include('apps.users.urls')),
    path('api/projects/', include('apps.projects.urls')),
    path('api/testcases/', include('apps.testcases.urls')),
    path('api/testsuites/', include('apps.testsuites.urls')),
    path('api/executions/', include('apps.executions.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/reviews/', include('apps.reviews.urls')),
    path('api/versions/', include('apps.versions.urls')),
    path('api/assistant/', include('apps.assistant.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/requirement-analysis/', include('apps.requirement_analysis.urls')),
    path('api/ui-automation/', include('apps.ui_automation.urls')),
    path('api/app-automation/', include('apps.app_automation.urls')),  # APP自动化测试
    path('api/', include('apps.api_testing.urls')),
    path('api/core/', include('apps.core.urls')),
    path('api/data-factory/', include('apps.data_factory.urls')),
]

# API测试 Allure 报告访问 - 使用自定义视图确保 UTF-8 编码
# 注意：这个路径必须在 Django static() 之前，否则会先被 static 处理
urlpatterns += [
    path('api-testing/allure-reports/<path:path>',
         serve_allure_report,
         {'document_root': os.path.join(settings.MEDIA_ROOT, 'api-testing', 'allure-reports')}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# APP自动化 Template 目录静态访问
import os
urlpatterns += [
    path('app-automation-templates/<path:path>', 
         serve, 
         {'document_root': os.path.join(settings.BASE_DIR, 'apps', 'app_automation', 'Template')}),
]

# APP自动化 Allure 报告访问 - 使用自定义视图确保 UTF-8 编码
urlpatterns += [
    path('app-automation-reports/<path:path>',
         serve_allure_report,
         {'document_root': os.path.join(settings.MEDIA_ROOT, 'app-automation', 'allure-reports')}),
]
