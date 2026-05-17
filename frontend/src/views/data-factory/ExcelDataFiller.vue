<template>
  <div class="excel-data-filler">
    <el-card class="main-card">
      <!-- 头部区域 -->
      <div class="page-header">
        <!-- 模式切换标签 -->
        <div class="mode-tabs">
          <div
            v-for="mode in modeList"
            :key="mode.key"
            class="mode-tab"
            :class="{ active: currentMode === mode.key }"
            @click="switchMode(mode.key)"
          >
            <el-icon class="mode-icon"><component :is="mode.icon" /></el-icon>
            <span class="mode-label">{{ mode.label }}</span>
          </div>
        </div>
        <div class="header-spacer"></div>
      </div>

      <!-- 智能填充模式：步骤卡片 -->
      <div v-if="currentMode === 'smart'" class="step-cards">
        <div
          v-for="(step, index) in stepList"
          :key="index"
          class="step-card"
          :class="{
            'is-active': currentStep === index,
            'is-completed': currentStep > index || (isFlowCompleted && index === 2),
            'is-pending': currentStep < index && !(isFlowCompleted && index === 2),
            'is-next-available': (currentStep === 0 && index === 1 && currentFile && fieldList.length > 0) ||
                                 (currentStep === 1 && index === 2 && fieldList.length > 0)
          }"
          @click="goToStep(index)"
        >
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-info">
            <div class="step-title">{{ step.title }}</div>
            <div class="step-desc">{{ step.desc }}</div>
          </div>
          <el-icon v-if="currentStep > index || (isFlowCompleted && index === 2)" class="step-check"><Check /></el-icon>
        </div>
      </div>

      <!-- 步骤1: 上传模板 -->
      <div v-if="currentStep === 0" class="step-content">
        <div class="upload-container">
          <el-upload
            class="upload-area"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            accept=".xlsx,.xls"
          >
            <el-icon class="upload-icon"><Upload /></el-icon>
            <div class="upload-text">
              <p>拖拽文件到此处，或 <em>点击上传</em></p>
              <p class="upload-tip">支持 .xlsx/.xls 格式的Excel文件</p>
            </div>
          </el-upload>
        </div>
      </div>

      <!-- 步骤2: 字段分析 (仅在智能填充模式下显示) -->
      <div v-if="currentStep === 1 && currentMode === 'smart'" class="step-content">
        <div class="analysis-container">
          <div class="analysis-result">
            <!-- 多Sheet切换 -->
            <div v-if="totalSheets > 1" class="sheet-tabs">
              <div class="sheet-tab-list">
                <div
                  v-for="(sheet, index) in sheetsInfo"
                  :key="index"
                  class="sheet-tab-item"
                  :class="{ active: currentSheetIndex === index }"
                  @click="handleSheetChange(index)"
                >
                  <span class="sheet-tab-name">{{ sheet.name }}</span>
                  <span class="sheet-tab-badge">{{ sheet.total_fields }}个字段</span>
                </div>
              </div>
            </div>

            <el-table :data="fieldList" border style="width: 100%">
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="name" label="字段名称" min-width="180">
              <template #default="scope">
                {{ scope.row.name.replace(/[\*\(必填\)]/g, '') }}
              </template>
            </el-table-column>
            <el-table-column label="是否必填" width="90" align="center" show-overflow-tooltip>
              <template #default="scope">
                <span :class="['badge', isRequired(scope.row.name) ? 'required' : 'optional']">
                  {{ isRequired(scope.row.name) ? '必填' : '非必填' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="识别类型" width="120">
              <template #default="scope">
                <span :class="['badge', getTypeTagType(scope.row.type) || 'default']">
                  {{ getTypeDisplayName(scope.row.type) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="固定值" min-width="200">
              <template #default="scope">
                <el-input
                  v-model="scope.row.customValue"
                  placeholder="非业务字段AI生成，业务字段手动输入"
                  size="small"
                  clearable
                >
                </el-input>
              </template>
            </el-table-column>
            <el-table-column label="示例数据" min-width="180">
              <template #default="scope">
                <span class="example-data">
                  {{ scope.row.customValue || getExampleData(scope.row.type) }}
                </span>
              </template>
            </el-table-column>
            </el-table>

          </div>
        </div>
      </div>

      <!-- 步骤3: 生成数据 (仅在智能填充模式下显示) -->
      <div v-if="currentStep === 2 && currentMode === 'smart'" class="step-content">
        <div class="generate-container">
          <div class="generate-section">
            <div class="generate-config">
              <div class="config-row">
                <div class="config-item">
                  <span class="config-label">生成行数</span>
                  <el-input-number
                    v-model="generateConfig.rowCount"
                    :min="1"
                    :max="2000"
                    :step="10"
                    size="small"
                  />
                </div>
                <div class="config-item">
                  <span class="config-label">预览行数</span>
                  <el-input-number
                    v-model="generateConfig.previewCount"
                    :min="1"
                    :max="20"
                    :step="5"
                    size="small"
                  />
                </div>
                <div class="config-actions">
                  <el-button type="primary" class="preview-btn" @click="previewData" :loading="previewLoading">
                    <el-icon><View /></el-icon>
                    预览数据
                  </el-button>
                  <el-button type="success" @click="downloadData" :loading="downloadLoading">
                    <el-icon><Download /></el-icon>
                    下载Excel
                  </el-button>
                </div>
              </div>
            </div>

            <!-- 数据预览 -->
            <div v-if="previewDataList.length > 0" class="data-preview">
              <div class="preview-header">
                <div class="preview-title-section">
                  <!-- 多Sheet预览切换 -->
                  <div v-if="previewSheetsData.length > 1" class="preview-sheet-tabs">
                    <div class="sheet-tab-list">
                      <div
                        v-for="(sheet, index) in previewSheetsData"
                        :key="index"
                        class="sheet-tab-item"
                        :class="{ active: currentPreviewSheetIndex === index }"
                        @click="handlePreviewSheetChange(index)"
                      >
                        <span class="sheet-tab-name">{{ sheet.sheet_name }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <el-table
                ref="previewTableRef"
                :data="previewDataList"
                border
                style="width: 100%"
                max-height="400"
                :scroll-x="true"
              >
                <el-table-column
                  v-for="field in currentPreviewFields"
                  :key="field.name"
                  :prop="field.name"
                  :label="field.name"
                  width="auto"
                  min-width="120"
                  show-overflow-tooltip
                />
              </el-table>
            </div>
          </div>
        </div>
      </div>

      <!-- 模块课程生成模式 -->
      <div v-if="currentMode === 'module'" class="module-course-section">
        <!-- 生成配置卡片 -->
        <div class="module-config-card">
          <div class="config-header">
            <h3 class="section-title">
              <el-icon><Setting /></el-icon>
              生成配置
            </h3>
            <div class="data-count-badge" :class="{ 'warning': moduleConfig.primaryCount * moduleConfig.secondaryCount > 2000 }">
              {{ moduleConfig.primaryCount }} × {{ moduleConfig.secondaryCount }} = {{ moduleConfig.primaryCount * moduleConfig.secondaryCount }} 条
            </div>
          </div>

          <div class="config-form">
            <!-- 第一行：前缀配置 -->
            <div class="config-row">
              <div class="config-item">
                <label class="config-label">
                  <span class="label-text">一级模块前缀</span>
                  <el-tooltip content="一级模块名称前缀，自动追加序号（如：基础001）" placement="top">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </label>
                <el-input v-model="moduleConfig.primaryPrefix" placeholder="如：基础课程" maxlength="50" show-word-limit size="default" />
              </div>
              <div class="config-item">
                <label class="config-label">
                  <span class="label-text">二级模块前缀</span>
                  <el-tooltip content="二级模块名称前缀，自动追加全局序号（如：第001）" placement="top">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </label>
                <el-input v-model="moduleConfig.secondaryPrefix" placeholder="如：第" maxlength="50" show-word-limit size="default" />
              </div>
            </div>

            <!-- 第二行：数量与长度配置 -->
            <div class="config-row four-cols">
              <div class="config-item">
                <label class="config-label">一级模块数</label>
                <el-input-number v-model="moduleConfig.primaryCount" :min="1" :max="100" :step="5" size="default" />
              </div>
              <div class="config-item">
                <label class="config-label">二级模块/一级</label>
                <el-input-number v-model="moduleConfig.secondaryCount" :min="1" :max="50" :step="5" size="default" />
              </div>
              <div class="config-item">
                <label class="config-label">一级最大长度</label>
                <el-input-number v-model="moduleConfig.primaryMaxLength" :min="5" :max="50" :step="5" size="default" />
              </div>
              <div class="config-item">
                <label class="config-label">二级最大长度</label>
                <el-input-number v-model="moduleConfig.secondaryMaxLength" :min="5" :max="50" :step="5" size="default" />
              </div>
            </div>

            <!-- 点播课ID录入 -->
            <div class="course-ids-section">
              <div class="section-header">
                <h4 class="section-subtitle">
                  <el-icon><Document /></el-icon>
                  点播课ID录入
                </h4>
                <el-switch v-model="moduleConfig.enableCourseIds" />
              </div>
              <div v-if="moduleConfig.enableCourseIds" class="course-ids-input">
                <el-input v-model="moduleConfig.courseIdsText" type="textarea" :rows="5" :placeholder="`请输入 ${moduleConfig.primaryCount * moduleConfig.secondaryCount} 个点播课ID，每行一个`" resize="vertical" />
                <div class="course-ids-stats">
                  <span :class="{ 'text-warning': courseIdsCount > moduleConfig.primaryCount * moduleConfig.secondaryCount }">
                    已录入 {{ courseIdsCount }} / {{ moduleConfig.primaryCount * moduleConfig.secondaryCount }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="config-actions">
              <el-button type="primary" size="large" :loading="modulePreviewLoading" @click="previewModuleData">
                <el-icon><View /></el-icon>预览数据
              </el-button>
              <el-button type="success" size="large" :loading="moduleDownloadLoading" :disabled="moduleConfig.primaryCount * moduleConfig.secondaryCount > 2000" @click="downloadModuleData">
                <el-icon><Download /></el-icon>下载Excel
              </el-button>
            </div>
          </div>
        </div>

        <!-- 数据预览 -->
        <div v-if="modulePreviewData.length > 0" class="module-preview-card">
          <h3 class="section-title">
            <el-icon><View /></el-icon>
            数据预览（前 {{ modulePreviewData.length }} 条）
          </h3>
          <el-table :data="modulePreviewData" border style="width: 100%" size="small">
            <el-table-column type="index" label="序号" width="50" align="center" />
            <el-table-column prop="primary_module" label="一级模块" min-width="150" show-overflow-tooltip />
            <el-table-column prop="secondary_module" label="二级模块" min-width="150" show-overflow-tooltip />
            <el-table-column prop="course_id" label="点播课ID" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span :class="{ 'empty-cell': !row.course_id }">{{ row.course_id || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

      </div>
    </el-card>

    <!-- 使用说明对话框 -->
    <el-dialog
      v-model="showHelp"
      title="使用说明"
      width="700px"
    >
      <div class="help-content">
        <h4>功能介绍</h4>
        <p>数据智能填充可以自动识别Excel模板中的字段类型，并生成对应的测试数据。</p>

        <h4>支持的字段类型</h4>
        <el-table :data="supportedTypes" border size="small">
          <el-table-column prop="type" label="字段类型" width="120" />
          <el-table-column prop="keywords" label="识别关键词" />
          <el-table-column prop="example" label="示例数据" min-width="180" />
        </el-table>

        <h4>使用步骤</h4>
        <ol>
          <li>上传模板：上传包含字段名称的Excel模板文件</li>
          <li>字段分析：系统自动识别字段类型，确认识别结果</li>
          <li>生成数据：设置生成行数，预览并下载数据</li>
        </ol>

      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document,
  Upload,
  InfoFilled,
  QuestionFilled,
  View,
  Download,
  Check,
  FolderOpened,
  Setting,
  Operation
} from '@element-plus/icons-vue'
import {
  analyzeExcelTemplate,
  previewFilledData,
  fillExcelData,
  generateModuleCourseData
} from '@/api/data-factory'

// 模式列表
const modeList = [
  { key: 'smart', label: '业务导入动态字段', icon: 'Operation' },
  { key: 'module', label: '业务引用点播课', icon: 'FolderOpened' }
]
const currentMode = ref('smart')

// 切换模式
const switchMode = (mode) => {
  currentMode.value = mode
  // 重置状态
  reset()
  resetModuleConfig()
}

const currentStep = ref(0)
const showHelp = ref(false)
const currentFile = ref(null)
const fieldList = ref([])
const previewDataList = ref([])
const previewLoading = ref(false)
const downloadLoading = ref(false)
const isFlowCompleted = ref(false)
// 多Sheet预览支持
const previewSheetsData = ref([])
const currentPreviewSheetIndex = ref(0)
const currentPreviewFields = ref([])
const previewTableRef = ref(null)

// 同步表格表头和内容的滚动
const syncTableScroll = () => {
  nextTick(() => {
    if (!previewTableRef.value) return
    
    const tableEl = previewTableRef.value.$el
    const headerWrapper = tableEl.querySelector('.el-table__header-wrapper')
    const bodyWrapper = tableEl.querySelector('.el-table__body-wrapper')
    
    if (headerWrapper && bodyWrapper) {
      // 监听内容区域滚动，同步到表头
      bodyWrapper.addEventListener('scroll', () => {
        headerWrapper.scrollLeft = bodyWrapper.scrollLeft
      })
      
      // 监听表头滚动，同步到内容区域
      headerWrapper.addEventListener('scroll', () => {
        bodyWrapper.scrollLeft = headerWrapper.scrollLeft
      })
    }
  })
}

// 多Sheet支持
const sheetsInfo = ref([])
const currentSheetIndex = ref(0)
const totalSheets = ref(1)
// 保存所有Sheet的自定义字段值 { sheetName: { fieldName: value } }
const allSheetsCustomFields = ref({})

// 步骤列表
const stepList = [
  { title: '上传模板', desc: '上传Excel模板文件' },
  { title: '字段分析', desc: '自动识别字段类型' },
  { title: '生成数据', desc: '预览并下载数据' }
]

// 跳转到指定步骤
const goToStep = (index) => {
  // 判断是否可以跳转到目标步骤
  // 规则：
  // 1. 可以跳转到已完成的步骤（index <= currentStep）
  // 2. 可以跳转到下一步，如果当前步骤数据已准备好
  
  const canGoNext = () => {
    // 步骤0 -> 步骤1：需要已上传文件并解析完成
    if (currentStep.value === 0) {
      return currentFile.value !== null && fieldList.value.length > 0
    }
    // 步骤1 -> 步骤2：字段列表已加载
    if (currentStep.value === 1) {
      return fieldList.value.length > 0
    }
    return false
  }
  
  // 可以跳转到已完成的步骤
  if (index <= currentStep.value) {
    currentStep.value = index
    return
  }
  
  // 可以跳转到下一步（如果数据已准备好）
  if (index === currentStep.value + 1 && canGoNext()) {
    currentStep.value = index
  }
}

const generateConfig = reactive({
  rowCount: 10,
  previewCount: 5
})

// ========== 模块课程数据生成 ==========

// 模块课程配置
const moduleConfig = reactive({
  primaryCount: 50,
  secondaryCount: 30,
  primaryMaxLength: 20,
  secondaryMaxLength: 20,
  dataStartRow: 3,
  primaryPrefix: '一级模块',
  secondaryPrefix: '二级模块',
  enableCourseIds: true,
  courseIdsText: ''
})

// 计算录入的点播课ID数量
const courseIdsCount = computed(() => {
  if (!moduleConfig.courseIdsText) return 0
  return moduleConfig.courseIdsText
    .split('\n')
    .map(id => id.trim())
    .filter(id => id.length > 0)
    .length
})

// 获取点播课ID列表
const getCourseIdsList = () => {
  if (!moduleConfig.enableCourseIds || !moduleConfig.courseIdsText) return []
  return moduleConfig.courseIdsText
    .split('\n')
    .map(id => id.trim())
    .filter(id => id.length > 0)
}

  // 模块课程预览数据
  const modulePreviewData = ref([])
const modulePreviewLoading = ref(false)
const moduleDownloadLoading = ref(false)

// 重置模块课程配置
const resetModuleConfig = () => {
  moduleConfig.primaryCount = 50
  moduleConfig.secondaryCount = 30
  moduleConfig.primaryMaxLength = 20
  moduleConfig.secondaryMaxLength = 20
  moduleConfig.dataStartRow = 3
  moduleConfig.primaryPrefix = '一级模块'
  moduleConfig.secondaryPrefix = '二级模块'
  modulePreviewData.value = []
}

// 预览模块课程数据
const previewModuleData = async () => {
  modulePreviewLoading.value = true
  try {
    const response = await generateModuleCourseData({
      primary_count: moduleConfig.primaryCount,
      secondary_count: moduleConfig.secondaryCount,
      primary_max_length: moduleConfig.primaryMaxLength,
      secondary_max_length: moduleConfig.secondaryMaxLength,
      data_start_row: moduleConfig.dataStartRow,
      primary_prefix: moduleConfig.primaryPrefix,
      secondary_prefix: moduleConfig.secondaryPrefix,
      course_ids: getCourseIdsList(),
      action: 'preview'
    })

    const data = response.data || response
    if (data.success) {
      modulePreviewData.value = data.preview_data || []
      ElMessage.success(`预览数据生成成功，共 ${data.total_rows} 条数据`)
    } else {
      ElMessage.error(data.error || '预览失败')
    }
  } catch (error) {
    console.error('预览错误:', error)
    ElMessage.error('预览失败：' + (error.message || '未知错误'))
  } finally {
    modulePreviewLoading.value = false
  }
}

// 下载模块课程数据
const downloadModuleData = async () => {
  moduleDownloadLoading.value = true
  try {
    const response = await generateModuleCourseData({
      primary_count: moduleConfig.primaryCount,
      secondary_count: moduleConfig.secondaryCount,
      primary_max_length: moduleConfig.primaryMaxLength,
      secondary_max_length: moduleConfig.secondaryMaxLength,
      data_start_row: moduleConfig.dataStartRow,
      primary_prefix: moduleConfig.primaryPrefix,
      secondary_prefix: moduleConfig.secondaryPrefix,
      course_ids: getCourseIdsList(),
      action: 'download'
    })

    // 从响应头中获取文件名
    let filename = `按模块导入点播课_${moduleConfig.primaryCount}一级_${moduleConfig.secondaryCount}二级_${new Date().getTime()}.xlsx`
    const contentDisposition = response.headers?.['content-disposition']
    if (contentDisposition) {
      const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''(.+)/)
      if (filenameStarMatch) {
        filename = decodeURIComponent(filenameStarMatch[1])
      }
    }

    // 从 response.data 获取 blob 数据
    const blobData = response.data || response
    const blob = new Blob([blobData], { type: 'application/vnd.ms-excel' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('文件下载成功')
  } catch (error) {
    console.error('下载错误:', error)
    ElMessage.error('下载失败：' + (error.message || '未知错误'))
  } finally {
    moduleDownloadLoading.value = false
  }
}

const supportedTypes = [
  { type: '姓名', keywords: '姓名、名字、name', example: '张伟' },
  { type: '手机号', keywords: '手机、电话、phone', example: '13800138000' },
  { type: '邮箱', keywords: '邮箱、email、邮件', example: 'test@qq.com' },
  { type: '身份证', keywords: '身份证、证件号', example: '110101199001011234' },
  { type: '地址', keywords: '地址、住址', example: '北京市朝阳区...' },
  { type: '省市区县', keywords: '省、市、区、县、省市、市区、区县', example: '北京市/朝阳区' },
  { type: '公司', keywords: '公司、单位、企业', example: '北京科技有限公司' },
  { type: '日期', keywords: '日期、时间、date', example: '2023-05-20' },
  { type: '数值', keywords: '数值、数量、年龄', example: '25' },
  { type: 'UUID', keywords: 'ID、编号、uuid', example: '8c4ee116-241b-49f9-a998' }
]

const typeDisplayMap = {
  'chinese_name': '姓名',
  'chinese_phone': '手机号',
  'email': '邮箱',
  'id_card': '身份证',
  'chinese_address': '地址',
  'province_city_district': '省市区县',
  'company_name': '公司',
  'bank_card': '银行卡',
  'random_int': '数值',
  'date': '日期',
  'select': '选项',
  'random_text': '文本',
  'uuid': 'UUID',
  'education_level': '学历',
  'school_name': '学校',
  'subject': '学科',
  'ethnicity': '民族',
  'gender': '性别'
}

const typeTagMap = {
  'chinese_name': 'name',
  'chinese_phone': 'phone',
  'email': 'email',
  'id_card': 'idcard',
  'chinese_address': 'address',
  'province_city_district': 'location',
  'company_name': 'company',
  'bank_card': 'bank',
  'random_int': 'number',
  'date': 'date',
  'select': 'select',
  'random_text': 'text',
  'uuid': 'uuid',
  'education_level': 'education',
  'school_name': 'school',
  'subject': 'subject',
  'ethnicity': 'ethnicity',
  'gender': 'gender'
}

const exampleDataMap = {
  'chinese_name': '张伟',
  'chinese_phone': '13800138000',
  'email': 'test@qq.com',
  'id_card': '110101199001011234',
  'chinese_address': '北京市朝阳区建设大街1号',
  'province_city_district': '北京市/朝阳区',
  'company_name': '北京科技有限公司',
  'bank_card': '6222021234567890123',
  'random_int': '25',
  'date': '2023-05-20',
  'select': '选项A',
  'random_text': '测试文本abc123',
  'uuid': '8c4ee116-241b-49f9-a998-297a1d200fdc',
  'education_level': '本科',
  'school_name': '北京大学',
  'subject': '数学',
  'ethnicity': '汉族',
  'gender': '男'
}

const handleFileChange = async (file) => {
  if (!file) return
  
  const isExcel = file.raw.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                  file.raw.type === 'application/vnd.ms-excel'
  
  if (!isExcel) {
    ElMessage.error('请上传Excel文件')
    return
  }
  
  currentFile.value = file.raw
  
  try {
    const response = await analyzeExcelTemplate(file.raw)
    // 从 response.data 中获取数据
    const data = response.data || response
    if (data.success) {
      // 保存多Sheet信息
      if (data.sheets && data.sheets.length > 0) {
        sheetsInfo.value = data.sheets
        totalSheets.value = data.total_sheets || data.sheets.length
        currentSheetIndex.value = 0
        fieldList.value = data.sheets[0].fields || []
      } else {
        // 兼容旧格式
        fieldList.value = data.fields || []
        sheetsInfo.value = []
        totalSheets.value = 1
      }
      currentStep.value = 1
      ElMessage.success('模板分析成功')
    } else {
      ElMessage.error(data.error || '分析失败')
    }
  } catch (error) {
    console.error('分析错误:', error)
    ElMessage.error('分析失败：' + (error.message || '未知错误'))
  }
}

// 切换Sheet
const handleSheetChange = (index) => {
  currentSheetIndex.value = index
  if (sheetsInfo.value[index]) {
    fieldList.value = sheetsInfo.value[index].fields || []
  }
}

const isRequired = (fieldName) => {
  return fieldName.includes('*') || fieldName.includes('必填')
}

const getTypeDisplayName = (type) => {
  return typeDisplayMap[type] || type
}

const getTypeTagType = (type) => {
  return typeTagMap[type] || ''
}

const getExampleData = (type) => {
  return exampleDataMap[type] || '测试数据'
}

const goToGenerate = () => {
  currentStep.value = 2
}

// 获取自定义字段值
const getCustomFields = () => {
  const customFields = {}
  // 收集所有Sheet的自定义字段
  sheetsInfo.value.forEach(sheet => {
    sheet.fields.forEach(field => {
      if (field.customValue && field.customValue.trim()) {
        customFields[field.name] = field.customValue.trim()
      }
    })
  })
  return customFields
}

const previewData = async () => {
  if (!currentFile.value) {
    ElMessage.error('请先上传文件')
    return
  }

  previewLoading.value = true
  try {
    const customFields = getCustomFields()
    const response = await previewFilledData(currentFile.value, generateConfig.previewCount, customFields)
    // 从 response.data 中获取数据
    const data = response.data || response
    if (data.success) {
      // 保存多Sheet预览数据
      if (data.sheets_preview && data.sheets_preview.length > 0) {
        previewSheetsData.value = data.sheets_preview
        currentPreviewSheetIndex.value = 0
        // 显示第一个Sheet的预览数据
        const firstSheet = data.sheets_preview[0]
        previewDataList.value = firstSheet.preview_data || []
        currentPreviewFields.value = firstSheet.fields || []
      } else {
        // 兼容旧格式
        previewDataList.value = data.preview_data || []
        currentPreviewFields.value = data.fields || []
        previewSheetsData.value = []
      }
      // 同步表格滚动
      syncTableScroll()
      ElMessage.success('预览数据生成成功')
    } else {
      ElMessage.error(data.error || '预览失败')
    }
  } catch (error) {
    console.error('预览错误:', error)
    ElMessage.error('预览失败：' + (error.message || '未知错误'))
  } finally {
    previewLoading.value = false
  }
}

// 监听预览Sheet切换
const handlePreviewSheetChange = (index) => {
  currentPreviewSheetIndex.value = index
  if (previewSheetsData.value[index]) {
    const sheet = previewSheetsData.value[index]
    previewDataList.value = sheet.preview_data || []
    currentPreviewFields.value = sheet.fields || []
    // 切换Sheet后重新同步滚动
    syncTableScroll()
  }
}

const downloadData = async () => {
  if (!currentFile.value) {
    ElMessage.error('请先上传文件')
    return
  }

  downloadLoading.value = true
  try {
    const customFields = getCustomFields()
    const response = await fillExcelData(currentFile.value, generateConfig.rowCount, customFields)

    // 从响应头中获取文件名
    let filename = `filled_data_${new Date().getTime()}.xlsx`
    const contentDisposition = response.headers?.['content-disposition']
    if (contentDisposition) {
      // 尝试解析 filename*=UTF-8'' 格式
      const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''(.+)/)
      if (filenameStarMatch) {
        filename = decodeURIComponent(filenameStarMatch[1])
      } else {
        // 尝试解析 filename="..." 格式
        const filenameMatch = contentDisposition.match(/filename="(.+)"/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
    }

    // 从 response.data 获取 blob 数据
    const blobData = response.data || response
    // 创建下载链接
    const blob = new Blob([blobData], { type: 'application/vnd.ms-excel' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('文件下载成功')
    isFlowCompleted.value = true
  } catch (error) {
    console.error('下载错误:', error)
    ElMessage.error('下载失败：' + (error.message || '未知错误'))
  } finally {
    downloadLoading.value = false
  }
}

const reset = () => {
  currentStep.value = 0
  currentFile.value = null
  fieldList.value = []
  previewDataList.value = []
  generateConfig.rowCount = 10
  generateConfig.previewCount = 5
  isFlowCompleted.value = false
}
</script>

<style lang="scss" scoped>
.excel-data-filler {
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

  :deep(.el-card__header) {
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);
    padding: 16px 20px;
  }

  :deep(.el-card__body) {
    padding: 24px;
    flex: 1;
    display: flex;
    flex-direction: column;
  }
}

// 页面头部样式
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  margin-bottom: 20px;

  .header-spacer {
    flex: 1;
  }

  .help-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    border: none;
    font-weight: 600;
    padding: 10px 20px;
    transition: all 0.25s ease;

    .el-icon {
      margin-right: 4px;
    }

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }

  .title-section {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .header-icon {
    font-size: 24px;
    color: #7b42f6;
  }

  .title {
    font-size: 18px;
    font-weight: 600;
    color: #5a32a3;
  }
}

// 步骤卡片样式
.step-cards {
  display: flex;
  gap: 16px;
  margin: 32px 0;
  padding: 0 20px;
}

.step-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border: 2px solid rgba(147, 112, 219, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;

  &:hover {
    border-color: rgba(147, 112, 219, 0.3);
    box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  }

  // 当前步骤 - 紫色高亮
  &.is-active {
    background: linear-gradient(135deg, #7b42f6 0%, #9f7aea 100%);
    border-color: #7b42f6;
    box-shadow: 0 4px 20px rgba(123, 66, 246, 0.3);

    .step-number {
      background: rgba(255, 255, 255, 0.2);
      color: #fff;
      border-color: rgba(255, 255, 255, 0.4);
    }

    .step-title {
      color: #fff;
      font-weight: 600;
    }

    .step-desc {
      color: rgba(255, 255, 255, 0.85);
    }
  }

  // 已完成步骤 - 绿色
  &.is-completed {
    background: linear-gradient(135deg, #f6ffed 0%, #e6f7d6 100%);
    border-color: #52c41a;

    .step-number {
      background: #52c41a;
      color: #fff;
      border-color: #52c41a;
    }

    .step-title {
      color: #52c41a;
      font-weight: 600;
    }

    .step-desc {
      color: #73d13d;
    }

    &:hover {
      box-shadow: 0 4px 16px rgba(82, 196, 26, 0.15);
    }
  }

  // 待处理步骤 - 灰色
  &.is-pending {
    cursor: not-allowed;
    opacity: 0.7;

    .step-number {
      background: #f5f7fa;
      color: #c0c4cc;
      border-color: #e4e7ed;
    }

    .step-title {
      color: #606266;
    }

    .step-desc {
      color: #909399;
    }
  }

  // 下一步可用状态 - 可点击
  &.is-next-available {
    cursor: pointer;
    opacity: 1;
    border-color: rgba(123, 66, 246, 0.4);
    background: linear-gradient(135deg, #ffffff 0%, #f0ecff 100%);

    .step-number {
      background: rgba(123, 66, 246, 0.1);
      color: #7b42f6;
      border-color: rgba(123, 66, 246, 0.3);
    }

    .step-title {
      color: #7b42f6;
    }

    .step-desc {
      color: #9f7aea;
    }

    &:hover {
      border-color: #7b42f6;
      box-shadow: 0 4px 16px rgba(123, 66, 246, 0.2);
      transform: translateY(-2px);
    }
  }
}

.step-number {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  border-radius: 50%;
  border: 2px solid;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.step-info {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 4px;
  transition: all 0.3s ease;
}

.step-desc {
  font-size: 12px;
  line-height: 1.4;
  transition: all 0.3s ease;
}

.step-check {
  font-size: 20px;
  color: #52c41a;
  flex-shrink: 0;
}

.step-content {
  margin-top: 30px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.upload-area {
  width: 100%;

  :deep(.el-upload-dragger) {
    background: linear-gradient(135deg, #faf8ff 0%, #f5f3ff 100%);
    border: 2px dashed rgba(147, 112, 219, 0.3);
    border-radius: 12px;
    transition: all 0.3s ease;

    &:hover {
      border-color: #7b42f6;
      background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
    }
  }
}

.upload-icon {
  font-size: 48px;
  color: #7b42f6;
  margin-bottom: 10px;
}

.upload-text {
  text-align: center;

  p {
    color: #666;
    font-size: 14px;
  }
}

.upload-text em {
  color: #7b42f6;
  font-style: normal;
  font-weight: 500;
}

.upload-tip {
  font-size: 12px;
  color: #999;
  margin-top: 10px;
}

.upload-container,
.analysis-container,
.generate-container,
.template-container {
  padding: 0 20px;
}

.template-tips {
  margin-top: 30px;
  padding: 20px;
  background: linear-gradient(135deg, #faf8ff 0%, #f5f3ff 100%);
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.15);

  h4 {
    margin: 0 0 12px 0;
    color: #5a32a3;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;

    .el-icon {
      color: #7b42f6;
    }
  }

  ul {
    margin: 0;
    padding-left: 20px;
    color: #666;
  }

  li {
    margin: 8px 0;
    line-height: 1.6;
  }
}

.analysis-result {
  h3 {
    margin-bottom: 10px;
    color: #5a32a3;
    font-weight: 600;
  }
  
  flex: 1;
  display: flex;
  flex-direction: column;
}

.analysis-summary {
  color: #666;
  margin-bottom: 20px;
  font-size: 14px;

  strong {
    color: #7b42f6;
  }

  .sheet-info {
    margin-left: 8px;
    color: #999;
    font-size: 13px;
  }
}

.sheet-tabs {
  margin-bottom: 20px;

  .sheet-tab-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .sheet-tab-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: #f5f5f5;
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.2s ease;
    border: 1px solid transparent;

    &:hover {
      background: #ebebeb;
    }

    &.active {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      border-color: #7b42f6;
      box-shadow: 0 2px 8px rgba(123, 66, 246, 0.25);

      .sheet-tab-name {
        color: #fff;
      }

      .sheet-tab-badge {
        background: rgba(255, 255, 255, 0.25);
        color: #fff;
      }
    }
  }

  .sheet-tab-name {
    font-size: 13px;
    color: #333;
    font-weight: 500;
  }

  .sheet-tab-badge {
    font-size: 11px;
    padding: 2px 6px;
    background: rgba(123, 66, 246, 0.1);
    color: #7b42f6;
    border-radius: 10px;
    font-weight: 500;
  }
}

.example-data {
  color: #999;
  font-size: 13px;
}

.step-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  justify-content: flex-end;

  .el-button {
    transition: all 0.25s ease;

    &:hover {
      background: #7b42f6;
      border-color: #7b42f6;
      color: #fff;
    }
  }
}

.generate-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-top: 20px;
}

.generate-config {
  background: linear-gradient(135deg, #faf8ff 0%, #f5f3ff 100%);
  padding: 12px 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  border: 1px solid rgba(147, 112, 219, 0.15);

  .config-row {
    display: flex;
    gap: 24px;
    align-items: center;
    justify-content: space-between;
  }

  .config-item {
    display: flex;
    align-items: center;
    gap: 8px;

    .config-label {
      color: #666;
      font-size: 13px;
      white-space: nowrap;
      font-weight: 500;
    }

    :deep(.el-input-number) {
      width: 100px;
    }
  }

  .config-actions {
    display: flex;
    gap: 10px;
    margin-left: auto;

    .preview-btn {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      border: none;
      transition: all 0.25s ease;

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
      }

      &:active {
        transform: translateY(0);
      }
    }

    .el-button {
      padding: 8px 16px;
      font-size: 13px;

      .el-icon {
        margin-right: 4px;
      }
    }
  }
}

.config-tip {
  margin-left: 10px;
  color: #999;
  font-size: 13px;
}

.generate-actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;

  .preview-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    border: none;
    transition: all 0.25s ease;

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }
}

.data-preview {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-top: 24px;
  background: linear-gradient(135deg, #faf8ff 0%, #f5f3ff 100%);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(147, 112, 219, 0.12);
  box-shadow: 0 4px 20px rgba(123, 66, 246, 0.06);

  .preview-header {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);

    .preview-title-section {
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: nowrap;

      h3 {
        margin: 0;
        color: #5a32a3;
        font-weight: 600;
        font-size: 18px;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
        white-space: nowrap;
      }

      .preview-sheet-tabs {
        flex: 1;
        overflow-x: auto;
        scrollbar-width: none;
        -ms-overflow-style: none;

        &::-webkit-scrollbar {
          display: none;
        }

        // 复用步骤2的sheet-tab-list样式
        .sheet-tab-list {
          display: flex;
          flex-wrap: nowrap;
          gap: 10px;
        }

        .sheet-tab-item {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          background: #f5f5f5;
          border-radius: 16px;
          cursor: pointer;
          transition: all 0.2s ease;
          border: 1px solid transparent;
          white-space: nowrap;

          &:hover {
            background: #ebebeb;
          }

          &.active {
            background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
            border-color: #7b42f6;
            box-shadow: 0 2px 8px rgba(123, 66, 246, 0.25);

            .sheet-tab-name {
              color: #fff;
            }
          }
        }

        .sheet-tab-name {
          font-size: 13px;
          color: #333;
          font-weight: 500;
        }
      }
    }
  }

  :deep(.el-table) {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #fff;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);

    .el-table__header-wrapper {
      background: linear-gradient(135deg, #f8f6ff 0%, #f0ecff 100%);
      overflow-x: auto;
      scrollbar-width: none;
      -ms-overflow-style: none;

      &::-webkit-scrollbar {
        display: none;
      }

      th {
        background: transparent;
        color: #5a32a3;
        font-weight: 600;
        font-size: 13px;
        padding: 14px 12px;
        border-bottom: 1px solid rgba(147, 112, 219, 0.15);
        white-space: nowrap;

        .cell {
          white-space: nowrap;
        }
      }
    }

    .el-table__body-wrapper {
      overflow-x: auto;
      scrollbar-width: thin;
      scrollbar-color: rgba(123, 66, 246, 0.3) transparent;

      td {
        padding: 12px;
        color: #444;
        font-size: 13px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.04);
        transition: background 0.2s ease;
        white-space: nowrap;
      }

      tr:hover td {
        background: rgba(123, 66, 246, 0.04);
      }

      tr:nth-child(even) {
        background: rgba(250, 248, 255, 0.5);
      }
    }

    .cell {
      line-height: 1.5;
    }
  }
}

.help-content {
  line-height: 1.8;

  h4 {
    margin: 20px 0 10px 0;
    color: #5a32a3;
    font-weight: 600;

    &:first-child {
      margin-top: 0;
    }
  }

  p {
    color: #666;
    margin: 10px 0;
  }

  ol,
  ul {
    color: #666;
    padding-left: 20px;
  }

  li {
    margin: 8px 0;
  }

  strong {
    color: #333;
    font-weight: 400;
  }
}

// 表格样式优化
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(147, 112, 219, 0.15);

  th.el-table__cell {
    background: linear-gradient(135deg, #faf8ff 0%, #f5f3ff 100%);
    color: #5a32a3;
    font-weight: 600;
    border-bottom: 1px solid rgba(147, 112, 219, 0.15);
    text-align: center;
    justify-content: center;
  }

  td.el-table__cell {
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);
    text-align: center;
  }

  tr:hover {
    background-color: rgba(147, 112, 219, 0.05);
  }
}

// 徽章样式
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  transition: all 0.3s ease;
  white-space: nowrap;
  min-width: 36px; /* 最小宽度保证一致性 */
  height: 20px; /* 固定高度保证一致性 */
  box-sizing: border-box; /* 确保padding不影响实际宽度计算 */

  // 成功 - 绿色
  &.success {
    background: #f6ffed;
    color: #52c41a;
  }

  // 警告 - 橙色
  &.warning {
    background: #fffbe6;
    color: #faad14;
  }

  // 信息 - 蓝色
  &.info {
    background: #e6f4ff;
    color: #1890ff;
  }

  // 默认 - 灰色
  &.default {
    background: #f5f5f5;
    color: #8c8c8c;
  }

  // 必填 - 红色
  &.required {
    background: #fff2f0;
    color: #ff4d4f;
  }

  // 非必填 - 灰色
  &.optional {
    background: #f5f5f5;
    color: #8c8c8c;
  }

  // 姓名 - 天蓝色
  &.name {
    background: #e6f7ff;
    color: #1890ff;
  }

  // 手机号 - 青色
  &.phone {
    background: #e6fffb;
    color: #13c2c2;
  }

  // 邮箱 - 紫色
  &.email {
    background: #f9f0ff;
    color: #722ed1;
  }

  // 身份证 - 橙色
  &.idcard {
    background: #fff7e6;
    color: #fa8c16;
  }

  // 地址 - 深青色
  &.address {
    background: #e6fffb;
    color: #006d75;
  }

  // 省市区县 - 蓝绿色
  &.location {
    background: #e6f7ff;
    color: #08979c;
  }

  // 公司 - 深蓝色
  &.company {
    background: #f0f5ff;
    color: #2f54eb;
  }

  // 银行卡 - 金黄色
  &.bank {
    background: #fffbe6;
    color: #d48806;
  }

  // 数值 - 深紫色
  &.number {
    background: #f9f0ff;
    color: #531dab;
  }

  // 日期 - 玫红色
  &.date {
    background: #fff0f6;
    color: #c41d7f;
  }

  // 选项 - 绿色
  &.select {
    background: #f6ffed;
    color: #389e0d;
  }

  // 文本 - 灰色
  &.text {
    background: #f5f5f5;
    color: #595959;
  }

  // UUID - 深灰色
  &.uuid {
    background: #fafafa;
    color: #262626;
  }

  // 学历 - 靛蓝色
  &.education {
    background: #f0f5ff;
    color: #1d39c4;
  }

  // 学校 - 浅蓝色
  &.school {
    background: #e6f7ff;
    color: #096dd9;
  }

  // 学科 - 蓝紫色
  &.subject {
    background: #f0f5ff;
    color: #4b5cb8;
  }

  // 民族 - 棕色
  &.ethnicity {
    background: #fff2e8;
    color: #ad6800;
  }

  // 性别 - 粉红色
  &.gender {
    background: #fff0f6;
    color: #eb2f96;
  }
}

// ========== 模式切换标签样式 ==========
.mode-tabs {
  display: flex;
  gap: 8px;
  padding: 4px;
  background: rgba(147, 112, 219, 0.08);
  border-radius: 10px;

  .mode-tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    color: #666;
    font-size: 14px;
    font-weight: 500;

    .mode-icon {
      font-size: 16px;
    }

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

// ========== 模块课程生成样式 ==========
.module-course-section {
  padding: 24px;

  .module-config-card,
  .module-preview-card {
    background: #fff;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
    border: 1px solid rgba(147, 112, 219, 0.1);
    box-shadow: 0 2px 12px rgba(147, 112, 219, 0.05);
  }

  // 配置头部
  .config-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 16px;
      font-weight: 600;
      color: #333;
      margin: 0;

      .el-icon {
        color: #7b42f6;
        font-size: 18px;
      }
    }

    .data-count-badge {
      padding: 6px 12px;
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      color: white;
      font-size: 13px;
      font-weight: 500;
      border-radius: 16px;

      &.warning {
        background: linear-gradient(135deg, #f56c6c 0%, #e64c4c 100%);
      }
    }
  }

  .config-form {
    .config-row {
      display: flex;
      gap: 20px;
      margin-bottom: 16px;

      @media (max-width: 768px) {
        flex-direction: column;
        gap: 12px;
      }

      // 四列布局：用于数量/长度配置行
      &.four-cols {
        .config-item {
          flex: 1;
          min-width: 0;
        }

        @media (max-width: 992px) {
          flex-wrap: wrap;

          .config-item {
            flex: 0 0 calc(50% - 10px);
          }
        }

        @media (max-width: 576px) {
          .config-item {
            flex: 1 1 100%;
          }
        }
      }
    }

    .config-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 0;

      .config-label {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        color: #666;
        font-weight: 500;
        white-space: nowrap;

        .help-icon {
          color: #bbb;
          font-size: 13px;
          cursor: help;

          &:hover {
            color: #7b42f6;
          }
        }
      }

      :deep(.el-input-number) {
        width: 100%;

        .el-input__wrapper {
          border-radius: 6px;
        }
      }

      :deep(.el-input__wrapper) {
        border-radius: 6px;
      }
    }

    // 点播课ID录入区域样式
    .course-ids-section {
      margin: 12px 0;
      padding: 14px 16px;
      background: #f8f9fa;
      border-radius: 8px;
      border: 1px solid rgba(147, 112, 219, 0.08);

      .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;

        .section-subtitle {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          color: #555;
          font-weight: 500;
          margin: 0;

          .el-icon {
            color: #7b42f6;
            font-size: 14px;
          }
        }
      }

      .course-ids-input {
        :deep(.el-textarea__inner) {
          font-family: monospace;
          font-size: 12px;
          padding: 10px 12px;
          border-radius: 6px;
        }

        .course-ids-stats {
          margin-top: 6px;
          font-size: 12px;
          color: #999;
          text-align: right;

          .text-warning {
            color: #e6a23c;
            font-weight: 500;
          }
        }
      }
    }

    .config-actions {
      display: flex;
      gap: 12px;
      margin-top: 16px;

      .el-button {
        flex: 1;
        height: 40px;
        font-size: 14px;
        font-weight: 500;
        border-radius: 8px;

        .el-icon {
          margin-right: 4px;
        }

        // 预览按钮 - 紫色主题
        &.el-button--primary {
          background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
          border: none;

          &:hover {
            background: linear-gradient(135deg, #8a5af7 0%, #6a42b3 100%);
          }

          &:active {
            background: linear-gradient(135deg, #6a35d9 0%, #4a2891 100%);
          }
        }

        // 下载按钮 - 绿色主题
        &.el-button--success {
          background: linear-gradient(135deg, #67c23a 0%, #529b2d 100%);
          border: none;

          &:hover {
            background: linear-gradient(135deg, #85ce61 0%, #6eb04a 100%);
          }

          &:active {
            background: linear-gradient(135deg, #5daf34 0%, #458a28 100%);
          }

          &.is-disabled {
            background: linear-gradient(135deg, #b3e19d 0%, #a4d68c 100%);
          }
        }
      }
    }
  }

  // 预览卡片
  .module-preview-card {
    margin-top: 20px;
    padding: 20px;
    background: white;
    border-radius: 12px;
    border: 1px solid rgba(147, 112, 219, 0.1);
    box-shadow: 0 2px 12px rgba(147, 112, 219, 0.05);

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      font-weight: 600;
      color: #333;
      margin-bottom: 16px;

      .el-icon {
        color: #7b42f6;
      }
    }

    .el-table {
      .empty-cell {
        color: #bbb;
      }
    }
  }
}
</style>