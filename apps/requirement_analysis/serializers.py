from rest_framework import serializers
from .models import (
    RequirementDocument, RequirementAnalysis, BusinessRequirement,
    GeneratedTestCase, AnalysisTask, AIModelConfig, PromptConfig, TestCaseGenerationTask,
    GenerationConfig, TestTemplateConfig, TestTemplateCategory,
    KnowledgeGraph, KnowledgeGraphQueryHistory, KnowledgeGraphBuildTask
)


class RequirementDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RequirementDocument
        fields = ['id', 'title', 'file', 'file_url', 'document_type', 'document_type_display', 
                 'status', 'status_display', 'uploaded_by', 'uploaded_by_name', 'project', 
                 'project_name', 'created_at', 'updated_at', 'file_size', 'extracted_text']
        read_only_fields = ['uploaded_by', 'file_size', 'extracted_text']
    
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class BusinessRequirementSerializer(serializers.ModelSerializer):
    requirement_type_display = serializers.CharField(source='get_requirement_type_display', read_only=True)
    requirement_level_display = serializers.CharField(source='get_requirement_level_display', read_only=True)
    parent_requirement_name = serializers.CharField(source='parent_requirement.requirement_name', read_only=True)
    
    class Meta:
        model = BusinessRequirement
        fields = ['id', 'requirement_id', 'requirement_name', 'requirement_type', 
                 'requirement_type_display', 'parent_requirement', 'parent_requirement_name',
                 'module', 'requirement_level', 'requirement_level_display', 'reviewer', 
                 'estimated_hours', 'description', 'acceptance_criteria', 'created_at', 'updated_at']


class RequirementAnalysisSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    document_id = serializers.IntegerField(source='document.id', read_only=True)
    requirements = BusinessRequirementSerializer(many=True, read_only=True)
    
    class Meta:
        model = RequirementAnalysis
        fields = ['id', 'document_id', 'document_title', 'analysis_report', 
                 'requirements_count', 'analysis_time', 'created_at', 'updated_at', 'requirements']


class GeneratedTestCaseSerializer(serializers.ModelSerializer):
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requirement_name = serializers.CharField(source='requirement.requirement_name', read_only=True)
    requirement_id_display = serializers.CharField(source='requirement.requirement_id', read_only=True)
    
    class Meta:
        model = GeneratedTestCase
        fields = ['id', 'case_id', 'title', 'priority', 'priority_display', 'precondition',
                 'test_steps', 'expected_result', 'status', 'status_display', 'generated_by_ai',
                 'reviewed_by_ai', 'review_comments', 'requirement', 'requirement_name', 
                 'requirement_id_display', 'created_at', 'updated_at']


class AnalysisTaskSerializer(serializers.ModelSerializer):
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = AnalysisTask
        fields = ['id', 'task_id', 'task_type', 'task_type_display', 'document', 'document_title',
                 'status', 'status_display', 'progress', 'result', 'error_message', 
                 'started_at', 'completed_at', 'created_at', 'duration']
        read_only_fields = ['task_id', 'result', 'error_message', 'started_at', 'completed_at']
    
    def get_duration(self, obj):
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class DocumentUploadSerializer(serializers.ModelSerializer):
    """文档上传专用序列化器"""
    class Meta:
        model = RequirementDocument
        fields = ['id', 'title', 'file', 'project']
    
    def create(self, validated_data):
        # 自动设置上传者（如果用户已登录）
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['uploaded_by'] = user
        else:
            # 如果是匿名用户，使用第一个超级用户作为默认用户
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['uploaded_by'] = default_user
        
        # 根据文件扩展名设置文档类型
        file = validated_data['file']
        if file.name.lower().endswith('.pdf'):
            validated_data['document_type'] = 'pdf'
        elif file.name.lower().endswith(('.doc', '.docx')):
            validated_data['document_type'] = 'docx'
        elif file.name.lower().endswith('.txt'):
            validated_data['document_type'] = 'txt'
        elif file.name.lower().endswith('.md'):
            validated_data['document_type'] = 'md'
        elif file.name.lower().endswith('.png'):
            validated_data['document_type'] = 'png'
        elif file.name.lower().endswith('.jpg'):
            validated_data['document_type'] = 'jpg'
        elif file.name.lower().endswith('.jpeg'):
            validated_data['document_type'] = 'jpeg'
        elif file.name.lower().endswith('.gif'):
            validated_data['document_type'] = 'gif'
        
        # 设置文件大小
        validated_data['file_size'] = file.size
        
        return super().create(validated_data)


class TestCaseGenerationRequestSerializer(serializers.Serializer):
    """测试用例生成请求序列化器"""
    # 输入源类型：manual(手动输入), file(文件上传), kb_chunks(知识库切片)
    input_source = serializers.ChoiceField(
        choices=[('manual', '手动输入'), ('file', '文件上传'), ('kb_chunks', '知识库切片')],
        default='manual',
        help_text="输入源类型"
    )
    
    # 对于手动输入和文件上传，使用需求ID列表
    requirement_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="需求ID列表（手动输入和文件上传时使用）"
    )
    
    # 对于知识库切片，使用切片ID列表
    chunk_ids = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        required=False,
        help_text="切片ID列表，格式：[{document_id: 1, chunk_index: 0}, {document_id: 2, chunk_index: 3}]（知识库切片时使用）"
    )
    
    test_level = serializers.ChoiceField(
        choices=[('unit', '单元测试'), ('integration', '集成测试'), ('system', '系统测试'), ('acceptance', '验收测试')],
        default='system',
        help_text="测试级别"
    )
    test_priority = serializers.ChoiceField(
        choices=[('P0', '最高优先级'), ('P1', '高优先级'), ('P2', '中优先级'), ('P3', '低优先级')],
        default='P1',
        help_text="测试优先级"
    )
    test_case_count = serializers.IntegerField(
        min_value=1,
        max_value=200,
        default=50,
        help_text="生成测试用例数量"
    )

    def validate(self, data):
        input_source = data.get('input_source', 'manual')
        
        if input_source in ['manual', 'file']:
            if not data.get('requirement_ids'):
                raise serializers.ValidationError("手动输入和文件上传方式需要提供 requirement_ids")
        elif input_source == 'kb_chunks':
            if not data.get('chunk_ids'):
                raise serializers.ValidationError("知识库切片方式需要提供 chunk_ids")
        
        return data


class TestCaseReviewRequestSerializer(serializers.Serializer):
    """测试用例评审请求序列化器"""
    test_case_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="测试用例ID列表"
    )
    review_criteria = serializers.CharField(
        max_length=500,
        default="检查测试用例的完整性、准确性和可执行性",
        help_text="评审标准"
    )


class AIModelConfigSerializer(serializers.ModelSerializer):
    """AI模型配置序列化器"""
    model_type_display = serializers.CharField(source='get_model_type_display', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    api_key_masked = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = AIModelConfig
        fields = ['id', 'name', 'model_type', 'model_type_display', 'role', 'role_display',
                 'api_key', 'api_key_masked', 'base_url', 'model_name', 'max_tokens', 'temperature', 'top_p', 
                 'is_active', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_by_name']
        extra_kwargs = {
            'api_key': {'write_only': True}  # API Key只用于写入，不在响应中返回
        }
    
    def get_api_key_masked(self, obj):
        """返回掩码版本的API Key"""
        if obj.api_key:
            # 显示前3个字符和后4个字符，中间用*替代
            if len(obj.api_key) > 7:
                return f"{obj.api_key[:3]}{'*' * (len(obj.api_key) - 7)}{obj.api_key[-4:]}"
            else:
                return '*' * len(obj.api_key)
        return ''
    
    def create(self, validated_data):
        # 自动设置创建者
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        else:
            # 如果是匿名用户，使用第一个超级用户作为默认用户
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['created_by'] = default_user
        
        return super().create(validated_data)


class PromptConfigSerializer(serializers.ModelSerializer):
    """提示词配置序列化器"""
    prompt_type_display = serializers.CharField(source='get_prompt_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = PromptConfig
        fields = ['id', 'name', 'prompt_type', 'prompt_type_display', 'content', 'is_active',
                 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_by_name']
    
    def create(self, validated_data):
        # 自动设置创建者
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        else:
            # 如果是匿名用户，使用第一个超级用户作为默认用户
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['created_by'] = default_user
        
        return super().create(validated_data)


class TestCaseGenerationTaskSerializer(serializers.ModelSerializer):
    """测试用例生成任务序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    output_mode_display = serializers.CharField(source='get_output_mode_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    writer_model_name = serializers.CharField(source='writer_model_config.name', read_only=True)
    reviewer_model_name = serializers.CharField(source='reviewer_model_config.name', read_only=True)
    writer_prompt_name = serializers.CharField(source='writer_prompt_config.name', read_only=True)
    reviewer_prompt_name = serializers.CharField(source='reviewer_prompt_config.name', read_only=True)

    class Meta:
        model = TestCaseGenerationTask
        fields = ['id', 'task_id', 'title', 'requirement_text', 'status', 'status_display',
                 'output_mode', 'output_mode_display', 'progress', 'project', 'project_name',
                 'writer_model_config', 'writer_model_name', 'reviewer_model_config', 'reviewer_model_name',
                 'writer_prompt_config', 'writer_prompt_name', 'reviewer_prompt_config', 'reviewer_prompt_name',
                 'generated_test_cases', 'review_feedback', 'final_test_cases', 'generation_log', 'error_message',
                 'created_by', 'created_by_name', 'created_at', 'updated_at', 'completed_at']
        read_only_fields = ['task_id', 'status', 'progress', 'generated_test_cases',
                          'review_feedback', 'final_test_cases', 'generation_log',
                          'error_message', 'created_by', 'completed_at']
    
    def create(self, validated_data):
        # 自动设置创建者和任务ID
        import uuid
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        else:
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['created_by'] = default_user
        
        validated_data['task_id'] = f"TASK_{uuid.uuid4().hex[:8].upper()}"
        
        return super().create(validated_data)


class NewTestCaseGenerationRequestSerializer(serializers.Serializer):
    """新的测试用例生成请求序列化器"""
    title = serializers.CharField(max_length=200, help_text="任务标题")
    requirement_text = serializers.CharField(help_text="需求描述")
    use_writer_model = serializers.BooleanField(default=True, help_text="是否使用编写模型")
    use_reviewer_model = serializers.BooleanField(default=True, help_text="是否使用评审模型")


class GenerationConfigSerializer(serializers.ModelSerializer):
    """生成行为配置序列化器"""
    default_output_mode_display = serializers.CharField(source='get_default_output_mode_display', read_only=True)

    class Meta:
        model = GenerationConfig
        fields = [
            'id', 'name', 'default_output_mode', 'default_output_mode_display',
            'enable_auto_review', 'review_timeout',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


# ==================== 测试模板配置序列化器 ====================

class TestTemplateConfigSerializer(serializers.ModelSerializer):
    """测试模板配置序列化器"""
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    keywords_list = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()

    class Meta:
        model = TestTemplateConfig
        fields = [
            'id', 'name', 'template_type', 'template_type_display',
            'keywords', 'keywords_list', 'content', 'content_preview',
            'priority', 'module_category', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_keywords_list(self, obj):
        """返回关键词列表"""
        return obj.get_keywords_list()

    def get_content_preview(self, obj):
        """返回内容预览（限制长度）"""
        content = obj.content
        if isinstance(content, list):
            preview = ', '.join(str(item) for item in content[:3])
            if len(content) > 3:
                preview += f' 等{len(content)}项'
            return preview
        elif isinstance(content, dict):
            return f'包含 {len(content)} 个字段的对象'
        return str(content)[:100]

    def validate_keywords(self, value):
        """验证关键词格式"""
        if not value or not value.strip():
            raise serializers.ValidationError('关键词不能为空')

        keywords = [k.strip() for k in value.replace('/', ',').split(',') if k.strip()]
        if not keywords:
            raise serializers.ValidationError('至少需要提供一个关键词')

        return value

    def validate_content(self, value):
        """验证内容格式"""
        if value is None:
            raise serializers.ValidationError('模板内容不能为空')

        # 根据模板类型验证内容格式
        template_type = self.initial_data.get('template_type')

        if template_type == 'test_point':
            if not isinstance(value, list):
                raise serializers.ValidationError('测试点模板的内容必须是数组格式')
            if len(value) == 0:
                raise serializers.ValidationError('测试点列表不能为空')

        elif template_type == 'test_scenario':
            if not isinstance(value, list):
                raise serializers.ValidationError('测试场景模板的内容必须是数组格式')
            if len(value) == 0:
                raise serializers.ValidationError('测试场景列表不能为空')

        elif template_type == 'precondition':
            if isinstance(value, dict):
                if 'precondition' not in value:
                    raise serializers.ValidationError('前置条件模板必须包含 precondition 字段')
            elif not isinstance(value, str):
                raise serializers.ValidationError('前置条件模板的内容必须是字符串或对象格式')

        return value


class TestTemplateCategorySerializer(serializers.ModelSerializer):
    """测试模板分类序列化器"""

    class Meta:
        model = TestTemplateCategory
        fields = ['id', 'name', 'description', 'icon', 'sort_order', 'is_active']


class TestTemplateBatchCreateSerializer(serializers.Serializer):
    """批量创建模板序列化器"""
    templates = serializers.ListField(
        child=serializers.DictField(),
        help_text='模板数据列表'
    )


class TestTemplateMatchTestSerializer(serializers.Serializer):
    """测试模板匹配序列化器"""
    text = serializers.CharField(required=True, help_text='测试文本')
    template_type = serializers.CharField(required=False, allow_blank=True, help_text='模板类型筛选')


# ==================== 测试模板配置序列化器结束 ====================


# ==================== LightRAG 知识图谱序列化器 ====================

class KnowledgeGraphSerializer(serializers.ModelSerializer):
    """知识图谱序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    document_count = serializers.SerializerMethodField()
    is_public = serializers.BooleanField(default=False)
    public_access_level = serializers.ChoiceField(
        choices=[('read', '只读'), ('write', '可编辑')],
        default='read'
    )
    graph_id = serializers.CharField(source='get_graph_id', read_only=True)

    class Meta:
        model = KnowledgeGraph
        fields = [
            'id', 'graph_id', 'name', 'description', 'project', 'project_name',
            'status', 'status_display', 'node_count', 'edge_count', 'document_count',
            'build_started_at', 'build_completed_at', 'build_error_message',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'is_public', 'public_access_level'
        ]
        read_only_fields = [
            'node_count', 'edge_count', 'build_started_at',
            'build_completed_at', 'build_error_message', 'created_by'
        ]

    def get_document_count(self, obj):
        """获取关联文档数量"""
        return obj.documents.count()

    def get_graph_id(self, obj):
        """获取图谱存储ID"""
        return obj.get_graph_id()


class KnowledgeGraphBuildRequestSerializer(serializers.Serializer):
    """知识图谱构建请求序列化器"""
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        min_length=1,
        help_text='需求文档ID列表'
    )


class KnowledgeGraphQuerySerializer(serializers.Serializer):
    """知识图谱查询请求序列化器"""
    question = serializers.CharField(
        required=True,
        min_length=1,
        max_length=2000,
        help_text='查询问题'
    )
    mode = serializers.ChoiceField(
        choices=[('local', '局部查询'), ('global', '全局查询'), ('mix', '混合查询')],
        default='mix',
        help_text='查询模式'
    )


class KnowledgeGraphStatsSerializer(serializers.Serializer):
    """知识图谱统计信息序列化器"""
    graph_id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    has_graph = serializers.BooleanField()
    nodes = serializers.IntegerField()
    edges = serializers.IntegerField()
    documents = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    build_completed_at = serializers.DateTimeField()


class KnowledgeGraphVersionCompareSerializer(serializers.Serializer):
    """知识图谱版本对比请求序列化器"""
    base_version = serializers.CharField(
        required=True,
        max_length=20,
        help_text='基准版本，如 V1'
    )
    compare_version = serializers.CharField(
        required=True,
        max_length=20,
        help_text='对比版本，如 V3'
    )


class KnowledgeGraphQueryHistorySerializer(serializers.ModelSerializer):
    """知识图谱查询历史序列化器"""
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = KnowledgeGraphQueryHistory
        fields = [
            'id', 'question', 'answer', 'mode', 'mode_display',
            'query_time', 'created_at', 'created_by_name'
        ]


class KnowledgeGraphBuildTaskSerializer(serializers.ModelSerializer):
    """知识图谱构建任务序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    graph_name = serializers.CharField(source='graph.name', read_only=True)
    
    class Meta:
        model = KnowledgeGraphBuildTask
        fields = [
            'id', 'task_id', 'graph', 'graph_name', 'status', 'status_display',
            'progress', 'current_document', 'error_message',
            'started_at', 'completed_at', 'created_at'
        ]


# ==================== LightRAG 知识图谱序列化器结束 ====================
