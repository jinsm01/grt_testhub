"""Apply exclusion rules to apifox-check HTML report.

Exclusion rules (applied in order):
1. Directory exclusion: scenarios under "前置"/"后置" folders are excluded by apifox-check
   (handled during report generation, not by this script)
2. Name exclusion: scenarios with "前置" or "后置" in their name → data-fixture-skip="true"
3. "不算入统计" prefix: scenarios whose name starts with this → data-exclude="true"

For each excluded scenario:
- Add appropriate data attribute to detail rows
- Set is_violation=false in scenario-meta JSON
- Update stat preset values (stat-total, stat-compliant, stat-violation)
- Update creator tab counts

Usage:
    python apply_exclusions.py <path/to/report.html>
"""

import re
import json
import sys
import os


def load_html(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def save_html(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def collect_excluded_ids(html):
    """Scan all detail rows and classify excluded scenarios."""
    fixture_skip_ids = set()  # name contains 前置/后置
    exclude_ids = set()       # name starts with 不算入统计

    for row_tag, row_body in re.findall(
        r'(<tr class="detail-row"[^>]*>)(.*?</tr>)', html, re.DOTALL
    ):
        tds = re.findall(r'<td>([^<]*)</td>', row_body)
        if len(tds) >= 2:
            sid = tds[0].strip()
            name = tds[1].strip()
            if '前置' in name or '后置' in name:
                fixture_skip_ids.add(sid)
            if name.startswith('不算入统计'):
                exclude_ids.add(sid)

    return fixture_skip_ids, exclude_ids


def add_data_attributes(html, fixture_skip_ids, exclude_ids):
    """Add data-fixture-skip and data-exclude attributes to matching rows."""

    def add_attr(m):
        row_tag = m.group(1)
        row_body = m.group(2)
        tds = re.findall(r'<td>([^<]*)</td>', row_body)
        if len(tds) < 2:
            return m.group(0)

        name = tds[1].strip()
        if ('前置' in name or '后置' in name) and 'data-fixture-skip' not in row_tag:
            row_tag = row_tag.replace(
                'class="detail-row"',
                'class="detail-row" data-fixture-skip="true"'
            )
        if name.startswith('不算入统计') and 'data-exclude' not in row_tag:
            row_tag = row_tag.replace(
                'class="detail-row"',
                'class="detail-row" data-exclude="true"'
            )
        return row_tag + row_body

    return re.sub(
        r'(<tr class="detail-row"[^>]*>)(.*?</tr>)',
        add_attr, html, flags=re.DOTALL
    )


def fix_scenario_meta(html, all_excluded):
    """Remove excluded scenarios from scenario-meta JSON."""
    meta_count = 0

    def fix_meta(m):
        nonlocal meta_count
        full = m.group(0)
        json_start = full.index('>') + 1
        json_end = full.index('</script>')
        json_text = full[json_start:json_end]

        try:
            data = json.loads(json_text)
        except Exception:
            print(f'  WARN: Cannot parse scenario-meta JSON')
            return full

        original_len = len(data)
        # Remove excluded scenarios entirely
        data = [item for item in data if str(item.get('id', '')) not in all_excluded]
        removed = original_len - len(data)
        if removed > 0:
            meta_count += removed
            new_json = json.dumps(data, ensure_ascii=False, separators=(',', ': '))
            return full[:json_start] + new_json + full[json_end:]
        return full

    html = re.sub(
        r'<script id="scenario-meta-\d+" type="application/json">.*?</script>',
        fix_meta, html, flags=re.DOTALL
    )
    return html, meta_count


def compute_exclusion_per_creator(html, all_excluded):
    """Count excluded scenarios per creator section."""
    result = {}
    for ci in range(6):
        section_pat = rf'id="creator-{ci}"[^>]*>'
        m = re.search(section_pat, html)
        if not m:
            continue
        start = m.start()
        next_m = re.search(r'id="creator-\d+"[^>]*>', html[start + 1:])
        end = start + 1 + next_m.start() if next_m else len(html)
        section = html[start:end]

        section_ids = set()
        for rm in re.finditer(
            r'<tr class="detail-row"[^>]*>.*?<td>(\d+)</td>', section, re.DOTALL
        ):
            section_ids.add(rm.group(1))

        excluded = section_ids & all_excluded
        if excluded:
            result[ci] = len(excluded)
            print(f'  Creator {ci}: {len(excluded)} excluded ({sorted(excluded)})')
    return result


def update_stat_presets(html, exclusion_map):
    """Reduce stat-total by exclusion count per creator."""
    for ci, count in exclusion_map.items():
        def make_replacer(n):
            def replacer(m):
                old = int(m.group(2))
                return m.group(1) + str(old - n) + m.group(3)
            return replacer

        html = re.sub(
            rf'(id="stat-total-{ci}"\s*>)(\d+)(</b>)',
            make_replacer(count), html
        )
        html = re.sub(
            rf'(id="stat-violation-{ci}"\s*>)(\d+)(</b>)',
            make_replacer(count), html
        )
    return html


def update_creator_tabs(html, exclusion_map, all_excluded):
    """Update creator tab counts (NN总/MM合/KK违)."""

    # Build a mapping from creator name to tab index
    name_to_idx = {}
    for ci in range(6):
        m = re.search(rf'<span class="creator-tab[^"]*" id="ctab-{ci}"[^>]*>(.*?)</span>', html, re.DOTALL)
        if m:
            content = m.group(1)
            # Extract creator name (text before <span class="count">)
            name_m = re.search(r'^\s*([^<\s][^<]*)', content)
            if name_m:
                name = name_m.group(1).strip()
                name_to_idx[name] = ci

    def update_tab(m):
        name = m.group(1)
        count_text = m.group(2)
        parts = re.match(r'(\d+)总/(\d+)合/(\d+)违', count_text)
        if not parts:
            return m.group(0)
        total = int(parts.group(1))
        compliant = int(parts.group(2))
        violation = int(parts.group(3))

        tab_idx = name_to_idx.get(name)

        if tab_idx is not None and tab_idx in exclusion_map:
            n = exclusion_map[tab_idx]
            total -= n
            violation -= n
            print(f'  Tab {tab_idx} ({name}): {total}总/{compliant}合/{violation}违')
            return f'{name}<span class="count">({total}总/{compliant}合/{violation}违)</span>'

        return m.group(0)

    return re.sub(
        r'(车黎朋|杨金金|王晶|徐世辉|王盼阳|Jinsm01)'
        r'<span class="count">\((\d+总/\d+合/\d+违)\)</span>',
        update_tab, html
    )


# ============================================================
# CSS / JS feature injection
# ============================================================

CSS_INJECTION = """
/* === injected by apply_exclusions.py === */
/* Exclusion row hiding */
tr[data-fixture-skip="true"] { display: none !important; }
tr[data-exclude="true"] { display: none !important; }
/* Compliant section styles */
.compliant-section { display: none; margin-top: 12px; }
.compliant-section.visible { display: block; }
.compliant-table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
.compliant-table th { background: #28a745; color: #fff; padding: 8px 10px; text-align: left; font-size: 12px; white-space: nowrap; }
.compliant-table td { padding: 8px 10px; border-bottom: 1px solid #d4edda; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.compliant-table tr:nth-child(even) td { background: #f0fff4; }
.compliant-table tr:hover td { background: #d4edda; }
.compliant-toggle { font-size: 12px; color: #28a745; background: #e8f5e9; padding: 2px 10px; border-radius: 12px; cursor: pointer; }
/* Violation section toggle styles */
.violation-section { display: block; }
.violation-section.hidden { display: none; }
.violation-toggle { font-size: 12px; color: #e94560; background: #ffe0e6; padding: 2px 10px; border-radius: 12px; cursor: pointer; }
/* Compliant sortable header */
.compliant-table th.sortable { cursor: pointer; user-select: none; }
.compliant-table th.sortable:hover { background: #218838; }
.compliant-table th .sort-icon { margin-left: 4px; font-size: 10px; opacity: 0.5; }
.compliant-table th.sortable.asc .sort-icon { opacity: 1; }
.compliant-table th.sortable.desc .sort-icon { opacity: 1; }
/* Click-to-expand full-text display for description cells */
.data-table td.tooltip-cell { cursor: pointer; }
.tooltip-cell-inner { display: inline-block; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #1a73e8; border-bottom: 1px dashed #1a73e8; padding-bottom: 1px; transition: all 0.15s; }
.tooltip-cell-inner::after { content: ' \\25b6'; font-size: 10px; opacity: 0.6; margin-left: 4px; }
.tooltip-cell:hover .tooltip-cell-inner { background-color: #e8f0fe; border-bottom-style: solid; }
/* Full-text overlay popup */
.desc-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 99998; background: rgba(0,0,0,0.35); justify-content: center; align-items: center; animation: descOverlayIn 0.15s ease-out; }
.desc-overlay.visible { display: flex; }
.desc-overlay-box { max-width: 680px; width: 90%; max-height: 70vh; background: #fff; border-radius: 12px; box-shadow: 0 12px 48px rgba(0,0,0,0.3); padding: 24px 28px; overflow-y: auto; font-size: 13px; line-height: 1.9; color: #333; word-break: break-all; white-space: pre-wrap; }
.desc-overlay-title { font-weight: bold; font-size: 14px; color: #1a1a2e; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #e94560; display: flex; justify-content: space-between; align-items: center; }
.desc-overlay-close { background: none; border: none; font-size: 20px; cursor: pointer; color: #999; line-height: 1; padding: 0 4px; }
.desc-overlay-close:hover { color: #e94560; }
@keyframes descOverlayIn { from { opacity: 0; } to { opacity: 1; } }
/* Keep hover tooltip as secondary option */
.tooltip-text { visibility: hidden; opacity: 0; position: fixed; z-index: 99999; background: #1a1a2e; color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 12px; line-height: 1.7; max-width: 500px; white-space: normal; word-break: break-all; box-shadow: 0 6px 20px rgba(0,0,0,0.4); transition: opacity 0.15s ease, visibility 0.15s ease; pointer-events: none; }
"""

JS_INJECTION = """
/* === injected by apply_exclusions.py === */

function toggleViolation(idx) {
    var container = document.getElementById('violation-container-' + idx);
    var arrow = document.getElementById('violation-arrow-' + idx);
    var btn = document.getElementById('violation-btn-' + idx);
    if (!container) return;
    var isHidden = container.classList.contains('hidden');
    if (isHidden) {
        container.classList.remove('hidden');
        if (arrow) arrow.style.transform = 'rotate(90deg)';
        if (btn) btn.textContent = btn.textContent.replace('展开', '收起');
    } else {
        container.classList.add('hidden');
        if (arrow) arrow.style.transform = 'rotate(0deg)';
        if (btn) btn.textContent = btn.textContent.replace('收起', '展开');
    }
}

function toggleCompliant(idx) {
    var container = document.getElementById('compliant-container-' + idx);
    var arrow = document.getElementById('compliant-arrow-' + idx);
    var btn = document.getElementById('compliant-btn-' + idx);
    if (!container) return;
    var isVisible = container.classList.contains('visible');
    if (isVisible) {
        container.classList.remove('visible');
        if (arrow) arrow.style.transform = 'rotate(0deg)';
        if (btn) btn.textContent = btn.textContent.replace('收起', '展开');
    } else {
        container.classList.add('visible');
        if (arrow) arrow.style.transform = 'rotate(90deg)';
        if (btn) btn.textContent = btn.textContent.replace('展开', '收起');
    }
}

function buildCompliantTable(idx) {
    var section = document.getElementById('creator-' + idx);
    if (!section) return;
    var wrapperId = 'compliant-wrapper-' + idx;
    var wrapper = document.getElementById(wrapperId);
    if (!wrapper) {
        var detailTable = document.getElementById('detail-table-' + idx);
        if (!detailTable) return;
        wrapper = document.createElement('div');
        wrapper.id = wrapperId;
        wrapper.innerHTML = '<h3 style="cursor:pointer;display:flex;align-items:center;margin-top:24px;" onclick="toggleCompliant(' + idx + ')" id="compliant-header-' + idx + '">' +
            '<span style="display:inline-block;transition:transform 0.2s;margin-right:8px;font-size:12px;" id="compliant-arrow-' + idx + '">\\u25b6</span>' +
            '\\u5408\\u89c4\\u573a\\u666f\\u660e\\u7ec6' +
            '<span class="compliant-toggle" id="compliant-btn-' + idx + '" style="margin-left:12px;">\\u5c55\\u5f00\\u67e5\\u770b</span>' +
            '</h3>' +
            '<div id="compliant-container-' + idx + '" class="compliant-section"></div>';
        section.appendChild(wrapper);
    }

    var container = document.getElementById('compliant-container-' + idx);
    if (!container) return;

    var metaEl = document.getElementById('scenario-meta-' + idx);
    if (!metaEl) return;
    var allScenarios;
    try { allScenarios = JSON.parse(metaEl.textContent); } catch(e) { return; }

    var monthVal = (document.getElementById('filter-month-' + idx) || {}).value || 'all';
    var statusVal = (document.getElementById('filter-status-' + idx) || {}).value || 'all';

    var compliantItems = [];
    for (var i = 0; i < allScenarios.length; i++) {
        var sc = allScenarios[i];
        if (monthVal !== 'all' && sc.month !== monthVal) continue;
        if (statusVal !== 'all' && sc.run_status !== statusVal) continue;
        var folder = sc.folder || '';
        var name = sc.name || '';
        if (folder.indexOf('\\u524d\\u7f6e') !== -1 || folder.indexOf('\\u540e\\u7f6e') !== -1) continue;
        if (name.indexOf('\\u524d\\u7f6e') !== -1 || name.indexOf('\\u540e\\u7f6e') !== -1) continue;
        if (!sc.is_violation) {
            var runHtml = '';
            if (sc.run_status === 'passed') runHtml = '<span class="run-passed">\\u2705 \\u901a\\u8fc7</span>';
            else if (sc.run_status === 'failed') runHtml = '<span class="run-failed">\\u274c \\u5931\\u8d25</span>';
            else if (sc.run_status === 'not_run') runHtml = '<span class="run-notrun">\\u23f8\\ufe0f \\u672a\\u8fd0\\u884c</span>';
            else runHtml = '<span class="run-unknown">' + sc.run_status + '</span>';
            compliantItems.push({
                id: sc.id,
                name: sc.name || '',
                folder: sc.folder || '',
                time: sc.created_at || '',
                runHtml: runHtml
            });
        }
    }

    var btn = document.getElementById('compliant-btn-' + idx);
    if (btn) {
        btn.textContent = '\\u5171 ' + compliantItems.length + ' \\u6761 - \\u70b9\\u51fb' + (container.classList.contains('visible') ? '\\u6536\\u8d77' : '\\u5c55\\u5f00');
    }

    var html = '';
    if (compliantItems.length > 0) {
        html += '<div class="detail-filter-bar"><span class="filter-result" style="background:#d4edda;color:#28a745;">\\u5408\\u89c4\\u573a\\u666f\\u5171 ' + compliantItems.length + ' \\u6761</span></div>';
        html += '<table class="compliant-table"><thead><tr>';
        html += '<th class="sortable" onclick="sortCompliantTable(' + idx + ',0)">\\u573a\\u666fID<span class="sort-icon">\\u21c5</span></th>';
        html += '<th class="sortable" onclick="sortCompliantTable(' + idx + ',1)">\\u573a\\u666f\\u540d\\u79f0<span class="sort-icon">\\u21c5</span></th>';
        html += '<th class="sortable" onclick="sortCompliantTable(' + idx + ',2)">\\u5f52\\u5c5e\\u76ee\\u5f55<span class="sort-icon">\\u21c5</span></th>';
        html += '<th class="sortable" onclick="sortCompliantTable(' + idx + ',3)">\\u521b\\u5efa\\u65f6\\u95f4<span class="sort-icon">\\u21c5</span></th>';
        html += '<th>\\u8fd0\\u884c\\u7ed3\\u679c</th>';
        html += '</tr></thead><tbody>';
        for (var k = 0; k < compliantItems.length; k++) {
            var item = compliantItems[k];
            html += '<tr>';
            html += '<td>' + item.id + '</td>';
            html += '<td>' + item.name + '</td>';
            html += '<td>' + item.folder + '</td>';
            html += '<td>' + item.time + '</td>';
            html += '<td>' + item.runHtml + '</td>';
            html += '</tr>';
        }
        html += '</tbody></table>';
    } else {
        html = '<div class="detail-filter-bar"><span class="filter-result" style="color:#adb5bd;">\\u65e0\\u5408\\u89c4\\u573a\\u666f</span></div>';
    }
    container.innerHTML = html;
}

function setupViolationToggles() {
    for (var idx = 0; idx <= 5; idx++) {
        var section = document.getElementById('creator-' + idx);
        if (!section) continue;
        var h3 = section.querySelector('h3');
        if (!h3) continue;
        var filterBar = h3.nextElementSibling;
        var table = filterBar ? filterBar.nextElementSibling : null;
        if (!table || table.tagName !== 'TABLE') continue;
        if (document.getElementById('violation-wrapper-' + idx)) continue;
        var wrapper = document.createElement('div');
        wrapper.id = 'violation-wrapper-' + idx;
        var header = document.createElement('h3');
        header.style.cssText = 'cursor:pointer;display:flex;align-items:center;margin-top:24px;';
        header.onclick = function(i) { return function() { toggleViolation(i); }; }(idx);
        header.innerHTML = '<span style="display:inline-block;transition:transform 0.2s;margin-right:8px;font-size:12px;transform:rotate(90deg);" id="violation-arrow-' + idx + '">\\u25b6</span>' +
            '\\u8fdd\\u89c4\\u573a\\u666f\\u660e\\u7ec6' +
            '<span class="violation-toggle" id="violation-btn-' + idx + '" style="margin-left:12px;">\\u6536\\u8d77</span>';
        var container = document.createElement('div');
        container.id = 'violation-container-' + idx;
        container.className = 'violation-section';
        container.appendChild(filterBar);
        container.appendChild(table);
        wrapper.appendChild(header);
        wrapper.appendChild(container);
        h3.parentNode.insertBefore(wrapper, h3);
        h3.parentNode.removeChild(h3);
    }
}

function sortCompliantTable(idx, colIdx) {
    var container = document.getElementById('compliant-container-' + idx);
    if (!container) return;
    var table = container.querySelector('table.compliant-table');
    if (!table) return;
    var thead = table.querySelector('thead tr');
    if (!thead) return;
    var ths = thead.querySelectorAll('th.sortable');
    var th = ths[colIdx];
    if (!th) return;
    var isAsc = !th.classList.contains('asc');
    ths.forEach(function(t) { t.classList.remove('asc', 'desc'); });
    th.classList.add(isAsc ? 'asc' : 'desc');
    var tbody = table.querySelector('tbody');
    if (!tbody) return;
    var rows = Array.from(tbody.querySelectorAll('tr'));
    function getCellValue(row, col) {
        var cell = row.cells[col];
        if (!cell) return '';
        var text = cell.textContent.trim();
        if (col === 0) { var n = parseInt(text, 10); return isNaN(n) ? text : n; }
        if (col === 3) { var d = new Date(text.replace(/-/g, '/')); return isNaN(d.getTime()) ? text : d.getTime(); }
        return text;
    }
    rows.sort(function(a, b) {
        var va = getCellValue(a, colIdx);
        var vb = getCellValue(b, colIdx);
        if (typeof va === 'number' && typeof vb === 'number') {
            return isAsc ? va - vb : vb - va;
        }
        return isAsc ? String(va).localeCompare(String(vb), 'zh-CN') : String(vb).localeCompare(String(va), 'zh-CN');
    });
    rows.forEach(function(r) { tbody.appendChild(r); });
}

document.addEventListener('DOMContentLoaded', function() {
    setupViolationToggles();

    // Sync all creator tabs with full (unfiltered) data from scenario-meta JSON
    // This runs once on load and ensures tab labels match stat card values
    for (var i = 0; ; i++) {
        var metaEl = document.getElementById('scenario-meta-' + i);
        if (!metaEl) break;
        var allScenarios;
        try { allScenarios = JSON.parse(metaEl.textContent); } catch(e) { continue; }
        var filteredTotal = 0, filteredViol = 0;
        for (var j = 0; j < allScenarios.length; j++) {
            var sc = allScenarios[j];
            var folder = sc.folder || '';
            var name = sc.name || '';
            if (folder.indexOf('\\u524d\\u7f6e') !== -1 || folder.indexOf('\\u540e\\u7f6e') !== -1) continue;
            if (name.indexOf('\\u524d\\u7f6e') !== -1 || name.indexOf('\\u540e\\u7f6e') !== -1) continue;
            filteredTotal++;
            if (sc.is_violation) filteredViol++;
        }
        var filteredCompliant = filteredTotal - filteredViol;
        var tabEl = document.getElementById('ctab-' + i);
        if (tabEl) {
            var countSpan = tabEl.querySelector('.count');
            if (countSpan) {
                countSpan.textContent = '(' + filteredTotal + '\\u603b/' + filteredCompliant + '\\u5408/' + filteredViol + '\\u8fdd)';
            }
        }
    }

    // Tooltip hover - JS-controlled positioning and visibility
    var activeTooltip = null;
    document.querySelectorAll('.tooltip-cell').forEach(function(cell) {
        cell.addEventListener('mouseenter', function() {
            var tooltip = cell.querySelector('.tooltip-text');
            if (!tooltip) return;
            if (activeTooltip && activeTooltip !== tooltip) {
                activeTooltip.style.visibility = 'hidden';
                activeTooltip.style.opacity = '0';
            }
            var rect = cell.getBoundingClientRect();
            var tipW = tooltip.offsetWidth;
            var tipH = tooltip.offsetHeight;
            var left = rect.left + (rect.width / 2) - (tipW / 2);
            var top = rect.top + window.scrollY - tipH - 10;
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

    // Click-to-show full description overlay popup for tooltip cells
    var descOverlay = null;
    function ensureDescOverlay() {
        if (descOverlay) return descOverlay;
        descOverlay = document.createElement('div');
        descOverlay.className = 'desc-overlay';
        descOverlay.innerHTML = '<div class="desc-overlay-box"><div class="desc-overlay-title">\\u95ee\\u9898\\u8be6\\u60c5<button class="desc-overlay-close" id="desc-close-btn">&times;</button></div><div class="desc-overlay-body"></div></div>';
        document.body.appendChild(descOverlay);
        var closeFn = function() { descOverlay.classList.remove('visible'); };
        descOverlay.addEventListener('click', closeFn);
        document.getElementById('desc-close-btn').addEventListener('click', closeFn);
        return descOverlay;
    }

    document.querySelectorAll('.tooltip-cell').forEach(function(cell) {
        cell.addEventListener('click', function(e) {
            if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') return;
            e.stopPropagation();
            var fullText = cell.getAttribute('data-full-text') || '';
            if (!fullText) {
                var tt = cell.querySelector('.tooltip-text');
                fullText = tt ? (tt.getAttribute('data-tooltip') || tt.textContent || '') : '';
                cell.setAttribute('data-full-text', fullText);
            }
            if (!fullText) return;
            var overlay = ensureDescOverlay();
            overlay.querySelector('.desc-overlay-body').textContent = fullText;
            overlay.classList.add('visible');
        });
    });
});
"""


def inject_css_styles(html):
    """Inject additional CSS rules before </style>."""
    return html.replace('</style>', CSS_INJECTION + '\n</style>', 1)


def inject_js_features(html):
    """Inject violation toggle + compliant sort JS before the final </script>."""
    # Find the last </script> before </body>
    last_script = html.rfind('</script>')
    if last_script == -1:
        return html
    return html[:last_script] + JS_INJECTION + '\n' + html[last_script:]


def patch_build_compliant_table(html):
    """Add sortable headers to buildCompliantTable's compliant-table (for old-version CLI output)."""
    old = (
        "html += '<th>场景ID</th><th>场景名称</th>"
        "<th>归属目录</th><th>创建时间</th><th>运行结果</th>';"
    )
    new = (
        "html += '<th class=\"sortable\" onclick=\"sortCompliantTable(' + idx + ',0)\">"
        "场景ID<span class=\"sort-icon\">\\u21c5</span></th>';"
        "html += '<th class=\"sortable\" onclick=\"sortCompliantTable(' + idx + ',1)\">"
        "场景名称<span class=\"sort-icon\">\\u21c5</span></th>';"
        "html += '<th class=\"sortable\" onclick=\"sortCompliantTable(' + idx + ',2)\">"
        "归属目录<span class=\"sort-icon\">\\u21c5</span></th>';"
        "html += '<th class=\"sortable\" onclick=\"sortCompliantTable(' + idx + ',3)\">"
        "创建时间<span class=\"sort-icon\">\\u21c5</span></th>';"
        "html += '<th>运行结果</th>';"
    )
    return html.replace(old, new)


def patch_apply_filters(html):
    """Fix applyFilters to skip excluded rows and call buildCompliantTable (for new-version CLI output).
    
    The new CLI version's applyFilters does not:
    1. Skip rows with data-fixture-skip/data-exclude attributes
    2. Show valid (non-excluded) count instead of raw row count
    3. Call buildCompliantTable(idx)
    """
    # Fix: add skip logic for fixture/exclude rows in applyFilters
    old_loop = (
        "var visible = 0;\n"
        "    for (var i = 0; i < rows.length; i++) {\n"
        "        var r = rows[i];\n"
        "        var m = r.getAttribute('data-month') || '';\n"
        "        var s = r.getAttribute('data-runstatus') || '';"
    )
    new_loop = (
        "var visible = 0;\n"
        "    var totalValid = 0;\n"
        "    for (var i = 0; i < rows.length; i++) {\n"
        "        var r = rows[i];\n"
        "        if (r.getAttribute('data-fixture-skip') === 'true' || r.getAttribute('data-exclude') === 'true') continue;\n"
        "        totalValid++;\n"
        "        var m = r.getAttribute('data-month') || '';\n"
        "        var s = r.getAttribute('data-runstatus') || '';"
    )
    html = html.replace(old_loop, new_loop)

    # Fix: show valid count instead of raw rows.length
    old_count = "countEl.textContent = '显示 ' + visible + ' / ' + rows.length + ' 条';"
    new_count = "countEl.textContent = '显示 ' + visible + ' / ' + totalValid + ' 条';"
    html = html.replace(old_count, new_count)

    # Fix: add buildCompliantTable call after updateStats
    old_end = "    updateStats(idx, monthVal, statusVal);\n}"
    new_end = "    updateStats(idx, monthVal, statusVal);\n    // Build compliant scenario table\n    buildCompliantTable(idx);\n}"
    html = html.replace(old_end, new_end)

    return html


def patch_switch_creator(html):
    """Fix switchCreator to synchronize month/status filter state across tabs.

    When switching between creator tabs, the month and status filter values
    should be carried over from the previously active tab.
    """
    # Add global filter state variables before switchCreator (only if not already present)
    if "_currentMonthFilter" not in html or "_currentStatusFilter" not in html:
        old_func_start = "function switchCreator(idx) {"
        new_func_start = (
            "// Track current filter values for synchronization across tabs\n"
            "var _currentMonthFilter = 'all';\n"
            "var _currentStatusFilter = 'all';\n\n"
            "function switchCreator(idx) {"
        )
        html = html.replace(old_func_start, new_func_start)

    # Add sync logic inside switchCreator before the sections loop
    # Only patch if the sync logic is not already present (check for "Sync the target")
    if "Sync the target tab's dropdowns" not in html:
        old_sync = (
            "    for (var i = 0; i < sections.length; i++) {\n"
            "        if (sections[i].id === 'creator-' + idx) {\n"
            "            sections[i].style.display = '';\n"
            "            applyFilters(i);"
        )
        new_sync = (
            "    // Sync the target tab's dropdowns to the global filter state\n"
            "    var targetMonth = document.getElementById('filter-month-' + idx);\n"
            "    var targetStatus = document.getElementById('filter-status-' + idx);\n"
            "    if (targetMonth && _currentMonthFilter !== 'all') targetMonth.value = _currentMonthFilter;\n"
            "    if (targetStatus && _currentStatusFilter !== 'all') targetStatus.value = _currentStatusFilter;\n"
            "    for (var i = 0; i < sections.length; i++) {\n"
            "        if (sections[i].id === 'creator-' + idx) {\n"
            "            sections[i].style.display = '';\n"
            "            applyFilters(i);"
        )
        html = html.replace(old_sync, new_sync)

    # Add save filter state in applyFilters (only if not already present)
    if "Save current filter values for cross-tab synchronization" not in html:
        old_save = (
            "    var monthVal = monthEl ? monthEl.value : 'all';\n"
            "    var statusVal = statusEl ? statusEl.value : 'all';\n"
            "    var visible = 0;"
        )
        new_save = (
            "    var monthVal = monthEl ? monthEl.value : 'all';\n"
            "    var statusVal = statusEl ? statusEl.value : 'all';\n"
            "    // Save current filter values for cross-tab synchronization\n"
            "    _currentMonthFilter = monthVal;\n"
            "    _currentStatusFilter = statusVal;\n"
            "    var visible = 0;"
        )
        html = html.replace(old_save, new_save)

    return html


def patch_update_stats(html):
    """Fix updateStats to filter out fixture/setup scenarios (for new-version CLI output).
    
    The new CLI version's updateStats does not filter by folder/name containing 前置/后置.
    """
    old = (
        "        if (monthVal !== 'all' && sc.month !== monthVal) continue;\n"
        "        if (statusVal !== 'all' && sc.run_status !== statusVal) continue;\n"
        "        filteredTotal++;"
    )
    new = (
        "        if (monthVal !== 'all' && sc.month !== monthVal) continue;\n"
        "        if (statusVal !== 'all' && sc.run_status !== statusVal) continue;\n"
        "        var folder = sc.folder || '';\n"
        "        var name = sc.name || '';\n"
        "        if (folder.indexOf('前置') !== -1 || folder.indexOf('后置') !== -1) continue;\n"
        "        if (name.indexOf('前置') !== -1 || name.indexOf('后置') !== -1) continue;\n"
        "        filteredTotal++;"
    )
    html = html.replace(old, new)

    return html


def patch_sort_detail_table(html):
    """Fix sortDetailTable to skip excluded rows (for new-version CLI output)."""
    old = (
        "var rows = Array.from(tbody.querySelectorAll('tr.detail-row'));"
    )
    new = (
        "var rows = Array.from(tbody.querySelectorAll('tr.detail-row')).filter(function(r) {\n"
        "        return r.getAttribute('data-fixture-skip') !== 'true' && r.getAttribute('data-exclude') !== 'true';\n"
        "    });"
    )
    html = html.replace(old, new)
    return html


def patch_update_rule_table_from_rows(html):
    """Fix updateRuleTableFromRows to:
    1. Skip excluded/fixture rows and apply month/status filter
    2. Build tbody from ruleScenarioCounts instead of oldTbody rows (fixes stale data issue)
    3. Filter ruleScenarioCounts by scenario-rule-months when month filter is active

    Without fix #1, rows with data-exclude/data-fixture-skip attributes (skipped by
    applyFilters) would still be counted in the rule violation table.

    Without fix #2, after filtering to a month with no data, oldTbody is replaced with
    a 'no data' row. Subsequent filters to months WITH data cannot find rule names
    in the oldTbody, so the table permanently shows 'no data'.

    Without fix #3, the rule violation counts don't reflect the selected month filter
    because ruleScenarioCounts aggregates all months.
    """
    # Fix 1: Insert skip logic for exclude/fixture rows + month/status filter
    old_skip = (
        "        if (r.classList.contains('detail-row-hidden')) continue;\n"
        "        var cells = r.querySelectorAll('td');"
    )
    new_skip = (
        "        if (r.classList.contains('detail-row-hidden')) continue;\n"
        "        // Skip excluded/fixture rows (same as applyFilters logic)\n"
        "        if (r.getAttribute('data-exclude') === 'true' || r.getAttribute('data-fixture-skip') === 'true') continue;\n"
        "        // Also apply month/status filter on data attributes as a safety net\n"
        "        var m = r.getAttribute('data-month') || '';\n"
        "        var s = r.getAttribute('data-runstatus') || '';\n"
        "        if (monthVal !== 'all' && m !== monthVal) continue;\n"
        "        if (statusVal !== 'all' && s !== statusVal) continue;\n"
        "        var cells = r.querySelectorAll('td');"
    )
    html = html.replace(old_skip, new_skip)

    # Fix 2+3: Replace the oldTbody-dependent tbody-building section with a version
    # that builds directly from ruleScenarioCounts, caches severity info, and
    # filters counts by scenario-rule-months when month filter is active.
    old_build = (
        "    // Build new tbody\n"
        "    var severityMap = {\n"
        "        'severity-high': ['🔴 高', 'severity-high'],\n"
        "        'severity-mid': ['🟡 中', 'severity-mid'],\n"
        "        'severity-low': ['🟢 低', 'severity-low'],\n"
        "        'severity-skip': ['⏭️ 跳过', 'severity-skip']\n"
        "    };\n"
        "    var html = '';\n"
        "    var hasData = false;\n"
        "    // Try to preserve original rule order and severity from existing rows\n"
        "    var existingRows = oldTbody.querySelectorAll('tr');\n"
        "    for (var j = 0; j < existingRows.length; j++) {\n"
        "        var er = existingRows[j];\n"
        "        var ec = er.querySelectorAll('td');\n"
        "        if (ec.length < 3) continue;\n"
        "        var rName = ec[0].textContent.trim();\n"
        "        var count = ruleScenarioCounts[rName] || 0;\n"
        "        if (count > 0) {\n"
        "            hasData = true;\n"
        "            var sevClass = '';\n"
        "            var sevText = '';\n"
        "            for (var cls in severityMap) {\n"
        "                if (ec[2].classList.contains(cls)) {\n"
        "                    sevClass = severityMap[cls][1];\n"
        "                    sevText = severityMap[cls][0];\n"
        "                    break;\n"
        "                }\n"
        "            }\n"
        "            if (!sevClass) { sevClass = 'severity-mid'; sevText = '🟡 中'; }\n"
        "            html += '<tr><td>' + rName + '</td><td><b>' + count + '</b></td><td class=\"' + sevClass + '\">' + sevText + '</td></tr>';\n"
        "        }\n"
        "    }\n"
        "    if (!hasData) {\n"
        "        html = '<tr><td colspan=\"3\" style=\"text-align:center;color:#999;padding:20px;\">该筛选条件下无违规数据</td></tr>';\n"
        "    }\n"
        "    oldTbody.innerHTML = html;\n"
        "}"
    )
    new_build = (
        "    // Build new tbody from ruleScenarioCounts (not from oldTbody rows)\n"
        "    var severityMap = {\n"
        "        'severity-high': ['🔴 高', 'severity-high'],\n"
        "        'severity-mid': ['🟡 中', 'severity-mid'],\n"
        "        'severity-low': ['🟢 低', 'severity-low'],\n"
        "        'severity-skip': ['⏭️ 跳过', 'severity-skip']\n"
        "    };\n"
        "    // Cache original rule severity info on the summaryTable element\n"
        "    if (!summaryTable._ruleSeverityCache) {\n"
        "        var cache = {};\n"
        "        var origRows = oldTbody.querySelectorAll('tr');\n"
        "        for (var k = 0; k < origRows.length; k++) {\n"
        "            var tds = origRows[k].querySelectorAll('td');\n"
        "            if (tds.length < 3) continue;\n"
        "            var rn = tds[0].textContent.trim();\n"
        "            var sevClass = '';\n"
        "            var sevText = '';\n"
        "            for (var cls in severityMap) {\n"
        "                if (tds[2].classList.contains(cls)) {\n"
        "                    sevClass = severityMap[cls][1];\n"
        "                    sevText = severityMap[cls][0];\n"
        "                    break;\n"
        "                }\n"
        "            }\n"
        "            if (sevClass) {\n"
        "                cache[rn] = { class: sevClass, text: sevText };\n"
        "            }\n"
        "        }\n"
        "        summaryTable._ruleSeverityCache = cache;\n"
        "    }\n"
        "    var ruleSeverityCache = summaryTable._ruleSeverityCache;\n"
        "    // Load scenario-rule-months if available for month-filtered counts\n"
        "    var monthsEl = document.getElementById('scenario-rule-months-' + idx);\n"
        "    var scenarioRuleMonths = {};\n"
        "    if (monthsEl) {\n"
        "        try { scenarioRuleMonths = JSON.parse(monthsEl.textContent); } catch(e) {}\n"
        "    }\n"
        "    // Fallback: build from scenario-meta if months element missing\n"
        "    if (Object.keys(scenarioRuleMonths).length === 0) {\n"
        "        var metaEl2 = document.getElementById('scenario-meta-' + idx);\n"
        "        if (metaEl2) {\n"
        "            var allMeta;\n"
        "            try { allMeta = JSON.parse(metaEl2.textContent); } catch(e) {}\n"
        "            if (allMeta) {\n"
        "                for (var mi = 0; mi < allMeta.length; mi++) {\n"
        "                    var msc = allMeta[mi];\n"
        "                    scenarioRuleMonths[String(msc.id)] = msc.month;\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "    var html = '';\n"
        "    var hasData = false;\n"
        "    var ruleNames = Object.keys(ruleScenarioCounts).sort();\n"
        "    for (var ri = 0; ri < ruleNames.length; ri++) {\n"
        "        var rName = ruleNames[ri];\n"
        "        var count = 0;\n"
        "        var sidMap = ruleScenarioCounts[rName];\n"
        "        for (var sid in sidMap) {\n"
        "            if (monthVal !== 'all' && scenarioRuleMonths[sid] && scenarioRuleMonths[sid] !== monthVal) continue;\n"
        "            count += sidMap[sid];\n"
        "        }\n"
        "        if (count > 0) {\n"
        "            hasData = true;\n"
        "            var sevInfo = ruleSeverityCache[rName];\n"
        "            var sevClass = sevInfo ? sevInfo.class : 'severity-mid';\n"
        "            var sevText = sevInfo ? sevInfo.text : '🟡 中';\n"
        "            html += '<tr><td>' + rName + '</td><td><b>' + count + '</b></td><td class=\"' + sevClass + '\">' + sevText + '</td></tr>';\n"
        "        }\n"
        "    }\n"
        "    if (!hasData) {\n"
        "        html = '<tr><td colspan=\"3\" style=\"text-align:center;color:#999;padding:20px;\">该筛选条件下无违规数据</td></tr>';\n"
        "    }\n"
        "    oldTbody.innerHTML = html;\n"
        "}"
    )
    html = html.replace(old_build, new_build)
    return html


def patch_legacy_rule_table(html):
    """For legacy reports that have scenario-meta and updateStats but lack
    updateRuleTable/updateRuleTableFromRows entirely. Injects a complete
    updateRuleTable function and wires it into updateStats so the rule
    violation table dynamically follows month/status filters.

    This handles the "middle-version" reports where:
    - scenario-meta JSON is present
    - applyFilters / updateStats exist
    - but the rule summary table is static HTML with no JS rebuild logic
    """
    # Only patch if neither updateRuleTable nor updateRuleTableFromRows exists
    if 'function updateRuleTable' in html or 'function updateRuleTableFromRows' in html:
        return html

    # 1. Wire updateRuleTable call into updateStats
    old_update_stats_end = (
        "    // Update rule violation table dynamically based on filtered scenarios\n"
        "    updateRuleTable(idx, monthVal, statusVal);\n"
        "}"
    )
    # If the old pattern exists (shouldn't in pure legacy), skip
    if old_update_stats_end in html:
        return html

    # Try to find the end of updateStats and add the call
    # Legacy updateStats ends with rateTextEl.style.display = 'none'; then }
    legacy_end = (
        "        } else {\n"
        "            rateTextEl.style.display = 'none';\n"
        "        }\n"
        "    }\n"
        "}"
    )
    if legacy_end in html:
        new_legacy_end = (
        "        } else {\n"
        "            rateTextEl.style.display = 'none';\n"
        "        }\n"
        "    }\n"
        "    // Update rule violation table dynamically based on filtered scenarios\n"
        "    updateRuleTable(idx, monthVal, statusVal);\n"
        "}"
        )
        html = html.replace(legacy_end, new_legacy_end)
    else:
        # Fallback: try another pattern
        alt_end = (
            "            rateTextEl.style.display = 'none';\n"
            "        }\n"
            "    }\n"
            "}\n"
            "\n"
            "// Apply filter on page load"
        )
        new_alt_end = (
            "            rateTextEl.style.display = 'none';\n"
            "        }\n"
            "    }\n"
            "    // Update rule violation table dynamically based on filtered scenarios\n"
            "    updateRuleTable(idx, monthVal, statusVal);\n"
            "}\n"
            "\n"
            "// Apply filter on page load"
        )
        html = html.replace(alt_end, new_alt_end)

    # 2. Inject updateRuleTable function before the final </script>
    update_rule_table_js = """
// Dynamically rebuild rule violation table based on filtered scenarios
function updateRuleTable(idx, monthVal, statusVal) {
    var metaEl = document.getElementById('scenario-meta-' + idx);
    var table = document.getElementById('detail-table-' + idx);
    var statsDiv = document.getElementById('creator-' + idx);
    if (!metaEl || !table || !statsDiv) return;

    var allScenarios;
    try { allScenarios = JSON.parse(metaEl.textContent); } catch(e) { return; }

    // Build set of scenario IDs that pass the current filters
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

    // Count violations per rule from visible detail rows
    var ruleCounts = {};
    var rows = table.querySelectorAll('tr.detail-row');
    for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        if (r.classList.contains('detail-row-hidden')) continue;
        if (r.getAttribute('data-exclude') === 'true' || r.getAttribute('data-fixture-skip') === 'true') continue;
        var cells = r.querySelectorAll('td');
        if (cells.length < 4) continue;
        var scenarioId = cells[0].textContent.trim();
        var ruleName = cells[3].textContent.trim();
        if (!filteredScenarioIds[scenarioId]) continue;
        ruleCounts[ruleName] = (ruleCounts[ruleName] || 0) + 1;
    }

    // Find summary table and rebuild tbody
    var summaryTable = statsDiv.querySelector('.creator-stats .summary-table');
    if (!summaryTable) return;
    var oldTbody = summaryTable.querySelector('tbody');
    if (!oldTbody) return;

    // Cache severity info from original rows
    var severityMap = {
        'severity-high': ['\\u1f534 \\u9ad8', 'severity-high'],
        'severity-mid': ['\\u1f7e1 \\u4e2d', 'severity-mid'],
        'severity-low': ['\\u1f7e2 \\u4f4e', 'severity-low'],
        'severity-skip': ['\\u23ed\\ufe0f \\u8df3\\u8fc7', 'severity-skip']
    };
    if (!summaryTable._ruleSeverityCache) {
        var cache = {};
        var origRows = oldTbody.querySelectorAll('tr');
        for (var k = 0; k < origRows.length; k++) {
            var tds = origRows[k].querySelectorAll('td');
            if (tds.length < 3) continue;
            var rn = tds[0].textContent.trim();
            var sevClass = '';
            var sevText = '';
            for (var cls in severityMap) {
                if (tds[2].classList.contains(cls)) {
                    sevClass = severityMap[cls][1];
                    sevText = severityMap[cls][0];
                    break;
                }
            }
            if (sevClass) {
                cache[rn] = { class: sevClass, text: sevText };
            }
        }
        summaryTable._ruleSeverityCache = cache;
    }
    var ruleSeverityCache = summaryTable._ruleSeverityCache;

    var html = '';
    var hasData = false;
    var ruleNames = Object.keys(ruleCounts).sort();
    for (var ri = 0; ri < ruleNames.length; ri++) {
        var rName = ruleNames[ri];
        var count = ruleCounts[rName];
        if (count > 0) {
            hasData = true;
            var sevInfo = ruleSeverityCache[rName];
            var sevClass = sevInfo ? sevInfo.class : 'severity-mid';
            var sevText = sevInfo ? sevInfo.text : '\\u1f7e1 \\u4e2d';
            html += '<tr><td>' + rName + '</td><td><b>' + count + '</b></td><td class="' + sevClass + '">' + sevText + '</td></tr>';
        }
    }
    if (!hasData) {
        html = '<tr><td colspan="3" style="text-align:center;color:#999;padding:20px;">\\u8be5\\u7b5b\\u9009\\u6761\\u4ef6\\u4e0b\\u65e0\\u8fdd\\u89c4\\u6570\\u636e</td></tr>';
    }
    oldTbody.innerHTML = html;
}
"""

    # Find a good place to inject: before the last </script> tag that contains DOMContentLoaded
    # or before the sortDetailTable function
    inject_marker = "// Sort detail table by column"
    if inject_marker in html:
        html = html.replace(inject_marker, update_rule_table_js + "\n" + inject_marker)
    else:
        # Fallback: inject before the final </script>
        last_script = html.rfind('</script>')
        if last_script != -1:
            html = html[:last_script] + update_rule_table_js + "\n" + html[last_script:]

    return html


def main():
    if len(sys.argv) < 2:
        # Default: look for report in current directory
        report_path = 'apifox-check-report.html'
        if not os.path.exists(report_path):
            print('Usage: python apply_exclusions.py <path/to/report.html>')
            sys.exit(1)
    else:
        report_path = sys.argv[1]

    print(f'Processing: {report_path}')
    html = load_html(report_path)

    # Step 1: Collect excluded IDs
    fixture_skip_ids, exclude_ids = collect_excluded_ids(html)
    all_excluded = fixture_skip_ids | exclude_ids
    print(f'Fixture-skip IDs: {len(fixture_skip_ids)}')
    print(f'Exclude IDs: {len(exclude_ids)}')
    print(f'Total excluded: {len(all_excluded)}')

    if len(all_excluded) == 0:
        print('No excluded scenarios found. Skipping exclusion steps.')
    else:
        # Step 2: Add data attributes
        html = add_data_attributes(html, fixture_skip_ids, exclude_ids)
        print(f'Added data attributes to rows.')

        # Step 3: Fix scenario-meta JSON
        html, meta_count = fix_scenario_meta(html, all_excluded)
        print(f'Fixed {meta_count} scenario-meta entries.')

        # Step 4: Compute per-creator exclusion counts
        print('\nExclusion per creator:')
        exclusion_map = compute_exclusion_per_creator(html, all_excluded)

        # Step 5: Update stat presets
        html = update_stat_presets(html, exclusion_map)
        print('\nUpdated stat presets.')

        # Step 6: Update creator tab counts
        html = update_creator_tabs(html, exclusion_map, all_excluded)

    # Step 7: Patch missing JS functions (for new-version CLI output that lacks them)
    html = patch_switch_creator(html)
    html = patch_apply_filters(html)
    html = patch_update_stats(html)
    html = patch_sort_detail_table(html)
    html = patch_update_rule_table_from_rows(html)
    html = patch_legacy_rule_table(html)
    print('\nPatched JS functions (switchCreator, applyFilters, updateStats, sortDetailTable, updateRuleTableFromRows, legacyRuleTable).')

    # Step 8: Inject UI features (violation toggle, compliant sort) — always run
    html = inject_css_styles(html)
    html = patch_build_compliant_table(html)
    html = inject_js_features(html)
    print('Injected UI features (violation toggle, compliant sort).')

    save_html(report_path, html)
    print(f'\nDone! Updated: {report_path}')


if __name__ == '__main__':
    main()
