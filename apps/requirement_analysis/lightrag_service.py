"""
LightRAG Service 封装层
将 LightRAG 功能集成到 TestHub 平台
"""
import os
import asyncio
import logging
import json
import queue
from typing import List, Dict, Any, Optional
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async
from concurrent.futures import ThreadPoolExecutor
import numpy as np

logger = logging.getLogger(__name__)

# LightRAG 相关导入
try:
    from lightrag import LightRAG, QueryParam
    from lightrag.llm.openai import openai_complete_if_cache
    from lightrag.utils import EmbeddingFunc
    from lightrag.prompt import PROMPTS
    LIGHT_RAG_AVAILABLE = True
    
    # 自定义实体提取提示词 - 明确要求保留原文语言
    PROMPTS["entity_extraction_system_prompt"] = """---Role---
You are a Knowledge Graph Specialist responsible for extracting entities and relationships from the input text.

----Instructions---
1.  **Entity Extraction & Output:**
    *   **Identification:** Identify clearly defined and meaningful entities in the input text.
    *   **Entity Details:** For each identified entity, extract the following information:
        *   `entity_name`: The name of the entity. **CRITICAL: You MUST use the EXACT text from the input document. DO NOT translate to English. If the document is in Chinese, use Chinese entity names.**
        *   `entity_type`: Categorize the entity using one of the following types: `{entity_types}`. If none of the provided entity types apply, classify it as `Other`.
        *   `entity_description`: Provide a concise yet comprehensive description of the entity's attributes and activities, based *solely* on the information present in the input text. **Use the same language as the input document.**
    *   **Output Format - Entities:** Output a total of 4 fields for each entity, delimited by `{tuple_delimiter}`, on a single line. The first field *must* be the literal string `entity`.
        *   Format: `entity{tuple_delimiter}entity_name{tuple_delimiter}entity_type{tuple_delimiter}entity_description`

2.  **Relationship Extraction & Output:**
    *   **Identification:** Identify direct, clearly stated, and meaningful relationships between previously extracted entities.
    *   **N-ary Relationship Decomposition:** If a single statement describes a relationship involving more than two entities, decompose it into multiple binary relationship pairs.
    *   **Relationship Details:** For each binary relationship, extract the following fields:
        *   `source_entity`: The name of the source entity. **Use the EXACT entity name as extracted, DO NOT translate.**
        *   `target_entity`: The name of the target entity. **Use the EXACT entity name as extracted, DO NOT translate.**
        *   `relationship_keywords`: One or more high-level keywords summarizing the relationship. **Use the same language as the input document.**
        *   `relationship_description`: A concise explanation of the relationship. **Use the same language as the input document.**
    *   **Output Format - Relationships:** Output a total of 5 fields for each relationship, delimited by `{tuple_delimiter}`, on a single line.
        *   Format: `relation{tuple_delimiter}source_entity{tuple_delimiter}target_entity{tuple_delimiter}relationship_keywords{tuple_delimiter}relationship_description`

3.  **Language Requirements:**
    *   **CRITICAL: The entire output (entity names, keywords, and descriptions) must be written in the SAME LANGUAGE as the input text (`{language}`).**
    *   **DO NOT translate entity names to English.**
    *   **DO NOT translate relationship keywords to English.**
    *   **If the input is Chinese, ALL output must be in Chinese.**
    *   Proper nouns (e.g., personal names, place names, organization names) should be retained in their original form.

4.  **Completion Signal:** Output the literal string `{completion_delimiter}` only after all entities and relationships have been completely extracted.

----Examples---
{examples}
"""
    
    logger.info("已加载自定义实体提取提示词，要求保留原文语言")
    
except ImportError:
    LIGHT_RAG_AVAILABLE = False
    logger.warning("LightRAG 未安装，知识图谱功能将不可用")


# 实体名称映射管理器
class EntityMappingManager:
    """实体名称映射管理器 - 从 JSON 配置文件加载映射"""
    
    _instance = None
    _mappings = {}
    _config_path = None
    _last_modified = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        if self._config_path is None:
            # 从 settings 获取基础路径
            base_dir = Path(settings.BASE_DIR)
            self._config_path = base_dir / 'config' / 'entity_mapping.json'
        return self._config_path
    
    def _load_config(self):
        """加载配置文件"""
        config_path = self._get_config_path()
        
        if not config_path.exists():
            logger.warning(f"实体映射配置文件不存在: {config_path}")
            self._mappings = {}
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self._mappings = config.get('mappings', {})
                self._last_modified = config_path.stat().st_mtime
                logger.info(f"已加载 {len(self._mappings)} 个实体名称映射")
        except Exception as e:
            logger.error(f"加载实体映射配置文件失败: {e}")
            self._mappings = {}
    
    def _check_reload(self):
        """检查配置文件是否已修改，如果是则重新加载"""
        config_path = self._get_config_path()
        if config_path.exists():
            current_modified = config_path.stat().st_mtime
            if current_modified > self._last_modified:
                logger.info("实体映射配置文件已修改，重新加载")
                self._load_config()
    
    def get_mapping(self, name: str) -> str:
        """
        获取实体名称的映射
        
        Args:
            name: 实体名称
            
        Returns:
            映射后的名称，如果没有映射则返回原名称
        """
        self._check_reload()
        return self._mappings.get(name, name)
    
    def get_all_mappings(self) -> Dict[str, str]:
        """获取所有映射"""
        self._check_reload()
        return self._mappings.copy()
    
    def add_mapping(self, english: str, chinese: str, save: bool = True):
        """
        添加新的映射
        
        Args:
            english: 英文实体名称
            chinese: 中文实体名称
            save: 是否保存到配置文件
        """
        self._mappings[english] = chinese
        logger.info(f"添加实体映射: {english} -> {chinese}")
        
        if save:
            self._save_config()
    
    def remove_mapping(self, english: str, save: bool = True):
        """
        删除映射
        
        Args:
            english: 英文实体名称
            save: 是否保存到配置文件
        """
        if english in self._mappings:
            del self._mappings[english]
            logger.info(f"删除实体映射: {english}")
            
            if save:
                self._save_config()
    
    def _save_config(self):
        """保存配置到文件"""
        config_path = self._get_config_path()
        
        try:
            config = {
                "_description": "实体名称映射配置 - 将英文实体名称映射为中文",
                "_comment": "键为英文实体名称，值为对应的中文翻译",
                "mappings": self._mappings
            }
            
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self._last_modified = config_path.stat().st_mtime
            logger.info(f"实体映射配置已保存到: {config_path}")
        except Exception as e:
            logger.error(f"保存实体映射配置文件失败: {e}")


# 全局映射管理器实例
_mapping_manager = None


def get_mapping_manager() -> EntityMappingManager:
    """获取实体映射管理器实例（单例模式）"""
    global _mapping_manager
    if _mapping_manager is None:
        _mapping_manager = EntityMappingManager()
    return _mapping_manager


# 自动翻译器
class EntityTranslator:
    """实体名称自动翻译器"""
    
    _cache = {}  # 翻译缓存
    
    @classmethod
    def translate(cls, text: str) -> str:
        """
        将英文文本翻译成中文
        
        Args:
            text: 英文文本
            
        Returns:
            中文翻译结果
        """
        # 检查缓存
        if text in cls._cache:
            return cls._cache[text]
        
        # 如果文本包含中文，直接返回
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            return text
        
        try:
            # 尝试使用 LLM 进行翻译（免费方案）
            translated = cls._translate_with_llm(text)
            if translated:
                cls._cache[text] = translated
                # 同时保存到配置文件
                manager = get_mapping_manager()
                manager.add_mapping(text, translated)
                return translated
        except Exception as e:
            logger.warning(f"LLM 翻译失败: {e}")
        
        # 如果翻译失败，返回原文
        return text
    
    @classmethod
    def _translate_with_llm(cls, text: str) -> str:
        """使用 LLM 进行翻译"""
        try:
            import openai

            # 获取配置
            config = LightRAGConfig
            api_key = config.get_api_key()

            if not api_key:
                logger.warning("没有配置 API Key，无法使用 LLM 翻译")
                return None

            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=config.DASHSCOPE_BASE_URL,
            )

            # 构建翻译提示
            prompt = f"""请将以下英文术语翻译成简洁的中文，只返回翻译结果，不要解释：

英文：{text}

中文："""

            # 使用同步方式调用
            import asyncio
            response = asyncio.run(client.chat.completions.create(
                model=config.QWEN_LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的翻译助手，擅长将技术术语翻译成简洁准确的中文。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.1
            ))

            translated = response.choices[0].message.content.strip()
            logger.info(f"LLM 翻译: {text} -> {translated}")
            return translated

        except Exception as e:
            logger.error(f"LLM 翻译失败: {e}")
            return None

    @classmethod
    def _is_english_text(cls, text: str) -> bool:
        """
        检测文本是否包含英文内容

        Args:
            text: 待检测文本

        Returns:
            如果包含英文单词则返回 True
        """
        if not text:
            return False

        # 如果文本中包含中文字符比例较高，认为是中文
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len([c for c in text if c.isalpha()])

        if total_chars == 0:
            return False

        # 如果中文字符占比超过 30%，认为是中文文本
        if chinese_chars / total_chars > 0.3:
            return False

        # 检测是否包含英文单词（简单的启发式方法）
        import re
        # 查找英文单词（连续的英文字母）
        english_words = re.findall(r'[a-zA-Z]{3,}', text)
        return len(english_words) > 0

    @classmethod
    async def translate_description_async(cls, description: str) -> str:
        """
        将英文描述翻译成中文（异步版本）

        Args:
            description: 英文描述

        Returns:
            中文翻译结果
        """
        if not description:
            return description

        # 检查缓存
        cache_key = f"desc:{hash(description) % 1000000}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        try:
            import openai

            # 获取配置
            config = LightRAGConfig
            api_key = config.get_api_key()

            if not api_key:
                logger.warning("没有配置 API Key，无法使用 LLM 翻译")
                return description

            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=config.DASHSCOPE_BASE_URL,
            )

            # 构建翻译提示 - 针对描述文本优化
            prompt = f"""请将以下描述翻译成中文，保持原意和流畅性：

{description}

中文翻译："""

            # 异步调用
            response = await client.chat.completions.create(
                model=config.QWEN_LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的翻译助手，擅长将技术描述翻译成准确流畅的中文。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            translated = response.choices[0].message.content.strip()
            logger.info(f"描述翻译完成: {description[:50]}... -> {translated[:50]}...")

            # 缓存结果
            cls._cache[cache_key] = translated
            return translated

        except Exception as e:
            logger.error(f"描述翻译失败: {e}")
            return description

    @classmethod
    def translate_description(cls, description: str) -> str:
        """
        将英文描述翻译成中文（同步版本，用于非异步上下文）

        Args:
            description: 英文描述

        Returns:
            中文翻译结果
        """
        if not description:
            return description

        # 检查缓存
        cache_key = f"desc:{hash(description) % 1000000}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        try:
            import openai

            # 获取配置
            config = LightRAGConfig
            api_key = config.get_api_key()

            if not api_key:
                logger.warning("没有配置 API Key，无法使用 LLM 翻译")
                return description

            # 使用同步客户端
            client = openai.OpenAI(
                api_key=api_key,
                base_url=config.DASHSCOPE_BASE_URL,
            )

            # 构建翻译提示 - 针对描述文本优化
            prompt = f"""请将以下描述翻译成中文，保持原意和流畅性：

{description}

中文翻译："""

            # 同步调用
            response = client.chat.completions.create(
                model=config.QWEN_LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的翻译助手，擅长将技术描述翻译成准确流畅的中文。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            translated = response.choices[0].message.content.strip()
            logger.info(f"描述翻译完成: {description[:50]}... -> {translated[:50]}...")

            # 缓存结果
            cls._cache[cache_key] = translated
            return translated

        except Exception as e:
            logger.error(f"描述翻译失败: {e}")
            return description


def translate_entity_name(name: str) -> str:
    """
    将英文实体名称映射回中文
    
    Args:
        name: 实体名称
        
    Returns:
        映射后的中文名称，如果没有映射则返回原名称
    """
    manager = get_mapping_manager()
    
    # 首先检查精确匹配
    translated = manager.get_mapping(name)
    if translated != name:
        return translated
    
    # 检查是否包含英文（简单的启发式规则）
    # 如果名称全是中文或数字，直接返回
    if all('\u4e00' <= c <= '\u9fff' or c.isdigit() or c in '（）()【】[]《》<>，,。.！!？?、：:""'' ' for c in name):
        return name
    
    # 如果包含英文字母，可能是英文实体，尝试查找包含该英文的映射
    mappings = manager.get_all_mappings()
    for eng, chn in mappings.items():
        if eng.lower() in name.lower():
            return chn
    
    # 如果没有找到映射，尝试自动翻译
    if any(c.isalpha() and c.isascii() for c in name):
        logger.info(f"未找到映射，尝试自动翻译: {name}")
        translated = EntityTranslator.translate(name)
        if translated != name:
            return translated
    
    return name


class LightRAGConfig:
    """LightRAG 配置类"""
    
    # 默认使用 DashScope (通义千问)
    DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_LLM_MODEL = "qwen-turbo"  # 使用更快的 turbo 模型
    QWEN_EMBED_MODEL = "text-embedding-v3"
    EMBED_DIM = 1024
    # 性能优化配置
    MAX_TOKEN_PER_CHUNK = 1024  # 减小 chunk 大小
    CHUNK_SIZE = 1024  # 更小的 chunk
    CHUNK_OVERLAP = 128  # 更小的重叠
    
    @classmethod
    def get_api_key(cls) -> str:
        """获取 API Key（优先从 settings 或环境变量）"""
        return getattr(settings, 'DASHSCOPE_API_KEY', '') or os.getenv('DASHSCOPE_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')


class LightRAGService:
    """LightRAG 服务封装类"""
    
    def __init__(self, project_id: int = None, graph_id: int = None):
        """
        初始化 LightRAG 服务
        
        Args:
            project_id: 项目ID，用于隔离不同项目的知识图谱。为 None 时表示公共图谱。
            graph_id: 图谱ID，用于创建图谱专属目录。如果提供，工作目录将包含 graph_{graph_id}。
        """
        self.project_id = project_id
        self.graph_id = graph_id
        # 使用与 KnowledgeGraph.get_working_dir() 相同的逻辑
        project_folder = f'project_{project_id}' if project_id else 'project_public'
        if graph_id:
            self.working_dir = Path(settings.BASE_DIR) / 'media' / 'lightrag' / project_folder / f'graph_{graph_id}'
        else:
            self.working_dir = Path(settings.BASE_DIR) / 'media' / 'lightrag' / project_folder
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self._rag_instance = None
        
        # 注意：环境变量应该在调用方（视图层）设置，避免在异步上下文中查询数据库
        
    def _get_llm_config_sync(self) -> Dict[str, Any]:
        """同步获取 LLM 配置（尝试从 AIModelConfig 读取）"""
        # 首先尝试从环境变量获取 API Key
        default_api_key = LightRAGConfig.get_api_key()

        try:
            from .models import AIModelConfig
            from asgiref.sync import sync_to_async
            import asyncio

            # 定义同步查询函数
            def get_config():
                # 优先查找 knowledge_graph 角色的配置（知识图谱专用）
                config = AIModelConfig.objects.filter(
                    role='knowledge_graph',
                    is_active=True
                ).first()

                # 如果没有 knowledge_graph 配置，尝试 knowledge_base
                if not config:
                    config = AIModelConfig.objects.filter(
                        role='knowledge_base',
                        is_active=True
                    ).first()

                if not config:
                    #  fallback 到任意可用配置
                    config = AIModelConfig.objects.filter(is_active=True).first()

                return config

            # 检查是否在异步上下文中
            try:
                asyncio.get_running_loop()
                # 如果在异步上下文中，使用 sync_to_async
                config = asyncio.get_event_loop().run_until_complete(sync_to_async(get_config)())
            except RuntimeError:
                # 不在异步上下文中，直接调用
                config = get_config()

            logger.info(f"查找 AI 配置结果: {config}")

            if config:
                api_key = config.api_key or default_api_key
                base_url = config.base_url or LightRAGConfig.DASHSCOPE_BASE_URL
                model_name = config.model_name or LightRAGConfig.QWEN_LLM_MODEL
                max_tokens = config.max_tokens or 4096
                temperature = config.temperature or 0.1
                logger.info(f"使用 AI 配置: {config.name} (role={config.role}, model={model_name})")
                logger.info(f"API Key: {'已设置' if api_key else '未设置'}")
                logger.info(f"参数配置: max_tokens={max_tokens}, temperature={temperature}")
                return {
                    'api_key': api_key,
                    'base_url': base_url,
                    'model_name': model_name,
                    'max_tokens': max_tokens,
                    'temperature': temperature,
                }
        except Exception as e:
            logger.warning(f"读取 AI 模型配置失败: {e}")
            import traceback
            logger.warning(f"堆栈: {traceback.format_exc()}")
        
        # 默认配置
        logger.info(f"使用默认配置, API Key: {'已设置' if default_api_key else '未设置'}")
        return {
            'api_key': default_api_key,
            'base_url': LightRAGConfig.DASHSCOPE_BASE_URL,
            'model_name': LightRAGConfig.QWEN_LLM_MODEL,
            'max_tokens': 4096,
            'temperature': 0.1,
        }
    
    async def _get_llm_config(self) -> Dict[str, Any]:
        """异步获取 LLM 配置（使用 sync_to_async 包装同步方法）"""
        from asgiref.sync import sync_to_async
        return await sync_to_async(self._get_llm_config_sync)()
    
    async def _llm_model_func_sync(self, prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
        """LLM 调用函数（LightRAG 使用 - 必须是 async）"""
        # 获取配置（使用同步版本）
        config = self._get_llm_config_sync()
        api_key = config['api_key']
        base_url = config['base_url']
        model_name = config['model_name']

        if not api_key:
            raise ValueError("API Key 未设置！请检查 AIModelConfig 配置")

        # 使用异步方式调用
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history_messages:
            messages.extend(history_messages)
        messages.append({"role": "user", "content": prompt})

        # 过滤掉 LightRAG 传递的额外参数
        lightrag_only_params = ['hashing_kv', 'api_key', 'base_url', 'model_name', 'embedding_model']
        openai_kwargs = {k: v for k, v in kwargs.items() if k not in lightrag_only_params}

        # 使用 LightRAG 传递的 model 参数
        final_model = openai_kwargs.pop('model', model_name)

        # 合并配置参数
        final_kwargs = {
            'max_tokens': config.get('max_tokens', 4096),
            'temperature': config.get('temperature', 0.1),
            **openai_kwargs
        }

        response = await client.chat.completions.create(
            model=final_model,
            messages=messages,
            **final_kwargs
        )
        return response.choices[0].message.content
    
    async def _embed_model_func_sync(self, texts: List[str]) -> np.ndarray:
        """Embedding 调用函数（LightRAG 使用 - 必须是 async）"""
        from openai import AsyncOpenAI
        from asgiref.sync import sync_to_async

        # 获取配置（使用同步版本）
        config = self._get_llm_config_sync()
        api_key = config['api_key']
        base_url = config['base_url']

        if not api_key:
            raise ValueError("API Key 未设置！请检查 AIModelConfig 配置")

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

        resp = await client.embeddings.create(
            model=LightRAGConfig.QWEN_EMBED_MODEL,
            input=texts,
            dimensions=LightRAGConfig.EMBED_DIM,
        )
        embeddings = [item.embedding for item in resp.data]
        return np.array(embeddings, dtype=np.float32)
    
    async def _llm_model_func_with_retry(self, prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
        """
        LLM 调用函数（带重试机制）
        实体提取对 LLM 调用稳定性要求高，添加重试机制避免偶发失败
        """
        import random
        
        max_retries = 3
        base_delay = 1  # 基础延迟 1 秒
        
        # LightRAG 会通过 llm_model_kwargs 传递 api_key 和 base_url
        api_key = kwargs.pop('api_key', None)
        base_url = kwargs.pop('base_url', None)
        model_name = kwargs.pop('model', None)
        
        if not api_key or not base_url:
            config = await self._get_llm_config()
            api_key = api_key or config['api_key']
            base_url = base_url or config['base_url']
            model_name = model_name or config['model_name']
        
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.debug(f"LLM 调用尝试 {attempt + 1}/{max_retries}")
                result = await openai_complete_if_cache(
                    model_name,
                    prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    base_url=base_url,
                    api_key=api_key,
                    **kwargs,
                )
                if attempt > 0:
                    logger.info(f"LLM 调用在第 {attempt + 1} 次尝试成功")
                return result
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # 判断是否需要重试的错误类型
                retryable_errors = [
                    'timeout', 'connection', 'rate limit', 'too many requests',
                    'internal server error', 'service unavailable', 'temporarily unavailable',
                    '连接超时', '请求过于频繁', '服务器错误', '服务暂时不可用'
                ]
                
                should_retry = any(err in error_msg for err in retryable_errors)
                
                if not should_retry and attempt < max_retries - 1:
                    # 对于非重试类错误，也尝试一次重试（可能是偶发问题）
                    should_retry = True
                
                if should_retry and attempt < max_retries - 1:
                    # 指数退避 + 随机抖动
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"LLM 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}, {delay:.1f}秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM 调用最终失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    break
        
        # 所有重试都失败，抛出最后一个错误
        raise last_error
    
    async def _llm_model_func(self, prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
        """LLM 调用函数（包装带重试的版本）"""
        return await self._llm_model_func_with_retry(
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs,
        )
    
    async def _embed_model_func(self, texts: List[str]) -> np.ndarray:
        """Embedding 调用函数"""
        from openai import AsyncOpenAI
        
        config = await self._get_llm_config()
        client = AsyncOpenAI(
            api_key=config['api_key'],
            base_url=config['base_url']
        )
        
        resp = await client.embeddings.create(
            model=LightRAGConfig.QWEN_EMBED_MODEL,
            input=texts,
            dimensions=LightRAGConfig.EMBED_DIM,
        )
        embeddings = [item.embedding for item in resp.data]
        return np.array(embeddings, dtype=np.float32)
    
    def _get_rag_sync(self):
        """获取或创建 LightRAG 实例（同步版本）"""
        if not LIGHT_RAG_AVAILABLE:
            logger.error("LightRAG 未安装")
            return None
            
        if self._rag_instance is None:
            try:
                # 同步方法使用同步配置获取
                config = self._get_llm_config_sync()
                logger.info(f"初始化 LightRAG，API Key: {'已设置' if config['api_key'] else '未设置'}")
                
                self._rag_instance = LightRAG(
                    working_dir=str(self.working_dir),
                    llm_model_func=self._llm_model_func_sync,
                    embedding_func=EmbeddingFunc(
                        embedding_dim=LightRAGConfig.EMBED_DIM,
                        max_token_size=8192,
                        func=self._embed_model_func_sync,
                    ),
                    llm_model_kwargs={
                        'api_key': config['api_key'],
                        'base_url': config['base_url'],
                        'model': config['model_name'],
                        'max_tokens': config.get('max_tokens', 4096),
                        'temperature': config.get('temperature', 0.1),
                    },
                    auto_manage_storages_states=True,  # 自动管理存储状态
                    chunk_token_size=LightRAGConfig.CHUNK_SIZE,
                    chunk_overlap_token_size=LightRAGConfig.CHUNK_OVERLAP,
                )
                
                # 初始化存储（必须在查询前完成）
                import asyncio
                logger.info("初始化 LightRAG 存储（同步版本）...")
                asyncio.run(self._rag_instance.initialize_storages())
                logger.info("LightRAG 存储初始化完成（同步版本）")
                
            except Exception as e:
                logger.error(f"创建 LightRAG 实例失败: {e}")
                import traceback
                logger.error(f"堆栈: {traceback.format_exc()}")
                return None
        return self._rag_instance

    async def _get_rag(self):
        """获取或创建 LightRAG 实例（异步版本）"""
        if not LIGHT_RAG_AVAILABLE:
            logger.error("LightRAG 未安装")
            return None

        if self._rag_instance is None:
            try:
                # 异步方法使用异步配置获取
                config = await self._get_llm_config()
                logger.info(f"初始化 LightRAG (异步版本)，API Key: {'已设置' if config['api_key'] else '未设置'}")

                self._rag_instance = LightRAG(
                    working_dir=str(self.working_dir),
                    llm_model_func=self._llm_model_func,
                    embedding_func=EmbeddingFunc(
                        embedding_dim=LightRAGConfig.EMBED_DIM,
                        max_token_size=8192,
                        func=self._embed_model_func,
                    ),
                    llm_model_kwargs={
                        'api_key': config['api_key'],
                        'base_url': config['base_url'],
                        'model': config['model_name'],
                        'max_tokens': config.get('max_tokens', 4096),
                        'temperature': config.get('temperature', 0.1),
                    },
                    auto_manage_storages_states=True,
                    chunk_token_size=LightRAGConfig.CHUNK_SIZE,
                    chunk_overlap_token_size=LightRAGConfig.CHUNK_OVERLAP,
                )
                
                # 初始化存储（必须在查询前完成）
                logger.info("初始化 LightRAG 存储...")
                await self._rag_instance.initialize_storages()
                logger.info("LightRAG 存储初始化完成")
                
            except Exception as e:
                logger.error(f"创建 LightRAG 实例失败: {e}")
                import traceback
                logger.error(f"堆栈: {traceback.format_exc()}")
                return None
        return self._rag_instance
    
    def _build_graph_sync(self, documents: List[Any], progress_callback=None) -> Dict[str, Any]:
        """
        同步方法：从需求文档构建知识图谱

        Args:
            documents: 文档列表
            progress_callback: 进度回调函数，接收 (progress, current_document) 参数（可以是异步函数）
        """
        rag = self._get_rag_sync()
        if not rag:
            return {'success': False, 'error': 'LightRAG 未初始化'}

        try:
            # 初始化存储（必须在插入前完成）
            import asyncio
            total_docs = len(documents)

            # 辅助函数：调用进度回调
            def call_progress_callback(progress, message):
                if progress_callback:
                    try:
                        progress_callback(progress, message)
                    except Exception as e:
                        logger.warning(f"进度回调执行失败: {e}")

            # 更新进度：开始初始化
            call_progress_callback(5, '正在初始化存储...')
            
            # LightRAG 需要显式初始化存储
            logger.info("正在初始化 LightRAG 存储...")
            # 使用 nest_asyncio 允许嵌套事件循环
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except ImportError:
                pass
            asyncio.run(rag.initialize_storages())
            logger.info("LightRAG 存储初始化完成")

            # 更新进度：初始化完成
            call_progress_callback(10, '存储初始化完成')

            inserted_count = 0
            for idx, doc in enumerate(documents):
                # 计算进度 (10% ~ 80%)
                progress = 10 + int((idx / total_docs) * 70)

                # 提取文档文本（支持图片流程图分析）
                text_content = self._extract_document_text_sync(doc)
                if text_content == "__IMAGE_FLOWCHART__":
                    # 图片文件需要异步分析
                    logger.info(f"检测到图片流程图，使用多模态 AI 分析: {doc.title}")
                    try:
                        # 获取知识图谱 AI 配置
                        from .models import AIModelConfig
                        from .services import ImageFlowchartProcessor
                        config = AIModelConfig.get_active_config('qwen', 'knowledge_graph')
                        if not config:
                            config = AIModelConfig.objects.filter(is_active=True).first()

                        if config:
                            # 使用 asyncio.run 在同步上下文中运行异步方法
                            import asyncio
                            try:
                                import nest_asyncio
                                nest_asyncio.apply()
                            except ImportError:
                                pass
                            text_content = asyncio.run(
                                ImageFlowchartProcessor.analyze_flowchart_with_vision(doc.file.path, config)
                            )
                            logger.info(f"图片流程图分析完成: {doc.title}, 内容长度: {len(text_content)}")
                        else:
                            logger.error(f"未找到 AI 配置，无法分析图片: {doc.title}")
                            continue
                    except Exception as e:
                        logger.error(f"图片流程图分析失败 {doc.title}: {e}")
                        import traceback
                        logger.error(f"分析错误堆栈: {traceback.format_exc()}")
                        continue

                if not text_content:
                    logger.warning(f"文档 {doc.title} 没有内容，跳过")
                    continue
                if text_content.startswith("流程图分析失败") or text_content.startswith("错误："):
                    logger.error(f"文档 {doc.title} 解析失败: {text_content}")
                    continue

                # 更新进度：正在处理当前文档
                call_progress_callback(progress, f'正在处理: {doc.title}')

                # 添加文档元数据标签
                version_label = self._extract_version_from_title(doc.title)
                tagged_content = f"[文档版本: {version_label}]\n[文件名: {doc.title}]\n[文档ID: {doc.id}]\n{text_content}"

                logger.info(f"正在插入文档: {doc.title} ({len(tagged_content)} 字符)")
                # 使用同步插入方法
                try:
                    # 更新进度：开始插入
                    call_progress_callback(progress, f'正在插入: {doc.title}')
                    logger.info(f"调用 rag.insert() 开始: {doc.title}")
                    rag.insert(tagged_content)
                    logger.info(f"文档插入成功: {doc.title}")
                except Exception as insert_error:
                    logger.error(f"文档插入失败: {doc.title}, 错误: {insert_error}")
                    import traceback
                    logger.error(f"插入错误堆栈: {traceback.format_exc()}")
                inserted_count += 1

                # 更新进度：文档处理完成
                progress = 10 + int(((idx + 1) / total_docs) * 70)
                call_progress_callback(progress, f'已完成: {doc.title}')

            # 更新进度：获取统计信息
            call_progress_callback(85, '正在生成统计信息...')
            
            # 获取统计信息
            stats = self.get_stats()
            stats['success'] = True
            stats['inserted_documents'] = inserted_count
            
            # 更新进度：完成
            if progress_callback:
                progress_callback(100, '构建完成')
            
            return stats
            
        except Exception as e:
            logger.error(f"构建知识图谱失败: {e}")
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}
    
    async def _build_graph_async(self, documents: List[Any], progress_callback=None) -> Dict[str, Any]:
        """
        异步方法：从需求文档构建知识图谱
        使用线程池隔离事件循环，避免 LightRAG 的锁绑定问题

        Args:
            documents: 文档列表
            progress_callback: 进度回调函数，接收 (progress, current_document) 参数

        Returns:
            构建结果统计
        """
        # 用于在线程间传递进度的队列（使用线程安全的 queue.Queue）
        progress_queue = queue.Queue()

        # 辅助函数：调用进度回调
        async def call_progress_callback(progress, message):
            if progress_callback:
                try:
                    # 支持异步回调函数
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(progress, message)
                    else:
                        progress_callback(progress, message)
                except Exception as e:
                    logger.warning(f"进度回调执行失败: {e}")

        try:
            total_docs = len(documents)

            # 更新进度：开始初始化
            await call_progress_callback(5, '正在初始化存储...')

            # 使用线程池在独立线程中执行 LightRAG 操作
            # 这样可以避免 asyncio.Lock 绑定到不同事件循环的问题
            loop = asyncio.get_event_loop()

            def build_in_thread():
                """在独立线程中执行构建"""
                # 创建新的事件循环
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(
                        self._build_graph_in_isolated_loop(documents, progress_queue)
                    )
                finally:
                    new_loop.close()

            # 启动构建任务
            build_task = loop.run_in_executor(None, build_in_thread)

            # 监听进度更新
            last_progress = 5
            while True:
                try:
                    # 等待进度更新或构建完成（使用非阻塞方式检查队列）
                    try:
                        progress, message = progress_queue.get(timeout=0.5)
                        if progress == -1:  # 构建完成的信号
                            break
                        if progress > last_progress:
                            last_progress = progress
                            await call_progress_callback(progress, message)
                    except queue.Empty:
                        # 检查构建任务是否完成
                        if build_task.done():
                            break
                except Exception as e:
                    logger.warning(f"进度监听出错: {e}")
                    # 检查构建任务是否完成
                    if build_task.done():
                        break

            # 获取构建结果
            result = await build_task

            # 最终进度更新
            if result.get('success'):
                await call_progress_callback(100, '构建完成')

            return result

        except Exception as e:
            logger.error(f"构建知识图谱失败: {e}")
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}

    async def _build_graph_in_isolated_loop(self, documents: List[Any], progress_queue) -> Dict[str, Any]:
        """
        在隔离的事件循环中构建知识图谱
        注意：此方法在独立线程的新事件循环中运行，不能使用 sync_to_async
        """
        # 在隔离的事件循环中直接创建 RAG 实例（不使用 _get_rag，因为它使用了 sync_to_async）
        if not LIGHT_RAG_AVAILABLE:
            return {'success': False, 'error': 'LightRAG 未安装'}

        # 验证 API Key 是否配置
        config = self._get_llm_config_sync()
        if not config.get('api_key'):
            logger.error("LLM API Key 未配置，无法构建知识图谱")
            return {'success': False, 'error': 'LLM API Key 未配置，请在系统设置中配置 API Key'}

        try:
            logger.info(f"初始化 LightRAG (隔离模式)，API Key: {'已设置' if config['api_key'] else '未设置'}, 模型: {config.get('model_name', '默认')}")

            rag = LightRAG(
                working_dir=str(self.working_dir),
                llm_model_func=self._llm_model_func,
                embedding_func=EmbeddingFunc(
                    embedding_dim=LightRAGConfig.EMBED_DIM,
                    max_token_size=8192,
                    func=self._embed_model_func,
                ),
                llm_model_kwargs={
                    'api_key': config['api_key'],
                    'base_url': config['base_url'],
                    'model': config['model_name'],
                    'max_tokens': config.get('max_tokens', 4096),
                    'temperature': config.get('temperature', 0.1),
                },
                auto_manage_storages_states=False,  # 禁用自动管理，避免锁冲突
                chunk_token_size=LightRAGConfig.CHUNK_SIZE,
                chunk_overlap_token_size=LightRAGConfig.CHUNK_OVERLAP,
            )

            # 初始化存储
            logger.info("初始化 LightRAG 存储...")
            await rag.initialize_storages()
            logger.info("LightRAG 存储初始化完成")

        except Exception as e:
            logger.error(f"创建 LightRAG 实例失败: {e}")
            import traceback
            logger.error(f"堆栈: {traceback.format_exc()}")
            return {'success': False, 'error': f'LightRAG 初始化失败: {str(e)}'}

        total_docs = len(documents)

        # 辅助函数：发送进度更新（使用线程安全的 queue.Queue，同步 put）
        def send_progress(progress, message):
            try:
                progress_queue.put((progress, message))
            except Exception as e:
                logger.warning(f"进度更新失败: {e}")

        # LightRAG 存储已在 _get_rag 中初始化
        logger.info("LightRAG 存储已初始化")

        # 更新进度：初始化完成
        send_progress(10, '存储初始化完成')

        inserted_count = 0
        for idx, doc in enumerate(documents):
            # 计算进度 (10% ~ 80%)
            progress = 10 + int((idx / total_docs) * 70)

            # 提取文档文本（支持图片流程图分析）
            # 注意：_extract_document_text_sync 是同步方法，但我们在新的事件循环中
            text_content = self._extract_document_text_sync(doc)
            
            if text_content == "__IMAGE_FLOWCHART__":
                # 图片文件需要异步分析
                logger.info(f"检测到图片流程图，使用多模态 AI 分析: {doc.title}")
                try:
                    from .services import ImageFlowchartProcessor
                    
                    # 使用已获取的 llm_config 配置，而不是直接查询数据库
                    # 在隔离的事件循环中不能直接访问 Django ORM
                    llm_config = self._get_llm_config_sync()
                    
                    # 创建配置对象供 ImageFlowchartProcessor 使用
                    class SimpleConfig:
                        def __init__(self, config_dict):
                            self.api_key = config_dict.get('api_key')
                            self.base_url = config_dict.get('base_url')
                            self.model_name = config_dict.get('model_name')
                    
                    config = SimpleConfig(llm_config)

                    if config.api_key:
                        text_content = await ImageFlowchartProcessor.analyze_flowchart_with_vision(doc.file.path, config)
                        logger.info(f"图片流程图分析完成: {doc.title}, 内容长度: {len(text_content)}")
                    else:
                        logger.error(f"未配置 API Key，无法分析图片: {doc.title}")
                        continue
                except Exception as e:
                    logger.error(f"图片流程图分析失败 {doc.title}: {e}")
                    import traceback
                    logger.error(f"分析错误堆栈: {traceback.format_exc()}")
                    continue

            if not text_content:
                logger.warning(f"文档 {doc.title} 没有内容，跳过")
                continue
            if text_content.startswith("流程图分析失败") or text_content.startswith("错误："):
                logger.error(f"文档 {doc.title} 解析失败: {text_content}")
                continue

            # 更新进度：正在处理当前文档
            send_progress(progress, f'正在处理: {doc.title}')

            # 添加文档元数据标签
            version_label = self._extract_version_from_title(doc.title)
            tagged_content = f"[文档版本: {version_label}]\n[文件名: {doc.title}]\n[文档ID: {doc.id}]\n{text_content}"

            logger.info(f"正在插入文档: {doc.title} ({len(tagged_content)} 字符)")
            # 使用异步插入方法
            try:
                # 更新进度：开始插入
                send_progress(progress, f'正在插入: {doc.title}')
                logger.info(f"调用 rag.ainsert() 开始: {doc.title}")
                await rag.ainsert(tagged_content)
                logger.info(f"文档插入成功: {doc.title}")
                inserted_count += 1

                # 等待 LightRAG 完成内部处理，避免锁冲突
                await asyncio.sleep(2)

            except Exception as insert_error:
                logger.error(f"文档插入失败: {doc.title}, 错误: {insert_error}")
                import traceback
                logger.error(f"插入错误堆栈: {traceback.format_exc()}")
                # 继续处理下一个文档，不中断整个流程

            # 更新进度：文档处理完成
            progress = 10 + int(((idx + 1) / total_docs) * 70)
            send_progress(progress, f'已完成: {doc.title}')

        # 更新进度：获取统计信息
        send_progress(85, '正在生成统计信息...')

        # 关键修复：手动调用 _insert_done 确保所有数据写入磁盘
        # LightRAG 使用共享存储，需要显式调用 index_done_callback 来持久化数据
        logger.info("强制保存 LightRAG 数据到磁盘...")
        try:
            if hasattr(rag, '_insert_done'):
                await rag._insert_done()
                logger.info("LightRAG _insert_done 调用成功")
            # 额外等待确保文件系统写入完成
            await asyncio.sleep(3)
        except Exception as e:
            logger.warning(f"保存 LightRAG 数据时出错: {e}")
            import traceback
            logger.error(f"保存错误堆栈: {traceback.format_exc()}")
            # 如果保存失败，等待更长时间
            await asyncio.sleep(5)

        # 验证实体是否成功提取
        logger.info("验证实体提取结果...")
        working_dir = Path(self.working_dir)
        entity_files = [
            'kv_store_entity_chunks.json',
            'kv_store_full_entities.json',
            'vdb_entities.json'
        ]
        
        entity_found = False
        for ef in entity_files:
            ef_path = working_dir / ef
            if ef_path.exists():
                try:
                    with open(ef_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and len(data) > 0:
                            logger.info(f"找到实体数据文件: {ef}, 实体数量: {len(data)}")
                            entity_found = True
                            break
                        elif isinstance(data, list) and len(data) > 0:
                            logger.info(f"找到实体数据文件: {ef}, 实体数量: {len(data)}")
                            entity_found = True
                            break
                except Exception as e:
                    logger.warning(f"读取实体文件 {ef} 失败: {e}")
        
        if not entity_found:
            logger.error("严重警告: 未找到任何实体数据，实体提取可能失败！")
            # 发送完成信号并返回错误
            progress_queue.put((-1, 'done'))
            return {
                'success': False,
                'error': '实体提取失败，未生成实体数据。请检查 LLM API 是否正常工作。',
                'inserted_documents': inserted_count,
                'nodes': 0,
                'edges': 0
            }

        # 获取统计信息
        stats = await self.get_stats_async()
        stats['success'] = True
        stats['inserted_documents'] = inserted_count

        # 验证统计信息合理性
        if stats.get('nodes', 0) == 0:
            logger.error(f"构建完成后实体数量为 0，请检查构建过程。工作目录: {self.working_dir}")
            stats['success'] = False
            stats['error'] = '构建完成但未生成实体节点，可能原因：1) LLM API 调用失败 2) 文档内容无法提取实体'

        # 更新进度：完成
        send_progress(100, '构建完成')

        # 发送完成信号
        progress_queue.put((-1, 'done'))

        return stats

    async def build_graph(self, documents: List[Any], progress_callback=None) -> Dict[str, Any]:
        """
        从需求文档构建知识图谱

        Args:
            documents: RequirementDocument 对象列表
            progress_callback: 进度回调函数，接收 (progress, current_document) 参数

        Returns:
            构建结果统计
        """
        # 使用异步版本构建方法
        return await self._build_graph_async(documents, progress_callback)

    def _extract_document_text_sync(self, document) -> str:
        """同步方法：提取文档文本内容"""
        logger.info(f"开始提取文档文本: {document.title}, 类型: {document.document_type}")

        # 如果已经有提取的文本，直接返回
        if hasattr(document, 'extracted_text') and document.extracted_text:
            logger.info(f"使用已提取的文本: {document.title}")
            return document.extracted_text

        # 否则从文件提取
        try:
            from .services import DocumentProcessor
            result = DocumentProcessor.extract_text(document)
            logger.info(f"DocumentProcessor.extract_text 返回结果: {result[:100] if result else 'None'}...")

            # 如果是图片文件，返回特殊标记，由异步方法处理
            if result == "__IMAGE_FLOWCHART__":
                logger.info(f"检测到图片流程图标记: {document.title}")
                return "__IMAGE_FLOWCHART__"
            return result
        except Exception as e:
            logger.error(f"提取文档文本失败 {document.title}: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return ""

    async def _extract_document_text(self, document) -> str:
        """异步方法：提取文档文本内容，图片使用多模态 AI 分析"""
        # 如果已经有提取的文本，直接返回
        if hasattr(document, 'extracted_text') and document.extracted_text:
            return document.extracted_text

        # 使用异步方法提取，支持图片流程图分析
        try:
            from .services import DocumentProcessor
            from .models import AIModelConfig

            # 获取知识图谱 AI 配置
            config = AIModelConfig.get_active_config('qwen', 'knowledge_graph')
            if not config:
                config = AIModelConfig.objects.filter(is_active=True).first()

            return await DocumentProcessor.extract_text_async(document, config)
        except Exception as e:
            logger.error(f"提取文档文本失败 {document.title}: {e}")
            return ""
    
    def _extract_version_from_title(self, title: str) -> str:
        """从标题提取版本号"""
        import re
        # 匹配 v1, v2, V1, V2 等格式
        match = re.search(r'[vV](\d+)', title)
        if match:
            return f"V{match.group(1)}"
        # 匹配 版本1, 版本2 等格式
        match = re.search(r'版本(\d+)', title)
        if match:
            return f"V{match.group(1)}"
        return "未知版本"
    
    async def query(self, question: str, mode: str = "mix") -> Dict[str, Any]:
        """
        查询知识图谱
        
        Args:
            question: 查询问题
            mode: 查询模式 (local/global/mix)
            
        Returns:
            查询结果
        """
        import asyncio
        
        # 使用同步方式查询（在单独的线程中执行）
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._query_sync, question, mode)
    
    def _query_sync(self, question: str, mode: str = "mix") -> Dict[str, Any]:
        """同步查询知识图谱"""
        import asyncio
        import nest_asyncio
        from openai import OpenAI
        
        # 允许嵌套的事件循环
        nest_asyncio.apply()
        
        rag = self._get_rag_sync()
        if not rag:
            return {'success': False, 'error': 'LightRAG 未初始化'}
        
        try:
            # 确保存储已初始化（这是必需的！）
            logger.info("确保 LightRAG 存储已初始化...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(rag.initialize_storages())
                logger.info("LightRAG 存储初始化完成")
            except Exception as init_err:
                logger.warning(f"存储初始化可能已存在: {init_err}")
            finally:
                loop.close()
            
            # 构建查询参数
            query_param = QueryParam(mode=mode)
            
            # 第一步：使用 query_data 获取检索结果（同步方法）
            logger.info(f"正在检索知识图谱，问题: {question}")
            retrieval_result = rag.query_data(question, param=query_param)
            
            if not retrieval_result or not retrieval_result.get('data'):
                logger.warning("未找到相关知识")
                return {
                    'success': True,
                    'answer': '抱歉，未找到与问题相关的知识。',
                    'mode': mode,
                }
            
            # 第二步：构建上下文
            context = retrieval_result.get('data', {}).get('context', '')
            if not context:
                logger.warning("检索结果为空")
                return {
                    'success': True,
                    'answer': '抱歉，无法从知识图谱中提取有效信息。',
                    'mode': mode,
                }
            
            # 第三步：调用 LLM 生成答案
            logger.info("正在生成答案...")
            config = self._get_llm_config_sync()
            
            client = OpenAI(
                api_key=config['api_key'],
                base_url=config['base_url']
            )
            
            system_prompt = """你是一个知识图谱问答助手。请根据提供的上下文信息回答用户的问题。
如果上下文中没有相关信息，请明确告知用户。
请用中文回答。"""
            
            user_prompt = f"""上下文信息：
{context}

用户问题：{question}

请根据上下文回答用户的问题："""
            
            response = client.chat.completions.create(
                model=config['model_name'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=config.get('max_tokens', 4096),
                temperature=config.get('temperature', 0.7)
            )
            
            answer = response.choices[0].message.content
            
            return {
                'success': True,
                'answer': answer,
                'mode': mode,
            }
            
        except Exception as e:
            logger.error(f"查询知识图谱失败: {e}")
            import traceback
            logger.error(f"堆栈: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}
    
    async def get_stats_async(self) -> Dict[str, Any]:
        """
        异步获取知识图谱统计信息
        注意：在隔离的事件循环中直接调用同步方法

        Returns:
            统计信息字典
        """
        # 在隔离的事件循环中直接调用同步方法
        return self.get_stats()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取知识图谱统计信息
        兼容多种 LightRAG 版本的存储文件名

        Returns:
            统计信息字典
        """
        try:
            import json
            from pathlib import Path

            stats = {
                'nodes': 0,
                'edges': 0,
                'documents': 0,
                'has_graph': False,
            }

            # 将 working_dir 转换为 Path 对象
            working_dir = Path(self.working_dir)
            logger.info(f"获取统计信息，工作目录: {working_dir}")
            
            # 检查工作目录中的文件
            if working_dir.exists():
                files = list(working_dir.glob('*.json'))
                logger.info(f"工作目录中的文件: {[f.name for f in files]}")
            
            # 检查图谱是否存在（通过检查实体文件是否存在）
            # 兼容多种可能的实体存储文件名
            entity_files = [
                'kv_store_entity_chunks.json',  # 新版 LightRAG
                'kv_store_full_entities.json',  # 旧版 LightRAG
            ]
            
            for ef_name in entity_files:
                entities_file = working_dir / ef_name
                if entities_file.exists():
                    stats['has_graph'] = True
                    try:
                        with open(entities_file, 'r', encoding='utf-8') as f:
                            entities_data = json.load(f)
                            logger.info(f"实体文件 {ef_name} 内容类型: {type(entities_data)}, 键数量: {len(entities_data) if isinstance(entities_data, dict) else 'N/A'}")
                            # 实体数据格式：{entity_name: {chunk_ids: [...]}} 或 {doc_id: {entity_names: [...]}}
                            if isinstance(entities_data, dict):
                                # 如果是文档级别的实体列表，需要计算所有唯一实体
                                if ef_name == 'kv_store_full_entities.json':
                                    all_entities = set()
                                    for doc_entities in entities_data.values():
                                        if isinstance(doc_entities, dict):
                                            entity_names = doc_entities.get('entity_names', [])
                                            all_entities.update(entity_names)
                                        elif isinstance(doc_entities, list):
                                            all_entities.update(doc_entities)
                                    stats['nodes'] = len(all_entities)
                                else:
                                    stats['nodes'] = len(entities_data)
                                logger.info(f"实体数量: {stats['nodes']}")
                                break
                    except Exception as e:
                        logger.warning(f"读取实体文件 {ef_name} 失败: {e}")
            
            if stats['nodes'] == 0:
                logger.warning(f"未找到实体数据文件或实体数量为 0")

            # 读取关系文件（兼容多种文件名）
            relation_files = [
                'kv_store_relation_chunks.json',  # 新版 LightRAG
                'kv_store_full_relations.json',   # 旧版 LightRAG
            ]
            
            for rf_name in relation_files:
                relations_file = working_dir / rf_name
                if relations_file.exists():
                    try:
                        with open(relations_file, 'r', encoding='utf-8') as f:
                            relations_data = json.load(f)
                            logger.info(f"关系文件 {rf_name} 内容类型: {type(relations_data)}, 键数量: {len(relations_data) if isinstance(relations_data, dict) else 'N/A'}")
                            # 关系数据格式：{relation_key: {source: ..., target: ...}}
                            if isinstance(relations_data, dict):
                                stats['edges'] = len(relations_data)
                                logger.info(f"关系数量: {stats['edges']}")
                                break
                    except Exception as e:
                        logger.warning(f"读取关系文件 {rf_name} 失败: {e}")
            
            if stats['edges'] == 0:
                logger.warning(f"未找到关系数据文件或关系数量为 0")
            
            # 读取文档文件 kv_store_full_docs.json
            docs_file = working_dir / 'kv_store_full_docs.json'
            if docs_file.exists():
                with open(docs_file, 'r', encoding='utf-8') as f:
                    docs_data = json.load(f)
                    stats['documents'] = len(docs_data)
                    logger.info(f"文档数量: {stats['documents']}")
            else:
                logger.warning(f"文档文件不存在: {docs_file}")
            
            logger.info(f"最终统计: nodes={stats['nodes']}, edges={stats['edges']}, documents={stats['documents']}")
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            return {'nodes': 0, 'edges': 0, 'documents': 0, 'has_graph': False}
    
    async def get_graph_data_async(self) -> Optional[Dict[str, Any]]:
        """
        异步获取知识图谱完整数据（用于可视化）- 使用 LightRAG API

        Returns:
            图谱数据字典，包含 nodes 和 edges
        """
        try:
            import json
            from pathlib import Path

            working_dir = Path(self.working_dir)
            logger.info(f"获取图谱数据（异步），工作目录: {working_dir}")

            nodes = []
            edges = []

            # 获取 LightRAG 实例
            rag = await self._get_rag()
            if not rag:
                logger.error("LightRAG 实例未初始化")
                return None

            # 从 LightRAG 的图存储中获取所有节点
            try:
                # 检查图存储是否可用
                if not rag.chunk_entity_relation_graph:
                    logger.warning("LightRAG 图存储未初始化，降级到 JSON 方式")
                    raise Exception("Graph storage not initialized")
                
                all_nodes = await rag.chunk_entity_relation_graph.get_all_nodes()
                logger.info(f"从 LightRAG 获取到 {len(all_nodes)} 个节点")

                # 调试：打印第一个节点的数据结构
                if all_nodes:
                    import json
                    logger.info(f"第一个节点数据示例: {json.dumps(all_nodes[0], ensure_ascii=False)}")
                    # 统计有多少节点有描述
                    nodes_with_desc = sum(1 for n in all_nodes if n.get('description'))
                    logger.info(f"有描述的节点数: {nodes_with_desc}/{len(all_nodes)}")

                # 构建节点列表
                node_id = 0
                entity_name_to_id = {}
                translated_name_to_original = {}  # 映射翻译后的名称到原始名称

                for node_data in all_nodes:
                    # 尝试多个可能的字段名获取实体名称
                    entity_name = node_data.get('id', '')
                    if not entity_name:
                        entity_name = node_data.get('entity_id', '')
                    if not entity_name:
                        continue

                    # 将英文实体名称映射回中文
                    translated_name = translate_entity_name(entity_name)
                    if translated_name != entity_name:
                        logger.info(f"实体名称翻译: {entity_name} -> {translated_name}")

                    # 获取实体描述 - 尝试多个可能的字段名
                    description = node_data.get('description', '')
                    if not description:
                        # 尝试其他可能的字段名
                        description = node_data.get('entity_description', '')
                    if not description:
                        # 尝试从 graphml 的 d2 字段获取
                        description = node_data.get('d2', '')

                    # 处理描述中的 <SEP> 分隔符（多个描述合并的情况）
                    if '<SEP>' in description:
                        desc_parts = description.split('<SEP>')
                        # 对每个部分分别处理：如果是英文则翻译，否则保留原样
                        processed_parts = []
                        for part in desc_parts:
                            part = part.strip()
                            if not part:
                                continue
                            # 如果这部分是英文，翻译成中文
                            if EntityTranslator._is_english_text(part):
                                try:
                                    translated_part = await EntityTranslator.translate_description_async(part)
                                    if translated_part:
                                        logger.info(f"描述部分翻译: {part[:50]}... -> {translated_part[:50]}...")
                                        processed_parts.append(translated_part)
                                    else:
                                        processed_parts.append(part)
                                except Exception as e:
                                    logger.warning(f"描述部分翻译失败: {e}")
                                    processed_parts.append(part)
                            else:
                                # 中文部分直接保留
                                processed_parts.append(part)
                        description = '\n\n'.join(processed_parts)
                    else:
                        # 单个描述，直接检测并翻译
                        if description and EntityTranslator._is_english_text(description):
                            try:
                                translated_desc = await EntityTranslator.translate_description_async(description)
                                if translated_desc:
                                    logger.info(f"描述翻译: {description[:50]}... -> {translated_desc[:50]}...")
                                    description = translated_desc
                            except Exception as e:
                                logger.warning(f"描述翻译失败: {e}")

                    # 获取实体类型
                    entity_type = node_data.get('entity_type', 'UNKNOWN')
                    if entity_type == 'UNKNOWN':
                        entity_type = node_data.get('d1', 'UNKNOWN')  # 尝试 graphml 的 d1 字段

                    # 获取 source_id 并计算 count
                    source_id = node_data.get('source_id', '')
                    if not source_id:
                        source_id = node_data.get('d3', '')  # 尝试 graphml 的 d3 字段
                    count = len(source_id.split('<SEP>')) if source_id else 1

                    node = {
                        'id': node_id,
                        'label': translated_name,  # 使用翻译后的名称
                        'original_name': entity_name,  # 保留原始名称
                        'count': count,
                        'weight': count,  # 添加 weight 字段
                        'category': 0,  # 添加 category 字段
                        'entity_type': entity_type,  # 添加实体类型
                        'description': description,  # 添加描述字段
                    }
                    nodes.append(node)
                    entity_name_to_id[entity_name] = node_id
                    translated_name_to_original[translated_name] = entity_name
                    node_id += 1

                logger.info(f"构建节点数量: {len(nodes)}")

                # 调试：打印几个节点的数据示例
                if nodes:
                    for i, n in enumerate(nodes[:3]):
                        logger.info(f"返回节点示例 {i}: id={n['id']}, label={n['label']}, description={n.get('description', '')[:50]}...")

            except Exception as e:
                logger.warning(f"从 LightRAG 获取节点失败: {e}")
                # 降级到从 JSON 文件读取
                return self._get_graph_data_from_json()

            # 从 LightRAG 的图存储中获取所有边
            try:
                all_edges = await rag.chunk_entity_relation_graph.get_all_edges()
                logger.info(f"从 LightRAG 获取到 {len(all_edges)} 条边")

                # 构建边列表
                edge_id = 0
                for edge_data in all_edges:
                    source_name = edge_data.get('source', '')
                    target_name = edge_data.get('target', '')

                    # 查找映射后的实体ID
                    source_id = entity_name_to_id.get(source_name)
                    target_id = entity_name_to_id.get(target_name)

                    # 如果找不到，尝试通过翻译后的名称查找
                    if source_id is None:
                        source_translated = translate_entity_name(source_name)
                        for orig_name, nid in entity_name_to_id.items():
                            if translate_entity_name(orig_name) == source_translated:
                                source_id = nid
                                break
                    if target_id is None:
                        target_translated = translate_entity_name(target_name)
                        for orig_name, nid in entity_name_to_id.items():
                            if translate_entity_name(orig_name) == target_translated:
                                target_id = nid
                                break

                    if source_id is not None and target_id is not None:
                        description = edge_data.get('description', '')
                        edge = {
                            'id': edge_id,
                            'source': source_id,
                            'target': target_id,
                            'label': description,  # 使用关系描述作为标签
                            'description': description,
                            'keywords': edge_data.get('keywords', ''),
                            'weight': edge_data.get('weight', 1),
                        }
                        edges.append(edge)
                        edge_id += 1

                logger.info(f"构建边数量: {len(edges)}")

            except Exception as e:
                logger.warning(f"从 LightRAG 获取边失败: {e}")
                # 继续返回已获取的节点，边可能为空

            return {
                'nodes': nodes,
                'edges': edges
            }

        except Exception as e:
            logger.error(f"获取图谱数据失败: {e}")
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            return None

    def _get_graph_data_from_json(self) -> Optional[Dict[str, Any]]:
        """
        从 JSON 文件获取图谱数据（降级方案）
        兼容多种 LightRAG 版本的存储文件名
        """
        try:
            import json
            from pathlib import Path

            working_dir = Path(self.working_dir)
            logger.info(f"从 JSON 获取图谱数据，工作目录: {working_dir}")

            nodes = []
            edges = []
            entity_name_to_id = {}

            # 兼容多种可能的实体存储文件名
            entity_files = [
                'kv_store_entity_chunks.json',  # 新版 LightRAG
                'kv_store_full_entities.json',  # 旧版 LightRAG
            ]
            
            entities_data = None
            for ef_name in entity_files:
                entities_file = working_dir / ef_name
                if entities_file.exists():
                    try:
                        with open(entities_file, 'r', encoding='utf-8') as f:
                            entities_data = json.load(f)
                            logger.info(f"读取实体文件: {ef_name}, 数据类型: {type(entities_data)}")
                            break
                    except Exception as e:
                        logger.warning(f"读取实体文件 {ef_name} 失败: {e}")
            
            if entities_data and isinstance(entities_data, dict):
                # 构建节点列表
                node_id = 0
                
                for entity_name, entity_info in entities_data.items():
                    translated_name = translate_entity_name(entity_name)
                    
                    # 处理不同格式的实体信息
                    if isinstance(entity_info, dict):
                        count = entity_info.get('count', 1)
                        description = entity_info.get('description', '')
                    else:
                        count = 1
                        description = ''

                    node = {
                        'id': node_id,
                        'label': translated_name,
                        'original_name': entity_name,
                        'count': count,
                        'weight': count,
                        'category': 0,
                        'description': description,
                    }
                    nodes.append(node)
                    entity_name_to_id[entity_name] = node_id
                    node_id += 1
                
                logger.info(f"构建节点数量: {len(nodes)}")
            else:
                logger.warning("未找到实体数据")

            # 读取关系详细信息
            relations_file = working_dir / 'kv_store_relation_chunks.json'
            if relations_file.exists():
                with open(relations_file, 'r', encoding='utf-8') as f:
                    relations_data = json.load(f)

                    edge_id = 0
                    for relation_key, relation_info in relations_data.items():
                        if '<SEP>' in relation_key:
                            source_name, target_name = relation_key.split('<SEP>', 1)
                            source_id = entity_name_to_id.get(source_name)
                            target_id = entity_name_to_id.get(target_name)

                            if source_id is not None and target_id is not None:
                                count = relation_info.get('count', 1) if isinstance(relation_info, dict) else 1
                                edges.append({
                                    'id': edge_id,
                                    'source': source_id,
                                    'target': target_id,
                                    'label': '',
                                    'count': count,
                                    'weight': count,
                                })
                                edge_id += 1

            return {'nodes': nodes, 'edges': edges}

        except Exception as e:
            logger.error(f"从 JSON 获取图谱数据失败: {e}")
            return None

    def get_graph_data(self) -> Optional[Dict[str, Any]]:
        """
        获取知识图谱完整数据（用于可视化）- 同步包装器

        Returns:
            图谱数据字典，包含 nodes 和 edges
        """
        # 直接使用 JSON 方式获取数据，避免异步问题
        return self._get_graph_data_from_json()

    async def compare_versions(self, base_version: str, compare_version: str) -> Dict[str, Any]:
        """
        对比两个版本的需求差异
        
        Args:
            base_version: 基准版本（如 "V1"）
            compare_version: 对比版本（如 "V3"）
            
        Returns:
            对比结果，包含统计信息和详细分析
        """
        import asyncio
        from openai import OpenAI
        
        try:
            logger.info(f"开始版本对比: {base_version} vs {compare_version}")
            
            # 获取图谱数据
            graph_data = self.get_graph_data()
            if not graph_data:
                return {
                    'success': False,
                    'error': '无法获取图谱数据'
                }
            
            # 获取知识图谱存储的原始数据
            working_dir = Path(self.working_dir)
            
            # 读取文档数据以获取版本信息
            docs_file = working_dir / 'kv_store_full_docs.json'
            docs_data = {}
            if docs_file.exists():
                with open(docs_file, 'r', encoding='utf-8') as f:
                    docs_data = json.load(f)
            
            # 读取实体数据
            entities_file = working_dir / 'kv_store_full_entities.json'
            entities_data = {}
            if entities_file.exists():
                with open(entities_file, 'r', encoding='utf-8') as f:
                    entities_data = json.load(f)
            
            # 读取关系数据
            relations_file = working_dir / 'kv_store_full_relations.json'
            relations_data = {}
            if relations_file.exists():
                with open(relations_file, 'r', encoding='utf-8') as f:
                    relations_data = json.load(f)
            
            # 构建对比提示词
            system_prompt = """你是一个需求分析专家，擅长对比不同版本的需求文档并找出差异。
请详细分析两个版本之间的差异，包括新增、修改和删除的需求。
用中文回答，使用 Markdown 格式。"""

            user_prompt = f"""请对比以下两个版本的需求文档：

基准版本: {base_version}
对比版本: {compare_version}

知识图谱统计信息:
- 实体数量: {len(entities_data)}
- 关系数量: {len(relations_data)}
- 文档数量: {len(docs_data)}

文档列表:
"""
            # 添加文档信息
            for doc_id, doc_info in list(docs_data.items())[:10]:  # 限制数量避免过长
                doc_title = doc_info.get('title', '未知文档') if isinstance(doc_info, dict) else str(doc_info)
                user_prompt += f"- {doc_title}\n"
            
            user_prompt += f"""

请分析并输出：
1. 新增需求（{compare_version} 中有但 {base_version} 中没有的）
2. 修改需求（两个版本中都存在但内容有变化的）
3. 删除需求（{base_version} 中有但 {compare_version} 中没有的）
4. 关键变更点总结

请以结构化格式输出，方便统计。"""

            # 调用 LLM 生成对比分析
            config = self._get_llm_config_sync()
            client = OpenAI(
                api_key=config['api_key'],
                base_url=config['base_url']
            )
            
            logger.info("正在调用 LLM 生成版本对比分析...")
            response = client.chat.completions.create(
                model=config['model_name'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=config.get('max_tokens', 4096),
                temperature=config.get('temperature', 0.7)
            )
            
            analysis = response.choices[0].message.content
            
            # 尝试从分析文本中提取统计数字
            added_count = 0
            modified_count = 0
            removed_count = 0
            
            # 简单的正则匹配来提取数字
            import re
            added_match = re.search(r'新增[:：]\s*(\d+)', analysis)
            if added_match:
                added_count = int(added_match.group(1))
            
            modified_match = re.search(r'修改[:：]\s*(\d+)', analysis)
            if modified_match:
                modified_count = int(modified_match.group(1))
            
            removed_match = re.search(r'删除[:：]\s*(\d+)', analysis)
            if removed_match:
                removed_count = int(removed_match.group(1))
            
            logger.info(f"版本对比完成: 新增={added_count}, 修改={modified_count}, 删除={removed_count}")

            return {
                'success': True,
                'base_version': base_version,
                'compare_version': compare_version,
                'analysis': analysis,
                'stats': {
                    'added': added_count,
                    'modified': modified_count,
                    'removed': removed_count
                }
            }

        except Exception as e:
            logger.error(f"版本对比失败: {e}")
            import traceback
            logger.error(f"堆栈: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_version(self, version_number: str, version_name: str = "", description: str = "", user=None) -> Dict[str, Any]:
        """创建知识图谱版本快照"""
        try:
            from .models import KnowledgeGraphVersion

            working_dir = Path(self.working_dir)

            # 读取文档数据
            docs_file = working_dir / 'kv_store_full_docs.json'
            docs_data = {}
            if docs_file.exists():
                with open(docs_file, 'r', encoding='utf-8') as f:
                    docs_data = json.load(f)

            # 读取实体数据
            entities_file = working_dir / 'kv_store_full_entities.json'
            entities_data = {}
            if entities_file.exists():
                with open(entities_file, 'r', encoding='utf-8') as f:
                    entities_data = json.load(f)

            # 读取关系数据
            relations_file = working_dir / 'kv_store_full_relations.json'
            relations_data = {}
            if relations_file.exists():
                with open(relations_file, 'r', encoding='utf-8') as f:
                    relations_data = json.load(f)

            # 创建版本记录
            version = KnowledgeGraphVersion.objects.create(
                graph_id=self.graph_id,
                version_number=version_number,
                version_name=version_name,
                description=description,
                created_by=user,
                node_count=len(entities_data),
                edge_count=len(relations_data),
                document_count=len(docs_data),
                document_ids=list(docs_data.keys()),
                snapshot_data={
                    'docs': docs_data,
                    'entities': entities_data,
                    'relations': relations_data,
                    'created_at': timezone.now().isoformat()
                }
            )

            logger.info(f"版本创建成功: {version_number}")
            return {
                'success': True,
                'version_id': version.id,
                'version_number': version_number,
                'stats': {
                    'nodes': len(entities_data),
                    'edges': len(relations_data),
                    'documents': len(docs_data)
                }
            }

        except Exception as e:
            logger.error(f"创建版本失败: {e}")
            import traceback
            logger.error(f"堆栈: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_versions(self) -> List[Dict[str, Any]]:
        """获取所有版本列表"""
        try:
            from .models import KnowledgeGraphVersion

            versions = KnowledgeGraphVersion.objects.filter(
                graph_id=self.graph_id
            ).order_by('-created_at')

            return [
                {
                    'id': v.id,
                    'version_number': v.version_number,
                    'version_name': v.version_name,
                    'description': v.description,
                    'node_count': v.node_count,
                    'edge_count': v.edge_count,
                    'document_count': v.document_count,
                    'created_at': v.created_at.isoformat(),
                    'created_by': v.created_by.username if v.created_by else None
                }
                for v in versions
            ]

        except Exception as e:
            logger.error(f"获取版本列表失败: {e}")
            return []

    def compare_versions_real(self, base_version_id: int, compare_version_id: int) -> Dict[str, Any]:
        """真正的版本对比 - 基于快照数据计算差异"""
        try:
            from .models import KnowledgeGraphVersion

            # 获取两个版本的快照
            base_version = KnowledgeGraphVersion.objects.get(id=base_version_id, graph_id=self.graph_id)
            compare_version = KnowledgeGraphVersion.objects.get(id=compare_version_id, graph_id=self.graph_id)

            base_snapshot = base_version.snapshot_data
            compare_snapshot = compare_version.snapshot_data

            # 计算实体差异
            base_entities = set(base_snapshot.get('entities', {}).keys())
            compare_entities = set(compare_snapshot.get('entities', {}).keys())

            added_entities = list(compare_entities - base_entities)
            removed_entities = list(base_entities - compare_entities)
            common_entities = base_entities & compare_entities

            # 计算关系差异
            base_relations = set(base_snapshot.get('relations', {}).keys())
            compare_relations = set(compare_snapshot.get('relations', {}).keys())

            added_relations = list(compare_relations - base_relations)
            removed_relations = list(base_relations - compare_relations)

            # 计算文档差异
            base_docs = set(base_snapshot.get('docs', {}).keys())
            compare_docs = set(compare_snapshot.get('docs', {}).keys())

            added_docs = list(compare_docs - base_docs)
            removed_docs = list(base_docs - compare_docs)

            # 构建对比报告
            analysis = f"""## 版本对比报告

### 对比版本
- 基准版本: {base_version.version_number} ({base_version.version_name or '未命名'})
- 对比版本: {compare_version.version_number} ({compare_version.version_name or '未命名'})

### 实体变化
- 新增实体: {len(added_entities)} 个
- 删除实体: {len(removed_entities)} 个
- 实体总数变化: {len(compare_entities)} - {len(base_entities)} = {len(compare_entities) - len(base_entities)}

### 关系变化
- 新增关系: {len(added_relations)} 个
- 删除关系: {len(removed_relations)} 个
- 关系总数变化: {len(compare_relations)} - {len(base_relations)} = {len(compare_relations) - len(base_relations)}

### 文档变化
- 新增文档: {len(added_docs)} 个
- 删除文档: {len(removed_docs)} 个
- 文档总数变化: {len(compare_docs)} - {len(base_docs)} = {len(compare_docs) - len(base_docs)}

### 详细变更
"""

            if added_entities:
                analysis += "\n**新增实体:**\n"
                for entity in added_entities[:10]:
                    entity_data = compare_snapshot['entities'].get(entity, {})
                    entity_desc = entity_data.get('description', '')[:50] if isinstance(entity_data, dict) else ''
                    analysis += f"- {entity}: {entity_desc}...\n"
                if len(added_entities) > 10:
                    analysis += f"- ... 还有 {len(added_entities) - 10} 个实体\n"

            if removed_entities:
                analysis += "\n**删除实体:**\n"
                for entity in removed_entities[:10]:
                    entity_data = base_snapshot['entities'].get(entity, {})
                    entity_desc = entity_data.get('description', '')[:50] if isinstance(entity_data, dict) else ''
                    analysis += f"- {entity}: {entity_desc}...\n"
                if len(removed_entities) > 10:
                    analysis += f"- ... 还有 {len(removed_entities) - 10} 个实体\n"

            if added_docs:
                analysis += "\n**新增文档:**\n"
                for doc in added_docs[:5]:
                    doc_data = compare_snapshot['docs'].get(doc, {})
                    doc_title = doc_data.get('title', doc) if isinstance(doc_data, dict) else doc
                    analysis += f"- {doc_title}\n"

            return {
                'success': True,
                'base_version': {
                    'id': base_version.id,
                    'number': base_version.version_number,
                    'name': base_version.version_name
                },
                'compare_version': {
                    'id': compare_version.id,
                    'number': compare_version.version_number,
                    'name': compare_version.version_name
                },
                'analysis': analysis,
                'stats': {
                    'entities': {
                        'added': len(added_entities),
                        'removed': len(removed_entities),
                        'total_change': len(compare_entities) - len(base_entities)
                    },
                    'relations': {
                        'added': len(added_relations),
                        'removed': len(removed_relations),
                        'total_change': len(compare_relations) - len(base_relations)
                    },
                    'documents': {
                        'added': len(added_docs),
                        'removed': len(removed_docs),
                        'total_change': len(compare_docs) - len(base_docs)
                    }
                },
                'details': {
                    'added_entities': added_entities,
                    'removed_entities': removed_entities,
                    'added_relations': added_relations,
                    'removed_relations': removed_relations,
                    'added_docs': added_docs,
                    'removed_docs': removed_docs
                }
            }

        except KnowledgeGraphVersion.DoesNotExist:
            return {
                'success': False,
                'error': '版本不存在'
            }
        except Exception as e:
            logger.error(f"版本对比失败: {e}")
            import traceback
            logger.error(f"堆栈: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
