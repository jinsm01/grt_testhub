<template>
  <div class="page-container">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <el-input
          v-model="searchText"
          :placeholder="$t('apiTesting.history.searchRequest')"
          class="search-input"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #suffix>
            <el-icon @click="handleSearch" style="cursor: pointer;"><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <div class="header-actions">
      </div>
    </div>

    <!-- 历史记录卡片 -->
    <div class="card-container">
      <!-- HTTP 请求历史表格 -->
      <div v-if="activeTab === 'HTTP'" class="table-wrapper">
        <HistoryTable
          :data="httpHistory"
          :loading="loading"
          @view-detail="viewDetail"
          @delete-item="handleDelete"
        />
      </div>
      <!-- WebSocket 请求历史表格 -->
      <div v-else class="table-wrapper">
        <HistoryTable
          :data="websocketHistory"
          :loading="loading"
          @view-detail="viewDetail"
          @delete-item="handleDelete"
        />
      </div>

      <!-- 分页 -->
      <div class="pagination-container">
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

    <!-- 请求详情抽屉 -->
    <el-drawer
      v-model="showDetailDialog"
      title="请求执行详情"
      size="50%"
      direction="rtl"
      :destroy-on-close="true"
      class="detail-drawer"
    >
      <div v-if="selectedHistory" class="request-detail-drawer">
        <!-- 顶部状态栏 -->
        <div class="request-header">
          <div class="request-title-row">
            <span class="request-name">{{ selectedHistory.request?.name || '未命名请求' }}</span>
            <span class="method-tag" :class="selectedHistory.request?.method?.toLowerCase()">{{ selectedHistory.request?.method }}</span>
            <span class="status-tag" :class="getDetailStatusClass(selectedHistory)">
              {{ getDetailStatusText(selectedHistory) }}
            </span>
            <span class="meta-tag time-tag">{{ selectedHistory.response_time?.toFixed(0) }}ms</span>
            <span class="meta-tag code-tag">{{ selectedHistory.status_code || '-' }}</span>
          </div>
          <div class="request-url">{{ selectedHistory.request_data?.url }}</div>
        </div>

        <!-- 错误信息 -->
        <div v-if="selectedHistory.error_message" class="error-banner">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ selectedHistory.error_message }}</span>
        </div>

        <!-- 数据交换区域 -->
        <div class="data-section" v-if="selectedHistory.request_data || selectedHistory.response_data">
          <!-- 主标签切换 -->
          <div class="main-tabs">
            <button
              class="main-tab-btn"
              :class="{ active: activeMainTab === '请求' }"
              @click="activeMainTab = '请求'"
            >
              请求
            </button>
            <button
              class="main-tab-btn"
              :class="{ active: activeMainTab === '响应' }"
              @click="activeMainTab = '响应'"
            >
              响应
            </button>
          </div>

          <!-- 请求内容 -->
          <div v-if="activeMainTab === '请求' && selectedHistory.request_data" class="data-panel">
            <div class="panel-header">
              <div class="sub-tabs">
                <button
                  v-for="tab in ['body', 'headers', 'params']"
                  :key="tab"
                  class="sub-tab-btn"
                  :class="{ active: activeRequestSubTab === tab }"
                  @click="activeRequestSubTab = tab"
                >
                  {{ tab.toUpperCase() }}
                </button>
              </div>
              <span class="data-badge">{{ activeRequestSubTab.toUpperCase() }}</span>
            </div>
            <div class="code-container">
              <pre v-if="activeRequestSubTab === 'body'" class="code-block">{{ formatJson(selectedHistory.request_data.body) || '无请求体' }}</pre>
              <pre v-else-if="activeRequestSubTab === 'headers'" class="code-block">{{ formatJson(selectedHistory.request_data.headers) || '无请求头' }}</pre>
              <pre v-else-if="activeRequestSubTab === 'params'" class="code-block">{{ formatJson(selectedHistory.request_data.params) || '无请求参数' }}</pre>
            </div>
          </div>

          <!-- 响应内容 -->
          <div v-if="activeMainTab === '响应' && selectedHistory.response_data" class="data-panel">
            <div class="panel-header">
              <div class="sub-tabs">
                <button
                  v-for="tab in responseTabs"
                  :key="tab.key"
                  class="sub-tab-btn"
                  :class="{ active: activeResponseSubTab === tab.key }"
                  @click="activeResponseSubTab = tab.key"
                >
                  {{ tab.label }}
                </button>
              </div>
              <span class="data-badge">{{ activeResponseSubTab.toUpperCase() }}</span>
            </div>
            <div class="code-container" v-if="activeResponseSubTab !== 'assertions'">
              <pre v-if="activeResponseSubTab === 'body'" class="code-block">{{ responseBodyText || '无响应体' }}</pre>
              <pre v-else-if="activeResponseSubTab === 'headers'" class="code-block">{{ formatJson(selectedHistory.response_data.headers) || '无响应头' }}</pre>
              <pre v-else-if="activeResponseSubTab === 'json'" class="code-block">{{ responseBodyText || '无响应体' }}</pre>
            </div>
            <div class="assertions-container" v-else>
              <div class="assertion-list">
                <div v-for="(item, idx) in selectedHistory.assertions_results" :key="idx" class="assertion-item" :class="item.passed ? 'passed' : 'failed'">
                  <el-icon><CircleCheck v-if="item.passed" /><CircleClose v-else /></el-icon>
                  <span class="assertion-name">{{ item.name }}</span>
                  <span class="assertion-detail">
                    <span class="detail-item expected">
                      <span class="label">期望</span>
                      <span class="value" :class="{ null: item.expected === null && !item.expected_desc, object: typeof item.expected === 'object' }">
                        {{ item.expected_desc || (item.expected === null ? 'null' : (typeof item.expected === 'object' ? JSON.stringify(item.expected).substring(0, 30) + '...' : item.expected)) }}
                      </span>
                    </span>
                    <span class="separator">|</span>
                    <span class="detail-item actual" :class="{ mismatch: !item.passed && item.actual !== item.expected }">
                      <span class="label">实际</span>
                      <span class="value" :class="{ null: item.actual === null, object: typeof item.actual === 'object' }">
                        {{ item.actual === null ? 'null' : (typeof item.actual === 'object' ? JSON.stringify(item.actual).substring(0, 30) + '...' : item.actual) }}
                      </span>
                    </span>
                  </span>
                  <span v-if="item.error" class="assertion-error">{{ item.error }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { Search, Delete, DocumentChecked, DocumentCopy, RefreshRight, CircleCheck, CircleClose, WarningFilled } from '@element-plus/icons-vue'
import api from '@/utils/api'
import { deleteRequestHistory, batchDeleteRequestHistory } from '@/api/api-testing'
import dayjs from 'dayjs'
import HistoryTable from './components/HistoryTable.vue'

const { t } = useI18n()
const activeTab = ref('HTTP')
const httpHistory = ref([])
const websocketHistory = ref([])
const loading = ref(false)
const searchText = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const showDetailDialog = ref(false)
const selectedHistory = ref(null)
const detailTab = ref('request')

// 详情弹窗相关
const activeMainTab = ref('响应')
const activeRequestSubTab = ref('body')
const activeResponseSubTab = ref('json')

const requestSubTabs = [
  { label: 'BODY', value: 'body' },
  { label: 'HEADERS', value: 'headers' },
  { label: 'PARAMS', value: 'params' }
]

const responseSubTabs = [
  { label: 'BODY', value: 'body' },
  { label: 'HEADERS', value: 'headers' },
  { label: 'JSON', value: 'json' }
]

// 响应 Tab 列表（动态包含断言 Tab）
const responseTabs = computed(() => {
  const tabs = [
    { key: 'body', label: 'BODY' },
    { key: 'headers', label: 'HEADERS' },
    { key: 'json', label: 'JSON' }
  ]
  if (selectedHistory.value?.assertions_results?.length > 0) {
    tabs.push({ key: 'assertions', label: `断言(${selectedHistory.value.assertions_results.length})` })
  }
  return tabs
})

// 检查断言是否失败
const hasAssertionsFailed = (history) => {
  if (!history?.assertions_results || !Array.isArray(history.assertions_results)) {
    return false
  }
  return history.assertions_results.some(result => result.passed === false)
}

// 获取状态文本（仅基于状态码，用于列表）
const getStatusText = (status) => {
  if (!status) return '未知'
  if (status >= 200 && status < 300) return '通过'
  if (status >= 300 && status < 400) return '重定向'
  if (status >= 400) return '失败'
  return '未知'
}

// 获取详情页状态文本（同时考虑状态码和断言结果）
const getDetailStatusText = (history) => {
  const status = history?.status_code
  if (!status) return '未知'
  if (status >= 400) return '失败'
  // 检查断言是否失败
  if (hasAssertionsFailed(history)) return '失败'
  if (status >= 200 && status < 300) return '通过'
  if (status >= 300 && status < 400) return '重定向'
  return '未知'
}

// 格式化 JSON
const formatJson = (data) => {
  if (!data) return ''
  try {
    return JSON.stringify(data, null, 2)
  } catch (e) {
    return String(data)
  }
}

const currentHistory = computed(() => {
  return activeTab.value === 'HTTP' ? httpHistory.value : websocketHistory.value
})

const responseBodyText = computed(() => {
  if (!selectedHistory.value?.response_data) return ''
  
  try {
    if (selectedHistory.value.response_data.json) {
      return JSON.stringify(selectedHistory.value.response_data.json, null, 2)
    } else {
      return selectedHistory.value.response_data.body || ''
    }
  } catch (e) {
    return selectedHistory.value.response_data.body || ''
  }
})

const getMethodClass = (method) => {
  const classMap = {
    'GET': 'get',
    'POST': 'post',
    'PUT': 'put',
    'DELETE': 'delete',
    'PATCH': 'patch'
  }
  return classMap[method] || 'default'
}

const getStatusClass = (status) => {
  if (!status) return 'default'
  if (status >= 200 && status < 300) return 'success'
  if (status >= 300 && status < 400) return 'warning'
  if (status >= 400) return 'error'
  return 'default'
}

// 获取详情页状态样式（同时考虑状态码和断言结果）
const getDetailStatusClass = (history) => {
  const status = history?.status_code
  if (!status) return 'default'
  if (status >= 400) return 'error'
  // 检查断言是否失败
  if (hasAssertionsFailed(history)) return 'error'
  if (status >= 200 && status < 300) return 'success'
  if (status >= 300 && status < 400) return 'warning'
  return 'default'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

const formatHeaders = (headers) => {
  if (!headers || typeof headers !== 'object') return []
  return Object.keys(headers).map(key => ({
    key,
    value: headers[key]
  }))
}

const handleSearch = () => {
  currentPage.value = 1
  loadHistory()
}

const loadHistory = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      request__request_type: activeTab.value
    }

    if (searchText.value) {
      params.search = searchText.value
    }

    const response = await api.get('/api-testing/histories/', { params })
    const data = response.data.results || response.data

    if (activeTab.value === 'HTTP') {
      httpHistory.value = data
    } else {
      websocketHistory.value = data
    }

    total.value = response.data.count || data.length
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadHistory'))
    console.error(error)
  } finally {
    loading.value = false
  }
}

const onTabChange = () => {
  currentPage.value = 1
  loadHistory()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  loadHistory()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  loadHistory()
}

const viewDetail = (history) => {
  selectedHistory.value = history
  detailTab.value = 'request'
  activeMainTab.value = '请求'
  activeRequestSubTab.value = 'body'
  activeResponseSubTab.value = 'body'
  showDetailDialog.value = true
}

const retryRequest = async (history) => {
  try {
    const response = await api.post(`/api-testing/requests/${history.request.id}/execute/`, {
      environment_id: history.environment?.id
    })
    ElMessage.success(t('apiTesting.messages.success.requestRetried'))
    showDetailDialog.value = false
    await loadHistory()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.sendFailed'))
    console.error(error)
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(t('apiTesting.history.confirmDelete'), t('apiTesting.common.tip'), {
    confirmButtonText: t('apiTesting.common.confirm'),
    cancelButtonText: t('apiTesting.common.cancel'),
    type: 'warning'
  }).then(async () => {
    try {
      await deleteRequestHistory(row.id)
      ElMessage.success(t('apiTesting.messages.success.delete'))
      loadHistory()
    } catch (error) {
      console.error('Delete failed:', error)
      ElMessage.error(t('apiTesting.messages.error.deleteFailed'))
    }
  })
}

const formatResponseBody = () => {
  if (selectedHistory.value?.response_data?.json) {
    // 已经格式化了
  }
}

const copyResponseBody = () => {
  if (responseBodyText.value) {
    navigator.clipboard.writeText(responseBodyText.value)
    ElMessage.success(t('apiTesting.messages.success.copiedToClipboard'))
  }
}

onMounted(() => {
  loadHistory()
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
    gap: 12px;
  }

  .type-select {
    width: 160px;

    :deep(.el-select__wrapper) {
      background-color: #ffffff;
      border: 1px solid rgba(147, 112, 219, 0.2);
      border-radius: 8px;
      box-shadow: none;

      &:hover,
      &.is-focused {
        border-color: #7b42f6;
      }
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .search-input {
    width: 240px;

    :deep(.el-input__wrapper) {
      background-color: #ffffff;
      border-radius: 8px;
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;

      &:hover,
      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }

    :deep(.el-input__inner) {
      color: #5a32a3;
      font-weight: 500;
    }
  }
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 24px 0;
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  margin-bottom: 8px;
}

// 自定义表格样式
.custom-table {
  border: none;
  border-radius: 8px 8px 0 0;
  overflow: hidden;
  min-height: 200px;
  box-shadow: none;
  transition: all 0.3s ease;
  background-color: transparent !important;

  /* 覆盖 Element Plus 默认主题变量 */
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
    white-space: normal !important;
    line-height: 20px !important;
    word-break: break-word;
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
}

// 分页容器样式 - 参考 ProjectManagement.vue
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
        }

        &.is-active:hover {
          background: #ede9fe;
          border-color: #8b5cf6;
        }

        &.btn-quicknext,
        &.btn-quickprev {
          border: none;
          background: transparent;
          color: #9ca3af;

          &:hover {
            background: #f5f3ff;
            color: #8b5cf6;
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
          padding: 0 8px;

          &:hover,
          &.is-focus {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
          }
        }

        .el-input__inner {
          height: 32px;
          line-height: 32px;
          color: #374151;
          font-weight: 500;
          text-align: center;
        }
      }
    }
  }
}

// 操作按钮样式
.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 16px !important;
  border-radius: 8px;
  transition: all 0.3s ease;

  .el-icon {
    font-size: 14px;
  }

  span {
    font-size: 13px;
  }

  &.batch-delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover:not(:disabled) {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(255, 77, 79, 0.4);
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
}

// 详情抽屉样式
// 抽屉样式
:deep(.el-drawer) {
  .el-drawer__header {
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    padding: 20px 24px;
    border-bottom: 1px solid #ebeef5;
    margin: 0;

    .el-drawer__title {
      font-size: 18px;
      font-weight: 600;
      color: #5a32a3;
    }

    .el-drawer__close-btn {
      color: #7b42f6;
      font-size: 18px;

      &:hover {
        color: #5a32a3;
      }
    }
  }

  .el-drawer__body {
    padding: 20px;
    background: #fafbfc;
    height: 100%;
    overflow-y: auto;
  }
}

// 详情抽屉特定样式
:deep(.detail-drawer) {
  .el-drawer__body {
    padding: 0;
    height: calc(100vh - 60px);
    overflow-y: auto;
  }
}

/* 请求详情抽屉样式 - 现代简洁设计 */
.request-detail-drawer {
  padding: 24px;
  min-height: 100%;

  /* 顶部状态栏 - 无边框设计 */
  .request-header {
    padding: 0 0 20px 0;
    margin-bottom: 20px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);

    .request-title-row {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      flex-wrap: wrap;

      .request-name {
        font-size: 18px;
        font-weight: 600;
        color: #1a1a2e;
      }

      .method-tag {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;

        &.get {
          background: #e6f7ff;
          color: #1890ff;
        }

        &.post {
          background: #f6ffed;
          color: #52c41a;
        }

        &.put {
          background: #fff7e6;
          color: #fa8c16;
        }

        &.delete {
          background: #fff1f0;
          color: #f5222d;
        }

        &.patch {
          background: #e6fffb;
          color: #13c2c2;
        }
      }

      .status-tag {
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;

        &.success {
          background: #f6ffed;
          color: #52c41a;
        }

        &.failed, &.error {
          background: #fff1f0;
          color: #f5222d;
        }
      }

      .meta-tag {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;

        &.time-tag {
          background: #f0f5ff;
          color: #2f54eb;
        }

        &.code-tag {
          background: #f6ffed;
          color: #389e0d;
        }
      }
    }

    .request-url {
      font-size: 13px;
      color: #666;
      font-family: 'Courier New', Consolas, Monaco, monospace;
      word-break: break-all;
      padding: 8px 0;
    }
  }

  /* 错误横幅 - 简洁设计 */
  .error-banner {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 0;
    margin-bottom: 20px;
    border-bottom: 1px solid #ffccc7;

    .el-icon {
      font-size: 16px;
      color: #f5222d;
      margin-top: 2px;
      flex-shrink: 0;
    }

    span {
      font-size: 13px;
      color: #cf1322;
      line-height: 1.5;
    }
  }

  /* 数据区域 - 现代卡片式设计 */
  .data-section {
    margin-bottom: 24px;

    /* 主标签 - 简洁文字切换 */
    .main-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 24px;

      .main-tab-btn {
        display: flex;
        align-items: center;
        padding: 10px 20px;
        border: none;
        border-radius: 8px;
        background: transparent;
        color: #666;
        font-size: 15px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;

        &:hover {
          color: #333;
          background: #f5f5f5;
        }

        &.active {
          background: #7b42f6;
          color: #fff;
        }
      }
    }

    /* 数据面板 - 无边框直接展示 */
    .data-panel {
      .panel-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;

        .sub-tabs {
          display: flex;
          gap: 4px;

          .sub-tab-btn {
            padding: 6px 14px;
            border: none;
            border-radius: 6px;
            background: transparent;
            color: #666;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;

            &:hover {
              color: #333;
              background: #f0f0f0;
            }

            &.active {
              background: #f0e6ff;
              color: #7b42f6;
            }
          }
        }

        .data-badge {
          display: none;
        }
      }

      .code-container {
        background: transparent !important;
        border: none !important;

        .code-block {
          margin: 0;
          padding: 0;
          font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', Consolas, Monaco, monospace;
          font-size: 13px;
          line-height: 1.7;
          color: #333;
          white-space: pre-wrap;
          word-wrap: break-word;
          background: transparent !important;
          border: none !important;
        }
      }

      /* 断言容器 - 在响应 Tab 内 */
      .assertions-container {
        .assertion-list {
          padding: 8px 0;

          .assertion-item {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
            font-size: 13px;

            &:last-child {
              border-bottom: none;
              margin-bottom: 0;
            }

            .el-icon {
              font-size: 16px;
              flex-shrink: 0;
            }

            .assertion-name {
              flex-shrink: 0;
              color: #333;
              max-width: 150px;
              word-break: break-all;
            }

            .assertion-detail {
              flex: 1;
              display: flex;
              align-items: center;
              gap: 8px;
              font-size: 12px;
              flex-wrap: wrap;

              .detail-item {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 2px 8px;
                border-radius: 4px;
                background: #f5f5f5;
                font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;

                .label {
                  color: #999;
                  font-size: 11px;
                }

                .value {
                  color: #333;
                  font-weight: 500;

                  &.null {
                    color: #999;
                    font-style: italic;
                  }

                  &.object {
                    color: #1890ff;
                  }
                }

                &.expected {
                  background: #e6f7ff;
                  .label { color: #1890ff; }
                }

                &.actual {
                  background: #f6ffed;
                  .label { color: #52c41a; }

                  &.mismatch {
                    background: #fff2f0;
                    .label { color: #f5222d; }
                    .value { color: #f5222d; }
                  }
                }
              }

              .separator {
                color: #d9d9d9;
                font-size: 11px;
              }
            }

            .assertion-error {
              color: #f5222d;
              font-size: 12px;
              flex: 1;
              word-break: break-all;
              white-space: pre-wrap;
              overflow-wrap: break-word;
              line-height: 1.4;
            }

            &.passed {
              .el-icon {
                color: #52c41a;
              }
            }

            &.failed {
              .el-icon {
                color: #f5222d;
              }
            }
          }
        }
      }
    }
  }
}



@media screen and (max-width: 1200px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;

    .header-actions {
      width: 100%;
      flex-wrap: wrap;
    }

    .search-input {
      width: 100%;
      max-width: 300px;
    }
  }
}

@media screen and (max-width: 768px) {
  .page-container {
    padding: 16px;
    gap: 16px;
  }

  .page-header {
    padding: 16px 20px;

    .page-title {
      font-size: 18px;
    }
  }

  .card-container {
    padding: 12px 16px 16px;
  }

  .action-btn {
    span {
      display: none;
    }

    .el-icon {
      margin: 0;
    }
  }
}

@media screen and (max-width: 480px) {
  .page-container {
    padding: 12px;
    gap: 12px;
  }

  .page-header {
    padding: 14px 16px;

    .page-title {
      font-size: 16px;
    }
  }

  .card-container {
    padding: 8px 12px 12px;
  }
}
</style>
