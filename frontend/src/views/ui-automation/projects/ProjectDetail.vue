<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">项目详情</h1>
      <el-button type="primary" @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>
    
    <div class="card-container">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="项目信息" name="info">
          <div v-if="project">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="项目名称">{{ project.name }}</el-descriptions-item>
              <el-descriptions-item label="项目状态">
                <el-tag :type="getStatusType(project.status)">{{ getStatusText(project.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="负责人">{{ project.owner?.username }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDate(project.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="基础URL">{{ project.base_url }}</el-descriptions-item>
              <el-descriptions-item label="开始日期">{{ project.start_date ? formatDate(project.start_date) : '未设置' }}</el-descriptions-item>
              <el-descriptions-item label="结束日期">{{ project.end_date ? formatDate(project.end_date) : '未设置' }}</el-descriptions-item>
              <el-descriptions-item label="更新时间">{{ formatDate(project.updated_at) }}</el-descriptions-item>
              <el-descriptions-item label="项目描述" :span="2">{{ project.description || '暂无描述' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="项目成员" name="members">
          <div class="members-section">
            <el-button type="primary" @click="showAddMemberDialog = true">添加成员</el-button>
            <el-table :data="project?.members || []" style="width: 100%; margin-top: 20px;">
              <el-table-column label="用户名">
                <template #default="{ row }">
                  {{ row.user?.username || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="邮箱">
                <template #default="{ row }">
                  {{ row.user?.email || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="角色">
                <template #default="{ row }">
                  {{ row.role || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="加入时间">
                <template #default="{ row }">
                  {{ formatDate(row.joined_at) || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button size="small" type="danger" @click="removeMember(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
    
    <!-- 添加成员对话框 -->
    <el-dialog v-model="showAddMemberDialog" title="添加项目成员" :close-on-click-modal="false" width="500px">
      <el-form ref="addMemberFormRef" :model="addMemberForm" :rules="addMemberRules" label-width="80px">
        <el-form-item label="用户" prop="user_id">
          <el-select v-model="addMemberForm.user_id" placeholder="请选择用户" filterable>
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="addMemberForm.role" placeholder="请选择角色">
            <el-option label="管理员" value="admin" />
            <el-option label="开发者" value="developer" />
            <el-option label="测试者" value="tester" />
            <el-option label="观察者" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddMemberDialog = false">取消</el-button>
          <el-button type="primary" @click="addMember">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getUiProjectDetail } from '@/api/ui_automation'
import api from '@/utils/api'
import dayjs from 'dayjs'

const route = useRoute()
const project = ref(null)
const activeTab = ref('info')
const showAddMemberDialog = ref(false)
const users = ref([])
const addMemberFormRef = ref()

const addMemberForm = ref({
  user_id: '',
  role: 'tester'
})

const addMemberRules = {
  user_id: [
    { required: true, message: '请选择用户', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'blur' }
  ]
}

const fetchProject = async () => {
  try {
    const response = await getUiProjectDetail(route.params.id)
    project.value = response.data
  } catch (error) {
    ElMessage.error('获取项目详情失败')
  }
}

const fetchUsers = async () => {
  try {
    const response = await api.get('/api-testing/users/')
    users.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('获取用户列表失败')
  }
}

const getStatusType = (status) => {
  const typeMap = {
    'NOT_STARTED': 'warning',
    'IN_PROGRESS': 'primary',
    'COMPLETED': 'success'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'NOT_STARTED': '未开始',
    'IN_PROGRESS': '进行中',
    'COMPLETED': '已结束'
  }
  return textMap[status] || status
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

const addMember = async () => {
  try {
    const response = await api.post(`/ui-automation/projects/${route.params.id}/members/`, addMemberForm.value)
    ElMessage.success('成员添加成功')
    showAddMemberDialog.value = false
    // 重置表单
    addMemberForm.value.user_id = ''
    addMemberForm.value.role = 'tester'
    // 重新获取项目信息
    fetchProject()
  } catch (error) {
    ElMessage.error('添加成员失败')
  }
}

const removeMember = async (row) => {
  try {
    await api.delete(`/ui-automation/projects/${route.params.id}/members/${row.user?.id || row.id}/`)
    ElMessage.success('成员删除成功')
    // 重新获取项目信息
    fetchProject()
  } catch (error) {
    ElMessage.error('删除成员失败')
  }
}

onMounted(() => {
  fetchProject()
  fetchUsers()
})
</script>

<style lang="scss" scoped>
.members-section {
  padding: 20px 0;
}
</style>