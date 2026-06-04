"""Data models for Apifox automation check."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Step:
    id: str
    name: str
    type: str
    request_method: str | None = None
    request_url: str | None = None
    request_base_url: str | None = None
    request_body_raw: str | None = None
    request_body_params: list[dict] | None = None
    request_headers: list[dict] | None = None
    assertions: list[dict] | None = None
    events: list[dict] | None = None
    delay_ms: int | None = None
    # Whether this step references another scenario/group
    is_group_ref: bool = False


@dataclass
class Scenario:
    id: int
    name: str
    folder_path: str
    folder_id: int | None = None
    priority: int | None = None
    options: dict | None = None
    steps: list[Step] | None = None  # 允许传入 None，post_init 中修正为 []
    has_pre_script: bool = False  # 场景自身是否配置了前置脚本
    has_post_script: bool = False  # 场景自身是否配置了后置脚本
    creator: str = ""
    created_at: str = ""
    last_run_status: str = ""  # passed / failed / not_run

    def __post_init__(self):
        # 防御性处理：确保 steps 永不为 None
        if self.steps is None:
            object.__setattr__(self, 'steps', [])


@dataclass
class CheckResult:
    rule_id: str
    severity: str
    passed: bool
    message: str
    scenario_id: int | None = None
    scenario_name: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class Rule:
    id: str
    name: str
    severity: str
    enabled: bool
    description: str
    check: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    rule: Rule
    results: list[CheckResult] = field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    compliance_rate: float = 0.0


@dataclass
class CheckConfig:
    project_id: int | None = None
    environment_id: int | None = None
    access_token: str | None = None
    thresholds: dict[str, Any] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)

    def get_threshold(self, key: str, default: Any = None) -> Any:
        return self.thresholds.get(key, default)


@dataclass
class ReportData:
    project_id: int
    environment_id: int
    total_scenarios: int
    total_rules_checked: int
    rule_results: list[RuleResult] = field(default_factory=list)
    timestamp: str = ""