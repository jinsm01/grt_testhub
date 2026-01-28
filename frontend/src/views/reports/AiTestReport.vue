<template>
  <div class="test-report">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="left-filters">
        <el-select v-model="filters.project" placeholder="选择项目" clearable @change="handleFilterChange" style="width: 200px">
          <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
        </el-select>
        <el-select v-model="filters.days" placeholder="时间范围" @change="handleFilterChange" style="width: 150px">
          <el-option label="最近7天" :value="7"></el-option>
          <el-option label="最近14天" :value="14"></el-option>
          <el-option label="最近30天" :value="30"></el-option>
        </el-select>
      </div>
      <div class="right-actions">
        <el-button type="primary" @click="exportReport">
          <el-icon><Download /></el-icon>
          导出报告
        </el-button>
      </div>
    </div>

    <!-- 概览卡片 -->
    <div class="dashboard-cards">
      <div class="card total-plans">
        <div class="card-icon">
          <el-icon><Collection /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.active_plans || 0 }}</div>
          <div class="card-label">活跃计划</div>
        </div>
        <div class="card-extra">
          <el-progress type="circle" :percentage="dashboardData.plan_progress || 0" :width="40" :stroke-width="4" :show-text="false" />
          <span class="progress-text">{{ dashboardData.plan_progress || 0 }}% 进度</span>
        </div>
      </div>
      <div class="card total-cases">
        <div class="card-icon">
          <el-icon><Document /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.total_cases || 0 }}</div>
          <div class="card-label">用例总数</div>
        </div>
      </div>
      <div class="card pass-rate">
        <div class="card-icon">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.pass_rate || 0 }}%</div>
          <div class="card-label">通过率</div>
        </div>
      </div>
      <div class="card defects">
        <div class="card-icon">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.total_defects || 0 }}</div>
          <div class="card-label">发现缺陷</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-container">
      <!-- 第一行：执行状态与趋势 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-header">
            <h3>执行状态分布</h3>
          </div>
          <div class="chart-body" ref="statusChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <h3>每日执行趋势</h3>
          </div>
          <div class="chart-body" ref="trendChartRef"></div>
        </div>
      </div>

      <!-- 第二行：缺陷分析 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-header">
            <h3>失败用例优先级分布 (缺陷分布)</h3>
          </div>
          <div class="chart-body" ref="defectChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <h3>失败用例 TOP 10</h3>
          </div>
          <div class="chart-body table-body">
            <el-table :data="failedCasesTop" style="width: 100%" size="small">
              <el-table-column prop="testcase__title" label="用例标题" show-overflow-tooltip />
              <el-table-column prop="fail_count" label="失败次数" width="100" align="center">
                <template #default="scope">
                  <el-tag type="danger">{{ scope.row.fail_count }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <!-- 第三行：AI效能 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-header">
            <h3>AI生成效能分析</h3>
          </div>
          <div class="ai-metrics-container">
            <div class="ai-metric-item">
              <div class="metric-value">{{ aiData.adoption_rate || 0 }}%</div>
              <div class="metric-label">生成采纳率</div>
              <el-progress :percentage="aiData.adoption_rate || 0" :show-text="false" status="success" />
            </div>
            <div class="ai-metric-item">
              <div class="metric-value">{{ aiData.requirement_coverage || 0 }}%</div>
              <div class="metric-label">需求覆盖率</div>
              <el-progress :percentage="aiData.requirement_coverage || 0" :show-text="false" />
            </div>
            <div class="ai-metric-item">
              <div class="metric-value">{{ aiData.saved_hours || 0 }}h</div>
              <div class="metric-label">节省工时估算</div>
            </div>
          </div>
          <div class="chart-body-small" ref="aiEfficiencyChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <h3>团队工作量统计</h3>
          </div>
          <div class="chart-body" ref="workloadChartRef"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Collection, Document, CircleCheck, Warning, Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import api from '@/utils/api'

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

// 获取基础数据
const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || []
  } catch (error) {
    console.error('获取项目失败', error)
  }
}

// 获取概览数据
const fetchDashboardData = async () => {
  try {
    const params = { project: filters.project }
    const response = await api.get('/reports/reports/dashboard/', { params })
    dashboardData.value = response.data
  } catch (error) {
    console.error('获取概览数据失败', error)
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

  // 1. 状态分布
  try {
    const res = await api.get('/reports/reports/status_distribution/', { params })
    const data = [
      { value: res.data.passed, name: '通过', itemStyle: { color: '#67C23A' } },
      { value: res.data.failed, name: '失败', itemStyle: { color: '#F56C6C' } },
      { value: res.data.blocked, name: '阻塞', itemStyle: { color: '#E6A23C' } },
      { value: res.data.retest, name: '重测', itemStyle: { color: '#409EFF' } },
      { value: res.data.untested, name: '未测', itemStyle: { color: '#909399' } }
    ]
    
    statusChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%', left: 'center' },
      series: [{
        name: '执行状态',
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

  // 2. 执行趋势
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
        name: '执行数量',
        type: 'line',
        stack: 'Total',
        smooth: true,
        areaStyle: { opacity: 0.3, color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#409EFF' }, { offset: 1, color: '#fff' }]) },
        itemStyle: { color: '#409EFF' },
        data: counts
      }]
    })
  } catch (e) { console.error(e) }

  // 3. 缺陷分布
  try {
    const res = await api.get('/reports/reports/defect_distribution/', { params })
    defectChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%', left: 'center' },
      series: [{
        name: '优先级分布',
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

  // 5. AI效能
  try {
    const res = await api.get('/reports/reports/ai_efficiency/', { params })
    aiData.value = res.data
    const aiCounts = res.data.ai_vs_manual
    
    aiEfficiencyChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: ['用例来源'] },
      series: [
        { name: 'AI生成', type: 'bar', stack: 'total', label: { show: true }, itemStyle: { color: '#8e44ad' }, data: [aiCounts.ai] },
        { name: '人工创建', type: 'bar', stack: 'total', label: { show: true }, itemStyle: { color: '#3498db' }, data: [aiCounts.manual] }
      ]
    })
  } catch (e) { console.error(e) }

  // 6. 团队工作量
  try {
    const res = await api.get('/reports/reports/team_workload/', { params })
    const users = res.data.map(item => item.username)
    const execCounts = res.data.map(item => item.execution_count)
    const defectCounts = res.data.map(item => item.defect_count)
    
    workloadChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['执行用例', '发现缺陷'], bottom: '0%' },
      grid: { left: '3%', right: '4%', bottom: '10%', top: '5%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: users },
      series: [
        {
          name: '执行用例',
          type: 'bar',
          stack: 'total',
          label: { show: true },
          itemStyle: { color: '#409EFF' },
          data: execCounts
        },
        {
          name: '发现缺陷',
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
  ElMessage.success('报告导出功能开发中...')
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

<style scoped>
.test-report {
  padding: 20px;
  min-height: 100vh;
  height: 100vh;
  background: linear-gradient(135deg, #f9f7ff 0%, #f3f0fa 100%);
  display: flex;
  flex-direction: column;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: #f3f0fa;
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(90, 50, 163, 0.08);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(90, 50, 163, 0.1);
  
  /* 覆盖 Element Plus 默认主题变量 */
  --el-color-primary: #7b42f6;
  --el-color-primary-light-3: #9370db;
  --el-color-primary-light-5: #a888e0;
  --el-color-primary-light-7: #c2a9f3;
  --el-color-primary-light-9: #f3f0fa;
  --el-border-color: rgba(90, 50, 163, 0.2);
  --el-border-color-light: rgba(90, 50, 163, 0.1);
  --el-border-color-lighter: rgba(90, 50, 163, 0.05);
  --el-fill-color-light: rgba(90, 50, 163, 0.05);
  --el-fill-color-lighter: rgba(90, 50, 163, 0.02);
  --el-fill-color-blank: #ffffff;
  --el-text-color-primary: #5a32a3;
  --el-text-color-regular: #5a32a3;
  --el-text-color-secondary: rgba(90, 50, 163, 0.7);
  --el-text-color-placeholder: rgba(90, 50, 163, 0.5);
}

.left-filters {
  display: flex;
  gap: 16px;
}

/* 选择器样式 */
.el-select {
  border-radius: 8px;
  border: 1px solid rgba(90, 50, 163, 0.2);
  transition: all 0.3s ease;
  
  &:hover {
    border-color: #9370db;
    box-shadow: 0 0 0 2px rgba(147, 112, 219, 0.1);
  }
  
  &.is-focus {
    border-color: #5a32a3;
    box-shadow: 0 0 0 2px rgba(90, 50, 163, 0.2);
  }
  
  .el-input__inner {
    color: #5a32a3;
    border: none;
    background: transparent;
    
    &::placeholder {
      color: rgba(90, 50, 163, 0.5);
    }
    
    &:focus {
      outline: none;
      box-shadow: none;
    }
  }
  
  .el-input.is-focus .el-input__inner {
    border: none;
    box-shadow: none;
  }
  
  .el-select.is-focus .el-input__wrapper {
    box-shadow: none;
    border-color: #5a32a3;
  }
  
  .el-select-dropdown {
    border: 1px solid rgba(90, 50, 163, 0.2);
    border-radius: 8px;
    background: #ffffff;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.15);
    
    .el-select-dropdown__item {
      color: #5a32a3;
      border-radius: 4px;
      margin: 4px;
      padding: 8px 12px;
      transition: all 0.3s ease;
      
      &:hover {
        background: rgba(90, 50, 163, 0.1);
        color: #5a32a3;
      }
      
      &.selected {
        background: rgba(90, 50, 163, 0.1);
        color: #5a32a3;
      }
      
      &.selected.hover,
      &.selected:hover {
        background: rgba(90, 50, 163, 0.1);
        color: #5a32a3;
      }
    }
    
    .el-select-dropdown__item.hover,
    .el-select-dropdown__item:hover {
      background: rgba(90, 50, 163, 0.1);
      color: #5a32a3;
    }
  }
  
  /* 修复时间选择器下拉菜单选中项颜色 */
  .el-select .el-select-dropdown__item.selected {
    color: #5a32a3 !important;
    background: rgba(90, 50, 163, 0.1) !important;
  }
  
  .el-select .el-select-dropdown__item.selected:hover {
    color: #5a32a3 !important;
    background: rgba(90, 50, 163, 0.1) !important;
  }
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
