"""
Apifox 自动化场景检查 - 后端视图
提供配置管理、报告生成、报告查阅接口
"""
import os
import re
import json
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

APPLY_EXCLUSIONS_SCRIPT = os.path.join(SKILL_SCRIPTS_DIR, 'apply_exclusions.py')
VERIFY_EXCLUSIONS_SCRIPT = os.path.join(SKILL_SCRIPTS_DIR, 'verify_exclusions.py')

# 生成任务状态存储 (内存中)
_task_status = {}


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


def _run_apifox_check(project_id, environment_id, access_token, output_path, id_field_exemptions=None):
    """运行 apifox-check CLI 生成原始报告"""
    # 构建 Python 命令，添加第三方包路径
    python_cmd = f'"{PYTHON_EXE}"'

    # 构建 --id-exemptions 参数
    exemptions_arg = ''
    if id_field_exemptions:
        exemptions_str = ','.join(id_field_exemptions)
        exemptions_arg = f", '--id-exemptions', '{exemptions_str}'"
    
    # 检查第三方包目录是否存在
    if os.path.exists(APIFOX_CHECK_DIR):
        # 使用第三方目录中的 apifox_check
        python_cmd += f' -c "import sys; sys.path.insert(0, \'{THIRD_PARTY_DIR}\'); from apifox_check.cli import main; import sys; sys.argv = [\'apifox-check\', \'--project-id\', \'{project_id}\', \'--environment-id\', \'{environment_id}\', \'--access-token\', \'{access_token}\'{exemptions_arg}, \'--output\', r\'{output_path}\']; main(); print(\'DONE\')"'
    else:
        # 尝试从已安装的包中导入
        python_cmd += f' -c "from apifox_check.cli import main; import sys; sys.argv = [\'apifox-check\', \'--project-id\', \'{project_id}\', \'--environment-id\', \'{environment_id}\', \'--access-token\', \'{access_token}\'{exemptions_arg}, \'--output\', r\'{output_path}\']; main(); print(\'DONE\')"'
    
    result = subprocess.run(python_cmd, shell=True, capture_output=True, text=True, timeout=300)
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
        })
    
    elif request.method == 'POST':
        config = _load_config()
        data = request.data
        if 'project_id' in data:
            config['project_id'] = data['project_id']
        if 'environment_id' in data:
            config['environment_id'] = data['environment_id']
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
                project_id, environment_id, access_token, report_path, id_field_exemptions
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
        for f in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if f.endswith('.html'):
                filepath = os.path.join(REPORTS_DIR, f)
                stat = os.stat(filepath)
                meta = _load_report_meta(f)
                reports.append({
                    'filename': f,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'executed_by': meta.get('executed_by', ''),
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
    return Response({'success': True, 'message': '报告已删除'})
