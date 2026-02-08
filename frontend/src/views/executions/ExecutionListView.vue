<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('execution.testPlan') }}</h1>
      <div class="header-actions">
        <el-button
          v-if="selectedPlans.length > 0"
          type="danger"
          class="batch-delete-btn"
          :icon="Delete"
          @click="batchDeletePlans"
          :disabled="isDeleting">
          {{ $t('execution.batchDelete') }} ({{ selectedPlans.length }})
        </el-button>
        <el-button type="primary" class="create-btn" @click="openCreatePlanDialog">
          <el-icon><Plus /></el-icon>
          {{ $t('execution.newPlan') }}
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item :label="$t('execution.project')">
          <el-select v-model="filters.project" :placeholder="$t('execution.selectProject')" clearable @change="applyFilters">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.status')">
          <el-select v-model="filters.is_active" :placeholder="$t('execution.selectStatus')" clearable @change="applyFilters">
            <el-option :label="$t('execution.filterActive')" :value="true"></el-option>
            <el-option :label="$t('execution.filterClosed')" :value="false"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <div class="table-container">
      <el-table
        :data="testPlans"
        v-loading="loading"
        stripe
        @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" header-align="center" />
      <el-table-column
        type="index"
        :label="$t('execution.serialNumber')"
        width="80"
        align="center"
        header-align="center"
        :index="getSerialNumber" />
      <el-table-column prop="name" :label="$t('execution.planName')" min-width="200" align="center" header-align="center">
        <template #default="scope">
          <el-link type="primary" @click="viewPlan(scope.row.id)">
            {{ scope.row.name }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column prop="projects" :label="$t('execution.projects')" width="200" align="center" header-align="center">
        <template #default="scope">
          <span v-if="scope.row.projects && scope.row.projects.length > 0">
            {{ scope.row.projects.join(', ') }}
          </span>
          <span v-else>{{ $t('execution.noData') }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="version" :label="$t('execution.version')" width="120" align="center" header-align="center"></el-table-column>
      <el-table-column prop="creator.username" :label="$t('execution.creator')" width="120" align="center" header-align="center"></el-table-column>
      <el-table-column :label="$t('execution.status')" width="100" align="center" header-align="center">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">
            {{ scope.row.is_active ? $t('execution.active') : $t('execution.closed') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" :label="$t('execution.createdAt')" width="180" align="center" header-align="center">
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('execution.actions')" width="200" fixed="right" align="center" header-align="center">
          <template #default="scope">
            <el-button link type="primary" @click="viewPlan(scope.row.id)">
              {{ $t('execution.viewExecution') }}
            </el-button>
            <el-button link type="warning" @click="editPlan(scope.row)">
              {{ $t('common.edit') }}
            </el-button>
            <el-button
              link
              :type="scope.row.is_active ? 'danger' : 'success'"
              @click="togglePlanStatus(scope.row)">
              {{ scope.row.is_active ? $t('execution.closePlan') : $t('execution.activatePlan') }}
            </el-button>
          </template>
        </el-table-column>
    </el-table>

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

    <!-- 创建测试计划对话框 -->
    <el-dialog :title="$t('execution.createPlanDialog')" v-model="isCreatePlanDialogOpen" width="600px">
      <el-form :model="newPlanForm" :rules="planRules" ref="planFormRef" label-width="100px">
        <el-form-item :label="$t('execution.planName')" prop="name">
          <el-input v-model="newPlanForm.name" :placeholder="$t('execution.planNamePlaceholder')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.planDescription')">
          <el-input
            v-model="newPlanForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('execution.planDescriptionPlaceholder')">
          </el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedProjects')" prop="projects">
          <el-select
            v-model="newPlanForm.projects"
            multiple
            :placeholder="$t('execution.selectProjects')"
            style="width: 100%"
            @change="handleProjectChange">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedVersion')">
          <el-select v-model="newPlanForm.version" :placeholder="$t('execution.selectVersion')" style="width: 100%">
            <el-option v-for="item in versions" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.testCases')" prop="testcases">
          <el-select
            v-model="newPlanForm.testcases"
            multiple
            :placeholder="loadingTestcases ? $t('execution.loadingTestcases') : (!newPlanForm.projects || newPlanForm.projects.length === 0 ? $t('execution.selectTestcasesDisabled') : $t('execution.selectTestcases'))"
            style="width: 100%"
            :disabled="!newPlanForm.projects || newPlanForm.projects.length === 0"
            :loading="loadingTestcases"
            @visible-change="handleTestcaseSelectOpen">
            <el-option v-for="item in filteredTestcases" :key="item.id" :label="item.title" :value="item.id">
              <span style="float: left">{{ item.title }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ item.project__name }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.assignees')">
          <el-select v-model="newPlanForm.assignees" multiple :placeholder="$t('execution.selectAssignees')" style="width: 100%">
            <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isCreatePlanDialogOpen = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="createPlan" :loading="creating">{{ $t('execution.createPlan') }}</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑测试计划对话框 -->
    <el-dialog :title="$t('execution.editPlanDialog')" v-model="isEditPlanDialogOpen" width="600px">
      <el-form :model="editPlanForm" :rules="planRules" ref="editPlanFormRef" label-width="100px">
        <el-form-item :label="$t('execution.planName')" prop="name">
          <el-input v-model="editPlanForm.name" :placeholder="$t('execution.planNamePlaceholder')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.planDescription')">
          <el-input
            v-model="editPlanForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('execution.planDescriptionPlaceholder')">
          </el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedProjects')" prop="projects">
          <el-select v-model="editPlanForm.projects" multiple :placeholder="$t('execution.selectProjects')" style="width: 100%">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedVersion')">
          <el-select v-model="editPlanForm.version" :placeholder="$t('execution.selectVersion')" style="width: 100%">
            <el-option v-for="item in versions" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.assignees')">
          <el-select v-model="editPlanForm.assignees" multiple :placeholder="$t('execution.selectAssignees')" style="width: 100%">
            <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.planStatus')">
          <el-switch
            v-model="editPlanForm.is_active"
            :active-text="$t('execution.activeText')"
            :inactive-text="$t('execution.inactiveText')">
          </el-switch>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isEditPlanDialogOpen = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="updatePlan" :loading="updating">{{ $t('execution.updatePlan') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'

const { t } = useI18n()

const router = useRouter()
const loading = ref(false)
const creating = ref(false)
const updating = ref(false)
const testPlans = ref([])
const projects = ref([])
const versions = ref([])
const testcases = ref([])
const filteredTestcases = ref([])
const loadingTestcases = ref(false)
const users = ref([])
const selectedPlans = ref([])
const isDeleting = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选
const filters = reactive({
  project: null,
  is_active: null
})

// 表单
const isCreatePlanDialogOpen = ref(false)
const isEditPlanDialogOpen = ref(false)
const planFormRef = ref()
const editPlanFormRef = ref()
const currentEditingPlan = ref(null)
const newPlanForm = reactive({
  name: '',
  description: '',
  projects: [], // 改为数组
  version: null,
  testcases: [],
  assignees: []
})

const editPlanForm = reactive({
  id: null,
  name: '',
  description: '',
  projects: [],
  version: null,
  assignees: [],
  is_active: true
})

const planRules = {
  name: [
    { required: true, message: computed(() => t('execution.planNameRequired')), trigger: 'blur' }
  ],
  projects: [
    { required: true, message: computed(() => t('execution.projectsRequired')), trigger: 'change' }
  ],
  testcases: [
    {
      required: true,
      message: computed(() => t('execution.testcasesRequired')),
      trigger: 'change',
      validator: (rule, value, callback) => {
        if (!newPlanForm.projects || newPlanForm.projects.length === 0) {
          callback(new Error(t('execution.selectProjectBeforeTestcases')))
        } else if (!value || value.length === 0) {
          callback(new Error(t('execution.testcasesRequired')))
        } else {
          callback()
        }
      }
    }
  ]
}

const fetchTestPlans = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      ...filters
    }
    // 过滤掉空值
    Object.keys(params).forEach(key => {
      if (params[key] === null || params[key] === '') {
        delete params[key]
      }
    })

    const response = await api.get('/executions/plans/', { params })
    testPlans.value = response.data.results || response.data || []
    total.value = response.data.count || testPlans.value.length
  } catch (error) {
    ElMessage.error(t('execution.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

const fetchBasicData = async () => {
  try {
    const [projectsRes, versionsRes, usersRes] = await Promise.all([
      api.get('/projects/'), // 只显示用户参与的项目
      api.get('/versions/'),
      api.get('/users/users/') // 修正用户API路径
    ])
    
    projects.value = (projectsRes.data.results || projectsRes.data || []).filter(item => item !== null && item !== undefined)
    versions.value = (versionsRes.data.results || versionsRes.data || []).filter(item => item !== null && item !== undefined)
    users.value = (usersRes.data.results || usersRes.data || []).filter(item => item !== null && item !== undefined)
  } catch (error) {
    console.error('获取基础数据失败:', error)
  }
}

// 根据选中的项目加载测试用例
const loadTestcasesByProjects = async (projectIds) => {
  if (!projectIds || projectIds.length === 0) {
    filteredTestcases.value = []
    return
  }

  loadingTestcases.value = true

  try {
    const params = new URLSearchParams()
    projectIds.forEach(id => params.append('project_ids', id))

    console.log('API URL:', `/executions/plans/testcases_by_projects/?${params.toString()}`)

    const response = await api.get(`/executions/plans/testcases_by_projects/?${params.toString()}`)
    console.log('API Response:', response.data)

    filteredTestcases.value = response.data.results || []
    console.log('Filtered testcases:', filteredTestcases.value)
  } catch (error) {
    console.error('Load testcases error:', error)
    if (error.response?.status === 400) {
      ElMessage.warning(error.response.data.detail || t('execution.selectProjectFirst'))
    } else if (error.response?.status === 401) {
      ElMessage.error(t('auth.loginFailed'))
    } else {
      ElMessage.error(t('execution.fetchTestcasesFailed') + ': ' + (error.response?.data?.detail || error.message))
    }
    filteredTestcases.value = []
  } finally {
    loadingTestcases.value = false
  }
}

// 处理测试用例选择器打开事件
const handleTestcaseSelectOpen = (visible) => {
  if (visible && (!newPlanForm.projects || newPlanForm.projects.length === 0)) {
    ElMessage.warning(t('execution.selectProjectFirst'))
    return false
  }
}

// 处理项目选择变化
const handleProjectChange = (selectedProjects) => {
  // 清空已选择的测试用例
  newPlanForm.testcases = []
  
  // 加载新项目的测试用例
  if (selectedProjects && selectedProjects.length > 0) {
    loadTestcasesByProjects(selectedProjects)
  } else {
    filteredTestcases.value = []
  }
}

const createPlan = async () => {
  try {
    await planFormRef.value.validate()
    creating.value = true

    await api.post('/executions/plans/', newPlanForm)
    ElMessage.success(t('execution.createSuccess'))
    isCreatePlanDialogOpen.value = false
    resetPlanForm()
    fetchTestPlans()
  } catch (error) {
    if (error.name !== 'ValidateError') {
      ElMessage.error(t('execution.createFailed'))
    }
  } finally {
    creating.value = false
  }
}

const viewPlan = (id) => {
  router.push(`/ai-generation/executions/${id}`)
}

const editPlan = async (plan) => {
  try {
    // 获取完整的测试计划详情
    const response = await api.get(`/executions/plans/${plan.id}/`)
    const planDetail = response.data

    // 设置当前编辑的计划
    currentEditingPlan.value = planDetail

    // 填充编辑表单数据
    Object.assign(editPlanForm, {
      id: planDetail.id,
      name: planDetail.name,
      description: planDetail.description || '',
      projects: planDetail.projects?.map(p => {
        // 如果是字符串，需要找到对应的项目ID
        const project = projects.value.find(proj => proj.name === p)
        return project ? project.id : p
      }) || [],
      version: planDetail.version ? versions.value.find(v => v.name === planDetail.version)?.id : null,
      assignees: planDetail.assignees || [],
      is_active: planDetail.is_active
    })

    isEditPlanDialogOpen.value = true
  } catch (error) {
    ElMessage.error(t('execution.fetchDetailFailed'))
  }
}

const updatePlan = async () => {
  try {
    await editPlanFormRef.value.validate()
    updating.value = true

    const updateData = {
      name: editPlanForm.name,
      description: editPlanForm.description,
      projects: editPlanForm.projects,
      version: editPlanForm.version,
      assignees: editPlanForm.assignees,
      is_active: editPlanForm.is_active
    }

    await api.put(`/executions/plans/${editPlanForm.id}/`, updateData)
    ElMessage.success(t('execution.updateSuccess'))
    isEditPlanDialogOpen.value = false
    resetEditForm()
    fetchTestPlans()
  } catch (error) {
    if (error.name !== 'ValidateError') {
      ElMessage.error(t('execution.updateFailed'))
    }
  } finally {
    updating.value = false
  }
}

const resetEditForm = () => {
  Object.assign(editPlanForm, {
    id: null,
    name: '',
    description: '',
    projects: [],
    version: null,
    assignees: [],
    is_active: true
  })
  currentEditingPlan.value = null
  editPlanFormRef.value?.resetFields()
}

const togglePlanStatus = async (plan) => {
  try {
    const action = plan.is_active ? t('execution.closePlan') : t('execution.activatePlan')
    await ElMessageBox.confirm(t('execution.toggleStatusConfirm', { action }), t('common.confirm'), {
      type: 'warning'
    })

    await api.patch(`/executions/plans/${plan.id}/`, {
      is_active: !plan.is_active
    })

    ElMessage.success(t('execution.toggleStatusSuccess', { action }))
    fetchTestPlans()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('execution.toggleStatusFailed'))
    }
  }
}

const openCreatePlanDialog = () => {
  resetPlanForm()
  isCreatePlanDialogOpen.value = true
}

const resetPlanForm = () => {
  Object.assign(newPlanForm, {
    name: '',
    description: '',
    projects: [], // 改为数组
    version: null,
    testcases: [],
    assignees: []
  })
  filteredTestcases.value = [] // 清空过滤后的测试用例
  loadingTestcases.value = false // 重置加载状态
  planFormRef.value?.resetFields()
}

const applyFilters = () => {
  currentPage.value = 1
  fetchTestPlans()
}

const resetFilters = () => {
  Object.assign(filters, {
    project: null,
    is_active: null
  })
  currentPage.value = 1
  fetchTestPlans()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchTestPlans()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchTestPlans()
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString()
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedPlans.value = selection
}

// 获取序号
const getSerialNumber = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 批量删除
const batchDeletePlans = async () => {
  if (selectedPlans.value.length === 0) {
    ElMessage.warning(t('execution.selectFirst'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('execution.batchDeleteConfirm', { count: selectedPlans.value.length }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    isDeleting.value = true
    let successCount = 0
    let failCount = 0

    for (const plan of selectedPlans.value) {
      try {
        await api.delete(`/executions/plans/${plan.id}/`)
        successCount++
      } catch (error) {
        console.error(`删除测试计划 ${plan.id} 失败:`, error)
        failCount++
      }
    }

    if (successCount > 0) {
      if (failCount > 0) {
        ElMessage.success(t('execution.batchDeletePartialSuccess', { successCount, failCount }))
      } else {
        ElMessage.success(t('execution.batchDeleteSuccess', { successCount }))
      }
    } else {
      ElMessage.error(t('execution.batchDeleteFailed'))
    }

    selectedPlans.value = []
    fetchTestPlans()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error(t('execution.batchDeleteFailed'))
    }
  } finally {
    isDeleting.value = false
  }
}

// 监听项目选择变化
watch(
  () => newPlanForm.projects,
  (newProjects, oldProjects) => {
    // 清空已选择的测试用例
    newPlanForm.testcases = []
    
    // 加载新项目的测试用例
    if (newProjects && newProjects.length > 0) {
      loadTestcasesByProjects(newProjects)
    } else {
      filteredTestcases.value = []
    }
  },
  { deep: true }
)

onMounted(() => {
  fetchTestPlans()
  fetchBasicData()
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
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .header-actions {
    display: flex;
    gap: 12px;

    .create-btn {
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

    .batch-delete-btn {
      background: linear-gradient(135deg, #ff7675 0%, #d63031 100%) !important;
      border: none !important;
      color: white !important;
      font-weight: 600 !important;
      padding: 10px 20px !important;
      border-radius: 8px !important;
      transition: all 0.3s ease !important;
      box-shadow: 0 4px 12px rgba(255, 118, 117, 0.3) !important;

      &:hover {
        background: linear-gradient(135deg, #d63031 0%, #ff7675 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 118, 117, 0.4) !important;
      }
    }
  }
}

// 筛选栏样式
.filter-bar {
  padding: 20px 24px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  border: 1px solid rgba(147, 112, 219, 0.1);

  .filter-form {
    :deep(.el-form-item) {
      margin-bottom: 0;
      margin-right: 16px;

      .el-form-item__label {
        color: #5a32a3;
        font-weight: 500;
      }

      .el-select {
        width: 200px;

        :deep(.el-input__wrapper) {
          box-shadow: 0 2px 8px rgba(147, 112, 219, 0.08);
          border-radius: 8px;
          background: #ffffff;
          border: 1px solid rgba(147, 112, 219, 0.2);
          transition: all 0.3s ease;

          &:hover {
            box-shadow: 0 2px 8px rgba(147, 112, 219, 0.15);
            border-color: #9370db;
          }

          &.is-focus {
            box-shadow: 0 0 0 2px rgba(147, 112, 219, 0.2);
            border-color: #5a32a3;
          }
        }

        :deep(.el-input__inner) {
          color: #5a32a3;
          font-weight: 500;

          &::placeholder {
            color: rgba(90, 50, 163, 0.5);
          }
        }

        :deep(.el-input__suffix) {
          color: #9370db;
        }
      }
    }
  }
}

// 表格容器
.table-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;
}

/* 表格样式 */
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

  :deep(.el-table__header-wrapper) {
    background-color: #ffffff !important;

    :deep(.el-table__header) {
      background-color: #ffffff !important;

      :deep(th) {
        background-color: #ffffff !important;
        color: #5a32a3;
        font-weight: 600;
        font-size: 14px;
        border-bottom: 1px solid #e9ecef;
        padding: 16px;
        text-align: left;
        line-height: 24px;
        transition: all 0.3s ease;

        &:hover {
          background-color: #ffffff !important;
        }

        :deep(.cell) {
          background-color: #ffffff !important;
          color: #5a32a3 !important;
          font-weight: 600 !important;
        }
      }
    }
  }

  :deep(.el-table__body-wrapper) {
    background-color: #ffffff !important;

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

      :deep(td) {
        padding: 14px 16px;
        border-bottom: 1px solid #e9ecef;
        color: #333;
        font-size: 14px;
        font-weight: 400;
        line-height: 24px;
        transition: all 0.3s ease;

        .el-tag {
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
          padding: 2px 8px;
          transition: all 0.3s ease;
        }

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

          &.el-button--text.el-button--warning {
            color: var(--warning-color);

            &:hover {
              color: #e09a00;
            }
          }

          &.el-button--text.el-button--success {
            color: var(--success-color);

            &:hover {
              color: #389e0d;
            }
          }
        }
      }
    }
  }

  :deep(.el-table__empty-block) {
    padding: 60px 0;
    background: #ffffff !important;

    :deep(.el-table__empty-text) {
      color: #666;
      font-size: 14px;
      line-height: 24px;
    }
  }

  &.el-table--enable-row-hover {
    background-color: #ffffff !important;
  }

  :deep(.el-table__row) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__row.el-table__row--striped) {
    background-color: #fafaff !important;
  }

  :deep(.el-table__row:hover) {
    background-color: #f8f7ff !important;
  }

  :deep(.el-table__header th) {
    background-color: #ffffff !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
  }

  :deep(.el-table__header th .cell) {
    background-color: #ffffff !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
  }

  .el-link {
    color: var(--primary-color);

    &:hover {
      color: var(--primary-dark);
    }
  }
}

// 分页容器
.pagination-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 8px 24px;
  background: transparent;
  border-top: 1px solid rgba(147, 112, 219, 0.1);
  transition: all 0.3s ease;

  /* 覆盖 Element Plus 分页组件样式 */
  --el-pagination-fill: #f8f7ff;
  --el-pagination-color: var(--text-secondary);
  --el-pagination-hover-color: var(--primary-color);
  --el-pagination-current-color: var(--primary-color);
  --el-pagination-current-bg-color: #f8f7ff;
  --el-pagination-btn-bg-color: #f8f7ff;
  --el-pagination-btn-hover-bg-color: rgba(102, 126, 234, 0.1);
  --el-pagination-border-color: rgba(147, 112, 219, 0.2);

  .el-pagination {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;

    // 总条数
    :deep(.el-pagination__total) {
      color: #5a32a3;
      font-size: 14px;
      font-weight: 500;
      margin-right: 12px;
    }

    // 每页条数选择器
    :deep(.el-pagination__sizes) {
      margin-right: 12px;

      .el-select {
        .el-input__wrapper {
          border-radius: 8px;
          border: 1px solid rgba(147, 112, 219, 0.2);
          background: #ffffff;
          box-shadow: none;

          &:hover {
            border-color: #7b42f6;
            box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.1);
          }

          &.is-focus {
            border-color: #7b42f6;
            box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.15);
          }
        }

        .el-input__inner {
          color: #5a32a3;
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
      border: 1px solid rgba(147, 112, 219, 0.2);
      background: #ffffff;
      color: #5a32a3;
      transition: all 0.3s ease;

      &:hover:not(:disabled) {
        background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
        border-color: transparent;
        color: white;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
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

    // 页码
    .el-pager {
      display: flex;
      gap: 4px;

      li {
        min-width: 32px;
        height: 32px;
        padding: 0 8px;
        border-radius: 8px;
        border: 1px solid rgba(147, 112, 219, 0.2);
        background: #ffffff;
        color: #5a32a3;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;

        &:hover:not(.is-active) {
          background: rgba(123, 66, 246, 0.1);
          border-color: #7b42f6;
          color: #7b42f6;
          transform: translateY(-1px);
        }

        &.is-active {
          background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
          border-color: transparent;
          color: white;
          box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
          font-weight: 600;
        }

        &.btn-quicknext,
        &.btn-quickprev {
          border: 1px solid rgba(147, 112, 219, 0.2);
          color: #9370db;

          &:hover {
            background: rgba(123, 66, 246, 0.1);
            color: #7b42f6;
          }
        }
      }
    }

    // 跳转页
    .el-pagination__jump {
      margin-left: 12px;
      color: #5a32a3;
      font-weight: 500;

      .el-input__wrapper {
        width: 48px;
        border-radius: 8px;
        border: 1px solid rgba(147, 112, 219, 0.2);
        background: #ffffff;
        box-shadow: none;

        &:hover {
          border-color: #7b42f6;
          box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.1);
        }

        &.is-focus {
          border-color: #7b42f6;
          box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.15);
        }
      }

      .el-input__inner {
        color: #5a32a3;
        font-weight: 500;
        text-align: center;
      }
    }
  }
}

/* 对话框样式 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
