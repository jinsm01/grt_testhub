from rest_framework import serializers
from .models import TestCase, TestCaseStep, TestCaseAttachment, TestCaseComment
from apps.users.serializers import UserSerializer
from apps.versions.serializers import VersionSimpleSerializer

class TestCaseStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseStep
        fields = '__all__'

class TestCaseAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    
    class Meta:
        model = TestCaseAttachment
        fields = '__all__'

class TestCaseCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = TestCaseComment
        fields = '__all__'

class TestCaseWriteMixin:
    """创建/更新用例时共享的归属目录和作者处理逻辑"""

    def _resolve_author(self, author_name):
        """根据用户名查找用户，找不到返回 None"""
        from apps.users.models import User
        if not author_name:
            return None
        user = User.objects.filter(username=author_name).first()
        if not user:
            user = User.objects.filter(username__icontains=author_name).first()
        return user

    def _process_category_path(self, category_path, validated_data):
        """处理归属目录路径，自动创建端和菜单"""
        from apps.projects.models import Project, ProjectMenu
        from apps.users.models import User

        path_parts = [p.strip() for p in category_path.split('/') if p.strip()]
        if not path_parts:
            return

        project_name = path_parts[0]
        menu_names = path_parts[1:]

        project = Project.objects.filter(name=project_name).first()
        if not project:
            current_user = self.context.get('request').user if self.context.get('request') else None
            project = Project.objects.create(
                name=project_name,
                description=f'从测试用例导入自动创建的端：{project_name}',
                owner=current_user if current_user else User.objects.first(),
                status='active'
            )
            if current_user:
                project.members.add(current_user)

        validated_data['project'] = project

        if menu_names:
            parent_menu = None
            for menu_name in menu_names:
                menu = ProjectMenu.objects.filter(
                    project=project,
                    name=menu_name,
                    parent=parent_menu
                ).first()

                if not menu:
                    menu = ProjectMenu.objects.create(
                        project=project,
                        name=menu_name,
                        parent=parent_menu,
                        description=f'从测试用例导入自动创建的菜单：{menu_name}'
                    )

                parent_menu = menu

            if parent_menu:
                validated_data['menu'] = parent_menu


class ProjectSimpleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()

class TestCaseSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    project = ProjectSimpleSerializer(read_only=True)
    versions = VersionSimpleSerializer(many=True, read_only=True)
    step_details = TestCaseStepSerializer(many=True, read_only=True)
    attachments = TestCaseAttachmentSerializer(many=True, read_only=True)
    comments = TestCaseCommentSerializer(many=True, read_only=True)
    category_path = serializers.SerializerMethodField()
    reviewer = UserSerializer(read_only=True)
    automation_scenario = serializers.SerializerMethodField()
    
    review_status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TestCase
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_automation_scenario(self, obj):
        """返回关联的接口自动化场景（TestSuite）"""
        from apps.api_testing.models import TestSuite
        suite = TestSuite.objects.filter(mainline_test_case=obj).first()
        if suite:
            return {
                'id': suite.id,
                'name': suite.name,
                'project_id': suite.project_id,
                'updated_at': suite.updated_at
            }
        return None
    
    def get_review_status_display(self, obj):
        """获取审核状态的中文显示"""
        status_map = {
            'none': '未审核',
            'pending': '待审核',
            'approved': '已通过',
            'rejected': '已拒绝',
        }
        return status_map.get(obj.review_status, obj.review_status)

    class Meta:
        model = TestCase
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_category_path(self, obj):
        """获取完整的归属目录路径：端名称/菜单/子菜单"""
        if not obj.project:
            return None

        path_parts = [obj.project.name]

        # 获取菜单层级
        menu = obj.menu
        menu_names = []
        while menu:
            menu_names.insert(0, menu.name)
            menu = menu.parent

        path_parts.extend(menu_names)
        return '/'.join(path_parts)

class TestCaseListSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    assignee = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    menu = serializers.SerializerMethodField()
    category_path = serializers.SerializerMethodField()
    reviewer = serializers.SerializerMethodField()
    automation_scenario = serializers.SerializerMethodField()
    
    review_status_display = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        fields = [
            'id', 'title', 'description', 'preconditions', 'steps', 'expected_result',
            'priority', 'test_type', 'module',
            'author', 'assignee', 'project', 'versions', 'tags', 'created_at', 'updated_at',
            'menu', 'category_path', 'review_status', 'review_status_display', 'review_comment', 'reviewer',
            'automation_scenario'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_automation_scenario(self, obj):
        """返回关联的接口自动化场景（TestSuite）"""
        from apps.api_testing.models import TestSuite
        suite = TestSuite.objects.filter(mainline_test_case=obj).first()
        if suite:
            return {
                'id': suite.id,
                'name': suite.name,
                'project_id': suite.project_id
            }
        return None
    
    def get_reviewer(self, obj):
        return {'id': obj.reviewer.id, 'username': obj.reviewer.username} if obj.reviewer else None
    
    def get_review_status_display(self, obj):
        """获取审核状态的中文显示"""
        status_map = {
            'none': '未审核',
            'pending': '待审核',
            'approved': '已通过',
            'rejected': '已拒绝',
        }
        return status_map.get(obj.review_status, obj.review_status)

    def get_author(self, obj):
        return {'id': obj.author.id, 'username': obj.author.username} if obj.author else None

    def get_assignee(self, obj):
        return {'id': obj.assignee.id, 'username': obj.assignee.username} if obj.assignee else None

    def get_project(self, obj):
        return {'id': obj.project.id, 'name': obj.project.name} if obj.project else None

    def get_versions(self, obj):
        return [{'id': v.id, 'name': v.name, 'is_baseline': v.is_baseline} for v in obj.versions.all()]

    def get_menu(self, obj):
        if obj.menu:
            return {'id': obj.menu.id, 'name': obj.menu.name, 'parent_id': obj.menu.parent_id}
        return None

    def get_category_path(self, obj):
        """获取完整的归属目录路径：端名称/菜单/子菜单"""
        if not obj.project:
            return None

        path_parts = [obj.project.name]

        # 获取菜单层级
        menu = obj.menu
        menu_names = []
        while menu:
            menu_names.insert(0, menu.name)
            menu = menu.parent

        path_parts.extend(menu_names)
        return '/'.join(path_parts)

class TestCaseCreateSerializer(TestCaseWriteMixin, serializers.ModelSerializer):
    version_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="关联版本ID列表"
    )
    author_name = serializers.CharField(required=False, allow_null=True, help_text="作者用户名，可选")
    created_at = serializers.DateTimeField(required=False, allow_null=True, help_text="创建时间，可选")
    category_path = serializers.CharField(required=False, allow_null=True, help_text="归属目录路径，格式：端名称/菜单/子菜单，可选")

    class Meta:
        model = TestCase
        fields = [
            'title', 'description', 'preconditions', 'steps', 'expected_result',
            'priority', 'test_type', 'module', 'tags', 'version_ids', 'author_name', 'created_at', 'category_path'
        ]

    def create(self, validated_data):
        from apps.users.models import User
        from apps.projects.models import Project, ProjectMenu
        version_ids = validated_data.pop('version_ids', [])
        author_name = validated_data.pop('author_name', None)
        created_at = validated_data.pop('created_at', None)
        category_path = validated_data.pop('category_path', None)
        request_user = validated_data.pop('request_user', None)

        # 如果指定了作者用户名，查找对应的用户
        if author_name:
            user = self._resolve_author(author_name)
            if user:
                validated_data['author'] = user
            else:
                raise serializers.ValidationError(f"创建人 '{author_name}' 不存在于平台，请先添加该用户或检查用户名是否正确")
        else:
            # 如果没有指定作者，直接报错，不允许导入
            raise serializers.ValidationError("创建人不能为空，请填写创建人字段")

        # 如果指定了创建时间，设置创建时间
        if created_at:
            validated_data['created_at'] = created_at

        # 处理归属目录路径（必须，用于确定端和菜单）
        if category_path:
            try:
                self._process_category_path(category_path, validated_data)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing category_path {category_path}: {e}")
                raise serializers.ValidationError(f"处理归属目录路径失败: {e}")
        else:
            raise serializers.ValidationError("归属目录路径不能为空")

        testcase = super().create(validated_data)

        # 设置版本关联
        if version_ids:
            testcase.versions.set(version_ids)

        return testcase

class TestCaseUpdateSerializer(TestCaseWriteMixin, serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="项目ID，可选")
    version_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False, 
        allow_empty=True,
        help_text="关联版本ID列表"
    )
    author_name = serializers.CharField(required=False, allow_null=True, help_text="作者用户名，可选")
    category_path = serializers.CharField(required=False, allow_null=True, help_text="归属目录路径，格式：端名称/菜单/子菜单，可选")
    
    class Meta:
        model = TestCase
        fields = [
            'title', 'description', 'preconditions', 'steps', 'expected_result',
            'priority', 'test_type', 'module', 'tags', 'project_id', 'version_ids',
            'review_status', 'review_comment', 'author_name', 'category_path'
        ]

    def update(self, instance, validated_data):
        version_ids = validated_data.pop('version_ids', None)
        # project_id会在视图中处理
        validated_data.pop('project_id', None)
        author_name = validated_data.pop('author_name', None)
        category_path = validated_data.pop('category_path', None)
        
        # 如果指定了作者用户名，查找对应的用户
        if author_name is not None:
            user = self._resolve_author(author_name)
            if user:
                validated_data['author'] = user
            else:
                raise serializers.ValidationError(f"创建人 '{author_name}' 不存在于平台")
        
        # 如果指定了归属目录路径，重新解析端和菜单
        if category_path is not None:
            self._process_category_path(category_path, validated_data)
        
        instance = super().update(instance, validated_data)
        
        # 更新版本关联
        if version_ids is not None:
            instance.versions.set(version_ids)

        return instance

