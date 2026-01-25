<template>
  <div class="layout">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="240px">
        <div class="logo" @click="router.push('/home')" style="cursor: pointer;">
          <h2>TestHub</h2>
        </div>
        <el-menu
          :default-active="$route.path"
          router
          text-color="#fff"
          active-text-color="#fff"
        >
          <!-- AI用例生成模块菜单 -->
          <template v-if="currentModule === 'ai-generation'">
            <el-sub-menu index="requirement">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>智能用例</span>
              </template>
              <el-menu-item index="/ai-generation/requirement-analysis">AI用例生成</el-menu-item>
              <el-menu-item index="/ai-generation/generated-testcases">AI用例记录</el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/ai-generation/projects">
              <el-icon><Folder /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/testcases">
              <el-icon><Document /></el-icon>
              <span>测试用例</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/versions">
              <el-icon><Flag /></el-icon>
              <span>版本管理</span>
            </el-menu-item>
            <el-sub-menu index="reviews">
              <template #title>
                <el-icon><Check /></el-icon>
                <span>评审管理</span>
              </template>
              <el-menu-item index="/ai-generation/reviews">评审列表</el-menu-item>
              <el-menu-item index="/ai-generation/review-templates">评审模板</el-menu-item>
            </el-sub-menu>

            <el-menu-item index="/ai-generation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>测试计划</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>测试报告</span>
            </el-menu-item>
          </template>

          <!-- 接口测试模块菜单 -->
          <template v-else-if="currentModule === 'api-testing'">
            <el-menu-item index="/api-testing/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/projects">
              <el-icon><Folder /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/interfaces">
              <el-icon><Link /></el-icon>
              <span>接口管理</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/automation">
              <el-icon><VideoPlay /></el-icon>
              <span>自动化测试</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/history">
              <el-icon><Timer /></el-icon>
              <span>请求历史</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/environments">
              <el-icon><Setting /></el-icon>
              <span>环境管理</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>测试报告</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>定时任务</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>通知列表</span>
            </el-menu-item>
          </template>

          <!-- UI自动化测试模块菜单 -->
          <template v-else-if="currentModule === 'ui-automation'">
            <el-menu-item index="/ui-automation/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/projects">
              <el-icon><Folder /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/elements-enhanced">
              <el-icon><Aim /></el-icon>
              <span>元素管理</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/test-cases">
              <el-icon><Document /></el-icon>
              <span>用例管理</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts-enhanced">
              <el-icon><Edit /></el-icon>
              <span>脚本生成</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts">
              <el-icon><DocumentCopy /></el-icon>
              <span>脚本列表</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/suites">
              <el-icon><Collection /></el-icon>
              <span>套件管理</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>执行记录</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>测试报告</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>定时任务</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>通知列表</span>
            </el-menu-item>
          </template>

          <!-- AI 智能模式模块菜单 -->
          <template v-else-if="currentModule === 'ai-intelligent-mode'">
            <el-menu-item index="/ai-intelligent-mode/testing">
              <el-icon><VideoPlay /></el-icon>
              <span>AI 智能测试</span>
            </el-menu-item>
            <el-menu-item index="/ai-intelligent-mode/cases">
              <el-icon><Document /></el-icon>
              <span>AI 用例管理</span>
            </el-menu-item>
            <el-menu-item index="/ai-intelligent-mode/execution-records">
              <el-icon><Timer /></el-icon>
              <span>AI 测试报告</span>
            </el-menu-item>

          </template>

          <!-- 配置中心模块菜单 -->
          <template v-else-if="currentModule === 'configuration'">
            <el-sub-menu index="ai-case-generation">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>AI用例配置</span>
              </template>
              <el-menu-item index="/configuration/ai-model">
                <el-icon><Cpu /></el-icon>
                <span>用例模型配置</span>
              </el-menu-item>
              <el-menu-item index="/configuration/prompt-config">
                <el-icon><Edit /></el-icon>
                <span>提示词配置</span>
              </el-menu-item>
              <el-menu-item index="/configuration/generation-config">
                <el-icon><Setting /></el-icon>
                <span>生成行为配置</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/configuration/ui-env">
              <el-icon><Monitor /></el-icon>
              <span>UI环境配置</span>
            </el-menu-item>
            <el-menu-item index="/configuration/ai-mode">
              <el-icon><MagicStick /></el-icon>
              <span>AI智能模式配置</span>
            </el-menu-item>
            <el-menu-item index="/configuration/scheduled-task">
              <el-icon><Timer /></el-icon>
              <span>定时任务配置</span>
            </el-menu-item>
            <el-menu-item index="/configuration/dify">
              <el-icon><ChatDotRound /></el-icon>
              <span>AI评测师配置</span>
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
                <el-breadcrumb-item :to="{ path: '/home' }">首页</el-breadcrumb-item>
                <el-breadcrumb-item v-if="moduleName">{{ moduleName }}</el-breadcrumb-item>
                <el-breadcrumb-item>{{ breadcrumbTitle }}</el-breadcrumb-item>
              </el-breadcrumb>
            </div>
            <div class="header-right">
              <el-dropdown @command="handleCommand" class="user-dropdown">
                <span class="user-info">
                  <el-avatar :size="32" :src="userStore.user?.avatar || ''" />
                  <span class="username">{{ userStore.user?.username }}</span>
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="profile">个人设置</el-dropdown-item>
                    <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
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
import { ElMessage } from 'element-plus'
import { 
  Monitor, Folder, Document, Flag, Check, Collection, VideoPlay, 
  DataAnalysis, ChatDotRound, DocumentCopy, Link, MagicStick,
  Odometer, Timer, Setting, AlarmClock, Bell, Aim, Edit, Cpu
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

onMounted(async () => {
  console.log('Layout 初始化用户信息...')
  await userStore.initAuth()
  console.log('Layout 用户信息初始化完成:', userStore.user)
  console.log('Layout 用户头像:', userStore.user?.avatar)
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
    'ai-generation': 'AI用例生成',
    'api-testing': '接口测试',
    'ui-automation': 'UI自动化测试',
    'ai-intelligent-mode': 'AI 智能模式',
    'configuration': '配置中心'
  }
  return map[currentModule.value] || ''
})

const breadcrumbTitle = computed(() => {
  const routeMap = {
    // AI用例生成
    '/ai-generation/requirement-analysis': 'AI用例生成',
    '/ai-generation/generated-testcases': 'AI生成用例记录',
    '/ai-generation/prompt-config': '提示词配置',
    '/ai-generation/projects': '项目管理',
    '/ai-generation/testcases': '测试用例',
    '/ai-generation/versions': '版本管理',
    '/ai-generation/reviews': '评审列表',
    '/ai-generation/review-templates': '评审模板',
    '/ai-generation/testsuites': '测试套件',
    '/ai-generation/executions': '执行记录',
    '/ai-generation/reports': '测试报告',
    
    // 接口测试
    '/api-testing/dashboard': '数据看板',
    '/api-testing/projects': '项目管理',
    '/api-testing/interfaces': '接口管理',
    '/api-testing/automation': '自动化测试',
    '/api-testing/history': '请求历史',
    '/api-testing/environments': '环境管理',
    '/api-testing/reports': '测试报告',
    '/api-testing/scheduled-tasks': '定时任务',
    '/api-testing/notification-logs': '通知列表',
    
    // UI自动化测试
    '/ui-automation/dashboard': '数据看板',
    '/ui-automation/projects': '项目管理',
    '/ui-automation/elements-enhanced': '元素管理',
    '/ui-automation/test-cases': '用例管理',
    '/ui-automation/scripts-enhanced': '脚本生成',
    '/ui-automation/scripts': '脚本列表',
    '/ui-automation/suites': '套件管理',
    '/ui-automation/executions': '执行记录',
    '/ui-automation/reports': '测试报告',
    '/ui-automation/scheduled-tasks': '定时任务',
    '/ui-automation/notification-logs': '通知列表',
    
    // AI 智能模式
    '/ai-intelligent-mode/testing': 'AI 智能测试',
    '/ai-intelligent-mode/cases': 'AI 用例管理',
    '/ai-intelligent-mode/execution-records': 'AI 测试报告',

    
    // 配置中心
    '/configuration/ai-model': '用例模型配置',
    '/configuration/prompt-config': '提示词配置',
    '/configuration/generation-config': '生成行为配置',
    '/configuration/ui-env': 'UI环境配置',
    '/configuration/ai-mode': 'AI智能模式配置',
    '/configuration/scheduled-task': '定时任务配置',
    '/configuration/dify': 'AI评测师配置',
    
    '/profile': '个人设置'
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
  
  /* 确保箭头右对齐 */
  :deep(.el-sub-menu__title) {
    position: relative;
  }
  
  :deep(.el-sub-menu__title .el-sub-menu__icon-arrow) {
    position: absolute;
    right: 16px;
  }
  
  :deep(.el-menu-item) {
    background: rgba(243, 240, 250, 0.8) !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(90, 50, 163, 0.05) !important;
    backdrop-filter: blur(10px) !important;
  }
  
  :deep(.el-sub-menu__title) {
    background: rgba(243, 240, 250, 0.8) !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(90, 50, 163, 0.05) !important;
    backdrop-filter: blur(10px) !important;
  }
  
  :deep(.el-menu-item.is-active) {
    background: rgba(90, 50, 163, 0.9) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-right: none !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.3) !important;
    backdrop-filter: blur(10px) !important;
  }
  
  :deep(.el-sub-menu__title.is-active) {
    background: rgba(90, 50, 163, 0.9) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-right: none !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.3) !important;
    backdrop-filter: blur(10px) !important;
  }
  
  :deep(.el-menu-item:hover) {
    background: rgba(225, 215, 240, 0.9) !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.1) !important;
    backdrop-filter: blur(10px) !important;
  }
  
  :deep(.el-sub-menu__title:hover) {
    background: rgba(225, 215, 240, 0.9) !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.1) !important;
    backdrop-filter: blur(10px) !important;
  }
  
  :deep(.el-menu-item.is-active:hover) {
    background: rgba(74, 20, 140, 0.9) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-right: none !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 6px 16px rgba(74, 20, 140, 0.4) !important;
    backdrop-filter: blur(10px) !important;
  }
  
  :deep(.el-sub-menu__title.is-active:hover) {
    background: rgba(74, 20, 140, 0.9) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-right: none !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 6px 16px rgba(74, 20, 140, 0.4) !important;
    backdrop-filter: blur(10px) !important;
  }
  
  /* 子菜单样式 - 统一背景 */
  :deep(.el-sub-menu__content) {
    background: #f3f0fa !important;
    border-left: none !important;
    padding-left: 32px !important;
    max-height: none !important;
    overflow: visible !important;
    transition: all 0.3s ease !important;
    margin: 0 !important;
    padding: 0 !important;
    box-shadow: none !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 智能用例生成子菜单特殊处理 */
  :deep(.el-menu-item-group) {
    background: #f3f0fa !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  :deep(.el-menu-item-group__title) {
    background: #f3f0fa !important;
    color: #5a32a3 !important;
    margin: 0 !important;
    padding: 0 !important;
    font-size: 12px !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 子菜单项样式 - 统一文字颜色 */
  :deep(.el-sub-menu__content .el-menu-item) {
    background: rgba(243, 240, 250, 0.8) !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    margin: 4px 12px !important;
    padding: 10px 16px !important;
    transition: all 0.3s ease !important;
    border-radius: 6px !important;
    box-shadow: 0 2px 6px rgba(90, 50, 163, 0.05) !important;
    backdrop-filter: blur(10px) !important;
    width: calc(100% - 24px) !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 子菜单项hover和激活状态 */
  :deep(.el-sub-menu__content .el-menu-item:hover) {
    background: rgba(225, 215, 240, 0.9) !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 3px 10px rgba(90, 50, 163, 0.1) !important;
    padding: 10px 16px !important;
    margin: 4px 12px !important;
    border-radius: 6px !important;
    backdrop-filter: blur(10px) !important;
    width: calc(100% - 24px) !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 子菜单项激活状态 - 高亮 */
  :deep(.el-sub-menu__content .el-menu-item.is-active) {
    background: rgba(90, 50, 163, 0.9) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding: 10px 16px !important;
    margin: 4px 12px !important;
    border-radius: 6px !important;
    box-shadow: 0 3px 10px rgba(90, 50, 163, 0.3) !important;
    backdrop-filter: blur(10px) !important;
    width: calc(100% - 24px) !important;
    border-right: none !important;
    border-bottom: none !important;
  }
  
  /* 子菜单项激活+hover状态 */
  :deep(.el-sub-menu__content .el-menu-item.is-active:hover) {
    background: rgba(74, 20, 140, 0.9) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding: 10px 16px !important;
    margin: 4px 12px !important;
    border-radius: 6px !important;
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
  }
  
  :deep(.el-sub-menu__title span),
  :deep(.el-menu-item span) {
    display: none;
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
      
      &:hover {
        border-color: #9370db;
        box-shadow: 0 0 0 2px rgba(147, 112, 219, 0.2);
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
  
  .logo h2 {
    font-size: 19px;
  }
}

@media screen and (max-width: 1600px) {
  .el-aside {
    width: 200px !important;
  }
  
  .el-main {
    padding: 16px;
  }
  
  .logo h2 {
    font-size: 18px;
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
  
  .logo h2 {
    font-size: 17px;
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
  
  .logo h2 {
    font-size: 16px;
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
  
  .logo h2 {
    font-size: 15px;
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
  
  .logo h2 {
    font-size: 14px;
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
  
  .logo h2 {
    font-size: 16px;
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
  
  .logo h2 {
    font-size: 15px;
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