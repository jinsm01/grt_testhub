import re

with open('apps/api_testing/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_str = '''class TestSuite(SoftDeleteModel):
    """测试套件模型（自动化场景）"""
    project = models.ForeignKey(ApiProject, on_delete=models.CASCADE, related_name='test_suites',
                                verbose_name='所属项目')
    name = models.CharField(max_length=200, verbose_name='套件名称')
    description = models.TextField(blank=True, verbose_name='套件描述')
    requests = models.ManyToManyField(ApiRequest, through='TestSuiteRequest', verbose_name='关联请求')
    environment = models.ForeignKey(Environment, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='执行环境')
    pre_process_script = models.TextField(blank=True, verbose_name='前置处理脚本')
    post_process_script = models.TextField(blank=True, verbose_name='后置处理脚本')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_test_suites',
                                   verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_test_suites'
        verbose_name = '测试套件'
        verbose_name_plural = '测试套件'
        ordering = ['-created_at']

    def __str__(self):
        return self.name'''

new_str = '''class TestSuite(SoftDeleteModel):
    """测试套件模型（自动化场景）"""
    project = models.ForeignKey(ApiProject, on_delete=models.CASCADE, related_name='test_suites',
                                verbose_name='所属项目')
    name = models.CharField(max_length=200, verbose_name='套件名称')
    description = models.TextField(blank=True, verbose_name='套件描述')
    requests = models.ManyToManyField(ApiRequest, through='TestSuiteRequest', verbose_name='关联请求')
    environment = models.ForeignKey(Environment, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name='执行环境')
    pre_process_script = models.TextField(blank=True, verbose_name='前置处理脚本')
    post_process_script = models.TextField(blank=True, verbose_name='后置处理脚本')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_test_suites',
                                   verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    mainline_test_case = models.ForeignKey(
        'testcases.TestCase', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='api_test_suites', verbose_name='关联主线用例'
    )
    mainline_case_checked_at = models.DateTimeField(
        null=True, blank=True, verbose_name='主线用例已确认时间',
        help_text='上次确认主线用例内容的时间，用于提示用例是否有更新'
    )

    class Meta:
        db_table = 'api_test_suites'
        verbose_name = '测试套件'
        verbose_name_plural = '测试套件'
        ordering = ['-created_at']

    def __str__(self):
        return self.name'''

if old_str in content:
    content = content.replace(old_str, new_str)
    with open('apps/api_testing/models.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('TestSuite updated successfully')
else:
    print('Old string not found')
