
<template>
  <div class="generated-testcase-list">
    <div class="page-header">
      <h2>AI生成用例记录</h2>
    </div>

    <!-- 统计信息 -->
    <div class="filters-stats-section" v-if="allStats.total > 0">
      <div class="filters-stats-card">
        <div class="stats-area">
          <div class="stat-item">
            <span class="stat-number">{{ allStats.total }}</span>
            <span class="stat-label">任务总数</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ allStats.completed }}</span>
            <span class="stat-label">已完成</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ allStats.running }}</span>
            <span class="stat-label">进行中</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ allStats.failed }}</span>
            <span class="stat-label">失败</span>
          </div>
        </div>
      </div>
    </div>

    <!-- AI任务列表 -->
    <div class="testcases-section">
      <div v-if="isLoading" class="loading-state">
        <p>🔄 正在加载任务列表...</p>
      </div>

      <div v-else-if="tasks.length === 0" class="empty-state">
        <div class="empty-icon">📝</div>
        <h3>暂无生成任务</h3>
        <p>还没有AI生成用例任务，去<router-link to="/ai-generation/requirement-analysis">AI用例生成</router-link>页面创建一个任务吧！</p>
      </div>

      <div v-else class="testcases-table">
        <div class="table-header">
          <div class="table-header-row">
            <div class="header-cell serial-cell">序号</div>
            <div class="header-cell task-id-cell">任务ID</div>
            <div class="header-cell requirement-name-cell">关联需求</div>
            <div class="header-cell status-cell">状态</div>
            <div class="header-cell count-cell">条数</div>
            <div class="header-cell time-cell">生成时间</div>
            <div class="header-cell action-cell">操作</div>
          </div>
        </div>
        
        <div class="table-body">
          <div 
            v-for="(task, index) in tasks" 
            :key="task.task_id"
            class="table-row">
            <div class="body-cell serial-cell">{{ getSerialNumber(index) }}</div>
            <div class="body-cell task-id-cell">{{ task.task_id }}</div>
            <div class="body-cell requirement-name-cell">
              <span class="requirement-name">{{ task.title }}</span>
            </div>
            <div class="body-cell status-cell">
              <span class="status-tag" :class="task.status">
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
                  class="view-detail-btn" 
                  @click="viewTaskDetail(task)">
                  详情
                </button>
                <button 
                  v-if="task.status === 'completed'"
                  class="adopt-btn" 
                  @click="batchAdoptTask(task)">
                  采纳
                </button>
                <button 
                  v-if="task.status === 'completed'"
                  class="discard-btn" 
                  @click="batchDiscardTask(task)">
                  弃用
                </button>
                <button 
                  v-if="task.status === 'completed'"
                  class="export-btn" 
                  @click="exportTestCasesMD(task)">
                  导出MD
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页组件 -->
    <div v-if="tasks.length > 0" class="pagination-section">
      <div class="pagination-info">
        {{ paginationInfo }}
      </div>
      
      <div class="pagination-controls">
        <!-- 每页条数选择 -->
        <div class="page-size-selector">
          <label>每页显示：</label>
          <select v-model="pagination.pageSize" @change="onPageSizeChange">
            <option v-for="size in pagination.pageSizeOptions" :key="size" :value="size">
              {{ size }} 条
            </option>
          </select>
        </div>
        
        <!-- 分页按钮 -->
        <div class="pagination-buttons">
          <button 
            class="page-btn" 
            :disabled="pagination.currentPage <= 1"
            @click="goToPage(pagination.currentPage - 1)">
            上一页
          </button>
          
          <!-- 页码显示 -->
          <div class="page-numbers">
            <span v-for="page in getVisiblePages()" :key="page" class="page-number">
              <button 
                v-if="page !== '...'"
                class="page-btn"
                :class="{ active: page === pagination.currentPage }"
                @click="goToPage(page)">
                {{ page }}
              </button>
              <span v-else class="ellipsis">...</span>
            </span>
          </div>
          
          <button 
            class="page-btn" 
            :disabled="pagination.currentPage >= totalPages"
            @click="goToPage(pagination.currentPage + 1)">
            下一页
          </button>
        </div>
        
        <!-- 页码跳转 -->
        <div class="page-jumper">
          <label>跳转到：</label>
          <input 
            v-model="jumpPage" 
            type="number" 
            :min="1" 
            :max="totalPages"
            @keyup.enter="jumpToPage"
            placeholder="页码">
          <button class="jump-btn" @click="jumpToPage">跳转</button>
        </div>
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
            <label>用例编号:</label>
            <span>{{ selectedTestCaseDetail.case_id }}</span>
          </div>
          <div class="detail-item">
            <label>关联需求:</label>
            <span>{{ selectedTestCaseDetail.requirement_name }} ({{ selectedTestCaseDetail.requirement_id_display }})</span>
          </div>
          <div class="detail-item">
            <label>优先级:</label>
            <span class="priority-tag" :class="selectedTestCaseDetail.priority.toLowerCase()">
              {{ selectedTestCaseDetail.priority_display }}
            </span>
          </div>
          <div class="detail-item">
            <label>状态:</label>
            <span class="status-tag" :class="selectedTestCaseDetail.status">
              {{ selectedTestCaseDetail.status_display }}
            </span>
          </div>
          <div class="detail-item">
            <label>前置条件:</label>
            <p>{{ selectedTestCaseDetail.precondition }}</p>
          </div>
          <div class="detail-item">
            <label>测试步骤:</label>
            <p class="test-steps" v-html="selectedTestCaseDetail.test_steps"></p>
          </div>
          <div class="detail-item">
            <label>预期结果:</label>
            <p v-html="selectedTestCaseDetail.expected_result"></p>
          </div>
          <div class="detail-item" v-if="selectedTestCaseDetail.review_comments">
            <label>评审意见:</label>
            <p>{{ selectedTestCaseDetail.review_comments }}</p>
          </div>
          <div class="detail-item">
            <label>生成AI:</label>
            <span>{{ selectedTestCaseDetail.generated_by_ai }}</span>
          </div>
          <div class="detail-item" v-if="selectedTestCaseDetail.reviewed_by_ai">
            <label>评审AI:</label>
            <span>{{ selectedTestCaseDetail.reviewed_by_ai }}</span>
          </div>
          <div class="detail-item">
            <label>生成时间:</label>
            <span>{{ formatDateTime(selectedTestCaseDetail.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 采纳用例编辑弹框 -->
    <div v-if="showAdoptModal" class="testcase-detail-modal" @click="closeAdoptModal">
      <div class="modal-content large-modal" @click.stop>
        <div class="modal-header">
          <h3>采纳测试用例</h3>
          <button class="close-btn" @click="closeAdoptModal">×</button>
        </div>
        <div class="modal-body">
          <form class="adopt-form">
            <div class="form-row">
              <div class="form-group">
                <label>用例标题:</label>
                <input v-model="adoptForm.title" type="text" placeholder="请输入用例标题" />
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>用例描述:</label>
                <textarea v-model="adoptForm.description" rows="3" placeholder="请输入用例描述"></textarea>
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>归属项目: <span class="required">*</span></label>
                <select v-model="adoptForm.project_id" @change="onAdoptProjectChange">
                  <option value="">请选择项目</option>
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.name }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label>关联版本: <span class="required">*</span></label>
                <select v-model="adoptForm.version_id">
                  <option value="">请选择版本</option>
                  <option v-for="version in availableVersions" :key="version.id" :value="version.id">
                    {{ version.name }}{{ version.is_baseline ? ' (基线)' : '' }}
                  </option>
                </select>
                <small class="form-hint">
                  {{ adoptForm.project_id ? 
                      `显示项目"${getProjectName(adoptForm.project_id)}"的版本` : 
                      '显示所有版本，选择项目后将过滤为项目版本' }}
                </small>
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>优先级:</label>
                <select v-model="adoptForm.priority">
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                  <option value="critical">紧急</option>
                </select>
              </div>
              <div class="form-group">
                <label>测试类型:</label>
                <select v-model="adoptForm.test_type">
                  <option value="functional">功能测试</option>
                  <option value="integration">集成测试</option>
                  <option value="api">API测试</option>
                  <option value="ui">UI测试</option>
                  <option value="performance">性能测试</option>
                  <option value="security">安全测试</option>
                </select>
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>状态:</label>
                <select v-model="adoptForm.status">
                  <option value="draft">草稿</option>
                  <option value="active">激活</option>
                </select>
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>前置条件:</label>
                <textarea v-model="adoptForm.preconditions" rows="3" placeholder="请输入前置条件"></textarea>
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>操作步骤:</label>
                <textarea v-model="adoptForm.steps" rows="6" placeholder="请输入详细的操作步骤"></textarea>
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>预期结果:</label>
                <textarea v-model="adoptForm.expected_result" rows="3" placeholder="请输入预期结果"></textarea>
              </div>
            </div>
            
            <div class="form-actions">
              <button type="button" class="confirm-btn" @click="confirmAdopt" :disabled="isAdopting">
                {{ isAdopting ? '正在采纳...' : '确认采纳' }}
              </button>
              <button type="button" class="cancel-btn" @click="closeAdoptModal">取消</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'GeneratedTestCaseList',
  data() {
    return {
      isLoading: false,
      tasks: [], // 改为任务列表
      selectedStatus: '',
      selectedTaskDetail: null,
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
      return `显示 ${start}-${end} 条，共 ${this.pagination.total} 条`
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
        params.append('page', this.pagination.currentPage)
        params.append('page_size', this.pagination.pageSize)
        
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
        console.error('加载任务列表失败:', error)
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
        ElMessage.warning('请先选择要删除的任务')
        return
      }

      try {
        await ElMessageBox.confirm(
          `确定要删除选中的 ${this.selectedTasks.length} 个任务吗？此操作不可恢复。`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
      } catch {
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
          ElMessage.success(`成功删除 ${successCount} 个任务${failCount > 0 ? `，${failCount} 个失败` : ''}`)
        } else {
          ElMessage.error('删除失败')
        }

        // 清空选择并重新加载列表
        this.selectedTasks = []
        this.loadTasks()

      } catch (error) {
        console.error('批量删除失败:', error)
        ElMessage.error('批量删除失败: ' + (error.message || '未知错误'))
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
        console.error('获取统计数据失败:', error)
        // 如果获取统计失败，使用分页信息的总数作为备选
        this.allStats.total = this.pagination.total || 0
        this.allStats.completed = 0
        this.allStats.running = 0
        this.allStats.failed = 0
      }
    },

    getStatusText(status) {
      const statusMap = {
        'pending': '需求分析中',
        'generating': '生成中', 
        'reviewing': '用例评审中',
        'revising': '改进中',
        'completed': '已完成',
        'failed': '失败'
      }
      return statusMap[status] || status
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
        ElMessage.info('用例正在生成中，请稍后查看！')
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
      try {
        await ElMessageBox.confirm(
          `确定要一键采纳任务"${task.title}"的所有测试用例吗？`,
          '确认采纳',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'success'
          }
        )
      } catch {
        return
      }

      try {
        // 调用后端API批量采纳该任务的所有测试用例
        await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch-adopt/`)
        ElMessage.success('一键采纳成功！所有测试用例已导入到测试用例列表')
        this.loadTasks()
      } catch (error) {
        console.error('一键采纳失败:', error)
        ElMessage.error('一键采纳失败: ' + (error.response?.data?.message || error.message))
      }
    },

    async batchDiscardTask(task) {
      try {
        await ElMessageBox.confirm(
          `确定要一键弃用任务"${task.title}"的所有测试用例吗？此操作不可恢复。`,
          '确认弃用',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
      } catch {
        return
      }

      try {
        // 调用后端API批量删除该任务的所有测试用例
        await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch-discard/`)
        ElMessage.success('一键弃用成功！该任务的所有测试用例已删除')
        this.loadTasks()
      } catch (error) {
        console.error('一键弃用失败:', error)
        ElMessage.error('一键弃用失败: ' + (error.response?.data?.message || error.message))
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
        console.error('获取项目列表失败:', error)
      }
    },

    // 获取所有版本列表
    async fetchAllVersions() {
      try {
        const response = await api.get('/versions/')
        this.allVersions = response.data.results || response.data || []
      } catch (error) {
        console.error('获取所有版本列表失败:', error)
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
        console.error('获取项目版本失败:', error)
        this.projectVersions = []
      }
    },

    // 采纳测试用例
    async adoptTestCase(testCase) {
      this.currentAdoptingTestCase = testCase
      
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
        ElMessage.warning('请选择归属项目')
        return
      }

      if (!this.adoptForm.version_id) {
        ElMessage.warning('请选择关联版本')
        return
      }

      if (!this.adoptForm.title.trim()) {
        ElMessage.warning('请输入用例标题')
        return
      }

      if (!this.adoptForm.expected_result.trim()) {
        ElMessage.warning('请输入预期结果')
        return
      }

      this.isAdopting = true

      try {
        // 准备提交的数据，将单选版本转换为数组格式（如果API需要）
        const submitData = { ...this.adoptForm }

        // 确保优先级有默认值
        if (!submitData.priority) {
          submitData.priority = 'low'
        }

        if (submitData.version_id) {
          submitData.version_ids = [submitData.version_id]
        }
        delete submitData.version_id

        // 调用API创建测试用例
        await api.post('/testcases/', submitData)

        // 将AI生成的用例状态更新为"已采纳"
        try {
          await api.patch(`/requirement-analysis/test-cases/${this.currentAdoptingTestCase.id}/`, {
            status: 'adopted'
          })
        } catch (updateError) {
          console.warn('更新AI用例状态失败:', updateError)
          // 即使状态更新失败，用例已成功导入，仍然提示成功
        }

        ElMessage.success('用例采纳成功！已导入到测试用例列表')
        this.closeAdoptModal()
        this.loadTestCases() // 重新加载列表

      } catch (error) {
        console.error('采纳用例失败:', error)
        ElMessage.error('采纳用例失败，请重试')
      } finally {
        this.isAdopting = false
      }
    },

    // 弃用测试用例
    async discardTestCase(testCase) {
      try {
        await ElMessageBox.confirm(
          `确定要弃用测试用例"${testCase.title}"吗？此操作不可恢复。`,
          '确认弃用',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
      } catch {
        return
      }

      try {
        // 将状态更新为"已弃用"
        await api.patch(`/requirement-analysis/test-cases/${testCase.id}/`, {
          status: 'discarded'
        })
        ElMessage.success('用例已弃用')
        this.loadTestCases() // 重新加载列表，已弃用的用例会被过滤掉
      } catch (error) {
        console.error('弃用用例失败:', error)
        ElMessage.error('弃用用例失败，请重试')
      }
    },

    // 关闭采纳弹框
    closeAdoptModal() {
      this.showAdoptModal = false
      this.currentAdoptingTestCase = null
      this.projectVersions = []
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
        ElMessage.warning(`请输入 1-${this.totalPages} 之间的页码`)
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
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 32px;
  padding: 20px 0;
}

.page-header h2 {
  font-size: 2rem;
  color: #4a249c;
  margin-bottom: 8px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-shadow: 0 1px 2px rgba(74, 36, 156, 0.1);
}

.page-header h2::before,
.page-header h2::after {
  content: '✨';
  font-size: 1.5rem;
}

.page-header p {
  color: #6d5d8f;
  font-size: 1.1rem;
  opacity: 0.9;
  margin: 0;
}

.filter-select {
  padding: 10px 16px;
  border: 2px solid rgba(147, 112, 219, 0.2);
  border-radius: 12px;
  font-size: 1rem;
  background: linear-gradient(145deg, #ffffff 0%, #f8f6ff 100%);
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 160px;
}

.filter-select:focus {
  outline: none;
  border-color: #9370db;
  box-shadow: 0 0 0 3px rgba(147, 112, 219, 0.25);
  background: rgba(243, 240, 250, 0.8);
}



.batch-delete-btn:disabled {
  background: linear-gradient(135deg, #fadbd8 0%, #f5c6c0 100%);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 筛选和统计信息 */
.filters-stats-section {
  margin-bottom: 24px;
}

.filters-stats-card {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.12);
  border: 1px solid rgba(147, 112, 219, 0.2);
  display: flex;
  gap: 32px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  transition: all 0.3s ease;
}

.filters-stats-card:hover {
  box-shadow: 0 12px 48px rgba(147, 112, 219, 0.18);
  transform: translateY(-2px);
}



.stats-area {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  align-items: center;
  width: 100%;
}

.stat-item {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 16px;
  border: 1px solid rgba(147, 112, 219, 0.1);
  transition: all 0.3s ease;
  min-width: 100px;
}

.stat-item:hover {
  background: rgba(243, 240, 250, 0.9);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.15);
}

.stat-number {
  font-size: 1.8rem;
  font-weight: 700;
  color: #5a32a3;
  text-shadow: 0 1px 2px rgba(90, 50, 163, 0.1);
}

.stat-label {
  color: #6d5d8f;
  font-size: 0.9rem;
  font-weight: 500;
  opacity: 0.9;
}

/* 测试用例列表 */
.testcases-section {
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 20px;
  padding: 32px;
  box-shadow: 0 8px 32px rgba(147, 112, 219, 0.12);
  border: 1px solid rgba(147, 112, 219, 0.2);
  transition: all 0.3s ease;
}

.testcases-section:hover {
  box-shadow: 0 12px 48px rgba(147, 112, 219, 0.18);
  transform: translateY(-2px);
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

.header-cell {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
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
  display: flex;
  align-items: center;
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



.serial-cell {
  justify-content: center;
  width: 80px;
  font-weight: 600;
  flex-shrink: 0;
  color: #5a32a3;
}

.body-cell.serial-cell {
  justify-content: center;
  align-items: center;
}

/* 任务ID列 */
.task-id-cell {
  width: 160px;
  flex-shrink: 0;
}

.body-cell.task-id-cell {
  justify-content: flex-start;
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
}

.body-cell.requirement-name-cell {
  justify-content: flex-start;
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
  width: 120px;
  flex-shrink: 0;
  white-space: nowrap;
}

.body-cell.status-cell {
  justify-content: center;
}

.status-tag {
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
}

.status-tag.completed {
  background: rgba(103, 194, 58, 0.1);
  color: #67c23a;
  border: 1px solid rgba(103, 194, 58, 0.2);
}

.status-tag.generating {
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
  border: 1px solid rgba(64, 158, 255, 0.2);
}

.status-tag.failed {
  background: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
  border: 1px solid rgba(245, 108, 108, 0.2);
}

.status-tag.pending,
.status-tag.reviewing {
  background: rgba(230, 162, 60, 0.1);
  color: #e6a23c;
  border: 1px solid rgba(230, 162, 60, 0.2);
}

.status-tag:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* 用例条数列 */
.count-cell {
  justify-content: center;
  width: 90px;
  flex-shrink: 0;
}

.count-badge {
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
  flex-shrink: 0;
  white-space: nowrap;
}

.body-cell.time-cell {
  justify-content: center;
  font-size: 13px;
  color: #6d5d8f;
  font-family: 'Courier New', monospace;
}

/* 操作列 */
.action-cell {
  min-width: 450px;
  flex-shrink: 0;
  white-space: nowrap;
}

.body-cell.action-cell {
  justify-content: center;
}

.action-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.view-detail-btn,
.adopt-btn,
.discard-btn,
.export-btn {
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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

/* 分页组件 */
.pagination-section {
  margin-top: 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.1);
  border: 1px solid rgba(147, 112, 219, 0.1);
}

.pagination-info {
  font-size: 14px;
  color: #5a32a3;
  font-weight: 400;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-size-selector label {
  font-size: 14px;
  color: #5a32a3;
  font-weight: 400;
}

.page-size-selector select {
  padding: 6px 10px;
  border: 2px solid rgba(147, 112, 219, 0.2);
  border-radius: 8px;
  font-size: 14px;
  background: linear-gradient(145deg, #ffffff 0%, #f8f6ff 100%);
  color: #5a32a3;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.1);
  min-width: 60px;
}

.page-size-selector select:focus {
  outline: none;
  border-color: #9370db;
  box-shadow: 0 0 0 3px rgba(147, 112, 219, 0.25);
  transform: translateY(-1px);
}

.pagination-buttons {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-btn {
  background: transparent;
  color: #5a32a3;
  border: 1px solid rgba(147, 112, 219, 0.2);
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 400;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.page-btn:hover:not(:disabled) {
  background: rgba(147, 112, 219, 0.1);
  transform: translateY(-1px);
  border-color: #9370db;
}

.page-btn:disabled {
  background: transparent;
  color: rgba(147, 112, 219, 0.4);
  border-color: rgba(147, 112, 219, 0.1);
  cursor: not-allowed;
  transform: none;
}

.page-btn.active {
  background: transparent;
  color: #5a32a3;
  font-weight: 500;
  border-color: #9370db;
}

.page-numbers {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-number {
  display: flex;
  align-items: center;
}

.ellipsis {
  padding: 6px 8px;
  font-size: 14px;
  color: #5a32a3;
  font-weight: 400;
}

.page-jumper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-jumper label {
  font-size: 14px;
  color: #5a32a3;
  font-weight: 400;
  white-space: nowrap;
}

.page-jumper input {
  padding: 6px 12px;
  border: 2px solid rgba(147, 112, 219, 0.2);
  border-radius: 6px;
  font-size: 14px;
  width: 120px;
  height: 32px;
  text-align: center;
  background: linear-gradient(145deg, #ffffff 0%, #f8f6ff 100%);
  color: #5a32a3;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.page-jumper input:focus {
  outline: none;
  border-color: #9370db;
  box-shadow: 0 0 0 3px rgba(147, 112, 219, 0.25);
}

.jump-btn {
  background: transparent;
  color: #5a32a3;
  border: 1px solid rgba(147, 112, 219, 0.2);
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 400;
  transition: all 0.3s ease;
  white-space: nowrap;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.jump-btn:hover {
  background: rgba(147, 112, 219, 0.1);
  border-color: #9370db;
  transform: translateY(-1px);
}

.requirement-name {
  font-weight: 500;
  color: #2c3e50;
  line-height: 1.4;
  word-wrap: break-word;
  word-break: break-word;
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 1;
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

.view-detail-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 2px 4px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.65rem;
  transition: background 0.3s ease;
  white-space: nowrap;
}

.view-detail-btn:hover {
  background: #2980b9;
}

.adopt-btn {
  background: #27ae60;
  color: white;
  border: none;
  padding: 2px 4px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.65rem;
  transition: background 0.3s ease;
  white-space: nowrap;
}

.adopt-btn:hover {
  background: #229954;
}

.discard-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 2px 4px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.65rem;
  transition: background 0.3s ease;
  white-space: nowrap;
}

.discard-btn:hover {
  background: #c0392b;
}

.export-btn {
  background: #9b59b6;
  color: white;
  border: none;
  padding: 2px 4px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.65rem;
  transition: background 0.3s ease;
  white-space: nowrap;
}

.export-btn:hover {
  background: #8e44ad;
}


.action-buttons {
  display: flex;
  gap: 5px;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-width: 300px;
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

/* 分页组件样式 */
.pagination-section {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.pagination-info {
  color: #666;
  font-size: 0.65rem;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-size-selector label {
  color: #666;
  font-size: 0.65rem;
}

.page-size-selector select {
  padding: 2px 4px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.65rem;
}

.pagination-buttons {
  display: flex;
  align-items: center;
  gap: 4px;
}



/* 测试用例详情弹窗 */
.testcase-detail-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 0;
  max-width: 800px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  color: #2c3e50;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 30px;
}

.detail-item {
  margin-bottom: 20px;
}

.detail-item label {
  font-weight: bold;
  color: #2c3e50;
  display: block;
  margin-bottom: 8px;
}

.detail-item span,
.detail-item p {
  color: #666;
  line-height: 1.6;
}

.test-steps {
  white-space: pre-line;
  line-height: 1.6;
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #3498db;
}

/* 采纳用例弹框样式 */
.large-modal {
  max-width: 900px;
}

.adopt-form {
  max-width: 100%;
}

.form-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
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
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 8px;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
  background: white;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.form-hint {
  color: #666;
  font-size: 0.8rem;
  margin-top: 5px;
}

.required {
  color: #e74c3c;
  font-weight: bold;
}

.form-actions {
  display: flex;
  gap: 15px;
  justify-content: flex-end;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.confirm-btn {
  background: #27ae60;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.3s ease;
}

.confirm-btn:hover:not(:disabled) {
  background: #229954;
}

.confirm-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.cancel-btn {
  background: #95a5a6;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.3s ease;
}

.cancel-btn:hover {
  background: #7f8c8d;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .table-header,
  .table-body .table-row {
    grid-template-columns: 150px 1fr 100px 140px 260px;
  }

  .action-buttons {
    flex-direction: row;
    gap: 2px;
    align-items: center;
    flex-wrap: nowrap;
  }

  .view-detail-btn,
  .adopt-btn,
  .discard-btn,
  .export-btn {
    margin-right: 0;
    font-size: 0.65rem;
    padding: 2px 4px;
  }
}

@media (max-width: 768px) {
  .filter-card {
    flex-direction: column;
    align-items: stretch;
  }

  .stats-card {
    flex-wrap: wrap;
    gap: 20px;
  }

  .table-header,
  .table-body .table-row {
    grid-template-columns: 120px 1fr 80px 120px 240px;
  }
  
  .header-cell,
  .body-cell {
    padding: 8px;
    font-size: 0.8rem;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 2px;
    align-items: stretch;
  }
  
  .view-detail-btn,
  .adopt-btn,
  .discard-btn,
  .export-btn {
    font-size: 0.65rem;
    padding: 2px 4px;
  }
  
  .form-row {
    flex-direction: column;
    gap: 15px;
  }
  
  .large-modal {
    max-width: 95%;
  }
  
  .pagination-section {
    flex-direction: column;
    gap: 15px;
    align-items: flex-start;
  }
  
  .pagination-controls {
    flex-direction: column;
    gap: 15px;
    align-items: flex-start;
    width: 100%;
  }
  
  .pagination-buttons {
    justify-content: center;
    width: 100%;
  }
}
</style>
