<template>
  <div class="author-testcase-detail-container">

    <!-- 全局筛选栏 - 白底容器 -->
    <div class="global-filter-bar">
      <div class="filter-left">
        <el-select v-model="globalPriorityFilter" placeholder="优先级筛选" clearable @change="handleGlobalPriorityFilterChange" style="width: 150px;">
          <el-option label="全部" value="" />
          <el-option label="P0" value="P0" />
          <el-option label="P1" value="P1" />
          <el-option label="P2" value="P2" />
          <el-option label="P3" value="P3" />
        </el-select>
        <el-select v-model="globalReviewFilter" placeholder="审核结果筛选" clearable @change="handleGlobalReviewFilterChange" style="width: 150px;">
          <el-option label="全部" value="" />
          <el-option label="已通过" value="approved" />
          <el-option label="已拒绝" value="rejected" />
          <el-option label="待审核" value="pending" />
        </el-select>
      </div>
    <!-- 全局操作按钮 -->
    <div class="filter-right">
      <el-button
        type="primary"
        class="action-btn ai-review-btn"
        @click="handleAIReview"
      >
        <el-icon><MagicStick /></el-icon>
        <span>一键AI审核</span>
      </el-button>
      <template v-if="hasSelectedCases">
        <el-button
          class="action-btn preview-btn"
          @click="openGlobalBatchPreviewDrawer"
        >
          <el-icon><List /></el-icon>
          <span>批量审核</span>
        </el-button>
        <el-button
          type="success"
          class="action-btn"
          @click="handleGlobalBatchReview('approved')"
        >
          <el-icon><CircleCheckFilled /></el-icon>
          <span>一键通过</span>
        </el-button>
        <el-button
          type="danger"
          class="action-btn"
          @click="handleGlobalBatchReview('rejected')"
        >
          <el-icon><CircleCloseFilled /></el-icon>
          <span>一键拒绝</span>
        </el-button>
      </template>
    </div>
    </div>

    <!-- 目录列表 - 可展开收起 -->
    <div class="directory-tree-container">
      <div
        v-for="(group, index) in groupedCases"
        :key="group.directory"
        class="directory-group"
        :class="{ expanded: expandedDirectories.includes(group.directory) }"
      >
        <!-- 目录卡片 - 点击展开/收起 -->
        <div
          class="directory-card"
          @click="toggleDirectory(group.directory)"
        >
          <div class="directory-card-content">
            <el-icon class="directory-icon">
              <Folder />
            </el-icon>
            <span class="directory-name">{{ getDirectoryName(group.directory) }}</span>
            <span class="directory-count">({{ group.cases.length }} 个用例)</span>
          </div>
          <el-icon class="expand-arrow" :class="{ 'is-expanded': expandedDirectories.includes(group.directory) }">
            <ArrowRight />
          </el-icon>
        </div>

        <!-- 展开后的用例列表 -->
        <div v-show="expandedDirectories.includes(group.directory)" class="case-list-wrapper">
          <el-table
            :data="getFilteredCases(group)"
            style="width: 100%"
            v-loading="loading"
            row-key="id"
            @selection-change="(selection) => handleSelectionChange(selection, group.directory)"
            :ref="(el) => setTableRef(el, group.directory)"
          >
            <el-table-column type="selection" width="55" align="center" :reserve-selection="true" />
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
                <span
                  class="badge"
                  :class="[`badge-review-${row.review_status || 'pending'}`, row.review_status === 'rejected' ? 'badge-review-rejected-clickable' : '']"
                  @click="handleReviewBadgeClick(row)"
                >
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
          </el-table>
        </div>
      </div>

      <!-- 空状态 -->
      <el-empty v-if="groupedCases.length === 0" description="暂无数据" />
    </div>

    <!-- 批量预览抽屉 -->
    <el-drawer
      v-model="batchPreviewDrawerVisible"
      title="批量审核"
      size="60%"
      :destroy-on-close="true"
      :close-on-click-modal="false"
      class="batch-review-drawer"
    >
      <div class="batch-preview-container">
        <div v-for="testCase in previewCases" :key="testCase.id" class="preview-case-item">
          <div class="preview-case-header">
            <h4 class="preview-case-title">{{ testCase.title }}</h4>
            <div class="preview-case-actions">
              <!-- 已通过状态：只显示拒绝按钮 -->
              <template v-if="testCase.review_status === 'approved'">
                <el-button
                  size="small"
                  type="default"
                  @click="handlePreviewCaseReview('rejected', testCase)"
                >
                  <el-icon><Close /></el-icon>
                  <span>拒绝</span>
                </el-button>
              </template>
              <!-- 已拒绝状态：只显示通过按钮 -->
              <template v-else-if="testCase.review_status === 'rejected'">
                <el-button
                  size="small"
                  type="success"
                  @click="handlePreviewCaseReview('approved', testCase)"
                >
                  <el-icon><Check /></el-icon>
                  <span>通过</span>
                </el-button>
              </template>
              <!-- 待审核状态：显示通过和拒绝两个按钮 -->
              <template v-else>
                <el-button
                  size="small"
                  type="success"
                  @click="handlePreviewCaseReview('approved', testCase)"
                >
                  <el-icon><Check /></el-icon>
                  <span>通过</span>
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  @click="handlePreviewCaseReview('rejected', testCase)"
                >
                  <el-icon><Close /></el-icon>
                  <span>拒绝</span>
                </el-button>
              </template>
            </div>
          </div>
          <div class="preview-case-meta">
            <span class="meta-item">
              <span class="meta-label">优先级:</span>
              <span class="badge" :class="`badge-priority-${testCase.priority}`">
                {{ getPriorityLabel(testCase.priority) }}
              </span>
            </span>
            <span class="meta-item">
              <span class="meta-label">状态:</span>
              <span class="badge" :class="`badge-status-${testCase.status}`">
                {{ getStatusLabel(testCase.status) }}
              </span>
            </span>
            <span class="meta-item">
              <span class="meta-label">审核:</span>
              <span class="badge" :class="`badge-review-${testCase.review_status || 'pending'}`">
                {{ getReviewStatusLabel(testCase.review_status) }}
              </span>
            </span>
          </div>
          <div class="preview-case-content">
            <!-- 用例详情表格：前置条件、测试步骤、预期结果 -->
            <div class="content-section case-detail-section" v-if="testCase.precondition || testCase.steps || testCase.expected_result">
              <div class="case-detail-table" :style="{ '--row-span': getStepCount(testCase.steps, testCase.expected_result) }">
                <div class="table-header">
                  <div class="header-cell precondition-cell">前置条件</div>
                  <div class="header-cell steps-cell">测试步骤</div>
                  <div class="header-cell result-cell">预期结果</div>
                </div>
                <div class="table-body">
                  <template v-for="(row, index) in parseCaseDetail(testCase.precondition, testCase.steps, testCase.expected_result)" :key="index">
                    <div class="table-row">
                      <!-- 第一行显示前置条件，跨所有行 -->
                      <div v-if="index === 0 && testCase.precondition" class="table-cell precondition-cell">
                        <pre>{{ testCase.precondition }}</pre>
                      </div>
                      <div class="table-cell steps-cell">{{ row.step || '-' }}</div>
                      <div class="table-cell result-cell">{{ row.result || '-' }}</div>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 拒绝原因弹窗 -->
    <el-dialog
      v-model="reasonDialogVisible"
      title="拒绝原因"
      width="520px"
      align-center
      :close-on-click-modal="false"
      class="reason-dialog"
    >
      <div class="reason-content">
        <pre>{{ currentReason }}</pre>
      </div>
      <template #footer>
        <el-button @click="reasonDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Folder, ArrowDown, ArrowRight, Operation, Check, Close, View, List, CircleCheckFilled, CircleCloseFilled, MagicStick } from '@element-plus/icons-vue'
import { getAuthorTestCases, getTestCaseStatistics, updateTestCase, batchUpdateReviewStatus, aiReviewTestCases } from '@/api/testcases'
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
const priorityFilter = ref({})
const globalPriorityFilter = ref('')
const globalReviewFilter = ref('')

// 批量预览抽屉
const batchPreviewDrawerVisible = ref(false)
const previewCases = ref([])
const currentPreviewDirectory = ref('')

// 拒绝原因弹窗
const reasonDialogVisible = ref(false)
const currentReason = ref('')

// 一键AI审核规则弹窗
const aiReviewDialogVisible = ref(false)
const aiReviewRules = [
  '测试步骤不能少于3步',
  '用例名称必填且全局不重复',
  '前置条件不能为空',
  '主线用例只描述当前最新功能，步骤和预期不能包含【原有规则】【调整】【历史数据】',
  '相同归属目录下：P0 ≤ 3 个，P1 ≤ 10 个，P2~P4 不限',
  '相同归属目录下，不同用例的测试步骤和预期结果重复率不能100%'
]

// 计算目录数量
const directoryCount = computed(() => groupedCases.value.length)

// 计算是否有选中的用例（全局）
const hasSelectedCases = computed(() => {
  return Object.values(selectedCasesByDirectory.value).some(cases => cases && cases.length > 0)
})

// 获取所有选中的用例（全局）
const getAllSelectedCases = computed(() => {
  const allCases = []
  const selectedIds = allSelectedCaseIds.value
  if (selectedIds.length === 0) {
    return allCases
  }
  // 从 groupedCases 中查找对应的用例对象
  groupedCases.value.forEach(group => {
    const cases = group.cases || []
    cases.forEach(testCase => {
      if (selectedIds.includes(testCase.id)) {
        allCases.push(testCase)
      }
    })
  })
  return allCases
})

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
async function loadData(keepExpanded = false) {
  if (!author.value) {
    ElMessage.error('未指定作者')
    return
  }

  loading.value = true
  // 保存当前展开的目录状态
  const currentExpandedDirs = keepExpanded ? [...expandedDirectories.value] : []

  try {
    const params = { username: author.value }
    if (selectedMonth.value) {
      params.month = selectedMonth.value
    }
    if (selectedPriority.value) {
      params.priority = selectedPriority.value
    }

    const res = await getAuthorTestCases(params)
    // 过滤掉"能力点"目录
    groupedCases.value = (res.data.grouped || []).filter(group => {
      const dirName = getDirectoryName(group.directory)
      return dirName !== '能力点'
    })
    totalCases.value = res.data.total || 0
    priorityStats.value = res.data.priority_stats || {}
    reviewStats.value = res.data.review_stats || {}

    // 恢复展开的目录状态，或者默认收起所有目录
    if (keepExpanded) {
      expandedDirectories.value = currentExpandedDirs
    } else {
      expandedDirectories.value = []
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
  router.push({
    name: 'TestCaseDetail',
    params: { id: row.id }
  })
}

// 处理优先级筛选变化
function handlePriorityFilterChange(directory, priority) {
  // 筛选后清空当前目录的选中状态
  if (selectedCasesByDirectory.value[directory]) {
    selectedCasesByDirectory.value[directory] = []
  }
  // 使用 nextTick 确保表格数据更新后再清空选中状态
  nextTick(() => {
    const tableRef = tableRefs.value[directory]
    if (tableRef) {
      tableRef.clearSelection()
    }
  })
}

// 全局优先级筛选变化处理
function handleGlobalPriorityFilterChange(priority) {
  // 同步到所有目录的筛选器
  groupedCases.value.forEach(group => {
    priorityFilter.value[group.directory] = priority
    // 清空选中状态
    if (selectedCasesByDirectory.value[group.directory]) {
      selectedCasesByDirectory.value[group.directory] = []
    }
    nextTick(() => {
      const tableRef = tableRefs.value[group.directory]
      if (tableRef) {
        tableRef.clearSelection()
      }
    })
  })
}

// 全局审核结果筛选变化处理
function handleGlobalReviewFilterChange(reviewStatus) {
  // 清空选中状态
  groupedCases.value.forEach(group => {
    if (selectedCasesByDirectory.value[group.directory]) {
      selectedCasesByDirectory.value[group.directory] = []
    }
    nextTick(() => {
      const tableRef = tableRefs.value[group.directory]
      if (tableRef) {
        tableRef.clearSelection()
      }
    })
  })
}

// 获取筛选后的用例列表
function getFilteredCases(group) {
  const cases = group.cases || []
  const priorityFilterValue = priorityFilter.value[group.directory]
  const reviewFilterValue = globalReviewFilter.value

  let filteredCases = cases

  // 优先级筛选
  if (priorityFilterValue) {
    filteredCases = filteredCases.filter(c => getPriorityLabel(c.priority) === priorityFilterValue)
  }

  // 审核结果筛选
  if (reviewFilterValue) {
    filteredCases = filteredCases.filter(c => {
      const status = c.review_status || 'none'
      if (reviewFilterValue === 'pending') {
        return status === 'pending' || status === 'none'
      }
      return status === reviewFilterValue
    })
  }

  return filteredCases
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

  let review_comment = ''
  if (command === 'rejected') {
    try {
      const { value } = await ElMessageBox.prompt('请输入拒绝理由', '批量拒绝', {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '拒绝理由不能为空'
          }
          return true
        }
      })
      review_comment = value.trim()
    } catch (error) {
      return
    }
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
      review_status: command,
      review_comment
    })

    ElMessage.success('批量审核成功')
    selectedCasesByDirectory.value[group.directory] = []
    // 清除表格选中状态
    const tableRef = tableRefs.value[group.directory]
    if (tableRef && tableRef.clearSelection) {
      tableRef.clearSelection()
    }
    await loadData(true)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量审核失败:', error)
      ElMessage.error('批量审核失败')
    }
  }
}

// 全局批量审核
async function handleGlobalBatchReview(command) {
  const allSelectedIds = getAllSelectedCases.value.map(c => c.id)
  if (allSelectedIds.length === 0) {
    ElMessage.warning('请先选择用例')
    return
  }

  let review_comment = ''
  if (command === 'rejected') {
    try {
      const { value } = await ElMessageBox.prompt('请输入拒绝理由', '批量拒绝', {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '拒绝理由不能为空'
          }
          return true
        }
      })
      review_comment = value.trim()
    } catch (error) {
      return
    }
  }

  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${allSelectedIds.length} 条用例审核结果设为「${getReviewStatusLabel(command)}」吗？`,
      '批量审核确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await batchUpdateReviewStatus({
      ids: allSelectedIds,
      review_status: command,
      review_comment
    })

    ElMessage.success('批量审核成功')
    // 清空所有选中状态
    Object.keys(selectedCasesByDirectory.value).forEach(key => {
      selectedCasesByDirectory.value[key] = []
    })
    // 清除所有表格选中状态
    Object.values(tableRefs.value).forEach(tableRef => {
      if (tableRef && tableRef.clearSelection) {
        tableRef.clearSelection()
      }
    })
    await loadData(true)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量审核失败:', error)
      ElMessage.error('批量审核失败')
    }
  }
}

// 一键AI审核
async function handleAIReview() {
  try {
    await ElMessageBox.confirm(
      '确定对当前作者所有待审核用例执行一键AI审核吗？',
      '一键AI审核',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch (error) {
    return
  }

  loading.value = true
  try {
    const res = await aiReviewTestCases({
      username: author.value,
      month: selectedMonth.value || undefined
    })
    ElMessage.success(`AI审核完成：通过 ${res.data.approved_count || 0} 条，拒绝 ${res.data.rejected_count || 0} 条`)
    await loadData(true)
  } catch (error) {
    console.error('AI审核失败:', error)
    ElMessage.error('AI审核失败')
  } finally {
    loading.value = false
  }
}

// 点击已拒绝徽章查看拒绝原因
function handleReviewBadgeClick(row) {
  if (row.review_status === 'rejected') {
    currentReason.value = row.review_comment || '暂无拒绝原因'
    reasonDialogVisible.value = true
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

// 打开批量预览抽屉
function openBatchPreviewDrawer(group) {
  const selectedIds = selectedCasesByDirectory.value[group.directory] || []
  if (selectedIds.length === 0) {
    ElMessage.warning('请先选择用例')
    return
  }

  // 获取选中的用例完整数据
  previewCases.value = group.cases.filter(testCase => selectedIds.includes(testCase.id))
  currentPreviewDirectory.value = group.directory
  batchPreviewDrawerVisible.value = true
}

// 打开全局批量预览抽屉
function openGlobalBatchPreviewDrawer() {
  const allCases = getAllSelectedCases.value
  if (allCases.length === 0) {
    ElMessage.warning('请先选择用例')
    return
  }

  // 获取所有选中的用例完整数据
  const allSelectedCases = []
  groupedCases.value.forEach(group => {
    const selectedIds = selectedCasesByDirectory.value[group.directory] || []
    const cases = group.cases.filter(testCase => selectedIds.includes(testCase.id))
    allSelectedCases.push(...cases)
  })

  previewCases.value = allSelectedCases
  currentPreviewDirectory.value = 'all'
  batchPreviewDrawerVisible.value = true
}

// 处理预览中的单个用例审核
async function handlePreviewCaseReview(status, testCase) {
  let review_comment = ''
  if (status === 'rejected') {
    try {
      const { value } = await ElMessageBox.prompt('请输入拒绝理由', '拒绝用例', {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '拒绝理由不能为空'
          }
          return true
        }
      })
      review_comment = value.trim()
    } catch (error) {
      return
    }
  }

  try {
    await updateTestCase(testCase.id, { review_status: status, review_comment })
    testCase.review_status = status
    testCase.review_comment = review_comment
    ElMessage.success('审核状态已更新')

    // 同步更新主列表中的数据
    groupedCases.value.forEach(group => {
      const caseInGroup = group.cases.find(c => c.id === testCase.id)
      if (caseInGroup) {
        caseInGroup.review_status = status
        caseInGroup.review_comment = review_comment
      }
    })
  } catch (error) {
    console.error('更新审核状态失败:', error)
    ElMessage.error('更新审核状态失败')
  }
}

// 解析带序号的行，返回 { index: number, content: string }
function parseNumberedLines(text) {
  if (!text) return []
  const lines = text.split('\n').filter(s => s.trim())
  const result = []
  for (const line of lines) {
    const match = line.match(/^(\d+)\.\s*(.*)$/)
    if (match) {
      result.push({
        index: parseInt(match[1]),
        content: match[2].trim()
      })
    } else {
      result.push({
        index: result.length + 1,
        content: line.trim()
      })
    }
  }
  return result
}

// 解析测试步骤和预期结果为表格数据
function parseStepsAndResults(steps, expectedResult) {
  const stepList = parseNumberedLines(steps)
  const resultList = parseNumberedLines(expectedResult)

  // 找出最大的序号
  const maxStepIndex = stepList.length > 0 ? Math.max(...stepList.map(s => s.index)) : 0
  const maxResultIndex = resultList.length > 0 ? Math.max(...resultList.map(r => r.index)) : 0
  const maxIndex = Math.max(maxStepIndex, maxResultIndex)

  const result = []
  for (let i = 1; i <= maxIndex; i++) {
    const step = stepList.find(s => s.index === i)
    const res = resultList.find(r => r.index === i)
    result.push({
      step: step ? `${i}. ${step.content}` : '-',
      result: res ? `${i}. ${res.content}` : '-'
    })
  }

  return result
}

// 解析用例详情（前置条件、测试步骤、预期结果）为表格数据
function parseCaseDetail(precondition, steps, expectedResult) {
  const stepList = parseNumberedLines(steps)
  const resultList = parseNumberedLines(expectedResult)

  // 找出最大的序号
  const maxStepIndex = stepList.length > 0 ? Math.max(...stepList.map(s => s.index)) : 0
  const maxResultIndex = resultList.length > 0 ? Math.max(...resultList.map(r => r.index)) : 0
  const maxIndex = Math.max(maxStepIndex, maxResultIndex)

  const result = []
  for (let i = 1; i <= maxIndex; i++) {
    const step = stepList.find(s => s.index === i)
    const res = resultList.find(r => r.index === i)
    result.push({
      precondition: i === 1 ? (precondition || '') : '',
      step: step ? `${i}. ${step.content}` : '-',
      result: res ? `${i}. ${res.content}` : '-'
    })
  }

  return result
}

// 获取步骤数量用于计算前置条件跨行数
function getStepCount(steps, expectedResult) {
  const stepList = steps ? steps.split('\n').filter(s => s.trim()) : []
  const resultList = expectedResult ? expectedResult.split('\n').filter(r => r.trim()) : []
  return Math.max(stepList.length, resultList.length)
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

// 全局筛选栏 - 参考 XMindConverter 风格
.global-filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;

  .filter-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .filter-right {
    display: flex;
    align-items: center;
    gap: 2px;

    .action-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      font-size: 14px;
      font-weight: 500;
      border-radius: 6px;
      transition: all 0.2s ease;

      &:hover {
        transform: translateY(-1px);
      }

      .el-icon {
        font-size: 16px;
      }

      // 批量预览按钮 - 紫色主题
      &.preview-btn {
        background: #7c3aed;
        border-color: #7c3aed;
        color: #ffffff;

        &:hover {
          background: #6d28d9;
          border-color: #6d28d9;
        }

        &:active {
          background: #5b21b6;
          border-color: #5b21b6;
        }

        .el-icon {
          color: #ffffff;
        }

        span {
          color: #ffffff;
        }
      }
    }
  }
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
    margin-bottom: 12px;

    &.expanded {
      .directory-card {
        border-color: #7c3aed;
        background: #faf5ff;
      }
    }
  }

  // 目录卡片样式
  .directory-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 24px;
    background: #ffffff;
    border: 1px solid rgba(147, 112, 219, 0.12);
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(147, 112, 219, 0.06);
    cursor: pointer;
    transition: all 0.25s ease;
    position: relative;
    z-index: 1;

    &:hover {
      border-color: #a78bfa;
      box-shadow: 0 4px 16px rgba(147, 112, 219, 0.12);
      transform: translateY(-2px);
    }

    // 展开状态下底部圆角去掉，与列表连接
    .directory-group.expanded & {
      border-radius: 12px 12px 0 0;
      border-bottom-color: transparent;
    }

    .directory-card-content {
      display: flex;
      align-items: center;
      gap: 12px;

      .directory-icon {
        font-size: 48px;
        color: #a78bfa;
        background: rgba(167, 139, 250, 0.1);
        padding: 16px;
        border-radius: 14px;
        width: 80px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .directory-name {
        font-size: 16px;
        font-weight: 600;
        color: #4b5563;
        letter-spacing: 0.3px;
      }

      .directory-count {
        font-size: 13px;
        color: #9ca3af;
        font-weight: 400;
      }
    }

    .expand-arrow {
      font-size: 16px;
      color: #a78bfa;
      transition: transform 0.3s ease;

      &.is-expanded {
        transform: rotate(90deg);
      }
    }
  }

  // 目录头部行 - 简洁风格
  .directory-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 0;
    cursor: pointer;
    background: transparent;
    border-bottom: 1px solid rgba(147, 112, 219, 0.08);
    transition: all 0.2s ease;

    &:hover {
      border-bottom-color: rgba(147, 112, 219, 0.15);
    }

    .directory-header-left {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-shrink: 0;

      .expand-icon {
        font-size: 11px;
        color: #a78bfa;
        transition: all 0.2s ease;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        background: rgba(167, 139, 250, 0.08);

        &:hover {
          background: rgba(167, 139, 250, 0.15);
        }
      }

      .directory-name {
        font-size: 14px;
        font-weight: 600;
        color: #4b5563;
        flex-shrink: 0;
        letter-spacing: 0.3px;
      }
    }

    .directory-header-filter {
      display: flex;
      align-items: center;
      justify-content: center;
      flex: 1;

      :deep(.el-radio-group) {
        display: flex;
        gap: 4px;
        padding: 3px;
        background: #f3f4f6;
        border-radius: 6px;

        .el-radio-button {
          .el-radio-button__inner {
            padding: 5px 14px;
            font-size: 12px;
            border: none;
            background: transparent;
            color: #6b7280;
            border-radius: 4px;
            transition: all 0.2s ease;

            &:hover {
              color: #7c3aed;
              background: rgba(255, 255, 255, 0.5);
            }
          }

          &.is-active .el-radio-button__inner {
            background: #ffffff;
            color: #7c3aed;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            font-weight: 500;
          }
        }
      }
    }

    .directory-header-right {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      gap: 6px;

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

      .batch-btn {
        font-size: 11px;
        padding: 5px 12px;
        border: none;
        border-radius: 5px;
        font-weight: 500;
        transition: all 0.2s ease;

        &.approved {
          background: #d1fae5;
          color: #059669;

          &:hover {
            background: #a7f3d0;
            transform: translateY(-1px);
          }
        }

        &.rejected {
          background: #fee2e2;
          color: #dc2626;

          &:hover {
            background: #fecaca;
            transform: translateY(-1px);
          }
        }

        &.pending {
          background: #fef3c7;
          color: #d97706;

          &:hover {
            background: #fde68a;
            transform: translateY(-1px);
          }
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
    padding: 16px 24px;
    background: #ffffff;
    border: 1px solid rgba(147, 112, 219, 0.12);
    border-top: none;
    border-radius: 12px;
    margin-top: -1px;
    position: relative;
    z-index: 0;
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

// 批量预览抽屉样式
.batch-preview-container {
  padding: 8px 4px;

  .preview-case-item {
    background: linear-gradient(145deg, #ffffff 0%, #fafbfc 100%);
    border-radius: 16px;
    border: 1px solid rgba(226, 232, 240, 0.8);
    margin-bottom: 20px;
    padding: 24px;
    box-shadow:
      0 1px 3px rgba(0, 0, 0, 0.02),
      0 4px 12px rgba(0, 0, 0, 0.04),
      0 0 0 1px rgba(0, 0, 0, 0.02);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      box-shadow:
        0 4px 6px rgba(0, 0, 0, 0.02),
        0 8px 24px rgba(0, 0, 0, 0.06),
        0 0 0 1px rgba(0, 0, 0, 0.02);
      transform: translateY(-2px);
    }

    &:last-child {
      margin-bottom: 0;
    }

    .preview-case-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
      gap: 16px;

      .preview-case-title {
        font-size: 17px;
        font-weight: 600;
        color: #1e293b;
        margin: 0;
        flex: 1;
        line-height: 1.5;
        letter-spacing: -0.01em;
      }

      .preview-case-actions {
        display: flex;
        gap: 10px;
        flex-shrink: 0;

        .el-button {
          border-radius: 10px;
          padding: 8px 16px;
          font-weight: 500;
          transition: all 0.2s ease;

          .el-icon {
            margin-right: 6px;
          }

          // 默认状态（未选中）
          &.el-button--default {
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            color: #64748b;

            &:hover {
              background: #e2e8f0;
              border-color: #cbd5e1;
              color: #475569;
            }
          }

          // 通过按钮（绿色）
          &.el-button--success {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            border: none;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
            color: #fff;

            &:hover {
              background: linear-gradient(135deg, #059669 0%, #047857 100%);
              box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
              transform: translateY(-1px);
            }
          }

          // 拒绝按钮（红色）
          &.el-button--danger {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            border: none;
            box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
            color: #fff;

            &:hover {
              background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
              box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
              transform: translateY(-1px);
            }
          }
        }
      }
    }

    .preview-case-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 20px;
      padding: 14px 16px;
      background: rgba(248, 250, 252, 0.8);
      border-radius: 12px;
      border: 1px solid rgba(226, 232, 240, 0.6);

      .meta-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        padding: 4px 0;

        .meta-label {
          color: #64748b;
          font-weight: 500;
        }

        .badge {
          font-weight: 600;
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 12px;
        }
      }
    }

    .preview-case-content {
      .content-section {
        margin-bottom: 20px;

        &:last-child {
          margin-bottom: 0;
        }

        h5 {
          font-size: 12px;
          font-weight: 600;
          color: #475569;
          margin: 0 0 10px 0;
          text-transform: uppercase;
          letter-spacing: 0.8px;
        }

        pre {
          background: #f8fafc;
          border-radius: 10px;
          padding: 14px 16px;
          margin: 0;
          font-size: 13px;
          line-height: 1.7;
          color: #334155;
          white-space: pre-wrap;
          word-wrap: break-word;
          font-family: inherit;
          border: 1px solid rgba(226, 232, 240, 0.6);
        }

        // 用例详情表格样式（前置条件、测试步骤、预期结果）
        &.case-detail-section {
          background: #ffffff;
          border-radius: 14px;
          border: 1px solid rgba(226, 232, 240, 0.8);
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);

          .case-detail-table {
            display: grid;
            grid-template-columns: 28% 1fr 1fr;

            .table-header {
              display: contents;

              .header-cell {
                padding: 14px 16px;
                font-size: 12px;
                font-weight: 600;
                color: #475569;
                background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border-bottom: 1px solid #e2e8f0;

                &:first-child {
                  border-radius: 0;
                }

                &:last-child {
                  border-radius: 0;
                }
              }
            }

            .table-body {
              display: contents;

              .table-row {
                display: contents;

                &:not(:last-child) .table-cell {
                  border-bottom: 1px solid #f1f5f9;
                }

                .table-cell {
                  padding: 14px 16px;
                  font-size: 13px;
                  line-height: 1.7;
                  color: #475569;

                  &.precondition-cell {
                    color: #64748b;
                    grid-row: span var(--row-span, 1);
                    display: flex;
                    align-items: flex-start;
                    background: rgba(248, 250, 252, 0.5);
                    border-right: 1px solid #f1f5f9;

                    pre {
                      margin: 0;
                      padding: 0;
                      background: transparent;
                      border: none;
                      font-family: inherit;
                      font-size: 13px;
                      line-height: 1.7;
                      color: #64748b;
                      white-space: pre-wrap;
                      word-wrap: break-word;
                    }
                  }

                  &.steps-cell {
                    border-right: 1px solid #f1f5f9;
                    color: #334155;
                  }

                  &.result-cell {
                    color: #334155;
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

// 批量预览按钮样式
.batch-btn {
  &.preview {
    background: #e0e7ff;
    color: #4f46e5;

    &:hover {
      background: #c7d2fe;
    }
  }
}

// 抽屉自定义样式
:deep(.batch-review-drawer) {
  .el-drawer__header {
    padding: 20px 24px;
    margin-bottom: 0;
    border-bottom: 1px solid rgba(226, 232, 240, 0.8);
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);

    .el-drawer__title {
      font-size: 18px;
      font-weight: 600;
      color: #1e293b;
      letter-spacing: -0.01em;
    }

    .el-drawer__close-btn {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      transition: all 0.2s ease;

      &:hover {
        background: rgba(0, 0, 0, 0.04);
        transform: rotate(90deg);
      }

      .el-icon {
        font-size: 18px;
        color: #64748b;
      }
    }
  }

  .el-drawer__body {
    padding: 24px;
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  }
}
// 一键AI审核按钮样式
.ai-review-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #6d28d9 100%);
  border: none;
  color: #ffffff;

  &:hover {
    background: linear-gradient(135deg, #6d28d9 0%, #5b21b6 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
  }

  .el-icon,
  span {
    color: #ffffff !important;
  }
}

// 已拒绝徽章可点击
.badge-review-rejected-clickable {
  cursor: pointer;
  text-decoration: underline;
  text-decoration-style: dashed;
  text-underline-offset: 3px;

  &:hover {
    opacity: 0.85;
  }
}

// 拒绝原因弹窗内容
.reason-content {
  pre {
    background: #f8fafc;
    border-radius: 10px;
    padding: 16px;
    margin: 0;
    font-size: 14px;
    line-height: 1.7;
    color: #334155;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: inherit;
    border: 1px solid rgba(226, 232, 240, 0.8);
    max-height: 400px;
    overflow-y: auto;
  }
}

::deep(.reason-dialog) {
  .el-dialog__header {
    padding: 20px 24px;
    margin-bottom: 0;
    border-bottom: 1px solid rgba(226, 232, 240, 0.8);
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);

    .el-dialog__title {
      font-size: 18px;
      font-weight: 600;
      color: #1e293b;
    }
  }

  .el-dialog__body {
    padding: 24px;
  }

  .el-dialog__footer {
    padding: 12px 24px 24px;
  }
}
</style>
