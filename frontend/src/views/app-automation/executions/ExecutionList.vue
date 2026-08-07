<template>
  <div class="execution-list">
    <!-- 工具栏 -->
    <el-card class="toolbar" shadow="never">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-input
            v-model="searchQuery"
            placeholder="搜索用例名称、设备"
            clearable
            @clear="loadExecutions"
            @keyup.enter="loadExecutions"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="4">
          <el-select v-model="projectFilter" placeholder="全部项目" clearable filterable @change="loadExecutions">
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select
            v-model="statusFilter"
            placeholder="执行状态"
            clearable
            @change="loadExecutions"
          >
            <el-option label="全部状态" value="" />
            <el-option label="等待中" value="pending" />
            <el-option label="执行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="执行异常" value="error" />
            <el-option label="已停止" value="stopped" />
          </el-select>
        </el-col>
        <el-col :span="10" class="text-right">
          <!-- 刷新按钮已隐藏 -->
        </el-col>
      </el-row>
    </el-card>
    
    <!-- 执行记录列表 -->
    <div class="card-container">
      <el-table
        v-loading="loading"
        :data="executions"
        stripe
        style="width: 100%"
      >
        <el-table-column label="测试用例" min-width="180">
          <template #default="{ row }">
            <el-link v-if="row.report_path" type="primary" @click="viewReport(row)">{{ row.case_name }}</el-link>
            <span v-else>{{ row.case_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="device_name" label="设备" width="150" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="getDisplayStatus(row.status, row.result).class">
              {{ getDisplayStatus(row.status, row.result).text }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress || 0"
              :status="row.status === 'error' ? 'exception' : row.result === 'failed' ? 'exception' : row.result === 'passed' ? 'success' : undefined"
            />
          </template>
        </el-table-column>
        <el-table-column label="步骤统计" width="220" align="center">
          <template #default="{ row }">
            <div class="count-cell">
              <span class="count-badge success">
                <el-icon><CircleCheck /></el-icon>
                {{ row.passed_steps || 0 }}
              </span>
              <span class="count-badge failed">
                <el-icon><CircleClose /></el-icon>
                {{ row.failed_steps || 0 }}
              </span>
              <span class="count-badge total">
                <el-icon><DataLine /></el-icon>
                总计 {{ row.total_steps || 0 }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column prop="user_name" label="执行人" width="100" />
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column label="结束时间" width="160">
          <template #default="{ row }">
            {{ row.finished_at ? formatDateTime(row.finished_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                v-if="row.status === 'running'"
                size="small"
                class="action-btn stop-btn"
                @click="stopExecution(row)"
              >
                <el-icon><VideoPause /></el-icon>
                <span>停止</span>
              </el-button>
              <el-button
                v-if="row.report_path"
                size="small"
                class="action-btn report-btn"
                @click="viewReport(row)"
              >
                <el-icon><Document /></el-icon>
                <span>报告</span>
              </el-button>
              <el-button
                v-if="row.error_message"
                size="small"
                class="action-btn error-btn"
                @click="viewError(row)"
              >
                <el-icon><Warning /></el-icon>
                <span>错误</span>
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
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadExecutions"
          @current-change="loadExecutions"
        />
      </div>
    </div>
    
    <!-- 错误信息对话框 -->
    <el-dialog
      v-model="errorDialogVisible"
      title="错误信息"
      width="600px"
    >
      <div class="error-content">
        <pre>{{ currentError }}</pre>
      </div>
      <template #footer>
        <el-button type="primary" @click="errorDialogVisible = false">
          关闭
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getExecutionList,
  stopExecution as apiStopExecution,
  getAppProjects
} from '@/api/app-automation'
import { Search, Refresh, VideoPause, Document, Warning, CircleCheck, CircleClose, DataLine } from '@element-plus/icons-vue'
import { getExecutionStatusType, getExecutionStatusText, getDisplayStatus, formatDateTime } from '@/utils/app-automation-helpers'

const loading = ref(false)
const executions = ref([])
const searchQuery = ref('')
const statusFilter = ref('')
const projectFilter = ref(null)
const projectList = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const errorDialogVisible = ref(false)
const currentError = ref('')

let refreshTimer = null

const loadExecutions = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value,
      status: statusFilter.value
    }
    if (projectFilter.value) params.project = projectFilter.value
    const res = await getExecutionList(params)
    executions.value = res.data.results || []
    total.value = res.data.count || 0
  } catch (error) {
    ElMessage.error('加载执行记录失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const stopExecution = async (execution) => {
  try {
    await ElMessageBox.confirm(
      '确定要停止该执行吗？',
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
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('停止失败: ' + (error.message || '未知错误'))
    }
  }
}

const viewReport = (execution) => {
  if (!execution || !execution.id) {
    ElMessage.warning('执行记录ID无效')
    return
  }
  
  const reportUrl = `/api/app-automation/executions/${execution.id}/report/`
  
  // 在新标签页打开报告
  window.open(reportUrl, '_blank')
}

const viewError = (execution) => {
  currentError.value = execution.error_message
  errorDialogVisible.value = true
}

// getDisplayStatus 已从 helpers 导入

const formatDuration = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${Math.floor(seconds)}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${minutes}分${secs}秒`
}

// 自动刷新执行中的记录
const startAutoRefresh = () => {
  refreshTimer = setInterval(() => {
    // 如果有执行中的记录，自动刷新
    const hasRunning = executions.value.some(e => ['running', 'pending'].includes(e.status))
    if (hasRunning) {
      loadExecutions()
    }
  }, 5000) // 每5秒刷新一次
}

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(() => {
  getAppProjects({ page_size: 100 }).then(res => { projectList.value = res.data.results || res.data || [] }).catch(() => {})
  loadExecutions()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped lang="scss">
.execution-list {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
}

.toolbar {
  margin-bottom: 20px;
  
  .text-right {
    text-align: right;
  }
}

.execution-list {
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

// 数量徽章容器
.count-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
}

// 数量徽章样式
.count-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  color: #0369a1;
  white-space: nowrap;
  line-height: 1.2;

  .el-icon {
    font-size: 12px;
  }

  &.success {
    background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
    color: #047857;
  }

  &.failed {
    background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
    color: #b91c1c;
  }

  &.total {
    background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%);
    color: #5b21b6;
  }
}

.step-stats {
  display: flex;
  gap: 8px;
  font-size: 12px;
  
  .stat-item {
    &.success { color: #67c23a; }
    &.danger { color: #f56c6c; }
  }
}

.error-content {
  max-height: 400px;
  overflow-y: auto;
  
  pre {
    background: #f5f7fa;
    padding: 15px;
    border-radius: 4px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-wrap: break-word;
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

    &.stop-btn {
      background: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #ffa940 0%, #fa8c16 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(250, 140, 22, 0.4);
      }
    }

    &.report-btn {
      background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #40a9ff 0%, #1890ff 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
      }
    }

    &.error-btn {
      background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
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
</style>
