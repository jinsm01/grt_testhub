<template>
  <div class="page-container">
    <!-- 任务输入区域 -->
    <div class="card-container">
      <div class="section-title">{{ $t('uiAutomation.ai.taskInput') }}</div>
      <el-form :model="taskForm" label-position="top">
        <el-form-item class="task-desc-item">
          <el-input
            v-model="taskForm.description"
            type="textarea"
            :rows="6"
            placeholder="请用自然语言按操作步骤描述，例如：

1. 访问 https://passport.grtcloud.net

2. 点击'密码登录'"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>

        <div class="form-actions">
          <div class="form-options">
            <el-form-item label="步骤截图" class="gif-option">
              <div class="gif-switch-wrapper">
                <el-switch
                  v-model="taskForm.enableGif"
                  :active-text="$t('uiAutomation.ai.on')"
                  :inactive-text="$t('uiAutomation.ai.off')"
                />
                <span class="gif-tip">
                  开启后每执行一步自动截图，可在报告详细步骤中查看
                </span>
              </div>
            </el-form-item>
          </div>
          <div class="form-buttons">
            <el-button
              type="primary"
              @click="handleRun"
              :loading="running"
              :disabled="!taskForm.description"
            >
              <el-icon><VideoPlay /></el-icon>
              {{ $t('uiAutomation.ai.startExecution') }}
            </el-button>
            <el-button
              type="danger"
              @click="handleStop"
              :disabled="!running"
              v-if="running"
            >
              <el-icon><SwitchButton /></el-icon>
              {{ $t('uiAutomation.ai.stopExecution') }}
            </el-button>
            <el-button
              type="success"
              @click="handleSaveAsCase"
              :disabled="!taskForm.description"
            >
              <el-icon><DocumentAdd /></el-icon>
              {{ $t('uiAutomation.ai.saveAsCase') }}
            </el-button>
          </div>
        </div>
      </el-form>
    </div>

    <!-- 任务明细和执行日志区域 -->
    <div class="bottom-section">
      <el-row :gutter="20">
        <el-col :span="12">
          <div class="card-container task-detail-card">
            <div class="section-title">{{ $t('uiAutomation.ai.taskDetails') }}</div>
            <div class="task-list-container">
              <div v-if="analyzing" class="analyzing-state">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>{{ $t('uiAutomation.ai.analyzing') }}</span>
              </div>
              <div v-else-if="plannedTasks.length > 0">
                <div
                  v-for="task in plannedTasks"
                  :key="task.id"
                  class="task-item"
                  :class="task.status"
                >
                  <div class="task-status-icon">
                    <el-icon v-if="task.status === 'completed'" color="#67C23A"><CircleCheckFilled /></el-icon>
                    <el-icon v-else-if="task.status === 'in_progress'" class="is-loading" color="#409EFF"><Loading /></el-icon>
                    <el-icon v-else color="#909399"><CircleCheck /></el-icon>
                  </div>
                  <div class="task-content">
                    <span class="task-id">{{ task.id }}.</span>
                    <span class="task-desc">{{ task.description }}</span>
                  </div>
                </div>
              </div>
              <div v-else class="empty-tasks">
                {{ $t('uiAutomation.ai.noTasks') }}
              </div>
            </div>
          </div>
        </el-col>

        <el-col :span="12">
          <div class="card-container log-card">
            <div class="section-title" style="display: flex; justify-content: space-between; align-items: center;">
              <span>{{ $t('uiAutomation.ai.executionLogs') }}</span>
              <el-button
                v-if="snapshotData.element_count > 0"
                type="primary"
                size="small"
                text
                @click="showSnapshot = !showSnapshot"
              >
                <el-icon><View /></el-icon>
                {{ showSnapshot ? '隐藏' : '查看' }}页面元素 ({{ snapshotData.element_count }})
              </el-button>
            </div>

            <!-- Snapshot 展示区域 -->
            <div v-if="showSnapshot && snapshotData.element_count > 0" class="snapshot-container">
              <div class="snapshot-header">
                <el-tag size="small" type="info" class="snapshot-url">{{ snapshotData.url }}</el-tag>
                <el-tag size="small" type="success">{{ snapshotData.element_count }} 个元素</el-tag>
              </div>
              <div class="snapshot-list">
                <div v-for="el in snapshotData.elements" :key="el.index" class="snapshot-item">
                  <span class="snapshot-index">[{{ el.index }}]</span>
                  <span class="snapshot-tag">&lt;{{ el.tag }}</span>
                  <span v-if="el.type" class="snapshot-attr">type='{{ el.type }}'</span>
                  <span v-if="el.text" class="snapshot-attr">text='{{ el.text }}'</span>
                  <span v-if="el.placeholder" class="snapshot-attr">placeholder='{{ el.placeholder }}'</span>
                  <span v-if="el.ariaLabel" class="snapshot-attr">aria-label='{{ el.ariaLabel }}'</span>
                  <span class="snapshot-tag">&gt;</span>
                </div>
              </div>
            </div>

            <div class="log-container" ref="logContainer">
              <div v-if="!logs && !running" class="empty-logs">
                {{ $t('uiAutomation.ai.noLogs') }}
              </div>
              <pre v-else class="log-content">{{ logs }}</pre>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 保存为用例对话框 -->
    <el-dialog v-model="showSaveDialog" :title="$t('uiAutomation.ai.saveAsCaseTitle')" width="500px">
      <el-form :model="saveForm" :rules="saveRules" ref="saveFormRef" label-width="80px">
        <el-form-item :label="$t('uiAutomation.ai.caseName')" prop="name">
          <el-input v-model="saveForm.name" :placeholder="$t('uiAutomation.ai.caseNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.common.description')" prop="description">
          <el-input v-model="saveForm.description" type="textarea" :placeholder="$t('uiAutomation.ai.caseDescPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showSaveDialog = false">{{ $t('uiAutomation.common.cancel') }}</el-button>
          <el-button type="primary" @click="confirmSaveCase" :loading="saving">{{ $t('uiAutomation.common.save') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, DocumentAdd, CircleCheckFilled, CircleCheck, Loading, SwitchButton, View } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import {
  runAdhocAITask,
  createAICase,
  getAIExecutionRecordDetail,
  stopAITask
} from '@/api/ui_automation'

const { t } = useI18n()

const running = ref(false)
const analyzing = ref(false)
const saving = ref(false)
const logs = ref('')
const plannedTasks = ref([])
const currentExecutionId = ref(null)
const logContainer = ref(null)
const snapshotData = ref({
  url: '',
  title: '',
  element_count: 0,
  elements: [],
  snapshot_text: '',
  timestamp: ''
})
const showSnapshot = ref(false)

const taskForm = reactive({
  description: '',
  enableGif: true  // GIF录制开关，默认开启
})

const showSaveDialog = ref(false)
const saveForm = reactive({
  name: '',
  description: ''
})
const saveFormRef = ref(null)

const saveRules = computed(() => ({
  name: [{ required: true, message: t('uiAutomation.ai.rules.nameRequired'), trigger: 'blur' }]
}))

// 执行任务
const handleRun = async () => {
  running.value = true
  analyzing.value = true
  logs.value = t('uiAutomation.ai.messages.initAgent')
  plannedTasks.value = []

  try {
    const response = await runAdhocAITask({
      task_description: taskForm.description,
      execution_mode: 'text',  // 始终使用文本模式
      enable_gif: taskForm.enableGif  // 传递GIF录制开关状态
    })

    // analyzing.value = false // 移除过早设置，改为在轮询获取到任务列表后再取消

    currentExecutionId.value = response.data.execution_id
    ElMessage.success(t('uiAutomation.ai.messages.startSuccess'))

    // 开始轮询日志
    pollLogs()

  } catch (error) {
    console.error('执行失败:', error)
    ElMessage.error(t('uiAutomation.ai.messages.startFailed') + ': ' + (error.response?.data?.error || error.message))
    running.value = false
    analyzing.value = false
  }
}

// 停止任务
const handleStop = async () => {
  if (!currentExecutionId.value) return

  try {
    await stopAITask(currentExecutionId.value)
    ElMessage.warning(t('uiAutomation.ai.messages.stopping'))
    // 不立即设置 running = false，等待轮询检测到状态变化
  } catch (error) {
    console.error('停止失败:', error)
    ElMessage.error(t('uiAutomation.ai.messages.stopFailed'))
  }
}

// 轮询日志
const pollLogs = () => {
  const pollInterval = setInterval(async () => {
    if (!currentExecutionId.value) {
      clearInterval(pollInterval)
      return
    }
    
    try {
      const response = await getAIExecutionRecordDetail(currentExecutionId.value)
      const record = response.data
      
      logs.value = record.logs || ''
      plannedTasks.value = record.planned_tasks || []
      
      // 更新页面快照数据
      if (record.snapshot_data && record.snapshot_data.element_count > 0) {
        snapshotData.value = record.snapshot_data
      }
      
      // 如果获取到了任务列表，则取消“分析中”状态
      if (plannedTasks.value.length > 0) {
        analyzing.value = false
      }
      
      // 滚动到底部
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight
        }
      })
      
      if (record.status === 'passed' || record.status === 'failed' || record.status === 'stopped') {
        clearInterval(pollInterval)
        running.value = false
        analyzing.value = false // 确保结束时必然取消分析状态
        if (record.status === 'passed') {
          ElMessage.success(t('uiAutomation.ai.messages.executionSuccess'))
        } else if (record.status === 'stopped') {
          ElMessage.warning(t('uiAutomation.ai.messages.taskStopped'))
        } else {
          ElMessage.error(t('uiAutomation.ai.messages.executionFailed'))
        }
      }
    } catch (error) {
      console.error('获取日志失败:', error)
      // 不停止轮询，可能是临时网络问题
    }
  }, 2000) // 每2秒轮询一次
}

// 保存为用例
const handleSaveAsCase = () => {
  showSaveDialog.value = true
  saveForm.name = ''
  saveForm.description = ''
}

const confirmSaveCase = async () => {
  if (!saveFormRef.value) return

  await saveFormRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        await createAICase({
          name: saveForm.name,
          description: saveForm.description,
          task_description: taskForm.description
        })

        ElMessage.success(t('uiAutomation.ai.messages.saveSuccess'))
        showSaveDialog.value = false
      } catch (error) {
        console.error('保存失败:', error)
        ElMessage.error(t('uiAutomation.ai.messages.saveFailed'))
      } finally {
        saving.value = false
      }
    }
  })
}
</script>

<style lang="scss" scoped>
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 28px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.1);

  .page-title {
    font-size: 24px;
    font-weight: 700;
    color: #5a32a3;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 24px;
  flex: 1;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
  padding-left: 10px;
  border-left: 4px solid #7b42f6;
  color: #5a32a3;
}

// 表单操作区域
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-top: 20px;
  flex-wrap: wrap;
  gap: 16px;

  .task-desc-item {
    margin-bottom: 20px;

    :deep(.el-form-item__label) {
      color: #5a32a3;
      font-weight: 600;
      font-size: 14px;
      padding-left: 10px;
      border-left: 4px solid #7b42f6;
    }
  }

  .form-options {
    .gif-option {
      margin-bottom: 0;

      :deep(.el-form-item__label) {
        color: #5a32a3;
        font-weight: 600;
        font-size: 14px;
        padding-left: 10px;
        border-left: 4px solid #7b42f6;
      }
    }

    .gif-switch-wrapper {
      display: flex;
      align-items: center;
      margin-top: 8px;

      :deep(.el-switch__label) {
        color: #5a32a3;
        font-weight: 500;
        font-size: 14px;
      }

      :deep(.el-switch.is-checked .el-switch__label) {
        color: #5a32a3;
      }
    }

    .gif-tip {
      margin-left: 10px;
      color: #909399;
      font-size: 12px;
    }
  }

  .form-buttons {
    display: flex;
    gap: 12px;
  }
}

// 底部区域
.bottom-section {
  .task-detail-card,
  .log-card {
    height: 100%;
    min-height: 400px;
  }
}

.task-list-container {
  background-color: #f8f7ff;
  border-radius: 8px;
  padding: 16px;
  height: calc(100% - 40px);
  overflow-y: auto;
  border: 1px solid rgba(147, 112, 219, 0.1);

  .task-item {
    display: flex;
    align-items: flex-start;
    padding: 12px;
    margin-bottom: 8px;
    border-radius: 8px;
    background-color: #ffffff;
    border: 1px solid rgba(147, 112, 219, 0.1);
    transition: all 0.3s;

    &:last-child {
      margin-bottom: 0;
    }

    &.completed {
      background-color: #f0f9eb;
      border-color: rgba(103, 194, 58, 0.2);
      .task-desc {
        color: #67c23a;
        text-decoration: line-through;
      }
    }

    &.in_progress {
      background-color: #ecf5ff;
      border-color: rgba(64, 158, 255, 0.2);
      .task-desc {
        color: #409eff;
        font-weight: bold;
      }
    }

    .task-status-icon {
      margin-right: 10px;
      margin-top: 2px;
      font-size: 16px;
    }

    .task-content {
      flex: 1;
      line-height: 1.5;

      .task-id {
        font-weight: bold;
        margin-right: 5px;
        color: #5a32a3;
      }

      .task-desc {
        color: #333;
      }
    }
  }
}

.empty-tasks {
  color: #909399;
  text-align: center;
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.analyzing-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #5a32a3;

  .el-icon {
    font-size: 24px;
    margin-bottom: 10px;
  }
}

.log-container {
  background-color: #1e1e1e;
  border-radius: 8px;
  height: 300px;
  overflow-y: auto;
  padding: 15px;
  color: #fff;
  font-family: 'Consolas', 'Monaco', monospace;
  display: flex;
  flex-direction: column;

  .empty-logs {
    color: #909399;
    text-align: center;
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0;
  }

  .log-content {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 14px;
    line-height: 1.5;
  }
}

// Snapshot 样式
.snapshot-container {
  background-color: #f8f7ff;
  border: 1px solid rgba(147, 112, 219, 0.2);
  border-radius: 8px;
  margin-bottom: 12px;
  max-height: 250px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;

  .snapshot-header {
    display: flex;
    gap: 8px;
    padding: 10px 12px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);
    background-color: #ffffff;
    position: sticky;
    top: 0;
    z-index: 1;

    .snapshot-url {
      max-width: 70%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .snapshot-list {
    padding: 8px 12px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    line-height: 1.6;
  }

  .snapshot-item {
    padding: 4px 0;
    border-bottom: 1px solid rgba(147, 112, 219, 0.05);
    color: #333;
    word-break: break-all;

    &:last-child {
      border-bottom: none;
    }

    .snapshot-index {
      color: #7b42f6;
      font-weight: bold;
      margin-right: 6px;
      min-width: 32px;
      display: inline-block;
    }

    .snapshot-tag {
      color: #e83e8c;
    }

    .snapshot-attr {
      color: #0066cc;
      margin-left: 4px;
    }
  }
}

// 按钮样式
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
  border: none !important;
  color: white !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;
  transition: all 0.3s ease !important;

  &:hover {
    background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(123, 66, 246, 0.4) !important;
  }

  .el-icon {
    margin-right: 6px;
  }
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #67c23a 0%, #389e0d 100%) !important;
  border: none !important;
  color: white !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.3) !important;
  transition: all 0.3s ease !important;

  &:hover {
    background: linear-gradient(135deg, #85ce61 0%, #67c23a 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(103, 194, 58, 0.4) !important;
  }

  .el-icon {
    margin-right: 6px;
  }
}

:deep(.el-button--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #c45656 100%) !important;
  border: none !important;
  color: white !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.3) !important;
  transition: all 0.3s ease !important;

  &:hover {
    background: linear-gradient(135deg, #f78989 0%, #f56c6c 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(245, 108, 108, 0.4) !important;
  }

  .el-icon {
    margin-right: 6px;
  }
}
</style>
