"""
AI 评分量表生成管理视图
调用配置中心「知识库问答」角色的AI模型生成评分量表和学习心得
"""
import os
import json
import logging
import asyncio
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import AIRubricRecord

logger = logging.getLogger(__name__)

# ========== 量表基础模板（作为 fallback 和参考）==========
BASE_RUBRIC_TEMPLATE = """你是一位资深的教育评估专家，擅长设计教学评价量表。

请根据用户上传的教学内容文档，生成一份完整的【评分量表】。

## 量表的通用框架要求：

### 一级指标分类（必须包含以下类别）：
1. 学习者分析与沟通
2. 学习路径/地图设计
3. 教学方案创新
4. 综合评价

### 输出格式要求：
请严格按以下 JSON 格式输出，不要输出任何其他内容：
```json
[
  {"level1": "一级指标名", "level2": "二级指标名", "desc": "详细描述说明"},
  ...
]
```

### 设计原则：
- 每个一级指标下包含 3-8 个二级指标
- 总共约 15-25 个评分点
- 描述要具体、可操作、可量化
- 如果上传了文档，指标要紧扣文档中的教学内容和主题
- 每条描述控制在 30-60 字之间
"""

NOTES_PROMPT_TEMPLATE = """你是一位教育学研究者，擅长撰写教学反思与学习心得。

请根据上述评分量表的主题和内容，为完成该课程/培训的学习者生成学习心得。

## 要求：
1. 共生成 {note_count} 条心得
2. 其中 {pass_count} 条是"得分心得"（正面积极的反思），{fail_count} 条是"不得分心得"（指出问题或困惑的）
3. 每条心得包含：title（标题，10-25字）和 body（正文，{note_length}字左右）
4. 得分心得应体现：深度理解、实践应用、认知转变等积极面
5. 不得分心得应体现：困惑、质疑、资源限制等真实挑战
6. 心得要围绕量表主题展开，不要泛泛而谈
7. 语言风格：第一人称，像一位一线教师的真实感悟

## 输出格式（严格 JSON，不要输出其他内容）：
```json
[
  {{"title": "心得标题", "body": "心得正文", "type": "pass"}},
  ...
]
```
"""


# ========== 文件内容提取 ==========

def extract_file_content(uploaded_file):
    """
    从上传的文件中提取文本内容
    支持: .txt, .pdf, .docx, .png/.jpg (OCR)
    """
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    content_bytes = uploaded_file.read()

    try:
        if ext == '.txt':
            return content_bytes.decode('utf-8', errors='ignore')

        elif ext == '.pdf':
            return _extract_pdf_text(content_bytes)

        elif ext in ('.docx',):
            return _extract_docx_text(content_bytes)

        elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'):
            return _extract_image_text(content_bytes, uploaded_file.name)

        else:
            # 尝试以文本读取
            try:
                return content_bytes.decode('utf-8', errors='ignore')
            except Exception:
                return f"[无法解析的文件类型: {ext}]"
    except Exception as e:
        logger.warning(f"[AI量表] 文件提取失败: {e}")
        return f"[文件提取失败: {str(e)}]"


def _extract_pdf_text(content_bytes):
    """提取PDF文本"""
    try:
        import io
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(content_bytes))
        texts = []
        for page in reader.pages:
            text = page.extract_text() or ''
            texts.append(text)
        result = '\n'.join(texts)
        return result[:8000]  # 限制长度避免token过多
    except ImportError:
        logger.warning("PyPDF2 未安装，无法提取 PDF")
        return "[PDF提取需要安装PyPDF2: pip install PyPDF2]"
    except Exception as e:
        return f"[PDF提取失败: {e}]"


def _extract_docx_text(content_bytes):
    """提取DOCX文本"""
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(content_bytes))
        paragraphs = [p.text for p in doc.paragraphs]
        result = '\n'.join(paragraphs)
        return result[:8000]
    except ImportError:
        logger.warning("python-docx 未安装，无法提取 DOCX")
        return "[DOCX提取需要安装python-docx: pip install python-docx]"
    except Exception as e:
        return f"[DOCX提取失败: {e}]"


def _extract_image_text(content_bytes, filename):
    """图片 OCR 提取文本"""
    try:
        import base64
        import httpx
        # 尝试调用通用的OCR服务或返回占位符
        # 这里使用简单策略：保存图片信息供AI分析
        b64 = base64.b64encode(content_bytes).decode('utf-8')
        return f"[已上传图片: {filename}，图片大小: {len(content_bytes)} 字节，Base64长度: {len(b64)}]"
    except Exception as e:
        return f"[图片文件: {filename}，大小: {len(content_bytes)} 字节]"


# ========== AI 配置获取 ==========

def get_knowledge_base_config():
    """获取「知识库问答」角色的 AI 模型配置"""
    from apps.requirement_analysis.models import AIModelConfig
    config = AIModelConfig.objects.filter(
        role='knowledge_base',
        is_active=True,
    ).order_by('-updated_at').first()

    if not config:
        # Fallback: 尝试任意可用配置
        config = AIModelConfig.objects.filter(
            is_active=True,
        ).order_by('-updated_at').first()

    return config


# ========== 视图函数 ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rubric_records(request):
    """获取AI量表生成记录列表"""
    records = AIRubricRecord.objects.filter(user=request.user).order_by('-created_at')
    status_filter = request.query_params.get('status')
    search = request.query_params.get('search', '')

    if status_filter and status_filter != 'all':
        records = records.filter(status=status_filter)
    if search:
        records = records.filter(name__icontains=search)

    data = [r.to_list_dict() for r in records]

    stats = {
        'total': data.__len__(),
        'done': len([r for r in data if r['status'] == 'done']),
        'running': len([r for r in data if r['status'] == 'running']),
        'error': len([r for r in data if r['status'] == 'error']),
    }

    return Response({
        'success': True,
        'data': data,
        'stats': stats,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rubric_detail(request, record_id):
    """获取单条记录详情"""
    try:
        record = AIRubricRecord.objects.get(id=record_id, user=request.user)
    except AIRubricRecord.DoesNotExist:
        return Response({'success': False, 'error': '记录不存在'}, status=status.HTTP_404_NOT_FOUND)

    result = {
        'id': record.id,
        'name': record.name,
        'status': record.status,
        'source_file_name': record.source_file_name,
        'note_count': record.note_count,
        'pass_ratio': record.pass_ratio,
        'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'rubric_data': record.rubric_data or [],
        'notes_data': record.notes_data or [],
        'rubric_url': record.rubric_file.url if record.rubric_file else None,
        'notes_url': record.notes_file.url if record.notes_file else None,
    }
    return Response({'success': True, 'data': result})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rubric_generate(request):
    """
    创建并执行量表生成任务
    
    调用配置中心「知识库问答」角色的 AI 模型来生成量表和心得。
    若 AI 调用失败则降级到本地模板。
    
    重要: 先创建记录并提交事务(让前端能立即看到running状态)，再执行耗时AI调用。
    """
    from django.db import transaction

    user = request.user
    name = request.POST.get('name') or f"量表生成_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    note_count = int(request.POST.get('note_count', 20))
    pass_ratio = float(request.POST.get('pass_ratio', 0.6))
    note_length = int(request.POST.get('note_length', 300))

    uploaded_file = request.FILES.get('file')
    file_content = None

    # 处理上传的源文件（必须在创建记录之前提取内容）
    if uploaded_file:
        record_source_name = uploaded_file.name
        try:
            file_content = extract_file_content(uploaded_file)
            logger.info(f"[AI量表] 文件内容提取成功: {uploaded_file.name}, "
                        f"内容长度={len(file_content) if file_content else 0}")
        except Exception as e:
            logger.error(f"[AI量表] 文件内容提取异常: {e}", exc_info=True)
            file_content = None

        # 重置文件指针（后续保存文件需要）
        if hasattr(uploaded_file, 'seek'):
            try:
                uploaded_file.seek(0)
            except Exception:
                pass

    # ====== 第一步：创建记录并立即提交事务 ======
    with transaction.atomic():
        record = AIRubricRecord.objects.create(
            user=user,
            name=name,
            status='running',
            note_count=note_count,
            pass_ratio=pass_ratio,
        )

        if uploaded_file:
            record.source_file_name = uploaded_file.name
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_name = f"{timestamp}_{uploaded_file.name[:50]}"
            record.source_file.save(safe_name, uploaded_file, save=False)
            record.save()

    logger.info(f"[AI量表] 记录已创建并提交, id={record.id}, name={name}, status=running")

    # ====== 调用 AI 生成 ======
    try:
        rubric_data, notes_data = _ai_generate_rubric_and_notes(
            file_content=file_content,
            file_name=uploaded_file.name if uploaded_file else None,
            note_count=note_count,
            pass_ratio=pass_ratio,
            task_name=name,
            note_length=note_length,
        )

        record.rubric_data = rubric_data
        record.notes_data = notes_data
        record.status = 'done'
        record.save()

        logger.info(f"[AI量表] AI 生成成功: 用户={user.username}, 任务={name}, "
                     f"量表{len(rubric_data)}项, 心得{len(notes_data)}条")

        return Response({
            'success': True,
            'data': {
                'id': record.id,
                'name': record.name,
                'status': 'done',
                'rubric_count': len(rubric_data),
                'notes_count': len(notes_data),
                'source': 'ai_generated',
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"[AI量表] AI 生成失败，降级到模板: {e}", exc_info=True)

        # ====== 降级: 使用本地模板（标记为 error 状态）======
        rubric_data = [{'seq': i + 1, **item} for i, item in enumerate(BASE_RUBRIC)]
        notes_data = _generate_notes_fallback(note_count, pass_ratio)

        record.rubric_data = rubric_data
        record.notes_data = notes_data
        record.status = 'error'
        record.save()

        logger.info(f"[AI量表] 模板降级成功: 用户={user.username}, 任务={name}")

        return Response({
            'success': True,
            'data': {
                'id': record.id,
                'name': record.name,
                'status': 'error',
                'rubric_count': len(rubric_data),
                'notes_count': len(notes_data),
                'source': 'template_fallback',
                'warning': f'AI 生成未成功，已使用默认模板。错误: {str(e)[:100]}',
            }
        }, status=status.HTTP_201_CREATED)


def _ai_generate_rubric_and_notes(file_content, file_name, note_count, pass_ratio, task_name, note_length=300):
    """
    同步调用 AI 模型生成量表和心得数据
    返回: (rubric_list, notes_list)
    使用同步 httpx.Client，避免 Django ASGI 异步上下文冲突。
    """
    import httpx

    # 获取知识库问答角色的配置
    config = get_knowledge_base_config()
    if not config:
        raise ValueError("未找到「知识库问答」角色的 AI 模型配置，请在配置中心添加")

    def call_ai_api(messages):
        """同步调用 OpenAI 兼容 API"""
        headers = {
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json',
        }
        data = {
            'model': config.model_name,
            'messages': messages,
            'max_tokens': getattr(config, 'max_tokens', 4096) or 4096,
            'temperature': getattr(config, 'temperature', 0.7) or 0.7,
            'top_p': getattr(config, 'top_p', 1.0) or 1.0,
            'stream': False,
        }
        base_url = config.base_url.rstrip('/')
        # 智能补全 URL 路径
        if base_url.endswith('/chat/completions'):
            url = base_url
        elif base_url.endswith('/v1'):
            url = f"{base_url}/chat/completions"
        else:
            url = f"{base_url}/v1/chat/completions"

        logger.info(f"[AI量表] AI API URL: {url}, model: {config.model_name}")

        with httpx.Client(timeout=httpx.Timeout(connect=30.0, read=None, write=30.0, pool=None)) as client:
            resp = client.post(url, headers=headers, json=data)
            resp.raise_for_status()
            return resp.json()

    # ---- Step 1: 生成量表 ----
    user_prompt_rubric = BASE_RUBRIC_TEMPLATE.strip()

    if file_content and file_name:
        user_prompt_rubric += f"""

## 参考文档信息：
- 文件名: {file_name}
- 内容如下:

```
{file_content[:6000]}
```

请根据以上文档内容，生成贴合文档主题的评分量表。
如果文档内容不足以生成特定领域的量表，请根据文档涉及的教学场景进行合理推断。"""

    messages_rubric = [
        {"role": "system", "content": "你是资深教育评估专家，擅长设计教学评分量表。只输出JSON格式的数组，不要包含markdown代码块标记或其他文字。"},
        {"role": "user", "content": user_prompt_rubric}
    ]

    response_rubric = call_ai_api(messages_rubric)
    rubric_raw = response_rubric['choices'][0]['message']['content'].strip()
    rubric_raw = _clean_json_response(rubric_raw)
    rubric_data = json.loads(rubric_raw)

    # 确保格式正确并添加序号
    rubric_list = []
    for i, item in enumerate(rubric_data):
        rubric_list.append({
            'seq': i + 1,
            'level1': item.get('level1', ''),
            'level2': item.get('level2', ''),
            'desc': item.get('desc', ''),
        })

    # ---- Step 2: 生成心得 ----
    pass_count = round(note_count * pass_ratio)
    fail_count = note_count - pass_count

    user_prompt_notes = NOTES_PROMPT_TEMPLATE.format(
        note_count=note_count,
        pass_count=pass_count,
        fail_count=fail_count,
        note_length=note_length,
    )

    user_prompt_notes += f"""

## 评分量表概览（作为心得撰写的依据）：
主题: {task_name}
一级指标: {', '.join(set(r['level1'] for r in rubric_list))}
共 {len(rubric_list)} 个评分点

请基于以上量表主题生成学习心得。"""

    messages_notes = [
        {"role": "system", "content": "你是教育学研究者，擅长撰写真实感人的教学反思与学习心得。只输出JSON格式的数组，不要包含markdown代码块标记或其他文字。"},
        {"role": "user", "content": user_prompt_notes}
    ]

    response_notes = call_ai_api(messages_notes)
    notes_raw = response_notes['choices'][0]['message']['content'].strip()
    notes_raw = _clean_json_response(notes_raw)
    notes_data = json.loads(notes_raw)

    # 标准化格式
    notes_list = []
    for item in notes_data:
        notes_list.append({
            'title': item.get('title', '无标题'),
            'body': item.get('body', ''),
            'type': item.get('type', 'pass'),
        })

    return rubric_list, notes_list


def _clean_json_response(raw_text):
    """清理 AI 返回的 JSON 响应，去除 markdown 包裹等"""
    text = raw_text.strip()

    # 移除 ```json ... ``` 包裹
    if text.startswith('```'):
        lines = text.split('\n')
        lines = [l for l in lines if not l.startswith('```')]
        text = '\n'.join(lines).strip()

    # 移除首尾可能的 [ ] 外的多余字符
    text = text.strip()
    if not text.startswith('['):
        idx = text.find('[')
        if idx >= 0:
            text = text[idx:]
    if not text.endswith(']'):
        idx = text.rfind(']')
        if idx >= 0:
            text = text[:idx + 1]

    return text


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def rubric_delete(request, record_id):
    """删除量表生成记录"""
    try:
        record = AIRubricRecord.objects.get(id=record_id, user=request.user)
    except AIRubricRecord.DoesNotExist:
        return Response({'success': False, 'error': '记录不存在'}, status=status.HTTP_404_NOT_FOUND)

    if record.source_file and os.path.exists(record.source_file.path):
        os.remove(record.source_file.path)
    if record.rubric_file and os.path.exists(record.rubric_file.path):
        os.remove(record.rubric_file.path)
    if record.notes_file and os.path.exists(record.notes_file.path):
        os.remove(record.notes_file.path)

    record.delete()
    return Response({'success': True, 'message': '删除成功'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rubric_statistics(request):
    """获取统计数据"""
    from django.db.models import Count, Q

    stats = (
        AIRubricRecord.objects.filter(user=request.user)
        .aggregate(
            total=Count('id'),
            done=Count('id', filter=Q(status='done')),
            running=Count('id', filter=Q(status='running')),
            error=Count('id', filter=Q(status='error')),
        )
    )

    files_done = AIRubricRecord.objects.filter(user=request.user, status='done').count()

    return Response({
        'success': True,
        'data': {
            **stats,
            'files': files_done * 2,
        }
    })


# ========== Fallback 模板（当 AI 调用失败时使用）==========

BASE_RUBRIC = [
    {'level1': '学习者分析与沟通', 'level2': '学习者档案建立', 'desc': '是否建立了完整的学习者基础信息档案，包括知识背景、学习习惯、技术接受度等维度'},
    {'level1': '学习者分析与沟通', 'level2': '需求分析深度', 'desc': '对学习者实际需求的分析是否深入，是否结合了调研数据或访谈结果'},
    {'level1': '学习者分析与沟通', 'level2': '访谈问题设计', 'desc': '访谈或调研问题的设计是否有针对性，能否有效获取关键信息'},
    {'level1': '学习者分析与沟通', 'level2': '沟通计划可行性', 'desc': '与学习者沟通的计划是否具体可执行，时间节点是否合理'},
    {'level1': '学习路径/地图设计', 'level2': '路径逻辑清晰度', 'desc': '学习路径的设计是否有清晰的先后逻辑，层次结构是否合理'},
    {'level1': '学习路径/地图设计', 'level2': '路径可视化表达', 'desc': '学习地图的可视化呈现是否直观易懂，是否便于学习者自我定位'},
    {'level1': '学习路径/地图设计', 'level2': '个性化路径支持', 'desc': '是否提供了差异化的学习路径，能否满足不同层次学习者的需求'},
    {'level1': '学习路径/地图设计', 'level2': 'AI技术融合度', 'desc': '学习路径设计中AI技术的融合是否自然，是否真正提升了学习体验'},
    {'level1': '学习路径/地图设计', 'level2': '里程碑节点设置', 'desc': '是否设置了清晰的学习里程碑，评估节点是否合理分布'},
    {'level1': '学习路径/地图设计', 'level2': '反馈机制设计', 'desc': '学习过程中的反馈机制是否及时有效，能否支持动态调整'},
    {'level1': '学习路径/地图设计', 'level2': '资源整合能力', 'desc': '对各类学习资源的整合是否充分，资源与路径的匹配度如何'},
    {'level1': '学习路径/地图设计', 'level2': '效率提升设计', 'desc': '路径设计是否有助于提升学习效率，是否避免了冗余内容'},
    {'level1': '学习路径/地图设计', 'level2': '质量保障机制', 'desc': '是否有明确的学习质量保障措施，包括监控和纠偏机制'},
    {'level1': '教学方案创新', 'level2': '技术创新应用', 'desc': 'AI及新技术在教学方案中的应用是否具有创新性，是否突破了传统框架'},
    {'level1': '教学方案创新', 'level2': '学科融合深度', 'desc': 'AI技术与具体学科的融合深度，是否真正服务于学科核心素养的提升'},
    {'level1': '教学方案创新', 'level2': '实践可操作性', 'desc': '创新方案的实际可操作性如何，是否考虑了资源限制和实施条件'},
    {'level1': '综合评价', 'level2': '整体设计完整性', 'desc': '教学设计方案的整体完整性，各模块是否协调一致'},
    {'level1': '综合评价', 'level2': '目标达成可能性', 'desc': '预期学习目标的可达成性评估，是否有清晰的成功指标'},
    {'level1': '综合评价', 'level2': '伦理与安全考量', 'desc': '方案是否考虑了AI应用的伦理问题，包括数据隐私、算法公平性等'},
    {'level1': '综合评价', 'level2': '持续改进机制', 'desc': '是否建立了持续改进的机制，包括评估周期和迭代流程'},
    {'level1': '综合评价', 'level2': '跨学科迁移价值', 'desc': '该方案是否具有跨学科推广的潜力和迁移价值'},
    {'level1': '综合评价', 'level2': '学生主体性体现', 'desc': '方案是否充分体现了学生的主体地位，是否鼓励主动学习'},
]

PASS_NOTES_TEMPLATES = [
    {'title': '这堂课彻底改变了我对AI辅助学习的认知', 'body': '完成视频学习后，我最深的感受是AI在教育中的角色比我想象的要复杂得多。原本我以为AI只是一个工具，就像PPT或者投影仪一样，加进去用就好了。但这次学习让我意识到，AI与学科的融合需要深度的教学设计思维作为支撑。\n\nAI帮助我从"教了多少"转向"学了多少"。这不是一次小的调整，而是一次根本性的教学观念转变。'},
    {'title': '学习地图让我终于理解了什么叫"以学定教"', 'body': '之前听过很多次"以学定教"这个概念，但真的要落地的时候总是不知道从哪里下手。这次视频课中专门讲到了如何用可视化学习地图来设计教学路径，这对我来说是一个非常具体的操作框架。\n\n但有了AI工具的支持，这件事变得可行了。我在课后立刻尝试为下一个单元设计了一张简单的学习地图，实施后效果出乎意料地好。'},
    {'title': '关于AI诊断报告：我的几点真实感受', 'body': '视频里提到AI生成的学习诊断报告可以替代传统的成绩单，我一开始是有点怀疑的。看到实际的案例演示之后，我的疑虑消散了很多。诊断报告并不是要抛弃分数，而是在分数之外提供更丰富的信息。\n\n我目前已经在自己班级的月考后试点了AI诊断报告，反馈出乎意料地积极——家长们觉得这比传统成绩单"说清楚了更多事情"。'},
    {'title': '产品化思维：教学设计的新视角', 'body': '这次学习中"产品化思维"这个提法对我触动很大。把教学方案当作产品来设计，意味着要考虑用户体验（即学习体验）、迭代优化、反馈收集和版本管理。\n\n产品化思维的第一个好处是：它会让你时刻考虑"用户"的感受，也就是学生的体验。第二个好处是：它鼓励持续迭代。'},
    {'title': '关于技术与学科融合的边界问题', 'body': '视频中有一个观点我非常认同：AI与学科的融合不应该是"为了用AI而用AI"，而应该是"用AI解决真实的教学问题"。真正的融合是：AI介入了学习过程的核心环节，改变了学习发生的方式，而不仅仅是改变了呈现形式。'},
    {'title': '从这门课我学到的：学科素养才是核心', 'body': '学完视频之后，我意识到一件很重要的事：AI技术与学科融合的终极目标不是让学生"会用AI"，而是通过AI的助力让学生更好地发展学科核心素养。\n\n这个认识改变了我评价一堂"AI融合课"好不好的标准：不看用了多少AI工具，而看AI的使用有没有真实促进学科素养的发展。'},
]

FAIL_NOTES_TEMPLATES = [
    {'title': '坦白说，我没太看懂这门课在讲什么', 'body': '完成了整个视频课程的学习，说实话，我有点困惑。课程内容涉及到了很多专业术语，比如"个性化学习路径"、"AI诊断报告"、"产品化思维"等，但对于我这个刚开始接触AI教育的老师来说，这些概念之间的关系还不是很清晰。\n\n也许是我的技术背景不够，需要先补充一些AI基础知识再来学这门课。'},
    {'title': '学习地图这个概念，我觉得有点理想化', 'body': '视频里花了很大篇幅讲学习地图和个性化学习路径，听起来确实很美好——每个学生都有自己专属的学习路线，AI实时调整、动态优化。但作为一个带三个班160名学生的老师，我实在看不到这件事在我的工作场景里如何落地。\n\n我理解这些先进理念的价值，但课程似乎假设了一个理想化的学校环境。'},
    {'title': '关于AI替代教师的担忧，课程没有解答我的疑虑', 'body': '这次视频学习，我带着一个核心问题进来：AI真的不会替代教师吗？课程里确实强调了AI是工具、教师是核心，但我总觉得这个论断说得有点轻描淡写。\n\n我不是在唱反调，我只是希望课程能更诚实地面对这个问题，给出更有说服力的分析。'},
    {'title': '视频质量不错，但我的收获有限', 'body': '客观说，这次视频课程的制作质量很好，讲师表达流畅，案例也比较生动。但回顾整个学习过程，我发现自己的收获比预期少。\n\n主要原因可能是：课程的内容对我来说有点偏"宏观"。我需要的是具体的操作步骤清单，而不是关于教育未来的宏大愿景。'},
]


def _generate_notes_fallback(count, pass_ratio):
    """Fallback: 基于模板生成心得数据"""
    import random
    pass_cnt = round(count * pass_ratio)
    fail_cnt = count - pass_cnt
    result = []

    pass_pool = list(PASS_NOTES_TEMPLATES)
    fail_pool = list(FAIL_NOTES_TEMPLATES)

    random.seed()
    for i in range(pass_cnt):
        template = pass_pool[i % len(pass_pool)]
        result.append({**template, 'type': 'pass'})

    for i in range(fail_cnt):
        template = fail_pool[i % len(fail_pool)]
        result.append({**template, 'type': 'fail'})

    random.shuffle(result)
    return result


from django.db import models as dj_models
