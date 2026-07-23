<template>
  <div class="app-automation-container">
    <!-- 子路由内容显示区域 -->
    <router-view></router-view>
  </div>
</template>

<script setup>
</script>

<style scoped>
.app-automation-container {
  padding: 0;
  height: 100%;
  overflow-y: auto;
  min-height: calc(100vh - 60px);
  background: transparent;
}
</style>
