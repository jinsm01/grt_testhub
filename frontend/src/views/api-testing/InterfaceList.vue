<template>
  <div class="page-container">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="filter-section">
        <el-select v-model="selectedProject" :placeholder="$t('apiTesting.common.selectProject')" @change="onProjectChange" class="project-select" style="width: 200px;">
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
        <el-select v-model="selectedCollection" placeholder="选择所属合集" clearable @change="onCollectionChange" class="collection-select" style="width: 200px;">
          <el-option :label="'全部合集'" :value="''" />
          <el-option
            v-for="collection in flatCollections"
            :key="collection.id"
            :label="collection.name"
            :value="collection.id"
          />
        </el-select>
        <el-input v-model="searchName" placeholder="输入接口名称搜索" clearable @keyup.enter="handleSearch" class="search-input" style="width: 200px;">
          <template #suffix>
            <el-icon @click="handleSearch" style="cursor: pointer;"><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <div class="header-actions">
        <!-- 创建集合按钮已隐藏，请使用合集管理页面 -->
        <el-button v-if="selectedRows.length > 0" type="danger" class="batch-delete-btn" @click="batchDelete">
          批量删除 ({{ selectedRows.length }})
        </el-button>
        <el-button class="import-btn" @click="showImportDialog = true">
          <el-icon style="margin-right: 4px;"><Upload /></el-icon>
          导入接口
        </el-button>
        <el-button class="add-element-btn" @click="createNewRequest">
          <el-icon style="margin-right: 4px;"><Plus /></el-icon>
          {{ $t('apiTesting.interface.addInterface') }}
        </el-button>
      </div>
    </div>

    <!-- 接口列表卡片 -->
    <div class="card-container">
      <!-- 接口列表表格 -->
      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="10" animated />
      </div>
      
      <div v-else-if="interfaceList.length === 0" class="empty-state">
        <el-empty :description="$t('apiTesting.interface.noInterfaces')" />
      </div>

      <div v-else class="interface-table-wrapper">
        <el-table
          ref="tableRef"
          :data="interfaceList"
          v-loading="loading"
          style="width: 100%"
          class="custom-table"
          @row-click="goToDetail"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" align="center" />
          <el-table-column label="序号" width="90" header-align="center" align="center">
            <template #default="{ $index }">
              {{ (currentPage - 1) * pageSize + $index + 1 }}
            </template>
          </el-table-column>
          <el-table-column label="接口名称" min-width="200" header-align="center" align="center">
            <template #default="{ row }">
              <div style="text-align: center; width: 100%;">{{ row.name }}</div>
            </template>
          </el-table-column>
          <el-table-column label="请求方式" width="140" header-align="center" align="center">
            <template #default="{ row }">
              <span 
                v-if="row.request_type !== 'WEBSOCKET'" 
                class="status-badge"
                :class="row.method?.toLowerCase()"
              >
                {{ row.method }}
              </span>
              <span v-else class="status-badge websocket">WebSocket</span>
            </template>
          </el-table-column>

          <el-table-column label="创建人" width="150" header-align="center" align="center">
            <template #default="{ row }">
              <span>{{ row.created_by?.username || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="200" header-align="center" align="center">
            <template #default="{ row }">
              <span>{{ row.updated_at ? new Date(row.updated_at).toLocaleString() : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right" header-align="center" align="center">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button size="small" type="primary" class="action-btn edit-btn" @click.stop="goToDetail(row)">
                  <el-icon><Edit /></el-icon>
                  <span>编辑</span>
                </el-button>
                <el-button size="small" type="danger" class="action-btn delete-btn" @click.stop="deleteRequest(row)">
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
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>

    <!-- 创建集合对话框 -->
    <el-dialog
      v-model="showCreateCollectionDialog"
      :title="$t('apiTesting.interface.createCollection')"
      width="500px"
    >
      <el-form :model="collectionForm" label-width="100px">
        <el-form-item :label="$t('apiTesting.interface.collectionName')">
          <el-input v-model="collectionForm.name" />
        </el-form-item>
        <el-form-item :label="$t('apiTesting.common.description')">
          <el-input v-model="collectionForm.description" type="textarea" />
        </el-form-item>
        <el-form-item :label="$t('apiTesting.interface.parentCollection')">
          <el-select v-model="collectionForm.parent" clearable :placeholder="$t('apiTesting.common.pleaseSelect')">
            <el-option :label="$t('apiTesting.common.none')" :value="null" />
            <el-option
              v-for="collection in flatCollections"
              :key="collection.id"
              :label="collection.name"
              :value="collection.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateCollectionDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="createCollection">{{ $t('apiTesting.common.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 导入接口对话框 -->
    <ImportDialog
      v-model="showImportDialog"
      :collections="flatCollections"
      :project-id="selectedProject"
      @success="loadRequests"
      @import-global-headers="handleImportGlobalHeaders"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Folder, Plus, Document, Edit, Delete, Connection, Search, Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import ImportDialog from './components/ImportDialog.vue'

const router = useRouter()
const { t } = useI18n()

const loading = ref(false)
const projects = ref([])
const selectedProject = ref('')
const collections = ref([])
const flatCollections = ref([])
const interfaceList = ref([])
const expandedCollections = ref([])
const showCreateCollectionDialog = ref(false)
const showImportDialog = ref(false)
const selectedRows = ref([])
const tableRef = ref(null)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 筛选相关
const selectedCollection = ref('')
const searchName = ref('')

const collectionForm = ref({
  name: '',
  description: '',
  parent: null
})

onMounted(() => {
  loadProjects()
})

const loadProjects = async () => {
  try {
    const res = await api.get('/api-testing/projects/')
    console.log('Projects loaded:', res.data)
    // 处理分页返回格式
    const projectList = res.data.results || res.data || []
    projects.value = projectList
    if (projects.value.length > 0) {
      selectedProject.value = projects.value[0].id
      console.log('Selected project:', selectedProject.value)
      await loadCollections()
    }
  } catch (error) {
    console.error('Load projects error:', error)
    ElMessage.error('加载项目列表失败：' + (error.message || '未知错误'))
  }
}

const onProjectChange = () => {
  loadCollections()
}

const loadCollections = async () => {
  if (!selectedProject.value) return
  
  loading.value = true
  try {
    // 1. 加载集合
    const res = await api.get('/api-testing/collections/', {
      params: { project: selectedProject.value }
    })
    const collectionList = res.data.results || res.data || []
    
    // 构建集合树（标记 type 为 collection）
    collections.value = buildTree(collectionList.map(c => ({ ...c, type: 'collection' })))
    flatCollections.value = collectionList
    
    // 默认展开所有集合
    expandedCollections.value = collectionList.map(c => c.id)
    
    // 2. 加载请求并关联到集合
    await loadRequests()
    
  } catch (error) {
    console.error('Load collections error:', error)
    ElMessage.error('加载集合失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const loadRequests = async () => {
  if (!selectedProject.value) return

  try {
    const params = {
      project: selectedProject.value,
      page: currentPage.value,
      page_size: pageSize.value
    }

    // 添加合集筛选
    if (selectedCollection.value) {
      params.collection = selectedCollection.value
    }

    // 添加名称搜索
    if (searchName.value) {
      params.search = searchName.value
    }

    const res = await api.get('/api-testing/requests/', { params })
    const requests = res.data.results || res.data || []
    const count = res.data.count !== undefined ? res.data.count : requests.length

    // 去重：根据接口名称去重，保留最近更新的数据（updated_at 更大的）
    const requestMap = new Map()
    for (const request of requests) {
      const existing = requestMap.get(request.name)
      if (!existing) {
        requestMap.set(request.name, request)
      } else {
        // 如果已存在，比较 updated_at，保留最近更新的
        const existingTime = new Date(existing.updated_at || 0).getTime()
        const currentTime = new Date(request.updated_at || 0).getTime()
        if (currentTime > existingTime) {
          requestMap.set(request.name, request)
        }
      }
    }
    const uniqueRequests = Array.from(requestMap.values())

    console.log('接口列表去重:', requests.length, '->', uniqueRequests.length, '条')
    if (requests.length !== uniqueRequests.length) {
      console.log('重复数据:', requests.filter(r => requests.filter(x => x.name === r.name).length > 1).map(r => ({ id: r.id, name: r.name })))
    }

    // 填充接口列表（用于表格展示）
    interfaceList.value = uniqueRequests
    total.value = uniqueRequests.length

    // 将请求添加到对应集合中
    requests.forEach(request => {
      if (request.collection) {
        const collection = findCollectionById(collections.value, request.collection)
        if (collection) {
          if (!collection.children) collection.children = []
          collection.children.push({
            ...request,
            type: 'request'
          })
        }
      }
    })
  } catch (error) {
    console.error('Load requests error:', error)
  }
}

// 分页大小变化
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  loadRequests()
}

// 页码变化
const handleCurrentChange = (val) => {
  currentPage.value = val
  loadRequests()
}

// 合集筛选变化
const onCollectionChange = () => {
  currentPage.value = 1
  loadRequests()
}

// 搜索接口名称
const handleSearch = () => {
  currentPage.value = 1
  loadRequests()
}

// 获取合集名称
const getCollectionName = (collectionId) => {
  if (!collectionId) return '未分类'
  const collection = flatCollections.value.find(c => c.id === collectionId)
  return collection ? collection.name : '未分类'
}

// 删除接口
const deleteRequest = async (row) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除此接口吗？',
      '确认删除',
      { type: 'warning' }
    )
    await api.delete(`/api-testing/requests/${row.id}/`)
    ElMessage.success('删除成功')
    // 如果被删除的接口在选中行中，从选中行中移除
    const index = selectedRows.value.findIndex(r => r.id === row.id)
    if (index > -1) {
      selectedRows.value.splice(index, 1)
    }
    // 清空表格选中状态
    if (tableRef.value) {
      tableRef.value.clearSelection()
    }
    // 如果当前页只有这一条数据，回到第一页
    if (interfaceList.value.length <= 1 && currentPage.value > 1) {
      currentPage.value = 1
    }
    await loadRequests()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 批量删除
const batchDelete = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要删除的接口')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRows.value.length} 个接口吗？`,
      '确认批量删除',
      { type: 'warning' }
    )

    // 依次删除选中的接口，使用 Promise.allSettled 处理部分失败
    const deletePromises = selectedRows.value.map(row =>
      api.delete(`/api-testing/requests/${row.id}/`).then(() => ({ success: true, id: row.id })).catch(err => ({ success: false, id: row.id, error: err }))
    )

    const results = await Promise.allSettled(deletePromises)
    const successCount = results.filter(r => r.status === 'fulfilled' && r.value.success).length
    const failCount = results.length - successCount

    if (successCount > 0) {
      ElMessage.success(`成功删除 ${successCount} 个接口`)
    }
    if (failCount > 0) {
      ElMessage.error(`${failCount} 个接口删除失败`)
    }

    selectedRows.value = []
    // 清空表格选中状态
    if (tableRef.value) {
      tableRef.value.clearSelection()
    }
    // 如果当前页没有数据了，回到第一页
    const remainingOnPage = interfaceList.value.length - successCount
    if (remainingOnPage <= 0 && currentPage.value > 1) {
      currentPage.value = 1
    }
    await loadRequests()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

const findCollectionById = (collections, id) => {
  for (const collection of collections) {
    if (collection.id === id) return collection
    if (collection.children) {
      const found = findCollectionById(collection.children, id)
      if (found) return found
    }
  }
  return null
}

const buildTree = (data) => {
  if (!data || !Array.isArray(data)) return []
  
  const map = {}
  const tree = []
  
  // 初始化所有节点
  data.forEach(item => {
    if (item && item.id) {
      map[item.id] = { ...item, children: [] }
    }
  })
  
  // 构建树结构
  data.forEach(item => {
    if (!item || !item.id) return
    
    // 判断是否为集合类型（可能是 'collection' 或 'folder' 或没有 type 但有 children）
    const isCollection = item.type === 'collection' || item.type === 'folder' || 
                         (!item.type && !item.collection) ||
                         (item.children && item.children.length > 0)
    
    // 判断是否为请求类型
    const isRequest = item.type === 'request' || item.collection
    
    if (isCollection) {
      // 集合类型：通过 parent 关联
      if (item.parent && map[item.parent]) {
        map[item.parent].children.push(map[item.id])
      } else if (!item.parent) {
        tree.push(map[item.id])
      }
    } else if (isRequest) {
      // 请求类型：通过 collection 关联到集合
      if (item.collection && map[item.collection]) {
        map[item.collection].children.push(map[item.id])
      }
    }
  })
  
  return tree
}

const getRequests = (collection) => {
  if (!collection || !collection.children) return []
  return collection.children.filter(child => {
    if (!child) return false
    // 判断是否为请求类型
    return child.type === 'request' || child.collection || child.method
  })
}

const getRequestCount = (collection) => {
  if (!collection) return 0
  return getRequests(collection).length
}

const toggleCollection = (id) => {
  const index = expandedCollections.value.indexOf(id)
  if (index > -1) {
    expandedCollections.value.splice(index, 1)
  } else {
    expandedCollections.value.push(id)
  }
}

const goToDetail = (request) => {
  router.push({
    name: 'ApiInterfaceDetail',
    params: { id: request.id }
  })
}

const createNewRequest = () => {
  router.push({
    name: 'ApiInterfaceCreate'
  })
}

// 处理导入的全局 headers（在列表页仅作提示）
const handleImportGlobalHeaders = (globalHeaders) => {
  if (!globalHeaders || globalHeaders.length === 0) return
  ElMessage.info(`导入完成，包含 ${globalHeaders.length} 个全局 Header 参数，请在接口详情页查看`)
}

const createCollection = async () => {
  if (!selectedProject.value) {
    ElMessage.error('请先选择项目')
    return
  }
  if (!collectionForm.value.name.trim()) {
    ElMessage.error('请输入集合名称')
    return
  }
  try {
    const data = {
      name: collectionForm.value.name.trim(),
      description: collectionForm.value.description,
      parent: collectionForm.value.parent || null,
      project: selectedProject.value
    }
    await api.post('/api-testing/collections/', data)
    ElMessage.success(t('apiTesting.messages.success.collectionCreated'))
    showCreateCollectionDialog.value = false
    collectionForm.value = { name: '', description: '', parent: null }
    await loadCollections()
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.response?.data?.message || t('apiTesting.messages.error.createFailed')
    ElMessage.error(errorMsg)
  }
}
</script>

<style scoped lang="scss">
.page-container {
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

  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 20px 24px;

  .filter-section {
    display: flex;
    align-items: center;
    gap: 12px;

    // 覆盖全局的紫色背景变量
    --el-fill-color-blank: #ffffff;

    :deep(.el-input__wrapper),
    :deep(.el-select .el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
      background: #ffffff !important;

      &:hover {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }

      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }

    :deep(.el-input__inner) {
      color: #5a32a3;
      font-weight: 500;
    }

    .project-select,
    .collection-select,
    .search-input {
      :deep(.el-input__wrapper) {
        border-radius: 8px;
        box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
        background: #ffffff;

        &:hover {
          box-shadow: 0 0 0 1px #7b42f6 inset;
        }

        &.is-focus {
          box-shadow: 0 0 0 1px #7b42f6 inset;
        }
      }

      :deep(.el-input__inner) {
        color: #5a32a3;
        font-weight: 500;
      }
    }

    .search-input {
      :deep(.el-input__prefix) {
        color: #9ca3af;
      }
    }
  }

  .header-actions {
    display: flex;
    gap: 1px;
  }
}

.card-container {
  flex: 1;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;
}

.loading-state {
  padding: 40px;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.interface-table-wrapper {
  padding: 0 20px 20px;
  height: 100%;
}

// 自定义表格样式
.custom-table {
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
  --el-fill-color-blank: #ffffff;

  :deep(.el-table__inner-wrapper) {
    background-color: transparent !important;
  }

  :deep(.el-table__header-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__header) {
    background-color: #ffffff !important;
  }

  :deep(th) {
    background-color: #ffffff !important;
    color: #5a32a3 !important;
    font-weight: 600;
    font-size: 14px;
    border-bottom: 1px solid #e9ecef;
    padding: 16px !important;
    text-align: center;
    transition: all 0.3s ease;

    &:hover {
      background-color: #ffffff !important;
    }
  }

  :deep(th .cell) {
    font-weight: 600;
    color: #5a32a3;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  :deep(.el-table__body-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(tr) {
    transition: all 0.3s ease;
    cursor: pointer;
    background-color: #ffffff !important;

    &:hover {
      background-color: #f8f7ff !important;
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(123, 66, 246, 0.1);
    }
  }

  :deep(td) {
    padding: 12px 16px;
    border-bottom: 1px solid #e9ecef;
    color: #333;
    font-size: 14px;
    font-weight: 400;
    line-height: 24px;
    transition: all 0.3s ease;
    vertical-align: middle;
    text-align: center;
    background-color: transparent !important;

    .cell {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 24px;
    }
  }

  :deep(.el-table__empty-block) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-right-patch) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-body-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-header-wrapper) {
    background-color: #ffffff !important;
  }

}

.interface-name-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  .el-icon {
    color: #909399;
  }
}

.collection-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #606266;

  .el-icon {
    color: #e6a23c;
  }
}

// 状态徽章样式
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 0;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
  white-space: nowrap;
  width: 72px;

  &.get {
    background: #f6ffed;
    color: #52c41a;
  }

  &.post {
    background: #e6f7ff;
    color: #1890ff;
  }

  &.put {
    background: #fff7e6;
    color: #fa8c16;
  }

  &.delete {
    background: #fff2f0;
    color: #f5222d;
  }

  &.patch {
    background: #f9f0ff;
    color: #722ed1;
  }

  &.options {
    background: #e6fffb;
    color: #13c2c2;
  }

  &.head {
    background: #fff0f6;
    color: #eb2f96;
  }

  &.websocket {
    background: #f6ffed;
    color: #52c41a;
  }
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
    border: none !important;
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
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
    }
  }
}

.interface-list {
  padding: 20px;
}

.collection-group {
  margin-bottom: 8px;
}

.collection-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f8f7ff;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  color: #5a32a3;

  &:hover {
    background: #f0edff;
  }

  .expand-icon {
    transition: transform 0.3s ease;
    
    &.expanded {
      transform: rotate(90deg);
    }
  }

  .collection-name {
    flex: 1;
  }

  .request-count {
    font-size: 12px;
    color: #909399;
  }
}

.request-list {
  padding-left: 24px;
  margin-top: 4px;
}

.request-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #606266;

  &:hover {
    background: rgba(123, 66, 246, 0.08);
    color: #7b42f6;
  }

  .request-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .method-tag {
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    color: white;
    font-weight: 600;

    &.get { background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%); }
    &.post { background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%); }
    &.put { background: linear-gradient(135deg, #e6a23c 0%, #ebb563 100%); }
    &.delete { background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%); }
    &.patch { background: linear-gradient(135deg, #909399 0%, #a6a9ad 100%); }
  }
}

.no-requests {
  padding: 16px;
  color: #909399;
  font-size: 14px;
  text-align: center;
}

.create-btn {
  height: 36px;
  padding: 0 18px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  background: #7b42f6;
  border: 1px solid #7b42f6;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);

  &:hover {
    background: #6d33e6;
    border-color: #6d33e6;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
  }

  &:active {
    transform: translateY(0);
  }
}

.batch-delete-btn {
  height: 36px;
  padding: 0 18px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  background: #ff4d4f;
  border: 1px solid #ff4d4f;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(255, 77, 79, 0.3);

  &:hover {
    background: #f5222d;
    border-color: #f5222d;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(255, 77, 79, 0.4);
  }

  &:active {
    transform: translateY(0);
  }
}

.import-btn {
  height: 36px;
  padding: 0 18px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  background: #52c41a;
  border: 1px solid #52c41a;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(82, 196, 26, 0.3);

  &:hover {
    background: #389e0d;
    border-color: #389e0d;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(82, 196, 26, 0.4);
  }

  &:active {
    transform: translateY(0);
  }
}

.add-element-btn {
  height: 36px;
  padding: 0 18px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  background: #7b42f6;
  border: 1px solid #7b42f6;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);

  &:hover {
    background: #8b5cf6;
    border-color: #8b5cf6;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
  }

  &:active {
    transform: translateY(0);
  }
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
</style>
