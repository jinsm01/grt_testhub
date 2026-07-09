import logging

logger = logging.getLogger('django')

import os

# 禁用 browser-use 遥测
os.environ['ANONYMIZED_TELEMETRY'] = 'false'

import asyncio
import base64
import functools
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载环境变量
load_dotenv()

# ============================================================================
import threading

_browser_use_patches_applied = False
_patch_lock = threading.Lock()


def _apply_browser_use_patches():
    """Apply all browser-use compatibility patches. Thread-safe, idempotent."""
    global _browser_use_patches_applied
    with _patch_lock:
        if _browser_use_patches_applied:
            return
        _browser_use_patches_applied = True

    # PART 1: Common Patches (Pydantic, ActionModel, TokenCost, Basic Connection)
    # ============================================================================
    
    # Patch ChatOpenAI to allow setting attributes (required for browser-use token counting)
    try:
        from pydantic import ConfigDict
    
        if hasattr(ChatOpenAI, 'model_config'):
            if isinstance(ChatOpenAI.model_config, dict):
                ChatOpenAI.model_config['extra'] = 'allow'
            else:
                ChatOpenAI.model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)
        else:
            ChatOpenAI.model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)
    except ImportError:
        if hasattr(ChatOpenAI, 'model_config'):
            ChatOpenAI.model_config['extra'] = 'allow'
    
    # 修改 ActionModel 配置以允许额外字段
    try:
        from browser_use.tools.registry.views import ActionModel
        from pydantic import ConfigDict
    
        ActionModel.model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
        logger.info("✅ Modified ActionModel.model_config to allow extra fields")
    except Exception as e:
        logger.warning(f"⚠️ Failed to modify ActionModel config: {e}")
    
    # Patch Agent.get_model_output 方法
    try:
        from browser_use.agent.service import Agent
        from browser_use.agent.message_manager.service import AgentOutput
        import json as json_module
    
        _original_get_model_output = Agent.get_model_output
    
    
        async def _patched_get_model_output(self, input_messages):
            """修补后的 get_model_output，直接从 response.content 解析 JSON"""
            # logger.info("🔧 _patched_get_model_output called")
    
            if hasattr(self, '_task_was_done') and self._task_was_done:
                logger.info("🔧 Task was marked as done, stopping LLM interaction")
                raise KeyboardInterrupt("Task finished")
    
            kwargs = {'output_format': self.AgentOutput}
    
            # Add retry logic for LLM invocation with timeout
            max_retries = 2  # 重试次数为2次
            last_exception = None
            response = None
            for attempt in range(max_retries):
                try:
                    # 添加超时控制，设置为60秒（支持硅基流动等大模型API的响应时间）
                    response = await asyncio.wait_for(
                        self.llm.ainvoke(input_messages, **kwargs),
                        timeout=60.0  # 超时时间60秒
                    )
                    break
                except asyncio.TimeoutError as te:
                    last_exception = te
                    logger.warning(f"⚠️ LLM invocation timed out (attempt {attempt + 1}/{max_retries}): {te}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 重试间隔0.5秒
                except Exception as e:
                    last_exception = e
                    logger.warning(f"⚠️ LLM invocation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 重试间隔0.5秒
            else:
                logger.error(f"❌ LLM invocation failed after {max_retries} attempts.")
                raise last_exception
    
            # 检查响应是否为空或无效
            if not response or not hasattr(response, 'content'):
                error_msg = "LLM returned invalid response (no content attribute)"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
    
            # 检查content是否为空字符串
            content = response.content
            if not content or not isinstance(content, str) or not content.strip():
                error_msg = "LLM returned empty content - possible API error or timeout"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
    
            try:
                if hasattr(response, 'content') and isinstance(response.content, str):
                    content_dict = json_module.loads(response.content)
    
                    # 规范化 action 字典
                    if 'action' in content_dict:
                        normalized_actions = []
                        for action_dict in content_dict['action']:
                            normalized_action = {}
                            for action_name, action_params in action_dict.items():
                                # 自动修复: 将 int 参数转换为 index 字典
                                if isinstance(action_params, int):
                                    normalized_action[action_name] = {'index': action_params}
                                # 自动修复: switch_tab 的 tab_id 字符串参数
                                elif action_name == 'switch_tab' and isinstance(action_params, str) and not isinstance(
                                        action_params, dict):
                                    normalized_action[action_name] = {'tab_id': action_params}
                                elif isinstance(action_params, dict):
                                    normalized_params = {}
                                    for k, v in action_params.items():
                                        if k == 'element_index':
                                            normalized_params['index'] = v
                                        else:
                                            normalized_params[k] = v
                                    normalized_action[action_name] = normalized_params
                                else:
                                    normalized_action[action_name] = action_params
                            normalized_actions.append(normalized_action)
                        content_dict['action'] = normalized_actions
    
                    parsed = AgentOutput.model_construct(
                        thinking=content_dict.get('thinking'),
                        evaluation_previous_goal=content_dict.get('evaluation_previous_goal'),
                        memory=content_dict.get('memory'),
                        next_goal=content_dict.get('next_goal'),
                        action=[]
                    )
    
                    class _ActionWrapper:
                        def __init__(self, action_dict):
                            self._action_dict = action_dict
    
                        def model_dump(self, **kwargs):
                            return self._action_dict
    
                        def get_index(self):
                            for action_params in self._action_dict.values():
                                if isinstance(action_params, dict) and 'index' in action_params:
                                    return action_params['index']
                            return None
    
                    action_list = []
                    for action_dict in content_dict.get('action', []):
                        action_list.append(_ActionWrapper(action_dict))
    
                    object.__setattr__(parsed, 'action', action_list)
    
                    if len(parsed.action) > self.settings.max_actions_per_step:
                        parsed.action = parsed.action[:self.settings.max_actions_per_step]
    
                    return parsed
            except Exception as e:
                # If our complex normalization fails, fall back to the original method
                logger.warning(f"⚠️ Custom output normalization failed, falling back: {e}")
                return await _original_get_model_output(self, input_messages)
    
    
        Agent.get_model_output = _patched_get_model_output
        logger.info("✅ Successfully patched Agent.get_model_output")
    except Exception as e:
        logger.error(f"❌ Failed to patch Agent.get_model_output: {e}")
    
    # Patch TokenCost
    try:
        from browser_use.tokens.service import TokenCost
        from langchain_core.messages import HumanMessage, SystemMessage as LangChainSystemMessage, AIMessage
    
    
        def _patched_register_llm(self, llm):
            """修补后的 register_llm，修复 langchain 兼容性"""
            instance_id = str(id(llm))
            if instance_id in self.registered_llms:
                return llm
    
            self.registered_llms[instance_id] = llm
            _original_ainvoke = llm.ainvoke
            _token_service = self
    
            async def _fixed_tracked_ainvoke(messages, output_format=None, **kwargs):
                # Sanitize message contents
                def _content_to_str(content):
                    if isinstance(content, str): return content
                    if isinstance(content, list):
                        parts = []
                        for item in content:
                            if isinstance(item, str):
                                parts.append(item)
                            elif isinstance(item, dict):
                                if 'text' in item:
                                    parts.append(str(item['text']))
                                elif 'image' in item or 'image_url' in item:
                                    parts.append("[image]")
                            else:
                                parts.append(str(item))
                        return "\n".join(parts)
                    if isinstance(content, dict):
                        if 'text' in content: return str(content['text'])
                        if 'content' in content: return str(content['content'])
                        if 'image' in content or 'image_url' in content: return "[image]"
                    return str(content)
    
                def _sanitize_message(msg):
                    msg_type_name = type(msg).__name__
                    content = getattr(msg, 'content', msg)
                    content_str = _content_to_str(content)
                    if msg_type_name == 'SystemMessage': return LangChainSystemMessage(content=content_str)
                    if msg_type_name in ('HumanMessage', 'UserMessage'): return HumanMessage(content=content_str)
                    if msg_type_name == 'AIMessage': return AIMessage(content=content_str)
                    if isinstance(msg, (HumanMessage, LangChainSystemMessage, AIMessage)): return type(msg)(
                        content=content_str)
                    return HumanMessage(content=str(content_str))
    
                sanitized_messages = [_sanitize_message(m) for m in messages]
    
                output_format = kwargs.pop('output_format', None)
                if output_format:
                    kwargs['response_format'] = {"type": "json_object"}

                # browser-use Agent 可能传递 session_id，但底层 openai 客户端不支持，需过滤
                kwargs.pop('session_id', None)

                # Add retry logic for LLM invocation
                max_retries = 2  # 重试次数为2次
                last_exception = None
                for attempt in range(max_retries):
                    try:
                        result = await _original_ainvoke(sanitized_messages, **kwargs)
                        break
                    except Exception as e:
                        last_exception = e
                        if "response_format" in str(e):
                            kwargs.pop('response_format', None)
                            # retry immediately without response_format
                            continue
    
                        logger.warning(f"⚠️ LLM ainvoke failed (attempt {attempt + 1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(0.5)  # 等待0.5秒
                else:
                    logger.error(f"❌ LLM ainvoke failed after {max_retries} attempts.")
                    raise last_exception
    
                # Enhance response parsing
                import json as json_module
                clean_content = result.content.strip() if hasattr(result, 'content') else str(result).strip()
    
                # Remove Markdown
                if '```' in clean_content:
                    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', clean_content, re.DOTALL)
                    if match:
                        clean_content = match.group(1).strip()
                    else:
                        clean_content = re.sub(r'```[a-z]*', '', clean_content).replace('```', '').strip()
    
                parsed_data = None
                try:
                    parsed_data = json_module.loads(clean_content)
                except:
                    try:
                        match = re.search(r'(\{.*\})', clean_content, re.DOTALL)
                        if match: parsed_data = json_module.loads(match.group(1))
                    except:
                        pass
    
                # Wrapper classes
                class _ActionWrapper:
                    def __init__(self, action_dict):
                        self._dict = {}
                        for k, v in action_dict.items():
                            if isinstance(v, dict):
                                norm = {}
                                for subk, subv in v.items():
                                    if subk == 'element_index':
                                        norm['index'] = subv
                                    else:
                                        norm[subk] = subv
                                self._dict[k] = norm
                            else:
                                self._dict[k] = v
                        for k, v in self._dict.items(): setattr(self, k, v)
    
                    def model_dump(self, **kwargs):
                        return self._dict
    
                    def get_index(self):
                        for v in self._dict.values():
                            if isinstance(v, dict) and 'index' in v: return v['index']
                        return None
    
                # Construct AgentOutput manually
                agent_output = None
                if parsed_data and 'action' in parsed_data:
                    # Normalize actions
                    normalized_actions = []
                    for action_dict in parsed_data['action']:
                        normalized_action = {}
                        for action_name, action_params in action_dict.items():
                            if isinstance(action_params, dict):
                                normalized_params = {}
                                for k, v in action_params.items():
                                    if k == 'element_index':
                                        normalized_params['index'] = v
                                    else:
                                        normalized_params[k] = v
                                normalized_action[action_name] = normalized_params
                            else:
                                normalized_action[action_name] = action_params
                        normalized_actions.append(normalized_action)
                    parsed_data['action'] = normalized_actions
    
                    try:
                        from browser_use.agent.message_manager.service import AgentOutput
                        agent_output = AgentOutput.model_construct(
                            thinking=parsed_data.get('thinking'),
                            evaluation_previous_goal=parsed_data.get('evaluation_previous_goal'),
                            memory=parsed_data.get('memory'),
                            next_goal=parsed_data.get('next_goal'),
                            action=[]
                        )
                        action_list = []
                        for action_dict in parsed_data.get('action', []):
                            action_list.append(_ActionWrapper(action_dict))
                        object.__setattr__(agent_output, 'action', action_list)
                    except Exception as e:
                        logger.error(f"🔧 Failed to create AgentOutput: {e}")
    
                class _ResponseWrapper:
                    def __init__(self, orig, completion_obj):
                        self._orig = orig
                        self.content = getattr(orig, 'content', '')
                        self.response_metadata = getattr(orig, 'response_metadata', {})
                        self.completion = completion_obj
                        usage = getattr(orig, 'usage', None) or (
                            orig.response_metadata.get('token_usage') if hasattr(orig, 'response_metadata') else None)
                        if not usage: usage = {}
                        # Fix usage
                        usage = dict(usage) if hasattr(usage, '__dict__') else usage
                        usage.setdefault('prompt_tokens', 0)
                        usage.setdefault('completion_tokens', 0)
                        usage.setdefault('total_tokens', 0)
                        self.usage = usage
    
                    def __getattr__(self, name): return getattr(self._orig, name)
    
                wrapped = _ResponseWrapper(result, agent_output)
                if hasattr(wrapped, 'usage') and wrapped.usage:
                    try:
                        _token_service.add_usage(llm.model, wrapped.usage)
                    except:
                        pass
    
                return wrapped
    
            setattr(llm, 'ainvoke', _fixed_tracked_ainvoke)
            return llm
    
    
        TokenCost.register_llm = _patched_register_llm
        logger.info("✅ Successfully patched TokenCost.register_llm")
    except Exception as e:
        logger.error(f"❌ Failed to patch TokenCost: {e}")
    
    # Patch BrowserSession.connect (Windows CDP fix)
    try:
        from browser_use.browser.session import BrowserSession
        import httpx
    
        _original_connect = BrowserSession.connect
    
    
        async def _patched_connect(self, cdp_url=None):
            if cdp_url: return await _original_connect(self, cdp_url=cdp_url)
    
            browser_profile = getattr(self, 'browser_profile', None)
            if hasattr(browser_profile, 'cdp_url') and browser_profile.cdp_url:
                return await _original_connect(self, cdp_url=browser_profile.cdp_url)
    
            port = 9222
            if hasattr(browser_profile, 'extra_chromium_args'):
                for arg in browser_profile.extra_chromium_args:
                    if '--remote-debugging-port=' in str(arg):
                        try:
                            port = int(arg.split('=')[1]); break
                        except:
                            pass
            if hasattr(browser_profile, 'remote_debugging_port'):
                port = browser_profile.remote_debugging_port
    
            cdp_endpoint = f"http://localhost:{port}/json/version"
    
            for attempt in range(5):
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(cdp_endpoint)
                        if response.status_code == 200 and response.text:
                            version_info = response.json()
                            browser_profile.cdp_url = version_info['webSocketDebuggerUrl']
                            return await _original_connect(self, cdp_url=browser_profile.cdp_url)
                except Exception:
                    if attempt < 4: await asyncio.sleep(1.0)
    
            return await _original_connect(self, cdp_url=cdp_url)
    
    
        BrowserSession.connect = _patched_connect
        logger.info("✅ Successfully patched BrowserSession.connect")
    except Exception as e:
        logger.error(f"❌ Failed to patch BrowserSession.connect: {e}")
    
    # Patch ClickElementAction parameters
    try:
        from browser_use.tools.views import ClickElementAction
    
        _original_click_init = ClickElementAction.__init__
    
    
        def _patched_click_init(self, **kwargs):
            fixed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, int) and key not in ['index']:
                    fixed_kwargs['index'] = value
                else:
                    fixed_kwargs[key] = value
            if len(kwargs) == 1:
                key, value = list(kwargs.items())[0]
                if isinstance(value, int) and key != 'index':
                    fixed_kwargs = {'index': value}
            try:
                return _original_click_init(self, **fixed_kwargs)
            except TypeError:
                if fixed_kwargs and isinstance(list(fixed_kwargs.values())[0], int):
                    return _original_click_init(self, **{'index': list(fixed_kwargs.values())[0]})
                raise
    
    
        ClickElementAction.__init__ = _patched_click_init
    except Exception:
        pass
    
    # Patch ToolRegistry
    try:
        from browser_use.tools.registry.service import Registry as ToolRegistry
    
        # Force patch Registry class
        _original_execute_action = ToolRegistry.execute_action
    
    
        async def _patched_execute_action(self, action_name: str, params: dict, **kwargs):
            # 自动映射 switch_tab -> switch (强制映射)
            if action_name == 'switch_tab':
                logger.info(f"🔧 Force aliasing: switch_tab -> switch")
                action_name = 'switch'
    
            if isinstance(params, int):
                params = {'index': params}
            elif not isinstance(params, dict) and params is not None:
                # 针对 switch_tab 可能是纯字符串的情况
                if action_name in ['switch_tab', 'switch']:
                    params = {'tab_id': params}
                else:
                    params = {'value': params} if params else {}
    
            # 🔧 修复 input action 的参数格式：将 content/value 转换为 text
            # 适配不同LLM模型生成的参数格式
            if action_name in ['input', 'input_text'] and isinstance(params, dict):
                # 检查是否有 content 或 value 字段，转换为 text
                if 'text' not in params:
                    if 'content' in params:
                        params['text'] = params.pop('content')
                        logger.info(f"🔧 Converted 'content' -> 'text' for input action: {params.get('index', '?')}")
                    elif 'value' in params:
                        params['text'] = params.pop('value')
                        logger.info(f"🔧 Converted 'value' -> 'text' for input action: {params.get('index', '?')}")
    
            # 针对点击增加延迟，确保 UI 更新 (如弹窗弹出、下拉框展开)
            if action_name in ['click_element', 'click']:
                result = await _original_execute_action(self, action_name, params, **kwargs)
                # 增加延迟到 1.5s，并强制在点击后等待浏览器渲染
                # 尤其是对于 element-plus 等 UI 框架，下拉列表渲染需要时间
                await asyncio.sleep(1.5)
                return result
    
            return await _original_execute_action(self, action_name, params, **kwargs)
    
    
        ToolRegistry.execute_action = _patched_execute_action
        logger.info("✅ Successfully patched ToolRegistry.execute_action with alias support")
    except Exception as e:
        logger.error(f"❌ Failed to patch ToolRegistry: {e}")
    
    # Patch ScreenshotWatchdog GLOBALLY to fix timeouts
    try:
        from browser_use.browser.watchdogs.screenshot_watchdog import ScreenshotWatchdog
    
        _original_on_screenshot_event = ScreenshotWatchdog.on_ScreenshotEvent
    
        # Check if already patched to avoid double patching
        if not getattr(_original_on_screenshot_event, '_is_patched_global', False):
            async def on_ScreenshotEvent(self, event):
                """
                Patched screenshot event handler with increased timeout and optimized parameters.
                """
                try:
                    # Try original method first with strict timeout
                    result = await asyncio.wait_for(
                        _original_on_screenshot_event(self, event),
                        timeout=3.0  # Reduced for fail-fast
                    )
                    return result
                except asyncio.TimeoutError:
                    logger.warning(f"DEBUG: Watchdog timeout (3s), trying optimized approach...")
                    try:
                        # Get CDP session
                        cdp_session = await self.browser_session.get_or_create_cdp_session(target_id=None)
                        if not cdp_session: raise Exception("Failed to get CDP session")
    
                        params = {'format': 'png', 'quality': 50, 'from_surface': True, 'capture_beyond_viewport': False}
    
                        # One quick retry
                        result = await asyncio.wait_for(
                            cdp_session.cdp_client.send.Page.captureScreenshot(params=params,
                                                                               session_id=cdp_session.session_id),
                            timeout=3.0
                        )
                        return result
    
                    except Exception as ex:
                        # In Text Mode especially, we don't want to die on screenshot
                        logger.warning(f"DEBUG: Screenshot failed optimized, returning placeholder: {ex}")
                        import base64
                        # 1x1 transparent pixel
                        placeholder = base64.b64decode(
                            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
                        return {'data': placeholder}
                except Exception as e:
                    logger.error(f"DEBUG: Screenshot unexpected error: {e}")
                    import base64
                    placeholder = base64.b64decode(
                        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
                    return {'data': placeholder}
    
    
            on_ScreenshotEvent._is_patched_global = True
            ScreenshotWatchdog.on_ScreenshotEvent = on_ScreenshotEvent
            logger.info("✅ Applied Global ScreenshotWatchdog Patch")
    
        # Patch DOMWatchdog
        from browser_use.browser.watchdogs.dom_watchdog import DOMWatchdog
    
        _original_capture_clean_screenshot = DOMWatchdog._capture_clean_screenshot
    
        if not getattr(_original_capture_clean_screenshot, '_is_patched_global', False):
            async def _capture_clean_screenshot(self):
                try:
                    # Very short timeout for DOM clean screenshot checks
                    return await asyncio.wait_for(_original_capture_clean_screenshot(self), timeout=3.0)
                except Exception as e:
                    logger.warning(f"DEBUG: Clean screenshot failed/timed out: {e}, continuing...")
                    return None
    
    
            _capture_clean_screenshot._is_patched_global = True
            DOMWatchdog._capture_clean_screenshot = _capture_clean_screenshot
            logger.info("✅ Applied Global DOMWatchdog Patch")
    
    except Exception as e:
        logger.error(f"❌ Failed to apply Global Watchdog patches: {e}")
    
    # Patch Agent verdict
    try:
        from browser_use.agent.service import Agent
        from browser_use.agent.message_manager.service import AgentOutput
    
        _original_judge_and_log = Agent._judge_and_log
    
    
        def _agent_output_getattr(self, name):
            if name == 'verdict':
                if hasattr(self, 'next_goal') and self.next_goal:
                    if any(
                        w in str(self.next_goal).lower() for w in ['complete', 'done', 'finished', 'success']): return True
                if hasattr(self, 'evaluation_previous_goal') and self.evaluation_previous_goal:
                    if any(w in str(self.evaluation_previous_goal).lower() for w in ['success', 'complete']): return True
                return False
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    
        if not hasattr(AgentOutput, '__getattr__'):
            AgentOutput.__getattr__ = _agent_output_getattr
    
    
        async def _patched_judge_and_log(self):
            try:
                return await _original_judge_and_log(self)
            except AttributeError as e:
                if 'verdict' in str(e):
                    return None
                raise
    
    
        Agent._judge_and_log = _patched_judge_and_log
    except Exception:
        pass
    
    # ============================================================================
# PART 2: Helper Classes
# ============================================================================

from langchain_core.callbacks import BaseCallbackHandler
from typing import Any


class RawResponseLogger(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs: Any) -> Any:
        pass

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        try:
            generation = response.generations[0][0]
            logger.info(f"DEBUG: Raw LLM Response: {generation.text}")
        except:
            pass


# ============================================================================
# Page Snapshot - 页面快照与元素索引映射
# ============================================================================

class PageSnapshot:
    """页面快照，包含可交互元素的索引映射

    设计灵感来自 Playwright CLI 的 snapshot 机制：
    1. 扫描页面所有可见的可交互元素
    2. 按 DOM 顺序分配稳定的数字索引 [1], [2], [3]...
    3. 生成文本化快照，供 LLM 基于索引操作元素
    """

    def __init__(self, elements=None, url="", title=""):
        self.elements = elements or []
        self.element_map = {e['index']: e for e in self.elements}
        self.url = url
        self.title = title
        self.snapshot_text = ""
        self.iframe_info = []

    @classmethod
    async def capture(cls, page) -> 'PageSnapshot':
        """通过 Playwright page 捕获页面快照"""
        if not page:
            return cls()

        url = page.url
        try:
            title = await page.title()
        except Exception:
            title = ""

        # 读取外部 JS 文件，避免内嵌大段脚本且便于维护
        import os
        js_path = os.path.join(os.path.dirname(__file__), 'snapshot_script.js')
        try:
            with open(js_path, 'r', encoding='utf-8') as f:
                js_code = f.read()
        except Exception:
            js_code = "(() => { return []; })()"

        elements = await page.evaluate(js_code)

        # 遍历 iframe（同源可访问的 frame），收集元信息供 LLM 参考
        iframe_info = []
        for frame in page.frames[1:]:
            try:
                frame_elements = await frame.evaluate(js_code)
                iframe_info.append({'url': frame.url, 'element_count': len(frame_elements)})
            except Exception:
                iframe_info.append({'url': frame.url, 'element_count': 0, 'inaccessible': True})

        snapshot = cls(elements=elements, url=url, title=title)
        snapshot.iframe_info = iframe_info
        snapshot.snapshot_text = snapshot._format_text()
        return snapshot

    def _format_text(self):
        """格式化为类似 Playwright CLI 的文本快照"""
        lines = [
            f"Page URL: {self.url}",
            f"Title: {self.title}",
            f"Interactive elements: {len(self.elements)}",
            "-" * 50
        ]
        for el in self.elements:
            line = f"[{el['index']:2d}] <{el['tag']}"
            if el['type']:
                line += f" type='{el['type']}'"
            attrs = []
            if el['text']:
                attrs.append(f"text='{el['text']}'")
            if el['placeholder']:
                attrs.append(f"placeholder='{el['placeholder']}'")
            if el['ariaLabel']:
                attrs.append(f"aria-label='{el['ariaLabel']}'")
            if el['id']:
                attrs.append(f"id='{el['id']}'")
            if el['role']:
                attrs.append(f"role='{el['role']}'")
            if attrs:
                line += " " + " ".join(attrs)
            line += ">"
            lines.append(line)
        if self.iframe_info:
            lines.append("")
            lines.append("Iframes detected:")
            for info in self.iframe_info:
                if info.get('inaccessible'):
                    lines.append(f"  - {info['url']} (inaccessible)")
                else:
                    lines.append(f"  - {info['url']} ({info['element_count']} elements)")
        return "\n".join(lines)

    def get_element_by_index(self, index: int) -> dict:
        return self.element_map.get(index, {})

    def to_dict(self):
        return {
            'url': self.url,
            'title': self.title,
            'elements': self.elements,
            'snapshot_text': self.snapshot_text,
            'element_count': len(self.elements)
        }


# ============================================================================
# PART 3: Base Browser Agent
# ============================================================================

from browser_use import Agent, Controller, BrowserSession
from browser_use.browser.profile import BrowserProfile


def _create_browser_profile_common(keep_alive=False):
    """创建浏览器配置文件的公共函数，避免 BaseBrowserAgent 和 PersistentBrowserSession 重复代码。"""
    chrome_path = None
    import platform

    system = platform.system()
    if system == 'Windows':
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        for p in paths:
            if os.path.exists(p):
                chrome_path = p
                break
    elif system == 'Linux':
        paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/opt/google/chrome/chrome',
            '/snap/bin/chromium',
        ]
        for p in paths:
            if os.path.exists(p):
                chrome_path = p
                break

    extra_args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-infobars', '--disable-notifications',
        '--disable-background-networking',
        '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding',
        '--disable-backgrounding-occluded-windows',
        '--disable-extensions',
        '--disable-web-security',
    ]

    if system == 'Linux':
        extra_args.extend([
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--headless=new',
            '--disable-software-rasterizer',
            '--remote-debugging-port=0',
        ])
    else:
        extra_args.extend([
            '--no-sandbox',
            '--disable-gpu',
            '--remote-debugging-port=9222',
        ])

    profile_kwargs = dict(
        headless=(system == 'Linux'),
        disable_security=True,
        executable_path=chrome_path,
        args=extra_args,
        wait_for_network_idle_page_load_time=0.2,
        minimum_wait_page_load_time=0.05,
        wait_between_actions=0.1,
        enable_default_extensions=False
    )
    if keep_alive:
        profile_kwargs['keep_alive'] = True
    return BrowserProfile(**profile_kwargs)


class BaseBrowserAgent:
    def __init__(self, execution_mode='text', enable_gif=True, case_name=None):
        # Ensure browser-use patches are applied before use
        _apply_browser_use_patches()

        self.execution_mode = 'text'
        self.enable_gif = enable_gif  # 步骤截图开关
        self.case_name = case_name or "Adhoc Task"  # 用例名称
        self.screenshots_sequence = []  # 每步截图路径列表

        # Snapshot 状态
        self.current_snapshot = None
        self._last_snapshot_url = ""

        # Load Config from DB
        from apps.requirement_analysis.models import AIModelConfig

        # Select Config (always use text mode config)
        role_name = 'browser_use_text'
        config_obj = AIModelConfig.objects.filter(role=role_name, is_active=True).first()

        model_config = {}
        if config_obj:
            model_config = {
                'api_key': config_obj.api_key,
                'base_url': config_obj.base_url,
                'model_name': config_obj.model_name,
                'provider': config_obj.model_type,
                'temperature': config_obj.temperature  # 读取配置的temperature
            }

        self.api_key = model_config.get('api_key') or os.getenv('AUTH_TOKEN')
        self.base_url = model_config.get('base_url') or os.getenv('BASE_URL')
        self.model_name = model_config.get('model_name') or os.getenv('MODEL_NAME')
        self.provider = model_config.get('provider', 'openai')

        if not self.api_key:
            raise ValueError(f"No API Key found for mode: {execution_mode}")

        # 智能temperature处理：特殊模型强制使用特定temperature值
        # 格式: {'模型名称关键字': temperature值}
        special_model_temperature_map = {
            'kimi-2.5': 1.0,  # Moonshot AI Kimi 2.5 只支持 temperature=1
            'kimi-k2.5': 1.0,  # Moonshot AI Kimi K2.5 只支持 temperature=1
            'kimi': 1.0,  # 通用Kimi模型匹配（兜底）
            # 未来可以在这里添加其他特殊模型，例如：
            # 'claude-3.5-sonnet': 0.7,
            # 'gpt-4-turbo': 0.0,
        }

        # 确定最终使用的temperature值
        final_temperature = 0.0  # 默认值
        model_name_lower = self.model_name.lower()

        # 1. 优先检查是否是特殊模型
        for model_keyword, temp in special_model_temperature_map.items():
            if model_keyword in model_name_lower:
                final_temperature = temp
                logger.info(f"✅ 检测到特殊模型 '{self.model_name}'，使用强制 temperature={temp}")
                break
        else:
            # 2. 如果不是特殊模型，使用配置中的值
            if 'temperature' in model_config:
                final_temperature = model_config['temperature']
                logger.info(f"📋 使用配置的 temperature={final_temperature}")
            else:
                # 3. 如果配置中没有，使用默认值
                final_temperature = 0.0
                logger.info(f"⚙️ 使用默认 temperature={final_temperature}")

        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=final_temperature,
            callbacks=[RawResponseLogger()]
        )

        # browser-use requirement
        try:
            object.__setattr__(self.llm, 'provider', self.provider)
            object.__setattr__(self.llm, 'model', self.model_name)
        except:
            if not hasattr(self.llm, '__pydantic_extra__') or self.llm.__pydantic_extra__ is None:
                self.llm.__pydantic_extra__ = {}
            self.llm.__pydantic_extra__['provider'] = self.provider
            self.llm.__pydantic_extra__['model'] = self.model_name

    def _format_action(self, action):
        try:
            action_dict = {}
            if hasattr(action, 'model_dump'):
                action_dict = action.model_dump()
            elif hasattr(action, '_action_dict'):
                action_dict = action._action_dict
            elif hasattr(action, '_dict'):
                action_dict = action._dict
            elif isinstance(action, dict):
                action_dict = action
            else:
                return str(action)

            if not action_dict: return "待机"

            descriptions = []
            for name, params in action_dict.items():
                # 将 snapshot_page 加入白名单，即使 params 为空也显示
                if not params and name not in ['scroll_down', 'scroll_up', 'done', 'snapshot_page']: continue

                if name in ['go_to_url', 'navigate']:
                    url = params.get('url') if isinstance(params, dict) else params
                    descriptions.append(f"访问: {url}")
                elif name in ['click_element', 'click']:
                    index = params.get('index') if isinstance(params, dict) else params
                    descriptions.append(f"点击[{index}]")
                elif name in ['input_text', 'input']:
                    text = params.get('text') if isinstance(params, dict) else None
                    descriptions.append(f"输入: '{text}'")
                elif name == 'switch_tab':
                    index = params.get('index', params)
                    descriptions.append(f"切换标签 {index}")
                elif name == 'open_new_tab':
                    url = params.get('url', params)
                    descriptions.append(f"新标签打开: {url}")
                elif name == 'snapshot_page':
                    descriptions.append("📸 捕获页面快照")
                elif name == 'done':
                    descriptions.append("任务完成")
                else:
                    descriptions.append(f"{name}")
            return " | ".join(descriptions)
        except Exception as e:
            logger.debug(f"_format_action error: {e}, action={action}")
            return str(action)

    async def analyze_task(self, task_description: str):
        """分析任务，带缓存机制"""
        # 导入缓存模块
        try:
            from .ai_cache import TaskAnalysisCache
            
            # 尝试从缓存获取
            cached_result = TaskAnalysisCache.get(task_description)
            if cached_result is not None:
                logger.info(f"[analyze_task] Cache hit, skipping LLM call")
                return cached_result
        except Exception as e:
            logger.warning(f"[analyze_task] Cache check failed: {e}")
        
        try:
            # 快速路径：如果用户输入已经是编号步骤，直接解析，不走 LLM
            lines = [line.strip() for line in task_description.split('\n') if line.strip()]
            numbered_lines = []
            for line in lines:
                match = re.match(r'^\s*\d+[\.\s、:)\]]\s*(.*)', line)
                if match:
                    numbered_lines.append(match.group(1).strip())

            if len(numbered_lines) >= 1 and len(numbered_lines) >= len(lines) * 0.5:
                cleaned_steps = []
                for desc in numbered_lines:
                    while True:
                        m = re.match(r'^\s*\d+[\.\s、:]+(.*)', desc)
                        if not m:
                            break
                        desc = m.group(1).strip()
                    if desc:
                        cleaned_steps.append(desc)

                result = [{'id': i + 1, 'description': s, 'status': 'pending'} for i, s in enumerate(cleaned_steps)]
                try:
                    TaskAnalysisCache.set(task_description, result, ttl_hours=24)
                    logger.info(f"[analyze_task] Parsed numbered steps directly, skipping LLM")
                except Exception as e:
                    logger.warning(f"[analyze_task] Cache save failed: {e}")
                return result

            prompt = f"Break down this task into steps: {task_description}. Return JSON list of strings."
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip() if hasattr(response, 'content') else str(response)

            steps = []
            try:
                import json
                match = re.search(r'(\[.*\])', content, re.DOTALL)
                if match: steps = json.loads(match.group(1))
            except:
                pass

            if not steps:
                steps = [s.strip() for s in task_description.split('\n') if s.strip()]

            # 彻底清理生成的步骤描述中的重复编号
            cleaned_steps = []
            for s in steps:
                desc = s
                while True:
                    match = re.match(r'^\s*\d+[\.\s、:]+(.*)', desc)
                    if not match: break
                    desc = match.group(1).strip()
                if desc:
                    cleaned_steps.append(desc)

            result = [{'id': i + 1, 'description': s, 'status': 'pending'} for i, s in enumerate(cleaned_steps)]
            
            # 缓存结果
            try:
                TaskAnalysisCache.set(task_description, result, ttl_hours=24)
                logger.info(f"[analyze_task] Cached result for future use")
            except Exception as e:
                logger.warning(f"[analyze_task] Cache save failed: {e}")
            
            return result
        except:
            return [{'id': 1, 'description': task_description, 'status': 'pending'}]

    def _create_browser_profile(self):
        return _create_browser_profile_common(keep_alive=False)

    async def run_task(self, task_description: str, planned_tasks=None, callback=None, should_stop=None):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        controller = Controller()
        _task_was_done = False

        @controller.action('Done')
        async def done(success: bool = True, text: str = ""):
            nonlocal _task_was_done
            _task_was_done = True
            return f"Finished: {text}"

        @controller.action('mark_task_complete')
        async def mark_task_complete(task_id: int):
            logger.info(f"✅ Explicitly marking task {task_id} as completed")
            if callback:
                try:
                    data = {'task_id': int(task_id), 'status': 'completed'}
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.warning(f"Failed to execute mark_task_complete callback: {e}")
            return f"Task {task_id} marked completed"

        @controller.action('snapshot_page')
        async def snapshot_page(browser):
            """捕获当前页面快照，返回可交互元素索引列表"""
            try:
                page = browser.page
                self.current_snapshot = await PageSnapshot.capture(page)
                self._last_snapshot_url = self.current_snapshot.url
                snapshot_text = self.current_snapshot.snapshot_text

                logger.info(f"📸 Snapshot captured: {len(self.current_snapshot.elements)} elements at {self.current_snapshot.url}")

                if callback:
                    data = {
                        'type': 'snapshot',
                        'content': snapshot_text,
                        'element_count': len(self.current_snapshot.elements),
                        'elements': self.current_snapshot.elements,
                        'url': self.current_snapshot.url,
                        'title': self.current_snapshot.title
                    }
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)

                return f"Page snapshot captured. {len(self.current_snapshot.elements)} interactive elements found.\n\n{snapshot_text}"
            except Exception as e:
                logger.warning(f"Failed to capture snapshot: {e}")
                return f"Snapshot failed: {e}"

        # 构建强化版 Prompt
        final_task = task_description
        if planned_tasks:
            final_task += "\n\nIMPORTANT INSTRUCTION:\n"
            final_task += "You have a list of sub-tasks. Execute strictly in order.\n"
            final_task += "CRITICAL: MUST call 'mark_task_complete(task_id=...)' IMMEDIATELY after verifying each sub-task completion. NEVER skip this step. For every action you take, there MUST be a corresponding mark_task_complete call.\n"
            final_task += "IMPORTANT: If a sub-task (like opening a URL) is already fulfilled by the initial state, YOU MUST mark it complete in your VERY FIRST STEP.\n"
            final_task += "Sub-tasks (Execute in order):\n"
            cleaned_tasks = []
            for t in planned_tasks:
                desc = t['description']
                # 递归去除所有层级的重复序号，例如 "1. 1. xxx" -> "xxx"
                while True:
                    match = re.match(r'^\s*\d+[\.\s、:]+(.*)', desc)
                    if not match: break
                    desc = match.group(1).strip()
                cleaned_tasks.append(f"{t['id']}. {desc}")
            final_task += "\n".join(cleaned_tasks)

        # Snapshot 使用说明
        final_task += "\n\nSNAPSHOT INSTRUCTION:\n"
        final_task += "You can call 'snapshot_page' at any time to get a text list of all interactive elements on the current page.\n"
        final_task += "Each element has a numeric index [1], [2], etc. Use these indexes for click and input actions.\n"
        final_task += "CRITICAL: After navigation or major UI changes (modal opens, dropdown expands, new page loads), you MUST call 'snapshot_page' first before interacting with new elements. The indexes from a previous page are INVALID after navigation.\n"
        final_task += "When unsure which element to interact with, call 'snapshot_page' to see the full list with text descriptions.\n"
        final_task += "Snapshot format: [index] <tag type='...' text='...' placeholder='...'>\n"

        # 极限效率版标记指令
        from datetime import datetime
        final_task += f"\n\nCURRENT TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        final_task += "\nCRITICAL PERFORMANCE & SYNC RULES:\n"
        final_task += "1. ACTION-TASK MAPPING: For EVERY sub-task that requires an action (click, input, select), you MUST call 'mark_task_complete(task_id=...)' in the SAME STEP as that action. DO NOT skip any task ID. Example: After clicking a button for task 8, immediately call mark_task_complete(task_id=8). IF YOU PERFORM MULTIPLE ACTIONS IN ONE STEP, YOU MUST CALL mark_task_complete FOR EACH CORRESPONDING TASK.\n"
        final_task += "2. NO JAVASCRIPT IN INPUT: When a task asks for a timestamp, YOU MUST compute the final string yourself (e.g., 'V8.01734892400').\n"
        final_task += "   - DO NOT output 'Date.now()' or '{{...}}' strings. Use the CURRENT TIME provided above to estimate a timestamp.\n"
        final_task += "3. DROPDOWN & MODAL ISOLATION: If an action (clicking a button/dropdown) triggers a UI change (modal opens/dropdown expands), YOU MUST STOP and WAIT for the next step to see the new elements. DO NOT attempt to interact with newly appeared elements (like dropdown options) in the same step as the click that opened them.\n"
        final_task += "4. ULTRALIGHT THINKING: Keep 'thinking' under 10 words. Just list next actions. Merge multiple INPUTS if they are on the same form, but NEVER merge a UI-opening click with its subsequent interaction. SPEED IS CRITICAL - respond as quickly as possible.\n"
        final_task += "5. RETRY LOGIC: If a previous 'save' or 'submit' failed (e.g., error toast), RE-VERIFY all fields. Re-select dropdowns and re-input text to ensure the form is complete. Often errors are caused by missing project selection.\n"
        final_task += "6. DO NOT REPEAT: If a task is complete, mark it and MOVE ON. Don't re-confirm unless the system requires it.\n"
        final_task += "7. VERIFICATION: Task 15/16 usually require checking the list. Ensure you are on the correct page and the new data is visible before marking complete.\n"

        if 'qwen' in self.model_name.lower() or 'deepseek' in self.model_name.lower():
            final_task += "8. EXTREMELY MINIMIZE output tokens for speed. Keep responses as short as possible while maintaining accuracy.\n"

        # 核心修复: 清理 task 长文本中的 URL，防止中文标点紧贴 URL 导致 browser-use 解析错误
        # 例如 "http://localhost:3000，" -> "http://localhost:3000 "
        try:
            # 在中文标点前加空格，避免它们成为 URL 的一部分
            final_task = re.sub(r'(https?://[^\s\u4e00-\u9fa5]+?)(?=[，；。、！])', r'\1 ', final_task)
            logger.info(f"🔧 Optimized task description for URL extraction")
        except:
            pass

        browser_profile = self._create_browser_profile()

        agent = Agent(
            task=final_task,
            llm=self.llm,
            controller=controller,
            browser_profile=browser_profile,
            use_vision=False,
            directly_open_url=False,  # 禁用自动初始导航，让访问URL成为主循环第一步，确保能正确截图
            max_actions_per_step=10,  # 增加步进密度，减少总步骤数，降低超时风险
            max_retries=1,  # 减少重试次数以提高速度 (从2改为1)
            max_failures=2,  # 减少最大失败次数，避免过长等待 (从默认3改为2)
            llm_timeout=60,  # 设置LLM调用超时为60秒（支持硅基流动等大模型API）
            step_timeout=90,  # 设置每步超时为90秒
            generate_gif=False,  # 显式禁用 GIF 生成
        )
        agent._task_was_done = False

        # Callback helper - 添加任务标记跟踪
        last_processed_step = 0
        last_marked_task_id = 0  # 跟踪上一次标记的任务ID

        async def on_step_end(agent_instance):
            nonlocal last_processed_step, last_marked_task_id

            if should_stop:
                do_stop = await should_stop() if asyncio.iscoroutinefunction(should_stop) else should_stop()
                if do_stop: raise KeyboardInterrupt("User requested stop")

            if _task_was_done:
                raise KeyboardInterrupt("Done")

            history = getattr(agent_instance, 'history', [])
            if hasattr(history, 'history'): history = history.history

            # 诊断日志：追踪 on_step_end 调用情况
            logger.info(f"[on_step_end] history_len={len(history)}, last_processed={last_processed_step}")

            if len(history) > last_processed_step:
                for i in range(last_processed_step, len(history)):
                    step = history[i]
                    # Log logic here
                    try:
                        actions = []
                        if hasattr(step, 'model_output') and step.model_output and hasattr(step.model_output, 'action'):
                            raw = step.model_output.action
                            actions = raw if isinstance(raw, list) else [raw]

                        logger.info(f"[on_step_end] Processing step {i+1}, actions_count={len(actions)}, action_types={[list(a.model_dump().keys()) if hasattr(a, 'model_dump') else str(a) for a in actions]}")

                        # 检查这一步是否调用了mark_task_complete
                        step_has_task_complete = False
                        step_marked_task_id = None
                        for action in actions:
                            action_dict = action.model_dump() if hasattr(action, 'model_dump') else getattr(action,
                                                                                                            '_action_dict',
                                                                                                            {})
                            if 'mark_task_complete' in action_dict:
                                step_has_task_complete = True
                                step_marked_task_id = action_dict['mark_task_complete'].get('task_id')
                                last_marked_task_id = step_marked_task_id
                                break

                        # 检查这一步是否有实际操作（非mark_task_complete的操作）
                        has_real_action = False
                        for action in actions:
                            action_dict = action.model_dump() if hasattr(action, 'model_dump') else getattr(action,
                                                                                                            '_action_dict',
                                                                                                            {})
                            for key in action_dict.keys():
                                if key not in ['mark_task_complete', 'done']:
                                    has_real_action = True
                                    break
                            if has_real_action:
                                break

                        action_str = " | ".join([self._format_action(a) for a in actions])
                        log_content = f"\n[Step {i + 1}]\n执行: {action_str}\n"

                        logger.info(f"[on_step_end] Step {i+1} has_real_action={has_real_action}, action_str='{action_str}', callback={'YES' if callback else 'NO'}")

                        if callback and has_real_action:
                            if asyncio.iscoroutinefunction(callback):
                                await callback({'type': 'log', 'content': log_content})
                            else:
                                callback({'type': 'log', 'content': log_content})

                        # 关键修复：如果这一步有实际操作但没有调用mark_task_complete，
                        # 自动标记 planned_tasks 中第一个未完成的任务（不依赖连续ID假设）
                        if has_real_action and not step_has_task_complete and planned_tasks:
                            # 找出第一个尚未完成的任务
                            next_pending_task = None
                            for task in planned_tasks:
                                if task.get('status') != 'completed':
                                    next_pending_task = task
                                    break

                            if next_pending_task:
                                next_expected_task_id = next_pending_task['id']
                                # 自动补充标记这个任务
                                logger.warning(
                                    f"⚠️ Auto-fixing: Step {i + 1} had actions but no mark_task_complete. Auto-marking task {next_expected_task_id} as completed.")
                                data = {'task_id': int(next_expected_task_id), 'status': 'completed'}
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                                last_marked_task_id = next_expected_task_id

                        # 每步截图：在步骤执行完成后保存当前页面截图
                        # 优化：只对有实际操作的步骤截图，降低质量
                        if self.enable_gif and has_real_action:
                            try:
                                from django.conf import settings
                                browser_session = getattr(agent_instance, 'browser_session', None)
                                if browser_session:
                                    page = await browser_session.get_current_page()
                                    if page:
                                        # 通过参数传递 page 和 step_idx 和 action，避免闭包变量被后续迭代覆盖
                                        async def _capture_and_save(_page, _step_idx, _action):
                                            try:
                                                url = await _page.evaluate('() => window.location.href') if _page else 'no page'
                                                logger.info(f"📸 Capturing screenshot for step {_step_idx}, action={_action}, url={url}")
                                                b64 = await _page.screenshot(format='jpeg', quality=50)
                                                ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                                                safe_case = "".join(c for c in self.case_name if c.isalnum() or c in ('_', '-')).rstrip()
                                                rel_path = f"media/ai_screenshots/{safe_case}_{ts}_step_{_step_idx:03d}.jpg"
                                                abs_path = os.path.join(settings.BASE_DIR, rel_path)
                                                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                                                with open(abs_path, 'wb') as f:
                                                    f.write(base64.b64decode(b64))
                                                self.screenshots_sequence.append(rel_path)
                                                logger.info(f"📸 Screenshot saved for step {_step_idx}: {rel_path}")
                                            except Exception as inner_err:
                                                logger.warning(f"⚠️ Screenshot failed for step {_step_idx}: {inner_err}")
                                        # 同步等待截图完成，确保截取到当前步骤的页面状态
                                        await _capture_and_save(page, i + 1, action_str)
                            except Exception as screenshot_err:
                                logger.warning(f"⚠️ Screenshot init failed for step {i+1}: {screenshot_err}")

                    except Exception as e:
                        logger.warning(f"⚠️ Error in on_step_end processing step {i+1}: {e}", exc_info=True)
                last_processed_step = len(history)
            else:
                logger.info(f"[on_step_end] No new steps to process")

            # 自动刷新 snapshot：检测 URL 变化或页面变化
            try:
                page = None
                # 尝试从 agent_instance 获取 browser/page（多种路径兼容不同 browser-use 版本）
                browser = getattr(agent_instance, 'browser', None)
                if browser:
                    if hasattr(browser, 'page'):
                        page = browser.page
                    elif hasattr(browser, 'pages') and browser.pages:
                        page = browser.pages[0]

                if not page:
                    browser_session = getattr(agent_instance, 'browser_session', None)
                    if browser_session:
                        if hasattr(browser_session, 'page'):
                            page = browser_session.page
                        elif hasattr(browser_session, 'browser'):
                            b = browser_session.browser
                            if hasattr(b, 'page'):
                                page = b.page
                            elif hasattr(b, 'pages') and b.pages:
                                page = b.pages[0]

                if page:
                    current_url = page.url
                    if current_url != self._last_snapshot_url:
                        logger.info(f"📸 Auto-refresh snapshot: URL changed from '{self._last_snapshot_url}' to '{current_url}'")
                        self.current_snapshot = await PageSnapshot.capture(page)
                        self._last_snapshot_url = current_url
                        if callback:
                            data = {
                                'type': 'snapshot',
                                'content': self.current_snapshot.snapshot_text,
                                'element_count': len(self.current_snapshot.elements),
                                'elements': self.current_snapshot.elements,
                                'url': current_url,
                                'title': self.current_snapshot.title,
                                'auto': True
                            }
                            if asyncio.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)
            except Exception as e:
                logger.debug(f"Auto-snapshot refresh failed: {e}")

        try:
            # Try to pass callback
            import inspect
            sig = inspect.signature(agent.run)
            if 'on_step_end' in sig.parameters:
                await agent.run(max_steps=100, on_step_end=on_step_end)
            else:
                await agent.run(max_steps=100)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            raise
        finally:
            # 单条用例执行完毕后关闭浏览器，避免进程残留
            try:
                browser_session = getattr(agent, 'browser_session', None)
                if browser_session:
                    await browser_session.kill()
                    logger.info("✓ browser_session 已关闭")
            except Exception as e:
                logger.warning(f"关闭 browser_session 时出错: {e}")
            try:
                if hasattr(controller, 'close'):
                    await controller.close()
                    logger.info("✓ controller 已关闭")
            except Exception as e:
                logger.warning(f"关闭 controller 时出错: {e}")

        # 在任务结束时检查不一致的任务状态
        history = getattr(agent, 'history', [])
        if history:
            logger.info("🔍 Performing final task status consistency check")
            # 检查是否有任务执行了但未标记完成
            executed_tasks_info = self._find_executed_tasks(history)
            if executed_tasks_info and executed_tasks_info.get('unmarked_actions'):
                logger.warning(
                    f"⚠️ Found {executed_tasks_info['executed_actions']} executed actions, but only {len(executed_tasks_info['marked_tasks'])} tasks were explicitly marked complete")
                logger.warning(f"⚠️ Unmarked actions: {executed_tasks_info['unmarked_actions']}")
                logger.warning("⚠️ This indicates the AI agent did not follow the 'mark_task_complete' rule properly.")

        # 解析最终 AI 判定的 success 状态
        ai_success = None
        if history:
            history_items = getattr(history, 'history', []) or getattr(history, 'steps', [])
            for step in reversed(history_items):
                # browser-use AgentOutput: step.model_output.action 是 action 列表
                model_output = getattr(step, 'model_output', None)
                if model_output:
                    actions = getattr(model_output, 'action', None)
                    if actions:
                        for action in actions:
                            try:
                                if hasattr(action, 'model_dump'):
                                    action_dict = action.model_dump(exclude_none=True, mode='json')
                                elif hasattr(action, '__dict__'):
                                    action_dict = dict(action.__dict__)
                                else:
                                    action_dict = {}
                                for action_name, params in action_dict.items():
                                    if action_name == 'done':
                                        if isinstance(params, dict):
                                            ai_success = params.get('success')
                                        break
                                if ai_success is not None:
                                    break
                            except Exception:
                                pass
                    if ai_success is not None:
                        break
                # 兜底：尝试直接从 step 获取 action（兼容其他格式）
                action_model = getattr(step, 'action', None) or getattr(step, 'action_model', None)
                if action_model:
                    action_name = getattr(action_model, 'action', None) or getattr(action_model, 'action_name', None)
                    if action_name == 'done':
                        params = getattr(action_model, 'params', None) or getattr(action_model, 'parameters', None) or {}
                        if isinstance(params, dict):
                            ai_success = params.get('success')
                        break

        return {'history': history, 'screenshots_sequence': self.screenshots_sequence, 'success': ai_success}

    def _find_executed_tasks(self, history):
        """
        通过分析执行历史找出已执行但未标记完成的任务
        """
        if not history or not hasattr(history, 'steps'):
            return []

        executed_actions = {}  # 已执行的操作类型和索引，以及对应的步骤
        marked_tasks = set()  # 已标记完成的任务ID

        # 分析执行历史
        for step_idx, step in enumerate(getattr(history, 'steps', [])):
            # 检查每一步中的actions
            actions = getattr(step, 'actions', [])
            for action in actions:
                # 记录已执行的操作
                if hasattr(action, 'input'):
                    action_key = f"input_{action.input.index}"
                    executed_actions[action_key] = {
                        'step': step_idx,
                        'action': 'input',
                        'index': action.input.index
                    }
                elif hasattr(action, 'click'):
                    action_key = f"click_{action.click.index}"
                    executed_actions[action_key] = {
                        'step': step_idx,
                        'action': 'click',
                        'index': action.click.index
                    }
                elif hasattr(action, 'switch_tab'):
                    action_key = f"switch_tab_{action.switch_tab.tab_id}"
                    executed_actions[action_key] = {
                        'step': step_idx,
                        'action': 'switch_tab',
                        'tab_id': action.switch_tab.tab_id
                    }

                # 记录已标记完成的任务
                if hasattr(action, 'mark_task_complete'):
                    marked_tasks.add(action.mark_task_complete.task_id)

        # 理想情况下应该有一个映射机制来关联操作和任务，但由于我们没有这个映射，
        # 我们只能记录未标记完成的执行操作作为调试信息
        unmarked_actions = []
        for action_key, action_info in executed_actions.items():
            unmarked_actions.append({
                'action': action_info['action'],
                'step': action_info['step'],
                'details': action_key
            })

        return {
            'marked_tasks': list(marked_tasks),
            'executed_actions': len(executed_actions),
            'unmarked_actions': unmarked_actions
        }

    async def run_full_process(self, task_description: str, analysis_callback=None, step_callback=None,
                               should_stop=None):
        planned_tasks = await self.analyze_task(task_description)
        if analysis_callback:
            if asyncio.iscoroutinefunction(analysis_callback):
                await analysis_callback(planned_tasks)
            else:
                analysis_callback(planned_tasks)

        return await self.run_task(task_description, planned_tasks, step_callback, should_stop)


class PersistentBrowserSession:
    """持久化浏览器会话，用于执行多个测试用例时复用浏览器"""
    
    def __init__(self, execution_mode='text', enable_gif=True):
        # Ensure browser-use patches are applied before use
        _apply_browser_use_patches()

        self.execution_mode = 'text'
        self.enable_gif = enable_gif
        self.controller = None
        self.browser_profile = None
        self.browser_session = None
        self.agent = None
        self._task_was_done = False
        self.current_snapshot = None
        self._last_snapshot_url = ""
        
        from apps.requirement_analysis.models import AIModelConfig
        
        role_name = 'browser_use_text'
        config_obj = AIModelConfig.objects.filter(role=role_name, is_active=True).first()
        
        model_config = {}
        if config_obj:
            model_config = {
                'api_key': config_obj.api_key,
                'base_url': config_obj.base_url,
                'model_name': config_obj.model_name,
                'provider': config_obj.model_type,
                'temperature': config_obj.temperature
            }
        
        self.api_key = model_config.get('api_key') or os.getenv('AUTH_TOKEN')
        self.base_url = model_config.get('base_url') or os.getenv('BASE_URL')
        self.model_name = model_config.get('model_name') or os.getenv('MODEL_NAME')
        self.provider = model_config.get('provider', 'openai')
        
        if not self.api_key:
            raise ValueError(f"No API Key found for mode: {execution_mode}")
        
        final_temperature = 0.0
        special_model_temperature_map = {
            'kimi-2.5': 1.0,
            'kimi-k2.5': 1.0,
            'kimi': 1.0,
        }
        
        model_name_lower = self.model_name.lower()
        for model_keyword, temp in special_model_temperature_map.items():
            if model_keyword in model_name_lower:
                final_temperature = temp
                logger.info(f"✅ 检测到特殊模型 '{self.model_name}'，使用强制 temperature={temp}")
                break
        else:
            if 'temperature' in model_config:
                final_temperature = model_config['temperature']
            else:
                final_temperature = 0.0
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=final_temperature,
            callbacks=[RawResponseLogger()]
        )
        
        try:
            object.__setattr__(self.llm, 'provider', self.provider)
            object.__setattr__(self.llm, 'model', self.model_name)
        except:
            if not hasattr(self.llm, '__pydantic_extra__') or self.llm.__pydantic_extra__ is None:
                self.llm.__pydantic_extra__ = {}
            self.llm.__pydantic_extra__['provider'] = self.provider
            self.llm.__pydantic_extra__['model'] = self.model_name
    
    def _create_browser_profile(self):
        return _create_browser_profile_common(keep_alive=True)
    
    def initialize(self):
        """初始化浏览器会话"""
        self.controller = Controller()
        self.browser_profile = self._create_browser_profile()
        
        # 创建 BrowserSession，这是实际管理浏览器实例的对象
        self.browser_session = BrowserSession(
            browser_profile=self.browser_profile
        )
        
        @self.controller.action('Done')
        async def done(success: bool = True, text: str = ""):
            self._task_was_done = True
            return f"Finished: {text}"
        
        @self.controller.action('mark_task_complete')
        async def mark_task_complete(task_id: int):
            logger.info(f"✅ Explicitly marking task {task_id} as completed")
            return f"Task {task_id} marked completed"

        @self.controller.action('snapshot_page')
        async def snapshot_page(browser):
            """捕获当前页面快照，返回可交互元素索引列表"""
            try:
                page = browser.page
                self.current_snapshot = await PageSnapshot.capture(page)
                self._last_snapshot_url = self.current_snapshot.url
                snapshot_text = self.current_snapshot.snapshot_text
                logger.info(f"📸 Snapshot captured: {len(self.current_snapshot.elements)} elements at {self.current_snapshot.url}")
                return f"Page snapshot captured. {len(self.current_snapshot.elements)} interactive elements found.\n\n{snapshot_text}"
            except Exception as e:
                logger.warning(f"Failed to capture snapshot: {e}")
                return f"Snapshot failed: {e}"
        
        # 预创建一个 Agent 实例（可选，主要用于占位）
        self.agent = Agent(
            task="",
            llm=self.llm,
            controller=self.controller,
            browser_session=self.browser_session,
            use_vision=False,
            max_actions_per_step=10,
            max_retries=1,
            max_failures=2,
            llm_timeout=60,
            step_timeout=90,
            generate_gif=False,  # 显式禁用 GIF 生成
        )
        self.agent._task_was_done = False
    
    async def run_single_case(self, task_description: str, analysis_callback=None, step_callback=None, should_stop=None, case_name=None, task_id_offset=0):
        """在持久浏览器会话中运行单个测试用例"""
        if not self.browser_session:
            logger.info(f"🔄 初始化浏览器会话 for case: {case_name}")
            self.initialize()
        else:
            logger.info(f"🔄 复用已有浏览器会话 for case: {case_name}")
        
        self._task_was_done = False
        self.screenshots_sequence = []  # 每次运行前清空截图列表，避免套件执行时累积
        
        # 每次运行用例时重新创建 Agent，但复用同一个 BrowserSession（浏览器会话）
        from apps.requirement_analysis.models import AIModelConfig
        role_name = 'browser_use_text'
        config_obj = AIModelConfig.objects.filter(role=role_name, is_active=True).first()
        model_config = {}
        if config_obj:
            model_config = {
                'api_key': config_obj.api_key,
                'base_url': config_obj.base_url,
                'model_name': config_obj.model_name,
                'provider': config_obj.model_type,
                'temperature': config_obj.temperature
            }
        
        planned_tasks = []
        try:
            # 快速路径：如果用户输入已经是编号步骤，直接解析，不走 LLM
            lines = [line.strip() for line in task_description.split('\n') if line.strip()]
            numbered_lines = []
            for line in lines:
                match = re.match(r'^\s*\d+[\.\s、:)\]]\s*(.*)', line)
                if match:
                    numbered_lines.append(match.group(1).strip())

            if len(numbered_lines) >= 1 and len(numbered_lines) >= len(lines) * 0.5:
                cleaned_steps = []
                for desc in numbered_lines:
                    while True:
                        m = re.match(r'^\s*\d+[\.\s、:]+(.*)', desc)
                        if not m:
                            break
                        desc = m.group(1).strip()
                    if desc:
                        cleaned_steps.append(desc)
                planned_tasks = [{'id': i + 1, 'description': s, 'status': 'pending'} for i, s in enumerate(cleaned_steps)]
                logger.info(f"[run_single_case] Parsed numbered steps directly, skipping LLM for case: {case_name}")
            else:
                # 尝试从缓存获取
                try:
                    from .ai_cache import TaskAnalysisCache
                    cached_result = TaskAnalysisCache.get(task_description)
                    if cached_result is not None:
                        planned_tasks = cached_result
                        logger.info(f"[run_single_case] Cache hit, skipping LLM call for case: {case_name}")
                except Exception as e:
                    logger.warning(f"[run_single_case] Cache check failed: {e}")

            if not planned_tasks:
                prompt = f"Break down this task into steps: {task_description}. Return JSON list of strings."
                response = await self.llm.ainvoke(prompt)
                content = response.content.strip() if hasattr(response, 'content') else str(response)
                
                try:
                    import json
                    match = re.search(r'(\[.*\])', content, re.DOTALL)
                    if match: 
                        planned_tasks = json.loads(match.group(1))
                except:
                    pass
                
                if not planned_tasks:
                    planned_tasks = [s.strip() for s in task_description.split('\n') if s.strip()]
                
                cleaned_steps = []
                for s in planned_tasks:
                    desc = s
                    while True:
                        match = re.match(r'^\s*\d+[\.\s、:]+(.*)', desc)
                        if not match: break
                        desc = match.group(1).strip()
                    if desc:
                        cleaned_steps.append(desc)
                
                planned_tasks = [{'id': i + 1, 'description': s, 'status': 'pending'} for i, s in enumerate(cleaned_steps)]
                
                try:
                    from .ai_cache import TaskAnalysisCache
                    TaskAnalysisCache.set(task_description, planned_tasks, ttl_hours=24)
                except Exception as e:
                    logger.warning(f"[run_single_case] Cache save failed: {e}")
        except:
            planned_tasks = [{'id': 1, 'description': task_description, 'status': 'pending'}]
        
        if analysis_callback:
            try:
                logger.info(f"📞 Calling analysis_callback for case: {case_name}")
                if asyncio.iscoroutinefunction(analysis_callback):
                    await analysis_callback(planned_tasks)
                else:
                    analysis_callback(planned_tasks)
                logger.info(f"✅ analysis_callback completed for case: {case_name}")
            except Exception as e:
                logger.error(f"❌ analysis_callback failed for case {case_name}: {e}", exc_info=True)
                raise
        
        logger.info(f"📝 Building final_task for case: {case_name}")
        final_task = task_description
        if planned_tasks:
            final_task += "\n\nIMPORTANT INSTRUCTION:\n"
            final_task += "You have a list of sub-tasks. Execute strictly in order.\n"
            final_task += "CRITICAL: MUST call 'mark_task_complete(task_id=...)' IMMEDIATELY after verifying each sub-task completion. NEVER skip this step.\n"
            final_task += "IMPORTANT: If a sub-task is already fulfilled, YOU MUST mark it complete in your VERY FIRST STEP.\n"
            final_task += "Sub-tasks (Execute in order):\n"
            cleaned_tasks = []
            for t in planned_tasks:
                desc = t['description']
                while True:
                    match = re.match(r'^\s*\d+[\.\s、:]+(.*)', desc)
                    if not match: break
                    desc = match.group(1).strip()
                cleaned_tasks.append(f"{t['id']}. {desc}")
            final_task += "\n".join(cleaned_tasks)
            final_task += "\n\nPERFORMANCE OPTIMIZATION RULES:\n"
            final_task += "1. NO JAVASCRIPT IN INPUT: Never type or input JavaScript code into form fields, text boxes, or any user input areas. Only type plain text, numbers, or natural language as a normal user would.\n"
            final_task += "2. DROPDOWN & MODAL ISOLATION: If you need to open a dropdown or modal, ONLY select from that dropdown/modal in the CURRENT step. Do NOT combine other page interactions in the same step.\n"
            final_task += "3. ULTRALIGHT THINKING: For simple interactions (click, input, navigate), respond within 50 tokens. Do NOT explain your reasoning.\n"
            final_task += "4. RETRY LOGIC: If an action fails (e.g., element not found), retry ONCE with a slightly different approach (scroll, wait, or alternative selector). After one retry, mark as failed and continue.\n"
            final_task += "5. DO NOT REPEAT: If an action was just performed (e.g., a link was already clicked), do NOT attempt to click it again. Instead, verify the result or move to the next step.\n"
            final_task += "6. VERIFICATION: Before marking a sub-task complete, verify the result matches the expected outcome (e.g., correct page loaded, correct text displayed).\n"
        
        final_task += "\n\nSNAPSHOT INSTRUCTION:\n"
        final_task += "You can call 'snapshot_page' at any time to get a text list of all interactive elements on the current page.\n"
        final_task += "Each element has a numeric index [1], [2], etc. Use these indexes for click and input actions.\n"
        final_task += "CRITICAL: After navigation or major UI changes (modal opens, dropdown expands, new page loads), you MUST call 'snapshot_page' first before interacting with new elements. The indexes from a previous page are INVALID after navigation.\n"
        final_task += "When unsure which element to interact with, call 'snapshot_page' to see the full list with text descriptions.\n"
        final_task += "Snapshot format: [index] <tag type='...' text='...' placeholder='...'>\n"

        from datetime import datetime
        final_task += f"\n\nCURRENT TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        try:
            final_task = re.sub(r'(https?://[^\s\u4e00-\u9fa5]+?)(?=[，；。、！])', r'\1 ', final_task)
        except:
            pass
        
        # 创建新的 Agent，但复用同一个 BrowserSession（浏览器会话）
        # 这样多个用例可以在同一个浏览器实例中运行，保持登录状态
        logger.info(f"🤖 创建 Agent for case: {case_name}, browser_session: {self.browser_session}")
        try:
            agent = Agent(
                task=final_task,
                llm=self.llm,
                controller=self.controller,
                browser_session=self.browser_session,  # 复用同一个浏览器会话
                use_vision=False,
                directly_open_url=False,  # 禁用自动初始导航，让访问URL成为主循环第一步，确保能正确截图
                max_actions_per_step=10,
                max_retries=1,
                max_failures=2,
                llm_timeout=60,
                step_timeout=90,
                generate_gif=False,  # 显式禁用 GIF 生成
            )
            agent._task_was_done = False
            logger.info(f"✅ Agent 创建完成 for case: {case_name}")
        except Exception as e:
            logger.error(f"❌ Agent 创建失败 for case {case_name}: {e}", exc_info=True)
            raise
        
        last_processed_step = 0
        last_marked_task_id = 0
        step_task_ids = {}  # 记录每个步骤对应的全局唯一 task_id
        
        async def on_step_end(agent_instance):
            nonlocal last_processed_step, last_marked_task_id, step_task_ids
            
            if should_stop:
                do_stop = await should_stop() if asyncio.iscoroutinefunction(should_stop) else should_stop()
                if do_stop: raise KeyboardInterrupt("User requested stop")
            
            if self._task_was_done:
                raise KeyboardInterrupt("Done")
            
            history = getattr(agent_instance, 'history', [])
            if hasattr(history, 'history'): history = history.history
            
            # 诊断日志：追踪 on_step_end 调用情况
            logger.info(f"[on_step_end_persistent] history_len={len(history)}, last_processed={last_processed_step}")
            
            if len(history) > last_processed_step:
                for i in range(last_processed_step, len(history)):
                    step = history[i]
                    try:
                        actions = []
                        if hasattr(step, 'model_output') and step.model_output and hasattr(step.model_output, 'action'):
                            raw = step.model_output.action
                            actions = raw if isinstance(raw, list) else [raw]
                        
                        logger.info(f"[on_step_end_persistent] Processing step {i+1}, actions_count={len(actions)}, action_types={[list(a.model_dump().keys()) if hasattr(a, 'model_dump') else str(a) for a in actions]}")
                        
                        step_has_task_complete = False
                        step_marked_task_id = None
                        for action in actions:
                            action_dict = action.model_dump() if hasattr(action, 'model_dump') else getattr(action, '_action_dict', {})
                            if 'mark_task_complete' in action_dict:
                                step_has_task_complete = True
                                step_marked_task_id = action_dict['mark_task_complete'].get('task_id')
                                last_marked_task_id = step_marked_task_id
                                # AI 已经在 final_task 中收到了偏移后的 task_id（on_analysis_complete 修改了 planned_tasks 的 id）
                                # 所以 AI 调用 mark_task_complete 时使用的已经是全局唯一ID，不需要再加偏移
                                global_task_id = int(step_marked_task_id)
                                # 记录步骤索引对应的全局唯一task_id，供run_suite后续使用
                                step_task_ids[i] = global_task_id
                                # 调用回调更新任务状态，与单场景执行保持一致
                                if step_callback:
                                    data = {'task_id': global_task_id, 'status': 'completed'}
                                    if asyncio.iscoroutinefunction(step_callback):
                                        await step_callback(data)
                                    else:
                                        step_callback(data)
                                break
                        
                        has_real_action = False
                        for action in actions:
                            action_dict = action.model_dump() if hasattr(action, 'model_dump') else getattr(action, '_action_dict', {})
                            for key in action_dict.keys():
                                if key not in ['mark_task_complete', 'done']:
                                    has_real_action = True
                                    break
                            if has_real_action:
                                break
                        
                        action_str = " | ".join([self._format_action_persistent(a) for a in actions])
                        log_content = f"\n[Step {i + 1}]\n执行: {action_str}\n"
                        
                        logger.info(f"[on_step_end_persistent] Step {i+1} has_real_action={has_real_action}, action_str='{action_str}', callback={'YES' if step_callback else 'NO'}")
                        
                        if step_callback and has_real_action:
                            if asyncio.iscoroutinefunction(step_callback):
                                await step_callback({'type': 'log', 'content': log_content})
                            else:
                                step_callback({'type': 'log', 'content': log_content})

                        # 每步截图：在步骤执行完成后保存当前页面截图
                        if self.enable_gif and has_real_action:
                            try:
                                from django.conf import settings
                                browser_session = getattr(agent_instance, 'browser_session', None)
                                if browser_session:
                                    page = None
                                    # 优先使用 get_current_page() 方法获取页面 (async 方法需要 await)
                                    if hasattr(browser_session, 'get_current_page'):
                                        try:
                                            page = await browser_session.get_current_page()
                                        except Exception:
                                            page = None
                                    if not page and hasattr(browser_session, 'page'):
                                        page = browser_session.page
                                    if not page and hasattr(browser_session, 'browser'):
                                        b = browser_session.browser
                                        if hasattr(b, 'page'):
                                            page = b.page
                                        elif hasattr(b, 'pages') and b.pages:
                                            page = b.pages[0]
                                    if page:
                                        async def _capture_and_save(_page, _step_idx, _action):
                                            try:
                                                url = await _page.evaluate('() => window.location.href') if _page else 'no page'
                                                logger.info(f"📸 Capturing screenshot for step {_step_idx}, action={_action}, url={url}")
                                                b64 = await _page.screenshot(format='jpeg', quality=50)
                                                ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                                                safe_case = "".join(c for c in case_name if c.isalnum() or c in ('_', '-')).rstrip()
                                                rel_path = f"media/ai_screenshots/{safe_case}_{ts}_step_{_step_idx:03d}.jpg"
                                                abs_path = os.path.join(settings.BASE_DIR, rel_path)
                                                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                                                with open(abs_path, 'wb') as f:
                                                    f.write(base64.b64decode(b64))
                                                self.screenshots_sequence.append(rel_path)
                                                logger.info(f"📸 Screenshot saved for step {_step_idx}: {rel_path}")
                                            except Exception as inner_err:
                                                logger.warning(f"⚠️ Screenshot failed for step {_step_idx}: {inner_err}")
                                        # 同步等待截图完成，确保截取到当前步骤的页面状态
                                        await _capture_and_save(page, i + 1, action_str)
                            except Exception as screenshot_err:
                                logger.warning(f"⚠️ Screenshot init failed for step {i+1}: {screenshot_err}")

                        if has_real_action and not step_has_task_complete and planned_tasks:
                            # 找出第一个尚未完成的任务（不依赖连续ID假设）
                            next_pending_task = None
                            for task in planned_tasks:
                                if task.get('status') != 'completed':
                                    next_pending_task = task
                                    break

                            if next_pending_task:
                                next_expected_task_id = next_pending_task['id']
                                logger.warning(
                                    f"⚠️ Auto-fixing: Step {i + 1} had actions but no mark_task_complete. Auto-marking task {next_expected_task_id} as completed.")
                                data = {'task_id': int(next_expected_task_id), 'status': 'completed'}
                                if step_callback:
                                    if asyncio.iscoroutinefunction(step_callback):
                                        await step_callback(data)
                                    else:
                                        step_callback(data)
                                last_marked_task_id = next_expected_task_id
                    except Exception as e:
                        logger.warning(f"⚠️ Error in on_step_end processing step {i+1}: {e}", exc_info=True)
                last_processed_step = len(history)
            else:
                logger.info(f"[on_step_end_persistent] No new steps to process")

            # 自动刷新 snapshot：检测 URL 变化或页面变化
            try:
                page = None
                browser = getattr(agent_instance, 'browser', None)
                if browser:
                    if hasattr(browser, 'page'):
                        page = browser.page
                    elif hasattr(browser, 'pages') and browser.pages:
                        page = browser.pages[0]

                if not page:
                    browser_session = getattr(agent_instance, 'browser_session', None)
                    if browser_session:
                        if hasattr(browser_session, 'page'):
                            page = browser_session.page
                        elif hasattr(browser_session, 'browser'):
                            b = browser_session.browser
                            if hasattr(b, 'page'):
                                page = b.page
                            elif hasattr(b, 'pages') and b.pages:
                                page = b.pages[0]

                if page:
                    current_url = page.url
                    if current_url != self._last_snapshot_url:
                        logger.info(f"📸 Auto-refresh snapshot: URL changed from '{self._last_snapshot_url}' to '{current_url}'")
                        self.current_snapshot = await PageSnapshot.capture(page)
                        self._last_snapshot_url = current_url
                        if step_callback:
                            data = {
                                'type': 'snapshot',
                                'content': self.current_snapshot.snapshot_text,
                                'element_count': len(self.current_snapshot.elements),
                                'elements': self.current_snapshot.elements,
                                'url': current_url,
                                'title': self.current_snapshot.title,
                                'auto': True
                            }
                            if asyncio.iscoroutinefunction(step_callback):
                                await step_callback(data)
                            else:
                                step_callback(data)
            except Exception as e:
                logger.debug(f"Auto-snapshot refresh failed: {e}")
        
        try:
            import inspect
            logger.info(f"🚀 开始执行 Agent.run() for case: {case_name}")
            sig = inspect.signature(agent.run)
            if 'on_step_end' in sig.parameters:
                history = await agent.run(max_steps=100, on_step_end=on_step_end)
            else:
                history = await agent.run(max_steps=100)
            logger.info(f"✅ Agent.run() 执行完成 for case: {case_name}, history steps: {len(history) if history else 0}")
        except KeyboardInterrupt:
            logger.info(f"⏹️ Agent.run() 被中断 for case: {case_name}")
            history = getattr(agent, 'history', [])
        except Exception as e:
            logger.error(f"❌ Agent execution error for case {case_name}: {e}")
            raise
        
        # 解析最终 AI 判定的 success 状态
        ai_success = None
        if history:
            history_items = getattr(history, 'history', []) or getattr(history, 'steps', [])
            for step in reversed(history_items):
                model_output = getattr(step, 'model_output', None)
                if model_output:
                    actions = getattr(model_output, 'action', None)
                    if actions:
                        for action in actions:
                            try:
                                if hasattr(action, 'model_dump'):
                                    action_dict = action.model_dump(exclude_none=True, mode='json')
                                elif hasattr(action, '__dict__'):
                                    action_dict = dict(action.__dict__)
                                else:
                                    action_dict = {}
                                for action_name, params in action_dict.items():
                                    if action_name == 'done':
                                        if isinstance(params, dict):
                                            ai_success = params.get('success')
                                        break
                                if ai_success is not None:
                                    break
                            except Exception:
                                pass
                    if ai_success is not None:
                        break
                action_model = getattr(step, 'action', None) or getattr(step, 'action_model', None)
                if action_model:
                    action_name = getattr(action_model, 'action', None) or getattr(action_model, 'action_name', None)
                    if action_name == 'done':
                        params = getattr(action_model, 'params', None) or getattr(action_model, 'parameters', None) or {}
                        if isinstance(params, dict):
                            ai_success = params.get('success')
                        break

        logger.info(f"🏁 run_single_case returning for case: {case_name}, screenshots: {len(self.screenshots_sequence)}, history steps: {len(history) if history else 0}")
        return {'history': history, 'screenshots_sequence': self.screenshots_sequence, 'success': ai_success, 'step_task_ids': step_task_ids}
    
    def _format_action_persistent(self, action):
        try:
            action_dict = {}
            if hasattr(action, 'model_dump'):
                action_dict = action.model_dump()
            elif hasattr(action, '_action_dict'):
                action_dict = action._action_dict
            elif hasattr(action, '_dict'):
                action_dict = action._dict
            elif isinstance(action, dict):
                action_dict = action
            else:
                return str(action)
            
            if not action_dict: return "待机"
            
            descriptions = []
            for name, params in action_dict.items():
                # 将 snapshot_page 加入白名单，即使 params 为空也显示
                if not params and name not in ['scroll_down', 'scroll_up', 'done', 'snapshot_page']: continue
                
                if name in ['go_to_url', 'navigate']:
                    url = params.get('url') if isinstance(params, dict) else params
                    descriptions.append(f"访问: {url}")
                elif name in ['click_element', 'click']:
                    index = params.get('index') if isinstance(params, dict) else params
                    descriptions.append(f"点击[{index}]")
                elif name in ['input_text', 'input']:
                    text = params.get('text') if isinstance(params, dict) else None
                    descriptions.append(f"输入: '{text}'")
                elif name == 'switch_tab':
                    index = params.get('index', params)
                    descriptions.append(f"切换标签 {index}")
                elif name == 'open_new_tab':
                    url = params.get('url', params)
                    descriptions.append(f"新标签打开: {url}")
                elif name == 'snapshot_page':
                    descriptions.append("📸 捕获页面快照")
                elif name == 'done':
                    descriptions.append("任务完成")
                else:
                    descriptions.append(f"{name}")
            return " | ".join(descriptions)
        except Exception as e:
            logger.debug(f"_format_action_persistent error: {e}, action={action}")
            return str(action)
    
    async def close_async(self):
        """异步关闭浏览器会话 - 强制杀死浏览器进程"""
        # 优先关闭 browser_session，因为它管理实际的浏览器实例
        if self.browser_session:
            try:
                # BrowserSession 没有 close()，只有 kill() 能真正关闭浏览器进程
                await self.browser_session.kill()
                logger.info("✓ browser_session 已强制关闭")
            except Exception as e:
                logger.warning(f"关闭 browser_session 时出错: {e}")
        
        # 然后关闭 controller
        if hasattr(self.controller, 'close'):
            try:
                await self.controller.close()
                logger.info("✓ controller 已关闭")
            except:
                pass
    
    def close(self):
        """同步关闭浏览器会话 - 确保浏览器进程被正确杀死"""
        import asyncio
        
        # 优先关闭 browser_session，因为它管理实际的浏览器实例
        if self.browser_session:
            try:
                # 尝试获取当前事件循环
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                
                if loop and loop.is_running():
                    # 如果事件循环正在运行，需要创建一个新任务并等待它完成
                    # 使用 run_coroutine_threadsafe 在运行中的循环中执行关闭
                    future = asyncio.run_coroutine_threadsafe(self.browser_session.kill(), loop)
                    try:
                        future.result(timeout=10)  # 等待最多10秒
                        logger.info("✓ browser_session 已强制关闭")
                    except Exception as e:
                        logger.warning(f"等待 browser_session 关闭时超时或出错: {e}")
                else:
                    # 没有运行的事件循环，直接运行
                    asyncio.run(self.browser_session.kill())
                    logger.info("✓ browser_session 已强制关闭")
            except Exception as e:
                logger.warning(f"关闭 browser_session 时出错: {e}")
        
        # 然后关闭 controller
        if hasattr(self.controller, 'close'):
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                
                if loop and loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(self.controller.close(), loop)
                    try:
                        future.result(timeout=5)
                        logger.info("✓ controller 已关闭")
                    except:
                        pass
                else:
                    asyncio.run(self.controller.close())
                    logger.info("✓ controller 已关闭")
            except:
                pass
