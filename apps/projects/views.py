from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from .models import Project, ProjectMember, ProjectEnvironment, ProjectMenu
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectMemberSerializer, 
    ProjectEnvironmentSerializer, ProjectMenuSerializer, ProjectMenuCreateSerializer
)

class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectSerializer
    
    def get_queryset(self):
        # 显示所有项目，和用例列表保持一致
        return Project.objects.all().distinct()

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_all_projects(request):
    """获取所有项目列表，用于下拉选择等场景"""
    projects = Project.objects.all().values('id', 'name', 'description', 'status')
    return Response(list(projects))


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_projects_with_menus(request):
    """获取所有项目及其完整目录树结构"""
    projects = Project.objects.all()
    result = []
    for project in projects:
        # 获取顶级菜单
        root_menus = ProjectMenu.objects.filter(project=project, parent=None).order_by('sort_order', 'created_at')
        project_data = {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status,
            'menus': ProjectMenuSerializer(root_menus, many=True).data
        }
        result.append(project_data)
    return Response(result)

class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        """删除项目，但保留关联的测试用例"""
        from apps.testcases.models import TestCase
        from django.db import transaction
        
        project = self.get_object()
        
        with transaction.atomic():
            # 获取该项目下的所有用例ID
            testcase_ids = list(TestCase.objects.filter(project=project).values_list('id', flat=True))
            
            # 先将关联的测试用例的 menu 和 project 字段都设为 null
            # 这样可以避免菜单级联删除时影响用例
            updated_count = TestCase.objects.filter(project=project).update(menu=None, project=None)
            
            # 删除项目（会级联删除关联的菜单）
            project.delete()
        
        return Response({
            'message': f'项目删除成功，已保留 {updated_count} 个关联的测试用例',
            'preserved_testcases': testcase_ids
        }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_project_member(request, project_id):
    try:
        project = Project.objects.get(id=project_id)
        if project.owner != request.user:
            return Response({'error': '无权限添加成员'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ProjectMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(project=project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Project.DoesNotExist:
        return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_project_members(request, project_id):
    """获取项目成员列表"""
    try:
        project = Project.objects.get(id=project_id)
        
        # 检查用户是否有权限查看项目成员
        if not (project.owner == request.user or 
                ProjectMember.objects.filter(project=project, user=request.user).exists()):
            return Response({'error': '无权限查看项目成员'}, status=status.HTTP_403_FORBIDDEN)
        
        # 获取项目成员，包括项目所有者
        members = []
        
        # 添加项目所有者
        members.append({
            'id': project.owner.id,
            'username': project.owner.username,
            'email': project.owner.email,
            'first_name': project.owner.first_name,
            'last_name': project.owner.last_name,
            'role': 'owner'
        })
        
        # 添加项目成员
        project_members = ProjectMember.objects.filter(project=project).select_related('user')
        for member in project_members:
            members.append({
                'id': member.user.id,
                'username': member.user.username,
                'email': member.user.email,
                'first_name': member.user.first_name,
                'last_name': member.user.last_name,
                'role': member.role
            })
        
        return Response(members)
    except Project.DoesNotExist:
        return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_project_member(request, project_id, member_id):
    try:
        project = Project.objects.get(id=project_id)
        if project.owner != request.user:
            return Response({'error': '无权限删除成员'}, status=status.HTTP_403_FORBIDDEN)
        
        member = ProjectMember.objects.get(id=member_id, project=project)
        member.delete()
        return Response({'message': '成员删除成功'})
    except (Project.DoesNotExist, ProjectMember.DoesNotExist):
        return Response({'error': '项目或成员不存在'}, status=status.HTTP_404_NOT_FOUND)

class ProjectEnvironmentListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectEnvironmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        project_id = self.kwargs['project_id']
        return ProjectEnvironment.objects.filter(project_id=project_id)
    
    def perform_create(self, serializer):
        project_id = self.kwargs['project_id']
        serializer.save(project_id=project_id)


# ==================== 端菜单管理视图 ====================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_project_menus(request, project_id):
    """获取端的所有菜单（树形结构）"""
    try:
        project = Project.objects.get(id=project_id)
        # 只获取顶级菜单，子菜单会通过序列化器递归获取
        menus = ProjectMenu.objects.filter(project=project, parent=None).order_by('sort_order', 'created_at')
        serializer = ProjectMenuSerializer(menus, many=True)
        return Response(serializer.data)
    except Project.DoesNotExist:
        return Response({'error': '端不存在'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_project_menu(request, project_id):
    """创建端菜单"""
    try:
        project = Project.objects.get(id=project_id)
        
        data = request.data.copy()
        data['project'] = project_id
        
        serializer = ProjectMenuCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        menu = serializer.save()
        
        return Response(ProjectMenuSerializer(menu).data, status=status.HTTP_201_CREATED)
    except Project.DoesNotExist:
        return Response({'error': '端不存在'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_project_menu(request, project_id, menu_id):
    """更新端菜单"""
    try:
        project = Project.objects.get(id=project_id)
        menu = ProjectMenu.objects.get(id=menu_id, project=project)
        
        serializer = ProjectMenuCreateSerializer(menu, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        menu = serializer.save()
        
        return Response(ProjectMenuSerializer(menu).data)
    except Project.DoesNotExist:
        return Response({'error': '端不存在'}, status=status.HTTP_404_NOT_FOUND)
    except ProjectMenu.DoesNotExist:
        return Response({'error': '菜单不存在'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_project_menu(request, project_id, menu_id):
    """删除端菜单"""
    try:
        project = Project.objects.get(id=project_id)
        menu = ProjectMenu.objects.get(id=menu_id, project=project)
        menu.delete()
        return Response({'message': '菜单删除成功'})
    except Project.DoesNotExist:
        return Response({'error': '端不存在'}, status=status.HTTP_404_NOT_FOUND)
    except ProjectMenu.DoesNotExist:
        return Response({'error': '菜单不存在'}, status=status.HTTP_404_NOT_FOUND)