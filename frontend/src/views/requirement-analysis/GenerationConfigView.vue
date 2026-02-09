<template>
  <div class="generation-config">
    <div class="page-header">
      <h1>{{ $t('generationConfig.title') }}</h1>
      <p>{{ $t('generationConfig.subtitle') }}</p>
    </div>

    <div class="main-content">
      <!-- 配置列表 -->
      <div class="configs-section">
        <div class="section-header">
          <h2>{{ $t('generationConfig.configList') }}</h2>
          <button class="add-config-btn" @click="openAddModal">
            {{ $t('generationConfig.addConfig') }}
          </button>
        </div>

        <div class="configs-grid">
          <div v-for="config in configs" :key="config.id" class="config-card">
            <div class="config-header">
              <div class="config-title">
                <h3>{{ config.name }}</h3>
                <div class="config-badges">
                  <span class="status-badge" :class="{ active: config.is_active }">
                    {{ config.is_active ? $t('generationConfig.enabled') : $t('generationConfig.disabled') }}
                  </span>
                  <span class="mode-badge">
                    {{ config.default_output_mode === 'stream' ? $t('generationConfig.streamMode') : $t('generationConfig.completeMode') }}
                  </span>
                </div>
              </div>
              <div class="config-actions">
                <button v-if="!config.is_active" class="enable-btn" @click="enableConfig(config.id)">
                  {{ $t('generationConfig.enable') }}
                </button>
                <button class="edit-btn" @click="editConfig(config)">{{ $t('generationConfig.edit') }}</button>
                <button class="delete-btn" @click="deleteConfig(config.id)">{{ $t('generationConfig.delete') }}</button>
              </div>
            </div>

            <div class="config-details">
              <div class="detail-section">
                <h4>{{ $t('generationConfig.outputMode') }}</h4>
                <div class="detail-item">
                  <label>{{ $t('generationConfig.defaultMode') }}</label>
                  <span>{{ config.default_output_mode === 'stream' ? $t('generationConfig.realtimeStream') : $t('generationConfig.completeOutput') }}</span>
                </div>
              </div>

              <div class="detail-section">
                <h4>{{ $t('generationConfig.automationProcess') }}</h4>
                <div class="detail-item">
                  <label>{{ $t('generationConfig.aiReview') }}</label>
                  <span :class="{ enabled: config.enable_auto_review, disabled: !config.enable_auto_review }">
                    {{ config.enable_auto_review ? $t('generationConfig.enabled') : $t('generationConfig.disabled') }}
                  </span>
                </div>
              </div>

              <div class="detail-section">
                <h4>{{ $t('generationConfig.timeoutSettings') }}</h4>
                <div class="detail-item">
                  <label>{{ $t('generationConfig.reviewTimeout') }}</label>
                  <span>{{ config.review_timeout }} {{ $t('generationConfig.seconds') }}</span>
                </div>
              </div>

              <div class="config-meta">
                <div class="meta-item">
                  <label>{{ $t('generationConfig.createdAt') }}</label>
                  <span>{{ formatDateTime(config.created_at) }}</span>
                </div>
                <div class="meta-item">
                  <label>{{ $t('generationConfig.updatedAt') }}</label>
                  <span>{{ formatDateTime(config.updated_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="configs.length === 0" class="empty-state">
          <div class="empty-icon">⚙️</div>
          <h3>{{ $t('generationConfig.emptyTitle') }}</h3>
          <p>{{ $t('generationConfig.emptyDescription') }}</p>
          <button class="add-first-config-btn" @click="openAddModal">
            {{ $t('generationConfig.addFirstConfig') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 添加/编辑配置弹窗 -->
    <div v-if="showAddModal || showEditModal" class="config-modal" @click="closeModals">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ isEditing ? $t('generationConfig.editTitle') : $t('generationConfig.addTitle') }}{{ $t('generationConfig.formTitle') }}</h3>
          <button class="close-btn" @click="closeModals">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveConfig">
            <div class="form-section">
              <h4>{{ $t('generationConfig.basicInfo') }}</h4>
              <div class="form-group">
                <label>{{ $t('generationConfig.configName') }} <span class="required">*</span></label>
                <input
                  v-model="configForm.name"
                  type="text"
                  class="form-input"
                  :placeholder="$t('generationConfig.configNamePlaceholder')"
                  required>
              </div>

              <div class="form-group">
                <label class="checkbox-label">
                  <input v-model="configForm.is_active" type="checkbox">
                  <span class="checkmark"></span>
                  {{ $t('generationConfig.enableThisConfig') }}
                </label>
                <div class="checkbox-hint">
                  {{ $t('generationConfig.enableHint') }}
                </div>
              </div>
            </div>

            <div class="form-section">
              <h4>{{ $t('generationConfig.outputModeSettings') }}</h4>
              <div class="form-group">
                <label>{{ $t('generationConfig.defaultOutputMode') }} <span class="required">*</span></label>
                <select v-model="configForm.default_output_mode" class="form-select" required>
                  <option value="stream">{{ $t('generationConfig.realtimeStream') }}</option>
                  <option value="complete">{{ $t('generationConfig.completeOutput') }}</option>
                </select>
                <div class="field-hint">
                  {{ $t('generationConfig.outputModeHint') }}
                </div>
              </div>
            </div>

            <div class="form-section">
              <h4>{{ $t('generationConfig.automationSettings') }}</h4>
              <div class="form-group">
                <label class="checkbox-label">
                  <input v-model="configForm.enable_auto_review" type="checkbox">
                  <span class="checkmark"></span>
                  {{ $t('generationConfig.enableAutoReview') }}
                </label>
                <div class="checkbox-hint">
                  {{ $t('generationConfig.autoReviewHint') }}
                </div>
              </div>
            </div>

            <div class="form-section">
              <h4>{{ $t('generationConfig.timeoutSettingsLabel') }}</h4>
              <div class="form-group">
                <label>{{ $t('generationConfig.reviewTimeoutLabel') }}</label>
                <input
                  v-model.number="configForm.review_timeout"
                  type="number"
                  class="form-input"
                  min="10"
                  max="3600">
                <div class="field-hint">{{ $t('generationConfig.timeoutHint') }}</div>
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="cancel-btn" @click="closeModals">{{ $t('generationConfig.cancel') }}</button>
              <button
                type="submit"
                class="confirm-btn"
                :disabled="isSaving">
                <span v-if="isSaving">{{ $t('generationConfig.saving') }}</span>
                <span v-else>{{ $t('generationConfig.saveConfig') }}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { getGenerationConfigs, createGenerationConfig, updateGenerationConfig, deleteGenerationConfig } from '@/api/requirement-analysis'
import api from '@/utils/api'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

export default {
  name: 'GenerationConfigView',
  setup() {
    const { t, locale } = useI18n()
    return { t, locale }
  },
  data() {
    return {
      configs: [],
      showAddModal: false,
      showEditModal: false,
      isEditing: false,
      isSaving: false,
      editingConfigId: null,
      configForm: {
        name: '',
        default_output_mode: 'stream',
        enable_auto_review: true,
        review_timeout: 1500,
        is_active: true
      }
    }
  },

  mounted() {
    this.configForm.name = this.t('generationConfig.defaultConfigName')
    this.loadConfigs()
  },

  methods: {
    openAddModal() {
      this.resetForm()
      this.isEditing = false
      this.showAddModal = true
    },

    async loadConfigs() {
      try {
        console.log('Loading generation configs...')
        const response = await getGenerationConfigs()
        console.log('Generation configs API response:', response.data)

        // 处理分页API响应格式
        if (response.data && response.data.results && Array.isArray(response.data.results)) {
          this.configs = response.data.results
        } else if (response.data && Array.isArray(response.data)) {
          this.configs = response.data
        } else {
          console.warn('Unexpected API response format:', response.data)
          this.configs = []
        }

        console.log('Final configs count:', this.configs.length)
      } catch (error) {
        console.error('Failed to load config:', error)
        this.configs = []

        if (error.response?.status === 401) {
          ElMessage.error(this.t('generationConfig.pleaseLogin'))
        } else {
          ElMessage.error(this.t('generationConfig.loadFailed') + ': ' + (error.response?.data?.error || error.message))
        }
      }
    },

    resetForm() {
      this.configForm = {
        name: this.t('generationConfig.defaultConfigName'),
        default_output_mode: 'stream',
        enable_auto_review: true,
        review_timeout: 1500,
        is_active: true
      }
    },

    editConfig(config) {
      this.isEditing = true
      this.editingConfigId = config.id
      this.configForm = {
        name: config.name,
        default_output_mode: config.default_output_mode,
        enable_auto_review: config.enable_auto_review,
        review_timeout: config.review_timeout,
        is_active: config.is_active
      }
      this.showEditModal = true
    },

    async saveConfig() {
      this.isSaving = true

      try {
        if (this.isEditing) {
          await updateGenerationConfig(this.editingConfigId, this.configForm)
          ElMessage.success(this.t('generationConfig.updateSuccess'))
        } else {
          await createGenerationConfig(this.configForm)
          ElMessage.success(this.t('generationConfig.saveSuccess'))
        }

        this.closeModals()
        this.loadConfigs()
      } catch (error) {
        console.error('Failed to save config:', error)
        ElMessage.error(this.t('generationConfig.saveFailed') + ': ' + (error.response?.data?.error || error.message))
      } finally {
        this.isSaving = false
      }
    },

    async enableConfig(configId) {
      try {
        await api.post(`/requirement-analysis/generation-config/${configId}/enable/`)
        ElMessage.success(this.t('generationConfig.enableSuccess'))
        this.loadConfigs()
      } catch (error) {
        console.error('Failed to enable config:', error)
        ElMessage.error(this.t('generationConfig.enableFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    async deleteConfig(configId) {
      if (!confirm(this.t('generationConfig.deleteConfirm'))) {
        return
      }

      try {
        await deleteGenerationConfig(configId)
        ElMessage.success(this.t('generationConfig.deleteSuccess'))
        this.loadConfigs()
      } catch (error) {
        console.error('Failed to delete config:', error)
        ElMessage.error(this.t('generationConfig.deleteFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    closeModals() {
      this.showAddModal = false
      this.showEditModal = false
      this.isEditing = false
      this.editingConfigId = null
      this.resetForm()
    },

    formatDateTime(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleString(this.locale === 'zh-cn' ? 'zh-CN' : 'en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
  }
}
</script>

<style scoped>
.generation-config {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
  padding: 28px 20px;
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.12);
  border: 1px solid rgba(147, 112, 219, 0.2);
}

.page-header h1 {
  font-size: 2.2rem;
  color: #5a32a3;
  margin-bottom: 12px;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(90, 50, 163, 0.1);
  line-height: 1.2;
}

.page-header p {
  color: #6d5d8f;
  font-size: 1.05rem;
  opacity: 0.9;
  margin: 0;
  line-height: 1.5;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
  flex-wrap: wrap;
  gap: 12px;
  padding: 0 16px;
}

.section-header h2 {
  color: #5a32a3;
  margin: 0;
  font-size: 1.4rem;
  font-weight: 600;
  line-height: 1.3;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-header h2::before {
  content: '⚙️';
  font-size: 1.2rem;
}

.add-config-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.2);
  display: flex;
  align-items: center;
  gap: 8px;
}

.add-config-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.3);
}

.add-config-btn:disabled {
  background: linear-gradient(135deg, #d1c5f7 0%, #b8a7e8 100%);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.configs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(550px, 1fr));
  gap: 20px;
  padding: 0 16px;
}

.config-card {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.2);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.config-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #7b42f6 0%, #5a32a3 100%);
  border-radius: 16px 16px 0 0;
}

.config-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.15);
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.config-title h3 {
  color: #5a32a3;
  margin: 0 0 8px 0;
  font-size: 1.2rem;
  font-weight: 600;
  line-height: 1.4;
}

.config-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-badge, .mode-badge {
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.8rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.status-badge {
  background: rgba(211, 47, 47, 0.1);
  color: #d32f2f;
  border: 1px solid rgba(211, 47, 47, 0.2);
}

.status-badge.active {
  background: rgba(74, 36, 156, 0.1);
  color: #5a32a3;
  border: 1px solid rgba(147, 112, 219, 0.2);
}

.mode-badge {
  background: rgba(25, 118, 210, 0.1);
  color: #1976d2;
  border: 1px solid rgba(25, 118, 210, 0.2);
}

.config-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.enable-btn, .edit-btn, .delete-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.enable-btn {
  background: linear-gradient(135deg, #27ae60 0%, #219a52 100%);
  color: white;
}

.enable-btn:hover {
  background: linear-gradient(135deg, #219a52 0%, #1e8449 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(39, 174, 96, 0.3);
}

.edit-btn {
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
  color: white;
}

.edit-btn:hover {
  background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(243, 156, 18, 0.3);
}

.delete-btn {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
}

.delete-btn:hover {
  background: linear-gradient(135deg, #c0392b 0%, #a93226 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);
}

.config-details {
  margin-top: 20px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.detail-section {
  padding: 16px;
  background: rgba(243, 240, 250, 0.6);
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.1);
}

.detail-section h4 {
  margin: 0 0 12px 0;
  color: #5a32a3;
  font-size: 0.95rem;
  font-weight: 600;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 0.9rem;
}

.detail-item label {
  color: #6d5d8f;
  font-weight: 500;
  font-size: 0.85rem;
}

.detail-item span {
  color: #5a32a3;
  font-weight: 600;
}

.detail-item span.enabled {
  color: #27ae60;
}

.detail-item span.disabled {
  color: #e74c3c;
}

.config-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-top: 16px;
  padding: 16px;
  background: rgba(243, 240, 250, 0.4);
  border-radius: 10px;
  border: 1px solid rgba(147, 112, 219, 0.1);
  grid-column: 1 / -1;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-item label {
  font-size: 0.75rem;
  color: #6d5d8f;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.meta-item span {
  color: #5a32a3;
  font-size: 0.85rem;
  font-weight: 500;
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

.add-first-config-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.2);
}

.add-first-config-btn:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.3);
}

.config-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 16px;
  padding: 0;
  max-width: 700px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(147, 112, 219, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.15);
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
}

.modal-header h3 {
  margin: 0;
  color: #5a32a3;
  font-size: 1.3rem;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6d5d8f;
  transition: all 0.3s ease;
  padding: 5px 10px;
  border-radius: 8px;
}

.close-btn:hover {
  color: #5a32a3;
  background: rgba(147, 112, 219, 0.1);
}

.modal-body {
  padding: 30px;
}

.form-section {
  margin-bottom: 25px;
  padding: 20px;
  background: rgba(243, 240, 250, 0.6);
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.1);
}

.form-section h4 {
  margin: 0 0 15px 0;
  color: #5a32a3;
  font-size: 1.1rem;
  font-weight: 600;
}

.form-group {
  margin-bottom: 18px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #5a32a3;
  font-size: 0.9rem;
}

.form-input, .form-select {
  width: 100%;
  padding: 10px;
  border: 1px solid rgba(147, 112, 219, 0.2);
  border-radius: 10px;
  font-size: 0.95rem;
  transition: all 0.3s ease;
  background: white;
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: #7b42f6;
  box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.15);
}

.field-hint {
  margin-top: 5px;
  font-size: 0.8rem;
  color: #6d5d8f;
  font-style: italic;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  color: #5a32a3;
  font-weight: 500;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  accent-color: #7b42f6;
}

.checkbox-hint {
  margin-top: 5px;
  font-size: 0.8rem;
  color: #6d5d8f;
  font-style: italic;
}

.required {
  color: #e74c3c;
}

.modal-actions {
  display: flex;
  gap: 15px;
  justify-content: flex-end;
  margin-top: 30px;
}

.cancel-btn {
  background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.cancel-btn:hover {
  background: linear-gradient(135deg, #7f8c8d 0%, #6c7a7d 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(149, 165, 166, 0.3);
}

.confirm-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.2);
}

.confirm-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.3);
}

.confirm-btn:disabled {
  background: linear-gradient(135deg, #d1c5f7 0%, #b8a7e8 100%);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

@media (max-width: 768px) {
  .configs-grid {
    grid-template-columns: 1fr;
  }

  .config-header {
    flex-direction: column;
    gap: 15px;
    align-items: flex-start;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .detail-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
}
</style>
