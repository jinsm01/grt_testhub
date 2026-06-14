import os
# 必须在导入任何browser-use相关模块之前设置环境变量
# 设置browser-use配置目录到项目内部临时目录，避免权限问题
# 正确计算项目根目录：/Users/jinsm/testhub/testhub_platform
# 从 ai_agent.py 向上走2级目录即可到达项目根目录
# 路径结构：apps/ui_automation/ai_agent.py → 向上2级 → 项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
browseruse_config_dir = os.path.join(project_root, 'temp', 'browseruse_config')
# 确保目录存在
os.makedirs(os.path.join(project_root, 'temp'), exist_ok=True)
os.makedirs(browseruse_config_dir, exist_ok=True)
os.environ['BROWSER_USE_CONFIG_DIR'] = browseruse_config_dir
# 禁用browser-use遥测
os.environ['ANONYMIZED_TELEMETRY'] = 'false'

import logging
import asyncio
import concurrent.futures
from .ai_base import BaseBrowserAgent

logger = logging.getLogger('django')


def _run_async_sync(coro):
    """
    兼容性地运行异步协程。
    如果当前线程没有运行中的事件循环，直接使用 asyncio.run()；
    如果已有事件循环（如 ASGI/uvicorn），在新线程中运行以避免 RuntimeError。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 没有运行中的事件循环，安全使用 asyncio.run
        return asyncio.run(coro)

    # 已有事件循环，在新线程中运行
    def _run_in_thread():
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_in_thread)
        return future.result()


class BrowserAgent(BaseBrowserAgent):
    """
    Standard Browser Agent for Text Mode.
    Inherits all base functionality without applying dangerous visual patches.
    """
    def __init__(self, execution_mode='text', enable_gif=True, case_name=None):
        self.enable_gif = enable_gif
        self.case_name = case_name or "Adhoc Task"
        super().__init__(execution_mode='text')

# ============================================================================
# EXPORTED FUNCTIONS (FACTORY)
# ============================================================================

def get_agent_class(execution_mode='text'):
    # 始终返回文本模式实现
    return BrowserAgent

def run_ai_task_sync(task_description: str, planned_tasks=None, callback=None, should_stop=None, execution_mode='text'):
    agent = BrowserAgent(execution_mode='text')
    return _run_async_sync(agent.run_task(task_description, planned_tasks, callback, should_stop))

def analyze_task_sync(task_description: str, execution_mode='text'):
    agent = BrowserAgent(execution_mode='text')
    return _run_async_sync(agent.analyze_task(task_description))

def run_full_process_sync(task_description: str, analysis_callback=None, step_callback=None, should_stop=None, execution_mode='text', enable_gif=True, case_name=None):
    logger.info(f"DEBUG: Entering run_full_process_sync with execution_mode=text, enable_gif={enable_gif}")

    agent = BrowserAgent(execution_mode='text', enable_gif=enable_gif, case_name=case_name)

    logger.info(f"DEBUG: Agent created successfully ({type(agent).__name__}), starting async execution")
    return _run_async_sync(agent.run_full_process(task_description, analysis_callback, step_callback, should_stop))
