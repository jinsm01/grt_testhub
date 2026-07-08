# -*- coding: utf-8 -*-
"""
自动化场景执行引擎
支持：跨步骤引用、循环、条件分支
"""

from .context import ScenarioContext, StepData
from .executor import ScenarioExecutor

__all__ = ['ScenarioContext', 'StepData', 'ScenarioExecutor']
