"""
RAG (Retrieval-Augmented Generation) 服务
使用 LangChain + Chroma 实现文档索引和问答
"""
import os
import logging
from typing import Optional, Dict, Any, List
from django.conf import settings

logger = logging.getLogger(__name__)


class DashScopeEmbeddings:
    """通义千问 DashScope Embedding 实现"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-v3"):
        self.api_key = api_key
        self.model = model
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入多个文档"""
        import requests
        
        url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        embeddings = []
        # DashScope 支持批量，但为安全起见，逐个处理
        for text in texts:
            payload = {
                "model": self.model,
                "input": {
                    "texts": [text]
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if "output" in result and "embeddings" in result["output"]:
                embedding = result["output"]["embeddings"][0]["embedding"]
                embeddings.append(embedding)
            else:
                raise ValueError(f"Embedding API 返回错误: {result}")
                
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        result = self.embed_documents([text])
        return result[0]


class RAGService:
    """RAG 服务类 - 基于 LangChain + Chroma"""

    def __init__(self):
        self.persist_directory = os.path.join(settings.BASE_DIR, 'data', 'chroma_db')
        # 确保目录存在
        os.makedirs(self.persist_directory, exist_ok=True)

    def _get_model_config(self, user=None) -> Optional[Dict[str, Any]]:
        """获取 AI 模型配置 - 优先使用 knowledge_base 角色的配置"""
        try:
            from apps.requirement_analysis.models import AIModelConfig

            # 优先查找 knowledge_base 角色的配置（系统级配置，不限制创建者）
            kb_query = {'is_active': True, 'role': 'knowledge_base'}
            config = AIModelConfig.objects.filter(**kb_query).first()

            if not config:
                # 如果没有 knowledge_base 配置，使用任意一个激活的配置作为 fallback
                query = {'is_active': True}
                if user:
                    query['created_by'] = user
                config = AIModelConfig.objects.filter(**query).first()
                if config:
                    logger.warning(f"未找到 knowledge_base 角色的模型配置，使用 {config.role} 角色配置 '{config.name}' 作为替代")

            if config:
                return {
                    'model_type': config.model_type,
                    'model_name': config.model_name,
                    'api_key': config.api_key,
                    'api_base': config.base_url,
                    'temperature': getattr(config, 'temperature', 0.7),
                    'top_p': getattr(config, 'top_p', 0.9)
                }
            else:
                logger.error("没有找到任何激活的 AI 模型配置")
        except Exception as e:
            logger.error(f"获取模型配置失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        return None

    def _get_vision_model_config(self, user=None) -> Optional[Dict[str, Any]]:
        """获取支持视觉的 AI 模型配置

        如果当前配置的模型不支持视觉，自动查找同类型的视觉模型
        """
        try:
            from apps.requirement_analysis.models import AIModelConfig

            # 首先获取基础模型配置
            base_config = self._get_model_config(user)
            if not base_config:
                return None

            model_name = base_config.get('model_name', '').lower()
            model_type = base_config.get('model_type', '').lower()

            # 检查当前模型是否已经支持视觉
            if self._is_vision_model(model_name):
                logger.info(f"当前模型 {model_name} 已支持视觉，直接使用")
                return base_config

            # 当前模型不支持视觉，需要查找同类型的视觉模型
            logger.info(f"当前模型 {model_name} 不支持视觉，尝试查找同类型视觉模型")

            # 构建查询条件
            query = {'is_active': True}
            if user:
                query['created_by'] = user

            # 根据模型类型查找对应的视觉模型
            vision_model_name = None

            if model_type == 'dashscope' or 'qwen' in model_name:
                # 通义千问系列，查找 VL 模型
                vision_candidates = ['qwen-vl-max', 'qwen-vl-plus']
                for candidate in vision_candidates:
                    vision_config = AIModelConfig.objects.filter(
                        **query,
                        model_name__icontains=candidate
                    ).first()
                    if vision_config:
                        vision_model_name = vision_config.model_name
                        break

                # 如果没找到专用配置，使用默认的 VL 模型名称
                if not vision_model_name:
                    vision_model_name = 'qwen-vl-plus'
                    logger.info(f"未找到 VL 模型配置，使用默认模型: {vision_model_name}")

            elif 'gpt' in model_name or 'openai' in model_type:
                # OpenAI 系列，查找 GPT-4V
                vision_candidates = ['gpt-4o', 'gpt-4-vision-preview']
                for candidate in vision_candidates:
                    vision_config = AIModelConfig.objects.filter(
                        **query,
                        model_name__icontains=candidate
                    ).first()
                    if vision_config:
                        vision_model_name = vision_config.model_name
                        break

                if not vision_model_name:
                    vision_model_name = 'gpt-4-vision-preview'
                    logger.info(f"未找到 GPT-4V 模型配置，使用默认模型: {vision_model_name}")

            else:
                logger.warning(f"不支持的模型类型: {model_type}，无法自动选择视觉模型")
                return None

            # 返回视觉模型配置（使用基础配置的 API Key 和 Base URL）
            vision_config = base_config.copy()
            vision_config['model_name'] = vision_model_name
            logger.info(f"自动选择视觉模型: {vision_model_name}")
            return vision_config

        except Exception as e:
            logger.error(f"获取视觉模型配置失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _is_vision_model(self, model_name: str) -> bool:
        """判断模型是否支持视觉"""
        vision_keywords = ['vl', 'vision', 'gpt-4o', '4o']
        model_name_lower = model_name.lower()
        return any(keyword in model_name_lower for keyword in vision_keywords)

    def _get_prompt_template(self) -> str:
        """获取知识库问答提示词配置"""
        try:
            from apps.requirement_analysis.models import PromptConfig

            # 获取启用的知识库提示词配置
            config = PromptConfig.get_active_config('knowledge_base')
            if config and config.content:
                logger.info(f"使用配置的知识库提示词: {config.name}")
                # 确保提示词包含必要的变量
                content = config.content
                if '{context}' not in content:
                    content += "\n\n文档内容：\n{context}"
                if '{question}' not in content:
                    content += "\n\n问题：\n{question}"
                return content
        except Exception as e:
            logger.warning(f"获取知识库提示词配置失败: {str(e)}")

        # 默认提示词
        return """你是一个专业的文档问答助手。请严格基于以下文档内容回答问题。

重要要求：
1. 如果文档中有明确的数字、时间、限制等具体信息，请直接给出精确答案
2. 优先回答问题的核心要点，不要罗列无关信息
3. 如果涉及规定、限制、标准等，请给出具体的数值或明确结论
4. 如果文档中没有明确答案，请直接说明"文档中未明确说明"

文档内容：
{context}

问题：{question}

请给出精确、简洁的回答："""

    def _is_dashscope(self, model_config: Dict[str, Any]) -> bool:
        """判断是否是通义千问/DashScope"""
        model_name = model_config.get('model_name', '')
        api_base = model_config.get('api_base', '')
        return 'qwen' in model_name.lower() or 'dashscope' in api_base.lower()

    def _get_embeddings(self, model_config: Dict[str, Any]):
        """获取 Embedding 模型"""
        if self._is_dashscope(model_config):
            # 使用通义千问 DashScope Embedding
            return DashScopeEmbeddings(
                api_key=model_config.get('api_key'),
                model='text-embedding-v3'
            )
        else:
            # 使用 OpenAI Embedding
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                openai_api_key=model_config.get('api_key'),
                openai_api_base=model_config.get('api_base'),
                model='text-embedding-ada-002'
            )

    def _extract_text(self, file_path: str, file_type: str, user=None) -> str:
        """从文档中提取文本

        Args:
            file_path: 文件路径
            file_type: 文件类型
            user: 当前用户，用于 AI 图片识别

        Returns:
            提取的文本内容
        """
        try:
            if file_type == 'pdf':
                try:
                    import pdfplumber
                    text = ""
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                    return text
                except ImportError:
                    logger.error("pdfplumber 未安装，尝试使用其他方式")
                    return self._read_as_text(file_path)
            elif file_type in ['doc', 'docx']:
                return self._extract_docx_text(file_path, user)
            else:
                return self._read_as_text(file_path)
        except Exception as e:
            logger.error(f"提取文本失败 {file_path}: {str(e)}")
            return self._read_as_text(file_path)

    def _read_as_text(self, file_path: str) -> str:
        """作为纯文本读取"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
            except:
                with open(file_path, 'rb') as f:
                    return f.read().decode('utf-8', errors='ignore')

    def _extract_docx_text(self, file_path: str, user=None) -> str:
        """提取 Word 文档内容，包括表格和图片说明

        Args:
            file_path: 文档路径
            user: 当前用户，用于 AI 图片识别

        Returns:
            提取的文本内容
        """
        try:
            from docx import Document

            doc = Document(file_path)
            text_parts = []

            # 导入 docx 子模块
            import docx.text.paragraph
            import docx.table

            # 遍历文档中的所有元素
            for element in doc.element.body:
                # 处理段落
                if element.tag.endswith('p'):
                    paragraph = docx.text.paragraph.Paragraph(element, doc)
                    if paragraph.text.strip():
                        text_parts.append(paragraph.text)

                # 处理表格
                elif element.tag.endswith('tbl'):
                    table = docx.table.Table(element, doc)
                    table_text = self._extract_table_text(table)
                    if table_text:
                        text_parts.append(f"\n【表格内容】\n{table_text}\n")

            # 提取图片信息
            image_count = len(doc.inline_shapes)
            if image_count > 0:
                text_parts.append(f"\n【文档包含 {image_count} 张图片】")

                # 尝试提取图片并 OCR
                try:
                    image_texts = self._extract_images_from_docx(doc, file_path, user)
                    if image_texts:
                        text_parts.append("\n【图片内容识别】")
                        for i, img_text in enumerate(image_texts, 1):
                            if img_text.strip():
                                text_parts.append(f"图片{i}: {img_text}")
                except Exception as e:
                    logger.warning(f"图片提取失败: {str(e)}")

            return '\n'.join(text_parts)

        except ImportError:
            logger.warning("python-docx 未安装，使用 docx2txt 作为备选")
            try:
                import docx2txt
                return docx2txt.process(file_path)
            except ImportError:
                logger.error("docx2txt 未安装，尝试使用其他方式")
                return self._read_as_text(file_path)
        except Exception as e:
            logger.error(f"提取 Word 文档失败: {str(e)}")
            return self._read_as_text(file_path)

    def _extract_table_text(self, table) -> str:
        """提取表格内容为文本格式

        Args:
            table: docx 表格对象

        Returns:
            表格的文本表示
        """
        try:
            rows_text = []
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    # 提取单元格文本，去除多余空白
                    cell_text = cell.text.strip().replace('\n', ' ')
                    row_text.append(cell_text)
                rows_text.append(' | '.join(row_text))

            return '\n'.join(rows_text)
        except Exception as e:
            logger.warning(f"提取表格内容失败: {str(e)}")
            return ""

    def _extract_images_from_docx(self, doc, file_path: str, user=None) -> List[str]:
        """从 Word 文档中提取图片并进行 AI 识别

        Args:
            doc: docx Document 对象
            file_path: 文档路径
            user: 当前用户，用于获取 AI 模型配置

        Returns:
            图片中的文本列表
        """
        image_texts = []

        try:
            # 导入必要的库
            from PIL import Image
            import io

            # 获取文档中的图片关系
            rels = doc.part.rels

            for rel in rels.values():
                # 检查是否是图片类型
                if "image" in rel.target_ref:
                    try:
                        # 获取图片数据
                        image_part = rel.target_part
                        image_bytes = image_part.blob

                        # 转换为 PIL Image
                        image = Image.open(io.BytesIO(image_bytes))

                        # 进行 AI 识别
                        ai_text = self._ocr_image(image, user)
                        if ai_text.strip():
                            image_texts.append(ai_text)

                    except Exception as e:
                        logger.warning(f"处理单张图片失败: {str(e)}")
                        continue

        except ImportError as e:
            logger.warning(f"图片处理库未安装: {str(e)}")
        except Exception as e:
            logger.error(f"提取图片失败: {str(e)}")

        return image_texts

    def _ocr_image(self, image, user=None) -> str:
        """使用多模态 AI 理解图片内容

        Args:
            image: PIL Image 对象
            user: 当前用户，用于获取模型配置

        Returns:
            AI 对图片的描述和文字提取
        """
        try:
            import base64
            import io
            import requests

            # 获取视觉模型配置（自动选择支持图片的模型）
            model_config = self._get_vision_model_config(user)
            if not model_config:
                logger.warning("未找到可用的视觉 AI 模型配置，跳过图片理解")
                return ""

            # 将图片转换为 base64
            buffered = io.BytesIO()
            # 转换为 RGB 模式（避免 PNG 透明通道问题）
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # 构建提示词
            prompt = "请详细描述这张图片的内容。如果图片包含文字，请提取所有文字内容；如果是图表，请说明图表类型和关键数据；如果是截图，请描述界面内容和功能。请用中文回答。"

            # 根据模型类型调用不同的 API
            if self._is_dashscope(model_config):
                # 使用通义千问多模态模型
                return self._call_qwen_vl(img_base64, prompt, model_config)
            else:
                # 使用 OpenAI GPT-4V
                return self._call_gpt4v(img_base64, prompt, model_config)

        except Exception as e:
            logger.warning(f"AI 图片理解失败: {str(e)}")
            return ""

    def _call_qwen_vl(self, img_base64: str, prompt: str, model_config: Dict[str, Any]) -> str:
        """调用通义千问多模态模型

        Args:
            img_base64: base64 编码的图片
            prompt: 提示词
            model_config: 模型配置

        Returns:
            AI 的回复内容
        """
        try:
            import requests

            api_key = model_config.get('api_key')
            model_name = model_config.get('model_name', 'qwen-vl-plus')

            # 确保使用视觉模型
            if 'vl' not in model_name.lower():
                model_name = 'qwen-vl-plus'

            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model_name,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"image": f"data:image/jpeg;base64,{img_base64}"},
                                {"text": prompt}
                            ]
                        }
                    ]
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                result = response.json()
                if 'output' in result and 'choices' in result['output']:
                    content = result['output']['choices'][0]['message']['content']
                    # 处理 content 可能是列表的情况
                    if isinstance(content, list):
                        # 提取列表中的文本内容
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                text_parts.append(item['text'])
                            elif isinstance(item, str):
                                text_parts.append(item)
                        return '\n'.join(text_parts)
                    return content
                else:
                    logger.warning(f"通义千问返回格式异常: {result}")
                    return ""
            else:
                logger.warning(f"通义千问 API 调用失败: {response.status_code} - {response.text}")
                return ""

        except Exception as e:
            logger.error(f"调用通义千问失败: {str(e)}")
            return ""

    def _call_gpt4v(self, img_base64: str, prompt: str, model_config: Dict[str, Any]) -> str:
        """调用 OpenAI GPT-4V 模型

        Args:
            img_base64: base64 编码的图片
            prompt: 提示词
            model_config: 模型配置

        Returns:
            AI 的回复内容
        """
        try:
            import requests

            api_key = model_config.get('api_key')
            api_base = model_config.get('api_base', 'https://api.openai.com/v1')
            model_name = model_config.get('model_name', 'gpt-4-vision-preview')

            # 确保使用视觉模型
            if 'vision' not in model_name.lower() and 'gpt-4o' not in model_name.lower():
                model_name = 'gpt-4-vision-preview'

            url = f"{api_base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }

            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
                else:
                    logger.warning(f"GPT-4V 返回格式异常: {result}")
                    return ""
            else:
                logger.warning(f"GPT-4V API 调用失败: {response.status_code} - {response.text}")
                return ""

        except Exception as e:
            logger.error(f"调用 GPT-4V 失败: {str(e)}")
            return ""

    def _split_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200, split_type: str = 'semantic') -> List[str]:
        """将文本分割成块

        Args:
            text: 文本内容
            chunk_size: 切块大小
            chunk_overlap: 重叠大小
            split_type: 切分方式，'semantic' 为语义切分，'fixed' 为固定长度切分
        """
        if not text:
            return []

        if split_type == 'semantic':
            # 使用 LangChain 的 RecursiveCharacterTextSplitter 进行语义切分
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter

                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separators=["\n\n", "\n", "。", "；", " ", ""],
                    length_function=len,
                    is_separator_regex=False
                )

                chunks = text_splitter.split_text(text)
                logger.info(f"使用语义切分，共 {len(chunks)} 块")
                return chunks
            except ImportError as e:
                logger.warning(f"RecursiveCharacterTextSplitter 未安装: {e}，使用简单切分")

        # 固定长度切分（降级方案）
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - chunk_overlap

        return chunks

    def generate_index(self, file_path: str, file_type: str, user=None, document_id=None, split_type: str = 'semantic') -> Dict[str, Any]:
        """
        生成文档索引

        Args:
            file_path: 文档文件路径
            file_type: 文件类型
            user: 当前用户
            document_id: 文档ID，用于作为 collection 名称
            split_type: 切分方式，'semantic' 为语义切分，'fixed' 为固定长度切分

        Returns:
            索引结果
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise ValueError(f"文件不存在: {file_path}")

            logger.info(f"开始处理文档: {file_path}, 切分方式: {split_type}")

            # 获取模型配置
            model_config = self._get_model_config(user)
            if not model_config:
                raise ValueError("未找到可用的 AI 模型配置")

            # 提取文本（传递 user 参数用于 AI 图片识别）
            text = self._extract_text(file_path, file_type, user)
            if not text.strip():
                raise ValueError("无法从文档中提取文本")

            logger.info(f"文本提取成功，长度: {len(text)} 字符")

            # 文本分块
            chunks = self._split_text(text, chunk_size=1000, chunk_overlap=200, split_type=split_type)
            logger.info(f"文档分块完成，共 {len(chunks)} 块")

            # 导入必要的库
            from langchain_chroma import Chroma
            from langchain_core.documents import Document

            # 获取 embeddings
            embeddings = self._get_embeddings(model_config)

            # 创建 Document 对象列表
            documents = [
                Document(page_content=chunk, metadata={"chunk_index": i, "source": file_path})
                for i, chunk in enumerate(chunks)
            ]

            # 使用 document_id 作为 collection 名称，实现文档隔离
            collection_name = f"doc_{document_id}" if document_id else "default"

            # 创建 vector store
            # 新版本的 Chroma 使用 persist_directory 参数自动持久化
            vector_store = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=self.persist_directory,
                collection_name=collection_name
            )

            logger.info(f"文档索引生成成功: {file_path}, collection: {collection_name}")

            return {
                'success': True,
                'index_id': collection_name,
                'index_data': {
                    'chunks_count': len(chunks),
                    'text_length': len(text),
                    'file_path': file_path
                },
                'pages': len(chunks)
            }

        except Exception as e:
            logger.error(f"生成索引失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
            }

    def query_document(self, question: str, index_data: Dict[str, Any], user=None, document=None) -> Dict[str, Any]:
        """
        基于索引回答问题

        Args:
            question: 用户问题
            index_data: 文档索引数据（包含 index_id）
            user: 当前用户
            document: 文档对象

        Returns:
            回答结果
        """
        try:
            # 获取索引 ID
            collection_name = index_data.get('index_id') if isinstance(index_data, dict) else None

            if not collection_name and document:
                collection_name = f"doc_{document.id}"

            if not collection_name:
                return {
                    'success': False,
                    'error': '未找到有效的索引 ID'
                }

            logger.info(f"开始查询，collection: {collection_name}, 问题: {question}")

            # 获取模型配置
            model_config = self._get_model_config(user)
            if not model_config:
                return {
                    'success': False,
                    'error': '未找到可用的 AI 模型配置'
                }

            # 导入必要的库
            from langchain_openai import ChatOpenAI
            from langchain_chroma import Chroma
            from langchain_core.prompts import PromptTemplate
            from langchain_core.runnables import RunnablePassthrough
            from langchain_core.output_parsers import StrOutputParser

            # 获取 embeddings
            embeddings = self._get_embeddings(model_config)

            # 加载 vector store
            vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings,
                collection_name=collection_name
            )

            # 获取 LLM
            llm = ChatOpenAI(
                openai_api_key=model_config.get('api_key'),
                openai_api_base=model_config.get('api_base'),
                model_name=model_config.get('model_name', 'gpt-3.5-turbo'),
                temperature=model_config.get('temperature', 0.7),
                model_kwargs={
                    'top_p': model_config.get('top_p', 0.9)
                }
            )

            # 创建检索器 - 使用 MMR 增加多样性，提高检索质量
            retriever = vector_store.as_retriever(
                search_type="mmr",  # 最大边际相关性，平衡相关性和多样性
                search_kwargs={
                    "k": 5,  # 返回 5 个结果
                    "fetch_k": 10,  # 从 10 个候选中选择
                    "lambda_mult": 0.7  # 相关性权重（0-1，越高越注重相关性）
                }
            )

            # 获取提示词配置
            prompt_template = self._get_prompt_template()

            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )

            # 使用 LCEL 构建 RAG 链
            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | PROMPT
                | llm
                | StrOutputParser()
            )

            # 执行查询
            answer = rag_chain.invoke(question)

            # 获取来源文档
            source_docs = retriever.invoke(question)

            # 提取来源信息
            sources = []
            for doc in source_docs:
                sources.append({
                    'content': doc.page_content[:200] + '...' if len(doc.page_content) > 200 else doc.page_content,
                    'metadata': doc.metadata
                })

            logger.info(f"查询完成，找到 {len(sources)} 个相关文本块")

            return {
                'success': True,
                'answer': answer,
                'retrieved_pages': sources
            }

        except Exception as e:
            logger.error(f"问答失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
            }

    def get_vector_storage_uuid(self, document_id: int) -> Optional[str]:
        """获取文档对应的向量存储目录 UUID"""
        try:
            import sqlite3
            import os

            collection_name = f"doc_{document_id}"
            db_path = os.path.join(self.persist_directory, 'chroma.sqlite3')

            if not os.path.exists(db_path):
                return None

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 获取 collection ID
            cursor.execute("SELECT id FROM collections WHERE name = ?;", (collection_name,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return None

            collection_uuid = result[0]

            # 获取 vector segment ID (HNSW 存储目录)
            cursor.execute(
                "SELECT id FROM segments WHERE collection = ? AND type LIKE '%hnsw-local-persisted%';",
                (collection_uuid,)
            )
            result = cursor.fetchone()
            conn.close()

            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"获取向量存储 UUID 失败: {str(e)}")
            return None

    def delete_index(self, document_id: int) -> bool:
        """删除文档索引"""
        try:
            collection_name = f"doc_{document_id}"
            import chromadb
            client = chromadb.PersistentClient(path=self.persist_directory)
            try:
                client.delete_collection(name=collection_name)
                logger.info(f"删除索引成功: {collection_name}")
            except Exception as e:
                logger.warning(f"删除索引时出错（可能不存在）: {str(e)}")
            return True
        except Exception as e:
            logger.error(f"删除索引失败: {str(e)}")
            return False

    def retrieve_documents(self, question: str, index_data: Dict[str, Any], user=None, document=None) -> List[Dict[str, Any]]:
        """检索相关文档片段"""
        try:
            # 获取索引 ID
            collection_name = index_data.get('index_id') if isinstance(index_data, dict) else None
            if not collection_name and document:
                collection_name = f"doc_{document.id}"
            if not collection_name:
                return []

            # 获取模型配置
            model_config = self._get_model_config(user)
            if not model_config:
                return []

            # 导入必要的库
            from langchain_chroma import Chroma

            # 获取 embeddings
            embeddings = self._get_embeddings(model_config)

            # 加载 vector store
            vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings,
                collection_name=collection_name
            )

            # 创建检索器
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )

            # 检索相关文档
            source_docs = retriever.invoke(question)

            # 提取来源信息
            sources = []
            for doc in source_docs:
                sources.append({
                    'content': doc.page_content[:200] + '...' if len(doc.page_content) > 200 else doc.page_content,
                    'metadata': doc.metadata
                })

            return sources
        except Exception as e:
            logger.error(f"检索文档失败: {str(e)}")
            return []

    def stream_query(self, question: str, index_data: Dict[str, Any], user=None, document=None):
        """流式查询生成回答"""
        try:
            # 获取索引 ID
            collection_name = index_data.get('index_id') if isinstance(index_data, dict) else None
            if not collection_name and document:
                collection_name = f"doc_{document.id}"
            if not collection_name:
                yield "未找到有效的索引 ID"
                return

            # 获取模型配置
            model_config = self._get_model_config(user)
            if not model_config:
                yield "未找到可用的 AI 模型配置"
                return

            # 导入必要的库
            from langchain_openai import ChatOpenAI
            from langchain_chroma import Chroma
            from langchain_core.prompts import PromptTemplate
            from langchain_core.runnables import RunnablePassthrough

            # 获取 embeddings
            embeddings = self._get_embeddings(model_config)

            # 加载 vector store
            vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings,
                collection_name=collection_name
            )

            # 创建检索器
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )

            # 自定义提示模板
            prompt_template = """基于以下文档内容回答问题。如果文档中没有相关信息，请明确说明。

文档内容：
{context}

问题：{question}

请提供准确、简洁的回答："""

            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )

            # 使用 LCEL 构建 RAG 链
            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            # 获取相关文档
            docs = retriever.invoke(question)
            context = format_docs(docs)

            # 获取 LLM 并启用流式输出
            llm = ChatOpenAI(
                openai_api_key=model_config.get('api_key'),
                openai_api_base=model_config.get('api_base'),
                model_name=model_config.get('model_name', 'gpt-3.5-turbo'),
                temperature=model_config.get('temperature', 0.7),
                streaming=True,
                model_kwargs={
                    'top_p': model_config.get('top_p', 0.9)
                }
            )

            # 构建消息
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content="你是一个专业的文档问答助手，基于提供的文档内容回答问题。"),
                HumanMessage(content=PROMPT.format(context=context, question=question))
            ]

            # 流式生成
            for chunk in llm.stream(messages):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            logger.error(f"流式查询失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            yield f"生成回答时出错: {str(e)}"

    def get_document_chunks(self, document_id: int, user=None) -> Dict[str, Any]:
        """获取文档的所有切块内容

        Args:
            document_id: 文档ID
            user: 当前用户

        Returns:
            包含切块内容的字典
        """
        try:
            collection_name = f"doc_{document_id}"

            # 获取模型配置
            model_config = self._get_model_config(user)
            if not model_config:
                return {
                    'success': False,
                    'error': '未找到可用的 AI 模型配置'
                }

            # 导入必要的库
            from langchain_chroma import Chroma

            # 获取 embeddings
            embeddings = self._get_embeddings(model_config)

            # 加载 vector store
            vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings,
                collection_name=collection_name
            )

            # 获取所有文档
            # 使用空查询获取所有文档，或者使用 get() 方法
            all_docs = vector_store.get()

            if not all_docs or not all_docs.get('documents'):
                return {
                    'success': True,
                    'chunks': [],
                    'total': 0
                }

            # 构建切块列表
            chunks = []
            for i, doc in enumerate(all_docs['documents']):
                metadata = all_docs['metadatas'][i] if all_docs.get('metadatas') and i < len(all_docs['metadatas']) else {}
                chunks.append({
                    'index': metadata.get('chunk_index', i),
                    'content': doc
                })

            # 按索引排序
            chunks.sort(key=lambda x: x['index'])

            return {
                'success': True,
                'chunks': chunks,
                'total': len(chunks)
            }

        except Exception as e:
            logger.error(f"获取文档切块失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
            }


# 全局服务实例
rag_service = RAGService()
