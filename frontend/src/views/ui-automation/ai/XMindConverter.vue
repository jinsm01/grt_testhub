<template>
  <div class="page-container">
    <!-- 历史记录筛选栏 - 包含文件选择和信息展示 -->
    <div class="filter-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索文件名"
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
        style="width: 300px;"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <div class="filter-bar-spacer"></div>
      <!-- 选择文件按钮和文件信息区域 -->
      <input
        ref="fileInput"
        type="file"
        accept=".xmind"
        @change="handleFileChange"
        class="hidden-input"
        style="display: none;"
      />
      <!-- 未选择文件时显示选择按钮 -->
      <el-button
        v-if="!selectedFile"
        type="primary"
        class="select-file-btn"
        @click="triggerFileSelect"
        :disabled="converting"
      >
        <el-icon><FolderOpened /></el-icon>
        选择文件
      </el-button>
      <!-- 选择文件后显示文件信息和操作 -->
      <div v-else class="selected-file-info">
        <span
          class="file-name-text clickable"
          :title="selectedFile.name"
          @click="triggerFileSelect"
        >
          {{ selectedFile.name.replace(/\.xmind$/i, '') }}
        </span>
        <el-button
          type="primary"
          size="small"
          :loading="converting"
          :disabled="converting"
          @click="handleConvert"
        >
          {{ converting ? '转换中' : '开始转换' }}
        </el-button>
      </div>
    </div>

    <!-- 历史记录列表 -->
    <div class="card-container history-card">
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="records"
        stripe
        style="width: 100%"
      >
        <el-table-column label="序号" width="80" header-align="center" align="center">
          <template #default="{ $index }">
            {{ (currentPage - 1) * pageSize + $index + 1 }}
          </template>
        </el-table-column>

        <el-table-column label="文件名" min-width="150" show-overflow-tooltip header-align="center" align="left">
          <template #default="{ row }">
            <span>{{ row.file_name }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="row.status">
              {{ row.status_display }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="用例数量" min-width="80" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.test_case_count > 0" class="count-badge">
              {{ row.test_case_count }}
            </span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column label="创建人" width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.created_by">{{ row.created_by.username }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="200" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="260" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" class="action-btn edit-btn" @click="viewDetail(row)">
                <el-icon><View /></el-icon>
                <span>查看</span>
              </el-button>
              <el-button
                v-if="row.status === 'success'"
                size="small"
                type="success"
                class="action-btn run-btn"
                @click="downloadFile(row)"
              >
                <el-icon><Download /></el-icon>
                <span>下载</span>
              </el-button>
              <el-button
                size="small"
                type="danger"
                class="action-btn delete-btn"
                @click="handleDelete(row)"
              >
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

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="导入记录详情"
      width="80%"
      :close-on-click-modal="false"
      class="detail-dialog"
    >
      <div v-if="currentRecord" class="detail-content">
        <!-- 错误信息 -->
        <div v-if="currentRecord.error_message" class="detail-section">
          <h3 class="section-title error-title">错误信息</h3>
          <el-alert
            :title="currentRecord.error_message"
            type="error"
            :closable="false"
            show-icon
          />
        </div>

        <!-- Tab 页签 -->
        <el-tabs v-if="currentRecord.import_data && currentRecord.import_data.length > 0" v-model="detailActiveTab" class="detail-tabs">
          <el-tab-pane label="测试用例数据" name="cases">
            <el-table
              :data="currentRecord.import_data"
              stripe
              border
              max-height="450"
              style="width: 100%"
            >
              <el-table-column type="index" label="序号" width="60" align="center" />
              <el-table-column label="用例名称" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">
                  <span class="case-name">{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="所属模块" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ row.suite || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="前置条件" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ row.preconditions || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="优先级" width="70" align="center">
                <template #default="{ row }">
                  <el-tag :type="getPriorityType(row.importance)" effect="plain" size="small">
                    {{ getPriorityText(row.importance) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="执行方式" width="90" align="center">
                <template #default="{ row }">
                  <span style="white-space: nowrap;">{{ row.execution_type === 2 ? '自动' : '手动' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="步骤数" width="70" align="center">
                <template #default="{ row }">
                  {{ row.steps?.length || 0 }}
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="测试步骤详情" name="steps">
            <el-collapse>
              <el-collapse-item
                v-for="(testCase, index) in (showAllSteps ? currentRecord.import_data : currentRecord.import_data.slice(0, 5))"
                :key="index"
                :title="`${Number(index) + 1}. ${testCase.name}`"
              >
                <div v-if="testCase.steps && testCase.steps.length > 0" class="steps-list">
                  <div
                    v-for="(step, stepIndex) in testCase.steps"
                    :key="stepIndex"
                    class="step-item"
                  >
                    <div class="step-header">
                      <span class="step-number">步骤 {{ step.step_number }}</span>
                    </div>
                    <div class="step-content">
                      <div class="step-row">
                        <span class="step-label">操作：</span>
                        <span class="step-value">{{ step.actions }}</span>
                      </div>
                      <div v-if="step.expectedresults" class="step-row">
                        <span class="step-label">预期结果：</span>
                        <span class="step-value">{{ step.expectedresults }}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <el-empty v-else description="暂无步骤数据" />
              </el-collapse-item>
            </el-collapse>
            <div v-if="currentRecord.import_data.length > 5 && !showAllSteps" class="more-cases-tip" @click="showAllSteps = true">
              <span class="expand-link">展开全部 {{ currentRecord.import_data.length }} 条用例</span>
            </div>
            <div v-if="showAllSteps && currentRecord.import_data.length > 5" class="more-cases-tip" @click="showAllSteps = false">
              <span class="collapse-link">收起用例</span>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Upload, FolderOpened, Document, Delete, Right, Loading,
  Search, Refresh, Clock, View, Download
} from '@element-plus/icons-vue'
import { convertXMindToExcel, getXmindImportRecords, getXmindImportRecordDetail, downloadXmindImportFile, deleteXmindImportRecord } from '@/api/ui_automation'

// ============ 文件转换相关 ============
const isDragOver = ref(false)
const selectedFile = ref(null)
const converting = ref(false)
const fileInput = ref(null)
const tableRef = ref(null)

const triggerFileSelect = () => {
  fileInput.value.click()
}

const handleFileChange = (event) => {
  const file = event.target.files[0]
  if (file) {
    validateAndSelectFile(file)
  }
}

const handleDrop = (event) => {
  isDragOver.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) {
    validateAndSelectFile(files[0])
  }
}

const validateAndSelectFile = (file) => {
  if (!file.name.endsWith('.xmind')) {
    ElMessage.error('请上传 .xmind 格式的文件')
    return
  }
  selectedFile.value = file
}

const clearFile = () => {
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const handleConvert = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择 XMind 文件')
    return
  }

  converting.value = true
  try {
    await convertXMindToExcel(selectedFile.value)

    ElMessage.success('转换成功！')

    // 刷新历史记录列表
    fetchRecords()
    // 清除已选文件
    clearFile()
  } catch (error) {
    console.error('转换失败:', error)
    let errorMessage = '转换失败，请重试'

    // 尝试从错误响应中获取详细错误信息
    if (error.response && error.response.data) {
      try {
        // 如果错误响应是 JSON 格式
        const errorData = JSON.parse(new TextDecoder().decode(error.response.data))
        errorMessage = errorData.error || errorMessage
      } catch {
        // 如果不是 JSON 格式，使用默认错误消息
        errorMessage = '转换失败，请检查 XMind 文件格式是否正确'
      }
    }

    ElMessage.error(errorMessage)
  } finally {
    converting.value = false
  }
}

// 下载文件
const downloadFile = async (row) => {
  // 检查状态，只有成功的记录才能下载
  if (row.status !== 'success') {
    ElMessage.warning('该记录尚未转换成功，无法下载')
    return
  }

  try {
    const response = await downloadXmindImportFile(row.id)

    // 检查响应是否是错误信息（blob 类型的错误响应）
    if (response.data.type === 'application/json') {
      // 如果是 JSON 类型，说明是错误响应
      const errorText = await response.data.text()
      const errorData = JSON.parse(errorText)
      ElMessage.error(errorData.error || '下载失败')
      return
    }

    // 处理文件下载
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

    // 从响应头中获取文件名，如果没有则使用原始文件名替换扩展名
    const contentDisposition = response.headers['content-disposition']
    let fileName = row.file_name.replace('.xmind', '.xlsx')  // 默认使用原始文件名
    if (contentDisposition) {
      const fileNameMatch = contentDisposition.match(/filename="?([^"]+)"?/)
      if (fileNameMatch && fileNameMatch[1]) {
        fileName = fileNameMatch[1]
      }
    }

    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('文件下载成功')
  } catch (error) {
    console.error('下载失败:', error)
    // 尝试解析错误信息
    if (error.response) {
      console.error('错误响应状态:', error.response.status)
      console.error('错误响应头:', error.response.headers)
      try {
        // 如果错误响应是 blob 类型，需要转换为文本
        if (error.response.data instanceof Blob) {
          const errorText = await error.response.data.text()
          console.error('错误响应内容:', errorText)
          try {
            const errorData = JSON.parse(errorText)
            ElMessage.error(errorData.error || errorData.detail || '文件下载失败')
          } catch {
            ElMessage.error('文件下载失败: ' + errorText)
          }
          return
        }
      } catch (e) {
        console.error('解析错误响应失败:', e)
      }
    }
    ElMessage.error('文件下载失败: ' + (error.message || '未知错误'))
  }
}

// ============ 历史记录相关 ============
const loading = ref(false)
const records = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')

// 详情对话框
const detailDialogVisible = ref(false)
const currentRecord = ref(null)
const detailActiveTab = ref('cases')  // 'cases' | 'steps'
const showAllSteps = ref(false)  // 是否展开所有测试步骤

// 获取列表数据
const fetchRecords = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined
    }
    const response = await getXmindImportRecords(params)
    records.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    console.error('获取导入记录失败:', error)
    ElMessage.error('获取导入记录失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  fetchRecords()
}

// 刷新
const refreshData = () => {
  searchQuery.value = ''
  currentPage.value = 1
  fetchRecords()
}

// 分页
const handleSizeChange = (val) => {
  pageSize.value = val
  fetchRecords()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchRecords()
}

// 查看详情
const viewDetail = async (row) => {
  detailDialogVisible.value = true
  currentRecord.value = null
  showAllSteps.value = false  // 重置展开状态
  detailActiveTab.value = 'cases'  // 默认显示用例数据页签

  try {
    const response = await getXmindImportRecordDetail(row.id)
    currentRecord.value = response.data
  } catch (error) {
    console.error('获取详情失败:', error)
    ElMessage.error('获取详情失败')
    detailDialogVisible.value = false
  }
}

// 删除记录
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除导入记录 "${row.file_name}" 吗？删除后将无法恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteXmindImportRecord(row.id)
    ElMessage.success('删除成功')

    // 刷新列表
    fetchRecords()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败，请重试')
    }
  }
}

// 状态标签类型
const getStatusType = (status) => {
  const typeMap = {
    'success': 'success',
    'failed': 'danger',
    'processing': 'warning',
    'pending': 'info'
  }
  return typeMap[status] || 'info'
}

// 优先级标签类型
const getPriorityType = (priority) => {
  const typeMap = {
    1: 'danger',    // P0
    2: 'warning',   // P1
    3: 'info',      // P2
    4: 'success'    // P3
  }
  return typeMap[priority] || 'info'
}

// 优先级文本
const getPriorityText = (priority) => {
  const textMap = {
    1: 'P0',
    2: 'P1',
    3: 'P2',
    4: 'P3'
  }
  return textMap[priority] || 'P0'
}

// 格式化日期时间
const formatDateTime = (datetime) => {
  if (!datetime) return '-'
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  fetchRecords()
})

// 在页面切换回来时刷新表格布局，修复固定列显示异常问题
onActivated(() => {
  nextTick(() => {
    if (tableRef.value) {
      tableRef.value.doLayout()
    }
  })
})
</script>

<style lang="scss" scoped>
.page-container {
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

  .page-title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #5a32a3;
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
  padding: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 4px solid #7b42f6;
  color: #5a32a3;
  display: flex;
  justify-content: space-between;
  align-items: center;
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

  .filter-bar-spacer {
    flex: 1;
  }

  // 选择文件按钮样式
  .select-file-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    border: none;
    font-weight: 600;
    padding: 10px 20px;

    .el-icon {
      margin-right: 4px;
    }

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }

    &:disabled {
      background: #d1d5db;
      transform: none;
      box-shadow: none;
    }
  }

  // 选中文件后的内联信息展示
  .selected-file-info {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 6px 6px 14px;
    background: #f8f7ff;
    border: 1px solid rgba(123, 66, 246, 0.12);
    border-radius: 8px;
    transition: all 0.25s ease;

    &:hover {
      background: #f0edff;
      border-color: rgba(123, 66, 246, 0.2);
    }

    .file-name-text {
      font-size: 14px;
      font-weight: 600;
      color: #5a32a3;
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;

      &.clickable {
        cursor: pointer;
        padding: 4px 8px;
        margin: -4px -8px;
        border-radius: 6px;
        transition: all 0.2s ease;

        &:hover {
          background: rgba(123, 66, 246, 0.1);
          color: #6d33e6;
        }
      }
    }

    .el-button {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 32px;
      padding: 0 14px;
      border-radius: 6px;
      font-weight: 500;
      font-size: 13px;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      border: 1px solid transparent;

      &--primary {
        background: #7b42f6;
        border-color: #7b42f6;
        color: #ffffff;

        &:hover:not(:disabled) {
          background: #6d33e6;
          border-color: #6d33e6;
          transform: translateY(-2px);
          box-shadow: 0 4px 14px rgba(123, 66, 246, 0.35);
        }

        &:active:not(:disabled) {
          transform: translateY(0);
          background: #5a32a3;
        }
      }
    }
  }
}

// 历史记录样式
.history-card {
  flex: 1;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
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

    // 表头包装器
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
      padding: 0 !important;
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

    // 直接覆盖表头单元格内容样式
    :deep(.el-table__header th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }

    // 修复固定列在路由切换时的显示问题
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
      background: #fff1f0;
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
  }

  // 数量徽章样式
  .count-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 24px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 500;
    background: #e6f7ff;
    color: #1890ff;
    white-space: nowrap;
  }

  // 时间文本样式
  .time-text {
    color: #666;
    font-size: 14px;
    white-space: nowrap;
  }

  .text-gray {
    color: #999;
  }
}

// 操作按钮样式 - 使用 .page-container 作为前缀避免样式冲突
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
      border: none !important;
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

// 详情对话框样式
.detail-dialog {
  :deep(.el-dialog__body) {
    max-height: 70vh;
    overflow-y: auto;
    padding: 20px;
  }
}

.detail-content {
  .detail-section {
    margin-bottom: 25px;

    &:last-child {
      margin-bottom: 0;
    }

    .section-title {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 15px;
      padding-left: 10px;
      border-left: 4px solid #409eff;

      &.error-title {
        border-left-color: #f56c6c;
      }
    }
  }

  // Tab 页签样式
  .detail-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 16px;
    }

    :deep(.el-tabs__nav-wrap::after) {
      background-color: rgba(123, 66, 246, 0.1);
    }

    :deep(.el-tabs__item) {
      font-size: 14px;
      font-weight: 500;
      color: #666;

      &:hover {
        color: #7b42f6;
      }

      &.is-active {
        color: #7b42f6;
        font-weight: 600;
      }
    }

    :deep(.el-tabs__active-bar) {
      background-color: #7b42f6;
    }

    :deep(.el-tab-pane) {
      max-height: 500px;
      overflow-y: auto;
    }
  }
}

.case-name {
  font-weight: 500;
  color: #303133;
}

.steps-list {
  padding: 10px;

  .step-item {
    margin-bottom: 15px;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 6px;

    &:last-child {
      margin-bottom: 0;
    }

    .step-header {
      margin-bottom: 8px;

      .step-number {
        font-weight: 600;
        color: #7b42f6;
      }
    }

    .step-content {
      .step-row {
        margin-bottom: 5px;

        &:last-child {
          margin-bottom: 0;
        }

        .step-label {
          font-weight: 500;
          color: #606266;
        }

        .step-value {
          color: #303133;
        }
      }
    }
  }
}

.more-cases-tip {
  text-align: center;
  padding: 15px;
  color: #909399;
  font-size: 14px;
  cursor: pointer;

  .expand-link,
  .collapse-link {
    color: #7b42f6;
    font-weight: 500;
    transition: all 0.2s ease;

    &:hover {
      color: #6d33e6;
      text-decoration: underline;
    }
  }
}
</style>
