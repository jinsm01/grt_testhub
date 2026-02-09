<template>
  <div class="ui-env-config">
    <div class="page-header">
      <h1>{{ $t('configuration.uiEnv.title') }}</h1>
      <p>{{ $t('configuration.uiEnv.description') }}</p>
    </div>

    <div class="main-content">
      <div class="check-section">
        <el-button type="primary" size="large" @click="checkEnvironment" :loading="checking">
          <el-icon><Refresh /></el-icon>
          {{ $t('configuration.uiEnv.checkEnvironment') }}
        </el-button>
        <div v-if="lastCheckTime" class="last-check">
          {{ $t('configuration.uiEnv.lastCheckTime') }}: {{ lastCheckTime }}
        </div>
      </div>

      <div v-if="environmentData" class="env-status-grid">
        <div class="os-info-card">
          <h3>{{ $t('configuration.uiEnv.operatingSystem') }}</h3>
          <div class="os-name">{{ environmentData.os }}</div>
        </div>

        <!-- 系统浏览器 (Selenium) -->
        <div class="section-title">
          <h3>{{ $t('configuration.uiEnv.systemBrowsers') }}</h3>
        </div>
        <div class="browser-cards">
          <div v-for="browser in environmentData.system_browsers" :key="browser.name" class="browser-card">
              <div class="browser-content">
                <div class="browser-icon">
                  <img :src="getBrowserIcon(browser.name)" :alt="browser.name" />
                </div>
                <div class="browser-info">
                  <h3>{{ formatBrowserName(browser.name) }}</h3>
                  <div class="status-row">
                    <el-tag :type="browser.installed ? 'success' : 'info'" effect="dark">
                      {{ browser.installed ? (browser.version || $t('configuration.uiEnv.installed')) : $t('configuration.uiEnv.notInstalled') }}
                    </el-tag>
                  </div>
                </div>
              </div>
          </div>
        </div>

        <!-- Playwright 浏览器 -->
        <div class="section-title">
          <h3>{{ $t('configuration.uiEnv.playwrightBrowsers') }}</h3>
        </div>
        <div class="browser-cards">
          <div v-for="browser in environmentData.playwright_browsers" :key="browser.name" class="browser-card">
              <div class="browser-content">
                <div class="browser-icon">
                  <img :src="getBrowserIcon(browser.name)" :alt="browser.name" />
                </div>
                <div class="browser-info">
                  <h3>{{ formatBrowserName(browser.name) }}</h3>
                  <div class="status-row">
                    <el-tag :type="browser.installed ? 'success' : 'warning'" effect="dark">
                      {{ browser.installed ? (browser.version || $t('configuration.uiEnv.installed')) : $t('configuration.uiEnv.notInstalled') }}
                    </el-tag>
                  </div>
                </div>
              </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const { t } = useI18n()

const checking = ref(false)
const installing = ref(null)
const lastCheckTime = ref('')
const environmentData = ref(null)

const getBrowserIcon = (name) => {
  const iconMap = {
    'chrome': 'https://raw.githubusercontent.com/alrra/browser-logos/main/src/chrome/chrome_48x48.png',
    'firefox': 'https://raw.githubusercontent.com/alrra/browser-logos/main/src/firefox/firefox_48x48.png',
    'safari': 'https://raw.githubusercontent.com/alrra/browser-logos/main/src/safari/safari_48x48.png',
    'edge': 'https://raw.githubusercontent.com/alrra/browser-logos/main/src/edge/edge_48x48.png',
    'chromium': 'https://raw.githubusercontent.com/alrra/browser-logos/main/src/chromium/chromium_48x48.png',
    'webkit': 'https://raw.githubusercontent.com/alrra/browser-logos/main/src/webkit/webkit_48x48.png'
  }
  return iconMap[name] || ''
}

const formatBrowserName = (name) => {
  return name.charAt(0).toUpperCase() + name.slice(1)
}

const checkEnvironment = async () => {
  checking.value = true
  try {
    const response = await api.get('/ui-automation/config/environment/check_environment/')
    environmentData.value = response.data
    lastCheckTime.value = new Date().toLocaleString()
    ElMessage.success(t('configuration.uiEnv.messages.checkSuccess'))
  } catch (error) {
    console.error('Environment check failed:', error)
    ElMessage.error(t('configuration.uiEnv.messages.checkFailed'))
  } finally {
    checking.value = false
  }
}

const installDriver = async (browserName) => {
  installing.value = browserName
  try {
    await api.post('/ui-automation/config/environment/install_driver/', { browser: browserName })
    ElMessage.success(t('configuration.uiEnv.messages.installSuccess', { browser: formatBrowserName(browserName) }))
    // Re-check environment
    await checkEnvironment()
  } catch (error) {
    console.error('Driver installation failed:', error)
    ElMessage.error(`${t('configuration.uiEnv.messages.installFailed')}: ${error.response?.data?.error || error.message}`)
  } finally {
    installing.value = null
  }
}

onMounted(() => {
  checkEnvironment()
})
</script>

<style scoped>
.ui-env-config {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
  padding: 28px 20px;
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.12);
  border: 1px solid rgba(147, 112, 219, 0.2);
}

.page-header h1 {
  font-size: 2.2rem;
  color: #5a32a3;
  margin-bottom: 12px;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(90, 50, 163, 0.1);
  line-height: 1.2;
}

.page-header p {
  color: #6d5d8f;
  font-size: 1.05rem;
  opacity: 0.9;
  margin: 0;
  line-height: 1.5;
}

.check-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 40px;
  gap: 10px;
  padding: 24px;
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.2);
}

.last-check {
  font-size: 0.9rem;
  color: #6d5d8f;
  font-style: italic;
}

.env-status-grid {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.os-info-card {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.2);
  text-align: center;
  position: relative;
  overflow: hidden;
}

.os-info-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #7b42f6 0%, #5a32a3 100%);
}

.os-info-card h3 {
  color: #5a32a3;
  font-size: 1.1rem;
  margin-bottom: 12px;
  font-weight: 600;
}

.os-name {
  font-size: 1.5rem;
  font-weight: bold;
  color: #7b42f6;
  margin-top: 10px;
}

.section-title {
  margin: 20px 0 10px;
  border-left: 4px solid #7b42f6;
  padding-left: 12px;
}

.section-title h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #5a32a3;
  font-weight: 600;
}

.browser-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.browser-card {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.2);
  transition: all 0.3s ease;
  cursor: default;
  position: relative;
  overflow: hidden;
}

.browser-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #7b42f6 0%, #5a32a3 100%);
}

.browser-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.15);
}

.browser-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.browser-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.browser-icon img {
  width: 48px;
  height: 48px;
  object-fit: contain;
}

.browser-info {
  width: 100%;
  text-align: center;
  margin-bottom: 15px;
}

.browser-info h3 {
  margin: 0 0 10px;
  color: #5a32a3;
  font-size: 1.1rem;
  font-weight: 600;
}

.status-row {
  display: flex;
  justify-content: center;
  margin-bottom: 5px;
}

.browser-actions {
  margin-top: 10px;
  width: 100%;
  display: flex;
  justify-content: center;
}
</style>
