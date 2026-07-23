<template>
  <div class="page-container">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filters.project" placeholder="全部项目" clearable filterable style="width: 160px;" @change="loadTasks">
        <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="filters.task_type" placeholder="任务类型" clearable style="width: 160px;" @change="loadTasks">
        <el-option label="测试套件执行" value="TEST_SUITE" />
        <el-option label="测试用例执行" value="TEST_CASE" />
      </el-select>
      <el-select v-model="filters.trigger_type" placeholder="触发器类型" clearable style="width: 160px;" @change="loadTasks">
        <el-option label="Cron表达式" value="CRON" />
        <el-option label="固定间隔" value="INTERVAL" />
        <el-option label="单次执行" value="ONCE" />
      </el-select>
      <el-select v-model="filters.status" placeholder="执行状态" clearable style="width: 160px;" @change="loadTasks">
        <el-option label="启用" value="ACTIVE" />
        <el-option label="暂停" value="PAUSED" />
        <el-option label="已完成" value="COMPLETED" />
        <el-option label="失败" value="FAILED" />
      </el-select>
      <div class="filter-bar-spacer"></div>
      <el-button type="primary" class="create-btn" @click="handleCreate">
        <el-icon><Plus /></el-icon>新建任务
      </el-button>
    </div>

    <!-- 表格容器 -->
    <div class="card-container">
      <el-table :data="tasks" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="name" label="任务名称" min-width="180" header-align="center" align="center" show-overflow-tooltip />
        <el-table-column label="任务类型" min-width="120" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="row.task_type === 'TEST_SUITE' ? 'success' : 'processing'">
              {{ row.task_type_display }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="触发器" min-width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge processing">{{ row.trigger_type_display }}</span>
          </template>
        </el-table-column>
        <el-table-column label="通知" min-width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.notification_type" class="status-badge" :class="row.notification_type === 'webhook' ? 'processing' : row.notification_type === 'both' ? 'pending' : ''">
              {{ row.notification_type_display }}
            </span>
            <span v-else class="status-badge pending">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="90" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="getStatusClass(row.status)">
              {{ row.status_display }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="设备" min-width="130" header-align="center" align="center">
          <template #default="{ row }">
            {{ row.device_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="下次执行" min-width="170" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.next_run_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="上次执行" min-width="170" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.last_run_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="执行统计" min-width="220" header-align="center" align="center">
          <template #default="{ row }">
            <span class="count-badge">总 {{ row.total_runs }}</span>
            <span class="count-badge success">成功 {{ row.successful_runs }}</span>
            <span class="count-badge failed">失败 {{ row.failed_runs }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" class="action-btn run-btn" @click="runNow(row)" :loading="row._running">
                <el-icon><VideoPlay /></el-icon>
                <span>执行</span>
              </el-button>
              <el-button size="small" class="action-btn edit-btn" @click="editTask(row)">
                <el-icon><Edit /></el-icon>
                <span>编辑</span>
              </el-button>
              <el-button size="small" class="action-btn delete-btn" @click="deleteTask(row)">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="showDialog" :title="editingTask ? '编辑定时任务' : '新建定时任务'" width="720px" :close-on-click-modal="false" @close="resetForm">
      <el-form :model="form" label-width="110px">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="所属项目">
          <el-select v-model="form.project" placeholder="请选择项目" clearable filterable style="width:100%">
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="form.description" type="textarea" placeholder="请输入描述" />
        </el-form-item>

        <el-form-item label="任务类型" required>
          <el-radio-group v-model="form.task_type">
            <el-radio value="TEST_SUITE">测试套件</el-radio>
            <el-radio value="TEST_CASE">测试用例</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="form.task_type === 'TEST_SUITE'" label="测试套件" required>
          <el-select v-model="form.test_suite" placeholder="选择套件" filterable>
            <el-option v-for="s in suites" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.task_type === 'TEST_CASE'" label="测试用例" required>
          <el-select v-model="form.test_case" placeholder="选择用例" filterable>
            <el-option v-for="tc in testCases" :key="tc.id" :label="tc.name" :value="tc.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="执行设备" required>
          <el-select v-model="form.device" placeholder="选择设备" filterable>
            <el-option v-for="d in devices" :key="d.id" :label="d.name || d.device_id" :value="d.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="应用包">
          <el-select v-model="form.app_package" placeholder="选择应用包" filterable clearable>
            <el-option v-for="p in packages" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="触发器类型" required>
          <el-radio-group v-model="form.trigger_type">
            <el-radio value="CRON">Cron表达式</el-radio>
            <el-radio value="INTERVAL">固定间隔</el-radio>
            <el-radio value="ONCE">单次执行</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="form.trigger_type === 'CRON'" label="Cron表达式" required>
          <el-input v-model="form.cron_expression" placeholder="如: 0 0 * * *" />
          <div class="cron-help">
            <el-tooltip raw-content placement="top">
              <template #content>
                <div style="line-height: 1.6; text-align: left;">
                  <div>Cron表达式格式: 分 时 日 月 周</div>
                  <div>分: 0-59</div>
                  <div>时: 0-23</div>
                  <div>日: 1-31</div>
                  <div>月: 1-12 或 JAN-DEC</div>
                  <div>周: 0-6 或 SUN-SAT (0=周日)</div>
                  <div style="margin-top: 8px;">常用示例:</div>
                  <div>每天0点: 0 0 * * *</div>
                  <div>每小时: 0 * * * *</div>
                  <div>每周一9点: 0 9 * * 1</div>
                  <div>每月1号0点: 0 0 1 * *</div>
                </div>
              </template>
              <span style="cursor: pointer; color: #409EFF;">Cron帮助</span>
            </el-tooltip>
          </div>
        </el-form-item>

        <el-form-item v-if="form.trigger_type === 'INTERVAL'" label="间隔时间" required>
          <el-input-number v-model="form.interval_seconds" :min="60" :step="60" />
          <span class="unit">秒</span>
        </el-form-item>

        <el-form-item v-if="form.trigger_type === 'ONCE'" label="执行时间" required>
          <el-date-picker v-model="form.execute_at" type="datetime" placeholder="选择执行时间" />
        </el-form-item>

        <el-form-item label="通知设置">
          <el-checkbox v-model="form.notify_on_success">成功时通知</el-checkbox>
          <el-checkbox v-model="form.notify_on_failure">失败时通知</el-checkbox>
        </el-form-item>

        <el-form-item v-if="form.notify_on_success || form.notify_on_failure" label="通知类型">
          <el-select v-model="form.notification_type" placeholder="选择通知类型">
            <el-option label="邮箱通知" value="email" />
            <el-option label="Webhook机器人" value="webhook" />
            <el-option label="两者都发送" value="both" />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="(form.notify_on_success || form.notify_on_failure) && (form.notification_type === 'email' || form.notification_type === 'both')"
          label="通知邮箱"
        >
          <el-select v-model="form.notify_emails" multiple filterable allow-create placeholder="输入或选择邮箱">
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ editingTask ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, VideoPlay, Edit, Delete } from '@element-plus/icons-vue'
import {
  getAppScheduledTasks,
  createAppScheduledTask,
  updateAppScheduledTask,
  deleteAppScheduledTask,
  pauseAppScheduledTask,
  resumeAppScheduledTask,
  runAppScheduledTask,
  getTestSuiteList,
  getTestCaseList,
  getDeviceList,
  getPackageList,
  getAppProjects,
} from '@/api/app-automation.js'

defineOptions({ name: 'AppScheduledTasks' })

const projectList = ref([])
const tasks = ref([])
const suites = ref([])
const testCases = ref([])
const devices = ref([])
const packages = ref([])
const loading = ref(false)
const submitting = ref(false)
const showDialog = ref(false)
const editingTask = ref(null)

const filters = reactive({ project: null, task_type: '', trigger_type: '', status: '' })
const pagination = reactive({ current: 1, size: 10, total: 0 })

const defaultForm = {
  name: '', description: '', project: null, task_type: 'TEST_SUITE', trigger_type: 'CRON',
  cron_expression: '0 0 * * *', interval_seconds: 3600, execute_at: '',
  device: '', app_package: '', test_suite: '', test_case: '',
  notify_on_success: false, notify_on_failure: false,
  notification_type: '', notify_emails: [],
}
const form = reactive({ ...defaultForm })

onMounted(() => {
  getAppProjects({ page_size: 100 }).then(res => { projectList.value = res.data.results || res.data || [] }).catch(() => {})
  loadTasks()
  loadOptions()
})

const loadTasks = async () => {
  loading.value = true
  try {
    const params = { page: pagination.current, page_size: pagination.size }
    if (filters.project) params.project = filters.project
    if (filters.task_type) params.task_type = filters.task_type
    if (filters.trigger_type) params.trigger_type = filters.trigger_type
    if (filters.status) params.status = filters.status
    const res = await getAppScheduledTasks(params)
    tasks.value = (res.data.results || []).map(t => ({ ...t, _running: false }))
    pagination.total = res.data.count || 0
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

const loadOptions = async () => {
  try {
    const [s, tc, d, p] = await Promise.all([
      getTestSuiteList({ page_size: 200 }),
      getTestCaseList({ page_size: 500 }),
      getDeviceList({ page_size: 100 }),
      getPackageList({ page_size: 100 }),
    ])
    suites.value = s.data.results || s.data || []
    testCases.value = tc.data.results || tc.data || []
    devices.value = d.data.results || d.data || []
    packages.value = p.data.results || p.data || []
  } catch (e) { console.error('加载选项失败', e) }
}

const handleCreate = () => {
  editingTask.value = null
  resetForm()
  showDialog.value = true
}

const resetForm = () => Object.assign(form, { ...defaultForm, notify_emails: [] })
const resetFilters = () => { Object.assign(filters, { project: null, task_type: '', trigger_type: '', status: '' }); loadTasks() }

const submitForm = async () => {
  if (!form.name) return ElMessage.warning('请输入任务名称')
  if (!form.device) return ElMessage.warning('请选择设备')

  submitting.value = true
  try {
    const data = { ...form }
    // 清理多余字段
    if (data.task_type === 'TEST_SUITE') delete data.test_case
    else delete data.test_suite
    if (data.trigger_type !== 'CRON') delete data.cron_expression
    if (data.trigger_type !== 'INTERVAL') delete data.interval_seconds
    if (data.trigger_type !== 'ONCE') delete data.execute_at
    if (!data.notify_on_success && !data.notify_on_failure) {
      delete data.notification_type
      delete data.notify_emails
    }
    if (!data.app_package) delete data.app_package

    if (editingTask.value) {
      await updateAppScheduledTask(editingTask.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await createAppScheduledTask(data)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.response?.data?.message || '操作失败')
  } finally { submitting.value = false }
}

const runNow = async (task) => {
  task._running = true
  try {
    await runAppScheduledTask(task.id)
    ElMessage.success('任务已开始执行')
    setTimeout(loadTasks, 2000)
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '执行失败')
  } finally { task._running = false }
}

const handleAction = (cmd, task) => {
  switch (cmd) {
    case 'edit': editTask(task); break
    case 'pause': pauseTask(task); break
    case 'resume': resumeTask(task); break
    case 'delete': deleteTask(task); break
  }
}

const editTask = (task) => {
  editingTask.value = task
  Object.assign(form, {
    name: task.name, description: task.description || '',
    task_type: task.task_type, trigger_type: task.trigger_type,
    cron_expression: task.cron_expression || '0 0 * * *',
    interval_seconds: task.interval_seconds || 3600,
    execute_at: task.execute_at || '',
    device: task.device || '', app_package: task.app_package || '',
    test_suite: task.test_suite || '', test_case: task.test_case || '',
    notify_on_success: task.notify_on_success || false,
    notify_on_failure: task.notify_on_failure || false,
    notification_type: task.notification_type || '',
    notify_emails: task.notify_emails || [],
  })
  showDialog.value = true
}

const pauseTask = async (task) => {
  try { await pauseAppScheduledTask(task.id); ElMessage.success('已暂停'); loadTasks() }
  catch { ElMessage.error('暂停失败') }
}
const resumeTask = async (task) => {
  try { await resumeAppScheduledTask(task.id); ElMessage.success('已恢复'); loadTasks() }
  catch { ElMessage.error('恢复失败') }
}
const deleteTask = async (task) => {
  try {
    await ElMessageBox.confirm(`确认删除任务「${task.name}」？`, '删除确认', { type: 'warning' })
    await deleteAppScheduledTask(task.id)
    ElMessage.success('已删除')
    loadTasks()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const getStatusClass = (status) => {
  const classMap = {
    'ACTIVE': 'success',
    'PAUSED': 'pending',
    'COMPLETED': 'success',
    'FAILED': 'failed',
  }
  return classMap[status] || 'pending'
}

const formatDateTime = (s) => {
  if (!s) return '-'
  return new Date(s).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).replace(/\//g, '-')
}
</script>

<style scoped lang="scss">
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  line-height: 24px;
  gap: 20px;
}

.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(167, 139, 250, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;

  .filter-bar-spacer {
    flex: 1;
  }

  .create-btn {
    background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(167, 139, 250, 0.3) !important;

    .el-icon {
      margin-right: 6px;
    }

    &:hover {
      background: linear-gradient(135deg, #9370db 0%, #7c3aed 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 20px rgba(167, 139, 250, 0.4) !important;
    }
  }
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(167, 139, 250, 0.08);
  display: flex;
  flex-direction: column;
  overflow-x: auto;
  overflow-y: hidden;
  padding-top: 16px;

  .el-table {
    border: none;
    border-radius: 8px 8px 0 0;
    overflow: hidden;
    min-height: 200px;
    box-shadow: none;
    transition: all 0.3s ease;
    background-color: transparent !important;

    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: #7b42f6;
    --el-color-primary-light-3: #9370db;
    --el-color-primary-light-5: #a888e0;
    --el-color-primary-light-7: #c2a9f3;
    --el-color-primary-light-9: #f8f7ff;
    --el-border-color: #e9ecef;
    --el-border-color-light: #e9ecef;
    --el-border-color-lighter: #e9ecef;
    --el-fill-color-light: #ffffff;
    --el-fill-color-lighter: #ffffff;
    --el-fill-color-blank: #ffffff;
    --el-text-color-primary: #333;
    --el-text-color-regular: #333;
    --el-text-color-secondary: #666;
    --el-text-color-placeholder: #999;
    --el-table-header-bg-color: #ffffff;
    --el-table-row-hover-bg-color: #f8f7ff;
    --el-table-stripe-bg-color: #fafaff;

    &::before {
      display: none;
    }

    :deep(.el-table__header-wrapper) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__header) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__header th) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
      font-size: 14px;
      border-bottom: 1px solid #e9ecef;
      padding: 0 !important;
      text-align: center;
      transition: all 0.3s ease;

      &:hover {
        background-color: #ffffff !important;
      }
    }

    :deep(.el-table__header th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
      white-space: nowrap !important;
      line-height: 24px !important;
      padding: 16px !important;
    }

    :deep(.el-table__body-wrapper) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__row) {
      transition: all 0.3s ease;
      background-color: #ffffff !important;
      line-height: 24px;

      &:hover {
        background-color: #f8f7ff !important;
      }

      &.el-table__row--striped {
        background-color: #fafaff !important;
      }
    }

    :deep(td) {
      padding: 14px 16px;
      border-bottom: 1px solid #e9ecef;
      color: #333;
      font-size: 14px;
      font-weight: 400;
      line-height: 24px;
      transition: all 0.3s ease;
      vertical-align: middle;
    }

    :deep(td .cell) {
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      min-height: 24px;
      line-height: 1.5;
      width: 100%;

      .time-text {
        color: #666 !important;
        font-size: 14px !important;
        white-space: nowrap;
      }
    }

    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;
    }
  }
}

// 时间文本样式
:deep(td) .time-text {
  color: #666 !important;
  font-size: 14px !important;
  white-space: nowrap;
  display: inline-block;
}

:deep(td .cell) > .time-text {
  color: #666 !important;
  font-size: 14px !important;
  white-space: nowrap;
}

:deep(.time-text) {
  color: #666 !important;
  font-size: 14px !important;
  white-space: nowrap;
  display: inline-block;
}

.time-text {
  color: #666 !important;
  font-size: 14px !important;
  white-space: nowrap;
  display: inline-block;
}

.pagination-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 0;
  margin-top: 8px;
  background: transparent;
  border: none;
  transition: all 0.3s ease;

  --primary-color: #a78bfa;
  --primary-dark: #8b5cf6;
  --primary-light: #f3f0ff;
  --text-primary: #262626;
  --text-secondary: #595959;
  --text-tertiary: #8c8c8c;

  --el-color-primary: var(--primary-color);
  --el-color-primary-light-3: #c4b5fd;
  --el-color-primary-light-5: #ddd6fe;
  --el-color-primary-light-7: #ede9fe;
  --el-color-primary-light-9: #f5f3ff;
  --el-border-color: rgba(167, 139, 250, 0.3);
  --el-border-color-light: rgba(167, 139, 250, 0.2);
  --el-border-color-lighter: rgba(167, 139, 250, 0.1);
  --el-fill-color-light: #f5f3ff;
  --el-fill-color-lighter: #f5f3ff;
  --el-fill-color-blank: #f5f3ff;
  --el-text-color-primary: var(--text-primary);
  --el-text-color-regular: var(--text-secondary);
  --el-text-color-secondary: var(--text-tertiary);

  :deep(.el-pagination) {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;

    .el-pagination__total { color: #6b7280; font-size: 14px; font-weight: 500; margin-right: 12px; }
    .el-pagination__sizes { margin-right: 12px; .el-select .el-input__wrapper { border-radius: 8px; border: 1px solid #e5e7eb; background: #ffffff; box-shadow: none; &:hover { border-color: #a78bfa; box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1); } &.is-focus { border-color: #a78bfa; box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15); } } .el-input__inner { color: #374151; font-weight: 500; } }
    .btn-prev, .btn-next { width: 32px; height: 32px; border-radius: 8px; border: 1px solid #e5e7eb; background: #ffffff; color: #6b7280; transition: all 0.3s ease; &:hover:not(:disabled) { background: #f5f3ff; border-color: #a78bfa; color: #8b5cf6; transform: translateY(-1px); box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2); } &:disabled { background: #f5f5f5; border-color: #e0e0e0; color: #c0c0c0; } .el-icon { font-size: 14px; font-weight: bold; } }
    .el-pager { display: flex; gap: 8px; li { min-width: 32px; height: 32px; padding: 0 8px; border-radius: 8px; border: 1px solid #d1d5db; background: #ffffff; color: #6b7280; font-size: 14px; font-weight: 500; transition: all 0.3s ease; display: flex; align-items: center; justify-content: center; &:hover:not(.is-active) { background: #f5f3ff; border-color: #a78bfa; color: #8b5cf6; transform: translateY(-1px); } &.is-active { background: #f5f3ff; border-color: #a78bfa; color: #8b5cf6; box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2); } &.is-active:hover { background: #ede9fe; border-color: #8b5cf6; } } }
    .el-pagination__jump { color: #6b7280; font-weight: 500; margin-left: 12px; .el-input { width: 50px; margin: 0 4px; .el-input__wrapper { border-radius: 8px; border: 1px solid #e5e7eb; background: #ffffff; box-shadow: none; &:hover { border-color: #a78bfa; box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1); } &.is-focus { border-color: #a78bfa; box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15); } } .el-input__inner { color: #374151; font-weight: 500; text-align: center; } } }
  }
}
.cron-help { margin-top: 8px; font-size: 12px; }
.unit { margin-left: 8px; color: #666; }

// 状态徽章样式
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
  white-space: nowrap;

  &.success {
    background: #f6ffed;
    color: #52c41a;
  }

  &.failed {
    background: #fff1f0;
    color: #f5222d;
  }

  &.processing {
    background: #fff7e6;
    color: #fa8c16;
  }

  &.pending {
    background: #f5f5f5;
    color: #8c8c8c;
  }
}

// 数量徽章样式
.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #e6f7ff;
  color: #1890ff;
  white-space: nowrap;
  margin-right: 4px;

  &.success {
    background: #f6ffed;
    color: #52c41a;
  }

  &.failed {
    background: #fff1f0;
    color: #f5222d;
  }
}

// 操作按钮样式
.action-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px !important;
  border-radius: 6px;
  transition: all 0.3s ease;
  border: none !important;

  .el-icon {
    font-size: 14px;
    color: #ffffff !important;
  }

  span {
    font-size: 12px;
    color: #ffffff !important;
  }

  &.edit-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }
  }

  &.run-btn {
    background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
    }
  }

  &.delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
    }
  }
}
</style>
