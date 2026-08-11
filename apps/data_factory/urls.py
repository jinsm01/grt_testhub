from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DataFactoryViewSet
from .excel_filler_view import (
    analyze_excel_template, fill_excel_data, preview_filled_data,
    generate_module_course_data,
)
# Bug 分析相关视图
from .bug_analysis_view import (
    analyze_bug_excel,
    analyze_bug_data,
    enhance_with_ai,
    bug_analysis_records,
    bug_analysis_record_detail,
    bug_analysis_record_delete,
    bug_analysis_compare,
    bug_analysis_module_detail,
    analyze_module_focus_intelligent,
    bug_analysis_summary,
    generate_summary_insight,
    bug_analysis_summaries,
    bug_analysis_summary_detail,
    bug_analysis_summary_delete,
    yunxiao_projects,
    yunxiao_sprints,
    yunxiao_members,
    yunxiao_labels,
    sync_from_yunxiao,
    yunxiao_sync_log,
    bug_analysis_ai_status,
    create_bug_to_yunxiao,
    update_bug_to_yunxiao,
    quick_change_bug_status,
    resync_bug_item,
    bug_sync_items,
    poll_remote_status,
    delete_bug_sync_item,
    yunxiao_token_list,
    yunxiao_token_detail,
    yunxiao_token_options,
    yunxiao_token_test,
    personnel_assessment,
)
# AI 评分量表生成视图
from .rubric_view import (
    rubric_records,
    rubric_detail,
    rubric_generate,
    rubric_delete,
    rubric_statistics,
)

router = DefaultRouter()
router.register(r'', DataFactoryViewSet, basename='data-factory')

urlpatterns = [
    path('', include(router.urls)),
    # Excel 模板填充
    path('excel-filler/analyze/', analyze_excel_template, name='excel-filler-analyze'),
    path('excel-filler/fill/', fill_excel_data, name='excel-filler-fill'),
    path('excel-filler/preview/', preview_filled_data, name='excel-filler-preview'),

    # 模块课程数据生成（按模块导入点播课）
    path('module-course/generate/', generate_module_course_data, name='module-course-generate'),

    # === Bug 分析核心接口 (原有) ===
    path('bug-analysis/analyze/', analyze_bug_excel, name='bug-analysis-analyze'),
    path('bug-analysis/analyze-data/', analyze_bug_data, name='bug-analysis-analyze-data'),

    # === AI 增强分析 (渐进式加载) ===
    path('bug-analysis/enhance-ai/', enhance_with_ai, name='bug-analysis-enhance-ai'),

    # === Bug 分析记录管理 (新增 V2) ===
    path('bug-analysis/records/', bug_analysis_records, name='bug-analysis-records'),  # GET 列表
    path('bug-analysis/records/<int:record_id>/', bug_analysis_record_detail, name='bug-analysis-record-detail'),  # GET 详情
    path('bug-analysis/records/<int:record_id>/delete/', bug_analysis_record_delete, name='bug-analysis-record-delete'),  # DELETE
    path('bug-analysis/records/<int:record_id>/ai-status/', bug_analysis_ai_status, name='bug-analysis-ai-status'),  # GET AI分析状态
    path('bug-analysis/records/<int:record_id>/assessment/', personnel_assessment, name='bug-analysis-personnel-assessment'),  # GET/POST 人员评估

    # === Bug 分析增强功能 (新增 V2) ===
    path('bug-analysis/compare/', bug_analysis_compare, name='bug-analysis-compare'),  # 跨版本对比
    path('bug-analysis/module/<int:record_id>/', bug_analysis_module_detail, name='bug-analysis-module-detail'),  # 模块详情含Bug列表
    path('bug-analysis/module-focus/', analyze_module_focus_intelligent, name='bug-analysis-module-focus'),  # 智能模块测试重点分析
    path('bug-analysis/summary/', bug_analysis_summary, name='bug-analysis-summary'),  # 汇总分析
    path('bug-analysis/generate-insight/', generate_summary_insight, name='bug-analysis-generate-insight'),  # AI 洞察生成

    # === 汇总分析记录管理 (新增 V3) ===
    path('bug-analysis/summaries/', bug_analysis_summaries, name='bug-analysis-summaries'),  # GET 汇总分析列表
    path('bug-analysis/summaries/<int:summary_id>/', bug_analysis_summary_detail, name='bug-analysis-summary-detail'),  # GET 汇总分析详情
    path('bug-analysis/summaries/<int:summary_id>/delete/', bug_analysis_summary_delete, name='bug-analysis-summary-delete'),  # DELETE

    # === 云效同步 (新增) ===
    path('bug-analysis/yunxiao/projects/', yunxiao_projects, name='yunxiao-projects'),
    path('bug-analysis/yunxiao/sprints/', yunxiao_sprints, name='yunxiao-sprints'),
    path('bug-analysis/yunxiao/members/', yunxiao_members, name='yunxiao-members'),
    path('bug-analysis/yunxiao/labels/', yunxiao_labels, name='yunxiao-labels'),
    path('bug-analysis/yunxiao/sync/', sync_from_yunxiao, name='yunxiao-sync'),
    path('bug-analysis/yunxiao/log/<int:record_id>/', yunxiao_sync_log, name='yunxiao-sync-log'),

    # === Bug 双向同步 (云效写入 + 反向同步) ===
    path('bug-analysis/yunxiao/create-bug/', create_bug_to_yunxiao, name='create-bug-to-yunxiao'),
    path('bug-analysis/yunxiao/update-bug/<int:sync_item_id>/', update_bug_to_yunxiao, name='update-bug-to-yunxiao'),
    path('bug-analysis/yunxiao/quick-change-status/<int:sync_item_id>/', quick_change_bug_status, name='quick-change-bug-status'),
    path('bug-analysis/yunxiao/resync-item/<int:sync_item_id>/', resync_bug_item, name='resync-bug-item'),
    path('bug-analysis/yunxiao/sync-items/', bug_sync_items, name='bug-sync-items'),
    path('bug-analysis/yunxiao/poll-status/', poll_remote_status, name='poll-remote-status'),
    path('bug-analysis/yunxiao/sync-items/<int:sync_item_id>/delete/', delete_bug_sync_item, name='delete-bug-sync-item'),

    # === 云效 Token 配置管理 ===
    path('bug-analysis/yunxiao/tokens/', yunxiao_token_list, name='yunxiao-token-list'),  # GET/POST
    path('bug-analysis/yunxiao/tokens/options/', yunxiao_token_options, name='yunxiao-token-options'),  # GET 下拉选项
    path('bug-analysis/yunxiao/tokens/<int:token_id>/', yunxiao_token_detail, name='yunxiao-token-detail'),  # GET/PUT/DELETE
    path('bug-analysis/yunxiao/tokens/<int:token_id>/test/', yunxiao_token_test, name='yunxiao-token-test'),  # POST 测试

    # === AI 评分量表生成管理 ===
    path('rubric/records/', rubric_records, name='rubric-records'),
    path('rubric/generate/', rubric_generate, name='rubric-generate'),
    path('rubric/statistics/', rubric_statistics, name='rubric-statistics'),
    path('rubric/<int:record_id>/', rubric_detail, name='rubric-detail'),
    path('rubric/<int:record_id>/delete/', rubric_delete, name='rubric-delete'),
]
