<template>
  <div class="page-container">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <el-select
          v-model="selectedProject"
          :placeholder="$t('apiTesting.common.selectProject')"
          @change="onProjectChange"
          class="project-select"
          popper-class="purple-select-dropdown"
        >
          <el-option
            v-for="project in httpProjects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
        <el-select
          v-model="selectedReviewStatus"
          placeholder="评审状态"
          clearable
          @change="onFilterChange"
          class="filter-select"
          popper-class="purple-select-dropdown"
        >
          <el-option label="全部" value="" />
          <el-option label="待评审" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已拒绝" value="rejected" />
        </el-select>
        <el-date-picker
          v-model="selectedMonthRange"
          type="monthrange"
          range-separator="至"
          start-placeholder="开始月份"
          end-placeholder="结束月份"
          value-format="YYYY-MM"
          @change="onFilterChange"
          class="month-range-picker"
          popper-class="purple-date-picker"
        />
      </div>
      <div class="header-actions">
        <el-button
          v-if="selectedSuites.length > 0"
          type="danger"
          class="batch-delete-btn"
          @click="handleBatchDelete"
        >
          <el-icon style="margin-right: 4px;"><Delete /></el-icon>
          批量删除 ({{ selectedSuites.length }})
        </el-button>
        <el-button type="primary" @click="showCreateSuiteDialog = true" class="create-btn">
          <el-icon><Plus /></el-icon>
          {{ $t('apiTesting.automation.createSuite') }}
        </el-button>
      </div>
    </div>

    <!-- 测试套件表格列表 -->
    <div class="card-container">
      <el-table :data="testSuites" v-loading="loading" style="width: 100%" class="custom-table" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" header-align="center" align="center" />
        <el-table-column label="序号" width="90" header-align="center" align="center">
          <template #default="{ $index }">
            {{ (currentPage - 1) * pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="name" :label="$t('apiTesting.automation.suiteName')" min-width="180" header-align="center" align="center" show-overflow-tooltip>
          <template #default="scope">
            <span>{{ scope.row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('apiTesting.automation.executionEnvironment')" width="150" header-align="center" align="center">
          <template #default="scope">
            <span class="status-badge" :class="scope.row.environment ? 'environment' : 'no-environment'">
              {{ getEnvironmentName(scope.row.environment) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="评审状态" width="150" header-align="center" align="center">
          <template #default="scope">
            <span class="status-badge" :class="getReviewStatusClass(scope.row.review_status)">
              {{ getReviewStatusText(scope.row.review_status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="关联主线用例" min-width="160" header-align="center" align="center">
          <template #default="scope">
            <template v-if="scope.row.mainline_test_case">
              <el-tooltip :content="scope.row.mainline_test_case.title" placement="top">
                <span
                  class="status-badge mainline-badge linked-badge"
                  @click="goToTestCase(scope.row.mainline_test_case.id)"
                >
                  <span class="badge-text">{{ scope.row.mainline_test_case.title }}</span>
                  <span v-if="scope.row.mainline_case_updated" class="badge-dot"></span>
                </span>
              </el-tooltip>
            </template>
            <span v-else class="status-badge mainline-badge unlinked-badge">未关联</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('apiTesting.automation.creator')" width="100" header-align="center" align="center">
          <template #default="scope">
            {{ scope.row.created_by?.username }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="$t('apiTesting.automation.createTime')" width="210" header-align="center" align="center">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('apiTesting.common.operation')" width="320" fixed="right" header-align="center" align="center">
          <template #default="scope">
            <div class="action-buttons">
              <el-button size="small" type="primary" class="action-btn view-btn" @click="goToSuiteDetail(scope.row.id)">
                <el-icon><View /></el-icon>
                <span>{{ $t('apiTesting.common.view') }}</span>
              </el-button>
              <el-button
                v-if="!scope.row.mainline_test_case"
                size="small"
                type="success"
                class="action-btn link-btn"
                @click="openLinkMainlineDialog(scope.row)"
              >
                <el-icon><Link /></el-icon>
                <span>关联</span>
              </el-button>
              <el-button
                v-else
                size="small"
                type="danger"
                class="action-btn unlink-btn"
                @click="handleUnlinkMainline(scope.row)"
                :loading="scope.row._unlinking"
              >
                <el-icon><Link /></el-icon>
                <span>取消</span>
              </el-button>
              <el-button size="small" type="warning" class="action-btn edit-btn" @click="editSuite(scope.row)">
                <el-icon><Edit /></el-icon>
                <span>{{ $t('apiTesting.common.edit') }}</span>
              </el-button>
              <el-button
                v-if="scope.row.mainline_test_case && scope.row.mainline_case_updated"
                size="small"
                class="action-btn update-btn"
                @click="openConfirmMainlineDialog(scope.row)"
              >
                <el-icon><Warning /></el-icon>
                <span>确认</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container" v-if="testSuites.length > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 关联主线用例对话框 -->
    <el-dialog
      v-model="linkMainlineDialogVisible"
      title="关联主线用例"
      width="900px"
      :close-on-click-modal="false"
      class="purple-dialog link-mainline-dialog"
    >
      <div class="link-dialog-content">
        <div class="link-dialog-info">
          <p class="suite-title">场景：<strong>{{ linkingSuite?.name }}</strong></p>
        </div>
        <div class="link-dialog-search">
          <el-input
            v-model="mainlineSearchText"
            placeholder="搜索主线用例标题..."
            clearable
            @input="fetchAvailableMainlines"
            style="margin-bottom: 12px;"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        <el-table
          :data="availableMainlines"
          v-loading="loadingMainlines"
          max-height="360"
          highlight-current-row
          @current-change="handleMainlineSelect"
          style="width: 100%"
        >
          <el-table-column label="" width="50" align="center">
            <template #default="{ row }">
              <el-radio
                :model-value="selectedMainlineId"
                :value="row.id"
                @change="handleMainlineSelect(row)"
              />
            </template>
          </el-table-column>
          <el-table-column label="用例标题" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">
              <span>{{ row.title }}</span>
              <el-tag v-if="row.is_linked" size="small" type="success" style="margin-left: 8px;">已关联</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="所属模块" width="130" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.module || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="用例级别" width="90" align="center">
            <template #default="{ row }">
              <span class="status-badge" :class="row.priority">
                {{ getPriorityText(row.priority) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="创建人" width="100" align="center">
            <template #default="{ row }">
              {{ row.author?.username || '-' }}
            </template>
          </el-table-column>
        </el-table>
        <div v-if="availableMainlines.length === 0 && !loadingMainlines" class="empty-hint">
          暂无可关联的主线用例
        </div>
        <div v-if="mainlineTotal > 0" class="pagination-container">
          <el-pagination
            v-model:current-page="mainlineCurrentPage"
            v-model:page-size="mainlinePageSize"
            :total="mainlineTotal"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="handleMainlinePageChange"
            @size-change="handleMainlineSizeChange"
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="linkMainlineDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!selectedMainlineId"
          :loading="linkingMainline"
          @click="handleLinkMainline"
        >
          确认关联
        </el-button>
      </template>
    </el-dialog>

    <!-- 确认主线用例一致性对话框 -->
    <el-dialog
      v-model="confirmMainlineDialogVisible"
      title="确认主线用例一致性"
      width="500px"
      :close-on-click-modal="false"
      class="purple-dialog confirm-mainline-dialog"
    >
      <div class="confirm-mainline-content">
        <p class="confirm-tip">
          场景 <strong>"{{ confirmingSuite?.name }}"</strong> 关联的主线用例
          <strong>"{{ confirmingSuite?.mainline_test_case?.title }}"</strong> 已发生更新。
        </p>
        <p class="confirm-question">请确认当前场景是否仍与该主线用例保持一致？</p>
      </div>
      <template #footer>
        <el-button @click="confirmMainlineDialogVisible = false">不一致</el-button>
        <el-button
          type="primary"
          :loading="confirmingMainline"
          @click="handleConfirmMainline"
        >
          一致
        </el-button>
      </template>
    </el-dialog>

    <!-- 创建/编辑测试套件对话框 -->
    <el-dialog
      v-model="showCreateSuiteDialog"
      :title="editingSuite ? $t('apiTesting.automation.editSuite') : $t('apiTesting.automation.createSuite')"
      width="600px"
      @close="resetSuiteForm"
      class="purple-dialog"
    >
      <el-form
        ref="suiteFormRef"
        :model="suiteForm"
        :rules="suiteRules"
        label-width="100px"
      >
        <el-form-item :label="$t('apiTesting.automation.suiteName')" prop="name">
          <el-input v-model="suiteForm.name" :placeholder="$t('apiTesting.automation.inputSuiteName')" />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.suiteDescription')" prop="description">
          <el-input
            v-model="suiteForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('apiTesting.automation.inputSuiteDescription')"
          />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.belongProject')" prop="project">
          <el-select v-model="suiteForm.project" :placeholder="$t('apiTesting.automation.selectProject')" class="full-width">
            <el-option
              v-for="project in httpProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.executionEnvironment')" prop="environment">
          <el-select v-model="suiteForm.environment" :placeholder="$t('apiTesting.automation.selectEnvironment')" clearable class="full-width">
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateSuiteDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="submitSuiteForm" :loading="submittingSuite">
          {{ editingSuite ? $t('apiTesting.common.update') : $t('apiTesting.common.create') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 执行结果对话框 -->
    <el-dialog
      v-model="showExecutionDialog"
      :title="$t('apiTesting.automation.testExecutionResult')"
      width="80%"
      :top="'5vh'"
      class="purple-dialog"
    >
      <div v-if="currentExecution" class="execution-detail">
        <div class="execution-summary">
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.totalRequests')" :value="currentExecution.total_requests" />
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.passedCount')" :value="currentExecution.passed_requests" />
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.failedCount')" :value="currentExecution.failed_requests" />
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.passRate')" :value="getPassRate(currentExecution)" suffix="%" />
            </el-col>
          </el-row>
        </div>

        <div class="execution-results">
          <h4>{{ $t('apiTesting.automation.detailedResults') }}</h4>
          <el-table :data="formatExecutionResults(currentExecution.results)" style="width: 100%" class="custom-table">
            <el-table-column prop="name" :label="$t('apiTesting.automation.requestName')" min-width="150" />
            <el-table-column prop="method" :label="$t('apiTesting.automation.method')" width="80" align="center">
              <template #default="scope">
                <span class="method-badge" :class="scope.row.method?.toLowerCase()">
                  {{ scope.row.method }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="status" :label="$t('apiTesting.automation.result')" width="80" align="center">
              <template #default="scope">
                <span class="result-badge" :class="scope.row.passed ? 'passed' : 'failed'">
                  {{ scope.row.passed ? $t('apiTesting.automation.testStatus.passed') : $t('apiTesting.automation.testStatus.failed') }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="status_code" :label="$t('apiTesting.automation.statusCode')" width="100" align="center" />
            <el-table-column prop="response_time" :label="$t('apiTesting.automation.responseTime')" width="100" align="center">
              <template #default="scope">
                {{ scope.row.response_time?.toFixed(0) }}ms
              </template>
            </el-table-column>
            <el-table-column prop="error" :label="$t('apiTesting.automation.errorMessage')" min-width="150" show-overflow-tooltip />
          </el-table>
        </div>
      </div>

      <template #footer>
        <el-button @click="showExecutionDialog = false">{{ $t('apiTesting.common.close') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import {
  linkAutomationSuiteMainline,
  unlinkAutomationSuiteMainline,
  getAutomationSuiteAvailableMainlines,
  confirmAutomationSuiteMainline
} from '@/api/automation-suites'
import { Plus, MoreFilled, Document, User, Clock, VideoPlay, Edit, CopyDocument, Delete, View, Search, Link, Warning } from '@element-plus/icons-vue'

const router = useRouter()
const { t } = useI18n()

// 数据
const projects = ref([])
const selectedProject = ref(null)
const testSuites = ref([])
const environments = ref([])
const loading = ref(false)
const running = ref(false)
const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)
const selectedSuites = ref([])

// 筛选条件
const selectedReviewStatus = ref('')
const selectedMonthRange = ref([])

// 对话框状态
const showCreateSuiteDialog = ref(false)
const showExecutionDialog = ref(false)
const submittingSuite = ref(false)
const editingSuite = ref(null)
const currentExecution = ref(null)

// 确认主线用例一致性弹窗
const confirmMainlineDialogVisible = ref(false)
const confirmingSuite = ref(null)
const confirmingMainline = ref(false)

// 关联主线用例弹窗
const linkMainlineDialogVisible = ref(false)
const linkingSuite = ref(null)
const mainlineSearchText = ref('')
const availableMainlines = ref([])
const loadingMainlines = ref(false)
const selectedMainlineId = ref(null)
const linkingMainline = ref(false)
const mainlineCurrentPage = ref(1)
const mainlinePageSize = ref(20)
const mainlineTotal = ref(0)

// 表单
const suiteFormRef = ref(null)
const suiteForm = ref({
  name: '',
  description: '',
  project: null,
  environment: null
})

const suiteRules = {
  name: [{ required: true, message: t('apiTesting.automation.inputSuiteName'), trigger: 'blur' }],
  project: [{ required: true, message: t('apiTesting.automation.selectProject'), trigger: 'change' }]
}

// 计算属性
const httpProjects = computed(() => {
  return projects.value.filter(project => project.project_type !== 'WEBSOCKET')
})

// 方法
const getPassRate = (execution) => {
  if (!execution || execution.total_requests === 0) return 0
  return Math.round((execution.passed_requests / execution.total_requests) * 100)
}

const getEnvironmentName = (environment) => {
  if (!environment) return t('apiTesting.automation.noEnvironment')
  if (typeof environment === 'object' && environment.name) {
    return environment.name
  }
  const env = environments.value.find(e => e.id === environment)
  return env ? env.name : t('apiTesting.automation.noEnvironment')
}

const getProjectName = (projectId) => {
  if (!projectId) return '-'
  const project = projects.value.find(p => p.id === projectId)
  return project ? project.name : '-'
}

const formatDate = (date) => {
  if (!date) return ''
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

const getReviewStatusClass = (status) => {
  switch (status) {
    case 'approved':
      return 'success'
    case 'rejected':
      return 'failed'
    case 'partial':
      return 'processing'
    default:
      return 'pending'
  }
}

const getReviewStatusText = (status) => {
  switch (status) {
    case 'approved':
      return '已通过'
    case 'rejected':
      return '已拒绝'
    case 'partial':
      return '部分通过'
    default:
      return '待评审'
  }
}

const formatExecutionResults = (results) => {
  if (!results || !Array.isArray(results)) return []
  return results
}

const loadProjects = async () => {
  try {
    const response = await api.get('/api-testing/projects/')
    projects.value = response.data.results || response.data

    const httpProjectsList = projects.value.filter(project => project.project_type !== 'WEBSOCKET')

    if (httpProjectsList.length > 0 && !selectedProject.value) {
      selectedProject.value = httpProjectsList[0].id
      await onProjectChange()
    }
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadProjects'))
  }
}

const loadTestSuites = async () => {
  if (!selectedProject.value) return

  loading.value = true
  try {
    // 构建查询参数
    const params = {
      project: selectedProject.value,
      page: currentPage.value,
      page_size: pageSize.value
    }

    // 添加评审状态筛选
    if (selectedReviewStatus.value) {
      params.review_status = selectedReviewStatus.value
    }

    // 添加月份范围筛选
    if (selectedMonthRange.value && selectedMonthRange.value.length === 2) {
      params.created_after = selectedMonthRange.value[0] + '-01'
      // 获取结束月份的最后一天
      const [year, month] = selectedMonthRange.value[1].split('-')
      const lastDay = new Date(year, month, 0).getDate()
      params.created_before = selectedMonthRange.value[1] + '-' + lastDay
    }

    const response = await api.get('/api-testing/test-suites/', { params })
    const suites = response.data.results || response.data
    total.value = response.data.count || suites.length

    // 为每个套件加载评审摘要
    const suitesWithReviewStatus = await Promise.all(
      suites.map(async (suite) => {
        try {
          const reviewResponse = await api.get(`/api-testing/test-suites/${suite.id}/review_summary/`)
          return {
            ...suite,
            review_status: reviewResponse.data.overall_status,
            review_summary: reviewResponse.data
          }
        } catch (e) {
          return {
            ...suite,
            review_status: 'pending',
            review_summary: null
          }
        }
      })
    )
    testSuites.value = suitesWithReviewStatus
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadTestSuites'))
  } finally {
    loading.value = false
  }
}

const loadEnvironments = async () => {
  try {
    const response = await api.get('/api-testing/environments/')
    const allEnvironments = response.data.results || response.data
    environments.value = allEnvironments.filter(env =>
      env.scope === 'GLOBAL' ||
      (env.scope === 'LOCAL' && (!selectedProject.value || env.project === selectedProject.value))
    )
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadEnvironments'))
  }
}

const onProjectChange = async () => {
  currentPage.value = 1
  // 清空筛选条件
  selectedReviewStatus.value = ''
  selectedMonthRange.value = []
  const selectedProjectData = projects.value.find(p => p.id === selectedProject.value)
  if (selectedProjectData && selectedProjectData.project_type === 'WEBSOCKET') {
    ElMessage.warning(t('apiTesting.messages.warning.websocketNotSupported'))
    const httpProjectsList = projects.value.filter(project => project.project_type !== 'WEBSOCKET')
    if (httpProjectsList.length > 0) {
      selectedProject.value = httpProjectsList[0].id
    } else {
      selectedProject.value = null
    }
    return
  }

  await Promise.all([
    loadTestSuites(),
    loadEnvironments()
  ])
}

const onFilterChange = () => {
  currentPage.value = 1
  loadTestSuites()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  loadTestSuites()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  loadTestSuites()
}

const goToSuiteDetail = (suiteId) => {
  router.push(`/api-testing/automation/${suiteId}`)
}

const goToTestCase = (testCaseId) => {
  router.push(`/ai-generation/testcases/${testCaseId}`)
}

// ========== 关联/取消关联主线用例 ==========

const openLinkMainlineDialog = async (suite) => {
  linkingSuite.value = suite
  selectedMainlineId.value = null
  mainlineSearchText.value = ''
  mainlineCurrentPage.value = 1
  linkMainlineDialogVisible.value = true
  await fetchAvailableMainlines()
}

const fetchAvailableMainlines = async () => {
  if (!linkingSuite.value) return
  loadingMainlines.value = true
  try {
    const params = {
      page: mainlineCurrentPage.value,
      page_size: mainlinePageSize.value
    }
    if (mainlineSearchText.value) {
      params.search = mainlineSearchText.value
    }
    const res = await getAutomationSuiteAvailableMainlines(linkingSuite.value.id, params)
    availableMainlines.value = res.data?.results || []
    mainlineTotal.value = res.data?.count || 0
  } catch (error) {
    console.error('获取可用主线用例失败:', error)
    ElMessage.error('获取可用主线用例列表失败')
  } finally {
    loadingMainlines.value = false
  }
}

const handleMainlinePageChange = (page) => {
  mainlineCurrentPage.value = page
  fetchAvailableMainlines()
}

const handleMainlineSizeChange = (size) => {
  mainlinePageSize.value = size
  mainlineCurrentPage.value = 1
  fetchAvailableMainlines()
}

const handleMainlineSelect = (row) => {
  if (row) {
    selectedMainlineId.value = row.id
  }
}

const getPriorityText = (priority) => {
  const textMap = {
    critical: 'P0',
    high: 'P1',
    medium: 'P2',
    low: 'P3'
  }
  return textMap[priority] || priority || '-'
}

const handleLinkMainline = async () => {
  if (!selectedMainlineId.value || !linkingSuite.value) return
  linkingMainline.value = true
  try {
    await linkAutomationSuiteMainline(linkingSuite.value.id, selectedMainlineId.value)
    ElMessage.success('关联成功')
    linkMainlineDialogVisible.value = false
    await loadTestSuites()
  } catch (error) {
    const msg = error.response?.data?.error || '关联失败'
    ElMessage.error(msg)
  } finally {
    linkingMainline.value = false
  }
}

const openConfirmMainlineDialog = (suite) => {
  confirmingSuite.value = suite
  confirmMainlineDialogVisible.value = true
}

const handleConfirmMainline = async () => {
  if (!confirmingSuite.value) return
  confirmingMainline.value = true
  try {
    await confirmAutomationSuiteMainline(confirmingSuite.value.id)
    ElMessage.success('已确认场景与主线用例一致')
    confirmMainlineDialogVisible.value = false
    await loadTestSuites()
  } catch (error) {
    const msg = error.response?.data?.error || '确认失败'
    ElMessage.error(msg)
  } finally {
    confirmingMainline.value = false
  }
}

const handleUnlinkMainline = async (suite) => {
  try {
    await ElMessageBox.confirm(
      `确定要取消场景 "${suite.name}" 与用例 "${suite.mainline_test_case.title}" 的关联吗？`,
      '取消关联',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    suite._unlinking = true
    await unlinkAutomationSuiteMainline(suite.id)
    ElMessage.success('已取消关联')
    await loadTestSuites()
  } catch (error) {
    if (error !== 'cancel') {
      const msg = error.response?.data?.error || '取消关联失败'
      ElMessage.error(msg)
    }
  } finally {
    suite._unlinking = false
  }
}

const handleMoreAction = (command, suite) => {
  switch (command) {
    case 'edit':
      editSuite(suite)
      break
    case 'delete':
      deleteSuite(suite)
      break
  }
}

const handleSuiteAction = async ({ action, suite }) => {
  switch (action) {
    case 'run':
      await runTestSuite(suite)
      break
    case 'edit':
      editSuite(suite)
      break
    case 'duplicate':
      await duplicateSuite(suite)
      break
    case 'delete':
      await deleteSuite(suite)
      break
  }
}

const runTestSuite = async (suite) => {
  running.value = true
  try {
    const response = await api.post(`/api-testing/test-suites/${suite.id}/execute/`)
    currentExecution.value = response.data
    showExecutionDialog.value = true
    ElMessage.success(t('apiTesting.messages.success.suiteExecuted'))
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.executeSuite'))
  } finally {
    running.value = false
  }
}

const editSuite = (suite) => {
  editingSuite.value = suite
  suiteForm.value.name = suite.name
  suiteForm.value.description = suite.description
  suiteForm.value.project = suite.project
  suiteForm.value.environment = suite.environment?.id || null
  showCreateSuiteDialog.value = true
}

const duplicateSuite = async (suite) => {
  try {
    const newSuite = {
      name: `${suite.name} - ${t('apiTesting.common.copyText')}`,
      description: suite.description,
      project: suite.project,
      environment_id: suite.environment?.id || null
    }
    await api.post('/api-testing/test-suites/', newSuite)
    ElMessage.success(t('apiTesting.messages.success.copy'))
    await loadTestSuites()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.copyFailed'))
  }
}

const deleteSuite = async (suite) => {
  try {
    await ElMessageBox.confirm(
      t('apiTesting.automation.confirmDeleteSuite', { name: suite.name }),
      t('apiTesting.messages.confirm.deleteTitle'),
      {
        confirmButtonText: t('apiTesting.common.confirm'),
        cancelButtonText: t('apiTesting.common.cancel'),
        type: 'warning'
      }
    )

    await api.delete(`/api-testing/test-suites/${suite.id}/`)
    ElMessage.success(t('apiTesting.messages.success.delete'))
    await loadTestSuites()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('apiTesting.messages.error.deleteFailed'))
    }
  }
}

const handleSelectionChange = (selection) => {
  selectedSuites.value = selection
}

const handleBatchDelete = async () => {
  if (selectedSuites.value.length === 0) {
    ElMessage.warning('请先选择要删除的测试场景')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedSuites.value.length} 个测试场景吗？`,
      '确认批量删除',
      {
        confirmButtonText: t('apiTesting.common.confirm'),
        cancelButtonText: t('apiTesting.common.cancel'),
        type: 'warning'
      }
    )

    const deletePromises = selectedSuites.value.map(suite =>
      api.delete(`/api-testing/test-suites/${suite.id}/`)
    )

    await Promise.all(deletePromises)
    ElMessage.success(`成功删除 ${selectedSuites.value.length} 个测试场景`)
    selectedSuites.value = []
    await loadTestSuites()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('apiTesting.messages.error.deleteFailed'))
    }
  }
}

const submitSuiteForm = async () => {
  if (!suiteFormRef.value) return

  const valid = await suiteFormRef.value.validate().catch(() => false)
  if (!valid) return

  submittingSuite.value = true
  try {
    const submitData = {
      name: suiteForm.value.name,
      description: suiteForm.value.description,
      project: suiteForm.value.project,
      environment_id: suiteForm.value.environment
    }

    if (editingSuite.value) {
      await api.put(`/api-testing/test-suites/${editingSuite.value.id}/`, submitData)
      ElMessage.success(t('apiTesting.messages.success.suiteUpdated'))
    } else {
      await api.post('/api-testing/test-suites/', submitData)
      ElMessage.success(t('apiTesting.messages.success.suiteCreated'))
    }

    showCreateSuiteDialog.value = false
    await loadTestSuites()
  } catch (error) {
    ElMessage.error(editingSuite.value ? t('apiTesting.messages.error.updateFailed') : t('apiTesting.messages.error.createFailed'))
  } finally {
    submittingSuite.value = false
  }
}

const resetSuiteForm = () => {
  editingSuite.value = null
  suiteForm.value = {
    name: '',
    description: '',
    project: selectedProject.value,
    environment: null
  }
  suiteFormRef.value?.resetFields()
}

onMounted(() => {
  loadProjects()
})
</script>

<style lang="scss" scoped>
.page-container {
  --primary-color: #7b42f6;
  --primary-light: #a78bfa;
  --primary-lighter: #c4b5fd;
  --primary-lightest: #f5f3ff;
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --text-primary: #1f2937;
  --text-secondary: #4b5563;
  --text-tertiary: #8c8c8c;

  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 20px 24px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .project-select {
    width: 240px;

    :deep(.el-input__wrapper) {
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
      border-radius: 8px;
      background-color: transparent;

      &:hover,
      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }
  }

  .filter-select {
    width: 140px;

    :deep(.el-input__wrapper) {
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
      border-radius: 8px;
      background-color: transparent;

      &:hover,
      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }
  }

  .month-range-picker {
    width: 280px;

    :deep(.el-input__wrapper) {
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
      border-radius: 8px;
      background-color: transparent;

      &:hover,
      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }
  }

  .create-btn {
    height: 36px;
    padding: 0 18px;
    border-radius: 8px;
    font-weight: 500;
    font-size: 14px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    background: #7b42f6;
    border: 1px solid #7b42f6;
    color: #ffffff;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);

    &:hover {
      background: #6d33e6;
      border-color: #6d33e6;
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
    }

    &:active {
      transform: translateY(0);
      background: #5a32a3;
    }

    .el-icon {
      margin-right: 6px;
      font-size: 16px;
    }
  }

  .batch-delete-btn {
    height: 36px;
    padding: 0 18px;
    border-radius: 8px;
    font-weight: 500;
    font-size: 14px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    background: #ff4d4f;
    border: 1px solid #ff4d4f;
    color: #ffffff;
    box-shadow: 0 4px 12px rgba(255, 77, 79, 0.3);

    &:hover {
      background: #f5222d;
      border-color: #f5222d;
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(255, 77, 79, 0.4);
    }

    &:active {
      transform: translateY(0);
      background: #cf1322;
    }

    .el-icon {
      margin-right: 6px;
      font-size: 16px;
    }
  }
}

.card-container {
  flex: 1;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;
}

.custom-table {
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

  // 表头样式
  :deep(.el-table__header-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__header) {
    background-color: #ffffff !important;
  }

  :deep(th) {
    background-color: #ffffff !important;
    color: #5a32a3 !important;
    font-weight: 600;
    font-size: 14px;
    border-bottom: 1px solid #e9ecef;
    padding: 16px !important;
    text-align: center;
    transition: all 0.3s ease;

    &:hover {
      background-color: #ffffff !important;
    }
  }

  :deep(th .cell) {
    background-color: #ffffff !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    line-height: 24px !important;
  }

  // 表格内容
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

  // 空状态
  :deep(.el-table__empty-block) {
    padding: 60px 0;
    background: #ffffff !important;

    :deep(.el-table__empty-text) {
      color: #666;
      font-size: 14px;
      line-height: 24px;
    }
  }

  // 修复固定列样式
  :deep(.el-table__fixed-right) {
    background-color: #ffffff !important;
    height: 100% !important;
  }

  :deep(.el-table__fixed-right-patch) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-body-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-header-wrapper) {
    background-color: #ffffff !important;
  }
}

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

  // 成功 - 绿色
  &.success {
    background: #f6ffed;
    color: #52c41a;
  }

  // 失败 - 红色
  &.failed {
    background: #fff2f0;
    color: #f5222d;
  }

  // 处理中 - 橙色
  &.processing {
    background: #fff7e6;
    color: #fa8c16;
  }

  // 待处理 - 灰色
  &.pending {
    background: #f5f5f5;
    color: #8c8c8c;
  }

  // 已通过 - 绿色
  &.approved {
    background: #f6ffed;
    color: #52c41a;
  }

  // 已拒绝 - 红色
  &.rejected {
    background: #fff2f0;
    color: #f5222d;
  }

  // 环境 - 紫色
  &.environment {
    background: #f9f0ff;
    color: #722ed1;
  }

  // 无环境 - 蓝色
  &.no-environment {
    background: #e6f7ff;
    color: #1890ff;
  }

  // 用例级别 - P3 低优先级
  &.low {
    background: #f6ffed;
    color: #52c41a;
  }

  // 用例级别 - P2 中优先级
  &.medium {
    background: #e6f7ff;
    color: #1890ff;
  }

  // 用例级别 - P1 高优先级
  &.high {
    background: #fff7e6;
    color: #fa8c16;
  }

  // 用例级别 - P0 严重优先级
  &.critical {
    background: #fff1f0;
    color: #f5222d;
    font-weight: 600;
  }
}

// 主线用例徽章样式
.mainline-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;

  .badge-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 120px;
  }

  .badge-dot {
    position: absolute;
    top: -2px;
    right: -2px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #f5222d;
    border: 2px solid #fff;
  }
}

.linked-badge {
  background: #e6f7ff;
  color: #1890ff;

  &:hover {
    background: #bae7ff;
    color: #096dd9;
  }
}

.unlinked-badge {
  background: #f5f5f5;
  color: #8c8c8c;
  cursor: default;

  &:hover {
    background: #f5f5f5;
    color: #8c8c8c;
  }
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

  /* 定义主题变量 - 浅紫色风格 */
  --primary-color: #a78bfa;
  --primary-dark: #8b5cf6;
  --primary-light: #f3f0ff;
  --text-primary: #262626;
  --text-secondary: #595959;
  --text-tertiary: #8c8c8c;

  /* 覆盖 Element Plus 默认主题变量 */
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

    // 总条数
    .el-pagination__total {
      color: #6b7280;
      font-size: 14px;
      font-weight: 500;
      margin-right: 12px;
    }

    // 每页条数选择器
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

    // 上一页/下一页按钮
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

    // 页码按钮
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

          &:hover {
            background: #ede9fe;
            border-color: #8b5cf6;
          }
        }
      }
    }

    // 跳转输入框
    .el-pagination__jump {
      margin-left: 12px;
      color: #6b7280;
      font-size: 14px;
      font-weight: 500;

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

.execution-detail {
  max-height: 70vh;
  overflow-y: auto;

  .execution-summary {
    margin-bottom: 24px;
    padding: 20px;
    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
    border-radius: 12px;
    border: 1px solid rgba(147, 112, 219, 0.15);

    :deep(.el-statistic) {
      text-align: center;

      .el-statistic__head {
        color: #6b7280;
        font-size: 14px;
        margin-bottom: 8px;
      }

      .el-statistic__content {
        color: #5a32a3;
        font-size: 28px;
        font-weight: 600;
      }
    }
  }

  .execution-results {
    h4 {
      margin: 0 0 16px 0;
      color: #5a32a3;
      font-size: 16px;
      font-weight: 600;
      padding-left: 12px;
      border-left: 3px solid #7b42f6;
    }

    .custom-table {
      border: none;
      border-radius: 8px;
      overflow: hidden;

      :deep(th) {
        background-color: #f9fafb !important;
        color: #5a32a3 !important;
        font-weight: 600;
        border-bottom: 1px solid rgba(147, 112, 219, 0.15);
      }

      :deep(td) {
        border-bottom: 1px solid rgba(147, 112, 219, 0.1);
      }

      :deep(.el-table__row) {
        &:hover {
          background-color: #f5f3ff !important;
        }
      }
    }
  }
}

.method-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;

  &.get {
    background: rgba(34, 197, 94, 0.15);
    color: #16a34a;
  }

  &.post {
    background: rgba(123, 66, 246, 0.15);
    color: #7b42f6;
  }

  &.put {
    background: rgba(245, 158, 11, 0.15);
    color: #d97706;
  }

  &.delete {
    background: rgba(239, 68, 68, 0.15);
    color: #dc2626;
  }

  &.patch {
    background: rgba(107, 114, 128, 0.15);
    color: #4b5563;
  }
}

.result-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;

  &.passed {
    background: rgba(34, 197, 94, 0.15);
    color: #16a34a;
  }

  &.failed {
    background: rgba(239, 68, 68, 0.15);
    color: #dc2626;
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

  .el-icon {
    font-size: 14px;
    color: #ffffff !important;
  }

  span {
    font-size: 12px;
    color: #ffffff !important;
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
    background: #fa8c16 !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: #ffb366 !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(250, 140, 22, 0.4);
    }
  }

  &.update-btn {
    background: linear-gradient(135deg, #ff9f43 0%, #ff6b35 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ffb366 0%, #ff7f50 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4);
    }
  }

  &.view-btn {
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

  &.delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
    }
  }

  &.link-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }
  }

  &.unlink-btn {
    background: linear-gradient(135deg, #ff7a45 0%, #ff4d4f 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ff9c6b 0%, #ff7875 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(255, 77, 79, 0.4);
    }
  }
}

// 关联主线用例相关样式
.mainline-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
}

.mainline-link {
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  color: #7b42f6;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    color: #6d33e6;
    text-decoration: underline;
  }
}

.text-muted {
  color: #999;
  font-size: 13px;
}

// 主线用例更新标识
.update-indicator {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #fff7e6;
  color: #fa8c16;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: #ffd8bf;
  }

  .el-icon {
    font-size: 12px;
  }
}

// 确认主线用例一致性弹窗样式
.confirm-mainline-dialog {
  .confirm-mainline-content {
    padding: 8px 4px;

    .confirm-tip {
      margin: 0 0 16px 0;
      font-size: 14px;
      line-height: 1.8;
      color: #333;

      strong {
        color: #7b42f6;
      }
    }

    .confirm-question {
      margin: 0;
      padding: 12px 16px;
      background: #f5f3ff;
      border-radius: 8px;
      border: 1px solid #e8e4ff;
      color: #5a32a3;
      font-size: 14px;
      font-weight: 500;
    }
  }
}

// 关联主线用例对话框样式
.link-mainline-dialog {
  .link-dialog-content {
    .link-dialog-info {
      margin-bottom: 16px;
      padding: 8px 16px;
      background: #f5f3ff;
      border-radius: 8px;
      border: 1px solid #e8e4ff;

      .suite-title {
        margin: 0;
        font-size: 14px;
        color: #5a32a3;
      }
    }

    .link-dialog-search {
      :deep(.el-input__wrapper) {
        border-radius: 8px;
        box-shadow: 0 0 0 1px #c4b5fd;
      }
    }

    .empty-hint {
      text-align: center;
      padding: 40px 0;
      color: #999;
      font-size: 14px;
    }
  }
}

// 响应式适配
@media screen and (max-width: 768px) {
  .page-container {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;

    .header-left {
      width: 100%;
      flex-wrap: wrap;

      .project-select,
      .filter-select,
      .month-range-picker {
        flex: 1;
        min-width: 140px;
      }
    }

    .create-btn {
      width: 100%;
    }
  }

  .action-buttons {
    flex-wrap: wrap;
    gap: 4px;
  }

  .action-btn {
    padding: 4px 8px !important;

    span {
      display: none;
    }

    .el-icon {
      margin: 0;
    }
  }
}
</style>

<style lang="scss">
// 下拉菜单样式
.purple-dropdown {
  .el-dropdown-menu__item {
    color: #4b5563;
    
    &:hover {
      background: rgba(123, 66, 246, 0.1);
      color: #7b42f6;
    }

    .el-icon {
      margin-right: 8px;
      color: #a78bfa;
    }

    &.delete-item {
      color: #ef4444;

      .el-icon {
        color: #ef4444;
      }

      &:hover {
        background: rgba(239, 68, 68, 0.1);
        color: #dc2626;
      }
    }
  }
}

// 选择器下拉样式
.purple-select-dropdown {
  .el-select-dropdown__item {
    &.selected {
      color: #7b42f6;
      font-weight: 600;
    }

    &:hover {
      background: rgba(123, 66, 246, 0.1);
    }
  }
}

// 对话框样式
.purple-dialog {
  .el-dialog {
    border-radius: 12px;
    box-shadow: 0 12px 24px rgba(147, 112, 219, 0.2);

    .el-dialog__header {
      background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
      padding: 20px 24px;
      border-bottom: 1px solid #ebeef5;
      margin: 0;

      .el-dialog__title {
        font-size: 18px;
        font-weight: 600;
        color: #5a32a3;
      }
    }

    .el-dialog__body {
      padding: 24px;

      .el-form {
        .el-form-item {
          margin-bottom: 20px;

          .el-form-item__label {
            color: #5a32a3;
            font-weight: 500;
          }

          .el-input__wrapper,
          .el-select .el-input__wrapper,
          .el-textarea__inner {
            box-shadow: none;
            border-radius: 8px;
            border: 1px solid rgba(147, 112, 219, 0.2);
            background-color: transparent;

            &:hover,
            &.is-focus {
              border-color: #7b42f6;
            }
          }

          .el-textarea__inner {
            &:focus {
              border-color: #7b42f6;
            }
          }

          .el-select {
            width: 100%;

            :deep(.el-select__wrapper) {
              background-color: #ffffff !important;
              box-shadow: none !important;
              border: 1px solid rgba(147, 112, 219, 0.2) !important;
              border-radius: 8px !important;

              &:hover,
              &.is-focused {
                border-color: #7b42f6 !important;
              }
            }
          }
        }
      }
    }

    .el-dialog__footer {
      padding: 16px 24px 20px;
      border-top: 1px solid #ebeef5;
      background: #fafafa;

      .el-button {
        font-weight: 500;
        padding: 8px 20px;
        border-radius: 8px;

        &.el-button--primary {
          background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
          border: none !important;
          color: white !important;
          font-weight: 600 !important;

          &:hover {
            background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
          }
        }
      }
    }
  }
}
</style>
