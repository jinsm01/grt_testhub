<template>
  <div class="app-package-list">
    <div class="filter-bar">
      <div class="filter-bar-spacer"></div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog" class="create-btn">
        新增包名
      </el-button>
    </div>

    <div class="card-container">
      <el-table
        v-loading="loading"
        :data="packages"
        stripe
        style="width: 100%"
        empty-text="暂无应用包名"
      >
      <el-table-column prop="name" label="应用名称" min-width="180" header-align="center" align="left" show-overflow-tooltip />
      <el-table-column prop="package_name" label="应用包名" min-width="220" header-align="center" align="left" show-overflow-tooltip />
      <el-table-column prop="created_by_name" label="创建人" width="120" header-align="center" align="center">
        <template #default="{ row }">
          <span v-if="row.created_by_name">{{ row.created_by_name }}</span>
          <span v-else class="text-gray">-</span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="200" header-align="center" align="center">
        <template #default="{ row }">
          <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="200" header-align="center" align="center">
        <template #default="{ row }">
          <span class="time-text">{{ formatDateTime(row.updated_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right" header-align="center" align="center">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button size="small" type="primary" class="action-btn edit-btn" @click="openEditDialog(row)">
              <el-icon><Edit /></el-icon>
              <span>编辑</span>
            </el-button>
            <el-button size="small" type="danger" class="action-btn delete-btn" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              <span>删除</span>
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

      <div class="pagination-container">
        <el-pagination
          v-show="total > 0"
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadPackages"
          @current-change="loadPackages"
        />
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="应用名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：Android设置" />
        </el-form-item>
        <el-form-item label="应用包名" prop="package_name">
          <el-input v-model="form.package_name" placeholder="例如：com.android.settings" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import {
  getPackageList,
  createPackage,
  updatePackage,
  deletePackage
} from '@/api/app-automation'
import { formatDateTime } from '@/utils/app-automation-helpers'

defineOptions({ name: 'AppPackageList' })

const loading = ref(false)
const saving = ref(false)
const packages = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const dialogVisible = ref(false)
const dialogTitle = ref('新增包名')
const isEditing = ref(false)
const formRef = ref(null)
const form = reactive({
  id: null,
  name: '',
  package_name: ''
})

const rules = {
  name: [{ required: true, message: '请输入应用名称', trigger: 'blur' }],
  package_name: [{ required: true, message: '请输入应用包名', trigger: 'blur' }]
}

const loadPackages = async () => {
  loading.value = true
  try {
    const res = await getPackageList({
      page: currentPage.value,
      page_size: pageSize.value
    })
    const data = res.data
    const payload = data.success !== undefined ? data.data : data
    packages.value = payload?.results || payload || []
    total.value = payload?.count || packages.value.length || 0
  } catch (error) {
    console.error('加载应用包名失败:', error)
    packages.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.id = null
  form.name = ''
  form.package_name = ''
  formRef.value?.clearValidate()
}

const openCreateDialog = () => {
  isEditing.value = false
  dialogTitle.value = '新增包名'
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEditing.value = true
  dialogTitle.value = '编辑包名'
  form.id = row.id
  form.name = row.name
  form.package_name = row.package_name
  dialogVisible.value = true
}

const submitForm = () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      if (isEditing.value && form.id) {
        await updatePackage(form.id, {
          name: form.name,
          package_name: form.package_name
        })
        ElMessage.success('更新成功')
      } else {
        await createPackage({
          name: form.name,
          package_name: form.package_name
        })
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      loadPackages()
    } catch (error) {
      console.error('保存应用包名失败:', error)
      ElMessage.error(error?.response?.data?.detail || '保存失败')
    } finally {
      saving.value = false
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确认删除应用包名「${row.name}」吗？`,
    '删除确认',
    { type: 'warning' }
  ).then(async () => {
    try {
      await deletePackage(row.id)
      ElMessage.success('删除成功')
      loadPackages()
    } catch (error) {
      console.error('删除应用包名失败:', error)
      ElMessage.error(error?.response?.data?.detail || '删除失败')
    }
  }).catch(() => {})
}

// formatDateTime 已从 app-automation-helpers 导入

onMounted(() => {
  loadPackages()
})
</script>

<style scoped lang="scss">
.app-package-list {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;

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

    &:hover {
      background: linear-gradient(135deg, #9370db 0%, #7c3aed 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 20px rgba(167, 139, 250, 0.4) !important;
    }
  }
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
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

    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;
    }
  }
}
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
  --primary-dark: #8b5cf6;
  --primary-light: #f3f0ff;
  --text-primary: #262626;
  --text-secondary: #595959;
  --text-tertiary: #8c8c8c;

  --el-color-primary: var(--primary-color);
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

    .el-pagination__total { color: #6b7280; font-size: 14px; font-weight: 500; margin-right: 12px; }
    .el-pagination__sizes { margin-right: 12px; .el-select .el-input__wrapper { border-radius: 8px; border: 1px solid #e5e7eb; background: #ffffff; box-shadow: none; &:hover { border-color: #a78bfa; box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1); } &.is-focus { border-color: #a78bfa; box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15); } } .el-input__inner { color: #374151; font-weight: 500; } }
    .btn-prev, .btn-next { width: 32px; height: 32px; border-radius: 8px; border: 1px solid #e5e7eb; background: #ffffff; color: #6b7280; transition: all 0.3s ease; &:hover:not(:disabled) { background: #f5f3ff; border-color: #a78bfa; color: #8b5cf6; transform: translateY(-1px); box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2); } &:disabled { background: #f5f5f5; border-color: #e0e0e0; color: #c0c0c0; } .el-icon { font-size: 14px; font-weight: bold; } }
    .el-pager { display: flex; gap: 8px; li { min-width: 32px; height: 32px; padding: 0 8px; border-radius: 8px; border: 1px solid #d1d5db; background: #ffffff; color: #6b7280; font-size: 14px; font-weight: 500; transition: all 0.3s ease; display: flex; align-items: center; justify-content: center; &:hover:not(.is-active) { background: #f5f3ff; border-color: #a78bfa; color: #8b5cf6; transform: translateY(-1px); } &.is-active { background: #f5f3ff; border-color: #a78bfa; color: #8b5cf6; box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2); } &.is-active:hover { background: #ede9fe; border-color: #8b5cf6; } } }
    .el-pagination__jump { color: #6b7280; font-weight: 500; margin-left: 12px; .el-input { width: 50px; margin: 0 4px; .el-input__wrapper { border-radius: 8px; border: 1px solid #e5e7eb; background: #ffffff; box-shadow: none; &:hover { border-color: #a78bfa; box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1); } &.is-focus { border-color: #a78bfa; box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15); } } .el-input__inner { color: #374151; font-weight: 500; text-align: center; } } }
  }
}

// 文本样式
.text-gray {
  color: #909399;
}

.time-text {
  color: #666;
  font-size: 14px;
}

// 操作按钮样式
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
</style>
