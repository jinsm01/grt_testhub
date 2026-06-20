<template>
  <div class="page-container">
    <div class="filter-bar">
      <el-input
        v-model="searchText"
        :placeholder="$t('uiAutomation.ai.caseList.searchPlaceholder')"
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
        style="width: 300px;"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button v-if="false" class="reset-btn" @click="handleReset">{{ $t('uiAutomation.common.reset') }}</el-button>
      <el-button v-if="false" type="primary" class="query-btn" @click="handleSearch">
        <el-icon><Search /></el-icon>
        {{ $t('uiAutomation.common.search') }}
      </el-button>
      <div class="filter-bar-spacer"></div>
      <el-button type="primary" class="create-btn" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        {{ $t('uiAutomation.ai.caseList.createCase') }}
      </el-button>
    </div>

    <div class="card-container">

      <el-table :data="cases" v-loading="loading" stripe>
        <el-table-column label="序号" width="80" header-align="center" align="center">
          <template #default="{ $index }">
            {{ (pagination.currentPage - 1) * pagination.pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="name" :label="$t('uiAutomation.ai.caseList.caseName')" min-width="200" show-overflow-tooltip header-align="center" align="left">
          <template #default="{ row }">
            <div class="case-name-cell">{{ row.name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="description" :label="$t('uiAutomation.common.description')" min-width="200" show-overflow-tooltip header-align="center" align="left" />
        <el-table-column prop="task_description" label="操作步骤" min-width="300" header-align="center" align="left">
          <template #default="{ row }">
            <el-tooltip placement="top" :show-after="200" popper-class="custom-tooltip">
              <template #content>
                <div class="tooltip-content">
                  <div v-for="(line, index) in getFormattedLines(row.task_description)" :key="index" class="tooltip-line">
                    {{ line }}
                  </div>
                </div>
              </template>
              <div class="task-description-cell">
                <div class="task-description-text">{{ row.task_description }}</div>
              </div>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="$t('uiAutomation.common.createTime')" width="180" header-align="center" align="center">
          <template #default="{ row }">
            {{ formatDate(null, null, row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('uiAutomation.common.operation')" width="280" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="success" class="action-btn run-btn" @click="runCase(row)">
                <el-icon><VideoPlay /></el-icon>
                <span>{{ $t('uiAutomation.common.run') }}</span>
              </el-button>
              <el-button size="small" type="primary" class="action-btn edit-btn" @click="editCase(row)">
                <el-icon><Edit /></el-icon>
                <span>{{ $t('uiAutomation.common.edit') }}</span>
              </el-button>
              <el-button size="small" type="danger" class="action-btn delete-btn" @click="deleteCase(row.id)">
                <el-icon><Delete /></el-icon>
                <span>{{ $t('uiAutomation.common.delete') }}</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 创建/编辑抽屉 -->
    <el-drawer v-model="showEditDialog" :title="isEdit ? $t('uiAutomation.ai.caseList.editCase') : $t('uiAutomation.ai.caseList.createCase')" size="600px" direction="rtl">
      <el-form :model="editForm" :rules="formRules" ref="editFormRef" label-width="100px">
        <el-form-item :label="$t('uiAutomation.ai.caseList.caseName')" prop="name">
          <el-input v-model="editForm.name" :placeholder="$t('uiAutomation.ai.caseNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.common.description')" prop="description">
          <el-input v-model="editForm.description" type="textarea" :placeholder="$t('uiAutomation.ai.caseDescPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.ai.caseList.taskDescription')" prop="task_description">
          <el-input
            v-model="editForm.task_description"
            type="textarea"
            :rows="6"
            :placeholder="$t('uiAutomation.ai.taskPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="drawer-footer">
          <el-button @click="showEditDialog = false">{{ $t('uiAutomation.common.cancel') }}</el-button>
          <el-button type="primary" @click="confirmEdit" :loading="saving">{{ $t('uiAutomation.common.save') }}</el-button>
        </span>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, VideoPlay, Edit, Delete, Plus } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import {
  getAICases,
  createAICase,
  updateAICase,
  deleteAICase,
  runAICase
} from '@/api/ui_automation'

const { t } = useI18n()
const router = useRouter()
const cases = ref([])
const loading = ref(false)
const searchText = ref('')
const total = ref(0)
const isEdit = ref(false)

const pagination = reactive({
  currentPage: 1,
  pageSize: 10
})

const showEditDialog = ref(false)
const saving = ref(false)
const currentCaseId = ref(null)
const editForm = reactive({
  name: '',
  description: '',
  task_description: ''
})
const editFormRef = ref(null)

const formRules = computed(() => ({
  name: [{ required: true, message: t('uiAutomation.ai.rules.nameRequired'), trigger: 'blur' }],
  task_description: [{ required: true, message: t('uiAutomation.ai.caseList.rules.taskDescriptionRequired'), trigger: 'blur' }]
}))

// 加载用例列表
const loadCases = async () => {
  loading.value = true
  try {
    const response = await getAICases({
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchText.value
    })

    cases.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    console.error('获取用例列表失败:', error)
    ElMessage.error(t('uiAutomation.ai.caseList.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.currentPage = 1
  loadCases()
}

const handleReset = () => {
  searchText.value = ''
  pagination.currentPage = 1
  loadCases()
}

const handleSizeChange = () => {
  pagination.currentPage = 1
  loadCases()
}

const handleCurrentChange = () => {
  loadCases()
}

// 创建用例
const handleCreate = () => {
  isEdit.value = false
  currentCaseId.value = null
  editForm.name = ''
  editForm.description = ''
  editForm.task_description = ''
  showEditDialog.value = true
}

// 编辑用例
const editCase = (row) => {
  isEdit.value = true
  currentCaseId.value = row.id
  editForm.name = row.name
  editForm.description = row.description
  editForm.task_description = row.task_description
  showEditDialog.value = true
}

const confirmEdit = async () => {
  if (!editFormRef.value) return

  await editFormRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        if (isEdit.value) {
          await updateAICase(currentCaseId.value, {
            name: editForm.name,
            description: editForm.description,
            task_description: editForm.task_description
          })
          ElMessage.success(t('uiAutomation.ai.caseList.messages.updateSuccess'))
        } else {
          await createAICase({
            name: editForm.name,
            description: editForm.description,
            task_description: editForm.task_description
          })
          ElMessage.success(t('uiAutomation.ai.caseList.messages.createSuccess'))
        }
        showEditDialog.value = false
        loadCases()
      } catch (error) {
        console.error('保存失败:', error)
        ElMessage.error(isEdit.value ? t('uiAutomation.ai.caseList.messages.updateFailed') : t('uiAutomation.ai.caseList.messages.createFailed'))
      } finally {
        saving.value = false
      }
    }
  })
}

// 删除用例
const deleteCase = async (id) => {
  try {
    await ElMessageBox.confirm(
      t('uiAutomation.ai.caseList.messages.deleteConfirm'),
      t('uiAutomation.messages.confirm.tip'),
      {
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel'),
        type: 'warning'
      }
    )

    await deleteAICase(id)
    ElMessage.success(t('uiAutomation.ai.caseList.messages.deleteSuccess'))
    loadCases()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error(t('uiAutomation.ai.caseList.messages.deleteFailed'))
    }
  }
}

// 执行用例
const runCase = async (row) => {
  try {
    await runAICase(row.id)
    ElMessage.success(t('uiAutomation.ai.caseList.messages.runSuccess'))
    // 跳转到执行记录页面
    router.push('/ai-intelligent-mode/execution-records')
  } catch (error) {
    console.error('执行失败:', error)
    ElMessage.error(t('uiAutomation.ai.caseList.messages.runFailed'))
  }
}

const getFormattedLines = (text) => {
  if (!text) return []

  const result = []
  let currentLine = ''
  // 只匹配行首的数字序号（前面是字符串开始或换行符）
  const parts = text.split(/(^\d+\.|\n\d+\.)/)

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i]
    // 匹配行首的数字序号（如 "1." 或 "\n1."）
    if (/^\n?\d+\.$/.test(part)) {
      if (currentLine.trim()) {
        result.push(currentLine.trim())
      }
      // 去掉开头的换行符
      currentLine = part.replace(/^\n/, '')
    } else {
      currentLine += part
    }
  }

  if (currentLine.trim()) {
    result.push(currentLine.trim())
  }

  return result.length > 0 ? result : [text.trim()]
}

const formatDate = (row, column, cellValue) => {
  if (!cellValue) return ''
  return new Date(cellValue).toLocaleString()
}

onMounted(() => {
  loadCases()
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
}

// 筛选栏
.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;

  :deep(.el-input__wrapper) {
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
    border-radius: 8px;
    background: #ffffff;

    &:hover,
    &:focus {
      box-shadow: 0 0 0 1px #7b42f6;
    }
  }

  :deep(.el-input__inner) {
    color: #5a32a3;
    font-weight: 500;
  }

  .reset-btn {
    background: #f8f7ff !important;
    border: 1px solid rgba(147, 112, 219, 0.2) !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    padding: 9px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;

    &:hover {
      background: #ede9fe !important;
      border-color: #7b42f6 !important;
      transform: translateY(-1px);
    }
  }

  .query-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;
    transition: all 0.3s ease !important;

    .el-icon {
      margin-right: 6px;
    }

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4) !important;
    }
  }

  .filter-bar-spacer {
    flex: 1;
  }

  .create-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;

    .el-icon {
      margin-right: 6px;
    }

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

// 表格容器
.card-container {
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
          text-align: center;
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
    padding: 16px 0;
    margin-top: 8px;
    background: transparent;
    border: none;
    transition: all 0.3s ease;

    /* 定义主题变量 - 浅紫色风格 */
    --primary-color: #a78bfa;
    --primary-dark: #8b5cf6;
    --primary-light: #f3f0ff;
    --text-primary: #262626;
    --text-secondary: #595959;
    --text-tertiary: #8c8c8c;

    /* 覆盖 Element Plus 默认主题变量 */
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

      // 总条数
      .el-pagination__total {
        color: #6b7280;
        font-size: 14px;
        font-weight: 500;
        margin-right: 12px;
      }

      // 每页条数选择器
      .el-pagination__sizes {
        margin-right: 12px;

        .el-select {
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
          }
        }
      }

      // 上一页/下一页按钮
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

      // 页码按钮
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

      // 跳转输入框
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
}

// 操作按钮容器
.action-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
}

// 操作按钮样式
.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px !important;
  border-radius: 8px;
  transition: all 0.3s ease;

  .el-icon {
    font-size: 14px;
  }

  span {
    font-size: 12px;
  }

  &.run-btn {
    background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }

  &.edit-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }

  &.delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(255, 77, 79, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }
}

.case-name-cell {
  padding: 4px 8px;
  line-height: 1.6;
}

.task-description-cell {
  line-height: 1.6;
  padding: 4px 8px;

  .task-description-text {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-align: left;
  }
}




</style>
