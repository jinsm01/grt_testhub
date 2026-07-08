import request from '@/utils/api'

// ==================== 自动化测试套件 API ====================

// 获取套件列表
export function getAutomationSuites(params) {
  return request({
    url: '/api-testing/test-suites/',
    method: 'get',
    params
  })
}

// 创建套件
export function createAutomationSuite(data) {
  return request({
    url: '/api-testing/test-suites/',
    method: 'post',
    data
  })
}

// 获取套件详情
export function getAutomationSuite(id) {
  return request({
    url: `/api-testing/test-suites/${id}/`,
    method: 'get'
  })
}

// 更新套件
export function updateAutomationSuite(id, data) {
  return request({
    url: `/api-testing/test-suites/${id}/`,
    method: 'patch',
    data
  })
}

// 删除套件
export function deleteAutomationSuite(id) {
  return request({
    url: `/api-testing/test-suites/${id}/`,
    method: 'delete'
  })
}

// 执行套件
export function executeAutomationSuite(id, data) {
  return request({
    url: `/api-testing/test-suites/${id}/execute/`,
    method: 'post',
    data
  })
}

// 获取套件执行历史
export function getSuiteExecutions(id, params) {
  return request({
    url: `/api-testing/test-suites/${id}/executions/`,
    method: 'get',
    params
  })
}

// 获取执行报告
export function getSuiteReport(id) {
  return request({
    url: `/api-testing/test-suites/${id}/report/`,
    method: 'get'
  })
}

// ==================== 套件执行记录 API ====================

// 获取所有执行记录
export function getSuiteExecutionList(params) {
  return request({
    url: '/api-testing/suite-executions/',
    method: 'get',
    params
  })
}

// 获取执行记录详情
export function getSuiteExecutionDetail(id) {
  return request({
    url: `/api-testing/suite-executions/${id}/`,
    method: 'get'
  })
}

// 获取执行记录详情报告
export function getSuiteExecutionReport(id) {
  return request({
    url: `/api-testing/suite-executions/${id}/detail_report/`,
    method: 'get'
  })
}

// ==================== 自动化场景 API ====================

// 获取场景列表（用于套件中选择场景）
export function getScenarios(params) {
  return request({
    url: '/api-testing/scenarios/',
    method: 'get',
    params
  })
}

// 获取场景详情
export function getScenario(id) {
  return request({
    url: `/api-testing/scenarios/${id}/`,
    method: 'get'
  })
}

// 关联场景到主线用例
export function linkScenarioMainline(id, testCaseId) {
  return request({
    url: `/api-testing/scenarios/${id}/link-mainline/`,
    method: 'post',
    data: { test_case_id: testCaseId }
  })
}

// 确认场景主线用例内容
export function confirmScenarioMainline(id) {
  return request({
    url: `/api-testing/scenarios/${id}/confirm-mainline/`,
    method: 'post'
  })
}

// 检查场景主线用例是否有更新
export function checkScenarioMainline(id) {
  return request({
    url: `/api-testing/scenarios/${id}/check-mainline/`,
    method: 'get'
  })
}

// ==================== 套件评审（主线用例同步）API ====================

// 获取套件评审摘要
export function getSuiteReviewSummary(id) {
  return request({
    url: `/api-testing/automation-suites/${id}/review_summary/`,
    method: 'get'
  })
}

// 提交套件评审（一键确认所有场景主线用例）
export function reviewSuite(id, confirmAll = true) {
  return request({
    url: `/api-testing/automation-suites/${id}/review/`,
    method: 'post',
    data: { confirm_all: confirmAll }
  })
}

// 重置套件评审
export function resetSuiteReviews(id) {
  return request({
    url: `/api-testing/automation-suites/${id}/reset_reviews/`,
    method: 'post'
  })
}

// 获取环境列表
export function getEnvironments(params) {
  return request({
    url: '/api-testing/environments/',
    method: 'get',
    params
  })
}

// ==================== AutomationSuite（自动化套件）主线用例关联 API ====================

// 关联自动化套件到主线用例
export function linkAutomationSuiteMainline(id, testCaseId) {
  return request({
    url: `/api-testing/test-suites/${id}/link-mainline/`,
    method: 'post',
    data: { test_case_id: testCaseId }
  })
}

// 取消自动化套件与主线用例的关联
export function unlinkAutomationSuiteMainline(id) {
  return request({
    url: `/api-testing/test-suites/${id}/unlink-mainline/`,
    method: 'post'
  })
}

// 获取可关联到自动化套件的主线用例列表
export function getAutomationSuiteAvailableMainlines(id, params = {}) {
  return request({
    url: `/api-testing/test-suites/${id}/available-mainlines/`,
    method: 'get',
    params
  })
}

// 确认自动化套件主线用例内容
export function confirmAutomationSuiteMainline(id) {
  return request({
    url: `/api-testing/test-suites/${id}/confirm-mainline/`,
    method: 'post'
  })
}

// 检查自动化套件主线用例是否有更新
export function checkAutomationSuiteMainline(id) {
  return request({
    url: `/api-testing/test-suites/${id}/check-mainline/`,
    method: 'get'
  })
}

// 自动化套件一键确认（等价于旧版的 AI 审核）
export function reviewAutomationSuite(id) {
  return request({
    url: `/api-testing/test-suites/${id}/review/`,
    method: 'post'
  })
}

// 自动化套件重置评审
export function resetAutomationSuiteReviews(id) {
  return request({
    url: `/api-testing/test-suites/${id}/reset_reviews/`,
    method: 'post'
  })
}

// ==================== 套件-场景关联 API ====================

// 更新套件-场景关联（替换旧的 TestSuiteRequest 更新）
export function updateSuiteScenario(id, data) {
  return request({
    url: `/api-testing/automation-suite-scenarios/${id}/`,
    method: 'patch',
    data
  })
}

// 添加场景到套件
export function addScenarioToSuite(suiteId, data) {
  return request({
    url: `/api-testing/automation-suites/${suiteId}/add-requests/`,
    method: 'post',
    data
  })
}

// 删除套件中的场景
export function removeSuiteScenario(id) {
  return request({
    url: `/api-testing/automation-suite-scenarios/${id}/`,
    method: 'delete'
  })
}

// 重新排序套件中的场景
export function reorderSuiteScenarios(suiteId, data) {
  return request({
    url: `/api-testing/automation-suites/${suiteId}/reorder/`,
    method: 'post',
    data
  })
}



