from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

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

    # AI 分析状态 (异步模式)
    AI_STATUS_CHOICES = (
        ('none', '无'),
        ('pending', '待分析'),
        ('running', '分析中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    )
    ai_status = models.CharField(max_length=20, choices=AI_STATUS_CHOICES, default='none',
                                  verbose_name='AI分析状态')
    ai_progress = models.IntegerField(default=0, verbose_name='AI分析进度', help_text='0-100')

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


class BugSyncItem(models.Model):
    """
    Bug 同步项 - 追踪单条 Bug 与云效的双向同步状态

    支持:
    - 本地创建的 Bug 推送到云效
    - 从云效拉取的 Bug 记录 workitem ID
    - 状态变更追踪 (本地 vs 云效)
    - 冲突检测 (双向同时修改)
    """

    SYNC_STATUS_CHOICES = (
        ('pending', '待同步'),
        ('synced', '已同步'),
        ('conflict', '冲突'),
        ('failed', '失败'),
    )

    id = models.AutoField(primary_key=True)
    # 关联分析记录
    analysis_record = models.ForeignKey(
        BugAnalysisRecord, on_delete=models.CASCADE,
        related_name='sync_items', null=True, blank=True,
        verbose_name='关联分析记录'
    )

    # 云效侧标识
    yunxiao_workitem_id = models.CharField(max_length=100, blank=True, default='',
                                            verbose_name='云效工作项ID')
    yunxiao_serial_number = models.CharField(max_length=100, blank=True, default='',
                                              verbose_name='云效序列号')

    # 本地 Bug 数据 (JSON 存储完整 Bug 信息)
    local_data = models.JSONField(default=dict, verbose_name='本地Bug数据')

    # 云效侧最新数据缓存 (用于对比变更)
    remote_data_cache = models.JSONField(default=dict, blank=True, verbose_name='云效数据缓存')

    # 同步状态
    sync_status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES,
                                    default='pending', verbose_name='同步状态')
    last_synced_at = models.DateTimeField(null=True, blank=True, verbose_name='最后同步时间')
    last_remote_check_at = models.DateTimeField(null=True, blank=True, verbose_name='最后远程检查时间')

    # 版本哈希 (用于检测变更)
    local_version_hash = models.CharField(max_length=64, blank=True, default='', verbose_name='本地版本哈希')
    remote_version_hash = models.CharField(max_length=64, blank=True, default='', verbose_name='远程版本哈希')

    # 元信息
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'df_bug_sync_item'
        verbose_name = 'Bug同步项'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['yunxiao_workitem_id']),
            models.Index(fields=['sync_status']),
            models.Index(fields=['analysis_record']),
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self):
        title = (self.local_data or {}).get('title', '无标题')
        return f"BugSyncItem [{self.sync_status}] {title[:30]} @{self.updated_at:%Y-%m-%d %H:%M}"

    def mark_synced(self, remote_data: dict):
        """标记为已同步"""
        self.remote_data_cache = remote_data
        self.last_synced_at = timezone.now()
        self.sync_status = 'synced'

    def mark_conflict(self):
        """标记为冲突"""
        self.sync_status = 'conflict'

    def mark_failed(self):
        """标记为失败"""
        self.sync_status = 'failed'

    def update_local(self, local_data: dict):
        """更新本地数据"""
        self.local_data = local_data
        self.sync_status = 'pending'
        self.save(update_fields=['local_data', 'sync_status', 'updated_at'])

    def to_list_dict(self) -> dict:
        """转换为列表展示格式"""
        # 处理时间字段，转换为本地时间
        last_synced_at = '-'
        if self.last_synced_at:
            last_synced_at = timezone.localtime(self.last_synced_at).strftime('%Y-%m-%d %H:%M:%S')
        
        created_at = timezone.localtime(self.created_at).strftime('%Y-%m-%d %H:%M:%S')
        updated_at = timezone.localtime(self.updated_at).strftime('%Y-%m-%d %H:%M:%S')
        
        d = {
            'id': self.id,
            'yunxiao_workitem_id': self.yunxiao_workitem_id,
            'yunxiao_serial_number': self.yunxiao_serial_number,
            'sync_status': self.sync_status,
            'sync_status_display': self.get_sync_status_display(),
            'last_synced_at': last_synced_at,
            'local_data': self.local_data,
            'created_at': created_at,
            'updated_at': updated_at,
        }
        return d


class YunxiaoToken(models.Model):
    """
    云效访问令牌配置 - 团队成员可添加各自的Token，通过下拉选择使用

    支持:
    - 多人协作: 每个成员可添加自己的云效PAT令牌
    - 标签化: 为Token添加备注标签(如"张三-日常用")
    - 启停控制: 可临时禁用某个Token
    - 安全存储: 令牌仅在服务端存储，前端展示时脱敏
    """

    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=100, verbose_name='标签/备注', default='',
                              help_text="如: 张三-日常使用、李四-CI专用")
    token = models.CharField(max_length=500, verbose_name='云效访问令牌(PAT)')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    # 元信息
    created_by = models.CharField(max_length=50, default='system', verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'df_yunxiao_token'
        verbose_name = '云效令牌配置'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        status = '启用' if self.is_active else '禁用'
        return f"[{status}] {self.label or f'Token#{self.id}'} ({self.created_by})"

    def mask_token(self) -> str:
        """脱敏显示Token"""
        if not self.token or len(self.token) <= 8:
            return '****'
        return self.token[:4] + '****' + self.token[-4:]

    def to_list_dict(self) -> dict:
        """转换为列表展示格式 (Token脱敏)"""
        local_tz = timezone.get_current_timezone()
        return {
            'id': self.id,
            'label': self.label,
            'token_masked': self.mask_token(),
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': timezone.localtime(self.created_at, local_tz).strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': timezone.localtime(self.updated_at, local_tz).strftime('%Y-%m-%d %H:%M:%S'),
        }

    def to_select_dict(self) -> dict:
        """转换为下拉选择格式"""
        label = self.label or f'Token#{self.id}'
        return {
            'id': self.id,
            'label': label,
            'display': f"{label} ({self.created_by})",
            'is_active': self.is_active,
        }
