<template>
  <div class="automation-suite-detail">
    <div class="content" v-loading="loading">
      <!-- 标题和操作按钮 -->
      <div class="header">
        <div class="header-left">
          <span class="page-title">{{ suite?.name || $t('apiTesting.automation.suiteDetail') }}</span>
          <!-- 评审状态徽章 -->
          <span v-if="reviewSummary" class="review-status-badge" :class="reviewSummary?.overall_status">
            {{ getReviewStatusText(reviewSummary?.overall_status) }}
          </span>
          <!-- 创建者、创建时间、更新时间 -->
          <span class="suite-meta-info" v-if="suite">
            <span class="meta-item">创建者: {{ suite.created_by?.username }}</span>
            <span class="meta-item">创建于: {{ formatDate(suite.created_at) }}</span>
            <span class="meta-item">更新于: {{ formatDate(suite.updated_at) }}</span>
          </span>
        </div>
        <div class="header-actions" v-if="suite">
          <!-- 执行环境选择器 -->
          <el-select
            :model-value="suite.environment?.id || suite.environment"
            :placeholder="$t('apiTesting.automation.selectEnvironment')"
            clearable
            class="env-select-inline"
            @change="handleEnvironmentChange"
            style="width: 180px;"
          >
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </div>
      </div>

      <!-- 场景编排 -->
      <div class="requests-section" v-if="suite">
        <div class="section-header">
          <h4>场景编排</h4>
          <div class="section-actions">
            <el-button type="info" @click="clearAllRequests" :disabled="!localSuiteRequests?.length">
              <el-icon><Delete /></el-icon>
              一键清空
            </el-button>
            <el-button type="success" @click="runTestSuite" :loading="running">
              <el-icon><VideoPlay /></el-icon>
              {{ $t('apiTesting.automation.runTest') }}
            </el-button>
            <el-button type="warning" @click="showAddRequest">
              <el-icon><Plus /></el-icon>
              {{ $t('apiTesting.automation.addRequest') }}
            </el-button>
            <!-- 评审按钮 - 只有未评审且不是创建者时显示 -->
            <template v-if="reviewSummary && !userHasReviewed && !isCreator">
              <el-button type="success" @click="submitReview('approved')">
                <el-icon><Check /></el-icon>
                通过
              </el-button>
              <el-button type="danger" @click="showRejectDialog = true">
                <el-icon><Close /></el-icon>
                拒绝
              </el-button>
            </template>
          </div>
        </div>
        
        <div class="requests-tree" v-if="localSuiteRequests?.length > 0">
          <draggable
            v-model="localSuiteRequests"
            :group="{ name: 'suite-requests', pull: true, put: true }"
            :animation="200"
            item-key="id"
            ghost-class="dragging-ghost"
            chosen-class="dragging-chosen"
            drag-class="dragging-drag"
            @change="onTopLevelChange"
          >
            <template #item="{ element, index }">
              <suite-request-tree
                :request="element"
                :index="index"
                :level="0"
                @edit="editRequest"
                @remove="removeRequest"
                @toggle-enabled="updateRequestEnabled"
                @order-change="onChildOrderChange"
              />
            </template>
          </draggable>
        </div>
        
        <el-empty v-else :description="$t('apiTesting.automation.noRequests')" class="requests-empty" />
      </div>

      <!-- 评审区域 - 有评审记录且(未通过或非创建人)时显示 -->
      <div class="review-section" v-if="suite && reviewRecords.length > 0 && (reviewSummary?.overall_status !== 'approved' || !isCreator)">
        <div class="section-header">
          <div class="header-left">
            <h4>场景评审</h4>
          </div>
        </div>

        <el-table :data="reviewRecords" v-loading="reviewLoading" size="small">
          <el-table-column type="index" :label="$t('apiTesting.common.sequence')" width="60" align="center">
            <template #default="scope">
              {{ scope.$index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="scope">
              <span class="status-badge" :class="scope.row.status">
                {{ getReviewStatusText(scope.row.status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="意见" min-width="200" align="center">
            <template #default="scope">
              <span style="display: inline-block; width: 100%; text-align: center;">
                {{ scope.row.status === 'approved' ? '-' : (scope.row.comment || '-') }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="reviewer.username" label="评审人" width="120" align="center" />
          <el-table-column prop="reviewed_at" label="评审时间" width="200" align="center">
            <template #default="scope">
              {{ formatDate(scope.row.reviewed_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right" align="center">
            <template #default="scope">
              <!-- 重新发起评审按钮 - 只有创建者且状态为拒绝时显示 -->
              <el-button
                v-if="isCreator && scope.row.status === 'rejected'"
                size="small"
                class="action-btn reset-btn"
                @click="resetReviews"
              >
                重新发起评审
              </el-button>
              <!-- 评审人操作按钮 -->
              <div v-else-if="scope.row.reviewer?.id === currentUser?.id" class="review-actions">
                <template v-if="scope.row.status === 'pending'">
                  <el-button
                    size="small"
                    class="action-btn approve-btn"
                    @click="submitReview('approved')"
                  >
                    通过
                  </el-button>
                  <el-button
                    size="small"
                    class="action-btn reject-btn"
                    @click="showRejectDialog = true"
                  >
                    拒绝
                  </el-button>
                </template>
                <template v-else>
                  <el-button
                    size="small"
                    class="action-btn edit-review-btn"
                    @click="editReview(scope.row)"
                  >
                    修改评审
                  </el-button>
                </template>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 拒绝原因对话框 -->
      <el-dialog v-model="showRejectDialog" title="拒绝原因" width="500px">
        <el-input
          v-model="rejectComment"
          type="textarea"
          :rows="4"
          placeholder="请输入拒绝原因（可选）"
        />
        <template #footer>
          <el-button @click="showRejectDialog = false">取消</el-button>
          <el-button type="primary" @click="submitReview('rejected')">确认</el-button>
        </template>
      </el-dialog>

      <!-- 执行历史 -->
      <div class="executions-section" v-if="suite">
        <div class="section-header">
          <h4>{{ $t('apiTesting.automation.executionHistory') }}</h4>
        </div>

        <el-table :data="executions" v-loading="executionsLoading" v-if="executions.length > 0">
          <el-table-column type="index" :label="$t('apiTesting.common.sequence')" width="60" align="center" />
          <el-table-column prop="status" :label="$t('apiTesting.common.status')" width="100" align="center">
            <template #default="scope">
              <span class="status-badge" :class="scope.row.status?.toLowerCase()">
                {{ getStatusText(scope.row.status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="total_requests" :label="$t('apiTesting.automation.totalRequests')" min-width="110" align="center" />
          <el-table-column prop="passed_requests" :label="$t('apiTesting.automation.passedCount')" min-width="90" align="center">
            <template #default="scope">
              <span style="color: #67c23a">{{ scope.row.passed_requests }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="failed_requests" :label="$t('apiTesting.automation.failedCount')" min-width="90" align="center">
            <template #default="scope">
              <span style="color: #f56c6c">{{ scope.row.failed_requests }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('apiTesting.automation.averageTime')" min-width="100" align="center">
            <template #default="scope">
              {{ getAverageExecutionTime(scope.row) }}
            </template>
          </el-table-column>
          <el-table-column prop="executed_by.username" :label="$t('apiTesting.automation.executor')" width="120" align="center" />
          <el-table-column prop="created_at" :label="$t('apiTesting.automation.executionTime')" width="200" align="center">
            <template #default="scope">
              {{ formatDate(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('apiTesting.common.operation')" width="120" align="center">
            <template #default="scope">
              <el-button size="small" class="action-btn view-detail-btn" @click="viewExecutionDetail(scope.row)">
                {{ $t('apiTesting.automation.viewDetails') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <el-empty v-else :description="$t('apiTesting.automation.noExecutions')" />
      </div>
    </div>

    <!-- 创建/编辑测试套件对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="$t('apiTesting.automation.editSuite')"
      width="600px"
      @close="resetEditForm"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="100px"
      >
        <el-form-item :label="$t('apiTesting.automation.suiteName')" prop="name">
          <el-input v-model="editForm.name" :placeholder="$t('apiTesting.automation.inputSuiteName')" class="suite-name-input" style="width: 320px;" />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.suiteDescription')" prop="description">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('apiTesting.automation.inputSuiteDescription')"
            class="suite-textarea"
          />
        </el-form-item>

      </el-form>

      <template #footer>
        <el-button @click="showEditDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="submitEditForm" :loading="submitting">
          {{ $t('apiTesting.common.update') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加步骤抽屉 -->
    <el-drawer
      v-model="showAddRequestDialog"
      :title="$t('apiTesting.automation.addStepToSuite')"
      size="600px"
      direction="rtl"
      :destroy-on-close="true"
      class="add-step-drawer"
    >
      <div class="add-request-content">
        <!-- Tab 切换 -->
        <el-tabs v-model="addStepTab" class="add-step-tabs">
          <!-- 接口 Tab -->
          <el-tab-pane label="引用接口" name="request">
            <div class="request-selector">
              <el-tree
                ref="requestTreeRef"
                :data="requestTree"
                :props="requestTreeProps"
                show-checkbox
                node-key="id"
                :check-on-click-node="false"
                @check="onRequestCheck"
              >
                <template #default="{ node, data }">
                  <div class="request-tree-node">
                    <el-icon v-if="data.type === 'collection'">
                      <Folder />
                    </el-icon>
                    <el-icon v-else>
                      <Document />
                    </el-icon>
                    <span>{{ data.name }}</span>
                    <span v-if="data.type === 'request'" class="method-tag" :class="data.method?.toLowerCase()">
                      {{ data.method }}
                    </span>
                  </div>
                </template>
              </el-tree>
            </div>
          </el-tab-pane>
          
          <!-- 场景 Tab -->
          <el-tab-pane label="引用场景" name="suite">
            <div class="suite-selector">
              <div v-if="availableSuites.length === 0" class="empty-suites">
                <el-empty description="暂无可引用的场景" />
              </div>
              <el-tree
                v-else
                ref="suiteTreeRef"
                :data="availableSuites"
                :props="suiteTreeProps"
                show-checkbox
                node-key="id"
                :check-on-click-node="false"
                @check="onSuiteCheck"
                default-expand-all
              >
                <template #default="{ node, data }">
                  <div class="suite-tree-node" :class="{ 'is-group': data.step_type === 'group', 'is-request': data.step_type === 'request' }">
                    <!-- 场景根节点 -->
                    <template v-if="!data.step_type">
                      <el-icon><Collection /></el-icon>
                      <span class="node-name">{{ data.name }}</span>
                      <span class="suite-request-count">({{ data.request_count }}个请求)</span>
                    </template>
                    <!-- 分组节点 -->
                    <template v-else-if="data.step_type === 'group'">
                      <el-icon><Folder /></el-icon>
                      <span class="node-name group-name">{{ data.name }}</span>
                      <span class="group-badge">{{ data.request_count }}个子项</span>
                    </template>
                    <!-- 请求节点 -->
                    <template v-else>
                      <span class="method-tag" :class="data.method?.toLowerCase()">{{ data.method }}</span>
                      <span class="node-name request-name">{{ data.name }}</span>
                    </template>
                  </div>
                </template>
              </el-tree>
            </div>
          </el-tab-pane>
          
          <!-- 等待时间 Tab -->
          <el-tab-pane label="等待时间" name="wait">
            <div class="wait-time-config">
              <el-form label-width="100px">
                <el-form-item label="等待时间">
                  <el-input-number 
                    v-model="waitTimeConfig.wait_time" 
                    :min="0" 
                    :max="3600" 
                    :step="1"
                    style="width: 180px"
                  >
                    <template #suffix>秒</template>
                  </el-input-number>
                </el-form-item>
                <el-form-item label="步骤名称">
                  <el-input 
                    v-model="waitTimeConfig.name" 
                    placeholder="等待时间"
                    style="width: 300px"
                  />
                </el-form-item>
              </el-form>
              <div class="wait-time-hint">
                <el-alert type="info" :closable="false">
                  <template #title>
                    <div class="hint-content">
                      <el-icon><InfoFilled /></el-icon>
                      <span>等待指定时间后继续执行后续步骤，适用于需要延时处理的场景</span>
                    </div>
                  </template>
                </el-alert>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      
      <template #footer>
        <el-button @click="showAddRequestDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="addSelectedSteps" :loading="addingRequests">
          {{ $t('apiTesting.automation.addSelectedSteps') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 执行结果抽屉 -->
    <el-drawer
      v-model="showExecutionDialog"
      :title="$t('apiTesting.automation.testExecutionResult')"
      size="70%"
      direction="rtl"
      :destroy-on-close="true"
      class="result-drawer"
    >
      <div v-if="currentExecution" class="execution-detail-drawer">
        <!-- 统计概览卡片 -->
        <div class="summary-cards">
          <el-row :gutter="16">
            <el-col :xs="12" :sm="12" :md="6" :lg="6">
              <div class="summary-card">
                <div class="card-icon total">
                  <el-icon><Document /></el-icon>
                </div>
                <div class="card-content">
                  <div class="card-label">{{ $t('apiTesting.automation.totalRequests') }}</div>
                  <div class="card-value">{{ currentExecution.total_requests }}</div>
                </div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" :lg="6">
              <div class="summary-card success">
                <div class="card-icon">
                  <el-icon><CircleCheck /></el-icon>
                </div>
                <div class="card-content">
                  <div class="card-label">{{ $t('apiTesting.automation.passedCount') }}</div>
                  <div class="card-value">{{ currentExecution.passed_requests }}</div>
                </div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" :lg="6">
              <div class="summary-card failed">
                <div class="card-icon">
                  <el-icon><CircleClose /></el-icon>
                </div>
                <div class="card-content">
                  <div class="card-label">{{ $t('apiTesting.automation.failedCount') }}</div>
                  <div class="card-value">{{ currentExecution.failed_requests }}</div>
                </div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" :lg="6">
              <div class="summary-card primary">
                <div class="card-icon">
                  <el-icon><TrendCharts /></el-icon>
                </div>
                <div class="card-content">
                  <div class="card-label">{{ $t('apiTesting.automation.passRate') }}</div>
                  <div class="card-value">{{ getPassRate(currentExecution) }}%</div>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 详细结果表格 -->
        <div class="result-table-section">
          <div class="section-header">
            <h4 class="section-title">
              <el-icon><List /></el-icon>
              {{ $t('apiTesting.automation.detailedResults') }}
            </h4>
          </div>
          <div class="table-wrapper">
            <el-table :data="formatExecutionResults(currentExecution.results)" class="custom-table">
              <el-table-column type="index" label="序号" width="70" header-align="center" align="center" />
              <el-table-column prop="name" :label="$t('apiTesting.automation.requestName')" min-width="150" header-align="center" align="center" />
              <el-table-column prop="method" :label="$t('apiTesting.automation.method')" width="100" header-align="center" align="center">
                <template #default="scope">
                  <span class="method-badge" :class="scope.row.method?.toLowerCase()">
                    {{ scope.row.method }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="status" :label="$t('apiTesting.automation.result')" width="100" header-align="center" align="center">
                <template #default="scope">
                  <span class="status-badge" :class="scope.row.passed ? 'success' : 'failed'">
                    {{ scope.row.passed ? $t('apiTesting.automation.testStatus.passed') : $t('apiTesting.automation.testStatus.failed') }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="status_code" :label="$t('apiTesting.automation.statusCode')" width="100" header-align="center" align="center" />
              <el-table-column prop="response_time" :label="$t('apiTesting.automation.responseTime')" width="100" header-align="center" align="center">
                <template #default="scope">
                  {{ scope.row.response_time?.toFixed(0) }}ms
                </template>
              </el-table-column>

              <el-table-column :label="$t('apiTesting.common.operation')" width="100" fixed="right" header-align="center" align="center">
                <template #default="scope">
                  <el-button link type="primary" size="small" @click="viewRequestDetail(scope.row)">
                    查看详情
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 请求详情抽屉 -->
    <el-drawer
      v-model="showRequestDetailDialog"
      title="请求执行详情"
      size="50%"
      direction="rtl"
      :destroy-on-close="true"
      class="detail-drawer"
    >
      <div v-if="currentRequestDetail" class="request-detail-drawer">
        <!-- 顶部状态栏 -->
        <div class="request-header">
          <div class="request-title-row">
            <span class="request-name">{{ currentRequestDetail.name }}</span>
            <span class="method-tag" :class="currentRequestDetail.method?.toLowerCase()">{{ currentRequestDetail.method }}</span>
            <span class="status-tag" :class="currentRequestDetail.passed ? 'success' : 'failed'">
              {{ currentRequestDetail.passed ? '通过' : '失败' }}
            </span>
            <span class="meta-tag time-tag">{{ currentRequestDetail.response_time?.toFixed(0) }}ms</span>
            <span class="meta-tag code-tag">{{ currentRequestDetail.status_code }}</span>
          </div>
          <div class="request-url">{{ currentRequestDetail.url }}</div>
        </div>

        <!-- 错误信息 -->
        <div v-if="currentRequestDetail.error" class="error-banner">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ currentRequestDetail.error }}</span>
        </div>

        <!-- 数据交换区域 -->
        <div class="data-section" v-if="currentRequestDetail.request_data || currentRequestDetail.response_data">
          <!-- 主标签切换 -->
          <div class="main-tabs">
            <button 
              class="main-tab-btn" 
              :class="{ active: activeDataTab === 'request' }"
              @click="activeDataTab = 'request'"
            >
              请求
            </button>
            <button 
              class="main-tab-btn" 
              :class="{ active: activeDataTab === 'response' }"
              @click="activeDataTab = 'response'"
            >
              响应
            </button>
          </div>
          
          <!-- 请求内容 -->
          <div v-if="activeDataTab === 'request' && currentRequestDetail.request_data" class="data-panel">
            <div class="panel-header">
              <div class="sub-tabs">
                <button 
                  v-for="tab in ['body', 'headers', 'params']" 
                  :key="tab"
                  class="sub-tab-btn"
                  :class="{ active: activeRequestTab === tab }"
                  @click="activeRequestTab = tab"
                >
                  {{ tab.toUpperCase() }}
                </button>
              </div>
              <span class="data-badge">{{ activeRequestTab.toUpperCase() }}</span>
            </div>
            <div class="code-container">
              <json-tree-viewer 
                :data="getRequestDataRaw()" 
                :root-path="getRequestJsonPathRoot()"
                @copy-path="copyJsonPathToClipboard"
              />
            </div>
          </div>
          
          <!-- 响应内容 -->
          <div v-if="activeDataTab === 'response' && currentRequestDetail.response_data" class="data-panel">
            <div class="panel-header">
              <div class="sub-tabs">
                <button 
                  v-for="tab in responseTabs" 
                  :key="tab.key"
                  class="sub-tab-btn"
                  :class="{ active: activeResponseTab === tab.key }"
                  @click="activeResponseTab = tab.key"
                >
                  {{ tab.label }}
                </button>
              </div>
              <span class="data-badge">{{ activeResponseTab.toUpperCase() }}</span>
            </div>
            <div class="code-container" v-if="activeResponseTab === 'body' || activeResponseTab === 'headers' || activeResponseTab === 'json'">
              <json-tree-viewer 
                :data="getResponseDataRaw()" 
                :root-path="getJsonPathRoot()"
                @copy-path="copyJsonPathToClipboard"
              />
            </div>
            <div class="assertions-container" v-else-if="activeResponseTab === 'assertions'">
              <div class="assertion-list">
                <div v-for="(item, idx) in currentRequestDetail.assertions_results" :key="idx" class="assertion-item" :class="item.passed ? 'passed' : 'failed'">
                  <el-icon><CircleCheck v-if="item.passed" /><CircleClose v-else /></el-icon>
                  <span class="assertion-name">{{ item.name }}</span>
                  <span class="assertion-detail">
                    <span class="detail-item expected">
                      <span class="label">期望</span>
                      <span class="value" :class="{ null: item.expected === null && !item.expected_desc, object: typeof item.expected === 'object' }">
                        {{ item.expected_desc || (item.expected === null ? 'null' : (typeof item.expected === 'object' ? JSON.stringify(item.expected).substring(0, 30) + '...' : item.expected)) }}
                      </span>
                    </span>
                    <span class="separator">|</span>
                    <span class="detail-item actual" :class="{ mismatch: !item.passed && item.actual !== item.expected }">
                      <span class="label">实际</span>
                      <span class="value" :class="{ null: item.actual === null, object: typeof item.actual === 'object' }">
                        {{ item.actual === null ? 'null' : (typeof item.actual === 'object' ? JSON.stringify(item.actual).substring(0, 30) + '...' : item.actual) }}
                      </span>
                    </span>
                  </span>
                  <span v-if="item.error" class="assertion-error">{{ item.error }}</span>
                </div>
              </div>
            </div>
            <div class="variables-container" v-else-if="activeResponseTab === 'variables'">
              <div class="variables-grid">
                <div v-for="(value, key) in currentRequestDetail.extracted_variables" :key="key" class="variable-item">
                  <span class="var-key">{{ key }}</span>
                  <span class="var-value">{{ value }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 接口编辑抽屉 -->
    <el-drawer
      v-model="showEditRequestDialog"
      title="编辑接口"
      size="900px"
      destroy-on-close
      class="edit-request-drawer"
    >
      <el-tabs v-model="editDrawerActiveTab" class="drawer-tabs">
        <!-- 基础信息 -->
        <el-tab-pane label="基础信息" name="basic">
          <!-- 等待时间步骤编辑表单 -->
          <el-form v-if="editingRequestData.step_type === 'wait'" :model="editingRequestData" label-width="100px">
            <el-form-item label="步骤名称">
              <el-input v-model="editingRequestData.name" placeholder="输入步骤名称" />
            </el-form-item>
            <el-form-item label="等待时间">
              <el-input-number 
                v-model="editingRequestData.wait_time" 
                :min="0" 
                :max="3600" 
                :step="1"
                style="width: 180px"
              >
                <template #suffix>秒</template>
              </el-input-number>
            </el-form-item>
          </el-form>
          <!-- 接口请求步骤编辑表单 -->
          <el-form v-else :model="editingRequestData" label-width="100px">
            <el-form-item label="接口名称">
              <el-input v-model="editingRequestData.name" placeholder="输入接口名称" />
            </el-form-item>
            <el-form-item label="请求方法">
              <el-select v-model="editingRequestData.method" style="width: 120px">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
                <el-option label="PUT" value="PUT" />
                <el-option label="DELETE" value="DELETE" />
                <el-option label="PATCH" value="PATCH" />
                <el-option label="HEAD" value="HEAD" />
                <el-option label="OPTIONS" value="OPTIONS" />
              </el-select>
            </el-form-item>
            <el-form-item label="请求URL">
              <el-input ref="urlInputRef" v-model="editingRequestData.url" placeholder="输入完整的请求URL">
                <template #append>
                  <el-button @click="openVariablePicker('url')" title="插入变量">
                    <el-icon><MagicStick /></el-icon>
                  </el-button>
                </template>
              </el-input>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 请求头 -->
        <el-tab-pane label="请求头" name="headers">
          <div class="key-value-editor">
            <div class="editor-header">
              <el-button size="small" @click="addEditingHeader">
                <el-icon><Plus /></el-icon> 添加
              </el-button>
            </div>
            <div class="kv-list">
              <div v-for="(item, index) in editingHeadersList" :key="index" class="kv-item">
                <el-input v-model="item.key" placeholder="Header 名称" class="kv-key" />
                <el-input v-model="item.value" placeholder="Header 值" class="kv-value">
                  <template #append>
                    <el-button @click="openVariablePicker('header', index)" title="插入变量">
                      <el-icon><MagicStick /></el-icon>
                    </el-button>
                  </template>
                </el-input>
                <el-button type="danger" size="small" circle @click="removeEditingHeader(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 请求参数 -->
        <el-tab-pane label="请求参数" name="params">
          <div class="key-value-editor">
            <div class="editor-header">
              <el-button size="small" @click="addEditingParam">
                <el-icon><Plus /></el-icon> 添加
              </el-button>
            </div>
            <div class="kv-list">
              <div v-for="(item, index) in editingParamsList" :key="index" class="kv-item">
                <el-input v-model="item.key" placeholder="参数名" class="kv-key" />
                <el-input v-model="item.value" placeholder="参数值" class="kv-value">
                  <template #append>
                    <el-button @click="openVariablePicker('param', index)" title="插入变量">
                      <el-icon><MagicStick /></el-icon>
                    </el-button>
                  </template>
                </el-input>
                <el-button type="danger" size="small" circle @click="removeEditingParam(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 请求体 -->
        <el-tab-pane label="请求体" name="body" v-if="['POST', 'PUT', 'PATCH'].includes(editingRequestData.method)">
          <div class="body-editor">
            <div class="body-toolbar">
              <el-radio-group v-model="editingRequestData.bodyType" size="small">
                <el-radio-button label="json">JSON</el-radio-button>
                <el-radio-button label="raw">Raw</el-radio-button>
              </el-radio-group>
              <el-button 
                size="small"
                @click="openVariablePicker('body')"
                title="插入变量"
              >
                <el-icon><MagicStick /></el-icon>
                插入变量
              </el-button>
            </div>
            <div class="body-input-wrapper">
              <el-input
                ref="bodyInputRef"
                v-model="editingRequestData.bodyContent"
                type="textarea"
                :rows="15"
                placeholder="输入请求体内容，支持 {{$env.variable}} 语法引用环境变量"
              />
            </div>
          </div>
        </el-tab-pane>

        <!-- 提取变量 -->
        <el-tab-pane label="提取变量" name="extractors">
          <div class="variable-extractors-editor">
            <div class="extractors-header" style="margin-bottom: 16px;">
              <el-button size="small" type="primary" @click="addEditingExtractor">
                <el-icon><Plus /></el-icon> 添加提取规则
              </el-button>
              <span class="extractors-hint" style="margin-left: 12px; color: #909399; font-size: 12px;">从响应中提取变量供后续接口使用</span>
            </div>
            <div class="extractors-table" v-if="editingExtractorsList && editingExtractorsList.length > 0">
              <div class="extractors-table-header" style="display: flex; padding: 8px; background: #f5f7fa; font-weight: 500; font-size: 13px;">
                <div style="flex: 1.5;">规则名称</div>
                <div style="flex: 1;">提取来源</div>
                <div style="flex: 2;">提取路径/Header名</div>
                <div style="flex: 1;">变量名</div>
                <div style="width: 50px;">操作</div>
              </div>
              <div class="extractors-table-body">
                <div
                  v-for="(extractor, index) in editingExtractorsList"
                  :key="index"
                  style="display: flex; padding: 8px; align-items: center; border-bottom: 1px solid #ebeef5;"
                >
                  <div style="flex: 1.5; padding-right: 8px;">
                    <el-input
                      v-model="extractor.name"
                      placeholder="规则名称"
                      size="small"
                    />
                  </div>
                  <div style="flex: 1; padding-right: 8px;">
                    <el-select
                      v-model="extractor.source"
                      placeholder="选择来源"
                      size="small"
                    >
                      <el-option label="JSON Body" value="json_body" />
                      <el-option label="Response Header" value="header" />
                    </el-select>
                  </div>
                  <div style="flex: 2; padding-right: 8px;">
                    <el-input
                      v-if="extractor.source === 'json_body'"
                      v-model="extractor.json_path"
                      placeholder="JSON Path 表达式"
                      size="small"
                    >
                      <template #append>
                        <el-button @click="openVariablePicker('extractor_json_path', index)" title="插入变量">
                          <el-icon><MagicStick /></el-icon>
                        </el-button>
                      </template>
                    </el-input>
                    <el-input
                      v-else-if="extractor.source === 'header'"
                      v-model="extractor.header_name"
                      placeholder="Header 名称"
                      size="small"
                    >
                      <template #append>
                        <el-button @click="openVariablePicker('extractor_header_name', index)" title="插入变量">
                          <el-icon><MagicStick /></el-icon>
                        </el-button>
                      </template>
                    </el-input>
                    <el-input
                      v-else
                      placeholder="请先选择提取来源"
                      size="small"
                      disabled
                    />
                  </div>
                  <div style="flex: 1; padding-right: 8px;">
                    <el-input
                      v-model="extractor.variable_name"
                      placeholder="变量名"
                      size="small"
                    />
                  </div>
                  <div style="width: 50px;">
                    <el-button
                      size="small"
                      type="danger"
                      @click="removeEditingExtractor(index)"
                      circle
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
            <div v-else style="text-align: center; padding: 40px; color: #909399;">
              <p>暂无提取规则</p>
              <el-button size="small" type="primary" @click="addEditingExtractor">
                <el-icon><Plus /></el-icon> 添加第一条规则
              </el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- 断言 -->
        <el-tab-pane label="断言" name="assertions">
          <div class="assertions-editor">
            <div class="assertions-header" style="margin-bottom: 16px; display: flex; gap: 2px; justify-content: flex-end;">
              <el-button size="small" type="primary" @click="addEditingAssertion">
                <el-icon><Plus /></el-icon> 添加断言
              </el-button>
              <el-button
                size="small"
                type="success"
                @click="testExecuteForAIAssertion"
                :loading="testingForAssertion"
                :disabled="!editingRequestData.url"
              >
                <el-icon><VideoPlay /></el-icon> 测试执行
              </el-button>
              <el-button
                v-if="editingTestResponse"
                size="small"
                type="warning"
                @click="generateAIAssertionsForEditing"
                :loading="generatingAIAssertions"
              >
                <el-icon><MagicStick /></el-icon> AI生成断言
              </el-button>
            </div>

            <!-- 测试执行响应展示 -->
            <div v-if="editingTestResponse" class="test-response-preview" style="margin-bottom: 16px; border: 1px solid #e4e7ed; border-radius: 8px; overflow: hidden;">
              <!-- 状态栏 -->
              <div style="display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #fafafa; border-bottom: 1px solid #e4e7ed;">
                <el-tag :type="editingTestResponse.status_code >= 200 && editingTestResponse.status_code < 300 ? 'success' : 'danger'" size="small" effect="light">
                  {{ editingTestResponse.status_code }}
                </el-tag>
                <span style="font-size: 13px; color: #606266;">{{ editingTestResponse.response_time?.toFixed(0) }}ms</span>
              </div>
              <!-- JSON 内容 -->
              <div style="max-height: 300px; overflow: auto; background: #fff;">
                <pre style="margin: 0; padding: 16px; font-size: 13px; line-height: 1.6; font-family: 'Monaco', 'Menlo', 'Consolas', monospace;" v-html="formatJSONWithSyntaxHighlight(editingTestResponse.response_data?.json || editingTestResponse.response_data?.body)"></pre>
              </div>
            </div>
            <div class="assertions-table" v-if="editingAssertionsList && editingAssertionsList.length > 0">
              <div class="assertions-table-header" style="display: flex; padding: 8px; background: #f5f7fa; font-weight: 500; font-size: 13px;">
                <div style="flex: 1.5;">断言名称</div>
                <div style="flex: 1;">断言类型</div>
                <div style="flex: 2.5;">参数</div>
                <div style="width: 50px;">操作</div>
              </div>
              <div class="assertions-table-body">
                <div
                  v-for="(assertion, index) in editingAssertionsList"
                  :key="index"
                  style="display: flex; padding: 8px; align-items: center; border-bottom: 1px solid #ebeef5;"
                >
                  <div style="flex: 1.5; padding-right: 8px;">
                    <el-input
                      v-model="assertion.name"
                      placeholder="断言名称"
                      size="small"
                    />
                  </div>
                  <div style="flex: 1; padding-right: 8px;">
                    <el-select
                      v-model="assertion.type"
                      placeholder="选择类型"
                      size="small"
                      @change="onEditingAssertionTypeChange(assertion)"
                    >
                      <el-option label="状态码" value="status_code" />
                      <el-option label="响应时间" value="response_time" />
                      <el-option label="包含文本" value="contains" />
                      <el-option label="JSON Path" value="json_path" />
                      <el-option label="Header" value="header" />
                      <el-option label="完全匹配" value="equals" />
                    </el-select>
                  </div>
                  <div style="flex: 2.5; padding-right: 8px;">
                    <el-input-number
                      v-if="assertion.type === 'status_code'"
                      v-model="assertion.expected"
                      :min="100"
                      :max="599"
                      size="small"
                      placeholder="预期状态码"
                    />
                    <el-input-number
                      v-else-if="assertion.type === 'response_time'"
                      v-model="assertion.expected"
                      :min="1"
                      size="small"
                      placeholder="最大响应时间(ms)"
                    />
                    <el-input
                      v-else-if="assertion.type === 'contains'"
                      v-model="assertion.expected"
                      placeholder="预期包含的文本"
                      size="small"
                    >
                      <template #append>
                        <el-button @click="openVariablePicker('assertion_contains', index)" title="插入变量">
                          <el-icon><MagicStick /></el-icon>
                        </el-button>
                      </template>
                    </el-input>
                    <div v-else-if="assertion.type === 'json_path'" style="display: flex; gap: 8px;">
                      <el-input
                        v-model="assertion.json_path"
                        placeholder="JSON Path"
                        size="small"
                        style="flex: 1;"
                      >
                        <template #append>
                          <el-button @click="openVariablePicker('assertion_json_path', index)" title="插入变量">
                            <el-icon><MagicStick /></el-icon>
                          </el-button>
                        </template>
                      </el-input>
                      <el-input
                        v-model="assertion.expected"
                        :placeholder="getExpectedPlaceholder(assertion)"
                        size="small"
                        style="flex: 1;"
                      >
                        <template #append>
                          <el-button @click="openVariablePicker('assertion_json_expected', index)" title="插入变量">
                            <el-icon><MagicStick /></el-icon>
                          </el-button>
                        </template>
                      </el-input>
                    </div>
                    <div v-else-if="assertion.type === 'header'" style="display: flex; gap: 8px;">
                      <el-input
                        v-model="assertion.header_name"
                        placeholder="Header名称"
                        size="small"
                        style="flex: 1;"
                      >
                        <template #append>
                          <el-button @click="openVariablePicker('assertion_header_name', index)" title="插入变量">
                            <el-icon><MagicStick /></el-icon>
                          </el-button>
                        </template>
                      </el-input>
                      <el-input
                        v-model="assertion.expected_value"
                        placeholder="预期值"
                        size="small"
                        style="flex: 1;"
                      >
                        <template #append>
                          <el-button @click="openVariablePicker('assertion_header_expected', index)" title="插入变量">
                            <el-icon><MagicStick /></el-icon>
                          </el-button>
                        </template>
                      </el-input>
                    </div>
                    <el-input
                      v-else-if="assertion.type === 'equals'"
                      v-model="assertion.expected"
                      placeholder="预期匹配内容"
                      size="small"
                    >
                      <template #append>
                        <el-button @click="openVariablePicker('assertion_equals', index)" title="插入变量">
                          <el-icon><MagicStick /></el-icon>
                        </el-button>
                      </template>
                    </el-input>
                    <el-input
                      v-else
                      placeholder="请先选择断言类型"
                      size="small"
                      disabled
                    />
                  </div>
                  <div style="width: 50px;">
                    <el-button
                      size="small"
                      type="danger"
                      @click="removeEditingAssertion(index)"
                      circle
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
            <div v-else style="text-align: center; padding: 40px; color: #909399;">
              <p>暂无断言</p>
              <el-button size="small" type="primary" @click="addEditingAssertion">
                <el-icon><Plus /></el-icon> 添加第一条断言
              </el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <div class="drawer-footer">
          <el-button type="default" class="btn-cancel" @click="showEditRequestDialog = false">取消</el-button>
          <el-button type="primary" @click="saveRequestEdit" :loading="savingRequestEdit">保存</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 变量选择器抽屉 -->
    <el-drawer
      v-model="showVariablePickerDialog"
      title="插入动态值"
      size="550px"
      direction="rtl"
      :close-on-click-modal="false"
      append-to-body
      class="variable-picker-drawer"
    >
      <div class="variable-picker-content">
        <div class="picker-section">
          <div class="section-title">选择变量类型</div>
          <el-radio-group v-model="selectedVarCategory" size="small">
            <el-radio-button label="prev">前置接口</el-radio-button>
            <el-radio-button label="env">环境变量</el-radio-button>
            <el-radio-button label="dynamic">动态函数</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 前置接口变量 -->
        <div v-if="selectedVarCategory === 'prev'" class="picker-section">
          <div v-if="previousRequests.length === 0" class="no-prev-requests">
            <el-alert
              title="没有可用的前置接口"
              type="warning"
              :closable="false"
              description="当前接口是集合中的第一个接口，或集合中没有其他接口。"
            />
          </div>
          <div v-else>
            <div class="section-title">选择前置接口</div>
            <el-select v-model="selectedPrevRequestId" placeholder="选择要引用的接口" style="width: 100%" @change="onPrevRequestChange">
              <el-option
                v-for="req in previousRequests"
                :key="req.id"
                :label="`${req.displayOrder}. ${req.alias || req.request?.name || '未命名接口'}`"
                :value="req.id"
              >
                <div class="request-option">
                  <span class="request-order">{{ req.displayOrder }}</span>
                  <span class="request-name">{{ req.alias || req.request?.name || '未命名接口' }}</span>
                  <el-tag v-if="req.alias" size="small" type="info">别名: {{ req.alias }}</el-tag>
                </div>
              </el-option>
            </el-select>

            <div v-if="selectedPrevRequest" class="var-type-section">
              <div class="section-title">选择变量类型</div>
              <el-radio-group v-model="selectedVarType" size="small" @change="onVarTypeChange">
                <el-radio-button label="request.body">请求体</el-radio-button>
                <el-radio-button label="response.body">响应体</el-radio-button>
                <el-radio-button label="response.headers">响应头</el-radio-button>
                <el-radio-button label="response.status_code">状态码</el-radio-button>
                <el-radio-button label="response.response_time">响应时间</el-radio-button>
              </el-radio-group>
            </div>

            <!-- 执行结果展示区域 -->
            <div v-if="selectedPrevRequest && selectedVarType && previewData" class="execution-preview-section">
              <div class="section-title">
                点击字段复制路径
                <el-tag v-if="selectedPrevRequestExecution" size="small" :type="selectedPrevRequestExecution.passed ? 'success' : 'danger'">
                  {{ selectedPrevRequestExecution.passed ? '通过' : '失败' }}
                </el-tag>
              </div>
              <div class="preview-data-container">
                <json-tree-viewer
                  :data="previewData"
                  :root-path="getVariablePreviewRoot()"
                  @copy-path="onJsonPathCopy"
                />
              </div>
            </div>

            <div v-if="selectedPrevRequest && loadingExecution" class="execution-loading">
              <el-skeleton :rows="3" animated />
            </div>

            <div v-if="selectedPrevRequest && executionError" class="execution-error">
              <el-alert
                :title="executionError"
                type="warning"
                :closable="false"
                show-icon
              />
            </div>

            <div v-if="selectedPrevRequest && needsJsonPath" class="json-path-section">
              <div class="section-title">
                JSON Path（已自动填充，可手动修改）
                <el-tooltip content="例如: $.data.id 或 $.list[0].name">
                  <el-icon><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
              <el-input
                v-model="jsonPath"
                placeholder="点击上方字段自动生成"
                clearable
              />
            </div>
          </div>
        </div>

        <!-- 环境变量 -->
        <div v-if="selectedVarCategory === 'env'" class="picker-section">
          <div class="section-title">环境变量名</div>
          <el-input
            v-model="varName"
            placeholder="如: base_url, api_key"
          />
          <div class="var-hint" v-pre>用法: {{$env.变量名}}</div>
        </div>

        <!-- 全局变量 -->
        <div v-if="selectedVarCategory === 'global'" class="picker-section">
          <div class="section-title">全局变量名</div>
          <el-input
            v-model="varName"
            placeholder="如: token, user_id"
          />
          <div class="var-hint" v-pre>用法: {{$global.变量名}}</div>
        </div>

        <!-- 动态函数 -->
        <div v-if="selectedVarCategory === 'dynamic'" class="picker-section">
          <div class="section-title">选择函数分类</div>
          <el-select v-model="selectedFunctionCategory" placeholder="选择函数分类" style="width: 100%; margin-bottom: 16px;">
            <el-option
              v-for="category in functionCategories"
              :key="category.value"
              :label="category.label"
              :value="category.value"
            />
          </el-select>

          <div v-if="selectedFunctionCategory" class="section-title">选择函数</div>
          <el-select
            v-if="selectedFunctionCategory"
            v-model="selectedFunction"
            placeholder="选择函数"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="func in filteredFunctions"
              :key="func.name"
              :label="func.display_name"
              :value="func.name"
            >
              <div class="function-option">
                <span class="function-name">{{ func.display_name }}</span>
                <span class="function-desc">{{ func.description }}</span>
              </div>
            </el-option>
          </el-select>

          <!-- 参数输入区域 -->
          <div v-if="selectedFunction && functionNeedsParams" class="function-params">
            <div class="section-title">参数配置</div>

            <!-- 随机字符串/随机整数参数 -->
            <div v-if="selectedFunction === 'random_string' || selectedFunction === 'random_int'" class="param-row">
              <el-input-number v-model="funcParam1" :min="1" :max="100" style="width: 120px" />
              <span class="param-hint">{{ selectedFunction === 'random_string' ? '长度' : '最大值' }}</span>
            </div>

            <!-- 随机浮点数参数 -->
            <div v-else-if="selectedFunction === 'random_float'" class="param-row">
              <el-input-number v-model="funcParamMin" :precision="2" style="width: 140px" placeholder="最小值" />
              <span class="param-separator">~</span>
              <el-input-number v-model="funcParamMax" :precision="2" style="width: 140px" placeholder="最大值" />
            </div>

            <!-- 随机日期参数 -->
            <div v-else-if="selectedFunction === 'random_date'" class="param-row">
              <el-date-picker
                v-model="funcParamDateStart"
                type="date"
                placeholder="开始日期"
                style="width: 140px"
                value-format="YYYY-MM-DD"
              />
              <span class="param-separator">~</span>
              <el-date-picker
                v-model="funcParamDateEnd"
                type="date"
                placeholder="结束日期"
                style="width: 140px"
                value-format="YYYY-MM-DD"
              />
            </div>

            <!-- 随机密码参数 -->
            <div v-else-if="selectedFunction === 'random_password'" class="param-row">
              <el-input-number v-model="funcParam1" :min="6" :max="32" style="width: 120px" />
              <span class="param-hint">密码长度</span>
            </div>

            <!-- 随机IP地址参数 -->
            <div v-else-if="selectedFunction === 'random_ip_address'" class="param-row">
              <el-radio-group v-model="funcParamIpType" size="small">
                <el-radio-button label="ipv4">IPv4</el-radio-button>
                <el-radio-button label="ipv6">IPv6</el-radio-button>
              </el-radio-group>
            </div>

            <!-- 其他需要参数的函数 -->
            <div v-else class="param-row">
              <el-input v-model="funcParamString" placeholder="输入参数（可选）" style="width: 200px" />
            </div>
          </div>

          <!-- 函数语法和示例说明 -->
          <div v-if="selectedFunction && currentFunction" class="function-syntax-section">
            <div class="syntax-row description-row">
              <span class="syntax-label">描述：</span>
              <span class="syntax-description">{{ currentFunction.description }}</span>
            </div>
            <div class="syntax-row">
              <span class="syntax-label">语法：</span>
              <code class="syntax-code">{{ currentFunction.syntax }}</code>
            </div>
            <div class="syntax-row">
              <span class="syntax-label">示例：</span>
              <code class="syntax-code">{{ currentFunction.example }}</code>
            </div>
          </div>

        </div>

        <div class="preview-section">
          <div class="preview-row">
            <div class="section-title">预览</div>
            <el-input v-model="variablePreview" readonly class="preview-input">
              <template #append>
                <el-button @click="copyVariableToClipboard">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="drawer-footer">
          <el-button type="default" class="btn-cancel" @click="closeVariablePicker">取消</el-button>
          <el-button type="primary" @click="confirmVariableInsertion">插入</el-button>
        </div>
      </template>
    </el-drawer>

  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import draggable from 'vuedraggable'
import api from '@/utils/api'
import { updateTestSuiteRequest } from '@/api/api-testing'
import { createScenarioStep } from '@/api/scenario'
import SuiteRequestTree from './components/SuiteRequestTree.vue'
import JsonTreeViewer from '@/components/JsonTreeViewer.vue'
import { VideoPlay, Plus, Refresh, Folder, Document, Check, Close, RefreshLeft, Edit, Delete, Rank, CircleCheck, CircleClose, TrendCharts, List, InfoFilled, WarningFilled, Upload, Download, Collection, Timer, DocumentChecked, MagicStick, CopyDocument } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

// 数据
const suite = ref(null)
const localSuiteRequests = ref([])  // 本地套件请求列表，用于拖拽排序
const environments = ref([])
const executions = ref([])
const loading = ref(false)
const executionsLoading = ref(false)
const running = ref(false)
const requestTree = ref([])

// 添加步骤相关
const addStepTab = ref('request')
const availableSuites = ref([])
const selectedSuiteIds = ref([])

// 等待时间配置
const waitTimeConfig = ref({
  wait_time: 1,
  name: '等待时间'
})
const suiteTreeRef = ref(null)
const suiteTreeProps = {
  children: 'children',
  label: 'name'
}

// 评审相关
const reviewRecords = ref([])
const reviewSummary = ref(null)
const showRejectDialog = ref(false)
const reviewLoading = ref(false)
const rejectComment = ref('')
const userHasReviewed = computed(() => {
  return reviewRecords.value.some(r => r.reviewer?.id === currentUser.value?.id && r.status !== 'pending')
})
const currentUser = ref(null)
const isCreator = computed(() => {
  return suite.value?.created_by?.id === currentUser.value?.id
})

// 对话框状态
const showEditDialog = ref(false)
const showAddRequestDialog = ref(false)
const showExecutionDialog = ref(false)
const showRequestDetailDialog = ref(false)
const submitting = ref(false)
const addingRequests = ref(false)
const currentExecution = ref(null)
const currentRequestDetail = ref(null)

// 请求详情抽屉状态
const activeDataTab = ref('request')
const activeRequestTab = ref('body')
const activeResponseTab = ref('body')

// 响应 Tab 列表（动态包含断言 Tab 和变量提取 Tab）
const responseTabs = computed(() => {
  const tabs = [
    { key: 'body', label: 'BODY' },
    { key: 'headers', label: 'HEADERS' },
    { key: 'json', label: 'JSON' }
  ]
  if (currentRequestDetail.value?.assertions_results?.length > 0) {
    tabs.push({ key: 'assertions', label: `断言(${currentRequestDetail.value.assertions_results.length})` })
  }
  if (currentRequestDetail.value?.extracted_variables && Object.keys(currentRequestDetail.value.extracted_variables).length > 0) {
    tabs.push({ key: 'variables', label: '变量提取' })
  }
  return tabs
})

// 接口编辑相关
const showEditRequestDialog = ref(false)
const editDrawerActiveTab = ref('body')
const savingRequestEdit = ref(false)
const editingRequestData = ref({
  id: null,
  step_type: 'request',
  name: '',
  method: 'GET',
  url: '',
  headers: {},
  params: {},
  body: {},
  bodyType: 'json',
  bodyContent: '',
  wait_time: 1
})
const editingHeadersList = ref([])
const editingParamsList = ref([])
const editingExtractorsList = ref([])
const editingAssertionsList = ref([])

// 接口编辑时的测试执行和AI断言相关
const testingForAssertion = ref(false)
const generatingAIAssertions = ref(false)
const editingTestResponse = ref(null)

// ========== 变量选择器相关 ==========
const showVariablePickerDialog = ref(false)
const selectedVarCategory = ref('env')
const varName = ref('')
const selectedFunction = ref('')
const selectedFunctionCategory = ref('')
const funcParam1 = ref(8)
const funcParamMin = ref(0)
const funcParamMax = ref(100)
const funcParamDateStart = ref('')
const funcParamDateEnd = ref('')
const funcParamIpType = ref('ipv4')
const funcParamString = ref('')
const variablePickerTarget = ref({ type: '', index: -1 })

// 函数分类列表
const functionCategories = [
  { label: '测试数据', value: 'test_data' },
  { label: '随机工具', value: 'random' },
  { label: '编码工具', value: 'encoding' },
  { label: '加密工具', value: 'encryption' },
  { label: '字符工具', value: 'string' },
  { label: 'JSON工具', value: 'json' },
  { label: '专业工具', value: 'professional' },
  { label: '系统工具', value: 'system' },
  { label: '娱乐工具', value: 'entertainment' },
  { label: 'Mock图片', value: 'mock_image' }
]

// 数据工厂函数列表
const dataFactoryFunctions = [
  // 测试数据
  { name: 'generate_chinese_name', display_name: '生成中文姓名', description: '生成随机中文姓名', category: 'test_data', hasParams: false, syntax: '{{$generate_chinese_name()}}', example: '{{$generate_chinese_name()}}' },
  { name: 'generate_chinese_phone', display_name: '生成手机号', description: '生成随机中国手机号', category: 'test_data', hasParams: false, syntax: '{{$generate_chinese_phone()}}', example: '{{$generate_chinese_phone()}}' },
  { name: 'generate_chinese_email', display_name: '生成邮箱', description: '生成随机邮箱地址', category: 'test_data', hasParams: false, syntax: '{{$generate_chinese_email()}}', example: '{{$generate_chinese_email()}}' },
  { name: 'generate_chinese_address', display_name: '生成地址', description: '生成随机中文地址', category: 'test_data', hasParams: false, syntax: '{{$generate_chinese_address()}}', example: '{{$generate_chinese_address()}}' },
  { name: 'generate_id_card', display_name: '生成身份证号', description: '生成随机身份证号', category: 'test_data', hasParams: false, syntax: '{{$generate_id_card()}}', example: '{{$generate_id_card()}}' },
  { name: 'generate_company_name', display_name: '生成公司名称', description: '生成随机公司名称', category: 'test_data', hasParams: false, syntax: '{{$generate_company_name()}}', example: '{{$generate_company_name()}}' },
  { name: 'generate_bank_card', display_name: '生成银行卡号', description: '生成随机银行卡号', category: 'test_data', hasParams: false, syntax: '{{$generate_bank_card()}}', example: '{{$generate_bank_card()}}' },
  { name: 'generate_hk_id_card', display_name: '生成香港身份证号', description: '生成随机香港身份证号', category: 'test_data', hasParams: false, syntax: '{{$generate_hk_id_card()}}', example: '{{$generate_hk_id_card()}}' },
  { name: 'generate_business_license', display_name: '生成营业执照号', description: '生成随机营业执照号', category: 'test_data', hasParams: false, syntax: '{{$generate_business_license()}}', example: '{{$generate_business_license()}}' },
  { name: 'generate_coordinates', display_name: '生成经纬度', description: '生成随机经纬度数据', category: 'test_data', hasParams: false, syntax: '{{$generate_coordinates()}}', example: '{{$generate_coordinates()}}' },
  { name: 'generate_user_profile', display_name: '生成用户档案', description: '生成完整用户档案', category: 'test_data', hasParams: false, syntax: '{{$generate_user_profile()}}', example: '{{$generate_user_profile()}}' },

  // 随机工具
  { name: 'random_int', display_name: '随机整数', description: '生成指定范围的随机整数', category: 'random', hasParams: true, syntax: '{{$random_int(min, max)}}', example: '{{$random_int(1, 100)}}' },
  { name: 'random_float', display_name: '随机浮点数', description: '生成指定范围的随机浮点数', category: 'random', hasParams: true, syntax: '{{$random_float(min, max, decimals)}}', example: '{{$random_float(0.1, 9.9, 2)}}' },
  { name: 'random_string', display_name: '随机字符串', description: '生成指定长度的随机字符串', category: 'random', hasParams: true, syntax: '{{$random_string(length, char_type)}}', example: '{{$random_string(10, "alphanumeric")}}' },
  { name: 'random_uuid', display_name: '随机UUID', description: '生成随机UUID(GUID)', category: 'random', hasParams: false, syntax: '{{$random_uuid()}}', example: '{{$random_uuid()}}' },
  { name: 'random_boolean', display_name: '随机布尔值', description: '生成随机布尔值', category: 'random', hasParams: false, syntax: '{{$random_boolean()}}', example: '{{$random_boolean()}}' },
  { name: 'random_mac_address', display_name: '随机MAC地址', description: '生成随机MAC地址', category: 'random', hasParams: false, syntax: '{{$random_mac_address()}}', example: '{{$random_mac_address()}}' },
  { name: 'random_ip_address', display_name: '随机IP地址', description: '生成随机IP地址(IPv4/IPv6)', category: 'random', hasParams: true, syntax: '{{$random_ip_address(ip_version)}}', example: '{{$random_ip_address("ipv4")}}' },
  { name: 'random_date', display_name: '随机日期', description: '生成指定范围内的随机日期', category: 'random', hasParams: true, syntax: '{{$random_date(start_date, end_date, format)}}', example: '{{$random_date("2024-01-01", "2024-12-31", "yyyy-MM-dd")}}' },
  { name: 'random_password', display_name: '随机密码', description: '生成随机密码(包含大小写、数字、特殊字符)', category: 'random', hasParams: true, syntax: '{{$random_password(length)}}', example: '{{$random_password(12)}}' },
  { name: 'random_color', display_name: '随机颜色', description: '生成随机颜色数据', category: 'random', hasParams: false, syntax: '{{$random_color()}}', example: '{{$random_color()}}' },
  { name: 'random_sequence', display_name: '随机序列数据', description: '生成随机序列数据', category: 'random', hasParams: false, syntax: '{{$random_sequence()}}', example: '{{$random_sequence()}}' },

  // 编码工具
  { name: 'timestamp_convert', display_name: '时间戳转换', description: '时间戳与日期时间相互转换', category: 'encoding', hasParams: false, syntax: '{{$timestamp_convert()}}', example: '{{$timestamp_convert()}}' },
  { name: 'base_convert', display_name: '进制转换', description: '不同进制之间的转换', category: 'encoding', hasParams: false, syntax: '{{$base_convert()}}', example: '{{$base_convert()}}' },
  { name: 'unicode_convert', display_name: 'Unicode转换', description: '中文与Unicode相互转换', category: 'encoding', hasParams: false, syntax: '{{$unicode_convert()}}', example: '{{$unicode_convert()}}' },
  { name: 'ascii_convert', display_name: 'ASCII转换', description: '字符与ASCII码相互转换', category: 'encoding', hasParams: false, syntax: '{{$ascii_convert()}}', example: '{{$ascii_convert()}}' },
  { name: 'color_convert', display_name: '颜色值转换', description: '不同颜色格式之间的转换', category: 'encoding', hasParams: false, syntax: '{{$color_convert()}}', example: '{{$color_convert()}}' },
  { name: 'url_encode', display_name: 'URL编码', description: '使用URL算法加密数据', category: 'encoding', hasParams: false, syntax: '{{$url_encode()}}', example: '{{$url_encode()}}' },
  { name: 'url_decode', display_name: 'URL解码', description: '使用URL算法解密数据', category: 'encoding', hasParams: false, syntax: '{{$url_decode()}}', example: '{{$url_decode()}}' },
  { name: 'jwt_decode', display_name: 'JWT解码', description: '解码JWT令牌', category: 'encoding', hasParams: false, syntax: '{{$jwt_decode()}}', example: '{{$jwt_decode()}}' },
  { name: 'base64_encode', display_name: 'Base64编码', description: '使用Base64算法加密数据', category: 'encoding', hasParams: false, syntax: '{{$base64_encode()}}', example: '{{$base64_encode()}}' },
  { name: 'base64_decode', display_name: 'Base64解码', description: '使用Base64算法解密数据', category: 'encoding', hasParams: false, syntax: '{{$base64_decode()}}', example: '{{$base64_decode()}}' },

  // 加密工具
  { name: 'md5_hash', display_name: 'MD5加密', description: '生成MD5哈希值', category: 'encryption', hasParams: false, syntax: '{{$md5_hash()}}', example: '{{$md5_hash()}}' },
  { name: 'sha1_hash', display_name: 'SHA1加密', description: '生成SHA1哈希值', category: 'encryption', hasParams: false, syntax: '{{$sha1_hash()}}', example: '{{$sha1_hash()}}' },
  { name: 'sha256_hash', display_name: 'SHA256加密', description: '生成SHA256哈希值', category: 'encryption', hasParams: false, syntax: '{{$sha256_hash()}}', example: '{{$sha256_hash()}}' },
  { name: 'sha512_hash', display_name: 'SHA512加密', description: '生成SHA512哈希值', category: 'encryption', hasParams: false, syntax: '{{$sha512_hash()}}', example: '{{$sha512_hash()}}' },
  { name: 'aes_encrypt', display_name: 'AES加密', description: '使用AES算法加密数据', category: 'encryption', hasParams: false, syntax: '{{$aes_encrypt()}}', example: '{{$aes_encrypt()}}' },
  { name: 'aes_decrypt', display_name: 'AES解密', description: '使用AES算法解密数据', category: 'encryption', hasParams: false, syntax: '{{$aes_decrypt()}}', example: '{{$aes_decrypt()}}' },
  { name: 'password_strength', display_name: '密码强度分析', description: '分析密码的强度', category: 'encryption', hasParams: false, syntax: '{{$password_strength()}}', example: '{{$password_strength()}}' },
  { name: 'generate_salt', display_name: '随机盐值', description: '生成随机盐值数据', category: 'encryption', hasParams: false, syntax: '{{$generate_salt()}}', example: '{{$generate_salt()}}' },

  // 字符工具
  { name: 'text_diff', display_name: '文本对比', description: '对比两段文本的差异', category: 'string', hasParams: false, syntax: '{{$text_diff()}}', example: '{{$text_diff()}}' },
  { name: 'regex_test', display_name: '正则测试', description: '测试正则表达式的匹配结果', category: 'string', hasParams: false, syntax: '{{$regex_test()}}', example: '{{$regex_test()}}' },
  { name: 'remove_whitespace', display_name: '去除空格换行', description: '去除字符串中的空格和换行符', category: 'string', hasParams: false, syntax: '{{$remove_whitespace()}}', example: '{{$remove_whitespace()}}' },
  { name: 'replace_string', display_name: '字符串替换', description: '替换字符串中的内容', category: 'string', hasParams: false, syntax: '{{$replace_string()}}', example: '{{$replace_string()}}' },
  { name: 'escape_string', display_name: '字符串转义', description: '将字符串进行转义处理', category: 'string', hasParams: false, syntax: '{{$escape_string()}}', example: '{{$escape_string()}}' },
  { name: 'unescape_string', display_name: '字符串反转义', description: '将转义字符串还原', category: 'string', hasParams: false, syntax: '{{$unescape_string()}}', example: '{{$unescape_string()}}' },
  { name: 'word_count', display_name: '字数统计', description: '统计字符串的字数和字符数', category: 'string', hasParams: false, syntax: '{{$word_count()}}', example: '{{$word_count()}}' },
  { name: 'case_convert', display_name: '大小写转换', description: '转换字符串的大小写', category: 'string', hasParams: false, syntax: '{{$case_convert()}}', example: '{{$case_convert()}}' },
  { name: 'string_format', display_name: '字符串格式化', description: '格式化字符串', category: 'string', hasParams: false, syntax: '{{$string_format()}}', example: '{{$string_format()}}' },

  // JSON工具
  { name: 'format_json', display_name: 'JSON格式化', description: '格式化或压缩JSON数据', category: 'json', hasParams: false, syntax: '{{$format_json()}}', example: '{{$format_json()}}' },
  { name: 'validate_json', display_name: 'JSON校验', description: '验证JSON格式的正确性', category: 'json', hasParams: false, syntax: '{{$validate_json()}}', example: '{{$validate_json()}}' },
  { name: 'json_diff_enhanced', display_name: 'JSON对比', description: '对比两个JSON数据的差异', category: 'json', hasParams: false, syntax: '{{$json_diff_enhanced()}}', example: '{{$json_diff_enhanced()}}' },
  { name: 'jsonpath_query', display_name: 'JSONPath查询', description: '使用JSONPath表达式查询JSON数据', category: 'json', hasParams: false, syntax: '{{$jsonpath_query()}}', example: '{{$jsonpath_query()}}' },
  { name: 'json_flatten', display_name: '扁平化JSON', description: '将嵌套JSON扁平化', category: 'json', hasParams: false, syntax: '{{$json_flatten()}}', example: '{{$json_flatten()}}' },
  { name: 'json_path_list', display_name: 'JSON路径', description: '列出JSON的所有路径', category: 'json', hasParams: false, syntax: '{{$json_path_list()}}', example: '{{$json_path_list()}}' },
  { name: 'json_to_xml', display_name: 'JSON转XML', description: '将JSON转换为XML格式', category: 'json', hasParams: false, syntax: '{{$json_to_xml()}}', example: '{{$json_to_xml()}}' },
  { name: 'xml_to_json', display_name: 'XML转JSON', description: '将XML转换为JSON格式', category: 'json', hasParams: false, syntax: '{{$xml_to_json()}}', example: '{{$xml_to_json()}}' },
  { name: 'json_to_yaml', display_name: 'JSON转YAML', description: '将JSON转换为YAML格式', category: 'json', hasParams: false, syntax: '{{$json_to_yaml()}}', example: '{{$json_to_yaml()}}' },
  { name: 'yaml_to_json', display_name: 'YAML转JSON', description: '将YAML转换为JSON格式', category: 'json', hasParams: false },

  // 专业工具 - 科学
  { name: 'science_chemical_element', display_name: '随机化学元素', description: '生成随机化学元素信息', category: 'professional', hasParams: false },
  { name: 'science_chemical_symbol', display_name: '随机化学元素符号', description: '生成随机化学元素符号', category: 'professional', hasParams: false },
  { name: 'science_chemical_name', display_name: '随机化学元素名称', description: '生成随机化学元素名称', category: 'professional', hasParams: false },
  { name: 'science_unit', display_name: '随机科学单位', description: '生成随机科学单位', category: 'professional', hasParams: false },
  // 专业工具 - 航空
  { name: 'airline_name', display_name: '随机航空公司', description: '生成随机航空公司名称', category: 'professional', hasParams: false },
  { name: 'airline_iata_code', display_name: '随机航司IATA代码', description: '生成随机航空公司IATA代码', category: 'professional', hasParams: false },
  { name: 'airline_airport', display_name: '随机机场信息', description: '生成随机机场完整信息', category: 'professional', hasParams: false },
  { name: 'airline_airport_name', display_name: '随机机场名称', description: '生成随机机场名称', category: 'professional', hasParams: false },
  { name: 'airline_airport_iata_code', display_name: '随机机场IATA代码', description: '生成随机机场IATA代码', category: 'professional', hasParams: false },
  { name: 'airline_aircraft_type', display_name: '随机机型', description: '生成随机飞机型号', category: 'professional', hasParams: false },
  // 专业工具 - 车辆
  { name: 'vehicle_manufacturer', display_name: '随机车辆制造商', description: '生成随机车辆制造商', category: 'professional', hasParams: false },
  { name: 'vehicle_model', display_name: '随机车辆型号', description: '生成随机车辆型号', category: 'professional', hasParams: false },
  { name: 'vehicle_type', display_name: '随机车辆类型', description: '生成随机车辆类型', category: 'professional', hasParams: false },
  { name: 'vehicle_fuel_type', display_name: '随机燃料类型', description: '生成随机车辆燃料类型', category: 'professional', hasParams: false },
  // 专业工具 - 数据库
  { name: 'database_type', display_name: '随机数据库类型', description: '生成随机数据库类型', category: 'professional', hasParams: false },
  { name: 'database_column', display_name: '随机数据库列名', description: '生成随机数据库列名', category: 'professional', hasParams: false },
  { name: 'database_engine', display_name: '随机数据库引擎', description: '生成随机数据库引擎', category: 'professional', hasParams: false },

  // 系统工具 - Git
  { name: 'git_branch', display_name: '随机Git分支名', description: '生成随机Git分支名称', category: 'system', hasParams: false },
  { name: 'git_commit_message', display_name: '随机Git提交信息', description: '生成随机Git提交信息', category: 'system', hasParams: false },
  { name: 'git_commit_sha', display_name: '随机Git Commit SHA', description: '生成随机Git commit SHA', category: 'system', hasParams: false },
  { name: 'git_short_commit_sha', display_name: '随机短Commit SHA', description: '生成随机短Git commit SHA(7位)', category: 'system', hasParams: false },
  // 系统工具 - 文件系统
  { name: 'system_file_name', display_name: '随机文件名', description: '生成随机文件名', category: 'system', hasParams: false },
  { name: 'system_file_ext', display_name: '随机文件扩展名', description: '生成随机文件扩展名', category: 'system', hasParams: false },
  { name: 'system_directory_path', display_name: '随机目录路径', description: '生成随机目录路径', category: 'system', hasParams: false },
  { name: 'system_file_path', display_name: '随机文件路径', description: '生成随机完整文件路径', category: 'system', hasParams: false },
  { name: 'system_mime_type', display_name: '随机MIME类型', description: '生成随机MIME类型', category: 'system', hasParams: false },
  // 系统工具 - 版本和平台
  { name: 'system_semver', display_name: '随机语义化版本号', description: '生成随机语义化版本号', category: 'system', hasParams: false },
  { name: 'system_platform', display_name: '随机平台名', description: '生成随机操作系统平台名', category: 'system', hasParams: false },
  { name: 'system_arch', display_name: '随机系统架构', description: '生成随机系统架构', category: 'system', hasParams: false },

  // 娱乐工具 - 音乐
  { name: 'music_genre', display_name: '随机音乐类型', description: '生成随机音乐类型', category: 'entertainment', hasParams: false },
  { name: 'music_song_name', display_name: '随机歌曲名', description: '生成随机歌曲名称', category: 'entertainment', hasParams: false },
  { name: 'music_artist', display_name: '随机艺术家', description: '生成随机艺术家/乐队名称', category: 'entertainment', hasParams: false },
  // 娱乐工具 - 动物
  { name: 'animal_type', display_name: '随机动物类型', description: '生成随机动物类型', category: 'entertainment', hasParams: false },
  { name: 'animal_name', display_name: '随机动物名称', description: '生成随机宠物名称', category: 'entertainment', hasParams: false },
  // 娱乐工具 - 食物
  { name: 'food_dish', display_name: '随机菜品', description: '生成随机菜品名称', category: 'entertainment', hasParams: false },
  { name: 'food_ingredient', display_name: '随机食材', description: '生成随机食材名称', category: 'entertainment', hasParams: false },
  { name: 'food_fruit', display_name: '随机水果', description: '生成随机水果名称', category: 'entertainment', hasParams: false },
  { name: 'food_vegetable', display_name: '随机蔬菜', description: '生成随机蔬菜名称', category: 'entertainment', hasParams: false },

  // Mock图片工具
  { name: 'image_url', display_name: '随机图片URL', description: '生成随机图片URL', category: 'mock_image', hasParams: false },
  { name: 'image_avatar', display_name: '随机头像URL', description: '生成随机头像URL', category: 'mock_image', hasParams: false },
  { name: 'image_placeholder', display_name: '生成占位图URL', description: '生成占位图URL', category: 'mock_image', hasParams: false }
]

// 根据分类筛选函数
const filteredFunctions = computed(() => {
  if (!selectedFunctionCategory.value) return []
  return dataFactoryFunctions.filter(func => func.category === selectedFunctionCategory.value)
})

// 判断当前选中的函数是否需要参数
const functionNeedsParams = computed(() => {
  const func = dataFactoryFunctions.find(f => f.name === selectedFunction.value)
  return func ? func.hasParams : false
})

// 获取当前选中的函数信息
const currentFunction = computed(() => {
  return dataFactoryFunctions.find(f => f.name === selectedFunction.value)
})

// 输入框 refs（用于光标位置插入）
const urlInputRef = ref(null)
const bodyInputRef = ref(null)

// 光标位置状态
const cursorPosition = ref({ type: '', index: -1, start: 0, end: 0 })

// 跨接口变量选择
const selectedPrevRequestId = ref(null)
const selectedVarType = ref('response.body')
const jsonPath = ref('')
const currentEditingRequestId = ref(null)

// 前置接口执行记录（用于变量选择器展示）
const selectedPrevRequestExecution = ref(null)
const loadingExecution = ref(false)
const executionError = ref('')

// 获取预览数据（用于 JSON 树形展示）
const previewData = computed(() => {
  if (!selectedPrevRequestExecution.value) return null

  const dataType = selectedVarType.value
  const requestData = selectedPrevRequestExecution.value.request_data || {}
  const responseData = selectedPrevRequestExecution.value.response_data || {}

  switch (dataType) {
    case 'request.body':
      return requestData.body || {}
    case 'request.headers':
      return requestData.headers || {}
    case 'request.params':
      return requestData.params || {}
    case 'response.body':
      return responseData.body || responseData.json || {}
    case 'response.headers':
      return responseData.headers || {}
    case 'response.status_code':
      return responseData.status_code
    case 'response.response_time':
      return selectedPrevRequestExecution.value.response_time
    default:
      return null
  }
})

// 获取所有实际请求（排除分组/文件夹节点）的扁平列表
const getAllRequestsFlat = (requests) => {
  const result = []
  const traverse = (items) => {
    items.forEach((item) => {
      // 如果有 request 对象，说明是实际请求
      if (item.request) {
        result.push({
          ...item,
          // 使用数据库的 order 字段，而不是列表索引
          displayOrder: item.order
        })
      }
      // 如果有子节点，递归遍历
      if (item.children && item.children.length > 0) {
        traverse(item.children)
      }
    })
  }
  traverse(requests)
  return result
}

// 计算总请求数（包含分组内的请求）
const totalRequestCount = computed(() => {
  if (!suite.value || !suite.value.suite_requests) return 0
  return getAllRequestsFlat(suite.value.suite_requests).length
})

// 获取前置接口列表（在同集合中，排在当前接口之前的接口）
const previousRequests = computed(() => {
  if (!suite.value || !suite.value.suite_requests || !currentEditingRequestId.value) return []

  // 获取扁平化的所有请求列表
  const flatRequests = getAllRequestsFlat(suite.value.suite_requests)
  const currentIndex = flatRequests.findIndex(r => r.id === currentEditingRequestId.value)
  if (currentIndex === -1) return []

  // 返回当前接口之前的所有接口
  return flatRequests.slice(0, currentIndex)
})

// 选中的前置接口
const selectedPrevRequest = computed(() => {
  return previousRequests.value.find(r => r.id === selectedPrevRequestId.value)
})

// 是否需要 JSON Path
const needsJsonPath = computed(() => {
  return selectedVarType.value.includes('body') || selectedVarType.value.includes('headers')
})

// 变量预览
const variablePreview = computed(() => {
  // 前置接口变量
  if (selectedVarCategory.value === 'prev') {
    if (!selectedPrevRequest.value) return '{{$.接口名.变量类型}}'
    const requestRef = selectedPrevRequest.value.alias || selectedPrevRequest.value.displayOrder
    if (needsJsonPath.value && jsonPath.value) {
      return `{{$.${requestRef}.${selectedVarType.value}.${jsonPath.value}}}`
    }
    return `{{$.${requestRef}.${selectedVarType.value}}}`
  }

  // 环境变量
  if (selectedVarCategory.value === 'env') {
    return varName.value ? `{{$env.${varName.value}}}` : '{{$env.变量名}}'
  } else if (selectedVarCategory.value === 'global') {
    return varName.value ? `{{$global.${varName.value}}}` : '{{$global.变量名}}'
  } else if (selectedVarCategory.value === 'dynamic') {
    if (!selectedFunction.value) return '{{$函数名(参数)}}'

    // 根据函数类型生成不同的参数格式
    switch (selectedFunction.value) {
      case 'random_string':
      case 'random_int':
        return `{{$${selectedFunction.value}(${funcParam1.value})}}`
      case 'random_float':
        return `{{$${selectedFunction.value}(${funcParamMin.value}, ${funcParamMax.value})}}`
      case 'random_date':
        const startDate = funcParamDateStart.value || '2024-01-01'
        const endDate = funcParamDateEnd.value || '2024-12-31'
        return `{{$${selectedFunction.value}('${startDate}', '${endDate}')}}`
      case 'random_ip_address':
        return `{{$${selectedFunction.value}('${funcParamIpType.value}')}}`
      case 'random_password':
        return `{{$${selectedFunction.value}(${funcParam1.value})}}`
      default:
        // 无参数函数
        return `{{$${selectedFunction.value}()}}`
    }
  }
  return ''
})

// 打开变量选择器
const openVariablePicker = (type, index = -1) => {
  variablePickerTarget.value = { type, index }

  // 记录光标位置
  let inputEl = null
  switch (type) {
    case 'url':
      inputEl = urlInputRef.value?.$el?.querySelector('input')
      break
    case 'header':
      // 对于 header 和 param，通过 document.querySelector 获取当前活动的输入框
      inputEl = document.activeElement
      break
    case 'param':
      inputEl = document.activeElement
      break
    case 'body':
      inputEl = bodyInputRef.value?.$el?.querySelector('textarea')
      break
  }

  if (inputEl && (inputEl.tagName === 'INPUT' || inputEl.tagName === 'TEXTAREA')) {
    cursorPosition.value = {
      type,
      index,
      start: inputEl.selectionStart || 0,
      end: inputEl.selectionEnd || 0
    }
  } else {
    // 如果无法获取光标位置，则默认在末尾插入
    let currentValue = ''
    switch (type) {
      case 'url':
        currentValue = editingRequestData.value.url || ''
        break
      case 'header':
        currentValue = index >= 0 ? (editingHeadersList.value[index]?.value || '') : ''
        break
      case 'param':
        currentValue = index >= 0 ? (editingParamsList.value[index]?.value || '') : ''
        break
      case 'body':
        currentValue = editingRequestData.value.bodyContent || ''
        break
    }
    cursorPosition.value = {
      type,
      index,
      start: currentValue.length,
      end: currentValue.length
    }
  }

  // 记录当前正在编辑的接口ID（用于获取前置接口）
  currentEditingRequestId.value = editingRequestData.value.id
  // 重置跨接口变量选择状态
  selectedPrevRequestId.value = null
  selectedVarType.value = 'response.body'
  jsonPath.value = ''
  // 默认选中"前置接口"（如果有前置接口），否则选中"环境变量"
  if (previousRequests.value.length > 0) {
    selectedVarCategory.value = 'prev'
  } else {
    selectedVarCategory.value = 'env'
    varName.value = ''
    selectedFunction.value = 'random_string'
    funcParam1.value = 8
  }
  showVariablePickerDialog.value = true
}

// 关闭变量选择器
const closeVariablePicker = () => {
  showVariablePickerDialog.value = false
  variablePickerTarget.value = { type: '', index: -1 }
  // 清空执行记录
  selectedPrevRequestExecution.value = null
  executionError.value = ''
  // 重置动态函数选择
  selectedFunctionCategory.value = ''
  selectedFunction.value = ''
  funcParam1.value = 8
  funcParamMin.value = 0
  funcParamMax.value = 100
  funcParamDateStart.value = ''
  funcParamDateEnd.value = ''
  funcParamIpType.value = 'ipv4'
  funcParamString.value = ''
}

// 前置接口变更时加载执行记录
const onPrevRequestChange = async () => {
  if (!selectedPrevRequest.value) return

  loadingExecution.value = true
  executionError.value = ''
  selectedPrevRequestExecution.value = null

  try {
    // request 可能是对象 {id: xxx, ...} 或直接的 ID
    let requestId = null
    const request = selectedPrevRequest.value?.request

    if (request) {
      if (typeof request === 'object') {
        requestId = request.id
      } else if (typeof request === 'number') {
        requestId = request
      } else if (typeof request === 'string') {
        requestId = parseInt(request, 10)
      }
    }

    if (!requestId) {
      executionError.value = '该接口没有关联的请求ID'
      return
    }

    // 确保 requestId 是数字
    const numericRequestId = Number(requestId)

    const response = await api.get('/api-testing/histories/latest/', {
      params: { request_id: numericRequestId }
    })

    selectedPrevRequestExecution.value = response.data
  } catch (error) {
    console.error('加载执行记录失败:', error)
    executionError.value = error.response?.data?.error || '加载执行记录失败，请确保该接口已执行过'
  } finally {
    loadingExecution.value = false
  }
}

// 变量类型变更时清空 JSON Path
const onVarTypeChange = () => {
  jsonPath.value = ''
}

// 获取变量预览的根路径
const getVariablePreviewRoot = () => {
  if (!selectedPrevRequest.value) return '$'
  const requestRef = selectedPrevRequest.value.alias || selectedPrevRequest.value.displayOrder
  return `$.${requestRef}.${selectedVarType.value}`
}

// 点击 JSON 字段复制路径（用于变量提取器）
const onJsonPathCopy = (fullPath) => {
  // 从完整路径中提取 JSON Path 部分
  // 例如: $.2.response.body.data.id -> data.id
  const match = fullPath.match(/\$\.\w+\.(request|response)\.(body|headers|params)\.?(.+)?/)
  if (match && match[3]) {
    jsonPath.value = match[3]
  } else if (match) {
    jsonPath.value = ''
  }
}

// 复制 JSON Path 到剪贴板（用于请求执行详情弹窗）
const copyJsonPathToClipboard = async (path) => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(path)
      ElMessage.success(`已复制 JSON Path: ${path}`)
    } else {
      // 降级方案：使用传统的复制方法
      const textarea = document.createElement('textarea')
      textarea.value = path
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      const success = document.execCommand('copy')
      document.body.removeChild(textarea)
      if (success) {
        ElMessage.success(`已复制 JSON Path: ${path}`)
      } else {
        ElMessage.error('复制失败，请手动复制')
      }
    }
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败，请手动复制')
  }
}

// 确认插入变量
const confirmVariableInsertion = () => {
  const variable = variablePreview.value
  const { type, index } = variablePickerTarget.value
  const { start, end } = cursorPosition.value

  switch (type) {
    case 'url': {
      const currentUrl = editingRequestData.value.url || ''
      editingRequestData.value.url = currentUrl.substring(0, start) + variable + currentUrl.substring(end)
      break
    }
    case 'header':
      if (index >= 0 && editingHeadersList.value[index]) {
        const currentValue = editingHeadersList.value[index].value || ''
        editingHeadersList.value[index].value = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
    case 'param':
      if (index >= 0 && editingParamsList.value[index]) {
        const currentValue = editingParamsList.value[index].value || ''
        editingParamsList.value[index].value = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
    case 'body': {
      const currentBody = editingRequestData.value.bodyContent || ''
      editingRequestData.value.bodyContent = currentBody.substring(0, start) + variable + currentBody.substring(end)
      break
    }
    case 'extractor_json_path':
      if (index >= 0 && editingExtractorsList.value[index]) {
        const currentValue = editingExtractorsList.value[index].json_path || ''
        editingExtractorsList.value[index].json_path = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
    case 'extractor_header_name':
      if (index >= 0 && editingExtractorsList.value[index]) {
        const currentValue = editingExtractorsList.value[index].header_name || ''
        editingExtractorsList.value[index].header_name = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
    case 'assertion_contains':
      if (index >= 0 && editingAssertionsList.value[index]) {
        const currentValue = editingAssertionsList.value[index].expected || ''
        editingAssertionsList.value[index].expected = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
    case 'assertion_json_path':
      if (index >= 0 && editingAssertionsList.value[index]) {
        const currentValue = editingAssertionsList.value[index].json_path || ''
        editingAssertionsList.value[index].json_path = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
    case 'assertion_json_expected':
      if (index >= 0 && editingAssertionsList.value[index]) {
        const currentValue = editingAssertionsList.value[index].expected || ''
        editingAssertionsList.value[index].expected = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
    case 'assertion_header_name':
      if (index >= 0 && editingAssertionsList.value[index]) {
        const currentValue = editingAssertionsList.value[index].header_name || ''
        editingAssertionsList.value[index].header_name = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
    case 'assertion_header_expected':
      if (index >= 0 && editingAssertionsList.value[index]) {
        const currentValue = editingAssertionsList.value[index].expected_value || ''
        editingAssertionsList.value[index].expected_value = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
    case 'assertion_equals':
      if (index >= 0 && editingAssertionsList.value[index]) {
        const currentValue = editingAssertionsList.value[index].expected || ''
        editingAssertionsList.value[index].expected = currentValue.substring(0, start) + variable + currentValue.substring(end)
      }
      break
  }

  closeVariablePicker()
}

// 复制变量到剪贴板
const copyVariableToClipboard = () => {
  navigator.clipboard.writeText(variablePreview.value).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// 编辑接口请求表单
const editFormRef = ref(null)
const editForm = ref({
  name: '',
  description: '',
  environment: null
})

const editRules = {
  name: [{ required: true, message: t('apiTesting.automation.inputSuiteName'), trigger: 'blur' }]
}

// 树形选择
const requestTreeRef = ref(null)

// 表格引用
const requestTableRef = ref(null)
const requestTreeProps = {
  children: 'children',
  label: 'name'
}

// 方法
const getMethodType = (method) => {
  const types = {
    'GET': 'success',
    'POST': 'info',
    'PUT': 'warning',
    'DELETE': 'danger',
    'PATCH': 'info'
  }
  return types[method?.toUpperCase()] || 'info'
}

const getStatusType = (status) => {
  const types = {
    'PENDING': 'info',
    'RUNNING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    'PENDING': t('apiTesting.automation.status.pending'),
    'RUNNING': t('apiTesting.automation.status.running'),
    'COMPLETED': t('apiTesting.automation.status.completed'),
    'FAILED': t('apiTesting.automation.status.failed')
  }
  return texts[status] || status
}

const getPassRate = (execution) => {
  if (!execution || execution.total_requests === 0) return 0
  return ((execution.passed_requests / execution.total_requests) * 100).toFixed(1)
}

const getAverageExecutionTime = (execution) => {
  if (!execution || execution.total_requests === 0) return '0ms'
  // 使用 start_time 和 end_time 计算总耗时
  const startTime = new Date(execution.start_time).getTime()
  const endTime = new Date(execution.end_time).getTime()
  const totalTime = endTime - startTime
  const avg = totalTime / execution.total_requests
  return `${avg.toFixed(0)}ms`
}

const getEnvironmentName = (environment) => {
  if (!environment) return t('apiTesting.automation.noEnvironment')
  if (typeof environment === 'object' && environment.name) {
    return environment.name
  }
  const env = environments.value.find(e => e.id === environment)
  return env ? env.name : t('apiTesting.automation.noEnvironment')
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

const getReviewStatusType = (status) => {
  switch (status) {
    case 'approved':
      return 'success'
    case 'rejected':
      return 'danger'
    case 'partial':
      return 'warning'
    default:
      return 'info'
  }
}

const getReviewStatusText = (status) => {
  switch (status) {
    case 'approved':
      return '已通过'
    case 'rejected':
      return '不通过'
    case 'partial':
      return '部分通过'
    default:
      return '待评审'
  }
}

const loadReviewData = async () => {
  const suiteId = suite.value?.id
  if (!suiteId) return

  reviewLoading.value = true
  try {
    const summaryResponse = await api.get(`/api-testing/test-suites/${suiteId}/review_summary/`)
    reviewSummary.value = summaryResponse.data
    reviewRecords.value = summaryResponse.data.records || []
  } catch (error) {
    console.error('加载评审数据失败:', error)
  } finally {
    reviewLoading.value = false
  }
}

const submitReview = async (status) => {
  const suiteId = suite.value?.id
  if (!suiteId) return

  try {
    await api.post(`/api-testing/test-suites/${suiteId}/review/`, {
      status: status,
      comment: status === 'rejected' ? rejectComment.value : ''
    })
    ElMessage.success(status === 'approved' ? '已通过评审' : '已拒绝')
    showRejectDialog.value = false
    rejectComment.value = ''
    await loadReviewData()
  } catch (error) {
    ElMessage.error('提交评审失败')
  }
}

const editReview = async (record) => {
  const suiteId = suite.value?.id
  if (!suiteId) return

  try {
    // 简单的方式：先问用户要修改成什么
    await ElMessageBox.confirm(
      '请选择新的评审结果',
      '修改评审',
      {
        confirmButtonText: '通过',
        cancelButtonText: '拒绝',
        type: 'warning',
        distinguishCancelAndClose: true
      }
    )
    // 用户点击"通过"
    await api.post(`/api-testing/test-suites/${suiteId}/review/`, {
      status: 'approved',
      comment: ''
    })
    ElMessage.success('已修改为通过')
    await loadReviewData()
  } catch (action) {
    // distinguishCancelAndClose: true 时，点击取消按钮会 reject 并返回 'cancel'
    if (action === 'cancel') {
      // 用户点击"拒绝"，弹出拒绝原因对话框
      rejectComment.value = record.comment || ''
      showRejectDialog.value = true
    }
    // 点击关闭按钮或按 ESC 时不执行任何操作
  }
}

const resetReviews = async () => {
  const suiteId = suite.value?.id
  if (!suiteId) return

  try {
    await ElMessageBox.confirm(
      '确定要重置评审状态吗？这将清除所有评审记录，需要所有人重新评审。',
      '确认重置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await api.post(`/api-testing/test-suites/${suiteId}/reset_reviews/`)
    ElMessage.success('评审状态已重置')
    await loadReviewData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重置评审失败')
    }
  }
}

const formatExecutionResults = (results) => {
  if (!results || !Array.isArray(results)) return []
  return results
}

const formatJson = (data) => {
  if (!data) return ''
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

const getRequestData = () => {
  if (!currentRequestDetail.value?.request_data) return ''
  const data = currentRequestDetail.value.request_data
  switch (activeRequestTab.value) {
    case 'body':
      return formatJson(data.body)
    case 'headers':
      return formatJson(data.headers)
    case 'params':
      return formatJson(data.params)
    default:
      return ''
  }
}

// 获取请求数据（原始格式，用于 JSON 树形展示）
const getRequestDataRaw = () => {
  if (!currentRequestDetail.value?.request_data) return ''
  const data = currentRequestDetail.value.request_data
  switch (activeRequestTab.value) {
    case 'body':
      return data.body || ''
    case 'headers':
      return data.headers || {}
    case 'params':
      return data.params || {}
    default:
      return ''
  }
}

// 获取请求 JSONPath 根路径（用于跨步骤引用）
const getRequestJsonPathRoot = () => {
  // 获取当前接口的别名或序号
  if (!currentRequestDetail.value) return '$.request.body'

  // 尝试从 suite_requests 中找到当前接口的别名
  const flatRequests = getAllRequestsFlat(suite.value?.suite_requests || [])
  const currentRequest = flatRequests.find(r => r.id === currentRequestDetail.value.request_id)
  const requestRef = currentRequest?.alias || currentRequest?.displayOrder || 'current'

  switch (activeRequestTab.value) {
    case 'body':
      return `$.${requestRef}.request.body`
    case 'headers':
      return `$.${requestRef}.request.headers`
    case 'params':
      return `$.${requestRef}.request.params`
    default:
      return `$.${requestRef}.request.body`
  }
}

const getResponseData = () => {
  if (!currentRequestDetail.value?.response_data) return ''
  const data = currentRequestDetail.value.response_data
  switch (activeResponseTab.value) {
    case 'body':
      return data.body || ''
    case 'headers':
      return formatJson(data.headers)
    case 'json':
      return formatJson(data.json)
    default:
      return ''
  }
}

// 获取响应数据（原始格式，用于 JSON 树形展示）
const getResponseDataRaw = () => {
  if (!currentRequestDetail.value?.response_data) return ''
  const data = currentRequestDetail.value.response_data
  switch (activeResponseTab.value) {
    case 'body':
      return data.body || ''
    case 'headers':
      return data.headers || {}
    case 'json':
      return data.json || {}
    default:
      return ''
  }
}

// 获取 JSONPath 根路径（用于跨步骤引用）
const getJsonPathRoot = () => {
  // 获取当前接口的别名或序号
  if (!currentRequestDetail.value) return '$.response.body'
  
  // 尝试从 suite_requests 中找到当前接口的别名
  const flatRequests = getAllRequestsFlat(suite.value?.suite_requests || [])
  const currentRequest = flatRequests.find(r => r.id === currentRequestDetail.value.request_id)
  const requestRef = currentRequest?.alias || currentRequest?.displayOrder || 'current'
  
  switch (activeResponseTab.value) {
    case 'body':
      return `$.${requestRef}.response.body`
    case 'headers':
      return `$.${requestRef}.response.headers`
    case 'json':
      return `$.${requestRef}.response.json`
    default:
      return `$.${requestRef}.response.body`
  }
}

const goBack = () => {
  router.push('/api-testing/automation')
}

const loadSuiteDetail = async () => {
  const suiteId = route.params.id
  if (!suiteId) return

  loading.value = true
  try {
    const response = await api.get(`/api-testing/test-suites/${suiteId}/`)
    suite.value = response.data
    // 同步本地套件请求列表
    localSuiteRequests.value = suite.value.suite_requests || []
    // 更新路由 query，添加测试套件名称，用于面包屑显示
    if (suite.value.name) {
      router.replace({
        query: { ...route.query, name: suite.value.name }
      })
    }
    await Promise.all([
      loadExecutions(),
      loadEnvironments(),
      loadReviewData()
    ])
    // 数据加载完成
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadSuiteDetail'))
  } finally {
    loading.value = false
  }
}

const loadEnvironments = async () => {
  try {
    const response = await api.get('/api-testing/environments/')
    const allEnvironments = response.data.results || response.data
    environments.value = allEnvironments.filter(env =>
      env.scope === 'GLOBAL' ||
      (env.scope === 'LOCAL' && (!suite.value?.project || env.project === suite.value.project))
    )
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadEnvironments'))
  }
}

const loadExecutions = async () => {
  if (!suite.value) return
  
  executionsLoading.value = true
  try {
    const response = await api.get('/api-testing/test-executions/', {
      params: { test_suite: suite.value.id }
    })
    executions.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadExecutionHistory'))
  } finally {
    executionsLoading.value = false
  }
}

const loadRequestTree = async () => {
  if (!suite.value?.project) return

  try {
    const collectionsRes = await api.get('/api-testing/collections/', {
      params: { project: suite.value.project }
    })
    const collections = collectionsRes.data.results || collectionsRes.data

    const requestsRes = await api.get('/api-testing/requests/')
    const requests = requestsRes.data.results || requestsRes.data

    requestTree.value = buildRequestTree(collections, requests)
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadRequestTree'))
  }
}

// 将场景请求树转换为带分组效果的树形数据
const buildSuiteRequestTree = (suiteRequests, suiteId, suiteName) => {
  if (!suiteRequests || suiteRequests.length === 0) {
    return []
  }

  const result = []
  
  suiteRequests.forEach((req, index) => {
    const nodeId = `${suiteId}_step_${req.id}`
    
    // 如果是分组类型或包含子节点，则作为父节点
    if (req.step_type === 'group' || (req.children && req.children.length > 0)) {
      const groupNode = {
        id: nodeId,
        name: req.override_name || req.request?.name || '分组',
        step_type: 'group',
        suite_id: suiteId,
        suite_name: suiteName,
        request_count: req.children?.length || 0,
        children: []
      }
      
      // 递归处理子节点
      if (req.children && req.children.length > 0) {
        req.children.forEach((child, childIndex) => {
          const childNodeId = `${suiteId}_step_${child.id}`
          groupNode.children.push({
            id: childNodeId,
            name: child.override_name || child.request?.name || '请求',
            method: child.request?.method,
            step_type: child.step_type || 'request',
            suite_id: suiteId,
            suite_name: suiteName,
            request: child.request
          })
        })
      }
      
      result.push(groupNode)
    } else {
      // 普通请求节点
      result.push({
        id: nodeId,
        name: req.override_name || req.request?.name || '请求',
        method: req.request?.method,
        step_type: req.step_type || 'request',
        suite_id: suiteId,
        suite_name: suiteName,
        request: req.request
      })
    }
  })
  
  return result
}

// 加载可引用的场景列表
const loadAvailableSuites = async () => {
  if (!suite.value?.project) return

  try {
    const response = await api.get('/api-testing/test-suites/', {
      params: {
        project: suite.value.project,
        exclude_self: suite.value.id
      }
    })
    const suites = response.data.results || response.data
    // 过滤掉当前场景，并构建带分组效果的树形数据
    availableSuites.value = suites
      .filter(s => s.id !== suite.value.id)
      .map(s => {
        const requestCount = s.suite_requests?.length || 0
        const children = buildSuiteRequestTree(s.suite_requests, s.id, s.name)
        return {
          ...s,
          request_count: requestCount,
          children: children
        }
      })
  } catch (error) {
    console.error('加载场景列表失败:', error)
    availableSuites.value = []
  }
}

// 场景选择处理
const onSuiteCheck = (data, checked) => {
  selectedSuiteIds.value = checked.checkedKeys
}

const buildRequestTree = (collections, requests) => {
  const map = {}
  const roots = []
  
  collections.forEach(collection => {
    map[collection.id] = {
      ...collection,
      type: 'collection',
      children: []
    }
  })
  
  collections.forEach(collection => {
    if (collection.parent && map[collection.parent]) {
      map[collection.parent].children.push(map[collection.id])
    } else {
      roots.push(map[collection.id])
    }
  })
  
  requests.forEach(request => {
    if (map[request.collection]) {
      map[request.collection].children.push({
        ...request,
        type: 'request',
        id: `request_${request.id}`
      })
    }
  })
  
  return roots
}

const runTestSuite = async () => {
  if (!suite.value) return
  
  running.value = true
  try {
    const response = await api.post(`/api-testing/test-suites/${suite.value.id}/execute/`)
    currentExecution.value = response.data
    showExecutionDialog.value = true
    await loadExecutions()
    ElMessage.success(t('apiTesting.messages.success.suiteExecuted'))
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.executeSuite'))
  } finally {
    running.value = false
  }
}

const editSuite = () => {
  if (!suite.value) return
  
  editForm.value.name = suite.value.name
  editForm.value.description = suite.value.description
  editForm.value.environment = suite.value.environment?.id || null
  showEditDialog.value = true
}

const duplicateSuite = async () => {
  if (!suite.value) return
  
  try {
    const newSuite = {
      name: `${suite.value.name} - ${t('apiTesting.common.copyText')}`,
      description: suite.value.description,
      project: suite.value.project,
      environment_id: suite.value.environment?.id || null
    }
    await api.post('/api-testing/test-suites/', newSuite)
    ElMessage.success(t('apiTesting.messages.success.copy'))
    goBack()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.copyFailed'))
  }
}

const submitEditForm = async () => {
  if (!editFormRef.value || !suite.value) return

  const valid = await editFormRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const submitData = {
      name: editForm.value.name,
      description: editForm.value.description,
      project: suite.value.project
    }

    await api.put(`/api-testing/test-suites/${suite.value.id}/`, submitData)
    ElMessage.success(t('apiTesting.messages.success.suiteUpdated'))
    showEditDialog.value = false
    await loadSuiteDetail()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.updateFailed'))
  } finally {
    submitting.value = false
  }
}

const resetEditForm = () => {
  editForm.value = {
    name: '',
    description: '',
    environment: null
  }
  editFormRef.value?.resetFields()
}

// 处理环境变更
const handleEnvironmentChange = async (envId) => {
  if (!suite.value) return

  try {
    const submitData = {
      name: suite.value.name,
      description: suite.value.description,
      project: suite.value.project,
      environment_id: envId
    }

    await api.put(`/api-testing/test-suites/${suite.value.id}/`, submitData)
    ElMessage.success(t('apiTesting.messages.success.suiteUpdated'))
    await loadSuiteDetail()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.updateFailed'))
    // 恢复原值
    await loadSuiteDetail()
  }
}

const showAddRequest = async () => {
  // 重置状态
  addStepTab.value = 'request'
  selectedSuiteIds.value = []

  await Promise.all([
    loadRequestTree(),
    loadAvailableSuites()
  ])

  showAddRequestDialog.value = true

  // 默认不选中任何接口（包括已添加的）
  nextTick(() => {
    setTimeout(() => {
      if (requestTreeRef.value) {
        requestTreeRef.value.setCheckedKeys([], false)
      }
    }, 200)
  })
}

const onRequestCheck = () => {
  // 请求选择变化处理
}

const addSelectedRequests = async () => {
  if (!suite.value) return
  
  const checkedNodes = requestTreeRef.value.getCheckedNodes()
  const requestIds = checkedNodes
    .filter(node => node.type === 'request')
    .map(node => node.id.replace('request_', ''))

  if (requestIds.length === 0) {
    ElMessage.warning(t('apiTesting.messages.warning.selectAtLeastOneRequest'))
    return
  }

  addingRequests.value = true
  try {
    const response = await api.post(`/api-testing/test-suites/${suite.value.id}/add-requests/`, {
      request_ids: requestIds
    })

    console.log('添加接口响应:', response.data)

    // 直接使用返回的套件数据更新列表
    if (response.data && response.data.suite) {
      suite.value = response.data.suite
      console.log('suite.value.suite_requests:', suite.value.suite_requests)
      // 同步更新本地套件请求列表
      localSuiteRequests.value = suite.value.suite_requests || []
      console.log('localSuiteRequests.value:', localSuiteRequests.value)
    }

    ElMessage.success(response.data.message || t('apiTesting.messages.success.addSuccess'))
    showAddRequestDialog.value = false
  } catch (error) {
    console.error('添加接口失败:', error)
    ElMessage.error(t('apiTesting.messages.error.addFailed'))
  } finally {
    addingRequests.value = false
  }
}

// 新的添加步骤方法（支持接口、场景和等待时间）
const addSelectedSteps = async () => {
  if (!suite.value) return
  
  // 根据当前 Tab 决定添加什么
  if (addStepTab.value === 'wait') {
    // 添加等待时间步骤
    if (!waitTimeConfig.value.wait_time || waitTimeConfig.value.wait_time < 0) {
      ElMessage.warning('请输入有效的等待时间')
      return
    }

    addingRequests.value = true
    try {
      // 获取当前最大的步骤编号
      const currentSteps = suite.value.suite_requests || []
      const maxStepNumber = currentSteps.length > 0 
        ? Math.max(...currentSteps.map(s => s.step_number || 0))
        : 0

      const response = await api.post(`/api-testing/test-suites/${suite.value.id}/add-wait-step/`, {
        wait_time: waitTimeConfig.value.wait_time,
        name: waitTimeConfig.value.name || '等待时间',
        step_number: maxStepNumber + 1
      })

      if (response.data && response.data.suite) {
        suite.value = response.data.suite
        // 同步更新本地套件请求列表
        localSuiteRequests.value = suite.value.suite_requests || []
        ElMessage.success('等待时间步骤添加成功')
        showAddRequestDialog.value = false
        // 重置配置
        waitTimeConfig.value = {
          wait_time: 1,
          name: '等待时间'
        }
      }
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.message || '添加等待时间步骤失败'
      ElMessage.error(errorMsg)
      console.error('添加等待时间步骤失败:', error)
    } finally {
      addingRequests.value = false
    }
    return
  }
  
  if (addStepTab.value === 'request') {
    // 添加接口
    const checkedNodes = requestTreeRef.value?.getCheckedNodes() || []
    console.log('addSelectedSteps checkedNodes:', checkedNodes)
    const requestIds = checkedNodes
      .filter(node => node.type === 'request')
      .map(node => node.id.replace('request_', ''))
    console.log('addSelectedSteps requestIds:', requestIds)

    if (requestIds.length === 0) {
      ElMessage.warning('请至少选择一个接口')
      return
    }

    addingRequests.value = true
    try {
      console.log('addSelectedSteps 发送请求:', { request_ids: requestIds })
      const response = await api.post(`/api-testing/test-suites/${suite.value.id}/add-requests/`, {
        request_ids: requestIds
      })

      console.log('addSelectedSteps 添加接口响应:', response.data)

      if (response.data && response.data.suite) {
        suite.value = response.data.suite
        console.log('addSelectedSteps suite.value.suite_requests:', suite.value.suite_requests)
        // 同步更新本地套件请求列表
        localSuiteRequests.value = suite.value.suite_requests || []
        console.log('addSelectedSteps localSuiteRequests.value:', localSuiteRequests.value)
      }

      ElMessage.success(response.data.message || '添加成功')
      showAddRequestDialog.value = false
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.message || '添加失败'
      ElMessage.error(errorMsg)
      console.error('添加接口失败:', error)
    } finally {
      addingRequests.value = false
    }
  } else {
    // 添加场景（作为分组）
    const checkedNodes = suiteTreeRef.value?.getCheckedNodes() || []
    const checkedKeys = suiteTreeRef.value?.getCheckedKeys() || []
    
    if (checkedNodes.length === 0) {
      ElMessage.warning('请至少选择一个场景或步骤')
      return
    }

    // 收集场景和选中的子项
    const suiteSelections = []
    const processedSuiteIds = new Set()
    
    // 辅助函数：递归收集节点及其所有子节点的ID
    const collectStepIds = (node, suiteId, resultSet) => {
      if (node.step_type && node.id) {
        const match = node.id.match(new RegExp(`^${suiteId}_step_(\\d+)$`))
        if (match) {
          resultSet.add(parseInt(match[1]))
        }
      }
      // 递归处理子节点
      if (node.children && node.children.length > 0) {
        node.children.forEach(child => collectStepIds(child, suiteId, resultSet))
      }
    }
    
    for (const node of checkedNodes) {
      if (!node.id) continue
      
      // 场景根节点（没有 step_type）
      if (!node.step_type) {
        if (!processedSuiteIds.has(node.id)) {
          suiteSelections.push({
            suite_id: node.id,
            selected_steps: null // null 表示选择整个场景
          })
          processedSuiteIds.add(node.id)
        }
      } else {
        // 子节点（分组或请求）
        const suiteId = node.suite_id
        if (suiteId && !processedSuiteIds.has(suiteId)) {
          // 收集该场景下所有选中的步骤ID（包括嵌套的子节点）
          const selectedStepsSet = new Set()
          
          checkedNodes
            .filter(n => n.suite_id === suiteId && n.step_type)
            .forEach(n => collectStepIds(n, suiteId, selectedStepsSet))
          
          const selectedSteps = Array.from(selectedStepsSet)
          
          if (selectedSteps.length > 0) {
            suiteSelections.push({
              suite_id: suiteId,
              selected_steps: selectedSteps
            })
            processedSuiteIds.add(suiteId)
          }
        }
      }
    }

    if (suiteSelections.length === 0) {
      ElMessage.warning('请至少选择一个场景或步骤')
      return
    }

    addingRequests.value = true
    try {
      const response = await api.post(`/api-testing/test-suites/${suite.value.id}/add-suites/`, {
        suite_selections: suiteSelections
      })

      if (response.data && response.data.suite) {
        suite.value = response.data.suite
        // 同步更新本地套件请求列表
        localSuiteRequests.value = suite.value.suite_requests || []
      }

      ElMessage.success(response.data.message || '添加场景成功')
      showAddRequestDialog.value = false
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.message || '添加场景失败'
      ElMessage.error(errorMsg)
      console.error('添加场景失败:', error)
    } finally {
      addingRequests.value = false
    }
  }
}

const updateRequestEnabled = async (suiteRequest) => {
  try {
    await api.put(`/api-testing/test-suite-requests/${suiteRequest.id}/`, {
      enabled: suiteRequest.enabled
    })
    // 重新加载套件详情以更新时间戳
    await loadSuiteDetail()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.updateFailed'))
    suiteRequest.enabled = !suiteRequest.enabled
  }
}

// 编辑接口请求
const editRequest = (suiteRequest) => {
  // 检查是否是等待时间步骤
  if (suiteRequest.step_type === 'wait') {
    editingRequestData.value = {
      id: suiteRequest.id,
      step_type: 'wait',
      name: suiteRequest.override_name || suiteRequest.name || '等待时间',
      method: 'GET',
      url: '',
      headers: {},
      params: {},
      body: {},
      bodyType: 'json',
      bodyContent: '',
      wait_time: suiteRequest.control_config?.wait_time || 1
    }
    editDrawerActiveTab.value = 'basic'
    showEditRequestDialog.value = true
    return
  }

  const request = suiteRequest.request || {}

  // 合并原始接口参数和覆盖参数（覆盖参数优先）
  const mergedHeaders = { ...(request.headers || {}), ...(suiteRequest.override_headers || {}) }
  const mergedParams = { ...(request.params || {}), ...(suiteRequest.override_params || {}) }

  // 确定使用哪个 body：优先使用覆盖的 body，否则使用原始接口的 body
  let mergedBody = suiteRequest.override_body
  if (!mergedBody || Object.keys(mergedBody).length === 0) {
    mergedBody = request.body || {}
  }

  // 初始化编辑数据
  editingRequestData.value = {
    id: suiteRequest.id,
    step_type: suiteRequest.step_type || 'request',
    name: suiteRequest.override_name || request.name || '',
    method: suiteRequest.override_method || request.method || 'GET',
    url: suiteRequest.override_url || request.url || '',
    headers: mergedHeaders,
    params: mergedParams,
    body: mergedBody,
    bodyType: 'json',
    bodyContent: '',
    wait_time: 1
  }
  
  // 初始化 body 内容
  const body = editingRequestData.value.body
  if (body && typeof body === 'object') {
    const bodyType = body['type']
    const bodyData = body['data']
    if (bodyType === 'json' || bodyType === 'raw') {
      editingRequestData.value.bodyType = bodyType
      editingRequestData.value.bodyContent = typeof bodyData === 'string' ? bodyData : JSON.stringify(bodyData, null, 2)
    } else {
      editingRequestData.value.bodyType = 'json'
      editingRequestData.value.bodyContent = JSON.stringify(body, null, 2)
    }
  } else if (body) {
    editingRequestData.value.bodyType = 'raw'
    editingRequestData.value.bodyContent = String(body)
  }
  
  // 初始化 headers 列表
  editingHeadersList.value = Object.entries(editingRequestData.value.headers || {}).map(([key, value]) => ({ key, value }))
  if (editingHeadersList.value.length === 0) {
    editingHeadersList.value.push({ key: '', value: '' })
  }
  
  // 初始化 params 列表
  editingParamsList.value = Object.entries(editingRequestData.value.params || {}).map(([key, value]) => ({ key, value }))
  if (editingParamsList.value.length === 0) {
    editingParamsList.value.push({ key: '', value: '' })
  }
  
  // 初始化提取变量列表 - 优先使用 suite_request 的 override_extractors，其次是 extracted_variables，最后是 request 的 variable_extractors
  let extractors = suiteRequest.override_extractors
  // 如果为空数组，则使用 extracted_variables
  if (!extractors || (Array.isArray(extractors) && extractors.length === 0)) {
    extractors = suiteRequest.extracted_variables
  }
  // 如果仍为空，则使用 request 的 variable_extractors
  if (!extractors || (Array.isArray(extractors) && extractors.length === 0) || (typeof extractors === 'object' && Object.keys(extractors).length === 0)) {
    extractors = request.variable_extractors
  }
  // 处理不同格式：如果是字典格式，转换为数组格式
  if (extractors && typeof extractors === 'object' && !Array.isArray(extractors)) {
    extractors = Object.entries(extractors).map(([key, value]) => ({
      name: key,
      variable_name: key,
      source: 'json_body',
      json_path: value
    }))
  }
  // 确保是数组类型
  if (!Array.isArray(extractors)) {
    extractors = []
  }
  editingExtractorsList.value = extractors.map(extractor => ({ ...extractor }))

  // 初始化断言列表 - 优先使用 suite_request 的 override_assertions，其次是 assertions，最后是 request 的 assertions
  let assertions = suiteRequest.override_assertions
  // 如果为空数组，则使用 assertions
  if (!assertions || (Array.isArray(assertions) && assertions.length === 0)) {
    assertions = suiteRequest.assertions
  }
  // 如果仍为空，则使用 request 的 assertions
  if (!assertions || (Array.isArray(assertions) && assertions.length === 0)) {
    assertions = request.assertions
  }
  // 确保是数组类型
  if (!Array.isArray(assertions)) {
    assertions = []
  }
  editingAssertionsList.value = assertions.map(assertion => ({ ...assertion }))

  // 重置测试执行相关数据
  editingTestResponse.value = null

  const method = suiteRequest.override_method || request.method || 'GET'
  editDrawerActiveTab.value = ['POST', 'PUT', 'PATCH'].includes(method) ? 'body' : 'basic'

  showEditRequestDialog.value = true
}

// Headers 操作
const addEditingHeader = () => editingHeadersList.value.push({ key: '', value: '' })
const removeEditingHeader = (index) => {
  editingHeadersList.value.splice(index, 1)
  if (editingHeadersList.value.length === 0) {
    editingHeadersList.value.push({ key: '', value: '' })
  }
}

// Params 操作
const addEditingParam = () => editingParamsList.value.push({ key: '', value: '' })
const removeEditingParam = (index) => {
  editingParamsList.value.splice(index, 1)
  if (editingParamsList.value.length === 0) {
    editingParamsList.value.push({ key: '', value: '' })
  }
}

// 提取变量操作
const addEditingExtractor = () => {
  editingExtractorsList.value.push({
    name: '',
    source: 'json_body',
    json_path: '',
    header_name: '',
    variable_name: ''
  })
}
const removeEditingExtractor = (index) => {
  editingExtractorsList.value.splice(index, 1)
}

// 断言操作
const addEditingAssertion = () => {
  editingAssertionsList.value.push({
    name: '',
    type: 'status_code',
    expected: 200,
    json_path: '',
    header_name: '',
    expected_value: ''
  })
}
const removeEditingAssertion = (index) => {
  editingAssertionsList.value.splice(index, 1)
}
const onEditingAssertionTypeChange = (assertion) => {
  assertion.expected = null
  assertion.json_path = ''
  assertion.header_name = ''
  assertion.expected_value = ''
  // 设置默认值
  if (assertion.type === 'status_code') {
    assertion.expected = 200
  } else if (assertion.type === 'response_time') {
    assertion.expected = 1000
  }
}

// JSON 语法高亮
const formatJSONWithSyntaxHighlight = (data) => {
  if (!data) return ''
  try {
    const json = typeof data === 'string' ? JSON.parse(data) : data
    const jsonStr = JSON.stringify(json, null, 2)
    return jsonStr
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/(".*?"):/g, '<span style="color: #881391;">$1</span>:')
      .replace(/: (".*?")/g, ': <span style="color: #1a1aa6;">$1</span>')
      .replace(/: (true|false)/g, ': <span style="color: #1c00cf;">$1</span>')
      .replace(/: (null)/g, ': <span style="color: #1c00cf;">$1</span>')
      .replace(/: (\d+)/g, ': <span style="color: #1c00cf;">$1</span>')
  } catch {
    return String(data)
  }
}

// 复制响应内容到剪贴板
const copyResponseToClipboard = async () => {
  if (!editingTestResponse.value) return
  try {
    const data = editingTestResponse.value.response_data?.json || editingTestResponse.value.response_data?.body
    const text = typeof data === 'object' ? JSON.stringify(data, null, 2) : String(data)
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 测试执行（用于AI断言生成）
const testExecuteForAIAssertion = async () => {
  if (!editingRequestData.value.url) {
    ElMessage.warning('请先填写请求URL')
    return
  }

  // 检查是否需要环境
  if (!editingRequestData.value.url.startsWith('http') && !suite.value?.environment) {
    ElMessage.warning('当前接口使用相对路径URL，但场景未配置环境，请先配置环境')
    return
  }

  testingForAssertion.value = true
  try {
    // 转换 headers
    const headers = {}
    editingHeadersList.value.forEach(item => {
      if (item.key.trim()) headers[item.key.trim()] = item.value
    })

    // 转换 params
    const params = {}
    editingParamsList.value.forEach(item => {
      if (item.key.trim()) params[item.key.trim()] = item.value
    })

    // 转换 body
    let body = null
    if (['POST', 'PUT', 'PATCH'].includes(editingRequestData.value.method)) {
      if (editingRequestData.value.bodyType === 'json') {
        try {
          body = JSON.parse(editingRequestData.value.bodyContent)
        } catch {
          body = editingRequestData.value.bodyContent
        }
      } else {
        body = editingRequestData.value.bodyContent
      }
    }

    // 获取环境ID
    const environmentId = suite.value?.environment?.id || suite.value?.environment

    // 发送测试请求
    const res = await api.post('/api-testing/requests/execute_single/', {
      method: editingRequestData.value.method,
      url: editingRequestData.value.url,
      headers: headers,
      params: params,
      body: body,
      environment_id: environmentId
    })

    editingTestResponse.value = res.data
    ElMessage.success('测试执行成功')
  } catch (error) {
    console.error('Test execute error:', error)
    ElMessage.error(error.response?.data?.error || '测试执行失败')
  } finally {
    testingForAssertion.value = false
  }
}

// AI生成断言（用于接口编辑）
const generateAIAssertionsForEditing = async () => {
  if (!editingTestResponse.value) {
    ElMessage.warning('请先执行测试获取响应数据')
    return
  }

  generatingAIAssertions.value = true

  // 显示加载提示
  const loadingMessage = ElMessage.info({
    message: 'AI正在分析响应数据并生成断言，请稍候...',
    duration: 0,
    showClose: true
  })

  try {
    const res = await api.post('/api-testing/requests/generate_assertions/', {
      status_code: editingTestResponse.value.status_code,
      response_body: editingTestResponse.value.response_data?.json || editingTestResponse.value.response_data?.body,
      response_headers: editingTestResponse.value.response_data?.headers || {},
      response_time: editingTestResponse.value.response_time
    })

    loadingMessage.close()

    if (res.data.assertions && res.data.assertions.length > 0) {
      // 将生成的断言添加到现有断言列表
      const newAssertions = res.data.assertions.map(assertion => ({
        name: assertion.name || 'AI生成断言',
        type: assertion.type || 'json_path',
        expected: assertion.expected,
        json_path: assertion.json_path || '',
        header_name: assertion.header_name || '',
        expected_value: assertion.expected_value || ''
      }))

      editingAssertionsList.value = [...editingAssertionsList.value, ...newAssertions]
      ElMessage.success(`成功生成 ${res.data.assertions.length} 个断言`)
    } else {
      ElMessage.warning('未能生成断言，请检查响应数据')
    }
  } catch (error) {
    console.error('Generate AI assertions error:', error)
    ElMessage.error(error.response?.data?.error || '生成断言失败，请稍后重试')
  } finally {
    generatingAIAssertions.value = false
    loadingMessage.close()
  }
}

// 获取预期值的占位符
const getExpectedPlaceholder = (assertion) => {
  if (assertion.expected === 'not_null') {
    return '不为空'
  } else if (assertion.expected === 'not_undefined') {
    return '不为undefined'
  } else if (assertion.expected === 'not_empty') {
    return '不为空'
  }
  return assertion.expected_display || '预期值'
}

// 保存接口编辑
const saveRequestEdit = async () => {
  if (!editingRequestData.value.id) return
  
  savingRequestEdit.value = true
  try {
    // 处理等待时间步骤
    if (editingRequestData.value.step_type === 'wait') {
      const updateData = {
        override_name: editingRequestData.value.name,
        control_config: {
          wait_time: editingRequestData.value.wait_time || 1
        }
      }
      
      await updateTestSuiteRequest(editingRequestData.value.id, updateData)
      ElMessage.success('保存成功')
      showEditRequestDialog.value = false
      // 重新加载套件详情
      await loadSuiteDetail()
      return
    }
    
    // 转换 headers
    const headers = {}
    editingHeadersList.value.forEach(item => {
      if (item.key.trim()) headers[item.key.trim()] = item.value
    })
    
    // 转换 params
    const params = {}
    editingParamsList.value.forEach(item => {
      if (item.key.trim()) params[item.key.trim()] = item.value
    })
    
    // 转换 body
    let body = {}
    if (['POST', 'PUT', 'PATCH'].includes(editingRequestData.value.method)) {
      if (editingRequestData.value.bodyType === 'json') {
        try {
          body = { type: 'json', data: JSON.parse(editingRequestData.value.bodyContent) }
        } catch {
          body = { type: 'raw', data: editingRequestData.value.bodyContent }
        }
      } else {
        body = { type: 'raw', data: editingRequestData.value.bodyContent }
      }
    }
    
    // 转换提取变量 - 过滤掉空名称的规则
    const extractors = editingExtractorsList.value.filter(item => item.name.trim()).map(item => ({
      name: item.name.trim(),
      source: item.source,
      json_path: item.json_path,
      header_name: item.header_name,
      variable_name: item.variable_name
    }))
    
    // 转换断言 - 过滤掉空名称的断言
    const assertions = editingAssertionsList.value.filter(item => item.name.trim()).map(item => ({
      name: item.name.trim(),
      type: item.type,
      expected: item.expected,
      json_path: item.json_path,
      header_name: item.header_name,
      expected_value: item.expected_value
    }))
    
    const updateData = {
      override_name: editingRequestData.value.name,
      override_method: editingRequestData.value.method,
      override_url: editingRequestData.value.url,
      override_headers: headers,
      override_params: params,
      override_body: body,
      extracted_variables: extractors,
      assertions: assertions
    }
    
    await updateTestSuiteRequest(editingRequestData.value.id, updateData)
    ElMessage.success('保存成功')
    showEditRequestDialog.value = false
    // 重新加载套件详情
    await loadSuiteDetail()
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  } finally {
    savingRequestEdit.value = false
  }
}

// 拖拽开始时的处理
const onDragStart = (evt) => {
  console.log('拖拽开始:', evt)
}

// 顶层拖拽排序处理 - 使用 @end 事件
const onTopLevelDragEnd = async (evt) => {
  console.log('拖拽结束:', evt)
  const { oldIndex, newIndex } = evt

  // 如果没有移动，直接返回
  if (oldIndex === newIndex) return

  // 获取移动的元素
  const element = localSuiteRequests.value[newIndex]

  // 先保存当前的本地状态，以便失败时恢复
  const previousRequests = [...localSuiteRequests.value]

  try {
    // 计算新的 order 值
    let newOrder
    const requests = localSuiteRequests.value

    if (newIndex === 0) {
      // 移动到第一位
      const firstOrder = requests[1]?.order || 1000
      newOrder = firstOrder - 100
    } else if (newIndex >= requests.length - 1) {
      // 移动到最后一位
      const lastOrder = requests[requests.length - 2]?.order || 0
      newOrder = lastOrder + 100
    } else {
      // 移动到中间位置，取前后两个 order 的平均值
      const prevOrder = requests[newIndex - 1]?.order || 0
      const nextOrder = requests[newIndex + 1]?.order || prevOrder + 200
      newOrder = (prevOrder + nextOrder) / 2
    }

    console.log('拖拽排序:', {
      id: element.id,
      name: element.override_name || element.request?.name,
      oldIndex,
      newIndex,
      newOrder: Math.round(newOrder)
    })

    // 更新后端 - 同时更新 order 和 parent_id (顶层没有 parent_id)
    const updateData = {
      order: Math.round(newOrder),
      parent_id: null
    }
    console.log('发送 PATCH 请求:', `/api-testing/test-suite-requests/${element.id}/`, updateData)

    const response = await api.patch(`/api-testing/test-suite-requests/${element.id}/`, updateData)
    console.log('PATCH 响应:', response.data)

    // 更新本地数据中的 order 值
    const updatedItem = localSuiteRequests.value.find(item => item.id === element.id)
    if (updatedItem) {
      updatedItem.order = Math.round(newOrder)
    }

    // 同步到 suite.value.suite_requests
    suite.value.suite_requests = [...localSuiteRequests.value]

    // 强制重新加载数据以确保排序正确
    await loadSuiteDetail()

    ElMessage.success(t('apiTesting.messages.success.orderUpdated'))
  } catch (error) {
    console.error('拖拽排序失败:', error)
    ElMessage.error(t('apiTesting.messages.error.orderUpdateFailed'))
    // 恢复本地顺序
    localSuiteRequests.value = previousRequests
    // 重新加载数据
    await loadSuiteDetail()
  }
}

// 顶层拖拽变化处理（统一处理所有拖拽情况）
const onTopLevelChange = async (evt) => {
  console.log('顶层拖拽变化:', evt)

  // 处理移动（同层级排序）
  if (evt.moved) {
    const { oldIndex, newIndex, element } = evt.moved
    console.log('同层级移动:', { oldIndex, newIndex, element })

    try {
      // 计算新的 order 值
      let newOrder
      const requests = localSuiteRequests.value

      if (newIndex === 0) {
        const firstOrder = requests[1]?.order || 1000
        newOrder = firstOrder - 100
      } else if (newIndex >= requests.length - 1) {
        const lastOrder = requests[requests.length - 2]?.order || 0
        newOrder = lastOrder + 100
      } else {
        const prevOrder = requests[newIndex - 1]?.order || 0
        const nextOrder = requests[newIndex + 1]?.order || prevOrder + 200
        newOrder = (prevOrder + nextOrder) / 2
      }

      // 发送 PATCH 请求更新后端
      await api.patch(`/api-testing/test-suite-requests/${element.id}/`, {
        order: Math.round(newOrder),
        parent_id: null
      })

      // 强制重新加载数据
      await loadSuiteDetail()

      ElMessage.success(t('apiTesting.messages.success.orderUpdated'))
    } catch (error) {
      console.error('同层级移动失败:', error)
      ElMessage.error(t('apiTesting.messages.error.orderUpdateFailed'))
      await loadSuiteDetail()
    }
  }

  // 处理从其他层级添加（从分组拖拽到顶层）
  if (evt.added) {
    const { newIndex, element } = evt.added
    console.log('从分组添加到顶层:', { newIndex, element })

    try {
      // 计算新的 order 值
      let newOrder
      const requests = localSuiteRequests.value

      if (newIndex === 0) {
        const firstOrder = requests[1]?.order || 1000
        newOrder = firstOrder - 100
      } else if (newIndex >= requests.length - 1) {
        const lastOrder = requests[requests.length - 2]?.order || 0
        newOrder = lastOrder + 100
      } else {
        const prevOrder = requests[newIndex - 1]?.order || 0
        const nextOrder = requests[newIndex + 1]?.order || prevOrder + 200
        newOrder = (prevOrder + nextOrder) / 2
      }

      // 发送 PATCH 请求更新后端（parent_id 设为 null）
      await api.patch(`/api-testing/test-suite-requests/${element.id}/`, {
        order: Math.round(newOrder),
        parent_id: null
      })

      // 强制重新加载数据
      await loadSuiteDetail()

      ElMessage.success(t('apiTesting.messages.success.orderUpdated'))
    } catch (error) {
      console.error('添加到顶层失败:', error)
      ElMessage.error(t('apiTesting.messages.error.orderUpdateFailed'))
      await loadSuiteDetail()
    }
  }
}

// 子节点顺序变化处理
const onChildOrderChange = async (data) => {
  const { parentId, children } = data

  try {
    // 批量更新子节点的顺序
    const updatePromises = children.map((child, index) => {
      return api.patch(`/api-testing/test-suite-requests/${child.id}/`, {
        order: (index + 1) * 100,
        parent_id: parentId
      })
    })

    await Promise.all(updatePromises)

    // 更新本地数据中的 order 值
    children.forEach((child, index) => {
      child.order = (index + 1) * 100
    })

    // 强制重新加载数据以确保排序正确
    await loadSuiteDetail()

    ElMessage.success(t('apiTesting.messages.success.orderUpdated'))
  } catch (error) {
    console.error('子节点排序失败:', error)
    ElMessage.error(t('apiTesting.messages.error.orderUpdateFailed'))
    // 恢复原顺序
    await loadSuiteDetail()
  }
}

const removeRequest = async (suiteRequest) => {
  try {
    await ElMessageBox.confirm(
      t('apiTesting.automation.confirmRemoveRequest'),
      t('apiTesting.automation.confirmRemove'),
      {
        confirmButtonText: t('apiTesting.common.confirm'),
        cancelButtonText: t('apiTesting.common.cancel'),
        type: 'warning'
      }
    )

    await api.delete(`/api-testing/test-suite-requests/${suiteRequest.id}/`)
    ElMessage.success(t('apiTesting.messages.success.removeSuccess'))
    await loadSuiteDetail()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('apiTesting.messages.error.removeFailed'))
    }
  }
}

// 一键清空所有接口
const clearAllRequests = async () => {
  if (!localSuiteRequests.value?.length) {
    ElMessage.warning('没有可删除的接口')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除所有 ${localSuiteRequests.value.length} 个接口吗？此操作不可恢复！`,
      '确认清空',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 收集所有需要删除的接口ID（包括子接口）
    const allRequestIds = []
    const collectIds = (requests) => {
      requests.forEach(req => {
        allRequestIds.push(req.id)
        if (req.children?.length) {
          collectIds(req.children)
        }
      })
    }
    collectIds(localSuiteRequests.value)

    console.log('一键清空，删除接口IDs:', allRequestIds)

    // 批量删除接口
    const deletePromises = allRequestIds.map(id =>
      api.delete(`/api-testing/test-suite-requests/${id}/`).catch(err => {
        console.error(`删除接口 ${id} 失败:`, err)
        return null
      })
    )

    await Promise.all(deletePromises)

    ElMessage.success(`已成功删除 ${allRequestIds.length} 个接口`)
    await loadSuiteDetail()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('一键清空失败:', error)
      ElMessage.error('一键清空失败，请稍后重试')
    }
  }
}

const viewExecutionDetail = (execution) => {
  currentExecution.value = execution
  showExecutionDialog.value = true
}

const viewRequestDetail = (requestResult) => {
  currentRequestDetail.value = requestResult
  showRequestDetailDialog.value = true
}

onMounted(async () => {
  // 获取当前用户信息
  try {
    const response = await api.get('/users/me/')
    currentUser.value = response.data
  } catch (error) {
    console.error('获取用户信息失败:', error)
  }
  loadSuiteDetail()
})
</script>

<style scoped lang="scss">
.automation-suite-detail {
  --primary-color: #7b42f6;
  --primary-light: #a78bfa;
  --primary-lighter: #c4b5fd;
  --primary-lightest: #f5f3ff;
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --text-primary: #1f2937;
  --text-secondary: #4b5563;
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

  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 20px 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #5a32a3;
}

.header-actions {
  display: flex;
  gap: 10px;

  .el-button {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

    .el-icon {
      margin-right: 6px;
    }

    &.el-button--primary {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
      border: none !important;
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
      }
    }

    &.el-button--success {
      background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
      border: none !important;
      box-shadow: 0 4px 12px rgba(82, 196, 26, 0.3);

      &:hover {
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(82, 196, 26, 0.4);
      }
    }

    &.el-button--danger {
      background: linear-gradient(135deg, #f5222d 0%, #ff4d4f 100%) !important;
      border: none !important;
      box-shadow: 0 4px 12px rgba(245, 34, 45, 0.3);

      &:hover {
        background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(245, 34, 45, 0.4);
      }
    }
  }
}

// 顶部评审状态徽章样式
.review-status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  margin-left: 10px;

  &.approved {
    background: rgba(82, 196, 26, 0.1);
    color: #52c41a;
  }

  &.rejected {
    background: rgba(245, 34, 45, 0.06);
    color: #ff4d4f;
  }

  &.pending {
    background: rgba(250, 140, 22, 0.1);
    color: #fa8c16;
  }
}

.suite-meta-info {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-left: 16px;
  font-size: 12px;
  color: #666;

  .meta-item {
    display: inline-flex;
    align-items: center;
  }
}

.content {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.suite-info-section {
  .info-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 24px;
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 16px;
    border-radius: 8px;
    transition: all 0.3s ease;

    background: #ffffff;
    border: 1px solid rgba(147, 112, 219, 0.15);
    border-left: 4px solid #7b42f6;

    &:nth-child(1) .info-label {
      color: #7b42f6;
    }

    &:nth-child(2) .info-label {
      color: #9370db;
    }

    &:nth-child(3) .info-label {
      color: #a888e0;
    }

    &:nth-child(4) .info-label {
      color: #b8a0e5;
    }

    &:nth-child(5) .info-label {
      color: #c8b8ea;
    }

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
  }

  .info-label {
    font-size: 13px;
    color: #8c8c8c;
    font-weight: 400;
  }

  .info-value {
    font-size: 15px;
    color: #333;
    font-weight: 500;
    word-break: break-all;
  }
}

.requests-section,
.executions-section,
.review-section {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.08);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.06),
              0 1px 3px rgba(0, 0, 0, 0.04);
  padding: 24px;
  transition: box-shadow 0.3s ease;

  &:hover {
    box-shadow: 0 8px 30px rgba(147, 112, 219, 0.1),
                0 2px 8px rgba(0, 0, 0, 0.04);
  }

  // Section header 优化
  .section-header {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #f0f0f0;

    h4 {
      font-size: 16px;
      font-weight: 600;
      color: #1a1a2e;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;

      &::before {
        content: '';
        width: 4px;
        height: 18px;
        background: linear-gradient(180deg, #7b42f6 0%, #5a32a3 100%);
        border-radius: 2px;
      }
    }
  }

  // 树形结构容器
  .requests-tree {
    border: 1px solid #f0f0f0;
    border-radius: 12px;
    overflow: hidden;
    background: #fafafa;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.02);

    // 拖拽相关样式
    .dragging-ghost {
      opacity: 0.5;
      background: #f0f9ff !important;
      border: 2px dashed #7b42f6;
    }

    .dragging-chosen {
      opacity: 0.9;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .dragging-drag {
      opacity: 1;
      background: #ffffff;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
      transform: scale(1.02);
    }
  }

  // 空状态样式
  .requests-empty {
    padding: 20px;

    :deep(.el-empty__description) {
      color: #8c8c8c;
      font-size: 14px;
      margin-top: 8px;
    }

    :deep(.el-empty__image) {
      opacity: 0.6;
    }
  }

  // 操作按钮容器
  .operation-btns,
  .review-actions {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }

  // 操作按钮样式 - 与列表页保持一致
  .action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 12px !important;
    border-radius: 6px;
    transition: all 0.3s ease;
    border: none !important;
    color: #ffffff !important;
    height: 28px;
    line-height: 1;

    // 编辑断言按钮 - 紫色
    &.edit-assertion-btn {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
      }
    }

    // 移除按钮 - 红色
    &.remove-btn {
      background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;

      &:hover {
        background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
      }
    }

    // 通过按钮 - 绿色
    &.approve-btn {
      background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;

      &:hover {
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
      }
    }

    // 拒绝按钮 - 红色
    &.reject-btn {
      background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;

      &:hover {
        background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
      }
    }

    // 修改评审按钮 - 紫色
    &.edit-review-btn {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
      }
    }

    // 重新发起评审按钮 - 蓝色
    &.reset-btn {
      background: linear-gradient(135deg, #409eff 0%, #1890ff 100%) !important;

      &:hover {
        background: linear-gradient(135deg, #69b1ff 0%, #40a9ff 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
      }
    }

    // 查看详情按钮 - 紫色
    &.view-detail-btn {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
      }
    }
  }
}

.review-section {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;

      h4 {
        margin: 0;
        color: #5a32a3;
        font-size: 16px;
        font-weight: 600;
      }
    }

    .reset-review-btn {
      color: #e6a23c;

      &:hover {
        color: #cf9236;
        background: rgba(230, 162, 60, 0.1);
      }
    }
  }

  .review-status {
    display: flex;
    align-items: center;
    gap: 8px;

    .review-count {
      font-size: 13px;
      color: #666;
    }
  }

  .pending-text {
    color: #909399;
    font-size: 13px;
  }

  .reviewed-text {
    color: #67c23a;
    font-size: 13px;
  }

}

// 拖拽手柄样式
.drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: grab;
  user-select: none;

  .drag-icon {
    font-size: 14px;
    color: #909399;
    transition: color 0.2s;
  }

  &:hover .drag-icon {
    color: #7b42f6;
  }

  span {
    font-size: 13px;
    color: #606266;
  }
}

.dragging {
  opacity: 0.7;
  background: #f5f3ff !important;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h4 {
    margin: 0;
    color: #5a32a3;
    font-size: 16px;
    font-weight: 600;
  }

  .el-button {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.25s ease;

    &.el-button--primary {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
      border: none !important;

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
      }
    }
  }
}

// 表格样式
:deep(.el-table) {
  border: none;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: none;
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

  .el-table__header-wrapper {
    background-color: #ffffff !important;
  }

  .el-table__header {
    background-color: #ffffff !important;

    th {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600;
      font-size: 14px;
      border-bottom: 1px solid #e9ecef;
      padding: 16px !important;
      vertical-align: middle !important;

      .cell {
        color: #5a32a3 !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-align: center !important;
      }
    }
  }

  // 序号列特殊样式 - 确保表头和内容都居中对齐
  th.el-table__cell:first-child,
  td.el-table__cell:first-child {
    text-align: center !important;

    .cell {
      text-align: center !important;
      justify-content: center !important;
      padding-left: 0 !important;
      padding-right: 0 !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
    }
  }

  // 序号列内容显示 - 使用更高的优先级
  :deep(.el-table__body) td.el-table__cell:first-child .cell {
    color: #333 !important;
    font-size: 14px !important;
    font-weight: normal !important;
  }

  // 序号列表头 - 使用更高的优先级
  :deep(.el-table__header) th.el-table__cell:first-child .cell {
    color: #5a32a3 !important;
    font-weight: 600 !important;
  }



  .el-table__row {
    transition: all 0.3s ease;
    background-color: #ffffff !important;

    &:hover {
      background-color: #f8f7ff !important;
    }

    &.el-table__row--striped {
      background-color: #fafaff !important;
    }
  }

  td {
    padding: 14px 16px;
    border-bottom: 1px solid #e9ecef;
    color: #333;
    font-size: 14px;
    font-weight: 400;
    vertical-align: middle !important;

    .cell {
      overflow: visible !important;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
    }
  }

  .el-table__empty-block {
    background: #ffffff !important;
  }

  // 方法标签样式 - 确保显示完整
  .method-tag {
    white-space: nowrap;
    overflow: visible;
  }

  // 方法徽章样式 - 参考 ProjectManagement.vue
  .method-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.3s ease;
    white-space: nowrap;
    overflow: visible;
    line-height: 1.5;
    height: 24px;

    &.get {
      background: #f6ffed;
      color: #52c41a;
    }

    &.post {
      background: #f5f3ff;
      color: #7b42f6;
    }

    &.put {
      background: #fff7e6;
      color: #fa8c16;
    }

    &.delete {
      background: #fff1f0;
      color: #f5222d;
    }

    &.patch {
      background: #f5f5f5;
      color: #8c8c8c;
    }

    &.wait {
      background: #fff7e6;
      color: #fa8c16;
    }
  }

  // 状态徽章样式 - 用于评审状态和执行状态
  .status-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 16px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.3s ease;
    white-space: nowrap;
    vertical-align: middle;

    // 评审状态
    &.approved {
      background: #f6ffed;
      color: #52c41a;
    }

    &.rejected {
      background: #fff2f0;
      color: #f5222d;
    }

    &.pending {
      background: #fff7e6;
      color: #fa8c16;
    }

    // 执行状态（小写）
    &.success,
    &.completed {
      background: #f6ffed;
      color: #52c41a;
    }

    &.failed {
      background: #fff2f0;
      color: #f5222d;
    }

    &.running,
    &.processing {
      background: #e6f4ff;
      color: #409eff;
    }

    // 执行状态（大写 - 执行历史用）
    &.completed {
      background: #f6ffed;
      color: #52c41a;
    }

    &.failed {
      background: #fff2f0;
      color: #f5222d;
    }

    &.running {
      background: #e6f4ff;
      color: #409eff;
    }

    &.pending {
      background: #fff7e6;
      color: #fa8c16;
    }
  }
}

// ==================== 添加步骤抽屉现代化样式 ====================

// 抽屉整体样式优化
:deep(.add-step-drawer) {
  .el-drawer__header {
    background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
    padding: 20px 24px;
    border-bottom: 1px solid rgba(123, 66, 246, 0.1);
    margin: 0;

    .el-drawer__title {
      font-size: 18px;
      font-weight: 600;
      color: #1a1a2e;
      letter-spacing: -0.3px;
    }

    .el-drawer__close-btn {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      color: #64748b;
      font-size: 18px;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

      &:hover {
        color: #7b42f6;
        background: rgba(123, 66, 246, 0.08);
        transform: rotate(90deg);
      }
    }
  }

  .el-drawer__body {
    padding: 0;
    background: #f8fafc;
  }

  .el-drawer__footer {
    padding: 16px 24px;
    background: #ffffff;
    border-top: 1px solid rgba(123, 66, 246, 0.08);
    display: flex;
    justify-content: flex-end;
    gap: 12px;

    .el-button {
      margin-left: 0 !important;
      padding: 10px 24px;
      font-weight: 500;
      border-radius: 8px;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

      &:not(.el-button--primary) {
        color: #64748b;
        border-color: #e2e8f0;

        &:hover {
          color: #7b42f6;
          border-color: #7b42f6;
          background: rgba(123, 66, 246, 0.04);
        }
      }

      &.el-button--primary {
        background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
        border: none;
        box-shadow: 0 4px 14px rgba(123, 66, 246, 0.35);

        &:hover {
          transform: translateY(-1px);
          box-shadow: 0 6px 20px rgba(123, 66, 246, 0.45);
        }

        &:active {
          transform: translateY(0);
        }
      }
    }
  }
}

.add-request-content {
  height: calc(100vh - 200px);
  overflow: hidden;

  .add-step-tabs {
    height: 100%;
    display: flex;
    flex-direction: column;

    // Tab 头部样式优化
    .el-tabs__header {
      margin: 0;
      background: #ffffff;
      border-bottom: 1px solid rgba(123, 66, 246, 0.08);
      padding: 0 24px;

      .el-tabs__nav-wrap::after {
        display: none;
      }

      .el-tabs__nav {
        gap: 8px;
      }

      .el-tabs__item {
        height: 48px;
        line-height: 48px;
        padding: 0 20px;
        font-size: 14px;
        font-weight: 500;
        color: #64748b;
        border-radius: 8px 8px 0 0;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

        &:hover {
          color: #7b42f6;
        }

        &.is-active {
          color: #7b42f6;
          font-weight: 600;
          background: linear-gradient(180deg, rgba(123, 66, 246, 0.06) 0%, transparent 100%);
        }

        &:focus.is-active.is-focus:not(:active) {
          box-shadow: none;
        }
      }

      .el-tabs__active-bar {
        height: 3px;
        background: linear-gradient(90deg, #7b42f6 0%, #a855f7 100%);
        border-radius: 3px 3px 0 0;
      }
    }

    .el-tabs__content {
      flex: 1;
      overflow-y: auto;
      padding: 0;

      .el-tab-pane {
        height: 100%;
        overflow-y: auto;
      }
    }
  }

  // 树形选择器容器
  .request-selector,
  .suite-selector {
    height: 100%;
  }

  .suite-selector {
    .empty-suites {
      padding: 60px 0;

      :deep(.el-empty__image) {
        filter: grayscale(0.3);
        opacity: 0.8;
      }

      :deep(.el-empty__description) {
        color: #94a3b8;
        font-size: 14px;
      }
    }

    .suite-tree-node {
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
      padding: 6px 8px;
      border-radius: 8px;
      transition: all 0.2s ease;

      .el-icon {
        color: #7b42f6;
        font-size: 16px;
      }

      .suite-request-count {
        color: #94a3b8;
        font-size: 12px;
        margin-left: auto;
        background: #f1f5f9;
        padding: 2px 10px;
        border-radius: 12px;
        font-weight: 500;
      }

      .node-name {
        flex: 1;
        font-size: 14px;
        color: #334155;
      }

      .group-name {
        color: #475569;
        font-weight: 600;
      }

      .request-name {
        color: #1e293b;
        font-weight: 500;
      }

      .group-badge {
        color: #7b42f6;
        font-size: 11px;
        background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
      }

      .method-tag {
        font-size: 10px;
        padding: 3px 8px;
        border-radius: 6px;
        color: white;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

        &.get { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); }
        &.post { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
        &.put { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
        &.delete { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
        &.patch { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
      }

      &.is-group {
        .el-icon {
          color: #f59e0b;
        }
      }

      &.is-request {
        padding-left: 12px;
      }

      &:hover {
        background: rgba(123, 66, 246, 0.04);
      }
    }
  }
}

// 请求树节点样式
.request-tree-node {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.2s ease;

  .el-icon {
    color: #7b42f6;
    font-size: 16px;
  }

  span:not(.method-tag) {
    font-size: 14px;
    color: #334155;
    font-weight: 500;
  }

  &:hover {
    background: rgba(123, 66, 246, 0.04);
  }
}

// 方法标签样式
.method-tag {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 6px;
  color: white;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-left: auto;

  &.get { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); }
  &.post { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
  &.put { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
  &.delete { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
  &.patch { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
  &.wait { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
}

// 等待时间配置样式
.wait-time-config {
  padding: 24px;

  .el-form {
    .el-form-item {
      margin-bottom: 20px;

      .el-form-item__label {
        font-weight: 500;
        color: #374151;
      }
    }
  }

  .wait-time-hint {
    margin-top: 24px;

    .hint-content {
      display: flex;
      align-items: center;
      gap: 8px;

      .el-icon {
        color: #7b42f6;
      }
    }
  }
}

// 树形组件样式优化
:deep(.add-step-drawer) {
  .el-tree {
    background: transparent;

    .el-tree-node {
      margin: 2px 0;

      &__content {
        height: 40px;
        border-radius: 8px;
        padding: 0 8px;
        transition: all 0.2s ease;

        &:hover {
          background: rgba(123, 66, 246, 0.06);
        }

        .el-checkbox {
          margin-right: 8px;

          &__inner {
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border-color: #d1d5db;
            transition: all 0.2s ease;

            &:hover {
              border-color: #7b42f6;
            }

            &::after {
              border-width: 2px;
              border-left: 0;
              border-top: 0;
              width: 4px;
              height: 8px;
              left: 50%;
              top: 45%;
              transform: translate(-50%, -50%) rotate(45deg);
            }
          }

          &__input.is-checked .el-checkbox__inner {
            background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
            border-color: #7b42f6;
          }

          &__input.is-indeterminate .el-checkbox__inner {
            background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
            border-color: #7b42f6;

            &::before {
              top: 8px;
            }
          }
        }

        .el-tree-node__expand-icon {
          color: #94a3b8;
          font-size: 14px;
          transition: all 0.2s ease;

          &.expanded {
            transform: rotate(90deg);
            color: #7b42f6;
          }

          &:hover {
            color: #7b42f6;
          }
        }
      }

      &.is-current {
        > .el-tree-node__content {
          background: rgba(123, 66, 246, 0.1);

          .request-tree-node span:not(.method-tag),
          .suite-tree-node .node-name {
            color: #7b42f6;
            font-weight: 600;
          }
        }
      }
    }

    // 子节点缩进优化
    .el-tree-node__children {
      padding-left: 12px;
    }
  }
}

.execution-detail {
  max-height: 70vh;
  overflow-y: auto;
}

/* 执行结果抽屉样式 - 参考 AutomationSuiteList.vue */
.execution-detail-drawer {
  padding: 0;

  /* 统计概览卡片 */
  .summary-cards {
    margin-bottom: 20px;

    .summary-card {
      display: flex;
      align-items: center;
      padding: 16px 20px;
      background: #ffffff;
      border: 1px solid rgba(147, 112, 219, 0.12);
      border-radius: 12px;
      box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
      transition: all 0.3s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(147, 112, 219, 0.12);
      }

      .card-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        border-radius: 10px;
        margin-right: 16px;
        background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);

        .el-icon {
          font-size: 24px;
          color: #7b42f6;
        }

        &.total {
          background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
          .el-icon { color: #7b42f6; }
        }
      }

      .card-content {
        flex: 1;

        .card-label {
          color: #8c8c8c;
          font-size: 13px;
          margin-bottom: 4px;
        }

        .card-value {
          color: #1f2937;
          font-size: 24px;
          font-weight: 600;
        }
      }

      &.success {
        .card-icon {
          background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
          .el-icon { color: #52c41a; }
        }
        .card-value { color: #52c41a; }
      }

      &.failed {
        .card-icon {
          background: linear-gradient(135deg, #fff2f0 0%, #ffccc7 100%);
          .el-icon { color: #f5222d; }
        }
        .card-value { color: #f5222d; }
      }

      &.primary {
        .card-icon {
          background: linear-gradient(135deg, #f9f0ff 0%, #efdbff 100%);
          .el-icon { color: #722ed1; }
        }
        .card-value { color: #722ed1; }
      }
    }
  }

  /* 结果表格区域 */
  .result-table-section {
    background: #ffffff;
    border: 1px solid rgba(147, 112, 219, 0.12);
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
    overflow: hidden;

    .section-header {
      padding: 16px 20px;
      background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
      border-bottom: 1px solid rgba(147, 112, 219, 0.12);

      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 0;
        color: #5a32a3;
        font-size: 15px;
        font-weight: 600;

        .el-icon {
          font-size: 18px;
          color: #7b42f6;
        }
      }
    }

    .table-wrapper {
      padding: 16px;
    }
  }
}

/* 执行结果旧样式兼容 */
.execution-summary {
  margin-bottom: 30px;
  padding: 24px;
  background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;

  :deep(.el-statistic) {
    .el-statistic__head {
      color: #5a32a3;
      font-weight: 500;
      margin-bottom: 8px;
    }

    .el-statistic__number {
      color: #7b42f6;
      font-weight: 600;
      font-size: 24px;
    }
  }
}

.execution-results h4 {
  margin: 0 0 15px 0;
  color: #5a32a3;
  font-weight: 600;
}

/* 请求详情对话框样式 */
.request-detail-dialog {
  max-height: 70vh;
  overflow-y: auto;
}

/* 请求详情抽屉样式 - 现代简洁设计 */
.request-detail-drawer {
  padding: 24px;
  min-height: 100%;

  /* 顶部状态栏 - 无边框设计 */
  .request-header {
    padding: 0 0 20px 0;
    margin-bottom: 20px;
    border-bottom: 1px solid rgba(147, 112, 219, 0.1);

    .request-title-row {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      flex-wrap: wrap;

      .request-name {
        font-size: 18px;
        font-weight: 600;
        color: #1a1a2e;
      }

      .method-tag {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;

        &.get {
          background: #e6f7ff;
          color: #1890ff;
        }

        &.post {
          background: #f6ffed;
          color: #52c41a;
        }

        &.put {
          background: #fff7e6;
          color: #fa8c16;
        }

        &.delete {
          background: #fff1f0;
          color: #f5222d;
        }

        &.patch {
          background: #e6fffb;
          color: #13c2c2;
        }
      }

      .status-tag {
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;

        &.success {
          background: #f6ffed;
          color: #52c41a;
        }

        &.failed {
          background: #fff1f0;
          color: #f5222d;
        }
      }

      .meta-tag {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;

        &.time-tag {
          background: #f0f5ff;
          color: #2f54eb;
        }

        &.code-tag {
          background: #f6ffed;
          color: #389e0d;
        }
      }
    }

    .request-url {
      font-size: 13px;
      color: #666;
      font-family: 'Courier New', Consolas, Monaco, monospace;
      word-break: break-all;
      padding: 8px 0;
    }
  }

  /* 错误横幅 - 简洁设计 */
  .error-banner {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 0;
    margin-bottom: 20px;
    border-bottom: 1px solid #ffccc7;

    .el-icon {
      font-size: 16px;
      color: #f5222d;
      margin-top: 2px;
      flex-shrink: 0;
    }

    span {
      font-size: 13px;
      color: #cf1322;
      line-height: 1.5;
      word-break: break-all;
      white-space: pre-wrap;
      overflow-wrap: break-word;
    }
  }

  /* 数据区域 - 现代卡片式设计 */
  .data-section {
    margin-bottom: 24px;

    /* 主标签 - 简洁文字切换 */
    .main-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 24px;

      .main-tab-btn {
        display: flex;
        align-items: center;
        padding: 10px 20px;
        border: none;
        border-radius: 8px;
        background: transparent;
        color: #666;
        font-size: 15px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;

        &:hover {
          color: #333;
          background: #f5f5f5;
        }

        &.active {
          background: #7b42f6;
          color: #fff;
        }
      }
    }

    /* 数据面板 - 无边框直接展示 */
    .data-panel {
      .panel-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;

        .sub-tabs {
          display: flex;
          gap: 4px;

          .sub-tab-btn {
            padding: 6px 14px;
            border: none;
            border-radius: 6px;
            background: transparent;
            color: #666;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;

            &:hover {
              color: #333;
              background: #f0f0f0;
            }

            &.active {
              background: #f0e6ff;
              color: #7b42f6;
            }
          }
        }

        .data-badge {
          display: none;
        }
      }

      .code-container {
        background: transparent !important;
        border: none !important;

        .json-path-hint {
          margin-bottom: 12px;

          .el-alert {
            padding: 8px 12px;

            .el-alert__title {
              font-size: 12px;
            }
          }
        }

        .code-block {
          margin: 0;
          padding: 0;
          font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', Consolas, Monaco, monospace;
          font-size: 13px;
          line-height: 1.7;
          color: #333;
          white-space: pre-wrap;
          word-wrap: break-word;
          background: transparent !important;
          border: none !important;
        }
      }
    }
  }

  /* 断言容器 - 在响应 Tab 内 */
  .assertions-container {
    .assertion-list {
      padding: 8px 0;

      .assertion-item {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 0;
        border-bottom: 1px solid #f0f0f0;
        font-size: 13px;

        &:last-child {
          border-bottom: none;
          margin-bottom: 0;
        }

        .el-icon {
          font-size: 16px;
          flex-shrink: 0;
        }

        .assertion-name {
          flex-shrink: 0;
          color: #333;
          max-width: 150px;
          word-break: break-all;
        }

        .assertion-detail {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          flex-wrap: wrap;

          .detail-item {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            border-radius: 4px;
            background: #f5f5f5;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;

            .label {
              color: #999;
              font-size: 11px;
            }

            .value {
              color: #333;
              font-weight: 500;

              &.null {
                color: #999;
                font-style: italic;
              }

              &.object {
                color: #1890ff;
              }
            }

            &.expected {
              background: #e6f7ff;
              .label { color: #1890ff; }
            }

            &.actual {
              background: #f6ffed;
              .label { color: #52c41a; }

              &.mismatch {
                background: #fff2f0;
                .label { color: #f5222d; }
                .value { color: #f5222d; }
              }
            }
          }

          .separator {
            color: #d9d9d9;
            font-size: 11px;
          }
        }

        .assertion-error {
          color: #f5222d;
          font-size: 12px;
          flex: 1;
          word-break: break-all;
          white-space: pre-wrap;
          overflow-wrap: break-word;
          line-height: 1.4;
        }

        &.passed {
          .el-icon {
            color: #52c41a;
          }
        }

        &.failed {
          .el-icon {
            color: #f5222d;
          }
        }
      }
    }
  }

  /* 变量区域 - 简洁列表设计 */
  .variables-section,
  .variables-container {
    .section-title-compact {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #5a32a3;
      border-bottom: 1px solid rgba(147, 112, 219, 0.1);

      .el-icon {
        font-size: 16px;
        color: #7b42f6;
      }
    }

    .variables-grid {
      padding: 12px 0;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px;

      .variable-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: 8px 0;
        border-bottom: 1px solid #f0f0f0;

        .var-key {
          font-size: 12px;
          color: #7b42f6;
          font-weight: 500;
        }

        .var-value {
          font-size: 13px;
          color: #333;
          word-break: break-all;
          font-family: 'Courier New', Consolas, Monaco, monospace;
        }
      }
    }
  }

  /* 变量提取容器 - Tab 内使用 */
  .variables-container {
    padding: 0;
    background: transparent;
    height: 100%;
    overflow-y: auto;

    .variables-grid {
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0;

      .variable-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: 12px 16px;
        border-bottom: 1px solid #f0f0f0;

        &:last-child {
          border-bottom: none;
        }

        .var-key {
          font-size: 13px;
          color: #7b42f6;
          font-weight: 600;
        }

        .var-value {
          font-size: 13px;
          color: #333;
          word-break: break-all;
          font-family: 'Courier New', Consolas, Monaco, monospace;
          line-height: 1.5;
        }
      }
    }
  }
}

.detail-section {
  margin-bottom: 20px;

  h4 {
    margin: 0 0 10px 0;
    color: #5a32a3;
    font-size: 14px;
    font-weight: 600;
    border-left: 3px solid #7b42f6;
    padding-left: 10px;
  }
}

.code-block {
  background: #f8f7ff;
  border: 1px solid rgba(147, 112, 219, 0.15);
  border-radius: 8px;
  padding: 12px;
  font-family: 'Courier New', Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #4a4a4a;
}

// 对话框样式
:deep(.el-dialog) {
  border-radius: 12px;
  box-shadow: 0 12px 24px rgba(147, 112, 219, 0.2);

  .el-dialog__header {
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    padding: 20px 24px;
    border-bottom: 1px solid #ebeef5;
    margin: 0;

    .el-dialog__title {
      font-size: 18px;
      font-weight: 600;
      color: #5a32a3;
    }
  }

  .el-dialog__body {
    padding: 24px;

    .el-form {
      .el-form-item {
        margin-bottom: 20px;

        .el-form-item__label {
          color: #5a32a3;
          font-weight: 500;
        }

        .el-input__wrapper,
        .el-select .el-input__wrapper {
          box-shadow: none;
          border-radius: 8px;
          border: 1px solid rgba(147, 112, 219, 0.2);
          background-color: transparent;

          &:hover,
          &.is-focus {
            border-color: #7b42f6;
          }
        }

        .el-textarea__inner {
          box-shadow: none;
          border-radius: 8px;
          border: 1px solid rgba(147, 112, 219, 0.2);
          background-color: transparent;
          padding: 8px 12px;
          line-height: 1.5;

          &:hover,
          &:focus {
            border-color: #7b42f6;
          }
        }
      }
    }
  }

  .el-dialog__footer {
    padding: 16px 24px 20px;
    border-top: 1px solid #ebeef5;
    background: #fafafa;

    .el-button {
      font-weight: 500;
      padding: 8px 20px;
      border-radius: 8px;

      &.el-button--primary {
        background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;

        &:hover {
          background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
        }
      }
    }
  }
}

// 状态徽章样式 - 参考 AutomationSuiteList.vue
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.3s ease;
  white-space: nowrap;

  &.success {
    background: #f6ffed;
    color: #52c41a;
  }

  &.failed {
    background: #fff2f0;
    color: #f5222d;
  }

  &.pending {
    background: #f5f5f5;
    color: #8c8c8c;
  }

  &.processing {
    background: #fff7e6;
    color: #fa8c16;
  }
}

// 自定义表格样式 - 参考 AutomationSuiteList.vue
.custom-table {
  border: none;
  border-radius: 8px;
  overflow: hidden;
  background-color: transparent !important;

  --el-color-primary: #7b42f6;
  --el-border-color: #e9ecef;
  --el-border-color-light: #e9ecef;
  --el-fill-color-light: #f8f7ff;
  --el-table-header-bg-color: #ffffff;
  --el-table-row-hover-bg-color: #f8f7ff;

  &::before {
    display: none;
  }

  :deep(th) {
    background-color: #ffffff !important;
    color: #5a32a3 !important;
    font-weight: 600;
    font-size: 13px;
    border-bottom: 1px solid #e9ecef;
    padding: 0 !important;
    height: 48px !important;
    text-align: center;
    vertical-align: middle !important;

    .cell {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      line-height: 1.4;
      white-space: normal;
      word-break: break-word;
    }
  }

  :deep(.el-table__row) {
    transition: all 0.3s ease;
    background-color: #ffffff !important;

    &:hover {
      background-color: #f8f7ff !important;
    }
  }

  :deep(td) {
    padding: 0 12px !important;
    border-bottom: 1px solid #e9ecef;
    color: #333;
    font-size: 13px;
    vertical-align: middle !important;
    height: 48px;

    .cell {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
    }
  }

  :deep(.el-table__empty-block) {
    padding: 40px 0;
  }
}

// 数据标签页样式
.data-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 0;
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    border-bottom: 1px solid rgba(147, 112, 219, 0.12);
  }

  :deep(.el-tabs__item) {
    color: #595959;
    font-weight: 500;

    &.is-active {
      color: #7b42f6;
      background: #ffffff;
    }
  }

  :deep(.el-tabs__active-bar) {
    background-color: #7b42f6;
  }

  :deep(.el-tabs__content) {
    padding: 16px;
    background: #fafbfc;
  }
}

// 抽屉样式
:deep(.el-drawer) {
  .el-drawer__header {
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    padding: 20px 24px;
    border-bottom: 1px solid #ebeef5;
    margin: 0;

    .el-drawer__title {
      font-size: 18px;
      font-weight: 600;
      color: #5a32a3;
    }

    .el-drawer__close-btn {
      color: #7b42f6;
      font-size: 18px;

      &:hover {
        color: #5a32a3;
      }
    }
  }

  .el-drawer__body {
    padding: 20px;
    background: #fafbfc;
    height: 100%;
    overflow-y: auto;
  }

  .el-drawer__footer {
    display: flex;
    justify-content: flex-start;
    gap: 4px;

    .el-button {
      margin-left: 0 !important;
    }
  }
}

// 详情抽屉特定样式
:deep(.detail-drawer) {
  .el-drawer__body {
    padding: 0;
    height: calc(100vh - 60px);
    overflow-y: auto;
  }
}

// 树形组件样式
:deep(.el-tree) {
  background: transparent;

  .el-tree-node__content {
    border-radius: 6px;
    margin: 2px 0;

    &:hover {
      background-color: #f8f7ff;
    }
  }

  .el-tree-node.is-current {
    > .el-tree-node__content {
      background-color: #f5f3ff;
      color: #7b42f6;
    }
  }
}

// Tab样式
:deep(.el-tabs) {
  .el-tabs__header {
    margin-bottom: 15px;
  }

  .el-tabs__item {
    color: #595959;
    font-weight: 500;

    &.is-active {
      color: #7b42f6;
    }
  }

  .el-tabs__active-bar {
    background-color: #7b42f6;
  }

  &.el-tabs--border-card {
    border: 1px solid rgba(147, 112, 219, 0.15);
    border-radius: 8px;

    .el-tabs__header {
      background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
      border-bottom: 1px solid rgba(147, 112, 219, 0.15);

      .el-tabs__item {
        &.is-active {
          background-color: #ffffff;
          border-bottom-color: #ffffff;
        }
      }
    }
  }
}

// Alert样式
:deep(.el-alert) {
  border-radius: 8px;

  &.el-alert--error {
    background: #fff1f0;
    border: 1px solid rgba(245, 34, 45, 0.2);
  }
}

// 断言编辑器样式
.assertions-editor {
  .assertions-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .request-name {
      font-size: 14px;
      font-weight: 600;
      color: #5a32a3;
    }

    .el-button--primary {
      --el-button-bg-color: #7c3aed;
      --el-button-border-color: #7c3aed;
      --el-button-hover-bg-color: #6d28d9;
      --el-button-hover-border-color: #6d28d9;
    }
  }

  .assertions-table {
    border: 1px solid rgba(147, 112, 219, 0.15);
    border-radius: 8px;
    overflow: hidden;
  }

  .assertions-table-header {
    display: flex;
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: #5a32a3;
    border-bottom: 1px solid rgba(147, 112, 219, 0.15);

    .col-name {
      width: 140px;
      padding-right: 12px;
    }

    .col-type {
      width: 140px;
      padding-right: 12px;
    }

    .col-params {
      flex: 1;
      padding-right: 12px;
    }

    .col-action {
      width: 50px;
      text-align: center;
    }
  }

  .assertions-table-body {
    .assertion-row {
      display: flex;
      padding: 12px 16px;
      border-bottom: 1px solid rgba(147, 112, 219, 0.1);
      align-items: center;
      background: #ffffff;

      &:last-child {
        border-bottom: none;
      }

      &:hover {
        background: #faf8ff;
      }

      .col-name {
        width: 140px;
        padding-right: 12px;
      }

      .col-type {
        width: 140px;
        padding-right: 12px;
      }

      .col-params {
        flex: 1;
        padding-right: 12px;

        .el-input,
        .el-input-number,
        .params-row {
          width: 100%;
        }

        .params-row {
          display: flex;
          gap: 8px;

          .el-input {
            flex: 1;
          }
        }
      }

      .col-action {
        width: 50px;
        text-align: center;
      }

      .el-input,
      .el-select,
      .el-input-number {
        width: 100%;
      }
    }
  }
}

// 响应式适配
@media screen and (max-width: 768px) {
  .automation-suite-detail {
    padding: 16px;
  }

  .header {
    flex-direction: column;
    gap: 16px;
    padding: 16px 20px;

    .header-left {
      width: 100%;
    }

    .header-actions {
      width: 100%;
      justify-content: flex-end;
    }
  }

  .page-title {
    font-size: 18px;
  }

  .suite-info-section,
  .requests-section,
  .executions-section,
  .review-section {
    padding: 16px;
  }

  :deep(.el-descriptions) {
    .el-descriptions__label {
      width: 100px !important;
    }
  }

  .assertions-editor {
    .assertions-table-header,
    .assertion-row {
      .col-name {
        width: 100px;
      }

      .col-type {
        width: 120px;
      }
    }
  }
}

@media screen and (max-width: 480px) {
  .automation-suite-detail {
    padding: 12px;
  }

  .header {
    padding: 14px 16px;
  }

  .page-title {
    font-size: 16px;
  }
}

// 执行环境下拉框白色背景
.env-select {
  :deep(.el-select__wrapper) {
    background-color: #ffffff !important;
  }
}

// 场景描述 textarea 样式与场景名称 input 一致
.suite-textarea {
  :deep(.el-textarea__inner) {
    box-shadow: none !important;
    border-radius: 8px !important;
    border: 1px solid rgba(147, 112, 219, 0.2) !important;
    background-color: transparent !important;
    padding: 8px 12px !important;
    line-height: 1.5 !important;

    &:hover,
    &:focus {
      border-color: #7b42f6 !important;
    }
  }
}

// 接口编辑抽屉样式
.edit-request-drawer {
  :deep(.el-drawer__header) {
    margin-bottom: 0;
    padding: 20px 24px;
    border-bottom: 1px solid #f0f0f0;

    .el-drawer__title {
      font-size: 18px;
      font-weight: 600;
      color: #1a1a2e;
      display: flex;
      align-items: center;
      gap: 10px;

      &::before {
        content: '';
        width: 4px;
        height: 20px;
        background: linear-gradient(180deg, #7b42f6 0%, #5a32a3 100%);
        border-radius: 2px;
      }
    }

    .el-drawer__close-btn {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      transition: all 0.2s ease;

      &:hover {
        background: #f5f5f5;
        color: #7b42f6;
      }
    }
  }

  :deep(.el-drawer__body) {
    padding: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    background: #fafafa;
  }

  :deep(.el-drawer__footer) {
    padding: 16px 24px;
    border-top: 1px solid #f0f0f0;
    background: #ffffff;
    display: flex;
    justify-content: flex-start;
    gap: 4px;

    .el-button {
      margin-left: 0 !important;
    }
  }

  .drawer-tabs {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;

    :deep(.el-tabs__header) {
      margin: 0;
      background: #ffffff;
      border-bottom: 1px solid #f0f0f0;
      padding: 0 24px;

      .el-tabs__nav {
        border: none;
      }

      .el-tabs__item {
        height: 48px;
        line-height: 48px;
        font-size: 14px;
        color: #595959;
        border: none;
        border-bottom: 2px solid transparent;
        transition: all 0.2s ease;
        padding: 0 20px;
        margin-right: 8px;

        &:hover {
          color: #7b42f6;
        }

        &.is-active {
          color: #7b42f6;
          border-bottom-color: #7b42f6;
          font-weight: 500;
        }
      }

      .el-tabs__active-bar {
        background: #7b42f6;
      }
    }

    :deep(.el-tabs__content) {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
    }

    :deep(.el-tab-pane) {
      height: 100%;
    }
  }

  .drawer-footer {
    display: flex;
    justify-content: flex-start;
    gap: 4px;

    .el-button {
      border-radius: 8px;
      padding: 10px 24px;
      font-weight: 500;
      transition: all 0.25s ease;
      margin-left: 0 !important;

      &.el-button--default {
        border-color: #d9d9d9;
        color: #595959;

        &:hover {
          border-color: #7b42f6;
          color: #7b42f6;
        }
      }

      &.el-button--primary {
        background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
        border: none;
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);

        &:hover {
          background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
          transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4);
        }
      }
    }
  }

  .key-value-editor {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #f0f0f0;

    .editor-header {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid #f5f5f5;

      .el-button {
        border-radius: 6px;
      }
    }

    .kv-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .kv-item {
      display: flex;
      gap: 12px;
      align-items: center;
      padding: 12px;
      background: #fafafa;
      border-radius: 8px;
      transition: all 0.2s ease;

      &:hover {
        background: #f5f0ff;
      }

      .kv-key {
        width: 200px;
      }

      .kv-value {
        flex: 1;
      }

      .el-button--danger {
        border-radius: 6px;
      }
    }
  }

  .body-editor {
    background: transparent;
    padding: 0;

    .body-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;

      .el-radio-group {
        .el-radio-button__inner {
          border-radius: 6px;
        }
      }
    }

    .body-input-wrapper {
      position: relative;
      background: #ffffff;
      border-radius: 8px;

      :deep(.el-textarea) {
        background: #ffffff;

        .el-textarea__inner {
          border-radius: 8px;
          font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
          font-size: 13px;
          line-height: 1.6;
          background: #ffffff;
          border: none;
          box-shadow: inset 0 0 0 1px #e8e8e8;
          padding: 16px;

          &:focus {
            box-shadow: inset 0 0 0 1px #7b42f6, 0 0 0 2px rgba(123, 66, 246, 0.1);
          }
        }
      }
    }
  }

  .el-form {
    background: #ffffff;
    border-radius: 12px;
    padding: 24px;
    border: 1px solid #f0f0f0;

    .el-form-item {
      margin-bottom: 20px;

      &:last-child {
        margin-bottom: 0;
      }

      .el-form-item__label {
        color: #262626;
        font-weight: 500;
      }

      .el-input__wrapper,
      .el-select .el-input__wrapper {
        border-radius: 8px;
        box-shadow: 0 0 0 1px #e4e7ed inset;

        &:hover,
        &.is-focus {
          box-shadow: 0 0 0 1px #7b42f6 inset;
        }
      }
    }
  }

  // 断言编辑器样式
  .assertions-editor {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #f0f0f0;

    .assertions-header {
      margin-bottom: 16px;
      display: flex;
      gap: 12px;
      padding-bottom: 16px;
      border-bottom: 1px solid #f5f5f5;

      .el-button {
        border-radius: 6px;
      }
    }

    .assertions-table {
      .assertions-table-header {
        display: flex;
        padding: 12px 16px;
        background: #fafafa;
        border-radius: 8px 8px 0 0;
        font-weight: 500;
        font-size: 13px;
        color: #595959;
        border-bottom: 1px solid #f0f0f0;
      }

      .assertions-table-body {
        > div {
          display: flex;
          padding: 12px 16px;
          align-items: center;
          border-bottom: 1px solid #f5f5f5;
          background: #ffffff;
          transition: all 0.2s ease;

          &:hover {
            background: #fafafa;
          }

          &:last-child {
            border-bottom: none;
            border-radius: 0 0 8px 8px;
          }

          > div {
            padding-right: 12px;

            &:last-child {
              padding-right: 0;
            }
          }

          .el-input__wrapper,
          .el-select .el-input__wrapper {
            border-radius: 6px;
          }

          .el-button--danger {
            border-radius: 6px;
          }
        }
      }
    }

    .el-empty {
      padding: 40px;
      color: #8c8c8c;

      .el-button {
        margin-top: 16px;
        border-radius: 6px;
      }
    }
  }

  // 提取规则编辑器样式
  .variable-extractors-editor {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #f0f0f0;

    .extractors-header {
      margin-bottom: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid #f5f5f5;

      .el-button {
        border-radius: 6px;
      }
    }

    .extractors-table {
      .extractors-table-header {
        display: flex;
        padding: 12px 16px;
        background: #fafafa;
        border-radius: 8px 8px 0 0;
        font-weight: 500;
        font-size: 13px;
        color: #595959;
        border-bottom: 1px solid #f0f0f0;
      }

      .extractors-table-body {
        > div {
          display: flex;
          padding: 12px 16px;
          align-items: center;
          border-bottom: 1px solid #f5f5f5;
          background: #ffffff;
          transition: all 0.2s ease;

          &:hover {
            background: #fafafa;
          }

          &:last-child {
            border-bottom: none;
            border-radius: 0 0 8px 8px;
          }

          > div {
            padding-right: 12px;

            &:last-child {
              padding-right: 0;
            }
          }

          .el-input__wrapper,
          .el-select .el-input__wrapper {
            border-radius: 6px;
          }

          .el-button--danger {
            border-radius: 6px;
          }
        }
      }
    }

    .el-empty {
      padding: 40px;
      color: #8c8c8c;

      .el-button {
        margin-top: 16px;
        border-radius: 6px;
      }
    }
  }
}

// 变量选择器样式
.variable-picker-content {
  padding: 8px 4px;

  .picker-section {
    margin-bottom: 28px;

    &:last-of-type {
      margin-bottom: 0;
    }

    .section-title {
      font-weight: 500;
      margin-bottom: 12px;
      color: #1f2937;
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 8px;

      .el-icon {
        color: #9ca3af;
        cursor: help;
        font-size: 14px;
      }
    }

    .var-hint {
      margin-top: 20px;
      color: #6b7280;
      font-size: 12px;
      font-family: 'SF Mono', Monaco, monospace;
      padding: 8px 12px;
      background: #f3f4f6;
      border-radius: 6px;
      border-left: 3px solid #7c3aed;
    }

    // 函数语法说明区域
    .function-syntax-section {
      margin-top: 16px;
      padding: 12px 16px;
      background: linear-gradient(135deg, #faf9ff 0%, #f5f3ff 100%);
      border-radius: 8px;
      border: 1px solid rgba(124, 58, 237, 0.15);

      .syntax-row {
        display: flex;
        align-items: center;
        margin-bottom: 8px;

        &:last-child {
          margin-bottom: 0;
        }

        .syntax-label {
          font-size: 13px;
          color: #6b7280;
          font-weight: 500;
          min-width: 48px;
          margin-right: 8px;
        }

        .syntax-code {
          font-family: 'SF Mono', Monaco, monospace;
          font-size: 13px;
          color: #7c3aed;
          background: #fff;
          padding: 4px 10px;
          border-radius: 4px;
          border: 1px solid rgba(124, 58, 237, 0.2);
          flex: 1;
        }

        .syntax-description {
          font-size: 13px;
          color: #4b5563;
          flex: 1;
          line-height: 1.5;
        }

        &.description-row {
          align-items: flex-start;
          padding-bottom: 8px;
          border-bottom: 1px dashed rgba(124, 58, 237, 0.15);
          margin-bottom: 10px;
        }
      }
    }

    .function-params {
      margin-top: 16px;
      padding: 16px;
      background: #fafafa;
      border-radius: 8px;

      .param-hint {
        margin-left: 12px;
        color: #6b7280;
        font-size: 13px;
      }

      .param-row {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;

        .param-separator {
          color: #9ca3af;
          font-weight: 500;
        }
      }
    }

    // 函数选项样式
    .function-option {
      display: flex;
      flex-direction: column;
      padding: 6px 0;

      .function-name {
        font-weight: 500;
        color: #1f2937;
        font-size: 13px;
      }

      .function-desc {
        font-size: 11px;
        color: #6b7280;
        margin-top: 2px;
      }
    }

    // 前置接口选择样式
    .no-prev-requests {
      margin-top: 16px;
    }

    .var-type-section,
    .json-path-section {
      margin-top: 20px;
    }

    // 执行结果预览区域
    .execution-preview-section {
      margin-top: 20px;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

      .section-title {
        padding: 14px 18px;
        background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 0;
        font-weight: 500;
      }

      .preview-data-container {
        max-height: 280px;
        overflow-y: auto;
        padding: 16px;
        background: #fff;
      }
    }

    .execution-loading,
    .execution-error {
      margin-top: 16px;
    }

    .request-option {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 4px 0;

      .request-order {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
        color: #fff;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        flex-shrink: 0;
      }

      .request-name {
        flex: 1;
        font-size: 13px;
        color: #374151;
      }
    }

    // 单选按钮组样式优化
    :deep(.el-radio-group) {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;

      .el-radio-button {
        .el-radio-button__inner {
          border-radius: 6px;
          border: 1px solid #e5e7eb;
          padding: 8px 16px;
          font-size: 13px;
          transition: all 0.2s ease;

          &:hover {
            border-color: #7c3aed;
            color: #7c3aed;
          }
        }

        &.is-active .el-radio-button__inner {
          background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
          border-color: #7c3aed;
          box-shadow: 0 2px 4px rgba(124, 58, 237, 0.2);
          color: #fff;

          &:hover {
            background: linear-gradient(135deg, #6d28d9 0%, #5b21b6 100%);
            border-color: #6d28d9;
            color: #fff;
          }
        }
      }
    }

    // 输入框样式优化
    :deep(.el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }

    // 下拉选择器样式
    :deep(.el-select) {
      width: 100%;

      .el-input__wrapper {
        border-radius: 8px;
      }
    }
  }

  .preview-section {
    padding: 16px 20px;
    background: linear-gradient(135deg, #faf9ff 0%, #f5f3ff 100%);
    border-radius: 10px;
    margin-top: 24px;
    border: 1px solid rgba(124, 58, 237, 0.1);

    .preview-row {
      display: flex;
      align-items: center;
      gap: 12px;

      .section-title {
        font-weight: 500;
        color: #1f2937;
        margin-bottom: 0;
        white-space: nowrap;
        font-size: 14px;
      }

      .preview-input {
        flex: 1;
      }
    }

    .section-title {
      font-weight: 500;
      color: #1f2937;
      margin-bottom: 12px;
    }

    .preview-input {
      :deep(.el-input__wrapper) {
        background: #fff;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        padding: 0;
        border: 1px solid #e5e7eb;
      }

      :deep(.el-input__inner) {
        font-family: 'SF Mono', Monaco, monospace;
        color: #7c3aed;
        font-weight: 500;
        font-size: 14px;
        padding: 0 12px;
        height: 40px;
      }

      :deep(.el-input-group__append) {
        background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
        border: none;
        border-radius: 0 7px 7px 0;
        padding: 0;
        overflow: hidden;

        .el-button {
          color: #fff;
          border: none;
          background: transparent;
          padding: 0 16px;
          height: 40px;
          margin: 0;
          display: flex;
          align-items: center;
          justify-content: center;

          &:hover {
            background: rgba(255, 255, 255, 0.1);
          }

          .el-icon {
            font-size: 16px;
          }
        }
      }
    }
  }

  // 抽屉底部按钮样式
  :deep(.el-drawer__footer) {
    display: flex;
    justify-content: flex-start;
    gap: 4px;

    .el-button {
      margin-left: 0 !important;
    }
  }
}

// 变量选择器抽屉特定样式 - 由于 append-to-body 需要全局样式
:global(.variable-picker-drawer .el-drawer__footer) {
  display: flex !important;
  justify-content: flex-start !important;
}

:global(.variable-picker-drawer .el-drawer__footer .el-button) {
  margin-left: 0 !important;
  border-radius: 8px !important;
  padding: 10px 24px !important;
  font-weight: 500 !important;
  transition: all 0.25s ease !important;
}

:global(.variable-picker-drawer .el-drawer__footer .el-button + .el-button) {
  margin-left: 4px !important;
}

:global(html body .variable-picker-drawer .el-drawer__footer .el-button--default) {
  --el-button-bg-color: #ffffff !important;
  --el-button-border-color: #d9d9d9 !important;
  --el-button-text-color: #595959 !important;
  --el-button-hover-bg-color: #f8f5ff !important;
  --el-button-hover-border-color: #7b42f6 !important;
  --el-button-hover-text-color: #7b42f6 !important;
  --el-button-active-bg-color: #f0e6ff !important;
  --el-button-active-border-color: #7b42f6 !important;
  --el-button-active-text-color: #7b42f6 !important;
  background-color: #ffffff !important;
  border-color: #d9d9d9 !important;
  color: #595959 !important;
}

:global(html body .variable-picker-drawer .el-drawer__footer .el-button--default:hover:not(.is-disabled):not([disabled])) {
  background-color: #f8f5ff !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

:global(html body .variable-picker-drawer .el-drawer__footer .el-button--default:focus:not(.is-disabled):not([disabled])) {
  background-color: #f8f5ff !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

:global(html body .variable-picker-drawer .el-drawer__footer .el-button--default:active:not(.is-disabled):not([disabled])) {
  background-color: #f0e6ff !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

/* 针对 btn-cancel 类的特殊处理 */
:global(html body .variable-picker-drawer .el-drawer__footer .el-button.btn-cancel) {
  --el-button-bg-color: #ffffff !important;
  --el-button-border-color: #d9d9d9 !important;
  --el-button-text-color: #595959 !important;
  --el-button-hover-bg-color: #f8f5ff !important;
  --el-button-hover-border-color: #7b42f6 !important;
  --el-button-hover-text-color: #7b42f6 !important;
  --el-button-active-bg-color: #f0e6ff !important;
  --el-button-active-border-color: #7b42f6 !important;
  --el-button-active-text-color: #7b42f6 !important;
  background-color: #ffffff !important;
  border-color: #d9d9d9 !important;
  color: #595959 !important;
}

:global(html body .variable-picker-drawer .el-drawer__footer .el-button.btn-cancel:hover:not(.is-disabled):not([disabled])) {
  background-color: #f8f5ff !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

:global(html body .variable-picker-drawer .el-drawer__footer .el-button.btn-cancel:focus:not(.is-disabled):not([disabled])) {
  background-color: #f8f5ff !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

:global(html body .variable-picker-drawer .el-drawer__footer .el-button.btn-cancel:active:not(.is-disabled):not([disabled])) {
  background-color: #f0e6ff !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

/* 编辑接口抽屉取消按钮样式 */
:global(html body .edit-request-drawer .el-drawer__footer .el-button.btn-cancel) {
  --el-button-bg-color: #ffffff !important;
  --el-button-border-color: #d9d9d9 !important;
  --el-button-text-color: #595959 !important;
  --el-button-hover-bg-color: #f8f5ff !important;
  --el-button-hover-border-color: #7b42f6 !important;
  --el-button-hover-text-color: #7b42f6 !important;
  --el-button-active-bg-color: #f0e6ff !important;
  --el-button-active-border-color: #7b42f6 !important;
  --el-button-active-text-color: #7b42f6 !important;
  background-color: #ffffff !important;
  border-color: #d9d9d9 !important;
  color: #595959 !important;
}

:global(html body .edit-request-drawer .el-drawer__footer .el-button.btn-cancel:hover:not(.is-disabled):not([disabled])) {
  background-color: #f8f5ff !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

:global(html body .edit-request-drawer .el-drawer__footer .el-button.btn-cancel:focus:not(.is-disabled):not([disabled])) {
  background-color: #f8f5ff !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

:global(html body .edit-request-drawer .el-drawer__footer .el-button.btn-cancel:active:not(.is-disabled):not([disabled])) {
  background-color: #f0e6ff !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

:global(.variable-picker-drawer .el-drawer__footer .el-button--primary) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;
}

:global(.variable-picker-drawer .el-drawer__footer .el-button--primary:hover) {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4) !important;
}
</style>
