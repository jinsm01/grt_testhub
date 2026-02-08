<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('reviewDetail.title') }}</h1>
      <div>
        <el-button @click="$router.back()">{{ $t('reviewDetail.back') }}</el-button>
        <el-button v-if="canEdit" type="warning" @click="editReview">{{ $t('reviewDetail.edit') }}</el-button>
        <el-button v-if="canReview" type="success" @click="showReviewDialog">{{ $t('reviewDetail.submitReview') }}</el-button>
      </div>
    </div>

    <div v-if="review" class="content-container">
      <!-- 评审基本信息 -->
      <el-card class="info-card">
        <template #header>
          <span class="card-header">{{ $t('reviewDetail.basicInfo') }}</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item :label="$t('reviewDetail.reviewTitle')" :span="2">{{ review.title }}</el-descriptions-item>
          <el-descriptions-item :label="$t('reviewDetail.associatedProject')">
            {{ Array.isArray(review.projects)
                ? review.projects.map(p => p.name).join(', ')
                : (review.projects?.name || $t('reviewDetail.notSet')) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('reviewDetail.creator')">{{ review.creator?.username }}</el-descriptions-item>
          <el-descriptions-item :label="$t('reviewDetail.useTemplate')">
            {{ review.template?.name || $t('reviewDetail.noTemplate') }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('reviewDetail.reviewStatus')">
            <el-tag :type="getStatusType(review.status)">{{ getStatusText(review.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="$t('reviewDetail.priority')">
            <el-tag :class="`priority-tag ${review.priority}`">{{ getPriorityText(review.priority) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="$t('reviewDetail.deadline')">{{ review.deadline ? formatDate(review.deadline) : $t('reviewDetail.none') }}</el-descriptions-item>
          <el-descriptions-item :label="$t('reviewDetail.createdAt')">{{ formatDate(review.created_at) }}</el-descriptions-item>
          <el-descriptions-item :label="$t('reviewDetail.reviewDescription')" :span="2">{{ review.description || $t('reviewDetail.none') }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 评审进度 -->
      <el-card class="progress-card">
        <template #header>
          <span class="card-header">{{ $t('reviewDetail.reviewProgress') }}</span>
        </template>
        <div class="progress-content">
          <div class="progress-stats">
            <div class="stat-item">
              <div class="stat-number">{{ review.assignments?.length || 0 }}</div>
              <div class="stat-label">{{ $t('reviewDetail.reviewers') }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ completedReviews }}</div>
              <div class="stat-label">{{ $t('reviewDetail.completed') }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ pendingReviews }}</div>
              <div class="stat-label">{{ $t('reviewDetail.pendingReview') }}</div>
            </div>
          </div>
          <el-progress
            :percentage="reviewProgress"
            :color="progressColor"
            :stroke-width="8"
            class="main-progress"
          />
        </div>
      </el-card>

      <!-- 评审人员状态 -->
      <el-card class="reviewers-card">
        <template #header>
          <span class="card-header">{{ $t('reviewDetail.reviewersCard') }}</span>
        </template>
        <el-table :data="review.assignments" stripe>
          <el-table-column prop="reviewer.username" :label="$t('reviewDetail.reviewer')" width="150" />
          <el-table-column :label="$t('reviewDetail.reviewerStatus')" width="120">
            <template #default="{ row }">
              <el-tag :type="getAssignmentStatusType(row.status)">
                {{ getAssignmentStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="comment" :label="$t('reviewDetail.reviewerComment')" min-width="200" show-overflow-tooltip />
          <el-table-column v-if="review.template?.checklist?.length" :label="$t('reviewDetail.checklist')" width="150">
            <template #default="{ row }">
              <div v-if="row.checklist_results && Object.keys(row.checklist_results).length > 0" class="checklist-summary">
                <el-tooltip effect="dark" placement="top">
                  <template #content>
                    <div class="checklist-tooltip">
                      <div v-for="(item, index) in review.template.checklist" :key="index" class="checklist-item">
                        <el-icon v-if="row.checklist_results[index] === true" class="pass-icon"><Check /></el-icon>
                        <el-icon v-else-if="row.checklist_results[index] === false" class="fail-icon"><Close /></el-icon>
                        <el-icon v-else class="pending-icon"><QuestionFilled /></el-icon>
                        <span>{{ item }}</span>
                      </div>
                    </div>
                  </template>
                  <span class="checklist-stats">
                    {{ getChecklistStats(row.checklist_results, review.template.checklist) }}
                  </span>
                </el-tooltip>
              </div>
              <span v-else class="no-checklist">{{ $t('reviewDetail.notFilled') }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="assigned_at" :label="$t('reviewDetail.assignedAt')" width="160">
            <template #default="{ row }">
              {{ formatDate(row.assigned_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="reviewed_at" :label="$t('reviewDetail.reviewedAt')" width="160">
            <template #default="{ row }">
              {{ row.reviewed_at ? formatDate(row.reviewed_at) : $t('reviewDetail.pendingReviewTime') }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 评审用例 -->
      <el-card class="testcases-card">
        <template #header>
          <span class="card-header">{{ $t('reviewDetail.reviewTestcases') }} ({{ review.testcases?.length || 0 }})</span>
        </template>
        <el-table :data="review.testcases" stripe>
          <el-table-column prop="title" :label="$t('reviewDetail.testcaseTitle')" min-width="200" show-overflow-tooltip />
          <el-table-column :label="$t('reviewDetail.testType')" width="120">
            <template #default="{ row }">
              {{ getTypeText(row.test_type) }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('reviewDetail.priority')" width="100">
            <template #default="{ row }">
              <el-tag :class="`priority-tag ${row.priority}`">{{ getPriorityText(row.priority) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="author.username" :label="$t('reviewDetail.author')" width="120" />
          <el-table-column :label="$t('reviewList.actions')" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewTestcase(row.id)">{{ $t('reviewDetail.view') }}</el-button>
              <el-button link type="success" @click="addComment(row)">{{ $t('reviewDetail.comment') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 评审意见 -->
      <el-card class="comments-card">
        <template #header>
          <div class="card-header-with-action">
            <span class="card-header">{{ $t('reviewDetail.reviewComments') }}</span>
            <el-button type="primary" size="small" @click="showAddCommentDialog">{{ $t('reviewDetail.addComment') }}</el-button>
          </div>
        </template>
        <div class="comments-list">
          <div
            v-for="comment in review.comments"
            :key="comment.id"
            class="comment-item"
          >
            <div class="comment-header">
              <div class="comment-author">
                <el-avatar :size="32" :src="comment.author.avatar" />
                <span class="author-name">{{ comment.author.username }}</span>
                <el-tag size="small" :type="getCommentTypeColor(comment.comment_type)">
                  {{ getCommentTypeText(comment.comment_type) }}
                </el-tag>
              </div>
              <div class="comment-time">{{ formatDate(comment.created_at) }}</div>
            </div>
            <div class="comment-content">{{ comment.content }}</div>
            <div v-if="comment.testcase" class="comment-testcase">
              {{ $t('reviewDetail.relatedTestcase') }}: {{ comment.testcase.title }}
            </div>
          </div>
          <div v-if="!review.comments?.length" class="empty-comments">
            {{ $t('reviewDetail.noComments') }}
          </div>
        </div>
      </el-card>
    </div>

    <!-- 提交评审对话框 -->
    <el-dialog v-model="reviewDialogVisible" :title="$t('reviewDetail.submitReviewDialog')" :close-on-click-modal="false" :close-on-press-escape="false" :modal="true" :destroy-on-close="false" width="800px">
      <el-form :model="reviewForm" label-width="100px">
        <el-form-item :label="$t('reviewDetail.reviewResult')" required>
          <el-radio-group v-model="reviewForm.status">
            <el-radio-button label="approved">{{ $t('reviewDetail.approved') }}</el-radio-button>
            <el-radio-button label="rejected">{{ $t('reviewDetail.rejected') }}</el-radio-button>
            <el-radio-button label="abstained">{{ $t('reviewDetail.abstained') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 模板检查清单 -->
        <el-form-item v-if="review?.template?.checklist?.length" :label="$t('reviewDetail.checklist')" class="checklist-form-item">
          <div class="checklist-container">
            <div class="checklist-header">
              <span class="checklist-title">{{ review.template.name }} - {{ $t('reviewDetail.checklistTitle') }}</span>
              <div class="checklist-actions">
                <el-button size="small" @click="checkAll(true)">{{ $t('reviewDetail.allPass') }}</el-button>
                <el-button size="small" @click="checkAll(false)">{{ $t('reviewDetail.allFail') }}</el-button>
              </div>
            </div>
            <div class="checklist-items">
              <div
                v-for="(item, index) in review.template.checklist"
                :key="index"
                class="checklist-item"
              >
                <div class="item-content">
                  <span class="item-text">{{ item }}</span>
                </div>
                <div class="item-controls">
                  <el-radio-group v-model="reviewForm.checklist_results[index]">
                    <el-radio-button :label="true">{{ $t('reviewDetail.approved') }}</el-radio-button>
                    <el-radio-button :label="false">{{ $t('reviewDetail.rejected') }}</el-radio-button>
                  </el-radio-group>
                </div>
              </div>
            </div>
          </div>
        </el-form-item>

        <el-form-item :label="$t('reviewDetail.reviewCommentLabel')">
          <el-input
            v-model="reviewForm.comment"
            type="textarea"
            :rows="4"
            :placeholder="$t('reviewDetail.reviewCommentPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">{{ $t('reviewDetail.cancel') }}</el-button>
        <el-button type="primary" @click="submitReview">{{ $t('reviewDetail.submit') }}</el-button>
      </template>
    </el-dialog>

    <!-- 添加意见对话框 -->
    <el-dialog v-model="commentDialogVisible" :title="$t('reviewDetail.addCommentDialog')" :close-on-click-modal="false" width="600px">
      <el-form :model="commentForm" label-width="100px">
        <el-form-item :label="$t('reviewDetail.commentType')" required>
          <el-radio-group v-model="commentForm.comment_type">
            <el-radio-button label="general">{{ $t('reviewDetail.generalComment') }}</el-radio-button>
            <el-radio-button label="testcase">{{ $t('reviewDetail.testcaseComment') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="commentForm.comment_type === 'testcase'" :label="$t('reviewDetail.relatedTestcaseLabel')">
          <el-select v-model="commentForm.testcase" :placeholder="$t('reviewDetail.selectTestcase')">
            <el-option
              v-for="testcase in review.testcases"
              :key="testcase.id"
              :label="testcase.title"
              :value="testcase.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('reviewDetail.commentContent')" required>
          <el-input
            v-model="commentForm.content"
            type="textarea"
            :rows="4"
            :placeholder="$t('reviewDetail.commentContentPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="commentDialogVisible = false">{{ $t('reviewDetail.cancel') }}</el-button>
        <el-button type="primary" @click="addCommentSubmit">{{ $t('reviewDetail.submit') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Check, Close, QuestionFilled } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { t } = useI18n()

const review = ref(null)
const reviewDialogVisible = ref(false)
const commentDialogVisible = ref(false)

const reviewForm = reactive({
  status: 'approved',
  comment: '',
  checklist_results: {}
})

const commentForm = reactive({
  comment_type: 'general',
  testcase: '',
  content: ''
})

const completedReviews = computed(() => {
  return review.value?.assignments?.filter(a => a.status !== 'pending').length || 0
})

const pendingReviews = computed(() => {
  return review.value?.assignments?.filter(a => a.status === 'pending').length || 0
})

const reviewProgress = computed(() => {
  const total = review.value?.assignments?.length || 0
  if (total === 0) return 0
  return Math.round((completedReviews.value / total) * 100)
})

const progressColor = computed(() => {
  const progress = reviewProgress.value
  if (progress === 100) return '#67c23a'
  if (progress >= 50) return '#e6a23c'
  return '#f56c6c'
})

const canEdit = computed(() => {
  return review.value?.creator?.id === userStore.user?.id &&
         ['pending', 'in_progress'].includes(review.value?.status)
})

const canReview = computed(() => {
  return review.value?.assignments?.some(a =>
    a.reviewer.id === userStore.user?.id && a.status === 'pending'
  )
})

const fetchReview = async () => {
  try {
    const response = await api.get(`/reviews/reviews/${route.params.id}/`)
    review.value = response.data
  } catch (error) {
    ElMessage.error(t('reviewDetail.fetchDetailFailed'))
    router.push('/ai-generation/reviews')
  }
}

const editReview = () => {
  router.push(`/ai-generation/reviews/${route.params.id}/edit`)
}

const showReviewDialog = () => {
  reviewForm.status = 'approved'
  reviewForm.comment = ''
  reviewForm.checklist_results = {}

  // 如果有模板检查清单，初始化检查清单结果
  if (review.value?.template?.checklist?.length) {
    review.value.template.checklist.forEach((item, index) => {
      reviewForm.checklist_results[index] = null
    })
  }

  reviewDialogVisible.value = true
}

const submitReview = async () => {
  try {
    await api.post(`/reviews/reviews/${route.params.id}/submit_review/`, reviewForm)
    ElMessage.success(t('reviewDetail.submitSuccess'))
    reviewDialogVisible.value = false
    fetchReview()
  } catch (error) {
    ElMessage.error(t('reviewDetail.submitFailed'))
  }
}

const showAddCommentDialog = () => {
  commentForm.comment_type = 'general'
  commentForm.testcase = ''
  commentForm.content = ''
  commentDialogVisible.value = true
}

const addComment = (testcase) => {
  commentForm.comment_type = 'testcase'
  commentForm.testcase = testcase.id
  commentForm.content = ''
  commentDialogVisible.value = true
}

const addCommentSubmit = async () => {
  if (!commentForm.content) {
    ElMessage.warning(t('reviewDetail.commentRequired'))
    return
  }

  try {
    const data = {
      review: review.value.id,
      comment_type: commentForm.comment_type,
      content: commentForm.content
    }

    if (commentForm.comment_type === 'testcase' && commentForm.testcase) {
      data.testcase = commentForm.testcase
    }

    await api.post('/reviews/review-comments/', data)
    ElMessage.success(t('reviewDetail.addCommentSuccess'))
    commentDialogVisible.value = false
    fetchReview()
  } catch (error) {
    console.error('Add comment failed:', error)
    ElMessage.error(t('reviewDetail.addCommentFailed'))
  }
}

const viewTestcase = (id) => {
  router.push(`/ai-generation/testcases/${id}`)
}

const getStatusType = (status) => {
  const typeMap = {
    pending: 'warning',
    in_progress: 'primary',
    approved: 'success',
    rejected: 'danger',
    cancelled: 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    pending: t('reviewDetail.assignmentPending'),
    in_progress: t('reviewList.statusInProgress'),
    approved: t('reviewDetail.assignmentApproved'),
    rejected: t('reviewDetail.assignmentRejected'),
    cancelled: t('reviewList.statusCancelled')
  }
  return textMap[status] || status
}

const getAssignmentStatusType = (status) => {
  const typeMap = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    abstained: 'info'
  }
  return typeMap[status] || 'info'
}

const getAssignmentStatusText = (status) => {
  const textMap = {
    pending: t('reviewDetail.assignmentPending'),
    approved: t('reviewDetail.assignmentApproved'),
    rejected: t('reviewDetail.assignmentRejected'),
    abstained: t('reviewDetail.assignmentAbstained')
  }
  return textMap[status] || status
}

const getPriorityText = (priority) => {
  const textMap = {
    low: t('reviewList.priorityLow'),
    medium: t('reviewList.priorityMedium'),
    high: t('reviewList.priorityHigh'),
    critical: t('reviewList.priorityCritical'),
    urgent: t('reviewList.priorityCritical')
  }
  return textMap[priority] || priority
}

const getTypeText = (type) => {
  const textMap = {
    functional: t('reviewDetail.testTypeFunctional'),
    integration: t('reviewDetail.testTypeIntegration'),
    api: t('reviewDetail.testTypeApi'),
    ui: t('reviewDetail.testTypeUi'),
    performance: t('reviewDetail.testTypePerformance'),
    security: t('reviewDetail.testTypeSecurity')
  }
  return textMap[type] || '-'
}

const getCommentTypeColor = (type) => {
  const colorMap = {
    general: 'primary',
    testcase: 'success',
    step: 'warning'
  }
  return colorMap[type] || 'info'
}

const getCommentTypeText = (type) => {
  const textMap = {
    general: t('reviewDetail.commentTypeGeneral'),
    testcase: t('reviewDetail.commentTypeTestcase'),
    step: t('reviewDetail.commentTypeStep')
  }
  return textMap[type] || '-'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

// 检查清单相关方法
const checkAll = (value) => {
  if (review.value?.template?.checklist?.length) {
    review.value.template.checklist.forEach((item, index) => {
      reviewForm.checklist_results[index] = value
    })
  }
}

const getChecklistStats = (checklistResults, checklist) => {
  if (!checklistResults || !checklist) return '0/0'

  const total = checklist.length
  const passed = Object.values(checklistResults).filter(result => result === true).length
  const failed = Object.values(checklistResults).filter(result => result === false).length

  return `${t('reviewDetail.checklistPass')}: ${passed}, ${t('reviewDetail.checklistFail')}: ${failed}, ${t('reviewDetail.checklistTotal')}: ${total}`
}

onMounted(() => {
  fetchReview()
})
</script>

<style lang="scss" scoped>
// 页面容器
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

// 页面头部
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

  // 按钮样式
  .el-button {
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 500;
    font-size: 14px;
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-1px);
    }

    // 返回按钮
    &:not(.el-button--primary):not(.el-button--success):not(.el-button--warning) {
      border: 1px solid rgba(147, 112, 219, 0.3);
      color: #5a32a3;
      background: #ffffff;

      &:hover {
        border-color: #7b42f6;
        color: #7b42f6;
        background: rgba(123, 66, 246, 0.05);
      }
    }

    // 编辑按钮
    &.el-button--warning {
      background: linear-gradient(135deg, #faad14 0%, #d48806 100%);
      border: none;
      color: white;
      box-shadow: 0 4px 12px rgba(250, 173, 20, 0.3);

      &:hover {
        background: linear-gradient(135deg, #ffc53d 0%, #faad14 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(250, 173, 20, 0.4);
      }
    }

    // 提交评审按钮
    &.el-button--success {
      background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
      border: none;
      color: white;
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.3);

      &:hover {
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(82, 196, 26, 0.4);
      }
    }
  }
}

// 内容容器
.content-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

// 卡片样式
:deep(.el-card) {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  overflow: hidden;

  .el-card__header {
    padding: 16px 24px;
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);

    .card-header {
      font-weight: 600;
      font-size: 16px;
      color: #5a32a3;
    }

    .card-header-with-action {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .el-card__body {
    padding: 24px;
  }
}

// 描述列表样式
:deep(.el-descriptions) {
  .el-descriptions__label {
    color: #5a32a3;
    font-weight: 500;
    background: #f8f7ff;
  }

  .el-descriptions__content {
    color: #333;
  }
}

// 标签样式
:deep(.el-tag) {
  border-radius: 4px;
  font-weight: 500;

  &.priority-tag {
    &.low { 
      background: rgba(82, 196, 26, 0.1);
      color: #52c41a;
      border-color: rgba(82, 196, 26, 0.2);
    }
    &.medium { 
      background: rgba(250, 173, 20, 0.1);
      color: #faad14;
      border-color: rgba(250, 173, 20, 0.2);
    }
    &.high { 
      background: rgba(255, 77, 79, 0.1);
      color: #ff4d4f;
      border-color: rgba(255, 77, 79, 0.2);
    }
    &.critical { 
      background: rgba(255, 77, 79, 0.15);
      color: #ff4d4f;
      border-color: rgba(255, 77, 79, 0.3);
      font-weight: 600;
    }
    &.urgent { 
      background: rgba(255, 77, 79, 0.15);
      color: #ff4d4f;
      border-color: rgba(255, 77, 79, 0.3);
      font-weight: 600;
    }
  }
}

// 进度卡片样式
.progress-content {
  .progress-stats {
    display: flex;
    justify-content: space-around;
    margin-bottom: 24px;
    padding: 20px;
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    border-radius: 8px;
    border: 1px solid rgba(147, 112, 219, 0.1);

    .stat-item {
      text-align: center;

      .stat-number {
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 8px;
      }

      .stat-label {
        color: #666;
        font-size: 14px;
        font-weight: 500;
      }
    }
  }

  .main-progress {
    margin-top: 16px;

    :deep(.el-progress-bar__outer) {
      background-color: rgba(147, 112, 219, 0.1);
      border-radius: 4px;
    }

    :deep(.el-progress-bar__inner) {
      border-radius: 4px;
    }
  }
}

// 表格样式
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;

  .el-table__header-wrapper {
    th {
      background-color: #f8f7ff !important;
      color: #5a32a3;
      font-weight: 600;
    }
  }

  .el-table__row {
    transition: all 0.3s ease;

    &:hover {
      background-color: #f8f7ff !important;
    }
  }
}

// 评论列表样式
.comments-list {
  .comment-item {
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);
    padding: 20px 0;

    &:last-child {
      border-bottom: none;
    }

    .comment-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;

      .comment-author {
        display: flex;
        align-items: center;
        gap: 8px;

        .author-name {
          font-weight: 500;
        }
      }

      .comment-time {
        color: #909399;
        font-size: 12px;
      }
    }

    .comment-content {
      margin-bottom: 8px;
      line-height: 1.6;
    }

    .comment-testcase {
      color: #409eff;
      font-size: 12px;
    }
  }

  .empty-comments {
    text-align: center;
    color: #909399;
    padding: 40px;
  }
}

// 检查清单样式
.checklist-summary {
  .checklist-stats {
    font-size: 12px;
    color: #5a32a3;
    cursor: pointer;
    font-weight: 500;
  }
}

.no-checklist {
  color: #999;
  font-size: 12px;
}

.checklist-tooltip {
  .checklist-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;

    .pass-icon {
      color: #52c41a;
    }

    .fail-icon {
      color: #ff4d4f;
    }

    .pending-icon {
      color: #999;
    }
  }
}

// 提交评审对话框中的检查清单样式
.checklist-form-item {
  .checklist-container {
    border: 1px solid rgba(147, 112, 219, 0.2);
    border-radius: 8px;
    overflow: hidden;

    .checklist-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
      border-bottom: 1px solid rgba(147, 112, 219, 0.15);

      .checklist-title {
        font-weight: 600;
        color: #5a32a3;
      }

      .checklist-actions {
        display: flex;
        gap: 8px;

        .el-button {
          border-radius: 4px;
        }
      }
    }

    .checklist-items {
      padding: 16px;

      .checklist-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid rgba(147, 112, 219, 0.1);

        &:last-child {
          border-bottom: none;
        }

        .item-content {
          flex: 1;

          .item-text {
            color: #333;
            line-height: 1.6;
          }
        }

        .item-controls {
          margin-left: 16px;
        }
      }
    }
  }
}

// 对话框样式
:deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.15);
  border: 1px solid rgba(147, 112, 219, 0.1);

  .el-dialog__header {
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    padding: 20px 24px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);
    margin: 0;

    .el-dialog__title {
      color: #5a32a3;
      font-weight: 600;
      font-size: 16px;
    }
  }

  .el-dialog__body {
    padding: 24px;
    background: #ffffff;
  }

  .el-dialog__footer {
    padding: 16px 24px;
    border-top: 1px solid rgba(147, 112, 219, 0.1);
    background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);

    .dialog-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
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

  :deep(.el-card) {
    .el-card__body {
      padding: 20px;
    }
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
  }

  .progress-content {
    .progress-stats {
      flex-direction: column;
      gap: 16px;
    }
  }
}
</style>
