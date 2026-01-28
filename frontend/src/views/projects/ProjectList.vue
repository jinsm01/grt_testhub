<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">项目管理</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新建项目
      </el-button>
    </div>
    
    <div class="filter-bar">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-input
            v-model="searchText"
            placeholder="搜索项目名称"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="4">
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="handleFilter">
            <el-option label="进行中" value="active" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已完成" value="completed" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-col>
      </el-row>
    </div>
    
    <div class="table-container">
      <el-table :data="projects" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="name" label="项目名称" min-width="200">
          <template #default="{ row }">
            <el-link @click="goToProject(row.id)" type="primary">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="300" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner.username" label="负责人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="editProject(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteProject(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
    
    <!-- 创建/编辑项目对话框 -->
    <el-dialog
      :title="isEdit ? '编辑项目' : '新建项目'"
      v-model="showCreateDialog"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
      width="600px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="请输入项目描述"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态">
            <el-option label="进行中" value="active" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已完成" value="completed" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import dayjs from 'dayjs'

const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const showCreateDialog = ref(false)
const isEdit = ref(false)
const formRef = ref()

const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchText = ref('')
const statusFilter = ref('')

const form = reactive({
  id: null,
  name: '',
  description: '',
  status: 'active'
})

const rules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 2, max: 200, message: '项目名称长度在 2 到 200 个字符', trigger: 'blur' }
  ],
  status: [
    { required: true, message: '请选择项目状态', trigger: 'change' }
  ]
}

const fetchProjects = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      status: statusFilter.value
    }
    const response = await api.get('/projects/', { params })
    projects.value = response.data.results
    total.value = response.data.count
  } catch (error) {
    ElMessage.error('获取项目列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchProjects()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchProjects()
}

const handlePageChange = () => {
  fetchProjects()
}

const goToProject = (id) => {
  router.push(`/ai-generation/projects/${id}`)
}

const editProject = (project) => {
  isEdit.value = true
  form.id = project.id
  form.name = project.name
  form.description = project.description
  form.status = project.status
  showCreateDialog.value = true
}

const resetForm = () => {
  form.id = null
  form.name = ''
  form.description = ''
  form.status = 'active'
  isEdit.value = false
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        if (isEdit.value) {
          await api.put(`/projects/${form.id}/`, form)
          ElMessage.success('项目更新成功')
        } else {
          await api.post('/projects/', form)
          ElMessage.success('项目创建成功')
        }
        showCreateDialog.value = false
        resetForm()
        fetchProjects()
      } catch (error) {
        ElMessage.error(isEdit.value ? '项目更新失败' : '项目创建失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

const deleteProject = async (project) => {
  try {
    await ElMessageBox.confirm('确定要删除这个项目吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.delete(`/projects/${project.id}/`)
    ElMessage.success('项目删除成功')
    fetchProjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('项目删除失败')
    }
  }
}

const getStatusType = (status) => {
  const typeMap = {
    active: 'success',
    paused: 'warning',
    completed: 'info',
    archived: 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    active: '进行中',
    paused: '已暂停',
    completed: '已完成',
    archived: '已归档'
  }
  return textMap[status] || status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
/* 全局变量 */
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

/* 页面容器 */
.page-container {
  padding: 24px;
  min-height: 100vh;
  background: linear-gradient(135deg, #f3f0fa 0%, #e8e3f5 100%);
  display: flex;
  flex-direction: column;
  line-height: 24px;
}

/* 页面头部 */
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
  
  .el-button {
    &.el-button--primary {
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
}

/* 筛选栏 */
.filter-bar {
  background-color: #f8f7ff;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
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
}

/* 表格容器 */
.table-container {
  background-color: #f8f7ff;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 表格样式 */
.el-table {
  border: none !important;
  border-radius: 8px !important;
  overflow: hidden !important;
  flex-grow: 1;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
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
    display: none !important;
  }
  
  /* 表头包装器 */
  :deep(.el-table__header-wrapper) {
    background-color: #f8f7ff !important;
    
    /* 表头 */
    :deep(.el-table__header) {
      background-color: #f8f7ff !important;
      
      /* 表头单元格 */
      :deep(th) {
        background-color: #f8f7ff !important;
        color: #5a32a3 !important;
        font-weight: 600 !important;
        font-size: 14px;
        border-bottom: 1px solid #e9ecef !important;
        padding: 16px;
        text-align: left;
        line-height: 24px;
        transition: all 0.3s ease;
        
        /* 表头单元格内部 */
        :deep(.cell) {
          background-color: #f8f7ff !important;
          color: #5a32a3 !important;
          font-weight: 600 !important;
        }
      }
    }
  }
  
  /* 表格体包装器 */
  :deep(.el-table__body-wrapper) {
    background-color: #f8f7ff !important;
    
    /* 表格行 */
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
      
      /* 表格单元格 */
      :deep(td) {
        padding: 14px 16px;
        border-bottom: 1px solid #e9ecef !important;
        color: #333;
        font-size: 14px;
        font-weight: 400;
        line-height: 24px;
        transition: all 0.3s ease;
        
        /* 标签样式 */
        .el-tag {
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
          padding: 2px 8px;
          transition: all 0.3s ease;
        }
        
        /* 按钮样式 */
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
  
  /* 空状态 */
  :deep(.el-table__empty-block) {
    padding: 60px 0;
    background: #f8f7ff !important;
    
    :deep(.el-table__empty-text) {
      color: #666;
      font-size: 14px;
      line-height: 24px;
    }
  }
  
  /* 确保整个表格容器都使用正确的背景色 */
  &.el-table--enable-row-hover {
    background-color: #f8f7ff !important;
  }
  
  /* 覆盖表格行的默认样式 */
  :deep(.el-table__row) {
    background-color: #f8f7ff !important;
  }
  
  /* 覆盖表格行的条纹样式 */
  :deep(.el-table__row.el-table__row--striped) {
    background-color: #f0edff !important;
  }
  
  /* 覆盖表格行的 hover 样式 */
  :deep(.el-table__row:hover) {
    background-color: #f0edff !important;
  }
  
  /* 直接覆盖表头单元格样式 */
  :deep(.el-table__header th) {
    background-color: #f8f7ff !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
  }
  
  /* 覆盖表头单元格内容样式 */
  :deep(.el-table__header th .cell) {
    background-color: #f8f7ff !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
  }
  
  /* 覆盖表格容器的背景色 */
  &.el-table {
    background-color: #f8f7ff !important;
  }
  
  /* 覆盖表格体的背景色 */
  :deep(.el-table__body) {
    background-color: #f8f7ff !important;
  }
  
  /* 覆盖表格行的背景色 */
  :deep(.el-table__row) {
    background-color: #f8f7ff !important;
  }
  
  /* 覆盖表格行的条纹背景色 */
  :deep(.el-table__row.el-table__row--striped) {
    background-color: #f0edff !important;
  }
  
  /* 覆盖表格行的 hover 背景色 */
  :deep(.el-table__row:hover) {
    background-color: #f0edff !important;
  }
  
  /* 覆盖表格单元格的背景色 */
  :deep(.el-table__cell) {
    background-color: inherit !important;
  }
  
  /* 覆盖表格表头的背景色 */
  :deep(.el-table__header) {
    background-color: #f8f7ff !important;
  }
  
  /* 覆盖表格表头单元格的背景色 */
  :deep(.el-table__header th) {
    background-color: #f8f7ff !important;
  }
  
  /* 覆盖表格表头单元格内容的背景色 */
  :deep(.el-table__header th .cell) {
    background-color: #f8f7ff !important;
  }
  
  /* 覆盖表格空状态的背景色 */
  :deep(.el-table__empty-block) {
    background-color: #f8f7ff !important;
  }
  
  /* 覆盖表格空状态文本的颜色 */
  :deep(.el-table__empty-text) {
    color: #666 !important;
  }
}

/* 分页容器 */
.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background-color: #f8f7ff !important;
  border: 1px solid #e9ecef !important;
  border-radius: 8px !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
  transition: all 0.3s ease !important;
  
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
  
  /* 分页组件 */
  :deep(.el-pagination) {
    display: flex;
    align-items: center;
    gap: 8px;
    
    /* 分页按钮 */
    :deep(.el-pagination__button) {
      border: 1px solid #e9ecef !important;
      background-color: #ffffff !important;
      color: #666 !important;
      border-radius: 4px !important;
      transition: all 0.3s ease !important;
      
      &:hover {
        border-color: var(--primary-color) !important;
        color: var(--primary-color) !important;
        background-color: #f8f7ff !important;
      }
      
      &:focus {
        border-color: var(--primary-color) !important;
        color: var(--primary-color) !important;
        background-color: #f8f7ff !important;
      }
    }
    
    /* 当前页码按钮 */
    :deep(.el-pagination__button.is-current) {
      border-color: var(--primary-color) !important;
      background-color: var(--primary-color) !important;
      color: #ffffff !important;
      border-radius: 4px !important;
      transition: all 0.3s ease !important;
      
      &:hover {
        border-color: var(--primary-dark) !important;
        background-color: var(--primary-dark) !important;
        color: #ffffff !important;
      }
      
      &:focus {
        border-color: var(--primary-dark) !important;
        background-color: var(--primary-dark) !important;
        color: #ffffff !important;
      }
    }
    
    /* 禁用的分页按钮 */
    :deep(.el-pagination__button:disabled) {
      border-color: #e9ecef !important;
      background-color: #f8f8f8 !important;
      color: #d9d9d9 !important;
      cursor: not-allowed !important;
      
      &:hover {
        border-color: #e9ecef !important;
        background-color: #f8f8f8 !important;
        color: #d9d9d9 !important;
      }
    }
    
    /* 分页输入框 */
    :deep(.el-pagination__editor) {
      border: 1px solid #e9ecef !important;
      border-radius: 4px !important;
      transition: all 0.3s ease !important;
      
      &:hover {
        border-color: var(--primary-color) !important;
      }
      
      &:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
      }
    }
    
    /* 分页选择器 */
    :deep(.el-select .el-input__wrapper) {
      border: 1px solid #e9ecef !important;
      border-radius: 4px !important;
      transition: all 0.3s ease !important;
      
      &:hover {
        border-color: var(--primary-color) !important;
      }
      
      &:focus-within {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
      }
    }
    
    /* 分页信息 */
    :deep(.el-pagination__total) {
      color: #666 !important;
      font-size: 14px !important;
      font-weight: 400 !important;
    }
    
    /* 分页跳转信息 */
    :deep(.el-pagination__jump) {
      color: #666 !important;
      font-size: 14px !important;
      font-weight: 400 !important;
    }
    
    /* 分页分隔符 */
    :deep(.el-pagination__separator) {
      color: #666 !important;
      font-size: 14px !important;
      font-weight: 400 !important;
    }
  }
  
  /* 确保分页容器的背景色 */
  &.pagination-container {
    background-color: #f8f7ff !important;
  }
}
/* 响应式设计 */
@media screen and (max-width: 1920px) {
  .filter-bar {
    margin-bottom: 16px;
  }
  
  .pagination-container {
    margin-top: 16px;
  }
}

@media screen and (max-width: 1600px) {
  .filter-bar {
    margin-bottom: 16px;
  }
  
  .pagination-container {
    margin-top: 16px;
  }
}

@media screen and (max-width: 1440px) {
  .filter-bar {
    margin-bottom: 16px;
  }
  
  .pagination-container {
    margin-top: 16px;
  }
}

@media screen and (max-width: 1366px) {
  .filter-bar {
    margin-bottom: 16px;
  }
  
  .pagination-container {
    margin-top: 16px;
  }
}

@media screen and (max-width: 1280px) {
  .filter-bar {
    margin-bottom: 16px;
  }
  
  .pagination-container {
    margin-top: 16px;
  }
}

@media screen and (max-width: 1024px) {
  .filter-bar {
    margin-bottom: 16px;
    
    :deep(.el-row) {
      flex-direction: column;
      
      .el-col {
        width: 100%;
        margin-bottom: 10px;
      }
    }
  }
  
  .pagination-container {
    margin-top: 16px;
    
    :deep(.el-pagination) {
      flex-wrap: wrap;
      justify-content: center;
    }
  }
}

@media screen and (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .filter-bar {
    margin-bottom: 16px;
  }
  
  .pagination-container {
    margin-top: 16px;
    
    :deep(.el-pagination) {
      :deep(.el-pagination__sizes),
      :deep(.el-pagination__jump) {
        display: none;
      }
    }
  }
  
  :deep(.el-dialog) {
    width: 95% !important;
    margin: 0 auto;
  }
}

@media screen and (max-width: 480px) {
  .page-header {
    :deep(.el-button) {
      width: 100%;
    }
  }
  
  .filter-bar {
    margin-bottom: 16px;
  }
  
  .pagination-container {
    margin-top: 16px;
  }
  
  :deep(.el-table) {
    font-size: 12px;
    
    .el-button {
      padding: 5px 8px;
      font-size: 12px;
    }
  }
  
  :deep(.el-dialog) {
    width: 98% !important;
  }
}
</style>