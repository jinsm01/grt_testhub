<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">版本管理</h1>
      <div class="header-actions">
        <el-button 
          v-if="selectedVersions.length > 0" 
          type="danger" 
          @click="batchDeleteVersions"
          :disabled="isDeleting">
          <el-icon><Delete /></el-icon>
          批量删除 ({{ selectedVersions.length }})
        </el-button>
        <el-button type="primary" @click="createVersion">
          <el-icon><Plus /></el-icon>
          新建版本
        </el-button>
      </div>
    </div>
    
    <div class="filter-bar">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-input
            v-model="searchText"
            placeholder="搜索版本名称"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="4">
          <el-select v-model="projectFilter" placeholder="关联项目" clearable @change="handleFilter">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-col>
        <el-col :span="3">
          <el-select v-model="baselineFilter" placeholder="版本类型" clearable @change="handleFilter">
            <el-option label="基线版本" :value="true" />
            <el-option label="普通版本" :value="false" />
          </el-select>
        </el-col>
      </el-row>
    </div>
    
    <div class="table-container">
      <el-table 
        :data="versions" 
        v-loading="loading" 
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column type="index" label="序号" width="80" :index="getSerialNumber" />
        <el-table-column prop="name" label="版本名称" min-width="100">
          <template #default="{ row }">
            <div class="version-name">
              <span>{{ row.name }}</span>
              <el-tag v-if="row.is_baseline" type="warning" size="small" class="baseline-tag">基线</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="projects" label="关联项目" width="300">
          <template #default="{ row }">
            <div v-if="row.projects && row.projects.length > 0" class="project-tags">
              <el-tag 
                v-for="project in row.projects.slice(0, 2)" 
                :key="project.id" 
                size="small" 
                type="primary"
                class="project-tag"
              >
                {{ project.name }}
              </el-tag>
              <el-tooltip v-if="row.projects.length > 2" :content="getProjectsTooltip(row.projects)">
                <el-tag size="small" type="info" class="project-tag">
                  +{{ row.projects.length - 2 }}
                </el-tag>
              </el-tooltip>
            </div>
            <span v-else class="no-project">未关联项目</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="testcases_count" label="用例数量" width="100">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.testcases_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_by.username" label="创建者" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="editVersion(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteVersion(row)">删除</el-button>
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
    
    <!-- 版本表单对话框 -->
    <el-dialog 
      v-model="versionDialogVisible" 
      :title="isEdit ? '编辑版本' : '创建版本'"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
      width="600px"
    >
      <el-form :model="versionForm" :rules="versionRules" ref="versionFormRef" label-width="120px">
        <el-form-item label="版本名称" prop="name">
          <el-input v-model="versionForm.name" placeholder="请输入版本名称" />
        </el-form-item>
        
        <el-form-item label="关联项目" prop="project_ids">
          <el-select 
            v-model="versionForm.project_ids" 
            placeholder="请选择项目（可多选）" 
            multiple
            style="width: 100%"
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="版本描述">
          <el-input
            v-model="versionForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入版本描述"
          />
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="versionForm.is_baseline">设为基线版本</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="versionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveVersion" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const loading = ref(false)
const versions = ref([])
const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchText = ref('')
const projectFilter = ref('')
const baselineFilter = ref('')
const selectedVersions = ref([])
const isDeleting = ref(false)

const versionDialogVisible = ref(false)
const versionFormRef = ref()
const saving = ref(false)
const isEdit = ref(false)
const editingVersionId = ref(null)

const versionForm = reactive({
  name: '',
  description: '',
  project_ids: [],
  is_baseline: false
})

const versionRules = {
  name: [{ required: true, message: '请输入版本名称', trigger: 'blur' }],
  project_ids: [{ required: true, message: '请选择关联项目', trigger: 'change' }]
}

const fetchVersions = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      projects: projectFilter.value,
      is_baseline: baselineFilter.value
    }
    const response = await api.get('/versions/', { params })
    versions.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取版本列表失败')
  } finally {
    loading.value = false
  }
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error('获取项目列表失败')
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchVersions()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchVersions()
}

const handlePageChange = () => {
  fetchVersions()
}

const createVersion = () => {
  isEdit.value = false
  resetVersionForm()
  versionDialogVisible.value = true
}

const editVersion = (version) => {
  isEdit.value = true
  editingVersionId.value = version.id
  
  versionForm.name = version.name
  versionForm.description = version.description
  versionForm.project_ids = version.projects.map(p => p.id)
  versionForm.is_baseline = version.is_baseline
  
  versionDialogVisible.value = true
}

const saveVersion = async () => {
  if (!versionFormRef.value) return
  
  try {
    await versionFormRef.value.validate()
    saving.value = true
    
    if (isEdit.value) {
      await api.put(`/versions/${editingVersionId.value}/`, versionForm)
      ElMessage.success('版本更新成功')
    } else {
      await api.post('/versions/', versionForm)
      ElMessage.success('版本创建成功')
    }
    
    versionDialogVisible.value = false
    fetchVersions()
    
  } catch (error) {
    if (error.response?.data) {
      const errors = Object.values(error.response.data).flat()
      ElMessage.error(errors[0] || '保存失败')
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

const deleteVersion = async (version) => {
  try {
    await ElMessageBox.confirm('确定要删除这个版本吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.delete(`/versions/${version.id}/`)
    ElMessage.success('版本删除成功')
    fetchVersions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('版本删除失败')
    }
  }
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedVersions.value = selection
}

// 获取序号
const getSerialNumber = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 批量删除
const batchDeleteVersions = async () => {
  if (selectedVersions.value.length === 0) {
    ElMessage.warning('请先选择要删除的版本')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedVersions.value.length} 个版本吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    isDeleting.value = true
    let successCount = 0
    let failCount = 0

    // 逐个删除选中的版本
    for (const version of selectedVersions.value) {
      try {
        await api.delete(`/versions/${version.id}/`)
        successCount++
      } catch (error) {
        console.error(`删除版本 ${version.id} 失败:`, error)
        failCount++
      }
    }

    // 显示删除结果
    if (successCount > 0) {
      ElMessage.success(`成功删除 ${successCount} 个版本${failCount > 0 ? `，${failCount} 个失败` : ''}`)
    } else {
      ElMessage.error('删除失败')
    }

    // 清空选择并重新加载列表
    selectedVersions.value = []
    fetchVersions()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败: ' + (error.message || '未知错误'))
    }
  } finally {
    isDeleting.value = false
  }
}

const resetVersionForm = () => {
  versionForm.name = ''
  versionForm.description = ''
  versionForm.project_ids = []
  versionForm.is_baseline = false
  editingVersionId.value = null
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const getProjectsTooltip = (projects) => {
  return projects.map(p => p.name).join('、')
}

onMounted(() => {
  fetchProjects()
  fetchVersions()
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
  
  .header-actions {
    display: flex;
    gap: 10px;
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
    
    &.el-button--danger {
      transition: all 0.3s ease !important;
      
      &:hover {
        transform: translateY(-1px) !important;
      }
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
            
            &.el-button--text.el-button--primary {
              color: var(--primary-color);
              
              &:hover {
                color: var(--primary-dark);
              }
            }
            
            &.el-button--text.el-button--danger {
              color: var(--danger-color);
              
              &:hover {
                color: #cf1322;
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

/* 版本名称 */
.version-name {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .baseline-tag {
    font-size: 12px;
  }
}

/* 项目标签 */
.project-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  
  .project-tag {
    margin: 0;
  }
}

/* 无项目状态 */
.no-project {
  color: #909399;
  font-size: 12px;
  font-style: italic;
}

// 响应式设计
@media screen and (max-width: 1200px) {
  .page-container {
    padding: 20px;
  }
  
  .filter-bar {
    padding: 16px;
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