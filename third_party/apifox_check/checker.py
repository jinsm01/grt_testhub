"""Rule engine: load config, validate, execute checks."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import CheckConfig, CheckResult, Rule, RuleResult, Scenario
from .rules import RULE_REGISTRY

DEFAULT_RULES_PATH = Path(__file__).parent / "default_rules.yaml"
USER_CONFIG_PATH = Path.home() / ".apifox-check" / "rules.yaml"


def load_yaml_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def merge_configs(base: dict, override: dict) -> dict:
    result = {**base}

    for key in ["project_id", "environment_id", "access_token", "thresholds"]:
        if key in override and override[key]:
            if key == "thresholds":
                result[key] = {**result.get(key, {}), **override[key]}
            else:
                result[key] = override[key]

    if "rules" in override:
        base_rules = {r["id"]: r for r in result.get("rules", [])}
        for ovr_rule in override["rules"]:
            if ovr_rule["id"] in base_rules:
                base_rules[ovr_rule["id"]] = {**base_rules[ovr_rule["id"]], **ovr_rule}
            else:
                base_rules[ovr_rule["id"]] = ovr_rule
        result["rules"] = list(base_rules.values())

    return result


def load_config(cli_config_path: str | None = None) -> CheckConfig:
    raw_base = load_yaml_config(DEFAULT_RULES_PATH)
    base_config = raw_base.get("apifox_check", raw_base)

    if USER_CONFIG_PATH.exists():
        raw_user = load_yaml_config(USER_CONFIG_PATH)
        user_config = raw_user.get("apifox_check", raw_user)
        base_config = merge_configs(base_config, user_config)

    if cli_config_path:
        raw_cli = load_yaml_config(Path(cli_config_path))
        cli_config = raw_cli.get("apifox_check", raw_cli)
        base_config = merge_configs(base_config, cli_config)

    rules = []
    for r in base_config.get("rules", []):
        rules.append(Rule(
            id=r["id"],
            name=r["name"],
            severity=r.get("severity", "mid"),
            enabled=r.get("enabled", True),
            description=r.get("description", ""),
            check=r.get("check", ""),
            params=r.get("params", {}),
        ))

    return CheckConfig(
        project_id=base_config.get("project_id"),
        environment_id=base_config.get("environment_id"),
        access_token=base_config.get("access_token"),
        thresholds=base_config.get("thresholds", {}),
        rules=rules,
    )


def init_user_config() -> Path:
    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    default_content = load_yaml_config(DEFAULT_RULES_PATH)
    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(default_content, f, allow_unicode=True, default_flow_style=False)
    return USER_CONFIG_PATH


def run_checks(
    scenarios: list[Scenario],
    config: CheckConfig,
    rule_ids: list[str] | None = None,
    exclude_ids: list[str] | None = None,
) -> list[RuleResult]:
    results = []

    for rule in config.rules:
        if not rule.enabled:
            continue
        if rule_ids and rule.id not in rule_ids:
            continue
        if exclude_ids and rule.id in exclude_ids:
            continue

        check_func = RULE_REGISTRY.get(rule.check)
        if not check_func:
            continue

        merged_params = {**rule.params}
        # Inject thresholds where applicable
        if "max_steps" not in merged_params and "max_steps_per_scenario" in config.thresholds:
            merged_params["max_steps"] = config.thresholds["max_steps_per_scenario"]
        if "max_wait_ms" not in merged_params and "max_wait_ms" in config.thresholds:
            merged_params["max_wait_ms"] = config.thresholds["max_wait_ms"]

        check_results = check_func(scenarios, merged_params)

        passed = sum(1 for r in check_results if r.passed)
        failed = sum(1 for r in check_results if not r.passed)
        total = passed + failed
        rate = passed / total * 100 if total > 0 else 100.0

        results.append(RuleResult(
            rule=rule,
            results=check_results,
            passed_count=passed,
            failed_count=failed,
            compliance_rate=round(rate, 1),
        ))

    return results