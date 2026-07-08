<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">{{ form.title || $t('testcase.edit') }}</h1>
      <div class="header-actions">
        <el-button @click="$router.back()" class="action-btn cancel-btn">
          <el-icon><ArrowLeft /></el-icon>
          <span>{{ $t('common.cancel') }}</span>
        </el-button>
        <el-button type="primary" class="action-btn edit-btn" @click="handleSubmit" :loading="submitting">
          <el-icon><Check /></el-icon>
          <span>{{ $t('testcase.saveChanges') }}</span>
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="card-container loading-card">
      <el-skeleton :rows="15" animated />
    </div>

    <!-- 表单内容 -->
    <div v-else class="detail-container">
      <el-form ref="formRef" :model="form" :rules="rules" class="testcase-form">
        <!-- 合并的卡片：基本信息 + 测试执行 -->
        <div class="card-container unified-card">
          <!-- 基本信息区域 -->
          <div class="section-header">
            <h3 class="card-title">{{ $t('testcase.basicInfo') }}</h3>
            <div class="card-tags">
              <el-tag :type="priorityType(form.priority)" class="priority-tag">
                {{ priorityLabel(form.priority) }}
              </el-tag>
              <el-tag type="info" class="type-tag">
                {{ testTypeLabel(form.test_type) }}
              </el-tag>
            </div>
          </div>

          <div class="info-section">
            <el-row :gutter="24" class="info-row">
              <el-col :span="12">
                <div class="info-item">
                  <span class="info-label">用例标题</span>
                  <el-input
                    v-model="form.title"
                    placeholder="请输入用例标题"
                    maxlength="500"
                    class="info-input"
                  />
                </div>
              </el-col>
              <el-col :span="6">
                <div class="info-item">
                  <span class="info-label">创建者</span>
                  <el-select
                    v-model="form.author_name"
                    placeholder="请选择作者"
                    filterable
                    clearable
                    class="info-select"
                    :loading="loadingUsers"
                  >
                    <el-option
                      v-for="user in users"
                      :key="user.id"
                      :label="user.username"
                      :value="user.username"
                    />
                  </el-select>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="info-item">
                  <span class="info-label">{{ $t('testcase.relatedProject') }}</span>
                  <el-input
                    v-model="form.category_path"
                    :placeholder="$t('testcase.categoryPathPlaceholder') || '端名称/菜单/子菜单'"
                    maxlength="500"
                    class="info-input"
                  />
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="24" class="info-row">
              <el-col :span="6">
                <div class="info-item">
                  <span class="info-label">{{ $t('testcase.moduleLabel') }}</span>
                  <el-input
                    v-model="form.module"
                    :placeholder="$t('testcase.modulePlaceholder')"
                    maxlength="200"
                    class="info-input"
                  />
                </div>
              </el-col>
              <el-col :span="6">
                <div class="info-item">
                  <span class="info-label">{{ $t('testcase.priority') }}</span>
                  <el-select v-model="form.priority" :placeholder="$t('testcase.selectPriority')" class="info-select">
                    <el-option label="P0" value="critical" />
                    <el-option label="P1" value="high" />
                    <el-option label="P2" value="medium" />
                    <el-option label="P3" value="low" />
                  </el-select>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="info-item">
                  <span class="info-label">{{ $t('testcase.testType') }}</span>
                  <el-select v-model="form.test_type" :placeholder="$t('testcase.selectTestType')" class="info-select">
                    <el-option :label="$t('testcase.text')" value="text" />
                    <el-option :label="$t('testcase.step')" value="step" />
                  </el-select>
                </div>
              </el-col>
            </el-row>
          </div>

          <!-- 分隔线 -->
          <div class="section-divider"></div>

          <!-- 测试执行区域 -->
          <div class="section-header">
            <h3 class="card-title card-title-with-icon">
              <el-icon><List /></el-icon>
              <span>测试执行</span>
            </h3>
          </div>

          <!-- 步骤与结果编辑表格 -->
          <div class="steps-table-wrapper">
            <table class="steps-edit-table">
              <thead>
                <tr>
                  <th class="col-precondition">前置条件</th>
                  <th class="col-step">测试步骤</th>
                  <th class="col-expected">预期结果</th>
                  <th class="col-action">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in form.stepItems" :key="item.id">
                  <!-- 前置条件列：只在第一行显示，合并行 -->
                  <td v-if="index === 0" class="cell-precondition" :rowspan="form.stepItems.length">
                    <el-input
                      v-model="form.preconditions"
                      type="textarea"
                      :rows="Math.min(form.stepItems.length * 3, 12)"
                      :placeholder="$t('testcase.preconditionsPlaceholder')"
                      class="table-textarea"
                    />
                  </td>
                  <td class="cell-step">
                    <div class="cell-inner">
                      <span class="cell-index">{{ index + 1 }}</span>
                      <el-input
                        v-model="item.step"
                        type="textarea"
                        :rows="3"
                        placeholder="请输入步骤描述"
                        class="table-textarea"
                      />
                    </div>
                  </td>
                  <td class="cell-expected">
                    <el-input
                      v-model="item.expected"
                      type="textarea"
                      :rows="3"
                      placeholder="请输入预期结果"
                      class="table-textarea"
                    />
                  </td>
                  <td class="cell-action">
                    <div class="action-btns">
                      <el-button type="primary" link size="small" @click="addStep(index)" title="添加步骤">
                        <el-icon><Plus /></el-icon>
                      </el-button>
                      <el-button type="primary" link size="small" @click="moveStepUp(index)" :disabled="index === 0" title="上移">
                        <el-icon><ArrowUp /></el-icon>
                      </el-button>
                      <el-button type="primary" link size="small" @click="moveStepDown(index)" :disabled="index === form.stepItems.length - 1" title="下移">
                        <el-icon><ArrowDown /></el-icon>
                      </el-button>
                      <el-button type="danger" link size="small" @click="removeStep(index)" title="删除">
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>


        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check, List, Plus, Delete, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import api from '@/utils/api'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const formRef = ref()
const loading = ref(true)
const submitting = ref(false)
const users = ref([])
const loadingUsers = ref(false)


const form = reactive({
  title: '',
  author_name: '',
  category_path: '',
  module: '',
  priority: 'medium',
  test_type: 'text',
  preconditions: '',
  stepItems: []
})

// 步骤项结构
const createStepItem = (step = '', expected = '') => ({
  id: Date.now() + Math.random(),
  step,
  expected
})

const rules = {
  title: [{ required: true, message: t('testcase.titleRequired'), trigger: 'blur' }],
  category_path: [{ required: true, message: t('testcase.categoryPathRequired') || '请输入归属目录', trigger: 'blur' }],
  priority: [{ required: true, message: t('testcase.priorityRequired'), trigger: 'change' }],
  test_type: [{ required: true, message: t('testcase.testTypeRequired'), trigger: 'change' }]
}

// 解析步骤和预期结果为数组
const parseSteps = (steps) => {
  if (!steps) return []
  return steps.split('\n').map(line => line.trim()).filter(line => line.length > 0)
}

// 添加步骤
const addStep = (index) => {
  const newItem = createStepItem()
  if (index !== undefined) {
    form.stepItems.splice(index + 1, 0, newItem)
  } else {
    form.stepItems.push(newItem)
  }
}

// 删除步骤
const removeStep = async (index) => {
  if (form.stepItems.length <= 1) {
    ElMessage.warning('至少需要保留一个步骤')
    return
  }
  try {
    await ElMessageBox.confirm('确定要删除这个步骤吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    form.stepItems.splice(index, 1)
    ElMessage.success('删除成功')
  } catch {
    // 取消删除
  }
}

// 上移步骤
const moveStepUp = (index) => {
  if (index === 0) return
  const temp = form.stepItems[index]
  form.stepItems[index] = form.stepItems[index - 1]
  form.stepItems[index - 1] = temp
}

// 下移步骤
const moveStepDown = (index) => {
  if (index === form.stepItems.length - 1) return
  const temp = form.stepItems[index]
  form.stepItems[index] = form.stepItems[index + 1]
  form.stepItems[index + 1] = temp
}

// 优先级类型
const priorityType = (priority) => {
  const types = {
    'low': 'success',
    'medium': 'warning',
    'high': 'danger',
    'critical': 'danger'
  }
  return types[priority] || 'info'
}

// 优先级标签
const priorityLabel = (priority) => {
  const labels = {
    'critical': 'P0',
    'high': 'P1',
    'medium': 'P2',
    'low': 'P3'
  }
  return labels[priority] || priority
}

// 测试类型标签
const testTypeLabel = (type) => {
  const labels = {
    'text': t('testcase.text'),
    'step': t('testcase.step')
  }
  return labels[type] || type
}

// 转换 <br> 为换行符
const convertBrToNewline = (content) => {
  if (!content) return ''
  return content.replace(/<br\s*\/?>/gi, '\n')
}

// 转换换行符为 <br>
const convertNewlineToBr = (content) => {
  if (!content) return ''
  return content.replace(/\n/g, '<br>')
}

const fetchTestCase = async () => {
  try {
    const response = await api.get(`/testcases/${route.params.id}/`)
    const testcase = response.data

    // Fill form data
    form.title = testcase.title
    form.author_name = testcase.author_name || testcase.author?.username || ''
    form.category_path = testcase.category_path || ''
    form.module = testcase.module || ''
    form.priority = testcase.priority
    form.test_type = testcase.test_type
    form.preconditions = convertBrToNewline(testcase.preconditions || '')

    // 解析步骤和预期结果为数组
    const steps = parseSteps(convertBrToNewline(testcase.steps || ''))
    const expectedResults = parseSteps(convertBrToNewline(testcase.expected_result || ''))

    // 创建步骤项数组
    form.stepItems = []
    const maxLength = Math.max(steps.length, expectedResults.length, 1)
    for (let i = 0; i < maxLength; i++) {
      form.stepItems.push(createStepItem(steps[i] || '', expectedResults[i] || ''))
    }

    loading.value = false
  } catch (error) {
    ElMessage.error(t('testcase.fetchDetailFailed'))
    router.back()
  }
}

const fetchUsers = async () => {
  loadingUsers.value = true
  try {
    const res = await api.get('/users/users/')
    users.value = (res.data.results || res.data || []).filter(item => item && item.username)
  } catch (error) {
    console.error('获取用户列表失败:', error)
    users.value = []
  } finally {
    loadingUsers.value = false
  }
}


const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        // 将步骤数组转换为字符串
        const steps = form.stepItems.map(item => item.step).filter(s => s).join('\n')
        const expectedResults = form.stepItems.map(item => item.expected).filter(s => s).join('\n')

        // 保存数据（保持换行符格式，不转换为<br>）
        const submitData = {
          title: form.title,
          author_name: form.author_name,
          category_path: form.category_path,
          module: form.module,
          priority: form.priority,
          test_type: form.test_type,
          preconditions: form.preconditions || '',
          steps: steps || '',
          expected_result: expectedResults || ''
        }

        await api.put(`/testcases/${route.params.id}/`, submitData)
        ElMessage.success(t('testcase.updateSuccess'))
        router.push(`/ai-generation/testcases/${route.params.id}`)
      } catch (error) {
        ElMessage.error(t('testcase.updateFailed'))
        console.error('Submit error:', error)
      } finally {
        submitting.value = false
      }
    }
  })
}

onMounted(async () => {
  await Promise.all([
    fetchTestCase(),
    fetchUsers()
  ])
})

</script>

<style lang="scss" scoped>
.page-container {
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

  .header-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
}

.detail-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 28px;

  &.loading-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 400px;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);

  .card-title {
    font-size: 18px;
    font-weight: 600;
    color: #5a32a3;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;

    &::before {
      content: '';
      width: 4px;
      height: 20px;
      background: linear-gradient(180deg, #7b42f6 0%, #5a32a3 100%);
      border-radius: 2px;
    }

    &.card-title-with-icon {
      &::before {
        display: none;
      }
    }
  }

  .card-tags {
    display: flex;
    gap: 8px;

    .priority-tag,
    .type-tag {
      font-weight: 500;
      padding: 4px 12px;
      border-radius: 6px;
    }
  }
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-row {
  margin-bottom: 0;
}

.info-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  overflow: hidden;

  .info-label {
    font-size: 13px;
    font-weight: 500;
    color: #7b42f6;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .info-select,
  .info-input {
    flex: 1;
    min-width: 0;
  }

  .info-select-multiple {
    flex: 1;
  }
}

// 合并卡片样式
.unified-card {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .card-title {
      font-size: 18px;
      font-weight: 600;
      color: #5a32a3;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;

      &::before {
        content: '';
        width: 4px;
        height: 20px;
        background: linear-gradient(180deg, #7b42f6 0%, #5a32a3 100%);
        border-radius: 2px;
      }

      &.card-title-with-icon {
        &::before {
          display: none;
        }
      }
    }

    .card-tags {
      display: flex;
      gap: 8px;

      .priority-tag,
      .type-tag {
        font-weight: 500;
        padding: 4px 12px;
        border-radius: 6px;
      }
    }
  }

  .section-divider {
    height: 1px;
    background: rgba(147, 112, 219, 0.1);
    margin: 24px 0;
  }

  // 步骤编辑表格样式
  .steps-table-wrapper {
    width: 100%;
    overflow-x: auto;
    border-radius: 8px;
    border: 1px solid #e8e8e8;
  }

  .steps-edit-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    background: #ffffff;

    thead tr {
      background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);

      th {
        padding: 12px 16px;
        font-size: 14px;
        font-weight: 600;
        color: #5a32a3;
        text-align: left;
        border-bottom: 1px solid rgba(147, 112, 219, 0.15);
        white-space: nowrap;
      }

      .col-precondition { width: 22%; }
      .col-step { width: 32%; }
      .col-expected { width: 32%; }
      .col-action { width: 14%; }
    }

    tbody tr {
      transition: background 0.2s ease;

      &:hover {
        background: #faf9ff;
      }

      &:not(:last-child) td {
        border-bottom: 1px solid #f0f0f0;
      }
    }

    td {
      padding: 12px 12px;
      font-size: 14px;
      line-height: 1.7;
      vertical-align: top;
    }

    .cell-precondition {
      background: #fafbff;
      vertical-align: top;
    }

    .cell-step .cell-inner {
      display: flex;
      gap: 8px;
      align-items: flex-start;

      .cell-index {
        color: #7b42f6;
        font-weight: 700;
        font-size: 14px;
        flex-shrink: 0;
        padding-top: 8px;
        min-width: 20px;
      }
    }

    .cell-action {
      vertical-align: middle;
      text-align: center;
    }

    .action-btns {
      display: flex;
      flex-direction: row;
      flex-wrap: wrap;
      gap: 2px;
      justify-content: center;
      align-items: center;
    }

    .table-textarea {
      :deep(.el-textarea__inner) {
        border-radius: 6px;
        border: 1px solid rgba(147, 112, 219, 0.2);
        background: #fafaff;
        font-size: 13px;
        resize: vertical;
        min-height: 36px;
        transition: all 0.3s ease;

        &:hover,
        &:focus {
          border-color: #7b42f6;
          box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.08);
          background: #fff;
        }
      }
    }
  }
}

// 响应式表格
@media (max-width: 768px) {
  .unified-card .steps-edit-table {
    thead th { padding: 8px 6px; font-size: 12px; }
    td { padding: 8px 6px; }

    .cell-action .action-btns {
      flex-direction: column;
    }
  }
}

// 底部操作按钮
.detail-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding-top: 20px;
}

// 按钮样式
.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s ease;

  &.cancel-btn {
    background: #f5f5f5;
    border: 1px solid #e0e0e0;
    color: #666;

    &:hover {
      background: #e8e8e8;
      border-color: #d0d0d0;
      color: #333;
    }
  }

  &.edit-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    border: none;
    color: #fff;

    &:hover {
      background: linear-gradient(135deg, #6a35e0 0%, #4a2880 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
    }
  }
}

// 表单元素样式覆盖
:deep(.el-select) {
  width: 100%;
}

:deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
  border-radius: 8px;
  background: #ffffff;
  transition: all 0.3s ease;

  &:hover,
  &.is-focus {
    box-shadow: 0 0 0 1px #7b42f6;
  }
}

:deep(.el-textarea__inner) {
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
}
</style>
