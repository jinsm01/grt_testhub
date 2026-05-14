<template>
  <div class="testcase-statistics-container">
    <!-- 数据概览 -->
    <div class="stats-section">
      <div class="section-header">
        <h3 class="section-title">
          <el-icon><Odometer /></el-icon>
          数据概览
        </h3>
      </div>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-value primary">{{ stats.total || 0 }}</div>
            <div class="stat-label">用例总数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-value success">{{ stats.status_stats?.active || 0 }}</div>
            <div class="stat-label">激活用例</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-value warning">{{ stats.status_stats?.draft || 0 }}</div>
            <div class="stat-label">草稿用例</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-value danger">{{ stats.priority_stats?.high || 0 }}</div>
            <div class="stat-label">高优先级</div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-row :gutter="20">
      <!-- 状态分布 -->
      <el-col :span="8">
        <div class="stats-section">
          <h3 class="section-title">
            <el-icon><PieChart /></el-icon>
            状态分布
          </h3>
          <el-card shadow="hover" class="chart-card">
            <div ref="statusChart" class="chart-container"></div>
          </el-card>
        </div>
      </el-col>
      
      <!-- 优先级分布 -->
      <el-col :span="8">
        <div class="stats-section">
          <h3 class="section-title">
            <el-icon><DataAnalysis /></el-icon>
            优先级分布
          </h3>
          <el-card shadow="hover" class="chart-card">
            <div ref="priorityChart" class="chart-container"></div>
          </el-card>
        </div>
      </el-col>
      
      <!-- 月度趋势 -->
      <el-col :span="8">
        <div class="stats-section">
          <h3 class="section-title">
            <el-icon><TrendCharts /></el-icon>
            近6月趋势
          </h3>
          <el-card shadow="hover" class="chart-card">
            <div ref="trendChart" class="chart-container"></div>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <!-- 项目统计 -->
    <div class="stats-section">
      <h3 class="section-title">
        <el-icon><Folder /></el-icon>
        项目用例分布
      </h3>
      <el-card shadow="hover" class="table-card">
        <el-table :data="stats.project_stats" style="width: 100%" v-loading="loading">
          <el-table-column prop="project_name" label="项目名称" min-width="150" />
          <el-table-column prop="total" label="总数" width="100" align="center" />
          <el-table-column prop="active" label="激活" width="100" align="center">
            <template #default="{ row }">
              <el-tag type="success" size="small">{{ row.active }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="draft" label="草稿" width="100" align="center">
            <template #default="{ row }">
              <el-tag type="info" size="small">{{ row.draft }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="deprecated" label="废弃" width="100" align="center">
            <template #default="{ row }">
              <el-tag type="danger" size="small">{{ row.deprecated }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="high_priority" label="高优先级" width="100" align="center">
            <template #default="{ row }">
              <span class="high-priority-count">{{ row.high_priority }}</span>
            </template>
          </el-table-column>
          <el-table-column label="占比" width="150" align="center">
            <template #default="{ row }">
              <el-progress 
                :percentage="stats.total ? Math.round(row.total / stats.total * 100) : 0" 
                :stroke-width="8"
                :color="progressColor"
              />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 作者排行 -->
    <div class="stats-section">
      <div class="section-header">
        <h3 class="section-title">
          <el-icon><User /></el-icon>
          用例合入统计
        </h3>
        <el-select v-model="selectedMonth" placeholder="全部时间" clearable size="default" class="month-filter">
          <el-option label="全部时间" value="" />
          <el-option 
            v-for="item in stats.monthly_stats" 
            :key="item.month" 
            :label="item.month" 
            :value="item.month" 
          />
        </el-select>
      </div>
      <el-card shadow="hover" class="table-card">
        <el-table :data="filteredAuthorStats" style="width: 100%" v-loading="loading">
          <el-table-column type="index" label="排名" width="60" align="center">
            <template #default="{ $index }">
              <div class="rank-badge" :class="{ 'top-3': $index < 3 }">
                {{ $index + 1 }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="username" label="作者" min-width="120" />
          <el-table-column label="是否全部审核通过" width="150" align="center">
            <template #default="{ row }">
              <span v-if="row.count === 0">-</span>
              <el-tag v-else-if="row.all_approved" type="success" size="small">是</el-tag>
              <el-tag v-else type="warning" size="small">否</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="P0" width="70" align="center" title="紧急">
            <template #default="{ row }">
              <span class="priority-critical">{{ row.critical || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="P1" width="70" align="center" title="高">
            <template #default="{ row }">
              <span class="priority-high">{{ row.high || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="P2" width="70" align="center" title="中">
            <template #default="{ row }">
              <span class="priority-medium">{{ row.medium || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="P3" width="70" align="center" title="低">
            <template #default="{ row }">
              <span class="priority-low">{{ row.low || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="count" label="用例数总计" width="100" align="center">
            <template #default="{ row }">
              <span class="case-count">{{ row.count }}</span>
            </template>
          </el-table-column>
          <el-table-column label="主线用例积分" width="110" align="center">
            <template #default="{ row }">
              <span class="score-value">{{ row.score || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" align="center" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="goToAuthorDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>


  </div>

</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Odometer, PieChart, DataAnalysis, TrendCharts, Folder, User, FolderOpened } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { getTestCaseStatistics } from '@/api/testcases'
import * as echarts from 'echarts'

const loading = ref(false)
const selectedMonth = ref('')
const router = useRouter()
const stats = ref({
  total: 0,
  status_stats: {},
  priority_stats: {},
  project_stats: [],
  author_stats: [],
  monthly_stats: []
})

// 根据月份筛选作者统计数据
const filteredAuthorStats = computed(() => {
  if (!selectedMonth.value) {
    // 全部时间：使用 author_stats 并按总数排序
    const allStats = stats.value.author_stats || []
    return allStats.map(item => ({
      username: item.username,
      count: item.count,
      critical: item.critical || 0,
      high: item.high || 0,
      medium: item.medium || 0,
      low: item.low || 0,
      score: item.score ?? (Math.floor((item.critical + item.high) / 5) + Math.floor((item.medium + item.low) / 10)),
      all_approved: item.all_approved || false
    })).sort((a, b) => b.count - a.count)
  }
  
  const monthData = stats.value.monthly_stats?.find(m => m.month === selectedMonth.value)
  if (!monthData || !monthData.author_detail_counts) {
    return []
  }
  
  const authorDetailCounts = monthData.author_detail_counts
  // 转换为排序后的数组，包含优先级细分和积分
  return Object.entries(authorDetailCounts)
    .map(([username, detail]) => ({
      username,
      count: detail.total,
      critical: detail.critical,
      high: detail.high,
      medium: detail.medium,
      low: detail.low,
      score: detail.score || 0,
      all_approved: detail.all_approved || false
    }))
    .sort((a, b) => b.count - a.count)
})

// 筛选后的总数
const filteredTotal = computed(() => {
  if (!selectedMonth.value) {
    return stats.value.total
  }
  return filteredAuthorStats.value.reduce((sum, item) => sum + item.count, 0)
})

const statusChart = ref(null)
const priorityChart = ref(null)
const trendChart = ref(null)

let statusChartInstance = null
let priorityChartInstance = null
let trendChartInstance = null

const progressColor = [
  { color: '#7b42f6', percentage: 20 },
  { color: '#8b5cf6', percentage: 40 },
  { color: '#a78bfa', percentage: 60 },
  { color: '#c4b5fd', percentage: 80 },
  { color: '#ddd6fe', percentage: 100 }
]

// 加载统计数据
async function loadStatistics() {
  loading.value = true
  try {
    const res = await getTestCaseStatistics()
    stats.value = res.data
    nextTick(() => {
      initCharts()
    })
  } catch (error) {
    console.error('加载统计失败:', error)
    ElMessage.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

// 跳转到作者用例详情页
function goToAuthorDetail(row) {
  const query = {}
  if (selectedMonth.value) {
    query.month = selectedMonth.value
  }
  router.push({
    name: 'AuthorTestCaseDetail',
    params: { author: row.username },
    query
  })
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

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return '-'
  return dateStr
}

// 跳转用例详情
function goToDetail(row) {
  // 如果有目录信息，跳转到目录页面并定位
  if (row.menu_id) {
    router.push({ 
      name: 'TestCases', 
      query: { menu: row.menu_id } 
    })
  } else {
    // 否则跳转到用例详情页
    router.push({ name: 'TestCaseDetail', params: { id: row.id } })
  }
}

// 初始化图表
function initCharts() {
  initStatusChart()
  initPriorityChart()
  initTrendChart()
}

// 状态分布饼图
function initStatusChart() {
  if (!statusChart.value) return
  if (statusChartInstance) statusChartInstance.dispose()
  
  statusChartInstance = echarts.init(statusChart.value)
  const data = [
    { value: stats.value.status_stats?.active || 0, name: '激活' },
    { value: stats.value.status_stats?.draft || 0, name: '草稿' },
    { value: stats.value.status_stats?.deprecated || 0, name: '废弃' }
  ].filter(item => item.value > 0)

  statusChartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 5, textStyle: { color: '#6b7280' }, itemGap: 15 },
    series: [{
      type: 'pie',
      radius: ['35%', '60%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}: {c}', position: 'outside' },
      labelLine: { show: true, length: 10, length2: 5 },
      data,
      color: ['#22c55e', '#f59e0b', '#ef4444']
    }]
  })
}

// 优先级分布饼图
function initPriorityChart() {
  if (!priorityChart.value) return
  if (priorityChartInstance) priorityChartInstance.dispose()
  
  priorityChartInstance = echarts.init(priorityChart.value)
  const data = [
    { value: stats.value.priority_stats?.critical || 0, name: 'P0' },
    { value: stats.value.priority_stats?.high || 0, name: 'P1' },
    { value: stats.value.priority_stats?.medium || 0, name: 'P2' },
    { value: stats.value.priority_stats?.low || 0, name: 'P3' }
  ].filter(item => item.value > 0)

  priorityChartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 5, textStyle: { color: '#6b7280' }, itemGap: 15 },
    series: [{
      type: 'pie',
      radius: ['35%', '60%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}: {c}', position: 'outside' },
      labelLine: { show: true, length: 10, length2: 5 },
      data,
      color: ['#dc2626', '#f97316', '#eab308', '#22c55e']
    }]
  })
}

// 月度趋势图
function initTrendChart() {
  if (!trendChart.value) return
  if (trendChartInstance) trendChartInstance.dispose()
  
  trendChartInstance = echarts.init(trendChart.value)
  const months = stats.value.monthly_stats.map(item => item.month)
  const counts = stats.value.monthly_stats.map(item => item.count)
  const actives = stats.value.monthly_stats.map(item => item.active)

  trendChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, data: ['新增用例', '激活用例'], textStyle: { color: '#6b7280' } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: months, axisLabel: { color: '#6b7280' } },
    yAxis: { type: 'value', axisLabel: { color: '#6b7280' } },
    series: [
      { name: '新增用例', type: 'bar', data: counts, itemStyle: { color: '#7b42f6', borderRadius: [4, 4, 0, 0] } },
      { name: '激活用例', type: 'bar', data: actives, itemStyle: { color: '#22c55e', borderRadius: [4, 4, 0, 0] } }
    ]
  })
}

onMounted(() => {
  loadStatistics()
  window.addEventListener('resize', () => {
    statusChartInstance?.resize()
    priorityChartInstance?.resize()
    trendChartInstance?.resize()
  })
})
</script>

<style lang="scss" scoped>
.testcase-statistics-container {
  padding: 20px 24px 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
}

.stats-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  .month-filter {
    width: 140px;
  }
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #6d28d9;
  margin: 0 0 14px 0;
  display: flex;
  align-items: center;
  gap: 8px;

  .el-icon {
    color: #7c3aed;
    font-size: 18px;
  }
}

.stat-card {
  text-align: center;
  padding: 20px 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.1);
  transition: all 0.3s ease;
  min-height: 100px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(147, 112, 219, 0.15);
  }
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 6px;

  &.primary { color: #6d28d9; }
  &.success { color: #16a34a; }
  &.warning { color: #f59e0b; }
  &.danger { color: #ef4444; }
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.chart-card {
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border: 1px solid rgba(147, 112, 219, 0.08);

  :deep(.el-card__body) {
    padding: 16px;
  }
}

.chart-container {
  height: 280px;
  width: 100%;
}

.table-card {
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border: 1px solid rgba(147, 112, 219, 0.08);
}

.high-priority-count {
  color: #dc2626;
  font-weight: 600;
}

.case-count {
  color: #6d28d9;
  font-weight: 600;
  font-size: 15px;
}

.priority-critical {
  color: #dc2626;
  font-weight: 600;
}

.priority-high {
  color: #f97316;
  font-weight: 600;
}

.priority-medium {
  color: #eab308;
  font-weight: 500;
}

.priority-low {
  color: #22c55e;
  font-weight: 500;
}

.score-value {
  color: #7c3aed;
  font-weight: 700;
  font-size: 16px;
}

.no-rejected {
  color: #c0c4cc;
}

.rank-badge {
  width: 28px;
  height: 28px;
  line-height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  color: #6b7280;
  font-weight: 600;
  font-size: 13px;
  display: inline-block;

  &.top-3 {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    color: #d97706;
  }
}

:deep(.el-table) {
  border-radius: 8px;
  background: transparent;

  th.el-table__cell {
    background: #f8f7ff;
    color: #6d28d9;
    font-weight: 600;
    border-bottom: 1px solid #e8e0ff;
  }

  td.el-table__cell {
    border-bottom: 1px solid #f0edff;
    color: #374151;
  }

  tr:hover > td {
    background: #f0edff !important;
  }
}

.detail-filters {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 16px;

  .month-select {
    width: 140px;
  }
}

.expand-content {
  padding: 8px 16px 8px 50px;
  background: #fafafa;

  :deep(.el-table) {
    background: #fff;
    border-radius: 8px;

    th.el-table__cell {
      background: #f0edff;
      color: #6d28d9;
      font-weight: 600;
      font-size: 12px;
      padding: 8px 0;
    }

    td.el-table__cell {
      padding: 6px 0;
      font-size: 13px;
    }
  }
}

.directory-cell {
  display: flex;
  align-items: center;
  gap: 8px;

  .directory-icon {
    color: #7c3aed;
    display: flex;
    align-items: center;
  }

  .directory-name {
    font-weight: 500;
    color: #374151;
  }
}

.case-title-link {
  color: #6d28d9;
  cursor: pointer;
  transition: color 0.2s;

  &:hover {
    color: #7c3aed;
    text-decoration: underline;
  }
}

.detail-summary {
  margin-top: 16px;
  text-align: right;
  color: #6b7280;
  font-size: 14px;
}

::deep(.el-dialog__header) {
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  border-bottom: 1px solid #e8e0ff;
  margin-right: 0;
  padding: 16px 20px;

  .el-dialog__title {
    color: #6d28d9;
    font-weight: 600;
  }
}
</style>
