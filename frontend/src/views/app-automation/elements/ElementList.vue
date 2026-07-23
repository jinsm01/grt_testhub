<template>
  <div class="page-container">
    <!-- 顶部操作栏 -->
    <div class="filter-bar">
      <div class="filter-bar-left">
        <el-space wrap>
          <!-- 搜索 -->
          <el-input
            v-model="searchQuery"
            placeholder="搜索元素名称/标签"
            style="width: 250px"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
            <template #suffix>
              <el-button
                v-if="searchQuery"
                type="primary"
                link
                :icon="Search"
                @click="handleSearch"
                style="padding: 0"
              />
            </template>
          </el-input>

          <!-- 项目筛选 -->
          <el-select v-model="projectFilter" placeholder="全部项目" clearable filterable style="width: 160px" @change="handleSearch">
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>

          <!-- 类型筛选 -->
          <el-select v-model="typeFilter" placeholder="全部类型" clearable style="width: 140px" @change="loadElements">
            <el-option label="全部" value="" />
            <el-option label="图片" value="image" />
            <el-option label="坐标" value="pos" />
            <el-option label="区域" value="region" />
          </el-select>
        </el-space>
      </div>
      
      <!-- 操作按钮 -->
      <div class="filter-bar-right">
        <el-space>
          <el-button class="capture-btn" @click="showCaptureDialog">
            <el-icon><Camera /></el-icon>
            从设备创建
          </el-button>
          <el-button class="create-btn" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            手动创建
          </el-button>
        </el-space>
      </div>
    </div>
  
    <!-- 元素列表 -->
    <div class="card-container">
      <el-table
        :data="elements"
        v-loading="loading"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" header-align="center" align="center" />
        
        <el-table-column prop="name" label="元素名称" width="200" fixed="left" align="center">
          <template #default="{ row }">
            <el-link type="primary" @click="handleView(row)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        
        <el-table-column prop="element_type" label="类型" width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="getTypeStatusClass(row.element_type)">
              {{ getTypeName(row.element_type) }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column label="图片分类" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.element_type === 'image' && row.config?.image_category" class="status-badge processing">
              {{ row.config.image_category }}
            </span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="tags" label="标签" width="200">
          <template #default="{ row }">
            <template v-if="row.tags && row.tags.length > 0">
              <el-tag
                v-for="tag in row.tags"
                :key="tag"
                size="small"
                style="margin-right: 5px"
              >
                {{ tag }}
              </el-tag>
            </template>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        
        <!-- 预览 -->
        <el-table-column label="预览" width="200" header-align="center" align="center">
          <template #default="{ row }">
            <!-- 图片类型 -->
            <div v-if="row.element_type === 'image'" class="preview-image">
              <el-image
                :src="getImageUrl(row)"
                fit="contain"
                style="width: 150px; height: 80px; cursor: pointer"
                :preview-src-list="[getImageUrl(row)]"
                preview-teleported
              />
            </div>
            
            <!-- 坐标类型 -->
            <div v-else-if="row.element_type === 'pos'" class="preview-coords">
              <span class="coord-badge coord-x">X: {{ row.config?.x }}</span>
              <span class="coord-badge coord-y">Y: {{ row.config?.y }}</span>
            </div>
            
            <!-- 区域类型 -->
            <div v-else-if="row.element_type === 'region'" class="preview-region">
              <div class="region-row">
                <span class="coord-badge coord-x1">X1: {{ row.config?.x1 }}</span>
                <span class="coord-badge coord-y1">Y1: {{ row.config?.y1 }}</span>
              </div>
              <div class="region-row">
                <span class="coord-badge coord-x2">X2: {{ row.config?.x2 }}</span>
                <span class="coord-badge coord-y2">Y2: {{ row.config?.y2 }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="usage_count" label="使用次数" width="150" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.usage_count > 0" class="count-badge">{{ row.usage_count }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="创建时间" width="200" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="280" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" class="action-btn edit-btn" @click="handleEdit(row)">
                <el-icon><Edit /></el-icon>
                <span>编辑</span>
              </el-button>
              <el-button size="small" type="warning" class="action-btn run-btn" @click="handleDuplicate(row)">
                <el-icon><CopyDocument /></el-icon>
                <span>复制</span>
              </el-button>
              <el-button size="small" type="danger" class="action-btn delete-btn" @click="handleDelete(row)">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 批量操作栏 -->
      <div v-if="selectedElements.length > 0" class="batch-actions">
        <el-space>
          <span>已选择 {{ selectedElements.length }} 项</span>
          <el-button type="danger" size="small" @click="handleBatchDelete">
            批量删除
          </el-button>
        </el-space>
      </div>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="loadElements"
          @size-change="loadElements"
        />
      </div>
    </div>

    <!-- 从设备截图创建对话框 -->
    <CaptureElementDialog
      v-model="captureDialogVisible"
      :project-list="projectList"
      @success="handleCreateSuccess"
    />

    <!-- 手动创建/编辑对话框 -->
    <ManualElementDialog
      v-model="dialogVisible"
      :edit-data="editElement"
      :project-list="projectList"
      @success="handleCreateSuccess"
    />

    <!-- 查看详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="元素详情"
      width="800px"
    >
      <el-descriptions :column="2" border v-if="viewingElement">
        <el-descriptions-item label="元素名称">{{ viewingElement.name }}</el-descriptions-item>
        <el-descriptions-item label="元素类型">
          <el-tag :type="getTypeColor(viewingElement.element_type)">
            {{ getTypeName(viewingElement.element_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="标签" :span="2">
          <el-tag v-for="tag in viewingElement.tags" :key="tag" size="small" style="margin-right: 5px">
            {{ tag }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="配置信息" :span="2">
          <pre style="margin: 0; padding: 10px; background: #f5f7fa; border-radius: 4px;">{{ JSON.stringify(viewingElement.config, null, 2) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="使用次数">{{ viewingElement.usage_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(viewingElement.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAppElementList,
  createAppElement,
  deleteAppElement as apiDeleteAppElement,
  getAppProjects
} from '@/api/app-automation'
import { Search, Plus, Camera, Edit, CopyDocument, Delete, View } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/app-automation-helpers'
import CaptureElementDialog from './components/CaptureElementDialog.vue'
import ManualElementDialog from './components/ManualElementDialog.vue'

defineOptions({ name: 'AppElementList' })

// 状态
const loading = ref(false)
const elements = ref([])
const selectedElements = ref([])

// 筛选条件
const searchQuery = ref('')
const typeFilter = ref('')
const projectFilter = ref(null)
const projectList = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 对话框
const dialogVisible = ref(false)
const captureDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const editElement = ref(null)
const viewingElement = ref(null)

const loadElements = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      element_type: typeFilter.value
    }
    if (projectFilter.value) params.project = projectFilter.value
    
    // 只有搜索关键词不为空时才添加 search 参数
    if (searchQuery.value && searchQuery.value.trim()) {
      params.search = searchQuery.value.trim()
    }
    
    const res = await getAppElementList(params)
    elements.value = res.data.results || []
    total.value = res.data.count || 0
  } catch (error) {
    ElMessage.error('加载元素列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1  // 搜索时重置到第一页
  loadElements()
}

// 对话框操作
const showCreateDialog = () => {
  editElement.value = null
  dialogVisible.value = true
}

const showCaptureDialog = () => {
  captureDialogVisible.value = true
}

const handleView = (element) => {
  viewingElement.value = element
  detailDialogVisible.value = true
}

const handleEdit = (element) => {
  editElement.value = element
  dialogVisible.value = true
}

// 智能生成唯一的副本名称
const findAvailableName = (baseName) => {
  // 先尝试 "原名_副本"
  const firstCandidate = `${baseName}_副本`
  if (!elements.value.some(el => el.name === firstCandidate)) {
    return firstCandidate
  }
  
  // 查找 "原名_副本(n)" 中的最大 n
  const pattern = new RegExp(`^${baseName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}_副本\\((\\d+)\\)$`)
  let maxNum = 1
  
  elements.value.forEach(el => {
    const match = el.name.match(pattern)
    if (match) {
      const num = parseInt(match[1])
      if (num > maxNum) {
        maxNum = num
      }
    }
  })
  
  return `${baseName}_副本(${maxNum + 1})`
}

const handleDuplicate = async (element) => {
  try {
    // 智能生成唯一名称
    const newName = findAvailableName(element.name)
    
    // 复制配置，移除 file_hash（避免重复检测）
    const newConfig = { ...element.config }
    delete newConfig.file_hash  // 允许多个元素共享同一图片
    
    // 复制元素数据
    const duplicateData = {
      ...element,
      name: newName,
      id: undefined,
      created_at: undefined,
      updated_at: undefined,
      created_by: undefined,
      created_by_id: undefined,
      last_used_at: undefined,
      usage_count: 0,
      config: newConfig  // 使用清理后的配置
    }
    
    await createAppElement(duplicateData)
    ElMessage.success(`已复制为 "${newName}"`)
    loadElements()
  } catch (error) {
    console.error('复制失败:', error)
    const errorMsg = error.response?.data?.config?.[0] ||
                     error.response?.data?.name?.[0] || 
                     error.response?.data?.message || 
                     '复制失败'
    ElMessage.error(errorMsg)
  }
}

const handleCreateSuccess = () => {
  loadElements()
}

const handleSelectionChange = (selection) => {
  selectedElements.value = selection
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedElements.value.length} 个元素吗？`,
      '批量删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    for (const element of selectedElements.value) {
      await apiDeleteAppElement(element.id)
    }
    
    ElMessage.success('批量删除成功')
    selectedElements.value = []
    loadElements()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

const handleDelete = async (element) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除元素 "${element.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await apiDeleteAppElement(element.id)
    ElMessage.success('删除成功')
    loadElements()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 获取图片URL
const getImageUrl = (element) => {
  if (!element?.id) return ''
  // 使用 updated_at 作为版本号，确保图片更新后能刷新
  const timestamp = element.updated_at ? new Date(element.updated_at).getTime() : Date.now()
  return `/api/app-automation/elements/${element.id}/preview/?t=${timestamp}`
}

const getTypeColor = (type) => {
  const colorMap = {
    'image': 'primary',
    'pos': 'success',
    'region': 'warning'
  }
  return colorMap[type] || 'info'
}

// 获取类型对应的徽章样式类
const getTypeStatusClass = (type) => {
  const classMap = {
    'image': 'success',      // 图片类型 - 绿色
    'pos': 'processing',     // 坐标类型 - 橙色
    'region': 'pending'      // 区域类型 - 灰色
  }
  return classMap[type] || 'pending'
}

const getTypeName = (type) => {
  const nameMap = {
    'image': '图片',
    'pos': '坐标',
    'region': '区域'
  }
  return nameMap[type] || type
}

// formatDateTime 已从 app-automation-helpers 导入

onMounted(() => {
  getAppProjects({ page_size: 100 }).then(res => { projectList.value = res.data.results || res.data || [] }).catch(() => {})
  loadElements()
})
</script>

<style scoped lang="scss">
.page-container {
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
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(167, 139, 250, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;

  .filter-bar-left {
    display: flex;
    align-items: center;

    :deep(.el-select) {
      .el-input__wrapper {
        border-radius: 8px;
        box-shadow: 0 0 0 1px rgba(167, 139, 250, 0.25) inset;
        background: #ffffff;

        &:hover, &.is-focus {
          box-shadow: 0 0 0 1px #7b42f6 inset;
        }
      }
    }

    :deep(.el-radio-group) {
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 0 0 1px rgba(167, 139, 250, 0.25);

      .el-radio-button__inner {
        border: none !important;
        color: #5a32a3;
        font-weight: 500;
        transition: all 0.3s ease;

        &:hover {
          color: #7b42f6;
          background: #f5f3ff;
        }
      }

      .el-radio-button.is-active .el-radio-button__inner {
        background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%) !important;
        color: #ffffff !important;
        box-shadow: none !important;
      }
    }
  }

  .filter-bar-right {
    display: flex;
    align-items: center;
  }

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

  .capture-btn {
    background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;

    &:hover {
      background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4) !important;
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

    .el-link { font-weight: 500; }

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
      display: flex;
      align-items: center;
      justify-content: center;
    }

    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;
    }
  }

  .preview-image {
    padding: 5px;

    :deep(.el-image) {
      border: 1px solid #e4e7ed;
      border-radius: 4px;
      overflow: hidden;

      &:hover {
        border-color: #a78bfa;
      }
    }
  }

  .batch-actions {
    margin-top: 15px;
    padding: 10px;
    background: #f5f3ff;
    border: 1px solid rgba(167, 139, 250, 0.2);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;

    span {
      color: #8b5cf6;
      font-weight: 500;
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
}

:deep(pre) {
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.5;
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

// 灰色文本
.text-gray {
  color: #909399;
}

// 坐标徽章样式
.coord-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;

  &.coord-x, &.coord-y {
    background: #e6f7ff;
    color: #1890ff;
    margin: 2px;
  }

  &.coord-x1, &.coord-y1 {
    background: #f6ffed;
    color: #52c41a;
    margin: 2px;
  }

  &.coord-x2, &.coord-y2 {
    background: #fff7e6;
    color: #fa8c16;
    margin: 2px;
  }
}

// 预览坐标容器
.preview-coords {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 4px;
}

// 预览区域容器
.preview-region {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;

  .region-row {
    display: flex;
    gap: 4px;
  }
}
</style>
