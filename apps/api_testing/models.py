from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import Dict, Any, List
import json

User = get_user_model()


class SoftDeleteQuerySet(models.QuerySet):
    """软删除 QuerySet"""

    def alive(self):
        """返回未删除的数据"""
        return self.filter(is_deleted=False)

    def deleted(self):
        """返回已删除的数据"""
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """软删除 Manager - 默认只返回未删除的数据"""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def all_with_deleted(self):
        """返回所有数据（包括已删除的）"""
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted(self):
        """只返回已删除的数据"""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()


class SoftDeleteModel(models.Model):
    """软删除基础模型"""
    is_deleted = models.BooleanField(default=False, verbose_name='是否已删除')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='删除时间')

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # 原始管理器，可访问所有数据

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """软删除：标记为已删除而不是物理删除"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """物理删除：真正从数据库中删除"""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """恢复已删除的数据"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class ApiProject(SoftDeleteModel):
    """API项目模型"""
    PROJECT_TYPE_CHOICES = [
        ('HTTP', 'HTTP'),
        ('WEBSOCKET', 'WebSocket'),
    ]

    STATUS_CHOICES = [
        ('NOT_STARTED', '未开始'),
        ('IN_PROGRESS', '进行中'),
        ('COMPLETED', '已结束'),
    ]

    name = models.CharField(max_length=200, verbose_name='项目名称')
    description = models.TextField(blank=True, verbose_name='项目描述')
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPE_CHOICES, verbose_name='项目类型')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='项目状态')
    start_date = models.DateField(null=True, blank=True, verbose_name='开始日期')
    end_date = models.DateField(null=True, blank=True, verbose_name='结束日期')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_api_projects', verbose_name='负责人')
    members = models.ManyToManyField(User, blank=True, related_name='api_projects', verbose_name='团队成员')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_projects'
        verbose_name = 'API项目'
        verbose_name_plural = 'API项目'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ApiCollection(SoftDeleteModel):
    """API集合模型"""
    name = models.CharField(max_length=200, verbose_name='集合名称')
    description = models.TextField(blank=True, verbose_name='集合描述')
    order = models.IntegerField(default=0, verbose_name='排序')
    project = models.ForeignKey(ApiProject, on_delete=models.CASCADE, related_name='collections',
                                verbose_name='所属项目')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children',
                               verbose_name='父级集合')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_collections'
        verbose_name = 'API集合'
        verbose_name_plural = 'API集合'
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.name


class ApiRequest(SoftDeleteModel):
    """API请求模型"""
    REQUEST_TYPE_CHOICES = [
        ('HTTP', 'HTTP'),
        ('WEBSOCKET', 'WebSocket'),
    ]

    HTTP_METHODS = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
        ('HEAD', 'HEAD'),
        ('OPTIONS', 'OPTIONS'),
    ]

    collection = models.ForeignKey(ApiCollection, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='requests', verbose_name='所属集合')
    name = models.CharField(max_length=200, verbose_name='请求名称')
    description = models.TextField(blank=True, verbose_name='请求描述')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES, default='HTTP',
                                    verbose_name='请求类型')
    method = models.CharField(max_length=10, choices=HTTP_METHODS, default='GET', verbose_name='请求方法')
    url = models.TextField(verbose_name='请求URL')
    headers = models.JSONField(default=dict, verbose_name='请求头')
    params = models.JSONField(default=dict, verbose_name='URL参数')
    path_params = models.JSONField(default=list, verbose_name='路径参数')
    body = models.JSONField(default=dict, verbose_name='请求体')
    auth = models.JSONField(default=dict, verbose_name='认证信息')
    pre_request_script = models.TextField(blank=True, verbose_name='请求前脚本')
    post_request_script = models.TextField(blank=True, verbose_name='请求后脚本')
    assertions = models.JSONField(default=list, verbose_name='断言规则')
    variable_extractors = models.JSONField(default=list, verbose_name='变量提取规则')
    order = models.IntegerField(default=0, verbose_name='排序')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_requests'
        verbose_name = 'API请求'
        verbose_name_plural = 'API请求'
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.name


class Environment(models.Model):
    """环境变量模型"""
    SCOPE_CHOICES = [
        ('GLOBAL', '全局环境变量'),
        ('LOCAL', '局部环境变量'),
    ]

    name = models.CharField(max_length=200, verbose_name='环境名称')
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, verbose_name='作用域')
    variables = models.JSONField(default=dict, verbose_name='环境变量')
    is_active = models.BooleanField(default=False, verbose_name='是否激活')
    project = models.ForeignKey(ApiProject, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='environments', verbose_name='关联项目')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_environments'
        verbose_name = '环境变量'
        verbose_name_plural = '环境变量'

    def __str__(self):
        return f"{self.name} ({self.get_scope_display()})"


class RequestHistory(SoftDeleteModel):
    """请求历史模型"""
    request = models.ForeignKey(ApiRequest, on_delete=models.CASCADE, related_name='histories', verbose_name='关联请求')
    environment = models.ForeignKey(Environment, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='使用环境')
    request_data = models.JSONField(verbose_name='请求数据')
    response_data = models.JSONField(null=True, blank=True, verbose_name='响应数据')
    status_code = models.IntegerField(null=True, blank=True, verbose_name='状态码')
    response_time = models.FloatField(null=True, blank=True, verbose_name='响应时间(ms)')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    assertions_results = models.JSONField(null=True, blank=True, verbose_name='断言结果')
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='执行者')
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name='执行时间')

    class Meta:
        db_table = 'api_request_histories'
        verbose_name = '请求历史'
        verbose_name_plural = '请求历史'
        ordering = ['-executed_at']

    def __str__(self):
        return f"{self.request.name} - {self.executed_at}"


class TestSuite(SoftDeleteModel):
    """测试套件模型（自动化测试）"""
    project = models.ForeignKey(ApiProject, on_delete=models.CASCADE, related_name='test_suites',
                                verbose_name='所属项目')
    name = models.CharField(max_length=200, verbose_name='套件名称')
    description = models.TextField(blank=True, verbose_name='套件描述')
    requests = models.ManyToManyField(ApiRequest, through='TestSuiteRequest', verbose_name='包含请求')
    environment = models.ForeignKey(Environment, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='执行环境')
    pre_process_script = models.TextField(blank=True, verbose_name='前置处理脚本')
    post_process_script = models.TextField(blank=True, verbose_name='后置处理脚本')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_test_suites',
                                   verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    # 关联主线用例
    mainline_test_case = models.ForeignKey(
        'testcases.TestCase', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='api_test_suites', verbose_name='关联主线用例',
        help_text='将该接口测试场景与主线用例一对一关联'
    )
    mainline_case_checked_at = models.DateTimeField(
        null=True, blank=True, verbose_name='主线用例已确认时间',
        help_text='上次确认主线用例内容的时间，用于提示用例内容是否有更新'
    )

    class Meta:
        db_table = 'api_test_suites'
        verbose_name = '测试套件'
        verbose_name_plural = '测试套件'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TestSuiteRequest(SoftDeleteModel):
    """测试套件中的请求关联模型"""
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, verbose_name='测试套件')
    request = models.ForeignKey(ApiRequest, on_delete=models.CASCADE, verbose_name='API请求', null=True, blank=True)
    order = models.IntegerField(default=0, verbose_name='执行顺序')
    assertions = models.JSONField(default=list, verbose_name='断言规则')
    extracted_variables = models.JSONField(default=dict, verbose_name='变量提取规则')
    enabled = models.BooleanField(default=True, verbose_name='是否启用')
    
    # 支持分组结构
    parent_id = models.IntegerField(null=True, blank=True, verbose_name='父分组ID')
    step_type = models.CharField(max_length=20, default='request', verbose_name='步骤类型')  # request, group

    # 接口覆盖配置字段
    override_name = models.CharField(max_length=200, blank=True, verbose_name='覆盖接口名称')
    override_method = models.CharField(max_length=10, blank=True, verbose_name='覆盖请求方法')
    override_url = models.TextField(blank=True, verbose_name='覆盖请求URL')
    override_headers = models.JSONField(default=dict, blank=True, verbose_name='覆盖请求头')
    override_params = models.JSONField(default=dict, blank=True, verbose_name='覆盖请求参数')
    override_body = models.JSONField(default=dict, blank=True, verbose_name='覆盖请求体')
    pre_script = models.TextField(blank=True, verbose_name='前置脚本')
    post_script = models.TextField(blank=True, verbose_name='后置脚本')

    class Meta:
        db_table = 'api_test_suite_requests'
        verbose_name = '套件请求'
        verbose_name_plural = '套件请求'
        ordering = ['order']

    def __str__(self):
        return f"{self.test_suite.name} - {self.request.name}"

    def get_effective_method(self):
        """获取有效的请求方法"""
        return self.override_method or self.request.method

    def get_effective_url(self):
        """获取有效的请求URL"""
        return self.override_url or self.request.url

    def get_effective_headers(self):
        """获取有效的请求头（合并原始和覆盖）"""
        headers = dict(self.request.headers or {})
        headers.update(self.override_headers or {})
        return headers

    def get_effective_params(self):
        """获取有效的请求参数（合并原始和覆盖）"""
        params = dict(self.request.params or {})
        params.update(self.override_params or {})
        return params

    def get_effective_body(self):
        """获取有效的请求体"""
        if self.override_body:
            return self.override_body
        return self.request.body


class TestExecution(SoftDeleteModel):
    """测试执行模型"""
    EXECUTION_STATUS_CHOICES = [
        ('PENDING', '待执行'),
        ('RUNNING', '执行中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '执行失败'),
        ('CANCELLED', '已取消'),
    ]

    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='executions',
                                   verbose_name='测试套件')
    status = models.CharField(max_length=20, choices=EXECUTION_STATUS_CHOICES, default='PENDING',
                              verbose_name='执行状态')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    total_requests = models.IntegerField(default=0, verbose_name='总请求数')
    passed_requests = models.IntegerField(default=0, verbose_name='通过请求数')
    failed_requests = models.IntegerField(default=0, verbose_name='失败请求数')
    results = models.JSONField(default=dict, verbose_name='执行结果')
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='执行者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'api_test_executions'
        verbose_name = '测试执行'
        verbose_name_plural = '测试执行'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.test_suite.name} - {self.created_at}"


# 定时任务相关模型
class ScheduledTask(SoftDeleteModel):
    """定时任务模型"""
    TASK_TYPE_CHOICES = [
        ('TEST_SUITE', '测试套件执行'),
        ('API_REQUEST', 'API请求执行'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', '激活'),
        ('PAUSED', '暂停'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
    ]

    TRIGGER_TYPE_CHOICES = [
        ('CRON', 'Cron表达式'),
        ('INTERVAL', '固定间隔'),
        ('ONCE', '单次执行'),
    ]

    name = models.CharField(max_length=200, verbose_name='任务名称')
    description = models.TextField(blank=True, verbose_name='任务描述')
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, verbose_name='任务类型')
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES, verbose_name='触发器类型')

    # Cron表达式配置
    cron_expression = models.CharField(max_length=100, blank=True, verbose_name='Cron表达式')

    # 固定间隔配置（秒）
    interval_seconds = models.IntegerField(null=True, blank=True, verbose_name='间隔秒数')

    # 单次执行时间
    execute_at = models.DateTimeField(null=True, blank=True, verbose_name='执行时间')

    # 任务配置
    test_suite = models.ForeignKey('TestSuite', on_delete=models.CASCADE, null=True, blank=True,
                                   verbose_name='测试套件')
    api_request = models.ForeignKey('ApiRequest', on_delete=models.CASCADE, null=True, blank=True,
                                    verbose_name='API请求')
    environment = models.ForeignKey('Environment', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='执行环境')

    # 状态管理
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='任务状态')
    last_run_time = models.DateTimeField(null=True, blank=True, verbose_name='最后运行时间')
    next_run_time = models.DateTimeField(null=True, blank=True, verbose_name='下次运行时间')
    total_runs = models.IntegerField(default=0, verbose_name='总运行次数')
    successful_runs = models.IntegerField(default=0, verbose_name='成功运行次数')
    failed_runs = models.IntegerField(default=0, verbose_name='失败运行次数')

    # 执行结果
    last_result = models.JSONField(default=dict, verbose_name='最后执行结果')
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    # 通知配置
    notify_on_success = models.BooleanField(default=False, verbose_name='成功时通知')
    notify_on_failure = models.BooleanField(default=True, verbose_name='失败时通知')
    notify_emails = models.JSONField(default=list, verbose_name='通知邮箱列表')

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_scheduled_tasks'
        verbose_name = '定时任务'
        verbose_name_plural = '定时任务'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_task_type_display()})"

    def calculate_next_run(self):
        """计算下次运行时间"""
        from datetime import datetime, timedelta
        from croniter import croniter

        now = timezone.now()

        if self.trigger_type == 'CRON' and self.cron_expression:
            try:
                iter = croniter(self.cron_expression, now)
                return iter.get_next(datetime)
            except Exception:
                return None

        elif self.trigger_type == 'INTERVAL' and self.interval_seconds:
            return now + timedelta(seconds=self.interval_seconds)

        elif self.trigger_type == 'ONCE' and self.execute_at:
            return self.execute_at if self.execute_at > now else None

        return None

    def should_run_now(self):
        """检查是否应该现在运行"""
        if self.status != 'ACTIVE':
            return False

        if not self.next_run_time:
            return False

        return timezone.now() >= self.next_run_time

    def update_run_stats(self, success=True):
        """更新运行统计"""
        self.total_runs += 1
        if success:
            self.successful_runs += 1
        else:
            self.failed_runs += 1
        self.last_run_time = timezone.now()
        self.next_run_time = self.calculate_next_run()
        self.save()


class TaskExecutionLog(models.Model):
    """任务执行日志模型"""
    STATUS_CHOICES = [
        ('PENDING', '待执行'),
        ('RUNNING', '执行中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
        ('CANCELLED', '已取消'),
    ]

    task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE, related_name='execution_logs',
                             verbose_name='关联任务')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='执行状态')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration = models.FloatField(null=True, blank=True, verbose_name='执行时长(秒)')
    result = models.JSONField(default=dict, verbose_name='执行结果')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    executed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='执行者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'api_task_execution_logs'
        verbose_name = '任务执行日志'
        verbose_name_plural = '任务执行日志'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.name} - {self.created_at}"

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        super().save(*args, **kwargs)


# ================ 通知管理相关模型 ================


class NotificationLog(models.Model):
    """通知日志模型"""
    NOTIFICATION_TYPES = [
        ('task_execution', '定时任务执行'),
        ('test_suite_execution', '测试套件执行'),
        ('api_request_execution', 'API请求执行'),
        ('system_alert', '系统警告'),
        ('manual', '手动通知'),
    ]

    STATUS_CHOICES = [
        ('pending', '待发送'),
        ('sending', '发送中'),
        ('success', '发送成功'),
        ('failed', '发送失败'),
        ('cancelled', '已取消'),
    ]

    task = models.ForeignKey(ScheduledTask, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联任务')
    task_name = models.CharField(max_length=200, verbose_name='任务名称', help_text='相关任务的名称')
    task_type = models.CharField(max_length=20, blank=True, null=True, verbose_name='任务类型快照', help_text='发送通知时的任务类型')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, verbose_name='通知类型')
    sender_name = models.CharField(max_length=100, verbose_name='发件人姓名')
    sender_email = models.EmailField(verbose_name='发件人邮箱')
    recipient_info = models.JSONField(verbose_name='收件人信息', help_text='接收通知的用户信息')
    webhook_bot_info = models.JSONField(default=dict, blank=True, null=True, verbose_name='Webhook机器人信息')
    notification_content = models.TextField(verbose_name='通知内容', help_text='发送的通知内容')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='发送状态')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息', help_text='发送失败时的错误信息')
    response_info = models.JSONField(default=dict, blank=True, null=True, verbose_name='响应信息',
                                     help_text='接收方返回的响应信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='发送时间')
    retry_count = models.IntegerField(default=0, verbose_name='重试次数', help_text='已重试的次数')
    is_retried = models.BooleanField(default=False, verbose_name='是否已重试')

    class Meta:
        db_table = 'api_notification_logs'
        verbose_name = '通知日志'
        verbose_name_plural = '通知日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        task_name = self.task.name if self.task else self.task_name
        return f"{task_name} - {self.get_notification_type_display()} - {self.status}"

    def get_recipient_names(self):
        """获取收件人姓名列表"""
        if self.recipient_info:
            if isinstance(self.recipient_info, list):
                recipient_list = []
                for rec in self.recipient_info:
                    email = rec.get('email', '')
                    name = rec.get('name', '')
                    if name and email:
                        recipient_list.append(f"{name}（{email}）")
                    elif email:
                        recipient_list.append(email)
                    else:
                        recipient_list.append('未知用户')
                return ', '.join(recipient_list)
            elif isinstance(self.recipient_info, dict):
                email = self.recipient_info.get('email', '')
                name = self.recipient_info.get('name', '')
                if name and email:
                    return f"{name}（{email}）"
                elif email:
                    return email
                else:
                    return '未知用户'
        return "未知收件人"

    def get_retry_status(self):
        """获取重试状态"""
        if self.is_retried:
            return f"已重试 {self.retry_count} 次"
        return "未重试"


class TaskNotificationSetting(models.Model):
    """定时任务通知设置模型"""
    NOTIFICATION_TYPES = [
        ('email', '邮箱通知'),
        ('webhook', 'Webhook机器人'),
        ('both', '两种都发送'),
    ]

    task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE, related_name='notification_settings',
                             verbose_name='关联任务')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='both',
                                         verbose_name='通知类型')
    notification_config = models.ForeignKey('core.UnifiedNotificationConfig', on_delete=models.SET_NULL,
                                            null=True, blank=True, related_name='task_notification_settings',
                                            verbose_name='通知配置')
    is_enabled = models.BooleanField(default=False, verbose_name='是否启用通知')
    notify_on_success = models.BooleanField(default=True, verbose_name='成功时通知')
    notify_on_failure = models.BooleanField(default=True, verbose_name='失败时通知')
    notify_on_timeout = models.BooleanField(default=False, verbose_name='超时时通知')
    notify_on_error = models.BooleanField(default=True, verbose_name='错误时通知')
    custom_webhook_bots = models.JSONField(default=dict, blank=True, null=True, verbose_name='自定义Webhook机器人',
                                           help_text='临时覆盖通知配置中的Webhook机器人设置')
    custom_recipients = models.ManyToManyField(User, blank=True,
                                               related_name='task_notification_settings_as_custom_recipient',
                                               verbose_name='自定义收件人', help_text='临时覆盖通知配置中的收件人设置')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_task_notification_settings'
        verbose_name = '任务通知设置'
        verbose_name_plural = '任务通知设置'
        unique_together = ['task']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.name} - {self.get_notification_type_display()}"

    def get_active_notification_types(self):
        """获取当前激活的通知类型"""
        active_types = []
        if self.notification_type in ['email', 'both']:
            active_types.append('email')
        if self.notification_type in ['webhook', 'both']:
            active_types.append('webhook')
        return active_types

    def get_notification_config(self):
        """获取通知配置，优先使用任务自定义配置"""
        if self.notification_config:
            return self.notification_config
        # 如果没有指定配置，返回系统默认配置
        # 使用字符串引用避免循环导入
        from apps.core.models import UnifiedNotificationConfig
        return UnifiedNotificationConfig.objects.filter(is_default=True, is_active=True).first()

    def should_notify(self, execution_status):
        """判断是否应该发送通知"""
        if not self.is_enabled:
            return False

        if execution_status == 'success' and self.notify_on_success:
            return True
        elif execution_status == 'failed' and self.notify_on_failure:
            return True
        elif execution_status == 'timeout' and self.notify_on_timeout:
            return True
        elif execution_status == 'error' and self.notify_on_error:
            return True

        return False


class OperationLog(models.Model):
    """操作日志模型"""
    OPERATION_TYPE_CHOICES = [
        ('create', '新增'),
        ('edit', '编辑'),
        ('delete', '删除'),
        ('execute', '执行'),
        ('run', '运行'),
        ('save', '保存'),
    ]

    RESOURCE_TYPE_CHOICES = [
        ('project', '项目'),
        ('collection', '集合'),
        ('request', '请求'),
        ('suite', '测试套件'),
        ('environment', '环境'),
        ('task', '定时任务'),
        ('execution', '执行记录'),
    ]

    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPE_CHOICES, verbose_name='操作类型')
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES, verbose_name='资源类型')
    resource_id = models.IntegerField(verbose_name='资源ID')
    resource_name = models.CharField(max_length=200, verbose_name='资源名称')
    description = models.TextField(verbose_name='操作描述')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='操作用户')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'api_operation_logs'
        verbose_name = 'API操作日志'
        verbose_name_plural = 'API操作日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.resource_name}"


class AIServiceConfig(models.Model):
    """AI服务配置模型"""
    SERVICE_TYPE_CHOICES = [
        ('openai', 'OpenAI'),
        ('azure', 'Azure OpenAI'),
        ('anthropic', 'Anthropic'),
        ('deepseek', 'DeepSeek'),
        ('qwen', '通义千问'),
        ('siliconflow', '硅基流动'),
        ('other', '其他'),
    ]

    ROLE_CHOICES = [
        ('doc_extractor', 'API文档提取'),
        ('naming', '参数命名规范化'),
        ('mock_data', '模拟数据生成'),
        ('description', '参数描述补全'),
    ]

    name = models.CharField(max_length=200, verbose_name='配置名称')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, verbose_name='服务类型')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='角色类型')
    api_key = models.CharField(max_length=500, verbose_name='API Key')
    base_url = models.CharField(max_length=500, verbose_name='API Base URL')
    model_name = models.CharField(max_length=200, verbose_name='模型名称')
    max_tokens = models.IntegerField(default=4096, verbose_name='最大Token数')
    temperature = models.FloatField(default=0.7, verbose_name='温度参数')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_ai_service_configs'
        verbose_name = 'AI服务配置'
        verbose_name_plural = 'AI服务配置'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['service_type', 'role']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name



class TestSuiteReviewRecord(SoftDeleteModel):
    """测试套件评审记录模型"""
    REVIEW_STATUS_CHOICES = [
        ('pending', '待评审'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    ]

    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='review_records',
                                   verbose_name='测试套件')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='suite_review_records',
                                 verbose_name='评审人')
    status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES, default='pending',
                              verbose_name='评审状态')
    comment = models.TextField(blank=True, verbose_name='评审意见')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='评审时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'api_test_suite_review_records'
        verbose_name = '测试套件评审记录'
        verbose_name_plural = '测试套件评审记录'
        ordering = ['-created_at']
        unique_together = ['test_suite', 'reviewer']

    def __str__(self):
        return f"{self.test_suite.name} - {self.reviewer.username} - {self.get_status_display()}"


class AutomationScenario(SoftDeleteModel):
    """自动化场景模型"""
    name = models.CharField(max_length=200, verbose_name='场景名称')
    description = models.TextField(blank=True, verbose_name='场景描述')
    project = models.ForeignKey(ApiProject, on_delete=models.CASCADE, related_name='scenarios',
                                verbose_name='所属项目')
    collection = models.ForeignKey(ApiCollection, on_delete=models.CASCADE, related_name='scenarios',
                                   verbose_name='所属集合', null=True, blank=True)
    legacy_test_suite = models.OneToOneField(TestSuite, on_delete=models.SET_NULL, null=True, blank=True,
                                             related_name='scenario', verbose_name='关联旧版测试套件')
    environment = models.ForeignKey(Environment, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='执行环境')
    global_variables = models.JSONField(default=dict, verbose_name='场景全局变量')
    pre_script = models.TextField(blank=True, verbose_name='场景前置脚本')
    post_script = models.TextField(blank=True, verbose_name='场景后置脚本')
    flow_control = models.JSONField(default=dict, verbose_name='流程控制配置')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_scenarios',
                                   verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_automation_scenarios'
        verbose_name = '自动化场景'
        verbose_name_plural = '自动化场景'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ScenarioStep(SoftDeleteModel):
    """场景步骤模型"""
    STEP_TYPE_CHOICES = [
        ('request', '接口请求'),
        ('group', '分组'),
        ('condition', '条件分支'),
        ('loop', '循环'),
        ('wait', '等待'),
        ('script', '自定义脚本'),
        ('scenario_ref', '引用场景'),
    ]

    scenario = models.ForeignKey(AutomationScenario, on_delete=models.CASCADE, related_name='steps',
                                 verbose_name='所属场景')
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES, default='request',
                                 verbose_name='步骤类型')
    step_number = models.IntegerField(verbose_name='步骤编号')
    step_alias = models.CharField(max_length=100, blank=True, verbose_name='步骤别名')
    name = models.CharField(max_length=200, verbose_name='步骤名称')
    api_request = models.ForeignKey(ApiRequest, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='关联接口')
    referenced_scenario = models.ForeignKey(AutomationScenario, on_delete=models.CASCADE, null=True, blank=True,
                                            related_name='referenced_by_steps', verbose_name='引用的场景')
    scenario_ref_config = models.JSONField(default=dict, blank=True,
                                           help_text='{"inherit_variables": true, "pass_variables": ["var1", "var2"], "execution_mode": "sync"}',
                                           verbose_name='场景引用配置')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                               related_name='children', verbose_name='父步骤')
    override_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    override_name = models.CharField(max_length=200, blank=True, verbose_name='覆盖名称')
    override_method = models.CharField(max_length=10, blank=True, verbose_name='覆盖方法')
    override_url = models.TextField(blank=True, verbose_name='覆盖URL')
    override_headers = models.JSONField(default=dict, blank=True, verbose_name='覆盖请求头')
    override_body = models.JSONField(default=dict, blank=True, verbose_name='覆盖请求体')
    override_params = models.JSONField(default=dict, blank=True, verbose_name='覆盖参数')
    override_assertions = models.JSONField(default=list, blank=True, verbose_name='覆盖断言规则')
    override_extractors = models.JSONField(default=list, blank=True, verbose_name='覆盖变量提取规则')
    pre_script = models.TextField(blank=True, verbose_name='步骤前置脚本')
    post_script = models.TextField(blank=True, verbose_name='步骤后置脚本')
    control_config = models.JSONField(default=dict, blank=True,
                                      help_text='条件、循环等配置，如 {"condition": "...", "loop_type": "for_each"}',
                                      verbose_name='控制配置')
    order = models.IntegerField(default=0, verbose_name='排序')
    legacy_suite_request = models.OneToOneField(TestSuiteRequest, on_delete=models.SET_NULL, null=True, blank=True,
                                                related_name='scenario_step', verbose_name='关联旧版套件请求')

    class Meta:
        db_table = 'api_scenario_steps'
        verbose_name = '场景步骤'
        verbose_name_plural = '场景步骤'
        ordering = ['order', 'step_number']
        unique_together = ['scenario', 'step_number']

    def __str__(self):
        return f"{self.scenario.name} - {self.name}"

    def get_effective_request_data(self) -> Dict[str, Any]:
        """获取有效的请求数据（合并原始请求和覆盖配置）"""
        if not self.api_request:
            return {}

        # 从原始请求获取基础数据
        request_data = {
            'method': self.api_request.method,
            'url': self.api_request.url,
            'headers': dict(self.api_request.headers or {}),
            'params': dict(self.api_request.params or {}),
            'body': self.api_request.body,
        }

        # 应用覆盖配置
        if self.override_method:
            request_data['method'] = self.override_method
        if self.override_url:
            request_data['url'] = self.override_url
        if self.override_headers:
            request_data['headers'].update(self.override_headers)
        if self.override_params:
            request_data['params'].update(self.override_params)
        if self.override_body:
            request_data['body'] = self.override_body

        return request_data

    def get_effective_extractors(self) -> List[Dict]:
        """获取有效的变量提取规则（合并原始请求和覆盖配置）"""
        extractors = []

        # 从原始请求获取提取规则
        if self.api_request and self.api_request.variable_extractors:
            extractors = list(self.api_request.variable_extractors)

        # 应用覆盖配置
        if self.override_extractors:
            # 使用覆盖的提取规则
            extractors = list(self.override_extractors)

        return extractors

    def get_effective_assertions(self) -> List[Dict]:
        """获取有效的断言规则（合并原始请求和覆盖配置）"""
        assertions = []

        # 从原始请求获取断言规则
        if self.api_request and self.api_request.assertions:
            assertions = list(self.api_request.assertions)

        # 应用覆盖配置
        if self.override_assertions:
            # 使用覆盖的断言规则
            assertions = list(self.override_assertions)

        return assertions


class ScenarioExecution(models.Model):
    """场景执行记录模型"""
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '执行失败'),
        ('cancelled', '已取消'),
    ]

    scenario = models.ForeignKey(AutomationScenario, on_delete=models.CASCADE, related_name='executions',
                                 verbose_name='所属场景')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='执行状态')
    execution_context = models.JSONField(default=dict, help_text='存储所有步骤的完整请求响应数据，用于跨步骤引用',
                                         verbose_name='执行上下文')
    step_results = models.JSONField(default=list, verbose_name='步骤结果')
    total_steps = models.IntegerField(default=0, verbose_name='总步骤数')
    passed_steps = models.IntegerField(default=0, verbose_name='通过步骤数')
    failed_steps = models.IntegerField(default=0, verbose_name='失败步骤数')
    parent_execution = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                         related_name='child_executions', verbose_name='父执行记录')
    parent_step_number = models.IntegerField(null=True, blank=True, verbose_name='父场景步骤编号')
    inherited_variables = models.JSONField(default=dict, blank=True, verbose_name='继承的变量')
    exported_variables = models.JSONField(default=dict, blank=True, verbose_name='导出的变量')
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='执行者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')

    class Meta:
        db_table = 'api_scenario_executions'
        verbose_name = '场景执行记录'
        verbose_name_plural = '场景执行记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.scenario.name} - {self.status}"
