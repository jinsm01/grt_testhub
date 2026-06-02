<template>
  <div class="page-container">
    <!-- 配置面板 - 参考 InterfaceList.vue 顶部样式 -->
    <div class="page-header">
      <div class="filter-section">
        <el-input v-model="config.project_id" placeholder="Apifox 项目 ID" clearable style="width: 200px;" />
        <el-input v-model="config.environment_id" placeholder="Apifox 环境 ID" clearable style="width: 200px;" />
        <el-input
          v-model="config.access_token"
          placeholder="请输入 Apifox Access Token"
          show-password
          clearable
          style="width: 300px;"
        />
      </div>
      <div class="header-actions">
        <el-button @click="rulesDrawerVisible = true">
          <el-icon style="margin-right: 4px;"><List /></el-icon>
          规则查看
        </el-button>
        <el-button type="primary" @click="generateReport" :loading="generating" :disabled="generating">
          <el-icon style="margin-right: 4px;"><VideoPlay /></el-icon>
          {{ generating ? '生成中...' : '开始检查' }}
        </el-button>
      </div>
    </div>

    <!-- 生成进度 -->
    <div v-if="generating || taskResult" class="card-container progress-card">
      <div class="card-body">
        <el-alert
          v-if="taskError"
          :title="taskError"
          type="error"
          show-icon
          :closable="true"
          @close="taskError = ''"
        />
        <el-alert
          v-else-if="taskResult === 'completed'"
          title="报告生成成功！"
          type="success"
          show-icon
          :closable="true"
          @close="taskResult = ''"
        />
        <div v-if="generating" class="progress-bar-wrap">
          <div class="progress-info">
            <el-progress :percentage="100" :indeterminate="true" :duration="2" :stroke-width="8" />
          </div>
          <p class="progress-text">{{ progressText }}</p>
        </div>
      </div>
    </div>

    <!-- 规则查看抽屉 -->
    <el-drawer
      v-model="rulesDrawerVisible"
      title="检查规则说明"
      direction="rtl"
      size="950px"
      :close-on-press-escape="true"
      :destroy-on-close="true"
    >
      <div class="rules-drawer-content">
        <p class="rules-intro">基于以下规则对场景进行质量评估</p>
        <el-table class="check-rules-table" :data="checkRules" stripe :header-cell-style="{ background: '#fafbff', color: '#5a32a3', fontWeight: 600, fontSize: '13px' }">
          <el-table-column prop="index" label="序号" width="70" align="center" />
          <el-table-column prop="name" label="规则名称" min-width="180" />
          <el-table-column prop="severity" label="严重程度" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.severityType" size="small" effect="dark" round>{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="desc" label="规则说明" min-width="280" show-overflow-tooltip />
        </el-table>
      </div>
    </el-drawer>

    <!-- 历史报告 -->
    <div class="card-container reports-card">
      <div class="card-body no-padding">
        <el-table
          :data="reports"
          v-loading="loadingReports"
          empty-text="暂无生成报告，请先配置并点击「开始检查」"
          stripe
          :header-cell-style="{ background: '#fafbff', color: '#5a32a3', fontWeight: 600, fontSize: '13px' }"
        >
          <el-table-column label="报告文件" min-width="360" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="report-link" @click="viewReport(row)">
                <el-icon><View /></el-icon> {{ row.filename }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="执行人" width="100" align="center" class-name="cell-nowrap">
            <template #default="{ row }">
              {{ row.executed_by || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="文件大小" width="120" align="center">
            <template #default="{ row }">
              {{ formatSize(row.size) }}
            </template>
          </el-table-column>
          <el-table-column label="生成时间" width="180" align="center">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" size="small" link @click="deleteReport(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 报告查看抽屉 -->
    <el-drawer
      v-model="reportDrawerVisible"
      :title="currentReportName"
      direction="rtl"
      size="90%"
      :close-on-press-escape="true"
      :destroy-on-close="true"
    >
      <div v-if="reportLoading" class="report-loading">
        <div class="loading-spinner">
          <el-icon class="is-loading" :size="40"><Loading /></el-icon>
        </div>
        <p>正在加载报告...</p>
      </div>
      <iframe
        v-show="!reportLoading"
        :src="reportIframeUrl"
        class="report-iframe"
        @load="reportLoading = false"
        frameborder="0"
      />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Setting, Check, VideoPlay, Refresh, FolderOpened, View, Delete, Loading, List } from '@element-plus/icons-vue'
import api from '@/utils/api'

// 配置
const config = reactive({
  project_id: '7366718',
  environment_id: '39566850',
  access_token: '',
})
const savingConfig = ref(false)

// 报告生成
const generating = ref(false)
const progressText = ref('')
const taskResult = ref('')
const taskError = ref('')
let pollTimer = null

// 历史报告
const reports = ref([])
const loadingReports = ref(false)

// 报告查看
const reportDrawerVisible = ref(false)
const reportIframeUrl = ref('')
const currentReportName = ref('')
const reportLoading = ref(true)

// 规则查看抽屉
const rulesDrawerVisible = ref(false)

// 检查规则
const checkRules = [
  { index: 1, name: '场景运行通过', severity: '🔴 高', severityType: 'danger', desc: '检查场景最近一次运行是否通过' },
  { index: 2, name: '单场景步骤数不超过10步', severity: '🟡 中', severityType: 'warning', desc: '不含引用其他场景或分组的步骤' },
  { index: 3, name: '增删改后查询断言', severity: '🔴 高', severityType: 'danger', desc: 'POST/PUT/DELETE/PATCH后是否有/search查询并断言' },
  { index: 4, name: 'Id参数不能写死', severity: '🔴 高', severityType: 'danger', desc: '请求body中Id参数是否硬编码' },
  { index: 5, name: '参数来源校验', severity: '🔴 高', severityType: 'danger', desc: '后续步骤参数是否从前置步骤或变量获取' },
  { index: 6, name: '名称参数自动化标识', severity: '🔴 高', severityType: 'danger', desc: 'name/title字段是否含"自动化"标识且为动态值' },
  { index: 7, name: '前置后置目录跳过统计', severity: '⏭️ 跳过', severityType: 'info', desc: '排除规则，不产生违规判定' },
]

// 加载配置
const loadConfig = async () => {
  try {
    const res = await api.get('/api-testing/apifox-check/config/')
    config.project_id = res.data.project_id || '7366718'
    config.environment_id = res.data.environment_id || '39566850'
    // 后端返回的 access_token 是脱敏的（含 ****），不要直接填入表单
    // 如果 has_token 为 true，保留空字符串提示用户已保存过
    config.access_token = ''
  } catch (e) {
    console.error('加载配置失败:', e)
  }
}

// 保存配置
const saveConfig = async () => {
  savingConfig.value = true
  try {
    await api.post('/api-testing/apifox-check/config/', {
      project_id: config.project_id,
      environment_id: config.environment_id,
      access_token: config.access_token,
    })
    ElMessage.success('配置保存成功')
  } catch (e) {
    ElMessage.error('配置保存失败: ' + (e.response?.data?.error || e.message))
  } finally {
    savingConfig.value = false
  }
}

// 生成报告
const generateReport = async () => {
  // 检查必要参数
  if (!config.project_id || !config.environment_id || !config.access_token) {
    ElMessage.warning('请填写完整的检查配置（项目ID、环境ID、令牌）')
    return
  }

  generating.value = true
  progressText.value = '正在保存配置并启动检查任务...'
  taskResult.value = ''
  taskError.value = ''

  try {
    // 先保存配置
    await api.post('/api-testing/apifox-check/config/', {
      project_id: config.project_id,
      environment_id: config.environment_id,
      access_token: config.access_token,
    })

    // 再启动检查任务
    const res = await api.post('/api-testing/apifox-check/generate/', {
      project_id: config.project_id,
      environment_id: config.environment_id,
      access_token: config.access_token,
    })

    if (res.data.task_id) {
      pollTaskStatus(res.data.task_id)
    } else {
      // 后端返回成功但没有 task_id，说明有错误
      generating.value = false
      taskError.value = res.data.error || '启动生成任务失败'
    }
  } catch (e) {
    generating.value = false
    taskError.value = e.response?.data?.error || '启动生成任务失败'
  }
}

// 轮询任务状态
const pollTaskStatus = (taskId) => {
  const poll = async () => {
    try {
      const res = await api.get(`/api-testing/apifox-check/task/${taskId}/`)
      progressText.value = res.data.progress || '处理中...'

      if (res.data.status === 'completed') {
        generating.value = false
        taskResult.value = 'completed'
        progressText.value = '报告生成完成！'
        ElMessage.success('检查报告生成成功！')
        loadReports()
        if (res.data.report_file) {
          setTimeout(() => {
            viewReport({ filename: res.data.report_file })
          }, 500)
        }
      } else if (res.data.status === 'failed') {
        generating.value = false
        taskError.value = res.data.error || '报告生成失败'
      } else {
        pollTimer = setTimeout(poll, 2000)
      }
    } catch (e) {
      generating.value = false
      taskError.value = '查询任务状态失败'
    }
  }
  poll()
}

// 加载历史报告
const loadReports = async () => {
  loadingReports.value = true
  try {
    const res = await api.get('/api-testing/apifox-check/reports/')
    reports.value = res.data.reports || []
  } catch (e) {
    ElMessage.error('加载报告列表失败')
  } finally {
    loadingReports.value = false
  }
}

// 查看报告
const viewReport = (row) => {
  currentReportName.value = row.filename
  reportIframeUrl.value = `/api/api-testing/apifox-check/report/${row.filename}/`
  reportDrawerVisible.value = true
  reportLoading.value = true
}

// 删除报告
const deleteReport = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除报告 "${row.filename}" 吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await api.delete(`/api-testing/apifox-check/report/${row.filename}/delete/`)
    ElMessage.success('报告已删除')
    loadReports()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 格式化文件大小
const formatSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 格式化时间
const formatTime = (isoStr) => {
  if (!isoStr) return '-'
  const d = new Date(isoStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

onMounted(() => {
  loadConfig()
  loadReports()
})
</script>

<style lang="scss" scoped>
// ========== 页面容器（与 GeneratedTestCaseList 统一） ==========
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

// ========== 页面标题栏（参考 InterfaceList.vue 样式） ==========
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 20px 24px;

  .filter-section {
    display: flex;
    align-items: center;
    gap: 12px;

    :deep(.el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
      background: #ffffff !important;

      &:hover {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }

      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }

    :deep(.el-input__inner) {
      color: #5a32a3;
      font-weight: 500;
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

// ========== 通用卡片容器 ==========
.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);
  background: linear-gradient(135deg, #fafbff 0%, #f8f7ff 100%);

  .card-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
    font-weight: 600;
    color: #5a32a3;

    .el-icon {
      color: #7b42f6;
    }
  }

  .card-subtitle {
    font-size: 12px;
    color: #8c8c8c;
    margin-left: auto;
    margin-right: 16px;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.card-body {
  padding: 20px 24px;

  &.no-padding {
    padding: 0;
  }
}

// ========== 进度卡片 ==========
.progress-card {
  .progress-bar-wrap {
    padding: 8px 0;
  }

  .progress-info {
    padding: 4px 0;
  }

  .progress-text {
    text-align: center;
    color: #7b42f6;
    font-size: 13px;
    font-weight: 500;
    margin: 12px 0 0 0;
  }
}

// ========== 报告链接 ==========
.report-link {
  color: #7b42f6;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;

  &:hover {
    color: #5a32a3;
    text-decoration: underline;
  }

  .el-icon {
    font-size: 14px;
  }
}

// ========== 表格全局样式覆盖 ==========
:deep(.el-table) {
  --el-table-header-bg-color: #fafbff;
  --el-table-row-hover-bg-color: #f8f7ff;
  --el-table-stripe-bg-color: #fafaff;
  border: none;
  border-radius: 0;

  &::before {
    display: none;
  }

  th {
    color: #5a32a3 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border-bottom: 1px solid rgba(147, 112, 219, 0.12) !important;
    padding: 14px 12px !important;
    white-space: nowrap !important;

    .cell {
      white-space: nowrap !important;
      overflow: visible !important;
      text-overflow: clip !important;
    }
  }

  td {
    padding: 12px !important;
    border-bottom: 1px solid #f0f0f0 !important;
    font-size: 13px;
    color: #333;

    .cell {
      white-space: nowrap !important;
      overflow: visible !important;
      text-overflow: clip !important;
    }
  }

  .el-table__row:hover > td {
    background-color: #f8f7ff !important;
  }

  .el-table__row--striped > td {
    background-color: #fafaff !important;
  }
}


// ========== Element Plus 组件微调 ==========
:deep(.el-tag--dark) {
  border-radius: 20px;
  padding: 0 12px;
  font-weight: 500;
}

:deep(.el-tag--dark.el-tag--danger) {
  background-color: #e94560;
  border-color: #e94560;
}

:deep(.el-tag--dark.el-tag--warning) {
  background-color: #f5a623;
  border-color: #f5a623;
}

:deep(.el-tag--dark.el-tag--info) {
  background-color: #909399;
  border-color: #909399;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(123, 66, 246, 0.25);

  &:hover {
    background: linear-gradient(135deg, #6b32e6 0%, #4a2393 100%);
    box-shadow: 0 4px 14px rgba(123, 66, 246, 0.35);
  }
}

// 规则查看按钮样式（与开始检查按钮类似，但使用浅色主题）
:deep(.el-button:not(.el-button--primary)) {
  background: linear-gradient(135deg, #f3f0ff 0%, #ede9fe 100%);
  border-color: rgba(123, 66, 246, 0.3);
  color: #7b42f6;
  box-shadow: 0 2px 8px rgba(123, 66, 246, 0.15);

  &:hover {
    background: linear-gradient(135deg, #ede9fe 0%, #e4dcfe 100%);
    border-color: rgba(123, 66, 246, 0.5);
    color: #5a32a3;
    box-shadow: 0 4px 14px rgba(123, 66, 246, 0.25);
  }

  .el-icon {
    color: #7b42f6;
  }
}

:deep(.el-progress-bar__outer) {
  background-color: #ede9fe;
  border-radius: 10px;
}

:deep(.el-progress-bar__inner) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border-radius: 10px;
}

:deep(.el-drawer__header) {
  background: linear-gradient(135deg, #fafbff 0%, #f8f7ff 100%);
  border-bottom: 1px solid rgba(147, 112, 219, 0.12);
  margin-bottom: 0;
  padding: 18px 24px;
  font-weight: 600;
  color: #5a32a3;
}

:deep(.el-form-item__label) {
  color: #5a32a3;
  font-weight: 500;
  font-size: 13px;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.15) inset;

  &:hover {
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.3) inset;
  }

  &.is-focus {
    box-shadow: 0 0 0 1px #7b42f6 inset;
  }
}

// ========== 报告查看 ==========
.report-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  gap: 20px;

  .loading-spinner {
    width: 80px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
    border-radius: 50%;

    .el-icon {
      color: #7b42f6;
    }
  }

  p {
    color: #6d5d8f;
    font-size: 14px;
    margin: 0;
  }
}

.report-iframe {
  width: 100%;
  height: calc(100vh - 70px);
  border: none;
  border-radius: 0 0 8px 8px;
}

// ========== 规则抽屉内容 ==========
.rules-drawer-content {
  padding: 20px;
  overflow-x: hidden;

  .rules-intro {
    color: #6d5d8f;
    font-size: 14px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);
  }

  :deep(.el-table) {
    overflow-x: hidden;

    .el-table__body-wrapper {
      overflow-x: hidden !important;
    }
  }
}

// ========== 响应式 ==========
@media (max-width: 1200px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;

    .header-right {
      width: 100%;

      .generate-btn {
        width: 100%;
      }
    }
  }
}
</style>
