/**
 * 测试用例相关 API
 */
import request from '@/utils/api'

// 获取测试用例列表
export function getTestCaseList(params) {
  return request({
    url: '/testcases/',
    method: 'get',
    params
  })
}

// 获取测试用例详情
export function getTestCaseDetail(id) {
  return request({
    url: `/testcases/${id}/`,
    method: 'get'
  })
}

// 创建测试用例
export function createTestCase(data) {
  return request({
    url: '/testcases/',
    method: 'post',
    data
  })
}

// 更新测试用例
export function updateTestCase(id, data) {
  return request({
    url: `/testcases/${id}/`,
    method: 'patch',
    data
  })
}

// 删除测试用例
export function deleteTestCase(id) {
  return request({
    url: `/testcases/${id}/`,
    method: 'delete'
  })
}

// 获取模块列表
export function getTestCaseModules() {
  return request({
    url: '/testcases/modules/',
    method: 'get'
  })
}

// 获取用例统计
export function getTestCaseStatistics(params) {
  return request({
    url: '/testcases/statistics/',
    method: 'get',
    params
  })
}

// 获取作者用例详情
export function getAuthorTestCases(params) {
  return request({
    url: '/testcases/author-cases/',
    method: 'get',
    params
  })
}

// 批量修改审核结果
export function batchUpdateReviewStatus(data) {
  return request({
    url: '/testcases/batch-review/',
    method: 'post',
    data
  })
}
