<template>
  <div class="page-container">
    <div class="filter-bar">
      <el-input
        v-model="searchText"
        :placeholder="$t('uiAutomation.ai.executionRecords.searchPlaceholder')"
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
        style="width: 300px;"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button v-if="false" class="reset-btn" @click="handleReset">{{ $t('uiAutomation.common.reset') }}</el-button>
      <el-button v-if="false" type="primary" class="query-btn" @click="handleSearch">
        <el-icon><Search /></el-icon>
        {{ $t('uiAutomation.common.search') }}
      </el-button>
      <div class="filter-bar-spacer"></div>
      <el-button
        v-if="selectedRecords.length > 0"
        type="danger"
        class="batch-delete-btn"
        @click="batchDeleteRecords"
        :loading="isDeleting"
      >
        <el-icon><Delete /></el-icon>
        {{ $t('uiAutomation.common.batchDelete') }}
      </el-button>
    </div>

    <div class="card-container">
      <el-table
        :data="records"
        v-loading="loading"
        stripe
        @selection-change="handleSelectionChange"
        ref="tableRef"
      >
        <el-table-column type="selection" width="55" header-align="center" align="center" />
        <el-table-column :label="$t('uiAutomation.ai.executionRecords.serialNumber')" width="80" header-align="center" align="center">
          <template #default="{ $index }">
            {{ getSerialNumber($index) }}
          </template>
        </el-table-column>
        <el-table-column prop="case_name" :label="$t('uiAutomation.ai.executionRecords.caseName')" min-width="200" show-overflow-tooltip header-align="center" align="left">
          <template #default="{ row }">
            <div class="case-name-cell">
              <el-tag v-if="row.ai_test_suite" type="warning" size="small" class="suite-tag">套件</el-tag>
              {{ row.case_name }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" :label="$t('uiAutomation.ai.executionRecords.status')" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="row.status">
              {{ getStatusText(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="duration" :label="$t('uiAutomation.ai.executionRecords.durationSeconds')" width="120" header-align="center" align="center">
          <template #default="{ row }">
            {{ row.duration ? row.duration.toFixed(2) : '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('uiAutomation.ai.executionRecords.startTime')" width="180" header-align="center" align="center">
          <template #default="{ row }">
            {{ formatDate(null, null, row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="executed_by.username" :label="$t('uiAutomation.ai.executionRecords.executor')" width="120" header-align="center" align="center" />
        <el-table-column :label="$t('uiAutomation.common.operation')" width="240" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" class="action-btn view-btn" @click="viewDetail(row)">
                <el-icon><View /></el-icon>
                <span>{{ $t('uiAutomation.ai.executionRecords.viewDetail') }}</span>
              </el-button>
              <el-button size="small" type="success" class="action-btn report-btn" @click="viewReport(row)">
                <el-icon><Document /></el-icon>
                <span>{{ $t('uiAutomation.ai.executionRecords.viewReport') }}</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handleCurrentChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="showDetailDialog" :title="$t('uiAutomation.ai.executionRecords.executionDetail')" size="1000px" direction="rtl">
      <div v-if="currentRecord" class="record-detail">
        <el-tabs v-model="detailActiveTab" @tab-change="handleDetailTabChange">
          <el-tab-pane :label="$t('uiAutomation.ai.executionRecords.executionLogs')" name="logs">
            <div class="log-container">
              <div
                v-for="(line, index) in formatLogLines(currentRecord.logs)"
                :key="index"
                :class="['log-line', getLogLineClass(line)]"
              >
                {{ line }}
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="$t('uiAutomation.ai.elementLocator.title')" name="elements">
            <div v-if="elementLoading" class="loading-container">
              <el-loading-directive />
            </div>
            <div v-else-if="elementError" class="error-container">
              <el-alert
                :title="elementError"
                type="error"
                show-icon
                :closable="false"
              />
            </div>
            <div v-else-if="!elementData" class="empty-container">
              <el-empty :description="$t('uiAutomation.ai.elementLocator.noData')" />
            </div>
            <div v-else class="element-locator-container">
              <div v-if="elementData.elements && elementData.elements.length > 0" class="elements-list">
                <el-table :data="elementData.elements" stripe style="width: 100%" class="locator-table">
                  <el-table-column type="index" :label="$t('uiAutomation.ai.elementLocator.step')" width="80" align="center" />
                  <el-table-column prop="element_name" :label="$t('uiAutomation.ai.elementLocator.elementName')" min-width="125" show-overflow-tooltip header-align="center" />
                  <el-table-column label="方式1" min-width="260" header-align="center">
                    <template #default="{ row }">
                      <div v-if="row.code_samples && row.code_samples.playwright && row.code_samples.playwright[0]" class="code-container">
                        <div class="code-block">
                          <pre><code>{{ row.code_samples.playwright[0].code }}</code></pre>
                          <el-tooltip content="复制" placement="top">
                            <el-button
                              size="small"
                              circle
                              class="copy-icon-btn"
                              @click="copyCode(row.code_samples.playwright[0].code)"
                            >
                              <el-icon><DocumentCopy /></el-icon>
                            </el-button>
                          </el-tooltip>
                        </div>
                      </div>
                      <span v-else>-</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="方式2" min-width="260" header-align="center">
                    <template #default="{ row }">
                      <div v-if="row.code_samples && row.code_samples.playwright && row.code_samples.playwright[1]" class="code-container">
                        <div class="code-block">
                          <pre><code>{{ row.code_samples.playwright[1].code }}</code></pre>
                          <el-tooltip content="复制" placement="top">
                            <el-button
                              size="small"
                              circle
                              class="copy-icon-btn"
                              @click="copyCode(row.code_samples.playwright[1].code)"
                            >
                              <el-icon><DocumentCopy /></el-icon>
                            </el-button>
                          </el-tooltip>
                        </div>
                      </div>
                      <span v-else>-</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>

              <div v-else class="no-elements">
                <el-empty :description="$t('uiAutomation.ai.elementLocator.noElements')" />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>


    </el-drawer>

    <!-- 报告对话框 -->
    <AIExecutionReport
      v-model="showReportDialog"
      :record-id="reportRecordId"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, View, Document, Search, DocumentCopy } from '@element-plus/icons-vue'
import { getAIExecutionRecords, batchDeleteAIExecutionRecords, extractElementsFromAIExecution } from '@/api/ui_automation'
import AIExecutionReport from './AIExecutionReport.vue'

const { t } = useI18n()
const router = useRouter()
const records = ref([])
const loading = ref(false)
const searchText = ref('')
const total = ref(0)
const pagination = reactive({
  currentPage: 1,
  pageSize: 10
})

const showDetailDialog = ref(false)
const currentRecord = ref(null)
let pollTimer = null

const selectedRecords = ref([])
const isDeleting = ref(false)
const tableRef = ref(null)

// 报告相关状态
const showReportDialog = ref(false)
const reportRecordId = ref(null)

// 详情抽屉标签页
const detailActiveTab = ref('logs')

// 元素提取相关状态
const elementLoading = ref(false)
const elementError = ref(null)
const elementData = ref(null)

// 加载记录列表
const loadRecords = async () => {
  loading.value = true
  try {
    const response = await getAIExecutionRecords({
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchText.value
    })

    records.value = response.data.results || []
    total.value = response.data.count || 0
    // 清空选择
    if (tableRef.value) {
      tableRef.value.clearSelection()
    }
  } catch (error) {
    console.error('获取执行记录失败:', error)
    ElMessage.error(t('uiAutomation.ai.executionRecords.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.currentPage = 1
  loadRecords()
}

const handleReset = () => {
  searchText.value = ''
  pagination.currentPage = 1
  loadRecords()
}

const handleSizeChange = () => {
  pagination.currentPage = 1
  loadRecords()
}

const handleCurrentChange = () => {
  loadRecords()
}

const viewDetail = (row) => {
  currentRecord.value = row
  showDetailDialog.value = true
}

// 查看报告
const viewReport = (row) => {
  router.push(`/ai-intelligent-mode/execution-report/${row.id}`)
}

// 从详情页打开报告
const openReportFromDetail = () => {
  if (currentRecord.value) {
    router.push(`/ai-intelligent-mode/execution-report/${currentRecord.value.id}`)
  }
}

// 加载元素提取数据
const loadElementData = async () => {
  if (!currentRecord.value?.id) return

  elementLoading.value = true
  elementError.value = null

  try {
    const response = await extractElementsFromAIExecution(currentRecord.value.id)
    elementData.value = response.data
  } catch (err) {
    console.error('Failed to load element data:', err)
    elementError.value = err.response?.data?.error || err.message || t('uiAutomation.ai.elementLocator.loadError')
  } finally {
    elementLoading.value = false
  }
}

// 详情抽屉标签页切换
const handleDetailTabChange = (tabName) => {
  if (tabName === 'elements' && !elementData.value && currentRecord.value?.id) {
    loadElementData()
  }
}

// 复制代码
const copyCode = async (code) => {
  try {
    await navigator.clipboard.writeText(code)
    ElMessage.success(t('uiAutomation.ai.elementLocator.copySuccess'))
  } catch (err) {
    console.error('Failed to copy code:', err)
    ElMessage.error(t('uiAutomation.ai.elementLocator.copyFailed'))
  }
}

const getStatusTag = (status) => {
  const map = {
    'pending': 'info',
    'running': 'warning',
    'passed': 'success',
    'failed': 'danger',
    'stopped': 'warning'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'pending': t('uiAutomation.status.pending'),
    'running': t('uiAutomation.status.running'),
    'passed': t('uiAutomation.status.success'),
    'failed': t('uiAutomation.status.failed'),
    'stopped': t('uiAutomation.status.stopped')
  }
  return map[status] || status
}

const formatDate = (row, column, cellValue) => {
  if (!cellValue) return ''
  return new Date(cellValue).toLocaleString()
}

// 将日志文本拆分为行数组
const formatLogLines = (logs) => {
  if (!logs) return []
  return logs.split('\n')
}

// 根据日志行内容判断样式类型
const getLogLineClass = (line) => {
  if (!line) return ''
  const trimmed = line.trim()

  // 分隔线：===== ... =====
  if (/^={3,}/.test(trimmed)) return 'log-separator'

  // 步骤标识：[Step X]
  if (/^\[Step\s+\d+\]/i.test(trimmed)) return 'log-step'

  // 错误/失败
  if (/错误|失败|exception|error|failed/i.test(trimmed)) return 'log-error'

  // 完成/成功
  if (/执行完成|完成|成功|success|done/i.test(trimmed)) return 'log-success'

  // 开始/启动
  if (/开始执行|启动|开始|starting/i.test(trimmed)) return 'log-start'

  // 执行动作
  if (/执行[：:]/.test(trimmed)) return 'log-action'

  // 提示信息
  if (/任务分析|等待|正在|加载/i.test(trimmed)) return 'log-info'

  return ''
}

// 获取序号
const getSerialNumber = (index) => {
  return (pagination.currentPage - 1) * pagination.pageSize + index + 1
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedRecords.value = selection
}

// 批量删除
const batchDeleteRecords = async () => {
  if (selectedRecords.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      t('uiAutomation.ai.executionRecords.messages.batchDeleteConfirm', { count: selectedRecords.value.length }),
      t('uiAutomation.ai.executionRecords.messages.batchDeleteTitle'),
      {
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel'),
        type: 'warning'
      }
    )

    isDeleting.value = true
    const ids = selectedRecords.value.map(item => item.id)
    await batchDeleteAIExecutionRecords(ids)

    ElMessage.success(t('uiAutomation.ai.executionRecords.messages.deleteSuccess'))

    // 如果当前页数据全部被删除，且不是第一页，则跳转到上一页
    if (records.value.length === ids.length && pagination.currentPage > 1) {
      pagination.currentPage--
    }

    loadRecords()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error(t('uiAutomation.ai.executionRecords.messages.batchDeleteFailed'))
    }
  } finally {
    isDeleting.value = false
  }
}



// 轮询更新状态
const startPolling = () => {
  pollTimer = setInterval(() => {
    // 只有在第一页且没有打开详情框且没有正在加载时才轮询
    if (pagination.currentPage === 1 && !showDetailDialog.value && !loading.value) {
      // 优化：检查当前列表是否有正在运行的任务，如果没有运行中的任务，则不轮询（或者降低频率）
      const hasActiveTasks = records.value.some(r => r.status === 'running' || r.status === 'pending')
      if (!hasActiveTasks) {
        return
      }

      // 静默刷新，不显示 loading
      getAIExecutionRecords({
        page: 1,
        page_size: pagination.pageSize
      }).then(response => {
        // 只有当没有选中项时才更新列表，避免干扰用户选择
        if (selectedRecords.value.length === 0) {
          records.value = response.data.results || []
          total.value = response.data.count || 0
        }
      }).catch(console.error)
    }
  }, 5000)
}

onMounted(() => {
  loadRecords()
  startPolling()
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>

<style lang="scss" scoped>
// 全局变量
:root {
  --primary-color: #667eea;
  --primary-dark: #764ba2;
  --primary-light: #f8f7ff;
  --primary-lighter: #fafbff;
  --border-color: #e8e8e8;
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

  // 待执行 - 蓝色
  &.pending {
    background: #e6f7ff;
    color: #1890ff;
  }

  // 运行中 - 橙色
  &.running {
    background: #fff7e6;
    color: #fa8c16;
  }

  // 通过 - 绿色
  &.passed {
    background: #f6ffed;
    color: #52c41a;
  }

  // 失败 - 红色
  &.failed {
    background: #fff1f0;
    color: #f5222d;
  }

  // 已停止 - 灰色
  &.stopped {
    background: #f5f5f5;
    color: #8c8c8c;
  }
}

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

// 页面头部
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 28px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.1);

  .page-title {
    font-size: 24px;
    font-weight: 700;
    color: #5a32a3;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .header-actions {
    display: flex;
    align-items: center;

    .batch-delete-btn {
      background: linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%) !important;
      border: none !important;
      color: white !important;
      font-weight: 600 !important;
      padding: 10px 20px !important;
      border-radius: 8px !important;
      transition: all 0.3s ease !important;
      box-shadow: 0 4px 12px rgba(255, 77, 79, 0.3) !important;

      .el-icon {
        margin-right: 6px;
      }

      &:hover:not(:disabled) {
        background: linear-gradient(135deg, #ff7875 0%, #ffa39e 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 77, 79, 0.4) !important;
      }

      &:active:not(:disabled) {
        transform: translateY(0) !important;
      }

      &:disabled {
        background: linear-gradient(135deg, #d9d9d9 0%, #bfbfbf 100%) !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
      }
    }
  }
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

  :deep(.el-input__wrapper) {
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

  .reset-btn {
    background: #f8f7ff !important;
    border: 1px solid rgba(147, 112, 219, 0.2) !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    padding: 9px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;

    &:hover {
      background: #ede9fe !important;
      border-color: #7b42f6 !important;
      transform: translateY(-1px);
    }
  }

  .query-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;
    transition: all 0.3s ease !important;

    .el-icon {
      margin-right: 6px;
    }

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4) !important;
    }
  }

  .filter-bar-spacer {
    flex: 1;
  }

  .batch-delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(255, 77, 79, 0.3) !important;

    .el-icon {
      margin-right: 6px;
    }

    &:hover:not(:disabled) {
      background: linear-gradient(135deg, #ff7875 0%, #ffa39e 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 20px rgba(255, 77, 79, 0.4) !important;
    }

    &:active:not(:disabled) {
      transform: translateY(0) !important;
    }

    &:disabled {
      background: linear-gradient(135deg, #d9d9d9 0%, #bfbfbf 100%) !important;
      box-shadow: none !important;
      cursor: not-allowed !important;
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

  // 表格样式
  .el-table {
    border: none;
    border-radius: 8px 8px 0 0;
    overflow: hidden;
    min-height: 200px;
    box-shadow: none;
    transition: all 0.3s ease;
    background-color: transparent !important;

    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: var(--primary-color);
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

    // 表头包装器
    :deep(.el-table__header-wrapper) {
      background-color: #ffffff !important;

      // 表头
      :deep(.el-table__header) {
        background-color: #ffffff !important;

        // 表头单元格
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

          // 表头单元格内部
          :deep(.cell) {
            background-color: #ffffff !important;
            color: #5a32a3 !important;
            font-weight: 600 !important;
          }
        }
      }
    }

    // 表格体包装器
    :deep(.el-table__body-wrapper) {
      background-color: #ffffff !important;

      // 表格行
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

        // 表格单元格
        :deep(td) {
          padding: 14px 16px;
          border-bottom: 1px solid #e9ecef;
          color: #333;
          font-size: 14px;
          font-weight: 400;
          line-height: 24px;
          transition: all 0.3s ease;

          // 标签样式
          .el-tag {
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            padding: 2px 8px;
            transition: all 0.3s ease;
          }

          // 按钮样式
          .el-button {
            font-size: 13px;
            padding: 0;
            margin-right: 12px;
            transition: all 0.3s ease;

            &:last-child {
              margin-right: 0;
            }

            &:hover {
              transform: translateY(-1px);
            }

            &.el-button--text {
              color: var(--primary-color);

              &:hover {
                color: var(--primary-dark);
                background: #f8f7ff;
                border-radius: 4px;
              }
            }
          }
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

    // 确保整个表格容器都使用正确的背景色
    &.el-table--enable-row-hover {
      background-color: #ffffff !important;
    }

    // 覆盖表格行的默认样式
    :deep(.el-table__row) {
      background-color: #ffffff !important;
    }

    // 覆盖表格行的条纹样式
    :deep(.el-table__row.el-table__row--striped) {
      background-color: #fafaff !important;
    }

    // 覆盖表格行的 hover 样式
    :deep(.el-table__row:hover) {
      background-color: #f8f7ff !important;
    }

    // 直接覆盖表头单元格样式
    :deep(.el-table__header th) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }

    // 覆盖表头单元格内容样式
    :deep(.el-table__header th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
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
        }
      }

      // 跳转输入框
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
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px !important;
  border-radius: 8px;
  transition: all 0.3s ease;

  .el-icon {
    font-size: 14px;
  }

  span {
    font-size: 12px;
  }

  &.view-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }

  &.report-btn {
    background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }

  &.element-btn {
    background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #40a9ff 0%, #1890ff 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }
}

// 详情对话框样式
.record-detail {
  display: flex;
  flex-direction: column;
  height: 100%;

  .detail-item {
    margin-bottom: 15px;
    .label {
      font-weight: bold;
      margin-right: 10px;
      color: #5a32a3;
    }
  }

  .log-container {
    flex: 1;
    min-height: 0;
    background-color: #fafbfc;
    color: #2c3e50;
    padding: 20px;
    border-radius: 8px;
    overflow-y: auto;
    font-family: 'SF Mono', 'Fira Code', 'Source Code Pro', 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.8;
    border: 1px solid #e9ecef;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.04);

    .log-line {
      white-space: pre-wrap;
      word-wrap: break-word;
      letter-spacing: 0.3px;
      padding: 1px 0;
      transition: background-color 0.15s ease;
      border-radius: 3px;
      padding-left: 6px;
      margin-left: -6px;

      &:hover {
        background-color: rgba(90, 50, 163, 0.06);
      }

      // 分隔线 =====
      &.log-separator {
        color: #7b42f6;
        font-weight: 700;
        margin: 8px 0;
        letter-spacing: 1px;
      }

      // 步骤标识 [Step X]
      &.log-step {
        color: #7b42f6;
        font-weight: 600;
        margin-top: 6px;
      }

      // 执行动作
      &.log-action {
        color: #1890ff;
        padding-left: 16px;
      }

      // 开始信息
      &.log-start {
        color: #52c41a;
        font-weight: 600;
      }

      // 完成/成功
      &.log-success {
        color: #52c41a;
        font-weight: 600;
      }

      // 错误/失败
      &.log-error {
        color: #f5222d;
        font-weight: 600;
        background-color: rgba(245, 34, 45, 0.06);
      }

      // 提示信息
      &.log-info {
        color: #8c8c8c;
        font-style: italic;
      }
    }
  }

}

.mt-15 {
  margin-top: 15px;
}

.case-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  line-height: 1.6;
}

.suite-tag {
  flex-shrink: 0;
  border-radius: 4px;
  padding: 0 6px;
  height: 22px;
  font-size: 12px;
  font-weight: 500;
}

// 元素提取相关样式
.loading-container {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-container,
.empty-container,
.no-elements {
  padding: 40px 0;
}

.element-locator-container {
  .elements-list {
    margin-top: 0;
  }

  .locator-table {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e9ecef;

    :deep(.el-table__header-wrapper) {
      th {
        background-color: #f8f7ff !important;
        color: #5a32a3;
        font-weight: 600;
        font-size: 13px;
        padding: 12px;
        border-bottom: 1px solid #e9ecef;

        .cell {
          color: #5a32a3;
          font-weight: 600;
        }
      }
    }

    :deep(.el-table__row) {
      transition: background-color 0.2s ease;

      td {
        padding: 12px;
        font-size: 13px;
        color: #333;
        border-bottom: 1px solid #f0f0f0;
        vertical-align: top;
      }

      &:hover {
        background-color: #f8f7ff !important;
      }

      &.el-table__row--striped {
        background-color: #fafaff !important;
      }
    }

    :deep(.el-tag) {
      border-radius: 4px;
      font-weight: 500;
    }
  }

  .code-container {
    .code-block {
      position: relative;
      background-color: #f8f9fa;
      border: 1px solid #e9ecef;
      border-radius: 6px;
      padding: 10px 36px 10px 12px;
      transition: all 0.2s ease;

      &:hover {
        border-color: #c2a9f3;
        box-shadow: 0 2px 8px rgba(162, 128, 227, 0.08);
      }

      pre {
        margin: 0;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 12px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-all;
        color: #303133;
      }

      code {
        font-family: inherit;
        font-size: inherit;
        line-height: inherit;
        color: inherit;
        white-space: pre-wrap;
        word-break: break-all;
      }
    }

    .copy-icon-btn {
      position: absolute;
      top: 6px;
      right: 6px;
      width: 24px;
      height: 24px;
      padding: 0;
      background: #fff;
      border: 1px solid #e9ecef;
      color: #a78bfa;
      opacity: 0;
      transition: all 0.2s ease;

      &:hover {
        background: #f8f7ff;
        border-color: #a78bfa;
        color: #5a32a3;
      }
    }

    .code-block:hover .copy-icon-btn {
      opacity: 1;
    }
  }
}
</style>
