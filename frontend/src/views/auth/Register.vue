<template>
  <div class="register-container">
    <div class="register-form">
      <div class="form-header">
        <h2>{{ $t('auth.registerTitle') }}</h2>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        @submit.prevent="handleRegister"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            :placeholder="$t('auth.username')"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            type="email"
            :placeholder="$t('auth.email')"
            size="large"
            :prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="$t('auth.password')"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item prop="password_confirm">
          <el-input
            v-model="form.password_confirm"
            type="password"
            :placeholder="$t('auth.confirmPassword')"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            size="large"
            :loading="loading"
            @click="handleRegister"
            style="width: 100%"
            class="register-button"
          >
            {{ $t('auth.register') }}
          </el-button>
        </el-form-item>

        <div class="form-footer">
          <router-link to="/login">{{ $t('auth.hasAccount') }}</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const { t } = useI18n()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  password_confirm: '',
  department: '',
  position: ''
})

const rules = computed(() => ({
  username: [
    { required: true, message: t('auth.usernameRequired'), trigger: 'blur' },
    { min: 3, max: 20, message: t('auth.usernameLength'), trigger: 'blur' }
  ],
  email: [
    { required: true, message: t('auth.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('auth.emailFormat'), trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('auth.passwordRequired'), trigger: 'blur' },
    { min: 6, message: t('auth.passwordLength'), trigger: 'blur' }
  ],
  password_confirm: [
    { required: true, message: t('auth.confirmPasswordRequired'), trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error(t('auth.passwordMismatch')))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}))

const handleRegister = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await userStore.register(form)
        ElMessage.success(t('auth.registerSuccess'))
        router.push('/login')
      } catch (error) {
        ElMessage.error(error.response?.data?.error || t('auth.registerFailed'))
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style lang="scss" scoped>
.register-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%);
}

.register-form {
  width: 500px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.5);

  :deep(.el-input__wrapper) {
    padding: 8px 16px;
    box-shadow: 0 0 0 1px #dcdfe6 inset;
    transition: all 0.3s ease;

    &:hover {
      box-shadow: 0 0 0 1px #8b5cf6 inset;
    }

    &.is-focus {
      box-shadow: 0 0 0 1px #8b5cf6 inset;
    }
  }

  .form-header {
    text-align: center;
    margin-bottom: 30px;
    
    h2 {
      color: #303133;
      font-size: 28px;
      font-weight: 600;
      margin: 0 0 10px 0;
    }
    
    p {
      color: #909399;
      margin: 0;
    }
  }
  
  .register-button {
    width: 100%;
    height: 48px;
    font-size: 16px;
    font-weight: 600;
    color: white;
    background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
    border: none;
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 20px rgba(139, 92, 246, 0.3);
    }
    
    &:active {
      transform: translateY(0);
    }
  }
  
  .form-footer {
    text-align: center;
    margin-top: 20px;

    a {
      color: #606266;
      text-decoration: none;
      font-size: 14px;
      transition: all 0.3s ease;

      &:hover {
        color: #8b5cf6;
      }
    }
  }
}
</style>