<template>
  <div class="page-container">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-bar-spacer"></div>
      <el-button
        type="primary"
        :icon="Refresh"
        :loading="refreshing"
        @click="refreshDevices"
        class="refresh-btn"
      >
        刷新设备
      </el-button>
      <el-button
        type="primary"
        :icon="Plus"
        @click="showAddRemoteDialog"
        class="create-btn"
      >
        添加远程设备
      </el-button>
    </div>

    <!-- 表格容器 -->
    <div class="card-container">
      <!-- 设备列表 -->
      <el-table
        v-loading="loading"
        :data="devices"
        stripe
        style="width: 100%"
        :empty-text="emptyText"
      >
        <el-table-column prop="name" label="设备名称" min-width="150" header-align="center" align="left">
          <template #default="{ row }">
            <span>{{ row.name || row.device_id }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="device_id" label="设备序列号" min-width="180" header-align="center" align="left" />

        <el-table-column prop="status" label="状态" width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="row.status">
              {{ getStatusText(row.status) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="locked_by" label="锁定用户" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.locked_by_name">
              {{ row.locked_by_name }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="locked_at" label="锁定时间" width="180" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.locked_at">
              {{ formatDate(row.locked_at) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="android_version" label="Android版本" width="120" header-align="center" align="center" />

        <el-table-column prop="connection_type" label="连接类型" width="160" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="getConnectionType(row.connection_type) === 'local' ? 'success' : 'processing'">
              {{ getConnectionTypeName(row.connection_type) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="ip_address" label="IP地址" width="150" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.ip_address">
              {{ row.ip_address }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="usage_count" label="使用次数" width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.usage_count > 0" class="count-badge">{{ row.usage_count }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="updated_at" label="更新时间" width="220" header-align="center" align="center">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="350" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                v-if="row.status === 'available' || row.status === 'online'"
                size="small"
                type="primary"
                class="action-btn edit-btn"
                @click="lockDevice(row)"
              >
                <el-icon><Lock /></el-icon>
                <span>锁定</span>
              </el-button>
              <el-button
                v-if="row.status === 'locked'"
                size="small"
                type="success"
                class="action-btn run-btn"
                @click="unlockDevice(row)"
              >
                <el-icon><Unlock /></el-icon>
                <span>解锁</span>
              </el-button>
              <el-button
                v-if="isRemoteDevice(row.connection_type) && row.status === 'offline'"
                size="small"
                type="warning"
                class="action-btn reconnect-btn"
                :loading="reconnectingDevices[row.id]"
                @click="reconnectDevice(row)"
              >
                <el-icon><Connection /></el-icon>
                <span>重连</span>
              </el-button>
              <el-button
                size="small"
                class="action-btn info-btn"
                @click="viewDeviceInfo(row)"
              >
                <el-icon><View /></el-icon>
                <span>详情</span>
              </el-button>
              <el-button
                v-if="isRemoteDevice(row.connection_type) && (row.status === 'online' || row.status === 'available')"
                size="small"
                type="warning"
                class="action-btn"
                @click="disconnectDevice(row)"
              >
                <el-icon><SwitchButton /></el-icon>
                <span>断开</span>
              </el-button>
              <el-button
                size="small"
                type="danger"
                class="action-btn delete-btn"
                @click="handleDeleteDevice(row)"
              >
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加远程设备对话框 -->
    <el-dialog
      v-model="addRemoteDialogVisible"
      title="添加远程设备"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="remoteDeviceFormRef"
        :model="remoteDeviceForm"
        :rules="remoteDeviceRules"
        label-width="100px"
      >
        <el-form-item label="IP地址" prop="ip_address">
          <el-input
            v-model="remoteDeviceForm.ip_address"
            placeholder="请输入远程设备IP地址"
          />
        </el-form-item>

        <el-form-item label="端口" prop="port">
          <el-input-number
            v-model="remoteDeviceForm.port"
            :min="1"
            :max="65535"
            placeholder="默认5555"
            style="width: 100%"
          />
        </el-form-item>

        <el-alert
          title="提示"
          type="info"
          :closable="false"
          style="margin-top: 10px"
        >
          <div>请确保：</div>
          <div>1. 远程设备已开启ADB调试</div>
          <div>2. 远程设备已开启网络ADB（adb tcpip 5555）</div>
          <div>3. 网络连接正常</div>
        </el-alert>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="addRemoteDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="connecting"
            @click="connectRemoteDevice"
          >
            连接
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 设备详情对话框 -->
    <el-dialog
      v-model="deviceInfoDialogVisible"
      title="设备详情"
      width="600px"
    >
      <el-descriptions v-if="selectedDevice" :column="2" border>
        <el-descriptions-item label="设备名称">
          {{ selectedDevice.name || selectedDevice.device_id }}
        </el-descriptions-item>
        <el-descriptions-item label="设备序列号">
          {{ selectedDevice.device_id }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(selectedDevice.status)" size="small">
            {{ getStatusText(selectedDevice.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="锁定用户">
          {{ selectedDevice.locked_by_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="锁定时间">
          {{ selectedDevice.locked_at ? formatDate(selectedDevice.locked_at) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Android版本">
          {{ selectedDevice.android_version || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="连接类型">
          <el-tag
            :type="getConnectionType(selectedDevice.connection_type) === 'local' ? 'primary' : 'warning'"
            size="small"
          >
            {{ getConnectionTypeName(selectedDevice.connection_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="IP地址">
          {{ selectedDevice.ip_address || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="端口">
          {{ selectedDevice.port || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="使用次数">
          {{ selectedDevice.usage_count || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDate(selectedDevice.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ formatDate(selectedDevice.updated_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="deviceInfoDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, Lock, Unlock, Connection, View, SwitchButton, Delete } from '@element-plus/icons-vue'
import {
  getDeviceList,
  discoverDevices,
  lockDevice as apiLockDevice,
  unlockDevice as apiUnlockDevice,
  connectDevice,
  disconnectDevice as apiDisconnectDevice,
  deleteDevice
} from '@/api/app-automation'
import { getDeviceStatusType, getDeviceStatusText, formatDateTime } from '@/utils/app-automation-helpers'

defineOptions({ name: 'AppDeviceList' })

// Refs
const remoteDeviceFormRef = ref(null)

// 响应式数据
const devices = ref([])
const loading = ref(false)
const refreshing = ref(false)
const connecting = ref(false)
const reconnectingDevices = ref({})
const addRemoteDialogVisible = ref(false)
const deviceInfoDialogVisible = ref(false)
const selectedDevice = ref(null)
const emptyText = ref('暂无设备，请点击刷新设备或添加远程设备')
const refreshTimer = ref(null)

const remoteDeviceForm = ref({
  ip_address: '',
  port: 5555
})

const remoteDeviceRules = {
  ip_address: [
    { required: true, message: '请输入IP地址', trigger: 'blur' },
    {
      pattern: /^(\d{1,3}\.){3}\d{1,3}$/,
      message: '请输入有效的IP地址',
      trigger: 'blur'
    }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' }
  ]
}

// 方法
const getDevices = async () => {
  loading.value = true
  try {
    const res = await getDeviceList({ page: 1, page_size: 1000 })
    devices.value = res.data.results || []
    if (devices.value.length === 0) {
      emptyText.value = '暂无设备，请点击刷新设备或添加远程设备'
    }
  } catch (error) {
    console.error('获取设备列表失败:', error)
    ElMessage.error('获取设备列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const refreshDevices = async () => {
  refreshing.value = true
  try {
    const res = await discoverDevices()
    if (res.data.success) {
      ElMessage.success(res.data.message || '设备列表已刷新')
      // 刷新后重新从数据库获取设备列表，确保显示所有设备（包括离线设备）
      await getDevices()
    } else {
      ElMessage.error(res.data.message || '刷新设备列表失败')
    }
  } catch (error) {
    console.error('刷新设备列表失败:', error)
    ElMessage.error('刷新设备列表失败: ' + (error.message || '未知错误'))
  } finally {
    refreshing.value = false
  }
}

const showAddRemoteDialog = () => {
  addRemoteDialogVisible.value = true
  remoteDeviceForm.value = {
    ip_address: '',
    port: 5555
  }
  if (remoteDeviceFormRef.value) {
    remoteDeviceFormRef.value.clearValidate()
  }
}

const connectRemoteDevice = async () => {
  if (!remoteDeviceFormRef.value) return
  
  remoteDeviceFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    connecting.value = true
    try {
      const res = await connectDevice({
        ip_address: remoteDeviceForm.value.ip_address,
        port: remoteDeviceForm.value.port
      })
      
      if (res.data.success) {
        ElMessage.success(res.data.message || '远程设备连接成功')
        addRemoteDialogVisible.value = false
        await getDevices()
      } else {
        ElMessage.error(res.data.message || '连接远程设备失败')
      }
    } catch (error) {
      console.error('连接远程设备失败:', error)
      ElMessage.error('连接远程设备失败: ' + (error.message || '未知错误'))
    } finally {
      connecting.value = false
    }
  })
}

const reconnectDevice = async (device) => {
  if (!device.ip_address || !device.port) {
    ElMessage.error('设备信息不完整，无法重连')
    return
  }

  reconnectingDevices.value[device.id] = true
  
  try {
    const res = await connectDevice({
      ip_address: device.ip_address,
      port: device.port
    })

    if (res.data.success) {
      ElMessage.success('设备重连成功')
      await getDevices()
    } else {
      ElMessage.error(res.data.message || '设备重连失败，请检查设备网络连接')
    }
  } catch (error) {
    console.error('设备重连失败:', error)
    ElMessage.error('设备重连失败，请检查设备网络连接')
  } finally {
    reconnectingDevices.value[device.id] = false
  }
}

const disconnectDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      `确定要断开设备 ${device.name || device.device_id} 的连接吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await apiDisconnectDevice(device.id)

    if (res.data.success) {
      ElMessage.success('设备已断开')
      await getDevices()
    } else {
      ElMessage.error(res.data.message || '断开设备失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('断开设备失败:', error)
      ElMessage.error('断开设备失败: ' + (error.message || '未知错误'))
    }
  }
}

const viewDeviceInfo = (device) => {
  selectedDevice.value = device
  deviceInfoDialogVisible.value = true
}

const lockDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      `确定要锁定设备 ${device.name || device.device_id} 吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await apiLockDevice(device.id)

    if (res.data.success) {
      ElMessage.success('设备已锁定')
      await getDevices()
    } else {
      ElMessage.error(res.data.message || '锁定设备失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('锁定设备失败:', error)
      ElMessage.error('锁定设备失败: ' + (error.message || '未知错误'))
    }
  }
}

const unlockDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      `确定要解锁设备 ${device.name || device.device_id} 吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await apiUnlockDevice(device.id)

    if (res.data.success) {
      ElMessage.success('设备已解锁')
      await getDevices()
    } else {
      ElMessage.error(res.data.message || '解锁设备失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('解锁设备失败:', error)
      ElMessage.error('解锁设备失败: ' + (error.message || '未知错误'))
    }
  }
}

const handleDeleteDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备 ${device.name || device.device_id} 吗？删除后将无法恢复。`,
      '删除设备',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false
      }
    )

    const res = await deleteDevice(device.id)

    if (res.status === 204 || res.status === 200) {
      ElMessage.success('设备已删除')
      await getDevices()
    } else {
      ElMessage.error(res.data?.message || '删除设备失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除设备失败:', error)
      ElMessage.error('删除设备失败: ' + (error.message || '未知错误'))
    }
  }
}

const formatDate = formatDateTime
const getStatusType = getDeviceStatusType
const getStatusText = getDeviceStatusText

const getConnectionType = (type) => {
  // emulator, remote_emulator, remote, usb 等
  if (type === 'emulator' || type === 'usb') {
    return 'local'
  }
  return 'remote'
}

const getConnectionTypeName = (type) => {
  const typeMap = {
    'emulator': '本地模拟器',
    'remote_emulator': '远程模拟器',
    'remote': '远程设备',
    'usb': 'USB连接'
  }
  return typeMap[type] || type
}

const isRemoteDevice = (type) => {
  return type === 'remote_emulator' || type === 'remote'
}

// 生命周期
onMounted(() => {
  getDevices()

  // 30秒自动刷新设备列表
  refreshTimer.value = setInterval(() => {
    getDevices()
  }, 30000)
})

onBeforeUnmount(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})
</script>

<style scoped lang="scss">
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;

  .filter-bar-spacer {
    flex: 1;
  }

  .el-button--primary {
    background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(167, 139, 250, 0.3) !important;

    &:hover {
      background: linear-gradient(135deg, #9370db 0%, #7c3aed 100%) !important;
      transform: translateY(-2px) !important;
      box-shadow: 0 6px 20px rgba(167, 139, 250, 0.4) !important;
    }
  }
}

.card-container {
  flex: 1;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;

  .el-table {
    border: none;
    border-radius: 8px 8px 0 0;
    overflow: hidden;
    min-height: 200px;
    box-shadow: none;
    transition: all 0.3s ease;
    background-color: transparent !important;

    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: #7b42f6;
    --el-color-primary-light-3: #9370db;
    --el-color-primary-light-5: #a888e0;
    --el-color-primary-light-7: #c2a9f3;
    --el-color-primary-light-9: #f8f7ff;
    --el-border-color: #e9ecef;
    --el-border-color-light: #e9ecef;
    --el-border-color-lighter: #e9ecef;
    --el-fill-color-light: #ffffff;
    --el-fill-color-lighter: #ffffff;
    --el-fill-color-blank: #ffffff;
    --el-text-color-primary: #333;
    --el-text-color-regular: #333;
    --el-text-color-secondary: #666;
    --el-text-color-placeholder: #999;
    --el-table-header-bg-color: #ffffff;
    --el-table-row-hover-bg-color: #f8f7ff;
    --el-table-stripe-bg-color: #fafaff;

    &::before {
      display: none;
    }

    // 表头包装器
    :deep(.el-table__header-wrapper) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__header) {
      background-color: #ffffff !important;
    }

    :deep(th) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600;
      font-size: 14px;
      border-bottom: 1px solid #e9ecef;
      padding: 0 !important;
      text-align: center;
      transition: all 0.3s ease;

      &:hover {
        background-color: #ffffff !important;
      }
    }

    :deep(th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
      white-space: nowrap !important;
      line-height: 24px !important;
      padding: 16px !important;
    }

    :deep(.el-table__body-wrapper) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__row) {
      transition: all 0.3s ease;
      background-color: #ffffff !important;
      line-height: 24px;

      &:hover {
        background-color: #f8f7ff !important;
      }

      &.el-table__row--striped {
        background-color: #fafaff !important;
      }
    }

    :deep(td) {
      padding: 14px 16px;
      border-bottom: 1px solid #e9ecef;
      color: #333;
      font-size: 14px;
      font-weight: 400;
      line-height: 24px;
      transition: all 0.3s ease;
      vertical-align: middle;
    }

    // 空状态
    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;

      :deep(.el-table__empty-text) {
        color: #666;
        font-size: 14px;
        line-height: 24px;
      }
    }

    // 确保整个表格容器都使用正确的背景色
    &.el-table--enable-row-hover {
      background-color: #ffffff !important;
    }

    // 覆盖表格行的默认样式
    :deep(.el-table__row) {
      background-color: #ffffff !important;
    }

    // 覆盖表格行的条纹样式
    :deep(.el-table__row.el-table__row--striped) {
      background-color: #fafaff !important;
    }

    // 覆盖表格行的 hover 样式
    :deep(.el-table__row:hover) {
      background-color: #f8f7ff !important;
    }

    // 直接覆盖表头单元格样式
    :deep(.el-table__header th) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }

    // 直接覆盖表头单元格内容样式
    :deep(.el-table__header th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }

    // 修复固定列在路由切换时的显示问题
    :deep(.el-table__fixed-right) {
      background-color: #ffffff !important;
      height: 100% !important;
    }

    :deep(.el-table__fixed-right-patch) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__fixed-body-wrapper) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__fixed-header-wrapper) {
      background-color: #ffffff !important;
    }
  }
}

// 操作按钮样式 - 使用 .page-container 作为前缀避免样式冲突
.page-container {
  .action-buttons {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 4px;
    flex-wrap: nowrap;
  }

  .action-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 10px !important;
    border-radius: 6px;
    transition: all 0.3s ease;
    border: none !important;

    .el-icon {
      font-size: 14px;
      color: #ffffff !important;
    }

    span {
      font-size: 12px;
      color: #ffffff !important;
    }

    // 默认按钮样式（断开等）
    &:not(.edit-btn):not(.run-btn):not(.delete-btn):not(.reconnect-btn):not(.info-btn) {
      background: linear-gradient(135deg, #909399 0%, #606266 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #a6a9ad 0%, #909399 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(144, 147, 153, 0.4);
      }
    }

    // 重连按钮样式（橙色）
    &.reconnect-btn {
      background: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #ffa940 0%, #fa8c16 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(250, 140, 22, 0.4);
      }
    }

    // 详情按钮样式（蓝灰色）
    &.info-btn {
      background: linear-gradient(135deg, #40a9ff 0%, #1890ff 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #69c0ff 0%, #40a9ff 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
      }
    }

    &.edit-btn {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
      }
    }

    &.run-btn {
      background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
      }
    }

    &.delete-btn {
      background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
      }
    }
  }
}

// 状态徽章样式
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
  white-space: nowrap;

  // 成功 - 绿色
  &.success {
    background: #f6ffed;
    color: #52c41a;
  }

  // 失败 - 红色
  &.failed {
    background: #fff1f0;
    color: #f5222d;
  }

  // 处理中 - 橙色
  &.processing {
    background: #fff7e6;
    color: #fa8c16;
  }

  // 待处理 - 灰色
  &.pending {
    background: #f5f5f5;
    color: #8c8c8c;
  }

  // 设备状态 - 可用（绿色）
  &.available {
    background: #f6ffed;
    color: #52c41a;
  }

  // 设备状态 - 在线（绿色）
  &.online {
    background: #f6ffed;
    color: #52c41a;
  }

  // 设备状态 - 锁定（橙色）
  &.locked {
    background: #fff7e6;
    color: #fa8c16;
  }

  // 设备状态 - 离线（灰色）
  &.offline {
    background: #f5f5f5;
    color: #8c8c8c;
  }

  // 设备状态 - 错误（红色）
  &.error {
    background: #fff1f0;
    color: #f5222d;
  }
}

// 数量徽章样式
.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #e6f7ff;
  color: #1890ff;
  white-space: nowrap;
}

// 时间文本样式
.time-text {
  color: #666;
  font-size: 14px;
  white-space: nowrap;
}

.text-gray {
  color: #999;
}

// 分页容器样式
.pagination-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 0;
  margin-top: 8px;
  background: transparent;
  border: none;
  transition: all 0.3s ease;

  --primary-color: #a78bfa;
  --primary-dark: #8b5cf6;
  --primary-light: #f3f0ff;
  --text-primary: #262626;
  --text-secondary: #595959;
  --text-tertiary: #8c8c8c;

  --el-color-primary: var(--primary-color);
  --el-color-primary-light-3: #c4b5fd;
  --el-color-primary-light-5: #ddd6fe;
  --el-color-primary-light-7: #ede9fe;
  --el-color-primary-light-9: #f5f3ff;
  --el-border-color: rgba(167, 139, 250, 0.3);
  --el-border-color-light: rgba(167, 139, 250, 0.2);
  --el-border-color-lighter: rgba(167, 139, 250, 0.1);
  --el-fill-color-light: #f5f3ff;
  --el-fill-color-lighter: #f5f3ff;
  --el-fill-color-blank: #f5f3ff;
  --el-text-color-primary: var(--text-primary);
  --el-text-color-regular: var(--text-secondary);
  --el-text-color-secondary: var(--text-tertiary);
}

.dialog-footer {
  text-align: right;
}

// 操作按钮样式
.page-container {
  .action-buttons {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 4px;
    flex-wrap: nowrap;
  }

  .action-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 10px !important;
    border-radius: 6px;
    transition: all 0.3s ease;
    border: none !important;

    .el-icon {
      font-size: 14px;
      color: #ffffff !important;
    }

    span {
      font-size: 12px;
      color: #ffffff !important;
    }

    &.edit-btn {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
      }
    }

    &.run-btn {
      background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
      }
    }

    &.delete-btn {
      background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
      }
    }
  }
}

// 状态徽章样式
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
  white-space: nowrap;

  &.success {
    background: #f6ffed;
    color: #52c41a;
  }

  &.failed {
    background: #fff1f0;
    color: #f5222d;
  }

  &.processing {
    background: #fff7e6;
    color: #fa8c16;
  }

  &.pending {
    background: #f5f5f5;
    color: #8c8c8c;
  }
}
</style>