"""Verify exclusion rules were correctly applied to apifox-check HTML report.

Checks:
1. Scenarios with "前置"/"后置" in name that are compliant → should have is_violation=false
2. Scenarios starting with "不算入统计" that are compliant → should have is_violation=false

Usage:
    python verify_exclusions.py <path/to/report.html>
"""

import re
import json
import sys
import os


def load_html(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def verify_exclusions(html):
    """Verify that excluded scenarios have is_violation=false in scenario-meta."""
    issues = []

    for idx in range(6):
        m = re.search(
            r'<script id="scenario-meta-' + str(idx) + r'"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if not m:
            continue

        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            issues.append(f"meta-{idx}: Cannot parse JSON")
            continue

        fixture_compliant = []
        exclude_compliant = []
        still_violating = []

        for item in data:
            name = item.get('name', '')
            folder = item.get('folder', '')
            is_violation = item.get('is_violation', False)

            # Check: name contains "前置"/"后置" and is NOT violating → should be excluded
            if ('前置' in name or '后置' in name):
                if not is_violation:
                    fixture_compliant.append(
                        f"  {item.get('id')}|{name}|{folder}"
                    )
                else:
                    still_violating.append(
                        f"  {item.get('id')}|{name}|{folder} (is_violation=true - BUG!)"
                    )

            # Check: name starts with "不算入统计" and is NOT violating → should be excluded
            if name.startswith('不算入统计'):
                if not is_violation:
                    exclude_compliant.append(
                        f"  {item.get('id')}|{name}|{folder}"
                    )
                else:
                    still_violating.append(
                        f"  {item.get('id')}|{name}|{folder} (is_violation=true - BUG!)"
                    )

        if still_violating:
            issues.append(f"meta-{idx}: {len(still_violating)} scenarios NOT excluded:")
            for sv in still_violating:
                issues.append(sv)

        if fixture_compliant:
            print(f"meta-{idx}: {len(fixture_compliant)} fixture-skip (前置/后置) scenarios correctly excluded:")
            for fc in fixture_compliant:
                print(fc)

        if exclude_compliant:
            print(f"meta-{idx}: {len(exclude_compliant)} exclude (不算入统计) scenarios correctly excluded:")
            for ec in exclude_compliant:
                print(ec)

    if issues:
        print("\n=== ISSUES FOUND ===")
        for issue in issues:
            print(issue)
        return 1
    else:
        print("\n=== All exclusions verified OK ===")
        return 0


def main():
    if len(sys.argv) < 2:
        report_path = 'apifox-check-report.html'
        if not os.path.exists(report_path):
            print('Usage: python verify_exclusions.py <path/to/report.html>')
            sys.exit(1)
    else:
        report_path = sys.argv[1]

    print(f'Verifying: {report_path}\n')
    html = load_html(report_path)
    result = verify_exclusions(html)
    sys.exit(result)


if __name__ == '__main__':
    main()
