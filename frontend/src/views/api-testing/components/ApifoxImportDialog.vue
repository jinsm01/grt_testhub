<template>
  <el-drawer
    v-model="visible"
    :title="$t('apiTesting.apifox.importTitle')"
    size="800px"
    :close-on-click-modal="false"
    direction="rtl"
    destroy-on-close
  >
    <div class="import-container">
      <!-- 导入结果展示 -->
      <div v-if="importStatus" class="step-content">
        <el-result
          v-if="importStatus === 'importing'"
          icon="info"
          :title="$t('apiTesting.apifox.importing')"
        >
          <template #extra>
            <el-progress :percentage="importProgress" />
          </template>
        </el-result>

        <template v-else-if="importStatus === 'success'">
          <div class="import-success-container">


            <!-- 导入的接口列表 -->
            <div class="imported-requests-section">
              <div class="section-header">
                <span class="section-title">{{ importResult.collection_name || '导入的接口' }}</span>
                <span class="section-count">共 {{ importResult.imported_requests }} 个</span>
              </div>
              <div class="requests-list">
                <template v-for="(item, index) in importResult.imported_requests_list" :key="index">
                  <!-- 分组 -->
                  <div v-if="item.type === 'group'" class="request-group">
                    <div class="group-header">
                      <el-icon><Folder /></el-icon>
                      <span class="group-name">{{ item.name }}</span>
                      <span class="group-count">({{ getGroupRequestCount(item) }} 个接口)</span>
                    </div>
                    <div class="group-children">
                      <div
                        v-for="(child, childIndex) in item.children"
                        :key="childIndex"
                        class="request-item"
                      >
                        <span class="method-tag" :class="child.method?.toLowerCase()">{{ child.method }}</span>
                        <span class="request-name">{{ child.name }}</span>
                        <span class="request-url">{{ child.url }}</span>
                      </div>
                    </div>
                  </div>
                  <!-- 单个请求 -->
                  <div
                    v-else
                    class="request-item"
                  >
                    <span class="method-tag" :class="item.method?.toLowerCase()">{{ item.method }}</span>
                    <span class="request-name">{{ item.name }}</span>
                    <span class="request-url">{{ item.url }}</span>
                  </div>
                </template>
              </div>
            </div>

          </div>
        </template>

        <el-result
          v-else-if="importStatus === 'error'"
          icon="error"
          :title="$t('apiTesting.apifox.importError')"
          :sub-title="importError"
        />
      </div>

      <!-- 上传和配置合并页面 -->
      <div v-else class="step-content">
        <!-- 上传区域 -->
        <div class="upload-section">
          <!-- 未上传文件时显示上传区域 -->
          <template v-if="!selectedFile">
            <el-upload
              ref="uploadRef"
              class="apifox-uploader"
              drag
              action="#"
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :limit="1"
              accept=".json"
            >
              <el-icon class="upload-icon"><upload-filled /></el-icon>
              <div class="upload-text">
                <span class="primary-text">{{ $t('apiTesting.apifox.dragText') }}</span>
                <span class="secondary-text">{{ $t('apiTesting.apifox.supportFormat') }}</span>
              </div>
            </el-upload>
          </template>

          <!-- 验证中状态 -->
          <div v-else-if="validationStatus === 'validating'" class="status-section">
            <el-progress :percentage="validationProgress" :indeterminate="true" status="exception" />
            <p class="status-text">{{ $t('apiTesting.apifox.validating') }}</p>
          </div>

          <!-- 验证成功 - 显示文件信息 -->
          <template v-else-if="validationStatus === 'success' || validationStatus === 'warning'">
            <div class="file-info-card">
              <div class="file-info-header">
                <el-icon class="file-icon"><document /></el-icon>
                <div class="file-info-content">
                  <span class="file-name">{{ selectedFile?.name }}</span>
                  <span class="file-meta">
                    共 {{ validationResult.total_requests }} 个请求
                    <template v-if="validationResult.scenario_name">
                      · 场景名称: {{ validationResult.scenario_name }}
                    </template>
                  </span>
                </div>
                <el-button link type="danger" size="small" @click="handleFileRemove">
                  {{ $t('common.delete') }}
                </el-button>
              </div>
            </div>

            <!-- 同名合集提示 -->
            <el-alert
              v-if="validationResult.scenario_name && !importConfig.collectionId"
              :title="collectionAlertTitle"
              type="info"
              :closable="false"
              show-icon
              class="info-alert"
              style="margin-bottom: 16px;"
            >
              <span>系统将自动创建此合集；如选择导入到已有合集，将会覆盖原合集中的接口</span>
            </el-alert>

            <!-- 重复合集警告 -->
            <el-alert
              v-if="validationResult.existing_collection && !importConfig.collectionId"
              :title="`检测到同名合集`"
              type="warning"
              :closable="false"
              show-icon
              class="warning-alert"
              style="margin-bottom: 16px;"
            >
              <div class="duplicate-collection-info">
                <p>已存在名为 "{{ validationResult.existing_collection.name }}" 的合集</p>
                <p class="detail">包含 {{ validationResult.existing_collection.request_count }} 个接口 · 创建于 {{ validationResult.existing_collection.created_at }}</p>
                <p class="hint">导入时将覆盖该合集中的原有接口</p>
              </div>
            </el-alert>

            <!-- 警告信息 -->
            <el-alert
              v-if="validationStatus === 'warning' && validationResult.unsupported_functions?.length"
              :title="$t('apiTesting.apifox.unsupportedFunctions')"
              type="warning"
              :closable="false"
              class="warning-alert"
            >
              <div class="unsupported-list">
                <el-tag
                  v-for="func in validationResult.unsupported_functions"
                  :key="func"
                  type="danger"
                  size="small"
                >
                  {{ func }}
                </el-tag>
              </div>
            </el-alert>
          </template>

          <!-- 验证错误 -->
          <el-result
            v-else-if="validationStatus === 'error'"
            icon="error"
            :title="$t('apiTesting.apifox.validationError')"
            :sub-title="validationError"
          />
        </div>

        <!-- 配置表单（验证成功后显示） -->
        <template v-if="(validationStatus === 'success' || validationStatus === 'warning') && selectedFile">
          <el-divider />
          <el-form :model="importConfig" label-position="top" class="import-form">
            <el-form-item :label="$t('apiTesting.apifox.labels.targetProject')" required>
              <el-select
                v-model="importConfig.projectId"
                :placeholder="$t('apiTesting.apifox.placeholders.selectProject')"
                @change="handleProjectChange"
                class="full-width"
              >
                <el-option
                  v-for="project in projectList"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item :label="$t('apiTesting.apifox.labels.targetCollection')">
              <el-select
                v-model="importConfig.collectionId"
                :placeholder="$t('apiTesting.apifox.placeholders.selectCollection')"
                clearable
                class="full-width"
              >
                <el-option
                  v-for="collection in collectionList"
                  :key="collection.id"
                  :label="collection.name"
                  :value="collection.id"
                />
              </el-select>
              <div class="form-hint">{{ $t('apiTesting.apifox.hints.newCollectionIfEmpty') }}</div>
            </el-form-item>
          </el-form>
        </template>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel">{{ $t('common.cancel') }}</el-button>
        <el-button
          v-if="!importStatus && (validationStatus === 'success' || validationStatus === 'warning')"
          type="primary"
          @click="handleImport"
          :loading="processing"
          :disabled="!importConfig.projectId"
        >
          {{ $t('apiTesting.apifox.buttons.startImport') }}
        </el-button>
        <el-button v-if="importStatus === 'success'" type="primary" @click="handleFinish">
          {{ $t('common.finish') }}
        </el-button>
        <el-button v-if="importStatus === 'error'" type="primary" @click="handleRetry">
          {{ $t('common.retry') }}
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, CircleCheckFilled, Document, WarningFilled, InfoFilled } from '@element-plus/icons-vue'
import api from '@/utils/api'

const { t } = useI18n()
const router = useRouter()

const props = defineProps({
  modelValue: Boolean,
  projects: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 合集提示标题
const collectionAlertTitle = computed(() => {
  const name = validationResult.value.scenario_name
  return name ? `将创建/导入到名为 "${name}" 的合集` : '导入合集'
})

// 步骤控制 (0: 配置, 1: 结果) - 保留变量但不再使用步骤切换
const processing = ref(false)

// 文件上传
const uploadRef = ref(null)
const selectedFile = ref(null)

// 验证状态
const validationStatus = ref('')
const validationProgress = ref(0)
const validationResult = ref({
  valid: false,
  unsupported_functions: [],
  total_requests: 0,
  warnings: [],
  scenario_name: '',
  existing_collection: null
})
const validationError = ref('')

// 导入配置
const importConfig = ref({
  projectId: '',
  collectionId: '',
  importEnv: false
})

// 数据列表
const projectList = ref([])
const collectionList = ref([])

// 导入状态
const importStatus = ref('')
const importProgress = ref(0)
const importResult = ref({
  collection_id: null,
  collection_name: '',
  suite_id: null,
  suite_name: '',
  imported_requests: 0,
  import_time: '',
  warnings: [],
  issues_by_request: {},
  imported_requests_list: []
})
const importError = ref('')

// 监听对话框打开
watch(() => props.modelValue, (val) => {
  if (val) {
    resetState()
    loadProjects()
  }
})

watch(() => props.projects, (val) => {
  projectList.value = val
}, { immediate: true })

// 方法
const resetState = () => {
  selectedFile.value = null
  validationStatus.value = ''
  validationProgress.value = 0
  validationResult.value = { valid: false, unsupported_functions: [], total_requests: 0, warnings: [], scenario_name: '', existing_collection: null }
  validationError.value = ''
  importConfig.value = { projectId: '', collectionId: '', importEnv: false }
  collectionList.value = []
  importStatus.value = ''
  importProgress.value = 0
  importResult.value = { collection_id: null, collection_name: '', suite_id: null, suite_name: '', imported_requests: 0, import_time: '', warnings: [], issues_by_request: {}, imported_requests_list: [] }
  importError.value = ''

  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

const loadProjects = async () => {
  try {
    const response = await api.get('/api-testing/projects/')
    projectList.value = response.data.results || []
  } catch (error) {
    console.error('加载项目列表失败:', error)
  }
}

const handleFileChange = (file) => {
  selectedFile.value = file
  // 自动开始验证
  if (file) {
    setTimeout(() => {
      validateFile()
    }, 300)
  }
}

const handleFileRemove = () => {
  selectedFile.value = null
  validationStatus.value = ''
  validationResult.value = { valid: false, unsupported_functions: [], total_requests: 0, warnings: [], scenario_name: '', existing_collection: null }
}

const handleProjectChange = async (projectId) => {
  importConfig.value.collectionId = ''
  if (!projectId) {
    collectionList.value = []
    return
  }

  try {
    const response = await api.get(`/api-testing/collections/?project=${projectId}`)
    collectionList.value = response.data.results || []
  } catch (error) {
    console.error('加载集合列表失败:', error)
    collectionList.value = []
  }

  // 如果已经上传了文件，重新验证以检测重复合集
  if (selectedFile.value && validationStatus.value === 'success' || validationStatus.value === 'warning') {
    validateFile()
  }
}

const validateFile = async () => {
  if (!selectedFile.value) {
    ElMessage.warning(t('apiTesting.apifox.messages.selectFile'))
    return false
  }

  processing.value = true
  validationStatus.value = 'validating'
  validationProgress.value = 0

  const formData = new FormData()
  formData.append('file', selectedFile.value.raw)
  if (importConfig.value.projectId) {
    formData.append('project_id', importConfig.value.projectId)
  }

  try {
    const response = await api.post('/api-testing/apifox/v2/validate/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        validationProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      }
    })

    validationResult.value = response.data

    if (response.data.unsupported_functions?.length > 0) {
      validationStatus.value = 'warning'
    } else {
      validationStatus.value = 'success'
    }

    return true
  } catch (error) {
    validationStatus.value = 'error'
    validationError.value = error.response?.data?.error || error.message
    ElMessage.error(t('apiTesting.apifox.messages.validationFailed'))
    return false
  } finally {
    processing.value = false
  }
}

// 检查是否存在同名合集
const checkDuplicateCollection = async (projectId, scenarioName) => {
  if (!projectId || !scenarioName) return null
  try {
    const response = await api.get(`/api-testing/collections/?project=${projectId}`)
    const collections = response.data.results || []
    // 检查是否有同名合集（忽略大小写）
    return collections.find(c =>
      c.name?.toLowerCase() === scenarioName?.toLowerCase()
    )
  } catch (error) {
    console.error('检查合集失败:', error)
    return null
  }
}

const handleImport = async () => {
  if (!importConfig.value.projectId) {
    ElMessage.warning(t('apiTesting.apifox.messages.selectProject'))
    return
  }

  // 如果没有选择目标合集，检查验证结果中是否返回了同名合集
  if (!importConfig.value.collectionId && validationResult.value.existing_collection) {
    const existing = validationResult.value.existing_collection
    try {
      await ElMessageBox.confirm(
        `该项目下已存在名为 "${existing.name}" 的合集（包含 ${existing.request_count} 个接口），导入将会覆盖合集中的原有接口，是否继续？`,
        '覆盖确认',
        {
          confirmButtonText: '覆盖导入',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      // 用户确认，使用现有合集
      importConfig.value.collectionId = existing.id
    } catch {
      // 用户取消
      return
    }
  }

  processing.value = true
  importStatus.value = 'importing'
  importProgress.value = 0

  const formData = new FormData()
  formData.append('file', selectedFile.value.raw)
  formData.append('project_id', importConfig.value.projectId)
  if (importConfig.value.collectionId) {
    formData.append('target_collection_id', importConfig.value.collectionId)
  }
  formData.append('import_env', String(importConfig.value.importEnv))

  const startTime = Date.now()

  try {
    const response = await api.post('/api-testing/apifox/import-v2/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        importProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      }
    })

    const endTime = Date.now()

    importResult.value = {
      ...response.data,
      import_time: `${((endTime - startTime) / 1000).toFixed(2)}s`,
      imported_requests: response.data.stats?.requests_created || 0,
      collection_name: response.data.collection_name || t('apiTesting.apifox.defaultCollectionName'),
      suite_name: response.data.suite_name || t('apiTesting.apifox.defaultSuiteName'),
      warnings: response.data.warnings || [],
      imported_requests_list: response.data.imported_requests || []
    }

    importStatus.value = 'success'
    emit('success', response.data)
  } catch (error) {
    importStatus.value = 'error'
    importError.value = error.response?.data?.error || error.message
    ElMessage.error(t('apiTesting.apifox.messages.importFailed'))
  } finally {
    processing.value = false
  }
}

const handleCancel = () => {
  if (importStatus.value === 'importing') {
    ElMessageBox.confirm(
      t('apiTesting.apifox.messages.confirmCancel'),
      t('common.warning'),
      { confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel'), type: 'warning' }
    ).then(() => {
      visible.value = false
    })
  } else {
    visible.value = false
  }
}

const handleFinish = () => {
  visible.value = false
}

const handleRetry = () => {
  importStatus.value = ''
  // 重新尝试导入
  handleImport()
}

const navigateToCollection = () => {
  if (importResult.value.collection_id) {
    router.push(`/api-testing/collections/${importResult.value.collection_id}`)
    visible.value = false
  }
}

const navigateToSuite = () => {
  if (importResult.value.suite_id) {
    router.push(`/api-testing/test-suites/${importResult.value.suite_id}`)
    visible.value = false
  }
}

// 计算分组中的请求数量
const getGroupRequestCount = (group) => {
  if (!group.children) return 0
  let count = 0
  for (const child of group.children) {
    if (child.type === 'request') {
      count++
    } else if (child.type === 'group' && child.children) {
      count += getGroupRequestCount(child)
    }
  }
  return count
}

// 跳转到请求详情
const navigateToRequest = (request) => {
  if (request && request.id) {
    router.push(`/api-testing/requests/${request.id}`)
    visible.value = false
  }
}
</script>

<style lang="scss" scoped>
:deep(.el-drawer__body) {
  padding: 20px;
  overflow-y: auto;
}

:deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
}

:deep(.el-drawer__footer) {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
}

.import-container {
  min-height: auto;
}

.step-content {
  padding: 10px 0;
}

// 上传区域
.upload-section {
  margin-bottom: 0;
}

.apifox-uploader {
  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    width: 100%;
    height: 160px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background-color: #faf5ff;
    border: 2px dashed #d4a5ff;
    border-radius: 8px;
    transition: all 0.3s;

    &:hover {
      border-color: #7B2FF7;
      background-color: #f3e8ff;
    }
  }
}

.upload-icon {
  font-size: 40px;
  color: #7B2FF7;
  margin-bottom: 12px;
}

.upload-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;

  .primary-text {
    font-size: 15px;
    color: #303133;
  }

  .secondary-text {
    font-size: 12px;
    color: #909399;
  }
}

// 状态区域
.status-section {
  margin-top: 20px;
  text-align: center;

  .status-text {
    margin-top: 10px;
    color: #606266;
    font-size: 14px;
  }
}

// 文件信息卡片
.file-info-card {
  background-color: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;

  .file-info-header {
    display: flex;
    align-items: center;
    gap: 12px;

    .file-icon {
      font-size: 32px;
      color: #7B2FF7;
    }

    .file-info-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 4px;

      .file-name {
        font-size: 14px;
        font-weight: 500;
        color: #303133;
        word-break: break-all;
      }

      .file-meta {
        font-size: 12px;
        color: #67c23a;
      }
    }
  }
}

.info-alert {
  margin-bottom: 16px;
  border-radius: 6px;

  :deep(.el-alert__title) {
    font-size: 13px;
    font-weight: 500;
    line-height: 1.5;
  }

  :deep(.el-alert__description) {
    font-size: 12px;
    line-height: 1.6;
    margin-top: 4px;
  }

  :deep(.el-alert__icon) {
    font-size: 16px;
  }
}

.warning-alert {
  margin-bottom: 16px;
}

.unsupported-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.duplicate-collection-info {
  p {
    margin: 4px 0;
    font-size: 13px;
    color: #606266;

    &.detail {
      font-size: 12px;
      color: #909399;
    }

    &.hint {
      font-size: 12px;
      color: #e6a23c;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px dashed #e4e7ed;
    }
  }
}

// 表单样式
.import-form {
  margin: 16px 0;
}

.full-width {
  width: 100%;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

// 导入成功页面样式
.import-success-container {
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: calc(100vh - 180px);

  // 单行状态栏
  .success-status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(135deg, #f6ffed 0%, #e6f7d9 100%);
    border: 1px solid #b7eb8f;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(82, 196, 26, 0.1);

    .status-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .status-icon-wrapper {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 6px rgba(82, 196, 26, 0.3);
      }

      .status-text {
        font-size: 16px;
        font-weight: 600;
        color: #52c41a;
      }
    }

    .status-right {
      display: flex;
      align-items: baseline;
      gap: 6px;

      .requests-label {
        font-size: 13px;
        color: #606266;
      }

      .requests-count {
        font-size: 24px;
        font-weight: 700;
        color: #52c41a;
        line-height: 1;
      }
    }
  }

  // 导入详情卡片
  .success-details {
    .detail-card {
      background: #fafafa;
      border-radius: 12px;
      padding: 20px;
      border: 1px solid #f0f0f0;

      .detail-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;

        &:last-child {
          border-bottom: none;
          padding-bottom: 0;
        }

        &:first-child {
          padding-top: 0;
        }

        .detail-label {
          font-size: 13px;
          color: #909399;
          font-weight: 400;
        }

        .detail-value {
          font-size: 14px;
          color: #303133;
          font-weight: 500;
          max-width: 60%;
          text-align: right;
          word-break: break-all;
        }
      }
    }
  }

  // 导入的接口列表样式
  .imported-requests-section {
    background: #ffffff;
    border-radius: 12px;
    overflow: hidden;
    flex: 1;
    display: flex;
    flex-direction: column;

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
      flex-shrink: 0;

      .section-title {
        font-size: 15px;
        font-weight: 600;
        color: #1a1a2e;
      }

      .section-count {
        font-size: 13px;
        color: #7b42f6;
        font-weight: 500;
        background: rgba(123, 66, 246, 0.1);
        padding: 4px 12px;
        border-radius: 12px;
      }
    }

    .requests-list {
      flex: 1;
      overflow-y: auto;
      padding: 12px;

      // 分组样式
      .request-group {
        margin-bottom: 12px;

        &:last-child {
          margin-bottom: 0;
        }

        .group-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
          border-radius: 8px;
          margin-bottom: 6px;

          .el-icon {
            color: #f59e0b;
            font-size: 16px;
          }

          .group-name {
            font-size: 14px;
            font-weight: 600;
            color: #92400e;
          }

          .group-count {
            font-size: 12px;
            color: #d97706;
            margin-left: auto;
            background: rgba(245, 158, 11, 0.15);
            padding: 2px 8px;
            border-radius: 10px;
          }
        }

        .group-children {
          padding-left: 12px;
        }
      }

      // 请求项样式
      .request-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        background: #fafafa;
        border-radius: 8px;
        margin-bottom: 4px;

        &:last-child {
          margin-bottom: 0;
        }

        .method-tag {
          font-size: 10px;
          padding: 2px 6px;
          border-radius: 4px;
          color: white;
          font-weight: 700;
          letter-spacing: 0.5px;
          text-transform: uppercase;
          flex-shrink: 0;
          min-width: 40px;
          text-align: center;

          &.get { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); }
          &.post { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
          &.put { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
          &.delete { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
          &.patch { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
        }

        .request-name {
          font-size: 14px;
          font-weight: 500;
          color: #1e293b;
          flex: 0 0 auto;
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .request-url {
          font-size: 12px;
          color: #64748b;
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-family: 'Monaco', 'Menlo', monospace;
        }
      }
    }
  }

  // 保留旧样式兼容
  .success-header {
    text-align: center;
    margin-bottom: 32px;

    .success-icon {
      margin-bottom: 16px;

      :deep(.el-icon) {
        font-size: 64px;
      }
    }

    .success-title {
      font-size: 20px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 8px;
    }

    .success-desc {
      font-size: 14px;
      color: #909399;
      margin: 0;
    }
  }

  .success-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 24px;

    .stat-card {
      background: #f5f7fa;
      border-radius: 8px;
      padding: 16px;
      text-align: center;

      .stat-label {
        font-size: 12px;
        color: #909399;
        margin-bottom: 8px;
      }

      .stat-value {
        font-size: 14px;
        font-weight: 500;
        color: #303133;
      }
    }
  }
}

// 旧的结果样式（保留兼容）
.result-descriptions {
  margin-bottom: 16px;
}

// 底部按钮
.dialog-footer {
  display: flex;
  justify-content: flex-start;
  gap: 2px;
}
</style>
