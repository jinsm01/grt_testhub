<template>
  <div class="author-testcase-detail-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button @click="goBack" :icon="ArrowLeft">返回</el-button>
        <h2 class="page-title">{{ author }} 的用例</h2>
      </div>
      <div class="header-filters">
        <el-select v-model="selectedMonth" placeholder="全部时间" clearable size="default" class="month-select">
          <el-option label="全部时间" value="" />
          <el-option 
            v-for="item in monthlyStats" 
            :key="item.month" 
            :label="item.month" 
            :value="item.month" 
          />
        </el-select>
        <el-radio-group v-model="selectedPriority" size="default">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="critical">P0</el-radio-button>
          <el-radio-button label="high">P1</el-radio-button>
          <el-radio-button label="medium">P2</el-radio-button>
          <el-radio-button label="low">P3</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="12" class="summary-cards">
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value primary">{{ totalCases }}</div>
          <div class="stat-label">用例总数</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ directoryCount }}</div>
          <div class="stat-label">涉及目录</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value success">{{ reviewStats.approved || 0 }}</div>
          <div class="stat-label">已通过</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value danger">{{ reviewStats.rejected || 0 }}</div>
          <div class="stat-label">已拒绝</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value warning">{{ reviewStats.pending || 0 }}</div>
          <div class="stat-label">待审核</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 用例列表 -->
    <el-card shadow="hover" class="table-card">
      <el-table
        :data="groupedCases"
        style="width: 100%"
        v-loading="loading"
        row-key="directory"
        default-expand-all
      >
        <el-table-column type="expand" width="50">
          <template #default="{ row }">
            <div class="expand-content">
              <el-table
                :data="row.cases"
                style="width: 100%"
                :show-header="true"
                size="small"
                @selection-change="(sel) => handleGroupSelectionChange(row.directory, sel)"
                ref="(el) => setGroupTableRef(el, row.directory)"
              >
                <el-table-column type="selection" width="45" align="center" />
                <el-table-column prop="title" label="用例标题" min-width="250">
                  <template #default="{ row: caseRow }">
                    <span class="case-title-link" @click="goToDetail(caseRow)">
                      {{ caseRow.title }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="priority" label="优先级" width="100" align="center">
                  <template #default="{ row: caseRow }">
                    <el-tag :type="getPriorityType(caseRow.priority)" size="small">
                      {{ getPriorityLabel(caseRow.priority) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="100" align="center">
                  <template #default="{ row: caseRow }">
                    <el-tag :type="getStatusType(caseRow.status)" size="small">
                      {{ getStatusLabel(caseRow.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="review_status" label="审核结果" width="100" align="center">
                  <template #default="{ row: caseRow }">
                    <el-dropdown trigger="click" @command="(cmd) => handleReviewStatusChange(cmd, caseRow)">
                      <span class="review-status-badge" :class="`status-${caseRow.review_status || 'pending'}`">
                        <span class="status-dot"></span>
                        {{ getReviewStatusLabel(caseRow.review_status) }}
                        <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                      </span>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="pending">
                            <span class="dropdown-status pending">待审核</span>
                          </el-dropdown-item>
                          <el-dropdown-item command="approved">
                            <span class="dropdown-status approved">已通过</span>
                          </el-dropdown-item>
                          <el-dropdown-item command="rejected">
                            <span class="dropdown-status rejected">已拒绝</span>
                          </el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" label="创建时间" width="160" align="center" />
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="directory" min-width="200">
          <template #header>
            <div class="directory-header">
              <span>归属目录</span>
              <el-dropdown :disabled="selectedCaseIds.length === 0" @command="handleBatchReview">
                <el-button type="primary" size="small" :disabled="selectedCaseIds.length === 0">
                  批量审核 ({{ selectedCaseIds.length }})
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
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
          </template>
          <template #default="{ row }">
            <div class="directory-cell">
              <span class="directory-icon">
                <el-icon><Folder /></el-icon>
              </span>
              <span class="directory-name">{{ row.directory }}</span>
              <el-tag size="small" type="info">{{ row.count }}</el-tag>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-summary">
        共 {{ groupedCases.length }} 个目录，{{ totalCases }} 条用例
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Folder, ArrowDown } from '@element-plus/icons-vue'
import { getAuthorTestCases, getTestCaseStatistics, updateTestCase, batchUpdateReviewStatus } from '@/api/testcases'

const route = useRoute()
const router = useRouter()

// 数据
const loading = ref(false)
const author = ref('')
const groupedCases = ref([])
const totalCases = ref(0)
const selectedMonth = ref('')
const selectedPriority = ref('')
const monthlyStats = ref([])
const priorityStats = ref({})
const reviewStats = ref({})
const selectedCaseIds = ref([])
const groupTableRefs = ref({})

// 计算目录数量
const directoryCount = computed(() => groupedCases.value.length)

// 初始化
onMounted(async () => {
  author.value = route.params.author || route.query.author || ''
  selectedMonth.value = route.query.month || ''
  
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

// 监听筛选条件变化
watch([selectedMonth, selectedPriority], () => {
  loadData()
})

// 设置分组表格 ref
function setGroupTableRef(el, directory) {
  if (el) {
    groupTableRefs.value[directory] = el
  }
}

// 处理分组内选择变化
function handleGroupSelectionChange(directory, selection) {
  const selectedIds = selection.map(item => item.id)
  const otherIds = selectedCaseIds.value.filter(id => {
    const group = groupedCases.value.find(g => g.directory === directory)
    if (!group) return true
    return !group.cases.some(c => c.id === id)
  })
  selectedCaseIds.value = [...otherIds, ...selectedIds]
}

// 处理批量审核
async function handleBatchReview(command) {
  if (selectedCaseIds.value.length === 0) {
    ElMessage.warning('请先选择用例')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${selectedCaseIds.value.length} 条用例审核结果设为「${getReviewStatusLabel(command)}」吗？`,
      '批量审核确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await batchUpdateReviewStatus({
      ids: selectedCaseIds.value,
      review_status: command
    })

    ElMessage.success('批量审核成功')
    selectedCaseIds.value = []
    // 清除各分组的选中状态
    Object.values(groupTableRefs.value).forEach(table => {
      if (table && table.clearSelection) {
        table.clearSelection()
      }
    })
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

<style scoped>
.author-testcase-detail-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-filters {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.month-select {
  width: 160px;
}

.summary-cards {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-card :deep(.el-card__body) {
  padding: 20px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}

.stat-value.primary {
  color: #409eff;
}

.stat-value.success {
  color: #67c23a;
}

.stat-value.warning {
  color: #e6a23c;
}

.stat-value.danger {
  color: #f56c6c;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.table-card {
  margin-bottom: 20px;
}

.directory-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.directory-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.directory-icon {
  color: #909399;
  display: flex;
  align-items: center;
}

.directory-name {
  flex: 1;
}

.expand-content {
  padding: 10px 20px;
  background-color: #fafafa;
}

.case-title-link {
  color: #409eff;
  cursor: pointer;
}

.case-title-link:hover {
  text-decoration: underline;
}

.table-summary {
  margin-top: 16px;
  text-align: right;
  color: #909399;
  font-size: 14px;
}

.review-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  white-space: nowrap;
}

.review-status-badge:hover {
  opacity: 0.85;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.review-status-badge.status-pending {
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.1);
}

.review-status-badge.status-approved {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

.review-status-badge.status-rejected {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

.review-status-badge.status-none {
  color: #909399;
  background: rgba(144, 147, 153, 0.1);
}

.dropdown-status {
  font-weight: 500;
}

.dropdown-status.pending { color: #e6a23c; }
.dropdown-status.approved { color: #67c23a; }
.dropdown-status.rejected { color: #f56c6c; }
</style>
