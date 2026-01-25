<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">用例评审</h1>
      <div>
        <el-button type="primary" @click="createReview">
          <el-icon><Plus /></el-icon>
          创建评审
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="项目">
          <el-select v-model="filters.project" placeholder="请选择项目" clearable @change="fetchReviews" style="min-width: 250px; max-width: 300px;">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="请选择状态" clearable @change="fetchReviews" style="min-width: 150px; max-width: 200px;">
            <el-option label="待评审" value="pending" />
            <el-option label="评审中" value="in_progress" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="评审人">
          <el-select v-model="filters.reviewer" placeholder="请选择评审人" clearable @change="fetchReviews" style="min-width: 200px; max-width: 250px;">
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
        <el-table-column prop="title" label="评审标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="关联项目" width="200">
          <template #default="{ row }">
            <span v-if="row.projects && row.projects.length > 0">
              {{ row.projects.map(p => p.name).join(', ') }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="评审状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :class="`priority-tag ${row.priority}`">{{ getPriorityText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator.username" label="创建人" width="120" />
        <el-table-column label="用例数量" width="100">
          <template #default="{ row }">
            {{ row.testcases?.length || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="评审进度" width="120">
          <template #default="{ row }">
            <el-progress 
              :percentage="getReviewProgress(row)" 
              :color="getProgressColor(row)"
              :stroke-width="6"
            />
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止时间" width="160">
          <template #default="{ row }">
            {{ row.deadline ? formatDate(row.deadline) : '无' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewReview(row.id)">详情</el-button>
            <el-button v-if="canReview(row)" link type="success" @click="submitReview(row)">评审</el-button>
            <el-button v-if="canEdit(row)" link type="warning" @click="editReview(row.id)">编辑</el-button>
            <el-popconfirm
              v-if="canDelete(row)"
              title="确定要删除这个评审吗？"
              @confirm="deleteReview(row.id)"
            >
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
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
    <el-dialog v-model="reviewDialogVisible" title="提交评审" :close-on-click-modal="false" :close-on-press-escape="false" :modal="true" :destroy-on-close="false" width="600px">
      <el-form :model="reviewForm" label-width="80px">
        <el-form-item label="评审结果" required>
          <el-radio-group v-model="reviewForm.status">
            <el-radio-button label="approved">通过</el-radio-button>
            <el-radio-button label="rejected">拒绝</el-radio-button>
            <el-radio-button label="abstained">弃权</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="评审意见">
          <el-input
            v-model="reviewForm.comment"
            type="textarea"
            :rows="4"
            placeholder="请输入评审意见"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSubmitReview">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

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
    ElMessage.error('获取评审列表失败')
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
    ElMessage.success('评审提交成功')
    reviewDialogVisible.value = false
    fetchReviews()
  } catch (error) {
    ElMessage.error('评审提交失败')
  }
}

const deleteReview = async (id) => {
  try {
    await api.delete(`/reviews/reviews/${id}/`)
    ElMessage.success('删除成功')
    fetchReviews()
  } catch (error) {
    ElMessage.error('删除失败')
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
    pending: '待评审',
    in_progress: '评审中',
    approved: '已通过',
    rejected: '已拒绝',
    cancelled: '已取消'
  }
  return textMap[status] || status
}

const getPriorityText = (priority) => {
  const textMap = {
    low: '低',
    medium: '中',
    high: '高',
    urgent: '紧急'
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
  return review.creator.id === userStore.user?.id && review.status === 'pending'
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
.page-container {
  padding: 20px;
  min-height: calc(100vh - 120px);
  background: linear-gradient(135deg, #f9f7ff 0%, #f3f0fa 100%);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(90, 50, 163, 0.1);
  
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #5a32a3;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  
  .el-button {
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.2);
    transition: all 0.3s ease;
    
    &:hover {
      box-shadow: 0 6px 16px rgba(90, 50, 163, 0.3);
      transform: translateY(-1px);
    }
  }
}

.filter-bar {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(90, 50, 163, 0.08);
  backdrop-filter: blur(10px);
  
  .filter-form {
    display: flex;
    gap: 16px;
    align-items: flex-end;
    
    .el-form-item {
      margin-bottom: 0;
      
      .el-form-item__label {
        font-weight: 500;
        color: #5a32a3;
      }
      
      .el-select {
        border-radius: 8px;
        border: 1px solid rgba(90, 50, 163, 0.2);
        transition: all 0.3s ease;
        
        &:hover {
          border-color: #9370db;
          box-shadow: 0 0 0 2px rgba(147, 112, 219, 0.1);
        }
        
        &.is-focus {
          border-color: #5a32a3;
          box-shadow: 0 0 0 2px rgba(90, 50, 163, 0.2);
        }
      }
    }
  }
}

.table-container {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(90, 50, 163, 0.08);
  backdrop-filter: blur(10px);
  
  .el-table {
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 20px;
    
    &::before {
      display: none;
    }
    
    .el-table__header-wrapper {
      .el-table__header {
        background: linear-gradient(135deg, #f3f0fa 0%, #e8e3f5 100%);
        
        th {
          background: transparent !important;
          color: #5a32a3;
          font-weight: 600;
          border-bottom: 2px solid rgba(90, 50, 163, 0.2);
          padding: 16px 12px;
        }
      }
    }
    
    .el-table__body-wrapper {
      .el-table__row {
        transition: all 0.3s ease;
        
        &:hover {
          background: rgba(90, 50, 163, 0.02) !important;
        }
        
        &.el-table__row--striped {
          background: rgba(243, 240, 250, 0.5) !important;
        }
        
        td {
          padding: 14px 12px;
          border-bottom: 1px solid rgba(90, 50, 163, 0.1);
          
          .el-tag {
            border-radius: 16px;
            padding: 2px 12px;
            font-size: 12px;
            font-weight: 500;
          }
          
          .priority-tag {
            &.low {
              background: rgba(103, 194, 58, 0.1);
              color: #67c23a;
            }
            &.medium {
              background: rgba(230, 162, 60, 0.1);
              color: #e6a23c;
            }
            &.high {
              background: rgba(245, 108, 108, 0.1);
              color: #f56c6c;
            }
            &.urgent {
              background: rgba(245, 108, 108, 0.2);
              color: #f56c6c;
              font-weight: 600;
            }
          }
          
          .el-button {
            transition: all 0.3s ease;
            
            &:hover {
              transform: translateY(-1px);
            }
          }
        }
      }
    }
    
    .el-table__empty-block {
      padding: 60px 0;
      
      .el-table__empty-text {
        color: #909399;
        font-size: 14px;
      }
    }
  }
  
  .pagination-container {
    display: flex;
    justify-content: flex-end;
    padding-top: 20px;
    border-top: 1px solid rgba(90, 50, 163, 0.1);
    
    .el-pagination {
      .el-pagination__sizes {
        margin-right: 16px;
      }
      
      .el-select .el-input {
        width: 100px;
      }
      
      .el-pager li {
        border-radius: 4px;
        margin: 0 4px;
        transition: all 0.3s ease;
        
        &:hover:not(.disabled) {
          color: #5a32a3;
        }
        
        &.active {
          background: #5a32a3;
          color: #ffffff;
        }
      }
      
      .el-pagination__prev, .el-pagination__next {
        border-radius: 4px;
        transition: all 0.3s ease;
        
        &:hover:not(.disabled) {
          color: #5a32a3;
        }
      }
    }
  }
}

// 对话框样式
.el-dialog {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(90, 50, 163, 0.2);
  
  .el-dialog__header {
    background: linear-gradient(135deg, #f3f0fa 0%, #e8e3f5 100%);
    padding: 20px;
    border-bottom: 1px solid rgba(90, 50, 163, 0.1);
    
    .el-dialog__title {
      color: #5a32a3;
      font-weight: 600;
      font-size: 18px;
    }
  }
  
  .el-dialog__body {
    padding: 24px;
  }
  
  .el-dialog__footer {
    padding: 16px 24px;
    border-top: 1px solid rgba(90, 50, 163, 0.1);
    background: #f9f7ff;
  }
}

// 按钮样式
.el-button {
  border-radius: 8px;
  transition: all 0.3s ease;
  
  &.el-button--primary {
    background: linear-gradient(135deg, #5a32a3 0%, #7b42f6 100%);
    border: none;
    
    &:hover {
      background: linear-gradient(135deg, #4a288a 0%, #6a36d6 100%);
      box-shadow: 0 4px 12px rgba(90, 50, 163, 0.3);
    }
  }
  
  &.el-button--success {
    background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
    border: none;
    
    &:hover {
      background: linear-gradient(135deg, #529b2e 0%, #67c23a 100%);
    }
  }
  
  &.el-button--warning {
    background: linear-gradient(135deg, #e6a23c 0%, #ebb563 100%);
    border: none;
    
    &:hover {
      background: linear-gradient(135deg, #cf9236 0%, #e6a23c 100%);
    }
  }
  
  &.el-button--danger {
    background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%);
    border: none;
    
    &:hover {
      background: linear-gradient(135deg, #e65252 0%, #f56c6c 100%);
    }
  }
  
  &.el-button--text {
    color: #5a32a3;
    
    &:hover {
      color: #7b42f6;
      background: rgba(90, 50, 163, 0.1);
    }
  }
}

// 进度条样式
.el-progress {
  .el-progress__bar {
    border-radius: 3px;
  }
  
  .el-progress__text {
    font-size: 12px;
    color: #606266;
  }
}

// 响应式设计
@media screen and (max-width: 1200px) {
  .page-container {
    padding: 16px;
  }
  
  .filter-bar .filter-form {
    flex-wrap: wrap;
    gap: 12px;
  }
  
  .table-container .el-table {
    .el-table__row td {
      padding: 12px 8px;
    }
  }
}

@media screen and (max-width: 768px) {
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
    padding: 12px;
  }
  
  .pagination-container {
    justify-content: center;
  }
}
</style>