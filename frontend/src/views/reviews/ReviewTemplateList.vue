<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('reviewTemplate.title') }}</h1>
      <div>
        <el-button type="primary" @click="createTemplate">
          <el-icon><Plus /></el-icon>
          {{ $t('reviewTemplate.createTemplate') }}
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item :label="$t('reviewTemplate.project')">
          <el-select v-model="filters.project" :placeholder="$t('reviewTemplate.selectProject')" clearable @change="fetchTemplates">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <div class="templates-grid">
      <el-card
        v-for="template in templates"
        :key="template.id"
        class="template-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <span class="template-name">{{ template.name }}</span>
            <div class="card-actions">
              <el-button link type="primary" @click="useTemplate(template)">{{ $t('reviewTemplate.useTemplate') }}</el-button>
              <el-button link type="warning" @click="editTemplate(template)">{{ $t('reviewTemplate.edit') }}</el-button>
              <el-button link type="danger" @click="deleteTemplate(template.id)">{{ $t('reviewTemplate.delete') }}</el-button>
            </div>
          </div>
        </template>

        <div class="template-content">
          <div class="template-info">
            <div class="info-item">
              <span class="info-label">{{ $t('reviewTemplate.projectLabel') }}</span>
              <span class="info-value">
                {{ Array.isArray(template.project)
                    ? template.project.map(p => p.name).join(', ')
                    : (template.project?.name || $t('reviewTemplate.noData')) }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ $t('reviewTemplate.creatorLabel') }}</span>
              <span class="info-value">{{ template.creator?.username }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ $t('reviewTemplate.createdAtLabel') }}</span>
              <span class="info-value">{{ formatDate(template.created_at) }}</span>
            </div>
          </div>

          <div class="template-description">
            {{ template.description || $t('reviewTemplate.noDescription') }}
          </div>

          <div class="template-checklist">
            <div class="checklist-title">{{ $t('reviewTemplate.checklistTitle') }}</div>
            <ul v-if="template.checklist?.length">
              <li v-for="(item, index) in template.checklist.slice(0, 3)" :key="index">
                {{ item }}
              </li>
              <li v-if="template.checklist.length > 3" class="more-items">
                {{ $t('reviewTemplate.moreItems', { count: template.checklist.length - 3 }) }}
              </li>
            </ul>
            <div v-else class="empty-checklist">{{ $t('reviewTemplate.noChecklist') }}</div>
          </div>

          <div class="template-reviewers">
            <div class="reviewers-title">{{ $t('reviewTemplate.reviewersTitle') }}</div>
            <div class="reviewers-list">
              <el-tag
                v-for="reviewer in template.default_reviewers"
                :key="reviewer.id"
                size="small"
                class="reviewer-tag"
              >
                {{ reviewer.username }}
              </el-tag>
              <span v-if="!template.default_reviewers?.length" class="empty-reviewers">
                {{ $t('reviewTemplate.noReviewers') }}
              </span>
            </div>
          </div>
        </div>
      </el-card>

      <div v-if="!templates.length && !loading" class="empty-templates">
        <el-empty :description="$t('reviewTemplate.noData')" />
      </div>
    </div>

    <!-- 模板表单对话框 -->
    <el-dialog
      v-model="templateDialogVisible"
      :title="isEdit ? $t('reviewTemplate.editTitle') : $t('reviewTemplate.createTitle')"
      width="800px"
    >
      <el-form :model="templateForm" :rules="templateRules" ref="templateFormRef" label-width="120px">
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item :label="$t('reviewTemplate.templateName')" prop="name">
              <el-input v-model="templateForm.name" :placeholder="$t('reviewTemplate.templateNamePlaceholder')" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('reviewTemplate.associatedProject')" prop="project">
              <el-select v-model="templateForm.project" :placeholder="$t('reviewTemplate.selectProject')" @change="onProjectChange">
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="$t('reviewTemplate.templateDescription')">
          <el-input
            v-model="templateForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('reviewTemplate.templateDescriptionPlaceholder')"
          />
        </el-form-item>

        <el-form-item :label="$t('reviewTemplate.checklist')">
          <div class="checklist-editor">
            <div
              v-for="(item, index) in templateForm.checklist"
              :key="index"
              class="checklist-item"
            >
              <el-input
                v-model="templateForm.checklist[index]"
                :placeholder="$t('reviewTemplate.checklistItemPlaceholder')"
              />
              <el-button
                type="danger"
                size="small"
                @click="removeChecklistItem(index)"
                :icon="Delete"
              />
            </div>
            <el-button type="primary" size="small" @click="addChecklistItem">
              <el-icon><Plus /></el-icon>
              {{ $t('reviewTemplate.addChecklistItem') }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item :label="$t('reviewTemplate.defaultReviewers')">
          <el-select
            v-model="templateForm.default_reviewers"
            multiple
            :placeholder="$t('reviewTemplate.selectDefaultReviewers')"
          >
            <el-option
              v-for="user in projectUsers"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="templateDialogVisible = false">{{ $t('reviewTemplate.cancel') }}</el-button>
          <el-button type="primary" @click="saveTemplate" :loading="saving">{{ $t('reviewTemplate.save') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const router = useRouter()
const { t } = useI18n()

const templates = ref([])
const projects = ref([])
const projectUsers = ref([])
const loading = ref(false)
const templateDialogVisible = ref(false)
const templateFormRef = ref()
const saving = ref(false)
const isEdit = ref(false)
const editingTemplateId = ref(null)

const filters = reactive({
  project: ''
})

const templateForm = reactive({
  name: '',
  description: '',
  project: '',
  checklist: [''],
  default_reviewers: []
})

const templateRules = {
  name: [{ required: true, message: t('reviewTemplate.nameRequired'), trigger: 'blur' }],
  project: [{ required: true, message: t('reviewTemplate.projectRequired'), trigger: 'change' }]
}

const fetchTemplates = async () => {
  loading.value = true
  try {
    const params = {}
    if (filters.project) {
      params.project = filters.project
    }

    const response = await api.get('/reviews/review-templates/', { params })
    templates.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(t('reviewTemplate.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(t('reviewTemplate.fetchProjectsFailed'))
  }
}

const fetchProjectUsers = async () => {
  try {
    const response = await api.get('/auth/users/')
    projectUsers.value = response.data.results || response.data || []
  } catch (error) {
    console.error('获取用户列表失败:', error)
    ElMessage.error(t('reviewTemplate.fetchUsersFailed'))
    projectUsers.value = []
  }
}

const createTemplate = () => {
  isEdit.value = false
  resetTemplateForm()
  templateDialogVisible.value = true
}

const editTemplate = (template) => {
  isEdit.value = true
  editingTemplateId.value = template.id
  
  templateForm.name = template.name
  templateForm.description = template.description
  // 处理project字段：如果是数组，取第一个ID；如果是单个对象，取其ID
  if (Array.isArray(template.project) && template.project.length > 0) {
    templateForm.project = template.project[0].id
  } else if (template.project && template.project.id) {
    templateForm.project = template.project.id
  } else {
    templateForm.project = ''
  }
  templateForm.checklist = template.checklist.length ? [...template.checklist] : ['']
  templateForm.default_reviewers = template.default_reviewers.map(u => u.id)
  
  // 用户列表已经在页面加载时获取，不需要重新获取
  templateDialogVisible.value = true
}

const useTemplate = (template) => {
  // 使用模板创建评审
  router.push({
    path: '/ai-generation/reviews/create',
    query: { template: template.id }
  })
}

const saveTemplate = async () => {
  if (!templateFormRef.value) return

  try {
    await templateFormRef.value.validate()
    saving.value = true

    const data = {
      ...templateForm,
      checklist: templateForm.checklist.filter(item => item.trim()),
      // 将project转换为数组格式，因为后端期望的是列表
      project: templateForm.project ? [templateForm.project] : []
    }

    if (isEdit.value) {
      await api.put(`/reviews/review-templates/${editingTemplateId.value}/`, data)
      ElMessage.success(t('reviewTemplate.updateSuccess'))
    } else {
      await api.post('/reviews/review-templates/', data)
      ElMessage.success(t('reviewTemplate.createSuccess'))
    }

    templateDialogVisible.value = false
    fetchTemplates()

  } catch (error) {
    console.error('保存模板失败:', error)
    ElMessage.error(isEdit.value ? t('reviewTemplate.updateFailed') : t('reviewTemplate.createFailed'))
  } finally {
    saving.value = false
  }
}

const deleteTemplate = async (id) => {
  try {
    await ElMessageBox.confirm(t('reviewTemplate.deleteConfirm'), t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })

    await api.delete(`/reviews/review-templates/${id}/`)
    ElMessage.success(t('reviewTemplate.deleteSuccess'))
    fetchTemplates()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('reviewTemplate.deleteFailed'))
    }
  }
}

const resetTemplateForm = () => {
  templateForm.name = ''
  templateForm.description = ''
  templateForm.project = ''
  templateForm.checklist = ['']
  templateForm.default_reviewers = []
  editingTemplateId.value = null
}

const addChecklistItem = () => {
  templateForm.checklist.push('')
}

const removeChecklistItem = (index) => {
  if (templateForm.checklist.length > 1) {
    templateForm.checklist.splice(index, 1)
  }
}

const onProjectChange = (projectId) => {
  if (projectId) {
    // 清空默认评审人选择
    templateForm.default_reviewers = []
  }
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}


onMounted(() => {
  fetchTemplates()
  fetchProjects()
  fetchProjectUsers() // 页面加载时就获取所有用户
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
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  line-height: 24px;
}

// 页面头部
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  
  .el-button {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;
    
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

// 筛选栏样式已在全局样式文件 filter-components.scss 中定义
// 这里只保留特定于本页面的额外样式
.filter-bar {
  /* 本页面特定的筛选栏样式可以在这里添加 */
}

// 模板网格
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 24px;
  flex-grow: 1;
}

// 模板卡片
.template-card {
  background: linear-gradient(135deg, #ffffff 0%, #faf8ff 100%);
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  transition: all 0.3s ease;
  overflow: hidden;
  
  &:hover {
    box-shadow: 0 8px 24px rgba(147, 112, 219, 0.15);
    transform: translateY(-4px);
    border-color: rgba(147, 112, 219, 0.2);
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);
    background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
    
    .template-name {
      font-weight: 700;
      font-size: 18px;
      color: #5a32a3;
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    
    .card-actions {
      display: flex;
      gap: 12px;
      
      .el-button {
        font-size: 14px;
        padding: 6px 12px;
        transition: all 0.3s ease;
        border-radius: 6px;
        
        &:hover {
          transform: translateY(-1px);
        }
        
        &.el-button--text {
          color: #7b42f6;
          
          &:hover {
            color: #5a32a3;
            background: rgba(123, 66, 246, 0.1);
          }
        }
      }
    }
  }
  
  .template-content {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    
    .template-info {
      background: linear-gradient(135deg, #f8f7ff 0%, #f5f3ff 100%);
      padding: 16px;
      border-radius: 8px;
      border: 1px solid rgba(147, 112, 219, 0.08);
      
      .info-item {
        display: flex;
        margin-bottom: 10px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .info-label {
          min-width: 80px;
          color: #7b42f6;
          font-size: 14px;
          font-weight: 500;
        }
        
        .info-value {
          color: #5a32a3;
          font-size: 14px;
          font-weight: 500;
        }
      }
    }
    
    .template-description {
      color: #6d5d8f;
      line-height: 1.7;
      font-size: 14px;
      padding: 12px 16px;
      background: linear-gradient(135deg, #faf8ff 0%, #f8f7ff 100%);
      border-radius: 8px;
      border-left: 3px solid #7b42f6;
    }
    
    .template-checklist {
      .checklist-title {
        font-weight: 600;
        margin-bottom: 12px;
        color: #5a32a3;
        font-size: 15px;
        display: flex;
        align-items: center;
        
        &::before {
          content: '';
          display: inline-block;
          width: 4px;
          height: 16px;
          background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
          border-radius: 2px;
          margin-right: 8px;
        }
      }
      
      ul {
        margin: 0;
        padding-left: 24px;
        
        li {
          margin-bottom: 6px;
          color: #6d5d8f;
          font-size: 14px;
          line-height: 1.5;
          
          &.more-items {
            color: #9370db;
            font-style: italic;
            font-weight: 500;
          }
        }
      }
      
      .empty-checklist {
        color: #a080d0;
        font-size: 14px;
        font-style: italic;
        padding: 12px 16px;
        background: linear-gradient(135deg, #faf8ff 0%, #f8f7ff 100%);
        border-radius: 8px;
        text-align: center;
      }
    }
    
    .template-reviewers {
      .reviewers-title {
        font-weight: 600;
        margin-bottom: 12px;
        color: #5a32a3;
        font-size: 15px;
        display: flex;
        align-items: center;
        
        &::before {
          content: '';
          display: inline-block;
          width: 4px;
          height: 16px;
          background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
          border-radius: 2px;
          margin-right: 8px;
        }
      }
      
      .reviewers-list {
        .reviewer-tag {
          margin-right: 10px;
          margin-bottom: 6px;
          background: linear-gradient(135deg, rgba(123, 66, 246, 0.1) 0%, rgba(90, 50, 163, 0.1) 100%);
          color: #7b42f6;
          border: 1px solid rgba(123, 66, 246, 0.2);
          padding: 6px 12px;
          border-radius: 20px;
          font-weight: 500;
          
          &:hover {
            background: linear-gradient(135deg, rgba(123, 66, 246, 0.2) 0%, rgba(90, 50, 163, 0.2) 100%);
            transform: translateY(-1px);
          }
        }
        
        .empty-reviewers {
          color: #a080d0;
          font-size: 14px;
          font-style: italic;
          padding: 12px 16px;
          background: linear-gradient(135deg, #faf8ff 0%, #f8f7ff 100%);
          border-radius: 8px;
          text-align: center;
        }
      }
    }
  }
}

// 空状态
.empty-templates {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.1);
  
  :deep(.el-empty__description) {
    color: #7b42f6;
    font-size: 16px;
    font-weight: 500;
  }
  
  :deep(.el-empty__image) {
    opacity: 0.7;
  }
}

// 检查清单编辑器
.checklist-editor {
  .checklist-item {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
    align-items: center;
  }
}

// 对话框样式
:deep(.el-dialog) {
  .el-form {
    // el-row 间距
    .el-row {
      margin-bottom: 24px;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .el-form-item {
      margin-bottom: 24px;

      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}
</style>