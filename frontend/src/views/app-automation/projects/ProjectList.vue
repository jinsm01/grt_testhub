<template>
  <div class="page-container">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input v-model="searchText" placeholder="搜索项目名称" clearable @clear="loadProjects" @keyup.enter="loadProjects" style="width: 300px;" class="search-input">
        <template #suffix><el-icon @click="loadProjects" style="cursor: pointer;"><Search /></el-icon></template>
      </el-input>
      <el-select v-model="statusFilter" placeholder="项目状态" clearable @change="loadProjects" style="width: 160px;">
        <el-option label="未开始" value="NOT_STARTED" />
        <el-option label="进行中" value="IN_PROGRESS" />
        <el-option label="已结束" value="COMPLETED" />
      </el-select>
      <div class="filter-bar-spacer"></div>
      <el-button type="primary" class="create-btn" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>新建项目
      </el-button>
    </div>

    <!-- 表格容器 -->
    <div class="card-container">
      <!-- 项目列表 -->
      <el-table :data="projects" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="name" label="项目名称" min-width="160" header-align="center" align="center" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="200" header-align="center" align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="140" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="getStatusClass(row.status)">
              {{ getStatusText(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="用例数" min-width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span class="count-badge">{{ row.test_case_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="套件数" min-width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span class="count-badge">{{ row.test_suite_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="负责人" min-width="100" header-align="center" align="center">
          <template #default="{ row }">{{ row.owner_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="成员数" min-width="80" header-align="center" align="center">
          <template #default="{ row }">{{ row.member_count || 0 }}</template>
        </el-table-column>
        <el-table-column label="开始日期" min-width="150" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ row.start_date || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="结束日期" min-width="150" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ row.end_date || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="180" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" class="action-btn edit-btn" @click="handleView(row)">
                <el-icon><View /></el-icon>
                <span>查看</span>
              </el-button>
              <el-button size="small" class="action-btn run-btn" @click="handleEdit(row)">
                <el-icon><Edit /></el-icon>
                <span>编辑</span>
              </el-button>
              <el-button size="small" class="action-btn delete-btn" @click="handleDelete(row)">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadProjects"
          @current-change="loadProjects"
        />
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑项目' : '新建项目'" width="520px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入项目描述" />
        </el-form-item>
        <el-form-item label="项目状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态" style="width:100%">
            <el-option label="未开始" value="NOT_STARTED" />
            <el-option label="进行中" value="IN_PROGRESS" />
            <el-option label="已结束" value="COMPLETED" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.start_date" type="date" placeholder="选择开始日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.end_date" type="date" placeholder="选择结束日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="项目详情" width="600px">
      <div v-if="selectedProject">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目名称">{{ selectedProject.name }}</el-descriptions-item>
          <el-descriptions-item label="项目状态">
            <el-tag :type="getStatusType(selectedProject.status)">{{ getStatusText(selectedProject.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="负责人">{{ selectedProject.owner_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="成员数">{{ selectedProject.member_count || 0 }} 人</el-descriptions-item>
          <el-descriptions-item label="测试用例">{{ selectedProject.test_case_count || 0 }} 个</el-descriptions-item>
          <el-descriptions-item label="测试套件">{{ selectedProject.test_suite_count || 0 }} 个</el-descriptions-item>
          <el-descriptions-item label="开始日期">{{ selectedProject.start_date || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="结束日期">{{ selectedProject.end_date || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ formatDateTime(selectedProject.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="项目描述" :span="2">{{ selectedProject.description || '无描述' }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, View, Edit, Delete } from '@element-plus/icons-vue'
import { getAppProjects, createAppProject, updateAppProject, deleteAppProject } from '@/api/app-automation.js'

defineOptions({ name: 'AppProjectList' })

const loading = ref(false)
const submitting = ref(false)
const projects = ref([])
const searchText = ref('')
const statusFilter = ref('')
const pagination = reactive({ current: 1, size: 20, total: 0 })

// 对话框
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)
const form = reactive({
  name: '',
  description: '',
  status: 'IN_PROGRESS',
  start_date: null,
  end_date: null,
})
const formRules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 2, max: 200, message: '长度在 2 到 200 个字符', trigger: 'blur' },
  ],
}

// 详情
const detailVisible = ref(false)
const selectedProject = ref(null)

onMounted(loadProjects)

async function loadProjects() {
  loading.value = true
  try {
    const params = { page: pagination.current, page_size: pagination.size }
    if (searchText.value) params.search = searchText.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getAppProjects(params)
    projects.value = res.data.results || res.data || []
    pagination.total = res.data.count || projects.value.length
  } catch { ElMessage.error('加载项目列表失败') }
  finally { loading.value = false }
}

function openCreateDialog() {
  isEdit.value = false
  editId.value = null
  Object.assign(form, { name: '', description: '', status: 'IN_PROGRESS', start_date: null, end_date: null })
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    name: row.name,
    description: row.description || '',
    status: row.status,
    start_date: row.start_date || null,
    end_date: row.end_date || null,
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateAppProject(editId.value, { ...form })
      ElMessage.success('项目更新成功')
    } else {
      await createAppProject({ ...form })
      ElMessage.success('项目创建成功')
    }
    dialogVisible.value = false
    loadProjects()
  } catch (e) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  } finally { submitting.value = false }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除项目「${row.name}」？此操作不可恢复`, '删除确认', { type: 'warning' })
    await deleteAppProject(row.id)
    ElMessage.success('已删除')
    loadProjects()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

function viewDetail(row) {
  selectedProject.value = row
  detailVisible.value = true
}

// 模板事件处理函数
function handleView(row) {
  viewDetail(row)
}

function handleEdit(row) {
  openEditDialog(row)
}

function getStatusType(status) {
  const map = { 'NOT_STARTED': 'warning', 'IN_PROGRESS': 'primary', 'COMPLETED': 'success' }
  return map[status] || 'info'
}

function getStatusClass(status) {
  const map = { 'NOT_STARTED': 'processing', 'IN_PROGRESS': 'success', 'COMPLETED': 'success' }
  return map[status] || 'pending'
}

function getStatusText(status) {
  const map = { 'NOT_STARTED': '未开始', 'IN_PROGRESS': '进行中', 'COMPLETED': '已结束' }
  return map[status] || status
}

function formatDate(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function formatDateTime(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped lang="scss">
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  line-height: 24px;
  gap: 20px;
}

.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(167, 139, 250, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;

  .search-input {
    :deep(.el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 0 0 1px rgba(167, 139, 250, 0.2) inset;
      background: #ffffff;

      &:hover, &.is-focus {
        box-shadow: 0 0 0 1px #a78bfa inset;
      }
    }

    :deep(.el-input__inner) {
      color: #8b5cf6;
      font-weight: 500;
    }
  }

  .filter-bar-spacer {
    flex: 1;
  }

  .create-btn {
    background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(167, 139, 250, 0.3) !important;

    .el-icon {
      margin-right: 6px;
    }

    &:hover {
      background: linear-gradient(135deg, #9370db 0%, #7c3aed 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 20px rgba(167, 139, 250, 0.4) !important;
    }
  }
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(167, 139, 250, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;

  .el-table {
    border: none;
    border-radius: 8px 8px 0 0;
    overflow: hidden;
    min-height: 200px;
    box-shadow: none;
    transition: all 0.3s ease;
    background-color: transparent !important;

    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: #7b42f6;
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

    :deep(.el-table__header-wrapper) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__header) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__header th) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
      font-size: 14px;
      border-bottom: 1px solid #e9ecef;
      padding: 0 !important;
      text-align: center;
      transition: all 0.3s ease;

      &:hover {
        background-color: #ffffff !important;
      }
    }

    :deep(.el-table__header th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
      white-space: nowrap !important;
      line-height: 24px !important;
      padding: 16px !important;
    }

    :deep(.el-table__body-wrapper) {
      background-color: #ffffff !important;
    }

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
    }

    :deep(td) {
      padding: 14px 16px;
      border-bottom: 1px solid #e9ecef;
      color: #333;
      font-size: 14px;
      font-weight: 400;
      line-height: 24px;
      transition: all 0.3s ease;
      vertical-align: middle;
    }

    :deep(td .cell) {
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      min-height: 24px;
      line-height: 1.5;
      width: 100%;
    }

    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;
    }
  }
}

// 操作按钮样式
.page-container {
  .action-buttons {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 4px;
    flex-wrap: nowrap;
  }

  .action-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 10px !important;
    border-radius: 6px;
    transition: all 0.3s ease;
    border: none !important;

    .el-icon {
      font-size: 14px;
      color: #ffffff !important;
    }

    span {
      font-size: 12px;
      color: #ffffff !important;
    }

    &.edit-btn {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
      }
    }

    &.run-btn {
      background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
      }
    }

    &.delete-btn {
      background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
      }
    }
  }
}

// 状态徽章样式
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
  white-space: nowrap;

  &.success {
    background: #f6ffed;
    color: #52c41a;
  }

  &.failed {
    background: #fff1f0;
    color: #f5222d;
  }

  &.processing {
    background: #fff7e6;
    color: #fa8c16;
  }

  &.pending {
    background: #f5f5f5;
    color: #8c8c8c;
  }
}

// 数量徽章样式
.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #e6f7ff;
  color: #1890ff;
  white-space: nowrap;
}

// 时间文本样式
.time-text {
  color: #666;
  font-size: 14px;
  white-space: nowrap;
}

// 分页容器样式
.pagination-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 0;
  margin-top: 8px;
  background: transparent;
  border: none;
  transition: all 0.3s ease;

  --primary-color: #a78bfa;
  --text-primary: #1f2937;
  --text-secondary: #4b5563;
  --text-tertiary: #6b7280;

  --el-color-primary: #a78bfa;
  --el-color-primary-light-3: #c4b5fd;
  --el-color-primary-light-5: #ddd6fe;
  --el-color-primary-light-7: #ede9fe;
  --el-color-primary-light-9: #f5f3ff;
  --el-border-color: rgba(167, 139, 250, 0.3);
  --el-border-color-light: rgba(167, 139, 250, 0.2);
  --el-border-color-lighter: rgba(167, 139, 250, 0.1);
  --el-fill-color-light: #f5f3ff;
  --el-fill-color-lighter: #f5f3ff;
  --el-fill-color-blank: #f5f3ff;
  --el-text-color-primary: var(--text-primary);
  --el-text-color-regular: var(--text-secondary);
  --el-text-color-secondary: var(--text-tertiary);

  :deep(.el-pagination) {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;

    .el-pagination__total {
      color: #6b7280;
      font-size: 14px;
      font-weight: 500;
      margin-right: 12px;
    }

    .el-pagination__sizes {
      margin-right: 12px;
      
      .el-select .el-input__wrapper {
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        box-shadow: none;
        
        &:hover {
          border-color: #a78bfa;
          box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
        }
        
        &.is-focus {
          border-color: #a78bfa;
          box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
        }
      }
      
      .el-input__inner {
        color: #374151;
        font-weight: 500;
      }
    }

    .btn-prev,
    .btn-next {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      border: 1px solid #e5e7eb;
      background: #ffffff;
      color: #6b7280;
      transition: all 0.3s ease;
      
      &:hover:not(:disabled) {
        background: #f5f3ff;
        border-color: #a78bfa;
        color: #8b5cf6;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
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

    .el-pager {
      display: flex;
      gap: 8px;
      
      li {
        min-width: 32px;
        height: 32px;
        padding: 0 8px;
        border-radius: 8px;
        border: 1px solid #d1d5db;
        background: #ffffff;
        color: #6b7280;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        
        &:hover:not(.is-active) {
          background: #f5f3ff;
          border-color: #a78bfa;
          color: #8b5cf6;
          transform: translateY(-1px);
        }
        
        &.is-active {
          background: #f5f3ff;
          border-color: #a78bfa;
          color: #8b5cf6;
          box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
        }
        
        &.is-active:hover {
          background: #ede9fe;
          border-color: #8b5cf6;
        }
      }
    }

    .el-pagination__jump {
      color: #6b7280;
      font-weight: 500;
      margin-left: 12px;
      
      .el-input {
        width: 50px;
        margin: 0 4px;
        
        .el-input__wrapper {
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          background: #ffffff;
          box-shadow: none;
          
          &:hover {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
          }
          
          &.is-focus {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
          }
        }
        
        .el-input__inner {
          color: #374151;
          font-weight: 500;
          text-align: center;
        }
      }
    }
  }
}
</style>
