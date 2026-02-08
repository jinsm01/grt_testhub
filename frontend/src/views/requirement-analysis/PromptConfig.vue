<template>
  <div class="prompt-config">
    <div class="page-header">
      <h1>{{ $t('promptConfig.title') }}</h1>
      <p>{{ $t('promptConfig.subtitle') }}</p>
    </div>

    <div class="main-content">
      <!-- 配置列表 -->
      <div class="configs-section">
        <div class="section-header">
          <h2>{{ $t('promptConfig.configListTitle') }}</h2>
          <div class="header-actions">
            <button class="load-defaults-btn" @click="loadDefaultPrompts">
              {{ $t('promptConfig.loadDefaults') }}
            </button>
            <button class="add-config-btn" @click="openAddModal">
              {{ $t('promptConfig.addConfig') }}
            </button>
          </div>
        </div>

        <div class="configs-grid">
          <div v-for="config in configs" :key="config.id" class="config-card">
            <div class="config-header">
              <div class="config-title">
                <h3>{{ config.name }}</h3>
                <div class="config-badges">
                  <span class="type-badge" :class="config.prompt_type">
                    {{ config.prompt_type === 'writer' ? $t('promptConfig.writerPrompt') : $t('promptConfig.reviewerPrompt') }}
                  </span>
                  <span class="status-badge" :class="{ active: config.is_active }">
                    {{ config.is_active ? $t('promptConfig.enabled') : $t('promptConfig.disabled') }}
                  </span>
                </div>
              </div>
              <div class="config-actions">
                <button class="preview-btn" @click="previewPrompt(config)">{{ $t('promptConfig.preview') }}</button>
                <button class="edit-btn" @click="editConfig(config)">{{ $t('promptConfig.edit') }}</button>
                <button class="delete-btn" @click="deleteConfig(config.id)">{{ $t('promptConfig.delete') }}</button>
              </div>
            </div>

            <div class="config-details">
              <div class="prompt-preview">
                <label>{{ $t('promptConfig.contentPreview') }}</label>
                <div class="content-preview">
                  {{ truncateContent(config.content, 200) }}
                </div>
              </div>
              <div class="config-meta">
                <div class="meta-item">
                  <label>{{ $t('promptConfig.createdAt') }}</label>
                  <span>{{ formatDateTime(config.created_at) }}</span>
                </div>
                <div class="meta-item">
                  <label>{{ $t('promptConfig.updatedAt') }}</label>
                  <span>{{ formatDateTime(config.updated_at) }}</span>
                </div>
                <div class="meta-item">
                  <label>{{ $t('promptConfig.createdBy') }}</label>
                  <span>{{ config.created_by_name || $t('promptConfig.unknown') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="configs.length === 0" class="empty-state">
          <div class="empty-icon">📝</div>
          <h3>{{ $t('promptConfig.noConfigs') }}</h3>
          <p>{{ $t('promptConfig.emptyHint') }}</p>
          <div class="empty-actions">
            <button class="add-first-config-btn" @click="openAddModal">
              {{ $t('promptConfig.addFirstConfig') }}
            </button>
            <button class="load-defaults-first-btn" @click="loadDefaultPrompts">
              {{ $t('promptConfig.loadDefaults') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加/编辑配置弹窗 -->
    <div v-if="showAddModal || showEditModal" class="config-modal" @click="closeModals">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>{{ isEditing ? $t('promptConfig.editConfig') : $t('promptConfig.addConfig') }}</h3>
          <button class="close-btn" @click="closeModals">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveConfig">
            <div class="form-group">
              <label>{{ $t('promptConfig.configName') }} <span class="required">*</span></label>
              <input
                v-model="configForm.name"
                type="text"
                class="form-input"
                :placeholder="$t('promptConfig.configNamePlaceholder')"
                required>
            </div>

            <div class="form-group">
              <label>{{ $t('promptConfig.promptType') }} <span class="required">*</span></label>
              <select v-model="configForm.prompt_type" class="form-select" required>
                <option value="">{{ $t('promptConfig.selectPromptType') }}</option>
                <option value="writer">{{ $t('promptConfig.writerPrompt') }}</option>
                <option value="reviewer">{{ $t('promptConfig.reviewerPrompt') }}</option>
              </select>
            </div>

            <div class="form-group">
              <label>{{ $t('promptConfig.promptContent') }} <span class="required">*</span></label>
              <div class="textarea-container">
                <textarea
                  v-model="configForm.content"
                  class="form-textarea large"
                  rows="20"
                  :placeholder="$t('promptConfig.contentPlaceholder')"
                  required></textarea>
                <div class="char-count">{{ $t('promptConfig.charCount', { count: configForm.content.length }) }}</div>
              </div>
              <div class="textarea-tips">
                <p><strong>{{ $t('promptConfig.writingTipsTitle') }}</strong></p>
                <ul>
                  <li>{{ $t('promptConfig.tip1') }}</li>
                  <li>{{ $t('promptConfig.tip2') }}</li>
                  <li>{{ $t('promptConfig.tip3') }}</li>
                  <li>{{ $t('promptConfig.tip4') }}</li>
                </ul>
              </div>
            </div>

            <div class="form-group">
              <label class="checkbox-label">
                <input
                  v-model="configForm.is_active"
                  type="checkbox">
                <span class="checkmark"></span>
                {{ $t('promptConfig.enableConfig') }}
              </label>
              <div class="checkbox-hint">
                {{ $t('promptConfig.enableHint') }}
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="cancel-btn" @click="closeModals">{{ $t('promptConfig.cancel') }}</button>
              <button
                type="submit"
                class="confirm-btn"
                :disabled="isSaving">
                <span v-if="isSaving">{{ $t('promptConfig.saving') }}</span>
                <span v-else>{{ $t('promptConfig.saveConfig') }}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <div v-if="showPreviewModal" class="preview-modal" @click="closePreview">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>{{ $t('promptConfig.previewTitle', { name: previewConfig.name }) }}</h3>
          <button class="close-btn" @click="closePreview">×</button>
        </div>
        <div class="modal-body">
          <div class="preview-content">
            <div class="preview-meta">
              <div class="meta-item">
                <label>{{ $t('promptConfig.type') }}</label>
                <span class="type-badge" :class="previewConfig.prompt_type">
                  {{ previewConfig.prompt_type === 'writer' ? $t('promptConfig.writerPrompt') : $t('promptConfig.reviewerPrompt') }}
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
        </div>
      </div>
    </div>

    <!-- 默认提示词预览弹窗 -->
    <div v-if="showDefaultsModal" class="defaults-modal" @click="closeDefaultsModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>{{ $t('promptConfig.defaultPromptsPreview') }}</h3>
          <button class="close-btn" @click="closeDefaultsModal">×</button>
        </div>
        <div class="modal-body">
          <div class="defaults-content">
            <div class="tabs">
              <button
                class="tab-btn"
                :class="{ active: activeTab === 'writer' }"
                @click="activeTab = 'writer'">
                {{ $t('promptConfig.writerTab') }}
              </button>
              <button
                class="tab-btn"
                :class="{ active: activeTab === 'reviewer' }"
                @click="activeTab = 'reviewer'">
                {{ $t('promptConfig.reviewerTab') }}
              </button>
            </div>

            <div class="tab-content">
              <div class="content-display">
                <div class="content-text">{{ defaultPrompts[activeTab] || $t('promptConfig.noContent') }}</div>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button class="cancel-btn" @click="closeDefaultsModal">{{ $t('promptConfig.cancel') }}</button>
            <button
              class="confirm-btn"
              @click="confirmLoadDefaults"
              :disabled="isLoadingDefaults">
              <span v-if="isLoadingDefaults">{{ $t('promptConfig.loading') }}</span>
              <span v-else>{{ $t('promptConfig.confirmLoad') }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'PromptConfig',
  data() {
    return {
      configs: [],
      showAddModal: false,
      showEditModal: false,
      showPreviewModal: false,
      showDefaultsModal: false,
      isEditing: false,
      isSaving: false,
      isLoadingDefaults: false,
      editingConfigId: null,
      previewConfig: {},
      defaultPrompts: {
        writer: '',
        reviewer: ''
      },
      activeTab: 'writer',
      configForm: {
        name: '',
        prompt_type: '',
        content: '',
        is_active: true
      }
    }
  },

  mounted() {
    this.loadConfigs()
  },

  methods: {
    openAddModal() {
      console.log('openAddModal clicked')
      this.resetForm()
      this.isEditing = false
      this.showAddModal = true
      console.log('showAddModal set to:', this.showAddModal)
    },

    async loadConfigs() {
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
        console.error(this.$t('promptConfig.loadConfigsFailed'), error)
        this.configs = [] // 确保configs始终是数组

        if (error.response?.status === 401) {
          ElMessage.error(this.$t('promptConfig.pleaseLogin'))
        } else {
          ElMessage.error(this.$t('promptConfig.loadConfigsFailed') + ': ' + (error.response?.data?.error || error.message))
        }
      }
    },

    async loadDefaultPrompts() {
      console.log('loadDefaultPrompts clicked')
      try {
        const response = await api.get('/requirement-analysis/prompts/load_defaults/')
        console.log('Default prompts response:', response.data)
        this.defaultPrompts = response.data.defaults
        this.showDefaultsModal = true
        console.log('showDefaultsModal set to:', this.showDefaultsModal)
      } catch (error) {
        console.error(this.$t('promptConfig.loadDefaultsFailed'), error)
        ElMessage.error(this.$t('promptConfig.loadDefaultsFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    async confirmLoadDefaults() {
      this.isLoadingDefaults = true
      
      try {
        // 创建编写提示词配置
        if (this.defaultPrompts.writer) {
          await api.post('/requirement-analysis/prompts/', {
            name: this.$t('promptConfig.defaultWriterName'),
            prompt_type: 'writer',
            content: this.defaultPrompts.writer,
            is_active: true
          })
        }

        // 创建评审提示词配置
        if (this.defaultPrompts.reviewer) {
          await api.post('/requirement-analysis/prompts/', {
            name: this.$t('promptConfig.defaultReviewerName'),
            prompt_type: 'reviewer',
            content: this.defaultPrompts.reviewer,
            is_active: true
          })
        }

        ElMessage.success(this.$t('promptConfig.defaultsLoadSuccess'))
        this.closeDefaultsModal()
        this.loadConfigs()
      } catch (error) {
        console.error(this.$t('promptConfig.loadDefaultsFailed'), error)
        ElMessage.error(this.$t('promptConfig.loadFailed') + ': ' + (error.response?.data?.error || error.message))
      } finally{
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

    editConfig(config) {
      this.isEditing = true
      this.editingConfigId = config.id
      this.configForm = {
        name: config.name,
        prompt_type: config.prompt_type,
        content: config.content,
        is_active: config.is_active
      }
      this.showEditModal = true
    },

    previewPrompt(config) {
      this.previewConfig = config
      this.showPreviewModal = true
    },

    async saveConfig() {
      this.isSaving = true
      
      try {
        if (this.isEditing) {
          await api.patch(`/requirement-analysis/prompts/${this.editingConfigId}/`, this.configForm)
          ElMessage.success(this.$t('promptConfig.updateSuccess'))
        } else {
          await api.post('/requirement-analysis/prompts/', this.configForm)
          ElMessage.success(this.$t('promptConfig.addSuccess'))
        }

        this.closeModals()
        this.loadConfigs()
      } catch (error) {
        console.error(this.$t('promptConfig.saveConfigFailed'), error)
        ElMessage.error(this.$t('promptConfig.saveFailed') + ': ' + (error.response?.data?.error || error.message))
      } finally {
        this.isSaving = false
      }
    },

    async deleteConfig(configId) {
      if (!confirm(this.$t('promptConfig.deleteConfirm'))) {
        return
      }

      try {
        await api.delete(`/requirement-analysis/prompts/${configId}/`)
        ElMessage.success(this.$t('promptConfig.deleteSuccess'))
        this.loadConfigs()
      } catch (error) {
        console.error(this.$t('promptConfig.deleteConfigFailed'), error)
        ElMessage.error(this.$t('promptConfig.deleteFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    closeModals() {
      this.showAddModal = false
      this.showEditModal = false
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
      this.defaultPrompts = { writer: '', reviewer: '' }
      this.activeTab = 'writer'
    },

    truncateContent(content, maxLength) {
      if (!content) return ''
      if (content.length <= maxLength) return content
      return content.substring(0, maxLength) + '...'
    },

    formatDateTime(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
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
.prompt-config {
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
  content: '📋';
  font-size: 1.2rem;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.load-defaults-btn {
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

.load-defaults-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.3);
}

.load-defaults-btn:disabled {
  background: linear-gradient(135deg, #d1c5f7 0%, #b8a7e8 100%);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
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

.type-badge, .status-badge {
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.8rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.type-badge.writer {
  background: rgba(74, 36, 156, 0.1);
  color: #5a32a3;
  border: 1px solid rgba(147, 112, 219, 0.2);
}

.type-badge.reviewer {
  background: rgba(245, 124, 0, 0.1);
  color: #f57c00;
  border: 1px solid rgba(245, 124, 0, 0.2);
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

.config-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.preview-btn, .edit-btn, .delete-btn {
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

.preview-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: white;
}

.preview-btn:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(147, 112, 219, 0.3);
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
}

.prompt-preview {
  margin-bottom: 16px;
  background: rgba(255, 255, 255, 0.8);
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.1);
}

.prompt-preview label {
  font-size: 0.85rem;
  color: #5a32a3;
  font-weight: 600;
  display: block;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.prompt-preview label::before {
  content: '📝';
  font-size: 0.9rem;
}

.content-preview {
  background: rgba(243, 240, 250, 0.6);
  padding: 14px;
  border-radius: 8px;
  color: #5a32a3;
  font-size: 0.85rem;
  line-height: 1.6;
  border-left: 3px solid #9370db;
  transition: all 0.3s ease;
  max-height: 120px;
  overflow: hidden;
  position: relative;
}

.content-preview:hover {
  background: rgba(243, 240, 250, 0.8);
}

.content-preview::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 30px;
  background: linear-gradient(to top, rgba(243, 240, 250, 0.9), transparent);
  pointer-events: none;
}

.config-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  padding: 16px;
  background: rgba(243, 240, 250, 0.6);
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.1);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-item label {
  font-size: 0.8rem;
  color: #6d5d8f;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.meta-item span {
  color: #5a32a3;
  font-size: 0.85rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.empty-state {
  text-align: center;
  padding: 100px 24px;
  color: #6d5d8f;
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.12);
  border: 1px solid rgba(147, 112, 219, 0.2);
  margin: 0 16px;
}

.empty-icon {
  font-size: 4.5rem;
  margin-bottom: 24px;
}

.empty-state h3 {
  color: #5a32a3;
  margin-bottom: 12px;
  font-size: 1.3rem;
  font-weight: 600;
}

.empty-state p {
  margin-bottom: 32px;
  font-size: 1rem;
  opacity: 0.9;
}

.empty-actions {
  display: flex;
  gap: 20px;
  justify-content: center;
  flex-wrap: wrap;
}

.add-first-config-btn, .load-defaults-first-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: white;
  border: none;
  padding: 16px 32px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 1.1rem;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.2);
}

.add-first-config-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.3);
}

.add-first-config-btn:disabled {
  background: linear-gradient(135deg, #d1c5f7 0%, #b8a7e8 100%);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.load-defaults-first-btn {
  background: linear-gradient(135deg, #9370db 0%, #6d5d8f 100%);
}

.load-defaults-first-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.3);
}

.load-defaults-first-btn:disabled {
  background: linear-gradient(135deg, #d1c5f7 0%, #b8a7e8 100%);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.config-modal, .preview-modal, .defaults-modal {
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
  backdrop-filter: blur(4px);
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 16px;
  padding: 0;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 20px 64px rgba(147, 112, 219, 0.25);
  border: 1px solid rgba(147, 112, 219, 0.2);
  animation: slideIn 0.3s ease;
  position: relative;
  display: flex;
  flex-direction: column;
}

@keyframes slideIn {
  from { 
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-content::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #7b42f6 0%, #5a32a3 100%);
  border-radius: 16px 16px 0 0;
}

.modal-content.large {
  max-width: 900px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.2);
  background: rgba(255, 255, 255, 0.9);
  position: sticky;
  top: 0;
  z-index: 10;
}

.modal-header h3 {
  margin: 0;
  color: #5a32a3;
  font-size: 1.2rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-header h3::before {
  content: '⚙️';
  font-size: 1.1rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6d5d8f;
  transition: all 0.3s ease;
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
}

.close-btn:hover {
  background: rgba(147, 112, 219, 0.1);
  color: #5a32a3;
  transform: rotate(90deg);
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.1);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #5a32a3;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.form-input, .form-select {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid rgba(147, 112, 219, 0.2);
  border-radius: 10px;
  font-size: 0.95rem;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.9);
  color: #5a32a3;
  box-shadow: inset 0 1px 3px rgba(147, 112, 219, 0.1);
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: #9370db;
  box-shadow: 0 0 0 3px rgba(147, 112, 219, 0.25), inset 0 1px 3px rgba(147, 112, 219, 0.1);
  background: rgba(243, 240, 250, 0.8);
}

.textarea-container {
  position: relative;
}

.form-textarea {
  width: 100%;
  padding: 14px 16px;
  border: 2px solid rgba(147, 112, 219, 0.2);
  border-radius: 10px;
  font-size: 0.95rem;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  resize: vertical;
  min-height: 200px;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.9);
  color: #5a32a3;
  line-height: 1.6;
  box-shadow: inset 0 1px 3px rgba(147, 112, 219, 0.1);
}

.form-textarea.large {
  min-height: 400px;
}

.form-textarea:focus {
  outline: none;
  border-color: #9370db;
  box-shadow: 0 0 0 3px rgba(147, 112, 219, 0.25), inset 0 1px 3px rgba(147, 112, 219, 0.1);
  background: rgba(243, 240, 250, 0.8);
}

.char-count {
  text-align: right;
  font-size: 0.8rem;
  color: #6d5d8f;
  margin-top: 8px;
  font-weight: 500;
  background: rgba(243, 240, 250, 0.6);
  padding: 6px 12px;
  border-radius: 6px;
  display: inline-block;
}

.textarea-tips {
  margin-top: 12px;
  padding: 14px;
  background: rgba(243, 240, 250, 0.8);
  border-radius: 10px;
  border-left: 4px solid #9370db;
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.1);
}

.textarea-tips p {
  margin: 0 0 8px 0;
  color: #5a32a3;
  font-weight: 600;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.textarea-tips p::before {
  content: '💡';
  font-size: 0.9rem;
}

.textarea-tips ul {
  margin: 0;
  padding-left: 20px;
}

.textarea-tips li {
  color: #6d5d8f;
  margin-bottom: 4px;
  line-height: 1.5;
  font-size: 0.8rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  font-size: 0.9rem;
  color: #5a32a3;
  padding: 10px 0;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  transform: scale(1.1);
  accent-color: #9370db;
}

.checkbox-hint {
  margin-top: 8px;
  font-size: 0.8rem;
  color: #6d5d8f;
  font-style: italic;
  background: rgba(243, 240, 250, 0.6);
  padding: 8px 12px;
  border-radius: 6px;
}

.required {
  color: #e74c3c;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(147, 112, 219, 0.2);
  flex-wrap: wrap;
}

.cancel-btn {
  background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(149, 165, 166, 0.2);
  display: flex;
  align-items: center;
  gap: 6px;
}

.cancel-btn:hover {
  background: linear-gradient(135deg, #7f8c8d 0%, #6c757d 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(149, 165, 166, 0.3);
}

.confirm-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(147, 112, 219, 0.2);
  display: flex;
  align-items: center;
  gap: 6px;
}

.confirm-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.3);
}

.confirm-btn:disabled {
  background: linear-gradient(135deg, #d1c5f7 0%, #b8a7e8 100%);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.preview-content, .defaults-content {
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

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  border-bottom: 2px solid rgba(147, 112, 219, 0.2);
  border-radius: 8px 8px 0 0;
  overflow: hidden;
}

.tab-btn {
  background: rgba(255, 255, 255, 0.8);
  border: none;
  padding: 14px 24px;
  cursor: pointer;
  color: #6d5d8f;
  font-size: 1rem;
  font-weight: 500;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
  flex: 1;
  text-align: center;
}

.tab-btn.active {
  color: #5a32a3;
  border-bottom-color: #9370db;
  background: rgba(243, 240, 250, 0.9);
  box-shadow: 0 -2px 8px rgba(147, 112, 219, 0.1);
}

.tab-btn:hover {
  background: rgba(243, 240, 250, 0.8);
  color: #5a32a3;
}

@media (max-width: 768px) {
  .prompt-config {
    padding: 16px;
  }
  
  .page-header {
    margin-bottom: 32px;
    padding: 24px 16px;
  }
  
  .page-header h1 {
    font-size: 2rem;
  }
  
  .section-header {
    padding: 0 8px;
    margin-bottom: 24px;
  }
  
  .header-actions {
    flex-direction: column;
    width: 100%;
  }
  
  .load-defaults-btn, .add-config-btn {
    width: 100%;
    justify-content: center;
  }
  
  .configs-grid {
    grid-template-columns: 1fr;
    padding: 0 8px;
    gap: 16px;
  }
  
  .config-card {
    padding: 20px;
  }
  
  .config-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
  
  .config-actions {
    width: 100%;
    justify-content: flex-start;
  }
  
  .empty-state {
    padding: 80px 16px;
    margin: 0 8px;
  }
  
  .empty-actions {
    flex-direction: column;
    align-items: center;
  }
  
  .add-first-config-btn, .load-defaults-first-btn {
    width: 100%;
    max-width: 300px;
  }
  
  .modal-content {
    width: 95%;
    max-height: 95vh;
  }
  
  .modal-header {
    padding: 20px 24px;
  }
  
  .modal-body {
    padding: 24px;
  }
  
  .preview-meta {
    flex-direction: column;
    gap: 12px;
  }
  
  .modal-actions {
    flex-direction: column;
  }
  
  .cancel-btn, .confirm-btn {
    width: 100%;
    justify-content: center;
  }
  
  .tabs {
    flex-direction: column;
  }
  
  .tab-btn {
    border-bottom: 2px solid transparent;
    border-radius: 0;
  }
  
  .tab-btn.active {
    border-bottom-color: transparent;
    border-left: 4px solid #9370db;
  }
}
</style>