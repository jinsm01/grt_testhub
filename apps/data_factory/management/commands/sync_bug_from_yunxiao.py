"""
定时反向同步云效 Bug 状态到本地

用法:
    python manage.py sync_bug_from_yunxiao [--token TOKEN] [--org ORG_ID] [--space SPACE_ID] [--all]

示例 (配合 cron 定时任务):
    # 每 5 分钟同步一次
    */5 * * * * cd /path/to/project && python manage.py sync_bug_from_yunxiao --token=xxx --org=xxx >> /var/log/sync_bug.log 2>&1
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '定时从云效反向同步 Bug 状态到本地'

    def add_arguments(self, parser):
        parser.add_argument('--token', type=str, required=True,
                            help='云效个人访问令牌')
        parser.add_argument('--org', type=str, default='',
                            help='云效组织 ID (中心版必填)')
        parser.add_argument('--space', type=str, default='',
                            help='项目 ID (可选，仅同步指定项目)')
        parser.add_argument('--all', action='store_true',
                            help='同步所有已同步的 Bug (默认最多100条)')
        parser.add_argument('--domain', type=str, default='',
                            help='API 域名 (可选)')
        parser.add_argument('--dry-run', action='store_true',
                            help='试运行模式，不实际保存')

    def handle(self, *args, **options):
        token = options['token']
        org_id = options.get('org', '')
        space_id = options.get('space', '')
        domain = options.get('domain', '')
        dry_run = options.get('dry_run', False)
        sync_all = options.get('all', False)

        self.stdout.write(f'[{timezone.now()}] 开始反向同步云效 Bug 状态...')

        try:
            from apps.data_factory.models import BugSyncItem
            from apps.data_factory.yunxiao_client import YunxiaoClient, YunxiaoAPIError

            # 获取需要同步的记录
            queryset = BugSyncItem.objects.exclude(yunxiao_workitem_id='')
            if space_id:
                queryset = queryset.filter(local_data__space_id=space_id)

            if not sync_all:
                queryset = queryset.order_by('-updated_at')[:100]

            sync_items = list(queryset)
            self.stdout.write(f'  待检查同步项: {len(sync_items)}')

            if not sync_items:
                self.stdout.write('  没有需要同步的 Bug')
                return

            client_kwargs = {"token": token}
            if org_id:
                client_kwargs["organization_id"] = org_id
            if domain:
                client_kwargs["domain"] = domain
            client = YunxiaoClient(**client_kwargs)

            updated_count = 0
            error_count = 0
            unchanged_count = 0

            for item in sync_items:
                try:
                    remote_data = client.get_workitem(item.yunxiao_workitem_id)
                    if not remote_data or isinstance(remote_data, list):
                        remote_data = remote_data[0] if isinstance(remote_data, list) and remote_data else {}

                    remote_status = ""
                    remote_subject = ""
                    if isinstance(remote_data, dict):
                        remote_status = str(remote_data.get("status", "") or "")
                        remote_subject = str(remote_data.get("subject", "") or "")

                    local_data = item.local_data or {}
                    local_status = str(local_data.get("status", "") or "")

                    changed = False
                    if remote_status and remote_status != local_status:
                        local_data['status'] = remote_status
                        changed = True
                        self.stdout.write(f'  [状态变更] {item.yunxiao_workitem_id}: {local_status} -> {remote_status}')

                    if remote_subject and remote_subject != local_data.get('title', ''):
                        local_data['title'] = remote_subject
                        changed = True

                    if changed:
                        if not dry_run:
                            item.local_data = local_data
                            item.remote_data_cache = remote_data
                            item.sync_status = 'synced'
                            item.last_synced_at = timezone.now()
                            item.last_remote_check_at = timezone.now()
                            item.save()
                        updated_count += 1
                    else:
                        if not dry_run:
                            item.last_remote_check_at = timezone.now()
                            item.remote_data_cache = remote_data
                            item.save(update_fields=['last_remote_check_at', 'remote_data_cache'])
                        unchanged_count += 1

                except YunxiaoAPIError as e:
                    error_count += 1
                    self.stderr.write(f'  [API错误] workitem_id={item.yunxiao_workitem_id}: {e}')
                except Exception as e:
                    error_count += 1
                    self.stderr.write(f'  [异常] workitem_id={item.yunxiao_workitem_id}: {e}')

            mode = " (DRY-RUN)" if dry_run else ""
            self.stdout.write(
                f'[{timezone.now()}] 同步完成{mode}: '
                f'共{len(sync_items)}项, 更新{updated_count}项, '
                f'无变更{unchanged_count}项, 错误{error_count}项'
            )
            logger.info(
                f'[sync_bug_from_yunxiao] 完成: total={len(sync_items)}, '
                f'updated={updated_count}, unchanged={unchanged_count}, errors={error_count}'
            )

        except Exception as e:
            self.stderr.write(f'同步失败: {e}')
            logger.error(f'[sync_bug_from_yunxiao] 失败: {e}', exc_info=True)
            raise
