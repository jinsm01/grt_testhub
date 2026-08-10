<template>
  <!-- Token 管理抽屉 -->
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="云效 Token 配置管理"
    direction="rtl"
    size="1200px"
    :close-on-click-modal="false"
    destroy-on-close
    class="token-manager-drawer"
  >
    <div class="token-manager-container">
      <div class="token-manager-form-section">
        <el-form
          ref="tokenFormRef"
          :model="tokenForm"
          :rules="tokenFormRules"
          label-width="100px"
          class="token-form"
        >
          <el-form-item label="用户名" prop="label">
            <el-input
              v-model="tokenForm.label"
              placeholder="请输入用户名"
              clearable
            />
          </el-form-item>
          <el-form-item label="访问令牌" prop="token" v-if="!tokenForm.id">
            <el-input
              v-model="tokenForm.token"
              type="password"
              show-password
              placeholder="粘贴云效个人访问令牌 (PAT)"
              clearable
            />
          </el-form-item>
          <el-form-item label="访问令牌" v-else>
            <el-input
              v-model="tokenForm.token"
              type="password"
              show-password
              placeholder="留空表示不修改，如需更新请输入新Token"
              clearable
            />
          </el-form-item>
        </el-form>
      </div>

      <div class="token-manager-list-section token-list-card">
        <h4 class="list-title">已有 Token 列表</h4>
        <el-table
          v-loading="tokenListLoading"
          :data="tokenList"
          stripe
          style="width: 100%"
          empty-text="暂无Token配置，快去添加吧！"
        >
          <el-table-column prop="id" label="ID" width="60" header-align="center" align="center" />
          <el-table-column prop="label" label="用户名" min-width="150" header-align="center" align="left" show-overflow-tooltip />
          <el-table-column prop="token_masked" label="令牌 (脱敏)" min-width="180" header-align="center" align="center" show-overflow-tooltip />
          <el-table-column prop="is_active" label="启用" width="80" header-align="center" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.is_active"
                @change="toggleTokenActive(row)"
                size="small"
              />
            </template>
          </el-table-column>
          <el-table-column prop="created_by" label="创建者" width="100" header-align="center" align="center" />
          <el-table-column prop="updated_at" label="更新时间" width="160" header-align="center" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="time-text">{{ row.updated_at || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right" header-align="center" align="center">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button
                  size="small"
                  :type="tokenTestResults[row.id] === 'success' ? 'success' : tokenTestResults[row.id] === 'fail' ? 'danger' : 'info'"
                  :loading="tokenTestResults[row.id] === 'loading'"
                  @click="testToken(row.id)"
                >
                  {{ tokenTestResults[row.id] === 'success' ? '✓' : tokenTestResults[row.id] === 'fail' ? '✗' : '测试' }}
                </el-button>
                <el-button size="small" type="primary" @click="editToken(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteToken(row.id)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!tokenListLoading && tokenList.length === 0" description="暂无Token配置，快去添加吧！" />
      </div>

      <div class="token-form-actions token-drawer-footer">
        <el-button type="primary" :loading="tokenFormSubmitting" @click="saveToken">
          {{ tokenForm.id ? '更新Token' : '创建Token' }}
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getYunxiaoTokens,
  createYunxiaoToken,
  updateYunxiaoToken,
  deleteYunxiaoToken,
  testYunxiaoToken,
} from '@/api/data-factory'

const props = defineProps({
  modelValue: Boolean,
})

const emit = defineEmits(['update:modelValue', 'tokens-updated'])

// Token 管理状态
const tokenList = ref([])
const tokenListLoading = ref(false)
const tokenFormRef = ref(null)
const tokenFormSubmitting = ref(false)
const tokenForm = ref({ id: null, label: '', token: '', is_active: true })
const tokenFormRules = {
  label: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  token: [{ required: true, message: '请输入云效访问令牌', trigger: 'blur' }],
}
const tokenTestResults = ref({})

// 抽屉打开时加载 Token 列表
watch(() => props.modelValue, async (visible) => {
  if (visible) {
    tokenForm.value = { id: null, label: '', token: '', is_active: true }
    tokenTestResults.value = {}
    await loadTokenList()
  }
})

// 加载 Token 列表
async function loadTokenList() {
  tokenListLoading.value = true
  try {
    const res = await getYunxiaoTokens({ page_size: 100 })
    if (res.data?.success) {
      tokenList.value = res.data.items || []
    }
  } catch (e) {
    ElMessage.error('加载Token列表失败: ' + (e.message || e))
  } finally {
    tokenListLoading.value = false
  }
}

// 保存 Token (新建或更新)
async function saveToken() {
  if (!tokenFormRef.value) return
  await tokenFormRef.value.validate(async (valid) => {
    if (!valid) return
    tokenFormSubmitting.value = true
    try {
      const data = {
        label: tokenForm.value.label,
        token: tokenForm.value.token,
        is_active: tokenForm.value.is_active,
      }
      let res
      if (tokenForm.value.id) {
        res = await updateYunxiaoToken(tokenForm.value.id, data)
      } else {
        res = await createYunxiaoToken(data)
      }
      if (res.data?.success) {
        ElMessage.success(res.data.message || '保存成功')
        tokenForm.value = { id: null, label: '', token: '', is_active: true }
        await loadTokenList()
        emit('tokens-updated')
      } else {
        ElMessage.error(res.data?.message || '保存失败')
      }
    } catch (e) {
      ElMessage.error('保存失败: ' + (e.message || e))
    } finally {
      tokenFormSubmitting.value = false
    }
  })
}

// 编辑 Token
function editToken(item) {
  tokenForm.value = {
    id: item.id,
    label: item.label || '',
    token: '',
    is_active: item.is_active,
  }
}

// 删除 Token
async function deleteToken(id) {
  try {
    await ElMessageBox.confirm('确认删除此Token配置？', '提示', { type: 'warning' })
  } catch { return }
  try {
    const res = await deleteYunxiaoToken(id)
    if (res.data?.success) {
      ElMessage.success('删除成功')
      await loadTokenList()
      emit('tokens-updated')
    }
  } catch (e) {
    ElMessage.error('删除失败: ' + (e.message || e))
  }
}

// 切换 Token 启用状态
async function toggleTokenActive(item) {
  try {
    const res = await updateYunxiaoToken(item.id, { is_active: !item.is_active })
    if (res.data?.success) {
      item.is_active = !item.is_active
      emit('tokens-updated')
    }
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.message || e))
  }
}

// 测试 Token
async function testToken(id) {
  tokenTestResults.value[id] = 'loading'
  try {
    const res = await testYunxiaoToken(id)
    if (res.data?.success) {
      tokenTestResults.value[id] = 'success'
      ElMessage.success('Token有效！')
    } else {
      tokenTestResults.value[id] = 'fail'
      ElMessage.error(res.data?.message || 'Token无效')
    }
  } catch (e) {
    tokenTestResults.value[id] = 'fail'
    ElMessage.error('测试失败: ' + (e.message || e))
  }
}
</script>

<style scoped>
.token-manager-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 0 4px;
}

.token-manager-form-section {
  background: #f8f7ff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  padding: 16px;
}

.token-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.list-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #5a32a3;
}

/* ==================== 表格卡片 ==================== */
.token-list-card {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 16px;
  overflow: hidden;
}

/* 表格样式 - 参考 BugSyncManagement 风格 */
.token-list-card :deep(.el-table) {
  --el-table-border-color: rgba(147, 112, 219, 0.1);
  --el-table-header-bg-color: #ffffff;
  --el-table-row-hover-bg-color: #f8f7ff;
  border: none;
  border-radius: 8px;
  overflow: hidden;
  min-height: 200px;
  box-shadow: none;
  transition: all 0.3s ease;
  background-color: transparent !important;
}

.token-list-card :deep(.el-table__header-wrapper) {
  background-color: #ffffff !important;
}

.token-list-card :deep(.el-table__header) {
  background-color: #ffffff !important;
}

.token-list-card :deep(th) {
  background-color: #ffffff !important;
  color: #5a32a3 !important;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid #e9ecef;
  padding: 0 !important;
  text-align: center;
  transition: all 0.3s ease;
}

.token-list-card :deep(th:hover) {
  background-color: #ffffff !important;
}

.token-list-card :deep(th .cell) {
  background-color: #ffffff !important;
  color: #5a32a3 !important;
  font-weight: 600 !important;
  white-space: nowrap !important;
  line-height: 24px !important;
  padding: 16px !important;
}

.token-list-card :deep(.el-table__body-wrapper) {
  background-color: #ffffff !important;
}

.token-list-card :deep(.el-table__row) {
  transition: all 0.3s ease;
  background-color: #ffffff !important;
  line-height: 24px;
}

.token-list-card :deep(.el-table__row:hover) {
  background-color: #f8f7ff !important;
}

.token-list-card :deep(.el-table__row.el-table__row--striped) {
  background-color: #fafaff !important;
}

.token-list-card :deep(td) {
  padding: 14px 16px;
  border-bottom: 1px solid #e9ecef;
  color: #333;
  font-size: 14px;
  font-weight: 400;
  line-height: 24px;
  transition: all 0.3s ease;
  vertical-align: middle;
}

.token-list-card :deep(.el-table__empty-block) {
  padding: 60px 0;
  background: #ffffff !important;
}

.token-list-card :deep(.el-table__empty-text) {
  color: #666;
  font-size: 14px;
  line-height: 24px;
}

/* 时间文本样式 */
.time-text {
  color: #333;
  font-size: 13px;
}

/* 操作按钮样式 */
.action-buttons {
  display: flex;
  gap: 4px;
  justify-content: center;
  align-items: center;
}

.action-buttons .el-button {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px !important;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.action-buttons .el-button--primary {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
  border: none !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

.action-buttons .el-button--primary:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
}

.action-buttons .el-button--danger {
  background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
  border: none !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

.action-buttons .el-button--danger:hover {
  background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
}

.action-buttons .el-button--info {
  background: linear-gradient(135deg, #00b96b 0%, #009a57 100%) !important;
  border: none !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

.action-buttons .el-button--info:hover {
  background: linear-gradient(135deg, #00a862 0%, #008a4d 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 185, 107, 0.4);
}

.action-buttons .el-button--success {
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
  border: none !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

.action-buttons .el-button--success:hover {
  background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
}

/* ==================== 抽屉样式 ==================== */
.token-manager-drawer :deep(.el-drawer__header) {
  background: linear-gradient(135deg, #f8f7ff 0%, #fff 100%);
  border-bottom: 1px solid rgba(147, 112, 219, 0.12);
  margin-bottom: 16px;
  padding: 20px 24px;
}

.token-manager-drawer :deep(.el-drawer__title) {
  color: #5a32a3;
  font-weight: 600;
  font-size: 18px;
}

.token-manager-drawer :deep(.el-drawer__body) {
  padding-top: 0;
  display: flex;
  flex-direction: column;
}

.token-drawer-footer {
  margin-top: auto;
  padding-top: 16px;
}

/* 空状态样式 */
.token-manager-drawer :deep(.el-empty__description p) {
  color: #7b6db3;
}

/* 保存按钮样式 */
.token-drawer-footer .el-button--primary {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
  border: none !important;
  font-weight: 600;
  padding: 10px 24px;
  border-radius: 8px !important;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
}

.token-drawer-footer .el-button--primary:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
}
</style>
