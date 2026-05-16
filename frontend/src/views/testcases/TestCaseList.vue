<template>
  <div class="page-container">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="searchText"
        :placeholder="$t('testcase.searchPlaceholder')"
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
        style="width: 280px;"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select
        v-model="moduleFilter"
        :placeholder="$t('testcase.moduleFilter')"
        clearable
        @change="handleFilter"
        style="width: 150px;"
        :popper-options="{ modifiers: [{ name: 'computeStyles', options: { gpuAcceleration: false } }] }"
      >
        <el-scrollbar max-height="200px">
          <el-option
            v-for="module in uniqueModules"
            :key="module"
            :label="module"
            :value="module"
          />
        </el-scrollbar>
      </el-select>
      <el-select v-model="priorityFilter" :placeholder="$t('testcase.priorityFilter')" clearable @change="handleFilter" style="width: 150px;">
        <el-option label="P0" value="critical" />
        <el-option label="P1" value="high" />
        <el-option label="P2" value="medium" />
        <el-option label="P3" value="low" />
      </el-select>
      <div class="filter-bar-spacer"></div>
      <el-button v-show="selectedTestCases.length > 0" type="danger" class="action-btn" @click="batchDeleteTestCases" :loading="isDeleting">
        <el-icon><Delete /></el-icon>
        <span>{{ $t('testcase.batchDelete') }}</span>
      </el-button>
      <el-button type="success" class="action-btn" @click="handleImport">
        <el-icon><Upload /></el-icon>
        <span>{{ $t('testcase.import') }}</span>
      </el-button>
      <el-button type="warning" class="action-btn" @click="exportToExcel">
        <el-icon><Download /></el-icon>
        <span>{{ $t('testcase.export') }}</span>
      </el-button>
      <el-button type="primary" class="action-btn edit-btn" @click="$router.push('/ai-generation/testcases/create')">
        <el-icon><Plus /></el-icon>
        <span>{{ $t('testcase.newCase') }}</span>
      </el-button>
    </div>

    <!-- 表格容器 -->
    <div class="card-container history-card">
      <el-table
        ref="tableRef"
        :data="testcases"
        v-loading="loading"
        stripe
        style="width: 100%"
        :row-class-name="getRowClassName"
        @selection-change="handleSelectionChange">
        <!-- 复选框 -->
        <el-table-column type="selection" width="55" header-align="center" align="center" class-name="selection-cell"></el-table-column>
        <!-- 用例编号 -->
        <el-table-column :label="$t('testcase.serialNumber')" width="80" header-align="center" align="center">
          <template #default="{ $index }">
            {{ (currentPage - 1) * pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <!-- 用例名称 -->
        <el-table-column :label="$t('testcase.caseTitle')" min-width="400" show-overflow-tooltip header-align="center" align="left">
          <template #default="{ row }">
            <span class="case-name clickable" @click="goToTestCase(row.id)">
              {{ row.title }}
            </span>
          </template>
        </el-table-column>
        <!-- 模块 -->
        <el-table-column :label="$t('testcase.moduleLabel')" width="130" header-align="center" align="center" class-name="module-cell">
          <template #default="{ row }">
            <span class="module-content">{{ row.module || '-' }}</span>
          </template>
        </el-table-column>
        <!-- 用例级别 -->
        <el-table-column :label="$t('testcase.priority')" width="98" header-align="center" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="row.priority">
              {{ getPriorityText(row.priority) }}
            </span>
          </template>
        </el-table-column>
        <!-- 创建者 -->
        <el-table-column :label="$t('testcase.author')" width="98" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.author">{{ row.author.username }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        <!-- 创建时间 -->
        <el-table-column :label="$t('testcase.createdAt')" width="135" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <!-- 操作 -->
        <el-table-column :label="$t('project.actions')" width="180" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" class="action-btn edit-btn" @click="editTestCase(row)">
                <el-icon><Edit /></el-icon>
                <span>{{ $t('common.edit') }}</span>
              </el-button>
              <el-button size="small" type="danger" class="action-btn delete-btn" @click="deleteTestCase(row)">
                <el-icon><Delete /></el-icon>
                <span>{{ $t('common.delete') }}</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
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
    </div>

    <!-- 导入对话框 - 步骤引导 -->
    <el-dialog
      v-model="importDialogVisible"
      :title="importStep === 3 ? $t('testcase.importResult') : $t('testcase.importTitle')"
      width="900px"
      :close-on-click-modal="false"
      :show-close="importStep !== 2"
      :close-on-press-escape="importStep !== 2"
      class="import-dialog"
    >


      <div class="import-container">
        <!-- 步骤1: 文件上传 -->
        <div v-if="importStep === 0" class="upload-section">
          <el-upload
            ref="uploadRef"
            class="upload-demo"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :limit="1"
            accept=".xlsx,.xls"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              {{ $t('testcase.dragFile') }} <em>{{ $t('testcase.clickUpload') }}</em>
            </div>
          </el-upload>
        </div>

        <!-- 步骤2: 数据预览 -->
        <div v-if="importStep === 1" class="preview-section">
          <el-table :data="previewData" stripe style="width: 100%" max-height="480">
            <el-table-column
              v-for="field in previewFields"
              :key="field.key"
              :prop="field.key"
              :label="field.label"
              :min-width="getPreviewColumnWidth(field.systemKey)"
              show-overflow-tooltip
            />
          </el-table>
        </div>

        <!-- 步骤3: 导入结果 -->
        <div v-if="importStep === 3" class="import-result" :class="{ 'import-success': importResult.success && importResult.failCount === 0 }">
          <!-- 导入成功时的特殊布局 -->
          <template v-if="importResult.success && importResult.failCount === 0">
            <div class="success-icon-wrapper">
              <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
            </div>
            <div class="result-title">{{ $t('testcase.importSuccess') }}</div>
            <div class="result-message">{{ importResult.message }}</div>
          </template>
          <!-- 导入失败/部分成功时的布局 -->
          <template v-else>
            <div class="result-header">
              <el-icon class="warning-icon"><WarningFilled /></el-icon>
              <span class="result-title">{{ $t('testcase.importPartialSuccess') }}</span>
            </div>
            <div class="result-message">{{ importResult.message }}</div>
            <div v-if="importResult.errors.length > 0" class="error-list">
              <h5>{{ $t('testcase.errorDetails') }} (共 {{ importResult.errors.length }} 条)</h5>
              <el-scrollbar max-height="420px">
                <div v-for="(error, index) in importResult.errors" :key="index" class="error-item">
                  <span class="error-index">{{ index + 1 }}.</span> {{ error }}
                </div>
              </el-scrollbar>
            </div>
          </template>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <!-- 步骤0: 上传文件 -->
          <template v-if="importStep === 0">
            <el-button @click="importDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button 
              type="primary" 
              @click="goToPreview" 
              :disabled="excelData.length === 0"
              class="action-btn edit-btn"
            >
              下一步
            </el-button>
          </template>

          <!-- 步骤1: 预览确认 -->
          <template v-if="importStep === 1">
            <el-button @click="importStep = 0">上一步</el-button>
            <el-button 
              type="primary" 
              @click="confirmImport" 
              :loading="isImporting"
              class="action-btn edit-btn"
            >
              确认导入
            </el-button>
          </template>

          <!-- 步骤3: 导入完成 -->
          <template v-if="importStep === 3">
            <el-button class="action-btn edit-btn" @click="closeImportDialog">{{ $t('common.confirm') }}</el-button>
          </template>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch, inject, onActivated, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Download, Delete, Edit, Upload, UploadFilled, Right, WarningFilled, CircleCheckFilled } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'
import * as XLSX from 'xlsx'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

// 注入刷新项目列表的方法
const refreshProjects = inject('refreshProjects', () => {})
const loading = ref(false)
const testcases = ref([])
const currentPage = ref(1)
const pageSize = ref(15)
const total = ref(0)
const searchText = ref('')
const tableRef = ref(null)
const moduleFilter = ref('')
const priorityFilter = ref('')
const projectFilter = ref('')
const menuFilter = ref('') // 当前选中的菜单ID
const highlightId = ref(null) // 需要高亮的用例ID
const selectedTestCases = ref([])
const isDeleting = ref(false)

// 所有模块列表（用于筛选下拉）
const allModules = ref([])

// 从所有模块数据中提取唯一的模块
const uniqueModules = computed(() => {
  return Array.from(allModules.value).sort()
})

// 获取所有模块（使用专用API）
const fetchAllModules = async () => {
  try {
    const response = await api.get('/testcases/modules/')
    allModules.value = response.data || []
    console.log('Fetched modules:', allModules.value)
  } catch (error) {
    console.error('Failed to fetch modules:', error)
  }
}

// 导入相关
const importDialogVisible = ref(false)
const importStep = ref(0) // 0:上传文件, 1:预览确认, 3:导入完成
const uploadRef = ref(null)
const excelHeaders = ref([])
const excelData = ref([])
const fieldMapping = ref({})
const isImporting = ref(false)
const importResult = ref({
  success: true,
  message: '',
  successCount: 0,
  failCount: 0,
  errors: []
})

// 进入预览步骤
const goToPreview = () => {
  if (excelData.value.length > 0) {
    importStep.value = 1
  }
}

// 关闭导入对话框
const closeImportDialog = () => {
  importDialogVisible.value = false
  // 重置状态
  setTimeout(() => {
    importStep.value = 0
    excelHeaders.value = []
    excelData.value = []
    fieldMapping.value = {}
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
  }, 300)
}

// 可映射的系统字段（以Excel字段为主）
const availableFields = computed(() => [
  { key: 'title', label: t('testcase.caseTitle'), required: true },
  { key: 'preconditions', label: t('testcase.preconditions'), required: false },
  { key: 'steps', label: t('testcase.steps'), required: false },
  { key: 'expected_result', label: t('testcase.expectedResult'), required: false },
  { key: 'priority', label: t('testcase.priority'), required: false },
  { key: 'test_type', label: t('testcase.testType'), required: false },
  { key: 'description', label: t('testcase.caseDescription'), required: false },
  { key: 'module', label: t('testcase.moduleLabel'), required: false },
  { key: 'category_path', label: t('testcase.project'), required: false },
  { key: 'author_name', label: t('testcase.author'), required: false }
])

// 默认字段映射（根据Excel文件字段预设）
const defaultFieldMapping = {
  '用例编号': '',
  '归属目录': 'category_path',
  '模块': 'module',
  '*用例名称': 'title',
  '前置条件': 'preconditions',
  '测试步骤1': 'steps',
  '预期结果1': 'expected_result',
  '用例级别': 'priority',
  '测试步骤模式': 'test_type',
  '创建者': 'author_name',
  '创建时间': ''
}

// 计算属性：已映射的字段
const mappedFields = computed(() => {
  const mapped = []
  Object.entries(fieldMapping.value).forEach(([excelField, systemField]) => {
    if (systemField) {
      const field = availableFields.value.find(f => f.key === systemField)
      if (field) {
        mapped.push({
          key: excelField,
          label: field.label,
          systemKey: systemField
        })
      }
    }
  })
  return mapped
})

// 计算属性：预览字段（只显示用例名称、归属目录、创建人）
const previewFields = computed(() => {
  const allowedSystemFields = ['title', 'category_path', 'author_name']

  const preview = []
  Object.entries(fieldMapping.value).forEach(([excelField, systemField]) => {
    if (systemField && allowedSystemFields.includes(systemField)) {
      const field = availableFields.value.find(f => f.key === systemField)
      if (field) {
        preview.push({
          key: excelField,
          label: field.label,
          systemKey: systemField
        })
      }
    }
  })
  return preview
})

// 计算属性：是否可以导入
const canImport = computed(() => {
  // 至少要有标题字段的映射
  const hasTitleMapping = Object.values(fieldMapping.value).includes('title')
  return hasTitleMapping && excelData.value.length > 0
})

// 计算属性：预览数据（显示所有数据）
const previewData = computed(() => {
  return excelData.value.map(row => {
    const preview = {}
    Object.entries(fieldMapping.value).forEach(([excelField, systemField]) => {
      if (systemField && row[excelField] !== undefined) {
        preview[excelField] = row[excelField]
      }
    })
    return preview
  })
})

// 打开导入对话框
const handleImport = () => {
  importDialogVisible.value = true
  importStep.value = 0
  excelHeaders.value = []
  excelData.value = []
  fieldMapping.value = {}
}

// 处理文件变化
const handleFileChange = (file) => {
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const result = e.target?.result
      if (!result || typeof result === 'string') {
        ElMessage.error(t('testcase.readFileFailed'))
        return
      }
      const data = new Uint8Array(result)
      const workbook = XLSX.read(data, { type: 'array' })
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
      const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 })

      if (jsonData.length < 2) {
        ElMessage.warning(t('testcase.emptyExcel'))
        return
      }

      // 获取表头
      const headers = jsonData[0].filter(h => h !== undefined && h !== null && h !== '')
      excelHeaders.value = headers

      // 初始化字段映射（使用默认映射）
      const mapping = {}
      headers.forEach(header => {
        mapping[header] = defaultFieldMapping[header] || ''
      })
      fieldMapping.value = mapping

      // 解析数据行
      const rows = []
      for (let i = 1; i < jsonData.length; i++) {
        const row = jsonData[i]
        if (row.every(cell => cell === undefined || cell === null || cell === '')) continue

        const rowData = {}
        headers.forEach((header, index) => {
          let value = row[index]
          // 处理Excel日期格式
          if (typeof value === 'number' && value > 40000 && value < 50000) {
            const date = XLSX.SSF.parse_date_code(value)
            value = `${date.y}-${String(date.m).padStart(2, '0')}-${String(date.d).padStart(2, '0')}`
          }
          rowData[header] = value !== undefined ? String(value) : ''
        })
        rows.push(rowData)
      }
      excelData.value = rows

      ElMessage.success(t('testcase.parseSuccess', { count: rows.length }))

      // 自动进入预览步骤
      setTimeout(() => {
        importStep.value = 1
      }, 500)
    } catch (error) {
      console.error('Parse Excel failed:', error)
      ElMessage.error(t('testcase.parseFailed'))
    }
  }
  reader.readAsArrayBuffer(file.raw)
}

// 处理文件移除
const handleFileRemove = () => {
  excelHeaders.value = []
  excelData.value = []
  fieldMapping.value = {}
}

// 优先级映射（从Excel值到系统值）
const mapPriority = (excelPriority) => {
  const priorityMap = {
    'Priority 0': 'critical',
    'Priority 1': 'high',
    'Priority 2': 'medium',
    'Priority 3': 'low',
    '紧急': 'critical',
    '高': 'high',
    '中': 'medium',
    '低': 'low',
    'critical': 'critical',
    'high': 'high',
    'medium': 'medium',
    'low': 'low'
  }
  return priorityMap[excelPriority] || 'medium'
}

const mapTestType = (excelType) => {
  const typeMap = {
    '文本模式': 'text',
    '步骤模式': 'step',
    'text': 'text',
    'step': 'step'
  }
  return typeMap[excelType] || 'text'
}

// 确认导入
const confirmImport = async () => {
  if (!canImport.value) {
    ElMessage.warning(t('testcase.noTitleMapping'))
    return
  }

  isImporting.value = true
  const errors = []
  let successCount = 0
  let failCount = 0

  try {
    // 获取所有现有用例名称用于去重校验
    const existingTitles = new Set()
    try {
      const response = await api.get('/testcases/', { params: { page_size: 10000 } })
      const allTestCases = response.data.results || []
      allTestCases.forEach(tc => {
        if (tc.title) {
          existingTitles.add(tc.title.trim())
        }
      })
    } catch (error) {
      console.error('Failed to fetch existing test cases:', error)
    }

    for (let i = 0; i < excelData.value.length; i++) {
      const row = excelData.value[i]
      const testcaseData = {
        title: '',
        preconditions: '',
        steps: '',
        expected_result: '',
        priority: 'medium',
        test_type: 'text',
        description: '',
        module: ''
      }

      // 处理创建者字段（直接从Excel行数据读取）
      if (row['创建者'] !== undefined) {
        testcaseData.author_name = row['创建者']
      }

      // 处理创建时间字段（直接从Excel行数据读取）
      if (row['创建时间'] !== undefined) {
        testcaseData.created_at = row['创建时间']
      }

      // 处理归属目录字段（直接从Excel行数据读取，格式：端名称/菜单/子菜单）
      if (row['归属目录'] !== undefined) {
        testcaseData.category_path = row['归属目录']
      }

      // 根据字段映射转换数据
      Object.entries(fieldMapping.value).forEach(([excelField, systemField]) => {
        if (!systemField || row[excelField] === undefined) return

        const value = row[excelField]
        // 跳过用例编号（系统自动生成）
        if (excelField === '用例编号') return

        // 跳过创建时间、创建者和归属目录（已单独处理）
        if (excelField === '创建时间' || excelField === '创建者' || excelField === '归属目录') return

        switch (systemField) {
          case 'title':
            testcaseData.title = value
            break
          case 'preconditions':
            testcaseData.preconditions = value
            break
          case 'steps':
            testcaseData.steps = value
            break
          case 'expected_result':
            testcaseData.expected_result = value
            break
          case 'priority':
            testcaseData.priority = mapPriority(value)
            break
          case 'test_type':
            testcaseData.test_type = mapTestType(value)
            break
          case 'description':
            testcaseData.description = value
            break
          case 'module':
            testcaseData.module = value
            break
        }
      })

      // 验证必填字段
      if (!testcaseData.title) {
        errors.push(t('testcase.rowNoTitle', { row: i + 2 }))
        failCount++
        continue
      }

      // 验证用例名称是否重复
      if (existingTitles.has(testcaseData.title.trim())) {
        errors.push(`第 ${i + 2} 行：用例名称 "${testcaseData.title}" 已存在，跳过导入`)
        failCount++
        continue
      }

      try {
        await api.post('/testcases/', testcaseData)
        successCount++
      } catch (error) {
        console.error(`Import row ${i + 2} failed:`, error)
        let errorMsg = error.message || t('common.error')
        if (error.response && error.response.data) {
          const responseData = error.response.data
          if (typeof responseData === 'object') {
            errorMsg = Object.entries(responseData).map(([key, value]) => {
              return `${key}: ${Array.isArray(value) ? value.join(', ') : value}`
            }).join('; ')
          } else {
            errorMsg = String(responseData)
          }
        }
        errors.push(t('testcase.rowImportFailed', { row: i + 2, error: errorMsg }))
        failCount++
      }
    }

    // 显示导入结果
    importResult.value = {
      success: failCount === 0,
      message: failCount === 0
        ? t('testcase.importAllSuccess', { count: successCount })
        : t('testcase.importPartialMessage', { success: successCount, fail: failCount }),
      successCount,
      failCount,
      errors: errors // 显示所有错误
    }
    // 进入结果步骤
    importStep.value = 3

    if (successCount > 0) {
      // 刷新列表和模块筛选
      fetchTestCases()
      fetchAllModules()
      // 刷新侧边栏项目列表（如果导入了新项目）
      refreshProjects()
    }
  } catch (error) {
    console.error('Import failed:', error)
    ElMessage.error(t('testcase.importFailed'))
  } finally {
    isImporting.value = false
  }
}

const filters = reactive({
  search: '',
  project: '',
  priority: ''
})

const fetchTestCases = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    // 只传递非空参数，避免 DjangoFilterBackend 对空字符串进行过滤
    if (searchText.value) {
      params.search = searchText.value
    }
    if (moduleFilter.value) {
      params.module = moduleFilter.value
    }
    if (priorityFilter.value) {
      params.priority = priorityFilter.value
    }
    if (projectFilter.value) {
      params.project = projectFilter.value
    }
    if (menuFilter.value) {
      params.menu = menuFilter.value
    }
    const response = await api.get('/testcases/', { params })
    testcases.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    ElMessage.error(t('testcase.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchTestCases()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchTestCases()
}

const handleCurrentChange = () => {
  fetchTestCases()
}

const handleSizeChange = () => {
  currentPage.value = 1
  fetchTestCases()
}

const goToTestCase = (id) => {
  router.push(`/ai-generation/testcases/${id}`)
}

const editTestCase = (testcase) => {
  router.push(`/ai-generation/testcases/${testcase.id}/edit`)
}

const deleteTestCase = async (testcase) => {
  try {
    await ElMessageBox.confirm(
      t('testcase.deleteConfirm'),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    await api.delete(`/testcases/${testcase.id}/`)
    ElMessage.success(t('testcase.deleteSuccess'))
    fetchTestCases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('testcase.deleteFailed'))
    }
  }
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedTestCases.value = selection
}

// 批量删除
const batchDeleteTestCases = async () => {
  if (selectedTestCases.value.length === 0) {
    ElMessage.warning(t('testcase.selectFirst'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('testcase.batchDeleteConfirm', { count: selectedTestCases.value.length }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    isDeleting.value = true
    let successCount = 0
    let failCount = 0

    for (const testcase of selectedTestCases.value) {
      try {
        await api.delete(`/testcases/${testcase.id}/`)
        successCount++
      } catch (error) {
        console.error(`Delete test case ${testcase.id} failed:`, error)
        failCount++
      }
    }

    if (successCount > 0) {
      if (failCount > 0) {
        ElMessage.success(t('testcase.batchDeletePartialSuccess', { successCount, failCount }))
      } else {
        ElMessage.success(t('testcase.batchDeleteSuccess', { successCount }))
      }
    } else {
      ElMessage.error(t('testcase.batchDeleteFailed'))
    }

    selectedTestCases.value = []
    fetchTestCases()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Batch delete failed:', error)
      ElMessage.error(t('testcase.batchDeleteError') + ': ' + (error.message || t('common.error')))
    }
  } finally {
    isDeleting.value = false
  }
}

const getPriorityText = (priority) => {
  const textMap = {
    critical: 'P0',
    high: 'P1',
    medium: 'P2',
    low: 'P3'
  }
  return textMap[priority] || priority
}

// 获取预览表格列宽：创建者固定宽度靠右，归属目录和用例名称占据剩余空间
const getPreviewColumnWidth = (systemKey) => {
  if (systemKey === 'author_name') {
    return 100 // 创建者固定较窄宽度
  } else if (systemKey === 'title') {
    return 350 // 用例名称较宽
  } else if (systemKey === 'category_path') {
    return 280 // 归属目录较宽
  }
  return 120
}

const getTypeText = (type) => {
  const textMap = {
    text: t('testcase.text'),
    step: t('testcase.step')
  }
  return textMap[type] || '-'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD')
}

const getVersionsTooltip = (versions) => {
  return versions.map(v => v.name + (v.is_baseline ? ' (' + t('testcase.baseline') + ')' : '')).join('、')
}

// 将HTML的<br>标签转换为换行符（用于Excel导出）
const convertBrToNewline = (text) => {
  if (!text) return ''
  return text.replace(/<br\s*\/?>/gi, '\n')
}

const exportToExcel = async () => {
  try {
    loading.value = true

    // 获取所有数据（不分页）
    const pageSize = 100
    let page = 1
    let hasMore = true
    let allData = []

    while (hasMore) {
      const response = await api.get('/testcases/', {
        params: {
          page: page,
          page_size: pageSize,
          search: searchText.value,
          module: moduleFilter.value,
          priority: priorityFilter.value
        }
      })

      const results = response.data.results || []
      allData.push(...results)

      if (results.length < pageSize) {
        hasMore = false
      } else {
        page++
      }
    }

    if (allData.length === 0) {
      ElMessage.warning(t('testcase.noDataToExport'))
      loading.value = false
      return
    }

    const workbook = XLSX.utils.book_new()

    // 表头：包含列表显示字段和导出额外字段
    const worksheetData = [
      ['用例编号', '归属目录', '模块', '用例名称', '前置条件', '测试步骤', '预期结果', '用例级别', '测试步骤模式', '创建者', '创建时间']
    ]

    allData.forEach((testcase, index) => {
      worksheetData.push([
        (currentPage.value - 1) * pageSize + index + 1,
        testcase.category_path || '',
        testcase.module || '',
        testcase.title || '',
        convertBrToNewline(testcase.preconditions || ''),
        convertBrToNewline(testcase.steps || ''),
        convertBrToNewline(testcase.expected_result || ''),
        getPriorityText(testcase.priority),
        getTypeText(testcase.test_type),
        testcase.author?.username || '',
        formatDate(testcase.created_at)
      ])
    })

    const worksheet = XLSX.utils.aoa_to_sheet(worksheetData)

    const colWidths = [
      { wch: 10 },  // 用例编号
      { wch: 25 },  // 归属目录
      { wch: 12 },  // 模块
      { wch: 40 },  // 用例名称
      { wch: 30 },  // 前置条件
      { wch: 40 },  // 测试步骤
      { wch: 30 },  // 预期结果
      { wch: 10 },  // 用例级别
      { wch: 12 },  // 测试步骤模式
      { wch: 10 },  // 创建者
      { wch: 12 }   // 创建时间
    ]
    worksheet['!cols'] = colWidths

    // 设置表头样式
    for (let col = 0; col < worksheetData[0].length; col++) {
      const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col })
      if (!worksheet[cellAddress]) continue
      worksheet[cellAddress].s = {
        font: { bold: true },
        alignment: { horizontal: 'center', vertical: 'center', wrapText: true }
      }
    }

    // 设置数据行样式
    for (let row = 1; row < worksheetData.length; row++) {
      for (let col = 0; col < worksheetData[row].length; col++) {
        const cellAddress = XLSX.utils.encode_cell({ r: row, c: col })
        if (worksheet[cellAddress]) {
          worksheet[cellAddress].s = {
            alignment: { vertical: 'top', wrapText: true }
          }
        }
      }
    }

    XLSX.utils.book_append_sheet(workbook, worksheet, t('testcase.excelSheetName'))

    const fileName = t('testcase.excelFileName', { date: new Date().toISOString().slice(0, 10) })

    XLSX.writeFile(workbook, fileName)

    ElMessage.success(t('testcase.exportSuccess'))
  } catch (error) {
    console.error('Export test cases failed:', error)
    ElMessage.error(t('testcase.exportFailed') + ': ' + (error.message || t('common.error')))
  } finally {
    loading.value = false
  }
}

// 统一监听路由参数变化，避免多个 watch 同时触发导致请求冲突
watch(() => route.query, (newQuery) => {
  const newProjectId = newQuery.project
  const newMenuId = newQuery.menu
  const newHighlightId = newQuery.highlight
  
  // 处理高亮参数
  if (newHighlightId) {
    highlightId.value = Array.isArray(newHighlightId) ? newHighlightId[0] : newHighlightId
  } else {
    highlightId.value = null
  }
  
  // 处理项目筛选
  if (newProjectId) {
    projectFilter.value = Array.isArray(newProjectId) ? newProjectId[0] : newProjectId
    // 清空其他筛选条件，避免叠加
    menuFilter.value = ''
    moduleFilter.value = ''
    priorityFilter.value = ''
    searchText.value = ''
  } else {
    projectFilter.value = ''
  }
  
  // 处理菜单筛选
  if (newMenuId) {
    menuFilter.value = Array.isArray(newMenuId) ? newMenuId[0] : newMenuId
    // 清空其他筛选条件，避免叠加
    projectFilter.value = ''
    moduleFilter.value = ''
    priorityFilter.value = ''
    searchText.value = ''
  } else {
    menuFilter.value = ''
  }
  
  currentPage.value = 1
  fetchTestCases().then(() => {
    // 数据加载完成后，如果有高亮参数，滚动到高亮行
    if (highlightId.value) {
      nextTick(() => {
        scrollToHighlightedRow()
      })
    }
  })
}, { immediate: true, deep: true })


// 获取行样式类名，用于高亮指定行
function getRowClassName({ row }) {
  if (highlightId.value && row.id && String(row.id) === String(highlightId.value)) {
    return 'highlighted-row'
  }
  return ''
}

// 滚动到高亮行
function scrollToHighlightedRow() {
  if (!tableRef.value || !highlightId.value) return
  
  const table = tableRef.value
  const rows = table.$el.querySelectorAll('.el-table__body-wrapper tr')
  
  for (const row of rows) {
    const rowData = row.__vnode?.props?.['data-row-key']
    if (rowData && String(rowData) === String(highlightId.value)) {
      row.scrollIntoView({ behavior: 'smooth', block: 'center' })
      break
    }
  }
}

onMounted(() => {
  fetchAllModules()
})

// 在页面切换回来时刷新表格布局，修复固定列显示异常问题
onActivated(() => {
  nextTick(() => {
    if (tableRef.value) {
      tableRef.value.doLayout()
    }
  })
})
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

  .header-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
}

// 筛选栏
.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;

  :deep(.el-input__wrapper),
  :deep(.el-select .el-input__wrapper) {
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
    border-radius: 8px;
    background: #ffffff;

    &:hover,
    &:focus {
      box-shadow: 0 0 0 1px #7b42f6;
    }
  }

  :deep(.el-input__inner) {
    color: #5a32a3;
    font-weight: 500;
  }

  .filter-bar-spacer {
    flex: 1;
  }
}

// 卡片容器
.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 20px;
}

// 历史记录样式
.history-card {
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

    // 高亮行样式
    :deep(.highlighted-row) {
      background-color: #ecf5ff !important;
      animation: highlight-pulse 2s ease-out;
      
      td {
        background-color: #ecf5ff !important;
        color: #409eff;
        font-weight: 500;
      }
    }

    @keyframes highlight-pulse {
      0% {
        background-color: #d9ecff;
      }
      50% {
        background-color: #b3d8ff;
      }
      100% {
        background-color: #ecf5ff;
      }
    }

    // 直接覆盖表头单元格样式
    :deep(.el-table__header th) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }

    // 覆盖表头单元格内容样式
    :deep(.el-table__header th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
    }

    // 模块单元格居中
    :deep(.module-cell) {
      text-align: center !important;

      .cell {
        text-align: center !important;
        justify-content: center !important;
      }

      .module-content {
        display: inline-block;
        text-align: center;
      }
    }

    // 复选框单元格垂直居中对齐
    :deep(.selection-cell) {
      .cell {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
      }

      .el-checkbox {
        margin: 0;
        height: auto;
      }
    }

    // 表头复选框垂直居中
    :deep(.el-table__header) {
      .selection-cell {
        .cell {
          display: flex;
          align-items: center;
          justify-content: center;
        }
      }
    }
  }

  // 状态徽章样式
  .status-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.3s ease;
    white-space: nowrap;
    min-width: 36px;

    // 低优先级 - 绿色
    &.low {
      background: #f6ffed;
      color: #52c41a;
    }

    // 中优先级 - 橙色
    &.medium {
      background: #fff7e6;
      color: #fa8c16;
    }

    // 高优先级 - 红色
    &.high {
      background: #fff1f0;
      color: #f5222d;
    }

    // 严重优先级 - 深红色
    &.critical {
      background: #fff1f0;
      color: #cf1322;
      font-weight: 600;
    }
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

  // 用例名称样式
  .case-name {
    font-weight: 500;
    color: #7b42f6;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      color: #6d33e6;
      text-decoration: underline;
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
      border: none !important;
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
      border: none !important;
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
      border: none !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
      }
    }

    // Element Plus 按钮类型样式 - 筛选栏按钮
    &.el-button--success {
      background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
      border: none !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
      }
    }

    &.el-button--warning {
      background: linear-gradient(135deg, #faad14 0%, #d48806 100%) !important;
      border: none !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #ffc53d 0%, #faad14 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(250, 173, 20, 0.4);
      }
    }

    &.el-button--danger {
      background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
      border: none !important;
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

// 分页容器
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

// 版本标签
.version-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;

  .version-tag {
    margin: 0;
  }
}

// 响应式布局
@media (max-width: 1200px) {
  .page-container {
    padding: 16px;
  }

  .page-header {
    padding: 20px;

    .page-title {
      font-size: 20px;
    }
  }

  .filter-bar {
    padding: 16px;
    flex-wrap: wrap;
  }

  .card-container {
    padding: 16px;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 12px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 16px;

    .page-title {
      font-size: 18px;
    }

    .header-actions {
      width: 100%;
    }
  }

  .page-container {
    .filter-bar {
      padding: 12px;

      :deep(.el-input),
      :deep(.el-select) {
        width: 100% !important;
      }
    }

    .card-container {
      padding: 12px;
    }

    .action-buttons {
      flex-direction: column;
      gap: 4px;
    }
  }
}

// 导入功能样式
.import-container {
  padding: 0;
  height: 520px;
  width: 100%;
  display: flex;
  flex-direction: column;

  .upload-section {
    margin-bottom: 0;
    flex: 1;
    width: 100%;
    min-height: 0;
    position: relative;

    :deep(.upload-demo) {
      width: 100%;
      height: 100%;
    }

    :deep(.el-upload) {
      width: 100%;
      height: 100% !important;
    }

    :deep(.el-upload-dragger) {
      width: 100%;
      height: 100% !important;
      min-height: 100% !important;
      border: 2px dashed #c4b5fd;
      border-radius: 16px;
      background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
      transition: all 0.3s ease;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;

      &:hover {
        border-color: #7b42f6;
        background: linear-gradient(135deg, #f0edff 0%, #e8e4ff 100%);
        box-shadow: 0 8px 32px rgba(123, 66, 246, 0.15);
      }

      .el-icon--upload {
        font-size: 80px;
        color: #7b42f6;
        margin-bottom: 24px;
        opacity: 0.8;
      }

      .el-upload__text {
        color: #5a32a3;
        font-size: 18px;
        font-weight: 500;

        em {
          color: #7b42f6;
          font-style: normal;
          font-weight: 600;
          text-decoration: underline;
          text-underline-offset: 4px;
        }
      }
    }

    .el-upload__tip {
      color: #999;
      font-size: 12px;
      margin-top: 8px;
    }
  }

  .mapping-section {
    margin-bottom: 24px;
    padding: 16px;
    background: #f8f7ff;
    border-radius: 8px;
    border: 1px solid #e9ecef;

    h4 {
      margin: 0 0 16px 0;
      font-size: 14px;
      color: #5a32a3;
      font-weight: 600;
    }

    .mapping-table {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .mapping-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        background: #ffffff;
        border-radius: 6px;
        border: 1px solid #e9ecef;

        &.header {
          background: #f0f0f0;
          font-weight: 600;
          color: #666;
        }

        .mapping-label {
          flex: 1;
          font-size: 13px;
          min-width: 0;

          &:first-child {
            max-width: calc(50% - 14px);
          }

          &:last-child {
            max-width: 200px;
          }
        }

        .excel-field {
          flex: 1;
          font-size: 13px;
          color: #333;
          font-weight: 500;
          max-width: calc(50% - 14px);
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .mapping-icon {
          color: #a78bfa;
          font-size: 16px;
          flex-shrink: 0;
        }

        .auto-generate-tip {
          width: 200px;
          font-size: 13px;
          color: #999;
          font-style: italic;
          flex-shrink: 0;
        }

        .el-select {
          flex-shrink: 0;
        }
      }
    }
  }

  .preview-section {
    margin-top: 0;
    padding-top: 0;
    height: 520px;

    :deep(.el-table) {
      border-radius: 8px;
      overflow: hidden;
    }

    :deep(.el-table__header-wrapper) {
      margin-top: 0;
    }
  }
}

// 步骤条样式
.import-steps {
  margin-bottom: 24px;
  padding: 20px 40px 30px;
  background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
  border-radius: 12px;

  // 步骤项改为垂直布局（圆球在上，文字在下）
  :deep(.el-step) {
    display: flex;
    flex-direction: column-reverse;
    align-items: center;

    .el-step__head {
      margin-top: 8px;
    }

    .el-step__main {
      text-align: center;
    }
  }

  :deep(.el-step__title) {
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
  }

  // 当前步骤 - 紫色主题
  :deep(.el-step.is-active) {
    .el-step__icon {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      border-color: #7b42f6;
      color: #fff;
      width: 36px;
      height: 36px;
      font-size: 16px;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
    }

    .el-step__title {
      color: #7b42f6;
      font-weight: 600;
    }

    .el-step__line {
      background-color: #7b42f6;
    }
  }

  // 已完成步骤 - 绿色
  :deep(.el-step.is-success) {
    .el-step__icon {
      background: #52c41a;
      border-color: #52c41a;
      color: #fff;
      width: 36px;
      height: 36px;
      font-size: 16px;
    }

    .el-step__title {
      color: #52c41a;
      font-weight: 500;
    }

    .el-step__line {
      background-color: #52c41a;
    }
  }

  // 等待步骤 - 灰色
  :deep(.el-step.is-wait) {
    .el-step__icon {
      background: #fff;
      border-color: #d9d9d9;
      color: #999;
      width: 36px;
      height: 36px;
      font-size: 16px;
    }

    .el-step__title {
      color: #999;
    }
  }

  // 连接线样式 - 调整位置适应垂直布局
  :deep(.el-step__line) {
    height: 2px;
    top: auto;
    bottom: 18px;
    left: 50% !important;
    right: -50% !important;
    width: 100%;
  }
}

// 导入结果样式
.import-result {
  padding: 0;
  height: 520px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  // 导入成功时的特殊样式
  &.import-success {
    .success-icon-wrapper {
      margin-bottom: 24px;

      .success-icon {
        font-size: 100px;
        color: #52c41a;
        animation: scaleIn 0.5s ease;
      }
    }

    .result-title {
      font-size: 36px;
      font-weight: 700;
      color: #333;
      margin-bottom: 24px;
      text-align: center;
    }

    .result-message {
      font-size: 18px;
      color: #52c41a;
      font-weight: 500;
      margin-bottom: 0;
      padding: 16px 40px;
      background: #f6ffed;
      border-radius: 12px;
      border: 2px solid #52c41a;
      text-align: center;
    }
  }

  // 导入失败/部分成功的样式
  &:not(.import-success) {
    padding: 40px 0 20px;
    justify-content: flex-start;

    .result-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;

      .warning-icon {
        font-size: 18px;
        color: #faad14;
      }

      .success-icon {
        font-size: 18px;
        color: #52c41a;
      }

      .result-title {
        font-size: 18px;
        font-weight: 600;
        color: #333;
      }
    }

    .result-message {
      font-size: 13px;
      color: #666;
      margin-bottom: 20px;
    }
  }

  @keyframes scaleIn {
    0% {
      transform: scale(0);
      opacity: 0;
    }
    50% {
      transform: scale(1.2);
    }
    100% {
      transform: scale(1);
      opacity: 1;
    }
  }

  .error-list {
    width: 100%;
    text-align: left;
    flex: 1;
    min-height: 0;
    max-height: 420px;
    padding: 16px 20px;
    background: #fff1f0;
    border-radius: 8px;
    border: 1px solid #ffccc7;
    overflow-y: auto;

    h5 {
      margin: 0 0 12px 0;
      font-size: 13px;
      color: #cf1322;
      font-weight: 600;
    }

    .error-item {
      padding: 6px 0;
      font-size: 12px;
      color: #f5222d;
      border-bottom: 1px dashed #ffccc7;
      line-height: 1.5;

      .error-index {
        display: inline-block;
        width: 24px;
        color: #999;
        font-weight: 500;
      }

      &:last-child {
        border-bottom: none;
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 导入弹窗样式 - 移除 body 内边距
:deep(.el-dialog.import-dialog .el-dialog__body) {
  padding: 0;
}
</style>
