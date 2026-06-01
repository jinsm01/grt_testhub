from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RequirementDocumentViewSet,
    RequirementAnalysisViewSet,
    BusinessRequirementViewSet,
    GeneratedTestCaseViewSet,
    AnalysisTaskViewSet,
    AIModelConfigViewSet,
    PromptConfigViewSet,
    GenerationConfigViewSet,
    TestCaseGenerationTaskViewSet,
    ConfigStatusViewSet,
    TestTemplateConfigViewSet,
    TestTemplateCategoryViewSet,
    upload_and_analyze,
    analyze_text
)
from .lightrag_views import (
    KnowledgeGraphViewSet,
    get_build_task_status,
    get_available_documents,
    upload_and_create_graph,
    ProjectDocumentListCreateView,
    ProjectDocumentDetailView,
)

# 创建DRF路由器
router = DefaultRouter()
router.register(r'documents', RequirementDocumentViewSet, basename='requirementdocument')
router.register(r'analyses', RequirementAnalysisViewSet, basename='requirementanalysis')
router.register(r'requirements', BusinessRequirementViewSet, basename='businessrequirement')
router.register(r'test-cases', GeneratedTestCaseViewSet, basename='generatedtestcase')
router.register(r'tasks', AnalysisTaskViewSet, basename='analysistask')
router.register(r'ai-models', AIModelConfigViewSet, basename='aimodelconfig')
router.register(r'prompts', PromptConfigViewSet, basename='promptconfig')
router.register(r'generation-config', GenerationConfigViewSet, basename='generationconfig')
router.register(r'testcase-generation', TestCaseGenerationTaskViewSet, basename='testcasegenerationtask')
router.register(r'config', ConfigStatusViewSet, basename='configstatus')
# 测试模板配置API
router.register(r'test-templates', TestTemplateConfigViewSet, basename='testtemplateconfig')
router.register(r'template-categories', TestTemplateCategoryViewSet, basename='testtemplatecategory')
# LightRAG 知识图谱API
router.register(r'knowledge-graphs', KnowledgeGraphViewSet, basename='knowledgegraph')

app_name = 'requirement_analysis'

# 创建知识图谱子路由
knowledge_graph_patterns = [
    path('build-tasks/<str:task_id>/status/', get_build_task_status, name='kg-build-task-status'),
    path('available-documents/<int:project_id>/', get_available_documents, name='kg-available-documents'),
    path('upload-and-create/', upload_and_create_graph, name='kg-upload-and-create'),
]

urlpatterns = [
    # LightRAG 知识图谱特殊端点 - 必须放在 router 之前
    path('knowledge-graphs/', include(knowledge_graph_patterns)),
    
    # 项目文档管理API
    path('project-documents/', ProjectDocumentListCreateView.as_view(), name='project-document-list'),
    path('project-documents/<int:pk>/', ProjectDocumentDetailView.as_view(), name='project-document-detail'),
    
    # DRF路由
    path('', include(router.urls)),

    # 特殊API端点
    path('upload-and-analyze/', upload_and_analyze, name='upload-and-analyze'),
    path('analyze-text/', analyze_text, name='analyze-text'),
]