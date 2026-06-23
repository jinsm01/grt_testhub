"""HTML report generator."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .models import CheckConfig, ReportData, RuleResult, Scenario


def _is_fixture_dir(scenario: Scenario) -> bool:
    """Check if a scenario is under a 前置/后置 (pre/post) directory or has 前置/后置 in its name."""
    # Check folder path
    path = scenario.folder_path
    if path:
        parts = path.split("/")
        for p in parts:
            if p in ("前置", "后置"):
                return True
    # Check scenario name
    name = scenario.name or ""
    if "前置" in name or "后置" in name:
        return True
    return False

CSS = """
* { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
body { max-width: 1600px; margin: 0 auto; padding: 20px; background: #ffffff; color: #333; }
h1 { text-align: center; color: #1a1a2e; font-size: 28px; border-bottom: 3px solid #e94560; padding-bottom: 12px; }
h2 { color: #1a1a2e; font-size: 20px; border-left: 4px solid #e94560; padding-left: 12px; margin-top: 32px; }
h3 { color: #16213e; font-size: 16px; margin-top: 24px; }
h4 { color: #16213e; font-size: 14px; margin-top: 16px; }
.summary-table { width: 100%; border-collapse: collapse; margin: 16px 0; }
.summary-table th { background: #1a1a2e; color: #fff; padding: 10px 14px; font-size: 14px; text-align: center; }
.summary-table td { padding: 10px 14px; font-size: 14px; text-align: center; border-bottom: 1px solid #eee; }
.summary-table tr:hover td { background: #f0f4ff; }
.severity-high { color: #e94560; font-weight: bold; }
.severity-mid { color: #f5a623; font-weight: bold; }
.severity-low { color: #7ed321; font-weight: bold; }
.severity-skip { color: #adb5bd; }
.status-violate { background: #ffe0e6; color: #e94560; font-weight: bold; padding: 2px 8px; border-radius: 4px; }
.status-partial { background: #fff3cd; color: #f5a623; font-weight: bold; padding: 2px 8px; border-radius: 4px; }
.status-ok { background: #d4edda; color: #28a745; font-weight: bold; padding: 2px 8px; border-radius: 4px; }
.status-skip { background: #e9ecef; color: #6c757d; padding: 2px 8px; border-radius: 4px; }
.data-table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }
.data-table th { background: #16213e; color: #fff; padding: 8px 10px; text-align: left; font-size: 12px; white-space: nowrap; }
.data-table td { padding: 8px 10px; border-bottom: 1px solid #eee; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.data-table tr:nth-child(even) td { background: #f8f9ff; }
.data-table tr:hover td { background: #e8f0fe; }
.run-passed { color: #28a745; font-weight: bold; }
.run-failed { color: #e94560; font-weight: bold; }
.run-notrun { color: #adb5bd; }
.run-running { color: #f5a623; font-weight: bold; }
.run-unknown { color: #6c757d; }
.creator-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.creator-tab { padding: 6px 16px; border-radius: 20px; background: #e9ecef; cursor: pointer; font-size: 13px; transition: background 0.2s; }
.creator-tab.active { background: #1a1a2e; color: #fff; }
.creator-tab .count { font-weight: bold; margin-left: 4px; }
.detail-row-hidden { display: none; }
/* Sortable table headers */
.sortable { cursor: pointer; user-select: none; white-space: nowrap; }
.sortable:hover { background: #1e3a5f; }
.sortable .sort-icon { margin-left: 4px; font-size: 10px; opacity: 0.5; }
.sortable.asc .sort-icon { opacity: 1; }
.sortable.desc .sort-icon { opacity: 1; }
/* Tooltip styles for hover full-text display */
.data-table td.tooltip-cell { position: static; cursor: default; overflow: visible; }
.tooltip-cell-inner { position: relative; display: inline-block; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle; }
.tooltip-text { visibility: hidden; opacity: 0; position: fixed; z-index: 99999; background: #1a1a2e; color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 12px; line-height: 1.7; max-width: 500px; white-space: normal; word-break: break-all; box-shadow: 0 6px 20px rgba(0,0,0,0.4); transition: opacity 0.15s ease, visibility 0.15s ease; pointer-events: none; }
.desc-cell { max-width: 260px; white-space: normal; font-size: 12px; color: #555; line-height: 1.5; }
"""

SEVERITY_MAP = {
    "high": ("🔴 高", "severity-high", "badge-high", "status-violate", "严重违规"),
    "mid": ("🟡 中", "severity-mid", "badge-mid", "status-partial", "部分违规"),
    "low": ("🟢 低", "severity-low", "badge-low", "status-partial", "轻微问题"),
    "skip": ("⏭️ 跳过", "severity-skip", "badge-skip", "status-skip", "跳过"),
}

RUN_STATUS_MAP = {
    "passed": ('<span class="run-passed">✅ 通过</span>',),
    "failed": ('<span class="run-failed">❌ 失败</span>',),
    "not_run": ('<span class="run-notrun">⏸️ 未运行</span>',),
    "running": ('<span class="run-running">🔄 运行中</span>',),
    "unknown": ('<span class="run-unknown">❓ 未知</span>',),
}


def make_table(headers: list[str], rows: list[list[str]], max_rows: int | None = None) -> str:
    if max_rows:
        rows = rows[:max_rows]
    parts = ['<table class="data-table"><thead><tr>']
    for h in headers:
        parts.append(f'<th>{h}</th>')
    parts.append('</tr></thead><tbody>')
    for row in rows:
        parts.append('<tr>')
        for val in row:
            parts.append(f'<td>{val}</td>')
        parts.append('</tr>')
    parts.append('</tbody></table>')
    return "\n".join(parts)


def _format_run_status(status: str) -> str:
    return RUN_STATUS_MAP.get(status, RUN_STATUS_MAP["unknown"])[0]


def _format_created_at(ts: str) -> str:
    """Format ISO datetime to readable short format."""
    if not ts:
        return "-"
    try:
        # Handle ISO format like "2025-11-06T12:36:41.000Z"
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00").replace("+00:00", ""))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts[:16] if len(ts) >= 16 else ts


def _build_scenario_map(scenarios: list[Scenario]) -> dict[int, Scenario]:
    return {s.id: s for s in scenarios}


def _extract_created_month(ts: str) -> str:
    """Extract YYYY-MM from an ISO datetime string."""
    if not ts:
        return "未知"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00").replace("+00:00", ""))
        return dt.strftime("%Y-%m")
    except Exception:
        return ts[:7] if len(ts) >= 7 else ts


def _generate_creator_summary(scenarios: list[Scenario], report: ReportData) -> str:
    """Generate a summary section grouped by creator with violation stats, filterable by month and run status."""
    parts = []
    parts.append('<h2>二、按创建人归纳总结</h2>')
    parts.append('<p style="color:#666;font-size:13px;margin:8px 0;">按创建人统计各人的场景违规情况，支持按月份和运行结果筛选</p>')

    # Build scenario map first for lookup
    scenarios_map = _build_scenario_map(scenarios)

    # Count unique scenarios per creator first (total)
    # Filter out scenarios in 前置/后置 directories
    creator_scenarios = defaultdict(set)  # creator -> set of scenario ids
    for s in scenarios:
        if _is_fixture_dir(s):
            continue
        creator = s.creator or "未知"
        creator_scenarios[creator].add(s.id)

    # Build per-creator violation stats
    creator_data = defaultdict(lambda: {
        "violations": defaultdict(int),  # rule_id -> count
        "violation_scenario_ids": set(),  # unique scenario ids that have violations
    })

    for rr in report.rule_results:
        for r in rr.results:
            if r.passed or r.scenario_id is None:
                continue
            sc = scenarios_map.get(r.scenario_id)
            if sc:
                creator = sc.creator or "未知"
                creator_data[creator]["violations"][rr.rule.id] += 1
                creator_data[creator]["violation_scenario_ids"].add(r.scenario_id)

    # Compute totals per creator
    for creator in list(creator_data.keys()):
        data = creator_data[creator]
        total_count = len(creator_scenarios.get(creator, set()))
        viol_count = len(data["violation_scenario_ids"])
        data["total_scenarios"] = total_count
        data["compliant_scenarios"] = max(total_count - viol_count, 0)
        data["total_violations"] = viol_count

    # Also include creators with zero violations
    all_creators = set(creator_scenarios.keys()) | set(creator_data.keys())
    for c in all_creators:
        if c not in creator_data:
            total_c = len(creator_scenarios.get(c, set()))
            creator_data[c] = {
                "violations": defaultdict(int),
                "violation_scenario_ids": set(),
                "total_scenarios": total_c,
                "compliant_scenarios": total_c,
                "total_violations": 0,
            }

    if not creator_data:
        parts.append('<p style="color:#999">无违规数据可按创建人统计</p>')
        return "\n".join(parts)

    # Sort by total violations descending
    sorted_creators = sorted(creator_data.items(), key=lambda x: x[1]["total_violations"], reverse=True)

    # Collect all months and run statuses for filter options (global)
    # Filter out scenarios in 前置/后置 directories
    all_months = set()
    all_statuses = set()
    for s in scenarios:
        if _is_fixture_dir(s):
            continue
        all_months.add(_extract_created_month(s.created_at))
        all_statuses.add(s.last_run_status or "unknown")
    sorted_months = sorted([m for m in all_months if m != "未知"], reverse=True)
    if "未知" in all_months:
        sorted_months.append("未知")

    # Creator tabs navigation
    parts.append('<div class="creator-tabs">')
    for idx, (creator, data) in enumerate(sorted_creators):
        active_class = " active" if idx == 0 else ""
        parts.append(f'<span class="creator-tab{active_class}" id="ctab-{idx}" onclick="switchCreator({idx})">')
        parts.append(f'{creator}<span class="count">({data["total_scenarios"]}总/{data["compliant_scenarios"]}合/{data["total_violations"]}违)</span></span>')
    parts.append('</div>')

    # Per-creator detail sections
    for idx, (creator, data) in enumerate(sorted_creators):
        display_style = "" if idx == 0 else "display:none"
        total = data["total_scenarios"]
        compliant = data["compliant_scenarios"]
        viol = data["total_violations"]
        parts.append(f'<div id="creator-{idx}" style="{display_style};margin-bottom:24px;">')
        parts.append(f'<h3>👤 {creator}</h3>')
        # Filter controls
        parts.append('<div style="margin:12px 0;">')
        parts.append('<label style="font-size:13px;color:#555;">📅 月份：</label>')
        parts.append(f'<select id="filter-month-{idx}" onchange="applyFilters({idx})" style="padding:4px 8px;border:1px solid #ccc;border-radius:4px;font-size:13px;">')
        parts.append('<option value="all">全部月份</option>')
        for m in sorted_months:
            parts.append(f'<option value="{m}">{m}</option>')
        parts.append('</select>')
        parts.append('<label style="margin-left:16px;font-size:13px;color:#555;">🏁 结果：</label>')
        parts.append(f'<select id="filter-status-{idx}" onchange="applyFilters({idx})" style="padding:4px 8px;border:1px solid #ccc;border-radius:4px;font-size:13px;">')
        parts.append('<option value="all">全部结果</option>')
        status_options = [("passed", "✅ 通过"), ("failed", "❌ 失败"), ("not_run", "⏸️ 未运行"), ("unknown", "❓ 未知")]
        for sv, sl in status_options:
            if sv in all_statuses:
                parts.append(f'<option value="{sv}">{sl}</option>')
        parts.append('</select>')
        parts.append('</div>')

        # Embed all scenario metadata for this creator as JSON (for dynamic stats filtering)
        # Filter out scenarios in 前置/后置 directories
        creator_scenario_list = [s for s in scenarios if (s.creator or "未知") == creator and not _is_fixture_dir(s)]
        scenario_meta = []
        # Build per-scenario rule violation mapping:
        # scenario_rule_violations: scenario_id -> set of violated rule_ids (for is_violation check)
        # scenario_rule_counts: scenario_id -> {rule_id: count} (for correct violation count stats)
        # scenario_rule_months: scenario_id -> month string (for filtering counts in updateRuleTable)
        scenario_rule_violations = {}
        scenario_rule_counts = {}
        scenario_rule_months = {}
        for s in creator_scenario_list:
            scenario_meta.append({
                "id": s.id,
                "name": s.name or "",
                "folder": s.folder_path or "",
                "month": _extract_created_month(s.created_at),
                "run_status": s.last_run_status or "unknown",
                "created_at": _format_created_at(s.created_at),
                "is_violation": s.id in data["violation_scenario_ids"],
            })
            # Collect unique violated rule IDs and their counts for this scenario
            violated_rules = set()
            rule_counts = {}
            for rr in report.rule_results:
                for r in rr.results:
                    if r.passed or r.scenario_id is None:
                        continue
                    if r.scenario_id == s.id:
                        violated_rules.add(rr.rule.id)
                        rule_counts[rr.rule.id] = rule_counts.get(rr.rule.id, 0) + 1
            if violated_rules:
                scenario_rule_violations[s.id] = list(violated_rules)
            if rule_counts:
                scenario_rule_counts[s.id] = rule_counts
            # Also embed per-scenario per-rule month info so updateRuleTable can filter correctly
            scenario_rule_months[s.id] = _extract_created_month(s.created_at)
        import json as _json
        parts.append(f'<script id="scenario-meta-{idx}" type="application/json">{_json.dumps(scenario_meta, ensure_ascii=False)}</script>')
        # Embed rules info and per-scenario rule violations for dynamic table rebuild
        rules_info = []
        for rr in report.rule_results:
            rules_info.append({
                "id": rr.rule.id,
                "name": rr.rule.name,
                "severity": rr.rule.severity,
            })
        parts.append(f'<script id="rules-info-{idx}" type="application/json">{_json.dumps(rules_info, ensure_ascii=False)}</script>')
        parts.append(f'<script id="scenario-rule-violations-{idx}" type="application/json">{_json.dumps(scenario_rule_violations, ensure_ascii=False)}</script>')
        parts.append(f'<script id="scenario-rule-counts-{idx}" type="application/json">{_json.dumps(scenario_rule_counts, ensure_ascii=False)}</script>')
        parts.append(f'<script id="scenario-rule-months-{idx}" type="application/json">{_json.dumps(scenario_rule_months, ensure_ascii=False)}</script>')

        # Stats cards: 总场景数 / 合规场景数 / 违规场景数
        parts.append(f'<p style="margin:12px 0;font-size:14px;">')
        parts.append(f'<b>📊 场景统计：</b>')
        parts.append(f'<span style="margin-left:8px;">总场景数: <b id="stat-total-{idx}">{total}</b></span>')
        parts.append(f'<span style="margin-left:16px;color:#28a745;">合规场景: <b id="stat-compliant-{idx}">{compliant}</b></span>')
        parts.append(f'<span style="margin-left:16px;color:#e94560;">违规场景: <b id="stat-violation-{idx}">{viol}</b></span>')
        if total > 0:
            pct_compliant = round(compliant / total * 100, 1)
            pct_color = "#e94560" if pct_compliant < 50 else ("#f5a623" if pct_compliant < 80 else "#28a745")
            parts.append(f'<span style="margin-left:16px;font-size:13px;" id="stat-rate-text-{idx}">(合规率 <b id="stat-rate-{idx}" style="color:{pct_color}">{pct_compliant}%</b>)</span>')
        parts.append('</p>')

        # Violation breakdown per rule (tbody will be rebuilt by JS on filter)
        parts.append('<div class="creator-stats">')
        parts.append(f'<table class="summary-table" id="rule-table-{idx}">')
        parts.append('<thead><tr><th>规则名称</th><th>违规数</th><th>严重程度</th></tr></thead>')
        parts.append(f'<tbody id="rule-table-body-{idx}">')
        # Initial render: only show rules with violations for the creator's first month (or all if no data)
        # We rebuild via JS on page load, so this static HTML is just a fallback.
        for rr in report.rule_results:
            v_count = data["violations"].get(rr.rule.id, 0)
            if v_count > 0:
                sev = SEVERITY_MAP.get(rr.rule.severity, SEVERITY_MAP["mid"])
                parts.append(f'<tr><td>{rr.rule.name}</td><td><b>{v_count}</b></td><td class="{sev[1]}">{sev[0]}</td></tr>')
        parts.append('</tbody></table>')

        # ---- Title + count ----
        parts.append('<h4 style="margin-top:20px;margin-bottom:8px;">违规场景明细</h4>')
        parts.append(f'<p style="text-align:right;font-size:13px;color:#666;margin:4px 0;"><span id="filter-count-{idx}"></span></p>')

        # Detailed violation list for this creator
        headers_detail = ["场景ID", "场景名称", "归属目录", "规则", "问题描述", "创建时间", "运行结果"]
        parts.append(f'<table class="data-table" id="detail-table-{idx}"><thead><tr>')
        for col_idx, h in enumerate(headers_detail):
            parts.append(f'<th class="sortable" onclick="sortDetailTable({idx}, {col_idx})">{h}<span class="sort-icon">⇅</span></th>')
        parts.append('</tr></thead><tbody>')

        row_index = 0
        for rr in report.rule_results:
            for r in rr.results:
                if r.passed or r.scenario_id is None:
                    continue
                sc = scenarios_map.get(r.scenario_id)
                if not sc or (sc.creator or "未知") != creator:
                    continue
                detail_str = ""
                if r.details:
                    for k, v in r.details.items():
                        if isinstance(v, (str, int, float, bool)):
                            detail_str += f"{k}={v}; "
                        elif isinstance(v, list):
                            detail_str += f"{k}=[{', '.join(str(x) for x in v[:3])}]; "
                detail_str = detail_str.rstrip("; ")[:200]
                month_val = _extract_created_month(sc.created_at)
                # 使用规则检查状态作为显示结果，而非 Apifox 执行结果
                rule_status = "failed" if not r.passed else "passed"
                parts.append(f'<tr class="detail-row" data-month="{month_val}" data-runstatus="{rule_status}">')
                parts.append(f'<td>{r.scenario_id}</td>')
                parts.append(f'<td>{r.scenario_name or "-"}</td>')
                parts.append(f'<td>{sc.folder_path or "-"}</td>')
                parts.append(f'<td>{rr.rule.name}</td>')
                full_msg = r.message + (" (" + detail_str + ")" if detail_str else "")
                parts.append(f'<td class="tooltip-cell"><span class="tooltip-cell-inner">{full_msg[:60]}{"..." if len(full_msg) > 60 else ""}</span><div class="tooltip-text" data-tooltip="{full_msg}">{full_msg}</div></td>')
                parts.append(f'<td>{_format_created_at(sc.created_at)}</td>')
                # 显示规则合规状态：违规=失败，通过=通过
                status_class = 'run-failed' if not r.passed else 'run-passed'
                status_text = '失败' if not r.passed else '通过'
                parts.append(f'<td class="{status_class}"><b>{status_text}</b></td>')
                parts.append('</tr>')
                row_index += 1

        parts.append('</tbody></table>')

    # JavaScript for tab switching and filtering
    parts.append("""
<script>
// Track current filter values for synchronization across tabs
var _currentMonthFilter = 'all';
var _currentStatusFilter = 'all';

function switchCreator(idx) {
    var sections = document.querySelectorAll('[id^="creator-"]');
    var tabs = document.querySelectorAll('[id^="ctab-"]');
    // Sync the target tab's dropdowns to the global filter state
    var targetMonth = document.getElementById('filter-month-' + idx);
    var targetStatus = document.getElementById('filter-status-' + idx);
    if (targetMonth && _currentMonthFilter !== 'all') targetMonth.value = _currentMonthFilter;
    if (targetStatus && _currentStatusFilter !== 'all') targetStatus.value = _currentStatusFilter;
    for (var i = 0; i < sections.length; i++) {
        if (sections[i].id === 'creator-' + idx) {
            sections[i].style.display = '';
            applyFilters(i);
        } else {
            sections[i].style.display = 'none';
        }
    }
    for (var i = 0; i < tabs.length; i++) {
        tabs[i].className = tabs[i].className.replace(' active', '');
    }
    document.getElementById('ctab-' + idx).className += ' active';
}

function applyFilters(idx) {
    var monthEl = document.getElementById('filter-month-' + idx);
    var statusEl = document.getElementById('filter-status-' + idx);
    var table = document.getElementById('detail-table-' + idx);
    var countEl = document.getElementById('filter-count-' + idx);
    if (!table) return;
    var rows = table.querySelectorAll('tr.detail-row');
    var monthVal = monthEl ? monthEl.value : 'all';
    var statusVal = statusEl ? statusEl.value : 'all';
    // Save current filter values for cross-tab synchronization
    _currentMonthFilter = monthVal;
    _currentStatusFilter = statusVal;
    var visible = 0;
    for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        var m = r.getAttribute('data-month') || '';
        var s = r.getAttribute('data-runstatus') || '';
        var show = true;
        if (monthVal !== 'all' && m !== monthVal) show = false;
        if (statusVal !== 'all' && s !== statusVal) show = false;
        if (show) {
            r.classList.remove('detail-row-hidden');
            visible++;
        } else {
            r.classList.add('detail-row-hidden');
        }
    }
    if (countEl) {
        countEl.textContent = '显示 ' + visible + ' / ' + rows.length + ' 条';
    }
    // Update stats cards from embedded scenario metadata
    updateStats(idx, monthVal, statusVal);
}

function updateStats(idx, monthVal, statusVal) {
    var metaEl = document.getElementById('scenario-meta-' + idx);
    if (!metaEl) return;
    var allScenarios;
    try { allScenarios = JSON.parse(metaEl.textContent); } catch(e) { return; }
    var filteredTotal = 0, filteredViol = 0;
    for (var i = 0; i < allScenarios.length; i++) {
        var sc = allScenarios[i];
        if (monthVal !== 'all' && sc.month !== monthVal) continue;
        if (statusVal !== 'all' && sc.run_status !== statusVal) continue;
        var folder = sc.folder || '';
        var name = sc.name || '';
        if (folder.indexOf('前置') !== -1 || folder.indexOf('后置') !== -1) continue;
        if (name.indexOf('前置') !== -1 || name.indexOf('后置') !== -1) continue;
        filteredTotal++;
        if (sc.is_violation) filteredViol++;
    }
    var filteredCompliant = filteredTotal - filteredViol;
    var totalEl = document.getElementById('stat-total-' + idx);
    var compliantEl = document.getElementById('stat-compliant-' + idx);
    var violEl = document.getElementById('stat-violation-' + idx);
    var rateEl = document.getElementById('stat-rate-' + idx);
    var rateTextEl = document.getElementById('stat-rate-text-' + idx);
    if (totalEl) totalEl.textContent = filteredTotal;
    if (compliantEl) compliantEl.textContent = filteredCompliant;
    if (violEl) violEl.textContent = filteredViol;
    if (rateEl && rateTextEl) {
        if (filteredTotal > 0) {
            var pct = (filteredCompliant / filteredTotal * 100).toFixed(1);
            rateEl.textContent = pct + '%';
            rateTextEl.style.display = '';
            if (pct < 50) { rateEl.style.color = '#e94560'; }
            else if (pct < 80) { rateEl.style.color = '#f5a623'; }
            else { rateEl.style.color = '#28a745'; }
        } else {
            rateTextEl.style.display = 'none';
        }
    }
    // Update rule violation table dynamically based on filtered scenarios
    updateRuleTable(idx, monthVal, statusVal);
}

function updateRuleTable(idx, monthVal, statusVal) {
    var rulesEl = document.getElementById('rules-info-' + idx);
    var countsEl = document.getElementById('scenario-rule-counts-' + idx);
    var monthsEl = document.getElementById('scenario-rule-months-' + idx);
    var metaEl = document.getElementById('scenario-meta-' + idx);
    var tbodyEl = document.getElementById('rule-table-body-' + idx);
    if (!rulesEl || !countsEl || !metaEl || !tbodyEl) return;
    var rulesInfo, scenarioRuleCounts, scenarioRuleMonths, allScenarios;
    try {
        rulesInfo = JSON.parse(rulesEl.textContent);
        scenarioRuleCounts = JSON.parse(countsEl.textContent);
        scenarioRuleMonths = monthsEl ? JSON.parse(monthsEl.textContent) : {};
        allScenarios = JSON.parse(metaEl.textContent);
    } catch(e) { return; }
    // Fallback: build scenarioRuleMonths from scenario-meta if not embedded
    if (Object.keys(scenarioRuleMonths).length === 0) {
        for (var i = 0; i < allScenarios.length; i++) {
            var sc = allScenarios[i];
            scenarioRuleMonths[String(sc.id)] = sc.month;
        }
    }
    // Build set of scenario IDs that pass the current filters (keys as strings for JSON object lookup)
    var filteredScenarioIds = {};
    for (var i = 0; i < allScenarios.length; i++) {
        var sc = allScenarios[i];
        if (monthVal !== 'all' && sc.month !== monthVal) continue;
        if (statusVal !== 'all' && sc.run_status !== statusVal) continue;
        var folder = sc.folder || '';
        var name = sc.name || '';
        if (folder.indexOf('前置') !== -1 || folder.indexOf('后置') !== -1) continue;
        if (name.indexOf('前置') !== -1 || name.indexOf('后置') !== -1) continue;
        filteredScenarioIds[String(sc.id)] = true;
    }
    // Sum violation counts per rule from scenario-rule-counts, but also check scenario-rule-months
    // because a scenario may have violations in multiple rules but only one month entry.
    var ruleCounts = {};
    for (var sid in scenarioRuleCounts) {
        if (!filteredScenarioIds[sid]) continue;
        // Double-check month filter using scenario-rule-months (defensive filter)
        if (monthVal !== 'all' && scenarioRuleMonths[sid] && scenarioRuleMonths[sid] !== monthVal) continue;
        var countsMap = scenarioRuleCounts[sid];
        for (var rid in countsMap) {
            ruleCounts[rid] = (ruleCounts[rid] || 0) + countsMap[rid];
        }
    }
    // Rebuild tbody HTML
    var severityMap = {
        'high': ['高', 'severity-high'],
        'mid': ['中', 'severity-mid'],
        'low': ['低', 'severity-low'],
        'skip': ['跳过', 'severity-skip']
    };
    var html = '';
    for (var i = 0; i < rulesInfo.length; i++) {
        var rule = rulesInfo[i];
        var count = ruleCounts[rule.id] || 0;
        if (count > 0) {
            var sev = severityMap[rule.severity] || severityMap['mid'];
            html += '<tr><td>' + rule.name + '</td><td><b>' + count + '</b></td><td class="' + sev[1] + '">' + sev[0] + '</td></tr>';
        }
    }
    if (!html) {
        html = '<tr><td colspan="3" style="text-align:center;color:#999;padding:20px;">该筛选条件下无违规数据</td></tr>';
    }
    tbodyEl.innerHTML = html;
}

// Apply filter on page load for the first (visible) creator
document.addEventListener('DOMContentLoaded', function() {
    for (var i = 0; ; i++) {
        var section = document.getElementById('creator-' + i);
        if (!section) break;
        if (section.style.display !== 'none') {
            applyFilters(i);
            break;
        }
    }
    // Also trigger filter rebuild for all hidden creator sections so their rule tables are correct if switched to
    for (var i = 0; ; i++) {
        var section = document.getElementById('creator-' + i);
        if (!section) break;
        if (section.style.display === 'none') {
            applyFilters(i);
        }
    }

    // Tooltip hover - fully JS-controlled positioning and visibility
    var activeTooltip = null;
    document.querySelectorAll('.tooltip-cell').forEach(function(cell) {
        cell.addEventListener('mouseenter', function() {
            var tooltip = cell.querySelector('.tooltip-text');
            if (!tooltip) return;
            // Hide any previously shown tooltip
            if (activeTooltip && activeTooltip !== tooltip) {
                activeTooltip.style.visibility = 'hidden';
                activeTooltip.style.opacity = '0';
            }
            var rect = cell.getBoundingClientRect();
            // Set position first so we can measure
            tooltip.style.visibility = 'visible';
            tooltip.style.left = '-9999px';
            tooltip.style.top = '0px';
            var tipW = tooltip.offsetWidth;
            var tipH = tooltip.offsetHeight;
            // Center above the cell
            var left = rect.left + (rect.width / 2) - (tipW / 2);
            var top = rect.top + window.scrollY - tipH - 10;
            // Keep within viewport
            left = Math.max(8, Math.min(left, window.innerWidth - tipW - 8));
            top = Math.max(window.scrollY + 8, top);
            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
            tooltip.style.opacity = '1';
            activeTooltip = tooltip;
        });
        cell.addEventListener('mouseleave', function() {
            var tooltip = cell.querySelector('.tooltip-text');
            if (tooltip) {
                tooltip.style.visibility = 'hidden';
                tooltip.style.opacity = '0';
                if (activeTooltip === tooltip) activeTooltip = null;
            }
        });
    });
});

// Sort detail table by column
function sortDetailTable(tableIdx, colIdx) {
    var table = document.getElementById('detail-table-' + tableIdx);
    if (!table) return;
    var thead = table.querySelector('thead tr');
    var ths = thead.querySelectorAll('th.sortable');
    // Determine sort direction
    var th = ths[colIdx];
    var isAsc = !th.classList.contains('asc');
    // Update header classes
    ths.forEach(function(t) { t.classList.remove('asc', 'desc'); });
    th.classList.add(isAsc ? 'asc' : 'desc');
    // Collect rows
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr.detail-row'));
    // Parse value from cell for sorting
    function getCellValue(row, col) {
        var cell = row.cells[col];
        if (!cell) return '';
        var text = cell.textContent.trim();
        // Try date parsing for created_at column (index 5)
        if (col === 5) {
            var d = new Date(text.replace(/-/g, '/'));
            return isNaN(d.getTime()) ? text : d.getTime();
        }
        // Try numeric parsing for scenario ID
        if (col === 0) {
            var n = parseInt(text, 10);
            return isNaN(n) ? text : n;
        }
        return text;
    }
    rows.sort(function(a, b) {
        var va = getCellValue(a, colIdx);
        var vb = getCellValue(b, colIdx);
        if (typeof va === 'number' && typeof vb === 'number') {
            return isAsc ? va - vb : vb - va;
        }
        return isAsc ? String(va).localeCompare(String(vb, 'zh-CN')) : String(vb).localeCompare(String(va), 'zh-CN');
    });
    // Re-append sorted rows
    rows.forEach(function(r) { tbody.appendChild(r); });
}
</script>""")

    return "\n".join(parts)


# Global map for cross-reference in _generate_creator_summary
scenarios_map: dict[int, Scenario] = {}


def generate_html_report(report: ReportData, config: CheckConfig, scenarios: list[Scenario] | None = None) -> str:
    global scenarios_map
    if scenarios:
        scenarios_map = _build_scenario_map(scenarios)
    else:
        scenarios_map = {}

    parts = []
    parts.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">')
    parts.append(f'<title>Apifox自动化检查报告 - 项目{report.project_id}</title>')
    parts.append(f'<style>{CSS}</style></head><body>')
    parts.append(f'<h1>Apifox接口自动化编写规范检查报告</h1>')
    parts.append(f'<p style="margin:12px 0;font-size:14px;"><b>项目ID：</b>{report.project_id} | <b>环境ID：</b>{report.environment_id} | <b>场景总数：</b>{report.total_scenarios} | <b>检查时间：</b>{report.timestamp}</p>')

    # Summary table
    parts.append('<h2>一、检查结果总览</h2>')
    parts.append('<table class="summary-table"><thead><tr>')
    parts.append('<th>序号</th><th>规则ID</th><th>规则名称</th><th>规则说明</th><th>合规率</th><th>严重程度</th><th>状态</th>')
    parts.append('</tr></thead><tbody>')

    for i, rr in enumerate(report.rule_results):
        sev = SEVERITY_MAP.get(rr.rule.severity, SEVERITY_MAP["mid"])
        sev_text, sev_class, badge_class, status_class, status_text = sev
        rate_str = f"{rr.compliance_rate}%"
        if rr.rule.severity == "skip":
            rate_str = "-"
            status_text = "跳过"
        elif rr.compliance_rate >= 90:
            status_text = "基本合规 ✅"
            status_class = "status-ok"
        elif rr.compliance_rate >= 70:
            status_text = "部分违规"
        elif rr.compliance_rate < 30:
            status_text = "严重违规"
            status_class = "status-violate"

        desc = rr.rule.description or ""
        parts.append(f'<tr><td>{i+1}</td><td>{rr.rule.id}</td><td>{rr.rule.name}</td>')
        parts.append(f'<td class="desc-cell">{desc}</td>')
        parts.append(f'<td><b>{rate_str}</b></td><td class="{sev_class}">{sev_text}</td>')
        parts.append(f'<td><span class="{status_class}">{status_text}</span></td></tr>')

    parts.append('</tbody></table>')

    # Creator summary section
    if scenarios and scenarios_map:
        parts.append(_generate_creator_summary(scenarios, report))

    # Footer
    parts.append(f'<p style="text-align:center; color:#999; margin-top:40px; font-size:12px;">')
    parts.append(f'报告生成时间：{report.timestamp} | 工具：apifox-check v1.0.0 | 场景总数：{report.total_scenarios}')
    parts.append('</p></body></html>')

    return "\n".join(parts)


def write_report(html: str, output_path: str) -> str:
    from pathlib import Path
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    return str(p.resolve())


def generate_json_report(report: ReportData, scenarios: list[Scenario] | None = None) -> dict:
    """Generate JSON format report data for Vue frontend rendering."""
    global scenarios_map
    if scenarios:
        scenarios_map = _build_scenario_map(scenarios)
    else:
        scenarios_map.clear()

    # Build rule results
    rule_results = []
    for rr in report.rule_results:
        rule_results.append({
            "rule": {
                "id": rr.rule.id,
                "name": rr.rule.name,
                "severity": rr.rule.severity,
                "description": rr.rule.description,
            },
            "passed_count": rr.passed_count,
            "failed_count": rr.failed_count,
            "compliance_rate": rr.compliance_rate,
        })

    # Build creator summary
    creators = []
    if scenarios and scenarios_map:
        creator_data = _build_creator_data(scenarios, report)
        for idx, (creator, data) in enumerate(creator_data.items()):
            # Build scenarios for this creator
            creator_scenarios = []
            for s in data["scenarios"]:
                # Find violations for this scenario
                violations = []
                for rr in report.rule_results:
                    for r in rr.results:
                        if not r.passed and r.scenario_id == s.id:
                            violations.append({
                                "rule_id": rr.rule.id,
                                "ruleName": rr.rule.name,
                                "message": r.message,
                                "details": r.details,
                            })

                creator_scenarios.append({
                    "id": s.id,
                    "name": s.name or "-",
                    "folder": s.folder_path or "-",
                    "month": _extract_created_month(s.created_at),
                    "run_status": s.last_run_status or "unknown",
                    "created_at": _format_created_at(s.created_at),
                    "is_violation": s.id in data["violation_scenario_ids"],
                    "violations": violations,
                    "ruleName": violations[0]["ruleName"] if violations else "",
                    "message": violations[0]["message"] if violations else "",
                })

            # Build rule violations summary
            rule_violations = []
            for rr in report.rule_results:
                v_count = data["violations"].get(rr.rule.id, 0)
                if v_count > 0:
                    rule_violations.append({
                        "ruleName": rr.rule.name,
                        "count": v_count,
                        "severity": rr.rule.severity,
                    })

            creators.append({
                "index": idx,
                "name": creator,
                "total": data["total_scenarios"],
                "compliant": data["compliant_scenarios"],
                "violations": data["total_violations"],
                "scenarios": creator_scenarios,
                "ruleViolations": rule_violations,
            })

    return {
        "project_id": report.project_id,
        "environment_id": report.environment_id,
        "total_scenarios": report.total_scenarios,
        "timestamp": report.timestamp,
        "rule_results": rule_results,
        "creators": creators,
    }


def _build_creator_data(scenarios: list[Scenario], report: ReportData) -> dict:
    """Build creator data mapping for JSON report."""
    creator_data = {}

    for s in scenarios:
        # Filter out scenarios in 前置/后置 directories
        if _is_fixture_dir(s):
            continue
        creator = s.creator or "未知"
        if creator not in creator_data:
            creator_data[creator] = {
                "scenarios": [],
                "total_scenarios": 0,
                "compliant_scenarios": 0,
                "total_violations": 0,
                "violations": {},
                "violation_scenario_ids": set(),
            }
        creator_data[creator]["scenarios"].append(s)
        creator_data[creator]["total_scenarios"] += 1

    # Count violations per creator
    for rr in report.rule_results:
        for r in rr.results:
            if r.passed or r.scenario_id is None:
                continue
            sc = scenarios_map.get(r.scenario_id)
            if not sc:
                continue
            creator = sc.creator or "未知"
            if creator not in creator_data:
                continue
            creator_data[creator]["violations"][rr.rule.id] = creator_data[creator]["violations"].get(rr.rule.id, 0) + 1
            creator_data[creator]["total_violations"] += 1
            creator_data[creator]["violation_scenario_ids"].add(r.scenario_id)

    # Calculate compliant scenarios
    for creator, data in creator_data.items():
        data["compliant_scenarios"] = data["total_scenarios"] - len(data["violation_scenario_ids"])

    return creator_data


def write_json_report(json_data: dict, output_path: str) -> str:
    """Write JSON report to file."""
    from pathlib import Path
    import json as _json
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        _json.dump(json_data, f, ensure_ascii=False, indent=2)
    return str(p.resolve())