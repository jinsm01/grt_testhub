<template>
  <div class="author-testcase-detail-container">


    <!-- 目录列表 - 可展开收起 -->
    <div class="directory-tree-container">
      <div
        v-for="(group, index) in groupedCases"
        :key="group.directory"
        class="directory-group"
        :class="{ expanded: expandedDirectories.includes(group.directory) }"
      >
        <!-- 目录头部 - 点击展开/收起 -->
        <div
          class="directory-header-row"
          @click="toggleDirectory(group.directory)"
        >
          <div class="directory-header-left">
            <el-icon class="expand-icon">
              <ArrowRight v-if="!expandedDirectories.includes(group.directory)" />
              <ArrowDown v-else />
            </el-icon>
            <span class="directory-name">{{ getDirectoryName(group.directory) }}</span>
            <span class="case-count">{{ group.count || 0 }} 个用例</span>
          </div>
          <div class="directory-header-right">
            <el-dropdown v-if="group.cases && group.cases.length > 0" @command="(cmd) => handleBatchReviewForDirectory(cmd, group)" @click.stop>
              <el-button link size="small" class="batch-action-btn" @click.stop>
                <el-icon><Operation /></el-icon>
                <span>批量操作</span>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="approved">
                    <span class="dropdown-status approved">批量通过</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="rejected">
                    <span class="dropdown-status rejected">批量拒绝</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="pending">
                    <span class="dropdown-status pending">批量待审</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- 展开后的用例列表 -->
        <div v-show="expandedDirectories.includes(group.directory)" class="case-list-wrapper">
          <el-table
            :data="group.cases || []"
            style="width: 100%"
            v-loading="loading"
            row-key="id"
            @selection-change="(selection) => handleSelectionChange(selection, group.directory)"
            :ref="(el) => setTableRef(el, group.directory)"
          >
            <el-table-column type="selection" width="55" align="center" />
            <el-table-column prop="title" label="用例标题" min-width="400">
              <template #default="{ row }">
                <span class="case-title-link" @click="goToDetail(row)">
                  {{ row.title }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="priority" label="用例级别" width="110" align="center">
              <template #default="{ row }">
                <span class="badge" :class="`badge-priority-${row.priority}`">
                  {{ getPriorityLabel(row.priority) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120" align="center">
              <template #default="{ row }">
                <span class="badge" :class="`badge-status-${row.status}`">
                  {{ getStatusLabel(row.status) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="review_status" label="审核结果" width="115" align="center">
              <template #default="{ row }">
                <span class="badge" :class="`badge-review-${row.review_status || 'pending'}`">
                  {{ getReviewStatusLabel(row.review_status) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="author" label="创建人" width="120" align="center">
              <template #default="{ row }">
                <span class="author-text">{{ row.author?.username || row.author?.name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160" align="center">
              <template #default="{ row }">
                <span class="time-text">{{ formatDate(row.created_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="210" align="center" fixed="right">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button
                    v-if="row.review_status !== 'approved' && row.author?.id !== currentUser?.id"
                    size="small"
                    type="success"
                    class="action-btn run-btn"
                    @click="handleReviewStatusChange('approved', row)"
                  >
                    <el-icon><Check /></el-icon>
                    <span>通过</span>
                  </el-button>
                  <el-button
                    v-if="row.review_status !== 'rejected' && row.author?.id !== currentUser?.id"
                    size="small"
                    type="danger"
                    class="action-btn delete-btn"
                    @click="handleReviewStatusChange('rejected', row)"
                  >
                    <el-icon><Close /></el-icon>
                    <span>拒绝</span>
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 空状态 -->
      <el-empty v-if="groupedCases.length === 0" description="暂无数据" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Folder, ArrowDown, ArrowRight, Operation, Check, Close } from '@element-plus/icons-vue'
import { getAuthorTestCases, getTestCaseStatistics, updateTestCase, batchUpdateReviewStatus } from '@/api/testcases'
import { useUserStore } from '@/stores/user'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 当前登录用户
const currentUser = computed(() => userStore.user)

// 数据
const loading = ref(false)
const author = ref('')
const groupedCases = ref([])
const totalCases = ref(0)
const selectedMonth = ref('')
const selectedPriority = ref('')
const monthlyStats = ref([])
const priorityStats = ref({})
const reviewStats = ref({ approved: 0, rejected: 0, pending: 0 })
const expandedDirectories = ref([])
const tableRefs = ref({})
const selectedCasesByDirectory = ref({})

// 计算目录数量
const directoryCount = computed(() => groupedCases.value.length)

// 设置表格引用
function setTableRef(el, directory) {
  if (el) {
    tableRefs.value[directory] = el
  }
}

// 切换目录展开/收起
function toggleDirectory(dirPath) {
  const index = expandedDirectories.value.indexOf(dirPath)
  if (index > -1) {
    expandedDirectories.value.splice(index, 1)
  } else {
    expandedDirectories.value.push(dirPath)
  }
}

// 获取目录名称
function getDirectoryName(path) {
  return path.split('/').pop() || path
}

// 初始化
onMounted(async () => {
  author.value = String(route.params.author || route.query.author || '')
  selectedMonth.value = String(route.query.month || '')

  // 加载月份统计数据用于筛选
  await loadMonthStats()

  // 加载用例数据
  await loadData()
})

// 加载月份统计数据
async function loadMonthStats() {
  try {
    const res = await getTestCaseStatistics()
    monthlyStats.value = res.data.monthly_stats || []
  } catch (error) {
    console.error('加载月份统计失败:', error)
  }
}

// 加载数据
async function loadData() {
  if (!author.value) {
    ElMessage.error('未指定作者')
    return
  }

  loading.value = true
  try {
    const params = { username: author.value }
    if (selectedMonth.value) {
      params.month = selectedMonth.value
    }
    if (selectedPriority.value) {
      params.priority = selectedPriority.value
    }

    const res = await getAuthorTestCases(params)
    groupedCases.value = res.data.grouped || []
    totalCases.value = res.data.total || 0
    priorityStats.value = res.data.priority_stats || {}
    reviewStats.value = res.data.review_stats || {}

    // 默认展开第一个目录
    if (groupedCases.value.length > 0) {
      expandedDirectories.value = [groupedCases.value[0].directory]
    }
  } catch (error) {
    console.error('加载失败:', error)
    ElMessage.error('加载用例详情失败')
  } finally {
    loading.value = false
  }
}

// 返回上一页
function goBack() {
  router.back()
}

// 跳转用例详情
function goToDetail(row) {
  if (row.menu_id) {
    router.push({
      name: 'TestCases',
      query: {
        menu: row.menu_id,
        highlight: row.id
      }
    })
  } else {
    router.push({
      name: 'TestCases',
      query: { highlight: row.id }
    })
  }
}

// 获取优先级标签
function getPriorityLabel(priority) {
  const map = { critical: 'P0', high: 'P1', medium: 'P2', low: 'P3' }
  return map[priority] || priority
}

// 获取优先级类型
function getPriorityType(priority) {
  const map = { critical: 'danger', high: 'warning', medium: 'info', low: 'success' }
  return map[priority] || ''
}

// 获取状态标签
function getStatusLabel(status) {
  const map = { active: '激活', draft: '草稿', deprecated: '废弃' }
  return map[status] || status
}

// 获取状态类型
function getStatusType(status) {
  const map = { active: 'success', draft: 'info', deprecated: 'danger' }
  return map[status] || ''
}

// 获取审核结果标签
function getReviewStatusLabel(status) {
  const map = { none: '未审核', pending: '待审核', approved: '已通过', rejected: '已拒绝' }
  return map[status] || status || '未审核'
}

// 获取审核结果类型
function getReviewStatusType(status) {
  const map = { none: 'info', pending: 'warning', approved: 'success', rejected: 'danger' }
  return map[status] || 'info'
}

// 格式化日期（年月日）
function formatDate(dateString) {
  if (!dateString) return '-'
  return dayjs(dateString).format('YYYY-MM-DD')
}

// 监听筛选条件变化
watch([selectedMonth, selectedPriority], () => {
  loadData()
})

// 处理表格选择变化
function handleSelectionChange(selection, directory) {
  selectedCasesByDirectory.value[directory] = selection.map(item => item.id)
}

// 获取所有选中的用例ID
const allSelectedCaseIds = computed(() => {
  const ids = []
  Object.values(selectedCasesByDirectory.value).forEach(dirIds => {
    ids.push(...dirIds)
  })
  return ids
})

// 处理批量审核（针对某个目录）
async function handleBatchReviewForDirectory(command, group) {
  const selectedIds = selectedCasesByDirectory.value[group.directory] || []
  if (selectedIds.length === 0) {
    ElMessage.warning('请先选择用例')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${selectedIds.length} 条用例审核结果设为「${getReviewStatusLabel(command)}」吗？`,
      '批量审核确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await batchUpdateReviewStatus({
      ids: selectedIds,
      review_status: command
    })

    ElMessage.success('批量审核成功')
    selectedCasesByDirectory.value[group.directory] = []
    // 清除表格选中状态
    const tableRef = tableRefs.value[group.directory]
    if (tableRef && tableRef.clearSelection) {
      tableRef.clearSelection()
    }
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量审核失败:', error)
      ElMessage.error('批量审核失败')
    }
  }
}

// 处理审核状态变更
async function handleReviewStatusChange(newStatus, caseRow) {
  try {
    await updateTestCase(caseRow.id, { review_status: newStatus })
    caseRow.review_status = newStatus
    ElMessage.success('审核状态已更新')
  } catch (error) {
    console.error('更新审核状态失败:', error)
    ElMessage.error('更新审核状态失败')
    // 回滚选择
    await loadData()
  }
}
</script>

<style lang="scss" scoped>
.author-testcase-detail-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

// 单行头部统计卡片 - 参考 XMindConverter 风格
.header-stats-card {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 16px 24px;

  // 单行布局
  &.single-line {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;

    .back-btn {
      border-radius: 8px;
      color: #6b7280;
      border-color: #e5e7eb;
      flex-shrink: 0;
      padding: 8px 16px;

      &:hover {
        color: #7b42f6;
        border-color: #7b42f6;
        background: rgba(123, 66, 246, 0.05);
      }
    }

    // 内联统计
    .stats-inline {
      display: flex;
      align-items: center;
      gap: 24px;
      flex: 1;
      justify-content: center;

      .stat-item {
        display: flex;
        align-items: baseline;
        gap: 8px;

        .stat-label {
          font-size: 13px;
          color: #6b7280;
          font-weight: 400;
        }

        .stat-value {
          font-size: 18px;
          font-weight: 600;
          color: #374151;

          &.primary {
            color: #7b42f6;
          }

          &.success {
            color: #22c55e;
          }

          &.warning {
            color: #f59e0b;
          }

          &.danger {
            color: #ef4444;
          }
        }
      }
    }

    // 筛选器
    .header-filters {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;

      .month-select {
        width: 130px;

        :deep(.el-input__wrapper) {
          box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
          border-radius: 8px;
          background: #ffffff;

          &:hover,
          &:focus {
            box-shadow: 0 0 0 1px #7b42f6;
          }
        }
      }

      .priority-filter {
        :deep(.el-radio-button__inner) {
          border-color: rgba(147, 112, 219, 0.25);
          background: #ffffff;
          color: #6b7280;
          padding: 6px 14px;

          &:hover {
            color: #7b42f6;
          }
        }

        :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
          background: linear-gradient(135deg, #7b42f6 0%, #6d28d9 100%);
          border-color: #7b42f6;
          color: #ffffff;
          box-shadow: -1px 0 0 0 #7b42f6;
        }
      }
    }
  }
}

// 目录树容器
.directory-tree-container {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .directory-group {
    background: #ffffff;
    border: 1px solid rgba(147, 112, 219, 0.12);
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
    overflow: hidden;
    transition: all 0.3s ease;

    &.expanded {
      box-shadow: 0 8px 24px rgba(147, 112, 219, 0.12);
    }
  }

  // 目录头部行 - 简洁风格
  .directory-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px;
    cursor: pointer;
    background: #ffffff;
    border-bottom: 1px solid rgba(147, 112, 219, 0.08);
    transition: all 0.2s ease;

    &:hover {
      background: #faf9ff;
    }

    .directory-header-left {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;

      .expand-icon {
        font-size: 12px;
        color: #9ca3af;
        transition: all 0.2s ease;
      }

      .directory-name {
        font-size: 14px;
        font-weight: 500;
        color: #374151;
      }

      .case-count {
        font-size: 12px;
        color: #9ca3af;
        font-weight: 400;
      }
    }

    .directory-header-right {
      flex-shrink: 0;

      .batch-action-btn {
        color: #7b42f6;
        font-weight: 500;

        &:hover {
          color: #5a32a3;
        }

        .el-icon {
          margin-right: 4px;
        }
      }
    }
  }

  // 展开状态下的头部样式
  &.expanded .directory-header-row {
    background: #f9f7ff;
    border-bottom-color: rgba(147, 112, 219, 0.15);

    .expand-icon {
      color: #7b42f6;
      transform: rotate(90deg);
    }

    .directory-name {
      color: #5a32a3;
      font-weight: 600;
    }
  }

  // 用例列表包装器
  .case-list-wrapper {
    padding: 0;
    animation: slideDown 0.3s ease;

    @keyframes slideDown {
      from {
        opacity: 0;
        transform: translateY(-10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    :deep(.el-table) {
      --el-table-header-bg-color: #fafafa;
      --el-table-header-text-color: #6b7280;
      --el-table-row-hover-bg-color: #faf9ff;
      --el-table-border-color: transparent;

      .el-table__header-wrapper {
        th {
          font-weight: 500;
          font-size: 12px;
          padding: 10px 16px;
          background-color: #fafafa;
          color: #6b7280;
          border-bottom: 1px solid #f0f0f0;

          .cell {
            line-height: 1.4;
          }
        }
      }

      .el-table__row {
        transition: all 0.2s ease;

        &:hover {
          background-color: #faf9ff;
        }

        td {
          padding: 12px 16px;
          border-bottom: 1px solid #f5f5f5;
        }

        &:last-child td {
          border-bottom: none;
        }
      }

      .el-table__inner-wrapper::before {
        display: none;
      }

      // 复选框列样式优化
      .el-table-column--selection .cell {
        padding-left: 20px;
      }
    }
  }
}

// 表格工具栏
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);

  .toolbar-title {
    font-size: 15px;
    font-weight: 600;
    color: #5a32a3;
    display: flex;
    align-items: center;
    gap: 8px;

    .current-dir {
      background: #ede9fe;
      color: #5a32a3;
      border: none;
    }
  }
}

// 用例标题链接
.case-title-link {
  color: #7b42f6;
  cursor: pointer;
  font-weight: 500;
  transition: color 0.2s ease;

  &:hover {
    color: #5a32a3;
    text-decoration: underline;
  }
}

// 创建人样式
.author-text {
  color: #6b7280;
  font-size: 13px;
}

// 徽章样式
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;

  &.badge-author {
    background: #f3f4f6;
    color: #6b7280;
  }

  &.badge-priority-critical {
    background: #fef2f2;
    color: #dc2626;
  }

  &.badge-priority-high {
    background: #fff7ed;
    color: #ea580c;
  }

  &.badge-priority-medium {
    background: #eff6ff;
    color: #2563eb;
  }

  &.badge-priority-low {
    background: #f0fdf4;
    color: #16a34a;
  }

  &.badge-status-active {
    background: #f0fdf4;
    color: #16a34a;
  }

  &.badge-status-draft {
    background: #f3f4f6;
    color: #6b7280;
  }

  &.badge-status-deprecated {
    background: #fef2f2;
    color: #dc2626;
  }

  &.badge-review-approved {
    background: #f0fdf4;
    color: #16a34a;
  }

  &.badge-review-rejected {
    background: #fef2f2;
    color: #dc2626;
  }

  &.badge-review-pending,
  &.badge-review-none {
    background: #fffbeb;
    color: #d97706;
  }

  .badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }
}

// 操作按钮样式
.action-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;

  .action-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px !important;
    border-radius: 6px;
    transition: all 0.3s ease;
    border: none !important;
    color: #ffffff !important;

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
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
      }
    }

    &.delete-btn {
      background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;

      &:hover {
        background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
      }
    }
  }
}

// 下拉状态样式
.dropdown-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;

  &.approved {
    color: #16a34a;
  }

  &.rejected {
    color: #dc2626;
  }

  &.pending {
    color: #d97706;
  }
}
</style>
