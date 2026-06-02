"""CLI entry point for apifox-check."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime

from .checker import init_user_config, load_config, run_checks
from .fetcher import fetch_all_scenarios, read_token_from_config
from .models import ReportData
from .reporter import generate_html_report, write_report


def parse_args():
    parser = argparse.ArgumentParser(
        prog="apifox-check",
        description="Apifox接口自动化编写规范检查工具",
    )
    parser.add_argument("--project-id", type=int, help="Apifox项目ID")
    parser.add_argument("--environment-id", type=int, help="Apifox环境ID")
    parser.add_argument("--access-token", type=str, help="Apifox访问令牌(优先从~/.apifox/config.toml读取)")
    parser.add_argument("--config", type=str, help="自定义YAML规则配置文件路径")
    parser.add_argument("--output", type=str, default="./apifox-check-report.html", help="报告输出路径(默认: ./apifox-check-report.html)")
    parser.add_argument("--format", choices=["html", "json", "text"], default="html", help="输出格式(默认: html)")
    parser.add_argument("--rules", type=str, help="仅运行指定规则ID(逗号分隔, 如: env-switching,assertions-after-request)")
    parser.add_argument("--exclude", type=str, help="排除指定规则ID(逗号分隔, 如: folder-structure)")
    parser.add_argument("--verbose", action="store_true", help="详细输出进度信息")
    parser.add_argument("--list-rules", action="store_true", help="列出所有可用规则并退出")
    parser.add_argument("--init-config", action="store_true", help="生成默认规则配置文件到~/.apifox-check/rules.yaml")
    return parser.parse_args()


async def main_async():
    args = parse_args()

    # Special commands first
    if args.init_config:
        path = init_user_config()
        print(f"默认配置文件已生成: {path}")
        print("编辑该文件可自定义规则参数、启用/禁用规则、调整阈值。")
        return

    config = load_config(args.config)

    if args.list_rules:
        print("\n可用检查规则列表:")
        print("-" * 80)
        for rule in config.rules:
            status = "启用" if rule.enabled else "禁用"
            print(f"  {rule.id:25s} | {rule.name:20s} | 严重性: {rule.severity:6s} | {status}")
        print("-" * 80)
        print(f"共 {len(config.rules)} 条规则")
        return

    # Resolve project info
    project_id = args.project_id or config.project_id
    environment_id = args.environment_id or config.environment_id
    access_token = args.access_token or config.access_token or read_token_from_config()

    if not project_id:
        print("错误: 请提供项目ID (--project-id 或在配置文件中设置)")
        sys.exit(1)
    if not environment_id:
        print("错误: 请提供环境ID (--environment-id 或在配置文件中设置)")
        sys.exit(1)
    if not access_token:
        print("错误: 请提供访问令牌 (--access-token, 环境变量APIFOX_ACCESS_TOKEN, 或~/.apifox/config.toml)")
        sys.exit(1)

    # Parse rule filters
    rule_ids = args.rules.split(",") if args.rules else None
    exclude_ids = args.exclude.split(",") if args.exclude else None

    # Step 1: Fetch data
    if args.verbose:
        print(f"正在从Apifox获取项目 {project_id} 的测试场景数据...")

    scenarios = await fetch_all_scenarios(int(project_id), int(environment_id) if environment_id else None, access_token)

    if args.verbose:
        print(f"获取完成: {len(scenarios)} 个场景")

    # Step 2: Run checks
    if args.verbose:
        print("正在执行规则检查...")

    rule_results = run_checks(scenarios, config, rule_ids, exclude_ids)

    if args.verbose:
        for rr in rule_results:
            print(f"  {rr.rule.id}: 合规率 {rr.compliance_rate}% (通过{rr.passed_count}/失败{rr.failed_count})")

    # Step 3: Generate report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_data = ReportData(
        project_id=int(project_id),
        environment_id=int(environment_id) if environment_id else 0,
        total_scenarios=len(scenarios),
        total_rules_checked=len(rule_results),
        rule_results=rule_results,
        timestamp=timestamp,
    )

    if args.format == "html":
        html = generate_html_report(report_data, config, scenarios)
        output_path = write_report(html, args.output)
        print(f"\nHTML报告已生成: {output_path}")

    elif args.format == "json":
        report_dict = {
            "project_id": report_data.project_id,
            "environment_id": report_data.environment_id,
            "total_scenarios": report_data.total_scenarios,
            "timestamp": report_data.timestamp,
            "rules": [
                {
                    "id": rr.rule.id,
                    "name": rr.rule.name,
                    "severity": rr.rule.severity,
                    "compliance_rate": rr.compliance_rate,
                    "passed": rr.passed_count,
                    "failed": rr.failed_count,
                    "violations": [
                        {
                            "scenario_id": r.scenario_id,
                            "scenario_name": r.scenario_name,
                            "message": r.message,
                            "details": r.details,
                        }
                        for r in rr.results if not r.passed
                    ],
                }
                for rr in report_data.rule_results
            ],
        }
        with open(args.output.replace(".html", ".json"), "w", encoding="utf-8") as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        print(f"\n✅ JSON报告已生成: {args.output.replace('.html', '.json')}")

    elif args.format == "text":
        print(f"\n{'='*60}")
        print(f"Apifox接口自动化检查结果 - 项目 {project_id}")
        print(f"{'='*60}")
        print(f"场景总数: {len(scenarios)} | 检查规则: {len(rule_results)} | 时间: {timestamp}")
        print(f"{'='*60}")
        for rr in rule_results:
            sev_icon = {"high": "🔴", "mid": "🟡", "low": "🟢", "skip": "⏭️"}[rr.rule.severity]
            print(f"\n{sev_icon} {rr.rule.name} ({rr.rule.id})")
            print(f"   合规率: {rr.compliance_rate}% | 通过: {rr.passed_count} | 失败: {rr.failed_count}")
            if rr.failed_count > 0:
                for r in rr.results[:5]:
                    if not r.passed:
                        print(f"   ⚠️ {r.scenario_name or '总体'}: {r.message}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()