<template>
  <div class="page-container">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filters.task_type" :placeholder="$t('apiTesting.scheduledTask.taskType')" clearable style="width: 160px;" @change="handleFilterChange">
        <el-option :label="$t('apiTesting.scheduledTask.taskTypes.testSuite')" value="TEST_SUITE" />
        <el-option :label="$t('apiTesting.scheduledTask.taskTypes.apiRequest')" value="API_REQUEST" />
        <el-option :label="$t('apiTesting.scheduledTask.taskTypes.apifoxScenario')" value="APIFOX_SCENARIO" />
      </el-select>
      <el-select v-model="filters.trigger_type" :placeholder="$t('apiTesting.scheduledTask.triggerType')" clearable style="width: 160px;" @change="handleFilterChange">
        <el-option :label="$t('apiTesting.scheduledTask.triggerTypes.cron')" value="CRON" />
        <el-option :label="$t('apiTesting.scheduledTask.triggerTypes.interval')" value="INTERVAL" />
        <el-option :label="$t('apiTesting.scheduledTask.triggerTypes.once')" value="ONCE" />
      </el-select>
      <el-select v-model="filters.status" :placeholder="$t('apiTesting.scheduledTask.taskStatus')" clearable style="width: 160px;" @change="handleFilterChange">
        <el-option :label="$t('apiTesting.scheduledTask.status.active')" value="ACTIVE" />
        <el-option :label="$t('apiTesting.scheduledTask.status.paused')" value="PAUSED" />
        <el-option :label="$t('apiTesting.scheduledTask.status.completed')" value="COMPLETED" />
        <el-option :label="$t('apiTesting.scheduledTask.status.failed')" value="FAILED" />
      </el-select>
      <div class="filter-bar-spacer"></div>
      <el-button type="primary" class="create-btn" @click="handleCreateClick">
        <el-icon><Plus /></el-icon>
        {{ $t('apiTesting.scheduledTask.createTask') }}
      </el-button>
    </div>

    <!-- 任务列表 -->
    <div class="card-container">
      <el-table :data="tasks" v-loading="loading" stripe>
        <el-table-column label="序号" width="80" header-align="center" align="center">
          <template #default="{ $index }">
            {{ (pagination.current - 1) * pagination.size + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="name" :label="$t('apiTesting.scheduledTask.taskName')" min-width="180" header-align="center" align="center" show-overflow-tooltip />
        <el-table-column prop="task_type" :label="$t('apiTesting.scheduledTask.taskType')" width="120" header-align="center" align="center">
          <template #default="scope">
            <span class="task-type-badge" :class="getTaskTypeClass(scope.row.task_type)">
              {{ getTaskTypeText(scope.row.task_type) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="notification_type_display" :label="$t('apiTesting.scheduledTask.notificationType')" min-width="140" header-align="center" align="center">
          <template #default="scope">
            <span v-if="scope.row.notification_type_display && scope.row.notification_type_display !== '-'"
                  class="notification-type-badge"
                  :class="getNotificationTypeClass(scope.row.notification_type_display)">
              {{ scope.row.notification_type_display }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_type" :label="$t('apiTesting.scheduledTask.triggerType')" width="120" header-align="center" align="center">
          <template #default="scope">
            <span class="trigger-type-badge">
              {{ getTriggerTypeText(scope.row.trigger_type) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="$t('apiTesting.common.status')" width="100" header-align="center" align="center">
          <template #default="scope">
            <span class="status-badge" :class="getStatusClass(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="next_run_time" :label="$t('apiTesting.scheduledTask.nextRunTime')" width="180" header-align="center" align="center">
          <template #default="scope">
            {{ formatDateTime(scope.row.next_run_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_run_time" :label="$t('apiTesting.scheduledTask.lastRunTime')" width="180" header-align="center" align="center">
          <template #default="scope">
            {{ formatDateTime(scope.row.last_run_time) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('apiTesting.common.operation')" width="410" fixed="right" header-align="center" align="center">
          <template #default="scope">
            <div class="action-buttons">
              <el-button size="small" class="action-btn run-btn" @click="runTaskNow(scope.row)" :loading="scope.row.running">
                <span>{{ $t('apiTesting.scheduledTask.runNow') }}</span>
              </el-button>
              <el-button size="small" class="action-btn edit-btn" @click="editTask(scope.row)">
                <span>{{ $t('apiTesting.common.edit') }}</span>
              </el-button>
              <el-button size="small" class="action-btn pause-btn" v-if="scope.row.status === 'ACTIVE'" @click="pauseTask(scope.row)">
                <span>{{ $t('apiTesting.scheduledTask.pause') }}</span>
              </el-button>
              <el-button size="small" class="action-btn resume-btn" v-if="scope.row.status === 'PAUSED'" @click="activateTask(scope.row)">
                <span>{{ $t('apiTesting.scheduledTask.activate') }}</span>
              </el-button>
              <el-button size="small" class="action-btn log-btn" @click="viewTaskLogs(scope.row)">
                <span>{{ $t('apiTesting.scheduledTask.executionLogs') }}</span>
              </el-button>
              <el-button size="small" class="action-btn delete-btn" @click="deleteTask(scope.row)">
                <span>{{ $t('apiTesting.common.delete') }}</span>
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
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTask ? $t('apiTesting.scheduledTask.editTask') : $t('apiTesting.scheduledTask.createTask')"
      width="800px"
      :close-on-click-modal="false"
      @close="resetTaskForm"
      class="task-dialog"
    >
      <el-form :model="taskForm" label-width="120px">
        <el-form-item :label="$t('apiTesting.scheduledTask.taskName')" required>
          <el-input v-model="taskForm.name" :placeholder="$t('apiTesting.scheduledTask.inputTaskName')" />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.scheduledTask.taskDescription')">
          <el-input v-model="taskForm.description" type="textarea" :placeholder="$t('apiTesting.scheduledTask.inputTaskDesc')" />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.scheduledTask.taskType')" required>
          <el-radio-group v-model="taskForm.task_type">
            <el-radio label="TEST_SUITE">{{ $t('apiTesting.scheduledTask.taskTypes.testSuite') }}</el-radio>
            <el-radio label="API_REQUEST">{{ $t('apiTesting.scheduledTask.taskTypes.apiRequest') }}</el-radio>
            <el-radio label="APIFOX_SCENARIO">{{ $t('apiTesting.scheduledTask.taskTypes.apifoxScenario') }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item :label="$t('apiTesting.scheduledTask.triggerType')" required>
          <el-radio-group v-model="taskForm.trigger_type">
            <el-radio label="CRON">{{ $t('apiTesting.scheduledTask.triggerTypes.cron') }}</el-radio>
            <el-radio label="INTERVAL">{{ $t('apiTesting.scheduledTask.triggerTypes.interval') }}</el-radio>
            <el-radio label="ONCE">{{ $t('apiTesting.scheduledTask.triggerTypes.once') }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 根据触发器类型显示不同配置 -->
        <el-form-item v-if="taskForm.trigger_type === 'CRON'" required>
          <template #label>
            <span style="white-space: nowrap;">{{ $t('apiTesting.scheduledTask.cronExpression') }}</span>
            <el-tooltip raw-content placement="top">
              <template #content>
                <div style="line-height: 1.6; text-align: left;">
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.format') }}</div>
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.minute') }}</div>
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.hour') }}</div>
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.day') }}</div>
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.month') }}</div>
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.week') }}</div>
                  <div style="margin-top: 8px;">{{ $t('apiTesting.scheduledTask.cronHelp.examples') }}</div>
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.daily') }}</div>
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.hourly') }}</div>
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.weekly') }}</div>
                  <div>{{ $t('apiTesting.scheduledTask.cronHelp.monthly') }}</div>
                </div>
              </template>
              <el-icon class="cron-help-icon"><Warning /></el-icon>
            </el-tooltip>
          </template>
          <el-input v-model="taskForm.cron_expression" placeholder="0 0 * * *" />
        </el-form-item>

        <el-form-item v-if="taskForm.trigger_type === 'INTERVAL'" :label="$t('apiTesting.scheduledTask.intervalTime')" required>
          <el-input-number v-model="taskForm.interval_seconds" :min="60" :step="60" />
          <span class="unit">{{ $t('apiTesting.scheduledTask.seconds') }}</span>
        </el-form-item>

        <el-form-item v-if="taskForm.trigger_type === 'ONCE'" :label="$t('apiTesting.scheduledTask.executeTime')" required>
          <el-date-picker
            v-model="taskForm.execute_at"
            type="datetime"
            :placeholder="$t('apiTesting.scheduledTask.selectExecuteTime')"
          />
        </el-form-item>

        <!-- 根据任务类型显示不同配置 -->
        <el-form-item v-if="taskForm.task_type === 'TEST_SUITE'" :label="$t('apiTesting.scheduledTask.testSuite')" required>
          <el-select v-model="taskForm.test_suite" :placeholder="$t('apiTesting.scheduledTask.selectTestSuite')">
            <el-option
              v-for="suite in testSuites"
              :key="suite.id"
              :label="suite.name"
              :value="suite.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="taskForm.task_type === 'API_REQUEST'" :label="$t('apiTesting.scheduledTask.apiRequest')" required>
          <el-select v-model="taskForm.api_request" :placeholder="$t('apiTesting.scheduledTask.selectApiRequest')">
            <el-option
              v-for="request in apiRequests"
              :key="request.id"
              :label="request.name"
              :value="request.id"
            />
          </el-select>
        </el-form-item>

        <!-- Apifox 场景配置 -->
        <template v-if="taskForm.task_type === 'APIFOX_SCENARIO'">
          <el-form-item :label="$t('apiTesting.scheduledTask.apifoxConfig')" required>
            <div class="apifox-config-section">
              <el-form-item :label="$t('apiTesting.scheduledTask.apifoxProjectId')" required>
                <el-input v-model="taskForm.apifox_config.project_id" :placeholder="$t('apiTesting.scheduledTask.apifoxProjectIdPlaceholder')" />
              </el-form-item>
              <el-form-item :label="$t('apiTesting.scheduledTask.apifoxEnvironmentId')" required>
                <el-input v-model="taskForm.apifox_config.environment_id" :placeholder="$t('apiTesting.scheduledTask.apifoxEnvironmentIdPlaceholder')" />
              </el-form-item>
              <el-form-item :label="$t('apiTesting.scheduledTask.apifoxAccessToken')" required>
                <el-input v-model="taskForm.apifox_config.access_token" type="password" show-password :placeholder="$t('apiTesting.scheduledTask.apifoxAccessTokenPlaceholder')" />
              </el-form-item>
              <el-form-item :label="$t('apiTesting.scheduledTask.apifoxLocalEnvironment')">
                <el-select v-model="taskForm.apifox_config.local_environment_id" clearable filterable :placeholder="$t('apiTesting.scheduledTask.apifoxSelectLocalEnv')">
                  <el-option
                    v-for="env in environments"
                    :key="env.id"
                    :label="env.name"
                    :value="env.id"
                  />
                </el-select>
              </el-form-item>
            </div>
          </el-form-item>

          <el-form-item :label="$t('apiTesting.scheduledTask.apifoxScenarios')" required>
            <div class="apifox-scenario-section">
              <div class="scenario-selector">
                <el-button type="primary" plain @click="openScenarioSelector">
                  {{ $t('apiTesting.scheduledTask.apifoxSelectScenarios') }}
                </el-button>
                <el-button link type="primary" @click="fetchApifoxScenarios" :loading="fetchingApifoxScenarios">
                  {{ $t('apiTesting.scheduledTask.apifoxRefreshScenarios') }}
                </el-button>
              </div>
              <div v-if="taskForm.apifox_scenario_ids.length > 0" class="selected-scenarios">
                <el-tag
                  v-for="sid in taskForm.apifox_scenario_ids"
                  :key="sid"
                  closable
                  @close="removeScenario(sid)"
                  class="scenario-tag"
                >
                  {{ getScenarioName(sid) }}
                </el-tag>
              </div>
              <div v-else class="no-scenarios-tip">
                {{ $t('apiTesting.scheduledTask.apifoxNoScenariosSelected') }}
              </div>
            </div>
          </el-form-item>
        </template>

        <el-form-item :label="$t('apiTesting.scheduledTask.executeEnvironment')">
          <el-select v-model="taskForm.environment" :placeholder="$t('apiTesting.scheduledTask.selectEnvironment')">
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('apiTesting.scheduledTask.notificationSettings')">
          <el-checkbox v-model="taskForm.notify_on_success">{{ $t('apiTesting.scheduledTask.notifyOnSuccess') }}</el-checkbox>
          <el-checkbox v-model="taskForm.notify_on_failure">{{ $t('apiTesting.scheduledTask.notifyOnFailure') }}</el-checkbox>
        </el-form-item>

        <el-form-item v-if="taskForm.notify_on_success || taskForm.notify_on_failure" :label="$t('apiTesting.scheduledTask.notificationType')">
          <el-select v-model="taskForm.notification_type" :placeholder="$t('apiTesting.scheduledTask.selectNotificationType')">
            <el-option :label="$t('apiTesting.notification.types.email')" value="email" />
            <el-option :label="$t('apiTesting.notification.types.webhook')" value="webhook" />
            <el-option :label="$t('apiTesting.notification.types.both')" value="both" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="(taskForm.notify_on_success || taskForm.notify_on_failure) && taskForm.notification_type !== 'webhook'" :label="$t('apiTesting.scheduledTask.notifyEmails')">
          <el-select
            v-model="taskForm.notify_emails"
            multiple
            filterable
            :placeholder="$t('apiTesting.scheduledTask.selectNotifyEmails')"
          >
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.display_name"
              :value="user.email"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button class="cancel-btn" @click="showCreateDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
          <el-button type="primary" class="save-btn" @click="submitTaskForm" :loading="submitting">
            {{ editingTask ? $t('apiTesting.common.update') : $t('apiTesting.common.create') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 执行日志对话框 -->
    <el-dialog v-model="showLogsDialog" :title="$t('apiTesting.scheduledTask.executionLogs')" width="1000px">
      <el-table :data="executionLogs" v-loading="logsLoading" stripe>
        <el-table-column prop="start_time" :label="$t('apiTesting.scheduledTask.startTime')" width="180" header-align="center" align="center">
          <template #default="scope">
            <div class="time-cell">{{ formatDateTime(scope.row.start_time) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="end_time" :label="$t('apiTesting.scheduledTask.endTime')" width="180" header-align="center" align="center">
          <template #default="scope">
            <div class="time-cell">{{ formatDateTime(scope.row.end_time) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="$t('apiTesting.common.status')" width="100" header-align="center" align="center">
          <template #default="scope">
            <span class="status-badge" :class="scope.row.status === 'COMPLETED' ? 'active' : 'failed'">
              {{ scope.row.status === 'COMPLETED' ? $t('apiTesting.common.success') : $t('apiTesting.common.failed') }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" :label="$t('apiTesting.scheduledTask.errorMessage')" min-width="300" show-overflow-tooltip header-align="center" align="center" />
      </el-table>
    </el-dialog>

    <!-- Apifox 场景选择对话框 -->
    <el-dialog v-model="showScenarioSelector" :title="$t('apiTesting.scheduledTask.apifoxSelectScenarios')" width="700px">
      <div class="scenario-selector-content">
        <div class="selector-tip">
          {{ $t('apiTesting.scheduledTask.apifoxConfigTip') }}
        </div>
        <div class="selector-search">
          <el-input v-model="scenarioSearchText" :placeholder="$t('apiTesting.scheduledTask.apifoxSearchScenario')" clearable style="width: 100%;" />
        </div>
        <div v-loading="fetchingApifoxScenarios" class="selector-table">
          <el-table :data="filteredApifoxScenarios" @selection-change="handleScenarioSelectionChange" ref="scenarioTableRef" height="360">
            <el-table-column type="selection" width="50" />
            <el-table-column prop="name" :label="$t('apiTesting.scheduledTask.apifoxScenarioName')" min-width="200" show-overflow-tooltip />
            <el-table-column prop="folder_path" :label="$t('apiTesting.scheduledTask.apifoxScenarioFolder')" width="150" show-overflow-tooltip />
            <el-table-column prop="step_count" :label="$t('apiTesting.scheduledTask.apifoxScenarioSteps')" width="80" align="center" />
          </el-table>
        </div>
        <div class="selector-footer">
          <span>{{ $t('apiTesting.scheduledTask.apifoxSelectedCount', { count: tempSelectedScenarioIds.length }) }}</span>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button class="cancel-btn" @click="cancelScenarioSelection">{{ $t('apiTesting.common.cancel') }}</el-button>
          <el-button type="primary" class="save-btn" @click="confirmScenarioSelection">{{ $t('apiTesting.common.confirm') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Warning } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import api from '@/utils/api'
import {
  getScheduledTasks,
  createScheduledTask,
  updateScheduledTask,
  deleteScheduledTask,
  runScheduledTask,
  getExecutionLogs,
  getTestSuites,
  getApiRequests,
  getEnvironments,
  getUsers,
  getApifoxScenarios,
  getApifoxConfig,
  saveApifoxConfig,
} from '@/api/api-testing.js'

const { t } = useI18n()

// 获取状态文本
const getStatusText = (status) => {
  const statusKey = {
    'ACTIVE': 'active',
    'PAUSED': 'paused',
    'COMPLETED': 'completed',
    'FAILED': 'failed'
  }[status]
  return statusKey ? t(`apiTesting.scheduledTask.status.${statusKey}`) : status
}

// 获取状态样式类
const getStatusClass = (status) => {
  const classMap = {
    'ACTIVE': 'active',
    'PAUSED': 'paused',
    'COMPLETED': 'completed',
    'FAILED': 'failed'
  }
  return classMap[status] || 'default'
}

// 获取触发器类型文本
const getTriggerTypeText = (type) => {
  const typeKey = {
    'CRON': 'cron',
    'INTERVAL': 'interval',
    'ONCE': 'once'
  }[type]
  return typeKey ? t(`apiTesting.scheduledTask.triggerTypes.${typeKey}`) : type
}

// 获取通知类型样式类
const getNotificationTypeClass = (typeDisplay) => {
  const typeMap = {
    '邮箱通知': 'email',
    'Email Notification': 'email',
    'Webhook机器人': 'webhook',
    'Webhook Robot': 'webhook',
    '两者都发送': 'both',
    'Both': 'both'
  }
  return typeMap[typeDisplay] || ''
}

// 获取任务类型样式类
const getTaskTypeClass = (taskType) => {
  const classMap = {
    'TEST_SUITE': 'test-suite',
    'API_REQUEST': 'api-request',
    'APIFOX_SCENARIO': 'apifox-scenario'
  }
  return classMap[taskType] || 'default'
}

// 获取任务类型文本
const getTaskTypeText = (taskType) => {
  const textMap = {
    'TEST_SUITE': t('apiTesting.scheduledTask.taskTypes.testSuiteShort'),
    'API_REQUEST': t('apiTesting.scheduledTask.taskTypes.apiRequestShort'),
    'APIFOX_SCENARIO': t('apiTesting.scheduledTask.taskTypes.apifoxScenarioShort')
  }
  return textMap[taskType] || taskType
}

// 数据状态
const tasks = ref([])
const executionLogs = ref([])
const testSuites = ref([])
const apiRequests = ref([])
const environments = ref([])
const users = ref([])
const loading = ref(false)
const logsLoading = ref(false)
const submitting = ref(false)
const showCreateDialog = ref(false)
const showLogsDialog = ref(false)
const editingTask = ref(null)

// 筛选条件
const filters = reactive({
  task_type: '',
  trigger_type: '',
  status: ''
})

// 分页配置
const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

// 表单数据
const taskForm = reactive({
  name: '',
  description: '',
  task_type: 'TEST_SUITE',
  trigger_type: 'CRON',
  cron_expression: '0 0 * * *',
  interval_seconds: 3600,
  execute_at: '',
  test_suite: '',
  api_request: '',
  environment: '',
  notify_on_success: false,
  notify_on_failure: false,
  notification_type: 'email',
  notify_emails: [],
  apifox_scenario_ids: [],
  apifox_config: {
    project_id: '',
    environment_id: '',
    access_token: '',
    local_environment_id: null,
  }
})

// Apifox 场景相关状态
const apifoxScenarios = ref([])
const fetchingApifoxScenarios = ref(false)
const showScenarioSelector = ref(false)
const scenarioSearchText = ref('')
const tempSelectedScenarioIds = ref([])
const scenarioTableRef = ref(null)
const apifoxScenarioNameMap = computed(() => {
  const map = {}
  apifoxScenarios.value.forEach(s => { map[s.id] = s.name })
  return map
})
const filteredApifoxScenarios = computed(() => {
  if (!scenarioSearchText.value) return apifoxScenarios.value
  const kw = scenarioSearchText.value.toLowerCase()
  return apifoxScenarios.value.filter(s =>
    (s.name && s.name.toLowerCase().includes(kw)) ||
    (s.folder_path && s.folder_path.toLowerCase().includes(kw))
  )
})

// 生命周期
onMounted(() => {
  loadTasks()
  loadTestSuites()
  loadApiRequests()
  loadEnvironments()
  loadUsers()
  loadApifoxConfig()
})

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.current,
      page_size: pagination.size,
      ...filters
    }
    const response = await getScheduledTasks(params)
    tasks.value = response.data.results
    pagination.total = response.data.count
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadTasksFailed'))
  } finally {
    loading.value = false
  }
}

// 处理筛选变化
const handleFilterChange = () => {
  pagination.current = 1
  loadTasks()
}

// 加载测试套件
const loadTestSuites = async () => {
  try {
    const response = await getTestSuites()
    testSuites.value = response.data.results
  } catch (error) {
    console.error('加载测试套件失败:', error)
  }
}

// 加载API请求
const loadApiRequests = async () => {
  try {
    const response = await getApiRequests()
    apiRequests.value = response.data.results
  } catch (error) {
    console.error('加载API请求失败:', error)
  }
}

// 加载环境
const loadEnvironments = async () => {
  try {
    const response = await getEnvironments()
    environments.value = response.data.results
  } catch (error) {
    console.error('加载环境失败:', error)
  }
}

// 加载用户列表
const loadUsers = async () => {
  try {
    const response = await getUsers()
    const usersData = response.data.results || response.data
    users.value = usersData.map(user => ({
      ...user,
      display_name: user.first_name ? `${user.first_name}（${user.email}）` : `${user.username}（${user.email}）`
    }))
  } catch (error) {
    console.error('加载用户列表失败:', error)
  }
}

// 新建按钮点击
const handleCreateClick = () => {
  editingTask.value = null
  resetTaskForm()
  showCreateDialog.value = true
}

// 重置表单
const resetTaskForm = () => {
  Object.assign(taskForm, {
    name: '',
    description: '',
    task_type: 'TEST_SUITE',
    trigger_type: 'CRON',
    cron_expression: '0 0 * * *',
    interval_seconds: 3600,
    execute_at: '',
    test_suite: '',
    api_request: '',
    environment: '',
    notify_on_success: false,
    notify_on_failure: false,
    notification_type: 'email',
    notify_emails: [],
    apifox_scenario_ids: [],
    apifox_config: {
      project_id: '',
      environment_id: '',
      access_token: '',
      local_environment_id: null,
    }
  })
}

// 提交任务表单
const submitTaskForm = async () => {
  submitting.value = true
  try {
    const submitData = {
      name: taskForm.name,
      description: taskForm.description,
      task_type: taskForm.task_type,
      trigger_type: taskForm.trigger_type,
      notify_on_success: taskForm.notify_on_success,
      notify_on_failure: taskForm.notify_on_failure,
      notification_type_input: taskForm.notification_type,
      notify_emails: taskForm.notify_emails,
      environment: taskForm.environment
    }

    if (taskForm.trigger_type === 'CRON') {
      submitData.cron_expression = taskForm.cron_expression
    } else if (taskForm.trigger_type === 'INTERVAL') {
      submitData.interval_seconds = taskForm.interval_seconds
    } else if (taskForm.trigger_type === 'ONCE') {
      submitData.execute_at = taskForm.execute_at
    }

    if (taskForm.task_type === 'TEST_SUITE') {
      submitData.test_suite = taskForm.test_suite
    } else if (taskForm.task_type === 'API_REQUEST') {
      submitData.api_request = taskForm.api_request
    } else if (taskForm.task_type === 'APIFOX_SCENARIO') {
      submitData.apifox_scenario_ids = taskForm.apifox_scenario_ids
      submitData.apifox_config = taskForm.apifox_config
      // 保存 Apifox 配置到后端
      try {
        await saveApifoxConfig(taskForm.apifox_config)
      } catch (e) {
        console.warn('保存Apifox配置失败:', e)
      }
    }

    if (editingTask.value) {
      await updateScheduledTask(editingTask.value.id, submitData)
      ElMessage.success(t('apiTesting.messages.success.taskUpdated'))
    } else {
      await createScheduledTask(submitData)
      ElMessage.success(t('apiTesting.messages.success.taskCreated'))
    }
    showCreateDialog.value = false
    loadTasks()
  } catch (error) {
    console.error('Task operation failed:', error)
    ElMessage.error(error.response?.data?.error ||
                   error.response?.data?.detail ||
                   (editingTask.value ? t('apiTesting.messages.error.updateTaskFailed') : t('apiTesting.messages.error.createTaskFailed')))
  } finally {
    submitting.value = false
  }
}

// 立即执行任务
const runTaskNow = async (task) => {
  try {
    task.running = true
    await runScheduledTask(task.id)
    ElMessage.success(t('apiTesting.messages.success.taskStarted'))
    setTimeout(() => {
      loadTasks()
    }, 2000)
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.executeTaskFailed'))
  } finally {
    task.running = false
  }
}

// 格式化日期时间
const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).replace(/\//g, '-')
}

// 查看执行日志
const viewTaskLogs = async (task) => {
  logsLoading.value = true
  try {
    const response = await getExecutionLogs(task.id)
    executionLogs.value = response.data.results || response.data
    showLogsDialog.value = true
  } catch (error) {
    console.error('Load execution logs failed:', error)
    ElMessage.error(t('apiTesting.messages.error.loadLogsFailed'))
  } finally {
    logsLoading.value = false
  }
}

// 编辑任务
const editTask = (task) => {
  editingTask.value = task
  Object.assign(taskForm, {
    name: task.name,
    description: task.description,
    task_type: task.task_type,
    trigger_type: task.trigger_type,
    cron_expression: task.cron_expression,
    interval_seconds: task.interval_seconds,
    execute_at: task.execute_at,
    test_suite: task.test_suite || null,
    api_request: task.api_request || null,
    environment: task.environment || null,
    notify_on_success: task.notify_on_success,
    notify_on_failure: task.notify_on_failure,
    notification_type: task.notification_type || 'email',
    notify_emails: task.notify_emails || [],
    apifox_scenario_ids: task.apifox_scenario_ids || [],
    apifox_config: task.apifox_config || {
      project_id: '',
      environment_id: '',
      access_token: '',
      local_environment_id: null,
    }
  })
  showCreateDialog.value = true
  // 如果是 Apifox 场景类型，加载场景列表
  if (task.task_type === 'APIFOX_SCENARIO' && task.apifox_config?.project_id) {
    fetchApifoxScenarios()
  }
}

// 暂停任务
const pauseTask = async (task) => {
  try {
    await api.post(`/api-testing/scheduled-tasks/${task.id}/pause/`)
    ElMessage.success(t('apiTesting.messages.success.taskPaused'))
    loadTasks()
  } catch (error) {
    console.error('Pause task failed:', error)
    ElMessage.error(t('apiTesting.messages.error.pauseTaskFailed'))
  }
}

// 激活任务
const activateTask = async (task) => {
  try {
    await api.post(`/api-testing/scheduled-tasks/${task.id}/activate/`)
    ElMessage.success(t('apiTesting.messages.success.taskActivated'))
    loadTasks()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.activateTaskFailed'))
  }
}

// 删除任务
const deleteTask = async (task) => {
  try {
    await ElMessageBox.confirm(
      t('apiTesting.scheduledTask.confirmDeleteTask'),
      t('apiTesting.common.tip'),
      {
        confirmButtonText: t('apiTesting.common.confirm'),
        cancelButtonText: t('apiTesting.common.cancel'),
        type: 'warning'
      }
    )
    await deleteScheduledTask(task.id)
    ElMessage.success(t('apiTesting.messages.success.taskDeleted'))
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('apiTesting.messages.error.deleteTaskFailed'))
    }
  }
}

// ==================== Apifox 场景相关方法 ====================

const fetchApifoxScenarios = async () => {
  if (!taskForm.apifox_config.project_id || !taskForm.apifox_config.environment_id) {
    ElMessage.warning(t('apiTesting.scheduledTask.apifoxConfigRequired'))
    return
  }
  fetchingApifoxScenarios.value = true
  try {
    const res = await getApifoxScenarios({
      project_id: taskForm.apifox_config.project_id,
      environment_id: taskForm.apifox_config.environment_id,
    })
    apifoxScenarios.value = res.data.scenarios || []
    ElMessage.success(t('apiTesting.scheduledTask.apifoxLoadSuccess', { count: apifoxScenarios.value.length }))
  } catch (e) {
    ElMessage.error(e.response?.data?.error || t('apiTesting.scheduledTask.apifoxLoadFailed'))
  } finally {
    fetchingApifoxScenarios.value = false
  }
}

const openScenarioSelector = async () => {
  if (apifoxScenarios.value.length === 0) {
    await fetchApifoxScenarios()
  }
  tempSelectedScenarioIds.value = [...taskForm.apifox_scenario_ids]
  scenarioSearchText.value = ''
  showScenarioSelector.value = true
}

const handleScenarioSelectionChange = (selection) => {
  tempSelectedScenarioIds.value = selection.map(s => s.id)
}

const confirmScenarioSelection = () => {
  taskForm.apifox_scenario_ids = [...tempSelectedScenarioIds.value]
  showScenarioSelector.value = false
  ElMessage.success(t('apiTesting.scheduledTask.apifoxSelectedCount', { count: taskForm.apifox_scenario_ids.length }))
}

const cancelScenarioSelection = () => {
  showScenarioSelector.value = false
}

const removeScenario = (sid) => {
  const idx = taskForm.apifox_scenario_ids.indexOf(sid)
  if (idx > -1) {
    taskForm.apifox_scenario_ids.splice(idx, 1)
  }
}

const getScenarioName = (sid) => {
  return apifoxScenarioNameMap.value[sid] || `场景_${sid}`
}

// 加载 Apifox 配置
const loadApifoxConfig = async () => {
  try {
    const res = await getApifoxConfig()
    if (res.data) {
      if (!taskForm.apifox_config.project_id && res.data.project_id) {
        taskForm.apifox_config.project_id = res.data.project_id
      }
      if (!taskForm.apifox_config.environment_id && res.data.environment_id) {
        taskForm.apifox_config.environment_id = res.data.environment_id
      }
    }
  } catch (e) {
    // 静默失败，配置可能不存在
  }
}
</script>

<style lang="scss" scoped>
// 页面容器
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  line-height: 24px;
  gap: 20px;
}

// 筛选栏
.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;

  :deep(.el-input__wrapper),
  :deep(.el-select .el-input__wrapper) {
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
    border-radius: 8px;
    background: #ffffff;

    &:hover,
    &:focus {
      box-shadow: 0 0 0 1px #7b42f6;
    }
  }

  :deep(.el-input__inner) {
    color: #5a32a3;
    font-weight: 500;
  }

  .filter-bar-spacer {
    flex: 1;
  }

  .create-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;

    .el-icon {
      margin-right: 6px;
    }

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 20px rgba(123, 66, 246, 0.4) !important;
    }
  }
}

// 表格容器
.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;

  // 任务类型徽章样式
  .task-type-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.3s ease;
    white-space: nowrap;

    &.test-suite {
      background: #f6ffed;
      color: #52c41a;
    }

    &.api-request {
      background: #e6f7ff;
      color: #1890ff;
    }

    &.apifox-scenario {
      background: #f9f0ff;
      color: #722ed1;
    }

    &.default {
      background: #f5f5f5;
      color: #8c8c8c;
    }
  }

  // 通知类型徽章样式
  .notification-type-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.3s ease;
    white-space: nowrap;

    &.email {
      background: #f5f5f5;
      color: #8c8c8c;
    }

    &.webhook {
      background: #e6f7ff;
      color: #1890ff;
    }

    &.both {
      background: #fff7e6;
      color: #fa8c16;
    }
  }

  // 触发器类型徽章样式
  .trigger-type-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.3s ease;
    white-space: nowrap;
    background: #f5f5f5;
    color: #8c8c8c;
  }

  // 状态徽章样式
  .status-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.3s ease;
    white-space: nowrap;

    &.active {
      background: #f6ffed;
      color: #52c41a;
    }

    &.paused {
      background: #fff7e6;
      color: #fa8c16;
    }

    &.completed {
      background: #e6f7ff;
      color: #1890ff;
    }

    &.failed {
      background: #fff1f0;
      color: #ff4d4f;
    }

    &.default {
      background: #f5f5f5;
      color: #8c8c8c;
    }
  }

  // 表格样式
  .el-table {
    border: none;
    border-radius: 8px 8px 0 0;
    overflow: hidden;
    min-height: 200px;
    box-shadow: none;
    transition: all 0.3s ease;
    background-color: transparent !important;

    --el-color-primary: #667eea;
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
    --el-text-color-primary: #262626;
    --el-text-color-regular: #595959;
    --el-text-color-secondary: #8c8c8c;
    --el-text-color-placeholder: #999;
    --el-table-header-bg-color: #ffffff;
    --el-table-row-hover-bg-color: #f8f7ff;
    --el-table-stripe-bg-color: #fafaff;

    &::before {
      display: none;
    }

    :deep(.el-table__header-wrapper) {
      background-color: #ffffff !important;

      :deep(.el-table__header) {
        background-color: #ffffff !important;

        :deep(th) {
          background-color: #ffffff !important;
          color: #5a32a3;
          font-weight: 600;
          font-size: 14px;
          border-bottom: 1px solid #e9ecef;
          padding: 16px;
          text-align: center;
          line-height: 24px;
          transition: all 0.3s ease;

          &:hover {
            background-color: #ffffff !important;
          }

          :deep(.cell) {
            background-color: #ffffff !important;
            color: #5a32a3 !important;
            font-weight: 600 !important;
          }
        }
      }
    }

    :deep(.el-table__body-wrapper) {
      background-color: #ffffff !important;

      :deep(.el-table__row) {
        transition: all 0.3s ease;
        background-color: #ffffff !important;
        line-height: 24px;

        &:hover {
          background-color: #f8f7ff !important;
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(147, 112, 219, 0.1);
        }

        &.el-table__row--striped {
          background-color: #fafaff !important;
        }

        :deep(td) {
          padding: 14px 8px;
          border-bottom: 1px solid #e9ecef;
          color: #595959;
          font-size: 14px;
          font-weight: normal;
          line-height: 24px;
          transition: all 0.3s ease;

          :deep(.cell) {
            font-size: 14px;
            font-weight: normal;
            color: #595959;
            line-height: 24px;
            white-space: nowrap;
            overflow: visible;
          }
        }
      }
    }

    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;

      :deep(.el-table__empty-text) {
        color: #666;
        font-size: 14px;
        line-height: 24px;
      }
    }

    :deep(.el-table__header th) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }

    :deep(.el-table__header th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }
  }
}

// 操作按钮容器
.action-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
}

// 操作按钮样式
.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px !important;
  border-radius: 6px;
  transition: all 0.3s ease;

  .el-icon {
    font-size: 14px;
  }

  span {
    font-size: 12px;
  }

  &.run-btn {
    background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
    }
  }

  &.edit-btn {
    background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #40a9ff 0%, #1890ff 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
    }
  }

  &.pause-btn {
    background: linear-gradient(135deg, #faad14 0%, #d48806 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ffc53d 0%, #faad14 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(250, 173, 20, 0.4);
    }
  }

  &.resume-btn {
    background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
    }
  }

  &.log-btn {
    background: linear-gradient(135deg, #722ed1 0%, #531dab 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #9254de 0%, #722ed1 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(114, 46, 209, 0.4);
    }
  }

  &.delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(255, 77, 79, 0.4);
    }
  }
}

// 分页容器
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

    .el-pagination__total {
      color: #6b7280;
      font-size: 14px;
      font-weight: 500;
      margin-right: 12px;
    }

    .el-pagination__sizes {
      margin-right: 12px;

      .el-select {
        .el-input__wrapper {
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          background: #ffffff;
          box-shadow: none;

          &:hover {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
          }

          &.is-focus {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
          }
        }

        .el-input__inner {
          color: #374151;
          font-weight: 500;
        }
      }
    }

    .btn-prev,
    .btn-next {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      border: 1px solid #e5e7eb;
      background: #ffffff;
      color: #6b7280;
      transition: all 0.3s ease;

      &:hover:not(:disabled) {
        background: #f5f3ff;
        border-color: #a78bfa;
        color: #8b5cf6;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
      }

      &:disabled {
        background: #f5f5f5;
        border-color: #e0e0e0;
        color: #c0c0c0;
      }

      .el-icon {
        font-size: 14px;
        font-weight: bold;
      }
    }

    .el-pager {
      display: flex;
      gap: 8px;

      li {
        min-width: 32px;
        height: 32px;
        padding: 0 8px;
        border-radius: 8px;
        border: 1px solid #d1d5db;
        background: #ffffff;
        color: #6b7280;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;

        &:hover:not(.is-active) {
          background: #f5f3ff;
          border-color: #a78bfa;
          color: #8b5cf6;
          transform: translateY(-1px);
        }

        &.is-active {
          background: #f5f3ff;
          border-color: #a78bfa;
          color: #8b5cf6;
          box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
        }

        &.is-active:hover {
          background: #ede9fe;
          border-color: #8b5cf6;
        }
      }
    }

    .el-pagination__jump {
      color: #6b7280;
      font-weight: 500;
      margin-left: 12px;

      .el-input {
        width: 50px;
        margin: 0 4px;

        .el-input__wrapper {
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          background: #ffffff;
          box-shadow: none;

          &:hover {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
          }

          &.is-focus {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
          }
        }

        .el-input__inner {
          color: #374151;
          font-weight: 500;
          text-align: center;
        }
      }
    }
  }
}

// Apifox 配置区域样式
.apifox-config-section {
  display: flex;
  flex-direction: column;
  gap: 0;
  width: 100%;

  .el-form-item {
    margin-bottom: 12px;
  }
}

// Apifox 场景选择区域样式
.apifox-scenario-section {
  width: 100%;

  .scenario-selector {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
  }

  .selected-scenarios {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    min-height: 40px;
    padding: 8px;
    background: #f8f7ff;
    border-radius: 8px;
    border: 1px dashed rgba(147, 112, 219, 0.3);

    .scenario-tag {
      margin: 0;
    }
  }

  .no-scenarios-tip {
    color: #999;
    font-size: 13px;
    padding: 12px;
    background: #fafafa;
    border-radius: 8px;
    text-align: center;
  }
}

// 场景选择对话框样式
.scenario-selector-content {
  .selector-tip {
    padding: 8px 12px;
    background: #fffbe6;
    border-radius: 6px;
    color: #fa8c16;
    font-size: 13px;
    margin-bottom: 12px;
  }

  .selector-search {
    margin-bottom: 12px;
  }

  .selector-table {
    margin-bottom: 12px;
  }

  .selector-footer {
    text-align: right;
    color: #666;
    font-size: 13px;
  }
}

// Cron帮助图标样式
:deep(.cron-help-icon) {
  margin-left: 6px;
  font-size: 20px;
  color: #7b42f6;
  cursor: pointer;
  padding: 2px;
  border-radius: 50%;
  transition: all 0.3s ease;
  vertical-align: baseline;

  &:hover {
    background: rgba(123, 66, 246, 0.1);
    transform: scale(1.1);
  }
}

// 单位样式
.unit {
  margin-left: 8px;
  color: #606266;
}

// 对话框底部按钮样式
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;

  .cancel-btn {
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: 500;
  }

  .save-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }
  }
}
</style>
