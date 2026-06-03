import request from '@/utils/api'

// 获取工具分类
export function getCategories() {
  return request({
    url: '/data-factory/categories/',
    method: 'get'
  })
}

// 获取数据工厂记录列表
export function getDataFactoryRecords(params) {
  return request({
    url: '/data-factory/',
    method: 'get',
    params
  })
}

// 获取数据工厂标签列表
export function getDataFactoryTags() {
  return request({
    url: '/data-factory/tags/',
    method: 'get'
  })
}

// 获取数据工厂分类列表
export function getDataFactoryCategories() {
  return request({
    url: '/data-factory/categories/',
    method: 'get'
  })
}

// 执行工具
export function executeTool(data) {
  return request({
    url: '/data-factory/',
    method: 'post',
    data
  })
}

// 获取历史记录
export function getHistory(params) {
  return request({
    url: '/data-factory/',
    method: 'get',
    params
  })
}

// 获取统计信息
export function getStatistics() {
  return request({
    url: '/data-factory/statistics/',
    method: 'get'
  })
}

// 删除记录
export function deleteRecord(id) {
  return request({
    url: `/data-factory/${id}/`,
    method: 'delete'
  })
}

// 批量生成
export function batchGenerate(data) {
  return request({
    url: '/data-factory/batch_generate/',
    method: 'post',
    data
  })
}

// DataFactoryRecord 类型定义
/**
 * @typedef {Object} DataFactoryRecord
 * @property {number} id - 记录ID
 * @property {string} tool_name - 工具名称
 * @property {string} tool_name_display - 工具显示名称
 * @property {string} tool_category - 工具分类
 * @property {string} tool_category_display - 分类显示名称
 * @property {Object} input_params - 输入参数
 * @property {Object} output_data - 输出数据
 * @property {string} created_at - 创建时间
 * @property {string[]} tags - 标签列表
 */

// Excel智能填充 - 分析模板
export function analyzeExcelTemplate(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/data-factory/excel-filler/analyze/',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// Excel智能填充 - 预览数据
export function previewFilledData(file, rowCount = 5, customFields = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('row_count', String(rowCount))
  if (Object.keys(customFields).length > 0) {
    formData.append('custom_fields', JSON.stringify(customFields))
  }
  return request({
    url: '/data-factory/excel-filler/preview/',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// Excel智能填充 - 生成并下载文件
export function fillExcelData(file, rowCount = 10, customFields = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('row_count', String(rowCount))
  if (Object.keys(customFields).length > 0) {
    formData.append('custom_fields', JSON.stringify(customFields))
  }
  return request({
    url: '/data-factory/excel-filler/fill/',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    responseType: 'blob'
  })
}

// ========== Bug分析 ==========

/**
 * @typedef {Object} BugAnalysisResult
 * @property {boolean} success - 是否成功
 * @property {string} message - 消息
 * @property {number} [record_id] - 保存的记录ID
 */

// 上传并分析Bug Excel文件 (V2: 支持AI增强和版本标签)
export function analyzeBugExcel(file, options = {}) {
  const formData = new FormData()
  formData.append('file', file)
  if (options.save !== undefined) formData.append('save', String(options.save))
  if (options.aiProvider) formData.append('ai_provider', options.aiProvider)
  if (options.versionTag) formData.append('version_tag', options.versionTag)
  if (options.aiConfigId) formData.append('ai_config_id', String(options.aiConfigId))
  // skip_ai: false 表示需要AI增强，后端会返回 ai_pending=true
  if (options.skip_ai !== undefined) formData.append('skip_ai', String(options.skip_ai))
  return request({
    url: '/data-factory/bug-analysis/analyze/',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    timeout: 30000  // 基础分析很快，30秒足够
  })
}

// 直接分析Bug数据(JSON格式) (V2增强)
export function analyzeBugData(bugs, filename = 'unknown', options = {}) {
  return request({
    url: '/data-factory/bug-analysis/analyze-data/',
    method: 'post',
    data: {
      bugs,
      filename,
      save: options.save || false,
      ai_provider: options.aiProvider || 'none',
      version_tag: options.versionTag || ''
    }
  })
}

// 获取Bug分析记录列表 (V2新增)
export function getBugAnalysisRecords(params = {}) {
  return request({
    url: '/data-factory/bug-analysis/records/',
    method: 'get',
    params
  })
}

// 获取单条分析记录详情 (V2新增)
export function getBugAnalysisRecordDetail(recordId) {
  return request({
    url: `/data-factory/bug-analysis/records/${recordId}/`,
    method: 'get'
  })
}

// 删除分析记录 (V2新增)
export function deleteBugAnalysisRecord(recordId) {
  return request({
    url: `/data-factory/bug-analysis/records/${recordId}/delete/`,
    method: 'delete'
  })
}

// 跨版本对比分析记录 (V2新增)
export function compareBugAnalysis(ids) {
  return request({
    url: '/data-factory/bug-analysis/compare/',
    method: 'get',
    params: { ids: ids.join(',') }
  })
}

// 获取模块详情(含Bug列表) (V2新增)
export function getModuleDetail(recordId, module, params = {}) {
  const queryParams = new URLSearchParams({ module, ...params })
  return request({
    url: `/data-factory/bug-analysis/module/${recordId}/?${queryParams.toString()}`,
    method: 'get'
  })
}

// AI 增强分析 (渐进式加载)
export function enhanceWithAI(recordId, options = {}) {
  return request({
    url: '/data-factory/bug-analysis/enhance-ai/',
    method: 'post',
    data: {
      record_id: recordId,
      ai_provider: options.aiProvider || 'qwen',
      ai_config_id: options.aiConfigId || null
    },
    timeout: 300000  // AI分析可能需要较长时间，设置5分钟超时
  })
}

// 智能模块测试重点分析 (三层架构)
export function analyzeModuleFocusIntelligent(recordId, module, options = {}) {
  return request({
    url: '/data-factory/bug-analysis/module-focus/',
    method: 'post',
    data: {
      record_id: recordId,
      module: module,
      ai_config_id: options.aiConfigId || null
    },
    timeout: 120000  // AI分析可能需要较长时间，设置2分钟超时
  })
}

// ========== AI 评分量表生成管理 ==========

/**
 * 获取AI量表生成记录列表
 * @param {Object} params - { status?: string, search?: string }
 */
export function getRubricRecords(params = {}) {
  return request({
    url: '/data-factory/rubric/records/',
    method: 'get',
    params
  })
}

/**
 * 获取AI量表生成记录详情（含完整数据）
 */
export function getRubricDetail(recordId) {
  return request({
    url: `/data-factory/rubric/${recordId}/`,
    method: 'get'
  })
}

/**
 * 创建并执行量表生成任务
 * @param {FormData} formData - 包含 name, note_count, pass_ratio, [file]
 */
export function generateRubric(formData) {
  return request({
    url: '/data-factory/rubric/generate/',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

/**
 * 删除AI量表生成记录
 */
export function deleteRubricRecord(recordId) {
  return request({
    url: `/data-factory/rubric/${recordId}/delete/`,
    method: 'delete'
  })
}

/**
 * 获取AI量表统计信息
 */
export function getRubricStatistics() {
  return request({
    url: '/data-factory/rubric/statistics/',
    method: 'get'
  })
}
