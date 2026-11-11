"""
Apifox 自动化场景检查 - 后端视图
提供配置管理、报告生成、报告查阅接口
"""
import os
import re
import json
import asyncio
import shutil
import tempfile
import subprocess
import uuid
import threading
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# 导入测试执行相关模型 - 用于将 Apifox 运行结果写入统一报告系统
from .models import ApiProject, TestSuite, TestExecution, User, Environment

# 配置文件路径
CONFIG_FILE = os.path.join(settings.BASE_DIR, 'data', 'apifox_check_config.json')
REPORTS_DIR = os.path.join(settings.MEDIA_ROOT, 'apifox-check-reports')

# apifox-check CLI 所在 Python 路径（使用当前运行 Django 的 Python，确保依赖一致）
import sys
PYTHON_EXE = sys.executable

# 技能脚本目录（相对于项目根目录，跨平台通用）
SKILL_SCRIPTS_DIR = os.path.join(settings.BASE_DIR, 'skills', 'apifox-scene-check', 'scripts')

# 第三方包路径 - 用于加载 apifox_check
THIRD_PARTY_DIR = os.path.join(settings.BASE_DIR, 'third_party')
APIFOX_CHECK_DIR = os.path.join(THIRD_PARTY_DIR, 'apifox_check')

# 将 third_party 目录加入 sys.path，使得可以直接 import apifox_check
if THIRD_PARTY_DIR not in sys.path:
    sys.path.insert(0, THIRD_PARTY_DIR)

APPLY_EXCLUSIONS_SCRIPT = os.path.join(SKILL_SCRIPTS_DIR, 'apply_exclusions.py')
VERIFY_EXCLUSIONS_SCRIPT = os.path.join(SKILL_SCRIPTS_DIR, 'verify_exclusions.py')

# 运行报告目录
RUN_REPORTS_DIR = os.path.join(settings.MEDIA_ROOT, 'apifox-run-reports')

# 生成任务状态存储 (内存中)
_task_status = {}

# 运行任务状态存储 (内存中)
_run_task_status = {}


def _ensure_dirs():
    """确保必要的目录存在"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)


def _load_config():
    """加载 Apifox 检查配置"""
    _ensure_dirs()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # 确保 id_field_exemptions 字段存在，并迁移旧格式
        if 'id_field_exemptions' not in config:
            config['id_field_exemptions'] = []
        else:
            config['id_field_exemptions'] = _migrate_exemptions(config['id_field_exemptions'])
        return config
    return {
        'project_id': '7366718',
        'environment_id': '39566850',
        'access_token': '',
        'id_field_exemptions': [],
    }


def _migrate_exemptions(exemptions):
    """将旧格式的字符串列表迁移为新格式的对象列表。
    旧格式: ["order_id", "user_id"]
    新格式: [{"field":"order_id","reason":"","added_by":"","added_at":"","enabled":true}, ...]
    """
    if not exemptions:
        return []
    migrated = []
    for item in exemptions:
        if isinstance(item, str):
            # 旧格式：纯字符串
            migrated.append({
                'field': item.strip().lower(),
                'reason': '',
                'added_by': '',
                'added_at': '',
                'enabled': True,
            })
        elif isinstance(item, dict):
            # 确保必备字段
            item.setdefault('field', '')
            item.setdefault('reason', '')
            item.setdefault('added_by', '')
            item.setdefault('added_at', '')
            item.setdefault('enabled', True)
            migrated.append(item)
    return migrated


def _save_config(config_data):
    """保存 Apifox 检查配置"""
    _ensure_dirs()
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)


def _extract_cli_error(stderr):
    """从 CLI stderr 中提取有用的错误信息，去掉 Python traceback"""
    lines = [l.strip() for l in stderr.strip().splitlines() if l.strip()]
    if not lines:
        return stderr[:200]
    # 倒序查找第一个异常消息行（通常格式为 XxxError: message）
    for line in reversed(lines):
        if ':' in line and not line.startswith('File "'):
            return line[:400]
    return lines[-1][:400]


def _get_default_rules():
    """获取内置默认规则定义（来自 YAML 配置）"""
    return [
        {'id': 'scenario-run-passed',      'name': '场景运行通过',           'severity': 'high', 'desc': '检查场景最近一次运行是否通过'},
        {'id': 'scenario-step-count',       'name': '单场景步骤数不超过10步',   'severity': 'mid', 'desc': '检查单个测试场景步骤数是否超过10步（不包含引用其他场景或分组的步骤）'},
        {'id': 'crud-query-assert',         'name': '增删改后查询断言',       'severity': 'high', 'desc': '增删改(POST/PUT/DELETE/PATCH)操作后是否/search查询步骤并使用断言校验'},
        {'id': 'no-hardcoded-id',           'name': 'Id参数不能写死',          'severity': 'high', 'desc': '检查步骤请求body中带有Id的参数是否硬编码而非使用变量'},
        {'id': 'param-from-prev-step',      'name': '参数来源校验',           'severity': 'high', 'desc': '检查后续步骤用到的参数是否从前置步骤中或变量获取，而非硬编码'},
        {'id': 'auto-name-tag',             'name': '名称参数自动化标识',     'severity': 'high', 'desc': '检查POST/PUT步骤中name/title等字段是否含"自动化"标识且为动态值（提取token步骤除外）'},
        {'id': 'fixture-dir-skip',          'name': '前置后置目录跳过统计',   'severity': 'skip', 'desc': '前置/后置目录下的场景不参与校验统计'},
    ]


def _load_rule_statuses():
    """从配置文件加载用户设置的规则启用/停用状态"""
    config = _load_config()
    return config.get('rule_statuses', {})


def _save_rule_statuses(rule_statuses):
    """保存规则启用/停用状态到配置文件"""
    config = _load_config()
    config['rule_statuses'] = rule_statuses
    _save_config(config)


def _run_apifox_check(project_id, environment_id, access_token, output_path,
                       id_field_exemptions=None, disabled_rule_ids=None):
    """运行 apifox-check CLI 生成原始报告"""
    # 构建命令行参数列表（避免 shell 字符串拼接的转义问题）
    cmd_args = [
        PYTHON_EXE,
        '-c',
        (
            'from apifox_check.cli import main; '
            'import sys; '
            f'sys.argv = [\'apifox-check\', \'--project-id\', {project_id!r}, \'--environment-id\', {environment_id!r}, \'--access-token\', {access_token!r}'
            + (f', \'--id-exemptions\', {",".join(id_field_exemptions)!r}' if id_field_exemptions else '')
            + (f', \'--exclude\', {",".join(disabled_rule_ids)!r}' if disabled_rule_ids else '')
            + f', \'--output\', {output_path!r}]; '
            'main(); '
            'print(\'DONE\')'
        ),
    ]

    # 通过环境变量设置 PYTHONPATH，避免 Windows 路径反斜杠转义问题
    env = os.environ.copy()
    pythonpath_parts = []
    if os.path.exists(APIFOX_CHECK_DIR):
        pythonpath_parts.append(THIRD_PARTY_DIR)
    existing_pythonpath = env.get('PYTHONPATH', '')
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    if pythonpath_parts:
        env['PYTHONPATH'] = os.pathsep.join(pythonpath_parts)

    result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=300, env=env, cwd=settings.BASE_DIR)
    success = result.returncode == 0 and 'DONE' in result.stdout
    if not success:
        error_msg = _extract_cli_error(result.stderr)
        return False, result.stdout, error_msg
    return True, result.stdout, result.stderr


def _save_report_meta(report_filename, meta):
    """保存报告元数据"""
    meta_file = os.path.join(REPORTS_DIR, report_filename + '.meta.json')
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def _load_report_meta(report_filename):
    """加载报告元数据"""
    meta_file = os.path.join(REPORTS_DIR, report_filename + '.meta.json')
    if os.path.exists(meta_file):
        with open(meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _run_apply_exclusions(report_path):
    """运行 apply_exclusions.py 后处理脚本"""
    cmd = f'"{PYTHON_EXE}" "{APPLY_EXCLUSIONS_SCRIPT}" "{report_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    return result.returncode == 0, result.stdout, result.stderr


def _run_verify_exclusions(report_path):
    """运行 verify_exclusions.py 验证脚本"""
    cmd = f'"{PYTHON_EXE}" "{VERIFY_EXCLUSIONS_SCRIPT}" "{report_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.returncode == 0, result.stdout, result.stderr


# ============================================================
# 平台风格 CSS 注入（TestHub 紫色主题统一）
# ============================================================

PLATFORM_CSS_OVERRIDE = """
/* ===== TestHub Platform Theme Override ===== */
/* 整体背景与字体 */
body {
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  color: #333;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  line-height: 1.6;
}

/* 页面头部 */
h1 {
  text-align: center;
  color: #5a32a3;
  font-size: 28px;
  font-weight: 700;
  border-bottom: 3px solid rgba(123, 66, 246, 0.3);
  padding-bottom: 14px;
  margin-bottom: 24px;
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
h1::after {
  content: '';
  display: block;
  width: 80px;
  height: 3px;
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  margin: 10px auto 0;
  border-radius: 2px;
  -webkit-text-fill-color: transparent;
}
h2 {
  color: #5a32a3;
  font-size: 20px;
  border-left: 4px solid #7b42f6;
  padding-left: 14px;
  margin-top: 32px;
  font-weight: 600;
}
h3 {
  color: #5a32a3;
  font-size: 16px;
  margin-top: 24px;
  font-weight: 600;
}

/* 元信息卡片 */
.meta {
  background: #ffffff;
  border-radius: 12px;
  padding: 18px 24px;
  margin-bottom: 20px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  border: 1px solid rgba(147, 112, 219, 0.12);
}
.meta b { color: #5a32a3; }

/* 汇总表格 */
.summary-table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  border: 1px solid rgba(147, 112, 219, 0.1);
}
.summary-table th {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: #fff;
  padding: 12px 14px;
  font-size: 14px;
  text-align: center;
  font-weight: 600;
}
.summary-table td {
  padding: 12px 14px;
  font-size: 14px;
  text-align: center;
  border-bottom: 1px solid rgba(147, 112, 219, 0.08);
}
.summary-table tr:hover td { background: #f8f7ff; }

/* 规则区块 */
.rule-section {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.06);
  border: 1px solid rgba(147, 112, 219, 0.1);
}
.rule-title { font-size: 18px; font-weight: 700; color: #5a32a3; }

/* 状态标签增强 */
.status-violate {
  background: #ffe8ec;
  color: #e94560;
  font-weight: 600;
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 13px;
}
.status-partial {
  background: #fff4e5;
  color: #f5a623;
  font-weight: 600;
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 13px;
}
.status-ok {
  background: #e8f5e9;
  color: #28a745;
  font-weight: 600;
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 13px;
}
.status-skip {
  background: #f0f0f0;
  color: #6c757d;
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 13px;
}

/* badge 增强 */
.rule-badge {
  padding: 5px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
.badge-high { background: linear-gradient(135deg, #e94560, #d63345); color: #fff; }
.badge-mid { background: linear-gradient(135deg, #f5a623, #e09515); color: #fff; }
.badge-low { background: linear-gradient(135deg, #28a745, #20a038); color: #fff; }
.badge-skip { background: #b0b0b0; color: #fff; }

/* 数据表格 */
.data-table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13px;
  border-radius: 8px;
  overflow: hidden;
}
.data-table th {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: #fff;
  padding: 10px 12px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}
.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.08);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.data-table tr:nth-child(even) td { background: #fafbff; }
.data-table tr:hover td { background: #f5f3ff; }

/* 可排序表头 hover */
.sortable:hover { background: #6b32e6; }

/* 创建人区块 */
.creator-section {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.06);
  border: 1px solid rgba(147, 112, 219, 0.1);
}
.creator-title { font-size: 18px; font-weight: 700; color: #5a32a3; }

/* 创建人 Tab 导航 */
.creator-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.creator-tab {
  padding: 8px 18px;
  border-radius: 22px;
  background: rgba(147, 112, 219, 0.08);
  color: #6d5d8f;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.25s ease;
  border: 1px solid transparent;
}
.creator-tab:hover {
  background: rgba(147, 112, 219, 0.18);
  color: #5a32a3;
  transform: translateY(-1px);
}
.creator-tab.active {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: #fff;
  box-shadow: 0 4px 14px rgba(123, 66, 246, 0.35);
  border-color: transparent;
}

/* 筛选栏 */
.filter-bar,
.header-filters {
  background: #fafbff;
  border-radius: 10px;
  padding: 12px 16px;
  border: 1px solid rgba(147, 112, 219, 0.08);
}
.filter-bar select,
.header-filters select {
  padding: 6px 10px;
  border: 1px solid rgba(147, 112, 219, 0.2);
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  transition: border-color 0.2s;
}
.filter-bar select:focus,
.header-filters select:focus {
  border-color: #7b42f6;
  outline: none;
  box-shadow: 0 0 0 2px rgba(123, 66, 246, 0.15);
}

/* 运行状态图标增强 */
.run-passed { color: #28a745; font-weight: 600; }
.run-failed { color: #e94560; font-weight: 600; }
.run-notrun { color: #b0b0b0; }
.run-running { color: #f5a623; font-weight: 600; }

/* 影响与修复提示 */
.impact {
  background: #fff8e1;
  border-left: 4px solid #f5a623;
  padding: 14px 18px;
  margin: 14px 0;
  border-radius: 0 10px 10px 0;
  font-size: 14px;
}
.fix {
  background: #e8f5e9;
  border-left: 4px solid #28a745;
  padding: 14px 18px;
  margin: 14px 0;
  border-radius: 0 10px 10px 0;
  font-size: 14px;
}

/* 页脚 */
.footer {
  text-align: center;
  padding: 24px 0;
  color: #8c8c8c;
  font-size: 13px;
  border-top: 1px solid rgba(147, 112, 219, 0.1);
  margin-top: 32px;
}

/* 详情筛选计数 */
.detail-filter-bar .filter-result {
  background: rgba(147, 112, 219, 0.08);
  color: #6d5d8f;
  padding: 5px 14px;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 500;
}

/* 合规/违规开关增强 */
.compliant-toggle {
  background: #e8f5e9;
  color: #28a745;
  padding: 3px 12px;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 500;
}
.violation-toggle {
  background: #ffe8ec;
  color: #e94560;
  padding: 3px 12px;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 500;
}

/* 描述浮层 */
.desc-overlay-box {
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.15);
}
.desc-overlay-title {
  color: #5a32a3;
  border-bottom-color: #7b42f6;
}

/* Tooltip */
.tooltip-text {
  background: #5a32a3;
  box-shadow: 0 6px 24px rgba(90, 50, 163, 0.35);
}

/* 合规表格 */
.compliant-table th {
  background: linear-gradient(135deg, #28a745, #20a038);
}
.compliant-table tr:nth-child(even) td { background: #f2fcf5; }
.compliant-table tr:hover td { background: #e8f5e9; }
"""

PLATFORM_JS_ENHANCE = """
// ===== TestHub Platform JS Enhance =====
// 页面加载完成后添加微交互
document.addEventListener('DOMContentLoaded', function() {
  // 为汇总表格行添加悬浮效果
  document.querySelectorAll('.summary-table tbody tr').forEach(function(row) {
    row.addEventListener('mouseenter', function() {
      this.style.transform = 'translateX(4px)';
      this.style.transition = 'transform 0.2s ease';
    });
    row.addEventListener('mouseleave', function() {
      this.style.transform = 'translateX(0)';
    });
  });

  // 为规则区块添加序号标记
  document.querySelectorAll('.rule-section').forEach(function(section, idx) {
    var header = section.querySelector('.rule-header');
    if (header) {
      var badge = document.createElement('span');
      badge.textContent = '规则 ' + (idx + 1);
      badge.style.cssText = 'background:linear-gradient(135deg,#7b42f6,#5a32a3);color:#fff;padding:2px 12px;border-radius:14px;font-size:12px;font-weight:600;margin-right:12px;';
      header.insertBefore(badge, header.firstChild);
    }
  });

  // 为创建人卡片添加渐变顶部装饰线
  document.querySelectorAll('.creator-section').forEach(function(section) {
    var line = document.createElement('div');
    line.style.cssText = 'height:3px;background:linear-gradient(135deg,#7b42f6,#5a32a3);border-radius:2px;margin-bottom:16px;';
    section.insertBefore(line, section.firstChild);
  });

  // 表格悬浮行增强
  document.querySelectorAll('.data-table tbody tr').forEach(function(row) {
    row.addEventListener('mouseenter', function() {
      this.style.boxShadow = '0 2px 8px rgba(147,112,219,0.12)';
      this.style.transition = 'all 0.2s ease';
      this.style.position = 'relative';
      this.style.zIndex = '1';
    });
    row.addEventListener('mouseleave', function() {
      this.style.boxShadow = 'none';
    });
  });
});
"""


def _inject_platform_styles(report_path):
    """在报告中注入 TestHub 平台统一风格 CSS 和 JS"""
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            html = f.read()

        # 在第一个 </style> 之前注入平台 CSS
        platform_style_block = f'<style>\n{PLATFORM_CSS_OVERRIDE}\n</style>'
        
        # 查找已有的 <style> 块结束位置，在最后一个 </style> 之后注入
        last_style_pos = html.rfind('</style>')
        if last_style_pos != -1:
            html = html[:last_style_pos + 8] + '\n' + platform_style_block + html[last_style_pos + 8:]
        else:
            # 如果没有 <style>，注入到 </head> 之前
            head_pos = html.find('</head>')
            if head_pos != -1:
                html = html[:head_pos] + platform_style_block + '\n' + html[head_pos:]
            else:
                # 最后兜底：注入到 <body> 之后
                body_pos = html.find('<body>')
                if body_pos != -1:
                    html = html[:body_pos + 6] + platform_style_block + '\n' + html[body_pos + 6:]

        # 在 </body> 之前注入平台 JS
        platform_js_block = f'<script>\n{PLATFORM_JS_ENHANCE}\n</script>'
        body_end = html.rfind('</body>')
        if body_end != -1:
            html = html[:body_end] + platform_js_block + '\n' + html[body_end:]

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return True, "平台样式注入成功"
    except Exception as e:
        return False, str(e)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def apifox_check_config(request):
    """获取或更新 Apifox 检查配置"""
    if request.method == 'GET':
        config = _load_config()
        # 返回时隐藏 access_token 的部分内容
        token = config.get('access_token', '')
        masked_token = token[:8] + '****' + token[-4:] if len(token) > 12 else token
        exemption_data = config.get('id_field_exemptions', [])
        return Response({
            'project_id': config.get('project_id', ''),
            'environment_id': config.get('environment_id', ''),
            'access_token': masked_token,
            'has_token': bool(token),
            'id_field_exemptions': exemption_data,
            'id_field_exemptions_enabled': [e['field'] for e in exemption_data if e.get('enabled')],
            'local_environment_id': config.get('local_environment_id'),
        })
    
    elif request.method == 'POST':
        config = _load_config()
        data = request.data
        if 'project_id' in data:
            config['project_id'] = data['project_id']
        if 'environment_id' in data:
            config['environment_id'] = data['environment_id']
        if 'local_environment_id' in data:
            config['local_environment_id'] = data['local_environment_id']
        if 'access_token' in data and data['access_token']:
            token = data['access_token']
            # 拒绝保存被 masking 的 token（包含 ****）
            if '****' in token:
                return Response({
                    'error': 'Access Token 不能为脱敏值，请输入完整的 Token',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
            # 校验 token 格式：Apifox Token 通常为 APS-xxx 或长字符串，拒绝明显无效的值
            if token.endswith('.html') or token.endswith('.json'):
                return Response({
                    'error': 'Access Token 格式无效（看起来是文件名），请输入正确的 Apifox Access Token',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
            if len(token) < 10:
                return Response({
                    'error': 'Access Token 长度过短，请输入完整的 Apifox Access Token',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
            config['access_token'] = token
        # 允许通过 POST 保存豁免列表（批量替换）- 支持新旧格式
        if 'id_field_exemptions' in data:
            config['id_field_exemptions'] = _migrate_exemptions(data['id_field_exemptions'])
        _save_config(config)
        return Response({'message': '配置已保存', 'success': True})


# ============================================================
# 检查规则管理 API
# ============================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def apifox_check_rules(request):
    """获取或更新检查规则的启用/停用状态"""
    if request.method == 'GET':
        default_rules = _get_default_rules()
        rule_statuses = _load_rule_statuses()

        rules = []
        for idx, rule in enumerate(default_rules, 1):
            rule_id = rule['id']
            # 用户设置的状态，默认为启用
            enabled = rule_statuses.get(rule_id, True) if isinstance(rule_statuses, dict) else True
            rules.append({
                'index': idx,
                'id': rule_id,
                'name': rule['name'],
                'severity': {'high': '高', 'mid': '中', 'low': '低', 'skip': '跳过'}.get(rule['severity'], rule['severity']),
                'desc': rule['desc'],
                'enabled': enabled,
                # 前端 tag 类型映射
                'severityType': {'high': 'danger', 'mid': 'warning', 'low': '', 'skip': 'info'}.get(rule['severity'], ''),
            })

        return Response({
            'rules': rules,
            'success': True,
        })

    elif request.method == 'POST':
        action = request.data.get('action', '')

        if action == 'toggle':
            # 切换单条规则的启用/停用状态
            rule_id = request.data.get('rule_id', '')
            enabled = request.data.get('enabled')

            if not rule_id:
                return Response({
                    'error': '请提供规则 ID',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)

            if enabled is None:
                return Response({
                    'error': '请提供 enabled 状态 (true/false)',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)

            # 验证规则是否存在
            valid_ids = {r['id'] for r in _get_default_rules()}
            if rule_id not in valid_ids:
                return Response({
                    'error': f'规则「{rule_id}」不存在',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)

            # 保存状态
            rule_statuses = _load_rule_statuses()
            rule_statuses[rule_id] = bool(enabled)
            _save_rule_statuses(rule_statuses)

            status_text = '启用' if enabled else '停用'
            return Response({
                'message': f'规则已{status_text}',
                'rule_id': rule_id,
                'enabled': bool(enabled),
                'success': True,
            })

        elif action == 'batch_toggle':
            # 批量切换多条规则的状态
            items = request.data.get('items', [])
            if not isinstance(items, list):
                return Response({
                    'error': 'items 应为数组格式: [{"rule_id": "xxx", "enabled": true}]',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)

            valid_ids = {r['id'] for r in _get_default_rules()}
            rule_statuses = _load_rule_statuses()
            updated = []
            for item in items:
                rid = item.get('rule_id', '')
                en = item.get('enabled')
                if rid and rid in valid_ids and en is not None:
                    rule_statuses[rid] = bool(en)
                    updated.append(rid)

            _save_rule_statuses(rule_statuses)
            return Response({
                'message': f'已批量更新 {len(updated)} 条规则状态',
                'updated_count': len(updated),
                'success': True,
            })

        else:
            return Response({
                'error': '未知操作，支持: toggle / batch_toggle',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)


# Apifox 内置默认豁免字段（不可删除）
_BUILTIN_EXEMPTIONS = {"scene_id", "template_id", "embd_id", "parser_id", "parent_id", "business_id", "category_id", "relation_template_id"}


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def apifox_check_exemptions(request):
    """管理 ID 字段豁免列表"""
    config = _load_config()
    exemptions = config.get('id_field_exemptions', [])

    if request.method == 'GET':
        return Response({
            'builtin': sorted(list(_BUILTIN_EXEMPTIONS)),
            'user_defined': exemptions,
            'all': sorted(list(_BUILTIN_EXEMPTIONS) + [e['field'] for e in exemptions if e.get('enabled')]),
            'success': True,
        })

    if request.method == 'POST':
        action = request.data.get('action', '')
        field = (request.data.get('field') or '').strip().lower()

        if not field and action not in ('delete',):
            return Response({
                'error': '请提供字段名(field)',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)

        # 禁止操作内置豁免字段
        if field in _BUILTIN_EXEMPTIONS:
            return Response({
                'error': f'「{field}」是内置豁免字段，不可操作',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)

        username = request.user.username if request.user.is_authenticated else 'unknown'
        now = datetime.now().isoformat()

        if action == 'add':
            # 检查是否已存在
            existing = next((e for e in exemptions if e['field'] == field), None)
            if existing:
                return Response({
                    'error': f'豁免字段「{field}」已存在',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)

            reason = (request.data.get('reason') or '').strip()
            new_item = {
                'field': field,
                'reason': reason,
                'added_by': username,
                'added_at': now,
                'enabled': True,
            }
            exemptions.append(new_item)
            config['id_field_exemptions'] = exemptions
            _save_config(config)
            return Response({
                'message': f'已添加豁免字段「{field}」',
                'item': new_item,
                'user_defined': exemptions,
                'success': True,
            })

        elif action == 'update_reason':
            existing = next((e for e in exemptions if e['field'] == field), None)
            if not existing:
                return Response({
                    'error': f'豁免字段「{field}」不存在',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
            existing['reason'] = (request.data.get('reason') or '').strip()
            config['id_field_exemptions'] = exemptions
            _save_config(config)
            return Response({
                'message': f'已更新豁免字段「{field}」的理由',
                'item': existing,
                'user_defined': exemptions,
                'success': True,
            })

        elif action == 'toggle':
            existing = next((e for e in exemptions if e['field'] == field), None)
            if not existing:
                return Response({
                    'error': f'豁免字段「{field}」不存在',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
            existing['enabled'] = not existing.get('enabled', True)
            config['id_field_exemptions'] = exemptions
            _save_config(config)
            new_status = '启用' if existing['enabled'] else '停用'
            return Response({
                'message': f'豁免字段「{field}」已{new_status}',
                'item': existing,
                'user_defined': exemptions,
                'success': True,
            })

        elif action == 'delete':
            # 支持按 field 删除或按 index 删除
            index = request.data.get('index')
            if index is not None and isinstance(index, int) and 0 <= index < len(exemptions):
                removed = exemptions.pop(index)
                config['id_field_exemptions'] = exemptions
                _save_config(config)
                return Response({
                    'message': f'已删除豁免字段「{removed["field"]}」',
                    'user_defined': exemptions,
                    'success': True,
                })
            elif field:
                existing = next((e for e in exemptions if e['field'] == field), None)
                if existing:
                    exemptions.remove(existing)
                    config['id_field_exemptions'] = exemptions
                    _save_config(config)
                    return Response({
                        'message': f'已删除豁免字段「{field}」',
                        'user_defined': exemptions,
                        'success': True,
                    })
            return Response({
                'error': f'豁免字段不存在',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'error': f'不支持的操作: {action}',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apifox_check_generate(request):
    """生成 Apifox 场景检查报告（异步）"""
    config = _load_config()
    project_id = request.data.get('project_id') or config.get('project_id', '')
    environment_id = request.data.get('environment_id') or config.get('environment_id', '')
    access_token = request.data.get('access_token') or ''
    # 如果前端传的是脱敏 token（包含 ****），使用配置文件中的完整 token
    if '****' in access_token:
        access_token = config.get('access_token', '')

    # 双重保险：如果配置文件中的 token 也是脱敏的，直接报错提示
    if '****' in access_token:
        return Response({
            'error': 'Access Token 无效（存储的是脱敏值），请先在「检查配置」中重新输入并保存完整的 Token',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)

    if not all([project_id, environment_id, access_token]):
        return Response({
            'error': '缺少必要参数：project_id, environment_id, access_token',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)

    # 校验 access_token 不是文件名等无效值
    if access_token.endswith('.html') or access_token.endswith('.json'):
        return Response({
            'error': '配置中的 Access Token 无效（可能被错误覆盖），请在「检查配置」中重新填写正确的 Apifox Access Token',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 确保目录存在
    _ensure_dirs()
    
    # 生成唯一任务ID和报告文件名
    task_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    executed_by = request.user.username if request.user.is_authenticated else 'unknown'
    report_filename = f'{executed_by}_Apifox_Check_{timestamp}.html'
    report_path = os.path.join(REPORTS_DIR, report_filename)

    # 获取用户自定义的豁免字段（仅启用状态的）
    all_exemptions = config.get('id_field_exemptions', [])
    id_field_exemptions = [e['field'] for e in all_exemptions if e.get('enabled', True)]
    # 内置豁免已在 rules.py 中默认包含，仅传递用户自定义项即可

    # 获取停用的规则 ID 列表（用于 --exclude 参数）
    rule_statuses = _load_rule_statuses()
    disabled_rule_ids = [rid for rid, enabled in rule_statuses.items() if not enabled]
    
    _task_status[task_id] = {
        'status': 'running',
        'progress': '正在生成原始报告...',
        'report_file': report_filename,
        'report_path': report_path,
        'created_at': datetime.now().isoformat(),
        'executed_by': executed_by,
        'error': None,
    }
    
    # 在后台线程中执行
    def generate_task():
        try:
            # Step 1: 生成原始报告
            _task_status[task_id]['progress'] = '正在从 Apifox 获取场景数据...'
            success, stdout, stderr = _run_apifox_check(
                project_id, environment_id, access_token, report_path,
                id_field_exemptions, disabled_rule_ids=disabled_rule_ids
            )
            if not success:
                _task_status[task_id]['status'] = 'failed'
                error_detail = stderr[:500] if stderr else '原始报告生成失败（无详细错误）'
                _task_status[task_id]['error'] = f'原始报告生成失败: {error_detail}'
                _save_report_meta(report_filename, {
                    'executed_by': executed_by,
                    'created_at': _task_status[task_id]['created_at'],
                    'status': 'failed',
                    'error': error_detail,
                })
                return
            
            # Step 2: 应用排除规则 + UI 注入
            _task_status[task_id]['progress'] = '正在应用排除规则和 UI 增强...'
            success, stdout, stderr = _run_apply_exclusions(report_path)
            if not success:
                _task_status[task_id]['status'] = 'failed'
                error_detail = stderr[:500] if stderr else '后处理失败（无详细错误）'
                _task_status[task_id]['error'] = f'后处理失败: {error_detail}'
                _save_report_meta(report_filename, {
                    'executed_by': executed_by,
                    'created_at': _task_status[task_id]['created_at'],
                    'status': 'failed',
                    'error': error_detail,
                })
                return

            # Step 2.5: 注入平台统一风格样式
            _task_status[task_id]['progress'] = '正在应用平台样式主题...'
            inject_ok, inject_msg = _inject_platform_styles(report_path)
            if not inject_ok:
                # 样式注入失败不阻塞，仅记录
                print(f'[ApifoxCheck] 平台样式注入失败: {inject_msg}')
            
            # Step 3: 验证
            _task_status[task_id]['progress'] = '正在验证排除规则...'
            verify_success, verify_stdout, verify_stderr = _run_verify_exclusions(report_path)
            
            _task_status[task_id]['status'] = 'completed'
            _task_status[task_id]['progress'] = '报告生成完成'
            _task_status[task_id]['verification'] = {
                'success': verify_success,
                'output': verify_stdout[:500],
            }
            # 持久化元数据
            _save_report_meta(report_filename, {
                'executed_by': executed_by,
                'created_at': _task_status[task_id]['created_at'],
            })
            
        except subprocess.TimeoutExpired:
            _task_status[task_id]['status'] = 'failed'
            _task_status[task_id]['error'] = '报告生成超时'
            _save_report_meta(report_filename, {
                'executed_by': executed_by,
                'created_at': _task_status[task_id]['created_at'],
                'status': 'failed',
                'error': '报告生成超时（超过300秒）',
            })
        except Exception as e:
            _task_status[task_id]['status'] = 'failed'
            error_msg = str(e)[:500]
            _task_status[task_id]['error'] = error_msg
            _save_report_meta(report_filename, {
                'executed_by': executed_by,
                'created_at': _task_status[task_id]['created_at'],
                'status': 'failed',
                'error': error_msg,
            })
    
    thread = threading.Thread(target=generate_task, daemon=True)
    thread.start()
    
    return Response({
        'task_id': task_id,
        'status': 'running',
        'message': '报告生成已启动',
        'success': True,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apifox_check_task_status(request, task_id):
    """查询报告生成任务状态"""
    if task_id not in _task_status:
        return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
    task = _task_status[task_id]
    return Response({
        'task_id': task_id,
        'status': task['status'],
        'progress': task['progress'],
        'report_file': task.get('report_file'),
        'error': task.get('error'),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apifox_check_reports(request):
    """获取历史报告列表"""
    _ensure_dirs()
    reports = []
    if os.path.exists(REPORTS_DIR):
        html_files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.html')]
        # 按文件修改时间（报告生成时间）倒序排列
        html_files.sort(key=lambda f: os.stat(os.path.join(REPORTS_DIR, f)).st_mtime, reverse=True)
        for f in html_files:
            filepath = os.path.join(REPORTS_DIR, f)
            stat = os.stat(filepath)
            meta = _load_report_meta(f)
            
            # 尝试从 JSON 文件中读取场景总数
            total_scenarios = None
            json_filename = f.replace('.html', '.json')
            json_filepath = os.path.join(REPORTS_DIR, json_filename)
            if os.path.exists(json_filepath):
                try:
                    with open(json_filepath, 'r', encoding='utf-8') as jf:
                        json_data = json.load(jf)
                        total_scenarios = json_data.get('total_scenarios')
                except Exception:
                    pass
            
            reports.append({
                    'filename': f,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'executed_by': meta.get('executed_by', ''),
                    'total_scenarios': total_scenarios,
                })
    return Response({'reports': reports})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apifox_check_report_detail(request, filename):
    """获取报告 HTML 内容"""
    filepath = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        raise Http404('报告文件不存在')

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    return HttpResponse(content, content_type='text/html; charset=utf-8')


# ============================================================
# Apifox 场景运行 - 通过 CLI 执行测试场景并生成运行报告
# ============================================================

def _run_apifox_scenario(access_token, project_id, scenario_id, environment_id,
                          output_dir, output_file, env_vars=None):
    """通过 apifox CLI 运行单个测试场景

    执行命令: apifox run --access-token <token> --project <pid> -t <sid> -e <eid>
                    -r cli,json --out-dir <dir> --out-file <name> --on-error continue
    使用 cli reporter 输出步骤详情到 stdout，json reporter 输出结构化数据到文件。
    env_vars: 本地环境变量字典，会通过 --env-var 参数传递给 CLI，
              解决 CLI 使用远程值而客户端使用本地值的差异问题。
    返回: (success, report_data, cli_stdout, error_message)
    """
    cmd_args = [
        'apifox', 'run',
        '--access-token', access_token,
        '--project', str(project_id),
        '-t', str(scenario_id),
        '-e', str(environment_id),
        '-r', 'cli,json',
        '--out-dir', output_dir,
        '--out-file', output_file,
        '--on-error', 'continue',
    ]

    # 添加本地环境变量到 CLI 参数，优先级高于远程值
    if env_vars and isinstance(env_vars, dict):
        for key, value in env_vars.items():
            # 处理 Apifox 变量可能的对象格式: {current_value: ..., initial_value: ...}
            if isinstance(value, dict):
                value = (value.get('current_value') or
                         value.get('currentValue') or
                         value.get('initial_value') or
                         value.get('initialValue') or
                         '')
            cmd_args.extend(['--env-var', f'{key}={value}'])

    result = subprocess.run(
        cmd_args,
        capture_output=True,
        text=True,
        timeout=600,  # 单场景10分钟超时
    )

    cli_stdout = result.stdout or ''

    # CLI 可能不会以非0退出码表示失败，查找生成的 JSON 报告文件
    json_file = os.path.join(output_dir, f'{output_file}.json')
    if not os.path.exists(json_file):
        # 尝试查找目录下最新的 json 文件
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        if json_files:
            json_file = os.path.join(output_dir, sorted(json_files)[-1])

    if not os.path.exists(json_file):
        error_msg = _extract_cli_error(result.stderr) if result.stderr else '未找到报告文件'
        return False, None, cli_stdout, f'CLI 运行失败: {error_msg}'

    with open(json_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)

    return True, report_data, cli_stdout, None


def _extract_url(url_val):
    """从 newman 格式的 URL 字段中提取可读的 URL 字符串"""
    if not url_val:
        return '-'
    if isinstance(url_val, str):
        return url_val
    if isinstance(url_val, dict):
        # 优先取 raw 字段
        raw = url_val.get('raw', '')
        if raw:
            return raw
        # 拼接 protocol://host/path
        protocol = url_val.get('protocol', 'https')
        host = url_val.get('host', [])
        if isinstance(host, list):
            host = '.'.join(host)
        path = url_val.get('path', [])
        if isinstance(path, list):
            path = '/'.join(path)
        url = f'{protocol}://{host}'
        if path:
            url += f'/{path}'
        query = url_val.get('query', [])
        if isinstance(query, list) and query:
            params = '&'.join(
                f"{q.get('key', '')}={q.get('value', '')}"
                for q in query if isinstance(q, dict)
            )
            if params:
                url += f'?{params}'
        return url
    return str(url_val)



def _parse_cli_stdout(stdout):
    """解析 apifox CLI 的 stdout 输出，提取每个步骤的执行详情

    CLI reporter 输出格式示例：
      ↳ 步骤名称
        POST https://example.com/api [200 OK, 1.75KB, 165.00ms]
        ✓  断言名称
        ✗  断言名称 (失败)

    返回: [{name, method, url, status_code, status_text, response_time, assertions: [{name, passed}]}]
    """
    if not stdout:
        return []

    steps = []
    current_step = None

    # 正则：步骤名 ↳ xxx
    step_re = re.compile(r'↳\s+(.+)')
    # 正则：请求行 METHOD URL [code status, size, time]
    req_re = re.compile(
        r'^\s*(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(.+?)\s+\[(\d+)\s+([^,]+),\s+[^,]+,\s+([\d.]+)ms\]'
    )
    # 正则：通过的断言 ✓
    pass_re = re.compile(r'^\s*✓\s+(.+)')
    # 正则：失败的断言 ✗
    fail_re = re.compile(r'^\s*✗\s+(.+)')

    for line in stdout.splitlines():
        # 匹配步骤名
        m = step_re.match(line)
        if m:
            if current_step:
                steps.append(current_step)
            current_step = {
                'name': m.group(1).strip(),
                'method': '-',
                'url': '-',
                'status_code': 0,
                'status_text': '',
                'response_time': 0,
                'assertions': [],
            }
            continue

        # 匹配请求行
        m = req_re.match(line)
        if m and current_step:
            current_step['method'] = m.group(1)
            current_step['url'] = m.group(2).strip()
            current_step['status_code'] = int(m.group(3))
            current_step['status_text'] = m.group(4).strip()
            current_step['response_time'] = float(m.group(5))
            continue

        # 匹配通过断言
        m = pass_re.match(line)
        if m and current_step:
            current_step['assertions'].append({
                'name': m.group(1).strip(),
                'passed': True,
                'error': '',
            })
            continue

        # 匹配失败断言
        m = fail_re.match(line)
        if m and current_step:
            current_step['assertions'].append({
                'name': m.group(1).strip(),
                'passed': False,
                'error': m.group(1).strip(),
            })
            continue

    if current_step:
        steps.append(current_step)

    return steps


def _parse_run_report(report_data, scenario_name='', cli_stdout=''):
    """解析 apifox CLI 生成的 JSON 报告 + stdout，提取关键指标和步骤详情

    JSON 报告提供汇总统计和场景定义（请求头/请求体），
    CLI stdout 提供每个步骤的执行结果（状态码/响应时间/断言）。
    """
    run_info = report_data.get('run', report_data)
    stats = run_info.get('stats', {})

    # 请求数据统计
    requests_stats = stats.get('requests', {})
    total_requests = requests_stats.get('total', 0)
    failed_requests = requests_stats.get('failed', 0)
    passed_requests = total_requests - failed_requests

    # 断言统计（apifox CLI 用 stats.assertions 而非 stats.tests）
    assertions_stats = stats.get('assertions', stats.get('tests', {}))
    total_assertions = assertions_stats.get('total', 0)
    failed_assertions = assertions_stats.get('failed', 0)
    passed_assertions = total_assertions - failed_assertions

    # 响应时间统计
    response_time = stats.get('responseTime', {})

    # 失败详情 - 提取可读的错误信息
    raw_failures = run_info.get('failures', [])
    failures = []
    for f in raw_failures[:30]:
        error = f.get('error', f) if isinstance(f, dict) else {}
        source = f.get('source', {}) if isinstance(f, dict) else {}
        failures.append({
            'step_name': source.get('name', '') if isinstance(source, dict) else '',
            'message': error.get('message', str(f)[:200]) if isinstance(error, dict) else str(f)[:200],
        })

    # 从 CLI stdout 解析每个步骤的执行结果（状态码/响应时间/断言）
    cli_steps = _parse_cli_stdout(cli_stdout)

    # 从 JSON collection 提取请求定义（请求头/请求体），按步骤名建立查找表
    collection = report_data.get('collection', {})
    col_items = collection.get('item', [])
    # collection.item[0] 通常是场景文件夹，里面的 item 才是实际步骤
    inner_items = []
    if col_items and isinstance(col_items[0], dict) and 'item' in col_items[0]:
        inner_items = col_items[0].get('item', [])
    elif col_items:
        inner_items = col_items

    # 按步骤名建立查找表
    col_lookup = {}
    for item in inner_items:
        if not isinstance(item, dict):
            continue
        name = item.get('name', '')
        if name:
            col_lookup[name] = item

    # 合并 CLI stdout 执行结果 + JSON collection 请求定义
    steps = []
    for cli_step in cli_steps:
        step_name = cli_step['name']
        col_item = col_lookup.get(step_name, {})

        # 从 collection 补充请求头和请求体
        req = col_item.get('request', {}) if isinstance(col_item, dict) else {}
        req_headers = req.get('header', []) if isinstance(req, dict) else []
        req_body = req.get('body', {}) if isinstance(req, dict) else {}
        req_body_str = ''
        if isinstance(req_body, dict):
            req_body_str = req_body.get('raw', req_body.get('content', ''))
            if not req_body_str:
                req_body_str = json.dumps(req_body, ensure_ascii=False)[:500] if req_body else ''
        elif isinstance(req_body, str):
            req_body_str = req_body[:500]

        # 断言
        assertions = cli_step.get('assertions', [])
        step_passed = len(assertions) == 0 or all(a['passed'] for a in assertions)
        # 如果没有断言但状态码 < 400，也算通过
        if not assertions and cli_step.get('status_code', 0):
            step_passed = cli_step['status_code'] < 400

        steps.append({
            'name': step_name,
            'method': cli_step['method'],
            'url': cli_step['url'],
            'status_code': cli_step['status_code'],
            'status_text': cli_step['status_text'],
            'response_time': cli_step['response_time'],
            'response_size': 0,
            'request_headers': req_headers[:20] if isinstance(req_headers, list) else [],
            'request_body': req_body_str,
            'response_body': '',
            'assertions': assertions,
            'passed': step_passed,
        })

    # 判断整体是否通过
    is_passed = failed_requests == 0 and failed_assertions == 0 and total_requests > 0

    # 优先使用显式传入的 scenario_name（来自数据库/API 查询，更可靠）
    # 仅在传入的是通用 fallback 名（如 "场景_8216859"）时，才尝试从 CLI 报告中取更友好的名称
    if scenario_name and not scenario_name.startswith('场景_'):
        final_name = scenario_name
    else:
        final_name = report_data.get('info', {}).get('name', scenario_name)

    return {
        'scenario_name': final_name,
        'is_passed': is_passed,
        'total_requests': total_requests,
        'passed_requests': passed_requests,
        'failed_requests': failed_requests,
        'total_assertions': total_assertions,
        'passed_assertions': passed_assertions,
        'failed_assertions': failed_assertions,
        'response_avg': response_time.get('average', 0),
        'response_min': response_time.get('min', 0),
        'response_max': response_time.get('max', 0),
        'failures': failures,
        'steps': steps,
    }


def _save_run_report_meta(report_filename, meta):
    """保存运行报告元数据"""
    os.makedirs(RUN_REPORTS_DIR, exist_ok=True)
    meta_file = os.path.join(RUN_REPORTS_DIR, report_filename + '.meta.json')
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def _load_run_report_meta(report_filename):
    """加载运行报告元数据"""
    meta_file = os.path.join(RUN_REPORTS_DIR, report_filename + '.meta.json')
    if os.path.exists(meta_file):
        with open(meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apifox_check_scenarios(request):
    """拉取 Apifox 项目中的场景列表"""
    config = _load_config()
    project_id = request.query_params.get('project_id') or config.get('project_id', '')
    environment_id = request.query_params.get('environment_id') or config.get('environment_id', '')
    access_token = request.query_params.get('access_token') or config.get('access_token', '')

    # 如果前端传的是脱敏 token，使用配置文件中的完整 token
    if '****' in access_token:
        access_token = config.get('access_token', '')

    if not all([project_id, environment_id, access_token]):
        return Response({
            'error': '缺少必要参数：project_id, environment_id, access_token，请先在「检查配置」中保存完整配置',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 复用已有的 fetcher
        from apifox_check.fetcher import fetch_all_scenarios

        scenarios = asyncio.run(
            fetch_all_scenarios(int(project_id), int(environment_id), access_token)
        )

        result = []
        for s in scenarios:
            result.append({
                'id': s.id,
                'name': s.name,
                'folder_path': s.folder_path,
                'folder_id': s.folder_id,
                'step_count': len(s.steps),
                'creator': s.creator,
                'created_at': s.created_at,
                'last_run_status': s.last_run_status,
                'has_pre_script': s.has_pre_script,
                'has_post_script': s.has_post_script,
            })

        return Response({
            'scenarios': result,
            'total': len(result),
            'success': True,
        })
    except Exception as e:
        return Response({
            'error': f'拉取场景列表失败: {str(e)[:500]}',
            'success': False,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_or_create_apifox_test_suite(user, suite_name='Apifox场景运行'):
    """获取或创建 Apifox 场景运行专用的项目和测试套件

    用于将 Apifox 运行结果接入平台统一的 TestExecution 报告系统。
    suite_name 可传入实际运行的场景名，使报告标题更有辨识度。
    """
    project, _ = ApiProject.objects.get_or_create(
        name='Apifox场景运行',
        defaults={
            'description': 'Apifox CLI 运行场景自动生成的项目',
            'project_type': 'HTTP',
            'status': 'IN_PROGRESS',
            'owner': user,
        }
    )
    suite, _ = TestSuite.objects.get_or_create(
        project=project,
        name=suite_name,
        defaults={
            'description': '通过 Apifox CLI 运行的场景集合',
            'created_by': user,
        }
    )
    return suite


def _convert_results_for_test_execution(all_results):
    """将 Apifox 运行结果转换为 TestExecution.results 所需的扁平列表格式

    返回的每个元素包含平台统一报告系统所需的字段：
      - name: 请求名称（含场景名前缀）
      - passed: 是否通过
      - method: HTTP 方法
      - url: 请求 URL
      - status_code: HTTP 状态码
      - response_time: 响应时间（毫秒）
      - error: 错误信息
      - assertions_results: 断言结果列表 [{name, passed, error}]
      - request_data: 请求数据 {headers, body}
      - response_data: 响应数据 {body}
    """
    flat_results = []
    for scenario in all_results:
        scenario_name = scenario.get('scenario_name', '未知场景')
        steps = scenario.get('steps', [])
        if not steps:
            # 如果没有步骤详情，至少生成一条汇总记录
            flat_results.append({
                'name': f'{scenario_name}（运行{"失败" if not scenario.get("is_passed") else "通过"}）',
                'passed': scenario.get('is_passed', False),
                'method': '-',
                'url': '-',
                'status_code': None,
                'response_time': None,
                'error': scenario.get('error', ''),
                'assertions_results': [],
            })
            continue
        for step in steps:
            # 提取断言信息
            raw_assertions = step.get('assertions', [])
            assertions_results = []
            if isinstance(raw_assertions, list):
                for a in raw_assertions:
                    if not isinstance(a, dict):
                        continue
                    assertions_results.append({
                        'name': a.get('name', '未命令断言'),
                        'passed': a.get('passed', False),
                        'error': a.get('error', ''),
                    })

            # 提取错误信息
            error_msg = ''
            if not step.get('passed'):
                failed_assertions = [a for a in assertions_results if not a.get('passed')]
                if failed_assertions:
                    error_msg = '; '.join(
                        a.get('error') or a.get('name', '') for a in failed_assertions[:3]
                    )
                elif step.get('status_code') and step['status_code'] >= 400:
                    error_msg = f'HTTP {step["status_code"]}'

            # 请求数据
            req_headers = step.get('request_headers', [])
            req_body = step.get('request_body', '')

            # 响应数据
            resp_body = step.get('response_body', '')

            flat_results.append({
                'name': f'{scenario_name} - {step.get("name", "未命名步骤")}',
                'passed': step.get('passed', False),
                'method': step.get('method', '-'),
                'url': step.get('url', '-'),
                'status_code': step.get('status_code', None),
                'response_time': step.get('response_time', None),
                'error': error_msg,
                'assertions_results': assertions_results,
                'request_data': {
                    'method': step.get('method', '-'),
                    'url': step.get('url', '-'),
                    'headers': req_headers if isinstance(req_headers, list) else [],
                    'body': req_body,
                },
                'response_data': {
                    'status_code': step.get('status_code', None),
                    'body': resp_body,
                },
            })
    return flat_results


def _create_test_execution_for_apifox_run(all_results, summary, user, start_time_iso=None, start_time_dt=None, end_time_dt=None):
    """为 Apifox 运行结果创建 TestExecution 记录

    将运行结果写入平台的统一报告系统 (TestExecution)，
    使其出现在 /api-testing/reports 页面中，支持生成 Allure 报告。

    支持两种时间传法：
    - start_time_dt + end_time_dt: 直接传 datetime 对象（推荐，精确控制执行时长）
    - start_time_iso: ISO 格式字符串，end_time 使用当前时间（兼容旧调用）
    """
    from django.db import connection
    # 关闭旧连接，避免线程中数据库连接问题
    connection.close()

    # 从运行结果中提取场景名，构建有辨识度的 suite 名称
    scenario_names = [r.get('scenario_name', '') for r in all_results if r.get('scenario_name')]
    if scenario_names:
        # 最多显示 3 个场景名，超出用省略号
        if len(scenario_names) <= 3:
            suite_name = f'Apifox场景运行_{"、".join(scenario_names)}'
        else:
            suite_name = f'Apifox场景运行_{"、".join(scenario_names[:3])}等{len(scenario_names)}个场景'
    else:
        suite_name = 'Apifox场景运行'

    suite = _get_or_create_apifox_test_suite(user, suite_name=suite_name)

    total_requests = summary.get('total_requests', 0)
    passed_requests = summary.get('passed_requests', 0)
    failed_requests = summary.get('failed_requests', 0)
    is_all_passed = failed_requests == 0 and total_requests > 0

    # 转换为 TestExecution.results 所需格式
    results_list = _convert_results_for_test_execution(all_results)

    # 支持两种方式传入时间
    start_dt = None
    end_dt = None
    if start_time_dt is not None and end_time_dt is not None:
        start_dt = start_time_dt
        end_dt = end_time_dt
    elif start_time_iso:
        try:
            from datetime import datetime as dt
            start_dt = dt.fromisoformat(start_time_iso)
            end_dt = dt.now()
        except (ValueError, TypeError):
            pass

    execution = TestExecution.objects.create(
        test_suite=suite,
        status='COMPLETED' if is_all_passed else 'FAILED',
        start_time=start_dt,
        end_time=end_dt,
        total_requests=total_requests,
        passed_requests=passed_requests,
        failed_requests=failed_requests,
        results=results_list,
        executed_by=user,
    )
    return execution


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apifox_check_run(request):
    """触发运行 Apifox 测试场景（异步）

    请求参数:
      - scenario_ids: 场景ID列表 [int]
      - project_id: Apifox 项目ID
      - environment_id: 环境ID (Apifox 远程环境ID)
      - access_token: Apifox Access Token
      - local_environment_id: 本地环境ID (可选，用于传递本地变量给 CLI)
    """
    config = _load_config()
    project_id = request.data.get('project_id') or config.get('project_id', '')
    environment_id = request.data.get('environment_id') or config.get('environment_id', '')
    access_token = request.data.get('access_token') or ''
    scenario_ids = request.data.get('scenario_ids', [])
    # 优先使用前端传递的 local_environment_id，否则使用配置中的
    local_environment_id = request.data.get('local_environment_id') or config.get('local_environment_id')

    # 如果前端传的是脱敏 token，使用配置文件中的完整 token
    if '****' in access_token:
        access_token = config.get('access_token', '')

    if not all([project_id, environment_id, access_token]):
        return Response({
            'error': '缺少必要参数：project_id, environment_id, access_token',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)

    if not scenario_ids or not isinstance(scenario_ids, list):
        return Response({
            'error': '请选择至少一个场景',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)

    # 获取本地环境变量（如果指定了 local_environment_id）
    local_env_vars = {}
    if local_environment_id:
        try:
            local_env = Environment.objects.get(id=local_environment_id)
            local_env_vars = local_env.variables or {}
        except Environment.DoesNotExist:
            pass

    # 确保目录存在
    os.makedirs(RUN_REPORTS_DIR, exist_ok=True)

    # 生成任务ID
    task_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    user_obj = request.user if request.user.is_authenticated else None
    executed_by = user_obj.username if user_obj else 'unknown'

    # 保存配置（如果有完整 token）
    if access_token and '****' not in access_token:
        config['project_id'] = project_id
        config['environment_id'] = environment_id
        config['access_token'] = access_token
        if local_environment_id:
            config['local_environment_id'] = local_environment_id
        _save_config(config)

    _run_task_status[task_id] = {
        'status': 'running',
        'progress': f'准备运行 {len(scenario_ids)} 个场景...',
        'total': len(scenario_ids),
        'completed': 0,
        'current_scenario_id': None,
        'current_scenario_name': '',
        'results': [],
        'report_file': f'{executed_by}_Apifox_Run_{timestamp}.json',
        'created_at': datetime.now().isoformat(),
        'executed_by': executed_by,
        'error': None,
    }

    # 查询场景名称（用于进度显示）
    scenario_names = {}
    try:
        from apifox_check.fetcher import fetch_all_scenarios

        all_scenarios = asyncio.run(
            fetch_all_scenarios(int(project_id), int(environment_id), access_token)
        )
        scenario_names = {s.id: s.name for s in all_scenarios}
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).warning(f"获取场景名称失败 (project={project_id}, env={environment_id}): {e}")

    # 在后台线程中执行
    def run_task():
        all_results = []
        report_data = {
            'info': {
                'executed_by': executed_by,
                'created_at': _run_task_status[task_id]['created_at'],
                'project_id': project_id,
                'environment_id': environment_id,
            },
            'scenarios': [],
        }

        for idx, sid in enumerate(scenario_ids):
            scenario_name = scenario_names.get(sid, f'场景_{sid}')
            _run_task_status[task_id]['current_scenario_id'] = sid
            _run_task_status[task_id]['current_scenario_name'] = scenario_name
            _run_task_status[task_id]['progress'] = (
                f'正在运行 [{idx + 1}/{len(scenario_ids)}] {scenario_name}...'
            )

            # 创建临时输出目录
            temp_dir = tempfile.mkdtemp(prefix='apifox_run_')
            output_file = f'scenario_{sid}'

            try:
                success, report, cli_stdout, error = _run_apifox_scenario(
                    access_token, project_id, sid, environment_id,
                    temp_dir, output_file, env_vars=local_env_vars
                )

                if success and report:
                    parsed = _parse_run_report(report, scenario_name, cli_stdout)
                    parsed['scenario_id'] = sid
                    all_results.append(parsed)
                    report_data['scenarios'].append(parsed)
                else:
                    failed_result = {
                        'scenario_id': sid,
                        'scenario_name': scenario_name,
                        'is_passed': False,
                        'error': error or '运行失败',
                        'total_requests': 0,
                        'passed_requests': 0,
                        'failed_requests': 0,
                    }
                    all_results.append(failed_result)
                    report_data['scenarios'].append(failed_result)

            except subprocess.TimeoutExpired:
                failed_result = {
                    'scenario_id': sid,
                    'scenario_name': scenario_name,
                    'is_passed': False,
                    'error': '场景运行超时（超过600秒）',
                    'total_requests': 0,
                    'passed_requests': 0,
                    'failed_requests': 0,
                }
                all_results.append(failed_result)
                report_data['scenarios'].append(failed_result)
            except Exception as e:
                failed_result = {
                    'scenario_id': sid,
                    'scenario_name': scenario_name,
                    'is_passed': False,
                    'error': str(e)[:300],
                    'total_requests': 0,
                    'passed_requests': 0,
                    'failed_requests': 0,
                }
                all_results.append(failed_result)
                report_data['scenarios'].append(failed_result)
            finally:
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)

            _run_task_status[task_id]['completed'] = idx + 1
            _run_task_status[task_id]['results'] = all_results

        # 生成汇总
        report_data['summary'] = {
            'total_scenarios': len(scenario_ids),
            'passed_scenarios': sum(1 for r in all_results if r.get('is_passed')),
            'failed_scenarios': sum(1 for r in all_results if not r.get('is_passed')),
            'total_requests': sum(r.get('total_requests', 0) for r in all_results),
            'passed_requests': sum(r.get('passed_requests', 0) for r in all_results),
            'failed_requests': sum(r.get('failed_requests', 0) for r in all_results),
        }

        # 保存合并报告
        report_filename = _run_task_status[task_id]['report_file']
        report_path = os.path.join(RUN_REPORTS_DIR, report_filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        # 保存元数据
        _save_run_report_meta(report_filename, {
            'executed_by': executed_by,
            'created_at': _run_task_status[task_id]['created_at'],
            'summary': report_data['summary'],
        })

        # 将运行结果写入平台统一报告系统 (TestExecution)
        test_execution_id = None
        if user_obj:
            try:
                execution = _create_test_execution_for_apifox_run(
                    all_results=all_results,
                    summary=report_data['summary'],
                    user=user_obj,
                    start_time_iso=_run_task_status[task_id]['created_at'],
                )
                test_execution_id = execution.id
            except Exception as e:
                # 写入 TestExecution 失败不影响运行报告本身
                print(f'[Apifox Run] 创建 TestExecution 失败: {e}')

        _run_task_status[task_id]['status'] = 'completed'
        _run_task_status[task_id]['test_execution_id'] = test_execution_id
        _run_task_status[task_id]['progress'] = (
            f'运行完成：{report_data["summary"]["passed_scenarios"]} 通过，'
            f'{report_data["summary"]["failed_scenarios"]} 失败'
        )

    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()

    return Response({
        'task_id': task_id,
        'status': 'running',
        'message': f'已启动 {len(scenario_ids)} 个场景的运行',
        'success': True,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apifox_check_run_status(request, task_id):
    """查询运行任务状态"""
    if task_id not in _run_task_status:
        return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
    task = _run_task_status[task_id]
    return Response({
        'task_id': task_id,
        'status': task['status'],
        'progress': task['progress'],
        'total': task.get('total'),
        'completed': task.get('completed'),
        'current_scenario_name': task.get('current_scenario_name'),
        'results': task.get('results', []),
        'report_file': task.get('report_file'),
        'test_execution_id': task.get('test_execution_id'),
        'error': task.get('error'),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apifox_check_run_reports(request):
    """获取运行报告列表"""
    os.makedirs(RUN_REPORTS_DIR, exist_ok=True)
    reports = []
    if os.path.exists(RUN_REPORTS_DIR):
        json_files = [
            f for f in os.listdir(RUN_REPORTS_DIR)
            if f.endswith('.json') and not f.endswith('.meta.json')
        ]
        json_files.sort(
            key=lambda f: os.stat(os.path.join(RUN_REPORTS_DIR, f)).st_mtime,
            reverse=True
        )
        for f in json_files:
            filepath = os.path.join(RUN_REPORTS_DIR, f)
            stat = os.stat(filepath)
            meta = _load_run_report_meta(f)
            summary = meta.get('summary', {})
            reports.append({
                'filename': f,
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'executed_by': meta.get('executed_by', ''),
                'total_scenarios': summary.get('total_scenarios', 0),
                'passed_scenarios': summary.get('passed_scenarios', 0),
                'failed_scenarios': summary.get('failed_scenarios', 0),
            })
    return Response({'reports': reports})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apifox_check_run_report_detail(request, filename):
    """获取运行报告JSON数据"""
    filepath = os.path.join(RUN_REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        raise Http404('报告文件不存在')
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return Response(data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def apifox_check_run_report_delete(request, filename):
    """删除运行报告"""
    filepath = os.path.join(RUN_REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        return Response({'error': '报告文件不存在'}, status=status.HTTP_404_NOT_FOUND)
    os.remove(filepath)
    meta_file = os.path.join(RUN_REPORTS_DIR, filename + '.meta.json')
    if os.path.exists(meta_file):
        os.remove(meta_file)
    return Response({'success': True, 'message': '报告已删除'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def apifox_check_report_delete(request, filename):
    """删除报告"""
    filepath = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        return Response({'error': '报告文件不存在'}, status=status.HTTP_404_NOT_FOUND)
    os.remove(filepath)
    # 同时删除元数据文件
    meta_file = os.path.join(REPORTS_DIR, filename + '.meta.json')
    if os.path.exists(meta_file):
        os.remove(meta_file)
    # 同时删除JSON文件
    json_file = os.path.join(REPORTS_DIR, filename.replace('.html', '.json'))
    if os.path.exists(json_file):
        os.remove(json_file)
    return Response({'success': True, 'message': '报告已删除'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apifox_check_report_json(request, filename):
    """获取报告JSON数据（用于Vue前端渲染）"""
    # 首先尝试查找对应的JSON文件
    json_filename = filename.replace('.html', '.json')
    json_filepath = os.path.join(REPORTS_DIR, json_filename)
    
    # 如果JSON文件存在，直接返回
    if os.path.exists(json_filepath):
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Response(data)
    
    # 如果JSON文件不存在，但HTML文件存在，返回错误提示
    html_filepath = os.path.join(REPORTS_DIR, filename)
    if os.path.exists(html_filepath):
        return Response(
            {'error': '该报告没有JSON格式数据，请重新生成报告'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    raise Http404('报告文件不存在')
