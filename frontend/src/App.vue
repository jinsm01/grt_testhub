<template>
  <el-config-provider :locale="elementLocale">
    <div id="app">
      <router-view />
    </div>
  </el-config-provider>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { ElConfigProvider } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'

const userStore = useUserStore()
const appStore = useAppStore()

// 根据 Element Plus 需要的 locale 配置
const elementLocale = computed(() => {
  return appStore.language === 'zh-cn' ? zhCn : en
})

onMounted(() => {
  userStore.initAuth()
})
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 
    'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  height: 100vh;
  width: 100vw;
}

/* 全局开关样式 - 紫色渐变主题 */
.el-switch.is-checked .el-switch__core {
  background: linear-gradient(135deg, #5a32a3 0%, #7b42f6 100%) !important;
  border-color: #5a32a3 !important;
}

.el-switch.is-checked .el-switch__core .el-switch__action {
  background-color: #ffffff !important;
}

/* 全局复选框样式 - 紫色渐变主题 */
.el-checkbox.is-checked .el-checkbox__inner {
  background: linear-gradient(135deg, #5a32a3 0%, #7b42f6 100%) !important;
  border-color: #5a32a3 !important;
}

.el-checkbox.is-checked .el-checkbox__inner::after {
  border-color: #ffffff !important;
}

.el-checkbox__input.is-checked + .el-checkbox__label {
  color: #5a32a3 !important;
}

/* 全局 Tab 样式 - 紫色主题 */
.el-tabs__nav {
  display: flex !important;
  justify-content: center !important;
  width: 100% !important;
}

.el-tabs__item {
  padding: 16px 48px !important;
  text-align: center !important;
}

.el-tabs__item:hover {
  color: #5a32a3 !important;
}

.el-tabs__item.is-active {
  color: #5a32a3 !important;
}

/* Tab 底部激活线 - 紫色 - 最高优先级覆盖 */
.el-tabs__active-bar,
.el-tabs--top .el-tabs__active-bar,
.el-tabs--bottom .el-tabs__active-bar {
  background-color: #5a32a3 !important;
  background: #5a32a3 !important;
}

/* 覆盖 Element Plus 默认的蓝色底部边框 */
.el-tabs__item.is-active,
.el-tabs--top .el-tabs__item.is-top.is-active,
.el-tabs--top .el-tabs__item.is-bottom.is-active {
  border-bottom-color: #5a32a3 !important;
  color: #5a32a3 !important;
}

/* 覆盖导航栏底部的默认线条 */
.el-tabs__nav-wrap::after {
  background-color: #e4e7ed !important;
  height: 1px !important;
}

/* 确保激活的底部线是紫色 */
.el-tabs__nav-wrap .el-tabs__active-bar {
  background-color: #5a32a3 !important;
  background: #5a32a3 !important;
  height: 2px !important;
}

/* 输入框聚焦样式 - 紫色主题 */
.el-input__wrapper.is-focus,
.el-input__wrapper:focus {
  box-shadow: 0 0 0 1px #5a32a3 inset !important;
}

.el-textarea__inner:focus {
  box-shadow: 0 0 0 1px #5a32a3 !important;
  border-color: #5a32a3 !important;
}
</style>