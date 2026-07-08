from rest_framework import generics, permissions, status, pagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models, transaction
from django.utils import timezone
from collections import Counter
import datetime
from .models import TestCase, TestCaseStep, TestCaseAttachment, TestCaseComment
from .serializers import (
    TestCaseSerializer, TestCaseListSerializer, TestCaseCreateSerializer, TestCaseUpdateSerializer
)
from apps.projects.models import Project


def count_text_steps(steps):
    """统计文本模式下的测试步骤数量（按非空行计算）"""
    if not steps:
        return 0
    lines = [line.strip() for line in steps.split('\n') if line.strip()]
    return len(lines)


def get_directory_key(case):
    """获取用例的归属目录键（由项目+菜单决定）"""
    return (case.project_id, case.menu_id)


def get_directory_string(case):
    """获取用例的归属目录路径字符串"""
    directory = ''
    if case.menu:
        directory = case.menu.name
        parent = case.menu.parent
        while parent:
            directory = f"{parent.name} / {directory}"
            parent = parent.parent
        if case.project:
            directory = f"{case.project.name} / {directory}"
    elif case.project:
        directory = case.project.name
    return directory or '未分配'

class TestCasePagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class TestCaseListCreateView(generics.ListCreateAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TestCasePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'test_type', 'project', 'module']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TestCaseCreateSerializer
        return TestCaseListSerializer
    
    def get_queryset(self):
        # 获取所有用例，不再按项目权限隔离
        queryset = TestCase.objects.all().select_related(
            'author', 'assignee', 'project'
        ).prefetch_related(
            'versions'
        ).distinct()
        
        # 支持按菜单ID筛选
        menu_id = self.request.query_params.get('menu')
        if menu_id:
            from apps.projects.models import ProjectMenu
            # 获取指定菜单及其所有子菜单的ID
            menu_ids = [int(menu_id)]
            def get_child_menu_ids(parent_id):
                children = ProjectMenu.objects.filter(parent_id=parent_id)
                for child in children:
                    menu_ids.append(child.id)
                    get_child_menu_ids(child.id)
            get_child_menu_ids(int(menu_id))
            queryset = queryset.filter(menu_id__in=menu_ids)
        
        return queryset

    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        
        # 如果请求中指定了作者（通过author_name），则让序列化器处理作者
        # 否则使用当前登录用户作为作者
        # 端和菜单由序列化器根据 category_path 自动创建
        if self.request.data.get('author_name'):
            # 传递当前用户给序列化器，以便在找不到 author_name 对应用户时使用
            serializer.save(request_user=user)
        else:
            serializer.save(author=user)

class TestCaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TestCaseUpdateSerializer
        return TestCaseSerializer
    
    def get_queryset(self):
        # 获取所有用例，不再按项目权限隔离
        return TestCase.objects.all().select_related(
            'author', 'assignee', 'project'
        ).prefetch_related(
            'versions', 'step_details', 'attachments', 'comments'
        ).distinct()

    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
    
    # 内容字段：修改这些字段时应重置审核状态
    CONTENT_FIELDS = {
        'title', 'description', 'preconditions', 'steps', 'expected_result',
        'priority', 'test_type', 'module', 'tags', 'author_name',
        'category_path', 'project_id', 'version_ids', 'created_at',
    }
    
    def perform_update(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')
        request_data = self.request.data
        
        # 如果修改了内容字段（非审核相关），重置审核状态为待审核
        content_changed = any(field in request_data for field in self.CONTENT_FIELDS)
        review_status_explicit = 'review_status' in request_data
        
        if content_changed and not review_status_explicit:
            serializer.validated_data['review_status'] = 'pending'
        
        if project_id:
            # 检查指定的项目是否存在且用户有权限
            accessible_projects = self.get_user_accessible_projects(user)
            try:
                project = accessible_projects.get(id=project_id)
                serializer.save(project=project)
            except Project.DoesNotExist:
                # 如果指定项目不存在或无权限，保持原项目不变
                serializer.save()
        else:
            # 没有指定项目，保持原项目不变
            serializer.save()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def testcase_modules(request):
    """获取所有测试用例的模块列表（去重）"""
    # 获取所有用例的模块字段（不按项目权限隔离，和全部用例列表保持一致）
    modules = TestCase.objects.exclude(
        module__isnull=True
    ).exclude(
        module=''
    ).values_list(
        'module', flat=True
    ).distinct().order_by('module')
    
    return Response(list(modules))


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def testcase_statistics(request):
    """获取主线用例统计数据（不按项目权限隔离，展示所有用例）"""
    import traceback
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 获取所有用例，不再按项目权限过滤
        queryset = TestCase.objects.all().select_related('author', 'project')
        logger.info(f"Total cases: {queryset.count()}")
        
        # 按项目统计（展示所有项目）
        all_projects = Project.objects.all()
        project_stats = []
        for project in all_projects:
            project_cases = queryset.filter(project=project)
            project_stats.append({
                'project_id': project.id,
                'project_name': project.name,
                'total': project_cases.count(),
                'draft': project_cases.filter(status='draft').count(),
                'active': project_cases.filter(status='active').count(),
                'deprecated': project_cases.filter(status='deprecated').count(),
                'high_priority': project_cases.filter(priority='high').count() + project_cases.filter(priority='critical').count(),
            })
        
        # 按状态统计
        status_stats = {
            'draft': queryset.filter(status='draft').count(),
            'active': queryset.filter(status='active').count(),
            'deprecated': queryset.filter(status='deprecated').count(),
        }
        
        # 按优先级统计
        priority_stats = {
            'critical': queryset.filter(priority='critical').count(),
            'high': queryset.filter(priority='high').count(),
            'medium': queryset.filter(priority='medium').count(),
            'low': queryset.filter(priority='low').count(),
        }
        
        # 自动化覆盖率统计（按优先级）
        from apps.api_testing.models import TestSuite
        automated_case_ids = set(
            TestSuite.objects.filter(
                mainline_test_case__isnull=False
            ).values_list('mainline_test_case_id', flat=True).distinct()
        )
        automated_cases = queryset.filter(id__in=automated_case_ids)
        automation_coverage = {}
        for priority in ['critical', 'high', 'medium', 'low']:
            total = priority_stats[priority]
            automated = automated_cases.filter(priority=priority).count()
            automation_coverage[priority] = {
                'total': total,
                'automated': automated,
                'rate': round(automated / total * 100, 2) if total else 0,
            }
        total_all = sum(priority_stats.values())
        automated_all = automated_cases.count()
        automation_coverage['total'] = {
            'total': total_all,
            'automated': automated_all,
            'rate': round(automated_all / total_all * 100, 2) if total_all else 0,
        }
        
        # 按作者统计（包含优先级细分和积分）
        # 用例数量统计所有用例，积分只统计审核通过的用例
        approved_queryset = queryset.filter(review_status='approved')
        author_stats = []
        from django.db.models import Count
        authors = queryset.exclude(author__isnull=True).exclude(author__username__isnull=True).values('author__username').annotate(count=Count('id')).order_by('-count')[:10]
        for author in authors:
            username = author['author__username']
            author_cases = queryset.filter(author__username=username)
            # 用例数量（所有用例）
            critical = author_cases.filter(priority='critical').count()
            high = author_cases.filter(priority='high').count()
            medium = author_cases.filter(priority='medium').count()
            low = author_cases.filter(priority='low').count()
            # 积分（只统计审核通过的用例）
            approved_cases = approved_queryset.filter(author__username=username)
            approved_critical = approved_cases.filter(priority='critical').count()
            approved_high = approved_cases.filter(priority='high').count()
            approved_medium = approved_cases.filter(priority='medium').count()
            approved_low = approved_cases.filter(priority='low').count()
            score = (approved_critical + approved_high) // 5 + (approved_medium + approved_low) // 10
            author_stats.append({
                'username': username,
                'count': author['count'],
                'critical': critical,
                'high': high,
                'medium': medium,
                'low': low,
                'score': score,
                'all_approved': author_cases.filter(review_status='approved').count() == author_cases.count(),
            })
        
        # 按月份统计（近12个月）
        monthly_stats = []
        
        # 获取活跃作者列表（按贡献量排序取前8个）
        top_authors = [a['username'] for a in author_stats[:8]] if author_stats else []
        
        # 获取用例创建时间范围
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 只统计近12个月的数据
        year, month = current_month.year, current_month.month
        month -= 11
        while month <= 0:
            month += 12
            year -= 1
        start_month = current_month.replace(year=year, month=month)
        
        # 从起始月份到当前月份，逐月统计
        month_start_dt = start_month
        while month_start_dt <= current_month:
                # 计算下个月初
                if month_start_dt.month == 12:
                    month_end_dt = month_start_dt.replace(year=month_start_dt.year + 1, month=1)
                else:
                    month_end_dt = month_start_dt.replace(month=month_start_dt.month + 1)
                
                month_cases = queryset.filter(created_at__gte=month_start_dt, created_at__lt=month_end_dt)
                
                # 按作者统计该月新增用例（按优先级细分）
                # 用例数量统计所有用例，积分只统计审核通过的用例
                author_detail_counts = {}
                for author in top_authors:
                    author_cases = month_cases.filter(author__username=author)
                    # 用例数量（所有用例）
                    author_detail_counts[author] = {
                        'critical': author_cases.filter(priority='critical').count(),
                        'high': author_cases.filter(priority='high').count(),
                        'medium': author_cases.filter(priority='medium').count(),
                        'low': author_cases.filter(priority='low').count(),
                        'total': author_cases.count(),
                    }
                    # 积分（只统计审核通过的用例）
                    approved_cases = month_cases.filter(author__username=author, review_status='approved')
                    approved_critical = approved_cases.filter(priority='critical').count()
                    approved_high = approved_cases.filter(priority='high').count()
                    approved_medium = approved_cases.filter(priority='medium').count()
                    approved_low = approved_cases.filter(priority='low').count()
                    author_detail_counts[author]['score'] = (approved_critical + approved_high) // 5 + (approved_medium + approved_low) // 10
                    # 是否全部审核通过
                    author_detail_counts[author]['all_approved'] = author_cases.filter(review_status='approved').count() == author_cases.count()
                
                # 统计该月更新用例（创建或编辑时间落在该月）
                month_updated = queryset.filter(
                    updated_at__gte=month_start_dt,
                    updated_at__lt=month_end_dt
                )
                
                monthly_stats.append({
                    'month': month_start_dt.strftime('%Y-%m'),
                    'count': month_cases.count(),
                    'updated': month_updated.count(),
                    'author_detail_counts': author_detail_counts,
                })
                month_start_dt = month_end_dt
        
        return Response({
            'total': queryset.count(),
            'status_stats': status_stats,
            'priority_stats': priority_stats,
            'automation_coverage': automation_coverage,
            'project_stats': project_stats,
            'author_stats': author_stats,
            'monthly_stats': monthly_stats,
            'top_authors': top_authors,
        })
    except Exception as e:
        import sys
        import traceback
        logger.error(f"testcase_statistics error: {type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())
        return Response({
            'error': str(e),
            'type': type(e).__name__,
            'detail': traceback.format_exception(type(e), e, e.__traceback__),
        }, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def author_test_cases(request):
    """获取指定作者的用例列表（不按项目权限隔离）"""
    username = request.GET.get('username')
    priority = request.GET.get('priority', '')
    month = request.GET.get('month', '')
    
    if not username:
        return Response({'error': 'username参数必填'}, status=400)
    
    # 获取该作者的所有用例，不再按项目权限过滤
    queryset = TestCase.objects.filter(
        author__username=username
    ).select_related('author', 'project')
    
    # 按月份筛选
    if month:
        try:
            year, mon = month.split('-')
            from datetime import date
            import calendar
            month_start = date(int(year), int(mon), 1)
            if int(mon) == 12:
                month_end = date(int(year) + 1, 1, 1)
            else:
                month_end = date(int(year), int(mon) + 1, 1)
            queryset = queryset.filter(
                created_at__gte=datetime.datetime.combine(month_start, datetime.time.min),
                created_at__lt=datetime.datetime.combine(month_end, datetime.time.min)
            )
        except (ValueError, IndexError):
            pass
    
    # 按优先级筛选
    if priority:
        queryset = queryset.filter(priority=priority)
    
    queryset = queryset.order_by('-created_at')
    
    cases = []
    for case in queryset[:200]:  # 限制返回200条
        # 获取归属目录（菜单路径）
        directory = ''
        if case.menu:
            directory = case.menu.name
            # 如果有父级菜单，拼接完整路径
            parent = case.menu.parent
            while parent:
                directory = f"{parent.name} / {directory}"
                parent = parent.parent
            # 加上所属端名称
            if case.project:
                directory = f"{case.project.name} / {directory}"
        elif case.project:
            directory = case.project.name
        
        cases.append({
            'id': case.id,
            'title': case.title,
            'priority': case.priority,
            'status': case.status,
            'review_status': case.review_status,
            'review_comment': case.review_comment,
            'reviewed_at': case.reviewed_at.strftime('%Y-%m-%d %H:%M') if case.reviewed_at else None,
            'directory': directory or '未分配',
            'menu_id': case.menu_id,
            'created_at': case.created_at.strftime('%Y-%m-%d %H:%M') if case.created_at else None,
            'precondition': case.preconditions,
            'steps': case.steps,
            'expected_result': case.expected_result,
            'author': {
                'id': case.author.id if case.author else None,
                'username': case.author.username if case.author else None,
                'name': case.author.get_full_name() if case.author else None,
            } if case.author else None,
        })
    
    # 按目录分组
    grouped = {}
    for case in cases:
        dir_name = case['directory']
        if dir_name not in grouped:
            grouped[dir_name] = []
        grouped[dir_name].append(case)
    
    # 转换为前端需要的树形结构
    grouped_list = [
        {
            'directory': dir_name,
            'count': len(items),
            'cases': items
        }
        for dir_name, items in grouped.items()
    ]
    # 按用例数量降序排列
    grouped_list.sort(key=lambda x: x['count'], reverse=True)
    
    # 审核结果统计
    review_stats = {
        'approved': queryset.filter(review_status='approved').count(),
        'rejected': queryset.filter(review_status='rejected').count(),
        'pending': queryset.filter(review_status__in=['pending', 'none']).count(),
    }
    
    return Response({
        'total': queryset.count(),
        'grouped': grouped_list,
        'cases': cases,  # 保留平铺数据备用
        'review_stats': review_stats,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def batch_update_review_status(request):
    """批量修改用例审核结果"""
    ids = request.data.get('ids', [])
    review_status = request.data.get('review_status')
    review_comment = request.data.get('review_comment', '')

    if not ids:
        return Response({'error': 'ids参数必填'}, status=400)
    if review_status not in ['pending', 'approved', 'rejected', 'none']:
        return Response({'error': 'review_status参数无效'}, status=400)
    if review_status == 'rejected' and not str(review_comment).strip():
        return Response({'error': '拒绝时必须填写拒绝理由'}, status=400)

    updated = TestCase.objects.filter(id__in=ids).update(
        review_status=review_status,
        review_comment=review_comment,
        reviewer=request.user,
        reviewed_at=timezone.now()
    )

    return Response({
        'success': True,
        'updated_count': updated,
        'review_status': review_status
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def ai_review_test_cases(request):
    """一键AI审核所有待审核用例。

    审核规则：
    1. 测试步骤不能少于3步
    2. 用例名称必填且全局不重复
    3. 前置条件不能为空
    4. 主线用例只描述当前最新功能，步骤和预期不能包含【原有规则】【调整】【历史数据】
    5. 相同归属目录下：P0 <= 3 个，P1 <= 10 个，P2~P4 不限
    6. 相同归属目录下，不同用例的测试步骤和预期结果重复率不能100%

    违反任意一条规则，审核结果设为已拒绝并记录原因；全部通过则设为已通过。
    """
    username = request.data.get('username')
    month = request.data.get('month', '')

    queryset = TestCase.objects.filter(review_status__in=['pending', 'none'])
    if username:
        queryset = queryset.filter(author__username=username)
    if month:
        try:
            year, mon = month.split('-')
            from datetime import date
            month_start = date(int(year), int(mon), 1)
            if int(mon) == 12:
                month_end = date(int(year) + 1, 1, 1)
            else:
                month_end = date(int(year), int(mon) + 1, 1)
            queryset = queryset.filter(
                created_at__gte=datetime.datetime.combine(month_start, datetime.time.min),
                created_at__lt=datetime.datetime.combine(month_end, datetime.time.min)
            )
        except (ValueError, IndexError):
            pass

    queryset = queryset.select_related('author', 'project', 'menu').prefetch_related('step_details')
    cases = list(queryset)

    if not cases:
        return Response({
            'success': True,
            'updated_count': 0,
            'approved_count': 0,
            'rejected_count': 0,
            'results': []
        })

    # 规则2：全局用例名称重复统计（忽略空标题）
    title_counts = dict(
        TestCase.objects
        .exclude(title__isnull=True)
        .exclude(title='')
        .values('title')
        .annotate(count=models.Count('id'))
        .values_list('title', 'count')
    )

    # 按归属目录分组，用于规则5、6（需考虑目录下所有用例，不局限于当前作者）
    directory_keys = {get_directory_key(case) for case in cases}
    directory_all_cases = {}
    if directory_keys:
        q = models.Q()
        for project_id, menu_id in directory_keys:
            if project_id is None and menu_id is None:
                q |= models.Q(project__isnull=True, menu__isnull=True)
            elif menu_id is None:
                q |= models.Q(project_id=project_id, menu__isnull=True)
            else:
                q |= models.Q(project_id=project_id, menu_id=menu_id)
        for c in TestCase.objects.filter(q).select_related('project', 'menu').prefetch_related('step_details'):
            directory_all_cases.setdefault(get_directory_key(c), []).append(c)

    # 规则5：目录内优先级数量
    directory_priority_counts = {}
    for key, all_cases in directory_all_cases.items():
        directory_priority_counts[key] = {
            'critical': sum(1 for c in all_cases if c.priority == 'critical'),
            'high': sum(1 for c in all_cases if c.priority == 'high'),
        }

    # 规则6：目录内步骤+预期100%重复分组
    directory_duplicate_groups = {}
    for key, all_cases in directory_all_cases.items():
        content_groups = {}
        for c in all_cases:
            content = f"{c.steps or ''}\n{c.expected_result or ''}".strip()
            if content:
                content_groups.setdefault(content, []).append(c)
        directory_duplicate_groups[key] = [
            group for group in content_groups.values() if len(group) > 1
        ]

    forbidden_keywords = ['【原有规则】', '【调整】', '【历史数据】']
    now = timezone.now()
    results = []
    updated_cases = []

    for case in cases:
        violations = []

        # 规则1：步骤不少于3步
        if case.test_type == 'step':
            step_count = case.step_details.count()
        else:
            step_count = count_text_steps(case.steps)
        if step_count < 3:
            violations.append(f'测试步骤不能少于3步（当前{step_count}步）')

        # 规则2：名称必填且全局不重复
        title = (case.title or '').strip()
        if not title:
            violations.append('用例名称必填')
        elif title_counts.get(title, 0) > 1:
            violations.append('用例名称全局重复')

        # 规则3：前置条件非空
        if not (case.preconditions or '').strip():
            violations.append('前置条件不能为空')

        # 规则4：主线用例不能包含历史/调整类描述
        content = f"{case.steps or ''}\n{case.expected_result or ''}"
        found = [k for k in forbidden_keywords if k in content]
        if found:
            violations.append(f'主线用例步骤/预期中不得包含：{"、".join(found)}')

        key = get_directory_key(case)

        # 规则5：同目录优先级数量限制
        p0_count = directory_priority_counts.get(key, {}).get('critical', 0)
        p1_count = directory_priority_counts.get(key, {}).get('high', 0)
        if case.priority == 'critical' and p0_count > 3:
            violations.append(f'相同归属目录下P0级用例不能超过3个（当前{p0_count}个）')
        if case.priority == 'high' and p1_count > 10:
            violations.append(f'相同归属目录下P1级用例不能超过10个（当前{p1_count}个）')

        # 规则6：同目录步骤+预期100%重复
        duplicates = []
        for group in directory_duplicate_groups.get(key, []):
            if case in group:
                duplicates.extend([c.title for c in group if c.id != case.id])
        if duplicates:
            duplicates = list(dict.fromkeys(duplicates))[:3]
            violations.append(f'与以下用例测试步骤和预期结果100%重复：{"、".join(duplicates)}')

        if violations:
            case.review_status = 'rejected'
            case.review_comment = '；'.join(violations)
        else:
            case.review_status = 'approved'
            case.review_comment = ''

        case.reviewer = request.user
        case.reviewed_at = now
        updated_cases.append(case)
        results.append({
            'id': case.id,
            'title': case.title,
            'review_status': case.review_status,
            'review_comment': case.review_comment,
        })

    TestCase.objects.bulk_update(
        updated_cases,
        ['review_status', 'review_comment', 'reviewer', 'reviewed_at'],
        batch_size=100
    )

    return Response({
        'success': True,
        'updated_count': len(updated_cases),
        'approved_count': sum(1 for r in results if r['review_status'] == 'approved'),
        'rejected_count': sum(1 for r in results if r['review_status'] == 'rejected'),
        'results': results
    })


# ==================== 关联自动化场景 API ====================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def link_testcase_to_suite(request, pk):
    """将测试用例与接口自动化场景（TestSuite）一一关联"""
    try:
        testcase = TestCase.objects.get(pk=pk)
    except TestCase.DoesNotExist:
        return Response({'error': '测试用例不存在'}, status=status.HTTP_404_NOT_FOUND)

    suite_id = request.data.get('suite_id')
    if not suite_id:
        return Response({'error': 'suite_id 参数必填'}, status=status.HTTP_400_BAD_REQUEST)

    from apps.api_testing.models import TestSuite

    try:
        suite = TestSuite.objects.get(pk=suite_id)
    except TestSuite.DoesNotExist:
        return Response({'error': '自动化场景不存在'}, status=status.HTTP_404_NOT_FOUND)

    # 检查该 TestSuite 是否已关联到其他 TestCase
    if suite.mainline_test_case_id and suite.mainline_test_case_id != testcase.id:
        return Response({
            'error': f'该场景已关联到其他用例（ID: {suite.mainline_test_case_id}），请先取消该关联'
        }, status=status.HTTP_409_CONFLICT)

    # 检查该 TestCase 是否已关联其他 TestSuite
    existing_suite = TestSuite.objects.filter(mainline_test_case=testcase).exclude(pk=suite_id).first()
    if existing_suite:
        return Response({
            'error': f'该用例已关联到另一个场景 "{existing_suite.name}"（ID: {existing_suite.id}），请先取消该关联'
        }, status=status.HTTP_409_CONFLICT)

    suite.mainline_test_case = testcase
    suite.save(update_fields=['mainline_test_case', 'updated_at'])

    return Response({
        'success': True,
        'message': f'已成功将用例 "{testcase.title}" 关联到场景 "{suite.name}"',
        'testcase_id': testcase.id,
        'suite_id': suite.id,
        'suite_name': suite.name,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unlink_testcase_from_suite(request, pk):
    """取消测试用例与接口自动化场景的关联"""
    try:
        testcase = TestCase.objects.get(pk=pk)
    except TestCase.DoesNotExist:
        return Response({'error': '测试用例不存在'}, status=status.HTTP_404_NOT_FOUND)

    from apps.api_testing.models import TestSuite

    suite_id = request.data.get('suite_id')
    if suite_id:
        # 取消指定的关联
        try:
            suite = TestSuite.objects.get(pk=suite_id, mainline_test_case=testcase)
            suite.mainline_test_case = None
            suite.mainline_case_checked_at = None
            suite.save(update_fields=['mainline_test_case', 'mainline_case_checked_at', 'updated_at'])
            return Response({
                'success': True,
                'message': f'已取消用例与场景 "{suite.name}" 的关联',
            })
        except TestSuite.DoesNotExist:
            return Response({'error': '未找到该关联关系'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # 取消该用例的所有关联
        suites = TestSuite.objects.filter(mainline_test_case=testcase)
        count = suites.count()
        suites.update(mainline_test_case=None, mainline_case_checked_at=None)
        return Response({
            'success': True,
            'message': f'已取消该用例的所有关联（共 {count} 个场景）',
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def available_suites_for_testcase(request, pk):
    """获取可关联到此用例的自动化场景列表（供关联弹窗选择）"""
    from apps.api_testing.models import TestSuite

    # 获取所有未关联到其他用例的 TestSuite（或已关联到此用例的）
    available = TestSuite.objects.filter(
        models.Q(mainline_test_case__isnull=True) | models.Q(mainline_test_case_id=pk)
    ).select_related('project', 'mainline_test_case').order_by('name')

    # 支持搜索
    search = request.query_params.get('search', '')
    if search:
        available = available.filter(name__icontains=search)

    # 支持项目筛选
    project_id = request.query_params.get('project_id')
    if project_id:
        available = available.filter(project_id=project_id)

    suites_data = []
    for s in available[:50]:  # 限制返回数量
        suites_data.append({
            'id': s.id,
            'name': s.name,
            'project_id': s.project_id,
            'project_name': s.project.name if s.project else '',
            'description': s.description or '',
            'is_linked': s.mainline_test_case_id == int(pk),
            'linked_to_other': s.mainline_test_case_id is not None and s.mainline_test_case_id != int(pk),
        })

    return Response(suites_data)
