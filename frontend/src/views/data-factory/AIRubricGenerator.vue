<template>
  <div class="ai-rubric-container">
    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon purple"><el-icon><DataAnalysis /></el-icon></div>
        <div>
          <div class="stat-num">{{ stats.total }}</div>
          <div class="stat-label">累计生成</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green"><el-icon><CircleCheck /></el-icon></div>
        <div>
          <div class="stat-num">{{ stats.done }}</div>
          <div class="stat-label">已完成</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon yellow"><el-icon><Loading /></el-icon></div>
        <div>
          <div class="stat-num">{{ stats.running }}</div>
          <div class="stat-label">生成中</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon blue"><el-icon><Document /></el-icon></div>
        <div>
          <div class="stat-num">{{ stats.files }}</div>
          <div class="stat-label">文件数量</div>
        </div>
      </div>
    </div>

    <!-- 上传卡片 -->
    <el-card shadow="hover" class="upload-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><Upload /></el-icon> 上传文件生成量表
            <el-tag size="small" type="primary" effect="plain" style="margin-left:8px;">支持文档/图片</el-tag>
          </span>
        </div>
      </template>
      <p class="card-desc">上传教学内容相关文档（.docx / .pdf / .txt）或图片（.png / .jpg），AI将自动分析内容并生成评分量表和学习心得</p>

      <!-- 上传区域 -->
      <el-upload
        v-show="!uploadedFile"
        ref="uploadRef"
        drag
        :auto-upload="false"
        :limit="1"
        :show-file-list="false"
        accept=".docx,.pdf,.txt,.png,.jpg,.jpeg,.xlsx"
        @change="handleFileChange"
      >
        <div class="upload-content">
          <el-icon :size="48" color="#e0d4ff"><UploadFilled /></el-icon>
          <p class="upload-text">拖拽文件到此处，或点击选择文件</p>
          <p class="upload-tip">支持 .docx · .pdf · .txt · .png · .jpg 格式，最大 20MB</p>
          <el-button type="primary" class="upload-btn"><el-icon><UploadFilled /></el-icon> 选择文件</el-button>
        </div>
      </el-upload>

      <!-- 已选文件信息 -->
      <div v-if="uploadedFile" class="file-info-row">
        <div class="file-item">
          <img v-if="isImageFile(uploadedFile.name)" :src="getImagePreview(uploadedFile)" class="file-thumb" />
          <el-icon v-else class="file-doc-icon"><Document /></el-icon>
          <span class="file-name">{{ uploadedFile.name }}</span>
          <span class="file-size">({{ formatFileSize(uploadedFile.size) }})</span>
        </div>
        <el-button link class="file-remove-btn" @click="clearFile"><el-icon><Close /></el-icon></el-button>
      </div>

      <!-- 配置行 -->
      <div class="config-row">
        <el-form-item label="任务名称" class="config-name-item">
          <el-input v-model="form.taskName" placeholder="例：AI技术与学科融合评分量表" />
        </el-form-item>
        <el-form-item label="心得数量" class="config-count-item">
          <el-select v-model="form.noteCount">
            <el-option label="10 条" :value="10" />
            <el-option label="20 条（推荐）" :value="20" />
            <el-option label="30 条" :value="30" />
          </el-select>
        </el-form-item>
        <el-form-item label="得分心得比例" class="config-ratio-item">
          <el-select v-model="form.passRatio">
            <el-option label="各占50%" :value="0.5" />
            <el-option label="60% 得 / 40% 不" :value="0.6" />
            <el-option label="70% 得 / 30% 不" :value="0.7" />
          </el-select>
        </el-form-item>
        <el-form-item label="心得字数" class="config-length-item">
          <el-select v-model="form.noteLength">
            <el-option label="100 字左右" :value="100" />
            <el-option label="300 字左右（推荐）" :value="300" />
            <el-option label="500 字左右" :value="500" />
          </el-select>
        </el-form-item>
        <el-button type="primary" class="gen-btn" @click="startGenerate" :disabled="!form.taskName.trim() || generating">
          <el-icon><MagicStick /></el-icon>
          开始生成
        </el-button>
      </div>
      <p class="config-tip">若生成失败，则会取用默认模板并根据配置项生成量表和心得</p>
    </el-card>

    <!-- 记录列表卡片 -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header" style="justify-content:space-between;">
          <span class="card-title">
            <el-icon><List /></el-icon> 生成记录
            <el-tag size="small" type="info" effect="plain" style="margin-left:8px;">共 {{ filteredRecords.length }} 条</el-tag>
          </span>
          <div class="filter-tabs">
            <el-radio-group v-model="currentFilter" size="small" @change="fetchRecords">
              <el-radio-button value="all">全部状态</el-radio-button>
              <el-radio-button value="running">生成中</el-radio-button>
              <el-radio-button value="done">已完成</el-radio-button>
              <el-radio-button value="error">失败</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>

      <div class="search-bar">
        <el-input
          v-model="searchText"
          placeholder="搜索任务名称..."
          clearable
          prefix-icon="Search"
          style="max-width:300px;"
          @input="onSearch"
        />
      </div>

      <!-- 表格 -->
      <el-table
        :data="paginatedRecords"
        stripe
        v-loading="tableLoading"
        empty-text="暂无生成记录，上传文件后点击「开始生成」"
        style="width:100%"
      >
        <el-table-column prop="id" label="序号" width="65" align="center">
          <template #default="{ $index }">{{ (currentPage - 1) * pageSize + $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="任务名称" min-width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="previewRecord(row)" :underline="false" style="font-weight:500;">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="source_file_name" label="关联文件" width="120" align="center">
          <template #default="{ row }">
            <span style="font-size:12px;color:#666;">{{ row.source_file_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="statusTagType(row.status)"
              size="small"
              :effect="row.status === 'running' ? 'dark' : 'light'"
              round
            >
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="心得数量" width="90" align="center">
          <template #default="{ row }">
            {{ row.note_count || '-' }} 条
            <small v-if="row.status === 'done'" style="color:#999;">
              ({{ Math.round(row.pass_ratio * 100) }}%得分)
            </small>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="160" align="center" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <!-- done 或 error 状态都允许查看（error 时有 fallback 数据） -->
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
              <el-tag size="small" type="primary" round>
                处理中
              </el-tag>
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
          style="margin-top:16px;justify-content:center;"
        />
      </div>
    </el-card>

    <!-- 删除确认对话框（居中） -->
    <el-dialog
      v-model="deleteDialogVisible"
      title="确认删除"
      width="420px"
      align-center
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div style="display:flex;align-items:flex-start;gap:12px;">
        <el-icon :size="22" color="#E6A23C" style="flex-shrink:0;margin-top:2px;"><WarningFilled /></el-icon>
        <span style="color:#606266;line-height:1.6;">确定要删除该任务吗？此操作将同时删除关联的量表和心得，删除后不可恢复。</span>
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
    >
      <el-tabs v-model="previewTab" v-if="previewData">
        <el-tab-pane label="评分量表" name="rubric">
          <div v-if="previewData.rubric_data && previewData.rubric_data.length" class="rubric-preview">
            <p style="margin-bottom:12px;font-size:13px;color:#666;">
              共 <strong>{{ uniqueLevel1Count }}</strong> 个一级指标，
              <strong>{{ previewData.rubric_data.length }}</strong> 个二级指标
            </p>
            <el-table :data="previewData.rubric_data" border stripe size="small" max-height="480">
              <el-table-column prop="seq" label="#" width="50" align="center" />
              <el-table-column prop="level1" label="一级指标" width="150">
                <template #default="{ row }">
                  <span v-if="isFirstInLevel1(row)" style="font-weight:600;color:#7c3aed;">{{ row.level1 }}</span>
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
            <div style="display:flex;gap:10px;margin-bottom:14px;font-size:13px;">
              <span style="color:#666;">共 <strong>{{ previewData.notes_data.length }}</strong> 条心得：</span>
              <el-tag size="small" type="success" round>得心 {{ passNoteCount }}条</el-tag>
              <el-tag size="small" type="danger" round>不得心 {{ failNoteCount }}条</el-tag>
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
                  <el-tag :type="note.type === 'pass' ? 'success' : 'danger'" size="small" round>
                    {{ note.type === 'pass' ? '得分' : '不得分' }}
                  </el-tag>
                </div>
                <div class="note-body">{{ note.body }}</div>
                <div class="note-meta">
                  <el-tag size="small" :type="note.type === 'pass' ? '' : 'danger'" effect="plain" round>观点{{ note.type === 'pass' ? '正确' : '偏差' }}</el-tag>
                  <el-tag size="small" :type="note.type === 'pass' ? '' : 'danger'" effect="plain" round>逻辑{{ note.type === 'pass' ? '清晰' : '不足' }}</el-tag>
                  <el-tag size="small" :type="note.type === 'pass' ? '' : 'danger'" effect="plain" round>内容{{ note.type === 'pass' ? '完整' : '欠缺' }}</el-tag>
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
  MagicStick, List, View, Download, Delete, Close, WarningFilled,
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
// 删除确认对话框
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
  return { done: 'success', running: 'warning', error: 'danger' }[status] || 'info'
}

function statusText(status) {
  return { done: '已完成', running: '生成中', error: '失败' }[status] || status
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

function isImageFile(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes(ext)
}

function getImagePreview(file) {
  return URL.createObjectURL(file)
}

function handleFileChange(uploadFile) {
  uploadedFile.value = uploadFile.raw
  if (!form.taskName && uploadFile.raw) {
    form.taskName = uploadFile.raw.name.replace(/\.[^.]+$/, '') + ' - 量表生成'
  }
}

function handleFileRemove() {
  uploadedFile.value = null
}

function clearFile() {
  if (uploadRef.value) uploadRef.value.clearFiles()
  uploadedFile.value = null
}

async function fetchStats() {
  try {
    const res = await getRubricStatistics()
    if (res.data.success) {
      Object.assign(stats, res.data.data)
    }
  } catch (e) {
    console.warn('获取统计失败:', e)
  }
}

async function fetchRecords() {
  tableLoading.value = true
  try {
    const params = {}
    if (currentFilter.value && currentFilter.value !== 'all') params.status = currentFilter.value
    const res = await getRubricRecords(params)
    if (res.data.success) {
      records.value = res.data.data
      Object.assign(stats, res.data.stats)
    }
  } catch (e) {
    console.error('获取记录失败:', e)
  } finally {
    tableLoading.value = false
  }
}

function onSearch() {
  currentPage.value = 1
}

async function startGenerate() {
  if (!form.taskName.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  if (generating.value) return // 防止重复提交
  generating.value = true

  try {
    const formData = new FormData()
    formData.append('name', form.taskName.trim())
    formData.append('note_count', String(form.noteCount))
    formData.append('pass_ratio', String(form.passRatio))
    formData.append('note_length', String(form.noteLength))
    if (uploadedFile.value) {
      formData.append('file', uploadedFile.value)
    }

    // 发起请求（不阻塞），延迟刷新列表确保后端事务已提交
    const reqPromise = generateRubric(formData)
    // 延迟 1000ms 再刷新，确保后端 transaction.atomic() 已提交新记录
    setTimeout(() => {
      fetchRecords()
      fetchStats()
    }, 1000)

    const res = await reqPromise

    if (res.data.success) {
      const d = res.data.data
      clearFile()
      form.taskName = ''
      await fetchRecords()
      await fetchStats()

      if (d.status === 'error') {
        ElMessage.error(`AI 生成失败: ${d.warning || 'AI 调用异常'}（已使用默认模板）`)
      } else {
        ElMessage.success(`生成完成！${d.rubric_count}个指标 + ${d.notes_count}条心得`)
      }
    } else {
      ElMessage.error(res.data.error || '生成失败')
      await fetchRecords()
    }
  } catch (e) {
    console.error('生成失败:', e)
    ElMessage.error(e.response?.data?.error || e.message || '生成失败，请重试')
    await fetchRecords()
  } finally {
    generating.value = false
  }
}

async function previewRecord(record) {
  try {
    // 如果当前记录有完整数据，直接使用
    if (record.rubric_data && record.notes_data) {
      previewData.value = record
    } else {
      // 否则从后端获取详情
      const res = await import('@/api/data-factory').then(m =>
        m.getRubricDetail(record.id)
      )
      if (res.data.success) {
        previewData.value = res.data.data
      } else {
        ElMessage.error(res.data.error || '获取详情失败')
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

  // 样式
  for (const cell of ['A1','B1','C1','D1']) {
    if (ws[cell]) ws[cell].s = {
      font: { bold: true, color: { rgb: 'FFFFFF' } },
      fill: { fgColor: { rgb: '7C3AED' } },
      alignment: { horizontal: 'center' }
    }
  }

  XLSX.utils.book_append_sheet(wb, ws, '评分量表')

  // 心得sheet
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

  // 使用 Word 兼容的 HTML 格式（Word 可直接打开）
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

  const blob = new Blob([html], {
    type: 'application/msword;charset=utf-8'
  })
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
  max-width: 1200px;
  margin: 0 auto;
}

.stats-row {
  display: flex;
  gap: 14px;
  margin-bottom: 20px;

  .stat-card {
    flex: 1;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 12px;

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

.upload-card {
  margin-bottom: 20px;

  .card-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    font-size: 15px;
  }

  .card-desc {
    font-size: 12.5px;
    color: #9ca3af;
    margin: 0 0 16px;
  }

  .upload-content {
    padding: 40px 0;
    display: flex;
    flex-direction: column;
    align-items: center;

    .upload-text {
      font-size: 14px;
      color: #374151;
      font-weight: 500;
      margin-top: 12px;
    }

    .upload-tip {
      font-size: 12px;
      color: #9ca3af;
      margin-top: 8px;
    }

    .upload-btn {
      margin-top: 14px;
      border-radius: 20px;
    }
  }

  :deep(.el-upload-dragger) {
        border: 2px dashed #c4b5fd !important;
    background: linear-gradient(180deg, #f5f0ff 0%, #ede9fe 100%) !important;
    border-radius: 10px !important;
    transition: all 0.3s;
    height: 255px !important;
    min-height: unset !important;
    padding: 20px 10px !important;
    &:hover {
      border-color: #7c3aed;
      background: linear-gradient(180deg, #ede9fe 0%, #ddd6fe 100%);
    }
  }

  .file-info-row {
    margin-top: 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    background: #fafafa;
    border-radius: 8px;
    border: 1px solid #eee;

    .file-item {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      flex: 1;
    }

    .file-thumb {
      width: 28px;
      height: 28px;
      object-fit: cover;
      border-radius: 4px;
      border: 1px solid #e5e7eb;
    }

    .file-doc-icon {
      font-size: 22px;
      color: #9ca3af;
      flex-shrink: 0;
    }

    .file-name {
      font-size: 13px;
      color: #374151;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .file-size {
      font-size: 11.5px;
      color: #b0b0b0;
      flex-shrink: 0;
    }

    .file-remove-btn {
      color: #999;
      padding: 4px;
      flex-shrink: 0;
      &:hover { color: #ef4444; }
    }
  }

    .config-row {
    display: flex;
    gap: 16px;
    margin-top: 20px;
    align-items: flex-end;
    flex-wrap: wrap;

    .config-name-item { width: 260px; min-width: 200px; flex: none; }
    .config-count-item { width: 130px; flex-shrink: 0; }
    .config-ratio-item { width: 160px; flex-shrink: 0; }
    .config-length-item { width: 165px; flex-shrink: 0; }

    :deep(.el-form-item) { margin-bottom: 0; }
    :deep(.el-form-item__label) {
      font-size: 13px;
      color: #606266;
      font-weight: 500;
    }

    :deep(.el-select),
    :deep(.el-input__wrapper) {
      height: 32px;
    }

    .gen-btn {
      border-radius: 6px;
      padding: 0 26px;
      height: 32px;
      line-height: 30px;
      flex-shrink: 0;
      font-size: 13px;
    }

    .config-tip {
      margin-top: 10px;
      font-size: 12px;
      color: #909399;
      line-height: 1.5;
    }
  }
}

.card-header {
  display: flex;
  align-items: center;

  .card-title {
    display: flex;
    align-items: center;
    font-weight: 600;
    font-size: 15px;
  }
}

.search-bar {
  margin-bottom: 12px;
}

.pagination-bar {
  display: flex;
  justify-content: center;
}

// ====== 预览弹窗样式 ======
.rubric-preview {
  max-height: 520px;
  overflow-y: auto;
}

.notes-preview {
  max-height: 520px;
  overflow-y: auto;
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.note-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.2s;

  &:hover { border-color: #c4b5fd; box-shadow: 0 2px 12px rgba(124,58,237,.08); }

  &.fail-note {
    border-color: #fecaca;

    &:hover { border-color: #ef4444; box-shadow: 0 2px 12px rgba(239,68,68,.08); }
  }

  .note-header {
    padding: 10px 14px;
    background: #f9fafb;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #f3f4f6;
  }

  .note-num {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #7c3aed;
    color: #fff;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
  }

  .note-title {
    font-size: 13.5px;
    font-weight: 600;
    flex: 1;
  }

  .note-body {
    padding: 12px 14px;
    font-size: 13px;
    line-height: 1.75;
    color: #374151;
    white-space: pre-wrap;
  }

  .note-meta {
    padding: 8px 14px;
    background: #fafafa;
    border-top: 1px solid #f3f4f6;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
}
</style>
