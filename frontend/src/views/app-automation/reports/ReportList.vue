<template>
  <div class="page-container">
    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- ==================== 套件报告 ==================== -->
      <el-tab-pane label="套件报告" name="suite">
        <!-- 统计 -->
        <div class="stats-row">
          <el-card v-for="stat in suiteStatsCards" :key="stat.label" class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-number" :style="{ color: stat.color }">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </el-card>
        </div>

        <!-- 筛选 -->
        <div class="filter-bar">
          <el-row :gutter="20">
            <el-col :span="4">
              <el-select v-model="suiteProjectFilter" placeholder="全部项目" clearable filterable @change="loadSuiteReports">
                <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-col>
            <el-col :span="4">
              <el-select v-model="suiteStatusFilter" placeholder="执行状态" clearable @change="loadSuiteReports">
                <el-option label="已完成" value="completed" />
                <el-option label="执行异常" value="error" />
                <el-option label="执行中" value="running" />
              </el-select>
            </el-col>
            <el-col :span="6">
              <el-input v-model="suiteSearch" placeholder="搜索套件名称" clearable @clear="loadSuiteReports" @keyup.enter="loadSuiteReports">
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
            </el-col>
          </el-row>
        </div>

        <!-- 套件报告列表 -->
        <div class="card-container">
          <el-table :data="suiteReports" v-loading="suiteLoading" stripe style="width: 100%">
            <el-table-column prop="name" label="套件名称" min-width="140" header-align="center" align="center" show-overflow-tooltip />
            <el-table-column prop="description" label="描述" min-width="120" header-align="center" align="center" show-overflow-tooltip>
              <template #default="{ row }">{{ row.description || '-' }}</template>
            </el-table-column>
            <el-table-column label="执行状态" min-width="100" header-align="center" align="center">
              <template #default="{ row }">
                <span class="status-badge" :class="getSuiteStatusClass(row)">
                  {{ getSuiteDisplayStatus(row).text }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="用例通过率" min-width="160" header-align="center" align="center">
              <template #default="{ row }">
                <el-progress
                  v-if="row.test_case_count > 0"
                  :percentage="getSuitePassRate(row)"
                  :color="getPassRateColor(getSuitePassRate(row))"
                  :stroke-width="16"
                  :text-inside="true"
                />
                <span v-else class="no-data-text">无用例</span>
              </template>
            </el-table-column>
            <el-table-column label="用例统计" min-width="220" header-align="center" align="center">
              <template #default="{ row }">
                <span class="count-badge">{{ row.passed_count || 0 }}</span>
                <span class="count-badge failed">{{ row.failed_count || 0 }}</span>
                <span class="count-badge total">总计 {{ row.test_case_count || 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="创建人" min-width="100" header-align="center" align="center">
              <template #default="{ row }">{{ row.created_by_name || '-' }}</template>
            </el-table-column>
            <el-table-column label="最后执行" min-width="170" header-align="center" align="center">
              <template #default="{ row }">
                <span class="time-text">{{ formatDateTime(row.last_run_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right" header-align="center" align="center">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button size="small" class="action-btn edit-btn" @click="viewSuiteDetail(row)">
                    <el-icon><View /></el-icon>
                    <span>详情</span>
                  </el-button>
                  <el-button size="small" class="action-btn run-btn" @click="viewSuiteExecutions(row)">
                    <el-icon><List /></el-icon>
                    <span>执行记录</span>
                  </el-button>
                  <el-button size="small" class="action-btn delete-btn" @click="deleteSuiteReport(row)">
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container">
            <el-pagination
              v-model:current-page="suitePagination.current"
              v-model:page-size="suitePagination.size"
              :total="suitePagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="loadSuiteReports"
              @current-change="loadSuiteReports"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- ==================== 用例报告 ==================== -->
      <el-tab-pane label="用例报告" name="case">
        <!-- 统计 -->
        <div class="stats-row">
          <el-card v-for="stat in caseStatsCards" :key="stat.label" class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-number" :style="{ color: stat.color }">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </el-card>
        </div>

        <!-- 筛选 -->
        <div class="filter-bar">
          <el-row :gutter="20">
            <el-col :span="4">
              <el-select v-model="caseProjectFilter" placeholder="全部项目" clearable filterable @change="loadCaseReports">
                <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-col>
            <el-col :span="4">
              <el-select v-model="caseStatusFilter" placeholder="执行状态" clearable @change="loadCaseReports">
                <el-option label="已完成" value="completed" />
                <el-option label="执行异常" value="error" />
                <el-option label="已停止" value="stopped" />
              </el-select>
            </el-col>
            <el-col :span="6">
              <el-input v-model="caseSearch" placeholder="搜索用例名称、设备" clearable @clear="loadCaseReports" @keyup.enter="loadCaseReports">
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
            </el-col>
          </el-row>
        </div>

        <!-- 用例报告列表 -->
        <div class="card-container">
          <el-table :data="caseReports" v-loading="caseLoading" stripe style="width: 100%">
            <el-table-column label="测试用例" min-width="140" header-align="center" align="center" show-overflow-tooltip>
              <template #default="{ row }">{{ row.case_name || '-' }}</template>
            </el-table-column>
            <el-table-column label="设备" min-width="100" header-align="center" align="center">
              <template #default="{ row }">{{ row.device_name || '-' }}</template>
            </el-table-column>
            <el-table-column label="状态" min-width="100" header-align="center" align="center">
              <template #default="{ row }">
                <span class="status-badge" :class="getCaseStatusClass(row)">
                  {{ getDisplayStatus(row.status, row.result).text }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="步骤通过率" min-width="160" header-align="center" align="center">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.pass_rate || 0"
                  :color="getPassRateColor(row.pass_rate)"
                  :stroke-width="16"
                  :text-inside="true"
                />
              </template>
            </el-table-column>
            <el-table-column label="步骤统计" min-width="220" header-align="center" align="center">
              <template #default="{ row }">
                <span class="count-badge">{{ row.passed_steps || 0 }}</span>
                <span class="count-badge failed">{{ row.failed_steps || 0 }}</span>
                <span class="count-badge total">总计 {{ row.total_steps || 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="耗时" min-width="100" header-align="center" align="center">
              <template #default="{ row }">
                <span class="time-text">{{ formatDuration(row.duration) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="执行人" min-width="100" header-align="center" align="center">
              <template #default="{ row }">{{ row.user_name || '-' }}</template>
            </el-table-column>
            <el-table-column label="执行时间" min-width="170" header-align="center" align="center">
              <template #default="{ row }">
                <span class="time-text">{{ formatDateTime(row.started_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right" header-align="center" align="center">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button size="small" class="action-btn edit-btn" @click="viewCaseDetail(row)">
                    <el-icon><View /></el-icon>
                    <span>详情</span>
                  </el-button>
                  <el-button v-if="row.report_path" size="small" class="action-btn run-btn" @click="viewAllureReport(row)">
                    <el-icon><Document /></el-icon>
                    <span>报告</span>
                  </el-button>
                  <el-button size="small" class="action-btn delete-btn" @click="deleteCaseReport(row)">
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container">
            <el-pagination
              v-model:current-page="casePagination.current"
              v-model:page-size="casePagination.size"
              :total="casePagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="loadCaseReports"
              @current-change="loadCaseReports"
            />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ==================== 套件详情弹窗 ==================== -->
    <el-dialog v-model="suiteDetailVisible" title="套件报告详情" width="750px">
      <div v-if="selectedSuite">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="套件名称">{{ selectedSuite.name }}</el-descriptions-item>
          <el-descriptions-item label="执行状态">
            <span class="status-badge" :class="getSuiteStatusClass(selectedSuite)">
              {{ getSuiteDisplayStatus(selectedSuite).text }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="创建人">{{ selectedSuite.created_by_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最后执行">
            <span class="time-text">{{ formatDateTime(selectedSuite.last_run_at) }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 用例级统计 -->
        <div class="detail-section">
          <h4>用例统计</h4>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="detail-stat success-bg">
                <div class="detail-stat-num">{{ selectedSuite.passed_count || 0 }}</div>
                <div class="detail-stat-label">通过用例</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="detail-stat danger-bg">
                <div class="detail-stat-num">{{ selectedSuite.failed_count || 0 }}</div>
                <div class="detail-stat-label">失败用例</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="detail-stat info-bg">
                <div class="detail-stat-num">{{ selectedSuite.test_case_count || 0 }}</div>
                <div class="detail-stat-label">总用例数</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <div class="detail-section">
          <h4>用例通过率</h4>
          <el-progress
            :percentage="getSuitePassRate(selectedSuite)"
            :color="getPassRateColor(getSuitePassRate(selectedSuite))"
            :stroke-width="20"
            :text-inside="true"
            style="margin-top:10px"
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="suiteDetailVisible = false">关闭</el-button>
        <el-button type="primary" @click="suiteDetailVisible = false; viewSuiteExecutions(selectedSuite)">查看执行记录</el-button>
      </template>
    </el-dialog>

    <!-- ==================== 套件执行记录弹窗 ==================== -->
    <el-dialog v-model="suiteExecVisible" :title="`执行记录 - ${selectedSuite?.name || ''}`" width="900px">
      <el-table :data="suiteExecRecords" v-loading="suiteExecLoading" border stripe max-height="500">
        <el-table-column label="测试用例" min-width="180" header-align="center" align="center">
          <template #default="{ row }">{{ row.case_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="getCaseStatusClass(row)">
              {{ getDisplayStatus(row.status, row.result).text }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="步骤统计" min-width="220" header-align="center" align="center">
          <template #default="{ row }">
            <span class="count-badge">{{ row.passed_steps || 0 }}</span>
            <span class="count-badge failed">{{ row.failed_steps || 0 }}</span>
            <span class="count-badge total">总计 {{ row.total_steps || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" min-width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDuration(row.duration) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="执行时间" min-width="170" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.started_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.report_path" type="success" link size="small" @click="viewAllureReport(row)">Allure报告</el-button>
            <el-button v-if="row.error_message" type="danger" link size="small" @click="viewCaseDetail(row)">错误</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="suiteExecVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- ==================== 用例详情弹窗 ==================== -->
    <el-dialog v-model="caseDetailVisible" title="用例执行报告详情" width="700px">
      <div v-if="selectedCase">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="测试用例">{{ selectedCase.case_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="执行设备">{{ selectedCase.device_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="执行状态">
            <span class="status-badge" :class="getCaseStatusClass(selectedCase)">
              {{ getDisplayStatus(selectedCase.status, selectedCase.result).text }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="执行人">{{ selectedCase.user_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatDateTime(selectedCase.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatDateTime(selectedCase.finished_at) }}</el-descriptions-item>
          <el-descriptions-item label="执行耗时">{{ formatDuration(selectedCase.duration) }}</el-descriptions-item>
          <el-descriptions-item label="步骤通过率">
            <span :style="{ color: getPassRateColor(selectedCase.pass_rate), fontWeight: 'bold' }">
              {{ selectedCase.pass_rate || 0 }}%
            </span>
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>步骤统计</h4>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="detail-stat success-bg">
                <div class="detail-stat-num">{{ selectedCase.passed_steps || 0 }}</div>
                <div class="detail-stat-label">通过步骤</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="detail-stat danger-bg">
                <div class="detail-stat-num">{{ selectedCase.failed_steps || 0 }}</div>
                <div class="detail-stat-label">失败步骤</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="detail-stat info-bg">
                <div class="detail-stat-num">{{ selectedCase.total_steps || 0 }}</div>
                <div class="detail-stat-label">总步骤数</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <div v-if="selectedCase.error_message" class="detail-section">
          <h4>错误信息</h4>
          <el-alert :title="selectedCase.error_message" type="error" show-icon :closable="false" />
        </div>

        <div v-if="selectedCase.report_path" class="detail-section" style="text-align:center">
          <el-button type="primary" @click="viewAllureReport(selectedCase)">
            <el-icon><DataAnalysis /></el-icon>
            查看完整 Allure 报告
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="caseDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, DataAnalysis, View, List, Delete, Document } from '@element-plus/icons-vue'
import {
  getExecutionList, deleteExecution,
  getTestSuiteList, getTestSuiteExecutions,
  getAppProjects,
} from '@/api/app-automation.js'
import { getExecutionStatusType, getExecutionStatusText, getDisplayStatus, formatDateTime } from '@/utils/app-automation-helpers.js'

defineOptions({ name: 'AppReportList' })

// ==================== 公共 ====================
const activeTab = ref('suite')
const projectList = ref([])

function onTabChange(tab) {
  if (tab === 'suite' && suiteReports.value.length === 0) loadSuiteReports()
  if (tab === 'case' && caseReports.value.length === 0) loadCaseReports()
}

onMounted(() => {
  getAppProjects({ page_size: 100 }).then(res => { projectList.value = res.data.results || res.data || [] }).catch(() => {})
  loadSuiteReports()
})

// ==================== 套件报告 ====================
const suiteLoading = ref(false)
const suiteReports = ref([])
const suiteSearch = ref('')
const suiteStatusFilter = ref('')
const suiteProjectFilter = ref(null)
const suitePagination = reactive({ current: 1, size: 20, total: 0 })
const suiteDetailVisible = ref(false)
const suiteExecVisible = ref(false)
const suiteExecLoading = ref(false)
const suiteExecRecords = ref([])
const selectedSuite = ref(null)

const suiteStatsCards = computed(() => {
  const data = suiteReports.value
  const executed = data.filter(s => s.last_run_at)
  const success = executed.filter(s => s.execution_result === 'passed')
  const failed = executed.filter(s => s.execution_result === 'failed')
  const avgRate = executed.length > 0
    ? Math.round(executed.reduce((sum, s) => sum + getSuitePassRate(s), 0) / executed.length)
    : 0
  return [
    { label: '套件总数', value: suitePagination.total, color: '#409eff' },
    { label: '已执行', value: executed.length, color: '#67c23a' },
    { label: '最近失败', value: failed.length, color: '#f56c6c' },
    { label: '平均通过率', value: avgRate + '%', color: '#e6a23c' },
  ]
})

async function loadSuiteReports() {
  suiteLoading.value = true
  try {
    const params = { page: suitePagination.current, page_size: suitePagination.size }
    if (suiteProjectFilter.value) params.project = suiteProjectFilter.value
    if (suiteSearch.value) params.search = suiteSearch.value
    const res = await getTestSuiteList(params)
    let list = res.data.results || res.data || []
    // 状态筛选
    if (suiteStatusFilter.value) {
      list = list.filter(s => s.execution_status === suiteStatusFilter.value)
    }
    suiteReports.value = list
    suitePagination.total = res.data.count || list.length
  } catch { ElMessage.error('加载套件报告失败') }
  finally { suiteLoading.value = false }
}

function viewSuiteDetail(suite) {
  selectedSuite.value = suite
  suiteDetailVisible.value = true
}

async function viewSuiteExecutions(suite) {
  selectedSuite.value = suite
  suiteExecVisible.value = true
  suiteExecLoading.value = true
  try {
    const res = await getTestSuiteExecutions(suite.id)
    suiteExecRecords.value = res.data.data || res.data.results || res.data || []
  } catch { ElMessage.error('加载执行记录失败') }
  finally { suiteExecLoading.value = false }
}

async function deleteSuiteReport(suite) {
  try {
    await ElMessageBox.confirm(`确认删除套件「${suite.name}」？此操作不可恢复`, '删除确认', { type: 'warning' })
    const { deleteTestSuite } = await import('@/api/app-automation.js')
    await deleteTestSuite(suite.id)
    ElMessage.success('已删除')
    loadSuiteReports()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

function getSuitePassRate(suite) {
  const total = suite.test_case_count || 0
  if (total === 0) return 0
  return Math.round(((suite.passed_count || 0) / total) * 100)
}

function getSuiteDisplayStatus(row) {
  const status = row.execution_status
  const result = row.execution_result
  if (status === 'not_run') return { type: 'info', text: '未执行' }
  if (status === 'running') return { type: 'warning', text: '执行中' }
  if (status === 'error') return { type: 'danger', text: '执行异常' }
  if (result === 'passed') return { type: 'success', text: '通过' }
  if (result === 'failed') return { type: 'danger', text: '失败' }
  if (result === 'skipped') return { type: 'warning', text: '跳过' }
  // 向后兼容
  if (status === 'success') return { type: 'success', text: '通过' }
  if (status === 'failed') return { type: 'danger', text: '失败' }
  return { type: 'info', text: status }
}

function getSuiteStatusClass(row) {
  const { type } = getSuiteDisplayStatus(row)
  const map = { success: 'success', danger: 'failed', warning: 'processing', info: 'pending' }
  return map[type] || 'pending'
}

function getCaseStatusClass(row) {
  const { type } = getDisplayStatus(row.status, row.result)
  const map = { success: 'success', danger: 'failed', warning: 'processing', info: 'pending' }
  return map[type] || 'pending'
}

// ==================== 用例报告 ====================
const caseLoading = ref(false)
const caseReports = ref([])
const caseSearch = ref('')
const caseStatusFilter = ref('')
const caseProjectFilter = ref(null)
const casePagination = reactive({ current: 1, size: 20, total: 0 })
const caseDetailVisible = ref(false)
const selectedCase = ref(null)

const caseStatsCards = computed(() => {
  const data = caseReports.value
  const success = data.filter(r => r.result === 'passed').length
  const failed = data.filter(r => r.result === 'failed').length
  const avgRate = data.length > 0
    ? Math.round(data.reduce((sum, r) => sum + (r.pass_rate || 0), 0) / data.length)
    : 0
  return [
    { label: '总报告数', value: casePagination.total, color: '#409eff' },
    { label: '本页通过', value: success, color: '#67c23a' },
    { label: '本页失败', value: failed, color: '#f56c6c' },
    { label: '本页平均通过率', value: avgRate + '%', color: '#e6a23c' },
  ]
})

async function loadCaseReports() {
  caseLoading.value = true
  try {
    const params = {
      page: casePagination.current,
      page_size: casePagination.size,
      ordering: '-created_at',
      'test_suite__isnull': true,  // 只查询单独执行的用例，排除套件执行记录
    }
    if (caseProjectFilter.value) params.project = caseProjectFilter.value
    if (caseStatusFilter.value) {
      params.status = caseStatusFilter.value
    } else {
      params.status__in = 'success,failed,stopped'
    }
    if (caseSearch.value) params.search = caseSearch.value

    const res = await getExecutionList(params)
    caseReports.value = res.data.results || []
    casePagination.total = res.data.count || 0
  } catch { ElMessage.error('加载用例报告失败') }
  finally { caseLoading.value = false }
}

function viewCaseDetail(row) {
  selectedCase.value = row
  caseDetailVisible.value = true
}

function viewAllureReport(row) {
  if (!row.report_path) return ElMessage.warning('该记录没有 Allure 报告')
  window.open(`/api/app-automation/executions/${row.id}/report/`, '_blank')
}

async function deleteCaseReport(row) {
  try {
    await ElMessageBox.confirm('确认删除该执行报告？', '删除确认', { type: 'warning' })
    await deleteExecution(row.id)
    ElMessage.success('已删除')
    loadCaseReports()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

// getDisplayStatus 已从 helpers 导入

function getPassRateColor(rate) {
  if (rate >= 80) return '#67c23a'
  if (rate >= 50) return '#e6a23c'
  return '#f56c6c'
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${Math.floor(seconds)}秒`
  const min = Math.floor(seconds / 60)
  const sec = Math.floor(seconds % 60)
  return `${min}分${sec}秒`
}
</script>

<style scoped lang="scss">
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
}

.stats-row { display: flex; gap: 16px; margin-bottom: 20px; }
.stat-card { flex: 1; }
.stat-content { text-align: center; }
.stat-number { font-size: 28px; font-weight: bold; line-height: 1.6; color: #8b5cf6; }
.stat-label { font-size: 13px; color: #666; }

.filter-bar {
  margin-bottom: 20px;
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(167, 139, 250, 0.08);
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
      line-height: 40px !important;
      height: 50px !important;

      &:hover {
        background-color: #ffffff !important;
      }

      .cell {
        background-color: #ffffff !important;
        color: #5a32a3 !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
        line-height: 24px !important;
        padding: 12px 16px !important;
      }
    }

    :deep(.el-table__body-wrapper) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__row) {
      transition: all 0.3s ease;
      background-color: #ffffff !important;
      line-height: 40px !important;
      height: 50px !important;

      td {
        padding: 10px 0 !important;
      }

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

      .cell {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 24px;
        line-height: 1.5;
        width: 100%;
      }
    }

    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;
    }
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

.detail-section { margin-top: 24px; }
.detail-section h4 { margin-bottom: 12px; color: #1a1a1a; }
.detail-stat { text-align: center; padding: 16px; border-radius: 8px; }
.detail-stat-num { font-size: 24px; font-weight: bold; }
.detail-stat-label { font-size: 13px; color: #666; margin-top: 4px; }
.success-bg { background: rgba(82, 196, 26, 0.1); color: #52c41a; }
.danger-bg { background: rgba(245, 34, 45, 0.1); color: #f5222d; }
.info-bg { background: rgba(147, 112, 219, 0.05); color: #666; }

// 时间文本样式
.time-text {
  color: #666;
  font-size: 14px;
  white-space: nowrap;
}

// 无数据文本
.no-data-text {
  color: #909399;
  font-size: 13px;
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

  &.failed {
    background: #fff1f0;
    color: #f5222d;
  }

  &.total {
    background: #f5f5f5;
    color: #595959;
  }
}
</style>
