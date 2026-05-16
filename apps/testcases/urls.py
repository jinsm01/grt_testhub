from django.urls import path
from . import views

urlpatterns = [
    # 测试用例相关
    path('', views.TestCaseListCreateView.as_view(), name='testcase-list'),
    path('<int:pk>/', views.TestCaseDetailView.as_view(), name='testcase-detail'),
    path('modules/', views.testcase_modules, name='testcase-modules'),
    path('statistics/', views.testcase_statistics, name='testcase-statistics'),
    path('author-cases/', views.author_test_cases, name='author-test-cases'),
    path('batch-review/', views.batch_update_review_status, name='batch-update-review'),
]