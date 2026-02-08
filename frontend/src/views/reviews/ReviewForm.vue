<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isEdit ? $t('reviewForm.editTitle') : $t('reviewForm.createTitle') }}</h1>
      <div>
        <el-button @click="$router.back()">{{ $t('reviewForm.back') }}</el-button>
        <el-button type="primary" @click="saveReview" :loading="saving">{{ $t('reviewForm.save') }}</el-button>
      </div>
    </div>

    <div class="form-container">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item :label="$t('reviewForm.reviewTitle')" prop="title">
              <el-input v-model="form.title" :placeholder="$t('reviewForm.reviewTitlePlaceholder')" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('reviewForm.associatedProject')" prop="projects">
              <el-select
                v-model="form.projects"
                multiple
                :placeholder="$t('reviewForm.selectProject')"
                @change="onProjectChange"
              >
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

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item :label="$t('reviewForm.priority')" prop="priority">
              <el-select v-model="form.priority" :placeholder="$t('reviewForm.selectPriority')">
                <el-option :label="$t('reviewForm.priorityLow')" value="low" />
                <el-option :label="$t('reviewForm.priorityMedium')" value="medium" />
                <el-option :label="$t('reviewForm.priorityHigh')" value="high" />
                <el-option :label="$t('reviewForm.priorityUrgent')" value="urgent" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('reviewForm.deadline')">
              <el-date-picker
                v-model="form.deadline"
                type="datetime"
                :placeholder="$t('reviewForm.deadlinePlaceholder')"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm:ss"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="$t('reviewForm.description')">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            :placeholder="$t('reviewForm.descriptionPlaceholder')"
          />
        </el-form-item>

        <el-form-item :label="$t('reviewForm.selectTestcases')" prop="testcases">
          <div class="testcase-selector">
            <div class="search-bar">
              <el-input
                v-model="testcaseSearch"
                :placeholder="$t('reviewForm.searchTestcases')"
                @input="searchTestcases"
                clearable
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-button type="primary" @click="showTestcaseSelector">{{ $t('reviewForm.selectTestcasesBtn') }}</el-button>
            </div>

            <div class="selected-testcases">
              <el-tag
                v-for="testcase in selectedTestcases"
                :key="testcase.id"
                closable
                @close="removeTestcase(testcase.id)"
                class="testcase-tag"
              >
                {{ testcase.title }}
              </el-tag>
              <div v-if="selectedTestcases.length === 0" class="empty-tip">
                {{ $t('reviewForm.emptyTestcasesTip') }}
              </div>
            </div>
          </div>
        </el-form-item>

        <el-form-item :label="$t('reviewForm.reviewers')" prop="reviewers">
          <el-select
            v-model="form.reviewers"
            multiple
            :placeholder="$t('reviewForm.selectReviewers')"
            @change="onReviewersChange"
          >
            <el-option
              v-for="user in projectUsers"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('reviewForm.reviewTemplate')">
          <el-select v-model="form.template" :placeholder="$t('reviewForm.selectTemplate')" @change="applyTemplate">
            <el-option
              v-for="template in templates"
              :key="template.id"
              :label="template.name"
              :value="template.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <!-- 用例选择对话框 -->
    <el-dialog v-model="testcaseSelectorVisible" :title="$t('reviewForm.testcaseSelectorTitle')" :close-on-click-modal="false" width="800px">
      <div class="testcase-selector-content">
        <el-input
          v-model="testcaseSearchInDialog"
          :placeholder="$t('reviewForm.searchTestcases')"
          @input="searchTestcasesInDialog"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-table
          :data="filteredTestcases"
          @selection-change="handleTestcaseSelection"
          max-height="400"
          class="testcase-table"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="title" :label="$t('reviewForm.testcaseTitle')" min-width="200" show-overflow-tooltip />
          <el-table-column prop="test_type" :label="$t('reviewForm.testType')" width="120" />
          <el-table-column prop="priority" :label="$t('reviewDetail.priority')" width="100">
            <template #default="{ row }">
              <el-tag :class="`priority-tag ${row.priority}`">{{ getPriorityText(row.priority) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="author.username" :label="$t('reviewForm.author')" width="120" />
        </el-table>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="testcaseSelectorVisible = false">{{ $t('reviewForm.cancel') }}</el-button>
          <el-button type="primary" @click="confirmTestcaseSelection">{{ $t('reviewForm.confirm') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const isEdit = computed(() => !!route.params.id)

const formRef = ref()
const saving = ref(false)
const testcaseSelectorVisible = ref(false)
const testcaseSearch = ref('')
const testcaseSearchInDialog = ref('')

const projects = ref([])
const projectUsers = ref([])
const templates = ref([])
const testcases = ref([])
const selectedTestcases = ref([])
const tempSelectedTestcases = ref([])

const form = reactive({
  title: '',
  description: '',
  projects: [],
  priority: 'medium',
  deadline: '',
  testcases: [],
  reviewers: [],
  template: ''
})

const rules = computed(() => ({
  title: [{ required: true, message: t('reviewForm.titleRequired'), trigger: 'blur' }],
  projects: [{ required: true, message: t('reviewForm.projectRequired'), trigger: 'change' }],
  testcases: [{ required: true, message: t('reviewForm.testcasesRequired'), trigger: 'change' }],
  reviewers: [{ required: true, message: t('reviewForm.reviewersRequired'), trigger: 'change' }]
}))

const filteredTestcases = computed(() => {
  if (!testcaseSearchInDialog.value) return testcases.value
  return testcases.value.filter(tc =>
    tc.title.toLowerCase().includes(testcaseSearchInDialog.value.toLowerCase())
  )
})

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(t('reviewForm.fetchProjectsFailed'))
  }
}

const fetchProjectUsers = async () => {
  try {
    const response = await api.get('/auth/users/')
    projectUsers.value = response.data.results || response.data || []
    console.log('All users:', projectUsers.value)
  } catch (error) {
    console.error('Fetch users failed:', error)
    ElMessage.error(t('reviewForm.fetchUsersFailed'))
    projectUsers.value = []
  }
}

const fetchTestcases = async (projectIds) => {
  try {
    // 如果没有选择项目，清空用例列表
    if (!projectIds || projectIds.length === 0) {
      testcases.value = []
      return
    }

    // 获取所有选中项目的用例
    const promises = projectIds.map(projectId =>
      api.get('/testcases/', { params: { project: projectId } })
    )

    const responses = await Promise.all(promises)
    const allTestcases = []

    responses.forEach(response => {
      const cases = response.data.results || response.data || []
      allTestcases.push(...cases)
    })

    // 去重（基于用例ID）
    const uniqueTestcases = allTestcases.filter((testcase, index, self) =>
      index === self.findIndex(t => t.id === testcase.id)
    )

    testcases.value = uniqueTestcases
  } catch (error) {
    console.error('Fetch testcases failed:', error)
  }
}

const fetchTemplates = async (projectIds) => {
  try {
    // 如果没有选择项目，清空模板列表
    if (!projectIds || projectIds.length === 0) {
      templates.value = []
      return
    }

    // 获取所有选中项目的模板
    const promises = projectIds.map(projectId =>
      api.get('/reviews/review-templates/', { params: { project: projectId } })
    )

    const responses = await Promise.all(promises)
    const allTemplates = []

    responses.forEach(response => {
      const temps = response.data.results || response.data || []
      allTemplates.push(...temps)
    })

    // 去重（基于模板ID）
    const uniqueTemplates = allTemplates.filter((template, index, self) =>
      index === self.findIndex(t => t.id === template.id)
    )

    templates.value = uniqueTemplates
  } catch (error) {
    console.error('Fetch templates failed:', error)
  }
}

const onProjectChange = (projectIds) => {
  if (projectIds && projectIds.length > 0) {
    fetchTestcases(projectIds)
    fetchTemplates(projectIds)
  } else {
    // 如果没有选择项目，清空相关数据
    testcases.value = []
    templates.value = []
  }

  // 清空相关选择
  form.reviewers = []
  form.testcases = []
  selectedTestcases.value = []
}

const showTestcaseSelector = () => {
  if (!form.projects || form.projects.length === 0) {
    ElMessage.warning(t('reviewForm.selectProjectFirst'))
    return
  }
  testcaseSelectorVisible.value = true
}

const handleTestcaseSelection = (selection) => {
  tempSelectedTestcases.value = selection
}

const confirmTestcaseSelection = () => {
  selectedTestcases.value = [...tempSelectedTestcases.value]
  form.testcases = selectedTestcases.value.map(tc => tc.id)
  testcaseSelectorVisible.value = false
}

const removeTestcase = (id) => {
  selectedTestcases.value = selectedTestcases.value.filter(tc => tc.id !== id)
  form.testcases = selectedTestcases.value.map(tc => tc.id)
}

const onReviewersChange = () => {
  // 可以在这里添加评审人员变更的逻辑
}

const applyTemplate = async (templateId) => {
  if (!templateId) return

  try {
    const template = templates.value.find(t => t.id === templateId)
    if (template) {
      // 应用模板的默认评审人员
      form.reviewers = template.default_reviewers.map(u => u.id)
    }
  } catch (error) {
    console.error('Apply template failed:', error)
  }
}

const saveReview = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    saving.value = true

    const data = {
      ...form,
      testcases: form.testcases,
      reviewers: form.reviewers,
      // 确保包含 template 字段
      template: form.template || null
    }

    if (isEdit.value) {
      await api.put(`/reviews/reviews/${route.params.id}/`, data)
      ElMessage.success(t('reviewForm.updateSuccess'))
    } else {
      await api.post('/reviews/reviews/', data)
      ElMessage.success(t('reviewForm.createSuccess'))
    }

    router.push('/ai-generation/reviews')

  } catch (error) {
    if (error.response?.data) {
      const errors = Object.values(error.response.data).flat()
      ElMessage.error(errors[0] || t('reviewForm.saveFailed'))
    } else {
      ElMessage.error(t('reviewForm.saveFailed'))
    }
  } finally {
    saving.value = false
  }
}

const getPriorityText = (priority) => {
  const textMap = {
    low: t('reviewForm.priorityLow'),
    medium: t('reviewForm.priorityMedium'),
    high: t('reviewForm.priorityHigh'),
    critical: t('reviewForm.priorityUrgent')
  }
  return textMap[priority] || priority
}

const findMatchingTemplate = (review, templateList) => {
  if (!templateList || templateList.length === 0) return null

  // 获取评审的项目ID列表和评审人ID列表
  const reviewProjectIds = review.projects.map(p => p.id).sort()
  const reviewReviewerIds = review.assignments.map(a => a.reviewer.id).sort()

  let bestMatch = null
  let bestScore = 0

  for (const template of templateList) {
    let score = 0

    // 检查项目匹配度
    const templateProjectIds = (template.project || []).map(p => p.id).sort()
    const projectIntersection = reviewProjectIds.filter(id => templateProjectIds.includes(id))
    if (projectIntersection.length > 0) {
      score += projectIntersection.length * 2 // 项目匹配权重更高
    }

    // 检查默认评审人匹配度
    const templateReviewerIds = (template.default_reviewers || []).map(r => r.id).sort()
    const reviewerIntersection = reviewReviewerIds.filter(id => templateReviewerIds.includes(id))
    if (reviewerIntersection.length > 0) {
      score += reviewerIntersection.length // 评审人匹配
    }

    // 如果有更高的匹配分数，更新最佳匹配
    if (score > bestScore) {
      bestScore = score
      bestMatch = template
    }
  }

  // 只有当匹配分数大于0时才返回匹配的模板
  return bestScore > 0 ? bestMatch : null
}

const fetchReviewData = async (reviewId) => {
  try {
    const response = await api.get(`/reviews/reviews/${reviewId}/`)
    const review = response.data

    // 填充表单数据
    form.title = review.title
    form.description = review.description
    form.projects = review.projects.map(p => p.id)
    form.priority = review.priority
    form.deadline = review.deadline
    form.reviewers = review.assignments.map(a => a.reviewer.id)

    // 处理测试用例
    selectedTestcases.value = review.testcases
    form.testcases = review.testcases.map(tc => tc.id)

    // 加载项目相关数据
    if (form.projects.length > 0) {
      await fetchTestcases(form.projects)
      await fetchTemplates(form.projects)

      // 在模板加载完成后，尝试找到匹配的模板
      const matchingTemplate = findMatchingTemplate(review, templates.value)
      if (matchingTemplate) {
        form.template = matchingTemplate.id
      }
    }

  } catch (error) {
    console.error('Fetch review data failed:', error)
    ElMessage.error(t('reviewForm.fetchReviewFailed'))
    router.push('/ai-generation/reviews')
  }
}

const searchTestcases = () => {
  // 搜索用例的逻辑
}

const searchTestcasesInDialog = () => {
  // 在对话框中搜索用例的逻辑
}

onMounted(() => {
  fetchProjects()
  fetchProjectUsers() // 页面加载时就获取所有用户

  if (isEdit.value) {
    // 如果是编辑模式，加载现有数据
    fetchReviewData(route.params.id)
  } else {
    // 如果是创建模式，检查是否有模板参数
    const templateId = route.query.template
    if (templateId) {
      form.template = templateId
    }
  }
})
</script>

<style lang="scss" scoped>
// 页面容器
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
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

  // 按钮样式
  .el-button {
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 500;
    font-size: 14px;
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-1px);
    }

    // 返回按钮
    &:not(.el-button--primary) {
      border: 1px solid rgba(147, 112, 219, 0.3);
      color: #5a32a3;
      background: #ffffff;

      &:hover {
        border-color: #7b42f6;
        color: #7b42f6;
        background: rgba(123, 66, 246, 0.05);
      }
    }

    // 保存按钮
    &.el-button--primary {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      border: none;
      color: white;
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(123, 66, 246, 0.4);
      }
    }
  }
}

// 表单容器
.form-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 32px;

  // 表单样式
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

      .el-form-item__label {
        color: #5a32a3;
        font-weight: 500;
        font-size: 14px;
      }

      // 输入框样式
      .el-input {
        .el-input__wrapper {
          box-shadow: 0 2px 8px rgba(147, 112, 219, 0.08);
          border-radius: 8px;
          border: 1px solid rgba(147, 112, 219, 0.15);
          background: #ffffff;
          transition: all 0.3s ease;

          &:hover,
          &.is-focus {
            border-color: #7b42f6;
            box-shadow: 0 2px 8px rgba(147, 112, 219, 0.15), 0 0 0 3px rgba(123, 66, 246, 0.1);
          }

          .el-input__inner {
            color: #333;
            font-size: 14px;

            &::placeholder {
              color: #999;
            }
          }
        }
      }

      // 文本域样式
      .el-textarea {
        .el-textarea__inner {
          box-shadow: 0 2px 8px rgba(147, 112, 219, 0.08);
          border-radius: 8px;
          border: 1px solid rgba(147, 112, 219, 0.15);
          background: #ffffff;
          transition: all 0.3s ease;
          padding: 12px 16px;
          line-height: 1.6;

          &:hover,
          &:focus {
            border-color: #7b42f6;
            box-shadow: 0 2px 8px rgba(147, 112, 219, 0.15), 0 0 0 3px rgba(123, 66, 246, 0.1);
          }

          &::placeholder {
            color: #999;
          }
        }
      }

      // 选择器样式
      .el-select {
        width: 100%;

        .el-input__wrapper {
          box-shadow: 0 2px 8px rgba(147, 112, 219, 0.08);
          border-radius: 8px;
          border: 1px solid rgba(147, 112, 219, 0.15);
          background: #ffffff;
          transition: all 0.3s ease;

          &:hover,
          &.is-focus {
            border-color: #7b42f6;
            box-shadow: 0 2px 8px rgba(147, 112, 219, 0.15), 0 0 0 3px rgba(123, 66, 246, 0.1);
          }

          .el-input__inner {
            color: #333;
            font-size: 14px;

            &::placeholder {
              color: #999;
            }
          }
        }
      }

      // 日期选择器样式
      .el-date-editor {
        width: 100%;

        .el-input__wrapper {
          box-shadow: 0 2px 8px rgba(147, 112, 219, 0.08);
          border-radius: 8px;
          border: 1px solid rgba(147, 112, 219, 0.15);
          background: #ffffff;
          transition: all 0.3s ease;

          &:hover,
          &.is-focus {
            border-color: #7b42f6;
            box-shadow: 0 2px 8px rgba(147, 112, 219, 0.15), 0 0 0 3px rgba(123, 66, 246, 0.1);
          }
        }
      }
    }
  }
}

// 用例选择器样式
.testcase-selector {
  .search-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;

    .el-button {
      border-radius: 8px;
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      border: none;
      color: white;
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(123, 66, 246, 0.4);
      }
    }
  }

  .selected-testcases {
    border: 1px solid rgba(147, 112, 219, 0.2);
    border-radius: 8px;
    min-height: 80px;
    padding: 12px;
    background: #fafaff;

    .testcase-tag {
      margin: 4px;
      background: rgba(123, 66, 246, 0.1);
      border-color: rgba(123, 66, 246, 0.2);
      color: #5a32a3;
      border-radius: 4px;

      &:hover {
        background: rgba(123, 66, 246, 0.15);
      }
    }

    .empty-tip {
      color: #999;
      text-align: center;
      padding: 24px;
      font-size: 14px;
    }
  }
}

// 优先级标签样式
.priority-tag {
  border-radius: 4px;
  font-weight: 500;

  &.low {
    background: rgba(82, 196, 26, 0.1);
    color: #52c41a;
    border-color: rgba(82, 196, 26, 0.2);
  }
  &.medium {
    background: rgba(250, 173, 20, 0.1);
    color: #faad14;
    border-color: rgba(250, 173, 20, 0.2);
  }
  &.high {
    background: rgba(255, 77, 79, 0.1);
    color: #ff4d4f;
    border-color: rgba(255, 77, 79, 0.2);
  }
  &.critical {
    background: rgba(255, 77, 79, 0.15);
    color: #ff4d4f;
    border-color: rgba(255, 77, 79, 0.3);
    font-weight: 600;
  }
}

// 对话框样式
:deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.15);
  border: 1px solid rgba(147, 112, 219, 0.1);

  .el-dialog__header {
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    padding: 20px 24px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);
    margin: 0;

    .el-dialog__title {
      color: #5a32a3;
      font-weight: 600;
      font-size: 16px;
    }
  }

  .el-dialog__body {
    padding: 24px;
    background: #ffffff;
  }

  .el-dialog__footer {
    padding: 16px 24px;
    border-top: 1px solid rgba(147, 112, 219, 0.1);
    background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);

    .dialog-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
  }
}

// 用例选择对话框内容样式
.testcase-selector-content {
  .el-input {
    margin-bottom: 16px;

    .el-input__wrapper {
      box-shadow: 0 2px 8px rgba(147, 112, 219, 0.08);
      border-radius: 8px;
      border: 1px solid rgba(147, 112, 219, 0.15);
      background: #ffffff;
      transition: all 0.3s ease;

      &:hover,
      &.is-focus {
        border-color: #7b42f6;
        box-shadow: 0 2px 8px rgba(147, 112, 219, 0.15), 0 0 0 3px rgba(123, 66, 246, 0.1);
      }
    }
  }

  .testcase-table {
    border-radius: 8px;
    overflow: hidden;

    :deep(.el-table__header-wrapper) {
      th {
        background-color: #f8f7ff !important;
        color: #5a32a3;
        font-weight: 600;
      }
    }

    :deep(.el-table__row) {
      transition: all 0.3s ease;

      &:hover {
        background-color: #f8f7ff !important;
      }
    }
  }
}

// 响应式布局
@media (max-width: 1200px) {
  .page-container {
    padding: 16px;
  }

  .page-header {
    padding: 20px;

    .page-title {
      font-size: 20px;
    }
  }

  .form-container {
    padding: 24px;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 12px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 16px;

    .page-title {
      font-size: 18px;
    }
  }

  .form-container {
    padding: 16px;

    .el-form {
      .el-form-item {
        margin-bottom: 20px;
      }
    }
  }
}
</style>
