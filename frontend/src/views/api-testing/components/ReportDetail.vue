<template>
  <div class="report-detail-container">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- 报告内容 -->
    <div v-else-if="reportData" class="report-content">
      <!-- 一、检查结果总览 -->
      <section class="report-section">
        <h2 class="section-title">一、检查结果总览</h2>
        <el-table :data="reportData.rule_results" class="summary-table">
          <el-table-column type="index" label="序号" width="60" align="center" />
          <el-table-column prop="rule.name" label="规则名称" width="170" show-overflow-tooltip />
          <el-table-column prop="rule.description" label="规则说明" min-width="40" show-overflow-tooltip />
          <el-table-column label="合规率" width="110" align="center">
            <template #default="{ row }">
              <span :class="getComplianceRateClass(row.compliance_rate)" style="white-space: nowrap;">
                {{ row.compliance_rate.toFixed(1) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="严重程度" width="100" align="center">
            <template #default="{ row }">
              <span class="status-badge" :class="row.rule.severity">
                {{ getSeverityLabel(row.rule.severity) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120" align="center">
            <template #default="{ row }">
              <span class="status-badge" :class="getStatusClass(row)">
                {{ getStatusLabel(row) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <!-- 二、按创建人归纳总结 -->
      <section class="report-section">
        <div class="section-header-with-filter">
          <div class="section-header-left">
            <h2 class="section-title">二、按创建人归纳总结</h2>
            <p class="section-desc-inline">按创建人统计各人的场景违规情况，支持按月份和运行结果筛选</p>
          </div>
          <!-- 筛选器 -->
          <div class="filter-bar-inline">
            <!-- 创建人选择 -->
            <el-select v-model="activeCreatorIndex" placeholder="选择创建人" style="width: 180px;">
              <el-option
                v-for="(creator, idx) in creators"
                :key="idx"
                :label="creator.name"
                :value="idx"
              />
            </el-select>
            <el-select v-model="filters.month" placeholder="月份" style="width: 120px; margin-left: 12px;">
              <el-option label="全部月份" value="all" />
              <el-option
                v-for="month in availableMonths"
                :key="month"
                :label="month"
                :value="month"
              />
            </el-select>
            <el-select v-model="filters.status" placeholder="运行结果" style="width: 140px; margin-left: 12px;">
              <el-option label="全部结果" value="all" />
              <el-option label="通过" value="passed" />
              <el-option label="失败" value="failed" />
              <el-option label="未运行" value="not_run" />
              <el-option label="未知" value="unknown" />
            </el-select>
          </div>
        </div>

        <!-- 场景统计 -->
        <div v-if="activeCreator" class="stats-cards">
          <div class="stat-card total">
            <div class="stat-label">总场景数</div>
            <div class="stat-value">{{ filteredStats.total }}</div>
          </div>
          <div class="stat-card compliant">
            <div class="stat-label">合规场景</div>
            <div class="stat-value">{{ filteredStats.compliant }}</div>
          </div>
          <div class="stat-card violation">
            <div class="stat-label">违规场景</div>
            <div class="stat-value">{{ filteredStats.violations }}</div>
          </div>
          <div class="stat-card rate" v-if="filteredStats.total > 0">
            <div class="stat-label">合规率</div>
            <div class="stat-value" :style="{ color: getComplianceColor(filteredStats.complianceRate) }">{{ filteredStats.complianceRate.toFixed(1) }}%</div>
          </div>
        </div>

        <!-- 当前创建人详情 -->
        <div v-if="activeCreator" class="creator-detail">
          <!-- 违规规则统计 -->
          <el-table :data="filteredRuleViolations" class="violation-summary-table">
            <el-table-column label="序号" width="100" align="center">
              <template #default="{ $index }">
                {{ $index + 1 }}
              </template>
            </el-table-column>
            <el-table-column prop="ruleName" label="规则名称" min-width="80" show-overflow-tooltip />
            <el-table-column prop="count" label="违规数" width="120" align="center" />
            <el-table-column label="严重程度" width="120" align="center">
              <template #default="{ row }">
                <span class="status-badge" :class="row.severity">
                  {{ getSeverityLabel(row.severity) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button type="primary" size="small" class="view-btn" @click="openViolationDrawer(row)">
                  <el-icon><View /></el-icon>
                  <span>查看</span>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 违规明细抽屉 -->
        <el-drawer
          v-model="violationDrawerVisible"
          :title="currentRuleName + ' - 违规明细'"
          size="80%"
          :close-on-click-modal="true"
          class="violation-drawer"
        >
          <div class="drawer-content">
            <p class="drawer-count">显示 {{ filteredRuleScenarios.length }} 条违规场景</p>
            <el-table
              :data="filteredRuleScenarios"
              class="detail-table"
              @sort-change="handleSort"
              stripe
              border
            >
              <el-table-column prop="id" label="场景ID" width="100" sortable />
              <el-table-column prop="name" label="场景名称" min-width="180" show-overflow-tooltip sortable />
              <el-table-column prop="folder" label="归属目录" min-width="150" show-overflow-tooltip />
              <el-table-column label="问题描述" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ row.message }}
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="150" sortable />
              <el-table-column label="运行结果" width="100" align="center">
                <template #default="{ row }">
                  <span v-html="formatRunStatus(row.run_status)" />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-drawer>
      </section>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <el-empty :description="error" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ArrowLeft, View } from '@element-plus/icons-vue'
import api from '@/utils/api'

const props = defineProps({
  filename: {
    type: String,
    required: true
  }
})

defineEmits(['back'])

// 状态
const loading = ref(false)
const error = ref('')
const reportData = ref(null)
const activeCreatorIndex = ref(0)
const filters = ref({
  month: 'all',
  status: 'all'
})
const sortConfig = ref({
  prop: '',
  order: ''
})

// 抽屉相关状态
const violationDrawerVisible = ref(false)
const currentRuleName = ref('')
const currentRuleScenarios = ref([])

// 严重程度映射
const SEVERITY_MAP = {
  high: { label: '高', type: 'danger' },
  mid: { label: '中', type: 'warning' },
  low: { label: '低', type: 'success' },
  skip: { label: '跳过', type: 'info' }
}

// 加载报告数据
const loadReport = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get(`/api-testing/apifox-check/report/${props.filename}/json/`)
    reportData.value = res.data
    activeCreatorIndex.value = 0
  } catch (err) {
    error.value = err.response?.data?.error || '加载报告失败'
  } finally {
    loading.value = false
  }
}

// 创建人列表
const creators = computed(() => {
  if (!reportData.value?.creators) return []
  return reportData.value.creators
})

// 当前选中的创建人
const activeCreator = computed(() => {
  return creators.value[activeCreatorIndex.value] || null
})

// 可用的月份列表
const availableMonths = computed(() => {
  if (!activeCreator.value) return []
  const months = new Set()
  activeCreator.value.scenarios.forEach(s => {
    if (s.month) months.add(s.month)
  })
  return Array.from(months).sort()
})

// 过滤后的场景列表
const filteredScenarios = computed(() => {
  if (!activeCreator.value) return []
  
  let result = activeCreator.value.scenarios.filter(s => {
    const monthMatch = filters.value.month === 'all' || s.month === filters.value.month
    const statusMatch = filters.value.status === 'all' || s.run_status === filters.value.status
    return monthMatch && statusMatch
  })
  
  // 排序
  if (sortConfig.value.prop && sortConfig.value.order) {
    result = [...result].sort((a, b) => {
      let va = a[sortConfig.value.prop]
      let vb = b[sortConfig.value.prop]
      
      // 数值比较
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortConfig.value.order === 'ascending' ? va - vb : vb - va
      }
      
      // 字符串比较
      va = String(va || '')
      vb = String(vb || '')
      const cmp = va.localeCompare(vb, 'zh-CN')
      return sortConfig.value.order === 'ascending' ? cmp : -cmp
    })
  }
  
  return result
})

// 过滤后的统计
const filteredStats = computed(() => {
  const total = filteredScenarios.value.length
  const violations = filteredScenarios.value.filter(s => s.is_violation).length
  const compliant = total - violations
  return {
    total,
    compliant,
    violations,
    complianceRate: total > 0 ? (compliant / total * 100) : 0
  }
})

// 过滤后的规则违规统计（基于筛选后的场景重新计算各规则违规数）
const filteredRuleViolations = computed(() => {
  if (!activeCreator.value) return []
  const rawRules = activeCreator.value.ruleViolations
  if (!rawRules || rawRules.length === 0) return []

  // 从筛选后的场景中，按去重场景统计每个规则的违规数
  const ruleCountMap = {}
  const ruleMetaMap = {} // 保存 ruleName 和 severity

  // 初始化所有规则的元信息和计数
  rawRules.forEach(r => {
    ruleCountMap[r.ruleName] = 0
    ruleMetaMap[r.ruleName] = { severity: r.severity }
  })

  // 遍历筛选后且违规的场景，按场景去重：同一场景在同一规则下只计1次
  filteredScenarios.value.forEach(s => {
    if (s.is_violation && Array.isArray(s.violations)) {
      // 收集该场景涉及的所有规则名（自动去重，用 Set）
      const violatedRuleNames = new Set(
        s.violations.filter(v => v.ruleName && ruleCountMap.hasOwnProperty(v.ruleName)).map(v => v.ruleName)
      )
      // 每个规则 +1（每个场景每规则最多贡献1次计数）
      violatedRuleNames.forEach(rn => {
        ruleCountMap[rn]++
      })
    }
  })

  // 构建结果数组，只保留有违规的规则
  return rawRules
    .map(r => ({
      ruleName: r.ruleName,
      count: ruleCountMap[r.ruleName],
      severity: ruleMetaMap[r.ruleName].severity
    }))
    .filter(r => r.count > 0)
})

// 处理排序
const handleSort = ({ prop, order }) => {
  sortConfig.value = { prop, order }
}

// 获取合规率样式类
const getComplianceRateClass = (rate) => {
  if (rate < 50) return 'rate-low'
  if (rate < 80) return 'rate-mid'
  return 'rate-high'
}

// 获取严重程度标签
const getSeverityLabel = (severity) => {
  return SEVERITY_MAP[severity]?.label || severity
}

// 获取严重程度类型
const getSeverityType = (severity) => {
  return SEVERITY_MAP[severity]?.type || 'info'
}

// 获取合规率颜色
const getComplianceColor = (rate) => {
  if (rate < 50) return '#e94560'
  if (rate < 80) return '#f5a623'
  return '#28a745'
}

// 获取状态标签
const getStatusLabel = (row) => {
  if (row.failed_count === 0) return '基本合规'
  if (row.compliance_rate < 50) return '严重违规'
  return '部分违规'
}

// 获取状态类型
const getStatusType = (row) => {
  if (row.failed_count === 0) return 'success'
  if (row.compliance_rate < 50) return 'danger'
  return 'warning'
}

// 获取状态样式类（用于自定义徽章）
const getStatusClass = (row) => {
  if (row.failed_count === 0) return 'success'
  if (row.compliance_rate < 50) return 'danger'
  return 'warning'
}

// 打开违规明细抽屉
const openViolationDrawer = (ruleRow) => {
  currentRuleName.value = ruleRow.ruleName
  // 从当前筛选后的场景中，找出 violations 数组中包含该规则的场景
  currentRuleScenarios.value = filteredScenarios.value.filter(s => {
    if (!s.is_violation || !Array.isArray(s.violations)) return false
    return s.violations.some(v => v.ruleName === ruleRow.ruleName)
  })
  violationDrawerVisible.value = true
}

// 抽屉中显示的规则场景列表
const filteredRuleScenarios = computed(() => {
  let result = currentRuleScenarios.value
  
  // 应用月份筛选
  if (filters.value.month !== 'all') {
    result = result.filter(s => s.month === filters.value.month)
  }
  
  // 应用状态筛选
  if (filters.value.status !== 'all') {
    result = result.filter(s => s.run_status === filters.value.status)
  }
  
  // 排序
  if (sortConfig.value.prop && sortConfig.value.order) {
    result = [...result].sort((a, b) => {
      let va = a[sortConfig.value.prop]
      let vb = b[sortConfig.value.prop]
      
      // 数值比较
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortConfig.value.order === 'ascending' ? va - vb : vb - va
      }
      
      // 字符串比较
      va = String(va || '')
      vb = String(vb || '')
      const cmp = va.localeCompare(vb, 'zh-CN')
      return sortConfig.value.order === 'ascending' ? cmp : -cmp
    })
  }
  
  return result
})

// 格式化运行状态
const formatRunStatus = (status) => {
  const map = {
    passed: '<span style="color: #28a745; font-weight: bold;">通过</span>',
    failed: '<span style="color: #e94560; font-weight: bold;">失败</span>',
    not_run: '<span style="color: #adb5bd;">未运行</span>',
    running: '<span style="color: #f5a623; font-weight: bold;">运行中</span>',
    unknown: '<span style="color: #6c757d;">未知</span>'
  }
  return map[status] || map.unknown
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped lang="scss">
.report-detail-container {
  padding: 0;
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  min-height: calc(100vh - 60px);
}

.report-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.report-title {
  font-size: 20px;
  color: #1a1a2e;
  margin: 0;
}

.report-meta {
  background: #fff;
  padding: 16px 24px;
  border-radius: 8px;
  margin-bottom: 20px;
  
  span {
    margin-right: 24px;
    font-size: 14px;
    color: #333;
  }
}

.report-section {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 24px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  border: 1px solid rgba(147, 112, 219, 0.12);
}

.section-title {
  font-size: 18px;
  color: #1a1a2e;
  border-left: 4px solid #7b42f6;
  padding-left: 12px;
  margin-bottom: 16px;
}

.section-desc {
  color: #666;
  font-size: 13px;
  margin-bottom: 16px;
}

// 标题、描述和筛选器同行布局
.section-header-with-filter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;

  .section-header-left {
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex: 1;
    min-width: 300px;
  }

  .section-title {
    margin-bottom: 0;
    flex-shrink: 0;
    line-height: 1.4;
  }

  .section-desc-inline {
    color: #666;
    font-size: 13px;
    margin: 0;
    line-height: 1.4;
    padding-top: 2px;
  }

  .filter-bar-inline {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;

    :deep(.el-select) {
      .el-input__wrapper {
        border-radius: 8px;
        box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
        background: #ffffff;

        &:hover {
          box-shadow: 0 0 0 1px #7b42f6 inset;
        }

        &.is-focus {
          box-shadow: 0 0 0 1px #7b42f6 inset;
        }
      }

      .el-input__inner {
        color: #333;
        font-weight: 400;
      }
    }
  }
}

// 状态徽章样式 - 参考 XMindConverter.vue
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

  // 严重程度样式 - 高
  &.high {
    background: #fff1f0;
    color: #f5222d;
  }

  // 严重程度样式 - 中
  &.mid {
    background: #fff7e6;
    color: #fa8c16;
  }

  // 严重程度样式 - 低
  &.low {
    background: #f6ffed;
    color: #52c41a;
  }

  // 严重程度样式 - 跳过
  &.skip {
    background: #f5f5f5;
    color: #8c8c8c;
  }

  // 状态样式 - 基本合规
  &.success {
    background: #f6ffed;
    color: #52c41a;
  }

  // 状态样式 - 严重违规
  &.danger {
    background: #fff1f0;
    color: #f5222d;
  }

  // 状态样式 - 部分违规
  &.warning {
    background: #fff7e6;
    color: #fa8c16;
  }
}

.creator-detail {
  padding: 0;
}

.creator-name {
  font-size: 16px;
  font-weight: 600;
  color: #5a32a3;
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 4px solid #7b42f6;
}

.filter-bar {
  margin-bottom: 16px;

  :deep(.el-select) {
    .el-input__wrapper {
      border-radius: 8px;
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
      background: #ffffff;

      &:hover {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }

      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }

    .el-input__inner {
      color: #333;
      font-weight: 400;
    }
  }
}

.stats-bar {
  margin-bottom: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  border: 1px solid rgba(147, 112, 219, 0.1);
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.05);
}

// 统计卡片容器
.stats-cards {
  display: flex;
  gap: 16px;
  margin: 0 0 24px 0;
  flex-wrap: wrap;
}

// 统计卡片
.stat-card {
  flex: 1;
  min-width: 140px;
  padding: 16px 20px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.1);
  box-shadow: 0 2px 12px rgba(147, 112, 219, 0.08);
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(147, 112, 219, 0.15);
  }

  .stat-label {
    font-size: 13px;
    color: #666;
    margin-bottom: 8px;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #1a1a2e;
  }

  // 不同类型卡片的颜色主题
  &.total {
    border-left: 4px solid #7b42f6;
    .stat-value {
      color: #7b42f6;
    }
  }

  &.compliant {
    border-left: 4px solid #52c41a;
    .stat-value {
      color: #52c41a;
    }
  }

  &.violation {
    border-left: 4px solid #f5222d;
    .stat-value {
      color: #f5222d;
    }
  }

  &.rate {
    border-left: 4px solid #fa8c16;
    .stat-value {
      color: #fa8c16;
    }
  }
}

.detail-title {
  margin-top: 20px;
  margin-bottom: 8px;
  font-size: 14px;
}

.detail-count {
  text-align: right;
  font-size: 13px;
  color: #666;
  margin: 4px 0;
}

.summary-table,
.violation-summary-table,
.detail-table {
  margin-top: 12px;
  border: none;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: none;
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

  // 表头样式
  :deep(.el-table__header-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__header) {
    background-color: #ffffff !important;
  }

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

    .cell {
      overflow: visible;
      white-space: nowrap;
    }
  }

  // 空状态
  :deep(.el-table__empty-block) {
    padding: 60px 0;
    background: #ffffff !important;

    :deep(.el-table__empty-text) {
      color: #666;
      font-size: 14px;
      line-height: 24px;
    }
  }

  // 修复固定列样式
  :deep(.el-table__fixed-right) {
    background-color: #ffffff !important;
    height: 100% !important;
  }

  :deep(.el-table__fixed-right-patch) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-body-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-header-wrapper) {
    background-color: #ffffff !important;
  }
}

.rate-low { color: #e94560; font-weight: bold; }
.rate-mid { color: #f5a623; font-weight: bold; }
.rate-high { color: #28a745; font-weight: bold; }

// 违规明细抽屉样式
.violation-drawer {
  :deep(.el-drawer__header) {
    margin-bottom: 0;
    padding: 20px;
    border-bottom: 1px solid #e9ecef;

    .el-drawer__title {
      font-size: 18px;
      font-weight: 600;
      color: #1a1a2e;
    }
  }

  :deep(.el-drawer__body) {
    padding: 0;
    background: #f5f3ff;
  }

  .drawer-content {
    padding: 20px;
    height: 100%;
    overflow-y: auto;
  }

  .drawer-count {
    margin: 0 0 16px 0;
    font-size: 13px;
    color: #666;
  }
}

// 违规规则统计表格样式 - 参考规则总览
.violation-summary-table {
  margin-top: 0;
  border: none;
  border-radius: 8px;
  overflow: hidden;
  background-color: #ffffff !important;

  :deep(.el-table__header-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__header) {
    background-color: #ffffff !important;
  }

  :deep(th) {
    background-color: #ffffff !important;
    color: #5a32a3 !important;
    font-weight: 600;
    font-size: 14px;
    border-bottom: 1px solid #e9ecef;
    padding: 12px 16px !important;
    text-align: center;
    vertical-align: middle;

    &:hover {
      background-color: #ffffff !important;
    }
  }

  :deep(th .cell) {
    background-color: #ffffff !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
  }

  :deep(.el-table__body-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__row) {
    background-color: #ffffff !important;

    &:hover {
      background-color: #f8f7ff !important;
    }
  }

  :deep(td) {
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
    color: #333;
    font-size: 14px;
    font-weight: 400;
    vertical-align: middle;

    .cell {
      overflow: visible;
      white-space: nowrap;
    }
  }

  // 最后一行无边框
  :deep(.el-table__row:last-child td) {
    border-bottom: none;
  }

  // 查看按钮样式 - 参考 XMindConverter.vue
  :deep(.view-btn) {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px !important;
    border-radius: 6px;
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: #ffffff !important;
    transition: all 0.3s ease;
    vertical-align: middle;

    .el-icon {
      font-size: 14px;
      color: #ffffff !important;
    }

    span {
      font-size: 12px;
      color: #ffffff !important;
    }

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }
  }
}

.loading-state,
.error-state {
  padding: 60px 40px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.12);
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
}
</style>
