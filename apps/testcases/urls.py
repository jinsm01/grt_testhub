from django.urls import path
from . import views

urlpatterns = [
    # 测试用例相关
    path('', views.TestCaseListCreateView.as_view(), name='testcase-list'),
    path('<int:pk>/', views.TestCaseDetailView.as_view(), name='testcase-detail'),
    path('<int:pk>/link-suite/', views.link_testcase_to_suite, name='testcase-link-suite'),
    path('<int:pk>/unlink-suite/', views.unlink_testcase_from_suite, name='testcase-unlink-suite'),
    path('<int:pk>/available-suites/', views.available_suites_for_testcase, name='testcase-available-suites'),
    path('modules/', views.testcase_modules, name='testcase-modules'),
    path('statistics/', views.testcase_statistics, name='testcase-statistics'),
    path('author-cases/', views.author_test_cases, name='author-test-cases'),
    path('batch-review/', views.batch_update_review_status, name='batch-update-review'),
    path('ai-review/', views.ai_review_test_cases, name='ai-review'),
]