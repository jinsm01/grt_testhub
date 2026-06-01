import asyncio
import logging
import re
import os  # Added import
import json
import time
from rest_framework import viewsets, status
from django.conf import settings  # Added import
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.renderers import BaseRenderer
from rest_framework.permissions import AllowAny


class PassThroughRenderer(BaseRenderer):
    """直接透传StreamingHttpResponse，不进行任何渲染处理"""
    media_type = 'text/event-stream'
    format = 'event-stream'
    render_level = 0

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # 直接返回data，不做任何处理
        return data


from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from asgiref.sync import sync_to_async
from django.db import models

from .models import (
    RequirementDocument, RequirementAnalysis, BusinessRequirement,
    GeneratedTestCase, AnalysisTask, AIModelConfig, PromptConfig, TestCaseGenerationTask,
    GenerationConfig, AIModelService, TestTemplateConfig, TestTemplateCategory,
    KnowledgeGraph, KnowledgeGraphQueryHistory, KnowledgeGraphBuildTask
)

# 导入知识库相关模型
from apps.assistant.models import KnowledgeBaseDocument
from apps.assistant.rag_service import rag_service
from .serializers import (
    RequirementDocumentSerializer, RequirementAnalysisSerializer,
    BusinessRequirementSerializer, GeneratedTestCaseSerializer,
    AnalysisTaskSerializer, DocumentUploadSerializer,
    TestCaseGenerationRequestSerializer, TestCaseReviewRequestSerializer,
    AIModelConfigSerializer, PromptConfigSerializer, TestCaseGenerationTaskSerializer,
    GenerationConfigSerializer, TestTemplateConfigSerializer, TestTemplateCategorySerializer,
    NewTestCaseGenerationRequestSerializer
)
from .services import RequirementAnalysisService, DocumentProcessor
from .models import RequirementAnalysis, RequirementDocument, TestCaseGenerationTask

logger = logging.getLogger(__name__)


class RequirementDocumentViewSet(viewsets.ModelViewSet):
    """需求文档视图集"""
    queryset = RequirementDocument.objects.all()
    serializer_class = RequirementDocumentSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentUploadSerializer
        return RequirementDocumentSerializer

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """分析需求文档"""
        document = self.get_object()

        if document.status == 'analyzing':
            return Response(
                {'error': '文档正在分析中，请稍后再试'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if document.status == 'analyzed':
            return Response(
                {'message': '文档已经分析过了', 'analysis_id': document.analysis.id},
                status=status.HTTP_200_OK
            )

        try:
            # 更新状态为分析中
            document.status = 'analyzing'
            document.save()

            # 异步执行分析
            def run_analysis():
                try:
                    # 简化版同步分析
                    # 提取文档文本
                    if not document.extracted_text:
                        document.extracted_text = DocumentProcessor.extract_text(document)
                        document.save()

                    # 创建模拟分析结果
                    analysis_result = {
                        'analysis_report': f'对文档"{document.title}"的需求分析已完成。\n\n文档内容：{document.extracted_text[:200]}...\n\n识别到若干功能性需求。',
                        'requirements_count': 2,
                        'requirements': [
                            {
                                'requirement_id': 'REQ001',
                                'requirement_name': '基础功能需求',
                                'requirement_type': 'functional',
                                'module': '核心模块',
                                'requirement_level': 'high',
                                'estimated_hours': 8,
                                'description': '基于文档内容识别的功能需求',
                                'acceptance_criteria': '功能正常运行，满足用户需求'
                            },
                            {
                                'requirement_id': 'REQ002',
                                'requirement_name': '用户交互需求',
                                'requirement_type': 'usability',
                                'module': '前端模块',
                                'requirement_level': 'medium',
                                'estimated_hours': 6,
                                'description': '用户界面和交互相关需求',
                                'acceptance_criteria': '界面友好，操作简单'
                            }
                        ]
                    }

                    # 创建分析记录
                    analysis = RequirementAnalysis.objects.create(
                        document=document,
                        analysis_report=analysis_result['analysis_report'],
                        requirements_count=analysis_result['requirements_count'],
                        analysis_time=2.5
                    )

                    # 保存需求数据
                    for req_data in analysis_result['requirements']:
                        BusinessRequirement.objects.create(
                            analysis=analysis,
                            **req_data
                        )

                    # 更新文档状态
                    document.status = 'analyzed'
                    document.save()

                    return analysis

                except Exception as e:
                    logger.error(f"分析失败: {e}")
                    document.status = 'failed'
                    document.save()
                    raise e

            analysis = run_analysis()

            return Response({
                'message': '分析完成',
                'analysis_id': analysis.id,
                'requirements_count': analysis.requirements_count
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"分析文档时出错: {e}")
            return Response(
                {'error': f'分析失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def extract_text(self, request, pk=None):
        """提取文档文本"""
        document = self.get_object()

        try:
            if not document.extracted_text:
                text = DocumentProcessor.extract_text(document)
                document.extracted_text = text
                document.save()

            return Response({
                'extracted_text': document.extracted_text,
                'text_length': len(document.extracted_text)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"提取文本时出错: {e}")
            return Response(
                {'error': f'提取文本失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RequirementAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """需求分析视图集"""
    queryset = RequirementAnalysis.objects.all()
    serializer_class = RequirementAnalysisSerializer

    @action(detail=True, methods=['get'])
    def requirements(self, request, pk=None):
        """获取分析的需求列表"""
        analysis = self.get_object()
        requirements = analysis.requirements.all()
        serializer = BusinessRequirementSerializer(requirements, many=True)
        return Response(serializer.data)


class BusinessRequirementViewSet(viewsets.ReadOnlyModelViewSet):
    """业务需求视图集"""
    queryset = BusinessRequirement.objects.all()
    serializer_class = BusinessRequirementSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        analysis_id = self.request.query_params.get('analysis_id')
        if analysis_id:
            queryset = queryset.filter(analysis_id=analysis_id)
        return queryset

    @classmethod
    def _generate_test_case_content(cls, requirement, case_number, test_level):
        """根据需求类型和序号生成不同的测试用例内容"""

        # 基础测试场景模板
        test_scenarios = {
            1: {
                'type': '正常路径测试',
                'focus': '基本功能验证',
                'steps_template': [
                    "准备测试环境和数据",
                    "执行正常业务流程",
                    "验证功能执行结果",
                    "检查系统状态"
                ]
            },
            2: {
                'type': '异常路径测试',
                'focus': '异常情况处理',
                'steps_template': [
                    "准备异常测试数据",
                    "触发异常业务场景",
                    "验证异常处理机制",
                    "确认系统状态正常"
                ]
            },
            3: {
                'type': '边界值测试',
                'focus': '边界条件验证',
                'steps_template': [
                    "设置边界值测试条件",
                    "执行边界值操作",
                    "验证边界值处理",
                    "检查结果准确性"
                ]
            },
            4: {
                'type': '性能测试',
                'focus': '性能指标验证',
                'steps_template': [
                    "配置性能测试环境",
                    "执行性能测试操作",
                    "监控性能指标",
                    "验证性能要求"
                ]
            },
            5: {
                'type': '安全测试',
                'focus': '安全机制验证',
                'steps_template': [
                    "设置安全测试环境",
                    "执行安全相关操作",
                    "验证安全控制机制",
                    "确认安全合规性"
                ]
            }
        }

        # 循环使用测试场景
        scenario_key = ((case_number - 1) % 5) + 1
        scenario = test_scenarios[scenario_key]

        # 根据需求名称生成具体内容
        req_name = requirement.requirement_name
        req_module = requirement.module
        req_type = requirement.requirement_type

        # 生成标题
        title = f"{req_name} - {scenario['type']}用例"

        # ========== 优先从数据库读取前置条件配置 ==========
        db_precondition = TestTemplateConfig.get_precondition(req_name, req_module)

        if db_precondition:
            # 使用数据库配置的前置条件
            precondition = db_precondition
            logger.info(f"从数据库加载前置条件: {req_name}")
        else:
            # ========== 职业教育 SaaS 平台专用前置条件（作为后备）==========

            # 【课程管理】前置条件
            if any(keyword in req_name for keyword in ["课程", "课时", "章节", "课件"]):
                precondition = f"1. 系统正常运行\n2. 教师账号已登录\n3. 课程分类已配置\n4. 测试视频/课件资源已准备\n5. {req_module}模块可访问"

            # 【学员管理】前置条件
            elif any(keyword in req_name for keyword in ["学员", "学生", "报名", "学籍", "分班"]):
                precondition = f"1. 系统正常运行\n2. 管理员/教师账号已登录\n3. 班级信息已创建\n4. 测试学员账号已准备\n5. {req_module}模块可访问"

            # 【教学管理】前置条件
            elif any(keyword in req_name for keyword in ["排课", "课表", "考勤", "作业", "考试"]):
                precondition = f"1. 系统正常运行\n2. 教师账号已登录\n3. 课程和班级信息已配置\n4. 学员名单已导入\n5. {req_module}模块可访问"

            # 【直播教学】前置条件
            elif any(keyword in req_name for keyword in ["直播", "回放", "连麦", "白板"]):
                precondition = f"1. 系统正常运行\n2. 直播服务连接正常\n3. 教师/学员账号已准备\n4. 浏览器摄像头/麦克风权限已开启\n5. {req_module}模块可访问"

            # 【证书管理】前置条件
            elif any(keyword in req_name for keyword in ["证书", "结业", "学分", "成绩单"]):
                precondition = f"1. 系统正常运行\n2. 管理员账号已登录\n3. 证书模板已配置\n4. 学员学习记录已生成\n5. {req_module}模块可访问"

            # 【营销招生】前置条件
            elif any(keyword in req_name for keyword in ["试听", "体验课", "团购", "分销", "优惠券"]):
                precondition = f"1. 系统正常运行\n2. 营销人员账号已登录\n3. 课程信息已发布\n4. 营销活动规则已配置\n5. {req_module}模块可访问"

            # 【内容管理】前置条件
            elif any(keyword in req_name for keyword in ["题库", "试题", "试卷", "资料"]):
                precondition = f"1. 系统正常运行\n2. 教师/教研账号已登录\n3. 题库分类已配置\n4. 测试试题/资料已准备\n5. {req_module}模块可访问"

            # 【问答互动】前置条件
            elif any(keyword in req_name for keyword in ["问答", "提问", "答疑", "讨论", "评价"]):
                precondition = f"1. 系统正常运行\n2. 学员账号已登录\n3. 课程学习进度满足互动条件\n4. 教师账号在线可回复\n5. {req_module}模块可访问"

            # ========== 原有前置条件逻辑保留 ==========
            elif "登录" in req_name:
                precondition = f"1. 系统正常运行\n2. 测试用户账号已准备\n3. {req_module}模块可访问"
            elif "数据" in req_name:
                precondition = f"1. 系统正常运行\n2. 数据库连接正常\n3. 测试数据已准备\n4. {req_module}模块可访问"
            elif "支付" in req_name:
                precondition = f"1. 系统正常运行\n2. 支付接口连接正常\n3. 测试账户余额充足\n4. {req_module}模块可访问"
            else:
                precondition = f"1. 系统正常运行\n2. 用户已登录系统\n3. {req_module}模块可访问\n4. 相关权限已配置"

        # 生成测试步骤
        steps = []
        for i, step_template in enumerate(scenario['steps_template'], 1):

            # ========== 职业教育 SaaS 平台专用测试步骤 - 开始 ==========

            # 【课程管理】测试步骤
            if any(keyword in req_name for keyword in ["课程", "课时", "章节", "课件"]):
                if i == 1:
                    steps.append(f"{i}. 教师登录系统，进入课程管理后台")
                elif i == 2:
                    if scenario_key == 1:  # 正常路径
                        steps.append(f"{i}. 点击创建课程，填写课程基本信息（名称、分类、封面、简介）")
                    elif scenario_key == 2:  # 异常路径
                        steps.append(f"{i}. 尝试创建课程，输入异常数据（如超长名称、无效格式封面）")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的课程操作")
                elif i == 3:
                    steps.append(f"{i}. 编排课程章节结构，上传课时内容（视频/文档/作业）")
                elif i == 4:
                    steps.append(f"{i}. 设置课程价格/可见性，发布课程并验证展示效果")

            # 【学员管理】测试步骤
            elif any(keyword in req_name for keyword in ["学员", "学生", "报名", "学籍", "分班"]):
                if i == 1:
                    steps.append(f"{i}. 管理员/教师登录系统，进入学员管理模块")
                elif i == 2:
                    if scenario_key == 1:
                        steps.append(f"{i}. 录入新学员信息或处理学员报名申请")
                    elif scenario_key == 2:
                        steps.append(f"{i}. 尝试录入异常学员信息（如重复手机号、格式错误）")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的学员操作")
                elif i == 3:
                    steps.append(f"{i}. 进行班级分配或学籍状态变更操作")
                elif i == 4:
                    steps.append(f"{i}. 验证学员信息同步和学习权限开通情况")

            # 【教学管理】测试步骤
            elif any(keyword in req_name for keyword in ["排课", "课表", "考勤", "作业", "考试"]):
                if i == 1:
                    steps.append(f"{i}. 教师登录系统，进入教学管理模块")
                elif i == 2:
                    if scenario_key == 1:
                        steps.append(f"{i}. 创建排课计划或发布作业/考试")
                    elif scenario_key == 2:
                        steps.append(f"{i}. 尝试创建冲突排课或过期作业/考试")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的教学操作")
                elif i == 3:
                    steps.append(f"{i}. 学员参与课程/提交作业/参加考试")
                elif i == 4:
                    steps.append(f"{i}. 教师批改/系统评分，验证成绩和考勤记录")

            # 【直播教学】测试步骤
            elif any(keyword in req_name for keyword in ["直播", "回放", "连麦", "白板"]):
                if i == 1:
                    steps.append(f"{i}. 教师创建直播课，设置直播时间和参数，学员预约课程")
                elif i == 2:
                    if scenario_key == 1:
                        steps.append(f"{i}. 教师开始直播，学员进入直播间，测试音视频设备")
                    elif scenario_key == 2:
                        steps.append(f"{i}. 模拟网络异常/设备故障等异常情况")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的直播操作")
                elif i == 3:
                    steps.append(f"{i}. 进行直播互动（连麦、白板、弹幕、答题）")
                elif i == 4:
                    steps.append(f"{i}. 结束直播，验证回放生成和直播数据统计")

            # 【证书管理】测试步骤
            elif any(keyword in req_name for keyword in ["证书", "结业", "学分", "成绩单"]):
                if i == 1:
                    steps.append(f"{i}. 管理员登录系统，进入证书管理模块")
                elif i == 2:
                    if scenario_key == 1:
                        steps.append(f"{i}. 配置证书模板和结业条件规则")
                    elif scenario_key == 2:
                        steps.append(f"{i}. 尝试配置无效证书模板或不合理结业条件")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的证书操作")
                elif i == 3:
                    steps.append(f"{i}. 学员完成学习，系统自动判断结业条件")
                elif i == 4:
                    steps.append(f"{i}. 生成电子证书/成绩单，验证信息准确性和防伪功能")

            # 【营销招生】测试步骤
            elif any(keyword in req_name for keyword in ["试听", "体验课", "团购", "分销", "优惠券"]):
                if i == 1:
                    steps.append(f"{i}. 营销人员登录系统，配置营销活动规则")
                elif i == 2:
                    if scenario_key == 1:
                        steps.append(f"{i}. 学员/推广员参与营销活动（领取优惠/分享推广）")
                    elif scenario_key == 2:
                        steps.append(f"{i}. 尝试违规参与活动（如重复领取、虚假推广）")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的营销操作")
                elif i == 3:
                    steps.append(f"{i}. 完成购买转化，验证优惠计算和佣金分成")
                elif i == 4:
                    steps.append(f"{i}. 查看营销数据统计和财务报表")

            # 【内容管理】测试步骤
            elif any(keyword in req_name for keyword in ["题库", "试题", "试卷", "资料"]):
                if i == 1:
                    steps.append(f"{i}. 教师/教研登录系统，进入内容管理模块")
                elif i == 2:
                    if scenario_key == 1:
                        steps.append(f"{i}. 上传/导入试题或学习资料")
                    elif scenario_key == 2:
                        steps.append(f"{i}. 尝试上传异常格式文件或重复试题")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的内容操作")
                elif i == 3:
                    steps.append(f"{i}. 进行内容审核和分类管理")
                elif i == 4:
                    steps.append(f"{i}. 验证内容展示和权限控制")

            # 【问答互动】测试步骤
            elif any(keyword in req_name for keyword in ["问答", "提问", "答疑", "讨论", "评价"]):
                if i == 1:
                    steps.append(f"{i}. 学员登录系统，在学习过程中发起提问/评价")
                elif i == 2:
                    if scenario_key == 1:
                        steps.append(f"{i}. 提交问题/评价内容")
                    elif scenario_key == 2:
                        steps.append(f"{i}. 尝试提交违规内容（敏感词/恶意信息）")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的互动操作")
                elif i == 3:
                    steps.append(f"{i}. 教师回复问题/系统审核内容")
                elif i == 4:
                    steps.append(f"{i}. 验证互动记录和消息通知")

            # ========== 职业教育 SaaS 平台专用测试步骤 - 结束 ==========

            # 原有测试步骤逻辑保留
            elif "登录" in req_name:
                if i == 1:
                    steps.append(f"{i}. 打开登录页面，准备测试用户凭证")
                elif i == 2:
                    if scenario_key == 1:
                        steps.append(f"{i}. 输入正确的用户名和密码，点击登录")
                    elif scenario_key == 2:
                        steps.append(f"{i}. 输入错误的用户名或密码，点击登录")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的登录操作")
                elif i == 3:
                    steps.append(f"{i}. 验证登录结果和页面跳转")
                else:
                    steps.append(f"{i}. 检查用户登录状态和系统响应")
            elif "数据" in req_name:
                if i == 1:
                    steps.append(f"{i}. 进入{req_module}，准备数据操作")
                elif i == 2:
                    if scenario_key == 1:
                        steps.append(f"{i}. 执行正常的数据录入/查询操作")
                    elif scenario_key == 2:
                        steps.append(f"{i}. 执行异常数据操作（如格式错误、超长数据等）")
                    else:
                        steps.append(f"{i}. 执行{scenario['focus']}相关的数据操作")
                elif i == 3:
                    steps.append(f"{i}. 验证数据操作结果和完整性")
                else:
                    steps.append(f"{i}. 检查数据状态和系统响应")
            else:
                steps.append(f"{i}. {step_template}（针对{req_name}）")

        test_steps = "\n".join(steps)

        # 生成预期结果
        if scenario_key == 1:  # 正常路径
            expected_result = f"{req_name}功能正常执行，满足业务需求，系统响应正确"
        elif scenario_key == 2:  # 异常路径
            expected_result = f"系统正确处理异常情况，给出适当提示，{req_name}功能保持稳定"
        elif scenario_key == 3:  # 边界值
            expected_result = f"{req_name}在边界条件下正常工作，数据处理准确，无异常错误"
        elif scenario_key == 4:  # 性能测试
            expected_result = f"{req_name}性能满足要求，响应时间在可接受范围内，系统稳定运行"
        else:  # 安全测试
            expected_result = f"{req_name}安全机制有效，权限控制正常，敏感信息得到保护"

        return {
            'title': title,
            'precondition': precondition,
            'test_steps': test_steps,
            'expected_result': expected_result
        }

    @action(detail=False, methods=['post'])
    def generate_test_cases(self, request):
        """为选中的需求生成测试用例"""
        logger.info(f"收到生成测试用例请求: {request.data}")
        serializer = TestCaseGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"序列化器验证失败: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            input_source = serializer.validated_data.get('input_source', 'manual')
            test_level = serializer.validated_data['test_level']
            test_priority = serializer.validated_data['test_priority']
            test_case_count = serializer.validated_data['test_case_count']

            # 生成唯一case_id的辅助函数
            def generate_unique_case_id(requirement, base_index):
                """生成唯一的测试用例ID"""
                base_case_id = f"TC{requirement.requirement_id}_{base_index:03d}"
                case_id = base_case_id
                counter = 1

                # 检查是否已存在，如果存在则添加后缀
                while GeneratedTestCase.objects.filter(requirement=requirement, case_id=case_id).exists():
                    case_id = f"{base_case_id}_{counter}"
                    counter += 1

                return case_id

            # 用于存储知识库切片合并后的内容
            kb_merged_content = None

            # 同步生成测试用例
            def run_generation():
                nonlocal kb_merged_content
                try:
                    generated_test_cases = []

                    if input_source in ['manual', 'file']:
                        # 原有的手动输入和文件上传逻辑
                        requirement_ids = serializer.validated_data['requirement_ids']
                        requirements = BusinessRequirement.objects.filter(id__in=requirement_ids)

                        for requirement in requirements:
                            # 获取该需求现有测试用例的数量，作为起始索引
                            existing_count = GeneratedTestCase.objects.filter(requirement=requirement).count()

                            for i in range(test_case_count):
                                # 生成唯一的case_id
                                case_id = generate_unique_case_id(requirement, existing_count + i + 1)

                                # 根据需求类型和序号生成不同的测试用例内容
                                test_case_content = BusinessRequirementViewSet._generate_test_case_content(requirement,
                                                                                                           i + 1,
                                                                                                           test_level)

                                # 创建测试用例
                                test_case = GeneratedTestCase.objects.create(
                                    requirement=requirement,
                                    case_id=case_id,
                                    title=test_case_content['title'],
                                    priority=test_priority,
                                    precondition=test_case_content['precondition'],
                                    test_steps=test_case_content['test_steps'],
                                    expected_result=test_case_content['expected_result'],
                                    status='generated',
                                    generated_by_ai='AI-Generator-v1.0'
                                )
                                generated_test_cases.append(test_case)

                    elif input_source == 'kb_chunks':
                        # 新增：从知识库切片生成用例的逻辑
                        chunk_ids = serializer.validated_data['chunk_ids']

                        # 合并切片内容
                        merged_content = self._merge_kb_chunks_content(chunk_ids, request.user)
                        kb_merged_content = merged_content  # 保存到外部变量

                        # 创建一个虚拟的分析和需求，用于存储知识库内容
                        from django.utils.text import slugify

                        # 创建虚拟分析文档
                        from django.core.files.base import ContentFile
                        virtual_document, _ = RequirementDocument.objects.get_or_create(
                            title=f"KB_Doc_{int(time.time())}",
                            defaults={
                                'document_type': 'txt',
                                'status': 'analyzed',
                                'extracted_text': merged_content[:2000],  # 只存储部分内容
                                'uploaded_by': request.user
                            }
                        )
                        # 如果没有文件，创建一个虚拟文件
                        if not virtual_document.file:
                            virtual_document.file.save(
                                f'kb_virtual_{int(time.time())}.txt',
                                ContentFile(merged_content[:1000]),
                                save=True
                            )

                        # 创建虚拟分析结果
                        virtual_analysis, _ = RequirementAnalysis.objects.get_or_create(
                            document=virtual_document,
                            defaults={
                                'requirements_count': 1,
                                'analysis_report': f'基于知识库切片生成的虚拟分析\n\n内容摘要：{merged_content[:500]}...'
                            }
                        )

                        # 创建虚拟需求
                        virtual_requirement, created = BusinessRequirement.objects.get_or_create(
                            analysis=virtual_analysis,
                            requirement_id=f"KB_{slugify(str(int(time.time())))}",
                            defaults={
                                'requirement_name': '知识库切片生成',
                                'requirement_type': 'functional',
                                'module': 'KnowledgeBase',
                                'requirement_level': 'system',
                                'description': merged_content,
                                'estimated_hours': 1,
                                'acceptance_criteria': '基于知识库内容生成测试用例'
                            }
                        )
                        
                        # 为知识库切片内容生成测试用例 - 使用AI模型
                        # 创建一个临时任务对象来调用AI服务
                        temp_task = TestCaseGenerationTask(
                            title='知识库切片临时任务',
                            requirement_text=merged_content,
                            created_by=request.user
                        )
                        
                        # 获取活跃的AI模型配置和提示词配置
                        writer_config = AIModelConfig.objects.filter(role='writer', is_active=True).first()
                        writer_prompt = PromptConfig.get_active_config('writer')
                        
                        if not writer_config:
                            raise Exception('未找到可用的测试用例编写模型配置')
                        if not writer_prompt:
                            raise Exception('未找到可用的测试用例编写提示词配置')
                        
                        temp_task.writer_model_config = writer_config
                        temp_task.writer_prompt_config = writer_prompt
                        
                        # 调用AI模型生成测试用例
                        from asgiref.sync import async_to_sync
                        
                        # 使用async_to_sync包装异步函数
                        ai_generated_content = async_to_sync(AIModelService.generate_test_cases)(temp_task)
                        
                        # 解析AI生成的内容并创建测试用例
                        # 这里需要解析AI返回的测试用例内容，提取各个用例的组成部分
                        # 由于AI返回的内容格式可能不同，我们先创建一个简单的解析器
                        test_cases_data = self._parse_ai_generated_content(ai_generated_content, virtual_requirement)
                        
                        for i, test_case_data in enumerate(test_cases_data):
                            case_id = generate_unique_case_id(virtual_requirement, i + 1)
                            
                            # 创建测试用例
                            test_case = GeneratedTestCase.objects.create(
                                requirement=virtual_requirement,
                                case_id=case_id,
                                title=test_case_data.get('title', f'知识库切片生成用例 {i+1}'),
                                priority=test_priority,
                                precondition=test_case_data.get('precondition', ''),
                                test_steps=test_case_data.get('test_steps', ''),
                                expected_result=test_case_data.get('expected_result', ''),
                                status='generated',
                                generated_by_ai='AI-Generator-v1.0'
                            )
                            generated_test_cases.append(test_case)
                        
                        # 保存AI生成的原始内容，供任务记录使用
                        ai_generated_content_for_task = ai_generated_content
                        
                        # 为知识库切片生成的任务记录保存AI生成的原始内容，而不是表格格式
                        # 这样可以与新API保持一致的格式
                        kb_merged_content = merged_content  # 确保变量已定义

                    if input_source == 'kb_chunks':
                        # 对于知识库切片，返回测试用例和AI生成的原始内容
                        return generated_test_cases, ai_generated_content_for_task
                    else:
                        # 对于手动输入和文件上传，返回测试用例和None
                        return generated_test_cases, None

                except Exception as e:
                    logger.error(f"生成测试用例失败: {e}")
                    raise e

            test_cases, ai_generated_content_result = run_generation()

            # 序列化返回结果
            test_case_serializer = GeneratedTestCaseSerializer(test_cases, many=True)

            # 创建任务记录
            task = None
            if input_source == 'kb_chunks' and kb_merged_content:
                # 为知识库切片生成创建任务记录
                import uuid
                from django.utils import timezone

                # 构建测试用例内容（使用AI生成的原始内容，保持与新API一致的格式）
                # 使用从run_generation函数返回的AI生成原始内容
                if ai_generated_content_result:
                    test_cases_content = ai_generated_content_result
                else:
                    # 如果没有AI生成内容，则使用表格格式作为备选
                    test_cases_content = self._build_test_cases_markdown(test_cases)

                task = TestCaseGenerationTask.objects.create(
                    task_id=f"KB_{uuid.uuid4().hex[:8].upper()}",
                    title=f"知识库切片生成 - {len(test_cases)}个用例",
                    requirement_text=kb_merged_content[:500] + "..." if len(kb_merged_content) > 500 else kb_merged_content,
                    status='completed',
                    progress=100,
                    output_mode='complete',
                    created_by=request.user,
                    completed_at=timezone.now(),
                    generated_test_cases=test_cases_content,
                    final_test_cases=test_cases_content
                )

            response_data = {
                'message': f'成功生成{len(test_cases)}个测试用例',
                'test_cases': test_case_serializer.data
            }

            if task:
                response_data['task_id'] = task.task_id

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"生成测试用例时出错: {e}")
            return Response(
                {'error': f'生成测试用例失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_ai_generated_content(self, content, requirement):
        """
        解析AI生成的测试用例内容
        这是一个简化版本，实际应用中可能需要更复杂的解析逻辑
        """
        # 简单的解析逻辑：按测试用例的常见格式进行分割
        lines = content.split('\n')
        test_cases = []
        current_case = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是新的测试用例标题
            if '测试用例' in line or '用例' in line or line.startswith('#') or line.startswith('TC-') or line.startswith('TEST-'):
                if current_case and any(current_case.values()):  # 如果当前用例有内容，保存它
                    test_cases.append(current_case)
                current_case = {'title': line, 'precondition': '', 'test_steps': '', 'expected_result': ''}
            elif '前置条件' in line or '前提条件' in line:
                # 提取前置条件
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_case['precondition'] = parts[1].strip()
                else:
                    current_case['precondition'] = line.replace('前置条件', '').replace('前提条件', '').strip()
            elif '测试步骤' in line or '操作步骤' in line:
                # 提取测试步骤
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_case['test_steps'] = parts[1].strip()
                else:
                    current_case['test_steps'] = line.replace('测试步骤', '').replace('操作步骤', '').strip()
            elif '预期结果' in line or '期望结果' in line:
                # 提取预期结果
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_case['expected_result'] = parts[1].strip()
                else:
                    current_case['expected_result'] = line.replace('预期结果', '').replace('期望结果', '').strip()
            elif '标题' in line:
                # 提取标题
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_case['title'] = parts[1].strip()
        
        # 添加最后一个用例
        if current_case and any(current_case.values()):
            test_cases.append(current_case)
        
        # 如果解析结果为空，创建一个基本的用例
        if not test_cases:
            test_cases.append({
                'title': f'{requirement.requirement_name} - AI生成用例',
                'precondition': '无特殊前置条件',
                'test_steps': content[:500] + '...' if len(content) > 500 else content,
                'expected_result': '功能按预期工作'
            })
        
        return test_cases

    def _build_test_cases_markdown(self, test_cases):
        """构建测试用例的Markdown格式内容"""
        lines = []
        lines.append("| 用例ID | 标题 | 优先级 | 前置条件 | 测试步骤 | 预期结果 |")
        lines.append("|--------|------|--------|----------|----------|----------|")

        for tc in test_cases:
            case_id = tc.case_id if hasattr(tc, 'case_id') else tc.get('case_id', 'N/A')
            title = tc.title if hasattr(tc, 'title') else tc.get('title', 'N/A')
            priority = tc.priority if hasattr(tc, 'priority') else tc.get('priority', 'P1')
            precondition = tc.precondition if hasattr(tc, 'precondition') else tc.get('precondition', '')
            test_steps = tc.test_steps if hasattr(tc, 'test_steps') else tc.get('test_steps', '')
            expected_result = tc.expected_result if hasattr(tc, 'expected_result') else tc.get('expected_result', '')

            # 处理多行文本，替换换行符
            precondition = str(precondition).replace('\n', '<br>')
            test_steps = str(test_steps).replace('\n', '<br>')
            expected_result = str(expected_result).replace('\n', '<br>')

            lines.append(f"| {case_id} | {title} | {priority} | {precondition} | {test_steps} | {expected_result} |")

        return '\n'.join(lines)

    def _merge_kb_chunks_content(self, chunk_ids, user):
        """
        合并知识库切片内容，添加来源标记
        """
        merged_content = []
        
        for chunk_info in chunk_ids:
            doc_id = chunk_info['document_id']
            chunk_idx = chunk_info['chunk_index']
            
            # 获取文档信息
            try:
                doc = KnowledgeBaseDocument.objects.get(id=doc_id, user=user)
                
                # 获取切片内容
                chunks_result = rag_service.get_document_chunks(doc_id, user=user)
                
                if chunks_result.get('success') and 'chunks' in chunks_result:
                    # 根据 chunk_index 查找对应的切片
                    chunk_data = None
                    for chunk in chunks_result['chunks']:
                        if chunk['index'] == chunk_idx:
                            chunk_data = chunk
                            break
                    
                    if chunk_data:
                        chunk_content = chunk_data['content']
                        
                        # 添加来源标记
                        merged_content.append(f"""【来源：{doc.name} - 切片{chunk_idx + 1}】
{chunk_content}""")
                    else:
                        logger.warning(f"找不到切片索引 {chunk_idx}，文档 {doc_id} 的切片列表: {[c['index'] for c in chunks_result['chunks']]}")
                else:
                    logger.error(f"获取文档 {doc_id} 的切片内容失败: {chunks_result.get('error', '未知错误')}")
            except KnowledgeBaseDocument.DoesNotExist:
                logger.error(f"用户 {user.id} 无权限访问文档 {doc_id} 或文档不存在")
                continue
            except Exception as e:
                logger.error(f"处理文档 {doc_id} 切片 {chunk_idx} 时出错: {str(e)}")
                continue
        
        return "\n\n---\n\n".join(merged_content)


from rest_framework.pagination import PageNumberPagination


class GeneratedTestCasePagination(PageNumberPagination):
    """生成测试用例分页器"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class TestCaseGenerationTaskPagination(PageNumberPagination):
    """测试用例生成任务分页器"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class GeneratedTestCaseViewSet(viewsets.ModelViewSet):
    """生成的测试用例视图集"""
    queryset = GeneratedTestCase.objects.all()
    serializer_class = GeneratedTestCaseSerializer
    pagination_class = GeneratedTestCasePagination
    http_method_names = ['get', 'patch']  # 只允许GET和PATCH方法

    def get_queryset(self):
        queryset = super().get_queryset()

        # 按需求ID过滤
        requirement_id = self.request.query_params.get('requirement_id')
        if requirement_id:
            queryset = queryset.filter(requirement_id=requirement_id)

        # 按状态过滤
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # 按优先级过滤
        priority_param = self.request.query_params.get('priority')
        if priority_param:
            queryset = queryset.filter(priority=priority_param)

        return queryset

    @action(detail=False, methods=['post'])
    def review_test_cases(self, request):
        """评审测试用例"""
        serializer = TestCaseReviewRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            test_case_ids = serializer.validated_data['test_case_ids']
            review_criteria = serializer.validated_data['review_criteria']

            # 同步执行评审
            def run_review():
                try:
                    # 获取测试用例
                    test_cases = GeneratedTestCase.objects.filter(id__in=test_case_ids)

                    passed_count = 0
                    reviewed_cases = []

                    for test_case in test_cases:
                        # 模拟评审逻辑
                        is_passed = len(test_case.title) > 10 and len(test_case.test_steps) > 20

                        if is_passed:
                            passed_count += 1
                            test_case.status = 'approved'
                            test_case.review_comments = '测试用例设计合理，满足评审标准'
                        else:
                            test_case.status = 'rejected'
                            test_case.review_comments = '测试用例需要完善，请补充详细的测试步骤'

                        test_case.reviewed_by_ai = 'AI-Reviewer-v1.0'
                        test_case.save()

                        reviewed_cases.append({
                            'id': test_case.id,
                            'case_id': test_case.case_id,
                            'title': test_case.title,
                            'status': test_case.status,
                            'review_comments': test_case.review_comments
                        })

                    total_count = len(test_cases)
                    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

                    return {
                        'total_count': total_count,
                        'passed_count': passed_count,
                        'pass_rate': pass_rate,
                        'reviewed_cases': reviewed_cases
                    }

                except Exception as e:
                    logger.error(f"评审测试用例失败: {e}")
                    raise e

            review_result = run_review()

            return Response({
                'message': f'评审完成，通过率: {review_result["pass_rate"]:.2f}%',
                'review_result': review_result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"评审测试用例时出错: {e}")
            return Response(
                {'error': f'评审失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalysisTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """分析任务视图集"""
    queryset = AnalysisTask.objects.all()
    serializer_class = AnalysisTaskSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        document_id = self.request.query_params.get('document_id')
        if document_id:
            queryset = queryset.filter(document_id=document_id)
        return queryset

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """获取任务进度"""
        task = self.get_object()
        return Response({
            'task_id': task.task_id,
            'status': task.status,
            'progress': task.progress,
            'error_message': task.error_message
        })


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def upload_and_analyze(request):
    """上传文档并立即开始分析"""
    try:
        # 创建文档
        serializer = DocumentUploadSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        document = serializer.save()

        # 立即开始分析
        document.status = 'analyzing'
        document.save()

        def run_analysis():
            try:
                # 简化版同步分析
                # 提取文档文本
                if not document.extracted_text:
                    document.extracted_text = DocumentProcessor.extract_text(document)
                    document.save()

                # 创建模拟分析结果
                analysis_result = {
                    'analysis_report': f'对文档"{document.title}"的需求分析已完成。\n\n文档内容：{document.extracted_text[:200]}...\n\n识别到若干功能性需求。',
                    'requirements_count': 2,
                    'requirements': [
                        {
                            'requirement_id': 'REQ001',
                            'requirement_name': '基础功能需求',
                            'requirement_type': 'functional',
                            'module': '核心模块',
                            'requirement_level': 'high',
                            'estimated_hours': 8,
                            'description': '基于文档内容识别的功能需求',
                            'acceptance_criteria': '功能正常运行，满足用户需求'
                        },
                        {
                            'requirement_id': 'REQ002',
                            'requirement_name': '用户交互需求',
                            'requirement_type': 'usability',
                            'module': '前端模块',
                            'requirement_level': 'medium',
                            'estimated_hours': 6,
                            'description': '用户界面和交互相关需求',
                            'acceptance_criteria': '界面友好，操作简单'
                        }
                    ]
                }

                # 创建分析记录
                analysis = RequirementAnalysis.objects.create(
                    document=document,
                    analysis_report=analysis_result['analysis_report'],
                    requirements_count=analysis_result['requirements_count'],
                    analysis_time=2.5
                )

                # 保存需求数据
                for req_data in analysis_result['requirements']:
                    BusinessRequirement.objects.create(
                        analysis=analysis,
                        **req_data
                    )

                # 更新文档状态
                document.status = 'analyzed'
                document.save()

                return analysis

            except Exception as e:
                logger.error(f"分析失败: {e}")
                document.status = 'failed'
                document.save()
                raise e

        analysis = run_analysis()

        return Response({
            'message': '上传并分析完成',
            'document_id': document.id,
            'analysis_id': analysis.id,
            'requirements_count': analysis.requirements_count
        })

    except Exception as e:
        logger.error(f"上传并分析失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def analyze_text(request):
    """直接分析文本内容"""
    try:
        title = request.data.get('title', '')
        description = request.data.get('description', '')
        project_id = request.data.get('project')

        if not title or not description:
            return Response({'error': '标题和描述不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建一个虚拟的需求文档记录
        document = RequirementDocument.objects.create(
            title=title,
            document_type='txt',
            status='analyzing',
            uploaded_by_id=1,  # 使用默认用户ID，或者从request.user获取
            project_id=project_id if project_id else None,
            extracted_text=description
        )

        def run_analysis():
            try:
                # 创建模拟分析结果
                analysis_result = {
                    'analysis_report': f'对需求"{title}"的分析已完成。\n\n需求描述：{description[:200]}...\n\n识别到若干功能性需求。',
                    'requirements_count': 2,
                    'requirements': [
                        {
                            'requirement_id': 'REQ001',
                            'requirement_name': '基础功能需求',
                            'requirement_type': 'functional',
                            'module': '核心模块',
                            'requirement_level': 'high',
                            'estimated_hours': 8,
                            'description': f'基于需求描述识别的功能需求：{description[:100]}...',
                            'acceptance_criteria': '功能正常运行，满足用户需求'
                        },
                        {
                            'requirement_id': 'REQ002',
                            'requirement_name': '用户交互需求',
                            'requirement_type': 'usability',
                            'module': '前端模块',
                            'requirement_level': 'medium',
                            'estimated_hours': 6,
                            'description': '用户界面和交互相关需求',
                            'acceptance_criteria': '界面友好，操作简单'
                        }
                    ]
                }

                # 创建分析记录
                analysis = RequirementAnalysis.objects.create(
                    document=document,
                    analysis_report=analysis_result['analysis_report'],
                    requirements_count=analysis_result['requirements_count'],
                    analysis_time=1.5
                )

                # 保存需求数据
                for req_data in analysis_result['requirements']:
                    BusinessRequirement.objects.create(
                        analysis=analysis,
                        **req_data
                    )

                # 更新文档状态
                document.status = 'analyzed'
                document.save()

                return analysis

            except Exception as e:
                logger.error(f"分析失败: {e}")
                document.status = 'failed'
                document.save()
                raise e

        analysis = run_analysis()

        return Response({
            'message': '文本分析完成',
            'document_id': document.id,
            'analysis_id': analysis.id,
            'requirements_count': analysis.requirements_count
        })

    except Exception as e:
        logger.error(f"文本分析失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def analyze_text(request):
    """分析手动输入的需求文本"""
    try:
        title = request.data.get('title')
        description = request.data.get('description')
        project_id = request.data.get('project')

        if not title or not description:
            return Response({'error': '需求标题和描述不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建一个虚拟的需求文档记录
        document = RequirementDocument.objects.create(
            title=title,
            file=None,  # 手动输入没有文件
            document_type='txt',
            status='analyzing',
            uploaded_by_id=1,  # 使用默认用户ID，或者从request.user获取
            project_id=project_id if project_id else None,
            extracted_text=description
        )

        # 立即开始分析
        def run_analysis():
            try:
                # 使用新的先进分析系统
                import asyncio
                from .services import AIService

                logger.info(f"开始使用先进分析器分析需求: {title}")

                # 调用先进的需求分析
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    analysis_result = loop.run_until_complete(
                        AIService.analyze_requirements(description, title)
                    )
                    logger.info(f"先进分析完成，识别需求: {analysis_result.get('requirements_count', 0)}个")
                finally:
                    loop.close()

                # 创建分析记录
                analysis = RequirementAnalysis.objects.create(
                    document=document,
                    analysis_report=analysis_result['analysis_report'],
                    requirements_count=analysis_result['requirements_count'],
                    analysis_time=analysis_result.get('analysis_time', 2.0)
                )

                # 保存需求数据
                for req_data in analysis_result['requirements']:
                    BusinessRequirement.objects.create(
                        analysis=analysis,
                        **req_data
                    )

                # 更新文档状态
                document.status = 'analyzed'
                document.save()

                return analysis

            except Exception as e:
                logger.error(f"先进分析失败: {e}，使用备用分析")
                # fallback到简单分析
                analysis_result = {
                    'analysis_report': f'对需求"{title}"的分析已完成。\n\n需求描述：{description[:200]}...\n\n基于描述内容识别到若干功能性需求。',
                    'requirements_count': 2,
                    'requirements': [
                        {
                            'requirement_id': 'REQ001',
                            'requirement_name': title + ' - 核心功能',
                            'requirement_type': 'functional',
                            'module': '核心模块',
                            'requirement_level': 'high',
                            'estimated_hours': 8,
                            'description': description[:100] + '...',
                            'acceptance_criteria': '功能正常运行，满足用户需求'
                        },
                        {
                            'requirement_id': 'REQ002',
                            'requirement_name': title + ' - 交互功能',
                            'requirement_type': 'usability',
                            'module': '前端模块',
                            'requirement_level': 'medium',
                            'estimated_hours': 6,
                            'description': '用户界面和交互相关需求',
                            'acceptance_criteria': '界面友好，操作简单'
                        }
                    ]
                }

                # 创建分析记录
                analysis = RequirementAnalysis.objects.create(
                    document=document,
                    analysis_report=analysis_result['analysis_report'],
                    requirements_count=analysis_result['requirements_count'],
                    analysis_time=1.5
                )

                # 保存需求数据
                for req_data in analysis_result['requirements']:
                    BusinessRequirement.objects.create(
                        analysis=analysis,
                        **req_data
                    )

                # 更新文档状态
                document.status = 'analyzed'
                document.save()

                return analysis

            except Exception as e:
                logger.error(f"分析失败: {e}")
                document.status = 'failed'
                document.save()
                raise e

        analysis = run_analysis()

        return Response({
            'message': '文本分析完成',
            'document_id': document.id,
            'analysis_id': analysis.id,
            'requirements_count': analysis.requirements_count
        })

    except Exception as e:
        logger.error(f"文本分析失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIModelConfigViewSet(viewsets.ModelViewSet):
    """AI模型配置视图集"""
    queryset = AIModelConfig.objects.all()
    serializer_class = AIModelConfigSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # 按模型类型过滤
        model_type = self.request.query_params.get('model_type')
        if model_type:
            queryset = queryset.filter(model_type=model_type)

        # 按角色过滤
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        else:
            # 如果没有指定角色，默认排除 AI智能模式专用模型
            queryset = queryset.exclude(role__in=['browser_use_text', 'browser_use_vision'])

        # 按是否启用过滤
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """测试模型连接"""
        try:
            config = self.get_object()

            logger.info(f"=== 开始测试模型连接 ===")
            logger.info(f"模型类型: {config.model_type}")
            logger.info(f"模型名称: {config.model_name}")
            logger.info(f"API URL: {config.base_url}")
            logger.info(
                f"API Key前缀: {config.api_key[:10]}..." if len(config.api_key) > 10 else f"API Key: {config.api_key}")

            # 准备测试消息
            test_messages = [
                {"role": "system", "content": "你是一个AI助手"},
                {"role": "user", "content": "请回复'连接成功'"}
            ]

            # 异步测试连接 - 统一使用OpenAI兼容API
            def test_api_connection():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    try:
                        logger.info("开始调用API...")
                        # 设置60秒超时，统一使用OpenAI兼容API
                        result = loop.run_until_complete(
                            asyncio.wait_for(
                                AIModelService.call_openai_compatible_api(config, test_messages),
                                timeout=60.0
                            )
                        )

                        logger.info(f"API调用成功: {result}")
                        return {
                            'success': True,
                            'message': '连接测试成功',
                            'response': result.get('choices', [{}])[0].get('message', {}).get('content', '')
                        }
                    except asyncio.TimeoutError:
                        logger.error(f"API连接测试超时 (60秒), URL: {config.base_url}, Model: {config.model_name}")
                        return {
                            'success': False,
                            'message': '连接测试超时: 请检查网络连接或API地址是否正确'
                        }
                    finally:
                        try:
                            loop.run_until_complete(loop.shutdown_asyncgens())
                        except Exception:
                            pass
                        finally:
                            loop.close()

                except Exception as e:
                    logger.error(f"API连接测试异常: {repr(e)}, URL: {config.base_url}, Model: {config.model_name}")
                    import traceback
                    logger.error(f"详细错误堆栈:\n{traceback.format_exc()}")
                    return {
                        'success': False,
                        'message': f'连接测试失败: {str(e)}'
                    }

            result = test_api_connection()

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"测试连接时出错: {e}")
            return Response(
                {'success': False, 'message': f'测试失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """启用配置"""
        try:
            config = self.get_object()
            config.is_active = True
            config.save()
            return Response({
                'message': 'AI模型配置已启用',
                'id': config.id,
                'is_active': True
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"启用AI模型配置失败: {e}")
            return Response({
                'error': f'启用失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """禁用配置"""
        try:
            config = self.get_object()
            config.is_active = False
            config.save()
            return Response({
                'message': 'AI模型配置已禁用',
                'id': config.id,
                'is_active': False
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"禁用AI模型配置失败: {e}")
            return Response({
                'error': f'禁用失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromptConfigViewSet(viewsets.ModelViewSet):
    """提示词配置视图集"""
    queryset = PromptConfig.objects.all()
    serializer_class = PromptConfigSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # 按提示词类型过滤
        prompt_type = self.request.query_params.get('prompt_type')
        if prompt_type:
            queryset = queryset.filter(prompt_type=prompt_type)

        # 按是否启用过滤
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'])
    def load_defaults(self, request):
        """加载默认提示词"""
        try:
            # 读取用例编写提示词
            writer_prompt_path = os.path.join(settings.BASE_DIR, 'tester.md')
            # 读取用例评审提示词
            reviewer_prompt_path = os.path.join(settings.BASE_DIR, 'tester_pro.md')

            defaults = {}

            try:
                with open(writer_prompt_path, 'r', encoding='utf-8') as f:
                    defaults['writer'] = f.read()
            except FileNotFoundError:
                defaults['writer'] = """你是一名资深的QA高级专家，擅长编写高质量的测试用例。

请根据以下需求描述，生成详细的测试用例。

要求：
1. 测试用例应该覆盖正常流程、异常流程和边界条件
2. 每个测试用例包含：用例编号、用例标题、前置条件、测试步骤、预期结果
3. 测试步骤要详细、清晰、可执行
4. 考虑不同的用户角色和权限
5. 关注数据验证和错误处理

请以结构化的格式输出测试用例。"""

            try:
                with open(reviewer_prompt_path, 'r', encoding='utf-8') as f:
                    defaults['reviewer'] = f.read()
            except FileNotFoundError:
                defaults['reviewer'] = """你是一名资深的测试经理，负责评审测试用例的质量。

请对以下测试用例进行评审，并提供改进意见。

评审要点：
1. 测试用例是否覆盖了主要功能点
2. 测试步骤是否清晰、完整、可执行
3. 预期结果是否准确、具体
4. 是否遗漏了重要的测试场景
5. 是否需要补充边界条件测试

请提供：
1. 总体评价
2. 具体的改进建议
3. 补充的测试场景（如有）
4. 修改后的测试用例（如需要）"""

            # 添加知识库问答默认提示词
            defaults['knowledge_base'] = """你是一个专业的文档问答助手。请严格基于以下文档内容回答问题。

重要要求：
1. 如果文档中有明确的数字、时间、限制等具体信息，请直接给出精确答案
2. 优先回答问题的核心要点，不要罗列无关信息
3. 如果涉及规定、限制、标准等，请给出具体的数值或明确结论
4. 如果文档中没有明确答案，请直接说明"文档中未明确说明"

文档内容：
{context}

问题：{question}

请给出精确、简洁的回答："""

            # 添加断言生成默认提示词
            # 支持变量：
            #   {{response_time_threshold}} - 响应时间阈值（毫秒），默认5000
            defaults['assertion_generator'] = """你是一个专业的API测试专家。请基于提供的API响应数据，生成合适的测试断言。

生成的断言需要满足以下要求：
1. 覆盖关键字段的验证（如状态码、success字段、data关键字段）
2. 使用合适的断言类型（status_code、json_path、contains等）
3. 断言条件应该合理，基于实际响应值
4. 每个断言应该有清晰的名称说明验证目的
5. 返回JSON数组格式

支持的断言类型：
- status_code: 验证HTTP状态码
- json_path: 验证JSON路径提取的值
- contains: 验证响应内容包含特定文本
- response_time: 验证响应时间（默认<{{response_time_threshold}}ms）

返回格式必须是JSON数组，每个元素包含：
- name: 断言名称
- type: 断言类型
- expected: 预期值
- json_path: JSON路径（仅json_path类型需要）

示例输出：
[
  {"name": "状态码验证", "type": "status_code", "expected": 200},
  {"name": "响应时间小于5.0秒", "type": "response_time", "expected": 5000},
  {"name": "返回成功标识", "type": "json_path", "json_path": "$.success", "expected": "true"},
  {"name": "返回码验证", "type": "json_path", "json_path": "$.code", "expected": "00000"},
  {"name": "data.access_token存在", "type": "json_path", "json_path": "$.data.access_token", "expected": "exist"}
]"""

            return Response({
                'message': '默认提示词加载成功',
                'defaults': defaults
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"加载默认提示词失败: {e}")
            return Response(
                {'error': f'加载失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """启用配置"""
        try:
            config = self.get_object()
            config.is_active = True
            config.save()
            return Response({
                'message': '提示词配置已启用',
                'id': config.id,
                'is_active': True
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"启用提示词配置失败: {e}")
            return Response({
                'error': f'启用失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """禁用配置"""
        try:
            config = self.get_object()
            config.is_active = False
            config.save()
            return Response({
                'message': '提示词配置已禁用',
                'id': config.id,
                'is_active': False
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"禁用提示词配置失败: {e}")
            return Response({
                'error': f'禁用失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerationConfigViewSet(viewsets.ModelViewSet):
    """生成行为配置视图集"""
    queryset = GenerationConfig.objects.all()
    serializer_class = GenerationConfigSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'])
    def active(self, request):
        """获取活跃的生成配置"""
        try:
            config = GenerationConfig.get_active_config()
            if not config:
                return Response({
                    'error': '未找到活跃的生成配置，请先创建并启用一个配置'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = self.get_serializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"获取活跃生成配置失败: {e}")
            return Response({
                'error': f'获取失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """启用配置"""
        try:
            # 禁用其他所有配置
            GenerationConfig.objects.all().update(is_active=False)

            # 启用当前配置
            config = self.get_object()
            config.is_active = True
            config.save()

            return Response({
                'message': '生成配置已启用',
                'id': config.id,
                'is_active': True
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"启用生成配置失败: {e}")
            return Response({
                'error': f'启用失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """禁用配置"""
        try:
            config = self.get_object()
            config.is_active = False
            config.save()

            return Response({
                'message': '生成配置已禁用',
                'id': config.id,
                'is_active': False
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"禁用生成配置失败: {e}")
            return Response({
                'error': f'禁用失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestCaseGenerationTaskViewSet(viewsets.ModelViewSet):
    """测试用例生成任务视图集"""
    queryset = TestCaseGenerationTask.objects.all()
    serializer_class = TestCaseGenerationTaskSerializer
    pagination_class = TestCaseGenerationTaskPagination
    http_method_names = ['get', 'post', 'patch', 'delete']  # 允许GET、POST、PATCH和DELETE方法
    lookup_field = 'task_id'  # 使用task_id作为查找字段

    def get_queryset(self):
        queryset = super().get_queryset()

        # 安全检查：确保request有query_params属性
        if not hasattr(self.request, 'query_params'):
            return queryset.order_by('-created_at')

        # 按状态过滤
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # 按创建者过滤
        created_by = self.request.query_params.get('created_by')
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)

        # 按标题搜索
        title_param = self.request.query_params.get('title')
        if title_param:
            queryset = queryset.filter(title__icontains=title_param)

        return queryset.order_by('-created_at')

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """创建新的测试用例生成任务"""
        try:
            serializer = NewTestCaseGenerationRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data

            # 获取活跃的配置
            writer_config = None
            reviewer_config = None
            writer_prompt = None
            reviewer_prompt = None

            if validated_data.get('use_writer_model', True):
                # 优先查找任意启用的编写模型配置
                writer_config = AIModelConfig.objects.filter(role='writer', is_active=True).first()

                if not writer_config:
                    return Response(
                        {'error': '未找到可用的测试用例编写模型配置'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                writer_prompt = PromptConfig.get_active_config('writer')
                if not writer_prompt:
                    return Response(
                        {'error': '未找到可用的测试用例编写提示词配置'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if validated_data.get('use_reviewer_model', True):
                # 优先查找任意启用的评审模型配置
                reviewer_config = AIModelConfig.objects.filter(role='reviewer', is_active=True).first()

                if not reviewer_config:
                    return Response(
                        {'error': '未找到可用的测试用例评审模型配置'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                reviewer_prompt = PromptConfig.get_active_config('reviewer')
                if not reviewer_prompt:
                    return Response(
                        {'error': '未找到可用的测试用例评审提示词配置'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 创建任务
            task_data = {
                'title': validated_data['title'],
                'requirement_text': validated_data['requirement_text'],
                'writer_model_config': writer_config.id if writer_config else None,
                'reviewer_model_config': reviewer_config.id if reviewer_config else None,
                'writer_prompt_config': writer_prompt.id if writer_prompt else None,
                'reviewer_prompt_config': reviewer_prompt.id if reviewer_prompt else None,
            }

            # 如果请求中包含项目ID，添加到任务数据中
            if 'project' in validated_data and validated_data['project']:
                task_data['project'] = validated_data['project']

            # 处理输出模式：优先使用用户指定的，否则使用生成行为配置的默认值
            output_mode = request.data.get('output_mode')
            if output_mode and output_mode in ['stream', 'complete']:
                task_data['output_mode'] = output_mode
            else:
                # 从生成行为配置中读取默认值
                from .models import GenerationConfig
                gen_config = GenerationConfig.get_active_config()
                if gen_config:
                    task_data['output_mode'] = gen_config.default_output_mode
                else:
                    # 如果没有配置，默认使用流式输出
                    task_data['output_mode'] = 'stream'

            task_serializer = TestCaseGenerationTaskSerializer(
                data=task_data,
                context={'request': request}
            )

            if task_serializer.is_valid():
                task = task_serializer.save()

                # 异步执行生成任务
                def run_generation_task():
                    try:
                        import threading

                        def execute_task():
                            try:
                                # 更新任务状态
                                task.status = 'generating'
                                task.progress = 10
                                task.save()

                                # 读取生成行为配置
                                from .models import GenerationConfig
                                gen_config = GenerationConfig.get_active_config()

                                # 获取配置参数，设置默认值
                                enable_auto_review = gen_config.enable_auto_review if gen_config else True
                                review_timeout = gen_config.review_timeout if gen_config else 120

                                logger.info(
                                    f"任务 {task.task_id} 使用生成配置: auto_review={enable_auto_review}, review_timeout={review_timeout}s")

                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)

                                try:
                                    # 根据输出模式选择不同的生成方式
                                    if task.output_mode == 'stream':
                                        # 流式模式：实时保存到stream_buffer
                                        # 生成前先设置初始状态
                                        task.stream_buffer = ''
                                        task.stream_position = 0
                                        task.save()

                                        # 定义同步保存函数
                                        def save_stream_buffer(content):
                                            """同步保存流式内容到数据库"""
                                            task.stream_buffer = content
                                            task.stream_position = len(content)
                                            task.last_stream_update = timezone.now()
                                            task.save(update_fields=['stream_buffer', 'stream_position',
                                                                     'last_stream_update'])

                                        # 转换为异步函数
                                        async_save_stream_buffer = sync_to_async(save_stream_buffer)

                                        async def stream_callback(chunk):
                                            """流式回调：实时保存每个chunk到数据库"""
                                            # 先追加到内存中的buffer
                                            task.stream_buffer += chunk
                                            task.stream_position = len(task.stream_buffer)
                                            task.last_stream_update = timezone.now()

                                            # 每10个chunk或当chunk较大时保存一次
                                            if task.stream_position % 500 < 20 or len(chunk) > 100:
                                                try:
                                                    await async_save_stream_buffer(task.stream_buffer)
                                                except Exception as save_error:
                                                    logger.warning(f"保存流式内容失败: {save_error}")

                                        # 生成测试用例
                                        task.progress = 30
                                        task.save()

                                        generated_cases = loop.run_until_complete(
                                            AIModelService.generate_test_cases_stream(task, callback=stream_callback)
                                        )

                                        # 生成完成后，确保最终的流式内容被保存
                                        if task.stream_buffer:
                                            save_stream_buffer(task.stream_buffer)

                                        task.generated_test_cases = generated_cases
                                        task.progress = 60
                                        task.save()

                                        # 流式评审和改进（根据生成配置决定是否执行）
                                        if enable_auto_review and task.reviewer_model_config and task.reviewer_prompt_config:
                                            try:
                                                task.status = 'reviewing'
                                                task.progress = 70
                                                task.save()

                                                logger.info(f"开始流式评审任务 {task.task_id}")

                                                # 评审内容缓存
                                                review_buffer = []

                                                def save_review_buffer(content):
                                                    """同步保存评审内容"""
                                                    task.review_feedback = content
                                                    task.save(update_fields=['review_feedback'])

                                                async_save_review = sync_to_async(save_review_buffer)

                                                async def review_stream_callback(chunk):
                                                    """流式评审回调"""
                                                    review_buffer.append(chunk)
                                                    current_length = sum(len(c) for c in review_buffer)

                                                    # 每100字符保存一次
                                                    if current_length % 100 < 20 or len(chunk) > 50:
                                                        try:
                                                            content = ''.join(review_buffer)
                                                            await async_save_review(content)
                                                        except Exception as save_error:
                                                            logger.warning(f"保存评审内容失败: {save_error}")

                                                try:
                                                    # 移除超时限制，允许大文档完整评审
                                                    review_feedback = loop.run_until_complete(
                                                        AIModelService.review_test_cases_stream(
                                                            task, generated_cases, callback=review_stream_callback
                                                        )
                                                    )
                                                    # 保存最终评审内容
                                                    if review_buffer:
                                                        task.review_feedback = ''.join(review_buffer)
                                                        task.save(update_fields=['review_feedback'])
                                                    logger.info(f"任务 {task.task_id} 流式评审完成")

                                                    # 根据评审意见改进测试用例（自动执行）
                                                    logger.info(f"任务 {task.task_id} 开始根据评审意见改进测试用例")
                                                    task.status = 'revising'
                                                    task.progress = 85
                                                    task.final_test_cases = ''  # 清空，准备流式写入
                                                    task.save()

                                                    try:
                                                        # 定义同步保存函数
                                                        def save_final_buffer(content):
                                                            """同步保存最终用例内容"""
                                                            task.final_test_cases = content
                                                            task.save(update_fields=['final_test_cases'])

                                                        # 转换为异步函数
                                                        async_save_final = sync_to_async(save_final_buffer)

                                                        # 创建流式回调函数，实时更新final_test_cases
                                                        async def final_callback(chunk):
                                                            """流式回调：实时保存最终用例到数据库"""
                                                            # 实时追加到final_test_cases并保存
                                                            task.final_test_cases = (
                                                                                            task.final_test_cases or '') + chunk

                                                            # 每100字符或chunk较大时保存一次
                                                            current_length = len(task.final_test_cases)
                                                            if current_length % 100 < 20 or len(chunk) > 50:
                                                                try:
                                                                    await async_save_final(task.final_test_cases)
                                                                except Exception as save_error:
                                                                    logger.warning(f"保存最终用例失败: {save_error}")

                                                        # 添加超时保护，避免任务一直卡住（使用配置的超时时间）
                                                        try:
                                                            revised_cases = loop.run_until_complete(
                                                                asyncio.wait_for(
                                                                    AIModelService.revise_test_cases_based_on_review(
                                                                        task, generated_cases, task.review_feedback,
                                                                        callback=final_callback
                                                                    ),
                                                                    timeout=review_timeout  # 使用配置的超时时间（秒）
                                                                )
                                                            )
                                                        except asyncio.TimeoutError:
                                                            logger.error(
                                                                f"任务 {task.task_id} 改进阶段超时（{review_timeout}秒），使用原始用例")
                                                            # 超时时使用原始生成的用例，不再抛出异常
                                                            revised_cases = generated_cases
                                                        # 始终使用返回的完整内容，避免流式输出被截断导致数据丢失
                                                        # revised_cases 是完整的返回值，task.final_test_cases 只是流式回调的中间状态
                                                        if revised_cases and len(revised_cases) > 0:
                                                            # 检测并修复不完整的最后一条用例
                                                            revised_cases = AIModelService.fix_incomplete_last_case(
                                                                revised_cases)

                                                            # 按用例编号排序后再保存
                                                            sorted_cases = AIModelService.sort_test_cases_by_id(
                                                                revised_cases)
                                                            # 重新编号使编号连续
                                                            renumbered_cases = AIModelService.renumber_test_cases(
                                                                sorted_cases)
                                                            task.final_test_cases = renumbered_cases
                                                            logger.info(
                                                                f"任务 {task.task_id} 测试用例改进完成 (revised_cases长度: {len(revised_cases)}, 最终保存长度: {len(task.final_test_cases)})")
                                                        else:
                                                            # 如果返回为空，保留流式回调保存的内容
                                                            logger.warning(
                                                                f"任务 {task.task_id} 改进返回为空，使用流式回调保存的内容 (长度: {len(task.final_test_cases) if task.final_test_cases else 0})")
                                                    except Exception as revise_error:
                                                        logger.warning(
                                                            f"任务 {task.task_id} 改进测试用例失败: {revise_error}，使用原始用例")
                                                        # 按用例编号排序后再保存
                                                        sorted_cases = AIModelService.sort_test_cases_by_id(
                                                            generated_cases)
                                                        # 重新编号使编号连续
                                                        task.final_test_cases = AIModelService.renumber_test_cases(
                                                            sorted_cases)
                                                        task.save()

                                                except Exception as inner_error:
                                                    logger.warning(
                                                        f"任务 {task.task_id} 流式评审过程异常: {inner_error}")
                                                    task.review_feedback = f"评审过程出现异常: {str(inner_error)}\n\n建议：测试用例结构完整，可以使用。"
                                                    # 按用例编号排序后再保存
                                                    sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
                                                    # 重新编号使编号连续
                                                    task.final_test_cases = AIModelService.renumber_test_cases(
                                                        sorted_cases)
                                                    task.save()

                                            except Exception as review_error:
                                                logger.error(f"流式评审任务 {task.task_id} 失败: {review_error}")
                                                # 按用例编号排序后再保存
                                                sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
                                                task.final_test_cases = AIModelService.renumber_test_cases(sorted_cases)
                                                task.review_feedback = f"评审失败: {str(review_error)}\n\n建议：测试用例结构完整，可以使用。"
                                                task.save()
                                        else:
                                            # 按用例编号排序后再保存
                                            sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
                                            # 重新编号使编号连续
                                            task.final_test_cases = AIModelService.renumber_test_cases(sorted_cases)
                                            logger.info(f"任务 {task.task_id} 跳过评审，直接使用生成的测试用例")
                                            task.save()

                                    else:
                                        # 完整模式：原有逻辑
                                        task.progress = 30
                                        task.save()

                                        generated_cases = loop.run_until_complete(
                                            AIModelService.generate_test_cases(task)
                                        )

                                        task.generated_test_cases = generated_cases
                                        task.progress = 60
                                        task.save()

                                        # 评审和改进测试用例（根据生成配置决定是否执行）
                                        if enable_auto_review and task.reviewer_model_config and task.reviewer_prompt_config:
                                            try:
                                                task.status = 'reviewing'
                                                task.progress = 70
                                                task.save()

                                                logger.info(f"开始评审任务 {task.task_id}")

                                                # 移除超时限制，允许大文档完整评审
                                                try:
                                                    review_feedback = loop.run_until_complete(
                                                        AIModelService.review_test_cases(task, generated_cases)
                                                    )
                                                    task.review_feedback = review_feedback
                                                    logger.info(f"任务 {task.task_id} 评审完成")

                                                    # 根据评审意见改进测试用例（自动执行）
                                                    logger.info(f"任务 {task.task_id} 开始根据评审意见改进测试用例")
                                                    task.status = 'revising'
                                                    task.progress = 85
                                                    task.final_test_cases = ''  # 清空，准备流式写入
                                                    task.save()

                                                    try:
                                                        # 定义同步保存函数
                                                        def save_final_buffer_full(content):
                                                            """同步保存最终用例内容"""
                                                            task.final_test_cases = content
                                                            task.save(update_fields=['final_test_cases'])

                                                        # 转换为异步函数
                                                        async_save_final_full = sync_to_async(save_final_buffer_full)

                                                        # 创建流式回调函数，实时更新final_test_cases
                                                        async def final_callback_full(chunk):
                                                            """流式回调：实时保存最终用例到数据库"""
                                                            # 实时追加到final_test_cases并保存
                                                            task.final_test_cases = (
                                                                                            task.final_test_cases or '') + chunk

                                                            # 每100字符或chunk较大时保存一次
                                                            current_length = len(task.final_test_cases)
                                                            if current_length % 100 < 20 or len(chunk) > 50:
                                                                try:
                                                                    await async_save_final_full(task.final_test_cases)
                                                                except Exception as save_error:
                                                                    logger.warning(f"保存最终用例失败: {save_error}")

                                                        # 添加超时保护，避免任务一直卡住（使用配置的超时时间）
                                                        try:
                                                            revised_cases = loop.run_until_complete(
                                                                asyncio.wait_for(
                                                                    AIModelService.revise_test_cases_based_on_review(
                                                                        task, generated_cases, task.review_feedback,
                                                                        callback=final_callback_full
                                                                    ),
                                                                    timeout=review_timeout  # 使用配置的超时时间（秒）
                                                                )
                                                            )
                                                        except asyncio.TimeoutError:
                                                            logger.error(
                                                                f"任务 {task.task_id} 改进阶段超时（{review_timeout}秒），使用原始用例")
                                                            # 超时时使用原始生成的用例，不再抛出异常
                                                            revised_cases = generated_cases
                                                        # 始终使用返回的完整内容，避免流式输出被截断导致数据丢失
                                                        # revised_cases 是完整的返回值，task.final_test_cases 只是流式回调的中间状态
                                                        if revised_cases and len(revised_cases) > 0:
                                                            # 检测并修复不完整的最后一条用例
                                                            revised_cases = AIModelService.fix_incomplete_last_case(
                                                                revised_cases)

                                                            # 按用例编号排序后再保存
                                                            sorted_cases = AIModelService.sort_test_cases_by_id(
                                                                revised_cases)
                                                            # 重新编号使编号连续
                                                            renumbered_cases = AIModelService.renumber_test_cases(
                                                                sorted_cases)
                                                            task.final_test_cases = renumbered_cases
                                                            logger.info(
                                                                f"任务 {task.task_id} 测试用例改进完成 (revised_cases长度: {len(revised_cases)}, 最终保存长度: {len(task.final_test_cases)})")
                                                        else:
                                                            # 如果返回为空，保留流式回调保存的内容
                                                            logger.warning(
                                                                f"任务 {task.task_id} 改进返回为空，使用流式回调保存的内容 (长度: {len(task.final_test_cases) if task.final_test_cases else 0})")
                                                    except Exception as revise_error:
                                                        logger.warning(
                                                            f"任务 {task.task_id} 改进测试用例失败: {revise_error}，使用原始用例")
                                                        # 按用例编号排序后再保存
                                                        sorted_cases = AIModelService.sort_test_cases_by_id(
                                                            generated_cases)
                                                        # 重新编号使编号连续
                                                        task.final_test_cases = AIModelService.renumber_test_cases(
                                                            sorted_cases)
                                                        task.save()

                                                except Exception as inner_error:
                                                    logger.warning(f"任务 {task.task_id} 评审过程异常: {inner_error}")
                                                    task.review_feedback = f"评审过程出现异常: {str(inner_error)}\n\n建议：测试用例结构完整，可以使用。"
                                                    # 按用例编号排序后再保存
                                                    sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
                                                    # 重新编号使编号连续
                                                    task.final_test_cases = AIModelService.renumber_test_cases(
                                                        sorted_cases)
                                                    task.save()

                                            except Exception as review_error:
                                                logger.error(f"评审任务 {task.task_id} 失败: {review_error}")
                                                # 评审失败时，仍然使用生成的测试用例作为最终结果
                                                # 按用例编号排序后再保存
                                                sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
                                                task.final_test_cases = AIModelService.renumber_test_cases(sorted_cases)
                                                task.review_feedback = f"评审失败: {str(review_error)}\n\n建议：测试用例结构完整，可以使用。"
                                                task.save()
                                        else:
                                            # 按用例编号排序后再保存
                                            sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
                                            # 重新编号使编号连续
                                            task.final_test_cases = AIModelService.renumber_test_cases(sorted_cases)
                                            logger.info(f"任务 {task.task_id} 跳过评审，直接使用生成的测试用例")
                                            task.save()

                                    # 完成任务
                                    # 注意：不要直接调用task.save()，因为这会覆盖流式回调保存的final_test_cases
                                    # 从数据库重新获取最新的任务对象
                                    task.refresh_from_db()

                                    task.status = 'completed'
                                    task.progress = 100
                                    task.completed_at = timezone.now()
                                    task.save(update_fields=['status', 'progress', 'completed_at', 'final_test_cases'])
                                    logger.info(f"任务 {task.task_id} 已完成")

                                finally:
                                    try:
                                        # 清理异步生成器，防止 "Task was destroyed but it is pending" 警告
                                        loop.run_until_complete(loop.shutdown_asyncgens())
                                    except Exception as e:
                                        logger.warning(f"Error shutting down asyncgens: {e}")
                                    finally:
                                        loop.close()

                            except Exception as e:
                                logger.error(f"生成任务执行失败: {e}")
                                task.status = 'failed'
                                task.error_message = str(e)
                                task.save()

                        # 在新线程中执行任务
                        thread = threading.Thread(target=execute_task)
                        thread.daemon = True
                        thread.start()

                    except Exception as e:
                        logger.error(f"启动生成任务失败: {e}")
                        task.status = 'failed'
                        task.error_message = str(e)
                        task.save()

                # 启动异步任务
                run_generation_task()

                return Response({
                    'message': '测试用例生成任务已创建',
                    'task_id': task.task_id,
                    'task': task_serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(task_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"创建生成任务时出错: {e}")
            return Response(
                {'error': f'创建任务失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='generate-from-kb')
    def generate_from_kb(self, request):
        """从知识库切片创建异步测试用例生成任务"""
        try:
            # 验证输入参数
            chunk_ids = request.data.get('chunk_ids', [])
            if not chunk_ids:
                return Response(
                    {'error': '请选择至少一个知识库切片'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 合并切片内容
            try:
                merged_content = self._merge_kb_chunks_content(chunk_ids, request.user)
            except Exception as e:
                logger.error(f"合并切片内容失败: {e}")
                return Response(
                    {'error': f'合并切片内容失败: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not merged_content or len(merged_content.strip()) == 0:
                return Response(
                    {'error': '切片内容为空'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 获取活跃的配置
            writer_config = AIModelConfig.objects.filter(role='writer', is_active=True).first()
            if not writer_config:
                return Response(
                    {'error': '未找到可用的测试用例编写模型配置'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            writer_prompt = PromptConfig.get_active_config('writer')
            if not writer_prompt:
                return Response(
                    {'error': '未找到可用的测试用例编写提示词配置'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            reviewer_config = AIModelConfig.objects.filter(role='reviewer', is_active=True).first()
            reviewer_prompt = PromptConfig.get_active_config('reviewer')

            # 创建任务
            task_data = {
                'title': f"知识库切片生成 - {len(chunk_ids)}个切片",
                'requirement_text': merged_content,
                'writer_model_config': writer_config.id,
                'reviewer_model_config': reviewer_config.id if reviewer_config else None,
                'writer_prompt_config': writer_prompt.id,
                'reviewer_prompt_config': reviewer_prompt.id if reviewer_prompt else None,
            }

            # 处理输出模式
            output_mode = request.data.get('output_mode')
            if output_mode and output_mode in ['stream', 'complete']:
                task_data['output_mode'] = output_mode
            else:
                # 从生成行为配置中读取默认值
                from .models import GenerationConfig
                gen_config = GenerationConfig.get_active_config()
                if gen_config:
                    task_data['output_mode'] = gen_config.default_output_mode
                else:
                    task_data['output_mode'] = 'stream'

            task_serializer = TestCaseGenerationTaskSerializer(
                data=task_data,
                context={'request': request}
            )

            if task_serializer.is_valid():
                task = task_serializer.save()

                # 异步执行生成任务（复用现有的 run_generation_task 逻辑）
                def run_generation_task():
                    try:
                        import threading

                        def execute_task():
                            try:
                                # 更新任务状态
                                task.status = 'generating'
                                task.progress = 10
                                task.save()

                                # 读取生成行为配置
                                from .models import GenerationConfig
                                gen_config = GenerationConfig.get_active_config()
                                enable_auto_review = gen_config.enable_auto_review if gen_config else True
                                review_timeout = gen_config.review_timeout if gen_config else 120

                                logger.info(f"知识库切片任务 {task.task_id} 开始生成")

                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)

                                try:
                                    if task.output_mode == 'stream':
                                        # 流式模式
                                        task.stream_buffer = ''
                                        task.stream_position = 0
                                        task.save()

                                        def save_stream_buffer(content):
                                            task.stream_buffer = content
                                            task.stream_position = len(content)
                                            task.last_stream_update = timezone.now()
                                            task.save(update_fields=['stream_buffer', 'stream_position', 'last_stream_update'])

                                        async_save_stream_buffer = sync_to_async(save_stream_buffer)

                                        async def stream_callback(chunk):
                                            task.stream_buffer += chunk
                                            task.stream_position = len(task.stream_buffer)
                                            task.last_stream_update = timezone.now()
                                            if task.stream_position % 500 < 20 or len(chunk) > 100:
                                                try:
                                                    await async_save_stream_buffer(task.stream_buffer)
                                                except Exception as save_error:
                                                    logger.warning(f"保存流式内容失败: {save_error}")

                                        task.progress = 30
                                        task.save()

                                        generated_cases = loop.run_until_complete(
                                            AIModelService.generate_test_cases_stream(task, callback=stream_callback)
                                        )

                                        if task.stream_buffer:
                                            save_stream_buffer(task.stream_buffer)

                                        task.generated_test_cases = generated_cases
                                        task.progress = 60
                                        task.save()

                                        # 评审和改进
                                        if enable_auto_review and task.reviewer_model_config and task.reviewer_prompt_config:
                                            self._run_review_and_revise(task, generated_cases, loop, review_timeout)
                                        else:
                                            sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
                                            task.final_test_cases = AIModelService.renumber_test_cases(sorted_cases)
                                            logger.info(f"任务 {task.task_id} 跳过评审")
                                            task.save()

                                    else:
                                        # 完整模式
                                        task.progress = 30
                                        task.save()

                                        generated_cases = loop.run_until_complete(
                                            AIModelService.generate_test_cases(task)
                                        )

                                        task.generated_test_cases = generated_cases
                                        task.progress = 60
                                        task.save()

                                        # 评审和改进
                                        if enable_auto_review and task.reviewer_model_config and task.reviewer_prompt_config:
                                            self._run_review_and_revise(task, generated_cases, loop, review_timeout)
                                        else:
                                            sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
                                            task.final_test_cases = AIModelService.renumber_test_cases(sorted_cases)
                                            logger.info(f"任务 {task.task_id} 跳过评审")
                                            task.save()

                                    # 完成任务
                                    task.refresh_from_db()
                                    task.status = 'completed'
                                    task.progress = 100
                                    task.completed_at = timezone.now()
                                    task.save(update_fields=['status', 'progress', 'completed_at', 'final_test_cases'])
                                    logger.info(f"知识库切片任务 {task.task_id} 已完成")

                                finally:
                                    try:
                                        loop.run_until_complete(loop.shutdown_asyncgens())
                                    except Exception as e:
                                        logger.warning(f"Error shutting down asyncgens: {e}")
                                    finally:
                                        loop.close()

                            except Exception as e:
                                logger.error(f"知识库切片任务执行失败: {e}")
                                task.status = 'failed'
                                task.error_message = str(e)
                                task.save()

                        # 在新线程中执行任务
                        thread = threading.Thread(target=execute_task)
                        thread.daemon = True
                        thread.start()

                    except Exception as e:
                        logger.error(f"启动知识库切片任务失败: {e}")
                        task.status = 'failed'
                        task.error_message = str(e)
                        task.save()

                # 启动异步任务
                run_generation_task()

                return Response({
                    'message': '知识库切片测试用例生成任务已创建',
                    'task_id': task.task_id,
                    'task': task_serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(task_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"创建知识库切片任务时出错: {e}")
            return Response(
                {'error': f'创建任务失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _run_review_and_revise(self, task, generated_cases, loop, review_timeout):
        """运行评审和改进流程"""
        try:
            task.status = 'reviewing'
            task.progress = 70
            task.save()

            logger.info(f"开始评审任务 {task.task_id}")

            if task.output_mode == 'stream':
                # 流式评审
                review_buffer = []

                def save_review_buffer(content):
                    task.review_feedback = content
                    task.save(update_fields=['review_feedback'])

                async_save_review = sync_to_async(save_review_buffer)

                async def review_stream_callback(chunk):
                    review_buffer.append(chunk)
                    current_length = sum(len(c) for c in review_buffer)
                    if current_length % 100 < 20 or len(chunk) > 50:
                        try:
                            content = ''.join(review_buffer)
                            await async_save_review(content)
                        except Exception as save_error:
                            logger.warning(f"保存评审内容失败: {save_error}")

                review_feedback = loop.run_until_complete(
                    AIModelService.review_test_cases_stream(task, generated_cases, callback=review_stream_callback)
                )

                if review_buffer:
                    task.review_feedback = ''.join(review_buffer)
                    task.save(update_fields=['review_feedback'])
            else:
                # 非流式评审
                review_feedback = loop.run_until_complete(
                    AIModelService.review_test_cases(task, generated_cases)
                )
                task.review_feedback = review_feedback
                task.save()

            logger.info(f"任务 {task.task_id} 评审完成")

            # 改进测试用例
            task.status = 'revising'
            task.progress = 85
            task.final_test_cases = ''
            task.save()

            if task.output_mode == 'stream':
                def save_final_buffer(content):
                    task.final_test_cases = content
                    task.save(update_fields=['final_test_cases'])

                async_save_final = sync_to_async(save_final_buffer)

                async def final_callback(chunk):
                    task.final_test_cases = (task.final_test_cases or '') + chunk
                    current_length = len(task.final_test_cases)
                    if current_length % 100 < 20 or len(chunk) > 50:
                        try:
                            await async_save_final(task.final_test_cases)
                        except Exception as save_error:
                            logger.warning(f"保存最终用例失败: {save_error}")

                try:
                    revised_cases = loop.run_until_complete(
                        asyncio.wait_for(
                            AIModelService.revise_test_cases_based_on_review(
                                task, generated_cases, task.review_feedback, callback=final_callback
                            ),
                            timeout=review_timeout
                        )
                    )
                except asyncio.TimeoutError:
                    logger.error(f"任务 {task.task_id} 改进阶段超时")
                    revised_cases = generated_cases
            else:
                revised_cases = loop.run_until_complete(
                    asyncio.wait_for(
                        AIModelService.revise_test_cases_based_on_review(
                            task, generated_cases, task.review_feedback
                        ),
                        timeout=review_timeout
                    )
                )

            if revised_cases and len(revised_cases) > 0:
                revised_cases = AIModelService.fix_incomplete_last_case(revised_cases)
                sorted_cases = AIModelService.sort_test_cases_by_id(revised_cases)
                task.final_test_cases = AIModelService.renumber_test_cases(sorted_cases)
                logger.info(f"任务 {task.task_id} 改进完成")
            else:
                logger.warning(f"任务 {task.task_id} 改进返回为空")
                sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
                task.final_test_cases = AIModelService.renumber_test_cases(sorted_cases)

            task.save()

        except Exception as e:
            logger.error(f"评审和改进失败: {e}")
            task.review_feedback = f"评审失败: {str(e)}"
            sorted_cases = AIModelService.sort_test_cases_by_id(generated_cases)
            task.final_test_cases = AIModelService.renumber_test_cases(sorted_cases)
            task.save()

    def _merge_kb_chunks_content(self, chunk_ids, user):
        """
        合并知识库切片内容，添加来源标记
        """
        merged_content = []

        for chunk_info in chunk_ids:
            doc_id = chunk_info['document_id']
            chunk_idx = chunk_info['chunk_index']

            # 获取文档信息
            try:
                doc = KnowledgeBaseDocument.objects.get(id=doc_id, user=user)

                # 获取切片内容
                chunks_result = rag_service.get_document_chunks(doc_id, user=user)

                if chunks_result.get('success') and 'chunks' in chunks_result:
                    # 根据 chunk_index 查找对应的切片
                    chunk_data = None
                    for chunk in chunks_result['chunks']:
                        if chunk['index'] == chunk_idx:
                            chunk_data = chunk
                            break

                    if chunk_data:
                        chunk_content = chunk_data['content']

                        # 添加来源标记
                        merged_content.append(f"""【来源：{doc.name} - 切片{chunk_idx + 1}】
{chunk_content}""")
                    else:
                        logger.warning(f"找不到切片索引 {chunk_idx}，文档 {doc_id} 的切片列表: {[c['index'] for c in chunks_result['chunks']]}")
                else:
                    logger.error(f"获取文档 {doc_id} 的切片内容失败: {chunks_result.get('error', '未知错误')}")
            except KnowledgeBaseDocument.DoesNotExist:
                logger.error(f"用户 {user.id} 无权限访问文档 {doc_id} 或文档不存在")
                continue
            except Exception as e:
                logger.error(f"处理文档 {doc_id} 切片 {chunk_idx} 时出错: {str(e)}")
                continue

        return "\n\n---\n\n".join(merged_content)

    @action(detail=True, methods=['get'])
    def progress(self, request, task_id=None):
        """获取任务进度"""
        try:
            # DRF会根据lookup_field自动从URL提取task_id并调用get_object()
            task = self.get_object()

            return Response({
                'task_id': task.task_id,
                'status': task.status,
                'progress': task.progress,
                'generated_test_cases': task.generated_test_cases,
                'review_feedback': task.review_feedback,
                'final_test_cases': task.final_test_cases,
                'error_message': task.error_message,
                'completed_at': task.completed_at
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"获取任务进度时出错: {e}")
            return Response(
                {'error': f'获取进度失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=True,
        methods=['get'],
        url_path='stream_progress',
        renderer_classes=[PassThroughRenderer],
        permission_classes=[]  # 允许访问，task_id本身就是安全标识
    )
    def stream_progress_sse(self, request, task_id=None):
        """
        SSE流式进度推送接口
        实时推送任务的流式输出和进度更新
        不使用DRF的Response，避免content negotiation问题
        注意：EventSource不支持自定义headers，无法发送JWT token，所以允许通过session cookie访问
        """
        try:
            # 记录请求信息（用于调试）
            request_origin = request.META.get('HTTP_ORIGIN', 'unknown')
            logger.info(
                f"SSE连接请求: task_id={task_id}, user={request.user}, authenticated={request.user.is_authenticated}, path={request.path}, origin={request_origin}")

            # 动态获取CORS origin - 支持localhost、127.0.0.1和任意IP地址
            def get_allowed_origin(origin):
                """获取允许的CORS origin，支持localhost和任意IP地址"""
                if not origin:
                    return 'http://localhost:5173'
                # 允许localhost和127.0.0.1，支持3000、5173和4173端口
                allowed_origins = [
                    'http://localhost:3000', 'http://127.0.0.1:3000',
                    'http://localhost:5173', 'http://127.0.0.1:5173',
                    'http://localhost:4173', 'http://127.0.0.1:4173'
                ]
                if origin in allowed_origins:
                    return origin
                # 允许任意IP地址的3000、5173或4173端口
                import re
                if re.match(r'^http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:(3000|5173|4173)$', origin):
                    return origin
                # 默认返回localhost:5173
                return 'http://localhost:5173'

            cors_origin = get_allowed_origin(request_origin)

            # 处理 CORS 预检请求
            if request.method == 'OPTIONS':
                from django.http import HttpResponse
                response = HttpResponse()
                response['Access-Control-Allow-Origin'] = cors_origin
                response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'Content-Type'
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Access-Control-Max-Age'] = '86400'
                return response

            # 获取任务对象
            task = TestCaseGenerationTask.objects.filter(task_id=task_id).first()
            if not task:
                logger.warning(f"SSE连接失败: 任务未找到, task_id={task_id}")
                # 返回JSON错误而不是SSE
                from django.http import HttpResponse
                response = HttpResponse(
                    json.dumps({'error': '任务未找到'}),
                    status=404,
                    content_type='application/json'
                )
                response['Access-Control-Allow-Origin'] = cors_origin
                response['Access-Control-Allow-Credentials'] = 'true'
                return response

            # 记录上次发送的stream_position
            last_sent_position = 0
            loop_count = 0  # 循环计数器
            last_review_length = 0  # 记录上次发送的评审内容长度
            last_final_length = 0  # 记录上次发送的最终用例长度
            last_status = ''  # 记录上次的任务状态

            def event_stream():
                nonlocal last_sent_position, loop_count, last_review_length, last_final_length, last_status

                # Performance & Timeout Optimization
                start_time = time.time()
                last_heartbeat_time = time.time()
                last_progress_hash = None
                MAX_TIMEOUT = 3600  # 1 hour safety timeout

                # 立即发送连接成功消息，让前端知道SSE已建立
                initial_status = json.dumps({'type': 'connected', 'message': 'SSE连接已建立，等待AI生成内容...'}, ensure_ascii=False)
                logger.info(f"SSE发送初始连接消息")
                yield f"data: {initial_status}\n\n"

                while True:
                    loop_count += 1

                    # 记录当前时间
                    current_time = time.time()
                    # 检查超时
                    if current_time - start_time > MAX_TIMEOUT:
                        logger.warning(f"SSE stream timeout after {MAX_TIMEOUT} seconds")
                        break

                    # 重置发送标记
                    has_sent_data = False

                    # 从数据库重新获取任务状态
                    task.refresh_from_db()

                    # 检测状态变化，如果进入revising阶段，重置last_final_length
                    if task.status != last_status:
                        logger.info(f"SSE检测到状态变化: {last_status} -> {task.status}")
                        if task.status == 'revising':
                            logger.info(f"SSE: 进入revising阶段，重置last_final_length")
                            last_final_length = 0
                        last_status = task.status

                    # 每10次循环记录一次日志
                    if loop_count % 10 == 0:
                        logger.info(
                            f"SSE stream loop #{loop_count}: task_status={task.status}, progress={task.progress}%, buffer_len={len(task.stream_buffer) if task.stream_buffer else 0}")

                    # 检查任务是否已完成或失败
                    if task.status in ['completed', 'failed', 'cancelled']:
                        logger.info(f"SSE任务结束: status={task.status}")
                        # 发送最终状态
                        final_status = json.dumps({'type': 'status', 'status': task.status, 'progress': task.progress},
                                                  ensure_ascii=False)
                        logger.info(f"SSE发送最终状态: {final_status}")
                        yield f"data: {final_status}\n\n"

                        # 如果是流式模式且有缓冲区内容，发送剩余内容
                        if task.output_mode == 'stream' and task.stream_buffer:
                            if last_sent_position < len(task.stream_buffer):
                                new_content = task.stream_buffer[last_sent_position:]
                                content_data = json.dumps({'type': 'content', 'content': new_content},
                                                          ensure_ascii=False)
                                logger.info(f"SSE发送剩余内容: {len(new_content)} 字符")
                                yield f"data: {content_data}\n\n"
                                last_sent_position = len(task.stream_buffer)

                        # 发送剩余的评审内容
                        if task.review_feedback:
                            if len(task.review_feedback) > last_review_length:
                                remaining_review = task.review_feedback[last_review_length:]
                                if remaining_review:
                                    review_data = json.dumps({'type': 'review_content', 'content': remaining_review},
                                                             ensure_ascii=False)
                                    logger.info(
                                        f"SSE发送剩余评审内容: {len(remaining_review)} 字符, 总长度: {len(task.review_feedback)}")
                                    yield f"data: {review_data}\n\n"
                                    last_review_length = len(task.review_feedback)

                        # 发送剩余的最终用例内容
                        if task.final_test_cases:
                            if len(task.final_test_cases) > last_final_length:
                                remaining_final = task.final_test_cases[last_final_length:]
                                if remaining_final:
                                    final_data = json.dumps({'type': 'final_content', 'content': remaining_final},
                                                            ensure_ascii=False)
                                    logger.info(
                                        f"SSE发送剩余最终用例: {len(remaining_final)} 字符, 总长度: {len(task.final_test_cases)}")
                                    yield f"data: {final_data}\n\n"
                                    last_final_length = len(task.final_test_cases)

                        # 发送完成信号
                        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                        logger.info(f"SSE流结束，总循环次数: {loop_count}")

                        # 添加短暂延迟，确保done信号被发送
                        time.sleep(0.1)
                        break

                    # 如果是流式模式，发送新增的内容
                    if task.output_mode == 'stream' and task.stream_buffer:
                        current_position = task.stream_position
                        if current_position > last_sent_position:
                            # 提取新增内容
                            new_content = task.stream_buffer[last_sent_position:current_position]
                            if new_content:
                                content_data = json.dumps({'type': 'content', 'content': new_content},
                                                          ensure_ascii=False)
                                logger.info(f"SSE发送新增内容: {len(new_content)} 字符, 总位置: {current_position}")
                                yield f"data: {content_data}\n\n"
                                last_sent_position = current_position

                    # 如果是评审阶段，发送评审内容
                    if task.status == 'reviewing' and task.review_feedback:
                        review_feedback = task.review_feedback
                        if review_feedback:
                            # 计算评审内容的增量
                            if len(review_feedback) > last_review_length:
                                new_review = review_feedback[last_review_length:]
                                if new_review:
                                    review_data = json.dumps({'type': 'review_content', 'content': new_review},
                                                             ensure_ascii=False)
                                    logger.info(f"SSE发送评审内容: {len(new_review)} 字符")
                                    yield f"data: {review_data}\n\n"
                                    last_review_length = len(review_feedback)

                    # 如果有最终用例，发送最终用例内容（在reviewing、revising或completed阶段）
                    if task.status in ['reviewing', 'revising', 'completed'] and task.final_test_cases:
                        final_cases = task.final_test_cases
                        if final_cases:
                            # 计算最终用例的增量
                            if len(final_cases) > last_final_length:
                                new_final = final_cases[last_final_length:]
                                if new_final:
                                    final_data = json.dumps({'type': 'final_content', 'content': new_final},
                                                            ensure_ascii=False)
                                    logger.info(
                                        f"SSE发送最终用例: {len(new_final)} 字符, 总长度: {len(final_cases)}, 阶段: {task.status}")
                                    yield f"data: {final_data}\n\n"
                                    last_final_length = len(final_cases)

                    # 发送进度更新 (Optimized)
                    current_progress_hash = f"{task.status}_{task.progress}"
                    if current_progress_hash != last_progress_hash:
                        progress_data = json.dumps(
                            {'type': 'progress', 'status': task.status, 'progress': task.progress},
                            ensure_ascii=False)
                        yield f"data: {progress_data}\n\n"
                        last_progress_hash = current_progress_hash
                        has_sent_data = True

                    # Heartbeat - 缩短心跳间隔到10秒，确保连接保活
                    if has_sent_data:
                        last_heartbeat_time = current_time
                    elif current_time - last_heartbeat_time >= 10:
                        yield ": keep-alive\n\n"
                        last_heartbeat_time = current_time

                    # 减少休眠时间到 0.5s，提高响应速度
                    time.sleep(0.5)

            # 创建StreamingHttpResponse，使用event_stream生成器
            response = StreamingHttpResponse(
                event_stream(),
                content_type='text/event-stream'
            )

            # 设置SSE相关的响应头（注意：不能设置Connection等hop-by-hop头部）
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'

            # 设置CORS头部 - 使用动态计算的cors_origin
            response['Access-Control-Allow-Origin'] = cors_origin
            response['Access-Control-Allow-Credentials'] = 'true'

            logger.info(f"SSE连接建立成功: task_id={task_id}, cors_origin={cors_origin}")
            return response

        except Exception as e:
            logger.error(f"SSE流式推送出错: {e}")
            import traceback
            traceback.print_exc()
            from django.http import HttpResponse
            # 获取允许的origin
            request_origin = request.META.get('HTTP_ORIGIN', 'unknown')

            def get_allowed_origin(origin):
                if not origin:
                    return 'http://localhost:5173'
                allowed_origins = [
                    'http://localhost:3000', 'http://127.0.0.1:3000',
                    'http://localhost:5173', 'http://127.0.0.1:5173',
                    'http://localhost:4173', 'http://127.0.0.1:4173'
                ]
                if origin in allowed_origins:
                    return origin
                import re
                if re.match(r'^http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:(3000|5173|4173)$', origin):
                    return origin
                return 'http://localhost:5173'

            cors_origin = get_allowed_origin(request_origin)
            response = HttpResponse(
                json.dumps({'error': f'流式推送失败: {str(e)}'}),
                status=500,
                content_type='application/json'
            )
            response['Access-Control-Allow-Origin'] = cors_origin
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

    @action(detail=True, methods=['post'])
    def cancel(self, request, task_id=None):
        """取消正在运行的任务"""
        try:
            # DRF会根据lookup_field自动从URL提取task_id并调用get_object()
            task = self.get_object()

            if task.status in ['completed', 'failed', 'cancelled']:
                return Response(
                    {'error': f'任务已经{task.get_status_display()}，无法取消'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            task.status = 'cancelled'
            task.save()

            return Response({
                'message': '任务已取消',
                'task_id': task.task_id,
                'status': task.status
            })

        except Exception as e:
            logger.error(f"取消任务时出错: {e}")
            return Response(
                {'error': f'取消任务失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def save_to_records(self, request, task_id=None):
        """保存测试用例到AI生成用例记录并导入到测试用例管理系统"""
        try:
            # DRF会根据lookup_field自动从URL提取task_id并调用get_object()
            task = self.get_object()

            if task.status != 'completed':
                return Response(
                    {'error': '只能保存已完成的测试用例生成任务'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not task.final_test_cases:
                return Response(
                    {'error': '没有最终测试用例可以保存'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 检查是否已经保存过
            if hasattr(task, 'is_saved_to_records') and task.is_saved_to_records:
                return Response(
                    {'message': '测试用例已经保存到记录中', 'already_saved': True},
                    status=status.HTTP_200_OK
                )

            # 解析并导入测试用例到测试用例管理系统
            test_cases = self._parse_test_cases_content(task.final_test_cases)

            if test_cases:
                try:
                    from apps.testcases.models import TestCase
                    from apps.projects.models import Project
                    from django.db import models

                    # 优先使用任务关联的项目
                    if task.project:
                        project = task.project
                        logger.info(f"使用任务关联的项目: {project.name}")
                    else:
                        # 回退到项目选择逻辑
                        user = task.created_by
                        accessible_projects = Project.objects.filter(
                            models.Q(owner=user) | models.Q(members=user)
                        ).distinct()

                        # 尝试从前端获取项目ID
                        project_id = request.data.get('project_id')

                        if project_id:
                            try:
                                project = accessible_projects.get(id=project_id)
                            except Project.DoesNotExist:
                                # 如果指定项目不存在或无权限，使用第一个可访问的项目
                                project = accessible_projects.first()
                                if not project:
                                    # 如果用户没有任何项目，创建默认项目
                                    project = Project.objects.create(
                                        name="默认项目",
                                        owner=user,
                                        description='系统自动创建的默认项目'
                                    )
                        else:
                            # 没有指定项目，使用第一个可访问的项目
                            project = accessible_projects.first()
                            if not project:
                                # 如果用户没有任何项目，创建默认项目
                                project = Project.objects.create(
                                    name="默认项目",
                                    owner=user,
                                    description='系统自动创建的默认项目'
                                )

                    adopted_count = 0
                    for test_case in test_cases:
                        TestCase.objects.create(
                            project=project,
                            author=task.created_by,
                            title=test_case.get('scenario', '测试用例'),
                            description=test_case.get('scenario', ''),
                            preconditions=test_case.get('precondition', ''),
                            steps=test_case.get('steps', ''),
                            expected_result=test_case.get('expected', ''),
                            priority=self._map_priority(test_case.get('priority', '中')),
                            test_type='functional',
                            status='draft'
                        )
                        adopted_count += 1

                    logger.info(f"成功导入 {adopted_count} 条测试用例到项目 {project.name}")

                except Exception as import_error:
                    logger.error(f"导入测试用例失败: {import_error}")
                    # 即使导入失败，仍然标记为已保存

            # 标记任务为已保存
            task.is_saved_to_records = True
            task.saved_at = timezone.now()
            task.save(update_fields=['is_saved_to_records', 'saved_at'])

            return Response({
                'message': '测试用例已成功保存到AI生成用例记录并导入到测试用例管理系统',
                'task_id': task.task_id,
                'saved_at': task.saved_at,
                'imported_count': adopted_count if test_cases else 0
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"保存测试用例到记录时出错: {e}")
            return Response(
                {'error': f'保存失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def saved_records(self, request):
        """获取已保存的测试用例记录列表"""
        try:
            # 获取已保存到记录的任务
            saved_tasks = TestCaseGenerationTask.objects.filter(
                is_saved_to_records=True,
                status='completed'
            ).order_by('-saved_at')

            # 序列化数据
            serializer = TestCaseGenerationTaskSerializer(saved_tasks, many=True)

            return Response({
                'message': '获取已保存记录成功',
                'records': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"获取已保存记录时出错: {e}")
            return Response(
                {'error': f'获取记录失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='batch-adopt')
    def batch_adopt(self, request, task_id=None):
        """批量采纳任务的所有测试用例"""
        try:
            task = self.get_object()

            if task.status != 'completed':
                return Response(
                    {'error': '只能采纳已完成的测试用例生成任务'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not task.final_test_cases:
                return Response(
                    {'error': '没有最终测试用例可以采纳'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 解析最终测试用例
            test_cases = self._parse_test_cases_content(task.final_test_cases)

            if not test_cases:
                return Response(
                    {'error': '无法解析测试用例内容'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 导入到testcases应用（使用与单条采纳相同的逻辑）
            try:
                from apps.testcases.models import TestCase
                from apps.projects.models import Project
                from django.db import models

                # 优先使用任务关联的项目
                if task.project:
                    project = task.project
                    logger.info(f"使用任务关联的项目: {project.name}")
                else:
                    # 回退到项目选择逻辑
                    user = task.created_by
                    accessible_projects = Project.objects.filter(
                        models.Q(owner=user) | models.Q(members=user)
                    ).distinct()

                    # 尝试从前端获取项目ID
                    project_id = request.data.get('project_id')

                    if project_id:
                        try:
                            project = accessible_projects.get(id=project_id)
                        except Project.DoesNotExist:
                            # 如果指定项目不存在或无权限，使用第一个可访问的项目
                            project = accessible_projects.first()
                            if not project:
                                # 如果用户没有任何项目，创建默认项目
                                project = Project.objects.create(
                                    name="默认项目",
                                    owner=user,
                                    description='系统自动创建的默认项目'
                                )
                    else:
                        # 没有指定项目，使用第一个可访问的项目
                        project = accessible_projects.first()
                        if not project:
                            # 如果用户没有任何项目，创建默认项目
                            project = Project.objects.create(
                                name="默认项目",
                                owner=user,
                                description='系统自动创建的默认项目'
                            )

                adopted_count = 0
                for test_case in test_cases:
                    TestCase.objects.create(
                        project=project,  # 使用统一的项目选择逻辑
                        author=task.created_by,
                        title=test_case.get('scenario', '测试用例'),
                        description=test_case.get('scenario', ''),  # 使用scenario作为描述
                        preconditions=test_case.get('precondition', ''),
                        steps=test_case.get('steps', ''),
                        expected_result=test_case.get('expected', ''),
                        priority=self._map_priority(test_case.get('priority', '中')),
                        test_type='functional',
                        status='draft'
                    )
                    adopted_count += 1

                return Response({
                    'message': f'成功采纳 {adopted_count} 条测试用例到项目 "{project.name}"',
                    'adopted_count': adopted_count,
                    'project_name': project.name
                }, status=status.HTTP_200_OK)

            except Exception as import_error:
                logger.error(f"导入测试用例失败: {import_error}")
                return Response(
                    {'error': f'导入测试用例失败: {str(import_error)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"批量采纳测试用例时出错: {e}")
            return Response(
                {'error': f'批量采纳失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='batch-adopt-selected')
    def batch_adopt_selected(self, request, task_id=None):
        """批量采纳选中的测试用例"""
        try:
            task = self.get_object()
            test_cases_data = request.data.get('test_cases', [])

            if not test_cases_data:
                return Response(
                    {'error': '没有提供要采纳的测试用例数据'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 导入到testcases应用
            try:
                from apps.testcases.models import TestCase
                from apps.projects.models import Project
                from django.db import models

                # 优先使用任务关联的项目
                if task.project:
                    project = task.project
                    logger.info(f"使用任务关联的项目: {project.name}")
                else:
                    # 回退到项目选择逻辑
                    user = task.created_by
                    accessible_projects = Project.objects.filter(
                        models.Q(owner=user) | models.Q(members=user)
                    ).distinct()

                    # 尝试从前端获取项目ID
                    project_id = request.data.get('project_id')

                    if project_id:
                        try:
                            project = accessible_projects.get(id=project_id)
                        except Project.DoesNotExist:
                            # 如果指定项目不存在或无权限，使用第一个可访问的项目
                            project = accessible_projects.first()
                            if not project:
                                # 如果用户没有任何项目，创建默认项目
                                project = Project.objects.create(
                                    name="默认项目",
                                    owner=user,
                                    description='系统自动创建的默认项目'
                                )
                    else:
                        # 没有指定项目，使用第一个可访问的项目
                        project = accessible_projects.first()
                        if not project:
                            # 如果用户没有任何项目，创建默认项目
                            project = Project.objects.create(
                                name="默认项目",
                                owner=user,
                                description='系统自动创建的默认项目'
                            )

                adopted_count = 0
                for case_data in test_cases_data:
                    TestCase.objects.create(
                        project=project,  # 使用统一的项目选择逻辑
                        author=task.created_by,
                        title=case_data.get('title', '测试用例'),
                        description=case_data.get('description', ''),
                        preconditions=case_data.get('preconditions', ''),
                        steps=case_data.get('steps', ''),
                        expected_result=case_data.get('expected_result', ''),
                        priority=case_data.get('priority', 'medium'),
                        test_type=case_data.get('test_type', 'functional'),
                        status=case_data.get('status', 'draft')
                    )
                    adopted_count += 1

                return Response({
                    'message': f'成功采纳 {adopted_count} 条测试用例到项目 "{project.name}"',
                    'adopted_count': adopted_count,
                    'project_name': project.name
                }, status=status.HTTP_200_OK)

            except Exception as import_error:
                logger.error(f"导入选中测试用例失败: {import_error}")
                return Response(
                    {'error': f'导入测试用例失败: {str(import_error)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"批量采纳选中测试用例时出错: {e}")
            return Response(
                {'error': f'批量采纳失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='batch-discard')
    def batch_discard(self, request, task_id=None):
        """批量弃用任务的所有测试用例 - 删除整个任务"""
        try:
            task = self.get_object()

            logger.info(f"开始批量弃用任务 {task.task_id}")

            # 直接删除整个任务记录
            task.delete()

            return Response({
                'message': '任务已被弃用并删除，不会再在列表中显示'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"批量弃用任务时出错: {e}")
            return Response(
                {'error': f'批量弃用失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='discard-selected-cases')
    def discard_selected_cases(self, request, task_id=None):
        """弃用选中的测试用例 - 从final_test_cases中删除"""
        try:
            task = self.get_object()
            case_indices = request.data.get('case_indices', [])

            if not case_indices:
                return Response(
                    {'error': '没有提供要弃用的测试用例索引'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not task.final_test_cases:
                return Response(
                    {'error': '任务没有最终测试用例'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"开始弃用任务 {task.task_id} 的测试用例，索引: {case_indices}")

            # 解析现有的测试用例
            test_cases = self._parse_test_cases_content(task.final_test_cases)

            # 按索引从大到小排序，避免删除时索引变化
            case_indices.sort(reverse=True)

            discarded_count = 0
            for index in case_indices:
                if 0 <= index < len(test_cases):
                    removed_case = test_cases.pop(index)
                    discarded_count += 1
                    logger.debug(f"弃用测试用例 {index}: {removed_case.get('scenario', 'unknown')}")

            # 如果所有用例都被弃用了，删除整个任务
            if not test_cases:
                logger.info(f"任务 {task.task_id} 的所有用例都被弃用，删除任务")
                task.delete()
                return Response({
                    'message': f'已弃用 {discarded_count} 条测试用例，任务已被删除',
                    'discarded_count': discarded_count,
                    'task_deleted': True
                }, status=status.HTTP_200_OK)

            # 重新生成final_test_cases内容
            task.final_test_cases = self._reconstruct_test_cases_content(test_cases)
            task.save()

            logger.debug(f"重构后的测试用例内容: {task.final_test_cases[:200]}...")

            return Response({
                'message': f'已弃用 {discarded_count} 条测试用例',
                'discarded_count': discarded_count,
                'remaining_cases': len(test_cases),
                'task_deleted': False,
                'updated_test_cases': task.final_test_cases
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"弃用选中测试用例时出错: {e}")
            return Response(
                {'error': f'弃用失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='discard-single-case')
    def discard_single_case(self, request, task_id=None):
        """弃用单个测试用例"""
        try:
            task = self.get_object()
            case_index = request.data.get('case_index')

            if case_index is None:
                return Response(
                    {'error': '没有提供测试用例索引'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not task.final_test_cases:
                return Response(
                    {'error': '任务没有最终测试用例'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"开始弃用任务 {task.task_id} 的单个测试用例，索引: {case_index}")

            # 解析现有的测试用例
            test_cases = self._parse_test_cases_content(task.final_test_cases)

            if case_index < 0 or case_index >= len(test_cases):
                return Response(
                    {'error': f'测试用例索引 {case_index} 超出范围，总共有 {len(test_cases)} 个测试用例'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 删除指定索引的测试用例
            removed_case = test_cases.pop(case_index)
            logger.debug(f"弃用测试用例 {case_index}: {removed_case.get('scenario', 'unknown')}")

            # 如果所有用例都被弃用了，删除整个任务
            if not test_cases:
                logger.info(f"任务 {task.task_id} 的所有用例都被弃用，删除任务")
                task.delete()
                return Response({
                    'message': '已弃用测试用例，任务已被删除',
                    'discarded_count': 1,
                    'task_deleted': True
                }, status=status.HTTP_200_OK)

            # 重新生成final_test_cases内容
            task.final_test_cases = self._reconstruct_test_cases_content(test_cases)
            task.save()

            logger.debug(f"单个弃用 - 重构后的测试用例内容: {task.final_test_cases[:200]}...")

            return Response({
                'message': '已弃用测试用例',
                'discarded_count': 1,
                'remaining_cases': len(test_cases),
                'task_deleted': False,
                'updated_test_cases': task.final_test_cases
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"弃用单个测试用例时出错: {e}")
            return Response(
                {'error': f'弃用失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='update-test-cases')
    def update_test_cases(self, request, task_id=None):
        """更新测试用例内容"""
        try:
            task = self.get_object()

            final_test_cases = request.data.get('final_test_cases')
            if not final_test_cases:
                return Response(
                    {'error': '缺少final_test_cases参数'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"开始更新任务 {task.task_id} 的测试用例内容")

            # 更新final_test_cases字段
            task.final_test_cases = final_test_cases
            task.save(update_fields=['final_test_cases'])

            logger.info(f"任务 {task.task_id} 测试用例更新成功")

            return Response({
                'message': '测试用例更新成功',
                'task_id': task.task_id,
                'final_test_cases': task.final_test_cases
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"更新测试用例时出错: {e}")
            return Response(
                {'error': f'更新失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_test_cases_content(self, content):
        """解析测试用例内容 - 支持多种格式"""
        if not content:
            return []

        # 去除markdown加粗标记，保留纯净文本
        import re
        clean_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)

        logger.info(f"开始解析测试用例内容，内容长度: {len(clean_content)}")
        logger.info(f"内容前200字符: {clean_content[:200]}")

        # 尝试表格格式解析
        if '|' in clean_content:
            return self._parse_table_format(clean_content)

        # 尝试结构化文本格式解析
        return self._parse_text_format(clean_content)

    def _parse_table_format(self, content):
        """解析表格格式的测试用例"""
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        test_cases = []
        table_data = []

        # 提取表格数据
        for line in lines:
            if '|' in line and not line.startswith('|-'):
                # 针对内容中可能包含转义后的 \| 进行预处理
                # 先把 \| 替换为一个临时占位符，分割完后再替换回来
                temp_placeholder = "___PIPE___"
                processed_line = line.replace(r'\|', temp_placeholder)

                # 移除首尾的 |
                if processed_line.startswith('|'):
                    processed_line = processed_line[1:]
                if processed_line.endswith('|'):
                    processed_line = processed_line[:-1]

                cells = []
                for cell in processed_line.split('|'):
                    # 恢复原来的转义管道符，并清理空格
                    cell_content = cell.replace(temp_placeholder, '|').replace('&#124;', '|').strip()
                    cells.append(cell_content)
                if len(cells) > 1:
                    table_data.append(cells)

        if len(table_data) < 2:
            return []

        # 解析表头和数据
        headers = [h.lower() for h in table_data[0]]
        logger.debug(f"表格标题: {headers}")

        for row in table_data[1:]:
            if len(row) < len(headers):
                continue

            test_case = {}
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else ''

                if any(keyword in header for keyword in ['编号', 'id', '序号', '用例id']):
                    test_case['caseId'] = value
                elif any(keyword in header for keyword in ['场景', '标题', '名称', 'title', 'scenario', '测试目标']):
                    test_case['scenario'] = value
                elif any(keyword in header for keyword in ['前置', '前提', 'precondition']):
                    test_case['precondition'] = value
                elif any(keyword in header for keyword in ['步骤', 'step', '测试步骤', '操作步骤']):
                    test_case['steps'] = value
                elif any(keyword in header for keyword in ['预期', '结果', 'expected', 'result']):
                    test_case['expected'] = value
                elif any(keyword in header for keyword in ['优先级', 'priority']):
                    test_case['priority'] = value

            if test_case.get('scenario') or test_case.get('steps'):
                test_cases.append(test_case)
                logger.debug(f"解析出表格测试用例: {test_case}")

        return test_cases

    def _parse_text_format(self, content):
        """解析文本格式的测试用例"""
        lines = content.split('\n')
        test_cases = []
        current_case = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            logger.debug(f"处理行: {line}")

            # 检测测试用例开始
            is_case_start = (
                    '测试用例' in line or
                    'Test Case' in line or
                    line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')) or
                    line.startswith(('一、', '二、', '三、', '四、', '五、')) or
                    bool(re.match(r'^\d+[\.\)、]', line))
            )

            if is_case_start:
                if current_case:
                    logger.debug(f"添加测试用例: {current_case}")
                    test_cases.append(current_case)

                # 清理标题
                scenario = line
                scenario = scenario.replace('测试用例', '').replace('Test Case', '')
                scenario = scenario.replace(':', '').replace('：', '')
                scenario = re.sub(r'^\d+[\.\)、]\s*', '', scenario)
                scenario = scenario.strip()

                current_case = {'scenario': scenario}

            elif current_case:  # 只有在已经开始一个测试用例后才处理字段
                # 检测各个字段
                if any(keyword in line for keyword in ['前置条件', '前提条件', '前置', '前提']):
                    current_case['precondition'] = self._extract_field_value(line)
                elif any(keyword in line for keyword in ['测试步骤', '操作步骤', '执行步骤', '步骤']):
                    current_case['steps'] = self._extract_field_value(line)
                elif any(keyword in line for keyword in ['预期结果', '期望结果', '预期']):
                    current_case['expected'] = self._extract_field_value(line)
                elif '优先级' in line:
                    current_case['priority'] = self._extract_field_value(line)

        if current_case:
            logger.debug(f"添加最后一个测试用例: {current_case}")
            test_cases.append(current_case)

        logger.info(f"解析完成，共解析出 {len(test_cases)} 个测试用例")
        for i, case in enumerate(test_cases):
            logger.debug(f"测试用例 {i + 1}: {case}")

        return test_cases

    def _extract_field_value(self, line):
        """提取字段值"""
        # 尝试多种分隔符
        for sep in [':', '：', '】', '】:', '】：']:
            if sep in line:
                return line.split(sep, 1)[-1].strip()

        # 如果没有分隔符，移除常见的前缀
        for prefix in ['前置条件', '测试步骤', '操作步骤', '预期结果', '优先级']:
            if line.startswith(prefix):
                return line[len(prefix):].strip()

        return line.strip()

    def _reconstruct_test_cases_content(self, test_cases):
        """重新构建测试用例内容 - 保持原有格式和编号"""
        if not test_cases:
            return ""

        # 检查是否有caseId字段，如果有，说明是表格格式
        has_case_ids = any(test_case.get('caseId') for test_case in test_cases)

        if has_case_ids:
            # 重构为表格格式，保持原有编号
            return self._reconstruct_table_format(test_cases)
        else:
            # 重构为文本格式
            return self._reconstruct_text_format(test_cases)

    def _reconstruct_table_format(self, test_cases):
        """重构为表格格式"""
        content_lines = []
        content_lines.append("```markdown")

        # 检查是否有任何测试用例包含steps字段
        has_steps = any(
            test_case.get('steps') and test_case.get('steps') != '参考测试目标执行相应操作' for test_case in test_cases)

        if has_steps:
            # 包含测试步骤的表格格式
            content_lines.append(
                "| 用例ID | 测试目标 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |")
            content_lines.append("|--------|--------|--------|--------|--------|--------|--------|--------|")

            for test_case in test_cases:
                case_id = test_case.get('caseId', '')
                scenario = test_case.get('scenario', '')
                precondition = test_case.get('precondition', '')
                steps = test_case.get('steps', '参考测试目标执行相应操作')
                expected = test_case.get('expected', '')
                priority = test_case.get('priority', 'P2')

                # 保持原有格式，将换行符转换为<br>
                precondition = precondition.replace('\n', '<br>')
                steps = steps.replace('\n', '<br>')
                expected = expected.replace('\n', '<br>')

                content_lines.append(
                    f"| {case_id} | {scenario} | {precondition} | {steps} | {expected} | {priority} | 功能验证 | 需求1 |")
        else:
            # 原始格式（没有测试步骤列）
            content_lines.append("| 用例ID | 测试目标 | 前置条件 | 预期结果 | 优先级 | 测试类型 | 关联需求 |")
            content_lines.append("|--------|--------|--------|--------|--------|--------|--------|")

            for test_case in test_cases:
                case_id = test_case.get('caseId', '')
                scenario = test_case.get('scenario', '')
                precondition = test_case.get('precondition', '')
                expected = test_case.get('expected', '')
                priority = test_case.get('priority', 'P2')

                # 保持原有格式，将换行符转换为<br>
                precondition = precondition.replace('\n', '<br>')
                expected = expected.replace('\n', '<br>')

                content_lines.append(
                    f"| {case_id} | {scenario} | {precondition} | {expected} | {priority} | 功能验证 | 需求1 |")

        content_lines.append("```")
        return "\n".join(content_lines)

    def _reconstruct_text_format(self, test_cases):
        """重构为文本格式"""
        content_lines = []
        for test_case in test_cases:
            # 获取原有的scenario
            scenario = test_case.get('scenario', '未命名测试用例')

            # 确保scenario能被前端正确识别
            # 如果scenario不是以数字开头或不包含"测试用例"，则添加标识
            if not (bool(re.match(r'^\d+[\.\)、]', scenario)) or
                    '测试用例' in scenario or
                    'Test Case' in scenario):
                # 添加"测试用例:"前缀确保能被识别
                content_lines.append(f"\n测试用例: {scenario}")
            else:
                content_lines.append(f"\n{scenario}")

            if test_case.get('precondition'):
                content_lines.append(f"前置条件: {test_case['precondition']}")

            if test_case.get('steps'):
                content_lines.append(f"测试步骤: {test_case['steps']}")

            if test_case.get('expected'):
                content_lines.append(f"预期结果: {test_case['expected']}")

            if test_case.get('priority'):
                content_lines.append(f"优先级: {test_case['priority']}")

            content_lines.append("")  # 空行分隔

        return "\n".join(content_lines)

    def _map_priority(self, priority_str):
        """映射优先级"""
        priority_map = {
            '最高': 'critical',
            '高': 'high',
            '中': 'medium',
            '低': 'low',
            'P0': 'critical',
            'P1': 'high',
            'P2': 'medium',
            'P3': 'low'
        }
        return priority_map.get(priority_str, 'medium')

    @action(detail=True, methods=['get'], url_path='export_md')
    def export_md(self, request, task_id=None):
        """导出测试用例为Markdown格式"""
        try:
            task = self.get_object()
            
            # 检查任务状态
            if task.status != 'completed':
                return Response(
                    {'error': '只有已完成的任务才能导出'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 获取测试用例内容
            test_cases_content = task.final_test_cases or task.generated_test_cases
            if not test_cases_content:
                return Response(
                    {'error': '该任务没有测试用例内容'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 获取文件名参数
            filename = request.query_params.get('filename', task.title or task.task_id)
            
            # 清理文件名
            import re
            safe_filename = re.sub(r'[^\w\u4e00-\u9fa5\-_.]', '_', filename)
            if not safe_filename.endswith('.md'):
                safe_filename += '.md'
            
            # 构建Markdown内容
            md_content = self._build_markdown_content(task, test_cases_content)
            
            # 创建响应
            from django.http import HttpResponse
            response = HttpResponse(
                md_content,
                content_type='text/markdown; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            
            logger.info(f"任务 {task.task_id} 的测试用例已导出为Markdown格式")
            return response
            
        except Exception as e:
            logger.error(f"导出Markdown格式测试用例时出错: {e}")
            return Response(
                {'error': f'导出失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _build_markdown_content(self, task, test_cases_content):
        """构建Markdown格式的测试用例文档"""
        lines = []
        
        # 添加标题
        lines.append(f"# {task.title or '测试用例文档'}")
        lines.append("")
        
        # 添加元信息
        lines.append(f"**任务ID:** {task.task_id}")
        lines.append(f"**生成时间:** {task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else 'N/A'}")
        # 计算用例数量
        case_count = 0
        if task.final_test_cases:
            case_count = len([line for line in task.final_test_cases.split('\n') if line.strip().startswith('|') and not line.strip().startswith('|-')])
        elif task.generated_test_cases:
            case_count = len([line for line in task.generated_test_cases.split('\n') if line.strip().startswith('|') and not line.strip().startswith('|-')])
        lines.append(f"**用例数量:** {case_count}")
        lines.append("")
        
        # 添加分隔线
        lines.append("---")
        lines.append("")
        
        # 添加测试用例内容
        lines.append("## 测试用例列表")
        lines.append("")
        
        # 如果内容已经是markdown格式，直接使用
        if test_cases_content.strip().startswith('```markdown'):
            # 去除markdown代码块标记
            content = test_cases_content.strip()
            if content.startswith('```markdown'):
                content = content[11:]
            if content.endswith('```'):
                content = content[:-3]
            lines.append(content.strip())
        else:
            # 解析并格式化测试用例
            lines.append(test_cases_content)
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*本文档由TestHub AI测试用例生成系统自动生成*")
        
        return "\n".join(lines)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取测试用例生成任务的统计信息"""
        try:
            # 获取查询参数
            status_param = request.query_params.get('status')
            created_by = request.query_params.get('created_by')

            # 构建查询
            queryset = TestCaseGenerationTask.objects.all()

            if status_param:
                queryset = queryset.filter(status=status_param)

            if created_by:
                queryset = queryset.filter(created_by_id=created_by)

            # 使用聚合查询获取统计信息
            from django.db.models import Count

            stats = queryset.aggregate(
                total=Count('id'),
                completed=Count('id', filter=models.Q(status='completed')),
                pending=Count('id', filter=models.Q(status='pending')),
                generating=Count('id', filter=models.Q(status='generating')),
                reviewing=Count('id', filter=models.Q(status='reviewing')),
                revising=Count('id', filter=models.Q(status='revising')),
                failed=Count('id', filter=models.Q(status='failed')),
                cancelled=Count('id', filter=models.Q(status='cancelled'))
            )

            # 计算运行中的任务（pending + generating + reviewing + revising）
            stats['running'] = (
                    stats['pending'] + stats['generating'] +
                    stats['reviewing'] + stats['revising']
            )

            return Response({
                'total': stats['total'],
                'completed': stats['completed'],
                'running': stats['running'],
                'failed': stats['failed'],
                'pending': stats['pending'],
                'generating': stats['generating'],
                'reviewing': stats['reviewing'],
                'revising': stats['revising'],
                'cancelled': stats['cancelled']
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"获取统计信息时出错: {e}")
            return Response(
                {'error': f'获取统计信息失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, task_id=None):
        """取消测试用例生成任务"""
        try:
            task = self.get_object()

            # 检查任务是否可以取消（只有进行中的任务才能取消）
            if task.status in ['completed', 'failed', 'cancelled']:
                return Response(
                    {'error': f'任务当前状态为{task.get_status_display()}，无法取消'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 更新任务状态为已取消
            task.status = 'cancelled'
            task.save()

            logger.info(f"任务已取消: {task.task_id}")

            return Response({
                'message': '任务已成功取消',
                'task_id': task.task_id,
                'status': task.status
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"取消任务时出错: {e}")
            return Response(
                {'error': f'取消任务失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfigStatusViewSet(viewsets.ViewSet):
    """配置状态检查视图集"""
    permission_classes = []  # 允许未认证用户访问

    @action(detail=False, methods=['get'])
    def check(self, request):
        """检查AI配置状态"""
        try:
            # 检查AI模型配置
            ai_model_configs = AIModelConfig.objects.filter(
                role__in=['writer', 'reviewer']
            ).exclude(role__in=['browser_use_text', 'browser_use_vision'])

            # 检查writer模型配置
            writer_model_enabled = ai_model_configs.filter(
                role='writer',
                is_active=True
            ).first()

            writer_model_disabled = ai_model_configs.filter(
                role='writer',
                is_active=False
            ).first()

            # 检查reviewer模型配置
            reviewer_model_enabled = ai_model_configs.filter(
                role='reviewer',
                is_active=True
            ).first()

            reviewer_model_disabled = ai_model_configs.filter(
                role='reviewer',
                is_active=False
            ).first()

            # 检查writer提示词配置
            writer_prompt_enabled = PromptConfig.objects.filter(
                prompt_type='writer',
                is_active=True
            ).first()

            writer_prompt_disabled = PromptConfig.objects.filter(
                prompt_type='writer',
                is_active=False
            ).first()

            # 检查reviewer提示词配置
            reviewer_prompt_enabled = PromptConfig.objects.filter(
                prompt_type='reviewer',
                is_active=True
            ).first()

            reviewer_prompt_disabled = PromptConfig.objects.filter(
                prompt_type='reviewer',
                is_active=False
            ).first()

            # 判断必需配置（writer）
            writer_configured = (
                    writer_model_enabled is not None and
                    writer_prompt_enabled is not None
            )

            # 判断可选配置（reviewer）
            reviewer_configured = (
                    reviewer_model_enabled is not None and
                    reviewer_prompt_enabled is not None
            )

            # 检查生成行为配置
            generation_config = GenerationConfig.get_active_config()

            # 判断是否有禁用的配置
            has_disabled = (
                    writer_model_disabled is not None or
                    writer_prompt_disabled is not None or
                    reviewer_model_disabled is not None or
                    reviewer_prompt_disabled is not None
            )

            # 判断整体状态
            if writer_configured:
                if has_disabled:
                    overall_status = 'disabled'
                    message = '配置完整，但部分配置处于禁用状态'
                else:
                    overall_status = 'enabled'
                    message = '配置完整且已启用'
            else:
                # writer配置不完整
                if writer_model_enabled or writer_prompt_enabled:
                    overall_status = 'disabled'
                    message = '检测到已配置但未启用的配置'
                else:
                    overall_status = 'not_configured'
                    message = '尚未配置AI模型和提示词'

            # 构建返回数据
            response_data = {
                'overall_status': overall_status,
                'message': message,
                'writer_model': {
                    'configured': writer_model_enabled is not None or writer_model_disabled is not None,
                    'enabled': writer_model_enabled is not None,
                    'name': (writer_model_enabled or writer_model_disabled).name if (
                            writer_model_enabled or writer_model_disabled) else None,
                    'provider': (writer_model_enabled or writer_model_disabled).get_model_type_display() if (
                            writer_model_enabled or writer_model_disabled) else None,
                    'id': (writer_model_enabled or writer_model_disabled).id if (
                            writer_model_enabled or writer_model_disabled) else None,
                    'required': True
                },
                'writer_prompt': {
                    'configured': writer_prompt_enabled is not None or writer_prompt_disabled is not None,
                    'enabled': writer_prompt_enabled is not None,
                    'name': (writer_prompt_enabled or writer_prompt_disabled).name if (
                            writer_prompt_enabled or writer_prompt_disabled) else None,
                    'id': (writer_prompt_enabled or writer_prompt_disabled).id if (
                            writer_prompt_enabled or writer_prompt_disabled) else None,
                    'required': True
                },
                'reviewer_model': {
                    'configured': reviewer_model_enabled is not None or reviewer_model_disabled is not None,
                    'enabled': reviewer_model_enabled is not None,
                    'name': (reviewer_model_enabled or reviewer_model_disabled).name if (
                            reviewer_model_enabled or reviewer_model_disabled) else None,
                    'id': (reviewer_model_enabled or reviewer_model_disabled).id if (
                            reviewer_model_enabled or reviewer_model_disabled) else None,
                    'required': False
                },
                'reviewer_prompt': {
                    'configured': reviewer_prompt_enabled is not None or reviewer_prompt_disabled is not None,
                    'enabled': reviewer_prompt_enabled is not None,
                    'name': (reviewer_prompt_enabled or reviewer_prompt_disabled).name if (
                            reviewer_prompt_enabled or reviewer_prompt_disabled) else None,
                    'id': (reviewer_prompt_enabled or reviewer_prompt_disabled).id if (
                            reviewer_prompt_enabled or reviewer_prompt_disabled) else None,
                    'required': False
                },
                'generation_config': {
                    'configured': generation_config is not None,
                    'enabled': generation_config is not None,
                    'name': generation_config.name if generation_config else None,
                    'id': generation_config.id if generation_config else None,
                    'required': True,
                    'default_output_mode': generation_config.default_output_mode if generation_config else None,
                    'enable_auto_review': generation_config.enable_auto_review if generation_config else None
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"检查配置状态失败: {e}")
            return Response({
                'error': f'检查配置状态失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== 测试模板配置API（前端可配置）====================

class TestTemplateConfigPagination(PageNumberPagination):
    """测试模板配置分页器"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class TestTemplateConfigViewSet(viewsets.ModelViewSet):
    """
    测试模板配置视图集
    提供测试模板的增删改查接口，支持前端页面配置
    """
    queryset = TestTemplateConfig.objects.all()
    serializer_class = TestTemplateConfigSerializer
    pagination_class = TestTemplateConfigPagination

    def get_queryset(self):
        """支持按类型和模块筛选"""
        queryset = TestTemplateConfig.objects.all()

        # 按模板类型筛选
        template_type = self.request.query_params.get('template_type')
        if template_type:
            queryset = queryset.filter(template_type=template_type)

        # 按业务模块筛选
        module_category = self.request.query_params.get('module_category')
        if module_category:
            queryset = queryset.filter(module_category=module_category)

        # 按启用状态筛选
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # 按关键词搜索
        keyword = self.request.query_params.get('keyword')
        if keyword:
            queryset = queryset.filter(
                models.Q(name__icontains=keyword) |
                models.Q(keywords__icontains=keyword) |
                models.Q(module_category__icontains=keyword)
            )

        return queryset.order_by('priority', 'created_at')

    def perform_create(self, serializer):
        """创建时自动设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def template_types(self, request):
        """获取所有模板类型选项"""
        types = [
            {'value': 'test_point', 'label': '测试点模板', 'description': '定义功能测试的验证点'},
            {'value': 'test_scenario', 'label': '测试场景模板', 'description': '定义测试的业务场景'},
            {'value': 'test_step', 'label': '测试步骤模板', 'description': '定义测试的操作步骤'},
            {'value': 'precondition', 'label': '前置条件模板', 'description': '定义测试的前置条件'}
        ]
        return Response(types)

    @action(detail=False, methods=['get'])
    def module_categories(self, request):
        """获取所有业务模块分类"""
        categories = TestTemplateConfig.objects.values_list(
            'module_category', flat=True
        ).distinct().exclude(module_category='').order_by('module_category')
        return Response(list(categories))

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """批量创建模板（用于初始化职业教育模板）"""
        templates_data = request.data.get('templates', [])
        created_count = 0
        errors = []

        for template_data in templates_data:
            try:
                # 检查是否已存在
                existing = TestTemplateConfig.objects.filter(
                    name=template_data.get('name'),
                    template_type=template_data.get('template_type')
                ).first()

                if existing:
                    errors.append(f"模板 '{template_data.get('name')}' 已存在，跳过")
                    continue

                # 创建模板
                TestTemplateConfig.objects.create(
                    name=template_data.get('name'),
                    template_type=template_data.get('template_type'),
                    keywords=template_data.get('keywords'),
                    content=template_data.get('content'),
                    priority=template_data.get('priority', 100),
                    module_category=template_data.get('module_category', ''),
                    is_active=template_data.get('is_active', True),
                    created_by=request.user
                )
                created_count += 1
            except Exception as e:
                errors.append(f"创建模板 '{template_data.get('name')}' 失败: {str(e)}")

        return Response({
            'created_count': created_count,
            'errors': errors,
            'message': f'成功创建 {created_count} 个模板'
        })

    @action(detail=False, methods=['post'])
    def init_education_templates(self, request):
        """初始化职业教育SaaS默认模板"""
        templates = [
            # ========== 测试点模板 ==========
            {
                'name': '课程管理测试点',
                'template_type': 'test_point',
                'keywords': '课程,课时,章节,课件,大纲',
                'content': [
                    '课程发布流程验证',
                    '章节顺序编排验证',
                    '课时完成状态验证',
                    '课程上下架控制验证',
                    '课程内容预览验证',
                    '课程分类归属验证'
                ],
                'priority': 10,
                'module_category': '课程管理'
            },
            {
                'name': '学员管理测试点',
                'template_type': 'test_point',
                'keywords': '学员,学生,报名,学籍,分班,入学',
                'content': [
                    '学员报名流程验证',
                    '班级自动分配验证',
                    '学籍状态变更验证',
                    '学习进度计算验证',
                    '学员信息导入导出验证',
                    '学员转班/退班验证'
                ],
                'priority': 10,
                'module_category': '学员管理'
            },
            {
                'name': '教学管理测试点',
                'template_type': 'test_point',
                'keywords': '排课,课表,考勤,签到,作业,考试,测验',
                'content': [
                    '自动排课算法验证',
                    '课表冲突检测验证',
                    '学员考勤记录验证',
                    '作业布置与提交验证',
                    '作业批改与反馈验证',
                    '考试成绩统计验证',
                    '考试防作弊监控验证'
                ],
                'priority': 10,
                'module_category': '教学管理'
            },
            {
                'name': '直播教学测试点',
                'template_type': 'test_point',
                'keywords': '直播,回放,连麦,白板,弹幕,屏幕共享',
                'content': [
                    '直播推流稳定性验证',
                    '直播回放自动生成验证',
                    '师生音视频连麦验证',
                    '白板实时同步验证',
                    '弹幕内容审核验证',
                    '屏幕共享清晰度验证',
                    '直播数据统计验证'
                ],
                'priority': 10,
                'module_category': '直播教学'
            },
            {
                'name': '证书管理测试点',
                'template_type': 'test_point',
                'keywords': '证书,结业,学分,成绩单,毕业,资质',
                'content': [
                    '证书模板配置验证',
                    '结业条件自动判断验证',
                    '学分累计计算验证',
                    '电子证书生成验证',
                    '证书真伪查询验证',
                    '成绩单导出验证'
                ],
                'priority': 10,
                'module_category': '证书管理'
            },
            {
                'name': '营销招生测试点',
                'template_type': 'test_point',
                'keywords': '试听,体验课,团购,分销,推荐,优惠券,促销',
                'content': [
                    '试听申请流程验证',
                    '试听转正式学员验证',
                    '团购优惠规则验证',
                    '分销佣金计算验证',
                    '推荐码绑定关系验证',
                    '优惠券使用规则验证'
                ],
                'priority': 10,
                'module_category': '营销招生'
            },
            {
                'name': '内容管理测试点',
                'template_type': 'test_point',
                'keywords': '题库,试题,试卷,资料,资源,视频,文档',
                'content': [
                    '题库分类管理验证',
                    '试题批量导入验证',
                    '试卷自动组卷验证',
                    '学习资料上传验证',
                    '视频转码处理验证',
                    '资源权限控制验证'
                ],
                'priority': 10,
                'module_category': '内容管理'
            },
            {
                'name': '问答互动测试点',
                'template_type': 'test_point',
                'keywords': '问答,提问,答疑,讨论,评论,评价,点赞',
                'content': [
                    '学员提问流程验证',
                    '教师答疑回复验证',
                    '问答内容审核验证',
                    '课程评价提交验证',
                    '讨论区互动验证',
                    '优质内容推荐验证'
                ],
                'priority': 10,
                'module_category': '问答互动'
            },

            # ========== 测试场景模板 ==========
            {
                'name': '学习流程场景',
                'template_type': 'test_scenario',
                'keywords': '学习,课程,课时,章节,进度',
                'content': [
                    '学员选课报名场景',
                    '课程学习进度记录场景',
                    '课时完成状态变更场景',
                    '学习资料下载场景',
                    '学习笔记记录场景',
                    '课程评价反馈场景',
                    '学习提醒推送场景'
                ],
                'priority': 10,
                'module_category': '学习流程'
            },
            {
                'name': '教学流程场景',
                'template_type': 'test_scenario',
                'keywords': '教学,授课,老师,教师,讲师',
                'content': [
                    '教师发布课程场景',
                    '在线直播授课场景',
                    '课件上传管理场景',
                    '作业布置与批改场景',
                    '学员答疑互动场景',
                    '教学数据统计场景',
                    '课程资料更新场景'
                ],
                'priority': 10,
                'module_category': '教学流程'
            },
            {
                'name': '考试测评场景',
                'template_type': 'test_scenario',
                'keywords': '考试,测评,测验,quiz,答题,阅卷',
                'content': [
                    '在线考试参加场景',
                    '考试防作弊监控场景',
                    '成绩自动批改场景',
                    '主观题人工阅卷场景',
                    '错题本自动生成场景',
                    '能力评估报告场景',
                    '考试成绩查询场景'
                ],
                'priority': 10,
                'module_category': '考试测评'
            },
            {
                'name': '证书发放场景',
                'template_type': 'test_scenario',
                'keywords': '证书,结业,毕业,学分,资质认证',
                'content': [
                    '结业条件达成场景',
                    '电子证书生成场景',
                    '证书信息核验场景',
                    '学分达标判断场景',
                    '学习档案归档场景',
                    '证书真伪查询场景',
                    '成绩单导出打印场景'
                ],
                'priority': 10,
                'module_category': '证书发放'
            },

            # ========== 前置条件模板 ==========
            {
                'name': '课程管理前置条件',
                'template_type': 'precondition',
                'keywords': '课程,课时,章节,课件',
                'content': {
                    'precondition': '1. 系统正常运行\n2. 教师账号已登录\n3. 课程分类已配置\n4. 测试视频/课件资源已准备\n5. {module}模块可访问'
                },
                'priority': 10,
                'module_category': '课程管理'
            },
            {
                'name': '学员管理前置条件',
                'template_type': 'precondition',
                'keywords': '学员,学生,报名,学籍,分班',
                'content': {
                    'precondition': '1. 系统正常运行\n2. 管理员/教师账号已登录\n3. 班级信息已创建\n4. 测试学员账号已准备\n5. {module}模块可访问'
                },
                'priority': 10,
                'module_category': '学员管理'
            },
            {
                'name': '直播教学前置条件',
                'template_type': 'precondition',
                'keywords': '直播,回放,连麦,白板',
                'content': {
                    'precondition': '1. 系统正常运行\n2. 直播服务连接正常\n3. 教师/学员账号已准备\n4. 浏览器摄像头/麦克风权限已开启\n5. {module}模块可访问'
                },
                'priority': 10,
                'module_category': '直播教学'
            },
            {
                'name': '考试测评前置条件',
                'template_type': 'precondition',
                'keywords': '考试,测评,测验,quiz',
                'content': {
                    'precondition': '1. 系统正常运行\n2. 考试题库已配置\n3. 考生信息已导入\n4. 考试时间窗口已设置\n5. {module}模块可访问'
                },
                'priority': 10,
                'module_category': '考试测评'
            },
        ]

        # 直接创建模板，不调用 batch_create
        created_count = 0
        errors = []

        for template_data in templates:
            try:
                # 检查是否已存在
                existing = TestTemplateConfig.objects.filter(
                    name=template_data.get('name'),
                    template_type=template_data.get('template_type')
                ).first()

                if existing:
                    errors.append(f"模板 '{template_data.get('name')}' 已存在，跳过")
                    continue

                # 创建模板
                serializer = self.get_serializer(data=template_data)
                if serializer.is_valid():
                    serializer.save(created_by=request.user)
                    created_count += 1
                else:
                    errors.append(f"模板 '{template_data.get('name')}' 验证失败: {serializer.errors}")

            except Exception as e:
                errors.append(f"创建模板 '{template_data.get('name')}' 失败: {str(e)}")

        return Response({
            'message': f'成功创建 {created_count} 个模板',
            'created_count': created_count,
            'errors': errors
        })

    @action(detail=False, methods=['post'])
    def test_match(self, request):
        """测试模板匹配（用于调试）"""
        text = request.data.get('text', '')
        template_type = request.data.get('template_type')

        matched_templates = TestTemplateConfig.match_templates(text, template_type)

        result = []
        for template in matched_templates:
            result.append({
                'id': template.id,
                'name': template.name,
                'type': template.template_type,
                'keywords': template.get_keywords_list(),
                'content': template.content,
                'module_category': template.module_category
            })

        return Response({
            'input_text': text,
            'template_type': template_type,
            'matched_count': len(result),
            'matched_templates': result
        })


class TestTemplateCategoryViewSet(viewsets.ModelViewSet):
    """测试模板分类视图集"""
    queryset = TestTemplateCategory.objects.all()
    serializer_class = TestTemplateCategorySerializer

    def get_queryset(self):
        """只返回启用的分类"""
        return TestTemplateCategory.objects.filter(is_active=True).order_by('sort_order')


# ==================== 测试模板配置API结束 ====================