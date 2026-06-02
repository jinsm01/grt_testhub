"""Built-in rule check functions."""

from __future__ import annotations

import json
import re
from collections import defaultdict

from .models import CheckResult, Scenario, Step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_fixture_dir(scenario: Scenario) -> bool:
    """Check if a scenario is under a 前置/后置 (pre/post) directory."""
    path = scenario.folder_path
    if not path:
        return False
    parts = path.split("/")
    for p in parts:
        if p in ("前置", "后置"):
            return True
    return False


def _has_assertions(step: Step) -> bool:
    """Check if a step has assertions in any detectable format."""
    if step.assertions and len(step.assertions) > 0:
        return True
    if step.events:
        for ev in step.events:
            if isinstance(ev, dict):
                # Postman-style: listen == "test"
                if ev.get("listen") == "test":
                    return True
                # Direct assert/assertions key
                if ev.get("assert") or ev.get("assertions"):
                    return True
                # Script with assertion content
                script = ev.get("script") or {}
                if isinstance(script, dict):
                    script_text = json.dumps(script, ensure_ascii=False)
                elif isinstance(script, str):
                    script_text = script
                else:
                    script_text = ""
                if script_text and any(kw in script_text.lower() for kw in ("pm.test", "assert", "expect(", ".to.")):
                    return True
    # Recursively search the whole step dict for assertion indicators
    step_dict = {
        "name": step.name,
        "request_method": step.request_method,
        "request_url": step.request_url,
        "assertions": step.assertions,
        "events": step.events,
    }
    serialized = json.dumps(step_dict, ensure_ascii=False)
    if any(kw in serialized.lower() for kw in ("pm.test", "pm.expect", "assertion", "断言")):
        return True
    return False


# Keywords that indicate a step is a verification/query step by name
VERIFY_STEP_KEYWORDS = ("验证", "校验", "查询", "检查", "assert", "verify", "check")


def _is_verify_step_by_name(step_name: str, parent_step_name: str) -> bool:
    """Check if a step name indicates it's a verification step.
    
    Returns True if:
    - The step name contains verification keywords
    - The step name follows parent-step + keyword pattern (e.g. "知识图谱_创建验证" after "知识图谱_创建")
    """
    name = step_name.lower()
    parent = parent_step_name.lower() if parent_step_name else ""
    for kw in VERIFY_STEP_KEYWORDS:
        if kw in name:
            return True
        # Check parent-derived naming: parent_name + keyword
        if parent and (parent + kw) in name:
            return True
    return False


def _is_variable_value(val: str) -> bool:
    """Check if a string looks like a variable reference, e.g. {{var}} or {{$var}}."""
    if not val:
        return False
    return "{{" in val or "{%" in val


def _parse_body_fields(step: Step) -> dict[str, str]:
    """
    Parse raw JSON body and parameter list into a flat dict of field-name -> value.
    Returns dict where key is the field name (case-insensitive lookup) and value is the string value.
    """
    fields: dict[str, str] = {}

    # 1) Raw JSON body
    if step.request_body_raw:
        try:
            obj = json.loads(step.request_body_raw)
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str):
                        fields[k] = v
                    elif isinstance(v, (int, float, bool)):
                        fields[k] = str(v)
        except (json.JSONDecodeError, TypeError):
            pass

    # 2) Parameter list (form-data / urlencoded / etc.)
    if step.request_body_params:
        for param in step.request_body_params:
            if isinstance(param, dict):
                key = param.get("key") or param.get("name", "")
                val = param.get("value") or param.get("description", "")
                if key and isinstance(val, str):
                    fields[key] = val

    return fields


def _is_crud_method(method: str) -> bool:
    return method.upper() in ("POST", "PUT", "DELETE", "PATCH")


def _is_query_method(method: str) -> bool:
    return method.upper() in ("GET", "POST")


# ---------------------------------------------------------------------------
# Rule 1: 场景运行通过
# ---------------------------------------------------------------------------

def check_scenario_run_passed(scenarios: list[Scenario], params: dict) -> list[CheckResult]:
    results = []
    for s in scenarios:
        if _is_fixture_dir(s):
            continue
        status = s.last_run_status
        # passed -> pass; failed/not_run -> fail
        passed = status == "passed"
        msg = {
            "passed": "场景最近一次运行通过",
            "failed": "场景最近一次运行失败",
            "not_run": "场景从未运行",
            "running": "场景正在运行中",
        }.get(status, f"运行状态异常: {status}")
        results.append(CheckResult(
            rule_id="scenario-run-passed",
            scenario_id=s.id,
            scenario_name=s.name,
            severity="high",
            passed=passed,
            message=msg,
            details={"last_run_status": status},
        ))
    return results


# ---------------------------------------------------------------------------
# Rule 2: 单场景步骤数不超过10步（不包含引用其他场景或分组的测试步骤）
# ---------------------------------------------------------------------------

def check_scenario_step_count(scenarios: list[Scenario], params: dict) -> list[CheckResult]:
    """Check that single scenario has at most N actual API test steps.

    Counts only 'http' type steps that are NOT part of a referenced scenario.
    Excludes:
      - group steps (pre/post hooks markers and scenario reference markers)
      - wait steps (delay/pause steps)
      - http steps inside a referenced scenario scope (is_group_ref=True)
    """
    results = []
    max_steps = params.get("max_steps", 10)

    for s in scenarios:
        if _is_fixture_dir(s):
            continue
        # Count http steps that are NOT part of a referenced scenario
        actual_steps = [st for st in s.steps if st.type == "http" and not st.is_group_ref]
        # Count all referenced steps (both group markers and http steps inside ref scope)
        ref_steps = [st for st in s.steps if st.is_group_ref]
        
        count = len(actual_steps)
        total = len(s.steps)
        ref_count = len(ref_steps)
        
        if count > max_steps:
            results.append(CheckResult(
                rule_id="scenario-step-count",
                scenario_id=s.id,
                scenario_name=s.name,
                severity="mid",
                passed=False,
                message=f"场景有{count}个实际步骤(超过阈值{max_steps})，含{ref_count}个引用场景步骤 (total_steps={total}; actual_steps={count}; ref_steps={ref_count})",
                details={"total_steps": total, "actual_steps": count, "ref_steps": ref_count},
            ))
        else:
            results.append(CheckResult(
                rule_id="scenario-step-count",
                scenario_id=s.id,
                scenario_name=s.name,
                severity="mid",
                passed=True,
                message=f"场景有{count}个实际步骤，含{ref_count}个引用场景步骤，符合阈值要求",
                details={"total_steps": total, "actual_steps": count, "ref_steps": ref_count},
            ))
    return results


# ---------------------------------------------------------------------------
# Rule 3: 增删改后需要有查询步骤并使用断言校验
# ---------------------------------------------------------------------------

def check_crud_query_assert(scenarios: list[Scenario], params: dict) -> list[CheckResult]:
    results = []
    for s in scenarios:
        if _is_fixture_dir(s):
            continue
        for i, step in enumerate(s.steps):
            if step.is_group_ref or not step.request_method:
                continue
            if not _is_crud_method(step.request_method):
                continue

            # Check if there is a subsequent GET/POST step with assertions
            has_query_verify = False
            for j in range(i + 1, len(s.steps)):
                next_step = s.steps[j]
                if next_step.is_group_ref:
                    continue
                if _is_query_method(next_step.request_method or ""):
                    # Check if this step has assertions (via data or name heuristic)
                    if _has_assertions(next_step) or _is_verify_step_by_name(next_step.name, step.name):
                        has_query_verify = True
                        break
                    # GET without assertions → fail immediately
                    if next_step.request_method.upper() == "GET":
                        break
                    # POST without assertions but name suggests it's a verify step → pass
                    if _is_verify_step_by_name(next_step.name, step.name):
                        has_query_verify = True
                        break
                    # POST without assertions and not a verify step → keep looking for next query step

            # If the CRUD step itself is a POST query/search type (e.g., POST /page/search),
            # it's a self-contained query operation and doesn't need a follow-up verify step.
            # This handles cases like "知识图谱_创建验证" where the POST is the verification.
            if not has_query_verify and step.request_method.upper() == "POST":
                url = (step.request_url or "").lower()
                name = step.name.lower()
                # Check if the POST URL or step name suggests it's a query/search/verify operation
                query_url_patterns = ("/search", "/list", "/query", "/page", "/find", "/get")
                is_query_post = any(p in url for p in query_url_patterns)
                if is_query_post or _is_verify_step_by_name(step.name, ""):
                    has_query_verify = True

            if not has_query_verify:
                results.append(CheckResult(
                    rule_id="crud-query-assert",
                    scenario_id=s.id,
                    scenario_name=s.name,
                    severity="high",
                    passed=False,
                    message=f"增删改操作'{step.name}' [{step.request_method}] 后无查询步骤或查询步骤无断言",
                    details={"step_name": step.name, "method": step.request_method},
                ))

    return results


# ---------------------------------------------------------------------------
# Rule 4: 步骤请求body中，带有Id的参数不能写死
# ---------------------------------------------------------------------------

# Fields that look like IDs and should NOT be hardcoded
ID_FIELD_PATTERN = re.compile(
    r"(^id$|_id$|Id$|_id$|\.id$)", re.IGNORECASE
)

# ID-like field names that are exempt from hardcoded check
# (e.g. scene_id is a config/classifier field, not a resource ID)
_DEFAULT_ID_FIELD_EXEMPTIONS = {"scene_id", "template_id", "embd_id", "parser_id", "parent_id", "business_id", "category_id", "relation_template_id"}

# 运行时豁免列表（默认包含内置豁免项）
ID_FIELD_EXEMPTIONS = set(_DEFAULT_ID_FIELD_EXEMPTIONS)


def get_id_field_exemptions() -> set:
    """获取当前的 ID 字段豁免列表。"""
    return set(ID_FIELD_EXEMPTIONS)


def set_id_field_exemptions(extra: list[str] | None = None) -> set:
    """设置运行时额外豁免字段（保留内置默认项 + 合并额外项）。
    
    Args:
        extra: 额外的豁免字段列表，若为 None 则仅使用默认值
    Returns:
        合并后的完整豁免集合
    """
    global ID_FIELD_EXEMPTIONS
    ID_FIELD_EXEMPTIONS = set(_DEFAULT_ID_FIELD_EXEMPTIONS)
    if extra:
        for item in extra:
            if item and isinstance(item, str):
                ID_FIELD_EXEMPTIONS.add(item.strip().lower())
    return set(ID_FIELD_EXEMPTIONS)


def _looks_like_id_field(field_name: str) -> bool:
    """Check if a field name looks like an ID field (and is not exempt)."""
    name = field_name.strip()
    if name.lower() in ID_FIELD_EXEMPTIONS:
        return False
    # Match: id, xxxId, xxx_id, Id, etc.
    if name.lower() == "id":
        return True
    if name.lower().endswith("id"):
        return True
    if name.lower().endswith("_id"):
        return True
    return bool(ID_FIELD_PATTERN.search(name))


def _is_hardcoded_value(val: str) -> bool:
    """Check if a value is hardcoded (not a variable reference)."""
    if not val:
        return False
    # Variable patterns: {{...}}, {% ... %}
    if "{{" in val:
        return False
    # Looks like a number or UUID - likely hardcoded
    if val.replace("-", "").isalnum() and len(val) > 2:
        return True
    # Any non-empty string that isn't a variable
    return True


def check_no_hardcoded_id(scenarios: list[Scenario], params: dict) -> list[CheckResult]:
    results = []
    for s in scenarios:
        if _is_fixture_dir(s):
            continue
        for step in s.steps:
            if step.is_group_ref or not step.request_method:
                continue
            if not _is_crud_method(step.request_method):
                continue

            fields = _parse_body_fields(step)
            for field_name, field_val in fields.items():
                if _looks_like_id_field(field_name) and _is_hardcoded_value(field_val):
                    results.append(CheckResult(
                        rule_id="no-hardcoded-id",
                        scenario_id=s.id,
                        scenario_name=s.name,
                        severity="high",
                        passed=False,
                        message=f"步骤'{step.name}' [{step.request_method}] 中ID字段'{field_name}'值'{field_val[:50]}'疑似写死",
                        details={"step_name": step.name, "field": field_name, "value": field_val[:50]},
                    ))
                    break  # one violation per step is enough

    return results


# ---------------------------------------------------------------------------
# Rule 5: 后续步骤用到的参数，要从前置步骤中或变量获取
# ---------------------------------------------------------------------------

def check_param_from_prev_step(scenarios: list[Scenario], params: dict) -> list[CheckResult]:
    """
    Check that parameters used in later steps come from previous steps or variables.
    Strategy: scan body fields in non-GET requests. If a field value is a plain
    string (not a variable), check if it could be an ID or key that should be
    extracted from previous response.
    """
    results = []
    for s in scenarios:
        if _is_fixture_dir(s):
            continue

        # Collect variable names set by previous steps (from assertions/extractions)
        prev_vars = set()

        for i, step in enumerate(s.steps):
            if step.is_group_ref:
                continue
            if not step.request_method:
                continue

            # Check current step's body fields
            if _is_crud_method(step.request_method):
                fields = _parse_body_fields(step)
                for field_name, field_val in fields.items():
                    # If value is hardcoded AND looks like it could be an extractable param
                    if _is_hardcoded_value(field_val) and not _is_variable_value(field_val):
                        # Check if this value appears in any previous step's response/assertion
                        # or if there's an extraction that sets it
                        if field_val not in prev_vars and _looks_like_id_field(field_name):
                            results.append(CheckResult(
                                rule_id="param-from-prev-step",
                                scenario_id=s.id,
                                scenario_name=s.name,
                                severity="high",
                                passed=False,
                                message=f"步骤'{step.name}'中'{field_name}'值'{field_val[:30]}'未从前置步骤或变量获取",
                                details={"step_name": step.name, "field": field_name, "value": field_val[:30]},
                            ))
                            break  # one per step

            # Track variables that could be extracted from assertions
            if step.assertions:
                for a in step.assertions:
                    if isinstance(a, dict):
                        var_name = a.get("variableName") or a.get("varName") or a.get("name", "")
                        if var_name:
                            prev_vars.add(var_name)
                        # Also track from expression target
                        expr = a.get("expression") or a.get("target", "")
                        if expr:
                            # Try to extract variable name from expression
                            match = re.search(r"(\w+)$", expr)
                            if match:
                                prev_vars.add(match.group(1))

    return results


# ---------------------------------------------------------------------------
# Rule 6: 创建或编辑步骤中，名称参数需要带有"自动化"标识和动态值
# ---------------------------------------------------------------------------

# Name-like fields that should carry the auto tag
NAME_FIELDS = {"name", "title", "label", "description", "备注", "名称", "标题", "描述"}

# Token extraction step keywords – these steps are skipped in rule 6
TOKEN_STEP_KEYWORDS = {"token", "登录", "login", "获取token", "获取令牌", "auth", "认证"}


def _is_token_step(step: Step) -> bool:
    """Check if a step is a token extraction / login step that should be skipped."""
    name_lower = step.name.lower() if step.name else ""
    for kw in TOKEN_STEP_KEYWORDS:
        if kw.lower() in name_lower:
            return True
    # Also check URL path for token/login
    url = (step.request_url or "").lower()
    if url:
        for kw in ("token", "login", "auth", "oauth"):
            if kw in url:
                return True
    return False


def check_auto_name_tag(scenarios: list[Scenario], params: dict) -> list[CheckResult]:
    results = []
    required_tag = params.get("required_tag", "自动化")

    for s in scenarios:
        if _is_fixture_dir(s):
            continue
        for step in s.steps:
            if step.is_group_ref or not step.request_method:
                continue
            # Only check POST/PUT (create/edit)
            if step.request_method.upper() not in ("POST", "PUT"):
                continue
            # Skip token extraction / login steps
            if _is_token_step(step):
                continue

            fields = _parse_body_fields(step)
            has_name_violation = False
            for field_name, field_val in fields.items():
                if field_name.lower() in NAME_FIELDS or field_name in NAME_FIELDS:
                    # Check 1: contains required_tag
                    if required_tag not in field_val:
                        has_name_violation = True
                        results.append(CheckResult(
                            rule_id="auto-name-tag",
                            scenario_id=s.id,
                            scenario_name=s.name,
                            severity="high",
                            passed=False,
                            message=f"步骤'{step.name}'中'{field_name}'不含'{required_tag}'标识",
                            details={"step_name": step.name, "field": field_name, "value": field_val[:50]},
                        ))
                    # Check 2: has dynamic value (variable or timestamp-like)
                    if not _is_variable_value(field_val) and required_tag in field_val:
                        # The value contains the tag but is static - check if it has dynamic part
                        has_dynamic = False
                        # Look for {{...}} or timestamp patterns
                        if re.search(r"\{\{.*?\}\}", field_val):
                            has_dynamic = True
                        elif re.search(r"\d{8,}", field_val):  # timestamp-like
                            has_dynamic = True
                        if not has_dynamic:
                            results.append(CheckResult(
                                rule_id="auto-name-tag",
                                scenario_id=s.id,
                                scenario_name=s.name,
                                severity="high",
                                passed=False,
                                message=f"步骤'{step.name}'中'{field_name}'含'{required_tag}'但值非动态",
                                details={"step_name": step.name, "field": field_name, "value": field_val[:50]},
                            ))
                    break  # one violation per step for this rule

            # Also check scenario name
            if not has_name_violation:
                # Scenario name check
                pass  # done via step-level only per requirement

    return results


# ---------------------------------------------------------------------------
# Rule 7: 前置/后置目录下场景，不校验统计 (placeholder, handled by other rules skipping)
# ---------------------------------------------------------------------------

def check_fixture_dir_skip(scenarios: list[Scenario], params: dict) -> list[CheckResult]:
    """This rule simply reports how many fixture-dir scenarios were skipped."""
    fixture_count = sum(1 for s in scenarios if _is_fixture_dir(s))
    total = len(scenarios)
    checked = total - fixture_count
    return [CheckResult(
        rule_id="fixture-dir-skip",
        severity="skip",
        passed=True,
        message=f"前置/后置目录下{fixture_count}个场景已跳过校验，实际校验{checked}个场景",
        details={"fixture_skipped": fixture_count, "checked_count": checked, "total": total},
    )]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

RULE_REGISTRY = {
    "check_scenario_run_passed": check_scenario_run_passed,
    "check_scenario_step_count": check_scenario_step_count,
    "check_crud_query_assert": check_crud_query_assert,
    "check_no_hardcoded_id": check_no_hardcoded_id,
    "check_param_from_prev_step": check_param_from_prev_step,
    "check_auto_name_tag": check_auto_name_tag,
    "check_fixture_dir_skip": check_fixture_dir_skip,
}
