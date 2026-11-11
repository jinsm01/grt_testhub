<template>
  <div class="page-container">
    <!-- 配置面板 - 参考 InterfaceList.vue 顶部样式 -->
    <div v-if="!showReportDetail" class="page-header">
      <div class="filter-section">
        <el-select
          v-if="isRunMode && scenarios.length > 0"
          v-model="creatorFilter"
          placeholder="创建人筛选"
          clearable
          style="width: 150px;"
        >
          <el-option v-for="c in uniqueCreators" :key="c" :label="c" :value="c" />
        </el-select>
        <el-select
          v-if="isRunMode && scenarios.length > 0"
          v-model="folderFilter"
          placeholder="所属目录筛选"
          clearable
          filterable
          style="width: 200px;"
        >
          <el-option v-for="f in uniqueFolders" :key="f" :label="f" :value="f" />
        </el-select>
      </div>
      <div class="header-actions">
        <el-button @click="configDrawerVisible = true">
          <el-icon style="margin-right: 4px;"><Setting /></el-icon>
          Apifox配置
          <el-tag v-if="config.project_id && config.environment_id && config.access_token" size="small" type="success" style="margin-left: 6px;">已配置</el-tag>
          <el-tag v-else size="small" type="warning" style="margin-left: 6px;">未配置</el-tag>
        </el-button>
        <el-button v-if="!isRunMode" @click="rulesDrawerVisible = true">
          <el-icon style="margin-right: 4px;"><List /></el-icon>
          规则查看
        </el-button>
        <el-button v-if="!isRunMode" @click="exemptionsDrawerVisible = true">
          <el-icon style="margin-right: 4px;"><CircleCheck /></el-icon>
          白名单
        </el-button>
        <el-button v-if="!isRunMode" type="primary" @click="generateReport" :loading="generating" :disabled="generating">
          <el-icon style="margin-right: 4px;"><VideoPlay /></el-icon>
          {{ generating ? '生成中...' : '开始检查' }}
        </el-button>
        <el-divider v-if="isRunMode" direction="vertical" />
        <el-tooltip v-if="isRunMode" :content="scenarioCacheTime ? `上次拉取: ${formatCacheTime(scenarioCacheTime)}` : '尚未拉取'" placement="top">
          <el-button @click="fetchScenarios" :loading="fetchingScenarios" :disabled="fetchingScenarios">
            <el-icon style="margin-right: 4px;"><Refresh /></el-icon>
            {{ fetchingScenarios ? '拉取中...' : (scenarios.length > 0 ? '刷新场景' : '拉取场景') }}
          </el-button>
        </el-tooltip>
        <el-button v-if="isRunMode" type="success" @click="runScenarios" :loading="running" :disabled="running || selectedScenarioIds.length === 0">
          <el-icon style="margin-right: 4px;"><VideoPlay /></el-icon>
          {{ running ? '运行中...' : `运行选中 (${selectedScenarioIds.length})` }}
        </el-button>
      </div>
    </div>

    <!-- 生成进度弹窗 -->
    <el-dialog
      v-model="progressDialogVisible"
      title="生成进度"
      width="480px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="!generating"
      destroy-on-close
    >
      <div class="progress-dialog-content">
        <el-alert
          v-if="taskError"
          :title="taskError"
          type="error"
          show-icon
          :closable="true"
          @close="taskError = ''"
        />
        <el-alert
          v-else-if="taskResult === 'completed'"
          title="报告生成成功！"
          type="success"
          show-icon
          :closable="true"
          @close="taskResult = ''"
        />
        <div v-if="generating" class="progress-bar-wrap">
          <div class="progress-info">
            <el-progress :percentage="100" :indeterminate="true" :duration="2" :stroke-width="8" />
          </div>
          <p class="progress-text">{{ progressText }}</p>
        </div>
      </div>
      <template #footer>
        <el-button v-if="!generating" @click="progressDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 运行进度抽屉 -->
    <el-drawer
      v-model="runProgressDialogVisible"
      :title="running ? '场景运行进度' : '运行报告详情'"
      direction="rtl"
      size="1000px"
      :close-on-click-modal="false"
      :close-on-press-escape="!running"
      :show-close="!running"
      :destroy-on-close="true"
      class="modern-drawer run-progress-drawer"
    >
      <div class="drawer-body progress-dialog-content">
        <el-alert
          v-if="runTaskError"
          :title="runTaskError"
          type="error"
          show-icon
          :closable="true"
          @close="runTaskError = ''"
        />
        <template v-else>
          <!-- 进度条 -->
          <div v-if="running" class="run-progress-wrap">
            <el-progress
              :percentage="runTotal > 0 ? Math.round((runCompleted / runTotal) * 100) : 0"
              :stroke-width="10"
              :status="runCompleted >= runTotal && runTotal > 0 ? 'success' : ''"
            />
            <p class="progress-text">{{ runProgressText }}</p>
            <p class="progress-sub-text">{{ runCompleted }} / {{ runTotal }} 个场景已完成</p>
          </div>
          <!-- 运行完成 - 实时结果 -->
          <div v-if="!running && runResults.length > 0" class="run-results-summary">
            <el-alert
              :title="runProgressText === '运行报告详情' ? '运行报告详情' : '运行完成！'"
              :type="runFailedCount > 0 ? 'warning' : 'success'"
              show-icon
              :closable="false"
            >
              <template #default>
                共 {{ runResults.length }} 个场景，{{ runPassedCount }} 通过，{{ runFailedCount }} 失败
              </template>
            </el-alert>
            <el-table :data="runResults" size="small" style="margin-top: 12px;" max-height="calc(100vh - 280px)">
              <el-table-column prop="scenario_name" label="场景名称" min-width="200" show-overflow-tooltip />
              <el-table-column label="结果" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.is_passed ? 'success' : 'danger'" size="small">
                    {{ row.is_passed ? '通过' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="请求" width="100" align="center">
                <template #default="{ row }">
                  {{ row.total_requests || 0 }} ({{ row.failed_requests || 0 }} 失败)
                </template>
              </el-table-column>
              <el-table-column label="断言" width="100" align="center">
                <template #default="{ row }">
                  {{ row.total_assertions || 0 }} ({{ row.failed_assertions || 0 }} 失败)
                </template>
              </el-table-column>
              <el-table-column label="错误" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <span v-if="row.error" style="color: #f56c6c; font-size: 12px;">{{ row.error }}</span>
                  <span v-else-if="row.failures && row.failures.length > 0" style="color: #f56c6c; font-size: 12px;">
                    {{ row.failures[0].message }}
                  </span>
                  <span v-else style="color: #999;">-</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" align="center">
                <template #default="{ row }">
                  <el-button size="small" class="action-btn view-btn" @click="viewRunDetail(row)">
                    <el-icon><View /></el-icon>
                    <span>详情</span>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </div>
      <template #footer>
        <div class="drawer-footer">
          <el-button v-if="!running" @click="runProgressDialogVisible = false">关闭</el-button>
          <el-button v-if="!running && runTestExecutionId" type="primary" @click="goToUnifiedReport">查看统一报告</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 运行详情抽屉 -->
    <el-drawer
      v-model="runDetailDrawerVisible"
      title="场景运行详情"
      direction="rtl"
      size="70%"
      :destroy-on-close="true"
      class="modern-drawer run-detail-drawer"
    >
      <div class="drawer-body" v-if="currentRunDetail">
        <!-- 场景概览 -->
        <div class="run-detail-header">
          <div class="run-detail-title">
            <el-tag :type="currentRunDetail.is_passed ? 'success' : 'danger'" size="large">
              {{ currentRunDetail.is_passed ? '通过' : '失败' }}
            </el-tag>
            <span class="scenario-detail-name">{{ currentRunDetail.scenario_name }}</span>
          </div>
          <div class="run-detail-stats">
            <span class="stat-item">请求: {{ currentRunDetail.total_requests || 0 }} ({{ currentRunDetail.failed_requests || 0 }} 失败)</span>
            <span class="stat-item">断言: {{ currentRunDetail.total_assertions || 0 }} ({{ currentRunDetail.failed_assertions || 0 }} 失败)</span>
            <span class="stat-item" v-if="currentRunDetail.response_avg">平均耗时: {{ currentRunDetail.response_avg }}ms</span>
          </div>
        </div>

        <!-- 错误信息（如果有） -->
        <el-alert
          v-if="currentRunDetail.error"
          :title="currentRunDetail.error"
          type="error"
          show-icon
          :closable="false"
          style="margin-bottom: 16px;"
        />
        <el-alert
          v-else-if="currentRunDetail.failures && currentRunDetail.failures.length > 0"
          type="error"
          show-icon
          :closable="false"
          style="margin-bottom: 16px;"
        >
          <template #title>有 {{ currentRunDetail.failures.length }} 个失败项</template>
          <div v-for="(f, i) in currentRunDetail.failures" :key="i" style="font-size: 12px; margin-top: 4px;">
            <strong v-if="f.step_name">{{ f.step_name }}:</strong> {{ f.message }}
          </div>
        </el-alert>

        <!-- 步骤详情 -->
        <div class="steps-section" v-if="currentRunDetail.steps && currentRunDetail.steps.length > 0">
          <h4 class="steps-title">执行步骤 ({{ currentRunDetail.steps.length }})</h4>
          <el-table :data="currentRunDetail.steps" style="width: 100%" class="custom-table" row-key="name">
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="step-expand-content">
                  <!-- 断言详情 -->
                  <div v-if="row.assertions && row.assertions.length > 0" class="step-sub-section">
                    <div class="sub-title">断言 ({{ row.assertions.length }})</div>
                    <div v-for="(a, i) in row.assertions" :key="i" class="assertion-item">
                      <el-tag :type="a.passed ? 'success' : 'danger'" size="small">
                        {{ a.passed ? '通过' : '失败' }}
                      </el-tag>
                      <span class="assertion-name">{{ a.name }}</span>
                      <span v-if="a.error" class="assertion-error">{{ a.error }}</span>
                    </div>
                  </div>
                  <!-- 请求体 -->
                  <div v-if="row.request_body" class="step-sub-section">
                    <div class="sub-title">请求体</div>
                    <pre class="code-block">{{ row.request_body }}</pre>
                  </div>
                  <!-- 响应体 -->
                  <div v-if="row.response_body" class="step-sub-section">
                    <div class="sub-title">响应体</div>
                    <pre class="code-block">{{ row.response_body }}</pre>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="结果" width="60" align="center">
              <template #default="{ row }">
                <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
                  {{ row.passed ? '通过' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="步骤名称" min-width="180" show-overflow-tooltip />
            <el-table-column label="方法" width="70" align="center">
              <template #default="{ row }">
                <el-tag :type="methodTagType(row.method)" size="small" effect="plain">{{ row.method }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="url" label="请求URL" min-width="300" show-overflow-tooltip />
            <el-table-column label="状态码" width="80" align="center">
              <template #default="{ row }">
                <span :style="{ color: statusCodeColor(row.status_code), fontWeight: '600' }">
                  {{ row.status_code || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="耗时" width="90" align="center">
              <template #default="{ row }">
                {{ row.response_time ? row.response_time + 'ms' : '-' }}
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 无步骤数据 -->
        <el-empty v-else description="无步骤详情数据" />
      </div>
    </el-drawer>

    <!-- 规则查看抽屉 -->
    <el-drawer
      v-model="rulesDrawerVisible"
      title="检查规则总览"
      direction="rtl"
      size="1200px"
      :close-on-press-escape="true"
      :destroy-on-close="false"
      @opened="loadRules"
      class="modern-drawer rules-drawer"
    >
      <div class="drawer-body">
        <!-- 详细结果表格 -->
        <div class="result-table-section">
          <div class="section-header">
            <h4 class="section-title">
              <el-icon><List /></el-icon>
              规则列表
            </h4>
            <div class="toolbar-info">
              <span>共 {{ checkRules.length }} 条检查规则，可根据需要启用或停用</span>
            </div>
          </div>
          <div class="table-wrapper">
            <el-table
              class="custom-table"
              :data="checkRules"
              v-loading="rulesLoading"
              empty-text="暂无检查规则"
            >
              <el-table-column type="index" label="序号" width="60" header-align="center" align="center" />
              <el-table-column prop="name" label="规则名称" min-width="130" align="center">
                <template #default="{ row }">
                  <span class="rule-name">{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="severity" label="严重程度" width="80" align="center">
                <template #default="{ row }">
                  <span class="status-badge" :class="`severity-${row.severityType}`">
                    {{ row.severity }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="desc" label="规则说明" min-width="340" show-overflow-tooltip align="center" />
              <el-table-column prop="enabled" label="状态" width="90" align="center">
                <template #default="{ row }">
                  <span class="status-badge" :class="row.enabled ? 'enabled' : 'disabled'">
                    {{ row.enabled ? '启用' : '停用' }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" align="center" fixed="right">
                <template #default="{ row }">
                  <el-switch
                    v-model="row.enabled"
                    :loading="row._toggling"
                    @change="(val) => toggleRule(row, val)"
                    class="modern-switch"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 白名单抽屉 -->
    <el-drawer
      v-model="exemptionsDrawerVisible"
      title="ID字段豁免列表"
      direction="rtl"
      size="1200px"
      :close-on-press-escape="true"
      :destroy-on-close="true"
      class="modern-drawer exemptions-drawer"
    >
      <div class="drawer-body">
        <!-- 统计卡片区域 -->
        <div class="stats-cards">
          <el-row :gutter="16">
            <el-col :xs="12" :sm="12" :md="6" :lg="6">
              <div class="stat-card total">
                <div class="stat-icon">
                  <el-icon><Document /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-label">总字段数</div>
                  <div class="stat-value">{{ exemptionStats.total }}</div>
                </div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" :lg="6">
              <div class="stat-card builtin">
                <div class="stat-icon">
                  <el-icon><Lock /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-label">内置字段</div>
                  <div class="stat-value">{{ exemptionStats.builtin }}</div>
                </div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" :lg="6">
              <div class="stat-card custom">
                <div class="stat-icon">
                  <el-icon><User /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-label">自定义字段</div>
                  <div class="stat-value">{{ exemptionStats.custom }}</div>
                </div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" :lg="6">
              <div class="stat-card enabled">
                <div class="stat-icon">
                  <el-icon><Check /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-label">已启用</div>
                  <div class="stat-value">{{ exemptionStats.enabled }}</div>
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
              详细列表
            </h4>
            <el-button type="primary" class="modern-btn primary" @click="openAddExemptionDialog">
              <el-icon><Plus /></el-icon>
              添加豁免
            </el-button>
          </div>
          <div class="table-wrapper">
            <el-table
              class="custom-table"
              :data="exemptionTableData"
              v-loading="exemptionLoading"
              empty-text="暂无豁免字段，点击「添加豁免」创建"
            >
              <el-table-column type="index" label="序号" width="70" header-align="center" align="center" />
              <el-table-column label="豁免ID字段" min-width="250" align="center">
                <template #default="{ row }">
                  <span>{{ row.field }}</span>
                </template>
              </el-table-column>
              <el-table-column label="豁免理由" min-width="240" show-overflow-tooltip>
                <template #default="{ row }">
                  <span v-if="row.reason" class="reason-text">{{ row.reason }}</span>
                  <span v-else class="reason-placeholder">未填写理由</span>
                </template>
              </el-table-column>
              <el-table-column label="添加人" width="100" align="center">
                <template #default="{ row }">
                  <span>{{ row.added_by || '-' }}</span>
                </template>
              </el-table-column>
            
              <el-table-column label="状态" width="120" align="center">
                <template #default="{ row }">
                  <span class="status-badge" :class="row._builtin ? 'enabled' : (row.enabled ? 'enabled' : 'disabled')">
                    {{ row._builtin ? '启用' : (row.enabled ? '启用' : '停用') }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="250" align="center" fixed="right">
                <template #default="{ row }">
                  <template v-if="!row._builtin">
                    <div class="action-buttons">
                      <el-button size="small" class="action-btn toggle-btn" @click="toggleExemption(row)">
                        <el-icon><Switch /></el-icon>
                        <span>{{ row.enabled ? '停用' : '启用' }}</span>
                      </el-button>
                      <el-button size="small" class="action-btn edit-btn" @click="openEditReasonDialog(row)">
                        <el-icon><Edit /></el-icon>
                        <span>编辑</span>
                      </el-button>
                      <el-button size="small" class="action-btn delete-btn" @click="deleteExemption(row)">
                        <el-icon><Delete /></el-icon>
                        <span>删除</span>
                      </el-button>
                    </div>
                  </template>
                  <span v-else class="text-gray">-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 添加/编辑豁免抽屉 -->
    <el-drawer
      v-model="exemptionDialogVisible"
      :title="editingExemption ? '编辑豁免理由' : '添加豁免字段'"
      direction="rtl"
      size="480px"
      :close-on-click-modal="false"
      :destroy-on-close="true"
      class="exemption-drawer"
    >
      <div class="drawer-form-content">
        <el-form :model="exemptionForm" label-width="90px" label-position="left">
          <el-form-item label="豁免字段" required>
            <div class="form-input-wrap">
              <el-input
                v-model="exemptionForm.field"
                placeholder="输入ID字段名，如 order_id"
                :disabled="!!editingExemption"
                clearable
                @keyup.enter="submitExemptionForm"
              />
              <div class="form-tip">匹配以 _id 或 Id 结尾的字段名（不区分大小写）</div>
            </div>
          </el-form-item>
          <el-form-item label="豁免理由" class="reason-form-item" required>
            <el-input
              v-model="exemptionForm.reason"
              type="textarea"
              :rows="3"
              placeholder="请说明为什么该字段不需要检查，如：该ID由系统自动生成，非外部传入"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="exemptionDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            @click="submitExemptionForm"
            :loading="exemptionSubmitting"
            :disabled="!exemptionForm.field.trim() || !exemptionForm.reason.trim()"
          >
            {{ editingExemption ? '保存' : '添加' }}
          </el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 报告详情 - 使用 Vue 组件渲染 -->
    <ReportDetail
      v-if="showReportDetail"
      :filename="currentReportName"
      @back="backToList"
    />

    <!-- 报告列表 / 场景运行 -->
    <div v-else class="card-container">
      <!-- 检查报告内容 -->
      <div v-if="!isRunMode">
          <!-- 加载状态 -->
          <div v-if="loadingReports" class="loading-state">
            <el-skeleton :rows="6" animated />
          </div>
          <!-- 空状态 -->
          <div v-else-if="reports.length === 0" class="empty-state">
            <el-empty description="暂无生成报告，请先配置并点击「开始检查」" />
          </div>
          <!-- 报告列表 -->
          <div v-else class="table-wrapper">
            <el-table
              ref="tableRef"
              :data="reports"
              v-loading="loadingReports"
              style="width: 100%"
              class="custom-table"
              :header-cell-style="{ background: '#ffffff', color: '#5a32a3', fontWeight: 600, fontSize: '14px' }"
            >
              <el-table-column label="序号" width="90" header-align="center" align="center">
                <template #default="{ $index }">
                  {{ $index + 1 }}
                </template>
              </el-table-column>
              <el-table-column label="报告文件" min-width="200" header-align="center" show-overflow-tooltip>
                <template #default="{ row }">
                  <div style="text-align: center; width: 100%;">
                    <span class="report-filename">{{ row.filename }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="场景总数" width="120" header-align="center" align="center">
                <template #default="{ row }">
                  <span>{{ row.total_scenarios !== null && row.total_scenarios !== undefined ? row.total_scenarios : '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="执行人" width="120" header-align="center" align="center">
                <template #default="{ row }">
                  <span>{{ row.executed_by || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="文件大小" width="120" header-align="center" align="center">
                <template #default="{ row }">
                  <span>{{ formatSize(row.size) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="生成时间" width="200" header-align="center" align="center">
                <template #default="{ row }">
                  <span>{{ formatTime(row.created_at) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="250" header-align="center" align="center" fixed="right">
                <template #default="{ row }">
                  <div class="action-buttons">
                    <el-button type="primary" size="small" class="action-btn view-btn" @click="viewReport(row)">
                      <el-icon><View /></el-icon>
                      <span>查看</span>
                    </el-button>
                    <el-button type="danger" size="small" class="action-btn delete-btn" @click="deleteReport(row)">
                      <el-icon><Delete /></el-icon>
                      <span>删除</span>
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
                :total="totalReports"
                layout="total, sizes, prev, pager, next, jumper"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
              />
            </div>
          </div>
      </div>

      <!-- 场景运行内容 -->
      <div v-else>
          <!-- 场景列表 -->
          <div v-if="scenarios.length > 0" class="table-wrapper">
            <el-table
              ref="scenarioTableRef"
              :data="pagedScenarios"
              v-loading="fetchingScenarios"
              style="width: 100%"
              class="custom-table"
              row-key="id"
              :header-cell-style="{ background: '#ffffff', color: '#5a32a3', fontWeight: 600, fontSize: '14px' }"
              @selection-change="handleSelectionChange"
            >
              <el-table-column type="selection" width="55" header-align="center" align="center" :reserve-selection="true" />
              <el-table-column prop="name" label="场景名称" min-width="150" show-overflow-tooltip header-align="center" align="left" />
              <el-table-column prop="folder_path" label="所属目录" min-width="150" show-overflow-tooltip header-align="center" align="center">
                <template #default="{ row }">
                  <span>{{ row.folder_path || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="step_count" label="步骤数" width="80" header-align="center" align="center" />
              <el-table-column label="最近运行" width="120" header-align="center" align="center">
                <template #default="{ row }">
                  <span class="status-badge" :class="row.last_run_status === 'passed' ? 'run-passed' : row.last_run_status === 'failed' ? 'run-failed' : 'run-pending'">
                    {{ row.last_run_status === 'passed' ? '通过' : row.last_run_status === 'failed' ? '失败' : '未运行' }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="creator" label="创建人" width="100" header-align="center" align="center">
                <template #default="{ row }">
                  <span>{{ row.creator || '-' }}</span>
                </template>
              </el-table-column>
            </el-table>
            <!-- 分页 -->
            <div class="pagination-container">
              <el-pagination
                v-model:current-page="scenarioCurrentPage"
                v-model:page-size="scenarioPageSize"
                :page-sizes="[10, 20, 50, 100]"
                :total="filteredScenarios.length"
                layout="total, sizes, prev, pager, next, jumper"
                @size-change="handleScenarioSizeChange"
                @current-change="handleScenarioCurrentChange"
              />
            </div>
          </div>
          <!-- 空状态 -->
          <div v-else class="empty-state">
            <el-empty :description="scenarioCacheTime ? '缓存已清空，请重新拉取' : '暂无场景数据，请先点击「拉取场景」获取 Apifox 场景列表'">
              <el-button type="primary" @click="fetchScenarios" :loading="fetchingScenarios">
                <el-icon style="margin-right: 4px;"><Refresh /></el-icon>
                拉取场景
              </el-button>
            </el-empty>
          </div>

      </div>
    </div>

    <!-- Apifox 配置抽屉 -->
    <el-drawer v-model="configDrawerVisible" title="Apifox 配置" size="450px" :close-on-click-modal="false" @closed="saveConfig">
      <el-form label-width="130px" label-position="left">
        <el-form-item label="项目 ID">
          <el-input v-model="config.project_id" placeholder="Apifox 项目 ID" clearable />
        </el-form-item>
        <el-form-item label="环境 ID">
          <el-input v-model="config.environment_id" placeholder="Apifox 环境 ID" clearable />
        </el-form-item>
        <el-form-item label="Access Token">
          <el-input v-model="config.access_token" placeholder="请输入 Apifox Access Token" show-password clearable />
        </el-form-item>
        <el-form-item label="本地环境变量" v-if="isRunMode">
          <el-select
            v-model="config.local_environment_id"
            placeholder="选择本地环境变量（可选）"
            clearable
            filterable
            style="width: 100%"
            :loading="loadingEnvironments"
          >
            <el-option
              v-for="env in localEnvironments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
          <div style="font-size: 12px; color: #909399; line-height: 1.4; margin-top: 4px;">
            选择后，本地环境变量将通过 CLI 参数传递给 Apifox，确保变量正确替换
          </div>
        </el-form-item>
      </el-form>
      <div style="margin-top: 20px; padding: 12px; background: #f5f7fa; border-radius: 4px; font-size: 12px; color: #909399; line-height: 1.6;">
        <p style="margin: 0 0 8px 0; font-weight: 600; color: #606266;">配置说明</p>
        <p style="margin: 0 0 4px 0;">• 项目 ID 和环境 ID 可在 Apifox 项目设置中查看</p>
        <p style="margin: 0 0 4px 0;">• Access Token 在 Apifox → 项目设置 → 访问令牌中创建</p>
        <p style="margin: 0 0 4px 0;">• Token 仅存储在服务端配置文件中，不会暴露给前端</p>
        <p style="margin: 0;">• 本地环境变量用于解决 CLI 与客户端变量值不一致的问题</p>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Setting, Check, VideoPlay, Refresh, FolderOpened, View, Delete, Loading, List, CircleCheck, Plus, Edit, ArrowLeft, InfoFilled, Lock, User, Document } from '@element-plus/icons-vue'
import api from '@/utils/api'
import { getEnvironments } from '@/api/api-testing'
import ReportDetail from './components/ReportDetail.vue'

// 模式：'check' = 场景检查（默认），'run' = 场景运行
const props = defineProps({
  mode: { type: String, default: 'check' },
})
const isRunMode = computed(() => props.mode === 'run')

// 配置
const config = reactive({
  project_id: '7366718',
  environment_id: '39566850',
  access_token: '',
  local_environment_id: null,
})
const savingConfig = ref(false)
const configDrawerVisible = ref(false)

// 本地环境列表
const localEnvironments = ref([])
const loadingEnvironments = ref(false)

// 报告生成
const generating = ref(false)
const progressText = ref('')
const taskResult = ref('')
const taskError = ref('')
let pollTimer = null

// 历史报告
const reports = ref([])
const loadingReports = ref(false)
const tableRef = ref(null)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const totalReports = ref(0)

// 报告查看
const currentReportName = ref('')
const showReportDetail = ref(false)

// 规则查看抽屉
const rulesDrawerVisible = ref(false)
const rulesLoading = ref(false)

// 检查规则（从后端API动态加载）
const checkRules = ref([
  { index: 1, name: '场景运行通过', severity: '高', severityType: 'danger', desc: '检查场景最近一次运行是否通过', enabled: true },
  { index: 2, name: '单场景步骤数不超过10步', severity: '中', severityType: 'warning', desc: '不含引用其他场景或分组的步骤', enabled: true },
  { index: 3, name: '增删改后查询断言', severity: '高', severityType: 'danger', desc: 'POST/PUT/DELETE/PATCH后是否有/Search查询并断言', enabled: true },
  { index: 4, name: 'Id参数不能写死', severity: '高', severityType: 'danger', desc: '请求Body中ID参数是否硬编码', enabled: true },
  { index: 5, name: '参数来源校验', severity: '高', severityType: 'danger', desc: '后续步骤参数是否从前置步骤或变量获取', enabled: true },
  { index: 6, name: '名称参数自动化标识', severity: '高', severityType: 'danger', desc: 'Name/Title字段是否含"自动化"标识且为动态值', enabled: true },
  { index: 7, name: '前置后置目录跳过统计', severity: '跳过', severityType: 'info', desc: '排除规则，不产生违规判定', enabled: true },
])

// 加载检查规则
const loadRules = async () => {
  rulesLoading.value = true
  try {
    const res = await api.get('/api-testing/apifox-check/rules/')
    if (res.data.rules && res.data.rules.length > 0) {
      checkRules.value = res.data.rules.map(r => ({ ...r, _toggling: false }))
    }
  } catch (e) {
    console.error('加载检查规则失败:', e)
  } finally {
    rulesLoading.value = false
  }
}

// 切换单条规则启用/停用
const toggleRule = async (row, val) => {
  row._toggling = true
  try {
    const res = await api.post('/api-testing/apifox-check/rules/', {
      action: 'toggle',
      rule_id: row.id,
      enabled: val,
    })
    ElMessage.success(res.data.message || (val ? '规则已启用' : '规则已停用'))
  } catch (e) {
    // 回滚状态
    row.enabled = !val
    ElMessage.error(e.response?.data?.error || '操作失败')
  } finally {
    row._toggling = false
  }
}
const exemptionsDrawerVisible = ref(false)

// 生成进度弹窗
const progressDialogVisible = ref(false)

// ID字段豁免列表
const builtinExemptions = ref([])
const userExemptions = ref([])
const exemptionLoading = ref(false)
const exemptionTableData = computed(() => {
  const builtin = builtinExemptions.value.map(f => ({
    field: f,
    reason: '系统内置豁免字段',
    added_by: 'system',
    added_at: '',
    enabled: true,
    _builtin: true,
  }))
  const user = userExemptions.value.map(e => ({
    ...e,
    _builtin: false,
  }))
  return [...builtin, ...user]
})

// 豁免列表统计
const exemptionStats = computed(() => {
  const data = exemptionTableData.value
  const builtinCount = data.filter(item => item._builtin).length
  const customCount = data.filter(item => !item._builtin).length
  const enabledCount = data.filter(item => item.enabled).length
  const disabledCount = data.filter(item => !item.enabled).length
  return {
    total: data.length,
    builtin: builtinCount,
    custom: customCount,
    enabled: enabledCount,
    disabled: disabledCount,
  }
})

// 添加/编辑弹窗
const exemptionDialogVisible = ref(false)
const editingExemption = ref(null)
const exemptionSubmitting = ref(false)
const exemptionForm = reactive({ field: '', reason: '' })

// 加载豁免列表
const loadExemptions = async () => {
  exemptionLoading.value = true
  try {
    const res = await api.get('/api-testing/apifox-check/exemptions/')
    builtinExemptions.value = res.data.builtin || []
    userExemptions.value = res.data.user_defined || []
  } catch (e) {
    console.error('加载豁免列表失败:', e)
  } finally {
    exemptionLoading.value = false
  }
}

// 打开添加弹窗
const openAddExemptionDialog = () => {
  editingExemption.value = null
  exemptionForm.field = ''
  exemptionForm.reason = ''
  exemptionDialogVisible.value = true
}

// 打开编辑理由弹窗
const openEditReasonDialog = (row) => {
  editingExemption.value = row
  exemptionForm.field = row.field
  exemptionForm.reason = row.reason || ''
  exemptionDialogVisible.value = true
}

// 提交弹窗表单
const submitExemptionForm = async () => {
  const field = exemptionForm.field.trim().toLowerCase()
  const reason = exemptionForm.reason.trim()
  if (!field) return
  if (!reason) {
    ElMessage.warning('请输入豁免理由')
    return
  }
  exemptionSubmitting.value = true
  try {
    if (editingExemption.value) {
      // 编辑理由
      const res = await api.post('/api-testing/apifox-check/exemptions/', {
        action: 'update_reason',
        field: editingExemption.value.field,
        reason: exemptionForm.reason.trim(),
      })
      // 更新本地数据
      const idx = userExemptions.value.findIndex(e => e.field === editingExemption.value.field)
      if (idx >= 0) userExemptions.value[idx] = res.data.item
      ElMessage.success(res.data.message || '更新成功')
    } else {
      // 添加
      const res = await api.post('/api-testing/apifox-check/exemptions/', {
        action: 'add',
        field: field,
        reason: exemptionForm.reason.trim(),
      })
      userExemptions.value = res.data.user_defined || []
      ElMessage.success(res.data.message || '添加成功')
    }
    exemptionDialogVisible.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '操作失败')
  } finally {
    exemptionSubmitting.value = false
  }
}

// 启停开关
const toggleExemption = async (row) => {
  row._toggling = true
  try {
    const res = await api.post('/api-testing/apifox-check/exemptions/', {
      action: 'toggle',
      field: row.field,
    })
    // 更新本地数据
    const idx = userExemptions.value.findIndex(e => e.field === row.field)
    if (idx >= 0) userExemptions.value[idx] = res.data.item
    ElMessage.success(res.data.message)
  } catch (e) {
    row.enabled = !row.enabled // 回滚
    ElMessage.error(e.response?.data?.error || '操作失败')
  } finally {
    row._toggling = false
  }
}

// 删除豁免
const deleteExemption = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除豁免字段「${row.field}」吗？删除后将恢复对该字段的检查。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await api.post('/api-testing/apifox-check/exemptions/', {
      action: 'delete',
      field: row.field,
    })
    userExemptions.value = userExemptions.value.filter(e => e.field !== row.field)
    ElMessage.success(`已删除豁免字段「${row.field}」`)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.error || '删除失败')
    }
  }
}

// 加载配置
const loadConfig = async () => {
  try {
    const res = await api.get('/api-testing/apifox-check/config/')
    config.project_id = res.data.project_id || '7366718'
    config.environment_id = res.data.environment_id || '39566850'
    // 后端返回的 access_token 是脱敏的（含 ****），不要直接填入表单
    // 如果 has_token 为 true，保留空字符串提示用户已保存过
    config.access_token = ''
    // 如果后端返回了 local_environment_id，恢复它
    config.local_environment_id = res.data.local_environment_id || null
  } catch (e) {
    console.error('加载配置失败:', e)
  }
}

// 加载本地环境列表
const loadLocalEnvironments = async () => {
  loadingEnvironments.value = true
  try {
    const res = await getEnvironments({ is_active: true })
    localEnvironments.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('加载本地环境列表失败:', e)
    localEnvironments.value = []
  } finally {
    loadingEnvironments.value = false
  }
}

// 保存配置
const saveConfig = async () => {
  savingConfig.value = true
  try {
    await api.post('/api-testing/apifox-check/config/', {
      project_id: config.project_id,
      environment_id: config.environment_id,
      access_token: config.access_token,
      local_environment_id: config.local_environment_id,
    })
    ElMessage.success('配置保存成功')
    configDrawerVisible.value = false
  } catch (e) {
    ElMessage.error('配置保存失败: ' + (e.response?.data?.error || e.message))
  } finally {
    savingConfig.value = false
  }
}

// 生成报告
const generateReport = async () => {
  // 检查必要参数
  if (!config.project_id || !config.environment_id || !config.access_token) {
    ElMessage.warning('请填写完整的检查配置（项目ID、环境ID、令牌）')
    return
  }

  generating.value = true
  progressDialogVisible.value = true
  progressText.value = '正在保存配置并启动检查任务...'
  taskResult.value = ''
  taskError.value = ''

  try {
    // 先保存配置
    await api.post('/api-testing/apifox-check/config/', {
      project_id: config.project_id,
      environment_id: config.environment_id,
      access_token: config.access_token,
    })

    // 再启动检查任务
    const res = await api.post('/api-testing/apifox-check/generate/', {
      project_id: config.project_id,
      environment_id: config.environment_id,
      access_token: config.access_token,
    })

    if (res.data.task_id) {
      pollTaskStatus(res.data.task_id)
    } else {
      // 后端返回成功但没有 task_id，说明有错误
      generating.value = false
      taskError.value = res.data.error || '启动生成任务失败'
    }
  } catch (e) {
    generating.value = false
    taskError.value = e.response?.data?.error || '启动生成任务失败'
  }
}

// 轮询任务状态
const pollTaskStatus = (taskId) => {
  const poll = async () => {
    try {
      const res = await api.get(`/api-testing/apifox-check/task/${taskId}/`)
      progressText.value = res.data.progress || '处理中...'

      if (res.data.status === 'completed') {
        generating.value = false
        taskResult.value = 'completed'
        progressText.value = '报告生成完成！'
        ElMessage.success('检查报告生成成功！')
        loadReports()
        if (res.data.report_file) {
          setTimeout(() => {
            viewReport({ filename: res.data.report_file })
          }, 500)
        }
      } else if (res.data.status === 'failed') {
        generating.value = false
        taskError.value = res.data.error || '报告生成失败'
      } else {
        pollTimer = setTimeout(poll, 2000)
      }
    } catch (e) {
      generating.value = false
      taskError.value = '查询任务状态失败'
    }
  }
  poll()
}

// 加载历史报告
const loadReports = async () => {
  loadingReports.value = true
  try {
    const res = await api.get('/api-testing/apifox-check/reports/')
    const allReports = res.data.reports || []
    totalReports.value = allReports.length
    
    // 分页处理
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    reports.value = allReports.slice(start, end)
  } catch (e) {
    ElMessage.error('加载报告列表失败')
  } finally {
    loadingReports.value = false
  }
}

// 分页大小变化
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  loadReports()
}

// 页码变化
const handleCurrentChange = (val) => {
  currentPage.value = val
  loadReports()
}

// 查看报告 - 在当前页显示详情
const viewReport = (row) => {
  currentReportName.value = row.filename
  showReportDetail.value = true
}

// 返回列表
const backToList = () => {
  showReportDetail.value = false
  currentReportName.value = ''
}

// 删除报告
const deleteReport = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除报告 "${row.filename}" 吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await api.delete(`/api-testing/apifox-check/report/${row.filename}/delete/`)
    ElMessage.success('报告已删除')
    loadReports()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 格式化文件大小
const formatSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 格式化时间
const formatTime = (isoStr) => {
  if (!isoStr) return '-'
  const d = new Date(isoStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

// ============================================================
// 场景运行功能
// ============================================================

// 场景列表
const scenarios = ref([])
const fetchingScenarios = ref(false)
const selectedScenarios = ref([])
const scenarioTableRef = ref(null)
const scenarioCacheTime = ref('')  // 场景列表缓存时间
const SCENARIO_CACHE_KEY = 'apifox_scenarios_cache'
const selectedScenarioIds = computed(() => selectedScenarios.value.map(s => s.id))

// 场景分页
const scenarioCurrentPage = ref(1)
const scenarioPageSize = ref(10)
const creatorFilter = ref('')
const folderFilter = ref('')
const uniqueCreators = computed(() => {
  const set = new Set(scenarios.value.map(s => s.creator).filter(Boolean))
  return [...set].sort()
})
const uniqueFolders = computed(() => {
  const set = new Set(scenarios.value.map(s => s.folder_path).filter(Boolean))
  return [...set].sort((a, b) => a.localeCompare(b, 'zh-CN'))
})
const filteredScenarios = computed(() => {
  let list = [...scenarios.value]
  if (creatorFilter.value) list = list.filter(s => s.creator === creatorFilter.value)
  if (folderFilter.value) list = list.filter(s => s.folder_path === folderFilter.value)
  return list.sort((a, b) => {
    const fa = a.folder_path || ''
    const fb = b.folder_path || ''
    if (fa !== fb) return fa.localeCompare(fb, 'zh-CN')
    return (a.name || '').localeCompare(b.name || '', 'zh-CN')
  })
})
const pagedScenarios = computed(() => {
  const start = (scenarioCurrentPage.value - 1) * scenarioPageSize.value
  const end = start + scenarioPageSize.value
  return filteredScenarios.value.slice(start, end)
})
watch(creatorFilter, () => { scenarioCurrentPage.value = 1 })
watch(folderFilter, () => { scenarioCurrentPage.value = 1 })

const handleScenarioSizeChange = (val) => {
  scenarioPageSize.value = val
  scenarioCurrentPage.value = 1
}
const handleScenarioCurrentChange = (val) => {
  scenarioCurrentPage.value = val
}

// 运行状态
const running = ref(false)
const runProgressDialogVisible = ref(false)
const runProgressText = ref('')
const runTaskError = ref('')
const runTotal = ref(0)
const runCompleted = ref(0)
const runResults = ref([])
const runTestExecutionId = ref(null)
let runPollTimer = null

const runPassedCount = computed(() => runResults.value.filter(r => r.is_passed).length)
const runFailedCount = computed(() => runResults.value.filter(r => !r.is_passed).length)



// 路由
const router = useRouter()

// 跳转到统一报告页面
const goToUnifiedReport = () => {
  runProgressDialogVisible.value = false
  router.push('/api-testing/reports')
}

// 运行详情抽屉
const runDetailDrawerVisible = ref(false)
const currentRunDetail = ref(null)

// HTTP 方法标签类型
const methodTagType = (method) => {
  const m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'warning'
  if (m === 'PUT' || m === 'PATCH') return ''
  if (m === 'DELETE') return 'danger'
  return 'info'
}

// 状态码颜色
const statusCodeColor = (code) => {
  if (!code) return '#999'
  if (code >= 200 && code < 300) return '#67c23a'
  if (code >= 400 && code < 500) return '#e6a23c'
  if (code >= 500) return '#f56c6c'
  return '#909399'
}

// 查看运行详情
const viewRunDetail = (row) => {
  currentRunDetail.value = row
  runDetailDrawerVisible.value = true
}

// 拉取场景列表
const fetchScenarios = async () => {
  if (!config.project_id || !config.environment_id) {
    ElMessage.warning('请先填写项目 ID 和环境 ID')
    return
  }

  fetchingScenarios.value = true
  try {
    // 先保存配置
    if (config.access_token) {
      await api.post('/api-testing/apifox-check/config/', {
        project_id: config.project_id,
        environment_id: config.environment_id,
        access_token: config.access_token,
      })
    }
    const res = await api.get('/api-testing/apifox-check/scenarios/', {
      params: {
        project_id: config.project_id,
        environment_id: config.environment_id,
      }
    })
    scenarios.value = res.data.scenarios || []
    scenarioCurrentPage.value = 1
    // 保存到 localStorage 缓存
    const cacheData = {
      scenarios: scenarios.value,
      cachedAt: new Date().toISOString(),
      projectId: config.project_id,
    }
    localStorage.setItem(SCENARIO_CACHE_KEY, JSON.stringify(cacheData))
    scenarioCacheTime.value = cacheData.cachedAt
    ElMessage.success(`成功拉取 ${scenarios.value.length} 个场景`)
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '拉取场景列表失败')
  } finally {
    fetchingScenarios.value = false
  }
}

// 从本地缓存加载场景列表
const loadCachedScenarios = () => {
  try {
    const raw = localStorage.getItem(SCENARIO_CACHE_KEY)
    if (!raw) return
    const cache = JSON.parse(raw)
    // 仅当缓存的项目 ID 与当前配置一致时才使用缓存
    if (cache.projectId && cache.projectId === config.project_id) {
      scenarios.value = cache.scenarios || []
      scenarioCacheTime.value = cache.cachedAt || ''
    }
  } catch {
    // 缓存解析失败，忽略
  }
}

// 格式化缓存时间
const formatCacheTime = (isoStr) => {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return isoStr
  }
}

// 表格选择变化
const handleSelectionChange = (selection) => {
  selectedScenarios.value = selection
}

// 全选/取消全选
const toggleAllScenarios = () => {
  if (!scenarioTableRef.value) return
  scenarioTableRef.value.toggleAllSelection()
}

// 运行选中场景
const runScenarios = async () => {
  if (selectedScenarioIds.value.length === 0) {
    ElMessage.warning('请先选择要运行的场景')
    return
  }

  running.value = true
  runProgressDialogVisible.value = true
  runProgressText.value = '正在启动运行任务...'
  runTaskError.value = ''
  runResults.value = []
  runTotal.value = selectedScenarioIds.value.length
  runCompleted.value = 0

  try {
    // 先保存配置
    if (config.access_token) {
      await api.post('/api-testing/apifox-check/config/', {
        project_id: config.project_id,
        environment_id: config.environment_id,
        access_token: config.access_token,
        local_environment_id: config.local_environment_id,
      })
    }

    const res = await api.post('/api-testing/apifox-check/run/', {
      project_id: config.project_id,
      environment_id: config.environment_id,
      access_token: config.access_token,
      scenario_ids: selectedScenarioIds.value,
      local_environment_id: config.local_environment_id,
    })

    if (res.data.task_id) {
      pollRunStatus(res.data.task_id)
    } else {
      running.value = false
      runTaskError.value = res.data.error || '启动运行任务失败'
    }
  } catch (e) {
    running.value = false
    runTaskError.value = e.response?.data?.error || '启动运行任务失败'
  }
}

// 轮询运行状态
const pollRunStatus = (taskId) => {
  const poll = async () => {
    try {
      const res = await api.get(`/api-testing/apifox-check/run/${taskId}/status/`)
      runProgressText.value = res.data.progress || '运行中...'
      runTotal.value = res.data.total || 0
      runCompleted.value = res.data.completed || 0
      runResults.value = res.data.results || []
      runTestExecutionId.value = res.data.test_execution_id || null

      if (res.data.status === 'completed') {
        running.value = false
        runProgressText.value = '运行完成！'
        ElMessage.success(`运行完成：${runPassedCount.value} 通过，${runFailedCount.value} 失败`)
      } else if (res.data.status === 'failed') {
        running.value = false
        runTaskError.value = res.data.error || '运行失败'
      } else {
        runPollTimer = setTimeout(poll, 2000)
      }
    } catch (e) {
      running.value = false
      runTaskError.value = '查询运行状态失败'
    }
  }
  poll()
}

onMounted(async () => {
  await loadConfig()
  loadCachedScenarios()
  loadReports()
  loadExemptions()
  loadLocalEnvironments()
})
</script>

<style lang="scss" scoped>
// ========== 页面容器（与 GeneratedTestCaseList 统一） ==========
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
}

// ========== Tab 样式 ==========
.content-tabs {
  :deep(.el-tabs__header) {
    margin: 0;
    padding: 0 24px;
    background: linear-gradient(135deg, #fafbff 0%, #f8f7ff 100%);
    border-bottom: 1px solid rgba(147, 112, 219, 0.12);

    .el-tabs__item {
      height: 52px;
      line-height: 52px;
      font-size: 14px;
      font-weight: 500;
      color: #6d5d8f;

      &.is-active {
        color: #5a32a3;
        font-weight: 600;
      }

      &:hover {
        color: #7b42f6;
      }
    }

    .el-tabs__active-bar {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      height: 3px;
      border-radius: 2px;
    }
  }

  :deep(.el-tabs__content) {
    padding: 20px 24px;
  }
}

// ========== 运行进度弹窗 ==========
.run-progress-wrap {
  padding: 16px 0;

  .progress-text {
    text-align: center;
    color: #7b42f6;
    font-size: 14px;
    font-weight: 500;
    margin: 16px 0 4px 0;
  }

  .progress-sub-text {
    text-align: center;
    color: #8c8c8c;
    font-size: 13px;
    margin: 0;
  }
}

.run-results-summary {
  padding: 8px 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .el-table {
    flex: 1;
  }
}

// ========== 场景列表区域 ==========
.scenario-section {
  margin-bottom: 20px;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
}

// ========== 运行详情抽屉 ==========
.run-detail-header {
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 16px;

  .run-detail-title {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;

    .scenario-detail-name {
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }
  }

  .run-detail-stats {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;

    .stat-item {
      font-size: 13px;
      color: #666;
      background: #f5f7fa;
      padding: 4px 12px;
      border-radius: 4px;
    }
  }
}

.steps-section {
  .steps-title {
    font-size: 14px;
    font-weight: 600;
    color: #5a32a3;
    margin: 0 0 12px 0;
  }
}

.step-expand-content {
  padding: 12px 24px;
  background: #fafbfc;

  .step-sub-section {
    margin-bottom: 16px;

    &:last-child {
      margin-bottom: 0;
    }

    .sub-title {
      font-size: 13px;
      font-weight: 600;
      color: #333;
      margin-bottom: 8px;
    }
  }

  .assertion-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 4px 0;

    .assertion-name {
      font-size: 13px;
      color: #333;
      flex: 1;
    }

    .assertion-error {
      font-size: 12px;
      color: #f56c6c;
      flex: 2;
    }
  }

  .code-block {
    background: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 12px;
    font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
    color: #333;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 300px;
    overflow-y: auto;
    margin: 0;
  }
}

// ========== 页面标题栏（参考 InterfaceList.vue 样式） ==========
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 20px 24px;

  .filter-section {
    display: flex;
    align-items: center;
    gap: 12px;

    :deep(.el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
      background: #ffffff !important;

      &:hover {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }

      &.is-focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }

    :deep(.el-input__inner) {
      color: #333333;
      font-weight: 400;
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

// ========== 通用卡片容器 ==========
.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);
  background: linear-gradient(135deg, #fafbff 0%, #f8f7ff 100%);

  .card-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
    font-weight: 600;
    color: #5a32a3;

    .el-icon {
      color: #7b42f6;
    }
  }

  .card-subtitle {
    font-size: 12px;
    color: #8c8c8c;
    margin-left: auto;
    margin-right: 16px;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.card-body {
  padding: 20px 24px;

  &.no-padding {
    padding: 0;
  }
}

// ========== 进度卡片 ==========
// 运行进度抽屉内容样式
.progress-dialog-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .progress-bar-wrap {
    padding: 16px 0;
  }

  .progress-info {
    padding: 8px 0;
  }

  .progress-text {
    text-align: center;
    color: #7b42f6;
    font-size: 14px;
    font-weight: 500;
    margin: 16px 0 0 0;
  }
}

// ========== 报告文件名（纯文本样式） ==========
.report-filename {
  color: #333333;
  font-size: 13px;
  font-weight: 400;
}

// ========== 操作按钮样式（参考 XMindConverter.vue） ==========
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

  &.view-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #6b32e6 0%, #4a2393 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
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
}

// ========== 表格全局样式覆盖（参考 InterfaceList.vue） ==========
:deep(.el-table) {
  border: none;
  border-radius: 8px 8px 0 0;
  overflow: hidden;
  min-height: 200px;
  box-shadow: none;
  transition: all 0.3s ease;
  background-color: #ffffff !important;

  /* 覆盖 Element Plus 默认主题变量 */
  --el-color-primary: #7b42f6;
  --el-color-primary-light-3: #9370db;
  --el-color-primary-light-5: #a888e0;
  --el-color-primary-light-7: #c2a9f3;
  --el-color-primary-light-9: #f8f7ff;
  --el-border-color: #e9ecef;
  --el-fill-color-blank: #ffffff;
  --el-table-header-bg-color: #ffffff;
  --el-table-row-hover-bg-color: #ffffff;
  --el-table-tr-bg-color: #ffffff;

  :deep(.el-table__inner-wrapper) {
    background-color: #ffffff !important;
  }

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
    padding: 16px !important;
    text-align: center;
    transition: all 0.3s ease;

    &:hover {
      background-color: #ffffff !important;
    }
  }

  :deep(th .cell) {
    font-weight: 600;
    color: #5a32a3;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  :deep(.el-table__body-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(tr) {
    cursor: pointer;
    background-color: #ffffff !important;

    &:hover {
      background-color: #ffffff !important;
    }
  }

  :deep(td) {
    padding: 12px 16px;
    border-bottom: 1px solid #e9ecef;
    color: #333;
    font-size: 14px;
    font-weight: 400;
    line-height: 24px;
    vertical-align: middle;
    text-align: center;
    background-color: #ffffff !important;

    .cell {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 24px;
    }
  }

  :deep(.el-table__empty-block) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-right-patch) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-body-wrapper) {
    background-color: #ffffff !important;
  }

  :deep(.el-table__fixed-header-wrapper) {
    background-color: #ffffff !important;
  }
}


// ========== Element Plus 组件微调 ==========
:deep(.el-tag--dark) {
  border-radius: 20px;
  padding: 0 12px;
  font-weight: 500;
}

:deep(.el-tag--dark.el-tag--danger) {
  background-color: #e94560;
  border-color: #e94560;
}

:deep(.el-tag--dark.el-tag--warning) {
  background-color: #f5a623;
  border-color: #f5a623;
}

:deep(.el-tag--dark.el-tag--info) {
  background-color: #909399;
  border-color: #909399;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(123, 66, 246, 0.25);

  &:hover {
    background: linear-gradient(135deg, #6b32e6 0%, #4a2393 100%);
    box-shadow: 0 4px 14px rgba(123, 66, 246, 0.35);
  }
}

// 规则查看按钮样式（与开始检查按钮类似，但使用浅色主题）
:deep(.el-button:not(.el-button--primary)) {
  background: linear-gradient(135deg, #f3f0ff 0%, #ede9fe 100%);
  border-color: rgba(123, 66, 246, 0.3);
  color: #7b42f6;
  box-shadow: 0 2px 8px rgba(123, 66, 246, 0.15);

  &:hover {
    background: linear-gradient(135deg, #ede9fe 0%, #e4dcfe 100%);
    border-color: rgba(123, 66, 246, 0.5);
    color: #5a32a3;
    box-shadow: 0 4px 14px rgba(123, 66, 246, 0.25);
  }

  .el-icon {
    color: #7b42f6;
  }
}

:deep(.el-progress-bar__outer) {
  background-color: #ede9fe;
  border-radius: 10px;
}

:deep(.el-progress-bar__inner) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border-radius: 10px;
}

:deep(.el-drawer__header) {
  background: linear-gradient(135deg, #fafbff 0%, #f8f7ff 100%);
  border-bottom: 1px solid rgba(147, 112, 219, 0.12);
  margin-bottom: 0;
  padding: 18px 24px;
  font-weight: 600;
  color: #5a32a3;
}

:deep(.el-form-item__label) {
  color: #5a32a3;
  font-weight: 500;
  font-size: 13px;
}

// 修复抽屉内表单项对齐
:deep(.el-form-item) {
  align-items: flex-start;
}

:deep(.el-form-item__content) {
  align-items: flex-start;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.15) inset;

  &:hover {
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.3) inset;
  }

  &.is-focus {
    box-shadow: 0 0 0 1px #7b42f6 inset;
  }
}

// ========== 报告查看 ==========
.report-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 20px;
  background: #ffffff;

  .loading-spinner {
    width: 80px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
    border-radius: 50%;

    .el-icon {
      color: #7b42f6;
    }
  }

  p {
    color: #6d5d8f;
    font-size: 14px;
    margin: 0;
  }
}

.report-iframe {
  width: 100%;
  height: calc(100vh - 120px);
  border: none;
  border-radius: 0 0 8px 8px;
}

// ========== 现代化抽屉样式 ==========
.modern-drawer {
  :deep(.el-drawer__header) {
    background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
    border-bottom: 1px solid rgba(147, 112, 219, 0.15);
    margin-bottom: 0;
    padding: 20px 24px;

    .el-drawer__title {
      font-size: 18px;
      font-weight: 600;
      color: #5a32a3;
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
      transition: all 0.3s ease;

      &:hover {
        background: rgba(123, 66, 246, 0.1);
        color: #7b42f6;
      }
    }
  }

  :deep(.el-drawer__body) {
    padding: 0;
    background: #fafbfc;
  }
}

// ========== 运行进度抽屉样式 ==========
.run-progress-drawer {
  :deep(.el-drawer__body) {
    padding: 0;
    background: #ffffff;
  }

  .drawer-body {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 24px;
  }

  :deep(.el-drawer__footer) {
    padding: 0;
    border-top: 1px solid #ebeef5;
    background: #ffffff;
  }
}

.drawer-body {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.drawer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(147, 112, 219, 0.08);

  .toolbar-info {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
    border: 1px solid rgba(123, 66, 246, 0.15);
    border-radius: 20px;
    color: #333;
    font-size: 13px;
    font-weight: 500;
    box-shadow: 0 2px 6px rgba(123, 66, 246, 0.06);

    .el-icon {
      color: #7b42f6;
      font-size: 15px;
    }
  }
}

// ========== 现代化表格样式 ==========
.modern-table {
  background: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(147, 112, 219, 0.08);

  :deep(.el-table__header) {
    th {
      background: linear-gradient(180deg, #fafbfc 0%, #f5f3ff 100%) !important;
      color: #5a32a3;
      font-weight: 600;
      font-size: 13px;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(147, 112, 219, 0.1);

      .cell {
        font-weight: 600;
        white-space: nowrap;
      }
    }
  }

  :deep(.el-table__body) {
    tr {
      transition: all 0.2s ease;

      &:hover {
        background-color: #f8f7ff !important;
      }

      td {
        padding: 14px 16px;
        border-bottom: 1px solid rgba(147, 112, 219, 0.06);
        color: #374151;
        font-size: 13px;
      }
    }
  }

  // 斑马纹样式
  :deep(.el-table__row--striped) {
    background-color: #fafbfc !important;

    &:hover {
      background-color: #f5f3ff !important;
    }
  }

  :deep(.el-table__empty-block) {
    padding: 60px 0;

    .el-table__empty-text {
      color: #9ca3af;
      font-size: 14px;
    }
  }
}

// ========== 严重程度标签 ==========
.severity-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  min-width: 48px;

  &.severity-danger {
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    color: #dc2626;
    border: 1px solid rgba(220, 38, 38, 0.15);
  }

  &.severity-warning {
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    color: #d97706;
    border: 1px solid rgba(217, 119, 6, 0.15);
  }

  &.severity-info {
    background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
    color: #6b7280;
    border: 1px solid rgba(107, 114, 128, 0.15);
  }
}

// ========== 规则名称单元格 ==========
.rule-name-cell {
  .rule-name {
    font-weight: 500;
    color: #1f2937;
    font-size: 13px;
  }
}

// ========== 字段徽章样式 ==========
.field-cell {
  display: flex;
  align-items: center;
  gap: 8px;

  .field-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 8px;
    font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
    font-size: 13px;
    font-weight: 500;

    &.builtin {
      background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
      color: #6b7280;
      border: 1px solid rgba(107, 114, 128, 0.15);

      .el-icon {
        font-size: 12px;
      }
    }

    &.custom {
      background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
      color: #2563eb;
      border: 1px solid rgba(37, 99, 235, 0.15);

      .el-icon {
        font-size: 12px;
      }
    }
  }

  .builtin-label {
    background: #f3f4f6;
    border-color: #e5e7eb;
    color: #9ca3af;
    font-weight: 500;
  }
}

// ========== 理由文本样式 ==========
.reason-text {
  color: #4b5563;
  font-size: 13px;
  line-height: 1.5;
}

.reason-placeholder {
  color: #9ca3af;
  font-size: 13px;
  font-style: italic;
}

// ========== 用户单元格样式 ==========
.user-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;

  .user-avatar {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    color: #ffffff;
    font-size: 10px;
    font-weight: 600;
  }

  span {
    color: #6b7280;
    font-size: 13px;
  }
}

// ========== 时间文本样式 ==========
.time-text {
  color: #6b7280;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
}

// ========== 状态徽章样式（参考 XMindConverter.vue） ==========
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

  // 启用 - 绿色
  &.enabled {
    background: #f6ffed;
    color: #52c41a;
  }

  // 停用 - 灰色
  &.disabled {
    background: #f5f5f5;
    color: #8c8c8c;
  }

  // 严重 - 红色
  &.severity-danger {
    background: #fff2f0;
    color: #ff4d4f;
  }

  // 中等 - 橙色
  &.severity-warning {
    background: #fff7e6;
    color: #fa8c16;
  }

  // 跳过/低 - 蓝色
  &.severity-info {
    background: #e6f7ff;
    color: #1890ff;
  }

  // 最近运行 - 通过（绿色）
  &.run-passed {
    background: #f6ffed;
    color: #52c41a;
  }

  // 最近运行 - 失败（红色）
  &.run-failed {
    background: #fff1f0;
    color: #f5222d;
  }

  // 最近运行 - 未运行（灰色）
  &.run-pending {
    background: #f5f5f5;
    color: #8c8c8c;
  }
}

// ========== 操作按钮样式（参考 XMindConverter.vue） ==========
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

  &.toggle-btn {
    background: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;

    &:hover {
      background: linear-gradient(135deg, #ffc53d 0%, #fa8c16 100%) !important;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(250, 140, 22, 0.4);
    }
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
}

.text-gray {
  color: #999;
}

// ========== 系统徽章 ==========
.system-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  color: #9ca3af;
  font-size: 12px;
  font-weight: 500;
  border-radius: 6px;

  .el-icon {
    font-size: 12px;
  }
}

// ========== 现代化按钮 ==========
.modern-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 13px;
  transition: all 0.25s ease;
  border: none;

  &.primary {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(123, 66, 246, 0.25);

    &:hover {
      background: linear-gradient(135deg, #6b32e6 0%, #4a2393 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 14px rgba(123, 66, 246, 0.35);
    }

    .el-icon {
      font-size: 14px;
    }
  }
}

// ========== 现代化开关 ==========
.modern-switch {
  :deep(.el-switch__core) {
    border-radius: 10px;

    .el-switch__action {
      border-radius: 50%;
    }
  }
}

// ========== 表格区域样式（参考 InterfaceList.vue） ==========
.loading-state {
  padding: 40px;
}

.empty-state {
  padding: 60px 0;
}

.table-wrapper {
  padding: 0;
}

.pagination-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 0;
  margin-top: 8px;
  background: transparent;
  border: none;
  transition: all 0.3s ease;

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

// ========== 响应式 ==========
@media (max-width: 1200px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;

    .header-right {
      width: 100%;

      .generate-btn {
        width: 100%;
      }
    }
  }
}

// ========== 豁免列表 ==========
// 白名单抽屉内容样式
.exemptions-drawer-content {
  padding: 20px;
  overflow-x: hidden;

  .exemptions-drawer-header {
    margin-bottom: 16px;
    display: flex;
    justify-content: flex-end;
  }

  .exemption-field-cell {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .builtin-tag {
    background: #f0edff;
    border-color: #d4c9f0;
    color: #5a32a3;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .user-tag {
    font-family: 'SF Mono', 'Fira Code', monospace;
    color: #1890ff;
    border-color: #91d5ff;
    background: #e6f7ff;
  }

  .ml-2 {
    margin-left: 6px;
  }

  .reason-text {
    color: #555;
    font-size: 13px;
  }

  .reason-placeholder {
    color: #c0c0c0;
  }

  .builtin-hint {
    color: #b0a8c4;
    font-size: 12px;
  }

  // 操作按钮（与项目管理页统一风格）
  .action-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 6px;
    border: none;
    transition: all 0.25s ease;

    .el-icon {
      font-size: 13px;
      color: #ffffff;
    }

    span {
      color: #ffffff;
    }

    &:hover {
      transform: translateY(-1px);
    }

    &:active {
      transform: translateY(0);
    }
  }

  .edit-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    box-shadow: 0 2px 8px rgba(123, 66, 246, 0.25);

    &:hover {
      background: linear-gradient(135deg, #6b32e6 0%, #4a2393 100%);
      box-shadow: 0 4px 14px rgba(123, 66, 246, 0.35);
    }
  }

  .delete-btn {
    background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%);
    box-shadow: 0 2px 8px rgba(255, 77, 79, 0.25);

    &:hover {
      background: linear-gradient(135deg, #e8383a 0%, #b9101a 100%);
      box-shadow: 0 4px 14px rgba(255, 77, 79, 0.35);
    }
  }
}

.form-tip {
  font-size: 12px;
  color: #9a8bbd;
  margin-top: 4px;
  line-height: 1.4;
}

// ========== 统计概览卡片（参考 AutomationSuiteDetail.vue 执行结果抽屉） ==========
.stats-cards {
  margin-bottom: 20px;

  .stat-card {
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

    .stat-icon {
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
    }

    .stat-info {
      flex: 1;

      .stat-label {
        color: #8c8c8c;
        font-size: 13px;
        margin-bottom: 4px;
      }

      .stat-value {
        color: #1f2937;
        font-size: 24px;
        font-weight: 600;
      }
    }

    &.total {
      .stat-icon {
        background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
        .el-icon { color: #7b42f6; }
      }
    }

    &.builtin {
      .stat-icon {
        background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
        .el-icon { color: #52c41a; }
      }
      .stat-value { color: #52c41a; }
    }

    &.custom {
      .stat-icon {
        background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%);
        .el-icon { color: #1890ff; }
      }
      .stat-value { color: #1890ff; }
    }

    &.enabled {
      .stat-icon {
        background: linear-gradient(135deg, #fff7e6 0%, #ffe7ba 100%);
        .el-icon { color: #fa8c16; }
      }
      .stat-value { color: #fa8c16; }
    }
  }
}

// ========== 结果表格区域（参考 AutomationSuiteDetail.vue 执行结果抽屉） ==========
.result-table-section {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  overflow: hidden;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: linear-gradient(135deg, #f8f7ff 0%, #ffffff 100%);
    border-bottom: 1px solid rgba(147, 112, 219, 0.12);
    margin-bottom: 0;
    border-left: none;
    border-radius: 0;

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

// ========== 自定义表格样式（参考 AutomationSuiteDetail.vue） ==========
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

  // 序号列样式修复
  :deep(.el-table__column--index) {
    .cell {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #333;
      font-size: 13px;
    }
  }

  :deep(.el-table__empty-block) {
    padding: 40px 0;
  }
}

// ========== 豁免抽屉表单样式 ==========
.exemption-drawer {
  :deep(.el-drawer__body) {
    padding: 0;
    display: flex;
    flex-direction: column;
  }

  .drawer-form-content {
    flex: 1;
    padding: 24px;
    overflow-y: auto;

    :deep(.el-form-item) {
      margin-bottom: 20px;

      &:last-child {
        margin-bottom: 0;
      }
    }

    :deep(.el-form-item__label) {
      color: #5a32a3;
      font-weight: 500;
      font-size: 13px;
      padding-right: 12px;
      line-height: 32px;
      height: 32px;
      align-self: flex-start;
    }

    :deep(.el-form-item__content) {
      line-height: 1.5;
    }

    :deep(.el-textarea__inner) {
      border-radius: 8px;
      padding: 8px 12px;
      line-height: 1.5;
    }
  }

  .drawer-footer {
    padding: 16px 24px;
    border-top: 1px solid rgba(147, 112, 219, 0.12);
    background: #ffffff;
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }

  .form-input-wrap {
    width: 100%;
  }
}

// ========== 运行进度抽屉 Footer ==========
.run-progress-drawer {
  .drawer-footer {
    padding: 16px 24px;
    border-top: 1px solid #ebeef5;
    background: #ffffff;
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
}
</style>
