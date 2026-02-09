<template>
  <div class="dify-config-container">
    <div class="page-header">
      <h1>{{ $t('configuration.dify.title') }}</h1>
      <p>{{ $t('configuration.dify.description') }}</p>
    </div>

    <div class="config-content">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <span>{{ $t('configuration.dify.apiConfig') }}</span>
            <el-tag v-if="currentConfig" type="success">{{ $t('configuration.common.configured') }}</el-tag>
            <el-tag v-else type="info">{{ $t('configuration.common.notConfigured') }}</el-tag>
          </div>
        </template>

        <el-form :model="form" :rules="rules" ref="configForm" label-width="120px">
          <el-form-item :label="$t('configuration.dify.apiUrl')" prop="api_url">
            <el-input
              v-model="form.api_url"
              :placeholder="$t('configuration.dify.apiUrlPlaceholder')"
              clearable
            >
              <template #prepend>
                <el-icon><Link /></el-icon>
              </template>
            </el-input>
            <div class="form-tip">{{ $t('configuration.dify.apiUrlTip') }}</div>
          </el-form-item>

          <el-form-item :label="$t('configuration.dify.apiKey')" prop="api_key">
            <el-input
              v-model="form.api_key"
              type="password"
              :placeholder="currentConfig ? $t('configuration.dify.apiKeyPlaceholderEdit') : $t('configuration.dify.apiKeyPlaceholder')"
              show-password
              clearable
            >
              <template #prepend>
                <el-icon><Key /></el-icon>
              </template>
            </el-input>
            <div class="form-tip">{{ $t('configuration.dify.apiKeyTip') }}</div>
          </el-form-item>

          <el-form-item :label="$t('configuration.dify.enableStatus')" prop="is_active">
            <el-switch v-model="form.is_active" />
            <span class="switch-label">{{ form.is_active ? $t('configuration.common.enabled') : $t('configuration.common.disabled') }}</span>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="testConnection" :loading="testing">
              <el-icon><Connection /></el-icon>
              {{ $t('configuration.dify.testConnection') }}
            </el-button>
            <el-button type="success" @click="saveConfig" :loading="saving">
              <el-icon><Check /></el-icon>
              {{ $t('configuration.common.save') }}
            </el-button>
            <el-button @click="resetForm">
              <el-icon><RefreshLeft /></el-icon>
              {{ $t('configuration.common.reset') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="info-card" v-if="currentConfig">
        <template #header>
          <span>{{ $t('configuration.dify.currentConfig') }}</span>
        </template>
        <el-descriptions :column="1" border>
          <el-descriptions-item :label="$t('configuration.dify.apiUrl')">
            {{ currentConfig.api_url }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.dify.apiKey')">
            {{ currentConfig.api_key_masked || '****' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.common.status')">
            <el-tag :type="currentConfig.is_active ? 'success' : 'info'">
              {{ currentConfig.is_active ? $t('configuration.common.enabled') : $t('configuration.common.disabled') }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.common.createdAt')">
            {{ formatDate(currentConfig.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.common.updatedAt')">
            {{ formatDate(currentConfig.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Link, Key, Connection, Check, RefreshLeft } from '@element-plus/icons-vue'
import api from '@/utils/api'

const { t, locale } = useI18n()

const configForm = ref(null)
const currentConfig = ref(null)
const testing = ref(false)
const saving = ref(false)

const form = ref({
  api_url: '',
  api_key: '',
  is_active: true
})

const rules = computed(() => ({
  api_url: [
    { required: true, message: t('configuration.dify.validation.apiUrlRequired'), trigger: 'blur' },
    { type: 'url', message: t('configuration.dify.validation.apiUrlInvalid'), trigger: 'blur' }
  ],
  api_key: [
    { min: 8, message: t('configuration.dify.validation.apiKeyMinLength'), trigger: 'blur' }
  ]
}))

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString(locale.value === 'zh-cn' ? 'zh-CN' : 'en-US')
}

const loadConfig = async () => {
  try {
    const response = await api.get('/assistant/config/dify/')
    currentConfig.value = response.data
    form.value = {
      api_url: response.data.api_url,
      api_key: '', // Don't populate API key for security
      is_active: response.data.is_active
    }
  } catch (error) {
    if (error.response?.status !== 404) {
      console.error(t('configuration.dify.messages.loadFailed'), error)
    }
  }
}

const testConnection = async () => {
  if (!configForm.value) return

  await configForm.value.validate(async (valid) => {
    if (!valid) return

    testing.value = true
    try {
      const response = await api.post('/assistant/config/dify/test_connection/', {
        api_url: form.value.api_url,
        api_key: form.value.api_key
      })

      if (response.data.success) {
        ElMessage.success(t('configuration.dify.messages.testSuccess'))
      } else {
        ElMessage.error(response.data.error || t('configuration.dify.messages.testFailed'))
      }
    } catch (error) {
      console.error(t('configuration.dify.messages.testFailed'), error)
      ElMessage.error(error.response?.data?.error || t('configuration.dify.messages.testFailed'))
    } finally {
      testing.value = false
    }
  })
}

const saveConfig = async () => {
  if (!configForm.value) return

  await configForm.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      // Prepare data to save
      const dataToSave = {
        api_url: form.value.api_url,
        is_active: form.value.is_active
      }

      // Only send API Key if user entered a new one
      if (form.value.api_key && form.value.api_key.trim()) {
        dataToSave.api_key = form.value.api_key
      }

      if (currentConfig.value) {
        // Update existing config
        await api.patch(`/assistant/config/dify/${currentConfig.value.id}/`, dataToSave)
        ElMessage.success(t('configuration.dify.messages.updateSuccess'))
      } else {
        // Create new config - API key is required
        if (!form.value.api_key || !form.value.api_key.trim()) {
          ElMessage.error(t('configuration.dify.messages.apiKeyRequired'))
          saving.value = false
          return
        }
        await api.post('/assistant/config/dify/', dataToSave)
        ElMessage.success(t('configuration.dify.messages.saveSuccess'))
      }

      // Clear API Key input for security
      form.value.api_key = ''
      await loadConfig()
    } catch (error) {
      console.error(t('configuration.dify.messages.saveFailed'), error)
      ElMessage.error(error.response?.data?.error || t('configuration.dify.messages.saveFailed'))
    } finally {
      saving.value = false
    }
  })
}

const resetForm = () => {
  if (configForm.value) {
    configForm.value.resetFields()
  }
  if (currentConfig.value) {
    form.value = {
      api_url: currentConfig.value.api_url,
      api_key: '',
      is_active: currentConfig.value.is_active
    }
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped lang="scss">
.dify-config-container {
  padding: 20px;
  max-width: 900px;
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

  h1 {
    font-size: 2.2rem;
    color: #5a32a3;
    margin-bottom: 12px;
    font-weight: 700;
    text-shadow: 0 1px 2px rgba(90, 50, 163, 0.1);
    line-height: 1.2;
  }

  p {
    color: #6d5d8f;
    font-size: 1.05rem;
    opacity: 0.9;
    margin: 0;
    line-height: 1.5;
  }
}

.config-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-card, .info-card {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.2);
  overflow: hidden;

  :deep(.el-card__header) {
    background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
    border-bottom: 1px solid rgba(147, 112, 219, 0.15);
    padding: 16px 20px;
  }

  :deep(.el-card__body) {
    padding: 24px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
    color: #5a32a3;
    font-size: 1.1rem;

    span {
      display: flex;
      align-items: center;
      gap: 8px;

      &::before {
        content: '🔧';
        font-size: 1.2rem;
      }
    }
  }
}

.form-tip {
  font-size: 12px;
  color: #6d5d8f;
  margin-top: 4px;
  font-style: italic;
}

.switch-label {
  margin-left: 10px;
  color: #5a32a3;
  font-weight: 500;
}

.el-form-item {
  margin-bottom: 24px;

  :deep(.el-form-item__label) {
    color: #5a32a3;
    font-weight: 600;
  }

  :deep(.el-input__wrapper) {
    border-radius: 10px;
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;

    &:hover {
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.4) inset;
    }

    &.is-focus {
      box-shadow: 0 0 0 1px #7b42f6 inset, 0 0 0 3px rgba(123, 66, 246, 0.15);
    }
  }
}

// 按钮样式优化
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border: none;
  border-radius: 10px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.2);

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(147, 112, 219, 0.3);
  }

  &:disabled {
    background: linear-gradient(135deg, #d1c5f7 0%, #b8a7e8 100%);
  }
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #27ae60 0%, #219a52 100%);
  border: none;
  border-radius: 10px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(39, 174, 96, 0.2);

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #219a52 0%, #1e8449 100%);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(39, 174, 96, 0.3);
  }
}

:deep(.el-descriptions__label) {
  color: #5a32a3;
  font-weight: 600;
  background: rgba(243, 240, 250, 0.6);
}

:deep(.el-descriptions__content) {
  color: #6d5d8f;
}
</style>
