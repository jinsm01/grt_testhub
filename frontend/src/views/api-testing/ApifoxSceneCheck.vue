<template>
  <div class="page-container">
    <!-- 配置面板 - 参考 InterfaceList.vue 顶部样式 -->
    <div v-if="!showReportDetail" class="page-header">
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
        <el-button @click="exemptionsDrawerVisible = true">
          <el-icon style="margin-right: 4px;"><CircleCheck /></el-icon>
          白名单
        </el-button>
        <el-button type="primary" @click="generateReport" :loading="generating" :disabled="generating">
          <el-icon style="margin-right: 4px;"><VideoPlay /></el-icon>
          {{ generating ? '生成中...' : '开始检查' }}
        </el-button>
      </div>
    </div>

    <!-- 生成进度弹窗 -->
    <el-dialog
      v-model="progressDialogVisible"
      title="生成进度"
      width="480px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="!generating"
      destroy-on-close
    >
      <div class="progress-dialog-content">
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
      <template #footer>
        <el-button v-if="!generating" @click="progressDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

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
        <el-table class="check-rules-table" :data="checkRules" :header-cell-style="{ background: '#ffffff', color: '#5a32a3', fontWeight: 600, fontSize: '14px' }">
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

    <!-- 白名单抽屉 -->
    <el-drawer
      v-model="exemptionsDrawerVisible"
      title="ID字段豁免列表"
      direction="rtl"
      size="950px"
      :close-on-press-escape="true"
      :destroy-on-close="true"
    >
      <div class="exemptions-drawer-content">
        <div class="exemptions-drawer-header">
          <el-button type="primary" size="small" @click="openAddExemptionDialog">
            <el-icon><Plus /></el-icon>
            添加豁免
          </el-button>
        </div>
        <el-table
          :data="exemptionTableData"
          v-loading="exemptionLoading"
          empty-text="暂无豁免字段，点击「添加豁免」创建"
          :header-cell-style="{ background: '#ffffff', color: '#5a32a3', fontWeight: 600, fontSize: '14px' }"
        >
          <el-table-column label="豁免ID字段" min-width="180">
            <template #default="{ row }">
              <span class="exemption-field-cell">
                <el-tag
                  :type="row._builtin ? 'info' : ''"
                  size="small"
                  :class="row._builtin ? 'builtin-tag' : 'user-tag'"
                  disable-transitions
                >{{ row.field }}</el-tag>
                <el-tag v-if="row._builtin" type="info" size="small" effect="plain" class="ml-2">内置</el-tag>
              </span>
            </template>
          </el-table-column>
          <el-table-column label="豁免理由" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.reason" class="reason-text">{{ row.reason }}</span>
              <span v-else class="reason-placeholder">-</span>
            </template>
          </el-table-column>
          <el-table-column label="添加人" width="110" align="center">
            <template #default="{ row }">
              {{ row.added_by || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="添加时间" width="170" align="center">
            <template #default="{ row }">
              {{ row._builtin ? '-' : (formatTime(row.added_at) || '-') }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-switch
                v-if="!row._builtin"
                v-model="row.enabled"
                size="small"
                @change="toggleExemption(row)"
                :loading="row._toggling"
              />
              <el-tag v-else type="success" size="small" effect="dark">启用</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" align="center" fixed="right">
            <template #default="{ row }">
              <template v-if="!row._builtin">
                <el-button class="action-btn edit-btn" size="small" @click="openEditReasonDialog(row)">
                  <el-icon><Edit /></el-icon>
                  <span>编辑</span>
                </el-button>
                <el-button class="action-btn delete-btn" size="small" @click="deleteExemption(row)">
                  <el-icon><Delete /></el-icon>
                  <span>删除</span>
                </el-button>
              </template>
              <span v-else class="builtin-hint">系统管理</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>

    <!-- 添加/编辑豁免弹窗 -->
    <el-dialog
      v-model="exemptionDialogVisible"
      :title="editingExemption ? '编辑豁免理由' : '添加豁免字段'"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="exemptionForm" label-width="90px" label-position="left">
        <el-form-item label="豁免字段名" required>
          <el-input
            v-model="exemptionForm.field"
            placeholder="输入ID字段名，如 order_id"
            :disabled="!!editingExemption"
            clearable
            @keyup.enter="submitExemptionForm"
          />
          <div class="form-tip">匹配以 _id 或 Id 结尾的字段名（不区分大小写）</div>
        </el-form-item>
        <el-form-item label="豁免理由">
          <el-input
            v-model="exemptionForm.reason"
            type="textarea"
            :rows="3"
            placeholder="请说明为什么该字段不需要检查，如：该ID由系统自动生成，非外部传入"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exemptionDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="submitExemptionForm"
          :loading="exemptionSubmitting"
          :disabled="!exemptionForm.field.trim()"
        >
          {{ editingExemption ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 报告详情 - 直接显示 -->
    <iframe
      v-if="showReportDetail"
      :src="reportIframeUrl"
      class="report-iframe-direct"
      @load="reportLoading = false"
      frameborder="0"
      scrolling="auto"
    />

    <!-- 历史报告列表 -->
    <div v-else class="card-container">
      <!-- 加载状态 -->
      <div v-if="loadingReports" class="loading-state">
        <el-skeleton :rows="6" animated />
      </div>
      
      <!-- 空状态 -->
      <div v-else-if="reports.length === 0" class="empty-state">
        <el-empty description="暂无生成报告，请先配置并点击「开始检查」" />
      </div>

      <!-- 报告列表 -->
      <div v-else class="table-wrapper">
        <el-table
          ref="tableRef"
          :data="reports"
          v-loading="loadingReports"
          style="width: 100%"
          class="custom-table"
          :header-cell-style="{ background: '#ffffff', color: '#5a32a3', fontWeight: 600, fontSize: '14px' }"
        >
          <el-table-column label="序号" width="90" header-align="center" align="center">
            <template #default="{ $index }">
              {{ $index + 1 }}
            </template>
          </el-table-column>
          <el-table-column label="报告文件" min-width="200" header-align="center" show-overflow-tooltip>
            <template #default="{ row }">
              <div style="text-align: center; width: 100%;">
                <span class="report-filename">{{ row.filename }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="执行人" width="200" header-align="center" align="center">
            <template #default="{ row }">
              <span>{{ row.executed_by || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="文件大小" width="200" header-align="center" align="center">
            <template #default="{ row }">
              <span>{{ formatSize(row.size) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="生成时间" width="200" header-align="center" align="center">
            <template #default="{ row }">
              <span>{{ formatTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="250" header-align="center" align="center" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button type="primary" size="small" class="action-btn view-btn" @click="viewReport(row)">
                  <el-icon><View /></el-icon>
                  <span>查看</span>
                </el-button>
                <el-button type="danger" size="small" class="action-btn delete-btn" @click="deleteReport(row)">
                  <el-icon><Delete /></el-icon>
                  <span>删除</span>
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="totalReports"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Setting, Check, VideoPlay, Refresh, FolderOpened, View, Delete, Loading, List, CircleCheck, Plus, Edit, ArrowLeft } from '@element-plus/icons-vue'
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
const tableRef = ref(null)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const totalReports = ref(0)

// 报告查看
const reportIframeUrl = ref('')
const currentReportName = ref('')
const reportLoading = ref(true)
const showReportDetail = ref(false)

// 规则查看抽屉
const rulesDrawerVisible = ref(false)

// 白名单抽屉
const exemptionsDrawerVisible = ref(false)

// 生成进度弹窗
const progressDialogVisible = ref(false)

// 检查规则
const checkRules = [
  { index: 1, name: '场景运行通过', severity: '高', severityType: 'danger', desc: '检查场景最近一次运行是否通过' },
  { index: 2, name: '单场景步骤数不超过10步', severity: '中', severityType: 'warning', desc: '不含引用其他场景或分组的步骤' },
  { index: 3, name: '增删改后查询断言', severity: '高', severityType: 'danger', desc: 'POST/PUT/DELETE/PATCH后是否有/Search查询并断言' },
  { index: 4, name: 'Id参数不能写死', severity: '高', severityType: 'danger', desc: '请求Body中ID参数是否硬编码' }, 
  { index: 5, name: '参数来源校验', severity: '高', severityType: 'danger', desc: '后续步骤参数是否从前置步骤或变量获取' },
  { index: 6, name: '名称参数自动化标识', severity: '高', severityType: 'danger', desc: 'Name/Title字段是否含"自动化"标识且为动态值' },
  { index: 7, name: '前置后置目录跳过统计', severity: '跳过', severityType: 'info', desc: '排除规则，不产生违规判定' },
]

// ID字段豁免列表
const builtinExemptions = ref([])
const userExemptions = ref([])
const exemptionLoading = ref(false)
const exemptionTableData = computed(() => {
  const builtin = builtinExemptions.value.map(f => ({
    field: f,
    reason: '系统内置豁免字段',
    added_by: 'system',
    added_at: '',
    enabled: true,
    _builtin: true,
  }))
  const user = userExemptions.value.map(e => ({
    ...e,
    _builtin: false,
  }))
  return [...builtin, ...user]
})

// 添加/编辑弹窗
const exemptionDialogVisible = ref(false)
const editingExemption = ref(null)
const exemptionSubmitting = ref(false)
const exemptionForm = reactive({ field: '', reason: '' })

// 加载豁免列表
const loadExemptions = async () => {
  exemptionLoading.value = true
  try {
    const res = await api.get('/api-testing/apifox-check/exemptions/')
    builtinExemptions.value = res.data.builtin || []
    userExemptions.value = res.data.user_defined || []
  } catch (e) {
    console.error('加载豁免列表失败:', e)
  } finally {
    exemptionLoading.value = false
  }
}

// 打开添加弹窗
const openAddExemptionDialog = () => {
  editingExemption.value = null
  exemptionForm.field = ''
  exemptionForm.reason = ''
  exemptionDialogVisible.value = true
}

// 打开编辑理由弹窗
const openEditReasonDialog = (row) => {
  editingExemption.value = row
  exemptionForm.field = row.field
  exemptionForm.reason = row.reason || ''
  exemptionDialogVisible.value = true
}

// 提交弹窗表单
const submitExemptionForm = async () => {
  const field = exemptionForm.field.trim().toLowerCase()
  if (!field) return
  exemptionSubmitting.value = true
  try {
    if (editingExemption.value) {
      // 编辑理由
      const res = await api.post('/api-testing/apifox-check/exemptions/', {
        action: 'update_reason',
        field: editingExemption.value.field,
        reason: exemptionForm.reason.trim(),
      })
      // 更新本地数据
      const idx = userExemptions.value.findIndex(e => e.field === editingExemption.value.field)
      if (idx >= 0) userExemptions.value[idx] = res.data.item
      ElMessage.success(res.data.message || '更新成功')
    } else {
      // 添加
      const res = await api.post('/api-testing/apifox-check/exemptions/', {
        action: 'add',
        field: field,
        reason: exemptionForm.reason.trim(),
      })
      userExemptions.value = res.data.user_defined || []
      ElMessage.success(res.data.message || '添加成功')
    }
    exemptionDialogVisible.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '操作失败')
  } finally {
    exemptionSubmitting.value = false
  }
}

// 启停开关
const toggleExemption = async (row) => {
  row._toggling = true
  try {
    const res = await api.post('/api-testing/apifox-check/exemptions/', {
      action: 'toggle',
      field: row.field,
    })
    // 更新本地数据
    const idx = userExemptions.value.findIndex(e => e.field === row.field)
    if (idx >= 0) userExemptions.value[idx] = res.data.item
    ElMessage.success(res.data.message)
  } catch (e) {
    row.enabled = !row.enabled // 回滚
    ElMessage.error(e.response?.data?.error || '操作失败')
  } finally {
    row._toggling = false
  }
}

// 删除豁免
const deleteExemption = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除豁免字段「${row.field}」吗？删除后将恢复对该字段的检查。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await api.post('/api-testing/apifox-check/exemptions/', {
      action: 'delete',
      field: row.field,
    })
    userExemptions.value = userExemptions.value.filter(e => e.field !== row.field)
    ElMessage.success(`已删除豁免字段「${row.field}」`)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.error || '删除失败')
    }
  }
}

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
  progressDialogVisible.value = true
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
    const allReports = res.data.reports || []
    totalReports.value = allReports.length
    
    // 分页处理
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    reports.value = allReports.slice(start, end)
  } catch (e) {
    ElMessage.error('加载报告列表失败')
  } finally {
    loadingReports.value = false
  }
}

// 分页大小变化
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  loadReports()
}

// 页码变化
const handleCurrentChange = (val) => {
  currentPage.value = val
  loadReports()
}

// 查看报告 - 在当前页显示详情
const viewReport = (row) => {
  currentReportName.value = row.filename
  reportIframeUrl.value = `/api/api-testing/apifox-check/report/${row.filename}/`
  reportLoading.value = true
  showReportDetail.value = true
}

// 返回列表
const backToList = () => {
  showReportDetail.value = false
  reportIframeUrl.value = ''
  currentReportName.value = ''
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
  loadExemptions()
})
</script>

<style lang="scss" scoped>
// ========== 页面容器（与 GeneratedTestCaseList 统一） ==========
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;

  // 当显示报告详情时，移除 flex 布局限制，让内容自然撑开
  &:has(.report-iframe-direct) {
    display: block;
    padding: 0;
    min-height: auto;
  }
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
      color: #333333;
      font-weight: 400;
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
// 生成进度弹窗样式
.progress-dialog-content {
  .progress-bar-wrap {
    padding: 16px 0;
  }

  .progress-info {
    padding: 8px 0;
  }

  .progress-text {
    text-align: center;
    color: #7b42f6;
    font-size: 14px;
    font-weight: 500;
    margin: 16px 0 0 0;
  }
}

// ========== 报告文件名（纯文本样式） ==========
.report-filename {
  color: #333333;
  font-size: 13px;
  font-weight: 400;
}

// ========== 操作按钮样式（参考 XMindConverter.vue） ==========
.action-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px !important;
  border-radius: 6px;
  transition: all 0.3s ease;

  .el-icon {
    font-size: 14px;
    color: #ffffff !important;
  }

  span {
    font-size: 12px;
    color: #ffffff !important;
  }

  &.view-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #6b32e6 0%, #4a2393 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }
  }

  &.delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
    }
  }
}

// ========== 表格全局样式覆盖（参考 InterfaceList.vue） ==========
:deep(.el-table) {
  border: none;
  border-radius: 8px 8px 0 0;
  overflow: hidden;
  min-height: 200px;
  box-shadow: none;
  transition: all 0.3s ease;
  background-color: #ffffff !important;

  /* 覆盖 Element Plus 默认主题变量 */
  --el-color-primary: #7b42f6;
  --el-color-primary-light-3: #9370db;
  --el-color-primary-light-5: #a888e0;
  --el-color-primary-light-7: #c2a9f3;
  --el-color-primary-light-9: #f8f7ff;
  --el-border-color: #e9ecef;
  --el-fill-color-blank: #ffffff;
  --el-table-header-bg-color: #ffffff;
  --el-table-row-hover-bg-color: #ffffff;
  --el-table-tr-bg-color: #ffffff;

  :deep(.el-table__inner-wrapper) {
    background-color: #ffffff !important;
  }

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
    padding: 16px !important;
    text-align: center;
    transition: all 0.3s ease;

    &:hover {
      background-color: #ffffff !important;
    }
  }

  :deep(th .cell) {
    font-weight: 600;
    color: #5a32a3;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  :deep(.el-table__body-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(tr) {
    cursor: pointer;
    background-color: #ffffff !important;

    &:hover {
      background-color: #ffffff !important;
    }
  }

  :deep(td) {
    padding: 12px 16px;
    border-bottom: 1px solid #e9ecef;
    color: #333;
    font-size: 14px;
    font-weight: 400;
    line-height: 24px;
    vertical-align: middle;
    text-align: center;
    background-color: #ffffff !important;

    .cell {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 24px;
    }
  }

  :deep(.el-table__empty-block) {
    background-color: #ffffff !important;
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
  height: 100%;
  gap: 20px;
  background: #ffffff;

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
  height: calc(100vh - 120px);
  border: none;
  border-radius: 0 0 8px 8px;
}

// ========== 报告详情页样式 ==========
// 报告详情 iframe 直接显示 - 使用浏览器原生滚动条
.report-iframe-direct {
  width: 100%;
  height: auto;
  min-height: 100vh;
  border: none;
  display: block;
}

// ========== 规则抽屉内容 ==========
.rules-drawer-content {
  padding: 20px;
  overflow-x: hidden;

  :deep(.el-table) {
    overflow-x: hidden;

    .el-table__body-wrapper {
      overflow-x: hidden !important;
    }
  }
}

// ========== 表格区域样式（参考 InterfaceList.vue） ==========
.loading-state {
  padding: 40px;
}

.empty-state {
  padding: 60px 0;
}

.table-wrapper {
  padding: 0;
}

.pagination-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 0;
  margin-top: 8px;
  background: transparent;
  border: none;
  transition: all 0.3s ease;

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

// ========== 豁免列表 ==========
// 白名单抽屉内容样式
.exemptions-drawer-content {
  padding: 20px;
  overflow-x: hidden;

  .exemptions-drawer-header {
    margin-bottom: 16px;
    display: flex;
    justify-content: flex-end;
  }

  .exemption-field-cell {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .builtin-tag {
    background: #f0edff;
    border-color: #d4c9f0;
    color: #5a32a3;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .user-tag {
    font-family: 'SF Mono', 'Fira Code', monospace;
    color: #1890ff;
    border-color: #91d5ff;
    background: #e6f7ff;
  }

  .ml-2 {
    margin-left: 6px;
  }

  .reason-text {
    color: #555;
    font-size: 13px;
  }

  .reason-placeholder {
    color: #c0c0c0;
  }

  .builtin-hint {
    color: #b0a8c4;
    font-size: 12px;
  }

  // 操作按钮（与项目管理页统一风格）
  .action-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 6px;
    border: none;
    transition: all 0.25s ease;

    .el-icon {
      font-size: 13px;
      color: #ffffff;
    }

    span {
      color: #ffffff;
    }

    &:hover {
      transform: translateY(-1px);
    }

    &:active {
      transform: translateY(0);
    }
  }

  .edit-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    box-shadow: 0 2px 8px rgba(123, 66, 246, 0.25);

    &:hover {
      background: linear-gradient(135deg, #6b32e6 0%, #4a2393 100%);
      box-shadow: 0 4px 14px rgba(123, 66, 246, 0.35);
    }
  }

  .delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%);
    box-shadow: 0 2px 8px rgba(255, 77, 79, 0.25);

    &:hover {
      background: linear-gradient(135deg, #e8383a 0%, #b9101a 100%);
      box-shadow: 0 4px 14px rgba(255, 77, 79, 0.35);
    }
  }
}

.form-tip {
  font-size: 12px;
  color: #9a8bbd;
  margin-top: 4px;
  line-height: 1.4;
}
</style>
