<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">个人设置</h1>
    </div>
    
    <div class="card-container">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="basic">
          <div class="profile-header" style="margin-bottom: 30px; display: flex; align-items: center;">
            <div class="avatar-container" style="margin-right: 30px;">
              <el-avatar :size="120" :src="userStore.user?.avatar || ''" style="border: 2px solid #eaeaea;">
                {{ userStore.user?.username?.charAt(0).toUpperCase() || 'U' }}
              </el-avatar>
              <div style="margin-top: 10px; text-align: center;">
                <el-button size="small" @click="triggerAvatarUpload">更换头像</el-button>
                <input type="file" ref="avatarInput" style="display: none;" accept="image/*" @change="handleAvatarUpload">
              </div>
            </div>
            <div>
              <h3>{{ userStore.user?.username }}</h3>
              <p style="color: #666;">{{ userStore.user?.email }}</p>
            </div>
          </div>
          
          <el-form v-if="userStore.user" :model="userStore.user" label-width="100px">
            <el-form-item label="用户名">
              <el-input v-model="userStore.user.username" disabled />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="userStore.user.email" />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="userStore.user.first_name" />
            </el-form-item>
            <el-form-item label="部门">
              <el-input v-model="userStore.user.department" />
            </el-form-item>
            <el-form-item label="职位">
              <el-input v-model="userStore.user.position" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveProfile">保存</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="修改密码" name="password">
          <el-form label-width="100px">
            <el-form-item label="当前密码">
              <el-input type="password" />
            </el-form-item>
            <el-form-item label="新密码">
              <el-input type="password" />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input type="password" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const userStore = useUserStore()
const activeTab = ref('basic')
const avatarInput = ref(null)

// 保存个人信息
const saveProfile = async () => {
  try {
    // 只发送存在的字段
    const updateData = {}
    if (userStore.user.email) updateData.email = userStore.user.email
    if (userStore.user.first_name) updateData.first_name = userStore.user.first_name
    if (userStore.user.department) updateData.department = userStore.user.department
    if (userStore.user.position) updateData.position = userStore.user.position
    
    const response = await api.put(`/auth/users/${userStore.user.id}/`, updateData)
    
    ElMessage.success('保存成功')
    // 更新本地存储的用户信息
    localStorage.setItem('user', JSON.stringify(response.data))
  } catch (error) {
    ElMessage.error('保存失败，请稍后重试')
    console.error('保存个人信息失败:', error)
  }
}

// 触发头像上传
const triggerAvatarUpload = () => {
  avatarInput.value.click()
}

// 处理头像上传
const handleAvatarUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  try {
    const formData = new FormData()
    formData.append('avatar', file)
    
    const response = await api.put(`/auth/users/${userStore.user.id}/`, formData)
    
    ElMessage.success('头像更新成功')
    // 更新本地存储的用户信息
    localStorage.setItem('user', JSON.stringify(response.data))
    // 刷新用户信息
    await userStore.fetchProfile()
  } catch (error) {
    ElMessage.error('头像更新失败，请稍后重试')
    console.error('上传头像失败:', error)
  } finally {
    // 清空文件输入，允许重复上传同一个文件
    event.target.value = ''
  }
}
</script>