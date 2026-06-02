"""Async Apifox API data fetcher."""

from __future__ import annotations

import asyncio
import json
import tomllib
from pathlib import Path

import aiohttp

from .models import Scenario, Step

API_BASE = "https://api.apifox.com/api/v1"
API_HEADERS_TEMPLATE = {
    "User-Agent": "apifox-cli/2.1.10",
    "X-apifox-Api-Version": "2025-09-01",
}
CONFIG_TOML_PATH = Path.home() / ".apifox" / "config.toml"
MAX_CONCURRENT = 10


def read_token_from_config() -> str | None:
    if CONFIG_TOML_PATH.exists():
        with open(CONFIG_TOML_PATH, "rb") as f:
            config = tomllib.load(f)
        return config.get("default", {}).get("access_token")
    return None


def parse_steps_from_detail(detail: dict) -> list[Step]:
    steps = []
    if "item" not in detail:
        return steps
    items = detail["item"]
    if not isinstance(items, list) or len(items) == 0:
        return steps

    inner = items[0].get("item", [])
    if not isinstance(inner, list):
        return steps

    # Phase 1: Identify __testCaseRef groups and their scope ranges.
    # When Apifox expands a referenced scenario, it wraps the referenced
    # steps between a start-group (__testCaseRef) and an end-group (scopeEndId).
    # All steps within this range belong to the referenced scenario.
    ref_scopes: list[tuple[str, int]] = []  # (scopeEndId, ref_related_id)
    for st in inner:
        stype = st.get("type", "")
        sid = st.get("id", "")
        if stype == "group" and "__testCaseRef" in str(sid):
            meta = (st.get("metaInfo") or {}) if isinstance(st.get("metaInfo"), dict) else {}
            extra = (meta.get("extraData") or {}) if isinstance(meta.get("extraData"), dict) else {}
            scope_end_id = meta.get("scopeEndId", "")
            ref_related_id = extra.get("relatedId")
            if scope_end_id and ref_related_id:
                ref_scopes.append((scope_end_id, ref_related_id))

    # Build a set of step IDs that are inside a referenced scope.
    # We track whether we're currently inside a scope, and collect step ids.
    ref_step_ids: set[str] = set()
    if ref_scopes:
        scope_end_set = {s[0] for s in ref_scopes}
        scope_stack: list[tuple[str, int]] = []  # [(scopeEndId, ref_related_id), ...]
        for st in inner:
            stype = st.get("type", "")
            sid = st.get("id", "")
            meta = (st.get("metaInfo") or {}) if isinstance(st.get("metaInfo"), dict) else {}
            extra = (meta.get("extraData") or {}) if isinstance(meta.get("extraData"), dict) else {}

            if stype == "group" and "__testCaseRef" in str(sid):
                # Enter a referenced scope
                scope_end_id = meta.get("scopeEndId", "")
                ref_related_id = extra.get("relatedId")
                if scope_end_id and ref_related_id:
                    scope_stack.append((scope_end_id, ref_related_id))
                continue

            if scope_stack and sid == scope_stack[-1][0]:
                # Exit the scope (scope-end marker)
                scope_stack.pop()
                continue

            if scope_stack:
                # Inside a referenced scope → mark as referenced step
                ref_step_ids.add(sid)

    # Phase 2: Build Step objects
    for st in inner:
        stype = st.get("type", "")
        sid = st.get("id", "")

        # Determine if this step belongs to a referenced scenario.
        # - group with __testCaseRef: reference marker itself
        # - any step whose id is inside a ref scope: referenced step
        is_ref = (
            (stype == "group" and "__testCaseRef" in str(sid))
            or (sid in ref_step_ids)
        )

        step = Step(
            id=sid,
            name=st.get("name", ""),
            type=stype,
            is_group_ref=is_ref,
        )

        if "request" in st:
            req = st["request"]
            step.request_method = req.get("method", "")
            step.request_base_url = req.get("baseUrl", "")

            url_obj = req.get("url", {})
            if isinstance(url_obj, dict):
                path_parts = url_obj.get("path", [])
                step.request_url = "/".join(str(p) for p in path_parts)
            elif isinstance(url_obj, str):
                step.request_url = url_obj

            body = req.get("body", {})
            if isinstance(body, dict):
                step.request_body_raw = body.get("raw", "")
                # Parse parameter list (key-value pairs in body)
                step.request_body_params = body.get("parameter", [])

            step.request_headers = req.get("header", [])

        step.assertions = st.get("assertions", [])
        step.events = st.get("event", [])

        if stype == "wait":
            step.delay_ms = st.get("delay", 0)

        steps.append(step)

    return steps


async def fetch_scenario_list(session: aiohttp.ClientSession, project_id: int) -> dict:
    url = f"{API_BASE}/projects/{project_id}/test-scenario/tree-list"
    async with session.get(url) as resp:
        data = await resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Failed to fetch scenario list: {data.get('errorMessage', 'unknown')}")
    return data["data"]


async def fetch_scenario_detail(
    session: aiohttp.ClientSession,
    scenario_id: int,
    environment_id: int | None,
) -> dict | None:
    options_param = ""
    if environment_id:
        options_param = f"?options=%7B%22environmentId%22:{environment_id}%7D"

    url = f"{API_BASE}/test-scenarios/{scenario_id}/run-config{options_param}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            data = await resp.json()
        if data.get("success"):
            return data["data"]
    except Exception:
        pass
    return None


async def fetch_user_name(
    session: aiohttp.ClientSession,
    user_id: int,
) -> str:
    """Fetch user name by user ID."""
    url = f"{API_BASE}/users/{user_id}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
        if data.get("success"):
            return data["data"].get("name", "") or data["data"].get("nickname", "")
    except Exception:
        pass
    return ""


async def fetch_all_test_reports(
    session: aiohttp.ClientSession,
    project_id: int,
) -> dict[int, dict]:
    """Fetch all test reports for a project and return latest report per scenario.

    Uses /projects/{projectId}/test-reports API which returns all reports
    sorted by createdAt DESC. We group by relatedId and keep the latest.
    
    Returns dict: scenario_id -> report dict (with stats, status, etc.)
    """
    url = f"{API_BASE}/projects/{project_id}/test-reports?page=1&pageSize=50"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            data = await resp.json()
    except Exception:
        return {}

    if not data.get("success"):
        return {}

    reports = data.get("data", [])
    if not reports:
        return {}

    # Reports are sorted by createdAt DESC (newest first).
    # Keep only the first (latest) report per relatedId.
    latest_per_scenario: dict[int, dict] = {}
    for r in reports:
        sid = r.get("relatedId")
        if sid and sid not in latest_per_scenario:
            latest_per_scenario[sid] = r

    return latest_per_scenario


def resolve_last_run_status(
    scenario_id: int,
    scenario_reports: dict[int, dict],
) -> str:
    """Determine last run status from test report data.

    Checks the scenario's latest test report stats to determine pass/fail:
      - steps.failed == 0 and steps.total > 0: "passed"
      - steps.failed > 0: "failed"
      - no report found: "not_run"
    """
    report = scenario_reports.get(scenario_id)
    if report is None:
        return "not_run"

    stats = report.get("stats", {})
    steps = stats.get("steps", {})
    total = steps.get("total", 0)
    failed = steps.get("failed", 0)

    if total == 0:
        return "not_run"
    if failed > 0:
        return "failed"
    return "passed"


async def fetch_all_scenarios(project_id: int, environment_id: int | None, access_token: str) -> list[Scenario]:
    headers = {**API_HEADERS_TEMPLATE, "Authorization": f"Bearer {access_token}"}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with aiohttp.ClientSession(headers=headers) as session:
        tree_data = await fetch_scenario_list(session, project_id)

        scenarios_meta = tree_data.get("testScenarios", [])
        folders = tree_data.get("testScenarioFolders", [])
        folder_map = {f["id"]: f["name"] for f in folders}

        # Build folder path map (parent chain)
        folder_parent = {f["id"]: f.get("parentId") for f in folders}

        def get_folder_path(fid: int | None) -> str:
            if fid is None or fid not in folder_map:
                return ""
            parts = []
            current = fid
            while current and current in folder_map:
                parts.append(folder_map[current])
                current = folder_parent.get(current)
            return "/".join(reversed(parts))

        # Step 1: Collect all unique creator/editor IDs from tree-list meta
        all_user_ids = set()
        scenario_meta_map = {}  # sid -> {creatorId, editorId, createdAt, ...}

        for s in scenarios_meta:
            sid = s["id"]
            creator_id = s.get("creatorId")
            editor_id = s.get("editorId")
            if creator_id:
                all_user_ids.add(creator_id)
            if editor_id:
                all_user_ids.add(editor_id)
            scenario_meta_map[sid] = s

        # Step 2: Fetch all test reports to get actual pass/fail status per scenario
        scenario_reports = await fetch_all_test_reports(session, project_id)
        import sys
        print(f"[DEBUG] Fetched test reports for {len(scenario_reports)} scenarios", file=sys.stderr)

        # Step 3: Batch fetch user names
        user_name_map: dict[int, str] = {}
        user_semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def fetch_user_name_cached(uid: int):
            async with user_semaphore:
                name = await fetch_user_name(session, uid)
            return uid, name

        if all_user_ids:
            user_tasks = [fetch_user_name_cached(uid) for uid in all_user_ids]
            user_results = await asyncio.gather(*user_tasks)
            for uid, name in user_results:
                if name:
                    user_name_map[uid] = name

        # Step 4: Fetch scenario details
        async def fetch_one(sid: int, meta: dict) -> Scenario | None:
            async with semaphore:
                detail = await fetch_scenario_detail(session, sid, environment_id)

            fid = meta.get("folderId")

            # Get creator name from user_name_map
            creator_id = scenario_meta_map.get(sid, {}).get("creatorId")
            creator = user_name_map.get(creator_id, "") if creator_id else ""
            created_at = scenario_meta_map.get(sid, {}).get("createdAt", "")

            # Determine last run status from actual test report data
            last_run_status = resolve_last_run_status(sid, scenario_reports)

            if detail is None:
                return Scenario(
                    id=sid,
                    name=meta.get("name", ""),
                    folder_path=get_folder_path(fid),
                    folder_id=fid,
                    priority=meta.get("priority"),
                    options=meta.get("options", {}),
                    steps=[],
                    creator=creator,
                    created_at=created_at,
                    last_run_status=last_run_status,
                )

            return Scenario(
                id=sid,
                name=meta.get("name", ""),
                folder_path=get_folder_path(fid),
                folder_id=fid,
                priority=meta.get("priority"),
                options=meta.get("options", {}),
                steps=parse_steps_from_detail(detail),
                creator=creator,
                created_at=created_at,
                last_run_status=last_run_status,
            )

        tasks = [fetch_one(s["id"], s) for s in scenarios_meta]
        results = await asyncio.gather(*tasks)

    return [r for r in results if r is not None]