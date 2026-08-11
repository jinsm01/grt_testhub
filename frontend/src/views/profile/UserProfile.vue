<template>
  <div class="page-container">
    <div class="card-container">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="$t('profile.basicInfo')" name="basic">
          <div class="profile-layout">
            <!-- 上方头像区域 -->
            <div class="avatar-section">
              <div class="avatar-wrapper">
                <el-avatar 
                  :size="100" 
                  :src="avatarUrl"
                  class="user-avatar"
                >
                  <el-icon :size="50"><UserFilled /></el-icon>
                </el-avatar>
                <div class="avatar-overlay" @click="triggerAvatarUpload">
                  <el-icon :size="20"><Camera /></el-icon>
                  <span>更换头像</span>
                </div>
              </div>
              <input
                ref="avatarInput"
                type="file"
                accept="image/*"
                style="display: none"
                @change="handleAvatarUpload"
              />
              <p class="avatar-hint">支持 JPG、PNG、GIF 格式，最大 5MB</p>
            </div>

            <!-- 下方表单区域 -->
            <div class="form-section">
              <el-form v-if="userStore.user" :model="userStore.user" label-width="100px">
                <el-form-item :label="$t('profile.username')">
                  <el-input v-model="userStore.user.username" disabled />
                </el-form-item>
                <el-form-item :label="$t('profile.email')">
                  <el-input v-model="userStore.user.email" />
                </el-form-item>
                <el-form-item :label="$t('profile.name')">
                  <el-input v-model="userStore.user.first_name" />
                </el-form-item>
                <el-form-item :label="$t('profile.department')">
                  <el-input v-model="userStore.user.department" />
                </el-form-item>
                <el-form-item :label="$t('profile.position')">
                  <el-input v-model="userStore.user.position" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveProfile">{{ $t('common.save') }}</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="$t('profile.changePassword')" name="password">
          <el-form label-width="120px">
            <el-form-item :label="$t('profile.currentPassword')">
              <el-input v-model="passwordForm.currentPassword" type="password" show-password />
            </el-form-item>
            <el-form-item :label="$t('profile.newPassword')">
              <el-input v-model="passwordForm.newPassword" type="password" show-password />
            </el-form-item>
            <el-form-item :label="$t('profile.confirmPassword')">
              <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleChangePassword">{{ $t('profile.changePasswordButton') }}</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { UserFilled, Camera } from '@element-plus/icons-vue'
import api from '@/utils/api'

const userStore = useUserStore()
const activeTab = ref('basic')
const avatarInput = ref(null)
const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 计算头像URL
const avatarUrl = computed(() => {
  if (userStore.user?.avatar) {
    // 如果头像URL已经是完整路径，直接返回
    if (userStore.user.avatar.startsWith('http')) {
      return userStore.user.avatar
    }
    // 否则拼接媒体文件基础URL
    return `/api${userStore.user.avatar}`
  }
  return ''
})

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

// 修改密码
const handleChangePassword = async () => {
  // 前端基础校验
  if (!passwordForm.value.currentPassword) {
    ElMessage.warning('请输入当前密码')
    return
  }
  if (!passwordForm.value.newPassword) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (passwordForm.value.newPassword.length < 6) {
    ElMessage.warning('新密码长度不能少于6位')
    return
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (passwordForm.value.newPassword === passwordForm.value.currentPassword) {
    ElMessage.warning('新密码不能与当前密码相同')
    return
  }

  try {
    await api.post('/auth/change-password/', {
      current_password: passwordForm.value.currentPassword,
      new_password: passwordForm.value.newPassword,
      confirm_password: passwordForm.value.confirmPassword
    })

    ElMessage.success('密码修改成功，请重新登录')
    // 密码修改后旧 token 已失效，调用 logout 清除本地状态并跳转登录页
    setTimeout(() => {
      userStore.logout()
    }, 1500)
  } catch (error) {
    // 提取后端返回的错误信息
    const errors = error.response?.data
    if (errors) {
      // DRF 返回的是 {field: [error_msg]} 格式
      const firstKey = Object.keys(errors)[0]
      if (Array.isArray(errors[firstKey])) {
        ElMessage.error(errors[firstKey][0])
      } else {
        ElMessage.error(errors[firstKey])
      }
    } else {
      ElMessage.error('密码修改失败，请稍后重试')
    }
    console.error('修改密码失败:', error)
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
  
  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('只支持 JPG、PNG、GIF、WEBP 格式的图片')
    event.target.value = ''
    return
  }
  
  // 验证文件大小 (最大 5MB)
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('头像文件大小不能超过 5MB')
    event.target.value = ''
    return
  }
  
  try {
    const formData = new FormData()
    formData.append('avatar', file)
    
    const response = await api.post('/auth/upload-avatar/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    ElMessage.success('头像上传成功')
    // 更新本地存储的用户信息
    if (userStore.user) {
      userStore.user.avatar = response.data.avatar
      // 同步更新 localStorage
      localStorage.setItem('user', JSON.stringify(userStore.user))
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '头像上传失败，请稍后重试')
    console.error('上传头像失败:', error)
  } finally {
    // 清空文件输入，允许重复上传同一个文件
    event.target.value = ''
  }
}
</script>

<style scoped lang="scss">
.page-container {
  padding: 0;
  height: 100%;
}

.card-container {
  background: #f5f0ff;
  border-radius: 0;
  padding: 24px;
  box-shadow: none;
  height: 100%;
}

.profile-layout {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  padding: 24px 0;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.avatar-wrapper {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    .avatar-overlay {
      opacity: 1;
    }
  }
}

.user-avatar {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #5a32a3 0%, #7b42f6 100%);
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.3s ease;

  span {
    margin-top: 8px;
    font-size: 12px;
  }
}

.avatar-hint {
  margin-top: 12px;
  font-size: 12px;
  color: #999;
  text-align: center;
}

.form-section {
  width: 100%;
  max-width: 500px;
}

:deep(.el-form-item__label) {
  color: #666;
}

:deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  
  &.is-focus {
    box-shadow: 0 0 0 1px #5a32a3 inset !important;
  }
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #5a32a3 0%, #7b42f6 100%);
  border: none;
  
  &:hover {
    background: linear-gradient(135deg, #4a2790 0%, #6b38e0 100%);
  }
}
</style>