
<template>
  <div class="generated-testcase-list">
    <div class="page-header">
      <h2>{{ $t('generatedTestCases.title') }}</h2>
      <p>点击导出MD，将下载文件导入Xmind生成测试脑图，提高效率</p>
    </div>

    <div class="filters-section">
      <div class="filter-card">
        <!-- 状态筛选标签 -->
        <div class="filter-group">
          <div class="status-tabs">
            <button 
              class="status-tab" 
              :class="{ active: selectedStatus === '' }"
              @click="selectedStatus = ''; loadTasks()">
              {{ $t('generatedTestCases.allStatus') }}
            </button>
            <button 
              class="status-tab pending" 
              :class="{ active: selectedStatus === 'pending' }"
              @click="selectedStatus = 'pending'; loadTasks()">
              {{ $t('generatedTestCases.statusPending') }}
            </button>
            <button 
              class="status-tab generating" 
              :class="{ active: selectedStatus === 'generating' }"
              @click="selectedStatus = 'generating'; loadTasks()">
              {{ $t('generatedTestCases.statusGenerating') }}
            </button>
            <button 
              class="status-tab reviewing" 
              :class="{ active: selectedStatus === 'reviewing' }"
              @click="selectedStatus = 'reviewing'; loadTasks()">
              {{ $t('generatedTestCases.statusReviewing') }}
            </button>
            <button 
              class="status-tab revising" 
              :class="{ active: selectedStatus === 'revising' }"
              @click="selectedStatus = 'revising'; loadTasks()">
              {{ $t('generatedTestCases.statusRevising') }}
            </button>
            <button 
              class="status-tab completed" 
              :class="{ active: selectedStatus === 'completed' }"
              @click="selectedStatus = 'completed'; loadTasks()">
              {{ $t('generatedTestCases.statusCompleted') }}
            </button>
            <button 
              class="status-tab failed" 
              :class="{ active: selectedStatus === 'failed' }"
              @click="selectedStatus = 'failed'; loadTasks()">
              {{ $t('generatedTestCases.statusFailed') }}
            </button>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="stats-divider" v-if="allStats.total > 0"></div>
        <div class="stats-container" v-if="allStats.total > 0">
          <div class="stat-item">
            <span class="stat-number">{{ allStats.total }}</span>
            <span class="stat-label">{{ $t('generatedTestCases.totalTasks') }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ allStats.completed }}</span>
            <span class="stat-label">{{ $t('generatedTestCases.completedCount') }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ allStats.running }}</span>
            <span class="stat-label">{{ $t('generatedTestCases.runningCount') }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ allStats.failed }}</span>
            <span class="stat-label">{{ $t('generatedTestCases.failedCount') }}</span>
          </div>
          <!-- 批量删除按钮 -->
          <button
            v-if="selectedTasks.length > 0"
            class="batch-delete-btn-inline"
            @click="batchDeleteTasks"
            :disabled="isDeleting">
            <span v-if="isDeleting">{{ $t('generatedTestCases.deleting') }}</span>
            <span v-else>{{ $t('generatedTestCases.batchDelete', { count: selectedTasks.length }) }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- AI任务列表 -->
    <div class="testcases-section">
      <div v-if="isLoading" class="loading-state">
        <p>{{ $t('generatedTestCases.loadingTasks') }}</p>
      </div>

      <div v-else-if="tasks.length === 0" class="empty-state">
        <div class="empty-icon">📝</div>
        <h3>{{ $t('generatedTestCases.noTasks') }}</h3>
        <p>{{ $t('generatedTestCases.emptyHint') }}<router-link to="/ai-generation/requirement-analysis">{{ $t('generatedTestCases.aiGeneration') }}</router-link>{{ $t('generatedTestCases.createTask') }}</p>
      </div>

      <div v-else class="testcases-table">
        <div class="table-header">
          <div class="table-header-row">
            <div class="header-cell checkbox-cell">
              <input
                type="checkbox"
                :checked="isAllSelected"
                @change="toggleSelectAll"
                class="checkbox-input">
            </div>
            <div class="header-cell serial-cell">{{ $t('generatedTestCases.serialNumber') }}</div>
            <div class="header-cell task-id-cell">{{ $t('generatedTestCases.taskId') }}</div>
            <div class="header-cell requirement-name-cell">{{ $t('generatedTestCases.requirement') }}</div>
            <div class="header-cell status-cell">{{ $t('generatedTestCases.status') }}</div>
            <div class="header-cell count-cell">{{ $t('generatedTestCases.caseCount') }}</div>
            <div class="header-cell time-cell">{{ $t('generatedTestCases.generationTime') }}</div>
            <div class="header-cell action-cell">{{ $t('generatedTestCases.actions') }}</div>
          </div>
        </div>

        <div class="table-body">
          <div
            v-for="(task, index) in tasks"
            :key="task.task_id"
            class="table-row"
            :class="{ selected: isTaskSelected(task.task_id) }">
            <div class="body-cell checkbox-cell">
              <input
                type="checkbox"
                :checked="isTaskSelected(task.task_id)"
                @change="toggleTaskSelection(task.task_id)"
                class="checkbox-input">
            </div>
            <div class="body-cell serial-cell">{{ getSerialNumber(index) }}</div>
            <div class="body-cell task-id-cell">{{ task.task_id }}</div>
            <div class="body-cell requirement-name-cell">
              <span class="requirement-name">{{ task.title }}</span>
            </div>
            <div class="body-cell status-cell">
              <span class="status-tag" :class="task.status">
                <i class="status-icon" :class="getStatusIcon(task.status)"></i>
                {{ getStatusText(task.status) }}
              </span>
            </div>
            <div class="body-cell count-cell">
              <span class="count-badge">{{ getTestCaseCount(task) }}</span>
            </div>
            <div class="body-cell time-cell">{{ formatDateTime(task.created_at) }}</div>
            <div class="body-cell action-cell">
              <div class="action-buttons">
                <button
                  v-if="task.status === 'completed'"
                  class="export-md-btn"
                  @click="exportTestCasesMD(task)">
                  {{ $t('generatedTestCases.exportMarkdown') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页组件 -->
    <div v-if="tasks.length > 0" class="pagination-section">
      <div class="pagination-simple">
        <button
          class="page-btn"
          :disabled="pagination.currentPage <= 1"
          @click="goToPage(pagination.currentPage - 1)">
          <
        </button>
        <span class="page-current">{{ pagination.currentPage }} / {{ totalPages }}</span>
        <button
          class="page-btn"
          :disabled="pagination.currentPage >= totalPages"
          @click="goToPage(pagination.currentPage + 1)">
          >
        </button>
      </div>
    </div>

    <!-- 测试用例详情弹窗 -->
    <div v-if="selectedTestCaseDetail" class="testcase-detail-modal" @click="closeTestCaseDetail">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ selectedTestCaseDetail.title }}</h3>
          <button class="close-btn" @click="closeTestCaseDetail">×</button>
        </div>
        <div class="modal-body">
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.caseNumber') }}</label>
            <span>{{ selectedTestCaseDetail.case_id }}</span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.relatedRequirement') }}</label>
            <span>{{ selectedTestCaseDetail.requirement_name }} ({{ selectedTestCaseDetail.requirement_id_display }})</span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.priority') }}</label>
            <span class="priority-tag" :class="selectedTestCaseDetail.priority.toLowerCase()">
              {{ selectedTestCaseDetail.priority_display }}
            </span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.status') }}</label>
            <span class="status-tag" :class="selectedTestCaseDetail.status">
              {{ selectedTestCaseDetail.status_display }}
            </span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.preconditions') }}</label>
            <p>{{ selectedTestCaseDetail.precondition }}</p>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.testSteps') }}</label>
            <p class="test-steps" v-html="selectedTestCaseDetail.test_steps"></p>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.expectedResult') }}</label>
            <p v-html="selectedTestCaseDetail.expected_result"></p>
          </div>
          <div class="detail-item" v-if="selectedTestCaseDetail.review_comments">
            <label>{{ $t('generatedTestCases.reviewComments') }}</label>
            <p>{{ selectedTestCaseDetail.review_comments }}</p>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.generatedAI') }}</label>
            <span>{{ selectedTestCaseDetail.generated_by_ai }}</span>
          </div>
          <div class="detail-item" v-if="selectedTestCaseDetail.reviewed_by_ai">
            <label>{{ $t('generatedTestCases.reviewedAI') }}</label>
            <span>{{ selectedTestCaseDetail.reviewed_by_ai }}</span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.generatedTime') }}</label>
            <span>{{ formatDateTime(selectedTestCaseDetail.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 采纳用例编辑弹框 -->
    <div v-if="showAdoptModal" class="testcase-detail-modal" @click="closeAdoptModal">
      <div class="modal-content large-modal" @click.stop>
        <div class="modal-header">
          <h3>{{ $t('generatedTestCases.adoptModalTitle') }}</h3>
          <button class="close-btn" @click="closeAdoptModal">×</button>
        </div>
        <div class="modal-body">
          <form class="adopt-form">
            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.caseTitle') }}</label>
                <input v-model="adoptForm.title" type="text" :placeholder="$t('generatedTestCases.caseTitlePlaceholder')" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.caseDescription') }}</label>
                <textarea v-model="adoptForm.description" rows="3" :placeholder="$t('generatedTestCases.caseDescriptionPlaceholder')"></textarea>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.belongsToProject') }} <span class="required">*</span></label>
                <select v-model="adoptForm.project_id" @change="onAdoptProjectChange">
                  <option value="">{{ $t('generatedTestCases.selectProject') }}</option>
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.name }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label>{{ $t('generatedTestCases.relatedVersion') }} <span class="required">*</span></label>
                <select v-model="adoptForm.version_id">
                  <option value="">{{ $t('generatedTestCases.selectVersion') }}</option>
                  <option v-for="version in availableVersions" :key="version.id" :value="version.id">
                    {{ version.name }}{{ version.is_baseline ? $t('generatedTestCases.baseline') : '' }}
                  </option>
                </select>
                <small class="form-hint">
                  {{ adoptForm.project_id ?
                      $t('generatedTestCases.showingProjectVersions', { project: getProjectName(adoptForm.project_id) }) :
                      $t('generatedTestCases.showingAllVersions') }}
                </small>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.priority') }}</label>
                <select v-model="adoptForm.priority">
                  <option value="low">{{ $t('generatedTestCases.priorityLow') }}</option>
                  <option value="medium">{{ $t('generatedTestCases.priorityMedium') }}</option>
                  <option value="high">{{ $t('generatedTestCases.priorityHigh') }}</option>
                  <option value="critical">{{ $t('generatedTestCases.priorityCritical') }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>{{ $t('generatedTestCases.testType') }}</label>
                <select v-model="adoptForm.test_type">
                  <option value="functional">{{ $t('generatedTestCases.testTypeFunctional') }}</option>
                  <option value="integration">{{ $t('generatedTestCases.testTypeIntegration') }}</option>
                  <option value="api">{{ $t('generatedTestCases.testTypeAPI') }}</option>
                  <option value="ui">{{ $t('generatedTestCases.testTypeUI') }}</option>
                  <option value="performance">{{ $t('generatedTestCases.testTypePerformance') }}</option>
                  <option value="security">{{ $t('generatedTestCases.testTypeSecurity') }}</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.status') }}</label>
                <select v-model="adoptForm.status">
                  <option value="draft">{{ $t('generatedTestCases.statusDraft') }}</option>
                  <option value="active">{{ $t('generatedTestCases.statusActive') }}</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.preconditions') }}</label>
                <textarea v-model="adoptForm.preconditions" rows="3" :placeholder="$t('generatedTestCases.preconditionsPlaceholder')"></textarea>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.operationSteps') }}</label>
                <textarea v-model="adoptForm.steps" rows="6" :placeholder="$t('generatedTestCases.operationStepsPlaceholder')"></textarea>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.expectedResult') }}</label>
                <textarea v-model="adoptForm.expected_result" rows="3" :placeholder="$t('generatedTestCases.expectedResultPlaceholder')"></textarea>
              </div>
            </div>

            <div class="form-actions">
              <button type="button" class="confirm-btn" @click="confirmAdopt" :disabled="isAdopting">
                {{ isAdopting ? $t('generatedTestCases.adopting') : $t('generatedTestCases.confirmAdopt') }}
              </button>
              <button type="button" class="cancel-btn" @click="closeAdoptModal">{{ $t('generatedTestCases.cancel') }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'


export default {
  name: 'GeneratedTestCaseList',
  data() {
    return {
      isLoading: false,
      tasks: [], // 改为任务列表
      selectedStatus: '',
      selectedTaskDetail: null,
      selectedTestCaseDetail: null,
      showAdoptModal: false,
      isAdopting: false,
      projects: [],
      projectVersions: [],
      allVersions: [], // 存储所有版本列表
      adoptForm: {
        title: '',
        description: '',
        project_id: null,
        priority: 'low', // 修改默认值为"低"
        test_type: 'functional',
        status: 'draft',
        preconditions: '',
        steps: '',
        expected_result: '',
        version_id: null // 改为单选
      },
      currentAdoptingTask: null,
      // 选择相关数据
      selectedTasks: [], // 已选中的任务ID列表
      isDeleting: false, // 是否正在删除
      // 分页相关数据
      pagination: {
        currentPage: 1,
        pageSize: 10, // 改为默认10条
        total: 0,
        pageSizeOptions: [10, 20, 50]
      },
      jumpPage: '', // 页码跳转输入
      // 统计数据
      allStats: {
        total: 0,
        completed: 0,
        running: 0,
        failed: 0
      }
    }
  },

  computed: {
    // 可用版本列表 - 根据是否选择项目来决定显示哪些版本
    availableVersions() {
      if (this.adoptForm.project_id) {
        // 如果选择了项目，显示该项目的版本
        return this.projectVersions
      } else {
        // 如果没有选择项目，显示系统所有版本
        return this.allVersions
      }
    },
    
    // 计算总页数
    totalPages() {
      return Math.ceil(this.pagination.total / this.pagination.pageSize)
    },
    
    // 计算分页显示信息
    paginationInfo() {
      const start = (this.pagination.currentPage - 1) * this.pagination.pageSize + 1
      const end = Math.min(this.pagination.currentPage * this.pagination.pageSize, this.pagination.total)
      return this.$t('generatedTestCases.paginationInfo', { start, end, total: this.pagination.total })
    },
    
    // 是否全选
    isAllSelected() {
      return this.tasks.length > 0 && this.selectedTasks.length === this.tasks.length
    }
  },
  
  mounted() {
    this.loadTasks()
    this.fetchProjects()
    this.fetchAllVersions()
  },
  
  methods: {
    async loadTasks() {
      this.isLoading = true
      try {
        let url = '/requirement-analysis/testcase-generation/'
        const params = new URLSearchParams()
        
        // 添加分页参数
        params.append('page', String(this.pagination.currentPage))
        params.append('page_size', String(this.pagination.pageSize))
        
        if (this.selectedStatus) {
          params.append('status', this.selectedStatus)
        }
        
        if (params.toString()) {
          url += '?' + params.toString()
        }
        
        const response = await api.get(url)
        
        if (response.data.results) {
          this.tasks = response.data.results
          this.pagination.total = response.data.count || 0
        } else {
          this.tasks = response.data || []
          this.pagination.total = this.tasks.length
        }
        
        // 更新统计数据（统计所有数据，不只是当前页）
        this.updateStats()
        
      } catch (error) {
        console.error(this.$t('generatedTestCases.loadTasksFailed'), error)
        this.tasks = []
        this.pagination.total = 0
      } finally {
        this.isLoading = false
        // 清空选择（因为任务列表已更新）
        this.selectedTasks = []
      }
    },

    // 获取序号
    getSerialNumber(index) {
      return (this.pagination.currentPage - 1) * this.pagination.pageSize + index + 1
    },

    // 切换任务选择
    toggleTaskSelection(taskId) {
      const index = this.selectedTasks.indexOf(taskId)
      if (index > -1) {
        this.selectedTasks.splice(index, 1)
      } else {
        this.selectedTasks.push(taskId)
      }
    },

    // 判断任务是否被选中
    isTaskSelected(taskId) {
      return this.selectedTasks.includes(taskId)
    },

    // 切换全选
    toggleSelectAll() {
      if (this.isAllSelected) {
        this.selectedTasks = []
      } else {
        this.selectedTasks = this.tasks.map(task => task.task_id)
      }
    },

    // 批量删除任务
    async batchDeleteTasks() {
      if (this.selectedTasks.length === 0) {
        ElMessage.warning(this.$t('generatedTestCases.selectTasksFirst'))
        return
      }

      if (!confirm(this.$t('generatedTestCases.batchDeleteConfirm', { count: this.selectedTasks.length }))) {
        return
      }

      this.isDeleting = true
      let successCount = 0
      let failCount = 0

      try {
        // 逐个删除选中的任务
        for (const taskId of this.selectedTasks) {
          try {
            await api.delete(`/requirement-analysis/testcase-generation/${taskId}/`)
            successCount++
          } catch (error) {
            console.error(`删除任务 ${taskId} 失败:`, error)
            failCount++
          }
        }

        // 显示删除结果
        if (successCount > 0) {
          ElMessage.success(this.$t('generatedTestCases.deleteSuccess', { success: successCount, failed: failCount }))
        } else {
          ElMessage.error(this.$t('generatedTestCases.deleteFailed'))
        }

        // 清空选择并重新加载列表
        this.selectedTasks = []
        this.loadTasks()

      } catch (error) {
        console.error(this.$t('generatedTestCases.batchDeleteFailed'), error)
        ElMessage.error(this.$t('generatedTestCases.batchDeleteFailed') + ': ' + (error.message || this.$t('generatedTestCases.unknownError')))
      } finally {
        this.isDeleting = false
      }
    },

    updateStats() {
      // 不再使用当前页数据统计，改为调用专门的统计方法
      this.loadAllStats()
    },

    // 新增方法：获取所有数据的统计信息
    async loadAllStats() {
      try {
        // 构建统计请求URL
        let url = '/requirement-analysis/testcase-generation/'
        const params = new URLSearchParams()
        
        // 获取所有数据来进行统计
        params.append('page_size', '10000') // 设置足够大的页面大小来获取所有数据
        params.append('page', '1')
        
        // 如果有状态筛选，也应用到统计中
        if (this.selectedStatus) {
          params.append('status', this.selectedStatus)
        }
        
        url += '?' + params.toString()
        
        const response = await api.get(url)
        const allTasks = response.data.results || response.data || []
        
        // 统计各状态的数量
        this.allStats.total = allTasks.length
        this.allStats.completed = allTasks.filter(t => t.status === 'completed').length
        this.allStats.running = allTasks.filter(t => ['pending', 'generating', 'reviewing'].includes(t.status)).length
        this.allStats.failed = allTasks.filter(t => t.status === 'failed').length
        
      } catch (error) {
        console.error(this.$t('generatedTestCases.loadStatsFailed'), error)
        // 如果获取统计失败，使用分页信息的总数作为备选
        this.allStats.total = this.pagination.total || 0
        this.allStats.completed = 0
        this.allStats.running = 0
        this.allStats.failed = 0
      }
    },

    getStatusText(status) {
      const statusMap = {
        'pending': this.$t('generatedTestCases.statusPending'),
        'generating': this.$t('generatedTestCases.statusGenerating'),
        'reviewing': this.$t('generatedTestCases.statusReviewing'),
        'revising': this.$t('generatedTestCases.statusRevising'),
        'completed': this.$t('generatedTestCases.statusCompleted'),
        'failed': this.$t('generatedTestCases.statusFailed')
      }
      return statusMap[status] || status
    },

    getStatusIcon(status) {
      const iconMap = {
        'pending': 'icon-pending',
        'generating': 'icon-generating',
        'reviewing': 'icon-reviewing',
        'revising': 'icon-revising',
        'completed': 'icon-completed',
        'failed': 'icon-failed'
      }
      return iconMap[status] || ''
    },



    // 获取测试用例条数
    getTestCaseCount(task) {
      if (!task.final_test_cases) {
        return 0
      }

      // 解析测试用例内容，计算条数
      const content = task.final_test_cases
      const lines = content.split('\n').filter(line => line.trim())

      // 尝试表格格式
      let tableRows = 0
      let isFirstRow = true
      let isTableFormat = false

      for (let line of lines) {
        if (line.includes('|') && !line.includes('--------')) {
          const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell)
          if (cells.length > 1) {
            // 检查第一行是否是表头
            if (isFirstRow) {
              isFirstRow = false
              // 如果第一行包含表头标识，标记为表格格式
              if (line.includes('测试用例编号') || line.includes('ID') || line.includes('用例ID') ||
                  line.includes('场景') || line.includes('步骤')) {
                isTableFormat = true
                continue  // 跳过表头行
              }
            }

            tableRows++
            if (tableRows >= 1) {
              isTableFormat = true
            }
          }
        }
      }

      if (isTableFormat && tableRows > 0) {
        return tableRows
      }

      // 尝试结构化文本格式
      let caseCount = 0
      for (const line of lines) {
        if (line.includes('测试用例') || line.includes('Test Case') || line.match(/^(\d+\.|测试场景)/)) {
          caseCount++
        }
      }

      return caseCount || 0
    },

    viewTaskDetail(task) {
      if (['pending', 'generating', 'reviewing'].includes(task.status)) {
        ElMessage.info(this.$t('generatedTestCases.generatingWait'))
        return
      }
      
      if (task.status === 'completed') {
        // 在新标签页打开任务详情
        const url = this.$router.resolve({
          name: 'TaskDetail',
          params: { taskId: task.task_id }
        }).href
        window.open(url, '_blank')
      }
    },

    async batchAdoptTask(task) {
      if (!confirm(this.$t('generatedTestCases.adoptConfirm', { title: task.title }))) {
        return
      }

      try {
        // 调用后端API批量采纳该任务的所有测试用例
        // await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch-adopt/`)
        await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch_adopt/`)
        ElMessage.success(this.$t('generatedTestCases.adoptSuccess'))
        this.loadTasks()
      } catch (error) {
        console.error(this.$t('generatedTestCases.adoptFailed'), error)
        ElMessage.error(this.$t('generatedTestCases.adoptFailed') + ': ' + (error.response?.data?.message || error.message))
      }
    },

    async batchDiscardTask(task) {
      if (!confirm(this.$t('generatedTestCases.discardConfirm', { title: task.title }))) {
        return
      }

      try {
        // 调用后端API批量删除该任务的所有测试用例
        // await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch-discard/`)
        await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch_discard/`)
        ElMessage.success(this.$t('generatedTestCases.discardSuccess'))
        this.loadTasks()
      } catch (error) {
        console.error(this.$t('generatedTestCases.discardFailed'), error)
        ElMessage.error(this.$t('generatedTestCases.discardFailed') + ': ' + (error.response?.data?.message || error.message))
      }
    },

    exportTestCasesMD(task) {
      try {
        // 使用相对路径或通过API模块构建URL，以确保与当前环境一致
        const exportUrl = `/api/requirement-analysis/testcase-generation/${task.task_id}/export_md/?filename=${encodeURIComponent(task.title || task.task_id)}`

        console.log('开始导出MD文件，URL:', exportUrl)

        // 使用fetch API代替XMLHttpRequest，以便更好地处理认证和跨域
        fetch(exportUrl, {
          method: 'GET',
          credentials: 'include', // 包含cookies等认证信息
        })
        .then(response => {
          if (response.ok) {
            return response.blob();
          } else {
            throw new Error(`导出失败: ${response.status} ${response.statusText}`);
          }
        })
        .then(blob => {
          console.log('获取到文件blob，大小:', blob.size)
          
          // 创建本地URL
          const urlObject = URL.createObjectURL(blob)
          
          // 创建下载链接
          const link = document.createElement('a')
          link.href = urlObject
          link.download = `${task.title || task.task_id}.md`
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          
          // 释放URL对象
          setTimeout(() => {
            URL.revokeObjectURL(urlObject)
          }, 100)

          console.log('文件下载已触发')
          ElMessage.success('MD格式测试用例导出成功！')
        })
        .catch(error => {
          console.error('导出失败:', error)
          ElMessage.error(`导出失败: ${error.message || '未知错误'}`)
        });
      } catch (error) {
        console.error('导出MD格式测试用例失败:', error)
        ElMessage.error(`导出失败: ${error.message || '未知错误'}`)
      }
    },


    formatDateTime(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    },

    // 获取项目列表
    async fetchProjects() {
      try {
        const response = await api.get('/projects/list/')
        this.projects = response.data.results || []
      } catch (error) {
        console.error(this.$t('generatedTestCases.fetchProjectsFailed'), error)
      }
    },

    // 获取所有版本列表
    async fetchAllVersions() {
      try {
        const response = await api.get('/versions/')
        this.allVersions = response.data.results || response.data || []
      } catch (error) {
        console.error(this.$t('generatedTestCases.fetchVersionsFailed'), error)
        this.allVersions = []
      }
    },

    // 获取项目版本列表
    async fetchProjectVersions(projectId) {
      if (!projectId) {
        this.projectVersions = []
        return
      }

      try {
        const response = await api.get(`/versions/projects/${projectId}/versions/`)
        this.projectVersions = response.data || []
      } catch (error) {
        console.error(this.$t('generatedTestCases.fetchProjectVersionsFailed'), error)
        this.projectVersions = []
      }
    },

    // 采纳测试用例
    async adoptTestCase(testCase) {
      this.currentAdoptingTask = testCase
      
      // 预填充表单数据
      this.adoptForm = {
        title: testCase.title,
        description: testCase.title, // 用标题作为描述的默认值
        project_id: null,
        priority: 'low', // 设置默认值为"低"
        test_type: 'functional',
        status: 'draft',
        preconditions: testCase.precondition || '',
        steps: testCase.test_steps || '',
        expected_result: testCase.expected_result || '',
        version_id: null // 改为单选
      }
      
      this.showAdoptModal = true
    },

    // 项目改变时的处理
    async onAdoptProjectChange() {
      if (this.adoptForm.project_id) {
        // 选择了项目，加载该项目的版本
        await this.fetchProjectVersions(this.adoptForm.project_id)
        
        // 检查当前选择的版本是否属于新项目，如果不属于则清空
        if (this.adoptForm.version_id) {
          const versionExists = this.projectVersions.some(v => v.id === this.adoptForm.version_id)
          if (!versionExists) {
            this.adoptForm.version_id = null
          }
        }
      } else {
        // 清空项目选择时，清空项目版本列表
        // 此时版本下拉会自动切换到显示所有版本（通过computed属性）
        this.projectVersions = []
        // 保持当前版本选择，因为可以从所有版本中选择
      }
    },

    // 确认采纳
    async confirmAdopt() {
      // 必填项验证
      if (!this.adoptForm.project_id) {
        alert(this.$t('generatedTestCases.selectProjectRequired'))
        return
      }

      if (!this.adoptForm.version_id) {
        alert(this.$t('generatedTestCases.selectVersionRequired'))
        return
      }

      if (!this.adoptForm.title.trim()) {
        alert(this.$t('generatedTestCases.enterCaseTitle'))
        return
      }

      if (!this.adoptForm.expected_result.trim()) {
        alert(this.$t('generatedTestCases.enterExpectedResult'))
        return
      }
      
      this.isAdopting = true
      
      try {
        // 准备提交的数据，将单选版本转换为数组格式（如果API需要）
        const submitData = {
          title: this.adoptForm.title,
          description: this.adoptForm.description,
          project_id: this.adoptForm.project_id,
          priority: this.adoptForm.priority || 'low',
          test_type: this.adoptForm.test_type,
          status: this.adoptForm.status,
          preconditions: this.adoptForm.preconditions,
          steps: this.adoptForm.steps,
          expected_result: this.adoptForm.expected_result,
          version_ids: this.adoptForm.version_id ? [this.adoptForm.version_id] : []
        }
        
        // 确保优先级有默认值
        if (!submitData.priority) {
          submitData.priority = 'low'
        }
        
        // 调用API创建测试用例
        await api.post('/testcases/', submitData)
        
        // 将AI生成的用例状态更新为"已采纳"
        try {
          await api.patch(`/requirement-analysis/test-cases/${this.currentAdoptingTask.id}/`, {
            status: 'adopted'
          })
        } catch (updateError) {
          console.warn(this.$t('generatedTestCases.updateStatusFailed'), updateError)
          // 即使状态更新失败，用例已成功导入，仍然提示成功
        }

        alert(this.$t('generatedTestCases.adoptModalSuccess'))
        this.closeAdoptModal()
        this.loadTestCases() // 重新加载列表

      } catch (error) {
        console.error(this.$t('generatedTestCases.adoptCaseFailed'), error)
        alert(this.$t('generatedTestCases.adoptCaseFailedRetry'))
      } finally{
        this.isAdopting = false
      }
    },

    // 弃用测试用例
    async discardTestCase(testCase) {
      if (!confirm(this.$t('generatedTestCases.discardCaseConfirm', { title: testCase.title }))) {
        return
      }

      try {
        // 将状态更新为"已弃用"
        await api.patch(`/requirement-analysis/test-cases/${testCase.id}/`, {
          status: 'discarded'
        })
        alert(this.$t('generatedTestCases.caseDiscarded'))
        this.loadTestCases() // 重新加载列表，已弃用的用例会被过滤掉
      } catch (error) {
        console.error(this.$t('generatedTestCases.discardCaseFailed'), error)
        alert(this.$t('generatedTestCases.discardCaseFailedRetry'))
      }
    },

    // 关闭采纳弹框
    closeAdoptModal() {
      this.showAdoptModal = false
      this.currentAdoptingTask = null
      this.projectVersions = []
    },

    // 关闭测试用例详情弹窗
    closeTestCaseDetail() {
      this.selectedTestCaseDetail = null
    },

    // 加载测试用例列表（别名，与loadTasks一致）
    loadTestCases() {
      this.loadTasks()
    },

    // 获取项目名称的辅助方法
    getProjectName(projectId) {
      const project = this.projects.find(p => p.id === projectId)
      return project ? project.name : ''
    },

    // 分页相关方法
    onPageSizeChange() {
      this.pagination.currentPage = 1
      this.loadTasks()
    },

    goToPage(page) {
      if (page >= 1 && page <= this.totalPages) {
        this.pagination.currentPage = page
        this.loadTasks()
      }
    },

    jumpToPage() {
      const page = parseInt(this.jumpPage)
      if (page >= 1 && page <= this.totalPages) {
        this.pagination.currentPage = page
        this.jumpPage = ''
        this.loadTasks()
      } else {
        alert(`请输入 1-${this.totalPages} 之间的页码`)
      }
    },

    getVisiblePages() {
      const current = this.pagination.currentPage
      const total = this.totalPages
      const pages = []

      if (total <= 7) {
        // 总页数少于等于7页，显示所有页码
        for (let i = 1; i <= total; i++) {
          pages.push(i)
        }
      } else {
        // 总页数大于7页，智能显示页码
        if (current <= 4) {
          // 当前页在前部
          for (let i = 1; i <= 5; i++) {
            pages.push(i)
          }
          pages.push('...')
          pages.push(total)
        } else if (current >= total - 3) {
          // 当前页在后部
          pages.push(1)
          pages.push('...')
          for (let i = total - 4; i <= total; i++) {
            pages.push(i)
          }
        } else {
          // 当前页在中部
          pages.push(1)
          pages.push('...')
          for (let i = current - 1; i <= current + 1; i++) {
            pages.push(i)
          }
          pages.push('...')
          pages.push(total)
        }
      }

      return pages
    }
  }
}
</script>

<style scoped>
.generated-testcase-list {
  padding: 16px 24px 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
  padding: 8px 0 12px;
}

.page-header h2 {
  font-size: 2.5rem;
  color: #4a249c;
  margin-bottom: 8px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  text-shadow: 0 2px 4px rgba(74, 36, 156, 0.15);
}

.page-header h2::before,
.page-header h2::after {
  content: '✨';
  font-size: 2rem;
}

.page-header p {
  color: #6d5d8f;
  font-size: 1.1rem;
  opacity: 0.9;
  margin: 0;
}

/* 筛选区域样式 */
.filters-section {
  margin-bottom: 20px;
}

.filter-card {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 16px;
  padding: 20px 24px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  border: 1px solid rgba(147, 112, 219, 0.15);
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}

/* 统计信息容器 */
.stats-container {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: nowrap;
}

.stats-divider {
  width: 1px;
  height: 32px;
  background: linear-gradient(180deg, transparent 0%, rgba(147, 112, 219, 0.3) 50%, transparent 100%);
  margin: 0 4px;
  flex-shrink: 0;
}

/* 统计项样式 - 左右结构 */
.stats-container .stat-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(147, 112, 219, 0.08);
  border-radius: 6px;
  min-width: auto;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.stats-container .stat-item:hover {
  background: rgba(147, 112, 219, 0.15);
}

.stats-container .stat-number {
  font-size: 1.2rem;
  font-weight: 700;
  color: #5a32a3;
  line-height: 1;
}

.stats-container .stat-label {
  font-size: 0.75rem;
  color: #6d5d8f;
  font-weight: 500;
  white-space: nowrap;
}

/* 批量删除按钮 - 内联样式 */
.batch-delete-btn-inline {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 6px rgba(238, 90, 90, 0.3);
  margin-left: 4px;
  flex-shrink: 0;
}

.batch-delete-btn-inline:hover:not(:disabled) {
  background: linear-gradient(135deg, #ee5a5a 0%, #dc3545 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(238, 90, 90, 0.4);
}

.batch-delete-btn-inline:disabled {
  background: linear-gradient(135deg, #fadbd8 0%, #f5c6c0 100%);
  color: #999;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 状态筛选标签样式 */
.status-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-tab {
  padding: 8px 16px;
  border: none;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(147, 112, 219, 0.1);
  color: #6d5d8f;
}

.status-tab:hover {
  background: rgba(147, 112, 219, 0.2);
  transform: translateY(-1px);
}

.status-tab.active {
  background: linear-gradient(135deg, #9370db 0%, #7b42f6 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(147, 112, 219, 0.3);
}

/* 不同状态的标签颜色 */
.status-tab.pending.active {
  background: linear-gradient(135deg, #f0ad4e 0%, #ec971f 100%);
  box-shadow: 0 4px 12px rgba(240, 173, 78, 0.3);
}

.status-tab.generating.active {
  background: linear-gradient(135deg, #5bc0de 0%, #46b8da 100%);
  box-shadow: 0 4px 12px rgba(91, 192, 222, 0.3);
}

.status-tab.reviewing.active {
  background: linear-gradient(135deg, #f0ad4e 0%, #ec971f 100%);
  box-shadow: 0 4px 12px rgba(240, 173, 78, 0.3);
}

.status-tab.revising.active {
  background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
  box-shadow: 0 4px 12px rgba(155, 89, 182, 0.3);
}

.status-tab.completed.active {
  background: linear-gradient(135deg, #5cb85c 0%, #4cae4c 100%);
  box-shadow: 0 4px 12px rgba(92, 184, 92, 0.3);
}

.status-tab.failed.active {
  background: linear-gradient(135deg, #d9534f 0%, #c9302c 100%);
  box-shadow: 0 4px 12px rgba(217, 83, 79, 0.3);
}



.batch-delete-btn:disabled {
  background: linear-gradient(135deg, #fadbd8 0%, #f5c6c0 100%);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 测试用例列表 */
.testcases-section {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.12);
  border: 1px solid rgba(147, 112, 219, 0.2);
  transition: all 0.3s ease;
  margin-top: 0;
}

.testcases-section:hover {
  box-shadow: 0 12px 48px rgba(147, 112, 219, 0.18);
}

.loading-state, .empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #6d5d8f;
}

.loading-state {
  font-size: 1.2rem;
  font-weight: 500;
}

.empty-icon {
  font-size: 5rem;
  margin-bottom: 24px;
  filter: drop-shadow(0 4px 8px rgba(147, 112, 219, 0.2));
}

.empty-state h3 {
  color: #4a249c;
  margin-bottom: 12px;
  font-size: 1.5rem;
  font-weight: 700;
}

.empty-state p {
  font-size: 1.1rem;
  line-height: 1.6;
  max-width: 600px;
  margin: 0 auto 24px;
}

.empty-state a {
  color: #7b42f6;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.3s ease;
  padding: 8px 16px;
  border-radius: 8px;
}

.empty-state a:hover {
  text-decoration: underline;
  background: rgba(147, 112, 219, 0.1);
  transform: translateY(-1px);
}

.testcases-table {
  border: 2px solid rgba(147, 112, 219, 0.1);
  border-radius: 16px;
  overflow: hidden;
  overflow-x: auto;
  display: block;
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  min-width: 1000px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  background: white;
}

.table-header {
  display: table;
  width: 100%;
  table-layout: fixed;
  background: linear-gradient(135deg, #f8f4ff 0%, #f0e8ff 100%);
  font-weight: 600;
  color: #4a249c;
  border-bottom: 2px solid rgba(147, 112, 219, 0.2);
}

.table-header-row {
  display: table-row;
}

.table-body {
  display: table;
  width: 100%;
  table-layout: fixed;
}

.table-body .table-row {
  display: table-row;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);
  transition: all 0.3s ease;
  min-height: 72px;
  height: auto;
}

.table-header .header-cell,
.table-body .body-cell {
  display: table-cell;
  vertical-align: middle;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.table-row:hover {
  background: rgba(243, 240, 250, 0.5);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
}

.table-row.selected {
  background: rgba(117, 70, 239, 0.15);
  border-left: 4px solid #7b42f6;
}

.table-row.selected:hover {
  background: rgba(117, 70, 239, 0.2);
}

/* 复选框样式 */
.checkbox-cell {
  width: 50px;
  min-width: 50px;
  max-width: 50px;
  text-align: center;
  vertical-align: middle;
  padding: 12px 16px;
  box-sizing: border-box;
  overflow: visible !important;
  text-overflow: clip !important;
  white-space: normal !important;
}

.checkbox-input {
  width: 16px;
  height: 16px;
  cursor: pointer;
  vertical-align: middle;
  margin: 0;
  position: relative;
  top: 1px;
}

.header-cell {
  padding: 16px 20px;
  border-right: 1px solid rgba(147, 112, 219, 0.1);
  word-wrap: break-word;
  word-break: break-word;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  text-align: center;
  color: #4a249c;
  text-shadow: 0 1px 2px rgba(74, 36, 156, 0.1);
}

.body-cell {
  padding: 16px 20px;
  border-right: 1px solid rgba(147, 112, 219, 0.1);
  word-wrap: break-word;
  word-break: break-word;
  font-size: 14px;
  color: #333;
  font-weight: 400;
}

.header-cell:last-child,
.body-cell:last-child {
  border-right: none;
}



/* 序号列 */
.serial-cell {
  width: 80px;
  text-align: center;
  font-weight: 600;
  flex-shrink: 0;
  color: #5a32a3;
}

.body-cell.serial-cell {
  text-align: center;
}

/* 任务ID列 */
.task-id-cell {
  width: 160px;
  text-align: center;
  flex-shrink: 0;
}

.body-cell.task-id-cell {
  text-align: left;
  font-size: 13px;
  font-weight: 500;
  color: #6d5d8f;
  font-family: 'Courier New', monospace;
}

/* 关联需求列 */
.requirement-name-cell {
  min-width: 350px;
  max-width: 450px;
  flex-grow: 1;
  text-align: center;
}

.body-cell.requirement-name-cell {
  text-align: left;
  padding-left: 16px;
}

.requirement-name {
  font-weight: 500;
  color: #4a249c;
  line-height: 1.4;
  display: block;
  white-space: normal;
  word-wrap: break-word;
}

/* 状态列 */
.status-cell {
  width: 140px;
  min-width: 140px;
  text-align: center;
  flex-shrink: 0;
  white-space: nowrap;
}

.body-cell.status-cell {
  text-align: center;
  overflow: visible !important;
  text-overflow: clip !important;
}

.status-tag {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(4px);
}

.status-tag.completed {
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.1) 0%, rgba(103, 194, 58, 0.05) 100%);
  color: #67c23a;
  border-color: rgba(103, 194, 58, 0.3);
  box-shadow: 0 4px 16px rgba(103, 194, 58, 0.2);
}

.status-tag.generating {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.1) 0%, rgba(64, 158, 255, 0.05) 100%);
  color: #409eff;
  border-color: rgba(64, 158, 255, 0.3);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.2);
  animation: pulse 2s infinite;
}

.status-tag.failed {
  background: linear-gradient(135deg, rgba(245, 108, 108, 0.1) 0%, rgba(245, 108, 108, 0.05) 100%);
  color: #f56c6c;
  border-color: rgba(245, 108, 108, 0.3);
  box-shadow: 0 4px 16px rgba(245, 108, 108, 0.2);
}

.status-tag.pending,
.status-tag.reviewing {
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.1) 0%, rgba(230, 162, 60, 0.05) 100%);
  color: #e6a23c;
  border-color: rgba(230, 162, 60, 0.3);
  box-shadow: 0 4px 16px rgba(230, 162, 60, 0.2);
}

.status-tag.revising {
  background: linear-gradient(135deg, rgba(155, 89, 182, 0.1) 0%, rgba(155, 89, 182, 0.05) 100%);
  color: #9b59b6;
  border-color: rgba(155, 89, 182, 0.3);
  box-shadow: 0 4px 16px rgba(155, 89, 182, 0.2);
}

.status-tag:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.15);
}

/* 状态图标样式 */
.status-icon {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
  position: relative;
  top: -1px;
}

.status-icon.icon-pending {
  background: #e6a23c;
  box-shadow: 0 0 0 2px rgba(230, 162, 60, 0.3);
}

.status-icon.icon-generating {
  background: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.3);
  animation: pulse-dot 2s infinite;
}

.status-icon.icon-reviewing {
  background: #e6a23c;
  box-shadow: 0 0 0 2px rgba(230, 162, 60, 0.3);
}

.status-icon.icon-revising {
  background: #9b59b6;
  box-shadow: 0 0 0 2px rgba(155, 89, 182, 0.3);
}

.status-icon.icon-completed {
  background: #67c23a;
  box-shadow: 0 0 0 2px rgba(103, 194, 58, 0.3);
}

.status-icon.icon-failed {
  background: #f56c6c;
  box-shadow: 0 0 0 2px rgba(245, 108, 108, 0.3);
}

@keyframes pulse-dot {
  0% {
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.3);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(64, 158, 255, 0);
  }
  100% {
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.3);
  }
}

@keyframes pulse {
  0% {
    box-shadow: 0 4px 16px rgba(64, 158, 255, 0.2);
  }
  50% {
    box-shadow: 0 6px 24px rgba(64, 158, 255, 0.4);
  }
  100% {
    box-shadow: 0 4px 16px rgba(64, 158, 255, 0.2);
  }
}

/* 用例条数列 */
.count-cell {
  width: 100px;
  text-align: center;
  flex-shrink: 0;
}

.body-cell.count-cell {
  text-align: center;
}

.count-badge {
  display: inline-block;
  padding: 6px 12px;
  background: linear-gradient(135deg, #f3f0fa 0%, #e9d8fd 100%);
  color: #5a32a3;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid rgba(147, 112, 219, 0.2);
  transition: all 0.3s ease;
}

.count-badge:hover {
  background: linear-gradient(135deg, #e9d8fd 0%, #d6bcfa 100%);
  transform: scale(1.1);
}

/* 生成时间列 */
.time-cell {
  width: 180px;
  text-align: center;
  flex-shrink: 0;
  white-space: nowrap;
}

.body-cell.time-cell {
  text-align: center;
  font-size: 13px;
  color: #6d5d8f;
  font-family: 'Courier New', monospace;
}

/* 操作列 */
.action-cell {
  width: 220px;
  min-width: 220px;
  text-align: center;
  flex-shrink: 0;
  white-space: nowrap;
}

.table-body .body-cell.action-cell {
  text-align: center !important;
  vertical-align: middle;
  padding: 12px 16px !important;
}

.action-buttons {
  display: flex;
  flex-direction: row;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  width: auto;
  max-width: 100%;
  margin: 0 auto;
  padding: 0;
  box-sizing: border-box;
}

.view-detail-btn,
.adopt-btn,
.discard-btn,
.export-btn,
.export-md-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 90px;
  height: 36px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.view-detail-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: white;
}

.view-detail-btn:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(117, 70, 239, 0.3);
}

.adopt-btn {
  background: linear-gradient(135deg, #67c23a 0%, #529b2e 100%);
  color: white;
}

.adopt-btn:hover {
  background: linear-gradient(135deg, #529b2e 0%, #3d7a22 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(103, 194, 58, 0.3);
}

.discard-btn {
  background: linear-gradient(135deg, #f56c6c 0%, #e74c3c 100%);
  color: white;
}

.discard-btn:hover {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(245, 108, 108, 0.3);
}

.export-btn {
  background: linear-gradient(135deg, #409eff 0%, #2979ff 100%);
  color: white;
}

.export-btn:hover {
  background: linear-gradient(135deg, #2979ff 0%, #1c66e0 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3);
}

.export-md-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 8px rgba(123, 66, 246, 0.3);
}

.export-md-btn:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(123, 66, 246, 0.4);
}

/* 分页组件 - 现代卡片风格 */
.pagination-section {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 24px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f6ff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  border: 1px solid rgba(147, 112, 219, 0.15);
}

.pagination-simple {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-btn {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border: 1px solid rgba(147, 112, 219, 0.2);
  border-radius: 10px;
  cursor: pointer;
  font-size: 16px;
  color: #5a32a3;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.1);
}

.page-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border-color: #7b42f6;
  color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(123, 66, 246, 0.3);
}

.page-btn:disabled {
  background: #f5f5f5;
  color: #ccc;
  cursor: not-allowed;
  border-color: #e0e0e0;
  box-shadow: none;
}

.page-current {
  font-size: 15px;
  color: #4a249c;
  font-weight: 600;
  min-width: 60px;
  text-align: center;
  padding: 8px 16px;
  background: rgba(147, 112, 219, 0.08);
  border-radius: 8px;
}

.requirement-name {
  font-weight: 500;
  color: #2c3e50;
  line-height: 1.4;
  word-wrap: break-word;
  word-break: break-word;
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.requirement-id {
  color: #666;
  font-size: 0.8rem;
  margin-left: 5px;
}

.priority-tag,
.status-tag {
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: bold;
  display: inline-block;
  min-width: 45px;
  text-align: center;
}

.priority-tag.p0 {
  background: #ffebee;
  color: #d32f2f;
}

.priority-tag.p1 {
  background: #fff3e0;
  color: #f57c00;
}

.priority-tag.p2 {
  background: #e3f2fd;
  color: #1976d2;
}

.priority-tag.p3 {
  background: #e8f5e8;
  color: #388e3c;
}

.status-tag.pending {
  background: #fff3cd;
  color: #856404;
}

.status-tag.generating {
  background: #e3f2fd;
  color: #1976d2;
}

.status-tag.reviewing {
  background: #e3f2fd;
  color: #1976d2;
}

.status-tag.revising {
  background: #e3f2fd;
  color: #1976d2;
}

.status-tag.completed {
  background: #d4edda;
  color: #155724;
}

.status-tag.failed {
  background: #f8d7da;
  color: #721c24;
}

.action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  width: auto;
  max-width: 100%;
  margin: 0 auto;
}

.adopted-label {
  color: #27ae60;
  font-weight: bold;
  font-size: 0.8rem;
  padding: 6px 12px;
  background: #e8f5e8;
  border-radius: 4px;
  border: 1px solid #27ae60;
}

/* 分页组件样式 - 已整合到上方现代卡片风格 */



/* 测试用例详情弹窗 - 现代风格 */
.testcase-detail-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(74, 36, 156, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-content {
  background: linear-gradient(135deg, #ffffff 0%, #f8f6ff 100%);
  border-radius: 20px;
  padding: 0;
  max-width: 800px;
  width: 90%;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(74, 36, 156, 0.3);
  border: 1px solid rgba(147, 112, 219, 0.2);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    transform: translateY(30px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  background: linear-gradient(135deg, #f8f4ff 0%, #f0e8ff 100%);
  border-bottom: 1px solid rgba(147, 112, 219, 0.15);
  position: sticky;
  top: 0;
  z-index: 10;
}

.modal-header h3 {
  margin: 0;
  color: #4a249c;
  font-size: 1.4rem;
  font-weight: 700;
}

.close-btn {
  background: rgba(147, 112, 219, 0.1);
  border: none;
  font-size: 1.8rem;
  cursor: pointer;
  color: #6d5d8f;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.close-btn:hover {
  background: rgba(147, 112, 219, 0.2);
  color: #4a249c;
  transform: rotate(90deg);
}

.modal-body {
  padding: 32px;
}

.detail-item {
  margin-bottom: 24px;
  padding: 16px 20px;
  background: rgba(147, 112, 219, 0.03);
  border-radius: 12px;
  border-left: 4px solid #9370db;
  transition: all 0.3s ease;
}

.detail-item:hover {
  background: rgba(147, 112, 219, 0.06);
  transform: translateX(4px);
}

.detail-item label {
  font-weight: 600;
  color: #4a249c;
  display: block;
  margin-bottom: 10px;
  font-size: 0.95rem;
}

.detail-item span,
.detail-item p {
  color: #555;
  line-height: 1.7;
  margin: 0;
}

.test-steps {
  white-space: pre-line;
  line-height: 1.8;
  background: linear-gradient(135deg, #f8f9fa 0%, #f0f4ff 100%);
  padding: 20px;
  border-radius: 12px;
  border-left: 4px solid #7b42f6;
  color: #444;
}

/* 采纳用例弹框样式 - 现代风格 */
.large-modal {
  max-width: 900px;
}

.adopt-form {
  max-width: 100%;
}

.form-row {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}

.form-row:last-child {
  margin-bottom: 0;
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 600;
  color: #4a249c;
  margin-bottom: 10px;
  font-size: 0.95rem;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 12px 16px;
  border: 1px solid rgba(147, 112, 219, 0.3);
  border-radius: 10px;
  font-size: 0.95rem;
  background: white;
  transition: all 0.3s ease;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #7b42f6;
  box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.15);
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.form-hint {
  color: #888;
  font-size: 0.85rem;
  margin-top: 6px;
}

.required {
  color: #e74c3c;
  font-weight: bold;
}

.form-actions {
  display: flex;
  gap: 16px;
  justify-content: flex-end;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(147, 112, 219, 0.15);
}

.confirm-btn {
  background: linear-gradient(135deg, #67c23a 0%, #529b2e 100%);
  color: white;
  border: none;
  padding: 12px 28px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.3);
}

.confirm-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #529b2e 0%, #3d7a22 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(103, 194, 58, 0.4);
}

.confirm-btn:disabled {
  background: linear-gradient(135deg, #bdc3c7 0%, #95a5a6 100%);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.cancel-btn {
  background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
  color: white;
  border: none;
  padding: 12px 28px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(149, 165, 166, 0.3);
}

.cancel-btn:hover {
  background: linear-gradient(135deg, #7f8c8d 0%, #6c7a7b 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(149, 165, 166, 0.4);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .action-cell {
    width: 200px;
    min-width: 200px;
  }

  .action-buttons {
    flex-direction: row;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  .view-detail-btn,
  .adopt-btn,
  .discard-btn,
  .export-btn,
  .export-md-btn {
    padding: 6px 12px;
    font-size: 12px;
    min-width: 80px;
    height: 32px;
  }
}

@media (max-width: 992px) {
  .action-cell {
    width: 180px;
    min-width: 180px;
  }

  .action-buttons {
    gap: 6px;
  }

  .view-detail-btn,
  .adopt-btn,
  .discard-btn,
  .export-btn,
  .export-md-btn {
    padding: 5px 10px;
    font-size: 11px;
    min-width: 70px;
    height: 30px;
  }
}

@media (max-width: 768px) {
  .generated-testcase-list {
    padding: 12px 16px 20px;
  }

  .page-header h2 {
    font-size: 1.8rem;
  }

  .filter-card {
    flex-direction: column;
    align-items: stretch;
    padding: 16px 20px;
  }

  .stats-container {
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
  }

  .status-tabs {
    justify-content: center;
  }

  .testcases-section {
    padding: 16px;
  }

  .testcases-table {
    min-width: auto;
  }

  .action-cell {
    width: 160px;
    min-width: 160px;
  }

  .action-buttons {
    flex-direction: column;
    gap: 6px;
    align-items: center;
  }

  .view-detail-btn,
  .adopt-btn,
  .discard-btn,
  .export-btn,
  .export-md-btn {
    width: 100%;
    max-width: 120px;
  }

  .form-row {
    flex-direction: column;
    gap: 16px;
  }

  .large-modal {
    max-width: 95%;
  }

  .modal-content {
    width: 95%;
    max-height: 90vh;
  }

  .modal-header {
    padding: 16px 20px;
  }

  .modal-header h3 {
    font-size: 1.2rem;
  }

  .modal-body {
    padding: 20px;
  }

  .pagination-section {
    padding: 12px 16px;
  }

  .pagination-simple {
    gap: 12px;
  }

  .page-btn {
    width: 36px;
    height: 36px;
    font-size: 14px;
  }

  .page-current {
    font-size: 14px;
    padding: 6px 12px;
  }
}

@media (max-width: 480px) {
  .page-header h2 {
    font-size: 1.5rem;
  }

  .page-header h2::before,
  .page-header h2::after {
    font-size: 1.2rem;
  }

  .status-tab {
    padding: 6px 12px;
    font-size: 0.8rem;
  }

  .stats-container .stat-item {
    padding: 6px 10px;
  }

  .stats-container .stat-number {
    font-size: 1rem;
  }

  .stats-container .stat-label {
    font-size: 0.7rem;
  }
}
</style>
