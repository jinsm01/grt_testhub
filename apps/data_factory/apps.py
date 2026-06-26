from django.apps import AppConfig


class DataFactoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_factory'
    verbose_name = '数据工厂'

    def ready(self):
        """Django 启动时检查并恢复被中断的 AI 分析任务"""
        import threading
        import time
        import logging

        logger = logging.getLogger(__name__)

        def _check_and_recover():
            # 延迟 15 秒，避免启动时数据库连接未就绪
            time.sleep(15)
            try:
                from .models import BugAnalysisRecord
                from .bug_analysis_view import _recover_ai_analysis

                # 查找状态为 running 的记录（可能被中断的）
                running_records = BugAnalysisRecord.objects.filter(ai_status='running')
                if running_records.exists():
                    logger.info(f"[AI Recovery] 发现 {running_records.count()} 个被中断的AI分析任务，准备恢复...")
                    for record in running_records:
                        logger.info(f"[AI Recovery] 恢复 record_id={record.id}, progress={record.ai_progress}")
                        _recover_ai_analysis(record.id)
                else:
                    logger.info("[AI Recovery] 没有被中断的AI分析任务")
            except Exception as e:
                logger.warning(f"[AI Recovery] 启动恢复检查失败: {e}")

        # 在后台线程中执行恢复检查，避免阻塞启动
        t = threading.Thread(target=_check_and_recover, daemon=True)
        t.start()
