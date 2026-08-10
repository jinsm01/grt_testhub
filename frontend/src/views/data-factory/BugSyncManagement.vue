<template>
  <div class="bug-sync-management">
    <!-- 工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-select v-model="filterTokenId" placeholder="按令牌筛选" clearable filterable style="width: 180px;">
            <el-option
              v-for="token in yunxiaoTokenOptions"
              :key="token.id"
              :label="token.display"
              :value="token.id"
            />
          </el-select>
          <el-select v-model="filterSeverity" placeholder="严重程度" clearable filterable style="width: 120px;">
            <el-option label="1-致命" value="1-致命" />
            <el-option label="2-严重" value="2-严重" />
            <el-option label="3-一般" value="3-一般" />
            <el-option label="4-轻微" value="4-轻微" />
          </el-select>
          <el-select v-model="filterAssignee" placeholder="负责人" clearable filterable style="width: 140px;">
            <el-option
              v-for="item in assigneeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button type="primary" plain class="custom-btn" @click="openCreateBugDialog">
            <el-icon><Plus /></el-icon>
            新建Bug并同步
          </el-button>
          <el-button type="warning" plain class="token-btn" @click="showTokenManager = true">
            <el-icon><Key /></el-icon>
            Token管理
          </el-button>
          <el-button
            class="sync-btn"
            @click="resyncAllBugs" 
            :loading="batchResyncLoading"
            :disabled="bugSyncItemsList.length === 0"
          >
            <el-icon><Refresh /></el-icon>
            <template v-if="batchResyncLoading">
              同步中 ({{ batchResyncProgress }}/{{ batchResyncTotal }})
            </template>
            <template v-else-if="selectedBugItems.length > 0">
              同步选中 ({{ selectedBugItems.length }})
            </template>
            <template v-else>
              一键同步当前页
            </template>
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- Bug同步列表 -->
    <el-card shadow="never" class="table-card">
      <el-table
        ref="bugTableRef"
        v-loading="bugSyncItemsLoading"
        :data="filteredBugSyncItems"
        stripe
        style="width: 100%"
        empty-text=" "
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="云效编号" width="150" header-align="center" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="formatYunxiaoId(row.yunxiao_serial_number, row.yunxiao_workitem_id)" 
                  class="yunxiao-link" 
                  :title="row.local_data?.space_id ? '点击在云效中查看' : '缺少项目ID，无法跳转'"
                  @click="openYunxiaoWorkitem(row.local_data?.space_id, row.yunxiao_workitem_id)">
              {{ formatYunxiaoId(row.yunxiao_serial_number, row.yunxiao_workitem_id).display }}
            </span>
            <el-tag v-else type="info" size="small">未同步</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Bug标题" min-width="280" show-overflow-tooltip header-align="center" align="left">
          <template #default="{ row }">
            <span class="bug-title-text">{{ row.local_data?.title || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="严重程度" width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span
              v-if="row.local_data?.severity"
              :class="['severity-badge', `severity-${getSeverityClass(row.local_data?.severity)}`]"
            >
              {{ row.local_data?.severity }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="90" header-align="center" align="center">
          <template #default="{ row }">
            <span
              v-if="row.local_data?.priority"
              :class="['priority-badge', `priority-${getPriorityClass(row.local_data?.priority)}`]"
            >
              {{ row.local_data?.priority }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <span :class="['status-tag', `status-${getStatusClass(row.local_data?.status)}`]">
              {{ row.local_data?.status || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="所属模块" min-width="120" show-overflow-tooltip header-align="center" align="center">
          <template #default="{ row }">
            <span class="module-text">{{ row.local_data?.module || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="负责人" width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span class="creator-text">{{ getMemberDisplayName(row.local_data?.assignee) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最后同步时间" width="180" header-align="center" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.last_synced_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-dropdown
                v-if="row.local_data?.status === '已修复'"
                trigger="click"
                placement="bottom-start"
                @command="(cmd) => openQuickChangeDialog(row, cmd)"
              >
                <el-button size="small" type="success" plain>
                  改状态<el-icon class="el-icon--right"><CaretBottom /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="已验证">标记为「已验证」</el-dropdown-item>
                    <el-dropdown-item command="已关闭">标记为「已关闭」</el-dropdown-item>
                    <el-dropdown-item command="再次打开">标记为「再次打开」</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button
                size="small"
                type="primary"
                @click="editBugSyncItem(row)"
              >
                <el-icon><Edit /></el-icon>
                <span>编辑</span>
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="handleDeleteBugSyncItem(row)"
              >
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container" v-if="!bugSyncItemsLoading && total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新建/编辑Bug对话框 -->
    <el-drawer
      v-model="showBugDialog"
      :title="bugDialogMode === 'create' ? '新建Bug' : '编辑Bug'"
      direction="rtl"
      size="820px"
      :close-on-click-modal="false"
      @closed="onBugDrawerClosed"
    >
      <el-form
        ref="bugFormRef"
        :model="bugForm"
        :rules="bugFormRules"
        label-width="100px"
      >
        <el-form-item label="访问令牌" prop="token_id" required>
          <el-select
            v-model="bugForm.token_id"
            placeholder="Token管理添加自己的云效令牌，后选择自己的令牌"
            filterable
            clearable
            style="width: 100%;"
            :disabled="bugDialogMode === 'edit'"
            @change="onBugFormTokenChange"
          >
            <el-option
              v-for="opt in yunxiaoTokenOptions"
              :key="opt.id"
              :label="opt.display"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="bugDialogMode !== 'edit'" label="项目">
          <el-input model-value="学习公社6.0" disabled style="width: 100%;" />
        </el-form-item>
        <el-form-item v-if="bugDialogMode !== 'edit'" label="迭代" prop="sprint_id" required>
          <el-select
            v-model="bugForm.sprint_id"
            placeholder="选择迭代"
            filterable
            clearable
            style="width: 100%;"
            :disabled="!bugForm.space_id"
            :loading="bugFormSprintLoading"
          >
            <el-option
              v-for="s in bugFormSprints"
              :key="s.id"
              :label="s.name || s.title"
              :value="s.id"
            />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">
          <span style="font-size: 13px; color: #909399;">Bug 信息</span>
        </el-divider>

        <el-form-item label="所属模块" prop="module" required>
          <el-select
            v-model="bugForm.module"
            placeholder="选择模块/标签"
            filterable
            clearable
            allow-create
            default-first-option
            style="width: 100%;"
            :disabled="!bugForm.space_id"
            :loading="bugFormLabelLoading"
            @visible-change="(visible) => { if (visible && bugFormLabels.length === 0) searchBugFormLabels() }"
          >
            <el-option
              v-for="label in bugFormLabels"
              :key="label.id || label.name"
              :label="label.name"
              :value="label.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="严重程度" prop="severity">
          <el-select v-model="bugForm.severity" placeholder="选择严重程度" filterable clearable style="width: 100%;">
            <el-option label="1-致命" value="1-致命" />
            <el-option label="2-严重" value="2-严重" />
            <el-option label="3-一般" value="3-一般" />
            <el-option label="4-轻微" value="4-轻微" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="bugForm.priority" placeholder="选择优先级" filterable clearable style="width: 100%;">
            <el-option label="紧急" value="紧急" />
            <el-option label="高" value="高" />
            <el-option label="中" value="中" />
            <el-option label="低" value="低" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人" prop="assignee" required>
          <el-select
            v-model="bugForm.assignee"
            placeholder="选择负责人"
            filterable
            clearable
            style="width: 100%;"
            :disabled="!bugForm.space_id"
            :loading="bugFormMemberLoading"
            @visible-change="(visible) => { if (visible && bugFormMembers.length === 0) searchBugFormMembers() }"
          >
            <el-option
              v-for="member in bugFormMembers"
              :key="member.userId || member.id"
              :label="member.displayName || member.userName || member.name"
              :value="member.userId || member.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" prop="title" required>
          <el-input v-model="bugForm.title" placeholder="请输入Bug标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="描述" prop="desc" required>
          <div class="desc-toolbar">
            <span class="desc-toolbar-label">快捷插入：</span>
            <el-tag
              v-for="tag in descTemplateTags"
              :key="tag"
              size="small"
              effect="plain"
              class="desc-template-tag"
              @click="insertDescTag(tag)"
            >
              {{ tag }}
            </el-tag>
            <el-button
              size="small"
              text
              type="primary"
              @click="fillDescTemplate"
            >
              填入完整模板
            </el-button>
          </div>
          <el-input
            v-model="bugForm.desc"
            type="textarea"
            :rows="10"
            placeholder="请输入Bug描述，支持粘贴图片自动上传"
            maxlength="2000"
            show-word-limit
            @paste="handleDescPaste"
            ref="descTextareaRef"
          />
          <div v-if="pendingAttachments.length > 0" style="margin-top: 8px;">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px;">
              待上传附件 ({{ pendingAttachments.length }})：
            </div>
            <div class="pending-attachments">
              <div
                v-for="(file, index) in pendingAttachments"
                :key="index"
                class="pending-file-item"
              >
                <el-icon class="file-icon"><Document /></el-icon>
                <span class="file-name" :title="file.name">{{ file.name }}</span>
                <span class="file-size">({{ formatFileSize(file.size) }})</span>
                <el-tag
                  v-if="file.uploading"
                  size="small"
                  type="warning"
                  style="margin-left: 8px;"
                >上传中...</el-tag>
                <el-button
                  type="danger"
                  link
                  size="small"
                  @click="removePendingAttachment(index)"
                  :disabled="file.uploading"
                >删除</el-button>
              </div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="附件">
          <el-upload
            ref="bugFormUploadRef"
            :auto-upload="false"
            :on-change="handleFileChange"
            :file-list="uploadFileList"
            :show-file-list="false"
            multiple
            :accept="imageAccept + ',' + videoAccept + ',*/*'"
          >
            <el-button type="primary" plain size="small">
              <el-icon><Upload /></el-icon>
              选择附件（支持图片/视频/文档）
            </el-button>
            <template #tip>
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                支持jpg/png/gif等图片、mp4视频、pdf/word等文档，单个文件不超过50MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <div style="text-align: right;">
          <el-button @click="showBugDialog = false">取消</el-button>
          <el-button type="primary" :loading="bugFormSubmitting" @click="submitBugForm">
            {{ bugDialogMode === 'create' ? '创建并同步到云效' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-drawer>

    <!-- Token 管理抽屉 -->
    <TokenManagerDrawer v-model="showTokenManager" @tokens-updated="loadTokenOptions" />

    <!-- 快捷改状态弹窗 -->
    <el-dialog
      v-model="quickChangeVisible"
      :title="`快捷改状态 → ${quickChangeData.targetStatus}`"
      width="480px"
      :close-on-click-modal="false"
    >
      <div class="quick-change-info">
        <span>Bug：{{ quickChangeData.row?.local_data?.title || '' }}</span>
      </div>
      <el-form label-width="80px" style="margin-top: 16px;">
        <el-form-item label="截图">
          <el-upload
            :auto-upload="false"
            :on-change="handleQuickScreenshotChange"
            :file-list="quickScreenshotList"
            :show-file-list="true"
            :limit="1"
            accept="image/*"
          >
            <el-button type="primary" plain size="small">
              <el-icon><Upload /></el-icon>
              选择验证截图
            </el-button>
            <template #tip>
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                支持jpg/png等图片，截图将上传到云效评论作为验证凭证
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="quickChangeData.comment"
            type="textarea"
            :rows="2"
            placeholder="可选，输入验证说明"
            maxlength="200"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quickChangeVisible = false">取消</el-button>
        <el-button type="primary" :loading="quickChangeLoading" @click="submitQuickChange">
          确认改状态
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Link, Edit, Delete, Document, Upload, Search, Key, CaretBottom } from '@element-plus/icons-vue'
import {
  getBugSyncItems,
  createBugToYunxiao,
  updateBugToYunxiao,
  quickChangeBugStatus,
  deleteBugSyncItem as deleteBugSyncItemApi,
  resyncBugItem as resyncBugItemApi,
  getYunxiaoTokenOptions,
  getYunxiaoProjects,
  getYunxiaoSprints,
  getYunxiaoMembers,
  getYunxiaoLabels
} from '@/api/data-factory'
import TokenManagerDrawer from './TokenManagerDrawer.vue'

// ============ 数据 ============
const bugSyncItemsList = ref([])
const bugSyncItemsLoading = ref(true)
const filterTokenId = ref('')
const filterSeverity = ref('')
const filterAssignee = ref('')

// 快捷改状态弹窗
const quickChangeVisible = ref(false)
const quickChangeLoading = ref(false)
const quickChangeData = reactive({
  row: null,
  targetStatus: '',
  comment: '',
})
const quickScreenshotList = ref([])
const quickScreenshotFile = ref(null)

// Token 管理抽屉
const showTokenManager = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 成员映射 (userId -> 显示名称)
const memberMap = ref(new Map())

// ============ 统计 ============
const syncedCount = computed(() => bugSyncItemsList.value.filter(i => i.sync_status === 'synced').length)
const failedCount = computed(() => bugSyncItemsList.value.filter(i => i.sync_status === 'failed').length)
const pendingCount = computed(() => bugSyncItemsList.value.filter(i => i.sync_status === 'pending').length)

// ============ 过滤后的列表（含分页）============
// 处理人选项（从列表数据中收集唯一处理人）
const assigneeOptions = computed(() => {
  const names = new Set()
  for (const item of bugSyncItemsList.value) {
    const assignee = item.local_data?.assignee
    if (assignee) {
      const displayName = memberMap.value.get(assignee) || assignee
      names.add(displayName)
    }
  }
  return Array.from(names).map(name => ({ value: name, label: name }))
})

const filteredBugSyncItems = computed(() => {
  let list = bugSyncItemsList.value
  // 按令牌筛选
  if (filterTokenId.value) {
    list = list.filter(i => String(i.local_data?.token_id) === String(filterTokenId.value))
  }
  if (filterSeverity.value) {
    list = list.filter(i => i.local_data?.severity === filterSeverity.value)
  }
  // 按处理人筛选（按显示名称匹配）
  if (filterAssignee.value) {
    list = list.filter(i => {
      const assignee = i.local_data?.assignee
      if (!assignee) return false
      const displayName = memberMap.value.get(assignee) || assignee
      return displayName === filterAssignee.value
    })
  }
  total.value = list.length
  // 按 created_at 倒序排序（最新的排前面）
  list = [...list].sort((a, b) => {
    const ta = a.created_at ? new Date(a.created_at).getTime() : 0
    const tb = b.created_at ? new Date(b.created_at).getTime() : 0
    return tb - ta
  })
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return list.slice(start, end)
})

// 分页处理
function handleSizeChange(val) {
  pageSize.value = val
  currentPage.value = 1
}

function handleCurrentChange(val) {
  currentPage.value = val
}

// ============ 新建/编辑对话框 ============
const showBugDialog = ref(false)
const bugDialogMode = ref('create')
const bugFormRef = ref(null)
const descTextareaRef = ref(null)
const bugFormSubmitting = ref(false)

const defaultBugForm = () => ({
  title: '',
  desc: '',
  severity: '3-一般',
  priority: '中',
  status: '待确认',
  module: '',
  assignee: '',
  token_id: null,
  space_id: '',
  sprint_id: '',
  sync_item_id: null
})

const bugForm = ref(defaultBugForm())

const bugFormRules = {
  title: [{ required: true, message: '请输入Bug标题', trigger: 'blur' }],
  severity: [{ required: true, message: '请选择严重程度', trigger: 'change' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  token_id: [{ required: true, message: '请选择访问令牌', trigger: 'change' }],
  space_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
  module: [{ required: true, message: '请选择所属模块', trigger: 'change' }],
  sprint_id: [{ required: true, message: '请选择迭代', trigger: 'change' }],
  desc: [{ required: true, message: '请输入Bug描述', trigger: 'blur' }],
  assignee: [{ required: true, message: '请选择负责人', trigger: 'change' }]
}

// ============ 表单相关数据 ============
const yunxiaoTokenOptions = ref([])
const bugFormProjects = ref([])
const bugFormSprints = ref([])
const bugFormMembers = ref([])
const bugFormLabels = ref([])
const bugFormProjectLoading = ref(false)
const bugFormSprintLoading = ref(false)
const bugFormMemberLoading = ref(false)
const bugFormLabelLoading = ref(false)

// ============ 附件上传 ============
const imageAccept = '.jpg,.jpeg,.png,.gif,.bmp,.webp'
const videoAccept = '.mp4,.mov,.avi,.wmv,.flv'
const pendingAttachments = ref([])
const uploadFileList = ref([])

// 批量同步状态
const batchResyncLoading = ref(false)
const batchResyncProgress = ref(0)
const batchResyncTotal = ref(0)

// 表格选中项
const bugTableRef = ref(null)
const selectedBugItems = ref([])

function handleSelectionChange(selection) {
  selectedBugItems.value = selection
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function addPendingFile(file) {
  // 检查文件大小 50MB
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.warning(`文件 ${file.name} 超过50MB限制`)
    return
  }
  pendingAttachments.value.push(file)
}

function handleFileChange(uploadFile) {
  if (uploadFile && uploadFile.raw) {
    addPendingFile(uploadFile.raw)
  }
}

function handleDescPaste(event) {
  // 处理粘贴图片
  const items = event.clipboardData?.items
  if (!items) return
  
  for (let i = 0; i < items.length; i++) {
    if (items[i].type.startsWith('image/')) {
      const file = items[i].getAsFile()
      if (file) {
        event.preventDefault()
        // 给粘贴的图片一个有意义的名称
        const ext = file.type.split('/')[1] || 'png'
        const pastedFile = new File([file], `pasted-image-${Date.now()}.${ext}`, { type: file.type })
        addPendingFile(pastedFile)
        ElMessage.success(`图片已添加到待上传列表，提交后将自动插入描述末尾`)
      }
    }
  }
}

function removePendingAttachment(index) {
  pendingAttachments.value.splice(index, 1)
}

function clearPendingAttachments() {
  pendingAttachments.value = []
  uploadFileList.value = []
}

// ============ 描述模板 ============
const descTemplateTags = ['【前置条件】', '【操作步骤】', '【预期结果】', '【实际结果】', '【复现概率】']

function insertDescTag(tag) {
  const textarea = descTextareaRef.value?.$el?.querySelector('textarea') || descTextareaRef.value?.textarea
  if (!textarea) {
    // fallback: 直接追加到末尾
    const sep = bugForm.value.desc && !bugForm.value.desc.endsWith('\n') ? '\n' : ''
    bugForm.value.desc = (bugForm.value.desc || '') + sep + tag + '\n'
    return
  }
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const val = bugForm.value.desc || ''
  // 在光标位置插入标签+换行
  const insertText = tag + '\n'
  bugForm.value.desc = val.slice(0, start) + insertText + val.slice(end)
  // 移动光标到插入内容之后
  nextTick(() => {
    const pos = start + insertText.length
    textarea.focus()
    textarea.setSelectionRange(pos, pos)
  })
}

function fillDescTemplate() {
  bugForm.value.desc = [
    '【前置条件】',
    '',
    '【操作步骤】',
    '1. ',
    '2. ',
    '3. ',
    '',
    '【预期结果】',
    '详见附件需求截图',
    '',
    '【实际结果】',
    '详见附件问题视频截图',
    ''
  ].join('\n')
  nextTick(() => {
    const textarea = descTextareaRef.value?.$el?.querySelector('textarea') || descTextareaRef.value?.textarea
    if (textarea) {
      textarea.focus()
      textarea.setSelectionRange(0, 0)
    }
  })
}

/**
 * 清理描述中的markdown图片/附件链接
 * 移除 ![alt](url) 格式的markdown图片，以及可能存在的纯附件URL
 * 图片和附件已经通过附件字段管理，不需要在纯文本描述中显示链接
 */
function cleanDescription(desc) {
  if (!desc) return ''
  // 移除markdown图片语法 ![...](url)
  let cleaned = desc.replace(/!\[.*?\]\(https?:\/\/[^\s)]+\)/g, '')
  // 移除可能单独存在的云效附件URL行（只包含URL的行）
  cleaned = cleaned.replace(/^\s*\(https?:\/\/[^\s)]+\)\s*$/gm, '')
  // 清理多余空行（连续2个以上空行变成1个）
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n')
  return cleaned.trim()
}

// ============ 工具方法 ============
// 云效网页版域名
const YUNXIAO_WEB_DOMAIN = 'https://devops.aliyun.com'

function getYunxiaoWorkitemUrl(spaceId, workitemId) {
  // 云效Bug详情页URL格式: https://devops.aliyun.com/projex/project/{spaceId}/bug/{workitemId}
  if (!spaceId || !workitemId) return ''
  return `${YUNXIAO_WEB_DOMAIN}/projex/project/${spaceId}/bug/${workitemId}`
}

function openYunxiaoWorkitem(spaceId, workitemId) {
  const url = getYunxiaoWorkitemUrl(spaceId, workitemId)
  if (!url) {
    ElMessage.warning('缺少项目ID或工作项ID，无法跳转')
    return
  }
  window.open(url, '_blank')
}

function getMemberDisplayName(userId) {
  if (!userId) return '-'
  return memberMap.value.get(userId) || userId
}

function formatYunxiaoId(serialNumber, workitemId) {
  // 优先显示序列号（格式如 XXSIX-4011）
  if (serialNumber) {
    // 判断是否是短编号格式（包含"-"且长度小于20）
    if (serialNumber.includes('-') && serialNumber.length < 30) {
      return { display: serialNumber, tooltip: serialNumber, isFull: true }
    }
    // 如果是长ID（如UUID），截断显示
    return { display: serialNumber.substring(0, 8) + '...', tooltip: serialNumber, isFull: false }
  }
  // 没有序列号，使用workitem_id
  if (workitemId) {
    return { display: workitemId.substring(0, 8) + '...', tooltip: workitemId, isFull: false }
  }
  return null
}

async function loadMemberMap() {
  // 尝试从第一个有效Token加载所有项目的成员
  if (!yunxiaoTokenOptions.value.length) {
    console.warn('[BugSyncManagement] loadMemberMap: no token options')
    return
  }
  const tokenId = yunxiaoTokenOptions.value[0]?.id
  if (!tokenId) {
    console.warn('[BugSyncManagement] loadMemberMap: no token ID')
    return
  }
  
  try {
    // 尝试从BugSyncItem中收集所有space_id，然后加载成员
    const spaceIds = [...new Set(bugSyncItemsList.value
      .map(item => item.local_data?.space_id)
      .filter(Boolean))]
    
    console.log('[BugSyncManagement] loadMemberMap: spaceIds=', spaceIds, 'tokenId=', tokenId)
    
    for (const spaceId of spaceIds) {
      try {
        const res = await getYunxiaoMembers({
          token_id: tokenId,
          space_id: spaceId,
        })
        console.log('[BugSyncManagement] members response for space', spaceId, ':', res.data)
        if (res.data?.success && res.data.items) {
          for (const member of res.data.items) {
            const userId = member.userId || member.id
            const displayName = member.displayName || member.userName || member.name || userId
            if (userId) {
              memberMap.value.set(userId, displayName)
            }
          }
        }
      } catch (e) {
        console.warn('[BugSyncManagement] loadMemberMap error for space', spaceId, ':', e)
      }
    }
    console.log('[BugSyncManagement] memberMap size:', memberMap.value.size)
  } catch (e) {
    console.warn('[BugSyncManagement] loadMemberMap error:', e)
  }
}

function getSeverityTagType(severity) {
  const map = { P0: 'danger', P1: 'danger', P2: 'warning', P3: 'info' }
  return map[severity] || ''
}

function getPriorityTagType(priority) {
  const map = { '高': 'danger', '中': 'warning', '低': 'info' }
  return map[priority] || ''
}

function getSyncStatusTagType(status) {
  const map = { synced: 'success', failed: 'danger', pending: 'warning' }
  return map[status] || 'info'
}

function getSyncStatusText(status) {
  const map = { synced: '已同步', failed: '同步失败', pending: '待同步' }
  return map[status] || status || '-'
}

function getPriorityClass(priority) {
  // 将优先级转换为class名称
  const map = { '高': 'high', '中': 'medium', '低': 'low', '紧急': 'high' }
  return map[priority] || 'medium'
}

function getSeverityClass(severity) {
  // 将严重程度转换为class名称，兼容云效格式和旧P等级格式
  if (!severity) return ''
  if (severity.startsWith('1-') || severity === 'P0' || severity === '致命') return 's1'
  if (severity.startsWith('2-') || severity === 'P1' || severity === '严重') return 's2'
  if (severity.startsWith('3-') || severity === 'P2' || severity === '一般') return 's3'
  if (severity.startsWith('4-') || severity === 'P3' || severity === '轻微') return 's4'
  return 's3'
}

function getStatusClass(status) {
  // 将状态转换为class名称
  if (!status) return ''
  const statusLower = status.toLowerCase()
  const map = {
    '新建': 'new',
    'new': 'new',
    '处理中': 'processing',
    'processing': 'processing',
    'in-progress': 'in-progress',
    '待确认': 'pending',
    'pending': 'pending',
    '已解决': 'resolved',
    'resolved': 'resolved',
    '已修复': 'fixed',
    'fixed': 'fixed',
    '已验证': 'verified',
    'verified': 'verified',
    '已关闭': 'closed',
    'closed': 'closed',
    'done': 'done',
    '已完成': 'done',
    '已拒绝': 'rejected',
    '不予解决': 'rejected',
    '暂不修复': 'wontfix',
    'rejected': 'rejected',
    '重新打开': 'reopened',
    '再次打开': 'reopened',
    'reopened': 'reopened'
  }
  return map[status] || map[statusLower] || ''
}

function formatDateTime(dt) {
  if (!dt || dt === '-') return '-'
  const pad = (n) => String(n).padStart(2, '0')
  // 如果已经是格式化的字符串（如 "2024-01-08 15:24:30"），直接返回
  if (typeof dt === 'string') {
    // 匹配 "2024-01-08 15:24:30" 格式
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(dt)) {
      return dt
    }
    // 匹配 "2024-01-08 15:24:30.xxx" 格式（带微秒）
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(dt)) {
      return dt.substring(0, 19)
    }
    // 尝试解析其他格式
    try {
      const d = new Date(dt)
      if (!isNaN(d.getTime())) {
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
      }
    } catch { /* ignore */ }
    return dt
  }
  // 如果是其他类型，尝试解析
  try {
    const d = new Date(dt)
    if (!isNaN(d.getTime())) {
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    }
  } catch { /* ignore */ }
  return String(dt)
}

// ============ 数据加载 ============
async function loadBugSyncItems() {
  bugSyncItemsLoading.value = true
  try {
    const res = await getBugSyncItems()
    if (res.data?.success) {
      bugSyncItemsList.value = res.data.items || []
      // 加载成员映射以正确显示处理人姓名
      await loadMemberMap()
    }
  } catch (e) {
    ElMessage.error('加载同步列表失败')
  } finally {
    bugSyncItemsLoading.value = false
  }
}

async function loadTokenOptions() {
  try {
    const res = await getYunxiaoTokenOptions()
    if (res.data?.success) {
      yunxiaoTokenOptions.value = res.data.options || []
    }
  } catch { /* ignore */ }
}

async function loadBugFormProjects() {
  if (!bugForm.value.token_id) return
  bugFormProjectLoading.value = true
  try {
    const res = await getYunxiaoProjects({
      token_id: bugForm.value.token_id,
      keyword: '',
      page: 1,
      per_page: 50,
    })
    if (res.data?.success) {
      bugFormProjects.value = res.data.items || []
    }
  } catch { /* ignore */ }
  finally {
    bugFormProjectLoading.value = false
  }
}

async function searchBugFormProjects(keyword) {
  if (!bugForm.value.token_id) return
  bugFormProjectLoading.value = true
  try {
    const res = await getYunxiaoProjects({
      token_id: bugForm.value.token_id,
      keyword: keyword || '',
      page: 1,
      per_page: 50,
    })
    if (res.data?.success) {
      bugFormProjects.value = res.data.items || []
    }
  } catch { /* ignore */ }
  finally {
    bugFormProjectLoading.value = false
  }
}

async function onBugFormTokenChange() {
  bugFormProjects.value = []
  bugFormSprints.value = []
  bugFormMembers.value = []
  bugFormLabels.value = []
  bugForm.value.space_id = ''
  bugForm.value.sprint_id = ''
  bugForm.value.assignee = ''
  await loadBugFormProjects()
  // 项目写死为"学习公社6.0"，从项目列表中按名称匹配
  const targetProject = bugFormProjects.value.find(p => p.name === '学习公社6.0')
  if (targetProject) {
    bugForm.value.space_id = targetProject.id
    await onBugFormProjectChange(bugForm.value.space_id)
  }
}

async function onBugFormProjectChange(spaceId, preserveFormValues = false) {
  console.log('[onBugFormProjectChange] spaceId:', spaceId, 'preserveFormValues:', preserveFormValues)
  console.log('[onBugFormProjectChange] token_id:', bugForm.value.token_id)
  if (!bugForm.value.token_id || !spaceId) {
    console.warn('[onBugFormProjectChange] Missing token_id or spaceId, skipping')
    return
  }
  
  bugFormSprintLoading.value = true
  bugFormMemberLoading.value = true
  bugFormLabelLoading.value = true
  bugFormSprints.value = []
  bugFormMembers.value = []
  bugFormLabels.value = []
  // 仅在非编辑模式下清空表单值
  if (!preserveFormValues) {
    bugForm.value.sprint_id = ''
    bugForm.value.assignee = ''
    bugForm.value.module = ''
  }

  try {
    console.log('[onBugFormProjectChange] Calling API...')
    const [sprintsRes, membersRes, labelsRes] = await Promise.all([
      getYunxiaoSprints({
        token_id: bugForm.value.token_id,
        space_id: spaceId,
      }).catch((err) => {
        console.error('[onBugFormProjectChange] getSprints error:', err)
        return { data: { success: false, items: [] } }
      }),
      getYunxiaoMembers({
        token_id: bugForm.value.token_id,
        space_id: spaceId,
      }).catch((err) => {
        console.error('[onBugFormProjectChange] getMembers error:', err)
        return { data: { success: false, items: [] } }
      }),
      getYunxiaoLabels({
        token_id: bugForm.value.token_id,
        space_id: spaceId,
      }).catch((err) => {
        console.error('[onBugFormProjectChange] getLabels error:', err)
        return { data: { success: false, items: [] } }
      }),
    ])

    console.log('[onBugFormProjectChange] sprintsRes:', sprintsRes.data)
    console.log('[onBugFormProjectChange] membersRes:', membersRes.data)
    console.log('[onBugFormProjectChange] labelsRes:', labelsRes.data)
    
    if (sprintsRes.data?.success) {
      bugFormSprints.value = sprintsRes.data.items || []
    }
    if (membersRes.data?.success) {
      bugFormMembers.value = membersRes.data.items || []
    }
    if (labelsRes.data?.success) {
      bugFormLabels.value = labelsRes.data.items || []
    }
    console.log('[onBugFormProjectChange] Loaded:', {
      sprints: bugFormSprints.value.length,
      members: bugFormMembers.value.length,
      labels: bugFormLabels.value.length
    })
  } catch (err) {
    console.error('[onBugFormProjectChange] Error:', err)
  }
  finally {
    bugFormSprintLoading.value = false
    bugFormMemberLoading.value = false
    bugFormLabelLoading.value = false
  }
}

async function searchBugFormLabels() {
  if (!bugForm.value.token_id || !bugForm.value.space_id) return
  bugFormLabelLoading.value = true
  try {
    const res = await getYunxiaoLabels({
      token_id: bugForm.value.token_id,
      space_id: bugForm.value.space_id,
    })
    if (res.data?.success) {
      bugFormLabels.value = res.data.items || []
    }
  } catch { /* ignore */ }
  finally {
    bugFormLabelLoading.value = false
  }
}

async function searchBugFormMembers() {
  if (!bugForm.value.token_id || !bugForm.value.space_id) return
  bugFormMemberLoading.value = true
  try {
    const res = await getYunxiaoMembers({
      token_id: bugForm.value.token_id,
      space_id: bugForm.value.space_id,
    })
    if (res.data?.success) {
      bugFormMembers.value = res.data.items || []
    }
  } catch { /* ignore */ }
  finally {
    bugFormMemberLoading.value = false
  }
}

// ============ 对话框操作 ============
function openCreateBugDialog() {
  bugDialogMode.value = 'create'
  bugForm.value = defaultBugForm()
  bugFormProjects.value = []
  bugFormSprints.value = []
  bugFormMembers.value = []
  bugFormLabels.value = []
  clearPendingAttachments()
  showBugDialog.value = true
}

function onBugDrawerClosed() {
  // 抽屉关闭动画结束后清除表单验证状态
  bugFormRef.value?.clearValidate()
}

function editBugSyncItem(row) {
  if (!row) return
  bugDialogMode.value = 'edit'
  bugForm.value = {
    title: row.local_data?.title || '',
    desc: cleanDescription(row.local_data?.desc),
    severity: row.local_data?.severity || '3-一般',
    priority: row.local_data?.priority || '中',
    status: row.local_data?.status || '待确认',
    module: row.local_data?.module || '',
    assignee: row.local_data?.assignee || '',
    token_id: row.local_data?.token_id || null,
    space_id: row.local_data?.space_id || '',
    sprint_id: row.local_data?.sprint_id || '',
    sync_item_id: row.id
  }
  clearPendingAttachments()
  showBugDialog.value = true
  // 编辑模式下，令牌禁用、项目和迭代隐藏，只需加载成员和标签列表
  console.log('[editBugSyncItem] token_id:', bugForm.value.token_id, 'space_id:', bugForm.value.space_id)
  console.log('[editBugSyncItem] yunxiaoTokenOptions:', yunxiaoTokenOptions.value)
  if (bugForm.value.token_id && bugForm.value.space_id) {
    onBugFormProjectChange(bugForm.value.space_id, true)
  }
}

// 快捷改状态：从「已修复」改为「已验证」或「已关闭」
// ============ 快捷改状态 ============
function openQuickChangeDialog(row, targetStatus) {
  quickChangeData.row = row
  quickChangeData.targetStatus = targetStatus
  quickChangeData.comment = ''
  quickScreenshotList.value = []
  quickScreenshotFile.value = null
  quickChangeVisible.value = true
}

function handleQuickScreenshotChange(file) {
  quickScreenshotFile.value = file.raw
  quickScreenshotList.value = [file]
}

async function submitQuickChange() {
  const row = quickChangeData.row
  if (!row) return

  quickChangeLoading.value = true
  try {
    const formData = new FormData()
    formData.append('token_id', row.local_data?.token_id || '')
    formData.append('status', quickChangeData.targetStatus)
    if (quickChangeData.comment) {
      formData.append('comment', quickChangeData.comment)
    }
    if (quickScreenshotFile.value) {
      formData.append('screenshot', quickScreenshotFile.value)
    }

    const res = await quickChangeBugStatus(row.id, formData)
    if (res.data?.success) {
      ElMessage.success(res.data.message || `状态已更新为「${quickChangeData.targetStatus}」`)
      quickChangeVisible.value = false
      loadBugSyncItems()
    } else {
      ElMessage.error(res.data?.message || '状态更新失败')
    }
  } catch (e) {
    const errorMsg = e?.response?.data?.error || e?.response?.data?.message || e?.message || String(e)
    ElMessage.error('状态更新失败: ' + errorMsg)
  } finally {
    quickChangeLoading.value = false
  }
}

async function reSyncBug(row) {
  if (!row?.id) return
  try {
    await ElMessageBox.confirm(
      `确定要重新同步Bug「${row.local_data?.title || row.id}」吗？将从云效获取最新信息（包括云效编号）。`,
      '重新同步',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info',
      }
    )
    
    const res = await resyncBugItemApi(row.id)
    if (res.data?.success) {
      ElMessage.success(res.data.message || '重新同步成功')
      // 刷新列表
      loadBugSyncItems()
    } else {
      ElMessage.error(res.data?.message || '重新同步失败')
    }
  } catch (err) {
    if (err !== 'cancel' && err?.response) {
      ElMessage.error(err.response?.data?.message || '重新同步失败')
    }
  }
}

/**
 * 一键同步
 * - 如果有勾选，只同步勾选的
 * - 如果没有勾选，同步当前页所有已同步过的Bug
 */
async function resyncAllBugs() {
  // 确定要同步的列表
  let itemsToSync
  if (selectedBugItems.value.length > 0) {
    itemsToSync = selectedBugItems.value.filter(item => item.yunxiao_workitem_id)
  } else {
    itemsToSync = filteredBugSyncItems.value.filter(item => item.yunxiao_workitem_id)
  }
  
  if (itemsToSync.length === 0) {
    ElMessage.warning(selectedBugItems.value.length > 0 ? '选中的Bug都还未同步到云效' : '当前页没有需要同步的Bug（尚未同步到云效）')
    return
  }
  
  const syncMode = selectedBugItems.value.length > 0 ? '选中' : '当前页'
  
  try {
    await ElMessageBox.confirm(
      `确定要重新同步${syncMode} ${itemsToSync.length} 个Bug吗？将从云效获取最新信息。`,
      '同步确认',
      {
        confirmButtonText: '开始同步',
        cancelButtonText: '取消',
        type: 'info',
      }
    )
  } catch {
    return
  }
  
  batchResyncLoading.value = true
  batchResyncTotal.value = itemsToSync.length
  batchResyncProgress.value = 0
  
  let successCount = 0
  let failCount = 0
  const errors = []
  
  for (let i = 0; i < itemsToSync.length; i++) {
    const item = itemsToSync[i]
    batchResyncProgress.value = i + 1
    try {
      await resyncBugItemApi(item.id)
      successCount++
    } catch (err) {
      failCount++
      const title = item.local_data?.title || item.yunxiao_workitem_id || item.id
      errors.push(`${title}: ${err?.response?.data?.message || err.message || '失败'}`)
    }
    // 稍微延迟避免请求过快
    if (i < itemsToSync.length - 1) {
      await new Promise(resolve => setTimeout(resolve, 200))
    }
  }
  
  batchResyncLoading.value = false
  
  // 清空选中
  if (bugTableRef.value) {
    bugTableRef.value.clearSelection()
  }
  selectedBugItems.value = []
  
  // 刷新列表
  loadBugSyncItems()
  
  // 显示结果
  if (failCount === 0) {
    ElMessage.success(`同步完成！共成功 ${successCount} 个Bug`)
  } else {
    ElMessageBox.alert(
      `同步完成：成功 ${successCount} 个，失败 ${failCount} 个\n\n失败列表：\n${errors.slice(0, 10).join('\n')}${errors.length > 10 ? '\n...' : ''}`,
      '同步结果',
      { type: 'warning' }
    )
  }
}

async function handleDeleteBugSyncItem(row) {
  if (!row?.id) return
  try {
    await ElMessageBox.confirm(
      `确定要删除Bug「${row.local_data?.title || row.id}」的同步记录吗？此操作不会删除云效上的Bug。`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    const res = await deleteBugSyncItemApi(row.id)
    if (res.data?.success) {
      ElMessage.success('删除成功')
      loadBugSyncItems()
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.error || e?.message || '删除失败')
    }
  }
}

async function submitBugForm() {
  if (!bugFormRef.value) return
  try {
    await bugFormRef.value.validate()
  } catch {
    return
  }
  bugFormSubmitting.value = true
  try {
    let res
    if (bugDialogMode.value === 'create') {
      // 创建模式：使用FormData支持文件上传
      const formData = new FormData()
      formData.append('token_id', bugForm.value.token_id)
      formData.append('space_id', bugForm.value.space_id)
      if (bugForm.value.sprint_id) formData.append('sprint_id', bugForm.value.sprint_id)
      formData.append('title', bugForm.value.title)
      formData.append('desc', bugForm.value.desc)
      formData.append('severity', bugForm.value.severity)
      formData.append('priority', bugForm.value.priority)
      formData.append('status', bugForm.value.status)
      if (bugForm.value.module) formData.append('module', bugForm.value.module)
      if (bugForm.value.assignee) formData.append('assignee', bugForm.value.assignee)
      
      // 添加附件
      pendingAttachments.value.forEach((file, index) => {
        formData.append(`attachment_${index}`, file)
      })
      
      res = await createBugToYunxiao(formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    } else {
      // 编辑模式：暂不支持附件，使用JSON
      const payload = {
        token_id: bugForm.value.token_id,
        space_id: bugForm.value.space_id,
        sprint_id: bugForm.value.sprint_id || undefined,
        title: bugForm.value.title,
        desc: bugForm.value.desc,
        severity: bugForm.value.severity,
        priority: bugForm.value.priority,
        status: bugForm.value.status,
        module: bugForm.value.module || undefined,
        assignee: bugForm.value.assignee || undefined,
      }
      res = await updateBugToYunxiao(bugForm.value.sync_item_id, payload)
    }
    if (res.data?.success) {
      ElMessage.success(res.data.message || '同步成功')
      showBugDialog.value = false
      clearPendingAttachments()
      loadBugSyncItems()
    } else {
      ElMessage.error(res.data?.message || '同步失败')
    }
  } catch (e) {
    const errorMsg = e?.response?.data?.error || e?.response?.data?.message || e?.message || String(e)
    ElMessage.error('同步失败: ' + errorMsg)
  } finally {
    bugFormSubmitting.value = false
  }
}

// ============ 监听表单变化 ============
watch(() => bugForm.value.token_id, async (newTokenId) => {
  // 编辑模式下不处理（由 editBugSyncItem 手动加载）
  if (bugDialogMode.value === 'edit') {
    return
  }
  // 创建模式下清空所有关联字段并重新加载
  bugFormProjects.value = []
  bugFormSprints.value = []
  bugFormMembers.value = []
  bugFormLabels.value = []
  bugForm.value.space_id = ''
  bugForm.value.sprint_id = ''
  bugForm.value.assignee = ''
  bugForm.value.module = ''
  if (newTokenId) {
    await loadBugFormProjects()
  }
})

// ============ 生命周期 ============
onMounted(async () => {
  // 先加载Token选项（成员映射需要使用Token ID）
  await loadTokenOptions()
  // 再加载Bug列表（内部会加载成员映射）
  await loadBugSyncItems()
})
</script>

<style scoped>
/* ==================== 设计系统变量 - 紫色主题 ==================== */
.bug-sync-management {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ==================== 页面标题 ==================== */
.page-header {
  text-align: center;
  margin-bottom: 8px;
  padding: 12px 0;
}

.page-title {
  font-size: 26px;
  font-weight: 600;
  color: #5a32a3;
  margin: 0 0 8px 0;
  letter-spacing: -0.02em;
}

.page-desc {
  font-size: 14px;
  color: #7b6db3;
  margin: 0;
  font-weight: 400;
}

/* ==================== 卡片容器 - 统一风格 ==================== */
.toolbar-card {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  gap: 4px;
}

/* 工具栏按钮 */
.toolbar-right .el-button .el-icon + span,
.toolbar-right .el-button .el-icon + template {
  margin-left: 6px;
}
.toolbar-right .el-button .el-icon {
  margin-right: 6px;
}

.toolbar-left .el-button--primary {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border: none;
  font-weight: 600;
  padding: 10px 20px;
  border-radius: 8px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
}

.toolbar-left .el-button--primary:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
}

.toolbar-left .el-button:not(.el-button--primary) {
  border-radius: 8px;
  border-color: rgba(147, 112, 219, 0.3);
  color: #5a32a3;
  transition: all 0.3s ease;
}

.toolbar-left .el-button:not(.el-button--primary):hover {
  background: #f8f7ff;
  border-color: #7b42f6;
  color: #7b42f6;
}

/* 筛选下拉框样式 */
.toolbar-right .el-select :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
  border-radius: 8px;
  background: #ffffff;
}

.toolbar-right .el-select :deep(.el-input__wrapper:hover),
.toolbar-right .el-select :deep(.el-input__wrapper:focus) {
  box-shadow: 0 0 0 1px #7b42f6;
}

/* 统一按钮风格到平台紫色渐变主题 */
.custom-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
  border: none !important;
  color: #fff !important;
  border-radius: 8px !important;
  font-weight: 500;
  transition: all 0.3s ease !important;
}
.custom-btn:hover,
.custom-btn:focus {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
}
.custom-btn:active {
  transform: translateY(0);
}

/* Token管理按钮橙色渐变 */
.token-btn {
  background: linear-gradient(135deg, #e6a23c 0%, #cf8a1e 100%) !important;
  border: none !important;
  color: #fff !important;
  border-radius: 8px !important;
  font-weight: 500;
  transition: all 0.3s ease !important;
}
.token-btn:hover,
.token-btn:focus {
  background: linear-gradient(135deg, #d99a2e 0%, #bf7c12 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.4);
}
.token-btn:active {
  transform: translateY(0);
}

/* 同步按钮绿色渐变 */
.sync-btn {
  background: linear-gradient(135deg, #00b96b 0%, #009a57 100%) !important;
  border: none !important;
  color: #fff !important;
  border-radius: 8px !important;
  font-weight: 500;
  transition: all 0.3s ease !important;
}
.sync-btn:hover,
.sync-btn:focus {
  background: linear-gradient(135deg, #00a862 0%, #008a4d 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 185, 107, 0.4);
}
.sync-btn:active {
  transform: translateY(0);
}

/* ==================== 统计卡片 ==================== */
.stats-row {
  margin-bottom: 4px;
}

.stats-card {
  text-align: center;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  transition: all 0.3s ease;
  background: #ffffff;
}

.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.12);
}

.stats-content {
  padding: 16px 0;
}

.stats-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 10px;
}

.stats-label {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

.stats-total .stats-value {
  color: #7b42f6;
}

.stats-synced .stats-value {
  color: #10b981;
}

.stats-failed .stats-value {
  color: #ef4444;
}

.stats-pending .stats-value {
  color: #f59e0b;
}

/* ==================== 表格卡片 ==================== */
.table-card {
  flex: 1;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 16px;
}

/* 表格样式 - 参考 history-card 风格 */
.table-card :deep(.el-table) {
  --el-table-border-color: rgba(147, 112, 219, 0.1);
  --el-table-header-bg-color: #ffffff;
  --el-table-row-hover-bg-color: #f8f7ff;
  border: none;
  border-radius: 8px 8px 0 0;
  overflow: hidden;
  min-height: 200px;
  box-shadow: none;
  background-color: transparent !important;
}

.table-card :deep(.el-table__header-wrapper) {
  background-color: #ffffff !important;
}

.table-card :deep(.el-table__header) {
  background-color: #ffffff !important;
}

.table-card :deep(th) {
  background-color: #ffffff !important;
  color: #5a32a3 !important;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid #e9ecef;
  padding: 0 !important;
  text-align: center;
  transition: background-color 0.3s ease;
}

.table-card :deep(th:hover) {
  background-color: #ffffff !important;
}

.table-card :deep(th .cell) {
  background-color: #ffffff !important;
  color: #5a32a3 !important;
  font-weight: 600 !important;
  white-space: nowrap !important;
  line-height: 24px !important;
  padding: 16px !important;
}

.table-card :deep(.el-table__body-wrapper) {
  background-color: #ffffff !important;
}

.table-card :deep(.el-table__row) {
  transition: background-color 0.3s ease;
  background-color: #ffffff !important;
  line-height: 24px;
}

.table-card :deep(.el-table__row:hover) {
  background-color: #f8f7ff !important;
}

.table-card :deep(.el-table__row.el-table__row--striped) {
  background-color: #fafaff !important;
}

.table-card :deep(td) {
  padding: 14px 16px;
  border-bottom: 1px solid #e9ecef;
  color: #333;
  font-size: 14px;
  font-weight: 400;
  line-height: 24px;
  transition: background-color 0.3s ease;
  vertical-align: middle;
}

.table-card :deep(.el-table__empty-block) {
  padding: 60px 0;
  background: #ffffff !important;
}

.table-card :deep(.el-table__empty-text) {
  color: #666;
  font-size: 14px;
  line-height: 24px;
}

/* ==================== Bug标题单元格 ==================== */
.bug-title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bug-title-text {
  font-weight: 500;
  color: #333;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 标签徽章样式 - 参考 XMindConverter 风格 */
.severity-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.3s ease;
}

/* 严重程度颜色 - 对应云效1-致命、2-严重、3-一般、4-轻微 */
.severity-badge.severity-s1 {
  background: #fff1f0;
  color: #f5222d;
}

.severity-badge.severity-s2 {
  background: #fff7e6;
  color: #fa8c16;
}

.severity-badge.severity-s3 {
  background: #e6f7ff;
  color: #1890ff;
}

.severity-badge.severity-s4 {
  background: #f6ffed;
  color: #52c41a;
}

/* 优先级徽章 */
.priority-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  padding: 4px 0;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.priority-badge.priority-high {
  background: #fff1f0;
  color: #f5222d;
}

.priority-badge.priority-medium {
  background: #fff7e6;
  color: #fa8c16;
}

.priority-badge.priority-low {
  background: #f6ffed;
  color: #52c41a;
}

/* 状态标签 */
.status-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.status-tag.status-new {
  background: #e6f7ff;
  color: #1890ff;
}

.status-tag.status-processing,
.status-tag.status-in-progress {
  background: #fff7e6;
  color: #fa8c16;
}

.status-tag.status-pending {
  background: #fffbe6;
  color: #d48806;
}

.status-tag.status-resolved,
.status-tag.status-fixed {
  background: #f6ffed;
  color: #52c41a;
}

.status-tag.status-verified {
  background: #f0f5ff;
  color: #2f54eb;
}

.status-tag.status-closed,
.status-tag.status-done {
  background: #f5f3ff;
  color: #7b42f6;
}

.status-tag.status-rejected {
  background: #f5f5f5;
  color: #8c8c8c;
}

.status-tag.status-wontfix {
  background: #fff0f6;
  color: #c41d7f;
}

.status-tag.status-reopened {
  background: #fff1f0;
  color: #f5222d;
}

/* 可点击的状态标签（已修复状态快捷操作） */
.status-clickable {
  cursor: pointer;
  outline: none;
}

.status-clickable:hover {
  filter: brightness(0.92);
  box-shadow: 0 0 0 2px rgba(82, 196, 26, 0.2);
}

.status-clickable .status-caret {
  font-size: 11px;
  margin-left: 2px;
}

.quick-change-info {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 13px;
  color: #606266;
}

/* 同步状态标签 */
.sync-status-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.sync-status-tag.synced {
  background: #f6ffed;
  color: #52c41a;
}

.sync-status-tag.failed {
  background: #fff1f0;
  color: #f5222d;
}

.sync-status-tag.pending {
  background: #fff7e6;
  color: #fa8c16;
}

.module-text {
  color: #333;
  font-size: 13px;
}

.time-text {
  color: #333;
  font-size: 13px;
}

.creator-text {
  color: #333;
  font-size: 13px;
}

.yunxiao-link {
  color: #7b42f6;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}

.yunxiao-link:hover {
  color: #5a32a3;
  text-decoration: underline;
  background-color: rgba(123, 66, 246, 0.08);
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

/* ==================== 抽屉样式 ==================== */
.bug-sync-management :deep(.el-drawer) {
  border-radius: 16px 0 0 16px;
}

.bug-sync-management :deep(.el-drawer__header) {
  background: linear-gradient(135deg, #f8f7ff 0%, #fff 100%);
  border-bottom: 1px solid rgba(147, 112, 219, 0.12);
  margin-bottom: 0;
  padding: 20px 24px;
}

.bug-sync-management :deep(.el-drawer__title) {
  color: #5a32a3;
  font-weight: 600;
  font-size: 18px;
}

.bug-sync-management :deep(.el-drawer__body) {
  padding: 24px;
}

.bug-sync-management :deep(.el-drawer__footer) {
  padding: 16px 24px;
  border-top: 1px solid rgba(147, 112, 219, 0.1);
  background: #faf9ff;
}

/* 对话框表单样式 */
.bug-sync-management :deep(.el-form-item__label) {
  color: #374151;
  font-weight: 500;
}

.bug-sync-management :deep(.el-input__wrapper),
.bug-sync-management :deep(.el-textarea__wrapper),
.bug-sync-management :deep(.el-select__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2);
  transition: all 0.25s ease;
}

.bug-sync-management :deep(.el-input__wrapper:hover),
.bug-sync-management :deep(.el-textarea__wrapper:hover),
.bug-sync-management :deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.35);
}

.bug-sync-management :deep(.el-input__wrapper.is-focus),
.bug-sync-management :deep(.el-textarea__wrapper.is-focus),
.bug-sync-management :deep(.el-select__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #7b42f6;
}

/* 抽屉按钮样式 */
.bug-sync-management :deep(.el-drawer__footer .el-button--primary) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border: none;
  font-weight: 600;
  padding: 10px 24px;
  border-radius: 8px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
}

.bug-sync-management :deep(.el-drawer__footer .el-button--primary):hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
}

.bug-sync-management :deep(.el-drawer__footer .el-button:not(.el-button--primary)) {
  border-radius: 8px;
  border-color: rgba(147, 112, 219, 0.3);
  color: #5a32a3;
}

.bug-sync-management :deep(.el-drawer__footer .el-button:not(.el-button--primary)):hover {
  background: #f8f7ff;
  border-color: #7b42f6;
  color: #7b42f6;
}

/* ==================== 空状态样式 ==================== */
.bug-sync-management :deep(.el-empty__description p) {
  color: #7b6db3;
}

/* ==================== 分页组件 - 紫色主题 ==================== */
.pagination-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 0;
  margin-top: 8px;
  background: transparent;
  border: none;
  transition: all 0.3s ease;

  /* 定义主题变量 - 浅紫色风格 */
  --primary-color: #a78bfa;
  --primary-dark: #8b5cf6;
  --primary-light: #f3f0ff;
  --text-primary: #262626;
  --text-secondary: #595959;
  --text-tertiary: #8c8c8c;

  /* 覆盖 Element Plus 默认主题变量 */
  --el-color-primary: var(--primary-color);
  --el-color-primary-light-3: #c4b5fd;
  --el-color-primary-light-5: #ddd6fe;
  --el-color-primary-light-7: #ede9fe;
  --el-color-primary-light-8: #f5f3ff;
  --el-color-primary-light-9: #fafaff;
  --el-color-primary-dark-2: #8b5cf6;
  --el-text-color-primary: var(--text-primary);
  --el-text-color-regular: var(--text-secondary);
  --el-text-color-secondary: var(--text-tertiary);
}

.pagination-container :deep(.el-pagination) {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}

/* 总条数 */
.pagination-container :deep(.el-pagination__total) {
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  margin-right: 12px;
}

/* 每页条数选择器 */
.pagination-container :deep(.el-pagination__sizes) {
  margin-right: 12px;
}

.pagination-container :deep(.el-pagination__sizes .el-select .el-input__wrapper) {
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  box-shadow: none;
}

.pagination-container :deep(.el-pagination__sizes .el-select .el-input__wrapper:hover) {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
}

.pagination-container :deep(.el-pagination__sizes .el-select .el-input__wrapper.is-focus) {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
}

.pagination-container :deep(.el-pagination__sizes .el-select .el-input__inner) {
  color: #374151;
  font-weight: 500;
}

/* 上一页/下一页按钮 */
.pagination-container :deep(.el-pagination .btn-prev),
.pagination-container :deep(.el-pagination .btn-next) {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #6b7280;
  transition: all 0.3s ease;
}

.pagination-container :deep(.el-pagination .btn-prev:hover:not(:disabled)),
.pagination-container :deep(.el-pagination .btn-next:hover:not(:disabled)) {
  background: #f5f3ff;
  border-color: #a78bfa;
  color: #8b5cf6;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
}

.pagination-container :deep(.el-pagination .btn-prev:disabled),
.pagination-container :deep(.el-pagination .btn-next:disabled) {
  background: #f5f5f5;
  border-color: #e0e0e0;
  color: #c0c0c0;
}

.pagination-container :deep(.el-pagination .btn-prev .el-icon),
.pagination-container :deep(.el-pagination .btn-next .el-icon) {
  font-size: 14px;
  font-weight: bold;
}

/* 页码按钮 */
.pagination-container :deep(.el-pager) {
  display: flex;
  gap: 8px;
}

.pagination-container :deep(.el-pager li) {
  min-width: 32px;
  height: 32px;
  padding: 0 8px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pagination-container :deep(.el-pager li:hover:not(.is-active)) {
  background: #f5f3ff;
  border-color: #a78bfa;
  color: #8b5cf6;
  transform: translateY(-1px);
}

.pagination-container :deep(.el-pager li.is-active) {
  background: #f5f3ff;
  border-color: #a78bfa;
  color: #8b5cf6;
  box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
}

.pagination-container :deep(.el-pager li.is-active:hover) {
  background: #ede9fe;
  border-color: #8b5cf6;
}

/* 跳转输入框 */
.pagination-container :deep(.el-pagination__jump) {
  color: #6b7280;
  font-weight: 500;
  margin-left: 12px;
}

.pagination-container :deep(.el-pagination__jump .el-input) {
  width: 50px;
  margin: 0 4px;
}

.pagination-container :deep(.el-pagination__jump .el-input__wrapper) {
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  box-shadow: none;
}

.pagination-container :deep(.el-pagination__jump .el-input__wrapper:hover) {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
}

.pagination-container :deep(.el-pagination__jump .el-input__wrapper.is-focus) {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
}

.pagination-container :deep(.el-pagination__jump .el-input__inner) {
  color: #374151;
  font-weight: 500;
  text-align: center;
}

/* ==================== 描述模板 ==================== */
.desc-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.desc-toolbar-label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.desc-template-tag {
  cursor: pointer;
  transition: all 0.2s ease;
}

.desc-template-tag:hover {
  color: #7b42f6;
  border-color: #7b42f6;
  background: #f8f7ff;
}

/* ==================== 附件上传 ==================== */
.pending-attachments {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pending-file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
}

.pending-file-item .file-icon {
  color: #6b7280;
  font-size: 16px;
  flex-shrink: 0;
}

.pending-file-item .file-name {
  color: #374151;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pending-file-item .file-size {
  color: #9ca3af;
  font-size: 12px;
  flex-shrink: 0;
}
</style>
