<template>
  <div class="home-container">
    <!-- 顶部用户信息 -->
    <div class="header-bar">
      <div class="user-dropdown">
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info">
            <template v-if="!isLoggingOut">
              <el-avatar
                :size="40"
                :src="userAvatar"
                class="user-avatar"
              >
                {{ userInitials }}
              </el-avatar>
              <span class="username">{{ userName }}</span>
              <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
            </template>
            <template v-else>
              <div class="logout-placeholder"></div>
            </template>
          </div>
          <template #dropdown>
            <el-dropdown-menu class="user-dropdown-menu">
              <el-dropdown-item command="logout">
                <el-icon><SwitchButton /></el-icon>
                <span>退出登录</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="content-wrapper">
      <div class="title-section" :class="{ 'title-animate': titleAnimated }">
        <h1 class="main-title">
          <span class="title-text">{{ $t('home.title') }}</span>
        </h1>
        <div class="title-divider">
          <div class="divider-line"></div>
          <div class="divider-dot"></div>
          <div class="divider-line"></div>
        </div>
        <p class="subtitle">{{ $t('home.subtitle') }}</p>
      </div>

      <div class="cards-container">
        <!-- AI智能用例 -->
        <div class="nav-card" :class="{ 'card-animate': pageLoaded, 'card-delay-1': true }" @click="handleNavigate('ai')" role="button" tabindex="0">
          <div class="card-shine"></div>
          <div class="card-icon ai-icon">
            <Wand2 :size="32" stroke-width="1.5" />
          </div>
          <h3>{{ $t('home.aiCase') }}</h3>
          <p>{{ $t('home.aiCaseDesc') }}</p>
        </div>

        <!-- AI智能测试 -->
        <div class="nav-card" :class="{ 'card-animate': pageLoaded, 'card-delay-2': true }" @click="handleNavigate('ai-intelligent')" role="button" tabindex="0">
          <div class="card-shine"></div>
          <div class="card-icon ai-intelligent-icon">
            <Brain :size="32" stroke-width="1.5" />
          </div>
          <h3>{{ $t('home.aiIntelligent') }}</h3>
          <p>{{ $t('home.aiIntelligentDesc') }}</p>
        </div>

        <!-- 接口测试 -->
        <div class="nav-card" :class="{ 'card-animate': pageLoaded, 'card-delay-3': true }" @click="handleNavigate('api')" role="button" tabindex="0">
          <div class="card-shine"></div>
          <div class="card-icon api-icon">
            <Share2 :size="32" stroke-width="1.5" />
          </div>
          <h3>{{ $t('home.apiTesting') }}</h3>
          <p>{{ $t('home.apiTestingDesc') }}</p>
        </div>

        <!-- Web自动化 -->
        <div class="nav-card" :class="{ 'card-animate': pageLoaded, 'card-delay-4': true }" @click="handleNavigate('ui')" role="button" tabindex="0">
          <div class="card-shine"></div>
          <div class="card-icon ui-icon">
            <Globe :size="32" stroke-width="1.5" />
          </div>
          <h3>Web自动化</h3>
          <p>可视化的Web UI自动化测试</p>
        </div>

        <!-- 配置中心 -->
        <div class="nav-card" :class="{ 'card-animate': pageLoaded, 'card-delay-5': true }" @click="handleNavigate('config')" role="button" tabindex="0">
          <div class="card-shine"></div>
          <div class="card-icon config-icon">
            <SlidersHorizontal :size="32" stroke-width="1.5" />
          </div>
          <h3>{{ $t('home.configCenter') }}</h3>
          <p>{{ $t('home.configCenterDesc') }}</p>
        </div>

        <!-- AI知识库 -->
        <div class="nav-card" :class="{ 'card-animate': pageLoaded, 'card-delay-6': true }" @click="handleNavigate('assistant')" role="button" tabindex="0">
          <div class="card-shine"></div>
          <div class="card-icon assistant-icon">
            <MessagesSquare :size="32" stroke-width="1.5" />
          </div>
          <h3>{{ $t('home.aiKnowledgeBase') }}</h3>
          <p>{{ $t('home.aiKnowledgeBaseDesc') }}</p>
        </div>

        <!-- 数据工具箱 -->
        <div class="nav-card" :class="{ 'card-animate': pageLoaded, 'card-delay-7': true }" @click="handleNavigate('data')" role="button" tabindex="0">
          <div class="card-shine"></div>
          <div class="card-icon data-icon">
            <BarChart3 :size="32" stroke-width="1.5" />
          </div>
          <h3>{{ $t('home.dataFactory') }}</h3>
          <p>{{ $t('home.dataFactoryDesc') }}</p>
        </div>

        <!-- APP自动化 -->
        <div class="nav-card" :class="{ 'card-animate': pageLoaded, 'card-delay-8': true }" @click="handleNavigate('app')" role="button" tabindex="0">
          <div class="card-shine"></div>
          <div class="card-icon app-icon">
            <Smartphone :size="32" stroke-width="1.5" />
          </div>
          <h3>APP自动化</h3>
          <p>可视化的Android App自动化测试</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { 
  Wand2, 
  Brain, 
  BarChart3, 
  SlidersHorizontal, 
  MessagesSquare, 
  Globe, 
  Smartphone, 
  Share2 
} from 'lucide-vue-next'

const router = useRouter()
const { t } = useI18n()
const appStore = useAppStore()
const userStore = useUserStore()

// 退出登录中标志，用于隐藏头像避免闪烁默认图
const isLoggingOut = ref(false)

// 页面动画控制
const pageLoaded = ref(false)
const titleAnimated = ref(false)

onMounted(() => {
  // 触发页面加载动画
  setTimeout(() => {
    pageLoaded.value = true
  }, 100)
  // 标题动画
  setTimeout(() => {
    titleAnimated.value = true
  }, 200)
})

// 用户信息
const userName = computed(() => {
  return userStore.user?.username || userStore.user?.first_name || '用户'
})

const userAvatar = computed(() => {
  // 退出登录过程中不显示头像
  if (isLoggingOut.value) {
    return ''
  }
  return userStore.user?.avatar || ''
})

const userInitials = computed(() => {
  const name = userStore.user?.username || userStore.user?.first_name || 'U'
  return name.charAt(0).toUpperCase()
})

// 下拉菜单命令处理
const handleCommand = (command) => {
  switch (command) {
    case 'profile':
      // 可以跳转到个人中心页面
      ElMessage.info('个人中心功能开发中')
      break
    case 'logout':
      handleLogout()
      break
  }
}

// 退出登录
const handleLogout = async () => {
  // 设置退出登录标志，避免头像闪烁默认图
  isLoggingOut.value = true
  await userStore.logout()
}

const handleNavigate = (type) => {
  const routes = {
    'ai': '/ai-generation/requirement-analysis',
    'api': '/api-testing/dashboard',
    'ui': '/ui-automation/dashboard',
    'app': '/app-automation/dashboard',
    'ai-intelligent': '/ai-intelligent-mode/testing',
    'assistant': '/ai-assistant/chat',
    'config': '/configuration/ai-model',
    'data': '/data-factory/by-scenario'
  }

  if (routes[type]) {
    router.push(routes[type])
  }
}
</script>

<style scoped lang="scss">
.home-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%);
  background-size: 400% 400%;
  display: flex;
  flex-direction: column;
  padding: 20px 40px 40px;
  position: relative;
  animation: gradientBreathe 12s ease infinite;
}

// 背景呼吸渐变动画
@keyframes gradientBreathe {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

// 顶部栏
.header-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 20px;
  padding: 0 20px;
}

// 用户下拉菜单
.user-dropdown {
  .user-info {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 12px;
    border-radius: 24px;
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    .user-avatar {
      border: 2px solid rgba(255, 255, 255, 0.8);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .username {
      font-size: 14px;
      font-weight: 500;
      color: #374151;
      transition: color 0.3s ease;
    }

    .dropdown-arrow {
      font-size: 12px;
      color: #6b7280;
      transition: transform 0.3s ease, color 0.3s ease;
    }

    .logout-placeholder {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: linear-gradient(135deg, rgba(123, 66, 246, 0.2) 0%, rgba(139, 92, 246, 0.1) 100%);
    }

    &:hover {
      .username {
        color: #111827;
      }
      .dropdown-arrow {
        color: #4b5563;
        transform: rotate(180deg);
      }
    }
  }
}

// 下拉菜单样式
:deep(.user-dropdown-menu) {
  border-radius: 12px;
  padding: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.95);

  // 覆盖所有子元素的默认蓝色
  * {
    color: inherit !important;
  }

  .el-dropdown-menu__item {
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: all 0.2s ease;
    color: #374151 !important;

    &.el-dropdown-menu__item--active,
    &:focus,
    &:hover,
    &:active {
      background: rgba(139, 92, 246, 0.1) !important;
      color: #7c3aed !important;
    }

    // 覆盖所有可能的颜色状态
    &:not(.is-disabled) {
      color: #374151 !important;
    }

    &:not(.is-disabled):hover,
    &:not(.is-disabled):focus,
    &:not(.is-disabled):active,
    &:not(.is-disabled).el-dropdown-menu__item--active {
      background: rgba(139, 92, 246, 0.1) !important;
      color: #7c3aed !important;
    }

    .el-icon {
      font-size: 16px;
      color: #6b7280 !important;
      transition: color 0.2s ease;
    }

    &:hover .el-icon,
    &:focus .el-icon,
    &:active .el-icon,
    &.el-dropdown-menu__item--active .el-icon {
      color: #7c3aed !important;
    }

    &.is-disabled {
      color: #9ca3af !important;
    }

    // 强制覆盖链接样式
    a,
    a:link,
    a:visited,
    a:hover,
    a:active {
      color: inherit !important;
      text-decoration: none !important;
    }

    // 覆盖 span 标签
    span {
      color: inherit !important;
    }
  }

  .el-dropdown-menu__item--divided {
    border-top: 1px solid rgba(0, 0, 0, 0.06);
    margin: 6px 0;
    padding-top: 6px;
  }
}

// 额外的全局覆盖，确保完全覆盖
:deep(.el-dropdown-menu__item) {
  &:not(.is-disabled) {
    color: #374151 !important;
  }
  
  &:hover,
  &:focus,
  &:active,
  &.el-dropdown-menu__item--active {
    color: #7c3aed !important;
    background: rgba(139, 92, 246, 0.1) !important;
  }
}

.content-wrapper {
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  text-align: center;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.title-section {
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);

  &.title-animate {
    opacity: 1;
    transform: translateY(0);
  }
}

.main-title {
  font-size: 68px;
  font-weight: 800;
  color: #2c3e50;
  margin-bottom: 20px;
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  letter-spacing: -1px;

  .title-text {
    display: inline-block;
    background: linear-gradient(135deg, #1a2a3a 0%, #4a6fa5 50%, #667eea 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    background-size: 200% auto;
    animation: titleGradient 4s ease infinite;
  }
}

@keyframes titleGradient {
  0% { background-position: 0% center; }
  50% { background-position: 100% center; }
  100% { background-position: 0% center; }
}

// 标题分割线
.title-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 24px;
  opacity: 0;
  transform: scaleX(0);
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) 0.3s;

  .title-animate & {
    opacity: 1;
    transform: scaleX(1);
  }
}

.divider-line {
  width: 120px;
  height: 3px;
  background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.6), transparent);
  border-radius: 2px;
}

.divider-dot {
  width: 8px;
  height: 8px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 50%;
  box-shadow: 0 0 12px rgba(102, 126, 234, 0.5);
  animation: dotPulse 2s ease infinite;
}

@keyframes dotPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.8; }
}

.subtitle {
  font-size: 20px;
  color: #5a6c7d;
  margin-bottom: 50px;
  font-weight: 400;
  letter-spacing: 0.5px;
  opacity: 0;
  transform: translateY(15px);
  transition: all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) 0.45s;

  .title-animate & {
    opacity: 1;
    transform: translateY(0);
  }
}

.cards-container {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  padding: 0 20px;
}

.nav-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 32px 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
  opacity: 0;
  transform: translateY(40px) scale(0.95);

  // 卡片入场动画
  &.card-animate {
    animation: cardSlideUp 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  }

  // 依次延迟
  &.card-delay-1.card-animate { animation-delay: 0.1s; }
  &.card-delay-2.card-animate { animation-delay: 0.18s; }
  &.card-delay-3.card-animate { animation-delay: 0.26s; }
  &.card-delay-4.card-animate { animation-delay: 0.34s; }
  &.card-delay-5.card-animate { animation-delay: 0.42s; }
  &.card-delay-6.card-animate { animation-delay: 0.5s; }
  &.card-delay-7.card-animate { animation-delay: 0.58s; }
  &.card-delay-8.card-animate { animation-delay: 0.66s; }

  @keyframes cardSlideUp {
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  // 光泽扫过效果
  .card-shine {
    position: absolute;
    top: 0;
    left: -100%;
    width: 50%;
    height: 100%;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(255, 255, 255, 0.4),
      transparent
    );
    transform: skewX(-25deg);
    transition: none;
    pointer-events: none;
  }

  &:hover {
    transform: translateY(-8px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
    background: rgba(255, 255, 255, 1);

    .card-shine {
      animation: shineSweep 0.8s ease forwards;
    }
  }

  &:active {
    transform: translateY(-4px);
  }

  @keyframes shineSweep {
    from {
      left: -100%;
    }
    to {
      left: 150%;
    }
  }

  .card-icon {
    width: 72px;
    height: 72px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 20px;
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    background-size: 200% 200%;
    position: relative;
    overflow: hidden;

    svg {
      width: 32px;
      height: 32px;
    }

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: linear-gradient(
        135deg,
        rgba(255, 255, 255, 0.3) 0%,
        transparent 50%,
        rgba(255, 255, 255, 0.1) 100%
      );
      pointer-events: none;
    }

    &.ai-icon {
      background: linear-gradient(-45deg, #667eea, #764ba2, #8b5cf6, #667eea);
      background-size: 300% 300%;
      animation: gradientFlow 4s ease infinite;
      color: white;
    }

    &.api-icon {
      background: linear-gradient(-45deg, #f093fb, #f5576c, #ff6b9d, #f093fb);
      background-size: 300% 300%;
      animation: gradientFlow 4.5s ease infinite;
      color: white;
    }

    &.ui-icon {
      background: linear-gradient(-45deg, #4facfe, #00f2fe, #00c9ff, #4facfe);
      background-size: 300% 300%;
      animation: gradientFlow 5s ease infinite;
      color: white;
    }

    &.data-icon {
      background: linear-gradient(-45deg, #43e97b, #38f9d7, #00e5ff, #43e97b);
      background-size: 300% 300%;
      animation: gradientFlow 4.2s ease infinite;
      color: white;
    }

    &.app-icon {
      background: linear-gradient(-45deg, #fa709a, #fee140, #ff8a65, #fa709a);
      background-size: 300% 300%;
      animation: gradientFlow 4.8s ease infinite;
      color: white;
    }

    &.ai-intelligent-icon {
      background: linear-gradient(-45deg, #a8edea, #fed6e3, #d299c2, #a8edea);
      background-size: 300% 300%;
      animation: gradientFlow 5.2s ease infinite;
      color: #4a5568;
    }

    &.assistant-icon {
      background: linear-gradient(-45deg, #ffecd2, #fcb69f, #ffecd2, #ff9a9e);
      background-size: 300% 300%;
      animation: gradientFlow 4.6s ease infinite;
      color: #4a5568;
    }

    &.config-icon {
      background: linear-gradient(-45deg, #d299c2, #fef9d7, #a8edea, #d299c2);
      background-size: 300% 300%;
      animation: gradientFlow 5.5s ease infinite;
      color: #4a5568;
    }
  }

  @keyframes gradientFlow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }

  &:hover .card-icon {
    transform: scale(1.15) rotate(5deg);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2);
  }

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 10px;
    transition: color 0.3s ease;
  }

  &:hover h3 {
    color: #667eea;
  }

  p {
    font-size: 14px;
    color: #5a6c7d;
    line-height: 1.5;
    margin: 0;
  }
}

@media (max-width: 1200px) {
  .cards-container {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 900px) {
  .cards-container {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .home-container {
    padding: 16px 20px 40px;
  }

  .header-bar {
    padding: 0;
    margin-bottom: 16px;
  }

  .user-dropdown .user-info {
    padding: 4px 10px;
    gap: 6px;

    .username {
      font-size: 13px;
    }
  }

  .cards-container {
    grid-template-columns: 1fr;
    padding: 0;
  }

  .main-title {
    font-size: 36px;
  }
}
</style>
