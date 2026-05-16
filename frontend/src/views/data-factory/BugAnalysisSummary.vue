<template>
  <div class="bug-analysis-container">
    <!-- 顶部筛选栏 -->
    <div v-show="viewMode === 'list'" class="filter-bar">
      <div class="filter-bar-left">
        <!-- 汇总分析名称搜索框 -->
        <el-input
          v-model="summarySearchQuery"
          placeholder="搜索汇总分析"
          clearable
          style="width: 240px;"
          size="default"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <div class="filter-bar-spacer"></div>
      <div class="filter-bar-right">
        <!-- 新建汇总分析按钮 -->
        <el-button
          type="primary"
          @click="openSelectDialog"
          class="generate-btn"
        >
          <el-icon><TrendCharts /></el-icon>
          新建汇总分析
        </el-button>
      </div>
    </div>

    <!-- 汇总分析列表 -->
    <div v-show="viewMode === 'list'" class="step-content-area">
      <div class="card-container">
        <!-- 汇总列表 -->
        <div class="records-selector">
          <el-table
            :data="paginatedSummaryList"
            row-key="id"
            style="width: 100%"
            stripe
            v-loading="loadingSummaryList"
          >
            <el-table-column label="序号" width="80" header-align="center" align="center">
              <template #default="{ $index }">
                <span>{{ $index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="汇总分析名称" min-width="180" show-overflow-tooltip header-align="center" align="left">
              <template #default="{ row }">
                <span class="summary-name">{{ row.name || '未命名汇总' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="关联文件" min-width="200" show-overflow-tooltip header-align="center" align="left">
              <template #default="{ row }">
                <div class="file-tags">
                  <el-tag
                    v-for="(file, index) in (row.related_files || []).slice(0, 3)"
                    :key="file.id"
                    size="small"
                    class="file-tag"
                    type="info"
                    effect="plain"
                  >
                    {{ file.file_name }}
                  </el-tag>
                  <el-tag
                    v-if="(row.related_files || []).length > 3"
                    size="small"
                    class="file-tag-more"
                    type="info"
                  >
                    +{{ row.related_files.length - 3 }}
                  </el-tag>
                  <span v-if="!(row.related_files || []).length" class="text-gray">-</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="record_count" label="文件数" width="100" header-align="center" align="center">
              <template #default="{ row }">
                <span class="count-badge">{{ row.record_count || 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="total_bugs" label="Bug数" width="120" header-align="center" align="center">
              <template #default="{ row }">
                <span class="count-badge bug-count">{{ row.total_bugs || 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="group_by" label="时间聚合" width="120" header-align="center" align="center" class-name="group-by-column">
              <template #default="{ row }">
                <span class="group-tag">{{ formatGroupBy(row.group_by) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" header-align="center" align="center">
              <template #default="{ row }">
                <span class="time-text">{{ formatDate(row.created_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right" header-align="center" align="center">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button size="small" type="primary" class="action-btn view-btn" @click="viewSummaryDetail(row)">
                    <el-icon><View /></el-icon>
                    <span>查看</span>
                  </el-button>
                  <el-button size="small" type="danger" class="action-btn delete-btn" @click="deleteSummary(row)">
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 分页 -->
        <div class="pagination-container" v-if="filteredSummaryList.length > 0">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="filteredSummaryList.length"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>

        <!-- 空状态提示 - 无汇总分析 -->
        <div v-if="summaryList.length === 0 && !loadingSummaryList" class="records-empty">
          <el-empty description="暂无汇总分析">
            <template #image>
              <el-icon :size="60" color="#dcdfe6"><Document /></el-icon>
            </template>
            <el-button type="primary" @click="openSelectDialog">
              <el-icon><TrendCharts /></el-icon>
              新建汇总分析
            </el-button>
          </el-empty>
        </div>

        <!-- 空状态提示 - 搜索无结果 -->
        <div v-else-if="filteredSummaryList.length === 0 && !loadingSummaryList" class="records-empty">
          <el-empty description="未找到匹配的汇总分析">
            <template #image>
              <el-icon :size="60" color="#dcdfe6"><Search /></el-icon>
            </template>
          </el-empty>
        </div>
      </div>
    </div>

    <!-- 汇总详情展示 -->
    <div v-if="viewMode === 'detail' && summaryData" class="step-content-area">
      <!-- 核心指标卡片 -->
      <div class="summary-cards">
        <el-row :gutter="16">
          <el-col :span="4" :xs="12">
            <div class="summary-card">
              <div class="summary-icon" style="background: #e6f7ff; color: #1890ff;"><el-icon><Document /></el-icon></div>
              <div class="summary-info">
                <div class="summary-value">{{ summaryData.metrics.total_bugs }}</div>
                <div class="summary-label">总 Bug 数</div>
                <div class="summary-sub">全部缺陷汇总</div>
              </div>
              <el-tooltip content="本次分析汇总的所有 Bug 总数，包括测试期间发现的缺陷和线上故障" placement="top" effect="dark">
                <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
              </el-tooltip>
            </div>
          </el-col>
          <el-col :span="4" :xs="12">
            <div class="summary-card">
              <div class="summary-icon" style="background: #f6ffed; color: #52c41a;"><el-icon><Grid /></el-icon></div>
              <div class="summary-info">
                <div class="summary-value">{{ summaryData.metrics.total_modules }}</div>
                <div class="summary-label">涉及模块</div>
                <div class="summary-sub">跨模块统计</div>
              </div>
              <el-tooltip content="出现 Bug 的功能模块数量，反映问题分布的广度" placement="top" effect="dark">
                <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
              </el-tooltip>
            </div>
          </el-col>
          <el-col :span="4" :xs="12">
            <div class="summary-card">
              <div class="summary-icon" style="background: #fff7e6; color: #fa8c16;"><el-icon><Files /></el-icon></div>
              <div class="summary-info">
                <div class="summary-value">{{ summaryData.metrics.record_count }}</div>
                <div class="summary-label">分析记录</div>
                <div class="summary-sub">历史版本数</div>
              </div>
              <el-tooltip content="参与本次汇总分析的原始 Bug 文件数量" placement="top" effect="dark">
                <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
              </el-tooltip>
            </div>
          </el-col>
          <el-col :span="4" :xs="12">
            <div class="summary-card">
              <div class="summary-icon" style="background: #fff2f0; color: #ff4d4f;"><el-icon><Warning /></el-icon></div>
              <div class="summary-info">
                <div class="summary-value">{{ summaryData.metrics.online_bugs }}</div>
                <div class="summary-label">线上故障</div>
                <div class="summary-sub">生产环境问题</div>
              </div>
              <el-tooltip content="已发布到生产环境后发现的 Bug 数量，代表漏测风险" placement="top" effect="dark">
                <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
              </el-tooltip>
            </div>
          </el-col>
          <el-col :span="4" :xs="12">
            <div class="summary-card">
              <div class="summary-icon" style="background: #f9f0ff; color: #722ed1;"><el-icon><CircleCheck /></el-icon></div>
              <div class="summary-info">
                <div class="summary-value">{{ summaryData.metrics.defect_bugs }}</div>
                <div class="summary-label">缺陷数量</div>
                <div class="summary-sub">功能/体验问题</div>
              </div>
              <el-tooltip content="测试期间发现的各类功能缺陷和体验问题数量" placement="top" effect="dark">
                <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
              </el-tooltip>
            </div>
          </el-col>
          <el-col :span="4" :xs="12">
            <div class="summary-card" :class="{ 'has-risk': summaryData?.risk_modules?.length > 0 }">
              <div class="summary-icon" style="background: #fff1f0; color: #cf1322;"><el-icon><Bell /></el-icon></div>
              <div class="summary-info">
                <div class="summary-value">{{ summaryData.risk_modules.length }}</div>
                <div class="summary-label">风险模块</div>
                <div class="summary-sub">需重点关注</div>
              </div>
              <el-tooltip content="Bug 数量增长较快或问题集中的高风险模块数量" placement="top" effect="dark">
                <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
              </el-tooltip>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- Tab 标签页导航 -->
      <div v-show="false" class="tab-navigation">
        <div class="tab-item active">
          <el-icon><TrendCharts /></el-icon>
          <span>趋势分析</span>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-section">
        <el-row :gutter="16" class="chart-row">
          <!-- 趋势分析 -->
          <el-col :span="12">
            <div class="card-container chart-card">
              <div class="card-header">
                <span class="header-title"><el-icon><TrendCharts /></el-icon> Bug 趋势分析</span>
              </div>
              <div ref="trendChartRef" class="chart-container"></div>
            </div>
          </el-col>

          <!-- 热点模块排名 -->
          <el-col :span="12">
            <div class="card-container chart-card">
              <div class="card-header">
                <span class="header-title"><el-icon><Histogram /></el-icon> 热点模块 Top10</span>
              </div>
              <div ref="moduleChartRef" class="chart-container"></div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 风险预警 -->
      <div class="risk-section" v-if="summaryData && summaryData.risk_modules && summaryData.risk_modules.length > 0">
        <div class="card-container">
          <div class="card-header">
            <span class="header-title"><el-icon><Warning /></el-icon> 风险预警</span>
            <el-tag type="danger" size="small">{{ summaryData.risk_modules.length }} 个高风险模块</el-tag>
          </div>
          <el-table :data="summaryData.risk_modules" style="width: 100%" stripe>
            <el-table-column type="index" width="50" align="center" />
            <el-table-column prop="module" label="模块名称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="current" label="当前数量" width="100" align="center">
              <template #default="{ row }">
                <span class="p0-badge">{{ row.current }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="previous" label="历史基数" width="100" align="center">
              <template #default="{ row }">
                <span class="text-gray">{{ row.previous }}</span>
              </template>
            </el-table-column>
            <el-table-column label="增长率" width="120" align="center">
              <template #default="{ row }">
                <span class="growth-rate" :class="row.growth_rate > 1 ? 'high-risk' : 'medium-risk'">
                  +{{ (row.growth_rate * 100).toFixed(0) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="趋势" min-width="200">
              <template #default="{ row }">
                <div class="mini-trend">
                  <span
                    v-for="(point, idx) in row.trend_data"
                    :key="idx"
                    class="trend-point"
                    :style="{ height: `${(point.count / Math.max(...row.trend_data.map(t => t.count))) * 30}px` }"
                    :title="`${point.date}: ${point.count}`"
                  />
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- AI 洞察 -->
      <div class="ai-section">
        <div class="card-container">
          <div class="card-header">
            <span class="header-title"><el-icon><Cpu /></el-icon> AI 智能洞察</span>
            <el-button
              type="primary"
              size="small"
              class="ai-generate-btn"
              :loading="isCurrentAnalyzing"
              :disabled="!!aiInsight || isCurrentAnalyzing"
              @click="generateAIInsight"
            >
              {{ isCurrentAnalyzing ? '生成中...' : (aiInsight ? '已生成' : '生成洞察') }}
            </el-button>
          </div>
          
          <div v-if="aiInsight" class="ai-content">
            <div class="ai-insight" v-html="renderMarkdown(aiInsight)"></div>
          </div>
          <div v-else class="ai-placeholder">
            <el-empty description="点击上方按钮生成 AI 智能洞察">
              <template #image>
                <el-icon :size="60" color="#909399"><Cpu /></el-icon>
              </template>
            </el-empty>
          </div>
        </div>
      </div>
    </div>

    <!-- 文件选择弹窗 -->
    <el-dialog
      v-model="selectDialogVisible"
      title="新建汇总分析"
      width="900px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="dialog-content">
        <!-- 弹窗顶部筛选栏 -->
        <div class="dialog-filter-bar">
          <el-input
            v-model="searchQuery"
            placeholder="搜索文件名"
            clearable
            style="width: 240px;"
            size="default"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select v-model="groupBy" size="default" style="width: 160px;">
            <template #prefix>
              <span class="select-prefix-label">时间聚合</span>
            </template>
            <el-option label="按周" value="week" />
            <el-option label="按月" value="month" />
            <el-option label="按季度" value="quarter" />
            <el-option label="按半年" value="half_year" />
            <el-option label="按年" value="year" />
          </el-select>
          <div class="flex-spacer"></div>
          <div class="status-tag">
            <el-icon class="status-icon"><Checked /></el-icon>
            <span>已选择 {{ selectedRecords.length }} 个记录</span>
          </div>
        </div>

        <!-- 文件列表 -->
        <div class="dialog-table-wrapper">
          <el-table
            ref="recordsTable"
            :data="filteredRecords"
            row-key="id"
            style="width: 100%"
            height="400"
            stripe
            @selection-change="handleSelectionChange"
            v-loading="loadingRecords"
          >
            <el-table-column type="selection" width="55" header-align="center" align="center" :reserve-selection="true" />
            <el-table-column label="序号" width="60" header-align="center" align="center">
              <template #default="{ $index }">
                <span>{{ $index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="file_name" label="文件名" min-width="180" show-overflow-tooltip header-align="center" align="left">
              <template #default="{ row }">
                <span>{{ row.file_name || '未命名' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="total_bugs" label="Bug数" width="80" header-align="center" align="center">
              <template #default="{ row }">
                <span class="count-badge">{{ row.total_bugs || 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="160" header-align="center" align="center">
              <template #default="{ row }">
                <span class="time-text">{{ formatDate(row.created_at) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 空状态 -->
        <div v-if="availableRecords.length === 0 && !loadingRecords" class="dialog-empty">
          <el-empty description="暂无历史记录">
            <template #image>
              <el-icon :size="60" color="#dcdfe6"><Document /></el-icon>
            </template>
          </el-empty>
        </div>
        <div v-else-if="filteredRecords.length === 0 && !loadingRecords" class="dialog-empty">
          <el-empty description="未找到匹配的文件">
            <template #image>
              <el-icon :size="60" color="#dcdfe6"><Search /></el-icon>
            </template>
          </el-empty>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="closeSelectDialog">取消</el-button>
          <el-button
            type="primary"
            :disabled="selectedRecords.length === 0"
            :loading="analyzing"
            @click="generateSummary"
          >
            生成汇总分析
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { marked } from 'marked'
import api from '@/utils/api'
import {
  Document, Grid, Files, Warning, CircleCheck, Bell,
  TrendCharts, Histogram, Cpu, Checked, ArrowLeft, Search,
  View, Delete, InfoFilled
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 视图模式: list-列表, detail-详情
const viewMode = ref(route.query.view === 'detail' ? 'detail' : 'list')

// 汇总分析列表相关
const summaryList = ref([])
const loadingSummaryList = ref(false)
const summarySearchQuery = ref('')

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)

// 文件选择弹窗相关
const selectDialogVisible = ref(false)
const availableRecords = ref([])
const selectedRecords = ref([])
const groupBy = ref('month')
const loadingRecords = ref(false)
const analyzing = ref(false)

// 汇总详情相关
const currentSummaryId = ref(null)
const summaryData = ref(null)
const aiAnalyzingIds = ref(new Set())  // 记录正在生成洞察的汇总ID集合
const aiInsight = ref('')
const searchQuery = ref('') // 弹窗内文件名搜索关键词

// 当前汇总是否正在生成洞察
const isCurrentAnalyzing = computed(() => {
  return currentSummaryId.value && aiAnalyzingIds.value.has(currentSummaryId.value)
})

// 过滤后的汇总列表（不分页，用于分页组件计算总数）
const filteredSummaryList = computed(() => {
  if (!summarySearchQuery.value.trim()) {
    return summaryList.value
  }
  const query = summarySearchQuery.value.toLowerCase()
  return summaryList.value.filter(summary => {
    const name = (summary.name || '').toLowerCase()
    return name.includes(query)
  })
})

// 分页后的汇总列表（用于表格展示）
const paginatedSummaryList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredSummaryList.value.slice(start, end)
})

// 过滤后的记录列表（弹窗内）
const filteredRecords = computed(() => {
  if (!searchQuery.value.trim()) {
    return availableRecords.value
  }
  const query = searchQuery.value.toLowerCase()
  return availableRecords.value.filter(record => {
    const fileName = (record.file_name || '').toLowerCase()
    return fileName.includes(query)
  })
})

// 图表引用
const trendChartRef = ref(null)
const moduleChartRef = ref(null)
let trendChart = null
let moduleChart = null

// 初始化
onMounted(() => {
  // 从 localStorage 恢复生成状态
  const savedAnalyzingIds = localStorage.getItem('bug_analysis_analyzing_ids')
  if (savedAnalyzingIds) {
    try {
      const ids = JSON.parse(savedAnalyzingIds)
      ids.forEach(id => aiAnalyzingIds.value.add(id))
    } catch (e) {
      console.error('恢复生成状态失败:', e)
    }
  }
  
  fetchSummaryList()
  // 如果 URL 中有 view=detail 和 id 参数，自动加载详情
  if (route.query.view === 'detail' && route.query.id) {
    const id = Array.isArray(route.query.id) ? route.query.id[0] : route.query.id
    const row = { id: parseInt(id) }
    viewSummaryDetail(row)
  }
})

// 监听路由 query 变化，切换视图模式
watch(() => route.query.view, (newView) => {
  if (newView === 'detail') {
    viewMode.value = 'detail'
  } else {
    viewMode.value = 'list'
    currentSummaryId.value = null
    summaryData.value = null
    aiInsight.value = ''
    if (trendChart) {
      trendChart.dispose()
      trendChart = null
    }
    if (moduleChart) {
      moduleChart.dispose()
      moduleChart = null
    }
  }
})

// 监听搜索词变化，重置页码到第一页
watch(summarySearchQuery, () => {
  currentPage.value = 1
})

// 获取汇总分析列表
const fetchSummaryList = async () => {
  loadingSummaryList.value = true
  try {
    const response = await api.get('/data-factory/bug-analysis/summaries/')
    console.log('获取汇总分析列表响应:', response.data)
    // 后端返回扁平结构: { items: [...], success: true, message: '...' }
    const items = response.data?.items || response.data?.data?.items || response.data?.data?.results || response.data?.data || []
    console.log('解析后的列表数据:', items)
    summaryList.value = items
  } catch (error) {
    console.error('获取汇总分析列表失败:', error)
    ElMessage.error('获取汇总分析列表失败')
  } finally {
    loadingSummaryList.value = false
  }
}

// 分页大小变化
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

// 页码变化
const handleCurrentChange = (val) => {
  currentPage.value = val
}

// 打开文件选择弹窗
const openSelectDialog = async () => {
  selectDialogVisible.value = true
  selectedRecords.value = []
  searchQuery.value = ''
  groupBy.value = 'month'
  await fetchAvailableRecords()
}

// 关闭文件选择弹窗
const closeSelectDialog = () => {
  selectDialogVisible.value = false
}

// 获取可用记录列表（弹窗内）
const fetchAvailableRecords = async () => {
  loadingRecords.value = true
  try {
    const response = await api.get('/data-factory/bug-analysis/records/', {
      params: { page_size: 1000 }
    })
    availableRecords.value = response.data?.data?.items || response.data?.data?.results || response.data?.data || []
  } catch (error) {
    console.error('获取记录列表失败:', error)
    ElMessage.error('获取历史记录失败')
  } finally {
    loadingRecords.value = false
  }
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedRecords.value = selection
}

// 生成汇总分析
const generateSummary = async () => {
  if (selectedRecords.value.length === 0) {
    ElMessage.warning('请至少选择一个分析记录')
    return
  }

  analyzing.value = true
  try {
    const recordIds = selectedRecords.value.map(r => r.id)
    const response = await api.post('/data-factory/bug-analysis/summary/', {
      record_ids: recordIds,
      group_by: groupBy.value
    })

    if (response.data.success) {
      ElMessage.success('汇总分析创建成功')
      selectDialogVisible.value = false
      await fetchSummaryList()
    } else {
      ElMessage.error(response.data.message || '分析失败')
    }
  } catch (error) {
    console.error('汇总分析失败:', error)
    ElMessage.error('汇总分析失败: ' + (error.response?.data?.message || error.message))
  } finally {
    analyzing.value = false
  }
}

// 查看汇总详情
const viewSummaryDetail = async (row) => {
  currentSummaryId.value = row.id
  loadingSummaryList.value = true
  try {
    const response = await api.get(`/data-factory/bug-analysis/summaries/${row.id}/`)
    if (response.data.success) {
      // 后端返回扁平结构: { metrics: {...}, trends: [...], ... }
      summaryData.value = response.data
      viewMode.value = 'detail'
      aiInsight.value = response.data.ai_insight || ''
      // 更新路由 query 参数
      router.replace({ query: { ...route.query, view: 'detail', id: row.id } })
      await nextTick()
      renderCharts()
      
      // 检查该汇总是否在生成中（页面刷新后恢复轮询）
      if (aiAnalyzingIds.value.has(row.id) && !response.data.ai_insight) {
        ElMessage.info('正在恢复洞察生成状态，请稍候...')
        pollAIInsightStatus(row.id)
      }
    } else {
      ElMessage.error(response.data.message || '获取详情失败')
    }
  } catch (error) {
    console.error('获取汇总详情失败:', error)
    ElMessage.error('获取汇总详情失败')
  } finally {
    loadingSummaryList.value = false
  }
}

// 删除汇总分析
const deleteSummary = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该汇总分析吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const response = await api.delete(`/data-factory/bug-analysis/summaries/${row.id}/delete/`)
    if (response.data.success) {
      ElMessage.success('删除成功')
      await fetchSummaryList()
    } else {
      ElMessage.error(response.data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      // 显示更详细的错误信息（后端使用 error 或 message 键）
      const responseData = error.response?.data || {}
      const errorMsg = responseData.message || responseData.error || error.message || '删除失败'
      ElMessage.error(errorMsg)
    }
  }
}

// 返回列表
const goBackToList = () => {
  viewMode.value = 'list'
  currentSummaryId.value = null
  summaryData.value = null
  aiInsight.value = ''
  // 移除路由 query 中的 view 和 id 参数
  const { view, id, ...otherQuery } = route.query
  router.replace({ query: otherQuery })
  if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }
  if (moduleChart) {
    moduleChart.dispose()
    moduleChart = null
  }
}

// 渲染图表
const renderCharts = () => {
  if (!summaryData.value) return
  
  renderTrendChart()
  renderModuleChart()
}

// 趋势图表
const renderTrendChart = () => {
  if (!trendChartRef.value) return
  
  if (trendChart) {
    trendChart.dispose()
  }
  
  trendChart = echarts.init(trendChartRef.value)
  
  const trends = summaryData.value.trends || []
  const dates = trends.map(t => t.date)
  const totals = trends.map(t => t.total)
  const onlines = trends.map(t => t.online)
  const defects = trends.map(t => t.defect)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['Bug总数', '线上故障', '缺陷'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: 'Bug数量'
    },
    series: [
      {
        name: 'Bug总数',
        type: 'line',
        smooth: true,
        data: totals,
        itemStyle: { color: '#1890ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(24,144,255,0.3)' },
            { offset: 1, color: 'rgba(24,144,255,0.05)' }
          ])
        }
      },
      {
        name: '线上故障',
        type: 'line',
        smooth: true,
        data: onlines,
        itemStyle: { color: '#ff4d4f' }
      },
      {
        name: '缺陷',
        type: 'line',
        smooth: true,
        data: defects,
        itemStyle: { color: '#52c41a' }
      }
    ]
  }
  
  trendChart.setOption(option)
}

// 模块排名图表
const renderModuleChart = () => {
  if (!moduleChartRef.value) return
  
  if (moduleChart) {
    moduleChart.dispose()
  }
  
  moduleChart = echarts.init(moduleChartRef.value)
  
  const ranking = summaryData.value.module_ranking || []
  const names = ranking.map(r => r.module).reverse()
  const counts = ranking.map(r => r.count).reverse()
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '8%',
      bottom: '3%',
      top: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: 'Bug数'
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: {
        width: 90,
        overflow: 'truncate'
      }
    },
    series: [
      {
        type: 'bar',
        data: counts,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: '#722ed1' },
            { offset: 1, color: '#b37feb' }
          ])
        },
        label: {
          show: true,
          position: 'right'
        }
      }
    ]
  }
  
  moduleChart.setOption(option)
}



// 保存生成状态到 localStorage
const saveAnalyzingState = () => {
  localStorage.setItem('bug_analysis_analyzing_ids', JSON.stringify([...aiAnalyzingIds.value]))
}

// 从 localStorage 清除生成状态
const clearAnalyzingState = (summaryId) => {
  aiAnalyzingIds.value.delete(summaryId)
  saveAnalyzingState()
}

// 轮询检查 AI 洞察生成状态
const pollAIInsightStatus = async (summaryId, maxAttempts = 30) => {
  let attempts = 0
  const pollInterval = setInterval(async () => {
    attempts++
    try {
      const response = await api.get(`/data-factory/bug-analysis/summaries/${summaryId}/`)
      if (response.data.success) {
        // 如果已经有洞察内容，说明生成完成
        if (response.data.ai_insight) {
          aiInsight.value = response.data.ai_insight
          clearAnalyzingState(summaryId)
          clearInterval(pollInterval)
          ElMessage.success('AI 洞察生成完成')
          return
        }
      }
      // 超过最大尝试次数，停止轮询
      if (attempts >= maxAttempts) {
        clearAnalyzingState(summaryId)
        clearInterval(pollInterval)
        ElMessage.warning('洞察生成时间较长，请稍后手动刷新查看')
      }
    } catch (error) {
      console.error('轮询洞察状态失败:', error)
      clearAnalyzingState(summaryId)
      clearInterval(pollInterval)
    }
  }, 3000) // 每3秒轮询一次
}

// 生成 AI 洞察
const generateAIInsight = async () => {
  if (!summaryData.value || !currentSummaryId.value) return

  const summaryId = currentSummaryId.value
  aiAnalyzingIds.value.add(summaryId)
  saveAnalyzingState() // 保存状态到 localStorage
  
  try {
    // 调用新的 AI 洞察生成接口（后端直接调用 AI，无需经过 Dify）
    const response = await api.post('/data-factory/bug-analysis/generate-insight/', {
      summary_data: summaryData.value,
      summary_id: summaryId  // 传递汇总分析ID用于保存
    })

    console.log('AI 响应:', response.data)

    // 提取洞察内容
    if (response.data.success) {
      aiInsight.value = response.data.data?.insight || 'AI 分析完成，但未返回有效内容'
      clearAnalyzingState(summaryId)
    } else {
      ElMessage.error(response.data.message || 'AI 洞察生成失败')
      clearAnalyzingState(summaryId)
    }
  } catch (error) {
    console.error('AI 洞察生成失败:', error)
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      ElMessage.info('洞察生成时间较长，将在后台继续处理，请稍后刷新查看')
      // 超时后开始轮询检查状态
      pollAIInsightStatus(summaryId)
    } else {
      ElMessage.error(error.response?.data?.message || 'AI 洞察生成失败')
      clearAnalyzingState(summaryId)
    }
  }
}

// 渲染 Markdown
const renderMarkdown = (text) => {
  return marked(text || '')
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).replace(/\//g, '/')
}

// 格式化时间聚合方式
const formatGroupBy = (groupBy) => {
  const groupMap = {
    'week': '按周',
    'month': '按月',
    'quarter': '按季度',
    'half_year': '按半年',
    'year': '按年'
  }
  return groupMap[groupBy] || groupBy
}

// 监听窗口大小变化，调整图表
window.addEventListener('resize', () => {
  trendChart?.resize()
  moduleChart?.resize()
})
</script>

<style scoped lang="scss">
/* 页面容器 - 参考 XMindConverter.vue 紫色主题 */
.bug-analysis-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
}

/* 顶部筛选栏 - 紫色主题卡片样式 */
.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  margin-bottom: 20px;

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

  :deep(.el-input__prefix) {
    color: #7b42f6;
  }

  :deep(.el-select .el-input__wrapper) {
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
    border-radius: 8px;
    background: #ffffff;

    &:hover,
    &:focus {
      box-shadow: 0 0 0 1px #7b42f6;
    }
  }

  :deep(.el-select .el-input__inner) {
    color: #5a32a3;
    font-weight: 500;
  }
}

.filter-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 顶部时间聚合维度选择器 */
.group-by-selector-top {
  display: flex;
  align-items: center;

  :deep(.el-select .el-input__wrapper) {
    height: 40px;
  }
}

.select-prefix-label {
  color: #9370db;
  font-size: 13px;
  font-weight: 400;
  padding-right: 4px;
  border-right: 1px solid rgba(147, 112, 219, 0.3);
  margin-right: 4px;
  line-height: 20px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #5a32a3;
}

.page-subtitle {
  color: #9370db;
  font-size: 13px;
}

.filter-bar-spacer {
  flex: 1;
}

.filter-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 状态标签 */
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.2);
  border-radius: 6px;
  font-size: 13px;
  color: #7b42f6;
  font-weight: 500;
}

.status-tag.success {
  background: rgba(103, 194, 58, 0.1);
  border-color: rgba(103, 194, 58, 0.2);
  color: #67c23a;
}

.status-icon {
  font-size: 14px;
}

/* 返回按钮栏 */
.back-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 步骤内容区域 */
.step-content-area {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 记录列表空状态 */
.records-empty {
  padding: 40px 0;
}

/* 卡片容器 - 参考 XMindConverter.vue 紫色主题 */
.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 20px;
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #5a32a3;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 10px;
  border-left: 4px solid #7b42f6;
}

.header-title .el-icon {
  font-size: 18px;
  color: #7b42f6;
}

/* 表格样式 - 与参考文件 XMindConverter.vue 一致 */
.records-selector {
  margin-bottom: 20px;

  /* 覆盖 Element Plus 默认主题变量 */
  --el-color-primary: #7b42f6;
  --el-border-color: #e9ecef;
  --el-border-color-light: #e9ecef;
  --el-border-color-lighter: #e9ecef;
  --el-fill-color-light: #ffffff;
  --el-fill-color-lighter: #ffffff;
  --el-fill-color-blank: #ffffff;
  --el-text-color-primary: #333;
  --el-text-color-regular: #333;
  --el-text-color-secondary: #666;
  --el-table-header-bg-color: #ffffff;
  --el-table-row-hover-bg-color: #f8f7ff;
  --el-table-stripe-bg-color: #fafaff;

  &::before {
    display: none;
  }

  /* 表头包装器 */
  :deep(.el-table__header-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__header) {
    background-color: #ffffff !important;
  }

  /* 表头单元格样式 */
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

  /* 表格体样式 */
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

  /* 复选框列对齐修复 */
  :deep(.el-table-column--selection .cell) {
    padding: 0 !important;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  /* 时间聚合列 - 修复徽章显示多余的点 */
  :deep(.group-by-column .cell) {
    overflow: visible;
    text-overflow: clip;
  }

  /* 空状态样式 */
  :deep(.el-table__empty-block) {
    padding: 60px 0;
    background: #ffffff !important;
  }

  :deep(.el-table__empty-text) {
    color: #666;
    font-size: 14px;
    line-height: 24px;
  }
}

/* 操作按钮组样式 - 参考 XMindConverter.vue */
.action-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 5px 12px !important;
  border-radius: 6px;
  transition: all 0.3s ease;
  border: none !important;

  .el-icon {
    font-size: 14px;
  }

  span {
    font-size: 12px;
  }

  &.view-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    color: #ffffff !important;

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }
  }

  &.delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
    color: #ffffff !important;

    &:hover {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
    }
  }
}

/* 数据单元格内容样式 */
.file-name {
  color: #5a32a3;
  font-weight: 500;
}

.index-number {
  display: inline-block;
  min-width: 24px;
  padding: 2px 6px;
  background: rgba(147, 112, 219, 0.1);
  color: #7b42f6;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
}

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

  &.bug-count {
    background: #fff7e6;
    color: #fa8c16;
  }
}

.p0-badge {
  display: inline-block;
  min-width: 28px;
  padding: 2px 8px;
  background: #fef0f0;
  color: #f56c6c;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}

.text-gray {
  color: #909399;
}

/* 文件标签样式 */
.file-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.file-tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #f0e6ff;
  color: #7b42f6;
  white-space: nowrap;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  border: none;
}

.file-tag-more {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #f5f5f5;
  color: #666;
  white-space: nowrap;
  border: none;
}

.time-text {
  color: #606266;
  font-size: 13px;
}

.generate-btn {
  margin-left: 8px;
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

/* Tab 导航 - 紫色主题 */
.tab-navigation {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  padding: 4px;
  background: rgba(147, 112, 219, 0.08);
  border-radius: 6px;
  width: fit-content;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  color: #7b42f6;
  transition: all 0.3s;
}

.tab-item:hover {
  color: #5a32a3;
  background: rgba(147, 112, 219, 0.15);
}

.tab-item.active {
  background: #fff;
  color: #5a32a3;
  font-weight: 500;
  box-shadow: 0 1px 4px rgba(147, 112, 219, 0.2);
}

.tab-item .el-icon {
  font-size: 16px;
}

/* 汇总统计卡片 - 紫色主题 */
.summary-cards {
  margin-bottom: 20px;
}

.summary-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid rgba(147, 112, 219, 0.12);
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  transition: all 0.3s;
  height: 100%;
  position: relative;
}

.summary-card:hover {
  box-shadow: 0 6px 20px rgba(147, 112, 219, 0.15);
  transform: translateY(-2px);
}

.summary-card.has-risk {
  border-color: #ff4d4f;
  background: #fff1f0;
}

.card-tooltip-icon {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #f0f0f0;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.card-tooltip-icon:hover {
  background: #7b42f6;
  color: #fff;
}

.summary-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.summary-info {
  flex: 1;
  min-width: 0;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: #5a32a3;
  line-height: 1.2;
}

.summary-label {
  font-size: 13px;
  color: #7b42f6;
  margin-top: 4px;
  font-weight: 500;
}

.summary-sub {
  font-size: 12px;
  color: #9370db;
  margin-top: 2px;
}

/* 图表区域 */
.charts-section {
  margin-bottom: 20px;
}

.chart-row {
  margin-bottom: 16px;
}

.chart-card {
  height: 100%;
}

.chart-container {
  height: 320px;
  width: 100%;
}

/* 风险预警 */
.risk-section {
  margin-bottom: 20px;
}

.growth-rate {
  font-weight: 600;
  font-size: 14px;
}

.growth-rate.high-risk {
  color: #cf1322;
}

.growth-rate.medium-risk {
  color: #fa8c16;
}

.mini-trend {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 30px;
}

.trend-point {
  width: 8px;
  background: #7b42f6;
  border-radius: 2px;
  min-height: 4px;
}

/* AI 洞察 - 紫色主题 */
.ai-section {
  margin-bottom: 20px;

  .ai-generate-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    border-color: #7b42f6;

    &:hover {
      background: linear-gradient(135deg, #8f5af7 0%, #6a3fb8 100%);
      border-color: #8f5af7;
    }

    &:active {
      background: linear-gradient(135deg, #6a3fb8 0%, #4a2878 100%);
      border-color: #6a3fb8;
    }

    &.is-disabled {
      background: linear-gradient(135deg, #67c23a 0%, #529b2e 100%);
      border-color: #67c23a;
    }
  }
}

.ai-content {
  padding: 20px;
  background: linear-gradient(135deg, #f5f3ff 0%, #ffffff 100%);
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.2);
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.1);
}

.ai-insight {
  line-height: 1.8;
  color: #262626;
  font-size: 14px;
}

.ai-insight :deep(h1), .ai-insight :deep(h2), .ai-insight :deep(h3) {
  color: #7b42f6;
  font-weight: 600;
  margin: 20px 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid rgba(147, 112, 219, 0.2);
}

.ai-insight :deep(h1:first-child), .ai-insight :deep(h2:first-child), .ai-insight :deep(h3:first-child) {
  margin-top: 0;
}

.ai-insight :deep(ul) {
  padding-left: 0;
  list-style: none;
}

.ai-insight :deep(li) {
  margin: 8px 0;
  padding-left: 20px;
  position: relative;
}

.ai-insight :deep(li::before) {
  content: '';
  position: absolute;
  left: 6px;
  top: 10px;
  width: 6px;
  height: 6px;
  background: #7b42f6;
  border-radius: 50%;
}

.ai-insight :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(147, 112, 219, 0.1);
}

.ai-insight :deep(th) {
  background: rgba(147, 112, 219, 0.1);
  color: #5a32a3;
  font-weight: 600;
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  border-bottom: 2px solid rgba(147, 112, 219, 0.2);
}

.ai-insight :deep(td) {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);
  vertical-align: top;
}

.ai-insight :deep(tr:last-child td) {
  border-bottom: none;
}

.ai-insight :deep(tr:hover td) {
  background: rgba(147, 112, 219, 0.05);
}

.ai-insight :deep(strong) {
  color: #5a32a3;
  font-weight: 600;
}

.ai-insight :deep(p) {
  margin: 12px 0;
}

.ai-insight :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(147, 112, 219, 0.3), transparent);
  margin: 20px 0;
}

.ai-placeholder {
  padding: 40px 0;
}

/* 弹窗样式 */
.dialog-content {
  padding: 0;
}

.dialog-filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;

  .flex-spacer {
    flex: 1;
  }

  :deep(.el-input__wrapper) {
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
    border-radius: 8px;

    &:hover, &:focus {
      box-shadow: 0 0 0 1px #7b42f6;
    }
  }

  :deep(.el-select .el-input__wrapper) {
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
    border-radius: 8px;

    &:hover, &:focus {
      box-shadow: 0 0 0 1px #7b42f6;
    }
  }
}

.dialog-table-wrapper {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

.dialog-empty {
  padding: 40px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 汇总名称样式 - 使用默认文本样式 */
.summary-name {
  color: #333;
  font-weight: 400;
}

/* 聚合标签样式 */
.group-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 24px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #f6ffed;
  color: #52c41a;
  white-space: nowrap;
  transition: all 0.3s ease;
}

/* 返回栏样式 */
.back-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding: 12px 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.12);
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #7b42f6;

  &:hover {
    color: #5a32a3;
  }
}

/* 分页容器样式 */
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
</style>
