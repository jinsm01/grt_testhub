<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">{{ testcase.title || $t('testcase.detail') }}</h1>
      <div class="header-actions">
        <el-button type="primary" class="action-btn edit-btn" @click="$router.push(`/ai-generation/testcases/${testcase.id}/edit`)">
          <el-icon><Edit /></el-icon>
          <span>{{ $t('testcase.edit') }}</span>
        </el-button>
        <el-button type="danger" class="action-btn delete-btn" @click="handleDelete">
          <el-icon><Delete /></el-icon>
          <span>{{ $t('testcase.delete') }}</span>
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="card-container loading-card">
      <el-skeleton :rows="15" animated />
    </div>

    <!-- 详情内容 -->
    <div v-else class="detail-container">
      <!-- 基本信息卡片 -->
      <div class="card-container">
        <div class="card-header">
          <h3 class="card-title">{{ $t('testcase.basicInfo') }}</h3>
          <div class="card-tags">
            <el-tag :type="getReviewStatusType(testcase.review_status)" class="review-tag">
              {{ testcase.review_status_display || '未审核' }}
            </el-tag>
            <el-tag :type="priorityType(testcase.priority)" class="priority-tag">
              {{ priorityLabel(testcase.priority) }}
            </el-tag>
            <el-tag type="info" class="type-tag">
              {{ testTypeLabel(testcase.test_type) }}
            </el-tag>
          </div>
        </div>

        <div class="info-section">
          <el-row :gutter="24" class="info-row">
            <el-col :span="12">
              <div class="info-item">
                <span class="info-label">{{ $t('testcase.relatedProject') }}</span>
                <span class="info-value">{{ testcase.category_path || '-' }}</span>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="info-item">
                <span class="info-label">{{ $t('testcase.moduleLabel') }}</span>
                <span class="info-value">{{ testcase.module || '-' }}</span>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="info-item">
                <span class="info-label">{{ $t('testcase.creator') }}</span>
                <span class="info-value">{{ testcase.author?.username || '-' }}</span>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="info-item">
                <span class="info-label">{{ $t('testcase.createTime') }}</span>
                <span class="info-value">{{ formatDate(testcase.created_at) }}</span>
              </div>
            </el-col>
          </el-row>

          <div class="info-item" v-if="testcase.versions && testcase.versions.length > 0">
            <span class="info-label">{{ $t('testcase.relatedVersions') }}</span>
            <div class="info-value">
              <el-tag
                v-for="version in testcase.versions"
                :key="version.id"
                type="info"
                size="small"
                class="version-tag"
              >
                {{ version.name }}
              </el-tag>
            </div>
          </div>

          <div class="info-item">
            <span class="info-label">关联自动化场景</span>
            <div class="info-value">
              <span
                v-if="testcase.automation_scenario"
                class="scenario-link"
                @click="goToAutomationScenario(testcase.automation_scenario.id)"
              >
                {{ testcase.automation_scenario.name }}
              </span>
              <span v-else class="text-muted">未关联</span>
            </div>
          </div>

        </div>
      </div>

      <!-- 测试执行卡片 -->
      <div class="card-container test-execution-card">
        <div class="card-header">
          <h3 class="card-title card-title-with-icon">
            <el-icon><List /></el-icon>
            <span>测试执行</span>
          </h3>
        </div>

        <!-- 步骤与结果表格 -->
        <div class="steps-table-wrapper">
          <table class="steps-table">
            <thead>
              <tr>
                <th class="col-precondition">前置条件</th>
                <th class="col-step">测试步骤</th>
                <th class="col-expected">预期结果</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(step, index) in parseSteps(testcase.steps)" :key="index">
                <td v-if="index === 0 && testcase.preconditions" class="cell-precondition" :rowspan="parseSteps(testcase.steps).length">
                  <div class="precondition-text">{{ testcase.preconditions }}</div>
                </td>
                <td v-else-if="!testcase.preconditions && index === 0" class="cell-precondition">
                  <span class="muted">无</span>
                </td>
                <td class="cell-step">
                  <div class="step-line">
                    <span class="step-index">{{ Number(index) + 1 }}. </span>
                    <span class="step-text">{{ stripStepPrefix(step) }}</span>
                  </div>
                </td>
                <td class="cell-expected">
                  <div class="expected-line">
                    <span class="expected-index">{{ Number(index) + 1 }}. </span>
                    <span class="expected-text">{{ stripResultPrefix(parseResults(testcase.expected_result)[index]) || '-' }}</span>
                  </div>
                </td>
              </tr>
              <tr v-if="parseSteps(testcase.steps).length === 0">
                <td class="cell-precondition"><span class="muted">无</span></td>
                <td class="cell-step muted">暂无测试步骤</td>
                <td class="cell-expected muted">-</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>

    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Edit, Delete, CircleCheck, List, CircleCheckFilled } from '@element-plus/icons-vue'
import api from '@/utils/api'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const testcase = ref({
  id: null,
  title: '',
  description: '',
  priority: 'medium',
  test_type: 'functional',
  preconditions: '',
  steps: '',
  expected_result: '',
  module: '',
  project: null,
  versions: [],
  author: null,
  created_at: null,
  category_path: '',
  review_status: 'none',
  review_status_display: '未审核',
  review_comment: '',
  reviewer: null,
  automation_scenario: null
})

const priorityType = (priority) => {
  const types = {
    'low': 'success',
    'medium': 'warning',
    'high': 'danger',
    'critical': 'danger'
  }
  return types[priority] || 'info'
}

const getReviewStatusType = (status) => {
  const types = {
    'none': 'info',
    'pending': 'warning',
    'approved': 'success',
    'rejected': 'danger'
  }
  return types[status] || 'info'
}

const priorityLabel = (priority) => {
  const labels = {
    'critical': 'P0',
    'high': 'P1',
    'medium': 'P2',
    'low': 'P3'
  }
  return labels[priority] || priority
}

const testTypeLabel = (type) => {
  const labels = {
    'text': t('testcase.text'),
    'step': t('testcase.step')
  }
  return labels[type] || type
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const goToAutomationScenario = (suiteId) => {
  router.push(`/api-testing/automation/${suiteId}`)
}

const formatContent = (content) => {
  if (!content) return ''
  // Convert <br> tags to actual line breaks for display
  return content.replace(/<br\s*\/?>/gi, '<br>')
}

// 解析步骤文本为数组
const parseSteps = (steps) => {
  if (!steps) return []
  // 按行分割，过滤空行
  return steps.split('\n').map(line => line.trim()).filter(line => line.length > 0)
}

// 解析预期结果为数组
const parseResults = (results) => {
  if (!results) return []
  // 按行分割，过滤空行
  return results.split('\n').map(line => line.trim()).filter(line => line.length > 0)
}

// 去除步骤行首的 "1. " / "1、" 之类的序号前缀
const stripStepPrefix = (text) => {
  if (!text) return ''
  return text.replace(/^\s*\d+\s*[\.\、\)]\s*/, '')
}

// 去除预期结果行首的 "1. " / "1、" 之类的前缀
const stripResultPrefix = (text) => {
  return stripStepPrefix(text)
}

const fetchTestCase = async () => {
  try {
    const response = await api.get(`/testcases/${route.params.id}/`)
    testcase.value = response.data
    loading.value = false
  } catch (error) {
    ElMessage.error(t('testcase.fetchDetailFailed'))
    router.push('/ai-generation/testcases')
  }
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm(
      t('testcase.deleteConfirm'),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    await api.delete(`/testcases/${route.params.id}/`)
    ElMessage.success(t('testcase.deleteSuccess'))
    router.push('/ai-generation/testcases')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('testcase.deleteFailed'))
      console.error('Delete error:', error)
    }
  }
}

onMounted(() => {
  fetchTestCase()
})
</script>

<style lang="scss" scoped>
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 28px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.1);

  .page-title {
    font-size: 24px;
    font-weight: 700;
    color: #5a32a3;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .header-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 28px;

  &.loading-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 400px;
  }
}

.detail-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);

  .card-title {
    font-size: 18px;
    font-weight: 600;
    color: #5a32a3;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;

    &::before {
      content: '';
      width: 4px;
      height: 20px;
      background: linear-gradient(180deg, #7b42f6 0%, #5a32a3 100%);
      border-radius: 2px;
    }

    &.card-title-with-icon {
      &::before {
        display: none;
      }
    }
  }

  .card-tags {
    display: flex;
    gap: 8px;

    .review-tag,
    .priority-tag,
    .type-tag {
      font-weight: 500;
      padding: 4px 12px;
      border-radius: 6px;
      height: 28px;
      line-height: 20px;
    }
  }
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-row {
  margin-bottom: 0;
}

.info-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  overflow: hidden;

  &.title-item {
    padding: 16px 20px;
    background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
    border-radius: 10px;
    border-left: 4px solid #7b42f6;
  }

  .info-label {
    font-size: 13px;
    font-weight: 500;
    color: #7b42f6;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .info-value {
    font-size: 14px;
    color: #333;
    line-height: 1.6;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;

    &.title-value {
      font-size: 18px;
      font-weight: 600;
      color: #5a32a3;
    }

    &.description-value {
      color: #666;
      line-height: 1.8;
    }
  }

  .version-tag {
    margin-right: 8px;
    margin-bottom: 4px;
  }

  .scenario-link {
    color: #7b42f6;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      color: #6d33e6;
      text-decoration: underline;
    }
  }

  .text-muted {
    color: #999;
    font-size: 14px;
  }
}

.info-item-vertical {
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;

  .info-value-block {
    display: block;
    width: 100%;
    white-space: pre-wrap;
    line-height: 1.8;
  }
}

// 测试执行卡片样式
.test-execution-card {
  .steps-table-wrapper {
    width: 100%;
    overflow-x: auto;
    border-radius: 8px;
    border: 1px solid #e8e8e8;
  }

  .steps-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    background: #ffffff;

    thead tr {
      background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);

      th {
        padding: 14px 16px;
        font-size: 14px;
        font-weight: 600;
        color: #5a32a3;
        text-align: left;
        border-bottom: 1px solid rgba(147, 112, 219, 0.15);
        white-space: nowrap;
      }

      .col-precondition {
        width: 22%;
      }

      .col-step {
        width: 39%;
      }

      .col-expected {
        width: 39%;
      }
    }

    tbody tr {
      transition: background 0.2s ease;

      &:hover {
        background: #faf9ff;
      }

      &:not(:last-child) td {
        border-bottom: 1px solid #f0f0f0;
      }
    }

    td {
      padding: 16px;
      font-size: 14px;
      line-height: 1.7;
      color: #333;
      vertical-align: top;
      word-break: break-word;
    }

    .cell-precondition {
      background: #fafbff;
      color: #444;
    }

    .precondition-text {
      white-space: pre-wrap;
      color: #5a32a3;
      font-weight: 500;
    }

    .cell-step {
      .step-line {
        display: flex;
        gap: 8px;
        align-items: flex-start;
      }

      .step-index {
        color: #7b42f6;
        font-weight: 600;
        flex-shrink: 0;
      }

      .step-text {
        color: #333;
        flex: 1;
      }
    }

    .cell-expected {
      .expected-line {
        display: flex;
        gap: 8px;
        align-items: flex-start;
      }

      .expected-index {
        color: #52c41a;
        font-weight: 600;
        flex-shrink: 0;
      }

      .expected-text {
        color: #333;
        flex: 1;
      }
    }

    .muted {
      color: #bbb;
      font-style: italic;
    }
  }
}

@media (max-width: 768px) {
  .test-execution-card {
    .steps-table {
      thead th {
        padding: 10px 8px;
        font-size: 13px;
      }

      td {
        padding: 10px 8px;
        font-size: 13px;
      }
    }
  }
}

.content-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.content-block {
  padding: 20px;
  background: linear-gradient(135deg, #faf9ff 0%, #f5f3ff 100%);
  border-radius: 10px;
  border: 1px solid rgba(147, 112, 219, 0.1);

  .content-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 600;
    color: #5a32a3;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);

    .el-icon {
      font-size: 16px;
      color: #7b42f6;
    }
  }

  .content-value {
    font-size: 14px;
    color: #333;
    line-height: 1.8;
    white-space: pre-wrap;

    &.steps-value {
      background: #ffffff;
      padding: 16px;
      border-radius: 8px;
      border: 1px solid rgba(147, 112, 219, 0.08);
    }

    &.result-value {
      background: linear-gradient(135deg, #f6ffed 0%, #f0f9eb 100%);
      padding: 16px;
      border-radius: 8px;
      border-left: 3px solid #52c41a;
    }
  }
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  padding: 10px 24px !important;
  border-radius: 8px;
  transition: all 0.3s ease;
  min-width: auto !important;

  .el-icon {
    font-size: 16px;
  }

  span {
    font-size: 14px;
  }

  &.edit-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(123, 66, 246, 0.4) !important;
    }

    &:active {
      transform: translateY(0);
    }

    .el-icon,
    span {
      color: #ffffff !important;
    }
  }

  &.cancel-btn {
    border: 1px solid rgba(147, 112, 219, 0.3) !important;
    color: #5a32a3 !important;
    background: #ffffff !important;

    &:hover {
      border-color: #7b42f6 !important;
      color: #7b42f6 !important;
      background: rgba(123, 66, 246, 0.05) !important;
      transform: translateY(-1px);
    }

    .el-icon,
    span {
      color: #5a32a3 !important;
    }
  }

  &.delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(255, 77, 79, 0.3) !important;

    &:hover {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(255, 77, 79, 0.4) !important;
    }

    &:active {
      transform: translateY(0);
    }

    .el-icon,
    span {
      color: #ffffff !important;
    }
  }
}

// 响应式布局
@media (max-width: 1200px) {
  .page-container {
    padding: 16px;
  }

  .page-header {
    padding: 20px;

    .page-title {
      font-size: 20px;
    }
  }

  .card-container {
    padding: 20px;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 12px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 16px;

    .page-title {
      font-size: 18px;
    }

    .header-actions {
      width: 100%;
      flex-wrap: wrap;
    }
  }

  .card-container {
    padding: 16px;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;

    .card-tags {
      width: 100%;
    }
  }

  .info-row {
    .el-col {
      width: 100%;
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }
    }
  }

  .detail-actions {
    flex-direction: column;

    .action-btn {
      width: 100%;
      justify-content: center;
    }
  }
}
</style>
