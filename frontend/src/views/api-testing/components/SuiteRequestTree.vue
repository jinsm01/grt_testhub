<template>
  <div class="request-tree-item">
    <div
      class="request-item"
      :class="{
        'is-disabled': !request.enabled,
        'is-group': request.step_type === 'group',
        'is-dragging': isDragging
      }"
      :style="{ paddingLeft: `${currentLevel * 20 + 16}px` }"
    >
      <!-- 拖拽手柄 -->
      <div class="drag-handle">
        <el-icon><Rank /></el-icon>
      </div>

      <!-- 展开/折叠按钮 (仅group类型显示) -->
      <div v-if="request.step_type === 'group' && request.children && request.children.length > 0"
           class="expand-btn"
           @click.stop="toggleExpand">
        <el-icon v-if="isExpanded"><ArrowDown /></el-icon>
        <el-icon v-else><ArrowRight /></el-icon>
      </div>
      <div v-else class="expand-placeholder"></div>

      <div class="request-number">{{ displayNumber }}</div>

      <div class="request-content">
        <div class="request-header">
          <div class="request-type-badge" :class="request.step_type || 'request'">
            {{ getTypeText(request.step_type) }}
          </div>
          <span class="request-name">{{ request.override_name || request.request?.name || request.name || '未命名' }}</span>
          <span v-if="request.children && request.children.length > 0" class="child-count">
            {{ request.children.length }} 个子项
          </span>
        </div>

        <div class="request-detail" v-if="request.step_type !== 'group' && request.request">
          <span class="method" :class="getMethodClass(request.override_method || request.request.method)">
            {{ request.override_method || request.request.method }}
          </span>
          <span class="url">{{ request.override_url || request.request.url }}</span>
        </div>
        
        <!-- 等待时间步骤详情 -->
        <div class="request-detail wait-detail" v-else-if="request.step_type === 'wait'">
          <el-icon><Timer /></el-icon>
          <span>等待 {{ request.control_config?.wait_time || 1 }} 秒</span>
        </div>
      </div>

      <div class="request-meta">
        <span class="assertion-count" v-if="request.assertions?.length > 0">
          <el-icon><Check /></el-icon>
          {{ request.assertions.length }} 个断言
        </span>
      </div>

      <div class="request-actions">
        <el-switch
          v-model="request.enabled"
          @change="$emit('toggleEnabled', request)"
          size="small"
          class="enable-switch"
        />
        <el-button
          size="small"
          class="action-btn edit-btn"
          @click="$emit('edit', request)"
        >
          <el-icon><Edit /></el-icon>
        </el-button>
        <el-button
          size="small"
          class="action-btn remove-btn"
          @click="$emit('remove', request)"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 递归渲染子请求 - 使用 draggable 支持拖拽 -->
    <div v-if="isExpanded && localChildren.length > 0" class="request-children">
      <draggable
        v-model="localChildren"
        :group="{ name: 'suite-requests', pull: true, put: true }"
        :animation="200"
        :disabled="false"
        item-key="id"
        ghost-class="dragging-ghost"
        chosen-class="dragging-chosen"
        drag-class="dragging-drag"
        @change="onChildChange"
      >
        <template #item="{ element, index }">
          <suite-request-tree
            :request="element"
            :index="index"
            :level="Number(level) + 1"
            :parent-number="displayNumber"
            :parent-request="request"
            @edit="$emit('edit', $event)"
            @remove="$emit('remove', $event)"
            @toggle-enabled="$emit('toggleEnabled', $event)"
            @order-change="handleChildOrderChange"
          />
        </template>
      </draggable>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ArrowRight, ArrowDown, Edit, Delete, Check, Rank, Timer } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'

const props = defineProps({
  request: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    default: 0
  },
  level: {
    type: [Number, String],
    default: 0
  },
  parentNumber: {
    type: [String, Number],
    default: null
  },
  parentRequest: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['edit', 'remove', 'toggleEnabled', 'orderChange'])

const isExpanded = ref(true)
const isDragging = ref(false)

// 本地子节点数据，用于拖拽
const localChildren = ref(props.request.children || [])

// 监听父组件传入的 children 变化
watch(() => props.request.children, (newChildren) => {
  localChildren.value = newChildren || []
}, { deep: true })

const currentLevel = computed(() => Number(props.level))

const displayNumber = computed(() => {
  if (props.parentNumber) {
    return `${props.parentNumber}.${props.index + 1}`
  }
  return String(props.index + 1)
})

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

const onChildDragStart = () => {
  isDragging.value = true
}

const onChildChange = (evt) => {
  console.log('子节点拖拽变化:', evt)

  // 处理同层级移动
  if (evt.moved) {
    isDragging.value = false
    // 通知父组件更新顺序
    emit('orderChange', {
      parentId: props.request.id,
      children: localChildren.value
    })
  }

  // 处理从其他层级添加
  if (evt.added) {
    const { newIndex, element } = evt.added
    console.log('元素被添加到当前分组:', { newIndex, element })

    // 更新元素的 parent_id
    const updatedElement = localChildren.value[newIndex]
    if (updatedElement) {
      updatedElement.parent_id = props.request.id
    }

    // 通知父组件更新
    emit('orderChange', {
      parentId: props.request.id,
      children: localChildren.value,
      movedElement: element
    })
  }

  // 处理移除（拖拽到其他层级）
  if (evt.removed) {
    console.log('元素从当前分组移除:', evt.removed)
    // 不需要特殊处理，因为目标层级会触发 added 事件
  }
}

const handleChildOrderChange = (data) => {
  // 向上传递子节点的顺序变化
  emit('orderChange', data)
}

const getTypeText = (type) => {
  const typeMap = {
    'request': '接口',
    'group': '分组',
    'wait': '等待',
    'script': '脚本',
    'condition': '条件',
    'loop': '循环',
    'scenario_ref': '引用'
  }
  return typeMap[type] || '接口'
}

const getMethodClass = (method) => {
  if (!method) return ''
  const methodClasses = {
    'GET': 'method-get',
    'POST': 'method-post',
    'PUT': 'method-put',
    'DELETE': 'method-delete',
    'PATCH': 'method-patch'
  }
  return methodClasses[method.toUpperCase()] || ''
}
</script>

<style scoped>
.request-tree-item {
  width: 100%;
}

.request-item {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  background: #ffffff;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.request-item:hover {
  background-color: #fafafa;
}

.request-item.is-disabled {
  opacity: 0.6;
  background-color: #f8f9fa;
}

.request-item.is-disabled .request-name,
.request-item.is-disabled .url {
  text-decoration: line-through;
  color: #bfbfbf;
}

.request-item.is-group {
  background: #f8f6ff;
  border-left: 3px solid #7b42f6;
}

.request-item.is-group:hover {
  background: #f0ecff;
}

.request-item.is-group .request-name {
  font-weight: 600;
  color: #5a32a3;
}

.request-item.is-dragging {
  opacity: 0.8;
  background: #f0f9ff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* 拖拽手柄样式 */
.drag-handle {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  color: #c0c4cc;
  margin-right: 8px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.drag-handle:hover {
  color: #7b42f6;
  background: rgba(123, 66, 246, 0.1);
}

.drag-handle:active {
  cursor: grabbing;
}

.expand-btn {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #7b42f6;
  margin-right: 10px;
  border-radius: 50%;
  border: 1px solid #d4c8f5;
  background: #ffffff;
  transition: all 0.2s ease;
  font-size: 12px;
}

.expand-btn:hover {
  background: #7b42f6;
  color: #ffffff;
  border-color: #7b42f6;
}

.expand-placeholder {
  width: 22px;
  margin-right: 10px;
}

.request-number {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f0ff;
  color: #7b42f6;
  border: 1.5px solid #7b42f6;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 600;
  margin-right: 12px;
  flex-shrink: 0;
}

.request-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.request-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.request-type-badge {
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.request-type-badge.request {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.request-type-badge.group {
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
}

.request-type-badge.wait {
  background: rgba(250, 173, 20, 0.1);
  color: #faad14;
}

.request-type-badge.script {
  background: rgba(114, 46, 209, 0.1);
  color: #722ed1;
}

.request-type-badge.condition {
  background: rgba(23, 125, 220, 0.1);
  color: #177ddc;
}

.request-type-badge.loop {
  background: rgba(19, 194, 194, 0.1);
  color: #13c2c2;
}

.request-type-badge.scenario_ref {
  background: rgba(235, 47, 150, 0.1);
  color: #eb2f96;
}

.request-name {
  font-weight: 500;
  color: #262626;
  font-size: 14px;
  line-height: 1.4;
}

.child-count {
  color: #8c8c8c;
  font-size: 12px;
  padding: 2px 8px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 10px;
}

.request-detail {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.method {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  min-width: 48px;
  text-align: center;
}

.method-get {
  background: #e6f4ff;
  color: #0958d9;
}

.method-post {
  background: #f6ffed;
  color: #389e0d;
}

.method-put {
  background: #fff7e6;
  color: #d46b08;
}

.method-delete {
  background: #fff2f0;
  color: #cf1322;
}

.method-patch {
  background: #f9f0ff;
  color: #531dab;
}

.url {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  color: #595959;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
}

/* 等待时间步骤详情样式 */
.wait-detail {
  color: #faad14;
  font-weight: 500;
}

.wait-detail .el-icon {
  font-size: 14px;
}

.request-meta {
  margin: 0 20px;
  flex-shrink: 0;
}

.assertion-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #52c41a;
  font-size: 12px;
  padding: 4px 10px;
  background: rgba(82, 196, 26, 0.08);
  border-radius: 12px;
  font-weight: 500;
}

.request-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  flex-shrink: 0;
  padding-left: 16px;
}

.enable-switch {
  flex-shrink: 0;
  margin-right: 12px;
}

.action-btn {
  width: 32px !important;
  height: 32px !important;
  padding: 0 !important;
  border-radius: 8px !important;
  border: none !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: all 0.2s ease !important;
}

.action-btn.edit-btn {
  background: rgba(123, 66, 246, 0.1) !important;
  color: #7b42f6 !important;
}

.action-btn.edit-btn:hover {
  background: #7b42f6 !important;
  color: #ffffff !important;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
}

.action-btn.remove-btn {
  background: rgba(255, 77, 79, 0.1) !important;
  color: #ff4d4f !important;
}

.action-btn.remove-btn:hover {
  background: #ff4d4f !important;
  color: #ffffff !important;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 77, 79, 0.4);
}

/* 拖拽时的样式 */
.dragging-ghost {
  opacity: 0.5;
  background: #f0f9ff !important;
  border: 2px dashed #7b42f6;
}

.dragging-chosen {
  opacity: 0.9;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.dragging-drag {
  opacity: 1;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  transform: scale(1.02);
}

.request-children {
  width: 100%;
}
</style>
