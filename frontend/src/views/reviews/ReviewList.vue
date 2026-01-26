<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">用例评审</h1>
      <div>
        <el-button type="primary" class="create-review-btn" @click="createReview">
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
  min-height: 100vh;
  background: linear-gradient(135deg, #f3f0fa 0%, #e8e3f5 100%);
  display: flex;
  flex-direction: column;
  line-height: 24px;
}

// 页面头部
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 20px 24px;
  background-color: #f8f7ff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  
  .page-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  
  .create-review-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    
    &:hover {
      background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
    }
    
    &:active {
      transform: translateY(0) !important;
    }
  }
}

// 筛选栏
.filter-bar {
  background-color: #f8f7ff;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  
  .filter-form {
    display: flex;
    gap: 16px;
    align-items: center;
    flex-wrap: wrap;
    
    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: var(--primary-color);
    --el-color-primary-light-3: #9370db;
    --el-color-primary-light-5: #a888e0;
    --el-color-primary-light-7: #c2a9f3;
    --el-color-primary-light-9: #f8f7ff;
    --el-border-color: var(--border-color);
    --el-border-color-light: var(--border-color);
    --el-border-color-lighter: var(--border-color);
    --el-fill-color-light: #f8f7ff;
    --el-fill-color-lighter: #f8f7ff;
    --el-fill-color-blank: #f8f7ff;
    --el-text-color-primary: var(--text-primary);
    --el-text-color-regular: var(--text-secondary);
    --el-text-color-secondary: var(--text-tertiary);
    --el-text-color-placeholder: var(--text-tertiary);
    
    .el-form-item {
      margin-bottom: 0;
      
      .el-form-item__label {
        font-weight: 500;
        color: var(--text-secondary);
        font-size: 14px;
      }
      
      .el-select {
        min-width: 180px;
        
        .el-select__wrapper {
          border-radius: 4px;
          border: 1px solid var(--border-color);
          transition: all 0.3s ease;
          background: var(--bg-light);
          
          &:hover {
            border-color: var(--primary-color);
          }
          
          &.is-focus {
            border-color: var(--primary-color);
          }
        }
        
        .el-select-dropdown {
          background: var(--bg-light);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          
          .el-select-dropdown__item {
            color: var(--text-primary);
            transition: all 0.3s ease;
            
            &:hover {
              background: var(--primary-light);
              color: var(--primary-color);
            }
            
            &.selected {
              background: var(--primary-light);
              color: var(--primary-color);
              font-weight: 500;
            }
          }
        }
      }
    }
  }
}

// 表格容器
.table-container {
  background: var(--primary-light);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  
  // 表格样式
  .el-table {
    border: none;
    border-radius: 8px;
    overflow: hidden;
    flex-grow: 1;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    transition: all 0.3s ease;
    background-color: #f8f7ff !important;
    
    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: var(--primary-color);
    --el-color-primary-light-3: #9370db;
    --el-color-primary-light-5: #a888e0;
    --el-color-primary-light-7: #c2a9f3;
    --el-color-primary-light-9: #f8f7ff;
    --el-border-color: #e9ecef;
    --el-border-color-light: #e9ecef;
    --el-border-color-lighter: #e9ecef;
    --el-fill-color-light: #f8f7ff;
    --el-fill-color-lighter: #f8f7ff;
    --el-fill-color-blank: #f8f7ff;
    --el-text-color-primary: #333;
    --el-text-color-regular: #333;
    --el-text-color-secondary: #666;
    --el-text-color-placeholder: #999;
    --el-table-header-bg-color: #f8f7ff;
    --el-table-row-hover-bg-color: #f0edff;
    --el-table-stripe-bg-color: #f0edff;
    
    &::before {
      display: none;
    }
    
    // 表头包装器
    :deep(.el-table__header-wrapper) {
      background-color: #f8f7ff !important;
      
      // 表头
      :deep(.el-table__header) {
        background-color: #f8f7ff !important;
        
        // 表头单元格
        :deep(th) {
          background-color: #f8f7ff !important;
          color: #5a32a3;
          font-weight: 600;
          font-size: 14px;
          border-bottom: 1px solid #e9ecef;
          padding: 16px;
          text-align: left;
          line-height: 24px;
          transition: all 0.3s ease;
          
          &:hover {
            background-color: #f8f7ff !important;
          }
          
          // 表头单元格内部
          :deep(.cell) {
            background-color: #f8f7ff !important;
            color: #5a32a3 !important;
            font-weight: 600 !important;
          }
        }
      }
    }
    
    // 表格体包装器
    :deep(.el-table__body-wrapper) {
      background-color: #f8f7ff !important;
      
      // 表格行
      :deep(.el-table__row) {
        transition: all 0.3s ease;
        background-color: #f8f7ff !important;
        line-height: 24px;
        
        &:hover {
          background-color: #f0edff !important;
        }
        
        &.el-table__row--striped {
          background-color: #f0edff !important;
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
      background: #f8f7ff !important;
      
      :deep(.el-table__empty-text) {
        color: #666;
        font-size: 14px;
        line-height: 24px;
      }
    }
    
    // 确保整个表格容器都使用正确的背景色
    &.el-table--enable-row-hover {
      background-color: #f8f7ff !important;
    }
    
    // 覆盖表格行的默认样式
    :deep(.el-table__row) {
      background-color: #f8f7ff !important;
    }
    
    // 覆盖表格行的条纹样式
    :deep(.el-table__row.el-table__row--striped) {
      background-color: #f0edff !important;
    }
    
    // 覆盖表格行的 hover 样式
    :deep(.el-table__row:hover) {
      background-color: #f0edff !important;
    }
    
    // 直接覆盖表头单元格样式
    :deep(.el-table__header th) {
      background-color: #f8f7ff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }
    
    // 覆盖表头单元格内容样式
    :deep(.el-table__header th .cell) {
      background-color: #f8f7ff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }
  }
  
  // 分页容器
  .pagination-container {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 16px;
    padding: 16px 24px;
    background-color: #f8f7ff;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    transition: all 0.3s ease;
    
    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: var(--primary-color);
    --el-color-primary-light-3: #9370db;
    --el-color-primary-light-5: #a888e0;
    --el-color-primary-light-7: #c2a9f3;
    --el-color-primary-light-9: #f8f7ff;
    --el-border-color: var(--border-color);
    --el-border-color-light: var(--border-color);
    --el-border-color-lighter: var(--border-color);
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
      gap: 12px;
      
      // 总数
      :deep(.el-pagination__total) {
        color: var(--text-secondary);
        font-size: 14px;
        font-weight: 500;
      }
      
      // 每页大小
      :deep(.el-pagination__sizes) {
        display: flex;
        align-items: center;
        gap: 8px;
        
        label {
          font-size: 14px;
          color: var(--text-secondary);
          font-weight: 500;
        }
        
        .el-select {
          min-width: 80px;
          
          .el-select__wrapper {
            border-radius: 4px;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
            
            &:hover {
              border-color: var(--primary-color);
            }
            
            &.is-focus {
              border-color: var(--primary-color);
            }
          }
          
          .el-select-dropdown {
            background: var(--bg-light);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            
            .el-select-dropdown__item {
              color: var(--text-primary);
              transition: all 0.3s ease;
              
              &:hover {
                background: var(--primary-light);
                color: var(--primary-color);
              }
              
              &.selected {
                background: var(--primary-light);
                color: var(--primary-color);
                font-weight: 500;
              }
            }
          }
        }
      }
      
      // 分页按钮
      :deep(.el-pagination__button) {
        transition: all 0.3s ease;
        border-radius: 4px;
        
        &:hover {
          background: var(--primary-light);
          color: var(--primary-color);
          border-color: var(--primary-color);
        }
        
        &:focus {
          box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
        }
      }
      
      // 当前页按钮
      :deep(.el-pagination__item--active) {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
        border-color: var(--primary-color);
        color: white;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        
        &:hover {
          background: linear-gradient(135deg, var(--primary-dark) 0%, #5a4ba2 100%);
          border-color: var(--primary-dark);
        }
      }
      
      // 禁用按钮
      :deep(.is-disabled) {
        opacity: 0.5;
        
        &:hover {
          background: transparent;
          color: var(--text-tertiary);
          border-color: var(--border-color);
        }
      }
      
      // 页码
      :deep(.el-pager li) {
        border-radius: 4px;
        margin: 0 3px;
        transition: all 0.3s ease;
        font-size: 14px;
        font-weight: 500;
        
        &:hover:not(.disabled) {
          color: var(--primary-color);
          background: var(--primary-light);
          transform: translateY(-1px);
        }
        
        &.active {
          background: var(--primary-color);
          color: #ffffff;
          box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }
      }
      
      // 上一页/下一页
      :deep(.el-pagination__prev),
      :deep(.el-pagination__next) {
        border-radius: 4px;
        transition: all 0.3s ease;
        font-size: 14px;
        
        &:hover:not(.is-disabled) {
          color: var(--primary-color);
          border-color: var(--primary-color);
          background: var(--primary-light);
          transform: translateY(-1px);
        }
      }
      
      // 跳转
      :deep(.el-pagination__jump) {
        display: flex;
        align-items: center;
        gap: 8px;
        
        label {
          font-size: 14px;
          color: var(--text-secondary);
          font-weight: 500;
        }
        
        .el-input {
          width: 80px;
          
          .el-input__wrapper {
            border-radius: 4px;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
            
            &:hover {
              border-color: var(--primary-color);
            }
            
            &.is-focus {
              border-color: var(--primary-color);
            }
          }
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
  
  .filter-bar {
    padding: 16px;
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