<template>
  <div class="test-report">
    <!-- Filter bar -->
    <div class="filter-bar">
      <div class="left-filters">
        <el-select v-model="filters.project" :placeholder="$t('report.selectProject')" clearable @change="handleFilterChange" style="width: 200px">
          <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
        </el-select>
        <el-select v-model="filters.days" :placeholder="$t('report.timeRange')" @change="handleFilterChange" style="width: 150px">
          <el-option :label="$t('report.recentDays')" :value="7"></el-option>
          <el-option :label="$t('report.recent14Days')" :value="14"></el-option>
          <el-option :label="$t('report.recent30Days')" :value="30"></el-option>
        </el-select>
      </div>
      <div class="right-actions">
        <el-button type="primary" @click="exportReport">
          <el-icon><Download /></el-icon>
          {{ $t('report.exportReport') }}
        </el-button>
      </div>
    </div>

    <!-- Dashboard cards -->
    <div class="dashboard-cards">
      <div class="card total-plans">
        <div class="card-icon">
          <el-icon><Collection /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.active_plans || 0 }}</div>
          <div class="card-label">{{ $t('report.activePlans') }}</div>
        </div>
        <div class="card-extra">
          <el-progress type="circle" :percentage="dashboardData.plan_progress || 0" :width="40" :stroke-width="4" :show-text="false" />
          <span class="progress-text">{{ dashboardData.plan_progress || 0 }}% {{ $t('report.progress') }}</span>
        </div>
      </div>
      <div class="card total-cases">
        <div class="card-icon">
          <el-icon><Document /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.total_cases || 0 }}</div>
          <div class="card-label">{{ $t('report.totalCases') }}</div>
        </div>
      </div>
      <div class="card pass-rate">
        <div class="card-icon">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.pass_rate || 0 }}%</div>
          <div class="card-label">{{ $t('report.passRate') }}</div>
        </div>
      </div>
      <div class="card defects">
        <div class="card-icon">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.total_defects || 0 }}</div>
          <div class="card-label">{{ $t('report.defectsFound') }}</div>
        </div>
      </div>
    </div>

    <!-- Charts area -->
    <div class="charts-container">
      <!-- First row: Execution status and trends -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-header">
            <h3>{{ $t('report.executionStatusDistribution') }}</h3>
          </div>
          <div class="chart-body" ref="statusChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <h3>{{ $t('report.dailyExecutionTrend') }}</h3>
          </div>
          <div class="chart-body" ref="trendChartRef"></div>
        </div>
      </div>

      <!-- Second row: Defect analysis -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-header">
            <h3>{{ $t('report.failureDistribution') }}</h3>
          </div>
          <div class="chart-body" ref="defectChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <h3>{{ $t('report.failureTop10') }}</h3>
          </div>
          <div class="chart-body table-body">
            <el-table :data="failedCasesTop" style="width: 100%" size="small">
              <el-table-column prop="testcase__title" :label="$t('report.caseTitle')" show-overflow-tooltip />
              <el-table-column prop="fail_count" :label="$t('report.failureCount')" width="100" align="center">
                <template #default="scope">
                  <el-tag type="danger">{{ scope.row.fail_count }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <!-- Third row: AI efficiency -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-header">
            <h3>{{ $t('report.aiEffectivenessAnalysis') }}</h3>
          </div>
          <div class="ai-metrics-container">
            <div class="ai-metric-item">
              <div class="metric-value">{{ aiData.adoption_rate || 0 }}%</div>
              <div class="metric-label">{{ $t('report.adoptionRate') }}</div>
              <el-progress :percentage="aiData.adoption_rate || 0" :show-text="false" status="success" />
            </div>
            <div class="ai-metric-item">
              <div class="metric-value">{{ aiData.requirement_coverage || 0 }}%</div>
              <div class="metric-label">{{ $t('report.requirementCoverage') }}</div>
              <el-progress :percentage="aiData.requirement_coverage || 0" :show-text="false" />
            </div>
            <div class="ai-metric-item">
              <div class="metric-value">{{ aiData.saved_hours || 0 }}h</div>
              <div class="metric-label">{{ $t('report.savedHours') }}</div>
            </div>
          </div>
          <div class="chart-body-small" ref="aiEfficiencyChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <h3>{{ $t('report.teamWorkload') }}</h3>
          </div>
          <div class="chart-body" ref="workloadChartRef"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Collection, Document, CircleCheck, Warning, Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import api from '@/utils/api'

const { t } = useI18n()

// 状态
const projects = ref([])
const filters = reactive({
  project: null,
  days: 7
})
const dashboardData = ref({})
const failedCasesTop = ref([])
const aiData = ref({})

// 图表实例
let statusChart = null
let trendChart = null
let defectChart = null
let aiEfficiencyChart = null
let workloadChart = null

// DOM引用
const statusChartRef = ref(null)
const trendChartRef = ref(null)
const defectChartRef = ref(null)
const aiEfficiencyChartRef = ref(null)
const workloadChartRef = ref(null)

// Fetch projects
const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || []
  } catch (error) {
    console.error(t('report.fetchProjectsFailed'), error)
  }
}

// Fetch dashboard data
const fetchDashboardData = async () => {
  try {
    const params = { project: filters.project }
    const response = await api.get('/reports/reports/dashboard/', { params })
    dashboardData.value = response.data
  } catch (error) {
    console.error(t('report.fetchDashboardFailed'), error)
  }
}

// 初始化图表
const initCharts = () => {
  if (statusChartRef.value) statusChart = echarts.init(statusChartRef.value)
  if (trendChartRef.value) trendChart = echarts.init(trendChartRef.value)
  if (defectChartRef.value) defectChart = echarts.init(defectChartRef.value)
  if (aiEfficiencyChartRef.value) aiEfficiencyChart = echarts.init(aiEfficiencyChartRef.value)
  if (workloadChartRef.value) workloadChart = echarts.init(workloadChartRef.value)
  
  window.addEventListener('resize', handleResize)
}

const handleResize = () => {
  statusChart?.resize()
  trendChart?.resize()
  defectChart?.resize()
  aiEfficiencyChart?.resize()
  workloadChart?.resize()
}

// 加载图表数据
const loadChartsData = async () => {
  const params = { 
    project: filters.project,
    days: filters.days
  }

  // 1. Status distribution
  try {
    const res = await api.get('/reports/reports/status_distribution/', { params })
    const data = [
      { value: res.data.passed, name: t('report.passed'), itemStyle: { color: '#67C23A' } },
      { value: res.data.failed, name: t('report.failed'), itemStyle: { color: '#F56C6C' } },
      { value: res.data.blocked, name: t('report.blocked'), itemStyle: { color: '#E6A23C' } },
      { value: res.data.retest, name: t('report.retest'), itemStyle: { color: '#409EFF' } },
      { value: res.data.untested, name: t('report.untested'), itemStyle: { color: '#909399' } }
    ]

    statusChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%', left: 'center' },
      series: [{
        name: t('report.executionStatus'),
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: data
      }]
    })
  } catch (e) { console.error(e) }

  // 2. Execution trend
  try {
    const res = await api.get('/reports/reports/execution_trend/', { params })
    const dates = res.data.map(item => item.date)
    const counts = res.data.map(item => item.count)

    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: dates },
      yAxis: { type: 'value' },
      series: [{
        name: t('report.executionCount'),
        type: 'line',
        stack: 'Total',
        smooth: true,
        areaStyle: { opacity: 0.3, color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#409EFF' }, { offset: 1, color: '#fff' }]) },
        itemStyle: { color: '#409EFF' },
        data: counts
      }]
    })
  } catch (e) { console.error(e) }

  // 3. Defect distribution
  try {
    const res = await api.get('/reports/reports/defect_distribution/', { params })
    defectChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%', left: 'center' },
      series: [{
        name: t('report.priorityDistribution'),
        type: 'pie',
        radius: '60%',
        center: ['50%', '45%'],
        data: res.data,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    })
  } catch (e) { console.error(e) }

  // 4. 失败用例TOP榜
  try {
    const res = await api.get('/reports/reports/failed_cases_top/', { params })
    failedCasesTop.value = res.data
  } catch (e) { console.error(e) }

  // 5. AI efficiency
  try {
    const res = await api.get('/reports/reports/ai_efficiency/', { params })
    aiData.value = res.data
    const aiCounts = res.data.ai_vs_manual

    aiEfficiencyChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: [t('report.caseSource')] },
      series: [
        { name: t('report.aiGenerated'), type: 'bar', stack: 'total', label: { show: true }, itemStyle: { color: '#8e44ad' }, data: [aiCounts.ai] },
        { name: t('report.manualCreated'), type: 'bar', stack: 'total', label: { show: true }, itemStyle: { color: '#3498db' }, data: [aiCounts.manual] }
      ]
    })
  } catch (e) { console.error(e) }

  // 6. Team workload
  try {
    const res = await api.get('/reports/reports/team_workload/', { params })
    const users = res.data.map(item => item.username)
    const execCounts = res.data.map(item => item.execution_count)
    const defectCounts = res.data.map(item => item.defect_count)

    workloadChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: [t('report.executedCases'), t('report.defectsFound')], bottom: '0%' },
      grid: { left: '3%', right: '4%', bottom: '10%', top: '5%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: users },
      series: [
        {
          name: t('report.executedCases'),
          type: 'bar',
          stack: 'total',
          label: { show: true },
          itemStyle: { color: '#409EFF' },
          data: execCounts
        },
        {
          name: t('report.defectsFound'),
          type: 'bar',
          stack: 'total',
          label: { show: true },
          itemStyle: { color: '#F56C6C' },
          data: defectCounts
        }
      ]
    })
  } catch (e) { console.error(e) }
}

const handleFilterChange = () => {
  fetchDashboardData()
  loadChartsData()
}

const exportReport = () => {
  ElMessage.success(t('report.exportInDevelopment'))
}

onMounted(async () => {
  await fetchProjects()
  await nextTick()
  initCharts()
  handleFilterChange()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  statusChart?.dispose()
  trendChart?.dispose()
  defectChart?.dispose()
  aiEfficiencyChart?.dispose()
  workloadChart?.dispose()
})
</script>

<style lang="scss" scoped>
.test-report {
  padding: 20px;
  min-height: 100vh;
  height: 100vh;
  background: linear-gradient(135deg, #f9f7ff 0%, #f3f0fa 100%);
  display: flex;
  flex-direction: column;
}

// 筛选栏样式 - 参考 ProjectList.vue
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  border: 1px solid rgba(147, 112, 219, 0.1);
}

.left-filters {
  display: flex;
  gap: 16px;
  align-items: center;

  // 下拉选择器样式优化
  .el-select {
    width: 200px;

    :deep(.el-input__wrapper) {
      box-shadow: 0 2px 8px rgba(147, 112, 219, 0.08);
      border-radius: 8px;
      background: #ffffff;
      border: 1px solid rgba(147, 112, 219, 0.2);
      transition: all 0.3s ease;

      &:hover {
        box-shadow: 0 2px 8px rgba(147, 112, 219, 0.15);
        border-color: #9370db;
      }

      &.is-focus {
        box-shadow: 0 0 0 2px rgba(147, 112, 219, 0.2);
        border-color: #5a32a3;
      }
    }

    :deep(.el-input__inner) {
      color: #5a32a3;
      font-weight: 500;

      &::placeholder {
        color: rgba(90, 50, 163, 0.5);
      }
    }

    :deep(.el-input__suffix) {
      color: #9370db;
    }
  }
}

/* 全局下拉菜单样式覆盖 - 修复选中项蓝色问题 */
/* 使用 :global 因为下拉菜单渲染在 body 上，不在组件内 */
:global(.el-select-dropdown__item) {
  &.selected {
    color: #5a32a3 !important;
    background-color: rgba(90, 50, 163, 0.1) !important;
    font-weight: 600;

    &:hover {
      color: #5a32a3 !important;
      background-color: rgba(90, 50, 163, 0.15) !important;
    }
  }

  &:hover {
    background-color: rgba(90, 50, 163, 0.08) !important;
    color: #5a32a3 !important;
  }
}

/* 覆盖 Element Plus 下拉菜单选中项的蓝色背景 */
:global(.el-select-dropdown__item.is-selected) {
  color: #5a32a3 !important;
  background-color: rgba(90, 50, 163, 0.1) !important;

  &:hover {
    color: #5a32a3 !important;
    background-color: rgba(90, 50, 163, 0.15) !important;
  }
}

/* 覆盖下拉菜单悬停和选中状态 */
:global(.el-select-dropdown__item.hover),
:global(.el-select-dropdown__item:hover) {
  background-color: rgba(90, 50, 163, 0.08) !important;
  color: #5a32a3 !important;
}

/* 覆盖 el-select-dropdown 的选中高亮样式 */
:global(.el-select-dropdown__item.is-selected) {
  color: #5a32a3 !important;
  background-color: rgba(90, 50, 163, 0.1) !important;
}

/* 覆盖 el-select-dropdown 的 hover 样式 */
:global(.el-select-dropdown__item:hover) {
  background-color: rgba(90, 50, 163, 0.08) !important;
  color: #5a32a3 !important;
}

/* 按钮样式 */
.el-button {
  transition: all 0.3s ease;
  font-weight: 500;
  border-radius: 8px;
  
  &.el-button--primary {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    border: none;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
      background: linear-gradient(135deg, #8a55f7 0%, #6b41b3 100%);
      color: #ffffff !important;
    }
    
    &:focus {
      box-shadow: 0 0 0 4px rgba(123, 66, 246, 0.2);
    }
  }
}

.dashboard-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 24px;
}

.card {
  background: linear-gradient(135deg, #ffffff 0%, #f3f0fa 100%);
  border-radius: 20px;
  padding: 24px;
  display: flex;
  align-items: center;
  box-shadow: 0 4px 16px rgba(90, 50, 163, 0.12);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(90, 50, 163, 0.15);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #7b42f6, #5a32a3);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(90, 50, 163, 0.18);
  border-color: rgba(90, 50, 163, 0.3);
}

.card:hover::before {
  transform: scaleX(1);
}

.card-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  font-size: 32px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(90, 50, 163, 0.15);
}

.card:hover .card-icon {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(90, 50, 163, 0.2);
}

.total-plans .card-icon { 
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%); 
  color: #ffffff; 
}
.total-cases .card-icon { 
  background: linear-gradient(135deg, #9370db 0%, #6a4b8e 100%); 
  color: #ffffff; 
}
.pass-rate .card-icon { 
  background: linear-gradient(135deg, #a888e0 0%, #7b5fb8 100%); 
  color: #ffffff; 
}
.defects .card-icon { 
  background: linear-gradient(135deg, #c2a9f3 0%, #9370db 100%); 
  color: #ffffff; 
}

.card-content {
  flex: 1;
}

.card-value {
  font-size: 32px;
  font-weight: 700;
  color: #4a249c;
  line-height: 1.1;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.card-label {
  font-size: 16px;
  color: #6d5d8f;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.card-extra {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 14px;
  color: #6d5d8f;
  font-weight: 500;
}

.progress-text {
  margin-top: 8px;
  font-weight: 500;
}

/* 进度条样式 */
.el-progress {
  --el-progress-color: #5a32a3;
  --el-progress-bg-color: rgba(90, 50, 163, 0.1);
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  flex-grow: 1;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.chart-card {
  background: linear-gradient(135deg, #ffffff 0%, #f3f0fa 100%);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 4px 16px rgba(90, 50, 163, 0.12);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(90, 50, 163, 0.15);
  display: flex;
  flex-direction: column;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.chart-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #7b42f6, #5a32a3);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.chart-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(90, 50, 163, 0.18);
  border-color: rgba(90, 50, 163, 0.3);
}

.chart-card:hover::before {
  transform: scaleX(1);
}

.chart-header {
  margin-bottom: 24px;
  border-bottom: 1px solid rgba(90, 50, 163, 0.15);
  padding-bottom: 12px;
}

.chart-header h3 {
  margin: 0;
  font-size: 18px;
  color: #4a249c;
  font-weight: 700;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-header h3::before {
  content: '';
  width: 4px;
  height: 16px;
  background: linear-gradient(135deg, #7b42f6, #5a32a3);
  border-radius: 2px;
}

.chart-body {
  height: 320px;
  width: 100%;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.chart-card:hover .chart-body {
  transform: scale(1.02);
}

.chart-body-small {
  height: 180px;
  width: 100%;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.chart-card:hover .chart-body-small {
  transform: scale(1.02);
}

.table-body {
  overflow-y: auto;
}

/* 表格样式 */
.el-table {
  background: transparent;
  border-radius: 8px;
  overflow: hidden;
  
  .el-table__header {
    background: linear-gradient(135deg, #f3f0fa 0%, #e8e3f5 100%);
    
    th {
      background: transparent !important;
      color: #5a32a3;
      font-weight: 600;
      border-bottom: 2px solid rgba(90, 50, 163, 0.2);
      padding: 16px 12px;
    }
  }
  
  .el-table__body-wrapper {
    .el-table__row {
      transition: all 0.3s ease;
      background: #f3f0fa !important;
      
      &:hover {
        background: rgba(90, 50, 163, 0.1) !important;
      }
      
      &.el-table__row--striped {
        background: rgba(243, 240, 250, 0.8) !important;
      }
      
      td {
        padding: 14px 12px;
        border-bottom: 1px solid rgba(90, 50, 163, 0.1);
      }
    }
  }
}

.ai-metrics-container {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;
}

.ai-metric-item {
  text-align: center;
  width: 30%;
}

.metric-value {
  font-size: 20px;
  font-weight: bold;
  color: #5a32a3;
  margin-bottom: 5px;
}

.metric-label {
  font-size: 12px;
  color: rgba(90, 50, 163, 0.7);
  margin-bottom: 5px;
}

/* 标签样式 */
.el-tag {
  border-radius: 16px;
  padding: 2px 12px;
  font-size: 12px;
  font-weight: 500;
  
  &.el-tag--danger {
    background: rgba(245, 108, 108, 0.1);
    border-color: rgba(245, 108, 108, 0.2);
    color: #F56C6C;
  }
}
</style>
