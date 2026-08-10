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

// ========== 模块课程数据生成 ==========

/**
 * 生成模块课程测试数据（按模块导入点播课）
 * @param {Object} params - 生成参数
 * @param {number} params.primary_count - 一级模块数量
 * @param {number} params.secondary_count - 每个一级模块下的二级模块数量
 * @param {number} params.primary_max_length - 一级模块名称最大长度
 * @param {number} params.secondary_max_length - 二级模块名称最大长度
 * @param {number} params.data_start_row - 数据起始行号
 * @param {string} params.primary_prefix - 一级模块名称前缀
 * @param {string} params.secondary_prefix - 二级模块名称前缀
 * @param {string[]} params.course_ids - 点播课ID列表（可选）
 * @param {string} params.action - 'preview' 或 'download'
 * @returns {Promise} - 预览数据或下载文件
 */
export function generateModuleCourseData(params) {
  const { action = 'preview', ...otherParams } = params

  if (action === 'download') {
    return request({
      url: '/data-factory/module-course/generate/',
      method: 'post',
      data: { ...otherParams, action: 'download' },
      responseType: 'blob'
    })
  }

  return request({
    url: '/data-factory/module-course/generate/',
    method: 'post',
    data: { ...otherParams, action: 'preview' }
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

// ========== 云效同步 (新增) ==========

/**
 * 获取云效项目列表
 * @param {Object} data - { token, organization_id, domain, keyword, page, per_page }
 */
export function getYunxiaoProjects(data) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/projects/',
    method: 'post',
    data
  })
}

/**
 * 获取云效迭代列表
 * @param {Object} data - { token, organization_id, domain, space_id, page, per_page }
 */
export function getYunxiaoSprints(data) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/sprints/',
    method: 'post',
    data
  })
}

/**
 * 获取云效项目成员列表
 * @param {Object} data - { token_id, space_id }
 */
export function getYunxiaoMembers(data) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/members/',
    method: 'post',
    data
  })
}

/**
 * 获取云效项目标签列表 (用于模块选择)
 * @param {Object} data - { token_id, space_id }
 */
export function getYunxiaoLabels(data) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/labels/',
    method: 'post',
    data
  })
}

/**
 * 从云效同步 Bug 数据并分析
 * @param {Object} data - { token, organization_id, domain, space_id, sprint_id, version_tag, ai_provider, skip_ai, max_bugs }
 */
export function syncFromYunxiao(data) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/sync/',
    method: 'post',
    data,
    timeout: 120000  // 只拉取数据+基础分析，AI在后台异步执行
  })
}

/**
 * 获取云效同步数据的详细字段信息（用于诊断）
 * @param {number} recordId - 分析记录ID
 */
export function getYunxiaoSyncLog(recordId) {
  return request({
    url: `/data-factory/bug-analysis/yunxiao/log/${recordId}/`,
    method: 'get'
  })
}

/**
 * 查询 AI 分析状态（异步轮询）
 * @param {number} recordId - 分析记录ID
 */
export function getBugAnalysisAiStatus(recordId) {
  return request({
    url: `/data-factory/bug-analysis/records/${recordId}/ai-status/`,
    method: 'get'
  })
}

// ========== Bug 双向同步 (云效写入 + 反向同步) ==========

/**
 * 创建 Bug 并推送到云效指定迭代
 * @param {Object|FormData} data - Bug数据（支持FormData包含附件）
 * @param {Object} [config] - axios配置（如headers）
 */
export function createBugToYunxiao(data, config = {}) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/create-bug/',
    method: 'post',
    data,
    timeout: 120000,  // 上传文件需要更长超时
    ...config
  })
}

/**
 * 更新 Bug 并同步到云效
 * @param {number} syncItemId - 同步项ID
 * @param {Object} data - Bug更新数据 + 云效认证信息
 */
export function updateBugToYunxiao(syncItemId, data) {
  return request({
    url: `/data-factory/bug-analysis/yunxiao/update-bug/${syncItemId}/`,
    method: 'put',
    data,
    timeout: 30000
  })
}

/**
 * 快捷修改Bug状态，支持上传截图
 * @param {number} syncItemId - 同步项ID
 * @param {FormData} formData - { token_id, status, screenshot?, comment? }
 */
export function quickChangeBugStatus(syncItemId, formData) {
  return request({
    url: `/data-factory/bug-analysis/yunxiao/quick-change-status/${syncItemId}/`,
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000
  })
}

/**
 * 获取 Bug 同步项列表
 * @param {Object} params - { analysis_record_id?, sync_status?, page?, page_size? }
 */
export function getBugSyncItems(params) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/sync-items/',
    method: 'get',
    params
  })
}

/**
 * 轮询云效 Bug 状态变更 (反向同步)
 * @param {Object} params - 云效认证信息 + 过滤条件
 */
export function pollRemoteStatus(params) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/poll-status/',
    method: 'get',
    params,
    timeout: 60000
  })
}

/**
 * 删除 Bug 同步项
 * @param {number} syncItemId - 同步项ID
 */
export function deleteBugSyncItem(syncItemId) {
  return request({
    url: `/data-factory/bug-analysis/yunxiao/sync-items/${syncItemId}/delete/`,
    method: 'delete'
  })
}

/**
 * 重新同步单个Bug项（从云效获取最新信息，补全serialNumber等字段）
 * @param {number} syncItemId - 同步项ID
 */
export function resyncBugItem(syncItemId) {
  return request({
    url: `/data-factory/bug-analysis/yunxiao/resync-item/${syncItemId}/`,
    method: 'post'
  })
}

// ========== 云效 Token 配置管理 ==========

/**
 * 获取云效 Token 列表
 * @param {Object} params - { keyword?, is_active?, page?, page_size? }
 */
export function getYunxiaoTokens(params) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/tokens/',
    method: 'get',
    params
  })
}

/**
 * 创建云效 Token
 * @param {Object} data - { label, token, is_active? }
 */
export function createYunxiaoToken(data) {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/tokens/',
    method: 'post',
    data
  })
}

/**
 * 更新云效 Token
 * @param {number} tokenId - Token ID
 * @param {Object} data - { label?, token?, is_active? }
 */
export function updateYunxiaoToken(tokenId, data) {
  return request({
    url: `/data-factory/bug-analysis/yunxiao/tokens/${tokenId}/`,
    method: 'put',
    data
  })
}

/**
 * 删除云效 Token
 * @param {number} tokenId - Token ID
 */
export function deleteYunxiaoToken(tokenId) {
  return request({
    url: `/data-factory/bug-analysis/yunxiao/tokens/${tokenId}/`,
    method: 'delete'
  })
}

/**
 * 获取启用的 Token 选项列表 (用于下拉选择)
 */
export function getYunxiaoTokenOptions() {
  return request({
    url: '/data-factory/bug-analysis/yunxiao/tokens/options/',
    method: 'get'
  })
}

/**
 * 测试 Token 是否有效
 * @param {number} tokenId - Token ID
 * @param {Object} data - { test_space_id? }
 */
export function testYunxiaoToken(tokenId, data) {
  return request({
    url: `/data-factory/bug-analysis/yunxiao/tokens/${tokenId}/test/`,
    method: 'post',
    data,
    timeout: 15000
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
