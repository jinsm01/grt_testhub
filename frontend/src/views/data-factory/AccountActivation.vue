<template>
  <div class="account-activation">
    <!-- 执行区域 -->
    <el-card class="execute-card" shadow="never">
      <template #header>
        <div class="execute-header">
          <span class="card-title">
            <el-icon style="margin-right: 6px;"><VideoPlay /></el-icon>
            执行批量激活
          </span>
          <div class="header-actions">
            <el-button class="ghost-btn" @click="configDrawerVisible = true">
              <el-icon><Setting /></el-icon> API 配置
            </el-button>
            <el-button class="ghost-btn" @click="importFromFactory">
              <el-icon><Upload /></el-icon> 从数据工厂导入
            </el-button>
            <el-button
              type="primary"
              class="gen-btn"
              :loading="executing"
              :disabled="!canExecute"
              @click="startBatchActivate"
            >
              <el-icon v-if="!executing"><VideoPlay /></el-icon>
              {{ executing ? '执行中...' : '开始批量激活' }}
            </el-button>
          </div>
        </div>
      </template>

      <el-form label-width="140px" label-position="right">
        <el-form-item label="租户ID">
          <el-select
            v-model="tenantId"
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入租户ID"
            style="width: 100%;"
          >
            <el-option
              v-for="t in tenantPresets"
              :key="t.id"
              :label="t.label"
              :value="t.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="用户Token">
          <el-input
            v-model="authorization"
            type="password"
            show-password
            placeholder="粘贴平台管理员的 Authorization Token"
          />
        </el-form-item>

        <el-form-item label="手机号列表">
          <div class="phone-input-wrapper">
            <el-input
              v-model="mobilesText"
              type="textarea"
              :rows="8"
              placeholder="每行一个手机号，例如：&#10;13800138000&#10;13900139000"
            />
            <div class="phone-input-footer">
            </div>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 执行结果 -->
    <el-card v-if="results.length > 0" class="result-card" shadow="never">
      <template #header>
        <div class="result-header">
          <span class="card-title">
            <el-icon style="margin-right: 6px;"><DataAnalysis /></el-icon>
            执行结果
          </span>
          <div class="summary-cards">
            <div class="summary-item total">
              <span class="num">{{ totalCount }}</span>
              <span class="label">总计</span>
            </div>
            <div class="summary-item success">
              <span class="num">{{ successCount }}</span>
              <span class="label">成功</span>
            </div>
            <div class="summary-item fail">
              <span class="num">{{ failCount }}</span>
              <span class="label">失败</span>
            </div>
          </div>
        </div>
      </template>

      <!-- 进度条 -->
      <el-progress
        :percentage="progressPercent"
        :status="executing ? '' : (failCount > 0 ? 'warning' : 'success')"
        :stroke-width="14"
        style="margin-bottom: 16px;"
      />

      <!-- 结果表格 -->
      <el-table :data="results" stripe size="small" max-height="400">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="mobile" label="手机号" width="140" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'SUCCESS' ? 'success' : 'danger'"
              size="small"
            >
              {{ row.status === 'SUCCESS' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="userId" label="用户ID" width="190">
          <template #default="{ row }">
            <span v-if="row.userId" class="mono">{{ row.userId }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="msg" label="消息" show-overflow-tooltip min-width="200">
          <template #default="{ row }">
            <span :class="{ 'msg-error': row.status !== 'SUCCESS' }">{{ row.msg || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 导出失败手机号 -->
      <div v-if="failCount > 0 && !executing" class="result-footer">
        <el-button size="small" plain @click="exportFailed">
          <el-icon><Download /></el-icon> 导出失败手机号
        </el-button>
      </div>
    </el-card>

    <!-- 激活历史 -->
    <el-card v-if="!executing" class="history-card" shadow="never">
      <template #header>
        <div class="card-header" @click="historyExpanded = !historyExpanded" style="cursor: pointer;">
          <span class="card-title">
            <el-icon style="margin-right: 6px;"><Clock /></el-icon>
            激活历史
          </span>
          <el-icon class="expand-icon" :class="{ 'is-expanded': historyExpanded }">
            <ArrowDown />
          </el-icon>
        </div>
      </template>

      <div v-show="historyExpanded">
        <el-table v-loading="historyLoading" :data="historyList" stripe size="small">
          <el-table-column prop="id" label="ID" width="60" align="center" />
          <el-table-column prop="api_url" label="接口URL" min-width="200" show-overflow-tooltip />
          <el-table-column prop="mobile_count" label="手机号数" width="100" align="center">
            <template #default="{ row }">
              <span class="mobile-count-link" @click="openLogDetail(row)">
                {{ row.mobile_count }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="结果" width="160" align="center">
            <template #default="{ row }">
              <span class="success-text">✓ {{ row.success_count }}</span>
              <span class="muted" style="margin: 0 4px;">/</span>
              <span class="fail-text">✗ {{ row.fail_count }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="执行时间" width="180" />
        </el-table>
      </div>
    </el-card>

    <!-- API 配置抽屉 -->
    <el-drawer
      v-model="configDrawerVisible"
      title="API 配置"
      size="560px"
      :close-on-click-modal="false"
    >
      <el-form label-width="120px" label-position="right" size="default">
        <el-form-item label="接口URL">
          <el-input v-model="form.api_url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="请求方法">
          <el-select v-model="form.api_method" style="width: 120px;">
            <el-option label="POST" value="POST" />
            <el-option label="GET" value="GET" />
            <el-option label="PUT" value="PUT" />
          </el-select>
        </el-form-item>
        <el-form-item label="自定义Headers">
          <el-input
            v-model="headersText"
            type="textarea"
            :rows="3"
            placeholder='{"TenantId": "xxx"}'
            @blur="syncHeadersFromText"
          />
          <div class="form-tip">JSON 格式，Authorization 由执行时输入</div>
        </el-form-item>
        <el-form-item label="Body 模板">
          <el-input
            v-model="form.body_template"
            type="textarea"
            :rows="3"
            :placeholder="bodyTemplatePlaceholder"
          />
          <div class="form-tip" v-pre>使用 {{tenant_id}} 和 {{mobiles}} 作为占位符</div>
        </el-form-item>
        <el-form-item label="执行参数">
          <div class="inline-forms">
            <div class="inline-item">
              <span class="inline-label">间隔(秒):</span>
              <el-input-number v-model="form.interval_sec" :min="0" :max="10" :step="0.1" size="small" />
            </div>
            <div class="inline-item">
              <span class="inline-label">重试次数:</span>
              <el-input-number v-model="form.max_retry" :min="0" :max="5" size="small" />
            </div>
            <div class="inline-item">
              <span class="inline-label">超时(秒):</span>
              <el-input-number v-model="form.timeout" :min="5" :max="60" size="small" />
            </div>
            <div class="inline-item">
              <span class="inline-label">每批数量:</span>
              <el-input-number v-model="form.per_batch" :min="1" :max="100" size="small" />
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="drawer-footer">
          <span></span>
          <div>
            <el-button plain @click="resetConfig">
              <el-icon><RefreshLeft /></el-icon> 恢复默认
            </el-button>
            <el-button type="primary" @click="saveConfig" :loading="savingConfig">
              <el-icon><Check /></el-icon> 保存配置
            </el-button>
          </div>
        </div>
      </template>
    </el-drawer>

    <!-- 手机号历史导入抽屉 -->
    <el-drawer
      v-model="importDrawerVisible"
      title="从数据工厂导入手机号"
      size="600px"
      :close-on-click-modal="false"
    >
      <div v-loading="phoneHistoryLoading">
        <div v-if="phoneHistoryList.length === 0" class="empty-hint">
          <el-icon :size="48" color="#c0c4cc"><Document /></el-icon>
          <p>暂无手机号生成记录</p>
          <p class="muted small">请先到「数据工厂 > 按使用场景」生成一些手机号</p>
        </div>

        <el-table
          v-else
          ref="importTableRef"
          :data="phoneHistoryList"
          stripe
          @selection-change="handleSelectionChange"
          empty-text="暂无可导入的记录"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="custom_name" label="记录名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="mobile_count" label="数量" width="80" align="center" />
          <el-table-column label="预览" min-width="180">
            <template #default="{ row }">
              <span class="mono">{{ row.preview?.join(', ') || '-' }}</span>
              <span v-if="row.mobile_count > 3" class="muted">等{{ row.mobile_count }}个</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" width="160" />
        </el-table>
      </div>

      <template #footer>
        <div class="drawer-footer">
          <span class="selection-info" v-if="selectedPhoneRecords.length">
            已选 <b>{{ selectedPhoneRecords.length }}</b> 条，合计
            <b>{{ totalImportMobiles }}</b> 个手机号
          </span>
          <span v-else class="selection-info muted">未选择任何记录</span>
          <div>
            <el-button @click="importDrawerVisible = false">取消</el-button>
            <el-button type="primary" :disabled="!selectedPhoneRecords.length" @click="confirmImport">
              确认导入
            </el-button>
          </div>
        </div>
      </template>
    </el-drawer>

    <!-- 激活日志详情抽屉 -->
    <el-drawer
      v-model="logDetailVisible"
      :title="`激活日志 ID ${logDetailData?.id || ''}`"
      size="890px"
    >
      <div v-loading="logDetailLoading">
        <div v-if="logDetailData" class="log-detail-summary">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="接口URL">{{ logDetailData.api_url }}</el-descriptions-item>
            <el-descriptions-item label="执行时间">{{ logDetailData.created_at }}</el-descriptions-item>
            <el-descriptions-item label="手机号总数">
              {{ logDetailData.mobiles?.length || logDetailData.mobile_count || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="结果">
              <span class="success-text">✓ {{ logDetailData.success_count }}</span>
              <span class="muted" style="margin: 0 4px;">/</span>
              <span class="fail-text">✗ {{ logDetailData.fail_count }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <el-table
          v-if="logDetailData?.mobiles?.length"
          :data="logDetailData.results || []"
          stripe
          size="small"
          style="margin-top: 16px;"
          max-height="calc(100vh - 260px)"
        >
          <el-table-column type="index" label="序号" width="60" align="center" />
          <el-table-column prop="mobile" label="手机号" width="150" />
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'SUCCESS' ? 'success' : 'danger'" size="small">
                {{ row.status === 'SUCCESS' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="userId" label="用户ID" width="190">
            <template #default="{ row }">
              <span v-if="row.userId" class="mono">{{ row.userId }}</span>
              <span v-else class="muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="msg" label="消息" show-overflow-tooltip min-width="160">
            <template #default="{ row }">
              <span :class="{ 'msg-error': row.status !== 'SUCCESS' }">{{ row.msg || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  User, Setting, ArrowDown, VideoPlay, Check, RefreshLeft,
  Upload, Delete, DataAnalysis, Clock, Download, Document
} from '@element-plus/icons-vue'
import {
  getActivationConfig, saveActivationConfig, resetActivationConfig,
  batchActivate, getPhoneHistory,
  getActivationLogs, getActivationLogDetail
} from '@/api/data-factory'

// ==================== 配置相关 ====================
const configDrawerVisible = ref(false)

const bodyTemplatePlaceholder = JSON.stringify(
  { tenant_id: '{{tenant_id}}', mobiles: '{{mobiles}}' },
  null, 2
).replace('"{{tenant_id}}"', '{{tenant_id}}').replace('"{{mobiles}}"', '{{mobiles}}')

const form = ref({
  api_url: '',
  api_method: 'POST',
  api_headers: {},
  body_template: '',
  interval_sec: 0.5,
  max_retry: 2,
  timeout: 15,
  per_batch: 1,
})
const headersText = ref('')
const savingConfig = ref(false)

function syncHeadersFromText() {
  try {
    form.value.api_headers = JSON.parse(headersText.value || '{}')
  } catch (e) {
    // 格式错误时保留原来的
  }
}

async function loadConfig() {
  try {
    const res = await getActivationConfig()
    const data = res.data || res
    // 兼容旧版 body_template: 把 {"tenant_id": "", ...} 自动替换成带占位符的新版
    let bt = data.body_template || ''
    if (bt.includes('"tenant_id": ""') && !bt.includes('{{tenant_id}}')) {
      bt = bt.replace('"tenant_id": ""', '"tenant_id": {{tenant_id}}')
      // 静默保存新版
      try { await saveActivationConfig({ ...data, body_template: bt }) } catch (e) {}
    }
    form.value = {
      api_url: data.api_url || '',
      api_method: data.api_method || 'POST',
      api_headers: data.api_headers || {},
      body_template: bt,
      interval_sec: data.interval_sec ?? 0.5,
      max_retry: data.max_retry ?? 2,
      timeout: data.timeout ?? 15,
      per_batch: 1,
    }
    headersText.value = JSON.stringify(form.value.api_headers || {}, null, 2)
  } catch (e) {
    console.error('[账号激活] 加载配置失败:', e)
  }
}

async function saveConfig() {
  syncHeadersFromText()
  savingConfig.value = true
  try {
    await saveActivationConfig({
      api_url: form.value.api_url,
      api_method: form.value.api_method,
      api_headers: form.value.api_headers,
      body_template: form.value.body_template,
      interval_sec: form.value.interval_sec,
      max_retry: form.value.max_retry,
      timeout: form.value.timeout,
    })
    ElMessage.success('配置已保存')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e?.response?.data?.error || e.message))
  } finally {
    savingConfig.value = false
  }
}

async function resetConfig() {
  try {
    const res = await resetActivationConfig()
    const data = res.data || res
    form.value = {
      api_url: data.api_url,
      api_method: data.api_method,
      api_headers: data.api_headers || {},
      body_template: data.body_template,
      interval_sec: data.interval_sec,
      max_retry: data.max_retry,
      timeout: data.timeout,
      per_batch: 1,
    }
    headersText.value = JSON.stringify(form.value.api_headers || {}, null, 2)
    ElMessage.success('已恢复默认配置')
  } catch (e) {
    ElMessage.error('恢复失败: ' + (e?.response?.data?.error || e.message))
  }
}

// ==================== 执行相关 ====================
const tenantPresets = [
  { label: '泳道1 - 资源租户', id: '1704384780671352833' },
  { label: '泳道2 - 38租户', id: '1630819861994663938' },
  { label: '泳道3 - 81租户', id: '1759923856565587969' },
  { label: '泳道4 - 69租户', id: '1759924268144250881' },
  { label: '泳道5 - 网院租户', id: '1759924268144250881' },
]
const tenantId = ref('')
const authorization = ref('')
const mobilesText = ref('')
const executing = ref(false)
const results = ref([])

const validMobiles = computed(() => {
  return mobilesText.value
    .split(/[\s,;，；\n]+/)
    .map(s => s.trim())
    .filter(s => s && /^1\d{10}$/.test(s))
})

const invalidMobiles = computed(() => {
  return mobilesText.value
    .split(/[\s,;，；\n]+/)
    .map(s => s.trim())
    .filter(s => s && !/^1\d{10}$/.test(s))
})

const canExecute = computed(() => {
  return tenantId.value.trim() && authorization.value.trim() && validMobiles.value.length > 0 && !executing.value
})

const totalCount = computed(() => results.value.length)
const successCount = computed(() => results.value.filter(r => r.status === 'SUCCESS').length)
const failCount = computed(() => results.value.filter(r => r.status !== 'SUCCESS').length)
const progressPercent = computed(() => {
  if (results.value.length === 0) return 0
  // 粗略估算
  const valid = validMobiles.value.length || results.value.length
  return Math.min(100, Math.round(results.value.length / valid * 100))
})

async function startBatchActivate() {
  if (!canExecute.value) return

  executing.value = true
  results.value = []
  const currentMobiles = [...validMobiles.value]

  try {
    const res = await batchActivate({
      authorization: authorization.value.trim(),
      tenant_id: tenantId.value.trim(),
      mobiles: currentMobiles,
      api_url: form.value.api_url,
      api_method: form.value.api_method,
      api_headers: form.value.api_headers,
      body_template: form.value.body_template,
      interval_sec: form.value.interval_sec,
      max_retry: form.value.max_retry,
      timeout: form.value.timeout,
      per_batch: form.value.per_batch,
    })

    const data = res.data || res
    results.value = data.results || []

    if (data.invalid_mobiles?.length) {
      ElMessage.warning(`有 ${data.invalid_mobiles.length} 个手机号格式非法已忽略`)
    }

    ElMessage.success(`执行完成！成功 ${data.success_count}，失败 ${data.fail_count}`)
    await loadHistory()
  } catch (e) {
    const msg = e?.response?.data?.error || e.message || '执行失败'
    ElMessage.error(msg)
    results.value = []
  } finally {
    executing.value = false
  }
}

function exportFailed() {
  const failed = results.value
    .filter(r => r.status !== 'SUCCESS')
    .map(r => r.mobile)
    .join('\n')
  if (!failed) return
  const blob = new Blob([failed], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `failed_mobiles_${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

// ==================== 手机号历史导入 ====================
const importDrawerVisible = ref(false)
const phoneHistoryLoading = ref(false)
const phoneHistoryList = ref([])
const selectedPhoneRecords = ref([])
const importTableRef = ref(null)

const totalImportMobiles = computed(() => {
  return selectedPhoneRecords.value.reduce((sum, r) => sum + (r.mobile_count || 0), 0)
})

async function importFromFactory() {
  importDrawerVisible.value = true
  selectedPhoneRecords.value = []
  await loadPhoneHistory()
}

async function loadPhoneHistory() {
  phoneHistoryLoading.value = true
  try {
    const res = await getPhoneHistory(50)
    const data = res.data || res
    phoneHistoryList.value = data.results || []
  } catch (e) {
    ElMessage.error('加载手机号历史失败')
  } finally {
    phoneHistoryLoading.value = false
  }
}

function handleSelectionChange(selection) {
  selectedPhoneRecords.value = selection
}

function confirmImport() {
  if (!selectedPhoneRecords.value.length) return

  const allMobiles = []
  selectedPhoneRecords.value.forEach(r => {
    if (r.mobiles && Array.isArray(r.mobiles)) {
      allMobiles.push(...r.mobiles)
    }
  })

  // 去重 + 去空
  const existing = new Set(
    mobilesText.value.split(/[\s,;，；\n]+/).map(s => s.trim()).filter(Boolean)
  )
  const newOnes = allMobiles.filter(m => m && !existing.has(m))

  if (newOnes.length === 0) {
    ElMessage.info('这些手机号已经在列表中了')
    importDrawerVisible.value = false
    return
  }

  // 追加到输入框
  if (mobilesText.value.trim()) {
    mobilesText.value = mobilesText.value.trim() + '\n' + newOnes.join('\n')
  } else {
    mobilesText.value = newOnes.join('\n')
  }

  ElMessage.success(`已导入 ${newOnes.length} 个手机号`)
  importDrawerVisible.value = false
}

// ==================== 激活历史 ====================
const historyExpanded = ref(true)
const historyLoading = ref(false)
const historyList = ref([])

async function loadHistory() {
  historyLoading.value = true
  try {
    // 延迟一点等日志写好
    await new Promise(r => setTimeout(r, 300))
    const res = await getActivationLogs(20)
    const data = res.data || res
    historyList.value = data.results || []
  } catch (e) {
    console.warn('[AccountActivation] 加载历史失败:', e)
  } finally {
    historyLoading.value = false
  }
}

// 日志详情抽屉
const logDetailVisible = ref(false)
const logDetailLoading = ref(false)
const logDetailData = ref(null)

async function openLogDetail(row) {
  logDetailVisible.value = true
  logDetailLoading.value = true
  logDetailData.value = null
  try {
    const res = await getActivationLogDetail(row.id)
    logDetailData.value = res.data || res
  } catch (e) {
    ElMessage.error('加载日志详情失败')
    console.warn('[AccountActivation] 加载日志详情失败:', e)
  } finally {
    logDetailLoading.value = false
  }
}

// ==================== 初始化 ====================
onMounted(async () => {
  await loadConfig()
  await loadHistory()
})
</script>

<style scoped>
.account-activation {
  padding: 24px;
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  min-height: calc(100vh - 64px);
}

/* 卡片通用 */
.execute-card,
.result-card,
.history-card {
  margin-bottom: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border-radius: 12px !important;
  border: 1px solid rgba(147, 112, 219, 0.12) !important;

  :deep(.el-card__header) {
    padding: 16px 20px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.08);
  }

  :deep(.el-card__body) {
    padding: 20px;
  }
}

.execute-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;

  .gen-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    border: none;
    font-weight: 600;
    padding: 8px 20px;
    font-size: 14px;
    transition: all 0.25s ease;
    box-shadow: 0 2px 8px rgba(123, 66, 246, 0.3);

    .el-icon {
      margin-right: 4px;
    }

    &:hover:not(:disabled) {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }

    &:active:not(:disabled) {
      transform: translateY(0);
    }

    &:disabled {
      background: #c0c4cc;
      border-color: #c0c4cc;
      box-shadow: none;
    }
  }

  .ghost-btn {
    color: #7b42f6;
    border-color: rgba(123, 66, 246, 0.4);
    background: rgba(123, 66, 246, 0.04);
    font-weight: 500;
    font-size: 14px;
    padding: 8px 20px;
    transition: all 0.25s ease;

    .el-icon {
      margin-right: 4px;
    }

    &:hover {
      color: #fff;
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      border-color: #7b42f6;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
    }

    &:active {
      transform: translateY(0);
    }
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-weight: 600;
  font-size: 15px;
  color: #3d2e6e;
}

.expand-icon {
  transition: transform 0.25s;
  color: #7b42f6;

  &.is-expanded {
    transform: rotate(180deg);
  }
}

.form-tip {
  color: #a79bc9;
  font-size: 12px;
  margin-top: 4px;
}

.inline-forms {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 24px;
}

.inline-item {
  display: flex;
  align-items: center;
  gap: 8px;

  .inline-label {
    color: #7b6fa8;
    font-size: 13px;
  }
}

.phone-input-wrapper {
  width: 100%;
}

.phone-input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.phone-count {
  color: #6d5f9f;
  font-size: 13px;

  b {
    color: #7b42f6;
    font-size: 15px;
    font-weight: 700;
  }

  .invalid-tip {
    color: #ef4444;
  }
}

.phone-actions {
  display: flex;
  gap: 8px;

  :deep(.el-button) {
    border-color: rgba(123, 66, 246, 0.3);
    color: #7b42f6;

    &:hover {
      background: rgba(123, 66, 246, 0.06);
      border-color: #7b42f6;
    }
  }
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.summary-cards {
  display: flex;
  gap: 12px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 72px;
  padding: 8px 14px;
  border-radius: 10px;
  background: rgba(123, 66, 246, 0.06);
  border: 1px solid rgba(123, 66, 246, 0.12);

  .num {
    font-size: 22px;
    font-weight: 700;
    line-height: 1.2;
  }

  .label {
    font-size: 12px;
    color: #9b8fc4;
    margin-top: 2px;
  }

  &.total {
    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
    border-color: rgba(123, 66, 246, 0.2);

    .num {
      color: #5a32a3;
    }
  }

  &.success {
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    border-color: rgba(34, 197, 94, 0.2);

    .num {
      color: #16a34a;
    }
  }

  &.fail {
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    border-color: rgba(239, 68, 68, 0.2);

    .num {
      color: #dc2626;
    }
  }
}

.mono {
  font-family: 'SF Mono', Consolas, Monaco, monospace;
  font-size: 12px;
  color: #5a32a3;
  background: rgba(123, 66, 246, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
}

.muted {
  color: #c4b5d9;
  font-size: 13px;
}

.msg-error {
  color: #ef4444;
}

.mobile-count-link {
  color: #7b42f6;
  cursor: pointer;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(123, 66, 246, 0.08);
    text-decoration: underline;
  }
}

.success-text {
  color: #16a34a;
  font-weight: 600;
}

.fail-text {
  color: #dc2626;
  font-weight: 600;
}

.result-footer {
  margin-top: 16px;
  text-align: right;
}

.empty-hint {
  text-align: center;
  padding: 40px 20px;
  color: #9b8fc4;

  p {
    margin: 10px 0 0;
  }

  .small {
    font-size: 12px;
  }
}

.drawer-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selection-info {
  font-size: 13px;
  color: #5a4d8f;

  b {
    color: #7b42f6;
    font-size: 15px;
    font-weight: 700;
  }
}

/* 进度条紫色主题 */
:deep(.el-progress-bar__outer) {
  background: rgba(123, 66, 246, 0.12);
  border-radius: 10px;
}

:deep(.el-progress-bar__inner) {
  background: linear-gradient(90deg, #7b42f6 0%, #9f7aea 100%);
  border-radius: 10px;
}

/* 表格主题色 */
:deep(.el-table) {
  --el-table-header-bg-color: rgba(123, 66, 246, 0.04);
  --el-table-tr-bg-color: #faf9ff;
}

:deep(.el-table th.el-table__cell) {
  color: #5a32a3;
  font-weight: 600;
}

:deep(.el-table tbody tr:hover > td) {
  background-color: rgba(123, 66, 246, 0.04) !important;
}

/* 输入框聚焦 */
:deep(.el-input__wrapper.is-focus),
:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #7b42f6 inset !important;
}

:deep(.el-textarea__inner:focus) {
  border-color: #7b42f6 !important;
}

/* Select */
:deep(.el-select__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #7b42f6 inset !important;
}
</style>
