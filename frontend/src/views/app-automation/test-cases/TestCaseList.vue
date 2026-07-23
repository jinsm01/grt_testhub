<template>
  <div class="page-container">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索测试用例名称"
        clearable
        @clear="loadTestCases"
        @keyup.enter="loadTestCases"
        class="search-input"
        style="width: 300px"
      >
        <template #suffix>
          <el-icon @click="loadTestCases" style="cursor: pointer;"><Search /></el-icon>
        </template>
      </el-input>
      <el-select
        v-model="form.projectId"
        placeholder="所属项目"
        clearable
        filterable
        style="width: 160px"
        @change="loadTestCases"
        class="filter-select"
      >
        <el-option
          v-for="proj in projectList"
          :key="proj.id"
          :label="proj.name"
          :value="proj.id"
        />
      </el-select>
      <el-select
        v-model="form.deviceId"
        placeholder="选择设备"
        filterable
        style="width: 160px"
        :loading="devicesLoading"
        class="filter-select"
      >
        <el-option
          v-for="device in availableDevices"
          :key="device.id"
          :label="`${device.name} (${device.device_id})`"
          :value="device.id"
          :disabled="device.status !== 'available' && device.status !== 'online'"
        />
      </el-select>
      <el-select
        v-model="form.packageId"
        placeholder="选择应用"
        clearable
        filterable
        style="width: 160px"
        class="filter-select"
      >
        <el-option
          v-for="pkg in appPackages"
          :key="pkg.id"
          :label="`${pkg.name} (${pkg.package_name})`"
          :value="pkg.id"
        />
      </el-select>
      <div class="filter-bar-spacer"></div>
      <!-- 刷新按钮已隐藏 -->
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedCases.length > 0" class="batch-bar">
      <span>已选择 <strong>{{ selectedCases.length }}</strong> 个用例</span>
      <el-button type="success" size="small" @click="batchRun">
        批量执行
      </el-button>
      <el-button size="small" @click="clearSelection">
        取消选择
      </el-button>
    </div>

    <!-- 表格容器 -->
    <div class="card-container">
      <!-- 测试用例列表 -->
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="testCases"
        stripe
        style="width: 100%"
        empty-text="暂无测试用例"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="name" label="用例名称" min-width="200" />
        <el-table-column label="场景描述" min-width="250">
          <template #default="{ row }">
            {{ row.description || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" class="action-btn run-btn" @click="runCase(row)">
                <el-icon><VideoPlay /></el-icon>
                <span>运行</span>
              </el-button>
              <el-button size="small" class="action-btn edit-btn" @click="editCase(row)">
                <el-icon><Edit /></el-icon>
                <span>编辑</span>
              </el-button>
              <el-button size="small" class="action-btn delete-btn" @click="deleteCase(row)">
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
          v-show="caseTotal > 0"
          v-model:current-page="caseCurrentPage"
          v-model:page-size="casePageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="caseTotal"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleCaseSizeChange"
          @current-change="handleCasePageChange"
        />
      </div>
    </div>

    <!-- 执行记录 - 已隐藏 -->
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, VideoPlay, Edit, Delete } from '@element-plus/icons-vue'

defineOptions({ name: 'AppTestCaseList' })
import {
  getTestCaseList,
  deleteTestCase as apiDeleteTestCase,
  executeTestCase as apiExecuteTestCase,
  getExecutionList,
  getExecutionDetail,
  stopExecution as apiStopExecution,
  getPackageList,
  getAppProjects,
  getWsStatus
} from '@/api/app-automation'
import { getDeviceList } from '@/api/app-automation'
import { getExecutionStatusType, getExecutionStatusText, getDisplayStatus, formatDateTime } from '@/utils/app-automation-helpers'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const devicesLoading = ref(false)
const executionsLoading = ref(false)
const availableDevices = ref([])
const appPackages = ref([])
const searchQuery = ref('')

const projectList = ref([])
const form = ref({
  projectId: null,
  deviceId: null,
  packageId: null
})

// 用例列表数据
const testCases = ref([])
const caseCurrentPage = ref(1)
const casePageSize = ref(20)
const caseTotal = ref(0)

// 批量选择
const tableRef = ref(null)
const selectedCases = ref([])

// 执行记录数据
const executionData = ref({
  count: 0,
  results: []
})
const websockets = ref({})
const lastStatusMessages = ref({})

// 定时刷新执行记录
let refreshTimer = null

// 加载项目列表
const loadProjectList = async () => {
  try {
    const res = await getAppProjects({ page_size: 100 })
    projectList.value = res.data.results || res.data || []
  } catch { /* ignore */ }
}

// 加载设备列表
const loadDevices = async () => {
  devicesLoading.value = true
  try {
    const res = await getDeviceList({ page_size: 100 })
    const data = res.data
    if (data.success !== undefined) {
      availableDevices.value = data.data?.results || data.data || []
    } else {
      availableDevices.value = data.results || data || []
    }
  } catch (error) {
    console.error('加载设备失败:', error)
    availableDevices.value = []
  } finally {
    devicesLoading.value = false
  }
}

const loadPackages = async () => {
  try {
    const res = await getPackageList({ page_size: 200 })
    const data = res.data
    if (data.success !== undefined) {
      appPackages.value = data.data?.results || data.data || []
    } else {
      appPackages.value = data.results || data || []
    }
  } catch (error) {
    console.error('加载应用包名失败:', error)
    appPackages.value = []
  }
}

// 加载测试用例列表
const loadTestCases = async () => {
  loading.value = true
  try {
    const params = {
      page: caseCurrentPage.value,
      page_size: casePageSize.value,
      search: searchQuery.value
    }
    if (form.value.projectId) params.project = form.value.projectId
    const res = await getTestCaseList(params)
    const data = res.data
    
    if (data.success !== undefined) {
      testCases.value = data.data?.results || data.data || []
      caseTotal.value = data.data?.count || 0
    } else {
      testCases.value = data.results || data || []
      caseTotal.value = data.count || 0
    }
  } catch (error) {
    console.error('加载测试用例失败:', error)
    testCases.value = []
    caseTotal.value = 0
  } finally {
    loading.value = false
  }
}

// 加载执行记录
const loadExecutions = async () => {
  executionsLoading.value = true
  try {
    const params = {
      page: 1,
      page_size: 5,
      ordering: '-start_time'
    }
    const res = await getExecutionList(params)
    const data = res.data
    
    if (data.success !== undefined) {
      executionData.value = {
        count: data.data?.count || 0,
        results: data.data?.results || data.data || []
      }
    } else {
      executionData.value = {
        count: data.count || 0,
        results: data.results || data || []
      }
    }

    executionData.value.results.forEach(execution => {
      if ((execution.status === 'pending' || execution.status === 'running') && execution.id) {
        trackExecution(execution.id)
      }
    })
  } catch (error) {
    console.error('加载执行记录失败:', error)
    executionData.value = { count: 0, results: [] }
  } finally {
    executionsLoading.value = false
  }
}

// 刷新执行记录
const refreshExecutions = () => {
  loadExecutions()
}

const viewAllExecutions = () => {
  router.push({ path: '/app-automation/executions' })
}

const viewReport = (execution) => {
  if (!execution.report_path) {
    ElMessage.info('报告路径不存在')
    return
  }
  const reportUrl = `/api/app-automation/executions/${execution.id}/report/`
  window.open(reportUrl, '_blank')
}

// 停止测试
const stopTest = async (execution) => {
  try {
    await ElMessageBox.confirm(
      '确定要停止这个测试吗？',
      '确认停止',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await apiStopExecution(execution.id)
    if (res.data.success) {
      ElMessage.success('已停止执行')
      loadExecutions()
    } else {
      ElMessage.error(res.data.message || '停止失败')
    }
  } catch (error) {
    // 用户取消
  }
}

// 运行测试用例
const runCase = async (testCase) => {
  if (!form.value.deviceId) {
    ElMessage.warning('请先选择设备')
    return
  }

  try {
    const params = {
      device_id: availableDevices.value.find(d => d.id === form.value.deviceId)?.device_id
    }

    if (form.value.packageId) {
      const selected = appPackages.value.find(pkg => pkg.id === form.value.packageId)
      if (selected) {
        params.package_name = selected.package_name
      }
    }
    
    const res = await apiExecuteTestCase(testCase.id, params)
    const data = res.data
    
    if (data.success || data.execution_id) {
      ElMessage.success('测试已提交执行')
      const executionId = data.execution?.id || data.execution_id
      if (executionId) {
        trackExecution(executionId)
        checkExecutionStatus(executionId)
      }
      // 刷新执行记录
      setTimeout(() => {
        loadExecutions()
      }, 1000)
    } else {
      ElMessage.error('执行失败: ' + (data.message || '未知错误'))
    }
  } catch (error) {
    ElMessage.error('执行失败: ' + (error.message || '未知错误'))
  }
}

const checkExecutionStatus = (executionId) => {
  setTimeout(async () => {
    try {
      const res = await getExecutionDetail(executionId)
      const data = res.data
      const status = data.status || data.data?.status
      if (status === 'pending') {
        ElMessage.warning('任务未开始，请确认 Celery worker/Redis 已启动')
      }
    } catch (error) {
      console.error('检查执行状态失败:', error)
    }
  }, 3000)
}

// 编辑测试用例
const editCase = (testCase) => {
  router.push({
    path: '/app-automation/scene-builder',
    query: { case_id: testCase.id }
  })
}

// 删除测试用例
const deleteCase = async (testCase) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除测试用例 "${testCase.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await apiDeleteTestCase(testCase.id)
    ElMessage.success('删除成功')
    loadTestCases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

// 查看测试报告

const updateExecutionData = (updates) => {
  if (!updates || !updates.execution_id) {
    return
  }
  const target = executionData.value.results.find(item => item.id === updates.execution_id)
  if (!target) {
    loadExecutions()
    return
  }
  if (updates.status) target.status = updates.status
  if (updates.result !== undefined) target.result = updates.result
  if (updates.progress !== null && updates.progress !== undefined) target.progress = updates.progress
  if (updates.report_path !== undefined) target.report_path = updates.report_path
  if (updates.finished_at) target.finished_at = updates.finished_at
}

// ===== 执行状态推送：WebSocket 模式 / 轮询模式（由 ws_status 接口决定） =====
const wsDisabled = ref(false)
const pollingTimers = ref({})
const wsRetryCount = ref({})  // WebSocket 重试计数
const WS_MAX_RETRY = 3       // 最大重试次数

// --- 轮询模式：每 3 秒查一次执行状态 ---
const startPolling = (executionId) => {
  if (pollingTimers.value[executionId]) return
  pollingTimers.value[executionId] = setInterval(async () => {
    try {
      const res = await getExecutionDetail(executionId)
      if (res.data) {
        updateExecutionData({
          execution_id: res.data.id,
          status: res.data.status,
          result: res.data.result,
          progress: res.data.progress,
          report_path: res.data.report_path,
          finished_at: res.data.finished_at,
        })
        if (['completed', 'error', 'stopped'].includes(res.data.status)) {
          stopPolling(executionId)
          if (res.data.result === 'passed') ElMessage.success('测试执行通过')
          else if (res.data.result === 'failed') ElMessage.error('测试用例失败')
          else if (res.data.status === 'error') ElMessage.error('执行异常')
        }
      }
    } catch (e) {
      console.error('轮询执行状态失败:', e)
    }
  }, 3000)
}

const stopPolling = (executionId) => {
  if (pollingTimers.value[executionId]) {
    clearInterval(pollingTimers.value[executionId])
    delete pollingTimers.value[executionId]
  }
}

const stopAllPolling = () => {
  Object.keys(pollingTimers.value).forEach(id => stopPolling(id))
}

// --- WebSocket 模式：实时推送 ---
const connectWebSocket = (executionId) => {
  if (websockets.value[executionId]) return

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsUrl = `${protocol}://${window.location.host}/ws/app-automation/executions/${executionId}/`

  const ws = new WebSocket(wsUrl)
  websockets.value[executionId] = ws

  ws.onopen = () => {
    wsRetryCount.value[executionId] = 0
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      updateExecutionData(data)
      if (data.status && lastStatusMessages.value[executionId] !== data.status) {
        lastStatusMessages.value[executionId] = data.status
        if (data.result === 'passed') ElMessage.success('测试执行通过')
        else if (data.result === 'failed') ElMessage.error('测试用例失败')
        else if (data.status === 'error') ElMessage.error('执行异常')
      }
      if (['completed', 'error', 'stopped'].includes(data.status)) {
        closeWebSocket(executionId)
      }
    } catch (error) {
      console.error('处理 WebSocket 消息失败:', error)
    }
  }

  ws.onclose = () => {
    delete websockets.value[executionId]
  }

  ws.onerror = () => {
    closeWebSocket(executionId)
    const retries = (wsRetryCount.value[executionId] || 0) + 1
    wsRetryCount.value[executionId] = retries
    if (retries <= WS_MAX_RETRY) {
      console.warn(`WebSocket 连接异常 (${retries}/${WS_MAX_RETRY})，${retries}秒后重试`)
      setTimeout(() => {
        const target = executionData.value.results.find(e => e.id === executionId)
        if (target && ['pending', 'running'].includes(target.status)) {
          connectWebSocket(executionId)
        }
      }, retries * 1000)
    } else {
      console.warn(`WebSocket 重试超限，execution_id=${executionId} 切换为轮询`)
      delete wsRetryCount.value[executionId]
      startPolling(executionId)
    }
  }
}

// --- 统一入口：根据模式选择推送方式 ---
const trackExecution = (executionId) => {
  if (wsDisabled.value) {
    startPolling(executionId)
  } else {
    connectWebSocket(executionId)
  }
}

const closeWebSocket = (executionId) => {
  const ws = websockets.value[executionId]
  if (ws) {
    ws.close()
    delete websockets.value[executionId]
  }
}

const closeAllWebSockets = () => {
  Object.keys(websockets.value).forEach(id => closeWebSocket(id))
}

// 批量选择与执行
const handleSelectionChange = (selection) => {
  selectedCases.value = selection
}

const clearSelection = () => {
  tableRef.value?.clearSelection()
  selectedCases.value = []
}

const batchRun = async () => {
  if (!form.value.deviceId) {
    ElMessage.warning('请先选择设备')
    return
  }
  if (selectedCases.value.length === 0) {
    ElMessage.warning('请至少选择一个用例')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要批量执行选中的 ${selectedCases.value.length} 个用例吗？`,
      '确认批量执行',
      { confirmButtonText: '执行', cancelButtonText: '取消', type: 'info' }
    )

    const deviceIdStr = availableDevices.value.find(d => d.id === form.value.deviceId)?.device_id
    let packageName = null
    if (form.value.packageId) {
      const selected = appPackages.value.find(pkg => pkg.id === form.value.packageId)
      if (selected) packageName = selected.package_name
    }

    // 逐个提交执行
    let submitted = 0
    for (const tc of selectedCases.value) {
      try {
        const params = { device_id: deviceIdStr }
        if (packageName) params.package_name = packageName
        await apiExecuteTestCase(tc.id, params)
        submitted++
      } catch (error) {
        console.error(`执行用例 ${tc.name} 失败:`, error)
      }
    }

    ElMessage.success(`已提交 ${submitted} 个用例执行`)
    clearSelection()
    setTimeout(() => loadExecutions(), 1500)
  } catch (error) {
    // 用户取消
  }
}

// 分页处理
const handleCaseSizeChange = () => {
  caseCurrentPage.value = 1  // 切换每页条数时回到第1页
  loadTestCases()
}

const handleCasePageChange = () => {
  loadTestCases()
}


// 计算执行进度
const calculateProgress = (execution) => {
  if (execution.status === 'completed') return 100
  if (execution.status === 'error' || execution.status === 'stopped') return execution.progress || 0
  if (execution.status === 'running') return execution.progress || 0
  return 0
}

// 获取进度条状态（基于测试结果）
const getProgressStatus = (row) => {
  if (row.status === 'completed') {
    return row.result === 'failed' ? 'exception' : 'success'
  }
  if (row.status === 'error') return 'exception'
  return undefined
}

// formatDateTime 已从 app-automation-helpers 导入

// 组件挂载
onMounted(async () => {
  // 先检测 WebSocket 是否可用
  try {
    const res = await getWsStatus()
    wsDisabled.value = !(res.data?.websocket)
  } catch {
    wsDisabled.value = true
  }
  if (wsDisabled.value) {
    console.info('WebSocket 不可用，将使用轮询模式')
  }

  loadProjectList()
  loadDevices()
  loadPackages()
  loadTestCases()
  loadExecutions()
  
  // WebSocket 模式下，每10秒刷新执行列表（补充 WS 推送）
  // 轮询模式下不需要（trackExecution 已有 3 秒轮询）
  if (!wsDisabled.value) {
    refreshTimer = setInterval(() => {
      const hasRunning = executionData.value.results.some(e => e.status === 'running')
      if (hasRunning) {
        loadExecutions()
      }
    }, 10000)
  }
})

// 组件卸载
onBeforeUnmount(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  closeAllWebSockets()
  stopAllPolling()
})
</script>

<style scoped lang="scss">
:root {
  --primary-color: #a78bfa;
  --primary-dark: #8b5cf6;
  --primary-light: #f3f0ff;
  --primary-lighter: #f5f3ff;
  --border-color: #e9ecef;
  --text-primary: #262626;
  --text-secondary: #595959;
  --text-tertiary: #8c8c8c;
  --bg-light: #ffffff;
  --bg-gray: #fafafa;
  --success-color: #52c41a;
  --warning-color: #faad14;
  --danger-color: #ff4d4f;
  --info-color: #1890ff;
}

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

  .filter-select {
    :deep(.el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 0 0 1px rgba(167, 139, 250, 0.2) inset;
      background: #ffffff;

      &:hover, &.is-focus {
        box-shadow: 0 0 0 1px #a78bfa inset;
      }
    }

    :deep(.el-input__inner) {
      color: #5b21b6;
      font-weight: 500;
    }
  }

  .search-input {
    :deep(.el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 0 0 1px rgba(167, 139, 250, 0.2) inset;
      background: #ffffff;

      &:hover, &.is-focus {
        box-shadow: 0 0 0 1px #a78bfa inset;
      }
    }

    :deep(.el-input__inner) {
      color: #8b5cf6;
      font-weight: 500;
    }
  }

  .filter-bar-spacer {
    flex: 1;
  }

  .refresh-btn {
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

.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(167, 139, 250, 0.08);
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: 8px;
  font-size: 14px;

  strong {
    color: #8b5cf6;
  }
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(167, 139, 250, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
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

    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;
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
}

.execution-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background: linear-gradient(135deg, #f8f7ff 0%, #f0e6ff 100%);
    border-bottom: 1px solid rgba(167, 139, 250, 0.15);
    font-size: 16px;
    font-weight: 600;
    color: #8b5cf6;
  }

  .card-actions {
    display: flex;
    gap: 12px;
  }
}

.progress-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 8px;
  background-color: #f5f7fa;
  border-radius: 4px;

  .progress-text {
    min-width: 45px;
    text-align: right;
    font-size: 12px;
    color: #606266;
    font-weight: 500;
  }
}

@media screen and (max-width: 1366px) {
  .filter-bar :deep(.el-form-item__label) {
    font-size: 13px;
  }
}

// 操作按钮样式
.page-container {
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

/* 操作按钮样式 */
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

  &.run-btn {
    background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.3);
    }
  }

  &.edit-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
    }
  }

  &.delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%) !important;

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(255, 77, 79, 0.3);
    }
  }
}
</style>
