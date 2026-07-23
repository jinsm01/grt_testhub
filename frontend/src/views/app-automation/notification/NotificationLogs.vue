<template>
  <div class="notification-logs">
    <!-- 搜索栏 -->
    <div class="filters">
      <el-input
        v-model="searchForm.taskName"
        placeholder="搜索任务名称"
        clearable
        class="filter-input"
        @clear="handleSearch"
        @input="handleSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select
        v-model="searchForm.status"
        placeholder="发送状态"
        clearable
        class="filter-select"
        popper-class="purple-select-dropdown"
        @change="handleSearch"
      >
        <el-option label="全部" value="" />
        <el-option label="发送成功" value="success" />
        <el-option label="发送失败" value="failed" />
        <el-option label="待发送" value="pending" />
      </el-select>
    </div>

    <!-- 列表 -->
    <div class="card-container">
      <el-table :data="logsData" v-loading="loading" stripe style="width: 100%" @sort-change="handleSortChange">
        <el-table-column prop="task_name" label="任务名称" min-width="150" sortable="custom" />
        <el-table-column label="任务类型" width="110">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.task_type_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="通知类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getNotificationTypeTag(row.actual_notification_type_display)" size="small">
              {{ row.actual_notification_type_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="通知时间" width="180" sortable="custom">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)" size="small">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="100">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchLogs"
          @current-change="fetchLogs"
        />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="通知详情" width="600px">
      <el-form v-if="selectedLog" label-position="top">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="任务名称"><span>{{ selectedLog.task_name }}</span></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="任务类型"><span>{{ selectedLog.task_type_display }}</span></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="通知类型">
              <el-tag :type="getNotificationTypeTag(selectedLog.actual_notification_type_display)">
                {{ selectedLog.actual_notification_type_display }}
              </el-tag>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-tag :type="getStatusTag(selectedLog.status)">{{ selectedLog.status_display }}</el-tag>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="通知时间"><span>{{ formatDate(selectedLog.created_at) }}</span></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发送时间"><span>{{ selectedLog.sent_at ? formatDate(selectedLog.sent_at) : '-' }}</span></el-form-item>
          </el-col>
          <el-col :span="24" v-if="selectedLog.webhook_bot_info && (selectedLog.webhook_bot_info.type || selectedLog.webhook_bot_info.bot_type)">
            <el-form-item label="Webhook机器人">
              <el-tag size="small" type="info">{{ selectedLog.webhook_bot_info.name || '默认机器人' }}</el-tag>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="通知内容">
              <div class="content-box">
                <div v-if="parsedContent" class="parsed-content">
                  <div v-for="(item, i) in parsedContent" :key="i" class="content-row">
                    <span class="label">{{ item.label }}:</span>
                    <span class="value">{{ item.value }}</span>
                  </div>
                </div>
                <pre v-else class="raw-content">{{ selectedLog.notification_content || '-' }}</pre>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="24" v-if="selectedLog.error_message">
            <el-form-item label="错误信息">
              <el-alert :title="selectedLog.error_message" type="error" show-icon :closable="false" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getAppNotificationLogs } from '@/api/app-automation.js'

defineOptions({ name: 'AppNotificationLogs' })

const loading = ref(false)
const logsData = ref([])
const detailVisible = ref(false)
const selectedLog = ref(null)

const searchForm = reactive({ taskName: '', status: '' })
const pagination = reactive({ currentPage: 1, pageSize: 10, total: 0 })
const sortParams = reactive({ prop: 'created_at', order: 'descending' })

onMounted(fetchLogs)

async function fetchLogs() {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      ordering: sortParams.order === 'ascending' ? sortParams.prop : `-${sortParams.prop}`,
    }
    if (searchForm.taskName) params.search = searchForm.taskName
    if (searchForm.status) params.status = searchForm.status
    const res = await getAppNotificationLogs(params)
    logsData.value = res.data.results || []
    pagination.total = res.data.count || 0
  } catch { ElMessage.error('加载通知日志失败') }
  finally { loading.value = false }
}

function handleSearch() { pagination.currentPage = 1; fetchLogs() }
function handleSortChange({ prop, order }) { sortParams.prop = prop; sortParams.order = order || 'descending'; fetchLogs() }
function viewDetail(row) { selectedLog.value = row; detailVisible.value = true }

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '-' }
function getStatusTag(s) { return { success: 'success', failed: 'danger', pending: 'info', sending: 'warning' }[s] || 'info' }
function getNotificationTypeTag(t) {
  if (!t || t === '-') return 'info'
  if (t.includes('邮箱')) return ''
  if (t.includes('机器人') || t.includes('Webhook')) return 'primary'
  return 'info'
}

const parsedContent = computed(() => {
  if (!selectedLog.value?.notification_content) return null
  const content = selectedLog.value.notification_content
  try {
    const json = JSON.parse(content)
    let text = ''
    if (json.markdown?.content) text = json.markdown.content
    else if (json.markdown?.text) text = json.markdown.text
    else if (json.card?.elements?.[0]?.text?.content) text = json.card.elements[0].text.content
    if (text) {
      return text.split('\n').filter(l => l.trim() && !l.includes('**')).map(l => {
        const idx = l.indexOf(':')
        return idx > 0 ? { label: l.substring(0, idx).trim(), value: l.substring(idx + 1).trim() } : null
      }).filter(Boolean)
    }
  } catch { /* fall through */ }
  // 纯文本
  const lines = content.split('\n').filter(l => l.trim())
  const result = lines.map(l => {
    const idx = l.indexOf(':')
    return idx > 0 ? { label: l.substring(0, idx).trim(), value: l.substring(idx + 1).trim() } : null
  }).filter(Boolean)
  return result.length ? result : null
})
</script>

<style scoped lang="scss">
.notification-logs { 
  padding: 24px; 
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
}
.filters {
  margin-bottom: 20px;
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(167, 139, 250, 0.08);
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;

  .filter-input { width: 240px; }
  .filter-select { width: 160px; }

  .filter-input,
  .filter-select {
    :deep(.el-input__wrapper) {
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
      border-radius: 8px;
      background-color: transparent;
      width: 100%;

      &:hover,
      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
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
      cursor: default;

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

    :deep(.el-table__sort-icon) {
      display: none;
    }

    :deep(.caret-wrapper) {
      display: none;
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
.content-box { width: 100%; }
.parsed-content { background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%); border-radius: 12px; padding: 16px; border: 1px solid rgba(167, 139, 250, 0.12); }
.content-row { display: flex; padding: 10px 0; border-bottom: 1px solid rgba(167, 139, 250, 0.12); }
.content-row:last-child { border-bottom: none; }
.label { font-weight: bold; color: #8b5cf6; min-width: 90px; margin-right: 12px; }
.value { color: #1a1a1a; flex: 1; word-break: break-word; }
.raw-content { white-space: pre-wrap; word-break: break-word; margin: 0; padding: 12px; background: rgba(167, 139, 250, 0.05); border-radius: 8px; font-size: 13px; max-height: 300px; overflow-y: auto; }

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

// 选择器下拉样式（与 api-testing/automation 保持一致）
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
</style>
