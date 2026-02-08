<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('reviewList.title') }}</h1>
      <div>
        <el-button type="primary" class="create-review-btn" @click="createReview">
          <el-icon><Plus /></el-icon>
          {{ $t('reviewList.createReview') }}
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item :label="$t('reviewList.project')">
          <el-select v-model="filters.project" :placeholder="$t('reviewList.selectProject')" clearable @change="fetchReviews">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('reviewList.status')">
          <el-select v-model="filters.status" :placeholder="$t('reviewList.selectStatus')" clearable @change="fetchReviews">
            <el-option :label="$t('reviewList.statusPending')" value="pending" />
            <el-option :label="$t('reviewList.statusInProgress')" value="in_progress" />
            <el-option :label="$t('reviewList.statusApproved')" value="approved" />
            <el-option :label="$t('reviewList.statusRejected')" value="rejected" />
            <el-option :label="$t('reviewList.statusCancelled')" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('reviewList.reviewer')">
          <el-select v-model="filters.reviewer" :placeholder="$t('reviewList.selectReviewer')" clearable @change="fetchReviews">
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <div class="table-container">
      <el-table :data="reviews" v-loading="loading" stripe>
        <el-table-column prop="title" :label="$t('reviewList.reviewTitle')" min-width="200" show-overflow-tooltip header-align="center" align="center" />
        <el-table-column :label="$t('reviewList.reviewProject')" width="200" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.projects && row.projects.length > 0">
              {{ row.projects.map(p => p.name).join(', ') }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('reviewList.reviewStatus')" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('reviewList.priority')" width="100" header-align="center" align="center">
          <template #default="{ row }">
            <el-tag :class="`priority-tag ${row.priority}`">{{ getPriorityText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator.username" :label="$t('reviewList.creator')" width="120" header-align="center" align="center" />
        <el-table-column :label="$t('reviewList.testcaseCount')" width="100" header-align="center" align="center">
          <template #default="{ row }">
            {{ row.testcases?.length || 0 }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('reviewList.progress')" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <el-progress
              :percentage="getReviewProgress(row)"
              :color="getProgressColor(row)"
              :stroke-width="6"
            />
          </template>
        </el-table-column>
        <el-table-column prop="deadline" :label="$t('reviewList.deadline')" width="160" header-align="center" align="center">
          <template #default="{ row }">
            {{ row.deadline ? formatDate(row.deadline) : $t('reviewList.noDeadline') }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="$t('reviewList.createdAt')" width="160" header-align="center" align="center">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('reviewList.actions')" width="200" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewReview(row.id)">{{ $t('reviewList.detail') }}</el-button>
            <el-button v-if="canReview(row)" link type="success" @click="submitReview(row)">{{ $t('reviewList.review') }}</el-button>
            <el-button v-if="canEdit(row)" link type="warning" @click="editReview(row.id)">{{ $t('reviewList.edit') }}</el-button>
            <el-button v-if="canDelete(row)" link type="danger" @click="handleDelete(row.id)">{{ $t('reviewList.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchReviews"
          @current-change="fetchReviews"
        />
      </div>
    </div>

    <!-- 评审对话框 -->
    <el-dialog v-model="reviewDialogVisible" :title="$t('reviewList.submitReview')" width="600px">
      <el-form :model="reviewForm" label-width="80px">
        <el-form-item :label="$t('reviewList.reviewResult')" required>
          <el-radio-group v-model="reviewForm.status">
            <el-radio-button label="approved">{{ $t('reviewList.approved') }}</el-radio-button>
            <el-radio-button label="rejected">{{ $t('reviewList.rejected') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('reviewList.reviewComment')">
          <el-input
            v-model="reviewForm.comment"
            type="textarea"
            :rows="4"
            :placeholder="$t('reviewList.reviewCommentPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">{{ $t('reviewList.cancel') }}</el-button>
        <el-button type="primary" @click="confirmSubmitReview">{{ $t('reviewList.submit') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const { t } = useI18n()

const reviews = ref([])
const projects = ref([])
const users = ref([])
const loading = ref(false)
const reviewDialogVisible = ref(false)
const currentReview = ref(null)

const filters = reactive({
  project: '',
  status: '',
  reviewer: ''
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const reviewForm = reactive({
  status: 'approved',
  comment: ''
})

const fetchReviews = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.size,
      ...filters
    }
    Object.keys(params).forEach(key => params[key] === '' && delete params[key])

    const response = await api.get('/reviews/reviews/', { params })
    reviews.value = response.data.results
    pagination.total = response.data.count
  } catch (error) {
    ElMessage.error(t('reviewList.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data || []
  } catch (error) {
    console.error('获取项目列表失败:', error)
  }
}

const fetchUsers = async () => {
  try {
    const response = await api.get('/auth/users/')
    users.value = response.data.results || response.data || []
  } catch (error) {
    console.error('获取用户列表失败:', error)
  }
}

const createReview = () => {
  router.push('/ai-generation/reviews/create')
}

const viewReview = (id) => {
  router.push(`/ai-generation/reviews/${id}`)
}

const editReview = (id) => {
  router.push(`/ai-generation/reviews/${id}/edit`)
}

const submitReview = (review) => {
  currentReview.value = review
  reviewForm.status = 'approved'
  reviewForm.comment = ''
  reviewDialogVisible.value = true
}

const confirmSubmitReview = async () => {
  try {
    await api.post(`/reviews/reviews/${currentReview.value.id}/submit_review/`, reviewForm)
    ElMessage.success(t('reviewList.submitSuccess'))
    reviewDialogVisible.value = false
    fetchReviews()
  } catch (error) {
    ElMessage.error(t('reviewList.submitFailed'))
  }
}

const handleDelete = (id) => {
  ElMessageBox.confirm(t('reviewList.deleteConfirm'), t('common.warning'), {
    confirmButtonText: t('common.confirm'),
    cancelButtonText: t('common.cancel'),
    type: 'warning',
    center: true
  }).then(() => {
    deleteReview(id)
  }).catch(() => {
    // 用户取消删除
  })
}

const deleteReview = async (id) => {
  try {
    await api.delete(`/reviews/reviews/${id}/`)
    ElMessage.success(t('reviewList.deleteSuccess'))
    fetchReviews()
  } catch (error) {
    ElMessage.error(t('reviewList.deleteFailed'))
  }
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
    pending: t('reviewList.statusPending'),
    in_progress: t('reviewList.statusInProgress'),
    approved: t('reviewList.statusApproved'),
    rejected: t('reviewList.statusRejected'),
    cancelled: t('reviewList.statusCancelled')
  }
  return textMap[status] || status
}

const getPriorityText = (priority) => {
  const textMap = {
    low: t('reviewList.priorityLow'),
    medium: t('reviewList.priorityMedium'),
    high: t('reviewList.priorityHigh'),
    urgent: t('reviewList.priorityCritical')
  }
  return textMap[priority] || priority
}

const getReviewProgress = (review) => {
  const assignments = review.assignments || []
  if (assignments.length === 0) return 0
  
  const completedCount = assignments.filter(a => a.status !== 'pending').length
  return Math.round((completedCount / assignments.length) * 100)
}

const getProgressColor = (review) => {
  const progress = getReviewProgress(review)
  if (progress === 100) return '#67c23a'
  if (progress >= 50) return '#e6a23c'
  return '#f56c6c'
}

const canReview = (review) => {
  return review.assignments?.some(a => a.reviewer.id === userStore.user?.id && a.status === 'pending')
}

const canEdit = (review) => {
  return review.creator.id === userStore.user?.id && ['pending', 'in_progress'].includes(review.status)
}

const canDelete = (review) => {
  return review.creator.id === userStore.user?.id && review.status !== 'pending'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

onMounted(() => {
  fetchReviews()
  fetchProjects()
  fetchUsers()
})
</script>

<style lang="scss" scoped>
// 全局变量
:root {
  --primary-color: #667eea;
  --primary-dark: #764ba2;
  --primary-light: #f8f7ff;
  --primary-lighter: #fafbff;
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

// 页面容器
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  line-height: 24px;
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
  
  .create-review-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;
    
    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 20px rgba(123, 66, 246, 0.4) !important;
    }
    
    &:active {
      transform: translateY(0) !important;
    }
  }
}

// 筛选栏样式已在全局样式文件 filter-components.scss 中定义
// 这里只保留特定于本页面的额外样式
.filter-bar {
  /* 本页面特定的筛选栏样式可以在这里添加 */
}

// 表格容器
.table-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;

  // 表格样式
  .el-table {
    border: none;
    border-radius: 8px 8px 0 0;
    overflow: hidden;
    min-height: 200px;
    box-shadow: none;
    transition: all 0.3s ease;
    background-color: transparent !important;

    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: var(--primary-color);
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
    
    // 表头包装器
    :deep(.el-table__header-wrapper) {
      background-color: #ffffff !important;

      // 表头
      :deep(.el-table__header) {
        background-color: #ffffff !important;

        // 表头单元格
        :deep(th) {
          background-color: #ffffff !important;
          color: #5a32a3;
          font-weight: 600;
          font-size: 14px;
          border-bottom: 1px solid #e9ecef;
          padding: 16px;
          text-align: left;
          line-height: 24px;
          transition: all 0.3s ease;

          &:hover {
            background-color: #ffffff !important;
          }

          // 表头单元格内部
          :deep(.cell) {
            background-color: #ffffff !important;
            color: #5a32a3 !important;
            font-weight: 600 !important;
          }
        }
      }
    }
    
    // 表格体包装器
    :deep(.el-table__body-wrapper) {
      background-color: #ffffff !important;

      // 表格行
      :deep(.el-table__row) {
        transition: all 0.3s ease;
        background-color: #ffffff !important;
        line-height: 24px;

        &:hover {
          background-color: #f8f7ff !important;
        }

        &.el-table__row--striped {
          background-color: #fafaff !important;
        }
        
        // 表格单元格
        :deep(td) {
          padding: 14px 16px;
          border-bottom: 1px solid #e9ecef;
          color: #333;
          font-size: 14px;
          font-weight: 400;
          line-height: 24px;
          transition: all 0.3s ease;
          
          // 标签样式
          .el-tag {
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            padding: 2px 8px;
            transition: all 0.3s ease;
          }
          
          // 优先级标签
          .priority-tag {
            &.low {
              background: rgba(82, 196, 26, 0.1);
              color: var(--success-color);
              
              &:hover {
                background: rgba(82, 196, 26, 0.2);
              }
            }
            &.medium {
              background: rgba(250, 173, 20, 0.1);
              color: var(--warning-color);
              
              &:hover {
                background: rgba(250, 173, 20, 0.2);
              }
            }
            &.high {
              background: rgba(255, 77, 79, 0.1);
              color: var(--danger-color);
              
              &:hover {
                background: rgba(255, 77, 79, 0.2);
              }
            }
            &.urgent {
              background: rgba(255, 77, 79, 0.2);
              color: var(--danger-color);
              font-weight: 600;
              
              &:hover {
                background: rgba(255, 77, 79, 0.3);
              }
            }
          }
          
          // 按钮样式
          .el-button {
            font-size: 13px;
            padding: 0;
            margin-right: 12px;
            transition: all 0.3s ease;
            
            &:last-child {
              margin-right: 0;
            }
            
            &:hover {
              transform: translateY(-1px);
            }
            
            &.el-button--text {
              color: var(--primary-color);
              
              &:hover {
                color: var(--primary-dark);
                background: #f8f7ff;
                border-radius: 4px;
              }
            }
          }
        }
      }
    }
    
    // 空状态
    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;

      :deep(.el-table__empty-text) {
        color: #666;
        font-size: 14px;
        line-height: 24px;
      }
    }

    // 确保整个表格容器都使用正确的背景色
    &.el-table--enable-row-hover {
      background-color: #ffffff !important;
    }

    // 覆盖表格行的默认样式
    :deep(.el-table__row) {
      background-color: #ffffff !important;
    }

    // 覆盖表格行的条纹样式
    :deep(.el-table__row.el-table__row--striped) {
      background-color: #fafaff !important;
    }

    // 覆盖表格行的 hover 样式
    :deep(.el-table__row:hover) {
      background-color: #f8f7ff !important;
    }

    // 直接覆盖表头单元格样式
    :deep(.el-table__header th) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }

    // 覆盖表头单元格内容样式
    :deep(.el-table__header th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }
  }
  
  // 分页容器
  .pagination-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 8px 24px;
    background: transparent;
    border-top: 1px solid rgba(147, 112, 219, 0.1);
    transition: all 0.3s ease;

    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: var(--primary-color);
    --el-color-primary-light-3: #9370db;
    --el-color-primary-light-5: #a888e0;
    --el-color-primary-light-7: #c2a9f3;
    --el-color-primary-light-9: #f8f7ff;
    --el-border-color: rgba(147, 112, 219, 0.2);
    --el-border-color-light: rgba(147, 112, 219, 0.15);
    --el-border-color-lighter: rgba(147, 112, 219, 0.1);
    --el-fill-color-light: #f8f7ff;
    --el-fill-color-lighter: #f8f7ff;
    --el-fill-color-blank: #f8f7ff;
    --el-text-color-primary: var(--text-primary);
    --el-text-color-regular: var(--text-secondary);
    --el-text-color-secondary: var(--text-tertiary);
    --el-text-color-placeholder: var(--text-tertiary);

    // 分页组件
    .el-pagination {
      display: flex;
      align-items: center;
      gap: 4px;
      font-weight: 500;

      // 总条数
      :deep(.el-pagination__total) {
        color: #5a32a3;
        font-size: 14px;
        font-weight: 500;
        margin-right: 12px;
      }

      // 每页条数选择器
      :deep(.el-pagination__sizes) {
        margin-right: 12px;

        .el-select {
          .el-input__wrapper {
            border-radius: 8px;
            border: 1px solid rgba(147, 112, 219, 0.2);
            background: #ffffff;
            box-shadow: none;

            &:hover {
              border-color: #7b42f6;
              box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.1);
            }

            &.is-focus {
              border-color: #7b42f6;
              box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.15);
            }
          }

          .el-input__inner {
            color: #5a32a3;
            font-weight: 500;
          }
        }
      }

      // 上一页/下一页按钮
      .btn-prev,
      .btn-next {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        border: 1px solid rgba(147, 112, 219, 0.2);
        background: #ffffff;
        color: #5a32a3;
        transition: all 0.3s ease;

        &:hover:not(:disabled) {
          background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
          border-color: transparent;
          color: white;
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
        }

        &:disabled {
          background: #f5f5f5;
          border-color: #e0e0e0;
          color: #c0c0c0;
        }

        .el-icon {
          font-size: 14px;
          font-weight: bold;
        }
      }

      // 页码
      .el-pager {
        display: flex;
        gap: 4px;

        li {
          min-width: 32px;
          height: 32px;
          padding: 0 8px;
          border-radius: 8px;
          border: 1px solid rgba(147, 112, 219, 0.2);
          background: #ffffff;
          color: #5a32a3;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: center;

          &:hover:not(.is-active) {
            background: rgba(123, 66, 246, 0.1);
            border-color: #7b42f6;
            color: #7b42f6;
            transform: translateY(-1px);
          }

          &.is-active {
            background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
            border-color: transparent;
            color: white;
            box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
            font-weight: 600;
          }

          &.btn-quicknext,
          &.btn-quickprev {
            border: 1px solid rgba(147, 112, 219, 0.2);
            color: #9370db;

            &:hover {
              background: rgba(123, 66, 246, 0.1);
              color: #7b42f6;
            }
          }
        }
      }

      // 跳转页
      .el-pagination__jump {
        margin-left: 12px;
        color: #5a32a3;
        font-weight: 500;

        .el-input__wrapper {
          width: 48px;
          border-radius: 8px;
          border: 1px solid rgba(147, 112, 219, 0.2);
          background: #ffffff;
          box-shadow: none;

          &:hover {
            border-color: #7b42f6;
            box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.1);
          }

          &.is-focus {
            border-color: #7b42f6;
            box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.15);
          }
        }

        .el-input__inner {
          color: #5a32a3;
          font-weight: 500;
          text-align: center;
        }
      }
    }
  }
}

// 对话框样式
.el-dialog {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  
  .el-dialog__header {
    background-color: var(--bg-gray);
    padding: 20px 24px;
    border-bottom: 1px solid var(--border-color);
    
    .el-dialog__title {
      color: var(--text-primary);
      font-weight: 600;
      font-size: 16px;
    }
  }
  
  .el-dialog__body {
    padding: 24px;
    background: var(--bg-light);
  }
  
  .el-dialog__footer {
    padding: 16px 24px;
    border-top: 1px solid var(--border-color);
    background: var(--bg-gray);
  }
}

// 按钮样式
.el-button {
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-1px);
  }
  
  &.el-button--primary {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
    border: none;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
    
    &:hover {
      background: linear-gradient(135deg, var(--primary-dark) 0%, #5a4ba2 100%);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
  }
  
  &.el-button--success {
    background: linear-gradient(135deg, var(--success-color) 0%, #389e0d 100%);
    border: none;
    box-shadow: 0 2px 8px rgba(82, 196, 26, 0.2);
    
    &:hover {
      background: linear-gradient(135deg, #389e0d 0%, #237804 100%);
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.3);
    }
  }
  
  &.el-button--warning {
    background: linear-gradient(135deg, var(--warning-color) 0%, #d48806 100%);
    border: none;
    box-shadow: 0 2px 8px rgba(250, 173, 20, 0.2);
    
    &:hover {
      background: linear-gradient(135deg, #d48806 0%, #ad6800 100%);
      box-shadow: 0 4px 12px rgba(250, 173, 20, 0.3);
    }
  }
  
  &.el-button--danger {
    background: linear-gradient(135deg, var(--danger-color) 0%, #cf1322 100%);
    border: none;
    box-shadow: 0 2px 8px rgba(255, 77, 79, 0.2);
    
    &:hover {
      background: linear-gradient(135deg, #cf1322 0%, #a8071a 100%);
      box-shadow: 0 4px 12px rgba(255, 77, 79, 0.3);
    }
  }
  
  &.el-button--text {
    color: var(--primary-color);
    
    &:hover {
      color: var(--primary-dark);
      background: var(--primary-light);
      border-radius: 4px;
    }
  }
}

// 进度条样式
.el-progress {
  .el-progress__bar {
    border-radius: 3px;
    transition: all 0.3s ease;
  }
  
  .el-progress__text {
    font-size: 12px;
    color: var(--text-tertiary);
    transition: all 0.3s ease;
  }
}

// 响应式设计
@media screen and (max-width: 1200px) {
  .page-container {
    padding: 20px;
  }
  
  .filter-bar .filter-form {
    gap: 12px;
  }
  
  .table-container .el-table {
    .el-table__row td {
      padding: 12px 14px;
    }
  }
}

@media screen and (max-width: 768px) {
  .page-container {
    padding: 16px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .filter-bar .filter-form {
    flex-direction: column;
    align-items: stretch;
  }

  .table-container {
    border-radius: 8px;
  }
  
  .pagination-container {
    justify-content: center;
    padding: 12px;
    gap: 12px;
  }
  
  .el-pagination {
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
  }
}
</style>