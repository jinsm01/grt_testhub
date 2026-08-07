<template>
  <div class="page-container">
    <div class="page-header-card">
      <div class="page-header-content">
        <h1>{{ $t('promptConfig.title') }}</h1>
      </div>
      <div class="header-actions">
        <el-button type="primary" class="load-defaults-btn" @click="loadDefaultPrompts">
          <el-icon><Download /></el-icon>
          {{ $t('promptConfig.loadDefaults') }}
        </el-button>
        <el-button type="primary" class="create-btn" @click="openAddModal">
          <el-icon><Plus /></el-icon>
          {{ $t('promptConfig.addConfig') }}
        </el-button>
      </div>
    </div>

    <div class="card-container">
      <el-table :data="configs" v-loading="loading" stripe style="width: 100%">
        <el-table-column type="index" label="序号" width="60" header-align="center" align="center" />
        <el-table-column :label="$t('promptConfig.configName')" min-width="180" show-overflow-tooltip header-align="center" align="left">
          <template #default="{ row }">
            <div class="config-name-cell">{{ row.name || $t('promptConfig.unnamed') }}</div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('promptConfig.promptType')" width="200" header-align="center" align="center">
          <template #default="{ row }">
            <span class="type-badge" :class="row.prompt_type">
              {{ getPromptTypeLabel(row.prompt_type) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('promptConfig.status')" width="90" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="{ active: row.is_active }">
              {{ row.is_active ? $t('promptConfig.enabled') : $t('promptConfig.disabled') }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('promptConfig.creator')" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <span class="creator-name">{{ row.created_by_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('promptConfig.operation')" width="280" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="info" class="action-btn preview-btn" @click="previewPrompt(row)">
                <el-icon><View /></el-icon>
                <span>{{ $t('promptConfig.preview') }}</span>
              </el-button>
              <el-button size="small" type="primary" class="action-btn edit-btn" @click="editConfig(row)">
                <el-icon><Edit /></el-icon>
                <span>{{ $t('promptConfig.edit') }}</span>
              </el-button>
              <el-button size="small" type="danger" class="action-btn delete-btn" @click="deleteConfig(row.id)">
                <el-icon><Delete /></el-icon>
                <span>{{ $t('promptConfig.delete') }}</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="configs.length === 0" class="empty-state">
        <div class="empty-icon">📝</div>
        <h3>{{ $t('promptConfig.noConfigs') }}</h3>
        <p>{{ $t('promptConfig.emptyHint') }}</p>
        <div class="empty-actions">
          <el-button type="primary" class="add-first-config-btn" @click="openAddModal">
            {{ $t('promptConfig.addFirstConfig') }}
          </el-button>
          <el-button class="load-defaults-first-btn" @click="loadDefaultPrompts">
            {{ $t('promptConfig.loadDefaults') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- 添加/编辑配置弹窗 -->
    <el-dialog v-model="showModal" :title="isEditing ? $t('promptConfig.editConfig') : $t('promptConfig.addConfig')" width="700px" :close-on-click-modal="false" class="config-dialog">
      <el-form :model="configForm" ref="configFormRef" label-width="110px" class="config-form">
        <el-form-item :class="{ 'is-error': formErrors.name }">
          <template #label>
            <span>{{ $t('promptConfig.configName') }}</span><span class="required-star">*</span>
          </template>
          <el-input v-model="configForm.name" :placeholder="$t('promptConfig.configNamePlaceholder')" />
          <div v-if="formErrors.name" class="error-message">{{ formErrors.name }}</div>
        </el-form-item>
        <el-form-item :class="{ 'is-error': formErrors.prompt_type }">
          <template #label>
            <span>{{ $t('promptConfig.promptType') }}</span><span class="required-star">*</span>
          </template>
          <el-select v-model="configForm.prompt_type" :placeholder="$t('promptConfig.selectPromptType')" style="width: 100%">
            <el-option
              v-for="choice in promptTypeChoices"
              :key="choice.value"
              :value="choice.value"
              :label="choice.label"
            />
          </el-select>
          <div v-if="formErrors.prompt_type" class="error-message">{{ formErrors.prompt_type }}</div>
        </el-form-item>
        <el-form-item :class="{ 'is-error': formErrors.content }">
          <template #label>
            <span>{{ $t('promptConfig.promptContent') }}</span><span class="required-star">*</span>
          </template>
          <div class="textarea-with-count" style="width: 100%">
            <el-input
              v-model="configForm.content"
              type="textarea"
              :rows="15"
              :placeholder="$t('promptConfig.contentPlaceholder')"
              class="prompt-textarea"
              style="width: 100%"
            />
            <div class="char-count">{{ $t('promptConfig.charCount', { count: configForm.content.length }) }}</div>
          </div>
          <div v-if="formErrors.content" class="error-message">{{ formErrors.content }}</div>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="configForm.is_active">
            {{ $t('promptConfig.enableConfig') }}
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button class="cancel-btn" @click="closeModals">{{ $t('promptConfig.cancel') }}</el-button>
          <el-button type="primary" class="save-btn" @click="saveConfig" :loading="isSaving">
            {{ $t('promptConfig.saveConfig') }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 预览弹窗 -->
    <el-dialog v-model="showPreviewModal" :title="$t('promptConfig.previewTitle', { name: previewConfig.name })" width="700px" class="preview-dialog">
      <div class="preview-content">
        <div class="preview-meta">
          <div class="meta-item">
            <label>{{ $t('promptConfig.promptType') }}</label>
            <span class="type-badge" :class="previewConfig.prompt_type">
              {{ getPromptTypeLabel(previewConfig.prompt_type) }}
            </span>
          </div>
          <div class="meta-item">
            <label>{{ $t('promptConfig.status') }}</label>
            <span class="status-badge" :class="{ active: previewConfig.is_active }">
              {{ previewConfig.is_active ? $t('promptConfig.enabled') : $t('promptConfig.disabled') }}
            </span>
          </div>
        </div>
        <div class="content-display">
          <label>{{ $t('promptConfig.promptContent') }}</label>
          <div class="content-text">{{ previewConfig.content }}</div>
        </div>
      </div>
    </el-dialog>

    <!-- 默认提示词预览弹窗 -->
    <el-dialog v-model="showDefaultsModal" :title="$t('promptConfig.defaultPromptsPreview')" width="900px" class="defaults-dialog">
      <div class="defaults-content">
        <el-tabs v-model="activeTab">
          <el-tab-pane
            v-for="choice in promptTypeChoices"
            :key="choice.value"
            :label="choice.label"
            :name="choice.value"
          >
            <div class="content-display">
              <div class="content-text">{{ defaultPrompts[choice.value] || $t('promptConfig.noContent') }}</div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button class="cancel-btn" @click="closeDefaultsModal">{{ $t('promptConfig.cancel') }}</el-button>
          <el-button type="primary" class="save-btn" @click="confirmLoadDefaults" :loading="isLoadingDefaults">
            {{ isLoadingDefaults ? $t('promptConfig.loading') : $t('promptConfig.confirmLoad') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { Plus, Edit, Delete, View, Download } from '@element-plus/icons-vue'

export default {
  name: 'PromptConfig',
  components: {
    Plus,
    Edit,
    Delete,
    View,
    Download
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
      isEditing: false,
      isSaving: false,
      editingConfigId: null,
      showPreviewModal: false,
      showDefaultsModal: false,
      isLoadingDefaults: false,
      previewConfig: {},
      defaultPrompts: {},
      activeTab: '',
      promptTypeChoices: [],
      configForm: {
        name: '',
        prompt_type: '',
        content: '',
        is_active: true
      },
      formErrors: {
        name: '',
        prompt_type: '',
        content: ''
      }
    }
  },

  mounted() {
    this.loadConfigs()
    this.loadPromptTypes()
  },

  methods: {
    getPromptTypeLabel(type) {
      const choice = this.promptTypeChoices.find(c => c.value === type)
      return choice ? choice.label : type
    },

    async loadPromptTypes() {
      try {
        const response = await api.get('/requirement-analysis/prompts/prompt_types/')
        if (response.data && response.data.choices) {
          this.promptTypeChoices = response.data.choices
        }
      } catch (error) {
        console.error('加载提示词类型失败:', error)
        this.promptTypeChoices = []
      }
    },

    openAddModal() {
      this.resetForm()
      this.clearFormErrors()
      this.isEditing = false
      this.showModal = true
    },

    async loadConfigs() {
      this.loading = true
      try {
        console.log('Loading prompt configs...')
        const response = await api.get('/requirement-analysis/prompts/')
        console.log('Prompts API response:', response.data)

        // 处理分页API响应格式
        if (response.data && response.data.results && Array.isArray(response.data.results)) {
          this.configs = response.data.results
          console.log('Loaded configs from results:', this.configs)
        } else if (response.data && Array.isArray(response.data)) {
          // 直接数组格式的fallback
          this.configs = response.data
          console.log('Loaded configs from direct array:', this.configs)
        } else {
          console.warn('Unexpected API response format:', response.data)
          this.configs = []
        }

        console.log('Final configs count:', this.configs.length)
      } catch (error) {
        console.error(this.t('promptConfig.loadConfigsFailed'), error)
        this.configs = [] // 确保configs始终是数组

        if (error.response?.status === 401) {
          ElMessage.error(this.t('promptConfig.pleaseLogin'))
        } else {
          ElMessage.error(this.t('promptConfig.loadConfigsFailed') + ': ' + (error.response?.data?.error || error.message))
        }
      } finally {
        this.loading = false
      }
    },

    async loadDefaultPrompts() {
      console.log('loadDefaultPrompts clicked')
      try {
        const response = await api.get('/requirement-analysis/prompts/load_defaults/')
        console.log('Default prompts response:', response.data)
        this.defaultPrompts = response.data.defaults
        if (this.promptTypeChoices.length > 0) {
          this.activeTab = this.promptTypeChoices[0].value
        }
        this.showDefaultsModal = true
        console.log('showDefaultsModal set to:', this.showDefaultsModal)
      } catch (error) {
        console.error(this.t('promptConfig.loadDefaultsFailed'), error)
        ElMessage.error(this.t('promptConfig.loadDefaultsFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    async confirmLoadDefaults() {
      this.isLoadingDefaults = true

      try {
        const promptType = this.activeTab
        const promptContent = this.defaultPrompts[promptType]

        if (promptContent) {
          const typeLabel = this.getPromptTypeLabel(promptType)
          const configName = `默认${typeLabel}`

          await api.post('/requirement-analysis/prompts/', {
            name: configName,
            prompt_type: promptType,
            content: promptContent,
            is_active: true
          })

          ElMessage.success(this.t('promptConfig.defaultsLoadSuccess'))
        } else {
          ElMessage.warning('当前选中的提示词类型没有默认内容')
        }
        this.closeDefaultsModal()
        this.loadConfigs()
      } catch (error) {
        console.error(this.t('promptConfig.loadDefaultsFailed'), error)
        ElMessage.error(this.t('promptConfig.loadFailed') + ': ' + (error.response?.data?.error || error.message))
      } finally {
        this.isLoadingDefaults = false
      }
    },

    resetForm() {
      this.configForm = {
        name: '',
        prompt_type: '',
        content: '',
        is_active: true
      }
    },

    clearFormErrors() {
      this.formErrors = {
        name: '',
        prompt_type: '',
        content: ''
      }
    },

    validateForm() {
      this.clearFormErrors()
      let isValid = true

      if (!this.configForm.name || this.configForm.name.trim() === '') {
        this.formErrors.name = this.t('promptConfig.nameRequired')
        isValid = false
      }

      if (!this.configForm.prompt_type) {
        this.formErrors.prompt_type = this.t('promptConfig.promptTypeRequired')
        isValid = false
      }

      if (!this.configForm.content || this.configForm.content.trim() === '') {
        this.formErrors.content = this.t('promptConfig.contentRequired')
        isValid = false
      }

      return isValid
    },

    editConfig(config) {
      this.isEditing = true
      this.editingConfigId = config.id
      this.configForm = {
        name: config.name,
        prompt_type: config.prompt_type,
        content: config.content,
        is_active: config.is_active
      }
      this.clearFormErrors()
      this.showModal = true
    },

    previewPrompt(config) {
      this.previewConfig = config
      this.showPreviewModal = true
    },

    async saveConfig() {
      if (!this.validateForm()) {
        return
      }

      this.isSaving = true

      try {
        if (this.isEditing) {
          await api.patch(`/requirement-analysis/prompts/${this.editingConfigId}/`, this.configForm)
          ElMessage.success(this.t('promptConfig.updateSuccess'))
        } else {
          await api.post('/requirement-analysis/prompts/', this.configForm)
          ElMessage.success(this.t('promptConfig.addSuccess'))
        }

        this.closeModals()
        this.loadConfigs()
      } catch (error) {
        console.error(this.t('promptConfig.saveConfigFailed'), error)
        ElMessage.error(this.t('promptConfig.saveFailed') + ': ' + (error.response?.data?.error || error.message))
      } finally {
        this.isSaving = false
      }
    },

    async deleteConfig(configId) {
      try {
        await ElMessageBox.confirm(
          this.t('promptConfig.deleteConfirm'),
          this.t('promptConfig.deleteTitle'),
          {
            confirmButtonText: this.t('promptConfig.confirm'),
            cancelButtonText: this.t('promptConfig.cancel'),
            type: 'warning'
          }
        )
      } catch {
        return
      }

      try {
        await api.delete(`/requirement-analysis/prompts/${configId}/`)
        ElMessage.success(this.t('promptConfig.deleteSuccess'))
        this.loadConfigs()
      } catch (error) {
        console.error(this.t('promptConfig.deleteConfigFailed'), error)
        ElMessage.error(this.t('promptConfig.deleteFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    closeModals() {
      this.showModal = false
      this.isEditing = false
      this.editingConfigId = null
      this.resetForm()
    },

    closePreview() {
      this.showPreviewModal = false
      this.previewConfig = {}
    },

    closeDefaultsModal() {
      this.showDefaultsModal = false
      this.defaultPrompts = {}
      this.activeTab = this.promptTypeChoices.length > 0 ? this.promptTypeChoices[0].value : ''
    },

    truncateContent(content, maxLength) {
      if (!content) return ''
      if (content.length <= maxLength) return content
      return content.substring(0, maxLength) + '...'
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
}

.page-header-content {
  display: flex;
  align-items: center;
}

.page-header-content h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #262626;
  line-height: 1.4;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.load-defaults-btn {
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
}

.config-name-cell {
  padding: 4px 8px;
  line-height: 1.6;
  font-weight: 400;
  color: #333;
  text-align: center;
}

.type-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.type-badge.writer {
  background: #e6f7ff;
  color: #1890ff;
}

.type-badge.reviewer {
  background: #f9f0ff;
  color: #722ed1;
}

.type-badge.knowledge_base {
  background: #e6fffb;
  color: #13c2c2;
}

.type-badge.assertion_generator {
  background: #fff7e6;
  color: #fa8c16;
}

.type-badge.bug_classify {
  background: #fff1f0;
  color: #cf1322;
}

.type-badge.bug_severity {
  background: #fff7e6;
  color: #d46b08;
}

.type-badge.bug_module_fallback {
  background: #f0f5ff;
  color: #2f54eb;
}

.type-badge.bug_root_cause {
  background: #f9f0ff;
  color: #531dab;
}

.type-badge.bug_test_focus {
  background: #e6fffb;
  color: #08979c;
}

.type-badge.bug_summary {
  background: #fcffe6;
  color: #614700;
}

.type-badge.bug_risks {
  background: #fff2f0;
  color: #a8071a;
}

.type-badge.bug_keywords {
  background: #e6f7ff;
  color: #096dd9;
}

.type-badge.bug_module_deep {
  background: #f3f0ff;
  color: #391085;
}

.creator-name {
  font-size: 14px;
  color: #595959;
  text-align: center;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  background: #fff1f0;
  color: #f5222d;
}

.status-badge.active {
  background: #f6ffed;
  color: #52c41a;
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

.preview-btn {
  background: #1890ff;
  border-color: #1890ff;
}

.preview-btn:hover {
  background: #40a9ff;
  border-color: #40a9ff;
}

.edit-btn {
  background: #7b42f6;
  border-color: #7b42f6;
}

.edit-btn:hover {
  background: #6d33e6;
  border-color: #6d33e6;
}

.delete-btn {
  background: #ff4d4f;
  border-color: #ff4d4f;
}

.delete-btn:hover {
  background: #e03c3e;
  border-color: #e03c3e;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #6d5d8f;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.empty-state h3 {
  color: #5a32a3;
  margin-bottom: 10px;
  font-size: 1.3rem;
  font-weight: 600;
}

.empty-state p {
  color: #6d5d8f;
  margin-bottom: 24px;
}

.empty-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.add-first-config-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border: none;
  padding: 12px 24px;
  font-size: 1rem;
  font-weight: 500;
  border-radius: 12px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.2);
}

.add-first-config-btn:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.3);
}

.load-defaults-first-btn {
  background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
  border: none;
  padding: 12px 24px;
  font-size: 1rem;
  font-weight: 500;
  border-radius: 12px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(149, 165, 166, 0.2);
  color: white;
}

.load-defaults-first-btn:hover {
  background: linear-gradient(135deg, #7f8c8d 0%, #6c757d 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(149, 165, 166, 0.3);
}

:deep(.el-table) {
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

.config-dialog :deep(.el-dialog__header),
.preview-dialog :deep(.el-dialog__header),
.defaults-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-bottom: 1px solid rgba(147, 112, 219, 0.15);
  padding: 20px 24px;
  margin-right: 0;
}

.config-dialog :deep(.el-dialog__title),
.preview-dialog :deep(.el-dialog__title),
.defaults-dialog :deep(.el-dialog__title) {
  color: #5a32a3;
  font-weight: 600;
  font-size: 1.2rem;
}

.config-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.config-form :deep(.el-form-item__label) {
  color: #5a32a3;
  font-weight: 500;
}

.required-star {
  color: #ff4d4f;
  margin-left: 4px;
}

.textarea-with-count {
  position: relative;
}

.prompt-textarea :deep(.el-textarea__inner) {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  line-height: 1.6;
  color: #262626;
  padding-bottom: 36px;
}

.char-count {
  position: absolute;
  bottom: 8px;
  right: 12px;
  font-size: 0.65rem;
  color: #8c8c8c;
  font-weight: 400;
}

.textarea-tips {
  margin-top: 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.2);
  box-shadow: 0 4px 12px rgba(147, 112, 219, 0.08);
}

.textarea-tips p {
  margin: 0 0 12px 0;
  color: #5a32a3;
  font-weight: 600;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.textarea-tips p::before {
  content: '💡';
  font-size: 1rem;
}

.textarea-tips ul {
  margin: 0;
  padding-left: 24px;
}

.textarea-tips li {
  color: #6d5d8f;
  margin-bottom: 6px;
  line-height: 1.6;
  font-size: 0.85rem;
}

.textarea-tips li::marker {
  color: #9370db;
}

.error-message {
  color: #ff4d4f;
  font-size: 0.8rem;
  margin-top: 4px;
}

:deep(.el-form-item.is-error .el-input__wrapper),
:deep(.el-form-item.is-error .el-textarea__inner) {
  box-shadow: 0 0 0 1px #ff4d4f inset;
}

/* 下拉选择框样式 - 紫色主题 */
:deep(.el-select .el-input__wrapper) {
  box-shadow: 0 0 0 1px #7b42f6 inset !important;
}

:deep(.el-select .el-input.is-focus .el-input__wrapper),
:deep(.el-select .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #7b42f6 inset !important;
}

:deep(.el-select:hover .el-input__wrapper) {
  box-shadow: 0 0 0 1px #7b42f6 inset !important;
}

/* 覆盖 Element Plus 默认的聚焦样式 */
:deep(.el-select .el-input__wrapper:focus-within) {
  box-shadow: 0 0 0 1px #7b42f6 inset !important;
}

/* 针对展开状态的下拉框 */
:deep(.el-select.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #7b42f6 inset !important;
}

/* 针对激活状态 */
:deep(.el-select .el-input__wrapper--focus) {
  box-shadow: 0 0 0 1px #7b42f6 inset !important;
}

/* 全局覆盖 */
:deep(.el-select .el-input__inner) {
  box-shadow: none !important;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 20px;
}

.cancel-btn {
  padding: 10px 24px;
  border-radius: 10px;
  transition: all 0.3s ease;
}

.save-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border: none;
  padding: 10px 24px;
  border-radius: 10px;
  transition: all 0.3s ease;
}

.save-btn:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-1px);
}

.preview-content {
  margin-bottom: 24px;
}

.preview-meta {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: rgba(243, 240, 250, 0.8);
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.1);
  flex-wrap: wrap;
}

.preview-meta .meta-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.preview-meta .meta-item label {
  font-weight: 600;
  color: #5a32a3;
  font-size: 0.9rem;
}

.content-display {
  margin-bottom: 24px;
}

.content-display label {
  font-weight: 600;
  color: #5a32a3;
  margin-bottom: 12px;
  display: block;
  font-size: 0.95rem;
}

.content-text {
  background: rgba(255, 255, 255, 0.9);
  padding: 20px;
  border-radius: 10px;
  color: #5a32a3;
  line-height: 1.6;
  white-space: pre-wrap;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9rem;
  border-left: 4px solid #9370db;
  max-height: 400px;
  overflow-y: auto;
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.1);
}

.defaults-content :deep(.el-tabs__header) {
  margin-bottom: 20px;
  overflow: hidden;
}

.defaults-content :deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  scrollbar-color: #c4b5e0 transparent;
}

.defaults-content :deep(.el-tabs__nav-wrap)::-webkit-scrollbar {
  height: 6px;
}

.defaults-content :deep(.el-tabs__nav-wrap)::-webkit-scrollbar-track {
  background: #f5f3ff;
  border-radius: 3px;
}

.defaults-content :deep(.el-tabs__nav-wrap)::-webkit-scrollbar-thumb {
  background: #c4b5e0;
  border-radius: 3px;
}

.defaults-content :deep(.el-tabs__nav-wrap)::-webkit-scrollbar-thumb:hover {
  background: #9370db;
}

.defaults-content :deep(.el-tabs__nav-scroll) {
  display: flex;
  min-width: min-content;
}

.defaults-content :deep(.el-tabs__item) {
  color: #6d5d8f;
  font-weight: 500;
  padding: 0 12px;
  height: 36px;
  line-height: 36px;
  font-size: 13px;
  white-space: nowrap;
}

.defaults-content :deep(.el-tabs__item.is-active) {
  color: #5a32a3;
}

.defaults-content :deep(.el-tabs__active-bar) {
  background-color: #9370db;
}

@media (max-width: 768px) {
  .page-container {
    padding: 16px;
    margin: -16px;
    min-height: calc(100% + 32px);
  }

  .page-header-card {
    padding: 20px;
    flex-direction: column;
    align-items: flex-start;
  }

  .page-header-content h1 {
    font-size: 1.4rem;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
  }

  .load-defaults-btn,
  .create-btn {
    width: 100%;
    justify-content: center;
  }

  .card-container {
    padding: 16px;
  }

  .action-buttons {
    flex-wrap: wrap;
  }

  .action-btn {
    padding: 4px 8px;
    font-size: 0.8rem;
  }

  .action-btn span {
    display: none;
  }

  .empty-actions {
    flex-direction: column;
    align-items: center;
  }

  .add-first-config-btn,
  .load-defaults-first-btn {
    width: 100%;
    max-width: 300px;
  }

  .preview-meta {
    flex-direction: column;
    gap: 12px;
  }

  .dialog-footer {
    flex-direction: column;
  }

  .cancel-btn,
  .save-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
