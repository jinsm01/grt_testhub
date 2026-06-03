from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DataFactoryRecord(models.Model):
    """数据工厂使用记录"""

    TOOL_CATEGORIES = (
        ('test_data', '测试数据'),
        ('json', 'JSON工具'),
        ('string', '字符工具'),
        ('encoding', '编码工具'),
        ('random', '随机工具'),
        ('encryption', '加密工具'),
        ('crontab', 'Crontab工具'),
    )

    TOOL_SCENARIOS = (
        ('test_data', '测试数据'),
        ('json', 'JSON工具'),
        ('string', '字符工具'),
        ('encoding', '编码工具'),
        ('random', '随机工具'),
        ('encryption', '加密工具'),
        ('crontab', 'Crontab工具'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    tool_name = models.CharField(max_length=100, verbose_name='工具名称')
    tool_category = models.CharField(max_length=20, choices=TOOL_CATEGORIES, verbose_name='工具分类')
    tool_scenario = models.CharField(max_length=20, choices=TOOL_SCENARIOS, verbose_name='使用场景')
    custom_name = models.CharField(max_length=200, verbose_name='自定义名称', null=True, blank=True)
    input_data = models.JSONField(verbose_name='输入数据', null=True, blank=True)
    output_data = models.JSONField(verbose_name='输出数据')
    is_saved = models.BooleanField(default=True, verbose_name='是否保存')
    tags = models.JSONField(verbose_name='标签', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'data_factory_record'
        verbose_name = '数据工厂记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['tool_category']),
            models.Index(fields=['tool_scenario']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.tool_name}"


class BugAnalysisRecord(models.Model):
    """
    Bug 分析记录

    支持历史回溯和跨版本趋势对比:
    - 保存原始 Bug 数据 + 完整分析结果
    - 支持版本标签标记 (如 "v6.0.0-2026-04-16")
    - 记录数据来源 (Excel上传 / API同步)
    - AI 增强分析结果也保存在此
    """

    SOURCE_TYPE_CHOICES = (
        ('excel', 'Excel上传'),
        ('json_api', 'JSON API'),
        ('yunxiao_api', '云效API'),
        ('tapd_api', 'TAPD API'),
    )

    id = models.AutoField(primary_key=True)
    version_tag = models.CharField(max_length=100, verbose_name='版本标签', default='', blank=True,
                                     help_text="如 v6.0.0-release、2026-Q2-sprint5 等")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default='excel',
                                    verbose_name='数据来源')
    file_name = models.CharField(max_length=255, blank=True, default='', verbose_name='源文件名')
    total_bugs = models.IntegerField(default=0, verbose_name='Bug总数')

    # 原始数据: 标准化后的 Bug 列表 (每条包含 title/desc/severity/status/creator/created/module/defect_type/inferred_sev 等)
    raw_bugs = models.JSONField(default=list, verbose_name='原始Bug数据')

    # 分析结果: analyze_bugs() 返回的完整字典 (含 modulesData/severityCrossData/riskData 等全部维度)
    analysis_result = models.JSONField(default=dict, verbose_name='分析结果')

    # 元信息
    created_by = models.CharField(max_length=50, default='system', verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'df_bug_analysis_record'
        verbose_name = 'Bug分析记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['source_type']),
            models.Index(fields=['version_tag']),
            models.Index(fields=['total_bugs']),
        ]

    def __str__(self):
        tag = f"[{self.version_tag}]" if self.version_tag else ""
        return f"Bug分析 {tag} {self.file_name or self.source_type} ({self.total_bugs}条) @{self.created_at:%Y-%m-%d %H:%M}"

    @property
    def p0_count(self) -> int:
        """推断 P0 数量"""
        return (self.analysis_result or {}).get('sevInfData', {}).get('推断P0', 0)

    @property
    def p1_count(self) -> int:
        """推断 P1 数量"""
        return (self.analysis_result or {}).get('sevInfData', {}).get('推断P1', 0)

    @property
    def top_module(self) -> str:
        """Bug数最多的模块"""
        modules = (self.analysis_result or {}).get('modulesData', {})
        if modules:
            return max(modules.items(), key=lambda x: x[1])[0]
        return ''


class BugAnalysisSummaryRecord(models.Model):
    """
    Bug 汇总分析记录

    保存汇总分析的结果，支持历史回溯
    """

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name='汇总分析名称', default='', blank=True)
    group_by = models.CharField(max_length=20, verbose_name='时间聚合方式', default='month',
                                 help_text="week|month|quarter|half_year|year")

    # 关联的记录ID列表
    record_ids = models.JSONField(default=list, verbose_name='关联分析记录ID列表')

    # 汇总数据
    total_bugs = models.IntegerField(default=0, verbose_name='总Bug数')
    total_modules = models.IntegerField(default=0, verbose_name='涉及模块数')
    record_count = models.IntegerField(default=0, verbose_name='分析记录数')
    online_bugs = models.IntegerField(default=0, verbose_name='线上故障数')
    defect_bugs = models.IntegerField(default=0, verbose_name='缺陷数')

    # 详细汇总数据
    summary_data = models.JSONField(default=dict, verbose_name='汇总数据',
                                     help_text="包含 trends/module_ranking/risk_modules 等")

    # AI 洞察报告
    ai_insight = models.TextField(blank=True, default='', verbose_name='AI洞察报告')

    # 元信息
    created_by = models.CharField(max_length=50, default='system', verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'df_bug_analysis_summary_record'
        verbose_name = 'Bug汇总分析记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['created_by']),
            models.Index(fields=['group_by']),
        ]

    def __str__(self):
        return f"Bug汇总分析 {self.name or '未命名'} ({self.total_bugs}条) @{self.created_at:%Y-%m-%d %H:%M}"

    @property
    def record_ids_list(self) -> list:
        """获取关联记录ID列表"""
        return self.record_ids or []

    def to_list_dict(self) -> dict:
        """转换为列表展示的格式"""
        return {
            'id': self.id,
            'name': self.name or f'汇总分析 {self.created_at.strftime("%Y%m%d")}',
            'record_count': self.record_count,
            'total_bugs': self.total_bugs,
            'group_by': self.group_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }

    def to_detail_dict(self) -> dict:
        """转换为详情展示的格式"""
        return {
            'id': self.id,
            'name': self.name or f'汇总分析 {self.created_at.strftime("%Y%m%d")}',
            'record_count': self.record_count,
            'group_by': self.group_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': {
                'total_bugs': self.total_bugs,
                'total_modules': self.total_modules,
                'record_count': self.record_count,
                'online_bugs': self.online_bugs,
                'defect_bugs': self.defect_bugs,
            },
            'trends': self.summary_data.get('trends', []),
            'module_ranking': self.summary_data.get('module_ranking', []),
            'risk_modules': self.summary_data.get('risk_modules', []),
            'ai_insight': self.ai_insight,
        }


class AIRubricRecord(models.Model):
    """AI 评分量表生成记录"""

    STATUS_CHOICES = (
        ('running', '生成中'),
        ('done', '已完成'),
        ('error', '失败'),
    )

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    name = models.CharField(max_length=200, verbose_name='任务名称')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running', verbose_name='状态')

    # 上传的源文件
    source_file = models.FileField(upload_to='rubric/sources/%Y/%m/', null=True, blank=True, verbose_name='源文件')
    source_file_name = models.CharField(max_length=255, blank=True, default='', verbose_name='源文件名')

    # 配置参数
    note_count = models.IntegerField(default=20, verbose_name='心得数量')
    pass_ratio = models.FloatField(default=0.6, verbose_name='得分心得比例')

    # 生成的结果文件
    rubric_file = models.FileField(upload_to='rubric/output/%Y/%m/', null=True, blank=True, verbose_name='量表文件(XLSX)')
    notes_file = models.FileField(upload_to='rubric/notes/%Y/%m/', null=True, blank=True, verbose_name='心得文件(DOCX)')

    # 生成的数据（JSON格式保存）
    rubric_data = models.JSONField(default=list, verbose_name='量表数据')
    notes_data = models.JSONField(default=list, verbose_name='心得数据')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'df_ai_rubric_record'
        verbose_name = 'AI量表生成记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()}) @{self.created_at:%Y-%m-%d %H:%M}"

    def to_list_dict(self) -> dict:
        """转换为列表展示格式"""
        d = {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'source_file_name': self.source_file_name,
            'note_count': self.note_count,
            'pass_ratio': self.pass_ratio,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        # 已完成的记录附带完整数据，供前端下载使用
        if self.status in ('done', 'error'):
            d['rubric_data'] = self.rubric_data or []
            d['notes_data'] = self.notes_data or []
        else:
            d['rubric_data'] = []
            d['notes_data'] = []
        return d
