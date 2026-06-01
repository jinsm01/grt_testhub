<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">项目文档管理</h1>
        <p class="page-subtitle">管理项目下的需求文档，用于构建知识图谱</p>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select
        v-model="selectedProjectId"
        placeholder="选择项目"
        clearable
        @change="handleProjectChange"
        style="width: 280px;"
      >
        <el-option
          v-for="project in projectList"
          :key="project.id"
          :label="project.name"
          :value="project.id"
        />
      </el-select>
      <el-input
        v-model="searchKeyword"
        placeholder="搜索文档标题"
        clearable
        @input="handleSearch"
        style="width: 300px; margin-left: 16px;"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <div class="filter-bar-spacer"></div>
      <el-button
        type="primary"
        :disabled="!selectedProjectId"
        @click="showUploadDialog = true"
      >
        <el-icon><Plus /></el-icon>
        上传文档
      </el-button>
    </div>

    <!-- 文档列表 -->
    <div v-if="documentList.length > 0" class="card-container">
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="filteredDocumentList"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" header-align="center" align="center" />

        <el-table-column prop="id" label="文档ID" width="80" header-align="center" align="center" />

        <el-table-column prop="title" label="文档标题" min-width="250" show-overflow-tooltip header-align="center" align="left" />

        <el-table-column label="文档类型" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <el-tag :type="getDocumentTypeType(row.document_type)" size="small">
              {{ getDocumentTypeLabel(row.document_type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="文件大小" width="120" header-align="center" align="center">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>

        <el-table-column label="上传时间" width="180" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                size="small"
                type="primary"
                @click="viewDocument(row)"
              >
                <el-icon><View /></el-icon>
                <span>查看</span>
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="confirmDelete(row)"
              >
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

    <!-- 空状态 -->
    <div v-else-if="!loading && selectedProjectId" class="empty-state">
      <div class="empty-icon">
        <el-icon><Document /></el-icon>
      </div>
      <div class="empty-title">暂无文档</div>
      <div class="empty-desc">该项目下还没有上传文档，点击上方按钮上传文档</div>
    </div>

    <!-- 未选择项目状态 -->
    <div v-else-if="!selectedProjectId" class="empty-state">
      <div class="empty-icon">
        <el-icon><FolderOpened /></el-icon>
      </div>
      <div class="empty-title">请选择项目</div>
      <div class="empty-desc">请先选择一个项目来管理其文档</div>
    </div>

    <!-- 上传文档对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传文档"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="100px">
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="uploadForm.title" placeholder="请输入文档标题" />
        </el-form-item>
        <el-form-item label="文档文件" prop="file">
          <el-upload
            ref="uploadRef"
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :limit="1"
            :file-list="fileList"
            accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.gif"
          >
            <el-button type="primary">
              <el-icon><Upload /></el-icon>
              选择文件
            </el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF、Word、TXT、Markdown、图片格式，单个文件不超过 50MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showUploadDialog = false">取消</el-button>
          <el-button type="primary" :loading="uploading" @click="submitUpload">上传</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 查看文档对话框 -->
    <el-dialog
      v-model="showViewDialog"
      title="文档详情"
      width="800px"
      :close-on-click-modal="false"
    >
      <div v-if="currentDocument" class="document-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文档ID">{{ currentDocument.id }}</el-descriptions-item>
          <el-descriptions-item label="文档标题">{{ currentDocument.title }}</el-descriptions-item>
          <el-descriptions-item label="文档类型">
            <el-tag :type="getDocumentTypeType(currentDocument.document_type)" size="small">
              {{ getDocumentTypeLabel(currentDocument.document_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentDocument.status)" size="small">
              {{ getStatusLabel(currentDocument.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatFileSize(currentDocument.file_size) }}</el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ formatDateTime(currentDocument.created_at) }}</el-descriptions-item>
        </el-descriptions>
        <div class="document-content" v-if="currentDocument.extracted_text">
          <h4>提取的文本内容</h4>
          <el-input
            type="textarea"
            :rows="10"
            v-model="currentDocument.extracted_text"
            readonly
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, View, Delete, Document, FolderOpened, Upload } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

// 状态
const loading = ref(false)
const uploading = ref(false)
const showUploadDialog = ref(false)
const showViewDialog = ref(false)
const selectedProjectId = ref(null)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const projectList = ref([])
const documentList = ref([])
const selectedRows = ref([])
const currentDocument = ref(null)
const fileList = ref([])
const uploadFormRef = ref(null)
const uploadRef = ref(null)

// 上传表单
const uploadForm = reactive({
  title: '',
  file: null
})

// 表单校验规则
const uploadRules = {
  title: [
    { required: true, message: '请输入文档标题', trigger: 'blur' },
    { min: 2, max: 200, message: '长度在 2 到 200 个字符', trigger: 'blur' }
  ]
}

// 计算属性：过滤后的文档列表
const filteredDocumentList = computed(() => {
  if (!searchKeyword.value) return documentList.value
  const keyword = searchKeyword.value.toLowerCase()
  return documentList.value.filter(doc =>
    doc.title.toLowerCase().includes(keyword)
  )
})

// 获取项目列表
const fetchProjectList = async () => {
  try {
    const response = await api.get('/projects/')
    projectList.value = response.data.results || []
  } catch (error) {
    ElMessage.error('获取项目列表失败')
  }
}

// 获取文档列表
const fetchDocumentList = async () => {
  if (!selectedProjectId.value) return

  loading.value = true
  try {
    const response = await api.get(`/requirement-analysis/project-documents/`, {
      params: {
        project_id: selectedProjectId.value,
        page: currentPage.value,
        page_size: pageSize.value
      }
    })
    documentList.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取文档列表失败')
  } finally {
    loading.value = false
  }
}

// 项目切换
const handleProjectChange = () => {
  currentPage.value = 1
  searchKeyword.value = ''
  fetchDocumentList()
}

// 搜索
const handleSearch = () => {
  // 前端过滤，无需重新请求
}

// 分页
const handleSizeChange = (val) => {
  pageSize.value = val
  fetchDocumentList()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchDocumentList()
}

// 选择变化
const handleSelectionChange = (val) => {
  selectedRows.value = val
}

// 文件选择
const handleFileChange = (file) => {
  uploadForm.file = file.raw
  // 自动填充标题
  if (!uploadForm.title && file.name) {
    uploadForm.title = file.name.replace(/\.[^/.]+$/, '')
  }
}

// 文件移除
const handleFileRemove = () => {
  uploadForm.file = null
}

// 提交上传
const submitUpload = async () => {
  if (!uploadFormRef.value) return

  await uploadFormRef.value.validate(async (valid) => {
    if (!valid) return

    if (!uploadForm.file) {
      ElMessage.warning('请选择要上传的文件')
      return
    }

    uploading.value = true
    try {
      const formData = new FormData()
      formData.append('title', uploadForm.title)
      formData.append('file', uploadForm.file)
      formData.append('project', selectedProjectId.value)

      await api.post('/requirement-analysis/project-documents/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      ElMessage.success('上传成功')
      showUploadDialog.value = false
      resetUploadForm()
      fetchDocumentList()
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '上传失败')
    } finally {
      uploading.value = false
    }
  })
}

// 重置上传表单
const resetUploadForm = () => {
  uploadForm.title = ''
  uploadForm.file = null
  fileList.value = []
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

// 查看文档
const viewDocument = async (row) => {
  try {
    const response = await api.get(`/requirement-analysis/project-documents/${row.id}/`)
    currentDocument.value = response.data
    showViewDialog.value = true
  } catch (error) {
    ElMessage.error('获取文档详情失败')
  }
}

// 确认删除
const confirmDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除文档"${row.title}"吗？此操作不可恢复。`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await api.delete(`/requirement-analysis/project-documents/${row.id}/`)
      ElMessage.success('删除成功')
      fetchDocumentList()
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '删除失败')
    }
  })
}

// 工具函数
const formatDateTime = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const formatFileSize = (size) => {
  if (!size) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let index = 0
  let fileSize = size
  while (fileSize >= 1024 && index < units.length - 1) {
    fileSize /= 1024
    index++
  }
  return `${fileSize.toFixed(2)} ${units[index]}`
}

const getDocumentTypeLabel = (type) => {
  const typeMap = {
    'pdf': 'PDF',
    'docx': 'Word',
    'txt': '文本',
    'md': 'Markdown',
    'png': 'PNG',
    'jpg': 'JPG',
    'jpeg': 'JPEG',
    'gif': 'GIF'
  }
  return typeMap[type] || type
}

const getDocumentTypeType = (type) => {
  const typeColorMap = {
    'pdf': 'danger',
    'docx': 'primary',
    'txt': 'info',
    'md': 'success',
    'png': 'warning',
    'jpg': 'warning',
    'jpeg': 'warning',
    'gif': 'warning'
  }
  return typeColorMap[type] || ''
}

const getStatusLabel = (status) => {
  const statusMap = {
    'uploaded': '已上传',
    'analyzing': '分析中',
    'analyzed': '分析完成',
    'failed': '分析失败'
  }
  return statusMap[status] || status
}

const getStatusType = (status) => {
  const statusColorMap = {
    'uploaded': 'info',
    'analyzing': 'warning',
    'analyzed': 'success',
    'failed': 'danger'
  }
  return statusColorMap[status] || ''
}

// 初始化
onMounted(() => {
  fetchProjectList()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-bar-spacer {
  flex: 1;
}

.card-container {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.empty-icon {
  font-size: 64px;
  color: #d1d5db;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: #6b7280;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.time-text {
  color: #6b7280;
  font-size: 13px;
}

.document-detail {
  padding: 20px;
}

.document-content {
  margin-top: 20px;
}

.document-content h4 {
  margin-bottom: 12px;
  color: #374151;
}

:deep(.el-upload__tip) {
  color: #6b7280;
  font-size: 12px;
  margin-top: 8px;
}
</style>
