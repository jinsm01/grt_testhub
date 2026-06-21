<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-main">
        <span class="page-title">
          {{ reportData?.execution_details?.case_name || reportData?.case_name || $t('uiAutomation.ai.executionReport.title') }}{{ $t('uiAutomation.ai.executionReport.reportSuffix') }}
        </span>
        <!-- 任务规划概览 -->
        <div v-if="reportData?.timeline && reportData.timeline.length > 0" class="task-plan-bar">
          <span class="plan-label">{{ $t('uiAutomation.ai.executionReport.taskPlan') }}：</span>
          <div class="plan-tags">
            <el-tooltip
              v-for="task in reportData.timeline"
              :key="task.id"
              :content="task.description"
              placement="bottom"
            >
              <el-tag :type="getTaskStatusType(task.status)" size="small" class="plan-tag">
                {{ $t('uiAutomation.ai.executionReport.task') }}{{ task.id }}
              </el-tag>
            </el-tooltip>
          </div>
        </div>
      </div>
      <div v-if="reportData?.overview" class="header-meta">
        <div class="meta-item">
          <el-icon><Timer /></el-icon>
          <span class="meta-label">{{ $t('uiAutomation.ai.executionReport.executionDuration') }}：</span>
          <span class="meta-value">{{ reportData.overview.duration_formatted }}</span>
        </div>
        <div class="meta-item">
          <el-icon><Clock /></el-icon>
          <span class="meta-label">{{ $t('uiAutomation.ai.executionReport.reportTime') }}：</span>
          <span class="meta-value">{{ formatTime(reportData.execution_details?.end_time || reportData.execution_details?.start_time) }}</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="report-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>{{ $t('uiAutomation.ai.executionReport.generatingReport') }}</span>
    </div>

    <div v-else-if="reportData" class="report-container">
      <!-- 摘要报告 -->
      <!-- 执行概览与任务统计（已隐藏，信息在步骤详情中已覆盖）
      <div v-if="reportData.overview || reportData.statistics" class="card-container">
        <div class="report-section">
          <h3 class="section-title">{{ $t('uiAutomation.ai.executionReport.overview') }}</h3>
          <div class="overview-cards">
            <div class="overview-card">
              <div class="card-label">{{ $t('uiAutomation.ai.executionReport.executionStatus') }}</div>
              <el-tag :type="reportData.overview.status_color" size="large">
                {{ reportData.overview.status }}
              </el-tag>
            </div>
            <div class="overview-card">
              <div class="card-label">{{ $t('uiAutomation.ai.executionReport.executionDuration') }}</div>
              <div class="card-value">{{ reportData.overview.duration_formatted }}</div>
            </div>
            <div class="overview-card">
              <div class="card-label">{{ $t('uiAutomation.ai.executionReport.completionRate') }}</div>
              <div class="card-value">{{ reportData.overview.completion_rate }}%</div>
            </div>
            <div class="overview-card">
              <div class="card-label">{{ $t('uiAutomation.ai.executionReport.executionSteps') }}</div>
              <div class="card-value">{{ reportData.overview.total_steps }} {{ $t('uiAutomation.ai.executionReport.steps') }}</div>
            </div>
          </div>
        </div>

        <div class="report-section" v-if="reportData.statistics">
          <h3 class="section-title">{{ $t('uiAutomation.ai.executionReport.taskStatistics') }}</h3>
          <div class="statistics-container">
            <div class="chart-wrapper">
              <div ref="pieChartRef" class="chart" style="height: 160px;"></div>
            </div>
            <div class="stats-table">
              <table class="stats-table-content">
                <tbody>
                  <tr>
                    <td>{{ $t('uiAutomation.ai.executionReport.totalTasks') }}</td>
                    <td class="stat-value">{{ reportData.statistics.total }}</td>
                  </tr>
                  <tr class="success-row">
                    <td>{{ $t('uiAutomation.ai.executionReport.completed') }}</td>
                    <td class="stat-value">{{ reportData.statistics.completed }}</td>
                  </tr>
                  <tr class="info-row">
                    <td>{{ $t('uiAutomation.ai.executionReport.pending') }}</td>
                    <td class="stat-value">{{ reportData.statistics.pending }}</td>
                  </tr>
                  <tr class="danger-row">
                    <td>{{ $t('uiAutomation.ai.executionReport.failed') }}</td>
                    <td class="stat-value">{{ reportData.statistics.failed }}</td>
                  </tr>
                  <tr class="warning-row">
                    <td>{{ $t('uiAutomation.ai.executionReport.skipped') }}</td>
                    <td class="stat-value">{{ reportData.statistics.skipped }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      -->

      <!-- 执行步骤 -->
      <div v-if="reportData.detailed_steps && reportData.detailed_steps.length > 0" class="card-container">
        <div class="report-section">
          <h3 class="section-title">{{ $t('uiAutomation.ai.executionReport.stepDetails') }}</h3>
          <div class="timeline-container">
            <template v-for="(group, groupIndex) in groupedSteps" :key="groupIndex">
              <!-- 用例分组标题 -->
              <div v-if="group.caseName" class="case-group-header">
                <el-divider content-position="left">
                  <el-tag type="primary" size="large" effect="dark">{{ group.caseName }}</el-tag>
                </el-divider>
              </div>
              <el-timeline>
                <el-timeline-item
                  v-for="step in group.steps"
                  :key="step.step_number"
                  :timestamp="`${$t('uiAutomation.ai.executionReport.step')} ${step.step_number}`"
                  placement="top"
                  :type="getStepStatusType(step.status)"
                >
                  <div class="step-card">
                    <div class="step-header">
                      <div class="action-tags">
                        <el-tag
                          v-for="(action, idx) in parseActions(step.action)"
                          :key="idx"
                          :type="getActionTagType(action.type)"
                          size="small"
                          class="action-tag"
                        >
                          {{ action.text }}
                        </el-tag>
                        <span v-if="!parseActions(step.action).length" class="no-action">-</span>
                      </div>
                      <el-tag :type="getStepStatusType(step.status)" size="small">
                        {{ step.status_display || getStepStatusText(step.status) }}
                      </el-tag>
                    </div>
                    <div v-if="step.element" class="step-element">
                      <strong>{{ $t('uiAutomation.ai.executionReport.element') }}:</strong> {{ step.element }}
                    </div>
                    <div v-if="step.thinking" class="step-thinking">
                      <strong>{{ $t('uiAutomation.ai.executionReport.thinking') }}:</strong> {{ step.thinking }}
                    </div>
                    <div v-if="step.screenshot" class="step-screenshot">
                      <el-image
                        :src="'/' + step.screenshot"
                        :preview-src-list="['/' + step.screenshot]"
                        fit="contain"
                        style="width: 100%; max-height: 200px; border-radius: 4px; margin-top: 8px;"
                      >
                        <template #error>
                          <div class="image-slot">截图加载失败</div>
                        </template>
                      </el-image>
                    </div>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </template>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="reportData.errors && reportData.errors.length > 0" class="report-section">
          <h3 class="section-title">{{ $t('uiAutomation.ai.executionReport.errorInfo') }}</h3>
          <div class="errors-list">
            <el-alert
              v-for="(error, index) in reportData.errors"
              :key="index"
              :type="error.type === 'error' ? 'error' : 'warning'"
              :title="error.message"
              :closable="false"
              show-icon
            />
          </div>
        </div>
      </div>

      <!-- 性能分析报告（已隐藏）
      <div v-if="reportData.metrics || reportData.action_distribution" class="card-container">
        <div class="report-section" v-if="reportData.metrics">
          <h3 class="section-title">{{ $t('uiAutomation.ai.executionReport.performanceMetrics') }}</h3>
          <div class="performance-metrics">
            <div class="metric-card">
              <div class="metric-label">{{ $t('uiAutomation.ai.executionReport.avgStepDuration') }}</div>
              <div class="metric-value">{{ reportData.metrics.avg_step_duration }} {{ $t('uiAutomation.ai.executionReport.seconds') }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">{{ $t('uiAutomation.ai.executionReport.maxStepDuration') }}</div>
              <div class="metric-value">{{ reportData.metrics.max_step_duration }} {{ $t('uiAutomation.ai.executionReport.seconds') }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">{{ $t('uiAutomation.ai.executionReport.minStepDuration') }}</div>
              <div class="metric-value">{{ reportData.metrics.min_step_duration }} {{ $t('uiAutomation.ai.executionReport.seconds') }}</div>
            </div>
          </div>
        </div>

        <div class="report-section" v-if="reportData.action_distribution">
          <h3 class="section-title">{{ $t('uiAutomation.ai.executionReport.actionDistribution') }}</h3>
          <div ref="barChartRef" class="chart" style="height: 250px;"></div>
        </div>

        <div v-if="reportData.bottlenecks && reportData.bottlenecks.length > 0" class="report-section">
          <h3 class="section-title">{{ $t('uiAutomation.ai.executionReport.performanceBottlenecks') }}</h3>
          <el-table :data="reportData.bottlenecks" stripe>
            <el-table-column prop="step_number" :label="$t('uiAutomation.ai.executionReport.step')" width="80" />
            <el-table-column prop="action" :label="$t('uiAutomation.ai.executionReport.action')" min-width="200" />
            <el-table-column prop="duration" :label="$t('uiAutomation.ai.executionReport.durationSeconds')" width="100" />
            <el-table-column prop="slower_than_avg_by" :label="$t('uiAutomation.ai.executionReport.slowerThanAvg')" width="100">
              <template #default="{ row }">
                {{ row.slower_than_avg_by }}%
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="reportData.recommendations && reportData.recommendations.length > 0" class="report-section">
          <h3 class="section-title">{{ $t('uiAutomation.ai.executionReport.recommendations') }}</h3>
          <div class="recommendations-list">
            <el-alert
              v-for="(rec, index) in reportData.recommendations"
              :key="index"
              type="info"
              :title="rec"
              :closable="false"
              show-icon
            />
          </div>
        </div>
      </div>
      -->
    </div>

    <div v-else class="report-error">
      <el-empty :description="$t('uiAutomation.ai.executionReport.noReportData')" />
    </div>

    <!-- GIF回放对话框 -->
    <el-dialog v-model="showGifDialog" :title="$t('uiAutomation.ai.executionReport.gifPlayback')" width="800px">
      <div v-if="reportData && reportData.gif_path" class="gif-container">
        <img :src="gifUrl" alt="Execution GIF" class="gif-image" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, nextTick, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Loading, Download, ArrowLeft, Timer, Clock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getAIExecutionReport, exportAIExecutionReportPDF } from '@/api/ui_automation'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const recordId = computed(() => route.params.id)

const loading = ref(false)
const reportData = ref(null)
const showGifDialog = ref(false)
const pieChartRef = ref(null)
const barChartRef = ref(null)
let pieChart = null
let barChart = null

// GIF URL（兼容旧数据）
const gifUrl = computed(() => {
  if (reportData.value && reportData.value.gif_path) {
    // gif_path格式：media/ai_recording/xxx.gif
    const path = reportData.value.gif_path
    // 如果路径已经包含media/，直接使用；否则添加media/
    if (path.startsWith('media/')) {
      return `/${path}`
    } else {
      return `/media/${path}`
    }
  }
  return ''
})

// 按 case_name 分组步骤（套件执行时每个步骤会带有 case_name）
const groupedSteps = computed(() => {
  if (!reportData.value || !reportData.value.detailed_steps) return []

  const steps = reportData.value.detailed_steps
  const groups = []
  let currentGroup = null

  for (const step of steps) {
    const caseName = step.case_name || ''
    if (!currentGroup || currentGroup.caseName !== caseName) {
      currentGroup = { caseName, steps: [] }
      groups.push(currentGroup)
    }
    currentGroup.steps.push(step)
  }

  return groups
})

// 加载报告数据
const loadReport = async (reportType = 'full') => {
  if (!recordId.value) return

  loading.value = true
  try {
    const response = await getAIExecutionReport(recordId.value, { report_type: reportType })
    console.log('API Response:', response.data)
    if (response.data.success) {
      reportData.value = response.data.data
      console.log('Report Data:', reportData.value)
      await nextTick()
      // 等待DOM更新后再初始化图表（单页展示同时初始化所有图表）
      setTimeout(() => {
        initPieChart()
        initBarChart()
      }, 100)
    } else {
      ElMessage.error(response.data.error || t('uiAutomation.ai.executionReport.messages.loadFailed'))
    }
  } catch (error) {
    console.error('加载报告失败:', error)
    ElMessage.error(t('uiAutomation.ai.executionReport.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

// 初始化饼图
const initPieChart = () => {
  if (!pieChartRef.value || !reportData.value) return

  // 确保统计数据存在
  if (!reportData.value.statistics) {
    console.warn('统计数据不存在')
    return
  }

  if (pieChart) {
    pieChart.dispose()
  }

  pieChart = echarts.init(pieChartRef.value)

  const stats = reportData.value.statistics
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      bottom: 0,
      left: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: {
        fontSize: 11
      }
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '65%'],
        center: ['50%', '42%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: stats.completed || 0, name: t('uiAutomation.ai.executionReport.completed'), itemStyle: { color: '#67C23A' } },
          { value: stats.pending || 0, name: t('uiAutomation.ai.executionReport.pending'), itemStyle: { color: '#909399' } },
          { value: stats.failed || 0, name: t('uiAutomation.ai.executionReport.failed'), itemStyle: { color: '#F56C6C' } },
          { value: stats.skipped || 0, name: t('uiAutomation.ai.executionReport.skipped'), itemStyle: { color: '#E6A23C' } }
        ].filter(item => item.value > 0)
      }
    ]
  }

  pieChart.setOption(option)
}

// 初始化柱状图
const initBarChart = () => {
  if (!barChartRef.value || !reportData.value) return

  // 确保性能数据存在
  if (!reportData.value.action_distribution) {
    console.warn('操作分布数据不存在')
    return
  }

  if (barChart) {
    barChart.dispose()
  }

  barChart = echarts.init(barChartRef.value)

  const distribution = reportData.value.action_distribution
  const data = [
    { name: t('uiAutomation.ai.executionReport.actions.click'), value: distribution.click || 0 },
    { name: t('uiAutomation.ai.executionReport.actions.input'), value: distribution.input || 0 },
    { name: t('uiAutomation.ai.executionReport.actions.scroll'), value: distribution.scroll || 0 },
    { name: t('uiAutomation.ai.executionReport.actions.wait'), value: distribution.wait || 0 },
    { name: t('uiAutomation.ai.executionReport.actions.switchTab'), value: distribution.switch_tab || 0 },
    { name: t('uiAutomation.ai.executionReport.actions.navigate'), value: distribution.navigate || 0 },
    { name: t('uiAutomation.ai.executionReport.actions.openTab'), value: distribution.open_tab || 0 },
    { name: t('uiAutomation.ai.executionReport.actions.done'), value: distribution.done || 0 },
    { name: t('uiAutomation.ai.executionReport.actions.other'), value: distribution.other || 0 }
  ].filter(item => item.value > 0)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.name)
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        type: 'bar',
        data: data.map(item => item.value),
        itemStyle: {
          color: '#8B5CF6'
        }
      }
    ]
  }

  barChart.setOption(option)
}

// 获取时间线类型
const getTimelineType = (status) => {
  const typeMap = {
    'completed': 'success',
    'pending': 'info',
    'failed': 'danger',
    'skipped': 'warning'
  }
  return typeMap[status] || 'info'
}

// 获取任务状态标签类型
const getTaskStatusType = (status) => {
  const typeMap = {
    'completed': 'success',
    'pending': 'info',
    'failed': 'danger',
    'skipped': 'warning'
  }
  return typeMap[status] || 'info'
}

// 获取步骤状态类型
const getStepStatusType = (status) => {
  const typeMap = {
    'completed': 'success',
    'pending': 'info',
    'failed': 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取步骤状态文本（中文）
const getStepStatusText = (status) => {
  const textMap = {
    'completed': t('uiAutomation.ai.executionReport.completed'),
    'pending': t('uiAutomation.ai.executionReport.pending'),
    'failed': t('uiAutomation.ai.executionReport.failed')
  }
  return textMap[status] || status
}

// 导出报告
const exportReport = async () => {
  if (!recordId.value) {
    ElMessage.error(t('uiAutomation.ai.executionReport.messages.missingRecordId'))
    return
  }

  try {
    ElMessage.info(t('uiAutomation.ai.executionReport.messages.generatingPdf'))

    const response = await exportAIExecutionReportPDF(recordId.value, {
      report_type: 'full'
    })

    // 创建下载链接
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    // 从响应头获取文件名，如果没有则使用默认名称
    const contentDisposition = response.headers['content-disposition']
    let filename = 'AI_Report.pdf'

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="(.+)"/)
      if (filenameMatch && filenameMatch[1]) {
        filename = decodeURIComponent(filenameMatch[1])
      }
    }

    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success(t('uiAutomation.ai.executionReport.messages.exportSuccess'))
  } catch (error) {
    console.error('导出报告失败:', error)
    ElMessage.error(error.response?.data?.error || t('uiAutomation.ai.executionReport.messages.exportFailed'))
  }
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  return new Date(timeStr).toLocaleString()
}

// 解析 action 字符串为标签列表
const parseActions = (actionStr) => {
  if (!actionStr || actionStr === '-') return []
  return actionStr.split('|').map(s => {
    const text = s.trim()
    return { text, type: getActionType(text) }
  })
}

// 根据 action 文本判断类型
const getActionType = (text) => {
  if (text.startsWith('输入')) return 'input'
  if (text.startsWith('点击')) return 'click'
  if (text.startsWith('访问') || text.startsWith('打开标签页') || text.startsWith('切换标签页')) return 'navigate'
  if (text.startsWith('标记任务完成') || text.startsWith('完成')) return 'system'
  if (text.startsWith('滚动')) return 'scroll'
  if (text.startsWith('等待')) return 'wait'
  if (text.startsWith('截图')) return 'snapshot'
  if (text.startsWith('提取内容')) return 'extract'
  if (text.startsWith('关闭标签页')) return 'close_tab'
  return 'other'
}

// 获取 action 标签的 el-tag type
const getActionTagType = (actionType) => {
  const typeMap = {
    'input': 'primary',
    'click': 'success',
    'navigate': 'warning',
    'system': 'info',
    'scroll': '',
    'wait': 'info',
    'snapshot': '',
    'extract': '',
    'close_tab': '',
    'other': ''
  }
  return typeMap[actionType] || ''
}

// 返回上一页
const goBack = () => {
  router.back()
}

// 页面加载时自动加载报告
onMounted(() => {
  if (recordId.value) {
    loadReport('full')
  }
})
</script>

<style scoped>
.report-page {
  padding: 20px;
  background: #fff;
  min-height: 100vh;
}

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
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 24px 28px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.1);
}

.page-header-main {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
}

.page-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
  flex-shrink: 0;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #7b6ca0;
}

.meta-item .el-icon {
  font-size: 14px;
  color: #7b42f6;
}

.meta-label {
  color: #9a8db8;
}

.meta-value {
  color: #5a32a3;
  font-weight: 600;
}

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
}

.report-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #909399;
  font-size: 16px;
}

.report-loading .el-icon {
  font-size: 32px;
  margin-bottom: 16px;
}

.report-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 24px;
}

.report-section {
  margin-bottom: 24px;
}

.report-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 4px solid #7b42f6;
  color: #5a32a3;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.overview-card {
  background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  border: 1px solid rgba(147, 112, 219, 0.1);
  transition: all 0.3s ease;
}

.overview-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.12);
}

.card-label {
  font-size: 11px;
  color: #7b6ca0;
  margin-bottom: 4px;
  font-weight: 500;
}

.card-value {
  font-size: 18px;
  font-weight: 700;
  color: #5a32a3;
}

.statistics-container {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.chart-wrapper {
  flex: 0 0 180px;
  max-width: 180px;
}

.chart {
  width: 100%;
  height: 100%;
}

.stats-table {
  flex: 1;
}

.stats-table-content {
  width: 100%;
  border-collapse: collapse;
  border-radius: 8px;
  overflow: hidden;
}

.stats-table-content td {
  padding: 6px 12px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.08);
  font-size: 13px;
}

.stats-table-content tr:last-child td {
  border-bottom: none;
}

.stat-value {
  font-weight: 700;
  text-align: right;
  font-size: 14px;
  color: #5a32a3;
}

.success-row {
  background-color: #f0fdf4;
}

.info-row {
  background-color: #f8f7ff;
}

.danger-row {
  background-color: #fef2f2;
}

.warning-row {
  background-color: #fffbeb;
}

.timeline-container {
  padding: 10px 0;
}

.task-plan-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  flex-wrap: wrap;
}

.plan-label {
  font-size: 12px;
  color: #7b6ca0;
  font-weight: 500;
  white-space: nowrap;
}

.plan-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.plan-tag {
  cursor: pointer;
}

.step-card {
  background: #ffffff;
  border-radius: 8px;
  padding: 14px;
  border: 1px solid rgba(147, 112, 219, 0.12);
  transition: all 0.3s ease;
}

.step-card:hover {
  box-shadow: 0 4px 12px rgba(147, 112, 219, 0.1);
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  gap: 8px;
}

.step-element,
.step-thinking {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
  line-height: 1.6;
}

.step-element strong,
.step-thinking strong {
  color: #5a32a3;
}

.action-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.action-tag {
  font-size: 13px;
}

.no-action {
  color: #909399;
  font-size: 13px;
}

.step-screenshot {
  width: 100%;
  overflow: hidden;
}

.step-screenshot :deep(.el-image__inner) {
  width: 100%;
  max-height: 200px;
  object-fit: contain;
}

.step-thinking {
  color: #7b6ca0;
  font-style: italic;
}

.performance-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.metric-card {
  background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  border: 1px solid rgba(147, 112, 219, 0.1);
  transition: all 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.12);
}

.metric-label {
  font-size: 12px;
  color: #7b6ca0;
  margin-bottom: 8px;
  font-weight: 500;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #7b42f6;
}

.gif-container {
  text-align: center;
}

.gif-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}

.report-error {
  padding: 40px 0;
  text-align: center;
}
</style>
