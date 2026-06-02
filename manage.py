#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # 添加项目根目录到 sys.path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # 强制设置 DJANGO_SETTINGS_MODULE，不使用 setdefault
    os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()