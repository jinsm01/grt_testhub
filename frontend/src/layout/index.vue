<template>
  <div class="layout">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="240px">
        <div class="logo" @click="router.push('/home')" style="cursor: pointer;">
          <img src="@/assets/images/logo_home.svg" alt="TestHub" />
        </div>
        <el-menu
          :default-active="$route.path"
          router
          text-color="#fff"
          active-text-color="#fff"
          mode="vertical"
          collapse-transition="false"
        >
          <!-- AI用例生成模块菜单 -->
          <template v-if="currentModule === 'ai-generation'">
            <el-sub-menu index="requirement">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>{{ $t('menu.intelligentCaseGeneration') }}</span>
              </template>
              <el-menu-item index="/ai-generation/requirement-analysis">
                <el-icon><Aim /></el-icon>
                <span>{{ $t('menu.aiCaseGeneration') }}</span>
              </el-menu-item>
              <el-menu-item index="/ai-generation/generated-testcases">
                <el-icon><Files /></el-icon>
                <span>{{ $t('menu.aiGeneratedTestcases') }}</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/ai-generation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/testcases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.testCases') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/versions">
              <el-icon><Flag /></el-icon>
              <span>{{ $t('menu.versionManagement') }}</span>
            </el-menu-item>
            <el-sub-menu index="reviews">
              <template #title>
                <el-icon><Check /></el-icon>
                <span>{{ $t('menu.reviewManagement') }}</span>
              </template>
              <el-menu-item index="/ai-generation/reviews">
                <el-icon><List /></el-icon>
                <span>{{ $t('menu.reviewList') }}</span>
              </el-menu-item>
              <el-menu-item index="/ai-generation/review-templates">
                <el-icon><Notebook /></el-icon>
                <span>{{ $t('menu.reviewTemplates') }}</span>
              </el-menu-item>
            </el-sub-menu>

            <el-menu-item index="/ai-generation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.testPlan') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
          </template>

          <!-- 接口测试模块菜单 -->
          <template v-else-if="currentModule === 'api-testing'">
            <el-menu-item index="/api-testing/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.dashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/interfaces">
              <el-icon><Link /></el-icon>
              <span>{{ $t('menu.interfaceManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/automation">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.automationTesting') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/history">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.requestHistory') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/environments">
              <el-icon><Setting /></el-icon>
              <span>{{ $t('menu.environmentManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.scheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.notificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- UI自动化测试模块菜单 -->
          <template v-else-if="currentModule === 'ui-automation'">
            <el-menu-item index="/ui-automation/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.dashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/elements-enhanced">
              <el-icon><Aim /></el-icon>
              <span>{{ $t('menu.elementManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/test-cases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.caseManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts-enhanced">
              <el-icon><Edit /></el-icon>
              <span>{{ $t('menu.scriptGeneration') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts">
              <el-icon><DocumentCopy /></el-icon>
              <span>{{ $t('menu.scriptList') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/suites">
              <el-icon><Collection /></el-icon>
              <span>{{ $t('menu.suiteManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.executionRecords') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.scheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.notificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- AI 智能模式模块菜单 -->
          <template v-else-if="currentModule === 'ai-intelligent-mode'">
            <el-menu-item index="/ai-intelligent-mode/testing">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.aiIntelligentTesting') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-intelligent-mode/cases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.aiCaseManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-intelligent-mode/execution-records">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.aiExecutionRecords') }}</span>
            </el-menu-item>

          </template>

          <!-- 配置中心模块菜单 -->
          <template v-else-if="currentModule === 'configuration'">
            <el-sub-menu index="ai-case-generation">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>{{ $t('menu.aiCaseGenerationConfig') }}</span>
              </template>
              <el-menu-item index="/configuration/ai-model">
                <el-icon><Cpu /></el-icon>
                <span>{{ $t('menu.aiModelConfig') }}</span>
              </el-menu-item>
              <el-menu-item index="/configuration/prompt-config">
                <el-icon><Edit /></el-icon>
                <span>{{ $t('menu.promptConfig') }}</span>
              </el-menu-item>
              <el-menu-item index="/configuration/generation-config">
                <el-icon><Setting /></el-icon>
                <span>{{ $t('menu.generationConfig') }}</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/configuration/ui-env">
              <el-icon><Monitor /></el-icon>
              <span>{{ $t('menu.uiEnvConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/ai-mode">
              <el-icon><MagicStick /></el-icon>
              <span>{{ $t('menu.aiModeConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/scheduled-task">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.scheduledTaskConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/dify">
              <el-icon><ChatDotRound /></el-icon>
              <span>{{ $t('menu.difyConfig') }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-aside>

      <!-- 主体内容 -->
      <el-container>
        <!-- 顶部导航 -->
        <el-header height="60px">
          <div class="header-content">
            <div class="header-left">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/home' }">{{ $t('nav.home') }}</el-breadcrumb-item>
                <el-breadcrumb-item v-if="moduleName">{{ moduleName }}</el-breadcrumb-item>
                <el-breadcrumb-item>{{ breadcrumbTitle }}</el-breadcrumb-item>
              </el-breadcrumb>
            </div>
            <div class="header-right">


              <!-- 用户信息 -->
              <el-dropdown @command="handleCommand" class="user-dropdown">
                <span class="user-info">
                  <el-avatar :size="32" :src="avatarUrl">
                    <el-icon :size="20"><UserFilled /></el-icon>
                  </el-avatar>
                  <span class="username">{{ userStore.user?.username }}</span>
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="profile">{{ $t('nav.profile') }}</el-dropdown-item>
                    <el-dropdown-item divided command="logout">{{ $t('nav.logout') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </el-header>

        <!-- 页面内容 -->
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  Monitor, Folder, Document, Flag, Check, Collection, VideoPlay,
  DataAnalysis, ChatDotRound, DocumentCopy, Link, MagicStick,
  Odometer, Timer, Setting, AlarmClock, Bell, Aim, Edit, Cpu,
  UserFilled, List, Files, Notebook
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const appStore = useAppStore()
const { t } = useI18n()

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

onMounted(async () => {
  console.log('Layout 初始化用户信息...')
  await userStore.initAuth()
  console.log('Layout 用户信息初始化完成:', userStore.user)
  console.log('Layout 用户头像:', userStore.user?.avatar)
  console.log('Layout 头像URL:', avatarUrl.value)
})

const currentModule = computed(() => {
  if (route.path.startsWith('/ai-generation')) return 'ai-generation'
  if (route.path.startsWith('/api-testing')) return 'api-testing'
  if (route.path.startsWith('/ui-automation')) return 'ui-automation'
  if (route.path.startsWith('/ai-intelligent-mode')) return 'ai-intelligent-mode'
  if (route.path.startsWith('/configuration')) return 'configuration'
  return ''
})

const moduleName = computed(() => {
  const map = {
    'ai-generation': t('modules.aiGeneration'),
    'api-testing': t('modules.apiTesting'),
    'ui-automation': t('modules.uiAutomation'),
    'ai-intelligent-mode': t('modules.aiIntelligentMode'),
    'configuration': t('modules.configuration')
  }
  return map[currentModule.value] || ''
})

const breadcrumbTitle = computed(() => {
  const routeMap = {
    // AI用例生成
    '/ai-generation/requirement-analysis': t('menu.aiCaseGeneration'),
    '/ai-generation/generated-testcases': t('menu.aiGeneratedTestcases'),
    '/ai-generation/projects': t('menu.projectManagement'),
    '/ai-generation/testcases': t('menu.testCases'),
    '/ai-generation/versions': t('menu.versionManagement'),
    '/ai-generation/reviews': t('menu.reviewList'),
    '/ai-generation/review-templates': t('menu.reviewTemplates'),
    '/ai-generation/testsuites': t('menu.suiteManagement'),
    '/ai-generation/executions': t('menu.executionRecords'),
    '/ai-generation/reports': t('menu.testReport'),

    // 接口测试
    '/api-testing/dashboard': t('menu.dashboard'),
    '/api-testing/projects': t('menu.projectManagement'),
    '/api-testing/interfaces': t('menu.interfaceManagement'),
    '/api-testing/automation': t('menu.automationTesting'),
    '/api-testing/history': t('menu.requestHistory'),
    '/api-testing/environments': t('menu.environmentManagement'),
    '/api-testing/reports': t('menu.testReport'),
    '/api-testing/scheduled-tasks': t('menu.scheduledTasks'),
    '/api-testing/notification-logs': t('menu.notificationList'),

    // UI自动化测试
    '/ui-automation/dashboard': t('menu.dashboard'),
    '/ui-automation/projects': t('menu.projectManagement'),
    '/ui-automation/elements-enhanced': t('menu.elementManagement'),
    '/ui-automation/test-cases': t('menu.caseManagement'),
    '/ui-automation/scripts-enhanced': t('menu.scriptGeneration'),
    '/ui-automation/scripts': t('menu.scriptList'),
    '/ui-automation/suites': t('menu.suiteManagement'),
    '/ui-automation/executions': t('menu.executionRecords'),
    '/ui-automation/reports': t('menu.testReport'),
    '/ui-automation/scheduled-tasks': t('menu.scheduledTasks'),
    '/ui-automation/notification-logs': t('menu.notificationList'),

    // AI 智能模式
    '/ai-intelligent-mode/testing': t('menu.aiIntelligentTesting'),
    '/ai-intelligent-mode/cases': t('menu.aiCaseManagement'),
    '/ai-intelligent-mode/execution-records': t('menu.aiExecutionRecords'),


    // 配置中心
    '/configuration/ai-model': t('menu.aiModelConfig'),
    '/configuration/prompt-config': t('menu.promptConfig'),
    '/configuration/generation-config': t('menu.generationConfig'),
    '/configuration/ui-env': t('menu.uiEnvConfig'),
    '/configuration/ai-mode': t('menu.aiModeConfig'),
    '/configuration/scheduled-task': t('menu.scheduledTaskConfig'),
    '/configuration/dify': t('menu.difyConfig'),
    
    '/profile': t('nav.profile')
  }
  return routeMap[route.path] || route.meta.title || ''
})

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success('退出登录成功')
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/ai-generation/profile')
  }
}
</script>

<style lang="scss" scoped>
.layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.layout > .el-container {
  height: 100%;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f0fa;
  color: #5a32a3;
  border-bottom: 1px solid rgba(90, 50, 163, 0.2);
  flex-shrink: 0;
  position: relative;
  overflow: hidden;

  img {
    height: 80%;
    width: auto;
    object-fit: contain;
    transition: all 0.3s ease;
  }

  &:hover img {
    transform: scale(1.05);
  }

  h2 {
    margin: 0;
    font-weight: 600;
    font-size: 20px;
  }
}

.el-aside {
  position: relative;
  background: linear-gradient(135deg, #f3f0fa 0%, #e8e3f5 50%, #f3f0fa 100%);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.3s ease;
  width: 240px !important;
  min-width: 240px;
  max-width: 240px;
  box-shadow: 2px 0 10px rgba(90, 50, 163, 0.1);

  &::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 100px;
    height: 100px;
    background: linear-gradient(45deg, rgba(90, 50, 163, 0.1), rgba(74, 20, 140, 0.05));
    border-radius: 0 0 0 100%;
    z-index: 1;
  }

  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 150px;
    height: 150px;
    background: linear-gradient(135deg, rgba(90, 50, 163, 0.05), rgba(74, 20, 140, 0.1));
    border-radius: 100% 0 0 0;
    z-index: 1;
  }

  .el-menu {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    border-right: none;
    background: transparent !important;
    position: relative;
    z-index: 2;
    
    &::-webkit-scrollbar {
      width: 6px;
    }
    
    &::-webkit-scrollbar-track {
      background: rgba(90, 50, 163, 0.05);
      border-radius: 10px;
    }
    
    &::-webkit-scrollbar-thumb {
      background: rgba(90, 50, 163, 0.2);
      border-radius: 10px;
    }
    
    &::-webkit-scrollbar-thumb:hover {
      background: rgba(90, 50, 163, 0.3);
    }
  }
}

.el-menu {
  :deep(.el-sub-menu__title),
  :deep(.el-menu-item) {
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    width: calc(100% - 24px) !important; /* Adjust for margins */
  }
  
  /* 调整图标与文字间距，固定图标宽度确保对齐 */
  :deep(.el-sub-menu__title > .el-icon),
  :deep(.el-menu-item > .el-icon) {
    width: 20px;
    margin-right: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* 子菜单项图标样式 */
  :deep(.el-sub-menu__content .el-menu-item > .el-icon) {
    width: 18px;
    margin-right: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
  }
  
  /* 确保箭头右对齐 */
  :deep(.el-sub-menu__title) {
    position: relative;
  }
  
  :deep(.el-sub-menu__title .el-sub-menu__icon-arrow) {
    position: absolute;
    right: 16px;
  }
  
  :deep(.el-menu-item) {
    background: #f3f0fa !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(90, 50, 163, 0.05) !important;
    backdrop-filter: blur(10px) !important;
    width: calc(100% - 24px) !important; /* Adjust for margins */
    box-sizing: border-box !important;
    outline: none !important;
    
    &:focus {
      outline: none !important;
      box-shadow: 0 2px 8px rgba(90, 50, 163, 0.05) !important;
    }
  }
  
  :deep(.el-sub-menu__title) {
    background: #f3f0fa !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(90, 50, 163, 0.05) !important;
    backdrop-filter: blur(10px) !important;
    width: calc(100% - 24px) !important; /* Adjust for margins */
    box-sizing: border-box !important;
    outline: none !important;
    
    &:focus {
      outline: none !important;
      box-shadow: 0 2px 8px rgba(90, 50, 163, 0.05) !important;
    }
  }
  
  :deep(.el-menu-item.is-active) {
    background: #5a32a3 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-right: none !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.3) !important;
    backdrop-filter: blur(10px) !important;
    outline: none !important;
    
    &:focus {
      outline: none !important;
      box-shadow: 0 4px 12px rgba(90, 50, 163, 0.3) !important;
    }
  }
  
  :deep(.el-sub-menu__title.is-active) {
    background: #5a32a3 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-right: none !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.3) !important;
    backdrop-filter: blur(10px) !important;
    outline: none !important;
    
    &:focus {
      outline: none !important;
      box-shadow: 0 4px 12px rgba(90, 50, 163, 0.3) !important;
    }
  }
  
  :deep(.el-menu-item:hover) {
    background: #e1d7f0 !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.1) !important;
    backdrop-filter: blur(10px) !important;
    outline: none !important;
    
    &:focus {
      outline: none !important;
      box-shadow: 0 4px 12px rgba(90, 50, 163, 0.1) !important;
    }
  }
  
  :deep(.el-sub-menu__title:hover) {
    background: #e1d7f0 !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.1) !important;
    backdrop-filter: blur(10px) !important;
    outline: none !important;
    
    &:focus {
      outline: none !important;
      box-shadow: 0 4px 12px rgba(90, 50, 163, 0.1) !important;
    }
  }
  
  :deep(.el-menu-item.is-active:hover) {
    background: #4a148c !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-right: none !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 6px 16px rgba(74, 20, 140, 0.4) !important;
    backdrop-filter: blur(10px) !important;
    outline: none !important;
    
    &:focus {
      outline: none !important;
      box-shadow: 0 6px 16px rgba(74, 20, 140, 0.4) !important;
    }
  }
  
  :deep(.el-sub-menu__title.is-active:hover) {
    background: #4a148c !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-right: none !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 6px 16px rgba(74, 20, 140, 0.4) !important;
    backdrop-filter: blur(10px) !important;
    outline: none !important;
    
    &:focus {
      outline: none !important;
      box-shadow: 0 6px 16px rgba(74, 20, 140, 0.4) !important;
    }
  }
  
  /* 自定义悬浮子菜单样式 - 统一背景 */
  :deep(.custom-submenu-popper .el-menu) {
    background: #f3f0fa !important; /* 统一背景色，与主侧边栏一致 */
    border: 1px solid #e9ecef !important; /* 添加边框 */
    border-radius: 8px !important; /* 保持圆角 */
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1) !important; /* 悬浮阴影 */
    padding: 4px !important; /* 内边距 */
  }
  
  /* 自定义悬浮子菜单项样式 */
  :deep(.custom-submenu-popper .el-menu .el-menu-item) {
    background: transparent !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    margin: 2px 4px !important;
    padding: 10px 16px !important;
    border-radius: 6px !important;
    transition: all 0.3s ease !important;
  }
  
  /* 自定义悬浮子菜单项悬停状态 */
  :deep(.custom-submenu-popper .el-menu .el-menu-item:hover) {
    background: #e1d7f0 !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
  }
  
  /* 自定义悬浮子菜单项激活状态 */
  :deep(.custom-submenu-popper .el-menu .el-menu-item.is-active) {
    background: #5a32a3 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
  }
  
  /* 通过popper显示子菜单内容 */
  :deep(.custom-submenu-popper.el-popper) {
    background: #f3f0fa !important;
    border: 1px solid #e9ecef !important;
    border-radius: 8px !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15) !important;
  }
  
  /* 子菜单样式 - 确保背景色一致 */
  :deep(.el-sub-menu) {
    background: transparent !important;
  }

  /* 旧的子菜单样式 - 保持兼容性 */
  :deep(.el-sub-menu__content) {
    background: #f3f0fa !important;
    border-left: none !important;
    max-height: none !important;
    overflow: visible !important;
    transition: all 0.3s ease !important;
    margin: 0 !important;
    padding: 0 !important;
    box-shadow: none !important;
    border: none !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 内联菜单样式 - 透明背景继承父级 */
  :deep(.el-menu--inline),
  :deep(.el-sub-menu .el-menu--inline),
  :deep(.el-menu--vertical .el-menu--inline) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  
  /* 智能用例生成子菜单特殊处理 */
  :deep(.el-menu-item-group) {
    background: transparent !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  :deep(.el-menu-item-group__title) {
    background: transparent !important;
    color: #5a32a3 !important;
    margin: 0 !important;
    padding: 0 !important;
    font-size: 12px !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 子菜单项样式 - 统一文字颜色 */
  :deep(.el-sub-menu__content .el-menu-item) {
    background: #f3f0fa !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    margin: 6px 12px !important;
    padding: 0 20px !important;
    transition: all 0.3s ease !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(90, 50, 163, 0.05) !important;
    backdrop-filter: blur(10px) !important;
    width: calc(100% - 24px) !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 子菜单项hover和激活状态 */
  :deep(.el-sub-menu__content .el-menu-item:hover) {
    background: #e1d7f0 !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.1) !important;
    padding: 0 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    backdrop-filter: blur(10px) !important;
    width: calc(100% - 24px) !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 子菜单项激活状态 - 高亮 */
  :deep(.el-sub-menu__content .el-menu-item.is-active) {
    background: #5a32a3 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding: 0 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.3) !important;
    backdrop-filter: blur(10px) !important;
    width: calc(100% - 24px) !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 子菜单项激活+hover状态 */
  :deep(.el-sub-menu__content .el-menu-item.is-active:hover) {
    background: #4a148c !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding: 0 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(74, 20, 140, 0.4) !important;
    backdrop-filter: blur(10px) !important;
    width: calc(100% - 24px) !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 智能用例生成子菜单特殊处理 - 确保无白色背景 */
  :deep(.el-sub-menu .el-sub-menu__content) {
    background: #f3f0fa !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 菜单项组特殊处理 */
  :deep(.el-menu-item-group) {
    background: #f3f0fa !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 菜单项组标题特殊处理 */
  :deep(.el-menu-item-group__title) {
    background: #f3f0fa !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 确保整个侧边栏无白色背景 */
  :deep(.el-menu) {
    background: #f3f0fa !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 确保所有菜单项无白色背景 */
  :deep(.el-menu-item) {
    background: #f3f0fa !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 确保所有子菜单项无白色背景 */
  :deep(.el-sub-menu__title) {
    background: #f3f0fa !important;
    border-right: none !important;
    border-bottom: none !important;
  }
}

.el-menu--collapse {
  width: 64px !important;
  
  :deep(.el-sub-menu__title),
  :deep(.el-menu-item) {
    padding-left: 20px !important;
    width: calc(100% - 24px) !important; /* Adjust for margins */
  }
  
  :deep(.el-sub-menu__title span),
  :deep(.el-menu-item span) {
    display: none;
  }
}

/* Responsive styles for smaller screens */
@media (max-width: 768px) {
  .el-aside {
    width: 200px !important;
    min-width: 200px;
    max-width: 200px;
  }
  
  .el-menu :deep(.el-menu-item),
  .el-menu :deep(.el-sub-menu__title) {
    margin: 4px 8px !important;
    width: calc(100% - 16px) !important;
  }
}

@media (max-width: 576px) {
  .el-aside {
    width: 180px !important;
    min-width: 180px;
    max-width: 180px;
  }
  
  .el-menu :deep(.el-menu-item),
  .el-menu :deep(.el-sub-menu__title) {
    margin: 3px 6px !important;
    width: calc(100% - 12px) !important;
    height: 36px !important;
    padding-left: 16px !important;
  }
  
  .el-menu :deep(.el-menu-item span),
  .el-menu :deep(.el-sub-menu__title span) {
    font-size: 13px !important;
  }
}

.el-container .el-container {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.el-header {
  background: linear-gradient(135deg, #f3f0fa 0%, #e8e3f5 100%);
  border-bottom: 1px solid rgba(90, 50, 163, 0.2);
  padding: 0;
  flex-shrink: 0;
  height: 60px !important;
  box-shadow: 0 2px 8px rgba(90, 50, 163, 0.1);
  backdrop-filter: blur(10px);

  .header-content {
    height: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 24px;
  }

  .header-left {
    flex: 1;
    overflow: hidden;
    
    :deep(.el-breadcrumb) {
      font-size: 14px;
      font-weight: 500;
      
      .el-breadcrumb__item {
        .el-breadcrumb__inner {
          color: #5a32a3;
          font-weight: 500;
          
          &:hover {
            color: #7b42f6;
          }
          
          &.is-link {
            color: #9370db;
            font-weight: 500;
            
            &:hover {
              color: #7b42f6;
              text-decoration: underline;
            }
          }
        }
        
        .el-breadcrumb__separator {
          color: #9370db;
          margin: 0 8px;
        }
      }
    }
  }

  .user-info {
    display: flex;
    align-items: center;
    cursor: pointer;
    white-space: nowrap;
    outline: none;
    padding: 6px 12px;
    border-radius: 20px;
    transition: all 0.3s ease;
    background: rgba(255, 255, 255, 0.8);
    box-shadow: 0 2px 8px rgba(90, 50, 163, 0.1);
    
    &:hover {
      background: rgba(255, 255, 255, 1);
      box-shadow: 0 4px 12px rgba(90, 50, 163, 0.15);
      transform: translateY(-1px);
    }

    .username {
      margin: 0 10px;
      color: #5a32a3;
      font-size: 14px;
      font-weight: 500;
    }
    
    .el-avatar {
      border: 2px solid rgba(90, 50, 163, 0.2);
      transition: all 0.3s ease;
      background: linear-gradient(135deg, #5a32a3 0%, #7b42f6 100%) !important;
      
      &:hover {
        border-color: #9370db;
        box-shadow: 0 0 0 2px rgba(147, 112, 219, 0.2);
      }
      
      :deep(img) {
        object-fit: cover;
      }
    }
    
    .el-icon {
      color: #5a32a3;
      transition: all 0.3s ease;
      
      &:hover {
        color: #7b42f6;
      }
    }
  }
  
  /* 下拉菜单样式 */
  .user-dropdown {
    :deep(.el-dropdown-menu) {
      background: rgba(255, 255, 255, 0.95) !important;
      border: 1px solid rgba(90, 50, 163, 0.2) !important;
      border-radius: 12px !important;
      box-shadow: 0 4px 16px rgba(90, 50, 163, 0.15) !important;
      backdrop-filter: blur(10px) !important;
      padding: 8px 0 !important;
      
      .el-dropdown-menu__item {
        color: #5a32a3 !important;
        font-weight: 500 !important;
        padding: 10px 20px !important;
        margin: 0 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        
        &:hover,
        &:focus {
          background: linear-gradient(135deg, #f3f0fa 0%, #e8e3f5 100%) !important;
          color: #7b42f6 !important;
          font-weight: 600 !important;
          box-shadow: 0 2px 8px rgba(90, 50, 163, 0.1) !important;
        }
        
        &.is-disabled {
          color: #c0c4cc !important;
          
          &:hover {
            background: transparent !important;
            color: #c0c4cc !important;
          }
        }
      }
      
      .el-dropdown-menu__item--divided {
        border-top: 1px solid rgba(90, 50, 163, 0.1) !important;
        margin-top: 8px !important;
        padding-top: 8px !important;
      }
    }
  }
  
  /* 全局下拉菜单样式覆盖 */
  :global(.el-dropdown-menu__item:hover) {
    background: linear-gradient(135deg, #f3f0fa 0%, #e8e3f5 100%) !important;
    color: #7b42f6 !important;
  }
}

/* 全局覆盖 Element Plus 默认样式 - 防止子菜单背景重叠 */
:global(.el-menu--inline) {
  background: transparent !important;
}

:global(.el-menu--vertical .el-menu--inline) {
  background: transparent !important;
}

/* 最高优先级覆盖 - 确保子菜单内联菜单背景透明 */
:global(.el-menu.el-menu--inline) {
  background-color: transparent !important;
  background: transparent !important;
}

/* 针对 AI 用例生成模块的子菜单样式 */
:global(.el-sub-menu .el-menu.el-menu--inline) {
  background: transparent !important;
  background-color: transparent !important;
}

/* 确保所有子菜单下的内联菜单背景透明 */
:global(.el-menu--vertical .el-sub-menu .el-menu--inline) {
  background: transparent !important;
  background-color: transparent !important;
}

/* 使用属性选择器提高优先级 */
:global([class*="el-menu--inline"]) {
  background: transparent !important;
  background-color: transparent !important;
}

/* 针对展开状态的子菜单内联菜单 */
:global(.el-sub-menu.is-opened .el-menu--inline) {
  background: transparent !important;
  background-color: transparent !important;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  

  .user-dropdown {
    .user-info {
      display: flex;
      align-items: center;
      cursor: pointer;
      white-space: nowrap;

      .username {
        margin: 0 8px;
        color: #303133;
      }
    }
  }

.el-main {
  background-color: #f5f5f5;
  padding: 20px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

@media screen and (max-width: 1920px) {
  .el-aside {
    width: 220px !important;
  }
  
  .el-main {
    padding: 18px;
  }
}

@media screen and (max-width: 1600px) {
  .el-aside {
    width: 200px !important;
  }
  
  .el-main {
    padding: 16px;
  }
  
  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 13px;
    }
  }
}

@media screen and (max-width: 1440px) {
  .el-aside {
    width: 180px !important;
  }
  
  .el-main {
    padding: 14px;
  }
  
  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 13px;
    }
  }
}

@media screen and (max-width: 1366px) {
  .el-aside {
    width: 180px !important;
  }
  
  .el-main {
    padding: 12px;
  }
  
  .el-header {
    height: 56px !important;
  }
  
  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 12px;
    }
  }
}

@media screen and (max-width: 1280px) {
  .el-aside {
    width: 160px !important;
  }
  
  .el-main {
    padding: 12px;
  }
  
  .el-header {
    height: 56px !important;
    
    .header-content {
      padding: 0 15px;
    }
  }
  
  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 12px;
      padding-left: 15px !important;
    }
  }
}

@media screen and (max-width: 1024px) {
  .el-aside {
    width: 140px !important;
  }
  
  .el-main {
    padding: 10px;
  }
  
  .el-header {
    height: 52px !important;
    
    .header-content {
      padding: 0 12px;
    }
  }
  
  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 12px;
    }
  }
  
  .user-info .username {
    display: none;
  }
}

@media screen and (max-width: 768px) {
  .el-aside {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    width: 240px !important;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    
    &.mobile-open {
      transform: translateX(0);
    }
  }
  
  .el-main {
    padding: 8px;
  }
  
  .el-header {
    height: 50px !important;
    
    .header-content {
      padding: 0 10px;
    }
    
    .header-left {
      :deep(.el-breadcrumb__item) {
        &:not(:last-child) {
          display: none;
        }
      }
    }
  }
}

@media screen and (max-width: 480px) {
  .el-aside {
    width: 220px !important;
  }
  
  .el-main {
    padding: 6px;
  }
  
  .el-header {
    height: 48px !important;
    
    .header-content {
      padding: 0 8px;
    }
  }
  
  .user-info {
    .el-avatar {
      width: 28px !important;
      height: 28px !important;
    }
  }
}
</style>