<template>
  <el-drawer
    v-model="visible"
    :title="$t('uiAutomation.ai.elementLocator.title')"
    size="900px"
    direction="rtl"
    destroy-on-close
  >
    <div v-if="loading" class="loading-container">
      <el-loading-directive />
    </div>
    
    <div v-else-if="error" class="error-container">
      <el-alert
        :title="error"
        type="error"
        show-icon
        :closable="false"
      />
    </div>
    
    <div v-else-if="!elementData" class="empty-container">
      <el-empty :description="$t('uiAutomation.ai.elementLocator.noData')" />
    </div>
    
    <div v-else class="element-locator-container">
      <div class="header-info">
        <div class="info-item">
          <strong>{{ $t('uiAutomation.ai.elementLocator.executionId') }}:</strong>
          <span>{{ elementData.execution_id }}</span>
        </div>
        <div class="info-item">
          <strong>{{ $t('uiAutomation.ai.elementLocator.caseName') }}:</strong>
          <span>{{ elementData.case_name }}</span>
        </div>
        <div class="info-item">
          <strong>{{ $t('uiAutomation.ai.elementLocator.totalElements') }}:</strong>
          <el-tag type="primary">{{ elementData.total_elements }}</el-tag>
        </div>
      </div>
      
      <div v-if="elementData.elements && elementData.elements.length > 0" class="elements-list">
        <el-collapse v-model="activeNames" accordion>
          <el-collapse-item
            v-for="(element, index) in elementData.elements"
            :key="index"
            :name="index"
          >
            <template #title>
              <div class="element-title">
                <span class="step-number">
                  {{ $t('uiAutomation.ai.elementLocator.step') }} {{ element.step_number }}
                </span>
                <span v-if="element.element_name" class="element-name">
                  {{ element.element_name }}
                </span>
                <el-tag v-if="element.locator_strategy" size="small" type="info">
                  {{ element.locator_strategy }}
                </el-tag>
                <el-tag v-else size="small" type="warning">
                  文本定位
                </el-tag>
              </div>
            </template>
            
            <div class="element-detail">
              <div v-if="element.description" class="detail-row">
                <label>{{ $t('uiAutomation.ai.elementLocator.description') }}:</label>
                <span>{{ element.description }}</span>
              </div>
              
              <div v-if="element.element_name" class="detail-row">
                <label>{{ $t('uiAutomation.ai.elementLocator.elementName') }}:</label>
                <span>{{ element.element_name }}</span>
              </div>
              
              <div v-if="element.locator_strategy" class="detail-row">
                <label>{{ $t('uiAutomation.ai.elementLocator.locatorStrategy') }}:</label>
                <el-tag size="small">{{ element.locator_strategy }}</el-tag>
              </div>
              
              <div v-if="element.locator_value" class="detail-row">
                <label>{{ $t('uiAutomation.ai.elementLocator.locatorValue') }}:</label>
                <div class="locator-value">
                  <code>{{ element.locator_value }}</code>
                  <el-button
                    size="small"
                    type="primary"
                    link
                    @click="copyLocatorValue(element.locator_value)"
                  >
                    <el-icon><DocumentCopy /></el-icon>
                    {{ $t('uiAutomation.common.copy') }}
                  </el-button>
                </div>
              </div>
              
              <div v-if="element.action_type" class="detail-row">
                <label>{{ $t('uiAutomation.ai.elementLocator.actionType') }}:</label>
                <span>{{ element.action_type }}</span>
              </div>
              
              <div v-if="element.code_samples" class="code-samples-section">
                <label>代码示例:</label>
                <div class="code-container">
                  <pre><code>{{ element.code_samples.playwright }}</code></pre>
                  <el-button
                    size="small"
                    type="primary"
                    link
                    class="copy-code-btn"
                    @click="copyCode(element.code_samples.playwright)"
                  >
                    <el-icon><DocumentCopy /></el-icon>
                    {{ $t('uiAutomation.common.copy') }}
                  </el-button>
                </div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
      
      <div v-else class="no-elements">
        <el-empty :description="$t('uiAutomation.ai.elementLocator.noElements')" />
      </div>
    </div>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">{{ $t('uiAutomation.common.close') }}</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'
import { extractElementsFromAIExecution } from '@/api/ui_automation'

const { t } = useI18n()

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  recordId: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(false)
const loading = ref(false)
const error = ref(null)
const elementData = ref(null)
const activeNames = ref([])

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val && props.recordId) {
    loadElementData()
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
  if (!val) {
    resetData()
  }
})

const loadElementData = async () => {
  if (!props.recordId) return
  
  loading.value = true
  error.value = null
  
  try {
    const response = await extractElementsFromAIExecution(props.recordId)
    elementData.value = response.data
    

  } catch (err) {
    console.error('Failed to load element data:', err)
    error.value = err.response?.data?.error || err.message || t('uiAutomation.ai.elementLocator.loadError')
  } finally {
    loading.value = false
  }
}

const copyLocatorValue = async (value) => {
  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success(t('common.copySuccess'))
  } catch (err) {
    console.error('Failed to copy:', err)
    ElMessage.error(t('common.copyFailed'))
  }
}

const copyCode = async (code) => {
  try {
    await navigator.clipboard.writeText(code)
    ElMessage.success(t('uiAutomation.ai.elementLocator.copySuccess'))
  } catch (err) {
    console.error('Failed to copy code:', err)
    ElMessage.error(t('uiAutomation.ai.elementLocator.copyFailed'))
  }
}

const handleClose = () => {
  visible.value = false
}

const resetData = () => {
  elementData.value = null
  error.value = null
  activeNames.value = []
}
</script>

<style scoped>
.loading-container {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-container,
.empty-container,
.no-elements {
  padding: 40px 0;
}

.header-info {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item strong {
  color: #606266;
}

.elements-list {
  margin-top: 20px;
}

.element-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.step-number {
  font-weight: 600;
  color: #409eff;
}

.element-name {
  color: #303133;
  font-weight: 500;
}

.element-detail {
  padding: 10px 0;
}

.detail-row {
  display: flex;
  margin-bottom: 12px;
  align-items: flex-start;
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-row label {
  width: 120px;
  font-weight: 500;
  color: #606266;
  flex-shrink: 0;
}

.detail-row span {
  color: #303133;
  flex: 1;
  word-break: break-word;
}

.locator-value {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.locator-value code {
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  color: #303133;
  word-break: break-all;
  flex: 1;
}

.code-samples-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.code-samples-section label {
  width: 120px;
  font-weight: 500;
  color: #606266;
  flex-shrink: 0;
  margin-bottom: 12px;
  display: block;
}

.code-container {
  position: relative;
  background-color: #1e1e1e;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

.code-container pre {
  margin: 0;
}

.code-container code {
  color: #d4d4d4;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.copy-code-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  color: #a0a0a0;
}

.copy-code-btn:hover {
  color: #409eff;
}
</style>
