import os
import json
import time
import uuid
import asyncio
import logging
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime

# docling 文档解析支持 - 统一使用 docling 处理所有格式
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.document import ConversionResult
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None

from django.conf import settings
from django.core.files.storage import default_storage

from .models import RequirementDocument, RequirementAnalysis, BusinessRequirement, GeneratedTestCase, AnalysisTask

logger = logging.getLogger(__name__)


class ImageFlowchartProcessor:
    """图片流程图解析服务 - 使用多模态 AI 理解流程图"""

    @staticmethod
    def is_image_file(file_path: str) -> bool:
        """检查是否为图片文件"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        ext = os.path.splitext(file_path.lower())[1]
        return ext in image_extensions

    @staticmethod
    def encode_image_to_base64(file_path: str) -> str:
        """将图片转换为 base64 编码"""
        with open(file_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @staticmethod
    async def analyze_flowchart_with_vision(file_path: str, config: Optional[Any] = None) -> str:
        """
        使用多模态 AI 分析流程图图片

        Args:
            file_path: 图片文件路径
            config: AI 模型配置（已废弃，自动使用 qwen-vl-plus）

        Returns:
            结构化文本描述
        """
        try:
            logger.info(f"开始分析图片流程图: {file_path}")

            # 获取图片 base64
            base64_image = ImageFlowchartProcessor.encode_image_to_base64(file_path)
            logger.info(f"图片已转换为 base64，长度: {len(base64_image)}")

            # 自动使用 qwen-vl-plus，不需要配置
            logger.info("自动使用 qwen-vl-plus 分析图片")

            # 获取 API Key（从环境变量或默认配置）
            api_key = os.environ.get('DASHSCOPE_API_KEY') or os.environ.get('OPENAI_API_KEY')
            if not api_key:
                # 尝试从 AIModelConfig 获取任意可用的 API Key
                from .models import AIModelConfig
                any_config = AIModelConfig.objects.filter(is_active=True).first()
                if any_config:
                    api_key = any_config.api_key

            if not api_key:
                logger.error("未找到可用的 API Key")
                return "错误：未找到可用的 API Key，请配置 AI 模型"

            # 构建提示词
            system_prompt = """你是一个专业的流程图分析专家。请仔细分析用户上传的流程图图片，并提取以下信息：

1. **流程节点**：识别图中的所有节点（方框、菱形、圆形等），包括：
   - 节点名称/标签
   - 节点类型（开始/结束、处理、判断、输入/输出等）
   - 节点描述

2. **流程关系**：识别节点之间的连接关系，包括：
   - 源节点 → 目标节点
   - 连接条件（如判断分支的"是"/"否"）
   - 流程方向

3. **整体结构**：
   - 流程的起点和终点
   - 主流程路径
   - 分支和循环
   - 并行流程（如果有）

请以结构化的方式输出，使用以下格式：

## 流程概述
[简要描述这个流程的整体功能和目的]

## 节点列表
1. **节点名称** (类型: [开始/结束/处理/判断/输入/输出])
   - 描述: [详细说明]

2. **节点名称** (类型: [开始/结束/处理/判断/输入/输出])
   - 描述: [详细说明]

## 流程关系
- [节点A] → [节点B] ([条件/说明])
- [节点B] → [节点C] ([条件/说明])

## 主流程路径
[描述从起点到终点的主要流程路径]

## 分支和循环
[描述所有的分支判断和循环结构]

请确保：
- 使用图片中显示的实际文本内容
- 保持原始语言（如果是中文图片，输出中文）
- 尽可能详细和准确
- 对于无法识别的内容，标注为"未识别"""

            # 调用 qwen-vl-plus 多模态 API（硬编码，不依赖配置）
            logger.info("开始调用 qwen-vl-plus 多模态 API")
            result = await ImageFlowchartProcessor._call_qwen_vision_with_key(
                api_key, base64_image, system_prompt
            )

            logger.info(f"流程图分析完成，结果长度: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"流程图分析失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return f"流程图分析失败: {str(e)}"

    @staticmethod
    async def _call_qwen_vision_with_key(api_key: str, base64_image: str, system_prompt: str) -> str:
        """调用通义千问多模态 API（直接使用 API Key，硬编码使用 qwen-vl-plus）"""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "qwen-vl-plus",  # 硬编码使用 qwen-vl-plus
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请详细分析这张流程图，提取所有节点和关系。"
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.7
        }

        async with aiohttp.ClientSession() as session:
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            logger.info(f"调用通义千问 qwen-vl-plus API: {url}")
            async with session.post(
                url,
                headers=headers,
                json=payload
            ) as response:
                response_text = await response.text()
                logger.info(f"API 响应状态: {response.status}")
                if response.status == 200:
                    result = json.loads(response_text)
                    content = result['choices'][0]['message']['content']
                    logger.info(f"API 调用成功，返回内容长度: {len(content)}")
                    return content
                else:
                    logger.error(f"API 调用失败: {response.status}, {response_text}")
                    raise Exception(f"API 调用失败: {response.status}, {response_text}")

    @staticmethod
    async def _call_qwen_vision(config, base64_image: str, system_prompt: str) -> str:
        """调用通义千问多模态 API（兼容旧版本，使用配置对象）"""
        return await ImageFlowchartProcessor._call_qwen_vision_with_key(
            config.api_key, base64_image, system_prompt
        )

    @staticmethod
    async def _call_deepseek_vision(config, base64_image: str, system_prompt: str) -> str:
        """调用 DeepSeek 多模态 API"""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": config.model_name or "deepseek-vl",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请详细分析这张流程图，提取所有节点和关系。"
                        }
                    ]
                }
            ],
            "max_tokens": config.max_tokens or 4096,
            "temperature": config.temperature or 0.7
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                config.base_url or "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    raise Exception(f"API 调用失败: {response.status}, {error_text}")

    @staticmethod
    async def _call_zhipu_vision(config, base64_image: str, system_prompt: str) -> str:
        """调用智谱 GLM-4V API"""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": config.model_name or "glm-4v",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请详细分析这张流程图，提取所有节点和关系。"
                        }
                    ]
                }
            ],
            "max_tokens": config.max_tokens or 4096,
            "temperature": config.temperature or 0.7
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                config.base_url or "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    raise Exception(f"API 调用失败: {response.status}, {error_text}")

    @staticmethod
    async def _call_openai_vision(config, base64_image: str, system_prompt: str) -> str:
        """调用 OpenAI 兼容接口的多模态 API"""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": config.model_name or "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请详细分析这张流程图，提取所有节点和关系。"
                        }
                    ]
                }
            ],
            "max_tokens": config.max_tokens or 4096,
            "temperature": config.temperature or 0.7
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    raise Exception(f"API 调用失败: {response.status}, {error_text}")


class DocumentProcessor:
    """文档处理服务 - 统一使用 docling 解析所有格式，图片使用多模态 AI"""

    @staticmethod
    def extract_text_with_docling(file_path: str) -> str:
        """使用 docling 提取文档文本（支持多种格式）"""
        if not DOCLING_AVAILABLE:
            return "docling 未安装，无法解析此格式"

        try:
            converter = DocumentConverter()
            result = converter.convert(file_path)

            if result.status.value == 'success':
                # 导出为 markdown 格式文本，保留表格结构
                text = result.document.export_to_markdown()
                return text.strip()
            else:
                return f"文档解析失败: {result.status.value}"
        except Exception as e:
            logger.error(f"docling 文档解析失败: {e}")
            return f"文档解析失败: {str(e)}"

    @classmethod
    def extract_text(cls, document: RequirementDocument) -> str:
        """根据文档类型提取文本 - 图片使用多模态 AI，其他使用 docling"""
        file_path = document.file.path
        logger.info(f"DocumentProcessor.extract_text 被调用: {file_path}")

        # 检查是否为图片文件
        is_image = ImageFlowchartProcessor.is_image_file(file_path)
        logger.info(f"是否为图片文件: {is_image}, 扩展名: {os.path.splitext(file_path.lower())[1]}")

        if is_image:
            logger.info(f"检测到图片文件: {file_path}，将使用多模态 AI 分析流程图")
            # 图片文件返回特殊标记，由调用方异步处理
            return "__IMAGE_FLOWCHART__"

        # 非图片文件使用 docling 解析
        if not DOCLING_AVAILABLE:
            return "docling 未安装，无法解析文档"

        return cls.extract_text_with_docling(file_path)

    @classmethod
    async def extract_text_async(cls, document: RequirementDocument, config: Optional[Any] = None) -> str:
        """异步提取文档文本 - 图片使用多模态 AI 分析"""
        file_path = document.file.path

        # 检查是否为图片文件
        if ImageFlowchartProcessor.is_image_file(file_path):
            logger.info(f"使用多模态 AI 分析图片流程图: {file_path}")
            return await ImageFlowchartProcessor.analyze_flowchart_with_vision(file_path, config)

        # 非图片文件使用 docling 解析
        if not DOCLING_AVAILABLE:
            return "docling 未安装，无法解析文档"

        return cls.extract_text_with_docling(file_path)


class AIService:
    """AI服务类 - 模拟大模型调用"""
    
    @staticmethod
    async def analyze_requirements(text: str, document_title: str = "") -> Dict[str, Any]:
        """
        先进的需求分析 - 使用新的智能分析引擎
        
        Args:
            text: 需求文档文本内容
            document_title: 文档标题
            
        Returns:
            Dict包含分析报告、结构化需求等信息
        """
        try:
            # 直接导入并使用先进分析器
            from apps.requirement_analysis.advanced_analyzer import advanced_analyzer
            
            logger.info(f"使用先进分析器分析需求，文档标题: {document_title}")
            
            # 使用先进分析器进行分析
            result = await advanced_analyzer.analyze_requirements_advanced(text, document_title)
            
            # 转换为原系统期望的格式
            analysis_report = result.get("analysis_report", "")
            structured_requirements = result.get("structured_requirements", {})
            requirements_list = structured_requirements.get("requirements", [])
            
            # 计算分析时间（模拟）
            import time
            analysis_time = time.time() % 10 + 2  # 2-12秒之间的模拟时间
            
            logger.info(f"先进需求分析完成，识别需求{len(requirements_list)}个")
            
            return {
                "analysis_report": analysis_report,
                "requirements": requirements_list,
                "requirements_count": len(requirements_list),
                "analysis_time": analysis_time,
                "quality_assessment": result.get("quality_assessment", {}),
                "risk_analysis": result.get("risk_analysis", {})
            }
            
        except Exception as e:
            logger.error(f"先进需求分析失败: {e}")
            logger.info("使用备用分析方法")
            # fallback到原来的分析逻辑
            return await AIService._fallback_analyze_requirements(text, document_title)
    
    @staticmethod
    async def _fallback_analyze_requirements(text: str, document_title: str = "") -> Dict[str, Any]:
        """备用需求分析方法"""
        # 模拟AI分析过程
        await asyncio.sleep(2)
        
        # 这里应该调用真实的大模型API
        # 现在返回改进的模拟数据
        analysis_report = f"""
# 需求分析报告

## 文档概述
基于提供的需求文档"{document_title}"，共识别出以下主要需求模块和功能点。

## 主要功能模块
1. 用户管理模块
2. 数据处理模块  
3. 报告生成模块
4. 系统配置模块

## 详细需求分析
基于文档内容分析，识别出以下具体需求：

### 功能需求
- 用户认证和权限管理
- 数据录入和维护功能
- 业务流程处理
- 报表和统计功能

### 非功能需求
- 系统性能要求：响应时间 < 3秒
- 安全性要求：数据加密存储
- 可用性要求：99.5%系统可用率
- 兼容性要求：支持主流浏览器

## 风险评估
- 技术实现风险：中等
- 进度风险：低
- 资源风险：低

## 建议
建议采用敏捷开发模式，分阶段实施各功能模块。

分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # 生成基础的结构化需求
        requirements = [
            {
                "requirement_id": "REQ-001",
                "requirement_name": "用户认证管理", 
                "requirement_type": "functional",
                "parent_requirement": None,
                "module": "用户管理",
                "requirement_level": "high",
                "reviewer": "admin",
                "estimated_hours": 16,
                "description": "作为一名系统用户，我希望通过用户名和密码登录系统，这样可以确保系统安全性并获得个性化服务。",
                "acceptance_criteria": "用户能够使用有效凭证成功登录系统，无效凭证登录失败，系统记录登录日志。"
            },
            {
                "requirement_id": "REQ-002",
                "requirement_name": "数据管理功能",
                "requirement_type": "functional", 
                "parent_requirement": None,
                "module": "数据管理",
                "requirement_level": "high",
                "reviewer": "admin",
                "estimated_hours": 24,
                "description": "作为一名数据操作员，我希望能够对系统数据进行增删改查操作，这样可以有效管理业务信息。",
                "acceptance_criteria": "数据操作功能正常，数据完整性得到保证，操作权限控制有效。"
            },
            {
                "requirement_id": "REQ-003",
                "requirement_name": "报表统计功能",
                "requirement_type": "functional",
                "parent_requirement": None,
                "module": "报表管理",
                "requirement_level": "medium", 
                "reviewer": "admin",
                "estimated_hours": 20,
                "description": "作为一名管理人员，我希望能够生成各类业务报表和统计图表，这样可以直观了解业务数据和趋势。",
                "acceptance_criteria": "系统能够生成多种格式的报表，数据准确，支持导出功能。"
            }
        ]
        
        return {
            "analysis_report": analysis_report,
            "requirements": requirements,
            "requirements_count": len(requirements)
        }
    
    @staticmethod
    async def generate_test_cases(requirement: BusinessRequirement, test_level: str, test_priority: str, count: int) -> List[Dict[str, Any]]:
        """生成测试用例 - 大模型A"""
        # 模拟AI生成过程
        await asyncio.sleep(1)
        
        # 生成唯一case_id的辅助函数
        def generate_unique_case_id(req, base_index):
            """生成唯一的测试用例ID"""
            base_case_id = f"TC-{req.requirement_id}-{base_index:03d}"
            case_id = base_case_id
            counter = 1
            
            # 检查是否已存在，如果存在则添加后缀
            from .models import GeneratedTestCase
            while GeneratedTestCase.objects.filter(requirement=req, case_id=case_id).exists():
                case_id = f"{base_case_id}_{counter}"
                counter += 1
            
            return case_id
        
        # 获取该需求现有测试用例的数量，作为起始索引
        from .models import GeneratedTestCase
        existing_count = GeneratedTestCase.objects.filter(requirement=requirement).count()
        
        # 根据需求生成测试用例
        test_cases = []
        for i in range(count):
            case_id = generate_unique_case_id(requirement, existing_count + i + 1)
            
            # 根据需求类型生成不同的测试用例
            if "登录" in requirement.requirement_name:
                test_cases.append({
                    "case_id": case_id,
                    "title": f"验证用户使用有效凭证登录系统的认证流程和权限获取",
                    "priority": test_priority,
                    "precondition": "系统正常运行，测试用户账号已创建",
                    "test_steps": "1. 打开登录页面\n2. 输入有效的用户名和密码\n3. 点击登录按钮\n4. 检查登录结果和页面跳转",
                    "expected_result": "用户成功登录系统，跳转到主页面，显示用户信息和相应权限功能"
                })
            elif "数据" in requirement.requirement_name:
                test_cases.append({
                    "case_id": case_id,
                    "title": f"测试数据录入功能在各种输入场景下的验证机制和保存结果",
                    "priority": test_priority,
                    "precondition": "系统正常运行，用户已登录具备数据操作权限",
                    "test_steps": "1. 进入数据录入页面\n2. 填写必填字段信息\n3. 提交数据\n4. 验证数据保存结果",
                    "expected_result": "数据成功保存到数据库，页面显示保存成功提示，可以查询到新录入的数据"
                })
            elif "报告" in requirement.requirement_name:
                test_cases.append({
                    "case_id": case_id,
                    "title": f"验证报告生成功能在不同格式和数据量下的处理能力和输出质量",
                    "priority": test_priority, 
                    "precondition": "系统正常运行，存在可用于生成报告的数据",
                    "test_steps": "1. 进入报告生成页面\n2. 选择报告类型和参数\n3. 点击生成报告\n4. 检查生成的报告内容和格式",
                    "expected_result": "报告成功生成，内容准确完整，格式符合要求，可以正常下载"
                })
            else:
                test_cases.append({
                    "case_id": case_id,
                    "title": f"验证{requirement.requirement_name}功能的基本操作流程和预期结果",
                    "priority": test_priority,
                    "precondition": "系统正常运行，用户已登录",
                    "test_steps": f"1. 访问{requirement.requirement_name}功能\n2. 执行主要操作步骤\n3. 验证操作结果",
                    "expected_result": f"{requirement.requirement_name}功能正常工作，操作结果符合预期"
                })
        
        return test_cases
    
    @staticmethod
    async def review_test_cases(test_cases: List[GeneratedTestCase], review_criteria: str) -> Dict[str, Any]:
        """评审测试用例 - 大模型B"""
        # 模拟AI评审过程
        await asyncio.sleep(1.5)
        
        reviewed_cases = []
        for test_case in test_cases:
            # 模拟评审逻辑
            review_score = 85  # 模拟评分
            
            review_comments = f"""
评审意见:
1. 测试用例标题清晰明确，能够准确描述测试目的
2. 测试步骤详细具体，具有良好的可执行性
3. 预期结果明确，便于验证
4. 建议补充异常场景的测试覆盖

评审分数: {review_score}/100
评审状态: 通过
"""
            
            reviewed_cases.append({
                "test_case_id": test_case.id,
                "review_score": review_score,
                "review_comments": review_comments.strip(),
                "status": "reviewed" if review_score >= 80 else "rejected"
            })
        
        return {
            "reviewed_cases": reviewed_cases,
            "overall_score": sum(case["review_score"] for case in reviewed_cases) / len(reviewed_cases),
            "pass_rate": len([case for case in reviewed_cases if case["status"] == "reviewed"]) / len(reviewed_cases) * 100
        }


class RequirementAnalysisService:
    """需求分析服务"""
    
    @classmethod
    def create_analysis_task(cls, document: RequirementDocument, task_type: str) -> AnalysisTask:
        """创建分析任务"""
        task_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        
        task = AnalysisTask.objects.create(
            task_id=task_id,
            task_type=task_type,
            document=document,
            status='pending'
        )
        
        return task
    
    @classmethod
    async def process_document_analysis(cls, document: RequirementDocument) -> RequirementAnalysis:
        """处理文档分析"""
        # 创建分析任务
        task = cls.create_analysis_task(document, 'requirement_analysis')
        
        try:
            # 更新任务状态
            task.status = 'running'
            task.started_at = datetime.now()
            task.progress = 10
            task.save()
            
            # 提取文档文本
            if not document.extracted_text:
                document.extracted_text = DocumentProcessor.extract_text(document)
                document.save()
            
            task.progress = 30
            task.save()
            
            # 调用AI分析
            start_time = time.time()
            analysis_result = await AIService.analyze_requirements(
                document.extracted_text, 
                document.title
            )
            analysis_time = time.time() - start_time
            
            task.progress = 70
            task.save()
            
            # 创建分析记录
            analysis = RequirementAnalysis.objects.create(
                document=document,
                analysis_report=analysis_result['analysis_report'],
                requirements_count=analysis_result['requirements_count'],
                analysis_time=analysis_time
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
            
            # 完成任务
            task.status = 'completed'
            task.completed_at = datetime.now()
            task.progress = 100
            task.result = analysis_result
            task.save()
            
            return analysis
            
        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            
            # 更新任务状态
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.now()
            task.save()
            
            # 更新文档状态
            document.status = 'failed'
            document.save()
            
            raise e
    
    @classmethod
    async def generate_test_cases_for_requirements(cls, requirement_ids: List[int], test_level: str, test_priority: str, test_case_count: int) -> List[GeneratedTestCase]:
        """为需求生成测试用例"""
        generated_cases = []
        
        for req_id in requirement_ids:
            try:
                requirement = BusinessRequirement.objects.get(id=req_id)
                
                # 调用AI生成测试用例
                test_cases_data = await AIService.generate_test_cases(
                    requirement, test_level, test_priority, test_case_count
                )
                
                # 保存生成的测试用例
                for case_data in test_cases_data:
                    test_case = GeneratedTestCase.objects.create(
                        requirement=requirement,
                        case_id=case_data['case_id'],
                        title=case_data['title'],
                        priority=case_data['priority'],
                        precondition=case_data['precondition'],
                        test_steps=case_data['test_steps'],
                        expected_result=case_data['expected_result'],
                        generated_by_ai='AI-A'
                    )
                    generated_cases.append(test_case)
                    
            except BusinessRequirement.DoesNotExist:
                logger.error(f"需求ID {req_id} 不存在")
                continue
            except Exception as e:
                logger.error(f"为需求 {req_id} 生成测试用例失败: {e}")
                continue
        
        return generated_cases
    
    @classmethod
    async def review_test_cases(cls, test_case_ids: List[int], review_criteria: str) -> Dict[str, Any]:
        """评审测试用例"""
        test_cases = GeneratedTestCase.objects.filter(id__in=test_case_ids)
        
        # 调用AI评审
        review_result = await AIService.review_test_cases(list(test_cases), review_criteria)
        
        # 更新测试用例状态
        for case_review in review_result['reviewed_cases']:
            try:
                test_case = GeneratedTestCase.objects.get(id=case_review['test_case_id'])
                test_case.status = case_review['status']
                test_case.review_comments = case_review['review_comments']
                test_case.reviewed_by_ai = 'AI-B'
                test_case.save()
            except GeneratedTestCase.DoesNotExist:
                logger.error(f"测试用例ID {case_review['test_case_id']} 不存在")
                continue
        
        return review_result