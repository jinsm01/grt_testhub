<template>
  <div class="ai-rubric-container">
    <el-card class="main-card" shadow="never">
      <!-- 上传区域标题 - 参考生成记录样式 -->
      <div class="section-header">
        <div class="section-title">
          <el-icon><Upload /></el-icon>
          <span>文件上传</span>
        </div>
      </div>

      <!-- 上传区域 -->
      <div v-show="!uploadedFile" class="upload-container">
        <el-upload
          ref="uploadRef"
          class="upload-area"
          drag
          :auto-upload="false"
          :limit="1"
          :show-file-list="false"
          accept=".docx,.pdf,.txt,.png,.jpg,.jpeg,.xlsx"
          @change="handleFileChange"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">
            <p>拖拽文件到此处，或 <em>点击选择文件</em></p>
            <p class="upload-desc">支持 .docx / .pdf / .txt / .png / .jpg 格式，AI将自动分析内容并生成评分量表和学习心得</p>
            <p class="upload-tip">最大 20MB</p>
          </div>
        </el-upload>
      </div>

      <!-- 已选文件信息 -->
      <div v-if="uploadedFile" class="file-info-row">
        <div class="file-item">
          <img v-if="isImageFile(uploadedFile.name)" :src="getImagePreview(uploadedFile)" class="file-thumb" />
          <el-icon v-else class="file-doc-icon"><Document /></el-icon>
          <span class="file-name">{{ uploadedFile.name }}</span>
          <span class="file-size">({{ formatFileSize(uploadedFile.size) }})</span>
        </div>
        <el-button link class="file-remove-btn" @click="clearFile">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>

      <!-- 配置行 -->
      <div class="config-row">
        <div class="config-item config-name-item">
          <label class="config-label">任务名称</label>
          <el-input v-model="form.taskName" placeholder="例：AI技术与学科融合评分量表" />
        </div>
        <div class="config-item config-count-item">
          <label class="config-label">心得数量</label>
          <el-select v-model="form.noteCount">
            <el-option label="10 条" :value="10" />
            <el-option label="20 条（推荐）" :value="20" />
            <el-option label="30 条" :value="30" />
          </el-select>
        </div>
        <div class="config-item config-ratio-item">
          <label class="config-label">得分心得比例</label>
          <el-select v-model="form.passRatio">
            <el-option label="各占50%" :value="0.5" />
            <el-option label="60% 得 / 40% 不" :value="0.6" />
            <el-option label="70% 得 / 30% 不" :value="0.7" />
          </el-select>
        </div>
        <div class="config-item config-length-item">
          <label class="config-label">心得字数</label>
          <el-select v-model="form.noteLength">
            <el-option label="100 字左右" :value="100" />
            <el-option label="300 字左右（推荐）" :value="300" />
            <el-option label="500 字左右" :value="500" />
          </el-select>
        </div>
        <el-button 
          type="primary" 
          class="gen-btn" 
          @click="startGenerate" 
          :disabled="!form.taskName.trim() || generating"
          :loading="generating"
        >
          <el-icon><MagicStick /></el-icon>
          开始生成
        </el-button>
      </div>
      <p class="config-tip">若生成失败，则会取用默认模板并根据配置项生成量表和心得</p>

      <!-- 分割线 -->
      <div class="section-divider"></div>

      <!-- 记录列表 -->
      <div class="records-section">
        <div class="card-header">
          <div class="card-title">
            <el-icon><List /></el-icon>
            <span>生成记录</span>
            <el-tag size="small" type="info" effect="plain" class="title-tag">共 {{ filteredRecords.length }} 条</el-tag>
          </div>
          <div class="filter-tabs">
            <div
              v-for="tab in filterTabs"
              :key="tab.value"
              class="filter-tab"
              :class="{ active: currentFilter === tab.value }"
              @click="currentFilter = tab.value; fetchRecords()"
            >
              {{ tab.label }}
            </div>
          </div>
        </div>

        <div class="search-bar">
          <el-input
            v-model="searchText"
            placeholder="搜索任务名称..."
            clearable
            prefix-icon="Search"
            @input="onSearch"
          />
        </div>

        <!-- 表格 -->
        <el-table
          :data="paginatedRecords"
          stripe
          v-loading="tableLoading"
          empty-text="暂无生成记录，上传文件后点击「开始生成」"
          class="records-table"
        >
          <el-table-column prop="id" label="序号" width="65" align="center">
            <template #default="{ $index }">{{ (currentPage - 1) * pageSize + $index + 1 }}</template>
          </el-table-column>
          <el-table-column label="任务名称" min-width="180">
            <template #default="{ row }">
              <el-link type="primary" @click="previewRecord(row)" :underline="false" class="task-name-link">
                {{ row.name }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="source_file_name" label="关联文件" width="120" align="center">
            <template #default="{ row }">
              <span class="file-name-text">{{ row.source_file_name || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <span :class="['status-badge', row.status]">
                {{ statusText(row.status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="心得数量" width="90" align="center">
            <template #default="{ row }">
              {{ row.note_count || '-' }} 条
              <small v-if="row.status === 'done'" class="ratio-text">
                ({{ Math.round(row.pass_ratio * 100) }}%得分)
              </small>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="生成时间" width="160" align="center" />
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'done' || row.status === 'error'">
                <el-button size="small" type="primary" link @click="previewRecord(row)">
                  <el-icon><View /></el-icon> 预览
                </el-button>
                <el-button size="small" type="success" link @click="downloadXlsx(row)">
                  <el-icon><Download /></el-icon> 量表
                </el-button>
                <el-button size="small" type="warning" link @click="downloadDocx(row)">
                  <el-icon><Download /></el-icon> 心得
                </el-button>
                <el-button size="small" type="danger" link @click="showDeleteDialog(row.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
              <template v-else-if="row.status === 'running'">
                <span class="status-badge running">处理中</span>
                <el-button size="small" type="danger" link @click="showDeleteDialog(row.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
              <template v-else>
                <el-button size="small" type="danger" link @click="showDeleteDialog(row.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="filteredRecords.length"
            :page-sizes="[5, 10, 20, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            background
          />
        </div>
      </div>
    </el-card>

    <!-- 删除确认对话框 -->
    <el-dialog
      v-model="deleteDialogVisible"
      title="确认删除"
      width="420px"
      align-center
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="delete-dialog-content">
        <el-icon :size="22" color="#E6A23C"><WarningFilled /></el-icon>
        <span>确定要删除该任务吗？此操作将同时删除关联的量表和心得，删除后不可恢复。</span>
      </div>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmDelete" :loading="deleteLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      :title="'预览：' + (previewData?.name || '')"
      width="880px"
      destroy-on-close
      top="5vh"
      class="preview-dialog"
    >
      <el-tabs v-model="previewTab" v-if="previewData">
        <el-tab-pane label="评分量表" name="rubric">
          <div v-if="previewData.rubric_data && previewData.rubric_data.length" class="rubric-preview">
            <p class="preview-summary">
              共 <strong>{{ uniqueLevel1Count }}</strong> 个一级指标，
              <strong>{{ previewData.rubric_data.length }}</strong> 个二级指标
            </p>
            <el-table :data="previewData.rubric_data" border stripe size="small" max-height="480">
              <el-table-column prop="seq" label="#" width="50" align="center" />
              <el-table-column prop="level1" label="一级指标" width="150">
                <template #default="{ row }">
                  <span v-if="isFirstInLevel1(row)" class="level1-tag">{{ row.level1 }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="level2" label="二级指标" width="170">
                <template #default="{ row }">
                  <span>{{ row.seq }}. {{ row.level2 }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="desc" label="指标说明" show-overflow-tooltip />
            </el-table>
          </div>
          <el-empty v-else description="暂无量表数据" />
        </el-tab-pane>

        <el-tab-pane label="学习心得" name="notes">
          <div v-if="previewData.notes_data && previewData.notes_data.length" class="notes-preview">
            <div class="notes-summary">
              <span>共 <strong>{{ previewData.notes_data.length }}</strong> 条心得：</span>
              <span class="status-badge done">得心 {{ passNoteCount }}条</span>
              <span class="status-badge error">不得心 {{ failNoteCount }}条</span>
            </div>
            <div class="notes-list">
              <div
                v-for="(note, idx) in previewData.notes_data"
                :key="idx"
                class="note-card"
                :class="{ 'fail-note': note.type === 'fail' }"
              >
                <div class="note-header">
                  <span class="note-num">{{ Number(idx) + 1 }}</span>
                  <span class="note-title">{{ note.title }}</span>
                  <span :class="['status-badge', note.type === 'pass' ? 'done' : 'error']">
                    {{ note.type === 'pass' ? '得分' : '不得分' }}
                  </span>
                </div>
                <div class="note-body">{{ note.body }}</div>
                <div class="note-meta">
                  <span class="meta-tag">观点{{ note.type === 'pass' ? '正确' : '偏差' }}</span>
                  <span class="meta-tag">逻辑{{ note.type === 'pass' ? '清晰' : '不足' }}</span>
                  <span class="meta-tag">内容{{ note.type === 'pass' ? '完整' : '欠缺' }}</span>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无心得数据" />
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" v-if="previewTab === 'rubric'" @click="downloadCurrentXlsx">
          <el-icon><Download /></el-icon> 下载量表 XLSX
        </el-button>
        <el-button type="primary" v-if="previewTab === 'notes'" @click="downloadCurrentDocx">
          <el-icon><Download /></el-icon> 下载心得文件
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis, CircleCheck, Loading, Document, Upload, UploadFilled,
  MagicStick, List, View, Download, Delete, Close, WarningFilled, Search
} from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import { getRubricRecords, generateRubric, deleteRubricRecord, getRubricStatistics } from '@/api/data-factory'

// ====== 状态 ======
const tableLoading = ref(false)
const generating = ref(false)
const uploadRef = ref()
const uploadedFile = ref(null)
const currentFilter = ref('all')
const searchText = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const previewVisible = ref(false)
const previewTab = ref('rubric')
const previewData = ref(null)
const deleteDialogVisible = ref(false)
const deleteTargetId = ref(null)
const deleteLoading = ref(false)
const records = ref([])

// 统计数据
const stats = reactive({
  total: 0,
  done: 0,
  running: 0,
  error: 0,
  files: 0,
})

// 表单配置
const form = reactive({
  taskName: '',
  noteCount: 20,
  passRatio: 0.6,
  noteLength: 300,
})

// 筛选标签
const filterTabs = [
  { label: '全部状态', value: 'all' },
  { label: '生成中', value: 'running' },
  { label: '已完成', value: 'done' },
  { label: '失败', value: 'error' }
]

// ====== 计算属性 ======
const filteredRecords = computed(() => {
  let result = records.value
  if (currentFilter.value && currentFilter.value !== 'all') {
    result = result.filter(r => r.status === currentFilter.value)
  }
  if (searchText.value) {
    const keyword = searchText.value.toLowerCase()
    result = result.filter(r =>
      r.name.toLowerCase().includes(keyword) ||
      (r.source_file_name || '').toLowerCase().includes(keyword)
    )
  }
  return result
})

const paginatedRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredRecords.value.slice(start, start + pageSize.value)
})

const uniqueLevel1Count = computed(() => {
  if (!previewData.value?.rubric_data) return 0
  const set = new Set(previewData.value.rubric_data.map(r => r.level1))
  return set.size
})

const passNoteCount = computed(() => {
  if (!previewData.value?.notes_data) return 0
  return previewData.value.notes_data.filter(n => n.type === 'pass').length
})

const failNoteCount = computed(() => {
  if (!previewData.value?.notes_data) return 0
  return previewData.value.notes_data.filter(n => n.type === 'fail').length
})

// ====== 方法 ======
function statusTagType(status) {
  const map = { done: 'success', running: 'primary', error: 'danger' }
  return map[status] || 'info'
}

function statusText(status) {
  const map = { done: '已完成', running: '生成中', error: '失败' }
  return map[status] || status
}

function isImageFile(name) {
  return /\.(png|jpe?g)$/i.test(name)
}

function getImagePreview(file) {
  return URL.createObjectURL(file.raw || file)
}

function formatFileSize(size) {
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / (1024 * 1024)).toFixed(1) + ' MB'
}

function handleFileChange(file) {
  uploadedFile.value = file
}

function clearFile() {
  uploadedFile.value = null
  if (uploadRef.value) uploadRef.value.clearFiles()
}

let searchTimer = null
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
  }, 300)
}

async function fetchStats() {
  try {
    const res = await getRubricStatistics()
    if (res.data.success) {
      Object.assign(stats, res.data.data)
    }
  } catch (e) {
    console.error('获取统计失败:', e)
  }
}

async function fetchRecords() {
  tableLoading.value = true
  try {
    const res = await getRubricRecords()
    if (res.data.success) {
      records.value = res.data.data || []
    } else {
      ElMessage.error(res.data.error || '获取记录失败')
    }
  } catch (e) {
    console.error('获取记录失败:', e)
    ElMessage.error('获取记录失败')
  } finally {
    tableLoading.value = false
  }
}

async function startGenerate() {
  if (!form.taskName.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  generating.value = true
  try {
    const params = new FormData()
    params.append('name', form.taskName.trim())
    params.append('note_count', form.noteCount)
    params.append('pass_ratio', form.passRatio)
    params.append('note_length', form.noteLength)
    if (uploadedFile.value) {
      params.append('file', uploadedFile.value.raw || uploadedFile.value)
    }
    const res = await generateRubric(params)
    if (res.data.success) {
      ElMessage.success('任务已创建，正在生成...')
      form.taskName = ''
      clearFile()
      await fetchRecords()
      await fetchStats()
    } else {
      ElMessage.error(res.data.error || '创建失败')
    }
  } catch (e) {
    console.error('生成失败:', e)
    ElMessage.error('生成失败')
  } finally {
    generating.value = false
  }
}

async function previewRecord(row) {
  try {
    if (row.status === 'running') {
      ElMessage.info('任务正在生成中，请稍后再试')
      return
    }
    const res = await getRubricRecords()
    if (res.data.success) {
      const detail = res.data.data.find(r => r.id === row.id)
      if (detail) {
        previewData.value = detail
      } else {
        ElMessage.error('获取详情失败')
        return
      }
    }
    previewTab.value = 'rubric'
    previewVisible.value = true
  } catch (e) {
    console.error('预览失败:', e)
    ElMessage.error('预览失败')
  }
}

function isFirstInLevel1(row) {
  if (!previewData.value?.rubric_data) return false
  const idx = previewData.value.rubric_data.indexOf(row)
  if (idx <= 0) return true
  return previewData.value.rubric_data[idx - 1].level1 !== row.level1
}

function showDeleteDialog(id) {
  deleteTargetId.value = id
  deleteDialogVisible.value = true
}

async function confirmDelete() {
  deleteLoading.value = true
  try {
    await deleteRecord(deleteTargetId.value)
    deleteDialogVisible.value = false
  } finally {
    deleteLoading.value = false
  }
}

async function deleteRecord(id) {
  try {
    const res = await deleteRubricRecord(id)
    if (res.data.success) {
      ElMessage.success('已删除')
      await fetchRecords()
      await fetchStats()
    } else {
      ElMessage.error(res.data.error || '删除失败')
    }
  } catch (e) {
    console.error('删除失败:', e)
    ElMessage.error('删除失败')
  }
}

function downloadXlsx(record) {
  const rubricData = record.rubric_data
  if (!rubricData || !rubricData.length) {
    ElMessage.warning('量表数据不存在')
    return
  }

  const wb = XLSX.utils.book_new()
  const header = [['序号', '一级指标', '二级指标', '指标说明']]
  const rows = rubricData.map(r => [r.seq, r.level1, r.level2, r.desc])
  const ws = XLSX.utils.aoa_to_sheet([...header, ...rows])
  ws['!cols'] = [{ wch: 6 }, { wch: 22 }, { wch: 24 }, { wch: 55 }]

  for (const cell of ['A1','B1','C1','D1']) {
    if (ws[cell]) ws[cell].s = {
      font: { bold: true, color: { rgb: 'FFFFFF' } },
      fill: { fgColor: { rgb: '7C3AED' } },
      alignment: { horizontal: 'center' }
    }
  }

  XLSX.utils.book_append_sheet(wb, ws, '评分量表')

  const notesData = record.notes_data || []
  if (notesData.length) {
    const nHeader = [['序号', '标题', '类型', '内容']]
    const nRows = notesData.map((n, i) => [i + 1, n.title, n.type === 'pass' ? '得分心得' : '不得分心得', n.body.replace(/\n/g, ' ')])
    const ws2 = XLSX.utils.aoa_to_sheet([...nHeader, ...nRows])
    ws2['!cols'] = [{ wch: 6 }, { wch: 32 }, { wch: 12 }, { wch: 85 }]
    XLSX.utils.book_append_sheet(wb, ws2, '学习心得')
  }

  XLSX.writeFile(wb, `${record.name.replace(/[/\\?%*:|"<>]/g, '_')}_量表.xlsx`)
  ElMessage.success('量表下载完成')
}

function downloadDocx(record) {
  const notesData = record.notes_data
  if (!notesData || !notesData.length) {
    ElMessage.warning('心得数据不存在')
    return
  }

  const passNotes = notesData.filter(n => n.type === 'pass')
  const failNotes = notesData.filter(n => n.type === 'fail')

  const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')

  let html = `<html xmlns:o="urn:schemas-microsoft-com:office:office"
xmlns:w="urn:schemas-microsoft-com:office:word"
xmlns:m="http://schemas.microsoft.com/office/2004/12/omml"
xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="UTF-8">
<meta name=ProgId content=Word.Document>
<!--[if gte mso 9]><xml>
<w:WordDocument><w:View>Print</w:View></w:WordDocument>
</xml><![endif]-->
<title>${esc(record.name)} - 学习心得</title>
<style>
body{font-family:'宋体';font-size:10.5pt;line-height:1.8;color:#333}
h1{font-size:16pt;text-align:center;color:#4B0082;margin-bottom:4pt}
.meta{text-align:center;font-size:9pt;color:#888;margin-bottom:24pt}
h2{font-size:13pt;margin-top:20pt;padding-bottom:4pt;border-bottom:2px solid #7C3AED;color:#7C3AED}
h2.fail-title{border-color:#EF4444;color:#EF4444}
.note{margin:14pt 0;padding:8pt 12pt;border-left:3px solid #7C3AED;background:#faf5ff}
.note.fail{border-color:#EF4444;background:#fff5f5}
.note-title{font-weight:bold;font-size:11pt;margin-bottom:4pt}
.note-body{white-space:pre-wrap}
</style></head><body>

<h1>${esc(record.name)}</h1>
<div class="meta">生成时间：${esc(record.created_at)} | 共 ${notesData.length} 条心得（得分 ${passNotes.length} 条 / 不得分 ${failNotes.length} 条）</div>

<h2>一、得分心得（共 ${passNotes.length} 条）</h2>`
  passNotes.forEach((n, i) => {
    html += `<div class="note"><div class="note-title">${i+1}. ${esc(n.title)} <span style="color:#065f46;font-size:9pt;">[得分]</span></div><div class="note-body">${esc(n.body)}</div></div>`
  })

  html += `<h2 class="fail-title">二、不得分心得（共 ${failNotes.length} 条）</h2>`
  failNotes.forEach((n, i) => {
    html += `<div class="note fail"><div class="note-title">${i+1}. ${esc(n.title)} <span style="color:#991b1b;font-size:9pt;">[不得分]</span></div><div class="note-body">${esc(n.body)}</div></div>`
  })
  html += '</body></html>'

  const blob = new Blob([html], { type: 'application/msword;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${record.name.replace(/[/\\?%*:|"<>]/g, '_')}_学习心得.doc`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('心得文档已下载')
}

function downloadCurrentXlsx() {
  if (previewData.value) downloadXlsx(previewData.value)
}

function downloadCurrentDocx() {
  if (previewData.value) downloadDocx(previewData.value)
}

// ====== 初始化 ======
onMounted(async () => {
  await Promise.all([fetchRecords(), fetchStats()])
})
</script>

<style lang="scss" scoped>
.ai-rubric-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
}

.main-card {
  flex: 1;
  min-height: 600px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.1);
  display: flex;
  flex-direction: column;

  :deep(.el-card__body) {
    padding: 24px;
    flex: 1;
    display: flex;
    flex-direction: column;
  }
}

// ====== 统计卡片 ======
.stats-row {
  display: flex;
  gap: 14px;
  margin-bottom: 24px;

  .stat-card {
    flex: 1;
    background: #fff;
    border: 1px solid rgba(147, 112, 219, 0.1);
    border-radius: 12px;
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 2px 12px rgba(147, 112, 219, 0.05);

    .stat-icon {
      width: 42px;
      height: 42px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;

      &.purple { background: #ede9fe; color: #7c3aed; }
      &.green { background: #d1fae5; color: #059669; }
      &.yellow { background: #fef3c7; color: #d97706; }
      &.blue { background: #dbeafe; color: #2563eb; }
    }

    .stat-num {
      font-size: 24px;
      font-weight: 700;
      color: #1f2937;
      line-height: 1;
    }

    .stat-label {
      font-size: 12px;
      color: #9ca3af;
      margin-top: 4px;
    }
  }
}

// ====== 页面头部 ======
.page-header {
  margin-bottom: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
  color: #333;

  .el-icon {
    color: #7b42f6;
    font-size: 18px;
  }

  .title-tag {
    margin-left: 8px;
  }
}

.card-desc {
  font-size: 12.5px;
  color: #9ca3af;
  margin: 0 0 16px;
}

// ====== 区块标题样式（参考生成记录） ======
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
    color: #5a32a3;

    .el-icon {
      color: #7b42f6;
      font-size: 18px;
    }
  }
}

// ====== 上传区域 ======
.upload-container {
  margin-bottom: 20px;
}

.upload-area {
  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    border: 2px dashed #c4b5fd !important;
    background: linear-gradient(180deg, #f5f0ff 0%, #ede9fe 100%) !important;
    border-radius: 12px !important;
    transition: all 0.3s;
    height: auto !important;
    min-height: 280px !important;
    padding: 24px 20px 40px !important;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;

    &:hover {
      border-color: #7b42f6 !important;
      background: linear-gradient(180deg, #ede9fe 0%, #ddd6fe 100%) !important;
    }
  }
}

// 上传区域头部样式
.upload-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;

  .upload-header-icon {
    color: #7b42f6;
    font-size: 18px;
  }

  .upload-header-title {
    font-weight: 600;
    font-size: 16px;
    color: #333;
  }

  .title-tag {
    margin-left: 4px;
  }
}

.upload-header-desc {
  font-size: 12.5px;
  color: #9ca3af;
  margin: 0 0 24px;
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  color: #a78bfa;
  margin-top: 8px;
}

.upload-text {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
  margin-top: 12px;
  text-align: center;

  em {
    color: #7b42f6;
    font-style: normal;
    cursor: pointer;
  }
}

.upload-desc {
  font-size: 13px;
  color: #6b7280;
  margin-top: 12px;
  line-height: 1.5;
}

.upload-tip {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 6px;
}

.upload-btn {
  margin-top: 16px;
  border-radius: 20px;
  padding: 0 24px;
  height: 36px;
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border: none;

  &:hover {
    background: linear-gradient(135deg, #8a5af7 0%, #6a42b3 100%);
  }
}

// ====== 文件信息 ======
.file-info-row {
  margin: 14px 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(147, 112, 219, 0.04);
  border-radius: 10px;
  border: 1px solid rgba(147, 112, 219, 0.08);

  .file-item {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    flex: 1;
  }

  .file-thumb {
    width: 32px;
    height: 32px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid #e5e7eb;
  }

  .file-doc-icon {
    font-size: 24px;
    color: #9ca3af;
    flex-shrink: 0;
  }

  .file-name {
    font-size: 14px;
    color: #374151;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-size {
    font-size: 12px;
    color: #9ca3af;
    flex-shrink: 0;
  }

  .file-remove-btn {
    color: #999;
    padding: 4px;
    flex-shrink: 0;
    &:hover { color: #ef4444; }
  }
}

// ====== 配置行 ======
.config-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: nowrap;

  .config-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;

    .config-label {
      font-size: 13px;
      color: #666;
      font-weight: 500;
    }
  }

  .config-name-item,
  .config-count-item,
  .config-ratio-item,
  .config-length-item {
    flex: 1;
    min-width: 0;
  }

  :deep(.el-input__wrapper),
  :deep(.el-select .el-input__wrapper) {
    border-radius: 8px;
    height: 36px;
  }

  .gen-btn {
    border-radius: 8px;
    padding: 0 26px;
    height: 36px;
    font-size: 14px;
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    border: none;

    &:hover {
      background: linear-gradient(135deg, #8a5af7 0%, #6a42b3 100%);
    }

    &:active {
      background: linear-gradient(135deg, #6a35d9 0%, #4a2891 100%);
    }

    &.is-disabled {
      background: linear-gradient(135deg, #c4b5fd 0%, #a78bfa 100%);
    }
  }
}

.config-tip {
  margin-top: 12px;
  font-size: 12px;
  color: #909399;
}

// ====== 分割线 ======
.section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(147, 112, 219, 0.2), transparent);
  margin: 24px 0;
}

// ====== 记录区域 ======
.records-section {
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }
}

// ====== 筛选标签 ======
.filter-tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: rgba(147, 112, 219, 0.08);
  border-radius: 10px;

  .filter-tab {
    padding: 6px 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    color: #666;
    font-size: 13px;
    font-weight: 500;

    &:hover {
      background: rgba(147, 112, 219, 0.1);
      color: #7b42f6;
    }

    &.active {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      color: #fff;
      box-shadow: 0 2px 8px rgba(123, 66, 246, 0.3);
    }
  }
}

// ====== 搜索栏 ======
.search-bar {
  margin-bottom: 16px;

  :deep(.el-input__wrapper) {
    border-radius: 8px;
  }
}

// ====== 表格样式 ======
.records-table {
  // 直接覆盖表头单元格样式 - 参考 XMindConverter.vue
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

  .task-name-link {
    font-weight: 500;
  }

  .file-name-text {
    font-size: 12px;
    color: #666;
  }

  .ratio-text {
    color: #999;
    font-size: 11px;
    display: block;
    margin-top: 2px;
  }
}

// ====== 状态标签 ======
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;

  &.done {
    background: #d1fae5;
    color: #059669;
  }

  &.running {
    background: #dbeafe;
    color: #2563eb;
  }

  &.error {
    background: #fee2e2;
    color: #dc2626;
  }
}

// ====== 分页 ======
.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 0;
  margin-top: 8px;
  background: transparent;
  border: none;

  :deep(.el-pagination) {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;

    // 总条数
    .el-pagination__total {
      color: #6b7280;
      font-size: 14px;
      font-weight: 500;
      margin-right: 12px;
    }

    // 每页条数选择器
    .el-pagination__sizes {
      margin-right: 12px;

      .el-select {
        .el-input__wrapper {
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          background: #ffffff;
          box-shadow: none;

          &:hover {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
          }

          &.is-focus {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
          }
        }

        .el-input__inner {
          color: #374151;
          font-weight: 500;
        }
      }
    }

    // 上一页/下一页按钮
    .btn-prev,
    .btn-next {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      border: 1px solid #e5e7eb;
      background: #ffffff;
      color: #6b7280;
      transition: all 0.3s ease;

      &:hover:not(:disabled) {
        background: #f5f3ff;
        border-color: #a78bfa;
        color: #8b5cf6;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
      }

      &:disabled {
        background: #f5f5f5;
        border-color: #e0e0e0;
        color: #c0c0c0;
      }

      .el-icon {
        font-size: 14px;
        font-weight: bold;
      }
    }

    // 页码按钮
    .el-pager {
      display: flex;
      gap: 8px;

      li {
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

        &:hover:not(.is-active) {
          background: #f5f3ff;
          border-color: #a78bfa;
          color: #8b5cf6;
          transform: translateY(-1px);
        }

        &.is-active {
          background: #f5f3ff;
          border-color: #a78bfa;
          color: #8b5cf6;
          box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
        }

        &.is-active:hover {
          background: #ede9fe;
          border-color: #8b5cf6;
        }
      }
    }

    // 跳转输入框
    .el-pagination__jump {
      color: #6b7280;
      font-weight: 500;
      margin-left: 12px;

      .el-input {
        width: 50px;
        margin: 0 4px;

        .el-input__wrapper {
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          background: #ffffff;
          box-shadow: none;

          &:hover {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
          }

          &.is-focus {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
          }
        }

        .el-input__inner {
          color: #374151;
          font-weight: 500;
          text-align: center;
        }
      }
    }
  }
}

// ====== 删除对话框 ======
.delete-dialog-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  color: #606266;
  line-height: 1.6;
}

// ====== 预览弹窗 ======
.preview-dialog {
  :deep(.el-dialog__body) {
    padding-top: 10px;
  }
}

.rubric-preview {
  max-height: 520px;
  overflow-y: auto;

  .preview-summary {
    margin-bottom: 12px;
    font-size: 13px;
    color: #666;

    strong {
      color: #7b42f6;
    }
  }
}

.level1-tag {
  font-weight: 600;
  color: #7b42f6;
}

.notes-preview {
  max-height: 520px;
  overflow-y: auto;

  .notes-summary {
    display: flex;
    gap: 10px;
    margin-bottom: 14px;
    font-size: 13px;
    color: #666;
    align-items: center;
  }
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.note-card {
  padding: 14px 16px;
  background: #faf8ff;
  border-radius: 10px;
  border: 1px solid rgba(147, 112, 219, 0.1);

  &.fail-note {
    background: #fff5f5;
    border-color: rgba(239, 68, 68, 0.1);
  }

  .note-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;

    .note-num {
      width: 22px;
      height: 22px;
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 600;
    }

    .note-title {
      flex: 1;
      font-weight: 600;
      color: #333;
      font-size: 14px;
    }
  }

  .note-body {
    color: #666;
    font-size: 13px;
    line-height: 1.6;
    margin-bottom: 10px;
    white-space: pre-wrap;
  }

  .note-meta {
    display: flex;
    gap: 8px;

    .meta-tag {
      padding: 3px 10px;
      background: rgba(147, 112, 219, 0.1);
      color: #7b42f6;
      border-radius: 10px;
      font-size: 11px;
    }
  }

  &.fail-note {
    .note-num {
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    }

    .note-meta .meta-tag {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }
  }
}

// ====== 下拉框样式覆盖 ======
:deep(.el-select-dropdown__item) {
  // 所有项默认透明背景
  background-color: transparent !important;

  // 选中项和悬停项使用完全相同的样式
  &.selected,
  &.hover,
  &:hover {
    background-color: #ede9fe !important;
    color: #7b42f6 !important;
    font-weight: 600;
  }
}

// ====== 响应式 ======
@media (max-width: 768px) {
  .stats-row {
    flex-wrap: wrap;

    .stat-card {
      flex: 0 0 calc(50% - 7px);
    }
  }

  .config-row {
    flex-direction: column;
    align-items: stretch;

    .config-item {
      width: 100% !important;
    }

    .gen-btn {
      width: 100%;
    }
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .filter-tabs {
    flex-wrap: wrap;
  }
}
</style>
