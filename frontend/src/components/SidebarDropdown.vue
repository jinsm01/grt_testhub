<template>
  <div class="el-menu-item sidebar-dropdown-wrapper">
    <el-dropdown 
      placement="right-start" 
      trigger="hover"
      :show-timeout="100"
      :hide-timeout="200"
    >
      <div class="dropdown-title-content">
        <el-icon v-if="icon">
          <component :is="icon" />
        </el-icon>
        <span>{{ title }}</span>
        <el-icon class="arrow-icon">
          <ArrowRight />
        </el-icon>
      </div>
      <template #dropdown>
        <el-dropdown-menu class="sidebar-dropdown-menu">
          <el-dropdown-item
            v-for="item in items"
            :key="item.index"
            @click="handleItemClick(item)"
          >
            {{ item.title }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'

const props = defineProps({
  title: String,
  icon: String,
  items: Array
})

const router = useRouter()

const handleItemClick = (item) => {
  if (item.index) {
    router.push(item.index)
  }
}
</script>

<style scoped lang="scss">
.sidebar-dropdown-wrapper {
  width: calc(100% - 24px) !important; /* Adjust for margins */
  display: flex;
  align-items: center;
  justify-content: flex-start;
  font-size: 14px;
  padding-left: 20px !important;
  background: #f3f0fa !important;
  color: #5a32a3 !important;
  font-weight: 500 !important;
  transition: all 0.3s ease !important;
  margin: 6px 12px !important;
  border-radius: 8px !important;
  box-shadow: 0 2px 8px rgba(90, 50, 163, 0.05) !important;
  backdrop-filter: blur(10px) !important;
  cursor: pointer;
  box-sizing: border-box !important;
  min-height: 40px !important;
  position: relative;
  outline: none;
  border-right: none !important;
  border-bottom: none !important;
  position: relative;
  
  &:focus {
    outline: none !important;
    box-shadow: 0 2px 8px rgba(90, 50, 163, 0.05) !important;
  }
  
  &:hover {
    background: #e1d7f0 !important;
    color: #5a32a3 !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding-left: 20px !important;
    margin: 6px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(90, 50, 163, 0.1) !important;
    backdrop-filter: blur(10px) !important;
  }
  
  &.is-active {
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
    
    &:focus {
      outline: none !important;
      box-shadow: 0 4px 12px rgba(90, 50, 163, 0.3) !important;
    }
  }
  
  &.is-active:hover {
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
    
    &:focus {
      outline: none !important;
      box-shadow: 0 6px 16px rgba(74, 20, 140, 0.4) !important;
    }
  }
  
  &.is-active .el-icon {
    color: #ffffff !important; /* 激活状态时图标为白色 */
  }
  
  :deep(.el-dropdown) {
    width: 100%;
    height: 100%;
    
    &:focus {
      outline: none !important;
    }
  }
  
  :deep(.el-dropdown-selfdefine) {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding: 0 !important;
    background: transparent !important;
    color: inherit !important;
    font-weight: inherit !important;
    margin: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    cursor: pointer;
    height: 100% !important;
    outline: none;
    
    &:focus {
      outline: none !important;
    }
  }
}

.dropdown-title-content {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  width: 100%;
  height: 100%;
  font-size: 14px;
  white-space: nowrap;
  outline: none;

  .el-icon {
    width: 20px;
    margin-right: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: inherit !important; /* 确保图标继承文字颜色 */
  }

  .arrow-icon {
    position: absolute;
    right: 16px;
    font-size: 12px;
    transition: transform 0.3s;
    color: inherit !important; /* 确保箭头图标继承文字颜色 */
  }
  
  &:focus {
    outline: none !important;
  }
}

.sidebar-dropdown-menu {
  background: #f3f0fa !important;
  border: 1px solid #e9ecef !important;
  border-radius: 8px !important;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important;
  min-width: 200px !important;
  padding: 4px !important;

  :deep(.el-dropdown-menu__item) {
    background: transparent !important;
    color: #5a32a3 !important;
    font-weight: 500 !important;
    margin: 2px 8px !important;
    padding: 10px 16px !important;
    border-radius: 6px !important;
    transition: all 0.3s ease !important;
    display: flex;
    align-items: center;

    &:hover {
      background: #e1d7f0 !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
      transform: translateX(2px);
    }

    &.is-active {
      background: #5a32a3 !important;
      color: #ffffff !important;
      font-weight: 600 !important;
    }
  }
}
</style>