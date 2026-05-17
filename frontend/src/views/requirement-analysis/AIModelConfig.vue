<template>
  <div class="page-container">
    <div class="page-header-card">
      <div class="page-header-content">
        <h1>配置用例生成、用例评审时的模型参数</h1>
      </div>
      <el-button type="primary" class="create-btn" @click="openAddModal">
        <el-icon><Plus /></el-icon>
        {{ $t('configuration.aiModel.addConfig') }}
      </el-button>
    </div>

    <div class="card-container">
      <el-table :data="configs" v-loading="loading" stripe style="width: 100%">
        <el-table-column type="index" label="序号" width="60" header-align="center" align="center" />
        <el-table-column :label="$t('configuration.aiModel.configName')" min-width="180" show-overflow-tooltip header-align="center" align="left">
          <template #default="{ row }">
            <div class="config-name-cell">{{ row.name || $t('configuration.common.unnamed') }}</div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('configuration.aiModel.modelType')" width="110" header-align="center" align="center">
          <template #default="{ row }">
            <span class="model-badge" :class="row.model_type">
              {{ $t('configuration.aiModel.modelTypes.' + row.model_type) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('configuration.aiModel.role')" width="180" header-align="center" align="center">
          <template #default="{ row }">
            <span class="role-badge" :class="row.role">
              {{ $t('configuration.aiModel.roles.' + row.role) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('configuration.aiModel.modelName')" min-width="240" show-overflow-tooltip header-align="center" align="center">
          <template #default="{ row }">
            <span class="model-name">{{ row.model_name }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('configuration.common.status')" width="90" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="{ active: row.is_active }">
              {{ row.is_active ? $t('configuration.common.enabled') : $t('configuration.common.disabled') }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('configuration.common.operation')" width="280" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" class="action-btn test-btn" @click="testConnection(row)" :disabled="isTestingConnection">
                <el-icon><Connection /></el-icon>
                <span>测试连接</span>
              </el-button>
              <el-button size="small" type="primary" class="action-btn edit-btn" @click="editConfig(row)">
                <el-icon><Edit /></el-icon>
                <span>编辑</span>
              </el-button>
              <el-button size="small" type="danger" class="action-btn delete-btn" @click="deleteConfig(row.id)">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="configs.length === 0" class="empty-state">
        <div class="empty-icon">🤖</div>
        <h3>{{ $t('configuration.aiModel.emptyTitle') }}</h3>
        <p>{{ $t('configuration.aiModel.emptyDescription') }}</p>
        <el-button type="primary" class="add-first-config-btn" @click="openAddModal">
          {{ $t('configuration.aiModel.addFirstConfig') }}
        </el-button>
      </div>
    </div>

    <el-dialog v-model="showModal" :title="isEditing ? $t('configuration.aiModel.editConfig') : $t('configuration.aiModel.addConfigTitle')" width="600px" :close-on-click-modal="false" class="config-dialog">
      <el-form :model="configForm" ref="configFormRef" label-width="110px" class="config-form">
        <el-form-item :class="{ 'is-error': formErrors.name }">
          <template #label>
            <span>{{ $t('configuration.aiModel.configName') }}</span><span class="required-star">*</span>
          </template>
          <el-input v-model="configForm.name" :placeholder="$t('configuration.aiModel.configNamePlaceholder')" />
          <div v-if="formErrors.name" class="error-message">{{ formErrors.name }}</div>
        </el-form-item>
        <el-form-item :class="{ 'is-error': formErrors.model_type }">
          <template #label>
            <span>{{ $t('configuration.aiModel.modelType') }}</span><span class="required-star">*</span>
          </template>
          <el-select v-model="configForm.model_type" :placeholder="$t('configuration.aiModel.selectModelType')" style="width: 100%" @change="onModelTypeChange(configForm.model_type)">
            <el-option value="deepseek" :label="$t('configuration.aiModel.modelTypes.deepseek')" />
            <el-option value="qwen" :label="$t('configuration.aiModel.modelTypes.qwen')" />
            <el-option value="siliconflow" :label="$t('configuration.aiModel.modelTypes.siliconflow')" />
            <el-option value="zhipu" :label="$t('configuration.aiModel.modelTypes.zhipu')" />
            <el-option value="other" :label="$t('configuration.aiModel.modelTypes.other')" />
          </el-select>
          <div v-if="formErrors.model_type" class="error-message">{{ formErrors.model_type }}</div>
        </el-form-item>
        <el-form-item :class="{ 'is-error': formErrors.role }">
          <template #label>
            <span>{{ $t('configuration.aiModel.role') }}</span><span class="required-star">*</span>
          </template>
          <el-select v-model="configForm.role" :placeholder="$t('configuration.aiModel.selectRole')" style="width: 100%">
            <el-option value="writer" :label="$t('configuration.aiModel.roles.writer')" />
            <el-option value="reviewer" :label="$t('configuration.aiModel.roles.reviewer')" />
            <el-option value="knowledge_base" :label="$t('configuration.aiModel.roles.knowledge_base')" />
            <el-option value="bug_analyzer" :label="$t('configuration.aiModel.roles.bug_analyzer')" />
            <el-option value="assertion_generator" :label="$t('configuration.aiModel.roles.assertion_generator')" />
            <el-option value="scene_generator" :label="$t('configuration.aiModel.roles.scene_generator')" />
          </el-select>
          <div v-if="formErrors.role" class="error-message">{{ formErrors.role }}</div>
        </el-form-item>
        <el-form-item :class="{ 'is-error': formErrors.api_key }">
          <template #label>
            <span>API Key</span><span class="required-star">*</span>
          </template>
          <el-input v-model="configForm.api_key" type="password" show-password :placeholder="isEditing ? $t('configuration.aiModel.apiKeyPlaceholderEdit') : $t('configuration.aiModel.apiKeyPlaceholder')" :required="!isEditing" />
          <div v-if="formErrors.api_key" class="error-message">{{ formErrors.api_key }}</div>
          <div v-if="isEditing && configForm.api_key && configForm.api_key.includes('*')" class="form-hint">
            {{ $t('configuration.aiModel.apiKeyMaskHint') }}
          </div>
        </el-form-item>
        <el-form-item :class="{ 'is-error': formErrors.base_url }">
          <template #label>
            <span style="white-space: nowrap">API Base URL</span><span class="required-star">*</span>
          </template>
          <el-input v-model="configForm.base_url" :placeholder="$t('configuration.aiModel.baseUrlPlaceholder')" />
          <div v-if="formErrors.base_url" class="error-message">{{ formErrors.base_url }}</div>
        </el-form-item>
        <el-form-item :class="{ 'is-error': formErrors.model_name }">
          <template #label>
            <span>{{ $t('configuration.aiModel.modelName') }}</span><span class="required-star">*</span>
          </template>
          <el-input v-model="configForm.model_name" :placeholder="$t('configuration.aiModel.modelNamePlaceholder')" />
          <div v-if="formErrors.model_name" class="error-message">{{ formErrors.model_name }}</div>
        </el-form-item>
        <el-form-item :label="$t('configuration.aiModel.maxTokens')">
          <el-input v-model.number="configForm.max_tokens" type="number" :min="100" :max="32000" :step="100" style="width: 200px" />
        </el-form-item>
        <el-form-item :label="$t('configuration.aiModel.temperature')">
          <el-input v-model.number="configForm.temperature" type="number" :min="0" :max="2" :step="0.1" style="width: 200px" />
        </el-form-item>
        <el-form-item :label="$t('configuration.aiModel.topP')">
          <el-input v-model.number="configForm.top_p" type="number" :min="0" :max="1" :step="0.1" style="width: 200px" />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="configForm.is_active">
            {{ $t('configuration.aiModel.enableConfig') }}
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button class="cancel-btn" @click="closeModals">{{ $t('configuration.common.cancel') }}</el-button>
          <el-button type="primary" class="save-btn" @click="saveConfig" :loading="isSaving">
            {{ $t('configuration.aiModel.saveConfig') }}</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="showTestResult" :title="$t('configuration.aiModel.testResult')" width="520px" class="test-result-dialog">
      <div class="test-result" :class="{ success: testResult.success, error: !testResult.success }">
        <div class="result-icon">
          <el-icon v-if="testResult.success" :size="32" color="#ffffff"><CircleCheckFilled /></el-icon>
          <el-icon v-else :size="32" color="#ffffff"><CircleCloseFilled /></el-icon>
        </div>
        <div class="result-content">
          <h4>{{ testResult.success ? $t('configuration.aiModel.connectionSuccess') : $t('configuration.aiModel.connectionFailed') }}</h4>
          <p v-if="!testResult.success">{{ testResult.message }}</p>
          <div v-if="testResult.response" class="api-response">
            <label>{{ $t('configuration.aiModel.aiResponse') }}</label>
            <p>{{ testResult.response }}</p>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { Plus, Connection, Edit, Delete, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'

export default {
  name: 'AIModelConfig',
  components: {
    Plus,
    Connection,
    Edit,
    Delete,
    CircleCheckFilled,
    CircleCloseFilled
  },
  setup() {
    const { t } = useI18n()
    return { t }
  },
  data() {
    return {
      configs: [],
      loading: false,
      showModal: false,
      showTestResult: false,
      isEditing: false,
      isSaving: false,
      isTestingConnection: false,
      testingConfigId: null,
      editingConfigId: null,
      configForm: {
        name: '',
        model_type: '',
        role: '',
        api_key: '',
        base_url: '',
        model_name: '',
        max_tokens: 4096,
        temperature: 0.7,
        top_p: 0.9,
        is_active: true
      },
      formErrors: {
        name: '',
        model_type: '',
        role: '',
        api_key: '',
        base_url: '',
        model_name: ''
      },
      modelBaseUrlMap: {
        deepseek: 'https://api.deepseek.com',
        qwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        siliconflow: 'https://api.siliconflow.cn/v1',
        zhipu: 'https://open.bigmodel.cn/api/paas/v4',
        other: ''
      },
      testResult: {
        success: false,
        message: '',
        response: ''
      }
    }
  },

  mounted() {
    this.initializeComponent()
    this.loadConfigs()
  },
  methods: {
    onModelTypeChange(modelType) {
      if (this.modelBaseUrlMap[modelType]) {
        this.configForm.base_url = this.modelBaseUrlMap[modelType]
      }
    },
    initializeComponent() {
      this.showModal = false
      this.showTestResult = false
      this.isEditing = false
      this.isSaving = false
      this.isTestingConnection = false
      this.testingConfigId = null
      this.editingConfigId = null
    },
    async loadConfigs() {
      this.loading = true
      try {
        const response = await api.get('/requirement-analysis/ai-models/')
        if (response.data && response.data.results && Array.isArray(response.data.results)) {
          this.configs = response.data.results.filter(config => config && config.id)
        } else if (response.data && Array.isArray(response.data)) {
          this.configs = response.data.filter(config => config && config.id)
        } else {
          this.configs = []
        }
      } catch (error) {
        console.error('Failed to load configs:', error)
        this.configs = []
        if (error.response?.status === 401) {
          ElMessage.error(this.t('configuration.aiModel.messages.pleaseLogin'))
        } else {
          ElMessage.error(this.t('configuration.aiModel.messages.loadFailedDetail', { error: error.response?.data?.error || error.message }))
        }
      } finally {
        this.loading = false
      }
    },
    openAddModal() {
      this.resetForm()
      this.clearFormErrors()
      this.isEditing = false
      this.showModal = true
    },
    resetForm() {
      Object.assign(this.configForm, {
        name: '',
        model_type: '',
        role: '',
        api_key: '',
        base_url: '',
        model_name: '',
        max_tokens: 4096,
        temperature: 0.7,
        top_p: 0.9,
        is_active: true
      })
    },
    editConfig(config) {
      this.isEditing = true
      this.editingConfigId = config.id
      Object.assign(this.configForm, {
        name: config.name,
        model_type: config.model_type,
        role: config.role,
        api_key: config.api_key_masked || '',
        base_url: config.base_url,
        model_name: config.model_name,
        max_tokens: config.max_tokens,
        temperature: config.temperature,
        top_p: config.top_p,
        is_active: config.is_active
      })
      this.clearFormErrors()
      this.showModal = true
    },
    clearFormErrors() {
      this.formErrors = {
        name: '',
        model_type: '',
        role: '',
        api_key: '',
        base_url: '',
        model_name: ''
      }
    },
    validateForm() {
      this.clearFormErrors()
      let isValid = true

      const fieldNames = {
        name: this.$t('configuration.aiModel.configName'),
        model_type: this.$t('configuration.aiModel.modelType'),
        role: this.$t('configuration.aiModel.role'),
        api_key: 'API Key',
        base_url: 'API Base URL',
        model_name: this.$t('configuration.aiModel.modelName')
      }

      if (!this.configForm.name || this.configForm.name.trim() === '') {
        this.formErrors.name = `请输入${fieldNames.name}`
        isValid = false
      }
      if (!this.configForm.model_type) {
        this.formErrors.model_type = `请选择${fieldNames.model_type}`
        isValid = false
      }
      if (!this.configForm.role) {
        this.formErrors.role = `请选择${fieldNames.role}`
        isValid = false
      }
      if (!this.configForm.api_key || this.configForm.api_key.trim() === '') {
        this.formErrors.api_key = `请输入${fieldNames.api_key}`
        isValid = false
      }
      if (!this.configForm.base_url || this.configForm.base_url.trim() === '') {
        this.formErrors.base_url = `请输入${fieldNames.base_url}`
        isValid = false
      }
      if (!this.configForm.model_name || this.configForm.model_name.trim() === '') {
        this.formErrors.model_name = `请输入${fieldNames.model_name}`
        isValid = false
      }

      return isValid
    },
    async saveConfig() {
      if (!this.validateForm()) {
        return
      }
      
      if (!this.isEditing && this.configForm.is_active) {
        const existingConfig = this.configs.find(config => 
          config.model_type === this.configForm.model_type && 
          config.role === this.configForm.role && 
          config.is_active === true
        )
        
        if (existingConfig) {
          ElMessage.error(this.t('configuration.aiModel.messages.duplicateConfig', { name: existingConfig.name }))
          return
        }
      }
      
      this.isSaving = true
      
      try {
        if (this.isEditing) {
          const updateData = { ...this.configForm }
          if (!updateData.api_key || updateData.api_key.includes('*')) {
            delete updateData.api_key
          }
          await api.patch('/requirement-analysis/ai-models/' + this.editingConfigId + '/', updateData)
          ElMessage.success(this.t('configuration.aiModel.messages.updateSuccess'))
        } else {
          await api.post('/requirement-analysis/ai-models/', this.configForm)
          ElMessage.success(this.t('configuration.aiModel.messages.saveSuccess'))
        }
        
        this.closeModals()
        await this.$nextTick()
        await this.loadConfigs()
        this.$forceUpdate()
      } catch (error) {
        console.error('Failed to save config:', error)
        if (error.response?.data) {
          const errors = error.response.data
          let errorMessage = this.t('configuration.aiModel.messages.saveFailed') + ': '
          
          if (errors.non_field_errors) {
            const uniqueConstraintError = errors.non_field_errors.find(err =>
              err.includes('唯一集合') || err.includes('unique')
            )
            if (uniqueConstraintError) {
              errorMessage = this.t('configuration.aiModel.messages.conflictError')
            } else {
              errorMessage += errors.non_field_errors.join(', ')
            }
          } else {
            Object.keys(errors).forEach(field => {
              if (Array.isArray(errors[field])) {
                errorMessage += field + ': ' + errors[field].join(', ') + '; '
              } else {
                errorMessage += field + ': ' + errors[field] + '; '
              }
            })
          }
          ElMessage.error(errorMessage)
        } else {
          ElMessage.error(this.t('configuration.aiModel.messages.saveFailedDetail', { error: error.message }))
        }
      } finally {
        this.isSaving = false
      }
    },
    async deleteConfig(configId) {
      try {
        await ElMessageBox.confirm(
          this.t('configuration.aiModel.messages.deleteConfirm'),
          this.t('configuration.aiModel.messages.deleteTitle'),
          {
            confirmButtonText: this.t('configuration.common.confirm'),
            cancelButtonText: this.t('configuration.common.cancel'),
            type: 'warning'
          }
        )
      } catch {
        return
      }

      try {
        await api.delete('/requirement-analysis/ai-models/' + configId + '/')
        ElMessage.success(this.t('configuration.aiModel.messages.deleteSuccess'))
        this.loadConfigs()
      } catch (error) {
        console.error('Failed to delete config:', error)
        ElMessage.error(this.t('configuration.aiModel.messages.deleteFailedDetail', { error: error.response?.data?.error || error.message }))
      }
    },
    async testConnection(config) {
      this.isTestingConnection = true
      this.testingConfigId = config.id

      try {
        const response = await api.post('/requirement-analysis/ai-models/' + config.id + '/test_connection/')
        this.testResult = response.data
        this.showTestResult = true
      } catch (error) {
        console.error('Failed to test connection:', error)
        this.testResult = {
          success: false,
          message: error.response?.data?.message || error.message,
          response: ''
        }
        this.showTestResult = true
      } finally {
        this.isTestingConnection = false
        this.testingConfigId = null
      }
    },
    closeModals() {
      this.showModal = false
      this.isEditing = false
      this.editingConfigId = null
      this.resetForm()
    },
    closeTestResult() {
      this.showTestResult = false
    }
  }
}
</script>

<style lang="scss" scoped>
:root {
  --primary-color: #7b42f6;
  --primary-dark: #5a32a3;
  --primary-light: #f8f7ff;
  --border-color: #e8e8e8;
  --text-primary: #262626;
  --text-secondary: #595959;
  --text-tertiary: #8c8c8c;
  --bg-light: #ffffff;
  --bg-gray: #fafafa;
  --success-color: #52c41a;
  --warning-color: #faad14;
  --danger-color: #ff4d4f;
  --info-color: #1890ff;
}

.page-container {
  margin: -20px;
  min-height: calc(100% + 40px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  line-height: 24px;
  gap: 20px;
  width: calc(100% + 40px);
  box-sizing: border-box;
  padding: 24px;
}

.page-header-card {
  padding: 24px 28px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;

  .page-header-content {
    display: flex;
    align-items: center;

    h1 {
      font-size: 20px;
      font-weight: 600;
      color: #262626;
      margin: 0;
    }
  }
}

.create-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
  border: none !important;
  color: white !important;
  font-weight: 600 !important;
  padding: 10px 20px !important;
  border-radius: 8px !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;

  .el-icon {
    margin-right: 6px;
  }

  &:hover {
    background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(123, 66, 246, 0.4) !important;
  }
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;

  .el-table {
    border: none;
    border-radius: 8px 8px 0 0;
    overflow: hidden;
    min-height: 200px;
    box-shadow: none;
    transition: all 0.3s ease;
    background-color: transparent !important;

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

    :deep(.el-table__header-wrapper) {
      background-color: #ffffff !important;

      :deep(.el-table__header) {
        background-color: #ffffff !important;

        :deep(th) {
          background-color: #ffffff !important;
          color: #5a32a3;
          font-weight: 600;
          font-size: 14px;
          border-bottom: 1px solid #e9ecef;
          padding: 16px;
          text-align: center;
          line-height: 24px;
          transition: all 0.3s ease;

          &:hover {
            background-color: #ffffff !important;
          }
        }
      }
    }

    :deep(.el-table__body-wrapper) {
      :deep(.el-table__body) {
        :deep(tr) {
          transition: all 0.3s ease;

          &:hover {
            background-color: #f8f7ff !important;
          }

          &.el-table__row--striped {
            background-color: #fafaff !important;
          }
        }

        :deep(td) {
          border-bottom: 1px solid #e9ecef;
          padding: 16px;
          color: #333;
          transition: all 0.3s ease;
        }
      }
    }
  }
}

.config-name-cell {
  padding: 4px 8px;
  line-height: 1.6;
  font-weight: 400;
  color: #333;
  text-align: center;
}

.model-badge, .role-badge, .status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.model-badge.deepseek {
  background: #e6f7ff;
  color: #1890ff;
}

.model-badge.qwen {
  background: #e6fffb;
  color: #13c2c2;
}

.model-badge.siliconflow {
  background: #f6ffed;
  color: #52c41a;
}

.model-badge.other {
  background: #f5f5f5;
  color: #8c8c8c;
}

.role-badge {
  width: 96px;
  text-align: center;
}

.role-badge.writer {
  background: #f9f0ff;
  color: #722ed1;
}

.role-badge.reviewer {
  background: #fff7e6;
  color: #fa8c16;
}

.role-badge.knowledge_base {
  background: #fff0f6;
  color: #eb2f96;
}

.role-badge.bug_analyzer {
  background: #fff2e8;
  color: #fa541c;
}

.role-badge.assertion_generator {
  background: #e6fffb;
  color: #13c2c2;
}

.role-badge.scene_generator {
  background: #e6f7ff;
  color: #1890ff;
}

.status-badge {
  background: #fff1f0;
  color: #f5222d;
}

.status-badge.active {
  background: #f6ffed;
  color: #52c41a;
}

.model-name {
  font-size: 14px;
  color: #333;
}

.action-buttons {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px !important;
  min-width: 32px;

  .el-icon {
    font-size: 14px;
  }
}

.test-btn {
  background: #52c41a;
  border-color: #52c41a;

  &:hover {
    background: #73d13d !important;
    border-color: #73d13d !important;
  }
}

.edit-btn {
  background: #7c3aed;
  border-color: #7c3aed;

  &:hover {
    background: #8b5cf6 !important;
    border-color: #8b5cf6 !important;
  }
}

.delete-btn {
  background: #ef4444;
  border-color: #ef4444;

  &:hover {
    background: #f87171 !important;
    border-color: #f87171 !important;
  }
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.empty-state h3 {
  color: #5a32a3;
  margin-bottom: 10px;
  font-size: 1.2rem;
  font-weight: 600;
}

.empty-state p {
  color: #666;
  margin-bottom: 24px;
}

.add-first-config-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);

  &:hover {
    background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(123, 66, 246, 0.4);
  }
}

.form-hint {
  display: block;
  margin-top: 6px;
  color: #999;
  font-size: 12px;
  line-height: 1.5;
}

.error-message {
  display: block;
  margin-top: 6px;
  color: #ff4d4f;
  font-size: 12px;
  line-height: 1.5;
}

.test-result {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  padding: 0;

  &.success {
    .result-icon {
      background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.3);
    }
  }

  &.error {
    .result-icon {
      background: linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%);
      box-shadow: 0 4px 12px rgba(255, 77, 79, 0.3);
    }
  }
}

.result-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 4px;
}

.result-content {
  flex: 1;

  h4 {
    margin: 0 0 6px 0;
    font-size: 18px;
    font-weight: 600;
    color: #333;
  }

  > p {
    margin: 0 0 16px 0;
    font-size: 14px;
    color: #666;
    line-height: 1.5;
  }
}

.api-response {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;

  label {
    display: block;
    margin-bottom: 10px;
    font-size: 14px;
    font-weight: 600;
    color: #333;
  }

  p {
    margin: 0;
    padding: 0;
    font-size: 14px;
    color: #333;
    line-height: 1.6;
    word-break: break-all;
  }
}

// 测试结果弹窗样式
:deep(.test-result-dialog) {
  .el-dialog__header {
    padding: 20px 24px;
    margin: 0;
    border-bottom: 1px solid #f0f0f0;

    .el-dialog__title {
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }
  }

  .el-dialog__body {
    padding: 24px;
  }

  .el-dialog__headerbtn {
    top: 20px;
    right: 20px;

    .el-dialog__close {
      font-size: 18px;
      color: #999;

      &:hover {
        color: #666;
      }
    }
  }
}

// 配置弹窗样式
:deep(.config-dialog) {
  .el-dialog__header {
    padding: 20px 24px;
    margin: 0;
    border-bottom: 1px solid #f0f0f0;

    .el-dialog__title {
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }
  }

  .el-dialog__body {
    padding: 24px;
  }

  .config-form {
    .el-form-item {
      margin-bottom: 20px;

      &__label {
        font-weight: 500;
        color: #333;
      }

      // 必填项红色星号
      .required-star {
        color: #ff4d4f;
        margin-left: 4px;
      }
    }

    // 下拉选择框紫色主题
    .el-select {
      .el-input__wrapper {
        &.is-focus {
          box-shadow: 0 0 0 1px #7b42f6 inset;
        }
      }

      .el-input.is-focus .el-input__wrapper {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }

    // 输入框紫色主题
    .el-input__wrapper {
      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding: 16px 24px 0;

    .cancel-btn {
      padding: 10px 24px;
      border-radius: 8px;
      font-weight: 500;

      &:hover {
        color: #7b42f6;
        border-color: #7b42f6;
        background: #f8f7ff;
      }
    }

    .save-btn {
      padding: 10px 24px;
      border-radius: 8px;
      font-weight: 500;
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      border: none;
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
        box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
      }
    }
  }
}
</style>
